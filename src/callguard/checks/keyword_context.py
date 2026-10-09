"""Passage-level G-Eval checks: score short passages of a call instead of the whole call.

``keyword_context`` (v2 plan §1b, research RQ7): keywords and digit patterns are blind to context
("kaufen Sie nie vor der Meldung"), whole-call judges spread their attention over 40 turns. This check
asks the LLM, G-Eval style (probability-weighted 1..scale over the digit tokens, the machinery of
:class:`~callguard.checks.geval.GEvalCheck`), whether the passage AROUND each keyword / pattern hit
shows the family's misconduct, with the keyword's ``harmless`` note and the family criteria in the
prompt. Family score = max over passages; the decisive passage gets one JSON call for a reason and the
segments that carry it, so findings are pinned to a few segments instead of the whole call.

``context`` decides what the model sees:

* ``window`` - only the passage (+-``window`` segments around the hit). Short prompts, but context that
  is 7+ turns away (C01: the source of the information in T004, the trade wish in T011) is cut off.
* ``full``   - research idea N4, "anchored full-call probe": the whole transcript (prefix shared with
  geval/llm_judge, so cheap under prefix caching) and the question anchored on the passage ids:
  "Consider the passage S012-S015. Given the whole call, ...". The passage stays the exact location.

``anchored`` is the same check with ``context: full`` and ``window: 0`` as defaults (rate the hit
segment itself).

Families without any hit get no score by default (``empty: skip``: no opinion, so the fusion is not
dragged down by "no keyword" - see research N14); ``empty: zero`` reports 0 at low confidence.

:class:`WindowGEvalCheck` is the shared base, also used by ``semantic_windows`` (checks/semantic.py).
"""

from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from callguard.checks import prompts, window_prompts
from callguard.checks.geval import GEvalCheck
from callguard.checks.keywords import KeywordCheck
from callguard.checks.patterns import ACCESS, NUMBERS, PatternCheck
from callguard.plugins import LLM, family_cache_view
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.window")

CONTEXTS = ("window", "full")
EMPTY_MODES = ("skip", "zero")
MAX_CUES = 8  # cue lines per passage in the prompt
EMPTY_CONFIDENCE = 0.3


class CountingLLM:
    """Counts requests of one family's scoring (``meta.llm_calls``); everything else passes through."""

    def __init__(self, llm: LLM):
        self.llm = llm
        self.calls = 0
        self._lock = threading.Lock()

    def _count(self) -> None:
        with self._lock:
            self.calls += 1

    def chat(self, messages, **kw):
        self._count()
        return self.llm.chat(messages, **kw)

    def choice_probs(self, messages, choices):
        self._count()
        return self.llm.choice_probs(messages, choices)

    @property
    def model_id(self) -> str:
        return self.llm.model_id

    def cache_params(self) -> dict[str, Any]:
        return self.llm.cache_params()


@dataclass
class Anchor:
    """One passage to probe: ``seg_ids`` is the passage (window), ``core_ids`` what triggered it."""

    seg_ids: list[str]
    core_ids: list[str]
    cues: list[str]
    priority: float = 0.0  # higher = probed first when capped
    source: str = ""
    detail: dict[str, Any] = field(default_factory=dict)


def sub_transcript(t: Transcript, seg_ids: list[str]) -> Transcript:
    keep = set(seg_ids)
    return t.model_copy(update={"segments": [s for s in t.segments if s.id in keep]})


def in_rendered(rendered: str, seg_id: str) -> bool:
    return f"[{seg_id} " in rendered or f"[{seg_id}]" in rendered


class WindowGEvalCheck(GEvalCheck):
    """G-Eval on passages chosen by :meth:`find_anchors`. Subclasses implement the anchor search."""

    plugin_kind = "check"
    plugin_type = "window_geval"

    def __init__(self, ctx: "Context", *, context: str = "window", empty: str = "skip",
                 use_steps: bool = True, **geval_params: Any):
        if context not in CONTEXTS:
            raise ValueError(f"context must be one of {CONTEXTS}, got {context!r}")
        if empty not in EMPTY_MODES:
            raise ValueError(f"empty must be one of {EMPTY_MODES}, got {empty!r}")
        super().__init__(ctx, **geval_params)
        self.params.update(context=context, empty=empty, use_steps=use_steps)
        self.context = context
        self.empty = empty
        self.use_steps = bool(use_steps)

    # -- hooks ------------------------------------------------------------------------------------

    def find_anchors(self, transcript: Transcript, family: Family) -> tuple[list[Anchor], dict[str, Any]]:
        """-> (passages to probe, best first, already capped; info for the family detail)."""
        raise NotImplementedError

    # -- cache / run --------------------------------------------------------------------------------

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        key = super().cache_key(families)
        key["window_prompt_version"] = window_prompts.PROMPT_VERSION
        key["steps_prompt_version"] = prompts.STEPS_PROMPT_VERSION
        return key

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        result = super().run(transcript, families)
        meta = result.meta
        meta["window_prompt_version"] = window_prompts.PROMPT_VERSION
        meta["context"] = self.context
        calls = 0
        no_anchor = []
        errors = dict(meta.get("errors") or {})
        for fid, fs in list(result.family_scores.items()):
            calls += int(fs.detail.get("llm_calls") or 0)
            if fs.detail.get("window_errors"):
                errors[fid] = "; ".join(fs.detail["window_errors"])[:500]
            if fs.detail.get("no_anchor"):
                no_anchor.append(fid)
                if self.empty == "skip":
                    del result.family_scores[fid]
        meta["llm_calls"] = calls + len(meta.get("errors") or {})  # a failed family made >= 1 request
        if no_anchor:
            meta["no_anchor_families"] = no_anchor
        if errors:
            meta["errors"] = errors
            meta["cacheable"] = False
        return result

    # -- scoring ---------------------------------------------------------------------------------

    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        counter = CountingLLM(llm)
        anchors, info = self.find_anchors(transcript, family)
        if not anchors:
            fs = FamilyScore(score=0.0, confidence=EMPTY_CONFIDENCE, verdict=None,
                             reason=info.get("empty_reason") or "Keine Stelle zum Prüfen gefunden",
                             detail={**info, "no_anchor": True, "llm_calls": 0})
            return fs, []
        return self.score_anchors(counter, transcript, rendered, family, anchors, info)

    def score_anchors(self, counter: CountingLLM, transcript: Transcript, rendered: str, family: Family,
                      anchors: list[Anchor], info: dict[str, Any]) -> tuple[FamilyScore, list[Finding]]:
        steps, steps_source, steps_error = (self.evaluation_steps(counter, family) if self.use_steps
                                            else (None, "none", None))
        full = rendered if self.context == "full" else None
        windows: list[dict[str, Any]] = []
        errors: list[str] = []
        for a in anchors:
            win_r = sub_transcript(transcript, a.seg_ids).render()
            # anchored mode needs the passage inside the (possibly truncated) rendered call
            use_full = full if full is not None and all(in_rendered(full, s) for s in a.seg_ids) else None
            msgs = window_prompts.window_geval_messages(
                family, win_r, a.seg_ids, a.cues[:MAX_CUES], steps, self.scale, self.reason_language,
                transcript_lang=transcript.lang, full_rendered=use_full)
            try:
                dist, sinfo = self.score_distribution(counter, msgs)
            except Exception as e:
                log.warning("%s: passage %s of %s failed: %s", self.name, window_prompts.span_label(a.seg_ids),
                            family.id, e)
                errors.append(f"{window_prompts.span_label(a.seg_ids)}: {type(e).__name__}: {e}")
                continue
            expected = sum(int(c) * p for c, p in dist.items())
            score = min(1.0, max(0.0, (expected - 1) / (self.scale - 1)))
            entropy = -sum(p * math.log(p) for p in dist.values() if p > 0)
            conf = min(1.0, max(0.0, 1 - entropy / math.log(self.scale)))
            windows.append({"segment_ids": a.seg_ids, "core_ids": a.core_ids, "source": a.source,
                            "cues": a.cues[:MAX_CUES], "expected": round(expected, 4), "score": round(score, 4),
                            "confidence": round(conf, 4), "mode": "full" if use_full else "window",
                            "distribution": {c: round(p, 4) for c, p in dist.items()},
                            "method": sinfo.get("method"), "_rendered": win_r, "_full": use_full,
                            **({"logprobs_error": sinfo["logprobs_error"]} if "logprobs_error" in sinfo else {}),
                            **a.detail})
        if not windows:
            raise RuntimeError(f"all {len(anchors)} passage probes failed: {errors[0] if errors else '?'}")

        best = max(windows, key=lambda w: (w["score"], w["confidence"]))
        label = window_prompts.span_label(best["segment_ids"])
        reason = f"{label}: G-Eval {best['expected']:.2f}/{self.scale}"
        if best["cues"]:
            reason = f"{best['cues'][0]} – {reason}"
        evidence_ids = list(best["segment_ids"])
        detail: dict[str, Any] = {**info, "passages": len(windows), "steps_source": steps_source}
        if steps_error:
            detail["steps_error"] = steps_error
        if self.locate_evidence and best["score"] >= self.evidence_min_score:
            try:
                ev_reason, ev_ids = self._explain(counter, transcript, family, best)
            except Exception as e:
                log.warning("%s: evidence call for %s failed: %s", self.name, family.id, e)
                detail["evidence_error"] = f"{type(e).__name__}: {e}"
            else:
                if ev_reason:
                    reason = f"{ev_reason} ({label}, G-Eval {best['expected']:.2f}/{self.scale})"
                if ev_ids:
                    evidence_ids = ev_ids
        for w in windows:
            w.pop("_rendered", None)
            w.pop("_full", None)
        detail["windows"] = sorted(windows, key=lambda w: -w["score"])
        detail["llm_calls"] = counter.calls
        if errors:
            detail["window_errors"] = errors
        fs = FamilyScore(score=best["score"], confidence=best["confidence"], verdict=None, reason=reason,
                         segment_ids=evidence_ids, detail=detail)

        findings: list[Finding] = []
        for w in windows:
            if w["score"] < self.evidence_min_score:
                continue
            is_best = w is best
            ids = evidence_ids if is_best else w["segment_ids"]
            w_reason = reason if is_best else (
                f"{w['cues'][0] + ' – ' if w['cues'] else ''}{window_prompts.span_label(w['segment_ids'])}: "
                f"G-Eval {w['expected']:.2f}/{self.scale}")
            findings += self.evidence_findings(transcript, family, ids, w["score"], lambda run, r=w_reason: r,
                                               {"expected": w["expected"], "passage": w["segment_ids"],
                                                "source": w["source"], "mode": w["mode"]})
        return fs, findings

    def _explain(self, llm: CountingLLM, transcript: Transcript, family: Family,
                 w: dict[str, Any]) -> tuple[str, list[str]]:
        msgs = window_prompts.window_evidence_messages(
            family, w["_rendered"], w["segment_ids"], w["cues"], w["expected"], self.scale,
            self.reason_language, transcript_lang=transcript.lang, full_rendered=w["_full"])
        raw = (llm.chat(msgs, temperature=0.0, max_tokens=self.max_tokens,
                        json_schema=prompts.evidence_schema()) or [""])[0]
        obj = prompts.parse_json_object(raw)
        if obj is None:
            raise ValueError(f"unparseable evidence answer: {str(raw)[:200]!r}")
        allowed = set(w["segment_ids"])
        ids = [s for s in prompts.clean_evidence(obj.get("evidence"), transcript) if s in allowed]
        return prompts.clean_reason(obj.get("reason")), ids


class KeywordContextCheck(WindowGEvalCheck):
    """G-Eval on +-``window`` segments around every keyword (and digit-pattern) hit of a family.

    Params (besides the G-Eval ones: llm, scale, steps, auto_steps, locate_evidence, evidence_min_score,
    max_tokens, reason_language, include_non_alarm, max_transcript_chars, parallel):
      window         segments on each side of the hit (default 3); hits closer than that share a passage
      context        window | full (N4 anchored full-call probe)
      min_hit_score  ignore keyword/pattern hits scoring below this (0 = every hit, negated ones too)
      max_hits       passages probed per family (default 6), strongest hits first
      patterns       also anchor on digit runs of the ``patterns`` check (access family; default true)
      keyword_params params of the internal keyword matcher (default: fuzzy 90, like the profiles)
      empty          skip (no opinion when a family has no hit, default) | zero
    """

    plugin_kind = "check"
    plugin_type = "keyword_context"
    lang_sensitive = True  # keyword forms depend on the view language

    def __init__(self, ctx: "Context", *, window: int = 3, min_hit_score: float = 0.0, max_hits: int = 6,
                 patterns: bool = True, keyword_params: dict[str, Any] | None = None,
                 context: str = "window", **params: Any):
        if int(window) < 0:
            raise ValueError(f"window must be >= 0, got {window}")
        if int(max_hits) < 1:
            raise ValueError(f"max_hits must be >= 1, got {max_hits}")
        if not 0 <= float(min_hit_score) <= 1:
            raise ValueError(f"min_hit_score must be in 0..1, got {min_hit_score}")
        super().__init__(ctx, context=context, **params)
        kw_params = {"fuzzy": 90, **(keyword_params or {})}
        self.params.update(window=window, min_hit_score=min_hit_score, max_hits=max_hits,
                           patterns=patterns, keyword_params=kw_params)
        self.window = int(window)
        self.min_hit_score = float(min_hit_score)
        self.max_hits = int(max_hits)
        self.use_patterns = bool(patterns)
        self._kw = KeywordCheck(ctx, name=f"{self.name}:keywords", **kw_params)
        self._pat = PatternCheck(ctx, name=f"{self.name}:patterns") if self.use_patterns else None

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        key = super().cache_key(families)
        # the hits and their harmless notes come from the keyword list: keyword edits must rerun this
        key["keywords"] = [family_cache_view(f)["keywords"] for f in self.select_families(families)]
        return key

    def hits(self, transcript: Transcript, family: Family) -> tuple[list[Finding], list[str]]:
        """Keyword + pattern findings of one family (the rule checks, run on this view)."""
        findings: list[Finding] = []
        errors: list[str] = []
        res = self._kw.run(transcript, [family])
        findings += [f for f in res.findings if f.family == family.id]
        errors += [str(e) for e in res.meta.get("errors") or []]
        if self._pat is not None and family.id in (ACCESS, NUMBERS):
            res = self._pat.run(transcript, [family])
            findings += [f for f in res.findings if f.family == family.id]
            errors += [str(e) for e in res.meta.get("errors") or []]
        return [f for f in findings if f.score >= self.min_hit_score and f.segment_ids], errors

    def find_anchors(self, transcript: Transcript, family: Family) -> tuple[list[Anchor], dict[str, Any]]:
        found, errors = self.hits(transcript, family)
        info: dict[str, Any] = {"hits": len(found)}
        if errors:
            info["hit_errors"] = errors[:5]
        if not found:
            info["empty_reason"] = "Keine Stichwort- oder Muster-Treffer: kein Kontext zu prüfen"
            return [], info
        kws = {k.id: k for k in family.keywords}
        order = {s.id: i for i, s in enumerate(transcript.segments)}
        located = sorted(((order[f.segment_ids[0]], f) for f in found if f.segment_ids[0] in order),
                         key=lambda x: x[0])
        # hits whose windows touch share one passage; a passage never grows beyond ~2 windows
        gap = max(self.window, 1)
        clusters: list[list[tuple[int, Finding]]] = []
        for idx, f in located:
            if clusters and idx - clusters[-1][-1][0] <= gap and idx - clusters[-1][0][0] <= 2 * gap:
                clusters[-1].append((idx, f))
            else:
                clusters.append([(idx, f)])
        n = len(transcript.segments)
        anchors = []
        for cl in clusters:
            first, last = cl[0][0], max(i for i, f in cl)
            last = max(last, max(order.get(s, last) for _, f in cl for s in f.segment_ids))
            ids = [s.id for s in transcript.segments[max(0, first - self.window):min(n, last + self.window + 1)]]
            cues = list(dict.fromkeys(self.cue(f, kws) for _, f in cl))
            distinct = {f.detail.get("keyword_id") or f.detail.get("kind") for _, f in cl}
            anchors.append(Anchor(
                seg_ids=ids, core_ids=list(dict.fromkeys(s for _, f in cl for s in f.segment_ids)), cues=cues,
                priority=max(f.score for _, f in cl) + 0.01 * len(distinct),
                source="+".join(sorted({f.check.rsplit(":", 1)[-1] for _, f in cl})),
                detail={"keywords": sorted(k for k in distinct if k)}))
        anchors.sort(key=lambda a: -a.priority)
        info["passages_found"] = len(anchors)
        if len(anchors) > self.max_hits:
            info["passages_dropped"] = len(anchors) - self.max_hits
        return anchors[:self.max_hits], info

    @staticmethod
    def cue(f: Finding, kws: dict[str, Any]) -> str:
        seg = f.segment_ids[0]
        text = f"{seg}: {f.reason}"
        kw = kws.get(f.detail.get("keyword_id"))
        if kw is not None and kw.harmless:
            text += f" – harmless when: {kw.harmless}"
        return text


class AnchoredProbeCheck(KeywordContextCheck):
    """Research idea N4: ``keyword_context`` with ``context: full`` and ``window: 0`` by default - the
    whole call in the prompt, the question pinned on the hit segment itself."""

    plugin_kind = "check"
    plugin_type = "anchored"

    def __init__(self, ctx: "Context", *, window: int = 0, context: str = "full", **params: Any):
        super().__init__(ctx, window=window, context=context, **params)
