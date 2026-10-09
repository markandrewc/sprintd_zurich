"""Process a call: run the full pipeline on a case recording or an uploaded file, stage by stage.

On a laptop CPU speech recognition runs about realtime, so the page says up front how long it will
take and shows which stage is running. Only the audio goes in: file names, scripts and expected labels
are never passed to the pipeline (case rule).
"""

from __future__ import annotations

import time

import streamlit as st

from callguard.types import fmt_ts
from callguard.ui import render as ui
from callguard.ui.backend import (
    AUDIO_SUFFIXES,
    LABEL_TEXT,
    audio_seconds,
    estimate_seconds,
    headline_reason,
    process_call,
    safe_call_id,
    save_upload,
)
from callguard.ui.session import current_app, ground_truth

app = current_app()
pipeline = app.engine.pipeline

st.title("Process a call")
if pipeline is None:
    st.error(f"Processing is not available: {app.engine.error}", icon=":material/block:")
    st.stop()

device = str(app.cfg.asr.get("device", "cpu")).lower()
if app.cfg.asr.get("type") == "reference":
    st.warning("This profile reads the case's reference scripts instead of running speech recognition (oracle, "
               "for ceiling experiments only; the case rules forbid it for the submission).",
               icon=":material/science:")
elif device == "cpu":
    st.info("This profile runs on the CPU: speech recognition takes about as long as the recording "
            "(a 4-minute call ≈ 4 minutes), plus the LLM checks. Keep this tab open while it runs; cached "
            "stages are skipped when a call is processed again.", icon=":material/hourglass_top:")
st.caption(f"Profile **{app.cfg.name}** · ASR `{app.cfg.asr.get('type')}` on {device} · results go to "
           f"`{app.runs_dir}`")


@st.cache_data(show_spinner=False)
def _duration(path: str) -> float | None:
    return audio_seconds(path)


def _fmt_dur(seconds: float | None) -> str:
    return "?" if seconds is None else fmt_ts(seconds)


def _run(audio_path, call_id: str) -> None:
    with st.status(f"Processing {call_id} …", expanded=True) as status:
        t0 = time.time()

        def notify(msg: str) -> None:
            status.update(label=f"{call_id}: {msg} …")
            st.write(f"`{fmt_ts(time.time() - t0)}` {msg}")

        try:
            result = process_call(pipeline, audio_path, call_id, notify=notify)
        except Exception as e:
            status.update(label=f"{call_id}: failed ({type(e).__name__})", state="error", expanded=True)
            st.error(f"{type(e).__name__}: {e}")
            st.session_state.setdefault("cg_proc_failed", {})[call_id] = f"{type(e).__name__}: {e}"
            return
        d = result.decision
        status.update(label=f"{call_id}: {LABEL_TEXT[d.label]} · score {d.score:.2f} · {time.time() - t0:.0f} s",
                      state="complete", expanded=False)
    st.session_state.get("cg_proc_failed", {}).pop(call_id, None)
    st.session_state.setdefault("cg_processed", []).insert(0, call_id)


def _run_all(jobs: list[tuple]) -> None:
    for audio_path, call_id in jobs:
        _run(audio_path, call_id)
    st.rerun()  # reload the results so the inbox, counts and the list below include the new calls


tab_data, tab_upload = st.tabs(["Case dataset", "Upload a recording"])

with tab_data:
    calls = {cid: c for cid, c in ground_truth(str(app.ctx.data_dir)).items() if c.audio_path.is_file()}
    if not calls:
        st.info(f"No case recordings found in `{app.ctx.data_dir}/Audio`.")
    else:
        done = app.loaded.results

        def _fmt(cid: str) -> str:
            return f"{cid}  ·  {LABEL_TEXT[app.decided[cid].decision.label]}" if cid in done else cid

        picked = st.multiselect("Recordings", sorted(calls), format_func=_fmt, key="cg_proc_pick",
                                placeholder="Choose one or more recordings",
                                help="Already processed calls show their current label; processing again reuses "
                                     "cached stages.")
        total = sum(_duration(str(calls[c].audio_path)) or 0.0 for c in picked)
        if picked:
            est = sum(estimate_seconds(app.cfg, _duration(str(calls[c].audio_path)) or 0.0) for c in picked)
            st.caption(f"{len(picked)} recording(s), {fmt_ts(total)} of audio · roughly {fmt_ts(est)} (mm:ss) on "
                       f"this machine without cache.")
        if st.button("Process", type="primary", icon=":material/play_arrow:", disabled=not picked,
                     key="cg_proc_go"):
            _run_all([(calls[cid].audio_path, cid) for cid in picked])

with tab_upload:
    up = st.file_uploader("Recording", type=[s.lstrip(".") for s in AUDIO_SUFFIXES], key="cg_proc_upload",
                          help="16 kHz mono WAV is best; other formats are converted with ffmpeg.")
    call_id = st.text_input("Call id", value=safe_call_id(up.name) if up else "", key="cg_proc_upload_id",
                            help="Name under which the result is stored. An existing result with this id is "
                                 "replaced.", disabled=up is None)
    if up is not None and call_id and call_id in app.loaded.results:
        st.caption(f":material/warning: `{call_id}` already exists and will be replaced.")
    if st.button("Process upload", type="primary", icon=":material/play_arrow:", disabled=up is None,
                 key="cg_proc_upload_go"):
        try:
            path = save_upload(app.runs_dir, up.name, up.getvalue())
        except Exception as e:
            st.error(f"Upload could not be saved: {e}")
        else:
            st.caption(f"Saved to `{path}` ({_fmt_dur(_duration(str(path)))})")
            _run_all([(path, safe_call_id(call_id or up.name))])

for cid, err in st.session_state.get("cg_proc_failed", {}).items():
    st.error(f"Processing {cid} failed: {err}", icon=":material/error:")

recent = [cid for cid in dict.fromkeys(st.session_state.get("cg_processed", [])) if cid in app.loaded.results]
if recent:
    st.subheader("Processed in this session")
    for cid in recent[:10]:
        d = app.decided[cid].decision
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 5, 1], vertical_alignment="center")
            c1.markdown(f"**{cid}**  \n{ui.label_md(d.label)} · score {d.score:.2f}")
            c2.caption(ui.esc(headline_reason(d, app.loaded.results[cid], app.settings.weights, app.can_alarm)))
            if c3.button("Open", key=f"cg_proc_open_{cid}", icon=":material/open_in_new:", width="stretch"):
                app.goto_call(cid)
