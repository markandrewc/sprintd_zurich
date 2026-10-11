"""Fact policy: how the two AI readers' answers become one fact value (ja / nein / unklar). Pure, no models.

The officer's mental model (demo tabs «Fakten» and «Regeln»):

* **Facts** are small yes/no questions per Prüfart. Two AI readers answer every fact with probabilities:
  reader A (Qwen2.5-7B, check ``facts``: p(ja), p(nein), p(unklar)) and reader B (Kev-4B, check ``facts_kev``:
  p(ja) only). Both answers are stored per call.
* **Resolution per reader** (this module): p -> ja / unklar / nein, either ``three_way`` (ja if p(ja) >= 0.5,
  nein if p(nein) >= 0.5, else unklar) or a ``band`` [lo, hi] on p(ja) (ja if p >= hi, nein if p <= lo, else
  unklar). A wider band = more «unklar» = more Prüfen. Global per reader, optional per-fact override.
* **Combination of the two readers per fact**: ``only_a`` (Nur Qwen), ``only_b`` (Nur Kev), ``agree``
  (Einigkeit: both ja -> ja, both nein -> nein, else unklar) or ``a_checked`` (Qwen, Kev als Kontrolle: Qwen's
  value unless Kev clearly says the opposite -> unklar).
* **Rules** are pure logic over the resolved values (``checks/facts.py``: first matching rule decides).

Defaults (``config/fact_policy.yaml``) are the pre-registered ones (research/findings/dual_facts_prereg.md):
Qwen three-way, Kev band [0.3, 0.7], Einigkeit. The live seam is the ``two_readers`` fusion with
``rule: policy`` (:mod:`callguard.fusion.two_readers`): it builds one combined facts result per call with
:func:`combined_result` and hands it to the weighted fusion, so the call label (threshold, review band, light
keyword / pattern checks) is decided exactly as for one reader. The demo re-decides every stored call with
:func:`redecide` for each band / rule the officer tries (no LLM, well under a second for 160 calls).
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from callguard.cache import stable_hash
from callguard.checks.facts import (
    CROSS_FAMILY,
    CROSS_LABEL,
    FamilyTable,
    PolicyTable,
    PolicyTableError,
    average_probs,
    decide_family,
    discretize,
    rule_facts,
)
from callguard.config import ROOT
from callguard.types import CallResult, CheckResult, FamilyScore

DEFAULT_PATH = "config/fact_policy.yaml"
VALUES = ("yes", "no", "unclear")
VALUE_DE = {"yes": "ja", "no": "nein", "unclear": "unklar"}
MODES = ("three_way", "band")
COMBINATIONS = ("only_a", "only_b", "agree", "a_checked")
# on_split: what a family becomes when the two readers ALONE would reach different verdicts (each reader's own
# values through the same rules): "rules" = nothing extra, the combined facts decide (default); "review" / "alarm"
# = at least Prüfen / Alarm. Never lowers a verdict.
ON_SPLIT = ("rules", "review", "alarm")
SEVERITY = {"no_alert": 0, "review": 1, "alarm": 2}
_LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}


class FactPolicyError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# the policy
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ReaderSpec:
    """One AI reader: which check holds its answers and how its p becomes ja / nein / unklar."""

    id: str  # short key used in overrides ("qwen", "kev")
    check: str  # the facts check instance whose stored answers this reader is ("facts", "facts_kev")
    label: str  # shown to the officer ("Qwen")
    model: str = ""  # display only ("Qwen2.5-7B")
    mode: str = "three_way"  # three_way | band
    lo: float = 0.3
    hi: float = 0.7
    decide_at: float = 0.5  # three_way

    def resolve(self, p: Mapping[str, float] | None) -> str:
        """ja / nein / unklar for one answer distribution. No answer (reader missing) = unklar."""
        if not p:
            return "unclear"
        if self.mode == "band":
            py = float(p.get("yes", 0.0))
            return "yes" if py >= self.hi else ("no" if py <= self.lo else "unclear")
        return discretize(dict(p), self.decide_at)

    def describe(self) -> str:
        if self.mode == "band":
            return f"Band {self.lo:.2f}–{self.hi:.2f}"
        return f"drei Antworten (≥ {self.decide_at:.2f})"

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "check": self.check, "label": self.label}
        if self.model:
            out["model"] = self.model
        out["mode"] = self.mode
        out["band"] = [round(self.lo, 4), round(self.hi, 4)]
        if self.decide_at != 0.5:
            out["decide_at"] = self.decide_at
        return out


def _band(raw: Any, where: str) -> tuple[float, float]:
    try:
        lo, hi = (float(x) for x in raw)
    except (TypeError, ValueError):
        raise FactPolicyError(f"{where}: band must be [lo, hi], got {raw!r}") from None
    if not 0.0 <= lo <= hi <= 1.0:
        raise FactPolicyError(f"{where}: band needs 0 <= lo <= hi <= 1, got {raw!r}")
    return lo, hi


def _reader(raw: Any, where: str) -> ReaderSpec:
    if not isinstance(raw, dict):
        raise FactPolicyError(f"{where}: expected a mapping")
    bad = set(raw) - {"id", "check", "label", "model", "mode", "band", "decide_at"}
    if bad:
        raise FactPolicyError(f"{where}: unknown keys {sorted(bad)}")
    rid, check = str(raw.get("id") or ""), str(raw.get("check") or "")
    if not rid or not check:
        raise FactPolicyError(f"{where}: needs id and check")
    mode = str(raw.get("mode") or "three_way")
    if mode not in MODES:
        raise FactPolicyError(f"{where}: mode must be one of {MODES}, got {mode!r}")
    lo, hi = _band(raw.get("band", [0.3, 0.7]), where)
    decide_at = float(raw.get("decide_at", 0.5))
    if not 1 / 3 < decide_at <= 1.0:
        raise FactPolicyError(f"{where}: decide_at must be in (1/3, 1]")
    return ReaderSpec(id=rid, check=check, label=str(raw.get("label") or rid), model=str(raw.get("model") or ""),
                      mode=mode, lo=lo, hi=hi, decide_at=decide_at)


@dataclass(frozen=True)
class FactOverride:
    """Per-fact exceptions to the global settings (only what is set here differs)."""

    readers: dict[str, dict[str, Any]] = field(default_factory=dict)  # reader id -> {mode?, band?}
    combination: str | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {rid: dict(v) for rid, v in self.readers.items() if v}
        if self.combination:
            out["combination"] = self.combination
        return out

    def empty(self) -> bool:
        return not self.combination and not any(self.readers.values())


@dataclass(frozen=True)
class FactPolicy:
    readers: tuple[ReaderSpec, ReaderSpec]  # (A = primary, with evidence; B = second reader)
    combination: str = "agree"
    overrides: dict[str, FactOverride] = field(default_factory=dict)  # "family.fact" -> override
    source: str = ""
    on_split: str = "rules"  # see ON_SPLIT

    # -- lookups -----------------------------------------------------------------------------------

    @property
    def a(self) -> ReaderSpec:
        return self.readers[0]

    @property
    def b(self) -> ReaderSpec:
        return self.readers[1]

    def reader(self, i: int, family: str | None = None, fact: str | None = None) -> ReaderSpec:
        """Reader ``i`` (0 = A, 1 = B) with the per-fact override applied."""
        spec = self.readers[i]
        ov = self.overrides.get(f"{family}.{fact}") if family and fact else None
        o = (ov.readers.get(spec.id) or {}) if ov else {}
        if not o:
            return spec
        lo, hi = _band(o["band"], f"override {family}.{fact}") if "band" in o else (spec.lo, spec.hi)
        return ReaderSpec(id=spec.id, check=spec.check, label=spec.label, model=spec.model,
                          mode=str(o.get("mode") or ("band" if "band" in o else spec.mode)), lo=lo, hi=hi,
                          decide_at=spec.decide_at)

    def combination_for(self, family: str | None = None, fact: str | None = None) -> str:
        ov = self.overrides.get(f"{family}.{fact}") if family and fact else None
        return (ov.combination if ov and ov.combination else self.combination)

    def has_override(self, family: str, fact: str) -> bool:
        ov = self.overrides.get(f"{family}.{fact}")
        return ov is not None and not ov.empty()

    def combination_de(self, mode: str | None = None) -> str:
        return combination_label(mode or self.combination, self.a.label, self.b.label)

    # -- editing (pure: return a new policy) -----------------------------------------------------------

    def with_reader(self, i: int, **changes: Any) -> "FactPolicy":
        spec = self.readers[i]
        d = {**spec.__dict__, **changes}
        new = ReaderSpec(**d)
        if new.mode not in MODES or not 0.0 <= new.lo <= new.hi <= 1.0:
            raise FactPolicyError(f"invalid reader settings {changes!r}")
        readers = (new, self.b) if i == 0 else (self.a, new)
        return FactPolicy(readers=readers, combination=self.combination, overrides=dict(self.overrides),
                          source=self.source, on_split=self.on_split)

    def with_certainty(self, c: float, readers: str = "both") -> "FactPolicy":
        """The «Sicherheit der KI» knob: ja if p(ja) >= c, nein if p(ja) <= 1 - c, else unklar, for both readers
        (``readers="both"``) or reader B only (``"b"``, reader A keeps its own rule). Per-fact overrides stay."""
        c = float(c)
        if not 0.5 <= c <= 1.0:
            raise FactPolicyError(f"certainty must be within 0.5..1, got {c}")
        lo, hi = round(1.0 - c, 4), round(c, 4)
        pol = self.with_reader(1, mode="band", lo=lo, hi=hi)
        return pol.with_reader(0, mode="band", lo=lo, hi=hi) if readers == "both" else pol

    def certainty(self) -> float:
        """The current knob value (reader B's upper band edge)."""
        return round(float(self.b.hi), 4)

    def with_combination(self, mode: str) -> "FactPolicy":
        if mode not in COMBINATIONS:
            raise FactPolicyError(f"combination must be one of {COMBINATIONS}, got {mode!r}")
        return FactPolicy(readers=self.readers, combination=mode, overrides=dict(self.overrides), source=self.source,
                          on_split=self.on_split)

    def with_on_split(self, mode: str) -> "FactPolicy":
        if mode not in ON_SPLIT:
            raise FactPolicyError(f"on_split must be one of {ON_SPLIT}, got {mode!r}")
        return FactPolicy(readers=self.readers, combination=self.combination, overrides=dict(self.overrides),
                          source=self.source, on_split=mode)

    def with_override(self, family: str, fact: str, *, reader: str | None = None, band: Iterable[float] | None = None,
                      mode: str | None = None, combination: str | None = None, clear: bool = False) -> "FactPolicy":
        """Set (or with ``clear`` remove) one per-fact exception. ``reader``: reader id for band / mode."""
        key = f"{family}.{fact}"
        ov = self.overrides.get(key) or FactOverride()
        readers = {k: dict(v) for k, v in ov.readers.items()}
        comb = ov.combination
        if clear:
            if reader:
                readers.pop(reader, None)
            else:
                readers, comb = {}, None
        if reader and not clear:
            r = readers.setdefault(reader, {})
            if band is not None:
                r["band"] = list(_band(list(band), key))
                r.setdefault("mode", "band")
            if mode is not None:
                if mode not in MODES:
                    raise FactPolicyError(f"mode must be one of {MODES}")
                r["mode"] = mode
        if combination is not None and not clear:
            if combination not in COMBINATIONS:
                raise FactPolicyError(f"combination must be one of {COMBINATIONS}")
            comb = combination
        new_ov = FactOverride(readers={k: v for k, v in readers.items() if v}, combination=comb)
        overrides = {k: v for k, v in self.overrides.items() if k != key}
        if not new_ov.empty():
            overrides[key] = new_ov
        return FactPolicy(readers=self.readers, combination=self.combination, overrides=overrides, source=self.source,
                          on_split=self.on_split)

    # -- (de)serialisation -------------------------------------------------------------------------

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"readers": [r.as_dict() for r in self.readers], "combination": self.combination}
        ovs = {k: v.as_dict() for k, v in sorted(self.overrides.items()) if not v.empty()}
        if ovs:
            out["overrides"] = ovs
        if self.on_split != "rules":  # only when set, so the key (and every cache) of existing policies is unchanged
            out["on_split"] = self.on_split
        return out

    def key(self) -> str:
        return stable_hash(self.as_dict())


def combination_label(mode: str, a: str = "Qwen", b: str = "Kev") -> str:
    return {"only_a": f"Nur {a}", "only_b": f"Nur {b}", "agree": "Einigkeit",
            "a_checked": f"{a}, {b} als Kontrolle"}.get(mode, mode)


def combination_help(mode: str, a: str = "Qwen", b: str = "Kev") -> str:
    return {"only_a": f"Nur {a} zählt; {b}s Antwort wird angezeigt, entscheidet aber nicht.",
            "only_b": f"Nur {b} zählt; {a}s Antwort wird angezeigt, entscheidet aber nicht.",
            "agree": "Beide ja → ja, beide nein → nein, sonst unklar (→ die Prüfen-Regeln greifen).",
            "a_checked": f"{a} entscheidet, ausser {b} sagt klar das Gegenteil → unklar."}.get(mode, "")


def parse_fact_policy(raw: Any, source: str = "fact policy") -> FactPolicy:
    if not isinstance(raw, dict):
        raise FactPolicyError(f"{source}: expected a mapping")
    bad = set(raw) - {"readers", "combination", "overrides", "on_split"}
    if bad:
        raise FactPolicyError(f"{source}: unknown keys {sorted(bad)}")
    rs = raw.get("readers") or []
    if not isinstance(rs, list) or len(rs) != 2:
        raise FactPolicyError(f"{source}: readers must list exactly two readers (A, B)")
    a, b = (_reader(r, f"{source}: reader #{i + 1}") for i, r in enumerate(rs))
    if a.id == b.id or a.check == b.check:
        raise FactPolicyError(f"{source}: the two readers need different ids and checks")
    comb = str(raw.get("combination") or "agree")
    if comb not in COMBINATIONS:
        raise FactPolicyError(f"{source}: combination must be one of {COMBINATIONS}, got {comb!r}")
    on_split = str(raw.get("on_split") or "rules")
    if on_split not in ON_SPLIT:
        raise FactPolicyError(f"{source}: on_split must be one of {ON_SPLIT}, got {on_split!r}")
    overrides: dict[str, FactOverride] = {}
    for key, ov in (raw.get("overrides") or {}).items():
        where = f"{source}: override {key}"
        if "." not in str(key) or not isinstance(ov, dict):
            raise FactPolicyError(f"{where}: key must be <family>.<fact> with a mapping")
        readers: dict[str, dict[str, Any]] = {}
        c = ov.get("combination")
        if c is not None and c not in COMBINATIONS:
            raise FactPolicyError(f"{where}: combination must be one of {COMBINATIONS}")
        for rid, spec in ov.items():
            if rid == "combination":
                continue
            if rid not in (a.id, b.id) or not isinstance(spec, dict):
                raise FactPolicyError(f"{where}: unknown reader {rid!r} (have {a.id}, {b.id})")
            r: dict[str, Any] = {}
            if "band" in spec:
                r["band"] = list(_band(spec["band"], where))
            if "mode" in spec:
                if spec["mode"] not in MODES:
                    raise FactPolicyError(f"{where}: mode must be one of {MODES}")
                r["mode"] = spec["mode"]
            readers[rid] = r
        overrides[str(key)] = FactOverride(readers=readers, combination=c)
    return FactPolicy(readers=(a, b), combination=comb, overrides=overrides, source=source, on_split=on_split)


def default_policy() -> FactPolicy:
    """The pre-registered defaults (research/findings/dual_facts_prereg.md)."""
    return FactPolicy(readers=(ReaderSpec("qwen", "facts", "Qwen", "Qwen2.5-7B", "three_way"),
                               ReaderSpec("kev", "facts_kev", "Kev", "Kev-4B", "band", 0.3, 0.7)),
                      combination="agree", source="default")


_MEMO: dict[str, tuple[float, FactPolicy]] = {}
_LOCK = threading.Lock()


def resolve_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def load_fact_policy(path: str | Path = DEFAULT_PATH) -> FactPolicy:
    """Read and validate (re-read when the file changes: the officer applies new defaults live)."""
    p = resolve_path(path)
    try:
        mtime = p.stat().st_mtime
    except OSError as e:
        raise FactPolicyError(f"fact policy {p} not readable: {e}") from e
    with _LOCK:
        hit = _MEMO.get(str(p))
        if hit and hit[0] == mtime:
            return hit[1]
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise FactPolicyError(f"fact policy {p} is not valid YAML: {e}") from e
    pol = parse_fact_policy(raw, source=str(p))
    with _LOCK:
        _MEMO[str(p)] = (mtime, pol)
    return pol


HEADER = """# Fact policy: how the two AI readers' answers become ja / nein / unklar (src/callguard/fact_policy.py).
# Part of the fact bundle: changing it needs four-eyes approval (demo tab «Fakten»; versions in config/policy_versions/).
# Defaults pre-registered in research/findings/dual_facts_prereg.md: Qwen three-way, Kev band [0.3, 0.7], Einigkeit.
#   readers      A (primary, with evidence) and B; mode three_way (ja if p(ja) >= 0.5, nein if p(nein) >= 0.5,
#                else unklar) or band [lo, hi] on p(ja) (ja if >= hi, nein if <= lo, else unklar)
#   combination  only_a (Nur Qwen) | only_b (Nur Kev) | agree (Einigkeit) | a_checked (Qwen, Kev als Kontrolle)
#   overrides    "<family>.<fact>": {<reader id>: {band: [lo, hi], mode: ...}, combination: ...}
#   on_split     rules | review | alarm: a family the two readers alone would decide differently becomes at
#                least Prüfen / Alarm ("rules", the default: the combined facts decide)
"""


def dump_fact_policy(pol: FactPolicy | dict[str, Any]) -> str:
    d = pol.as_dict() if isinstance(pol, FactPolicy) else pol
    return HEADER + yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=110)


# --------------------------------------------------------------------------------------------
# one fact
# --------------------------------------------------------------------------------------------


def combine_values(mode: str, va: str, vb: str) -> str:
    """The truth table of the four combination modes (va = reader A's value, vb = reader B's)."""
    if mode == "only_a":
        return va
    if mode == "only_b":
        return vb
    if mode == "agree":
        return va if va == vb and va in ("yes", "no") else "unclear"
    if mode == "a_checked":
        return "unclear" if {va, vb} == {"yes", "no"} else va
    raise FactPolicyError(f"combination must be one of {COMBINATIONS}, got {mode!r}")


@dataclass
class ResolvedFact:
    fact: str
    value: str  # the combined value the rules see
    p: dict[str, float]  # distribution for the soft score (the deciding reader's, or the mean)
    pa: dict[str, float] | None  # reader A's stored answer (None: missing)
    pb: dict[str, float] | None
    va: str  # reader A's value under its band / three-way
    vb: str
    combination: str
    agree: bool  # both readers resolve to the same value

    def badge(self) -> str:
        if self.agree:
            return "einig"
        return "uneinig → unklar" if self.value == "unclear" else "uneinig"


def _clean_p(p: Any) -> dict[str, float] | None:
    if not isinstance(p, Mapping) or not p:
        return None
    return {k: float(v) for k, v in p.items() if isinstance(v, (int, float))}


def resolve_fact(policy: FactPolicy, family: str, fact: str, pa: Mapping[str, float] | None,
                 pb: Mapping[str, float] | None) -> ResolvedFact:
    pa_, pb_ = _clean_p(pa), _clean_p(pb)
    va = policy.reader(0, family, fact).resolve(pa_)
    vb = policy.reader(1, family, fact).resolve(pb_)
    mode = policy.combination_for(family, fact)
    value = combine_values(mode, va, vb)
    if mode == "only_a" or pb_ is None:
        p = pa_ or pb_ or {"unclear": 1.0}
    elif mode == "only_b" or pa_ is None:
        p = pb_ or pa_ or {"unclear": 1.0}
    else:
        p = average_probs([pa_, pb_])
    return ResolvedFact(fact, value, dict(p), pa_, pb_, va, vb, mode, va == vb)


# --------------------------------------------------------------------------------------------
# one call
# --------------------------------------------------------------------------------------------


def _facts_of(fs: FamilyScore | None) -> dict[str, dict[str, Any]]:
    return dict(((fs.detail or {}).get("facts") or {})) if fs is not None else {}


def usable(r: CheckResult | None) -> CheckResult | None:
    return None if r is None or (r.meta or {}).get("error") else r


def readers_of(result: CallResult | Mapping[str, CheckResult], policy: FactPolicy
               ) -> tuple[CheckResult | None, CheckResult | None]:
    checks = result.checks if isinstance(result, CallResult) else result
    return usable(checks.get(policy.a.check)), usable(checks.get(policy.b.check))


def has_both(result: CallResult, policy: FactPolicy) -> bool:
    a, b = readers_of(result, policy)
    return a is not None and b is not None


def combine_family(ft: FamilyTable, fs_a: FamilyScore | None, fs_b: FamilyScore | None, policy: FactPolicy, *,
                   alarm_base: float = 0.6, review_score: float = 0.5, review_confidence: float = 0.3,
                   no_alert_scale: float = 0.4) -> FamilyScore:
    """One family: resolve every fact of the table from both readers, then the rules (first match decides).
    Shaped like the facts check's FamilyScore; the detail carries both readers per fact."""
    fa, fb = _facts_of(fs_a), _facts_of(fs_b)
    fam = ft.family
    values: dict[str, str] = {}
    probs: dict[str, dict[str, float]] = {}
    facts: dict[str, dict[str, Any]] = {}
    split: list[str] = []
    values_a: dict[str, str] = {}
    values_b: dict[str, str] = {}
    for fact in ft.facts:
        da, db = fa.get(fact.id) or {}, fb.get(fact.id) or {}
        rf = resolve_fact(policy, fam, fact.id, da.get("p"), db.get("p"))
        values[fact.id], probs[fact.id] = rf.value, rf.p
        values_a[fact.id], values_b[fact.id] = rf.va, rf.vb
        ra, rb_ = policy.reader(0, fam, fact.id), policy.reader(1, fam, fact.id)
        entry: dict[str, Any] = {
            "label": fact.label, "role": fact.role, "question": da.get("question") or db.get("question") or "",
            "p": rf.p, "value": rf.value, "agree": rf.agree, "combination": rf.combination,
            "readers": {policy.a.id: {"label": ra.label, "p": rf.pa, "value": rf.va, "rule": ra.describe(),
                                      **({"band": [ra.lo, ra.hi]} if ra.mode == "band" else {})},
                        policy.b.id: {"label": rb_.label, "p": rf.pb, "value": rf.vb, "rule": rb_.describe(),
                                      **({"band": [rb_.lo, rb_.hi]} if rb_.mode == "band" else {})}}}
        for k in ("evidence", "reason"):  # only reader A asks for evidence
            if da.get(k):
                entry[k] = da[k]
        facts[fact.id] = entry
        if not rf.agree:
            split.append(f"{fact.label} ({ra.label} {VALUE_DE[rf.va]}, {rb_.label} {VALUE_DE[rf.vb]}"
                         f" → {VALUE_DE[rf.value]})")
    fd = decide_family(ft, values, probs, alarm_base=alarm_base, review_score=review_score,
                       review_confidence=review_confidence, no_alert_scale=no_alert_scale)
    reason = fd.summary
    if split:
        reason += f". Leser uneinig: {'; '.join(split)}"
    verdict_split = None
    if policy.on_split != "rules" and fs_a is not None and fs_b is not None:
        la, lb = ((r.label if r else "no_alert") for r in (ft.decide(values_a), ft.decide(values_b)))
        if la != lb and SEVERITY[fd.label] < SEVERITY[policy.on_split]:
            if policy.on_split == "alarm":
                fd = replace(fd, label="alarm", score=alarm_base + (1.0 - alarm_base) * fd.p_alarm,
                             confidence=max(0.7, fd.p_alarm), verdict="present")
            else:
                fd = replace(fd, label="review", score=review_score, confidence=review_confidence,
                             verdict="undetermined")
            verdict_split = {"a": la, "b": lb, "on_split": policy.on_split}
            reason = (f"{_LABEL_DE[fd.label]}: {policy.a.label} allein {_LABEL_DE[la]}, {policy.b.label} allein "
                      f"{_LABEL_DE[lb]} (Einstellung bei Uneinigkeit). {reason}")
    rule = fd.rule
    detail: dict[str, Any] = {
        "decision": fd.label, "facts": facts, "summary": reason,
        "rule": ({"id": rule.id, "label": rule.label, "when": rule.when, "text": rule.text} if rule
                 else {"id": None, "label": "no_alert", "when": None, "text": "keine Regel trifft zu"}),
        "rule_probs": fd.soft, "p_alarm": round(fd.p_alarm, 4), "p_review": round(fd.p_review, 4),
        "fact_policy": {"combination": policy.combination, "readers": [policy.a.id, policy.b.id],
                        "disagree": [f for f, e in facts.items() if not e["agree"]],
                        "missing": [r.label for r, fs in zip(policy.readers, (fs_a, fs_b)) if fs is None]},
    }
    if verdict_split:
        detail["verdict_split"] = verdict_split
    return FamilyScore(score=round(min(1.0, max(0.0, fd.score)), 4), confidence=round(min(1.0, fd.confidence), 4),
                       verdict=fd.verdict, reason=reason,  # type: ignore[arg-type]
                       segment_ids=list(fs_a.segment_ids) if fs_a is not None else [], detail=detail)


def split_tables(tables: Any) -> tuple[Mapping[str, FamilyTable], FamilyTable | None]:
    """(families, cross rules) of a PolicyTable, or (the mapping, None) for a plain ``families`` mapping."""
    if isinstance(tables, PolicyTable):
        return tables.families, tables.cross
    return tables, None


def cross_family(cross: FamilyTable | None, fam_scores: Mapping[str, FamilyScore], findings: list[Any],
                 family_names: Mapping[str, str] | None = None, **scoring: float
                 ) -> tuple[FamilyScore, list[Any]] | None:
    """The cross rules (section ``cross_rules``) over the union of every family's RESOLVED facts: the first
    matching rule decides the virtual family :data:`CROSS_FAMILY`. None when no cross rule matches (the call
    is then decided exactly as without cross rules). Pure: the same function serves the live fusion and the
    instant re-decision. Returns the FamilyScore and the evidence findings of the decisive facts."""
    if cross is None or not cross.rules:
        return None
    names = family_names or {}
    values: dict[str, str] = {}
    probs: dict[str, dict[str, float]] = {}
    facts: dict[str, dict[str, Any]] = {}
    for f in cross.facts:
        fam, fid = f.id.split(".", 1)
        fs = fam_scores.get(fam)
        e = ((fs.detail or {}).get("facts") or {}).get(fid) if fs is not None else None
        label = f"{names.get(fam, fam)}: {f.label}"
        if e:
            values[f.id], probs[f.id] = str(e.get("value") or "unclear"), dict(e.get("p") or {"unclear": 1.0})
            facts[f.id] = {**e, "label": label, "family": fam}
        else:
            values[f.id], probs[f.id] = "unclear", {"unclear": 1.0}
            facts[f.id] = {"label": label, "family": fam, "role": f.role, "value": "unclear", "p": {"unclear": 1.0}}
    rule = cross.decide(values)
    if rule is None:
        return None
    ft = FamilyTable(family=CROSS_FAMILY, facts=[f.__class__(**{**f.__dict__, "label": facts[f.id]["label"]})
                                                 for f in cross.facts], rules=cross.rules)
    fd = decide_family(ft, values, probs, **scoring)
    decisive = rule_facts(rule.node)
    segs: list[str] = []
    for q in decisive:
        segs += [s for s in facts[q].get("evidence") or [] if s not in segs]
    keep = {(q.split(".", 1)[0], q.split(".", 1)[1]) for q in decisive}
    ev = [f.model_copy(update={"family": CROSS_FAMILY}) for f in findings
          if (f.family, str((f.detail or {}).get("fact") or "")) in keep]
    title = rule.title or rule.text or rule.id
    detail: dict[str, Any] = {
        "decision": fd.label, "facts": {q: facts[q] for q in [*decisive, *[x for x in facts if x not in decisive]]},
        "summary": fd.summary, "cross": True, "report_as": rule.report_as,
        "rule": {"id": rule.id, "label": rule.label, "when": rule.when, "text": rule.text, "title": rule.title,
                 "report_as": rule.report_as},
        "rule_probs": fd.soft, "p_alarm": round(fd.p_alarm, 4), "p_review": round(fd.p_review, 4)}
    reason = f"{title.rstrip('.')}. Regel: {rule.id} (übergreifend)."
    return FamilyScore(score=round(min(1.0, max(0.0, fd.score)), 4), confidence=round(min(1.0, fd.confidence), 4),
                       verdict=fd.verdict, reason=reason, segment_ids=segs, detail=detail), ev  # type: ignore[arg-type]


def cross_family_label(detail: Mapping[str, Any], family_names: Mapping[str, str] | None = None) -> str:
    rep_ = str(detail.get("report_as") or "")
    return f"{CROSS_LABEL} · {(family_names or {}).get(rep_, rep_)}" if rep_ else CROSS_LABEL


def combined_result(tables: Any, a: CheckResult | None, b: CheckResult | None,
                    policy: FactPolicy, *, name: str = "facts", family_names: Mapping[str, str] | None = None,
                    **scoring: float) -> CheckResult:
    """One call's combined facts result: every family either reader scored (and the table has), plus the virtual
    family of the cross rules when one matches (``tables`` a PolicyTable with a ``cross_rules`` section).
    Findings (audio evidence) are both readers': A's pointed segments and, when reader B finds passages itself
    (``kev_facts`` with ``evidence: true``), B's; the fusion merges overlapping ones into one passage."""
    tables, cross = split_tables(tables)
    a, b = usable(a), usable(b)
    fams = [f for f in tables if (a and f in a.family_scores) or (b and f in b.family_scores)]
    out = {f: combine_family(tables[f], a.family_scores.get(f) if a else None, b.family_scores.get(f) if b else None,
                             policy, **scoring) for f in fams}
    disagree = {f: fs.detail["fact_policy"]["disagree"] for f, fs in out.items() if fs.detail["fact_policy"]["disagree"]}
    meta: dict[str, Any] = {"fact_policy": {"key": policy.key(), "combination": policy.combination,
                                            "readers": [policy.a.label, policy.b.label], "disagree": disagree,
                                            "missing": [r.label for r, x in zip(policy.readers, (a, b))
                                                        if x is None or x.meta.get("errors")]},
                            "models": sorted({str(r.meta["model"]) for r in (a, b) if r is not None and r.meta.get("model")})}
    if a is not None and a.meta.get("model"):
        meta["model"] = a.meta["model"]
    src = a or b
    fam_ok = set(fams)
    findings = [f for r in (a, b) if r is not None for f in r.findings if f.family in fam_ok]
    xr = cross_family(cross, out, findings, family_names, **scoring)
    if xr is not None:
        out[CROSS_FAMILY], ev = xr
        findings = [*findings, *ev]
        meta["cross_rule"] = xr[0].detail["rule"]["id"]
    return CheckResult(check=name, type="facts", family_scores=out, findings=findings, meta=meta,
                       view=src.view if src else None)


def combined_checks(result: CallResult | Mapping[str, CheckResult], tables: Any,
                    policy: FactPolicy, *, family_names: Mapping[str, str] | None = None,
                    **scoring: float) -> dict[str, CheckResult]:
    """The call's checks as the fusion sees them under ``policy``: both readers replaced by one combined
    facts result under reader A's name (so A's weight applies); every other check unchanged."""
    checks = result.checks if isinstance(result, CallResult) else result
    a, b = policy.a.check, policy.b.check
    rest = {k: v for k, v in checks.items() if k not in (a, b)}
    if checks.get(a) is None and checks.get(b) is None:
        return rest
    return {**rest, a: combined_result(tables, checks.get(a), checks.get(b), policy, name=a,
                                       family_names=family_names, **scoring)}


# --------------------------------------------------------------------------------------------
# all calls (what-if): stored answers + policy + rules -> labels, instantly
# --------------------------------------------------------------------------------------------


@dataclass
class FamilyVerdict:
    label: str
    rule: str | None
    facts: dict[str, ResolvedFact]


@dataclass
class CallOutcome:
    call_id: str
    label: str  # the call label (fusion: threshold, review band, light checks)
    score: float
    families: dict[str, FamilyVerdict]  # per family: the rules' verdict + resolved facts
    reasons: list[str] = field(default_factory=list)

    @property
    def rule_label(self) -> str:
        """The rules' own verdict for the call: the most severe family verdict."""
        return max((v.label for v in self.families.values()), key=SEVERITY.get, default="no_alert")


def family_verdicts(combined: CheckResult, policy: FactPolicy) -> dict[str, FamilyVerdict]:
    out: dict[str, FamilyVerdict] = {}
    for fam, fs in combined.family_scores.items():
        d = fs.detail or {}
        facts = {}
        for fid, e in (d.get("facts") or {}).items():
            ra, rb_ = (e.get("readers") or {}).get(policy.a.id) or {}, (e.get("readers") or {}).get(policy.b.id) or {}
            facts[fid] = ResolvedFact(fid, e["value"], e["p"], ra.get("p"), rb_.get("p"), ra.get("value", "unclear"),
                                      rb_.get("value", "unclear"), e.get("combination", policy.combination),
                                      bool(e.get("agree")))
        out[fam] = FamilyVerdict(str(d.get("decision") or "no_alert"), (d.get("rule") or {}).get("id"), facts)
    return out


Decide = Callable[[CallResult, dict[str, CheckResult]], Any]  # (call, checks) -> Decision


def redecide_one(result: CallResult, tables: Any, policy: FactPolicy, decide: Decide,
                 family_names: Mapping[str, str] | None = None, **scoring: float) -> CallOutcome:
    checks = combined_checks(result, tables, policy, family_names=family_names, **scoring)
    d = decide(result, checks)
    comb = checks.get(policy.a.check)
    fams = family_verdicts(comb, policy) if comb is not None and comb.meta.get("fact_policy") else {}
    return CallOutcome(result.call_id, d.label, float(d.score), fams, list(d.reasons))


def redecide(results: Mapping[str, CallResult], tables: Any, policy: FactPolicy,
             decide: Decide, family_names: Mapping[str, str] | None = None, **scoring: float) -> dict[str, CallOutcome]:
    """Every stored call re-decided under ``policy`` + ``tables`` (no LLM; a PolicyTable also applies its cross
    rules). ``decide(call, checks)`` is the fusion; the fusion's ``decide_checks`` adds the cross rules' virtual
    family (:func:`with_cross_family`)."""
    return {cid: redecide_one(r, tables, policy, decide, family_names, **scoring) for cid, r in results.items()}


def with_cross_family(families: list[Any], checks: Mapping[str, CheckResult],
                      family_names: Mapping[str, str] | None = None) -> list[Any]:
    """``families`` plus the virtual family of the cross rules when a combined facts result carries it (the
    fusion only scores families it is given)."""
    from callguard.types import Family

    for cr in checks.values():
        fs = cr.family_scores.get(CROSS_FAMILY)
        if fs is not None and not any(f.id == CROSS_FAMILY for f in families):
            return [*families, Family(id=CROSS_FAMILY, label=cross_family_label(fs.detail or {}, family_names),
                                      can_alarm=True)]
    return families


def effect(before: Mapping[str, CallOutcome | str], after: Mapping[str, CallOutcome | str]) -> dict[str, Any]:
    """Which calls change label, and the net change per label."""
    def lab(x: CallOutcome | str) -> str:
        return x if isinstance(x, str) else x.label

    changed = [(cid, lab(before[cid]), lab(a)) for cid, a in after.items() if cid in before and lab(before[cid]) != lab(a)]
    net = {k: 0 for k in SEVERITY}
    for _, b, a in changed:
        net[b] -= 1
        net[a] += 1
    return {"n": len(after), "changed": changed, "net": net}


def effect_line(eff: Mapping[str, Any]) -> str:
    """«ändert 4 von 60 Anrufen: +3 Prüfen, −1 Alarm» (or «ändert keinen der 60 Anrufe»)."""
    n, ch = eff["n"], eff["changed"]
    if not ch:
        return f"ändert keinen der {n} Anrufe"
    parts = [f"{'+' if v > 0 else '−'}{abs(v)} {LABEL_DE[k]}" for k, v in
             sorted(eff["net"].items(), key=lambda kv: -SEVERITY[kv[0]]) if v]
    return f"ändert {len(ch)} von {n} Anrufen" + (f": {', '.join(parts)}" if parts else " (Verschiebungen gleichen sich aus)")


# --------------------------------------------------------------------------------------------
# per fact across calls (the «Fakten» tab: strips, disagreements)
# --------------------------------------------------------------------------------------------


@dataclass
class FactAnswer:
    call_id: str
    pa: dict[str, float] | None
    pb: dict[str, float] | None

    @property
    def ya(self) -> float | None:
        return None if self.pa is None else float(self.pa.get("yes", 0.0))

    @property
    def yb(self) -> float | None:
        return None if self.pb is None else float(self.pb.get("yes", 0.0))


def fact_answers(results: Mapping[str, CallResult], policy: FactPolicy) -> dict[tuple[str, str], list[FactAnswer]]:
    """(family, fact) -> both readers' stored answers per call (calls where at least one reader answered)."""
    out: dict[tuple[str, str], list[FactAnswer]] = {}
    for cid, r in sorted(results.items()):
        a, b = readers_of(r, policy)
        fams = set(a.family_scores if a else {}) | set(b.family_scores if b else {})
        for fam in sorted(fams):
            fa = _facts_of(a.family_scores.get(fam) if a else None)
            fb = _facts_of(b.family_scores.get(fam) if b else None)
            for fid in dict.fromkeys([*fa, *fb]):
                out.setdefault((fam, fid), []).append(
                    FactAnswer(cid, _clean_p((fa.get(fid) or {}).get("p")), _clean_p((fb.get(fid) or {}).get("p"))))
    return out


def disagreements(answers: Iterable[FactAnswer], policy: FactPolicy, family: str, fact: str) -> list[ResolvedFact]:
    """Calls where the two readers resolve this fact differently (under the policy's bands), in call order;
    ``ResolvedFact.fact`` is the call id here."""
    out = []
    for a in answers:
        rf = resolve_fact(policy, family, fact, a.pa, a.pb)
        if not rf.agree and a.pa is not None and a.pb is not None:
            rf.fact = a.call_id
            out.append(rf)
    return out


def value_counts(answers: Iterable[FactAnswer], policy: FactPolicy, family: str, fact: str) -> dict[str, dict[str, int]]:
    """Per reader and combined: how many calls resolve to ja / nein / unklar."""
    out = {k: {v: 0 for v in VALUES} for k in ("a", "b", "combined")}
    for a in answers:
        rf = resolve_fact(policy, family, fact, a.pa, a.pb)
        out["a"][rf.va] += 1
        out["b"][rf.vb] += 1
        out["combined"][rf.value] += 1
    return out


# --------------------------------------------------------------------------------------------
# governance helpers: what is a fact change, what is a rule change
# --------------------------------------------------------------------------------------------


def facts_part(doc: Mapping[str, Any]) -> dict[str, Any]:
    """The facts of a policy table document (per family: facts + whether the family exists); rules excluded."""
    return {fid: copy.deepcopy((fam or {}).get("facts") or []) for fid, fam in ((doc or {}).get("families") or {}).items()}


CROSS_KEY = "__cross__"  # rules_part: the section ``cross_rules`` (rules over several Prüfarten)


def rules_part(doc: Mapping[str, Any]) -> dict[str, Any]:
    """Per family its rules, plus :data:`CROSS_KEY` -> the cross rules (both are RULES: instant, with undo)."""
    out = {fid: copy.deepcopy((fam or {}).get("rules") or []) for fid, fam in ((doc or {}).get("families") or {}).items()}
    out[CROSS_KEY] = copy.deepcopy(list((doc or {}).get("cross_rules") or []))
    return out


def with_rules(doc: Mapping[str, Any], rules: Mapping[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """``doc`` with the rules of ``rules`` (per family present in both, and the cross rules); facts kept."""
    out = copy.deepcopy(dict(doc))
    for fid, fam in (out.get("families") or {}).items():
        if fid in rules:
            fam["rules"] = copy.deepcopy(list(rules[fid]))
    if CROSS_KEY in rules:
        if rules[CROSS_KEY]:
            out["cross_rules"] = copy.deepcopy(list(rules[CROSS_KEY]))
        else:
            out.pop("cross_rules", None)
    return out


def only_rules_changed(old: Mapping[str, Any], new: Mapping[str, Any]) -> bool:
    """True if ``new`` differs from ``old`` in rules only (family rules and cross rules; facts, families and every
    other key equal)."""
    if facts_part(old) != facts_part(new):
        return False
    strip = lambda d: {fid: {k: v for k, v in (fam or {}).items() if k != "rules"}  # noqa: E731
                       for fid, fam in ((d or {}).get("families") or {}).items()}
    top = lambda d: {k: v for k, v in (d or {}).items() if k not in ("families", "cross_rules")}  # noqa: E731
    return strip(old) == strip(new) and top(old) == top(new)


def validate_policy_dict(raw: Any) -> FactPolicy:
    try:
        return parse_fact_policy(raw)
    except FactPolicyError as e:
        raise PolicyTableError(str(e)) from None
