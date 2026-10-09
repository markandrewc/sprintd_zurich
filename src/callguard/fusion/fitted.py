"""Shared base of the fusions that apply a fitted model (``calibrated``, ``learned``).

Config::

    fusion:
      type: calibrated            # or learned
      model: runs/fusion/fusion-base-calibrated.json   # written by `callguard fit-fusion`
      threshold: 0.5              # on the call probability q (the officer slider moves it)
      review_band: 0.15           # q in [threshold - band, threshold) -> review
      alpha: 0.1                  # calibrated only: conformal miscoverage

What the fusion does per call: the weighted fusion with the parameters stored in the model (``base``)
computes the per-family features exactly as at fitting time; the model turns them into one probability
per family; the call probability ``q`` is the highest one among the families that may alarm. Passages and
family reasons are the weighted fusion's, ranked by the fitted family probabilities.

Not used by the fitted fusions: per-check weight sliders (the model was fitted with the weights stored in
it; a weight of 0 or ``disabled_checks`` still removes a check, which the model then sees as "no score"),
``max_uncertainty`` / ``min_score_for_review`` / the "undetermined" escalation of the weighted fusion.

No model file (or an unreadable one): the call is decided by the weighted fusion with this block's
parameters, a warning is logged and the reasons say so. A model applied to a call whose dialogue it was
fitted on logs a warning (in-sample = optimistic numbers; use ``callguard fusion-cv`` to evaluate).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from callguard.fusion import fit as F
from callguard.fusion.weighted import WeightedFusion, _num, short_label, view_text
from callguard.types import CheckResult, Decision, Family, FusedFamily, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard")


class FittedFusion(WeightedFusion):
    kind = ""
    name_de = "angepasst"

    def __init__(self, ctx: "Context", *, model: str | dict[str, Any] | None = None, threshold: float = 0.5,
                 review_band: float = 0.15, **kw: Any):
        super().__init__(ctx, threshold=threshold, review_band=review_band, **kw)
        self.model_ref = model if isinstance(model, str) else ("<in-memory>" if model else None)
        self.params["model"] = self.model_ref
        self.model: dict[str, Any] | None = None
        self.model_error: str | None = None
        try:
            if model is None:
                raise FileNotFoundError("no model configured (fusion.model)")
            m = dict(model) if isinstance(model, dict) else F.load_model(model)
            if m.get("kind") != self.kind:
                raise ValueError(f"model kind is {m.get('kind')!r}, this fusion needs {self.kind!r}")
            self.model = m
        except Exception as e:  # never break a call over a missing model: fall back, loudly
            self.model_error = f"{type(e).__name__}: {e}"
            log.warning("%s fusion: %s; falling back to the weighted fusion. Fit one with "
                        "`callguard fit-fusion --kind %s --experiment <name> --variant <v>`.",
                        self.kind, self.model_error, self.kind)
        self._base = WeightedFusion(ctx, **(self.model or {}).get("base", {})) if self.model else None
        self._train = set((self.model or {}).get("train_dialogues") or ())
        self._warned_in_sample = False

    # -- per kind -----------------------------------------------------------------------------------

    def _verdict(self, feats: F.CallFeatures, t: float, band: float, o: dict[str, Any]) -> F.Verdict:
        return F.fitted_verdict(self.model or {}, feats, t, band)

    def _label_reasons(self, v: F.Verdict, t: float, band: float, top_name: str) -> list[str]:
        if v.label == "alarm":
            return [f"Alarm: {self.name_de} Wahrscheinlichkeit {v.score:.2f} für '{top_name}' >= Schwelle {t:.2f}."]
        if v.why == "band":
            return [f"Prüfen (knapp unter Schwelle): {self.name_de} Wahrscheinlichkeit {v.score:.2f} für "
                    f"'{top_name}' liegt zwischen {F._band_floor(t, band):.2f} und der Schwelle {t:.2f}."]
        return [f"Kein Alarm: höchste {self.name_de} Wahrscheinlichkeit {v.score:.2f} ('{top_name}') liegt unter "
                f"{F._band_floor(t, band):.2f} (Schwelle {t:.2f} minus Band {band:.2f})."]

    def _detail_reasons(self, v: F.Verdict, feats: F.CallFeatures) -> list[str]:
        return []

    # -- decide -------------------------------------------------------------------------------------

    def decide(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
               overrides: dict[str, Any] | None = None,
               views: dict[str, Transcript] | None = None) -> Decision:
        if self.model is None or self._base is None:
            d = super().decide(transcript, results, families, overrides, views)
            d.reasons.append(f"Hinweis: kein angepasstes Fusionsmodell ({self.kind}: {self.model_error}); "
                             f"entschieden mit der gewichteten Fusion.")
            return d
        o = overrides or {}

        def knob(name: str) -> float:
            x = _num(o.get(name))
            return x if x is not None else float(getattr(self, name))

        t, band = knob("threshold"), knob("review_band")
        merge_gap, max_len = knob("merge_gap"), knob("max_passage_seconds")
        max_passages = int(o.get("max_passages", self.max_passages))
        weights = {**{c: 1.0 for c in results}, **(self.model.get("weights") or {})}
        disabled = set(o.get("disabled_checks") or ()) | {
            n for n, w in (o.get("weights") or {}).items() if _num(w) is not None and _num(w) <= 0}
        if self._train and not self._warned_in_sample and \
                F.dialogue_of(transcript.call_id or "") in self._train:
            self._warned_in_sample = True
            log.warning("%s fusion: call %s belongs to a dialogue the model was fitted on (in-sample, "
                        "optimistic); evaluate fitted fusions with `callguard fusion-cv`.",
                        self.kind, transcript.call_id)

        base = self._base.decide(transcript, results, families,
                                 {"weights": weights, "disabled_checks": sorted(disabled)})
        usable = F.usable_checks(results, weights, disabled)
        failed = {n: str(r.meta.get("error")) for n, r in results.items()
                  if n not in disabled and r.meta.get("error")}
        feats = F.call_features(transcript.call_id, results, families, base, usable)
        v = self._verdict(feats, t, band, o)

        fams = [f for f in families if f.enabled]
        fam_by_id = {f.id: f for f in fams}
        fused: dict[str, FusedFamily] = {}
        for fid, ff in base.families.items():
            fused[fid] = ff.model_copy(update={"score": round(v.probs[fid], 4)}) if fid in v.probs else ff
        top_name = short_label(fam_by_id[v.top].label) if v.top in fam_by_id else "-"

        if not usable:
            label, reasons = "review", ["Prüfen (unsicher): Keine Prüfung lieferte ein verwertbares Ergebnis; "
                                        "ein Mensch muss den Anruf beurteilen."]
        else:
            label = v.label
            reasons = self._label_reasons(v, t, band, top_name)
            reasons += self._detail_reasons(v, feats)
            if v.top and fused[v.top].reason and (label != "no_alert" or v.score > 0):
                reasons.append(f"{top_name}: {fused[v.top].reason}")
        for name, err in failed.items():
            reasons.append(f"Hinweis: Prüfung '{name}' ist ausgefallen und fehlt in der Bewertung ({err[:120]}).")
        if disabled & set(results):
            reasons.append(f"Deaktivierte Prüfungen: {', '.join(sorted(disabled & set(results)))}.")

        floor = F._band_floor(t, band)
        passages = self._passages(transcript, usable, fused, fam_by_id, floor, merge_gap, max_len,
                                  views)[:max(0, max_passages)]
        if views:
            for p in passages:
                p.texts = {name: view_text(tv, p.start, p.end) for name, tv in views.items()}
        return Decision(label=label, score=round(v.score, 4), uncertainty=v.uncertainty, threshold=t,
                        families=fused, passages=passages, reasons=reasons,
                        top_family=v.top if v.score > 0 else None)
