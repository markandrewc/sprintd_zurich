"""Load and save what the system looks for: keyword families (``keywords.json``, the case's
``Stichwortliste.json`` format) merged with the per-family criteria (``criteria.yaml``).

Both files are meant to be edited by a compliance officer through the UI; nothing here is code.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from callguard.types import Family, Keyword


def load_families(keywords_path: Path, criteria_path: Path | None = None,
                  only: list[str] | None = None) -> list[Family]:
    kw_raw = json.loads(Path(keywords_path).read_text())
    crit: dict[str, Any] = {}
    if criteria_path and Path(criteria_path).exists():
        crit = (yaml.safe_load(Path(criteria_path).read_text()) or {}).get("families", {})

    kw_by_id = {k["id"]: k for k in kw_raw.get("keywords", [])}
    policies = kw_raw.get("policy_examples", {})
    families: list[Family] = []
    fam_ids = list(dict.fromkeys([*kw_raw.get("families", {}).keys(), *crit.keys()]))
    for fid in fam_ids:
        f = kw_raw.get("families", {}).get(fid, {})
        c = crit.get(fid, {})
        keywords = []
        for kid in f.get("keywords", []):
            k = kw_by_id.get(kid)
            if not k:
                continue
            keywords.append(Keyword(
                id=k["id"], label=k.get("label", k["id"]), de=k.get("de", []), gsw=k.get("gsw", []),
                en=k.get("en", []), harmless=k.get("harmless"), enabled=k.get("enabled", True),
                case_sensitive=k.get("case_sensitive", False),
            ))
        fam = Family(
            id=fid,
            label=c.get("label") or f.get("label", fid),
            task=f.get("task"),
            policy=c.get("policy") or policies.get(fid, ""),
            alarm_when=c.get("alarm_when", []),
            not_alarm_when=c.get("not_alarm_when", []),
            review_when=c.get("review_when", []),
            keywords=keywords,
            enabled=c.get("enabled", True),
            can_alarm=c.get("can_alarm", True),
        )
        if only is not None and fid not in only:
            continue
        families.append(fam)
    return families


def save_keywords(families: list[Family], keywords_path: Path) -> None:
    """Write keyword edits back, keeping every field of the original file we don't model, the file's
    keyword order, and leaving defaults unwritten where the entry had none: a no-op save from the UI
    leaves the file byte-identical, so officer edits show up as small diffs."""
    path = Path(keywords_path)
    raw = json.loads(path.read_text()) if path.exists() else {"families": {}, "keywords": []}
    old_list: list[dict] = raw.get("keywords", [])
    edited: dict[str, Keyword] = {}
    for fam in families:
        fam_entry = raw.setdefault("families", {}).setdefault(fam.id, {"label": fam.label})
        fam_entry["keywords"] = [k.id for k in fam.keywords]
        for k in fam.keywords:
            edited.setdefault(k.id, k)  # an id shared by two families: the first family's version wins

    def entry_for(k: Keyword, old: dict) -> dict:
        entry = dict(old)
        entry.update(id=k.id, label=k.label, de=k.de, gsw=k.gsw)
        if k.en or "en" in old:
            entry["en"] = k.en
        for name, default in (("enabled", True), ("case_sensitive", False)):
            value = getattr(k, name)
            if name in old or value != default:
                entry[name] = value
        if k.harmless is not None:
            entry["harmless"] = k.harmless
        return entry

    known = {e.get("id") for e in old_list}
    # keywords that belong to no family we know stay as they were (don't silently drop data)
    new_keywords = [entry_for(edited[e["id"]], e) if e.get("id") in edited else e for e in old_list]
    new_keywords += [entry_for(k, {}) for kid, k in edited.items() if kid not in known]
    raw["keywords"] = new_keywords
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")


def family_policy_view(f: Family) -> dict[str, Any]:
    """The fields an LLM check reads. Used as cache key so keyword-list edits don't rerun LLMs."""
    return {
        "id": f.id, "label": f.label, "policy": f.policy, "alarm_when": f.alarm_when,
        "not_alarm_when": f.not_alarm_when, "review_when": f.review_when, "can_alarm": f.can_alarm,
    }
