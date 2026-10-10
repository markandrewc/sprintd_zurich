"""Fraud-Analyse eines Transkripts mit Kev: ganzes Transkript rein, ein p(yes) pro Check raus.

Die Checks stehen in questions.json, in zwei Listen ("gesetzlich", "intern"). Das Risiko eines Anrufs ist das höchste
p(yes) über alle Checks; ab der Schwelle gibt es einen Alarm (geht zur manuellen Prüfung).
"""
import json
import re
from pathlib import Path

from .kev.api import SystemOneRequest

CONFIG = Path(__file__).parent / "questions.json"

SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")
TURN = re.compile(r"^(T\d{3})\s*·\s*(.+?)\s*$", re.M)   # Sprecher-Turn im Format der Inventx-Skripte: "T003 · Beratung"


def load_config(path=CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def flatten(questions):
    """{"gesetzlich": {id: frage}, "intern": {...}} -> {id: frage}; jede Frage bekommt ihre Liste als "source".
    Ein schon flaches {id: frage} (jede Frage hat "type") bleibt, wie es ist; die ganze Config ({"questions": ...})
    geht auch. Schlüssel mit "_" werden ignoriert. Unbrauchbare Struktur -> ValueError."""
    if isinstance(questions.get("questions"), dict):
        questions = questions["questions"]
    questions = {k: v for k, v in questions.items() if not k.startswith("_")}
    if all(isinstance(v, dict) and "type" in v for v in questions.values()):
        return questions
    flat = {}
    for source, qs in questions.items():
        if not isinstance(qs, dict) or not all(isinstance(q, dict) for q in qs.values()):
            raise ValueError(f"'{source}' ist weder eine Frage (mit \"type\") noch eine Liste von Fragen")
        flat.update({qid: {**q, "source": source} for qid, q in qs.items()})
    return flat


def prepare(text):
    """Das ganze Transkript als Text für Kev: eine Zeile pro Sprecher-Turn ("T003 Beratung: ...") beim Skript-Format,
    sonst ein Satz pro Zeile (z.B. Transkription)."""
    heads = list(TURN.finditer(text))
    if not heads:
        return "\n".join(s for s in SENTENCE_END.split(" ".join(text.split())) if s)
    ends = [h.start() for h in heads[1:]] + [len(text)]
    return "\n".join(f"{h[1]} {h[2]}: {' '.join(text[h.end():e].split())}" for h, e in zip(heads, ends))


def decide(risk, threshold):
    return risk >= threshold


def analyze(kev, transcript, questions, threshold):
    """Kev liest das ganze Transkript und beantwortet alle Checks in einem Forward-Pass.
    questions: Listen-Form oder flach (siehe flatten). -> Ergebnis-Dict, wie es POST /analyze zurückgibt."""
    checks = {qid: q for qid, q in flatten(questions).items() if q.get("type") == "noul"}
    if not checks: raise ValueError("Keine Checks (noul-Fragen) konfiguriert.")
    # Kev ignoriert category/basis/source; SystemOneRequest validiert type/instructions/criteria
    resp = kev.systemone(SystemOneRequest(state=prepare(transcript), questions=checks))
    rows = [{"id": qid, "p": a["noul"], "category": checks[qid].get("category", ""), "source": checks[qid].get("source", ""),
             "basis": checks[qid].get("basis", ""), "question": checks[qid].get("instructions", "")}
            for qid, a in resp["answers"].items()]
    rows.sort(key=lambda r: r["p"], reverse=True)
    risk = rows[0]["p"]
    return {"alert": decide(risk, threshold), "risk": risk, "threshold": threshold, "top_check": rows[0]["id"],
            "checks": rows, "model": resp["model"], "input_tokens": resp["usage"]["input_tokens"], "latency_ms": resp["latency_ms"]}
