"""LLM translator: segments in batches as JSON, a few preceding segments as context.

Request (user message): the context lines (source language, NOT to be translated) and the batch as
JSON ``[{"id": "S007", "speaker": "advisor", "text": "..."}]``. Answer (JSON schema enforced where the
backend supports it): ``{"translations": [{"id": "S007", "text": "..."}]}``.

Robustness: a batch answer that misses ids, invents ids or comes back empty is not trusted for those
segments; each missing segment is asked again on its own (with context). A segment that still fails
keeps its source text and the transcript is marked ``degraded`` (so the pipeline does not cache it).
Numbers, amounts, codes, IBANs, card numbers and names must stay verbatim: the patterns check and the
officer read them from the translated view.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from callguard.llm.jsonutil import chat_json
from callguard.plugins import LLM, Translator
from callguard.translate import lang_name, translated_copy
from callguard.types import Segment, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.translate")

PROMPT_VERSION = "translate-v1"

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
            },
        },
    },
    "required": ["translations"],
}

SYSTEM = """You translate transcripts of phone calls between a Swiss bank and its customers for a \
compliance review. Translate each given segment from {src} into {tgt}.

Rules:
- Translate faithfully and completely, segment by segment. Do not summarise, merge, split, soften or \
explain. Keep hedges, negations, hesitations and the speaker's tone ("not yet public", "between us").
- Copy verbatim: numbers, amounts, currencies, dates, times, percentages, account/card/IBAN numbers, \
PINs, TANs and other codes, names of people, companies, products and places.
- Speech recognition errors stay as they are; do not invent content that is not there.
- Context lines are only there to understand the conversation: do NOT translate them.
- Answer with JSON only: {{"translations": [{{"id": "<segment id>", "text": "<translation>"}}]}} with \
exactly one entry per given segment id, in the given order."""


def _speaker(seg: Segment) -> str:
    return seg.role if seg.role != "unknown" else (seg.speaker or "unknown")


class LLMTranslator(Translator):
    """``llm``: name of a configured LLM (``llms:`` block). ``batch_size`` segments per request,
    ``context`` preceding segments as (untranslated) context, ``concurrency`` parallel batches (speed
    only, not part of the cache key)."""

    def __init__(self, ctx: "Context", *, llm: str = "default", batch_size: int = 12, context: int = 3,
                 concurrency: int = 1, temperature: float = 0.0, max_tokens: int | None = None,
                 source_lang: str | None = None):
        if int(batch_size) < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        if int(concurrency) < 1:
            raise ValueError(f"concurrency must be >= 1, got {concurrency}")
        super().__init__(ctx, llm=llm, batch_size=batch_size, context=context, concurrency=concurrency,
                         temperature=temperature, max_tokens=max_tokens, source_lang=source_lang)
        self.llm_name = llm
        self.batch_size = int(batch_size)
        self.context = max(0, int(context))
        self.concurrency = int(concurrency)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens) if max_tokens else None
        self.source_lang = source_lang

    def _llm(self) -> LLM:
        return self.ctx.llm(self.llm_name)

    def cache_params(self) -> dict[str, Any]:
        # the real model (served identity), not the alias: a model swap must re-translate
        return {"type": self.plugin_type, "llm": self._llm().cache_params(), "batch_size": self.batch_size,
                "context": self.context, "temperature": self.temperature, "max_tokens": self.max_tokens,
                "source_lang": self.source_lang, "prompt_version": PROMPT_VERSION}

    # -- prompting --------------------------------------------------------------------------------

    def messages(self, batch: list[Segment], context: list[Segment], src: str | None,
                 tgt: str) -> list[dict[str, str]]:
        parts = []
        if context:
            parts.append("Context (do not translate):\n" + "\n".join(
                f"[{s.id} {_speaker(s)}] {s.text.strip()}" for s in context))
        items = [{"id": s.id, "speaker": _speaker(s), "text": s.text.strip()} for s in batch]
        parts.append(f"Segments to translate into {lang_name(tgt)}:\n" + json.dumps(items, ensure_ascii=False))
        return [{"role": "system", "content": SYSTEM.format(src=lang_name(src), tgt=lang_name(tgt))},
                {"role": "user", "content": "\n\n".join(parts)}]

    def _budget(self, batch: list[Segment]) -> int:
        if self.max_tokens:
            return self.max_tokens
        chars = sum(len(s.text) for s in batch)
        return min(8192, 256 + chars + 24 * len(batch))  # ~1 token per char is generous for de/en

    def _ask(self, llm: LLM, batch: list[Segment], context: list[Segment], src: str | None,
             tgt: str) -> dict[str, str]:
        """id -> translated text for the ids of ``batch`` the answer got right (others left out)."""
        wanted = {s.id for s in batch}
        out = chat_json(llm, self.messages(batch, context, src, tgt), SCHEMA, temperature=self.temperature,
                        max_tokens=self._budget(batch))[0]
        got: dict[str, str] = {}
        for item in out.get("translations") or []:
            if not isinstance(item, dict):
                continue
            sid, text = str(item.get("id", "")).strip(), item.get("text")
            if sid in wanted and isinstance(text, str) and text.strip() and sid not in got:
                got[sid] = " ".join(text.split())
        return got

    def _batch(self, llm: LLM, segs: list[Segment], start: int, src: str | None,
               tgt: str) -> tuple[dict[str, str], list[str], list[str]]:
        """Translate segs[start:start+batch_size]. Returns (texts, retried ids, failed ids)."""
        batch = segs[start:start + self.batch_size]
        context = segs[max(0, start - self.context):start]
        try:
            got = self._ask(llm, batch, context, src, tgt)
        except Exception as e:
            log.warning("translate: batch at %s failed (%s), falling back to single segments", batch[0].id, e)
            got = {}
        retried, failed = [], []
        if len(batch) > 1:
            for i, seg in enumerate(batch):
                if seg.id in got:
                    continue
                retried.append(seg.id)
                pos = start + i
                try:
                    one = self._ask(llm, [seg], segs[max(0, pos - self.context):pos], src, tgt)
                except Exception as e:
                    log.warning("translate: segment %s failed: %s", seg.id, e)
                    one = {}
                if seg.id in one:
                    got[seg.id] = one[seg.id]
        failed = [s.id for s in batch if s.id not in got]
        return got, retried, failed

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        src = self.source_lang or transcript.lang or transcript.language
        segs = [s for s in transcript.segments if s.text.strip()]
        if not segs or src == target_lang:
            return translated_copy(transcript, {}, target_lang, f"llm_translate:{self._llm().model_id}",
                                   {"skipped": "same language" if segs else "empty transcript"})
        llm = self._llm()
        starts = list(range(0, len(segs), self.batch_size))
        if self.concurrency > 1 and len(starts) > 1:
            with ThreadPoolExecutor(max_workers=min(self.concurrency, len(starts))) as ex:
                outs = list(ex.map(lambda st: self._batch(llm, segs, st, src, target_lang), starts))
        else:
            outs = [self._batch(llm, segs, st, src, target_lang) for st in starts]
        texts: dict[str, str] = {}
        retried: list[str] = []
        failed: list[str] = []
        for got, r, f in outs:
            texts.update(got)
            retried += r
            failed += f
        meta: dict[str, Any] = {"model": llm.model_id, "prompt_version": PROMPT_VERSION,
                                "batches": len(starts), "segments": len(segs)}
        if retried:
            meta["retried_segments"] = retried
        if failed and len(failed) == len(segs):  # server down / wrong model: no view, not a fake one
            raise RuntimeError(f"llm_translate: no segment of {transcript.call_id} could be translated "
                               f"({len(segs)} segments, model {llm.model_id})")
        if failed:
            meta["untranslated_segments"] = failed
            meta["degraded"] = f"{len(failed)} of {len(segs)} segments kept their source text"
            log.warning("translate %s: %s", transcript.call_id, meta["degraded"])
        return translated_copy(transcript, texts, target_lang, f"llm_translate:{llm.model_id}", meta)
