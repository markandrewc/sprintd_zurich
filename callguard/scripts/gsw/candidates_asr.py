"""Research only: ASR candidates for an automatic Swiss German (dialect spelling) transcript.

  whisper  vanilla multilingual Whisper large-v3 (faster-whisper), language=de, a dialect initial_prompt
  w2v      scasutt/wav2vec2-large-xlsr-52_Swiss_German (SwissDial, character CTC), run on each segment of OUR
           Standard German ASR transcript (so the segments keep their times)

Writes <out>/<call_id>.json = {"segments": [{"start", "end", "text"}], "seconds": wall time}. Audio only (plus our
own ASR segment times for w2v); never reads reference scripts.

  python scripts/gsw/candidates_asr.py whisper <out> <audio_dir> <call_id>...
  python scripts/gsw/candidates_asr.py w2v <out> <audio_dir> <results_dir> <call_id>...
"""

from __future__ import annotations

import json
import os
import sys
import time
import wave
from pathlib import Path

import numpy as np

PROMPT = ("Grüezi mitenand. Jo, i ha e Frog zu mim Konto. Chönd Sie mir säge, wie vill Gäld no druf isch? "
          "Merci vilmal, uf Widerluege.")


def load_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        assert w.getframerate() == 16000 and w.getsampwidth() == 2, path
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if w.getnchannels() > 1:
            x = x.reshape(-1, w.getnchannels()).mean(axis=1)
    return x


def whisper(out: Path, audio_dir: Path, ids: list[str]) -> None:
    from faster_whisper import WhisperModel
    m = WhisperModel("Systran/faster-whisper-large-v3", device="cpu", compute_type="int8", cpu_threads=12)
    for cid in ids:
        t0 = time.time()
        segs, _ = m.transcribe(load_wav(audio_dir / f"{cid}.wav"), language="de", beam_size=1, vad_filter=True,
                               initial_prompt=PROMPT, condition_on_previous_text=True)
        rows = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segs]
        (out / f"{cid}.json").write_text(json.dumps({"segments": rows, "seconds": time.time() - t0},
                                                    ensure_ascii=False, indent=1))
        print(cid, round(time.time() - t0, 1), flush=True)


def w2v(out: Path, audio_dir: Path, results: Path, ids: list[str]) -> None:
    import torch
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    name = "scasutt/wav2vec2-large-xlsr-52_Swiss_German"
    proc, model = Wav2Vec2Processor.from_pretrained(name), Wav2Vec2ForCTC.from_pretrained(name).eval()
    for cid in ids:
        t0 = time.time()
        audio = load_wav(audio_dir / f"{cid}.wav")
        segs = json.loads((results / cid / "result.json").read_text())["transcript"]["segments"]
        rows = []
        pre, post, cap = (float(os.environ.get(k, d)) for k, d in (("PAD_START", 0), ("PAD_END", 0), ("CAP", 1)))
        for i, s in enumerate(segs):
            end = s["end"] + post
            if cap and i + 1 < len(segs):
                end = min(end, max(s["end"], segs[i + 1]["start"]))
            x = audio[int(max(0.0, s["start"] - pre) * 16000):int(end * 16000)]
            if len(x) < 1600:
                continue
            inp = proc(x, sampling_rate=16000, return_tensors="pt")
            with torch.no_grad():
                ids_ = model(inp.input_values).logits.argmax(-1)
            rows.append({"start": s["start"], "end": s["end"], "text": proc.batch_decode(ids_)[0].strip()})
        (out / f"{cid}.json").write_text(json.dumps({"segments": rows, "seconds": time.time() - t0},
                                                    ensure_ascii=False, indent=1))
        print(cid, round(time.time() - t0, 1), flush=True)


if __name__ == "__main__":
    kind, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    if kind == "whisper":
        whisper(out, Path(sys.argv[3]), sys.argv[4:])
    else:
        w2v(out, Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5:])
