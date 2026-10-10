"""Offline stand-in for an LLM whose results are already cached: answers nothing, keys like the original.

Why: on one 12 GB GPU the Kev service (~8 GB) and vLLM cannot run together, but the Kev profiles still read
advisor/customer roles that the diarizer computed with ``llms.default`` (vLLM) earlier. The diarization cache key
contains that LLM's ``cache_params()``, and the experiment preflight demands every configured LLM be confirmed
live (audit F3). A ``pinned`` LLM declares the identity verbatim instead (``identity:`` = exactly the
``cache_params()`` the live client had, e.g. ``{type: openai_compat, model: Qwen/Qwen2.5-7B-Instruct-AWQ,
json_mode: json_schema, seed: null, extra_body: {}}``), so the cached roles are found without a server.

Any actual use (``chat`` / ``choice_probs``) raises :class:`PinnedLLMError`: a cache miss can never be answered
by a stand-in. The role assignment then falls back to the first speaker, records ``role_error`` in the
transcript meta and is not cached (tests/test_audit_fixes.py), so a wrong pin is loud in the logs
(``diarize <call>`` without ``(cached)``) and costs nothing permanent.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from callguard.plugins import LLM

if TYPE_CHECKING:
    from callguard.context import Context


class PinnedLLMError(RuntimeError):
    pass


class PinnedLLM(LLM):
    def __init__(self, ctx: "Context", identity: dict[str, Any], note: str = ""):
        if not isinstance(identity, dict) or not identity.get("type") or not identity.get("model"):
            raise ValueError("pinned LLM: `identity` must be the cache_params of the live client "
                             "(at least type and model)")
        super().__init__(ctx, identity=dict(identity), note=note)
        self.identity = dict(identity)
        self.note = str(note)

    @property
    def model_id(self) -> str:
        return str(self.identity["model"])

    def cache_params(self) -> dict[str, Any]:
        return dict(self.identity)

    def _refuse(self) -> PinnedLLMError:
        return PinnedLLMError(f"pinned LLM ({self.model_id}) is an offline stand-in for cached results and "
                              f"answers nothing; this request needs the live model "
                              f"{('(' + self.note + ')') if self.note else ''}".rstrip())

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512,
             n: int = 1, json_schema: dict | None = None, stop: list[str] | None = None) -> list[str]:
        raise self._refuse()

    def choice_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float] | None:
        raise self._refuse()
