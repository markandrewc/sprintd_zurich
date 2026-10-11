"""Candidate matrix for the open team decisions: every candidate system side by side with the same numbers.

Driven by ``experiments/contrib/candidates.yaml`` (which stored variants make up each candidate) plus two editable
text files: ``experiments/contrib/decisions.yaml`` (the open team decisions: options, pros/cons, recommendation)
and ``experiments/contrib/comparison_zurich.yaml`` (our design vs the teammate's prototype). The team's choices are
recorded by the UI page "Team-Entscheidungen" in ``experiments/contrib/team_decisions.yaml``.

Nothing is recomputed: no ASR, no LLM. Every number comes from stored ``rows.json`` (statistics of
:mod:`callguard.stats` / :mod:`callguard.contrib`) and, optionally, the passage hit rate (the
``callguard evidence-eval`` method) on stored ``results.jsonl`` (cached per file mtime).

Per candidate (dev split, 48 calls / 24 dialogues, 95% bootstrap CIs over twin groups/dialogues):

* tuned: flag AUC [CI] (fixed-threshold scores), CV false-alarm / miss rate, review recall, 3-class accuracy,
* paired against the reference candidate (the champion) on the same calls: deltas with CIs; ``real`` = CI
  excludes 0. Anything not real is shown as "≈ Champion",
* generalisation: flag AUC with reworded questions (mean over the paraphrase sets), the blind table and the
  re-recorded audio, each with the paired drop against the candidate's own tuned run (same calls, mean-of-AUC
  bootstrap with shared resampling weights) and against the champion under the same condition (reworded: the
  champion's paraphrase sets at the same list positions, e.g. a candidate with only para 1 vs the champion's para 1),
* evidence hit@1 with chance@1, passages / hardware / licence / end-to-end status from the spec.

Slots that have no rows yet are classified from the files: ``running`` (variant folder exists, no rows.json yet:
"läuft noch"), ``pending`` (named in an ``experiments/*.yaml`` spec: "ausstehend"), ``missing`` (not planned),
``na`` (does not apply). Re-running the command (or reloading the UI page) picks up new rows automatically.

Refs: ``<experiment>/<variant>`` under the default data root (``runs/experiments``) or ``<root>:<experiment>/<variant>``
for a named root (``perturbed:`` = ``runs/perturbed/experiments``). A list = fallbacks, first available wins
(for ``reworded``: every entry is a separate paraphrase set and the AUC is their mean).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from callguard import contrib as cb
from callguard import stats
from callguard.config import ROOT
from callguard.datasets import CASE, DatasetMixError, rows_dataset, same_dataset

DEFAULT_SPEC = ROOT / "experiments" / "contrib" / "candidates.yaml"
DEFAULT_DECISIONS = ROOT / "experiments" / "contrib" / "decisions.yaml"
DEFAULT_COMPARISON = ROOT / "experiments" / "contrib" / "comparison_zurich.yaml"
DEFAULT_TEAM = ROOT / "experiments" / "contrib" / "team_decisions.yaml"
DEFAULT_OUT = ROOT / "runs" / "candidates"
DEFAULT_DOC = ROOT / "docs" / "TEAM_OPTIONS.md"
ENV_ZURICH = "CALLGUARD_ZURICH_REPO"
DEFAULT_ROOTS = {"default": "runs/experiments", "perturbed": "runs/perturbed/experiments",
                 "test50": "runs/test50/experiments"}
# dataset every root must hold (callguard.datasets): rows of different datasets are never combined
DEFAULT_ROOT_DATASETS = {"default": CASE, "perturbed": CASE, "test50": "test50"}
T50 = "test50"

SLOTS = ("tuned", "reworded", "blind", "rerecorded")
GEN_SLOTS = ("reworded", "blind", "rerecorded")
ALL_SLOTS = (*SLOTS, T50)
SLOT_LABELS = {"tuned": "abgestimmt (Dev)", "reworded": "umformuliert", "blind": "blinde Tabelle",
               "rerecorded": "neu aufgenommen", T50: "test50 (extern)"}
T50_TITLE = "test50 (extern, FHNW-TTS, 8 Dialekte)"
T50_BANNER = ("Externer Testsatz: nie zum Tunen verwendet; Zahlen nicht mit Dev vergleichbar gepoolt. "
              "Eigener Datensatz (100 Anrufe, 50 Dialoge sauber/verrauscht, 8 Dialekt-Stimmen), eigene "
              "Ergebnisse (runs/test50), vorregistriert (research/findings/test50_prereg.md).")
T50_TYPES = {"pair": "Paar (A/B)", "trap": "Stichwort-Falle", "review": "Prüfen-Fall", "numbers": "Zahlen-Paar",
             "multi": "Mehrere Themen"}
STATUS_TEXT = {"ok": "da", "running": "läuft noch", "pending": "ausstehend", "missing": "nicht geplant",
               "na": "n/a"}
METRICS = ("false_alarm_rate", "miss_rate", "review_recall", "accuracy")
# column key -> (label, higher is better, percent)
COLUMNS = {
    "auc": ("Flag-AUC", True, False), "false_alarm_rate": ("Fehlalarme (CV)", False, True),
    "miss_rate": ("Verpasst (CV)", False, True), "review_recall": ("Prüf-Recall", True, True),
    "accuracy": ("Exakt 3 Klassen", True, True), "reworded": ("AUC umformuliert", True, False),
    "blind": ("AUC blinde Tabelle", True, False), "rerecorded": ("AUC neu aufgenommen", True, False),
    "hit1": ("Beleg hit@1", True, True), "cost": ("s/Anruf", False, False),
    # test50: own dataset, fixed (dev-frozen) threshold; never pooled with the columns above
    "t50_auc": ("test50 Flag-AUC", True, False), "t50_far": ("test50 Fehlalarme (fix)", False, True),
    "t50_miss": ("test50 Verpasst (fix)", False, True), "t50_acc": ("test50 Exakt (fix)", True, True),
    "t50_rr": ("test50 Prüf-Recall (fix)", True, True),
}
T50_KEYS = {"t50_far": "false_alarm_rate", "t50_miss": "miss_rate", "t50_acc": "accuracy", "t50_rr": "review_recall"}
GEN_COLUMNS = ("reworded", "blind", "rerecorded")


class SpecError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# spec + data access
# --------------------------------------------------------------------------------------------


def _abs(p: str | Path) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def load_yaml(path: str | Path | None, default: Path) -> dict[str, Any]:
    p = _abs(path or default)
    if not p.exists():
        return {"_path": str(p), "_missing": True}
    d = yaml.safe_load(p.read_text()) or {}
    d["_path"] = str(p)
    return d


def _as_list(x: Any) -> list[str]:
    if x is None:
        return []
    return [x] if isinstance(x, str) else [r for r in x if r]


def parse_ref(ref: str) -> tuple[str, str, str]:
    """``[root:]experiment/variant`` -> (root, experiment, variant)."""
    root, _, rest = ref.rpartition(":")
    if not isinstance(rest, str) or rest.count("/") != 1:
        raise SpecError(f"variant reference must be '[root:]<experiment>/<variant>', got {ref!r}")
    e, v = rest.split("/")
    return root or "default", e, v


def load_spec(path: str | Path | None = None) -> dict[str, Any]:
    s = load_yaml(path, DEFAULT_SPEC)
    if s.get("_missing"):
        raise FileNotFoundError(f"candidates spec not found: {s['_path']}")
    if not isinstance(s.get("candidates"), list) or not s["candidates"]:
        raise SpecError(f"{s['_path']}: needs a `candidates:` list")
    ids = set()
    for c in s["candidates"]:
        if not c.get("id") or c["id"] in ids:
            raise SpecError(f"{s['_path']}: every candidate needs a unique `id` ({c!r:.80})")
        ids.add(c["id"])
        for slot in ALL_SLOTS:
            for r in _as_list(c.get(slot)):
                if r != "na":
                    root = parse_ref(r)[0]
                    ds = root_datasets(s).get(root)
                    if ds is not None and (slot == T50) != (ds == T50):
                        raise SpecError(f"{s['_path']}: {c['id']}.{slot} = {r!r} reads root {root!r} (dataset {ds}): "
                                        f"test50 rows only in the `test50` slot, never in a dev slot")
    if s.get("reference") and s["reference"] not in ids:
        raise SpecError(f"{s['_path']}: reference {s['reference']!r} is not a candidate id")
    return s


def root_datasets(spec: dict[str, Any] | None = None) -> dict[str, str]:
    return {**DEFAULT_ROOT_DATASETS, **((spec or {}).get("root_datasets") or {})}


class Data:
    """Stores per named data root + the variant names planned in ``experiments/*.yaml``. Every root is keyed to
    one dataset (``datasets``): a variant whose rows belong to another dataset raises :class:`DatasetMixError`."""

    def __init__(self, roots: dict[str, str | Path], experiments_dir: str | Path | None = None,
                 datasets: dict[str, str] | None = None):
        self.roots = {k: _abs(v) for k, v in roots.items()}
        self.datasets = {**DEFAULT_ROOT_DATASETS, **(datasets or {})}
        self.stores = {k: cb.Store(v) for k, v in self.roots.items()}
        self.planned: dict[str, set[str]] = {}
        ed = _abs(experiments_dir or "experiments")
        if ed.exists():
            for p in sorted(ed.glob("*.yaml")):
                try:
                    d = yaml.safe_load(p.read_text()) or {}
                except (OSError, yaml.YAMLError):
                    continue
                if isinstance(d, dict) and d.get("name"):
                    self.planned.setdefault(d["name"], set()).update(
                        v.get("name") for v in d.get("variants") or [] if isinstance(v, dict))

    def _store(self, root: str) -> cb.Store:
        if root not in self.stores:
            raise SpecError(f"unknown data root {root!r} (known: {', '.join(self.stores)})")
        return self.stores[root]

    def get(self, ref: str) -> cb.Variant | None:
        root, e, v = parse_ref(ref)
        var = self._store(root).get(f"{e}/{v}")
        if var is not None and self.datasets.get(root):
            got = rows_dataset(var.rows.get("fixed") or [], ref)
            if got and got != self.datasets[root]:
                raise DatasetMixError(f"{ref}: rows are dataset {got!r}, root {root!r} holds {self.datasets[root]!r}")
        return var

    def status(self, ref: str) -> str:
        if ref == "na":
            return "na"
        if self.get(ref) is not None:
            return "ok"
        root, e, v = parse_ref(ref)
        if (self._store(root).root / e / v).is_dir():
            return "running"
        return "pending" if v in self.planned.get(e, set()) else "missing"

    def results_path(self, ref: str) -> Path:
        root, e, v = parse_ref(ref)
        return self._store(root).root / e / v / "results.jsonl"

    def fingerprint(self, *extra: str | Path | None) -> float:
        newest = 0.0
        for r in self.roots.values():
            newest = max(newest, cb.fingerprint(r))
            if r.exists():  # a new (still empty) variant folder also changes the status
                for p in r.glob("*/*"):
                    try:
                        newest = max(newest, p.stat().st_mtime)
                    except OSError:
                        pass
        for p in extra:
            if p and Path(p).exists():
                newest = max(newest, Path(p).stat().st_mtime)
        return newest


def resolve(data: Data, refs: Any) -> dict[str, Any]:
    """First available of the fallback refs; else the most advanced status (running > pending > missing)."""
    refs = _as_list(refs)
    if not refs or refs == ["na"]:
        return {"ref": None, "status": "na", "refs": []}
    sts = [(r, data.status(r)) for r in refs]
    for r, s in sts:
        if s == "ok":
            return {"ref": r, "status": "ok", "refs": refs}
    order = {"running": 0, "pending": 1, "missing": 2}
    r, s = min(sts, key=lambda x: order[x[1]])
    return {"ref": r, "status": s, "refs": refs}


# --------------------------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------------------------


def mean_auc_delta(sets_a: Sequence[Sequence[dict]], sets_b: Sequence[Sequence[dict]], n_boot: int = 2000,
                   seed: int = 13, alpha: float = 0.05) -> dict[str, Any]:
    """mean(AUC of sets_b) - mean(AUC of sets_a) on the calls every set scored, paired: all sets use the same
    resampled units (twin groups / dialogues) per bootstrap replicate. With one set per side this equals
    :func:`stats.paired_auc` (flag target)."""
    same_dataset([*sets_a, *sets_b], "AUC sets")  # never a mean / delta across datasets
    scored = [{r["call_id"]: r for r in stats._scored(s)} for s in [*sets_a, *sets_b]]
    if not sets_a or not sets_b or not scored:
        return {"a": None, "b": None, "diff": None, "lo": None, "hi": None, "real": False, "n": 0}
    common = sorted(set.intersection(*(set(d) for d in scored)))
    out: dict[str, Any] = {"a": None, "b": None, "diff": None, "lo": None, "hi": None, "real": False,
                           "n": len(common)}
    if not common:
        return out
    pos_lab = stats.AUC_TARGETS["flag"]
    ordered = [[d[c] for c in common] for d in scored]
    if not any(r["expected"] in pos_lab for r in ordered[0]) or all(r["expected"] in pos_lab for r in ordered[0]):
        return out
    w, _ = stats._unit_weights(ordered[0], n_boot, seed)
    reps, points = [], []
    for rows in ordered:
        pos, neg, m = stats._auc_parts(rows, pos_lab)
        reps.append(stats._weighted_auc(w, pos, neg, m))
        points.append(stats.auc(rows, "flag"))
    na = len(sets_a)
    a, b = float(np.mean(points[:na])), float(np.mean(points[na:]))
    lo, hi, _ = stats._ci(np.mean(reps[na:], axis=0) - np.mean(reps[:na], axis=0), alpha)
    out.update(a=round(a, 4), b=round(b, 4), diff=round(b - a, 4), lo=lo, hi=hi,
               real=lo is not None and hi is not None and (lo > 0 or hi < 0))
    return out


def _fixed(v: cb.Variant) -> list[dict]:
    return v.rows.get("fixed") or []


def trivial_variant(ref_variant: cb.Variant, label: str = "alarm", ref: str = "trivial/flag_all") -> cb.Variant:
    """Flag everything (``alarm``) on the reference calls: constant score -> AUC 0.5."""
    def conv(rows: list[dict]) -> list[dict]:
        return [{**r, "predicted": label, "score": 1.0, "llm_calls": 0, "check_seconds": {}} for r in rows]
    rows = {k: conv(v) for k, v in ref_variant.rows.items() if k in ("fixed", "cv") and v}
    return cb.Variant(ref, rows, {"description": f"trivial: every call {label}"}, {}, {})


def review_counts(v: cb.Variant, basis: str = "cv") -> dict[str, int]:
    rows, _ = v.basis_rows(basis)
    lab = stats.labeled(rows)
    return {"predicted": sum(r.get("predicted") == "review" for r in lab),
            "expected": sum(r.get("expected") == "review" for r in lab),
            "hit": sum(r.get("predicted") == "review" == r.get("expected") for r in lab), "n": len(lab)}


# --------------------------------------------------------------------------------------------
# evidence (optional, cached)
# --------------------------------------------------------------------------------------------


def evidence_for(data: Data, refs: Sequence[str], cache_path: Path | None,
                 compute: Callable[[Path], dict[str, Any] | None] | None) -> dict[str, dict[str, Any]]:
    """Evidence summaries per ref from the cache (keyed by results.jsonl mtime); ``compute`` fills misses
    (the label-reading part lives in ``callguard.commands.evidence_eval.results_summary``, evaluation only)."""
    cache: dict[str, Any] = {}
    if cache_path and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text())
        except (OSError, ValueError):
            cache = {}
    out, dirty = {}, False
    for ref in refs:
        p = data.results_path(ref)
        if not p.exists():
            continue
        key = f"{ref}@{p.stat().st_mtime:.0f}"
        if key in cache:
            out[ref] = cache[key]
        elif compute is not None:
            s = compute(p)
            if s is not None:
                cache[key] = out[ref] = s
                dirty = True
    if dirty and cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=1, ensure_ascii=False))
    return out


# --------------------------------------------------------------------------------------------
# the matrix
# --------------------------------------------------------------------------------------------


def _delta(d: dict[str, Any] | None) -> dict[str, Any] | None:
    if not d or d.get("diff") is None:
        return None
    return {k: d.get(k) for k in ("a", "b", "diff", "lo", "hi", "real")}


def analyse(spec: dict[str, Any], roots: dict[str, str | Path] | None = None, n_boot: int | None = None,
            seed: int | None = None, evidence: dict[str, dict[str, Any]] | None = None,
            experiments_dir: str | Path | None = None) -> dict[str, Any]:
    roots = {**DEFAULT_ROOTS, **(spec.get("data_roots") or {}), **(roots or {})}
    data = Data(roots, experiments_dir or spec.get("experiments_dir"), root_datasets(spec))
    n_boot = int(n_boot or spec.get("n_boot") or 2000)
    seed = int(seed if seed is not None else spec.get("seed", 13))
    basis = spec.get("rows") or "cv"
    evidence = evidence or {}

    ref_id = spec.get("reference")
    slots = {c["id"]: {s: resolve(data, c.get(s)) for s in ALL_SLOTS} for c in spec["candidates"]
             if not c.get("trivial")}
    ref_slots = slots.get(ref_id) or {}
    ref_tuned = data.get(ref_slots["tuned"]["ref"]) if ref_slots.get("tuned", {}).get("status") == "ok" else None
    ref_t50 = data.get(ref_slots[T50]["ref"]) if ref_slots.get(T50, {}).get("status") == "ok" else None

    def gen_sets(sl: dict[str, Any], slot: str, positions: Sequence[int] | None = None) -> list[list[dict]]:
        """Row sets of a condition; for ``reworded`` one per available paraphrase set (``positions``: only those
        list positions, so a candidate with only para 1 is paired against the champion's para 1)."""
        if slot == "reworded":
            return [_fixed(data.get(r)) for i, r in enumerate(sl["refs"])
                    if data.status(r) == "ok" and (positions is None or i in positions)]
        return [_fixed(data.get(sl["ref"]))] if sl["status"] == "ok" else []

    cands = []
    for c in spec["candidates"]:
        cid = c["id"]
        rec: dict[str, Any] = {k: c.get(k) for k in ("id", "label", "short", "group", "kind", "passages", "hardware",
                                                    "licence", "e2e", "profile", "note", "table", "model", "hidden")}
        rec["kind"] = c.get("kind") or "candidate"
        if c.get("trivial"):
            if ref_tuned is None:
                rec.update(slots={"tuned": {"ref": None, "status": "pending", "refs": []}}, tuned=None)
                cands.append(rec)
                continue
            v = trivial_variant(ref_tuned, ref=f"trivial/{c['trivial']}")
            sl = {"tuned": {"ref": f"trivial/{c['trivial']}", "status": "ok", "refs": []},
                  **{s: {"ref": None, "status": "na", "refs": []} for s in GEN_SLOTS},
                  T50: ({"ref": f"trivial/{c['trivial']}@test50", "status": "ok", "refs": []} if ref_t50 is not None
                        else {"ref": ref_slots.get(T50, {}).get("ref"), "refs": [],
                              "status": "pending" if ref_slots.get(T50, {}).get("refs") else "na"})}
            v50 = trivial_variant(ref_t50, ref=f"trivial/{c['trivial']}@test50") if ref_t50 is not None else None
        else:
            sl = slots[cid]
            v = data.get(sl["tuned"]["ref"]) if sl["tuned"]["status"] == "ok" else None
            v50 = data.get(sl[T50]["ref"]) if sl[T50]["status"] == "ok" else None
        rec["slots"] = sl
        if v50 is not None:  # own dataset: never pooled with the dev numbers of the same candidate
            rec[T50] = test50_record(v50, ref_t50 if cid != ref_id else None, v, n_boot, seed,
                                     trivial=bool(c.get("trivial")))
        if v is None:
            rec["tuned"] = None
            cands.append(rec)
            continue
        r = cb.variant_record(v, basis, n_boot, seed)
        rec["tuned"] = {k: r[k] for k in ("ref", "basis", "n_calls", "n_dialogues", "auc", "metrics", "cost",
                                          "tags", "description", "far20")}
        rec["reviews"] = review_counts(v, basis)
        if c.get("trivial"):
            rec["tuned"]["cost"] = {"s_per_call": 0.0, "llm_calls_per_call": 0.0, "wall_s_per_call": None}
        # paired against the reference candidate on the same calls
        if ref_tuned is not None and cid != ref_id:
            cmp = cb.compare_rows(ref_tuned.rows, v.rows, basis, n_boot, seed)
            if cmp.get("paired"):
                rec["vs_ref"] = {"n_common": cmp["n_common"], "verdict": cmp["verdict"], "flips": cmp["flips"]["n"],
                                 **{k: _delta(cmp["deltas"].get(k)) for k in ("auc", *METRICS)}}
        # generalisation
        gen = {}
        tuned_rows = _fixed(v)
        for slot in GEN_SLOTS:
            g: dict[str, Any] = {"status": sl[slot]["status"], "refs": sl[slot]["refs"], "auc": None}
            if slot == "reworded" and sl[slot]["refs"]:
                g["parts"] = [{"ref": x, "status": data.status(x)} for x in sl[slot]["refs"]]
                n_ok = sum(p["status"] == "ok" for p in g["parts"])
                if n_ok and n_ok < len(g["parts"]):
                    g["status"] = "partial"
            sets = gen_sets(sl[slot], slot)
            if sets:
                aucs = [stats.bootstrap_auc(s, n_boot=n_boot, seed=seed)["flag"] for s in sets]
                g["aucs"] = [{"value": a["value"], "lo": a["lo"], "hi": a["hi"]} for a in aucs]
                g["n_sets"] = len(sets)
                if len(sets) == 1:
                    g["auc"] = g["aucs"][0]
                else:  # mean over the paraphrase sets, CI from the shared-weight bootstrap
                    lo, hi = mean_auc_ci(sets, n_boot, seed)
                    pts = [a["value"] for a in aucs if a["value"] is not None]
                    g["auc"] = {"value": round(float(np.mean(pts)), 4) if pts else None, "lo": lo, "hi": hi}
                g["drop"] = mean_auc_delta([tuned_rows], sets, n_boot, seed)
                ref_sl = ref_slots.get(slot)
                if cid != ref_id and ref_sl:
                    pos = ([i for i, r in enumerate(sl[slot]["refs"]) if data.status(r) == "ok"]
                           if slot == "reworded" else None)
                    ref_sets = gen_sets(ref_sl, slot, pos)
                    if ref_sets:
                        g["vs_ref"] = mean_auc_delta(ref_sets, sets, n_boot, seed)
            gen[slot] = g
        rec["gen"] = gen
        ev_ref = c.get("evidence_ref") or sl["tuned"]["ref"]
        if ev_ref in evidence:
            rec["evidence"] = {"ref": ev_ref, **evidence[ev_ref]}
        cands.append(rec)

    result = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": spec.get("_path"),
        "roots": {k: str(v) for k, v in data.roots.items()}, "n_boot": n_boot, "seed": seed, "basis": basis,
        "reference": ref_id, "candidates": cands,
        "fingerprint": data.fingerprint(spec.get("_path")),
        "evidence_note": spec.get("evidence_note"),
    }
    result["best"] = best_marks(result)
    result["pending"] = pending_items(result)
    return result


def mean_auc_ci(sets: Sequence[Sequence[dict]], n_boot: int = 2000, seed: int = 13,
                alpha: float = 0.05) -> tuple[float | None, float | None]:
    """Percentile CI of the mean AUC over several row sets (common calls, shared resampling weights)."""
    same_dataset(sets, "AUC sets")
    scored = [{r["call_id"]: r for r in stats._scored(s)} for s in sets]
    common = sorted(set.intersection(*(set(d) for d in scored))) if scored else []
    if not common:
        return None, None
    ordered = [[d[c] for c in common] for d in scored]
    pos_lab = stats.AUC_TARGETS["flag"]
    w, _ = stats._unit_weights(ordered[0], n_boot, seed)
    reps = [stats._weighted_auc(w, *stats._auc_parts(rows, pos_lab)) for rows in ordered]
    lo, hi, _ = stats._ci(np.mean(reps, axis=0), alpha)
    return lo, hi


# --------------------------------------------------------------------------------------------
# test50 (external held-out set): own record, never pooled
# --------------------------------------------------------------------------------------------


def t50_type(call_id: str) -> str:
    """pair / trap / review / numbers / multi from the test50 call id (``T50-<family>-<NN>-A-K1`` etc.)."""
    dlg = call_id.rsplit("-K", 1)[0]
    if dlg.endswith("-review"):
        return "review"
    if dlg.endswith("-trap"):
        return "trap"
    if dlg.startswith("T50-multi-"):
        return "multi"
    if dlg.startswith("T50-numbers-"):
        return "numbers"
    return "pair"


def _acc_block(rows: Sequence[dict]) -> dict[str, Any]:
    lab = stats.labeled(rows)
    n = len(lab)
    return {"n": n, "label_acc": _r(sum(stats.label_correct(r) for r in lab) / n) if n else None,
            "flag_acc": _r(sum(stats.flag_correct(r) for r in lab) / n) if n else None,
            "expected": {k: sum(r["expected"] == k for r in lab) for k in ("alarm", "review", "no_alert")}}


def _r(x: float | None) -> float | None:
    return None if x is None else round(float(x), 4)


def test50_breakdown(rows: Sequence[dict]) -> dict[str, Any]:
    """Exact label / flag correct per call type and per clean vs noisy recording (fixed-threshold rows)."""
    rows_dataset(rows, "test50 rows")
    by_type = {t: _acc_block([r for r in rows if t50_type(r["call_id"]) == t]) for t in T50_TYPES}
    noisy = lambda r: bool(r.get("noisy")) if r.get("noisy") is not None else r["call_id"].endswith("-K2")  # noqa: E731
    return {"types": {t: b for t, b in by_type.items() if b["n"]},
            "audio": {"sauber": _acc_block([r for r in rows if not noisy(r)]),
                      "verrauscht": _acc_block([r for r in rows if noisy(r)])}}


def unpaired_auc_delta(rows_a: Sequence[dict], rows_b: Sequence[dict], n_boot: int = 2000, seed: int = 13,
                       alpha: float = 0.05) -> dict[str, Any]:
    """AUC(B) - AUC(A) for two DIFFERENT datasets (e.g. dev -> test50): nothing is pooled or paired; each AUC is
    bootstrapped over its own units (independent seeds) and the CI is that of the difference of the replicates."""
    out: dict[str, Any] = {"a": None, "b": None, "diff": None, "lo": None, "hi": None, "real": False,
                           "paired": False, "datasets": [rows_dataset(rows_a, "A"), rows_dataset(rows_b, "B")]}
    reps = []
    for rows, sd in ((rows_a, seed), (rows_b, seed + 1)):
        sc = stats._scored(rows)
        pos_lab = stats.AUC_TARGETS["flag"]
        if not sc or all(r["expected"] in pos_lab for r in sc) or not any(r["expected"] in pos_lab for r in sc):
            return out
        w, _ = stats._unit_weights(sc, n_boot, sd)
        reps.append(stats._weighted_auc(w, *stats._auc_parts(sc, pos_lab)))
    a, b = stats.auc(rows_a, "flag"), stats.auc(rows_b, "flag")
    lo, hi, _ = stats._ci(reps[1] - reps[0], alpha)
    out.update(a=a, b=b, diff=_r(b - a), lo=lo, hi=hi, real=lo is not None and hi is not None and (lo > 0 or hi < 0))
    return out


def test50_record(v50: cb.Variant, ref50: cb.Variant | None, dev: cb.Variant | None, n_boot: int, seed: int,
                  trivial: bool = False) -> dict[str, Any]:
    """Fixed-threshold (dev-frozen) metrics, CV-within-test50 metrics, paired delta against the champion's test50
    run (twin groups = resampling units) and the unpaired dev -> test50 AUC drop."""
    fx = cb.variant_record(v50, "fixed", n_boot, seed)
    rec: dict[str, Any] = {"ref": v50.ref, "dataset": fx.get("dataset"), "n_calls": fx["n_calls"],
                           "n_units": len({stats._dialogue(r) for r in _fixed(v50)}), "auc": fx["auc"],
                           "fixed": fx["metrics"], "reviews": review_counts(v50, "fixed"),
                           "breakdown": test50_breakdown(_fixed(v50))}
    if v50.rows.get("cv"):
        rec["cv"] = cb.variant_record(v50, "cv", n_boot, seed)["metrics"]
    if ref50 is not None and not trivial:
        cmp = cb.compare_rows(ref50.rows, v50.rows, "fixed", n_boot, seed)
        if cmp.get("paired"):
            rec["vs_ref"] = {"n_common": cmp["n_common"], "units": cmp.get("units"), "verdict": cmp["verdict"],
                             "flips": cmp["flips"]["n"],
                             **{k: _delta(cmp["deltas"].get(k)) for k in ("auc", *METRICS)}}
    if dev is not None and not trivial:
        rec["dev_drop"] = unpaired_auc_delta(_fixed(dev), _fixed(v50), n_boot, seed)
    return rec


# --------------------------------------------------------------------------------------------
# accessors used by the tables, the placeholders and the UI
# --------------------------------------------------------------------------------------------


def value(c: dict[str, Any], key: str) -> dict[str, Any] | None:
    """{value, lo, hi} of a column for one candidate (None when not available)."""
    t = c.get("tuned")
    if key == "auc":
        return (t or {}).get("auc") if t else None
    if key in METRICS:
        return ((t or {}).get("metrics") or {}).get(key) if t else None
    if key in GEN_COLUMNS:
        return ((c.get("gen") or {}).get(key) or {}).get("auc")
    if key == "hit1":
        return (c.get("evidence") or {}).get("hit1")
    if key == "cost":
        s = ((t or {}).get("cost") or {}).get("s_per_call") if t else None
        return None if s is None else {"value": s, "lo": None, "hi": None}
    if key == "t50_auc":
        return (c.get(T50) or {}).get("auc")
    if key in T50_KEYS:
        return ((c.get(T50) or {}).get("fixed") or {}).get(T50_KEYS[key])
    return None


def vs_ref(c: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Paired delta (candidate - reference) of a column, when computable."""
    if key in ("auc", *METRICS):
        return (c.get("vs_ref") or {}).get(key)
    if key in GEN_COLUMNS:
        return ((c.get("gen") or {}).get(key) or {}).get("vs_ref")
    if key == "t50_auc":
        return ((c.get(T50) or {}).get("vs_ref") or {}).get("auc")
    if key in T50_KEYS:
        return ((c.get(T50) or {}).get("vs_ref") or {}).get(T50_KEYS[key])
    return None


def best_marks(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Best candidate per column (kind == candidate only) and whether it differs from the reference for real."""
    out = {}
    pool = [c for c in result["candidates"] if c.get("kind") == "candidate"]
    for key, (_, higher, _) in COLUMNS.items():
        vals = [(c, (value(c, key) or {}).get("value")) for c in pool]
        vals = [(c, v) for c, v in vals if v is not None]
        if not vals:
            continue
        best = max(v for _, v in vals) if higher else min(v for _, v in vals)
        ids = [c["id"] for c, v in vals if v == best]
        real = {i: bool((vs_ref(next(c for c in pool if c["id"] == i), key) or {}).get("real")) for i in ids}
        out[key] = {"ids": ids, "value": best, "real_vs_ref": real}
    return out


def slot_states(c: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(slot, ref, status) for every slot of a candidate, reworded expanded per paraphrase set."""
    out = []
    for slot in ALL_SLOTS:
        sl = (c.get("slots") or {}).get(slot) or {}
        if slot == "reworded" and sl.get("refs"):
            parts = ((c.get("gen") or {}).get("reworded") or {}).get("parts")
            for p in parts or [{"ref": r, "status": sl["status"]} for r in sl["refs"]]:
                out.append((slot, p["ref"], p["status"]))
        else:
            out.append((slot, sl.get("ref") or "", sl.get("status") or "na"))
    return out


def visible(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Candidates shown in the matrix (``hidden: true`` ones only feed the text placeholders)."""
    return [c for c in result["candidates"] if not c.get("hidden")]


def pending_items(result: dict[str, Any]) -> list[dict[str, str]]:
    return [{"candidate": c["id"], "label": c.get("label") or c["id"], "slot": s, "ref": r, "status": st}
            for c in result["candidates"] for s, r, st in slot_states(c) if st in ("running", "pending")]


# --------------------------------------------------------------------------------------------
# formatting + placeholders for the decision texts
# --------------------------------------------------------------------------------------------


def fmt_num(x: Any, pct: bool = False, nd: int = 2) -> str:
    if x is None:
        return "–"
    return f"{100 * x:.0f}%" if pct else f"{x:.{nd}f}"


def fmt_ci(d: dict[str, Any] | None, pct: bool = False, nd: int = 2) -> str:
    if not d or d.get("value") is None:
        return "–"
    v = fmt_num(d["value"], pct, nd)
    if d.get("lo") is None or d.get("hi") is None:
        return v
    if pct:
        return f"{v} [{100 * d['lo']:.0f}, {100 * d['hi']:.0f}]"
    return f"{v} [{d['lo']:.{nd}f}, {d['hi']:.{nd}f}]"


def fmt_delta(d: dict[str, Any] | None, pct: bool = False, approx: str = "≈") -> str:
    """'+0.06 [-0.00, +0.16] ≈' / '-15 Pkt. [-32, -2] belegt'."""
    if not d or d.get("diff") is None:
        return "–"
    if pct:
        s = f"{100 * d['diff']:+.0f} Pkt."
        if d.get("lo") is not None:
            s += f" [{100 * d['lo']:+.0f}, {100 * d['hi']:+.0f}]"
    else:
        # a bound that rounds to 0.00 hides whether the CI excludes 0: show one more decimal then
        nd = 3 if d.get("lo") is not None and min(abs(d["lo"]), abs(d["hi"])) < 0.005 else 2
        s = f"{d['diff']:+.{nd}f}"
        if d.get("lo") is not None:
            s += f" [{d['lo']:+.{nd}f}, {d['hi']:+.{nd}f}]"
    return f"{s} belegt" if d.get("real") else f"{s} {approx}".rstrip()


def slot_text(c: dict[str, Any], slot: str) -> str:
    st = ((c.get("gen") or {}).get(slot) or {}).get("status") or ((c.get("slots") or {}).get(slot) or {}).get("status")
    if slot == T50 and (st or "na") == "na":
        return "nicht geplant"  # the test50 candidate list is fixed (pre-registered)
    return {"running": "läuft noch", "pending": "ausstehend", "missing": "nicht geplant", "na": "n/a",
            "partial": "teilweise"}.get(st or "na", "–")


def cell(c: dict[str, Any], key: str) -> str:
    """Markdown/table cell: value [CI], or the slot state when there is no value."""
    _, _, pct = COLUMNS[key]
    v = value(c, key)
    if v is None or v.get("value") is None:
        if key in GEN_COLUMNS:
            return slot_text(c, key)
        if key.startswith("t50_"):
            return slot_text(c, T50) if not c.get(T50) else "–"
        if key == "hit1":
            return "keine Passagen" if c.get("passages") == "nein" else "–"
        if c.get("tuned") is None:
            return STATUS_TEXT.get(((c.get("slots") or {}).get("tuned") or {}).get("status") or "", "–")
        return "–"
    if key == "cost":
        return fmt_num(v["value"], nd=1)
    s = fmt_ci(v, pct)
    if key == "reworded" and ((c.get("gen") or {}).get("reworded") or {}).get("n_sets", 0) > 1:
        s += f" (Ø {c['gen']['reworded']['n_sets']})"
    if key == "reworded" and ((c.get("gen") or {}).get("reworded") or {}).get("status") == "partial":
        s += " (teilweise)"
    if key == "hit1":
        ev = c.get("evidence") or {}
        s += f", Zufall {fmt_num(ev.get('chance1'), True)}"
        if ev.get("no_passage"):
            s += f", {ev['no_passage']}/{ev.get('n')} ohne Passage"
    return s


def vs_text(c: dict[str, Any], ref_label: str = "Champion") -> str:
    """One line: which paired differences against the reference are real; else '≈ Champion'."""
    if c.get("kind") == "trivial":
        return "Untergrenze"
    vr = c.get("vs_ref")
    if c.get("_is_ref"):
        return "Referenz"
    if c.get("tuned") is None:
        return STATUS_TEXT.get(((c.get("slots") or {}).get("tuned") or {}).get("status") or "", "–")
    if not vr:
        return "nicht gepaart"
    bits = []
    for key in ("auc", *METRICS):
        d = vr.get(key)
        if d and d.get("real"):
            lab, higher, pct = COLUMNS[key]
            better = (d["diff"] > 0) == higher
            bits.append(f"{'▲' if better else '▼'} {lab} {fmt_delta(d, pct).replace(' belegt', '')}")
    for key in GEN_COLUMNS:
        d = vs_ref(c, key)
        if d and d.get("real"):
            lab = COLUMNS[key][0]
            bits.append(f"{'▲' if d['diff'] > 0 else '▼'} {lab} {fmt_delta(d).replace(' belegt', '')}")
    return "; ".join(bits) if bits else f"≈ {ref_label}"


def drop_text(c: dict[str, Any], slot: str) -> str:
    g = (c.get("gen") or {}).get(slot) or {}
    return fmt_delta(g.get("drop")) if g.get("drop") else slot_text(c, slot) if g.get("status") != "ok" else "–"


PLACEHOLDER = re.compile(r"\{\{\s*([\w-]+)\.([\w-]+)\s*\}\}")


def placeholder(cands: dict[str, dict[str, Any]], cid: str, key: str) -> str:
    """Value behind ``{{<candidate>.<key>}}`` in the decision / comparison texts."""
    c = cands.get(cid)
    if c is None:
        return f"[? {cid}]"
    simple = {"auc": "auc", "far": "false_alarm_rate", "miss": "miss_rate", "rr": "review_recall",
              "acc": "accuracy", "reworded": "reworded", "blind": "blind", "rerecorded": "rerecorded",
              "hit1": "hit1", "cost": "cost", "t50_auc": "t50_auc", "t50_far": "t50_far", "t50_miss": "t50_miss",
              "t50_acc": "t50_acc", "t50_rr": "t50_rr"}
    if key in simple:
        k = simple[key]
        if value(c, k) is None:
            return cell(c, k) if k in GEN_COLUMNS or k.startswith("t50_") or c.get("tuned") is None else "–"
        return cell(c, k) if k != "cost" else f"{cell(c, k)} s"
    if key.startswith("vs_"):
        k = simple.get(key[3:])
        if k is None:
            return f"[? {key}]"
        d = vs_ref(c, k)
        if d:
            return fmt_delta(d, COLUMNS[k][2])
        return (slot_text(c, T50) if k.startswith("t50_") else "ausstehend") if value(c, k) is None else "–"
    if key == "t50_drop":
        d = (c.get(T50) or {}).get("dev_drop")
        return f"{fmt_delta(d)} (ungepaart)" if d and d.get("diff") is not None else slot_text(c, T50)
    if key.startswith("drop_"):
        return drop_text(c, key[5:])
    if key == "reviews":
        r = c.get("reviews") or {}
        return (f"{r.get('predicted', '–')}× Prüfen vorhergesagt, {r.get('hit', '–')} von {r.get('expected', '–')} "
                "Soll-Prüfen getroffen") if r else "ausstehend"
    if key == "vs":
        return vs_text(c)
    if key == "label":
        return c.get("label") or cid
    if key == "status":
        return ", ".join(f"{SLOT_LABELS[s]}: {STATUS_TEXT.get(st, st)}" for s, _, st in slot_states(c)
                         if st != "ok") or "vollständig"
    return f"[? {key}]"


def fill(text: Any, result: dict[str, Any]) -> Any:
    """Replace ``{{candidate.key}}`` placeholders in strings (recursively in lists/dicts)."""
    cands = {c["id"]: c for c in result.get("candidates") or []}
    if isinstance(text, str):
        return PLACEHOLDER.sub(lambda m: placeholder(cands, m.group(1), m.group(2)), text)
    if isinstance(text, list):
        return [fill(x, result) for x in text]
    if isinstance(text, dict):
        return {k: fill(v, result) for k, v in text.items()}
    return text


# --------------------------------------------------------------------------------------------
# team decisions (written by the UI) + teammate comparison
# --------------------------------------------------------------------------------------------


def load_team(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    d = load_yaml(path, DEFAULT_TEAM)
    return {k: v for k, v in (d.get("decisions") or {}).items() if isinstance(v, dict)}


def save_team_decision(decision_id: str, entry: dict[str, Any], path: str | Path | None = None) -> Path:
    """Record (or replace) the team's choice for one decision; keeps the others. ``when`` defaults to now."""
    p = _abs(path or DEFAULT_TEAM)
    cur = load_team(p)
    e = {k: v for k, v in entry.items() if v not in (None, "")}
    e.setdefault("when", _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    cur[decision_id] = e
    p.parent.mkdir(parents=True, exist_ok=True)
    header = ("# Team choices per open decision (experiments/contrib/decisions.yaml), recorded on the UI page\n"
              "# \"Team-Entscheidungen\" (or by hand). Keys = decision ids. Fields: choice, who, when, note.\n")
    p.write_text(header + yaml.safe_dump({"decisions": cur}, allow_unicode=True, sort_keys=False))
    return p


def git_head(repo: str | Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def zurich_status(comp: dict[str, Any]) -> dict[str, Any]:
    """Is the comparison written against the teammate repo's current HEAD?"""
    repo = _abs(os.environ.get(ENV_ZURICH) or comp.get("teammate_repo") or "sprintd_zurich")
    head = git_head(repo) if repo.exists() else None
    want = str(comp.get("written_against") or "")
    same = bool(head and want and (head.startswith(want) or want.startswith(head)))
    return {"repo": str(repo), "available": repo.exists(), "head": head, "written_against": want,
            "stale": bool(head) and not same}


# --------------------------------------------------------------------------------------------
# outputs
# --------------------------------------------------------------------------------------------


MATRIX_HEAD = ["Kandidat", "Flag-AUC [KI]", "Fehlalarme (CV)", "Verpasst (CV)", "Prüf-Recall", "Exakt 3 Klassen",
               "gepaart vs. Champion", "AUC umformuliert", "Δ umf.", "AUC blinde Tabelle", "Δ blind",
               "AUC neu aufgenommen", "Δ neu aufg.", "Beleg hit@1", "Passagen", "s/Anruf", "Hardware", "Lizenz",
               "E2E getestet"]


def matrix_rows(result: dict[str, Any], bold: bool = True) -> list[list[str]]:
    best = result.get("best") or {}
    rows = []
    for c in visible(result):
        c = {**c, "_is_ref": c["id"] == result.get("reference")}

        def b(key: str, txt: str) -> str:
            m = best.get(key)
            if not bold or not m or c["id"] not in m["ids"] or c.get("kind") != "candidate":
                return txt
            if c["_is_ref"] or key == "cost":
                tag = ""
            elif key == "hit1":
                tag = " (ungepaart, Zufall beachten)"
            else:
                tag = " belegt" if m["real_vs_ref"].get(c["id"]) else " (≈ Champion)"
            return f"**{txt}**{tag}"

        rows.append([
            c.get("label") or c["id"], b("auc", cell(c, "auc")), b("false_alarm_rate", cell(c, "false_alarm_rate")),
            b("miss_rate", cell(c, "miss_rate")), b("review_recall", cell(c, "review_recall")),
            b("accuracy", cell(c, "accuracy")), "Referenz" if c["_is_ref"] else vs_text(c),
            b("reworded", cell(c, "reworded")), drop_text(c, "reworded"), b("blind", cell(c, "blind")),
            drop_text(c, "blind"), b("rerecorded", cell(c, "rerecorded")), drop_text(c, "rerecorded"),
            b("hit1", cell(c, "hit1")), c.get("passages") or "–", b("cost", cell(c, "cost")),
            c.get("hardware") or "–", c.get("licence") or "–", c.get("e2e") or "–"])
    return rows


T50_HEAD = ["Kandidat", "Flag-AUC [KI]", "Fehlalarme (fix)", "Verpasst (fix)", "Exakt 3 Klassen (fix)",
            "Prüf-Recall (fix)", "CV in test50: Fehlalarme / Verpasst / Exakt", "gepaart vs. Champion (test50)",
            "Dev → test50 AUC (ungepaart)"]


def t50_vs_text(c: dict[str, Any]) -> str:
    vr = (c.get(T50) or {}).get("vs_ref")
    if not c.get(T50):
        return slot_text(c, T50)
    if not vr:
        return "Untergrenze" if c.get("kind") == "trivial" else "Referenz" if c.get("_is_ref") else "nicht gepaart"
    bits = []
    for key in ("t50_auc", *T50_KEYS):
        d = vs_ref(c, key)
        if d and d.get("real"):
            lab, higher, pct = COLUMNS[key]
            bits.append(f"{'▲' if (d['diff'] > 0) == higher else '▼'} {lab.replace('test50 ', '')} "
                        f"{fmt_delta(d, pct).replace(' belegt', '')}")
    return "; ".join(bits) if bits else "≈ Champion"


def test50_rows(result: dict[str, Any], bold: bool = True) -> list[list[str]]:
    """The test50 column group (own table): fixed-threshold numbers, CV-within-test50, paired vs champion."""
    best = result.get("best") or {}
    rows = []
    for c in visible(result):
        c = {**c, "_is_ref": c["id"] == result.get("reference")}

        def b(key: str, txt: str) -> str:
            m = best.get(key)
            if not bold or not m or c["id"] not in m["ids"] or c.get("kind") != "candidate":
                return txt
            tag = "" if c["_is_ref"] else (" belegt" if m["real_vs_ref"].get(c["id"]) else " (≈ Champion)")
            return f"**{txt}**{tag}"

        t = c.get(T50) or {}
        cvm = t.get("cv") or {}
        cv_txt = (" / ".join(fmt_num((cvm.get(k) or {}).get("value"), True) for k in ("false_alarm_rate", "miss_rate",
                                                                                      "accuracy")) if cvm else
                  slot_text(c, T50) if not t else "–")
        drop = t.get("dev_drop")
        rows.append([c.get("label") or c["id"], b("t50_auc", cell(c, "t50_auc")), b("t50_far", cell(c, "t50_far")),
                     b("t50_miss", cell(c, "t50_miss")), b("t50_acc", cell(c, "t50_acc")),
                     b("t50_rr", cell(c, "t50_rr")), cv_txt, t50_vs_text(c),
                     fmt_delta(drop) if drop and drop.get("diff") is not None else (slot_text(c, T50) if not t else "–")])
    return rows


def breakdown_rows(result: dict[str, Any]) -> list[list[str]]:
    """Per candidate with test50 data: exact label correct per call type and clean / noisy (n in brackets)."""
    out = []
    for c in visible(result):
        bd = (c.get(T50) or {}).get("breakdown")
        if not bd:
            continue
        cells = []
        for t in T50_TYPES:
            x = bd["types"].get(t)
            cells.append(f"{fmt_num(x['label_acc'], True)} ({x['n']})" if x else "–")
        for a in ("sauber", "verrauscht"):
            x = bd["audio"].get(a) or {}
            cells.append(f"{fmt_num(x.get('label_acc'), True)} ({x.get('n', 0)})" if x.get("n") else "–")
        out.append([c.get("label") or c["id"], *cells])
    return out


def _md_table(head: list[str], rows: list[list[str]]) -> list[str]:
    esc = [[str(x).replace("|", "\\|").replace("\n", " ") for x in r] for r in rows]
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head), *("| " + " | ".join(r) + " |" for r in esc)]


def render_markdown(result: dict[str, Any], decisions: dict[str, Any] | None = None,
                    comparison: dict[str, Any] | None = None, team: dict[str, dict[str, Any]] | None = None,
                    zurich: dict[str, Any] | None = None) -> str:
    out = ["# Team-Optionen: alle Kandidaten mit denselben Zahlen", "",
           f"Generiert {result['created']} von `callguard candidates` (Spezifikation `{_rel(result['spec'])}`, "
           f"{result['n_boot']} Bootstrap-Stichproben, Seed {result['seed']}). Nicht von Hand bearbeiten: Texte in "
           "`experiments/contrib/decisions.yaml` / `comparison_zurich.yaml` ändern und neu erzeugen.", "",
           "Lesehilfe: Dev-Split (48 Anrufe / 24 Dialoge), 95%-Bootstrap-KI über Zwillingsgruppen/Dialoge. AUC = "
           "Flag-AUC aus den Scores (schwellenfrei); Fehlalarme / Verpasst / Prüf-Recall / Exakt an der out-of-fold "
           "CV-Schwelle. **Fett** = bester Wert der Spalte unter den Kandidaten; „belegt“ nur, wenn das gepaarte KI "
           "gegen den Champion 0 ausschliesst, sonst „≈ Champion“. Δ = gepaarte Differenz zum eigenen abgestimmten "
           "Lauf (gleiche Anrufe). „ausstehend“ / „läuft noch“ füllt sich beim nächsten Lauf von `callguard "
           "candidates` automatisch. Der Holdout ist verbraucht und kommt hier nicht vor.", "",
           "## Kandidaten-Matrix", ""]
    out += _md_table(MATRIX_HEAD, matrix_rows(result))
    out += ["", "Prüfen-Fälle (CV, vorhergesagt, davon richtig; Soll 6 von 48): " + "; ".join(
        f"{c.get('short') or c['id']} {c['reviews']['predicted']} ({c['reviews']['hit']} richtig)"
        for c in visible(result) if c.get("reviews")) + "."]
    if result.get("evidence_note"):
        out += ["", result["evidence_note"]]
    out += ["", f"## {T50_TITLE}", "", f"> **{T50_BANNER}**", "",
            "Eigene Spaltengruppe, eigene Anrufe: fixe Schwelle = die auf Dev eingefrorene Konfiguration jeder Variante; "
            "CV in test50 = Schwelle out-of-fold innerhalb von test50 (Zwillingsgruppen zusammen), nur zum Vergleich. "
            "Gepaart gegen den Champion auf denselben test50-Anrufen (KI über A/B-Paare). „Dev → test50“ ist eine "
            "ungepaarte Differenz zweier getrennt gebooteter AUCs (verschiedene Anrufe), kein gepoolter Wert.", ""]
    out += _md_table(T50_HEAD, test50_rows(result))
    bd = breakdown_rows(result)
    if bd:
        out += ["", "Exakt richtig je Anruf-Typ und Aufnahme (fixe Schwelle, Anzahl Anrufe in Klammern):", ""]
        out += _md_table(["Kandidat", *T50_TYPES.values(), "sauber", "verrauscht"], bd)
    notes = [(c.get("label") or c["id"], c.get("note")) for c in visible(result) if c.get("note")]
    if notes:
        out += ["", "### Anmerkungen je Kandidat", ""] + [f"- **{lab}**: {n}" for lab, n in notes]
    out += ["", "### Zuordnung zu gespeicherten Varianten", "",
            "| Kandidat | abgestimmt | umformuliert | blinde Tabelle | neu aufgenommen | test50 (extern) |",
            "|---|---|---|---|---|---|"]
    for c in visible(result):
        sl = c.get("slots") or {}
        cells = []
        for s in ALL_SLOTS:
            st = sl.get(s) or {}
            if s == "reworded" and st.get("refs"):
                parts = ((c.get("gen") or {}).get("reworded") or {}).get("parts") or []
                cells.append(", ".join(f"`{p['ref']}` ({STATUS_TEXT[p['status']]})" for p in parts) or "–")
            elif st.get("ref"):
                cells.append(f"`{st['ref']}` ({STATUS_TEXT.get(st['status'], st['status'])})")
            else:
                cells.append(slot_text(c, s) if s == T50 else STATUS_TEXT.get(st.get("status") or "na", "–"))
        out.append(f"| {c.get('label') or c['id']} | " + " | ".join(cells) + " |")
    if result.get("pending"):
        out += ["", "### Ausstehend / läuft noch", ""]
        out += [f"- {p['label']}: {SLOT_LABELS[p['slot']]} `{p['ref']}` ({STATUS_TEXT[p['status']]})"
                for p in result["pending"]]
    team = team or {}
    if decisions and decisions.get("decisions"):
        out += ["", "## Offene Team-Entscheidungen", ""]
        if decisions.get("intro"):
            out += [fill(decisions["intro"], result), ""]
        for d in decisions["decisions"]:
            out += decision_markdown(fill(d, result), team.get(d.get("id") or ""))
    if comparison and comparison.get("rows"):
        out += comparison_markdown(fill(comparison, result), zurich)
    return "\n".join(out) + "\n"


def decision_markdown(d: dict[str, Any], chosen: dict[str, Any] | None = None) -> list[str]:
    out = [f"### {d.get('title') or d.get('id')}", ""]
    if d.get("question"):
        out += [f"**Frage:** {d['question']}", ""]
    if d.get("context"):
        out += [d["context"].strip(), ""]
    for o in d.get("options") or []:
        out += [f"- **Option {o.get('name')}**" + (f": {o['summary']}" if o.get("summary") else "")]
        for k, lab in (("pros", "pro"), ("cons", "contra"), ("cost", "Aufwand")):
            for x in _as_list(o.get(k)):
                out.append(f"  - {lab}: {x}")
    if d.get("recommendation"):
        out += ["", f"**Unsere Empfehlung:** {d['recommendation'].strip()}"]
    if d.get("would_change"):
        out += ["", "**Was die Empfehlung ändern würde:**"] + [f"- {x}" for x in _as_list(d["would_change"])]
    if d.get("sources"):
        out += ["", "Quellen: " + ", ".join(f"`{s}`" for s in _as_list(d["sources"]))]
    if chosen:
        out += ["", f"**Entscheid des Teams:** {chosen.get('choice', '–')} ({chosen.get('who', '?')}, "
                    f"{chosen.get('when', '?')})" + (f": {chosen['note']}" if chosen.get("note") else "")]
    else:
        out += ["", "**Entscheid des Teams:** offen"]
    return out + [""]


COMPARISON_HEAD = ["Thema", "Unser Ansatz (callguard)", "sprintd_zurich (Teamkollege)", "Messung / Beleg",
                   "Wirkung", "Empfehlung"]


def comparison_markdown(comp: dict[str, Any], zurich: dict[str, Any] | None = None) -> list[str]:
    out = ["## Unser Ansatz vs. sprintd_zurich (Teamkollege)", ""]
    want = str(comp.get("written_against") or "?")
    out.append(f"Geschrieben gegen Commit `{want[:7]}` von `{comp.get('teammate_repo_url') or comp.get('teammate_repo')}`.")
    if zurich and zurich.get("stale"):
        out.append(f"**Achtung:** das Repo steht jetzt auf `{(zurich.get('head') or '?')[:7]}`; der Vergleich muss "
                   "aktualisiert werden.")
    if comp.get("intro"):
        out += ["", comp["intro"].strip()]
    out += [""]
    out += _md_table(COMPARISON_HEAD, [[r.get("topic", ""), r.get("ours", ""), r.get("theirs", ""),
                                        r.get("evidence", ""), r.get("impact", ""),
                                        f"**{r.get('recommendation', 'offen')}**" + (f": {r['why']}" if r.get("why") else "")]
                                       for r in comp["rows"]])
    return out + [""]


def _rel(p: Any) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except (ValueError, TypeError):
        return str(p)


def write_outputs(result: dict[str, Any], out_dir: str | Path | None = None, doc: str | Path | None = None,
                  decisions: dict[str, Any] | None = None, comparison: dict[str, Any] | None = None,
                  team: dict[str, dict[str, Any]] | None = None, zurich: dict[str, Any] | None = None
                  ) -> tuple[Path, Path | None]:
    d = _abs(out_dir or DEFAULT_OUT)
    d.mkdir(parents=True, exist_ok=True)
    pj = d / "candidates.json"
    pj.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    pm = None
    if doc is not False:
        pm = _abs(doc or DEFAULT_DOC)
        pm.parent.mkdir(parents=True, exist_ok=True)
        pm.write_text(render_markdown(result, decisions, comparison, team, zurich))
    return pj, pm


def load_or_compute(spec_path: str | Path | None = None, out_dir: str | Path | None = None,
                    roots: dict[str, str | Path] | None = None) -> tuple[dict[str, Any], str]:
    """candidates.json if nothing changed since (rows, variant folders, spec); else analyse live with the cached
    evidence summaries (no evidence computation in the UI). Returns (result, "file" | "live")."""
    spec = load_spec(spec_path)
    all_roots = {**DEFAULT_ROOTS, **(spec.get("data_roots") or {}), **(roots or {})}
    data = Data(all_roots, spec.get("experiments_dir"), root_datasets(spec))
    p = _abs(out_dir or DEFAULT_OUT) / "candidates.json"
    if p.exists():
        try:
            res = json.loads(p.read_text())
            if (res.get("spec") == spec.get("_path") and res.get("roots") == {k: str(v) for k, v in data.roots.items()}
                    and float(res.get("fingerprint") or 0) >= data.fingerprint(spec.get("_path"))):
                return res, "file"
        except (OSError, ValueError):
            pass
    refs = [r for c in spec["candidates"] if not c.get("trivial")
            for r in [c.get("evidence_ref") or resolve(data, c.get("tuned"))["ref"]] if r]
    ev = evidence_for(data, refs, _abs(out_dir or DEFAULT_OUT) / "evidence_cache.json", None)
    return analyse(spec, all_roots, evidence=ev), "live"
