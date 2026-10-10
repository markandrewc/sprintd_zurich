"""Was das Dashboard anzeigt, berechnet aus der Ablage (store.py) und den Fakten und Regeln (fraud_analysis/facts.json).

Kev hat pro Anruf jeden Fakt mit p(yes) beantwortet; die Werte sind gespeichert. Ein Fakt ist ja ab der Schwelle (eine
für alle, Einstellung des Dashboards). Eine Regel legt pro Fakt ja oder nein fest (übrige egal) und löst aus, wenn alle
Bedingungen erfüllt sind; mindestens eine -> Alarm. Ändert man Schwelle oder Regeln über bestehende Fakten, ergibt sich
das neue Urteil ohne neue Analyse.
"""
import json
from pathlib import Path

from fraud_analysis import client as fraud
from fraud_analysis.rules import fired_rules, met

from . import store

CONFIG_FILE = Path(__file__).resolve().parent.parent / "fraud_analysis" / "facts.json"
MERGE_GAP = 2.0   # Sekunden: Fundstellen, die sich überlappen oder näher beieinander liegen, werden eine Stelle


def config():
    """Fakten, Regeln und Default-Schwelle vom Analyse-Dienst; ist er nicht erreichbar, direkt aus der Datei."""
    try:
        cfg = fraud.config()
        if "rules" in cfg and "facts" in cfg: return cfg
    except Exception:
        pass
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def threshold(cfg):
    return store.get_setting("threshold", cfg.get("threshold", 0.7))


def passage_words(cfg):
    return store.get_setting("passage_words", cfg.get("localization", {}).get("passage_words", 25))


def evaluation(call, th, cfg):
    """-> {"facts": {id: fakt}, "p": {id: p}, "rules": {id: regel}, "fired": [regel-id]} oder None (nicht fertig oder mit
    den früheren Prüfpunkten analysiert). Es gelten die aktuellen Regeln, deren Fakten alle einen gespeicherten Wert
    haben; sonst die Regeln vom Zeitpunkt der Analyse."""
    a = call.get("analysis") if call["status"] == "fertig" else None
    if not a or "facts" not in a: return None
    p = {f["id"]: f["p"] for f in a["facts"]}
    rules = ({rid: r for rid, r in cfg["rules"].items() if all(f in p for f in r["conditions"])}
             or {r["id"]: r for r in a["rules"] if "conditions" in r})
    return {"facts": {f["id"]: f for f in a["facts"]}, "p": p, "rules": rules, "fired": fired_rules(p, rules, th)}


def verdict(call, ev):
    """alarm | ok | busy | error | stale (mit den früheren Prüfpunkten analysiert, neu prüfen)."""
    if call["status"] == "in_arbeit": return "busy"
    if call["status"] == "fehler": return "error"
    if ev is None: return "stale"
    return "alarm" if ev["fired"] else "ok"


def findings(ev):
    """Die Fakten, die in ausgelösten Regeln ja sein müssen, je einmal, in der Reihenfolge der Regeln."""
    if not ev: return []
    ids = dict.fromkeys(f for rid in ev["fired"] for f, v in ev["rules"][rid]["conditions"].items() if v == "ja")
    return [ev["facts"][f] for f in ids if f in ev["facts"]]


def regions(ev):
    """Fundstellen der Befund-Fakten, überlappende zu einer Stelle zusammengefasst, nach Zeit sortiert.
    -> [{"n", "start", "end", "facts": [fakt, ...], "text"?}]. Fakten ohne Zeitangabe bilden je eine eigene Stelle."""
    found = findings(ev)
    timed = sorted((f for f in found if f.get("passage") and f["passage"].get("start") is not None), key=lambda f: f["passage"]["start"])
    out = []
    for f in timed:
        p = f["passage"]
        if out and p["start"] <= out[-1]["end"] + MERGE_GAP:
            out[-1]["end"] = max(out[-1]["end"], p["end"]); out[-1]["facts"].append(f)
        else:
            out.append({"start": p["start"], "end": p["end"], "facts": [f]})
    for f in found:
        if f.get("passage") and f["passage"].get("start") is None:
            out.append({"start": None, "end": None, "facts": [f], "text": f["passage"]["text"]})
    for n, r in enumerate(out, 1): r["n"] = n
    return out


def region_text(call, r):
    """Text der Stelle aus den Abschnitten: die Wörter, deren geschätzte Zeit in [start, end] liegt (die Wörter eines
    Abschnitts gleichmässig über seine Dauer verteilt, wie bei der Lokalisierung)."""
    if r.get("text") is not None: return r["text"]
    lines = []
    for s in call.get("segments") or []:
        words = s["text"].split()
        if not words or s.get("start") is None or s["end"] <= r["start"] or s["start"] >= r["end"]: continue
        step = (s["end"] - s["start"]) / len(words)
        keep = [w for i, w in enumerate(words) if r["start"] <= s["start"] + (i + 0.5) * step <= r["end"]]
        if keep: lines.append({"speaker": s.get("speaker"), "text": " ".join(keep)})
    return lines


def summary(call, th, cfg):
    ev = evaluation(call, th, cfg)
    return {"id": call["id"], "created_at": call["created_at"], "filename": call["filename"], "status": call["status"],
            "verdict": verdict(call, ev), "rules": [ev["rules"][rid]["name"] for rid in ev["fired"]] if ev else [],
            "label": call["label"]}


def detail(call, th, cfg):
    ev = evaluation(call, th, cfg)
    regs = regions(ev)
    where = {f["id"]: r["n"] for r in regs for f in r["facts"]}
    rules = []
    if ev:
        for rid, r in ev["rules"].items():
            conds = [{"fact": fid, "label": ev["facts"][fid]["label"], "question": ev["facts"][fid]["question"], "want": want,
                      "p": ev["p"][fid], "yes": ev["p"][fid] >= th, "met": met(ev["p"], fid, want, th), "region": where.get(fid)}
                     for fid, want in r["conditions"].items() if fid in ev["facts"]]
            rules.append({"id": rid, "name": r["name"], "fired": rid in ev["fired"], "conditions": conds})
        rules.sort(key=lambda r: (not r["fired"], -sum(c["met"] for c in r["conditions"]) / max(1, len(r["conditions"]))))
    segs = call.get("segments") or []
    hit = [i for i, s in enumerate(segs) if s.get("start") is not None
           and any(r["start"] is not None and s["start"] < r["end"] and s["end"] > r["start"] for r in regs)]
    return {**summary(call, th, cfg), "error": call.get("error"), "threshold": th,
            "audio": bool(call.get("audio_path")) and Path(call["audio_path"]).is_file(),
            "transcript": call.get("transcript") or "", "segments": segs, "highlight": hit, "rules": rules,
            "regions": [{"n": r["n"], "start": r["start"], "end": r["end"], "facts": [f["label"] for f in r["facts"]],
                         "lines": region_text(call, r) if r.get("text") is None else [{"speaker": None, "text": r["text"]}]}
                        for r in regs],
            "findings": [{"id": f["id"], "label": f["label"], "region": where.get(f["id"])} for f in findings(ev)],
            "review": {"label": call["label"], "checks": call["label_checks"] or {}, "missed": call["label_missed"] or [],
                       "comment": call["label_comment"] or "", "labeled_by": call["labeled_by"] or "",
                       "labeled_at": call["labeled_at"]}}
