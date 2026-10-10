"""Fälle: the worklist. Alarms first, then reviews, then the rest; Alarmschwelle and Prüfmodus right above the
list, with the live counts, so changing either is one move with a visible effect."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard.demo import common as cm
from callguard.demo import state as ds
from callguard.ui import modes as md
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
    st.caption(f"{len(app.loaded.results)} Anrufe · {open_flagged} davon brauchen noch einen Menschen "
               "(Alarm oder Prüfen, noch nicht bearbeitet)")

    with st.container(border=True):
        c1, c2, c3 = st.columns([4, 4, 5], gap="large")
        with c1:
            st.slider("Alarmschwelle", 0.0, 1.0, step=0.01, key=ds.THRESHOLD_KEY, persist_state="session",
                      help="Ab diesem Score löst ein Anruf Alarm aus; knapp darunter geht er zur Prüfung an einen "
                           "Menschen. Wirkt sofort auf alle Anrufe (keine Spracherkennung, kein Sprachmodell).")
            st.caption(f"Alarm ab **{s.threshold:.2f}** · Prüfen ab **{max(0.0, s.review_floor):.2f}** · "
                       f"Standard {app.defaults['threshold']:.2f}")
        with c2:
            if app.modes is not None:
                modes = app.modes
                by = {m.id: m for m in modes.spec.modes}
                st.segmented_control(
                    "Prüfmodus", ds.available_modes(modes), key=ds.MODE_KEY, required=True,
                    format_func=lambda k: by[k].label, persist_state="session",
                    on_change=ds.on_mode_change,
                    args=(str(app.runs_root), app.source.key, str(app.runs_dir), ds.profile_threshold(app)),
                    help="Wie streng callguard entscheidet. Die Wahl gilt für dieses Profil und wird im "
                         "Audit-Log vermerkt.")
                cur = by.get(s.mode or modes.spec.default)
                if cur is not None:
                    note = md.consequence_short(modes.metrics.get(cur.id))
                    st.caption(cur.text + (f" Gemessen: {note}." if note else ""))
                off = [m for m in modes.spec.modes if not modes.avail.get(m.id, md.Availability(True)).ok]
                if off:
                    st.caption(":material/block: " + ", ".join(f"«{m.label}»" for m in off) + " brauchen die "
                               "Zweitmeinung eines zweiten Modells; für diese Anrufe nicht verfügbar.")
            else:
                st.caption("Prüfmodi sind in diesem Profil nicht eingerichtet.")
        with c3:
            m = st.columns(3)
            for col, lbl in zip(m, ("alarm", "review", "no_alert")):
                delta = counts[lbl] - base[lbl]
                col.metric(cm.cd.LABEL_DE[lbl], counts[lbl], delta=f"{delta:+d} zum Standard" if delta else None,
                           delta_color="off", border=False)
            st.caption(f"Ein Mensch hört **{counts['alarm'] + counts['review']}** von {len(app.decided)} Anrufen "
                       "(Alarm + Prüfen). Schwelle oder Modus verschieben: die Zahlen folgen sofort.")

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
