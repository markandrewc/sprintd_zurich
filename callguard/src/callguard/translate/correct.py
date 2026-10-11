"""LLM transcript correction (docs/design/v2_plan.md §7 A4): several ASR hypotheses of one call -> one
Standard German transcript, as a multi-source view.

```yaml
de_fused:
  lang: de
  from: [de, de_large, de_vanilla]       # first = primary: its segments, times, speakers, roles are kept
  translator: {type: llm_correct, llm: default}
```

**Alignment.** Every alternative hypothesis is cut into timed units (its words if the segment has word
timestamps whose text matches the segment, else the segment's tokens spread evenly over its time
span). A unit goes to the primary segment containing its midpoint (several: the one with the nearest
centre), else to the nearest primary segment within ``max_gap`` seconds, else it is dropped (counted in
the meta). So each primary segment gets the text the other recognisers heard in the same time span.

**LLM.** Segments whose hypotheses all agree (after lower-casing and dropping punctuation) are kept
without asking. The rest go in batches as JSON ``[{"id", "speaker", "A", "B", "C"}]`` (A = primary)
with a few preceding primary segments as context; the answer is ``{"corrections": [{"id", "text"}]}``.
Robustness is the translator's (:mod:`callguard.translate.llm`): missing / invented ids are asked again
one by one; a segment that still fails keeps its primary text and the transcript is ``degraded`` (not
cached); no segment at all -> RuntimeError (no fake view). On top, a **support guard**: an answer whose
content words (>= 3 letters) are mostly not found (fuzzy) in any hypothesis of that segment is
rejected and the primary text kept, so the LLM cannot write content no recogniser heard. An empty
answer is accepted only if some hypothesis is empty too (a recogniser loop over silence/noise); else it
is rejected the same way. Rejections are answers (deterministic at temperature 0), not failures: the
view stays cacheable and lists them in ``meta.translation.unsupported_segments``.

Never part of the prompt: keyword lists, criteria, file names or labels (only "Swiss bank call").
"""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from rapidfuzz import fuzz

from callguard.llm.jsonutil import chat_json
from callguard.plugins import LLM, Translator
from callguard.types import Segment, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.translate")

PROMPT_VERSION = "correct-v1"
LETTERS = "ABCDEFGH"

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "corrections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
                "required": ["id", "text"],
            },
        },
    },
    "required": ["corrections"],
}

SYSTEM = """You repair speech-recognition transcripts of phone calls between a Swiss bank and its \
customers (Swiss German speech, written down as Standard German) for a compliance review. Several \
speech recognisers transcribed the same audio. For each segment you get hypothesis A (the main one) \
and the hypotheses {others} of the other recognisers for the same time span. The recognisers cut the \
speech slightly differently, so a word at the edge may belong to the neighbouring segment; an empty \
hypothesis means that recogniser heard nothing there. No recogniser is reliably better than the others.

Write the most plausible Standard German transcript of each segment.

Rules:
- Use only words that at least one hypothesis supports. Prefer the reading the hypotheses share or the \
one that makes sense in a bank call. Replace an obvious misrecognition (a nonsense word, wrong word \
boundaries) by the word another hypothesis has. Never add, complete, summarise or explain content that \
no hypothesis contains.
- Copy verbatim: names of people, companies, products and places, numbers, amounts, currencies, dates, \
percentages, account/card/IBAN numbers, PINs, TANs and other codes.
- Keep negations, hedges and the speaker's wording ("noch nicht öffentlich", "unter uns"); do not \
soften, rephrase or translate into dialect.
- If one hypothesis repeats the same few words over and over and the others do not, that is a \
recognition loop: leave the repetition out. The text may be empty only if the segment holds nothing \
but such a loop or noise.
- Context lines only help you follow the conversation: do NOT correct them.
- Answer with JSON only: {{"corrections": [{{"id": "<segment id>", "text": "<corrected text>"}}]}} with \
exactly one entry per given segment id, in the given order."""

_WORD = re.compile(r"[\wäöüÄÖÜß]+", re.UNICODE)


def _norm(text: str) -> str:
    return " ".join(_WORD.findall(text.lower()))


def _speaker(seg: Segment) -> str:
    return seg.role if seg.role != "unknown" else (seg.speaker or "unknown")


# --------------------------------------------------------------------------------------------
# alignment by time
# --------------------------------------------------------------------------------------------


def timed_units(transcript: Transcript) -> list[tuple[float, float, str]]:
    """(start, end, token) for every word of ``transcript``: real word timestamps where they match the
    segment text, else the segment's tokens spread evenly over the segment."""
    out: list[tuple[float, float, str]] = []
    for seg in transcript.segments:
        words = [w for w in seg.words if w.text.strip()]
        if words and "".join("".join(w.text.split()) for w in words) == "".join(seg.text.split()):
            out += [(w.start, max(w.end, w.start), w.text.strip()) for w in words]
            continue
        toks = seg.text.split()
        if not toks:
            continue
        step = max(seg.end - seg.start, 0.0) / len(toks)
        out += [(seg.start + i * step, seg.start + (i + 1) * step, tok) for i, tok in enumerate(toks)]
    return out


def align(primary: list[Segment], alternative: Transcript, max_gap: float = 1.5) -> tuple[dict[str, str], int]:
    """Text of ``alternative`` per primary segment id (by unit midpoint, see module doc) and the number
    of units that matched no primary segment within ``max_gap`` seconds."""
    buckets: dict[str, list[tuple[float, str]]] = {s.id: [] for s in primary}
    dropped = 0
    for start, end, tok in timed_units(alternative):
        mid = (start + end) / 2
        inside = [s for s in primary if s.start <= mid <= s.end]
        if inside:
            best = min(inside, key=lambda s: abs((s.start + s.end) / 2 - mid))
        else:
            dist, best = min(((max(s.start - mid, mid - s.end), s) for s in primary),
                             key=lambda x: x[0], default=(None, None))
            if best is None or dist is None or dist > max_gap:
                dropped += 1
                continue
        buckets[best.id].append((mid, tok))
    return {sid: " ".join(t for _, t in sorted(units, key=lambda u: u[0])) for sid, units in buckets.items()}, dropped


def support(text: str, hypotheses: list[str]) -> float:
    """Share of the content words (>= 3 letters) of ``text`` found (fuzzy, partial ratio >= 80, so split
    compounds and spelling variants count) in the hypotheses. 1.0 if ``text`` has no content words."""
    words = [w for w in _WORD.findall(text.lower()) if len(w) >= 3 and not w.isdigit()]
    if not words:
        return 1.0
    pool = " ".join(_norm(h) for h in hypotheses)
    return sum(1 for w in words if fuzz.partial_ratio(w, pool) >= 80) / len(words)


@dataclass
class Item:
    seg: Segment
    hyps: list[str]  # A (primary text), then one per alternative transcript
    context: list[Segment] = field(default_factory=list)

    def payload(self) -> dict[str, str]:
        return {"id": self.seg.id, "speaker": _speaker(self.seg),
                **{LETTERS[i]: h for i, h in enumerate(self.hyps)}}


# --------------------------------------------------------------------------------------------
# the plugin
# --------------------------------------------------------------------------------------------


class LLMCorrector(Translator):
    """``llm``: configured LLM name. ``batch_size`` segments per request, ``context`` preceding primary
    segments as context, ``concurrency`` parallel batches (speed only, not in the cache key),
    ``max_gap`` seconds a unit of an alternative may lie outside every primary segment and still be
    attached to the nearest one, ``min_support`` the support guard (0 = off), ``correct_alone``: also
    send segments no alternative covers (single-hypothesis clean-up; default off = kept as they are)."""

    multi_source = True

    def __init__(self, ctx: "Context", *, llm: str = "default", batch_size: int = 8, context: int = 2,
                 concurrency: int = 1, temperature: float = 0.0, max_tokens: int | None = None,
                 max_gap: float = 1.5, min_support: float = 0.6, correct_alone: bool = False):
        if int(batch_size) < 1:
            raise ValueError(f"batch_size must be >= 1, got {batch_size}")
        if int(concurrency) < 1:
            raise ValueError(f"concurrency must be >= 1, got {concurrency}")
        super().__init__(ctx, llm=llm, batch_size=batch_size, context=context, concurrency=concurrency,
                         temperature=temperature, max_tokens=max_tokens, max_gap=max_gap,
                         min_support=min_support, correct_alone=correct_alone)
        self.llm_name = llm
        self.batch_size = int(batch_size)
        self.context = max(0, int(context))
        self.concurrency = int(concurrency)
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens) if max_tokens else None
        self.max_gap = float(max_gap)
        self.min_support = float(min_support)
        self.correct_alone = bool(correct_alone)

    def _llm(self) -> LLM:
        return self.ctx.llm(self.llm_name)

    def cache_params(self) -> dict[str, Any]:
        return {"type": self.plugin_type, "llm": self._llm().cache_params(), "batch_size": self.batch_size,
                "context": self.context, "temperature": self.temperature, "max_tokens": self.max_tokens,
                "max_gap": self.max_gap, "min_support": self.min_support, "correct_alone": self.correct_alone,
                "prompt_version": PROMPT_VERSION}

    # -- prompting --------------------------------------------------------------------------------

    def messages(self, batch: list[Item]) -> list[dict[str, str]]:
        n = max(len(i.hyps) for i in batch)
        others = ", ".join(LETTERS[1:n]) or "B"
        parts = []
        context = batch[0].context
        if context:
            parts.append("Context (do not correct):\n" + "\n".join(
                f"[{s.id} {_speaker(s)}] {s.text.strip()}" for s in context))
        parts.append("Segments to correct:\n" + json.dumps([i.payload() for i in batch], ensure_ascii=False))
        return [{"role": "system", "content": SYSTEM.format(others=others)},
                {"role": "user", "content": "\n\n".join(parts)}]

    def _budget(self, batch: list[Item]) -> int:
        if self.max_tokens:
            return self.max_tokens
        chars = sum(max(len(h) for h in i.hyps) for i in batch)
        return min(8192, 256 + chars + 24 * len(batch))

    def _ask(self, llm: LLM, batch: list[Item]) -> tuple[dict[str, str], list[str]]:
        """id -> corrected text for the ids the answer got right, plus ids rejected by the support guard."""
        wanted = {i.seg.id: i for i in batch}
        out = chat_json(llm, self.messages(batch), SCHEMA, temperature=self.temperature,
                        max_tokens=self._budget(batch))[0]
        got: dict[str, str] = {}
        rejected: list[str] = []
        for entry in out.get("corrections") or []:
            if not isinstance(entry, dict):
                continue
            sid, text = str(entry.get("id", "")).strip(), entry.get("text")
            if sid not in wanted or sid in got or sid in rejected or not isinstance(text, str):
                continue
            text = " ".join(text.split())
            item = wanted[sid]
            # empty only if a recogniser heard nothing there; low support = words no hypothesis has
            if (not text and all(h.strip() for h in item.hyps)) or \
                    (self.min_support > 0 and support(text, item.hyps) < self.min_support):
                rejected.append(sid)
                got[sid] = item.hyps[0]  # keep the primary text: an answer, not a failure
                continue
            got[sid] = text
        return got, rejected

    def _batch(self, llm: LLM, items: list[Item]) -> tuple[dict[str, str], list[str], list[str], list[str]]:
        """(texts, retried ids, failed ids, rejected ids) for one batch."""
        try:
            got, rejected = self._ask(llm, items)
        except Exception as e:
            log.warning("correct: batch at %s failed (%s), falling back to single segments", items[0].seg.id, e)
            got, rejected = {}, []
        retried = []
        if len(items) > 1:
            for item in items:
                if item.seg.id in got:
                    continue
                retried.append(item.seg.id)
                try:
                    one, rej = self._ask(llm, [item])
                except Exception as e:
                    log.warning("correct: segment %s failed: %s", item.seg.id, e)
                    one, rej = {}, []
                got.update(one)
                rejected += rej
        failed = [i.seg.id for i in items if i.seg.id not in got]
        return got, retried, failed, rejected

    # -- the view ---------------------------------------------------------------------------------

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        """Single source: nothing to fuse; segments pass unchanged unless ``correct_alone``."""
        return self.translate_multi(transcript, [], target_lang)

    def items(self, primary: Transcript, alternatives: list[Transcript]) -> tuple[list[Item], dict[str, Any]]:
        """The segments worth asking about, with their hypotheses and context, plus alignment stats."""
        segs = list(primary.segments)
        aligned = [align(segs, alt, self.max_gap) for alt in alternatives]
        stats: dict[str, Any] = {"dropped_units": {alt.view: d for alt, (_, d) in zip(alternatives, aligned)},
                                 "agreeing": 0, "uncovered": 0}
        items: list[Item] = []
        for pos, seg in enumerate(segs):
            hyps = [seg.text.strip(), *(texts.get(seg.id, "") for texts, _ in aligned)]
            if not any(hyps):
                continue
            if not alternatives:
                if not self.correct_alone or not hyps[0]:
                    stats["uncovered"] += 1
                    continue
            elif len({_norm(h) for h in hyps}) == 1:
                stats["agreeing"] += 1
                continue
            ctx = [s for s in segs[max(0, pos - self.context):pos] if s.text.strip()] if self.context else []
            items.append(Item(seg, hyps, ctx))
        return items, stats

    def translate_multi(self, primary: Transcript, alternatives: list[Transcript], target_lang: str) -> Transcript:
        if len(alternatives) >= len(LETTERS):
            raise ValueError(f"llm_correct takes at most {len(LETTERS) - 1} alternatives")
        items, stats = self.items(primary, alternatives)
        texts: dict[str, str] = {}
        retried: list[str] = []
        failed: list[str] = []
        rejected: list[str] = []
        model = "-"
        n_batches = 0
        if items:
            llm = self._llm()
            model = llm.model_id
            batches = [items[i:i + self.batch_size] for i in range(0, len(items), self.batch_size)]
            n_batches = len(batches)
            if self.concurrency > 1 and len(batches) > 1:
                with ThreadPoolExecutor(max_workers=min(self.concurrency, len(batches))) as ex:
                    outs = list(ex.map(lambda b: self._batch(llm, b), batches))
            else:
                outs = [self._batch(llm, b) for b in batches]
            for got, r, f, rej in outs:
                texts.update(got)
                retried += r
                failed += f
                rejected += rej
        changed = [i.seg.id for i in items if i.seg.id in texts and _norm(texts[i.seg.id]) != _norm(i.hyps[0])]
        meta: dict[str, Any] = {"model": model, "prompt_version": PROMPT_VERSION,
                                "alternatives": [a.view for a in alternatives], "batches": n_batches,
                                "segments": len(primary.segments), "asked": len(items), "changed": len(changed),
                                **stats}
        if retried:
            meta["retried_segments"] = retried
        if rejected:
            meta["unsupported_segments"] = rejected  # support guard: primary text kept
        if items and len(failed) == len(items):
            raise RuntimeError(f"llm_correct: no segment of {primary.call_id} could be corrected "
                               f"({len(items)} segments, model {model})")
        if failed:
            meta["uncorrected_segments"] = failed
            meta["degraded"] = f"{len(failed)} of {len(items)} segments kept their primary text"
            log.warning("correct %s: %s", primary.call_id, meta["degraded"])
        return corrected_copy(primary, texts, target_lang, f"llm_correct:{model}", meta)


def corrected_copy(primary: Transcript, texts: dict[str, str], target_lang: str, backend: str,
                   meta: dict[str, Any]) -> Transcript:
    """``primary`` with corrected texts. Like :func:`callguard.translate.translated_copy`, but segments
    whose text did not change keep their word timestamps (they still belong to these words)."""
    segments = []
    for seg in primary.segments:
        text = texts.get(seg.id, seg.text)
        same = text == seg.text
        segments.append(seg.model_copy(update={"text": text, "words": list(seg.words) if same else []}))
    out_meta: dict[str, Any] = {"translation": {"from_view": primary.view, "from_lang": primary.lang,
                                                "to_lang": target_lang, "backend": backend, **meta}}
    if meta.get("degraded"):
        out_meta["degraded"] = meta["degraded"]
    return Transcript(call_id=primary.call_id, audio_path=primary.audio_path, duration=primary.duration,
                      language=target_lang, segments=segments, asr_backend=f"{primary.asr_backend} -> {backend}",
                      meta=out_meta, view=primary.view, lang=target_lang)
