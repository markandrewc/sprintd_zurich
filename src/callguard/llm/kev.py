"""Client for a Kev service: ``jaredpalmer/kev-4b`` (Qwen3.5-4B LoRA + pointer head) answers many yes/no
questions about one text in a single forward pass and returns p(yes) per question. No torch here: the model
runs in the teammate's environment behind ``scripts/remote/serve_kev.py`` (docs/KEV.md).

Wire format (TypeSafe "systemone", as in sprintd_zurich ``fraud_analysis/kev/api.py``)::

    POST /v1/systemone {"state": "<text>", "questions": {qid: {"type": "noul", "instructions": "...",
                         "criteria"?: {"true": ..., "false": ...}}}, "calibrated": false}
    -> {"model": "jaredpalmer/kev-4b", "answers": {qid: {"type": "noul", "noul": 0.83}},
        "usage": {"input_tokens": n, "output_tokens": m}, "latency_ms": 41.0}
    GET /health -> {"status": "ok", "model": ..., "dtype": "bf16", "revision": ..., "loaded": true}

Checks use it in two ways:

* :meth:`KevLLM.noul_batch` ``(state, {qid: question}) -> {qid: p(yes)}``: the ``questions`` check
  (checks/questions.py) asks all its questions in one request per call.
* :meth:`KevLLM.choice_probs`: lets the unchanged ``facts`` check use Kev as its probability backend
  (``checks.facts.llm: kev``). The transcript and the question are read back out of the fact prompt
  (``fact_prompts.fact_messages``: ``<transcript>...</transcript>``, ``Topic:``, ``Question:``); the
  system prompt and the answer instruction are dropped (Kev has its own head). ``fact_answer: noul``
  returns ``{"yes": p, "no": 1 - p, "unknown": 0}`` (Kev has no "unknown": rules that test ``= unclear``
  only fire through ``unclear_band``); ``fact_answer: choice`` asks a Kev choice question over
  yes / no / unknown with the fact prompt's definitions of the three answers.

``chat`` raises: Kev writes no text, so the facts check's JSON evidence step needs ``evidence: false``
(otherwise every fact with p(yes) > evidence_min is reported as an evidence error).

Identity (audit F3): ``model_id`` is the model the service reports (``GET /health``), confirmed live by
:meth:`resolve_served` at experiment start (raises if the service is down or serves another model / dtype);
offline it is the configured ``model``. ``cache_params`` adds dtype, calibration and the fact mapping, so
noul and choice answers never share cache entries. ``calibrated: false`` (default) matches the teammate's
analysis (raw logits, T = 1); the checkpoint's fitted temperature is one monotone transform for all
questions, so it moves thresholds but not the ranking of max p(yes) (AUC unchanged).
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import TYPE_CHECKING, Any

import httpx

from callguard.llm.openai_compat import LLMIdentityError
from callguard.plugins import LLM

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.llm.kev")

FACT_ANSWERS = ("noul", "choice")
# fact_prompts.system_prompt's definitions of the three answers, as Kev choice options
CHOICE_CRITERIA = {
    "yes": "the call shows it",
    "no": "the call shows it is not so, or it does not happen in the call",
    "unknown": "the call raises the matter but does not let you decide",
}
_TRANSCRIPT = re.compile(r"<transcript>\n?(.*?)\n?</transcript>", re.S)
_TOPIC = re.compile(r"^Topic: (.+)$", re.M)
_QUESTION = re.compile(r"^Question: (.+)$", re.M)


class KevError(RuntimeError):
    """The Kev service is unreachable or answered with an error."""


def parse_fact_prompt(messages: list[dict[str, Any]]) -> tuple[str, str, str | None]:
    """(transcript, question, topic) from a ``fact_prompts.fact_messages`` prompt. ValueError if the prompt
    has another shape: Kev must never be fed the whole instruction text as its "state" silently."""
    user = next((m.get("content") for m in reversed(messages) if m.get("role") == "user"), None)
    if not isinstance(user, str):
        raise ValueError("Kev: no user message in the prompt")
    t, q = _TRANSCRIPT.search(user), _QUESTION.search(user)
    if t is None or q is None:
        raise ValueError("Kev: prompt is not a fact prompt (<transcript>...</transcript> + 'Question: ...' "
                         "expected); only the facts / questions checks can use a kev LLM")
    topic = _TOPIC.search(user)
    return t.group(1), q.group(1).strip(), topic.group(1).strip() if topic else None


class KevLLM(LLM):
    down_cooldown = 30.0  # after "unreachable", fail fast (no retries) for this many seconds
    backoff = 1.0

    def __init__(self, ctx: "Context", base_url: str = "http://127.0.0.1:8003", model: str = "jaredpalmer/kev-4b",
                 dtype: str = "bf16", calibrated: bool = False, fact_answer: str = "noul",
                 include_topic: bool = True, timeout: float = 300, max_retries: int = 1,
                 max_concurrency: int = 1):
        if fact_answer not in FACT_ANSWERS:
            raise ValueError(f"fact_answer must be one of {FACT_ANSWERS}, got {fact_answer!r}")
        super().__init__(ctx, base_url=base_url, model=model, dtype=dtype, calibrated=calibrated,
                         fact_answer=fact_answer, include_topic=include_topic, timeout=timeout,
                         max_retries=max_retries, max_concurrency=max_concurrency)
        self.base_url = str(base_url).rstrip("/").removesuffix("/v1")
        self.model = str(model)
        self.dtype = str(dtype)
        self.calibrated = bool(calibrated)
        self.fact_answer = fact_answer
        self.include_topic = bool(include_topic)
        self.timeout = float(timeout)
        self.max_retries = max(0, int(max_retries))
        self._served: str | None = None  # confirmed live by resolve_served()
        self.served_info: dict[str, Any] = {}
        self._down_at: float | None = None
        self._sem = threading.BoundedSemaphore(max(1, int(max_concurrency)))
        self._local = threading.local()  # last choice_probs error of this thread (see chat)
        self._client = self._build_client()

    def _build_client(self, transport: httpx.BaseTransport | None = None) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, transport=transport,
                            timeout=httpx.Timeout(self.timeout, connect=min(10.0, self.timeout)))

    # -- identity -------------------------------------------------------------------------------

    @property
    def model_id(self) -> str:
        return self._served or self.model

    def cache_params(self) -> dict[str, Any]:
        # not the URL, timeouts or concurrency: only what changes the probabilities
        return {"type": "kev", "model": self.model_id, "dtype": self.dtype, "calibrated": self.calibrated,
                "fact_answer": self.fact_answer, "include_topic": self.include_topic}

    def health(self, timeout: float = 5.0) -> dict[str, Any]:
        r = self._client.get("/health", timeout=httpx.Timeout(timeout, connect=min(3.0, timeout)))
        r.raise_for_status()
        data = r.json()
        if not isinstance(data, dict):
            raise ValueError(f"/health answered {str(data)[:100]!r}")
        return data

    def resolve_served(self, timeout: float = 10.0) -> str:
        """Live ``GET /health``: the service must be up and serve the configured model and dtype. Pins
        ``model_id`` for this process. Raises :class:`LLMIdentityError` (experiments abort before running)."""
        try:
            info = self.health(timeout)
        except (httpx.HTTPError, ValueError) as e:
            raise LLMIdentityError(f"{self.base_url}: GET /health failed ({type(e).__name__}: {e}); Kev service "
                                   f"down or still loading? (scripts/remote/serve_kev.py, docs/KEV.md)") from e
        served = str(info.get("model") or "")
        if served != self.model:
            raise LLMIdentityError(f"{self.base_url} serves Kev model {served!r}, configured {self.model!r}")
        if info.get("dtype") and str(info["dtype"]) != self.dtype:
            raise LLMIdentityError(f"{self.base_url} runs {served} in {info['dtype']}, configured {self.dtype}")
        self._served, self.served_info = served, info
        return self.model_id

    # -- requests -------------------------------------------------------------------------------

    def systemone(self, state: str, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        """One POST /v1/systemone. Raises :class:`KevError` on transport errors (after retries) and HTTP
        errors (422 = state too long / invalid question: not retried), and when an answer is missing."""
        payload = {"state": state, "questions": questions, "calibrated": self.calibrated}
        recently_down = self._down_at is not None and time.monotonic() - self._down_at < self.down_cooldown
        attempts = 1 if recently_down else 1 + self.max_retries
        last: Exception | None = None
        for attempt in range(attempts):
            if attempt:
                time.sleep(self.backoff * 2 ** (attempt - 1))
            try:
                with self._sem:
                    r = self._client.post("/v1/systemone", json=payload)
            except httpx.TransportError as e:
                last = e
                continue
            self._down_at = None
            if r.status_code >= 500 and attempt + 1 < attempts:
                last = KevError(f"Kev at {self.base_url} returned HTTP {r.status_code}: {r.text[:300]}")
                continue
            if r.status_code >= 400:
                raise KevError(f"Kev at {self.base_url} returned HTTP {r.status_code}: {r.text[:300]}")
            try:
                data = r.json()
            except ValueError as e:
                raise KevError(f"Kev at {self.base_url} sent non-JSON: {r.text[:200]}") from e
            answers = data.get("answers") if isinstance(data, dict) else None
            missing = sorted(set(questions) - set(answers or {}))
            if missing:
                raise KevError(f"Kev at {self.base_url} answered without {missing}")
            return data
        if isinstance(last, KevError):
            raise last
        self._down_at = time.monotonic()
        raise KevError(f"Kev service at {self.base_url} not reachable - start scripts/remote/serve_kev.py on the "
                       f"GPU host (docs/KEV.md) [{type(last).__name__}: {last}]") from last

    def noul_batch(self, state: str, questions: dict[str, str | dict[str, Any]]) -> tuple[dict[str, float], dict[str, Any]]:
        """p(yes) per question in one request. ``questions``: qid -> instruction text, or a dict with
        ``instructions`` (+ ``criteria``). -> ({qid: p}, info with model / usage / latency_ms)."""
        qs: dict[str, dict[str, Any]] = {}
        for qid, q in questions.items():
            q = {"instructions": q} if isinstance(q, str) else q
            qs[qid] = {"type": "noul", "instructions": str(q["instructions"]),
                       **({"criteria": q["criteria"]} if q.get("criteria") else {})}
        data = self.systemone(state, qs)
        out = {}
        for qid in qs:
            a = data["answers"][qid]
            p = a.get("noul") if isinstance(a, dict) else None
            if not isinstance(p, (int, float)) or not 0.0 <= float(p) <= 1.0:
                raise KevError(f"Kev answer for {qid!r} has no noul probability: {str(a)[:120]}")
            out[qid] = float(p)
        info = {"model": data.get("model"), "usage": data.get("usage"), "latency_ms": data.get("latency_ms")}
        return out, info

    # -- LLM interface ----------------------------------------------------------------------------

    def choice_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float] | None:
        """For the facts check: p(yes / no / unknown) of one fact prompt (see module doc)."""
        self._local.error = None
        try:
            return self._fact_probs(messages, choices)
        except Exception as e:
            self._local.error = e  # the facts check falls back to chat(), which then names this error
            raise

    def _fact_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float]:
        transcript, question, topic = parse_fact_prompt(messages)
        instructions = f"Topic: {topic}\n{question}" if topic and self.include_topic else question
        if self.fact_answer == "noul":
            p, _ = self.noul_batch(transcript, {"fact": instructions})
            dist = {"yes": p["fact"], "no": 1.0 - p["fact"], "unknown": 0.0}
        else:
            data = self.systemone(transcript, {"fact": {"type": "choice", "instructions": instructions,
                                                        "criteria": CHOICE_CRITERIA}})
            probs = (data["answers"]["fact"] or {}).get("probabilities") or {}
            dist = {k: float(probs.get(k) or 0.0) for k in CHOICE_CRITERIA}
            if not sum(dist.values()) > 0:
                raise KevError(f"Kev choice answer without probabilities: {str(data['answers']['fact'])[:120]}")
        return {c: dist.get(c, 0.0) for c in choices}

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512,
             n: int = 1, json_schema: dict | None = None, stop: list[str] | None = None) -> list[str]:
        err = getattr(self._local, "error", None)
        if err is not None:  # the facts check's sampling fallback after a failed probe: report the cause
            self._local.error = None
            raise KevError(f"{type(err).__name__}: {err}") from err
        raise NotImplementedError("Kev answers yes/no/choice questions only and writes no text: use it for the "
                                  "facts check with evidence: false, or for the questions check")
