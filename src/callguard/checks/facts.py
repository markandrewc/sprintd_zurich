"""Fact sheet + policy table check (v2_plan A1, sharpened by research ideas N6, N7, N8).

Instead of one "is this misconduct?" judgement per family, the LLM answers a few atomic yes / no /
unknown FACT questions per family (``config/policy_table.yaml``: "was a complete code said?", "is the
value expired?", ...), each in its own prompt over the whole transcript. The answer is one token, so
the next-token log-probabilities give p(yes), p(no), p(unclear) per fact from a single forward pass
(sampling fallback for servers without logprobs). An officer-editable decision table then maps the
fact values to alarm / review / no_alert with the first matching rule, e.g.::

    alarm   if spoken = yes and current = yes and expired_or_sample != yes
    review  if spoken = yes and current = unclear and expired_or_sample != yes

Why: it separates "did the act happen" from "is the context incriminating", which is exactly what the
Stufe2 twins differ in; "unclear" facts become review (the case's "undetermined"); and every decision
names the facts and the rule that produced it ("Fakt: Code ausgesprochen = ja (0.92); Regel:
access.alarm_1"), which is the traceability the jury scores.

Scores for the fusion: alarm -> ``alarm_base + (1 - alarm_base) * P(rule)``, review -> ``review_score``
with low confidence and verdict "undetermined" (the weighted fusion escalates that to review),
no_alert -> ``no_alert_scale * max P(alarm rule)``. P(rule) is the rule evaluated on the fact
probabilities (and = product, or = noisy-or, != x = 1 - p(x)): a soft score that moves the threshold
slider smoothly although the rule itself is discrete.

Optional: ``evidence: true`` asks once per fact with p(yes) > ``evidence_min`` for segment ids and a
German reason (findings -> audio passages); ``prefix_max: true`` (N8) also asks the act facts on
growing prefixes of the call and keeps the highest p(yes), so a later refusal cannot talk the model
out of an act that already happened (context and exculpatory facts always read the whole call).

Fact probes are cached per prompt (namespace ``fact_probe``), so editing a rule or one question
reruns only the cheap rule evaluation or that one question.

Robustness (research R6): ``paraphrase_tables: [path, ...]`` asks every fact that also exists (same
family + fact id) in one of these tables once per wording and averages p(yes), p(no), p(unclear) over
the wordings before the fact is discretized; the main table's rules decide, the per-wording
probabilities are kept in the detail (``facts.<id>.wordings``). ``unclear_band: [lo, hi]`` decides a
fact from p(yes) alone (yes if p(yes) >= hi, no if p(yes) < lo, else unclear), so a rule that tests
``= unclear`` no longer depends on how the remaining mass splits between the "no" and "unknown" tokens.
Both default to off, and then neither the behaviour nor the cache key changes.
"""

from __future__ import annotations

import logging
import math
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, Field

from callguard.cache import stable_hash
from callguard.checks import fact_prompts as fp
from callguard.checks import prompts
from callguard.checks.llm_judge import LLMCheck
from callguard.config import ROOT
from callguard.plugins import LLM
from callguard.types import CheckResult, Family, FamilyScore, Finding, Label, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.facts")

PROBE_NAMESPACE = "fact_probe"
FACT_ROLES = ("act", "context", "exculpatory", "authorization")
RULE_LABELS: tuple[Label, ...] = ("alarm", "review", "no_alert")
DEFAULT_TABLE = "config/policy_table.yaml"
_LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}


class PolicyTableError(ValueError):
    pass


# --------------------------------------------------------------------------------------------
# Rule language: a tiny, safe parser (no eval)
#
#   expr   := and_e ('or' and_e)*
#   and_e  := not_e ('and' not_e)*
#   not_e  := 'not' not_e | atom
#   atom   := '(' expr ')' | 'true' | FACT ('=' | '==' | '!=') VALUE | FACT ['not'] 'in' '[' VALUE {',' VALUE} ']'
#   VALUE  := yes | no | unclear   (aliases: ja, nein, unklar, unknown)
# --------------------------------------------------------------------------------------------

_VALUE_ALIASES = {"yes": "yes", "ja": "yes", "no": "no", "nein": "no", "unclear": "unclear",
                  "unklar": "unclear", "unknown": "unclear"}
_TOKEN = re.compile(r"\s*(?:(!=|==|=|\(|\)|\[|\]|,)|([A-Za-z_][A-Za-z0-9_]*))")
_KEYWORDS = {"and", "or", "not", "in", "true"}

# AST nodes are tuples: ("true",) | ("cmp", fact, frozenset(values)) | ("not", node)
#                       | ("and", node, ...) | ("or", node, ...)
Node = tuple


def tokenize(text: str) -> list[str]:
    out, pos, text = [], 0, str(text)
    while pos < len(text):
        if text[pos:].strip() == "":
            break
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise PolicyTableError(f"cannot read rule {text!r} at position {pos}: {text[pos:pos + 15]!r}")
        out.append(m.group(1) or m.group(2))
        pos = m.end()
    return out


class _Parser:
    def __init__(self, text: str, facts: set[str] | None):
        self.text, self.facts = text, facts
        self.toks = tokenize(text)
        self.i = 0

    def error(self, msg: str) -> PolicyTableError:
        return PolicyTableError(f"rule {self.text!r}: {msg}")

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, expected: str | None = None) -> str:
        tok = self.peek()
        if tok is None:
            raise self.error(f"unexpected end{f', expected {expected!r}' if expected else ''}")
        if expected is not None and tok.lower() != expected:
            raise self.error(f"expected {expected!r}, got {tok!r}")
        self.i += 1
        return tok

    def parse(self) -> Node:
        if not self.toks:
            raise self.error("empty condition (use `true` for a default rule)")
        node = self.expr()
        if self.peek() is not None:
            raise self.error(f"unexpected {self.peek()!r}")
        return node

    def expr(self) -> Node:
        parts = [self.and_e()]
        while (self.peek() or "").lower() == "or":
            self.take()
            parts.append(self.and_e())
        return parts[0] if len(parts) == 1 else ("or", *parts)

    def and_e(self) -> Node:
        parts = [self.not_e()]
        while (self.peek() or "").lower() == "and":
            self.take()
            parts.append(self.not_e())
        return parts[0] if len(parts) == 1 else ("and", *parts)

    def not_e(self) -> Node:
        if (self.peek() or "").lower() == "not":
            self.take()
            return ("not", self.not_e())
        return self.atom()

    def value(self) -> str:
        tok = self.take()
        v = _VALUE_ALIASES.get(tok.lower())
        if v is None:
            raise self.error(f"{tok!r} is not a fact value (yes / no / unclear)")
        return v

    def atom(self) -> Node:
        tok = self.take()
        low = tok.lower()
        if tok == "(":
            node = self.expr()
            self.take(")")
            return node
        if low == "true":
            return ("true",)
        if low in _KEYWORDS or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", tok):
            raise self.error(f"expected a fact name, got {tok!r}")
        if self.facts is not None and tok not in self.facts:
            raise self.error(f"unknown fact {tok!r} (facts of this family: {sorted(self.facts)})")
        op = self.take()
        negate = False
        if op.lower() == "not":
            negate, op = True, self.take("in")
        if op in ("=", "=="):
            return ("cmp", tok, frozenset([self.value()]))
        if op == "!=":
            return ("not", ("cmp", tok, frozenset([self.value()])))
        if op.lower() == "in":
            self.take("[")
            vals = [self.value()]
            while self.peek() == ",":
                self.take()
                vals.append(self.value())
            self.take("]")
            node: Node = ("cmp", tok, frozenset(vals))
            return ("not", node) if negate else node
        raise self.error(f"expected =, != or in after {tok!r}, got {op!r}")


def parse_rule(text: str, facts: set[str] | None = None) -> Node:
    """Parse a rule condition. ``facts``: the known fact ids (None = accept any name)."""
    return _Parser(str(text), facts).parse()


def eval_hard(node: Node, values: dict[str, str]) -> bool:
    """Evaluate on discrete fact values (yes / no / unclear). A fact without a value is unclear."""
    kind = node[0]
    if kind == "true":
        return True
    if kind == "cmp":
        return values.get(node[1], "unclear") in node[2]
    if kind == "not":
        return not eval_hard(node[1], values)
    if kind == "and":
        return all(eval_hard(n, values) for n in node[1:])
    if kind == "or":
        return any(eval_hard(n, values) for n in node[1:])
    raise ValueError(f"bad rule node {node!r}")


def eval_soft(node: Node, probs: dict[str, dict[str, float]]) -> float:
    """Probability that the condition holds, treating facts as independent: and = product,
    or = noisy-or, not = complement. A fact without probabilities is fully unclear."""
    kind = node[0]
    if kind == "true":
        return 1.0
    if kind == "cmp":
        p = probs.get(node[1]) or {"unclear": 1.0}
        return min(1.0, max(0.0, sum(float(p.get(v, 0.0)) for v in node[2])))
    if kind == "not":
        return 1.0 - eval_soft(node[1], probs)
    if kind == "and":
        out = 1.0
        for n in node[1:]:
            out *= eval_soft(n, probs)
        return out
    if kind == "or":
        miss = 1.0
        for n in node[1:]:
            miss *= 1.0 - eval_soft(n, probs)
        return 1.0 - miss
    raise ValueError(f"bad rule node {node!r}")


def rule_facts(node: Node) -> list[str]:
    """Fact ids a condition mentions, in order of appearance."""
    if node[0] == "cmp":
        return [node[1]]
    out: list[str] = []
    for n in node[1:]:
        if isinstance(n, tuple):
            out += [f for f in rule_facts(n) if f not in out]
    return out


def average_probs(dists: list[dict[str, float]]) -> dict[str, float]:
    """Mean of several yes / no / unclear distributions (missing keys count as 0)."""
    keys = [k for k in ("yes", "no", "unclear") if any(k in d for d in dists)]
    keys += sorted({k for d in dists for k in d} - set(keys))
    return {k: round(sum(float(d.get(k, 0.0)) for d in dists) / len(dists), 4) for k in keys}


def discretize_band(p: dict[str, float], lo: float, hi: float) -> str:
    """From p(yes) alone: yes if p(yes) >= hi, no if p(yes) < lo, else unclear."""
    py = p.get("yes", 0.0)
    return "yes" if py >= hi else ("no" if py < lo else "unclear")


def discretize(p: dict[str, float], decide_at: float = 0.5) -> str:
    """yes if p(yes) >= decide_at, no if p(no) >= decide_at, else unclear."""
    if p.get("yes", 0.0) >= decide_at:
        return "yes"
    if p.get("no", 0.0) >= decide_at:
        return "no"
    return "unclear"


# --------------------------------------------------------------------------------------------
# Policy table
# --------------------------------------------------------------------------------------------


@dataclass
class Fact:
    id: str
    label: str
    role: str
    de: str
    en: str = ""

    def question(self, lang: str) -> str:
        return (self.en if lang == "en" and self.en else self.de).strip()


@dataclass
class Rule:
    id: str
    label: Label
    when: str
    text: str = ""
    node: Node = field(default=("true",), repr=False)


@dataclass
class FamilyTable:
    family: str
    facts: list[Fact]
    rules: list[Rule]
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    def fact(self, fid: str) -> Fact:
        return next(f for f in self.facts if f.id == fid)

    def decide(self, values: dict[str, str]) -> Rule | None:
        return next((r for r in self.rules if eval_hard(r.node, values)), None)


@dataclass
class PolicyTable:
    families: dict[str, FamilyTable]
    path: str = ""

    def key(self, family_ids: list[str]) -> str:
        """Hash of the parsed entries of these families (comment / formatting edits don't count)."""
        return stable_hash({fid: self.families[fid].raw for fid in sorted(family_ids) if fid in self.families})


def parse_policy_table(raw: Any, source: str = "policy table") -> PolicyTable:
    if not isinstance(raw, dict) or not isinstance(raw.get("families"), dict):
        raise PolicyTableError(f"{source}: expected a mapping with a `families:` block")
    out: dict[str, FamilyTable] = {}
    for fid, entry in raw["families"].items():
        where = f"{source}: family {fid}"
        if not isinstance(entry, dict):
            raise PolicyTableError(f"{where}: expected a mapping with facts and rules")
        bad = set(entry) - {"facts", "rules"}
        if bad:
            raise PolicyTableError(f"{where}: unknown keys {sorted(bad)}")
        facts: list[Fact] = []
        for i, f in enumerate(entry.get("facts") or []):
            if not isinstance(f, dict):
                raise PolicyTableError(f"{where}: fact #{i} is not a mapping")
            bad = set(f) - {"id", "label", "role", "de", "en"}
            if bad:
                raise PolicyTableError(f"{where}: fact #{i}: unknown keys {sorted(bad)}")
            fact_id = str(f.get("id") or "")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", fact_id) or fact_id.lower() in _KEYWORDS:
                raise PolicyTableError(f"{where}: fact #{i}: id {fact_id!r} must be a plain name")
            if any(x.id == fact_id for x in facts):
                raise PolicyTableError(f"{where}: duplicate fact id {fact_id!r}")
            role = str(f.get("role") or "")
            if role not in FACT_ROLES:
                raise PolicyTableError(f"{where}: fact {fact_id}: role {role!r} not in {FACT_ROLES}")
            if not str(f.get("de") or f.get("en") or "").strip():
                raise PolicyTableError(f"{where}: fact {fact_id}: needs a question (de and/or en)")
            facts.append(Fact(id=fact_id, label=str(f.get("label") or fact_id), role=role,
                              de=str(f.get("de") or f.get("en")), en=str(f.get("en") or "")))
        if not facts:
            raise PolicyTableError(f"{where}: no facts")
        ids = {f.id for f in facts}
        rules: list[Rule] = []
        for i, r in enumerate(entry.get("rules") or []):
            if not isinstance(r, dict):
                raise PolicyTableError(f"{where}: rule #{i} is not a mapping")
            bad = set(r) - {"id", "label", "when", "text"}
            if bad:
                raise PolicyTableError(f"{where}: rule #{i}: unknown keys {sorted(bad)}")
            rid = str(r.get("id") or f"{fid}.rule_{i + 1}")
            if any(x.id == rid for x in rules):
                raise PolicyTableError(f"{where}: duplicate rule id {rid!r}")
            label = str(r.get("label") or "")
            if label not in RULE_LABELS:
                raise PolicyTableError(f"{where}: rule {rid}: label {label!r} not in {RULE_LABELS}")
            when = r.get("when")
            when = "true" if when is True else str(when if when is not None else "")
            try:
                node = parse_rule(when, ids)
            except PolicyTableError as e:
                raise PolicyTableError(f"{where}: rule {rid}: {e}") from None
            rules.append(Rule(id=rid, label=label, when=when, text=str(r.get("text") or ""), node=node))  # type: ignore[arg-type]
        out[str(fid)] = FamilyTable(family=str(fid), facts=facts, rules=rules,
                                    raw={"facts": [f.__dict__ for f in facts],
                                         "rules": [{"id": r.id, "label": r.label, "when": r.when,
                                                    "text": r.text} for r in rules]})
    return PolicyTable(families=out, path=source)


_TABLE_MEMO: dict[str, tuple[float, PolicyTable]] = {}
_TABLE_LOCK = threading.Lock()


def load_policy_table(path: str | Path) -> PolicyTable:
    """Read and validate the table; re-read when the file changes (the officer may edit it live)."""
    p = Path(path)
    p = p if p.is_absolute() else ROOT / p
    try:
        mtime = p.stat().st_mtime
    except OSError as e:
        raise PolicyTableError(f"policy table {p} not readable: {e}") from e
    with _TABLE_LOCK:
        hit = _TABLE_MEMO.get(str(p))
        if hit and hit[0] == mtime:
            return hit[1]
    try:
        raw = yaml.safe_load(p.read_text())
    except yaml.YAMLError as e:
        raise PolicyTableError(f"policy table {p} is not valid YAML: {e}") from e
    table = parse_policy_table(raw, source=str(p))
    with _TABLE_LOCK:
        _TABLE_MEMO[str(p)] = (mtime, table)
    return table


# --------------------------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------------------------


class FactProbe(BaseModel):
    """One fact question answered once: the answer distribution and how it was obtained."""

    p: dict[str, float]
    method: str
    info: dict[str, Any] = Field(default_factory=dict)


def _fmt_fact(label: str, value: str, p: dict[str, float]) -> str:
    if value == "unclear":
        return f"{label} = unklar (ja {p.get('yes', 0):.2f}, nein {p.get('no', 0):.2f})"
    return f"{label} = {fp.VALUE_DE[value]} ({p.get(value, 0):.2f})"


def prefix_cuts(n_segments: int, cuts: int) -> list[int]:
    """Prefix lengths (segment counts) at k/(cuts+1) of the call, k = 1..cuts, without the full call."""
    out = sorted({max(1, math.ceil(n_segments * k / (cuts + 1))) for k in range(1, cuts + 1)})
    return [m for m in out if m < n_segments]


class FactSheetCheck(LLMCheck):
    plugin_kind = "check"
    plugin_type = "facts"

    _SPEED_ONLY_PARAMS = ("parallel",)

    def __init__(self, ctx: "Context", *, llm: str = "default", policy_table: str = DEFAULT_TABLE,
                 question_lang: str = "en", roles: bool = True, decide_at: float = 0.5,
                 evidence: bool = True, evidence_min: float = 0.5, prefix_max: bool = False,
                 prefix_cuts: int = 3, prefix_roles: list[str] | None = None,
                 prefix_families: list[str] | None = None, fallback_samples: int = 5,
                 alarm_base: float = 0.6, review_score: float = 0.5, review_confidence: float = 0.3,
                 no_alert_scale: float = 0.4, max_tokens: int = 300, reason_language: str = "de",
                 include_non_alarm: bool = False, max_transcript_chars: int = 24000, parallel: int = 1,
                 paraphrase_tables: list[str] | None = None, unclear_band: list[float] | None = None,
                 name: str | None = None, weight: float = 1.0, enabled: bool = True):
        if isinstance(paraphrase_tables, str):
            paraphrase_tables = [paraphrase_tables]
        band: tuple[float, float] | None = None
        if unclear_band is not None:
            try:
                lo, hi = (float(x) for x in unclear_band)
            except (TypeError, ValueError):
                raise ValueError(f"unclear_band must be [lo, hi], got {unclear_band!r}") from None
            if not 0.0 <= lo < hi <= 1.0:
                raise ValueError(f"unclear_band needs 0 <= lo < hi <= 1, got {unclear_band!r}")
            band = (lo, hi)
        # R6 params enter the cache params only when set: existing configs keep their cache keys
        extra: dict[str, Any] = {}
        if paraphrase_tables:
            extra["paraphrase_tables"] = [str(t) for t in paraphrase_tables]
        if band is not None:
            extra["unclear_band"] = list(band)
        if question_lang not in ("en", "de"):
            raise ValueError(f"question_lang must be en or de, got {question_lang!r}")
        if not 1 / 3 < float(decide_at) <= 1.0:
            raise ValueError(f"decide_at must be in (1/3, 1], got {decide_at}")
        if int(fallback_samples) < 1:
            raise ValueError(f"fallback_samples must be >= 1, got {fallback_samples}")
        if int(prefix_cuts) < 1:
            raise ValueError(f"prefix_cuts must be >= 1, got {prefix_cuts}")
        bad_roles = set(prefix_roles or []) - set(FACT_ROLES)
        if bad_roles:
            raise ValueError(f"prefix_roles {sorted(bad_roles)} not in {FACT_ROLES}")
        if not 0.0 <= float(alarm_base) <= 1.0 or not 0.0 <= float(no_alert_scale) <= 1.0:
            raise ValueError("alarm_base and no_alert_scale must be within 0..1")
        super().__init__(ctx, llm=llm, reason_language=reason_language, include_non_alarm=include_non_alarm,
                         max_transcript_chars=max_transcript_chars, parallel=parallel, name=name,
                         weight=weight, enabled=enabled, policy_table=policy_table,
                         question_lang=question_lang, roles=roles, decide_at=decide_at, evidence=evidence,
                         evidence_min=evidence_min, prefix_max=prefix_max, prefix_cuts=prefix_cuts,
                         prefix_roles=prefix_roles, prefix_families=prefix_families,
                         fallback_samples=fallback_samples, alarm_base=alarm_base,
                         review_score=review_score, review_confidence=review_confidence,
                         no_alert_scale=no_alert_scale, max_tokens=max_tokens, **extra)
        self.policy_table = str(policy_table)
        self.paraphrase_tables = tuple(str(t) for t in paraphrase_tables or ())
        self.unclear_band = band
        self.question_lang = question_lang
        self.roles = bool(roles)
        self.decide_at = float(decide_at)
        self.evidence = bool(evidence)
        self.evidence_min = float(evidence_min)
        self.prefix_max = bool(prefix_max)
        self.n_prefix_cuts = int(prefix_cuts)
        self.prefix_roles = tuple(prefix_roles or ("act",))
        self.prefix_families = set(prefix_families) if prefix_families is not None else None
        self.fallback_samples = int(fallback_samples)
        self.alarm_base = float(alarm_base)
        self.review_score = float(review_score)
        self.review_confidence = float(review_confidence)
        self.no_alert_scale = float(no_alert_scale)
        self.max_tokens = int(max_tokens)
        self.table()  # a broken table fails at startup, not on the first call
        main = self.table()
        for path in self.paraphrase_tables:
            para = load_policy_table(path)
            shared = [(fid, f.id) for fid, ft in main.families.items() if fid in para.families
                      for f in ft.facts if any(x.id == f.id for x in para.families[fid].facts)]
            if not shared:
                raise PolicyTableError(f"paraphrase table {path} shares no (family, fact id) with {self.policy_table}")

    def table(self) -> PolicyTable:
        return load_policy_table(self.policy_table)

    def wordings(self, family_id: str) -> dict[str, list[tuple[str, Fact]]]:
        """Per fact id of the main table: (source table, fact) for the main wording and every
        paraphrase table that has the same family + fact id (identical questions count once)."""
        ft = self.table().families[family_id]
        out = {f.id: [(self.policy_table, f)] for f in ft.facts}
        for path in self.paraphrase_tables:
            para = load_policy_table(path).families.get(family_id)
            if para is None:
                continue
            for pf in para.facts:
                ws = out.get(pf.id)
                if ws is not None and all(w.question(self.question_lang) != pf.question(self.question_lang)
                                          for _, w in ws):
                    ws.append((path, pf))
        return out

    def _decide(self, p: dict[str, float]) -> str:
        if self.unclear_band is not None:
            return discretize_band(p, *self.unclear_band)
        return discretize(p, self.decide_at)

    def select_families(self, families: list[Family]) -> list[Family]:
        table = self.table()
        return [f for f in super().select_families(families) if f.id in table.families]

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        fams = self.select_families(families)
        key = {
            "params": self.cache_params(),
            "llm": self.llm_identity,
            "families": [{"id": f.id, "label": f.label} for f in fams],
            "policy_table": self.table().key([f.id for f in fams]),
            "prompt_version": fp.PROMPT_VERSION,
        }
        if self.paraphrase_tables:  # only the extra wordings matter (the main table's rules decide)
            key["paraphrases"] = stable_hash({
                f.id: {fid: [w.question(self.question_lang) for _, w in ws[1:]]
                       for fid, ws in self.wordings(f.id).items()} for f in fams})
        return key

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        if not self.roles:  # N12 "neutral": speaker clusters stay, advisor/customer labels go
            transcript = transcript.model_copy(update={"segments": [
                s.model_copy(update={"role": "unknown"}) for s in transcript.segments]})
        result = super().run(transcript, families)
        meta = result.meta
        meta["prompt_version"] = fp.PROMPT_VERSION
        table = self.table()  # families without a fact sheet are in meta["skipped_families"] already
        meta["policy_table"] = {"path": self.policy_table,
                                "hash": table.key(list(result.family_scores))}
        if self.paraphrase_tables:
            meta["policy_table"]["paraphrase_tables"] = list(self.paraphrase_tables)
        details = [fs.detail for fs in result.family_scores.values()]
        meta["llm_calls"] = sum(int(d.get("llm_calls", 0)) for d in details)
        meta["cached_probes"] = sum(int(d.get("cached_probes", 0)) for d in details)
        ev_errors = {fid: fs.detail["evidence_errors"] for fid, fs in result.family_scores.items()
                     if fs.detail.get("evidence_errors")}
        if ev_errors:
            meta["evidence_errors"] = ev_errors
        return result

    # -- one fact ----------------------------------------------------------------------------------

    def probe(self, llm: LLM, messages: list[dict[str, str]], counts: dict[str, int],
              lock: threading.Lock) -> FactProbe:
        """p(yes / no / unclear) for one prompt: logprobs, else sampling; cached per prompt + model."""
        key = {"messages": stable_hash(messages), "llm": llm.cache_params(), "version": fp.PROMPT_VERSION,
               "fallback_samples": self.fallback_samples}
        hit = self.ctx.cache.get(PROBE_NAMESPACE, key, FactProbe)
        if hit is not None:
            with lock:
                counts["cached_probes"] += 1
            return hit
        info: dict[str, Any] = {}
        probs: dict[str, float] | None = None
        calls = 1
        try:
            raw = llm.choice_probs(messages, list(fp.ANSWERS))
            probs = fp.probs_from_choices(raw) if raw else None
            if raw and probs is None:
                info["logprobs_error"] = "no probability mass on yes/no/unknown"
        except Exception as e:
            log.warning("%s: choice_probs failed, falling back to sampling: %s", self.name, e)
            info["logprobs_error"] = f"{type(e).__name__}: {e}"
        if probs is not None:
            out = FactProbe(p={k: round(v, 4) for k, v in probs.items()}, method="logprobs", info=info)
        else:
            calls += 1
            outs = llm.chat(messages, temperature=1.0, max_tokens=4, n=self.fallback_samples) or []
            answers = [a for a in (fp.parse_answer(o) for o in outs) if a]
            if not answers:
                with lock:
                    counts["llm_calls"] += calls
                raise ValueError(f"no yes/no/unknown in {len(outs)} sampled answers, e.g. {outs[:1]!r}")
            info.update(samples=[str(o)[:20] for o in outs], valid=len(answers))
            out = FactProbe(p={v: round(answers.count(v) / len(answers), 4) for v in fp.VALUES},
                            method="sampling", info=info)
        with lock:
            counts["llm_calls"] += calls
        if "logprobs_error" not in info:  # a transient logprob failure must not stick in the cache
            self.ctx.cache.put(PROBE_NAMESPACE, key, out)
        return out

    def _messages(self, rendered: str, family: Family, fact: Fact, lang: str | None) -> list[dict[str, str]]:
        return fp.fact_messages(rendered, family.label, family.id, fact.question(self.question_lang),
                                transcript_lang=lang)

    def _uses_prefix(self, family: Family, fact: Fact) -> bool:
        return (self.prefix_max and fact.role in self.prefix_roles
                and (self.prefix_families is None or family.id in self.prefix_families))

    # -- one family --------------------------------------------------------------------------------

    def score_family(self, llm: LLM, transcript: Transcript, rendered: str,
                     family: Family) -> tuple[FamilyScore, list[Finding]]:
        ft = self.table().families[family.id]
        counts = {"llm_calls": 0, "cached_probes": 0}
        lock = threading.Lock()

        # (fact, wording index, wording, prefix length or None for the whole call); wording 0 = main table
        wordings = self.wordings(family.id)
        cuts = prefix_cuts(len(transcript.segments), self.n_prefix_cuts)
        tasks: list[tuple[Fact, int, Fact, int | None]] = [
            (f, w, wf, None) for f in ft.facts for w, (_, wf) in enumerate(wordings[f.id])]
        tasks += [(f, w, wf, m) for f in ft.facts if self._uses_prefix(family, f)
                  for w, (_, wf) in enumerate(wordings[f.id]) for m in cuts]
        renders = {None: rendered}
        for m in {t[3] for t in tasks if t[3] is not None}:
            prefix = transcript.model_copy(update={"segments": transcript.segments[:m]})
            renders[m] = prompts.render_transcript(prefix, self.max_transcript_chars)[0]

        def one(task: tuple[Fact, int, Fact, int | None]) -> FactProbe:
            _, _, wording, m = task
            return self.probe(llm, self._messages(renders[m], family, wording, transcript.lang), counts, lock)

        if self.parallel > 1 and len(tasks) > 1:
            with ThreadPoolExecutor(max_workers=min(self.parallel, len(tasks))) as ex:
                results = list(ex.map(one, tasks))
        else:
            results = [one(t) for t in tasks]

        per: dict[tuple[str, int], dict[str, Any]] = {}  # one entry per (fact, wording)
        for (fact, w, wording, m), res in zip(tasks, results):
            if m is None:
                per[(fact.id, w)] = {"question": wording.question(self.question_lang), "p": dict(res.p),
                                     "method": res.method, **({"info": res.info} if res.info else {})}
        for (fact, w, _, m), res in zip(tasks, results):  # N8: max p(yes) over the prefixes and the full call
            if m is None:
                continue
            d = per[(fact.id, w)]
            d.setdefault("prefix", {"full": d["p"]["yes"]})[f"{m}/{len(transcript.segments)}"] = res.p["yes"]
            if res.p["yes"] > d["p"]["yes"]:
                d["p"] = dict(res.p)
                d["prefix_used"] = m

        facts: dict[str, dict[str, Any]] = {}
        probs: dict[str, dict[str, float]] = {}
        for fact in ft.facts:
            ws = [per[(fact.id, w)] for w in range(len(wordings[fact.id]))]
            facts[fact.id] = {"label": fact.label, "role": fact.role, **ws[0]}
            if len(ws) > 1:  # R6: average the answer distribution over the wordings of this fact
                facts[fact.id]["p"] = average_probs([d["p"] for d in ws])
                facts[fact.id]["wordings"] = [
                    {"table": src, "p": d["p"], "method": d["method"],
                     **({"prefix_used": d["prefix_used"]} if "prefix_used" in d else {})}
                    for (src, _), d in zip(wordings[fact.id], ws)]
            probs[fact.id] = dict(facts[fact.id]["p"])

        values = {fid: self._decide(p) for fid, p in probs.items()}
        for fid, v in values.items():
            facts[fid]["value"] = v
        rule = ft.decide(values)
        label: Label = rule.label if rule else "no_alert"
        soft = {r.id: round(eval_soft(r.node, probs), 4) for r in ft.rules}
        p_alarm = max((soft[r.id] for r in ft.rules if r.label == "alarm"), default=0.0)
        p_review = max((soft[r.id] for r in ft.rules if r.label == "review"), default=0.0)

        if label == "alarm":
            p_rule = soft[rule.id] if rule else 1.0
            score = self.alarm_base + (1.0 - self.alarm_base) * p_rule
            confidence, verdict = max(0.05, p_rule), "present"
        elif label == "review":
            score, confidence, verdict = self.review_score, self.review_confidence, "undetermined"
        else:
            score = self.no_alert_scale * p_alarm
            confidence, verdict = 1.0 - max(p_alarm, p_review), "absent"

        shown = rule_facts(rule.node) if rule and rule.node != ("true",) else \
            [f.id for f in ft.facts if f.role != "exculpatory" or values[f.id] == "yes"]
        fact_txt = "; ".join(_fmt_fact(ft.fact(fid).label, values[fid], probs[fid]) for fid in shown)
        rule_id = rule.id if rule else "(keine Regel)"
        rule_txt = (rule.text if rule and rule.text else _LABEL_DE[label]).rstrip(".")
        summary = f"{rule_txt}. Regel: {rule_id}. Fakten: {fact_txt}"
        detail: dict[str, Any] = {
            "decision": label, "facts": facts, "summary": summary,
            "rule": ({"id": rule.id, "label": rule.label, "when": rule.when, "text": rule.text} if rule
                     else {"id": None, "label": "no_alert", "when": None, "text": "keine Regel trifft zu"}),
            "rule_probs": soft, "p_alarm": round(p_alarm, 4), "p_review": round(p_review, 4),
            "question_lang": self.question_lang,
        }
        if self.unclear_band is not None:
            detail["unclear_band"] = list(self.unclear_band)
        fs = FamilyScore(score=round(min(1.0, max(0.0, score)), 4), confidence=round(min(1.0, confidence), 4),
                         verdict=verdict, reason=summary, detail=detail)

        findings: list[Finding] = []
        if self.evidence:
            findings = self._evidence(llm, transcript, rendered, family, ft, facts, fs, rule_id, counts, lock)
        fs.detail.update(llm_calls=counts["llm_calls"], cached_probes=counts["cached_probes"])  # pydantic copied `detail`
        return fs, findings

    def _evidence(self, llm: LLM, transcript: Transcript, rendered: str, family: Family, ft: FamilyTable,
                  facts: dict[str, dict[str, Any]], fs: FamilyScore, rule_id: str,
                  counts: dict[str, int], lock: threading.Lock) -> list[Finding]:
        """One JSON call per fact with p(yes) > evidence_min: segment ids + a short German reason.
        Exculpatory facts keep theirs in the detail ("why not an alarm"); the others become findings."""
        findings: list[Finding] = []
        errors: dict[str, str] = {}
        cited: set[str] = set()
        for fact in ft.facts:
            d = facts[fact.id]
            if d["p"]["yes"] <= self.evidence_min:
                continue
            messages = fp.evidence_messages(rendered, family.label, family.id, fact.question(self.question_lang),
                                            d["p"]["yes"], self.reason_language,
                                            example_id=transcript.segments[0].id, transcript_lang=transcript.lang)
            with lock:
                counts["llm_calls"] += 1
            try:
                raw = (llm.chat(messages, temperature=0.0, max_tokens=self.max_tokens,
                                json_schema=prompts.evidence_schema()) or [""])[0]
                obj = prompts.parse_json_object(raw)
                if obj is None:
                    raise ValueError(f"unparseable evidence answer: {str(raw)[:200]!r}")
            except Exception as e:
                log.warning("%s: evidence for %s.%s failed: %s", self.name, family.id, fact.id, e)
                errors[fact.id] = f"{type(e).__name__}: {e}"
                continue
            seg_ids = prompts.clean_evidence(obj.get("evidence"), transcript)
            reason = prompts.clean_reason(obj.get("reason"))
            d["evidence"], d["reason"] = seg_ids, reason
            if fact.role == "exculpatory" or not seg_ids:
                continue
            cited.update(seg_ids)
            head = f"Fakt: {_fmt_fact(fact.label, d['value'], d['p'])}"
            text = f"{head} - {reason} (Regel: {rule_id})" if reason else f"{head} (Regel: {rule_id})"
            findings += self.evidence_findings(transcript, family, seg_ids, fs.score, lambda run, t=text: t,
                                               {"fact": fact.id, "role": fact.role, "p_yes": d["p"]["yes"],
                                                "rule": rule_id})
        fs.segment_ids = [s.id for s in transcript.segments if s.id in cited]
        if errors:
            fs.detail["evidence_errors"] = errors
        return findings
