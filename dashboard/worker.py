"""Hintergrund-Arbeit des Dashboards: Transkription und Analyse in einem Thread, nacheinander.

Pro Auftrag werden zuerst alle Aufnahmen transkribiert, dann das ASR-Modell entladen, dann alles analysiert: So liegt
nie mehr als ein Modell gleichzeitig auf der GPU. Der Fortschritt steht in progress() (für die Statuszeile).
"""
import queue
import threading

from fraud_analysis import client as fraud
from transcription import client as asr

from . import store, views

JOBS = queue.Queue()
_state = {"step": "", "pending": 0}
_lock = threading.Lock()


def progress():
    with _lock:
        return {"busy": bool(_state["step"]) or _state["pending"] > 0, "step": _state["step"], "pending": _state["pending"]}


def _set(step):
    with _lock: _state["step"] = step


def submit(kind, ids):
    """kind: "process" (transkribieren + analysieren) oder "reanalyze" (nur analysieren, gespeichertes Transkript)."""
    for cid in ids: store.set_status(cid, "in_arbeit")
    with _lock: _state["pending"] += len(ids)
    JOBS.put((kind, list(ids)))


def _done(n=1):
    with _lock: _state["pending"] = max(0, _state["pending"] - n)


def _analyze(cid, transcription):
    cfg = views.config()
    a = fraud.analyze(transcription["text"], segments=transcription["segments"], threshold=views.threshold(cfg),
                      passage_words=views.passage_words(cfg))
    store.save_result(cid, transcription, a)


def _run(kind, ids):
    texts = {}
    if kind == "process":
        for i, cid in enumerate(ids, 1):
            call = store.get_call(cid)
            if call is None: continue
            _set(f"Transkription {i}/{len(ids)}: {call['filename']}")
            try: texts[cid] = asr.transcribe(call["audio_path"])
            except Exception as e: store.save_error(cid, str(e)); _done()
        asr.unload()   # VRAM frei für die Analyse
    else:
        for cid in ids:
            call = store.get_call(cid)
            if call and call.get("transcript"): texts[cid] = {"text": call["transcript"], "segments": call["segments"]}
            elif call: store.save_error(cid, "Kein Transkript vorhanden"); _done()
    for i, (cid, t) in enumerate(texts.items(), 1):
        call = store.get_call(cid)
        if call is None: _done(); continue
        _set(f"Analyse {i}/{len(texts)}: {call['filename']}")
        try: _analyze(cid, t)
        except Exception as e: store.save_error(cid, str(e))
        _done()


def _loop():
    while True:
        kind, ids = JOBS.get()
        try: _run(kind, ids)
        finally: _set("")


def start():
    threading.Thread(target=_loop, daemon=True, name="dashboard-worker").start()
