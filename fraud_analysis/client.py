"""HTTP-Client für den Fraud-Analyse-Dienst (fraud_analysis.api). Ohne torch/Kev importierbar.

URL über FRAUD_URL (Default http://127.0.0.1:8002).
"""
import os

import httpx

URL = os.environ.get("FRAUD_URL", "http://127.0.0.1:8002")


def analyze(transcript=None, segments=None, threshold=None, passage_words=None, url=URL, timeout=300):
    """-> Ergebnis von POST /analyze (Fakten, ausgelöste Regeln, Alarm). segments: [{start, end, text, speaker?}] aus der
    Transkription. Wirft RuntimeError mit der Meldung des Dienstes bei einem Fehler."""
    body = {"transcript": transcript, "segments": segments, "threshold": threshold, "passage_words": passage_words}
    try:
        r = httpx.post(f"{url}/analyze", json=body, timeout=timeout)
    except httpx.HTTPError as e:
        raise RuntimeError(f"Fraud-Analyse-Dienst nicht erreichbar ({url}): {e}") from None
    if r.status_code != 200:
        raise RuntimeError(f"Fraud-Analyse: {r.json().get('detail', r.text) if r.headers.get('content-type', '').startswith('application/json') else r.text}")
    return r.json()


def save_config(facts, rules, url=URL, timeout=30):
    """Fakten und Regeln ersetzen (PUT /config). -> {"version", "facts", "rules"}. RuntimeError mit der Meldung des Dienstes."""
    try:
        r = httpx.put(f"{url}/config", json={"facts": facts, "rules": rules}, timeout=timeout)
    except httpx.HTTPError as e:
        raise RuntimeError(f"Fraud-Analyse-Dienst nicht erreichbar ({url}): {e}") from None
    if r.status_code != 200:
        raise RuntimeError(r.json().get("detail", r.text) if r.headers.get("content-type", "").startswith("application/json") else r.text)
    return r.json()


def config(url=URL, timeout=10):
    return httpx.get(f"{url}/config", timeout=timeout).raise_for_status().json()


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
