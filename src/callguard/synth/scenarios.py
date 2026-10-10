"""Scenario seeds for synthetic scripts (``config/synth_scenarios.yaml``) and the generation plan.

A scenario is one situation (setting, speakers, who opens) with twin VARIANTS that differ only in the
decisive context; each variant carries its expected label. The plan numbers the variants per scenario
family in file order: ``Synth_trade_001`` .. (stable as long as scenarios are appended, not inserted).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from callguard.config import ROOT

DEFAULT_SCENARIOS = ROOT / "config" / "synth_scenarios.yaml"
FAMILIES = ("trade", "access", "disclosure", "documentation", "splitting", "numbers")
LABELS = ("alarm", "review", "no_alert")
DEFAULT_EVENT = {"alarm": "present", "no_alert": "absent", "review": "undetermined"}
CUSTOMERS = ("Kundin", "Kunde")
OPENERS = ("advisor", "customer")
MIN_TURNS, MAX_TURNS = 12, 30
_SCENARIO_KEYS = {"id", "family", "customer", "opens", "turns", "setting", "must_include", "variants", "dialect",
                  "language"}
LANGUAGES = ("de", "gsw")  # de: Swiss Standard German (what the de ASR view produces); gsw: dialect
_VARIANT_KEYS = {"label", "decisive", "reason", "open", "event", "family", "must_include"}


class ScenarioError(ValueError):
    pass


@dataclass
class Variant:
    name: str
    label: str
    decisive: str
    reason: str
    open: str = ""
    event: str = ""
    family: str = ""  # effective Testziel ("" = the scenario's family)
    must_include: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    id: str
    family: str
    customer: str
    opens: str
    turns: int
    setting: str
    dialect: str
    must_include: list[str]
    variants: list[Variant]
    language: str = "de"


@dataclass
class Job:
    """One script to write."""
    dialogue_id: str  # Synth_trade_001
    scenario: Scenario
    variant: Variant
    base: bool  # first variant of its scenario (written freely; its twins are rewrites of it)

    @property
    def family(self) -> str:
        return self.variant.family or self.scenario.family

    @property
    def call_id(self) -> str:
        return f"{self.dialogue_id}-K1"

    @property
    def event(self) -> str:
        return self.variant.event or DEFAULT_EVENT[self.variant.label]

    @property
    def must_include(self) -> list[str]:
        return [*self.scenario.must_include, *self.variant.must_include]

    @property
    def turn_range(self) -> tuple[int, int]:
        t = self.scenario.turns
        return max(MIN_TURNS, t - 4), min(MAX_TURNS, t + 6)


def _str_list(x: Any, where: str) -> list[str]:
    if x is None:
        return []
    if isinstance(x, (str, int, float)):
        return [str(x)]
    if not isinstance(x, list):
        raise ScenarioError(f"{where}: must_include must be a list of strings")
    return [str(i) for i in x]


def parse_scenarios(raw: dict[str, Any]) -> list[Scenario]:
    if not isinstance(raw, dict) or not isinstance(raw.get("families"), dict):
        raise ScenarioError("scenario file needs a `families:` mapping")
    d = raw.get("defaults") or {}
    out: list[Scenario] = []
    seen: set[str] = set()
    for fam, entries in raw["families"].items():
        if fam not in FAMILIES:
            raise ScenarioError(f"unknown family {fam!r} (expected one of {FAMILIES})")
        for i, e in enumerate(entries or []):
            where = f"{fam}[{i}]"
            if not isinstance(e, dict):
                raise ScenarioError(f"{where}: expected a mapping")
            bad = set(e) - _SCENARIO_KEYS
            if bad:
                raise ScenarioError(f"{where}: unknown keys {sorted(bad)}")
            sid = str(e.get("id") or "")
            if not sid or sid in seen:
                raise ScenarioError(f"{where}: missing or duplicate id {sid!r}")
            seen.add(sid)
            customer = str(e.get("customer") or d.get("customer") or "Kundin")
            opens = str(e.get("opens") or d.get("opens") or "advisor")
            turns = int(e.get("turns") or d.get("turns") or 18)
            if customer not in CUSTOMERS:
                raise ScenarioError(f"{sid}: customer must be one of {CUSTOMERS}")
            if opens not in OPENERS:
                raise ScenarioError(f"{sid}: opens must be one of {OPENERS}")
            if not MIN_TURNS <= turns <= MAX_TURNS:
                raise ScenarioError(f"{sid}: turns must be within {MIN_TURNS}..{MAX_TURNS}")
            language = str(e.get("language") or d.get("language") or "de")
            if language not in LANGUAGES:
                raise ScenarioError(f"{sid}: language must be one of {LANGUAGES}")
            if not str(e.get("setting") or "").strip():
                raise ScenarioError(f"{sid}: setting is empty")
            variants: list[Variant] = []
            for vname, v in (e.get("variants") or {}).items():
                vw = f"{sid}.{vname}"
                if not isinstance(v, dict):
                    raise ScenarioError(f"{vw}: expected a mapping")
                bad = set(v) - _VARIANT_KEYS
                if bad:
                    raise ScenarioError(f"{vw}: unknown keys {sorted(bad)}")
                label = str(v.get("label") or "")
                if label not in LABELS:
                    raise ScenarioError(f"{vw}: label must be one of {LABELS}, got {label!r}")
                vf = str(v.get("family") or "")
                if vf and vf not in FAMILIES:
                    raise ScenarioError(f"{vw}: unknown family {vf!r}")
                if (vf or fam) == "numbers" and label != "no_alert":
                    raise ScenarioError(f"{vw}: numbers never alarms; give the variant another family")
                if not str(v.get("decisive") or "").strip() or not str(v.get("reason") or "").strip():
                    raise ScenarioError(f"{vw}: decisive and reason are required")
                if label == "review" and not str(v.get("open") or "").strip():
                    raise ScenarioError(f"{vw}: a review variant needs `open` (what stays undecided)")
                variants.append(Variant(name=str(vname), label=label, decisive=" ".join(str(v["decisive"]).split()),
                                        reason=" ".join(str(v["reason"]).split()),
                                        open=" ".join(str(v.get("open") or "").split()),
                                        event=str(v.get("event") or ""), family=vf,
                                        must_include=_str_list(v.get("must_include"), vw)))
            if len(variants) < 2:
                raise ScenarioError(f"{sid}: needs at least two variants (twins)")
            out.append(Scenario(id=sid, family=fam, customer=customer, opens=opens, turns=turns,
                                setting=" ".join(str(e["setting"]).split()),
                                dialect=str(e.get("dialect") or d.get("dialect") or "Zürichdeutsch"),
                                must_include=_str_list(e.get("must_include"), where), variants=variants,
                                language=language))
    return out


def load_scenarios(path: str | Path | None = None) -> list[Scenario]:
    p = Path(path) if path else DEFAULT_SCENARIOS
    return parse_scenarios(yaml.safe_load(p.read_text(encoding="utf-8")) or {})


def plan(scenarios: list[Scenario]) -> list[Job]:
    """Jobs in file order; ids numbered per scenario family (twins get consecutive numbers)."""
    counter: dict[str, int] = {}
    jobs: list[Job] = []
    for s in scenarios:
        for j, v in enumerate(s.variants):
            counter[s.family] = counter.get(s.family, 0) + 1
            jobs.append(Job(dialogue_id=f"Synth_{s.family}_{counter[s.family]:03d}", scenario=s, variant=v,
                            base=j == 0))
    return jobs


def summary(jobs: list[Job]) -> dict[str, dict[str, int]]:
    """family (effective) -> label -> count."""
    out: dict[str, dict[str, int]] = {}
    for j in jobs:
        out.setdefault(j.family, {}).setdefault(j.variant.label, 0)
        out[j.family][j.variant.label] += 1
    return out
