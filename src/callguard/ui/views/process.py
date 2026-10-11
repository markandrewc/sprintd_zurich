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

st.title("Anruf verarbeiten")
if pipeline is None:
    st.error(f"Verarbeitung nicht verfügbar: {app.engine.error}", icon=":material/block:")
    st.stop()
if app.read_only:
    st.info("Angezeigt wird eine Experiment-Variante (nur lesen). Zum Verarbeiten in der Seitenleiste einen "
            "Profil-Lauf als Quelle wählen.", icon=":material/lock:")
    st.stop()

device = str(app.cfg.asr.get("device", "cpu")).lower()
if app.cfg.asr.get("type") == "reference":
    st.warning("Dieses Profil liest die Referenz-Skripte des Falls statt Spracherkennung (Orakel, nur für "
               "Experimente; für die Abgabe verboten).",
               icon=":material/science:")
elif device == "cpu":
    st.info("Dieses Profil läuft auf der CPU: die Spracherkennung dauert etwa so lange wie die Aufnahme "
            "(4 Minuten Anruf ≈ 4 Minuten), dazu die LLM-Prüfungen. Diesen Tab offen lassen; bereits gerechnete "
            "Schritte werden beim erneuten Verarbeiten übersprungen.", icon=":material/hourglass_top:")
st.caption(f"Profil **{app.cfg.name}** · Spracherkennung `{app.cfg.asr.get('type')}` auf {device} · Ergebnisse "
           f"nach `{app.runs_dir}`")


@st.cache_data(show_spinner=False)
def _duration(path: str) -> float | None:
    return audio_seconds(path)


def _fmt_dur(seconds: float | None) -> str:
    return "?" if seconds is None else fmt_ts(seconds)


def _run(audio_path, call_id: str) -> None:
    with st.status(f"{call_id} wird verarbeitet …", expanded=True) as status:
        t0 = time.time()

        def notify(msg: str) -> None:
            status.update(label=f"{call_id}: {msg} …")
            st.write(f"`{fmt_ts(time.time() - t0)}` {msg}")

        try:
            result = process_call(pipeline, audio_path, call_id, notify=notify)
        except Exception as e:
            status.update(label=f"{call_id}: fehlgeschlagen ({type(e).__name__})", state="error", expanded=True)
            st.error(f"{type(e).__name__}: {e}")
            st.session_state.setdefault("cg_proc_failed", {})[call_id] = f"{type(e).__name__}: {e}"
            return
        d = result.decision
        status.update(label=f"{call_id}: {LABEL_TEXT[d.label]} · Score {d.score:.2f} · {time.time() - t0:.0f} s",
                      state="complete", expanded=False)
    st.session_state.get("cg_proc_failed", {}).pop(call_id, None)
    st.session_state.setdefault("cg_processed", []).insert(0, call_id)


def _run_all(jobs: list[tuple]) -> None:
    for audio_path, call_id in jobs:
        _run(audio_path, call_id)
    st.rerun()  # reload the results so the inbox, counts and the list below include the new calls


tab_data, tab_upload = st.tabs(["Falldaten", "Aufnahme hochladen"])

with tab_data:
    calls = {cid: c for cid, c in ground_truth(str(app.ctx.data_dir)).items() if c.audio_path.is_file()}
    if not calls:
        st.info(f"Keine Fallaufnahmen in `{app.ctx.data_dir}/Audio` gefunden.")
    else:
        done = app.loaded.results

        def _fmt(cid: str) -> str:
            return f"{cid}  ·  {LABEL_TEXT[app.decided[cid].decision.label]}" if cid in done else cid

        picked = st.multiselect("Aufnahmen", sorted(calls), format_func=_fmt, key="cg_proc_pick",
                                placeholder="Eine oder mehrere Aufnahmen wählen",
                                help="Bereits verarbeitete Anrufe zeigen ihren Status; erneutes Verarbeiten nutzt "
                                     "den Zwischenspeicher.")
        total = sum(_duration(str(calls[c].audio_path)) or 0.0 for c in picked)
        if picked:
            est = sum(estimate_seconds(app.cfg, _duration(str(calls[c].audio_path)) or 0.0) for c in picked)
            st.caption(f"{len(picked)} Aufnahme(n), {fmt_ts(total)} Audio · etwa {fmt_ts(est)} (mm:ss) auf "
                       f"diesem Rechner ohne Zwischenspeicher.")
        if st.button("Verarbeiten", type="primary", icon=":material/play_arrow:", disabled=not picked,
                     key="cg_proc_go"):
            _run_all([(calls[cid].audio_path, cid) for cid in picked])

with tab_upload:
    up = st.file_uploader("Aufnahme", type=[s.lstrip(".") for s in AUDIO_SUFFIXES], key="cg_proc_upload",
                          help="Am besten 16 kHz Mono-WAV; andere Formate wandelt ffmpeg um.")
    call_id = st.text_input("Anruf-Id", value=safe_call_id(up.name) if up else "", key="cg_proc_upload_id",
                            help="Name, unter dem das Ergebnis gespeichert wird. Ein bestehendes Ergebnis mit "
                                 "dieser Id wird ersetzt.", disabled=up is None)
    if up is not None and call_id and call_id in app.loaded.results:
        st.caption(f":material/warning: `{call_id}` existiert schon und wird ersetzt.")
    if st.button("Hochgeladene Aufnahme verarbeiten", type="primary", icon=":material/play_arrow:", disabled=up is None,
                 key="cg_proc_upload_go"):
        try:
            path = save_upload(app.runs_dir, up.name, up.getvalue())
        except Exception as e:
            st.error(f"Upload konnte nicht gespeichert werden: {e}")
        else:
            st.caption(f"Gespeichert unter `{path}` ({_fmt_dur(_duration(str(path)))})")
            _run_all([(path, safe_call_id(call_id or up.name))])

for cid, err in st.session_state.get("cg_proc_failed", {}).items():
    st.error(f"Verarbeitung von {cid} fehlgeschlagen: {err}", icon=":material/error:")

recent = [cid for cid in dict.fromkeys(st.session_state.get("cg_processed", [])) if cid in app.loaded.results]
if recent:
    st.subheader("In dieser Sitzung verarbeitet")
    for cid in recent[:10]:
        d = app.decided[cid].decision
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 5, 1], vertical_alignment="center")
            c1.markdown(f"**{cid}**  \n{ui.label_md(d.label)} · Score {d.score:.2f}")
            c2.caption(ui.esc(headline_reason(d, app.loaded.results[cid], app.settings.weights, app.can_alarm)))
            if c3.button("Öffnen", key=f"cg_proc_open_{cid}", icon=":material/open_in_new:", width="stretch"):
                app.goto_call(cid)
