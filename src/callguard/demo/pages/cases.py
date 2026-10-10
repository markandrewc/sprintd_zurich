"""Fälle: the worklist. Alarms first, then reviews, then the rest; Alarmschwelle and Prüfmodus right above the
list, with the live counts, so changing either is one move with a visible effect."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard.demo import common as cm
from callguard.demo import controls as ctl
from callguard.demo import state as ds
from callguard.ui import render as ui
from callguard.ui.backend import label_counts
from callguard.ui.session import current_app

app = current_app()
s = app.settings

st.title("Fälle")
if not app.loaded.results:
    st.info("Noch keine verarbeiteten Anrufe. Einen Anruf auf **Anruf verarbeiten** hochladen.",
            icon=":material/inbox:")
else:
    judged = {i.call_id for i in ds.feedback_items(app)}
    counts, base = label_counts(app.decided), label_counts(app.baseline)
    open_flagged = sum(1 for cid, d in app.decided.items() if d.decision.label != "no_alert" and cid not in judged)
    ps = cm.policy_status(app)
    rule_note = ""
    if ps["version"] is not None and ps["same"]:
        rule_note = (f" · entschieden mit dem aktiven Regelwerk (Version {ps['version']})" if not ps["other"]
                     else f" · {ps['same']} mit dem aktiven Regelwerk (Version {ps['version']}) entschieden")
    st.caption(f"{len(app.loaded.results)} Anrufe · {open_flagged} davon brauchen noch einen Menschen "
               f"(Alarm oder Prüfen, noch nicht bearbeitet){rule_note}")
    if ps["other"]:
        st.warning(f"{len(ps['other'])} Anrufe wurden mit einer älteren Regelwerk-Version entschieden; ihre Zahlen "
                   "können vom aktiven Regelwerk abweichen (Regeln & Einstellungen → «Gespeicherte Anrufe neu "
                   "entscheiden» nach einer Freigabe).", icon=":material/history:")

    # 1. the four boxes (as on the internal Eingang page)
    help_text = {
        "alarm": "Score ab der Schwelle und die Prüfungen sind sich sicher genug.",
        "review": "Knapp unter der Schwelle oder die Prüfungen sind unsicher: ein Mensch muss zuhören.",
        "no_alert": "Nichts ausreichend Verdächtiges gefunden.",
    }
    boxes = st.columns(4)
    for col, lbl in zip(boxes, ("alarm", "review", "no_alert")):
        delta = counts[lbl] - base[lbl]
        col.metric(cm.cd.LABEL_DE[lbl], counts[lbl], delta=f"{delta:+d} zum Standard" if delta else None,
                   delta_color="off", delta_arrow="auto" if delta else "off", border=True, help=help_text[lbl])
    flagged, flagged_base = counts["alarm"] + counts["review"], base["alarm"] + base["review"]
    boxes[3].metric("Mensch nötig", flagged,
                    delta=f"{flagged - flagged_base:+d} zum Standard" if flagged != flagged_base else None,
                    delta_color="off", delta_arrow="auto" if flagged != flagged_base else "off", border=True,
                    help="Alarm + Prüfen: Anrufe, die jemand anhören muss.")

    # 2. the Alarmschwelle, full width
    ctl.threshold_slider(app)

    # 3. the score distribution: bars recolour as the threshold moves
    st.altair_chart(ui.score_bars(app.rows(), s.threshold, max(0.0, s.review_floor)), width="stretch")

    rows = cm.case_rows(app, judged)
    f1, f2, f3 = st.columns([3, 3, 4], vertical_alignment="bottom")
    work = f1.segmented_control("Bearbeitung", ["Offen", "Bearbeitet", "Alle"], default="Alle", key="dm_work",
                                persist_state="session")
    shown = f2.pills("Status", ["Alarm", "Prüfen", "Kein Alarm"], selection_mode="multi",
                     default=["Alarm", "Prüfen", "Kein Alarm"], key="dm_labels", persist_state="session")
    query = f3.text_input("Suche", placeholder="Anruf, Art oder Grund", key="dm_search",
                          label_visibility="collapsed")
    wanted = {k for k, v in cm.cd.LABEL_DE.items() if v in (shown or [])}
    q = (query or "").strip().lower()
    rows = [r for r in rows if r["label"] in wanted
            and (work in (None, "Alle") or r["status"] == work.lower())
            and (not q or q in r["call_id"].lower() or q in r["family"].lower() or q in r["reason"].lower())]

    df = pd.DataFrame([{
        "Status": cm.cd.LABEL_DE[r["label"]], "Bearbeitung": "✓ bearbeitet" if r["status"] == "bearbeitet" else "offen",
        "Anruf": r["call_id"], "Art": r["family"], "Warum": r["reason"], "Rechtsgrundlage": r["basis"],
        "Score": r["score"], "Unsicherheit": r["uncertainty"],
    } for r in rows], columns=["Status", "Bearbeitung", "Anruf", "Art", "Warum", "Rechtsgrundlage", "Score",
                               "Unsicherheit"])
    if df.empty:
        st.info("Kein Anruf passt zu den Filtern.", icon=":material/filter_alt_off:")
    else:
        event = st.dataframe(
            ui.style_labels(df, "Status"), hide_index=True, width="stretch", key="dm_cases_table",
            height=min(40 + 35 * len(df), 720), on_select="rerun", selection_mode="single-row",
            column_order=["Status", "Bearbeitung", "Anruf", "Art", "Warum", "Rechtsgrundlage", "Score"],
            column_config={
                "Status": st.column_config.TextColumn(width=90),
                "Bearbeitung": st.column_config.TextColumn("Bearbeitung", width=105),
                "Anruf": st.column_config.TextColumn(width=125),
                "Art": st.column_config.TextColumn(width=200, help="Art von Fehlverhalten."),
                "Warum": st.column_config.TextColumn(width=470, help="Der Grund in einem Satz."),
                "Rechtsgrundlage": st.column_config.TextColumn(width=170),
                "Score": ui.score_column(width=100, help="Gesamtrisiko 0..1; ab der Schwelle Alarm."),
            })
        st.caption(":material/touch_app: Zeile anklicken öffnet den Anruf. Rechtsgrundlagen sind Vorschläge, "
                   "durch Compliance zu bestätigen.")
        sel = event.selection.rows if event is not None and hasattr(event, "selection") else []
        if sel and 0 <= sel[0] < len(df):
            app.goto_call(df.iloc[sel[0]]["Anruf"])
