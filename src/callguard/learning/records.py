"""Labels from the stored officer judgements: one per call, per passage and per fact (latest wins).

Sources:

* ``feedback.jsonl`` (or ``feedback_demo.jsonl`` for the simulated demo store), schema 1 and 2 items;
* the ``fact_answer`` audit events of the "Offene Fakten" panel (``callguard.ui.panels.facts``): an
  officer answering an open fact *is* a per-fact label (``source: open_facts``; a later
  ``fact_answer_reset`` of the call drops the earlier answers). Real store only.

Each label carries ``use`` (:mod:`callguard.learning.hygiene`) so nobody downstream has to decide again
whether it may be trained on. Pure functions over loaded data, no Streamlit, no model.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Any

from callguard import audit
from callguard import feedback as fb
from callguard.learning import hygiene as hy
from callguard.splits import Splits
from callguard.types import CallResult


@dataclass
class CallLabel:
    call_id: str
    label: str  # officer: alarm / review / no_alert
    system_label: str | None  # what the officer was shown (else the stored decision)
    system_family: str | None
    families: list[str]  # families the officer named (passage / missed category / call item)
    verdict: str
    user: str
    ts: str
    officers: list[str]  # everyone who gave a call verdict
    disagreement: bool  # officers' latest call verdicts differ
    use: str
    source: str
    provenance: dict[str, Any] = field(default_factory=dict)
    call_use: str = ""  # the call's own use, ignoring the demo marker (what calibration may read)

    def row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FactLabel:
    call_id: str
    check: str
    family: str
    fact: str
    fact_label: str
    role: str | None
    question: str | None
    answer: str  # officer: yes / no / unclear
    model_value: str | None
    model_p: dict[str, float] | None
    agrees: bool | None
    rule_id: str | None  # the policy-table rule that fired for this family (system)
    user: str
    ts: str
    source: str  # officer / open_facts / demo
    policy_table_hash: str | None
    use: str

    @property
    def corrected(self) -> bool:
        return self.model_value is not None and self.answer != self.model_value

    def row(self) -> dict[str, Any]:
        return {**asdict(self), "corrected": self.corrected}


@dataclass
class PassageLabel:
    call_id: str
    family: str | None
    start: float | None
    end: float | None
    text: str
    applies: bool
    user: str
    ts: str
    source: str
    use: str

    def row(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------------------------


def _use(cid: str, splits: Splits | None, source: str) -> str:
    return hy.use_of(cid, splits, demo=source == "demo")


def fact_detail(result: CallResult | None, check: str | None, family: str | None, fact: str | None
                ) -> tuple[dict[str, Any], dict[str, Any]]:
    """(stored fact entry, family detail) of the facts check, empty dicts if absent."""
    if result is None or not check or check not in result.checks or not family:
        return {}, {}
    fs = result.checks[check].family_scores.get(family)
    detail = (fs.detail or {}) if fs else {}
    return dict((detail.get("facts") or {}).get(fact or "") or {}), detail


def facts_check_of(result: CallResult | None) -> str | None:
    if result is None:
        return None
    return next((n for n, c in result.checks.items() if c.type == "facts" and not (c.meta or {}).get("error")), None)


def call_labels(items: Sequence[fb.FeedbackItem], results: Mapping[str, CallResult],
                splits: Splits | None) -> dict[str, CallLabel]:
    """call_id -> label, by :func:`callguard.feedback.labels_from_feedback` (same semantics as the
    threshold suggestion), plus who said it and what the system said."""
    stored = {cid: r.decision.label for cid, r in results.items()}
    labels = fb.labels_from_feedback(items, stored)
    by_call: dict[str, list[fb.FeedbackItem]] = {}
    for it in sorted(items, key=lambda i: i.ts):
        by_call.setdefault(it.call_id, []).append(it)
    out: dict[str, CallLabel] = {}
    for cid, lab in labels.items():
        its = by_call[cid]
        deciding = [i for i in its if i.target == "call"] or [i for i in its if i.target in ("passage", "family")]
        last = deciding[-1]
        latest_per_officer: dict[str, str] = {}
        for i in its:
            if i.target == "call":
                latest_per_officer[i.user] = fb.derive_label(i, stored.get(cid)) or ""
        r = results.get(cid)
        fams = sorted({i.family for i in its if i.family and i.target in ("call", "family", "passage")})
        out[cid] = CallLabel(
            call_id=cid, label=lab, system_label=last.label_seen or stored.get(cid),
            system_family=(r.decision.top_family if r else None) or last.provenance.get("decision", {}).get("top_family"),
            families=fams, verdict=last.verdict, user=last.user, ts=last.ts,
            officers=sorted(latest_per_officer), disagreement=len(set(latest_per_officer.values())) > 1,
            use=_use(cid, splits, last.source), source=last.source, provenance=last.provenance,
            call_use=hy.use_of(cid, splits))
    return out


def _open_fact_events(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """``fact_answer`` events still in force (a later ``fact_answer_reset`` of the call drops them)."""
    out: list[dict[str, Any]] = []
    for e in sorted(events, key=lambda e: str(e.get("ts", ""))):
        if e.get("kind") == "fact_answer_reset":
            out = [x for x in out if x.get("call_id") != e.get("call_id")]
        elif e.get("kind") == "fact_answer" and e.get("answer") in fb.FACT_ANSWERS and e.get("fact"):
            out.append(dict(e))
    return out


def fact_labels(items: Sequence[fb.FeedbackItem], results: Mapping[str, CallResult], splits: Splits | None,
                events: Sequence[Mapping[str, Any]] = ()) -> list[FactLabel]:
    """Per (call, family, fact) the latest officer answer, from feedback items and open-fact answers."""
    raw: list[dict[str, Any]] = []
    for i in items:
        if i.target == "fact" and i.answer in fb.FACT_ANSWERS and i.fact and i.family:
            raw.append({"call_id": i.call_id, "check": i.check or facts_check_of(results.get(i.call_id)),
                        "family": i.family, "fact": i.fact, "answer": i.answer, "model_value": i.model_value,
                        "agrees": i.agrees, "question": i.question, "user": i.user, "ts": i.ts, "source": i.source,
                        "policy_table_hash": (i.provenance.get("policy_table") or {}).get("hash")})
    for e in _open_fact_events(events):
        raw.append({"call_id": e["call_id"], "check": e.get("check"), "family": e.get("family"), "fact": e["fact"],
                    "answer": e["answer"], "model_value": e.get("model_value"), "agrees": None, "question": None,
                    "user": e.get("user") or "officer", "ts": str(e.get("ts", "")), "source": "open_facts",
                    "policy_table_hash": e.get("policy_table_hash")})
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for x in sorted(raw, key=lambda x: x["ts"]):
        latest[(x["call_id"], x["family"], x["fact"])] = x
    out = []
    for x in latest.values():
        r = results.get(x["call_id"])
        entry, detail = fact_detail(r, x["check"], x["family"], x["fact"])
        model_value = x["model_value"] if x["model_value"] is not None else entry.get("value")
        agrees = x["agrees"] if x["agrees"] is not None else (None if model_value is None else x["answer"] == model_value)
        out.append(FactLabel(
            call_id=x["call_id"], check=x["check"] or "facts", family=x["family"], fact=x["fact"],
            fact_label=str(entry.get("label") or x["fact"]), role=entry.get("role"),
            question=x["question"] or entry.get("question"), answer=x["answer"], model_value=model_value,
            model_p=entry.get("p"), agrees=agrees, rule_id=(detail.get("rule") or {}).get("id"),
            user=x["user"], ts=x["ts"], source=x["source"], policy_table_hash=x["policy_table_hash"],
            use=_use(x["call_id"], splits, x["source"])))
    return sorted(out, key=lambda f: (f.call_id, f.family, f.fact))


def passage_labels(items: Sequence[fb.FeedbackItem], results: Mapping[str, CallResult],
                   splits: Splits | None) -> list[PassageLabel]:
    """Per (call, passage) the latest trifft zu / trifft nicht zu (schema 1: confirmed / false_alarm on
    a passage count too)."""
    latest: dict[tuple[str, int], fb.FeedbackItem] = {}
    for i in sorted(items, key=lambda i: i.ts):
        if i.target == "passage" and i.passage_index is not None:
            latest[(i.call_id, i.passage_index)] = i
    out = []
    for (cid, idx), i in sorted(latest.items()):
        snap = dict(i.passage or {})
        if not snap:
            r = results.get(cid)
            if r is not None and idx < len(r.decision.passages):
                p = r.decision.passages[idx]
                snap = {"family": p.family, "start": p.start, "end": p.end, "text": p.text}
        out.append(PassageLabel(call_id=cid, family=snap.get("family") or i.family, start=snap.get("start"),
                                end=snap.get("end"), text=str(snap.get("text") or ""),
                                applies=i.verdict not in fb.NEGATIVE, user=i.user, ts=i.ts, source=i.source,
                                use=_use(cid, splits, i.source)))
    return out


def load_events(runs_dir: Any) -> list[dict[str, Any]]:
    return [e for e in audit.read_events(runs_dir) if e.get("kind") in ("fact_answer", "fact_answer_reset")]


@dataclass
class LabelSet:
    store: str
    items: list[fb.FeedbackItem]
    calls: dict[str, CallLabel]
    facts: list[FactLabel]
    passages: list[PassageLabel]


def collect(runs_dir: Any, results: Mapping[str, CallResult], splits: Splits | None, store: str = "real") -> LabelSet:
    items = fb.load(runs_dir, store)
    events = load_events(runs_dir) if store == "real" else []
    return LabelSet(store=store, items=items, calls=call_labels(items, results, splits),
                    facts=fact_labels(items, results, splits, events),
                    passages=passage_labels(items, results, splits))
