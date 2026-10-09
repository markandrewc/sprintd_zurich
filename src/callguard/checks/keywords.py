"""Keyword check: the officer's keyword list, matched transparently against the transcript.

Cheap and fully explainable, but blind to context: "ich will vor der Meldung kaufen" and "kaufen
Sie nie vor der Meldung" both contain the phrase. So hits are weak evidence (score 0.35, confidence
0.4 by default), negated hits are marked and scored lower, and the LLM checks decide the context.

Matching rules (each one fixes a real false hit or miss):

* whole tokens only: "PIN" never matches "Pinnwand", "TAN" never matches "Tante";
* umlauts and ß folded, punctuation and «» quotes dropped (Swiss spellings vs. ASR output);
* short all-caps entries (PIN, TAN, BIN, WIR) must look like the acronym in the text, see
  :func:`textnorm.acronym_like`; ``case_sensitive`` keywords must match case exactly;
* the same letters split differently still match ("Kreditkarten-Nummer", "Insidertrading");
* ``fuzzy < 100`` adds rapidfuzz near-misses for phrases of >= 6 letters ("Quartalszahle"),
  multi-word phrases also against one extra token ("Prüfung zu umgehen").
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rapidfuzz import fuzz

from callguard.checks.textnorm import Token, acronym_like, is_acronym, segment_tokens, token_times, tokenize
from callguard.plugins import Check
from callguard.types import CheckResult, Family, FamilyScore, Finding, Keyword, Segment, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.keywords")

ROLES = ("advisor", "customer", "unknown")
NEGATION_CUES = ("nicht", "nichts", "nöd", "nid", "nit", "kein", "keine", "keinen", "keinem", "keiner",
                 "keines", "kei", "keini", "keis", "nie", "niemals", "nimmer", "ohne", "ohni", "nüt", "nüüt")
MAX_FAMILY_SCORE = 0.9  # keywords alone never make a family certain


@dataclass(frozen=True)
class _Phrase:
    family: Family
    keyword: Keyword
    text: str  # as written in the keyword list
    toks: tuple[str, ...]  # matching form: lower+folded, or folded with case for case-sensitive keywords
    acro: tuple[bool, ...]  # per token: short acronym that must look like one in the transcript
    case_sensitive: bool
    has_negation: bool  # "nicht öffentlich": its own "nicht" is part of the phrase, not a negation

    @property
    def plain(self) -> bool:
        """Eligible for compound and fuzzy matching (not case-bound)."""
        return not self.case_sensitive and not any(self.acro)


@dataclass
class _Hit:
    phrase: _Phrase
    first: int  # token indices into the segment's tokens, inclusive
    last: int
    fuzzy_score: float
    negated: bool = False
    cue: str | None = None

    def overlaps(self, other: _Hit) -> bool:
        return self.first <= other.last and other.first <= self.last


class KeywordCheck(Check):
    plugin_kind = "check"
    plugin_type = "keywords"

    def __init__(self, ctx: "Context", *, fuzzy: float = 90, hit_score: float = 0.35,
                 negated_score: float = 0.1, confidence: float = 0.4, absent_confidence: float = 0.25,
                 negation_window: int = 4, roles: list[str] | None = None,
                 negation_cues: list[str] | None = None, fuzzy_min_chars: int = 6,
                 name: str | None = None, weight: float = 1.0, enabled: bool = True):
        if not 0 <= float(fuzzy) <= 100:
            raise ValueError(f"fuzzy must be in 0..100, got {fuzzy}")
        for key, v in (("hit_score", hit_score), ("negated_score", negated_score),
                       ("confidence", confidence), ("absent_confidence", absent_confidence)):
            if not 0 <= float(v) <= 1:
                raise ValueError(f"{key} must be in 0..1, got {v}")
        if int(negation_window) < 0:
            raise ValueError(f"negation_window must be >= 0, got {negation_window}")
        if int(fuzzy_min_chars) < 1:
            raise ValueError(f"fuzzy_min_chars must be >= 1, got {fuzzy_min_chars}")
        bad = [r for r in roles or [] if r not in ROLES]
        if bad:
            raise ValueError(f"unknown roles {bad}; expected some of {ROLES}")
        super().__init__(ctx, name=name, weight=weight, enabled=enabled, fuzzy=fuzzy, hit_score=hit_score,
                         negated_score=negated_score, confidence=confidence,
                         absent_confidence=absent_confidence, negation_window=negation_window,
                         roles=roles, negation_cues=negation_cues, fuzzy_min_chars=fuzzy_min_chars)
        self.fuzzy = float(fuzzy)
        self.fuzzy_min_chars = int(fuzzy_min_chars)  # shorter phrases collide with too many words
        self.hit_score = float(hit_score)
        self.negated_score = float(negated_score)
        self.confidence = float(confidence)
        self.absent_confidence = float(absent_confidence)
        self.negation_window = int(negation_window)
        self.roles = list(roles) if roles else None
        cues = NEGATION_CUES if negation_cues is None else negation_cues
        self.negation_cues = frozenset(t.text for c in cues for t in tokenize(c))

    # -- matching -------------------------------------------------------------------------------

    def compile(self, families: list[Family]) -> tuple[list[_Phrase], list[str]]:
        """Keyword list -> match patterns. Returns patterns and warnings for unusable entries."""
        phrases: list[_Phrase] = []
        warnings: list[str] = []
        for fam in families:
            if not fam.enabled:
                continue
            for kw in fam.keywords:
                if not kw.enabled:
                    continue
                for text in kw.phrases:
                    toks = tokenize(text)
                    if not toks:
                        log.warning("keywords: %s phrase %r has no letters or digits, skipped", kw.id, text)
                        warnings.append(f"{kw.id}: phrase {text!r} has no letters or digits, skipped")
                        continue
                    cs = kw.case_sensitive
                    acro = tuple(not cs and is_acronym(t.raw) for t in toks)
                    phrases.append(_Phrase(
                        family=fam, keyword=kw, text=text, case_sensitive=cs, acro=acro,
                        toks=tuple(t.cased if cs else t.text for t in toks),
                        has_negation=any(t.text in self.negation_cues for t in toks),
                    ))
        return phrases, warnings

    def match(self, phrase: _Phrase, toks: list[Token]) -> list[_Hit]:
        n = len(phrase.toks)
        forms = [t.cased if phrase.case_sensitive else t.text for t in toks]
        hits: list[_Hit] = []
        for i in range(len(toks) - n + 1):
            if tuple(forms[i:i + n]) == phrase.toks and all(
                    not a or acronym_like(toks[i + k]) for k, a in enumerate(phrase.acro)):
                hits.append(_Hit(phrase, i, i + n - 1, 100.0))
        if not phrase.plain:
            return hits
        joined = "".join(phrase.toks)
        for w in (n - 1, n + 1):  # same letters, different word split
            if w < 1:
                continue
            for i in range(len(toks) - w + 1):
                if "".join(forms[i:i + w]) == joined:
                    hits.append(_Hit(phrase, i, i + w - 1, 100.0))
        if self.fuzzy < 100 and len(joined) >= self.fuzzy_min_chars:
            target = " ".join(phrase.toks)
            for w in ((n, n + 1) if n > 1 else (n,)):
                for i in range(len(toks) - w + 1):
                    s = fuzz.ratio(" ".join(forms[i:i + w]), target, score_cutoff=self.fuzzy)
                    if s and tuple(forms[i:i + w]) != phrase.toks:
                        hits.append(_Hit(phrase, i, i + w - 1, round(s, 1)))
        return hits

    def segment_hits(self, phrases: list[_Phrase], toks: list[Token]) -> list[_Hit]:
        """All hits in one segment: best non-overlapping span per keyword, negation resolved."""
        by_kw: dict[str, list[_Hit]] = {}
        for p in phrases:
            by_kw.setdefault(f"{p.family.id}/{p.keyword.id}", []).extend(self.match(p, toks))
        kept: list[_Hit] = []
        for cands in by_kw.values():
            chosen: list[_Hit] = []
            for h in sorted(cands, key=lambda h: (-h.fuzzy_score, h.last - h.first, h.first)):
                if not any(h.overlaps(c) for c in chosen):
                    chosen.append(h)
            kept.extend(chosen)
        kept.sort(key=lambda h: (h.first, h.phrase.keyword.id))
        # a cue inside a negation-bearing phrase ("nicht öffentlich") belongs to that phrase
        consumed = {i for h in kept if h.phrase.has_negation for i in range(h.first, h.last + 1)}
        for h in kept:
            for j in range(h.first - 1, max(-1, h.first - 1 - self.negation_window), -1):
                if toks[j + 1].boundary:
                    break
                if toks[j].text in self.negation_cues and j not in consumed:
                    h.negated, h.cue = True, toks[j].raw
                    break
        return kept

    # -- check ----------------------------------------------------------------------------------

    def select_segments(self, transcript: Transcript) -> tuple[list[Segment], str | None]:
        if not self.roles:
            return transcript.segments, None
        if all(s.role == "unknown" for s in transcript.segments):
            return transcript.segments, "no speaker roles in transcript: checked all segments"
        return [s for s in transcript.segments if s.role in self.roles], None

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        phrases, errors = self.compile(families)
        segments, note = self.select_segments(transcript)
        findings: list[Finding] = []
        best: dict[str, dict[str, float]] = {}  # family -> keyword -> best hit score
        for seg in segments:
            try:
                text, toks = segment_tokens(seg)
                hits = self.segment_hits(phrases, toks)
            except Exception as e:  # one odd segment must not cost the whole call its keyword evidence
                log.warning("keywords: segment %s skipped: %r", seg.id, e)
                errors.append(f"segment {seg.id}: {e!r}")
                continue
            for h in hits:
                f = self.finding(seg, text, toks, h)
                findings.append(f)
                kws = best.setdefault(h.phrase.family.id, {})
                kws[h.phrase.keyword.id] = max(kws.get(h.phrase.keyword.id, 0.0), f.score)

        result = CheckResult(check=self.name, type=self.plugin_type, meta={
            "segments_checked": len(segments), "phrases": len(phrases), "fuzzy": self.fuzzy})
        if note:
            result.meta["note"] = note
        if errors:
            result.meta["errors"] = errors
        no_keywords = []
        for fam in (f for f in families if f.enabled):
            if not any(k.enabled for k in fam.keywords):
                no_keywords.append(fam.id)  # no opinion, rather than a misleading "nothing found"
                continue
            fam_findings = [f for f in findings if f.family == fam.id]
            result.family_scores[fam.id] = self.family_score(fam_findings, best.get(fam.id, {}))
        if no_keywords:
            result.meta["families_without_keywords"] = no_keywords
        result.findings = findings
        return result

    def finding(self, seg: Segment, text: str, toks: list[Token], h: _Hit) -> Finding:
        kw, p = h.phrase.keyword, h.phrase
        matched = text[toks[h.first].start:toks[h.last].end]
        score = self.negated_score if h.negated else self.hit_score * h.fuzzy_score / 100
        reason = f"Stichwort {kw.id} «{p.text}» ({kw.label})"
        if h.fuzzy_score < 100:
            reason += f" – ähnlich: «{matched}» ({h.fuzzy_score:.0f} %)"
        if h.negated:
            reason += f" – verneint («{h.cue}»)"
        start, end = token_times(seg, toks, h.first, h.last)
        detail: dict[str, Any] = {"keyword_id": kw.id, "phrase": p.text, "matched_text": matched,
                                  "fuzzy_score": h.fuzzy_score, "negated": h.negated,
                                  "harmless": kw.harmless}
        if h.negated:
            detail["negation_cue"] = h.cue
        if not seg.words:
            detail["char_span"] = [toks[h.first].start, toks[h.last].end]  # offsets into seg.text
        return Finding(check=self.name, family=p.family.id, score=round(score, 4), segment_ids=[seg.id],
                       start=start, end=end, reason=reason, detail=detail)

    def family_score(self, findings: list[Finding], best: dict[str, float]) -> FamilyScore:
        """Noisy-OR over the best hit per keyword: independent cues add up, while repeating one
        word ("Quartalszahlen" five times in an explanation) does not inflate the score."""
        if not findings:
            return FamilyScore(score=0.0, confidence=self.absent_confidence, reason="Keine Stichwörter gefunden")
        score = min(MAX_FAMILY_SCORE, 1 - math.prod(1 - s for s in best.values()))
        parts = []
        for kid in best:
            kf = [f for f in findings if f.detail["keyword_id"] == kid]
            part = f"{kid} «{kf[0].detail['phrase']}»" + (f" ({len(kf)}×)" if len(kf) > 1 else "")
            if all(f.detail["negated"] for f in kf):
                part += " – verneint"
            parts.append(part)
        seg_ids = list(dict.fromkeys(s for f in findings for s in f.segment_ids))
        return FamilyScore(
            score=round(score, 4), confidence=self.confidence, reason="Stichwörter: " + ", ".join(parts),
            segment_ids=seg_ids,
            detail={"hits": len(findings), "negated_hits": sum(f.detail["negated"] for f in findings),
                    "keywords": {kid: sum(f.detail["keyword_id"] == kid for f in findings) for kid in best}},
        )
