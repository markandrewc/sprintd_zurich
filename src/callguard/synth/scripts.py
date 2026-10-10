"""LLM script writer for synthetic calls (v2_plan §4, research RQ10 / queue D1).

Per scenario (``config/synth_scenarios.yaml``) the FIRST variant is written freely from the setting and
its decisive context; every twin is then a REWRITE of that base script in which only the turns needed for
the twin's decisive context change (minimal pairs, like the case's Stufe2 twins). If a rewrite keeps
failing validation the twin is written freely instead (recorded as ``mode: free`` in the manifest).

The LLM is told what must happen in the call; it is never asked for a label. The expected label, the
Begründung and the Offen line come from the scenario file. Output per script, in the case layout::

    data_synth/<set>/Transkript/Synth_trade_001.txt                 turns only ("T001 · Beratung" ...)
    data_synth/<set>/Skript_mit_Sollbewertung/Synth_trade_001.txt   header (Testziel, Ereignis,
                                                                    Bearbeitung, Begründung, Offen,
                                                                    Belege, Gruppe) + the same turns
    data_synth/<set>/manifest.json                                  scenario, variant, model, attempts

Validation (each attempt; a failed attempt is retried with the errors as feedback): JSON shape, turn
count, who opens, only the two speaker labels, no meta words, the scenario's must-include strings,
evidence turns in range, twins neither identical to nor unrelated to their base, and a round trip through
``data.parse_turns`` / ``data.parse_expected``.
"""

from __future__ import annotations

import difflib
import json
import logging
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from callguard.data import parse_expected, parse_turns
from callguard.llm.jsonutil import parse_json
from callguard.synth.scenarios import Job, Scenario

log = logging.getLogger("callguard.synth")

ADVISOR = "Beratung"
META_WORDS = ("Testziel", "Sollbewertung", "Szenario", "Variante", "no_alert", "Compliance-Test", "Regieanweisung")
MIN_WORDS_PER_TURN = 2  # the last two turns (goodbyes) are exempt
TWIN_KEPT_MIN = 0.3  # a twin keeps at least this share of its base's turns verbatim (minimal pair) ...
TWIN_IDENTICAL = 0.985  # ... and is not (almost) identical to it (difflib ratio of the whole text)
GENERATOR_VERSION = "synth-scripts-v1"

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "turns": {"type": "array", "items": {
            "type": "object",
            "properties": {"speaker": {"type": "string"}, "text": {"type": "string"}},
            "required": ["speaker", "text"]}},
        "evidence_turns": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["title", "turns", "evidence_turns"],
}

# Fresh, neutral samples (not from the case data): they show spelling and tone only.
STYLE_EXAMPLES = {
    "gsw": """T001 · Beratung
Grüezi Herr Muster, da isch de Marco Steiner vo de Bank. Sie händ eus wäge Ihrem Dauerauftrag gschribe. Was chan ich für Sie mache?

T002 · Kunde
Grüezi. Ich wett de Dauerauftrag für d Miete aapasse, mir zahled ab nöchschtem Monet hundertfüfzg Franke meh.

T003 · Beratung
Das chömer grad mache. Isch es immer no s gliiche Konto vom Vermieter, oder hät sich da au öppis gänderet?

T004 · Kunde
Nei, s Konto bliibt gliich. Nume de Betrag ändert. Und bitte ab em erschte, nöd ab em füfzähte.""",
    "de": """T001 · Beratung
Grüezi Herr Muster, hier ist Marco Steiner von der Bank. Sie haben uns wegen Ihres Dauerauftrags geschrieben. Was kann ich für Sie tun?

T002 · Kunde
Grüezi. Ich möchte den Dauerauftrag für die Miete anpassen, wir zahlen ab nächstem Monat hundertfünfzig Franken mehr.

T003 · Beratung
Das können wir gleich machen. Ist es immer noch das gleiche Konto vom Vermieter, oder hat sich da auch etwas geändert?

T004 · Kunde
Nein, das Konto bleibt gleich. Nur der Betrag ändert. Und bitte ab dem Ersten, nicht ab dem Fünfzehnten.""",
}
STYLE_EXAMPLE = STYLE_EXAMPLES["gsw"]
LANGUAGE_RULE = {
    "gsw": "Alles auf Schweizerdeutsch ({dialect}), so wie man spricht, in einfacher Dialektschreibweise wie im "
           "Beispiel unten. Keine hochdeutschen Sätze.",
    "de": "Alles auf Hochdeutsch in Schweizer Schreibweise (ss statt ß, Franken, Grüezi), in einfachen, "
          "gesprochenen Sätzen, so wie eine Spracherkennung ein Schweizer Telefongespräch auf Hochdeutsch "
          "transkribiert.",
}


def system_prompt(language: str = "de", dialect: str = "Zürichdeutsch") -> str:
    rule = LANGUAGE_RULE[language].format(dialect=dialect)
    return f"""Du schreibst realistische, fiktive Telefongespräche zwischen der Beratung einer Schweizer Bank und
einer Kundin oder einem Kunden. Die Gespräche dienen als Testmaterial; alle Personen und Firmen sind erfunden.

Regeln:
- {rule} Keine Regieanweisungen, keine Geräusche, kein Erzähler.
- Genau zwei Sprecher: "{ADVISOR}" (die Bankberatung) und die anrufende bzw. angerufene Kundin / der Kunde.
- Ein natürlicher Gesprächsverlauf: Begrüssung, Anliegen, Rückfragen, Alltagsdetails, Abschluss. Der
  entscheidende Inhalt ist eingebettet, nicht das ganze Gespräch. Jeder Turn bringt etwas Neues; keine
  Wiederholungen.
- Halte dich GENAU an den vorgegebenen entscheidenden Inhalt: nicht mehr und nicht weniger. Wenn etwas offen
  bleiben soll, bleibt es bis zum Schluss offen. Wenn etwas öffentlich, abgelaufen oder ein Beispiel ist, sagt
  das jemand im Gespräch ausdrücklich.
- Niemand bewertet das Gespräch, nennt Prüfkategorien oder spricht über "Testfälle".
- Zahlen dürfen als Ziffern oder als Wörter stehen.

Beispiel für Ton und Schreibweise (anderes Thema):
{STYLE_EXAMPLES[language]}

Antworte nur mit JSON: {{"title": "<kurzer Titel auf Hochdeutsch, ohne Bewertung>",
"turns": [{{"speaker": "...", "text": "..."}}, ...],
"evidence_turns": [<Nummern (1 = erster Turn) der Turns, die den entscheidenden Inhalt tragen>]}}"""


SYSTEM = system_prompt("gsw")


@dataclass
class Script:
    title: str
    turns: list[tuple[str, str]]  # (speaker, text)
    evidence: list[int]  # 1-based turn numbers

    def as_json(self) -> dict[str, Any]:
        return {"title": self.title, "turns": [{"speaker": s, "text": t} for s, t in self.turns],
                "evidence_turns": self.evidence}


@dataclass
class Outcome:
    job: Job
    ok: bool
    mode: str = "free"  # free | rewrite | existing
    attempts: int = 0
    errors: list[str] = field(default_factory=list)
    script: Script | None = None
    model: str = ""
    seconds: float = 0.0


# --------------------------------------------------------------------------------------------
# prompts
# --------------------------------------------------------------------------------------------


def _who(s: Scenario) -> str:
    return "die Beratung" if s.opens == "advisor" else f"die/der {s.customer}"


def _frame(job: Job) -> str:
    s, v = job.scenario, job.variant
    lo, hi = job.turn_range
    musts = ", ".join(f'"{m}"' for m in job.must_include)
    return (f"Sprecher-Bezeichnungen: \"{ADVISOR}\" und \"{s.customer}\". Das Gespräch beginnt mit {_who(s)} "
            f"(Turn 1 = \"{ADVISOR if s.opens == 'advisor' else s.customer}\").\n"
            f"Länge: ungefähr {s.turns} Turns (mindestens {lo}, höchstens {hi}); die Sprecher wechseln sich ab.\n"
            + (f"Dialekt: {s.dialect}.\n" if s.language == "gsw" else "Sprache: Hochdeutsch (Schweizer Schreibweise).\n")
            + (f"Diese Wörter müssen wörtlich vorkommen: {musts}.\n" if musts else "")
            + f"\nSituation: {s.setting}\n\nEntscheidender Inhalt (muss genau so vorkommen): {v.decisive}")


def messages_free(job: Job, feedback: list[str] | None = None) -> list[dict[str, str]]:
    user = "Schreib das folgende Telefongespräch.\n\n" + _frame(job)
    if feedback:
        user += "\n\nDein letzter Versuch war ungültig: " + "; ".join(feedback[:6]) + ". Bitte korrigieren."
    return [{"role": "system", "content": system_prompt(job.scenario.language, job.scenario.dialect)},
            {"role": "user", "content": user}]


def messages_rewrite(job: Job, base: Script, base_job: Job, feedback: list[str] | None = None
                     ) -> list[dict[str, str]]:
    user = ("Hier ist ein bestehendes Gespräch. Schreib eine Variante davon: Ändere NUR die Turns, die nötig "
            "sind, damit der entscheidende Inhalt dem neuen Inhalt unten entspricht, und alles, was dem neuen "
            "Inhalt widersprechen würde. Alle anderen Turns übernimmst du wörtlich. Vom alten entscheidenden "
            "Inhalt darf nichts übrig bleiben, was dem neuen widerspricht.\n\n"
            f"Alter entscheidender Inhalt: {base_job.variant.decisive}\n\n"
            f"Bestehendes Gespräch (JSON):\n{json.dumps(base.as_json(), ensure_ascii=False)}\n\n"
            "Rahmen für die Variante:\n" + _frame(job))
    if feedback:
        user += "\n\nDein letzter Versuch war ungültig: " + "; ".join(feedback[:6]) + ". Bitte korrigieren."
    return [{"role": "system", "content": system_prompt(job.scenario.language, job.scenario.dialect)},
            {"role": "user", "content": user}]


# --------------------------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------------------------


def _norm(s: str) -> str:
    """Lower case, typographic apostrophes / thousands separators unified, whitespace collapsed."""
    s = s.lower().replace("’", "'").replace("`", "'")
    return " ".join(s.split())


def _contains(text: str, needle: str) -> bool:
    t, n = _norm(text), _norm(needle)
    if n in t:
        return True
    if any(ch.isdigit() for ch in n):  # 1'280 == 1280 == 1 280
        squash = lambda x: re.sub(r"(?<=\d)['\s.](?=\d)", "", x)  # noqa: E731
        return squash(n) in squash(t)
    return False


def _canon_speaker(name: str, customer: str) -> str | None:
    n = name.strip().strip(":").strip().lower()
    if n.startswith("berat") or n in ("bank", "berater", "beraterin"):
        return ADVISOR
    if n.startswith("kund"):
        return customer
    return None


def validate_script(data: Any, job: Job, base: Script | None = None) -> tuple[Script | None, list[str]]:
    """Check one LLM output for ``job``. Returns the script (None if unusable) and the list of errors."""
    errors: list[str] = []
    if not isinstance(data, dict):
        return None, ["Antwort ist kein JSON-Objekt"]
    raw_turns = data.get("turns")
    if not isinstance(raw_turns, list) or not raw_turns:
        return None, ["keine Turns"]
    s = job.scenario
    turns: list[tuple[str, str]] = []
    for i, t in enumerate(raw_turns, 1):
        if not isinstance(t, dict):
            errors.append(f"Turn {i} ist kein Objekt")
            continue
        sp = _canon_speaker(str(t.get("speaker") or ""), s.customer)
        text = " ".join(str(t.get("text") or "").split())
        text = re.sub(r"^(T\d{3}\s*·\s*\S+\s*)", "", text)  # a turn header copied into the text
        if sp is None:
            errors.append(f"Turn {i}: unbekannter Sprecher {t.get('speaker')!r} (nur {ADVISOR} / {s.customer})")
            continue
        if len(text.split()) < MIN_WORDS_PER_TURN and i < len(raw_turns) - 1:
            errors.append(f"Turn {i} ist zu kurz")
        turns.append((sp, text))
    lo, hi = job.turn_range
    if not lo <= len(turns) <= hi:
        errors.append(f"{len(turns)} Turns, verlangt {lo} bis {hi}")
    want_first = ADVISOR if s.opens == "advisor" else s.customer
    if turns and turns[0][0] != want_first:
        errors.append(f"Turn 1 muss von \"{want_first}\" sein")
    run = 1
    for a, b in zip(turns, turns[1:]):
        run = run + 1 if a[0] == b[0] else 1
        if run > 2:
            errors.append("mehr als zwei Turns hintereinander vom gleichen Sprecher")
            break
    if turns and {sp for sp, _ in turns} != {ADVISOR, s.customer}:
        errors.append("beide Sprecher müssen vorkommen")
    errors += repetition_errors(turns)
    full = "\n".join(t for _, t in turns)
    for w in META_WORDS:
        if re.search(rf"\b{re.escape(w)}\b", full, re.IGNORECASE):
            errors.append(f"Meta-Wort {w!r} im Gespräch")
    for m in job.must_include:
        if not _contains(full, m):
            errors.append(f"\"{m}\" fehlt")
    ev_raw = data.get("evidence_turns") or []
    evidence = sorted({int(x) for x in ev_raw if isinstance(x, (int, float)) or str(x).strip().isdigit()})
    if not evidence:
        errors.append("evidence_turns fehlt")
    elif any(not 1 <= e <= len(turns) for e in evidence):
        errors.append(f"evidence_turns ausserhalb 1..{len(turns)}")
    if base is not None and turns:
        if similarity(base, turns) >= TWIN_IDENTICAL:
            errors.append("die Variante ist mit dem bestehenden Gespräch identisch; der entscheidende Inhalt muss sich ändern")
        elif kept_share(base, turns) < TWIN_KEPT_MIN:
            errors.append("die Variante weicht zu stark ab; übernimm die nicht betroffenen Turns wörtlich")
    title = " ".join(str(data.get("title") or "").split())[:90] or s.id
    title = title.replace("·", "-")
    if not turns:
        return None, errors or ["keine gültigen Turns"]
    return Script(title=title, turns=turns, evidence=evidence), errors


def repetition_errors(turns: list[tuple[str, str]]) -> list[str]:
    """Degenerate loops of small models: a turn repeating an earlier one, or one sentence said 3+ times."""
    errs: list[str] = []
    seen: dict[str, int] = {}
    for i, (_, t) in enumerate(turns, 1):
        k = _turn_key(t)
        if k in seen:
            errs.append(f"Turn {i} wiederholt Turn {seen[k]}")
            break
        seen[k] = i
    counts: dict[str, int] = {}
    for _, t in turns:
        for sent in re.split(r"(?<=[.!?])\s+", t):
            k = _turn_key(sent)
            if len(k.split()) >= 5:
                counts[k] = counts.get(k, 0) + 1
    rep = [k for k, n in counts.items() if n >= 3]
    if rep:
        errs.append(f"der Satz \"{rep[0][:60]}\" kommt {counts[rep[0]]} Mal vor")
    return errs


def _turn_key(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.lower()).strip()


def kept_share(base: Script, turns: list[tuple[str, str]]) -> float:
    """Share of the base's turns that reappear verbatim (up to case/punctuation), in order."""
    a = [_turn_key(t) for _, t in base.turns]
    b = [_turn_key(t) for _, t in turns]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    return sum(m.size for m in sm.get_matching_blocks()) / max(1, len(a))


def similarity(base: Script, turns: list[tuple[str, str]]) -> float:
    a = "\n".join(t for _, t in base.turns)
    b = "\n".join(t for _, t in turns)
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


# --------------------------------------------------------------------------------------------
# rendering (case layout)
# --------------------------------------------------------------------------------------------


def render_turns(script: Script) -> str:
    return "\n\n".join(f"T{i:03d} · {sp}\n{text}" for i, (sp, text) in enumerate(script.turns, 1)) + "\n"


def render_expected(job: Job, script: Script, model: str) -> str:
    v = job.variant
    ev = ", ".join(f"T{e:03d}" for e in script.evidence)
    words = sum(len(t.split()) for _, t in script.turns)
    head = [
        f"{job.dialogue_id} · {script.title}",
        f"Synthetisches Textskript (ohne Audio) zu Szenario {job.scenario.id}, Variante {v.name}.",
        f"Dauer: ungefähr {words / 120:.1f} min bei 120 Wörtern/min; {words} Wörter.",
        f"Testziel: {job.family}",
        f"Ereignis: {job.event}",
        f"Bearbeitung: {v.label}",
        f"Begründung: {v.reason}",
        f"Offen: {v.open or 'keine Voraussetzung für diese Sollbewertung'}",
        f"Prüfpräfix bis T{max(script.evidence):03d}; Belege: {ev}",
        "Keywordstellen: nicht annotiert (synthetisch)",
        f"Gruppe: {job.scenario.id}",
        f"Variante: {v.name}",
        f"Quelle: LLM {model} ({GENERATOR_VERSION}); Label aus config/synth_scenarios.yaml, nicht vom LLM",
    ]
    return "\n".join(head) + "\n\n" + render_turns(script)


def check_rendered(job: Job, script: Script, transcript: str, expected: str) -> list[str]:
    """Round trip through the case parsers (what load_calls / the reference ASR will read)."""
    errors: list[str] = []
    turns = parse_turns(transcript)
    if len(turns) != len(script.turns):
        errors.append(f"parse_turns: {len(turns)} turns, expected {len(script.turns)}")
    roles = {t.role for t in turns}
    if roles != {"advisor", "customer"}:
        errors.append(f"roles {sorted(roles)}")
    title, exp = parse_expected(expected)
    if exp is None:
        errors.append("parse_expected: no Bearbeitung")
    else:
        if exp.label != job.variant.label:
            errors.append(f"label {exp.label!r} != {job.variant.label!r}")
        if exp.family != job.family:
            errors.append(f"family {exp.family!r} != {job.family!r}")
        ids = {t.id for t in turns}
        if not exp.evidence_turns or not set(exp.evidence_turns) <= ids:
            errors.append(f"Belege {exp.evidence_turns} not in turns")
    if not title.startswith(job.dialogue_id):
        errors.append("title line")
    return errors


def paths(out_dir: Path, job: Job) -> tuple[Path, Path]:
    return (out_dir / "Transkript" / f"{job.dialogue_id}.txt",
            out_dir / "Skript_mit_Sollbewertung" / f"{job.dialogue_id}.txt")


def write_script(out_dir: Path, job: Job, script: Script, model: str) -> tuple[Path, Path]:
    tp, ep = paths(out_dir, job)
    transcript, expected = render_turns(script), render_expected(job, script, model)
    errs = check_rendered(job, script, transcript, expected)
    if errs:
        raise ValueError(f"{job.dialogue_id}: rendered script does not parse: {errs}")
    tp.parent.mkdir(parents=True, exist_ok=True)
    ep.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text(transcript, encoding="utf-8")
    ep.write_text(expected, encoding="utf-8")
    return tp, ep


def read_script(out_dir: Path, job: Job) -> Script | None:
    """A previously written script of ``job`` if it still validates (resume), else None."""
    tp, ep = paths(out_dir, job)
    if not tp.exists() or not ep.exists():
        return None
    title, exp = parse_expected(ep.read_text(encoding="utf-8"))
    turns = parse_turns(tp.read_text(encoding="utf-8"))
    if exp is None or exp.label != job.variant.label or exp.family != job.family or not turns:
        return None
    t = title.split("·", 1)[1].strip() if "·" in title else title
    ev = [int(e[1:]) for e in exp.evidence_turns]
    return Script(title=t, turns=[(x.speaker, x.text) for x in turns], evidence=ev)


# --------------------------------------------------------------------------------------------
# generation
# --------------------------------------------------------------------------------------------


def wait_for_llm(llm: Any, budget_s: float = 2400.0, *, sleep: Callable[[float], None] = time.sleep,
                 on_wait: Callable[[float], None] | None = None) -> bool:
    """Poll ``GET /models`` (``llm.ping``) with backoff 15 s -> 60 s until it answers or ``budget_s`` runs out.
    Also waits while the server answers but has no model loaded yet (swap in progress)."""
    t0 = time.monotonic()
    delay = 15.0
    while True:
        alive = False
        try:
            alive = bool(llm.ping()) if hasattr(llm, "ping") else True
            if alive and hasattr(llm, "list_models"):
                alive = bool(llm.list_models())
        except Exception:  # noqa: BLE001 - any failure = not ready yet
            alive = False
        if alive:
            return True
        waited = time.monotonic() - t0
        if waited >= budget_s:
            return False
        if on_wait:
            on_wait(waited)
        sleep(min(delay, max(1.0, budget_s - waited)))
        delay = min(60.0, delay * 1.5)


def _model_name(llm: Any) -> str:
    try:
        return str(llm.model_id)
    except Exception:  # noqa: BLE001
        return str(getattr(llm, "model", "unknown"))


def generate_one(job: Job, llm: Any, *, base: Script | None = None, base_job: Job | None = None,
                 attempts: int = 4, temperature: float = 0.8, max_tokens: int = 3500,
                 request_retries: int = 3, retry_wait: float = 20.0,
                 sleep: Callable[[float], None] = time.sleep) -> Outcome:
    """Write one script; ``base`` given = rewrite it into this twin (falls back to a free write on the
    last attempt). Transport errors (server swapping) are retried separately from validation errors."""
    t0 = time.time()
    out = Outcome(job=job, ok=False, model=_model_name(llm))
    feedback: list[str] = []
    for a in range(1, attempts + 1):
        rewrite = base is not None and base_job is not None and a < attempts
        msgs = messages_rewrite(job, base, base_job, feedback) if rewrite else messages_free(job, feedback)  # type: ignore[arg-type]
        text = None
        for r in range(request_retries + 1):
            try:
                text = llm.chat(msgs, temperature=temperature, max_tokens=max_tokens, json_schema=SCHEMA)[0]
                break
            except Exception as e:  # noqa: BLE001 - transport / server errors
                out.errors.append(f"request: {type(e).__name__}: {str(e)[:160]}")
                if r < request_retries:
                    sleep(retry_wait * (r + 1))
        out.attempts = a
        if text is None:
            continue
        try:
            data = parse_json(text)
        except Exception as e:  # noqa: BLE001
            feedback = [f"kein gültiges JSON ({type(e).__name__})"]
            out.errors.append(f"attempt {a}: " + feedback[0])
            continue
        script, errs = validate_script(data, job, base if rewrite else None)
        if script is not None and not errs:
            out.ok, out.script, out.mode = True, script, "rewrite" if rewrite else "free"
            out.model = _model_name(llm)
            break
        feedback = errs
        out.errors.append(f"attempt {a}: " + "; ".join(errs[:6]))
    out.seconds = round(time.time() - t0, 1)
    return out


def generate_set(jobs: list[Job], llm: Any, out_dir: str | Path, *, workers: int = 4, force: bool = False,
                 attempts: int = 4, temperature: float = 0.8,
                 progress: Callable[[Outcome], None] | None = None) -> list[Outcome]:
    """Write every job's script under ``out_dir``. Scenarios run in parallel (``workers`` <= 4 keeps
    the shared GPU usable); inside a scenario the base variant comes first, its twins after it. Scripts
    already on disk that still match their job are kept (resume) unless ``force``. Writes manifest.json."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    by_scenario: dict[str, list[Job]] = {}
    for j in jobs:
        by_scenario.setdefault(j.scenario.id, []).append(j)
    outcomes: list[Outcome] = []
    lock = threading.Lock()
    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, Any] = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.setdefault("scripts", {})

    def record(o: Outcome) -> None:
        with lock:
            outcomes.append(o)
            if o.ok and o.mode != "existing":
                write_script(out_dir, o.job, o.script, o.model)  # type: ignore[arg-type]
            if o.ok:
                prev = manifest["scripts"].get(o.job.dialogue_id, {})
                manifest["scripts"][o.job.dialogue_id] = {
                    "call_id": o.job.call_id, "scenario": o.job.scenario.id, "variant": o.job.variant.name,
                    "label": o.job.variant.label, "family": o.job.family, "base": o.job.base,
                    "mode": prev.get("mode", o.mode) if o.mode == "existing" else o.mode,
                    "model": prev.get("model", o.model) if o.mode == "existing" else o.model,
                    "attempts": prev.get("attempts", o.attempts) if o.mode == "existing" else o.attempts,
                    "turns": len(o.script.turns) if o.script else None,
                    "created": prev.get("created") if o.mode == "existing" else time.strftime("%Y-%m-%dT%H:%M:%S"),
                }
            manifest.update(generator=GENERATOR_VERSION, updated=time.strftime("%Y-%m-%dT%H:%M:%S"))
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True))
        if progress:
            progress(o)

    def scenario(js: list[Job]) -> None:
        base_job = js[0]
        base = None if force else read_script(out_dir, base_job)
        if base is not None:
            record(Outcome(job=base_job, ok=True, mode="existing", script=base))
        else:
            o = generate_one(base_job, llm, attempts=attempts, temperature=temperature)
            record(o)
            base = o.script if o.ok else None
        for j in js[1:]:
            have = None if force else read_script(out_dir, j)
            if have is not None:
                record(Outcome(job=j, ok=True, mode="existing", script=have))
                continue
            record(generate_one(j, llm, base=base, base_job=base_job if base else None, attempts=attempts,
                                temperature=temperature))

    groups = list(by_scenario.values())
    if workers > 1 and len(groups) > 1:
        with ThreadPoolExecutor(max_workers=min(workers, 4, len(groups))) as pool:
            list(pool.map(scenario, groups))
    else:
        for g in groups:
            scenario(g)
    order = {j.dialogue_id: i for i, j in enumerate(jobs)}
    return sorted(outcomes, key=lambda o: order.get(o.job.dialogue_id, 1 << 30))


def validate_set(out_dir: str | Path, jobs: list[Job]) -> dict[str, list[str]]:
    """Offline check of a written set: every job present, parsable, label/family as planned.
    Returns dialogue id -> errors (empty dict = all good)."""
    out_dir = Path(out_dir)
    problems: dict[str, list[str]] = {}
    for j in jobs:
        tp, ep = paths(out_dir, j)
        if not tp.exists() or not ep.exists():
            problems[j.dialogue_id] = ["missing"]
            continue
        s = read_script(out_dir, j)
        if s is None:
            problems[j.dialogue_id] = ["label/family mismatch or no turns"]
            continue
        errs = check_rendered(j, s, tp.read_text(encoding="utf-8"), ep.read_text(encoding="utf-8"))
        lo, hi = j.turn_range
        if not lo <= len(s.turns) <= hi:
            errs.append(f"{len(s.turns)} turns not in {lo}..{hi}")
        if errs:
            problems[j.dialogue_id] = errs
    return problems
