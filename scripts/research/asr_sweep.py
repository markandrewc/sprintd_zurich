"""Transcribe every case call with one ASR config (ASR stage only, cached; no LLM needed).

Usage: uv run python scripts/research/asr_sweep.py -c gpu-12gb [--set asr.model=...] [--noisy-first]
Writes timings to runs/logs/asr_sweep_<tag>.jsonl (seconds per call, audio seconds, cached or not).
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from callguard.cache import file_hash
from callguard.config import load_config
from callguard.data import load_calls
from callguard.pipeline import Pipeline


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--config", default="gpu-12gb")
    ap.add_argument("--set", dest="set_", action="append", default=[])
    ap.add_argument("--tag", default=None)
    ap.add_argument("--calls", default=None, help="comma-separated call ids")
    a = ap.parse_args()
    cfg = load_config(a.config, a.set_)
    pipe = Pipeline(cfg)
    calls = load_calls(cfg.paths.resolve("data_dir"))
    if a.calls:
        keep = set(a.calls.split(","))
        calls = [c for c in calls if c.call_id in keep]
    tag = a.tag or Path(str(cfg.asr.get("model", "asr"))).name + "_" + str(cfg.asr.get("task", "transcribe"))
    out = Path("runs/logs") / f"asr_sweep_{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"{len(calls)} calls -> {out}", flush=True)
    for i, c in enumerate(calls, 1):
        key = {"audio": file_hash(c.audio_path), "asr": pipe.asr.cache_params()}
        t0 = time.time()
        t = pipe.transcribe(Path(c.audio_path), c.call_id)
        dt = time.time() - t0
        dur = max((s.end for s in t.segments), default=0.0)
        rec = {"call_id": c.call_id, "seconds": round(dt, 2), "audio_s": round(dur, 1), "tag": tag,
               "segments": len(t.segments), "chars": sum(len(s.text) for s in t.segments)}
        with out.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{i}/{len(calls)}] {c.call_id} {dt:.1f}s audio {dur:.0f}s", flush=True)


if __name__ == "__main__":
    main()
