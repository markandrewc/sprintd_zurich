"""YAML config loading.

* ``extends: base.yaml`` merges this file on top of another (deep merge; lists are replaced; a plugin
  block whose ``type`` changes is replaced whole, so ``asr: {type: reference}`` does not inherit the
  faster-whisper params of the parent).
* ``${VAR}`` and ``${VAR:-default}`` in string values are read from the environment (after the
  ``extends`` merge, before ``--set``), so one profile serves several machines:
  ``base_url: http://${CALLGUARD_GPU_HOST:-gpu-pc}:8000/v1``. See :func:`expand_env`.
* ``--set fusion.threshold=0.5`` style overrides via :func:`apply_overrides`.
* Relative paths are resolved against the project root (the directory holding ``pyproject.toml``).
"""

from __future__ import annotations

import copy
import hashlib
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class ConfigError(ValueError):
    """A profile that cannot be loaded as written (e.g. an unset environment variable)."""


def find_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / "pyproject.toml").exists() and (cand / "src" / "callguard").exists():
            return cand
    return Path(__file__).resolve().parents[2]


ROOT = find_root()


class Paths(BaseModel):
    data_dir: str = "data_upstream/inventx-case-study/data"
    keywords: str = "config/keywords.json"
    criteria: str = "config/criteria.yaml"
    runs_dir: str = "runs"
    cache_dir: str = ".cache"
    # officer tuning overlay (callguard feedback apply); absent file = no change. None/"" = never load one
    tuning: str | None = "config/tuning.yaml"

    def resolve(self, name: str) -> Path:
        p = Path(getattr(self, name))
        return p if p.is_absolute() else ROOT / p


class AppConfig(BaseModel):
    name: str = "default"
    description: str = ""
    paths: Paths = Field(default_factory=Paths)
    asr: dict[str, Any]
    diarizer: dict[str, Any] = Field(default_factory=lambda: {"type": "none"})
    llms: dict[str, dict[str, Any]] = Field(default_factory=dict)
    checks: list[dict[str, Any]] = Field(default_factory=list)
    fusion: dict[str, Any] = Field(default_factory=lambda: {"type": "weighted"})
    sinks: list[dict[str, Any]] = Field(default_factory=list)
    families: list[str] | None = None  # restrict to these family ids (None = all enabled)
    snippets: dict[str, Any] = Field(default_factory=lambda: {"pad": 2.0, "link_pad": 10.0})
    app: dict[str, Any] = Field(default_factory=lambda: {"base_url": "http://localhost:8501"})
    # Transcript views (docs/design/v2_plan.md §1). Empty -> one view "main" = asr + diarizer (v1).
    # name -> {lang, asr?, diarize?} (ASR view) or {lang, from, translator} (translated view).
    views: dict[str, dict[str, Any]] = Field(default_factory=dict)
    primary_view: str | None = None  # passages, snippets, UI transcript; default: first view
    check_view: str | None = None  # overrides every check's ``view`` (experiments)
    extra_views: list[str] = Field(default_factory=list)  # computed even if no check reads them
    # DISPLAY-ONLY views (callguard.views.parse_display_views): translated from a computed view after the
    # decision, stored in CallResult.display_views, never given to checks or fusion. name -> {lang, from?,
    # translator, description?, in_pipeline?}. Left out of the config hash while empty (old hashes unchanged).
    display_views: dict[str, dict[str, Any]] = Field(default_factory=dict)
    # set by load_config when a tuning overlay was applied: {path, hash, profile_scoped, applied}
    tuning: dict[str, Any] | None = None
    source_path: str | None = None


def hash_dump(cfg: "AppConfig") -> dict[str, Any]:
    """The config as hashed for provenance / experiment stamps: no ``source_path``; ``display_views`` only when
    set (a field added later must not change the hash of every existing config)."""
    exclude = {"source_path"} | (set() if cfg.display_views else {"display_views"})
    return cfg.model_dump(mode="json", exclude=exclude)


def _deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and not _swaps_type(out[k], v):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _swaps_type(base: dict, over: dict) -> bool:
    """Another plugin type means other constructor params: inherit nothing from the old block."""
    return "type" in over and "type" in base and over["type"] != base["type"]


def _load_raw(path: Path) -> dict:
    data = yaml.safe_load(path.read_text()) or {}
    parent = data.pop("extends", None)
    if parent:
        parent_path = (path.parent / parent).resolve()
        data = _deep_merge(_load_raw(parent_path), data)
    return data


def _parse_scalar(v: str) -> Any:
    return yaml.safe_load(v)


# ``$${...}`` is the escape for a literal ``${...}``; group 1 is "$" then.
_ENV_REF = re.compile(r"\$(\$?)\{([^}]*)\}")
_ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_INT = re.compile(r"[-+]?(?:0|[1-9][0-9]*)")
_FLOAT = re.compile(r"[-+]?(?:0|[1-9][0-9]*)\.[0-9]+(?:[eE][-+]?[0-9]+)?")


def _typed(text: str) -> Any:
    """Type a value that was nothing but one ``${...}``, so ``threshold: ${T:-0.55}`` stays a number
    and ``enabled: ${X:-false}`` a real False (``bool("false")`` is True). Deliberately narrower than
    YAML: ``0123`` (a PIN, a token) and ``yes``/``no`` stay text."""
    low = text.strip().lower()
    if low in ("true", "false"):
        return low == "true"
    if low in ("null", "~"):
        return None
    if _INT.fullmatch(text.strip()):
        return int(text)
    if _FLOAT.fullmatch(text.strip()):
        return float(text)
    return text


def expand_env(obj: Any, environ: Mapping[str, str] | None = None, *, source: str | Path | None = None) -> Any:
    """Copy of ``obj`` with ``${VAR}`` / ``${VAR:-default}`` replaced in every string value.

    Shell semantics for ``:-``: the default applies when the variable is unset *or empty*. An unset
    variable without a default raises :class:`ConfigError` instead of becoming "" (a silent
    ``http://:8000/v1`` fails much later and far less clearly). Keys are never expanded; ``$${X}``
    gives a literal ``${X}``; nested references (``${A:-${B}}``) are not supported. A string that is
    exactly one reference is typed by :func:`_typed`, embedded references always give text.
    """
    env = os.environ if environ is None else environ
    where = f" in {source}" if source else ""

    def sub(m: re.Match[str]) -> str:
        escaped, body = m.group(1), m.group(2)
        if escaped:
            return "${" + body + "}"
        name, sep, default = body.partition(":-")
        if not _ENV_NAME.fullmatch(name):
            raise ConfigError(f"bad environment reference ${{{body}}}{where}: expected ${{NAME}} or "
                              f"${{NAME:-default}}")
        if "${" in default:
            raise ConfigError(f"nested environment reference ${{{body}}}{where} is not supported")
        value = env.get(name)
        if value:
            return value
        if sep:
            return default
        if value is not None:
            return value  # set but empty, no default: "" as in the shell
        raise ConfigError(f"environment variable {name} is not set{where} (referenced as ${{{name}}}; "
                          f"export it or write ${{{name}:-default}})")

    def walk(v: Any) -> Any:
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, str) and "${" in v:
            m = _ENV_REF.fullmatch(v)
            out = _ENV_REF.sub(sub, v)
            return _typed(out) if m and not m.group(1) else out
        return v

    return walk(obj)


def apply_overrides(raw: dict, overrides: list[str] | None) -> dict:
    """``["fusion.threshold=0.5", "checks.1.enabled=false"]`` -> mutate a copy of ``raw``."""
    raw = copy.deepcopy(raw)
    for item in overrides or []:
        key, _, value = item.partition("=")
        cur: Any = raw
        parts = key.split(".")
        for part in parts[:-1]:
            if isinstance(cur, list):
                cur = cur[int(part)]
            else:
                cur = cur.setdefault(part, {})
        last = parts[-1]
        if isinstance(cur, list):
            cur[int(last)] = _parse_scalar(value)
        else:
            cur[last] = _parse_scalar(value)
    return raw


def resolve_config_path(path: str | Path) -> Path:
    p = Path(path)
    if p.exists():
        return p.resolve()
    for cand in (ROOT / p, ROOT / "config" / p, ROOT / "config" / f"{p}.yaml"):
        if cand.exists():
            return cand.resolve()
    raise FileNotFoundError(f"config {path!r} not found (looked in ., {ROOT}, {ROOT / 'config'})")


# --------------------------------------------------------------------------------------------
# Tuning overlay (config/tuning.yaml, written by `callguard feedback apply` / the UI)
# --------------------------------------------------------------------------------------------

TUNING_FUSION_KEYS = ("threshold", "review_band")  # the only knobs an overlay may set (+ check weights)


def tuning_values(data: Mapping[str, Any] | None, profile: str) -> dict[str, Any]:
    """The overlay for ``profile``: top-level ``fusion``/``weights`` (all profiles), then
    ``profiles.<profile>`` on top. Only threshold, review_band and per-check weights are taken."""
    data = data or {}
    out: dict[str, Any] = {"fusion": {}, "weights": {}}
    for block in (data, (data.get("profiles") or {}).get(profile) or {}):
        out["fusion"].update({k: v for k, v in (block.get("fusion") or {}).items() if k in TUNING_FUSION_KEYS})
        out["weights"].update(block.get("weights") or {})
    return out


def apply_tuning(raw: dict, values: Mapping[str, Any]) -> tuple[dict, dict[str, Any]]:
    """Copy of ``raw`` with the overlay applied; returns (raw, what was actually changed)."""
    raw = copy.deepcopy(raw)
    applied: dict[str, Any] = {}
    fusion = values.get("fusion") or {}
    if fusion:
        raw["fusion"] = {**(raw.get("fusion") or {}), **fusion}
        applied.update({f"fusion.{k}": v for k, v in fusion.items()})
    for spec in raw.get("checks") or []:
        name = spec.get("name") or spec.get("type")
        if name in (values.get("weights") or {}):
            spec["weight"] = float(values["weights"][name])
            applied[f"weight.{name}"] = spec["weight"]
    return raw, applied


def _tuning_path(raw: dict) -> Path | None:
    value = (raw.get("paths") or {}).get("tuning", Paths().tuning)
    if not value:
        return None
    p = Path(value)
    return p if p.is_absolute() else ROOT / p


def load_config(path: str | Path, overrides: list[str] | None = None) -> AppConfig:
    p = resolve_config_path(path)
    base = expand_env(_load_raw(p), source=p.name)
    # --set comes last and literally: the shell has already expanded its values
    raw = apply_overrides(base, overrides)
    raw.setdefault("name", p.stem)
    raw.pop("tuning", None)
    tp = _tuning_path(raw)
    if tp is not None and tp.is_file():  # profile, then the officer's overlay, then --set
        text = tp.read_text()
        tuned, applied = apply_tuning(base, tuning_values(yaml.safe_load(text) or {}, raw["name"]))
        if applied:
            raw = apply_overrides(tuned, overrides)
            raw.setdefault("name", p.stem)
            raw["tuning"] = {"path": str(tp), "hash": hashlib.sha256(text.encode()).hexdigest()[:16],
                             "applied": applied}
    cfg = AppConfig(**raw)
    cfg.source_path = str(p)
    return cfg
