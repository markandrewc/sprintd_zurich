"""Speaker separation: who speaks when, and which speaker is the bank advisor.

A diarizer plugin produces speaker :class:`Turn` s from the audio. The helpers here are model-free
and shared by every diarizer:

* :func:`apply_turns` maps turns onto the ASR transcript. Whisper segments often run across a
  speaker change, so with word timestamps each word gets its own speaker and segments are re-split
  where the speaker changes.
* :func:`assign_roles` decides advisor vs customer, either by asking an LLM (trusted only if its
  answer survives relabelling the speakers) or by the case convention that the bank opens the call.
"""

from __future__ import annotations

import inspect
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from callguard.llm.jsonutil import chat_json
from callguard.types import Role, Segment

if TYPE_CHECKING:
    from callguard.plugins import LLM

log = logging.getLogger("callguard.diarization")

ROLE_METHODS = ("none", "first_speaker_advisor", "llm")

# Every script in the case data opens with "Beratung", so the first speaker is the advisor unless
# diarization got the very first segment wrong (noise, overlap) - hence not 1.0.
FIRST_SPEAKER_CONFIDENCE = 0.7
# Below this the LLM's pick is worth less than the first-speaker convention.
MIN_LLM_ROLE_CONFIDENCE = 0.5
# Long first turns add prompt tokens (slow on CPU) without helping to tell advisor from customer.
MAX_ROLE_LINE_CHARS = 300


@dataclass(frozen=True)
class Turn:
    """One stretch of speech by one diarization speaker (e.g. ``SPK0``), in seconds."""

    start: float
    end: float
    speaker: str


def speaker_name(index: int) -> str:
    return f"SPK{index}"


def speakers_of(segments: Sequence[Segment]) -> list[str]:
    """Speaker ids in order of first appearance."""
    return list(dict.fromkeys(s.speaker for s in segments if s.speaker))


# --------------------------------------------------------------------------------------------
# turns -> transcript
# --------------------------------------------------------------------------------------------


class TurnIndex:
    """Answers "who speaks in [start, end]?" for many words without rescanning Python lists."""

    def __init__(self, turns: Sequence[Turn]):
        self.turns = sorted(turns, key=lambda t: (t.start, t.end))
        self.starts = np.array([t.start for t in self.turns], dtype=float)
        self.ends = np.array([t.end for t in self.turns], dtype=float)
        self.speakers = list(dict.fromkeys(t.speaker for t in self.turns))
        idx = {s: i for i, s in enumerate(self.speakers)}
        self.speaker_idx = np.array([idx[t.speaker] for t in self.turns], dtype=int)

    def __bool__(self) -> bool:
        return bool(self.turns)

    def speaker(self, start: float, end: float) -> str | None:
        """Speaker with the most total overlap; the nearest turn when nothing overlaps (words in a
        pause, zero-length words, boundary jitter between ASR and diarization)."""
        if not self.turns:
            return None
        overlap = np.clip(np.minimum(end, self.ends) - np.maximum(start, self.starts), 0.0, None)
        if overlap.max() > 0:
            per_speaker = np.bincount(self.speaker_idx, weights=overlap, minlength=len(self.speakers))
            return self.speakers[int(np.argmax(per_speaker))]
        mid = (start + end) / 2
        distance = np.maximum(self.starts - mid, 0.0) + np.maximum(mid - self.ends, 0.0)
        return self.turns[int(np.argmin(distance))].speaker


def runs(labels: Sequence[Any]) -> list[tuple[int, int, Any]]:
    """``[a, a, b, a]`` -> ``[(0, 2, a), (2, 3, b), (3, 4, a)]`` (half-open index ranges)."""
    out: list[tuple[int, int, Any]] = []
    for i, lab in enumerate(labels):
        if out and out[-1][2] == lab:
            out[-1] = (out[-1][0], i + 1, lab)
        else:
            out.append((i, i + 1, lab))
    return out


def smooth_labels(starts: Sequence[float], ends: Sequence[float], labels: Sequence[str | None],
                  min_duration: float, max_words: int = 1) -> list[str | None]:
    """Give interior runs of at most ``max_words`` words or shorter than ``min_duration`` the
    speaker that surrounds them.

    ASR word times and diarization boundaries each drift by a few hundred ms, and a backchannel
    Whisper did not transcribe still leaves a short turn of the other voice. Splitting there would
    cut "vor der Meldung" into three segments, which breaks keyword and LLM checks. Only runs
    enclosed by the same other speaker within one ASR segment are touched, so speaker changes at
    segment edges survive.
    """
    out = list(labels)
    rs = runs(labels)
    for k in range(1, len(rs) - 1):
        i, j, lab = rs[k]
        prev, nxt = rs[k - 1][2], rs[k + 1][2]
        if prev == nxt and prev != lab and (j - i <= max_words or ends[j - 1] - starts[i] < min_duration):
            out[i:j] = [prev] * (j - i)
    return out


def apply_turns(segments: Sequence[Segment], turns: Sequence[Turn], *, resplit: bool = True,
                min_run: float = 0.0, max_flip_words: int = 1) -> list[Segment]:
    """New segments with ``speaker`` set from ``turns`` (roles reset to unknown).

    With ``resplit`` and word timestamps, every word gets the speaker it overlaps most and a
    segment is split where the speaker changes (after :func:`smooth_labels`); pieces keep their
    words and the segment's ASR confidence. Segments without words get the majority-overlap
    speaker. Ids are renumbered ``S001..`` only if something was split, so unsplit transcripts keep
    their ids (e.g. the reference ASR's script turn ids).
    """
    index = TurnIndex(turns)
    if not index:
        return [s.model_copy(deep=True) for s in segments]
    out: list[Segment] = []
    split = False
    for seg in segments:
        if not (resplit and seg.words):
            out.append(seg.model_copy(deep=True, update={
                "speaker": index.speaker(seg.start, seg.end), "role": "unknown"}))
            continue
        words = seg.words
        labels = [index.speaker(w.start, w.end) for w in words]
        labels = smooth_labels([w.start for w in words], [w.end for w in words], labels, min_run,
                               max_flip_words)
        pieces = runs(labels)
        if len(pieces) == 1:
            out.append(seg.model_copy(deep=True, update={"speaker": labels[0], "role": "unknown"}))
            continue
        split = True
        for k, (i, j, spk) in enumerate(pieces):
            ws = [w.model_copy() for w in words[i:j]]
            text = " ".join(w.text.strip() for w in ws if w.text.strip())
            if not text:
                continue
            end = seg.end if k == len(pieces) - 1 else ws[-1].end
            start = min(seg.start if k == 0 else ws[0].start, end)
            out.append(Segment(id=seg.id, start=start, end=end, text=text, speaker=spk, role="unknown",
                               confidence=seg.confidence, words=ws))
    if split:
        for n, s in enumerate(out, 1):
            s.id = f"S{n:03d}"
    return out


# --------------------------------------------------------------------------------------------
# roles
# --------------------------------------------------------------------------------------------


def set_roles(segments: Sequence[Segment], advisor: str) -> dict[str, Role]:
    """``advisor`` -> advisor, every other speaker -> customer (calls with >2 speakers included)."""
    roles: dict[str, Role] = {spk: ("advisor" if spk == advisor else "customer") for spk in speakers_of(segments)}
    for s in segments:
        s.role = roles.get(s.speaker, "unknown") if s.speaker else "unknown"
    return roles


def first_speaker(segments: Sequence[Segment]) -> str | None:
    return next((s.speaker for s in sorted(segments, key=lambda s: s.start) if s.speaker), None)


def label_order(speakers: Sequence[str]) -> list[str]:
    """``SPK0, SPK1, .., SPK10``: prompts list speakers in label order, never in speaking order, so
    the label-swap check really moves each voice to another position."""
    return sorted(set(speakers), key=lambda s: (len(s), s))


def relabel(segments: Sequence[Segment], mapping: dict[str, str]) -> list[Segment]:
    return [s.model_copy(update={"speaker": mapping.get(s.speaker, s.speaker)}) if s.speaker else s
            for s in segments]


def role_schema(speakers: Sequence[str]) -> dict[str, Any]:
    # reason first: constrained decoding emits keys in order, so the model argues before it picks
    return {
        "type": "object",
        "properties": {
            "reason": {"type": "string"},
            "advisor": {"type": "string", "enum": label_order(speakers)},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["reason", "advisor", "confidence"],
    }


def role_context(segments: Sequence[Segment], n_segments: int, per_speaker: int = 2) -> list[Segment]:
    """The first ``n_segments`` segments with text, plus the first lines of any speaker who does
    not talk in them (a long opening monologue must not leave the LLM a single choice)."""
    spoken = [s for s in segments if s.speaker and s.text.strip()]
    context = spoken[:max(1, n_segments)]
    present = {s.speaker for s in context}
    for spk in speakers_of(spoken):
        if spk not in present:
            context += [s for s in spoken if s.speaker == spk][:per_speaker]
    return context


def role_messages(segments: Sequence[Segment], n_segments: int) -> list[dict[str, str]]:
    """What each speaker said in the :func:`role_context`, grouped per speaker label.

    Grouped rather than chronological: on the case calls a 1.5B model read a chronological
    transcript as "whoever asks about shares is the advisor" and was confidently wrong on most
    calls; per-speaker blocks at least leave it no wrong content cue, and the label-swap check
    in :func:`llm_advisor` catches the position bias that remains.
    """
    context = role_context(segments, n_segments)
    speakers = label_order([s.speaker for s in context if s.speaker])
    blocks = []
    for spk in speakers:
        lines = []
        for s in context:
            if s.speaker == spk:
                text = " ".join(s.text.split())
                lines.append(text if len(text) <= MAX_ROLE_LINE_CHARS else text[:MAX_ROLE_LINE_CHARS] + " ...")
        blocks.append(f"Speaker {spk} says:\n" + "\n".join(f"- {line}" for line in lines))
    ids = " or ".join(speakers)
    system = (
        "You read phone calls between an employee of a Swiss bank (the advisor, German 'Beratung') "
        "and a bank customer ('Kunde', 'Kundin'). Speaker labels come from automatic speaker "
        "separation. You decide which label belongs to the bank employee.")
    user = (
        "\n\n".join(blocks) + "\n\n"
        f"Which speaker is the bank employee: {ids}? The bank employee greets the customer by name, "
        "asks what the customer wants, explains bank rules, and accepts or refuses orders. The customer "
        "wants to buy, sell or learn about their own money and tells personal details.\n"
        f"Answer as JSON: reason (one short sentence), advisor ({ids}), confidence (0 to 1).")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def ask_llm_advisor(llm: "LLM", segments: Sequence[Segment], n_segments: int = 12,
                    max_tokens: int = 200) -> tuple[str, float, str]:
    """``(advisor speaker id, confidence, reason)``; raises ValueError on unusable output."""
    schema = role_schema([s.speaker for s in role_context(segments, n_segments) if s.speaker])
    ans = chat_json(llm, role_messages(segments, n_segments), schema, temperature=0.0, max_tokens=max_tokens)[0]
    return str(ans["advisor"]), float(ans["confidence"]), str(ans.get("reason", "")).strip()


def llm_advisor(llm: "LLM", segments: Sequence[Segment], n_segments: int = 12,
                swap_check: bool = True) -> tuple[str | None, float, str]:
    """Advisor per LLM, or ``(None, conf, why)`` when the answer cannot be trusted.

    With ``swap_check`` the question is asked again with the speaker labels rotated. A model that
    reads the content names the same person both times; one that answers by label or position
    (small local models do, with confidence 0.9-1.0 regardless) names the other one.
    """
    advisor, conf, reason = ask_llm_advisor(llm, segments, n_segments)
    speakers = label_order(speakers_of(segments))
    if swap_check and len(speakers) > 1:
        mapping = dict(zip(speakers, speakers[1:] + speakers[:1]))
        inverse = {v: k for k, v in mapping.items()}
        swapped, conf2, _ = ask_llm_advisor(llm, relabel(segments, mapping), n_segments)
        if inverse.get(swapped) != advisor:
            return None, conf, (f"LLM answer follows the speaker labels, not the content ({advisor}, "
                                f"then {inverse.get(swapped)} after relabelling)")
        conf = min(conf, conf2)
    if conf < MIN_LLM_ROLE_CONFIDENCE:
        return None, conf, f"LLM unsure ({advisor}, confidence {conf:.2f}: {reason})"
    return advisor, conf, reason


def _model_id(client: Any) -> str | None:
    """The role LLM's model identity (served weights, not the alias) for the diarization meta."""
    try:
        mid = client.model_id
    except Exception:  # identity lookup failed: the meta just lacks it
        return None
    return str(mid) if mid is not None else None


def assign_roles(segments: Sequence[Segment], method: str, *, llm: Callable[[], "LLM"] | None = None,
                 context_segments: int = 12, swap_check: bool = True) -> dict[str, Any]:
    """Set ``Segment.role`` in place; returns the ``role_*`` fields for ``meta["diarization"]``.

    ``llm`` is a factory so an unconfigured or unreachable LLM is just another failure that falls
    back to the first-speaker convention instead of breaking the call.
    """
    if method not in ROLE_METHODS:
        raise ValueError(f"unknown role method {method!r}; expected one of {ROLE_METHODS}")
    for s in segments:
        s.role = "unknown"
    speakers = speakers_of(segments)
    info: dict[str, Any] = {"role_method": "none", "role_confidence": None, "role_reason": "", "roles": {}}
    if method == "none":
        info["role_reason"] = "role assignment disabled"
        return info
    if len(speakers) < 2:
        # one voice cannot be advisor and customer at once; labelling it would mislead the checks
        info["role_reason"] = f"{len(speakers)} speaker(s) detected; roles left unknown"
        return info

    note = ""
    if method == "llm":
        try:
            if llm is None:
                raise ValueError("no LLM given")
            client = llm()
            info["role_llm_model"] = _model_id(client)
            advisor, conf, reason = llm_advisor(client, segments, context_segments, swap_check)
            if advisor is not None:
                info.update(role_method="llm", role_confidence=round(conf, 3), role_reason=reason,
                            roles=set_roles(segments, advisor))
                return info
            note = f"{reason}; "
        except Exception as e:
            log.warning("LLM role assignment failed, using first speaker as advisor: %r", e)
            note = f"LLM failed ({e!r}"[:300] + "); "
            # a fallback caused by an error (server down, broken output) is not the answer of the
            # configured setup: the pipeline does not cache it, so the next run asks the LLM again
            info["role_error"] = f"{type(e).__name__}: {e}"[:300]

    advisor = first_speaker(segments)
    info.update(role_method="first_speaker_advisor", role_confidence=FIRST_SPEAKER_CONFIDENCE,
                role_reason=f"{note}first speaker {advisor} taken as advisor (the bank opens the call)",
                roles=set_roles(segments, advisor or ""))
    return info


# --------------------------------------------------------------------------------------------
# config helpers
# --------------------------------------------------------------------------------------------


def known_diarizer_params() -> set[str]:
    """Constructor params of every built-in diarizer."""
    from callguard import registry

    names: set[str] = set()
    for type_name in registry.BUILTINS["diarizer"]:
        try:
            cls = registry.resolve("diarizer", type_name)
        except Exception:  # an optional backend that fails to import has no params to inherit
            continue
        params = inspect.signature(cls.__init__).parameters.values()
        names |= {p.name for p in params
                  if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY) and p.name not in ("self", "ctx")}
    return names


def drop_inherited(diarizer: str, extra: dict[str, Any]) -> dict[str, Any]:
    """Ignore params that belong to another diarizer, raise on anything else.

    Profiles deep-merge, so ``diarizer: {type: none}`` in oracle.yaml still carries base.yaml's
    sherpa model paths; those must not break the switch. Typos still raise.
    """
    unknown = sorted(set(extra) - known_diarizer_params())
    if unknown:
        raise TypeError(f"diarizer type {diarizer!r} got unknown param(s) {unknown}")
    if extra:
        log.debug("diarizer %s ignores params inherited from another diarizer: %s", diarizer, sorted(extra))
    return extra
