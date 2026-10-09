"""Local machine translation with a transformers seq2seq model (NLLB-200 by default). UNTESTED.

Lazy import: needs ``transformers`` + ``torch`` (``uv sync --extra asr`` style extras on the GPU host).
NLLB has no Swiss German code; ``gsw`` is sent as Standard German (``deu_Latn``), which works poorly on
dialect spellings: prefer ``llm_translate`` from a gsw view, or translate the ``de`` view.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from callguard.plugins import Translator
from callguard.translate import translated_copy
from callguard.types import Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.translate")

NLLB_CODES = {"de": "deu_Latn", "gsw": "deu_Latn", "en": "eng_Latn", "fr": "fra_Latn", "it": "ita_Latn"}
_MODELS: dict[tuple[str, str], Any] = {}
_LOCK = threading.Lock()


class HFTranslator(Translator):
    def __init__(self, ctx: "Context", *, model: str = "facebook/nllb-200-distilled-600M", device: str = "cpu",
                 batch_size: int = 16, max_length: int = 400, source_lang: str | None = None):
        super().__init__(ctx, model=model, device=device, batch_size=batch_size, max_length=max_length,
                         source_lang=source_lang)
        self.model = model
        self.device = device
        self.batch_size = int(batch_size)
        self.max_length = int(max_length)
        self.source_lang = source_lang

    def cache_params(self) -> dict[str, Any]:
        return {"type": self.plugin_type, "model": self.model, "max_length": self.max_length,
                "source_lang": self.source_lang}  # device and batch size change speed only

    def _pipeline(self) -> tuple[Any, Any]:
        key = (self.model, self.device)
        with _LOCK:
            if key not in _MODELS:
                try:
                    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
                except ImportError as e:
                    raise ImportError("translator 'hf_mt' needs transformers + torch on this machine") from e
                tok = AutoTokenizer.from_pretrained(self.model)
                mdl = AutoModelForSeq2SeqLM.from_pretrained(self.model).to(self.device)
                _MODELS[key] = (tok, mdl)
            return _MODELS[key]

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        src = self.source_lang or transcript.lang or transcript.language or "de"
        if src not in NLLB_CODES or target_lang not in NLLB_CODES:
            raise ValueError(f"hf_mt: unsupported languages {src!r} -> {target_lang!r} (known: {list(NLLB_CODES)})")
        segs = [s for s in transcript.segments if s.text.strip()]
        tok, mdl = self._pipeline()
        tok.src_lang = NLLB_CODES[src]
        bos = tok.convert_tokens_to_ids(NLLB_CODES[target_lang])
        texts: dict[str, str] = {}
        for i in range(0, len(segs), self.batch_size):
            batch = segs[i:i + self.batch_size]
            enc = tok([s.text for s in batch], return_tensors="pt", padding=True, truncation=True,
                      max_length=self.max_length).to(self.device)
            out = mdl.generate(**enc, forced_bos_token_id=bos, max_length=self.max_length)
            for seg, text in zip(batch, tok.batch_decode(out, skip_special_tokens=True)):
                texts[seg.id] = text.strip()
        return translated_copy(transcript, texts, target_lang, f"hf_mt:{self.model}", {"model": self.model})
