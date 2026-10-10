"""Split hygiene for learning: which labelled call may be used for what.

Rules (docs/LEARNING.md, CLAUDE.md rule 3):

* **Case calls are evaluation-only.** Every call of a case dialogue (in ``config/splits.yaml``, or with a
  case-style id ``Stufe<n>_<X><nn>`` even if missing there) is never training data for a model: dev
  dialogues -> ``eval_case_dev``, holdout dialogues -> ``eval_case_holdout``. Threshold calibration may
  use dev calls (that is the project's tuning protocol: dev folds only); the holdout is used by nothing.
* **Simulated demo feedback is never training data** (``demo_only``), whatever the call.
* **New calls** (real traffic, synthetic sets) are split by *twin group*: the unit is the twin group of
  ``config/splits.yaml`` if the dialogue is in one, else the dialogue (``dialogue_of``: the clean / noisy
  recordings ``-K1`` / ``-K2`` of one conversation share it). A stable hash of the unit puts it in
  ``train`` or ``shadow_test`` (default 20 %), so all recordings of a conversation land on one side and
  a call never moves when more labels arrive.

:func:`check` re-verifies an exported record set and is called by every export; tests enforce it.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Mapping
from typing import Any

from callguard.data import dialogue_of
from callguard.splits import HOLDOUT, Splits, load_splits

TRAIN = "train"
SHADOW = "shadow_test"
EVAL_DEV = "eval_case_dev"
EVAL_HOLDOUT = "eval_case_holdout"
DEMO = "demo_only"
USES = (TRAIN, SHADOW, EVAL_DEV, EVAL_HOLDOUT, DEMO)
TRAINABLE = frozenset({TRAIN})
# calibration (threshold) may use these; never the holdout, never demo labels for a real proposal
CALIBRATION = frozenset({TRAIN, SHADOW, EVAL_DEV})
USE_DE = {TRAIN: "Training", SHADOW: "Schatten-Test", EVAL_DEV: "nur Evaluation (Fall, dev)",
          EVAL_HOLDOUT: "gesperrt (Fall, Holdout)", DEMO: "nur Demo"}
CASE_DIALOGUE = re.compile(r"^Stufe\d_[A-Z]\d{2}$")
SALT = "callguard-learn-v1"
DEFAULT_SHADOW = 0.2


class HygieneError(ValueError):
    """An export would put an evaluation-only call into training data (or split a twin group)."""


def splits_or_none() -> Splits | None:
    try:
        return load_splits(required=False)
    except Exception:
        return None


def unit_of(call_id: str, splits: Splits | None) -> str:
    """The resampling / split unit: twin group if known, else the dialogue."""
    d = dialogue_of(call_id)
    return splits.group_of(d) if splits is not None else d


def is_case(call_id: str, splits: Splits | None) -> bool:
    d = dialogue_of(call_id)
    return bool(CASE_DIALOGUE.match(d)) or (splits is not None and d in splits.fold_of())


def _bucket(unit: str) -> float:
    h = hashlib.sha256(f"{SALT}:{unit}".encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def use_of(call_id: str, splits: Splits | None, *, demo: bool = False,
           shadow_fraction: float = DEFAULT_SHADOW) -> str:
    """What this call's labels may be used for (see module doc)."""
    if demo:
        return DEMO
    d = dialogue_of(call_id)
    fold = splits.fold_of().get(d) if splits is not None else None
    if fold == HOLDOUT:
        return EVAL_HOLDOUT
    if fold is not None:
        return EVAL_DEV
    if CASE_DIALOGUE.match(d):  # a case dialogue missing from the split file: strictest treatment
        return EVAL_HOLDOUT
    return SHADOW if _bucket(unit_of(call_id, splits)) < shadow_fraction else TRAIN


def cv_fold_of(call_ids: Iterable[str], splits: Splits | None, n_folds: int = 4) -> dict[str, int]:
    """dialogue -> CV fold for calibration: case dev dialogues keep their dev fold of config/splits.yaml,
    new dialogues get a stable hash fold per twin unit. Holdout dialogues are left out (never tuned on)."""
    out: dict[str, int] = {}
    dev = splits.dev_fold_of() if splits is not None else {}
    n = max(n_folds, len(set(dev.values())) or n_folds)
    for cid in call_ids:
        d = dialogue_of(cid)
        u = use_of(cid, splits)
        if u == EVAL_HOLDOUT:
            continue
        out[d] = dev[d] if d in dev else int(_bucket("cv:" + unit_of(cid, splits)) * n) % n
    return out


def check(records: Iterable[Mapping[str, Any]], splits: Splits | None, *, training: bool) -> list[str]:
    """Problems of a record set (empty list = clean). ``training=True``: every record must be trainable
    and the call's own use must agree. Always: no unit on both sides of train / shadow_test."""
    problems: list[str] = []
    side: dict[str, set[str]] = {}
    for r in records:
        cid = str(r.get("call_id"))
        use = r.get("use")
        demo = r.get("source") == "demo"
        expect = use_of(cid, splits, demo=demo)
        if use != expect:
            problems.append(f"{cid}: marked {use!r}, hygiene says {expect!r}")
        if training and (use not in TRAINABLE or expect not in TRAINABLE):
            problems.append(f"{cid}: {expect} call in a training file")
        if expect in (TRAIN, SHADOW):
            side.setdefault(unit_of(cid, splits), set()).add(expect)
    problems += [f"twin unit {u} is on both sides: {sorted(s)}" for u, s in side.items() if len(s) > 1]
    return problems


def enforce(records: list[dict[str, Any]], splits: Splits | None, *, training: bool) -> list[dict[str, Any]]:
    problems = check(records, splits, training=training)
    if problems:
        raise HygieneError("; ".join(problems[:5]) + (f" (+{len(problems) - 5} more)" if len(problems) > 5 else ""))
    return records
