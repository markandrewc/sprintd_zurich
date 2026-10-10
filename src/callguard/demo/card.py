"""The decision card of the demo («Anruf prüfen», right column) and the one-liners of the worklist, as data.

For one call under the live decision: the label in plain German, the reason sentence, the rule that fired
(in words: «WENN «Handelswunsch» = ja UND … → ALARM»), the facts the model read with their confidence
(«Eigener Handelswunsch geäussert: ja (0.98)»; the ones the rule used first), the legal basis from the
policy table, for «Prüfen» the open fact («Offen: Wert gehört zum laufenden, gültigen Vorgang?») and for
«Kein Alarm» the answer to «Warum kein Alarm?», including the keyword trap (keywords occur, the facts that
block every alarm rule say why that is harmless).

Results without a facts check (other profiles, test fixtures) fall back to the fusion's own reasons and
:func:`callguard.ui.explain.why_not_alarm`. Pure: no Streamlit; tests/test_demo.py.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from callguard.checks.facts import FamilyTable, PolicyTable, eval_hard, parse_rule, rule_facts
from callguard.learning.records import facts_check_of
from callguard.policy_edit import render_rule
from callguard.types import CallResult, Decision, Family
from callguard.ui import explain as ex
from callguard.ui.backend import headline_reason, short_label, top_family

LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
LABEL_SENTENCE = {"alarm": "Verdacht auf einen Verstoss: bitte anhören und eskalieren, wenn er sich bestätigt.",
                  "review": "Das System entscheidet diesen Anruf nicht allein: ein Mensch muss zuhören.",
                  "no_alert": "Nichts ausreichend Verdächtiges gefunden."}
VALUE_DE = {"yes": "ja", "no": "nein", "unclear": "unklar"}
BASIS_NOTE = "Vorschlag, durch Compliance zu bestätigen"


@dataclass
class FactRow:
    fact: str
    label: str
    value: str  # yes / no / unclear (the model's)
    confidence: float | None  # p of that value
    role: str | None = None
    decisive: bool = False  # used by the rule that fired (or blocks every alarm rule, for "Kein Alarm")
    question: str | None = None

    @property
    def text(self) -> str:
        """«Eigener Handelswunsch geäussert: ja (0.98)»."""
        conf = f" ({self.confidence:.2f})" if self.confidence is not None else ""
        return f"{self.label}: {VALUE_DE.get(self.value, self.value)}{conf}"


@dataclass
class WhyNot:
    summary: str  # one or two plain sentences
    keywords: list[str] = field(default_factory=list)  # keyword hits (the trap)
    blocking: list[FactRow] = field(default_factory=list)  # facts that keep every alarm rule from holding
    rule: str | None = None  # the rule text that decided "kein Alarm"
    harmless_notes: list[str] = field(default_factory=list)  # «harmlos, wenn …» of the keyword list
    lead: str = ""  # the summary without the fact list (the page lists ``blocking`` right below it)

    @property
    def is_trap(self) -> bool:
        return bool(self.keywords)


@dataclass
class Card:
    call_id: str
    label: str
    label_de: str
    sentence: str  # what the label means for the officer
    family: str | None
    family_label: str  # short
    reason: str  # the one sentence why
    score: float
    threshold: float
    uncertainty: float
    rule_id: str | None = None
    rule_plain: str | None = None  # «WENN … → ALARM»
    facts: list[FactRow] = field(default_factory=list)
    basis: str = ""  # legal basis (family + rule), may be empty
    open_facts: list[tuple[str, str]] = field(default_factory=list)  # (label, question) of a review
    open_causes: list[str] = field(default_factory=list)  # review without an open fact: why (fusion)
    why_not: WhyNot | None = None
    passages: int = 0


def plain_question(question: str) -> str:
    """The fact question for the officer: without the answer instructions meant for the model
    («Antworte "unknown", wenn …»)."""

    parts = re.split(r"(?<=[.?!])\s+", (question or "").strip())
    keep = [p for p in parts if not re.match(r"^(Antworte|Answer)\b", p)]
    return " ".join(keep) or (question or "")


def short_basis(basis: str) -> str:
    """«FinfraG Art. 142 (Ausnützen …) – Vorschlag, …» -> «FinfraG Art. 142» for tables."""
    head = basis.split(" – ")[0].strip()
    return head.split(" (")[0].strip() or head


def _family_table(table: PolicyTable | None, family: str | None) -> FamilyTable | None:
    if table is None or not family:
        return None
    return table.families.get(family)


def _rule_basis(ft: FamilyTable | None, rule_id: str | None) -> str:
    if ft is None:
        return ""
    rule = next((r for r in [*ft.rules, *ft.disabled] if r.id == rule_id), None)
    parts = [b for b in (ft.basis, rule.basis if rule else "") if b]
    return " · ".join(dict.fromkeys(parts))


def failing_facts(node: Any, values: Mapping[str, str]) -> list[str]:
    """The facts of the conditions that make ``node`` false: for AND the failing parts, for OR all parts,
    a comparison (or its negation) names its fact. Empty when the node holds."""
    vals = dict(values)
    if eval_hard(node, vals):
        return []
    kind = node[0]
    if kind == "and":
        return [f for child in node[1:] if not eval_hard(child, vals) for f in failing_facts(child, vals)]
    if kind == "or":
        return [f for child in node[1:] for f in failing_facts(child, vals)]
    return list(rule_facts(node))


def blocking_facts(ft: FamilyTable, values: Mapping[str, str]) -> list[str]:
    """Facts whose value keeps the alarm rules of the table from holding (the failing conditions of each
    alarm rule), in table order."""
    out: list[str] = []
    for r in ft.rules:
        if r.label != "alarm":
            continue
        for fid in failing_facts(r.node, values):
            if fid not in out:
                out.append(fid)
    order = [f.id for f in ft.facts]
    return sorted(out, key=lambda f: order.index(f) if f in order else 99)


def fact_rows(detail: Mapping[str, Any], ft: FamilyTable | None, decisive: Sequence[str] = ()) -> list[FactRow]:
    """The stored facts of one family, decisive ones first (each group in table order)."""
    stored = detail.get("facts") or {}
    order = [f.id for f in ft.facts] if ft is not None else list(stored)
    rows = []
    for fid in [*order, *[k for k in stored if k not in order]]:
        e = stored.get(fid)
        if not e:
            continue
        v = str(e.get("value") or "unclear")
        p = (e.get("p") or {}).get(v)
        rows.append(FactRow(fact=fid, label=str(e.get("label") or fid), value=v,
                            confidence=None if p is None else float(p), role=e.get("role"),
                            decisive=fid in decisive, question=e.get("question")))
    return sorted(rows, key=lambda r: not r.decisive)


def _strip_family(reason: str, family_label: str) -> str:
    for prefix in (family_label, short_label(family_label)):
        if prefix and reason.startswith(prefix + ": "):
            return reason[len(prefix) + 2:]
    return reason


def _clean_reason(text: str) -> str:
    """Rule summaries carry «Regel: x. Fakten: …» for the logs; the card shows those separately."""
    return text.split(" Regel: ")[0].strip()


def pick_family(result: CallResult, decision: Decision, families: Sequence[Family],
                can_alarm: set[str] | None, why: Any = None) -> str | None:
    """The family the card is about: the decision's top family, else the one «Warum kein Alarm?» explains,
    else the strongest scored one."""
    if decision.top_family and decision.top_family in decision.families:
        ff = decision.families[decision.top_family]
        if ff.score > 0 or decision.label != "no_alert":
            return decision.top_family
    if why is not None:
        return why.family
    top = top_family(decision, can_alarm)
    return top.family if top else None


def build_card(result: CallResult, decision: Decision, families: Sequence[Family], *,
               table: PolicyTable | None = None, can_alarm: set[str] | None = None,
               weights: Mapping[str, float] | None = None, threshold: float | None = None,
               review_band: float = 0.15, max_uncertainty: float = 0.35,
               open_families: Sequence[Any] | None = None) -> Card:
    """The card for ``result`` under ``decision`` (the live one). ``table``: the policy table the facts check
    read (for rule texts, blocking facts and the legal basis). ``open_families``: the
    :func:`callguard.ui.fact_answers.open_families` of the result (computed by the caller, it reads files)."""
    thr = float(decision.threshold if threshold is None else threshold)
    fam_labels = {f.id: f.label for f in families}
    why_raw = ex.why_not_alarm(result, decision, families, threshold=thr, review_band=review_band,
                               weights=weights) if decision.label != "alarm" else None
    fam = pick_family(result, decision, families, can_alarm, why_raw)
    ff = decision.families.get(fam) if fam else None
    family_label = (ff.label if ff and ff.label else fam_labels.get(fam or "", fam or "")) or ""
    check = facts_check_of(result)
    fs = result.checks[check].family_scores.get(fam) if check and fam else None
    detail = (fs.detail or {}) if fs is not None else {}
    ft = _family_table(table, fam)
    rule = detail.get("rule") if isinstance(detail.get("rule"), dict) else None

    card = Card(call_id=result.call_id, label=decision.label, label_de=LABEL_DE.get(decision.label, decision.label),
                sentence=LABEL_SENTENCE.get(decision.label, ""), family=fam,
                family_label=short_label(family_label) if family_label else "", reason="",
                score=float(decision.score), threshold=thr, uncertainty=float(decision.uncertainty),
                passages=len(decision.passages))

    decisive: list[str] = []
    if rule:
        card.rule_id = rule.get("id")
        when = str(rule.get("when") or "true")
        labels = {k: str((v or {}).get("label") or k) for k, v in (detail.get("facts") or {}).items()}
        card.rule_plain = render_rule({"label": rule.get("label"), "when": when}, labels)
        try:
            decisive = rule_facts(parse_rule(when)) if when.strip().lower() != "true" else []
        except Exception:
            decisive = []
        if not decisive and ft is not None:  # the default rule decided: show what blocked the alarm rules
            values = {k: str((v or {}).get("value") or "unclear") for k, v in (detail.get("facts") or {}).items()}
            decisive = blocking_facts(ft, values)
        card.facts = fact_rows(detail, ft, decisive)
    card.basis = _rule_basis(ft, card.rule_id)

    # the reason sentence: the rule's text, else the most trusted check's own words
    if rule and rule.get("text"):
        card.reason = str(rule["text"]).strip()
    elif fs is not None and fs.reason:
        card.reason = _clean_reason(fs.reason)
    else:
        card.reason = _clean_reason(_strip_family(headline_reason(decision, result, weights, can_alarm),
                                                  family_label))
    if decision.label == "no_alert" and (not card.reason or not fam or card.reason.startswith("Kein Alarm:")):
        card.reason = "Keine Prüfung hat etwas Verdächtiges gefunden."

    if decision.label == "review":
        for of in open_families or []:
            if of.family != fam:
                continue
            for fid in of.facts:
                f = of.table.fact(fid)
                card.open_facts.append((f.label, plain_question(f.question("de"))))
        if not card.open_facts:
            causes = ex.review_causes(result, decision, threshold=thr, review_band=review_band,
                                      max_uncertainty=max_uncertainty, can_alarm=can_alarm, weights=weights)
            card.open_causes = [f"{c.title}: {c.text}" for c in causes]

    if decision.label != "alarm":
        card.why_not = _why_not(result, card, why_raw, ft, detail)
    return card


def _why_not(result: CallResult, card: Card, why: Any, ft: FamilyTable | None,
             detail: Mapping[str, Any]) -> WhyNot | None:
    hits = list(dict.fromkeys(h.phrase for h in (why.hits if why is not None else []) if h.phrase and not h.negated))
    notes = list(why.harmless_notes) if why is not None else []
    blocking = [f for f in card.facts if f.decisive] if card.label == "no_alert" else []
    if card.label == "review" and ft is not None and detail.get("facts"):
        values = {k: str((v or {}).get("value") or "unclear") for k, v in detail["facts"].items()}
        keep = set(blocking_facts(ft, values))
        blocking = [f for f in card.facts if f.fact in keep]
    if not hits and not blocking and why is None:
        if card.label != "no_alert":
            return None
        return WhyNot(summary="Keine Prüfung hat in diesem Gespräch etwas Verdächtiges gefunden.")
    parts = []
    if hits:
        shown = ", ".join(f"«{h}»" for h in hits[:4])
        parts.append(f"Stichwörter wie {shown} kommen vor; ein Stichwort allein ist aber kein Verstoss.")
    lead = " ".join(parts + (["Entscheidend ist, was im Gespräch passiert:"] if blocking else []))
    if blocking:
        parts.append("Entscheidend ist, was im Gespräch passiert: "
                     + "; ".join(f.text for f in blocking[:4]) + ".")
    elif why is not None and why.summary and not card.facts:
        parts.append(why.summary)
    if not parts:
        parts.append("Keine Prüfung hat in diesem Gespräch etwas Verdächtiges gefunden.")
    if card.label == "review":
        parts.append("Für einen Alarm reicht es nicht; ganz entlasten lässt sich der Anruf aber auch nicht.")
    rule = card.reason if card.rule_id else (why.rule.rule if why is not None and why.rule is not None else None)
    if card.label == "review" and blocking:
        lead += " Für einen Alarm reicht es nicht; ganz entlasten lässt sich der Anruf aber auch nicht."
    return WhyNot(summary=" ".join(parts), keywords=hits, blocking=blocking, rule=rule, harmless_notes=notes,
                  lead=lead if blocking else " ".join(parts))


def one_liner(card: Card) -> str:
    """The worklist's «Warum» column."""
    if card.label == "review" and card.open_facts:
        return f"Offen: {card.open_facts[0][0]}"
    if card.label == "no_alert" and card.why_not is not None and card.why_not.is_trap:
        return f"Stichwort-Falle: {', '.join(card.why_not.keywords[:2])} – {card.reason}"
    return card.reason
