"""Base classes for every plugin kind. Subclass one, register it, reference it from the YAML config.

Constructor convention: ``__init__(self, ctx: Context, **params)``. ``params`` are the YAML keys of the
plugin's config block (minus ``type``). Unknown params should raise, so typos in configs surface early;
the base classes accept and store anything, subclasses declare explicit keyword arguments.

``cache_params()`` must return everything that changes the plugin's output. The pipeline hashes it to
cache transcripts and check results, so changing a prompt or model invalidates exactly what it should.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.types import CallResult, CheckResult, Decision, Family, Transcript

if TYPE_CHECKING:
    from callguard.context import Context


class Plugin(ABC):
    plugin_kind: str = ""
    plugin_type: str = ""

    def __init__(self, ctx: "Context", **params: Any):
        self.ctx = ctx
        self.params = params

    def cache_params(self) -> dict[str, Any]:
        return {"type": self.plugin_type, **self.params}


class ASRBackend(Plugin):
    """Audio file -> Transcript with segment (ideally word) timestamps."""

    @abstractmethod
    def transcribe(self, audio_path: Path, call_id: str) -> Transcript: ...


class Diarizer(Plugin):
    """Fills ``Segment.speaker`` and ``Segment.role`` (advisor/customer); may re-split segments
    at speaker changes using word timestamps. Must return a Transcript (may be the same object)."""

    @abstractmethod
    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript: ...


class Check(Plugin):
    """One kind of fraud check. Scores every enabled family it understands.

    ``name`` is the instance name from the config (several instances of one type may run, e.g.
    two LLM judges with different models), ``weight`` is read by the fusion.
    """

    def __init__(self, ctx: "Context", *, name: str | None = None, weight: float = 1.0,
                 enabled: bool = True, **params: Any):
        super().__init__(ctx, **params)
        self.name = name or self.plugin_type
        self.weight = weight
        self.enabled = enabled

    def cache_params(self) -> dict[str, Any]:
        # weight and enabled only affect fusion, not the check output
        return {"type": self.plugin_type, **self.params}

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        """Everything the output depends on besides the transcript. LLM checks override this to
        depend only on the family criteria (not the keyword list) and on the LLM's model id."""
        return {"params": self.cache_params(), "families": [f.model_dump(mode="json") for f in families]}

    @abstractmethod
    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult: ...


class Fusion(Plugin):
    """Combines all CheckResults into one Decision. Must be cheap and pure: the UI re-runs it on every
    threshold slider move without touching ASR or LLMs. ``overrides`` carries UI knobs such as
    ``threshold`` and per-check ``weights``."""

    @abstractmethod
    def decide(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
               overrides: dict[str, Any] | None = None) -> Decision: ...


class LLM(Plugin):
    """Minimal chat interface so checks don't care whether the model is vLLM on a GPU, a llama.cpp
    server on a laptop or an in-process model."""

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512,
             n: int = 1, json_schema: dict | None = None, stop: list[str] | None = None) -> list[str]:
        """Return ``n`` completions. If ``json_schema`` is given the backend should constrain output
        to it when it can (vLLM guided decoding, llama.cpp grammar); callers still validate."""

    def choice_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float] | None:
        """Probability of each single-token answer in ``choices`` as the next token (used by G-Eval).
        Return None if the backend exposes no logprobs; callers then fall back to sampling."""
        return None

    @property
    def model_id(self) -> str:
        return str(self.params.get("model", self.plugin_type))


class Sink(Plugin):
    """Receives every finished CallResult: write files, notify, post to the Outcept trigger API..."""

    def __init__(self, ctx: "Context", *, enabled: bool = True, **params: Any):
        super().__init__(ctx, **params)
        self.enabled = enabled

    @abstractmethod
    def emit(self, result: CallResult) -> None: ...
