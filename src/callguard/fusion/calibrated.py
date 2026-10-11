"""Calibrated fusion with conformal abstention (A5, docs/design/v2_plan.md §7).

Per (check, family) Platt scaling turns raw check scores into P(alarm of this family); per family they
are pooled in log-odds (check weights) and re-calibrated once; the call probability ``q`` is the max over
the families that may alarm. Fitted with ``callguard fit-fusion --kind calibrated`` on dev results only
(math and fitting: :mod:`callguard.fusion.fit`). A calibrated keyword score of 0 carries exactly the
evidence it had on dev, so N14's "absent keyword drags the alarm down" is learned rather than hand-set.

Label = two layers:

1. **Officer threshold** on ``q``: ``q >= threshold`` -> alarm, ``q`` in ``[threshold - review_band,
   threshold)`` -> review, else no_alert. The UI slider / ``overrides["threshold"]`` moves this alarm cut
   exactly as in the weighted fusion (but on a probability: 0.5 = "as likely an alarm as not" on dev).
2. **Conformal set** (split-conformal, LAC score ``1 - p(label)``; quantile at level ``1 - alpha`` of
   out-of-fold scores stored in the model; over the 3 labels from a small softmax on ``logit(q)``, or with
   ``fit-fusion --labels 2`` over alarm / no_alert with p(alarm) = q, which makes the review region the
   interval of q where both labels stay plausible): if the set
   holds not exactly one label - or exactly {review} - the call becomes review with the reason
   "Prüfen (unsicher: {alarm, no_alert} beide plausibel)". The set can only add reviews; it never creates
   an alarm and never removes one the threshold did not give. ``alpha`` can be changed in the config
   without refitting (the scores are stored).

Coverage caveat: the guarantee "the true label is in the set with probability >= 1 - alpha" assumes
exchangeable calls; clean/noisy recordings of one dialogue and twin dialogues are not independent, and
with ~36 calibration calls the realised coverage is noisy. Read it as a principled abstention rule, not as
a certificate.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from callguard.fusion import fit as F
from callguard.fusion.fitted import FittedFusion
from callguard.fusion.weighted import _num

if TYPE_CHECKING:
    from callguard.context import Context


class CalibratedFusion(FittedFusion):
    kind = "calibrated"
    name_de = "kalibrierte"

    def __init__(self, ctx: "Context", *, alpha: float | None = None, **kw: Any):
        super().__init__(ctx, **kw)
        if alpha is not None:
            self.params["alpha"] = alpha
        self.alpha = alpha  # None = the model's alpha

    def _alpha(self, o: dict[str, Any]) -> float:
        a = _num(o.get("alpha"))
        if a is None:
            a = self.alpha
        if a is None:
            a = float(((self.model or {}).get("conformal") or {}).get("alpha", 0.1))
        return float(a)

    def _verdict(self, feats: F.CallFeatures, t: float, band: float, o: dict[str, Any]) -> F.Verdict:
        return F.fitted_verdict(self.model or {}, feats, t, band, self._alpha(o))

    def _label_reasons(self, v: F.Verdict, t: float, band: float, top_name: str) -> list[str]:
        if v.why != "conformal":
            out = super()._label_reasons(v, t, band, top_name)
            out.append(f"Vorhersagemenge {{{', '.join(v.pset or [])}}} (Konformitätsniveau "
                       f"{1 - self._alpha({}):.0%}).")
            return out
        pset = v.pset or []
        if not pset:
            what = "kein Label plausibel"
        elif pset == ["review"]:
            what = "{review} allein plausibel"
        else:
            what = f"{{{', '.join(pset)}}} {'beide' if len(pset) == 2 else 'alle'} plausibel"
        cp = v.class_probs or {}
        return [f"Prüfen (unsicher: {what}): kalibrierte Wahrscheinlichkeit {v.score:.2f} für '{top_name}' "
                f"(Schwelle {t:.2f}); Klassen alarm {cp.get('alarm', 0):.2f} / review {cp.get('review', 0):.2f} / "
                f"no_alert {cp.get('no_alert', 0):.2f}, Konformitätsniveau {1 - self._alpha({}):.0%}."]

    def _detail_reasons(self, v: F.Verdict, feats: F.CallFeatures) -> list[str]:
        if not v.top:
            return []
        probs = F.cal_check_probs(self.model or {}, feats, v.top)
        if not probs:
            return []
        return ["Kalibriert je Prüfung: " + ", ".join(f"{c} {p:.2f}" for c, p in
                                                      sorted(probs.items(), key=lambda x: -x[1])) + "."]
