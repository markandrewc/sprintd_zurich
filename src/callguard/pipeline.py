"""The end-to-end chain: audio -> ASR -> diarization -> checks -> fusion -> snippets -> sinks.

Every stage is a plugin picked by the YAML config and every expensive stage is cached, so
changing one check only reruns that check, and moving the threshold reruns nothing but fusion.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable

from callguard import audio, registry
from callguard.cache import file_hash, stable_hash
from callguard.config import AppConfig
from callguard.context import Context
from callguard.plugins import ASRBackend, Check, Diarizer, Fusion, Sink
from callguard.types import CallResult, CheckResult, Decision, Family, Transcript

log = logging.getLogger("callguard")


class Pipeline:
    def __init__(self, cfg: AppConfig, *, use_cache: bool = True):
        self.cfg = cfg
        self.ctx = Context(cfg, use_cache=use_cache)
        self._asr: ASRBackend | None = None
        self._diarizer: Diarizer | None = None
        self.checks: list[Check] = [registry.create("check", spec, ctx=self.ctx) for spec in cfg.checks]
        self.fusion: Fusion = registry.create("fusion", cfg.fusion, ctx=self.ctx)
        self.sinks: list[Sink] = [registry.create("sink", spec, ctx=self.ctx) for spec in cfg.sinks]

    # -- lazily built: loading Whisper is slow and not needed when everything is cached ----------

    @property
    def asr(self) -> ASRBackend:
        if self._asr is None:
            self._asr = registry.create("asr", self.cfg.asr, ctx=self.ctx)
        return self._asr

    @property
    def diarizer(self) -> Diarizer:
        if self._diarizer is None:
            self._diarizer = registry.create("diarizer", self.cfg.diarizer, ctx=self.ctx)
        return self._diarizer

    # -- stages ---------------------------------------------------------------------------------

    # Cache keys come from the plugins' cache_params() (not the raw YAML block), so plugins can leave
    # out speed-only knobs (threads, concurrency) and add what the YAML does not show (the role LLM's
    # model). Building a plugin is cheap: models load lazily on first use.

    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        key = {"audio": file_hash(audio_path), "asr": self.asr.cache_params()}
        t, cached = self.ctx.cache.get_or_compute(
            "asr", key, Transcript, lambda: self.asr.transcribe(Path(audio_path), call_id),
            store=lambda t: not t.meta.get("degraded"))
        log.info("asr %s %s", call_id, "(cached)" if cached else "")
        t.call_id, t.audio_path = call_id, str(audio_path)
        return t

    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript:
        key = {"transcript": stable_hash(transcript.segments), "diarizer": self.diarizer.cache_params(),
               "audio": file_hash(audio_path) if audio_path else None}
        t, cached = self.ctx.cache.get_or_compute(
            "diarize", key, Transcript, lambda: self.diarizer.diarize(audio_path, transcript),
            store=lambda t: not (t.meta.get("diarization") or {}).get("error"))
        log.info("diarize %s %s", transcript.call_id, "(cached)" if cached else "")
        return t

    def check_key(self, check: Check, transcript: Transcript, families: list[Family]) -> dict[str, Any]:
        return {"transcript": stable_hash(transcript.segments), "check": check.cache_key(families)}

    def cached_check(self, check: Check, transcript: Transcript, families: list[Family]) -> CheckResult | None:
        """The cached result of ``check`` if there is one; never runs the check (UI: reuse LLM results)."""
        return self.ctx.cache.get(f"check/{check.name}", self.check_key(check, transcript, families), CheckResult)

    def run_check(self, check: Check, transcript: Transcript, families: list[Family]) -> CheckResult:
        key = self.check_key(check, transcript, families)
        t0 = time.time()

        def compute() -> CheckResult:
            r = check.run(transcript, families)
            r.check, r.type = check.name, check.plugin_type
            r.meta.setdefault("seconds", round(time.time() - t0, 2))
            return r

        def complete(r: CheckResult) -> bool:  # a family that failed briefly must be retried next run
            return r.meta.get("cacheable", True) and not r.meta.get("errors") and not r.meta.get("error")

        try:
            res, cached = self.ctx.cache.get_or_compute(f"check/{check.name}", key, CheckResult, compute,
                                                        store=complete)
        except Exception as e:  # a broken check must not kill the call: fusion sees it as missing
            log.exception("check %s failed", check.name)
            return CheckResult(check=check.name, type=check.plugin_type, meta={"error": repr(e)})
        log.info("check %s %s %s", check.name, transcript.call_id, "(cached)" if cached else "")
        return res

    def run_checks(self, transcript: Transcript, families: list[Family] | None = None) -> dict[str, CheckResult]:
        families = families if families is not None else self.ctx.families()
        return {c.name: self.run_check(c, transcript, families) for c in self.checks if c.enabled}

    def decide(self, transcript: Transcript, results: dict[str, CheckResult],
               overrides: dict[str, Any] | None = None, families: list[Family] | None = None) -> Decision:
        families = families if families is not None else self.ctx.families()
        overrides = dict(overrides or {})
        overrides.setdefault("weights", {c.name: c.weight for c in self.checks})
        return self.fusion.decide(transcript, results, families, overrides)

    def make_snippets(self, result: CallResult) -> None:
        if not result.audio_path or not result.decision.passages:
            return
        pad = float(self.cfg.snippets.get("pad", 2.0))
        out_dir = self.ctx.runs_dir / result.call_id / "snippets"
        try:
            samples = audio.load_audio(result.audio_path)
        except Exception as e:  # unreadable audio: passages keep timestamps + reasons, just no clip
            log.warning("snippets for %s skipped: %s", result.call_id, e)
            result.meta.setdefault("warnings", []).append(f"snippets: {e}")
            return
        for i, p in enumerate(result.decision.passages):
            out = out_dir / f"{i:02d}_{p.family}_{int(p.start)}s.wav"
            audio.cut(result.audio_path, p.start, p.end, out, pad=pad, audio=samples)
            p.snippet_path = str(out)

    # -- whole call -------------------------------------------------------------------------------

    def process(self, audio_path: str | Path, call_id: str | None = None, *, emit: bool = True,
                overrides: dict[str, Any] | None = None,
                on_stage: Callable[[str], None] | None = None) -> CallResult:
        """``on_stage(name)`` is called before each stage (asr, diarize, checks, decide, snippets, emit)
        so a UI can show progress without re-implementing the chain."""
        audio_path = Path(audio_path)
        call_id = call_id or audio_path.stem
        timings: dict[str, float] = {}
        stage = on_stage or (lambda name: None)

        stage("asr")
        t = time.time()
        transcript = self.transcribe(audio_path, call_id)
        timings["asr"] = time.time() - t

        stage("diarize")
        t = time.time()
        warnings: list[str] = []
        try:
            transcript = self.diarize(audio_path, transcript)
        except Exception as e:  # roles are a refinement: the checks still run on the plain transcript
            log.warning("diarization of %s failed, continuing without speakers: %s", call_id, e)
            warnings.append(f"diarization failed: {type(e).__name__}: {e}")
        timings["diarize"] = time.time() - t

        families = self.ctx.families()
        stage("checks")
        t = time.time()
        results = self.run_checks(transcript, families)
        timings["checks"] = time.time() - t

        stage("decide")
        decision = self.decide(transcript, results, overrides, families)
        result = CallResult(call_id=call_id, audio_path=str(audio_path), transcript=transcript,
                            checks=results, decision=decision, config_name=self.cfg.name,
                            timings={k: round(v, 2) for k, v in timings.items()},
                            meta={"warnings": warnings} if warnings else {})
        stage("snippets")
        self.make_snippets(result)
        if emit:
            stage("emit")
            self.emit(result)
        return result

    def process_transcript(self, transcript: Transcript, *, emit: bool = False,
                           overrides: dict[str, Any] | None = None) -> CallResult:
        """Skip audio: run checks + fusion on a given transcript (reference scripts, synthetic text)."""
        families = self.ctx.families()
        results = self.run_checks(transcript, families)
        decision = self.decide(transcript, results, overrides, families)
        result = CallResult(call_id=transcript.call_id, audio_path=transcript.audio_path,
                            transcript=transcript, checks=results, decision=decision,
                            config_name=self.cfg.name)
        if emit:
            self.emit(result)
        return result

    def emit(self, result: CallResult) -> None:
        for s in self.sinks:
            if not s.enabled:
                continue
            try:
                s.emit(result)
            except Exception:
                log.exception("sink %s failed", s.plugin_type)
