"""Swiss German as spoken: each segment of a transcript re-transcribed from the AUDIO by a character CTC model
trained on Swiss German dialect transcriptions (default: scasutt/wav2vec2-large-xlsr-52_Swiss_German, Apache-2.0,
SwissDial; exported to ONNX by scripts/gsw/export_w2v_onnx.py, so only onnxruntime is needed, no torch).

Meant for a DISPLAY-ONLY view (config ``display_views``): the source transcript gives the segments (ids, times,
speakers, roles), the model writes what is said in that time span in dialect spelling, so the view plays in sync
with the recording. Measured against the dialect scripts of test50 (scripts/gsw/eval_gsw.py, 8 calls): turn chrF
~85 vs ~57 for an LLM rewriting the Standard German transcript into Zürich German and ~49 for the Standard German
transcript itself; on 35 case calls (call-level chrF) 71 vs 63 clean, 67 vs 63 noisy. Output is lower case without punctuation (the model has none); ``cosmetics`` capitalises the
first letter and copies the source segment's final ``.?!``. Names and rare words come out phonetically.

``pad_end``: seconds added after each segment end (Whisper's segment ends are early; without it the last word is
cut), capped at the next segment's start so no word is heard twice. Reads the recording, so the pipeline adds the
audio hash to the translation cache key (``reads_audio``).
"""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from callguard.config import ROOT
from callguard.plugins import Translator
from callguard.translate import translated_copy
from callguard.types import Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.translate")

DEFAULT_MODEL = "models/asr/wav2vec2-gsw-swissdial-onnx"
VERSION = "ctc-dialect-v1"
SR = 16000


def ctc_greedy(ids: np.ndarray, vocab: dict[int, str], blank: int, delimiter: str = "|") -> str:
    """Greedy CTC decoding: collapse repeats, drop blanks, word delimiter -> space."""
    out, prev = [], None
    for i in ids.tolist():
        if i != prev and i != blank:
            out.append(vocab.get(i, ""))
        prev = i
    text = "".join(" " if c == delimiter else ("" if c.startswith("[") else c) for c in out)
    return " ".join(text.split())


def tidy(text: str, source_text: str) -> str:
    """First letter upper case, the source segment's final ``.?!`` appended (display cosmetics only)."""
    if not text:
        return text
    text = text[0].upper() + text[1:]
    end = source_text.rstrip()[-1:] if source_text.strip() else ""
    return text + end if end in ".?!" else text


class CTCDialect(Translator):
    reads_audio = True  # the pipeline adds the audio hash to the cache key

    def __init__(self, ctx: "Context", *, model: str = DEFAULT_MODEL, pad_start: float = 0.0, pad_end: float = 0.6,
                 min_seconds: float = 0.1, cosmetics: bool = True, threads: int = 4, device: str = "cpu"):
        super().__init__(ctx, model=model, pad_start=pad_start, pad_end=pad_end, min_seconds=min_seconds,
                         cosmetics=cosmetics, threads=threads, device=device)
        self.model = model
        self.pad_start, self.pad_end = float(pad_start), float(pad_end)
        self.min_seconds = float(min_seconds)
        self.cosmetics = bool(cosmetics)
        self.threads, self.device = int(threads), device
        self._sess = None
        self._lock = threading.Lock()

    @property
    def model_dir(self) -> Path:
        p = Path(self.model)
        return p if p.is_absolute() else ROOT / p

    def cache_params(self) -> dict[str, Any]:
        return {"type": self.plugin_type, "model": Path(self.model).name, "pad_start": self.pad_start,
                "pad_end": self.pad_end, "min_seconds": self.min_seconds, "cosmetics": self.cosmetics,
                "version": VERSION}

    def _load(self):
        with self._lock:
            if self._sess is None:
                import onnxruntime as ort

                d = self.model_dir
                if not (d / "model.onnx").exists():
                    raise FileNotFoundError(f"ctc_dialect: no model at {d} (scripts/gsw/export_w2v_onnx.py)")
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = self.threads
                providers = (["CUDAExecutionProvider", "CPUExecutionProvider"] if self.device == "cuda"
                             else ["CPUExecutionProvider"])
                vocab = json.loads((d / "vocab.json").read_text())
                meta = json.loads((d / "meta.json").read_text()) if (d / "meta.json").exists() else {}
                self._vocab = {int(i): tok for tok, i in vocab.items()}
                self._blank = int(vocab.get(meta.get("pad_token", "[PAD]"), 0))
                self._delim = meta.get("word_delimiter_token", "|")
                self._normalize = bool(meta.get("do_normalize", True))
                self._sess = ort.InferenceSession(str(d / "model.onnx"), opts, providers=providers)
        return self._sess

    def recognize(self, samples: np.ndarray) -> str:
        """Dialect text of one chunk of 16 kHz mono audio."""
        sess = self._load()
        x = samples.astype(np.float32)
        if self._normalize:
            x = (x - x.mean()) / np.sqrt(x.var() + 1e-7)
        logits = sess.run(None, {"input_values": x[None, :]})[0][0]
        return ctc_greedy(logits.argmax(-1), self._vocab, self._blank, self._delim)

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        from callguard.audio import load_audio

        if not transcript.audio_path or not Path(transcript.audio_path).exists():
            raise FileNotFoundError(f"ctc_dialect: recording of {transcript.call_id} not found "
                                    f"({transcript.audio_path})")
        audio = load_audio(transcript.audio_path, sr=SR)
        segs = transcript.segments
        texts: dict[str, str] = {}
        skipped: list[str] = []
        for i, s in enumerate(segs):
            end = s.end + self.pad_end
            if i + 1 < len(segs):
                end = min(end, max(s.end, segs[i + 1].start))
            a, b = int(max(0.0, s.start - self.pad_start) * SR), int(end * SR)
            chunk = audio[a:b]
            if len(chunk) < self.min_seconds * SR:
                skipped.append(s.id)
                texts[s.id] = ""
                continue
            text = self.recognize(chunk)
            texts[s.id] = tidy(text, s.text) if self.cosmetics else text
        meta = {"model": Path(self.model).name, "version": VERSION, "segments": len(segs), "pad_end": self.pad_end}
        if skipped:
            meta["too_short"] = skipped
        return translated_copy(transcript, texts, target_lang, f"ctc_dialect:{Path(self.model).name}", meta)
