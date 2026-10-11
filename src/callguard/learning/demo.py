"""Simulated officer feedback for the demo: what an officer *would* have said on the dev calls, derived
from the case's expected assessment (Sollbewertung). Clearly marked, separate store, never trained on.

* Only **dev** dialogues of config/splits.yaml (never the holdout); calls need a stored result.
* Written to ``runs/<profile>/feedback_demo.jsonl`` with ``source: demo``, user ``Demo (simuliert)`` and
  the comment "Demo-Feedback (simuliert aus Sollbewertung)". :mod:`callguard.feedback` refuses to mix the
  stores and :mod:`callguard.learning.hygiene` makes every demo label ``demo_only``.
* Call verdict: expected alarm -> Verstoss bestätigt, review -> unklar, no_alert -> kein Verstoss.
* Passages: "trifft zu" when the call should be flagged and the passage is of the expected family.
* Missed category: the expected family when the call should be flagged but the system did not show it.
* Facts (the interesting part for "Frage X wird oft korrigiert"): per family of the facts check the
  target label is the expected label for the expected family, else no_alert. If the policy table already
  gives that label with the model's fact values, the facts of the rule that fired are confirmed; if not,
  the smallest change of fact values (one fact, else two; least confident facts first) that makes the
  table give the target label is recorded as the officer's correction. That is a simulation of *a*
  consistent officer, not a measurement.
"""

from __future__ import annotations

import itertools
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from callguard import feedback as fb
from callguard.checks.facts import FamilyTable, load_policy_table, rule_facts
from callguard.data import Call
from callguard.learning.records import facts_check_of
from callguard.splits import Splits
from callguard.types import CallResult

DEMO_USER = "Demo (simuliert)"
CALL_VERDICT = {"alarm": "violation", "review": "unclear", "no_alert": "no_violation"}
VALUES = ("yes", "no", "unclear")


def _label(ft: FamilyTable, values: Mapping[str, str]) -> str:
    rule = ft.decide(dict(values))
    return rule.label if rule else "no_alert"


def minimal_flip(ft: FamilyTable, values: Mapping[str, str], probs: Mapping[str, Mapping[str, float]],
                 target: str, max_changes: int = 2) -> dict[str, str] | None:
    """Fewest fact changes that make the table decide ``target`` (least confident facts tried first)."""
    order = sorted((f.id for f in ft.facts), key=lambda fid: max((probs.get(fid) or {"x": 0.0}).values()))
    for k in range(1, max_changes + 1):
        for facts in itertools.combinations(order, k):
            for alts in itertools.product(*[[v for v in VALUES if v != values.get(fid, "unclear")] for fid in facts]):
                trial = {**values, **dict(zip(facts, alts))}
                if _label(ft, trial) == target:
                    return dict(zip(facts, alts))
    return None


def _fact_items(r: CallResult, exp_label: str, exp_family: str, common: dict[str, Any]) -> list[fb.FeedbackItem]:
    check = facts_check_of(r)
    if check is None:
        return []
    meta = r.checks[check].meta or {}
    try:
        table = load_policy_table(((meta.get("policy_table") or {}).get("path")) or "config/policy_table.yaml")
    except Exception:
        return []
    out: list[fb.FeedbackItem] = []
    for fid, fs in r.checks[check].family_scores.items():
        ft = table.families.get(fid)
        stored = (fs.detail or {}).get("facts") or {}
        if ft is None or not stored:
            continue
        values = {f.id: str((stored.get(f.id) or {}).get("value") or "unclear") for f in ft.facts}
        probs = {f.id: dict((stored.get(f.id) or {}).get("p") or {}) for f in ft.facts}
        target = exp_label if fid == exp_family else "no_alert"
        system = _label(ft, values)
        if system == target and system == "no_alert" and fid != exp_family:
            continue  # quiet family the officer had no reason to look at
        flips = {} if system == target else minimal_flip(ft, values, probs, target)
        if flips is None:
            continue
        final = {**values, **flips}
        fired = ft.decide(final)
        judged = list(dict.fromkeys([*flips, *(rule_facts(fired.node) if fired else [])]))
        for fact_id in judged:
            if fact_id not in values:
                continue
            entry = stored.get(fact_id) or {}
            out.append(fb.FeedbackItem(verdict="fact", check=check, family=fid, fact=fact_id,
                                       question=entry.get("question"), answer=final[fact_id],
                                       model_value=values[fact_id], agrees=final[fact_id] == values[fact_id],
                                       **common))
    return out


def simulate(results: Mapping[str, CallResult], calls: Sequence[Call], splits: Splits) -> list[fb.FeedbackItem]:
    dev = set(splits.dev_dialogues())
    gt = {c.call_id: c for c in calls if c.expected and c.dialogue_id in dev}
    items: list[fb.FeedbackItem] = []
    for cid in sorted(results):
        c = gt.get(cid)
        if c is None:
            continue
        r, exp = results[cid], c.expected
        assert exp is not None
        d = r.decision
        common = dict(call_id=cid, user=DEMO_USER, label_seen=d.label, threshold_seen=d.threshold, schema_version=2,
                      batch=fb.new_batch(), provenance=fb.provenance_of(r), source="demo", comment=fb.DEMO_NOTE)
        items.append(fb.FeedbackItem(verdict=CALL_VERDICT[exp.label],
                                     family=exp.family if exp.label != "no_alert" else None, **common))
        flag = exp.label in fb.FLAG
        for idx, p in enumerate(d.passages):
            items.append(fb.FeedbackItem(
                verdict="applies" if flag and p.family == exp.family else "not_applies", family=p.family,
                passage_index=idx, passage={"family": p.family, "start": p.start, "end": p.end, "text": p.text},
                **common))
        shown = {p.family for p in d.passages} | ({d.top_family} if d.label != "no_alert" and d.top_family else set())
        if flag and exp.family not in shown:
            items.append(fb.FeedbackItem(verdict="missed_family", family=exp.family, **common))
        items += _fact_items(r, exp.label, exp.family, common)
    return items


def seed(runs_dir: str | Path, results: Mapping[str, CallResult], calls: Sequence[Call], splits: Splits) -> int:
    """(Re)write the demo store; returns the number of items. The real store is never touched."""
    items = simulate(results, calls, splits)
    p = fb.feedback_path(runs_dir, "demo")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.unlink(missing_ok=True)
    fb.add_many(runs_dir, items, store="demo")
    return len(items)


def clear(runs_dir: str | Path) -> None:
    fb.feedback_path(runs_dir, "demo").unlink(missing_ok=True)
