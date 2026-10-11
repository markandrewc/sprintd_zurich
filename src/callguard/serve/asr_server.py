"""HTTP front for the profile's ASR backend, so the GPU PC transcribes for the laptop.

    uv run python -m callguard.serve.asr_server -c gpu-12gb --host 127.0.0.1 --port 8010 [--token T]

* ``GET  /health`` -> ``{"status": "ok", "model_tag", "asr": <ASR cache params>, "busy", ...}``
* ``POST /transcribe?call_id=<id>[&model_tag=<tag>][&filename=<name.wav>]``, body = the raw audio
  file -> Transcript JSON (``meta.remote`` names the server setup that made it)

stdlib only (ThreadingHTTPServer): no new dependency on either machine. The ASR plugin is built once
from the profile's ``asr`` block and one lock serializes transcriptions, so concurrent requests queue
instead of competing for GPU memory. Results go through the pipeline's ASR cache (``.cache/asr``),
shared with ``callguard batch`` on the same machine: a call transcribed by either is not redone.

Bind to 127.0.0.1 (then reach it through ``scripts/remote/tunnel.sh``) or to the Tailscale IP
(``tailscale ip -4``), never to 0.0.0.0 or a public interface. With a token (``--token`` or env
``CALLGUARD_TOKEN``) every request must send ``Authorization: Bearer <token>``.
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import re
import socket
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import numpy as np
import soundfile as sf

from callguard.cache import stable_hash
from callguard.config import AppConfig, load_config
from callguard.pipeline import Pipeline
from callguard.plugins import ASRBackend
from callguard.types import Transcript

log = logging.getLogger("callguard.serve")

DEFAULT_PORT = 8010
MAX_UPLOAD = 1 << 30  # 1 GiB; a two-hour 16 kHz 16-bit mono WAV is ~230 MB
AUDIO_SUFFIXES = (".wav", ".flac", ".mp3", ".m4a", ".ogg")
ALL_INTERFACES = ("0.0.0.0", "::", "")


def default_tag(asr: ASRBackend) -> str:
    """A tag that changes whenever the ASR's output-relevant params change."""
    return f"{asr.plugin_type}-{stable_hash(asr.cache_params())[:8]}"


class ASRService:
    """Profile -> ASR plugin -> transcripts, one at a time. Socket-free, so tests can drive it directly."""

    def __init__(self, cfg: AppConfig, *, model_tag: str | None = None, use_cache: bool = True):
        if cfg.asr.get("type") == "remote":
            raise ValueError("asr type 'remote' cannot be served (the server would call itself): start it "
                             "with the profile that runs the model, e.g. -c gpu-12gb")
        self.cfg = cfg
        # only the ASR stage: no checks and no sinks, so no LLM client is ever built here
        self.pipeline = Pipeline(cfg.model_copy(update={"checks": [], "sinks": []}), use_cache=use_cache)
        self.asr = self.pipeline.asr  # built now: a missing model dir fails at start, not per request
        self.model_tag = str(model_tag or cfg.asr.get("model_tag") or default_tag(self.asr))
        self.lock = threading.Lock()
        self.started = time.time()
        self.served = 0

    def health(self) -> dict[str, Any]:
        return {"status": "ok", "model_tag": self.model_tag, "config": self.cfg.name,
                "asr": self.asr.cache_params(), "busy": self.lock.locked(), "served": self.served,
                "uptime_s": round(time.time() - self.started, 1)}

    def transcribe(self, data: bytes, call_id: str, filename: str | None = None) -> Transcript:
        suffix = Path(filename or "").suffix.lower()
        suffix = suffix if suffix in AUDIO_SUFFIXES else ".wav"
        with tempfile.TemporaryDirectory(prefix="callguard-asr-") as tmp:
            path = Path(tmp) / f"{re.sub(r'[^A-Za-z0-9._-]+', '_', call_id)[:120] or 'call'}{suffix}"
            path.write_bytes(data)
            with self.lock:
                t0 = time.time()
                t = self.pipeline.transcribe(path, call_id)  # cached per audio hash + ASR params
                seconds = time.time() - t0
                self.served += 1
        log.info("transcribed %s (%d segments) in %.1fs", call_id, len(t.segments), seconds)
        t.audio_path = None  # the temp file is gone; the client sets its own path
        t.meta["remote"] = {"model_tag": self.model_tag, "server_config": self.cfg.name,
                            "server_seconds": round(seconds, 2)}
        return t

    def warmup(self) -> None:
        """Load the model before the first request pays for it: 1 s of silence, never cached."""
        with tempfile.TemporaryDirectory(prefix="callguard-asr-") as tmp:
            p = Path(tmp) / "warmup.wav"
            sf.write(str(p), np.zeros(16000, dtype=np.float32), 16000, subtype="PCM_16")
            t0 = time.time()
            try:
                with self.lock:
                    self.asr.transcribe(p, "warmup")
            except Exception as e:  # e.g. the reference backend has no script for "warmup"
                log.warning("warm-up failed (%s: %s); the first request loads the model", type(e).__name__, e)
            else:
                log.info("warm-up done in %.1fs", time.time() - t0)


class Handler(BaseHTTPRequestHandler):
    server: ASRHTTPServer
    server_version = "callguard-asr/1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path != "/health":
            self._json(404, {"error": f"unknown path {path}: use GET /health or POST /transcribe"})
        elif self._authorized():
            self._json(200, self.server.service.health())
        else:
            self._unauthorized()

    def do_POST(self) -> None:
        url = urlparse(self.path)
        if url.path != "/transcribe":
            self._json(404, {"error": f"unknown path {url.path}: use GET /health or POST /transcribe"})
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self._json(411, {"error": "Content-Length required (send the audio file as the request body)"})
            return
        if length > MAX_UPLOAD:
            self.close_connection = True
            self._json(413, {"error": f"upload of {length} bytes exceeds {MAX_UPLOAD} bytes"})
            return
        if not self._authorized():
            self._drain(length)  # answer only after the upload, else the client sees a reset, not a 401
            self._unauthorized()
            return
        body = self.rfile.read(length)
        query = parse_qs(url.query)
        call_id = (query.get("call_id") or [""])[0].strip()
        wanted = (query.get("model_tag") or [""])[0].strip()
        service = self.server.service
        if len(body) != length or not body:
            self._json(400, {"error": f"expected {length} bytes of audio, got {len(body)}"})
        elif not call_id:
            self._json(400, {"error": "query parameter call_id missing"})
        elif wanted and wanted != service.model_tag:
            self._json(409, {"error": f"this server runs model_tag {service.model_tag!r} "
                                      f"({service.cfg.name}: {service.asr.plugin_type}), the client expects "
                                      f"{wanted!r}: align asr.model_tag in the client profile, or restart the "
                                      f"server with the intended profile / --model-tag"})
        else:
            try:
                t = service.transcribe(body, call_id, (query.get("filename") or [None])[0])
            except (FileNotFoundError, ValueError) as e:  # unreadable audio, no script for this call...
                self._json(422, {"error": f"{type(e).__name__}: {e}"})
            except Exception as e:
                log.exception("transcription of %s failed", call_id)
                self._json(500, {"error": f"{type(e).__name__}: {e}"})
            else:
                self._send(200, t.model_dump_json().encode(), "application/json")

    # -- helpers ------------------------------------------------------------------------------

    def _authorized(self) -> bool:
        token = self.server.token
        if not token:
            return True
        got = self.headers.get("Authorization", "")
        return hmac.compare_digest(got.encode(), f"Bearer {token}".encode())

    def _unauthorized(self) -> None:
        self._json(401, {"error": "missing or wrong bearer token (set CALLGUARD_TOKEN on the client)"},
                   {"WWW-Authenticate": "Bearer"})

    def _drain(self, length: int) -> None:
        while length > 0:
            chunk = self.rfile.read(min(length, 1 << 20))
            if not chunk:
                break
            length -= len(chunk)

    def _json(self, status: int, obj: Any, headers: dict[str, str] | None = None) -> None:
        self._send(status, json.dumps(obj, ensure_ascii=False, default=str).encode(), "application/json",
                   headers)

    def _send(self, status: int, body: bytes, ctype: str, headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002 - signature of the base class
        log.info("%s %s", self.address_string(), format % args)


class ASRHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: ASRService, token: str | None = None):
        if ":" in address[0]:
            self.address_family = socket.AF_INET6
        super().__init__(address, Handler)
        self.service = service
        self.token = token or None

    @property
    def url(self) -> str:
        host, port = self.server_address[:2]
        return f"http://[{host}]:{port}" if ":" in str(host) else f"http://{host}:{port}"


def make_server(service: ASRService, host: str = "127.0.0.1", port: int = DEFAULT_PORT,
                token: str | None = None) -> ASRHTTPServer:
    """Bound but not yet serving (call ``serve_forever``). ``port=0`` picks a free port (tests)."""
    return ASRHTTPServer((host, port), service, token)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m callguard.serve.asr_server",
                                description="Serve the profile's ASR backend over HTTP (see docs/REMOTE_GPU.md).")
    p.add_argument("-c", "--config", default=os.environ.get("CALLGUARD_CONFIG") or "gpu-12gb",
                   help="profile whose asr block is served (default gpu-12gb)")
    p.add_argument("--set", dest="sets", action="append", default=[], help="config override, repeatable")
    p.add_argument("--host", default="127.0.0.1",
                   help="address to bind: 127.0.0.1 (SSH tunnel) or the Tailscale IP (`tailscale ip -4`)")
    p.add_argument("--port", type=int, default=DEFAULT_PORT)
    p.add_argument("--token", default=None, help="require this bearer token (default: env CALLGUARD_TOKEN)")
    p.add_argument("--model-tag", default=None,
                   help="name of this ASR setup (default: asr.model_tag of the profile, else derived)")
    p.add_argument("--warmup", action="store_true", help="load the model before accepting requests")
    p.add_argument("--no-cache", action="store_true", help="do not read or write .cache/asr")
    p.add_argument("--allow-all-interfaces", action="store_true",
                   help="permit --host 0.0.0.0 / :: (exposes the server to every network the host is on)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if args.host in ALL_INTERFACES and not args.allow_all_interfaces:
        p.error("refusing to listen on all interfaces: bind 127.0.0.1 or the Tailscale IP (`tailscale ip -4`)")
    token = args.token if args.token is not None else os.environ.get("CALLGUARD_TOKEN")
    service = ASRService(load_config(args.config, args.sets), model_tag=args.model_tag,
                         use_cache=not args.no_cache)
    if args.warmup:
        service.warmup()
    httpd = make_server(service, args.host, args.port, token)
    log.info("callguard ASR server on %s (profile %s, %s, model_tag %s, token %s)", httpd.url,
             service.cfg.name, service.asr.plugin_type, service.model_tag, "required" if token else "off")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
