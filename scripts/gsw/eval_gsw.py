"""Evaluation only: how close is an automatic Swiss German transcript to the dialect script a test call was
synthesised from (``<data>/Transkript_CH_timed/<dialogue>.json``)? The reference is a YARDSTICK here and nothing
else; it never feeds the pipeline.

Each candidate is a list of timed segments. Per reference turn, the candidate text is every segment whose time
overlaps the turn most; scored with chrF (character 1-6-grams, beta 2) and normalised Levenshtein similarity
after lower-casing and dropping punctuation. Per call: mean over turns, and chrF of the whole call (time-free).
Means over calls with a 95 % bootstrap CI (calls resampled). Without ``Transkript_CH_timed/`` (the case data:
``Transkript/<dialogue>.txt``, turns without times) only the time-free call chrF is computed.

Candidates (``name=spec``, repeatable):
  name=asr:<runs_dir>          the Standard German ASR transcript of result.json (baseline: no dialect at all)
  name=display:<runs_dir>      result.json display_views.gsw
  name=segments:<dir>          <dir>/<call_id>.json = {"segments": [{"start", "end", "text"}], "seconds"?}

  uv run python scripts/gsw/eval_gsw.py --data data_test50/v1 --calls A-K1,B-K1 de=asr:runs/x llm=display:runs/x
"""

from __future__ import annotations

import argparse
import json
import random
import re
import statistics
from collections import Counter
from pathlib import Path

from rapidfuzz.distance import Levenshtein

_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def norm(text: str) -> str:
    return " ".join(_PUNCT.sub(" ", text.lower().replace("’", "'")).split())


def chrf(hyp: str, ref: str, n: int = 6, beta: float = 2.0) -> float:
    hyp, ref = norm(hyp).replace(" ", ""), norm(ref).replace(" ", "")
    if not hyp or not ref:
        return 0.0
    ps, rs = [], []
    for k in range(1, n + 1):
        h = Counter(hyp[i:i + k] for i in range(len(hyp) - k + 1))
        r = Counter(ref[i:i + k] for i in range(len(ref) - k + 1))
        if not h or not r:
            continue
        hit = sum((h & r).values())
        ps.append(hit / sum(h.values()))
        rs.append(hit / sum(r.values()))
    p, r = statistics.mean(ps), statistics.mean(rs)
    return 0.0 if p + r == 0 else 100 * (1 + beta ** 2) * p * r / (beta ** 2 * p + r)


def lev(hyp: str, ref: str) -> float:
    return 100 * Levenshtein.normalized_similarity(norm(hyp), norm(ref))


def load_candidate(spec: str, call_id: str) -> tuple[list[dict], float | None] | None:
    kind, _, where = spec.partition(":")
    if kind in ("asr", "display"):
        p = Path(where) / call_id / "result.json"
        if not p.exists():
            return None
        d = json.loads(p.read_text())
        t = d["transcript"] if kind == "asr" else (d.get("display_views") or {}).get("gsw")
        if t is None:
            return None
        return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in t["segments"]], None
    p = Path(where) / f"{call_id}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text())
    return d["segments"], d.get("seconds")


def assign(turns: list[dict], segs: list[dict]) -> list[str]:
    out = [[] for _ in turns]
    for s in segs:
        best, ov = None, 0.0
        for i, t in enumerate(turns):
            o = min(s["end"], t["end"]) - max(s["start"], t["start"])
            if o > ov:
                best, ov = i, o
        if best is not None:
            out[best].append(s["text"])
    return [" ".join(x) for x in out]


def ci(xs: list[float], n: int = 2000) -> tuple[float, float, float]:
    rng = random.Random(0)
    means = sorted(statistics.mean(rng.choices(xs, k=len(xs))) for _ in range(n))
    return statistics.mean(xs), means[int(0.025 * n)], means[int(0.975 * n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="dataset folder with Transkript_CH_timed/")
    ap.add_argument("--calls", required=True, help="comma-separated call ids (<dialogue>-K<n>)")
    ap.add_argument("--samples", type=int, default=3, help="turns printed per call for a human look")
    ap.add_argument("candidates", nargs="+", help="name=spec")
    a = ap.parse_args()
    cands = dict(c.split("=", 1) for c in a.candidates)
    calls = [c.strip() for c in a.calls.split(",") if c.strip()]
    per: dict[str, dict[str, list[float]]] = {n: {"turn_chrf": [], "turn_lev": [], "call_chrf": [], "sec": []}
                                              for n in cands}
    samples: list[str] = []
    for cid in calls:
        dlg = re.sub(r"-K\d+$", "", cid)
        timed = Path(a.data) / "Transkript_CH_timed" / f"{dlg}.json"
        if timed.exists():
            turns = json.loads(timed.read_text())["turns"]
        else:  # untimed script: call-level score only
            from callguard.data import parse_turns
            turns = [{"id": t.id, "speaker": t.speaker, "start": -1.0, "end": -1.0, "text": t.text}
                     for t in parse_turns((Path(a.data) / "Transkript" / f"{dlg}.txt").read_text())]
        texts = {}
        for name, spec in cands.items():
            got = load_candidate(spec, cid)
            if got is None:
                continue
            segs, secs = got
            hyp = assign(turns, segs)
            texts[name] = hyp
            if timed.exists():
                per[name]["turn_chrf"].append(statistics.mean(chrf(h, t["text"]) for h, t in zip(hyp, turns)))
                per[name]["turn_lev"].append(statistics.mean(lev(h, t["text"]) for h, t in zip(hyp, turns)))
            per[name]["call_chrf"].append(chrf(" ".join(s["text"] for s in segs), " ".join(t["text"] for t in turns)))
            if secs is not None:
                per[name]["sec"].append(secs)
        for i in (list(range(len(turns)))[1:1 + a.samples] if timed.exists() else []):
            samples.append(f"\n{cid} {turns[i]['id']} ({turns[i]['speaker']}, {turns[i].get('dialect', '?')})")
            samples.append(f"  {'REFERENZ':<12} {turns[i]['text']}")
            for name, hyp in texts.items():
                samples.append(f"  {name:<12} {hyp[i]}")
    print(f"{len(calls)} calls; mean over calls [95% bootstrap CI]\n")
    print(f"| candidate | turn chrF | turn Levenshtein sim. | call chrF | s/call | n |\n|---|---|---|---|---|---|")
    for name, m in per.items():
        if not m["call_chrf"]:
            continue
        cells = []
        for k in ("turn_chrf", "turn_lev", "call_chrf"):
            mu, lo, hi = ci(m[k]) if m[k] else (float("nan"),) * 3
            cells.append(f"{mu:.1f} [{lo:.1f}, {hi:.1f}]" if m[k] else "-")
        sec = f"{statistics.mean(m['sec']):.0f}" if m["sec"] else "-"
        print(f"| {name} | {' | '.join(cells)} | {sec} | {len(m['call_chrf'])} |")
    print("\n".join(samples))


if __name__ == "__main__":
    main()
