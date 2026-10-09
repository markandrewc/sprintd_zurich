"""faster-whisper (CTranslate2) backend: the default ASR. int8 on CPU, float16 on GPU, same code.

Audio is decoded with :func:`callguard.audio.load_audio` and passed as a numpy array because
faster-whisper's own PyAV decoding is broken in this environment.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.asr import (clean_text, clean_words, drop_inherited, geometric_mean, model_name,
                           resolve_model)
from callguard.audio import SR, load_audio
from callguard.plugins import ASRBackend
from callguard.types import Segment, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.asr")

# Loaded models shared across plugin instances: the UI and the eval scripts build several Pipelines
# per process and loading Whisper costs seconds and ~1 GB each time.
_MODELS: dict[tuple[str, str, str, int], Any] = {}
_LOCK = threading.Lock()


def check_ct2_dir(path: Path) -> None:
    """Fail early on model dirs faster-whisper would load "successfully" but decode wrongly."""
    if not path.is_dir():
        raise NotADirectoryError(f"faster-whisper model {path} is not a directory")
    if not (path / "model.bin").exists():
        if (path / "pytorch_model.bin").exists() or any(path.glob("*.safetensors")):
            raise ValueError(
                f"{path} is a transformers checkpoint, not CTranslate2. Convert it with "
                f"`ct2-transformers-converter --model {path} --output_dir {path}-ct2 --quantization int8 "
                f"--copy_files tokenizer.json preprocessor_config.json`, or use `asr.type: hf_whisper`.")
        raise FileNotFoundError(f"{path} has no model.bin: not a CTranslate2 Whisper model directory")
    if not (path / "tokenizer.json").exists():
        raise FileNotFoundError(
            f"{path} has no tokenizer.json. faster-whisper would silently fall back to the "
            f"openai/whisper-tiny tokenizer, which garbles large-v3/turbo output. Copy tokenizer.json "
            f"(and preprocessor_config.json) from the source checkpoint, e.g. `huggingface-cli download "
            f"<source-repo> tokenizer.json preprocessor_config.json --local-dir {path}`.")


def _load_model(path: str, device: str, compute_type: str, cpu_threads: int) -> Any:
    key = (path, device, compute_type, cpu_threads)
    with _LOCK:
        if key in _MODELS:
            return _MODELS[key]
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise ImportError("asr type 'faster_whisper' needs faster-whisper: uv sync --extra asr") from e
        t0 = time.time()
        model = WhisperModel(path, device=device, compute_type=compute_type, cpu_threads=cpu_threads)
        n_model = getattr(model.model, "n_mels", None)
        n_feat = getattr(getattr(model.feature_extractor, "mel_filters", None), "shape", (None,))[0]
        if n_model and n_feat and n_model != n_feat:
            raise RuntimeError(
                f"{path}: model expects {n_model} mel bins but the feature extractor makes {n_feat}. "
                f"preprocessor_config.json is missing or wrong (large-v3/turbo need feature_size 128).")
        log.info("loaded faster-whisper %s (%s/%s) in %.1fs", path, device, compute_type, time.time() - t0)
        _MODELS[key] = model
        return model


def segment_confidence(avg_logprob: float, no_speech_prob: float, word_probs: list[float]) -> float:
    """0..1 confidence for one segment.

    faster-whisper computes ``avg_logprob`` once per 30 s decoding window, so all segments of a window
    share it. The geometric mean of the segment's own word probabilities is the same quantity
    (exp of the mean log-probability) restricted to this segment, so it is used when available.
    """
    base = geometric_mean(word_probs)
    if base is None:
        base = math.exp(min(float(avg_logprob), 0.0))
    speech = 1.0 - min(max(float(no_speech_prob), 0.0), 1.0)
    return round(min(max(base * speech, 0.0), 1.0), 4)


class FasterWhisperASR(ASRBackend):
    """``model``: local CTranslate2 dir (relative to the project root) or a HF repo id / size name.

    ``cpu_threads=0`` keeps CTranslate2's default (OMP_NUM_THREADS or 4), leaving cores for the LLM.
    """

    def __init__(self, ctx: Context, model: str, device: str = "cpu", compute_type: str = "int8",
                 language: str | None = "de", beam_size: int = 1, vad_filter: bool = True,
                 word_timestamps: bool = True, initial_prompt: str | None = None, cpu_threads: int = 0,
                 condition_on_previous_text: bool = True, vad_parameters: dict[str, Any] | None = None,
                 hotwords: str | None = None, **inherited: Any):
        super().__init__(ctx, model=model, device=device, compute_type=compute_type, language=language,
                         beam_size=beam_size, vad_filter=vad_filter, word_timestamps=word_timestamps,
                         initial_prompt=initial_prompt, cpu_threads=cpu_threads,
                         condition_on_previous_text=condition_on_previous_text,
                         vad_parameters=vad_parameters, hotwords=hotwords)
        self.ignored_params = drop_inherited("faster_whisper", inherited)
        self.model_path, self.is_local = resolve_model(model)
        if self.is_local:
            check_ct2_dir(Path(self.model_path))
        self.name = model_name(self.model_path, self.is_local)
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = int(cpu_threads)
        self.options: dict[str, Any] = {
            "language": language or None,
            "beam_size": int(beam_size),
            "vad_filter": bool(vad_filter),
            "vad_parameters": dict(vad_parameters) if vad_parameters else None,
            "word_timestamps": bool(word_timestamps),
            "initial_prompt": " ".join(initial_prompt.split()) if initial_prompt else None,
            "condition_on_previous_text": bool(condition_on_previous_text),
            "hotwords": hotwords or None,
        }

    def cache_params(self) -> dict[str, Any]:
        # thread count changes speed, not the transcript: a demo run with more cores reuses the cache
        return {k: v for k, v in super().cache_params().items() if k != "cpu_threads"}

    def _model(self) -> Any:
        return _load_model(self.model_path, self.device, self.compute_type, self.cpu_threads)

    def _decode(self, audio: Any, options: dict[str, Any]) -> tuple[list[Any], Any]:
        segments, info = self._model().transcribe(audio, **options)
        return list(segments), info  # the generator does the actual decoding

    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        audio = load_audio(audio_path)
        duration = len(audio) / SR
        meta: dict[str, Any] = {"model": self.model_path, "params": dict(self.options),
                                "device": self.device, "compute_type": self.compute_type}
        self._model()  # load errors are config errors: let them raise before the retry logic
        t0 = time.time()
        try:
            raw, info = self._decode(audio, self.options)
        except Exception as e:
            fallback = {**self.options, "vad_filter": False, "word_timestamps": False}
            if fallback == self.options:
                raise
            # VAD (onnxruntime) and word alignment are the fragile parts; plain decoding still
            # gives the checks text with segment timestamps.
            log.warning("faster-whisper failed on %s (%r); retrying without VAD and word timestamps",
                        call_id, e)
            meta["degraded"] = f"retried without VAD and word timestamps after: {e!r}"
            meta["params"] = dict(fallback)
            try:
                raw, info = self._decode(audio, fallback)
            except Exception as e2:
                raise RuntimeError(f"faster-whisper failed on {call_id}: {e!r}; fallback: {e2!r}") from e2
        elapsed = time.time() - t0

        segments: list[Segment] = []
        for s in raw:
            text = clean_text(s.text)
            if not text:
                continue
            raw_words = list(s.words or [])
            segments.append(Segment(
                id=f"S{len(segments) + 1:03d}",
                start=round(float(s.start), 3),
                end=round(max(float(s.end), float(s.start)), 3),
                text=text,
                confidence=segment_confidence(s.avg_logprob, s.no_speech_prob,
                                              [w.probability for w in raw_words if w.probability is not None]),
                words=clean_words((w.start, w.end, w.word, w.probability) for w in raw_words),
            ))

        meta.update({
            "language_probability": round(float(info.language_probability), 4),
            "elapsed_s": round(elapsed, 2),
            "rtf": round(elapsed / duration, 3) if duration else None,
            "speech_s": round(float(getattr(info, "duration_after_vad", duration) or 0.0), 2),
            "mean_confidence": _weighted_confidence(segments),
        })
        if not segments:
            log.warning("faster-whisper recognised no speech in %s", call_id)
            meta["warnings"] = ["no speech recognised"]
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=round(duration, 3),
                          language=info.language, segments=segments,
                          asr_backend=f"faster_whisper:{self.name}", meta=meta)


def _weighted_confidence(segments: list[Segment]) -> float | None:
    """Duration-weighted mean, so a long mumbled passage counts more than a short "Ja"."""
    pairs = [(max(s.end - s.start, 0.1), s.confidence) for s in segments if s.confidence is not None]
    total = sum(w for w, _ in pairs)
    return round(sum(w * c for w, c in pairs) / total, 4) if total else None
