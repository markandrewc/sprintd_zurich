"""Everything the UI does besides drawing: read results, re-decide them live, edit the keyword list and
criteria, re-run cheap checks, process a call stage by stage, play passages.

No Streamlit import here on purpose: the logic is unit-tested directly and the pages stay thin.
Results are treated as read-only shared objects (one parse per file version for all sessions).
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import re
import shlex
import shutil
import sys
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from callguard import audio, registry
from callguard.cache import stable_hash
from callguard.config import AppConfig
from callguard.context import Context
from callguard.data import Call, load_calls
from callguard.families import load_families, save_keywords
from callguard.types import (LABELS, CallResult, CheckResult, Decision, Family, FusedFamily, Keyword, Passage,
                             Transcript)

if TYPE_CHECKING:
    from callguard.pipeline import Pipeline
    from callguard.plugins import Check

log = logging.getLogger("callguard.ui")

ENV_ARGS = "CALLGUARD_ARGS"
LABEL_TEXT = {"alarm": "Alarm", "review": "Review", "no_alert": "No alert"}
LABEL_RANK = {lbl: i for i, lbl in enumerate(LABELS)}
FUSION_DEFAULTS = {"threshold": 0.55, "review_band": 0.15, "max_uncertainty": 0.35, "min_score_for_review": 0.25}
CHEAP_CHECK_TYPES = frozenset({"keywords", "patterns"})
CRITERIA_LIST_FIELDS = ("alarm_when", "not_alarm_when", "review_when")
AUDIO_SUFFIXES = (".wav", ".flac", ".mp3", ".m4a", ".ogg")
# fusion's own label sentences; the first reason that is none of these says *why* in domain terms
_LABEL_REASON_PREFIXES = ("Alarm:", "Prüfen", "Kein Alarm:", "Hinweis:", "Deaktivierte Prüfungen")


# --------------------------------------------------------------------------------------------
# Launch arguments
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class UIArgs:
    config: str = "local"
    sets: tuple[str, ...] = ()
    no_cache: bool = False


def parse_args(argv: list[str] | None = None, environ: Mapping[str, str] | None = None) -> UIArgs:
    """``streamlit run app.py -- --config local --set a.b=c``.

    ``CALLGUARD_ARGS`` (same syntax) wins when set: under pytest/AppTest ``sys.argv`` belongs to pytest,
    whose own ``-c`` would otherwise be read as our profile.
    """
    env = os.environ if environ is None else environ
    raw = env.get(ENV_ARGS, "").strip()
    tokens = shlex.split(raw) if raw else list(sys.argv[1:] if argv is None else argv)
    p = argparse.ArgumentParser(prog="callguard-ui", add_help=False, exit_on_error=False)
    p.add_argument("--config", "-c", default=env.get("CALLGUARD_CONFIG") or "local")
    p.add_argument("--set", dest="sets", action="append", default=[])
    p.add_argument("--no-cache", action="store_true")
    try:
        ns, unknown = p.parse_known_args(tokens)
    except (argparse.ArgumentError, SystemExit) as e:
        log.warning("ignoring UI arguments %r (%s)", tokens, e)
        return UIArgs(config=env.get("CALLGUARD_CONFIG") or "local")
    if unknown:
        log.warning("ignoring unknown UI arguments %s", unknown)
    return UIArgs(config=ns.config, sets=tuple(ns.sets), no_cache=bool(ns.no_cache))


def parse_seconds(value: Any) -> float | None:
    """Deep-link ``t``: ``83``, ``83.5`` or ``01:23``. Garbage -> None (never an exception)."""
    if value is None:
        return None
    if isinstance(value, list):
        value = value[-1] if value else None
        if value is None:
            return None
    s = str(value).strip()
    try:
        if ":" in s:
            parts = [float(x) for x in s.split(":")]
            secs = 0.0
            for x in parts:
                secs = secs * 60 + x
        else:
            secs = float(s)
    except ValueError:
        return None
    return max(0.0, secs) if math.isfinite(secs) else None


# --------------------------------------------------------------------------------------------
# Config views
# --------------------------------------------------------------------------------------------


def fusion_defaults(cfg: AppConfig) -> dict[str, float]:
    out = dict(FUSION_DEFAULTS)
    for k in out:
        try:
            if cfg.fusion.get(k) is not None:
                out[k] = float(cfg.fusion[k])
        except (TypeError, ValueError):
            log.warning("fusion.%s=%r is not a number; using %s", k, cfg.fusion.get(k), out[k])
    return out


def check_weights(cfg: AppConfig) -> dict[str, float]:
    """Configured weight per enabled check instance (the sidebar sliders start here)."""
    out: dict[str, float] = {}
    for spec in cfg.checks:
        if spec.get("enabled", True) is False:
            continue
        name = str(spec.get("name") or spec.get("type"))
        try:
            out[name] = float(spec.get("weight", 1.0))
        except (TypeError, ValueError):
            out[name] = 1.0
    return out


def short_label(label: str) -> str:
    """'Insiderhandel (Information und Kaufwunsch)' -> 'Insiderhandel' for tables and badges."""
    return label.split(" (")[0].strip() or label


# --------------------------------------------------------------------------------------------
# Engine: the pipeline, or as much of it as can be built
# --------------------------------------------------------------------------------------------


class Engine:
    """The full pipeline when it can be built, else only the fusion plugin (enough to re-decide stored
    results), else nothing (stored decisions are shown as they are).

    Plugins are written in parallel during the event; one broken check module must not take the
    officer's inbox down with it.
    """

    def __init__(self, cfg: AppConfig, *, use_cache: bool = True):
        self.cfg = cfg
        self.pipeline: Pipeline | None = None
        self.fusion: Any = None
        self.error: str | None = None
        try:
            from callguard.pipeline import Pipeline  # deferred: building it imports every configured plugin

            self.pipeline = Pipeline(cfg, use_cache=use_cache)
            self.ctx = self.pipeline.ctx
            self.fusion = self.pipeline.fusion
        except Exception as e:
            self.error = f"Pipeline could not be built ({type(e).__name__}: {e})"
            log.warning("UI: %s; falling back to fusion only", self.error)
            self.ctx = Context(cfg, use_cache=use_cache)
            try:
                self.fusion = registry.create("fusion", cfg.fusion, ctx=self.ctx)
            except Exception as e2:
                self.error += f"; fusion unavailable too ({type(e2).__name__}: {e2})"
                log.warning("UI: fusion unavailable: %s", e2)
        # memo key for derived data; id() would be reused once an old engine is garbage-collected
        self.key = stable_hash({"cfg": cfg.model_dump(mode="json"), "pipeline": self.pipeline is not None,
                                "fusion": self.fusion is not None})

    @property
    def can_decide(self) -> bool:
        return self.fusion is not None

    def families(self) -> list[Family]:
        try:
            return self.ctx.families()
        except Exception as e:
            log.warning("UI: families could not be loaded: %s", e)
            return []

    def decide(self, result: CallResult, overrides: dict[str, Any] | None = None,
               families: list[Family] | None = None) -> Decision:
        views = result.views or None  # multi-view results: fusion places other views' findings
        if self.pipeline is not None:
            return self.pipeline.decide(result.transcript, result.checks, overrides, families, views=views)
        if self.fusion is None:
            raise RuntimeError(self.error or "no fusion plugin")
        fams = families if families is not None else self.families()
        o = dict(overrides or {})
        o.setdefault("weights", check_weights(self.cfg))
        if views:
            return self.fusion.decide(result.transcript, result.checks, fams, o, views=views)
        return self.fusion.decide(result.transcript, result.checks, fams, o)


# --------------------------------------------------------------------------------------------
# Results on disk
# --------------------------------------------------------------------------------------------


@dataclass
class Loaded:
    results: dict[str, CallResult] = field(default_factory=dict)
    paths: dict[str, Path] = field(default_factory=dict)  # call_id -> result.json it came from
    errors: list[str] = field(default_factory=list)
    signature: str = ""  # changes whenever any result file changes: key for everything derived


_PARSED: dict[str, tuple[tuple[int, int], CallResult]] = {}
_PARSED_LOCK = threading.Lock()


def load_results(runs_dir: str | Path) -> Loaded:
    """Every ``<runs_dir>/<call_id>/result.json``. A file is parsed once per version (mtime + size), so
    scanning on every rerun stays cheap; unreadable files are reported, not raised."""
    out = Loaded()
    sig: list[tuple[str, int, int]] = []
    root = Path(runs_dir)
    for f in sorted(root.glob("*/result.json")) if root.is_dir() else []:
        try:
            st = f.stat()
            version = (st.st_mtime_ns, st.st_size)
            key = str(f.resolve())
            with _PARSED_LOCK:
                hit = _PARSED.get(key)
            if hit is not None and hit[0] == version:
                r = hit[1]
            else:
                r = CallResult.model_validate_json(f.read_text())
                with _PARSED_LOCK:
                    _PARSED[key] = (version, r)
        except Exception as e:
            out.errors.append(f"{f.parent.name}: {type(e).__name__}: {str(e)[:200]}")
            continue
        if r.call_id in out.results:
            out.errors.append(f"{f.parent.name}: duplicate call id {r.call_id!r} (also in "
                              f"{out.paths[r.call_id].parent.name}); ignored")
            continue
        out.results[r.call_id] = r
        out.paths[r.call_id] = f
        sig.append((key, *version))
    out.signature = stable_hash(sig)
    return out


def write_result(path: str | Path, result: CallResult) -> Path:
    """Write-then-rename, like the json_dir sink: the UI may be reading the folder concurrently."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text(result.model_dump_json(indent=1))
    tmp.replace(out)
    return out


# --------------------------------------------------------------------------------------------
# Live re-decision
# --------------------------------------------------------------------------------------------


@dataclass
class Decided:
    decision: Decision  # what the UI shows: the live re-decision, or the stored one if that failed
    stored: Decision  # as written by the pipeline when the call was processed
    live: bool = True
    error: str | None = None


class _LRU:
    def __init__(self, size: int):
        self.size = size
        self.data: OrderedDict[str, Any] = OrderedDict()
        self.lock = threading.Lock()

    def get_or(self, key: str, fn: Callable[[], Any]) -> Any:
        with self.lock:
            if key in self.data:
                self.data.move_to_end(key)
                return self.data[key]
        value = fn()
        with self.lock:
            self.data[key] = value
            while len(self.data) > self.size:
                self.data.popitem(last=False)
        return value

    def clear(self) -> None:
        with self.lock:
            self.data.clear()


_DECIDE_MEMO = _LRU(64)
_SWEEP_MEMO = _LRU(16)


def _families_key(families: list[Family] | None) -> Any:
    return None if families is None else [f.model_dump(mode="json") for f in families]


def carry_snippets(new: Decision, old: Decision) -> Decision:
    """Re-decided passages lose ``snippet_path`` (it is set after fusion); reuse the stored cut when the
    passage is the same stretch of audio."""
    for p in new.passages:
        if p.snippet_path:
            continue
        for q in old.passages:
            if q.snippet_path and q.family == p.family and abs(q.start - p.start) < 0.5 and abs(q.end - p.end) < 0.5:
                p.snippet_path = q.snippet_path
                break
    return new


def redecide(engine: Engine | None, result: CallResult, overrides: dict[str, Any] | None,
             families: list[Family] | None) -> Decided:
    """Fusion only (cheap, pure). Any failure falls back to the stored decision with the error attached."""
    if engine is None or not engine.can_decide:
        why = engine.error if engine is not None else "no pipeline"
        return Decided(result.decision, result.decision, live=False, error=why)
    try:
        d = engine.decide(result, overrides, families)
    except Exception as e:
        log.warning("UI: re-deciding %s failed: %s", result.call_id, e)
        return Decided(result.decision, result.decision, live=False, error=f"{type(e).__name__}: {e}")
    return Decided(carry_snippets(d, result.decision), result.decision, live=True)


def decide_all(engine: Engine | None, loaded: Loaded, overrides: dict[str, Any] | None,
               families: list[Family] | None) -> dict[str, Decided]:
    key = stable_hash({"engine": getattr(engine, "key", None), "sig": loaded.signature, "overrides": overrides,
                       "families": _families_key(families)})
    return _DECIDE_MEMO.get_or(key, lambda: {cid: redecide(engine, r, overrides, families)
                                             for cid, r in loaded.results.items()})


def default_thresholds(step: float = 0.05) -> list[float]:
    n = int(round(1 / step))
    return [round(i * step, 4) for i in range(1, n)]


def sweep_labels(engine: Engine | None, loaded: Loaded, overrides: dict[str, Any] | None,
                 families: list[Family] | None, thresholds: Iterable[float],
                 call_ids: Iterable[str] | None = None) -> dict[float, dict[str, str]]:
    """Labels of every call at each threshold, all other knobs as given. Calls that cannot be re-decided
    keep their stored label (they then don't move with the threshold)."""
    ths = [float(t) for t in thresholds]
    ids = sorted(call_ids) if call_ids is not None else sorted(loaded.results)
    base = {k: v for k, v in (overrides or {}).items() if k != "threshold"}  # moving the slider keeps the memo
    key = stable_hash({"engine": getattr(engine, "key", None), "sig": loaded.signature, "overrides": base,
                       "families": _families_key(families), "t": ths, "ids": ids})

    def compute() -> dict[float, dict[str, str]]:
        out: dict[float, dict[str, str]] = {}
        for t in ths:
            o = {**base, "threshold": t}
            out[t] = {cid: redecide(engine, loaded.results[cid], o, families).decision.label
                      for cid in ids if cid in loaded.results}
        return out

    return _SWEEP_MEMO.get_or(key, compute)


def label_counts(decided: Mapping[str, Decided] | Iterable[Decision]) -> dict[str, int]:
    decisions = [d.decision for d in decided.values()] if isinstance(decided, Mapping) else list(decided)
    counts = {lbl: 0 for lbl in LABELS}
    for d in decisions:
        counts[d.label] = counts.get(d.label, 0) + 1
    return counts


# --------------------------------------------------------------------------------------------
# Explaining a decision
# --------------------------------------------------------------------------------------------


def top_family(decision: Decision, can_alarm: set[str] | None = None) -> FusedFamily | None:
    fams = [f for f in decision.families.values() if can_alarm is None or f.family in can_alarm]
    best = max(fams, key=lambda f: (f.score, -f.uncertainty), default=None)
    return best if best is not None and best.score > 0 else None


def headline_reason(decision: Decision, result: CallResult | None = None,
                    weights: Mapping[str, float] | None = None, can_alarm: set[str] | None = None) -> str:
    """One sentence that explains the call in domain terms: the most trusted check's own reason for the
    top family (weight x confidence; terse ones like 'G-Eval 1.5/5' skipped), else the fusion's family
    reason, else its label sentence."""
    top = top_family(decision, can_alarm)
    if result is not None and top is not None:
        best: tuple[float, str] | None = None
        for name in top.per_check:
            cr = result.checks.get(name)
            fs = cr.family_scores.get(top.family) if cr else None
            if fs is None or len(fs.reason.split()) < 4:
                continue
            trust = float((weights or {}).get(name, 1.0)) * float(fs.confidence)
            if best is None or trust > best[0]:
                best = (trust, fs.reason.strip())
        if best is not None:
            return f"{short_label(top.label)}: {best[1]}"
    for r in decision.reasons:
        if not r.startswith(_LABEL_REASON_PREFIXES):
            return r
    if decision.passages and decision.passages[0].reasons:
        return decision.passages[0].reasons[0]
    return decision.reasons[0] if decision.reasons else ""


def label_change(current: str, baseline: str | None) -> str:
    if baseline is None or baseline == current:
        return ""
    return f"{LABEL_TEXT.get(baseline, baseline)} → {LABEL_TEXT.get(current, current)}"


def inbox_rows(loaded: Loaded, decided: Mapping[str, Decided], families: list[Family],
               baseline: Mapping[str, Decided] | None = None,
               weights: Mapping[str, float] | None = None) -> list[dict[str, Any]]:
    """One row per call, riskiest first."""
    can_alarm = {f.id for f in families if f.can_alarm} or None
    rows = []
    for cid in loaded.results:
        dd = decided.get(cid)
        if dd is None:
            continue
        d = dd.decision
        top = top_family(d, can_alarm)
        base = baseline.get(cid) if baseline else None
        # a check that failed at processing time (e.g. LLM server down) is missing from the label: say so
        # in the list, not only on the detail page, so a "No alert" is not mistaken for a full assessment
        failed = sorted(check_problems(loaded.results[cid]))
        reason = headline_reason(d, loaded.results[cid], weights, can_alarm)
        rows.append({
            "call_id": cid, "label": d.label, "score": round(d.score, 3), "uncertainty": round(d.uncertainty, 3),
            "family": short_label(top.label) if top else "", "passages": len(d.passages),
            "reason": f"Checks failed: {', '.join(failed)} · {reason}" if failed else reason,
            "changed": label_change(d.label, base.decision.label if base else None),
            "live": dd.live, "failed_checks": failed,
        })
    rows.sort(key=lambda r: (-r["score"], LABEL_RANK.get(r["label"], 9), r["call_id"]))
    return rows


def checks_said(result: CallResult, decision: Decision, weights: Mapping[str, float] | None = None,
                families: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Per family and check: score, confidence, verdict and reason. The 'which check said what' table."""
    fam_order = list(families) if families is not None else [
        f.family for f in sorted(decision.families.values(), key=lambda f: -f.score)]
    rows = []
    for fid in fam_order:
        ff = decision.families.get(fid)
        for name, cr in result.checks.items():
            fs = cr.family_scores.get(fid)
            if fs is None:
                continue
            rows.append({
                "family": short_label(ff.label) if ff else fid, "check": name,
                "weight": (weights or {}).get(name), "score": round(float(fs.score), 3),
                "confidence": round(float(fs.confidence), 3), "verdict": fs.verdict or "",
                "reason": fs.reason, "used": bool(ff and name in ff.per_check),
            })
    return rows


def check_problems(result: CallResult) -> dict[str, str]:
    return {name: str(cr.meta.get("error")) for name, cr in result.checks.items() if cr.meta.get("error")}


def linked_passage(passages: list[Passage], t: float | None, link_pad: float = 10.0) -> int | None:
    """Index of the passage a deep link ``t`` points at (links start ``link_pad`` s before the passage)."""
    if t is None or not passages:
        return None
    best, best_d = None, None
    for i, p in enumerate(passages):
        if p.start - link_pad - 2 <= t <= p.end:
            d = abs(p.start - link_pad - t)
            if best_d is None or d < best_d:
                best, best_d = i, d
    return best


# --------------------------------------------------------------------------------------------
# Audio
# --------------------------------------------------------------------------------------------


@dataclass
class Clip:
    path: str
    start: float = 0.0
    end: float | None = None
    note: str = ""


def passage_clip(result: CallResult, passage: Passage, result_dir: Path, pad: float = 2.0) -> Clip | None:
    """Audio for a passage: the pipeline's snippet, else a freshly cut one in the call's run folder, else
    the full recording with a time window. None when the recording is not on this machine."""
    if passage.snippet_path and Path(passage.snippet_path).is_file():
        return Clip(passage.snippet_path)
    src = result.audio_path
    if not src or not Path(src).is_file():
        return None
    out = result_dir / "snippets" / f"ui_{passage.family}_{passage.start:.1f}-{passage.end:.1f}.wav"
    try:
        if not out.is_file():
            audio.cut(src, passage.start, passage.end, out, pad=pad)
        return Clip(str(out))
    except Exception as e:
        log.warning("UI: cutting snippet for %s failed: %s", result.call_id, e)
        return Clip(src, max(0.0, passage.start - pad), passage.end + pad,
                    note=f"snippet could not be cut ({type(e).__name__}); playing the window of the full call")


# --------------------------------------------------------------------------------------------
# Keyword list and criteria editing
# --------------------------------------------------------------------------------------------

KEYWORD_COLUMNS = ("enabled", "id", "label", "de", "gsw", "en", "harmless", "case_sensitive")


def join_phrases(phrases: Iterable[str]) -> str:
    return ", ".join(phrases)


def split_phrases(text: Any) -> list[str]:
    if text is None or (isinstance(text, float) and math.isnan(text)):
        return []
    parts = re.split(r"[,;\n]", str(text))
    return list(dict.fromkeys(p.strip() for p in parts if p.strip()))


def keyword_rows(family: Family) -> list[dict[str, Any]]:
    return [{"enabled": k.enabled, "id": k.id, "label": k.label, "de": join_phrases(k.de),
             "gsw": join_phrases(k.gsw), "en": join_phrases(k.en), "harmless": k.harmless or "",
             "case_sensitive": k.case_sensitive}
            for k in family.keywords]


def all_keyword_ids(keywords_path: Path) -> set[str]:
    import json

    try:
        raw = json.loads(Path(keywords_path).read_text())
    except Exception:
        return set()
    return {str(k.get("id")) for k in raw.get("keywords", []) if k.get("id")}


def next_keyword_id(taken: set[str]) -> str:
    nums = [int(m.group(1)) for t in taken if (m := re.fullmatch(r"K(\d+)", t))]
    n = max(nums, default=0) + 1
    while f"K{n:02d}" in taken:
        n += 1
    return f"K{n:02d}"


def _blank(v: Any) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or str(v).strip() == ""


def rows_to_keywords(rows: Iterable[Mapping[str, Any]], taken_ids: set[str]) -> tuple[list[Keyword], list[str]]:
    """Editor rows -> Keywords. New rows get the next free ``Kxx`` id; rows without any phrase are
    dropped with a warning (an empty keyword would match nothing and only confuse)."""
    taken = set(taken_ids)
    out: list[Keyword] = []
    warnings: list[str] = []
    seen: set[str] = set()
    for i, row in enumerate(rows, 1):
        de, gsw = split_phrases(row.get("de")), split_phrases(row.get("gsw"))
        en = split_phrases(row.get("en"))  # English forms: only matched on English transcript views
        kid = "" if _blank(row.get("id")) else str(row.get("id")).strip()
        if not de and not gsw:
            if kid or not all(_blank(row.get(c)) for c in ("label", "harmless")):
                warnings.append(f"Row {i} ({kid or 'new'}) has no phrases and was not saved.")
            continue
        if not kid:
            kid = next_keyword_id(taken | seen)
        if kid in seen:
            warnings.append(f"Keyword id {kid} appears twice; only the first row was saved.")
            continue
        seen.add(kid)
        label = "" if _blank(row.get("label")) else str(row.get("label")).strip()
        harmless = None if _blank(row.get("harmless")) else str(row.get("harmless")).strip()
        enabled, case = row.get("enabled"), row.get("case_sensitive")
        out.append(Keyword(id=kid, label=label or (de + gsw)[0], de=de, gsw=gsw, en=en, harmless=harmless,
                           enabled=True if _blank(enabled) else bool(enabled),
                           case_sensitive=False if _blank(case) else bool(case)))
    return out, warnings


def backup_file(path: Path, backup_dir: Path) -> Path | None:
    """Copy before every officer edit, so a bad save is one file copy away from undone."""
    if not path.is_file():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    out = backup_dir / f"{path.stem}.{time.strftime('%Y%m%d-%H%M%S')}{path.suffix}"
    shutil.copy2(path, out)
    return out


def save_family_keywords(keywords_path: Path, criteria_path: Path | None, family_id: str,
                         keywords: list[Keyword]) -> None:
    """Replace one family's keywords; every other family (also disabled ones) is written back unchanged."""
    fams = load_families(keywords_path, criteria_path)
    target = next((f for f in fams if f.id == family_id), None)
    if target is None:
        target = Family(id=family_id, label=family_id)
        fams.append(target)
    target.keywords = list(keywords)
    save_keywords(fams, keywords_path)


def _criteria_header(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("#") or (not line.strip() and lines):
            lines.append(line)
        else:
            break
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines) + "\n\n" if lines else ""


def criteria_entry(criteria_path: Path, family_id: str) -> dict[str, Any]:
    if not Path(criteria_path).is_file():
        return {}
    raw = yaml.safe_load(Path(criteria_path).read_text()) or {}
    return dict((raw.get("families") or {}).get(family_id) or {})


def save_criteria(criteria_path: Path, family_id: str, fields: Mapping[str, Any]) -> None:
    """Update one family in ``criteria.yaml``; the file's header comment survives, inline comments don't
    (PyYAML drops them), every other key and family is kept."""
    path = Path(criteria_path)
    text = path.read_text() if path.is_file() else ""
    raw = yaml.safe_load(text) or {}
    fams = raw.setdefault("families", {}) or {}
    raw["families"] = fams
    entry = dict(fams.get(family_id) or {})
    for k, v in fields.items():
        if k in CRITERIA_LIST_FIELDS:
            v = [s.strip() for s in (v.splitlines() if isinstance(v, str) else v or []) if str(s).strip()]
        elif isinstance(v, str):
            v = " ".join(v.split()) if k == "label" else v.strip()
        entry[k] = v
    fams[family_id] = entry
    body = yaml.safe_dump(raw, allow_unicode=True, sort_keys=False, width=110)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(_criteria_header(text) + body)
    tmp.replace(path)


# --------------------------------------------------------------------------------------------
# Re-running checks after an edit
# --------------------------------------------------------------------------------------------


def is_cheap(check: Check) -> bool:
    """Keyword/pattern checks rerun in milliseconds; anything talking to an LLM does not."""
    return check.plugin_type in CHEAP_CHECK_TYPES or "llm" not in check.params


def cached_check(pipeline: Pipeline, check: Check, result: CallResult, families: list[Family]) -> CheckResult | None:
    """The check's result from the pipeline cache, if its inputs are unchanged (never runs the check)."""
    try:
        return pipeline.cached_check(check, check_view_transcript(pipeline, check, result), families)
    except Exception:
        return None


def check_view_transcript(pipeline: Pipeline, check: Check, result: CallResult) -> Transcript:
    """The transcript view ``check`` reads in ``result`` (the primary one for single-view results)."""
    return result.view(pipeline.view_of(check)) if result.views else result.transcript


@dataclass
class RerunReport:
    calls: int = 0
    rerun: int = 0  # check runs actually executed
    reused: int = 0  # taken from the pipeline cache
    kept: int = 0  # expensive checks whose inputs changed: previous result kept, marked stale
    failed: list[str] = field(default_factory=list)


def rerun_checks(pipeline: Pipeline, loaded: Loaded, *, include_llm: bool = False,
                 progress: Callable[[int, int, str], None] | None = None) -> RerunReport:
    """After a keyword/criteria edit: recompute each processed call's checks and write result.json.

    Cheap checks always rerun (or come from the cache); LLM checks are taken from the cache when their
    inputs (criteria, model) are unchanged, else rerun only with ``include_llm`` and otherwise kept with
    ``meta.stale`` so the officer sees the result predates the edit.
    """
    report = RerunReport()
    families = pipeline.ctx.families()
    items = list(loaded.results.items())
    for i, (cid, r) in enumerate(items):
        if progress:
            progress(i, len(items), cid)
        try:
            checks: dict[str, CheckResult] = {}
            for check in pipeline.checks:
                if not check.enabled:
                    continue
                hit = cached_check(pipeline, check, r, families)
                if hit is not None:
                    checks[check.name] = hit
                    report.reused += 1
                elif include_llm or is_cheap(check):
                    checks[check.name] = pipeline.run_check(check, check_view_transcript(pipeline, check, r),
                                                            families)
                    report.rerun += 1
                elif check.name in r.checks:
                    old = r.checks[check.name].model_copy(deep=True)
                    old.meta["stale"] = "Kriterien seit dieser Bewertung geändert; Prüfung nicht neu gelaufen."
                    checks[check.name] = old
                    report.kept += 1
            decision = pipeline.decide(r.transcript, checks, None, families, views=r.views or None)
            new = r.model_copy(update={"checks": checks, "decision": carry_snippets(decision, r.decision)})
            try:
                pipeline.make_snippets(new)
            except Exception as e:  # missing recording: the UI cuts or windows on demand instead
                log.warning("UI: snippets for %s not cut: %s", cid, e)
            write_result(loaded.paths[cid], new)
            report.calls += 1
        except Exception as e:
            log.warning("UI: re-running checks for %s failed: %s", cid, e)
            report.failed.append(f"{cid}: {type(e).__name__}: {e}")
    if progress:
        progress(len(items), len(items), "")
    return report


# --------------------------------------------------------------------------------------------
# Processing a call
# --------------------------------------------------------------------------------------------


def process_call(pipeline: Pipeline, audio_path: str | Path, call_id: str,
                 notify: Callable[[str], None] | None = None) -> CallResult:
    """``Pipeline.process`` stage by stage, so the UI can say which stage is running (on CPU the ASR
    alone takes about as long as the call). Same stage methods and result as ``Pipeline.process``."""
    say = notify or (lambda msg: None)
    audio_path = Path(audio_path)
    if pipeline.multi_view:  # several transcript views: the pipeline builds them (stage-level progress)
        stages = {"asr": "Transcribing (speech recognition, every ASR view)",
                  "diarize": "Separating speakers (advisor / customer)", "translate": "Translating views",
                  "checks": "Running the checks", "decide": "Deciding", "snippets": "Cutting audio snippets",
                  "emit": "Saving the result"}
        return pipeline.process(audio_path, call_id, on_stage=lambda name: say(stages.get(name, name)))
    timings: dict[str, float] = {}

    say("Transcribing (speech recognition)")
    t = time.time()
    transcript = pipeline.transcribe(audio_path, call_id)
    timings["asr"] = time.time() - t
    say(f"Transcript ready: {len(transcript.segments)} segments ({timings['asr']:.0f} s)")

    say("Separating speakers (advisor / customer)")
    t = time.time()
    try:
        transcript = pipeline.diarize(audio_path, transcript)
    except Exception as e:  # roles are a refinement: the checks still run without them
        log.warning("UI: diarization of %s failed: %s", call_id, e)
        say(f"Speaker separation failed ({type(e).__name__}); continuing without roles")
    timings["diarize"] = time.time() - t

    families = pipeline.ctx.families()
    results: dict[str, CheckResult] = {}
    t = time.time()
    for check in pipeline.checks:
        if not check.enabled:
            continue
        say(f"Check '{check.name}' running")
        t1 = time.time()
        results[check.name] = pipeline.run_check(check, transcript, families)
        err = results[check.name].meta.get("error")
        say(f"Check '{check.name}' {'FAILED: ' + str(err)[:120] if err else 'done'} ({time.time() - t1:.0f} s)")
    timings["checks"] = time.time() - t

    say("Deciding")
    decision = pipeline.decide(transcript, results, None, families)
    result = CallResult(call_id=call_id, audio_path=str(audio_path), transcript=transcript, checks=results,
                        decision=decision, config_name=pipeline.cfg.name,
                        timings={k: round(v, 2) for k, v in timings.items()},
                        meta={"provenance": pipeline.provenance({transcript.view: transcript})})
    say("Cutting audio snippets")
    try:
        pipeline.make_snippets(result)
    except Exception as e:
        log.warning("UI: snippets for %s failed: %s", call_id, e)
        say(f"Snippets could not be cut ({type(e).__name__}); passages play from the full call")
    say("Saving the result")
    pipeline.emit(result)
    return result


def safe_call_id(filename: str) -> str:
    stem = Path(filename).stem
    cid = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-")
    return cid or "upload"


def save_upload(runs_dir: Path, filename: str, data: bytes) -> Path:
    suffix = Path(filename).suffix.lower()
    if suffix not in AUDIO_SUFFIXES:
        raise ValueError(f"unsupported audio type {suffix or '(none)'}; use one of {', '.join(AUDIO_SUFFIXES)}")
    out = runs_dir / "uploads" / f"{safe_call_id(filename)}{suffix}"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def audio_seconds(path: str | Path) -> float | None:
    try:
        return float(audio.duration(path))
    except Exception:
        return None


def estimate_seconds(cfg: AppConfig, audio_s: float) -> float:
    """Rough wall time for the progress hint: CPU Whisper runs about realtime, a GPU ~20x faster."""
    device = str(cfg.asr.get("device", "cpu")).lower()
    asr = audio_s * (1.0 if device == "cpu" else 0.05)
    llm_checks = sum(1 for c in cfg.checks if "llm" in c and c.get("enabled", True))
    return asr + llm_checks * (60.0 if device == "cpu" else 5.0)


# --------------------------------------------------------------------------------------------
# Ground truth (evaluation display only, never pipeline input)
# --------------------------------------------------------------------------------------------


def ground_truth(data_dir: str | Path) -> dict[str, Call]:
    try:
        return {c.call_id: c for c in load_calls(data_dir)}
    except Exception as e:
        log.warning("UI: ground truth not loaded from %s: %s", data_dir, e)
        return {}
