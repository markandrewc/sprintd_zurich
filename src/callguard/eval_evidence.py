"""Evidence hit rate: do the passages we show the officer land on the turns the case annotates as evidence?

EVALUATION ONLY. This module reads the labelled scripts (``Skript_mit_Sollbewertung``: ``Belege`` turn ids,
``Keywordstellen``) and stored results; the pipeline never imports it, and nothing computed here is
written back into a result or a config. Dev dialogues only (holdout dialogues are dropped with a warning).

What is measured (per variant, per family, bootstrap CIs over twin groups / dialogues like stats.py):

* population: true flags = calls predicted alarm|review whose expected label is alarm|review. A true
  flag without any passage counts as a miss (nothing to trace) and is listed separately.
* ``hit@1`` / ``hit@3`` / ``hit@all``: the first / any of the first three / any shown passage (in the
  order the officer sees them) overlaps in time with at least one aligned ``Belege`` turn.
* ``dist@1``: when the top passage misses, the gap in seconds to the nearest evidence turn (median).

Alignment (dialect script turn -> ASR segments, no word timings for the script): see
:mod:`callguard.align` (moved there unchanged so the demo can use it without this module).
Validation (:func:`keyword_anchor_check`): every keyword finding of our keyword check whose keyword id
occurs in exactly one turn of the dialogue's ``Keywordstellen`` is an independent anchor; the share of
anchors whose segment is aligned to that turn is the alignment accuracy (pessimistic: a keyword our
check found in another turn than the annotated one also counts as an alignment error). See
research/findings/evidence_hit_rate.md for the numbers and a hand spot check of 10 alignments.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from callguard.align import (  # noqa: F401  (re-exported: the evaluation's public names stay as they were)
    MATCH_RATIO,
    W_POS,
    W_ROLE,
    W_SIM,
    W_SKIP,
    Alignment,
    TurnSpan,
    align,
    content_tokens,
    similarity,
)
from callguard.data import Call, dialogue_of
from callguard.eval_asr import parse_keyword_spots
from callguard.misheard import (
    DEFAULT_THRESHOLD,
    bottom_quantile,
    is_misheard,
    passage_confidence,
)
from callguard.splits import group_of
from callguard.types import CallResult, Passage

log = logging.getLogger(__name__)

FLAG = ("alarm", "review")
PAD = 2.0  # snippets.pad: the officer hears every passage with 2 s of context on each side
DEFAULT_VARIANTS = ("kev_vs_facts/champion", "kev_vs_facts/kev_facts", "kev_vs_facts/kev_general")

# --------------------------------------------------------------------------------------------
# hits
# --------------------------------------------------------------------------------------------


def gap(a0: float, a1: float, b0: float, b1: float) -> float:
    """Seconds between two intervals (0 when they overlap or touch)."""
    return max(0.0, b0 - a1, a0 - b1)


def _nearest(p: Passage, spans: Sequence[TurnSpan]) -> float | None:
    return min((gap(p.start, p.end, s.start, s.end) for s in spans), default=None)


def chance_hit(length: float, spans: Sequence[TurnSpan], t0: float, t1: float, steps: int = 400) -> float | None:
    """Probability that an interval of ``length`` s placed uniformly at random in [t0, t1] overlaps one of
    ``spans``: the hit rate a passage of the same length would get by luck."""
    if not spans or t1 <= t0:
        return None
    room = max(t1 - t0 - length, 0.0)
    starts = [t0 + room * k / (steps - 1) for k in range(steps)] if room > 0 else [t0]
    return sum(any(gap(a, a + length, s.start, s.end) <= 0.0 for s in spans) for a in starts) / len(starts)


def call_row(result: CallResult, call: Call, alignment: Alignment | None = None,
             misheard_below: float | None = DEFAULT_THRESHOLD) -> dict[str, Any]:
    """One row per call: labels, passages (time, family, ASR confidence) and evidence hits."""
    exp = call.expected
    d = result.decision
    al = alignment or align(call.turns, result.transcript.segments)
    ev = [al.spans[t] for t in (exp.evidence_turns if exp else []) if t in al.spans]
    passages = d.passages
    dists = [_nearest(p, ev) for p in passages]
    hits = [x is not None and x <= 0.0 for x in dists]
    confs = [passage_confidence(result.transcript, p)[0] for p in passages]
    return {
        "call_id": result.call_id, "dialogue_id": call.dialogue_id, "group": group_of(call.dialogue_id),
        "family": exp.family if exp else "", "expected": exp.label if exp else None, "predicted": d.label,
        "noisy": call.noisy, "evidence_turns": list(exp.evidence_turns) if exp else [],
        "evidence": [{"turn": s.turn, "start": round(s.start, 2), "end": round(s.end, 2), "aligned": s.aligned}
                     for s in ev],
        "passages": [{"start": p.start, "end": p.end, "family": p.family, "score": p.score,
                      "asr_confidence": None if c is None else round(c, 4),
                      "misheard": is_misheard(c, misheard_below)} for p, c in zip(passages, confs)],
        "n_passages": len(passages),
        "hit1": bool(hits[:1] and hits[0]), "hit3": any(hits[:3]), "hit_all": any(hits),
        "hit1_pad": bool(dists[:1] and dists[0] is not None and dists[0] <= PAD),
        "dist1": None if not dists or hits[0] or dists[0] is None else round(dists[0], 2),
        "family_match1": bool(passages) and passages[0].family == (exp.family if exp else None),
        "len1": round(passages[0].end - passages[0].start, 2) if passages else None,
        "chance1": (None if not passages or not al.segments else
                    chance_hit(passages[0].end - passages[0].start, ev, al.segments[0].start, al.segments[-1].end)),
    }


def true_flags(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r["predicted"] in FLAG and r["expected"] in FLAG]


def boot_rate(rows: Sequence[dict[str, Any]], key: str, n_boot: int = 2000, seed: int = 13,
              alpha: float = 0.05) -> dict[str, Any]:
    """Share of rows with ``row[key]`` true + percentile CI resampling twin groups / dialogues."""
    k = sum(bool(r[key]) for r in rows)
    n = len(rows)
    out: dict[str, Any] = {"k": k, "n": n, "value": round(k / n, 4) if n else None, "lo": None, "hi": None}
    if not n:
        return out
    units: dict[str, list[int]] = {}
    for r in rows:
        u = units.setdefault(r.get("group") or r["dialogue_id"], [0, 0])
        u[0] += bool(r[key])
        u[1] += 1
    kn = np.array(list(units.values()), dtype=float)
    idx = np.random.default_rng(seed).integers(0, len(kn), size=(n_boot, len(kn)))
    s = kn[idx].sum(axis=1)
    rate = s[:, 0] / s[:, 1]
    lo, hi = np.percentile(rate, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    out.update(lo=round(float(lo), 4), hi=round(float(hi), 4), units=len(kn))
    return out


def summarize(rows: Sequence[dict[str, Any]], n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    """Hit rates over the true flags, overall and per expected family."""
    tf = true_flags(rows)

    def block(rs: Sequence[dict[str, Any]]) -> dict[str, Any]:
        d = [r["dist1"] for r in rs if r["dist1"] is not None]
        ch = [r["chance1"] for r in rs if r.get("chance1") is not None]
        ln = [r["len1"] for r in rs if r.get("len1") is not None]
        return {"n": len(rs), "no_passage": sum(r["n_passages"] == 0 for r in rs),
                # luck baseline: same-length top passage at a random place (mean over calls with a passage)
                "chance1": round(sum(ch) / len(ch), 3) if ch else None,
                "median_len1": round(statistics.median(ln), 1) if ln else None,
                **{k: boot_rate(rs, k, n_boot, seed) for k in ("hit1", "hit1_pad", "hit3", "hit_all",
                                                                 "family_match1")},
                "median_dist1": round(statistics.median(d), 1) if d else None, "n_dist1": len(d)}

    fams = sorted({r["family"] for r in tf})
    return {"all": block(tf), "families": {f: block([r for r in tf if r["family"] == f]) for f in fams},
            "n_calls": len(rows), "n_flagged": sum(r["predicted"] in FLAG for r in rows)}


# --------------------------------------------------------------------------------------------
# alignment validation
# --------------------------------------------------------------------------------------------


def keyword_anchor_check(result: CallResult, call: Call, alignment: Alignment) -> list[dict[str, Any]]:
    """Keyword findings whose keyword id sits in exactly one annotated turn: was the finding's segment
    aligned to that turn (``exact``) or a neighbour (``near``, +-1 turn)?"""
    if not call.expected:
        return []
    spots = parse_keyword_spots(call.expected.keyword_spots)
    by_id: dict[str, set[str]] = {}
    for sp in spots:
        by_id.setdefault(sp.keyword_id, set()).add(sp.turn)
    order = {t.id: k for k, t in enumerate(alignment.turns)}
    out = []
    for cr in result.checks.values():
        if cr.type != "keywords":
            continue
        for f in cr.findings:
            kid = (f.detail or {}).get("keyword_id")
            turns = by_id.get(kid or "")
            if not turns or len(turns) != 1 or not f.segment_ids:
                continue
            want = next(iter(turns))
            got = alignment.turn_of(f.segment_ids[0])
            if got is None or want not in order:
                continue
            out.append({"call_id": result.call_id, "keyword_id": kid, "want": want, "got": got,
                        "exact": got == want, "near": abs(order[got] - order[want]) <= 1})
    return out


def spot_check_lines(result: CallResult, call: Call, alignment: Alignment, turn_ids: Sequence[str]) -> list[str]:
    """Human-readable script turn vs aligned ASR text, for the hand spot check."""
    by_id = {t.id: t for t in alignment.turns}
    seg = {s.id: s for s in alignment.segments}
    lines = []
    for t in turn_ids:
        sp = alignment.spans.get(t)
        if t not in by_id or sp is None:
            continue
        asr = " ".join(seg[i].text.strip() for i in sp.segment_ids)
        lines.append(f"{result.call_id} {t} [{sp.start:.1f}-{sp.end:.1f}s{'' if sp.aligned else ', interpoliert'}]"
                     f"\n  SKRIPT: {by_id[t].text}\n  ASR:    {asr or '(kein Segment)'}")
    return lines


# --------------------------------------------------------------------------------------------
# misheard analysis
# --------------------------------------------------------------------------------------------


def fisher_exact(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p for [[a, b], [c, d]]."""
    n = a + b + c + d
    r1, c1 = a + b, a + c

    def pr(x: int) -> float:
        return math.comb(c1, x) * math.comb(n - c1, r1 - x) / math.comb(n, r1)

    p0 = pr(a)
    lo, hi = max(0, r1 + c1 - n), min(r1, c1)
    return min(1.0, sum(pr(x) for x in range(lo, hi + 1) if pr(x) <= p0 * (1 + 1e-9)))


def misheard_table(rows: Sequence[dict[str, Any]], top: int = 1) -> dict[str, Any]:
    """Flagged calls with passages: is the decision wrong (3-class label != expected) more often when one of
    its top ``top`` passages is flagged «möglicherweise verhört»? Also the flag-level view (false flag =
    expected no_alert)."""
    flagged = [r for r in rows if r["predicted"] in FLAG and r["n_passages"] and r["expected"] is not None]

    def low(r: dict[str, Any]) -> bool:
        return any(p["misheard"] for p in r["passages"][:top])

    out: dict[str, Any] = {"top": top, "n": len(flagged)}
    for name, wrong in (("label", lambda r: r["predicted"] != r["expected"]),
                        ("flag", lambda r: r["expected"] not in FLAG)):
        t = {"wrong_low": sum(wrong(r) and low(r) for r in flagged),
             "wrong_ok": sum(wrong(r) and not low(r) for r in flagged),
             "right_low": sum(not wrong(r) and low(r) for r in flagged),
             "right_ok": sum(not wrong(r) and not low(r) for r in flagged)}
        nw, nr = t["wrong_low"] + t["wrong_ok"], t["right_low"] + t["right_ok"]
        t["p_low_wrong"] = round(t["wrong_low"] / nw, 3) if nw else None
        t["p_low_right"] = round(t["right_low"] / nr, 3) if nr else None
        t["fisher_p"] = round(fisher_exact(t["wrong_low"], t["wrong_ok"], t["right_low"], t["right_ok"]), 3)
        out[name] = t
    return out


def passage_stats(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    ps = [p for r in rows if r["predicted"] in FLAG for p in r["passages"]]
    top = [r["passages"][0] for r in rows if r["predicted"] in FLAG and r["passages"]]
    return {"passages": len(ps), "misheard": sum(p["misheard"] for p in ps),
            "top_passages": len(top), "top_misheard": sum(p["misheard"] for p in top)}


# --------------------------------------------------------------------------------------------
# runner
# --------------------------------------------------------------------------------------------


@dataclass
class VariantEval:
    name: str
    rows: list[dict[str, Any]]
    summary: dict[str, Any]
    anchors: list[dict[str, Any]]
    misheard: dict[str, Any]
    dropped_holdout: list[str] = field(default_factory=list)


def evaluate_variant(name: str, results: Sequence[CallResult], calls: Sequence[Call], *,
                     holdout: Iterable[str] = (), misheard_below: float | None = DEFAULT_THRESHOLD,
                     n_boot: int = 2000, seed: int = 13) -> VariantEval:
    by_id = {c.call_id: c for c in calls}
    hold = set(holdout)
    rows, anchors, dropped = [], [], []
    for res in results:
        call = by_id.get(res.call_id)
        if call is None or call.expected is None or not call.turns:
            continue
        if dialogue_of(res.call_id) in hold:
            dropped.append(res.call_id)
            continue
        al = align(call.turns, res.transcript.segments)
        rows.append(call_row(res, call, al, misheard_below))
        anchors.extend(keyword_anchor_check(res, call, al))
    if dropped:
        log.warning("%s: %d holdout calls ignored (dev only)", name, len(dropped))
    mh = {"threshold": misheard_below, "passages": passage_stats(rows),
          "top1": misheard_table(rows, 1), "top3": misheard_table(rows, 3)}
    return VariantEval(name, rows, summarize(rows, n_boot, seed), anchors, mh, dropped)


def dev_threshold(results: Iterable[CallResult], q: float = 0.1) -> float | None:
    """Label-free: the ``q`` quantile of every segment confidence in the given results."""
    return bottom_quantile(s.confidence for r in results for s in r.transcript.segments)


def anchor_summary(anchors: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(anchors)
    return {"n": n, "exact": sum(a["exact"] for a in anchors), "near": sum(a["near"] for a in anchors),
            "exact_rate": round(sum(a["exact"] for a in anchors) / n, 3) if n else None,
            "near_rate": round(sum(a["near"] for a in anchors) / n, 3) if n else None}


# --------------------------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------------------------


def _pct(b: dict[str, Any]) -> str:
    if b.get("value") is None:
        return "–"
    ci = f" [{b['lo'] * 100:.0f}–{b['hi'] * 100:.0f}]" if b.get("lo") is not None else ""
    return f"{b['value'] * 100:.0f}%{ci} ({b['k']}/{b['n']})"


def _num(x: float | None, pct: bool = False) -> str:
    if x is None:
        return "–"
    return f"{x * 100:.0f}%" if pct else f"{x:.1f}"


def _table(header: list[str], body: list[list[Any]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "---|" * len(header),
            *("| " + " | ".join(str(c) for c in row) + " |" for row in body)]


def render_markdown(evals: Sequence[VariantEval], dev_thr: float | None) -> str:
    out = ["# Evidence hit rate (dev)", "",
           "True flags (predicted alarm|review, expected alarm|review). Hit = passage overlaps an aligned "
           "`Belege` turn in time. 95% bootstrap CIs over twin groups / dialogues. Small n: read the CIs.", ""]
    body = []
    for ev in evals:
        a = ev.summary["all"]
        body.append([ev.name, a["n"], a["no_passage"], _pct(a["hit1"]), _pct(a["hit1_pad"]), _pct(a["hit3"]),
                     _pct(a["hit_all"]),
                     _num(a["chance1"], pct=True), _num(a["median_len1"]), _num(a["median_dist1"]), a["n_dist1"]])
    out += _table(["variant", "true flags", "no passage", "hit@1", "hit@1 ±2 s", "hit@3", "hit@all", "chance@1",
                   "median top-passage s", "median miss s @1", "misses @1 w/ dist"], body)
    out += ["", "hit@1 ±2 s = the top passage's snippet as played (2 s context each side) reaches an evidence "
                "turn. chance@1 = mean probability that a top passage of the same length, placed at a random point "
                "of the call, overlaps an evidence turn (what luck would give)."]
    for ev in evals:
        out += ["", f"## {ev.name}: per family", ""]
        body = []
        for f, b in ev.summary["families"].items():
            body.append([f, b["n"], b["no_passage"], _pct(b["hit1"]), _pct(b["hit3"]), _num(b["chance1"], pct=True),
                         _num(b["median_dist1"])])
        out += _table(["family", "true flags", "no passage", "hit@1", "hit@3", "chance@1", "median miss s @1"],
                      body)
    anchors = [a for ev in evals[:1] for a in ev.anchors]
    s = anchor_summary(anchors)
    out += ["", "## Alignment check (keyword anchors, first variant's transcripts)", "",
            f"{s['n']} keyword findings whose keyword id has exactly one annotated turn: aligned to that turn "
            f"{s['exact']}/{s['n']} ({(s['exact_rate'] or 0) * 100:.0f}%), within ±1 turn {s['near']}/{s['n']} "
            f"({(s['near_rate'] or 0) * 100:.0f}%)."]
    out += ["", "## «Möglicherweise verhört» vs wrong decisions", "",
            f"Threshold {evals[0].misheard['threshold'] if evals else '–'} (label-free dev p10 of segment "
            f"confidences; recomputed on these transcripts: {dev_thr:.3f})." if dev_thr is not None else ""]
    for ev in evals:
        ps = ev.misheard["passages"]
        out += ["", f"### {ev.name}", "",
                f"{ps['misheard']}/{ps['passages']} shown passages flagged, {ps['top_misheard']}/{ps['top_passages']} "
                "top passages."]
        for top in ("top1", "top3"):
            t = ev.misheard[top]
            for kind in ("label", "flag"):
                c = t[kind]
                out += ["", f"{top}, wrong = {'3-class label wrong' if kind == 'label' else 'false flag (expected no_alert)'}"
                            f" (n = {t['n']} flagged calls with passages):", ""]
                out += _table(["", "low-confidence passage", "no low-confidence passage", "share low"],
                              [["wrong", c["wrong_low"], c["wrong_ok"], c["p_low_wrong"]],
                               ["right", c["right_low"], c["right_ok"], c["p_low_right"]]])
                out.append(f"\nFisher exact p = {c['fisher_p']}")
    return "\n".join(out) + "\n"


def load_variant(root: Path, ref: str) -> list[CallResult]:
    from callguard.experiments import load_results

    return load_results(root / ref)
