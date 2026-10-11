"""The learning step that works now: re-fit the decision threshold from officer labels, honestly.

* Labels: per call the officer's label (:mod:`callguard.learning.records`); holdout calls are dropped
  (hygiene), nothing else is (calibration is tuning, which the protocol allows on dev folds).
* Proposed threshold: :func:`callguard.eval.suggest_threshold` on all usable labelled calls (only the
  fusion re-runs on the stored check results; no ASR, no LLM).
* Its expected effect is **not** read off the same calls: a dialogue-fold cross-validation
  (:func:`callguard.eval.cross_validate`, folds from :func:`callguard.learning.hygiene.cv_fold_of`: the dev
  folds of config/splits.yaml, twin units together) picks the threshold on the other folds and decides
  the held-out fold with it. Those out-of-fold decisions are compared with the current threshold on the
  same calls by a paired bootstrap over twin units (:func:`callguard.stats.paired_bootstrap`).
* ``keep``: the current threshold is tied with the best one on the labelled calls (nothing to change).
* Verdict: ``better`` only if the flag-F1 CI excludes 0 upward **and** the false-alarm rate does not
  rise (CI upper bound <= 0 or no point increase); ``worse`` if a CI excludes 0 the wrong way; else
  ``no_difference`` (the usual outcome with tens of calls: say so).

Per-family thresholds are reported as readiness only (labels per family vs the ~30 needed).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any

from callguard import eval as ev
from callguard import stats
from callguard.learning import hygiene as hy
from callguard.splits import Splits
from callguard.types import CallResult

if TYPE_CHECKING:
    from callguard.pipeline import Pipeline

MIN_CALLS = 10
EFFECT_METRICS = ("flag_f1", "false_alarm_rate", "miss_rate", "accuracy")
METRIC_DE = {"flag_f1": "F1 (Markierungen)", "false_alarm_rate": "Fehlalarmquote", "miss_rate": "Verpasst-Quote",
             "accuracy": "Genauigkeit (3 Klassen)"}


def usable(labels: Mapping[str, str], splits: Splits | None, results: Mapping[str, CallResult]) -> dict[str, str]:
    """Labels of calls that may tune the threshold (no holdout) and have a stored result."""
    return {cid: lab for cid, lab in labels.items()
            if cid in results and hy.use_of(cid, splits) in hy.CALIBRATION}


def _rows_at(pipeline: "Pipeline", results: Sequence[CallResult], labels: Mapping[str, str], t: float,
             overrides: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    families = pipeline.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    rows = []
    for r in results:
        d = pipeline.decide(r.transcript, r.checks, {**(overrides or {}), "threshold": t}, families)
        rows.append(ev.make_row(r.model_copy(update={"decision": d}), labels.get(r.call_id), can_alarm))
    return rows


def verdict_of(effect: Mapping[str, Mapping[str, Any]]) -> str:
    f1, far = effect.get("flag_f1") or {}, effect.get("false_alarm_rate") or {}
    if (f1.get("real") and (f1.get("diff") or 0) < 0) or (far.get("real") and (far.get("diff") or 0) > 0):
        return "worse"
    far_ok = (far.get("hi") is not None and far["hi"] <= 0) or (far.get("diff") or 0) <= 0
    if f1.get("real") and (f1.get("diff") or 0) > 0 and far_ok:
        return "better"
    return "no_difference"


VERDICT_DE = {
    "better": "Messbar besser: das Konfidenzintervall der F1-Differenz schliesst 0 aus, keine zusätzlichen Fehlalarme.",
    "worse": "Messbar schlechter als die aktuelle Schwelle: nicht übernehmen.",
    "no_difference": "Kein messbarer Unterschied (Konfidenzintervall enthält 0). Übernehmen nur, wenn es fachlich "
                     "begründet ist; mehr Rückmeldungen machen die Schätzung genauer.",
    "too_few": "Zu wenige bewertete Anrufe für einen Vorschlag.",
    "keep": "Die aktuelle Schwelle ist auf den bewerteten Anrufen bereits unter den besten (gleichauf): "
            "nichts zu ändern. Die Kreuzvalidierung zeigt, was eine neu gewählte Schwelle bewirkt hätte.",
}


def propose_threshold(pipeline: "Pipeline", results: Sequence[CallResult], labels: Mapping[str, str],
                      splits: Splits | None, *, overrides: Mapping[str, Any] | None = None,
                      thresholds: Sequence[float] | None = None, n_folds: int = 4, n_boot: int = 2000,
                      seed: int = 13, max_false_alarm_rate: float | None = None) -> dict[str, Any]:
    by_id = {r.call_id: r for r in results}
    lab = usable(labels, splits, by_id)
    dropped = sorted(set(labels) - set(lab))
    calls = [by_id[c] for c in sorted(lab)]
    current = float((overrides or {}).get("threshold", pipeline.cfg.fusion.get("threshold", 0.55)))
    out: dict[str, Any] = {"n_labels": len(labels), "n_calls": len(calls), "dropped": dropped,
                           "n_dialogues": len({hy.unit_of(c.call_id, None) for c in calls}),
                           "n_units": len({hy.unit_of(c.call_id, splits) for c in calls}),
                           "current_threshold": current, "proposed_threshold": None, "fit": None, "cv": None,
                           "effect": {}, "verdict": "too_few", "label_counts": {}, "keep_current": False}
    out["label_counts"] = {k: sum(1 for c in calls if lab[c.call_id] == k) for k in ("alarm", "review", "no_alert")}
    if len(calls) < MIN_CALLS:
        out["message"] = f"{len(calls)} nutzbare bewertete Anrufe; mindestens {MIN_CALLS} nötig."
        return out
    grid = sorted({*(thresholds or ev.DEFAULT_THRESHOLDS), round(current, 4)})
    swept = ev.sweep(pipeline, calls, lab, grid, dict(overrides or {}))
    pick = ev.suggest_threshold(swept, max_false_alarm_rate)
    if pick is None:
        out["message"] = "Kein Vorschlag möglich (keine bewerteten Anrufe im Sweep)."
        return out
    out["fit"] = pick
    out["keep_current"] = any(abs(t - current) < 1e-9 for t in pick.get("tied") or [])
    # the current threshold is among the best: nothing to change (decisions would be identical)
    out["proposed_threshold"] = current if out["keep_current"] else pick["threshold"]
    fold_of = hy.cv_fold_of([c.call_id for c in calls], splits, n_folds)
    cv = ev.cross_validate(pipeline, calls, lab, thresholds=grid, overrides=dict(overrides or {}), fold_of=fold_of)
    if cv is None:
        out["message"] = "Weniger als zwei Folds mit bewerteten Anrufen: keine Kreuzvalidierung möglich."
        out["verdict"] = "too_few"
        return out
    out["cv"] = {"n_folds": cv["n_folds"], "folds": cv["folds"]}
    base_rows = _rows_at(pipeline, calls, lab, current, overrides)
    eff = stats.paired_bootstrap(base_rows, cv["rows"], n_boot=n_boot, seed=seed, metrics=EFFECT_METRICS)
    out["n_bootstrap_units"] = (eff.get("_n") or {}).get("units")
    out["effect"] = {k: v for k, v in eff.items() if k in EFFECT_METRICS}
    out["verdict"] = "keep" if out["keep_current"] else verdict_of(out["effect"])
    out["current_counts"] = _counts(base_rows)
    out["cv_counts"] = _counts(cv["rows"])
    return out


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    m = ev.metrics(rows)
    f = m["flag"]
    return {"fp": f["fp"], "fn": f["fn"], "tp": f["tp"], "tn": f["tn"], "alarms": m["workload"]["alarms"],
            "reviews": m["workload"]["reviews"]}


def family_readiness(call_labels: Mapping[str, Any], need: int = 30) -> list[dict[str, Any]]:
    """Per family: labelled calls that concern it (officer named it, or the system's top family)."""
    per: dict[str, int] = {}
    for c in call_labels.values():
        for fid in {*(c.families or []), *([c.system_family] if c.system_family else [])}:
            per[fid] = per.get(fid, 0) + 1
    return [{"family": f, "labels": n, "need": need, "ready": n >= need} for f, n in sorted(per.items())]
