"""Audio pre-processors (plugin kind ``preprocess``): audio -> audio before the ASR hears it.

Configured per ASR, so every ASR view can have its own (``views.<v>.asr.preprocess``)::

    asr:
      type: faster_whisper
      ...
      preprocess: {type: denoise_sherpa, model: models/denoise/dpdfnet2.onnx}

Only the ASR reads the processed audio. Diarization, snippets and ``Transcript.audio_path`` keep the
original file. The ASR cache key gets ``preprocess: <cache_params>`` only when a non-identity
pre-processor is set, so transcripts cached without one keep their keys.

The processed audio is written once to ``<cache_dir>/preprocess/<audio hash>-<params hash>.wav``
(16 kHz mono PCM16) and reused by every later ASR run (other models, beam sizes, ...).
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import soundfile as sf

from callguard.audio import SR, load_audio
from callguard.cache import file_hash, stable_hash
from callguard.plugins import Preprocessor

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.preprocess")
_LOCK = threading.Lock()  # one writer per cache file at a time (experiments run calls in threads)


class NoPreprocessor(Preprocessor):
    """Identity. ``preprocess: {type: none}`` switches an inherited pre-processor off for one view."""

    identity = True

    def __init__(self, ctx: "Context", **params: Any):
        if params:
            raise TypeError(f"preprocess type 'none' takes no params, got {sorted(params)}")
        super().__init__(ctx)

    def process(self, samples: np.ndarray, sr: int) -> np.ndarray:
        return samples


def is_active(pre: Preprocessor | None) -> bool:
    return pre is not None and not pre.identity


def cache_file(pre: Preprocessor, audio_hash: str, cache_dir: Path) -> Path:
    return cache_dir / "preprocess" / f"{audio_hash}-{stable_hash(pre.cache_params())}.wav"


def fit_length(y: np.ndarray, n: int) -> np.ndarray:
    """Pad with zeros / trim to ``n`` samples (frame-based models drop a partial last frame)."""
    y = np.asarray(y, dtype=np.float32).reshape(-1)
    if len(y) >= n:
        return y[:n]
    return np.concatenate([y, np.zeros(n - len(y), dtype=np.float32)])


def run(pre: Preprocessor, audio_path: str | Path, out_path: str | Path) -> dict[str, Any]:
    """Process ``audio_path`` into ``out_path`` (atomic write). Returns timing info."""
    x = load_audio(audio_path, SR)
    t0 = time.time()
    y = fit_length(pre.process(x, SR), len(x))
    elapsed = time.time() - t0
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(f".{out.name}.{os.getpid()}.{threading.get_ident()}.tmp.wav")
    sf.write(str(tmp), np.clip(y, -1.0, 1.0), SR, subtype="PCM_16")
    tmp.replace(out)
    dur = len(x) / SR
    return {"seconds": round(elapsed, 2), "audio_s": round(dur, 2),
            "s_per_audio_min": round(elapsed / (dur / 60), 3) if dur else None}


@contextmanager
def prepared(pre: Preprocessor, audio_path: str | Path, cache_dir: Path, *, audio_hash: str | None = None,
             keep: bool = True) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Yield ``(path of the processed audio, info)``. ``keep=False`` (cache disabled) processes into a
    temp file that is deleted afterwards; otherwise the file in ``cache_dir`` is reused or created."""
    info: dict[str, Any] = {"params": pre.cache_params()}
    if not keep:
        with tempfile.TemporaryDirectory(prefix="callguard-pre-") as d:
            p = Path(d) / "audio.wav"
            info.update(run(pre, audio_path, p), cached=False)
            yield p, info
        return
    path = cache_file(pre, audio_hash or file_hash(audio_path), cache_dir)
    with _LOCK:
        if path.exists():
            info["cached"] = True
        else:
            info.update(run(pre, audio_path, path), cached=False)
            log.info("preprocess %s -> %s (%.1fs)", Path(audio_path).name, path.name, info["seconds"])
    info["path"] = str(path)
    yield path, info
