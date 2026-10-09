"""G-Eval check (Liu et al. 2023, "G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment").

Per family: (a) evaluation steps, configured or written once by the LLM from the criteria and
cached; (b) form filling - the prompt ends in an empty score slot and the score is the
probability-weighted mean over the digit tokens, which is smoother and better calibrated than the
single argmax digit; (c) optionally one JSON call that points at the evidence segments so the
officer gets audio passages. The spread of the digit distribution becomes the check's confidence.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from callguard.cache import stable_hash
from callguard.checks import prompts
from callguard.checks.llm_judge import LLMCheck
from callguard.families import family_policy_view
from callguard.plugins import LLM
from callguard.types import Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.geval")

STEPS_NAMESPACE = "geval_steps"


class GEvalSteps(BaseModel):
    """Auto-generated evaluation steps, cached per family criteria + model."""

    family: str
    steps: list[str]
    model: str | None = None
    raw: str = ""


class GEvalCheck(LLMCheck):
    plugin_kind = "check"
    plugin_type = "geval"

    def __init__(self, ctx: "Context", *, llm: str = "default", steps: dict[str, list[str] | str] | None = None,
                 auto_steps: bool = True, scale: int = 5, fallback_samples: int = 5,
                 locate_evidence: bool = True, evidence_min_score: float = 0.4, max_tokens: int = 400,
                 reason_language: str = "de", include_non_alarm: bool = False,
                 max_transcript_chars: int = 24000, parallel: int = 1, name: str | None = None,
                 weight: float = 1.0, enabled: bool = True):
        if not 2 <= int(scale) <= 9:
            raise ValueError(f"scale must be 2..9 (single-digit answers), got {scale}")
        if int(fallback_samples) < 1:
            raise ValueError(f"fallback_samples must be >= 1, got {fallback_samples}")
        if steps is not None and not isinstance(steps, dict):
            raise ValueError("steps must map family id -> list of steps (or one multi-line string)")
        super().__init__(ctx, llm=llm, reason_language=reason_language, include_non_alarm=include_non_alarm,
                         max_transcript_chars=max_transcript_chars, parallel=parallel, name=name,
                         weight=weight, enabled=enabled, steps=steps, auto_steps=auto_steps, scale=scale,
                         fallback_samples=fallback_samples, locate_evidence=locate_evidence,
                         evidence_min_score=evidence_min_score, max_tokens=max_tokens)
        self.steps = {k: prompts.normalize_steps(v) for k, v in (steps or {}).items()}
        self.auto_steps = bool(auto_steps)
        self.scale = int(scale)
        self.fallback_samples = int(fallback_samples)
        self.locate_evidence = bool(locate_evidence)
        self.evidence_min_score = float(evidence_min_score)
        self.max_tokens = int(max_tokens)
        self._steps_memo: dict[str, GEvalSteps] = {}  # survives a disabled disk cache within one run

    # -- (a) evaluation steps ---------------------------------------------------------------------

    def steps_key(self, family: Family) -> dict[str, Any]:
        return {"policy": family_policy_view(family), "llm": self.llm_identity,
                "version": prompts.STEPS_PROMPT_VERSION}

    def evaluation_steps(self, llm: LLM, family: Family) -> tuple[list[str], str, str | None]:
        """-> (steps, source, error). Source is config | auto | auto_cached | default; a failed
        generation falls back to generic steps and is not cached, so the next run tries again."""
        if self.steps.get(family.id):
            return self.steps[family.id], "config", None
        if not self.auto_steps:
            return list(prompts.DEFAULT_STEPS), "default", None
        key = self.steps_key(family)
        memo_key = stable_hash(key)
        hit = self._steps_memo.get(memo_key) or self.ctx.cache.get(STEPS_NAMESPACE, key, GEvalSteps)
        if hit is not None and hit.steps:
            self._steps_memo[memo_key] = hit
            return hit.steps, "auto_cached", None
        try:
            raw = (llm.chat(prompts.steps_messages(family), temperature=0.0, max_tokens=self.max_tokens) or [""])[0]
            steps = prompts.parse_steps(raw)
            if not steps:
                raise ValueError(f"no numbered steps in {raw[:200]!r}")
        except Exception as e:
            log.warning("%s: step generation for %s failed, using default steps: %s", self.name, family.id, e)
            return list(prompts.DEFAULT_STEPS), "default", f"{type(e).__name__}: {e}"
        entry = GEvalSteps(family=family.id, steps=steps, model=self.model_name, raw=raw)
        self.ctx.cache.put(STEPS_NAMESPACE, key, entry)
        self._steps_memo[memo_key] = entry
        return steps, "auto", None

    # -- (b) form filling ------------------------------------------------------------------------

    def score_distribution(self, llm: LLM, messages: list[dict[str, str]]) -> tuple[dict[str, float], dict[str, Any]]:
        """Digit -> probability, from next-token logprobs or, without them, from sampling."""
        choices = [str(i) for i in range(1, self.scale + 1)]
        info: dict[str, Any] = {}
        probs: dict[str, float] | None = None
        try:
            probs = llm.choice_probs(messages, choices)
        except Exception as e:
            log.warning("%s: choice_probs failed, falling back to sampling: %s", self.name, e)
            info["logprobs_error"] = f"{type(e).__name__}: {e}"
        if probs:
            mass = {c: max(0.0, float(probs.get(c) or 0.0)) for c in choices}
            total = sum(mass.values())
            if total > 0 and math.isfinite(total):
                info.update(method="logprobs", coverage=round(total, 4))
                return {c: v / total for c, v in mass.items()}, info
            info["logprobs_error"] = "no probability mass on the score digits"

        outs = llm.chat(messages, temperature=1.0, max_tokens=4, n=self.fallback_samples) or []
        digits = [d for d in (prompts.parse_digit(o, self.scale) for o in outs) if d is not None]
        if not digits:
            raise ValueError(f"no score digit in {len(outs)} sampled answers, e.g. {outs[:1]!r}")
        info.update(method="sampling", samples=[str(o)[:20] for o in outs], valid=len(digits))
        return {c: digits.count(int(c)) / len(digits) for c in choices}, info

    # -- (c) evidence ----------------------------------------------------------------------------

    def locate(self, llm: LLM, transcript: Transcript, rendered: str, family: Family,
               expected: float) -> tuple[list[str], str]:
        messages = prompts.evidence_messages(family, rendered, expected, self.scale, self.reason_language,
                                             example_id=transcript.segments[0].id)
        raw = (llm.chat(messages, temperature=0.0, max_tokens=self.max_tokens,
                        json_schema=prompts.evidence_schema()) or [""])[0]
        obj = prompts.parse_json_object(raw)
        if obj is None:
            raise ValueError(f"unparseable evidence answer: {str(raw)[:200]!r}")
        return prompts.clean_evidence(obj.get("evidence"), transcript), prompts.clean_reason(obj.get("reason"))

    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        steps, steps_source, steps_error = self.evaluation_steps(llm, family)
        messages = prompts.geval_messages(family, rendered, steps, self.scale, self.reason_language)
        dist, info = self.score_distribution(llm, messages)

        expected = sum(int(c) * p for c, p in dist.items())
        score = min(1.0, max(0.0, (expected - 1) / (self.scale - 1)))
        entropy = -sum(p * math.log(p) for p in dist.values() if p > 0)
        confidence = min(1.0, max(0.0, 1 - entropy / math.log(self.scale)))
        detail: dict[str, Any] = {"distribution": {c: round(p, 4) for c, p in dist.items()},
                                  "expected": round(expected, 4), "steps": steps,
                                  "steps_source": steps_source, **info}
        if steps_error:
            detail["steps_error"] = steps_error
        fs = FamilyScore(score=round(score, 4), confidence=round(confidence, 4), verdict=None,
                         reason=f"G-Eval {expected:.2f}/{self.scale}", detail=detail)

        findings: list[Finding] = []
        if self.locate_evidence and score >= self.evidence_min_score:
            try:
                seg_ids, reason = self.locate(llm, transcript, rendered, family, expected)
            except Exception as e:
                log.warning("%s: evidence call for %s failed: %s", self.name, family.id, e)
                fs.detail["evidence_error"] = f"{type(e).__name__}: {e}"
            else:
                fs.segment_ids = seg_ids
                if reason:
                    fs.reason = f"{reason} (G-Eval {expected:.2f}/{self.scale})"
                findings = self.evidence_findings(transcript, family, seg_ids, fs.score,
                                                  lambda run: reason or fs.reason,
                                                  {"expected": fs.detail["expected"]})
        return fs, findings
