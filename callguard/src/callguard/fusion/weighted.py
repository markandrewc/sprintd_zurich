"""Weighted-mean fusion with explicit, explainable escalation rules.

Why not a learned combiner: 30 dialogues are far too few to train one, and a compliance officer must
be able to read *why* a call alarmed. Every rule that fires leaves a German sentence with the numbers
in ``Decision.reasons``.

Uncertainty has two sources, both of which push borderline calls to ``review`` instead of guessing:
checks contradicting each other (weighted spread of their scores) and checks reporting low
confidence in their own score.

Per family, with effective weight ``e_c = weight_c * max(conf_c, 0.05)`` over the checks that scored it:
``score = sum(e_c * s_c) / sum(e_c)``, ``disagreement = min(1, 2 * sqrt(sum(e_c * (s_c - score)^2) / sum(e_c)))``,
``uncertainty = 0.5 * disagreement + 0.5 * (1 - sum(weight_c * conf_c) / sum(weight_c))``. The call score is
the highest family score among families that may alarm.

Optional knobs (all off by default; off = exactly the v1 numbers):

* ``abstain_on_empty: true`` (idea N14, "absence of evidence is not evidence of absence"): a rule check
  (``rule_checks``, default the types ``keywords`` and ``patterns``) that found nothing for a family
  (family score <= 0 and no finding of that family with a positive score) abstains for that family: it is
  left out of the weighted mean, the disagreement AND the mean confidence, as if it had not scored the
  family. Without the knob it enters all three as "score 0 at its absent_confidence" (keywords: 0.25 at
  weight 0.35), which pulls the mean down and inflates the uncertainty of a clear no-keyword alarm (the
  Stufe2 profile) until it is escalated to review. Rule checks with a hit, and LLM checks saying 0, still
  count in full. If every check that scored the family is an empty rule check, nothing abstains (they are
  the only opinion there is; score 0 as before).
* ``uncertainty_from: llm``: disagreement and mean confidence are computed only over the non-rule checks
  that went into the family (their own weighted mean and spread); the score still uses every check. Falls
  back to all checks when no non-rule check scored the family. ``all`` (default) = v1.
* ``family_thresholds: {trade: 0.5, ...}`` (or the path of a ``callguard fit-fusion --kind thresholds``
  JSON; idea N2): the alarm threshold per family, shown to the officer in the reasons. The officer's one
  threshold slider shifts all of them together: ``t_f = family_thresholds[f] + (slider - threshold)``;
  families not listed use the slider value. The top family is then the one with the largest margin
  ``score_f - t_f`` and the call is labelled against its ``t_f`` (review band below it as usual);
  ``Decision.threshold`` is that ``t_f``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from callguard.plugins import Fusion
from callguard.types import (
    CheckResult,
    Decision,
    Family,
    FamilyScore,
    FusedFamily,
    Label,
    Passage,
    Transcript,
    fmt_ts,
)

if TYPE_CHECKING:
    from callguard.context import Context

MIN_CONFIDENCE = 0.05  # a check saying "confidence 0" still counts a little, so its score is visible
HINT_MIN_WEIGHT = 0.5  # only substantial checks may escalate an "undetermined" verdict to review


def _clip(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if x < lo else hi if x > hi else x


def _num(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def _band_floor(t: float, band: float) -> float:
    """Rounded so a slider at 0.45 with band 0.15 includes a score of exactly 0.30 (float noise)."""
    return round(t - band, 6)


def short_label(label: str) -> str:
    """'Insiderhandel (Information und Kaufwunsch)' -> 'Insiderhandel' for titles and sentences."""
    return label.split(" (")[0].strip() or label


@dataclass
class _Contribution:
    check: str
    weight: float
    score: float
    confidence: float
    fs: FamilyScore
    rule: bool = False  # a rule check (rule_checks): context-blind cue matching
    empty: bool = False  # a rule check that found nothing for this family


UNCERTAINTY_FROM = ("all", "llm")
RULE_CHECKS = ("keywords", "patterns")


def load_family_thresholds(spec: dict[str, Any] | str | None) -> dict[str, float] | None:
    """``{family: threshold}`` from a dict or the path of a fitted ``thresholds`` model (JSON with a
    ``family_thresholds`` block). Relative paths are resolved against the repo root."""
    if spec is None or spec == {} or spec == "":
        return None
    if isinstance(spec, str):
        import json
        from pathlib import Path

        from callguard.config import ROOT
        p = Path(spec)
        p = p if p.is_absolute() else ROOT / p
        raw = json.loads(p.read_text())
        spec = raw.get("family_thresholds", raw)
    if not isinstance(spec, dict):
        raise ValueError(f"family_thresholds must be a mapping family -> threshold, got {spec!r}")
    out = {}
    for k, v in spec.items():
        x = _num(v)
        if x is None:
            raise ValueError(f"family_thresholds.{k}={v!r} is not a number")
        out[str(k)] = x
    return out or None


@dataclass
class _Evidence:
    start: float
    end: float
    segment_ids: list[str]
    score: float
    check: str
    reason: str


class WeightedFusion(Fusion):
    def __init__(self, ctx: "Context", *, threshold: float = 0.55, review_band: float = 0.15,
                 max_uncertainty: float = 0.35, min_score_for_review: float = 0.25,
                 max_passages: int = 5, merge_gap: float = 3.0, max_passage_seconds: float = 60.0,
                 abstain_on_empty: bool = False, uncertainty_from: str = "all",
                 rule_checks: list[str] | tuple[str, ...] = RULE_CHECKS,
                 family_thresholds: dict[str, float] | str | None = None):
        if uncertainty_from not in UNCERTAINTY_FROM:
            raise ValueError(f"uncertainty_from must be one of {UNCERTAINTY_FROM}, got {uncertainty_from!r}")
        # the v2 knobs enter params (provenance) only when set, so default configs keep their v1 params
        extra: dict[str, Any] = {}
        if abstain_on_empty:
            extra["abstain_on_empty"] = True
        if uncertainty_from != "all":
            extra["uncertainty_from"] = uncertainty_from
        if tuple(rule_checks) != RULE_CHECKS:
            extra["rule_checks"] = list(rule_checks)
        if family_thresholds:
            extra["family_thresholds"] = family_thresholds
        super().__init__(ctx, threshold=threshold, review_band=review_band,
                         max_uncertainty=max_uncertainty, min_score_for_review=min_score_for_review,
                         max_passages=max_passages, merge_gap=merge_gap, max_passage_seconds=max_passage_seconds,
                         **extra)
        self.abstain_on_empty = bool(abstain_on_empty)
        self.uncertainty_from = uncertainty_from
        self.rule_checks = frozenset(rule_checks)  # check types or instance names
        self.family_thresholds = load_family_thresholds(family_thresholds)
        self.threshold = threshold
        self.review_band = review_band
        self.max_uncertainty = max_uncertainty
        self.min_score_for_review = min_score_for_review
        self.max_passages = max_passages
        self.merge_gap = merge_gap
        self.max_passage_seconds = max_passage_seconds  # 0 = no cap

    # -- knobs ------------------------------------------------------------------------------------

    def _config_weights(self) -> dict[str, float]:
        """Weights from the YAML, so a UI override that only names one check keeps the others' weights."""
        cfg = getattr(self.ctx, "cfg", None)
        out: dict[str, float] = {}
        for spec in getattr(cfg, "checks", None) or []:
            name = spec.get("name") or spec.get("type")
            w = _num(spec.get("weight", 1.0))
            if name and w is not None:
                out[str(name)] = w
        return out

    def decide(self, transcript: Transcript, results: dict[str, CheckResult], families: list[Family],
               overrides: dict[str, Any] | None = None,
               views: dict[str, Transcript] | None = None) -> Decision:
        """``views``: every view of the call (multi-view configs). Findings of a check that read another
        view are placed by audio time and mapped onto the primary ``transcript``'s segments; each
        passage gets ``texts`` (what every view says in its time range)."""
        o = overrides or {}

        def knob(name: str) -> float:
            v = _num(o.get(name))
            return v if v is not None else float(getattr(self, name))

        t, band = knob("threshold"), knob("review_band")
        max_unc, min_review = knob("max_uncertainty"), knob("min_score_for_review")
        max_passages = int(o.get("max_passages", self.max_passages))
        merge_gap, max_len = knob("merge_gap"), knob("max_passage_seconds")
        disabled = set(o.get("disabled_checks") or ())
        weights = {**self._config_weights(), **{k: v for k, v in (o.get("weights") or {}).items()
                                                if _num(v) is not None}}

        failed = {n: str(r.meta.get("error")) for n, r in results.items()
                  if n not in disabled and r.meta.get("error")}
        usable = {n: r for n, r in results.items()
                  if n not in disabled and n not in failed and (_num(weights.get(n, 1.0)) or 0.0) > 0}
        w_of = {n: float(weights.get(n, 1.0)) for n in usable}

        fams = [f for f in families if f.enabled]
        fam_by_id = {f.id: f for f in fams}
        fused: dict[str, FusedFamily] = {}
        hints: dict[str, list[str]] = {}
        has_contrib: set[str] = set()
        for f in fams:
            contribs = []
            for name, r in usable.items():
                fs = r.family_scores.get(f.id)
                score = _num(fs.score) if fs is not None else None
                if fs is None or score is None:
                    continue
                conf = _clip(_num(fs.confidence) if _num(fs.confidence) is not None else 1.0)
                rule = r.type in self.rule_checks or name in self.rule_checks
                empty = rule and score <= 0 and not any(
                    x.family == f.id and (_num(x.score) or 0.0) > 0 for x in r.findings)
                contribs.append(_Contribution(name, w_of[name], _clip(score), conf, fs, rule, empty))
            fused[f.id] = self._fuse_family(f, contribs)
            if contribs:
                has_contrib.add(f.id)
            hint = [c.check for c in contribs if c.fs.verdict == "undetermined" and c.weight >= HINT_MIN_WEIGHT]
            if hint:
                hints[f.id] = hint

        alarming = [f.id for f in fams if f.can_alarm]
        fam_t, listed = self._family_cuts(o, t, alarming)
        if fam_t is None:
            top = max(alarming, key=lambda fid: (fused[fid].score, fid in has_contrib, -fused[fid].uncertainty),
                      default=None)
        else:  # per-family thresholds: the family closest to (or furthest over) its own line decides
            top = max(alarming, key=lambda fid: (round(fused[fid].score - fam_t[fid], 6), fused[fid].score,
                                                 fid in has_contrib, -fused[fid].uncertainty), default=None)
        score = fused[top].score if top else 0.0
        unc = fused[top].uncertainty if top else 0.0
        t_call = fam_t[top] if fam_t is not None and top else t

        label, reasons = self._label(score, unc, t_call, band, max_unc, min_review, top, fused, fam_by_id,
                                     hints, usable, failed)
        if fam_t is not None and top:
            base_t = listed.get(top)
            reasons.append(
                f"Schwelle je Familie: '{short_label(fam_by_id[top].label)}' {t_call:.2f}"
                + (f" (konfiguriert {base_t:.2f}, Regler verschiebt alle Familien um {t - self.threshold:+.2f})."
                   if base_t is not None else " (globale Schwelle, keine eigene Familienschwelle)."))
        if failed:
            for name, err in failed.items():
                reasons.append(f"Hinweis: Prüfung '{name}' ist ausgefallen und fehlt in der Bewertung "
                               f"({err[:120]}).")
        if disabled & set(results):
            reasons.append(f"Deaktivierte Prüfungen: {', '.join(sorted(disabled & set(results)))}.")

        floor = min(_band_floor(min([t, *fam_t.values()]) if fam_t else t, band), min_review)
        passages = self._passages(transcript, usable, fused, fam_by_id, floor, merge_gap,
                                  max_len, views)[:max(0, max_passages)]
        if views:
            for p in passages:
                p.texts = {name: view_text(v, p.start, p.end) for name, v in views.items()}
        return Decision(label=label, score=score, uncertainty=unc, threshold=t_call, families=fused,
                        passages=passages, reasons=reasons, top_family=top if score > 0 else None)

    def _family_cuts(self, o: dict[str, Any], t: float, alarming: list[str]
                     ) -> tuple[dict[str, float] | None, dict[str, float]]:
        """(per-family alarm thresholds after the slider shift, the configured ones), or (None, {}) for
        one global threshold (v1). ``overrides["family_thresholds"]`` replaces the configured block."""
        listed = load_family_thresholds(o["family_thresholds"]) if o.get("family_thresholds") \
            else self.family_thresholds
        if not listed:
            return None, {}
        shift = t - float(self.threshold)
        return {fid: round(_clip(listed[fid] + shift), 6) if fid in listed else t for fid in alarming}, listed

    # -- per family -------------------------------------------------------------------------------

    def _fuse_family(self, fam: Family, contribs: list[_Contribution]) -> FusedFamily:
        if not contribs:
            return FusedFamily(family=fam.id, label=fam.label, score=0.0, uncertainty=1.0,
                               reason="Keine Prüfung hat diese Familie bewertet.")
        if self.abstain_on_empty:  # N14: an empty rule check abstains (unless it is the only opinion)
            contribs = [c for c in contribs if not c.empty] or contribs
        eff = [c.weight * max(c.confidence, MIN_CONFIDENCE) for c in contribs]
        total = sum(eff)
        mean = sum(e * c.score for e, c in zip(eff, contribs)) / total
        src = contribs
        if self.uncertainty_from == "llm":
            src = [c for c in contribs if not c.rule] or contribs
        if src is contribs:
            var = sum(e * (c.score - mean) ** 2 for e, c in zip(eff, contribs)) / total
        else:  # spread of the non-rule checks around their own weighted mean
            s_eff = [c.weight * max(c.confidence, MIN_CONFIDENCE) for c in src]
            s_mean = sum(e * c.score for e, c in zip(s_eff, src)) / sum(s_eff)
            var = sum(e * (c.score - s_mean) ** 2 for e, c in zip(s_eff, src)) / sum(s_eff)
        disagreement = min(1.0, 2.0 * math.sqrt(max(var, 0.0)))
        w_total = sum(c.weight for c in src)
        mean_conf = sum(c.weight * c.confidence for c in src) / w_total
        unc = _clip(0.5 * disagreement + 0.5 * (1.0 - mean_conf))
        # an explanation ("Kunde will vor der Meldung kaufen ...") beats a bare score ("G-Eval 1.75/5")
        reason = next((c.fs.reason.strip() for c in sorted(
            contribs, key=lambda c: (-c.weight, len(c.fs.reason.split()) < 4, -c.score))
            if c.fs.reason and c.fs.reason.strip()), "")
        return FusedFamily(
            family=fam.id, label=fam.label, score=round(mean, 4), uncertainty=round(unc, 4),
            per_check={c.check: round(c.score, 4) for c in contribs},
            verdicts={c.check: c.fs.verdict for c in contribs},
            reason=reason,
        )

    # -- call label -------------------------------------------------------------------------------

    def _label(self, score: float, unc: float, t: float, band: float, max_unc: float, min_review: float,
               top: str | None, fused: dict[str, FusedFamily], fams: dict[str, Family],
               hints: dict[str, list[str]], usable: dict[str, CheckResult],
               failed: dict[str, str]) -> tuple[Label, list[str]]:
        reasons: list[str] = []
        top_name = short_label(fams[top].label) if top else "-"
        label: Label
        if not usable:
            label = "review"
            why = "alle Prüfungen sind ausgefallen" if failed else "keine Prüfung ist aktiv"
            reasons.append(f"Prüfen (unsicher): Keine Prüfung lieferte ein verwertbares Ergebnis ({why}); "
                           f"ein Mensch muss den Anruf beurteilen.")
            return label, reasons

        hinted = [fid for fid, checks in hints.items()
                  if fams[fid].can_alarm and fused[fid].score >= min_review]
        if score >= t:
            if unc > max_unc:
                label = "review"
                reasons.append(f"Prüfen (unsicher): Score {score:.2f} für '{top_name}' erreicht die Schwelle "
                               f"{t:.2f}, aber die Unsicherheit {unc:.2f} liegt über {max_unc:.2f}.")
            else:
                label = "alarm"
                reasons.append(f"Alarm: Score {score:.2f} für '{top_name}' >= Schwelle {t:.2f} "
                               f"bei Unsicherheit {unc:.2f} (max. {max_unc:.2f}).")
        elif score >= _band_floor(t, band):
            label = "review"
            reasons.append(f"Prüfen (knapp unter Schwelle): Score {score:.2f} für '{top_name}' liegt zwischen "
                           f"{_band_floor(t, band):.2f} und der Schwelle {t:.2f}.")
        elif hinted:
            label = "review"
            for fid in sorted(hinted, key=lambda f: -fused[f].score):
                reasons.append(f"Prüfen (offener Sachverhalt): {', '.join(hints[fid])} bewertet "
                               f"'{short_label(fams[fid].label)}' als unbestimmt "
                               f"(Score {fused[fid].score:.2f} >= {min_review:.2f}).")
        elif unc > max_unc and score >= min_review:
            label = "review"
            reasons.append(f"Prüfen (unsicher): Unsicherheit {unc:.2f} > {max_unc:.2f} bei Score {score:.2f} "
                           f"für '{top_name}' (>= {min_review:.2f}).")
        else:
            label = "no_alert"
            reasons.append(f"Kein Alarm: höchster Score {score:.2f} ('{top_name}') liegt unter "
                           f"{_band_floor(t, band):.2f} (Schwelle {t:.2f} minus Band {band:.2f}).")

        shown = [top] if top else []
        if label == "review" and hinted:
            shown += [fid for fid in hinted if fid != top]
        for fid in shown:
            if fused[fid].reason and fid in fams and (label != "no_alert" or fused[fid].score > 0):
                reasons.append(f"{short_label(fams[fid].label)}: {fused[fid].reason}")
        return label, reasons

    # -- passages ---------------------------------------------------------------------------------

    def _passages(self, transcript: Transcript, usable: dict[str, CheckResult], fused: dict[str, FusedFamily],
                  fams: dict[str, Family], floor: float, merge_gap: float, max_len: float,
                  views: dict[str, Transcript] | None = None) -> list[Passage]:
        out: list[Passage] = []

        def source(r: CheckResult) -> Transcript:
            """The transcript the check's segment ids refer to."""
            if views and r.view and r.view != transcript.view and r.view in views:
                return views[r.view]
            return transcript

        def evidence(name: str, r: CheckResult, start: float | None, end: float | None,
                     seg_ids: list[str], score: float, reason: str) -> _Evidence | None:
            src = source(r)
            ev = self._evidence(src, name, start, end, seg_ids, score, reason)
            if ev is not None and src is not transcript:  # another view's segment ids: re-anchor by time
                ev.segment_ids = overlapping_ids(transcript, ev.start, ev.end)
            return ev
        for fid, ff in fused.items():
            fam = fams[fid]
            # numbers-like families only annotate; their passages would crowd out real evidence
            if not fam.can_alarm or ff.score < floor or ff.score <= 0:
                continue
            items: list[_Evidence] = []
            for name, r in usable.items():
                for f in r.findings:
                    if f.family != fid:
                        continue
                    ev = evidence(name, r, f.start, f.end, f.segment_ids, f.score, f.reason)
                    if ev:
                        items.append(ev)
            if not items:  # checks gave a call-level opinion only: point at the segments they cited
                for name in ff.per_check:
                    fs = usable[name].family_scores[fid]
                    if fs.segment_ids:
                        ev = evidence(name, usable[name], None, None, fs.segment_ids, fs.score, fs.reason)
                        if ev:
                            items.append(ev)
            out.extend(self._merge(transcript, fam, items, merge_gap, max_len))
        # the families that drive the label first: a keyword passage of the top family must not be cut by
        # max_passages in favour of a weaker family's confident-but-wrong LLM passage
        out.sort(key=lambda p: (-fused[p.family].score, -p.score, p.start))
        return out

    @staticmethod
    def _evidence(transcript: Transcript, check: str, start: float | None, end: float | None,
                  segment_ids: list[str], score: float, reason: str) -> _Evidence | None:
        span = transcript.span(segment_ids) if segment_ids else None
        s = _num(start) if start is not None else (span[0] if span else None)
        e = _num(end) if end is not None else (span[1] if span else None)
        if s is None:
            return None
        e = s if e is None or e < s else e
        return _Evidence(s, e, list(segment_ids), _clip(_num(score) or 0.0), check, (reason or "").strip())

    @staticmethod
    def _merge(transcript: Transcript, fam: Family, items: list[_Evidence], gap: float,
               max_len: float = 0.0) -> list[Passage]:
        order = {s.id: i for i, s in enumerate(transcript.segments)}
        groups: list[list[_Evidence]] = []
        for ev in sorted(items, key=lambda x: (x.start, x.end)):
            if groups and ev.start <= max(x.end for x in groups[-1]) + gap:
                groups[-1].append(ev)
            else:
                groups.append([ev])

        passages = []
        for g in groups:
            start, end = min(x.start for x in g), max(x.end for x in g)
            seg_ids = list(dict.fromkeys(sid for x in g for sid in x.segment_ids))
            if not seg_ids:  # time-only findings: attach the overlapping segments for text and highlighting
                seg_ids = overlapping_ids(transcript, start, end)
            seg_ids.sort(key=lambda sid: order.get(sid, len(order)))
            by_score = sorted(g, key=lambda x: -x.score)
            reasons = list(dict.fromkeys(f"{x.check}: {x.reason}" for x in by_score if x.reason))
            if max_len > 0 and end - start > max_len:
                # an LLM citing minutes of the call has not localised anything; the officer gets a
                # listenable window, anchored at the strongest short evidence inside (e.g. a keyword)
                short = [x for x in g if x.end - x.start <= max_len]
                anchor = max(short, key=lambda x: (x.score, -x.start)).start if short else start
                cut = max(start, min(anchor, end - max_len))
                reasons.append(f"Passage gekürzt auf {fmt_ts(cut)}-{fmt_ts(cut + max_len)}; die Prüfungen "
                               f"zitieren {fmt_ts(start)}-{fmt_ts(end)}.")
                start, end = cut, cut + max_len
                seg_ids = [sid for sid in seg_ids
                           if (seg := transcript.segment(sid)) and seg.end > start and seg.start < end] or seg_ids[:1]
            text = " ".join(seg.text.strip() for sid in seg_ids if (seg := transcript.segment(sid)))
            passages.append(Passage(
                family=fam.id, family_label=fam.label, start=round(start, 3), end=round(end, 3),
                segment_ids=seg_ids, score=round(by_score[0].score, 4), reasons=reasons,
                checks=list(dict.fromkeys(x.check for x in by_score)), text=text,
            ))
        return passages


def overlapping_ids(transcript: Transcript, start: float, end: float) -> list[str]:
    """Ids of the segments overlapping [start, end] (a zero-length range still hits its segment)."""
    return [s.id for s in transcript.segments if s.end > start and s.start < max(end, start + 1e-3)]


def view_text(transcript: Transcript, start: float, end: float) -> str:
    """What ``transcript`` says in [start, end]: the text of its overlapping segments."""
    return " ".join(s.text.strip() for s in transcript.segments
                    if s.end > start and s.start < max(end, start + 1e-3))
