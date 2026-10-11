"""Explaining a decision to the compliance officer, in plain German. Pure (no Streamlit), unit-tested.

* :func:`review_causes`   why a call went to *Prüfen* (score in band / checks disagree / LLM undetermined /
  failed check), derived from the numbers, not parsed from the fusion's reason strings, so it stays
  right when the fusion plugin changes its wording.
* :func:`why_not_alarm`   for keyword-heavy calls that did not alarm: the per-check scores vs the
  threshold, the strongest counter-evidence, the keyword hits with their ``harmless`` notes and the
  ``not_alarm_when`` rule of ``criteria.yaml`` that best matches the counter-evidence.
* :func:`passage_criterion` the ``alarm_when`` rule a passage matches best (or the policy).
* :func:`timeline_events` every piece of evidence pinned to call time, for the evidence timeline.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from callguard.types import CallResult, Decision, Family, Passage, Transcript, fmt_ts

LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
VERDICT_DE = {"present": "liegt vor", "absent": "liegt nicht vor", "undetermined": "unbestimmt", None: "–", "": "–"}
VIEW_LANG_DE = {"gsw": "Schweizerdeutsch", "de": "Deutsch", "en": "Englisch"}
RULE_CHECK_TYPES = frozenset({"keywords", "patterns"})


def short(label: str) -> str:
    return (label or "").split(" (")[0].strip() or label


def view_title(name: str, transcript: Transcript | None = None) -> str:
    """'main' + lang gsw -> 'Schweizerdeutsch (main)'; 'en_from_de' -> 'Englisch (en_from_de)'."""
    lang = (transcript.lang if transcript is not None else None) or (
        name if name in VIEW_LANG_DE else name.split("_")[0] if name.split("_")[0] in VIEW_LANG_DE else None)
    if lang in VIEW_LANG_DE:
        return VIEW_LANG_DE[lang] if name == lang else f"{VIEW_LANG_DE[lang]} ({name})"
    return "Transkript" if name == "main" else name


# --------------------------------------------------------------------------------------------
# text matching against the criteria (cheap, transparent: shared word stems)
# --------------------------------------------------------------------------------------------

_STOP = {
    "aber", "alle", "also", "auch", "bereits", "dass", "dann", "denn", "diese", "dieser", "dieses", "doch", "eine",
    "einem", "einen", "einer", "eines", "etwas", "für", "hier", "ihre", "ihren", "kein", "keine", "keinen", "mehr",
    "nach", "noch", "nicht", "nur", "oder", "ohne", "schon", "sein", "seine", "sich", "sind", "unter", "über",
    "wird", "werden", "wenn", "wird", "wurde", "zum", "zur", "this", "that", "with", "from", "have", "the", "and",
    "kunde", "kundin", "beratung", "person", "anruf", "gespräch", "call", "customer", "advisor", "wert",
    "ausdrücklich", "begründet", "begründen", "tatsächlich", "konkret", "konkrete", "konkreten", "eigene",
    "eigenen", "eigener", "einen", "werden", "wird", "dabei", "trotzdem", "später",
}


def stems(text: str) -> set[str]:
    words = re.findall(r"[a-zäöüß]+", (text or "").lower())
    return {w[:6] for w in words if len(w) >= 4 and w not in _STOP}


@dataclass
class RuleMatch:
    rule: str
    score: float  # share of the rule's word stems found in the evidence (0..1)
    shared: list[str] = field(default_factory=list)


def best_rule(evidence: Iterable[str], rules: Sequence[str], min_score: float = 0.2,
              min_shared: int = 2) -> RuleMatch | None:
    """The rule sharing the most word stems with the evidence texts (ties: the larger share of the rule);
    None below the bar. A transparent hint for the officer, not a classifier."""
    ev = set().union(*(stems(t) for t in evidence)) if evidence else set()
    best: RuleMatch | None = None
    for rule in rules:
        rs = stems(rule)
        if not rs:
            continue
        shared = sorted(rs & ev)
        score = len(shared) / len(rs)
        if len(shared) >= min_shared and score >= min_score and (
                best is None or (len(shared), score) > (len(best.shared), best.score)):
            best = RuleMatch(rule, round(score, 3), shared)
    return best


def _first_sentence(text: str, limit: int = 220) -> str:
    s = re.split(r"(?<=[.!?])\s", (text or "").strip(), maxsplit=1)[0]
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"


@dataclass
class Criterion:
    text: str
    kind: str  # "alarm_when" | "review_when" | "policy" | "rule" (fact-sheet policy table)
    score: float | None = None  # match strength for alarm_when/review_when


def _fact_rule(result: CallResult, family: str) -> str | None:
    for cr in result.checks.values():
        fs = cr.family_scores.get(family)
        rule = (fs.detail or {}).get("rule") if fs is not None else None
        if isinstance(rule, dict) and (rule.get("text") or rule.get("when")):
            return str(rule.get("text") or rule.get("when"))
    return None


def passage_criterion(passage: Passage, family: Family | None, result: CallResult | None = None) -> Criterion | None:
    """The criterion a passage matched: the fact-sheet rule if a fact check decided it, else the
    ``alarm_when`` / ``review_when`` line sharing most words with the passage's reasons and text, else the
    family policy (first sentence)."""
    if result is not None:
        rule = _fact_rule(result, passage.family)
        if rule:
            return Criterion(rule, "rule")
    if family is None:
        return None
    evidence = [*passage.reasons, passage.text]
    m = best_rule(evidence, family.alarm_when, min_score=0.15)
    if m:
        return Criterion(m.rule, "alarm_when", m.score)
    m = best_rule(evidence, family.review_when, min_score=0.15)
    if m:
        return Criterion(m.rule, "review_when", m.score)
    if family.policy:
        return Criterion(_first_sentence(family.policy), "policy")
    return None


# --------------------------------------------------------------------------------------------
# why "Prüfen"
# --------------------------------------------------------------------------------------------


@dataclass
class Cause:
    code: str  # band | disagree | low_confidence | undetermined | failed | no_checks | uncertain
    title: str  # short German heading
    text: str  # one plain German sentence with the numbers


def _floor(t: float, band: float) -> float:
    return round(t - band, 6)


def review_causes(result: CallResult, decision: Decision, *, threshold: float, review_band: float,
                  max_uncertainty: float, min_score_for_review: float = 0.25,
                  can_alarm: set[str] | None = None, weights: Mapping[str, float] | None = None) -> list[Cause]:
    """Why the call is (or nearly is) a human's job. Empty for clear alarms / clear no-alerts without
    failed checks. ``threshold`` is the decision's own (per-family thresholds may shift it)."""
    out: list[Cause] = []
    failed = {n: str(cr.meta.get("error")) for n, cr in result.checks.items() if cr.meta.get("error")}
    for name, err in failed.items():
        out.append(Cause("failed", "Prüfung ausgefallen",
                         f"Die Prüfung «{name}» ist bei der Verarbeitung ausgefallen ({err[:120]}); "
                         "ihr Urteil fehlt in der Bewertung."))
    if not decision.families:
        if decision.label == "review":
            out.append(Cause("no_checks", "Keine Prüfung verwertbar",
                             "Keine Prüfung lieferte ein verwertbares Ergebnis; ein Mensch muss den Anruf beurteilen."))
        return out

    fams = [f for f in decision.families.values() if can_alarm is None or f.family in can_alarm]
    top = (decision.families.get(decision.top_family) if decision.top_family else None) or max(
        fams, key=lambda f: f.score, default=None)
    if top is None:
        return out
    name = short(top.label)
    s, u, t = top.score, top.uncertainty, threshold
    floor = _floor(t, review_band)

    if decision.label == "review" or (decision.label != "alarm" and failed):
        if s >= t and u > max_uncertainty:
            out.append(Cause("uncertain", "Schwelle erreicht, aber unsicher",
                             f"«{name}» erreicht mit {s:.2f} die Alarmschwelle {t:.2f}, die Unsicherheit "
                             f"{u:.2f} liegt aber über dem Maximum {max_uncertainty:.2f}."))
        elif floor <= s < t:
            out.append(Cause("band", "Knapp unter der Schwelle",
                             f"«{name}» liegt mit {s:.2f} im Prüfbereich {max(0.0, floor):.2f}–{t:.2f}: "
                             "zu hoch für «Kein Alarm», zu tief für einen Alarm."))
        elif u > max_uncertainty and s >= min_score_for_review:
            out.append(Cause("uncertain", "Unsicher",
                             f"Die Unsicherheit für «{name}» ist {u:.2f} (Maximum {max_uncertainty:.2f}) bei "
                             f"Score {s:.2f}."))

    # what makes the checks uncertain: contradiction and/or self-reported low confidence
    if decision.label == "review":
        per = top.per_check
        if per:
            hi = max(per.items(), key=lambda kv: kv[1])
            lo = min(per.items(), key=lambda kv: kv[1])
            if hi[1] >= max(t, 0.5) and lo[1] < floor and hi[1] - lo[1] >= 0.3 and hi[0] != lo[0]:
                out.append(Cause("disagree", "Prüfungen widersprechen sich",
                                 f"«{hi[0]}» sieht {hi[1]:.2f}, «{lo[0]}» nur {lo[1]:.2f} für «{name}»."))
        low = []
        for check in per:
            cr = result.checks.get(check)
            fs = cr.family_scores.get(top.family) if cr else None
            if fs is not None and fs.confidence < 0.5 and (weights or {}).get(check, 1.0) >= 0.5 \
                    and (cr.type not in RULE_CHECK_TYPES):
                low.append(f"{check} ({100 * fs.confidence:.0f}%)")
        if low:
            out.append(Cause("low_confidence", "Prüfungen sind sich selbst unsicher",
                             f"Geringe Selbstsicherheit bei {', '.join(low)}."))
        for f in decision.families.values():
            if can_alarm is not None and f.family not in can_alarm:
                continue
            und = [c for c, v in f.verdicts.items() if v == "undetermined"]
            if und and f.score >= min(min_score_for_review, floor):
                reason = ""
                for c in und:
                    cr = result.checks.get(c)
                    fs = cr.family_scores.get(f.family) if cr else None
                    if fs is not None and fs.reason:
                        reason = fs.reason.strip()
                        break
                out.append(Cause("undetermined", "Sachverhalt offen",
                                 f"{', '.join(und)} kann «{short(f.label)}» nicht entscheiden (unbestimmt)"
                                 + (f": {reason}" if reason else ".")))
    return out


# --------------------------------------------------------------------------------------------
# why not an alarm
# --------------------------------------------------------------------------------------------


@dataclass
class KeywordHit:
    phrase: str
    keyword_id: str
    start: float | None
    negated: bool
    harmless: str | None


@dataclass
class CheckOpinion:
    check: str
    type: str
    weight: float
    score: float
    confidence: float
    verdict: str | None
    reason: str
    above: bool  # score >= threshold


@dataclass
class WhyNot:
    family: str
    family_label: str
    label: str
    score: float
    threshold: float
    floor: float
    hits: list[KeywordHit]
    opinions: list[CheckOpinion]  # every check that scored the family, strongest first
    counter: CheckOpinion | None  # the strongest counter-evidence
    rule: RuleMatch | None  # best-matching not_alarm_when rule
    rule_source: str = ""  # "fact" (the fact sheet named it) | "match" (word overlap: a hint)
    harmless_notes: list[str] = field(default_factory=list)
    summary: str = ""


def keyword_hits(result: CallResult, family: str) -> list[KeywordHit]:
    out = []
    for cr in result.checks.values():
        if cr.type != "keywords":
            continue
        for f in cr.findings:
            if f.family != family:
                continue
            d = f.detail if isinstance(f.detail, dict) else {}
            out.append(KeywordHit(str(d.get("matched_text") or d.get("phrase") or ""), str(d.get("keyword_id") or ""),
                                  f.start, bool(d.get("negated")), d.get("harmless")))
    return out


def why_not_alarm(result: CallResult, decision: Decision, families: Sequence[Family], *, threshold: float,
                  review_band: float, weights: Mapping[str, float] | None = None,
                  min_hits: int = 1) -> WhyNot | None:
    """Explanation for a call that looks suspicious on the surface (keyword hits, or one check above the
    threshold) but is not an alarm. None for alarms and for calls with nothing to explain."""
    if decision.label == "alarm":
        return None
    fam_by_id = {f.id: f for f in families}
    candidates = []
    for fid, ff in decision.families.items():
        fam = fam_by_id.get(fid)
        if fam is None or not fam.can_alarm:
            continue
        hits = keyword_hits(result, fid)
        loudest = max(ff.per_check.values(), default=0.0)
        if len(hits) >= min_hits or loudest >= threshold:
            candidates.append((len(hits), loudest, ff.score, fid, hits))
    if not candidates:
        return None
    _, _, _, fid, hits = max(candidates, key=lambda c: (c[0] > 0, c[1], c[0], c[2]))
    ff, fam = decision.families[fid], fam_by_id[fid]
    floor = _floor(threshold, review_band)

    opinions = []
    for name, cr in result.checks.items():
        fs = cr.family_scores.get(fid)
        if fs is None or cr.meta.get("error"):
            continue
        w = float((weights or {}).get(name, 1.0))
        opinions.append(CheckOpinion(name, cr.type, w, float(fs.score), float(fs.confidence), fs.verdict,
                                     (fs.reason or "").strip(), float(fs.score) >= threshold))
    opinions.sort(key=lambda o: -o.score)

    def counter_strength(o: CheckOpinion) -> float:
        explained = 1.0 if len(o.reason.split()) >= 4 else 0.5  # "G-Eval 1.5/5" explains nothing
        return o.weight * max(o.confidence, 0.05) * (1.0 - o.score) * explained

    # rule checks only count cues (their low score is absence of a cue, not an argument against)
    low = [o for o in opinions if o.type not in RULE_CHECK_TYPES and (o.score < max(floor, 0.0) or o.verdict == "absent")]
    counter = max(low, key=counter_strength, default=None)

    rule, source = None, ""
    fact_rule = _fact_rule(result, fid)
    if fact_rule:
        rule, source = RuleMatch(fact_rule, 1.0), "fact"
    else:
        texts = [o.reason for o in low if o.reason] + [h.harmless for h in hits if h.harmless]
        rule = best_rule(texts, fam.not_alarm_when, min_score=0.15)
        source = "match" if rule else ""
    notes = list(dict.fromkeys(h.harmless for h in hits if h.harmless))

    phrases = list(dict.fromkeys(h.phrase for h in hits if h.phrase))
    parts = []
    if phrases:
        parts.append(f"Stichwörter wie {', '.join('«' + p + '»' for p in phrases[:3])} kommen vor")
    loud = [o for o in opinions if o.above]
    if loud and not phrases:
        parts.append(f"{', '.join(o.check for o in loud)} schlägt an")
    if counter is not None:
        why = counter.reason.rstrip(" .") if counter.reason and len(counter.reason.split()) >= 4 else ""
        parts.append(f"aber «{counter.check}» bewertet «{short(fam.label)}» nur mit {counter.score:.2f}"
                     + (f": {why}" if why else ""))
    summary = ", ".join(parts) + "." if parts else ""
    return WhyNot(fid, fam.label, decision.label, ff.score, threshold, floor, hits, opinions, counter, rule,
                  source, notes, summary)


# --------------------------------------------------------------------------------------------
# evidence timeline
# --------------------------------------------------------------------------------------------


def call_duration(result: CallResult) -> float:
    ends = [s.end for v in result.all_views().values() for s in v.segments]
    return float(result.transcript.duration or max(ends, default=0.0) or 1.0)


def timeline_events(result: CallResult, decision: Decision, *, min_score: float = 0.05) -> list[dict[str, Any]]:
    """One marker per finding (check x family x time), plus call-level citations of checks without
    findings. Times come from the finding, else from the cited segments of the view the check read."""
    rows: list[dict[str, Any]] = []
    labels = {fid: f.label for fid, f in decision.families.items()}
    for name, cr in result.checks.items():
        src = result.view(cr.view) if cr.view else result.transcript
        seen_fams = set()
        for f in cr.findings:
            if f.score < min_score:
                continue
            start, end = f.start, f.end
            if start is None:
                span = src.span(f.segment_ids) if f.segment_ids else None
                if span is None:
                    continue
                start, end = span
            seen_fams.add(f.family)
            rows.append({"check": name, "family": f.family, "family_label": short(labels.get(f.family, f.family)),
                         "start": float(start), "end": float(end if end is not None else start),
                         "score": float(f.score), "reason": (f.reason or "").strip(), "kind": "Fund"})
        for fid, fs in cr.family_scores.items():
            if fid in seen_fams or fs.score < max(min_score, 0.2) or not fs.segment_ids:
                continue
            span = src.span(fs.segment_ids)
            if span is None:
                continue
            rows.append({"check": name, "family": fid, "family_label": short(labels.get(fid, fid)),
                         "start": float(span[0]), "end": float(span[1]), "score": float(fs.score),
                         "reason": (fs.reason or "").strip(), "kind": "Zitat"})
    for r in rows:
        r["time"] = fmt_ts(r["start"])
    rows.sort(key=lambda r: (r["start"], r["check"]))
    return rows
