"""Officer answers to open facts (research/ideas_round3.md S6). Pure (no Streamlit), unit-tested.

The ``facts`` check stores, per family, every fact's value (yes / no / unclear) and probabilities plus the
policy-table rule that fired. A fact is *open* when the model left it ``unclear`` and a ``yes`` or ``no``
would change the family's label (e.g. C17: "gehört der Wert zum laufenden, gültigen Vorgang?" = unclear
blocks ``access.alarm_1``), or, failing that, when it is a non-act fact of the review rule that fired.

The officer answers Ja / Nein / Weiss nicht. :func:`apply_answers` replaces the model's value with the
answer (probability 1.0; ``config/open_facts.yaml`` may say that an answer settles further facts too),
and :func:`redecide_family` re-reads the policy table with ``checks.facts.decide_family``: the same rule
evaluator and score formula as the check, no LLM. :func:`override_result` puts the new family scores into
a copy of the call, which the UI then re-fuses with the live threshold.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from callguard.checks.facts import (
    FactSheetCheck,
    FamilyDecision,
    FamilyTable,
    PolicyTable,
    decide_family,
    load_policy_table,
    rule_facts,
)
from callguard.config import ROOT
from callguard.types import CallResult, FamilyScore

ANSWERS = ("yes", "no", "unclear")
ANSWER_DE = {"yes": "Ja", "no": "Nein", "unclear": "Weiss nicht"}
VALUE_DE = {"yes": "ja", "no": "nein", "unclear": "unklar"}
OPTIONS_FILE = "config/open_facts.yaml"
SCORE_PARAMS = ("alarm_base", "review_score", "review_confidence", "no_alert_scale")
_YAML_BOOL = {True: "yes", False: "no"}  # unquoted yes/no keys are booleans in YAML 1.1


@dataclass
class AnswerOption:
    answer: str  # yes | no | unclear
    label: str  # button text
    also: dict[str, str] = field(default_factory=dict)  # further facts this answer settles


def _norm_value(v: Any) -> str | None:
    v = _YAML_BOOL.get(v, v) if isinstance(v, bool) else v
    v = str(v).strip().lower() if v is not None else None
    return {"ja": "yes", "nein": "no", "unklar": "unclear", "unknown": "unclear"}.get(v, v) if v else None


def load_options(path: str | Path | None = None) -> dict[str, dict[str, dict[str, AnswerOption]]]:
    """family -> fact -> answer -> option, from ``config/open_facts.yaml`` (missing file: defaults only)."""
    p = Path(path or OPTIONS_FILE)
    p = p if p.is_absolute() else ROOT / p
    try:
        raw = yaml.safe_load(p.read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}
    out: dict[str, dict[str, dict[str, AnswerOption]]] = {}
    for fam, facts in (raw.get("families") or {}).items() if isinstance(raw, dict) else []:
        for fact, answers in (facts or {}).items():
            for ans, spec in (answers or {}).items():
                a = _norm_value(ans)
                if a not in ANSWERS or not isinstance(spec, dict):
                    continue
                also = {str(k): v for k, v in ((k, _norm_value(v)) for k, v in (spec.get("also") or {}).items())
                        if v in ANSWERS}
                out.setdefault(str(fam), {}).setdefault(str(fact), {})[a] = AnswerOption(
                    a, str(spec.get("label") or ANSWER_DE[a]), also)
    return out


def options_for(family: str, fact: str, options: dict | None = None) -> list[AnswerOption]:
    """The three buttons for one fact: configured labels / implications, else Ja / Nein / Weiss nicht."""
    conf = (options or {}).get(family, {}).get(fact, {})
    return [conf.get(a) or AnswerOption(a, ANSWER_DE[a]) for a in ANSWERS]


# --------------------------------------------------------------------------------------------
# which facts are open
# --------------------------------------------------------------------------------------------


def model_values(ft: FamilyTable, detail: dict[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, float]]]:
    """The model's fact values and probabilities as stored by the check (missing fact = unclear)."""
    stored = detail.get("facts") or {}
    values = {f.id: str((stored.get(f.id) or {}).get("value") or "unclear") for f in ft.facts}
    probs = {f.id: dict((stored.get(f.id) or {}).get("p") or {"unclear": 1.0}) for f in ft.facts}
    return values, probs


def _label(ft: FamilyTable, values: dict[str, str]) -> str:
    rule = ft.decide(values)
    return rule.label if rule else "no_alert"


def open_facts(ft: FamilyTable, values: dict[str, str]) -> list[str]:
    """Facts the officer can settle: ``unclear`` facts of the rules up to the one that fired whose ``yes``
    or ``no`` changes the label; for a review without such a fact, the non-act facts of that rule."""
    fired = ft.decide(values)
    label = fired.label if fired else "no_alert"
    upto = ft.rules[: ft.rules.index(fired) + 1] if fired else ft.rules
    seen: list[str] = []
    for r in upto:
        for fid in rule_facts(r.node):
            if fid not in seen and values.get(fid, "unclear") == "unclear":
                seen.append(fid)
    out = [fid for fid in seen if any(_label(ft, {**values, fid: v}) != label for v in ("yes", "no"))]
    if not out and label == "review" and fired is not None:
        out = [fid for fid in rule_facts(fired.node) if ft.fact(fid).role != "act"]
    return out


def could_alarm(ft: FamilyTable, values: dict[str, str], facts: list[str]) -> bool:
    return any(_label(ft, {**values, fid: v}) == "alarm" for fid in facts for v in ("yes", "no"))


@dataclass
class OpenFamily:
    check: str  # name of the facts check in result.checks
    family: str
    table: FamilyTable
    values: dict[str, str]  # the model's
    probs: dict[str, dict[str, float]]
    label: str  # the model's family label (policy table, current version)
    rule_id: str | None
    facts: list[str]  # open fact ids


def facts_checks(result: CallResult) -> list[str]:
    return [name for name, cr in result.checks.items() if cr.type == "facts" and not cr.meta.get("error")]


def table_of(result: CallResult, check: str) -> PolicyTable:
    path = ((result.checks[check].meta or {}).get("policy_table") or {}).get("path") or "config/policy_table.yaml"
    return load_policy_table(path)


def open_families(result: CallResult) -> list[OpenFamily]:
    """Families of the facts check(s) that went to review, or that one open fact could turn into an alarm."""
    out: list[OpenFamily] = []
    for name in facts_checks(result):
        try:
            table = table_of(result, name)
        except Exception:
            continue
        for fid, fs in result.checks[name].family_scores.items():
            ft = table.families.get(fid)
            if ft is None or not (fs.detail or {}).get("facts"):
                continue
            values, probs = model_values(ft, fs.detail)
            facts = open_facts(ft, values)
            label = _label(ft, values)
            if facts and (label == "review" or could_alarm(ft, values, facts)):
                rule = ft.decide(values)
                out.append(OpenFamily(name, fid, ft, values, probs, label, rule.id if rule else None, facts))
    return out


# --------------------------------------------------------------------------------------------
# answering
# --------------------------------------------------------------------------------------------


def apply_answers(ft: FamilyTable, values: dict[str, str], probs: dict[str, dict[str, float]],
                  answers: dict[str, str], options: dict | None = None
                  ) -> tuple[dict[str, str], dict[str, dict[str, float]]]:
    """Values / probabilities with the officer's answers in place (certain: p = 1.0). An answer may settle
    further facts (``also`` in config/open_facts.yaml); a direct answer to such a fact wins."""
    v, p = dict(values), {k: dict(x) for k, x in probs.items()}
    known = {f.id for f in ft.facts}
    implied: dict[str, str] = {}
    for fact, ans in answers.items():
        conf = (options or {}).get(ft.family, {}).get(fact, {}).get(ans)
        if conf is not None:
            implied.update(conf.also)
    for fact, ans in {**implied, **answers}.items():
        if fact in known and ans in ANSWERS:
            v[fact], p[fact] = ans, {a: (1.0 if a == ans else 0.0) for a in ANSWERS}
    return v, p


def check_params(engine: Any, check: str) -> dict[str, float]:
    """The score parameters of the facts check as configured (pipeline instance, else the defaults)."""
    sig = inspect.signature(FactSheetCheck.__init__).parameters
    out = {k: float(sig[k].default) for k in SCORE_PARAMS}
    pipeline = getattr(engine, "pipeline", None)
    for c in getattr(pipeline, "checks", None) or []:
        if getattr(c, "name", None) == check:
            out.update({k: float(getattr(c, k)) for k in SCORE_PARAMS if hasattr(c, k)})
    return out


def redecide_family(fam: OpenFamily, answers: dict[str, str], params: dict[str, float] | None = None,
                    options: dict | None = None) -> tuple[FamilyDecision, dict[str, str], dict[str, dict[str, float]]]:
    values, probs = apply_answers(fam.table, fam.values, fam.probs, answers, options)
    return decide_family(fam.table, values, probs, **(params or {})), values, probs


def family_score(fs: FamilyScore, fd: FamilyDecision, values: dict[str, str], probs: dict[str, dict[str, float]],
                 answers: dict[str, str]) -> FamilyScore:
    """The stored family score with the re-decided label, score and reason (findings stay)."""
    detail = dict(fs.detail or {})
    detail["facts"] = {fid: {**(d or {}), "value": values.get(fid, (d or {}).get("value")),
                             "p": probs.get(fid, (d or {}).get("p"))}
                       for fid, d in (detail.get("facts") or {}).items()}
    r = fd.rule
    detail.update(decision=fd.label, summary=fd.summary, rule_probs=fd.soft, p_alarm=round(fd.p_alarm, 4),
                  p_review=round(fd.p_review, 4), officer_answers=dict(answers),
                  rule=({"id": r.id, "label": r.label, "when": r.when, "text": r.text} if r
                        else {"id": None, "label": "no_alert", "when": None, "text": "keine Regel trifft zu"}))
    return fs.model_copy(update={"score": round(min(1.0, max(0.0, fd.score)), 4),
                                 "confidence": round(min(1.0, fd.confidence), 4), "verdict": fd.verdict,
                                 "reason": f"Mit Antwort der Fachstelle: {fd.summary}", "detail": detail})


def override_result(result: CallResult, fams: list[OpenFamily], answers: dict[str, dict[str, str]],
                    params: dict[str, dict[str, float]] | None = None, options: dict | None = None) -> CallResult:
    """A copy of the call whose facts check carries the officer's answers (``answers[family][fact]``)."""
    checks = dict(result.checks)
    for fam in fams:
        ans = answers.get(fam.family) or {}
        if not ans:
            continue
        fd, values, probs = redecide_family(fam, ans, (params or {}).get(fam.check), options)
        cr = checks[fam.check]
        fss = dict(cr.family_scores)
        fss[fam.family] = family_score(fss[fam.family], fd, values, probs, ans)
        checks[fam.check] = cr.model_copy(update={"family_scores": fss})
    return result.model_copy(update={"checks": checks})
