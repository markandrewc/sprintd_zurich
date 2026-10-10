"""Prüfmodi: operating modes the compliance officer picks in the sidebar. Pure (no Streamlit).

A mode is a rule of the ``two_readers`` fusion (:mod:`callguard.fusion.two_readers`) applied to the stored
per-check results of every call: ``a`` (reader A alone = the champion), ``b`` (reader B alone, Kev) or
``labels`` (R1: agreement decides, disagreement -> review). Switching mode re-decides every call from stored
results (no ASR, no LLM), exactly like the threshold slider does.

* :func:`load_spec` reads ``config/pruefmodi.yaml`` (modes, default, readers, metrics source).
* :func:`load_metrics` reads each mode's measured consequences from the experiment's out-of-fold CV rows
  (``runs/experiments/<experiment>/summary.json``), falling back to the committed snapshot
  ``research/evidence/pruefmodi_metrics.json``. Nothing about the numbers is hardcoded.
* :func:`availability` says per mode whether it can run on the shown calls (modes needing reader B are
  disabled when no call has reader B's results) and why not.
* :func:`engine_for` wraps the UI :class:`~callguard.ui.backend.Engine` so ``decide`` uses the mode's rule;
  calls that lack reader B fall back to the default mode and say so in their reasons.
* :func:`load_choice` / :func:`save_choice` persist the choice per profile (``runs/ui_prefs.json``).

Regenerate the snapshot after re-running the experiment::

    uv run python -m callguard.ui.modes snapshot
"""

from __future__ import annotations

import datetime as _dt
import json
import logging
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from callguard import agreement as ag
from callguard.cache import stable_hash
from callguard.config import ROOT, AppConfig
from callguard.types import CallResult, Decision, Family

log = logging.getLogger("callguard")

MODES_FILE = ROOT / "config" / "pruefmodi.yaml"
SNAPSHOT_FILE = ROOT / "research" / "evidence" / "pruefmodi_metrics.json"
PREFS_FILE = "ui_prefs.json"  # under the runs root, one entry per profile / source
CAN_SWITCH = ("weighted", "two_readers")  # fusion types a two_readers rule can be laid over


# --------------------------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Mode:
    id: str
    label: str
    text: str
    rule: str  # a | b | labels (see callguard.agreement.RULES)
    needs_second: bool
    metrics: str  # experiment variant whose CV rows describe the mode
    threshold: str | float = "profile"  # profile | suggested | number


@dataclass(frozen=True)
class ModeSpec:
    modes: tuple[Mode, ...]
    default: str
    experiment: str
    readers: tuple[str, str] = ("facts", "facts_kev")
    reader_labels: tuple[str, str] = ("Qwen", "Kev")
    second_reader: str = "Kev"

    def get(self, mode_id: str | None) -> Mode:
        return next((m for m in self.modes if m.id == mode_id), self.default_mode)

    @property
    def default_mode(self) -> Mode:
        return next(m for m in self.modes if m.id == self.default)

    @property
    def ids(self) -> list[str]:
        return [m.id for m in self.modes]


def parse_spec(data: Mapping[str, Any]) -> ModeSpec:
    modes = []
    for raw in data.get("modes") or []:
        rule = str(raw.get("rule", "a"))
        if rule not in ag.RULES or rule == "facts":
            raise ValueError(f"Prüfmodus {raw.get('id')!r}: rule must be a, b or labels, got {rule!r}")
        thr = raw.get("threshold", "profile")
        if not (thr in ("profile", "suggested") or isinstance(thr, (int, float))):
            raise ValueError(f"Prüfmodus {raw.get('id')!r}: threshold must be profile, suggested or a number")
        modes.append(Mode(id=str(raw["id"]), label=str(raw.get("label") or raw["id"]), text=str(raw.get("text") or ""),
                          rule=rule, needs_second=bool(raw.get("needs_second", rule != "a")),
                          metrics=str(raw.get("metrics") or raw["id"]), threshold=thr))
    if not modes:
        raise ValueError("Prüfmodi: no modes configured")
    ids = [m.id for m in modes]
    if len(set(ids)) != len(ids):
        raise ValueError(f"Prüfmodi: duplicate ids {ids}")
    default = str(data.get("default") or modes[0].id)
    if default not in ids:
        raise ValueError(f"Prüfmodi: default {default!r} is not a mode ({ids})")
    if next(m for m in modes if m.id == default).needs_second:
        raise ValueError("Prüfmodi: the default mode must not need the second reader (it is the fallback)")
    readers = tuple(data.get("readers") or ("facts", "facts_kev"))
    labels = tuple(data.get("reader_labels") or readers)
    if len(readers) != 2 or len(labels) != 2:
        raise ValueError("Prüfmodi: readers / reader_labels need exactly two entries")
    return ModeSpec(modes=tuple(modes), default=default, experiment=str(data.get("experiment") or ""),
                    readers=(str(readers[0]), str(readers[1])), reader_labels=(str(labels[0]), str(labels[1])),
                    second_reader=str(data.get("second_reader") or labels[1]))


def load_spec(path: str | Path | None = None) -> ModeSpec:
    p = Path(path) if path else MODES_FILE
    return parse_spec(yaml.safe_load(p.read_text()) or {})


# --------------------------------------------------------------------------------------------
# measured consequences (CV rows of the experiment)
# --------------------------------------------------------------------------------------------

Z95 = 1.959964


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """95 % Wilson score interval for k of n (used where the bootstrap CI collapses, e.g. 0 of 22 -> [0, 0])."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centre - half), min(1.0, centre + half)


@dataclass(frozen=True)
class Rate:
    """A measured proportion k / n with its 95 % interval (bootstrap over dialogues; Wilson if that collapses)."""
    value: float
    lo: float
    hi: float
    k: int
    n: int
    method: str = "bootstrap"

    @classmethod
    def build(cls, value: float, ci: Mapping[str, Any] | None, k: int, n: int) -> "Rate":
        lo, hi = (ci or {}).get("lo"), (ci or {}).get("hi")
        if lo is None or hi is None or hi - lo < 1e-9:
            lo, hi = wilson(k, n)
            return cls(float(value), round(lo, 4), round(hi, 4), int(k), int(n), "wilson")
        return cls(float(value), float(lo), float(hi), int(k), int(n), "bootstrap")


@dataclass(frozen=True)
class ModeMetrics:
    variant: str
    n_calls: int
    far: Rate  # harmless calls flagged (alarm or review) / harmless calls
    recall: Rate  # flaggable calls flagged / flaggable calls
    review_recall: float | None = None
    review_k: int | None = None
    review_n: int | None = None
    accuracy: float | None = None
    auc: float | None = None
    n_alarm: int | None = None
    n_review: int | None = None
    suggested_threshold: float | None = None
    source: str = ""

    @property
    def miss(self) -> float:
        return 1.0 - self.recall.value

    @property
    def prevalence(self) -> float:
        return self.recall.n / self.n_calls if self.n_calls else 0.0


def variant_metrics(summary: Mapping[str, Any], variant: str, rows: list[dict[str, Any]] | None = None,
                    source: str = "") -> ModeMetrics | None:
    """One variant's out-of-fold CV block (+ its CV rows for review counts) as :class:`ModeMetrics`."""
    v = (summary.get("variants") or {}).get(variant)
    cv = (v or {}).get("cv")
    if not cv:
        return None
    ci = cv.get("ci") or {}
    tp, fn, fp, tn = (int(cv.get(k) or 0) for k in ("tp", "fn", "fp", "tn"))
    rev_k = rev_n = n_alarm = n_review = None
    if rows:
        rev_n = sum(1 for r in rows if r.get("expected") == "review")
        rev_k = sum(1 for r in rows if r.get("expected") == "review" and r.get("predicted") == "review")
        n_alarm = sum(1 for r in rows if r.get("predicted") == "alarm")
        n_review = sum(1 for r in rows if r.get("predicted") == "review")
    return ModeMetrics(
        variant=variant, n_calls=int(cv.get("n") or tp + fn + fp + tn),
        far=Rate.build(cv.get("false_alarm_rate") or 0.0, ci.get("false_alarm_rate"), fp, fp + tn),
        recall=Rate.build(cv.get("flag_recall") or 0.0, ci.get("flag_recall"), tp, tp + fn),
        review_recall=cv.get("review_recall"), review_k=rev_k, review_n=rev_n, accuracy=cv.get("accuracy"),
        auc=((v.get("auc") or {}).get("flag") or {}).get("value"), n_alarm=n_alarm, n_review=n_review,
        suggested_threshold=(v.get("suggestion") or {}).get("threshold"), source=source)


def _metrics_to_json(m: ModeMetrics) -> dict[str, Any]:
    d = dict(m.__dict__)
    d["far"], d["recall"] = dict(m.far.__dict__), dict(m.recall.__dict__)
    return d


def _metrics_from_json(d: Mapping[str, Any]) -> ModeMetrics:
    d = dict(d)
    d["far"], d["recall"] = Rate(**d["far"]), Rate(**d["recall"])
    return ModeMetrics(**d)


def metrics_from_runs(spec: ModeSpec, runs_root: str | Path) -> dict[str, ModeMetrics]:
    exp = Path(runs_root) / "experiments" / spec.experiment
    f = exp / "summary.json"
    if not spec.experiment or not f.is_file():
        return {}
    try:
        summary = json.loads(f.read_text())
    except Exception as e:
        log.warning("Prüfmodi: unreadable %s: %s", f, e)
        return {}
    out = {}
    for m in spec.modes:
        rows = None
        rf = exp / m.metrics / "rows.json"
        if rf.is_file():
            try:
                rows = (json.loads(rf.read_text()) or {}).get("cv")
            except Exception:
                rows = None
        mm = variant_metrics(summary, m.metrics, rows, source=f"runs/experiments/{spec.experiment} (CV-Zeilen)")
        if mm is not None:
            out[m.id] = mm
    return out


def write_snapshot(spec: ModeSpec, runs_root: str | Path, path: str | Path | None = None) -> Path:
    metrics = metrics_from_runs(spec, runs_root)
    if not metrics:
        raise FileNotFoundError(f"no CV metrics under {Path(runs_root) / 'experiments' / spec.experiment}")
    summary = json.loads((Path(runs_root) / "experiments" / spec.experiment / "summary.json").read_text())
    p = Path(path) if path else SNAPSHOT_FILE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({
        "about": "Measured consequences of each Prüfmodus (config/pruefmodi.yaml): out-of-fold CV rows of the "
                 "experiment, dev split. Generated by `python -m callguard.ui.modes snapshot`; read by the UI "
                 "when runs/ is absent.",
        "experiment": spec.experiment, "split": summary.get("split"), "experiment_created": summary.get("created"),
        "experiment_git": summary.get("git"),
        "created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "modes": {k: _metrics_to_json(v) for k, v in metrics.items()},
    }, indent=1, ensure_ascii=False) + "\n")
    return p


def load_metrics(spec: ModeSpec, runs_root: str | Path | None, snapshot: str | Path | None = None
                 ) -> dict[str, ModeMetrics]:
    """Per mode id: the experiment's CV metrics from ``runs/``, else the committed snapshot, else nothing."""
    if runs_root is not None:
        live = metrics_from_runs(spec, runs_root)
        if live:
            return live
    p = Path(snapshot) if snapshot else SNAPSHOT_FILE
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text())
        if data.get("experiment") != spec.experiment:
            return {}
        src = f"Schnappschuss {p.name} ({data.get('experiment')}, {str(data.get('experiment_created') or '')[:10]})"
        return {k: _metrics_from_json({**v, "source": src}) for k, v in (data.get("modes") or {}).items()
                if k in spec.ids}
    except Exception as e:
        log.warning("Prüfmodi: unreadable snapshot %s: %s", p, e)
        return {}


def pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.0f} %"


def pct_range(lo: float, hi: float) -> str:
    return f"{100 * lo:.0f}–{100 * hi:.0f} %"


def per_ten(x: float) -> int:
    return int(math.floor(10 * x + 0.5))


def consequence(m: ModeMetrics | None) -> str:
    """One German line: what the mode did on the test data (computed, never hardcoded)."""
    if m is None:
        return "Keine Messwerte vorhanden."
    far = f"~{pct(m.far.value)} Fehlalarme ({m.far.k} von {m.far.n} harmlosen Anrufen markiert)"
    miss = f"{per_ten(m.miss)} von 10 auffälligen Fällen verpasst ({m.recall.n - m.recall.k} von {m.recall.n})"
    joiner = ", aber " if m.far.value <= 0.05 and m.miss >= 0.2 else ", "
    out = f"Auf den Testdaten: {far}{joiner}{miss}"
    if m.review_k is not None and m.review_n:
        out += f"; Grenzfälle zur Prüfung erkannt: {m.review_k} von {m.review_n}"
    return out + "."


def consequence_short(m: ModeMetrics | None) -> str:
    """Sidebar caption: «Testdaten: ~0 % Fehlalarme, aber 3 von 10 Fällen verpasst»."""
    if m is None:
        return "keine Messwerte"
    joiner = ", aber " if m.far.value <= 0.05 and m.miss >= 0.2 else ", "
    out = f"Testdaten: ~{pct(m.far.value)} Fehlalarme{joiner}{per_ten(m.miss)} von 10 Fällen verpasst"
    if m.n_review is not None:
        out += f"; {m.n_review} von {m.n_calls} zur Prüfung"
    return out


def uncertainty_note(m: ModeMetrics | None) -> str:
    if m is None:
        return ""
    miss_lo, miss_hi = 1 - m.recall.hi, 1 - m.recall.lo
    return (f"n = {m.n_calls}, Unsicherheit gross: Fehlalarme {pct_range(m.far.lo, m.far.hi)}, "
            f"verpasst {pct_range(miss_lo, miss_hi)} (95 %-Intervalle)")


def workload_note(m: ModeMetrics | None) -> str:
    if m is None or m.n_review is None or m.n_alarm is None:
        return ""
    return f"{m.n_alarm} Alarme + {m.n_review} Prüfungen von {m.n_calls} Anrufen"


def mode_threshold(mode: Mode, metrics: ModeMetrics | None, profile_threshold: float) -> float:
    if isinstance(mode.threshold, (int, float)):
        return float(mode.threshold)
    if mode.threshold == "suggested" and metrics is not None and metrics.suggested_threshold is not None:
        return float(metrics.suggested_threshold)
    return float(profile_threshold)


# --------------------------------------------------------------------------------------------
# availability on the shown calls
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Availability:
    ok: bool
    reason: str = ""  # why not (German), or a note when only some calls have reader B
    n_both: int = 0
    n_calls: int = 0


def fusion_type(cfg: AppConfig) -> str:
    return str((cfg.fusion or {}).get("type", "weighted"))


def readers_of(spec: ModeSpec, cfg: AppConfig) -> tuple[str, str]:
    if fusion_type(cfg) == "two_readers" and len((cfg.fusion or {}).get("readers") or ()) == 2:
        r = cfg.fusion["readers"]
        return str(r[0]), str(r[1])
    return spec.readers


def reader_labels_of(spec: ModeSpec, cfg: AppConfig) -> tuple[str, str]:
    if fusion_type(cfg) == "two_readers" and len((cfg.fusion or {}).get("reader_labels") or ()) == 2:
        r = cfg.fusion["reader_labels"]
        return str(r[0]), str(r[1])
    return spec.reader_labels


def has_both(result: CallResult, readers: tuple[str, str]) -> bool:
    return all(ag.usable(result.checks.get(r)) is not None for r in readers)


def availability(spec: ModeSpec, cfg: AppConfig, results: Mapping[str, CallResult],
                 can_decide: bool = True) -> dict[str, Availability]:
    readers = readers_of(spec, cfg)
    n = len(results)
    n_both = sum(1 for r in results.values() if has_both(r, readers))
    ftype = fusion_type(cfg)
    second = spec.second_reader
    out = {}
    for m in spec.modes:
        if not m.needs_second:
            out[m.id] = Availability(True, "", n_both, n)
        elif not can_decide:
            out[m.id] = Availability(False, "Neu-Bewertung nicht möglich (Fusion nicht geladen).", n_both, n)
        elif ftype not in CAN_SWITCH:
            out[m.id] = Availability(False, f"Die Fusion «{ftype}» dieses Profils kennt keine Zweitmeinung.", n_both, n)
        elif n == 0:
            out[m.id] = Availability(False, "Noch keine Anrufe geladen.", 0, 0)
        elif n_both == 0:
            out[m.id] = Availability(False, f"Zweitmeinung braucht {second}-Ergebnisse; {second}-Dienst nicht aktiv "
                                             f"(keiner der {n} Anrufe hat welche).", 0, n)
        elif n_both < n:
            out[m.id] = Availability(True, f"{n - n_both} von {n} Anrufen ohne {second}-Ergebnis: dort gilt "
                                           f"«{spec.default_mode.label}».", n_both, n)
        else:
            out[m.id] = Availability(True, "", n_both, n)
    return out


# --------------------------------------------------------------------------------------------
# deciding under a mode
# --------------------------------------------------------------------------------------------


class ModeEngine:
    """The UI engine with the fusion swapped for the mode's two_readers rule. Everything else (pipeline,
    ctx, families, error) is the base engine's, so pages that re-run checks or process calls are unaffected."""

    def __init__(self, base: Any, mode: Mode, fusion: Any, fallback: Any, spec: ModeSpec,
                 readers: tuple[str, str]):
        self.base = base
        self.mode = mode
        self.mode_fusion = fusion
        self.fallback = fallback  # engine-like for calls without reader B (the default mode)
        self.spec = spec
        self.readers = readers
        self.key = stable_hash({"base": base.key, "mode": mode.id, "rule": mode.rule, "readers": list(readers)})

    def __getattr__(self, name: str) -> Any:  # pipeline, ctx, cfg, error, families, ...
        if name.startswith("__") or name == "base":
            raise AttributeError(name)
        return getattr(self.base, name)

    @property
    def can_decide(self) -> bool:
        return self.mode_fusion is not None

    def _weights(self) -> dict[str, float]:
        pipe = getattr(self.base, "pipeline", None)
        if pipe is not None:
            return {c.name: c.weight for c in pipe.checks}
        from callguard.ui.backend import check_weights

        return check_weights(self.base.cfg)

    def decide(self, result: CallResult, overrides: dict[str, Any] | None = None,
               families: list[Family] | None = None) -> Decision:
        if self.mode.needs_second and not has_both(result, self.readers):
            d = self.fallback.decide(result, overrides, families)
            d.reasons.insert(0, f"Prüfmodus «{self.mode.label}»: keine {self.spec.second_reader}-Ergebnisse für "
                                f"diesen Anruf, entschieden wie «{self.spec.default_mode.label}».")
            return d
        fams = families if families is not None else self.base.families()
        o = dict(overrides or {})
        o.setdefault("weights", self._weights())
        views = result.views or None
        if views:
            return self.mode_fusion.decide(result.transcript, result.checks, fams, o, views=views)
        return self.mode_fusion.decide(result.transcript, result.checks, fams, o)


_ENGINES: dict[str, Any] = {}


def _make_fusion(base: Any, rule: str, readers: tuple[str, str], labels: tuple[str, str]) -> Any:
    from callguard import registry

    f = dict(base.cfg.fusion or {})
    f.update(type="two_readers", rule=rule, readers=list(readers), reader_labels=list(labels))
    return registry.create("fusion", f, ctx=base.ctx)


def engine_for(base: Any, spec: ModeSpec, mode_id: str | None, second_present: bool = True) -> Any:
    """The engine the UI decides with under ``mode_id``. The base engine itself when the profile's own
    fusion already is the mode (two_readers with the same rule, or a weighted fusion + rule a on calls that
    have no second reader: a weighted fusion would count reader B as one more check) or when the profile's
    fusion cannot be switched; raises when the mode's fusion cannot be built."""
    mode = spec.get(mode_id)
    cfg = base.cfg
    ftype = fusion_type(cfg)
    if not getattr(base, "can_decide", False) or ftype not in CAN_SWITCH:
        return base
    if ftype == "weighted" and mode.rule == "a" and not second_present:
        return base
    if ftype == "two_readers" and str(cfg.fusion.get("rule", "labels")) == mode.rule:
        return base
    readers = readers_of(spec, cfg)
    key = stable_hash([base.key, mode.id, mode.rule, list(readers)])
    hit = _ENGINES.get(key)
    if hit is not None and hit.base is base:
        return hit
    # calls without reader B: decided like the default mode (for them rule a == the profile's own fusion)
    fallback = base if mode.id == spec.default else engine_for(base, spec, spec.default, second_present)
    eng = ModeEngine(base, mode, _make_fusion(base, mode.rule, readers, reader_labels_of(spec, cfg)), fallback,
                     spec, readers)
    if len(_ENGINES) > 32:
        _ENGINES.clear()
    _ENGINES[key] = eng
    return eng


# --------------------------------------------------------------------------------------------
# persistence (per profile / source)
# --------------------------------------------------------------------------------------------


def prefs_path(runs_root: str | Path) -> Path:
    return Path(runs_root) / PREFS_FILE


def load_choice(runs_root: str | Path, key: str) -> str | None:
    p = prefs_path(runs_root)
    try:
        data = json.loads(p.read_text()) if p.is_file() else {}
    except Exception as e:
        log.warning("Prüfmodi: unreadable %s: %s", p, e)
        return None
    entry = (data.get("pruefmodus") or {}).get(key) or {}
    return entry.get("mode")


def save_choice(runs_root: str | Path, key: str, mode_id: str, user: str | None = None) -> dict[str, Any]:
    from callguard import audit

    p = prefs_path(runs_root)
    try:
        data = json.loads(p.read_text()) if p.is_file() else {}
    except Exception:
        data = {}
    entry = {"mode": mode_id, "by": user or audit.current_user(), "at": audit.now_iso()}
    data.setdefault("pruefmodus", {})[key] = entry
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    tmp.replace(p)
    return entry


@dataclass
class ModeState:
    """What the UI holds about modes for one script run."""
    spec: ModeSpec
    current: str
    metrics: dict[str, ModeMetrics] = field(default_factory=dict)
    avail: dict[str, Availability] = field(default_factory=dict)

    @property
    def mode(self) -> Mode:
        return self.spec.get(self.current)

    @property
    def is_default(self) -> bool:
        return self.current == self.spec.default

    @property
    def second_present(self) -> bool:
        """Any shown call has the second reader's results."""
        return any(a.n_both > 0 for a in self.avail.values())

    def engine(self, base: Any, mode_id: str | None = None) -> Any:
        return engine_for(base, self.spec, mode_id or self.current, self.second_present)


def _main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m callguard.ui.modes")
    ap.add_argument("cmd", choices=["snapshot", "show"])
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    a = ap.parse_args(argv)
    spec = load_spec()
    if a.cmd == "snapshot":
        print(write_snapshot(spec, a.runs))
    for mid, m in load_metrics(spec, a.runs).items():
        print(f"{mid}: {consequence(m)} [{uncertainty_note(m)}] {workload_note(m)} thr={m.suggested_threshold}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
