"""Hand-built, realistic CallResults for the UI tests, written the way the json_dir sink writes them.

Three calls cover the officer's cases: an insider-trading alarm with two passages (like the case's
Stufe1_D02), a harmless call with keyword hits that stays no_alert (published quarterly figures) and an
undecidable access case that goes to review. Built by hand so the UI tests don't depend on the check or
fusion plugins being finished; a tiny case-style data folder (audio, expected labels, one script)
makes the quality view and the offline "process a call" flow testable too.
"""

from __future__ import annotations

import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from callguard.audio import SR, cut
from callguard.config import ROOT
from callguard.types import (
    CallResult,
    CheckResult,
    Decision,
    FamilyScore,
    Finding,
    FusedFamily,
    Passage,
    Segment,
    Transcript,
)

FAMILY_LABELS = {
    "numbers": "Zahlenobjekte (Karten- und Referenznummern)",
    "trade": "Insiderhandel (Information und Kaufwunsch)",
    "access": "Zugangsinformation preisgegeben",
    "disclosure": "Auskunft an Dritte",
    "documentation": "Relevante Angabe verschweigen",
    "splitting": "Zuständigkeit/Kontrolle umgehen (Aufteilen)",
}
ALARM_ID, HARMLESS_ID, REVIEW_ID, UNPROCESSED_ID = "Stufe1_D02-K1", "Stufe1_D03-K1", "Stufe3_C17-K3", "Stufe1_D01-K1"
EXPECTED = {ALARM_ID: ("alarm", "trade"), HARMLESS_ID: ("no_alert", "trade"), REVIEW_ID: ("review", "access"),
            UNPROCESSED_ID: ("no_alert", "numbers")}


@dataclass
class FixtureEnv:
    root: Path
    runs_dir: Path  # runs/<config name>, where result.json files live
    data_dir: Path
    keywords: Path
    criteria: Path
    config: str
    sets: list[str]

    @property
    def args(self) -> str:
        """Value for ``CALLGUARD_ARGS``."""
        return " ".join(["--config", self.config, *(f"--set {shlex.quote(s)}" for s in self.sets)])

    def result_path(self, call_id: str) -> Path:
        return self.runs_dir / call_id / "result.json"


# --------------------------------------------------------------------------------------------
# building blocks
# --------------------------------------------------------------------------------------------


def _segments(rows: list[tuple[float, float, str, str]]) -> list[Segment]:
    return [Segment(id=f"S{i:03d}", start=a, end=b, role=role, speaker="SPK0" if role == "advisor" else "SPK1",
                    text=text, confidence=0.9) for i, (a, b, role, text) in enumerate(rows)]


def _fused(scores: dict[str, tuple[float, float, dict[str, float], dict[str, str | None], str]]) -> dict[str, FusedFamily]:
    out = {}
    for fid, label in FAMILY_LABELS.items():
        score, unc, per_check, verdicts, reason = scores.get(fid, (0.0, 0.3, {}, {}, ""))
        out[fid] = FusedFamily(family=fid, label=label, score=score, uncertainty=unc, per_check=per_check,
                               verdicts=verdicts, reason=reason)
    return out


def _flat(check: str, families: list[str], score: float, conf: float, reason: str,
          verdict: str | None = None) -> dict[str, FamilyScore]:
    return {f: FamilyScore(score=score, confidence=conf, verdict=verdict, reason=reason) for f in families}


def _kw_finding(fid: str, kid: str, phrase: str, label: str, seg: Segment, harmless: str) -> Finding:
    i = seg.text.lower().find(phrase.lower())
    frac = max(i, 0) / max(len(seg.text), 1)
    start = round(seg.start + frac * (seg.end - seg.start), 2)
    return Finding(check="keywords", family=fid, score=0.35, segment_ids=[seg.id], start=start,
                   end=round(start + 1.2, 2), reason=f"Stichwort {kid} «{phrase}» ({label})",
                   detail={"keyword_id": kid, "phrase": phrase, "matched_text": phrase, "fuzzy_score": 100.0,
                           "negated": False, "harmless": harmless})


ALL = list(FAMILY_LABELS)
ALARMING = [f for f in ALL if f != "numbers"]


# --------------------------------------------------------------------------------------------
# the three calls
# --------------------------------------------------------------------------------------------


def alarm_call(audio_path: str | None) -> CallResult:
    """Insider trading: the customer wants to buy before the publication, citing her sister's
    unpublished quarterly figures. Two passages: the information and the buy wish."""
    segs = _segments([
        (0.0, 7.5, "advisor", "Grüezi Frau Aebi, hier ist Claudia Frei. Sie haben um einen Rückruf wegen Ihres "
                              "Wertschriftendepots gebeten."),
        (8.0, 17.0, "customer", "Ich habe bis jetzt vor allem Fonds und möchte mich über einzelne Aktien "
                                "informieren. Es geht um die Rigi Sensorik."),
        (17.5, 24.0, "advisor", "Haben Sie schon einen Betrag im Kopf, und woher kommt das Interesse an dieser Firma?"),
        (24.5, 38.0, "customer", "Etwa achttausend Franken. Meine Schwester arbeitet dort in der Finanzabteilung. "
                                 "Sie hat mir gestern gesagt, die Quartalszahlen sind viel besser als erwartet. "
                                 "Die sind noch nicht publiziert."),
        (38.5, 43.0, "advisor", "Sie haben das direkt von Ihrer Schwester, nicht aus einer öffentlichen Meldung?"),
        (43.5, 50.0, "customer", "Ja. Sie hat gesagt, ich soll es vertraulich behandeln. Unter uns, sie hat mir "
                                 "sogar ein Foto der Übersicht gezeigt."),
        (50.5, 58.0, "advisor", "Ich stoppe hier kurz die normale Auftragsbesprechung. Was genau möchten Sie jetzt "
                                "von mir?"),
        (58.5, 68.0, "customer", "Gerade darum möchte ich diese Aktie jetzt kaufen vor der Meldung. Wenn alle am "
                                 "Freitag die Quartalszahlen sehen, ist der Preis doch schon oben."),
        (68.5, 75.0, "advisor", "Den Auftrag nehme ich so nicht entgegen. Ich gebe den Vorgang intern zur Klärung "
                                "weiter."),
    ])
    t = Transcript(call_id=ALARM_ID, audio_path=audio_path, duration=76.0, language="de", segments=segs,
                   asr_backend="faster_whisper:whisper-turbo-gsw-ct2-int8")
    harmless = "Die Aussage ist negiert, zitiert oder betrifft bereits veröffentlichte Angaben."
    kw_findings = [
        _kw_finding("trade", "K02", "Finanzabteilung", "Interne Quelle", segs[3], harmless),
        _kw_finding("trade", "K03", "Quartalszahlen", "Marktrelevanter Inhalt", segs[3], harmless),
        _kw_finding("trade", "K01", "noch nicht publiziert", "Nicht öffentliche Information", segs[3], harmless),
        _kw_finding("trade", "K05", "vertraulich", "Vertraulichkeit", segs[5], harmless),
        _kw_finding("trade", "K04", "vor der Meldung", "Handeln vor der Meldung", segs[7], harmless),
    ]
    judge_reason = ("Kundin will die Aktie ausdrücklich vor der Meldung kaufen und begründet das mit "
                    "unveröffentlichten Quartalszahlen ihrer Schwester aus der Finanzabteilung.")
    checks = {
        "keywords": CheckResult(check="keywords", type="keywords", findings=kw_findings, family_scores={
            **_flat("keywords", ALL, 0.0, 0.25, "Keine Stichwörter gefunden"),
            "trade": FamilyScore(score=0.88, confidence=0.4, reason="Stichwörter: K02 «Finanzabteilung», K03 "
                                 "«Quartalszahlen», K01 «noch nicht publiziert», K05 «vertraulich», K04 «vor der Meldung»",
                                 segment_ids=["S003", "S005", "S007"])}, meta={"seconds": 0.03}),
        "patterns": CheckResult(check="patterns", type="patterns", family_scores=_flat(
            "patterns", ["access", "numbers"], 0.0, 0.2, "Keine auffälligen Ziffernfolgen gefunden"),
            meta={"seconds": 0.01}),
        "llm_judge": CheckResult(check="llm_judge", type="llm_judge", findings=[
            Finding(check="llm_judge", family="trade", score=0.92, segment_ids=["S007"], start=58.5, end=68.0,
                    reason=judge_reason),
            Finding(check="llm_judge", family="trade", score=0.85, segment_ids=["S003", "S005"], start=24.5,
                    end=50.0, reason="Information stammt aus der Finanzabteilung, ist noch nicht publiziert und "
                                     "ausdrücklich vertraulich."),
        ], family_scores={
            **_flat("llm_judge", ALARMING, 0.05, 0.9, "Keine Hinweise im Gespräch.", "absent"),
            "trade": FamilyScore(score=0.92, confidence=0.85, verdict="present", reason=judge_reason,
                                 segment_ids=["S003", "S005", "S007"]),
        }, meta={"model": "qwen2.5-1.5b-instruct", "seconds": 41.2}),
        "geval": CheckResult(check="geval", type="geval", family_scores={
            **_flat("geval", ALARMING, 0.06, 0.7, "G-Eval 1.2/5"),
            "trade": FamilyScore(score=0.8, confidence=0.7, reason="G-Eval 4.2/5", segment_ids=["S007"]),
        }, meta={"model": "qwen2.5-1.5b-instruct", "seconds": 23.5}),
    }
    passages = [
        Passage(family="trade", family_label=FAMILY_LABELS["trade"], start=58.5, end=68.0, segment_ids=["S007"],
                score=0.92, checks=["llm_judge", "geval", "keywords"], text=segs[7].text,
                reasons=[f"llm_judge: {judge_reason}", "keywords: Stichwort K04 «vor der Meldung» (Handeln vor der "
                                                       "Meldung)"]),
        Passage(family="trade", family_label=FAMILY_LABELS["trade"], start=24.5, end=50.0,
                segment_ids=["S003", "S004", "S005"], score=0.85, checks=["llm_judge", "keywords"],
                text=" ".join(s.text for s in segs[3:6]),
                reasons=["llm_judge: Information stammt aus der Finanzabteilung, ist noch nicht publiziert und "
                         "ausdrücklich vertraulich.", "keywords: Stichwort K02 «Finanzabteilung» (Interne Quelle)"]),
    ]
    decision = Decision(
        label="alarm", score=0.86, uncertainty=0.12, threshold=0.55, passages=passages,
        families=_fused({"trade": (0.86, 0.12, {"keywords": 0.88, "llm_judge": 0.92, "geval": 0.8},
                                   {"keywords": None, "llm_judge": "present", "geval": None}, judge_reason),
                         "access": (0.05, 0.1, {"keywords": 0.0, "patterns": 0.0, "llm_judge": 0.05, "geval": 0.06},
                                    {"llm_judge": "absent"}, "Keine Hinweise im Gespräch.")}),
        reasons=["Alarm: Score 0.86 für 'Insiderhandel' >= Schwelle 0.55 bei Unsicherheit 0.12 (max. 0.35).",
                 f"Insiderhandel: {judge_reason}"])
    return CallResult(call_id=ALARM_ID, audio_path=audio_path, transcript=t, checks=checks, decision=decision,
                      timings={"asr": 71.3, "diarize": 6.2, "checks": 64.9}, config_name="local")


def harmless_call(audio_path: str | None) -> CallResult:
    """Keyword hits ('Quartalszahlen') but the figures are public: the LLM checks clear it."""
    segs = _segments([
        (0.0, 6.0, "advisor", "Guten Tag Herr Keller, Sie wollten über die Quartalszahlen der Alpina Holding sprechen?"),
        (6.5, 14.0, "customer", "Ja, die Quartalszahlen sind seit gestern veröffentlicht, ich habe den Bericht in "
                                "der Zeitung gelesen."),
        (14.5, 21.0, "advisor", "Genau, die Medienmitteilung ist öffentlich. Möchten Sie aufgrund des Berichts etwas "
                                "anpassen?"),
        (21.5, 29.0, "customer", "Ich überlege, Aktien zu kaufen, aber nur wenn die Zahlen mit dem Vorjahr "
                                 "vergleichbar sind."),
        (29.5, 36.0, "advisor", "Die zwei Berichte haben verschiedene Bezugsperioden; ich schicke Ihnen beide."),
    ])
    t = Transcript(call_id=HARMLESS_ID, audio_path=audio_path, duration=37.0, language="de", segments=segs,
                   asr_backend="faster_whisper:whisper-turbo-gsw-ct2-int8")
    harmless = "Öffentliche Unternehmensmeldungen werden sachlich erläutert."
    reason = "Kaufwunsch beruht auf veröffentlichten Quartalszahlen; keine Insiderinformation."
    checks = {
        "keywords": CheckResult(check="keywords", type="keywords", findings=[
            _kw_finding("trade", "K03", "Quartalszahlen", "Marktrelevanter Inhalt", segs[0], harmless),
            _kw_finding("trade", "K03", "Quartalszahlen", "Marktrelevanter Inhalt", segs[1], harmless),
        ], family_scores={**_flat("keywords", ALL, 0.0, 0.25, "Keine Stichwörter gefunden"),
                          "trade": FamilyScore(score=0.7, confidence=0.4, reason="Stichwörter: K03 «Quartalszahlen» (2×)",
                                               segment_ids=["S000", "S001"])}),
        "patterns": CheckResult(check="patterns", type="patterns", family_scores=_flat(
            "patterns", ["access", "numbers"], 0.0, 0.2, "Keine auffälligen Ziffernfolgen gefunden")),
        "llm_judge": CheckResult(check="llm_judge", type="llm_judge", family_scores={
            **_flat("llm_judge", ALARMING, 0.05, 0.9, "Keine Hinweise im Gespräch.", "absent"),
            "trade": FamilyScore(score=0.08, confidence=0.9, verdict="absent", reason=reason)}),
        "geval": CheckResult(check="geval", type="geval", family_scores={
            **_flat("geval", ALARMING, 0.05, 0.6, "G-Eval 1.2/5"),
            "trade": FamilyScore(score=0.12, confidence=0.6, reason="G-Eval 1.5/5")}),
    }
    decision = Decision(
        label="no_alert", score=0.15, uncertainty=0.3, threshold=0.55, passages=[],
        families=_fused({"trade": (0.15, 0.3, {"keywords": 0.7, "llm_judge": 0.08, "geval": 0.12},
                                   {"llm_judge": "absent"}, reason)}),
        reasons=["Kein Alarm: höchster Score 0.15 ('Insiderhandel') liegt unter 0.40 (Schwelle 0.55 minus Band 0.15).",
                 f"Insiderhandel: {reason}"])
    return CallResult(call_id=HARMLESS_ID, audio_path=audio_path, transcript=t, checks=checks, decision=decision,
                      config_name="local")


def review_call(audio_path: str | None) -> CallResult:
    """A code is read out from a cut-off screenshot; whether it is still valid stays open -> review."""
    segs = _segments([
        (0.0, 5.0, "advisor", "Guten Tag, hier ist der Support der Bank. Wie kann ich helfen?"),
        (5.5, 14.0, "customer", "Ich komme beim E-Banking nicht weiter, auf dem Screenshot ist nur ein Teil des "
                                "Codes zu sehen."),
        (14.5, 18.0, "advisor", "Bitte lesen Sie mir keine Codes vor."),
        (18.5, 27.0, "customer", "Da steht vier sieben eins neun, der Rest ist abgeschnitten. Ich weiss nicht, ob "
                                 "der noch gilt."),
        (27.5, 35.0, "advisor", "Ich kann nicht beurteilen, zu welchem Vorgang das gehört. Wir sperren "
                                "sicherheitshalber den Zugang."),
    ])
    t = Transcript(call_id=REVIEW_ID, audio_path=audio_path, duration=36.0, language="de", segments=segs,
                   asr_backend="faster_whisper:whisper-turbo-gsw-ct2-int8")
    reason = "Ein Wert wird vorgelesen, aber ob er gültig ist und zu welchem Vorgang er gehört, bleibt offen."
    checks = {
        "keywords": CheckResult(check="keywords", type="keywords", findings=[
            _kw_finding("access", "K10", "Codes", "Zugangsgeheimnis", segs[1], "Nur Erwähnung oder Warnung."),
        ], family_scores={**_flat("keywords", ALL, 0.0, 0.25, "Keine Stichwörter gefunden"),
                          "access": FamilyScore(score=0.35, confidence=0.4, reason="Stichwort K10 «Codes»",
                                                segment_ids=["S001"])}),
        "patterns": CheckResult(check="patterns", type="patterns", findings=[
            Finding(check="patterns", family="access", score=0.6, segment_ids=["S003"], start=18.5, end=22.0,
                    reason="4-stellige Ziffernfolge «4719» nahe «Code»", detail={"digits": "4719"}),
        ], family_scores={"access": FamilyScore(score=0.6, confidence=0.5, reason="Ziffernfolge nahe «Code»",
                                                segment_ids=["S003"]),
                          "numbers": FamilyScore(score=0.4, confidence=0.5, reason="4 Ziffern: möglicher Code")}),
        "llm_judge": CheckResult(check="llm_judge", type="llm_judge", family_scores={
            **_flat("llm_judge", ALARMING, 0.05, 0.9, "Keine Hinweise im Gespräch.", "absent"),
            "access": FamilyScore(score=0.5, confidence=0.5, verdict="undetermined", reason=reason,
                                  segment_ids=["S003"])}),
        "geval": CheckResult(check="geval", type="geval", family_scores={
            **_flat("geval", ALARMING, 0.05, 0.6, "G-Eval 1.2/5"),
            "access": FamilyScore(score=0.45, confidence=0.5, reason="G-Eval 2.8/5")}),
    }
    passages = [Passage(family="access", family_label=FAMILY_LABELS["access"], start=18.5, end=27.0,
                        segment_ids=["S003"], score=0.6, checks=["patterns", "llm_judge"], text=segs[3].text,
                        reasons=["patterns: 4-stellige Ziffernfolge «4719» nahe «Code»", f"llm_judge: {reason}"])]
    decision = Decision(
        label="review", score=0.47, uncertainty=0.32, threshold=0.55, passages=passages,
        families=_fused({"access": (0.47, 0.32, {"keywords": 0.35, "patterns": 0.6, "llm_judge": 0.5, "geval": 0.45},
                                    {"llm_judge": "undetermined"}, reason)}),
        reasons=["Prüfen (knapp unter Schwelle): Score 0.47 für 'Zugangsinformation preisgegeben' liegt zwischen "
                 "0.40 und der Schwelle 0.55.", f"Zugangsinformation preisgegeben: {reason}"])
    return CallResult(call_id=REVIEW_ID, audio_path=audio_path, transcript=t, checks=checks, decision=decision,
                      config_name="local")


# --------------------------------------------------------------------------------------------
# on disk
# --------------------------------------------------------------------------------------------


def _write_audio(path: Path, seconds: float, seed: int) -> None:
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    tone = 0.05 * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 0.25 * t) > 0)
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), (tone + 0.005 * rng.standard_normal(n)).astype(np.float32), SR, subtype="PCM_16")


def _expected_file(call_id: str, label: str, family: str) -> str:
    dlg = call_id.split("-K")[0]
    return (f"{dlg.split('_')[1]} · Testanruf\nKurzbeschreibung.\nTestziel: {family}\nEreignis: present\n"
            f"Bearbeitung: {label}\nBegründung: Erwartete Bewertung für den UI-Test.\nOffen: keine\n\n"
            f"T001 · Beratung\nGrüezi.\n")


REFERENCE_SCRIPT = """T001 · Beratung
Grüezi, da isch d Simone Wenger vom Service-Team. Passt es grad für en Rückruf?

T002 · Kundin
Ja. Ich gseh de Betrag zweimal uf de Kreditkarte.

T003 · Beratung
Das cha e Reservation sii. Bitte läsed mir kei Code vor.

T004 · Kundin
Guet, denn warte ich no.
"""


def write_fixture_env(root: Path, config: str = "local", with_snippet: bool = True) -> FixtureEnv:
    """Results, a case-style data folder, editable copies of keywords/criteria and the ``--set`` list that
    points the UI at all of it (plus a fake LLM, so nothing in the tests can reach a server)."""
    root = Path(root)
    data = root / "data"
    audio = {cid: data / "Audio" / f"{cid}.wav" for cid in EXPECTED}
    for i, (cid, secs) in enumerate([(ALARM_ID, 78), (HARMLESS_ID, 38), (REVIEW_ID, 37), (UNPROCESSED_ID, 12)]):
        _write_audio(audio[cid], secs, seed=i)
    for cid, (label, family) in EXPECTED.items():
        p = data / "Skript_mit_Sollbewertung" / f"{cid.split('-K')[0]}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_expected_file(cid, label, family))
    (data / "Transkript").mkdir(parents=True, exist_ok=True)
    (data / "Transkript" / f"{UNPROCESSED_ID.split('-K')[0]}.txt").write_text(REFERENCE_SCRIPT)

    cfg_dir = root / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    keywords, criteria = cfg_dir / "keywords.json", cfg_dir / "criteria.yaml"
    shutil.copy(ROOT / "config" / "keywords.json", keywords)
    shutil.copy(ROOT / "config" / "criteria.yaml", criteria)

    runs_root = root / "runs"
    runs_dir = runs_root / config
    results = [alarm_call(str(audio[ALARM_ID])), harmless_call(str(audio[HARMLESS_ID])),
               review_call(str(audio[REVIEW_ID]))]
    for r in results:
        out = runs_dir / r.call_id / "result.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        if with_snippet and r.decision.passages:  # first passage pre-cut like the pipeline does, others not
            p = r.decision.passages[0]
            snip = cut(r.audio_path, p.start, p.end, out.parent / "snippets" / f"00_{p.family}_{int(p.start)}s.wav",
                       pad=2.0)
            p.snippet_path = str(snip)
        out.write_text(r.model_dump_json(indent=1))

    sets = [f"paths.runs_dir={runs_root}", f"paths.data_dir={data}", f"paths.keywords={keywords}",
            f"paths.criteria={criteria}", f"paths.cache_dir={root / 'cache'}", "llms.default={type: fake}"]
    return FixtureEnv(root=root, runs_dir=runs_dir, data_dir=data, keywords=keywords, criteria=criteria,
                      config=config, sets=sets)
