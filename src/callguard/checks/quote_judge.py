"""Quote-grounded LLM judge (research idea N3): no verified quote, no "present".

Like ``llm_judge``, but the model must back its verdict with verbatim ``quotes`` (each at most
``max_quote_words`` words) plus the segment id each quote comes from. Code checks every quote against
the transcript of the same view (rapidfuzz ``partial_ratio`` on folded text >= ``min_ratio``, first on
the cited segment and its neighbours, then anywhere in the call). A "present" sample with zero verified
quotes is downgraded to "undetermined" (probability 0.5, i.e. the score is capped at 0.5) and the reason
says so. Verified quotes become the findings, pinned to the segments where they were actually found, so
every alarm comes with a passage the officer can listen to.

Why: 7B judges primed with long criteria produce plausible but ungrounded "present" answers; the jury
asks for passage + criterion for every hit anyway. Risk: noisy ASR text can make correct quotes fail;
``min_ratio`` (default 85) can be lowered for noisy views - measure the false-rejection rate on alarms.
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import TYPE_CHECKING, Any

from rapidfuzz import fuzz

from callguard.checks import prompts, window_prompts
from callguard.checks.llm_judge import RETRY_TEMPERATURE, LLMJudgeCheck, aggregate_samples, sample_probability
from callguard.checks.textnorm import normalize
from callguard.plugins import LLM
from callguard.types import CheckResult, Family, FamilyScore, Finding, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.quote_judge")

MIN_QUOTE_CHARS = 8  # shorter quotes ("ja", "PIN") match almost anywhere: never count as proof
DOWNGRADE_NOTE = "Kein Zitat im Transkript verifiziert: «vorhanden» herabgestuft auf «unbestimmt»."


def verify_quote(quote: str, cited: str | None, transcript: Transcript, min_ratio: float,
                 max_words: int) -> dict[str, Any]:
    """-> {quote, segment_id (cited), verified, ratio, found_in (segment ids), where, truncated}."""
    words = str(quote or "").split()
    truncated = len(words) > max_words
    q = " ".join(words[:max_words])
    out: dict[str, Any] = {"quote": q, "segment_id": cited, "verified": False, "ratio": 0.0, "found_in": [],
                           "where": None}
    if truncated:
        out["truncated"] = True
    qn = normalize(q)
    if len(qn) < MIN_QUOTE_CHARS:
        out["where"] = "too_short"
        return out
    segs = transcript.segments
    norm = [normalize(s.text) for s in segs]
    order = {s.id: i for i, s in enumerate(segs)}

    def score_at(i: int) -> tuple[float, list[str]]:
        """Best match of the quote in segment i or in i joined with a neighbour (quotes may cross a
        segment boundary). The target is never shorter than the quote, so a long invented quote that
        merely contains the segment text cannot pass."""
        best, ids = 0.0, [segs[i].id]
        for lo, hi in ((i, i), (i - 1, i), (i, i + 1)):
            if lo < 0 or hi >= len(segs):
                continue
            target = " ".join(norm[lo:hi + 1])
            if not target:
                continue
            r = fuzz.partial_ratio(qn, target) if len(qn) <= len(target) else fuzz.ratio(qn, target)
            if r > best + 1e-9:
                best, ids = r, [segs[j].id for j in range(lo, hi + 1)]
        return best, ids

    cited_ids = prompts.clean_evidence([cited], transcript) if cited else []
    if cited_ids:
        r, ids = score_at(order[cited_ids[0]])
        out["ratio"] = round(r, 1)
        if r >= min_ratio:
            out.update(verified=True, found_in=ids, where="cited")
            return out
    best, best_ids = 0.0, []
    for i in range(len(segs)):
        r, ids = score_at(i)
        if r > best:
            best, best_ids = r, ids
    if best >= min_ratio:
        out.update(verified=True, ratio=round(best, 1), found_in=best_ids, where="elsewhere")
    else:
        out["ratio"] = max(out["ratio"], round(best, 1))
        out["where"] = "not_found"
    return out


class QuoteJudgeCheck(LLMJudgeCheck):
    plugin_kind = "check"
    plugin_type = "quote_judge"

    def __init__(self, ctx: "Context", *, min_ratio: float = 85, max_quote_words: int = 25,
                 max_quotes: int = 3, **params: Any):
        if not 0 < float(min_ratio) <= 100:
            raise ValueError(f"min_ratio must be in (0, 100], got {min_ratio}")
        if int(max_quote_words) < 3 or int(max_quotes) < 1:
            raise ValueError("max_quote_words must be >= 3 and max_quotes >= 1")
        super().__init__(ctx, **params)
        self.params.update(min_ratio=min_ratio, max_quote_words=max_quote_words, max_quotes=max_quotes)
        self.min_ratio = float(min_ratio)
        self.max_quote_words = int(max_quote_words)
        self.max_quotes = int(max_quotes)

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        key = super().cache_key(families)
        key["window_prompt_version"] = window_prompts.PROMPT_VERSION
        return key

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        result = super().run(transcript, families)
        result.meta["window_prompt_version"] = window_prompts.PROMPT_VERSION
        calls = sum(int(fs.detail.get("llm_calls") or 1) for fs in result.family_scores.values())
        result.meta["llm_calls"] = calls + len(result.meta.get("errors") or {})
        quotes = [q for fs in result.family_scores.values() for s in fs.detail.get("samples") or []
                  for q in s.get("quotes") or []]
        result.meta["quotes"] = {"total": len(quotes), "verified": sum(q["verified"] for q in quotes)}
        return result

    def _ask(self, llm: LLM, messages: list[dict[str, str]], transcript: Transcript,
             temperature: float) -> tuple[list[dict[str, Any]], list[str]]:
        raws = llm.chat(messages, temperature=temperature, max_tokens=self.max_tokens, n=self.samples,
                        json_schema=window_prompts.quote_judge_schema(self.max_quotes))
        samples, invalid = [], []
        for raw in raws or []:
            obj = prompts.parse_json_object(raw)
            verdict = prompts.parse_verdict(obj.get("verdict")) if obj else None
            if verdict is None:
                invalid.append(str(raw)[:500])
                continue
            conf = prompts.parse_confidence(obj.get("confidence"))
            raw_quotes = obj.get("quotes") if isinstance(obj.get("quotes"), list) else []
            quotes = []
            for q in raw_quotes[:self.max_quotes]:
                if isinstance(q, dict):
                    text = q.get("quote") or q.get("text") or ""
                    sid = q.get("segment_id") or q.get("segment") or q.get("id")
                else:
                    text, sid = str(q), None
                if str(text).strip():
                    quotes.append(verify_quote(str(text), str(sid) if sid is not None else None, transcript,
                                               self.min_ratio, self.max_quote_words))
            verified = [q for q in quotes if q["verified"]]
            reason = prompts.clean_reason(obj.get("reason"))
            sample: dict[str, Any] = {"verdict": verdict, "confidence": round(conf, 4),
                                      "p": round(sample_probability(verdict, conf), 4), "reason": reason,
                                      "quotes": quotes,
                                      "evidence": prompts.clean_evidence([s for q in verified for s in q["found_in"]],
                                                                         transcript)}
            if verdict == "present" and not verified:
                sample.update(verdict="undetermined", downgraded=True, p=min(sample["p"], 0.5),
                              reason=f"{reason} [{DOWNGRADE_NOTE}]".strip())
            samples.append(sample)
        return samples, invalid

    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        messages = window_prompts.quote_judge_messages(
            family, rendered, self.reason_language, example_id=transcript.segments[0].id,
            max_quotes=self.max_quotes, max_quote_words=self.max_quote_words, transcript_lang=transcript.lang)
        calls = 1
        samples, invalid = self._ask(llm, messages, transcript, self.temperature)
        retried = False
        if not samples:
            retried, calls = True, 2
            log.warning("%s: unparseable answer for %s, retrying once", self.name, family.id)
            samples, invalid2 = self._ask(llm, messages, transcript, max(self.temperature, RETRY_TEMPERATURE))
            invalid += invalid2
        if not samples:
            first = invalid[0][:200] if invalid else "<no completion>"
            raise ValueError(f"no valid judge answer after retry; first output: {first!r}")

        score, verdict, confidence, majority = aggregate_samples(samples)
        by_conf = sorted(majority, key=lambda i: -samples[i]["confidence"])
        cited = {sid for i in majority for sid in samples[i]["evidence"]}
        seg_ids = [s.id for s in transcript.segments if s.id in cited]
        downgraded = sum(1 for s in samples if s.get("downgraded"))
        detail: dict[str, Any] = {"samples": samples, "votes": dict(Counter(s["verdict"] for s in samples)),
                                  "llm_calls": calls, "downgraded": downgraded,
                                  "verified_quotes": sum(q["verified"] for s in samples for q in s["quotes"])}
        if invalid:
            detail["invalid"] = invalid
        if retried:
            detail["retried"] = True
        fs = FamilyScore(score=round(score, 4), confidence=round(confidence, 4), verdict=verdict,
                         reason=samples[by_conf[0]]["reason"], segment_ids=seg_ids, detail=detail)

        findings: list[Finding] = []
        if verdict in ("present", "undetermined") and seg_ids:
            def reason_for(run: list[str]) -> str:
                for i in by_conf:
                    qs = [q["quote"] for q in samples[i]["quotes"] if q["verified"] and set(q["found_in"]) & set(run)]
                    if qs:
                        return f"{samples[i]['reason']} «{qs[0]}»"
                return samples[by_conf[0]]["reason"]

            findings = self.evidence_findings(transcript, family, seg_ids, fs.score, reason_for,
                                              {"verdict": verdict, "confidence": fs.confidence, "grounded": True})
        return fs, findings
