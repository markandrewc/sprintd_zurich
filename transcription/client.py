"""HTTP-Client für den Transkriptions-Dienst (transcription.api). Ohne torch importierbar.

URL über TRANSCRIPTION_URL (Default http://127.0.0.1:8001).
"""
import os
from pathlib import Path

import httpx

URL = os.environ.get("TRANSCRIPTION_URL", "http://127.0.0.1:8001")


def transcribe(audio_path, url=URL, timeout=1800):
    """-> {"text", "segments", "seconds"} von POST /transcribe. Wirft RuntimeError mit der Meldung des Dienstes."""
    path = Path(audio_path)
    try:
        with path.open("rb") as fh:
            r = httpx.post(f"{url}/transcribe", files={"file": (path.name, fh)}, timeout=timeout)
    except httpx.HTTPError as e:
        raise RuntimeError(f"Transkriptions-Dienst nicht erreichbar ({url}): {e}") from None
    if r.status_code != 200:
        raise RuntimeError(f"Transkription: {r.json().get('detail', r.text) if r.headers.get('content-type', '').startswith('application/json') else r.text}")
    return r.json()


def health(url=URL, timeout=3):
    try:
        return httpx.get(f"{url}/health", timeout=timeout).json()
    except httpx.HTTPError:
        return {"status": "offline"}


def unload(url=URL, timeout=30):
    """Modell des Dienstes sofort von der GPU entladen. -> True, wenn etwas entladen wurde; False auch, wenn offline."""
    try:
        return httpx.post(f"{url}/unload", timeout=timeout).json().get("unloaded", False)
    except httpx.HTTPError:
        return False
