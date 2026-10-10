""""Neue Regel in eigenen Worten": the officer describes a rule in free text, the configured LLM drafts it
as policy-table entries (UI page "Regelwerk").

    draft = draft_rule(llm, doc, "Alarm, wenn ein Kunde eine Zahlung knapp unter 10'000 aufteilen will ...")
    draft.family, draft.facts, draft.rule, draft.warnings

One JSON call (``json_schema``: vLLM guided decoding on the GPU host) returns the target family, 1-4 atomic
yes / no / unknown fact questions (German + English, role) and the rule (condition over those facts and the
family's existing facts, label, German explanation, suggested legal basis). Everything is validated strictly
with the facts check's own parser before the officer sees it: unknown family, a condition that does not
parse, unknown fact names, labels outside alarm / review / no_alert are errors (one repair turn with the
error, then :class:`DraftError`); colliding fact ids are renamed, unused facts dropped (warnings).

A draft is never active: :func:`apply_draft` only adds it to the officer's working copy, which goes
through preview, versioning and four-eyes approval like any manual edit. The new questions have no fact
probes yet; the preview asks the LLM for them (or says that it cannot).
"""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from callguard import policy_edit as pe
from callguard.checks.facts import FACT_ROLES, RULE_LABELS, PolicyTableError, parse_rule, rule_facts
from callguard.llm.jsonutil import chat_json, strip_reasoning
from callguard.plugins import LLM

log = logging.getLogger("callguard.rule_drafter")

MAX_FACTS = 4
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class DraftError(ValueError):
    """The LLM's answer could not be turned into a valid rule (message is German, for the officer)."""


@dataclass
class Draft:
    family: str
    facts: list[dict[str, Any]]  # new facts: id, label, role, de, en
    rule: dict[str, Any]  # id, label, when, text, basis
    note: str = ""
    warnings: list[str] = field(default_factory=list)
    request: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


def draft_schema(families: list[str]) -> dict[str, Any]:
    fact = {"type": "object", "properties": {
        "id": {"type": "string"}, "label": {"type": "string"}, "role": {"type": "string", "enum": list(FACT_ROLES)},
        "de": {"type": "string"}, "en": {"type": "string"}},
        "required": ["id", "label", "role", "de", "en"]}
    return {"type": "object", "properties": {
        "family": {"type": "string", "enum": list(families)},
        "facts": {"type": "array", "items": fact, "maxItems": MAX_FACTS},
        "rule": {"type": "object", "properties": {
            "label": {"type": "string", "enum": list(RULE_LABELS)}, "when": {"type": "string"},
            "text": {"type": "string"}, "basis": {"type": "string"}},
            "required": ["label", "when", "text", "basis"]},
        "note": {"type": "string"}},
        "required": ["family", "facts", "rule", "note"]}


def _table_summary(doc: dict[str, Any], family_names: dict[str, str] | None) -> str:
    out = []
    for fam, entry in (doc.get("families") or {}).items():
        out.append(f"Family `{fam}` ({(family_names or {}).get(fam, fam)}):")
        for f in entry.get("facts") or []:
            q = " ".join(str(f.get("en") or f.get("de") or "").split())
            out.append(f"  fact {f.get('id')} [{f.get('role')}]: {q}")
        for r in entry.get("rules") or []:
            out.append(f"  rule {r.get('id')}: {r.get('label')} if {r.get('when')}")
    return "\n".join(out)


def draft_messages(request: str, doc: dict[str, Any], family_names: dict[str, str] | None = None) -> list[dict[str, str]]:
    system = (
        "You help a bank compliance officer write rules for an automatic check of recorded phone calls "
        "between bank advisors and customers. A language model answers atomic FACT questions about each call "
        "with exactly one word (yes / no / unknown); RULES then map the fact answers to a label "
        "(alarm / review / no_alert). The first matching rule of a family decides.\n\n"
        "Rule condition language (field `when`): `fact = yes`, `fact = no`, `fact = unclear`, `fact != yes`, "
        "combined with `and` / `or` and brackets. Use only fact ids of the chosen family (existing ones or the "
        "new ones you define).\n"
        "Fact roles: act = the misconduct itself happened; context = what makes it incriminating; "
        "exculpatory = what makes it harmless; authorization = whether a permission was established.\n\n"
        "Write 1 to 4 NEW facts only if the existing facts of the family cannot express the officer's rule. "
        "Each fact question must be atomic (one thing), answerable from the call alone with yes / no / "
        "unknown, and phrased like the existing questions. `de` is the question in German, `en` the same "
        "question in English. Fact ids: short lowercase snake_case, not already used in the family. "
        "`label`: a short German label (max. 6 words).\n"
        "`rule.text`: one German sentence the officer reads when the rule fires. `rule.basis`: the Swiss "
        "legal basis or internal directive this rule implements, if you know one (e.g. 'GwG Art. 6'), else "
        "an empty string. `note`: one short German sentence on what the officer should double-check.\n"
        "Choose the family the officer's rule belongs to. Answer with one JSON object only."
    )
    user = (f"Current policy table:\n{_table_summary(doc, family_names)}\n\n"
            f"The officer's rule, in their own words:\n<request>\n{request.strip()}\n</request>")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _rename_tokens(when: str, mapping: dict[str, str]) -> str:
    return _TOKEN.sub(lambda m: mapping.get(m.group(0), m.group(0)), when) if mapping else when


def validate_draft(obj: Any, doc: dict[str, Any], request: str = "") -> Draft:
    """Strict check of the LLM's object against the table; raises DraftError (German) when unusable."""
    if not isinstance(obj, dict):
        raise DraftError("Die KI-Antwort ist kein JSON-Objekt.")
    families = list((doc.get("families") or {}).keys())
    family = str(obj.get("family") or "").strip()
    if family not in families:
        raise DraftError(f"Unbekannte Art von Fehlverhalten {family!r} (möglich: {', '.join(families)}).")
    fam = pe.family_doc(copy.deepcopy(doc), family)
    existing = {str(f.get("id")) for f in fam["facts"]}
    warnings: list[str] = []

    raw_facts = obj.get("facts") or []
    if not isinstance(raw_facts, list):
        raise DraftError("`facts` ist keine Liste.")
    if len(raw_facts) > MAX_FACTS:
        warnings.append(f"Die KI hat {len(raw_facts)} Fakten vorgeschlagen; nur die ersten {MAX_FACTS} übernommen.")
        raw_facts = raw_facts[:MAX_FACTS]
    trial = copy.deepcopy(doc)
    facts: list[dict[str, Any]] = []
    rename: dict[str, str] = {}
    for i, f in enumerate(raw_facts):
        if not isinstance(f, dict):
            raise DraftError(f"Fakt #{i + 1} ist kein Objekt.")
        de, en = " ".join(str(f.get("de") or "").split()), " ".join(str(f.get("en") or "").split())
        if not de:
            warnings.append(f"Fakt #{i + 1} ohne deutsche Frage verworfen.")
            continue
        wanted = str(f.get("id") or "").strip()
        fid = pe.new_fact_id(trial, family, wanted or str(f.get("label") or de))
        if wanted and fid != wanted:
            rename[wanted] = fid
            if wanted in existing:
                warnings.append(f"Fakt-Id {wanted!r} gibt es schon; der neue Fakt heisst {fid!r}.")
        role = str(f.get("role") or "")
        if role not in FACT_ROLES:
            warnings.append(f"Rolle {role!r} von {fid} unbekannt; als «context» übernommen.")
            role = "context"
        fact = {"id": fid, "label": str(f.get("label") or "").strip() or de[:40], "role": role, "de": de, "en": en}
        if not en:
            warnings.append(f"Fakt {fid}: keine englische Fassung; das Modell liest dann die deutsche Frage.")
        pe.upsert_fact(trial, family, fact)
        facts.append(pe.clean_fact(fact))

    rule = obj.get("rule")
    if not isinstance(rule, dict):
        raise DraftError("Die KI-Antwort enthält keine Regel.")
    label = str(rule.get("label") or "").strip().lower()
    if label not in RULE_LABELS:
        raise DraftError(f"Ergebnis {label!r} ist nicht alarm / review / no_alert.")
    when = _rename_tokens(str(rule.get("when") or "").strip(), rename)
    known = existing | {f["id"] for f in facts}
    try:
        node = parse_rule(when, known)
    except PolicyTableError as e:
        raise DraftError(f"Die Bedingung «{when}» ist ungültig: {e}") from None
    if node == ("true",):
        raise DraftError("Die Regel hat keine Bedingung (`true`); so würde sie immer greifen.")
    used = set(rule_facts(node))
    unused = [f["id"] for f in facts if f["id"] not in used]
    if unused:
        warnings.append(f"Nicht verwendete Fakten verworfen: {', '.join(unused)}.")
        facts = [f for f in facts if f["id"] in used]
    text = " ".join(str(rule.get("text") or "").split()) or f"{pe.LABEL_DE[label]}: von der KI vorgeschlagene Regel."
    out_rule = {"id": pe.new_rule_id(doc, family, label), "label": label, "when": when, "text": text,
                "basis": " ".join(str(rule.get("basis") or "").split())}
    draft = Draft(family=family, facts=facts, rule=out_rule, note=" ".join(str(obj.get("note") or "").split()),
                  warnings=warnings, request=request, raw=obj)
    try:
        pe.validate(apply_draft(doc, draft))
    except PolicyTableError as e:
        raise DraftError(f"Der Entwurf passt nicht in die Tabelle: {e}") from None
    return draft


def apply_draft(doc: dict[str, Any], draft: Draft, position: int | None = None) -> dict[str, Any]:
    """A copy of ``doc`` with the draft's facts and rule added (rule at its default position)."""
    out = copy.deepcopy(doc)
    for f in draft.facts:
        pe.upsert_fact(out, draft.family, f)
    rule = dict(draft.rule)
    if rule["id"] in {str(r.get("id")) for r in pe.family_doc(out, draft.family)["rules"]}:
        rule["id"] = pe.new_rule_id(out, draft.family, rule["label"])
    pe.add_rule(out, draft.family, rule, position)
    return out


def draft_rule(llm: LLM, doc: dict[str, Any], request: str, family_names: dict[str, str] | None = None,
               max_tokens: int = 900) -> Draft:
    """One drafting call (+ one repair turn on a schema or rule error). Raises DraftError."""
    if not str(request or "").strip():
        raise DraftError("Bitte die Regel in eigenen Worten beschreiben.")
    families = list((doc.get("families") or {}).keys())
    schema = draft_schema(families)
    messages = draft_messages(request, doc, family_names)
    try:
        obj = chat_json(llm, messages, schema, temperature=0.0, max_tokens=max_tokens)[0]
    except ValueError as e:
        raise DraftError(f"Die KI-Antwort war kein gültiges JSON ({str(e)[:200]}).") from None
    try:
        return validate_draft(obj, doc, request)
    except DraftError as e:
        log.info("draft rejected, one repair turn: %s", e)
        fix = [*messages, {"role": "assistant", "content": json.dumps(obj, ensure_ascii=False)},
               {"role": "user", "content": f"That draft is invalid: {e} Fix it and answer with the corrected "
                                           "JSON object only."}]
        try:
            obj2 = chat_json(llm, fix, schema, temperature=0.0, max_tokens=max_tokens, repair=False)[0]
        except ValueError:
            raise e from None
        return validate_draft(obj2, doc, request)


def translate_question(llm: LLM, de: str) -> str:
    """English version of a German fact question (the model reads English by default)."""
    messages = [
        {"role": "system", "content": "You translate compliance questions from German to English. Keep the "
                                      "meaning exact, keep it a yes/no question, keep examples in brackets. "
                                      "Answer with the English question only."},
        {"role": "user", "content": " ".join(str(de).split())}]
    out = (llm.chat(messages, temperature=0.0, max_tokens=300) or [""])[0]
    out = " ".join(strip_reasoning(str(out)).strip().strip('"').strip("«»").split())
    if not out:
        raise DraftError("Die Übersetzung ist leer.")
    return out
