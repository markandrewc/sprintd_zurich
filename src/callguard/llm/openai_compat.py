"""Client for any OpenAI-compatible chat server: vLLM on the event GPUs, llama-cpp-python or the
llama.cpp server on a laptop, Ollama. One code path; only ``base_url``, ``model`` and ``json_mode``
differ between machines.

Servers disagree on structured output, so ``json_mode`` picks the dialect:

* ``json_schema``        ``{"type": "json_schema", "json_schema": {...}}`` (OpenAI, vLLM, llama.cpp server)
* ``json_object_schema`` ``{"type": "json_object", "schema": {...}}`` (llama-cpp-python's server)
* ``json_object``        plain JSON mode; the schema goes into the prompt
* ``none``               no ``response_format``; the schema goes into the prompt

If the server rejects the configured ``response_format`` the client falls back to ``none`` for the
rest of the session instead of failing every call.

Model identity: the GPU profiles serve whatever model under one alias (``callguard-llm``), so the
configured name says nothing about the weights. ``model_id`` (and with it every LLM check's cache
key) is therefore what ``GET /models`` reports behind the name (vLLM: ``root``), or ``cache_tag`` when
set; see :meth:`OpenAICompatLLM.served_model`.
"""

from __future__ import annotations

import copy
import json
import logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from callguard.cache import stable_hash
from callguard.llm import choice_distribution, request_seeds, with_schema_instruction
from callguard.llm.jsonutil import strip_reasoning
from callguard.plugins import LLM

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.llm")

JSON_MODES = ("json_schema", "json_object_schema", "json_object", "none")
_RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}
_FORMAT_WORDS = ("response_format", "json_schema", "schema", "guided", "grammar", "structured output")


class LLMRequestError(RuntimeError):
    """The server answered, but with an error (bad model name, rejected parameter, overload...)."""

    def __init__(self, message: str, status: int | None = None, body: str = ""):
        super().__init__(message)
        self.status = status
        self.body = body


def _snippet(text: str, n: int = 300) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[:n] + "..."


def _resolve_api_key(api_key: str | None) -> str | None:
    """``none``/empty -> no Authorization header; ``env:VAR`` -> read the secret from the
    environment so keys never end up in YAML or cache keys."""
    if not api_key or str(api_key).lower() == "none":
        return None
    if str(api_key).startswith("env:"):
        var = str(api_key)[4:]
        val = os.environ.get(var)
        if not val:
            log.warning("api_key env var %s is not set; sending no Authorization header", var)
        return val or None
    return str(api_key)


def model_entries(data: Any) -> list[dict[str, Any]]:
    """The model objects of an OpenAI-style ``GET /models`` answer (``{"data": [...]}``)."""
    items = data.get("data") if isinstance(data, dict) else None
    return [e for e in items if isinstance(e, dict)] if isinstance(items, list) else []


def served_identity(data: Any, model: str) -> tuple[bool, str | None]:
    """``(listed, identity)`` of the weights a server answers to as ``model``.

    vLLM names the checkpoint in ``root`` (``--served-model-name`` only renames it; a LoRA adapter adds
    its base as ``parent``). The llama.cpp server describes the loaded GGUF in ``meta`` (parameter
    count, file size). llama-cpp-python and Ollama report the name only: identity None, use
    ``cache_tag`` there when serving under an alias.
    """
    entry = next((e for e in model_entries(data) if str(e.get("id")) in (model, f"{model}:latest")), None)
    if entry is None:
        return False, None
    root, parent = entry.get("root"), entry.get("parent")
    if root and str(root) != model:
        return True, f"{root}@{parent}" if parent else str(root)
    meta = entry.get("meta")
    if isinstance(meta, dict) and (meta.get("n_params") or meta.get("size")):
        return True, f"{model}#gguf:{meta.get('n_params')}p:{meta.get('size')}b"
    return True, None


class OpenAICompatLLM(LLM):
    backoff = 1.0  # seconds before the first retry, doubled each time
    down_cooldown = 30.0  # after "unreachable", fail fast (no retries) for this many seconds
    served_ttl = 300.0  # re-read GET /models after this long: the alias may name another model by now

    def __init__(self, ctx: "Context", base_url: str, model: str, api_key: str | None = "none",
                 timeout: float = 120, json_mode: str = "json_schema", max_retries: int = 2,
                 extra_body: dict[str, Any] | None = None, supports_n: bool = False,
                 seed: int | None = None, max_concurrency: int = 1, cache_tag: str | None = None):
        super().__init__(ctx, base_url=base_url, model=model, api_key=api_key, timeout=timeout,
                         json_mode=json_mode, max_retries=max_retries, extra_body=extra_body,
                         supports_n=supports_n, seed=seed, max_concurrency=max_concurrency,
                         cache_tag=cache_tag)
        if json_mode not in JSON_MODES:
            raise ValueError(f"json_mode {json_mode!r} unknown; expected one of {JSON_MODES}")
        self.base_url = str(base_url).rstrip("/")
        self.model = str(model)
        self.timeout = float(timeout)
        self.json_mode = json_mode
        self.max_retries = max(0, int(max_retries))
        self.extra_body = dict(extra_body or {})
        self.supports_n = bool(supports_n)
        self.seed = seed
        self.max_concurrency = max(1, int(max_concurrency))
        self._api_key = _resolve_api_key(api_key)
        self._active_json_mode = json_mode  # degrades to "none" once the server rejects it
        self._logprobs_ok: bool | None = None  # None = not probed yet
        self._down_at: float | None = None
        self.cache_tag = str(cache_tag) if cache_tag not in (None, "") else None
        self._served: str | None = None  # identity behind `model` per GET /models (None: the name itself)
        self._served_at: float | None = None
        self._served_ok = False  # last lookup reached the server (else: fallback, retried sooner)
        self._served_lock = threading.Lock()
        self._sem = threading.BoundedSemaphore(self.max_concurrency)
        self._rng = random.Random()
        self._client = self._build_client()

    def _build_client(self, transport: httpx.BaseTransport | None = None) -> httpx.Client:
        headers = {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}
        return httpx.Client(base_url=self.base_url, headers=headers, transport=transport,
                            timeout=httpx.Timeout(self.timeout, connect=min(10.0, self.timeout)))

    @property
    def model_id(self) -> str:
        """What the answers come from: ``cache_tag`` if configured, else the served model's identity
        (:meth:`served_model`), else the configured name."""
        return self.cache_tag or self.served_model() or self.model

    def cache_params(self) -> dict[str, Any]:
        # Only what changes the answers; not the URL, key, timeouts or concurrency. "model" is the
        # identity, not the alias: swapping the model behind `callguard-llm` must not reuse old results.
        return {"type": self.plugin_type, "model": self.model_id, "json_mode": self.json_mode,
                "seed": self.seed, "extra_body": self.extra_body}

    def list_models(self, timeout: float = 5.0) -> list[dict[str, Any]]:
        """``GET /models`` entries (raises on transport/HTTP errors). Used by ``callguard doctor``."""
        r = self._client.get("/models", timeout=httpx.Timeout(timeout, connect=min(3.0, timeout)))
        r.raise_for_status()
        return model_entries(r.json())

    def served_model(self) -> str | None:
        """Identity of the weights behind ``model`` (see :func:`served_identity`), re-read every
        ``served_ttl`` seconds. None when the server names nothing beyond ``model``.

        Server unreachable: the identity last seen for this name, persisted in
        ``<cache_dir>/llm_served/`` (and pulled back from the GPU box with its cache), so cached
        results stay usable offline; a failed lookup is retried after ``down_cooldown``.
        """
        with self._served_lock:
            now = time.monotonic()
            ttl = self.served_ttl if self._served_ok else self.down_cooldown
            if self._served_at is not None and now - self._served_at < ttl:
                return self._served
            self._served_at = now
            try:
                listed, ident = served_identity({"data": self.list_models(timeout=5.0)}, self.model)
            except (httpx.HTTPError, ValueError) as e:
                self._served_ok = False
                self._served = self._load_served()
                if self._served:
                    log.warning("%s unreachable for GET /models (%s); cache keys use the last known model "
                                "behind %r: %s", self.base_url, type(e).__name__, self.model, self._served)
                return self._served
            self._served_ok = True
            if ident and ident != self._served:
                log.info("%s serves %r as %s", self.base_url, self.model, ident)
            self._served = ident
            if listed:
                self._store_served(ident)
            return ident

    def _served_file(self) -> Path | None:
        cache = getattr(self.ctx, "cache", None)
        if cache is None or not getattr(cache, "enabled", False):
            return None
        return Path(cache.root) / "llm_served" / f"{stable_hash(self.model)}.json"

    def _load_served(self) -> str | None:
        p = self._served_file()
        try:
            data = json.loads(p.read_text()) if p is not None and p.exists() else {}
        except (OSError, ValueError):
            return None
        served = data.get("served") if isinstance(data, dict) and data.get("model") == self.model else None
        return str(served) if served else None

    def _store_served(self, ident: str | None) -> None:
        p = self._served_file()
        if p is None:
            return
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps({"model": self.model, "served": ident, "base_url": self.base_url,
                                       "seen": time.strftime("%Y-%m-%d %H:%M:%S")}, indent=1))
            tmp.replace(p)
        except OSError as e:  # read-only cache dir: the key is still right, only offline reuse suffers
            log.debug("could not remember served model in %s: %s", p, e)

    def ping(self, timeout: float = 3.0) -> bool:
        """Liveness probe (``GET /models``) for the UI, CLI and test skips. llama-cpp-python holds
        its model lock for ``/models`` too, so a server busy generating does not answer in time:
        an accepted connection without an answer counts as alive, only connect failures as down."""
        try:
            return self._client.get("/models", timeout=timeout).status_code < 500
        except (httpx.ReadTimeout, httpx.PoolTimeout):
            return True
        except httpx.HTTPError:
            return False

    # -- public API ---------------------------------------------------------------------------

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512,
             n: int = 1, json_schema: dict | None = None, stop: list[str] | None = None) -> list[str]:
        n = max(1, int(n))
        out: list[str] = []
        if self.supports_n and n > 1:
            out = self._complete(messages, temperature, max_tokens, json_schema, stop, n=n, seed=self.seed)[:n]
            if len(out) < n:
                log.warning("%s returned %d of %d requested samples; requesting the rest one by one",
                            self.base_url, len(out), n)
        missing = n - len(out)
        if missing:
            seeds = request_seeds(missing, temperature, None if self.seed is None else self.seed + len(out),
                                  self._rng)

            def one(seed: int | None) -> str:
                got = self._complete(messages, temperature, max_tokens, json_schema, stop, n=1, seed=seed)
                return got[0] if got else ""

            if self.max_concurrency > 1 and missing > 1:
                with ThreadPoolExecutor(max_workers=min(missing, self.max_concurrency)) as pool:
                    out.extend(pool.map(one, seeds))
            else:
                out.extend(one(s) for s in seeds)
        return out

    def choice_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float] | None:
        if self._logprobs_ok is False or not choices:
            return None
        payload = {**copy.deepcopy(self.extra_body), "model": self.model, "messages": messages,
                   "max_tokens": 1, "temperature": 0.0, "logprobs": True, "top_logprobs": 20}
        if self.seed is not None:
            payload["seed"] = int(self.seed)
        try:
            data = self._post(payload)
        except LLMRequestError as e:
            if e.status and 400 <= e.status < 600 and "logprob" in e.body.lower():
                self._logprobs_disabled(f"server rejected logprobs: {_snippet(e.body, 160)}")
                return None
            raise
        top = _top_logprobs(data)
        if top is None:
            self._logprobs_disabled("response carries no logprobs")
            return None
        self._logprobs_ok = True
        return choice_distribution(top, choices)

    # -- internals ----------------------------------------------------------------------------

    def _logprobs_disabled(self, why: str) -> None:
        log.warning("%s (%s): %s; choice_probs returns None from now on (callers fall back to sampling)",
                    self.base_url, self.model, why)
        self._logprobs_ok = False

    def _payload(self, messages: list[dict[str, str]], temperature: float, max_tokens: int,
                 json_schema: dict | None, stop: list[str] | None, n: int, seed: int | None,
                 mode: str) -> dict[str, Any]:
        if json_schema and mode in ("json_object", "none"):
            messages = with_schema_instruction(messages, json_schema)
        payload: dict[str, Any] = {**copy.deepcopy(self.extra_body), "model": self.model,
                                   "messages": messages, "temperature": float(temperature),
                                   "max_tokens": int(max_tokens)}
        if n > 1:
            payload["n"] = n
        if stop:
            payload["stop"] = list(stop)
        if seed is not None:
            payload["seed"] = int(seed)
        if json_schema:
            if mode == "json_schema":
                payload["response_format"] = {"type": "json_schema", "json_schema": {
                    "name": "output", "schema": json_schema, "strict": True}}
            elif mode == "json_object_schema":
                payload["response_format"] = {"type": "json_object", "schema": json_schema}
            elif mode == "json_object":
                payload["response_format"] = {"type": "json_object"}
        return payload

    def _complete(self, messages: list[dict[str, str]], temperature: float, max_tokens: int,
                  json_schema: dict | None, stop: list[str] | None, *, n: int, seed: int | None) -> list[str]:
        mode = self._active_json_mode
        payload = self._payload(messages, temperature, max_tokens, json_schema, stop, n, seed, mode)
        try:
            data = self._post(payload)
        except LLMRequestError as e:
            body = e.body.lower()
            if not ("response_format" in payload and e.status and e.status >= 400
                    and any(w in body for w in _FORMAT_WORDS)):
                raise
            if "response_format" in body or "json_schema" in body:  # the dialect itself is unsupported
                log.warning("%s rejected response_format for json_mode=%s (%s); using json_mode=none "
                            "(schema in the prompt) for this session - set json_mode in the config to "
                            "match the server", self.base_url, mode, _snippet(e.body, 160))
                self._active_json_mode = "none"
            else:  # only this schema cannot be compiled into a grammar
                log.warning("%s could not constrain output to this schema (%s); schema goes into the "
                            "prompt for this request", self.base_url, _snippet(e.body, 160))
            payload = self._payload(messages, temperature, max_tokens, json_schema, stop, n, seed, "none")
            data = self._post(payload)
        choices = data.get("choices") or []
        if not choices:
            raise LLMRequestError(f"LLM server at {self.base_url} returned no choices: "
                                  f"{_snippet(str(data))}", 200, str(data))
        return [strip_reasoning(_content(c)) for c in choices]

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        recently_down = self._down_at is not None and time.monotonic() - self._down_at < self.down_cooldown
        attempts = 1 if recently_down else 1 + self.max_retries
        last: Exception | None = None
        for attempt in range(attempts):
            if attempt:
                time.sleep(self.backoff * 2 ** (attempt - 1))
            try:
                with self._sem:
                    r = self._client.post("/chat/completions", json=payload)
            except httpx.TransportError as e:  # refused, reset, DNS, any timeout
                last = e
                continue
            self._down_at = None
            if r.status_code < 400:
                try:
                    return r.json()
                except ValueError as e:
                    raise LLMRequestError(f"LLM server at {self.base_url} sent non-JSON: "
                                          f"{_snippet(r.text)}", r.status_code, r.text) from e
            err = LLMRequestError(f"LLM server at {self.base_url} returned HTTP {r.status_code}: "
                                  f"{_snippet(r.text)}", r.status_code, r.text)
            if r.status_code in _RETRY_STATUS and not any(w in r.text.lower() for w in _FORMAT_WORDS):
                last = err
                continue
            raise err
        if isinstance(last, LLMRequestError):
            raise last
        if isinstance(last, (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout)):
            raise LLMRequestError(f"LLM request to {self.base_url} timed out after {self.timeout:g}s "
                                  f"({attempts} attempt(s)); raise `timeout` in the llm config or use "
                                  f"a smaller model") from last
        self._down_at = time.monotonic()
        raise RuntimeError(f"LLM server at {self.base_url} not reachable - start scripts/serve_llm_local.sh "
                           f"(local), scripts/serve_vllm.sh (GPU) or scripts/remote/serve_models.sh on the "
                           f"GPU host (then check `tailscale status`) [{type(last).__name__}: {last}]") from last


def _content(choice: dict[str, Any]) -> str:
    msg = choice.get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):  # content parts
        content = "".join(p.get("text", "") for p in content if isinstance(p, dict))
    if content is None:
        content = choice.get("text")
    return content or ""


def _top_logprobs(data: dict[str, Any]) -> list[tuple[str, float]] | None:
    """Top alternatives for the first generated token, in either the chat (``content``) or the
    legacy completions (``top_logprobs`` dicts) shape."""
    try:
        lp = (data.get("choices") or [{}])[0].get("logprobs")
    except (AttributeError, IndexError):
        return None
    if not isinstance(lp, dict):
        return None
    content = lp.get("content")
    if isinstance(content, list) and content:
        first = content[0] or {}
        top = first.get("top_logprobs") or []
        pairs = [(t.get("token", ""), t.get("logprob")) for t in top if isinstance(t, dict)]
        if not pairs and "token" in first:
            pairs = [(first.get("token", ""), first.get("logprob"))]
        return pairs or None
    legacy = lp.get("top_logprobs")
    if isinstance(legacy, list) and legacy and isinstance(legacy[0], dict):
        return list(legacy[0].items()) or None
    return None
