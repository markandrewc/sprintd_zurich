"""Einstellungen: what the officer changes without code. The keyword list with its effect shown before saving
(«Treffer vorher → nachher»), the Prüfarten on / off for this session, and the way into the Regelwerk."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard import audit
from callguard.demo import keywords as kw
from callguard.demo import state as ds
from callguard.families import load_families
from callguard.types import LABELS
from callguard.ui import backend as be
from callguard.ui.backend import label_counts, short_label
from callguard.ui.session import current_app, reload_everything

app = current_app()
LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}

st.title("Einstellungen")
st.caption("Was callguard sucht und wie streng es urteilt, ändern Sie hier ohne Code. Jede Änderung zeigt ihre "
           "Wirkung auf die verarbeiteten Anrufe, bevor sie gilt.")

for msg in st.session_state.pop("dm_set_messages", []):
    st.toast(msg, icon=":material/check_circle:")

tab_kw, tab_fam, tab_rules = st.tabs(["Stichwortliste", "Prüfarten", "Regelwerk"])

# -- keyword list ------------------------------------------------------------------------------

with tab_kw:
    kw_path, crit_path = app.ctx.path("keywords"), app.ctx.path("criteria")
    try:
        families = sorted(load_families(kw_path, crit_path), key=lambda f: not f.can_alarm)
    except Exception as e:
        st.error(f"Die Stichwortliste ist nicht lesbar: {type(e).__name__}: {e}", icon=":material/error:")
        families = []
    check = kw.keyword_check(app.engine)
    if families:
        by = {f.id: f for f in families}
        fid = st.segmented_control("Art von Fehlverhalten", list(by), format_func=lambda k: short_label(by[k].label),
                                   default=families[0].id, required=True, key="dm_kw_family")
        fam = by[fid or families[0].id]
        version = st.session_state.setdefault("dm_kw_version", 0)
        st.caption("Ein Stichwort pro Zeile, Formen durch Komma trennen. Eine neue Zeile unten anfügen; lieber "
                   "ausschalten als löschen. «Harmlos, wenn …» erklärt Treffer, die kein Verstoss sind.")
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
            st.info("In diesem Profil ist keine Stichwort-Prüfung eingeschaltet; die Liste wirkt erst, wenn sie "
                    "läuft.", icon=":material/info:")
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
                st.caption(f"Stichwort-Treffer insgesamt {eff.hits_before} → {eff.hits_after}. Stichwörter sind "
                           "ein Hinweis mit kleinem Gewicht; entscheidend sind die Fakten des Gesprächs (Regelwerk). "
                           "Deshalb ändern sich Treffer oft, Entscheide selten.")
                if eff.changed:
                    st.markdown("Anrufe, deren Entscheid sich ändern würde: " + ", ".join(
                        f"**{c}** ({LABEL_DE[a]} → {LABEL_DE[b]})" for c, a, b in eff.changed[:8]))

        c1, c2 = st.columns([1, 1])
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
        if c2.button("Änderungen verwerfen", icon=":material/undo:", disabled=not dirty, width="stretch"):
            st.session_state["dm_kw_version"] = version + 1
            st.rerun()

# -- Prüfarten ---------------------------------------------------------------------------------

with tab_fam:
    st.caption("Eine Prüfart ausschalten: sie zählt in keinem Entscheid mehr. Gilt sofort für alle Anrufe dieser "
               "Sitzung; dauerhaft ändern (mit Vier-Augen-Freigabe) im Regelwerk.")
    counts, base = label_counts(app.decided), label_counts(app.baseline)
    cols = st.columns(2, gap="large")
    for i, f in enumerate(sorted(app.all_families, key=lambda f: not f.can_alarm)):
        with cols[i % 2]:
            st.toggle(short_label(f.label), key=ds.family_key(f.id), persist_state="session",
                      help=None if f.can_alarm else "Nur Hinweis: löst nie selbst Alarm aus.")
    st.markdown(" · ".join(f"{LABEL_DE[lbl]} **{counts[lbl]}**" + (f" ({counts[lbl] - base[lbl]:+d})"
                                                                    if counts[lbl] != base[lbl] else "")
                           for lbl in LABELS))

# -- Regelwerk -----------------------------------------------------------------------------------

with tab_rules:
    st.markdown("Im **Regelwerk** steht in Klartext, wann ein Gespräch ein Alarm, ein Prüffall oder unbedenklich "
                "ist: einfache Ja/Nein-Fragen an das Sprachmodell (Fakten) und Regeln darüber, mit "
                "Rechtsgrundlage und Meldeweg.")
    st.markdown("- Regeln lesen und ändern ohne Code (Bausteine statt Syntax)\n"
                "- Neue Regel in eigenen Worten beschreiben: die KI entwirft, Sie prüfen\n"
                "- Vorschau: welche Anrufe sich ändern würden, bevor etwas gilt\n"
                "- Vier-Augen-Freigabe, Versionen und Rücknahme, alles im Audit-Log")
    st.page_link(app.pages["rules"], label="Regelwerk öffnen", icon=":material/rule:")
