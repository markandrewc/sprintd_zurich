"""Fitting the data-driven fusions on stored check results, and evaluating them honestly.

Three kinds of fitted model, each a small JSON file (``runs/fusion/<name>.json``):

* ``calibrated`` (A5, :mod:`callguard.fusion.calibrated`): Platt scaling per (check, family) of the raw
  check score -> P(this call is an alarm of this family); a family needs ``min_pos`` positive and
  ``min_neg`` negative calls of its own, otherwise the check's pooled fit over all families is used. Per
  family the calibrated probabilities are pooled in log-odds (weighted by the check weights) and that
  pool is Platt-scaled once more (2 parameters, all families). Call probability ``q`` = max over the
  families that may alarm. Split-conformal prediction sets (LAC score ``1 - p(true label)``) over
  ``labels: 3`` (default; a small softmax on ``[1, z, z^2/10]``, ``z = logit(q)``, gives p(no_alert /
  review / alarm)) or ``labels: 2`` (alarm vs no_alert read off ``q``; a review-labelled calibration call
  counts as covered by either label). The conformal scores come from out-of-fold fits over the training
  folds (cross-conformal), never from the data the scorer saw. Warning: with 3 labels and a review class
  that is more frequent than ``alpha`` but not separable from the others, review is in almost every set
  and almost every call becomes review; ``labels: 2`` then gives a usable "review if both plausible" band.
* ``learned`` (:mod:`callguard.fusion.learned`): one L2 logistic regression over (call, family) rows,
  features = the weighted fusion's family score and uncertainty plus every check's score and a
  "check gave no score" indicator, standardized. -> per-family probability; call = max.
* ``thresholds`` (N2): per-family alarm thresholds for the weighted fusion at a fixed family-level
  false-positive rate over cross-family negatives (every (call, other family) pair is a negative).

Targets: a (call, family) row is 1 when the call's expected label is alarm and its expected family is
this family, ``review_target`` (default 0.5) when the expected label is review for this family, else 0.
Ground truth is read only here (fitting), never by the fusion at decision time.

Honest evaluation: :func:`nested_cv` fits on the other dev folds only, picks the threshold on
out-of-fold predictions inside those folds, then predicts the held-out fold. Calls outside the dev
folds (holdout, synthetic) are never used. Rows come out in the experiment runner's format
(``experiments.result_row`` + ``cv_fold`` / ``cv_threshold``) so :mod:`callguard.stats` can pair them with
the weighted fusion's CV rows.

Everything is numpy (Newton steps on tiny problems); no scikit-learn.
"""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from callguard.data import Call, dialogue_of
from callguard.fusion.weighted import RULE_CHECKS, WeightedFusion, _band_floor, _num
from callguard.types import LABELS, CallResult, CheckResult, Decision, Family

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard")

KINDS = ("calibrated", "learned", "thresholds")
CLASSES = ("no_alert", "review", "alarm")  # ordinal order for the class model
EPS = 1e-4
Row = dict[str, Any]


# --------------------------------------------------------------------------------------------
# numerics
# --------------------------------------------------------------------------------------------


def sigmoid(z: Any) -> Any:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35.0, 35.0)))


def logit(p: Any, eps: float = EPS) -> Any:
    p = np.clip(p, eps, 1.0 - eps)
    return np.log(p / (1.0 - p))


def fit_logreg(X: np.ndarray, y: np.ndarray, l2: float | np.ndarray = 1.0, sample_weight: np.ndarray | None = None,
               iters: int = 100, tol: float = 1e-9) -> np.ndarray:
    """Binary logistic regression with soft targets ``y`` in [0, 1] and per-coefficient L2 penalty
    (``l2`` scalar or vector; put 0 for an unpenalized intercept). Newton-Raphson (IRLS); a tiny ridge
    keeps separable data finite."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n, d = X.shape
    w = np.ones(n) if sample_weight is None else np.asarray(sample_weight, float)
    lam = np.broadcast_to(np.asarray(l2, float), (d,)) + 1e-6
    beta = np.zeros(d)
    for _ in range(iters):
        p = sigmoid(X @ beta)
        grad = X.T @ (w * (p - y)) + lam * beta
        H = (X * (w * p * (1 - p))[:, None]).T @ X + np.diag(lam)
        step = np.linalg.solve(H, grad)
        beta -= step
        if np.max(np.abs(step)) < tol:
            break
    return beta


def fit_softmax(X: np.ndarray, Y: np.ndarray, l2: float | np.ndarray = 1.0, iters: int = 100,
                tol: float = 1e-9) -> np.ndarray:
    """Multinomial logistic regression, ``Y`` one-hot (or soft) n x K, returns W (K x d). Newton on all
    K*d coefficients; the L2 penalty (plus a tiny ridge) makes the over-parameterized softmax
    identifiable. Classes absent from ``Y`` simply get low probability."""
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    n, d = X.shape
    K = Y.shape[1]
    lam = np.tile(np.broadcast_to(np.asarray(l2, float), (d,)) + 1e-6, K)
    W = np.zeros((K, d))
    for _ in range(iters):
        P = softmax(X @ W.T)
        G = ((P - Y).T @ X).reshape(-1) + lam * W.reshape(-1)
        H = np.zeros((K * d, K * d))
        for i in range(n):
            p = P[i]
            H += np.kron(np.diag(p) - np.outer(p, p), np.outer(X[i], X[i]))
        H += np.diag(lam)
        step = np.linalg.solve(H, G)
        W -= step.reshape(K, d)
        if np.max(np.abs(step)) < tol:
            break
    return W


def softmax(Z: np.ndarray) -> np.ndarray:
    Z = Z - Z.max(axis=-1, keepdims=True)
    E = np.exp(Z)
    return E / E.sum(axis=-1, keepdims=True)


def platt_targets(y: np.ndarray) -> np.ndarray:
    """Platt's (1999) prior correction of hard 0/1 targets: (N+ + 1)/(N+ + 2) and 1/(N- + 2). Keeps a
    perfectly separating score (a keyword hit) from getting an infinite slope; soft targets stay."""
    y = np.asarray(y, float)
    n_pos, n_neg = float(np.sum(y >= 1.0)), float(np.sum(y <= 0.0))
    hi, lo = (n_pos + 1) / (n_pos + 2), 1.0 / (n_neg + 2)
    return np.where(y >= 1.0, hi, np.where(y <= 0.0, lo, y))


def platt_fit(s: Sequence[float], y: Sequence[float], l2: float = 0.01) -> tuple[float, float]:
    """``p = sigmoid(a * s + b)``; returns (a, b)."""
    s = np.asarray(s, float)
    X = np.column_stack([np.ones_like(s), s])
    b, a = fit_logreg(X, platt_targets(np.asarray(y, float)), l2=np.array([0.0, l2]))
    return float(a), float(b)


def conformal_qhat(scores: Sequence[float], alpha: float) -> float:
    """Split-conformal quantile: the ceil((n+1)(1-alpha))-th smallest nonconformity score (1.0 = every
    label is plausible, when there are too few calibration points for this alpha)."""
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    if n == 0:
        return 1.0
    k = math.ceil((n + 1) * (1 - alpha))
    return 1.0 if k > n else float(s[k - 1])


# --------------------------------------------------------------------------------------------
# features: what a fitted fusion sees of one call
# --------------------------------------------------------------------------------------------


@dataclass
class CallFeatures:
    call_id: str
    fams: list[str]  # families that may alarm, config order
    scores: dict[str, dict[str, float]] = field(default_factory=dict)  # family -> check -> raw score
    confs: dict[str, dict[str, float]] = field(default_factory=dict)
    fused: dict[str, tuple[float, float]] = field(default_factory=dict)  # family -> weighted (score, unc)

    @property
    def dialogue(self) -> str:
        return dialogue_of(self.call_id)


def usable_checks(results: Mapping[str, CheckResult], weights: Mapping[str, float],
                  disabled: set[str] | frozenset[str] = frozenset()) -> dict[str, CheckResult]:
    """As in WeightedFusion.decide: not disabled, not failed, weight > 0."""
    return {n: r for n, r in results.items()
            if n not in disabled and not r.meta.get("error") and (_num(weights.get(n, 1.0)) or 0.0) > 0}


def call_features(call_id: str, results: Mapping[str, CheckResult], families: Sequence[Family],
                  base_decision: Decision, usable: Mapping[str, CheckResult]) -> CallFeatures:
    fams = [f.id for f in families if f.enabled and f.can_alarm]
    cf = CallFeatures(call_id=call_id, fams=fams)
    for fid in fams:
        cf.scores[fid], cf.confs[fid] = {}, {}
        for name, r in usable.items():
            fs = r.family_scores.get(fid)
            s = _num(fs.score) if fs is not None else None
            if s is None:
                continue
            cf.scores[fid][name] = min(1.0, max(0.0, s))
            c = _num(fs.confidence)
            cf.confs[fid][name] = 1.0 if c is None else min(1.0, max(0.0, c))
        ff = base_decision.families.get(fid)
        cf.fused[fid] = (float(ff.score), float(ff.uncertainty)) if ff else (0.0, 1.0)
    return cf


def features_of(base: WeightedFusion, result: CallResult, families: Sequence[Family],
                weights: Mapping[str, float]) -> CallFeatures:
    dec = base.decide(result.transcript, result.checks, list(families), {"weights": dict(weights)})
    return call_features(result.call_id, result.checks, families, dec, usable_checks(result.checks, weights))


# --------------------------------------------------------------------------------------------
# targets (ground truth: fitting only)
# --------------------------------------------------------------------------------------------


Truth = Mapping[str, Call]


def family_target(call: Call | None, fid: str, review_target: float) -> float | None:
    if call is None or call.expected is None or call.expected.label not in LABELS:
        return None
    if call.expected.family != fid:
        return 0.0
    return {"alarm": 1.0, "review": review_target}.get(call.expected.label, 0.0)


def call_class(call: Call | None) -> str | None:
    return call.expected.label if call is not None and call.expected is not None else None


def _labeled(feats: Sequence[CallFeatures], truth: Truth) -> list[CallFeatures]:
    return [f for f in feats if call_class(truth.get(f.call_id)) in LABELS]


# --------------------------------------------------------------------------------------------
# calibrated (A5)
# --------------------------------------------------------------------------------------------


def _fit_cal_core(feats: Sequence[CallFeatures], truth: Truth, *, checks: Sequence[str], weights: Mapping[str, float],
                  review_target: float, min_pos: int, min_neg: int, l2_platt: float, l2_class: float,
                  labels: int = 3) -> dict[str, Any]:
    platt: dict[str, dict[str, list[float]]] = {}
    for c in checks:
        pts: dict[str, list[tuple[float, float]]] = {}
        for f in feats:
            for fid in f.fams:
                y = family_target(truth.get(f.call_id), fid, review_target)
                if y is None or c not in f.scores[fid]:
                    continue
                pts.setdefault(fid, []).append((f.scores[fid][c], y))
        allp = [p for v in pts.values() for p in v]
        if not allp:
            continue
        platt[c] = {"_pooled": list(platt_fit([s for s, _ in allp], [y for _, y in allp], l2_platt))}
        for fid, v in pts.items():
            n_pos = sum(1 for _, y in v if y >= 1.0)
            n_neg = sum(1 for _, y in v if y <= 0.0)
            if n_pos >= min_pos and n_neg >= min_neg:
                platt[c][fid] = list(platt_fit([s for s, _ in v], [y for _, y in v], l2_platt))
    core: dict[str, Any] = {"checks": list(checks), "weights": {c: float(weights.get(c, 1.0)) for c in checks},
                            "platt": platt, "pool": [1.0, 0.0]}
    # second stage: one Platt on the pooled log-odds, over every (call, family) row
    Ls, ys = [], []
    for f in feats:
        for fid in f.fams:
            y = family_target(truth.get(f.call_id), fid, review_target)
            if y is not None:
                Ls.append(_pooled_logit(core, f, fid))
                ys.append(y)
    if Ls:
        core["pool"] = list(platt_fit(Ls, ys, l2_platt))
    # 3-label class model on z = logit(q): softmax over [1, z, z^2] (the square lets review own the middle)
    X, Y = [], []
    for f in _labeled(feats, truth) if labels == 3 else []:
        q, _, _ = cal_call_prob(core, f)
        X.append(_class_x(q))
        Y.append([1.0 if call_class(truth[f.call_id]) == k else 0.0 for k in CLASSES])
    if X:
        core["softmax"] = fit_softmax(np.array(X), np.array(Y), l2=np.array([0.01, l2_class, l2_class])).tolist()
    return core


def _class_x(q: float) -> list[float]:
    z = float(logit(q))
    return [1.0, z, z * z / 10.0]


def cal_check_prob(model: Mapping[str, Any], check: str, fid: str, score: float) -> float | None:
    p = (model.get("platt") or {}).get(check)
    if not p:
        return None
    a, b = p.get(fid) or p["_pooled"]
    return float(sigmoid(a * score + b))


def cal_check_probs(model: Mapping[str, Any], f: CallFeatures, fid: str) -> dict[str, float]:
    out = {}
    for c, s in f.scores.get(fid, {}).items():
        p = cal_check_prob(model, c, fid, s)
        if p is not None:
            out[c] = p
    return out


def _pooled_logit(model: Mapping[str, Any], f: CallFeatures, fid: str) -> float:
    probs = cal_check_probs(model, f, fid)
    if not probs:
        return 0.0
    w = model.get("weights") or {}
    ws = np.array([max(float(w.get(c, 1.0)), 1e-6) for c in probs])
    return float(np.sum(ws * logit(np.array(list(probs.values())))) / np.sum(ws))


def cal_family_prob(model: Mapping[str, Any], f: CallFeatures, fid: str) -> float:
    a0, b0 = model.get("pool") or (1.0, 0.0)
    return float(sigmoid(a0 * _pooled_logit(model, f, fid) + b0))


def cal_call_prob(model: Mapping[str, Any], f: CallFeatures) -> tuple[float, str | None, dict[str, float]]:
    probs = {fid: cal_family_prob(model, f, fid) for fid in f.fams}
    if not probs:
        return 0.0, None, probs
    top = max(f.fams, key=lambda fid: (probs[fid], f.fused[fid][0]))
    return probs[top], top, probs


def class_probs(model: Mapping[str, Any], q: float) -> dict[str, float]:
    W = model.get("softmax")
    if not W:  # 2-label mode (or no class model): alarm vs no_alert read straight off q
        return {"no_alert": 1.0 - q, "review": 0.0, "alarm": q}
    p = softmax(np.array(W) @ np.array(_class_x(q)))
    return {k: float(v) for k, v in zip(CLASSES, p)}


def set_labels(model: Mapping[str, Any]) -> tuple[str, ...]:
    """The labels a prediction set ranges over: all three, or alarm / no_alert (``labels: 2``)."""
    return LABELS if int((model.get("conformal") or {}).get("labels", 3)) == 3 else ("alarm", "no_alert")


def nonconformity(model: Mapping[str, Any], q: float, label: str) -> float:
    """LAC score ``1 - p(true label)``. In 2-label mode a review call is covered by either label (its
    score is the smaller one): "a human should look" is compatible with both."""
    cp = class_probs(model, q)
    if label not in set_labels(model):
        return min(1.0 - cp[k] for k in set_labels(model))
    return 1.0 - cp[label]


def prediction_set(model: Mapping[str, Any], probs: Mapping[str, float], alpha: float | None = None) -> list[str]:
    """Labels whose nonconformity ``1 - p`` is within the conformal quantile, in LABELS order."""
    conf = model.get("conformal") or {}
    a = float(alpha if alpha is not None else conf.get("alpha", 0.1))
    qhat = conformal_qhat(conf.get("scores") or [], a)
    return [k for k in set_labels(model) if 1.0 - probs[k] <= qhat + 1e-12]


def fit_calibrated(feats: Sequence[CallFeatures], truth: Truth, fold_of: Mapping[str, int] | None = None, *,
                   checks: Sequence[str], weights: Mapping[str, float], alpha: float = 0.1,
                   review_target: float = 0.5, min_pos: int = 4, min_neg: int = 4, l2_platt: float = 0.01,
                   l2_class: float = 1.0, labels: int = 3, **_: Any) -> dict[str, Any]:
    if labels not in (2, 3):
        raise ValueError(f"labels must be 2 or 3, got {labels!r}")
    kw = dict(checks=checks, weights=weights, review_target=review_target, min_pos=min_pos, min_neg=min_neg,
              l2_platt=l2_platt, l2_class=l2_class, labels=labels)
    mode = {"labels": labels}
    lab = _labeled(feats, truth)
    model = _fit_cal_core(lab, truth, **kw)
    folds = sorted({fold_of[f.dialogue] for f in lab if f.dialogue in fold_of}) if fold_of else []
    scores: list[float] = []
    if len(folds) >= 2:  # cross-conformal: every score from a scorer that did not see that fold
        for j in folds:
            inner = _fit_cal_core([f for f in lab if fold_of.get(f.dialogue) != j], truth, **kw)  # type: ignore[union-attr]
            for f in lab:
                if fold_of.get(f.dialogue) == j:  # type: ignore[union-attr]
                    q, _, _ = cal_call_prob(inner, f)
                    scores.append(nonconformity({**inner, "conformal": mode}, q, call_class(truth[f.call_id])))  # type: ignore[arg-type]
        source = f"out-of-fold over {len(folds)} training folds (cross-conformal)"
    else:
        for f in lab:
            q, _, _ = cal_call_prob(model, f)
            scores.append(nonconformity({**model, "conformal": mode}, q, call_class(truth[f.call_id])))  # type: ignore[arg-type]
        source = "in-sample (only one fold: optimistic, sets too small)"
    model["conformal"] = {"alpha": alpha, "labels": labels, "scores": sorted(round(s, 6) for s in scores),
                          "source": source, "n": len(scores)}
    model["options"] = {**{k: v for k, v in kw.items() if k not in ("checks", "weights")}}
    return model


# --------------------------------------------------------------------------------------------
# learned
# --------------------------------------------------------------------------------------------


def learned_feature_names(checks: Sequence[str]) -> list[str]:
    return ["fused_score", "fused_uncertainty", *(f"score:{c}" for c in checks), *(f"missing:{c}" for c in checks)]


def learned_row(f: CallFeatures, fid: str, checks: Sequence[str]) -> list[float]:
    s, u = f.fused[fid]
    sc = f.scores.get(fid, {})
    return [s, u, *(sc.get(c, 0.0) for c in checks), *(0.0 if c in sc else 1.0 for c in checks)]


def fit_learned(feats: Sequence[CallFeatures], truth: Truth, fold_of: Mapping[str, int] | None = None, *,
                checks: Sequence[str], weights: Mapping[str, float], l2: float = 1.0, review_target: float = 0.5,
                **_: Any) -> dict[str, Any]:
    X, y = [], []
    for f in feats:
        for fid in f.fams:
            t = family_target(truth.get(f.call_id), fid, review_target)
            if t is not None:
                X.append(learned_row(f, fid, checks))
                y.append(t)
    names = learned_feature_names(checks)
    if not X:
        raise ValueError("no labelled calls to fit the learned fusion on")
    A = np.array(X)
    mu, sd = A.mean(axis=0), A.std(axis=0)
    sd = np.where(sd < 1e-9, 1.0, sd)  # constant features (a check that always scored) stay at 0
    Z = np.column_stack([np.ones(len(A)), (A - mu) / sd])
    beta = fit_logreg(Z, np.array(y), l2=np.array([0.0, *([l2] * len(names))]))
    return {"checks": list(checks), "weights": {c: float(weights.get(c, 1.0)) for c in checks},
            "feature_names": names, "mean": mu.tolist(), "std": sd.tolist(), "intercept": float(beta[0]),
            "coef": beta[1:].tolist(), "options": {"l2": l2, "review_target": review_target}}


def learned_contributions(model: Mapping[str, Any], f: CallFeatures, fid: str) -> dict[str, float]:
    x = (np.array(learned_row(f, fid, model["checks"])) - np.array(model["mean"])) / np.array(model["std"])
    return {n: float(c * v) for n, c, v in zip(model["feature_names"], model["coef"], x)}


def learned_family_prob(model: Mapping[str, Any], f: CallFeatures, fid: str) -> float:
    return float(sigmoid(model["intercept"] + sum(learned_contributions(model, f, fid).values())))


def learned_call_prob(model: Mapping[str, Any], f: CallFeatures) -> tuple[float, str | None, dict[str, float]]:
    probs = {fid: learned_family_prob(model, f, fid) for fid in f.fams}
    if not probs:
        return 0.0, None, probs
    top = max(f.fams, key=lambda fid: (probs[fid], f.fused[fid][0]))
    return probs[top], top, probs


# --------------------------------------------------------------------------------------------
# per-family thresholds (N2)
# --------------------------------------------------------------------------------------------


def fit_family_thresholds(feats: Sequence[CallFeatures], truth: Truth, fold_of: Mapping[str, int] | None = None, *,
                          max_fpr: float = 0.05, lo: float = 0.2, hi: float = 0.95, step: float = 0.01,
                          min_neg: int = 10, **_: Any) -> dict[str, Any]:
    """Per family the lowest threshold (grid ``step``) at which at most ``max_fpr`` of its negatives -
    every labelled call that should not alarm or be reviewed for this family, i.e. also the calls about
    other families - reach the weighted family score. Families with fewer than ``min_neg`` negatives keep
    the global threshold. The officer slider shifts every family threshold by the same amount."""
    grid = np.round(np.arange(lo, hi + 1e-9, step), 4)
    out: dict[str, float] = {}
    stats: dict[str, Any] = {}
    fams = list(dict.fromkeys(fid for f in feats for fid in f.fams))
    for fid in fams:
        neg, pos = [], []
        for f in feats:
            if fid not in f.fams:
                continue
            y = family_target(truth.get(f.call_id), fid, 0.5)
            if y is None:
                continue
            (pos if y > 0 else neg).append(f.fused[fid][0])
        if len(neg) < min_neg:
            stats[fid] = {"n_neg": len(neg), "n_pos": len(pos), "threshold": None}
            continue
        negs = np.array(neg)
        t = next((float(x) for x in grid if np.mean(negs >= x) <= max_fpr), float(hi))
        out[fid] = t
        stats[fid] = {"n_neg": len(neg), "n_pos": len(pos), "threshold": t,
                      "neg_fpr": round(float(np.mean(negs >= t)), 4),
                      "pos_recall": round(float(np.mean(np.array(pos) >= t)), 4) if pos else None}
    return {"family_thresholds": out, "family_stats": stats,
            "options": {"max_fpr": max_fpr, "lo": lo, "hi": hi, "step": step, "min_neg": min_neg}}


# --------------------------------------------------------------------------------------------
# one entry point for fitting
# --------------------------------------------------------------------------------------------


FITTERS: dict[str, Callable[..., dict[str, Any]]] = {
    "calibrated": fit_calibrated, "learned": fit_learned, "thresholds": fit_family_thresholds}
DEFAULT_THRESHOLD = {"calibrated": 0.5, "learned": 0.5}


def fit_model(kind: str, feats: Sequence[CallFeatures], truth: Truth, fold_of: Mapping[str, int] | None = None,
              *, base: Mapping[str, Any] | None = None, **opts: Any) -> dict[str, Any]:
    """Fit one model of ``kind`` on ``feats`` (the caller decides which calls those are: dev only!).
    ``base`` = the weighted-fusion params the features were computed with (stored, so the fusion that
    loads the model recomputes the same features)."""
    if kind not in FITTERS:
        raise ValueError(f"unknown fusion kind {kind!r}; expected one of {KINDS}")
    lab = _labeled(feats, truth)
    model = FITTERS[kind](lab, truth, fold_of, **opts)
    model.update(kind=kind, base=dict(base or {}), n_calls=len(lab),
                 train_dialogues=sorted({f.dialogue for f in lab}),
                 train_calls=sorted(f.call_id for f in lab))
    return model


def save_model(model: Mapping[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(model, ensure_ascii=False, indent=1, default=str))
    return p


def load_model(path: str | Path) -> dict[str, Any]:
    from callguard.config import ROOT
    p = Path(path)
    p = p if p.is_absolute() or p.exists() else ROOT / p
    return json.loads(p.read_text())


# --------------------------------------------------------------------------------------------
# label rule shared by the fitted fusions (pure: also used to pick thresholds quickly)
# --------------------------------------------------------------------------------------------


@dataclass
class Verdict:
    label: str
    score: float  # call probability q
    uncertainty: float
    top: str | None
    probs: dict[str, float]  # family -> probability
    pset: list[str] | None = None  # calibrated: conformal prediction set
    class_probs: dict[str, float] | None = None
    why: str = ""  # threshold | band | below | conformal


def threshold_label(q: float, t: float, band: float) -> tuple[str, str]:
    if q >= t:
        return "alarm", "threshold"
    if q >= _band_floor(t, band):
        return "review", "band"
    return "no_alert", "below"


def fitted_verdict(model: Mapping[str, Any], f: CallFeatures, t: float, band: float,
                   alpha: float | None = None) -> Verdict:
    """calibrated: point label from q against the officer threshold ``t`` (review band below it); the
    conformal set can only turn that label into review (set size != 1, or the set is exactly {review}),
    never create an alarm. learned: threshold + band only."""
    kind = model.get("kind")
    if kind == "calibrated":
        q, top, probs = cal_call_prob(model, f)
        cp = class_probs(model, q)
        pset = prediction_set(model, cp, alpha)
        label, why = threshold_label(q, t, band)
        if len(pset) != 1 or pset == ["review"]:
            label, why = "review", "conformal"
        return Verdict(label, q, round(1.0 - max(cp.values()), 4), top, probs, pset, cp, why)
    if kind == "learned":
        q, top, probs = learned_call_prob(model, f)
        label, why = threshold_label(q, t, band)
        return Verdict(label, q, round(1.0 - abs(2 * q - 1), 4), top, probs, None, None, why)
    raise ValueError(f"fitted_verdict: model kind {kind!r} has no pure label rule")


# --------------------------------------------------------------------------------------------
# nested cross-validation over the dev folds
# --------------------------------------------------------------------------------------------


def make_fusion(kind: str, ctx: "Context", model: Mapping[str, Any], base: Mapping[str, Any],
                passage_params: Mapping[str, Any] | None = None) -> Any:
    """The fusion plugin that applies ``model`` (in memory)."""
    if kind == "thresholds":
        return WeightedFusion(ctx, **{**base, "family_thresholds": dict(model["family_thresholds"]) or None})
    from callguard.fusion.calibrated import CalibratedFusion
    from callguard.fusion.learned import LearnedFusion
    cls = CalibratedFusion if kind == "calibrated" else LearnedFusion
    return cls(ctx, model=dict(model), **dict(passage_params or {}))


def _decide(fusion: Any, r: CallResult, families: list[Family], weights: Mapping[str, float], t: float) -> Decision:
    return fusion.decide(r.transcript, r.checks, families, {"threshold": t, "weights": dict(weights)})


def _mini_row(call: Call | None, call_id: str, label: str, score: float) -> Row:
    from callguard import eval as ev
    return {**ev._base_row(call_id, call), "predicted": label, "score": score, "error": None,
            "failed_checks": [], "top_family": None}


class LeakError(AssertionError):
    pass


def nested_cv(kind: str, results: Sequence[CallResult], calls: Sequence[Call], fold_of: Mapping[str, int],
              ctx: "Context", *, base: Mapping[str, Any], weights: Mapping[str, float],
              threshold: float | None = None, thresholds: Sequence[float] | None = None,
              error_rows: Sequence[Row] = (), fit_fn: Callable[..., dict[str, Any]] | None = None,
              passage_params: Mapping[str, Any] | None = None, **opts: Any) -> dict[str, Any]:
    """Out-of-fold predictions of a fitted fusion over the dev folds in ``fold_of`` (dialogue -> fold;
    pass ``Splits.dev_fold_of()``: the holdout is not in it and is never touched).

    For each fold k: fit on the other folds; choose the threshold on out-of-fold predictions INSIDE the
    other folds (each inner fold predicted by a model fitted on the remaining training folds,
    ``eval.suggest_threshold``); predict fold k with the model fitted on all other folds, once at the
    fixed ``threshold`` (rows "fixed") and once at the chosen one (rows "cv", the primary number, like
    the weighted fusion's CV rows). Every fit's training dialogues are recorded in ``fits`` and checked
    against the test fold. Returns {"fixed", "cv", "cv_folds", "results_cv", "fits"}."""
    from callguard import eval as ev
    from callguard.experiments import result_row

    fit = fit_fn or fit_model
    families = ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    truth = {c.call_id: c for c in calls}
    t0 = float(threshold if threshold is not None else DEFAULT_THRESHOLD.get(kind, base.get("threshold", 0.55)))
    grid = list(thresholds) if thresholds is not None else list(ev.DEFAULT_THRESHOLDS)
    feat_base = WeightedFusion(ctx, **{k: v for k, v in base.items() if k != "family_thresholds"})
    in_dev = [r for r in results if dialogue_of(r.call_id) in fold_of]
    feats = {r.call_id: features_of(feat_base, r, families, weights) for r in in_dev}
    by_fold: dict[int, list[CallResult]] = {}
    for r in in_dev:
        by_fold.setdefault(int(fold_of[dialogue_of(r.call_id)]), []).append(r)
    if len(by_fold) < 3:
        raise ValueError(f"nested CV needs >= 3 dev folds with results, got {sorted(by_fold)}")
    checks = list(dict.fromkeys(n for r in in_dev for n in r.checks))
    fit_opts = {"checks": checks, "weights": weights, **opts}
    fits: list[dict[str, Any]] = []

    def do_fit(train: list[CallResult], test_fold: int, role: str) -> dict[str, Any]:
        train_dlg = {dialogue_of(r.call_id) for r in train}
        test_dlg = {dialogue_of(r.call_id) for r in by_fold[test_fold]}
        if train_dlg & test_dlg or not train_dlg <= set(fold_of):
            raise LeakError(f"fit for fold {test_fold} would see {sorted(train_dlg & test_dlg)}")
        sub_fold = {d: k for d, k in fold_of.items() if d in train_dlg}
        m = fit(kind, [feats[r.call_id] for r in train], truth, sub_fold, base=base, **fit_opts)
        fits.append({"test_fold": test_fold, "role": role, "train_dialogues": sorted(train_dlg)})
        return m

    def labels(model: dict[str, Any], rs: Sequence[CallResult], t: float, fusion: Any) -> list[Row]:
        out = []
        for r in rs:
            if kind == "thresholds":
                d = _decide(fusion, r, families, weights, t)
                out.append(_mini_row(truth.get(r.call_id), r.call_id, d.label, d.score))
            else:
                v = fitted_verdict(model, feats[r.call_id], t, float(fusion.review_band))
                out.append(_mini_row(truth.get(r.call_id), r.call_id, v.label, v.score))
        return out

    rows_fixed: list[Row] = []
    rows_cv: list[Row] = []
    results_cv: list[CallResult] = []
    folds_info: list[dict[str, Any]] = []
    for k in sorted(by_fold):
        train_folds = [j for j in sorted(by_fold) if j != k]
        train = [r for j in train_folds for r in by_fold[j]]
        # threshold: out-of-fold inside the training folds
        inner_models = []
        for j in train_folds:
            inner_train = [r for i in train_folds if i != j for r in by_fold[i]]
            m_j = do_fit(inner_train, k, f"inner-threshold (predicts fold {j})")
            inner_models.append((j, m_j, make_fusion(kind, ctx, m_j, base, passage_params)))
        swept = []
        for t in grid:
            rows_t = [row for j, m_j, fu in inner_models for row in labels(m_j, by_fold[j], t, fu)]
            swept.append({"threshold": round(float(t), 4), "metrics": ev.metrics(rows_t)})
        pick = ev.suggest_threshold(swept)
        t_cv = float(pick["threshold"]) if pick else t0
        model = do_fit(train, k, "outer")
        fusion = make_fusion(kind, ctx, model, base, passage_params)
        for r in by_fold[k]:
            if dialogue_of(r.call_id) in set(model.get("train_dialogues") or ()):
                raise LeakError(f"{r.call_id} was in the training data of its own fold's model")
            call = truth.get(r.call_id)
            d_fix = _decide(fusion, r, families, weights, t0)
            row = result_row(r.model_copy(update={"decision": d_fix}), call, can_alarm)
            rows_fixed.append({**row, "cv_fold": k, "cv_threshold": t0})
            d_cv = _decide(fusion, r, families, weights, t_cv)
            new = r.model_copy(update={"decision": d_cv})
            results_cv.append(new)
            rows_cv.append({**result_row(new, call, can_alarm), "cv_fold": k, "cv_threshold": t_cv})
        folds_info.append({"fold": k, "threshold": t_cv, "n_test": len(by_fold[k]),
                           "dialogues": sorted({dialogue_of(r.call_id) for r in by_fold[k]}),
                           "train_dialogues": model.get("train_dialogues"),
                           "model_summary": summarize_model(model)})
    for er in error_rows:
        d = er.get("dialogue_id") or dialogue_of(er["call_id"])
        if d in fold_of:
            rows_fixed.append({**er, "cv_fold": fold_of[d], "cv_threshold": None})
            rows_cv.append({**er, "cv_fold": fold_of[d], "cv_threshold": None})
    order = {c.call_id: i for i, c in enumerate(calls)}
    for rows in (rows_fixed, rows_cv):
        rows.sort(key=lambda r: order.get(r["call_id"], 1 << 30))
    return {"fixed": rows_fixed, "cv": rows_cv, "cv_folds": folds_info, "results_cv": results_cv, "fits": fits,
            "threshold_fixed": t0}


def summarize_model(model: Mapping[str, Any]) -> dict[str, Any]:
    """A few human-readable numbers per model (for meta.json / the fold table)."""
    kind = model.get("kind")
    if kind == "thresholds":
        return {"family_thresholds": model.get("family_thresholds")}
    if kind == "learned":
        return {"coef": {n: round(c, 3) for n, c in zip(model["feature_names"], model["coef"])},
                "intercept": round(model["intercept"], 3)}
    if kind == "calibrated":
        conf = model.get("conformal") or {}
        return {"platt_families": {c: sorted(k for k in v if k != "_pooled") for c, v in model.get("platt", {}).items()},
                "pool": [round(x, 3) for x in model.get("pool", [])], "conformal_n": conf.get("n"),
                "qhat": round(conformal_qhat(conf.get("scores") or [], float(conf.get("alpha", 0.1))), 4)}
    return {}


def check_weights(cfg: Any) -> dict[str, float]:
    """Configured weight per check instance (as Pipeline.decide passes them to the fusion)."""
    out = {}
    for spec in cfg.checks:
        name = spec.get("name") or spec.get("type")
        w = _num(spec.get("weight", 1.0))
        out[str(name)] = 1.0 if w is None else w
    return out


def base_params(cfg: Any) -> dict[str, Any]:
    """The weighted-fusion params of a config's fusion block (the features of a fitted fusion are computed
    with them; for a ``thresholds`` fit they are the fusion the thresholds are applied to)."""
    import inspect
    allowed = set(inspect.signature(WeightedFusion.__init__).parameters) - {"self", "ctx"}
    return {k: v for k, v in dict(cfg.fusion or {}).items() if k in allowed}


__all__ = ["KINDS", "CLASSES", "RULE_CHECKS", "CallFeatures", "fit_model", "nested_cv", "save_model", "load_model",
           "fitted_verdict", "features_of", "conformal_qhat", "platt_fit", "fit_logreg", "fit_softmax"]
