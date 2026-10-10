"""The locked dialogue split: one ``holdout`` fold that tuning never sees, plus dev folds for CV.

``config/splits.yaml`` is generated once (``callguard splits --make``, refuses to overwrite) and then
committed. Every tuning step (prompts, weights, thresholds, few-shot pools, learned fusion) runs on the
dev dialogues with cross-validation over the dev folds; the holdout is scored once per final
candidate with ``callguard eval --split holdout``, and every such run is appended to
``runs/holdout_log.jsonl`` so peeking is visible.

Unit = twin group: the clean and noisy recordings of a dialogue always share a fold, and so do the
Stufe2 twin dialogues (same script, different context); ``group_of`` gives the same unit to the
bootstrap in :mod:`callguard.stats`. Calls whose
dialogue is not in the file (synthetic calls, new data) are ``unassigned``: never dev, never holdout.
"""

from __future__ import annotations

import json
import random
import re
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

import yaml

from callguard.cache import stable_hash
from callguard.config import ROOT, AppConfig
from callguard.data import Call, dialogue_of

SPLITS_PATH = ROOT / "config" / "splits.yaml"
HOLDOUT = "holdout"
# external: only calls whose dialogue is in NO fold of the case split (synthetic sets, data_synth/). It
# can never contain a case dialogue, so it is not a holdout look; CV folds come from data.split_dialogues
# (twin groups together).
EXTERNAL = "external"
Split = Literal["dev", "holdout", "all", "external"]
SPLIT_CHOICES = ("dev", "holdout", "all", "external")


class SplitsMissing(FileNotFoundError):
    pass


@dataclass
class Splits:
    holdout: list[str]
    dev_folds: dict[int, list[str]]
    meta: dict[str, Any] = field(default_factory=dict)
    path: Path | None = None
    groups: dict[str, list[str]] = field(default_factory=dict)  # twin group id -> its dialogues

    def group_map(self) -> dict[str, str]:
        """dialogue id -> twin group id (dialogues without a twin are their own group)."""
        return {d: g for g, ds in self.groups.items() for d in ds}

    def group_of(self, call_or_dialogue: str) -> str:
        d = dialogue_of(call_or_dialogue)
        return self.group_map().get(d, d)

    def fold_of(self) -> dict[str, int | str]:
        """dialogue id -> dev fold number or ``"holdout"``."""
        out: dict[str, int | str] = {d: HOLDOUT for d in self.holdout}
        for k, ds in self.dev_folds.items():
            out.update({d: k for d in ds})
        return out

    def dev_fold_of(self) -> dict[str, int]:
        """dialogue id -> dev fold, for cross-validation over the dev dialogues only."""
        return {d: k for k, ds in self.dev_folds.items() for d in ds}

    def all_fold_of(self) -> dict[str, int]:
        """Dev folds plus the holdout as one more fold (only for ``--split all`` CV)."""
        out = self.dev_fold_of()
        nxt = max(self.dev_folds, default=-1) + 1
        out.update({d: nxt for d in self.holdout})
        return out

    def dev_dialogues(self) -> list[str]:
        return sorted(d for ds in self.dev_folds.values() for d in ds)

    def holdout_dialogues(self) -> list[str]:
        return sorted(self.holdout)

    def select(self, calls: Sequence[Call], split: str) -> list[Call]:
        if split not in SPLIT_CHOICES:
            raise ValueError(f"split must be one of {SPLIT_CHOICES}, got {split!r}")
        if split == "all":
            return list(calls)
        if split == EXTERNAL:
            known = set(self.holdout_dialogues()) | set(self.dev_dialogues())
            return [c for c in calls if c.dialogue_id not in known]
        wanted = set(self.holdout_dialogues() if split == HOLDOUT else self.dev_dialogues())
        return [c for c in calls if c.dialogue_id in wanted]


# --------------------------------------------------------------------------------------------
# load / make
# --------------------------------------------------------------------------------------------


def load_splits(path: str | Path | None = None, *, required: bool = True) -> Splits | None:
    p = Path(path) if path else SPLITS_PATH
    if not p.exists():
        if required:
            raise SplitsMissing(f"{p} does not exist: create the locked split once with `callguard splits --make`")
        return None
    raw = yaml.safe_load(p.read_text()) or {}
    holdout = [str(d) for d in raw.get("holdout") or []]
    dev = {int(k): [str(d) for d in v or []] for k, v in (raw.get("dev_folds") or {}).items()}
    seen = Counter(holdout + [d for ds in dev.values() for d in ds])
    dup = sorted(d for d, n in seen.items() if n > 1)
    if dup:
        raise ValueError(f"{p}: dialogues in more than one fold: {dup}")
    groups = {str(g): [str(d) for d in ds or []] for g, ds in (raw.get("groups") or {}).items()}
    meta = {k: v for k, v in raw.items() if k not in ("holdout", "dev_folds", "groups")}
    s = Splits(holdout=holdout, dev_folds=dev, meta=meta, path=p, groups=groups)
    fold = s.fold_of()
    for g, ds in groups.items():
        if len({fold.get(d) for d in ds}) > 1:
            raise ValueError(f"{p}: twin group {g} ({ds}) is split across folds")
    return s


def dev_dialogues(path: str | Path | None = None) -> list[str]:
    return load_splits(path).dev_dialogues()  # type: ignore[union-attr]


def holdout_dialogues(path: str | Path | None = None) -> list[str]:
    return load_splits(path).holdout_dialogues()  # type: ignore[union-attr]


def fold_of(path: str | Path | None = None) -> dict[str, int | str]:
    return load_splits(path).fold_of()  # type: ignore[union-attr]


_CACHE: dict[str, tuple[float, Splits | None]] = {}


def cached_splits(path: str | Path | None = None) -> Splits | None:
    """The split file, re-read only when it changes (stats calls ``group_of`` per row)."""
    p = Path(path) if path else SPLITS_PATH
    mtime = p.stat().st_mtime if p.exists() else -1.0
    hit = _CACHE.get(str(p))
    if hit is None or hit[0] != mtime:
        hit = (mtime, load_splits(p, required=False))
        _CACHE[str(p)] = hit
    return hit[1]


def group_of(call_or_dialogue: str, path: str | Path | None = None) -> str:
    """Resampling unit of a call: its twin group from config/splits.yaml, else its dialogue."""
    s = cached_splits(path)
    return s.group_of(call_or_dialogue) if s else dialogue_of(call_or_dialogue)


def _stratum(c: Call) -> tuple[str, int]:
    return (c.expected.label if c.expected else "unknown", c.level)


_TITLE_ID = re.compile(r"^[A-Z]\d{2}\s*·\s*")


def find_twins(calls: Sequence[Call]) -> dict[str, list[str]]:
    """Twin groups: dialogues of one level with the same title (minus the id) and the same Testziel.

    The case's Stufe2 dialogues come in pairs (C01/C02 ... C15/C16) that are 90-97% the same script and
    differ only in the context that makes one harmless and the other misconduct. Splitting a pair across
    folds would leak (tune on one twin, score the other), so a pair is one unit for folds and bootstrap.
    Stufe1 dialogues that merely share a family (D02 alarm / D03 harmless) have different titles and
    scripts (text similarity ~5%) and are not grouped. Group id = the dialogue ids joined by ``+``."""
    by_key: dict[tuple[int, str, str], list[str]] = {}
    for c in calls:
        title = _TITLE_ID.sub("", c.title or "").strip().lower()
        if not title:
            continue
        key = (c.level, title, c.expected.family if c.expected else "")
        if c.dialogue_id not in by_key.setdefault(key, []):
            by_key[key].append(c.dialogue_id)
    groups = {}
    for ds in by_key.values():
        if len(ds) > 1:
            ds = sorted(ds)
            groups["+".join(ds)] = ds
    return dict(sorted(groups.items()))


def make_splits(calls: Sequence[Call], n_dev_folds: int = 4, seed: int = 13,
                groups: dict[str, list[str]] | None = None) -> Splits:
    """``n_dev_folds + 1`` buckets of equal size (in dialogues), filled with whole twin groups, stratified
    by (expected label, level); the bucket whose label and level mix is closest to the whole set becomes
    the holdout. Clean and noisy recordings share their dialogue's fold; twins share a fold.

    Units (twin groups first, being the largest, then single dialogues; seeded shuffle within stratum)
    are placed greedily into the bucket that still has room and holds the fewest dialogues of the unit's
    labels and level, so every bucket gets its share of every label and level as far as the case allows
    (4 review dialogues, all Stufe3, cannot reach 5 buckets).
    """
    groups = find_twins(calls) if groups is None else groups
    n_buckets = n_dev_folds + 1
    dlg_stratum: dict[str, tuple[str, int]] = {}
    for c in calls:
        dlg_stratum.setdefault(c.dialogue_id, _stratum(c))
    in_group = {d for ds in groups.values() for d in ds}
    units = [list(ds) for ds in groups.values() if all(d in dlg_stratum for d in ds)]
    units += [[d] for d in sorted(dlg_stratum) if d not in in_group]
    rng = random.Random(seed)
    rng.shuffle(units)
    # big units first; within a size, by stratum so the strata are dealt out together
    units.sort(key=lambda u: (-len(u), sorted(dlg_stratum[d] for d in u)))

    n = len(dlg_stratum)
    cap = -(-n // n_buckets)  # ceil: buckets of 6 for 30 dialogues
    buckets: list[list[str]] = [[] for _ in range(n_buckets)]
    for u in units:
        labels = Counter(dlg_stratum[d][0] for d in u)
        levels = Counter(dlg_stratum[d][1] for d in u)

        def cost(j: int) -> tuple[float, ...]:
            b = buckets[j]
            over = max(0, len(b) + len(u) - cap)
            same_label = sum(min(labels[k], 1) * sum(1 for d in b if dlg_stratum[d][0] == k) for k in labels)
            same_level = sum(min(levels[k], 1) * sum(1 for d in b if dlg_stratum[d][1] == k) for k in levels)
            return (over, same_label + same_level, len(b), rng.random())

        buckets[min(range(n_buckets), key=cost)].extend(u)

    labels_all = Counter(s[0] for s in dlg_stratum.values())
    levels_all = Counter(s[1] for s in dlg_stratum.values())

    def distance(b: list[str]) -> float:
        lab = Counter(dlg_stratum[d][0] for d in b)
        lev = Counter(dlg_stratum[d][1] for d in b)
        frac = len(b) / n if n else 0
        return (sum(abs(lab[k] - frac * v) for k, v in labels_all.items())
                + sum(abs(lev[k] - frac * v) for k, v in levels_all.items()) + abs(len(b) - n / n_buckets))

    order = list(range(n_buckets))
    rng.shuffle(order)  # seeded tie-break among equally representative buckets
    h = min(order, key=lambda j: distance(buckets[j]))
    dev = [b for j, b in enumerate(buckets) if j != h]
    return Splits(holdout=sorted(buckets[h]), dev_folds={k: sorted(b) for k, b in enumerate(dev)},
                  groups=groups,
                  meta={"seed": seed, "n_dev_folds": n_dev_folds, "n_dialogues": n,
                        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "method": "whole twin groups, stratified by (expected label, level); clean+noisy of a "
                                  "dialogue together"})


def describe(splits: Splits, calls: Sequence[Call]) -> dict[str, dict[str, Any]]:
    """Per fold: dialogues, labels, levels (for the YAML comment and `callguard splits`)."""
    strat = {c.dialogue_id: _stratum(c) for c in calls}
    groups = {HOLDOUT: splits.holdout, **{f"dev{k}": v for k, v in sorted(splits.dev_folds.items())}}
    out = {}
    for name, ds in groups.items():
        out[name] = {"n": len(ds),
                     "labels": dict(sorted(Counter(strat[d][0] for d in ds if d in strat).items())),
                     "levels": dict(sorted(Counter(strat[d][1] for d in ds if d in strat).items()))}
    return out


def write_splits(splits: Splits, calls: Sequence[Call], path: str | Path | None = None, *,
                 overwrite: bool = False, note: str | None = None) -> Path:
    p = Path(path) if path else SPLITS_PATH
    if p.exists() and not overwrite:
        raise FileExistsError(f"{p} exists and is locked; delete it by hand only if you really mean to "
                              f"re-split (that invalidates every holdout number so far)")
    desc = describe(splits, calls)
    lines = ["# LOCKED dialogue split. Generated once by `callguard splits --make`; do not edit or regenerate.",
             "# Tune only on dev folds (CV over dev0..devN). The holdout is scored once per final candidate:",
             "#   callguard eval -c <profile> --split holdout     (every run is logged to runs/holdout_log.jsonl)",
             "# Fold composition (dialogues; labels; levels):"]
    for name, d in desc.items():
        lines.append(f"#   {name:8s} n={d['n']}  labels={d['labels']}  levels={d['levels']}")
    if splits.groups:
        lines.append(f"# Twin groups (one unit for folds and for the bootstrap): {len(splits.groups)}")
    if note:
        lines += [f"# NOTE: {x}" for x in note.splitlines()]
    body = {**splits.meta, "holdout": splits.holdout, "dev_folds": splits.dev_folds, "groups": splits.groups}
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + "\n" + yaml.safe_dump(body, sort_keys=False, allow_unicode=True))
    splits.path = p
    return p


# --------------------------------------------------------------------------------------------
# provenance + holdout log
# --------------------------------------------------------------------------------------------


def git_info(root: Path = ROOT) -> dict[str, Any]:
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True,
                                  timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    sha = git("rev-parse", "--short=10", "HEAD")
    dirty = bool(git("status", "--porcelain", "--untracked-files=no"))
    return {"sha": sha or None, "dirty": dirty, "branch": git("rev-parse", "--abbrev-ref", "HEAD") or None}


def config_hash(cfg: AppConfig) -> str:
    return stable_hash(cfg.model_dump(mode="json", exclude={"source_path"}))


def holdout_log_path(cfg: AppConfig) -> Path:
    return cfg.paths.resolve("runs_dir") / "holdout_log.jsonl"


def log_holdout_run(cfg: AppConfig, m: dict[str, Any], n_calls: int, *, kind: str = "eval",
                    overrides: Sequence[str] = (), extra: dict[str, Any] | None = None) -> Path:
    """Append one line per look at the holdout. Never rewritten: this file is the peeking record."""
    flag, alarm = m.get("flag", {}), m.get("alarm", {})
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "kind": kind, "config": cfg.name,
        "config_hash": config_hash(cfg), "overrides": list(overrides), "git": git_info(), "n_calls": n_calls,
        "metrics": {"flag_f1": flag.get("f1"), "flag_precision": flag.get("precision"),
                    "flag_recall": flag.get("recall"), "false_alarm_rate": flag.get("false_alarm_rate"),
                    "miss_rate": flag.get("miss_rate"), "alarm_f1": alarm.get("f1"),
                    "accuracy": m.get("accuracy"),
                    "review_escalation": (m.get("review_handling") or {}).get("escalation_rate"),
                    "errors": m.get("errors"), "check_failures": (m.get("check_failures") or {}).get("calls")},
        **(extra or {}),
    }
    p = holdout_log_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    return p


def holdout_looks(cfg: AppConfig) -> int:
    p = holdout_log_path(cfg)
    return sum(1 for line in p.read_text().splitlines() if line.strip()) if p.exists() else 0
