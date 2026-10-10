"""
Trainingsdaten für Kev aus unseren Quellen, im Format von kev.train --data (kev.data.load_records):

  - Gespräche: finetuning/data/synthetic/batch_*.jsonl ({"turns", "labels": {fakt: bool}, "alarm": bool|null})
  - Beurteilungen aus dem Dashboard (finetuning.export_labels), sobald es Fakten-Labels liefert

Die Fragen sind die Fakten aus fraud_analysis/facts.json (hierarchische Prüfung: Fakten -> UND-Regeln -> Alarm). Ein
Gespräch muss nicht alle Fakten gelabelt haben; Kev lernt nur die vorhandenen. Fakten, die über alle Daten nur ja oder
nur nein haben, werden weggelassen (sonst lernt Kev, immer dasselbe zu antworten). Der Text wird genau so gebaut wie
bei der Analyse (fraud_analysis.analysis.units/render), damit Kev im Training dasselbe sieht wie im Einsatz.

  python -m finetuning.build_dataset              # -> outputs/finetuning/kev_train.jsonl und kev_val.jsonl
  python -m finetuning.build_dataset --val 0.2    # Anteil für die Validierung (Default 0.15)
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

from fraud_analysis.analysis import render, units

ROOT = Path(__file__).resolve().parent.parent
SYNTHETIC = ROOT / "finetuning" / "data" / "synthetic"
OUT = ROOT / "outputs" / "finetuning"
FACTS = ROOT / "fraud_analysis" / "facts.json"


def load_facts():
    return {k: v for k, v in json.loads(FACTS.read_text(encoding="utf-8"))["facts"].items() if not k.startswith("_")}


def turns_to_segments(turns):
    """Synthetische Beiträge -> Abschnitte wie aus der Transkription: Sprecher in Reihenfolge des ersten Auftretens
    als "Sprecher 1", "Sprecher 2" (so benennt die Sprechererkennung), ohne Zeitstempel."""
    names = {}
    return [{"speaker": f"Sprecher {names.setdefault(t['speaker'], len(names) + 1)}", "text": t["text"]} for t in turns]


def record(segments, labels, facts, source, ref, alarm=None):
    """-> Trainingsbeispiel oder None. Nur Fakten, für die ein Label vorliegt; alarm (Sollurteil des Anrufs, None =
    unbekannt/review) geht in _meta für die Auswertung."""
    qs = {f: {"type": "noul", "instructions": q["instructions"], "label": bool(labels[f])}
          for f, q in facts.items() if isinstance(labels.get(f), bool)}
    state = render(units("", segments))
    if not qs or not state.strip(): return None
    return {"state": state, "questions": qs, "_meta": {"origin": source, "ref": ref, "alarm": alarm}}


def synthetic_records(facts):
    for path in sorted(SYNTHETIC.glob("batch_*.jsonl")):
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        unknown = {k for r in rows for k in r.get("labels", {})} - set(facts)
        if unknown: print(f"{path.name}: Labels ohne passenden Fakt werden ignoriert: {sorted(unknown)}")
        for n, r in enumerate(rows, 1):
            rec = record(turns_to_segments(r["turns"]), r["labels"], facts, "synthetisch", f"{path.name}:{n}", r.get("alarm"))
            if rec: yield rec


def dashboard_records(facts):
    from finetuning.export_labels import records   # Dashboard-Datenbank; fehlt sie, gibt es einfach keine Beispiele
    for r in records():
        if not set(r["check_labels"]) <= set(facts):   # mit den früheren Prüfpunkten beurteilt
            print(f"übersprungen: Anruf {r['call_id']} hat Labels für andere Fragen als die aktuellen Fakten")
            continue
        rec = record(r["segments"] or [{"text": r["transcript"]}], r["check_labels"], facts, "dashboard", f"Anruf {r['call_id']}",
                     r.get("alarm"))
        if rec: yield rec


def one_class(recs, facts):
    """Fakten, die über alle Beispiele nur ja oder nur nein haben."""
    seen = {f: {q["label"] for r in recs for qid, q in r["questions"].items() if qid == f} for f in facts}
    return sorted(f for f, v in seen.items() if len(v) == 1)


def is_val(rec, share):
    """Feste Zuteilung nach dem Text: ein Gespräch landet bei jedem Lauf in derselben Hälfte."""
    h = int(hashlib.sha256(rec["state"].encode()).hexdigest()[:8], 16)
    return h / 0xFFFFFFFF < share


def build(val_share=0.15, out=OUT):
    facts = {f: q for f, q in load_facts().items() if q.get("type") == "noul"}
    recs = list(synthetic_records(facts)) + list(dashboard_records(facts))
    drop = one_class(recs, facts)
    if drop:
        print(f"weggelassen (nur eine Klasse in den Daten): {drop}")
        for r in recs: r["questions"] = {f: q for f, q in r["questions"].items() if f not in drop}
        recs = [r for r in recs if r["questions"]]
    out.mkdir(parents=True, exist_ok=True)
    train = [r for r in recs if not is_val(r, val_share)]
    val = [r for r in recs if is_val(r, val_share)]
    for name, part in (("kev_train.jsonl", train), ("kev_val.jsonl", val)):
        with (out / name).open("w", encoding="utf-8") as fh:
            for r in part: fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    origin = Counter(r["_meta"]["origin"] for r in recs)
    print(f"{len(recs)} Beispiele ({dict(origin)}): {len(train)} Training, {len(val)} Validierung -> {out}")
    for name, part in (("Training", train), ("Validierung", val)):
        pos = Counter(f for r in part for f, q in r["questions"].items() if q["label"])
        neg = Counter(f for r in part for f, q in r["questions"].items() if not q["label"])
        print(f"{name} ja/nein pro Fakt: " + ", ".join(f"{f} {pos[f]}/{neg[f]}" for f in facts if pos[f] or neg[f]))
    return out / "kev_train.jsonl", out / "kev_val.jsonl"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--val", type=float, default=0.15, help="Anteil für die Validierung")
    build(ap.parse_args().val)


if __name__ == "__main__":
    main()
