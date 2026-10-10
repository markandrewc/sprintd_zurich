"""
Auswertung gegen die Inventx-Sollbewertung, über den Fraud-Analyse-Dienst (muss laufen: python -m fraud_analysis.api).

  python -m analysis_ui.evaluate                            # die 30 Skripte in inventx-case-study/data/Transkript
  python -m analysis_ui.evaluate --asr                      # stattdessen die Transkripte in outputs/transcriptions
  python -m analysis_ui.evaluate a.txt b.txt                # bestimmte Transkripte
  python -m analysis_ui.evaluate --rescore --threshold 0.6  # nur neu entscheiden, ohne Dienst (gespeicherte Ergebnisse)

Schreibt pro Transkript die Antwort von POST /analyze nach outputs/kev/<quelle>/<name>.json und eine Übersicht
summary.csv. Die Sollbewertung wird erst NACH der Analyse gelesen, nie als Eingabe.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from fraud_analysis import client as fraud

ROOT = Path(__file__).resolve().parent.parent
SCRIPT_DIR = ROOT / "inventx-case-study" / "data" / "Transkript"
ASR_DIR = ROOT / "outputs" / "transcriptions"
OUT_ROOT = ROOT / "outputs" / "kev"
EXPECTED_DIR = ROOT / "inventx-case-study" / "data" / "Skript_mit_Sollbewertung"
SOURCES = {"scripts": SCRIPT_DIR, "asr": ASR_DIR}
ALERT_LABELS = {"alarm", "review"}   # Inventx-Bearbeitungen, die bei uns ein Alarm sind
SWEEP = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]


def decide(risk, threshold):
    return "alert" if risk >= threshold else "no_alert"


def scores(res):
    """{check: p} aus einem gespeicherten Ergebnis von POST /analyze."""
    return {c["id"]: c["p"] for c in res["checks"]}


def expected(stem):
    """-> (alert | no_alert, Original-Bearbeitung) aus Stufe1_D01.txt (für Stufe1_D01 und Stufe1_D01-K1); (None, None)
    ohne Datei. Inventx' alarm und review heissen beide "ein Mensch muss hinschauen" -> alert."""
    f = EXPECTED_DIR / f"{stem.split('-', 1)[0]}.txt"
    if not f.is_file(): return None, None
    label = re.search(r"^Bearbeitung:\s*(\w+)", f.read_text(encoding="utf-8"), re.M)
    raw = label[1] if label else None
    return ("alert" if raw in ALERT_LABELS else "no_alert" if raw else None), raw


def testziel(stem):
    f = EXPECTED_DIR / f"{stem.split('-', 1)[0]}.txt"
    m = f.is_file() and re.search(r"^Testziel:\s*(\S+)", f.read_text(encoding="utf-8"), re.M)
    return m[1] if m else ""


def counts(rows):
    """TP/FP/FN/TN und Metriken; rows brauchen "soll" und "ist" (alert | no_alert). Positiv = alert."""
    tp = sum(r["soll"] == "alert" and r["ist"] == "alert" for r in rows); fp = sum(r["soll"] == "no_alert" and r["ist"] == "alert" for r in rows)
    fn = sum(r["soll"] == "alert" and r["ist"] == "no_alert" for r in rows); tn = len(rows) - tp - fp - fn
    div = lambda a, b: a / b if b else float("nan")   # noqa: E731
    prec, rec = div(tp, tp + fp), div(tp, tp + fn)
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "Precision": prec, "Recall": rec,
            "F1": div(2 * prec * rec, prec + rec) if tp else 0.0, "Specificity": div(tn, tn + fp), "Accuracy": div(tp + tn, len(rows))}


def run(source, files=None, on_progress=None):
    """Alle Transkripte der Quelle durch POST /analyze; speichert jede Antwort. -> {stem: antwort}."""
    out_dir = OUT_ROOT / source; out_dir.mkdir(parents=True, exist_ok=True)
    files = files or sorted(SOURCES[source].glob("*.txt"))
    results = {}
    for i, f in enumerate(files):
        res = fraud.analyze(Path(f).read_text(encoding="utf-8"))
        (out_dir / f"{Path(f).stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        results[Path(f).stem] = res
        if on_progress: on_progress(i + 1, len(files), Path(f).stem, res)
    return results


def cached(source):
    stems = {p.stem for p in SOURCES[source].glob("*.txt")}
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((OUT_ROOT / source).glob("*.json")) if p.stem in stems}


def rows_for(results, threshold):
    rows = []
    for stem, res in results.items():
        soll, raw = expected(stem)
        rows.append({"call": stem, "testziel": testziel(stem), "soll": soll, "soll_original": raw, "ist": decide(res["risk"], threshold),
                     "risk": res["risk"], "top_check": res["top_check"], "scores": scores(res)})
    return rows


def report(rows, threshold):
    rows = [r for r in rows if r["soll"]]
    if not rows:
        print("\n(keine Sollbewertung gefunden, keine Auswertung)"); return
    c = counts(rows)
    pct = lambda x: "–" if x != x else f"{x:.0%}"   # noqa: E731
    print(f"\nAuswertung auf {len(rows)} Anrufen  (Schwelle {threshold})")
    print(f"TP {c['TP']}  FP {c['FP']}  FN {c['FN']}  TN {c['TN']}   Precision {pct(c['Precision'])}  Recall {pct(c['Recall'])}  "
          f"F1 {pct(c['F1'])}  Specificity {pct(c['Specificity'])}  Accuracy {pct(c['Accuracy'])}")
    print(f"\n{'Schwelle':>8} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4} {'Prec':>6} {'Recall':>7} {'F1':>6}")
    for t in SWEEP:
        s = counts([{**r, "ist": decide(r["risk"], t)} for r in rows])
        print(f"{t:>8.2f} {s['TP']:>4} {s['FP']:>4} {s['FN']:>4} {s['TN']:>4} {pct(s['Precision']):>6} {pct(s['Recall']):>7} {pct(s['F1']):>6}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--threshold", type=float, help="Default: Schwelle aus fraud_analysis/questions.json")
    ap.add_argument("--asr", action="store_true", help="Transkripte aus outputs/transcriptions statt der Skripte")
    ap.add_argument("--rescore", action="store_true", help="ohne Dienst: gespeicherte Ergebnisse neu entscheiden")
    args = ap.parse_args()

    source = "asr" if args.asr else "scripts"
    threshold = args.threshold
    if threshold is None:
        threshold = json.loads((ROOT / "fraud_analysis" / "questions.json").read_text(encoding="utf-8"))["threshold"]
    if args.rescore:
        results = cached(source)
    else:
        results = run(source, args.files or None, on_progress=lambda i, n, stem, res: print(
            f"[{i}/{n}] {stem}  risk={res['risk']:.2f} ({res['top_check']})  {res['latency_ms'] / 1000:.1f}s", flush=True))

    rows = rows_for(results, threshold)
    with open(OUT_ROOT / source / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        fields = ["call", "testziel", "soll", "soll_original", "ist", "risk", "top_check"]
        check_ids = list(rows[0]["scores"]) if rows else []
        w = csv.DictWriter(fh, fieldnames=fields + check_ids); w.writeheader()
        w.writerows({**{k: r[k] for k in fields}, **r["scores"]} for r in rows)

    print(f"\n{'Anruf':<16} {'Ist':<9} {'Risk':>5}  {'Check':<24} Soll")
    for r in rows:
        mark = "" if not r["soll"] else "✓" if r["soll"] == r["ist"] else "✗"
        print(f"{r['call']:<16} {r['ist']:<9} {r['risk']:>5.2f}  {r['top_check'] or '-':<24} {r['soll'] or '-'} ({r['soll_original'] or '-'}) {mark}")
    report(rows, threshold)
    print(f"\nDetails: {OUT_ROOT / source}")


if __name__ == "__main__":
    main()
