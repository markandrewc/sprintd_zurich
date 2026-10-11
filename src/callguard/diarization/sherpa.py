"""sherpa-onnx speaker diarization: pyannote segmentation-3.0 + WeSpeaker ResNet34, ONNX only (no torch).

sherpa clusters embeddings of short analysis chunks. On the case calls (two similar synthetic voices)
that collapses most calls into a single speaker, so by default (``recluster``) the turns sherpa finds
are clustered again with one embedding per whole turn, which carries far more voice evidence. On six
case calls (clean and noisy) that reproduced the scripts' turn order exactly on all six; sherpa's own
labels did so on none.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from callguard.audio import SR, load_audio
from callguard.config import ROOT
from callguard.diarization import (FIRST_SPEAKER_CONFIDENCE, ROLE_METHODS, Turn, apply_turns, assign_roles,
                                   first_speaker, set_roles, speaker_name, speakers_of)
from callguard.plugins import Diarizer
from callguard.types import Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.diarization")

DEFAULT_SEGMENTATION = "models/diar/sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
DEFAULT_EMBEDDING = "models/diar/wespeaker_en_voxceleb_resnet34.onnx"

MIN_EMBED_S = 0.25  # shorter clips give NaN or pure-noise embeddings
MAX_EMBED_S = 12.0  # the middle of a long turn identifies the voice as well as all of it, for less CPU

RawTurn = tuple[float, float, int]


class SherpaDiarizer(Diarizer):
    """Fills ``speaker`` (``SPK0`` = first to talk) and ``role``; re-splits segments at speaker changes.

    ``num_speakers > 0`` fixes the number of speakers (2 for a phone call); ``<= 0`` lets sherpa
    decide with ``cluster_threshold`` and skips re-clustering. ``window_shift_ratio`` 0.5 is ~4x
    faster than sherpa's 0.1 default; with re-clustering the coarser chunk labels cost nothing.
    ``num_threads=0`` uses up to 8 cores. Models are built on first use, once per instance.

    ``roles: llm`` asks ``llm`` which speaker is the advisor; with ``role_swap_check`` it asks again
    with the labels rotated and only trusts an answer that names the same voice twice (see
    :func:`callguard.diarization.llm_advisor`), else the first speaker is the advisor.
    """

    def __init__(self, ctx: Context, segmentation_model: str = DEFAULT_SEGMENTATION,
                 embedding_model: str = DEFAULT_EMBEDDING, num_speakers: int = 2, cluster_threshold: float = 0.5,
                 min_duration_on: float = 0.3, min_duration_off: float = 0.5, resplit: bool = True,
                 roles: str = "llm", llm: str = "default", role_context_segments: int = 12,
                 role_swap_check: bool = True, recluster: bool = True, window_shift_ratio: float = 0.5,
                 num_threads: int = 0, provider: str = "cpu"):
        super().__init__(ctx, segmentation_model=segmentation_model, embedding_model=embedding_model,
                         num_speakers=num_speakers, cluster_threshold=cluster_threshold,
                         min_duration_on=min_duration_on, min_duration_off=min_duration_off, resplit=resplit,
                         roles=roles, llm=llm, role_context_segments=role_context_segments,
                         role_swap_check=role_swap_check, recluster=recluster,
                         window_shift_ratio=window_shift_ratio, num_threads=num_threads, provider=provider)
        if roles not in ROLE_METHODS:
            raise ValueError(f"roles {roles!r} unknown; expected one of {ROLE_METHODS}")
        if not 0 < float(window_shift_ratio) <= 1:
            raise ValueError(f"window_shift_ratio must be in (0, 1], got {window_shift_ratio}")
        self.segmentation_model = segmentation_model
        self.embedding_model = embedding_model
        self.num_speakers = int(num_speakers)
        self.cluster_threshold = float(cluster_threshold)
        self.min_duration_on = float(min_duration_on)
        self.min_duration_off = float(min_duration_off)
        self.resplit = bool(resplit)
        self.role_method = roles
        self.llm_name = llm
        self.role_context_segments = max(1, int(role_context_segments))
        self.role_swap_check = bool(role_swap_check)
        self.recluster = bool(recluster)
        self.window_shift_ratio = float(window_shift_ratio)
        self.num_threads = int(num_threads) if int(num_threads) > 0 else min(8, os.cpu_count() or 1)
        self.provider = provider
        self._lock = threading.Lock()
        self._sd: Any = None
        self._embedder: Any = None

    def cache_params(self) -> dict[str, Any]:
        """Roles depend on the LLM's model, not just on its config name. Threads only change speed."""
        params = super().cache_params()
        params.pop("num_threads", None)
        if self.role_method == "llm":
            try:
                params["role_llm"] = self.ctx.llm(self.llm_name).cache_params()
            except Exception as e:  # unconfigured LLM: roles will come from the fallback
                params["role_llm"] = repr(e)
        return params

    # -- models ---------------------------------------------------------------------------------

    @staticmethod
    def _model_path(path: str) -> str:
        p = Path(path).expanduser()
        p = p if p.is_absolute() else ROOT / p
        if not p.is_file():
            raise FileNotFoundError(
                f"diarization model {path!r} not found (looked at {p}). Put the sherpa-onnx pyannote "
                f"segmentation-3.0 and WeSpeaker ONNX models into models/diar/ or fix the diarizer config.")
        return str(p)

    def _build(self) -> tuple[Any, Any]:
        with self._lock:
            if self._sd is None:
                try:
                    import sherpa_onnx
                except ImportError as e:
                    raise ImportError("diarizer 'sherpa_onnx' needs sherpa-onnx: uv sync --extra diarize") from e
                t0 = time.time()
                emb_cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                    model=self._model_path(self.embedding_model), num_threads=self.num_threads,
                    provider=self.provider)
                cfg = sherpa_onnx.OfflineSpeakerDiarizationConfig(
                    segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                        pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                            model=self._model_path(self.segmentation_model),
                            window_shift_ratio=self.window_shift_ratio),
                        num_threads=self.num_threads, provider=self.provider),
                    embedding=emb_cfg,
                    clustering=sherpa_onnx.FastClusteringConfig(
                        num_clusters=self.num_speakers if self.num_speakers > 0 else -1,
                        threshold=self.cluster_threshold),
                    min_duration_on=self.min_duration_on, min_duration_off=self.min_duration_off)
                if not cfg.validate():
                    raise ValueError("sherpa-onnx rejected the diarization config (details on stderr)")
                sd = sherpa_onnx.OfflineSpeakerDiarization(cfg)
                self._embedder = sherpa_onnx.SpeakerEmbeddingExtractor(emb_cfg) if self.recluster else None
                self._sd = sd
                log.info("loaded sherpa-onnx diarization (%d threads) in %.1fs", self.num_threads, time.time() - t0)
            return self._sd, self._embedder

    # -- turns ----------------------------------------------------------------------------------

    def speaker_turns(self, audio: np.ndarray) -> tuple[list[Turn], dict[str, Any]]:
        """Speaker turns of 16 kHz mono ``audio`` plus info for the transcript meta."""
        sd, embedder = self._build()
        t0 = time.time()
        result = sd.process(np.ascontiguousarray(audio, dtype=np.float32))
        raw: list[RawTurn] = [(float(s.start), float(s.end), int(s.speaker))
                              for s in result.sort_by_start_time() if s.end > s.start]
        info: dict[str, Any] = {"clustering": "sherpa", "timings": {"sherpa": round(time.time() - t0, 2)}}
        labels: list[int | None] = [r[2] for r in raw]
        if embedder is not None and self.num_speakers > 0 and len(raw) > 1:
            t1 = time.time()
            try:
                labels, extra = recluster_turns(embedder, audio, raw, self.num_speakers)
                info.update(clustering="turn_embeddings", **extra)
            except Exception as e:
                log.warning("re-clustering diarization turns failed, keeping sherpa's labels: %r", e)
                info["recluster_error"] = repr(e)
            info["timings"]["recluster"] = round(time.time() - t1, 2)
        return name_turns(raw, labels), info

    # -- plugin API -----------------------------------------------------------------------------

    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript:
        t0 = time.time()
        out = transcript.model_copy(deep=True)
        info: dict[str, Any] = {"num_turns": 0, "speakers": [], "role_method": "none", "role_confidence": None,
                                "role_reason": "", "seconds": 0.0}
        try:
            if audio_path is None:
                raise ValueError("no audio: speaker diarization needs the recording")
            turns, extra = self.speaker_turns(load_audio(audio_path, sr=SR))
            info.update(extra)
            info["num_turns"] = len(turns)
            if not turns:
                raise ValueError("no speech turns found")
            info["speaker_seconds"] = speaker_seconds(turns)
            out.segments = apply_turns(out.segments, turns, resplit=self.resplit, min_run=self.min_duration_on)
        except Exception as e:
            log.warning("diarization of %s failed, transcript kept as is: %r", transcript.call_id, e)
            info["error"] = repr(e)
            info.update(self._fallback_roles(out))
        else:
            t1 = time.time()
            info.update(assign_roles(out.segments, self.role_method, llm=lambda: self.ctx.llm(self.llm_name),
                                     context_segments=self.role_context_segments,
                                     swap_check=self.role_swap_check))
            info.setdefault("timings", {})["roles"] = round(time.time() - t1, 2)
        info["speakers"] = speakers_of(out.segments)
        info["seconds"] = round(time.time() - t0, 2)
        out.meta["diarization"] = info
        log.info("diarized %s: %d turns, speakers %s, roles by %s (%.1fs)", transcript.call_id,
                 info["num_turns"], info["speakers"], info["role_method"], info["seconds"])
        return out

    def _fallback_roles(self, t: Transcript) -> dict[str, Any]:
        """After a failure only the cheap heuristic runs, and only on speakers that already exist
        without roles: roles that came with the transcript (reference ASR) are better than a guess."""
        info: dict[str, Any] = {"role_method": "none", "role_confidence": None, "roles": {}}
        speakers = speakers_of(t.segments)
        if self.role_method == "none":
            info["role_reason"] = "role assignment disabled"
        elif any(s.role != "unknown" for s in t.segments):
            info.update(role_method="transcript", role_reason="diarization failed; kept the transcript's roles")
        elif len(speakers) < 2:
            info["role_reason"] = "diarization failed; no speakers to assign roles to"
        else:
            advisor = first_speaker(t.segments) or ""
            info.update(role_method="first_speaker_advisor", roles=set_roles(t.segments, advisor),
                        role_confidence=FIRST_SPEAKER_CONFIDENCE,
                        role_reason=f"diarization failed; first speaker {advisor} taken as advisor")
        return info


# --------------------------------------------------------------------------------------------
# re-clustering (pure numpy apart from the embedder, so it can be tested without models)
# --------------------------------------------------------------------------------------------


def embed_turn(embedder: Any, audio: np.ndarray, start: float, end: float) -> np.ndarray | None:
    """Unit-length speaker embedding of ``audio[start:end]``, or None if the clip is too short."""
    a, b = max(0, int(start * SR)), min(len(audio), int(end * SR))
    if b - a < MIN_EMBED_S * SR:
        return None
    max_n = int(MAX_EMBED_S * SR)
    if b - a > max_n:
        a = (a + b) // 2 - max_n // 2
        b = a + max_n
    stream = embedder.create_stream()
    stream.accept_waveform(SR, np.ascontiguousarray(audio[a:b], dtype=np.float32))
    stream.input_finished()
    if not embedder.is_ready(stream):
        return None
    v = np.asarray(embedder.compute(stream), dtype=np.float64)
    norm = float(np.linalg.norm(v))
    if not np.isfinite(norm) or norm == 0.0:
        return None
    return v / norm


def recluster_turns(embedder: Any, audio: np.ndarray, raw: Sequence[RawTurn],
                    k: int) -> tuple[list[int | None], dict[str, Any]]:
    """New cluster label per turn (None = too short to embed; the caller drops it, its words go to
    the nearest remaining turn)."""
    embs, weights, keep = [], [], []
    for i, (start, end, _) in enumerate(raw):
        e = embed_turn(embedder, audio, start, end)
        if e is not None:
            embs.append(e)
            weights.append(min(end - start, MAX_EMBED_S))
            keep.append(i)
    if len(keep) < 2:
        raise ValueError(f"only {len(keep)} turn(s) long enough to embed")
    labels, margins = cluster_embeddings(np.stack(embs), np.asarray(weights), k)
    out: list[int | None] = [None] * len(raw)
    for i, lab in zip(keep, labels):
        out[i] = int(lab)
    return out, {"cluster_margin": round(float(np.median(margins)), 3),
                 "dropped_turns": len(raw) - len(keep)}


def cluster_embeddings(emb: np.ndarray, weights: np.ndarray, k: int, *, restarts: int = 10,
                       iters: int = 50, seed: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """Weighted spherical k-means (cosine) with seeded k-means++ restarts.

    Returns ``(labels, margins)``; margin = similarity to the own centroid minus the best other
    one, a per-turn measure of how clearly the voices separate. Unlike agglomerative clustering
    with a fixed k, k-means does not spend a cluster on one odd short turn, which is how chunk-level
    clustering ends up with a one-speaker call.
    """
    n = len(emb)
    k = max(1, min(int(k), n))
    w = np.clip(np.asarray(weights, dtype=np.float64), 1e-6, None)
    rng = np.random.default_rng(seed)
    best: tuple[float, np.ndarray, np.ndarray] | None = None
    for _ in range(max(1, restarts)):
        centers = _kmeanspp(emb, w, k, rng)
        for _ in range(iters):
            labels = np.argmax(emb @ centers.T, axis=1)
            new = centers.copy()
            for j in range(k):
                members = labels == j
                if members.any():
                    c = (w[members, None] * emb[members]).sum(axis=0)
                    norm = np.linalg.norm(c)
                    if norm > 0:
                        new[j] = c / norm
            if np.allclose(new, centers):
                break
            centers = new
        sims = emb @ centers.T
        labels = np.argmax(sims, axis=1)
        cost = float((w * (1.0 - sims[np.arange(n), labels])).sum())
        if best is None or cost < best[0] - 1e-12:
            best = (cost, labels, sims)
    assert best is not None
    _, labels, sims = best
    if k == 1:
        return labels, np.ones(n)
    top = np.sort(sims, axis=1)
    return labels, top[:, -1] - top[:, -2]


def _kmeanspp(emb: np.ndarray, w: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    idx = [int(rng.choice(len(emb), p=w / w.sum()))]
    for _ in range(1, k):
        dist = np.clip(1.0 - np.max(emb @ emb[idx].T, axis=1), 0.0, None)
        p = w * dist ** 2
        idx.append(int(rng.choice(len(emb), p=p / p.sum())) if p.sum() > 0 else int(rng.integers(len(emb))))
    return emb[idx].copy()


def name_turns(raw: Sequence[RawTurn], labels: Sequence[int | None]) -> list[Turn]:
    """``SPK0`` is whoever talks first, so names do not depend on cluster numbering."""
    names: dict[int, str] = {}
    out = []
    for (start, end, _), lab in zip(raw, labels):
        if lab is None:
            continue
        if lab not in names:
            names[lab] = speaker_name(len(names))
        out.append(Turn(round(start, 3), round(end, 3), names[lab]))
    return out


def speaker_seconds(turns: Sequence[Turn]) -> dict[str, float]:
    out: dict[str, float] = {}
    for t in turns:
        out[t.speaker] = out.get(t.speaker, 0.0) + (t.end - t.start)
    return {k: round(v, 1) for k, v in out.items()}
