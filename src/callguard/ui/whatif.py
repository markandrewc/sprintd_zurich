"""What-if for the policy table (UI page "Regelwerk"): apply a draft table to the STORED results of the
processed calls before anything is saved. Pure (no Streamlit), unit-tested.

The ``facts`` check stores, per call and family, every fact's probabilities, its yes / no / unclear value
and the question it asked. A draft that only changes rules (conditions, order, labels, on/off) re-decides
every call instantly from those stored values with the check's own rule evaluator
(:func:`callguard.checks.facts.decide_family`, no LLM). A NEW fact, or a fact whose question (in the
language the model reads, ``question_lang``) changed, has no valid stored answer: :func:`probe_tasks` lists
them, :func:`run_probes` asks the configured LLM for exactly those (the facts check's own probe, cached
per prompt, so the next real run reuses them), and until then such a fact counts as ``unclear`` and the
preview says so. The call-level label comes from the caller's fusion (``decide``: the live sidebar knobs).
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from callguard.checks import prompts
from callguard.checks.facts import FamilyDecision, FamilyTable, PolicyTable, decide_family, discretize, eval_hard
from callguard.types import CallResult, FamilyScore

FLAGGED = ("alarm", "review")
Key = tuple[str, str, str]  # (call_id, family, fact id)


def facts_check_name(result: CallResult) -> str | None:
    return next((n for n, cr in result.checks.items() if cr.type == "facts" and not (cr.meta or {}).get("error")),
                None)


def _norm(text: Any) -> str:
    return " ".join(str(text or "").split())


def stale_facts(ft: FamilyTable, detail: dict[str, Any], lang: str) -> list[str]:
    """Facts of the (draft) family without a valid stored answer: missing, or asked with another question.
    Results that did not store the question (old runs, fixtures) count as asked with the same one."""
    stored = detail.get("facts") or {}
    out = []
    for f in ft.facts:
        d = stored.get(f.id)
        if d is None or (d.get("question") and _norm(d["question"]) != _norm(f.question(lang))):
            out.append(f.id)
    return out


def probe_tasks(results: dict[str, CallResult], table: PolicyTable, lang: str,
                new_families: set[str] | None = None) -> list[Key]:
    """(call, family, fact) for every fact answer the draft needs and the stored results do not have.
    ``new_families``: Prüfarten of the draft that no stored run knows yet: every fact of theirs is needed."""
    out: list[Key] = []
    for cid, r in results.items():
        check = facts_check_name(r)
        if check is None:
            continue
        stored = r.checks[check].family_scores
        for fam, fs in stored.items():
            ft = table.families.get(fam)
            if ft is not None and (fs.detail or {}).get("facts") is not None:
                out += [(cid, fam, fid) for fid in stale_facts(ft, fs.detail, lang)]
        for fam in sorted((new_families or set()) - set(stored)):
            if fam in table.families:
                out += [(cid, fam, f.id) for f in table.families[fam].facts]
    return out


def family_inputs(ft: FamilyTable, detail: dict[str, Any], lang: str | None, probes: dict[str, dict[str, float]],
                  decide: Callable[[dict[str, float]], str] = discretize
                  ) -> tuple[dict[str, str], dict[str, dict[str, float]], list[str]]:
    """Fact values / probabilities for one family: fresh probes first, then stored answers that are still
    valid; anything else is unclear (returned as the third element). ``lang=None``: no staleness check."""
    stored = detail.get("facts") or {}
    stale = set(stale_facts(ft, detail, lang)) if lang else {f.id for f in ft.facts if f.id not in stored}
    values: dict[str, str] = {}
    probs: dict[str, dict[str, float]] = {}
    unresolved: list[str] = []
    for f in ft.facts:
        if f.id in probes:
            probs[f.id] = dict(probes[f.id])
            values[f.id] = decide(probs[f.id])
        elif f.id not in stale:
            d = stored[f.id]
            probs[f.id] = dict(d.get("p") or {"unclear": 1.0})
            values[f.id] = str(d.get("value") or decide(probs[f.id]))
        else:
            probs[f.id], values[f.id] = {"unclear": 1.0}, "unclear"
            unresolved.append(f.id)
    return values, probs, unresolved


def _family_score(fs: FamilyScore, fd: FamilyDecision, values: dict[str, str], probs: dict[str, dict[str, float]],
                  ft: FamilyTable) -> FamilyScore:
    detail = dict(fs.detail or {})
    old = detail.get("facts") or {}
    detail["facts"] = {f.id: {**(old.get(f.id) or {}), "label": f.label, "role": f.role, "value": values[f.id],
                              "p": probs[f.id]} for f in ft.facts}
    r = fd.rule
    detail.update(decision=fd.label, summary=fd.summary, rule_probs=fd.soft, p_alarm=round(fd.p_alarm, 4),
                  p_review=round(fd.p_review, 4),
                  rule=({"id": r.id, "label": r.label, "when": r.when, "text": r.text} if r
                        else {"id": None, "label": "no_alert", "when": None, "text": "keine Regel trifft zu"}))
    return fs.model_copy(update={"score": round(min(1.0, max(0.0, fd.score)), 4),
                                 "confidence": round(min(1.0, fd.confidence), 4), "verdict": fd.verdict,
                                 "reason": fd.summary, "detail": detail})


@dataclass
class FamilyOutcome:
    label: str
    rule: str | None
    unresolved: list[str] = field(default_factory=list)
    values: dict[str, str] = field(default_factory=dict)


def redecide_result(result: CallResult, table: PolicyTable, params: dict[str, float] | None = None,
                    probes: dict[Key, dict[str, float]] | None = None, lang: str | None = None,
                    decide: Callable[[dict[str, float]], str] = discretize
                    ) -> tuple[CallResult, dict[str, FamilyOutcome]]:
    """A copy of the call whose facts check is re-decided with ``table`` (no LLM)."""
    check = facts_check_name(result)
    if check is None:
        return result, {}
    cr = result.checks[check]
    fss = dict(cr.family_scores)
    outcomes: dict[str, FamilyOutcome] = {}
    probed = {f for (cid, f, _) in (probes or {}) if cid == result.call_id}
    # a Prüfart the stored run did not know: decided only once some of its facts were asked (else no entry)
    fresh = {fam: FamilyScore(score=0.0, confidence=0.0, detail={"facts": {}, "new_family": True})
             for fam in sorted(probed - set(cr.family_scores)) if fam in table.families}
    for fam, fs in [*cr.family_scores.items(), *fresh.items()]:
        ft = table.families.get(fam)
        if ft is None or (fs.detail or {}).get("facts") is None:
            continue
        mine = {fid: p for (cid, f, fid), p in (probes or {}).items() if cid == result.call_id and f == fam}
        values, probs, unresolved = family_inputs(ft, fs.detail, lang, mine, decide)
        fd = decide_family(ft, values, probs, **(params or {}))
        fss[fam] = _family_score(fs, fd, values, probs, ft)
        outcomes[fam] = FamilyOutcome(fd.label, fd.rule.id if fd.rule else None, unresolved, values)
    checks = {**result.checks, check: cr.model_copy(update={"family_scores": fss})}
    return result.model_copy(update={"checks": checks}), outcomes


@dataclass
class CallPreview:
    call_id: str
    before: str
    after: str
    score_before: float
    score_after: float
    families_before: dict[str, FamilyOutcome]
    families_after: dict[str, FamilyOutcome]

    @property
    def changed(self) -> bool:
        return self.before != self.after

    def changed_families(self) -> list[str]:
        return [f for f, a in self.families_after.items()
                if (b := self.families_before.get(f)) is None or (b.label, b.rule) != (a.label, a.rule)]


@dataclass
class Preview:
    calls: list[CallPreview]
    rule_hits: dict[str, dict[str, int]]  # family -> rule id -> calls where it decided (draft table)
    cond_hits: dict[str, dict[str, int]]  # family -> disabled rule id -> calls where its condition holds
    n_calls: int  # calls with a facts check result
    unresolved: dict[tuple[str, str], int]  # (family, fact) -> calls where the draft needs a new answer
    errors: list[str] = field(default_factory=list)

    @property
    def changed(self) -> list[CallPreview]:
        return [c for c in self.calls if c.changed]

    def family_calls(self, family: str) -> int:
        return sum(1 for c in self.calls if family in c.families_after)


def preview(results: dict[str, CallResult], active: PolicyTable, draft: PolicyTable,
            decide_call: Callable[[CallResult], Any], params: dict[str, float] | None = None,
            probes: dict[Key, dict[str, float]] | None = None, lang: str = "en",
            decide: Callable[[dict[str, float]], str] = discretize,
            decide_after: Callable[[CallResult], Any] | None = None) -> Preview:
    """Every call decided with the active table and with the draft. ``decide_call`` is the fusion now;
    ``decide_after`` the fusion under the draft's switches (Prüfarten / kinds of check on or off), default
    the same."""
    calls: list[CallPreview] = []
    hits: dict[str, dict[str, int]] = {}
    cond: dict[str, dict[str, int]] = {}
    unresolved: dict[tuple[str, str], int] = {}
    errors: list[str] = []
    for cid, r in sorted(results.items()):
        if facts_check_name(r) is None:
            continue
        try:
            rb, ob = redecide_result(r, active, params, None, None, decide)
            ra, oa = redecide_result(r, draft, params, probes, lang, decide)
            db, da = decide_call(rb), (decide_after or decide_call)(ra)
        except Exception as e:  # one broken result must not hide the preview of the others
            errors.append(f"{cid}: {type(e).__name__}: {e}")
            continue
        calls.append(CallPreview(cid, db.label, da.label, float(db.score), float(da.score), ob, oa))
        for fam, o in oa.items():
            if o.rule:
                hits.setdefault(fam, {}).setdefault(o.rule, 0)
                hits[fam][o.rule] += 1
            for fid in o.unresolved:
                unresolved[(fam, fid)] = unresolved.get((fam, fid), 0) + 1
            for rule in draft.families[fam].disabled:
                if eval_hard(rule.node, o.values):
                    cond.setdefault(fam, {}).setdefault(rule.id, 0)
                    cond[fam][rule.id] += 1
    return Preview(calls, hits, cond, len(calls), unresolved, errors)


def label_effect(calls: list[CallPreview], truth: dict[str, str]) -> dict[str, int]:
    """Against expected labels (evaluation only): flagged = alarm or review, as on the quality page."""
    out = {"n": 0, "hits_before": 0, "hits_after": 0, "false_before": 0, "false_after": 0,
           "exact_before": 0, "exact_after": 0}
    for c in calls:
        t = truth.get(c.call_id)
        if t is None:
            continue
        out["n"] += 1
        for when, label in (("before", c.before), ("after", c.after)):
            flagged = label in FLAGGED
            out[f"hits_{when}"] += int(flagged and t in FLAGGED)
            out[f"false_{when}"] += int(flagged and t not in FLAGGED)
            out[f"exact_{when}"] += int(label == t)
    return out


# --------------------------------------------------------------------------------------------
# new fact answers through the configured LLM
# --------------------------------------------------------------------------------------------


def seconds_per_probe(results: dict[str, CallResult], default: float = 0.5) -> float:
    """Measured wall seconds per LLM call of the facts check in the stored runs (rough, honest estimate)."""
    secs = calls = 0.0
    for r in results.values():
        check = facts_check_name(r)
        meta = (r.checks[check].meta or {}) if check else {}
        if int(meta.get("llm_calls") or 0) > 0 and meta.get("seconds"):
            secs += float(meta["seconds"])
            calls += int(meta["llm_calls"])
    return secs / calls if calls >= 3 else default


class ProbeUnavailable(RuntimeError):
    """The LLM could not answer (unreachable, no facts check configured...)."""


def run_probes(check: Any, results: dict[str, CallResult], table: PolicyTable, tasks: list[Key],
               families: dict[str, Any], view_of: Callable[[CallResult], Any],
               progress: Callable[[int, int], None] | None = None) -> tuple[dict[Key, dict[str, float]], list[str]]:
    """Ask the facts check's LLM for the listed fact answers (draft wording). Returns (probes, errors).
    Raises ProbeUnavailable when the very first answer fails (server down): nothing is half-done then."""
    if check is None or not hasattr(check, "probe"):
        raise ProbeUnavailable("keine Fakten-Prüfung (facts) im Profil")
    try:
        llm = check.ctx.llm(check.llm_name)
    except Exception as e:
        raise ProbeUnavailable(f"LLM nicht verfügbar: {e}") from e
    counts = {"llm_calls": 0, "cached_probes": 0}
    lock = threading.Lock()
    rendered: dict[str, tuple[str, str | None]] = {}

    def render(cid: str) -> tuple[str, str | None]:
        if cid not in rendered:
            t = view_of(results[cid])
            if not getattr(check, "roles", True):
                t = t.model_copy(update={"segments": [s.model_copy(update={"role": "unknown"}) for s in t.segments]})
            rendered[cid] = (prompts.render_transcript(t, check.max_transcript_chars)[0], t.lang)
        return rendered[cid]

    def one(task: Key) -> dict[str, float]:
        cid, fam, fid = task
        text, lang = render(cid)
        fact = table.families[fam].fact(fid)
        return dict(check.probe(llm, check._messages(text, families[fam], fact, lang), counts, lock).p)

    out: dict[Key, dict[str, float]] = {}
    errors: list[str] = []
    if not tasks:
        return out, errors
    try:
        out[tasks[0]] = one(tasks[0])
    except Exception as e:
        raise ProbeUnavailable(f"{type(e).__name__}: {e}") from e
    if progress:
        progress(1, len(tasks))
    rest = tasks[1:]
    with ThreadPoolExecutor(max_workers=max(1, int(getattr(check, "parallel", 1) or 1))) as ex:
        futs = {ex.submit(one, t): t for t in rest}
        for i, fut in enumerate(as_completed(futs), 2):
            t = futs[fut]
            try:
                out[t] = fut.result()
            except Exception as e:
                errors.append(f"{t[0]} {t[1]}.{t[2]}: {type(e).__name__}: {e}")
            if progress:
                progress(i, len(tasks))
    return out, errors
