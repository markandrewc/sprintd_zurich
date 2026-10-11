"""The recording for the browser player: transcoded once per call to a small mono MP3 (speech, 32 kbit/s) in
the call's run folder and embedded as a data URI, so the component needs no file server and no network.

MP3 because every browser plays it (Ogg/Opus is not universal on Safari). Without ffmpeg (or if it fails) a
WAV up to :data:`MAX_RAW_BYTES` is embedded as it is; anything else -> None and the player says the
recording is not available. Never raises.
"""

from __future__ import annotations

import base64
import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("callguard.demo")

FILE_NAME = "demo_audio.mp3"
BITRATE = "32k"
SAMPLE_RATE = 16000
MAX_RAW_BYTES = 24 * 1024 * 1024
MIME = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".flac": "audio/flac", ".m4a": "audio/mp4"}


@dataclass
class Audio:
    src: str | None  # data URI, None = not available
    note: str = ""  # why not (German, for the player)
    path: str | None = None  # the file that was embedded


def transcode(src: str | Path, out_dir: str | Path, *, ffmpeg: str | None = None, timeout: float = 120.0) -> Path | None:
    """``out_dir/demo_audio.mp3`` from ``src``; reused while it is newer than the source. None on failure."""
    src, out = Path(src), Path(out_dir) / FILE_NAME
    try:
        if out.is_file() and out.stat().st_size > 0 and out.stat().st_mtime >= src.stat().st_mtime:
            return out
    except OSError:
        pass
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return None
    tmp = out.with_suffix(".tmp.mp3")
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([exe, "-nostdin", "-loglevel", "error", "-y", "-i", str(src), "-vn", "-ac", "1",
                        "-ar", str(SAMPLE_RATE), "-c:a", "libmp3lame", "-b:a", BITRATE, str(tmp)],
                       check=True, capture_output=True, timeout=timeout)
        tmp.replace(out)
        return out
    except Exception as e:
        log.warning("demo: transcoding %s failed: %s", src, e)
        tmp.unlink(missing_ok=True)
        return None


def data_uri(path: str | Path) -> str:
    p = Path(path)
    mime = MIME.get(p.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def player_audio(audio_path: str | None, run_dir: str | Path | None) -> Audio:
    """What the player embeds for one call."""
    if not audio_path or not Path(audio_path).is_file():
        return Audio(None, "die Aufnahme liegt nicht auf diesem Rechner")
    out = transcode(audio_path, run_dir) if run_dir is not None else None
    if out is not None:
        try:
            return Audio(data_uri(out), path=str(out))
        except OSError as e:
            log.warning("demo: reading %s failed: %s", out, e)
    try:
        if Path(audio_path).stat().st_size <= MAX_RAW_BYTES:
            return Audio(data_uri(audio_path), path=str(audio_path))
    except OSError:
        pass
    return Audio(None, "die Aufnahme konnte nicht für den Browser umgewandelt werden (ffmpeg fehlt?)")
