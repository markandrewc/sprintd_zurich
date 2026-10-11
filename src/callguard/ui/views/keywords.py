"""Stichwörter & Kriterien: the officer edits what the system looks for, without code.

Keywords (``keywords.json``) feed the cheap keyword check: an edit plus "Re-run cheap checks" changes the
hit counts within seconds. Criteria (``criteria.yaml``) are read by the LLM checks; changing them
invalidates cached LLM results, so those rerun only on request (slow on CPU).
"""

from __future__ import annotations

import time
from dataclasses import asdict

import pandas as pd
import streamlit as st

from callguard.families import load_families
from callguard.types import LABELS, Segment, Transcript
from callguard.ui import render as ui
from callguard.ui.backend import (
    KEYWORD_COLUMNS,
    LABEL_TEXT,
    all_keyword_ids,
    backup_file,
    decide_all,
    keyword_rows,
    label_counts,
    load_results,
    rerun_checks,
    rows_to_keywords,
    save_criteria,
    save_family_keywords,
    short_label,
)
from callguard.ui.session import current_app

app = current_app()
kw_path, crit_path = app.ctx.path("keywords"), app.ctx.path("criteria")
backup_dir = app.runs_dir / "_backups"
pipeline = app.engine.pipeline

st.title("Stichwörter & Kriterien")
st.caption(f"Stichwörter werden im Transkript gesucht (schnell, sofort). Kriterien sagen den LLM-Prüfungen, wann "
           f"eine Art von Fehlverhalten ein Alarm ist. Dateien: `{kw_path.name}`, `{crit_path.name}`; jedes "
           f"Speichern legt eine Sicherung in `{backup_dir}` an.")
if app.read_only:
    st.info("Angezeigt wird eine Experiment-Variante (nur lesen). Änderungen an Stichwörtern und Kriterien gelten "
            "für die Profil-Läufe; zum Anwenden in der Seitenleiste einen Profil-Lauf als Quelle wählen.",
            icon=":material/lock:")

for msg in st.session_state.pop("cg_kw_messages", []):
    st.toast(msg, icon=":material/check_circle:")

try:
    families = sorted(load_families(kw_path, crit_path), key=lambda f: not f.can_alarm)  # misconduct first
except Exception as e:
    st.error(f"Stichwortliste oder Kriterien unlesbar: {type(e).__name__}: {e}")
    st.stop()

version = st.session_state.setdefault("cg_kw_version", 0)


def _saved(msg: str) -> None:
    st.session_state["cg_kw_version"] = version + 1  # fresh editors showing the file as saved
    st.session_state.setdefault("cg_kw_messages", []).append(msg)
    st.session_state["cg_kw_dirty"] = True
    st.rerun()


KW_CONFIG = {
    "enabled": st.column_config.CheckboxColumn("An", width="small", default=True,
                                               help="Stichwort ausschalten, ohne es zu löschen."),
    "id": st.column_config.TextColumn("Id", width="small", help="Für ein neues Stichwort leer lassen."),
    "label": st.column_config.TextColumn("Bezeichnung", help="Kurzer Name, erscheint in den Begründungen."),
    "de": st.column_config.TextColumn("Hochdeutsch", width="large",
                                      help="Durch Komma getrennt. Die Spracherkennung schreibt meist Hochdeutsch."),
    "gsw": st.column_config.TextColumn("Schweizerdeutsch", width="large", help="Durch Komma getrennt."),
    "en": st.column_config.TextColumn("Englisch", width="large",
                                      help="Durch Komma getrennt. Nur auf englischen Transkript-Ansichten gesucht."),
    "harmless": st.column_config.TextColumn("Harmlos, wenn …", width="large",
                                            help="Wann ein Treffer NICHT verdächtig ist; wird auch den LLM-Prüfungen "
                                                 "gezeigt und unter «Warum kein Alarm?» angezeigt."),
    "case_sensitive": st.column_config.CheckboxColumn("Aa", width="small", default=False,
                                                      help="Gross-/Kleinschreibung genau beachten (z.B. PIN, TAN)."),
}

tabs = st.tabs([short_label(f.label) + ("" if f.enabled else " (aus)") for f in families])
for tab, fam in zip(tabs, families):
    with tab:
        st.markdown(f"**{ui.esc(fam.label)}** · `{fam.id}`"
                    + ("" if fam.can_alarm else " · :gray-badge[nur Hinweis, löst nie Alarm aus]")
                    + ("" if fam.enabled else " · :red-badge[ausgeschaltet]"))

        st.markdown("##### Stichwörter")
        df = pd.DataFrame(keyword_rows(fam), columns=list(KEYWORD_COLUMNS))
        edited = st.data_editor(df, key=f"cg_kw_{fam.id}_{version}", num_rows="dynamic", hide_index=True,
                                width="stretch", column_config=KW_CONFIG)
        st.caption("Neues Stichwort in der leeren letzten Zeile; Formen durch Komma trennen. Lieber ausschalten "
                   "als löschen.")
        if st.button("Stichwörter speichern", key=f"cg_kw_save_{fam.id}", icon=":material/save:", type="primary",
                     disabled=app.read_only):
            keywords, warnings = rows_to_keywords(edited.to_dict("records"), all_keyword_ids(kw_path))
            for w in warnings:
                st.warning(w)
            try:
                backup_file(kw_path, backup_dir)
                save_family_keywords(kw_path, crit_path, fam.id, keywords)
            except Exception as e:
                st.error(f"Speichern fehlgeschlagen: {type(e).__name__}: {e}")
            else:
                _saved(f"Stichwörter für «{short_label(fam.label)}» gespeichert ({len(keywords)}).")

        st.markdown("##### Kriterien (lesen die LLM-Prüfungen)")
        with st.form(f"cg_crit_{fam.id}_{version}", border=True):
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            label = c1.text_input("Bezeichnung", value=fam.label)
            enabled = c2.toggle("Diese Art prüfen", value=fam.enabled)
            policy = st.text_area("Richtlinie: wann ist das ein Alarm?", value=fam.policy, height=110)
            a, b, c = st.columns(3)
            alarm_when = a.text_area("Alarm, wenn … (eine Regel pro Zeile)", "\n".join(fam.alarm_when), height=180)
            not_alarm = b.text_area("Kein Alarm, wenn … (eine pro Zeile)", "\n".join(fam.not_alarm_when), height=180)
            review_when = c.text_area("An Menschen übergeben, wenn … (eine pro Zeile)", "\n".join(fam.review_when),
                                      height=180)
            st.caption(":material/info: Speichern ändert die LLM-Prompts: zwischengespeicherte LLM-Ergebnisse dieses "
                       "Profils veralten, die LLM-Prüfungen laufen beim nächsten Verarbeiten neu (auf CPU langsam).")
            if st.form_submit_button("Kriterien speichern", icon=":material/save:", disabled=app.read_only):
                try:
                    backup_file(crit_path, backup_dir)
                    save_criteria(crit_path, fam.id, {"label": label, "policy": policy, "alarm_when": alarm_when,
                                                      "not_alarm_when": not_alarm, "review_when": review_when,
                                                      "enabled": enabled})
                except Exception as e:
                    st.error(f"Speichern fehlgeschlagen: {type(e).__name__}: {e}")
                else:
                    _saved(f"Kriterien für «{short_label(label)}» gespeichert.")

# -- try a sentence ----------------------------------------------------------------------------

kw_check = next((c for c in (pipeline.checks if pipeline else []) if c.plugin_type == "keywords"), None)
with st.expander("Einen Satz gegen die Stichwortliste testen", icon=":material/science:"):
    sample = st.text_input("Satz", placeholder="z.B. Ich möchte die Aktie vor der Meldung kaufen.",
                           key="cg_kw_try")
    if sample.strip():
        if kw_check is None:
            st.info("In diesem Profil ist keine Stichwort-Prüfung konfiguriert.")
        else:
            try:
                tr = Transcript(call_id="try", segments=[Segment(id="S001", start=0.0, end=5.0, text=sample)])
                res = kw_check.run(tr, app.engine.families())
            except Exception as e:
                st.warning(f"Die Stichwort-Prüfung ist fehlgeschlagen: {type(e).__name__}: {e}")
            else:
                if res.findings:
                    st.dataframe(pd.DataFrame([{
                        "Art": f.family, "Treffer": str(f.detail.get("matched_text", "")), "Score": f.score,
                        "Begründung": f.reason} for f in res.findings]), hide_index=True, width="stretch")
                else:
                    st.caption("Kein Stichwort gefunden.")

# -- apply to processed calls ------------------------------------------------------------------

st.divider()
st.subheader("Auf die verarbeiteten Anrufe anwenden")
st.caption("Lässt die Stichwort- und Muster-Prüfung auf allen verarbeiteten Anrufen neu laufen (Sekunden) und "
           "entscheidet mit den aktuellen Reglern neu. LLM-Prüfungen kommen aus dem Zwischenspeicher; haben sich "
           "ihre Kriterien geändert, behalten sie ihr altes Ergebnis (als «nicht neu gelaufen» markiert), ausser "
           "Sie schliessen sie unten ein.")
if st.session_state.get("cg_kw_dirty"):
    st.info("Stichwörter oder Kriterien wurden geändert. Neu anwenden, um die Wirkung auf die Anrufe zu sehen.",
            icon=":material/sync_problem:")
include_llm = st.checkbox("Auch LLM-Prüfungen mit geänderten Kriterien neu laufen lassen (langsam: rund eine "
                          "Minute pro Anruf und Prüfung auf CPU; nutzt den gemeinsamen LLM-Server)",
                          key="cg_kw_include_llm")
disabled = pipeline is None or not app.loaded.results or app.read_only
if pipeline is None:
    st.caption(f":material/block: Nicht verfügbar: {app.engine.error}")
elif not app.loaded.results:
    st.caption(":material/block: Noch keine verarbeiteten Anrufe.")
elif app.read_only:
    st.caption(":material/block: Experiment-Varianten werden nicht überschrieben.")


def _keyword_hits(results) -> int:
    return sum(len(cr.findings) for r in results.values() for cr in r.checks.values() if cr.type == "keywords")


if st.button("Stichwörter jetzt auf alle Anrufe anwenden", type="primary", icon=":material/sync:", disabled=disabled):
    before, hits_before = label_counts(app.decided), _keyword_hits(app.loaded.results)
    bar = st.progress(0.0, text="Prüfungen laufen neu …")

    def _progress(i: int, n: int, cid: str) -> None:
        bar.progress(min(1.0, i / max(n, 1)), text=f"{cid} ({i + 1}/{n})" if cid else "fertig")

    t0 = time.time()
    report = rerun_checks(pipeline, app.loaded, include_llm=include_llm, progress=_progress)
    loaded = load_results(app.runs_dir)
    after = label_counts(decide_all(app.engine, loaded, app.settings.overrides(), app.families))
    st.session_state["cg_kw_report"] = {
        "before": before, "after": after, "hits_before": hits_before, "hits_after": _keyword_hits(loaded.results),
        "report": asdict(report), "seconds": time.time() - t0, "threshold": app.settings.threshold,
    }
    st.session_state["cg_kw_dirty"] = False
    st.rerun()

rep = st.session_state.get("cg_kw_report")
if rep:
    r = rep["report"]
    st.markdown(f"**Letzter Durchlauf** · {r['calls']} Anrufe in {rep['seconds']:.1f} s · Schwelle "
                f"{rep['threshold']:.2f} · Veränderung gegenüber vorher:")
    cols = st.columns(4)
    for col, label in zip(cols, LABELS):
        col.metric(LABEL_TEXT[label], rep["after"][label], delta=f"{rep['after'][label] - rep['before'][label]:+d}",
                   delta_color="off", border=True)
    cols[3].metric("Stichwort-Treffer", rep["hits_after"], delta=f"{rep['hits_after'] - rep['hits_before']:+d}",
                   delta_color="off", border=True)
    st.caption(f"Prüfungsläufe: {r['rerun']} ausgeführt, {r['reused']} aus dem Zwischenspeicher, {r['kept']} "
               f"LLM-Ergebnisse behalten (Kriterien geändert, nicht neu gelaufen).")
    for f in r["failed"]:
        st.warning(f"Fehlgeschlagen: {f}")
