"""The case data package: calls (audio), reference scripts and expected assessments.

File layout (see data/README.md of the case):
  Audio/Stufe1_D02-K1.wav              level 1, dialogue D02, K1 = clean (K2 = noisy; K3/K4 for C-dialogues)
  Transkript/Stufe1_D02.txt            script, turn by turn: "T001 · Beratung" then the text
  Skript_mit_Sollbewertung/Stufe1_D02.txt   header with Testziel / Bearbeitung / Belege ... + script

Ground truth is only for evaluation. Never feed file names, scripts or expected labels into the
audio pipeline (case rule). The ``reference`` ASR backend is an explicit oracle for ceiling studies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from callguard.types import Label, Role

_TURN_RE = re.compile(r"^(T\d{3})\s*·\s*(.+?)\s*$")
_CALL_RE = re.compile(r"^(Stufe(\d))_([A-Z]\d{2})-K(\d)$")


@dataclass
class Turn:
    id: str  # "T004"
    speaker: str  # "Beratung", "Kundin", "Kunde", ...
    role: Role
    text: str


@dataclass
class Expected:
    label: Label  # alarm / review / no_alert
    family: str  # Testziel: trade / access / ...
    event: str  # present / absent / undetermined / not_applicable
    reason: str
    open_question: str
    evidence_turns: list[str] = field(default_factory=list)  # "Belege"
    keyword_spots: str = ""


@dataclass
class Call:
    call_id: str  # "Stufe1_D02-K1"
    dialogue_id: str  # "Stufe1_D02"  (clean + noisy share it -> split by this!)
    level: int
    variant: int  # 1/3 clean, 2/4 noisy
    noisy: bool
    audio_path: Path
    title: str = ""
    expected: Expected | None = None
    turns: list[Turn] = field(default_factory=list)


def speaker_role(speaker: str) -> Role:
    s = speaker.lower()
    if s.startswith("berat") or "bank" in s:
        return "advisor"
    if s.startswith("kund"):
        return "customer"
    return "unknown"


def parse_turns(text: str) -> list[Turn]:
    turns: list[Turn] = []
    cur: Turn | None = None
    for line in text.splitlines():
        m = _TURN_RE.match(line.strip())
        if m:
            cur = Turn(id=m.group(1), speaker=m.group(2), role=speaker_role(m.group(2)), text="")
            turns.append(cur)
        elif cur is not None and line.strip():
            cur.text = (cur.text + " " + line.strip()).strip()
    return turns


def parse_expected(text: str) -> tuple[str, Expected | None]:
    header: dict[str, str] = {}
    lines = text.splitlines()
    title = lines[0].strip() if lines else ""
    for line in lines[1:]:
        if _TURN_RE.match(line.strip()):
            break
        key, sep, value = line.partition(":")
        if sep:
            header[key.strip()] = value.strip()
    if "Bearbeitung" not in header:
        return title, None
    evidence: list[str] = []
    for k, v in header.items():  # "Prüfpräfix bis T008; Belege: T004, T008" lands under key "Prüfpräfix bis T008; Belege"
        if "Belege" in k:
            evidence = re.findall(r"T\d{3}", v)
    return title, Expected(
        label=header["Bearbeitung"],  # type: ignore[arg-type]
        family=header.get("Testziel", ""),
        event=header.get("Ereignis", ""),
        reason=header.get("Begründung", ""),
        open_question=header.get("Offen", ""),
        evidence_turns=evidence,
        keyword_spots=header.get("Keywordstellen", ""),
    )


def dialogue_of(call_id: str) -> str:
    return call_id.split("-K")[0]


def load_calls(data_dir: str | Path) -> list[Call]:
    data_dir = Path(data_dir)
    calls: list[Call] = []
    for wav in sorted((data_dir / "Audio").glob("*.wav")):
        m = _CALL_RE.match(wav.stem)
        if not m:
            continue
        dlg = dialogue_of(wav.stem)
        variant = int(m.group(4))
        call = Call(call_id=wav.stem, dialogue_id=dlg, level=int(m.group(2)), variant=variant,
                    noisy=variant in (2, 4), audio_path=wav)
        exp_file = data_dir / "Skript_mit_Sollbewertung" / f"{dlg}.txt"
        if exp_file.exists():
            call.title, call.expected = parse_expected(exp_file.read_text())
        script = data_dir / "Transkript" / f"{dlg}.txt"
        if script.exists():
            call.turns = parse_turns(script.read_text())
        calls.append(call)
    return calls


def split_dialogues(calls: list[Call], n_folds: int = 5, seed: int = 13) -> dict[str, int]:
    """Deterministic dialogue -> fold assignment, stratified by expected label.

    Clean and noisy versions of one dialogue always land in the same fold (no leakage).
    """
    import random

    by_label: dict[str, list[str]] = {}
    for c in calls:
        lbl = c.expected.label if c.expected else "unknown"
        by_label.setdefault(lbl, [])
        if c.dialogue_id not in by_label[lbl]:
            by_label[lbl].append(c.dialogue_id)
    rng = random.Random(seed)
    fold_of: dict[str, int] = {}
    i = 0
    for lbl in sorted(by_label):
        dlgs = sorted(by_label[lbl])
        rng.shuffle(dlgs)
        for d in dlgs:
            fold_of[d] = i % n_folds
            i += 1
    return fold_of
