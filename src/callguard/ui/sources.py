"""Where the UI reads results from, and the experiment / holdout files it displays. Pure (no Streamlit).

Sources (sidebar "Quelle"):

* ``profile:<name>``: ``runs/<name>/<call_id>/result.json`` written by the ``json_dir`` sink; decided
  with the profile ``config/<name>.yaml`` (the launch profile, or another one that has results).
* ``exp:<experiment>/<variant>``: ``runs/experiments/<experiment>/<variant>/results.jsonl`` written by
  ``callguard experiment``; decided with that variant's exact config (spec + variant overrides).
  Read-only: keyword re-runs and processing write to profile runs only.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from callguard.cache import stable_hash
from callguard.config import ROOT, AppConfig, apply_overrides, load_config, resolve_config_path
from callguard.types import CallResult
from callguard.ui.backend import Loaded

log = logging.getLogger("callguard")


@dataclass(frozen=True)
class Source:
    key: str  # "profile:local" | "exp:smoke/all"
    kind: str  # "profile" | "experiment"
    name: str  # profile name, or "<experiment>/<variant>"
    path: Path  # runs/<profile> or runs/experiments/<exp>/<variant>
    label: str  # German, for the selector
    experiment: str | None = None
    variant: str | None = None

    @property
    def read_only(self) -> bool:
        return self.kind != "profile"


def profile_source(name: str, runs_root: Path) -> Source:
    return Source(f"profile:{name}", "profile", name, runs_root / name, f"Profil-Lauf · {name}")


def source_from_key(key: str, runs_root: Path) -> Source:
    kind, _, name = key.partition(":")
    if kind == "profile":
        return profile_source(name, runs_root)
    exp, _, var = name.partition("/")
    return Source(key, "experiment", name, runs_root / "experiments" / exp / var, f"Experiment · {exp} / {var}",
                  experiment=exp, variant=var)


def list_sources(runs_root: str | Path, current_profile: str) -> list[Source]:
    """The launch profile first, then other profiles that have results and a config file, then every
    experiment variant with a ``results.jsonl``."""
    root = Path(runs_root)
    out = [profile_source(current_profile, root)]
    if root.is_dir():
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            if d.name in (current_profile, "experiments", "logs", "asr_eval") or d.name.startswith(("_", ".")):
                continue
            if not any(d.glob("*/result.json")):
                continue
            try:
                resolve_config_path(d.name)
            except Exception:
                continue
            out.append(profile_source(d.name, root))
        exp_root = root / "experiments"
        for f in sorted(exp_root.glob("*/*/results.jsonl")) if exp_root.is_dir() else []:
            exp, var = f.parent.parent.name, f.parent.name
            out.append(source_from_key(f"exp:{exp}/{var}", root))
    return out


def source_config(src: Source, sets: Sequence[str]) -> AppConfig:
    """The config a source's results are decided with; the UI's ``--set`` overrides apply on top."""
    if src.kind == "profile":
        return load_config(src.name, list(sets))
    from callguard.experiments import _named_paths, load_spec, variant_raw  # deferred: heavy import

    spec_path = src.path.parent / "spec.yaml"
    spec = load_spec(spec_path)
    raw, p = variant_raw(spec, spec.variant(src.variant or ""))
    raw = apply_overrides(raw, _named_paths(raw, list(sets)))
    cfg = AppConfig(**raw)
    cfg.source_path = str(p)
    return cfg


_JSONL: dict[str, tuple[tuple[int, int], Loaded]] = {}
_JSONL_LOCK = threading.Lock()


def load_jsonl(vdir: str | Path) -> Loaded:
    """``results.jsonl`` of an experiment variant as a ``Loaded``. ``paths[call_id]`` points at a
    (virtual) ``<vdir>/_ui/<call_id>/result.json`` so snippets the UI cuts land next to the variant."""
    vdir = Path(vdir)
    f = vdir / "results.jsonl"
    out = Loaded()
    if not f.is_file():
        return out
    st = f.stat()
    version = (st.st_mtime_ns, st.st_size)
    key = str(f.resolve())
    with _JSONL_LOCK:
        hit = _JSONL.get(key)
    if hit is not None and hit[0] == version:
        return hit[1]
    for i, line in enumerate(f.read_text().splitlines()):
        if not line.strip():
            continue
        try:
            r = CallResult.model_validate_json(line)
        except Exception as e:
            out.errors.append(f"{f.name}:{i + 1}: {type(e).__name__}: {str(e)[:200]}")
            continue
        if r.call_id in out.results:
            out.errors.append(f"{f.name}:{i + 1}: duplicate call id {r.call_id!r}; ignored")
            continue
        out.results[r.call_id] = r
        out.paths[r.call_id] = vdir / "_ui" / r.call_id / "result.json"
    out.signature = stable_hash([key, *version])
    with _JSONL_LOCK:
        _JSONL[key] = (version, out)
    return out


# --------------------------------------------------------------------------------------------
# experiments (runs/experiments/*/summary.json) and the holdout log
# --------------------------------------------------------------------------------------------


def load_summaries(runs_root: str | Path) -> list[dict[str, Any]]:
    out = []
    for p in sorted((Path(runs_root) / "experiments").glob("*/summary.json")):
        try:
            s = json.loads(p.read_text())
        except Exception as e:
            log.warning("UI: unreadable %s: %s", p, e)
            continue
        s["_path"] = str(p)
        out.append(s)
    return out


def _ci(block: dict[str, Any] | None, k: str) -> tuple[float | None, float | None]:
    c = ((block or {}).get("ci") or {}).get(k) or {}
    return c.get("lo"), c.get("hi")


def variant_rows(summary: dict[str, Any], metric: str = "flag_f1") -> list[dict[str, Any]]:
    """One row per variant: the primary block (out-of-fold CV if present, else the fixed threshold)."""
    rows = []
    for name, v in (summary.get("variants") or {}).items():
        primary = v.get("cv") or v.get("fixed") or {}
        lo, hi = _ci(primary, metric)
        cost = v.get("cost") or {}
        tags = [t for t, on in (("ORACLE", v.get("oracle")), ("DEGRADED", v.get("degraded"))) if on]
        if (v.get("meta") or {}).get("refuse_from"):
            tags.append(f"Re-Fusion von {(v.get('meta') or {})['refuse_from']}")
        rows.append({
            "variant": name, "basis": "CV" if v.get("cv") else "fest", "n": v.get("n_calls"),
            "value": primary.get(metric), "lo": lo, "hi": hi,
            "flag_f1": primary.get("flag_f1"), "flag_precision": primary.get("flag_precision"),
            "flag_recall": primary.get("flag_recall"), "far": primary.get("false_alarm_rate"),
            "miss": primary.get("miss_rate"), "alarm_f1": primary.get("alarm_f1"),
            "review_recall": primary.get("review_recall"), "accuracy": primary.get("accuracy"),
            "s_per_call": cost.get("check_compute_s_total_per_call"), "llm_calls": cost.get("llm_calls_per_call"),
            "threshold": (v.get("suggestion") or {}).get("threshold"),
            "description": (v.get("meta") or {}).get("description") or "",
            "tags": ", ".join(tags), "commit": (v.get("commit") or "") + ("*" if v.get("dirty") else ""),
        })
    rows.sort(key=lambda r: (r["value"] is None, -(r["value"] or 0.0)))
    return rows


def comparison_rows(summary: dict[str, Any], basis: str = "cv") -> list[dict[str, Any]]:
    """Paired bootstrap differences per comparison and metric (b - a)."""
    rows = []
    for c in summary.get("comparisons") or []:
        block = c.get(basis) or c.get("fixed") or {}
        for metric, p in (block.get("paired") or {}).items():
            if metric.startswith("_") or not isinstance(p, dict):
                continue
            rows.append({"a": c.get("a"), "b": c.get("b"), "metric": metric, "a_value": p.get("a"),
                         "b_value": p.get("b"), "diff": p.get("diff"), "lo": p.get("lo"), "hi": p.get("hi"),
                         "real": bool(p.get("real")), "better": p.get("better")})
        mc = block.get("mcnemar_flag") or {}
        if mc:
            rows.append({"a": c.get("a"), "b": c.get("b"), "metric": "McNemar (Markierung) p", "a_value": mc.get("a_only"),
                         "b_value": mc.get("b_only"), "diff": None, "lo": None, "hi": None,
                         "real": (mc.get("p") or 1.0) < 0.05, "better": None, "p": mc.get("p")})
    return rows


def flip_rows(summary: dict[str, Any], a: str, b: str, basis: str = "cv") -> list[dict[str, Any]]:
    for c in summary.get("comparisons") or []:
        if c.get("a") == a and c.get("b") == b:
            return list(((c.get(basis) or c.get("fixed") or {}).get("flips")) or [])
    return []


def report_images(experiment: str, report_dir: Path | None = None) -> list[Path]:
    d = (report_dir or ROOT / "research" / "report") / experiment
    return sorted(d.glob("*.png")) if d.is_dir() else []


def read_text(path: Path) -> str | None:
    try:
        return path.read_text()
    except OSError:
        return None


def read_holdout_log(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        return []
    out = []
    for line in p.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out
