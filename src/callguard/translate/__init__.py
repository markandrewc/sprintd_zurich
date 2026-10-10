"""Translator plugins: one transcript view -> the same call in another language.

Built-ins (``translator`` kind in :mod:`callguard.registry`): ``llm_translate`` (any configured LLM,
batched JSON), ``hf_mt`` (NLLB via transformers, untested), ``identity`` (tests / offline demo),
``llm_correct`` (multi-source: fuses several ASR hypotheses of one call into one transcript, A4).
"""

from __future__ import annotations

from typing import Any

from callguard.types import Transcript

LANG_NAMES = {"gsw": "Swiss German (Schweizerdeutsch dialect)", "de": "Standard German", "en": "English",
              "fr": "French", "it": "Italian"}


def lang_name(code: str | None) -> str:
    return LANG_NAMES.get(code or "", code or "the source language")


def translated_copy(source: Transcript, texts: dict[str, str], target_lang: str, backend: str,
                    meta: dict[str, Any] | None = None) -> Transcript:
    """``source`` with each segment's text replaced by ``texts[id]`` (missing ids keep the source text).

    Keeps ids, start/end, speaker, role, confidence; drops word timestamps (they belong to the
    source words). ``meta`` lands in ``Transcript.meta["translation"]``."""
    segments = [seg.model_copy(update={"text": texts.get(seg.id, seg.text), "words": []})
                for seg in source.segments]
    out_meta = {"translation": {"from_view": source.view, "from_lang": source.lang, "to_lang": target_lang,
                                "backend": backend, **(meta or {})}}
    if (meta or {}).get("degraded"):
        out_meta["degraded"] = meta["degraded"]  # type: ignore[index]
    return Transcript(call_id=source.call_id, audio_path=source.audio_path, duration=source.duration,
                      language=target_lang, segments=segments,
                      asr_backend=f"{source.asr_backend} -> {backend}", meta=out_meta,
                      view=source.view, lang=target_lang)
