"""ASR backends: audio file -> :class:`~callguard.types.Transcript`.

Backends are imported lazily through the registry, so faster-whisper / transformers are only loaded
when a config actually selects them. This module holds the dependency-free helpers they share.
"""

from __future__ import annotations

import inspect
import logging
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from callguard.config import ROOT
from callguard.types import Word

log = logging.getLogger("callguard.asr")

_DOUBLE_QUOTES = re.compile(r"[«»‹›\"“”„‟]")
# single quotes only when they wrap text; apostrophes inside words ("geht's") stay
_SINGLE_QUOTES = re.compile(r"(?<!\w)['‘’‚‛]|['‘’‚‛](?!\w)")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([.,!?;:…])")
_WS = re.compile(r"\s+")
_NO_WORD_CHARS = re.compile(r"\W+")


def clean_text(text: str) -> str:
    """Strip the «» guillemets and stray quotes the Swiss German fine-tunes wrap sentences in.

    Keyword and pattern checks match on this text, so ``«Aktie`` must become ``Aktie``.
    """
    text = _DOUBLE_QUOTES.sub(" ", text)
    text = _SINGLE_QUOTES.sub(" ", text)
    text = _WS.sub(" ", text)
    return _SPACE_BEFORE_PUNCT.sub(r"\1", text).strip()


def clean_words(raw: Iterable[tuple[float, float | None, str, float | None]]) -> list[Word]:
    """``(start, end, text, prob)`` tuples -> cleaned :class:`Word` list.

    Whisper emits trailing punctuation as its own "word" (``'?»'``); it is glued to the previous word
    so every Word is a real token a check can match. ``Word.text`` carries no leading space: join
    words with ``" "``. A missing ``end`` (last transformers chunk) becomes ``start``.
    """
    out: list[Word] = []
    for start, end, text, prob in raw:
        t = clean_text(text)
        if not t:
            continue
        s = float(start)
        e = max(float(end), s) if end is not None else s
        if _NO_WORD_CHARS.fullmatch(t):
            if out:
                prev = out[-1]
                out[-1] = prev.model_copy(update={"text": prev.text + t, "end": round(max(prev.end, e), 3)})
            continue
        out.append(Word(start=round(s, 3), end=round(e, 3), text=t,
                        prob=None if prob is None else round(float(prob), 4)))
    return out


def geometric_mean(probs: Iterable[float]) -> float | None:
    vals = [math.log(min(max(float(p), 1e-6), 1.0)) for p in probs]
    return math.exp(sum(vals) / len(vals)) if vals else None


def resolve_model(model: str) -> tuple[str, bool]:
    """``(path_or_repo_id, is_local)``.

    Relative paths are resolved against the project root like every other path in the configs. A
    missing path that clearly is a local path (``models/asr/...``) fails here with a hint instead of
    being sent to the Hugging Face Hub as a bogus repo id.
    """
    p = Path(model).expanduser()
    cand = p if p.is_absolute() else ROOT / p
    if cand.exists():
        return str(cand.resolve()), True
    looks_local = (p.is_absolute() or model.startswith(".") or len(p.parts) > 2
                   or (len(p.parts) > 1 and (ROOT / p.parts[0]).is_dir()))
    if looks_local:
        raise FileNotFoundError(
            f"ASR model {model!r} not found (looked at {cand}). Download or convert it first "
            f"(see scripts/), or set the model to a Hugging Face repo id.")
    return model, False


def model_name(model: str, is_local: bool) -> str:
    """Short provenance name for ``Transcript.asr_backend``."""
    return Path(model).name if is_local else model


def known_asr_params() -> set[str]:
    """Constructor params of every built-in ASR backend."""
    from callguard import registry

    names: set[str] = set()
    for type_name in registry.BUILTINS["asr"]:
        params = inspect.signature(registry.resolve("asr", type_name).__init__).parameters.values()
        names |= {p.name for p in params
                  if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) and p.name not in ("self", "ctx")}
    return names


def drop_inherited(backend: str, extra: dict[str, Any]) -> dict[str, Any]:
    """Ignore params that belong to another ASR backend, raise on anything else.

    Config profiles deep-merge, so ``asr: {type: reference}`` in oracle.yaml still carries base.yaml's
    faster-whisper ``model``/``beam_size``/...; those must not break the switch. Typos still raise.
    """
    unknown = sorted(set(extra) - known_asr_params())
    if unknown:
        raise TypeError(f"asr type {backend!r} got unknown param(s) {unknown}")
    if extra:
        log.debug("asr %s ignores params inherited from another backend: %s", backend, sorted(extra))
    return extra
