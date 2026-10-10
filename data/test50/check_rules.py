#!/usr/bin/env python3
"""Apply the v3 rule table and score it.

  python3 check_rules.py families-v3.json                    # self-test: gold facts -> verdicts
  python3 check_rules.py families-v3.json predictions.json   # score model output

predictions.json (one entry per call, keyed by script ID such as "C06"):
  {"C06": {"families": {"trade": {"facts": {"kaufwunsch": "ja", ...},
                                  "evidence": ["T006", "T032"]}, ...}}}
Families missing from a prediction count as no_alert. Evidence is scored
against the expected Belege of the target family (context + act turn).
"""
import json
import sys

SEVERITY = {"no_alert": 0, "review": 1, "alarm": 2}


def family_verdict(cfg, facts):
    if cfg.get("classify_only"):
        return "no_alert"
    if facts.get(cfg["gate"]) == "nein":
        return "no_alert"
    if any(facts.get(s) == "unklar" for s in cfg.get("review_if_unklar", [])):
        return "review"
    vals = [facts.get(s, "unklar") for s in cfg["alarm_if"]]
    if all(v == "ja" for v in vals):
        return "alarm"
    if any(v == "nein" for v in vals):
        return "no_alert"
    return "review"


def call_verdict(families_cfg, per_family):
    verdicts = {f: family_verdict(families_cfg[f], d.get("facts", {})) for f, d in per_family.items()
                if f in families_cfg}
    worst = max(verdicts.values(), key=SEVERITY.get, default="no_alert")
    return worst, verdicts


def main():
    cfg = json.load(open(sys.argv[1], encoding="utf-8"))
    fams, gold = cfg["families"], {k: v for k, v in cfg["gold"].items() if not k.startswith("_")}
    if len(sys.argv) > 2:
        pred = json.load(open(sys.argv[2], encoding="utf-8"))
    else:  # self-test: the gold facts are the "prediction"
        pred = {cid: {"families": {g["family"]: {"facts": g["facts"], "evidence": g["belege"]}}}
                for cid, g in gold.items()}
    labels = ["alarm", "review", "no_alert"]
    matrix = {e: {p: 0 for p in labels} for e in labels}
    ev_hit = ev_total = 0
    for cid, g in sorted(gold.items()):
        p = pred.get(cid, {"families": {}})
        verdict, _ = call_verdict(fams, p["families"])
        matrix[g["expected"]][verdict] += 1
        if verdict != g["expected"]:
            print(f"MISMATCH {cid} [{g['family']}]: expected {g['expected']}, got {verdict}")
        if g["expected"] != "no_alert" or g["family"] != "numbers":
            ev = set(p["families"].get(g["family"], {}).get("evidence", []))
            ev_total += 1
            ev_hit += bool(ev & {g["belege"][-1]})  # act turn found
    print("expected \\ predicted  " + "  ".join(f"{l:>8}" for l in labels))
    for e in labels:
        print(f"{e:>20}  " + "  ".join(f"{matrix[e][p]:>8}" for p in labels))
    correct = sum(matrix[l][l] for l in labels)
    print(f"correct {correct}/{len(gold)} · false alarms {matrix['no_alert']['alarm']} · "
          f"missed alarms {matrix['alarm']['no_alert']} · act turn found {ev_hit}/{ev_total}")


if __name__ == "__main__":
    main()
