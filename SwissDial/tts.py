"""
Schweizerdeutsch Text -> Sprache mit swordi/SwissDial-TTS (ESPnet VITS + x-Vektor, 22.05 kHz).

  python SwissDial/tts.py "Grüezi mitenand, wie gaht's?"              # Zürcher Stimme
  python SwissDial/tts.py "Grüessech mitenand" --dialect be           # Berner Stimme
  python SwissDial/tts.py -f text.txt --dialect bs -o basel.wav       # Text aus Datei
  python SwissDial/tts.py "Hoi zäme" --all                            # eine WAV pro Dialekt

Das Modell ist auf Text in Dialekt-Schreibweise trainiert (SwissDial-Korpus); Hochdeutsch geht,
klingt aber weniger natürlich. Die Dialekte sind je eine Sprecherin/ein Sprecher, ausgewählt über
den gemittelten x-Vektor aus dem Training. Ausgabe nach ./outputs/swissdial, falls kein -o.

Umgebungsvariablen:
  SWISSDIAL_DEVICE  cuda | cpu (Default: cuda, falls vorhanden)
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

import kaldiio
import numpy as np
import soundfile as sf
import torch
from espnet2.bin.tts_inference import Text2Speech
from huggingface_hub import snapshot_download

MODEL_ID = "swordi/SwissDial-TTS"
DEVICE = os.environ.get("SWISSDIAL_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
OUT_DIR = Path(__file__).resolve().parent.parent / "outputs" / "swissdial"

DIALECTS = {
    "ag": "Aargau",
    "be": "Bern",
    "bs": "Basel",
    "gr": "Graubünden",
    "lu": "Luzern",
    "sg": "St. Gallen",
    "vs": "Wallis",
    "zh": "Zürich",
}

# Satzende (. ! ? …) gefolgt von Leerzeichen; jeder Satz wird einzeln synthetisiert
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+")
PAUSE_S = 0.25


class SwissDialTTS:
    def __init__(self, device=DEVICE):
        t0 = time.perf_counter()
        root = Path(snapshot_download(MODEL_ID, ignore_patterns=["*.png", "*.zip"]))
        exp = next((root / "exp" / "22k").glob("tts_train*"))
        self.tts = Text2Speech(train_config=exp / "config.yaml", model_file=exp / "531epoch.pth", device=device)
        self.fs = self.tts.fs
        self.device = device
        # spk_xvector.scp hat relative Pfade, deshalb die .ark direkt lesen
        xvecs = kaldiio.load_ark(str(root / "dump" / "22k" / "xvector" / "train" / "spk_xvector.ark"))
        self.xvectors = {spk: torch.tensor(v, dtype=torch.float32) for spk, v in xvecs}
        print(f"{MODEL_ID} geladen auf {device} ({time.perf_counter() - t0:.1f}s)")

    @torch.inference_mode()
    def synthesize(self, text: str, dialect: str = "zh", speed: float = 1.0) -> np.ndarray:
        """Text -> Mono-Waveform (float32, self.fs Hz). speed > 1 = schneller."""
        if dialect not in self.xvectors:
            raise ValueError(f"Unbekannter Dialekt {dialect!r}, erlaubt: {', '.join(self.xvectors)}")
        sentences = [s for s in SENTENCE_END.split(" ".join(text.split())) if s]
        if not sentences:
            raise ValueError("Leerer Text")
        pause = np.zeros(int(PAUSE_S * self.fs), dtype=np.float32)
        parts = []
        for s in sentences:
            wav = self.tts(s, spembs=self.xvectors[dialect], decode_conf={"alpha": 1.0 / speed})["wav"]
            parts += [wav.float().cpu().numpy(), pause]
        return np.concatenate(parts[:-1])

    def to_file(self, text: str, path, dialect: str = "zh", speed: float = 1.0) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(path, self.synthesize(text, dialect, speed), self.fs)
        return path


def slug(text: str, n: int = 40) -> str:
    return re.sub(r"[^\w]+", "_", text.lower())[:n].strip("_") or "tts"


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Umlaute in der Windows-Konsole
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="?", help="zu sprechender Text")
    ap.add_argument("-f", "--file", help="Text aus Datei lesen (UTF-8)")
    ap.add_argument("-d", "--dialect", default="zh", choices=DIALECTS, help="Dialekt/Stimme (Default zh)")
    ap.add_argument("--all", action="store_true", help="eine WAV pro Dialekt")
    ap.add_argument("-s", "--speed", type=float, default=1.0, help="Sprechtempo, z.B. 0.9 oder 1.2")
    ap.add_argument("-o", "--out", help="Ziel-WAV (Default outputs/swissdial/<dialekt>_<text>.wav)")
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8") if args.file else args.text
    if not text or not text.strip():
        ap.error("Text oder --file angeben")

    tts = SwissDialTTS()
    for d in DIALECTS if args.all else [args.dialect]:
        t0 = time.perf_counter()
        if not args.out:
            out = OUT_DIR / f"{d}_{slug(text)}.wav"
        elif args.all:
            out = Path(args.out).with_name(f"{Path(args.out).stem}_{d}.wav")
        else:
            out = Path(args.out)
        tts.to_file(text, out, d, args.speed)
        print(f"{d} ({DIALECTS[d]}): {out} ({time.perf_counter() - t0:.1f}s)")


if __name__ == "__main__":
    main()
