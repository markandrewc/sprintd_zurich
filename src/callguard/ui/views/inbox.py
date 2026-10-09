"""Eingang (inbox): every call of the selected source under the current sidebar settings. Moving the alarm
threshold re-decides all calls instantly (fusion only, no ASR / LLM); the counts show the effect against
the profile default. Filter by status / family / level, sort by score, status, uncertainty or call.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from callguard.types import LABELS
from callguard.ui import render as ui
from callguard.ui.backend import LABEL_RANK, LABEL_TEXT, label_counts
from callguard.ui.session import current_app

app = current_app()
s = app.settings

st.title("Eingang")
if not app.loaded.results:
    st.info(f"Noch keine verarbeiteten Anrufe in `{app.runs_dir}`.", icon=":material/inbox:")
    st.markdown(
        "- Eine Aufnahme auf **Anruf verarbeiten** hochladen, oder\n"
        f"- im Terminal alle Fallanrufe verarbeiten: `uv run callguard batch -c {app.cfg.name}`\n\n"
        "Ergebnisse erscheinen hier, sobald sie geschrieben sind.")
    for err in app.loaded.errors:
        st.warning(err)
    st.stop()

changed = app.customized
counts, base = label_counts(app.decided), label_counts(app.baseline)
st.caption(f"{len(app.loaded.results)} Anrufe · {app.source.label if app.source else ''} · Alarm ab "
           f"**{s.threshold:.2f}**, Prüfen ab **{max(0.0, s.review_floor):.2f}**"
           + (" · *Einstellungen weichen vom Profil ab*" if changed else ""))

help_text = {
    "alarm": "Score ab der Schwelle und die Prüfungen sind sich sicher genug.",
    "review": "Knapp unter der Schwelle oder die Prüfungen sind unsicher: ein Mensch muss zuhören.",
    "no_alert": "Nichts ausreichend Verdächtiges gefunden.",
}
cols = st.columns(4)
for col, label in zip(cols, LABELS):
    delta = counts[label] - base[label]
    col.metric(LABEL_TEXT[label], counts[label], delta=f"{delta:+d} zum Profil" if changed else None,
               delta_color="off", delta_arrow="auto" if delta else "off", border=True, help=help_text[label])
flagged, flagged_base = counts["alarm"] + counts["review"], base["alarm"] + base["review"]
cols[3].metric("Mensch nötig", flagged, delta=f"{flagged - flagged_base:+d} zum Profil" if changed else None,
               delta_color="off", delta_arrow="auto" if flagged != flagged_base else "off", border=True,
               help="Alarm + Prüfen: Anrufe, die jemand anhören muss.")

stale = [cid for cid, d in app.decided.items() if not d.live]
if stale:
    err = app.decided[stale[0]].error
    st.warning(f"{len(stale)} Anruf(e) zeigen den gespeicherten Entscheid; die Neu-Bewertung schlug fehl ({err}). "
               "Die Regler wirken auf diese Anrufe nicht.", icon=":material/history:")
for err in app.loaded.errors:
    st.warning(f"Unlesbares Ergebnis: {err}", icon=":material/error:")

rows = app.rows()
incomplete = [r for r in rows if r["failed_checks"]]
if incomplete:
    names = sorted({n for r in incomplete for n in r["failed_checks"]})
    st.warning(f"{len(incomplete)} Anruf(e) wurden ohne {', '.join(names)} entschieden: die Prüfung ist bei der "
               f"Verarbeitung ausgefallen (z.B. LLM-Server nicht erreichbar). Bitte neu verarbeiten: "
               f"{', '.join(r['call_id'] for r in incomplete)}.", icon=":material/report:")
st.altair_chart(ui.score_strip(rows, s.threshold, max(0.0, s.review_floor)), width="stretch")
st.caption(":material/tune: Alarmschwelle links in der Seitenleiste verschieben: Punkte wandern sofort zwischen "
           "den Spuren, die Zahlen oben ändern sich mit.")


def _level(call_id: str) -> str:
    m = re.search(r"Stufe\s*(\d+)", call_id)
    return f"Stufe {m.group(1)}" if m else "ohne Stufe"


for r in rows:
    r["level"] = _level(r["call_id"])

f1, f2, f3 = st.columns([3, 3, 2], vertical_alignment="bottom")
shown = f1.pills("Status", [LABEL_TEXT[x] for x in LABELS], selection_mode="multi",
                 default=[LABEL_TEXT[x] for x in LABELS], key="cg_inbox_filter")
fam_opts = sorted({r["family"] for r in rows if r["family"]})
fams = f2.multiselect("Art von Fehlverhalten", fam_opts, key="cg_inbox_family", placeholder="alle Arten")
lvl_opts = sorted({r["level"] for r in rows})
lvls = f3.multiselect("Stufe", lvl_opts, key="cg_inbox_level", placeholder="alle Stufen")
g1, g2 = st.columns([3, 5], vertical_alignment="bottom")
SORTS = {"Score (höchster zuerst)": lambda r: (-r["score"], LABEL_RANK[r["label"]], r["call_id"]),
         "Status (Alarm zuerst)": lambda r: (LABEL_RANK[r["label"]], -r["score"], r["call_id"]),
         "Unsicherheit (höchste zuerst)": lambda r: (-r["uncertainty"], -r["score"], r["call_id"]),
         "Anruf (A–Z)": lambda r: r["call_id"]}
sort_by = g1.selectbox("Sortieren nach", list(SORTS), key="cg_inbox_sort")
query = g2.text_input("Suche", placeholder="Anruf, Art oder Begründung", key="cg_inbox_search")

wanted = {k for k, v in LABEL_TEXT.items() if v in (shown or [])}
q = (query or "").strip().lower()
rows = [r for r in rows if r["label"] in wanted
        and (not fams or r["family"] in fams) and (not lvls or r["level"] in lvls)
        and (not q or q in r["call_id"].lower() or q in r["family"].lower() or q in r["reason"].lower())]
rows.sort(key=SORTS[sort_by])

df = pd.DataFrame([{
    "Status": LABEL_TEXT[r["label"]], "Anruf": r["call_id"], "Score": r["score"], "Unsicherheit": r["uncertainty"],
    "Art": r["family"], "Stufe": r["level"], "Passagen": r["passages"], "Warum": r["reason"], "Änderung": r["changed"],
} for r in rows], columns=["Status", "Anruf", "Score", "Unsicherheit", "Art", "Stufe", "Passagen", "Warum", "Änderung"])

if df.empty:
    st.info("Kein Anruf passt zu den Filtern.", icon=":material/filter_alt_off:")
event = st.dataframe(
    ui.style_labels(df, "Status"), hide_index=True, width="stretch", key="cg_inbox_table",
    height=min(36 + 35 * max(len(df), 1), 760),
    on_select="rerun", selection_mode="single-row",
    column_order=["Status"] + (["Änderung"] if any(df["Änderung"]) else [])
    + ["Anruf", "Score", "Art", "Warum", "Passagen", "Unsicherheit", "Stufe"],
    column_config={
        "Status": st.column_config.TextColumn(width="small"),
        "Anruf": st.column_config.TextColumn(width="medium"),
        "Score": ui.score_column(width="small", help="Gesamtrisiko der stärksten Art (0..1)."),
        "Unsicherheit": st.column_config.NumberColumn(format="%.2f", width="small",
                                                      help="Uneinigkeit und geringe Sicherheit der Prüfungen."),
        "Art": st.column_config.TextColumn(help="Art von Fehlverhalten, die den Score bestimmt."),
        "Stufe": st.column_config.TextColumn(width="small", help="Schwierigkeitsstufe des Falls (aus dem Anrufnamen)."),
        "Passagen": st.column_config.NumberColumn(width="small", help="Verdächtige Passagen zum Anhören."),
        "Warum": st.column_config.TextColumn(width="large", help="Hauptgrund laut den Prüfungen."),
        "Änderung": st.column_config.TextColumn("Geändert", help="Status mit Profil-Standard → Status jetzt."),
    },
)
st.caption(":material/touch_app: Zeile anklicken: der Anruf öffnet sich mit Passagen, Zeitachse und Audio.")

selected = event.selection.rows if event and hasattr(event, "selection") else []
if selected and 0 <= selected[0] < len(df):
    app.goto_call(df.iloc[selected[0]]["Anruf"])

c1, c2 = st.columns([1, 1])
c1.download_button("Tabelle herunterladen (CSV)", df.to_csv(index=False).encode("utf-8"),
                   file_name="callguard_eingang.csv", mime="text/csv", icon=":material/download:")
if "keywords" in app.pages and not app.read_only:
    c2.page_link(app.pages["keywords"], label="Stichwortliste bearbeiten und sofort anwenden",
                 icon=":material/tune:")
