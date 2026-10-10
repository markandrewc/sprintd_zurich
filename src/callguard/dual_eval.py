"""Dual-reader facts evaluation (research/findings/dual_facts_prereg.md). Pure re-fusion, no models.

Both AI readers' stored fact answers (Qwen ``facts``, Kev ``facts_kev``) are combined under a
:class:`~callguard.fact_policy.FactPolicy`, then decided by the profile's fusion exactly as for one reader. This
module turns that into eval rows (``experiments.result_row``), out-of-fold CV rows (``experiments.cv_predict``)
and the metric blocks the pre-registration asks for: flag AUC, false-alarm rate, miss rate, 3-class accuracy,
review recall, each with a 95% bootstrap CI over twin groups (:mod:`callguard.stats`), and paired differences
against the champion v3 (= combination ``only_a``: Qwen alone, same table) on the same calls.

Sets are never pooled: dev (dev folds only, never the holdout) and test50 (external, fixed threshold, one look)
are evaluated and reported separately by the caller (``callguard dualfacts eval``).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from callguard import fact_policy as fpol
from callguard import stats
from callguard.types import CallResult, CheckResult, Decision, Family, Transcript

Row = dict[str, Any]

# the pre-registered read-outs (stats.METRICS names) + the threshold-free flag AUC
METRICS = ("false_alarm_rate", "miss_rate", "accuracy", "review_recall")
LABEL = {"auc": "flag AUC", "false_alarm_rate": "FAR", "miss_rate": "miss", "accuracy": "3-class acc",
         "review_recall": "review recall"}
GRID_BANDS = ((0.2, 0.8), (0.3, 0.7), (0.4, 0.6))


# --------------------------------------------------------------------------------------------
# policies
# --------------------------------------------------------------------------------------------


def champion_v3(base: fpol.FactPolicy | None = None) -> fpol.FactPolicy:
    """Champion v3 = Qwen alone on the same table: the pre-registered policy with combination ``only_a``."""
    return (base or fpol.default_policy()).with_combination("only_a")


def kev_band(policy: fpol.FactPolicy, lo: float, hi: float) -> fpol.FactPolicy:
    return policy.with_reader(1, mode="band", lo=float(lo), hi=float(hi))


def setting_name(policy: fpol.FactPolicy) -> str:
    b = policy.b
    kb = f"{b.lo:.1f}-{b.hi:.1f}" if b.mode == "band" else "3way"
    return f"{policy.combination}/kev{kb}"


def grid(base: fpol.FactPolicy | None = None, bands: Iterable[tuple[float, float]] = GRID_BANDS,
         combinations: Iterable[str] = fpol.COMBINATIONS) -> list[fpol.FactPolicy]:
    """Kev bands x combination modes (reader A stays as in ``base``: Qwen three-way)."""
    base = base or fpol.default_policy()
    return [kev_band(base, lo, hi).with_combination(c) for (lo, hi) in bands for c in combinations]


# --------------------------------------------------------------------------------------------
# re-fusion: a pipeline stand-in whose decide() is the fusion on the combined checks
# --------------------------------------------------------------------------------------------


def combine_results(results: Iterable[CallResult], tables: Mapping[str, Any], policy: fpol.FactPolicy,
                    **scoring: float) -> list[CallResult]:
    """Each call with both readers replaced by the combined facts result under ``policy`` (computed once, so a
    threshold sweep only re-runs the weighted fusion)."""
    return [r.model_copy(update={"checks": fpol.combined_checks(r, tables, policy, **scoring)}) for r in results]


class PolicyPipe:
    """Duck-typed :class:`~callguard.pipeline.Pipeline` for ``eval.sweep`` / ``experiments.cv_predict`` on
    results already combined by :func:`combine_results`: ``decide`` = the two-readers fusion's weighted decision
    on the combined checks (``TwoReadersFusion.decide_checks``; identical label and score to
    ``decide_policy``, which only adds a reason line)."""

    def __init__(self, pipe: Any):
        self.pipe = pipe
        self.ctx = pipe.ctx
        self.cfg = pipe.cfg
        self.checks = pipe.checks
        self.fusion = pipe.fusion
        if not hasattr(self.fusion, "decide_checks"):
            raise TypeError("dual_eval needs the two_readers fusion (fusion.type: two_readers, rule: policy)")

    def decide(self, transcript: Transcript, results: dict[str, CheckResult], overrides: dict[str, Any] | None = None,
               families: list[Family] | None = None, views: dict[str, Transcript] | None = None) -> Decision:
        families = families if families is not None else self.ctx.families()
        ov = dict(overrides or {})
        ov.setdefault("weights", {c.name: c.weight for c in self.checks})
        return self.fusion.decide_checks(transcript, results, families, ov)


@dataclass
class PolicyRows:
    policy: fpol.FactPolicy
    fixed: list[Row]
    cv: list[Row]
    cv_folds: list[dict[str, Any]]


def policy_rows(pipe: Any, results: Sequence[CallResult], calls: Sequence[Any], policy: fpol.FactPolicy,
                tables: Mapping[str, Any], *, threshold: float, fold_of: Mapping[str, int] | None = None,
                thresholds: Sequence[float] | None = None) -> PolicyRows:
    """Fixed-threshold rows and (with ``fold_of``) out-of-fold CV rows (max-F1 threshold chosen on the other
    folds, ``experiments.cv_predict``) for one policy."""
    from callguard import eval as ev
    from callguard import experiments as ex

    pp = PolicyPipe(pipe)
    combined = combine_results(results, tables, policy, **getattr(pipe.fusion, "scoring", {}))
    families = pp.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    weights = ev.check_weights(pp)
    idx = {c.call_id: c for c in calls}
    fixed = []
    for r in combined:
        d = pp.decide(r.transcript, r.checks, {"threshold": threshold}, families)
        fixed.append(ex.result_row(r.model_copy(update={"decision": d}), idx.get(r.call_id), can_alarm, weights))
    cv, folds = ([], [])
    if fold_of:
        cv, folds = ex.cv_predict(pp, combined, calls, dict(fold_of), thresholds)
    return PolicyRows(policy, fixed, cv, folds)


# --------------------------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------------------------


def counts(rows: Sequence[Row]) -> dict[str, int]:
    lab = stats.labeled(rows)
    return {"n": len(lab), "units": len({stats._dialogue(r) for r in lab}),
            "flagged": sum(r["predicted"] in stats.FLAG for r in lab),
            "alarms": sum(r["predicted"] == "alarm" for r in lab),
            "reviews": sum(r["predicted"] == "review" for r in lab),
            "expected": {k: sum(r["expected"] == k for r in lab) for k in ("alarm", "review", "no_alert")}}


def metric_block(rows: Sequence[Row], n_boot: int = 2000, seed: int = 13, with_auc: bool = True) -> dict[str, Any]:
    """Counts + each read-out as {value, lo, hi} (95% percentile CI over resampled twin groups)."""
    ci = stats.bootstrap_ci(rows, n_boot, seed, metrics=METRICS)
    out: dict[str, Any] = {**counts(rows), **{k: {kk: ci[k][kk] for kk in ("value", "lo", "hi")} for k in METRICS}}
    if with_auc:
        a = stats.bootstrap_auc(rows, n_boot, seed)["flag"]
        out["auc"] = {k: a[k] for k in ("value", "lo", "hi")}
    return out


def paired_block(base: Sequence[Row], rows: Sequence[Row], n_boot: int = 2000, seed: int = 13,
                 with_auc: bool = True) -> dict[str, Any]:
    """``rows`` minus ``base`` on the same calls, paired bootstrap over twin groups; McNemar on flag / label
    correctness; ``changed`` = calls whose label differs."""
    pb = stats.paired_bootstrap(base, rows, n_boot, seed, metrics=METRICS)
    out: dict[str, Any] = {k: {kk: pb[k][kk] for kk in ("a", "b", "diff", "lo", "hi", "real")} for k in METRICS}
    if with_auc:
        pa = stats.paired_auc(base, rows, n_boot, seed)["flag"]
        out["auc"] = {kk: pa[kk] for kk in ("a", "b", "diff", "lo", "hi", "real")}
    fl = stats.flips(base, rows)
    out["n"] = pb.get("_n", {})
    out["changed"] = len(fl)
    out["flips"] = [{k: f[k] for k in ("call_id", "expected", "a", "b", "flag_change", "label_change")} for f in fl]
    out["mcnemar_flag"] = stats.mcnemar(base, rows, stats.flag_correct)
    out["mcnemar_label"] = stats.mcnemar(base, rows, stats.label_correct)
    return out


def label_diff(rows_a: Sequence[Row], rows_b: Sequence[Row]) -> dict[str, Any]:
    """Sanity: calls whose predicted label differs between two row sets (same call ids), max |score diff|."""
    b = {r["call_id"]: r for r in rows_b}
    common = [r for r in rows_a if r["call_id"] in b]
    diff = [r["call_id"] for r in common if r.get("predicted") != b[r["call_id"]].get("predicted")]
    ds = [abs(float(r["score"]) - float(b[r["call_id"]]["score"])) for r in common
          if isinstance(r.get("score"), (int, float)) and isinstance(b[r["call_id"]].get("score"), (int, float))]
    return {"n": len(common), "differ": len(diff), "calls": diff, "max_score_diff": round(max(ds), 6) if ds else None,
            "missing": sorted({r["call_id"] for r in rows_a} ^ {r["call_id"] for r in rows_b})}


# --------------------------------------------------------------------------------------------
# reader agreement
# --------------------------------------------------------------------------------------------


def agreement_counts(answers: Iterable[tuple[str, str, Mapping[str, float] | None, Mapping[str, float] | None]],
                     policy: fpol.FactPolicy) -> dict[str, Any]:
    """Over (family, fact, p_A, p_B) answers: per reader how often a fact resolves ja / nein / unklar (answers
    that reader gave), and among answers both gave: how many differ (``disagree``) and how many are a hard
    contradiction ja vs nein (``contradict``)."""
    out: dict[str, Any] = {"answers": 0, "both": 0, "disagree": 0, "contradict": 0,
                           "a": {v: 0 for v in fpol.VALUES}, "b": {v: 0 for v in fpol.VALUES},
                           "combined": {v: 0 for v in fpol.VALUES}}
    for fam, fact, pa, pb in answers:
        rf = fpol.resolve_fact(policy, fam, fact, pa, pb)
        out["answers"] += 1
        if rf.pa is not None:
            out["a"][rf.va] += 1
        if rf.pb is not None:
            out["b"][rf.vb] += 1
        out["combined"][rf.value] += 1
        if rf.pa is not None and rf.pb is not None:
            out["both"] += 1
            out["disagree"] += rf.va != rf.vb
            out["contradict"] += {rf.va, rf.vb} == {"yes", "no"}
    return out


def stored_answers(results: Mapping[str, CallResult], policy: fpol.FactPolicy, tables: Mapping[str, Any]
                   ) -> list[tuple[str, str, dict[str, float] | None, dict[str, float] | None]]:
    """Every stored (family, fact) answer pair of the table's facts (calls where at least one reader answered)."""
    known = {(fam, f.id) for fam, ft in tables.items() for f in ft.facts}
    return [(fam, fid, a.pa, a.pb) for (fam, fid), lst in fpol.fact_answers(results, policy).items()
            if (fam, fid) in known for a in lst]


# --------------------------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------------------------


def _pct(x: float | None, pct: bool) -> str:
    if x is None:
        return "–"
    return f"{100 * x:.0f}%" if pct else f"{x:.2f}"


def fmt_ci(m: Mapping[str, Any] | None, pct: bool = True) -> str:
    if not m or m.get("value") is None:
        return "–"
    return f"{_pct(m['value'], pct)} [{_pct(m.get('lo'), pct)}, {_pct(m.get('hi'), pct)}]"


def fmt_diff(m: Mapping[str, Any] | None, pct: bool = True) -> str:
    if not m or m.get("diff") is None:
        return "–"
    s = (lambda x: "–" if x is None else (f"{100 * x:+.0f}" if pct else f"{x:+.2f}"))
    unit = " pp" if pct else ""
    return f"{s(m['diff'])}{unit} [{s(m.get('lo'))}, {s(m.get('hi'))}]" + (" *" if m.get("real") else "")


COLS = ("auc", *METRICS)


def metrics_table(blocks: Sequence[tuple[str, Mapping[str, Any]]], cols: Sequence[str] = COLS) -> str:
    head = ["setting", "n (units)", "flagged / alarm / review", *(LABEL[c] for c in cols)]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for name, b in blocks:
        cells = [name, f"{b['n']} ({b['units']})", f"{b['flagged']} / {b['alarms']} / {b['reviews']}",
                 *(fmt_ci(b.get(c), pct=c != "auc") for c in cols)]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def paired_table(blocks: Sequence[tuple[str, Mapping[str, Any]]], cols: Sequence[str] = COLS) -> str:
    head = ["comparison (variant − champion v3)", "calls changed", *(f"Δ {LABEL[c]}" for c in cols), "McNemar flag p"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for name, p in blocks:
        mc = p.get("mcnemar_flag") or {}
        cells = [name, str(p.get("changed", "–")), *(fmt_diff(p.get(c), pct=c != "auc") for c in cols),
                 f"{mc.get('p', '–')} ({mc.get('a_only', 0)}↔{mc.get('b_only', 0)})"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def agreement_table(blocks: Sequence[tuple[str, Mapping[str, Any]]]) -> str:
    def vc(d: Mapping[str, int]) -> str:
        n = sum(d.values()) or 1
        return " / ".join(f"{d[v]} ({100 * d[v] / n:.0f}%)" for v in fpol.VALUES)

    head = ["set / Kev band", "fact answers (both)", "Qwen ja / nein / unklar", "Kev ja / nein / unklar",
            "readers differ", "ja vs nein"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for name, a in blocks:
        both = a["both"] or 1
        lines.append("| " + " | ".join([name, f"{a['answers']} ({a['both']})", vc(a["a"]), vc(a["b"]),
                                         f"{a['disagree']} ({100 * a['disagree'] / both:.0f}%)",
                                         f"{a['contradict']} ({100 * a['contradict'] / both:.0f}%)"]) + " |")
    return "\n".join(lines)


def grid_entry(name: str, policy: fpol.FactPolicy, fixed: Mapping[str, Any], cv: Mapping[str, Any] | None,
               paired: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The compact per-setting record the UI cites (research/evidence/dual_facts_grid.json)."""
    def v(b: Mapping[str, Any] | None, k: str) -> Any:
        return None if not b or not b.get(k) else b[k].get("value")

    out = {"setting": name, "kev_band": [policy.b.lo, policy.b.hi], "combination": policy.combination,
           "combination_de": policy.combination_de(), "n": fixed["n"], "flagged": fixed["flagged"],
           "alarms": fixed["alarms"], "reviews": fixed["reviews"],
           "false_alarm_rate": v(fixed, "false_alarm_rate"), "miss_rate": v(fixed, "miss_rate"),
           "review_recall": v(fixed, "review_recall"), "accuracy": v(fixed, "accuracy"), "auc": v(fixed, "auc"),
           "ci": {k: [fixed[k]["lo"], fixed[k]["hi"]] for k in COLS if fixed.get(k)}}
    if cv:
        out["cv"] = {k: v(cv, k) for k in METRICS} | {"flagged": cv["flagged"], "alarms": cv["alarms"],
                                                     "reviews": cv["reviews"]}
    if paired:
        out["vs_champion_v3"] = {"calls_changed": paired.get("changed"),
                                 **{k: paired[k]["diff"] for k in COLS if paired.get(k)}}
    return out
