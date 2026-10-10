"""Fraud-Analyse eines Transkripts mit Kev, hierarchisch: Fakten -> Regeln -> Alarm (Konfiguration: facts.json).

Entscheid: Kev liest das ganze Transkript und beantwortet jeden Grundfakt (Ja/Nein-Frage) mit einem p(yes). Ein Fakt
ist ja, wenn p die Schwelle erreicht (eine für alle). Eine Regel legt pro Fakt ja, nein oder egal fest und löst aus,
wenn alle Bedingungen erfüllt sind; löst mindestens eine aus, gibt es einen Alarm (geht zur manuellen Prüfung).
Lokalisierung: für die Fakten, die in ausgelösten Regeln ja sein müssen, sucht ein
gleitender Kev über überlappende Fenster den Kontext und grenzt darin die Stelle auf ~passage_words Wörter (~10 s) ein,
mit Zeitstempeln aus den Abschnitten der Transkription.
"""
import re

from .kev.api import SystemOneRequest
from .rules import fired_rules, load_config, validate   # noqa: F401  (load_config für api.py)

SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")
TURN = re.compile(r"^(T\d{3})\s*·\s*(.+?)\s*$", re.M)   # Sprecher-Turn im Format der Inventx-Skripte: "T003 · Beratung"


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


def analyze(kev, transcript, facts, rules, threshold, segments=None, localization=None):
    """1. Kev liest das ganze Transkript und beantwortet alle Fakten in einem Durchgang.
    2. Fakten ab der Schwelle sind ja; Regeln, deren Bedingungen (ja/nein pro Fakt) alle erfüllt sind, lösen aus;
       mindestens eine -> Alarm.
    3. Für die Fakten, die in ausgelösten Regeln ja sein müssen, sucht der gleitende Kev die Stelle (localize); sie
       steht als "passage" am Fakt. (Was nein sein muss, hat keine Stelle.)
    segments: Abschnitte der Transkription [{start, end, speaker, text}]; ohne sie wird der Text aus transcript gebildet
    und die Stellen haben keine Zeitstempel. localization: {"window_words", "overlap_words", "passage_words"}.
    -> Ergebnis-Dict, wie es POST /analyze zurückgibt (Fakten und Regeln in der Reihenfolge der Konfiguration)."""
    facts, rules = validate(facts, rules)
    qs = {fid: {"type": "noul", "instructions": f["instructions"]} for fid, f in facts.items()}
    items = units(transcript, segments)
    resp = kev.systemone(SystemOneRequest(state=render(items), questions=qs))
    p = {fid: a["noul"] for fid, a in resp["answers"].items()}
    fired = fired_rules(p, rules, threshold)
    involved = {f: qs[f] for rid in fired for f, v in rules[rid]["conditions"].items() if v == "ja"}
    passages = {}
    if involved:
        loc = localization or {}
        passages = localize(kev, items, involved, int(loc.get("window_words", 40)), int(loc.get("overlap_words", 20)),
                            int(loc.get("passage_words", 25)))
    return {"alert": bool(fired), "threshold": threshold, "fired": fired,
            "facts": [{"id": fid, "label": f["label"], "question": f["instructions"], "p": p[fid], "yes": p[fid] >= threshold,
                       "passage": passages.get(fid)} for fid, f in facts.items()],
            "rules": [{"id": rid, **r, "fired": rid in fired} for rid, r in rules.items()],
            "model": resp["model"], "input_tokens": resp["usage"]["input_tokens"], "latency_ms": resp["latency_ms"]}
