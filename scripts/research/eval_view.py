"""ASR-level metrics of arbitrary transcript VIEWS of a views profile: keyword-spot recall, false keyword
hits, WER/CER vs the gsw scripts (same definitions as `callguard asr-eval`, callguard.eval_asr).

ASR is cached-only (an ASR view whose transcript is not in the cache is skipped for that call; Whisper
is never loaded). Diarization and translated / corrected views (llm_translate, llm_correct) ARE computed
if not cached, so they need their LLM. No checks run.

Usage:
  uv run python scripts/research/eval_view.py -c gpu-views --views de,de_large,de_vanilla,de_fused \
      --calls Stufe1_D02-K2,Stufe1_D05-K2 [--set views.de_fused.translator.concurrency=1] [--tag name]
Writes runs/view_eval/<tag>/{per_call.csv, summary.json, summary.md}.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
from pathlib import Path
from typing import Any

from callguard import eval_asr as ea
from callguard.config import ROOT, load_config
from callguard.data import load_calls
from callguard.pipeline import Pipeline
from callguard.views import build_order


class NotCached(LookupError):
    pass


def cached_only(pipe: Pipeline, views: list[str]) -> None:
    """Make every ASR plugin the views need refuse to decode: Pipeline.transcribe then only serves the
    cache (with its own key logic) and raises NotCached otherwise."""
    for name in views:
        if pipe.view_specs[name].kind != "asr":
            continue
        asr = pipe.asr_for(name)

        def refuse(audio_path: Path, call_id: str, _n: str = name) -> Any:
            raise NotCached(f"{call_id}: ASR of view {_n} not cached")

        asr.transcribe = refuse  # type: ignore[method-assign]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("-c", "--config", default="gpu-views")
    ap.add_argument("--set", dest="set_", action="append", default=[])
    ap.add_argument("--views", required=True, help="comma-separated view names")
    ap.add_argument("--calls", default=None, help="comma-separated call ids (default: all with keyword spots)")
    ap.add_argument("--tag", default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO if a.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    cfg = load_config(a.config, a.set_)
    pipe = Pipeline(cfg)
    wanted = [v.strip() for v in a.views.split(",") if v.strip()]
    order = build_order(pipe.view_specs, [pipe.primary_view, *wanted])
    pipe.needed_views = lambda: order  # type: ignore[method-assign]  # only these views (+ sources), no check views
    cached_only(pipe, order)

    calls = load_calls(cfg.paths.resolve("data_dir"))
    if a.calls:
        keep = [c.strip() for c in a.calls.split(",")]
        calls = [c for c in calls if c.call_id in keep]
    else:
        calls = [c for c in calls if c.expected and c.expected.keyword_spots]
    spotter = ea.spotter_for(pipe)
    rows: dict[str, list[dict[str, Any]]] = {v: [] for v in wanted}
    notes: dict[str, list[str]] = {}
    for c in calls:
        warnings: list[str] = []
        try:
            views = pipe.build_views(c.audio_path, c.call_id, warnings=warnings)
        except Exception as e:  # primary not cached
            notes.setdefault(c.call_id, []).append(f"skipped: {type(e).__name__}: {e}")
            print(f"{c.call_id}: skipped ({e})", flush=True)
            continue
        if warnings:
            notes.setdefault(c.call_id, []).extend(warnings)
        for v in wanted:
            t = views.get(v)
            if t is None:
                continue
            row = ea.evaluate_call(c, t, spotter)
            row["view"] = v
            tm = (t.meta or {}).get("translation") or {}
            for k in ("asked", "changed", "agreeing"):
                if k in tm:
                    row[f"corr_{k}"] = tm[k]
            row["corr_unsupported"] = len(tm.get("unsupported_segments") or []) if tm else None
            rows[v].append(row)
        print(f"{c.call_id}: " + "  ".join(
            f"{v} {r[-1]['kw_matched']}/{r[-1]['kw_annotated']}" for v, r in rows.items()
            if r and r[-1]["call_id"] == c.call_id), flush=True)

    tag = a.tag or f"{a.config}_{'-'.join(wanted)}"
    out = ROOT / "runs" / "view_eval" / tag
    out.mkdir(parents=True, exist_ok=True)
    flat = [r for v in wanted for r in rows[v]]
    if flat:
        with open(out / "per_call.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(dict.fromkeys(k for r in flat for k in r)))
            w.writeheader()
            w.writerows(flat)
    summary = {v: ea.summarize_group(rows[v]) if rows[v] else None for v in wanted}
    meta = {"profile": a.config, "overrides": a.set_, "views": wanted, "calls": [c.call_id for c in calls],
            "notes": notes, "keyword_fuzzy": spotter.check.fuzzy,
            "ci": "95% percentile bootstrap over dialogues (clean+noisy together)"}
    (out / "summary.json").write_text(json.dumps({"meta": meta, "views": summary}, indent=1, default=str))

    header = ["view", "calls", "kw recall", "kw spots", "false hits/call", "CER gsw", "WER gsw"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for v, g in summary.items():
        if g is None:
            lines.append(f"| {v} | 0 | - | - | - | - | - |")
            continue
        lines.append(" | ".join([f"| {v}", str(g["n_calls"]),
                                 ea.fmt_pct(g.get("kw_recall")) + ea.fmt_ci(g.get("kw_recall_ci95")),
                                 f"{g['kw_matched']}/{g['kw_spots']}",
                                 ea.fmt_num(g.get("kw_false_hits_per_call")),
                                 ea.fmt_pct(g.get("cer")), ea.fmt_pct(g.get("wer"))]) + " |")
    per_call = ["", "| call | " + " | ".join(wanted) + " |", "|---|" + "---|" * len(wanted)]
    for c in calls:
        cells = []
        for v in wanted:
            r = next((r for r in rows[v] if r["call_id"] == c.call_id), None)
            cells.append("-" if r is None else f"{r['kw_matched']}/{r['kw_annotated']}"
                         + (f" (missed {r['kw_missed_ids']})" if r["kw_missed_ids"] else "")
                         + (f" false {r['kw_false_hit_ids']}" if r["kw_false_hit_ids"] else ""))
        per_call.append(f"| {c.call_id} | " + " | ".join(cells) + " |")
    md = "\n".join([f"# View eval {tag}", "", f"profile `{a.config}` {' '.join(a.set_)}",
                    "WER/CER vs the Swiss German scripts (dialect spelling: inflated, compare views only). "
                    "Brackets: 95% dialogue bootstrap CI.", "", *lines, *per_call, ""])
    if notes:
        md += "\nNotes:\n" + "\n".join(f"- {cid}: {'; '.join(n)}" for cid, n in notes.items()) + "\n"
    (out / "summary.md").write_text(md)
    print(md)
    print(f"Wrote {out.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
