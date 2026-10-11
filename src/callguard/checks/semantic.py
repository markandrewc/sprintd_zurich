"""Semantic windows check (v2 plan §1b): find misconduct passages that contain no keyword at all.

Sliding windows of the call (``size`` segments, ``stride``) are embedded with a multilingual embedding
model and compared (cosine) with per-family "misconduct descriptions" built from criteria.yaml (the
policy and every ``alarm_when`` bullet; override per family with ``descriptions``). The ``top_k``
windows above ``min_similarity`` are candidates; with ``verify: true`` (default) each candidate is
scored by the same G-Eval passage prompt as ``keyword_context`` (``context: window|full``) and the family
score is the max verified score. With ``verify: false`` the score is the similarity mapped linearly
from [min_similarity, sim_ceil] to [0, 0.9] at low confidence (no LLM at all).

Embedders (``embedder: {type: ...}``):

* ``openai`` - an OpenAI-compatible ``/v1/embeddings`` endpoint (vLLM ``--task embed``, llama.cpp
  ``--embedding``, TEI with the OpenAI route). Default: bge-m3 on a second vLLM at :8001.
* ``sentence_transformers`` - in-process, lazy import. NOT in the app env (it pulls CUDA torch, ~3 GB):
  install it yourself; without it the check fails with a clear error.
* ``fake`` - deterministic hashed bag of words + char trigrams, for offline tests.
* ``"module:Class"`` - any class with ``__init__(**params)``, ``embed(texts) -> list[list[float]]``
  and ``identity() -> dict``.

Window embeddings are computed once per call (not per family); description embeddings once per process.
"""

from __future__ import annotations

import hashlib
import importlib
import logging
import math
import threading
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import TYPE_CHECKING, Any

import httpx

from callguard.cache import stable_hash
from callguard.checks.keyword_context import Anchor, WindowGEvalCheck
from callguard.checks.textnorm import normalize
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.semantic")

DEFAULT_EMBEDDER = {"type": "openai", "base_url": "http://127.0.0.1:8001/v1", "model": "BAAI/bge-m3"}
MAPPED_MAX = 0.9  # similarity alone never makes a family certain
MAPPED_CONFIDENCE = 0.3
_MEMO_CALLS = 64


# --------------------------------------------------------------------------------------------
# Embedding clients
# --------------------------------------------------------------------------------------------


class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def identity(self) -> dict[str, Any]:
        """What the vectors depend on (model id); part of the check's cache key via its params."""


class OpenAIEmbedder(Embedder):
    def __init__(self, *, base_url: str = DEFAULT_EMBEDDER["base_url"], model: str = DEFAULT_EMBEDDER["model"],
                 api_key: str | None = None, timeout: float = 60.0, batch_size: int = 64):
        self.base_url = str(base_url).rstrip("/")
        self.model = str(model)
        self.api_key = api_key if api_key not in (None, "", "none") else None
        self.timeout = float(timeout)
        self.batch_size = max(1, int(batch_size))
        self.requests = 0

    def identity(self) -> dict[str, Any]:
        return {"type": "openai", "model": self.model}

    def embed(self, texts: list[str]) -> list[list[float]]:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            self.requests += 1
            try:
                r = httpx.post(f"{self.base_url}/embeddings", json={"model": self.model, "input": batch},
                               headers=headers, timeout=self.timeout)
            except httpx.HTTPError as e:
                raise RuntimeError(f"embedding server {self.base_url} unreachable ({type(e).__name__}: {e}); "
                                   "serve an embedding model there (e.g. vLLM --task embed BAAI/bge-m3) "
                                   "or use embedder.type fake / sentence_transformers") from e
            if r.status_code != 200:
                raise RuntimeError(f"embedding server {self.base_url} answered {r.status_code}: {r.text[:200]}")
            data = sorted(r.json().get("data") or [], key=lambda d: d.get("index", 0))
            if len(data) != len(batch):
                raise RuntimeError(f"embedding server returned {len(data)} vectors for {len(batch)} texts")
            out += [list(map(float, d["embedding"])) for d in data]
        return out


class SentenceTransformerEmbedder(Embedder):
    def __init__(self, *, model: str = "BAAI/bge-m3", device: str = "cpu", batch_size: int = 16):
        self.model_name = str(model)
        self.device = str(device)
        self.batch_size = int(batch_size)
        self._model = None
        self._lock = threading.Lock()

    def identity(self) -> dict[str, Any]:
        return {"type": "sentence_transformers", "model": self.model_name}

    def embed(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            if self._model is None:
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as e:
                    raise RuntimeError(
                        "embedder type 'sentence_transformers' needs the sentence-transformers package, which "
                        "is not part of the app env (it pulls CUDA torch). Install it (uv pip install "
                        "sentence-transformers) or use embedder.type 'openai' with a served embedding model."
                    ) from e
                self._model = SentenceTransformer(self.model_name, device=self.device)
            vecs = self._model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]


class FakeEmbedder(Embedder):
    """Deterministic offline embedder: hashed word + char-trigram counts, L2-normalized. Texts sharing
    words (or word pieces: German compounds, dialect spellings) get similar vectors."""

    def __init__(self, *, dim: int = 512):
        self.dim = int(dim)

    def identity(self) -> dict[str, Any]:
        return {"type": "fake", "dim": self.dim, "version": 1}

    def _bucket(self, feat: str) -> int:
        return int.from_bytes(hashlib.md5(feat.encode()).digest()[:4], "little") % self.dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            v = [0.0] * self.dim
            for tok in normalize(text).split():
                if len(tok) < 3:
                    continue
                v[self._bucket("w:" + tok)] += 1.0
                padded = f"#{tok}#"
                for i in range(len(padded) - 2):
                    v[self._bucket("c:" + padded[i:i + 3])] += 0.3
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            out.append([x / norm for x in v])
        return out


EMBEDDERS: dict[str, type[Embedder]] = {
    "openai": OpenAIEmbedder, "openai_compat": OpenAIEmbedder,
    "sentence_transformers": SentenceTransformerEmbedder, "fake": FakeEmbedder,
}


def make_embedder(spec: dict[str, Any] | None) -> Embedder:
    spec = dict(spec or DEFAULT_EMBEDDER)
    kind = str(spec.pop("type", "openai"))
    if kind in EMBEDDERS:
        cls: type = EMBEDDERS[kind]
    elif ":" in kind:
        module, _, attr = kind.partition(":")
        cls = getattr(importlib.import_module(module), attr)
    else:
        raise ValueError(f"unknown embedder type {kind!r}; expected one of {sorted(EMBEDDERS)} or 'module:Class'")
    return cls(**spec)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# --------------------------------------------------------------------------------------------
# Check
# --------------------------------------------------------------------------------------------


class SemanticWindowCheck(WindowGEvalCheck):
    """Params (besides the G-Eval ones, see :class:`~callguard.checks.keyword_context.KeywordContextCheck`):
      embedder        {type: openai|sentence_transformers|fake|module:Class, model, base_url, ...}
      size, stride    window length and step in segments (default 4, 2)
      top_k           candidate windows per family (default 3, non-overlapping)
      min_similarity  cosine floor for a candidate (default 0.35; model dependent, tune on dev)
      sim_ceil        similarity mapped to the top score when verify is false (default 0.75)
      verify          G-Eval each candidate (default true) or use the mapped similarity
      descriptions    {family: [text, ...]} instead of policy + alarm_when
      query_prefix / passage_prefix   e.g. "query: " / "passage: " for multilingual-e5
      context         window | full (verification prompt, as in keyword_context)
      empty           skip (no candidate -> no opinion, default) | zero
    """

    plugin_kind = "check"
    plugin_type = "semantic_windows"

    def __init__(self, ctx: "Context", *, embedder: dict[str, Any] | None = None, size: int = 4, stride: int = 2,
                 top_k: int = 3, min_similarity: float = 0.35, sim_ceil: float = 0.75, verify: bool = True,
                 descriptions: dict[str, list[str]] | None = None, query_prefix: str = "",
                 passage_prefix: str = "", **params: Any):
        if int(size) < 1 or int(stride) < 1:
            raise ValueError(f"size and stride must be >= 1, got {size}, {stride}")
        if int(top_k) < 1:
            raise ValueError(f"top_k must be >= 1, got {top_k}")
        if not float(sim_ceil) > float(min_similarity):
            raise ValueError(f"sim_ceil ({sim_ceil}) must be > min_similarity ({min_similarity})")
        if descriptions is not None and not isinstance(descriptions, dict):
            raise ValueError("descriptions must map family id -> list of texts")
        super().__init__(ctx, **params)
        spec = dict(embedder or DEFAULT_EMBEDDER)
        self.embedder = make_embedder(spec)  # validates the spec now; no model is loaded yet
        self.params.update(embedder={k: v for k, v in spec.items() if k not in ("api_key", "timeout", "batch_size", "base_url")},
                           size=size, stride=stride, top_k=top_k, min_similarity=min_similarity,
                           sim_ceil=sim_ceil, verify=verify, descriptions=descriptions,
                           query_prefix=query_prefix, passage_prefix=passage_prefix)
        self.size, self.stride, self.top_k = int(size), int(stride), int(top_k)
        self.min_similarity, self.sim_ceil = float(min_similarity), float(sim_ceil)
        self.verify = bool(verify)
        self.descriptions = {k: [str(x) for x in v] for k, v in (descriptions or {}).items()}
        self.query_prefix, self.passage_prefix = str(query_prefix), str(passage_prefix)
        self._lock = threading.Lock()
        self._desc_memo: dict[str, list[float]] = {}
        self._call_memo: OrderedDict[str, tuple[list[list[str]], list[list[float]], int]] = OrderedDict()

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        key = super().cache_key(families)
        key["embedder"] = self.embedder.identity()
        return key

    # -- windows ----------------------------------------------------------------------------------

    def make_windows(self, transcript: Transcript) -> list[list[str]]:
        segs = transcript.segments
        if not segs:
            return []
        starts = list(range(0, max(1, len(segs) - self.size + 1), self.stride))
        if starts[-1] + self.size < len(segs):
            starts.append(len(segs) - self.size)  # cover the tail
        return [[s.id for s in segs[i:i + self.size]] for i in starts]

    def family_descriptions(self, f: Family) -> list[str]:
        if f.id in self.descriptions:
            return self.descriptions[f.id]
        out = [f"{f.label}: {f.policy.strip()}"] if f.policy.strip() else []
        out += [f"{f.label}: {b}" for b in f.alarm_when if str(b).strip()]
        return out or [f.label]

    def _embed_descriptions(self, texts: list[str]) -> list[list[float]]:
        missing = [t for t in texts if t not in self._desc_memo]
        if missing:
            vecs = self.embedder.embed([self.query_prefix + t for t in missing])
            with self._lock:
                self._desc_memo.update(zip(missing, vecs))
        return [self._desc_memo[t] for t in texts]

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        windows = self.make_windows(transcript)
        embed_calls = 0
        if windows and self.select_families(families):
            texts = [self.passage_prefix + " ".join(s.text.strip() for s in transcript.segments
                                                   if s.id in set(w)) for w in windows]
            try:
                vecs = self.embedder.embed(texts)
                embed_calls = 1
            except Exception as e:
                raise RuntimeError(f"{self.name}: embedding failed: {e}") from e
            with self._lock:
                self._call_memo[stable_hash(transcript.segments)] = (windows, vecs, embed_calls)
                while len(self._call_memo) > _MEMO_CALLS:
                    self._call_memo.popitem(last=False)
        result = super().run(transcript, families)
        result.meta["embedder"] = self.embedder.identity()
        result.meta["windows"] = len(windows)
        result.meta["embed_calls"] = embed_calls
        return result

    # -- per family -------------------------------------------------------------------------------

    def candidates(self, transcript: Transcript, family: Family) -> list[tuple[list[str], float, str]]:
        with self._lock:
            memo = self._call_memo.get(stable_hash(transcript.segments))
        if memo is None:
            return []
        windows, vecs, _ = memo
        descs = self.family_descriptions(family)
        dvecs = self._embed_descriptions(descs)
        scored = []
        for ids, v in zip(windows, vecs):
            sims = [cosine(v, d) for d in dvecs]
            j = max(range(len(sims)), key=sims.__getitem__)
            scored.append((ids, sims[j], descs[j]))
        scored.sort(key=lambda x: -x[1])
        chosen: list[tuple[list[str], float, str]] = []
        for ids, sim, desc in scored:
            if sim < self.min_similarity or len(chosen) >= self.top_k:
                break
            if any(len(set(ids) & set(c[0])) * 2 > len(ids) for c in chosen):
                continue  # mostly the same passage as a better candidate
            chosen.append((ids, sim, desc))
        return chosen

    def find_anchors(self, transcript: Transcript, family: Family) -> tuple[list[Anchor], dict[str, Any]]:
        cands = self.candidates(transcript, family)
        info: dict[str, Any] = {"candidates": [{"segment_ids": ids, "similarity": round(sim, 4)}
                                               for ids, sim, _ in cands]}
        if not cands:
            info["empty_reason"] = (f"Kein Abschnitt ähnelt der Beschreibung (Ähnlichkeit < "
                                    f"{self.min_similarity:.2f})")
        anchors = [Anchor(seg_ids=ids, core_ids=ids, priority=sim, source="semantic",
                          cues=[f"semantic similarity {sim:.2f} to: «{desc[:200]}»"],
                          detail={"similarity": round(sim, 4)})
                   for ids, sim, desc in cands]
        return anchors, info

    def mapped_score(self, sim: float) -> float:
        x = (sim - self.min_similarity) / (self.sim_ceil - self.min_similarity)
        return round(MAPPED_MAX * min(1.0, max(0.0, x)), 4)

    def score_anchors(self, counter, transcript: Transcript, rendered: str, family: Family,
                      anchors: list[Anchor], info: dict[str, Any]) -> tuple[FamilyScore, list[Finding]]:
        if self.verify:
            return super().score_anchors(counter, transcript, rendered, family, anchors, info)
        best = max(anchors, key=lambda a: a.priority)
        label = f"{best.seg_ids[0]}-{best.seg_ids[-1]}"
        fs = FamilyScore(score=self.mapped_score(best.priority), confidence=MAPPED_CONFIDENCE, verdict=None,
                         reason=f"{label}: {best.cues[0]}", segment_ids=best.seg_ids,
                         detail={**info, "llm_calls": 0, "verified": False})
        findings: list[Finding] = []
        for a in anchors:
            s = self.mapped_score(a.priority)
            if s >= self.evidence_min_score:
                findings += self.evidence_findings(transcript, family, a.seg_ids, s, lambda run, a=a: a.cues[0],
                                                   {"similarity": a.detail["similarity"], "verified": False})
        return fs, findings
