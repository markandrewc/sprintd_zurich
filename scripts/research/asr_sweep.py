"""Transcribe every case call with one ASR config (ASR stage only, cached; no LLM needed).

Usage: uv run python scripts/research/asr_sweep.py -c gpu-12gb [--set asr.model=...] [--noisy-only|--clean-only]
Writes timings to runs/logs/asr_sweep_<tag>.jsonl (seconds per call, audio seconds, cached or not).

Audio pre-processing (A10): ``--set asr.preprocess.type=denoise_sherpa`` denoises before the ASR (CPU,
cached in .cache/preprocess/). ``--preprocess-only`` fills that cache without running the ASR (no GPU),
so a later GPU sweep only transcribes.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from callguard import preprocess
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
    noise = ap.add_mutually_exclusive_group()
    noise.add_argument("--noisy-only", action="store_true", help="only the noisy calls (K2/K4)")
    noise.add_argument("--clean-only", action="store_true", help="only the clean calls (K1/K3)")
    ap.add_argument("--preprocess-only", action="store_true",
                    help="only run asr.preprocess into .cache/preprocess (CPU), no ASR")
    a = ap.parse_args()
    cfg = load_config(a.config, a.set_)
    pipe = Pipeline(cfg)
    calls = load_calls(cfg.paths.resolve("data_dir"))
    if a.calls:
        keep = set(a.calls.split(","))
        calls = [c for c in calls if c.call_id in keep]
    if a.noisy_only or a.clean_only:
        calls = [c for c in calls if c.noisy == a.noisy_only]
    pre = pipe.preprocessor_for(pipe.asr)
    if a.preprocess_only:
        if pre is None:
            raise SystemExit("--preprocess-only needs asr.preprocess (e.g. --set asr.preprocess.type=denoise_sherpa)")
        return preprocess_only(pipe, pre, calls)
    tag = a.tag or Path(str(cfg.asr.get("model", "asr"))).name + "_" + str(cfg.asr.get("task", "transcribe"))
    out = Path("runs/logs") / f"asr_sweep_{tag}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"{len(calls)} calls -> {out}" + (f" (preprocess {pre.cache_params()})" if pre else ""), flush=True)
    for i, c in enumerate(calls, 1):
        t0 = time.time()
        t = pipe.transcribe(Path(c.audio_path), c.call_id)
        dt = time.time() - t0
        dur = max((s.end for s in t.segments), default=0.0)
        rec = {"call_id": c.call_id, "seconds": round(dt, 2), "audio_s": round(dur, 1), "tag": tag,
               "segments": len(t.segments), "chars": sum(len(s.text) for s in t.segments)}
        if "preprocess" in t.meta:
            rec["preprocess"] = {k: v for k, v in t.meta["preprocess"].items() if k != "path"}
        with out.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        print(f"[{i}/{len(calls)}] {c.call_id} {dt:.1f}s audio {dur:.0f}s", flush=True)


def preprocess_only(pipe: Pipeline, pre: preprocess.Preprocessor, calls: list) -> None:
    """Fill .cache/preprocess for ``calls`` with exactly the files Pipeline.transcribe will look for."""
    total_s = total_audio = 0.0
    print(f"{len(calls)} calls: preprocess {pre.cache_params()} -> {pipe.ctx.cache.root / 'preprocess'}", flush=True)
    for i, c in enumerate(calls, 1):
        with preprocess.prepared(pre, c.audio_path, pipe.ctx.cache.root, audio_hash=file_hash(c.audio_path),
                                 keep=True) as (_, info):
            pass
        if not info["cached"]:
            total_s += info["seconds"]
            total_audio += info["audio_s"]
        print(f"[{i}/{len(calls)}] {c.call_id} " + ("cached" if info["cached"] else
              f"{info['seconds']:.1f}s for {info['audio_s']:.0f}s audio ({info['s_per_audio_min']:.2f} s/audio-min)"),
              flush=True)
    if total_audio:
        print(f"total {total_s:.1f}s for {total_audio / 60:.1f} audio-min = {total_s / (total_audio / 60):.2f} "
              f"s per audio minute (RTF {total_s / total_audio:.3f})", flush=True)


if __name__ == "__main__":
    main()
