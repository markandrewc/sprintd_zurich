"""Transkriptions-Dienst (FastAPI). Lädt das ASR-Modell einmal beim Start.

  python -m transcription.api           # -> http://127.0.0.1:8001  (Doku: /docs)

  POST /transcribe   Audiodatei (multipart, Feld "file")  -> {"text", "segments": [{"start", "end", "text"}], "seconds"}
  GET  /health

Umgebungsvariablen: TRANSCRIPTION_HOST (127.0.0.1), TRANSCRIPTION_PORT (8001), dazu ASR_* aus asr.py.
"""
import os
import tempfile
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from .asr import AUDIO_EXTS, Transcriber

STATE = {}
LOCK = threading.Lock()   # ein Modell auf einer GPU: Anfragen nacheinander


@asynccontextmanager
async def lifespan(app):
    STATE["asr"] = Transcriber()
    yield
    STATE.clear()


app = FastAPI(title="Transkription", version="1.0", lifespan=lifespan)


@app.post("/transcribe")
def transcribe(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in AUDIO_EXTS:
        raise HTTPException(415, f"Dateityp {suffix or '(keiner)'} nicht unterstützt; erlaubt: {', '.join(sorted(AUDIO_EXTS))}")
    # die ASR-Pipeline liest über ffmpeg von einem Pfad
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
    try:
        with LOCK:
            return STATE["asr"].transcribe(tmp.name)
    except Exception as e:   # z.B. defekte Datei, ffmpeg-Fehler
        raise HTTPException(422, f"Transkription fehlgeschlagen: {e}") from None
    finally:
        os.unlink(tmp.name)


@app.get("/health")
def health():
    asr = STATE.get("asr")
    return {"status": "ok" if asr else "loading", "model": asr.model_id if asr else None, "device": asr.device if asr else None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("TRANSCRIPTION_HOST", "127.0.0.1"), port=int(os.environ.get("TRANSCRIPTION_PORT", "8001")))
