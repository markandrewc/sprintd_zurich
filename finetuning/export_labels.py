"""
Export der im Dashboard beurteilten Anrufe als Trainingsdaten.

  python -m finetuning.export_labels                 # -> outputs/finetuning/labels.jsonl

Eine Zeile pro beurteiltem Anruf: Transkript, Beurteilung, Kategorien, Kevs Scores zum Zeitpunkt der Analyse und
abgeleitete Ja/Nein-Labels pro Check:
  - "Verstoss bestätigt": Checks der angekreuzten Kategorien = true, alle anderen = false
  - "Kein Verstoss":      alle Checks = false
  - "Unklar":             nicht exportiert (kein verlässliches Label)
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
        cats = set(c["label_categories"] or []) if c["label"] == "fraud" else set()
        yield {"call_id": c["id"], "filename": c["filename"], "transcript": c["transcript"], "segments": c["segments"],
               "label": c["label"], "categories": sorted(cats), "comment": c["label_comment"],
               "labeled_by": c["labeled_by"], "labeled_at": c["labeled_at"],
               "check_labels": {qid: cat in cats for qid, cat in checks.items()},
               "model_scores": {x["id"]: x["p"] for x in (c["analysis"] or {}).get("checks", [])}}


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
