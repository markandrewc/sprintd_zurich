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
NEW_FAMILY = "neu"  # the drafter's answer when no existing Prüfart fits: the UI offers "Neue Prüfart anlegen"

# Shared wording rules (seen live with Qwen2.5-7B: English legal basis, snake_case labels).
WORDING = (
    "Language: every text the officer reads (label, text, basis, note, policy, cases) is GERMAN (Swiss "
    "Standard German, write ss instead of ß). Only `en` and ids are English.\n"
    "Fact labels: readable German words with spaces, max. 6 words, e.g. 'Persönlicher Vorteil angeboten' "
    "or 'Betrag knapp unter 10 000 CHF'; never snake_case, never underscores, never the id.\n"
    "Legal basis (`basis`): name the Swiss provision when one clearly applies, in German citation style, "
    "e.g. 'FinfraG Art. 142 (Insiderhandel)', 'FinfraG Art. 143 (Marktmanipulation)', 'GwG Art. 6 "
    "(besondere Abklärungspflichten)', 'StGB Art. 305bis (Geldwäscherei)', 'StGB Art. 322ter ff. "
    "(Bestechung)', 'BankG Art. 47 (Bankkundengeheimnis)', 'DSG Art. 6 (Datenbearbeitung)'. If no law "
    "clearly applies, write 'Interne Weisung: <Thema auf Deutsch>'. At most 10 words. Never write English, "
    "never an explanation or a comment; compliance confirms it later.\n"
)
_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class DraftError(ValueError):
    """The LLM's answer could not be turned into a valid rule (message is German, for the officer)."""


class NeedsNewFamily(DraftError):
    """The described rule fits no existing Prüfart: create a new one (``draft_family``)."""

    def __init__(self, request: str = ""):
        super().__init__("Die Regel passt zu keiner bestehenden Prüfart. Legen Sie dafür eine neue Prüfart an.")
        self.request = request


def german_label(label: Any, fallback: str = "") -> str:
    """Readable German label: no snake_case / underscores, first letter upper case."""
    text = " ".join(str(label or "").replace("_", " ").split()) or " ".join(str(fallback).split())[:60]
    return text[:1].upper() + text[1:] if text else text


def suggested_basis(basis: Any) -> str:
    """The model's legal basis, marked as a suggestion for compliance to confirm (empty stays empty)."""
    text = " ".join(str(basis or "").split())
    if len(text) > 120:  # a rambling answer: keep the citation, drop the commentary
        text = text[:117].rsplit(" ", 1)[0] + " …"
    if not text or text.lower() in ("none", "keine", "n/a", "-"):
        return ""
    return text if "vorschlag" in text.lower() else f"{text} (Vorschlag)"


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
        "family": {"type": "string", "enum": [*families, NEW_FAMILY]},
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
        + WORDING +
        "Write 1 to 4 NEW facts only if the existing facts of the family cannot express the officer's rule. "
        "Each fact question must be atomic (one thing), answerable from the call alone with yes / no / "
        "unknown, and phrased like the existing questions: `de` a complete German question ending with '?', "
        "`en` the same question in English. Fact ids: short lowercase snake_case, not already used in the family. "
        "`rule.text`: one German sentence the officer reads when the rule fires. `note`: one short German "
        "sentence on what the officer should double-check.\n"
        f"Choose the family the officer's rule belongs to. If it belongs to NONE of them (a different kind of "
        f"misconduct), answer family '{NEW_FAMILY}' with empty facts and an empty rule condition. Answer with "
        "one JSON object only."
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
    if family == NEW_FAMILY:
        raise NeedsNewFamily(request)
    if family not in families:
        raise DraftError(f"Unbekannte Art von Fehlverhalten {family!r} (möglich: {', '.join(families)}).")
    fam = pe.family_doc(copy.deepcopy(doc), family)
    existing = {str(f.get("id")) for f in fam["facts"]}
    existing_labels = {str(f.get("id")): str(f.get("label") or f.get("id")) for f in fam["facts"]}
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
        if wanted in existing:  # seen live: the model restates an existing fact it means to reuse
            warnings.append(f"Die KI hat den bestehenden Fakt «{existing_labels.get(wanted, wanted)}» neu "
                            "formuliert; verwendet wird der bestehende (seine Antworten sind schon berechnet).")
            continue
        fid = pe.new_fact_id(trial, family, wanted or str(f.get("label") or de))
        if wanted and fid != wanted:
            rename[wanted] = fid
        role = str(f.get("role") or "")
        if role not in FACT_ROLES:
            warnings.append(f"Rolle {role!r} von {fid} unbekannt; als «context» übernommen.")
            role = "context"
        fact = {"id": fid, "label": german_label(f.get("label"), de[:40]), "role": role, "de": de, "en": en}
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
                "basis": suggested_basis(rule.get("basis"))}
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
    except NeedsNewFamily:
        raise
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


# --------------------------------------------------------------------------------------------
# a whole new Prüfart ("Neue Prüfart anlegen")
# --------------------------------------------------------------------------------------------

MAX_FAMILY_FACTS = 5
MAX_FAMILY_RULES = 3


@dataclass
class FamilyDraft:
    spec: dict[str, Any]  # input for callguard.rulebook.add_family
    note: str = ""
    warnings: list[str] = field(default_factory=list)
    request: str = ""
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


def family_schema(teams: list[str]) -> dict[str, Any]:
    fact = {"type": "object", "properties": {
        "id": {"type": "string"}, "label": {"type": "string"}, "role": {"type": "string", "enum": list(FACT_ROLES)},
        "de": {"type": "string"}, "en": {"type": "string"}}, "required": ["id", "label", "role", "de", "en"]}
    rule = {"type": "object", "properties": {
        "label": {"type": "string", "enum": list(RULE_LABELS)}, "when": {"type": "string"},
        "text": {"type": "string"}}, "required": ["label", "when", "text"]}
    strs = {"type": "array", "items": {"type": "string"}}
    props: dict[str, Any] = {
        "id": {"type": "string"}, "label": {"type": "string"}, "policy": {"type": "string"},
        "alarm_when": strs, "not_alarm_when": strs, "review_when": strs, "keywords": strs,
        "basis": {"type": "string"},
        "facts": {"type": "array", "items": fact, "maxItems": MAX_FAMILY_FACTS},
        "rules": {"type": "array", "items": rule, "maxItems": MAX_FAMILY_RULES},
        "note": {"type": "string"}}
    if teams:
        props["team"] = {"type": "string", "enum": list(teams)}
    return {"type": "object", "properties": props, "required": list(props)}


def family_messages(request: str, bundle: dict[str, Any], family_names: dict[str, str] | None = None,
                    teams: dict[str, str] | None = None, name: str = "") -> list[dict[str, str]]:
    existing = ", ".join(f"{fid} ({(family_names or {}).get(fid, fid)})"
                         for fid in ((bundle.get("policy_table") or {}).get("families") or {}))
    system = (
        "You help a bank compliance officer define a NEW kind of misconduct (a 'Prüfart') for an automatic "
        "check of recorded phone calls between bank advisors and customers (Swiss bank, calls in Swiss "
        "German, transcribed to Standard German). The definition is pure configuration:\n"
        "- `label`: the German name of the Prüfart (2-5 words), `id`: a short lowercase snake_case id.\n"
        "- `policy`: one German paragraph defining the misconduct neutrally (do not copy the officer's words, "
        "no 'Alarm, wenn'): what exactly counts, what does not.\n"
        "- `alarm_when` (1-4): cases that ARE the misconduct; `not_alarm_when` (1-4): harmless look-alikes "
        "(refused, reported, quoted, hypothetical, small customary gifts...); `review_when` (0-3): what stays "
        "undecidable from the call. Short German sentences; a harmless case never appears under alarm_when.\n"
        "- `keywords`: 3-8 German words or short phrases specific to THIS misconduct that a transcript would "
        "contain (e.g. 'Gegenleistung', 'unter der Hand'); never generic banking words such as Berater, Kunde, "
        "Zahlung, Konto, Prüfung.\n"
        "- `facts`: 2-5 atomic yes / no / unknown questions a language model answers about the whole call. "
        "`de` is a complete German question ending with '?', in the style 'Bietet eine Person der "
        "Beraterin/dem Berater im Gespräch Geld, ein Geschenk oder eine Einladung an?'; `en` the same question "
        "in English. The act fact asks whether the act happens in the call (an offer or request counts even "
        "if refused later); `role`: act = the misconduct itself happened; context = "
        "what makes it incriminating; exculpatory = what makes it harmless; authorization = a permission was "
        "established). `id`: short lowercase snake_case.\n"
        "- `rules`: 1-3 rules, read top to bottom, the first match decides: `label` alarm / review, `when` a "
        "condition over YOUR fact ids: `fact = yes`, `fact = unclear`, `fact != yes`, joined with `and` / "
        "`or`; `text` one German sentence for the officer. A final 'otherwise no alarm' rule is added "
        "automatically, do not write it. Typical: alarm when act = yes and context = yes and exculpatory != "
        "yes; review when act = yes and context = unclear.\n"
        + ("- `team`: which team should be told about a flagged call.\n" if teams else "")
        + WORDING +
        "`note`: one short German sentence on what the officer should double-check. Answer with one JSON "
        "object only."
    )
    team_txt = ("\nTeams: " + "; ".join(f"{k} = {v}" for k, v in teams.items())) if teams else ""
    user = (f"Existing Prüfarten (do not duplicate them): {existing}{team_txt}\n\n"
            + (f"Name suggested by the officer: {name.strip()}\n" if name.strip() else "")
            + f"The officer's description:\n<request>\n{request.strip()}\n</request>")
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def validate_family(obj: Any, bundle: dict[str, Any], request: str = "", teams: list[str] | None = None,
                    name: str = "") -> FamilyDraft:
    """Strict check against the bundle; returns the spec for ``rulebook.add_family`` (raises DraftError)."""
    from callguard import rulebook as rb

    if not isinstance(obj, dict):
        raise DraftError("Die KI-Antwort ist kein JSON-Objekt.")
    warnings: list[str] = []
    label = german_label(name.strip() or obj.get("label"))
    if not label:
        raise DraftError("Die KI hat keinen Namen für die Prüfart vorgeschlagen.")
    fid = rb.new_family_id(bundle, str(obj.get("id") or "") or label)
    if obj.get("id") and fid != obj.get("id"):
        warnings.append(f"Kennung {obj.get('id')!r} angepasst zu {fid!r}.")
    raw_facts = obj.get("facts") or []
    if not isinstance(raw_facts, list) or not raw_facts:
        raise DraftError("Die KI hat keine Fakten (Ja/Nein-Fragen) vorgeschlagen.")
    if len(raw_facts) > MAX_FAMILY_FACTS:
        warnings.append(f"Nur die ersten {MAX_FAMILY_FACTS} Fakten übernommen.")
    scratch = {"families": {fid: {"facts": [], "rules": []}}}
    facts: list[dict[str, Any]] = []
    rename: dict[str, str] = {}
    for i, f in enumerate(raw_facts[:MAX_FAMILY_FACTS]):
        if not isinstance(f, dict) or not " ".join(str(f.get("de") or "").split()):
            warnings.append(f"Fakt #{i + 1} ohne deutsche Frage verworfen.")
            continue
        de, en = " ".join(str(f["de"]).split()), " ".join(str(f.get("en") or "").split())
        wanted = str(f.get("id") or "").strip()
        new = pe.new_fact_id(scratch, fid, wanted or de)
        if wanted and new != wanted:
            rename[wanted] = new
        role = str(f.get("role") or "")
        if role not in FACT_ROLES:
            warnings.append(f"Rolle {role!r} von {new} unbekannt; als «context» übernommen.")
            role = "context"
        fact = pe.clean_fact({"id": new, "label": german_label(f.get("label"), de[:40]), "role": role,
                              "de": de, "en": en})
        pe.upsert_fact(scratch, fid, fact)
        facts.append(fact)
    known = {f["id"] for f in facts}
    rules: list[dict[str, Any]] = []
    for i, r in enumerate((obj.get("rules") or [])[:MAX_FAMILY_RULES]):
        if not isinstance(r, dict):
            continue
        rlabel = str(r.get("label") or "").strip().lower()
        when = _rename_tokens(" ".join(str(r.get("when") or "").split()), rename)
        if rlabel not in RULE_LABELS:
            warnings.append(f"Regel #{i + 1}: Ergebnis {rlabel!r} unbekannt, verworfen.")
            continue
        try:
            node = parse_rule(when, known)
        except PolicyTableError as e:
            warnings.append(f"Regel #{i + 1} verworfen: Bedingung «{when}» ungültig ({e}).")
            continue
        if node == ("true",):
            continue
        n = sum(1 for x in rules if x["label"] == rlabel) + 1
        rules.append({"id": f"{fid}.{rlabel}_{n}", "label": rlabel, "when": when,
                      "text": " ".join(str(r.get("text") or "").split()) or pe.LABEL_DE[rlabel]})
    if not rules:
        raise DraftError("Keine gültige Regel im Entwurf (die Bedingungen liessen sich nicht lesen).")
    used = {fact for r in rules for fact in rule_facts(parse_rule(r["when"]))}
    unused = [f["id"] for f in facts if f["id"] not in used]
    if unused:
        warnings.append(f"Fakten ohne Regel (bleiben zur Ansicht, entscheiden nichts): {', '.join(unused)}.")
    team = str(obj.get("team") or "").strip()
    known_teams = teams if teams is not None else list(((bundle.get("routing") or {}).get("teams") or {}))
    if team and team not in known_teams:
        warnings.append(f"Team {team!r} gibt es nicht; Standard-Meldeweg.")
        team = ""
    spec = {"id": fid, "label": label, "policy": " ".join(str(obj.get("policy") or "").split()) or label,
            "alarm_when": rb._phrases(obj.get("alarm_when")), "not_alarm_when": rb._phrases(obj.get("not_alarm_when")),
            "review_when": rb._phrases(obj.get("review_when")), "keywords": rb._phrases(obj.get("keywords"))[:10],
            "keywords_gsw": [], "basis": suggested_basis(obj.get("basis")),
            "team": team, "facts": facts, "rules": rules}
    try:
        rb.add_family(bundle, spec)
    except PolicyTableError as e:
        raise DraftError(f"Der Entwurf passt nicht ins Regelwerk: {e}") from None
    return FamilyDraft(spec, " ".join(str(obj.get("note") or "").split()), warnings, request, obj)


def blank_family(bundle: dict[str, Any], name: str, description: str = "") -> FamilyDraft:
    """A starting point without the LLM: one act fact, one context fact, alarm + review rule."""
    from callguard import rulebook as rb

    label = german_label(name) or "Neue Prüfart"
    fid = rb.new_family_id(bundle, label)
    spec = {"id": fid, "label": label, "policy": " ".join(description.split()) or label, "alarm_when": [],
            "not_alarm_when": [], "review_when": [], "keywords": [], "keywords_gsw": [], "basis": "", "team": "",
            "facts": [{"id": "act", "label": "Handlung findet statt", "role": "act",
                       "de": f"Kommt im Gespräch {label} vor?", "en": ""},
                      {"id": "context", "label": "Verdächtiger Umstand", "role": "context",
                       "de": "Gibt es einen Umstand, der es verdächtig macht?", "en": ""}],
            "rules": [{"id": f"{fid}.alarm_1", "label": "alarm", "when": "act = yes and context = yes",
                       "text": f"{label}: Handlung mit verdächtigem Umstand."},
                      {"id": f"{fid}.review_1", "label": "review", "when": "act = yes and context = unclear",
                       "text": f"{label}: Umstand unklar, bitte prüfen."}]}
    return FamilyDraft(spec, "Ohne KI erstellt: Fragen und Regeln bitte anpassen.", [], description, {})


def draft_family(llm: LLM, bundle: dict[str, Any], request: str, family_names: dict[str, str] | None = None,
                 teams: dict[str, str] | None = None, name: str = "", max_tokens: int = 1800) -> FamilyDraft:
    """One drafting call for a whole Prüfart (+ one repair turn when nothing usable came back)."""
    if not str(request or "").strip():
        raise DraftError("Bitte die neue Prüfart in eigenen Worten beschreiben.")
    schema = family_schema(list(teams or {}))
    messages = family_messages(request, bundle, family_names, teams, name)
    try:
        obj = chat_json(llm, messages, schema, temperature=0.0, max_tokens=max_tokens)[0]
    except ValueError as e:
        raise DraftError(f"Die KI-Antwort war kein gültiges JSON ({str(e)[:200]}).") from None
    try:
        return validate_family(obj, bundle, request, list(teams) if teams is not None else None, name)
    except DraftError as e:
        fix = [*messages, {"role": "assistant", "content": json.dumps(obj, ensure_ascii=False)},
               {"role": "user", "content": f"That draft is unusable: {e} Fix it and answer with the corrected "
                                           "JSON object only."}]
        try:
            obj2 = chat_json(llm, fix, schema, temperature=0.0, max_tokens=max_tokens, repair=False)[0]
        except ValueError:
            raise e from None
        return validate_family(obj2, bundle, request, list(teams) if teams is not None else None, name)
