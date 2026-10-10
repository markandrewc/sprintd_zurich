"""
Batch-Transkription ohne Dienst (lädt das Modell selbst).

  python -m transcription.batch                  # alle Audiodateien in ./data/audios
  python -m transcription.batch a.wav b.mp3      # bestimmte Dateien
  python -m transcription.batch --reformat       # bestehende .txt neu umbrechen (ohne Modell)

Schreibt pro Datei eine <name>.txt nach ./outputs/transcriptions. Braucht ffmpeg im PATH.
"""

import sys
from pathlib import Path

from .asr import AUDIO_EXTS, Transcriber, one_sentence_per_line

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "data" / "audios"
OUT_DIR = ROOT / "outputs" / "transcriptions"


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Umlaute in der Windows-Konsole
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if sys.argv[1:] == ["--reformat"]:
        for t in OUT_DIR.glob("*.txt"):
            t.write_text(one_sentence_per_line(t.read_text(encoding="utf-8")), encoding="utf-8")
            print(f"umgebrochen: {t.name}")
        return

    files = [Path(f) for f in sys.argv[1:]] or sorted(
        p for p in AUDIO_DIR.iterdir() if p.suffix.lower() in AUDIO_EXTS
    )
    if not files:
        print(f"Keine Audiodateien gefunden in {AUDIO_DIR}")
        return

    asr = Transcriber()
    for f in files:
        res = asr.transcribe(f)
        (OUT_DIR / f"{f.stem}.txt").write_text(res["text"], encoding="utf-8")
        print(f"\n[{f.name}] ({res['seconds']}s)\n{res['text']}")


if __name__ == "__main__":
    main()
