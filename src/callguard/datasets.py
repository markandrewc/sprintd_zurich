"""Which dataset a stored result row comes from, and the guard that keeps datasets apart in the analyses.

Every evaluation row (``rows.json``) is keyed to a dataset by its call id: the case data (``Stufe…``; dev,
holdout and the re-recorded dev audio share these ids, so re-recorded vs dev is a paired comparison of the SAME
calls), the synthetic scripts (``Synth_…``) and the teammate's external held-out set test50 (``T50-…``). A row may
also carry an explicit ``dataset`` field, which wins.

Rule (user requirement): numbers of different datasets are NEVER combined: no pooled metric, no mean over sets
from different datasets, no paired delta across datasets. :func:`rows_dataset` raises on a row set that mixes
datasets, :func:`same_dataset` on sets that differ; cross-dataset comparisons are only shown side by side
(unpaired, labelled as such). Used by :mod:`callguard.contrib` and :mod:`callguard.candidates`.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

PREFIXES: tuple[tuple[str, str], ...] = (("T50-", "test50"), ("Synth_", "synth"))
CASE = "case"
LABELS = {CASE: "Fall-Daten (Dev)", "test50": "test50 (extern)", "synth": "synthetisch"}


class DatasetMixError(ValueError):
    """Rows of different datasets would be combined."""


def row_dataset(row: dict[str, Any]) -> str:
    if row.get("dataset"):
        return str(row["dataset"])
    cid = str(row.get("call_id") or "")
    for prefix, name in PREFIXES:
        if cid.startswith(prefix):
            return name
    return CASE


def rows_dataset(rows: Iterable[dict[str, Any]], what: str = "rows") -> str | None:
    """The one dataset of a row set (None if empty); raises if the set mixes datasets."""
    found = {row_dataset(r) for r in rows}
    if len(found) > 1:
        raise DatasetMixError(f"{what} mix datasets {sorted(found)}: never pooled")
    return next(iter(found), None)


def same_dataset(sets: Sequence[Iterable[dict[str, Any]]], what: str = "row sets") -> str | None:
    """The common dataset of several row sets; raises if they differ (or any set is mixed)."""
    names = {rows_dataset(s, what) for s in sets} - {None}
    if len(names) > 1:
        raise DatasetMixError(f"{what} come from different datasets {sorted(names)}: never combined")
    return next(iter(names), None)
