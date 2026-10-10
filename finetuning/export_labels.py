"""
Export der im Dashboard beurteilten Anrufe als Trainingsdaten.

  python -m finetuning.export_labels                 # -> outputs/finetuning/labels.jsonl

Eine Zeile pro beurteiltem Anruf: Transkript mit Abschnitten, Beurteilung, Kevs Scores zum Zeitpunkt der Analyse und
abgeleitete Labels:
  check_labels    Ja/Nein pro Check. Ein Befund, den die Prüferin als korrekt angehakt hat = true, nicht angehakt = false;
                  Checks einer als übersehen markierten Kategorie = true; alle übrigen = false.
                  Bei "Kein Verstoss" sind alle Checks false. "Unklar" wird nicht exportiert (kein verlässliches Label).
  passage_labels  pro Befund die Fundstelle des gleitenden Kev mit korrekt/falsch (Material für die Lokalisierung)
Die Checks und ihre Kategorien kommen aus fraud_analysis/questions.json.
"""
import json
import sys
from pathlib import Path

from dashboard import store

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "finetuning" / "labels.jsonl"


def check_categories():
    cfg = json.loads((ROOT / "fraud_analysis" / "questions.json").read_text(encoding="utf-8"))
    return {qid: q.get("category", qid) for source, qs in cfg["questions"].items() for qid, q in qs.items()}


def records():
    checks = check_categories()
    for c in store.list_calls():
        if c["status"] != "fertig" or c["label"] not in ("fraud", "no_fraud"): continue
        judged = c["label_checks"] or {}                                   # {check_id: korrekt?} für die Befunde
        missed = set(c["label_missed"] or []) if c["label"] == "fraud" else set()
        labels = {qid: (judged.get(qid, False) or cat in missed) if c["label"] == "fraud" else False for qid, cat in checks.items()}
        analysis = c["analysis"] or {}
        yield {"call_id": c["id"], "filename": c["filename"], "transcript": c["transcript"], "segments": c["segments"],
               "label": c["label"], "categories": c["label_categories"] or [], "missed_categories": sorted(missed),
               "comment": c["label_comment"], "labeled_by": c["labeled_by"], "labeled_at": c["labeled_at"],
               "check_labels": labels,
               "passage_labels": [{"check": x["id"], **x["passage"], "correct": judged[x["id"]]}
                                  for x in analysis.get("checks", []) if x.get("passage") and x["id"] in judged],
               "model_scores": {x["id"]: x["p"] for x in analysis.get("checks", [])}}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with OUT.open("w", encoding="utf-8") as fh:
        for r in records():
            fh.write(json.dumps(r, ensure_ascii=False) + "\n"); n += 1
    print(f"{n} beurteilte Anrufe -> {OUT}")


if __name__ == "__main__":
    main()
