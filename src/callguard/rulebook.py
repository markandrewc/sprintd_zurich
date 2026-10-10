"""The officer's rulebook as one bundle of configuration files (UI page "Regelwerk").

A *Prüfart* (misconduct type, internally a family) is pure configuration, spread over the files the
pipeline already reads; nothing here is code and no code changes when a new one is added:

=============  ==================================  =====================================================
name           file (profile ``paths`` / config)   what the Regelwerk changes there
=============  ==================================  =====================================================
policy_table   ``config/policy_table.yaml``        facts + rules (the decision), legal basis
criteria       ``paths.criteria``                  label, description, alarm / harmless / review cases,
                                                   ``enabled: false`` = Prüfart switched off
keywords       ``paths.keywords``                  the Prüfart's keyword family and its keywords
routing        ``config/routing.yaml``             which team is told about a flagged call
tuning         ``paths.tuning``                    ``profiles.<profile>.weights.<check>: 0`` = a kind
                                                   of check (Stichwörter, Muster, KI) switched off
=============  ==================================  =====================================================

Pure (no Streamlit), unit-tested. ``policy_versions`` versions the whole bundle (four-eyes approval writes
exactly the files a draft changed); :func:`diff_bundle` describes a change in plain German.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any

import yaml

from callguard import policy_edit as pe
from callguard.checks.facts import PolicyTableError

EXTRA_NAMES = ("criteria", "keywords", "routing", "tuning")
NAMES = ("policy_table", *EXTRA_NAMES)
FILE_DE = {"policy_table": "Regeltabelle", "criteria": "Kriterien", "keywords": "Stichwortliste",
           "routing": "Meldewege", "tuning": "Prüfungen an/aus"}
CHECK_KIND_DE = {"keywords": "Stichwörter", "patterns": "Muster (Ziffernfolgen, Codes)", "facts": "KI-Faktenprüfung",
                 "llm_judge": "KI-Gesamturteil", "geval": "KI-Bewertung (G-Eval)", "geval_cot": "KI-Bewertung",
                 "quote_judge": "KI-Zitatprüfung", "semantic": "Semantische Suche", "entities": "Entitäten"}
_ID = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
RESERVED_FAMILY_IDS = {"main", "all", "none", "true", "false"}


# --------------------------------------------------------------------------------------------
# reading / writing the files
# --------------------------------------------------------------------------------------------


def parse_text(name: str, text: str | None) -> dict[str, Any]:
    if not text or not text.strip():
        return {}
    out = json.loads(text) if name == "keywords" else yaml.safe_load(text)
    return out if isinstance(out, dict) else {}


def dump_text(name: str, doc: dict[str, Any], old_text: str | None = None) -> str:
    """keywords.json as the keyword editor writes it; YAML files keep their leading comment block."""
    if name == "keywords":
        return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    return pe.dump_doc(doc, pe.header_of(old_text or ""))


def changed_names(old: dict[str, dict], new: dict[str, dict]) -> list[str]:
    return [n for n in NAMES if (old.get(n) or {}) != (new.get(n) or {})]


# --------------------------------------------------------------------------------------------
# switches: Prüfart on/off (criteria), kind of check on/off (tuning weights)
# --------------------------------------------------------------------------------------------


def family_enabled(bundle: dict[str, dict], fid: str) -> bool:
    return ((bundle.get("criteria") or {}).get("families") or {}).get(fid, {}).get("enabled", True) is not False


def set_family_enabled(bundle: dict[str, dict], fid: str, on: bool) -> None:
    fams = bundle.setdefault("criteria", {}).setdefault("families", {})
    entry = fams.setdefault(fid, {})
    if on:
        entry.pop("enabled", None)
    else:
        entry["enabled"] = False


def checks_off(bundle: dict[str, dict], profile: str) -> set[str]:
    """Check names with weight 0 in the tuning overlay for this profile (top-level or profile block)."""
    t = bundle.get("tuning") or {}
    weights = {**(t.get("weights") or {}), **(((t.get("profiles") or {}).get(profile) or {}).get("weights") or {})}
    return {k for k, v in weights.items() if _num(v) == 0.0}


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def set_check_enabled(bundle: dict[str, dict], profile: str, check: str, on: bool) -> None:
    """Off = weight 0 for this profile (the fusion ignores the check); on = drop that override again, so the
    profile's own weight (or a tuned one at the top level) applies."""
    t = bundle.setdefault("tuning", {})
    prof = t.setdefault("profiles", {}).setdefault(profile, {})
    w = prof.setdefault("weights", {})
    if on:
        if _num(w.get(check)) == 0.0:
            w.pop(check)
        if _num((t.get("weights") or {}).get(check)) == 0.0:
            t["weights"].pop(check)
    else:
        w[check] = 0.0
    if not w:
        prof.pop("weights")
    if not prof:
        t["profiles"].pop(profile)
    if not t.get("profiles"):
        t.pop("profiles", None)


# --------------------------------------------------------------------------------------------
# a new Prüfart
# --------------------------------------------------------------------------------------------


def family_ids(bundle: dict[str, dict]) -> set[str]:
    return (set((bundle.get("policy_table") or {}).get("families") or {})
            | set((bundle.get("criteria") or {}).get("families") or {})
            | set((bundle.get("keywords") or {}).get("families") or {}))


def new_family_id(bundle: dict[str, dict], wanted: str) -> str:
    base = pe.slug(wanted or "pruefart")
    base = base if _ID.match(base) and base not in RESERVED_FAMILY_IDS else f"art_{base}"[:30]
    taken = family_ids(bundle)
    out, n = base, 2
    while out in taken:
        out, n = f"{base}_{n}", n + 1
    return out


def _next_keyword_id(kw: dict[str, Any]) -> str:
    nums = [int(m.group(1)) for k in kw.get("keywords") or [] if (m := re.fullmatch(r"K(\d+)", str(k.get("id"))))]
    return f"K{max(nums, default=0) + 1:02d}"


def _phrases(items: Any) -> list[str]:
    if isinstance(items, str):
        items = re.split(r"[,;\n]", items)
    return [" ".join(str(x).split()) for x in items or [] if str(x).strip()]


def add_family(bundle: dict[str, dict], spec: dict[str, Any]) -> dict[str, dict]:
    """A copy of the bundle with a new Prüfart. ``spec``: id, label, policy, alarm_when, not_alarm_when,
    review_when, basis, keywords (German phrases), keywords_gsw, keywords_en, keyword_label, team,
    facts (list), rules (list; a default "sonst kein Alarm" rule is appended when missing)."""
    out = copy.deepcopy(bundle)
    fid = str(spec["id"])
    if not _ID.match(fid) or fid in RESERVED_FAMILY_IDS:
        raise PolicyTableError(f"Kennung {fid!r}: nur Kleinbuchstaben, Ziffern und _, 2-31 Zeichen")
    if fid in family_ids(bundle):
        raise PolicyTableError(f"Die Prüfart {fid!r} gibt es schon")
    label = " ".join(str(spec.get("label") or "").split())
    if not label:
        raise PolicyTableError("Die Prüfart braucht einen Namen")
    if not spec.get("facts") or not spec.get("rules"):
        raise PolicyTableError("Die Prüfart braucht mindestens einen Fakt und eine Regel")

    crit = out.setdefault("criteria", {}).setdefault("families", {})
    crit[fid] = {"label": label, "policy": " ".join(str(spec.get("policy") or label).split()),
                 "alarm_when": _phrases(spec.get("alarm_when")), "not_alarm_when": _phrases(spec.get("not_alarm_when")),
                 "review_when": _phrases(spec.get("review_when"))}

    kw = out.setdefault("keywords", {})
    words = _phrases(spec.get("keywords"))
    ids: list[str] = []
    if words:
        kid = _next_keyword_id(kw)
        kw.setdefault("keywords", []).append({
            "id": kid, "label": str(spec.get("keyword_label") or label), "de": words,
            "gsw": _phrases(spec.get("keywords_gsw")), "en": _phrases(spec.get("keywords_en")),
            "harmless": " ".join(str(spec.get("harmless") or "").split()) or None, "enabled": True})
        if kw["keywords"][-1]["harmless"] is None:
            kw["keywords"][-1].pop("harmless")
        ids.append(kid)
    kw.setdefault("families", {})[fid] = {"label": label, "keywords": ids, "task": "custom"}

    team = str(spec.get("team") or "").strip()
    if team:
        teams = (out.get("routing") or {}).get("teams") or {}
        if team not in teams:
            raise PolicyTableError(f"Team {team!r} gibt es in den Meldewegen nicht")
        out.setdefault("routing", {}).setdefault("rules", []).insert(0, {"when": {"family": fid}, "notify": [team]})

    pt = out.setdefault("policy_table", {}).setdefault("families", {})
    rules = [pe.clean_rule(r) for r in spec["rules"]]
    if not any(str(r["when"]).strip() == "true" for r in rules):
        rules.append({"id": f"{fid}.no_alert", "label": "no_alert", "when": "true",
                      "text": f"Kein Hinweis auf {label}."})
    entry: dict[str, Any] = {"facts": [pe.clean_fact(f) for f in spec["facts"]], "rules": rules}
    if str(spec.get("basis") or "").strip():
        entry = {"basis": " ".join(str(spec["basis"]).split()), **entry}
    pt[fid] = entry
    pe.validate(out["policy_table"])
    return out


def family_team(bundle: dict[str, dict], fid: str) -> list[str]:
    return [t for r in (bundle.get("routing") or {}).get("rules") or []
            if fid in _as_list((r.get("when") or {}).get("family")) for t in r.get("notify") or []]


def _as_list(v: Any) -> list[str]:
    return [str(x) for x in v] if isinstance(v, list) else ([str(v)] if v is not None else [])


# --------------------------------------------------------------------------------------------
# diff of the whole bundle in plain German
# --------------------------------------------------------------------------------------------


def _fam_name(bundle: dict[str, dict], fid: str, names: dict[str, str] | None) -> str:
    c = ((bundle.get("criteria") or {}).get("families") or {}).get(fid) or {}
    return (names or {}).get(fid) or str(c.get("label") or fid)


def diff_bundle(old: dict[str, dict], new: dict[str, dict], family_names: dict[str, str] | None = None,
                profile: str = "", check_kinds: dict[str, str] | None = None) -> list[str]:
    names = dict(family_names or {})
    for fid in family_ids(new):
        names.setdefault(fid, _fam_name(new, fid, None))
    out: list[str] = []
    ocrit = (old.get("criteria") or {}).get("families") or {}
    ncrit = (new.get("criteria") or {}).get("families") or {}
    new_fams = [f for f in family_ids(new) - family_ids(old)]
    for fid in sorted(new_fams):
        out.append(f"Neue Prüfart «{names[fid]}» ({fid})")
    for fid, c in ncrit.items():
        if fid in new_fams:
            continue
        o = ocrit.get(fid) or {}
        if (o.get("enabled", True) is not False) != (c.get("enabled", True) is not False):
            out.append(f"Prüfart «{names.get(fid, fid)}» {'eingeschaltet' if c.get('enabled', True) is not False else 'ausgeschaltet'}")
        for key, de in (("label", "Name"), ("policy", "Beschreibung"), ("alarm_when", "Alarmfälle"),
                        ("not_alarm_when", "harmlose Fälle"), ("review_when", "Prüffälle")):
            if o and o.get(key) != c.get(key):
                out.append(f"Prüfart «{names.get(fid, fid)}»: {de} geändert")
    out += [line for line in pe.diff_docs(old.get("policy_table") or {}, new.get("policy_table") or {}, names)
            if not line.endswith(": neue Art von Fehlverhalten")]
    okw, nkw = old.get("keywords") or {}, new.get("keywords") or {}
    owords = {k.get("id"): k for k in okw.get("keywords") or []}
    for fid, f in (nkw.get("families") or {}).items():
        ofam = (okw.get("families") or {}).get(fid) or {}
        kws = [k for k in nkw.get("keywords") or [] if k.get("id") in (f.get("keywords") or [])]
        added = [w for k in kws for w in k.get("de") or [] if w not in ((owords.get(k.get("id")) or {}).get("de") or [])]
        if added or set(f.get("keywords") or []) != set(ofam.get("keywords") or []):
            out.append(f"Stichwörter «{names.get(fid, fid)}»: " + (", ".join(f"+ {w}" for w in added) or "Liste geändert"))
    oroute, nroute = old.get("routing") or {}, new.get("routing") or {}
    if (oroute.get("rules") or []) != (nroute.get("rules") or []):
        for fid in sorted(family_ids(new)):
            a, b = family_team(old, fid), family_team(new, fid)
            if a != b:
                teams = (nroute.get("teams") or {})
                out.append(f"Meldeweg «{names.get(fid, fid)}» → "
                           + (", ".join(str((teams.get(t) or {}).get("name") or t) for t in b) or "kein eigenes Team"))
    a, b = checks_off(old, profile), checks_off(new, profile)
    for c in sorted(b - a):
        out.append(f"Prüfung «{(check_kinds or {}).get(c, c)}» ausgeschaltet (Profil {profile})")
    for c in sorted(a - b):
        out.append(f"Prüfung «{(check_kinds or {}).get(c, c)}» wieder eingeschaltet (Profil {profile})")
    if not out and changed_names(old, new):
        out.append("Formale Änderungen an: " + ", ".join(FILE_DE[n] for n in changed_names(old, new)))
    return out
