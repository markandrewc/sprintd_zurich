"""Call detail: why the call got its label, the suspicious passages with audio first (officers want the
passage, not the whole call), then what each check said, then the full transcript and recording.

Deep link: ``?call=<id>&t=<seconds>`` (alert triggers) opens the call with the full recording at ``t``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from callguard.types import fmt_ts
from callguard.ui import render as ui
from callguard.ui.backend import (
    LABEL_TEXT,
    check_problems,
    checks_said,
    linked_passage,
    parse_seconds,
    short_label,
    top_family,
)
from callguard.ui.session import current_app, ground_truth

app = current_app()
s = app.settings

if not app.loaded.results:
    st.title("Call detail")
    st.info(f"No processed calls yet in `{app.runs_dir}`. Process one on **Process a call**.",
            icon=":material/inbox:")
    st.stop()

order = [r["call_id"] for r in app.rows()]
wanted = st.query_params.get("call") or st.session_state.get("cg_last_call") or order[0]
missing = wanted not in app.loaded.results
call_id = order[0] if missing else wanted
st.session_state["cg_last_call"] = call_id
if not missing and st.query_params.get("call") != call_id:  # keep the URL shareable
    st.query_params["call"] = call_id
t = parse_seconds(st.query_params.get("t")) if not missing else None


def _pick() -> None:
    st.query_params.clear()
    st.query_params["call"] = st.session_state["cg_detail_pick"]


def _step(delta: int) -> None:
    i = (order.index(call_id) + delta) % len(order)
    st.query_params.clear()
    st.query_params["call"] = order[i]


def _fmt(cid: str) -> str:
    d = app.decided[cid].decision
    return f"{cid}  ·  {LABEL_TEXT[d.label]}  ·  {d.score:.2f}"


st.session_state["cg_detail_pick"] = call_id  # the URL is the source of truth, the picker follows it
nav1, nav2, nav3 = st.columns([6, 1, 1], vertical_alignment="bottom")
nav1.selectbox("Call", order, format_func=_fmt, key="cg_detail_pick", on_change=_pick,
               help="Calls ordered by score, riskiest first.")
nav2.button("Previous", icon=":material/arrow_back:", on_click=_step, args=(-1,), width="stretch")
nav3.button("Next", icon=":material/arrow_forward:", on_click=_step, args=(1,), width="stretch")
if missing:
    st.warning(f"Call `{wanted}` has no result in `{app.runs_dir}` (not processed with profile "
               f"'{app.cfg.name}'?). Showing `{call_id}` instead.", icon=":material/search_off:")

result = app.loaded.results[call_id]
dd = app.decided[call_id]
d = dd.decision
result_dir = app.loaded.paths[call_id].parent
top = top_family(d, app.can_alarm)

# -- header ------------------------------------------------------------------------------------

st.title(f"{call_id} {ui.label_md(d.label)}", anchor=False)
fam_line = (f"**{ui.esc(top.label)}**" if top else "No family scored above zero")
st.markdown(f"{fam_line} · {len(d.passages)} suspicious passage{'s' if len(d.passages) != 1 else ''}"
            + (f" · {fmt_ts(result.transcript.duration)} call" if result.transcript.duration else ""))

m = st.columns(3)
m[0].metric("Score", f"{d.score:.2f}", delta=f"{d.score - s.threshold:+.2f} vs threshold {s.threshold:.2f}",
            delta_color="inverse", border=True, help="Fused risk of the strongest family. At or above the "
                                                     "threshold = alarm.")
m[1].metric("Uncertainty", f"{d.uncertainty:.2f}", delta=f"review above {s.max_uncertainty:.2f}",
            delta_color="off", delta_arrow="off", border=True,
            help="How much the checks disagree or doubt themselves. Above the maximum, the call is handed to a human.")
m[2].metric("Review band", f"{max(0.0, s.review_floor):.2f} – {s.threshold:.2f}", border=True,
            help="Scores in this range go to a human for review (sidebar).")

if d.label == "review":
    st.warning("**Unsicher → an Menschen übergeben.** The checks are not sure enough to decide this call "
               "on their own. Please listen to the passages below and decide.", icon=":material/person_search:")
elif d.label == "alarm":
    st.error("**Alarm.** Listen to the passages below and escalate if confirmed.",
             icon=":material/notifications_active:")

with st.container(border=True):
    st.markdown("**Why this label**")
    st.markdown("\n".join(f"- {ui.esc(r)}" for r in d.reasons) or "–")

if not dd.live:
    st.warning(f"Showing the decision stored at processing time; live re-deciding failed ({dd.error}). "
               "The sidebar settings do not apply to this call.", icon=":material/history:")
elif dd.stored.label != d.label:
    st.info(f"At processing time this call was **{LABEL_TEXT[dd.stored.label]}** (threshold "
            f"{dd.stored.threshold:.2f}). With the current sidebar settings it is **{LABEL_TEXT[d.label]}**.",
            icon=":material/tune:")
for name, err in check_problems(result).items():
    st.warning(f"Check **{name}** failed for this call and is missing from the score: {err[:300]}",
               icon=":material/error:")
stale = [n for n, cr in result.checks.items() if cr.meta.get("stale")]
if stale:
    st.caption(f":material/history: Not re-run since the last criteria edit: {', '.join(stale)}.")

# -- passages ----------------------------------------------------------------------------------

st.subheader(f"Suspicious passages ({len(d.passages)})")
link_i = linked_passage(d.passages, t, app.link_pad)
if t is not None:
    st.caption(f":material/link: Opened from an alert link at {fmt_ts(t)}"
               + (f"; it points at passage {link_i + 1}." if link_i is not None else "."))
if not d.passages:
    st.success("No passage reached the review level under the current settings.", icon=":material/check:")
for i, p in enumerate(d.passages):
    ui.passage_card(i + 1, p, result, result_dir, app.snippet_pad, linked=(i == link_i))

# -- per family / per check ---------------------------------------------------------------------

st.subheader("How the checks scored")
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    if d.families:
        st.altair_chart(ui.family_chart(d, s.threshold, max(0.0, s.review_floor), app.can_alarm), width="stretch")
        st.caption("Bar = fused family score, black tick = fused value, dots = each check's own score. "
                   "Solid line: alarm threshold, dashed: start of the review band.")
    else:
        st.info("No family was scored.")
with c2:
    fam_rows = [{"Family": short_label(f.label), "Score": f.score, "Uncertainty": f.uncertainty}
                for f in sorted(d.families.values(), key=lambda f: -f.score)]
    st.dataframe(pd.DataFrame(fam_rows, columns=["Family", "Score", "Uncertainty"]),
                 hide_index=True, width="stretch",
                 column_config={"Score": ui.score_column(),
                                "Uncertainty": st.column_config.NumberColumn(format="%.2f")})

said = checks_said(result, d, s.weights)
with st.expander("What each check said", icon=":material/fact_check:", expanded=d.label != "no_alert"):
    only_top = st.toggle("Only relevant families", value=True, key="cg_detail_only_scored",
                         help="The top family and every family scoring at least half the review level.")
    if only_top:
        bar = 0.5 * max(0.0, s.review_floor)
        relevant = {short_label(f.label) for f in d.families.values() if f.score >= bar and f.score > 0}
        if top:
            relevant.add(short_label(top.label))
        said = [r for r in said if r["family"] in relevant]
    st.dataframe(pd.DataFrame([{
        "Family": r["family"], "Check": r["check"], "Weight": r["weight"], "Score": r["score"],
        "Confidence": r["confidence"], "Verdict": r["verdict"], "Reason": r["reason"],
    } for r in said], columns=["Family", "Check", "Weight", "Score", "Confidence", "Verdict", "Reason"]),
        hide_index=True, width="stretch",
        column_config={"Score": ui.score_column(),
                       "Confidence": st.column_config.NumberColumn(format="%.2f"),
                       "Weight": st.column_config.NumberColumn(format="%.2f"),
                       "Reason": st.column_config.TextColumn(width="large")})

# -- transcript and recording -------------------------------------------------------------------

st.subheader("Transcript")
if result.audio_path and Path(result.audio_path).is_file():
    start = int(t) if t is not None else 0
    st.caption("Full recording" + (f", starting at {fmt_ts(start)}" if start else ""))
    try:
        st.audio(result.audio_path, start_time=start)
    except Exception as e:
        st.caption(f":material/volume_off: Recording could not be loaded ({type(e).__name__}).")
else:
    st.caption(":material/volume_off: Recording not available on this machine.")
if result.transcript.segments:
    st.caption("Highlighted: segments of a suspicious passage. Bold: keyword hits.")
    with st.container(height=560 if len(result.transcript.segments) > 12 else "content", border=True):
        st.markdown(ui.transcript_markdown(result.transcript, d.passages, result))
else:
    st.info("The transcript is empty (silence, or speech recognition failed).")

# -- provenance and evaluation ------------------------------------------------------------------

with st.expander("Processing details", icon=":material/info:"):
    tr = result.transcript
    ui.kv_table({
        "Profile": result.config_name or "–", "ASR": tr.asr_backend or "–", "Language": tr.language or "–",
        "Duration": fmt_ts(tr.duration) if tr.duration else "–", "Segments": len(tr.segments),
        "Recording": result.audio_path or "–", "Result file": str(app.loaded.paths[call_id]),
        **{f"Time {k}": f"{v:.1f} s" for k, v in result.timings.items()},
    })
    meta = [{"Check": n, "Type": cr.type, **{k: str(v)[:120] for k, v in cr.meta.items()}}
            for n, cr in result.checks.items()]
    if meta:
        st.dataframe(pd.DataFrame(meta).fillna(""), hide_index=True, width="stretch")

truth = ground_truth(str(app.ctx.data_dir)).get(call_id)
if truth is not None and truth.expected is not None:
    with st.expander("Evaluation only: expected assessment from the case data", icon=":material/school:"):
        exp = truth.expected
        ok = exp.label == d.label
        st.markdown(f"Expected {ui.label_md(exp.label)} · family `{exp.family}` · "
                    + (":green[matches]" if ok else ":red[differs from the current label]"))
        if exp.reason:
            st.markdown(f"> {ui.esc(exp.reason)}")
        st.caption("Never used by the pipeline; shown here only to explain the evaluation.")
