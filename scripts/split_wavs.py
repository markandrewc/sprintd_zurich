#!/usr/bin/env python3
"""Split a folder of .wav files into N folders of about equal total audio length (one per GPU host).

Longest call first, each to the folder with the least audio so far. Copies the files; the names are kept.

    python3 scripts/split_wavs.py <folder-with-wavs> <out-1> <out-2> [...] [--speeds S1 S2 ...]
    # then on each host: scripts/run_testset.sh <out-k> <name-k>

``--speeds``: seconds of run time per minute of audio for each output host (from a run's timings.tsv: total / audio
minutes). Then each call goes to the host that would finish it first, so a slower host gets less audio.
"""

from __future__ import annotations

import shutil
import sys
import wave
from pathlib import Path


def seconds(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    args = sys.argv[1:]
    speeds: list[float] | None = None
    if "--speeds" in args:
        i = args.index("--speeds")
        speeds = [float(x) for x in args[i + 1:]]
        args = args[:i]
    if len(args) < 3:
        sys.exit(__doc__)
    src, outs = Path(args[0]), [Path(a) for a in args[1:]]
    rate = speeds or [1.0] * len(outs)
    if len(rate) != len(outs):
        sys.exit(f"--speeds needs one value per output folder ({len(outs)})")
    files = sorted([*src.glob("*.wav"), *src.glob("*.WAV")])
    if not files:
        sys.exit(f"no .wav files in {src}")
    dur = {f: seconds(f) for f in files}
    total = [0.0] * len(outs)
    for o in outs:
        o.mkdir(parents=True, exist_ok=True)
    for f in sorted(files, key=lambda x: -dur[x]):
        k = min(range(len(outs)), key=lambda h: (total[h] + dur[f]) * rate[h])
        shutil.copy2(f, outs[k] / f.name)
        total[k] += dur[f]
    for o, t in zip(outs, total):
        print(f"{o}: {len(list(o.glob('*.wav')) + list(o.glob('*.WAV')))} calls, {t / 60:.1f} min")


if __name__ == "__main__":
    main()
