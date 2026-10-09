"""LLM-as-judge check: one structured question per misconduct family.

Keywords cannot tell "I want to buy before the announcement" from "buying before the announcement
would be insider trading"; a model reading the whole call against the family's criteria can, and it
says why and where. ``samples > 1`` asks several times at ``temperature > 0`` (self-consistency):
disagreement between samples lowers the confidence so the fusion can route the call to review.

Also home of :class:`LLMCheck`, the plumbing shared with the G-Eval check.
"""

from __future__ import annotations

import logging
import time
from abc import abstractmethod
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Callable

from callguard.checks import prompts
from callguard.families import family_policy_view
from callguard.plugins import LLM, Check
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript, Verdict

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.llm")

RETRY_TEMPERATURE = 0.5  # a deterministic retry would repeat the same broken output


class LLMCheck(Check):
    """Shared plumbing of the LLM checks: family selection, transcript rendering, a cache key that
    ignores the keyword list, and per-family error isolation.

    Subclasses implement :meth:`score_family`. If every family fails (server down, wrong model
    name) :meth:`run` raises, so the pipeline reports the check as missing instead of caching an
    empty result; partial failures are returned with ``meta["errors"]``.
    """

    _SPEED_ONLY_PARAMS = ("parallel",)

    def __init__(self, ctx: "Context", *, llm: str = "default", reason_language: str = "de",
                 include_non_alarm: bool = False, max_transcript_chars: int = 24000, parallel: int = 1,
                 name: str | None = None, weight: float = 1.0, enabled: bool = True, **params: Any):
        if int(max_transcript_chars) < 200:
            raise ValueError(f"max_transcript_chars must be >= 200, got {max_transcript_chars}")
        if int(parallel) < 1:
            raise ValueError(f"parallel must be >= 1, got {parallel}")
        super().__init__(ctx, name=name, weight=weight, enabled=enabled, llm=llm,
                         reason_language=reason_language, include_non_alarm=include_non_alarm,
                         max_transcript_chars=max_transcript_chars, parallel=parallel, **params)
        self.llm_name = llm
        self.reason_language = reason_language
        self.include_non_alarm = bool(include_non_alarm)
        self.max_transcript_chars = int(max_transcript_chars)
        self.parallel = int(parallel)

    def cache_params(self) -> dict[str, Any]:
        p = super().cache_params()
        for k in self._SPEED_ONLY_PARAMS:
            p.pop(k, None)
        return p

    @property
    def model_name(self) -> str | None:
        """Model id from the config, available without connecting to the server."""
        spec = self.ctx.cfg.llms.get(self.llm_name) or {}
        model = spec.get("model")
        return str(model) if model is not None else None

    @property
    def llm_identity(self) -> dict[str, Any]:
        """What the answers depend on: the LLM plugin's cache params (type + model + decoding), so a
        fake LLM and the real model with the same configured name never share cached results."""
        try:
            return self.ctx.llm(self.llm_name).cache_params()
        except Exception:  # unconfigured / unbuildable LLM: the run fails anyway, keep the key stable
            spec = self.ctx.cfg.llms.get(self.llm_name) or {}
            return {"type": spec.get("type"), "model": spec.get("model")}

    def select_families(self, families: list[Family]) -> list[Family]:
        return [f for f in families if f.enabled and (f.can_alarm or self.include_non_alarm)]

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        return {
            "params": self.cache_params(),
            "llm": self.llm_identity,
            "families": [family_policy_view(f) for f in self.select_families(families)],
            "prompt_version": prompts.PROMPT_VERSION,
        }

    @abstractmethod
    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        """Score one family. May raise: :meth:`run` turns that into ``meta["errors"][family]``."""

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        fams = self.select_families(families)
        chosen = {f.id for f in fams}
        result = CheckResult(check=self.name, type=self.plugin_type)
        meta = result.meta  # mutate the model's own dict: pydantic copies dicts passed in
        meta.update(llm=self.llm_name, model=self.model_name, prompt_version=prompts.PROMPT_VERSION)
        skipped = [f.id for f in families if f.id not in chosen]
        if skipped:
            meta["skipped_families"] = skipped
        if not fams:
            return result
        if not transcript.segments:
            meta["skipped"] = "empty transcript"
            return result

        rendered, omitted = prompts.render_transcript(transcript, self.max_transcript_chars)
        if omitted:
            meta["omitted_lines"] = omitted
            log.warning("%s: %s transcript too long, %d lines omitted from the prompt",
                        self.name, transcript.call_id, omitted)
        try:
            llm = self.ctx.llm(self.llm_name)
        except Exception as e:
            raise RuntimeError(f"{self.name}: LLM {self.llm_name!r} unavailable: {e}") from e
        meta["model"] = llm.model_id

        def one(f: Family) -> tuple[Family, Any, str | None, float]:
            t0 = time.time()
            try:
                return f, self.score_family(llm, transcript, rendered, f), None, time.time() - t0
            except Exception as e:
                log.warning("%s: family %s failed on %s: %s", self.name, f.id, transcript.call_id, e)
                return f, None, f"{type(e).__name__}: {e}", time.time() - t0

        if self.parallel > 1 and len(fams) > 1:
            with ThreadPoolExecutor(max_workers=min(self.parallel, len(fams))) as ex:
                outs = list(ex.map(one, fams))
        else:
            outs = [one(f) for f in fams]

        errors: dict[str, str] = {}
        meta["family_seconds"] = {}
        for f, out, err, secs in outs:
            meta["family_seconds"][f.id] = round(secs, 2)
            if err is not None:
                errors[f.id] = err
                continue
            fs, findings = out
            result.family_scores[f.id] = fs
            result.findings.extend(findings)
        if errors:
            meta["errors"] = errors
            meta["cacheable"] = False  # hint for the pipeline: a rerun may fill the gaps
            if not result.family_scores:
                raise RuntimeError(f"{self.name}: every family failed: {errors}")
        return result

    def evidence_findings(self, transcript: Transcript, family: Family, seg_ids: list[str],
                          score: float, reason_for: Callable[[list[str]], str],
                          detail: dict[str, Any] | None = None) -> list[Finding]:
        """One Finding per contiguous run of cited segments, so each becomes one audio passage."""
        findings = []
        for run in contiguous_runs(transcript, seg_ids):
            span = transcript.span(run)
            findings.append(Finding(
                check=self.name, family=family.id, score=score, segment_ids=run,
                start=span[0] if span else None, end=span[1] if span else None,
                reason=reason_for(run), detail=dict(detail or {}),
            ))
        return findings


def contiguous_runs(transcript: Transcript, seg_ids: list[str]) -> list[list[str]]:
    """Group segment ids into runs of neighbouring segments (transcript order)."""
    order = {s.id: i for i, s in enumerate(transcript.segments)}
    idx = sorted({order[s] for s in seg_ids if s in order})
    runs: list[list[int]] = []
    for i in idx:
        if runs and i == runs[-1][-1] + 1:
            runs[-1].append(i)
        else:
            runs.append([i])
    return [[transcript.segments[i].id for i in run] for run in runs]


def sample_probability(verdict: Verdict, confidence: float) -> float:
    """Map one judge answer to a risk probability: undetermined sits on the fence at 0.5."""
    if verdict == "present":
        return 0.5 + 0.5 * confidence
    if verdict == "absent":
        return 0.5 - 0.5 * confidence
    return 0.5


def aggregate_samples(samples: list[dict[str, Any]]) -> tuple[float, Verdict, float, list[int]]:
    """Self-consistency vote -> (score, verdict, confidence, indices of the majority samples).

    A tie between verdicts is itself a sign of doubt, so it resolves to "undetermined".
    """
    score = sum(s["p"] for s in samples) / len(samples)
    votes = Counter(s["verdict"] for s in samples)
    top = max(votes.values())
    tied = [v for v in prompts.VERDICTS if votes.get(v) == top]
    verdict: Verdict = tied[0] if len(tied) == 1 else "undetermined"
    majority = [i for i, s in enumerate(samples) if s["verdict"] in tied]
    mean_conf = sum(samples[i]["confidence"] for i in majority) / len(majority)
    return score, verdict, top / len(samples) * mean_conf, majority


class LLMJudgeCheck(LLMCheck):
    plugin_kind = "check"
    plugin_type = "llm_judge"

    def __init__(self, ctx: "Context", *, llm: str = "default", samples: int = 1, temperature: float = 0.0,
                 max_tokens: int = 400, reason_language: str = "de", include_non_alarm: bool = False,
                 max_transcript_chars: int = 24000, parallel: int = 1, name: str | None = None,
                 weight: float = 1.0, enabled: bool = True):
        if int(samples) < 1:
            raise ValueError(f"samples must be >= 1, got {samples}")
        super().__init__(ctx, llm=llm, reason_language=reason_language, include_non_alarm=include_non_alarm,
                         max_transcript_chars=max_transcript_chars, parallel=parallel, name=name,
                         weight=weight, enabled=enabled, samples=samples, temperature=temperature,
                         max_tokens=max_tokens)
        self.samples = int(samples)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        if self.samples > 1 and self.temperature == 0.0:
            log.warning("%s: samples=%d at temperature 0 gives identical samples", self.name, self.samples)

    def _ask(self, llm: LLM, messages: list[dict[str, str]], transcript: Transcript,
             temperature: float) -> tuple[list[dict[str, Any]], list[str]]:
        raws = llm.chat(messages, temperature=temperature, max_tokens=self.max_tokens, n=self.samples,
                        json_schema=prompts.judge_schema())
        samples, invalid = [], []
        for raw in raws or []:
            obj = prompts.parse_json_object(raw)
            verdict = prompts.parse_verdict(obj.get("verdict")) if obj else None
            if verdict is None:
                invalid.append(str(raw)[:500])
                continue
            conf = prompts.parse_confidence(obj.get("confidence"))
            samples.append({
                "verdict": verdict, "confidence": round(conf, 4),
                "p": round(sample_probability(verdict, conf), 4),
                "reason": prompts.clean_reason(obj.get("reason")),
                "evidence": prompts.clean_evidence(obj.get("evidence"), transcript),
            })
        return samples, invalid

    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        messages = prompts.judge_messages(family, rendered, self.reason_language,
                                          example_id=transcript.segments[0].id)
        samples, invalid = self._ask(llm, messages, transcript, self.temperature)
        retried = False
        if not samples:
            retried = True
            log.warning("%s: unparseable answer for %s, retrying once", self.name, family.id)
            samples, invalid2 = self._ask(llm, messages, transcript, max(self.temperature, RETRY_TEMPERATURE))
            invalid += invalid2
        if not samples:
            first = invalid[0][:200] if invalid else "<no completion>"
            raise ValueError(f"no valid judge answer after retry; first output: {first!r}")

        score, verdict, confidence, majority = aggregate_samples(samples)
        by_conf = sorted(majority, key=lambda i: -samples[i]["confidence"])
        cited = {sid for i in majority for sid in samples[i]["evidence"]}
        seg_ids = [s.id for s in transcript.segments if s.id in cited]
        detail: dict[str, Any] = {"samples": samples,
                                  "votes": dict(Counter(s["verdict"] for s in samples))}
        if invalid:
            detail["invalid"] = invalid
        if retried:
            detail["retried"] = True
        fs = FamilyScore(score=round(score, 4), confidence=round(confidence, 4), verdict=verdict,
                         reason=samples[by_conf[0]]["reason"], segment_ids=seg_ids, detail=detail)

        findings: list[Finding] = []
        if verdict in ("present", "undetermined"):
            def reason_for(run: list[str]) -> str:
                i = next((i for i in by_conf if set(run) & set(samples[i]["evidence"])), by_conf[0])
                return samples[i]["reason"]

            findings = self.evidence_findings(transcript, family, seg_ids, fs.score, reason_for,
                                              {"verdict": verdict, "confidence": fs.confidence})
        return fs, findings
