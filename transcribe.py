"""
Schweizerdeutsch -> Hochdeutsch Transkription mit Flix-AI/flix-swissgerman-full.

  python transcribe.py                  # alle Audiodateien in ./data/audios
  python transcribe.py a.wav b.mp3      # bestimmte Dateien
  python transcribe.py --force          # auch bereits transkribierte neu generieren
  python transcribe.py --reformat       # bestehende .txt neu umbrechen (ohne Modell)

Schreibt pro Datei eine <name>.txt nach ./outputs/transcriptions und überspringt
Dateien, für die es schon eine gibt. Braucht ffmpeg im PATH.
"""

import argparse
import re
import sys
import time
from pathlib import Path

import torch
from transformers import pipeline

MODEL_ID = "Flix-AI/flix-swissgerman-full"
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm", ".mp4"}
ROOT = Path(__file__).parent
AUDIO_DIR = ROOT / "data" / "audios"
OUT_DIR = ROOT / "outputs" / "transcriptions"

# Satzende (. ! ? …) gefolgt von Leerzeichen und Grossbuchstabe/Ziffer
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")


def one_sentence_per_line(text: str) -> str:
    return "\n".join(SENTENCE_END.split(" ".join(text.split()))) + "\n"


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Umlaute in der Windows-Konsole
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="Audiodateien (Standard: alle in data/audios)")
    ap.add_argument("--force", action="store_true", help="vorhandene Transkriptionen überschreiben")
    ap.add_argument("--reformat", action="store_true", help="bestehende .txt neu umbrechen, ohne Modell")
    args = ap.parse_args()

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.reformat:
        for t in OUT_DIR.glob("*.txt"):
            t.write_text(one_sentence_per_line(t.read_text(encoding="utf-8")), encoding="utf-8")
            print(f"umgebrochen: {t.name}")
        return

    files = [Path(f) for f in args.files] or sorted(
        p for p in AUDIO_DIR.iterdir() if p.suffix.lower() in AUDIO_EXTS
    )
    if not files:
        print(f"Keine Audiodateien gefunden in {AUDIO_DIR}")
        return

    todo = [f for f in files if args.force or not (OUT_DIR / f"{f.stem}.txt").exists()]
    if len(todo) < len(files):
        print(f"{len(files) - len(todo)} bereits transkribiert, übersprungen (--force zum Neugenerieren)")
    if not todo:
        return

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    dtype = torch.bfloat16 if device != "cpu" else torch.float32
    print(f"Lade {MODEL_ID} auf {device} ...")
    asr = pipeline("automatic-speech-recognition", model=MODEL_ID, dtype=dtype, device=device)

    for i, f in enumerate(todo, 1):
        t0 = time.perf_counter()
        text = asr(
            str(f),
            chunk_length_s=30,  # Audio > 30 s wird in Stücken verarbeitet
            batch_size=8,
            generate_kwargs={"language": "de", "task": "transcribe"},
        )["text"].strip()
        text = one_sentence_per_line(text)
        (OUT_DIR / f"{f.stem}.txt").write_text(text, encoding="utf-8")
        print(f"\n[{i}/{len(todo)}] {f.name} ({time.perf_counter() - t0:.1f}s)\n{text}")


if __name__ == "__main__":
    main()
