"""
Export der im Dashboard beurteilten Anrufe als Trainingsdaten.

  python -m finetuning.export_labels                 # -> outputs/finetuning/labels.jsonl

Eine Zeile pro beurteiltem Anruf: Transkript mit Abschnitten, Beurteilung, Kevs Werte pro Fakt zum Zeitpunkt der
Analyse und abgeleitete Labels:
  check_labels    Ja/Nein pro Fakt. Ein Fakt einer ausgelösten Regel, den die Prüferin als stimmend angehakt hat = true,
                  nicht angehakt = false; die Fakten, die in einer als übersehen markierten Regel ja sein müssen = true. Andere Fakten bleiben
                  ohne Label. "Unklar" wird nicht exportiert (kein verlässliches Label).
  passage_labels  pro beurteiltem Fakt die Fundstelle des gleitenden Kev mit stimmt/stimmt nicht (für die Lokalisierung)
Anrufe, die noch mit den früheren Prüfpunkten analysiert wurden, werden übersprungen.
Fakten und Regeln kommen aus fraud_analysis/facts.json.
"""
import json
import sys
from pathlib import Path

from dashboard import store

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "finetuning" / "labels.jsonl"


def rules_by_name():
    cfg = json.loads((ROOT / "fraud_analysis" / "facts.json").read_text(encoding="utf-8"))
    return {r["name"]: [f for f, v in r["conditions"].items() if v == "ja"] for r in cfg["rules"].values()}


def records():
    by_name = rules_by_name()
    for c in store.list_calls():
        analysis = c["analysis"] or {}
        if c["status"] != "fertig" or c["label"] not in ("fraud", "no_fraud") or "facts" not in analysis: continue
        judged = c["label_checks"] or {}                                   # {fakt_id: stimmt?} für die ausgelösten Regeln
        missed = set(c["label_missed"] or []) if c["label"] == "fraud" else set()
        labels = dict(judged) | {f: True for name in missed for f in by_name.get(name, [])}
        yield {"call_id": c["id"], "filename": c["filename"], "transcript": c["transcript"], "segments": c["segments"],
               "label": c["label"], "alarm": c["label"] == "fraud", "categories": c["label_categories"] or [],
               "missed_rules": sorted(missed), "comment": c["label_comment"], "labeled_by": c["labeled_by"],
               "labeled_at": c["labeled_at"], "check_labels": labels,
               "passage_labels": [{"fact": x["id"], **x["passage"], "correct": judged[x["id"]]}
                                  for x in analysis["facts"] if x.get("passage") and x["id"] in judged],
               "model_scores": {x["id"]: x["p"] for x in analysis["facts"]}}


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
