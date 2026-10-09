"""Inbox: every processed call under the current sidebar settings, riskiest first. Moving the threshold
re-decides all calls instantly (fusion only), the counts show the effect against the config default."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard.types import LABELS
from callguard.ui import render as ui
from callguard.ui.backend import LABEL_TEXT, label_counts
from callguard.ui.session import current_app

app = current_app()
s = app.settings

st.title("Inbox")
if not app.loaded.results:
    st.info(f"No processed calls yet in `{app.runs_dir}`.", icon=":material/inbox:")
    st.markdown(
        "- Process a recording on **Process a call**, or\n"
        f"- run the batch from a terminal: `uv run callguard batch -c {app.cfg.name}`\n\n"
        "Results appear here as soon as they are written.")
    for err in app.loaded.errors:
        st.warning(err)
    st.stop()

changed = app.customized
counts, base = label_counts(app.decided), label_counts(app.baseline)
st.caption(f"{len(app.loaded.results)} calls · alarm threshold **{s.threshold:.2f}**, review from "
           f"**{max(0.0, s.review_floor):.2f}**" + (" · *settings differ from the config defaults*" if changed else ""))

help_text = {
    "alarm": "Score at or above the threshold and the checks are sure enough.",
    "review": "Close to the threshold or the checks are unsure: a human has to listen.",
    "no_alert": "Nothing suspicious enough was found.",
}
cols = st.columns(4)
for col, label in zip(cols, LABELS):
    delta = counts[label] - base[label]
    col.metric(LABEL_TEXT[label], counts[label], delta=f"{delta:+d} vs default" if changed else None,
               delta_color="off", delta_arrow="auto" if delta else "off", border=True, help=help_text[label])
flagged, flagged_base = counts["alarm"] + counts["review"], base["alarm"] + base["review"]
cols[3].metric("Need a human", flagged, delta=f"{flagged - flagged_base:+d} vs default" if changed else None,
               delta_color="off", delta_arrow="auto" if flagged != flagged_base else "off", border=True,
               help="Alarm + review: calls an officer listens to.")

stale = [cid for cid, d in app.decided.items() if not d.live]
if stale:
    err = app.decided[stale[0]].error
    st.warning(f"{len(stale)} call(s) show the decision stored at processing time; live re-deciding failed "
               f"({err}). The sliders do not affect them.", icon=":material/history:")
for err in app.loaded.errors:
    st.warning(f"Unreadable result: {err}", icon=":material/error:")

rows = app.rows()
incomplete = [r for r in rows if r["failed_checks"]]
if incomplete:
    names = sorted({n for r in incomplete for n in r["failed_checks"]})
    st.warning(f"{len(incomplete)} call(s) were decided without {', '.join(names)}: the check failed when the "
               f"call was processed (e.g. LLM server down). Re-process them once it works again: "
               f"{', '.join(r['call_id'] for r in incomplete)}.", icon=":material/report:")
st.altair_chart(ui.score_strip(rows, s.threshold, max(0.0, s.review_floor)), width="stretch")

f1, f2 = st.columns([2, 3], vertical_alignment="bottom")
shown = f1.pills("Show", [LABEL_TEXT[x] for x in LABELS], selection_mode="multi",
                 default=[LABEL_TEXT[x] for x in LABELS], key="cg_inbox_filter")
query = f2.text_input("Search", placeholder="Call id, family or reason", key="cg_inbox_search",
                      label_visibility="collapsed")
wanted = {k for k, v in LABEL_TEXT.items() if v in (shown or [])}
q = (query or "").strip().lower()
rows = [r for r in rows if r["label"] in wanted
        and (not q or q in r["call_id"].lower() or q in r["family"].lower() or q in r["reason"].lower())]

df = pd.DataFrame([{
    "Status": LABEL_TEXT[r["label"]], "Call": r["call_id"], "Score": r["score"], "Uncertainty": r["uncertainty"],
    "Family": r["family"], "Passages": r["passages"], "Why": r["reason"], "Change": r["changed"],
} for r in rows], columns=["Status", "Call", "Score", "Uncertainty", "Family", "Passages", "Why", "Change"])

event = st.dataframe(
    ui.style_labels(df, "Status"), hide_index=True, width="stretch", key="cg_inbox_table",
    height=min(36 + 35 * max(len(df), 1), 760),
    on_select="rerun", selection_mode="single-row",
    column_order=["Status"] + (["Change"] if any(df["Change"]) else [])
    + ["Call", "Score", "Family", "Why", "Passages", "Uncertainty"],
    column_config={
        "Status": st.column_config.TextColumn(width="small"),
        "Call": st.column_config.TextColumn(width="medium"),
        "Score": ui.score_column(width="small", help="Fused risk of the strongest family (0..1)."),
        "Uncertainty": st.column_config.NumberColumn(format="%.2f", width="small",
                                                     help="Disagreement and low confidence of the checks."),
        "Family": st.column_config.TextColumn(help="Kind of misconduct that drives the score."),
        "Passages": st.column_config.NumberColumn(width="small", help="Suspicious passages to listen to."),
        "Why": st.column_config.TextColumn(width="large", help="Main reason given by the checks."),
        "Change": st.column_config.TextColumn("Changed", help="Label under the config defaults → label now."),
    },
)
st.caption(":material/touch_app: Select a row to open the call with its passages and audio.")

selected = event.selection.rows if event and hasattr(event, "selection") else []
if selected and 0 <= selected[0] < len(df):
    app.goto_call(df.iloc[selected[0]]["Call"])

st.download_button("Download table (CSV)", df.to_csv(index=False).encode("utf-8"), file_name="callguard_inbox.csv",
                   mime="text/csv", icon=":material/download:")
