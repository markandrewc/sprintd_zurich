"""The end-to-end chain: audio -> ASR -> diarization -> checks -> fusion -> snippets -> sinks.

Every stage is a plugin picked by the YAML config and every expensive stage is cached, so
changing one check only reruns that check, and moving the threshold reruns nothing but fusion.

Transcript views (config ``views``, :mod:`callguard.views`): a call may be rendered several times
(Standard German ASR, dialect ASR, translations, Whisper speech translation). :meth:`Pipeline.build_views`
computes the views the enabled checks need, each check reads its own view, fusion merges by audio time.
Without a ``views`` block there is one view ``main`` and every cache key is exactly the v1 key.
"""

from __future__ import annotations

import datetime as _dt
import functools
import logging
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from callguard import audio, preprocess, registry
from callguard.cache import file_hash, stable_hash
from callguard.config import ROOT, AppConfig
from callguard.context import Context
from callguard.plugins import ASRBackend, Check, Diarizer, Fusion, Preprocessor, Sink, Translator
from callguard.types import CallResult, CheckResult, Decision, Family, Transcript
from callguard.views import ViewConfigError, ViewSpec, build_order, parse_views, primary_of, root_of

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
        # views: plugins per view are built lazily (keyed by spec), like the top-level ASR
        self.view_specs: dict[str, ViewSpec] = parse_views(cfg)
        self.multi_view = bool(cfg.views)
        self.primary_view = primary_of(cfg, self.view_specs)
        self._view_asrs: dict[str, ASRBackend] = {}
        self._translators: dict[str, Translator] = {}
        self._preprocessors: dict[str, Preprocessor] = {}
        for c in self.checks:  # fail at start, not after an hour of ASR
            if c.view is not None and c.view not in self.view_specs and not cfg.check_view:
                raise ViewConfigError(f"check {c.name!r} reads view {c.view!r}, which is not defined "
                                      f"(views: {list(self.view_specs)})")
        for name in self.needed_views():  # multi-source views need a translator that takes several
            if self.view_specs[name].alternatives and not self.translator_for(name).multi_source:
                raise ViewConfigError(f"view {name!r}: `from` lists several views but translator "
                                      f"{self.view_specs[name].translator!r} takes one source")

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

    # -- views ----------------------------------------------------------------------------------

    def view_of(self, check: Check) -> str:
        """The view ``check`` reads: ``check_view`` overrides all, else the check's ``view``, else primary."""
        return self.cfg.check_view or check.view or self.primary_view

    def needed_views(self) -> list[str]:
        """Views to compute, sources first: primary + views of enabled checks + extra_views (+ sources)."""
        wanted = [self.primary_view, *(self.view_of(c) for c in self.checks if c.enabled),
                  *self.cfg.extra_views]
        return build_order(self.view_specs, dict.fromkeys(wanted))

    def asr_for(self, view: str) -> ASRBackend:
        spec = self.view_specs[view]
        if spec.asr is None:
            raise ViewConfigError(f"view {view!r} is a translated view, it has no ASR")
        if spec.asr == self.cfg.asr:
            return self.asr  # shared with transcribe() without a view: same plugin, same cache keys
        key = stable_hash(spec.asr)
        if key not in self._view_asrs:
            self._view_asrs[key] = registry.create("asr", spec.asr, ctx=self.ctx)
        return self._view_asrs[key]

    def translator_for(self, view: str) -> Translator:
        spec = self.view_specs[view]
        if spec.translator is None:
            raise ViewConfigError(f"view {view!r} is not a translated view")
        key = stable_hash(spec.translator)
        if key not in self._translators:
            self._translators[key] = registry.create("translator", spec.translator, ctx=self.ctx)
        return self._translators[key]

    def _built_asr(self, spec: ViewSpec) -> ASRBackend | None:
        if spec.asr is None:
            return None
        if spec.asr == self.cfg.asr:
            return self._asr
        return self._view_asrs.get(stable_hash(spec.asr))

    def _as_view(self, t: Transcript, view: str) -> Transcript:
        spec = self.view_specs.get(view)
        t.view = view
        t.lang = spec.lang if spec is not None and spec.lang is not None else t.lang
        return t

    def translate(self, source: Transcript, view: str,
                  alternatives: list[Transcript] | None = None) -> Transcript:
        """Translated view ``view`` of ``source`` (cached on source segments + translator + languages).

        Multi-source views (``from: [primary, ...]``) pass the other source transcripts as
        ``alternatives``; their segments join the key (single-source keys are unchanged)."""
        spec = self.view_specs[view]
        tr = self.translator_for(view)
        target = spec.lang or "en"
        key: dict[str, Any] = {"source": stable_hash(source.segments), "source_lang": source.lang,
                               "translator": tr.cache_params(), "target": target}
        multi = spec.alternatives or alternatives
        if multi:
            alts = list(alternatives or [])
            key["alternatives"] = [{"segments": stable_hash(a.segments), "lang": a.lang} for a in alts]
            compute = lambda: tr.translate_multi(source, alts, target)  # noqa: E731
        else:
            compute = lambda: tr.translate(source, target)  # noqa: E731
        t, cached = self.ctx.cache.get_or_compute("translate", key, Transcript, compute,
                                                  store=lambda t: not t.meta.get("degraded"))
        log.info("translate %s %s -> %s %s", source.call_id, source.view, view, "(cached)" if cached else "")
        t.call_id, t.audio_path = source.call_id, source.audio_path
        return self._as_view(t, view)

    def build_views(self, audio_path: str | Path | None, call_id: str, *,
                    given: dict[str, Transcript] | None = None, warnings: list[str] | None = None,
                    timings: dict[str, float] | None = None,
                    on_stage: Callable[[str], None] | None = None) -> dict[str, Transcript]:
        """Compute every needed view (see :meth:`needed_views`).

        ``given`` binds views to ready transcripts (transcript-only path: reference scripts, synthetic
        text). Views that cannot be computed (an ASR view without audio, a failed translation) are left
        out with a warning; checks reading them then report the view as missing. The primary view must
        exist, else this raises.
        """
        warnings = warnings if warnings is not None else []
        timings = timings if timings is not None else {}
        stage = on_stage or (lambda name: None)
        announced: set[str] = set()

        def enter(name: str) -> float:
            if name not in announced:
                announced.add(name)
                stage(name)
            return time.time()

        def took(name: str, t0: float) -> None:
            timings[name] = timings.get(name, 0.0) + time.time() - t0

        out: dict[str, Transcript] = {}
        multi = self.multi_view
        for name in self.needed_views():
            spec = self.view_specs[name]
            if given and name in given:
                out[name] = self._as_view(given[name].model_copy(deep=True), name)
                continue
            if spec.kind == "asr":
                if audio_path is None:
                    warnings.append(f"view {name}: no audio, ASR view not computed")
                    continue
                t0 = enter("asr")
                try:
                    t = self.transcribe(Path(audio_path), call_id, view=name if multi else None)
                except Exception as e:
                    took("asr", t0)
                    if name == self.primary_view or not multi:
                        raise
                    log.exception("view %s of %s: ASR failed", name, call_id)
                    warnings.append(f"view {name}: ASR failed: {type(e).__name__}: {e}")
                    continue
                took("asr", t0)
                if spec.diarize:
                    t0 = enter("diarize")
                    try:
                        t = self.diarize(Path(audio_path), t)
                    except Exception as e:  # roles are a refinement: checks still run on the plain transcript
                        log.warning("diarization of %s (view %s) failed, continuing without speakers: %s",
                                    call_id, name, e)
                        prefix = f"view {name}: " if multi else ""
                        warnings.append(f"{prefix}diarization failed: {type(e).__name__}: {e}")
                    took("diarize", t0)
                out[name] = t
            else:
                src = out.get(spec.source or "")
                if src is None:
                    warnings.append(f"view {name}: source view {spec.source} missing, not translated")
                    continue
                alts = [out[a] for a in spec.alternatives if a in out]
                missing = [a for a in spec.alternatives if a not in out]
                if missing:  # correct with what is there; the key names the sources actually used
                    warnings.append(f"view {name}: source view(s) {', '.join(missing)} missing, "
                                    f"built from {', '.join([spec.source or '', *(a.view for a in alts)])}")
                t0 = enter("translate")
                try:
                    out[name] = self.translate(src, name, alts) if spec.alternatives else self.translate(src, name)
                except Exception as e:
                    log.exception("view %s of %s: translation failed", name, call_id)
                    warnings.append(f"view {name}: translation failed: {type(e).__name__}: {e}")
                took("translate", t0)
        if self.primary_view not in out:
            raise RuntimeError(f"primary view {self.primary_view!r} of {call_id} could not be built: "
                               f"{'; '.join(warnings) or 'no audio / no transcript'}")
        return out

    # -- stages ---------------------------------------------------------------------------------

    # Cache keys come from the plugins' cache_params() (not the raw YAML block), so plugins can leave
    # out speed-only knobs (threads, concurrency) and add what the YAML does not show (the role LLM's
    # model). Building a plugin is cheap: models load lazily on first use.

    def asr_key(self, audio_path: str | Path, view: str | None = None) -> dict[str, Any]:
        """The key :meth:`transcribe` caches under: the v1 key {audio hash, asr.cache_params()} (views
        with the same ASR share transcripts), plus ``preprocess`` only when ``asr.preprocess`` is set."""
        asr = self.asr if view is None else self.asr_for(view)
        key: dict[str, Any] = {"audio": file_hash(audio_path), "asr": asr.cache_params()}
        pre = self.preprocessor_for(asr)
        if pre is not None:  # the ASR hears processed audio
            key["preprocess"] = pre.cache_params()
        return key

    def transcribe(self, audio_path: Path, call_id: str, view: str | None = None) -> Transcript:
        """ASR of the top-level ``asr`` (``view=None``, v1) or of an ASR view, keyed by :meth:`asr_key`."""
        asr = self.asr if view is None else self.asr_for(view)
        key = self.asr_key(audio_path, view)
        pre = self.preprocessor_for(asr)

        def compute() -> Transcript:
            if pre is None:
                return asr.transcribe(Path(audio_path), call_id)
            with preprocess.prepared(pre, audio_path, self.ctx.cache.root, audio_hash=key["audio"],
                                     keep=self.ctx.cache.enabled) as (processed, info):
                t = asr.transcribe(processed, call_id)
            t.audio_path = str(audio_path)  # timestamps and snippets refer to the original audio
            t.meta["preprocess"] = info
            return t

        t, cached = self.ctx.cache.get_or_compute("asr", key, Transcript, compute,
                                                  store=lambda t: not t.meta.get("degraded"))
        log.info("asr %s %s%s", call_id, f"[{view}] " if view else "", "(cached)" if cached else "")
        t.call_id, t.audio_path = call_id, str(audio_path)
        return self._as_view(t, view) if view is not None else t

    def preprocessor_for(self, asr: ASRBackend) -> Preprocessor | None:
        """The audio pre-processor of ``asr`` (its config ``preprocess`` block), None if unset or identity."""
        spec = getattr(asr, "preprocess", None)
        if not spec:
            return None
        k = stable_hash(spec)
        if k not in self._preprocessors:
            self._preprocessors[k] = registry.create("preprocess", spec, ctx=self.ctx)
        pre = self._preprocessors[k]
        return pre if preprocess.is_active(pre) else None

    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript:
        key = {"transcript": stable_hash(transcript.segments), "diarizer": self.diarizer.cache_params(),
               "audio": file_hash(audio_path) if audio_path else None}
        t, cached = self.ctx.cache.get_or_compute(
            "diarize", key, Transcript, lambda: self.diarizer.diarize(audio_path, transcript),
            store=lambda t: not any((t.meta.get("diarization") or {}).get(k) for k in ("error", "role_error")))
        log.info("diarize %s %s", transcript.call_id, "(cached)" if cached else "")
        t.view, t.lang = transcript.view, transcript.lang  # the cached copy may come from another view
        return t

    def check_key(self, check: Check, transcript: Transcript, families: list[Family]) -> dict[str, Any]:
        key = {"transcript": stable_hash(transcript.segments), "check": check.cache_key(families)}
        if check.lang_sensitive and transcript.lang is not None:
            key["lang"] = transcript.lang  # v1 transcripts have no lang: their key is unchanged
        return key

    def cached_check(self, check: Check, transcript: Transcript, families: list[Family]) -> CheckResult | None:
        """The cached result of ``check`` if there is one; never runs the check (UI: reuse LLM results)."""
        res = self.ctx.cache.get(f"check/{check.name}", self.check_key(check, transcript, families), CheckResult)
        if res is not None:
            res.view = transcript.view
        return res

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
            return CheckResult(check=check.name, type=check.plugin_type, meta={"error": repr(e)},
                               view=transcript.view)
        log.info("check %s %s %s", check.name, transcript.call_id, "(cached)" if cached else "")
        res.view = transcript.view  # not part of the cached value's key: set on every read
        return res

    def check_transcript(self, check: Check, views: dict[str, Transcript] | Transcript) -> Transcript | None:
        """The transcript ``check`` reads among ``views`` (a bare Transcript = single view)."""
        if isinstance(views, Transcript):
            return views
        return views.get(self.view_of(check))

    def run_checks(self, transcript: Transcript | dict[str, Transcript],
                   families: list[Family] | None = None) -> dict[str, CheckResult]:
        """Run every enabled check on its view. ``transcript``: one Transcript (all checks read it, v1)
        or the dict from :meth:`build_views`."""
        families = families if families is not None else self.ctx.families()
        out: dict[str, CheckResult] = {}
        for c in self.checks:
            if not c.enabled:
                continue
            t = self.check_transcript(c, transcript)
            if t is None:
                view = self.view_of(c)
                out[c.name] = CheckResult(check=c.name, type=c.plugin_type, view=view,
                                          meta={"error": f"view {view!r} not available for this call"})
                continue
            out[c.name] = self.run_check(c, t, families)
        return out

    def decide(self, transcript: Transcript, results: dict[str, CheckResult],
               overrides: dict[str, Any] | None = None, families: list[Family] | None = None,
               views: dict[str, Transcript] | None = None) -> Decision:
        """``views`` (multi-view calls: ``CallResult.views``) lets fusion place findings of checks that
        read other views and fill ``Passage.texts``. Omitted for single-view calls (v1 decisions)."""
        families = families if families is not None else self.ctx.families()
        overrides = dict(overrides or {})
        overrides.setdefault("weights", {c.name: c.weight for c in self.checks})
        if views:
            return self.fusion.decide(transcript, results, families, overrides, views=views)
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
        """``on_stage(name)`` is called before each stage (asr, diarize, [translate,] checks, decide,
        snippets, emit) so a UI can show progress without re-implementing the chain."""
        audio_path = Path(audio_path)
        call_id = call_id or audio_path.stem
        timings: dict[str, float] = {}
        stage = on_stage or (lambda name: None)
        warnings: list[str] = []
        views = self.build_views(audio_path, call_id, warnings=warnings, timings=timings, on_stage=stage)
        return self._finish(views, call_id, str(audio_path), warnings, timings, overrides, stage, emit)

    def process_transcript(self, transcript: Transcript, *, emit: bool = False,
                           overrides: dict[str, Any] | None = None, view: str | None = None) -> CallResult:
        """Skip audio: run checks + fusion on a given transcript (reference scripts, synthetic text).

        With views, ``transcript`` is bound to ``view`` (default: the ASR view the primary view is
        built from) and translated views are derived from it; other ASR views need audio and are
        skipped with a warning."""
        bound = view or root_of(self.view_specs, self.primary_view)
        if bound not in self.view_specs:
            raise ViewConfigError(f"view {bound!r} is not defined (views: {list(self.view_specs)})")
        warnings: list[str] = []
        if self.multi_view:
            views = self.build_views(None, transcript.call_id, given={bound: transcript}, warnings=warnings)
        else:
            views = {bound: transcript}  # v1: the transcript object itself, untouched
        return self._finish(views, transcript.call_id, transcript.audio_path, warnings, None, overrides,
                            lambda name: None, emit, snippets=False)

    def _finish(self, views: dict[str, Transcript], call_id: str, audio_path: str | None,
                warnings: list[str], timings: dict[str, float] | None, overrides: dict[str, Any] | None,
                stage: Callable[[str], None], emit: bool, snippets: bool = True) -> CallResult:
        transcript = views[self.primary_view]
        families = self.ctx.families()
        stage("checks")
        t = time.time()
        results = self.run_checks(views if self.multi_view else transcript, families)
        if timings is not None:
            timings["checks"] = time.time() - t

        stage("decide")
        decision = self.decide(transcript, results, overrides, families, views=views if self.multi_view else None)
        meta: dict[str, Any] = {"warnings": warnings} if warnings else {}
        meta["provenance"] = self.provenance(views)
        result = CallResult(call_id=call_id, audio_path=audio_path, transcript=transcript,
                            views=views if self.multi_view else {}, checks=results, decision=decision,
                            config_name=self.cfg.name, timings={k: round(v, 2) for k, v in (timings or {}).items()},
                            meta=meta)
        if snippets:
            stage("snippets")
            self.make_snippets(result)
        if emit:
            stage("emit")
            self.emit(result)
        return result

    # -- provenance -------------------------------------------------------------------------------

    def provenance(self, views: dict[str, Transcript]) -> dict[str, Any]:
        """What produced a result (docs/design/v2_plan.md §5). Only plugins that were actually built are
        asked for their params (no diarizer is loaded just to describe it). Never raises: a plugin whose
        params cannot be read is recorded with the error."""
        def safe(fn: Callable[[], Any]) -> Any:
            try:
                return fn()
            except Exception as e:
                return {"error": f"{type(e).__name__}: {e}"}

        view_info: dict[str, Any] = {}
        for name, t in views.items():
            spec = self.view_specs.get(name)
            info: dict[str, Any] = {"lang": t.lang, "asr_backend": t.asr_backend}
            if spec is not None and spec.kind == "translate":
                info["params"] = {"from": list(spec.sources) if spec.alternatives else spec.source,
                                  "translator": safe(lambda n=name: self.translator_for(n).cache_params())}
            elif spec is not None:
                asr = self._built_asr(spec)
                params: dict[str, Any] = {"asr": safe(asr.cache_params) if asr is not None else None}
                pre = safe(lambda a=asr: self.preprocessor_for(a)) if asr is not None else None
                if pre is not None:  # only when set: v1 provenance unchanged
                    params["preprocess"] = safe(pre.cache_params) if isinstance(pre, Preprocessor) else pre
                if spec.diarize and self._diarizer is not None:
                    params["diarizer"] = safe(self._diarizer.cache_params)
                info["params"] = params
            view_info[name] = info
        checks = {c.name: {"type": c.plugin_type, "view": self.view_of(c), "weight": c.weight,
                           "params": safe(c.cache_params),
                           **({"llm": safe(lambda c=c: c.llm_identity)} if hasattr(c, "llm_identity") else {})}
                  for c in self.checks if c.enabled}
        return {
            "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
            "config_name": self.cfg.name,
            "config_hash": config_hash(self.cfg),
            **({"tuning": self.cfg.tuning} if self.cfg.tuning else {}),  # officer overlay: path, hash, applied
            "code_version": code_version(),
            "primary_view": self.primary_view,
            "views": view_info,
            "checks": checks,
            "fusion": {"type": self.fusion.plugin_type, "params": safe(self.fusion.cache_params)},
        }

    def emit(self, result: CallResult) -> None:
        for s in self.sinks:
            if not s.enabled:
                continue
            try:
                s.emit(result)
            except Exception:
                log.exception("sink %s failed", s.plugin_type)


def config_hash(cfg: AppConfig) -> str:
    return stable_hash(cfg.model_dump(mode="json", exclude={"source_path"}))


@functools.lru_cache(maxsize=1)
def code_version() -> str:
    """Git commit of the code (``+dirty`` with uncommitted changes), or "unknown" outside a checkout."""
    try:
        sha = subprocess.run(["git", "rev-parse", "--short=12", "HEAD"], cwd=ROOT, capture_output=True,
                             text=True, timeout=5).stdout.strip()
        if not sha:
            return "unknown"
        dirty = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", "src"], cwd=ROOT,
                               capture_output=True, timeout=5).returncode != 0
        return sha + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"
