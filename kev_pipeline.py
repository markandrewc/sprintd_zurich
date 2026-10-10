"""
Transkripte -> Kev-4B Compliance-Checks -> alert / no_alert.

  python kev_pipeline.py                            # die 30 Skripte in inventx-case-study/data/Transkript
  python kev_pipeline.py --asr                      # stattdessen die Whisper-Transkripte in outputs/transcriptions
  python kev_pipeline.py a.txt b.txt                # bestimmte Transkripte
  python kev_pipeline.py --rescore --threshold 0.6  # nur neu entscheiden/auswerten, ohne Modell (gespeicherte Scores)

Kev liest das ganze Transkript auf einmal und beantwortet alle Checks aus compliance_questions.json (zwei Listen:
gesetzlich und intern) in einem Forward-Pass. Das Risiko eines Checks ist sein p(yes); das höchste Risiko über alle
Checks entscheidet: >= threshold -> alert (geht zur manuellen Prüfung), sonst no_alert.

Schreibt pro Transkript outputs/kev/<quelle>/<name>.json und eine Übersicht summary.csv. Liegt eine Sollbewertung
(inventx-case-study/data/Skript_mit_Sollbewertung) daneben, wird erst NACH der Entscheidung dagegen ausgewertet.
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
SCRIPT_DIR = ROOT / "inventx-case-study" / "data" / "Transkript"
ASR_DIR = ROOT / "outputs" / "transcriptions"
OUT_ROOT = ROOT / "outputs" / "kev"
CONFIG = ROOT / "compliance_questions.json"
EXPECTED_DIR = ROOT / "inventx-case-study" / "data" / "Skript_mit_Sollbewertung"
ALERT_LABELS = {"alarm", "review"}   # Inventx-Bearbeitungen, die bei uns ein Alert sind
SWEEP = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]

SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")
TURN = re.compile(r"^(T\d{3})\s*·\s*(.+?)\s*$", re.M)   # "T003 · Beratung"


def prepare(text):
    """Das ganze Transkript als Text für Kev: eine Zeile pro Sprecher-Turn ("T003 Beratung: ...") beim Skript-Format,
    sonst ein Satz pro Zeile (z.B. Whisper-Ausgabe)."""
    heads = list(TURN.finditer(text))
    if not heads:
        return "\n".join(s for s in SENTENCE_END.split(" ".join(text.split())) if s)
    ends = [h.start() for h in heads[1:]] + [len(text)]
    return "\n".join(f"{h[1]} {h[2]}: {' '.join(text[h.end():e].split())}" for h, e in zip(heads, ends))


def questions(cfg):
    """-> {check_id: frage} aus beiden Listen in cfg["questions"] (gesetzlich, intern); jede Frage bekommt ihre Liste
    als "source". Kev ignoriert source, category und basis."""
    return {qid: {**q, "source": source} for source, qs in cfg["questions"].items() for qid, q in qs.items()}


def decide(risk, threshold):
    """Ein einziger Alert: alles ab der Schwelle geht zur manuellen Prüfung."""
    return "alert" if risk >= threshold else "no_alert"


def analyze(kev, text, cfg):
    """Kev liest das ganze Transkript, alle Checks in einem Forward-Pass. -> {"checks": {check: p(yes)}, "top_check", "risk"}."""
    checks = {qid: q for qid, q in questions(cfg).items() if q["type"] == "noul"}
    ps = {qid: a["noul"] for qid, a in kev.decide(prepare(text), checks).items()}
    top = max(ps, key=ps.get) if ps else None
    return {"checks": ps, "top_check": top, "risk": ps[top] if top else 0.0}


def expected(stem):
    """-> (alert | no_alert, Original-Bearbeitung) aus Stufe1_D01.txt (für Stufe1_D01 und Stufe1_D01-K1); (None, None)
    ohne Datei. Inventx' alarm und review heissen beide "ein Mensch muss hinschauen" -> alert."""
    f = EXPECTED_DIR / f"{stem.split('-', 1)[0]}.txt"
    if not f.is_file(): return None, None
    label = re.search(r"^Bearbeitung:\s*(\w+)", f.read_text(encoding="utf-8"), re.M)
    raw = label[1] if label else None
    return ("alert" if raw in ALERT_LABELS else "no_alert" if raw else None), raw


def counts(rows):
    """TP/FP/FN/TN und Metriken; rows brauchen "soll" und "ist" (alert | no_alert). Positiv = alert."""
    tp = sum(r["soll"] == "alert" and r["ist"] == "alert" for r in rows); fp = sum(r["soll"] == "no_alert" and r["ist"] == "alert" for r in rows)
    fn = sum(r["soll"] == "alert" and r["ist"] == "no_alert" for r in rows); tn = len(rows) - tp - fp - fn
    div = lambda a, b: a / b if b else float("nan")   # noqa: E731
    prec, rec = div(tp, tp + fp), div(tp, tp + fn)
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "Precision": prec, "Recall": rec,
            "F1": div(2 * prec * rec, prec + rec) if tp else 0.0, "Specificity": div(tn, tn + fp), "Accuracy": div(tp + tn, len(rows))}


def report(rows, threshold):
    """TP/FP/FN/TN, Precision/Recall/F1, plus Schwellen-Sweep auf den gespeicherten Scores."""
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
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--threshold", type=float, help="überschreibt threshold aus der Config")
    ap.add_argument("--asr", action="store_true", help="Whisper-Transkripte (outputs/transcriptions) statt der Skripte")
    ap.add_argument("--rescore", action="store_true", help="kein Modell: gespeicherte Scores aus outputs/kev neu entscheiden")
    args = ap.parse_args()

    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    threshold = cfg["threshold"] if args.threshold is None else args.threshold
    src_dir = ASR_DIR if args.asr else SCRIPT_DIR
    OUT_DIR = OUT_ROOT / ("asr" if args.asr else "scripts")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.rescore:
        results = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(OUT_DIR.glob("*.json"))}
    else:
        files = args.files or sorted(src_dir.glob("*.txt"))
        if not files:
            print(f"Keine Transkripte gefunden in {src_dir}"); return
        from kev_runtime import Kev   # erst hier: --rescore braucht weder torch noch GPU
        kev = Kev()
        results = {}
        for f in files:
            t0 = time.perf_counter()
            res = analyze(kev, f.read_text(encoding="utf-8"), cfg)
            res["seconds"] = round(time.perf_counter() - t0, 1)
            (OUT_DIR / f"{f.stem}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
            results[f.stem] = res
            print(f"[{f.stem}] {res['seconds']}s  risk={res['risk']:.2f} ({res['top_check']})  "
                  + " ".join(f"{q}={p:.2f}" for q, p in res["checks"].items()), flush=True)

    rows = []
    for stem, res in results.items():
        soll, raw = expected(stem)
        rows.append({"call": stem, "ist": decide(res["risk"], threshold), "risk": res["risk"], "top_check": res["top_check"],
                     "soll": soll, "soll_original": raw, **res["checks"]})
    with open(OUT_DIR / "summary.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["call"]); w.writeheader(); w.writerows(rows)

    print(f"\n{'Anruf':<16} {'Ist':<9} {'Risk':>5}  {'Check':<22} Soll")
    for r in rows:
        mark = "" if not r["soll"] else "✓" if r["soll"] == r["ist"] else "✗"
        print(f"{r['call']:<16} {r['ist']:<9} {r['risk']:>5.2f}  {r['top_check'] or '-':<22} {r['soll'] or '-'} ({r['soll_original'] or '-'}) {mark}")
    report(rows, threshold)
    print(f"\nDetails: {OUT_DIR}")


if __name__ == "__main__":
    main()
