"""General yes/no question set (``type: questions``): p(yes) per question, call risk = max p(yes).

The teammate prototype's decision rule (sprintd_zurich ``fraud_analysis/analysis.py``) as a check: a list of
general, law-based yes/no questions (``config/general_questions.yaml``, written without test data) is asked
about the whole transcript and the highest p(yes) is the call's risk. Each question names one of our
families (``family:``); the family score is the max p(yes) of its questions, and since every question
belongs to exactly one alarmable family, the fusion's call score (max over families) is the max over all
questions. Alone in a variant with the weighted fusion this reproduces their rule exactly.

Two backends, picked by what the configured LLM offers:

* an LLM with ``noul_batch`` (``llm/kev.py``, Kev-4B): all questions in ONE request per call, as the
  teammate's service does it (Kev's question branches see only the state and themselves, so the answers
  do not depend on which other questions share the request);
* any other LLM (vLLM Qwen2.5-7B, fake): one single-token prompt per question, exactly the ``facts`` check's
  prompt (``fact_prompts.fact_messages``, topic = the question's category) and logprob read-out:
  p(yes) renormalised over yes / no / unknown, sampling fallback without logprobs. Probes are cached per
  prompt (namespace ``question_probe``).

``localize: true`` (Kev backend only; their localisation step 1 without the word occlusion): for every
question with p(yes) >= ``localize_min`` the call is cut into windows of ``window_segments`` segments
(half overlap), all those questions are asked on every window in one request each, and the best window per
question becomes a finding (= an audio passage). Costs one Kev request per window.

Failures are never a silent 0: a failed Kev request fails the check (the pipeline records the error and
the experiment marks the variant DEGRADED); a failed single question on the LLM path is reported in
``meta.errors`` and the result is not cached.

Cache key: params + LLM identity (served model, for Kev also dtype / calibration) + a hash of the
questions that are asked (instructions, criteria, family, category; ``basis`` / ``list`` are display only).
"""

from __future__ import annotations

import logging
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel

from callguard.cache import stable_hash
from callguard.checks import fact_prompts as fp
from callguard.checks import prompts
from callguard.checks.llm_judge import LLMCheck
from callguard.config import ROOT
from callguard.plugins import LLM
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.questions")

QUESTIONS_VERSION = "questions-1"
PROBE_NAMESPACE = "question_probe"
DEFAULT_QUESTIONS = "config/general_questions.yaml"
_QID = re.compile(r"^[a-z][a-z0-9_]{1,40}$")


class QuestionSetError(ValueError):
    pass


class _Probe(BaseModel):
    """One single-prompt answer (LLM backend), cached in ``question_probe``."""

    p_yes: float
    method: str


@dataclass
class Question:
    id: str
    instructions: str
    family: str
    category: str = ""
    basis: str = ""
    list: str = ""
    criteria: dict[str, str] = field(default_factory=dict)

    def keyed(self) -> dict[str, Any]:
        """What the answer depends on (basis / list are display only)."""
        return {"id": self.id, "instructions": self.instructions, "criteria": self.criteria,
                "family": self.family, "category": self.category}

    def kev(self) -> dict[str, Any]:
        return {"instructions": self.instructions, **({"criteria": self.criteria} if self.criteria else {})}

    def llm_text(self) -> str:
        if not self.criteria:
            return self.instructions
        parts = [f"{k} = {v}" for k, v in (("yes", self.criteria.get("true")), ("no", self.criteria.get("false"))) if v]
        return f"{self.instructions} ({'; '.join(parts)})"


@dataclass
class QuestionSet:
    questions: list[Question]
    path: str = ""
    threshold: float | None = None
    source: str = ""

    def key(self, asked: list[Question]) -> str:
        return stable_hash([q.keyed() for q in asked])


def parse_question_set(raw: Any, source: str = "question set") -> QuestionSet:
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), dict) or not raw["questions"]:
        raise QuestionSetError(f"{source}: expected a mapping with a non-empty `questions:` block")
    out: list[Question] = []
    for qid, q in raw["questions"].items():
        where = f"{source}: question {qid}"
        if not _QID.match(str(qid)):
            raise QuestionSetError(f"{where}: id must be lower-case letters, digits and _")
        if not isinstance(q, dict):
            raise QuestionSetError(f"{where}: expected a mapping")
        bad = set(q) - {"instructions", "family", "category", "basis", "list", "criteria", "type"}
        if bad:
            raise QuestionSetError(f"{where}: unknown keys {sorted(bad)}")
        if q.get("type", "noul") != "noul":
            raise QuestionSetError(f"{where}: only yes/no (noul) questions are supported")
        text = " ".join(str(q.get("instructions") or "").split())
        if not text:
            raise QuestionSetError(f"{where}: instructions missing")
        if not str(q.get("family") or "").strip():
            raise QuestionSetError(f"{where}: `family` missing (the family that shows this question)")
        crit = {k: str(v).strip() for k, v in (q.get("criteria") or {}).items() if k in ("true", "false") and str(v).strip()}
        out.append(Question(id=str(qid), instructions=text, family=str(q["family"]).strip(),
                            category=str(q.get("category") or ""), basis=str(q.get("basis") or ""),
                            list=str(q.get("list") or ""), criteria=crit))
    thr = raw.get("threshold")
    return QuestionSet(questions=out, path=source, threshold=float(thr) if thr is not None else None,
                       source=str(raw.get("source") or ""))


_MEMO: dict[str, tuple[float, QuestionSet]] = {}
_LOCK = threading.Lock()


def load_question_set(path: str | Path) -> QuestionSet:
    """Read and validate; re-read when the file changes."""
    p = Path(path)
    p = p if p.is_absolute() else ROOT / p
    try:
        mtime = p.stat().st_mtime
    except OSError as e:
        raise QuestionSetError(f"question set {p} not readable: {e}") from e
    with _LOCK:
        hit = _MEMO.get(str(p))
        if hit and hit[0] == mtime:
            return hit[1]
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise QuestionSetError(f"question set {p} is not valid YAML: {e}") from e
    qs = parse_question_set(raw, source=str(p))
    with _LOCK:
        _MEMO[str(p)] = (mtime, qs)
    return qs


def windows(n: int, size: int) -> list[tuple[int, int]]:
    """Segment windows [i, j) of ``size`` segments with half overlap covering 0..n."""
    if n <= size:
        return [(0, n)] if n else []
    step = max(1, math.ceil(size / 2))
    out = [(i, min(n, i + size)) for i in range(0, n - size + 1, step)]
    if out[-1][1] < n:
        out.append((n - size, n))
    return out


class QuestionSetCheck(LLMCheck):
    plugin_kind = "check"
    plugin_type = "questions"

    def __init__(self, ctx: "Context", *, llm: str = "default", questions: str = DEFAULT_QUESTIONS,
                 roles: bool = True, localize: bool = False, localize_min: float = 0.5,
                 window_segments: int = 8, fallback_samples: int = 5, reason_language: str = "de",
                 include_non_alarm: bool = False, max_transcript_chars: int = 24000, parallel: int = 1,
                 name: str | None = None, weight: float = 1.0, enabled: bool = True):
        if int(window_segments) < 1:
            raise ValueError(f"window_segments must be >= 1, got {window_segments}")
        if int(fallback_samples) < 1:
            raise ValueError(f"fallback_samples must be >= 1, got {fallback_samples}")
        super().__init__(ctx, llm=llm, reason_language=reason_language, include_non_alarm=include_non_alarm,
                         max_transcript_chars=max_transcript_chars, parallel=parallel, name=name,
                         weight=weight, enabled=enabled, questions=str(questions), roles=roles,
                         localize=localize, localize_min=localize_min, window_segments=window_segments,
                         fallback_samples=fallback_samples)
        self.questions_path = str(questions)
        self.roles = bool(roles)
        self.localize = bool(localize)
        self.localize_min = float(localize_min)
        self.window_segments = int(window_segments)
        self.fallback_samples = int(fallback_samples)
        self.question_set()  # a broken file fails at startup, not on the first call

    def question_set(self) -> QuestionSet:
        return load_question_set(self.questions_path)

    def asked(self, families: list[Family]) -> list[Question]:
        ids = {f.id for f in self.select_families(families)}
        return [q for q in self.question_set().questions if q.family in ids]

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        return {
            "params": self.cache_params(),
            "llm": self.llm_identity,
            "families": [f.id for f in self.select_families(families)],
            "questions": self.question_set().key(self.asked(families)),
            "version": QUESTIONS_VERSION,
            "prompt_version": fp.PROMPT_VERSION,  # the single-question prompt of the LLM backend
        }

    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        raise NotImplementedError("questions are asked per call, not per family (see run)")

    # -- the call -----------------------------------------------------------------------------------

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        fams = self.select_families(families)
        result = CheckResult(check=self.name, type=self.plugin_type)
        meta = result.meta
        qset = self.question_set()
        asked = self.asked(families)
        meta.update(llm=self.llm_name, model=self.model_name, version=QUESTIONS_VERSION,
                    questions={"path": self.questions_path, "hash": qset.key(asked), "n": len(asked)})
        asked_ids = {q.id for q in asked}
        skipped = [q.id for q in qset.questions if q.id not in asked_ids]
        if skipped:
            meta["skipped_questions"] = skipped  # their family is disabled or not alarmable
        if not asked:
            return result
        if not transcript.segments:
            meta["skipped"] = "empty transcript"
            return result
        if not self.roles:
            transcript = transcript.model_copy(update={"segments": [
                s.model_copy(update={"role": "unknown"}) for s in transcript.segments]})
        rendered, omitted = prompts.render_transcript(transcript, self.max_transcript_chars)
        if omitted:
            meta["omitted_lines"] = omitted
        try:
            llm = self.ctx.llm(self.llm_name)
        except Exception as e:
            raise RuntimeError(f"{self.name}: LLM {self.llm_name!r} unavailable: {e}") from e
        meta["model"] = llm.model_id

        batch = getattr(llm, "noul_batch", None)
        errors: dict[str, str] = {}
        if callable(batch):
            p, info = batch(rendered, {q.id: q.kev() for q in asked})  # raises: the whole check fails
            meta.update(backend="noul_batch", llm_calls=1, served=info)
        else:
            p, errors, calls, cached = self._ask_each(llm, rendered, asked, transcript.lang)
            meta.update(backend="single_prompts", llm_calls=calls, cached_probes=cached)
        if not p:
            raise RuntimeError(f"{self.name}: every question failed: {errors}")
        if errors:
            meta["errors"] = errors
            meta["cacheable"] = False

        by_id = {q.id: q for q in asked}
        top = max(p, key=lambda qid: p[qid])
        meta["call_score"] = round(p[top], 4)
        meta["top_question"] = top
        if qset.threshold is not None:
            meta["source_threshold"] = qset.threshold
        for f in fams:
            fq = [q for q in asked if q.family == f.id and q.id in p]
            if not fq:
                continue
            best = max(fq, key=lambda q: p[q.id])
            pb = p[best.id]
            detail = {"questions": {q.id: {"p": round(p[q.id], 4), "question": q.instructions,
                                           "category": q.category, "basis": q.basis} for q in fq},
                      "top_question": best.id}
            result.family_scores[f.id] = FamilyScore(
                score=round(pb, 4), confidence=1.0, verdict="present" if pb >= 0.5 else "absent",
                reason=f"{best.category or best.id}: «{best.instructions}» p(ja) = {pb:.2f}"
                       + (f" ({best.basis})" if best.basis else ""),
                detail=detail)

        if self.localize:
            if not callable(batch):
                meta["localize_skipped"] = "localisation needs a noul_batch backend (Kev)"
            else:
                fired = [by_id[qid] for qid, v in p.items() if v >= self.localize_min]
                if fired:
                    try:
                        result.findings.extend(self._localize(batch, transcript, fired, p, result, meta))
                    except Exception as e:  # the score stands; passages are retried on the next run
                        log.warning("%s: localisation failed on %s: %s", self.name, transcript.call_id, e)
                        meta["localize_error"] = f"{type(e).__name__}: {e}"[:300]
                        meta["cacheable"] = False
        return result

    # -- LLM backend (one prompt per question) -------------------------------------------------------

    def _ask_each(self, llm: LLM, rendered: str, asked: list[Question], lang: str | None
                  ) -> tuple[dict[str, float], dict[str, str], int, int]:
        counts = {"calls": 0, "cached": 0}
        lock = threading.Lock()

        def one(q: Question) -> tuple[str, float | None, str | None]:
            messages = fp.fact_messages(rendered, q.category or q.id, q.id, q.llm_text(), transcript_lang=lang)
            try:
                return q.id, self._probe(llm, messages, counts, lock), None
            except Exception as e:
                log.warning("%s: question %s failed: %s", self.name, q.id, e)
                return q.id, None, f"{type(e).__name__}: {e}"[:300]

        if self.parallel > 1 and len(asked) > 1:
            with ThreadPoolExecutor(max_workers=min(self.parallel, len(asked))) as ex:
                outs = list(ex.map(one, asked))
        else:
            outs = [one(q) for q in asked]
        p = {qid: v for qid, v, err in outs if v is not None}
        errors = {qid: err for qid, _, err in outs if err is not None}
        return p, errors, counts["calls"], counts["cached"]

    def _probe(self, llm: LLM, messages: list[dict[str, str]], counts: dict[str, int], lock: threading.Lock) -> float:
        """p(yes) of one prompt: next-token logprobs over yes / no / unknown (as in the facts check), else
        the share of "yes" among ``fallback_samples`` samples. Cached per prompt + model."""
        key = {"messages": stable_hash(messages), "llm": llm.cache_params(), "version": fp.PROMPT_VERSION,
               "fallback_samples": self.fallback_samples}
        hit = self.ctx.cache.get(PROBE_NAMESPACE, key, _Probe)
        if hit is not None:
            with lock:
                counts["cached"] += 1
            return hit.p_yes
        with lock:
            counts["calls"] += 1
        transient = False
        probs = None
        try:
            raw = llm.choice_probs(messages, list(fp.ANSWERS))
            probs = fp.probs_from_choices(raw) if raw else None
        except Exception as e:
            transient = True
            log.warning("%s: choice_probs failed, sampling instead: %s", self.name, e)
        if probs is not None:
            out = _Probe(p_yes=round(probs["yes"], 4), method="logprobs")
        else:
            with lock:
                counts["calls"] += 1
            outs = llm.chat(messages, temperature=1.0, max_tokens=4, n=self.fallback_samples) or []
            answers = [a for a in (fp.parse_answer(o) for o in outs) if a]
            if not answers:
                raise ValueError(f"no yes/no/unknown in {len(outs)} sampled answers, e.g. {outs[:1]!r}")
            out = _Probe(p_yes=round(answers.count("yes") / len(answers), 4), method="sampling")
        if not transient:
            self.ctx.cache.put(PROBE_NAMESPACE, key, out)
        return out.p_yes

    # -- localisation (Kev) --------------------------------------------------------------------------

    def _localize(self, batch: Any, transcript: Transcript, fired: list[Question], p: dict[str, float],
                  result: CheckResult, meta: dict[str, Any]) -> list[Finding]:
        segs = transcript.segments
        best: dict[str, tuple[float, int, int]] = {}
        wins = windows(len(segs), self.window_segments)
        for i, j in wins:
            part = transcript.model_copy(update={"segments": segs[i:j]})
            text, _ = prompts.render_transcript(part, self.max_transcript_chars)
            pw, _ = batch(text, {q.id: q.kev() for q in fired})
            for qid, v in pw.items():
                if qid not in best or v > best[qid][0]:
                    best[qid] = (v, i, j)
        meta["llm_calls"] = int(meta.get("llm_calls", 0)) + len(wins)
        meta["localize_windows"] = len(wins)
        findings = []
        for q in fired:
            if q.id not in best:
                continue
            v, i, j = best[q.id]
            ids = [s.id for s in segs[i:j]]
            span = transcript.span(ids)
            findings.append(Finding(
                check=self.name, family=q.family, score=round(p[q.id], 4), segment_ids=ids,
                start=span[0] if span else None, end=span[1] if span else None,
                reason=f"{q.category or q.id}: «{q.instructions}» (Stelle p(ja) {v:.2f}, ganzer Anruf {p[q.id]:.2f})",
                detail={"question": q.id, "p_window": round(v, 4), "p_call": round(p[q.id], 4)}))
            fs = result.family_scores.get(q.family)
            if fs is not None and fs.detail.get("top_question") == q.id:
                fs.segment_ids = ids
        return findings
