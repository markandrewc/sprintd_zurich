"""Fraud-Analyse-Dienst (FastAPI). Lädt Kev einmal beim Start und hält es auf der GPU.

  python -m fraud_analysis.api          # -> http://127.0.0.1:8002  (Doku: /docs)

  POST /analyze   {"transcript": "...", "threshold": 0.7?, "questions": {...}?}  -> Alarm, Risiko, Wert pro Check
  GET  /config    aktuelle Fragen und Schwelle aus questions.json
  GET  /health

questions.json wird bei jedem Aufruf neu gelesen: Änderungen gelten ohne Neustart.
Umgebungsvariablen: FRAUD_HOST (127.0.0.1), FRAUD_PORT (8002), dazu KEV_* aus runtime.py.
"""
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

from .analysis import analyze, load_config
from .runtime import Kev

STATE = {}
LOCK = threading.Lock()   # ein Modell auf einer GPU: Anfragen nacheinander


@asynccontextmanager
async def lifespan(app):
    STATE["kev"] = Kev()
    yield
    STATE.clear()


app = FastAPI(title="Fraud-Analyse", version="1.0", lifespan=lifespan)


class AnalyzeRequest(BaseModel):
    transcript: str
    threshold: float | None = None      # None: Schwelle aus questions.json
    questions: dict | None = None       # None: Fragen aus questions.json (Listen-Form oder flach)


@app.post("/analyze")
def post_analyze(req: AnalyzeRequest):
    if not req.transcript.strip(): raise HTTPException(422, "transcript ist leer")
    cfg = load_config()
    threshold = cfg["threshold"] if req.threshold is None else req.threshold
    try:
        with LOCK:
            return analyze(STATE["kev"], req.transcript, req.questions or cfg["questions"], threshold)
    except (ValueError, ValidationError) as e:   # z.B. Transkript zu lang, ungültige Frage
        raise HTTPException(422, str(e)) from None


@app.get("/config")
def get_config():
    return load_config()


@app.get("/health")
def health():
    kev = STATE.get("kev")
    return {"status": "ok" if kev else "loading", "model": kev.repo if kev else None, "device": kev.device if kev else None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("FRAUD_HOST", "127.0.0.1"), port=int(os.environ.get("FRAUD_PORT", "8002")))
