"""Uncertainty for 30 dialogues: bootstrap CIs over dialogues, paired comparisons, McNemar, flip tables.

Definitions (research/AGENT.md):
* flag positive = predicted alarm or review; truth positive = expected alarm or review.
* ``false_alarm_rate`` = FP / expected no_alert, ``miss_rate`` = FN / expected positives.
* ``review_recall`` = expected review -> predicted review. ``accuracy`` = 3-class accuracy.

Resampling unit = twin group (config/splits.yaml ``groups``: the Stufe2 pairs that differ only in
context), else the dialogue; clean + noisy of a dialogue always stay together. Each row is reduced to a
vector of counts once; a bootstrap replicate is then a sum over resampled dialogues, so 2000+
replicates take milliseconds. Differences are always ``B - A`` (variant minus baseline): a positive
F1 difference is good, a positive FAR / miss difference is bad.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

import numpy as np

from callguard.data import dialogue_of
from callguard.splits import group_of
from callguard.types import LABELS

Row = dict[str, Any]
FLAG = ("alarm", "review")

# count vector layout
_C = ["n", "tp", "fp", "fn", "tn", "atp", "afp", "afn", "correct", "rev_n", "rev_hit"]
_I = {k: i for i, k in enumerate(_C)}


def _counts(r: Row) -> np.ndarray:
    e, p = r.get("expected"), r.get("predicted")
    v = np.zeros(len(_C))
    v[_I["n"]] = 1
    ep, pp = e in FLAG, p in FLAG
    v[_I["tp"]], v[_I["fp"]] = ep and pp, (not ep) and pp
    v[_I["fn"]], v[_I["tn"]] = ep and not pp, (not ep) and not pp
    ea, pa = e == "alarm", p == "alarm"
    v[_I["atp"]], v[_I["afp"]], v[_I["afn"]] = ea and pa, (not ea) and pa, ea and not pa
    v[_I["correct"]] = e == p
    v[_I["rev_n"]], v[_I["rev_hit"]] = e == "review", e == "review" and p == "review"
    return v


def _ratio(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(b > 0, a / np.where(b > 0, b, 1), np.nan)


def _col(c: np.ndarray, k: str) -> np.ndarray:
    return c[..., _I[k]]


METRICS: dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "flag_f1": lambda c: _ratio(2 * _col(c, "tp"), 2 * _col(c, "tp") + _col(c, "fp") + _col(c, "fn")),
    "flag_precision": lambda c: _ratio(_col(c, "tp"), _col(c, "tp") + _col(c, "fp")),
    "flag_recall": lambda c: _ratio(_col(c, "tp"), _col(c, "tp") + _col(c, "fn")),
    "false_alarm_rate": lambda c: _ratio(_col(c, "fp"), _col(c, "fp") + _col(c, "tn")),
    "miss_rate": lambda c: _ratio(_col(c, "fn"), _col(c, "tp") + _col(c, "fn")),
    "alarm_f1": lambda c: _ratio(2 * _col(c, "atp"), 2 * _col(c, "atp") + _col(c, "afp") + _col(c, "afn")),
    "review_recall": lambda c: _ratio(_col(c, "rev_hit"), _col(c, "rev_n")),
    "accuracy": lambda c: _ratio(_col(c, "correct"), _col(c, "n")),
}
DIFF_METRICS = ("flag_f1", "alarm_f1", "false_alarm_rate", "miss_rate", "accuracy", "review_recall")
LOWER_IS_BETTER = {"false_alarm_rate", "miss_rate"}


def labeled(rows: Sequence[Row]) -> list[Row]:
    return [r for r in rows if r.get("expected") in LABELS and r.get("predicted") in LABELS]


def _dialogue(r: Row) -> str:
    """Resampling unit: the twin group of config/splits.yaml (Stufe2 pairs that differ only in context),
    else the dialogue. A row may carry its own ``group`` (tests, other splits)."""
    if r.get("group"):
        return r["group"]
    return group_of(r.get("dialogue_id") or dialogue_of(r["call_id"]))


def _by_dialogue(rows: Sequence[Row]) -> tuple[list[str], np.ndarray]:
    """(dialogue ids, counts[dialogue, k])."""
    ids: dict[str, int] = {}
    vecs: list[np.ndarray] = []
    for r in rows:
        d = _dialogue(r)
        if d not in ids:
            ids[d] = len(vecs)
            vecs.append(np.zeros(len(_C)))
        vecs[ids[d]] += _counts(r)
    return list(ids), (np.array(vecs) if vecs else np.zeros((0, len(_C))))


def point(rows: Sequence[Row]) -> dict[str, float | None]:
    """Every metric on the rows as they are (no resampling)."""
    c = sum((_counts(r) for r in labeled(rows)), np.zeros(len(_C)))
    return {k: _clean(float(f(c))) for k, f in METRICS.items()}


def _clean(x: float) -> float | None:
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else round(float(x), 4)


def _resample_index(n_dialogues: int, n_boot: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.integers(0, n_dialogues, size=(n_boot, n_dialogues))


def _ci(samples: np.ndarray, alpha: float) -> tuple[float | None, float | None, int]:
    ok = samples[~np.isnan(samples)]
    if not len(ok):
        return None, None, 0
    lo, hi = np.percentile(ok, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return _clean(float(lo)), _clean(float(hi)), int(len(ok))


def bootstrap_ci(rows: Sequence[Row], n_boot: int = 2000, seed: int = 13, alpha: float = 0.05,
                 metrics: Sequence[str] | None = None) -> dict[str, dict[str, Any]]:
    """Per metric: point value + percentile CI from resampling dialogues with replacement.
    ``n_valid`` = replicates where the metric was defined (e.g. a replicate without harmless calls has
    no false-alarm rate)."""
    rows = labeled(rows)
    _, per = _by_dialogue(rows)
    pt = point(rows)
    out: dict[str, dict[str, Any]] = {}
    if not len(per):
        return {k: {"value": None, "lo": None, "hi": None, "n_valid": 0} for k in metrics or METRICS}
    idx = _resample_index(len(per), n_boot, seed)
    sums = per[idx].sum(axis=1)  # (n_boot, k)
    for k in metrics or METRICS:
        lo, hi, nv = _ci(METRICS[k](sums), alpha)
        out[k] = {"value": pt[k], "lo": lo, "hi": hi, "n_valid": nv}
    return out


def pair_rows(rows_a: Sequence[Row], rows_b: Sequence[Row]) -> list[tuple[Row, Row]]:
    """Rows of both variants for the calls both have (labelled), in A's order."""
    b = {r["call_id"]: r for r in labeled(rows_b)}
    return [(r, b[r["call_id"]]) for r in labeled(rows_a) if r["call_id"] in b]


def paired_bootstrap(rows_a: Sequence[Row], rows_b: Sequence[Row], n_boot: int = 2000, seed: int = 13,
                     alpha: float = 0.05, metrics: Sequence[str] = DIFF_METRICS) -> dict[str, dict[str, Any]]:
    """Difference B - A per metric with a paired percentile CI: each replicate draws the same dialogues
    for both variants. ``real`` = the CI excludes 0 (the protocol's bar for "a difference")."""
    pairs = pair_rows(rows_a, rows_b)
    ra, rb = [a for a, _ in pairs], [b for _, b in pairs]
    ids_a, per_a = _by_dialogue(ra)
    ids_b, per_b = _by_dialogue(rb)
    assert ids_a == ids_b  # same calls in the same order -> same dialogue order
    pa, pb = point(ra), point(rb)
    out: dict[str, dict[str, Any]] = {}
    if not len(per_a):
        return {k: {"a": None, "b": None, "diff": None, "lo": None, "hi": None, "real": False, "n_valid": 0}
                for k in metrics}
    idx = _resample_index(len(per_a), n_boot, seed)
    sa, sb = per_a[idx].sum(axis=1), per_b[idx].sum(axis=1)
    for k in metrics:
        d = METRICS[k](sb) - METRICS[k](sa)
        lo, hi, nv = _ci(d, alpha)
        diff = None if pa[k] is None or pb[k] is None else round(pb[k] - pa[k], 4)
        better = None
        if diff is not None and diff != 0:
            better = "b" if (diff < 0) == (k in LOWER_IS_BETTER) else "a"
        out[k] = {"a": pa[k], "b": pb[k], "diff": diff, "lo": lo, "hi": hi, "n_valid": nv,
                  "real": lo is not None and hi is not None and (lo > 0 or hi < 0), "better": better}
    out["_n"] = {"calls": len(pairs), "units": len(ids_a),  # type: ignore[assignment]
                 "dialogues": len({r.get("dialogue_id") or dialogue_of(r["call_id"]) for r in ra})}
    return out


def binom_two_sided(k: int, n: int) -> float:
    """Exact two-sided p of k successes in n fair-coin trials (doubled smaller tail, capped at 1)."""
    if n == 0:
        return 1.0
    k = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def flag_correct(r: Row) -> bool:
    return (r["expected"] in FLAG) == (r["predicted"] in FLAG)


def label_correct(r: Row) -> bool:
    return r["expected"] == r["predicted"]


def mcnemar(rows_a: Sequence[Row], rows_b: Sequence[Row],
            correct: Callable[[Row], bool] = flag_correct) -> dict[str, Any]:
    """Exact McNemar on per-call correctness. ``a_only`` = calls only A gets right, ``b_only`` = only B.
    Calls, not dialogues, are the unit here (clean and noisy count twice): read it next to the
    dialogue bootstrap, not instead of it."""
    pairs = pair_rows(rows_a, rows_b)
    a_only = sum(1 for a, b in pairs if correct(a) and not correct(b))
    b_only = sum(1 for a, b in pairs if correct(b) and not correct(a))
    both = sum(1 for a, b in pairs if correct(a) and correct(b))
    return {"n": len(pairs), "a_only": a_only, "b_only": b_only, "both": both,
            "neither": len(pairs) - a_only - b_only - both,
            "p": round(binom_two_sided(b_only, a_only + b_only), 4)}


def flips(rows_a: Sequence[Row], rows_b: Sequence[Row]) -> list[dict[str, Any]]:
    """Calls whose label differs between A and B, with both scores and the decisive passage/reason."""
    out = []
    for a, b in pair_rows(rows_a, rows_b):
        if a["predicted"] == b["predicted"]:
            continue
        fa, fb = flag_correct(a), flag_correct(b)
        out.append({
            "call_id": a["call_id"], "expected": a["expected"], "a": a["predicted"], "b": b["predicted"],
            "a_score": a.get("score"), "b_score": b.get("score"),
            "flag_change": "fixed" if fb and not fa else "broken" if fa and not fb else "same",
            "label_change": ("fixed" if label_correct(b) and not label_correct(a)
                             else "broken" if label_correct(a) and not label_correct(b) else "same"),
            "a_reason": a.get("reason"), "b_reason": b.get("reason"),
            "a_passage": a.get("passage"), "b_passage": b.get("passage"),
        })
    return out


def compare(rows_a: Sequence[Row], rows_b: Sequence[Row], n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    """Everything the protocol asks for one A-vs-B comparison on one set of predictions."""
    return {"paired": paired_bootstrap(rows_a, rows_b, n_boot, seed),
            "mcnemar_flag": mcnemar(rows_a, rows_b, flag_correct),
            "mcnemar_label": mcnemar(rows_a, rows_b, label_correct),
            "flips": flips(rows_a, rows_b)}
