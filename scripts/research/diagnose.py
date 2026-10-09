"""Per-call diagnosis of an experiment variant: expected vs predicted, and per-check scores for the
expected family and the top family. Usage: diagnose.py <experiment> <variant> [--only-wrong]"""
import json
import sys

exp, var = sys.argv[1], sys.argv[2]
only_wrong = "--only-wrong" in sys.argv
base = f"runs/experiments/{exp}/{var}"
rows = {r["call_id"]: r for r in json.load(open(f"{base}/rows.json"))["fixed"]}
res = {}
for line in open(f"{base}/results.jsonl"):
    r = json.loads(line)
    res[r["call_id"]] = r
checks = None
print(f"{'call':16} {'exp':8} {'fam':13} {'pred':8} score  | expected-family per-check scores | top family")
for cid in sorted(rows):
    row = rows[cid]
    if only_wrong and (row["expected"] in ("alarm", "review")) == (row["predicted"] in ("alarm", "review")):
        continue
    fams = res[cid]["decision"]["families"]
    ef = row.get("expected_family")
    pc = fams.get(ef, {}).get("per_check", {}) if ef else {}
    tops = sorted(fams.values(), key=lambda f: -f["score"])[:1]
    top = f"{tops[0]['family']} {tops[0]['score']:.2f} {json.dumps({k: round(v, 2) for k, v in tops[0]['per_check'].items()})}" if tops else ""
    print(f"{cid:16} {row['expected']:8} {str(ef):13} {row['predicted']:8} {row['score']:.2f} | "
          f"{json.dumps({k: round(v, 2) for k, v in pc.items()}):60} | {top}")
