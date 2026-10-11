"""No speaker separation: the transcript passes through untouched."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.diarization import drop_inherited
from callguard.plugins import Diarizer
from callguard.types import Transcript

if TYPE_CHECKING:
    from callguard.context import Context


class NoDiarizer(Diarizer):
    """For the reference (oracle) ASR, whose segments already carry the script's speakers and roles,
    and for setups without the diarization models. Checks then see roles as they came from ASR.

    Params of other diarizer types are accepted and ignored (see :func:`drop_inherited`), so they
    stay out of ``cache_params``.
    """

    def __init__(self, ctx: Context, **inherited: Any):
        self.ignored_params = drop_inherited("none", inherited)
        super().__init__(ctx)

    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript:
        return transcript
