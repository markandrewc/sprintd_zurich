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


# --------------------------------------------------------------------------------------------
# evaluation sets + the two reports (callguard dualfacts eval)
# --------------------------------------------------------------------------------------------

SETS = {"dev": "dual-facts", "test50": "dual-facts-test50"}  # set -> profile
DEFAULT_THRESHOLD = 0.55


@dataclass
class EvalSet:
    """One evaluation set: the profile's pipeline (only its fusion is used), the stored results of the set's
    calls, their ground truth, the active policy table and (dev) the locked CV folds."""
    name: str
    profile: str
    pipe: Any
    results: list[CallResult]
    calls: list[Any]
    tables: dict[str, Any]
    fold_of: dict[str, int] | None
    threshold: float
    runs_dir: str = ""
    policy_table: str = ""
    missing: list[str] | None = None


def load_set(name: str, profile: str | None = None, overrides: Sequence[str] = (),
             threshold: float = DEFAULT_THRESHOLD) -> EvalSet:
    """``dev``: the case calls of the dev folds only (never the holdout), CV over the locked dev folds.
    ``test50``: every call of the external set (split ``external``; rows carry the dataset's twin group via
    ``Call.group``, so the bootstrap resamples twin groups as ``callguard experiment`` does)."""
    from callguard import splits as sp
    from callguard.config import load_config
    from callguard.data import load_calls
    from callguard.ui import backend as be

    if name not in SETS:
        raise ValueError(f"set must be one of {tuple(SETS)}, got {name!r}")
    cfg = load_config(profile or SETS[name], list(overrides))
    eng = be.Engine(cfg, use_cache=True)
    if eng.pipeline is None:
        raise RuntimeError(eng.error or "pipeline unavailable")
    pipe = eng.pipeline
    PolicyPipe(pipe)  # fails early unless the fusion is two_readers
    calls = load_calls(eng.ctx.data_dir)
    fold_of = None
    if name == "dev":
        splits = sp.load_splits()
        calls = splits.select(calls, "dev")
        fold_of = splits.dev_fold_of()
    loaded = be.load_results(eng.ctx.runs_dir).results
    ids = [c.call_id for c in calls]
    results = [loaded[i] for i in ids if i in loaded]
    return EvalSet(name, cfg.name, pipe, results, calls, pipe.fusion.tables(), fold_of, float(threshold),
                   str(eng.ctx.runs_dir), str(pipe.fusion.policy_table), [i for i in ids if i not in loaded])


def rule_a_rows(pipe: Any, results: Sequence[CallResult], calls: Sequence[Any], threshold: float) -> list[Row]:
    """Sanity reference: the same fusion with rule ``a`` (reader A's stored facts result as computed, reader B
    dropped), fixed threshold. Combination ``only_a`` must give the same labels."""
    import copy

    from callguard import eval as ev
    from callguard import experiments as ex

    fa = copy.copy(pipe.fusion)
    fa.rule = "a"
    families = pipe.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    weights = ev.check_weights(pipe)
    ov = {"threshold": threshold, "weights": {c.name: c.weight for c in pipe.checks}}
    idx = {c.call_id: c for c in calls}
    out = []
    for r in results:
        d = fa.decide(r.transcript, r.checks, families, dict(ov))
        out.append(ex.result_row(r.model_copy(update={"decision": d}), idx.get(r.call_id), can_alarm, weights))
    return out


def set_agreement(results: Sequence[CallResult], tables: Mapping[str, Any], policy: fpol.FactPolicy
                  ) -> dict[str, Any]:
    return agreement_counts(stored_answers({r.call_id: r for r in results}, policy, tables), policy)


def _set_meta(es: EvalSet, n_boot: int, seed: int) -> dict[str, Any]:
    import datetime as dt

    return {"set": es.name, "profile": es.profile, "runs_dir": es.runs_dir, "policy_table": es.policy_table,
            "n_results": len(es.results), "missing": es.missing or [], "threshold": es.threshold,
            "n_boot": n_boot, "seed": seed, "created": dt.datetime.now().isoformat(timespec="seconds"),
            "bootstrap_unit": "twin group (case: config/splits.yaml groups; test50: data_test50 dataset.yaml groups)"}


def evaluate_dev(es: EvalSet, n_boot: int = 2000, seed: int = 13,
                 bands: Iterable[tuple[float, float]] = GRID_BANDS) -> dict[str, Any]:
    """Dev report: default vs champion v3 (fixed + CV rows, metric blocks, paired deltas), the 12-setting grid
    (Kev band x combination, Qwen three-way), reader agreement per Kev band, and the only_a == rule a sanity."""
    bands = list(bands)
    default = fpol.default_policy()
    champ = champion_v3(default)
    kw: dict[str, Any] = {"threshold": es.threshold, "fold_of": es.fold_of}
    pr = {"default": policy_rows(es.pipe, es.results, es.calls, default, es.tables, **kw),
          "champion_v3": policy_rows(es.pipe, es.results, es.calls, champ, es.tables, **kw)}
    blocks = {k: {"fixed": metric_block(v.fixed, n_boot, seed), "cv": metric_block(v.cv, n_boot, seed),
                  "cv_folds": v.cv_folds} for k, v in pr.items()}
    paired = {"fixed": paired_block(pr["champion_v3"].fixed, pr["default"].fixed, n_boot, seed),
              "cv": paired_block(pr["champion_v3"].cv, pr["default"].cv, n_boot, seed)}
    entries = []
    for pol in grid(default, bands):
        rows = policy_rows(es.pipe, es.results, es.calls, pol, es.tables, **kw)
        fb = metric_block(rows.fixed, n_boot, seed)
        cb = metric_block(rows.cv, n_boot, seed, with_auc=False)
        pb = paired_block(pr["champion_v3"].fixed, rows.fixed, n_boot, seed)
        entries.append(flag_entry(grid_entry(setting_name(pol), pol, fb, cb, pb), pol, default))
    agreement = {f"dev, Kev {lo:.1f}-{hi:.1f}": set_agreement(es.results, es.tables, kev_band(default, lo, hi))
                 for lo, hi in bands}
    ra = rule_a_rows(es.pipe, es.results, es.calls, es.threshold)
    return {"meta": _set_meta(es, n_boot, seed) | {"folds": "locked dev folds (config/splits.yaml), holdout excluded"},
            "policies": {"default": default.as_dict(), "champion_v3": champ.as_dict()},
            "blocks": blocks, "paired": paired, "grid": entries, "ui_text": ui_text(entries, default),
            "agreement": agreement, "sanity": {"only_a_vs_rule_a": label_diff(pr["champion_v3"].fixed, ra)},
            "rows": {k: {"fixed": v.fixed, "cv": v.cv} for k, v in pr.items()}}


def flag_entry(e: dict[str, Any], pol: fpol.FactPolicy, default: fpol.FactPolicy) -> dict[str, Any]:
    """Mark the pre-registered default and the champion v3 (only_a at the default Kev band; the other only_a
    rows ignore Kev too and are equivalent)."""
    same_band = (pol.b.lo, pol.b.hi) == (default.b.lo, default.b.hi)
    e["default"] = same_band and pol.combination == default.combination
    e["champion_v3"] = same_band and pol.combination == "only_a"
    e["equivalent_to_champion_v3"] = pol.combination == "only_a"
    return e


def evaluate_test50(es: EvalSet, n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    """test50 report (ONE look): default vs champion v3 at the fixed threshold only, paired deltas, agreement
    (default Kev band), sanity. No grid, no CV, nothing is chosen from it."""
    default = fpol.default_policy()
    champ = champion_v3(default)
    pr = {"default": policy_rows(es.pipe, es.results, es.calls, default, es.tables, threshold=es.threshold),
          "champion_v3": policy_rows(es.pipe, es.results, es.calls, champ, es.tables, threshold=es.threshold)}
    blocks = {k: {"fixed": metric_block(v.fixed, n_boot, seed)} for k, v in pr.items()}
    paired = {"fixed": paired_block(pr["champion_v3"].fixed, pr["default"].fixed, n_boot, seed)}
    ra = rule_a_rows(es.pipe, es.results, es.calls, es.threshold)
    return {"meta": _set_meta(es, n_boot, seed) | {"look": "test50 one look (research/findings/test50_prereg.md)"},
            "policies": {"default": default.as_dict(), "champion_v3": champ.as_dict()},
            "blocks": blocks, "paired": paired,
            "agreement": {f"test50, Kev {default.b.lo:.1f}-{default.b.hi:.1f}":
                          set_agreement(es.results, es.tables, default)},
            "sanity": {"only_a_vs_rule_a": label_diff(pr["champion_v3"].fixed, ra)},
            "rows": {k: {"fixed": v.fixed} for k, v in pr.items()}}


# --------------------------------------------------------------------------------------------
# plain-German one-liners for the officer UI (dev numbers)
# --------------------------------------------------------------------------------------------

UI_COMBINATION = {"only_a": "Nur Qwen entscheidet (= Champion v3), Kev wird nur angezeigt.",
                  "only_b": "Nur Kev entscheidet, Qwen wird nur angezeigt.",
                  "agree": "Einigkeit: zählt nur, wenn beide gleich antworten, sonst «unklar» → Prüfen.",
                  "a_checked": "Qwen entscheidet; sagt Kev klar das Gegenteil, wird es «unklar» → Prüfen."}
UI_BAND = {"0.2-0.8": "Kev muss sehr sicher sein (ja ab 80 %, nein bis 20 %), sonst «unklar».",
           "0.3-0.7": "Kev muss recht sicher sein (ja ab 70 %, nein bis 30 %), sonst «unklar» (Standard).",
           "0.4-0.6": "Kev darf knapp entscheiden (ja ab 60 %, nein bis 40 %), seltener «unklar»."}


def band_key(e: Mapping[str, Any]) -> str:
    lo, hi = e["kev_band"]
    return f"{lo:.1f}-{hi:.1f}"


def numbers_line(e: Mapping[str, Any], set_label: str = "Dev") -> str:
    def pct(x: Any) -> str:
        return "–" if x is None else f"{100 * x:.0f} %"

    return (f"{set_label} ({e['n']} Anrufe): {e['flagged']} markiert ({e['alarms']} Alarm, {e['reviews']} Prüfen), "
            f"FAR {pct(e['false_alarm_rate'])}, Miss {pct(e['miss_rate'])}")


def ui_text(entries: Sequence[Mapping[str, Any]], default: fpol.FactPolicy | None = None) -> dict[str, dict[str, str]]:
    """{"combination": {mode: text}, "band": {"lo-hi": text}}: each combination at the default Kev band, each
    band at the default combination; text = plain-German meaning + the dev numbers of that setting."""
    default = default or fpol.default_policy()
    dband = f"{default.b.lo:.1f}-{default.b.hi:.1f}"
    out: dict[str, dict[str, str]] = {"combination": {}, "band": {}}
    for e in entries:
        if band_key(e) == dband:
            out["combination"][e["combination"]] = f"{UI_COMBINATION.get(e['combination'], '')} {numbers_line(e)}."
        if e["combination"] == default.combination:
            out["band"][band_key(e)] = f"{UI_BAND.get(band_key(e), '')} {numbers_line(e)}."
    return out


# --------------------------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------------------------


def grid_table(entries: Sequence[Mapping[str, Any]]) -> str:
    def p(x: Any) -> str:
        return "–" if x is None else f"{100 * x:.0f}%"

    head = ["setting", "flagged / alarm / review", "FAR", "miss", "3-class acc", "review recall", "flag AUC",
            "CV FAR", "CV miss", "CV acc", "calls changed vs v3", ""]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for e in entries:
        cv = e.get("cv") or {}
        tag = " ".join(t for t, k in (("**default**", "default"), ("**champion v3**", "champion_v3")) if e.get(k))
        if not tag and e.get("equivalent_to_champion_v3"):
            tag = "(= v3)"
        auc = "–" if e.get("auc") is None else f"{e['auc']:.2f}"
        lines.append("| " + " | ".join([
            e["setting"], f"{e['flagged']} / {e['alarms']} / {e['reviews']}", p(e["false_alarm_rate"]),
            p(e["miss_rate"]), p(e["accuracy"]), p(e["review_recall"]), auc, p(cv.get("false_alarm_rate")),
            p(cv.get("miss_rate")), p(cv.get("accuracy")), str((e.get("vs_champion_v3") or {}).get("calls_changed")),
            tag]) + " |")
    return "\n".join(lines)


def sanity_line(s: Mapping[str, Any]) -> str:
    return (f"only_a vs rule `a` (fixed threshold): {s['differ']} of {s['n']} calls differ in label "
            f"(max |score diff| {s['max_score_diff']}, unmatched calls {len(s['missing'])}).")


def _flip_line(p: Mapping[str, Any]) -> str:
    return ", ".join(f"{f['call_id']} ({f['expected']}: {f['a']}→{f['b']})" for f in p["flips"]) or "none"


DEFAULT_NAME = "default (agree, Kev 0.3-0.7)"
CHAMP_NAME = "champion v3 (only_a)"


def dev_markdown(rep: Mapping[str, Any]) -> str:
    m, b, p = rep["meta"], rep["blocks"], rep["paired"]

    def folds(k: str) -> str:
        return ", ".join(f"{f['fold']}: {f['threshold']:.2f}" for f in b[k]["cv_folds"])

    out = [f"# Dual-reader facts: DEV evaluation ({m['created']})", "",
           f"Profile `{m['profile']}`, table `{m['policy_table']}`, {m['n_results']} dev calls (dev folds only, "
           f"holdout excluded), fixed threshold {m['threshold']}, 95% bootstrap CIs over twin groups "
           f"({m['n_boot']}x, seed {m['seed']}). Pure re-fusion of stored answers, no model ran. "
           "Default = pre-registered (Qwen three-way, Kev band [0.3, 0.7], Einigkeit); champion v3 = Qwen alone "
           "(combination only_a).", "", "## Fixed threshold", "",
           metrics_table([(DEFAULT_NAME, b["default"]["fixed"]), (CHAMP_NAME, b["champion_v3"]["fixed"])]),
           "", "## CV (out-of-fold max-F1 threshold over the 4 dev folds)", "",
           metrics_table([(DEFAULT_NAME, b["default"]["cv"]), (CHAMP_NAME, b["champion_v3"]["cv"])]),
           "", f"CV thresholds per fold: default {folds('default')}; champion v3 {folds('champion_v3')}.", "",
           "## Paired: default − champion v3 (same calls, paired bootstrap over twin groups; * = CI excludes 0)", "",
           paired_table([("fixed threshold", p["fixed"]), ("CV", p["cv"])]), "",
           f"Calls whose label changes (fixed threshold): {_flip_line(p['fixed'])}.", "",
           f"Calls whose label changes (CV): {_flip_line(p['cv'])}.", "",
           "## Grid (DEV ONLY; Qwen three-way; for the officer UI, nothing is selected from it)", "",
           grid_table(rep["grid"]), "",
           "only_a ignores Kev, so its three rows are the champion v3 regardless of the band.", "",
           "## Reader agreement (dev calls, stored answers of the table's facts)", "",
           agreement_table(list(rep["agreement"].items())), "",
           "## Sanity", "", sanity_line(rep["sanity"]["only_a_vs_rule_a"]), ""]
    return "\n".join(out)


def test50_markdown(rep: Mapping[str, Any]) -> str:
    m, b, p = rep["meta"], rep["blocks"], rep["paired"]
    out = [f"# Dual-reader facts: test50 (ONE look, {m['created']})", "",
           f"Profile `{m['profile']}`, table `{m['policy_table']}`, {m['n_results']} calls (external set, never "
           f"pooled with dev), fixed threshold {m['threshold']}, 95% bootstrap CIs over twin groups ({m['n_boot']}x, "
           f"seed {m['seed']}). Default vs champion v3 only, as pre-registered. Nothing is tuned on this.", "",
           metrics_table([(DEFAULT_NAME, b["default"]["fixed"]), (CHAMP_NAME, b["champion_v3"]["fixed"])]),
           "", "## Paired: default − champion v3 (* = CI excludes 0)", "",
           paired_table([("fixed threshold", p["fixed"])]), "",
           f"Calls whose label changes: {_flip_line(p['fixed'])}.", "",
           "## Reader agreement (test50 calls)", "", agreement_table(list(rep["agreement"].items())), "",
           "## Sanity", "", sanity_line(rep["sanity"]["only_a_vs_rule_a"]), ""]
    return "\n".join(out)
