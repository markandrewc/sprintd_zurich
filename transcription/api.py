"""Transkriptions-Dienst (FastAPI). Lädt das ASR-Modell bei der ersten Anfrage und entlädt es nach
TRANSCRIPTION_IDLE_SECONDS ohne Anfrage.

  python -m transcription.api           # -> http://127.0.0.1:8001  (Doku: /docs)

  POST /transcribe   Audiodatei (multipart, Feld "file")
                     -> {"text", "segments": [{"start", "end", "speaker", "text"}], "seconds"}  (Ablauf: siehe asr.py)
  POST /unload       Modelle sofort von der GPU entladen (die nächste Transkription lädt sie wieder, ~5 s)
  GET  /health       Dienst erreichbar; "loaded": ob das Modell gerade auf der GPU liegt

Umgebungsvariablen: TRANSCRIPTION_HOST (127.0.0.1), TRANSCRIPTION_PORT (8001), TRANSCRIPTION_IDLE_SECONDS (120; 0 = nie
entladen), dazu ASR_* aus asr.py.
"""
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile

from shared.model_slot import ModelSlot

from .asr import AUDIO_EXTS, DIARIZATION_ID, MODEL_ID, Transcriber

ASR = ModelSlot("asr", loader=Transcriber, idle_seconds=float(os.environ.get("TRANSCRIPTION_IDLE_SECONDS", "120")))

app = FastAPI(title="Transkription", version="1.1")


@app.post("/transcribe")
def transcribe(file: UploadFile):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in AUDIO_EXTS:
        raise HTTPException(415, f"Dateityp {suffix or '(keiner)'} nicht unterstützt; erlaubt: {', '.join(sorted(AUDIO_EXTS))}")
    # die ASR-Pipeline liest über ffmpeg von einem Pfad
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
    try:
        with ASR.use() as asr:
            return asr.transcribe(tmp.name)
    except Exception as e:   # z.B. defekte Datei, ffmpeg-Fehler
        raise HTTPException(422, f"Transkription fehlgeschlagen: {e}") from None
    finally:
        os.unlink(tmp.name)


@app.post("/unload")
def unload():
    return {"unloaded": ASR.unload()}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_ID, "diarization": DIARIZATION_ID, **ASR.status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("TRANSCRIPTION_HOST", "127.0.0.1"), port=int(os.environ.get("TRANSCRIPTION_PORT", "8001")))
