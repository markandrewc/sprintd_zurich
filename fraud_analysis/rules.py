"""Fakten und Regeln der hierarchischen Prüfung (fraud_analysis/facts.json). Ohne torch/Kev importierbar, damit auch
das Dashboard Regeln auswerten kann.

  Grundfakt: Ja/Nein-Frage an Kev. Ja, wenn p(yes) die Schwelle erreicht (eine Schwelle für alle Fakten).
  Regel:     Kombination der Fakten: "conditions" legt pro Fakt "ja" oder "nein" fest, nicht genannte sind egal. Sie löst
             aus, wenn alle Bedingungen erfüllt sind.
  Alarm:     mindestens eine Regel löst aus.
"""
import json
import os
import re
from pathlib import Path

CONFIG = Path(__file__).parent / "facts.json"
HISTORY = Path(__file__).parent / "config_history"   # frühere Fassungen von facts.json, eine pro Version
ID = re.compile(r"^[a-z][a-z0-9_]{1,40}$")
VALUES = ("ja", "nein")


def load_config(path=CONFIG):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(facts, rules):
    """Fakten und Regeln prüfen und bereinigen. -> (facts, rules). ValueError mit einer Meldung, die man ohne
    Code-Kenntnis versteht."""
    if not isinstance(facts, dict) or not isinstance(rules, dict): raise ValueError("Fakten oder Regeln fehlen")
    clean_f = {}
    for fid, f in facts.items():
        if fid.startswith("_"): continue
        if not ID.match(fid): raise ValueError(f"Fakt-ID '{fid}': nur Kleinbuchstaben, Ziffern und _, z.B. trade_wish")
        question = str((f or {}).get("instructions", "")).strip()
        if not question: raise ValueError(f"Fakt '{fid}': die Frage fehlt")
        clean_f[fid] = {"type": "noul", "label": str(f.get("label", "")).strip() or fid, "instructions": question}
    clean_r = {}
    for rid, r in rules.items():
        if rid.startswith("_"): continue
        if not ID.match(rid): raise ValueError(f"Regel-ID '{rid}': nur Kleinbuchstaben, Ziffern und _, z.B. insider_trading")
        name = str((r or {}).get("name", "")).strip()
        if not name: raise ValueError(f"Regel '{rid}': der Name fehlt")
        cond = {f: v for f, v in (r.get("conditions") or {}).items() if v != "egal"}
        if not cond: raise ValueError(f"Regel '{name}': mindestens ein Fakt muss ja oder nein sein")
        bad = [f"{f}={v}" for f, v in cond.items() if v not in VALUES]
        if bad: raise ValueError(f"Regel '{name}': Bedingung muss ja, nein oder egal sein ({', '.join(bad)})")
        unknown = [f for f in cond if f not in clean_f]
        if unknown: raise ValueError(f"Regel '{name}': unbekannte Fakten {', '.join(unknown)}")
        clean_r[rid] = {"name": name, "conditions": {f: cond[f] for f in clean_f if f in cond}}
    if not clean_r: raise ValueError("Mindestens eine Regel ist nötig")
    return clean_f, clean_r


def save_config(facts, rules, path=CONFIG):
    """Ersetzt Fakten und Regeln in facts.json, zählt "version" hoch und legt die vorherige Fassung in config_history/
    ab. Schwelle und localization bleiben. -> neue Config."""
    cfg = load_config(path)
    facts, rules = validate(facts, rules)
    version = int(cfg.get("version", 1))
    HISTORY.mkdir(exist_ok=True)
    (HISTORY / f"facts_v{version}.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    new = {k: v for k, v in cfg.items() if k not in ("version", "facts", "rules")} | {"version": version + 1, "facts": facts, "rules": rules}
    tmp = Path(path).with_suffix(".tmp")
    tmp.write_text(json.dumps(new, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)   # atomar: eine laufende Analyse liest nie eine halb geschriebene Datei
    return new


def met(p, fact, value, threshold):
    """Ist die Bedingung fact = value ("ja"/"nein") erfüllt? Ein Fakt ohne Wert erfüllt keine Bedingung."""
    return fact in p and (p[fact] >= threshold) == (value == "ja")


def fired_rules(p, rules, threshold):
    """p: {fakt: p(yes)} -> IDs der Regeln, deren Bedingungen alle erfüllt sind."""
    return [rid for rid, r in rules.items() if r["conditions"] and all(met(p, f, v, threshold) for f, v in r["conditions"].items())]
