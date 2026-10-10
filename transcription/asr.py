"""Audio -> Abschnitte mit Zeitstempel, Sprecher und Text.

Ablauf: Nemotron-3-Diarization findet die Sprachabschnitte und wer spricht; benachbarte Abschnitte desselben Sprechers
werden zu Stücken von höchstens MAX_CHUNK_SECONDS zusammengefasst; Flix-AI/flix-swissgerman-full (Whisper large,
Schweizerdeutsch -> Hochdeutsch) transkribiert jedes Stück. So hat jedes Stück eigene Zeitstempel (statt der groben
Whisper-Zeitstempel) und einen Sprecher. Findet die Diarization keine Sprache, wird das ganze Audio wie früher in
30-s-Stücken transkribiert (dann ohne Sprecher). Braucht ffmpeg im PATH.

Umgebungsvariablen:
  ASR_MODEL         Hugging-Face-Modell (Default Flix-AI/flix-swissgerman-full)
  DIARIZATION_MODEL Hugging-Face-Modell (Default nvidia/Nemotron-3-Diarization)
  ASR_BATCH_SIZE    Stücke pro GPU-Durchlauf (Default 4)
  MAX_SPEAKERS      Anzahl Sprecher in einem Anruf (Default 2: Beratung und Kunde)
"""
import os
import re
import time

import torch
from transformers import AutoModelForAudioFrameClassification, AutoProcessor, pipeline
from transformers.audio_utils import load_audio

MODEL_ID = os.environ.get("ASR_MODEL", "Flix-AI/flix-swissgerman-full")
DIARIZATION_ID = os.environ.get("DIARIZATION_MODEL", "nvidia/Nemotron-3-Diarization")
BATCH_SIZE = int(os.environ.get("ASR_BATCH_SIZE", "4"))
MAX_SPEAKERS = int(os.environ.get("MAX_SPEAKERS", "2"))
MAX_CHUNK_SECONDS = 20.0   # Stücklänge für Whisper (Whisper sieht höchstens 30 s)
MAX_GAP_SECONDS = 1.0      # Pause, über die hinweg Abschnitte desselben Sprechers zusammengefasst werden
SAMPLE_RATE = 16000
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".webm", ".mp4"}

# Satzende (. ! ? …) gefolgt von Leerzeichen und Grossbuchstabe/Ziffer
SENTENCE_END = re.compile(r"(?<=[.!?…])\s+(?=[A-ZÄÖÜ0-9„\"])")


def one_sentence_per_line(text: str) -> str:
    return "\n".join(SENTENCE_END.split(" ".join(text.split()))) + "\n"


def limit_speakers(turns, n):
    """Sprecher-Nummern auf die n mit der meisten Sprechzeit beschränken; ein Abschnitt eines weiteren Sprechers gehört
    zum vorherigen Sprecher. Danach umnummeriert in Reihenfolge des ersten Auftretens: 'Sprecher 1', 'Sprecher 2'."""
    talk = {}
    for t in turns: talk[t["Speaker"]] = talk.get(t["Speaker"], 0) + t["End"] - t["Start"]
    keep = set(sorted(talk, key=talk.get, reverse=True)[:n])
    order, prev = {}, None
    for t in turns:
        spk = t["Speaker"] if t["Speaker"] in keep else (prev if prev is not None else min(keep))
        prev = spk
        t["speaker"] = f"Sprecher {order.setdefault(spk, len(order) + 1)}"
    return turns


def chunk(turns):
    """Benachbarte Abschnitte desselben Sprechers zu Stücken <= MAX_CHUNK_SECONDS; ein einzelner längerer Abschnitt
    wird geteilt."""
    chunks = []
    for t in turns:
        c = chunks[-1] if chunks else None
        if c and c["speaker"] == t["speaker"] and t["Start"] - c["end"] <= MAX_GAP_SECONDS and t["End"] - c["start"] <= MAX_CHUNK_SECONDS:
            c["end"] = t["End"]
            continue
        start = t["Start"]
        while t["End"] - start > MAX_CHUNK_SECONDS:
            chunks.append({"start": start, "end": start + MAX_CHUNK_SECONDS, "speaker": t["speaker"]})
            start += MAX_CHUNK_SECONDS
        chunks.append({"start": start, "end": t["End"], "speaker": t["speaker"]})
    return chunks


class Transcriber:
    def __init__(self, model_id=MODEL_ID, diarization_id=DIARIZATION_ID, batch_size=BATCH_SIZE):
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        dtype = torch.bfloat16 if self.device != "cpu" else torch.float32
        t0 = time.perf_counter()
        self.asr = pipeline("automatic-speech-recognition", model=model_id, dtype=dtype, device=self.device)
        self.diar_proc = AutoProcessor.from_pretrained(diarization_id)
        self.diar = AutoModelForAudioFrameClassification.from_pretrained(diarization_id, device_map=self.device)
        self.model_id, self.diarization_id, self.batch_size = model_id, diarization_id, batch_size
        mem = f", {torch.cuda.memory_allocated() / 2**30:.1f} GB VRAM" if self.device != "cpu" else ""
        print(f"[asr] {model_id} + {diarization_id} auf {self.device}, {time.perf_counter() - t0:.0f}s{mem}", flush=True)

    def diarize(self, audio):
        """-> [{"Start", "End", "Speaker"}] (Sekunden), nach Start sortiert."""
        inputs = self.diar_proc(audio, sampling_rate=SAMPLE_RATE).to(self.diar.device, dtype=self.diar.dtype)
        with torch.inference_mode():
            logits = self.diar(**inputs).logits
        return sorted(self.diar_proc.extract_speaker_dict(logits, inputs.attention_mask)[0], key=lambda t: t["Start"])

    def transcribe(self, path):
        """-> {"text": ein Satz pro Zeile, "segments": [{"start", "end", "speaker", "text"}] in Sekunden, "seconds": Rechenzeit}."""
        t0 = time.perf_counter()
        audio = load_audio(str(path), sampling_rate=SAMPLE_RATE)
        turns = self.diarize(audio)
        if turns:
            chunks = chunk(limit_speakers(turns, MAX_SPEAKERS))
            pieces = [audio[int(c["start"] * SAMPLE_RATE): int(c["end"] * SAMPLE_RATE)] for c in chunks]
            outs = self.asr(pieces, batch_size=self.batch_size, generate_kwargs={"language": "de", "task": "transcribe"})
            segments = [{"start": round(c["start"], 2), "end": round(c["end"], 2), "speaker": c["speaker"], "text": o["text"].strip()}
                        for c, o in zip(chunks, outs) if o["text"].strip()]
        else:   # keine Sprache erkannt: ganzes Audio, grobe Whisper-Zeitstempel, ohne Sprecher
            out = self.asr(audio.copy(), chunk_length_s=30, batch_size=self.batch_size, return_timestamps=True,
                           generate_kwargs={"language": "de", "task": "transcribe"})
            segments = [{"start": c["timestamp"][0], "end": c["timestamp"][1], "speaker": None, "text": c["text"].strip()}
                        for c in out.get("chunks", []) if c["text"].strip()]
        return {"text": one_sentence_per_line(" ".join(s["text"] for s in segments)), "segments": segments,
                "seconds": round(time.perf_counter() - t0, 1)}
