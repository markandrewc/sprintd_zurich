"""Score stored results against expected labels (Sunday: hidden test set, any file names).

Usage: uv run python scripts/score_results.py runs/recommended labels.csv [--threshold 0.55]
labels.csv: call_id,expected   (expected in alarm | review | no_alert; call_id = wav file stem)
Prints flag precision/recall/F1, false-alarm rate, miss rate, alarm F1, review recall, 3-class accuracy and the
per-call table. --threshold re-labels from the stored call score only when given (otherwise the stored labels).
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FLAG = ("alarm", "review")


def f1(p: float, r: float) -> float:
    return 2 * p * r / (p + r) if p + r else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir")
    ap.add_argument("labels_csv")
    ap.add_argument("--threshold", type=float, default=None)
    a = ap.parse_args()
    truth = {r["call_id"].strip(): r["expected"].strip() for r in csv.DictReader(open(a.labels_csv))}
    rows = []
    for cid, exp in sorted(truth.items()):
        f = Path(a.results_dir) / cid / "result.json"
        if not f.exists():
            print(f"missing result: {cid}")
            continue
        d = json.loads(f.read_text())["decision"]
        pred = d["label"]
        if a.threshold is not None and pred != "review":
            pred = "alarm" if d["score"] >= a.threshold else "no_alert"
        rows.append((cid, exp, pred, d["score"]))
    tp = sum(1 for _, e, p, _ in rows if e in FLAG and p in FLAG)
    fp = sum(1 for _, e, p, _ in rows if e not in FLAG and p in FLAG)
    fn = sum(1 for _, e, p, _ in rows if e in FLAG and p not in FLAG)
    neg = sum(1 for _, e, _, _ in rows if e == "no_alert")
    pos = sum(1 for _, e, _, _ in rows if e in FLAG)
    prec, rec = (tp / (tp + fp) if tp + fp else 0.0), (tp / pos if pos else 0.0)
    atp = sum(1 for _, e, p, _ in rows if e == "alarm" and p == "alarm")
    ap_ = sum(1 for _, _, p, _ in rows if p == "alarm")
    aex = sum(1 for _, e, _, _ in rows if e == "alarm")
    rev = sum(1 for _, e, _, _ in rows if e == "review")
    print(f"calls {len(rows)} | flag P {prec:.0%} R {rec:.0%} F1 {f1(prec, rec):.2f} | false-alarm rate "
          f"{(fp / neg if neg else 0):.0%} | miss rate {(fn / pos if pos else 0):.0%} | alarm F1 "
          f"{f1(atp / ap_ if ap_ else 0, atp / aex if aex else 0):.2f} | review recall "
          f"{(sum(1 for _, e, p, _ in rows if e == p == 'review') / rev if rev else 0):.0%} | 3-class acc "
          f"{sum(1 for _, e, p, _ in rows if e == p) / len(rows):.0%}")
    for cid, e, p, s in rows:
        print(f"  {cid:28} expected {e:9} predicted {p:9} score {s:.2f} {'OK' if e == p else ''}")


if __name__ == "__main__":
    main()
