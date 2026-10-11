"""Audio I/O helpers. We decode with soundfile (PyAV in faster-whisper's decoder is version-fragile)
and fall back to ffmpeg for anything that is not 16 kHz mono WAV."""

from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 16000


def load_audio(path: str | Path, sr: int = SR) -> np.ndarray:
    """Mono float32 at ``sr``."""
    try:
        audio, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
        audio = audio.mean(axis=1)
        if file_sr == sr:
            return audio
    except Exception:
        pass
    out = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(path), "-f", "f32le", "-ac", "1",
         "-ar", str(sr), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(out, dtype=np.float32).copy()


def duration(path: str | Path) -> float:
    try:
        return float(sf.info(str(path)).duration)
    except Exception:
        return len(load_audio(path)) / SR


def cut(path: str | Path, start: float, end: float, out_path: str | Path, pad: float = 0.0,
        audio: np.ndarray | None = None) -> Path:
    """Write ``[start - pad, end + pad]`` of ``path`` as 16 kHz mono WAV. Pass the already decoded
    ``audio`` (from :func:`load_audio`) when cutting several passages of one call."""
    if audio is None:
        audio = load_audio(path)
    a = max(0, int((start - pad) * SR))
    b = min(len(audio), int((end + pad) * SR))
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), audio[a:b], SR, subtype="PCM_16")
    return out
