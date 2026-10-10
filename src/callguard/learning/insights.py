"""What the officers' labels say, and which learning step they are enough for. Pure, unit-tested.

* :func:`overview`: labels per kind / family / fact, officer-vs-system confusion (3 x 3) with agreement
  and a Wilson 95 % CI, calls on which officers disagree.
* :func:`corrections`: per fact question (and per policy-table rule) how often officers correct the
  model; a question corrected in >= ``flag_rate`` of >= ``min_n`` labels gets "Formulierung prüfen".
* :func:`readiness`: the four learning steps with honest thresholds (docs/LEARNING.md):

  =====================================  ==========================  ===================================
  step                                   needs                       evidence for the threshold
  =====================================  ==========================  ===================================
  Schwelle / Kalibrierung pro Familie    ~30 call labels per family  rule of thumb for a 2-parameter fit;
                                                                     dev has 4-14 calls per family
  Few-shot-Beispiele                     ~5 confirmed per fact       measured on dev (S2): AUC -0.07
                                                                     (tuned) / -0.17 (paraphrased): no-go
  LoRA-Faktenleser (Kev / Qwen)          ~1000 trainable fact labels Kev upstream: ~1000 records for a
                                                                     measurable +5 points; 400 = noise
  Whisper-Feintuning                     real recordings with        ORACLE: perfect transcripts +0.03-0.05
                                         corrected transcripts       AUC; ASR is not the bottleneck
  =====================================  ==========================  ===================================
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from callguard.learning import hygiene as hy
from callguard.learning.records import CallLabel, FactLabel, LabelSet

LABELS = ("alarm", "review", "no_alert")
LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
NEED_FAMILY = 30
NEED_FEWSHOT = 5
NEED_LORA = 1000
NEED_WHISPER_HOURS = 50.0


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if n <= 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return round((c - h) / d, 4), round((c + h) / d, 4)


def confusion(calls: Mapping[str, CallLabel]) -> dict[str, Any]:
    """rows = officer label, columns = system label (what the officer was shown)."""
    m = {o: {s: 0 for s in LABELS} for o in LABELS}
    n = agree = 0
    for c in calls.values():
        if c.label in LABELS and c.system_label in LABELS:
            m[c.label][c.system_label] += 1
            n += 1
            agree += c.label == c.system_label
    flag_agree = sum(m[o][s] for o in LABELS for s in LABELS if (o == "no_alert") == (s == "no_alert"))
    lo, hi = wilson(agree, n)
    flo, fhi = wilson(flag_agree, n)
    return {"matrix": m, "n": n, "agree": agree, "agreement": round(agree / n, 4) if n else None,
            "ci": [lo, hi], "flag_agreement": round(flag_agree / n, 4) if n else None, "flag_ci": [flo, fhi],
            "false_alarms": sum(m["no_alert"][s] for s in ("alarm", "review")),
            "missed": sum(m[o]["no_alert"] for o in ("alarm", "review"))}


def overview(labels: LabelSet) -> dict[str, Any]:
    items = labels.items
    kinds = Counter(i.target for i in items)
    fam = Counter()
    for c in labels.calls.values():
        for f in {*c.families, *([c.system_family] if c.system_family else [])}:
            fam[f] += 1
    per_fact = Counter((f.family, f.fact) for f in labels.facts)
    return {
        "items": len(items), "officers": sorted({i.user for i in items}),
        "kinds": {k: kinds.get(k, 0) for k in ("call", "passage", "fact", "family")},
        "calls": len(labels.calls), "facts": len(labels.facts), "passages": len(labels.passages),
        "per_family": dict(sorted(fam.items())),
        "per_fact": {f"{a}.{b}": n for (a, b), n in sorted(per_fact.items())},
        "uses": dict(Counter(c.use for c in labels.calls.values())),
        "fact_uses": dict(Counter(f.use for f in labels.facts)),
        "confusion": confusion(labels.calls),
        "disagreements": sorted(c.call_id for c in labels.calls.values() if c.disagreement),
        "passages_applies": sum(1 for p in labels.passages if p.applies),
        "missed_families": dict(Counter(i.family for i in items if i.target == "family" and i.family)),
    }


def corrections(facts: Sequence[FactLabel], *, min_n: int = 5, flag_rate: float = 0.3,
                hint_n: int = 3) -> list[dict[str, Any]]:
    """Per (family, fact): labels, corrections (officer answer != model value), rate with Wilson CI.
    ``flag``: corrected in >= ``flag_rate`` of >= ``hint_n`` labels; ``strong`` once n >= ``min_n``
    (below that the advice says how few labels it rests on)."""
    groups: dict[tuple[str, str], list[FactLabel]] = {}
    for f in facts:
        if f.model_value is None:
            continue
        groups.setdefault((f.family, f.fact), []).append(f)
    out = []
    for (fam, fact), fs in groups.items():
        k = sum(1 for f in fs if f.corrected)
        lo, hi = wilson(k, len(fs))
        rate = k / len(fs)
        flagged = len(fs) >= hint_n and rate >= flag_rate
        strong = flagged and len(fs) >= min_n
        q = next((f.question for f in fs if f.question), None)
        directions = Counter(f"{f.model_value}->{f.answer}" for f in fs if f.corrected)
        advice = ""
        if flagged:
            advice = (f"Frage «{fs[0].fact_label}» wird in {rate:.0%} der Fälle korrigiert ({k} von {len(fs)}, "
                      f"95%-KI {lo:.0%}–{hi:.0%}) -> Formulierung prüfen.")
            if not strong:
                advice += f" Erst {len(fs)} Labels: ein Hinweis, noch keine Messung."
        out.append({"family": fam, "fact": fact, "fact_label": fs[0].fact_label, "question": q, "n": len(fs),
                    "corrected": k, "rate": round(rate, 4), "ci": [lo, hi], "flag": flagged, "strong": strong,
                    "directions": dict(directions.most_common()), "advice": advice})
    return sorted(out, key=lambda r: (-r["rate"], -r["n"], r["family"], r["fact"]))


def rule_corrections(calls: Mapping[str, CallLabel], facts: Sequence[FactLabel]) -> list[dict[str, Any]]:
    """Per policy-table rule that fired (from fact labels' families): how often the officer's call label
    differs from the system's."""
    rule_of: dict[tuple[str, str], str] = {}
    for f in facts:
        if f.rule_id:
            rule_of[(f.call_id, f.family)] = f.rule_id
    per: dict[str, list[bool]] = {}
    for c in calls.values():
        fam = c.system_family
        rid = rule_of.get((c.call_id, fam or ""))
        if rid and c.system_label in LABELS:
            per.setdefault(rid, []).append(c.label != c.system_label)
    out = []
    for rid, xs in per.items():
        lo, hi = wilson(sum(xs), len(xs))
        out.append({"rule": rid, "n": len(xs), "corrected": sum(xs), "rate": round(sum(xs) / len(xs), 4),
                    "ci": [lo, hi]})
    return sorted(out, key=lambda r: (-r["rate"], -r["n"], r["rule"]))


def readiness(labels: LabelSet, *, whisper_hours: float = 0.0) -> list[dict[str, Any]]:
    """The four learning steps: have / need / status / honest note. Counts only labels that may be used
    for the step (calibration: no holdout; training: ``train`` use only, never case or demo labels)."""
    cal_calls = [c for c in labels.calls.values() if (c.call_use or c.use) in hy.CALIBRATION]
    fam = Counter()
    for c in cal_calls:
        for f in {*c.families, *([c.system_family] if c.system_family else [])}:
            fam[f] += 1
    fam_min = min(fam.values()) if fam else 0
    fam_ready = sum(1 for n in fam.values() if n >= NEED_FAMILY)
    confirmed = Counter((f.family, f.fact) for f in labels.facts if f.agrees is True)
    fewshot_ready = sum(1 for n in confirmed.values() if n >= NEED_FEWSHOT)
    n_questions = len({(f.family, f.fact) for f in labels.facts}) or 20  # policy table: 20 facts
    trainable = sum(1 for f in labels.facts if f.use in hy.TRAINABLE)
    demo = labels.store == "demo"
    return [
        {"key": "calibration", "title": "Schwelle / Kalibrierung", "stage": "jetzt",
         "have": len(cal_calls), "need": 10, "unit": "bewertete Anrufe (ohne Holdout)",
         "progress": min(1.0, len(cal_calls) / 10), "ready": len(cal_calls) >= 10,
         "detail": {"per_family": dict(sorted(fam.items())), "families_ready": fam_ready,
                    "need_per_family": NEED_FAMILY, "min_family": fam_min},
         "note": (f"Globale Schwelle: ab 10 Anrufen als Vorschlag mit Kreuzvalidierung. Pro Familie braucht es "
                  f"~{NEED_FAMILY} Labels; {fam_ready} von {len(fam) or 0} Familien erreichen das. "
                  "Erwartung ehrlich: die Fakten-Scores sind fast diskret (Schwelle 0.45-0.65 entscheidet gleich), "
                  "der Effekt ist meist «kein messbarer Unterschied».")},
        {"key": "fewshot", "title": "Few-shot-Beispiele aus bestätigten Fällen", "stage": "gemessen: nein",
         "have": fewshot_ready, "need": n_questions,
         "unit": f"Fragen mit >= {NEED_FEWSHOT} bestätigten Antworten",
         "progress": min(1.0, fewshot_ready / n_questions), "ready": False,
         "note": ("Auf den Dev-Anrufen bereits gemessen (S2, fold-sauber): AUC 0.80 statt 0.87 mit den "
                  "abgestimmten Fragen, 0.70 mit umformulierten (-0.17, echt). Few-shot bleibt aus, auch wenn "
                  "genug Beispiele da sind.")},
        {"key": "lora", "title": "LoRA-Feintuning des Faktenlesers (Kev / Qwen)", "stage": "Roadmap",
         "have": trainable, "need": NEED_LORA, "unit": "trainierbare Fakten-Labels (nur neue, echte Anrufe)",
         "progress": min(1.0, trainable / NEED_LORA), "ready": trainable >= NEED_LORA,
         "note": ("Kev upstream: ~1000 Datensätze für +5 Punkte messbar, 400 lagen im Rauschen. Fall-Anrufe "
                  "zählen nie (nur Evaluation)" + ("; Demo-Feedback zählt nie." if demo else ".")
                  + " Aktivierung nur nach Schatten-Test (finetune/README.md).")},
        {"key": "whisper", "title": "Whisper-Feintuning (Spracherkennung)", "stage": "Roadmap",
         "have": whisper_hours, "need": NEED_WHISPER_HOURS, "unit": "Stunden echter Aufnahmen mit korrigiertem Transkript",
         "progress": min(1.0, whisper_hours / NEED_WHISPER_HOURS), "ready": whisper_hours >= NEED_WHISPER_HOURS,
         "note": ("Braucht echte Bank-Aufnahmen (Telefon-Codec, echte Anrufende) mit korrigierten Transkripten. "
                  "ORACLE-Messung: perfekte Transkripte bringen nur +0.03-0.05 AUC, die Spracherkennung ist "
                  "derzeit nicht der Engpass.")},
    ]
