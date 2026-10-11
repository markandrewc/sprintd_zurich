"""G-Eval with a written analysis before the score (``geval_cot``).

Measured on the dev folds (research/journal.md, 01:45): plain ``geval`` with Qwen2.5-7B puts ~99% of
the probability on "3" (the scale middle, described as "undetermined") for almost every call and
family, even when its own evidence reason describes the misconduct. Two changes, both switchable:

- ``analysis: true``: the model first writes a short analysis (who said what, did the act happen,
  harmless explanation?), then the score digit is read from the next-token log-probabilities in a
  second turn that sees the analysis (G-Eval's "chain of thought" step, done per call, not per family
  description). The analysis doubles as the officer-readable reason.
- ``anchor_middle: false``: the scale text no longer labels the middle as "undetermined"; open
  questions are named in the analysis and scored by how likely the misconduct is.

Plugin type ``geval_cot``; drop-in next to or instead of ``geval``.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from callguard.checks import prompts
from callguard.checks.geval import GEvalCheck
from callguard.types import Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context
    from callguard.llm import LLM

log = logging.getLogger("callguard.checks")

COT_PROMPT_VERSION = "geval-cot-1"


def _scale_text(scale: int, anchor_middle: bool) -> str:
    if anchor_middle:
        mid = (1 + scale) // 2
        return (f"1 = clearly absent (not discussed, or only mentioned, explained, quoted, negated, refused or "
                f"harmless); {mid} = undetermined (a decisive fact cannot be established from the call); "
                f"{scale} = clearly present (the misconduct actually happens).")
    return (f"1 = clearly absent (not discussed, or only mentioned, explained, quoted, negated, refused or "
            f"harmless); {scale} = clearly present (the misconduct actually happens in this call). Use the "
            f"values in between for how likely it is that the misconduct actually happened.")


def analysis_messages(f: Family, rendered: str, steps: list[str], reason_language: str,
                      transcript_lang: str | None) -> list[dict[str, str]]:
    steps_txt = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    lang = prompts.language_name(reason_language)
    user = (
        f"{prompts._transcript_block(rendered)}\n\n"
        "Task: analyse whether the phone call above shows the misconduct defined by the criteria.\n\n"
        f"Criteria:\n{prompts.family_block(f)}\n\n"
        f"Evaluation steps:\n{steps_txt}\n\n"
        f"Write a short analysis in {lang} (at most 5 sentences): quote the decisive passage(s) with "
        "their segment ids and who said it, say whether the act actually happened or was only "
        "mentioned/refused/harmless, and name any decisive fact that stays open. No score yet."
    )
    return [{"role": "system", "content": prompts.system_prompt(reason_language, scoring=True,
                                                                transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]


class GEvalCoTCheck(GEvalCheck):
    plugin_kind = "check"
    plugin_type = "geval_cot"

    def __init__(self, ctx: "Context", *, analysis: bool = True, anchor_middle: bool = False,
                 analysis_max_tokens: int = 300, **kw: Any):
        super().__init__(ctx, **kw)
        self.params.update(analysis=bool(analysis), anchor_middle=bool(anchor_middle),
                           analysis_max_tokens=int(analysis_max_tokens), cot_version=COT_PROMPT_VERSION)
        self.analysis = bool(analysis)
        self.anchor_middle = bool(anchor_middle)
        self.analysis_max_tokens = int(analysis_max_tokens)

    def score_family(self, llm: "LLM", transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        steps, steps_source, steps_error = self.evaluation_steps(llm, family)
        lang = transcript.lang
        text = ""
        llm_calls = 0
        if self.analysis:
            msgs = analysis_messages(family, rendered, steps, self.reason_language, lang)
            text = ((llm.chat(msgs, temperature=0.0, max_tokens=self.analysis_max_tokens) or [""])[0] or "").strip()
            llm_calls += 1
            messages = msgs + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": (
                    f"Scale: {_scale_text(self.scale, self.anchor_middle)}\n"
                    f"Based on your analysis, rate the misconduct \"{family.label}\" (1-{self.scale}). "
                    "Answer with the digit only:")},
            ]
        else:
            messages = prompts.geval_messages(family, rendered, steps, self.scale, self.reason_language,
                                              transcript_lang=lang)
            if not self.anchor_middle:
                old = messages[1]["content"]
                start = old.index("Scale: ")
                end = old.index("\n\n", start)
                messages[1]["content"] = old[:start] + "Scale: " + _scale_text(self.scale, False) + old[end:]
        dist, info = self.score_distribution(llm, messages)
        llm_calls += 1

        expected = sum(int(c) * p for c, p in dist.items())
        score = min(1.0, max(0.0, (expected - 1) / (self.scale - 1)))
        entropy = -sum(p * math.log(p) for p in dist.values() if p > 0)
        confidence = min(1.0, max(0.0, 1 - entropy / math.log(self.scale)))
        detail: dict[str, Any] = {"distribution": {c: round(p, 4) for c, p in dist.items()},
                                  "expected": round(expected, 4), "steps": steps,
                                  "steps_source": steps_source, "analysis": text, "llm_calls": llm_calls, **info}
        if steps_error:
            detail["steps_error"] = steps_error
        reason = prompts.clean_reason(text) if text else ""
        fs = FamilyScore(score=round(score, 4), confidence=round(confidence, 4), verdict=None,
                         reason=f"{reason} (G-Eval {expected:.2f}/{self.scale})" if reason
                         else f"G-Eval {expected:.2f}/{self.scale}", detail=detail)
        findings: list[Finding] = []
        if self.locate_evidence and score >= self.evidence_min_score:
            try:
                seg_ids, ev_reason = self.locate(llm, transcript, rendered, family, expected)
            except Exception as e:
                log.warning("%s: evidence call for %s failed: %s", self.name, family.id, e)
                fs.detail["evidence_error"] = f"{type(e).__name__}: {e}"
            else:
                fs.segment_ids = seg_ids
                why = reason or ev_reason or fs.reason
                findings = self.evidence_findings(transcript, family, seg_ids, fs.score, lambda run: why,
                                                  {"expected": fs.detail["expected"]})
        return fs, findings
