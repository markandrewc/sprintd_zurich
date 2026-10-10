"""Regeln & Einstellungen: everything the officer changes, in one place and top-down.

(a) Wie streng? Alarmschwelle + Prüfmodus with the measured consequences and the workload sentence.
(b) Was wird gesucht? Prüfarten on/off, then per Prüfart its questions to the AI and directly below the rules
    built from them; «Neue Regel in eigenen Worten» and «Neue Prüfart».
(c) Stichwörter with «Treffer vorher → nachher».
(d) Änderungen prüfen & freigeben: preview, draft versions, four-eyes approval, rollback.

(b) and (d) are the officer UI's Regelwerk page (``ui/views/rules.py``) run in its embedded layout: same
working copy, same version store, same audit events; only the order differs.
"""

from __future__ import annotations

import runpy
from pathlib import Path

import pandas as pd
import streamlit as st

from callguard import audit
from callguard.demo import controls as ctl
from callguard.demo import keywords as kw
from callguard.demo import state as ds
from callguard.families import load_families
from callguard.types import LABELS
from callguard.ui import backend as be
from callguard.ui.backend import label_counts, short_label
from callguard.ui.session import current_app, reload_everything

RULES = Path(__file__).resolve().parents[2] / "ui" / "views" / "rules.py"
LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
EXPLAINER = ("**So entscheidet callguard:** 1) Die KI beantwortet pro Prüfart kleine Ja/Nein-Fragen zum Gespräch "
             "(mit Sicherheit). 2) Ihre Regeln verknüpfen diese Antworten zu Alarm / Prüfen / Kein Alarm. Regeln ändern "
             "kostet keine KI-Zeit; neue oder umformulierte Fragen muss die KI neu beantworten.")

app = current_app()
st.title("Regeln & Einstellungen")
for msg in st.session_state.pop("dm_set_messages", []):
    st.toast(msg, icon=":material/check_circle:")
st.info(EXPLAINER, icon=":material/lightbulb:")

rw = runpy.run_path(str(RULES), init_globals={"RW_LAYOUT": "embedded"})  # loads state, draws nothing yet

# -- (a) how strict -------------------------------------------------------------------------------

st.header("Wie streng?", anchor="wie-streng", divider="gray")
counts, base = label_counts(app.decided), label_counts(app.baseline)
c1, c2 = st.columns([1, 1], gap="large")
with c1:
    ctl.threshold_slider(app)
    st.markdown(" · ".join(f"{LABEL_DE[lbl]} **{counts[lbl]}**"
                           + (f" ({counts[lbl] - base[lbl]:+d})" if counts[lbl] != base[lbl] else "")
                           for lbl in LABELS) + f" von {len(app.decided)} Anrufen")
    sentence = ctl.workload_sentence(app)
    if sentence:
        st.markdown(f":material/groups: {sentence}")
        st.caption(ctl.WORKLOAD_NOTE)
with c2:
    ctl.mode_control(app, details=True)

# -- (b) what is looked for -----------------------------------------------------------------------

st.header("Was wird gesucht?", anchor="was-wird-gesucht", divider="gray")
st.subheader("Prüfarten", anchor=False)
st.caption("Eine Prüfart ausschalten: diese Art von Fehlverhalten wird nicht mehr gesucht. Wie jede Änderung hier gilt "
           "das erst nach Vorschau und Freigabe durch eine zweite Person (unten).")
rw["family_switches"]()
rw["_preview_line"]()

st.subheader("Fragen und Regeln je Prüfart", anchor=False)
fam_ids = list((rw["doc"]().get("families") or {}).keys())
names = rw["fam_names"]
if fam_ids:
    for tab, fam in zip(st.tabs([names.get(f, f) + (" (neu)" if f in rw["new_family_ids"] else "") for f in fam_ids]),
                        fam_ids):
        with tab:
            rw["family_questions_rules"](fam)
with st.expander("Neue Regel in eigenen Worten", icon=":material/auto_awesome:"):
    rw["ai_tab"]()
with st.expander("Neue Prüfart", icon=":material/category:"):
    rw["family_wizard"]()

# -- (c) keywords -----------------------------------------------------------------------------------


def keywords_section() -> None:
    kw_path, crit_path = app.ctx.path("keywords"), app.ctx.path("criteria")
    try:
        families = sorted(load_families(kw_path, crit_path), key=lambda f: not f.can_alarm)
    except Exception as e:
        st.error(f"Die Stichwortliste ist nicht lesbar: {type(e).__name__}: {e}", icon=":material/error:")
        return
    if not families:
        return
    check = kw.keyword_check(app.engine)
    by = {f.id: f for f in families}
    fid = st.segmented_control("Art von Fehlverhalten", list(by), format_func=lambda k: short_label(by[k].label),
                               default=families[0].id, required=True, key="dm_kw_family")
    fam = by[fid or families[0].id]
    version = st.session_state.setdefault("dm_kw_version", 0)
    st.caption("Ein Stichwort pro Zeile, Formen durch Komma trennen. Eine neue Zeile unten anfügen; lieber ausschalten "
               "als löschen. «Harmlos, wenn …» erklärt Treffer, die kein Verstoss sind. Speichern gilt sofort (mit "
               "Sicherungskopie und Audit-Log).")
    df = pd.DataFrame(be.keyword_rows(fam), columns=list(be.KEYWORD_COLUMNS))
    edited = st.data_editor(
        df, key=f"dm_kw_{fam.id}_{version}", num_rows="dynamic", hide_index=True, width="stretch",
        column_order=["enabled", "label", "de", "gsw", "harmless"],
        column_config={
            "enabled": st.column_config.CheckboxColumn("An", width="small", default=True),
            "label": st.column_config.TextColumn("Bezeichnung", width="medium"),
            "de": st.column_config.TextColumn("Hochdeutsch", width="large"),
            "gsw": st.column_config.TextColumn("Schweizerdeutsch", width="large"),
            "harmless": st.column_config.TextColumn("Harmlos, wenn …", width="large"),
        })
    new_keywords, warnings = be.rows_to_keywords(edited.to_dict("records"), be.all_keyword_ids(kw_path))
    old_keywords = list(fam.keywords)
    dirty = [k.model_dump() for k in new_keywords] != [k.model_dump() for k in old_keywords]
    for w in warnings:
        st.caption(f":material/warning: {w}")
    if check is None:
        st.info("In diesem Profil ist keine Stichwort-Prüfung eingeschaltet; die Liste wirkt erst, wenn sie läuft.",
                icon=":material/info:")
    elif app.loaded.results:
        with st.spinner("Wirkung auf alle Anrufe wird berechnet …"):
            eff = kw.keyword_effect(app.engine, app.loaded.results, app.decided, app.all_families,
                                    app.settings.families_on, app.settings.overrides(), fam.id,
                                    new_keywords if dirty else None)
        with st.container(border=True):
            st.markdown("**Wirkung auf die verarbeiteten Anrufe** · vorher → nachher"
                        + ("" if dirty else " · *noch keine Änderung*"))
            m = st.columns(5)
            m[0].metric(f"Treffer «{short_label(fam.label)}»", eff.family_hits_after,
                        delta=f"{eff.family_hits_after - eff.family_hits_before:+d}" if dirty else None,
                        delta_color="off", help=f"vorher {eff.family_hits_before}")
            m[1].metric("Anrufe mit Treffer", eff.calls_after,
                        delta=f"{eff.calls_after - eff.calls_before:+d}" if dirty else None, delta_color="off",
                        help=f"vorher {eff.calls_before}")
            for col, lbl in zip(m[2:], LABELS):
                d = eff.labels_after[lbl] - eff.labels_before[lbl]
                col.metric(LABEL_DE[lbl], eff.labels_after[lbl], delta=f"{d:+d}" if dirty and d else None,
                           delta_color="off", help=f"vorher {eff.labels_before[lbl]}")
            st.caption(f"Stichwort-Treffer insgesamt {eff.hits_before} → {eff.hits_after}. Stichwörter sind ein Hinweis "
                       "mit kleinem Gewicht; entscheidend sind die Antworten auf die Fragen und Ihre Regeln. Deshalb "
                       "ändern sich Treffer oft, Entscheide selten.")
            if eff.changed:
                st.markdown("Anrufe, deren Entscheid sich ändern würde: " + ", ".join(
                    f"**{c}** ({LABEL_DE[a]} → {LABEL_DE[b]})" for c, a, b in eff.changed[:8]))
    c1, c2 = st.columns(2)
    if c1.button("Stichwörter speichern und anwenden", type="primary", icon=":material/save:",
                 disabled=not dirty or app.engine.pipeline is None, width="stretch"):
        try:
            be.backup_file(kw_path, app.runs_dir / "_backups")
            be.save_family_keywords(kw_path, crit_path, fam.id, new_keywords)
            audit.log_event(app.runs_dir, "keywords_save", user=st.session_state.get(ds.NAME_KEY) or None,
                            family=fam.id, before=len(old_keywords), after=len(new_keywords), via="demo")
            with st.spinner("Stichwort-Prüfung läuft auf allen Anrufen neu …"):
                rep = be.rerun_checks(app.engine.pipeline, app.loaded, include_llm=False)
        except Exception as e:
            st.error(f"Speichern fehlgeschlagen: {type(e).__name__}: {e}", icon=":material/error:")
        else:
            reload_everything()
            st.session_state["dm_kw_version"] = version + 1
            st.session_state.setdefault("dm_set_messages", []).append(
                f"Stichwörter «{short_label(fam.label)}» gespeichert, {rep.calls} Anrufe neu bewertet.")
            st.rerun()
    if c2.button("Änderungen verwerfen", icon=":material/undo:", disabled=not dirty, width="stretch",
                 key="dm_kw_discard"):
        st.session_state["dm_kw_version"] = version + 1
        st.rerun()


st.header("Stichwörter", anchor="stichwoerter", divider="gray")
keywords_section()

# -- (d) governance ---------------------------------------------------------------------------------

st.header("Änderungen prüfen & freigeben", anchor="freigeben", divider="gray")
st.caption("Alles, was Sie oben an Prüfarten, Fragen und Regeln ändern, landet zuerst in einer Arbeitskopie. Hier sehen "
           "Sie, welche Anrufe sich dadurch ändern würden, speichern einen Entwurf, und eine zweite Person gibt ihn frei. "
           "Erst dann gilt er.")
rw["status_row"]()
n_changes, n_drafts = len(rw["changes"]), rw["n_drafts"]
tab_prev, tab_ver = st.tabs([f"Vorschau & Speichern{f' ({n_changes})' if n_changes else ''}",
                             f"Versionen & Freigabe{f' ({n_drafts})' if n_drafts else ''}"])
with tab_prev:
    rw["preview_tab"]()
with tab_ver:
    rw["versions_tab"]()
