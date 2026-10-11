"""Can this profile process a NEW recording right now? A quick, model-free probe for «Anruf verarbeiten»:
the language model server answers ``GET /models`` (3 s), the speech recognition is either a reachable
remote server or a local model with what it needs (``callguard doctor``'s ASR probe, loads no weights).
Plain German summary; never raises."""

from __future__ import annotations

from dataclasses import dataclass, field

from callguard import registry
from callguard.config import load_config
from callguard.context import Context
from callguard.serve import doctor as doc


@dataclass
class Ready:
    ok: bool
    summary: str
    problems: list[str] = field(default_factory=list)


def _llm_ok(cfg, ctx) -> tuple[bool, str]:
    names = {str(c.get("llm")) for c in cfg.checks if c.get("llm") and c.get("enabled", True) is not False}
    if not names:
        return True, "keine Sprachmodell-Prüfung nötig"
    for name in sorted(names):
        spec = dict((cfg.llms or {}).get(name) or {})
        kind = str(spec.get("type", ""))
        if kind == "fake":
            continue
        if kind != "openai_compat":
            return True, f"Sprachmodell «{name}» läuft im Prozess"
        try:
            llm = registry.create("llm", {**spec, "max_retries": 0}, ctx=ctx)
            llm.list_models(timeout=3.0)
        except Exception as e:
            return False, f"Sprachmodell-Server nicht erreichbar ({type(e).__name__})"
    return True, "Sprachmodell erreichbar"


def _asr_ok(cfg, ctx) -> tuple[bool, str]:
    try:
        rows = doc._asr(cfg, ctx)
    except Exception as e:
        return False, f"Spracherkennung nicht prüfbar ({type(e).__name__})"
    bad = [r for r in rows if r.status == doc.FAIL]
    if bad:
        why = {"model": "Modell fehlt auf diesem Rechner", "cuda": "keine GPU", "server": "Server nicht erreichbar",
               "cublas": "GPU-Bibliotheken fehlen"}.get(bad[0].item, "nicht eingerichtet")
        return False, f"Spracherkennung nicht bereit ({why})"
    return True, "Spracherkennung bereit"


def check(config: str, sets: list[str] | None = None) -> Ready:
    try:
        cfg = load_config(config, sets or [])
        ctx = Context(cfg)
    except Exception as e:
        return Ready(False, f"Profil «{config}» nicht ladbar ({type(e).__name__})", [str(e)])
    out = [_asr_ok(cfg, ctx), _llm_ok(cfg, ctx)]
    ok = all(o for o, _ in out)
    return Ready(ok, " · ".join(msg for _, msg in out), [msg for o, msg in out if not o])
