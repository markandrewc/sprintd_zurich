"""Prompt texts and output parsing for the LLM-based checks (``llm_judge``, ``geval``).

Instructions are English because small instruction-tuned models follow English best; the family
criteria stay German exactly as compliance wrote them, and reasons come back in ``reason_language``
so the officer can read them. Bump ``PROMPT_VERSION`` whenever a judge/score prompt changes and
``STEPS_PROMPT_VERSION`` when the G-Eval step generation prompt changes: both are part of cache keys.

Parsing is deliberately forgiving: models wrap JSON in prose or code fences, run out of tokens
mid-object or write "S7" for "S007". Everything here is pure and offline-testable.
"""

from __future__ import annotations

import ast
import copy
import json
import math
import re
from typing import Any

from callguard.types import Family, Transcript, Verdict

# The transcript opens every user message: all calls of one check then share a long identical prefix,
# which llama.cpp (KV reuse of the previous prompt) and vLLM (prefix caching) evaluate only once.
PROMPT_VERSION = "llm-checks-3"
STEPS_PROMPT_VERSION = "geval-steps-1"

VERDICTS: tuple[Verdict, ...] = ("present", "absent", "undetermined")

LANGUAGES = {"de": "German", "en": "English", "fr": "French", "it": "Italian", "gsw": "Swiss German"}

# Property order matters: constrained decoding emits keys in this order, so the model writes its
# reason and evidence before it commits to a verdict.
_JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "verdict": {"type": "string", "enum": list(VERDICTS)},
        "confidence": {"type": "number"},
    },
    "required": ["reason", "evidence", "verdict", "confidence"],
    "additionalProperties": False,
}

_EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "reason": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["reason", "evidence"],
    "additionalProperties": False,
}

DEFAULT_STEPS = [
    "Find every passage of the transcript that relates to the policy of this misconduct family.",
    "For each passage decide whether the misconduct is actually done, or only mentioned, explained, "
    "quoted, asked about, negated or refused.",
    "Compare the passages with the 'alarm when' and 'not an alarm when' criteria.",
    "If a decisive fact cannot be established from the call (see 'undetermined when'), "
    "choose the middle of the scale.",
    "Assign the risk score.",
]


def judge_schema() -> dict[str, Any]:
    return copy.deepcopy(_JUDGE_SCHEMA)


def evidence_schema() -> dict[str, Any]:
    return copy.deepcopy(_EVIDENCE_SCHEMA)


def language_name(code: str) -> str:
    return LANGUAGES.get(code.lower(), code) if code else "German"


# --------------------------------------------------------------------------------------------
# Prompt building
# --------------------------------------------------------------------------------------------


# How the transcript came about, per view language. The `de` text is the original wording (cache-stable).
_TRANSCRIPT_NOTES = {
    "de": ("- It is an automatic transcription of a Swiss German phone call, translated by the speech "
           "recognizer into Standard German. It may contain recognition errors: misheard words, odd "
           "grammar, garbled names and numbers."),
    "en": ("- It is an automatic transcription of a Swiss German phone call, machine-translated into "
           "English. It may contain recognition and translation errors: misheard words, odd grammar, "
           "garbled names and numbers."),
    "gsw": ("- It is a transcription of a Swiss German phone call written in Swiss German dialect "
            "(non-standard spelling). It may contain errors: misheard words, garbled names and numbers."),
}


def transcript_note(lang: str | None) -> str:
    return _TRANSCRIPT_NOTES.get((lang or "de").lower(), _TRANSCRIPT_NOTES["de"])


def system_prompt(reason_language: str, *, scoring: bool = False, transcript_lang: str | None = None) -> str:
    """Shared rules for every LLM check call. ``scoring`` swaps the "answer undetermined" rule for
    "pick the middle of the scale", so G-Eval maps unknowable cases to ~0.5 like the judge does."""
    if scoring:
        unsure = ("If a decisive fact cannot be established from the call (for example whether "
                  "information is public, whether a code is still valid, whether an authorization "
                  "exists), give a score in the middle of the scale instead of guessing.")
    else:
        unsure = ("If a decisive fact cannot be established from the call (for example whether "
                  "information is public, whether a code is still valid, whether an authorization "
                  "exists), answer \"undetermined\" instead of guessing.")
    return (
        "You are a careful compliance analyst at a Swiss bank. You review recorded phone calls "
        "between bank advisors and customers for one specific kind of misconduct.\n\n"
        "About the transcript:\n"
        f"{transcript_note(transcript_lang)}\n"
        "- Each line is one segment: [segment-id mm:ss speaker] text. Speaker roles "
        "(advisor/customer) may be missing or wrong; work out who says what from the content when "
        "it matters.\n\n"
        "How to judge:\n"
        "- Judge ONLY the misconduct family defined in the user message. Ignore every other issue "
        "in the call.\n"
        "- Distinguish talking about an act from doing it: mentioning, explaining, quoting, asking "
        "about, negating, warning against or refusing an act is not the act itself.\n"
        "- Public information, expired or sample values, and refusals are not misconduct.\n"
        "- Misconduct that actually happened is not undone by a later warning, refusal or "
        "cancellation.\n"
        f"- {unsure}\n"
        f"- Write every reason in {language_name(reason_language)}."
    )


def _bullets(items: list[str]) -> str:
    lines = [f"- {str(x).strip()}" for x in items if x is not None and str(x).strip()]
    return "\n".join(lines) or "- (none specified)"


def family_block(f: Family) -> str:
    """The family criteria, inserted verbatim (German, as configured in criteria.yaml)."""
    return (
        f"Misconduct family: {f.label} [{f.id}]\n\n"
        f"Policy:\n{f.policy.strip() or '(none specified)'}\n\n"
        f"Alarm when (this IS the misconduct):\n{_bullets(f.alarm_when)}\n\n"
        f"Not an alarm when (harmless look-alikes):\n{_bullets(f.not_alarm_when)}\n\n"
        f"Undetermined when (a decisive fact cannot be established from the call):\n"
        f"{_bullets(f.review_when)}"
    )


def _transcript_block(rendered: str) -> str:
    return ("Transcript of the call (one line per segment: [segment-id mm:ss speaker] text):\n"
            f"<transcript>\n{rendered}\n</transcript>")


def render_transcript(t: Transcript, max_chars: int) -> tuple[str, int]:
    """``t.render()``, cut in the middle at line boundaries if longer than ``max_chars``.

    Returns (text, omitted line count). Openings and closings of calls carry most of the
    decisive content (the request, the final agreement), so the middle goes first.
    """
    text = t.render()
    if len(text) <= max_chars:
        return text, 0
    lines = text.split("\n")
    budget = max(0, max_chars - 60) // 2
    head: list[str] = []
    used = 0
    for line in lines:
        if used + len(line) + 1 > budget:
            break
        head.append(line)
        used += len(line) + 1
    tail: list[str] = []
    used = 0
    for line in reversed(lines[len(head):]):
        if used + len(line) + 1 > budget:
            break
        tail.append(line)
        used += len(line) + 1
    tail.reverse()
    omitted = len(lines) - len(head) - len(tail)
    marker = f"[... {omitted} lines omitted: transcript too long ...]"
    if not head and not tail:  # a single giant line: fall back to a character cut
        return f"{text[:budget]}\n{marker}\n{text[-budget:]}", omitted
    return "\n".join([*head, marker, *tail]), omitted


def judge_messages(f: Family, rendered: str, reason_language: str, example_id: str = "S001",
                   transcript_lang: str | None = None) -> list[dict[str, str]]:
    lang = language_name(reason_language)
    user = (
        f"{_transcript_block(rendered)}\n\n{family_block(f)}\n\n"
        f"Question: does this call contain the misconduct \"{f.label}\" as defined above?\n"
        "Answer with a JSON object with exactly these keys, in this order:\n"
        f"\"reason\": 1-2 sentences in {lang} that cite what was actually said and by whom,\n"
        f"\"evidence\": list of the segment ids (like \"{example_id}\") of the decisive passages, "
        "empty list if there are none,\n"
        "\"verdict\": \"present\" if the misconduct actually happens in this call, \"absent\" if it "
        "does not happen or is only mentioned, explained, quoted, negated, refused or harmless, "
        "\"undetermined\" if a decisive fact cannot be established from the call,\n"
        "\"confidence\": number from 0 to 1, how sure you are about the verdict.\n"
        f"The reason must be written in {lang}."
    )
    return [{"role": "system", "content": system_prompt(reason_language, transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]


def steps_messages(f: Family) -> list[dict[str, str]]:
    user = (
        f"{family_block(f)}\n\n"
        "A reviewer will read the automatic transcript of a bank phone call (Swiss German speech, "
        "transcribed and translated to Standard German, may contain recognition errors) and rate "
        "how strongly this misconduct is present in the call.\n"
        "Write 3-5 concise numbered evaluation steps for this rating, in English. "
        "Output only the numbered list."
    )
    return [{"role": "system", "content": "You write evaluation procedures for compliance reviewers "
                                          "at a Swiss bank."},
            {"role": "user", "content": user}]


def _scale_middle(scale: int) -> str:
    lo, hi = (1 + scale) // 2, (2 + scale) // 2
    return str(lo) if lo == hi else f"{lo}-{hi}"


def geval_messages(f: Family, rendered: str, steps: list[str], scale: int,
                   reason_language: str, transcript_lang: str | None = None) -> list[dict[str, str]]:
    """G-Eval form filling: input, task, criteria, evaluation steps, then the bare score slot so the
    next token is the digit whose probabilities we read. The input comes first (unlike the paper) so
    the transcript prefix is shared with the other calls (see PROMPT_VERSION)."""
    steps_txt = "\n".join(f"{i}. {s}" for i, s in enumerate(steps, 1))
    user = (
        f"{_transcript_block(rendered)}\n\n"
        "Task: rate how strongly the phone call above shows the misconduct defined by the "
        "evaluation criteria.\n\n"
        f"Evaluation criteria:\n{family_block(f)}\n\n"
        f"Scale: 1 = clearly absent (not discussed, or only mentioned, explained, quoted, negated, "
        f"refused or harmless); {_scale_middle(scale)} = undetermined (a decisive fact cannot be "
        f"established from the call); {scale} = clearly present (the misconduct actually happens).\n\n"
        f"Evaluation steps:\n{steps_txt}\n\n"
        "Evaluation form (score only):\n"
        f"Risk score (1-{scale}), answer with the digit only:"
    )
    return [{"role": "system", "content": system_prompt(reason_language, scoring=True, transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]


def evidence_messages(f: Family, rendered: str, expected: float, scale: int, reason_language: str,
                      example_id: str = "S001", transcript_lang: str | None = None) -> list[dict[str, str]]:
    lang = language_name(reason_language)
    user = (
        f"{_transcript_block(rendered)}\n\n{family_block(f)}\n\n"
        f"An automatic review rated this call {expected:.1f} on a risk scale from 1 (clearly absent) "
        f"to {scale} (clearly present) for the misconduct \"{f.label}\".\n"
        "Point to the passages that support or explain this rating.\n"
        "Answer with a JSON object with exactly these keys, in this order:\n"
        f"\"reason\": 1-2 sentences in {lang} that cite what was actually said and by whom,\n"
        f"\"evidence\": list of the segment ids (like \"{example_id}\") of the relevant passages, "
        "empty list if there are none.\n"
        f"The reason must be written in {lang}."
    )
    return [{"role": "system", "content": system_prompt(reason_language, scoring=True, transcript_lang=transcript_lang)},
            {"role": "user", "content": user}]


# --------------------------------------------------------------------------------------------
# Output parsing
# --------------------------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json|JSON)?\s*(.*?)```", re.S)
_CLOSERS = {"{": "}", "[": "]"}


def _scan(s: str) -> tuple[int | None, list[tuple[int, str]], str, bool]:
    """Walk a JSON fragment starting at ``{``. Returns (end index of the balanced object or None,
    [(comma position, open-bracket stack there)], final stack, still inside a string)."""
    stack: list[str] = []
    commas: list[tuple[int, str]] = []
    in_str = esc = False
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            if not stack:
                return i, commas, "", False
        elif ch == ",":
            commas.append((i, "".join(stack)))
    return None, commas, "".join(stack), in_str


def _close(stack: str) -> str:
    return "".join(_CLOSERS[c] for c in reversed(stack))


def _loads_dict(s: str) -> dict | None:
    for attempt in (s, re.sub(r",\s*([}\]])", r"\1", s)):
        try:
            obj = json.loads(attempt)
        except (json.JSONDecodeError, ValueError):
            try:  # python-style dicts with single quotes / True / None
                obj = ast.literal_eval(attempt)
            except (ValueError, SyntaxError, MemoryError, RecursionError):
                continue
        if isinstance(obj, dict):
            return obj
    return None


def parse_json_object(text: str | None) -> dict | None:
    """First JSON object in ``text``; tolerates prose, code fences, trailing commas and output
    truncated by max_tokens (keeps every complete key before the cut). None if hopeless."""
    if not text or not text.strip():
        return None
    candidates = [m.group(1) for m in _FENCE.finditer(text)] + [text]
    for cand in candidates:
        start = cand.find("{")
        if start < 0:
            continue
        frag = cand[start:]
        end, commas, stack, in_str = _scan(frag)
        if end is not None:
            obj = _loads_dict(frag[:end + 1])
            if obj is not None:
                return obj
            continue
        # truncated: close what is open, else back off to the last complete member
        tries = [frag + ('"' if in_str else "") + _close(stack)]
        tries += [frag[:pos] + _close(st) for pos, st in reversed(commas[-30:])]
        for t in tries:
            obj = _loads_dict(t)
            if obj is not None:
                return obj
    return None


_VERDICT_ALIASES: dict[str, Verdict] = {
    "present": "present", "yes": "present", "true": "present", "vorhanden": "present",
    "absent": "absent", "no": "absent", "false": "absent", "nicht vorhanden": "absent",
    "undetermined": "undetermined", "unclear": "undetermined", "unknown": "undetermined",
    "uncertain": "undetermined", "unbestimmt": "undetermined", "unklar": "undetermined",
}


def parse_verdict(v: Any) -> Verdict | None:
    if isinstance(v, bool):
        return "present" if v else "absent"
    if not isinstance(v, str):
        return None
    return _VERDICT_ALIASES.get(v.strip().strip(".\"'").lower())


def parse_confidence(v: Any, default: float = 0.5) -> float:
    """0..1; accepts "0.8", "80%", 80 (percent) and falls back to ``default`` for junk."""
    try:
        c = float(str(v).strip().rstrip("%")) if not isinstance(v, (int, float)) else float(v)
    except (TypeError, ValueError):
        return default
    if math.isnan(c) or math.isinf(c):
        return default
    if 1.0 < c <= 100.0:
        c /= 100.0
    return min(1.0, max(0.0, c))


def clean_reason(v: Any, limit: int = 1000) -> str:
    if v is None:
        return ""
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
    return " ".join(s.split())[:limit]


_ID_TOKEN = re.compile(r"([A-Za-z]*)(\d+)")
_ID_SHAPE = re.compile(r"([A-Za-z]*)0*(\d+)")


def clean_evidence(raw: Any, transcript: Transcript) -> list[str]:
    """Segment ids the model cited that exist in ``transcript``, in transcript order.

    Accepts exact ids, "S7" for "S007", bare numbers when ids share one prefix, whole rendered
    tags like "[S007 01:23 advisor]" and ranges "S007-S009". Invented ids are dropped.
    """
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    order = {s.id: i for i, s in enumerate(transcript.segments)}
    ids = list(order)
    by_num: dict[tuple[str, int], str] = {}
    for sid in ids:
        m = _ID_SHAPE.fullmatch(sid)
        if m:
            by_num.setdefault((m.group(1).upper(), int(m.group(2))), sid)
    prefixes = {p for p, _ in by_num}

    def lookup(prefix: str, num: int, bare_ok: bool) -> str | None:
        sid = by_num.get((prefix.upper(), num))
        if sid is None and not prefix and bare_ok and len(prefixes) == 1:
            sid = by_num.get((next(iter(prefixes)), num))
        return sid

    found: set[str] = set()
    for item in items:
        if isinstance(item, dict):
            item = next((v for v in item.values() if isinstance(v, (str, int))), None)
        if isinstance(item, bool) or item is None:
            continue
        if isinstance(item, (int, float)):
            item = str(int(item))
        if not isinstance(item, str):
            continue
        s = item.strip()
        if s in order:
            found.add(s)
            continue
        bare = s.isdigit()
        hits = []
        for prefix, num in _ID_TOKEN.findall(s):
            if prefix or bare:  # bare numbers inside text are timestamps, not ids
                sid = lookup(prefix, int(num), bare)
                if sid:
                    hits.append(sid)
        if len(hits) == 2 and re.search(r"[-–]", s):
            lo, hi = sorted((order[hits[0]], order[hits[1]]))
            if hi - lo <= 50:
                hits = ids[lo:hi + 1]
        found.update(hits)
    return sorted(found, key=order.__getitem__)


_STEP_LINE = re.compile(r"^\s*[*_]*(?:step\s*)?(?:\d+\s*[.):-]|[-*•])[*_]*\s*(.+?)\s*$", re.I)


def parse_steps(text: str, max_steps: int = 8) -> list[str]:
    """Numbered or bulleted lines of an LLM answer -> step texts (numbering stripped)."""
    steps = []
    for line in (text or "").splitlines():
        m = _STEP_LINE.match(line)
        step = _strip_markup(m.group(1)) if m else ""
        if step:
            steps.append(step)
    return steps[:max_steps]


def _strip_markup(s: str) -> str:
    return re.sub(r"\*\*|__", "", s).strip("*_ ")


def normalize_steps(v: list[str] | str) -> list[str]:
    """Configured steps: a YAML list or one multi-line string, numbered or not."""
    if isinstance(v, str):
        return parse_steps(v) or [line.strip() for line in v.splitlines() if line.strip()]
    out = []
    for s in v:
        s = str(s).strip()
        m = _STEP_LINE.match(s)
        out.append(m.group(1) if m else s)
    return [s for s in out if s]


def parse_digit(text: str | None, scale: int) -> int | None:
    m = re.search(r"\d+", text or "")
    if not m:
        return None
    d = int(m.group())
    return d if 1 <= d <= scale else None
