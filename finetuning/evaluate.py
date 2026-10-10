"""
Vergleicht das ursprüngliche Kev-4B mit einem nachtrainierten Modell auf den zurückgehaltenen Beispielen.

  python -m finetuning.evaluate outputs/finetuning/runs/<name>
  python -m finetuning.evaluate outputs/finetuning/runs/<name> --threshold 0.6

Gemessen wird auf outputs/finetuning/kev_val.jsonl (finetuning.build_dataset): dem zurückgehaltenen Teil unserer
Daten, der nicht trainiert wurde. Kev beantwortet pro Gespräch alle Fakten aus fraud_analysis/facts.json.
  - Pro Fakt: TP/FP/FN/TN bei der Schwelle (Default aus facts.json), nur wo ein Label vorliegt.
  - Pro Anruf: Alarm, wenn eine Regel auslöst (alle Bedingungen ja/nein erfüllt), gegen das Sollurteil des Anrufs
    (_meta.alarm; Anrufe mit Sollurteil "review" werden separat gezählt).
"""
import argparse
import gc
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAL = ROOT / "outputs" / "finetuning" / "kev_val.jsonl"
CONFIG = ROOT / "fraud_analysis" / "facts.json"
BASE = "jaredpalmer/kev-4b"


def predict(repo, records, facts):
    """-> pro Beispiel {fakt: p(yes)} für alle Fakten. Lädt das Modell, rechnet, gibt die GPU wieder frei."""
    import torch
    from fraud_analysis.kev.api import SystemOneRequest
    from fraud_analysis.runtime import Kev
    kev = Kev(repo)
    qs = {f: {"type": "noul", "instructions": q["instructions"]} for f, q in facts.items()}
    out = [{f: a["noul"] for f, a in kev.systemone(SystemOneRequest(state=r["state"], questions=qs))["answers"].items()}
           for r in records]
    del kev; gc.collect(); torch.cuda.empty_cache()
    return out


def fired(p, rules, th):
    """Regeln, deren Bedingungen (ja/nein pro Fakt) alle erfüllt sind."""
    from fraud_analysis.rules import fired_rules
    return fired_rules(p, rules, th)


def counts(pairs):
    """pairs: [(label, vorhergesagt)] -> TP, FP, FN, TN."""
    return [sum(y and p for y, p in pairs), sum(p and not y for y, p in pairs),
            sum(y and not p for y, p in pairs), sum(not y and not p for y, p in pairs)]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="Ordner des nachtrainierten Modells")
    ap.add_argument("--threshold", type=float)
    a = ap.parse_args()
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    facts, rules = cfg["facts"], cfg["rules"]
    th = a.threshold if a.threshold is not None else cfg["threshold"]
    records = [json.loads(l) for l in VAL.read_text(encoding="utf-8").splitlines() if l.strip()]
    if not records: sys.exit(f"Keine Validierungsbeispiele in {VAL}")
    print(f"{len(records)} Validierungsbeispiele, {len(facts)} Fakten, {len(rules)} Regeln, Schwelle {th}")
    models = {"Kev-4B": BASE, "nachtrainiert": str(Path(a.run).resolve())}
    preds = {name: predict(repo, records, facts) for name, repo in models.items()}

    print(f"\n{'Fakt':<28} {'ja':>3} {'nein':>4} | {'Kev-4B  TP FP FN TN':>22} | {'nachtrainiert  TP FP FN TN':>28}")
    for f in facts:
        rows = [(r["questions"][f]["label"], i) for i, r in enumerate(records) if f in r["questions"]]
        if not rows: continue
        c = [counts([(y, preds[m][i][f] >= th) for y, i in rows]) for m in models]
        pos = sum(y for y, _ in rows)
        print(f"{f:<28} {pos:>3} {len(rows) - pos:>4} | {'':>8}{c[0][0]:>3}{c[0][1]:>3}{c[0][2]:>3}{c[0][3]:>3}"
              f" | {'':>14}{c[1][0]:>3}{c[1][1]:>3}{c[1][2]:>3}{c[1][3]:>3}")

    known = [i for i, r in enumerate(records) if r["_meta"].get("alarm") is not None]
    review = [i for i, r in enumerate(records) if r["_meta"].get("alarm") is None]
    print(f"\nPro Anruf (Alarm, wenn eine Regel auslöst), {len(known)} Anrufe mit Sollurteil alarm/no_alert:")
    for m in models:
        tp, fp, fn, tn = counts([(records[i]["_meta"]["alarm"], bool(fired(preds[m][i], rules, th))) for i in known])
        prec = tp / (tp + fp) if tp + fp else float("nan"); rec = tp / (tp + fn) if tp + fn else float("nan")
        wrong = sum(sum((preds[m][i][f] >= th) != q["label"] for f, q in r["questions"].items()) for i, r in enumerate(records))
        rv = f"   review-Anrufe mit Alarm: {sum(bool(fired(preds[m][i], rules, th)) for i in review)}/{len(review)}" if review else ""
        print(f"  {m:<14} TP {tp:>3}  FP {fp:>3}  FN {fn:>3}  TN {tn:>3}   Precision {prec:.0%}  Recall {rec:.0%}   "
              f"falsche Fakten-Entscheide: {wrong}{rv}")
    print("\nAusgelöste Regeln pro Anruf (Kev-4B | nachtrainiert):")
    for i, r in enumerate(records):
        soll = {True: "alarm", False: "kein", None: "review"}[r["_meta"].get("alarm")]
        print(f"  {r['_meta']['ref']:<22} Soll {soll:<6} | {', '.join(fired(preds['Kev-4B'][i], rules, th)) or '-'}"
              f" | {', '.join(fired(preds['nachtrainiert'][i], rules, th)) or '-'}")


if __name__ == "__main__":
    main()
