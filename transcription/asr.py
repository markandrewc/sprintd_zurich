"""Schweizerdeutsch -> Hochdeutsch mit Flix-AI/flix-swissgerman-full (Whisper large). Braucht ffmpeg im PATH.

Umgebungsvariablen:
  ASR_MODEL       Hugging-Face-Modell (Default Flix-AI/flix-swissgerman-full)
  ASR_BATCH_SIZE  30-s-Stücke pro GPU-Durchlauf (Default 4; höher = schneller, braucht mehr VRAM neben Kev)
"""
import os
import re
import time

import torch
from transformers import pipeline

MODEL_ID = os.environ.get("ASR_MODEL", "Flix-AI/flix-swissgerman-full")
BATCH_SIZE = int(os.environ.get("ASR_BATCH_SIZE", "4"))
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm", ".mp4"}

# Satzende (. ! ? …) gefolgt von Leerzeichen und Grossbuchstabe/Ziffer
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")


def one_sentence_per_line(text: str) -> str:
    return "\n".join(SENTENCE_END.split(" ".join(text.split()))) + "\n"


class Transcriber:
    def __init__(self, model_id=MODEL_ID, batch_size=BATCH_SIZE):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if self.device != "cpu" else torch.float32
        t0 = time.perf_counter()
        self.asr = pipeline("automatic-speech-recognition", model=model_id, dtype=dtype, device=self.device)
        self.model_id, self.batch_size = model_id, batch_size
        mem = f", {torch.cuda.memory_allocated() / 2**30:.1f} GB VRAM" if self.device != "cpu" else ""
        print(f"[asr] {model_id} auf {self.device}, {time.perf_counter() - t0:.0f}s{mem}", flush=True)

    def transcribe(self, path):
        """-> {"text": ein Satz pro Zeile, "segments": [{"start", "end", "text"}] in Sekunden, "seconds": Rechenzeit}."""
        t0 = time.perf_counter()
        out = self.asr(
            str(path),
            chunk_length_s=30,  # Audio > 30 s wird in Stücken verarbeitet
            batch_size=self.batch_size,
            return_timestamps=True,
            generate_kwargs={"language": "de", "task": "transcribe"},
        )
        segments = [{"start": c["timestamp"][0], "end": c["timestamp"][1], "text": c["text"].strip()}
                    for c in out.get("chunks", []) if c["text"].strip()]
        return {"text": one_sentence_per_line(out["text"].strip()), "segments": segments,
                "seconds": round(time.perf_counter() - t0, 1)}
