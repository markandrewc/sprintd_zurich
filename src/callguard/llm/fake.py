"""Deterministic offline stand-in for an LLM: a cue-word heuristic instead of a model.

Lets tests, caching, fusion and the UI run without a server, GPU or network (``llms.default.type:
fake``). It is a plumbing double, not a classifier. The rules, so tests can rely on them:

* The transcript is read from rendered lines ``[S007 01:23 advisor] text`` (``Transcript.render``)
  in the last user message (else in any message); without such lines the whole last user message
  is searched. A cue from ``CUES`` in a line marks that line for the cue's family. Cues match as
  whole words, short upper-case ones (``TAN``, ``PIN``) case-sensitively.
* Family scope: a JSON property named after a family id (``{"trade": {...}}``), an array item whose
  ``family`` enum value is the id, a prompt tagging exactly one family as ``[id]``, or a prompt naming
  exactly one family (id or label, outside the transcript lines) only counts that family's cues.
  Otherwise any cue counts.
* JSON: verdict-like enums -> ``present``/``absent`` (also yes/no, alarm/no_alert); advisor/speaker/
  role enums -> first value; ``confidence`` -> 0.8; other numbers -> 0.8 / 0.2 scaled into
  minimum..maximum (integer scales: 4 / 1 on 1..5); segment-id arrays -> ids of cue lines; strings
  -> a German reason naming the cue; booleans -> cue found, mitigating flags (negated, quoted,
  expired, public...) -> False.
* Plain text: a fixed numbered list if the prompt ends asking for numbered steps (G-Eval step
  generation), a digit if it ends asking for a score (``4`` / ``1`` on 1..5), else a short German
  sentence. ``choice_probs``: 0.7 on that answer, the rest spread evenly.
* ``n > 1`` with ``temperature > 0``: sample 0 is canonical, later samples jitter float fields by
  up to 0.05 (seeded), verdicts never change.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from callguard.llm.jsonutil import deref_schema, schema_types
from callguard.plugins import LLM

if TYPE_CHECKING:
    from callguard.context import Context

CUES: dict[str, tuple[str, ...]] = {
    "trade": ("vor der Meldung", "vor der Bekanntgabe", "nicht öffentlich", "noch nicht publiziert",
              "noch nicht veröffentlicht", "unter uns"),
    "access": ("TAN", "PIN", "Bestätigungscode", "Passwort"),
    "disclosure": ("ohne Vollmacht",),
    "documentation": ("nicht protokollieren", "nicht in die Notiz"),
    "splitting": ("aufteilen", "Kontrolle umgehen"),
}

# Words that name a family in a prompt (besides its id); labels from ctx.families() are added.
FAMILY_NAMES: dict[str, tuple[str, ...]] = {
    "trade": ("Insiderhandel", "Kaufwunsch"),
    "access": ("Zugangsinformation", "Zugangsgeheimnis"),
    "disclosure": ("Auskunft an Dritte",),
    "documentation": ("Angabe verschweigen", "Angabe auslassen"),
    "splitting": ("Zuständigkeit", "Kontrolle umgehen (Aufteilen)"),
    "numbers": ("Zahlenobjekte",),
}

_LINE = re.compile(r"^[ \t]*\[(?P<id>[A-Z]+\d+)(?P<tags>[^\]\n]*)\][ \t]?(?P<text>.*)$", re.M)
_TIME = re.compile(r"^\d+:\d\d$")
_RANGE = re.compile(r"(?<!\d)(\d{1,3})\s*(?:-|–|bis|to)\s*(\d{1,3})(?!\d)")
_STEPS_ASK = re.compile(r"\bnumbered (?:evaluation )?(?:steps|list)\b", re.I)
FAKE_STEPS = ("1. Read the policy and what makes the misconduct harmless.\n"
              "2. Find the transcript lines that match the policy.\n"
              "3. Rate how clearly the misconduct is present.")
_SCORE_ASK = re.compile(r"\b(score|punktzahl|punkte|bewerte\w*|rating|skala|ziffer|digit|zahl)\b", re.I)
_POS = {"present", "yes", "ja", "true", "alarm", "suspicious", "verdächtig", "violation", "verstoss", "high", "hoch"}
_NEG = {"absent", "no", "nein", "false", "no_alert", "none", "harmless", "unbedenklich", "unauffällig", "low",
        "niedrig", "ok", "clean"}
_MITIGATING = ("negat", "verneint", "zitiert", "quot", "refus", "verweiger", "expired", "abgelaufen", "public",
               "öffentlich", "harmless", "harmlos", "hypothet", "example", "beispiel", "unclear", "unklar")
_ROLE_WORDS = ("advisor", "speaker", "role", "berater", "sprecher")


def _norm(s: str) -> str:
    return re.sub(r"[\s-]+", "_", s.strip().casefold())


def _cue_pattern(cue: str) -> re.Pattern[str]:
    flags = 0 if cue.isupper() and len(cue) <= 4 else re.IGNORECASE
    return re.compile(r"(?<!\w)" + re.escape(cue).replace(r"\ ", r"\s+") + r"(?!\w)", flags)


def _pick_numeric(values: list[Any], flag: bool) -> Any:
    vals = sorted(values)
    return vals[round(0.75 * (len(vals) - 1))] if flag else vals[0]


@dataclass
class _Hit:
    family: str
    cue: str
    seg: str  # "" when the prompt carries no rendered transcript lines
    text: str


@dataclass
class _Scene:
    """What the fake 'understood' from one prompt."""

    hits: list[_Hit] = field(default_factory=list)
    scope: str | None = None
    named: list[str] = field(default_factory=list)
    seg_ids: list[str] = field(default_factory=list)
    speakers: list[str] = field(default_factory=list)
    instructions: str = ""  # the prompt without transcript lines

    def hits_for(self, fam: str | None) -> list[_Hit]:
        fam = fam or self.scope
        return [h for h in self.hits if fam is None or h.family == fam]

    def flag(self, fam: str | None) -> bool:
        return bool(self.hits_for(fam))


class FakeLLM(LLM):
    """``backend_params`` swallows the server keys a profile inherits (``base_url``, ``model``,
    ``json_mode``...), so ``--set llms.default.type=fake`` works on any profile. They change
    nothing and stay out of ``cache_params``."""

    version = "fake-v3"  # v3: answers G-Eval step prompts with a numbered list. Bump when the heuristic changes, so cached check results are recomputed

    def __init__(self, ctx: "Context | None" = None, seed: int = 0,
                 cues: dict[str, list[str]] | None = None, **backend_params: Any):
        super().__init__(ctx, seed=seed, cues=cues)
        self.ignored_params = backend_params
        self.seed = int(seed)
        self.cues = {f: tuple(c) for f, c in (cues if cues is not None else CUES).items()}
        self._patterns = [(f, c, _cue_pattern(c)) for f, cs in self.cues.items() for c in cs]
        self._names: dict[str, tuple[str, ...]] | None = None
        self.calls: deque[dict[str, Any]] = deque(maxlen=200)  # for tests: what was asked

    @property
    def model_id(self) -> str:
        return f"{self.version}-s{self.seed}"

    def cache_params(self) -> dict[str, Any]:
        return {"type": self.plugin_type, "model": self.model_id, "cues": self.params.get("cues")}

    # -- public API ---------------------------------------------------------------------------

    def chat(self, messages: list[dict[str, str]], *, temperature: float = 0.0, max_tokens: int = 512,
             n: int = 1, json_schema: dict | None = None, stop: list[str] | None = None) -> list[str]:
        scene = self._scene(messages)
        self.calls.append({"kind": "chat", "messages": messages, "json_schema": json_schema, "n": n,
                           "temperature": temperature})
        digest = hashlib.sha256(json.dumps(messages, sort_keys=True, default=str).encode()).hexdigest()[:16]
        outs = []
        for i in range(max(1, int(n))):
            jitter = random.Random(f"{self.seed}:{i}:{digest}") if i and temperature > 0 else None
            if json_schema:
                text = json.dumps(_Builder(json_schema, scene, set(self._family_names()), jitter).value(json_schema),
                                  ensure_ascii=False)
            else:
                text = self._text(scene)
            for s in stop or []:
                if s and s in text:
                    text = text[:text.index(s)]
            outs.append(text)
        return outs

    def choice_probs(self, messages: list[dict[str, str]], choices: list[str]) -> dict[str, float] | None:
        if not choices:
            return None
        scene = self._scene(messages)
        self.calls.append({"kind": "choice_probs", "messages": messages, "choices": list(choices)})
        flag = scene.flag(None)
        try:
            nums = [float(c) for c in choices]
            target = nums.index(_pick_numeric(nums, flag))
        except ValueError:
            want = _POS if flag else _NEG
            target = next((i for i, c in enumerate(choices) if _norm(c) in want), 0)
        if len(choices) == 1:
            return {choices[0]: 1.0}
        rest = 0.3 / (len(choices) - 1)
        return {c: (0.7 if i == target else rest) for i, c in enumerate(choices)}

    # -- prompt reading -----------------------------------------------------------------------

    def _family_names(self) -> dict[str, tuple[str, ...]]:
        if self._names is None:
            names = {f: (f, *FAMILY_NAMES.get(f, ())) for f in [*self.cues, *FAMILY_NAMES]}
            families = getattr(self.ctx, "families", None)
            if callable(families):
                try:
                    for fam in families():
                        names[fam.id] = (*names.get(fam.id, (fam.id,)), fam.label)
                except Exception:  # broken criteria file must not break a test double
                    pass
            self._names = names
        return self._names

    def _scene(self, messages: list[dict[str, str]]) -> _Scene:
        texts = [(m.get("role", ""), m["content"]) for m in messages if isinstance(m.get("content"), str)]
        user = next((t for r, t in reversed(texts) if r == "user"), texts[-1][1] if texts else "")
        source = user if _LINE.search(user) else next((t for _, t in reversed(texts) if _LINE.search(t)), "")
        scene = _Scene()
        if source:
            for m in _LINE.finditer(source):
                seg, line = m.group("id"), m.group("text").strip()
                scene.seg_ids.append(seg)
                for tag in m.group("tags").split():
                    if not _TIME.match(tag) and tag not in scene.speakers:
                        scene.speakers.append(tag)
                scene.hits += [_Hit(f, c, seg, line) for f, c in self._find_cues(line)]
        else:
            scene.hits = [_Hit(f, c, "", user.strip()[:200]) for f, c in self._find_cues(user)]
        outside = [t for r, t in texts if r == "system"] + [_LINE.sub("", user)]
        scene.instructions = "\n".join(outside)
        # An explicit family id beats label words: a prompt may list every family's label but
        # still be about one id.
        by_id, by_label = [], []
        folded = scene.instructions.casefold()
        for f, (fid, *labels) in self._family_names().items():
            if re.search(rf"(?<![\w-]){re.escape(fid)}(?![\w-])", scene.instructions):
                by_id.append(f)
            elif any(w.casefold() in folded for w in labels):
                by_label.append(f)
        scene.named = by_id + by_label
        # "[trade]" tags the family a prompt is about; a bare id can also be an ordinary English word
        # ("numbers") in the instructions, so a unique tag wins over word matches
        tagged = [f for f in by_id if f"[{f}]" in scene.instructions]
        scene.scope = (tagged[0] if len(tagged) == 1 else by_id[0] if len(by_id) == 1
                       else by_label[0] if not by_id and len(by_label) == 1 else None)
        return scene

    def _find_cues(self, text: str) -> list[tuple[str, str]]:
        return [(f, c) for f, c, pat in self._patterns if pat.search(text)]

    def _text(self, scene: _Scene) -> str:
        tail = scene.instructions.rstrip()[-300:]
        if _STEPS_ASK.search(tail):
            return FAKE_STEPS
        rng = _RANGE.search(tail)
        if rng or _SCORE_ASK.search(tail):
            lo, hi = (int(rng.group(1)), int(rng.group(2))) if rng else (1, 5)
            if not lo < hi <= lo + 100:
                lo, hi = 1, 5
            return str(_pick_numeric(list(range(lo, hi + 1)), scene.flag(None)))
        hits = scene.hits_for(None)
        return _reason(hits[0] if hits else None)


def _reason(hit: _Hit | None) -> str:
    if hit is None:
        return "Keine verdächtigen Hinweise im Gespräch gefunden."
    where = f"in [{hit.seg}]" if hit.seg else "im Text"
    return f"Verdächtige Formulierung «{hit.cue}» {where}: {hit.text[:120]}"


class _Builder:
    """Walks a JSON schema and fills it from the scene."""

    def __init__(self, root: dict, scene: _Scene, families: set[str], jitter: random.Random | None):
        self.root, self.scene, self.families, self.jitter = root, scene, families, jitter

    def value(self, sch: Any, name: str = "", fam: str | None = None, hit: _Hit | None = None) -> Any:
        sch = deref_schema(sch, self.root)
        if "const" in sch:
            return sch["const"]
        if sch.get("enum"):
            return self.enum(list(sch["enum"]), name, fam)
        for key in ("anyOf", "oneOf"):
            opts = sch.get(key)
            if isinstance(opts, list) and opts:
                real = [o for o in opts if deref_schema(o, self.root).get("type") != "null"]
                return self.value((real or opts)[0], name, fam, hit)
        t = next((x for x in schema_types(sch) if x != "null"), "string")
        if t == "object":
            return self.obj(sch, fam, hit)
        if t == "array":
            return self.array(sch, name, fam)
        if t in ("number", "integer"):
            return self.number(sch, name, fam, t == "integer")
        if t == "boolean":
            low = name.lower()
            if any(w in low for w in _MITIGATING) and not low.startswith(("non", "not_", "nicht")):
                return False
            return self.scene.flag(fam)
        if t == "null":
            return None
        return self.string(sch, name, fam, hit)

    def obj(self, sch: dict, fam: str | None, hit: _Hit | None) -> dict[str, Any]:
        props = sch.get("properties") or {}
        out = {k: self.value(sub, k, k if k in self.families else fam, hit) for k, sub in props.items()}
        extra = sch.get("additionalProperties")
        if not props and isinstance(extra, dict):  # dict keyed by family id
            for f in self.scene.named:
                out[f] = self.value(extra, f, f)
        return out

    def array(self, sch: dict, name: str, fam: str | None) -> list[Any]:
        items = deref_schema(sch.get("items") or {}, self.root)
        item_type = next((x for x in schema_types(items) if x != "null"), "string")
        props = items.get("properties") or {}
        fam_key = next((k for k in ("family", "family_id", "familie") if k in props), None)
        hits = self.scene.hits_for(fam)
        low = name.lower()
        out: list[Any]
        if fam_key:  # one entry per family
            enum = deref_schema(props[fam_key], self.root).get("enum") or self.scene.named
            out = [{**self.obj(items, f, None), fam_key: f} for f in enum]
        elif item_type == "object":
            out = [self.value(items, name, fam, h) for h in hits[:3]]
        elif item_type == "string" and any(w in low for w in ("segment", "ids", "line", "turn", "evidence")):
            out = list(dict.fromkeys(h.seg for h in hits if h.seg))
        elif item_type == "string":
            out = list(dict.fromkeys(h.cue for h in hits))
        else:
            out = []
        while len(out) < int(sch.get("minItems", 0)):
            out.append(self.value(items, name, fam))
        return out[:int(sch["maxItems"])] if "maxItems" in sch else out

    def enum(self, values: list[Any], name: str, fam: str | None) -> Any:
        low = name.lower()
        if low in ("family", "family_id", "familie") and fam in values:
            return fam
        if any(w in low for w in _ROLE_WORDS):
            return values[0]
        flag = self.scene.flag(fam)
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            return _pick_numeric(values, flag)
        want = _POS if flag else _NEG
        return next((v for v in values if isinstance(v, str) and _norm(v) in want), values[0])

    def number(self, sch: dict, name: str, fam: str | None, integer: bool) -> int | float:
        low = name.lower()
        confidence = "conf" in low or "sicher" in low
        frac = 0.8 if confidence or self.scene.flag(fam) else 0.2
        lo = sch.get("minimum", sch.get("exclusiveMinimum"))
        hi = sch.get("maximum", sch.get("exclusiveMaximum"))
        if integer and not confidence:
            if lo is None or hi is None or not 0 < hi - lo <= 100:
                lo, hi = (lo, lo + 4) if lo is not None else ((hi - 4, hi) if hi is not None else (1, 5))
            return _pick_numeric(list(range(int(lo), int(hi) + 1)), frac > 0.5)
        lo_f = float(lo) if lo is not None else 0.0
        hi_f = float(hi) if hi is not None else max(lo_f + 1.0, 1.0)
        v = lo_f + frac * (hi_f - lo_f)
        if self.jitter is not None:
            v += self.jitter.uniform(-0.05, 0.05) * (hi_f - lo_f)
        v = min(hi_f, max(lo_f, v))
        return int(round(v)) if integer else round(v, 3)

    def string(self, sch: dict, name: str, fam: str | None, hit: _Hit | None) -> str:
        low = name.lower()
        hits = self.scene.hits_for(fam)
        h = hit or (hits[0] if hits else None)
        if low in ("family", "family_id", "familie"):
            out = fam or self.scene.scope or ""
        elif "segment" in low or low in ("id", "seg_id", "turn_id", "line_id", "turn", "line"):
            out = h.seg if h else ""
        elif any(w in low for w in ("quote", "zitat", "excerpt", "auszug", "text", "passage")):
            out = h.text if h else ""
        elif any(w in low for w in _ROLE_WORDS):
            out = self.scene.speakers[0] if self.scene.speakers else ""
        elif any(w in low for w in ("cue", "keyword", "phrase", "stichwort")):
            out = h.cue if h else ""
        else:
            out = _reason(h)
        return out[:int(sch["maxLength"])] if "maxLength" in sch else out
