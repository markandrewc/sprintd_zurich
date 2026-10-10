"""HTTP-Client für den Fraud-Analyse-Dienst (fraud_analysis.api). Ohne torch/Kev importierbar.

URL über FRAUD_URL (Default http://127.0.0.1:8002).
"""
import os

import httpx

URL = os.environ.get("FRAUD_URL", "http://127.0.0.1:8002")


def analyze(transcript, threshold=None, questions=None, url=URL, timeout=300):
    """-> Ergebnis von POST /analyze. Wirft RuntimeError mit der Meldung des Dienstes bei einem Fehler."""
    body = {"transcript": transcript, "threshold": threshold, "questions": questions}
    try:
        r = httpx.post(f"{url}/analyze", json=body, timeout=timeout)
    except httpx.HTTPError as e:
        raise RuntimeError(f"Fraud-Analyse-Dienst nicht erreichbar ({url}): {e}") from None
    if r.status_code != 200:
        raise RuntimeError(f"Fraud-Analyse: {r.json().get('detail', r.text) if r.headers.get('content-type', '').startswith('application/json') else r.text}")
    return r.json()


def config(url=URL, timeout=10):
    return httpx.get(f"{url}/config", timeout=timeout).raise_for_status().json()


def health(url=URL, timeout=3):
    try:
        return httpx.get(f"{url}/health", timeout=timeout).json()
    except httpx.HTTPError:
        return {"status": "offline"}
