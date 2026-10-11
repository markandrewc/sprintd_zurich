"""Contribution / ablation analysis: which part of the system gives which part of the result.

Driven by a spec file (``experiments/contrib/contrib.yaml``) that names **factor comparisons** as pairs of stored
experiment variants on the SAME calls (``<experiment>/<variant>``, read from
``<data_root>/<experiment>/<variant>/rows.json`` + ``meta.json``; ``summary.json`` is optional). Nothing is
recomputed: no ASR, no LLM, only the statistics of :mod:`callguard.stats` over the stored per-call rows.

Per pair (B - A, paired over the calls both have, CI = 95% percentile bootstrap over twin groups/dialogues; rows of
different datasets (case / synthetic / test50, :mod:`callguard.datasets`) are never paired or pooled):

* flag AUC (threshold-free, from the scores) via :func:`stats.paired_auc`,
* false-alarm rate, miss rate, 3-class accuracy, review recall (and flag F1, for completeness) at the
  out-of-fold CV threshold (``rows: cv``; ``fixed`` for threshold knobs) via :func:`stats.paired_bootstrap`,
* label flips (:func:`stats.flips`) and McNemar on flag correctness.

``real`` = the CI excludes 0. A pair's **verdict** (from AUC, FAR, miss, 3-class accuracy; review recall is
shown but rests on too few calls to decide): ``gain`` (some decision metric really better, none really worse), ``loss`` (the reverse), ``mixed`` (both), ``noise`` (nothing real), ``unpaired`` (different
calls: shown side by side, no delta), ``missing`` (no data yet; ``pending: true`` marks expected runs).

Each pair also carries the spec's honesty label ``status`` (``exact`` = only the named factor differs,
``caveat`` = near-exact, read the note, ``confounded`` = something else differs too, named in ``differs``)
and an automatic ``meta_diff`` of the two variants' meta.json (profile, ASR model, check weights, LLM ids,
``--set`` overrides, oracle, commit) so a reader can verify the claim.

Other spec sections: ``path`` (waterfall of paired steps), ``generalisation`` (the same system on tuned dev,
paraphrased questions, blind table, re-recorded audio, synthetic out-of-sample), ``systems`` (per-family
heat map + cost), ``baselines`` (flag-all / flag-none on the reference rows, keyword-only), ``holdout``
(only counted for the metric guide). :func:`metric_guide` turns the result into "which metric to use for
decisions, and which not", each with our own number.

Output: ``runs/contrib/contrib.json`` + ``contrib.md`` (``callguard contrib``); the UI page
"Entscheidungshilfe" reads the JSON (or computes it on the fly when it is missing or stale).
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from callguard import stats
from callguard.config import ROOT
from callguard.datasets import rows_dataset

DEFAULT_SPEC = ROOT / "experiments" / "contrib" / "contrib.yaml"  # own folder: experiments/*.yaml = experiment specs
DEFAULT_DATA = ROOT / "runs" / "experiments"
DEFAULT_OUT = ROOT / "runs" / "contrib"
ENV_DATA = "CALLGUARD_CONTRIB_DATA"

ROW_METRICS = ("false_alarm_rate", "miss_rate", "accuracy", "review_recall", "flag_f1")
# review recall is reported but does not decide a verdict: on dev it rests on 6 calls / 3 dialogues, so its
# bootstrap CI is often degenerate (e.g. -100 [-100, -100] when all three units flip together)
VERDICT_METRICS = ("auc", "false_alarm_rate", "miss_rate", "accuracy")
LOWER_IS_BETTER = stats.LOWER_IS_BETTER
METRIC_LABELS = {
    "auc": "Flag-AUC", "false_alarm_rate": "Fehlalarmquote", "miss_rate": "Verpasst",
    "accuracy": "Exakter Status", "review_recall": "Prüf-Recall", "flag_f1": "Flag-F1",
}
VERDICT_LABELS = {"gain": "belegter Gewinn", "loss": "belegter Verlust", "mixed": "Abwägung (Gewinn und Verlust)",
                  "noise": "Rauschen (KI enthält 0)", "unpaired": "nicht gepaart", "missing": "Daten fehlen",
                  "pending": "ausstehend"}
STATUS_LABELS = {"exact": "sauber", "caveat": "fast sauber", "confounded": "verzerrt", "unpaired": "nicht gepaart",
                 "pending": "ausstehend"}
FAMILIES = ("trade", "access", "disclosure", "documentation", "splitting", "numbers")


class SpecError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# data access
# --------------------------------------------------------------------------------------------


def resolve_data_root(data_root: str | Path | None = None) -> Path:
    """Explicit argument > $CALLGUARD_CONTRIB_DATA > runs/experiments."""
    p = data_root or os.environ.get(ENV_DATA) or DEFAULT_DATA
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def split_ref(ref: str) -> tuple[str, str]:
    if not isinstance(ref, str) or ref.count("/") != 1:
        raise SpecError(f"variant reference must be '<experiment>/<variant>', got {ref!r}")
    e, v = ref.split("/")
    return e, v


@dataclass
class Variant:
    ref: str
    rows: dict[str, Any]
    meta: dict[str, Any]
    summary: dict[str, Any]  # the variant's entry in summary.json ({} if none)
    experiment_summary: dict[str, Any]

    def basis_rows(self, basis: str) -> tuple[list[dict[str, Any]], str]:
        """Rows of the requested basis; falls back to ``fixed`` when that basis was not computed (holdout)."""
        rows = self.rows.get(basis) or []
        if rows:
            return rows, basis
        return self.rows.get("fixed") or [], "fixed"


@dataclass
class Store:
    """Loads ``<data_root>/<experiment>/<variant>/`` once per reference."""
    root: Path
    _cache: dict[str, Variant | None] = field(default_factory=dict)
    _summaries: dict[str, dict[str, Any]] = field(default_factory=dict)

    def summary(self, exp: str) -> dict[str, Any]:
        if exp not in self._summaries:
            p = self.root / exp / "summary.json"
            try:
                self._summaries[exp] = json.loads(p.read_text()) if p.exists() else {}
            except (OSError, ValueError):
                self._summaries[exp] = {}
        return self._summaries[exp]

    def get(self, ref: str) -> Variant | None:
        if ref in self._cache:
            return self._cache[ref]
        exp, var = split_ref(ref)
        d = self.root / exp / var
        v = None
        if (d / "rows.json").exists():
            try:
                rows = json.loads((d / "rows.json").read_text())
                meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
            except (OSError, ValueError):
                rows = None
            if isinstance(rows, dict) and rows.get("fixed"):
                s = self.summary(exp)
                v = Variant(ref, rows, meta, (s.get("variants") or {}).get(var) or {}, s)
        self._cache[ref] = v
        return v


def fingerprint(data_root: Path, spec_path: Path | None = None) -> float:
    """Newest mtime of the spec and every rows.json/summary.json under the data root (staleness check)."""
    newest = spec_path.stat().st_mtime if spec_path and spec_path.exists() else 0.0
    if data_root.exists():
        for pat in ("*/*/rows.json", "*/summary.json"):
            for p in data_root.glob(pat):
                try:
                    newest = max(newest, p.stat().st_mtime)
                except OSError:
                    pass
    return newest


# --------------------------------------------------------------------------------------------
# per-variant record
# --------------------------------------------------------------------------------------------


def _round(x: Any, nd: int = 4) -> Any:
    return None if x is None else round(float(x), nd)


def _llm_ids(meta: dict[str, Any]) -> list[str]:
    ids = {(x or {}).get("model_id") or (x or {}).get("model") for x in (meta.get("llm_resolved") or {}).values()}
    return sorted(i for i in ids if i)


def _short_meta(meta: dict[str, Any]) -> dict[str, Any]:
    return {"profile": meta.get("profile"), "asr": meta.get("asr"), "asr_model": meta.get("asr_model"),
            "check_weights": meta.get("check_weights"), "llm": _llm_ids(meta), "set": meta.get("set") or [],
            "oracle": bool(meta.get("oracle")), "fusion": meta.get("fusion"), "threshold": meta.get("threshold"),
            "refuse_from": meta.get("refuse_from"), "commit": (meta.get("git") or {}).get("sha"),
            "description": meta.get("description")}


DIFF_KEYS = ("profile", "asr_model", "check_weights", "llm", "set", "oracle", "fusion", "threshold", "commit")


def meta_diff(meta_a: dict[str, Any], meta_b: dict[str, Any]) -> dict[str, list[Any]]:
    """What differs between two variants' meta.json (empty fields on one side are reported too)."""
    a, b = _short_meta(meta_a), _short_meta(meta_b)
    out = {}
    for k in DIFF_KEYS:
        if not meta_a or not meta_b:
            break
        if a.get(k) != b.get(k):
            out[k] = [a.get(k), b.get(k)]
    return out


def family_table(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per expected family: calls, exact label correct, flag correct (labelled rows only)."""
    out: dict[str, dict[str, Any]] = {}
    for r in stats.labeled(rows):
        f = r.get("expected_family") or "?"
        e = out.setdefault(f, {"n": 0, "label_correct": 0, "flag_correct": 0})
        e["n"] += 1
        e["label_correct"] += int(stats.label_correct(r))
        e["flag_correct"] += int(stats.flag_correct(r))
    for e in out.values():
        e["label_acc"] = _round(e["label_correct"] / e["n"])
        e["flag_acc"] = _round(e["flag_correct"] / e["n"])
    return out


def _cost(v: Variant) -> dict[str, Any]:
    c = v.summary.get("cost") or {}
    s, llm = c.get("check_compute_s_total_per_call"), c.get("llm_calls_per_call")
    rows = v.rows.get("fixed") or []
    if s is None and rows:
        s = sum(sum((r.get("check_seconds") or {}).values()) for r in rows) / len(rows)
    if llm is None and rows:
        llm = sum(r.get("llm_calls") or 0 for r in rows) / len(rows)
    return {"s_per_call": _round(s, 2), "llm_calls_per_call": _round(llm, 2),
            "wall_s_per_call": _round(c.get("wall_s_per_call"), 3)}


def variant_record(v: Variant, basis: str = "cv", n_boot: int = 2000, seed: int = 13) -> dict[str, Any]:
    rows, used = v.basis_rows(basis)
    fixed = v.rows.get("fixed") or []
    auc_s = ((v.summary.get("auc") or {}).get("flag")) or {}
    if auc_s.get("value") is None:
        auc_s = stats.bootstrap_auc(fixed, n_boot=n_boot, seed=seed)["flag"]
    ci = stats.bootstrap_ci(rows, n_boot=n_boot, seed=seed, metrics=ROW_METRICS)
    far20 = v.summary.get("cv_far") or {}
    if not far20 and v.rows.get("cv_far"):
        far20 = stats.point(v.rows["cv_far"])
    floor = ((v.summary.get("cap") or {}).get("floor")) or v.rows.get("far_floor") or {}
    dialogues = {r.get("dialogue_id") or r["call_id"].split("-K")[0] for r in fixed}
    exp_split = v.experiment_summary.get("split") or v.meta.get("split")
    tags = [t for t, on in (("ORACLE", v.meta.get("oracle") or v.summary.get("oracle")),
                            ("DEGRADED", v.summary.get("degraded")),
                            ("WARN", v.summary.get("warnings"))) if on]
    return {
        "ref": v.ref, "basis": used, "split": exp_split, "dataset": rows_dataset(fixed, v.ref), "n_calls": len(fixed), "n_dialogues": len(dialogues),
        "description": v.meta.get("description") or v.summary.get("meta", {}).get("description"),
        "tags": tags, "warnings": v.summary.get("warnings") or [],
        "auc": {"value": auc_s.get("value"), "lo": auc_s.get("lo"), "hi": auc_s.get("hi")},
        "metrics": {k: {"value": c["value"], "lo": c["lo"], "hi": c["hi"]} for k, c in ci.items()},
        "far20": {"flag_recall": far20.get("flag_recall"), "false_alarm_rate": far20.get("false_alarm_rate"),
                  "flag_f1": far20.get("flag_f1")},
        "far_floor": floor.get("false_alarm_rate"),
        "cost": _cost(v), "families": family_table(rows), "meta": _short_meta(v.meta),
    }


# --------------------------------------------------------------------------------------------
# per-pair comparison
# --------------------------------------------------------------------------------------------


def _better(metric: str, diff: float | None) -> str | None:
    if diff is None or diff == 0:
        return None
    return "b" if (diff < 0) == (metric in LOWER_IS_BETTER) else "a"


def verdict(deltas: dict[str, dict[str, Any]]) -> str:
    """gain / loss / mixed / noise from the real (CI excludes 0) decision-metric deltas."""
    good = bad = False
    for k in VERDICT_METRICS:
        d = deltas.get(k) or {}
        if d.get("real"):
            if _better(k, d.get("diff")) == "b":
                good = True
            else:
                bad = True
    return "mixed" if good and bad else "gain" if good else "loss" if bad else "noise"


def compare_rows(rows_a: dict[str, list], rows_b: dict[str, list], basis: str = "cv", n_boot: int = 2000,
                 seed: int = 13) -> dict[str, Any]:
    """Paired deltas B - A. ``rows_*`` = the rows.json dicts (``fixed`` for AUC, ``basis`` for the rest)."""
    fa, fb = rows_a.get("fixed") or [], rows_b.get("fixed") or []
    da, db = rows_dataset(fa, "rows A"), rows_dataset(fb, "rows B")  # raises on a set that mixes datasets
    if da and db and da != db:  # different datasets are never paired or pooled: side by side only
        return {"basis": basis, "n_common": 0, "only_a": len(stats.labeled(fa)), "only_b": len(stats.labeled(fb)),
                "paired": False, "datasets": [da, db]}
    ra, used_a = (rows_a.get(basis) or [], basis) if rows_a.get(basis) else (fa, "fixed")
    rb, used_b = (rows_b.get(basis) or [], basis) if rows_b.get(basis) else (fb, "fixed")
    if used_a != used_b:  # never mix a CV basis with a fixed one
        ra, rb, used_a = fa, fb, "fixed"
    ids_a = {r["call_id"] for r in stats.labeled(ra)}
    ids_b = {r["call_id"] for r in stats.labeled(rb)}
    common = ids_a & ids_b
    out: dict[str, Any] = {"basis": used_a, "n_common": len(common), "only_a": len(ids_a - ids_b),
                           "only_b": len(ids_b - ids_a)}
    if not common:
        out["paired"] = False
        return out
    out["paired"] = True
    pa = stats.paired_auc(fa, fb, n_boot=n_boot, seed=seed)["flag"]
    pb = stats.paired_bootstrap(ra, rb, n_boot=n_boot, seed=seed, metrics=ROW_METRICS)
    n = pb.pop("_n", {})
    deltas = {"auc": {k: pa.get(k) for k in ("a", "b", "diff", "lo", "hi", "real")}}
    for k in ROW_METRICS:
        deltas[k] = {x: pb[k].get(x) for x in ("a", "b", "diff", "lo", "hi", "real")}
    for k, d in deltas.items():
        d["better"] = _better(k, d.get("diff"))
    fl = stats.flips(ra, rb)
    out.update({
        "units": n.get("units"), "dialogues": n.get("dialogues"), "deltas": deltas,
        "flips": {"n": len(fl), "label_fixed": sum(f["label_change"] == "fixed" for f in fl),
                  "label_broken": sum(f["label_change"] == "broken" for f in fl),
                  "flag_fixed": sum(f["flag_change"] == "fixed" for f in fl),
                  "flag_broken": sum(f["flag_change"] == "broken" for f in fl),
                  "calls": [{k: f[k] for k in ("call_id", "expected", "a", "b", "label_change")} for f in fl]},
        "mcnemar_flag": stats.mcnemar(ra, rb, stats.flag_correct),
        "verdict": verdict(deltas),
    })
    return out


def _pct(x: Any) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def _pp(x: Any) -> str:
    return "–" if x is None else f"{100 * x:+.0f} Pkt."


def _f(x: Any, nd: int = 2) -> str:
    return "–" if x is None else f"{x:.{nd}f}"


def _s(x: Any, nd: int = 2) -> str:
    return "–" if x is None else f"{x:+.{nd}f}"


def takeaway(p: dict[str, Any]) -> str:
    """One plain German line for a pair."""
    if p["verdict"] == "missing":
        return f"{p['label']}: {'ausstehend' if p.get('pending') else 'Daten fehlen'} ({', '.join(p.get('missing_refs') or [])})."
    if p["verdict"] == "unpaired":
        a, b = p.get("rec_a") or {}, p.get("rec_b") or {}
        return (f"{p['label']}: verschiedene Anrufe, nur nebeneinander lesbar: Flag-AUC {_f((a.get('auc') or {}).get('value'))} "
                f"gegen {_f((b.get('auc') or {}).get('value'))}.")
    d = p["deltas"]
    auc = d["auc"]
    word = {"gain": "belegter Gewinn", "loss": "belegter Verlust", "mixed": "Abwägung",
            "noise": "im Rauschen"}[p["verdict"]]
    real_bits = [f"{METRIC_LABELS[k]} {_pp(d[k]['diff']) if k != 'auc' else _s(d[k]['diff'])}"
                 for k in VERDICT_METRICS if k != "auc" and (d.get(k) or {}).get("real")]
    txt = (f"{p['label']}: Flag-AUC {_f(auc['a'])} → {_f(auc['b'])} ({_s(auc['diff'])} "
           f"[{_s(auc['lo'])}, {_s(auc['hi'])}]){' belegt' if auc.get('real') else ''}; "
           f"Fehlalarme {_pct(d['false_alarm_rate']['a'])} → {_pct(d['false_alarm_rate']['b'])}, verpasst "
           f"{_pct(d['miss_rate']['a'])} → {_pct(d['miss_rate']['b'])}; {p['flips']['n']} von {p['n_common']} "
           f"Entscheiden ändern sich → **{word}**")
    if real_bits and p["verdict"] != "noise":
        txt += f" ({', '.join(real_bits)} belegt)"
    if p.get("status") == "confounded":
        txt += " · verzerrt: " + (p.get("differs") or "").rstrip(".")
    return txt + "."


def pair_record(store: Store, spec: dict[str, Any], factor: str, basis: str, n_boot: int, seed: int,
                variants: dict[str, dict[str, Any]]) -> dict[str, Any]:
    a_ref, b_ref = spec.get("a"), spec.get("b")
    split_ref(a_ref)
    split_ref(b_ref)
    label = spec.get("label") or f"{a_ref} → {b_ref}"
    p: dict[str, Any] = {"factor": factor, "label": label, "a": a_ref, "b": b_ref,
                         "status": spec.get("status") or "exact", "differs": spec.get("differs"),
                         "note": spec.get("note"), "pending": bool(spec.get("pending")),
                         "basis": spec.get("rows") or basis}
    va, vb = store.get(a_ref), store.get(b_ref)
    if va is None or vb is None:
        p.update(verdict="missing", missing_refs=[r for r, v in ((a_ref, va), (b_ref, vb)) if v is None])
        if p["pending"]:
            p["status"] = "pending"
        p["takeaway"] = takeaway(p)
        return p
    for v in (va, vb):
        if v.ref not in variants:
            variants[v.ref] = variant_record(v, basis, n_boot, seed)
    p["meta_diff"] = meta_diff(va.meta, vb.meta)
    if spec.get("unpaired"):
        c = {"paired": False, "n_common": 0}
    else:
        c = compare_rows(va.rows, vb.rows, p["basis"], n_boot, seed)
    p.update(c)
    if not c.get("paired"):
        p["verdict"] = "unpaired"
        if p["status"] == "exact":
            p["status"] = "unpaired"
        p["rec_a"], p["rec_b"] = variants[a_ref], variants[b_ref]
        p["takeaway"] = takeaway(p)
        p.pop("rec_a"), p.pop("rec_b")
        return p
    if c["only_a"] or c["only_b"]:
        p["note"] = ((p.get("note") or "") + f" Nur {c['n_common']} gemeinsame Anrufe "
                     f"(A ohne B: {c['only_a']}, B ohne A: {c['only_b']}).").strip()
    p["takeaway"] = takeaway(p)
    return p


# --------------------------------------------------------------------------------------------
# the whole analysis
# --------------------------------------------------------------------------------------------


def load_spec(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path or DEFAULT_SPEC)
    if not p.is_absolute() and not p.exists():
        p = ROOT / p
    if not p.exists():
        raise FileNotFoundError(f"contrib spec not found: {p}")
    s = yaml.safe_load(p.read_text()) or {}
    if not isinstance(s.get("factors"), list):
        raise SpecError(f"{p}: needs a `factors:` list")
    for f in s["factors"]:
        if not f.get("id") or not isinstance(f.get("pairs"), list):
            raise SpecError(f"{p}: every factor needs `id` and a `pairs` list ({f!r:.80})")
        for pr in f["pairs"]:
            split_ref(pr.get("a"))
            split_ref(pr.get("b"))
    s["_path"] = str(p)
    return s


def _identical(store: Store, a: str, b: str, basis: str) -> dict[str, Any] | None:
    """Link check between path steps: do two references hold the same decisions?"""
    va, vb = store.get(a), store.get(b)
    if va is None or vb is None:
        return None
    ra = {r["call_id"]: r for r in va.basis_rows(basis)[0]}
    rb = {r["call_id"]: r for r in vb.basis_rows(basis)[0]}
    common = set(ra) & set(rb)
    diff = sum(1 for c in common if ra[c].get("predicted") != rb[c].get("predicted"))
    sdiff = sum(1 for c in common if ra[c].get("score") != rb[c].get("score"))
    return {"a": a, "b": b, "n_common": len(common), "label_differs": diff, "score_differs": sdiff,
            "identical": diff == 0 and sdiff == 0 and len(common) == len(ra) == len(rb)}


def analyse(spec: dict[str, Any], data_root: str | Path | None = None, n_boot: int | None = None,
            seed: int | None = None) -> dict[str, Any]:
    root = resolve_data_root(data_root or spec.get("data_root"))
    store = Store(root)
    n_boot = int(n_boot or spec.get("n_boot") or 2000)
    seed = int(seed if seed is not None else spec.get("seed", 13))
    basis = spec.get("rows") or "cv"
    variants: dict[str, dict[str, Any]] = {}

    def rec(ref: str) -> dict[str, Any] | None:
        if ref in variants:
            return variants[ref]
        v = store.get(ref)
        if v is None:
            return None
        variants[ref] = variant_record(v, basis, n_boot, seed)
        return variants[ref]

    factors = []
    for f in spec["factors"]:
        pairs = [pair_record(store, pr, f["id"], basis, n_boot, seed, variants) for pr in f["pairs"]]
        factors.append({"id": f["id"], "title": f.get("title") or f["id"], "short": f.get("short") or f["id"],
                        "meaning": f.get("meaning"),
                        "group": f.get("group"), "pending": bool(f.get("pending")), "pairs": pairs,
                        "summary": factor_summary(pairs, f.get("lead"))})

    path = None
    if spec.get("path"):
        ps = spec["path"]
        steps = [pair_record(store, st, "path", basis, n_boot, seed, variants) for st in ps.get("steps") or []]
        links = []
        for s1, s2 in zip(ps.get("steps") or [], (ps.get("steps") or [])[1:]):
            if s1["b"] != s2["a"]:
                links.append(_identical(store, s1["b"], s2["a"], basis))
        path = {"title": ps.get("title"), "start_label": ps.get("start_label"), "end_label": ps.get("end_label"),
                "steps": steps, "links": [x for x in links if x]}

    gen = []
    for tr in spec.get("generalisation") or []:
        entries = []
        base_ref = (tr.get("entries") or [{}])[0].get("ref")
        for e in tr.get("entries") or []:
            r = rec(e["ref"])
            item = {"label": e.get("label") or e["ref"], "ref": e["ref"], "kind": e.get("kind"),
                    "note": e.get("note"), "pending": bool(e.get("pending")), "available": r is not None}
            if r is not None and base_ref and e["ref"] != base_ref and store.get(base_ref) is not None:
                c = compare_rows(store.get(base_ref).rows, store.get(e["ref"]).rows, basis, n_boot, seed)
                item["vs_base"] = ({"paired": True, "n_common": c["n_common"], "verdict": c["verdict"],
                                    "deltas": {k: c["deltas"][k] for k in ("auc", "false_alarm_rate", "miss_rate")},
                                    "flips": c["flips"]["n"]} if c.get("paired") else {"paired": False})
            entries.append(item)
        gen.append({"title": tr.get("title"), "base": base_ref, "entries": entries})

    systems = []
    for s in spec.get("systems") or []:
        r = rec(s["ref"])
        systems.append({"label": s.get("label") or s["ref"], "ref": s["ref"], "pending": bool(s.get("pending")),
                        "available": r is not None, "note": s.get("note")})

    bl = spec.get("baselines") or {}
    baselines: dict[str, Any] = {}
    if bl.get("reference") and store.get(bl["reference"]) is not None:
        ref_rows, _ = store.get(bl["reference"]).basis_rows(basis)
        rec(bl["reference"])
        baselines = {"reference": bl["reference"], **stats.trivial_baselines(ref_rows)}
    for key in ("keyword_only", "v1"):
        if bl.get(key) and rec(bl[key]) is not None:
            baselines[key] = bl[key]
    noise = None
    if bl.get("rerun"):
        noise = pair_record(store, {**bl["rerun"], "status": "caveat"}, "rerun", basis, n_boot, seed, variants)

    holdout = []
    for ref in spec.get("holdout") or []:
        r = rec(ref)
        if r is not None:
            holdout.append(ref)
    log = root.parent / "holdout_log.jsonl"
    looks = sum(1 for line in log.read_text().splitlines() if line.strip()) if log.exists() else None

    result = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "spec": spec.get("_path"), "data_root": str(root),
        "fingerprint": fingerprint(root, Path(spec["_path"]) if spec.get("_path") else None),
        "n_boot": n_boot, "seed": seed, "basis": basis, "reference": spec.get("reference"),
        "factors": factors, "path": path, "generalisation": gen, "systems": systems, "baselines": baselines,
        "rerun": noise, "holdout": {"refs": holdout, "looks_logged": looks}, "variants": variants,
    }
    result["guide"] = metric_guide(result)
    return result


def factor_summary(pairs: Sequence[dict[str, Any]], lead_label: str | None = None) -> dict[str, Any]:
    """Verdict counts over the clean comparisons (confounded ones counted apart) + the lead comparison:
    the spec's ``lead`` label if given, else the cleanest status first (exact > caveat > confounded), then the
    largest |delta AUC|."""
    counts: dict[str, int] = {}
    n_conf = 0
    for p in pairs:
        if p.get("status") == "confounded" and p["verdict"] not in ("missing", "unpaired"):
            n_conf += 1
            continue
        counts[p["verdict"]] = counts.get(p["verdict"], 0) + 1
    rank = {"exact": 2, "caveat": 1}
    scored = [p for p in pairs if p.get("deltas") and p["deltas"]["auc"].get("diff") is not None]
    lead = next((p for p in scored if lead_label and p["label"] == lead_label), None) or max(
        scored, key=lambda p: (rank.get(p["status"], 0), abs(p["deltas"]["auc"]["diff"])), default=None)
    parts = [f"{n}× {VERDICT_LABELS[v]}" for v, n in sorted(counts.items())]
    if n_conf:
        parts.append(f"{n_conf}× verzerrt (nicht gezählt)")
    line = ", ".join(parts)
    if lead:
        line += f". Leitvergleich: {lead['takeaway']}"
    elif pairs:
        line += ". " + pairs[0]["takeaway"]
    return {"counts": counts, "confounded": n_conf, "line": line, "lead": lead["label"] if lead else None}


def iter_pairs(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for f in result["factors"] for p in f["pairs"]]


# --------------------------------------------------------------------------------------------
# metric guide
# --------------------------------------------------------------------------------------------


def metric_guide(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Which metrics to use for decisions and which not, each with the number from our own data."""
    V = result["variants"]
    ref = V.get(result.get("reference") or "") or {}
    m = ref.get("metrics") or {}
    bl = result.get("baselines") or {}
    kw = V.get(bl.get("keyword_only") or "") or {}
    pairs = [p for p in iter_pairs(result) if p.get("deltas")]
    noise_pairs = [p for p in pairs if p["verdict"] == "noise"]
    rr = result.get("rerun") or {}
    rd = rr.get("deltas") or {}
    hold = [V[r] for r in (result.get("holdout") or {}).get("refs") or [] if r in V]
    looks = (result.get("holdout") or {}).get("looks_logged") or len(hold)

    def ci(block: dict[str, Any] | None, pct: bool = True) -> str:
        b = block or {}
        if b.get("value") is None:
            return "–"
        f = _pct if pct else _f
        return f"{f(b['value'])} [{f(b.get('lo'))}, {f(b.get('hi'))}]" if b.get("lo") is not None else f(b["value"])

    name = result.get("reference") or "Referenz"
    fa = bl.get("flag_all") or {}
    guide = [
        {"metric": "Flag-AUC", "use": "ja (Hauptmass)",
         "why": "Schwellenfrei: rangiert der Score markierungswürdige Anrufe über harmlose? Unabhängig von Schwelle "
                "und Prävalenz; 0.5 = Zufall.",
         "number": f"{name}: {ci(ref.get('auc'), pct=False)}; nur Stichwörter: {_f((kw.get('auc') or {}).get('value'))}"},
        {"metric": "CV@FAR20 (Recall bei ≤ 20% Fehlalarmen)", "use": "ja (Betriebspunkt)",
         "why": "Schwelle auf den anderen Dev-Folds gewählt (out-of-fold), so dass höchstens 20% harmlose Anrufe "
                "markiert werden: so würde das System betrieben.",
         "number": f"{name}: Recall {_pct((ref.get('far20') or {}).get('flag_recall'))} bei "
                   f"{_pct((ref.get('far20') or {}).get('false_alarm_rate'))} Fehlalarmen"},
        {"metric": "Fehlalarmquote und Verpasst (CV-Schwelle)", "use": "ja (immer zusammen)",
         "why": "Die zwei Fehlerarten, die Officer und Bank spüren: Fehlalarme kosten Zeit, Verpasste sind das "
                "Compliance-Risiko. Einzeln lässt sich jede auf 0 drücken.",
         "number": f"{name}: Fehlalarme {ci(m.get('false_alarm_rate'))}, verpasst {ci(m.get('miss_rate'))}"},
        {"metric": "Exakter Status (3 Klassen)", "use": "ja (Zweitmass)",
         "why": "Alarm / Prüfen / Kein Alarm genau richtig: zählt, ob offene Fälle als Prüfen erkannt werden.",
         "number": f"{name}: {ci(m.get('accuracy'))}; immer 'Kein Alarm': {_pct((bl.get('flag_none') or {}).get('accuracy'))}"},
        {"metric": "Prüf-Recall", "use": "mit Vorsicht",
         "why": "Anteil der Soll-'Prüfen'-Fälle, die als Prüfen kommen. Sehr wenige Fälle: breite Intervalle.",
         "number": f"{name}: {ci(m.get('review_recall'))}"},
        {"metric": "FAR-Boden", "use": "ja (Ausschlusskriterium)",
         "why": "Fehlalarmquote bei Schwelle 1.0: Anrufe, die die Prüf-Regeln von sich aus markieren. Liegt er über "
                "20%, kann keine Schwelle die Vorgabe erfüllen.",
         "number": f"{name}: {_pct(ref.get('far_floor'))}"
                   + (f"; v1: {_pct((V.get(bl.get('v1') or '') or {}).get('far_floor'))}" if bl.get("v1") else "")},
        {"metric": "Flag-F1 allein", "use": "nein",
         "why": "Etwa die Hälfte der Dev-Anrufe ist markierungswürdig: 'alles markieren' erreicht schon einen hohen "
                "F1 bei 100% Fehlalarmen.",
         "number": f"alles markieren: F1 {_f(fa.get('flag_f1'))} (Prävalenz {_pct((bl.get('_n') or {}).get('prevalence_flag'))}, "
                   f"Fehlalarme {_pct(fa.get('false_alarm_rate'))}); {name}: F1 {_f((m.get('flag_f1') or {}).get('value'))}"},
        {"metric": "Holdout-Zahlen", "use": "nein (nur Plausibilität)",
         "why": "Sehr wenige Dialoge und mehrfach angeschaut: jede Zahl kippt mit einem Anruf. Der echte Test ist das "
                "versteckte Set am Sonntag.",
         "number": (f"{hold[0]['n_calls']} Anrufe / {hold[0]['n_dialogues']} Dialoge, {looks} Blicke" if hold
                    else "keine Holdout-Läufe gefunden")},
        {"metric": "Einzellauf-Unterschiede innerhalb der Intervalle", "use": "nein",
         "why": "Überlappen sich die 95%-Intervalle bzw. enthält das gepaarte Intervall 0, ist kein Unterschied belegt. "
                "v1 (freier Richter, T=0.7) ist zudem von Lauf zu Lauf nicht reproduzierbar.",
         "number": f"{len(noise_pairs)} von {len(pairs)} gepaarten Vergleichen sind Rauschen"
                   + (f"; v1 zweimal gerechnet: Fehlalarme {_pct((rd.get('false_alarm_rate') or {}).get('a'))} vs "
                      f"{_pct((rd.get('false_alarm_rate') or {}).get('b'))}, {rr.get('flips', {}).get('n')} von "
                      f"{rr.get('n_common')} Entscheiden anders" if rd else "")},
    ]
    return guide


# --------------------------------------------------------------------------------------------
# outputs
# --------------------------------------------------------------------------------------------


def _ci_cell(d: dict[str, Any] | None, pct: bool) -> str:
    if not d or d.get("diff") is None:
        return "–"
    if pct:
        s = f"{100 * d['diff']:+.0f} [{100 * d['lo']:+.0f}, {100 * d['hi']:+.0f}]" if d.get("lo") is not None else f"{100 * d['diff']:+.0f}"
    else:
        s = f"{d['diff']:+.2f} [{d['lo']:+.2f}, {d['hi']:+.2f}]" if d.get("lo") is not None else f"{d['diff']:+.2f}"
    return f"**{s}**" if d.get("real") else s


def render_markdown(result: dict[str, Any]) -> str:
    V = result["variants"]
    out = ["# Was bringt was: Beitrag der Komponenten", "",
           f"Generated {result['created']} by `callguard contrib` from `{result['data_root']}` "
           f"(spec `{result['spec']}`, {result['n_boot']} bootstrap resamples, seed {result['seed']}). "
           "Every row is a **paired** comparison B − A on the same calls; 95% percentile bootstrap CI over twin "
           "groups/dialogues; **bold** = CI excludes 0 (real). AUC = flag AUC from the scores; FAR / miss / acc / "
           f"review recall at the `{result['basis']}` threshold (out-of-fold CV unless the row says `fixed`), "
           "differences in percentage points. Verdict: gain / loss = some decision metric (AUC, FAR, miss, 3-class "
           "acc) really better / worse, mixed = both, noise = nothing real; review recall is shown but does not "
           "decide (6 dev calls / 3 dialogues). Status: exact = only the factor differs, caveat = near-exact (note), "
           "confounded = something else differs too.", ""]
    out += ["## Factors", "",
            "| factor | comparison (A → B) | status | n | Δ flag AUC | Δ FAR (pp) | Δ miss (pp) | Δ 3-class acc (pp) | "
            "Δ review recall (pp) | flips | verdict |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    confounded = []
    pending = []
    for f in result["factors"]:
        for p in f["pairs"]:
            if p["verdict"] == "missing":
                pending.append(p)
                continue
            if p["status"] in ("confounded", "caveat") and (p.get("differs") or p.get("note")):
                confounded.append(p)
            if p["verdict"] == "unpaired":
                a, b = V.get(p["a"], {}), V.get(p["b"], {})
                out.append(f"| {f['title']} | {p['label']} | unpaired | {a.get('n_calls')} / {b.get('n_calls')} | "
                           f"{_f((a.get('auc') or {}).get('value'))} vs {_f((b.get('auc') or {}).get('value'))} | "
                           f"{_pct((a.get('metrics') or {}).get('false_alarm_rate', {}).get('value'))} vs "
                           f"{_pct((b.get('metrics') or {}).get('false_alarm_rate', {}).get('value'))} | "
                           f"{_pct((a.get('metrics') or {}).get('miss_rate', {}).get('value'))} vs "
                           f"{_pct((b.get('metrics') or {}).get('miss_rate', {}).get('value'))} | – | – | – | unpaired |")
                continue
            d = p["deltas"]
            basis = "" if p["basis"] == result["basis"] else f" ({p['basis']})"
            out.append(f"| {f['title']} | {p['label']}{basis} | {p['status']} | {p['n_common']} | "
                       f"{_ci_cell(d['auc'], False)} | {_ci_cell(d['false_alarm_rate'], True)} | "
                       f"{_ci_cell(d['miss_rate'], True)} | {_ci_cell(d['accuracy'], True)} | "
                       f"{_ci_cell(d['review_recall'], True)} | {p['flips']['n']} | {p['verdict']} |")
    out += ["", "### Takeaway per factor", ""]
    out += [f"- **{f['title']}**: {f['summary']['line']}" for f in result["factors"] if f["pairs"]]
    if confounded:
        out += ["", "### Confounded / caveat comparisons (what else differs)", ""]
        out += [f"- `{p['a']}` → `{p['b']}` ({p['status']}): {p.get('differs') or ''} {p.get('note') or ''}".rstrip()
                for p in confounded]
    path = result.get("path")
    if path and path["steps"]:
        out += ["", f"## Path: {path.get('title') or ''}", "",
                "| step | A → B | flag AUC A → B | Δ AUC | Δ FAR (pp) | Δ miss (pp) | Δ acc (pp) | verdict |",
                "|---|---|---|---|---|---|---|---|"]
        for s in path["steps"]:
            if not s.get("deltas"):
                out.append(f"| {s['label']} | `{s['a']}` → `{s['b']}` | – | – | – | – | – | {s['verdict']} |")
                continue
            d = s["deltas"]
            out.append(f"| {s['label']} | `{s['a']}` → `{s['b']}` | {_f(d['auc']['a'])} → {_f(d['auc']['b'])} | "
                       f"{_ci_cell(d['auc'], False)} | {_ci_cell(d['false_alarm_rate'], True)} | "
                       f"{_ci_cell(d['miss_rate'], True)} | {_ci_cell(d['accuracy'], True)} | {s['verdict']} |")
        for ln in path.get("links") or []:
            out.append(f"\nLink check `{ln['a']}` = `{ln['b']}`: "
                       + ("identical decisions and scores." if ln["identical"] else
                          f"{ln['label_differs']} labels / {ln['score_differs']} scores differ of {ln['n_common']}."))
    if result.get("generalisation"):
        out += ["", "## Generalisation (same system, other conditions)", "",
                "| track | condition | variant | n | flag AUC [95% CI] | FAR | miss | 3-class acc | vs first row |",
                "|---|---|---|---|---|---|---|---|---|"]
        for tr in result["generalisation"]:
            for e in tr["entries"]:
                r = V.get(e["ref"])
                if r is None:
                    out.append(f"| {tr['title']} | {e['label']} | `{e['ref']}` | – | {'pending' if e['pending'] else 'missing'} | | | | |")
                    continue
                a = r["auc"]
                vs = e.get("vs_base")
                vs_txt = "base" if vs is None else ("unpaired (other calls)" if not vs.get("paired") else
                                                    f"Δ AUC {_ci_cell(vs['deltas']['auc'], False)}, {vs['flips']} flips")
                out.append(f"| {tr['title']} | {e['label']} | `{e['ref']}` | {r['n_calls']} | "
                           f"{_f(a['value'])} [{_f(a['lo'])}, {_f(a['hi'])}] | "
                           f"{_pct(r['metrics']['false_alarm_rate']['value'])} | {_pct(r['metrics']['miss_rate']['value'])} | "
                           f"{_pct(r['metrics']['accuracy']['value'])} | {vs_txt} |")
    bl = result.get("baselines") or {}
    if bl:
        out += ["", "## Reference rows (baselines)", "", "| system | flag AUC | flag F1 | FAR | miss | 3-class acc |",
                "|---|---|---|---|---|---|"]
        ref = V.get(bl.get("reference") or "")
        if ref:
            m = ref["metrics"]
            out.append(f"| {bl['reference']} | {_f(ref['auc']['value'])} | {_f(m['flag_f1']['value'])} | "
                       f"{_pct(m['false_alarm_rate']['value'])} | {_pct(m['miss_rate']['value'])} | {_pct(m['accuracy']['value'])} |")
        for k, lab in (("flag_all", "flag everything (alarm)"), ("flag_none", "flag nothing (no_alert)")):
            x = bl.get(k) or {}
            out.append(f"| {lab} | 0.50 | {_f(x.get('flag_f1'))} | {_pct(x.get('false_alarm_rate'))} | "
                       f"{_pct(x.get('miss_rate'))} | {_pct(x.get('accuracy'))} |")
        for k in ("keyword_only", "v1"):
            r = V.get(bl.get(k) or "")
            if r:
                m = r["metrics"]
                out.append(f"| {k}: {r['ref']} | {_f(r['auc']['value'])} | {_f(m['flag_f1']['value'])} | "
                           f"{_pct(m['false_alarm_rate']['value'])} | {_pct(m['miss_rate']['value'])} | {_pct(m['accuracy']['value'])} |")
    out += ["", "## Metric guide", "", "| metric | use for decisions? | why | our number |", "|---|---|---|---|"]
    out += [f"| {g['metric']} | {g['use']} | {g['why']} | {g['number']} |" for g in result.get("guide") or []]
    systems = [s for s in result.get("systems") or [] if s["available"]]
    if systems:
        fams = [f for f in FAMILIES if any(f in V[s["ref"]]["families"] for s in systems)]
        out += ["", "## Per family (% exact label) and cost", "",
                "| system | " + " | ".join(fams) + " | flag AUC | s/call | LLM calls/call |",
                "|---|" + "---|" * (len(fams) + 3)]
        for s in systems:
            r = V[s["ref"]]
            cells = []
            for f in fams:
                x = r["families"].get(f)
                cells.append("–" if not x else f"{_pct(x['label_acc'])} ({x['n']})")
            out.append(f"| {s['label']} | " + " | ".join(cells) + f" | {_f(r['auc']['value'])} | "
                       f"{_f(r['cost']['s_per_call'], 1)} | {_f(r['cost']['llm_calls_per_call'], 1)} |")
    if pending:
        out += ["", "## Pending / missing comparisons (light up when the data appears)", ""]
        out += [f"- {p['factor']}: `{p['a']}` → `{p['b']}` ({'pending' if p['pending'] else 'missing'}: "
                f"{', '.join(p.get('missing_refs') or [])})" for p in pending]
    return "\n".join(out) + "\n"


def write_outputs(result: dict[str, Any], out_dir: str | Path | None = None) -> tuple[Path, Path]:
    d = Path(out_dir or DEFAULT_OUT)
    d.mkdir(parents=True, exist_ok=True)
    pj, pm = d / "contrib.json", d / "contrib.md"
    pj.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    pm.write_text(render_markdown(result))
    return pj, pm


def load_or_compute(spec_path: str | Path | None = None, data_root: str | Path | None = None,
                    out_dir: str | Path | None = None) -> tuple[dict[str, Any], str]:
    """The precomputed contrib.json if it matches this data root and nothing changed since; else analyse
    live. Returns (result, "file" | "live")."""
    spec = load_spec(spec_path)
    root = resolve_data_root(data_root or spec.get("data_root"))
    p = Path(out_dir or DEFAULT_OUT) / "contrib.json"
    if p.exists():
        try:
            res = json.loads(p.read_text())
            if (res.get("data_root") == str(root) and res.get("spec") == spec.get("_path")
                    and float(res.get("fingerprint") or 0) >= fingerprint(root, Path(spec["_path"]))):
                return res, "file"
        except (OSError, ValueError):
            pass
    return analyse(spec, root), "live"
