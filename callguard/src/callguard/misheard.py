"""Flag passages whose audio the ASR was unsure about: «möglicherweise verhört — bitte anhören».

Every ASR segment carries ``confidence`` (faster-whisper: geometric mean of its word probabilities times
1 - no_speech_prob). A passage shown to the officer gets the LOWEST confidence of its segments: if any
sentence of the passage is in the bottom of the confidence distribution, the text the reasons quote may
be wrong, and the officer should listen instead of trusting the transcript.

Threshold (``snippets.misheard_below``, default :data:`DEFAULT_THRESHOLD`): the bottom decile of all
segment confidences on the dev dialogues, label-free (no expected label was looked at to choose it):
2860 segments of whisper-large-v3-gsw-ct2 (runs/experiments/kev_vs_facts/champion, 48 dev calls) have
p10 = 0.597 -> 0.60. It is specific to that ASR model; another model needs its own decile
(:func:`bottom_quantile`). Backends without confidences (hf_whisper: None) never flag; the oracle
``reference`` backend reports 1.0 and never flags. ``misheard_below: 0`` (or null) switches it off.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from callguard.types import CallResult, Passage, Segment, Transcript

DEFAULT_THRESHOLD = 0.60
LABEL_DE = "möglicherweise verhört — bitte anhören"


def threshold_of(snippets: Mapping[str, Any] | None) -> float | None:
    """``snippets.misheard_below`` from the config (default 0.60); None = flag switched off."""
    raw = (snippets or {}).get("misheard_below", DEFAULT_THRESHOLD)
    try:
        thr = float(raw) if raw is not None else 0.0
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD
    return thr if thr > 0 else None


def passage_segments(transcript: Transcript, passage: Passage) -> list[Segment]:
    """The passage's segments by id; passages without ids (or ids of another view) by time overlap."""
    ids = set(passage.segment_ids)
    segs = [s for s in transcript.segments if s.id in ids]
    if segs:
        return segs
    return [s for s in transcript.segments if min(s.end, passage.end) > max(s.start, passage.start)
            or (passage.start == passage.end and s.start <= passage.start <= s.end)]


def passage_confidence(transcript: Transcript, passage: Passage) -> tuple[float | None, str | None]:
    """(lowest ASR confidence among the passage's segments, id of that segment); (None, None) when the
    ASR reported no confidences."""
    scored = [s for s in passage_segments(transcript, passage) if s.confidence is not None]
    if not scored:
        return None, None
    low = min(scored, key=lambda s: s.confidence)  # type: ignore[arg-type, return-value]
    return float(low.confidence), low.id  # type: ignore[arg-type]


def is_misheard(confidence: float | None, threshold: float | None) -> bool:
    return confidence is not None and threshold is not None and confidence < threshold


def annotate(result: CallResult, threshold: float | None) -> int:
    """Set ``asr_confidence`` / ``misheard`` on every passage of the decision; returns the flagged count."""
    n = 0
    for p in result.decision.passages:
        conf, _ = passage_confidence(result.transcript, p)
        p.asr_confidence = None if conf is None else round(conf, 4)
        p.misheard = is_misheard(conf, threshold)
        n += p.misheard
    return n


def bottom_quantile(confidences: Iterable[float | None], q: float = 0.1) -> float | None:
    """The ``q`` quantile (linear interpolation) of the given segment confidences (Nones skipped)."""
    xs = sorted(float(c) for c in confidences if c is not None)
    if not xs:
        return None
    pos = q * (len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
