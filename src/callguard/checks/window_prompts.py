"""Prompts for the passage-level LLM checks (``keyword_context``, ``anchored``, ``semantic_windows``)
and the quote-grounded judge (``quote_judge``).

Shared rules, criteria rendering and output parsing come from :mod:`callguard.checks.prompts`; this
module only adds the passage-focused questions. Bump ``PROMPT_VERSION`` whenever any prompt or schema
here changes: it is part of the cache key of every check that uses this module.

Prefix layout (vLLM prefix caching / llama.cpp KV reuse):

* window mode: system rules + family criteria + steps first, the excerpt last, so every window of one
  family shares the long prefix;
* anchored full-call mode (N4): the whole transcript first (shared with geval / llm_judge and with every
  anchor), then criteria + steps, the anchored question last;
* quote judge: the transcript first, like ``prompts.judge_messages``.
"""

from __future__ import annotations

import copy
from typing import Any

from callguard.checks.prompts import (
    _scale_middle,
    _transcript_block,
    family_block,
    language_name,
    system_prompt,
)
from callguard.types import Family

PROMPT_VERSION = "window-checks-1"

LINE_FORMAT = "one line per segment: [segment-id mm:ss speaker] text"


def span_label(seg_ids: list[str]) -> str:
    """``S012`` or ``S010-S016`` (ids in transcript order)."""
    if not seg_ids:
        return "(none)"
    return seg_ids[0] if len(seg_ids) == 1 else f"{seg_ids[0]}-{seg_ids[-1]}"


def _steps_block(steps: list[str] | None) -> str:
    if not steps:
        return ""
    return "Evaluation steps:\n" + "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1)) + "\n\n"


def _cues_block(cues: list[str]) -> str:
    if not cues:
        return ""
    lines = "\n".join(f"- {c}" for c in cues)
    return ("Why this passage was selected (automatic cues; they only show where to look and are no "
            f"evidence by themselves):\n{lines}\n\n")


def _scale_text(scale: int, *, full_call: bool) -> str:
    subject = "this passage, read in the context of the whole call," if full_call else "this passage"
    where = "the call" if full_call else "this passage"
    return (f"Scale: 1 = {subject} clearly does not show the misconduct (not discussed, or only mentioned, "
            f"explained, quoted, negated, refused or harmless); {_scale_middle(scale)} = undetermined (it "
            f"points to the misconduct but a decisive fact cannot be established from {where}); "
            f"{scale} = the misconduct clearly, actually happens in this passage.")


def window_geval_messages(f: Family, window_rendered: str, window_ids: list[str], cues: list[str],
                          steps: list[str] | None, scale: int, reason_language: str,
                          transcript_lang: str | None = None,
                          full_rendered: str | None = None) -> list[dict[str, str]]:
    """G-Eval form filling for one passage. ``full_rendered`` None = window mode (only the excerpt is
    shown); else anchored full-call mode: the whole call is shown and the question is anchored on
    ``window_ids``. The prompt ends in the bare score slot (next token = the digit)."""
    label = span_label(window_ids)
    if full_rendered is None:
        user = (
            "Task: rate how strongly ONE PASSAGE of a phone call shows the misconduct defined by the "
            "evaluation criteria. You only see this excerpt of the call.\n\n"
            f"Evaluation criteria:\n{family_block(f)}\n\n"
            f"{_steps_block(steps)}"
            f"{_scale_text(scale, full_call=False)}\n\n"
            f"Passage to rate (segments {label}; {LINE_FORMAT}):\n<passage>\n{window_rendered}\n</passage>\n\n"
            f"{_cues_block(cues)}"
            "Judge what the passage actually shows: who asks for or does what, and whether it is only "
            "mentioned, explained, quoted, negated or refused.\n\n"
            "Evaluation form (score only):\n"
            f"Risk score (1-{scale}) for passage {label}, answer with the digit only:"
        )
    else:
        user = (
            f"{_transcript_block(full_rendered)}\n\n"
            "Task: rate how strongly ONE PASSAGE of the call above shows the misconduct defined by the "
            "evaluation criteria. Use any context from anywhere in the call that decides what the "
            "passage means (who the information came from, whether it is public, whether a code is "
            "still valid, whether an authorization exists, what was asked before or agreed after).\n\n"
            f"Evaluation criteria:\n{family_block(f)}\n\n"
            f"{_steps_block(steps)}"
            f"{_scale_text(scale, full_call=True)}\n\n"
            f"Passage to rate: segments {label} (repeated from the transcript above):\n"
            f"<passage>\n{window_rendered}\n</passage>\n\n"
            f"{_cues_block(cues)}"
            f"Consider the passage {label}. Given the whole call, does THIS passage show the misconduct?\n\n"
            "Evaluation form (score only):\n"
            f"Risk score (1-{scale}) for passage {label}, answer with the digit only:"
        )
    return [{"role": "system", "content": system_prompt(reason_language, scoring=True,
                                                        transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]


def window_evidence_messages(f: Family, window_rendered: str, window_ids: list[str], cues: list[str],
                             expected: float, scale: int, reason_language: str,
                             transcript_lang: str | None = None,
                             full_rendered: str | None = None) -> list[dict[str, str]]:
    """One JSON call ({reason, evidence}) for the decisive passage: why it got its rating and which of
    its segments carry it. Same prefix as :func:`window_geval_messages` up to the passage."""
    lang = language_name(reason_language)
    label = span_label(window_ids)
    head = f"{_transcript_block(full_rendered)}\n\n" if full_rendered is not None else ""
    user = (
        f"{head}Evaluation criteria:\n{family_block(f)}\n\n"
        f"Passage (segments {label}; {LINE_FORMAT}):\n<passage>\n{window_rendered}\n</passage>\n\n"
        f"{_cues_block(cues)}"
        f"An automatic review rated this passage {expected:.1f} on a risk scale from 1 (clearly absent) "
        f"to {scale} (clearly present) for the misconduct \"{f.label}\".\n"
        "Explain the rating. Answer with a JSON object with exactly these keys, in this order:\n"
        f"\"reason\": 1-2 sentences in {lang} that cite what was actually said and by whom,\n"
        f"\"evidence\": list of the segment ids within {label} (like \"{window_ids[0] if window_ids else 'S001'}\") "
        "that carry the rating, empty list if there are none.\n"
        f"The reason must be written in {lang}."
    )
    return [{"role": "system", "content": system_prompt(reason_language, scoring=True,
                                                        transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]


# --------------------------------------------------------------------------------------------
# Quote-grounded judge (N3)
# --------------------------------------------------------------------------------------------

def quote_judge_schema(max_quotes: int = 3, max_quote_chars: int = 400) -> dict[str, Any]:
    """Like ``prompts.judge_schema`` with ``quotes`` instead of ``evidence``. Property order matters:
    the model writes reason and quotes before it commits to a verdict."""
    return copy.deepcopy({
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
            "quotes": {
                "type": "array", "maxItems": int(max_quotes),
                "items": {
                    "type": "object",
                    "properties": {"segment_id": {"type": "string"},
                                   "quote": {"type": "string", "maxLength": int(max_quote_chars)}},
                    "required": ["segment_id", "quote"],
                    "additionalProperties": False,
                },
            },
            "verdict": {"type": "string", "enum": ["present", "absent", "undetermined"]},
            "confidence": {"type": "number"},
        },
        "required": ["reason", "quotes", "verdict", "confidence"],
        "additionalProperties": False,
    })


def quote_judge_messages(f: Family, rendered: str, reason_language: str, example_id: str = "S001",
                         max_quotes: int = 3, max_quote_words: int = 25,
                         transcript_lang: str | None = None) -> list[dict[str, str]]:
    lang = language_name(reason_language)
    user = (
        f"{_transcript_block(rendered)}\n\n{family_block(f)}\n\n"
        f"Question: does this call contain the misconduct \"{f.label}\" as defined above?\n"
        "Answer with a JSON object with exactly these keys, in this order:\n"
        f"\"reason\": 1-2 sentences in {lang} that cite what was actually said and by whom,\n"
        f"\"quotes\": up to {max_quotes} objects {{\"segment_id\": the id of one segment (like "
        f"\"{example_id}\"), \"quote\": words copied EXACTLY from that segment, at most {max_quote_words} "
        "words, in the transcript's language and spelling, not translated, not paraphrased} that prove "
        "the verdict. A \"present\" verdict needs at least one quote of the decisive words; "
        "empty list if there is nothing to quote,\n"
        "\"verdict\": \"present\" if the misconduct actually happens in this call, \"absent\" if it "
        "does not happen or is only mentioned, explained, quoted, negated, refused or harmless, "
        "\"undetermined\" if a decisive fact cannot be established from the call,\n"
        "\"confidence\": number from 0 to 1, how sure you are about the verdict.\n"
        f"The reason must be written in {lang}. Quotes that do not appear in the transcript are discarded."
    )
    return [{"role": "system", "content": system_prompt(reason_language, transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]
