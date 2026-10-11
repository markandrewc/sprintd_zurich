"""Notify the right person: flagged call -> teams, supervisor cc, message (docs/design/v2_plan.md §3).

* ``config/routing.yaml``: teams + rules (``family`` / ``label`` / ``pattern`` / ``min_score`` -> teams,
  ``cc_supervisor``), ``supervisor_cc_on`` labels, ``fallback`` teams, ``labels`` routed at all.
* ``config/directory.yaml``: advisors -> unit + supervisor (fictional stand-in for the HR system).

:func:`route` is pure and cheap (the UI calls it for every call shown, under the live threshold);
:func:`build_message` renders what a desk receives: label, families, deep link (``?call=..&t=..``),
passages with times + reasons, snippet paths. Delivery is :mod:`callguard.sinks.notify`.

Routing runs strictly AFTER the decision: nothing here can change a label.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from callguard.config import ROOT, AppConfig
from callguard.types import CallResult, Decision, Passage, fmt_ts

DEFAULT_ROUTING = "config/routing.yaml"
DEFAULT_DIRECTORY = "config/directory.yaml"


def resolve(path: str | Path | None, default: str) -> Path:
    p = Path(path or default)
    return p if p.is_absolute() else ROOT / p


def _fold(text: str) -> str:
    text = text.replace("ß", "ss")
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).lower().strip()


def _as_list(v: Any) -> list[Any]:
    if v is None:
        return []
    return list(v) if isinstance(v, (list, tuple, set)) else [v]


def _email_of(name: str, domain: str = "bank.example") -> str:
    local = ".".join(re.sub(r"[^a-z]", "", _fold(part.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")))
                     for part in name.split())
    return f"{local}@{domain}"


# --------------------------------------------------------------------------------------------
# Directory (who is who)
# --------------------------------------------------------------------------------------------


@dataclass
class Person:
    id: str
    name: str
    email: str = ""
    unit: str = ""
    supervisor: str | None = None  # supervisor id (advisors only)


@dataclass
class Directory:
    advisors: dict[str, Person] = field(default_factory=dict)
    supervisors: dict[str, Person] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Directory":
        p = resolve(path, DEFAULT_DIRECTORY)
        if not p.is_file():
            return cls()
        raw = yaml.safe_load(p.read_text()) or {}

        def people(block: dict[str, Any] | None) -> dict[str, Person]:
            out = {}
            for pid, d in (block or {}).items():
                d = d or {}
                name = str(d.get("name", pid))
                out[str(pid)] = Person(id=str(pid), name=name, email=str(d.get("email") or _email_of(name)),
                                       unit=str(d.get("unit", "")), supervisor=d.get("supervisor"))
            return out

        return cls(advisors=people(raw.get("advisors")), supervisors=people(raw.get("supervisors")))

    def advisor(self, key: str | None) -> Person | None:
        """By id or by (accent/case-insensitive) full name."""
        if not key:
            return None
        if key in self.advisors:
            return self.advisors[key]
        k = _fold(key)
        return next((a for a in self.advisors.values() if _fold(a.name) == k), None)

    def supervisor_of(self, advisor: Person | None) -> Person | None:
        return self.supervisors.get(advisor.supervisor) if advisor and advisor.supervisor else None


# --------------------------------------------------------------------------------------------
# Routing rules
# --------------------------------------------------------------------------------------------


@dataclass
class Team:
    id: str
    name: str
    email: str = ""
    webhook: str | None = None


@dataclass
class Rule:
    when: dict[str, Any]
    notify: list[str]
    cc_supervisor: bool = False


@dataclass
class RoutingConfig:
    teams: dict[str, Team] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    labels: list[str] = field(default_factory=lambda: ["alarm", "review"])
    supervisor_cc_on: list[str] = field(default_factory=lambda: ["alarm"])
    fallback: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "RoutingConfig":
        p = resolve(path, DEFAULT_ROUTING)
        if not p.is_file():
            return cls()
        return cls.from_dict(yaml.safe_load(p.read_text()) or {})

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "RoutingConfig":
        teams = {str(k): Team(id=str(k), name=str((v or {}).get("name", k)), email=str((v or {}).get("email", "")),
                              webhook=(v or {}).get("webhook")) for k, v in (raw.get("teams") or {}).items()}
        rules = [Rule(when=dict(r.get("when") or {}), notify=[str(t) for t in _as_list(r.get("notify"))],
                      cc_supervisor=bool(r.get("cc_supervisor", False))) for r in raw.get("rules") or []]
        unknown = sorted({t for r in rules for t in r.notify} - set(teams))
        if unknown:
            raise ValueError(f"routing rules name unknown teams: {unknown} (define them under teams:)")
        return cls(teams=teams, rules=rules, labels=[str(x) for x in _as_list(raw.get("labels", ["alarm", "review"]))],
                   supervisor_cc_on=[str(x) for x in _as_list(raw.get("supervisor_cc_on", ["alarm"]))],
                   fallback=[str(x) for x in _as_list(raw.get("fallback"))])


@dataclass
class Recipient:
    kind: str  # team | supervisor
    id: str
    name: str
    email: str = ""
    why: list[str] = field(default_factory=list)


@dataclass
class Route:
    call_id: str
    label: str
    families: list[str]
    to: list[Recipient] = field(default_factory=list)
    cc: list[Recipient] = field(default_factory=list)
    advisor: dict[str, Any] | None = None
    patterns: list[str] = field(default_factory=list)  # pattern flags that apply to this call

    @property
    def routed(self) -> bool:
        return bool(self.to or self.cc)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def flagged_families(decision: Decision) -> list[str]:
    """Families the call is flagged for: the top family, then every passage family (in order)."""
    out: list[str] = []
    for f in [decision.top_family, *(p.family for p in decision.passages)]:
        if f and f not in out:
            out.append(f)
    return out


def call_patterns(call_id: str, entities: dict[str, Any] | None, analysis: dict[str, Any] | None) -> list[str]:
    """Pattern flag kinds (``callguard.patterns.analyze``) that concern this call: its advisor, its
    customer or one of its companies is flagged, or the flag lists the call explicitly."""
    if not analysis:
        return []
    ent = entities or {}
    subjects = {("advisor", ent.get("advisor_key")), ("customer", ent.get("customer_key"))}
    subjects |= {("company", c) for c in ent.get("company_keys") or []}
    out = []
    for flag in analysis.get("flags") or []:
        hit = (flag.get("subject_type"), flag.get("subject")) in subjects or call_id in (flag.get("calls") or [])
        if hit and flag.get("kind") not in out:
            out.append(flag["kind"])
    return out


def _matches(when: dict[str, Any], label: str, families: list[str], patterns: list[str], score: float) -> bool:
    for key, want in when.items():
        wanted = {str(w) for w in _as_list(want)}
        if key == "family" and not wanted & set(families):
            return False
        if key == "label" and label not in wanted:
            return False
        if key == "pattern" and not wanted & set(patterns):
            return False
        if key == "min_score" and score < float(want):
            return False
        if key not in ("family", "label", "pattern", "min_score"):
            raise ValueError(f"unknown routing condition {key!r} (family, label, pattern, min_score)")
    return True


def route(result: CallResult, cfg: RoutingConfig, directory: Directory | None = None, *,
          decision: Decision | None = None, entities: dict[str, Any] | None = None,
          analysis: dict[str, Any] | None = None) -> Route:
    """Who is told about this call. ``decision`` overrides the stored one (UI: live threshold);
    ``entities`` (``checks.entities.entities_of``) names the advisor; ``analysis``
    (``patterns.analyze``) feeds ``pattern:`` rules. A label outside ``cfg.labels`` routes nowhere."""
    d = decision or result.decision
    directory = directory or Directory()
    fams = flagged_families(d)
    ent = entities or {}
    adv_name = (ent.get("advisor") or {}).get("name") if isinstance(ent.get("advisor"), dict) else None
    adv_id = (ent.get("advisor") or {}).get("id") if isinstance(ent.get("advisor"), dict) else None
    advisor = directory.advisor(adv_id) or directory.advisor(adv_name)
    pats = call_patterns(result.call_id, ent, analysis)
    r = Route(call_id=result.call_id, label=d.label, families=fams, patterns=pats,
              advisor={"id": advisor.id, "name": advisor.name, "unit": advisor.unit} if advisor
              else ({"id": adv_id, "name": adv_name} if adv_name or adv_id else None))
    if d.label not in cfg.labels:
        return r

    to: dict[str, Recipient] = {}
    cc_sup: list[str] = []

    def add_team(tid: str, why: str) -> None:
        team = cfg.teams.get(tid)
        if team is None:
            return
        rec = to.setdefault(tid, Recipient(kind="team", id=tid, name=team.name, email=team.email))
        if why not in rec.why:
            rec.why.append(why)

    for rule in cfg.rules:
        if _matches(rule.when, d.label, fams, pats, d.score):
            why = ", ".join(f"{k}={'/'.join(map(str, _as_list(v)))}" for k, v in rule.when.items()) or "always"
            for tid in rule.notify:
                add_team(tid, why)
            if rule.cc_supervisor:
                cc_sup.append(f"rule {why}")
    if not to:
        for tid in cfg.fallback:
            add_team(tid, "fallback (no rule matched)")
    if d.label in cfg.supervisor_cc_on:
        cc_sup.append(f"label={d.label}")
    sup = directory.supervisor_of(advisor)
    if cc_sup and sup is not None:
        r.cc.append(Recipient(kind="supervisor", id=sup.id, name=sup.name, email=sup.email,
                              why=[f"supervisor of {advisor.name} ({'; '.join(cc_sup)})"]))
    r.to = list(to.values())
    return r


# --------------------------------------------------------------------------------------------
# Message
# --------------------------------------------------------------------------------------------

LABEL_DE = {"alarm": "ALARM", "review": "PRÜFEN", "no_alert": "KEIN ALARM"}


def deep_link(cfg: AppConfig, call_id: str, start: float | None = None) -> str:
    """``<base_url>/?call=<id>&t=<s>``, ``link_pad`` seconds before the passage (like the Outcept sink)."""
    base = str(cfg.app.get("base_url", "http://localhost:8501")).rstrip("/")
    url = f"{base}/?call={quote(call_id, safe='')}"
    if start is not None:
        pad = float(cfg.snippets.get("link_pad", 10.0))
        url += f"&t={max(0, int(start - pad))}"
    return url


def _passage_dict(cfg: AppConfig, call_id: str, p: Passage) -> dict[str, Any]:
    return {"family": p.family, "family_label": p.family_label or p.family, "start": round(p.start, 2),
            "end": round(p.end, 2), "time": f"{fmt_ts(p.start)}-{fmt_ts(p.end)}", "score": round(p.score, 3),
            "reasons": list(p.reasons), "checks": list(p.checks), "text": p.text[:400],
            "snippet_path": p.snippet_path, "link": deep_link(cfg, call_id, p.start)}


def build_message(result: CallResult, r: Route, cfg: AppConfig, *, decision: Decision | None = None) -> dict[str, Any]:
    """The notification as data (outbox / webhook) plus ``subject`` + plain-text ``body`` (mail)."""
    d = decision or result.decision
    fam_labels = {fid: (d.families[fid].label if fid in d.families else fid) for fid in r.families}
    top = d.top_family or (r.families[0] if r.families else None)
    first = d.passages[0].start if d.passages else None
    passages = [_passage_dict(cfg, result.call_id, p) for p in d.passages]
    short = (fam_labels.get(top, top) or "unklar").split(" (")[0]
    subject = f"[{LABEL_DE.get(d.label, d.label)}] {short} - {result.call_id}"
    link = deep_link(cfg, result.call_id, first)
    lines = [f"{LABEL_DE.get(d.label, d.label)}: Anruf {result.call_id}, Score {d.score:.2f} "
             f"(Schwelle {d.threshold:.2f}, Unsicherheit {d.uncertainty:.2f}).",
             f"Familien: {', '.join(fam_labels.get(f, f) for f in r.families) or '-'}"]
    if r.advisor:
        lines.append(f"Beratung: {r.advisor.get('name') or r.advisor.get('id')}"
                     + (f" ({r.advisor['unit']})" if r.advisor.get("unit") else ""))
    if r.patterns:
        lines.append(f"Muster über mehrere Anrufe: {', '.join(r.patterns)}")
    lines += [f"Direkt anhören: {link}", "", "Entscheid:", *[f"- {x}" for x in d.reasons]]
    for i, p in enumerate(passages, 1):
        lines += ["", f"Passage {i}: {p['time']} {p['family_label']} (Score {p['score']:.2f})",
                  *[f"- {x}" for x in p["reasons"]]]
        if p["text"]:
            lines.append(f'  Wortlaut: "{p["text"]}"')
        lines.append(f"  Link: {p['link']}" + (f" · Audio: {p['snippet_path']}" if p["snippet_path"] else ""))
    return {
        "call_id": result.call_id, "label": d.label, "score": round(d.score, 4), "threshold": d.threshold,
        "uncertainty": round(d.uncertainty, 4), "top_family": top, "families": r.families,
        "family_labels": fam_labels, "link": link, "subject": subject, "body": "\n".join(lines),
        "to": [asdict(x) for x in r.to], "cc": [asdict(x) for x in r.cc], "advisor": r.advisor,
        "patterns": r.patterns, "passages": passages, "config_name": result.config_name,
    }
