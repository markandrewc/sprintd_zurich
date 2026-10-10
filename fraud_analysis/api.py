"""Fraud-Analyse-Dienst (FastAPI). Lädt Kev bei der ersten Anfrage und entlädt es nach FRAUD_IDLE_SECONDS ohne Anfrage.

  python -m fraud_analysis.api          # -> http://127.0.0.1:8002  (Doku: /docs)

  POST /analyze   {"transcript": "...", "segments": [...]?, "threshold": 0.7?, "passage_words": 25?}
                  -> Alarm, ausgelöste Regeln, p(yes) und ja/nein pro Fakt; für die Fakten ausgelöster Regeln die
                  Fundstelle ("passage", siehe analysis.py). segments: Abschnitte der Transkription mit Zeitstempeln
                  [{"start", "end", "text", "speaker"?}]; fehlt transcript, wird es aus den segments zusammengesetzt
  GET  /config    Fakten, Regeln, Schwelle und Version aus facts.json
  PUT  /config    {"facts": {...}, "rules": {...}}  ersetzen (geprüft, Version +1, vorherige Fassung in config_history/)
  POST /unload    Kev sofort von der GPU entladen (die nächste Analyse lädt es wieder, ~10 s)
  GET  /health    Dienst erreichbar; "loaded": ob Kev gerade auf der GPU liegt

facts.json wird bei jedem Aufruf neu gelesen: Änderungen gelten ohne Neustart.
Umgebungsvariablen: FRAUD_HOST (127.0.0.1), FRAUD_PORT (8002), FRAUD_IDLE_SECONDS (120; 0 = nie entladen),
dazu KEV_* aus runtime.py.
"""
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError

from shared.model_slot import ModelSlot

from .analysis import analyze, load_config
from .rules import save_config
from .runtime import DEVICE, MODEL_REPO, Kev

KEV = ModelSlot("kev", loader=Kev, idle_seconds=float(os.environ.get("FRAUD_IDLE_SECONDS", "120")))

app = FastAPI(title="Fraud-Analyse", version="2.0")


class Segment(BaseModel):
    start: float | None = None          # Sekunden ab Anrufbeginn
    end: float | None = None
    text: str
    speaker: str | None = None


class AnalyzeRequest(BaseModel):
    transcript: str | None = None       # None: aus segments zusammengesetzt
    segments: list[Segment] | None = None
    threshold: float | None = None      # None: Schwelle aus facts.json
    passage_words: int | None = None    # Länge der Fundstelle in Wörtern; None: localization.passage_words aus facts.json


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
            result = analyze(kev, transcript, cfg["facts"], cfg["rules"], threshold, segments=segments, localization=loc)
        result["config_version"] = cfg.get("version", 1)   # mit welchen Fakten und Regeln analysiert
        return result
    except (ValueError, ValidationError) as e:   # z.B. Transkript zu lang, ungültige Konfiguration
        raise HTTPException(422, str(e)) from None


@app.get("/config")
def get_config():
    return load_config()


class ConfigRequest(BaseModel):
    facts: dict
    rules: dict


@app.put("/config")
def put_config(req: ConfigRequest):
    try:
        cfg = save_config(req.facts, req.rules)
    except (ValueError, ValidationError) as e:
        raise HTTPException(422, str(e)) from None
    return {"version": cfg["version"], "facts": cfg["facts"], "rules": cfg["rules"]}


@app.post("/unload")
def unload():
    return {"unloaded": KEV.unload()}


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_REPO, "device": DEVICE, **KEV.status()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("FRAUD_HOST", "127.0.0.1"), port=int(os.environ.get("FRAUD_PORT", "8002")))
