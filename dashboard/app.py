"""Dashboard: Anrufe hochladen, Ergebnisse ansehen, Anrufe beurteilen (Labels für späteres Finetuning), Grundfakten
und Regeln pflegen. Web-Oberfläche (dashboard/web/) über eine JSON-API.

  python -m dashboard.app        # -> http://<diese-IP>:7860 (lauscht auf 0.0.0.0)

Braucht die zwei Dienste: transcription.api (Port 8001) und fraud_analysis.api (Port 8002). Hochgeladene Aufnahmen
werden im Hintergrund transkribiert und analysiert (worker.py); die Oberfläche fragt den Stand regelmässig ab.
Umgebungsvariablen: DASHBOARD_HOST (0.0.0.0), DASHBOARD_PORT (7860), TRANSCRIPTION_URL, FRAUD_URL, DASHBOARD_DATA.

API (alles JSON, Doku unter /api/docs):
  GET    /api/status                    Dienste erreichbar? Was läuft gerade im Hintergrund?
  GET    /api/calls                     Anrufe mit Urteil und ausgelösten Regeln, dazu Zähler
  POST   /api/calls                     Aufnahmen hochladen (multipart, Feld "files"); Prüfung startet im Hintergrund
  GET    /api/calls/{id}                ein Anruf mit Regeln, Bedingungen, Fundstellen, Transkript und Beurteilung
  GET    /api/calls/{id}/audio          die Aufnahme
  POST   /api/calls/{id}/reanalyze      mit den aktuellen Fakten und Regeln neu prüfen (gespeichertes Transkript)
  PUT    /api/calls/{id}/review         Beurteilung speichern
  DELETE /api/calls/{id}                Anruf endgültig löschen
  GET    /api/config                    Grundfakten, Regeln, Schwelle, Länge der Fundstelle
  PUT    /api/config                    Grundfakten und Regeln ersetzen (über den Fraud-Analyse-Dienst, geprüft, versioniert)
  PUT    /api/settings                  Schwelle und Länge der Fundstelle
  GET    /api/preview?threshold=0.6     wie viele Anrufe mit dieser Schwelle einen Alarm hätten
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from fraud_analysis import client as fraud
from transcription import client as asr

from . import store, views, worker

WEB = Path(__file__).parent / "web"


@asynccontextmanager
async def lifespan(_):
    worker.start()
    # Was beim letzten Beenden noch in Arbeit war, wieder einreihen
    stuck = [c for c in store.list_calls() if c["status"] == "in_arbeit"]
    again = [c["id"] for c in stuck if c.get("transcript")]
    fresh = [c["id"] for c in stuck if not c.get("transcript")]
    if again: worker.submit("reanalyze", again)
    if fresh: worker.submit("process", fresh)
    yield


app = FastAPI(title="Sherlock Phones", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)


def get(cid):
    call = store.get_call(cid)
    if call is None: raise HTTPException(404, f"Anruf {cid} gibt es nicht")
    return call


@app.get("/api/status")
def status():
    def state(h): return "ok" if h.get("status") == "ok" else "offline" if h.get("status") == "offline" else "starting"
    return {"transcription": state(asr.health()), "analysis": state(fraud.health()), "worker": worker.progress()}


@app.get("/api/calls")
def calls():
    cfg = views.config(); th = views.threshold(cfg)
    rows = [views.summary(c, th, cfg) for c in store.list_calls()]
    return {"calls": rows, "threshold": th,
            "counts": {"all": len(rows), "alarm": sum(r["verdict"] == "alarm" for r in rows),
                       "open": sum(r["status"] == "fertig" and r["label"] is None for r in rows)}}


@app.post("/api/calls")
async def upload(files: list[UploadFile] = File(...)):
    if not files: raise HTTPException(422, "Keine Dateien")
    ids = [store.add_call(Path(f.filename or "aufnahme").name, await f.read()) for f in files]
    worker.submit("process", ids)
    return {"ids": ids}


@app.get("/api/calls/{cid}")
def call_detail(cid: int):
    cfg = views.config()
    return views.detail(get(cid), views.threshold(cfg), cfg)


@app.get("/api/calls/{cid}/audio")
def audio(cid: int):
    call = get(cid)
    if not Path(call["audio_path"]).is_file(): raise HTTPException(404, "Aufnahme fehlt")
    return FileResponse(call["audio_path"])


@app.post("/api/calls/{cid}/reanalyze")
def reanalyze(cid: int):
    if not get(cid).get("transcript"): raise HTTPException(422, "Dieser Anruf hat kein Transkript.")
    worker.submit("reanalyze", [cid])
    return {"ok": True}


class Review(BaseModel):
    label: str
    checks: dict[str, bool] = {}
    missed: list[str] = []
    comment: str = ""
    name: str = ""


@app.put("/api/calls/{cid}/review")
def review(cid: int, r: Review):
    if r.label not in store.LABELS: raise HTTPException(422, "Bitte eine Beurteilung wählen.")
    if not r.name.strip(): raise HTTPException(422, "Bitte Ihren Namen angeben.")
    call = get(cid)
    cfg = views.config()
    ev = views.evaluation(call, views.threshold(cfg), cfg)
    allowed = {f["id"] for f in views.findings(ev)}
    checks = {f: ok for f, ok in r.checks.items() if f in allowed}
    confirmed = [ev["rules"][rid]["name"] for rid in ev["fired"]
                 if all(checks.get(f) for f, v in ev["rules"][rid]["conditions"].items() if v == "ja")] if ev else []
    store.save_label(cid, r.label, checks, r.missed, sorted(set(confirmed) | set(r.missed)), r.comment, r.name.strip())
    return {"ok": True}


@app.delete("/api/calls/{cid}")
def delete(cid: int):
    get(cid)
    store.delete_call(cid)
    return {"ok": True}


@app.get("/api/config")
def get_config():
    cfg = views.config()
    return {"facts": cfg["facts"], "rules": cfg["rules"], "version": cfg.get("version", 1),
            "threshold": views.threshold(cfg), "passage_words": views.passage_words(cfg)}


class Config(BaseModel):
    facts: dict
    rules: dict


@app.put("/api/config")
def put_config(c: Config):
    try: res = fraud.save_config(c.facts, c.rules)
    except RuntimeError as e: raise HTTPException(422, str(e)) from None
    return {"version": res["version"]}


class Settings(BaseModel):
    threshold: float | None = None
    passage_words: int | None = None


@app.put("/api/settings")
def settings(s: Settings):
    if s.threshold is not None:
        if not 0 <= s.threshold <= 1: raise HTTPException(422, "Die Schwelle liegt zwischen 0 und 1.")
        store.set_setting("threshold", s.threshold)
    if s.passage_words is not None:
        if not 5 <= s.passage_words <= 200: raise HTTPException(422, "Zwischen 5 und 200 Wörtern.")
        store.set_setting("passage_words", s.passage_words)
    return {"ok": True}


@app.get("/api/preview")
def preview(threshold: float):
    cfg = views.config()
    done = [c for c in store.list_calls() if c["status"] == "fertig"]
    alarms = sum(bool((ev := views.evaluation(c, threshold, cfg)) and ev["fired"]) for c in done)
    return {"alarms": alarms, "done": len(done)}


app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index():
    return FileResponse(WEB / "index.html", headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("DASHBOARD_HOST", "0.0.0.0"), port=int(os.environ.get("DASHBOARD_PORT", "7860")),
                log_level="warning")
