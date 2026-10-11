"""Hybrid fusion: a core check decides, second-opinion checks may only escalate to review.

Measured (research/findings/RQ5.md): the `facts` check (fact questions + policy table) separates misconduct from
harmless calls much better than the free LLM judge, but misses open cases (review). The free judge, on the other
hand, raises many false alarms but often says "undetermined" exactly where a decisive fact is open. This fusion
keeps the weighted fusion over the ``core`` checks (default: facts) and lets ``second_opinion`` checks turn a
no_alert into review (never into an alarm):

- ``escalate_on_undetermined``: a second-opinion check's majority verdict for a family is "undetermined"
  (llm_judge self-consistency votes), and the core did not clear that family with an exculpatory fact.
- ``escalate_min_score``: a second-opinion family score at or above this (default 1.01 = off).

Escalated calls get the score ``max(score, threshold - review_band / 2)`` so the call ranking agrees with the
label; the officer threshold keeps its meaning (alarm cut on the core score).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from callguard.fusion.weighted import WeightedFusion
from callguard.types import CheckResult, Decision, Family, Transcript

if TYPE_CHECKING:
    from callguard.context import Context


def _majority_verdict(fs: Any) -> str | None:
    detail = getattr(fs, "detail", None) or {}
    votes = detail.get("votes") if isinstance(detail, dict) else None
    if isinstance(votes, dict) and votes:
        return max(votes.items(), key=lambda kv: kv[1])[0]
    return getattr(fs, "verdict", None)


class HybridFusion(WeightedFusion):
    def __init__(self, ctx: "Context", *, core: list[str] | tuple[str, ...] = ("facts",),
                 second_opinion: list[str] | tuple[str, ...] = ("llm_judge",),
                 escalate_on_undetermined: bool = True, escalate_min_score: float = 1.01, **kw: Any):
        super().__init__(ctx, **kw)
        self.params.update(core=list(core), second_opinion=list(second_opinion),
                           escalate_on_undetermined=bool(escalate_on_undetermined),
                           escalate_min_score=float(escalate_min_score))
        self.core = list(core)
        self.second_opinion = list(second_opinion)
        self.escalate_on_undetermined = bool(escalate_on_undetermined)
        self.escalate_min_score = float(escalate_min_score)

    def decide(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
               overrides: dict[str, Any] | None = None,
               views: dict[str, Transcript] | None = None) -> Decision:
        o = dict(overrides or {})
        core_present = [n for n in self.core if n in results]
        weights = {n: (1.0 if n in core_present else 0.0) for n in results}
        if core_present:  # only the core decides; without a core result fall back to the configured weights
            o["weights"] = {**(o.get("weights") or {}), **weights}
        d = super().decide(transcript, results, families, o, views)
        if d.label != "no_alert":
            return d
        t = float(o.get("threshold", self.threshold))
        band = float(o.get("review_band", self.review_band))
        enabled = {f.id for f in families if f.enabled}
        reasons = []
        for name in self.second_opinion:
            r = results.get(name)
            if r is None or r.meta.get("error"):
                continue
            for fam, fs in (r.family_scores or {}).items():
                if fam not in enabled:
                    continue
                why = None
                if self.escalate_on_undetermined and _majority_verdict(fs) == "undetermined":
                    why = "offen (undetermined)"
                elif fs.score is not None and fs.score >= self.escalate_min_score:
                    why = f"Score {fs.score:.2f}"
                if why:
                    label = next((f.label for f in families if f.id == fam), fam)
                    reasons.append(f"Zweitmeinung {name} zu «{label}»: {why} – bitte prüfen.")
        if not reasons:
            return d
        d.label = "review"
        d.score = max(d.score, round(t - band / 2, 4))
        d.reasons = reasons + list(d.reasons)
        return d
