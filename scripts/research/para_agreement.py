"""R3 paraphrase robustness: compare the facts answers and call labels of two experiment variants.

Reads <exp>/<a>/results.jsonl and <exp>/<b>/results.jsonl (default: champion vs para) plus rows.json for the
expected labels, and prints
  - call label flips (3-class, and flag = alarm|review) with expected labels,
  - per-fact value agreement (yes / no / unclear, the value the rules see, after the prefix max) and mean |dp(yes)|,
  - the same on the full-call probe only (no prefix max), and a confusion matrix of fact values.

    uv run python scripts/research/para_agreement.py [--exp runs/experiments/champion] [--a champion] [--b para]
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

VALUES = ("yes", "no", "unclear")


def load(vdir: Path) -> dict[str, dict]:
    out = {}
    for line in (vdir / "results.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["call_id"]] = r
    return out


def expected(vdir: Path) -> dict[str, str]:
    rows = json.loads((vdir / "rows.json").read_text())
    return {r["call_id"]: r["expected"] for r in rows["fixed"]}


def facts_of(r: dict) -> dict[tuple[str, str], dict]:
    out = {}
    fs = (r["checks"].get("facts") or {}).get("family_scores") or {}
    for fam, s in fs.items():
        for fid, d in (s.get("detail") or {}).get("facts", {}).items():
            out[(fam, fid)] = d
    return out


def full_p(d: dict) -> float:
    return float((d.get("prefix") or {}).get("full", d["p"]["yes"]))


def flag(lbl: str) -> bool:
    return lbl in ("alarm", "review")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--exp", default="runs/experiments/champion")
    ap.add_argument("--a", default="champion")
    ap.add_argument("--b", default="para")
    args = ap.parse_args()
    exp = Path(args.exp)
    A, B = load(exp / args.a), load(exp / args.b)
    exp_lbl = expected(exp / args.a)
    calls = sorted(set(A) & set(B))
    print(f"calls: {len(calls)} (a={len(A)}, b={len(B)})")

    # -- call labels
    flips3, flipsf = [], []
    for c in calls:
        la, lb = A[c]["decision"]["label"], B[c]["decision"]["label"]
        if la != lb:
            flips3.append((c, exp_lbl.get(c), la, lb, A[c]["decision"]["score"], B[c]["decision"]["score"]))
            if flag(la) != flag(lb):
                flipsf.append(c)
    print(f"\n3-class label flips: {len(flips3)}/{len(calls)} ({100 * len(flips3) / len(calls):.0f}%); "
          f"flag flips: {len(flipsf)}/{len(calls)}")
    for c, e, la, lb, sa, sb in flips3:
        ok_a, ok_b = la == e, lb == e
        tag = "better" if ok_b and not ok_a else "worse" if ok_a and not ok_b else "neutral"
        print(f"  {c:22s} expected {e:9s} {args.a} {la:8s} ({sa:.2f}) -> {args.b} {lb:8s} ({sb:.2f})  [{tag}]")

    # -- fact answers
    per_fact: dict[tuple[str, str], list[tuple[str, str, float]]] = defaultdict(list)
    conf: Counter = Counter()
    full_agree = full_n = 0
    full_dp: list[float] = []
    for c in calls:
        fa, fb = facts_of(A[c]), facts_of(B[c])
        for k in sorted(set(fa) & set(fb)):
            va, vb = fa[k]["value"], fb[k]["value"]
            per_fact[k].append((va, vb, abs(fa[k]["p"]["yes"] - fb[k]["p"]["yes"])))
            conf[(va, vb)] += 1
            full_dp.append(abs(full_p(fa[k]) - full_p(fb[k])))
            if "prefix_used" not in fa[k] and "prefix_used" not in fb[k]:
                full_n += 1
                full_agree += va == vb
    n = sum(conf.values())
    agree = sum(v for (a, b), v in conf.items() if a == b)
    dps = [dp for v in per_fact.values() for _, _, dp in v]
    print(f"\nfact answers compared: {n}; value agreement {agree}/{n} = {100 * agree / n:.1f}%; "
          f"mean |dp(yes)| {sum(dps) / len(dps):.3f} (rule-level p, after prefix max); "
          f"full-call probe mean |dp(yes)| {sum(full_dp) / len(full_dp):.3f}")
    print(f"  answers with no prefix win on either side: agreement {full_agree}/{full_n} = "
          f"{100 * full_agree / max(1, full_n):.1f}%")
    print(f"\nconfusion (rows {args.a}, cols {args.b}):")
    print("            " + "".join(f"{v:>9s}" for v in VALUES))
    for a in VALUES:
        print(f"  {a:9s} " + "".join(f"{conf[(a, b)]:9d}" for b in VALUES))
    yes_a = sum(v for (a, _), v in conf.items() if a == "yes")
    yes_b = sum(v for (_, b), v in conf.items() if b == "yes")
    print(f"  yes answers: {args.a} {yes_a}, {args.b} {yes_b}; "
          f"yes-agreement (both yes / either yes) {conf[('yes', 'yes')]}/{n - conf[('no', 'no')] - conf[('unclear', 'unclear')] - conf[('no', 'unclear')] - conf[('unclear', 'no')]}")

    print(f"\nper fact: agreement, mean |dp(yes)|, disagreements ({args.a}->{args.b})")
    for (fam, fid), v in sorted(per_fact.items()):
        ag = sum(a == b for a, b, _ in v)
        dis = Counter(f"{a}->{b}" for a, b, _ in v if a != b)
        print(f"  {fam + '.' + fid:36s} {ag:2d}/{len(v):2d} ({100 * ag / len(v):3.0f}%)  "
              f"|dp| {sum(dp for *_, dp in v) / len(v):.3f}  {dict(dis) if dis else ''}")


if __name__ == "__main__":
    main()
