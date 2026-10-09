"""Remote ASR: the audio goes to ``callguard.serve.asr_server`` on the GPU PC, a Transcript comes back.

For ``config/remote.yaml``: app and UI stay on the laptop, Whisper runs on the PC's GPU, reached over
the tailnet (or an SSH tunnel, ``scripts/remote/tunnel.sh``). The pipeline caches the answer like any
ASR output, so each recording crosses the network once.

The cache identity is ``model_tag``, the server's name for its ASR setup, not the URL: the same server
reached by tailnet name or through a tunnel shares cached transcripts. The server refuses a request
whose ``model_tag`` differs from its own, so a transcript is never filed under the wrong model.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from callguard.asr import drop_inherited
from callguard.plugins import ASRBackend
from callguard.types import Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.asr")

TOKEN_ENV = "CALLGUARD_TOKEN"
UNREACHABLE_HINT = ("start scripts/remote/serve_models.sh on the GPU host; check `tailscale status` "
                    "(or run scripts/remote/tunnel.sh and set CALLGUARD_GPU_HOST=127.0.0.1)")


class RemoteASRError(RuntimeError):
    """The ASR server could not be reached, refused the request or sent no transcript."""


def resolve_token(token: str | None) -> str | None:
    """``None`` -> env ``CALLGUARD_TOKEN`` (unset: no token); ``none``/empty -> no token;
    ``env:VAR`` -> ``$VAR``. Keeps the secret out of YAML files and cache keys."""
    if token is None:
        return os.environ.get(TOKEN_ENV) or None
    text = str(token)
    if not text or text.lower() == "none":
        return None
    if text.startswith("env:"):
        return os.environ.get(text[4:]) or None
    return text


def _error_text(r: httpx.Response) -> str:
    try:
        data = r.json()
    except ValueError:
        data = None
    if isinstance(data, dict) and data.get("error"):
        return str(data["error"])
    text = " ".join(r.text.split())
    return text[:300] + ("..." if len(text) > 300 else "")


class RemoteASR(ASRBackend):
    """``url``: the ASR server, e.g. ``http://gpu-pc:8010``. ``model_tag``: the ASR setup this profile
    expects (None: adopt whatever the server announces). ``token``: see :func:`resolve_token`."""

    plugin_kind = "asr"
    plugin_type = "remote"
    down_cooldown = 30.0  # after a connect failure, fail fast instead of waiting per call

    def __init__(self, ctx: Context, url: str, timeout: float = 900, model_tag: str | None = None,
                 token: str | None = None, **inherited: Any):
        super().__init__(ctx, url=url, timeout=timeout, model_tag=model_tag)  # no token in params/keys
        self.ignored_params = drop_inherited("remote", inherited)
        if not str(url).startswith(("http://", "https://")):
            raise ValueError(f"asr.url must start with http:// or https://, got {url!r}")
        self.url = str(url).rstrip("/")
        self.timeout = float(timeout)
        self.model_tag = str(model_tag) if model_tag not in (None, "") else None
        self._token = resolve_token(token)
        self._server_tag: str | None = None
        self._down_at: float | None = None

    def cache_params(self) -> dict[str, Any]:
        """The transcript depends on the server's ASR setup, which ``model_tag`` names; URL, token
        and timeout only decide how to reach it."""
        return {"type": self.plugin_type, "model_tag": self.model_tag or self.server_tag()}

    def health(self, timeout: float = 5.0) -> dict[str, Any]:
        """The server's ``GET /health`` (raises :class:`RemoteASRError` with a hint on failure)."""
        r = self._request("GET", "/health", timeout=httpx.Timeout(timeout, connect=min(timeout, 5.0)))
        try:
            return dict(r.json())
        except (ValueError, TypeError) as e:
            raise RemoteASRError(f"{self.url}/health sent no JSON object: {_error_text(r)}") from e

    def server_tag(self) -> str:
        """The tag the server announces (asked once): the cache identity when none is configured."""
        if self._server_tag is None:
            tag = self.health().get("model_tag")
            if not tag:
                raise RemoteASRError(f"remote ASR at {self.url} announces no model_tag; set asr.model_tag")
            self._server_tag = str(tag)
        return self._server_tag

    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        path = Path(audio_path)
        params = {"call_id": call_id, "filename": path.name}
        if self.model_tag:
            params["model_tag"] = self.model_tag
        t0 = time.time()
        r = self._request("POST", "/transcribe", params=params, content=path.read_bytes(),
                          headers={"Content-Type": "application/octet-stream"},
                          timeout=httpx.Timeout(self.timeout, connect=min(self.timeout, 10.0)))
        try:
            t = Transcript.model_validate_json(r.content)
        except ValueError as e:
            raise RemoteASRError(f"remote ASR at {self.url} sent no valid transcript: {_error_text(r)}") from e
        remote = t.meta.setdefault("remote", {})
        served = remote.get("model_tag")
        if self.model_tag and served and served != self.model_tag:  # a server too old to check itself
            raise RemoteASRError(f"remote ASR at {self.url} runs model_tag {served!r}, this profile expects "
                                 f"{self.model_tag!r}")
        remote.update(url=self.url, roundtrip_seconds=round(time.time() - t0, 2))
        t.call_id, t.audio_path = call_id, str(audio_path)  # the server only saw a temp file
        return t

    def _request(self, method: str, path: str, *, headers: dict[str, str] | None = None,
                 **kw: Any) -> httpx.Response:
        if self._down_at is not None and time.monotonic() - self._down_at < self.down_cooldown:
            raise RemoteASRError(f"remote ASR at {self.url} not reachable (failed less than "
                                 f"{self.down_cooldown:g}s ago) - {UNREACHABLE_HINT}")
        hdrs = dict(headers or {})
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"
        try:
            r = httpx.request(method, self.url + path, headers=hdrs, **kw)
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as e:
            raise RemoteASRError(f"remote ASR at {self.url} did not answer in time ({type(e).__name__}); a "
                                 f"long call behind others on the GPU can take minutes: raise asr.timeout "
                                 f"(now {self.timeout:g}s)") from e
        except httpx.TransportError as e:  # refused, DNS, connect timeout: the host or server is down
            self._down_at = time.monotonic()
            raise RemoteASRError(f"remote ASR at {self.url} not reachable - {UNREACHABLE_HINT} "
                                 f"[{type(e).__name__}: {e}]") from e
        self._down_at = None
        if r.status_code == 401:
            raise RemoteASRError(f"remote ASR at {self.url} rejected the request (HTTP 401): set {TOKEN_ENV} "
                                 f"(or asr.token) to the server's token")
        if r.status_code >= 400:
            raise RemoteASRError(f"remote ASR at {self.url} returned HTTP {r.status_code}: {_error_text(r)}")
        return r
