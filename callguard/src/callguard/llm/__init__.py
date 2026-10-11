"""LLM client plugins behind :class:`callguard.plugins.LLM`.

* ``openai_compat``: any OpenAI-compatible server (vLLM on the GPU box, llama-cpp-python / llama.cpp
  server on a laptop, Ollama). Switching machines is a config change, never a code change.
* ``llama_cpp``: in-process llama.cpp, for when no server should run.
* ``fake``: deterministic cue heuristic for offline tests and the no-server demo.

Checks should go through :func:`chat_json` (or ``parse_json`` + ``validate_minimal``) instead of
``json.loads``: small local models wrap JSON in prose, fences or stop mid-object.

This module only holds the small helpers the backends share; it must stay cheap to import
(no llama_cpp, no httpx), because every check imports it.
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Iterable, Sequence
from typing import Any

from callguard.llm.jsonutil import chat_json, parse_json, strip_reasoning, validate_minimal

__all__ = [
    "SCHEMA_INSTRUCTION", "chat_json", "choice_distribution", "parse_json", "request_seeds",
    "strip_reasoning", "validate_minimal", "with_schema_instruction",
]

SCHEMA_INSTRUCTION = "Respond ONLY with JSON matching this JSON schema:"


def with_schema_instruction(messages: list[dict[str, Any]], schema: dict) -> list[dict[str, Any]]:
    """Copy of ``messages`` with the schema appended to the last user turn, for backends that cannot
    constrain decoding. Never mutates the caller's list (it is reused for retries and samples)."""
    note = f"{SCHEMA_INSTRUCTION}\n{json.dumps(schema, ensure_ascii=False)}"
    out = [dict(m) for m in messages]
    for m in reversed(out):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            m["content"] = f"{m['content'].rstrip()}\n\n{note}"
            return out
    out.append({"role": "user", "content": note})
    return out


def request_seeds(n: int, temperature: float, seed: int | None, rng: random.Random) -> list[int | None]:
    """One seed per request when sampling ``n`` completions one by one.

    A configured seed gives reproducible but distinct samples (seed, seed+1, ...). Without one we
    still send random seeds when sampling: llama-cpp-python keeps the last request's seed for
    later unseeded requests, so on a shared server repeated samples could otherwise come out
    identical and self-consistency would measure nothing.
    """
    if seed is not None:
        return [int(seed) + i for i in range(n)]
    if temperature > 0:
        return [rng.randrange(1, 2**31 - 1) for _ in range(n)]
    return [None] * n


def choice_distribution(top: Iterable[tuple[str, float | None]], choices: Sequence[str],
                        min_mass: float = 0.0) -> dict[str, float] | None:
    """Turn next-token ``(token, logprob)`` pairs into a distribution over ``choices``.

    Tokens are compared after ``strip()`` (``" 4"`` counts for ``"4"``) and, if that is unambiguous,
    case-insensitively. Mass is summed per choice and renormalised over the choices, so tokens that
    are no valid answer (``"Based"``, ``"**"``) do not dilute the score. None if the choices carry
    no more than ``min_mass`` probability: the model was about to say something else entirely.
    """
    if not choices:
        return None
    exact = {c.strip(): c for c in choices}
    folded: dict[str, list[str]] = {}
    for c in choices:
        folded.setdefault(c.strip().casefold(), []).append(c)
    mass = dict.fromkeys(choices, 0.0)
    for tok, lp in top:
        key = (tok or "").strip()
        if not key or lp is None:
            continue
        c = exact.get(key)
        if c is None:
            cands = folded.get(key.casefold(), [])
            c = cands[0] if len(cands) == 1 else None
        if c is not None:
            mass[c] += math.exp(lp)
    total = sum(mass.values())
    if total <= min_mass or total <= 0.0:
        return None
    return {c: v / total for c, v in mass.items()}
