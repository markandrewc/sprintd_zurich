"""Fusion plugins: all CheckResults of a call -> one Decision (alarm / review / no_alert).

Kept import-light on purpose: the UI and the eval re-run fusion thousands of times.
"""

from __future__ import annotations

from callguard.types import Decision


def top_family(decision: Decision, can_alarm: set[str] | None = None) -> str | None:
    """The family that drove the call score: ``Decision.top_family`` when the fusion set it, else (results
    written before that field existed) the highest-scoring family that may alarm (``can_alarm`` ids if
    known, else the family whose score equals the call score). ``None`` when nothing scored above zero."""
    if decision.top_family and (can_alarm is None or decision.top_family in can_alarm):
        return decision.top_family
    fams = list(decision.families.values())
    if can_alarm is not None:
        fams = [f for f in fams if f.family in can_alarm]
    else:
        exact = [f for f in fams if abs(f.score - decision.score) < 1e-6]
        fams = exact or fams
    if not fams:
        return None
    best = max(fams, key=lambda f: (f.score, -f.uncertainty))
    return best.family if best.score > 0 else None
