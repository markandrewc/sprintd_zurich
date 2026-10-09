"""In-process llama.cpp (llama-cpp-python): no server to start, same chat/choice_probs semantics as
the OpenAI-compatible client. Handy for a single laptop run or CI; a shared server is still better
when several processes (UI + batch) need the model, since each in-process copy costs its own RAM.
"""

from __future__ import annotations

import logging
import random
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.config import ROOT
from callguard.llm import choice_distribution, request_seeds, with_schema_instruction
from callguard.llm.jsonutil import strip_reasoning
from callguard.plugins import LLM

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.llm")


class LlamaCppLLM(LLM):
    def __init__(self, ctx: "Context", model_path: str, n_ctx: int = 8192, n_threads: int | None = None,
                 chat_format: str | None = None, verbose: bool = False, n_gpu_layers: int = 0,
                 seed: int | None = None):
        super().__init__(ctx, model_path=model_path, n_ctx=n_ctx, n_threads=n_threads,
                         chat_format=chat_format, verbose=verbose, n_gpu_layers=n_gpu_layers, seed=seed)
        p = Path(model_path)
        self.model_path = p if p.is_absolute() else ROOT / p
        self.n_ctx = int(n_ctx)
        self.n_threads = n_threads
        self.chat_format = chat_format
        self.verbose = verbose
        self.n_gpu_layers = int(n_gpu_layers)
        self.seed = seed
        self._llm: Any = None
        self._lock = threading.RLock()  # a Llama instance is not thread-safe
        self._rng = random.Random()
        self._logprobs_ok: bool | None = None
        self._schema_ok = True  # grammar conversion of the schema works

    @property
    def model_id(self) -> str:
        return self.model_path.stem

    def cache_params(self) -> dict[str, Any]:
        return {"type": self.plugin_type, "model": self.model_path.name, "chat_format": self.chat_format,
                "seed": self.seed}

    def _load(self) -> Any:
        with self._lock:
            if self._llm is None:
                try:
                    from llama_cpp import Llama
                except ImportError as e:
                    raise RuntimeError("llama-cpp-python is not installed: `uv sync --extra llm-local`, "
                                       "or use the openai_compat LLM against a server") from e
                if not self.model_path.exists():
                    raise RuntimeError(f"GGUF model not found: {self.model_path} "
                                       "(download it into models/llm/ or fix llms.<name>.model_path)")
                log.info("loading %s (n_ctx=%d)", self.model_path.name, self.n_ctx)
                self._llm = Llama(model_path=str(self.model_path), n_ctx=self.n_ctx, n_threads=self.n_threads,
                                  n_gpu_layers=self.n_gpu_layers, chat_format=self.chat_format,
                                  verbose=self.verbose)
            return self._llm

    def _create(self, **kw: Any) -> dict[str, Any]:
        llm = self._load()
        try:
            with self._lock:
                return llm.create_chat_completion(**kw)
        except ValueError as e:
            if "context window" in str(e) or "exceed" in str(e):
                raise RuntimeError(f"llama.cpp: {e} (n_ctx={self.n_ctx}; raise n_ctx in the llm config)") from e
            raise

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512,
             n: int = 1, json_schema: dict | None = None, stop: list[str] | None = None) -> list[str]:
        out = []
        for seed in request_seeds(max(1, int(n)), temperature, self.seed, self._rng):
            kw: dict[str, Any] = dict(messages=messages, temperature=float(temperature),
                                      max_tokens=int(max_tokens), stop=list(stop or []), seed=seed)
            if json_schema and self._schema_ok:
                try:
                    r = self._create(**kw, response_format={"type": "json_object", "schema": json_schema})
                    out.append(strip_reasoning(_content(r)))
                    continue
                except RuntimeError:
                    raise
                except Exception as e:  # schema -> grammar conversion failed: keep JSON mode, drop schema
                    log.warning("llama.cpp could not use the JSON schema as grammar (%r); "
                                "putting the schema into the prompt from now on", e)
                    self._schema_ok = False
            if json_schema:
                kw["messages"] = with_schema_instruction(messages, json_schema)
                kw["response_format"] = {"type": "json_object"}
            out.append(strip_reasoning(_content(self._create(**kw))))
        return out

    def choice_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float] | None:
        """Next-token distribution from the raw logits, captured by a logits processor.

        llama-cpp-python's own ``logprobs`` needs ``logits_all=True``, which keeps an
        n_ctx x vocab float matrix (1.2 GB at n_ctx=2048 for Qwen2.5); the processor sees exactly
        one row for the single token generated here.
        """
        if self._logprobs_ok is False or not choices:
            return None
        import numpy as np
        from llama_cpp import LogitsProcessorList

        llm = self._load()
        captured: list[np.ndarray] = []

        def grab(_input_ids: Any, logits: Any) -> Any:
            if not captured:
                captured.append(np.array(logits, dtype=np.float64))
            return logits

        with self._lock:
            self._create(messages=messages, max_tokens=1, temperature=0.0,
                         logits_processor=LogitsProcessorList([grab]))
            if not captured or captured[0].shape != (llm.n_vocab(),):
                log.warning("llama.cpp logits capture failed; choice_probs returns None from now on")
                self._logprobs_ok = False
                return None
            logits = captured[0]
            m = float(logits.max())
            logprobs = logits - (m + np.log(np.exp(logits - m).sum()))
            ids = {int(i) for i in np.argpartition(-logprobs, 20)[:20]}
            for c in choices:  # also the exact answer tokens, even when outside the top 20
                for variant in (c, " " + c):
                    toks = llm.tokenize(variant.encode("utf-8"), add_bos=False, special=False)
                    if len(toks) == 1:
                        ids.add(int(toks[0]))
            pairs = [(llm.detokenize([i]).decode("utf-8", errors="ignore"), float(logprobs[i])) for i in ids]
        self._logprobs_ok = True
        return choice_distribution(pairs, choices, min_mass=1e-6)


def _content(response: dict[str, Any]) -> str:
    try:
        return response["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError):
        return ""
