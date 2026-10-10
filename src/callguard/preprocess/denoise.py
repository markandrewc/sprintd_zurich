"""Speech denoising with sherpa-onnx ``OfflineSpeechDenoiser`` (no torch, CPU is fine).

Models (16 kHz, Apache-2.0, ``scripts/download_models.sh denoise``):

- ``models/denoise/dpdfnet2.onnx`` (default): DPDFNet, a DeepFilterNet2 derivative with a dual-path
  RNN, 10 MB. About 4 s per audio minute on one CPU thread.
- ``models/denoise/gtcrn_simple.onnx``: GTCRN, 0.5 MB, roughly 2x faster, weaker.

Heavy denoising can *raise* Whisper's error rate (it removes speech cues along with the noise). Two
knobs keep it mild: ``attenuation_limit_db`` (DPDFNet only; 0 = no limit, the sherpa default; e.g. 12
caps noise suppression at 12 dB) and ``mix`` (1.0 = fully denoised, 0.7 = 70 % denoised + 30 % original;
the models have no delay, so the two signals are aligned).
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from callguard.config import ROOT
from callguard.plugins import Preprocessor

if TYPE_CHECKING:
    from callguard.context import Context

ARCHS = ("dpdfnet", "gtcrn")
_MODELS: dict[tuple, tuple[Any, threading.Lock]] = {}
_LOCK = threading.Lock()


def _resolve(model: str) -> Path:
    p = Path(model).expanduser()
    p = p if p.is_absolute() else ROOT / p
    if not p.is_file():
        raise FileNotFoundError(f"denoise model {model!r} not found (looked at {p}). "
                                f"Run scripts/download_models.sh denoise")
    return p


def _resample(y: np.ndarray, src: int, dst: int) -> np.ndarray:
    if src == dst:
        return y
    n = int(round(len(y) * dst / src))
    return np.interp(np.arange(n) * (src / dst), np.arange(len(y)), y).astype(np.float32)


class SherpaDenoiser(Preprocessor):
    """``model``: ONNX file (relative to the project root). ``arch``: dpdfnet | gtcrn | auto (from the
    file name). ``num_threads`` changes speed only and stays out of the cache key."""

    def __init__(self, ctx: "Context", model: str = "models/denoise/dpdfnet2.onnx", arch: str = "auto",
                 attenuation_limit_db: float = 0.0, mix: float = 1.0, provider: str = "cpu",
                 num_threads: int = 1):
        if arch == "auto":
            arch = "gtcrn" if "gtcrn" in Path(model).name.lower() else "dpdfnet"
        if arch not in ARCHS:
            raise ValueError(f"denoise_sherpa arch must be one of {ARCHS} or 'auto', got {arch!r}")
        if not 0.0 <= float(mix) <= 1.0:
            raise ValueError(f"denoise_sherpa mix must be in [0, 1], got {mix}")
        if arch == "gtcrn" and attenuation_limit_db:
            raise ValueError("attenuation_limit_db is a DPDFNet option; gtcrn has none")
        super().__init__(ctx, model=model, arch=arch, attenuation_limit_db=float(attenuation_limit_db),
                         mix=float(mix), provider=provider, num_threads=int(num_threads))
        self.model_path = _resolve(model)

    def cache_params(self) -> dict[str, Any]:
        return {k: v for k, v in super().cache_params().items() if k != "num_threads"}

    def _denoiser(self) -> tuple[Any, threading.Lock]:
        """(shared denoiser, its lock): instances with the same model share one ONNX session."""
        p = self.params
        key = (str(self.model_path), p["arch"], p["attenuation_limit_db"], p["provider"], p["num_threads"])
        with _LOCK:
            if key not in _MODELS:
                try:
                    import sherpa_onnx as so
                except ImportError as e:
                    raise ImportError("preprocess 'denoise_sherpa' needs sherpa-onnx: uv sync --extra diarize") from e
                if p["arch"] == "dpdfnet":
                    arch_cfg = {"dpdfnet": so.OfflineSpeechDenoiserDpdfNetModelConfig(
                        model=str(self.model_path), attenuation_limit_db=p["attenuation_limit_db"])}
                else:
                    arch_cfg = {"gtcrn": so.OfflineSpeechDenoiserGtcrnModelConfig(model=str(self.model_path))}
                cfg = so.OfflineSpeechDenoiserConfig(model=so.OfflineSpeechDenoiserModelConfig(
                    num_threads=p["num_threads"], provider=p["provider"], **arch_cfg))
                if not cfg.validate():
                    raise ValueError(f"sherpa-onnx rejected the denoiser config for {self.model_path}")
                _MODELS[key] = (so.OfflineSpeechDenoiser(cfg), threading.Lock())
            return _MODELS[key]

    def process(self, samples: np.ndarray, sr: int) -> np.ndarray:
        x = np.ascontiguousarray(samples, dtype=np.float32)
        den, lock = self._denoiser()
        with lock:  # not documented as thread-safe
            r = den(x, sr)
        y = _resample(np.asarray(r.samples, dtype=np.float32), int(r.sample_rate), sr)
        n = len(x)
        y = y[:n] if len(y) >= n else np.concatenate([y, np.zeros(n - len(y), dtype=np.float32)])
        mix = self.params["mix"]
        return y if mix >= 1.0 else (mix * y + (1.0 - mix) * x).astype(np.float32)
