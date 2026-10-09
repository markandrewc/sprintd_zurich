"""Detection quality on the case's test calls: false alarms, misses, and a better threshold.

Two views, because "review" is neither a hit nor a miss by itself:

* **flag** (the case's headline metric): positive = alarm or review, i.e. a human listens to the call.
  ``false_alarm_rate`` = harmless calls flagged / harmless calls, ``miss_rate`` = flaggable calls
  passed as no_alert / flaggable calls.
* **alarm** (strict): alarm vs. everything else.

``cross_validate`` gives the honest number: the threshold of each dialogue-level fold is chosen on the
other folds only (clean and noisy recordings of one dialogue always share a fold).

``sweep`` re-runs only the fusion on cached check results, so trying 15 thresholds over 60 calls takes
milliseconds; ``suggest_threshold`` is the "system suggests a better threshold" feature. Ground truth
is read here only, never fed into the pipeline.
"""

from __future__ import annotations

import json
import logging
import statistics
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.data import Call, dialogue_of, split_dialogues
from callguard.fusion import top_family
from callguard.types import LABELS, CallResult

if TYPE_CHECKING:
    from callguard.pipeline import Pipeline

log = logging.getLogger("callguard")

Row = dict[str, Any]
Truth = Sequence[Call] | Mapping[str, str]  # dataset calls, or {call_id: label} from officer feedback
FLAG = ("alarm", "review")
DEFAULT_THRESHOLDS = [round(0.20 + 0.05 * i, 2) for i in range(15)]  # 0.20 .. 0.90


# --------------------------------------------------------------------------------------------
# Rows
# --------------------------------------------------------------------------------------------


def _truth_index(truth: Truth) -> dict[str, Call | str]:
    if isinstance(truth, Mapping):
        return dict(truth)
    return {c.call_id: c for c in truth}


def _base_row(call_id: str, gt: Call | str | None) -> Row:
    if isinstance(gt, Call):
        exp = gt.expected
        return {"call_id": call_id, "dialogue_id": gt.dialogue_id, "level": gt.level, "noisy": gt.noisy,
                "expected": exp.label if exp else None, "expected_family": exp.family if exp else None}
    return {"call_id": call_id, "dialogue_id": dialogue_of(call_id), "level": None, "noisy": None,
            "expected": gt, "expected_family": None}


def failed_checks(result: CallResult) -> list[str]:
    """Checks that failed entirely or for some families. The fusion decides without them, so a run with
    the LLM server down must not read like an LLM measurement."""
    return sorted(n for n, c in result.checks.items() if c.meta.get("error") or c.meta.get("errors"))


def make_row(result: CallResult, gt: Call | str | None, can_alarm: set[str] | None = None) -> Row:
    d = result.decision
    return {**_base_row(result.call_id, gt), "predicted": d.label, "score": round(d.score, 4),
            "uncertainty": round(d.uncertainty, 4), "top_family": top_family(d, can_alarm), "error": None,
            "failed_checks": failed_checks(result)}


def error_row(call_id: str, gt: Call | str | None, error: str) -> Row:
    """A call the pipeline could not assess. Counted as ``review``: operationally a human must look."""
    return {**_base_row(call_id, gt), "predicted": "review", "score": None, "uncertainty": None,
            "top_family": None, "error": error, "failed_checks": []}


def make_rows(results: Sequence[CallResult], truth: Truth, can_alarm: set[str] | None = None) -> list[Row]:
    idx = _truth_index(truth)
    return [make_row(r, idx.get(r.call_id), can_alarm) for r in results]


# --------------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------------


def _div(a: float, b: float) -> float | None:
    return round(a / b, 4) if b else None


def _binary(rows: list[Row], positive: tuple[str, ...]) -> dict[str, Any]:
    tp = sum(1 for r in rows if r["expected"] in positive and r["predicted"] in positive)
    fp = sum(1 for r in rows if r["expected"] not in positive and r["predicted"] in positive)
    fn = sum(1 for r in rows if r["expected"] in positive and r["predicted"] not in positive)
    tn = len(rows) - tp - fp - fn
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "precision": _div(tp, tp + fp), "recall": _div(tp, tp + fn),
            "f1": _div(2 * tp, 2 * tp + fp + fn), "false_alarm_rate": _div(fp, fp + tn),
            "miss_rate": _div(fn, tp + fn)}


def _summary(rows: list[Row]) -> dict[str, Any]:
    flag, alarm = _binary(rows, FLAG), _binary(rows, ("alarm",))
    return {"n": len(rows), "accuracy": _div(sum(r["expected"] == r["predicted"] for r in rows), len(rows)),
            "flag_precision": flag["precision"], "flag_recall": flag["recall"], "flag_f1": flag["f1"],
            "false_alarm_rate": flag["false_alarm_rate"], "miss_rate": flag["miss_rate"],
            "alarm_f1": alarm["f1"]}


def metrics(rows: list[Row]) -> dict[str, Any]:
    labeled = [r for r in rows if r.get("expected") in LABELS and r.get("predicted") in LABELS]
    n = len(labeled)
    confusion = {e: {p: sum(1 for r in labeled if r["expected"] == e and r["predicted"] == p) for p in LABELS}
                 for e in LABELS}
    exp_review = [r for r in labeled if r["expected"] == "review"]
    exp_alarm = [r for r in labeled if r["expected"] == "alarm" and r.get("expected_family")]
    hits = sum(1 for r in exp_alarm if r.get("top_family") == r["expected_family"])

    by_level = {str(lv): _summary([r for r in labeled if r.get("level") == lv])
                for lv in sorted({r["level"] for r in labeled if r.get("level") is not None})}
    by_noise = {name: _summary(sub) for name, sub in
                (("clean", [r for r in labeled if r.get("noisy") is False]),
                 ("noisy", [r for r in labeled if r.get("noisy") is True])) if sub}

    def mean_score(label: str) -> float | None:
        s = [r["score"] for r in labeled if r["expected"] == label and r.get("score") is not None]
        return round(statistics.fmean(s), 4) if s else None

    failed_by_check: dict[str, int] = {}
    for r in rows:
        for name in r.get("failed_checks") or ():
            failed_by_check[name] = failed_by_check.get(name, 0) + 1

    return {
        "n": n,
        "unlabeled": len(rows) - n,
        "errors": sum(1 for r in rows if r.get("error")),
        "check_failures": {"calls": sum(1 for r in rows if r.get("failed_checks")), "by_check": failed_by_check},
        "accuracy": _div(sum(confusion[label][label] for label in LABELS), n),
        "confusion": confusion,
        "flag": _binary(labeled, FLAG),
        "alarm": _binary(labeled, ("alarm",)),
        "review_handling": {
            "n": len(exp_review),
            "escalated": sum(1 for r in exp_review if r["predicted"] in FLAG),
            "as_review": sum(1 for r in exp_review if r["predicted"] == "review"),
            "escalation_rate": _div(sum(1 for r in exp_review if r["predicted"] in FLAG), len(exp_review)),
        },
        "workload": {
            "alarms": sum(1 for r in labeled if r["predicted"] == "alarm"),
            "reviews": sum(1 for r in labeled if r["predicted"] == "review"),
            "flag_rate": _div(sum(1 for r in labeled if r["predicted"] in FLAG), n),
        },
        "by_level": by_level,
        "by_noise": by_noise,
        "family_hit": {"n": len(exp_alarm), "hits": hits, "rate": _div(hits, len(exp_alarm))},
        "mean_score": {label: mean_score(label) for label in LABELS},
    }


# --------------------------------------------------------------------------------------------
# Threshold sweep (fusion only, on cached check results)
# --------------------------------------------------------------------------------------------


def sweep(pipeline: "Pipeline", results: Sequence[CallResult], calls: Truth,
          thresholds: Sequence[float] | None = None, overrides: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Metrics per threshold. Only ``pipeline.decide`` runs, so this is cheap enough for a UI slider."""
    families = pipeline.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    idx = _truth_index(calls)
    out = []
    for t in thresholds if thresholds is not None else DEFAULT_THRESHOLDS:
        rows = []
        for r in results:
            d = pipeline.decide(r.transcript, r.checks, {**(overrides or {}), "threshold": t}, families)
            rows.append(make_row(r.model_copy(update={"decision": d}), idx.get(r.call_id), can_alarm))
        out.append({"threshold": round(float(t), 4), "metrics": metrics(rows)})
    return out


def suggest_threshold(swept: list[dict[str, Any]], max_false_alarm_rate: float | None = None) -> dict[str, Any] | None:
    """Best flag-F1; ties -> higher recall (a missed case costs more than a review), then fewer false
    alarms, then the strict alarm-F1 and accuracy (right label, not just flagged). Among thresholds
    that are still tied, take the middle one: the widest safety margin on both sides.

    Thresholds that flag every call (or none) are skipped while any other exists: "listen to all
    calls" can have a decent F1 when half the test set is positive, but it is not a threshold.
    ``max_false_alarm_rate`` lets the officer cap false alarms (best effort: ignored if unreachable).
    """
    def key(s: dict[str, Any]) -> tuple[float, ...]:
        m = s["metrics"]
        f, a = m["flag"], m.get("alarm", {})
        return (f["f1"] or 0.0, f["recall"] or 0.0, -(f["false_alarm_rate"] or 0.0), a.get("f1") or 0.0,
                m.get("accuracy") or 0.0)

    def degenerate(s: dict[str, Any]) -> bool:
        return s["metrics"].get("workload", {}).get("flag_rate") in (0.0, 1.0)

    def within_cap(s: dict[str, Any]) -> bool:
        far = s["metrics"]["flag"]["false_alarm_rate"]
        return max_false_alarm_rate is None or far is None or far <= max_false_alarm_rate

    scored = [s for s in swept if s["metrics"]["n"]]
    if not scored:
        return None
    pool = [s for s in scored if not degenerate(s)] or scored
    pool = [s for s in pool if within_cap(s)] or pool
    best = max(key(s) for s in pool)
    tied = sorted((s for s in pool if key(s) == best), key=lambda s: s["threshold"])
    pick = tied[len(tied) // 2]
    f = pick["metrics"]["flag"]
    reason = (f"Schwelle {pick['threshold']:.2f} maximiert F1 der Markierungen ({_pct(f['f1'])}) bei "
              f"Recall {_pct(f['recall'])} und Fehlalarmquote {_pct(f['false_alarm_rate'])}.")
    if len(pool) < len(scored):
        reason += " Schwellen, die alle oder keinen Anruf markieren"
        reason += (" bzw. die Fehlalarmgrenze verletzen," if max_false_alarm_rate is not None else "")
        reason += " wurden nicht berücksichtigt."
    return {
        "threshold": pick["threshold"], "flag_f1": f["f1"], "flag_recall": f["recall"],
        "flag_precision": f["precision"], "false_alarm_rate": f["false_alarm_rate"], "miss_rate": f["miss_rate"],
        "tied": [s["threshold"] for s in tied], "reason": reason,
    }


def cross_validate(pipeline: "Pipeline", results: Sequence[CallResult], calls: Sequence[Call], n_folds: int = 5,
                   thresholds: Sequence[float] | None = None,
                   overrides: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Out-of-fold metrics for the threshold suggestion: per dialogue-level fold, ``suggest_threshold`` on
    the other folds, then that threshold on the held-out fold. A suggestion fitted and scored on the same
    30 dialogues is optimistic; this is not. ``None`` when the results cover fewer than two folds."""
    fold_of = split_dialogues(list(calls), n_folds)
    by_fold: dict[int, list[CallResult]] = {}
    for r in results:
        k = fold_of.get(dialogue_of(r.call_id))
        if k is not None:
            by_fold.setdefault(k, []).append(r)
    if len(by_fold) < 2:
        return None
    families = pipeline.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    idx = _truth_index(calls)
    default = float(pipeline.cfg.fusion.get("threshold", 0.55))
    folds, oof = [], []
    for k in sorted(by_fold):
        train = [r for j, rs in by_fold.items() if j != k for r in rs]
        pick = suggest_threshold(sweep(pipeline, train, calls, thresholds, overrides))
        t = pick["threshold"] if pick else default
        for r in by_fold[k]:
            d = pipeline.decide(r.transcript, r.checks, {**(overrides or {}), "threshold": t}, families)
            oof.append(make_row(r.model_copy(update={"decision": d}), idx.get(r.call_id), can_alarm))
        folds.append({"fold": k, "threshold": t, "n_test": len(by_fold[k]),
                      "dialogues": sorted({dialogue_of(r.call_id) for r in by_fold[k]})})
    return {"n_folds": len(folds), "folds": folds, "metrics": metrics(oof), "rows": oof}


# --------------------------------------------------------------------------------------------
# Full evaluation run
# --------------------------------------------------------------------------------------------


def load_results(runs_dir: str | Path) -> list[CallResult]:
    """Every ``<runs_dir>/<call_id>/result.json`` the sinks wrote, e.g. to sweep thresholds on officer
    feedback without re-processing audio. Unreadable files are skipped with a warning."""
    out = []
    for p in sorted(Path(runs_dir).glob("*/result.json")):
        try:
            out.append(CallResult.model_validate_json(p.read_text()))
        except Exception as e:
            log.warning("skipping %s: %s", p, e)
    return out


def evaluate(pipeline: "Pipeline", calls: Sequence[Call],
             progress: Callable[[int, int, Call, Row], None] | None = None,
             overrides: dict[str, Any] | None = None) -> tuple[list[Row], list[CallResult]]:
    """Process every call from audio (ASR, checks... are cached by the pipeline). A failing call
    becomes an error row instead of aborting the run. Returns (rows, successful results)."""
    can_alarm = {f.id for f in pipeline.ctx.families() if f.can_alarm}
    rows: list[Row] = []
    results: list[CallResult] = []
    for i, call in enumerate(calls, 1):
        try:
            res = pipeline.process(call.audio_path, call.call_id, emit=False, overrides=overrides)
        except Exception as e:
            log.exception("eval: call %s failed", call.call_id)
            row = error_row(call.call_id, call, f"{type(e).__name__}: {e}")
        else:
            results.append(res)
            row = make_row(res, call, can_alarm)
        rows.append(row)
        if progress:
            progress(i, len(calls), call, row)
    return rows, results


# --------------------------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------------------------


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def _f(x: float | None, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def _meta_value(v: Any) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k}={x}" for k, x in v.items() if x not in (None, False, "")) or "-"
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v)


def _table(header: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(lines)


def _summary_rows(groups: dict[str, dict[str, Any]], prefix: str = "") -> list[list[Any]]:
    return [[f"{prefix}{k}", s["n"], _pct(s["accuracy"]), _pct(s["flag_precision"]), _pct(s["flag_recall"]),
             _f(s["flag_f1"]), _pct(s["false_alarm_rate"]), _pct(s["miss_rate"]), _f(s["alarm_f1"])]
            for k, s in groups.items()]


SUMMARY_HEADER = ["Gruppe", "n", "Accuracy", "Precision", "Recall", "F1", "Fehlalarme", "Verpasst", "Alarm-F1"]


def render_markdown(m: dict[str, Any], rows: list[Row], swept: list[dict[str, Any]] | None = None,
                    suggestion: dict[str, Any] | None = None, meta: dict[str, Any] | None = None,
                    cv: dict[str, Any] | None = None) -> str:
    meta = meta or {}
    flag, alarm, rh = m["flag"], m["alarm"], m["review_handling"]
    out = [f"# callguard Evaluation{(' - ' + meta['config']) if meta.get('config') else ''}", ""]
    if meta:
        out += [", ".join(f"{k}: {_meta_value(v)}" for k, v in meta.items() if v not in (None, [], {}, "")), ""]
    cf = m.get("check_failures") or {}
    if cf.get("calls"):
        by = ", ".join(f"{k} {v}x" for k, v in sorted(cf["by_check"].items()))
        out += [f"**Achtung:** In {cf['calls']} von {len(rows)} Anrufen ist mindestens eine Prüfung ausgefallen "
                f"({by}). Diese Anrufe wurden ohne sie entschieden; die Zahlen messen dann nur die übrigen "
                f"Prüfungen.", ""]
    out += [
        "## Kennzahlen", "",
        "Markiert = Alarm oder Prüfen (ein Mensch hört den Anruf an).", "",
        _table(["Kennzahl", "Wert"], [
            ["Anrufe (mit Sollbewertung)", m["n"]],
            ["Fehler", m["errors"]],
            ["Accuracy (3 Klassen)", _pct(m["accuracy"])],
            ["Fehlalarmquote (harmlos, aber markiert)", f"{_pct(flag['false_alarm_rate'])} ({flag['fp']}/{flag['fp'] + flag['tn']})"],
            ["Verpasste Fälle (markierungswürdig, aber kein Alarm)", f"{_pct(flag['miss_rate'])} ({flag['fn']}/{flag['tp'] + flag['fn']})"],
            ["Markiert: Precision / Recall / F1", f"{_pct(flag['precision'])} / {_pct(flag['recall'])} / {_f(flag['f1'])}"],
            ["Nur Alarm: Precision / Recall / F1", f"{_pct(alarm['precision'])} / {_pct(alarm['recall'])} / {_f(alarm['f1'])}"],
            ["Soll-Prüffälle eskaliert", f"{rh['escalated']}/{rh['n']} (davon als Prüfen: {rh['as_review']})"],
            ["Familie getroffen (Soll-Alarme)", f"{m['family_hit']['hits']}/{m['family_hit']['n']}"],
            ["Arbeitslast: Alarme / Prüfen", f"{m['workload']['alarms']} / {m['workload']['reviews']}"],
        ]), "",
        "## Konfusionsmatrix (Zeilen = Soll, Spalten = Ist)", "",
        _table(["Soll \\ Ist", *LABELS], [[e, *(m["confusion"][e][p] for p in LABELS)] for e in LABELS]), "",
    ]
    groups = {**{f"Stufe {k}": v for k, v in m["by_level"].items()}, **m["by_noise"]}
    if groups:
        out += ["## Aufschlüsselung", "", _table(SUMMARY_HEADER, _summary_rows(groups)), ""]
    if swept:
        out += ["## Schwellen-Sweep", "", _table(
            ["Schwelle", "Precision", "Recall", "F1", "Fehlalarme", "Verpasst", "Alarm-F1", "Accuracy"],
            [[_f(s["threshold"]), _pct(s["metrics"]["flag"]["precision"]), _pct(s["metrics"]["flag"]["recall"]),
              _f(s["metrics"]["flag"]["f1"]), _pct(s["metrics"]["flag"]["false_alarm_rate"]),
              _pct(s["metrics"]["flag"]["miss_rate"]), _f(s["metrics"]["alarm"]["f1"]),
              _pct(s["metrics"]["accuracy"])] for s in swept]), ""]
    if suggestion:
        out += [f"**Vorschlag:** {suggestion['reason']}", ""]
    if cv:
        out += ["## Kreuzvalidierung (Schwelle je Fold nur auf den übrigen Folds gewählt)", "",
                _table(["Fold", "Schwelle", "Anrufe", "Dialoge"],
                       [[f["fold"], _f(f["threshold"]), f["n_test"], " ".join(f["dialogues"])] for f in cv["folds"]]),
                "", _table(SUMMARY_HEADER, _summary_rows({"out-of-fold": _summary(cv["rows"])})), ""]
    out += ["## Anrufe", "", _table(
        ["Anruf", "Stufe", "Rauschen", "Soll", "Ist", "Score", "Unsicherheit", "Familie", "Soll-Familie", ""],
        [[r["call_id"], r.get("level") or "-", "ja" if r.get("noisy") else "nein", r.get("expected") or "-",
          r["predicted"], _f(r.get("score")), _f(r.get("uncertainty")), r.get("top_family") or "-",
          r.get("expected_family") or "-",
          ("FEHLER" if r.get("error") else ("ok" if r.get("expected") == r["predicted"] else "x"))
          + (f" (ohne {', '.join(r['failed_checks'])})" if r.get("failed_checks") else "")]
         for r in rows]), ""]
    return "\n".join(out)


def write_report(out_dir: str | Path, m: dict[str, Any], rows: list[Row], swept: list[dict[str, Any]] | None = None,
                 suggestion: dict[str, Any] | None = None, meta: dict[str, Any] | None = None,
                 cv: dict[str, Any] | None = None) -> tuple[Path, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    j, md = out / "report.json", out / "report.md"
    j.write_text(json.dumps({"meta": meta or {}, "metrics": m, "sweep": swept or [], "suggestion": suggestion,
                             "cv": cv, "rows": rows}, ensure_ascii=False, indent=1, default=str))
    md.write_text(render_markdown(m, rows, swept, suggestion, meta, cv))
    return j, md
