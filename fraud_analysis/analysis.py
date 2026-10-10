"""Fraud-Analyse eines Transkripts mit Kev.

Entscheid: Kev liest das ganze Transkript, ein p(yes) pro Check. Das Risiko eines Anrufs ist das höchste p(yes) über
alle Checks; ab der Schwelle gibt es einen Alarm (geht zur manuellen Prüfung). Lokalisierung: für jeden Check ab der
Schwelle sucht ein gleitender Kev über überlappende Fenster den Kontext und grenzt darin die Stelle auf ~passage_words
Wörter (~10 s) ein, mit Zeitstempeln aus den Abschnitten der Transkription. Die Checks stehen in questions.json, in zwei Listen ("gesetzlich", "intern").
"""
import json
import os
import re
from pathlib import Path

from .kev.api import Noul, SystemOneRequest

CONFIG = Path(__file__).parent / "questions.json"

SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")
TURN = re.compile(r"^(T\d{3})\s*·\s*(.+?)\s*$", re.M)   # Sprecher-Turn im Format der Inventx-Skripte: "T003 · Beratung"


def load_config(path=CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


HISTORY = Path(__file__).parent / "questions_history"   # frühere Fassungen von questions.json, eine pro Version
QID = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


def validate_questions(questions):
    """Prüfpunkte in Listen-Form {liste: {id: prüfpunkt}} prüfen und bereinigen (type = noul, leere criteria weg).
    -> bereinigte Form. ValueError mit einer Meldung, die man ohne Code-Kenntnis versteht."""
    if not isinstance(questions, dict): raise ValueError("Prüfpunkte fehlen")
    clean, seen = {}, set()
    for source, qs in questions.items():
        if source.startswith("_"): continue
        if not isinstance(qs, dict): raise ValueError(f"Liste '{source}' enthält keine Prüfpunkte")
        clean[source] = {}
        for qid, q in qs.items():
            if not QID.match(qid): raise ValueError(f"ID '{qid}': nur Kleinbuchstaben, Ziffern und _, z.B. insider_trading")
            if qid in seen: raise ValueError(f"ID '{qid}' kommt mehrfach vor")
            seen.add(qid)
            if not str(q.get("instructions", "")).strip(): raise ValueError(f"Prüfpunkt '{qid}': die Frage fehlt")
            crit = {k: str(v).strip() for k, v in (q.get("criteria") or {}).items() if k in ("true", "false") and str(v).strip()}
            q = {k: v for k, v in q.items() if k != "criteria"} | {"type": "noul"} | ({"criteria": crit} if crit else {})
            Noul.model_validate({k: q[k] for k in ("type", "instructions", "criteria") if k in q})
            clean[source][qid] = q
    if not seen: raise ValueError("Mindestens ein Prüfpunkt ist nötig")
    return clean


def save_questions(questions, path=CONFIG):
    """Ersetzt die Prüfpunkte in questions.json, zählt "version" hoch und legt die vorherige Fassung in
    questions_history/ ab. Schwelle und localization bleiben. -> neue Config."""
    cfg = load_config(path)
    clean = validate_questions(questions)
    version = int(cfg.get("version", 1))
    HISTORY.mkdir(exist_ok=True)
    (HISTORY / f"questions_v{version}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    new = {k: v for k, v in cfg.items() if k not in ("version", "questions")} | {"version": version + 1, "questions": clean}
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)   # atomar: eine laufende Analyse liest nie eine halb geschriebene Datei
    return new


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


def units(transcript, segments=None):
    """-> Einheiten [{start, end, speaker, words}]: mit segments eine pro Abschnitt der Transkription, sonst eine pro
    Zeile von prepare(transcript) ohne Zeitstempel (beim Skript-Format ist "T003 Beratung" der Sprecher)."""
    if segments:
        return [{"start": s.get("start"), "end": s.get("end"), "speaker": s.get("speaker"), "words": s["text"].split()}
                for s in segments if s.get("text", "").strip()]
    out = []
    for line in prepare(transcript).split("\n"):
        m = re.match(r"^(T\d{3} [^:]+):\s*(.*)$", line)
        words = (m[2] if m else line).split()
        if words: out.append({"start": None, "end": None, "speaker": m[1] if m else None, "words": words})
    return out


def render(items, i=0, j=None, skip=frozenset()):
    """Text der Einheiten i..j-1 für Kev, eine Zeile pro Einheit ("Sprecher 1: ..."); skip: (einheit, wort) weglassen."""
    lines = []
    for k in range(i, len(items) if j is None else j):
        words = [w for n, w in enumerate(items[k]["words"]) if (k, n) not in skip]
        if words: lines.append(f"{items[k]['speaker']}: {' '.join(words)}" if items[k]["speaker"] else " ".join(words))
    return "\n".join(lines)


def word_time(unit, n, end=False):
    """Geschätzte Zeit von Wort n: die Wörter eines Abschnitts gleichmässig über seine Dauer verteilt."""
    if unit["start"] is None or unit["end"] is None: return None
    return round(unit["start"] + (unit["end"] - unit["start"]) * (n + end) / len(unit["words"]), 2)


def windows(items, words, overlap):
    """Überlappende Fenster aus ganzen Einheiten, je ~words Wörter, Schritt ~words - overlap. -> [(i, j)] (j exklusiv)."""
    sizes = [len(u["words"]) for u in items]
    out, i = [], 0
    while i < len(items):
        j, n = i, 0
        while j < len(items) and (n < words or j == i):
            n += sizes[j]; j += 1
        out.append((i, j))
        if j >= len(items): break
        k, dropped = i, 0
        while k < j - 1 and dropped < words - overlap:
            dropped += sizes[k]; k += 1
        i = max(k, i + 1)
    return out


def ask(kev, state, checks):
    return {qid: a["noul"] for qid, a in kev.systemone(SystemOneRequest(state=state, questions=checks))["answers"].items()}


def localize(kev, items, checks, words=40, overlap=20, passage_words=25):
    """Wo im Anruf liegt der Befund? Entscheidet nichts, findet nur die Stelle.
    1. Kontext: gleitende Fenster von ~words Wörtern; pro Check das Fenster mit dem höchsten p(yes).
    2. Eingrenzen: im besten Fenster nacheinander je passage_words Wörter weglassen; die Wörter, ohne die p(yes) am
       stärksten fällt, sind die Fundstelle. Ihre Zeiten sind geschätzt (word_time).
    -> {check: {"start", "end", "text", "p", "drop", "units": [erste, letzte], "context", "context_start", "context_end"}}."""
    best = {}
    for i, j in windows(items, words, overlap):
        for qid, p in ask(kev, render(items, i, j), checks).items():
            if qid not in best or p > best[qid][0]: best[qid] = (p, i, j)
    groups = {}
    for qid, (p, i, j) in best.items(): groups.setdefault((i, j), []).append(qid)
    out = {}
    for (i, j), qids in groups.items():
        flat = [(k, n) for k in range(i, j) for n in range(len(items[k]["words"]))]
        size = max(1, min(passage_words, len(flat)))
        drop = {q: (0.0, 0) for q in qids}
        if size < len(flat):
            step = max(1, size // 3)
            starts = list(range(0, len(flat) - size + 1, step))
            if starts[-1] != len(flat) - size: starts.append(len(flat) - size)
            for s0 in starts:
                ps = ask(kev, render(items, i, j, frozenset(flat[s0:s0 + size])), {q: checks[q] for q in qids})
                for q, p in ps.items():
                    if best[q][0] - p > drop[q][0]: drop[q] = (best[q][0] - p, s0)
        for q in qids:
            d, s0 = drop[q]
            sel = flat[s0:s0 + size]
            keep = frozenset(flat) - frozenset(sel)
            (k0, n0), (k1, n1) = sel[0], sel[-1]
            out[q] = {"start": word_time(items[k0], n0), "end": word_time(items[k1], n1, end=True),
                      "text": render(items, k0, k1 + 1, keep), "p": best[q][0], "drop": round(d, 4), "units": [k0, k1],
                      "context": render(items, i, j), "context_start": items[i]["start"], "context_end": items[j - 1]["end"]}
    return out


def analyze(kev, transcript, questions, threshold, segments=None, localization=None):
    """1. Kev liest das ganze Transkript und beantwortet alle Checks in einem Forward-Pass (Entscheid).
    2. Für jeden Check ab der Schwelle sucht der gleitende Kev die Stelle (localize); sie steht als "passage" am Check.
    questions: Listen-Form oder flach (siehe flatten). segments: Abschnitte der Transkription [{start, end, speaker,
    text}]; ohne sie wird der Text aus transcript gebildet und die Stellen haben keine Zeitstempel.
    localization: {"window_words", "overlap_words", "passage_words"} (Default 40 / 20 / 25).
    -> Ergebnis-Dict, wie es POST /analyze zurückgibt."""
    checks = {qid: q for qid, q in flatten(questions).items() if q.get("type") == "noul"}
    if not checks: raise ValueError("Keine Checks (noul-Fragen) konfiguriert.")
    items = units(transcript, segments)
    # Kev ignoriert category/basis/source; SystemOneRequest validiert type/instructions/criteria
    resp = kev.systemone(SystemOneRequest(state=render(items), questions=checks))
    rows = [{"id": qid, "p": a["noul"], "category": checks[qid].get("category", ""), "source": checks[qid].get("source", ""),
             "basis": checks[qid].get("basis", ""), "question": checks[qid].get("instructions", ""), "passage": None}
            for qid, a in resp["answers"].items()]
    rows.sort(key=lambda r: r["p"], reverse=True)
    fired = {r["id"]: checks[r["id"]] for r in rows if decide(r["p"], threshold)}
    if fired:
        loc = localization or {}
        passages = localize(kev, items, fired, int(loc.get("window_words", 40)), int(loc.get("overlap_words", 20)),
                            int(loc.get("passage_words", 25)))
        for r in rows: r["passage"] = passages.get(r["id"])
    risk = rows[0]["p"]
    return {"alert": decide(risk, threshold), "risk": risk, "threshold": threshold, "top_check": rows[0]["id"],
            "checks": rows, "model": resp["model"], "input_tokens": resp["usage"]["input_tokens"], "latency_ms": resp["latency_ms"]}
