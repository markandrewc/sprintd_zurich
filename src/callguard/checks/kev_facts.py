"""Facts check read by Kev (``type: kev_facts``): the policy table's facts, Kev's p(yes), and passages
found by Kev itself. In the sherlock profile it is reader B (``facts_kev``) and the passage finder.

Same fact questions, table and fusion scores as :class:`~callguard.checks.facts.FactSheetCheck`; two things
differ because Kev answers yes/no only (no "unknown" mass, no text):

* **Read-out per fact role** (``yes_at``, ``no_below``): a fact is yes if p(yes) >= ``yes_at[role]``, no if
  p(yes) < ``no_below``, else unclear (defaults: act facts 0.5, other roles 0.7, because Kev tends to say yes
  to context / exculpatory facts). With ``yes_at`` 0.5 for every role this is exactly the plain facts check's
  read-out of a Kev answer. In the sherlock profile the call decision comes from the two-reader fact policy,
  which reads p(yes) itself, so this read-out only labels Kev's own fact list.
* **Passages without pointing** (``evidence_method``), for every fact with p(yes) > ``evidence_min``:

  - ``mask`` (default): remove one window of ``mask_segments`` segments (half overlap) at a time and ask
    the fact again; the passage is the window whose removal drops p(yes) most. All fired facts of a family
    share one Kev request per window. The reason states the drop ("ohne diese Stelle sinkt p(ja) von X auf
    Y"); it is not a correctness check. If no window drops p(yes) by ``mask_min_drop`` (a fact said several
    times), Kev gives no passage for that fact instead of an arbitrary one.
  - ``anchor``: one request per fired fact asking "does segment Sx itself show this?" for every segment;
    the passage is the best segment, the next ``anchor_top - 1`` are kept in the detail. One request per
    fact instead of one per window: much cheaper on long calls, single-segment passages.

Kev requests of both methods are cached per (state, questions, model) in namespace ``kev_batch``.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from callguard.cache import stable_hash
from callguard.checks import prompts
from callguard.checks.facts import FACT_ROLES, Fact, FactSheetCheck, FamilyTable, _fmt_fact
from callguard.checks.questions import windows
from callguard.llm.kev import parse_fact_prompt
from callguard.plugins import LLM
from callguard.types import Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.kev_facts")

BATCH_NAMESPACE = "kev_batch"
EVIDENCE_METHODS = ("mask", "anchor")
DEFAULT_YES_AT = {"act": 0.5, "context": 0.7, "exculpatory": 0.7, "authorization": 0.7}


class KevBatch(BaseModel):
    p: dict[str, float]


def anchor_question(question: str, sid: str) -> str:
    return (f"Look only at segment {sid}, but use the whole call to understand what it means. "
            f"Does segment {sid} itself show the following? {' '.join(question.split())}")


class KevFactSheetCheck(FactSheetCheck):
    plugin_kind = "check"
    plugin_type = "kev_facts"

    def __init__(self, ctx: "Context", *, yes_at: dict[str, float] | None = None, no_below: float = 0.5,
                 evidence_method: str = "mask", mask_segments: int = 4, mask_min_drop: float = 0.05,
                 anchor_top: int = 3, **params: Any):
        super().__init__(ctx, **params)
        merged = {**DEFAULT_YES_AT, **{str(k): float(v) for k, v in (yes_at or {}).items()}}
        bad = set(merged) - set(FACT_ROLES)
        if bad:
            raise ValueError(f"yes_at roles {sorted(bad)} not in {FACT_ROLES}")
        if not all(0.0 < float(no_below) <= t <= 1.0 for t in merged.values()):
            raise ValueError(f"need 0 < no_below <= yes_at[role] <= 1, got no_below={no_below}, yes_at={merged}")
        if evidence_method not in EVIDENCE_METHODS:
            raise ValueError(f"evidence_method must be one of {EVIDENCE_METHODS}, got {evidence_method!r}")
        if int(mask_segments) < 1 or int(anchor_top) < 1:
            raise ValueError("mask_segments and anchor_top must be >= 1")
        self.yes_at = merged
        self.no_below = float(no_below)
        self.evidence_method = evidence_method
        self.mask_segments = int(mask_segments)
        self.mask_min_drop = float(mask_min_drop)
        self.anchor_top = int(anchor_top)
        self.params.update(yes_at=merged, no_below=self.no_below, evidence_method=evidence_method,
                           mask_segments=self.mask_segments, mask_min_drop=self.mask_min_drop,
                           anchor_top=self.anchor_top)

    # -- read-out ----------------------------------------------------------------------------------

    def _decide_fact(self, fact: Fact, p: dict[str, float]) -> str:
        y = float(p.get("yes", 0.0))
        if y >= self.yes_at.get(fact.role, 0.5):
            return "yes"
        return "no" if y < self.no_below else "unclear"

    # -- Kev requests ------------------------------------------------------------------------------

    def _batch(self, llm: LLM, state: str, questions: dict[str, str], counts: dict[str, int],
               lock: threading.Lock) -> dict[str, float]:
        key = {"state": stable_hash(state), "questions": questions, "llm": llm.cache_params()}
        hit = self.ctx.cache.get(BATCH_NAMESPACE, key, KevBatch)
        if hit is not None:
            with lock:
                counts["cached_probes"] += 1
            return hit.p
        p, _ = llm.noul_batch(state, questions)  # type: ignore[attr-defined]
        with lock:
            counts["llm_calls"] += 1
        self.ctx.cache.put(BATCH_NAMESPACE, key, KevBatch(p={k: round(float(v), 5) for k, v in p.items()}))
        return p

    def _instructions(self, llm: LLM, rendered: str, family: Family, fact: Fact, lang: str | None,
                      question_fn: Any = None) -> str:
        """What KevLLM sends for this fact prompt (topic line + question), so the whole-call p(yes) of the
        facts step and the masked / anchored requests ask the same thing. ``question_fn`` rewrites the
        question (anchor)."""
        _, question, topic = parse_fact_prompt(self._messages(rendered, family, fact, lang))
        if question_fn is not None:
            question = question_fn(question)
        return f"Topic: {topic}\n{question}" if topic and getattr(llm, "include_topic", True) else question

    def _render(self, transcript: Transcript, keep: list[int]) -> str:
        sub = transcript.model_copy(update={"segments": [transcript.segments[i] for i in keep]})
        return prompts.render_transcript(sub, self.max_transcript_chars)[0]

    # -- passages ----------------------------------------------------------------------------------

    def _evidence(self, llm: LLM, transcript: Transcript, rendered: str, family: Family, ft: FamilyTable,
                  facts: dict[str, dict[str, Any]], fs: FamilyScore, rule_id: str,
                  counts: dict[str, int], lock: threading.Lock) -> list[Finding]:
        if not hasattr(llm, "noul_batch"):
            raise ValueError(f"{self.name}: kev_facts needs a Kev LLM (noul_batch), got {type(llm).__name__}")
        fired = [f for f in ft.facts if facts[f.id]["p"]["yes"] > self.evidence_min]
        segs = transcript.segments
        if not fired or not segs:
            fs.segment_ids = []
            return []
        errors: dict[str, str] = {}
        try:
            if self.evidence_method == "mask":
                found = self._mask(llm, transcript, family, fired, facts, counts, lock)
            else:
                found = self._anchor(llm, transcript, rendered, family, fired, counts, lock)
        except Exception as e:  # a passage failure must not lose the decision
            log.warning("%s: Kev passages for %s failed: %s", self.name, family.id, e)
            found, errors = {}, {f.id: f"{type(e).__name__}: {e}" for f in fired}

        findings: list[Finding] = []
        cited: set[str] = set()
        for fact in fired:
            if fact.id not in found:
                continue
            seg_ids, info = found[fact.id]
            d = facts[fact.id]
            d["evidence"], d["evidence_method"] = seg_ids, self.evidence_method
            d.update(info)
            if fact.role == "exculpatory" or not seg_ids:
                continue
            cited.update(seg_ids)
            head = f"Fakt: {_fmt_fact(fact.label, d['value'], d['p'])}"
            if self.evidence_method == "mask":
                why = f"ohne diese Stelle sinkt p(ja) von {d['p']['yes']:.2f} auf {info['p_without']:.2f}"
            else:
                why = f"Kev: diese Stelle zeigt es (p {info['anchor_p']:.2f})"
            text = f"{head} - {why} (Regel: {rule_id})"
            findings += self.evidence_findings(transcript, family, seg_ids, fs.score, lambda run, t=text: t,
                                               {"fact": fact.id, "role": fact.role, "p_yes": d["p"]["yes"],
                                                "rule": rule_id, "evidence_method": self.evidence_method})
        fs.segment_ids = [s.id for s in segs if s.id in cited]
        if errors:
            fs.detail["evidence_errors"] = errors
        return findings

    def _mask(self, llm: LLM, transcript: Transcript, family: Family, fired: list[Fact],
              facts: dict[str, dict[str, Any]], counts: dict[str, int],
              lock: threading.Lock) -> dict[str, tuple[list[str], dict[str, Any]]]:
        segs = transcript.segments
        wins = windows(len(segs), self.mask_segments)
        lang = transcript.lang
        masked: list[dict[str, float]] = []
        for i, j in wins:
            text = self._render(transcript, [k for k in range(len(segs)) if not i <= k < j])
            qs = {f.id: self._instructions(llm, text, family, f, lang) for f in fired}
            masked.append(self._batch(llm, text, qs, counts, lock))
        out = {}
        for f in fired:
            full = facts[f.id]["p"]["yes"]
            drops = [full - m[f.id] for m in masked]
            best = max(range(len(wins)), key=lambda k: drops[k])
            i, j = wins[best]
            info = {"p_without": round(masked[best][f.id], 4), "drop": round(drops[best], 4)}
            # no window matters (the fact is said several times, or Kev's p(yes) is low anyway): no Kev passage,
            # rather than the first of many equal windows; the other reader's pointing still shows the place
            out[f.id] = ([s.id for s in segs[i:j]] if drops[best] >= self.mask_min_drop else [], info)
        return out

    def _anchor(self, llm: LLM, transcript: Transcript, rendered: str, family: Family, fired: list[Fact],
                counts: dict[str, int], lock: threading.Lock) -> dict[str, tuple[list[str], dict[str, Any]]]:
        segs = transcript.segments
        out = {}
        for f in fired:
            qs = {s.id: self._instructions(llm, rendered, family, f, transcript.lang,
                                           lambda q, sid=s.id: anchor_question(q, sid)) for s in segs}
            p = self._batch(llm, rendered, qs, counts, lock)
            ranked = sorted(segs, key=lambda s: -p[s.id])[:self.anchor_top]
            out[f.id] = ([ranked[0].id], {"anchor_p": round(p[ranked[0].id], 4),
                                          "anchor_ranked": [[s.id, round(p[s.id], 4)] for s in ranked]})
        return out
