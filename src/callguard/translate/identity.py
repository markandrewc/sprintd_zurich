"""Identity "translator": copies the text and only relabels the language. For tests and the offline
demo (``config/demo-views.yaml``), where it exercises the translated-view plumbing without a model."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from callguard.plugins import Translator
from callguard.translate import translated_copy
from callguard.types import Transcript

if TYPE_CHECKING:
    from callguard.context import Context


class IdentityTranslator(Translator):
    def __init__(self, ctx: "Context", **ignored: Any):
        super().__init__(ctx)
        self.ignored_params = ignored  # `llm: default` etc. from a swapped-out block change nothing

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        return translated_copy(transcript, {s.id: s.text for s in transcript.segments}, target_lang, "identity")
