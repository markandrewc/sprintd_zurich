"""Shared state + frames for the "Feedback & Tuning" and "Lernen" pages: which feedback store is shown
(real officers vs simulated demo), the label set, the memoized threshold re-fit, proposal rows and the
German texts. Streamlit is only used by :func:`store_picker`; the rest is pure and unit-tested.

Charts follow the dataviz method: no categorical colour is needed here. Agreement is a KPI row of stat
tiles, the confusion is a table (counts in the cells, status words in the headers), correction rates and
readiness are single-hue meters (the neutral ``render.SCORE_BAR`` slate / Streamlit's progress bar) that
always print the number, so colour is never the only cue.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from callguard import feedback as fb
from callguard.learning import hygiene as hy
from callguard.learning import insights, recalibrate, records
from callguard.learning import proposals as pr

STORE_KEY = "cg_learn_store"
STORE_DE = {"real": "Echte Rückmeldungen", "demo": "Demo-Feedback (simuliert aus Sollbewertung)"}
_MEMO: dict[Any, Any] = {}

PITCH_DE = ("Die Feedbacks der Prüferinnen werden zu Trainingsdaten — aber ein neues Modell geht erst live, "
            "wenn es auf ungesehenen, geprüften Anrufen nachweislich besser ist.")
SHADOW_DE = (
    "**Schatten-Test vor jeder Modell-Aktivierung.** Ein nachtrainiertes Modell (Faktenleser Kev/Qwen oder "
    "Spracherkennung) läuft zuerst im Schatten: es bewertet die Anrufe des Schatten-Testsets mit, entscheidet "
    "aber nichts. Diese Anrufe hat es nie gesehen (Aufteilung pro Gespräch, saubere und verrauschte Aufnahme "
    "immer auf derselben Seite; Fall-Anrufe nie im Training). Live geht es nur, wenn es dort gegenüber dem "
    "aktuellen Modell nachweislich besser ist (gepaartes Bootstrap-Konfidenzintervall der Differenz schliesst "
    "0 aus) **und** nicht mehr Fehlalarme erzeugt — und auch dann erst nach Freigabe durch eine zweite Person, "
    "mit Rückweg auf das alte Modell.")


def store_picker(st: Any, runs_dir: Path, key: str = STORE_KEY) -> str:
    n_real = len(fb.load(runs_dir, "real"))
    n_demo = len(fb.load(runs_dir, "demo"))
    st.session_state.setdefault(key, "real" if n_real or not n_demo else "demo")
    store = st.segmented_control(
        "Quelle der Labels", list(STORE_DE), key=key, format_func=lambda s: f"{STORE_DE[s]} ({n_real if s == 'real' else n_demo})",
        help="Demo-Feedback ist aus der Sollbewertung der Dev-Anrufe simuliert, liegt in einer eigenen Datei und "
             "wird nie zum Training verwendet.") or "real"
    if store == "demo":
        st.warning("**Demo-Feedback (simuliert aus Sollbewertung)** — keine echten Prüfer-Urteile. Nur zur "
                   "Vorführung; nie Trainingsdaten.", icon=":material/science:")
    return store


def _stamp(p: Path) -> tuple[float, int] | None:
    try:
        s = p.stat()
        return (s.st_mtime, s.st_size)
    except OSError:
        return None


def labels(runs_dir: Path, results: Mapping[str, Any], signature: str, store: str) -> records.LabelSet:
    key = ("labels", str(runs_dir), signature, store, _stamp(fb.feedback_path(runs_dir, store)),
           _stamp(Path(runs_dir) / "audit.jsonl"))
    if key not in _MEMO:
        if len(_MEMO) > 32:
            _MEMO.clear()
        _MEMO[key] = records.collect(runs_dir, results, hy.splits_or_none(), store)
    return _MEMO[key]


def refit(pipeline: Any, results: Mapping[str, Any], ls: records.LabelSet, signature: str,
          overrides: Mapping[str, Any]) -> dict[str, Any]:
    lab = {c: x.label for c, x in ls.calls.items()}
    key = ("refit", signature, ls.store, tuple(sorted(lab.items())),
           tuple(sorted((k, str(v)) for k, v in overrides.items())))
    if key not in _MEMO:
        _MEMO[key] = recalibrate.propose_threshold(pipeline, list(results.values()), lab, hy.splits_or_none(),
                                                   overrides=dict(overrides))
    return _MEMO[key]


def effect_rows(effect: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for k, e in effect.items():
        rows.append({"Kennzahl": recalibrate.METRIC_DE.get(k, k), "aktuell": e.get("a"), "neu (Kreuzvalidierung)": e.get("b"),
                     "Differenz": e.get("diff"), "95%-KI": _ci(e.get("lo"), e.get("hi")),
                     "Ergebnis": "echt" if e.get("real") else "Rauschen"})
    return rows


def _ci(lo: float | None, hi: float | None) -> str:
    return "–" if lo is None or hi is None else f"[{lo:+.3f}, {hi:+.3f}]"


def confusion_rows(cm: Mapping[str, Any]) -> list[dict[str, Any]]:
    m = cm["matrix"]
    return [{"Prüfer:in sagt": insights.LABEL_DE[o], **{f"System: {insights.LABEL_DE[s]}": m[o][s] for s in insights.LABELS}}
            for o in insights.LABELS]


def proposal_rows(props: list[pr.Proposal]) -> list[dict[str, Any]]:
    return [{"ID": p.id, "Profil": p.profile, "Änderung": ", ".join(f"{k} = {v:.2f}" for k, v in p.change.items()),
             "Status": pr.STATUS_DE.get(p.status, p.status), "Vorgeschlagen von": p.proposed_by,
             "Genehmigt von": p.approved_by or "–", "Labels": "Demo" if p.label_source == "demo" else "echt",
             "Zeit": p.proposed_at} for p in props]


def evidence_of(rec: Mapping[str, Any]) -> dict[str, Any]:
    return {k: rec.get(k) for k in ("n_calls", "n_units", "current_threshold", "proposed_threshold", "verdict",
                                    "effect", "cv", "label_counts")}


def regelwerk_page(pages: Mapping[str, Any]) -> Any | None:
    """The rule-book page if the app has one (another team's page; matched by key)."""
    for k in ("regelwerk", "rules", "policy", "policy_table"):
        if k in pages:
            return pages[k]
    return next((v for k, v in pages.items() if "regel" in k.lower() or "policy" in k.lower()), None)
