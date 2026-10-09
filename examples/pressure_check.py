"""Example plugin: a "pressure" check that flags urgency and secrecy phrases.

Pressure ("sofort", "niemandem sagen") often accompanies misconduct without naming it. It is weak
evidence on its own, so it reports low confidence and lets the fusion weigh it against the others.

Use it without touching the registry:
    checks:
      - name: pressure
        type: examples.pressure_check:PressureCheck
        weight: 0.2
        families: [trade, splitting]
and run with the project root on the import path:  PYTHONPATH=. uv run callguard run call.wav
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from callguard.plugins import Check
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

CUES = ["sofort", "dringend", "heute noch", "so schnell wie möglich", "niemandem sagen", "unter uns"]


class PressureCheck(Check):
    def __init__(self, ctx: Context, cues: list[str] | None = None, families: list[str] | None = None,
                 per_hit: float = 0.2, confidence: float = 0.3, *, name: str | None = None,
                 weight: float = 1.0, enabled: bool = True):
        # explicit params: a typo in the YAML raises; all of them go up so cache_params() (the cache key) sees them
        super().__init__(ctx, name=name, weight=weight, enabled=enabled, cues=cues, families=families,
                         per_hit=per_hit, confidence=confidence)
        self.patterns = [re.compile(rf"\b{re.escape(c)}\b", re.I) for c in (cues or CUES)]
        self.families = families
        self.per_hit = per_hit
        self.confidence = confidence

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        hits = [(seg, m.group(0)) for seg in transcript.segments for p in self.patterns
                if (m := p.search(seg.text))]
        result = CheckResult(check=self.name, type=self.plugin_type, meta={"hits": len(hits)})
        for fam in families:
            if not fam.can_alarm or (self.families and fam.id not in self.families):
                continue
            score = 1 - (1 - self.per_hit) ** len(hits)  # noisy-OR: more cues, more pressure
            result.family_scores[fam.id] = FamilyScore(
                score=round(score, 4), confidence=self.confidence,
                reason=f"{len(hits)} Druck-/Geheimhaltungssignal(e)" if hits else "Kein Druck erkennbar",
                segment_ids=[seg.id for seg, _ in hits])
            result.findings += [
                Finding(check=self.name, family=fam.id, score=self.per_hit, segment_ids=[seg.id],
                        start=seg.start, end=seg.end, reason=f"Druck: «{cue}»", detail={"cue": cue})
                for seg, cue in hits]
        return result
