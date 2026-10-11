"""Learned fusion: one L2 logistic regression over (call, family) rows (v2_plan §3 "Learned fusion").

Features per family: the weighted fusion's family score and uncertainty, every check's raw score and a
"check gave no score" indicator, standardized on the training calls. Output: P(alarm of this family);
the call probability ``q`` is the max over the families that may alarm. Label: ``q >= threshold`` ->
alarm, ``q`` in ``[threshold - review_band, threshold)`` -> review, else no_alert; the officer slider moves
``threshold`` as in the weighted fusion. Review-labelled calls are soft targets (``review_target``, 0.5),
so "between" calls land near the cut, where the review band catches them.

Fitted with ``callguard fit-fusion --kind learned`` on dev results only; evaluate with
``callguard fusion-cv`` (nested CV). With ~48 dev calls and ~10 coefficients the L2 penalty does most
of the work: expect it to behave like a re-weighted mean, and do not read single coefficients as truths.
Math: :mod:`callguard.fusion.fit`.
"""

from __future__ import annotations

from callguard.fusion import fit as F
from callguard.fusion.fitted import FittedFusion


class LearnedFusion(FittedFusion):
    kind = "learned"
    name_de = "gelernte"

    def _detail_reasons(self, v: F.Verdict, feats: F.CallFeatures) -> list[str]:
        if not v.top or not self.model:
            return []
        contrib = F.learned_contributions(self.model, feats, v.top)
        top3 = sorted(contrib.items(), key=lambda x: -abs(x[1]))[:3]
        return ["Stärkste Beiträge (Log-Odds): " + ", ".join(f"{n} {c:+.2f}" for n, c in top3) + "."]
