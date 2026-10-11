#!/usr/bin/env python3
"""Import the teammate's held-out test50 set (sprintd_zurich data/test50, commit 954446c) as its OWN dataset.

    python3 scripts/data/import_test50.py <sprintd_zurich>/data/test50 data_test50/v1
    python3 scripts/data/import_test50.py <sprintd_zurich>/data/test50 data_test50/v1 --timed-only
        (only (re)writes Transkript_CH_timed/; every other file stays untouched, audio mtimes included)

Layout written (the case layout, so every tool reads it, but marked external so it never joins dev/holdout):
  dataset.yaml                     name: test50, external: true, levels per dialogue, provenance
  Audio/<id>-K1.wav, <id>-K2.wav   clean / noisy (copied as is)
  Skript_mit_Sollbewertung/<id>.txt  the call's _outcept.txt (labels, Belege) + "Gruppe: <pair_id>" so A/B twins
                                     are one resampling unit (evaluation only, never pipeline input)
  Transkript/<id>.txt              the CH turns (reference script, ORACLE experiments only)
  Transkript_CH_timed/<id>.json    the same CH turns with their times in the recording, DISPLAY ONLY (the demo's
                                   «Schweizerdeutsch (Originalskript)» view; never pipeline input):
                                   {"turns": [{id, speaker, dialect, start, end, text, sentences: [{start, end,
                                   text}]}]}. Turn text and times only: no label, fact or evidence field is copied.
                                   Clean K1 and noisy K2 share it (noisy = clean + noise: same length, zero lag).
Held out by its authors: never train or tune on it (data/test50/README.md). Non-commercial TTS data.
"""
import csv
import json
import shutil
import sys
from pathlib import Path

LEVEL = {"trap": 1, "pair": 2, "numbers_pair": 2, "multi": 2, "review": 3}  # case Stufe analogues


TIMED_DIR = "Transkript_CH_timed"


def timed_turns(meta: dict) -> dict:
    """The display-only timed dialect script of one call from its ``<id>.json``: text and times, nothing else."""
    def text(x: dict) -> str:
        return (x.get("ch_final") or x.get("ch_auto") or "").strip()

    turns = [{"id": t["id"], "speaker": t.get("speaker", ""), "dialect": t.get("dialect", ""),
              "start": round(float(t["start"]), 3), "end": round(float(t["end"]), 3), "text": text(t),
              "sentences": [{"start": round(float(x["start"]), 3), "end": round(float(x["end"]), 3), "text": text(x)}
                            for x in t.get("sentences") or []]}
             for t in meta.get("turns") or []]
    return {"source": "sprintd_zurich data/test50 <id>.json turns (ch_final, start, end)", "timing": "test_data",
            "turns": turns}


def write_timed(src: Path, dst: Path) -> int:
    """``dst/Transkript_CH_timed/<id>.json`` for every call of ``src/calls``; returns how many."""
    (dst / TIMED_DIR).mkdir(parents=True, exist_ok=True)
    n = 0
    for d in sorted(p for p in (src / "calls").iterdir() if (p / f"{p.name}.json").is_file()):
        meta = json.loads((d / f"{d.name}.json").read_text(encoding="utf-8"))
        (dst / TIMED_DIR / f"{d.name}.json").write_text(
            json.dumps(timed_turns(meta), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    return n


def main(src: Path, dst: Path) -> None:
    rows = {r["id"]: r for r in csv.DictReader((src / "manifest.csv").open(encoding="utf-8"))}
    for sub in ("Audio", "Skript_mit_Sollbewertung", "Transkript"):
        (dst / sub).mkdir(parents=True, exist_ok=True)
    levels, groups = {}, {}
    for cid, row in sorted(rows.items()):
        d = src / "calls" / cid
        meta = json.loads((d / f"{cid}.json").read_text(encoding="utf-8"))
        group = meta.get("pair_id") or cid
        shutil.copyfile(d / f"{cid}_clean.wav", dst / "Audio" / f"{cid}-K1.wav")
        shutil.copyfile(d / f"{cid}_noisy.wav", dst / "Audio" / f"{cid}-K2.wav")
        script = (d / f"{cid}_outcept.txt").read_text(encoding="utf-8")
        head, _, body = script.partition("\nT001 ·")
        body = "T001 ·" + body
        lines = head.rstrip("\n").split("\n")
        at = next((i + 1 for i, l in enumerate(lines) if l.startswith("Testziel:")), len(lines))
        lines.insert(at, f"Gruppe: {group}")
        (dst / "Skript_mit_Sollbewertung" / f"{cid}.txt").write_text("\n".join(lines) + "\n\n" + body, encoding="utf-8")
        (dst / "Transkript" / f"{cid}.txt").write_text(body, encoding="utf-8")
        levels[cid] = LEVEL.get(row["type"], 2)
        groups[cid] = group
    (dst / "dataset.yaml").write_text(
        "# Imported by scripts/data/import_test50.py. EXTERNAL held-out set: never train or tune on it.\n"
        + json.dumps({"name": "test50", "external": True, "source": "sprintd_zurich data/test50 @ 954446c",
                      "tts": "FHNW STT4SG demo, 8 dialect voices (non-commercial)",
                      "levels": levels, "groups": groups}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_timed(src, dst)
    print(f"{len(rows)} dialogues -> {2 * len(rows)} calls in {dst}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--timed-only"]
    if "--timed-only" in sys.argv:
        print(f"{write_timed(Path(args[0]), Path(args[1]))} timed dialect scripts in {Path(args[1]) / TIMED_DIR}")
    else:
        main(Path(args[0]), Path(args[1]))
