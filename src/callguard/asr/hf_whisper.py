"""transformers backend for Whisper checkpoints that only exist in transformers format on the HF Hub
(e.g. ``Flix-AI/flix-swissgerman-full``, ``gcoli/whisper-large-v3-swiss-german-mit``) and for our own
fine-tunes before they are converted to CTranslate2.

transformers/torch are deliberately not project dependencies (too heavy for the laptop setup), so
they are imported only when this backend is used.
"""

from __future__ import annotations

import inspect
import logging
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.asr import clean_text, clean_words, drop_inherited, model_name, resolve_model
from callguard.audio import SR, load_audio
from callguard.plugins import ASRBackend
from callguard.types import Segment, Transcript, Word

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.asr")

INSTALL_HINT = "uv pip install transformers torch accelerate"
SENTENCE_END = (".", "?", "!", "…")

_PIPES: dict[tuple, Any] = {}
_LOCK = threading.Lock()


def require_transformers() -> tuple[Any, Any]:
    try:
        import torch
        import transformers
    except ImportError as e:
        raise ImportError(f"asr type 'hf_whisper' needs transformers + torch: {INSTALL_HINT}") from e
    return transformers, torch


def group_chunks(chunks: list[dict[str, Any]], *, word_level: bool = True, max_gap: float = 0.8,
                 max_words: int = 60, duration: float | None = None) -> list[Segment]:
    """transformers ASR pipeline ``chunks`` -> Segments.

    Word-level chunks are grouped into sentence-like segments: a segment ends at sentence punctuation,
    before a pause longer than ``max_gap`` seconds, or after ``max_words`` words (models that emit no
    punctuation would otherwise produce one segment per call). Segment-level chunks
    (``return_timestamps=True``) map one-to-one. A missing end time (transformers leaves the last chunk
    open) becomes ``duration`` for segments and ``start`` for words, so a trailing "?" does not
    stretch the word before it.
    """
    def times(c: dict[str, Any]) -> tuple[float, float | None]:
        ts = c.get("timestamp") or (None, None)
        start = float(ts[0]) if ts[0] is not None else 0.0
        if len(ts) > 1 and ts[1] is not None:
            return start, float(ts[1])
        return start, (None if word_level else duration)

    segments: list[Segment] = []

    def flush(words: list[Word]) -> None:
        if words:
            segments.append(Segment(id=f"S{len(segments) + 1:03d}", start=words[0].start,
                                    end=max(words[-1].end, words[0].start),
                                    text=" ".join(w.text for w in words), words=words))

    if not word_level:
        for c in chunks:
            text = clean_text(c.get("text", ""))
            if not text:
                continue
            start, end = times(c)
            segments.append(Segment(id=f"S{len(segments) + 1:03d}", start=round(start, 3),
                                    end=round(max(end if end is not None else start, start), 3), text=text))
        return segments

    words = clean_words((*times(c), c.get("text", ""), None) for c in chunks)
    cur: list[Word] = []
    for w in words:
        if cur and w.start - cur[-1].end > max_gap:
            flush(cur)
            cur = []
        cur.append(w)
        if w.text.endswith(SENTENCE_END) or len(cur) >= max_words:
            flush(cur)
            cur = []
    flush(cur)
    return segments


def _resolve_dtype(torch: Any, torch_dtype: str, device: str) -> Any:
    if torch_dtype == "auto":
        return torch.float16 if device.startswith("cuda") else torch.float32
    return getattr(torch, torch_dtype)


class HFWhisperASR(ASRBackend):
    """No per-segment confidence: the transformers pipeline exposes no token probabilities."""

    def __init__(self, ctx: Context, model: str, device: str = "cpu", chunk_length_s: float = 30,
                 batch_size: int = 8, language: str | None = "de", torch_dtype: str = "auto",
                 return_word_timestamps: bool = True, **inherited: Any):
        super().__init__(ctx, model=model, device=device, chunk_length_s=chunk_length_s,
                         batch_size=batch_size, language=language, torch_dtype=torch_dtype,
                         return_word_timestamps=return_word_timestamps)
        self.ignored_params = drop_inherited("hf_whisper", inherited)
        self.model_path, self.is_local = resolve_model(model)
        self.name = model_name(self.model_path, self.is_local)
        self.device = device
        self.chunk_length_s = chunk_length_s
        self.batch_size = int(batch_size)
        self.language = language or None
        self.torch_dtype = torch_dtype
        self.return_word_timestamps = bool(return_word_timestamps)

    def _pipe(self) -> Any:
        transformers, torch = require_transformers()
        device = self.device
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"
        key = (self.model_path, device, self.torch_dtype, self.chunk_length_s, self.batch_size)
        with _LOCK:
            if key not in _PIPES:
                t0 = time.time()
                dtype = _resolve_dtype(torch, self.torch_dtype, device)
                # transformers >= 4.56 renamed torch_dtype -> dtype
                dtype_kw = "dtype" if "dtype" in inspect.signature(transformers.pipeline).parameters else "torch_dtype"
                _PIPES[key] = transformers.pipeline(
                    "automatic-speech-recognition", model=self.model_path, device=device,
                    chunk_length_s=self.chunk_length_s, batch_size=self.batch_size, **{dtype_kw: dtype})
                log.info("loaded hf_whisper %s on %s in %.1fs", self.model_path, device, time.time() - t0)
            return _PIPES[key]

    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        pipe = self._pipe()
        audio = load_audio(audio_path)
        duration = len(audio) / SR
        generate_kwargs: dict[str, Any] = {"task": "transcribe"}
        if self.language:
            generate_kwargs["language"] = self.language
        meta: dict[str, Any] = {"model": self.model_path, "params": dict(self.params)}

        def run(timestamps: str | bool) -> dict[str, Any]:
            return pipe({"raw": audio, "sampling_rate": SR}, return_timestamps=timestamps,
                        generate_kwargs=dict(generate_kwargs))

        word_level = self.return_word_timestamps
        t0 = time.time()
        try:
            out = run("word" if word_level else True)
        except Exception as e:
            if not word_level:
                raise
            # fine-tunes often ship without alignment_heads, which word timestamps need
            log.warning("hf_whisper word timestamps failed on %s (%r); using segment timestamps", call_id, e)
            meta["degraded"] = f"segment timestamps only after: {e!r}"
            word_level = False
            out = run(True)
        elapsed = time.time() - t0

        segments = group_chunks(out.get("chunks") or [], word_level=word_level, duration=duration)
        text = clean_text(out.get("text", ""))
        if not segments and text:
            segments = [Segment(id="S001", start=0.0, end=round(duration, 3), text=text)]
        meta.update({"elapsed_s": round(elapsed, 2), "rtf": round(elapsed / duration, 3) if duration else None,
                     "word_timestamps": word_level})
        if not segments:
            log.warning("hf_whisper recognised no speech in %s", call_id)
            meta["warnings"] = ["no speech recognised"]
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=round(duration, 3),
                          language=self.language, segments=segments,
                          asr_backend=f"hf_whisper:{self.name}", meta=meta)
