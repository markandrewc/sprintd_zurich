"""Check ``entities``: who talks and about what (advisor, customer, companies), for cross-call patterns.

Scores no family and is configured with ``weight: 0``: it never moves a label. Its output lives in
``CheckResult.meta["entities"]`` and feeds :mod:`callguard.patterns` and :mod:`callguard.routing`.

Sources, strongest first:

1. **Sidecar** ``<audio>.meta.json`` or ``<audio stem>.meta.json`` next to the recording
   (``advisor_id``, ``advisor_name``, ``customer_id``, ``customer_name``, ``started_at``, ``line``):
   the target picture, where the recording system knows who was on the line. Wins over everything.
2. **Directory**: an advisor of ``config/directory.yaml`` named in the first advisor turns (handles
   "Grüezi, Online-Service, Sonja Hess." that no greeting pattern catches).
3. **Greeting patterns** (Swiss German + Standard German ASR output): "da isch d Simone Wenger",
   "hier ist die ...", "mein Name ist ...", customer addressed as "Frau Aebi" / "Herr ...".
4. **LLM** (optional, ``llm: default``): JSON with names, companies / securities and third parties;
   fills what the patterns left empty.

Companies / securities: capitalised name + typical company word ("Rigi Sensorik", "Limmat Energie",
"... AG", "... Holding"). Rough on purpose; the LLM option does better.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.checks.textnorm import fold
from callguard.plugins import Check
from callguard.routing import Directory
from callguard.types import CallResult, CheckResult, Family, Transcript

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard.checks.entities")

_N = r"[A-ZÄÖÜ][a-zäöüéèàëï]+(?:-[A-ZÄÖÜ][a-zäöüéèàëï]+)?"
INTRO = re.compile(r"(?i:\b(?:da|hier|do)\s+(?:isch|ist|is|spricht|schpricht)\s+(?:d|di|die|de|der|dr)?\s*)"
                   rf"({_N}\s+{_N})")
NAME_IS = re.compile(rf"(?i:\b(?:mein|min|mi)\s+name\s+(?:ist|isch|is)\s+)({_N}(?:\s+{_N})?)")
ADDRESS = re.compile(rf"\b(Frau|Herr)\s+({_N})")
_COMPANY_WORDS = ("AG", "SA", "Holding", "Gruppe", "Group", "Energie", "Sensorik", "Optik", "Pharma", "Technik",
                  "Technologies", "Systems", "Industrie", "Industries", "Werke", "Immobilien", "Versicherungen",
                  "Medtech", "Logistik", "Chemie", "Solar", "Robotik", "Biotech", "Elektronik", "Software", "Bank")
COMPANY = re.compile(rf"\b({_N}(?:\s+{_N})?)\s+({'|'.join(_COMPANY_WORDS)})\b")
NOT_A_NAME = {fold(w).lower() for w in (
    "Die", "Der", "Das", "De", "Dr", "Di", "D", "Eine", "Ein", "En", "E", "Ihre", "Ihri", "Ihrer", "Ihrem", "Ihren",
    "Ihres", "Mini", "Minere", "Meine", "Meiner", "Unsere", "Unserer", "Eusere", "Eurer", "Jede", "Jeder", "Andere",
    "Eusi", "Neue", "Neui", "Erneuerbare", "Diese", "Dä", "Säb", "Sie", "Ich", "Mir", "Wir", "Und", "Aber",
    "Rechnung", "Rechnig", "Bank", "Kunde", "Kundin", "Beratung", "Service", "Online", "Team", "Grüezi", "Guete")}
INTRO_SEGMENTS = 4  # greetings happen at the start of a call


def _key(name: str | None) -> str | None:
    return re.sub(r"\s+", " ", fold(name).lower()).strip() if name else None


def _clean(name: str) -> str | None:
    parts = name.split()
    if not parts or any(fold(p).lower() in NOT_A_NAME for p in parts):
        return None
    return " ".join(parts)


def read_sidecar(audio_path: str | Path | None) -> dict[str, Any] | None:
    if not audio_path:
        return None
    p = Path(audio_path)
    for cand in (p.with_name(p.name + ".meta.json"), p.with_suffix(".meta.json")):
        if cand.is_file():
            try:
                data = json.loads(cand.read_text())
                return data if isinstance(data, dict) else None
            except Exception as e:
                log.warning("sidecar %s unreadable: %s", cand, e)
    return None


def _roles(t: Transcript) -> tuple[list, list]:
    """(advisor segments, customer segments). Without roles: the first speaker is the advisor
    (callbacks), without speakers: every segment is a candidate for both."""
    segs = t.segments
    if any(s.role != "unknown" for s in segs):
        return [s for s in segs if s.role == "advisor"], [s for s in segs if s.role == "customer"]
    if segs and segs[0].speaker:
        first = segs[0].speaker
        return [s for s in segs if s.speaker == first], [s for s in segs if s.speaker != first]
    return list(segs), list(segs)


def _directory_hit(directory: Directory, segs: list) -> tuple[Any, str] | None:
    text = {s.id: f" {_key(s.text)} " for s in segs}
    for a in directory.advisors.values():
        k = _key(a.name)
        for sid, t in text.items():
            if k and re.search(rf"\b{re.escape(k)}\b", t):
                return a, sid
    return None


def extract_entities(t: Transcript, directory: Directory | None = None,
                     sidecar: dict[str, Any] | None = None) -> dict[str, Any]:
    """Entities of one transcript (regex + directory + sidecar; no LLM). ``directory`` None = the default
    config/directory.yaml."""
    directory = directory if directory is not None else Directory.load()
    adv_segs, cus_segs = _roles(t)
    adv_head, cus_head = adv_segs[:INTRO_SEGMENTS], cus_segs[:INTRO_SEGMENTS]
    advisor: dict[str, Any] | None = None
    customer: dict[str, Any] | None = None

    hit = _directory_hit(directory, adv_head)
    if hit:
        a, sid = hit
        advisor = {"name": a.name, "id": a.id, "source": "directory", "segment_id": sid}
    for s in adv_head:
        if advisor:
            break
        m = INTRO.search(s.text) or NAME_IS.search(s.text)
        if m and (name := _clean(m.group(1))):
            a = directory.advisor(name)
            advisor = {"name": a.name if a else name, "id": a.id if a else None, "source": "greeting",
                       "segment_id": s.id}
    adv_key = _key(advisor["name"]) if advisor else None
    for s in cus_head:
        m = INTRO.search(s.text) or NAME_IS.search(s.text)
        if m and (name := _clean(m.group(1))) and _key(name) != adv_key:
            customer = {"name": name, "id": None, "source": "greeting", "segment_id": s.id}
            break
    if customer is None:
        for s in adv_head:
            m = ADDRESS.search(s.text)
            if m and (name := _clean(m.group(2))):
                customer = {"name": f"{m.group(1)} {name}", "id": None, "source": "address", "segment_id": s.id}
                break

    companies: dict[str, dict[str, Any]] = {}
    for s in t.segments:
        for m in COMPANY.finditer(s.text):
            head = _clean(m.group(1))
            if not head:
                continue
            name = f"{head} {m.group(2)}"
            c = companies.setdefault(_key(name), {"name": name, "segment_ids": [], "count": 0})
            c["count"] += 1
            if s.id not in c["segment_ids"]:
                c["segment_ids"].append(s.id)

    ent: dict[str, Any] = {"advisor": advisor, "customer": customer, "companies": list(companies.values()),
                           "third_parties": []}
    if sidecar:
        apply_sidecar(ent, sidecar, directory)
    return finalize(ent)


def apply_sidecar(ent: dict[str, Any], sidecar: dict[str, Any], directory: Directory | None = None) -> None:
    directory = directory or Directory()
    if sidecar.get("advisor_id") or sidecar.get("advisor_name"):
        a = directory.advisor(sidecar.get("advisor_id")) or directory.advisor(sidecar.get("advisor_name"))
        ent["advisor"] = {"name": a.name if a else sidecar.get("advisor_name") or sidecar.get("advisor_id"),
                          "id": a.id if a else sidecar.get("advisor_id"), "source": "sidecar"}
    if sidecar.get("customer_id") or sidecar.get("customer_name"):
        ent["customer"] = {"name": sidecar.get("customer_name") or sidecar.get("customer_id"),
                           "id": sidecar.get("customer_id"), "source": "sidecar"}
    ent["sidecar"] = {k: sidecar[k] for k in ("started_at", "line", "advisor_id", "customer_id") if k in sidecar}


def finalize(ent: dict[str, Any]) -> dict[str, Any]:
    """Grouping keys for patterns: directory/sidecar id if known, else the folded name."""
    adv, cus = ent.get("advisor") or {}, ent.get("customer") or {}
    ent["advisor_key"] = adv.get("id") or _key(adv.get("name"))
    ent["customer_key"] = cus.get("id") or _key(cus.get("name"))
    ent["company_keys"] = sorted({_key(c["name"]) for c in ent.get("companies") or [] if c.get("name")})
    return ent


def entities_of(result: CallResult, directory: Directory | None = None) -> dict[str, Any]:
    """Entities of a stored result: the ``entities`` check's output if it ran, else extracted now from the
    primary transcript. A sidecar next to the audio always wins (also for results computed before it
    existed)."""
    directory = directory if directory is not None else Directory.load()
    ent = None
    for c in result.checks.values():
        if c.type == "entities" and isinstance(c.meta.get("entities"), dict):
            ent = json.loads(json.dumps(c.meta["entities"]))  # copy: never mutate the stored result
            break
    if ent is None:
        ent = extract_entities(result.transcript, directory)
    sidecar = read_sidecar(result.audio_path)
    if sidecar:
        apply_sidecar(ent, sidecar, directory)
    return finalize(ent)


LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "advisor_name": {"type": ["string", "null"]},
        "customer_name": {"type": ["string", "null"]},
        "companies": {"type": "array", "items": {"type": "string"}},
        "third_parties": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["advisor_name", "customer_name", "companies", "third_parties"],
}
LLM_PROMPT = (
    "Lies das Transkript eines Bank-Telefonats (Beratung und Kundschaft). Gib NUR JSON zurück mit: "
    "advisor_name (Name der Beratungsperson oder null), customer_name (Name der Kundin/des Kunden oder null), "
    "companies (genannte Firmen oder Wertschriften), third_parties (andere genannte Personen, z.B. Angehörige). "
    "Nur Namen, die wörtlich vorkommen; nichts erfinden.")


class EntityCheck(Check):
    def __init__(self, ctx: "Context", *, directory: str | None = None, llm: str | None = None,
                 max_chars: int = 12000, **kw: Any):
        super().__init__(ctx, directory=directory, llm=llm, max_chars=max_chars, **kw)
        self.directory_path = directory
        self.llm_name = llm
        self.max_chars = int(max_chars)

    def cache_key(self, families: list[Family]) -> dict[str, Any]:
        # families are irrelevant; the directory content is not (its file hash)
        from callguard.audit import file_hash
        from callguard.routing import DEFAULT_DIRECTORY, resolve

        key: dict[str, Any] = {"params": self.cache_params(),
                               "directory": file_hash(resolve(self.directory_path, DEFAULT_DIRECTORY))}
        if self.llm_name and self.ctx is not None:
            try:
                key["llm"] = self.ctx.llm(self.llm_name).cache_params()
            except Exception:
                key["llm"] = self.llm_name
        return key

    def run(self, transcript: Transcript, families: list[Family]) -> CheckResult:
        directory = Directory.load(self.directory_path)
        ent = extract_entities(transcript, directory, read_sidecar(transcript.audio_path))
        meta: dict[str, Any] = {"entities": ent, "cacheable": bool(self.llm_name)}  # regex: cheap, always fresh
        if self.llm_name and self.ctx is not None:
            try:
                self._llm_fill(transcript, ent, directory)
            except Exception as e:
                meta["llm_error"] = f"{type(e).__name__}: {e}"
                meta["cacheable"] = False
        finalize(ent)
        return CheckResult(check=self.name, type=self.plugin_type or "entities", meta=meta)

    def _llm_fill(self, t: Transcript, ent: dict[str, Any], directory: Directory) -> None:
        from callguard.llm.jsonutil import chat_json

        text = t.render(times=False)[: self.max_chars]
        out = chat_json(self.ctx.llm(self.llm_name), [{"role": "system", "content": LLM_PROMPT},
                                                      {"role": "user", "content": text}], LLM_SCHEMA)[0]
        if not ent.get("advisor") and out.get("advisor_name"):
            a = directory.advisor(out["advisor_name"])
            ent["advisor"] = {"name": a.name if a else out["advisor_name"], "id": a.id if a else None, "source": "llm"}
        if not ent.get("customer") and out.get("customer_name"):
            ent["customer"] = {"name": out["customer_name"], "id": None, "source": "llm"}
        have = {_key(c["name"]) for c in ent["companies"]}
        for name in out.get("companies") or []:
            if name and _key(name) not in have:
                ent["companies"].append({"name": name, "segment_ids": [], "count": 1, "source": "llm"})
                have.add(_key(name))
        ent["third_parties"] = [x for x in out.get("third_parties") or [] if x]
