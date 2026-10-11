"""The API's backend logic (no FastAPI here): stored results + the live rule book + per-client settings ->
JSON-ready dicts. Contract: docs/API.md.

Everything is re-decided from the stored per-call results (both readers' fact answers are in result.json), with
the same pure functions the Streamlit demo uses (:mod:`callguard.fact_policy`, the ``two_readers`` fusion with
``rule: policy``, :mod:`callguard.policy_versions`, :mod:`callguard.feedback`). No model is ever called.
"""

from __future__ import annotations

import copy
import logging
import re
import threading
import time
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml

from callguard import audit
from callguard import fact_policy as fpol
from callguard import feedback as fb
from callguard import policy_edit as pe
from callguard.cache import stable_hash
from callguard.checks.facts import CROSS_FAMILY, DEFAULT_TABLE, PolicyTable, PolicyTableError, parse_rule
from callguard.config import ROOT, AppConfig
from callguard.policy_versions import FourEyesError, VersionStore
from callguard.types import LABELS, CallResult, CheckResult, Decision, Family
from callguard.ui import backend as be

log = logging.getLogger(__name__)

API_VERSION = "1"
APP_NAME = "Sherlock Phones"
LABELS_EN_FILE = ROOT / "config" / "display" / "labels_en.yaml"
LABEL_EN = {"alarm": "Alarm", "review": "Review", "no_alert": "No alert"}
VALUE_EN = {"yes": "yes", "no": "no", "unclear": "unclear"}
CROSS_OUT = "cross"  # the API's id of the virtual family of cross rules (internally CROSS_FAMILY)
COMBINATION_EN = {
    "agree": ("Agreement", "Both readers yes -> yes, both no -> no, otherwise unclear (the review rules apply)."),
    "a_checked": ("{a}, {b} as check", "{a} decides, unless {b} clearly says the opposite -> unclear."),
    "only_a": ("{a} only", "Only {a} counts; {b}'s answer is shown but does not decide."),
    "only_b": ("{b} only", "Only {b} counts; {a}'s answer is shown but does not decide."),
}
ON_SPLIT_EN = {
    "rules": ("Rule book decides", "The combined facts go through the rules as usual (default)."),
    "review": ("Review", "If {a} alone and {b} alone would reach different verdicts, the call goes at least to review."),
    "alarm": ("Alarm", "If {a} alone and {b} alone would reach different verdicts, the call becomes an alarm."),
}
REVIEW_REASONS = ("context_harmless", "transcript_error", "rule_too_strict", "rule_too_lax", "missing_info",
                  "other_family")
FLAG = ("alarm", "review")


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        detail = english(detail)
        super().__init__(detail)
        self.status = status
        self.detail = detail


_EN = [  # policy_versions' German messages -> English (officer-facing strings of the API are English)
    (r"^Bitte Ihren Namen angeben.*", "Please give your name (it is recorded in the audit log)."),
    (r"^Version (\d+) ist (\w+), nicht Entwurf\.$", r"Version \1 is not an open draft (status: \2)."),
    (r"^Freigabe braucht den Namen.*", "Approval needs the name of the approving person."),
    (r"^Vier-Augen-Prinzip: (.+) hat Version (\d+) verfasst.*",
     r"Four-eyes principle: \1 wrote version \2 and cannot approve it. A second person must approve."),
    (r"^Version (\d+) ist ungültig: (.*)", r"Version \1 is invalid: \2"),
    (r"^Seit dem Entwurf wurde ausserhalb geändert: ([^.]*)\..*",
     r"Changed elsewhere since the draft was made (\1). Reject this draft and create it again on the current version."),
    (r"^Version (\d+) ist kein Entwurf\.$", r"Version \1 is not an open draft."),
    (r"^Fakten ändern: .*", "Changing facts needs approval by a second person: this change is not only about rules "
                            "(questions, facts or categories). Submit it as a fact proposal."),
    (r"^Keine Änderung an den Regeln\.$", "No change to the rules."),
    (r"^Keine sofort wirksame Regeländerung.*", "There is no instant rule change to undo."),
]


def english(msg: str) -> str:
    for pat, rep in _EN:
        if re.match(pat, msg, flags=re.S):
            return re.sub(pat, rep, msg, flags=re.S)
    return msg


def bad(detail: str) -> ApiError:
    return ApiError(400, detail)


def missing(detail: str) -> ApiError:
    return ApiError(404, detail)


def conflict(detail: str) -> ApiError:
    return ApiError(409, detail)


def fam_out(fid: str | None) -> str | None:
    return CROSS_OUT if fid == CROSS_FAMILY else fid


def fam_in(fid: str | None) -> str | None:
    return CROSS_FAMILY if fid == CROSS_OUT else fid


def r4(x: Any) -> float | None:
    return None if x is None else round(float(x), 4)


@dataclass
class ClientSettings:
    certainty: float | None  # None: the profile has no fact policy
    combination: str | None
    threshold: float
    on_split: str | None = None  # None: the profile has no fact policy (or keep the live policy's value)


@dataclass
class Outcome:
    decision: Decision
    facts: CheckResult | None  # the combined facts result (both readers resolved + rules per family)
    error: str | None = None


@dataclass
class Outcomes:
    by_call: dict[str, Outcome]
    key: str
    elapsed_ms: float = 0.0
    policy: Any = None


class _NoVersion:
    """What :meth:`Service._apply` returns for a demo-book change: no rule-book version was written."""

    n = None


@dataclass
class Labels:
    families: dict[str, str] = field(default_factory=dict)
    facts: dict[str, str] = field(default_factory=dict)
    rules: dict[str, str] = field(default_factory=dict)


def load_labels_en(path: Path = LABELS_EN_FILE) -> Labels:
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except Exception:
        return Labels()
    return Labels(**{k: {str(a): str(b) for a, b in (raw.get(k) or {}).items()} for k in ("families", "facts", "rules")})


# --------------------------------------------------------------------------------------------
# rule conditions in plain English
# --------------------------------------------------------------------------------------------


def render_node_en(node: Any, labels: Mapping[str, str], top: bool = True) -> str:
    kind = node[0]
    if kind == "true":
        return "always"
    if kind == "cmp":
        fact, vals = node[1], sorted(node[2])
        name = f"\"{labels.get(fact, fact)}\""
        if len(vals) == 1:
            return f"{name} is {VALUE_EN.get(vals[0], vals[0])}"
        if len(vals) == 2:
            (other,) = set(VALUE_EN) - set(vals)
            return f"{name} is not {other}"
        return f"{name} is anything"
    if kind == "not":
        inner = node[1]
        if inner[0] == "cmp" and len(inner[2]) == 1:
            (v,) = tuple(inner[2])
            return f"\"{labels.get(inner[1], inner[1])}\" is not {VALUE_EN.get(v, v)}"
        return f"NOT ({render_node_en(inner, labels, False)})"
    if kind in ("and", "or"):
        joiner = " AND " if kind == "and" else " OR "
        out = joiner.join(render_node_en(n, labels, False) for n in node[1:])
        return out if top or kind == "and" else f"({out})"
    return str(node)


def condition_text(when: str, labels: Mapping[str, str]) -> str:
    try:
        return render_node_en(parse_rule(when or "true"), labels)
    except PolicyTableError:
        return when


def tree_node(node: Any, labels: Mapping[str, str]) -> dict[str, Any]:
    """A parsed rule node as JSON for the UI: ``{"op": "and"|"or", "items": [...]}``, ``{"op": "not", "item": …}``,
    ``{"op": "true"}`` or a fact test ``{"op": "fact", "fact": id, "label": …, "values": [...]}`` (the fact must
    have one of ``values``; negations of one fact test are folded into ``values``, as the rule engine reads them)."""
    kind = node[0]
    if kind == "cmp":
        vals = [v for v in ("yes", "unclear", "no") if v in node[2]]
        return {"op": "fact", "fact": node[1], "label": labels.get(node[1], node[1]), "values": vals}
    if kind == "not":
        inner = node[1]
        if inner[0] == "cmp":
            vals = [v for v in ("yes", "unclear", "no") if v not in inner[2]]
            return {"op": "fact", "fact": inner[1], "label": labels.get(inner[1], inner[1]), "values": vals}
        return {"op": "not", "item": tree_node(inner, labels)}
    if kind in ("and", "or"):
        return {"op": kind, "items": [tree_node(n, labels) for n in node[1:]]}
    return {"op": "true"}


def condition_tree(when: str, labels: Mapping[str, str]) -> dict[str, Any] | None:
    try:
        return tree_node(parse_rule(when or "true"), labels)
    except PolicyTableError:
        return None


# A fact reader's passage reason as the pipeline writes it (checks/facts.py, checks/kev_facts.py):
#   "Fakt: <label> = <value> (<p>) - <why> (Regel: <id of the rule that reader alone matched>)"
_FACT_REASON = re.compile(r"^Fakt:\s*(?P<label>.*?)\s*=\s*(?P<value>ja|nein|unklar)(?:\s*\([^)]*\))?\s*(?:-\s*(?P<why>.*?))?\s*"
                          r"(?:\(Regel:\s*[^)]*\))?\s*$", re.S)
_MASK_DROP = re.compile(r"ohne diese Stelle sinkt p\(ja\) von ([\d.]+) auf ([\d.]+)")
_VALUE_DE = {"ja": "yes", "nein": "no", "unklar": "unclear"}


HARMLESS_SEP = "; "  # the keyword list stores one text; the API shows / accepts a list of notes


def harmless_list(text: Any) -> list[str]:
    """When a keyword hit is NOT suspicious: the stored text as a list of notes (``; ``-separated)."""
    return [p.strip() for p in str(text or "").split(HARMLESS_SEP) if p.strip()]


def harmless_text(value: Any) -> str | None:
    """List (or a plain string, for older clients) -> the stored text; empty -> None."""
    items = [str(v).strip() for v in value] if isinstance(value, (list, tuple)) else [str(value or "").strip()]
    out = HARMLESS_SEP.join(i for i in items if i)
    return out or None


def build_when(conds: list[tuple[str, str, bool]], join: str) -> str:
    if not conds:
        return "true"
    return (" and " if join == "and" else " or ").join(f"{f} {'!=' if neg else '='} {v}" for f, v, neg in conds)


# --------------------------------------------------------------------------------------------
# model names for people (the stored results name models by their id / cache tag)
# --------------------------------------------------------------------------------------------

_PRETTY = [  # (pattern on the stored id, readable name); first match wins, unknown ids are shown as they are
    (r"whisper-large-v3-turbo.*(gsw|swiss)|whisper-turbo-gsw", "Whisper large-v3-turbo, Swiss German fine-tune"),
    (r"whisper-large-v3.*(gsw|swiss)", "Whisper large-v3, Swiss German fine-tune"),
    (r"qwen3\.8-27b.*(iq3|q3|3bit)", "Qwen3.8-27B (3-bit)"),
    (r"qwen3\.8-27b.*(q6|6bit)", "Qwen3.8-27B (6-bit)"),
    (r"qwen2\.5-7b-instruct-awq", "Qwen2.5-7B-Instruct (AWQ)"),
    (r"kev-4b", "Kev-4B"),
    (r"wav2vec2.*(gsw|swissdial)", "wav2vec2 XLS-R Swiss German dialect model (SwissDial)"),
    (r"^sherpa_onnx$", "sherpa-onnx speaker separation"),
]


def pretty_model(model_id: str | None) -> str | None:
    if not model_id:
        return None
    for pat, name in _PRETTY:
        if re.search(pat, model_id, flags=re.I):
            return name
    return model_id


def _compact(s: str) -> str:
    return re.sub(r"[^a-z0-9.]", "", s.lower())


def display_model(model_id: str | None, configured: str | None) -> str | None:
    """The configured display name (fact_policy.yaml ``model:``) when it names the model the run used (or no
    run says), else the readable form of what the run used: a stale display name never hides the real model."""
    if configured and (not model_id or _compact(configured.split("(")[0]) in _compact(model_id)):
        return configured
    return pretty_model(model_id) if model_id else (configured or None)


def llm_model_id(cfg: AppConfig, name: str) -> str | None:
    spec = dict((cfg.llms or {}).get(name) or {})
    ident = dict(spec.get("identity") or {})
    return str(spec.get("cache_tag") or ident.get("model") or spec.get("model") or "") or None


# --------------------------------------------------------------------------------------------
# the service
# --------------------------------------------------------------------------------------------


class Service:
    """One per API process. Thread-safe enough for a demo: writes and memo updates hold ``self.lock``."""

    def __init__(self, cfg: AppConfig, *, labels_en: Labels | None = None):
        self.cfg = cfg
        self.labels = labels_en or load_labels_en()
        self.engine = be.Engine(cfg)
        self.fusion = self.engine.fusion
        self.runs_dir: Path = self.engine.ctx.runs_dir
        self.has_policy = getattr(self.fusion, "rule", None) == "policy" and hasattr(self.fusion, "decide_checks")
        self.defaults = be.fusion_defaults(cfg)
        self.weights = be.check_weights(cfg)
        self.lock = threading.RLock()
        self.clients: dict[str, ClientSettings] = {}
        self.prev: dict[str, dict[str, str]] = {}  # client -> labels at its previous settings
        self._memo: OrderedDict[str, Outcomes] = OrderedDict()
        # Demo rule book (``PUT /api/rulebook``): rules kept in this process only, never written to the policy
        # table or its versions. None = production (the live config/policy_table.yaml decides).
        self.demo: dict[str, Any] | None = None
        self.demo_undo: list[dict[str, Any]] = []
        self.reload()

    # -- loading -------------------------------------------------------------------------------

    def _dir_stamp(self) -> Any:
        root = Path(self.runs_dir)
        out = []
        for f in sorted(root.glob("*/result.json")) if root.is_dir() else []:
            try:
                st = f.stat()
                out.append((f.parent.name, st.st_mtime_ns, st.st_size))
            except OSError:
                pass
        return out

    def reload(self, force: bool = False) -> None:
        """Re-read the results when any result.json changed (a cheap stat of every file; parsing is memoised
        by :func:`be.load_results` per file version anyway)."""
        stamp = self._dir_stamp()
        if force or stamp != getattr(self, "_stamp", None):
            self.loaded = be.load_results(self.runs_dir)
            self._stamp = stamp

    def _file_memo(self, path: Path, fn: Any) -> Any:
        """``fn(path)`` memoised per file version (mtime + size): the YAML files are re-read only when changed."""
        try:
            st = path.stat()
            ver = (st.st_mtime_ns, st.st_size)
        except OSError:
            ver = None
        memo = self.__dict__.setdefault("_files", {})
        hit = memo.get((str(path), fn))
        if hit is not None and hit[0] == ver and ver is not None:
            return copy.deepcopy(hit[1])
        val = fn(path)
        memo[(str(path), fn)] = (ver, val)
        return copy.deepcopy(val)

    @property
    def results(self) -> dict[str, CallResult]:
        """The stored results, with the keyword check re-run on each stored transcript against the CURRENT keyword
        list (milliseconds per call, deterministic). So a keyword edit saved here changes hits, highlights and
        decisions at once, not only after the next pipeline run. Everything else is the stored result."""
        return self._live_keywords()

    def keyword_check(self) -> Any:
        from callguard.demo import keywords as kwe

        return kwe.keyword_check(self.engine)

    def _live_keywords(self) -> dict[str, CallResult]:
        stored = self.loaded.results
        check = self.keyword_check()
        if check is None:
            return stored
        # keyed on the keyword list + criteria only (what the keyword check reads): a rule edit rewrites the policy
        # table, and re-running the keyword check on every transcript for it cost ~1 s per 10 calls per edit
        key = (self.loaded.signature, stable_hash(self._families_key()[:2]))
        hit = self.__dict__.get("_kw_live")
        if hit is not None and hit[0] == key:
            return hit[1]
        with self.lock:
            hit = self.__dict__.get("_kw_live")
            if hit is not None and hit[0] == key:
                return hit[1]
            fams = self.families()
            out: dict[str, CallResult] = {}
            for cid, r in stored.items():
                if check.name not in r.checks:  # the run had no keyword check: keep it that way
                    out[cid] = r
                    continue
                try:
                    tr = be.check_view_transcript(self.engine.pipeline, check, r)
                    cr = check.run(tr, fams)
                    cr.check, cr.type, cr.view = check.name, check.plugin_type, tr.view
                    out[cid] = r.model_copy(update={"checks": {**r.checks, check.name: cr}})
                except Exception as e:  # keep the stored hits rather than lose the call
                    log.warning("API: keyword re-run of %s failed: %s", cid, e)
                    out[cid] = r
            self._kw_live = (key, out)
        return out

    def result(self, call_id: str) -> CallResult:
        r = self.results.get(call_id)
        if r is None:
            raise missing(f"unknown call {call_id!r}")
        return r

    def families(self) -> list[Family]:
        key = self._families_key()
        hit = self.__dict__.get("_fams")
        if hit is None or hit[0] != key:
            hit = self._fams = (key, self.engine.families())
        return [f.model_copy() for f in hit[1]]

    def table_path(self) -> Path:
        rel = str(getattr(self.fusion, "policy_table", None) or next(
            (c.get("policy_table") for c in self.cfg.checks if c.get("type") == "facts" and c.get("policy_table")),
            DEFAULT_TABLE))
        return Path(rel) if Path(rel).is_absolute() else ROOT / rel

    def live_doc(self) -> dict[str, Any]:
        return self._file_memo(self.table_path(), pe.load_doc)

    # -- the active rule book: production (the live file) or the in-memory demo book -----------------

    @property
    def demo_mode(self) -> bool:
        return self.demo is not None

    def demo_doc(self) -> dict[str, Any] | None:
        """The live table with its rules replaced by the demo book's (facts, questions, bases stay the live ones,
        so an approved fact is in the demo too); None in production mode. A demo rule whose fact was removed
        meanwhile is left out rather than break every decision."""
        if self.demo is None:
            return None
        doc = self.live_doc()
        fams = doc.get("families") or {}
        for fid, fd in fams.items():
            fd["rules"] = copy.deepcopy((self.demo.get("families") or {}).get(fid) or [])
        cross = copy.deepcopy(self.demo.get("cross_rules") or [])
        if cross:
            doc["cross_rules"] = cross
        else:
            doc.pop("cross_rules", None)
        try:
            pe.validate(doc)
        except PolicyTableError:
            for fid, fd in fams.items():
                ids = {str(f.get("id")) for f in fd.get("facts") or []}
                fd["rules"] = [r for r in fd["rules"] if self._parses(r, ids)]
            qual = {f"{fid}.{f.get('id')}" for fid, fd in fams.items() for f in fd.get("facts") or []}
            cross_ok = [r for r in doc.get("cross_rules") or [] if self._parses(r, qual)]
            if cross_ok:
                doc["cross_rules"] = cross_ok
            else:
                doc.pop("cross_rules", None)
        return doc

    @staticmethod
    def _parses(rule: Mapping[str, Any], facts: set[str]) -> bool:
        try:
            parse_rule(str(rule.get("when") or "true"), facts)
            return True
        except PolicyTableError:
            return False

    def active_doc(self) -> dict[str, Any]:
        """The rule book that decides now: the demo book in demo mode, else the live policy table."""
        demo = self.demo_doc()
        return self.live_doc() if demo is None else demo

    @staticmethod
    def rule_count(doc: Mapping[str, Any]) -> tuple[int, int]:
        """(all rules, switched-on rules) of a rule book, cross rules included."""
        rules = [r for fd in (doc.get("families") or {}).values() for r in (fd or {}).get("rules") or []]
        rules += list(doc.get("cross_rules") or [])
        return len(rules), sum(1 for r in rules if pe.is_enabled(r))

    def rulebook_json(self) -> dict[str, Any]:
        live = self.live_doc() if self.has_policy else {}
        n_live, on_live = self.rule_count(live) if live else (0, 0)
        name = self.cfg.name.split("-")[0].capitalize() if self.cfg.name else "Production"
        out: dict[str, Any] = {"mode": "demo" if self.demo_mode else "production", "name": name,
                               "production": {"rules": n_live, "enabled": on_live},
                               "editable": self.has_policy}
        if self.demo_mode:
            n, on = self.rule_count(self.demo_doc() or {})
            out.update(rules=n, enabled=on, can_undo=bool(self.demo_undo))
        else:
            out.update(rules=n_live, enabled=on_live)
        return out

    def set_rulebook(self, client: str, mode: str) -> dict[str, Any]:
        """``demo``: an EMPTY rule book in this process (every call is re-decided from its stored facts with no
        rule; rules added now go to this book only). ``production``: back to the live policy table. Nothing is
        written either way."""
        self._require_policy()
        if mode not in ("demo", "production"):
            raise bad("mode must be demo or production")
        s = self.settings(client)
        before = self.labels_of(s)
        with self.lock:
            if mode == "demo":
                self.demo = {"families": {}, "cross_rules": []}
            else:
                self.demo = None
            self.demo_undo = []
        after = self.labels_of(s)
        return {"rulebook": self.rulebook_json(), "counts": self.counts(after), "effect": self.effect(before, after)}

    def _set_demo_rules(self, cand: Mapping[str, Any]) -> None:
        """Store a candidate doc's rules as the demo book (the previous book goes on the undo stack)."""
        assert self.demo is not None
        self.demo_undo.append(copy.deepcopy(self.demo))
        del self.demo_undo[:-50]
        self.demo = {"families": {fid: copy.deepcopy((fd or {}).get("rules") or [])
                                  for fid, fd in (cand.get("families") or {}).items()},
                     "cross_rules": copy.deepcopy(list(cand.get("cross_rules") or []))}

    def table(self, doc: dict[str, Any] | None = None) -> PolicyTable:
        return pe.validate(self.live_doc() if doc is None else doc)

    def live_policy(self) -> Any:
        return self.fusion.fact_policy() if self.has_policy else None

    def store(self) -> VersionStore:
        from callguard.routing import DEFAULT_ROUTING

        notify = next((s for s in self.cfg.sinks if s.get("type") == "notify"), {})
        routing = Path(str(notify.get("routing") or DEFAULT_ROUTING))
        extras: dict[str, Path] = {"criteria": self.cfg.paths.resolve("criteria"),
                                   "keywords": self.cfg.paths.resolve("keywords"),
                                   "routing": routing if routing.is_absolute() else ROOT / routing}
        if self.cfg.paths.tuning:
            t = Path(self.cfg.paths.tuning)
            extras["tuning"] = t if t.is_absolute() else ROOT / t
        if self.has_policy:
            extras["fact_policy"] = fpol.resolve_path(self.fusion.fact_policy_path)
        return VersionStore(self.table_path(), audit_dir=self.runs_dir, extras=extras)

    # -- labels --------------------------------------------------------------------------------

    def family_label(self, fid: str | None, families: list[Family] | None = None) -> str:
        if fid is None:
            return ""
        if fid in self.labels.families:
            return self.labels.families[fid]
        for f in families or self.families():
            if f.id == fid:
                return be.short_label(f.label)
        return fid

    def fact_label(self, fam: str, fid: str, de: str = "") -> str:
        return self.labels.facts.get(f"{fam}.{fid}") or de or fid

    def rule_text(self, rule_id: str | None, de: str = "") -> str:
        return (self.labels.rules.get(rule_id or "") or de or "").strip()

    def fact_labels_for(self, doc: dict[str, Any], fam: str | None) -> dict[str, str]:
        """fact id (family rules) or ``family.fact`` (cross rules) -> English label."""
        out: dict[str, str] = {}
        for f_id, fd in (doc.get("families") or {}).items():
            for f in (fd or {}).get("facts") or []:
                lab = self.fact_label(f_id, str(f.get("id")), str(f.get("label") or ""))
                out[f"{f_id}.{f.get('id')}"] = f"{self.family_label(f_id)}: {lab}"
                if fam == f_id:
                    out[str(f.get("id"))] = lab
        return out

    def legal_basis(self, doc: dict[str, Any], fam: str | None, rule_id: str | None = None) -> str:
        fd = (doc.get("families") or {}).get(fam or "") or {}
        if rule_id:
            for r in fd.get("rules") or []:
                if r.get("id") == rule_id and r.get("basis"):
                    return str(r["basis"])
        return str(fd.get("basis") or "")

    # -- settings ------------------------------------------------------------------------------

    def default_settings(self) -> ClientSettings:
        pol = self.live_policy()
        return ClientSettings(certainty=pol.certainty() if pol is not None else None,
                              combination=pol.combination if pol is not None else None,
                              threshold=float(self.defaults["threshold"]),
                              on_split=pol.on_split if pol is not None else None)

    def settings(self, client: str) -> ClientSettings:
        with self.lock:
            s = self.clients.get(client)
            if s is None:
                s = self.clients[client] = self.default_settings()
            return s

    def policy_for(self, s: ClientSettings) -> Any:
        live = self.live_policy()
        if live is None:
            return None
        pol = live
        if s.certainty is not None and abs(s.certainty - live.certainty()) > 1e-9:
            pol = pol.with_certainty(s.certainty, "both" if live.a.mode == "band" else "b")
        if s.combination and s.combination != pol.combination:
            pol = pol.with_combination(s.combination)
        if s.on_split and s.on_split != pol.on_split:
            pol = pol.with_on_split(s.on_split)
        return pol

    def overrides(self, s: ClientSettings) -> dict[str, Any]:
        return {"threshold": s.threshold, "review_band": self.defaults["review_band"],
                "max_uncertainty": min(1.0, max(0.0, self.defaults["max_uncertainty"])),
                "weights": dict(self.weights)}

    def settings_json(self, s: ClientSettings) -> dict[str, Any]:
        d = self.default_settings()
        pol = self.live_policy()
        a, b = (pol.a.label, pol.b.label) if pol is not None else ("A", "B")
        out: dict[str, Any] = {
            "certainty": r4(s.certainty), "combination": s.combination, "threshold": r4(s.threshold),
            "on_split": s.on_split,
            "review_band": r4(self.defaults["review_band"]),
            "defaults": {"certainty": r4(d.certainty), "combination": d.combination, "threshold": r4(d.threshold),
                         "on_split": d.on_split},
            "options": {
                "certainty": {"min": 0.5, "max": 1.0, "step": 0.01,
                              "help": "A reader's answer counts as yes if p(yes) >= c, as no if p(yes) <= 1 - c, "
                                      "else unclear. Higher c = more unclear facts = more calls to review."},
                "combination": [{"id": k, "label": lab.format(a=a, b=b), "help": h.format(a=a, b=b)}
                                for k, (lab, h) in COMBINATION_EN.items()],
                "on_split": [{"id": k, "label": lab, "help": h.format(a=a, b=b)} for k, (lab, h) in ON_SPLIT_EN.items()],
                "threshold": {"min": 0.05, "max": 0.95, "step": 0.01,
                              "help": "Call score at or above this is an alarm; within the review band below it, review."},
            },
        }
        if pol is None:
            out["options"]["combination"] = []
            out["options"]["on_split"] = []
        return out

    def update_settings(self, client: str, body: Mapping[str, Any]) -> dict[str, Any]:
        t0 = time.perf_counter()
        with self.lock:
            old = self.settings(client)
            before = self.labels_of(old)
            if body.get("reset"):
                new = self.default_settings()
            else:
                new = replace(old)
                if body.get("certainty") is not None:
                    c = float(body["certainty"])
                    if new.certainty is None:
                        raise bad("this profile has no fact policy (certainty)")
                    if not 0.5 <= c <= 1.0:
                        raise bad("certainty must be within 0.5 .. 1.0")
                    new.certainty = c
                if body.get("combination") is not None:
                    if new.combination is None:
                        raise bad("this profile has no fact policy (combination)")
                    if body["combination"] not in fpol.COMBINATIONS:
                        raise bad(f"combination must be one of {', '.join(fpol.COMBINATIONS)}")
                    new.combination = str(body["combination"])
                if body.get("on_split") is not None:
                    if new.on_split is None:
                        raise bad("this profile has no fact policy (on_split)")
                    if body["on_split"] not in fpol.ON_SPLIT:
                        raise bad(f"on_split must be one of {', '.join(fpol.ON_SPLIT)}")
                    new.on_split = str(body["on_split"])
                if body.get("threshold") is not None:
                    t = float(body["threshold"])
                    if not 0.0 < t < 1.0:
                        raise bad("threshold must be within 0 .. 1")
                    new.threshold = t
            self.clients[client] = new
        after = self.labels_of(new)
        changed = [{"id": cid, "before": before[cid], "after": lab} for cid, lab in sorted(after.items())
                   if cid in before and before[cid] != lab]
        return {"settings": self.settings_json(new), "counts": self.counts(after), "changed": changed,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1)}

    # -- deciding ------------------------------------------------------------------------------

    def _families_key(self) -> Any:
        """(path, mtime, size) of the keyword list, the criteria and the policy table, in this order."""
        out = []
        for p in (self.cfg.paths.resolve("keywords"), self.cfg.paths.resolve("criteria"), self.table_path()):
            try:
                st = p.stat()
                out.append((str(p), st.st_mtime_ns, st.st_size))
            except OSError:
                out.append((str(p), 0, 0))
        return out

    # Speed (60 calls, a laptop): the expensive part of a re-decision is resolving both readers' facts and the
    # rules per family (fact_policy.combine_family), then the weighted fusion per call. Both are memoised by
    # CONTENT, so a rule edit only recomputes its own family, and a call whose combined facts did not change keeps
    # its decision (only calls that move are re-fused). Settings that were seen before are a dict lookup; a
    # background thread pre-computes the slider grid at start-up (:meth:`prewarm`).

    _FAM_MEMO_MAX = 60_000
    _DEC_MEMO_MAX = 60_000

    def _combine_one(self, r: CallResult, tables: Any, cross: Any, pol: Any, pkey: str, fam_keys: Mapping[str, str],
                     names: Mapping[str, str], fam_memo: dict) -> dict[str, CheckResult]:
        """fact_policy.combined_checks for one call, with combine_family memoised per (call, family, policy, family
        table): the same result as the core function (tests compare), computed once per distinct input."""
        checks = r.checks
        a_name, b_name = pol.a.check, pol.b.check
        rest = {k: v for k, v in checks.items() if k not in (a_name, b_name)}
        if checks.get(a_name) is None and checks.get(b_name) is None:
            return rest
        a, b = fpol.usable(checks.get(a_name)), fpol.usable(checks.get(b_name))
        fams = [f for f in tables if (a and f in a.family_scores) or (b and f in b.family_scores)]
        scoring = self.fusion.scoring
        out = {}
        for f in fams:
            k = (r.call_id, f, pkey, fam_keys[f])
            fs = fam_memo.get(k)
            if fs is None:
                fs = fam_memo[k] = fpol.combine_family(tables[f], a.family_scores.get(f) if a else None,
                                                       b.family_scores.get(f) if b else None, pol, **scoring)
            out[f] = fs
        disagree = {f: fs.detail["fact_policy"]["disagree"] for f, fs in out.items() if fs.detail["fact_policy"]["disagree"]}
        meta: dict[str, Any] = {"fact_policy": {"key": pkey, "combination": pol.combination,
                                                "readers": [pol.a.label, pol.b.label], "disagree": disagree,
                                                "missing": [x.label for x, y in zip(pol.readers, (a, b)) if y is None]},
                                "models": sorted({str(x.meta["model"]) for x in (a, b) if x is not None and x.meta.get("model")})}
        if a is not None and a.meta.get("model"):
            meta["model"] = a.meta["model"]
        src = a or b
        fam_ok = set(fams)
        # both readers' passages (A points at segments; B, e.g. Kev with mask passages, finds its own): as
        # fact_policy.combined_result does
        findings = [f for x in (a, b) if x is not None for f in x.findings if f.family in fam_ok]
        xr = fpol.cross_family(cross, out, findings, names, **scoring)
        if xr is not None:
            out = {**out, CROSS_FAMILY: xr[0]}
            findings = [*findings, *xr[1]]
            meta["cross_rule"] = xr[0].detail["rule"]["id"]
        comb = CheckResult(check=a_name, type="facts", family_scores=out, findings=findings, meta=meta,
                           view=src.view if src else None)
        return {**rest, a_name: comb}

    def combined(self, pol: Any, doc: dict[str, Any] | None, families: list[Family]) -> dict[str, Any]:
        """call -> the checks as the fusion sees them under ``pol`` + table (both readers resolved, rules applied),
        memoised apart from the fusion knobs: moving the threshold only re-runs the fusion."""
        key = stable_hash({"p": pol.as_dict(), "sig": self.loaded.signature, "f": self._families_key(), "doc": doc})
        memo: OrderedDict[str, dict[str, Any]] = self.__dict__.setdefault("_comb", OrderedDict())
        with self.lock:
            hit = memo.get(key)
            if hit is not None:
                memo.move_to_end(key)
                return hit
        table = self.table(doc)
        tables, cross = fpol.split_tables(table)
        fam_keys = {f: stable_hash(ft.raw) for f, ft in tables.items()}
        pkey = pol.key()
        names = self.fusion._names(families)
        fam_memo: dict = self.__dict__.setdefault("_fam_memo", {})
        if fam_memo.get("__sig__") != self.loaded.signature or len(fam_memo) > self._FAM_MEMO_MAX:
            fam_memo.clear()
            fam_memo["__sig__"] = self.loaded.signature
        out: dict[str, Any] = {}
        for cid, r in self.results.items():
            try:
                out[cid] = self._combine_one(r, tables, cross, pol, pkey, fam_keys, names, fam_memo)
            except Exception as e:
                out[cid] = e
        with self.lock:
            memo[key] = out
            while len(memo) > 48:
                memo.popitem(last=False)
        return out

    @staticmethod
    def _content_sig(checks: Mapping[str, CheckResult], a_name: str) -> str:
        """What the fusion reads from the combined facts result (scores, verdicts, reasons, evidence)."""
        comb = checks.get(a_name)
        if comb is None:
            return "-"
        return stable_hash([[f, fs.score, fs.confidence, fs.verdict, fs.reason, list(fs.segment_ids),
                             (fs.detail or {}).get("report_as")]
                            for f, fs in sorted(comb.family_scores.items())]
                           + [[x.family, x.score, x.start, x.end, x.reason, list(x.segment_ids)] for x in comb.findings])

    def warm(self) -> None:
        """Decide every call at the defaults once (start-up), so the first request is fast."""
        try:
            self.outcomes(self.default_settings())
        except Exception as e:
            log.warning("API: warm-up failed: %s", e)

    def prewarm(self, pause: float = 0.05) -> None:
        """Background: every combination x certainty on a 0.05 grid, then the default combination on 0.01 steps
        (the slider's), at the default threshold. Runs once; requests always win (each step yields)."""
        if not self.has_policy:
            return
        d = self.default_settings()
        grid = [round(0.5 + 0.05 * i, 2) for i in range(11)]
        fine = [round(0.5 + 0.01 * i, 2) for i in range(51)]
        todo = [(c, m) for m in [d.combination, *[x for x in fpol.COMBINATIONS if x != d.combination]] for c in grid]
        todo += [(c, d.combination) for c in fine if c not in grid]
        for c, m in todo:
            try:
                self.outcomes(ClientSettings(certainty=c, combination=m, threshold=d.threshold))
            except Exception as e:
                log.warning("API: prewarm %s/%s failed: %s", c, m, e)
                return
            time.sleep(pause)

    def outcomes(self, s: ClientSettings, doc: dict[str, Any] | None = None) -> Outcomes:
        if doc is None and self.has_policy:
            doc = self.demo_doc()  # None in production: the live table
        pol = self.policy_for(s)
        ov = self.overrides(s)
        self.reload()  # cheap: a stat per result file; parsed again only when one changed
        fkey = self._families_key()
        key = stable_hash({"p": pol.as_dict() if pol is not None else None, "o": ov, "sig": self.loaded.signature,
                           "f": fkey, "doc": doc})
        with self.lock:
            hit = self._memo.get(key)
            if hit is not None:
                self._memo.move_to_end(key)
                return hit
        t0 = time.perf_counter()
        families = self.families()
        out: dict[str, Outcome] = {}
        if self.has_policy:
            combined = self.combined(pol, doc, families)
            dec_memo: dict = self.__dict__.setdefault("_dec_memo", {})
            okey = stable_hash({"o": ov, "sig": self.loaded.signature, "f": fkey})
            if len(dec_memo) > self._DEC_MEMO_MAX:
                dec_memo.clear()
            for cid, r in self.results.items():
                try:
                    checks = combined[cid]
                    if isinstance(checks, Exception):
                        raise checks
                    dk = (cid, okey, self._content_sig(checks, pol.a.check))
                    d = dec_memo.get(dk)
                    if d is None:
                        d = self.fusion.decide_checks(r.transcript, checks, families, ov, r.views or None)
                        d = dec_memo[dk] = be.carry_snippets(d, r.decision)
                    out[cid] = Outcome(d, checks.get(pol.a.check))
                except Exception as e:  # one broken result must not take the inbox down
                    log.warning("API: re-deciding %s failed: %s", cid, e)
                    out[cid] = Outcome(r.decision, r.checks.get("facts"), f"{type(e).__name__}: {e}")
        else:
            for cid, r in self.results.items():
                dd = be.redecide(self.engine, r, ov, families or None)
                out[cid] = Outcome(dd.decision, r.checks.get("facts"), dd.error)
        res = Outcomes(out, key, round((time.perf_counter() - t0) * 1000, 1), pol)
        with self.lock:
            self._memo[key] = res
            while len(self._memo) > 400:
                self._memo.popitem(last=False)
        return res

    def labels_of(self, s: ClientSettings, doc: dict[str, Any] | None = None) -> dict[str, str]:
        return {cid: o.decision.label for cid, o in self.outcomes(s, doc).by_call.items()}

    @staticmethod
    def counts(labels: Mapping[str, str]) -> dict[str, int]:
        out = {lbl: 0 for lbl in LABELS}
        for lab in labels.values():
            out[lab] = out.get(lab, 0) + 1
        return out

    @staticmethod
    def effect(before: Mapping[str, str], after: Mapping[str, str]) -> dict[str, Any]:
        changed = [{"id": cid, "before": before[cid], "after": a} for cid, a in sorted(after.items())
                   if cid in before and before[cid] != a]
        net = {k: 0 for k in LABELS}
        for c in changed:
            net[c["before"]] -= 1
            net[c["after"]] += 1
        if changed:
            parts = [f"{'+' if v > 0 else '-'}{abs(v)} {LABEL_EN[k].lower()}" for k, v in net.items() if v]
            summary = f"changes {len(changed)} of {len(after)} calls: {', '.join(parts)}"
        else:
            summary = f"changes none of the {len(after)} calls"
        return {"changed": changed, "net": net, "summary": summary}

    # -- serialisation: one call ----------------------------------------------------------------

    def _can_alarm(self, families: list[Family]) -> set[str]:
        return {f.id for f in families if f.can_alarm} | {CROSS_FAMILY}

    def _family_rule(self, o: Outcome, fam: str | None) -> dict[str, Any] | None:
        if o.facts is None or fam is None:
            return None
        fs = o.facts.family_scores.get(fam)
        rule = ((fs.detail or {}).get("rule") if fs is not None else None) or None
        return rule if rule and rule.get("id") else None

    def rule_json(self, rule: Mapping[str, Any], fam: str, doc: dict[str, Any]) -> dict[str, Any]:
        cross = fam == CROSS_FAMILY
        labels = self.fact_labels_for(doc, None if cross else fam)
        if cross:
            labels = {k: v for k, v in labels.items() if "." in k}
        rid = str(rule.get("id") or "")
        out = {"id": rid, "family": fam_out(fam), "outcome": str(rule.get("label") or ""),
               "title": str(rule.get("title") or ""),
               "text": self.rule_text(rid, str(rule.get("text") or "")),
               "condition": str(rule.get("when") or "true"),
               "condition_text": condition_text(str(rule.get("when") or "true"), labels),
               "condition_tree": condition_tree(str(rule.get("when") or "true"), labels)}
        if cross:
            out["report_as"] = str(rule.get("report_as") or "") or None
        return out

    def _reason(self, o: Outcome, top: str | None, doc: dict[str, Any], families: list[Family]) -> tuple[str, dict | None]:
        d = o.decision
        if top is None:
            if self.demo_mode:
                return "No rule of the demo rule book flags this call.", None
            return "No category reached a score worth reviewing.", None
        rule = self._family_rule(o, top)
        fam_lab = self.family_label(top, families)
        if rule is not None:
            rj = self.rule_json(rule, top, doc)
            what = rj["title"] or rj["text"] or rj["condition_text"]
            return f"{fam_lab}: {what.rstrip('.')}. Rule: {rj['id']}.", rj
        fs = o.facts.family_scores.get(top) if o.facts is not None else None
        if fs is not None and "rule" in (fs.detail or {}) and o.decision.label == "no_alert":
            # the readers answered this category's facts, but no rule of the active rule book matched (in
            # production every category ends with a default rule, so this is the empty demo book's case)
            book = "demo rule book" if self.demo_mode else "rule book"
            return f"{fam_lab}: No rule of the {book} matched these facts.", None
        ff = d.families.get(top)
        return f"{fam_lab}: {ff.reason if ff is not None else ''}".strip().rstrip(":"), None

    def row(self, cid: str, o: Outcome, doc: dict[str, Any], families: list[Family], reviewed: set[str]) -> dict[str, Any]:
        r = self.results[cid]
        d = o.decision
        top = be.top_family(d, self._can_alarm(families))
        top_id = top.family if top is not None else None
        reason, rule = self._reason(o, top_id, doc, families)
        return {"id": cid, "label": d.label, "score": r4(d.score), "uncertainty": r4(d.uncertainty),
                "family": fam_out(top_id), "family_label": self.family_label(top_id, families) if top_id else "",
                "reason": reason, "rule_id": rule["id"] if rule else None,
                "legal_basis": self.legal_basis(doc, (rule or {}).get("report_as") or top_id,
                                                rule["id"] if rule else None),
                "passages": len(d.passages), "duration": r4(r.transcript.duration), "reviewed": cid in reviewed,
                "stored_label": r.decision.label, **({"error": o.error} if o.error else {})}

    def _feedback_stamp(self) -> Any:
        p = fb.feedback_path(self.runs_dir)
        try:
            st = p.stat()
            return (st.st_mtime_ns, st.st_size)
        except OSError:
            return None

    def reviewed_calls(self) -> set[str]:
        stamp = self._feedback_stamp()
        hit = self.__dict__.get("_reviewed")
        if hit is not None and hit[0] == stamp:
            return set(hit[1])
        try:
            done = fb.judged_calls(fb.load(self.runs_dir))
        except Exception:
            done = set()
        self._reviewed = (stamp, done)
        return set(done)

    def _inbox_rows(self, outs: Outcomes) -> list[dict[str, Any]]:
        """Inbox rows of one decided state, memoised per (decision state, rule book, feedback file)."""
        key = (outs.key, self._feedback_stamp(), stable_hash(self._families_key()))
        memo: OrderedDict = self.__dict__.setdefault("_rows_memo", OrderedDict())
        with self.lock:
            hit = memo.get(key)
        if hit is None:
            doc = self.active_doc() if self.has_policy else {}
            families = self.families()
            done = self.reviewed_calls()
            hit = [self.row(cid, o, doc, families, done) for cid, o in outs.by_call.items()]
            rank = {lbl: i for i, lbl in enumerate(("alarm", "review", "no_alert"))}
            hit.sort(key=lambda r: (rank.get(r["label"], 9), -(r["score"] or 0), r["id"]))
            with self.lock:
                memo[key] = hit
                while len(memo) > 64:
                    memo.popitem(last=False)
        return [dict(r) for r in hit]

    def _text_of(self, cid: str) -> str:
        memo: dict = self.__dict__.setdefault("_texts", {})
        r = self.results[cid]
        k = (cid, id(r))
        if k not in memo:
            memo[k] = " ".join(sg.text for sg in r.transcript.segments).lower()
        return memo[k]

    def list_calls(self, client: str, status: str | None = None, q: str | None = None, family: str | None = None,
                   reviewed: bool | None = None) -> dict[str, Any]:
        s = self.settings(client)
        outs = self.outcomes(s)
        rows = self._inbox_rows(outs)
        counts = self.counts({r["id"]: r["label"] for r in rows})
        if status:
            want = set(FLAG) if status == "flagged" else {status}
            if not want <= set(LABELS):
                raise bad("status must be alarm, review, no_alert or flagged")
            rows = [r for r in rows if r["label"] in want]
        if family:
            rows = [r for r in rows if r["family"] == family]
        if reviewed is not None:
            rows = [r for r in rows if r["reviewed"] == reviewed]
        if q:
            ql = q.lower()
            rows = [r for r in rows if ql in r["id"].lower() or ql in r["reason"].lower() or ql in self._text_of(r["id"])]
        return {"calls": rows, "counts": counts, "total": len(outs.by_call)}

    @staticmethod
    def segment_json(sg: Any) -> dict[str, Any]:
        return {"id": sg.id, "start": r4(sg.start), "end": r4(sg.end), "speaker": sg.speaker, "role": sg.role,
                "text": sg.text, "confidence": r4(sg.confidence)}

    def facts_json(self, o: Outcome, pol: Any) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        if o.facts is None:
            return out
        a_id, b_id = (pol.a.id, pol.b.id) if pol is not None else ("qwen", "kev")
        for fam, fs in o.facts.family_scores.items():
            if fam == CROSS_FAMILY:
                continue
            rows = []
            for fid, e in ((fs.detail or {}).get("facts") or {}).items():
                readers = e.get("readers") or {}
                ra, rb = readers.get(a_id), readers.get(b_id)
                pa = (ra or {}).get("p") if ra else (e.get("p") if not readers else None)
                pb = (rb or {}).get("p") if rb else None
                rows.append({
                    "id": fid, "label": self.fact_label(fam, fid, str(e.get("label") or "")),
                    "label_de": str(e.get("label") or ""), "role": e.get("role"),
                    "question": e.get("question") or "", "resolved": e.get("value"),
                    "agree": e.get("agree"), "combination": e.get("combination"),
                    "readers": {
                        a_id: None if not pa else {"p_yes": r4(pa.get("yes", 0.0)), "p_no": r4(pa.get("no", 0.0)),
                                                   "p_unknown": r4(pa.get("unclear", 0.0)),
                                                   "value": (ra or {}).get("value", e.get("value"))},
                        b_id: None if not pb else {"p_yes": r4(pb.get("yes", 0.0)), "value": (rb or {}).get("value")},
                    },
                    "evidence_segment_ids": list(e.get("evidence") or []),
                    **({"evidence_reason": e["reason"]} if e.get("reason") else {}),
                })
            out[fam] = rows
        return out

    def _fact_reason(self, text: str, det: Mapping[str, Any], p: Any) -> dict[str, Any]:
        """The parts of a fact reader's passage reason, for display: the fact's label, the value that reader gave,
        its p(yes), and either the drop of p(yes) without this window (Kev masking) or the reader's own sentence
        (Qwen pointing). The ``(Regel: …)`` suffix is left out on purpose: it names the rule that this ONE reader's
        answers matched when it searched for evidence, not the rule that decided the call (that is
        ``decision.rule``), so on a flagged call it is often the category's ``no_alert`` rule."""
        fid = det.get("fact")
        m = _FACT_REASON.match(text.strip())
        de = m.group("label") if m else ""
        out: dict[str, Any] = {"fact_label": self.fact_label(p.family, fid, de) if fid else (de or None),
                               "value": None, "p_yes": r4(det.get("p_yes")), "p_without": None, "why": None}
        if m:
            out["value"] = _VALUE_DE.get(m.group("value"))
            why = (m.group("why") or "").strip()
            drop = _MASK_DROP.search(why)
            if drop:
                out["p_without"] = r4(float(drop.group(2)))
            elif why and not why.startswith("Kev: diese Stelle zeigt es"):  # anchor: no sentence of its own
                out["why"] = why
        return out

    def passage_sources(self, p: Any, r: CallResult, o: Outcome, pol: Any) -> dict[str, Any]:
        """Who found a passage and why, per reason. The fusion writes each reason as ``<check>: <text>``; the text
        is matched to the finding it came from, whose detail names the fact and the rule and, for a reader that
        finds passages itself (Kev: ``evidence_method`` mask / anchor), how. Findings without a method are the
        pointed evidence of the primary reader (Qwen)."""
        checks: dict[str, CheckResult] = {n: c for n, c in r.checks.items() if c.type in ("keywords", "patterns")}
        if o.facts is not None:
            checks[o.facts.check] = o.facts
        by_reason: dict[tuple[str, str], dict[str, Any]] = {}
        for name, cr in checks.items():
            for f in cr.findings:
                by_reason.setdefault((name, (f.reason or "").strip()), dict(f.detail or {}))
        specs = self._reader_specs()

        def reader(check: str, method: str | None) -> Any:
            if method:
                return (pol.b if pol is not None else None) or next(
                    (x for x in specs if self._check_cfg(x.check).get("type") == "kev_facts"), None)
            if pol is not None:
                return pol.a
            return next((x for x in specs if x.check == check), None)

        out: list[dict[str, Any]] = []
        found: list[str] = []
        for text in p.reasons:
            check, sep, why = text.partition(": ")
            cr = checks.get(check)
            if not sep or cr is None:
                out.append({"source": "note", "source_label": None, "method": None, "text": text.strip(),
                            "fact": None, "rule": None})
                continue
            det = by_reason.get((check, why.strip()), {})
            item: dict[str, Any] = {"text": why.strip(), "fact": det.get("fact"), "rule": det.get("rule")}
            if cr.type == "keywords":
                item.update(source="keyword", source_label="Keyword", method=None,
                            phrase=det.get("phrase"), keyword_id=det.get("keyword_id"))
            elif cr.type == "patterns":
                n = det.get("n_digits")
                item.update(source="pattern", source_label="Pattern", method=None,
                            phrase=f"{n}-digit number" if n else det.get("kind"))
            else:
                method = det.get("evidence_method")
                spec = reader(check, method)
                item.update(source=spec.id if spec is not None else check,
                            source_label=spec.label if spec is not None else check,
                            method=str(method) if method else "pointing", **self._fact_reason(why, det, p))
            out.append(item)
            if item["source_label"] not in found:
                found.append(item["source_label"])
        return {"sources": out, "found_by": found}

    def call_detail(self, client: str, call_id: str) -> dict[str, Any]:
        r = self.result(call_id)
        s = self.settings(client)
        outs = self.outcomes(s)
        o = outs.by_call[call_id]
        d = o.decision
        doc = self.active_doc() if self.has_policy else {}
        families = self.families()
        row = self.row(call_id, o, doc, families, self.reviewed_calls())
        top = fam_in(row["family"])
        _, rule = self._reason(o, top, doc, families)
        gsw = (r.display_views or {}).get("gsw")
        fams = []
        for fid, ff in sorted(d.families.items(), key=lambda kv: -kv[1].score):
            fr = self._family_rule(o, fid)
            fs = o.facts.family_scores.get(fid) if o.facts is not None else None
            fams.append({"id": fam_out(fid), "label": self.family_label(fid, families), "score": r4(ff.score),
                         "uncertainty": r4(ff.uncertainty),
                         "outcome": (fs.detail or {}).get("decision") if fs is not None else None,
                         "rule_id": fr["id"] if fr else None,
                         "rule_text": self.rule_text(fr["id"], str(fr.get("text") or "")) if fr else None,
                         "reason": ff.reason})
        hits = []
        for cr in r.checks.values():
            if cr.type not in ("keywords", "patterns"):
                continue
            for f in cr.findings:
                det = f.detail or {}
                hits.append({"kind": "keyword" if cr.type == "keywords" else "pattern", "family": f.family,
                             "keyword_id": det.get("keyword_id"), "phrase": det.get("phrase") or det.get("kind"),
                             "matched_text": det.get("matched_text"), "negated": bool(det.get("negated")),
                             "segment_ids": list(f.segment_ids), "start": r4(f.start), "end": r4(f.end),
                             "score": r4(f.score), "reason": f.reason})
        hits.sort(key=lambda h: (h["start"] or 0.0))
        return {
            "id": call_id, "duration": r4(r.transcript.duration), "audio_url": f"/api/calls/{call_id}/audio",
            "has_audio": self.audio_path(r) is not None,
            "segments": [self.segment_json(sg) for sg in r.transcript.segments],
            "swiss_german": None if gsw is None or not gsw.segments else {
                "description": "Swiss German, re-transcribed from the recording per segment by a dialect speech "
                               "model (display only; no check or decision reads it)",
                "model": gsw.asr_backend.split("->")[-1].strip(),
                "segments": [{k: v for k, v in self.segment_json(sg).items() if k != "confidence"}
                             for sg in gsw.segments]},
            "decision": {"label": d.label, "score": r4(d.score), "uncertainty": r4(d.uncertainty),
                         "threshold": r4(d.threshold),
                         "review_floor": r4(d.threshold - float(self.defaults["review_band"])),
                         "family": row["family"], "family_label": row["family_label"],
                         "legal_basis": row["legal_basis"], "reason": row["reason"], "reasons": list(d.reasons),
                         "rule": rule, "stored_label": r.decision.label},
            "families": fams,
            "passages": [{"index": i, "start": r4(p.start), "end": r4(p.end), "family": fam_out(p.family),
                          "family_label": self.family_label(p.family, families), "score": r4(p.score),
                          "segment_ids": list(p.segment_ids), "reasons": list(p.reasons), "text": p.text,
                          **self.passage_sources(p, r, o, outs.policy)}
                         for i, p in enumerate(d.passages)],
            "facts": self.facts_json(o, outs.policy),
            "keyword_hits": hits,
            "reviews": self.reviews_of(call_id),
        }

    def audio_path(self, r: CallResult) -> Path | None:
        for p in (r.audio_path, r.transcript.audio_path):
            if p and Path(p).is_file():
                return Path(p)
        return None

    # -- summary -------------------------------------------------------------------------------

    def summary(self, client: str) -> dict[str, Any]:
        s = self.settings(client)
        outs = self.outcomes(s)
        pol = outs.policy
        edges = [round(i / 20, 2) for i in range(21)]

        def bin_of(x: float) -> int:
            return min(19, max(0, int(float(x) * 20)))

        score_h = {lbl: [0] * 20 for lbl in LABELS}
        by_family: dict[str, dict[str, int]] = {}
        families = self.families()
        for o in outs.by_call.values():
            d = o.decision
            score_h[d.label][bin_of(d.score)] += 1
            top = be.top_family(d, self._can_alarm(families))
            if top is not None and d.label in FLAG:
                fam = fam_out(top.family) or ""
                by_family.setdefault(fam, {"alarm": 0, "review": 0})[d.label] += 1
        a_id, b_id = (pol.a.id, pol.b.id) if pol is not None else ("qwen", "kev")
        p_h = {a_id: [0] * 20, b_id: [0] * 20}
        answered = agree = unclear = 0
        for o in outs.by_call.values():
            if o.facts is None:
                continue
            for fam, fs in o.facts.family_scores.items():
                if fam == CROSS_FAMILY:
                    continue
                for e in ((fs.detail or {}).get("facts") or {}).values():
                    answered += 1
                    agree += bool(e.get("agree"))
                    unclear += e.get("value") == "unclear"
                    for rid in (a_id, b_id):
                        p = ((e.get("readers") or {}).get(rid) or {}).get("p")
                        if p:
                            p_h[rid][bin_of(p.get("yes", 0.0))] += 1
        labels = {cid: o.decision.label for cid, o in outs.by_call.items()}
        c = s.certainty
        return {"total": len(labels), "counts": self.counts(labels),
                "score_histogram": {"edges": edges, **score_h},
                "fact_p_yes_histogram": {"edges": edges, **p_h},
                "certainty": r4(c), "band": [r4(1 - c), r4(c)] if c is not None else None,
                "facts": {"answered": answered, "agree": agree, "unclear": unclear},
                "by_family": by_family, "threshold": r4(s.threshold), "elapsed_ms": outs.elapsed_ms}

    # -- meta / how it works -------------------------------------------------------------------------

    def _check_cfg(self, name: str) -> dict[str, Any]:
        return next((dict(c) for c in self.cfg.checks if c.get("name") == name), {})

    def _reader_specs(self) -> list[Any]:
        """The readers of the live fact policy; for a profile without one (Qwen-only fallback) the specs of
        config/fact_policy.yaml whose check this profile runs (display names only, nothing is decided with them)."""
        pol = self.live_policy()
        if pol is not None:
            return list(pol.readers)
        try:
            specs = list(fpol.load_fact_policy().readers)
        except Exception:
            return []
        names = {c.get("name") for c in self.cfg.checks}
        return [r for r in specs if r.check in names]

    def models(self) -> dict[str, Any]:
        """Model names as the stored results report them (``model_id``) plus a readable ``model``: the fact
        policy's display name when it names the same model, else :func:`pretty_model` of the stored id."""
        seen: dict[str, dict[str, int]] = {}
        asr: dict[str, int] = {}
        gsw: dict[str, int] = {}
        for r in self.results.values():
            for name, cr in r.checks.items():
                m = (cr.meta or {}).get("model")
                if m:
                    seen.setdefault(name, {}).setdefault(str(m), 0)
                    seen[name][str(m)] += 1
            if r.transcript.asr_backend:
                asr[r.transcript.asr_backend] = asr.get(r.transcript.asr_backend, 0) + 1
            g = (r.display_views or {}).get("gsw")
            if g is not None and g.asr_backend:
                k = g.asr_backend.split("->")[-1].strip()
                gsw[k] = gsw.get(k, 0) + 1

        def top(d: Mapping[str, int]) -> str | None:
            return max(d, key=d.get) if d else None

        readers = []
        specs = self._reader_specs()
        for spec in specs:
            raw = top(seen.get(spec.check, {}))
            c = self._check_cfg(spec.check)
            readers.append({"id": spec.id, "label": spec.label, "check": spec.check,
                            "model": display_model(raw, spec.model), "model_id": raw or spec.model or None,
                            "type": c.get("type"), "evidence": bool(c.get("evidence")),
                            "evidence_method": (c.get("evidence_method") or "mask") if c.get("type") == "kev_facts"
                            and c.get("evidence") else ("pointing" if c.get("evidence") else None),
                            **({"mask_segments": int(c.get("mask_segments") or 4)}
                               if c.get("type") == "kev_facts" and c.get("evidence") else {})})
        if not specs:
            for name, ms in seen.items():
                c = self._check_cfg(name)
                readers.append({"id": name, "label": name, "check": name, "model": display_model(top(ms), None),
                                "model_id": top(ms), "type": c.get("type"), "evidence": bool(c.get("evidence")),
                                "evidence_method": "pointing" if c.get("evidence") else None})
        a = top(asr)
        a = a.split(":", 1)[-1] if a else None
        g = top(gsw)
        return {"asr": a, "asr_label": pretty_model(a), "fact_readers": readers, "swiss_german_view": g,
                "swiss_german_view_label": pretty_model(g)}

    def code_version(self) -> str | None:
        import subprocess

        try:
            return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                                  timeout=2).stdout.strip() or None
        except Exception:
            return None

    def meta(self, client: str) -> dict[str, Any]:
        labels = self.labels_of(self.settings(client))
        doc = self.active_doc() if self.has_policy else {}
        fams = [{"id": f.id, "label": self.family_label(f.id), "label_de": f.label, "can_alarm": f.can_alarm,
                 "legal_basis": self.legal_basis(doc, f.id)} for f in self.families()]
        try:
            rel = str(self.runs_dir.relative_to(ROOT))
        except ValueError:
            rel = str(self.runs_dir)
        return {"app": APP_NAME, "api_version": API_VERSION, "profile": self.cfg.name, "runs_dir": rel,
                "code_version": self.code_version(), "models": self.models(),
                "counts": {"calls": len(labels), **self.counts(labels), "reviewed": len(self.reviewed_calls())},
                "families": fams, "has_fact_policy": self.has_policy, "load_errors": list(self.loaded.errors),
                "rulebook": self.rulebook_json()}

    def how_it_works(self) -> dict[str, Any]:
        """The pipeline as this profile runs it, built from the config and the stored results (models)."""
        m = self.models()
        readers = m["fact_readers"]
        pol = self.live_policy()
        diar = dict(self.cfg.diarizer or {})
        diar_model = pretty_model(str(diar.get("type") or "")) if diar.get("type") else None
        if diar_model and diar.get("provider"):
            diar_model += f", {str(diar['provider']).upper()}"
        roles_llm = None
        if diar.get("roles") == "llm":
            llm = diar.get("llm") or "default"
            roles_llm = next((r["model"] for r in readers if self._check_cfg(r["check"]).get("llm") == llm), None)
            if roles_llm is None:
                roles_llm = pretty_model(llm_model_id(self.cfg, llm)) or llm
        if roles_llm:
            roles_text = f"advisor or customer is decided by {roles_llm} from what each speaker says."
        elif diar.get("roles") == "first_speaker_advisor":
            roles_text = "the first speaker is taken as the advisor."
        else:
            roles_text = "no advisor / customer roles are assigned."

        def reader_text(r: dict[str, Any]) -> str:
            if r["type"] == "kev_facts" and r["evidence"]:
                k = r.get("mask_segments", 4)
                how = (f"gives p(yes) for each fact and finds the passages itself by masking: for each fact it says "
                       f"yes to, the window of {k} segments whose removal drops p(yes) most is the passage (the reason "
                       "states the drop, e.g. \u00abohne diese Stelle sinkt p(ja) von 0.91 auf 0.42\u00bb)."
                       if r["evidence_method"] == "mask" else
                       "gives p(yes) for each fact and marks for each fact the segment that shows it best.")
            elif r["evidence"]:
                how = ("answers each fact with p(yes / no / unclear) and points to the segments that show it, with a "
                       "short German reason: these are the passages the officer hears.")
            else:
                how = "answers each fact with p(yes); it cites no passages."
            return f"{r['label']} ({r['model'] or 'model unknown'}) {how}"

        rnames = " + ".join(f"{r['model'] or r['label']}" for r in readers) or None
        if len(readers) > 1:
            facts_title = "Two AI readers answer yes/no facts"
            facts_lead = "For every category the rule book asks small yes/no questions (facts). Both readers answer every fact: "
        else:
            facts_title = "An AI reader answers yes/no facts"
            facts_lead = "For every category the rule book asks small yes/no questions (facts). "
        facts_desc = facts_lead + " ".join(reader_text(r) for r in readers)
        if pol is not None:
            bands = "; ".join(f"{x.label}: yes at p(yes) \u2265 {x.hi:g}, no at \u2264 {x.lo:g}" if x.mode == "band"
                              else f"{x.label}: the most likely of yes / no / unclear" for x in pol.readers)
            comb = COMBINATION_EN.get(pol.combination, (pol.combination, ""))
            combine = {"id": "combine", "title": "Combine the readers", "model": None, "phase": "Decide",
                       "description": f"Each reader's answer becomes yes / no / unclear ({bands}; the certainty cutoff "
                                      f"c on the Calls page moves these bands). The two readers are combined per fact: "
                                      f"{comb[0].format(a=pol.a.label, b=pol.b.label)} \u2013 "
                                      f"{comb[1].format(a=pol.a.label, b=pol.b.label)}"}
        else:
            combine = None
        thr = float(self.defaults["threshold"])
        band = float(self.defaults["review_band"])
        steps = [
            {"id": "audio", "title": "Recording", "model": None, "phase": "Listen",
             "description": "Each bank phone call (Swiss German) is processed on the bank's own machines; nothing "
                            "is sent to a cloud service."},
            {"id": "asr", "title": "Speech to text", "model": m["asr_label"] or m["asr"], "phase": "Listen",
             "description": "A Whisper large-v3 model fine-tuned on Swiss German writes a Standard German transcript "
                            "with timestamps per segment." if m["asr"] and "large-v3" in m["asr"] else
                            "A Whisper model fine-tuned on Swiss German writes a Standard German transcript with "
                            "timestamps per segment."},
            {"id": "diarization", "title": "Who speaks", "model": " + ".join(x for x in (diar_model, roles_llm) if x)
             or None, "phase": "Listen",
             "description": f"Speaker separation splits the call into the two speakers' turns; {roles_text}"},
            {"id": "keywords", "title": "Keywords and patterns", "model": None, "phase": "Read",
             "description": "The keyword list (editable on the Keywords page) and number patterns mark candidate "
                            "passages. They are light cues: they add a little to the score, the facts and rules "
                            "decide."},
            {"id": "facts", "title": facts_title, "model": rnames, "phase": "Read", "description": facts_desc},
            *([combine] if combine else []),
            {"id": "rules", "title": "Rules decide", "model": None, "phase": "Decide",
             "description": "Per category, the first matching rule of the compliance rule book (policy table) turns "
                            "the facts into alarm, review or no alert. Rule edits on the Rules page apply at once, "
                            "are versioned and can be undone. New or changed fact questions take effect for a call "
                            "once the AI readers have answered them (next pipeline run)."},
            {"id": "fusion", "title": "Score and label", "model": None, "phase": "Decide",
             "description": f"Rule outcomes and the keyword / pattern cues become one call score: alarm at "
                            f"{thr:.2f} or more, review from {max(0.0, thr - band):.2f}, otherwise no alert. The "
                            "passages to listen to are the AI readers' passages (and keyword hits), with time, "
                            "category and reason."},
            *([{"id": "swiss_german", "title": "Swiss German view (display only)", "phase": "Display",
                "model": m["swiss_german_view_label"] or m["swiss_german_view"],
                "description": "After the decision, a separate step: a Swiss German dialect speech model "
                               "re-transcribes each segment from the recording so officers can read the dialect. "
                               "Display only; no check, rule or decision reads it."}]
              if m["swiss_german_view"] or self.cfg.display_views.get("gsw") else []),
            {"id": "review", "title": "Officer review", "model": None, "phase": "Person",
             "description": "The officer listens to the passages and confirms or corrects the result; every review "
                            "is stored with the officer's name and written to the audit log."},
        ]
        return {"steps": steps}

    # -- rules ---------------------------------------------------------------------------------

    def _require_policy(self) -> None:
        if not self.has_policy:
            raise bad("this profile has no editable rule book (fusion two_readers with rule: policy)")

    def rules(self, client: str, doc: dict[str, Any] | None = None) -> dict[str, Any]:
        self._require_policy()
        doc = self.active_doc() if doc is None else doc
        outs = self.outcomes(self.settings(client), doc)
        hits: dict[str, list[str]] = {}
        for cid, o in sorted(outs.by_call.items()):
            if o.facts is None:
                continue
            for fam, fs in o.facts.family_scores.items():
                rid = ((fs.detail or {}).get("rule") or {}).get("id")
                if rid:
                    hits.setdefault(rid, []).append(cid)
        families = self.families()

        def rj(rule: dict[str, Any], fam: str, i: int) -> dict[str, Any]:
            out = self.rule_json(rule, fam, doc)
            out.update(enabled=pe.is_enabled(rule), position=i, hits=len(hits.get(out["id"], [])),
                       hit_calls=hits.get(out["id"], []), basis=str(rule.get("basis") or "") or None)
            return out

        fams = []
        for fid, fd in (doc.get("families") or {}).items():
            fams.append({"id": fid, "label": self.family_label(fid, families),
                         "label_de": next((f.label for f in families if f.id == fid), fid),
                         "legal_basis": str((fd or {}).get("basis") or ""),
                         "facts": [{"id": str(f.get("id")), "label": self.fact_label(fid, str(f.get("id")),
                                                                                       str(f.get("label") or ""))}
                                   for f in (fd or {}).get("facts") or []],
                         "rules": [rj(r, fid, i) for i, r in enumerate((fd or {}).get("rules") or [])]})
        if self.demo_mode:
            version, can_undo = None, bool(self.demo_undo)
        else:
            store = self.store()
            act = store.active()
            version, can_undo = (act.n if act else None), store.last_rule_change() is not None
        return {"version": version, "can_undo": can_undo, "rulebook": self.rulebook_json(),
                "families": fams,
                "cross_rules": [rj(r, CROSS_FAMILY, i) for i, r in enumerate(doc.get("cross_rules") or [])]}

    def _draft_rule(self, body: Mapping[str, Any], doc: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
        """(candidate doc, family (CROSS_FAMILY for a cross rule), rule dict) of a wizard body."""
        facts = body.get("facts") or []
        if not facts:
            raise bad("a rule needs at least one fact")
        fams = {str(f.get("family")) for f in facts}
        known = {fid: {str(f.get("id")) for f in (fd or {}).get("facts") or []}
                 for fid, fd in (doc.get("families") or {}).items()}
        for f in facts:
            fam, fid = str(f.get("family")), str(f.get("fact"))
            if fid not in known.get(fam, set()):
                raise bad(f"unknown fact {fam}.{fid}")
            if str(f.get("value") or "yes") not in fpol.VALUES:
                raise bad("fact value must be yes, no or unclear")
        outcome = str(body.get("outcome") or "review")
        if outcome not in LABELS:
            raise bad("outcome must be alarm, review or no_alert")
        join = str(body.get("join") or "and")
        if join not in ("and", "or"):
            raise bad("join must be and or or")
        cross = len(fams) > 1
        conds = [((f"{f['family']}.{f['fact']}" if cross else str(f["fact"])), str(f.get("value") or "yes"),
                  bool(f.get("negate"))) for f in facts]
        cand = copy.deepcopy(doc)
        fam = CROSS_FAMILY if cross else next(iter(fams))
        # demo rules get their own ids (``trade.demo_alarm_1``), so a production rule's wording never labels them
        tag = "demo_" + outcome if self.demo_mode else outcome
        rid = pe.new_cross_rule_id(cand, tag) if cross else pe.new_rule_id(cand, fam, tag)
        rule = {"id": rid, "label": outcome, "when": build_when(conds, join),
                "text": str(body.get("description") or "").strip(), "title": str(body.get("title") or "").strip()}
        try:
            if cross:
                rep = fam_in(body.get("report_as"))
                if rep:
                    if rep not in known:
                        raise bad(f"report_as: unknown family {rep!r}")
                    rule["report_as"] = rep
                pe.add_cross_rule(cand, rule)
            else:
                pe.add_rule(cand, fam, rule, body.get("position"))
            pe.validate(cand)
        except PolicyTableError as e:
            raise bad(str(e)) from None
        return cand, fam, rule

    def preview_rule(self, client: str, body: Mapping[str, Any]) -> dict[str, Any]:
        self._require_policy()
        doc = self.active_doc()
        cand, fam, rule = self._draft_rule(body, doc)
        s = self.settings(client)
        before, after = self.labels_of(s), self.labels_of(s, cand)
        outs = self.outcomes(s, cand)
        hit = [cid for cid, o in sorted(outs.by_call.items()) if o.facts is not None and any(
            ((fs.detail or {}).get("rule") or {}).get("id") == rule["id"] for fs in o.facts.family_scores.values())]
        return {"rule": self.rule_json(rule, fam, cand), "hits": hit, "effect": self.effect(before, after)}

    def _apply(self, client: str, cand: dict[str, Any], author: str, comment: str) -> tuple[Any, dict[str, Any]]:
        s = self.settings(client)
        before = self.labels_of(s)
        if self.demo_mode:  # demo book: in memory only, no rule-book version, no audit entry
            try:
                pe.validate(cand)
            except PolicyTableError as e:
                raise bad(str(e)) from None
            with self.lock:
                self._set_demo_rules(cand)
            return _NoVersion(), self.effect(before, self.labels_of(s))
        names = {f.id: be.short_label(f.label) for f in self.families()}
        with self.lock:
            try:
                v = self.store().apply_rules(cand, author, comment=comment, family_names=names)
            except FourEyesError as e:
                raise conflict(str(e)) from None
            except PolicyTableError as e:
                raise bad(str(e)) from None
        return v, self.effect(before, self.labels_of(s))

    def create_rule(self, client: str, body: Mapping[str, Any], author: str) -> dict[str, Any]:
        self._require_policy()
        cand, fam, rule = self._draft_rule(body, self.active_doc())
        title = rule.get("title") or rule["id"]
        v, eff = self._apply(client, cand, author, f"New rule: {title}")
        return {"rule": self.rule_json(rule, fam, cand), "version": v.n, "effect": eff}

    def _find_rule(self, doc: dict[str, Any], rule_id: str) -> tuple[str, int]:
        for i, r in enumerate(doc.get("cross_rules") or []):
            if str(r.get("id")) == rule_id:
                return CROSS_FAMILY, i
        for fid, fd in (doc.get("families") or {}).items():
            for i, r in enumerate((fd or {}).get("rules") or []):
                if str(r.get("id")) == rule_id:
                    return fid, i
        raise missing(f"unknown rule {rule_id!r}")

    def patch_rule(self, client: str, rule_id: str, body: Mapping[str, Any], author: str) -> dict[str, Any]:
        self._require_policy()
        cand = self.active_doc()
        fam, i = self._find_rule(cand, rule_id)
        what = []
        if body.get("enabled") is not None:
            on = bool(body["enabled"])
            (pe.set_cross_enabled(cand, rule_id, on) if fam == CROSS_FAMILY else pe.set_enabled(cand, fam, rule_id, on))
            what.append("enabled" if on else "disabled")
        if body.get("move"):
            delta = int(body["move"])
            if fam == CROSS_FAMILY:
                rules = cand["cross_rules"]
                j = i + delta
                if not 0 <= j < len(rules):
                    raise bad("cannot move the rule further")
                rules[i], rules[j] = rules[j], rules[i]
            elif not pe.move_rule(cand, fam, rule_id, delta):
                raise bad("cannot move the rule further")
            what.append("moved up" if delta < 0 else "moved down")
        if not what:
            raise bad("nothing to change: give enabled and/or move")
        v, eff = self._apply(client, cand, author, f"Rule {rule_id} {' and '.join(what)}")
        fam2, j = self._find_rule(cand, rule_id)
        rule = (cand["cross_rules"][j] if fam2 == CROSS_FAMILY else cand["families"][fam2]["rules"][j])
        out = self.rule_json(rule, fam2, cand)
        out.update(enabled=pe.is_enabled(rule), position=j)
        return {"rule": out, "version": v.n, "effect": eff}

    def delete_rule(self, client: str, rule_id: str, author: str) -> dict[str, Any]:
        self._require_policy()
        cand = self.active_doc()
        fam, _ = self._find_rule(cand, rule_id)
        (pe.delete_cross_rule(cand, rule_id) if fam == CROSS_FAMILY else pe.delete_rule(cand, fam, rule_id))
        v, eff = self._apply(client, cand, author, f"Rule {rule_id} deleted")
        return {"deleted": rule_id, "version": v.n, "effect": eff}

    def undo_rules(self, client: str, author: str) -> dict[str, Any]:
        self._require_policy()
        s = self.settings(client)
        before = self.labels_of(s)
        if self.demo_mode:
            with self.lock:
                if not self.demo_undo:
                    raise conflict("There is no instant rule change to undo.")
                self.demo = self.demo_undo.pop()
            return {"version": None, "reverted": None, "effect": self.effect(before, self.labels_of(s))}
        names = {f.id: be.short_label(f.label) for f in self.families()}
        with self.lock:
            store = self.store()
            last = store.last_rule_change()
            try:
                v = store.undo_rules(author, names)
            except FourEyesError as e:
                raise conflict(str(e)) from None
        return {"version": v.n, "reverted": last.n if last else None, "effect": self.effect(before, self.labels_of(s))}

    # -- facts ---------------------------------------------------------------------------------

    def proposal_json(self, v: Any) -> dict[str, Any]:
        m = v.meta
        return {"id": v.n, "status": v.status, "author": v.author, "created": m.get("created"),
                "comment": m.get("comment") or "", "changes": list(m.get("diff") or []),
                "approver": m.get("approver"), "approved_at": m.get("approved_at"),
                "rejected_by": m.get("rejected_by"), "files": list(m.get("changed_files") or [])}

    def facts(self, client: str) -> dict[str, Any]:
        self._require_policy()
        doc = self.active_doc()
        s = self.settings(client)
        pol = self.policy_for(s)
        self.reload()
        fkey = (pol.key(), self.loaded.signature, stable_hash(self._families_key()), stable_hash(doc))
        hit = self.__dict__.get("_facts_memo")
        if hit is not None and hit[0] == fkey:
            fams = copy.deepcopy(hit[1])
        else:
            fams = self._fact_families(doc, pol)
            self._facts_memo = (fkey, copy.deepcopy(fams))
        return self._facts_tail(fams, pol)

    def _fact_families(self, doc: dict[str, Any], pol: Any) -> list[dict[str, Any]]:
        answers = fpol.fact_answers(self.results, pol)
        families = self.families()
        fams = []
        for fid, fd in (doc.get("families") or {}).items():
            used: dict[str, int] = {}
            for r in (fd or {}).get("rules") or []:
                try:
                    from callguard.checks.facts import rule_facts

                    for q in rule_facts(parse_rule(str(r.get("when") or "true"))):
                        used[q] = used.get(q, 0) + 1
                except PolicyTableError:
                    pass
            for r in doc.get("cross_rules") or []:
                try:
                    from callguard.checks.facts import rule_facts

                    for q in rule_facts(parse_rule(str(r.get("when") or "true"))):
                        if q.startswith(f"{fid}."):
                            used[q.split(".", 1)[1]] = used.get(q.split(".", 1)[1], 0) + 1
                except PolicyTableError:
                    pass
            facts = []
            for f in (fd or {}).get("facts") or []:
                fact_id = str(f.get("id"))
                ans = answers.get((fid, fact_id)) or []
                cnt = fpol.value_counts(ans, pol, fid, fact_id)["combined"] if ans else {}
                ag = sum(1 for x in ans if fpol.resolve_fact(pol, fid, fact_id, x.pa, x.pb).agree)
                facts.append({"id": fact_id, "label": self.fact_label(fid, fact_id, str(f.get("label") or "")),
                              "label_de": str(f.get("label") or ""), "role": f.get("role"),
                              "question": str(f.get("en") or f.get("de") or ""), "question_de": str(f.get("de") or ""),
                              "used_in_rules": used.get(fact_id, 0),
                              "answers": {"calls": len(ans), "yes": cnt.get("yes", 0), "no": cnt.get("no", 0),
                                          "unclear": cnt.get("unclear", 0), "agree": ag}})
            fams.append({"id": fid, "label": self.family_label(fid, families),
                         "label_de": next((x.label for x in families if x.id == fid), fid), "facts": facts})
        return fams

    def _facts_tail(self, fams: list[dict[str, Any]], pol: Any) -> dict[str, Any]:
        models = {r["check"]: r["model"] for r in self.models()["fact_readers"]}
        readers = [{"id": r.id, "label": r.label, "model": models.get(r.check) or r.model, "mode": r.mode,
                    **({"band": [r4(r.lo), r4(r.hi)]} if r.mode == "band" else {})} for r in pol.readers]
        store = self.store()
        act = store.active()
        props = [self.proposal_json(v) for v in store.versions() if not v.meta.get("instant")]
        return {"families": fams, "readers": readers, "combination": pol.combination,
                "active_version": act.n if act else None,
                "proposals": [p for p in props if p["status"] == "draft"] + [p for p in props if p["status"] != "draft"][-10:]}

    def propose_fact(self, body: Mapping[str, Any], author: str) -> dict[str, Any]:
        self._require_policy()
        fam = str(body.get("family") or "")
        doc = self.live_doc()
        if fam not in (doc.get("families") or {}):
            raise bad(f"unknown family {fam!r}")
        cand = copy.deepcopy(doc)
        fid = body.get("fact_id")
        try:
            if body.get("delete"):
                if not fid:
                    raise bad("fact_id is required to delete a fact")
                pe.delete_fact(cand, fam, str(fid))
                comment = str(body.get("comment") or f"Remove fact {fam}.{fid}")
            else:
                label = str(body.get("label") or "").strip()
                q_en = " ".join(str(body.get("question") or "").split())
                q_de = " ".join(str(body.get("question_de") or "").split())
                if not label or not (q_en or q_de):
                    raise bad("label and question are required")
                fid = str(fid) if fid else pe.new_fact_id(cand, fam, label)
                old = next((f for f in pe.family_doc(cand, fam)["facts"] if str(f.get("id")) == fid), None)
                if body.get("fact_id") and old is None:
                    raise missing(f"unknown fact {fam}.{fid}")
                pe.upsert_fact(cand, fam, {"id": fid, "label": label, "role": str(body.get("role") or "context"),
                                           "de": q_de or (old or {}).get("de") or q_en, "en": q_en or (old or {}).get("en", ""),
                                           "description": str(body.get("description") or "")})
                comment = str(body.get("comment") or f"{'Change' if old else 'New'} fact {fam}.{fid}: {label}")
            names = {f.id: be.short_label(f.label) for f in self.families()}
            with self.lock:
                v = self.store().save_draft({"policy_table": cand}, author, comment=comment[:300], family_names=names,
                                            profile=self.cfg.name)
        except FourEyesError as e:
            raise bad(str(e)) from None
        except (PolicyTableError, KeyError) as e:
            raise bad(str(e)) from None
        return {"proposal": self.proposal_json(v)}

    def _version(self, store: VersionStore, n: int) -> Any:
        try:
            return store.get(n)
        except Exception:
            raise missing(f"unknown proposal {n}") from None

    def approve(self, n: int, approver: str, note: str = "") -> dict[str, Any]:
        self._require_policy()
        with self.lock:
            store = self.store()
            self._version(store, n)
            try:
                v = store.approve(n, approver, note)
            except FourEyesError as e:
                raise conflict(str(e)) from None
            act = store.active()
        return {"proposal": self.proposal_json(v), "active_version": act.n if act else None,
                "note": "New or changed questions take effect for calls once the AI readers answer them again "
                        "(next pipeline run); stored calls keep their stored answers."}

    def reject(self, n: int, user: str, note: str = "") -> dict[str, Any]:
        self._require_policy()
        with self.lock:
            store = self.store()
            self._version(store, n)
            try:
                v = store.reject(n, user, note)
            except FourEyesError as e:
                raise conflict(str(e)) from None
        return {"proposal": self.proposal_json(v)}

    # -- keywords --------------------------------------------------------------------------------

    def keyword_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.results.values():
            for cr in r.checks.values():
                if cr.type != "keywords":
                    continue
                for f in cr.findings:
                    k = (f.detail or {}).get("keyword_id")
                    if k and not (f.detail or {}).get("negated"):
                        out[k] = out.get(k, 0) + 1
        return out

    @staticmethod
    def keyword_json(k: Any, hits: Mapping[str, int]) -> dict[str, Any]:
        return {"id": k.id, "label": k.label, "enabled": k.enabled, "case_sensitive": k.case_sensitive,
                "de": list(k.de), "gsw": list(k.gsw), "en": list(k.en), "harmless": harmless_list(k.harmless),
                "hits": hits.get(k.id, 0)}

    def keywords(self) -> dict[str, Any]:
        hits = self.keyword_counts()
        return {"families": [{"id": f.id, "label": self.family_label(f.id), "label_de": f.label,
                              "keywords": [self.keyword_json(k, hits) for k in f.keywords]}
                             for f in self.families()]}

    def _keywords_of(self, body: Mapping[str, Any]) -> tuple[str, list[Any]]:
        fam = str(body.get("family") or "")
        if fam not in {f.id for f in self.families()}:
            raise bad(f"unknown family {fam!r}")
        rows = []
        for k in body.get("keywords") or []:
            rows.append({"id": k.get("id"), "label": k.get("label"), "enabled": k.get("enabled", True),
                         "case_sensitive": k.get("case_sensitive", False),
                         "de": ", ".join(k.get("de") or []), "gsw": ", ".join(k.get("gsw") or []),
                         "en": ", ".join(k.get("en") or []), "harmless": harmless_text(k.get("harmless"))})
        kws, _warn = be.rows_to_keywords(rows, be.all_keyword_ids(self.cfg.paths.resolve("keywords")))
        return fam, kws

    def keyword_preview(self, client: str, body: Mapping[str, Any]) -> dict[str, Any]:
        from callguard.demo import keywords as kwe

        fam, kws = self._keywords_of(body)
        s = self.settings(client)
        families = self.families()
        ov = {**self.overrides(s)}
        pol = self.policy_for(s)
        if pol is not None:
            ov["fact_policy"] = pol.as_dict()
        decided = {cid: be.Decided(o.decision, self.results[cid].decision) for cid, o in self.outcomes(s).by_call.items()}
        if self.demo_mode:  # the engine's fusion would decide with the live table: use the demo book instead
            eff = self._keyword_effect_doc(s, families, fam, kws)
        else:
            eff = kwe.keyword_effect(self.engine, self.results, decided, families, None, ov, fam, kws)
        if eff is None:
            raise bad("this profile has no keyword check")
        before = {c[0]: c[1] for c in eff.changed}
        after = {c[0]: c[2] for c in eff.changed}
        out = self.effect(before, after)
        out["summary"] = out["summary"].replace(f"of {len(after)} calls", f"of {len(self.results)} calls").replace(
            f"none of the {len(after)} calls", f"none of the {len(self.results)} calls")
        per = self._edited_keyword_hits(fam, kws)
        return {"effect": out, "hits": {"before": eff.family_hits_before, "after": eff.family_hits_after,
                                        "per_keyword": per},
                "keywords": [self.keyword_json(k, per) for k in kws]}

    def _keyword_effect_doc(self, s: ClientSettings, families: list[Family], fam: str, kws: list[Any]) -> Any:
        """keyword_effect under the ACTIVE rule book (demo mode): each call's combined checks as :meth:`outcomes`
        builds them, with the edited family's keyword findings swapped in, through the same fusion."""
        from callguard.demo import keywords as kwe

        check = self.keyword_check()
        if check is None:
            return None
        new_fams = kwe.with_keywords(families, fam, kws)
        edited = next((f for f in new_fams if f.id == fam), None)
        pol = self.policy_for(s)
        ov = self.overrides(s)
        doc = self.active_doc()
        combined = self.combined(pol, doc, families)
        outs = self.outcomes(s, doc)
        eff = kwe.KeywordEffect(0, 0, 0, 0, {lbl: 0 for lbl in LABELS}, {lbl: 0 for lbl in LABELS})
        for cid, r in self.results.items():
            before = outs.by_call[cid].decision.label
            after = before
            checks = combined.get(cid)
            base = r.checks.get(check.name)
            hb = ha = fb_ = fa = 0
            if base is not None and edited is not None and not isinstance(checks, Exception) and checks is not None:
                try:
                    part = check.run(be.check_view_transcript(self.engine.pipeline, check, r), [edited])
                    new = kwe.merge_family(base, part, fam)
                    d = self.fusion.decide_checks(r.transcript, {**checks, check.name: new}, new_fams, ov,
                                                  r.views or None)
                    after = d.label

                    def count(cr: CheckResult, only: str | None = None) -> int:
                        return sum(1 for f in cr.findings if not (f.detail or {}).get("negated")
                                   and (only is None or f.family == only))

                    hb, ha, fb_, fa = count(base), count(new), count(base, fam), count(new, fam)
                except Exception as e:
                    log.warning("API: keyword preview of %s failed: %s", cid, e)
            eff.hits_before += hb
            eff.hits_after += ha
            eff.family_hits_before += fb_
            eff.family_hits_after += fa
            eff.calls_before += hb > 0
            eff.calls_after += ha > 0
            eff.labels_before[before] += 1
            eff.labels_after[after] += 1
            if after != before:
                eff.changed.append((cid, before, after))
        eff.changed.sort()
        return eff

    def _edited_keyword_hits(self, fam: str, kws: list[Any]) -> dict[str, int]:
        """Hits per keyword id of the edited family over all stored transcripts (as the Hits column counts)."""
        from callguard.demo import keywords as kwe

        check = self.keyword_check()
        if check is None:
            return {}
        edited = next((f for f in kwe.with_keywords(self.families(), fam, kws) if f.id == fam), None)
        if edited is None:
            return {}
        out: dict[str, int] = {}
        for r in self.loaded.results.values():
            if check.name not in r.checks:
                continue
            try:
                cr = check.run(be.check_view_transcript(self.engine.pipeline, check, r), [edited])
            except Exception:
                continue
            for f in cr.findings:
                k = (f.detail or {}).get("keyword_id")
                if k and not (f.detail or {}).get("negated"):
                    out[k] = out.get(k, 0) + 1
        return out

    def save_keywords(self, client: str, body: Mapping[str, Any], author: str) -> dict[str, Any]:
        """Writes the keyword list. The keyword check is then re-run on every stored transcript (see
        :attr:`results`), so hits, highlights and decisions change at once; the effect returned is the real one
        (labels before vs after the save, at the caller's settings)."""
        prev = self.keyword_preview(client, body)
        fam, kws = self._keywords_of(body)
        kw_path = self.cfg.paths.resolve("keywords")
        s = self.settings(client)
        before = self.labels_of(s)
        with self.lock:
            be.backup_file(kw_path, self.runs_dir / "backups")
            be.save_family_keywords(kw_path, self.cfg.paths.resolve("criteria"), fam, kws)
        after = self.labels_of(s)
        eff = self.effect(before, after)
        hits = self.keyword_counts()
        saved = next((f for f in self.families() if f.id == fam), None)
        audit.log_event(self.runs_dir, "keywords_saved", user=author, family=fam, via="api",
                        keywords=[k.id for k in kws], effect=eff["summary"])
        return {"effect": eff, "hits": {**prev["hits"], "per_keyword": {k.id: hits.get(k.id, 0) for k in
                                                                         (saved.keywords if saved else [])}},
                "keywords": [self.keyword_json(k, hits) for k in (saved.keywords if saved else kws)],
                "saved": True, "applied": "now: hits and decisions of all stored calls were recomputed"}

    # -- review ----------------------------------------------------------------------------------

    def reviews_of(self, call_id: str) -> list[dict[str, Any]]:
        try:
            items = [i for i in fb.load(self.runs_dir) if i.call_id == call_id]
        except Exception:
            return []
        out: dict[str, dict[str, Any]] = {}
        for i in items:
            key = i.batch or f"{i.ts}|{i.verdict}"
            e = out.setdefault(key, {"id": key, "ts": i.ts, "reviewer": i.user, "verdict": None, "agree": None,
                                     "comment": "", "reasons": [], "label_seen": None, "items": 0})
            e["items"] += 1
            if i.target == "call":
                e.update(verdict=i.verdict, agree=i.agrees, comment=i.comment, label_seen=i.label_seen,
                         reasons=[r.code for r in i.reasons])
        return sorted(out.values(), key=lambda e: e["ts"])

    def review(self, client: str, call_id: str, body: Mapping[str, Any], reviewer: str) -> dict[str, Any]:
        r = self.result(call_id)
        verdict = body.get("verdict")
        if verdict not in fb.CALL_VERDICTS:
            raise bad(f"verdict must be one of {', '.join(fb.CALL_VERDICTS)}")
        s = self.settings(client)
        o = self.outcomes(s).by_call[call_id]
        live = r.model_copy(update={"decision": o.decision})
        facts = self.facts_json(o, self.policy_for(s))
        reasons: list[dict[str, Any]] = []
        for code in body.get("reasons") or []:
            if isinstance(code, Mapping):
                reasons.append(dict(code))
            elif code in REVIEW_REASONS:
                reasons.append({"code": code})
            else:
                raise bad(f"unknown reason {code!r}; known: {', '.join(REVIEW_REASONS)}")
        for key, val in (body.get("fact_corrections") or {}).items():
            if "." not in str(key) or val not in fb.FACT_ANSWERS:
                raise bad("fact_corrections: keys family.fact, values yes / no / unclear")
            fam, fid = str(key).split(".", 1)
            before = next((x["resolved"] for x in facts.get(fam, []) if x["id"] == fid), None)
            if before is None:
                raise bad(f"fact_corrections: unknown fact {key}")
            reasons.append({"code": "fact_wrong", "family": fam, "fact": fid, "before": before, "after": val})
        n_pass = len(o.decision.passages)
        for idx, ok in (body.get("passage_ok") or {}).items():
            try:
                i = int(idx)
            except ValueError:
                raise bad("passage_ok: keys are passage indexes") from None
            if not 0 <= i < n_pass:
                raise bad(f"passage_ok: no passage {i}")
            reasons.append({"code": "passage_applies" if ok else "passage_not_applies", "passage_index": i,
                            "family": o.decision.passages[i].family})
        try:
            items = fb.items_from_review(live, user=reviewer, verdict=verdict,
                                         agrees=None if body.get("agree") is None else bool(body["agree"]),
                                         reasons=reasons, comment=str(body.get("comment") or ""),
                                         threshold=s.threshold)
        except ValueError as e:
            raise bad(str(e)) from None
        with self.lock:
            saved = fb.add_many(self.runs_dir, items)
            audit.log_event(self.runs_dir, "review", user=reviewer, call_id=call_id, verdict=verdict, via="api",
                            label_seen=o.decision.label, batch=saved[0].batch if saved else None,
                            agree=body.get("agree"), reasons=[x["code"] for x in reasons])
        all_items = fb.load(self.runs_dir)
        counts: dict[str, int] = {}
        for i in all_items:
            counts[i.target] = counts.get(i.target, 0) + 1
        return {"id": saved[0].batch if saved else None, "items": len(saved), "label_seen": o.decision.label,
                "data_points": fb.batch_count(all_items), "counts": counts}
