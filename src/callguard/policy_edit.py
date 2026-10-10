"""Plain-language editing of the policy table (``config/policy_table.yaml``) for the UI page "Regelwerk".

Pure (no Streamlit), unit-tested. The table is edited as its YAML document (a dict: ``families -> {basis,
facts, rules}``) and validated with the facts check's own parser (:func:`callguard.checks.facts.
parse_policy_table`), so whatever the editor produces is exactly what the pipeline reads.

* **Condition builder**: a rule condition (``when``) as a list of rows "Fakt | ist / ist nicht | ja / nein /
  unklar", joined by UND / ODER (UND binds stronger, like in the rule language). :func:`builder_from_when`
  and :func:`when_from_builder` convert both ways; conditions the rows cannot express (brackets around an
  ODER, ``not (...)``) return None and stay editable as text.
* **Rendering**: :func:`render_rule` writes "WENN «Handelswunsch» = ja UND «Information öffentlich» ≠ ja →
  ALARM" with the fact labels, never the ids.
* **Edits**: move / switch off / replace / delete rules, add or change facts, new ids.
* **Diff**: :func:`diff_docs` lists what changed between two versions in plain German.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from callguard.checks.facts import (
    FACT_ROLES,
    RULE_LABELS,
    Node,
    PolicyTable,
    PolicyTableError,
    parse_policy_table,
    parse_rule,
)

VALUES = ("yes", "no", "unclear")
VALUE_DE = {"yes": "ja", "no": "nein", "unclear": "unklar"}
LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
LABEL_UPPER = {"alarm": "ALARM", "review": "PRÜFEN", "no_alert": "KEIN ALARM"}
ROLE_DE = {"act": "Handlung (das Fehlverhalten selbst)", "context": "Umstand (macht es verdächtig)",
           "exculpatory": "Entlastung (macht es harmlos)", "authorization": "Berechtigung (Vollmacht)"}
JOIN_DE = {"and": "UND", "or": "ODER"}
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_RESERVED = {"and", "or", "not", "in", "true"}


# --------------------------------------------------------------------------------------------
# condition builder <-> rule text
# --------------------------------------------------------------------------------------------


@dataclass
class Cond:
    """One row of the builder: ``fact`` (ist | ist nicht) ``value``; ``join`` links it to the row before."""

    fact: str
    value: str = "yes"  # yes | no | unclear
    negate: bool = False  # "ist nicht"
    join: str = "and"  # and | or (ignored for the first row)

    def text(self) -> str:
        return f"{self.fact} {'!=' if self.negate else '='} {self.value}"


def _atom(node: Node) -> Cond | None:
    neg = False
    if node[0] == "not" and node[1][0] == "cmp":
        neg, node = True, node[1]
    if node[0] != "cmp":
        return None
    vals = set(node[2])
    if len(vals) == 1:
        return Cond(node[1], next(iter(vals)), neg)
    if len(vals) == 2:  # `in [yes, unclear]` is `!= no`; `not in [yes, unclear]` is `= no`
        (missing,) = set(VALUES) - vals
        return Cond(node[1], missing, not neg)
    return None  # all three values: always true, not a builder row


def builder_from_when(when: str, facts: set[str] | None = None) -> list[Cond] | None:
    """Rows for a condition; ``[]`` for ``true``; None if the rows cannot express it (raises on syntax errors)."""
    node = parse_rule(when, facts)
    if node == ("true",):
        return []
    groups = list(node[1:]) if node[0] == "or" else [node]
    out: list[Cond] = []
    for g in groups:
        parts = list(g[1:]) if g[0] == "and" else [g]
        for j, part in enumerate(parts):
            c = _atom(part)
            if c is None:
                return None
            c.join = "or" if (j == 0 and out) else "and"
            out.append(c)
    return out


def when_from_builder(conds: list[Cond]) -> str:
    """The rule text of the rows (``true`` for none). UND binds stronger than ODER."""
    out = ""
    for i, c in enumerate(conds):
        if c.value not in VALUES:
            raise PolicyTableError(f"Wert {c.value!r} ist nicht ja / nein / unklar")
        out += ("" if i == 0 else f" {c.join if c.join in JOIN_DE else 'and'} ") + c.text()
    return out or "true"


# --------------------------------------------------------------------------------------------
# rendering in plain German
# --------------------------------------------------------------------------------------------


def _vals_de(vals: Any) -> str:
    ordered = [VALUE_DE[v] for v in VALUES if v in set(vals)]
    return " oder ".join(ordered)


def render_node(node: Node, labels: dict[str, str], top: bool = True) -> str:
    kind = node[0]
    if kind == "true":
        return "immer"
    if kind == "cmp" or (kind == "not" and node[1][0] == "cmp"):
        c = _atom(node)
        fid = node[1] if kind == "cmp" else node[1][1]
        lab = f"«{labels.get(fid, fid)}»"
        if c is None:
            return f"{lab} beliebig"
        return f"{lab} {'≠' if c.negate else '='} {VALUE_DE[c.value]}"
    if kind == "not":
        return f"NICHT ({render_node(node[1], labels, True)})"
    sep = " UND " if kind == "and" else " ODER "
    parts = [render_node(n, labels, False) for n in node[1:]]
    if kind == "or":
        parts = [f"({p})" if n[0] == "and" else p for p, n in zip(parts, node[1:])]
    text = sep.join(parts)
    return text if top or kind == "and" else f"({text})"


def render_when(when: str, labels: dict[str, str]) -> str:
    try:
        return render_node(parse_rule(when), labels)
    except PolicyTableError:
        return str(when)


def render_rule(rule: dict[str, Any], labels: dict[str, str]) -> str:
    """"WENN «A» = ja UND «B» ≠ ja → ALARM"; the default rule reads "SONST → KEIN ALARM"."""
    label = LABEL_UPPER.get(str(rule.get("label")), str(rule.get("label")))
    when = str(rule.get("when", "true"))
    if when.strip().lower() == "true" or rule.get("when") is True:
        return f"SONST (immer) → {label}"
    return f"WENN {render_when(when, labels)} → {label}"


def fact_labels(doc: dict[str, Any], family: str) -> dict[str, str]:
    return {str(f.get("id")): str(f.get("label") or f.get("id")) for f in family_doc(doc, family).get("facts") or []}


# --------------------------------------------------------------------------------------------
# the YAML document
# --------------------------------------------------------------------------------------------


def load_doc(path: str | Path) -> dict[str, Any]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("families"), dict):
        raise PolicyTableError(f"{path}: expected a mapping with a `families:` block")
    return raw


def header_of(text: str) -> str:
    """The leading comment block of a table file (kept when the UI writes a new version)."""
    lines = []
    for line in text.splitlines():
        if line.startswith("#") or not line.strip():
            lines.append(line)
        else:
            break
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def dump_doc(doc: dict[str, Any], header: str = "") -> str:
    body = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=110, default_flow_style=False)
    return (header.rstrip() + "\n\n" if header.strip() else "") + body


def validate(doc: dict[str, Any]) -> PolicyTable:
    """Exactly the facts check's validation; raises PolicyTableError with the reason."""
    return parse_policy_table(copy.deepcopy(doc), source="Entwurf")


def family_doc(doc: dict[str, Any], family: str) -> dict[str, Any]:
    fam = (doc.get("families") or {}).get(family)
    if not isinstance(fam, dict):
        raise KeyError(f"Familie {family!r} nicht in der Tabelle")
    fam.setdefault("facts", [])
    fam.setdefault("rules", [])
    return fam


def rule_index(doc: dict[str, Any], family: str, rule_id: str) -> int:
    for i, r in enumerate(family_doc(doc, family)["rules"]):
        if str(r.get("id")) == rule_id:
            return i
    raise KeyError(f"Regel {rule_id!r} nicht in {family}")


def is_enabled(rule: dict[str, Any]) -> bool:
    return rule.get("enabled", True) is not False


def move_rule(doc: dict[str, Any], family: str, rule_id: str, delta: int) -> bool:
    rules = family_doc(doc, family)["rules"]
    i = rule_index(doc, family, rule_id)
    j = i + delta
    if not 0 <= j < len(rules):
        return False
    rules[i], rules[j] = rules[j], rules[i]
    return True


def set_enabled(doc: dict[str, Any], family: str, rule_id: str, on: bool) -> None:
    r = family_doc(doc, family)["rules"][rule_index(doc, family, rule_id)]
    if on:
        r.pop("enabled", None)  # default: keeps the cache key of the table unchanged
    else:
        r["enabled"] = False


def delete_rule(doc: dict[str, Any], family: str, rule_id: str) -> None:
    del family_doc(doc, family)["rules"][rule_index(doc, family, rule_id)]


def clean_rule(rule: dict[str, Any]) -> dict[str, Any]:
    """Key order as in the shipped file, empty optional keys dropped."""
    out: dict[str, Any] = {"id": str(rule["id"]), "label": str(rule["label"]), "when": str(rule.get("when") or "true"),
                           "text": str(rule.get("text") or "").strip()}
    if str(rule.get("basis") or "").strip():
        out["basis"] = str(rule["basis"]).strip()
    if rule.get("enabled", True) is False:
        out["enabled"] = False
    return out


def replace_rule(doc: dict[str, Any], family: str, rule_id: str, new: dict[str, Any]) -> None:
    rules = family_doc(doc, family)["rules"]
    rules[rule_index(doc, family, rule_id)] = clean_rule(new)


def default_position(doc: dict[str, Any], family: str, label: str) -> int:
    """Where a new rule goes: alarm and no_alert (an exception that clears) at the top, review after the
    last alarm rule; never behind the default rule ``true``."""
    rules = family_doc(doc, family)["rules"]
    if label == "review":
        alarms = [i for i, r in enumerate(rules) if r.get("label") == "alarm"]
        return (alarms[-1] + 1) if alarms else 0
    return 0


def add_rule(doc: dict[str, Any], family: str, rule: dict[str, Any], position: int | None = None) -> int:
    rules = family_doc(doc, family)["rules"]
    pos = default_position(doc, family, rule["label"]) if position is None else max(0, min(position, len(rules)))
    rules.insert(pos, clean_rule(rule))
    return pos


def new_rule_id(doc: dict[str, Any], family: str, label: str) -> str:
    taken = {str(r.get("id")) for r in family_doc(doc, family)["rules"]}
    n = 1
    while f"{family}.{label}_{n}" in taken or (label == "no_alert" and f"{family}.no_alert_{n}" in taken):
        n += 1
    return f"{family}.{label}_{n}"


def slug(text: str) -> str:
    s = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    s = s[:30].rstrip("_") or "fakt"
    return f"f_{s}" if s[0].isdigit() or s in _RESERVED else s


def new_fact_id(doc: dict[str, Any], family: str, wanted: str) -> str:
    taken = {str(f.get("id")) for f in family_doc(doc, family)["facts"]}
    base = wanted if _NAME.fullmatch(wanted or "") and wanted.lower() not in _RESERVED else slug(wanted or "fakt")
    out, n = base, 2
    while out in taken:
        out, n = f"{base}_{n}", n + 1
    return out


def clean_fact(fact: dict[str, Any]) -> dict[str, Any]:
    out = {"id": str(fact["id"]), "label": str(fact.get("label") or fact["id"]).strip(),
           "role": str(fact.get("role") or "context"), "de": " ".join(str(fact.get("de") or "").split())}
    en = " ".join(str(fact.get("en") or "").split())
    if en:
        out["en"] = en
    if out["role"] not in FACT_ROLES:
        raise PolicyTableError(f"Rolle {out['role']!r} nicht in {FACT_ROLES}")
    return out


def upsert_fact(doc: dict[str, Any], family: str, fact: dict[str, Any]) -> None:
    facts = family_doc(doc, family)["facts"]
    new = clean_fact(fact)
    for i, f in enumerate(facts):
        if str(f.get("id")) == new["id"]:
            facts[i] = new
            return
    facts.append(new)


def facts_in_use(doc: dict[str, Any], family: str) -> set[str]:
    from callguard.checks.facts import rule_facts

    out: set[str] = set()
    for r in family_doc(doc, family)["rules"]:
        try:
            out.update(rule_facts(parse_rule(str(r.get("when", "true")))))
        except PolicyTableError:
            pass
    return out


def delete_fact(doc: dict[str, Any], family: str, fact_id: str) -> None:
    if fact_id in facts_in_use(doc, family):
        raise PolicyTableError(f"Fakt {fact_id!r} wird noch in einer Regel verwendet")
    fam = family_doc(doc, family)
    fam["facts"] = [f for f in fam["facts"] if str(f.get("id")) != fact_id]


# --------------------------------------------------------------------------------------------
# diff in plain German
# --------------------------------------------------------------------------------------------


def _q(f: dict[str, Any], lang: str) -> str:
    return " ".join(str(f.get(lang) or "").split())


def changed_questions(old: dict[str, Any], new: dict[str, Any]) -> dict[str, list[str]]:
    """family -> fact ids that are new or whose German or English question changed."""
    out: dict[str, list[str]] = {}
    for fam, entry in (new.get("families") or {}).items():
        before = {str(f.get("id")): f for f in ((old.get("families") or {}).get(fam) or {}).get("facts") or []}
        for f in entry.get("facts") or []:
            b = before.get(str(f.get("id")))
            if b is None or _q(b, "de") != _q(f, "de") or _q(b, "en") != _q(f, "en"):
                out.setdefault(fam, []).append(str(f.get("id")))
    return out


def diff_docs(old: dict[str, Any], new: dict[str, Any], family_names: dict[str, str] | None = None) -> list[str]:
    """What changed, one German sentence per change (empty list: identical in effect and wording)."""
    names = family_names or {}
    out: list[str] = []
    ofams, nfams = old.get("families") or {}, new.get("families") or {}
    for fam in [*nfams, *[f for f in ofams if f not in nfams]]:
        name = names.get(fam, fam)
        if fam not in ofams:
            out.append(f"{name}: neue Art von Fehlverhalten")
            continue
        if fam not in nfams:
            out.append(f"{name}: Art von Fehlverhalten entfernt")
            continue
        o, n = ofams[fam], nfams[fam]
        if str(o.get("basis") or "") != str(n.get("basis") or ""):
            out.append(f"{name}: Rechtsgrundlage jetzt «{n.get('basis') or '–'}»")
        ofacts = {str(f.get("id")): f for f in o.get("facts") or []}
        nfacts = {str(f.get("id")): f for f in n.get("facts") or []}
        labels = {**{k: str(v.get("label") or k) for k, v in ofacts.items()},
                  **{k: str(v.get("label") or k) for k, v in nfacts.items()}}
        for fid, f in nfacts.items():
            b = ofacts.get(fid)
            if b is None:
                out.append(f"{name}: neuer Fakt «{labels[fid]}» – Frage: «{_q(f, 'de')}»")
                continue
            if str(b.get("label")) != str(f.get("label")):
                out.append(f"{name}: Fakt «{b.get('label')}» heisst jetzt «{f.get('label')}»")
            if _q(b, "de") != _q(f, "de"):
                out.append(f"{name}: Frage zu «{labels[fid]}» (Deutsch) geändert: «{_q(f, 'de')}»")
            if _q(b, "en") != _q(f, "en"):
                out.append(f"{name}: Frage zu «{labels[fid]}» (Englisch, liest das Modell) geändert")
            if str(b.get("role")) != str(f.get("role")):
                out.append(f"{name}: Fakt «{labels[fid]}» ist jetzt {ROLE_DE.get(str(f.get('role')), f.get('role'))}")
        for fid in ofacts:
            if fid not in nfacts:
                out.append(f"{name}: Fakt «{labels[fid]}» entfernt")
        orules = {str(r.get("id")): r for r in o.get("rules") or []}
        nrules = {str(r.get("id")): r for r in n.get("rules") or []}
        for rid, r in nrules.items():
            b = orules.get(rid)
            if b is None:
                out.append(f"{name}: neue Regel {rid}: {render_rule(r, labels)}"
                           + ("" if is_enabled(r) else " (ausgeschaltet)"))
                continue
            if is_enabled(b) != is_enabled(r):
                out.append(f"{name}: Regel {rid} {'eingeschaltet' if is_enabled(r) else 'ausgeschaltet'}")
            if str(b.get("when")) != str(r.get("when")):
                out.append(f"{name}: Regel {rid} Bedingung vorher {render_rule(b, labels)}; jetzt {render_rule(r, labels)}")
            elif str(b.get("label")) != str(r.get("label")):
                out.append(f"{name}: Regel {rid} Ergebnis {LABEL_DE.get(str(b.get('label')))} → "
                           f"{LABEL_DE.get(str(r.get('label')))}")
            if str(b.get("text") or "") != str(r.get("text") or ""):
                out.append(f"{name}: Regel {rid} Erklärung jetzt «{r.get('text') or ''}»")
            if str(b.get("basis") or "") != str(r.get("basis") or ""):
                out.append(f"{name}: Regel {rid} Rechtsgrundlage jetzt «{r.get('basis') or '–'}»")
        for rid, b in orules.items():
            if rid not in nrules:
                out.append(f"{name}: Regel {rid} gelöscht ({render_rule(b, labels)})")
        common_o = [rid for rid in orules if rid in nrules]
        common_n = [rid for rid in nrules if rid in orules]
        if common_o != common_n:
            out.append(f"{name}: Reihenfolge der Regeln geändert: {' → '.join(common_n)}")
    return out
