"""The Swiss German original script of a TEST call, timed against the recording: DISPLAY ONLY.

The test recordings were synthesised from dialect scripts. The demo can show that script next to the
Standard German ASR transcript (what callguard produces and what the AI reads), synchronised with the audio.
It is never pipeline input: no check, fusion, learning export or LLM call sees it (CLAUDE.md rule 2; guarded by
tests/test_original_script.py). Only the UI calls this module, at render time; nothing is written anywhere.

Where it comes from (the dataset folder the recording lives in, ``<data>/Audio/<id>-K<n>.wav``):

* ``<data>/Transkript_CH_timed/<dialogue>.json``: test50 (scripts/data/import_test50.py), turn times from the
  test data itself.
* ``<data>/Transkript/<dialogue>.txt``: the case dialogues, turns without times; each turn gets the time span
  of the ASR segments it is aligned to (:func:`callguard.align.align`, monotonic, about one sentence of slack).

Only those two folders are read, never ``Skript_mit_Sollbewertung`` (the labels). A recording that is not in
such a dataset folder (a new, uploaded call) has no original script: :func:`load` returns None. When the
recording is not on this machine, the configured data folder is tried instead.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from callguard.align import align
from callguard.data import parse_turns, speaker_role
from callguard.types import Segment, Transcript

log = logging.getLogger("callguard.demo")

TIMED_DIR = "Transkript_CH_timed"
SCRIPT_DIR = "Transkript"
NO_SCRIPT_DE = ("Kein Originalskript vorhanden: Sherlock Phones erzeugt Hochdeutsch; Schweizerdeutsch gibt es nur für "
                "Testdaten.")
TIMING_DE = {"test_data": "aus den Testdaten", "aligned": "per Ausrichtung an das KI-Transkript, ±1 Satz"}
_VARIANT = re.compile(r"-K\d+$")
_SAFE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

Timing = Literal["test_data", "aligned"]


@dataclass
class DialectTurn:
    id: str  # "T004"
    speaker: str  # "Kundin"
    role: str  # advisor / customer / unknown
    start: float
    end: float
    text: str
    aligned: bool = True  # False: no ASR segment matched (aligned timing only); the gap between its neighbours


@dataclass
class OriginalScript:
    dialogue_id: str
    turns: list[DialectTurn]
    timing: Timing
    path: str

    @property
    def note(self) -> str:
        """The honest label shown under the Swiss German view."""
        return ("Originalskript aus den Testdaten (Vorlage der Aufnahme), nicht von Sherlock Phones erzeugt und nicht "
                f"von der KI ausgewertet. Zeiten: {TIMING_DE[self.timing]}.")


def dialogue_id(call_id: str, audio_path: str | None = None) -> str:
    """``Stufe1_D02-K1`` -> ``Stufe1_D02`` (from the recording's file name when there is one)."""
    stem = Path(audio_path).stem if audio_path else call_id
    return _VARIANT.sub("", stem)


def dataset_dirs(audio_path: str | None, data_dirs: Iterable[str | Path] = ()) -> list[Path]:
    """Dataset folders that may hold the script: the one the recording lives in (``<data>/Audio/x.wav``);
    only when the recording is not on this machine, the configured data folders."""
    if audio_path and Path(audio_path).is_file():
        p = Path(audio_path).resolve()
        return [p.parent.parent] if p.parent.name == "Audio" else []
    return [Path(d) for d in data_dirs]


def read_timed(path: str | Path) -> list[DialectTurn]:
    """Turns of a ``Transkript_CH_timed/<id>.json`` (times from the test data), sorted by start."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    turns = [DialectTurn(id=str(t["id"]), speaker=str(t.get("speaker", "")),
                         role=speaker_role(str(t.get("speaker", ""))), start=float(t["start"]), end=float(t["end"]),
                         text=str(t.get("text", "")).strip())
             for t in raw.get("turns") or [] if t.get("text")]
    return sorted(turns, key=lambda t: (t.start, t.end))


def aligned_turns(script_text: str, segments: Sequence[Segment]) -> list[DialectTurn]:
    """The script's turns with the time span of the ASR segments aligned to them (monotonic, script order)."""
    turns = parse_turns(script_text)
    al = align(turns, segments)
    out = []
    for t in turns:
        sp = al.spans.get(t.id)
        if sp is None:
            continue
        out.append(DialectTurn(id=t.id, speaker=t.speaker, role=t.role, start=float(sp.start), end=float(sp.end),
                               text=t.text.strip(), aligned=sp.aligned))
    return out


def load(call_id: str, audio_path: str | None, transcript: Transcript,
         data_dirs: Iterable[str | Path] = ()) -> OriginalScript | None:
    """The original script of this call, or None (a new call, or no script in its dataset folder). Never raises."""
    dlg = dialogue_id(call_id, audio_path)
    if not _SAFE.match(dlg):
        return None
    for d in dataset_dirs(audio_path, data_dirs):
        timed, plain = d / TIMED_DIR / f"{dlg}.json", d / SCRIPT_DIR / f"{dlg}.txt"
        try:
            if timed.is_file():
                turns = read_timed(timed)
                if turns:
                    return OriginalScript(dlg, turns, "test_data", str(timed))
            if plain.is_file() and transcript.segments:
                turns = aligned_turns(plain.read_text(encoding="utf-8"), transcript.segments)
                if turns:
                    return OriginalScript(dlg, turns, "aligned", str(plain))
        except Exception as e:  # a broken script must never break the call page
            log.warning("demo: original script of %s not readable: %s", call_id, e)
    return None


def turns_in(turns: Sequence[DialectTurn], start: float, end: float) -> list[str]:
    """Ids of the turns overlapping [start, end]; none overlapping -> the nearest one (a passage always shows)."""
    hit = [t.id for t in turns if min(t.end, end) > max(t.start, start)]
    if hit or not turns:
        return hit
    gap = [max(0.0, t.start - end, start - t.end) for t in turns]
    return [turns[gap.index(min(gap))].id]
