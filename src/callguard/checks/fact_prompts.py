"""Prompt texts and answer parsing for the ``facts`` check (``checks/facts.py``).

One prompt per fact: the transcript first (shared prefix with every other fact, family and LLM check
of the call, so vLLM's prefix cache evaluates it once), then one yes/no/unknown question, and the
next token is the answer. ``yes``, ``no`` and ``unknown`` are single tokens in the Qwen2.5 tokenizer
(``Nein`` / ``Unklar`` / ``unclear`` are not), so the answer words stay English even when the
question is asked in German; ``choice_probs`` reads their probabilities from one forward pass.

Bump ``PROMPT_VERSION`` whenever a text here changes: it is part of the check's cache key and of
the per-fact probe cache key.
"""

from __future__ import annotations

import re
from typing import Any

from callguard.checks import prompts

PROMPT_VERSION = "facts-1"

# answer token -> fact value. The order is the order of choice_probs' choices.
ANSWERS: dict[str, str] = {"yes": "yes", "no": "no", "unknown": "unclear"}
VALUES = ("yes", "no", "unclear")
VALUE_DE = {"yes": "ja", "no": "nein", "unclear": "unklar"}

# sampling fallback: what a model may write instead of the single token
_ANSWER_ALIASES = {
    "yes": "yes", "ja": "yes", "true": "yes", "y": "yes",
    "no": "no", "nein": "no", "false": "no", "n": "no",
    "unknown": "unclear", "unclear": "unclear", "unklar": "unclear", "unbekannt": "unclear",
    "undetermined": "unclear", "uncertain": "unclear", "offen": "unclear",
}


def system_prompt(transcript_lang: str | None = None, *, one_word: bool = True) -> str:
    """Shared rules; ``one_word=False`` for the evidence call (JSON answer instead of one token)."""
    return (
        "You are a careful compliance analyst at a Swiss bank. You answer one factual question about a "
        "recorded phone call between a bank advisor and a customer.\n\n"
        "About the transcript:\n"
        f"{prompts.transcript_note(transcript_lang)}\n"
        "- Each line is one segment: [segment-id mm:ss speaker] text. Speaker roles (advisor/customer) "
        "may be missing or wrong; work out who says what from the content when it matters.\n\n"
        "How to answer:\n"
        "- Answer only the question asked, based only on what is said in this call.\n"
        "- \"yes\": the call shows it. \"no\": the call shows it is not so, or it does not happen in "
        "the call. \"unknown\": the call raises the matter but does not let you decide.\n"
        "- Talking about something (explaining it, quoting it, asking about it, warning against it, a "
        "hypothetical example) is not doing it, unless the question asks about the talking.\n"
        "- Something that actually happened still counts if it is later regretted, refused or "
        "cancelled."
        + ("\n- Answer with exactly one word: yes, no or unknown." if one_word else "")
    )


def examples_block(examples: list[dict[str, str]]) -> str:
    """Research S2: short worked examples (excerpts of OTHER calls + the answer) for one question."""
    out = ["Worked examples for this question (short excerpts from OTHER calls, not from this call):"]
    for i, ex in enumerate(examples, 1):
        out.append(f"<example {i}>\n{ex['excerpt'].strip()}\n</example {i}>\nAnswer for example {i}: "
                   f"{'unknown' if ex['answer'] == 'unclear' else ex['answer']}")
    return "\n".join(out)


def fact_messages(rendered: str, family_label: str, family_id: str, question: str,
                  transcript_lang: str | None = None,
                  examples: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    shots = (f"{examples_block(examples)}\n\nNow answer the question for the call transcript above.\n"
             if examples else "")
    user = (
        "Transcript of the call (one line per segment: [segment-id mm:ss speaker] text):\n"
        f"<transcript>\n{rendered}\n</transcript>\n\n"
        f"Topic: {family_label} [{family_id}]\n"
        f"Question: {' '.join(question.split())}\n\n"
        f"{shots}"
        "Answer with exactly one word: yes, no or unknown."
    )
    return [{"role": "system", "content": system_prompt(transcript_lang)},
            {"role": "user", "content": user}]


def evidence_messages(rendered: str, family_label: str, family_id: str, question: str, p_yes: float,
                      reason_language: str = "de", example_id: str = "S001",
                      transcript_lang: str | None = None) -> list[dict[str, str]]:
    lang = prompts.language_name(reason_language)
    user = (
        "Transcript of the call (one line per segment: [segment-id mm:ss speaker] text):\n"
        f"<transcript>\n{rendered}\n</transcript>\n\n"
        f"Topic: {family_label} [{family_id}]\n"
        f"Question: {' '.join(question.split())}\n\n"
        f"An automatic review answered this question with \"yes\" (probability {p_yes:.2f}).\n"
        "Point to the segments that show it.\n"
        "Answer with a JSON object with exactly these keys, in this order:\n"
        f"\"reason\": one short sentence in {lang} that cites what was actually said and by whom,\n"
        f"\"evidence\": list of the segment ids (like \"{example_id}\") that show it, empty list if none.\n"
        f"The reason must be written in {lang}."
    )
    return [{"role": "system", "content": system_prompt(transcript_lang, one_word=False)},
            {"role": "user", "content": user}]


def parse_answer(text: str | None) -> str | None:
    """First answer word of a sampled completion -> yes / no / unclear (None if there is none)."""
    for word in re.findall(r"[A-Za-zÄÖÜäöü]+", text or "")[:3]:
        v = _ANSWER_ALIASES.get(word.casefold())
        if v:
            return v
    return None


def probs_from_choices(probs: dict[str, Any]) -> dict[str, float] | None:
    """choice_probs output (keyed by answer token) -> {yes, no, unclear}, renormalised."""
    mass = {v: 0.0 for v in VALUES}
    for tok, value in ANSWERS.items():
        try:
            p = float(probs.get(tok) or 0.0)
        except (TypeError, ValueError):
            p = 0.0
        mass[value] += max(0.0, p)
    total = sum(mass.values())
    if not total > 0:
        return None
    return {v: m / total for v, m in mass.items()}
