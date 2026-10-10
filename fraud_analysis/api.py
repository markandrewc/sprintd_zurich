"""Fraud-Analyse-Dienst (FastAPI). Lädt Kev bei der ersten Anfrage und entlädt es nach FRAUD_IDLE_SECONDS ohne Anfrage.

  python -m fraud_analysis.api          # -> http://127.0.0.1:8002  (Doku: /docs)

  POST /analyze   {"transcript": "...", "segments": [...]?, "threshold": 0.7?, "questions": {...}?}
                  -> Alarm, Risiko, Wert pro Check; für Checks ab der Schwelle die Fundstelle ("passage", siehe analysis.py)
                  segments: Abschnitte der Transkription mit Zeitstempeln [{"start", "end", "text", "speaker"?}]; fehlt
                  transcript, wird es aus den segments zusammengesetzt
  GET  /config    aktuelle Prüfpunkte, Schwelle und Version aus questions.json
  PUT  /questions {"questions": {"gesetzlich": {...}, "intern": {...}}}  Prüfpunkte ersetzen (geprüft, Version +1,
                  vorherige Fassung in questions_history/)
  POST /unload    Kev sofort von der GPU entladen (die nächste Analyse lädt es wieder, ~10 s)
  GET  /health    Dienst erreichbar; "loaded": ob Kev gerade auf der GPU liegt

questions.json wird bei jedem Aufruf neu gelesen: Änderungen gelten ohne Neustart.
Umgebungsvariablen: FRAUD_HOST (127.0.0.1), FRAUD_PORT (8002), FRAUD_IDLE_SECONDS (120; 0 = nie entladen),
dazu KEV_* aus runtime.py.
"""
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

from shared.model_slot import ModelSlot

from .analysis import analyze, load_config, save_questions
from .runtime import DEVICE, MODEL_REPO, Kev

KEV = ModelSlot("kev", loader=Kev, idle_seconds=float(os.environ.get("FRAUD_IDLE_SECONDS", "120")))

app = FastAPI(title="Fraud-Analyse", version="1.1")


class Segment(BaseModel):
    start: float | None = None          # Sekunden ab Anrufbeginn
    end: float | None = None
    text: str
    speaker: str | None = None          # folgt mit der Sprechererkennung


class AnalyzeRequest(BaseModel):
    transcript: str | None = None       # None: aus segments zusammengesetzt
    segments: list[Segment] | None = None
    threshold: float | None = None      # None: Schwelle aus questions.json
    questions: dict | None = None       # None: Fragen aus questions.json (Listen-Form oder flach)
    passage_words: int | None = None    # Länge der Fundstelle in Wörtern; None: localization.passage_words aus questions.json


@app.post("/analyze")
def post_analyze(req: AnalyzeRequest):
    segments = [s.model_dump() for s in req.segments] if req.segments else None
    transcript = req.transcript if req.transcript is not None else " ".join(s["text"] for s in segments or [])
    if not transcript.strip(): raise HTTPException(422, "Weder transcript noch segments enthalten Text")
    cfg = load_config()
    threshold = cfg["threshold"] if req.threshold is None else req.threshold
    try:
        with KEV.use() as kev:
            loc = {**cfg.get("localization", {}), **({"passage_words": req.passage_words} if req.passage_words else {})}
            result = analyze(kev, transcript, req.questions or cfg["questions"], threshold, segments=segments, localization=loc)
        result["questions_version"] = None if req.questions else cfg.get("version", 1)   # mit welchen Prüfpunkten analysiert
        return result
    except (ValueError, ValidationError) as e:   # z.B. Transkript zu lang, ungültige Frage
        raise HTTPException(422, str(e)) from None


@app.get("/config")
def get_config():
    return load_config()


class QuestionsRequest(BaseModel):
    questions: dict


@app.put("/questions")
def put_questions(req: QuestionsRequest):
    try:
        cfg = save_questions(req.questions)
    except (ValueError, ValidationError) as e:
        raise HTTPException(422, str(e)) from None
    return {"version": cfg["version"], "questions": cfg["questions"]}


@app.post("/unload")
def unload():
    return {"unloaded": KEV.unload()}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_REPO, "device": DEVICE, **KEV.status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("FRAUD_HOST", "127.0.0.1"), port=int(os.environ.get("FRAUD_PORT", "8002")))
