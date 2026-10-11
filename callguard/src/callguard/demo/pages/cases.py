"""Fälle: the worklist. Alarms first, then reviews, then the rest; above the list the four status boxes, the
«Sicherheit der KI» slider (dual-reader profiles; else the Alarmschwelle) and the spread of all fact answers."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard.demo import common as cm
from callguard.demo import controls as ctl
from callguard.demo import facts_ui as fu
from callguard.demo import state as ds
from callguard.ui import render as ui
from callguard.ui.backend import label_counts
from callguard.ui.session import current_app

app = current_app()
s = app.settings

head, new = st.columns([5, 1.3], vertical_alignment="bottom")
head.title("Fälle")
new.page_link(app.pages["process"], label="Neuen Anruf prüfen", icon=":material/upload_file:",
              help="Eine Aufnahme hochladen: von der Spracherkennung bis zum Alarm (braucht den GPU-Rechner).")
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
                   "können vom aktiven Regelwerk abweichen (Einstellungen → Regeln; «Gespeicherte Anrufe neu "
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

    fus = fu.fusion(app)
    if fus is not None:
        # 2. «Sicherheit der KI», full width: how sure a reader must be for ja / nein (else unklar -> Prüfen)
        live = fu.live_policy(app)
        c_default = live.certainty()
        st.slider("Sicherheit der KI", 0.5, 0.95, step=0.05, key=ds.CERTAINTY_KEY, persist_state="session",
                  format="%.2f",
                  help="Pro Fakt und KI-Leser: ja, wenn die KI mindestens so sicher ist; nein, wenn sie höchstens "
                       "1 − Wert sicher ist; dazwischen unklar. Höher = mehr «unklar» = weniger Alarme, mehr Prüfen. "
                       f"Standard {c_default:.2f} (auf den Dev-Anrufen gemessen). Wirkt sofort, nur für Sie.")
        pol = fu.session_policy(app)
        c = pol.certainty()
        spread = fu.answer_spread(app.loaded.results, pol, fus.tables(), sig=app.loaded.signature)
        comb = spread["combined"]
        st.caption(f"**ja ab {c:.2f} · nein bis {1 - c:.2f} · dazwischen unklar → eher Prüfen** · beide KI-Leser "
                   f"({pol.a.label}, {pol.b.label}), danach «{pol.combination_de()}» je Fakt · Standard {c_default:.2f}")
        # 3. the spread of all fact answers under this certainty
        st.altair_chart(fu.spread_chart(spread["rows"], round(1 - c, 4), c), width="stretch")
        st.markdown(f":material/fact_check: **Fakten** (je Anruf und Fakt, beide Leser zusammen): "
                    f"ja **{comb['yes']}** · unklar **{comb['unclear']}** · nein **{comb['no']}** → Anrufe: "
                    f"Alarm **{counts['alarm']}** · Prüfen **{counts['review']}** · Kein Alarm **{counts['no_alert']}**")
    else:
        # 2. the Alarmschwelle, full width (profiles with one reader)
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
