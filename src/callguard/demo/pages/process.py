"""Anruf verarbeiten: a recording in, a decision out (speech recognition -> speakers -> checks -> decision), stage
by stage, then straight to «Anruf prüfen». Needs the models (GPU host); when they are not reachable the page
says so in plain words instead of failing halfway. Only the audio goes in: no file names, scripts or
expected labels reach the pipeline."""

from __future__ import annotations

import time

import streamlit as st

from callguard.demo import common as cm
from callguard.demo import readiness
from callguard.types import fmt_ts
from callguard.ui import render as ui
from callguard.ui.backend import (
    AUDIO_SUFFIXES,
    audio_seconds,
    estimate_seconds,
    process_call,
    safe_call_id,
    save_upload,
)
from callguard.ui.session import current_app, ground_truth

app = current_app()
pipeline = app.engine.pipeline

st.title("Anruf verarbeiten")
st.caption("Eine Aufnahme hochladen: Sherlock Phones erkennt die Sprache, trennt Beratung und Kunde, prüft das Gespräch "
           "und entscheidet. Danach öffnet sich der Anruf mit Begründung und Passagen.")


@st.cache_data(show_spinner="Modelle werden gesucht …", ttl=60)
def _ready(config: str, sets: tuple[str, ...], nonce: int) -> readiness.Ready:
    return readiness.check(config, list(sets))


nonce = st.session_state.setdefault("dm_ready_nonce", 0)
ready = _ready(app.args.config, tuple(app.args.sets), nonce)
with st.container(border=True):
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    if ready.ok:
        c1.markdown(f":material/check_circle: **Bereit.** {ui.esc(ready.summary)}")
    else:
        c1.markdown(f":material/cloud_off: **Die Modelle sind gerade nicht erreichbar.** {ui.esc(ready.summary)}  \n"
                    ":small[Bereits verarbeitete Anrufe lassen sich weiterhin prüfen. Für neue Aufnahmen den "
                    "GPU-Rechner starten (scripts/remote/serve_models.sh start).]")
    if c2.button("Erneut prüfen", icon=":material/refresh:", width="stretch"):
        st.session_state["dm_ready_nonce"] = nonce + 1
        st.rerun()

if pipeline is None:
    st.error(f"Die Verarbeitung ist in diesem Profil nicht verfügbar: {app.engine.error}", icon=":material/block:")
    st.stop()


@st.cache_data(show_spinner=False)
def _duration(path: str) -> float | None:
    return audio_seconds(path)


def _run(audio_path, call_id: str) -> bool:
    with st.status(f"{call_id} wird verarbeitet …", expanded=True) as status:
        t0 = time.time()

        def notify(msg: str) -> None:
            status.update(label=f"{call_id}: {msg} …")
            st.write(f"`{fmt_ts(time.time() - t0)}` {msg}")

        try:
            result = process_call(pipeline, audio_path, call_id, notify=notify)
        except Exception as e:
            status.update(label=f"{call_id}: nicht verarbeitet", state="error", expanded=True)
            st.error("Die Verarbeitung ist fehlgeschlagen" + ("" if ready.ok else " (Modelle nicht erreichbar)")
                     + f": {type(e).__name__}: {str(e)[:300]}", icon=":material/error:")
            return False
        d = result.decision
        status.update(label=f"{call_id}: {cm.cd.LABEL_DE[d.label]} · {time.time() - t0:.0f} s", state="complete",
                      expanded=False)
    st.session_state["dm_processed"] = call_id
    return True


tab_up, tab_case = st.tabs(["Aufnahme hochladen", "Fallaufnahme wählen"])
with tab_up:
    up = st.file_uploader("Aufnahme (WAV, MP3, M4A …)", type=[x.lstrip(".") for x in AUDIO_SUFFIXES],
                          key="dm_upload")
    if up is not None:
        cid = safe_call_id(up.name)
        st.caption(f"Wird gespeichert als **{cid}**" + (" (ersetzt das bisherige Ergebnis)"
                                                         if cid in app.loaded.results else ""))
    if st.button("Verarbeiten", type="primary", icon=":material/play_arrow:", disabled=up is None, key="dm_up_go"):
        try:
            path = save_upload(app.runs_dir, up.name, up.getvalue())
        except Exception as e:
            st.error(f"Die Aufnahme konnte nicht gespeichert werden: {e}", icon=":material/error:")
        else:
            est = estimate_seconds(app.cfg, _duration(str(path)) or 0.0)
            st.caption(f"Aufnahme {fmt_ts(_duration(str(path)) or 0)} · etwa {fmt_ts(est)} Rechenzeit")
            if _run(path, safe_call_id(up.name)):
                st.rerun()
with tab_case:
    calls = {c: x for c, x in ground_truth(str(app.ctx.data_dir)).items() if x.audio_path.is_file()}
    if not calls:
        st.caption("Keine Fallaufnahmen auf diesem Rechner.")
    else:
        pick = st.selectbox("Aufnahme", sorted(calls), index=None, placeholder="Fallaufnahme wählen",
                            key="dm_case_pick")
        if st.button("Verarbeiten", type="primary", icon=":material/play_arrow:", disabled=pick is None,
                     key="dm_case_go"):
            if _run(calls[pick].audio_path, pick):
                st.rerun()

done = st.session_state.get("dm_processed")
if done and done in app.loaded.results:
    d = app.decided[done].decision
    with st.container(border=True):
        a, b = st.columns([4, 1], vertical_alignment="center")
        a.markdown(f"**{done}** {cm.badge(d.label)}  \n{ui.esc(cm.cd.one_liner(cm.card_for(app, done)))}")
        if b.button("Anruf prüfen", type="primary", icon=":material/arrow_forward:", width="stretch"):
            app.goto_call(done)
