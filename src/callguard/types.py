"""Core data model shared by every stage and plugin.

Flow:  audio -> Transcript (ASR) -> Transcript with speaker/role (Diarizer)
       -> CheckResult per check (Check plugins) -> Decision (Fusion) -> CallResult (+ snippets, sinks)

Everything is a pydantic model so it can be cached as JSON, shown in the UI and diffed between runs.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Role = Literal["advisor", "customer", "unknown"]
Label = Literal["alarm", "review", "no_alert"]
Verdict = Literal["present", "absent", "undetermined"]

LABELS: tuple[Label, ...] = ("alarm", "review", "no_alert")


# --------------------------------------------------------------------------------------------
# Transcript
# --------------------------------------------------------------------------------------------


class Word(BaseModel):
    start: float
    end: float
    text: str
    prob: float | None = None


class Segment(BaseModel):
    """One utterance. After diarization ideally one speaker turn."""

    id: str  # stable id inside the call, e.g. "S007"
    start: float  # seconds
    end: float
    text: str
    speaker: str | None = None  # diarization cluster, e.g. "SPK0"
    role: Role = "unknown"  # advisor / customer
    confidence: float | None = None  # 0..1, ASR confidence for this segment
    words: list[Word] = Field(default_factory=list)


class Transcript(BaseModel):
    call_id: str
    audio_path: str | None = None
    duration: float | None = None
    language: str | None = None
    segments: list[Segment] = Field(default_factory=list)
    asr_backend: str = ""  # provenance, e.g. "faster_whisper:whisper-turbo-gsw-ct2-int8"
    meta: dict[str, Any] = Field(default_factory=dict)
    # Which rendering of the call this is (``config.views``): "main" in single-view (v1) configs.
    # ``lang`` is the view's configured language (gsw / de / en; None = unspecified, v1); ``language``
    # above is what the ASR reported. Neither enters cache keys (those hash the segments only).
    view: str = "main"
    lang: str | None = None

    def segment(self, seg_id: str) -> Segment | None:
        return next((s for s in self.segments if s.id == seg_id), None)

    def span(self, seg_ids: list[str]) -> tuple[float, float] | None:
        segs = [s for s in self.segments if s.id in set(seg_ids)]
        if not segs:
            return None
        return min(s.start for s in segs), max(s.end for s in segs)

    def text(self) -> str:
        return " ".join(s.text.strip() for s in self.segments)

    def render(self, *, roles: bool = True, times: bool = True) -> str:
        """Line-per-segment rendering used in LLM prompts and the UI.

        Example line: ``[S007 01:23 advisor] Das cha e Reservation sii.``
        """
        lines = []
        for s in self.segments:
            tag = [s.id]
            if times:
                tag.append(fmt_ts(s.start))
            if roles and (s.role != "unknown" or s.speaker):
                tag.append(s.role if s.role != "unknown" else (s.speaker or ""))
            lines.append(f"[{' '.join(tag)}] {s.text.strip()}")
        return "\n".join(lines)


def fmt_ts(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:02d}:{s:02d}"


# --------------------------------------------------------------------------------------------
# Configuration objects the officer edits (keyword families + criteria)
# --------------------------------------------------------------------------------------------


class Keyword(BaseModel):
    id: str
    label: str
    de: list[str] = Field(default_factory=list)  # Standard German surface forms
    gsw: list[str] = Field(default_factory=list)  # Swiss German spellings
    harmless: str | None = None  # when a hit is NOT suspicious (shown to LLM checks, too)
    enabled: bool = True
    case_sensitive: bool = False

    en: list[str] = Field(default_factory=list)  # English forms, matched on English views

    @property
    def phrases(self) -> list[str]:
        return list(dict.fromkeys([*self.de, *self.gsw]))

    def forms(self, lang: str | None = None) -> list[str]:
        """Phrases to match on a view of language ``lang``. German and Swiss German views both match
        de + gsw forms (ASR output mixes them); English views match only the English forms; unknown /
        unset languages (v1 single view) behave like German."""
        if lang == "en":
            return list(dict.fromkeys(self.en))
        if lang == "gsw":
            return list(dict.fromkeys([*self.gsw, *self.de]))
        return self.phrases


class Family(BaseModel):
    """A kind of misconduct we check for (e.g. insider trading). The unit every check scores."""

    id: str  # "trade", "access", ...
    label: str  # human label shown in the UI
    task: str | None = None  # short machine name from the keyword list
    policy: str = ""  # one-paragraph rule: when is this an alarm
    alarm_when: list[str] = Field(default_factory=list)
    not_alarm_when: list[str] = Field(default_factory=list)
    review_when: list[str] = Field(default_factory=list)
    keywords: list[Keyword] = Field(default_factory=list)
    enabled: bool = True
    can_alarm: bool = True  # e.g. "numbers" only classifies objects and never alarms by itself


# --------------------------------------------------------------------------------------------
# Check output
# --------------------------------------------------------------------------------------------


class Finding(BaseModel):
    """One piece of evidence a check found, pinned to a passage of the call."""

    check: str  # check instance name (from config)
    family: str
    score: float  # 0..1: how strongly this passage indicates the family's misconduct
    segment_ids: list[str] = Field(default_factory=list)
    start: float | None = None
    end: float | None = None
    reason: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)  # keyword id, matched phrase, raw LLM output...


class FamilyScore(BaseModel):
    """A check's call-level opinion about one family."""

    score: float  # 0..1 risk that the misconduct is present in this call
    confidence: float = 1.0  # 0..1 how sure the check is about its own score
    verdict: Verdict | None = None
    reason: str = ""
    segment_ids: list[str] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


class CheckResult(BaseModel):
    check: str  # instance name
    type: str  # plugin type
    family_scores: dict[str, FamilyScore] = Field(default_factory=dict)
    findings: list[Finding] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)  # model, latency, errors...
    view: str | None = None  # transcript view the check read (None: results from before views)


# --------------------------------------------------------------------------------------------
# Decision
# --------------------------------------------------------------------------------------------


class FusedFamily(BaseModel):
    family: str
    label: str  # human label
    score: float
    uncertainty: float  # 0..1
    per_check: dict[str, float] = Field(default_factory=dict)  # check -> score that went in
    verdicts: dict[str, Verdict | None] = Field(default_factory=dict)
    reason: str = ""


class Passage(BaseModel):
    """What the compliance officer listens to: a short stretch of audio plus why."""

    family: str
    family_label: str = ""
    start: float
    end: float
    segment_ids: list[str] = Field(default_factory=list)
    score: float
    reasons: list[str] = Field(default_factory=list)
    checks: list[str] = Field(default_factory=list)
    text: str = ""
    texts: dict[str, str] = Field(default_factory=dict)  # view -> what that view says in [start, end]
    snippet_path: str | None = None
    # lowest ASR confidence of the passage's segments (None: the ASR reports none) and whether it is below
    # ``snippets.misheard_below``: "möglicherweise verhört — bitte anhören" (callguard.misheard)
    asr_confidence: float | None = None
    misheard: bool = False


class Decision(BaseModel):
    label: Label
    score: float  # call-level risk 0..1
    uncertainty: float  # 0..1
    threshold: float
    families: dict[str, FusedFamily] = Field(default_factory=dict)
    passages: list[Passage] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)  # human-readable explanation of the label
    top_family: str | None = None  # family that set the call score (None: nothing scored)


class CallResult(BaseModel):
    call_id: str
    audio_path: str | None = None
    transcript: Transcript  # the primary view
    views: dict[str, Transcript] = Field(default_factory=dict)  # every computed view (incl. primary)
    # DISPLAY-ONLY renderings (config ``display_views``, e.g. an automatic Swiss German transcript): for people
    # to read, never read by checks or fusion (kept out of ``views`` on purpose, so no code path can mix them in)
    display_views: dict[str, Transcript] = Field(default_factory=dict)
    checks: dict[str, CheckResult] = Field(default_factory=dict)
    decision: Decision
    timings: dict[str, float] = Field(default_factory=dict)
    config_name: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)  # sink delivery info, stage warnings, provenance

    def all_views(self) -> dict[str, Transcript]:
        """Every view of the call; results from before views have only the primary transcript."""
        return self.views or {self.transcript.view: self.transcript}

    def view(self, name: str | None) -> Transcript:
        """Transcript of view ``name`` (the primary one for None or an unknown name)."""
        return self.all_views().get(name or "", self.transcript) if name else self.transcript
