"""Experiment runner: a matrix of config variants on the same calls, with honest statistics.

Spec (``experiments/<name>.yaml``)::

    name: checks_ablation                # default: file stem; output dir runs/experiments/<name>/
    description: which checks carry the decision
    rq: [RQ4]
    base: gpu-12gb                       # profile every variant starts from
    split: dev                           # dev (default) | holdout (logged!) | all
    compare_to: all                      # baseline variant for the paired comparisons (default: first)
    thresholds: [0.3, 0.4, 0.5]          # optional: sweep / CV grid (default eval.DEFAULT_THRESHOLDS)
    variants:
      - name: keywords
        checks: [keywords]               # keep only these checks (by name), in config order
      - name: all_minus_geval
        drop_checks: [geval]             # or remove these
      - name: judge_x1
        set: ["checks.llm_judge.samples=1"]   # --set overrides; list items can be addressed by name
      - name: oracle_ref
        profile: oracle                  # another base profile for this variant
        oracle: true                     # label ORACLE (auto for asr type reference / ref_* views)
      - name: new_check
        add_checks: [{name: kwctx, type: keyword_context, weight: 1.0}]
      - name: t045
        refuse_from: all                 # no check runs: re-fuse the stored results of variant "all"
        set: ["fusion.threshold=0.45"]

Per variant this writes ``runs/experiments/<name>/<variant>/``: ``results.jsonl`` (CallResults without
word timestamps), ``rows.json`` (fixed-threshold rows, out-of-fold CV rows, CV folds, threshold sweep),
``metrics.json`` (eval.metrics of both) and ``meta.json`` (config, provenance, cost). The experiment's
``summary.json`` / ``summary.md`` are always rebuilt from what is on disk, so a rerun of one variant
(``--variants x``) or ``--rescore`` (stats only, nothing recomputed) keeps the other variants.

Caches are shared with every other command (ASR, checks), so a variant only computes what it changes.
Calls run in a thread pool (LLM checks are I/O bound); ASR + diarization are serialized by a lock so one
GPU model is never loaded or driven twice at once. Snippets are never cut in experiments.
"""

from __future__ import annotations

import json
import logging
import statistics
import threading
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from callguard import eval as ev
from callguard import splits as sp
from callguard import stats
from callguard.config import ROOT, AppConfig, _load_raw, apply_overrides, expand_env, resolve_config_path
from callguard.data import Call, dialogue_of
from callguard.types import CallResult, fmt_ts

log = logging.getLogger("callguard")

Row = dict[str, Any]
EXPERIMENTS_DIR = ROOT / "experiments"


class SpecError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------------------------


@dataclass
class Variant:
    name: str
    set: list[str] = field(default_factory=list)
    profile: str | None = None
    oracle: bool | None = None
    checks: list[str] | None = None
    drop_checks: list[str] = field(default_factory=list)
    add_checks: list[dict[str, Any]] = field(default_factory=list)
    refuse_from: str | None = None
    description: str = ""


@dataclass
class Spec:
    name: str
    base: str
    variants: list[Variant]
    description: str = ""
    rq: list[str] = field(default_factory=list)
    split: str = "dev"
    compare_to: str | None = None
    thresholds: list[float] | None = None
    path: Path | None = None

    def variant(self, name: str) -> Variant:
        for v in self.variants:
            if v.name == name:
                return v
        raise SpecError(f"{self.name}: no variant {name!r} (have {[v.name for v in self.variants]})")

    @property
    def baseline(self) -> str:
        return self.compare_to or self.variants[0].name


_VARIANT_KEYS = set(Variant.__dataclass_fields__)
_SPEC_KEYS = set(Spec.__dataclass_fields__) - {"path"}


def resolve_spec_path(path: str | Path) -> Path:
    p = Path(path)
    for cand in (p, ROOT / p, EXPERIMENTS_DIR / p, EXPERIMENTS_DIR / f"{p}.yaml"):
        if cand.exists():
            return cand.resolve()
    raise FileNotFoundError(f"experiment spec {path!r} not found (looked in ., {ROOT}, {EXPERIMENTS_DIR})")


def parse_spec(raw: dict[str, Any], *, name: str = "experiment", path: Path | None = None) -> Spec:
    unknown = set(raw) - _SPEC_KEYS
    if unknown:
        raise SpecError(f"{name}: unknown spec keys {sorted(unknown)} (allowed: {sorted(_SPEC_KEYS)})")
    if not raw.get("base"):
        raise SpecError(f"{name}: 'base' (profile) is required")
    variants = []
    for i, v in enumerate(raw.get("variants") or []):
        if not isinstance(v, dict) or not v.get("name"):
            raise SpecError(f"{name}: variant #{i} needs a name")
        bad = set(v) - _VARIANT_KEYS
        if bad:
            raise SpecError(f"{name}: variant {v['name']!r}: unknown keys {sorted(bad)} (allowed: {sorted(_VARIANT_KEYS)})")
        v = dict(v)
        v["name"] = str(v["name"])
        v["set"] = [str(s) for s in v.get("set") or []]
        v["drop_checks"] = list(v.get("drop_checks") or [])
        v["add_checks"] = list(v.get("add_checks") or [])
        variants.append(Variant(**v))
    if not variants:
        raise SpecError(f"{name}: no variants")
    names = [v.name for v in variants]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise SpecError(f"{name}: duplicate variant names {dup}")
    spec = Spec(name=str(raw.get("name") or name), base=str(raw["base"]), variants=variants,
                description=str(raw.get("description") or ""), rq=[str(x) for x in raw.get("rq") or []],
                split=str(raw.get("split") or "dev"), compare_to=raw.get("compare_to"),
                thresholds=[float(t) for t in raw["thresholds"]] if raw.get("thresholds") else None, path=path)
    if spec.split not in sp.SPLIT_CHOICES:
        raise SpecError(f"{name}: split must be one of {sp.SPLIT_CHOICES}")
    if spec.compare_to is not None:
        spec.variant(spec.compare_to)
    for v in variants:
        if v.refuse_from is not None:
            src = spec.variant(v.refuse_from)
            if src.refuse_from is not None:
                raise SpecError(f"{name}: {v.name} re-fuses {src.name}, which is itself a re-fusion")
            if v.profile or v.add_checks:
                raise SpecError(f"{name}: {v.name}: refuse_from variants take only set/checks/drop_checks")
    return spec


def load_spec(path: str | Path) -> Spec:
    p = resolve_spec_path(path)
    raw = yaml.safe_load(p.read_text()) or {}
    return parse_spec(raw, name=p.stem, path=p)


# --------------------------------------------------------------------------------------------
# variant config
# --------------------------------------------------------------------------------------------


def _named_paths(raw: dict[str, Any], overrides: Sequence[str]) -> list[str]:
    """``checks.llm_judge.samples=1`` -> ``checks.2.samples=1``: list items with a ``name`` can be
    addressed by it (indices shift when variants drop checks; names do not)."""
    out = []
    for item in overrides:
        key, sep, value = item.partition("=")
        parts = key.split(".")
        cur: Any = raw
        for i, part in enumerate(parts):
            if isinstance(cur, list):
                if not part.lstrip("-").isdigit():
                    idx = next((j for j, x in enumerate(cur) if isinstance(x, dict) and x.get("name") == part), None)
                    if idx is None:
                        raise SpecError(f"--set {item}: no list item named {part!r} under {'.'.join(parts[:i])}")
                    parts[i] = part = str(idx)
                cur = cur[int(part)] if -len(cur) <= int(part) < len(cur) else None
            elif isinstance(cur, dict):
                cur = cur.get(part)
            else:
                break
        out.append(".".join(parts) + sep + value)
    return out


def select_checks(checks: list[dict[str, Any]], keep: Sequence[str] | None = None, drop: Sequence[str] = (),
                  add: Sequence[dict[str, Any]] = ()) -> list[dict[str, Any]]:
    """Edit the raw check list by name (no config.py support needed): keep only ``keep`` (config order),
    then remove ``drop``, then append ``add``. Unknown names are an error, not a silent no-op."""
    names = [c.get("name") or c.get("type") for c in checks]
    for n in [*(keep or []), *drop]:
        if n not in names:
            raise SpecError(f"unknown check {n!r} (configured: {names})")
    out = [c for c, n in zip(checks, names) if (keep is None or n in keep) and n not in drop]
    return out + [dict(c) for c in add]


def variant_raw(spec: Spec, v: Variant) -> tuple[dict[str, Any], Path]:
    """The raw (merged, env-expanded, overridden) config dict of a variant, before validation."""
    if v.refuse_from:
        src = spec.variant(v.refuse_from)
        p = resolve_config_path(src.profile or spec.base)
        raw = expand_env(_load_raw(p), source=p.name)
        sets = [*src.set, *v.set]
        raw = apply_overrides(raw, _named_paths(raw, sets))
        raw["checks"] = select_checks(raw.get("checks") or [], src.checks, src.drop_checks, src.add_checks)
        raw["checks"] = select_checks(raw["checks"], v.checks, v.drop_checks)
    else:
        p = resolve_config_path(v.profile or spec.base)
        raw = expand_env(_load_raw(p), source=p.name)
        raw = apply_overrides(raw, _named_paths(raw, v.set))
        raw["checks"] = select_checks(raw.get("checks") or [], v.checks, v.drop_checks, v.add_checks)
    raw.setdefault("name", p.stem)
    return raw, p


def variant_config(spec: Spec, v: Variant) -> AppConfig:
    raw, p = variant_raw(spec, v)
    cfg = AppConfig(**raw)
    cfg.source_path = str(p)
    return cfg


def is_oracle(v: Variant, cfg: AppConfig) -> bool:
    """ORACLE = the variant reads the reference scripts (never a submission candidate): explicit
    ``oracle:`` in the spec wins; otherwise any view the variant uses is ``ref_*`` or has a ``reference``
    ASR (views as in v2_plan §1; without views: the top-level ASR)."""
    if v.oracle is not None:
        return bool(v.oracle)
    raw = cfg.model_dump()
    views = raw.get("views") or {}
    if not views:
        return str(cfg.asr.get("type", "")) == "reference"
    used = {raw.get("primary_view"), raw.get("check_view"), *(raw.get("extra_views") or []),
            *(c.get("view") for c in cfg.checks)} - {None}
    seen: set[str] = set()
    todo = list(used)
    while todo:
        name = str(todo.pop())
        if name in seen:
            continue
        seen.add(name)
        if name.startswith("ref_"):
            return True
        spec = views.get(name) or {}
        if spec.get("from"):
            todo += spec["from"] if isinstance(spec["from"], list) else [spec["from"]]
        elif str((spec.get("asr") or cfg.asr).get("type", "")) == "reference":
            return True
    return False


# --------------------------------------------------------------------------------------------
# calls
# --------------------------------------------------------------------------------------------


def select_calls(calls: Sequence[Call], split: str, splits: sp.Splits | None, call_ids: Sequence[str] | None = None,
                 level: int | None = None, clean_only: bool = False, limit: int | None = None) -> list[Call]:
    if split != "all":
        if splits is None:
            raise sp.SplitsMissing("config/splits.yaml is missing: `callguard splits --make` first")
        calls = splits.select(calls, split)
    else:
        calls = list(calls)
    if call_ids:
        ids = set(call_ids)
        calls = [c for c in calls if c.call_id in ids]
    if level is not None:
        calls = [c for c in calls if c.level == level]
    if clean_only:
        calls = [c for c in calls if not c.noisy]
    return calls[:limit] if limit is not None else calls


def cv_fold_map(split: str, splits: sp.Splits | None, calls: Sequence[Call]) -> dict[str, int]:
    if splits is not None:
        return splits.dev_fold_of() if split == "dev" else splits.all_fold_of()
    from callguard.data import split_dialogues
    return split_dialogues(list(calls))


# --------------------------------------------------------------------------------------------
# rows
# --------------------------------------------------------------------------------------------


def llm_calls(res: CallResult) -> int:
    """LLM requests behind a call (as computed, cached or not). Checks may report ``meta.llm_calls``;
    otherwise every family an LLM check scored counts as one request (self-consistency with n>1 is one
    request on vLLM)."""
    n = 0
    for c in res.checks.values():
        m = c.meta or {}
        if isinstance(m.get("llm_calls"), (int, float)):
            n += int(m["llm_calls"])
        elif "llm" in m or "prompt_version" in m:
            n += len(m.get("family_seconds") or {}) or len(c.family_scores)
    return n


def check_seconds(res: CallResult) -> dict[str, float]:
    """Compute seconds per check as recorded when the result was computed (cache hits keep it)."""
    return {k: float(c.meta.get("seconds") or 0.0) for k, c in res.checks.items()}


def enrich(row: Row, res: CallResult) -> Row:
    """Add the decisive passage + reason (flip tables) and cost fields to an eval row."""
    d = res.decision
    p = max(d.passages, key=lambda x: x.score) if d.passages else None
    if p is not None:
        txt = (p.text or "").replace("\n", " ")
        row["passage"] = f"{fmt_ts(p.start)}-{fmt_ts(p.end)} {p.family}: {txt[:240]}"
        row["reason"] = p.reasons[0] if p.reasons else (d.reasons[0] if d.reasons else None)
    else:
        row["passage"] = None
        row["reason"] = d.reasons[0] if d.reasons else None
    row["llm_calls"] = llm_calls(res)
    row["check_seconds"] = check_seconds(res)
    row["asr_seconds"] = res.transcript.meta.get("seconds") if isinstance(res.transcript.meta, dict) else None
    row["timings"] = dict(res.timings)
    row["models"] = sorted({str(c.meta["model"]) for c in res.checks.values() if c.meta.get("model")})
    row["asr_backend"] = res.transcript.asr_backend
    return row


def result_row(res: CallResult, call: Call | None, can_alarm: set[str]) -> Row:
    return enrich(ev.make_row(res, call, can_alarm), res)


def strip_words(res: CallResult) -> dict[str, Any]:
    d = res.model_dump(mode="json")
    for t in [d.get("transcript") or {}, *(d.get("views") or {}).values()]:
        for s in t.get("segments") or []:
            s.pop("words", None)
    return d


def cv_predict(pipe: Any, results: Sequence[CallResult], calls: Sequence[Call], fold_of: dict[str, int],
               thresholds: Sequence[float] | None = None, error_rows: Sequence[Row] = ()
               ) -> tuple[list[Row], list[dict[str, Any]]]:
    """Out-of-fold predictions (adapted from ``eval.cross_validate``, keeping the decisions for flip
    tables): per dev fold, ``suggest_threshold`` on the other folds' results, then that threshold on the
    fold. Calls whose dialogue has no fold are left out; error rows stay error rows (counted as review)."""
    by_fold: dict[int, list[CallResult]] = {}
    for r in results:
        k = fold_of.get(dialogue_of(r.call_id))
        if k is not None:
            by_fold.setdefault(k, []).append(r)
    families = pipe.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    idx = {c.call_id: c for c in calls}
    default = float(pipe.cfg.fusion.get("threshold", 0.55))
    rows: list[Row] = []
    folds: list[dict[str, Any]] = []
    if len(by_fold) < 2:
        return [], []
    for k in sorted(by_fold):
        train = [r for j, rs in by_fold.items() if j != k for r in rs]
        pick = ev.suggest_threshold(ev.sweep(pipe, train, calls, thresholds))
        t = pick["threshold"] if pick else default
        for r in by_fold[k]:
            d = pipe.decide(r.transcript, r.checks, {"threshold": t}, families)
            row = result_row(r.model_copy(update={"decision": d}), idx.get(r.call_id), can_alarm)
            row.update(cv_fold=k, cv_threshold=t)
            rows.append(row)
        folds.append({"fold": k, "threshold": t, "n_test": len(by_fold[k]),
                      "dialogues": sorted({dialogue_of(r.call_id) for r in by_fold[k]})})
    for er in error_rows:
        k = fold_of.get(er.get("dialogue_id") or dialogue_of(er["call_id"]))
        if k is not None:
            rows.append({**er, "cv_fold": k, "cv_threshold": None})
    order = {c.call_id: i for i, c in enumerate(calls)}
    rows.sort(key=lambda r: order.get(r["call_id"], 1 << 30))
    return rows, folds


def compact_sweep(swept: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"threshold": s["threshold"], "flag_f1": s["metrics"]["flag"]["f1"],
             "flag_precision": s["metrics"]["flag"]["precision"], "flag_recall": s["metrics"]["flag"]["recall"],
             "false_alarm_rate": s["metrics"]["flag"]["false_alarm_rate"],
             "miss_rate": s["metrics"]["flag"]["miss_rate"], "alarm_f1": s["metrics"]["alarm"]["f1"],
             "accuracy": s["metrics"]["accuracy"]} for s in swept]


# --------------------------------------------------------------------------------------------
# running
# --------------------------------------------------------------------------------------------

Progress = Callable[[str, int, int, str, Row], None]


@dataclass
class VariantOutput:
    name: str
    rows: list[Row]
    results: list[CallResult]
    out_dir: Path


def experiment_dir(spec: Spec, runs_dir: Path | None = None) -> Path:
    return (runs_dir or ROOT / "runs") / "experiments" / spec.name


def _serialize_stages(pipe: Any) -> None:
    """ASR and diarization hold one model each: run them one call at a time (instance-level wrap,
    the pipeline class stays untouched); checks of other calls keep going in parallel."""
    lock = threading.Lock()
    for stage in ("transcribe", "diarize"):
        fn = getattr(pipe, stage, None)
        if fn is None:
            continue

        def locked(*a: Any, _fn: Callable[..., Any] = fn, **kw: Any) -> Any:
            with lock:
                return _fn(*a, **kw)

        setattr(pipe, stage, locked)
    pipe.make_snippets = lambda result: None  # experiments never cut audio


def run_variant(spec: Spec, v: Variant, calls: Sequence[Call], out_dir: Path, *, jobs: int = 6,
                use_cache: bool = True, progress: Progress | None = None,
                pipeline_cls: Any = None) -> VariantOutput:
    from callguard.pipeline import Pipeline

    cfg = variant_config(spec, v)
    pipe = (pipeline_cls or Pipeline)(cfg, use_cache=use_cache)
    vdir = out_dir / v.name
    vdir.mkdir(parents=True, exist_ok=True)
    can_alarm = {f.id for f in pipe.ctx.families() if f.can_alarm}
    t_start = time.time()

    if v.refuse_from:
        results, rows = _refuse(pipe, cfg, out_dir / v.refuse_from, calls, can_alarm)
        for i, r in enumerate(rows, 1):
            if progress:
                progress(v.name, i, len(rows), r["call_id"], r)
    else:
        _serialize_stages(pipe)
        n = len(calls)
        done = [0]
        done_lock = threading.Lock()

        def one(call: Call) -> tuple[Row, CallResult | None]:
            t0 = time.time()
            try:
                res = pipe.process(call.audio_path, call.call_id, emit=False)
            except Exception as e:  # one broken call must not kill the variant: it becomes an error row
                log.exception("experiment %s/%s: call %s failed", spec.name, v.name, call.call_id)
                row, res = ev.error_row(call.call_id, call, f"{type(e).__name__}: {e}"), None
            else:
                row = result_row(res, call, can_alarm)
            row["seconds"] = round(time.time() - t0, 3)
            with done_lock:
                done[0] += 1
                if progress:
                    progress(v.name, done[0], n, call.call_id, row)
            return row, res

        if jobs > 1 and n > 1:
            with ThreadPoolExecutor(max_workers=jobs) as ex:
                outs = list(ex.map(one, calls))
        else:
            outs = [one(c) for c in calls]
        rows = [r for r, _ in outs]
        results = [res for _, res in outs if res is not None]

    _write_variant(spec, v, cfg, pipe, calls, rows, results, vdir, wall=time.time() - t_start)
    return VariantOutput(v.name, rows, results, vdir)


def load_results(vdir: Path) -> list[CallResult]:
    p = vdir / "results.jsonl"
    if not p.exists():
        return []
    return [CallResult.model_validate_json(line) for line in p.read_text().splitlines() if line.strip()]


def _refuse(pipe: Any, cfg: AppConfig, src_dir: Path, calls: Sequence[Call], can_alarm: set[str]
            ) -> tuple[list[CallResult], list[Row]]:
    """Re-fusion only: the source variant's stored check results, this variant's fusion/weights/checks."""
    src = {r.call_id: r for r in load_results(src_dir)}
    if not src:
        raise SpecError(f"re-fusion source {src_dir} has no results.jsonl: run that variant first")
    src_rows = {r["call_id"]: r for r in _read_rows(src_dir).get("fixed", [])}
    keep = {c.get("name") or c.get("type") for c in cfg.checks}
    families = pipe.ctx.families()
    results, rows = [], []
    for call in calls:
        r = src.get(call.call_id)
        if r is None:
            er = src_rows.get(call.call_id)
            if er is not None:
                rows.append(dict(er))
            continue
        checks = {k: c for k, c in r.checks.items() if k in keep}
        t0 = time.time()
        d = pipe.decide(r.transcript, checks, None, families)
        new = r.model_copy(update={"decision": d, "checks": checks, "config_name": cfg.name})
        results.append(new)
        row = result_row(new, call, can_alarm)
        row["seconds"] = round(time.time() - t0, 4)
        rows.append(row)
    return results, rows


def _write_variant(spec: Spec, v: Variant, cfg: AppConfig, pipe: Any, calls: Sequence[Call], rows: list[Row],
                   results: list[CallResult], vdir: Path, wall: float) -> None:
    splits = sp.load_splits(required=False)
    fold_of = cv_fold_map(spec.split, splits, calls)
    errors = [r for r in rows if r.get("error")]
    cv_rows, cv_folds = ([], []) if spec.split == sp.HOLDOUT else cv_predict(
        pipe, results, calls, fold_of, spec.thresholds, errors)
    swept = ev.sweep(pipe, results, calls, spec.thresholds) if results else []
    suggestion = ev.suggest_threshold(swept) if swept else None
    with (vdir / "results.jsonl").open("w") as f:
        for r in results:
            f.write(json.dumps(strip_words(r), ensure_ascii=False) + "\n")
    (vdir / "rows.json").write_text(json.dumps(
        {"fixed": rows, "cv": cv_rows, "cv_folds": cv_folds, "sweep": compact_sweep(swept),
         "suggestion": suggestion}, ensure_ascii=False, indent=1, default=str))
    (vdir / "metrics.json").write_text(json.dumps(
        {"fixed": ev.metrics(rows), "cv": ev.metrics(cv_rows) if cv_rows else None}, ensure_ascii=False,
        indent=1, default=str))
    meta = {
        "variant": v.name, "description": v.description, "experiment": spec.name, "split": spec.split,
        "profile": v.profile or spec.base, "set": v.set, "checks": [c.get("name") or c.get("type") for c in cfg.checks],
        "refuse_from": v.refuse_from, "oracle": is_oracle(v, cfg), "config_name": cfg.name,
        "config_hash": sp.config_hash(cfg), "threshold": cfg.fusion.get("threshold"),
        "fusion": cfg.fusion.get("type"), "asr": cfg.asr.get("type"), "asr_model": cfg.asr.get("model"),
        "llm": {k: {kk: spec_v for kk, spec_v in s.items() if kk in ("type", "model", "base_url", "cache_tag")}
                for k, s in cfg.llms.items()},
        "git": sp.git_info(), "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "wall_seconds": round(wall, 2),
        "n_calls": len(rows), "calls": [r["call_id"] for r in rows],
    }
    (vdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str))
    if spec.split == sp.HOLDOUT:
        sp.log_holdout_run(cfg, ev.metrics(rows), len(rows), kind=f"experiment {spec.name}/{v.name}",
                           overrides=v.set)


def run_experiment(spec: Spec, calls: Sequence[Call], *, variants: Sequence[str] | None = None, jobs: int = 6,
                   use_cache: bool = True, runs_dir: Path | None = None, progress: Progress | None = None,
                   n_boot: int = 2000, seed: int = 13, pipeline_cls: Any = None) -> dict[str, Any]:
    out = experiment_dir(spec, runs_dir)
    out.mkdir(parents=True, exist_ok=True)
    chosen = [spec.variant(n) for n in variants] if variants else list(spec.variants)
    chosen.sort(key=lambda v: v.refuse_from is not None)  # sources before their re-fusions
    if spec.path:
        (out / "spec.yaml").write_text(spec.path.read_text())
    for v in chosen:
        if v.refuse_from and v.refuse_from not in {c.name for c in chosen} \
                and not (out / v.refuse_from / "results.jsonl").exists():
            raise SpecError(f"{v.name} re-fuses {v.refuse_from}: run that variant first (or include it)")
        run_variant(spec, v, calls, out, jobs=jobs, use_cache=use_cache, progress=progress,
                    pipeline_cls=pipeline_cls)
    return summarize(spec, out, n_boot=n_boot, seed=seed)


# --------------------------------------------------------------------------------------------
# dry run
# --------------------------------------------------------------------------------------------


def dry_run(spec: Spec, calls: Sequence[Call], variants: Sequence[str] | None = None,
            runs_dir: Path | None = None) -> list[dict[str, Any]]:
    """What each variant would compute: config, checks, ORACLE, and (best effort) how many transcripts /
    check results are already cached. Loads no model."""
    from callguard.cache import file_hash, stable_hash
    from callguard.pipeline import Pipeline

    out_dir = experiment_dir(spec, runs_dir)
    plan = []
    for v in [spec.variant(n) for n in variants] if variants else spec.variants:
        cfg = variant_config(spec, v)
        entry: dict[str, Any] = {
            "variant": v.name, "profile": v.profile or spec.base, "set": v.set,
            "checks": [c.get("name") or c.get("type") for c in cfg.checks], "oracle": is_oracle(v, cfg),
            "refuse_from": v.refuse_from, "calls": len(calls), "threshold": cfg.fusion.get("threshold"),
            "done_before": (out_dir / v.name / "rows.json").exists()}
        if v.refuse_from:
            entry["cache"] = "re-fusion only (no ASR, no checks)"
            plan.append(entry)
            continue
        try:
            pipe = Pipeline(cfg)
            fams = pipe.ctx.families()
            asr_hit, check_miss = 0, {c.name: 0 for c in pipe.checks if c.enabled}
            for call in calls:
                key = {"audio": file_hash(call.audio_path), "asr": pipe.asr.cache_params()}
                from callguard.types import Transcript
                t = pipe.ctx.cache.get("asr", key, Transcript)
                if t is None:
                    for k in check_miss:
                        check_miss[k] += 1
                    continue
                asr_hit += 1
                dkey = {"transcript": stable_hash(t.segments), "diarizer": pipe.diarizer.cache_params(),
                        "audio": file_hash(call.audio_path)}
                t = pipe.ctx.cache.get("diarize", dkey, Transcript) or t
                for c in pipe.checks:
                    if c.enabled and pipe.cached_check(c, t, fams) is None:
                        check_miss[c.name] += 1
            entry["cache"] = {"asr_cached": f"{asr_hit}/{len(calls)}", "checks_to_compute": check_miss}
        except Exception as e:  # pipeline internals moved (views): the plan itself still stands
            entry["cache"] = f"unknown ({type(e).__name__}: {e})"
        plan.append(entry)
    return plan


# --------------------------------------------------------------------------------------------
# summary
# --------------------------------------------------------------------------------------------


def _read_rows(vdir: Path) -> dict[str, Any]:
    p = vdir / "rows.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _mean(xs: Sequence[float]) -> float | None:
    xs = [float(x) for x in xs if x is not None]
    return round(statistics.fmean(xs), 3) if xs else None


def cost(rows: Sequence[Row]) -> dict[str, Any]:
    ok = [r for r in rows if not r.get("error")]
    stages: dict[str, list[float]] = {}
    for r in ok:
        for k, x in (r.get("timings") or {}).items():
            stages.setdefault(k, []).append(x)
    checks: dict[str, list[float]] = {}
    for r in ok:
        for k, x in (r.get("check_seconds") or {}).items():
            checks.setdefault(k, []).append(x)
    return {
        "wall_s_per_call": _mean([r.get("seconds") for r in rows]),
        "stage_s_per_call": {k: _mean(v) for k, v in stages.items()},
        "check_compute_s_per_call": {k: _mean(v) for k, v in checks.items()},
        "check_compute_s_total_per_call": _mean([sum((r.get("check_seconds") or {}).values()) for r in ok]),
        "asr_compute_s_per_call": _mean([r.get("asr_seconds") for r in ok if r.get("asr_seconds") is not None]),
        "llm_calls_per_call": _mean([r.get("llm_calls") or 0 for r in ok]),
    }


def _flat(m: dict[str, Any]) -> dict[str, Any]:
    """The headline numbers of eval.metrics in one flat dict."""
    f, a, rh = m["flag"], m["alarm"], m["review_handling"]
    return {"n": m["n"], "flag_precision": f["precision"], "flag_recall": f["recall"], "flag_f1": f["f1"],
            "false_alarm_rate": f["false_alarm_rate"], "miss_rate": f["miss_rate"], "alarm_f1": a["f1"],
            "review_recall": ev._div(rh["as_review"], rh["n"]), "review_escalation": rh["escalation_rate"],
            "accuracy": m["accuracy"], "tp": f["tp"], "fp": f["fp"], "fn": f["fn"], "tn": f["tn"]}


def _groups(m: dict[str, Any]) -> dict[str, Any]:
    return {"by_level": {f"Stufe{k}": v for k, v in m["by_level"].items()}, "by_noise": m["by_noise"]}


def variant_summary(name: str, vdir: Path, n_boot: int, seed: int) -> dict[str, Any] | None:
    data = _read_rows(vdir)
    if not data:
        return None
    meta = json.loads((vdir / "meta.json").read_text()) if (vdir / "meta.json").exists() else {}
    fixed, cv = data.get("fixed") or [], data.get("cv") or []
    mf = ev.metrics(fixed)
    out: dict[str, Any] = {
        "variant": name, "oracle": bool(meta.get("oracle")), "meta": meta,
        "n_calls": len(fixed), "n_dialogues": len({r.get("dialogue_id") or dialogue_of(r["call_id"]) for r in fixed}),
        "fixed": {**_flat(mf), "ci": stats.bootstrap_ci(fixed, n_boot, seed), **_groups(mf)},
        "cv": None, "cv_folds": data.get("cv_folds") or [], "suggestion": data.get("suggestion"),
        "sweep": data.get("sweep") or [],
        "errors": mf["errors"], "check_failures": mf["check_failures"],
        "cost": cost(fixed), "commit": (meta.get("git") or {}).get("sha"),
        "dirty": (meta.get("git") or {}).get("dirty"),
    }
    if meta.get("refuse_from"):
        out["cost_note"] = f"re-fusion of {meta['refuse_from']}: check cost is that variant's"
    if cv:
        mc = ev.metrics(cv)
        out["cv"] = {**_flat(mc), "ci": stats.bootstrap_ci(cv, n_boot, seed), **_groups(mc)}
    out["degraded"] = bool(out["errors"] or out["check_failures"]["calls"])
    return out


def summarize(spec: Spec, out_dir: Path, *, n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    """Build summary.json + summary.md from every variant of the spec that has results on disk."""
    variants: dict[str, Any] = {}
    rows: dict[str, dict[str, Any]] = {}
    for v in spec.variants:
        s = variant_summary(v.name, out_dir / v.name, n_boot, seed)
        if s is not None:
            variants[v.name] = s
            rows[v.name] = _read_rows(out_dir / v.name)
    base = spec.baseline
    comparisons = []
    if base in rows:
        for name in variants:
            if name == base:
                continue
            comp: dict[str, Any] = {"a": base, "b": name,
                                    "fixed": stats.compare(rows[base]["fixed"], rows[name]["fixed"], n_boot, seed)}
            if rows[base].get("cv") and rows[name].get("cv"):
                comp["cv"] = stats.compare(rows[base]["cv"], rows[name]["cv"], n_boot, seed)
            comparisons.append(comp)
    summary = {
        "experiment": spec.name, "description": spec.description, "rq": spec.rq, "base": spec.base,
        "split": spec.split, "compare_to": base, "n_boot": n_boot, "seed": seed,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "git": sp.git_info(),
        "spec": str(spec.path.relative_to(ROOT)) if spec.path and spec.path.is_relative_to(ROOT) else (
            str(spec.path) if spec.path else None),
        "variants": variants, "comparisons": comparisons,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, default=str))
    (out_dir / "summary.md").write_text(render_summary(summary))
    return summary


# --------------------------------------------------------------------------------------------
# markdown
# --------------------------------------------------------------------------------------------


def _p(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def _f(x: float | None, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def _ci(block: dict[str, Any] | None, k: str, pct: bool = False) -> str:
    if not block:
        return "-"
    v = block.get(k)
    c = (block.get("ci") or {}).get(k) or {}
    fmt = _p if pct else _f
    if v is None:
        return "-"
    if c.get("lo") is None:
        return fmt(v)
    return f"{fmt(v)} [{fmt(c['lo'])}, {fmt(c['hi'])}]"


def _signed(x: float | None, pct: bool = False) -> str:
    if x is None:
        return "-"
    return f"{100 * x:+.0f}pp" if pct else f"{x:+.3f}"


def _tags(s: dict[str, Any]) -> str:
    tags = []
    if s.get("oracle"):
        tags.append("**ORACLE**")
    if s.get("degraded"):
        tags.append("**DEGRADED**")
    if (s.get("meta") or {}).get("refuse_from"):
        tags.append(f"re-fusion of {s['meta']['refuse_from']}")
    return ", ".join(tags)


def _table(header: list[str], body: list[list[Any]]) -> list[str]:
    return ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|",
            *("| " + " | ".join(str(c) for c in r) + " |" for r in body)]


PCT = {"false_alarm_rate", "miss_rate", "accuracy", "review_recall", "flag_precision", "flag_recall"}


def _metric_table(variants: dict[str, Any], key: str) -> list[str]:
    head = ["variant", "n", "flag F1 [95% CI]", "P", "R", "FAR [CI]", "miss [CI]", "alarm F1", "review recall",
            "3-class acc", ""]
    body = []
    for name, s in variants.items():
        b = s.get(key)
        if not b:
            continue
        body.append([name, b["n"], _ci(b, "flag_f1"), _p(b["flag_precision"]), _p(b["flag_recall"]),
                     _ci(b, "false_alarm_rate", True), _ci(b, "miss_rate", True), _f(b["alarm_f1"]),
                     _p(b["review_recall"]), _p(b["accuracy"]), _tags(s)])
    return _table(head, body)


def render_summary(s: dict[str, Any]) -> str:
    V = s["variants"]
    git = s.get("git") or {}
    out = [f"# Experiment `{s['experiment']}`", ""]
    if s.get("description"):
        out += [s["description"], ""]
    out += [f"RQ: {', '.join(s['rq']) or '-'} · base profile `{s['base']}` · split **{s['split']}** · "
            f"baseline `{s['compare_to']}` · commit {git.get('sha')}{' (dirty)' if git.get('dirty') else ''} · "
            f"{s['created']} · bootstrap {s['n_boot']}x over twin groups / dialogues (seed {s['seed']})", ""]
    if s["split"] == "holdout":
        out += ["> **HOLDOUT run**: logged in runs/holdout_log.jsonl. Do not tune on these numbers.", ""]
    if not V:
        return "\n".join(out + ["No variant has results yet."])
    out += ["Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged "
            "flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = "
            "the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 "
            "twins are paired), CIs are wide: a difference counts "
            "only if its CI excludes 0.", ""]
    out += ["## Out-of-fold (CV) - primary", "", *_metric_table(V, "cv"), ""]
    out += ["## Fixed threshold", "", *_metric_table(V, "fixed"), ""]
    out += ["## Threshold, cost, errors", ""]
    body = []
    for name, v in V.items():
        c, sug = v["cost"], v.get("suggestion") or {}
        cv_t = ", ".join(_f(f["threshold"]) for f in v.get("cv_folds") or []) or "-"
        stages = ", ".join(f"{k} {_f(x, 1)}" for k, x in (c.get("stage_s_per_call") or {}).items()) or "-"
        fails = ", ".join(f"{k} {n}x" for k, n in (v["check_failures"].get("by_check") or {}).items())
        body.append([name, _f((v["meta"] or {}).get("threshold")), _f(sug.get("threshold")), cv_t,
                     _f(c.get("wall_s_per_call"), 1), stages, _f(c.get("check_compute_s_total_per_call"), 1),
                     _f(c.get("llm_calls_per_call"), 1), v["errors"],
                     f"{v['check_failures']['calls']} ({fails})" if fails else "0", v.get("commit") or "-"])
    out += _table(["variant", "threshold", "suggested", "CV fold thresholds", "wall s/call",
                   "stage s/call (this run)", "check compute s/call", "LLM calls/call", "errors",
                   "calls w/ failed checks", "commit"], body) + [""]
    if any(v["degraded"] for v in V.values()):
        out += ["> **DEGRADED** variants had failed checks or failed calls: their numbers measure the "
                "remaining checks only (failed calls count as review). Fix and rerun before concluding.", ""]
    out += ["## Breakdown (CV, flag F1 / FAR / miss)", ""]
    groups = sorted({g for v in V.values() for g in ((v.get("cv") or v["fixed"]).get("by_level") or {})}) + \
        ["clean", "noisy"]
    body = []
    for name, v in V.items():
        b = v.get("cv") or v["fixed"]
        cells = [name]
        for g in groups:
            m = (b.get("by_level") or {}).get(g) or (b.get("by_noise") or {}).get(g)
            cells.append("-" if not m else f"{_f(m['flag_f1'])} / {_p(m['false_alarm_rate'])} / {_p(m['miss_rate'])}")
        body.append(cells)
    out += _table(["variant", *groups], body) + [""]
    for comp in s.get("comparisons") or []:
        out += _render_comparison(comp, V)
    return "\n".join(out) + "\n"


def _render_comparison(comp: dict[str, Any], V: dict[str, Any]) -> list[str]:
    a, b = comp["a"], comp["b"]
    primary = "cv" if comp.get("cv") else "fixed"
    out = [f"## `{b}` vs `{a}`" + (" (ORACLE involved)" if V[a].get("oracle") or V[b].get("oracle") else ""), ""]
    for key in ("cv", "fixed"):
        c = comp.get(key)
        if not c:
            continue
        p = c["paired"]
        n = p.get("_n", {})
        out += [f"**{'Out-of-fold (CV)' if key == 'cv' else 'Fixed threshold'}** - {n.get('calls', 0)} calls / "
                f"{n.get('dialogues', 0)} dialogues ({n.get('units', 0)} resampling units: twins together); "
                f"difference = {b} - {a}", ""]
        body = []
        for k in stats.DIFF_METRICS:
            d = p.get(k) or {}
            pct = k in PCT
            fmt = _p if pct else _f
            verdict = ("**real**: " + (b if d.get("better") == "b" else a) + " better") if d.get("real") else \
                "no detectable difference"
            body.append([k, fmt(d.get("a")), fmt(d.get("b")), _signed(d.get("diff"), pct),
                         f"[{_signed(d.get('lo'), pct)}, {_signed(d.get('hi'), pct)}]", verdict])
        out += _table(["metric", a, b, "diff", "95% CI", ""], body) + [""]
        mf, ml = c["mcnemar_flag"], c["mcnemar_label"]
        out += [f"McNemar exact (calls): flag correct only-{a} {mf['a_only']} vs only-{b} {mf['b_only']}, "
                f"p={mf['p']}; 3-class only-{a} {ml['a_only']} vs only-{b} {ml['b_only']}, p={ml['p']}.", ""]
    flips = (comp.get(primary) or {}).get("flips") or []
    if flips:
        out += [f"Flips ({primary}, {len(flips)} calls):", ""]
        out += _table(["call", "expected", a, b, "score a/b", "flag", "decisive passage / reason (b)",
                       "reason (a)"],
                      [[f["call_id"], f["expected"], f["a"], f["b"], f"{_f(f['a_score'])}/{_f(f['b_score'])}",
                        f["flag_change"], _cell(f.get("b_passage") or f.get("a_passage"), f.get("b_reason")),
                        _cell(None, f.get("a_reason"))] for f in flips]) + [""]
    else:
        out += [f"No call changes its label ({primary}).", ""]
    return out


def _cell(passage: str | None, reason: str | None) -> str:
    txt = " - ".join(x for x in (passage, reason) if x)
    txt = txt.replace("|", "/").replace("\n", " ")
    return (txt[:200] + "...") if len(txt) > 200 else (txt or "-")
