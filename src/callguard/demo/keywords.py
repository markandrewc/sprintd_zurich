"""«Treffer vorher → nachher»: the effect of an edited keyword list on every processed call, before saving.

The configured keyword check runs in memory on each stored transcript (milliseconds per call) with the
edited family, its result replaces the stored one and the call is re-decided with the live knobs. Nothing
is written; saving (and persisting the new keyword results) is the page's job. No Streamlit here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from callguard.cache import stable_hash
from callguard.types import LABELS, CallResult, CheckResult, Family, Keyword
from callguard.ui import backend as be


@dataclass
class KeywordEffect:
    hits_before: int
    hits_after: int
    calls_before: int  # calls with at least one hit
    calls_after: int
    labels_before: dict[str, int]
    labels_after: dict[str, int]
    changed: list[tuple[str, str, str]] = field(default_factory=list)  # (call, label before, label after)
    family_hits_before: int = 0  # hits of the edited family only
    family_hits_after: int = 0


def keyword_check(engine: Any) -> Any:
    pipeline = getattr(engine, "pipeline", None)
    return next((c for c in (pipeline.checks if pipeline else []) if c.plugin_type == "keywords" and c.enabled), None)


def _hits(result: CallResult, check_name: str, family: str | None = None) -> int:
    cr = result.checks.get(check_name)
    if cr is None:
        return 0
    return sum(1 for f in cr.findings if not (f.detail or {}).get("negated") and (family is None or f.family == family))


_BASE = be._LRU(512)  # (check, call, transcript, keyword list) -> CheckResult of the unedited list


def merge_family(base: CheckResult, part: CheckResult, family_id: str) -> CheckResult:
    """``base`` with one family's findings and score replaced by those of ``part`` (a run on that family
    alone; the keyword check scores every family independently)."""
    findings = [f for f in base.findings if f.family != family_id] + [f for f in part.findings if f.family == family_id]
    scores = {k: v for k, v in base.family_scores.items() if k != family_id}
    if family_id in part.family_scores:
        scores[family_id] = part.family_scores[family_id]
    return base.model_copy(update={"findings": findings, "family_scores": scores})


def with_keywords(families: Sequence[Family], family_id: str, keywords: Sequence[Keyword]) -> list[Family]:
    return [f.model_copy(update={"keywords": list(keywords)}) if f.id == family_id else f for f in families]


def keyword_effect(engine: Any, results: Mapping[str, CallResult], decided: Mapping[str, be.Decided],
                   families: Sequence[Family], families_on: Sequence[str] | None, overrides: dict[str, Any] | None,
                   family_id: str, keywords: Sequence[Keyword] | None) -> KeywordEffect | None:
    """None when the profile has no keyword check (or no pipeline)."""
    check = keyword_check(engine)
    if check is None:
        return None
    new_fams = list(families) if keywords is None else with_keywords(families, family_id, keywords)
    on = set(families_on) if families_on is not None else {f.id for f in families}
    decide_fams = [f for f in new_fams if f.id in on]
    pipeline = engine.pipeline
    old_fams = [f for f in families if f.id in on]
    edited = None if keywords is None else next((f for f in new_fams if f.id == family_id), None)
    fam_key = stable_hash([f.model_dump(mode="json") for f in families])
    eff = KeywordEffect(0, 0, 0, 0, {lbl: 0 for lbl in LABELS}, {lbl: 0 for lbl in LABELS})
    for cid, r in results.items():
        # both sides in memory with the same check, so the difference is the edit alone (not an older list
        # the call was processed with). The unedited run is memoized; the edit reruns only its family.
        try:
            tr = be.check_view_transcript(pipeline, check, r)
            base = _BASE.get_or(stable_hash([check.name, cid, len(tr.segments), tr.duration, fam_key]),
                                lambda: check.run(tr, list(families)))
            cr = merge_family(base, check.run(tr, [edited]), family_id) if edited is not None else base
            old = r.model_copy(update={"checks": {**r.checks, check.name: base}})
            new = r.model_copy(update={"checks": {**r.checks, check.name: cr}})
            before = be.redecide(engine, old, overrides, old_fams).decision.label
            after = be.redecide(engine, new, overrides, decide_fams).decision.label
        except Exception:
            old = new = r
            before = after = decided[cid].decision.label if cid in decided else r.decision.label
        hb, ha = _hits(old, check.name), _hits(new, check.name)
        eff.hits_before += hb
        eff.hits_after += ha
        eff.family_hits_before += _hits(old, check.name, family_id)
        eff.family_hits_after += _hits(new, check.name, family_id)
        eff.calls_before += hb > 0
        eff.calls_after += ha > 0
        eff.labels_before[before] = eff.labels_before.get(before, 0) + 1
        eff.labels_after[after] = eff.labels_after.get(after, 0) + 1
        if after != before:
            eff.changed.append((cid, before, after))
    eff.changed.sort()
    return eff
