""""No silent clearance" fusion (research S3, simplified): weighted fusion + one escalation rule.

A call must not end as no_alert while there is positive evidence of the act that no fact explained away. After
the weighted fusion, a no_alert call goes to review when, for an enabled family that may alarm,

- the ``facts`` check's act fact(s) have p(yes) >= ``act_min`` (default 0.3), or a rule check of type
  ``keywords`` has a non-negated, non-harmless hit of that family (``use_keywords``), and
- no exculpatory fact of that family is "yes" in the facts check.

Pure re-fusion: it only reads the stored CheckResults (facts detail ``facts.<id>.role/p/value``, keyword
findings' ``negated`` / ``harmless``), no LLM calls. Escalated calls get the score
``max(score, threshold - review_band / 2)`` (as fusion/hybrid.py) so the ranking agrees with the label.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from callguard.fusion.weighted import WeightedFusion
from callguard.types import CheckResult, Decision, Family, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

REASON = "Handlung möglich, aber nicht entkräftet – bitte prüfen"


class NoSilentFusion(WeightedFusion):
    def __init__(self, ctx: "Context", *, act_min: float = 0.3, use_keywords: bool = True,
                 facts_checks: list[str] | tuple[str, ...] = ("facts",),
                 keyword_checks: list[str] | tuple[str, ...] = ("keywords",), **kw: Any):
        super().__init__(ctx, **kw)
        self.params.update(act_min=float(act_min), use_keywords=bool(use_keywords),
                           facts_checks=list(facts_checks), keyword_checks=list(keyword_checks))
        self.act_min = float(act_min)
        self.use_keywords = bool(use_keywords)
        self.facts_checks = frozenset(facts_checks)  # check types or instance names
        self.keyword_checks = frozenset(keyword_checks)

    @staticmethod
    def _of(results: dict[str, CheckResult], kinds: frozenset[str]) -> list[CheckResult]:
        return [r for n, r in results.items() if (n in kinds or r.type in kinds) and not r.meta.get("error")]

    def _triggers(self, results: dict[str, CheckResult], families: list[Family]) -> list[str]:
        facts_rs = self._of(results, self.facts_checks)
        kw_rs = self._of(results, self.keyword_checks) if self.use_keywords else []
        reasons = []
        for f in families:
            if not (f.enabled and f.can_alarm):
                continue
            facts: dict[str, dict[str, Any]] = {}
            for r in facts_rs:
                fs = r.family_scores.get(f.id)
                facts.update(((fs.detail or {}).get("facts") or {}) if fs is not None else {})
            if any(d.get("role") == "exculpatory" and d.get("value") == "yes" for d in facts.values()):
                continue
            why = []
            acts = [(d.get("label") or fid, float((d.get("p") or {}).get("yes", 0.0)))
                    for fid, d in facts.items() if d.get("role") == "act"]
            hit = [(lab, p) for lab, p in acts if p >= self.act_min]
            if hit:
                lab, p = max(hit, key=lambda x: x[1])
                why.append(f"Fakt «{lab}» p(ja) = {p:.2f}")
            kws = sorted({str(x.detail.get("keyword_id") or x.reason) for r in kw_rs for x in r.findings
                          if x.family == f.id and (x.score or 0) > 0
                          and not x.detail.get("negated") and not x.detail.get("harmless")})
            if kws:
                why.append(f"Stichwort {', '.join(kws[:3])}")
            if why:
                reasons.append(f"«{f.label}»: {REASON} ({'; '.join(why)}; keine entlastende Tatsache).")
        return reasons

    def decide(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
               overrides: dict[str, Any] | None = None,
               views: dict[str, Transcript] | None = None) -> Decision:
        d = super().decide(transcript, results, families, overrides, views)
        if d.label != "no_alert":
            return d
        reasons = self._triggers(results, families)
        if not reasons:
            return d
        o = overrides or {}
        t = float(o.get("threshold", self.threshold))
        band = float(o.get("review_band", self.review_band))
        d.label = "review"
        d.score = max(d.score, round(t - band / 2, 4))
        d.reasons = reasons + list(d.reasons)
        return d
