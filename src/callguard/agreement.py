"""Two readers: two model families answer the same fact sheet; agreement decides, disagreement escalates.

Pre-registered in ``research/findings/two_readers_prereg.md`` (rules, constants and acceptance criteria were
fixed there before any combined number was computed). Reader A is the facts check with the champion's backend
(Qwen2.5-7B, log-probs, evidence), reader B the same fact sheet read by another model family (Kev-4B). Both
are ordinary ``facts`` check instances in one config (e.g. ``facts`` and ``facts_kev``); the fusion plugin
``two_readers`` (:mod:`callguard.fusion.two_readers`) combines them per call with one of these rules:

* ``labels`` (R1): each reader's call is decided by the weighted fusion with only its own facts result (plus
  the shared rule checks); both alarm -> alarm, both no_alert -> no_alert, anything else -> review.
* ``facts`` (R2): per fact, gap = |p_A(yes) - p_B(yes)|; gap > ``gap`` (0.5) -> the fact is ``unclear``
  (the policy table's "unclear -> review" rules can fire), else the mean distribution is discretized. The
  table is re-evaluated (:func:`callguard.checks.facts.decide_family`) and the combined result replaces both
  readers in the weighted fusion.
* ``a`` / ``b``: one reader alone (sanity checks: must reproduce the single-reader runs exactly; live
  fallback when the second model is down).

This module holds the pure combination logic and :func:`merge_variants`, which joins two stored experiment
variants (same calls, one reader each) into one results.jsonl a re-fusion can read: then the standard
experiment runner (``refuse_from``) computes fixed / CV / CV@FAR20 rows, AUC and paired statistics with no
model running. ``callguard agreement`` wraps both (see commands/agreement.py).
"""

from __future__ import annotations

import json
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from callguard.cache import stable_hash
from callguard.checks.facts import (
    FamilyTable,
    average_probs,
    decide_family,
    discretize,
)
from callguard.types import CallResult, CheckResult, FamilyScore, Label

RULES = ("labels", "facts", "a", "b")
DEFAULT_GAP = 0.5  # pre-registered: |p_A(yes) - p_B(yes)| above this = the readers disagree on the fact
UNCLEAR: dict[str, float] = {"unclear": 1.0}
_LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}


# --------------------------------------------------------------------------------------------
# R1: call labels
# --------------------------------------------------------------------------------------------


def label_agreement(a: Label | None, b: Label | None) -> Label:
    """Both alarm -> alarm, both no_alert -> no_alert, anything else (a review, a contradiction, a missing
    reader) -> review."""
    if a == b and a in ("alarm", "no_alert"):
        return a  # type: ignore[return-value]
    return "review"


# --------------------------------------------------------------------------------------------
# R2: facts
# --------------------------------------------------------------------------------------------


def combine_fact(p_a: dict[str, float] | None, p_b: dict[str, float] | None, gap: float = DEFAULT_GAP,
                 decide_at: float = 0.5) -> tuple[str, dict[str, float], float, bool]:
    """(value, mean distribution, gap, disagree) for one fact. A missing reader counts as fully unclear."""
    pa, pb = p_a or UNCLEAR, p_b or UNCLEAR
    g = abs(float(pa.get("yes", 0.0)) - float(pb.get("yes", 0.0)))
    m = average_probs([pa, pb])
    disagree = g > gap
    return ("unclear" if disagree else discretize(m, decide_at)), m, round(g, 4), disagree


def _facts_of(fs: FamilyScore | None) -> dict[str, dict[str, Any]]:
    return dict(((fs.detail or {}).get("facts") or {})) if fs is not None else {}


def combine_family(ft: FamilyTable, fs_a: FamilyScore | None, fs_b: FamilyScore | None, *,
                   gap: float = DEFAULT_GAP, decide_at: float = 0.5, names: tuple[str, str] = ("A", "B"),
                   alarm_base: float = 0.6, review_score: float = 0.5, review_confidence: float = 0.3,
                   no_alert_scale: float = 0.4) -> FamilyScore:
    """One family's combined fact sheet -> the policy table -> a FamilyScore shaped like the facts check's
    (score / confidence / verdict as in FactSheetCheck.score_family), with both readers in the detail."""
    fa, fb = _facts_of(fs_a), _facts_of(fs_b)
    values: dict[str, str] = {}
    probs: dict[str, dict[str, float]] = {}
    facts: dict[str, dict[str, Any]] = {}
    split: list[str] = []
    for fact in ft.facts:
        da, db = fa.get(fact.id) or {}, fb.get(fact.id) or {}
        value, m, g, disagree = combine_fact(da.get("p"), db.get("p"), gap, decide_at)
        values[fact.id], probs[fact.id] = value, m
        entry: dict[str, Any] = {"label": fact.label, "role": fact.role,
                                 "question": da.get("question") or db.get("question") or "",
                                 "p": m, "value": value, "gap": g, "disagree": disagree,
                                 "readers": {names[0]: da.get("p"), names[1]: db.get("p")}}
        for k in ("evidence", "reason"):  # only reader A asks for evidence
            if da.get(k):
                entry[k] = da[k]
        facts[fact.id] = entry
        if disagree:
            pa_y = (da.get("p") or {}).get("yes")
            pb_y = (db.get("p") or {}).get("yes")
            split.append(f"{fact.label} ({names[0]} p(ja) {'-' if pa_y is None else f'{pa_y:.2f}'}, "
                         f"{names[1]} {'-' if pb_y is None else f'{pb_y:.2f}'})")
    fd = decide_family(ft, values, probs, alarm_base=alarm_base, review_score=review_score,
                       review_confidence=review_confidence, no_alert_scale=no_alert_scale)
    reason = fd.summary
    if split:
        reason += f". Leser uneinig (offen): {'; '.join(split)}"
    rule = fd.rule
    detail: dict[str, Any] = {
        "decision": fd.label, "facts": facts, "summary": reason,
        "rule": ({"id": rule.id, "label": rule.label, "when": rule.when, "text": rule.text} if rule
                 else {"id": None, "label": "no_alert", "when": None, "text": "keine Regel trifft zu"}),
        "rule_probs": fd.soft, "p_alarm": round(fd.p_alarm, 4), "p_review": round(fd.p_review, 4),
        "two_readers": {"readers": list(names), "gap": gap, "disagree": [f for f, e in facts.items() if e["disagree"]],
                        "missing": [n for n, fs in zip(names, (fs_a, fs_b)) if fs is None],
                        "labels": {names[0]: (fs_a.detail or {}).get("decision") if fs_a else None,
                                   names[1]: (fs_b.detail or {}).get("decision") if fs_b else None}},
    }
    return FamilyScore(score=round(min(1.0, max(0.0, fd.score)), 4), confidence=round(min(1.0, fd.confidence), 4),
                       verdict=fd.verdict, reason=reason,  # type: ignore[arg-type]
                       segment_ids=list(fs_a.segment_ids) if fs_a is not None else [], detail=detail)


def usable(r: CheckResult | None) -> CheckResult | None:
    """A reader's result unless it is missing or failed entirely."""
    return None if r is None or r.meta.get("error") else r


def combine_facts_results(tables: dict[str, FamilyTable], a: CheckResult | None, b: CheckResult | None, *,
                          name: str = "facts", gap: float = DEFAULT_GAP, decide_at: float = 0.5,
                          names: tuple[str, str] = ("A", "B"), **scoring: float) -> CheckResult:
    """R2 for one call: every family either reader scored (and the table has) is re-decided from both
    readers' facts. Findings (audio evidence) are reader A's; B's facts check runs without evidence."""
    a, b = usable(a), usable(b)
    fams = [f for f in tables if (a and f in a.family_scores) or (b and f in b.family_scores)]
    out = {f: combine_family(tables[f], a.family_scores.get(f) if a else None,
                             b.family_scores.get(f) if b else None, gap=gap, decide_at=decide_at, names=names,
                             **scoring) for f in fams}
    disagree = {f: fs.detail["two_readers"]["disagree"] for f, fs in out.items() if fs.detail["two_readers"]["disagree"]}
    meta = {"two_readers": {"rule": "facts", "readers": list(names), "gap": gap, "disagree": disagree,
                            "missing": [n for n, r in zip(names, (a, b)) if r is None]},
            "models": sorted({str(r.meta["model"]) for r in (a, b) if r is not None and r.meta.get("model")})}
    if a is not None and a.meta.get("model"):
        meta["model"] = a.meta["model"]
    src = a or b
    return CheckResult(check=name, type="facts", family_scores=out, findings=list(a.findings) if a else [],
                       meta=meta, view=src.view if src else None)


# --------------------------------------------------------------------------------------------
# joining two stored variants (offline evaluation)
# --------------------------------------------------------------------------------------------


def _transcript_key(r: CallResult) -> str:
    return stable_hash([(s.id, s.start, s.end, s.text, s.role) for s in r.transcript.segments])


def _check_key(c: CheckResult | None) -> str | None:
    return None if c is None else stable_hash({f: fs.model_dump(mode="json") for f, fs in c.family_scores.items()})


def merge_results(res_a: Sequence[CallResult], res_b: Sequence[CallResult], *, source_check: str = "facts",
                  reader_b: str = "facts_kev", shared: Sequence[str] = ("keywords", "patterns")
                  ) -> tuple[list[CallResult], dict[str, Any]]:
    """Reader A's results with reader B's ``source_check`` added as ``reader_b``, for the calls both have.
    The report lists calls only one side has and calls whose transcript or shared rule checks differ
    (they should not: both readers read the same cached transcript)."""
    b_idx = {r.call_id: r for r in res_b}
    merged: list[CallResult] = []
    report: dict[str, Any] = {"only_a": [], "only_b": sorted(set(b_idx) - {r.call_id for r in res_a}),
                              "transcript_differs": [], "shared_check_differs": {}, "missing_b_check": []}
    for ra in res_a:
        rb = b_idx.get(ra.call_id)
        if rb is None:
            report["only_a"].append(ra.call_id)
            continue
        cb = rb.checks.get(source_check)
        if cb is None:
            report["missing_b_check"].append(ra.call_id)
        if _transcript_key(ra) != _transcript_key(rb):
            report["transcript_differs"].append(ra.call_id)
        for n in shared:
            if _check_key(ra.checks.get(n)) != _check_key(rb.checks.get(n)):
                report["shared_check_differs"].setdefault(n, []).append(ra.call_id)
        checks = dict(ra.checks)
        if cb is not None:
            checks[reader_b] = cb.model_copy(update={"check": reader_b})
        merged.append(ra.model_copy(update={"checks": checks}))
    report["n_merged"] = len(merged)
    return merged, report


def merge_variants(dir_a: Path, dir_b: Path, out_dir: Path, *, source_check: str = "facts",
                   reader_b: str = "facts_kev") -> dict[str, Any]:
    """Write ``out_dir/results.jsonl`` (+ meta.json, merge_report.json) joining two stored variants; the
    experiment runner re-fuses it like any variant (``refuse_from``). Returns the merge report."""
    from callguard import experiments as ex

    res_a, res_b = ex.load_results(dir_a), ex.load_results(dir_b)
    if not res_a or not res_b:
        missing = [str(d) for d, r in ((dir_a, res_a), (dir_b, res_b)) if not r]
        raise FileNotFoundError(f"no results.jsonl in {', '.join(missing)}")
    merged, report = merge_results(res_a, res_b, source_check=source_check, reader_b=reader_b)
    tables = {}
    for side, res in (("a", res_a), ("b", res_b)):
        paths = {str(((r.checks.get(source_check) or CheckResult(check="", type="")).meta.get("policy_table") or {})
                     .get("path")) for r in res}
        tables[side] = sorted(paths)
    report["policy_tables"] = tables
    report["policy_table_mismatch"] = tables["a"] != tables["b"]
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.jsonl").open("w") as f:
        for r in merged:
            f.write(json.dumps(ex.strip_words(r), ensure_ascii=False) + "\n")
    meta_a, meta_b = ex._read_meta(dir_a), ex._read_meta(dir_b)
    meta = {"variant": out_dir.name, "description": f"merged sources for two-readers re-fusion: A = {dir_a.parent.name}/"
            f"{dir_a.name}, B = {dir_b.parent.name}/{dir_b.name} (facts -> {reader_b})",
            "merged_from": {"a": ex.source_provenance(dir_a), "b": ex.source_provenance(dir_b)},
            "split": meta_a.get("split") or meta_b.get("split"), "n_calls": len(merged),
            "calls": [r.call_id for r in merged], "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "llm_resolved": {**{f"a.{k}": v for k, v in (meta_a.get("llm_resolved") or {}).items()},
                             **{f"b.{k}": v for k, v in (meta_b.get("llm_resolved") or {}).items()}}}
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str))
    (out_dir / "merge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    return report


# --------------------------------------------------------------------------------------------
# the pre-registered evaluation: pairs, acceptance criteria, report
# --------------------------------------------------------------------------------------------

# wording -> (experiment spec, joined source variant, reader A ref, reader B ref); refs relative to the runs dir
# of the spec's base profile (<runs_dir>/experiments/<experiment>/<variant>)
PAIRS: dict[str, tuple[str, str, str, str]] = {
    "tuned": ("two_readers", "tuned_src", "kev_vs_facts/champion", "kev_vs_facts/kev_facts"),
    "para": ("two_readers", "para_src", "kev_vs_facts/qwen_facts_para", "kev_vs_facts/kev_facts_para"),
    "para2": ("two_readers", "para2_src", "kev_vs_facts/qwen_facts_para2", "kev_vs_facts/kev_facts_para2"),
    "blind": ("two_readers", "blind_src", "kev_vs_facts/qwen_facts_blind", "kev_vs_facts/kev_facts_blind"),
    "perturbed": ("two_readers_perturbed", "perturbed_src", "kev_perturbed/perturbed", "kev_perturbed/kev_facts"),
}
REWORDED = ("para", "para2", "blind")
# pre-registered acceptance constants (research/findings/two_readers_prereg.md)
FAR_MARGIN = 0.05
AUC_MARGIN = 0.10
ACC_MARGIN = 0.05


def rule_of(set_: Sequence[str]) -> str | None:
    """``fusion.rule=labels`` in a variant's ``set`` -> ``labels``."""
    for s in set_:
        k, _, v = s.partition("=")
        if k.strip() == "fusion.rule":
            return v.strip()
    return None


def pair_variants(spec: Any, src: str) -> dict[str, str]:
    """rule -> variant name for the re-fusions of one joined source in an experiment spec."""
    out = {}
    for v in spec.variants:
        if v.refuse_from == src:
            r = rule_of(v.set)
            if r:
                out[r] = v.name
    return out


def same_decisions(rows_x: Sequence[dict[str, Any]], rows_y: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Sanity check: do two row sets (e.g. reader A alone re-fused vs the stored single-reader run) give the
    same label and score on every common call?"""
    y = {r["call_id"]: r for r in rows_y}
    common = [r for r in rows_x if r["call_id"] in y]
    bad = [r["call_id"] for r in common
           if r.get("predicted") != y[r["call_id"]].get("predicted")
           or abs(float(r.get("score") or 0) - float(y[r["call_id"]].get("score") or 0)) > 1e-4]
    return {"n": len(common), "differ": bad, "only_x": len(rows_x) - len(common), "only_y": len(rows_y) - len(common)}


def variant_numbers(rows: dict[str, Any], n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    """Point + 95% CI (twin-group bootstrap) of the reported metrics on the CV rows, AUC on the fixed rows."""
    from callguard import stats

    cv, fixed, far = rows.get("cv") or [], rows.get("fixed") or [], rows.get("cv_far") or []
    lab = stats.labeled(cv)
    return {"auc": stats.bootstrap_auc(fixed, n_boot, seed)["flag"], "cv": stats.bootstrap_ci(cv, n_boot, seed),
            "cv_far": stats.point(far) if far else None,
            "reviews": sum(1 for r in lab if r["predicted"] == "review"),
            "review_hits": sum(1 for r in lab if r["predicted"] == "review" and r["expected"] == "review"),
            "n_review": sum(1 for r in lab if r["expected"] == "review"), "n": len(lab)}


def acceptance(data: dict[str, dict[str, dict[str, Any]]], n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    """The pre-registered verdict. ``data[wording][role]`` = rows.json of the re-fusions, role in
    a / b / labels / facts (wording in PAIRS). Numbers, paired comparisons vs reader A alone on the same
    wording (A on the tuned table = the champion), pass/fail per rule and criterion."""
    from callguard import stats

    nums = {w: {role: variant_numbers(r, n_boot, seed) for role, r in roles.items() if r.get("fixed")}
            for w, roles in data.items()}
    comps: dict[str, dict[str, Any]] = {}
    for w, roles in data.items():
        base = roles.get("a") or {}
        for role in ("b", "labels", "facts"):
            r = roles.get(role) or {}
            if base.get("cv") and r.get("cv"):
                c = stats.compare(base["cv"], r["cv"], n_boot, seed)
                c["auc"] = stats.paired_auc(base["fixed"], r["fixed"], n_boot, seed)
                comps.setdefault(w, {})[role] = c
    verdict: dict[str, Any] = {}
    champ = nums.get("tuned", {}).get("a")
    for rule in ("labels", "facts"):
        crit: dict[str, Any] = {}
        mine = nums.get("tuned", {}).get(rule)
        comp = (comps.get("tuned") or {}).get(rule)
        if champ and mine and comp:
            far_c, far_r = champ["cv"]["false_alarm_rate"]["value"], mine["cv"]["false_alarm_rate"]["value"]
            rr_c, rr_r = champ["cv"]["review_recall"]["value"], mine["cv"]["review_recall"]["value"]
            dacc = comp["paired"]["accuracy"]
            crit["A1"] = {"pass": far_r is not None and far_c is not None and far_r <= far_c + FAR_MARGIN + 1e-9,
                          "text": f"CV FAR {_pc(far_r)} vs champion {_pc(far_c)} (limit {_pc((far_c or 0) + FAR_MARGIN)})"}
            crit["A2"] = {"pass": rr_r is not None and rr_c is not None and rr_r >= rr_c - 1e-9,
                          "text": f"CV review recall {_pc(rr_r)} ({mine['review_hits']}/{mine['n_review']}) vs champion "
                                  f"{_pc(rr_c)} ({champ['review_hits']}/{champ['n_review']})"}
            crit["A3"] = {"pass": dacc["hi"] is not None and dacc["hi"] >= 0,
                          "text": f"CV 3-class acc {_pc(dacc['b'])} vs champion {_pc(dacc['a'])}: diff "
                                  f"{_pp(dacc['diff'])} [{_pp(dacc['lo'])}, {_pp(dacc['hi'])}]"}
        a4 = []
        for w in REWORDED:
            q, me = nums.get(w, {}).get("a"), nums.get(w, {}).get(rule)
            if not (q and me):
                a4.append({"wording": w, "pass": None, "text": f"{w}: not available"})
                continue
            auc_q, auc_r = q["auc"]["value"], me["auc"]["value"]
            acc_q, acc_r = q["cv"]["accuracy"]["value"], me["cv"]["accuracy"]["value"]
            ok_auc = auc_q is not None and auc_r is not None and auc_r >= auc_q + AUC_MARGIN - 1e-9
            ok_acc = acc_q is not None and acc_r is not None and acc_r >= acc_q + ACC_MARGIN - 1e-9
            a4.append({"wording": w, "pass": ok_auc and ok_acc, "auc_pass": ok_auc, "acc_pass": ok_acc,
                       "text": f"{w}: AUC {_f2(auc_r)} vs Qwen {_f2(auc_q)} (need >= {_f2((auc_q or 0) + AUC_MARGIN)}) "
                               f"{'ok' if ok_auc else 'NO'}, CV acc {_pc(acc_r)} vs Qwen {_pc(acc_q)} "
                               f"(need >= {_pc((acc_q or 0) + ACC_MARGIN)}) {'ok' if ok_acc else 'NO'}"})
        crit["A4"] = {"pass": bool(a4) and all(x["pass"] is True for x in a4), "parts": a4,
                      "text": "; ".join(x["text"] for x in a4)}
        verdict[rule] = {"criteria": crit, "pass": all(k in crit and crit[k]["pass"] for k in ("A1", "A2", "A3", "A4"))}
    passing = [r for r in ("labels", "facts") if verdict.get(r, {}).get("pass")]
    if len(passing) == 2:  # pre-registered tie-break: higher tuned CV accuracy, tie -> R1
        accs = {r: nums["tuned"][r]["cv"]["accuracy"]["value"] or 0 for r in passing}
        pick: str | None = "facts" if accs["facts"] > accs["labels"] else "labels"
    else:
        pick = passing[0] if passing else None
    return {"numbers": nums, "comparisons": comps, "verdict": verdict, "recommend": pick}


def _pc(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def _pp(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:+.0f}pp"


def _f2(x: float | None) -> str:
    return "-" if x is None else f"{x:.2f}"


def _cell(c: dict[str, Any] | None, pct: bool = True) -> str:
    if not c or c.get("value") is None:
        return "-"
    f = _pc if pct else _f2
    return f"{f(c['value'])} [{f(c.get('lo'))}, {f(c.get('hi'))}]"


RULE_NAMES = {"a": "Qwen alone", "b": "Kev alone", "labels": "R1 labels", "facts": "R2 facts"}


def _delta(x: dict[str, Any], pct: bool = True) -> str:
    if x.get("diff") is None:
        return "-"
    f = _pp if pct else (lambda v: "-" if v is None else f"{v:+.2f}")
    s = f"{f(x['diff'])} [{f(x.get('lo'))}, {f(x.get('hi'))}]"
    return f"**{s}**" if x.get("real") else s


def render_acceptance(res: dict[str, Any], sanity: dict[str, Any] | None = None) -> str:
    L = ["# Two readers: pre-registered evaluation (dev)", "",
         "Pre-registration: research/findings/two_readers_prereg.md. Metrics on out-of-fold CV rows (threshold per "
         "fold chosen on the other folds); AUC on the fixed-threshold call scores. 95% CIs: 2000 bootstrap "
         "replicates over twin groups. n = 48 calls / 24 dialogues; 6 expected-review calls (1 call = 17 pp of "
         "review recall).", "",
         "| wording | system | flag AUC [CI] | CV flag F1 [CI] | CV FAR [CI] | CV miss [CI] | review recall | "
         "3-class acc [CI] | reviews | CV@FAR20 FAR / recall |", "|---|---|---|---|---|---|---|---|---|---|"]
    for w, roles in res["numbers"].items():
        for role in ("a", "b", "labels", "facts"):
            n = roles.get(role)
            if not n:
                continue
            cv, far20 = n["cv"], n.get("cv_far") or {}
            L.append(f"| {w} | {RULE_NAMES[role]} | {_cell(n['auc'], False)} | {_cell(cv['flag_f1'], False)} | "
                     f"{_cell(cv['false_alarm_rate'])} | {_cell(cv['miss_rate'])} | "
                     f"{_pc(cv['review_recall']['value'])} ({n['review_hits']}/{n['n_review']}) | "
                     f"{_cell(cv['accuracy'])} | {n['reviews']} | "
                     f"{_pc(far20.get('false_alarm_rate'))} / {_pc(far20.get('flag_recall'))} |")
    L += ["", "## Paired vs Qwen alone on the same wording (B - A on CV rows; bold = CI excludes 0)", "",
          "| wording | system | d AUC [CI] | d FAR [CI] | d miss [CI] | d review recall | d 3-class acc [CI] | "
          "McNemar flag (A only / B only, p) | McNemar label | flips |", "|---|---|---|---|---|---|---|---|---|---|"]
    for w, roles in res["comparisons"].items():
        for role, c in roles.items():
            p, mf, ml = c["paired"], c["mcnemar_flag"], c["mcnemar_label"]
            L.append(f"| {w} | {RULE_NAMES[role]} | {_delta(c['auc']['flag'], False)} | {_delta(p['false_alarm_rate'])} | "
                     f"{_delta(p['miss_rate'])} | {_pp(p['review_recall']['diff'])} | {_delta(p['accuracy'])} | "
                     f"{mf['a_only']} / {mf['b_only']}, p={mf['p']} | {ml['a_only']} / {ml['b_only']}, p={ml['p']} | "
                     f"{len(c['flips'])} |")
    L += ["", "## Verdict per pre-registered criterion", ""]
    for rule, v in res["verdict"].items():
        L.append(f"### {RULE_NAMES[rule]}: {'PASS' if v['pass'] else 'FAIL'}")
        for k in ("A1", "A2", "A3", "A4"):
            c = v["criteria"].get(k)
            L.append(f"- {k}: not evaluable" if c is None else f"- {k} {'pass' if c['pass'] else 'FAIL'}: {c['text']}")
        L.append("")
    L.append("Recommendation by the pre-registered tie-break: "
             + (RULE_NAMES[res["recommend"]] if res["recommend"] else "none passes - the champion stays") + ".")
    for role in ("labels", "facts"):
        fl = ((res["comparisons"].get("tuned") or {}).get(role) or {}).get("flips") or []
        if fl:
            L += ["", f"## Flips vs Qwen alone (= champion), tuned table: {RULE_NAMES[role]}", "",
                  "| call | expected | Qwen | rule | flag | label | rule's first reason |", "|---|---|---|---|---|---|---|"]
            L += [f"| {x['call_id']} | {x['expected']} | {x['a']} | {x['b']} | {x['flag_change']} | {x['label_change']} | "
                  f"{(x.get('b_reason') or '')[:140].replace('|', '/')} |" for x in fl]
    if sanity:
        L += ["", "## Sanity: single readers re-fused from the joined source vs the stored runs", ""]
        L += [f"- {k}: {s}" for k, s in sanity.items()]
    return "\n".join(L) + "\n"
