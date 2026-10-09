"""ORACLE backend: the case's reference script instead of speech recognition.

Only for ceiling experiments (are misses caused by ASR or by the checks?) and offline demos. It reads
the script that belongs to the call, which the case forbids in the real audio pipeline.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard import audio
from callguard.asr import drop_inherited
from callguard.data import dialogue_of, parse_turns
from callguard.plugins import ASRBackend
from callguard.types import Segment, Transcript, Word

if TYPE_CHECKING:
    from callguard.context import Context

TURN_GAP_S = 0.4


class ReferenceASR(ASRBackend):
    """One Segment per script turn (id = turn id, e.g. ``T004``) with synthetic timings.

    Timings are proportional to word count so snippets and the UI timeline still work; with
    ``scale_to_audio`` they are stretched to span the real recording, which lands snippets roughly
    (not exactly) on the right passage.
    """

    def __init__(self, ctx: Context, words_per_second: float = 2.2, scale_to_audio: bool = True,
                 **inherited: Any):
        super().__init__(ctx, words_per_second=words_per_second, scale_to_audio=scale_to_audio)
        self.ignored_params = drop_inherited("reference", inherited)
        if words_per_second <= 0:
            raise ValueError("words_per_second must be > 0")
        self.words_per_second = float(words_per_second)
        self.scale_to_audio = bool(scale_to_audio)

    def script_path(self, call_id: str) -> Path:
        return Path(self.ctx.data_dir) / "Transkript" / f"{dialogue_of(call_id)}.txt"

    def transcribe(self, audio_path: Path | None, call_id: str) -> Transcript:
        script = self.script_path(call_id)
        if not script.exists():
            raise FileNotFoundError(
                f"reference ASR: no script for call {call_id!r} (expected {script}). It only works for "
                f"case calls named like 'Stufe1_D02-K1'; use a real ASR backend for other audio.")
        turns = [t for t in parse_turns(script.read_text(encoding="utf-8")) if t.text.strip()]
        if not turns:
            raise ValueError(f"reference ASR: script {script} contains no turns")

        spans: list[tuple[float, float]] = []
        t = 0.0
        for turn in turns:
            dur = max(len(turn.text.split()), 1) / self.words_per_second
            spans.append((t, t + dur))
            t += dur + TURN_GAP_S
        length = spans[-1][1]

        scale = 1.0
        duration = length
        if self.scale_to_audio and audio_path is not None and Path(audio_path).exists():
            duration = audio.duration(audio_path)
            scale = duration / length if length > 0 else 1.0

        segments = []
        for turn, (start, end) in zip(turns, spans):
            start, end = start * scale, end * scale
            segments.append(Segment(id=turn.id, start=round(start, 3), end=round(end, 3), text=turn.text,
                                    speaker=turn.speaker, role=turn.role, confidence=1.0,
                                    words=_spread_words(turn.text, start, end)))
        return Transcript(call_id=call_id, audio_path=str(audio_path) if audio_path else None,
                          duration=round(duration, 3), language="gsw", segments=segments,
                          asr_backend="reference",
                          meta={"oracle": True, "script": script.name, "time_scale": round(scale, 4)})


def _spread_words(text: str, start: float, end: float) -> list[Word]:
    """Evenly spaced words so word-level consumers (diarizer re-splits, keyword spans) see the same
    shape as real ASR output."""
    tokens = text.split()
    step = (end - start) / len(tokens) if tokens else 0.0
    return [Word(start=round(start + i * step, 3), end=round(start + (i + 1) * step, 3), text=tok, prob=1.0)
            for i, tok in enumerate(tokens)]
