"""Evidence hit rate (evaluation only): script-turn -> ASR alignment, hits @1/@3, bootstrap, keyword anchors,
the misheard 2x2, and that the pipeline never imports the label-reading module. Offline, synthetic data."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from callguard import eval_evidence as ee
from callguard.config import ROOT
from callguard.data import Call, Expected, Turn
from callguard.types import (
    CallResult,
    CheckResult,
    Decision,
    Finding,
    Passage,
    Segment,
    Transcript,
)

# dialect script (like the case's) and what a Standard German ASR makes of it, one segment per turn except
# T003, which the ASR splits in two, and T005 ("Ja."), which it drops
TURNS = [
    ("T001", "Beratung", "Grüezi Frau Aebi, hier isch d Claudia Frei vo de Bank. Was chan ich für Sie tue?"),
    ("T002", "Kundin", "Ich ha bis jetzt vor allem Fonds und wett mich über Aktie vo de Rigi Sensorik informiere."),
    ("T003", "Kundin", "Öppe achttuusig Franke. Mini Schwöschter schaffet det i de Finanzabteilig. Sie het mir "
                       "gseit, d Quartalszahle sind viel besser als erwartet und no nöd publiziert."),
    ("T004", "Beratung", "Sie händ das direkt vo Ihrer Schwöschter, nöd us ere öffentliche Meldig?"),
    ("T005", "Kundin", "Ja."),
    ("T006", "Kundin", "Drum wett ich die Aktie jetzt chaufe, vor de Meldig am Friitig."),
    ("T007", "Beratung", "De Uftrag nimm ich so nöd entgäge. Ich gib de Vorgang intern zur Klärig wiiter."),
]
SEGS = [
    (0.0, 6.0, "advisor", "Grüezi Frau Aebi, hier ist Claudia Frei von der Bank. Was kann ich für Sie tun?"),
    (6.5, 13.0, "customer", "Ich habe bis jetzt vor allem Fonds und möchte mich über Aktien der Rigi Sensorik informieren."),
    (13.5, 18.0, "customer", "Etwa 8000 Franken. Meine Schwester arbeitet dort in der Finanzabteilung."),
    (18.2, 25.0, "customer", "Sie hat mir gesagt, die Quartalszahlen sind viel besser als erwartet und noch nicht publiziert."),
    (25.5, 30.0, "advisor", "Sie haben das direkt von Ihrer Schwester, nicht aus einer öffentlichen Meldung?"),
    (31.0, 36.0, "customer", "Darum möchte ich die Aktie jetzt kaufen, vor der Meldung am Freitag."),
    (36.5, 43.0, "advisor", "Den Auftrag nehme ich so nicht entgegen. Ich gebe den Vorgang intern zur Klärung weiter."),
]


def _call(evidence: list[str], label: str = "alarm", spots: str = "") -> Call:
    turns = [Turn(id=i, speaker=sp, role="advisor" if sp == "Beratung" else "customer", text=tx) for i, sp, tx in TURNS]
    return Call(call_id="Stufe1_D02-K1", dialogue_id="Stufe1_D02", level=1, variant=1, noisy=False,
                audio_path=Path("x.wav"), turns=turns,
                expected=Expected(label=label, family="trade", event="present", reason="", open_question="",  # type: ignore[arg-type]
                                  evidence_turns=evidence, keyword_spots=spots))


def _transcript() -> Transcript:
    return Transcript(call_id="Stufe1_D02-K1", segments=[
        Segment(id=f"S{i:03d}", start=a, end=b, role=r, text=t, confidence=0.9) for i, (a, b, r, t) in enumerate(SEGS)])


def _result(passages: list[tuple[float, float]], label: str = "alarm", findings: list[Finding] | None = None) -> CallResult:
    ps = [Passage(family="trade", start=a, end=b, score=0.9) for a, b in passages]
    return CallResult(call_id="Stufe1_D02-K1", transcript=_transcript(),
                      checks={"keywords": CheckResult(check="keywords", type="keywords", findings=findings or [])},
                      decision=Decision(label=label, score=0.9, uncertainty=0.1, threshold=0.55, passages=ps))  # type: ignore[arg-type]


def test_alignment_maps_dialect_turns_to_standard_german_segments():
    call, t = _call(["T003", "T006"]), _transcript()
    al = ee.align(call.turns, t.segments)
    assert [call.turns[j].id for j in al.assignment] == ["T001", "T002", "T003", "T003", "T004", "T006", "T007"]
    assert (al.spans["T003"].start, al.spans["T003"].end) == (13.5, 25.0)
    assert al.spans["T003"].segment_ids == ["S002", "S003"]
    t5 = al.spans["T005"]  # dropped by the ASR: the gap between its neighbours, marked
    assert not t5.aligned and (t5.start, t5.end) == (30.0, 31.0)
    assert al.turn_of("S005") == "T006"


def test_tokens_fold_umlauts_numbers_and_drop_function_words():
    assert ee.content_tokens("Öppe achttuusig Franke, mini Schwöschter, zwölf Prozent") == \
        ["oppe", "achttuusig", "franke", "schwoschter", "12", "prozent"]
    assert "nicht" not in ee.content_tokens("das ist nicht publiziert") and "publiziert" in ee.content_tokens(
        "das ist nicht publiziert")


def test_hits_at_1_and_3_distance_and_padding():
    call = _call(["T003", "T006"])
    hit = ee.call_row(_result([(14.0, 18.0), (40.0, 42.0)]), call)
    assert hit["hit1"] and hit["hit3"] and hit["dist1"] is None and hit["family_match1"]
    later = ee.call_row(_result([(37.0, 42.0), (0.0, 2.0), (31.5, 35.0)]), call)
    assert not later["hit1"] and later["hit3"] and later["dist1"] == pytest.approx(1.0)
    assert later["hit1_pad"]  # the 2 s context of the snippet reaches T006 (ends 36.0)
    far = ee.call_row(_result([(0.0, 3.0)]), call)
    assert not far["hit1"] and not far["hit3"] and far["dist1"] == pytest.approx(10.5) and not far["hit1_pad"]
    none = ee.call_row(_result([]), call)
    assert none["n_passages"] == 0 and not none["hit1"] and none["dist1"] is None and none["chance1"] is None
    assert 0.0 < hit["chance1"] < 1.0


def test_chance_hit_baseline():
    span = [ee.TurnSpan("T1", 0.0, 100.0)]
    assert ee.chance_hit(5.0, span, 0.0, 100.0) == 1.0
    small = [ee.TurnSpan("T1", 45.0, 55.0)]
    assert ee.chance_hit(10.0, small, 0.0, 100.0) == pytest.approx(20 / 90, abs=0.02)


def test_summary_counts_only_true_flags_and_bootstraps_over_dialogues():
    rows = []
    for i in range(6):
        rows.append({"call_id": f"D{i}-K1", "dialogue_id": f"D{i}", "group": f"D{i}", "family": "trade",
                     "expected": "alarm", "predicted": "alarm", "n_passages": 1, "hit1": i < 4, "hit1_pad": i < 4,
                     "hit3": True, "hit_all": True, "family_match1": True, "dist1": None if i < 4 else 5.0,
                     "chance1": 0.2, "len1": 10.0})
    rows.append({**rows[0], "call_id": "N-K1", "dialogue_id": "N", "group": "N", "expected": "no_alert"})
    s = ee.summarize(rows, n_boot=500)
    a = s["all"]
    assert a["n"] == 6 and a["hit1"]["k"] == 4 and a["hit1"]["value"] == pytest.approx(0.6667, abs=1e-3)
    assert a["hit1"]["lo"] <= a["hit1"]["value"] <= a["hit1"]["hi"] and a["hit3"]["lo"] == 1.0
    assert a["median_dist1"] == 5.0 and a["chance1"] == 0.2 and s["n_flagged"] == 7


def test_keyword_anchor_check_uses_unique_annotated_turns():
    spots = "K04 'vor de Meldig' T006 K relevant; K03 'Quartalszahle' T003 K relevant; K03 'Quartalszahle' T007 B benign"
    call = _call(["T003", "T006"], spots=spots)
    fs = [Finding(check="keywords", family="trade", score=0.35, segment_ids=["S005"], detail={"keyword_id": "K04"}),
          Finding(check="keywords", family="trade", score=0.35, segment_ids=["S003"], detail={"keyword_id": "K03"})]
    r = _result([(31.0, 36.0)], findings=fs)
    al = ee.align(call.turns, r.transcript.segments)
    anchors = ee.keyword_anchor_check(r, call, al)
    assert [(a["keyword_id"], a["want"], a["got"], a["exact"]) for a in anchors] == [("K04", "T006", "T006", True)]


def test_fisher_exact_matches_reference_values():
    assert ee.fisher_exact(1, 9, 11, 3) == pytest.approx(0.002759, abs=1e-5)  # Fisher's textbook table
    assert ee.fisher_exact(3, 3, 3, 3) == pytest.approx(1.0)


def test_misheard_table_counts_wrong_vs_right():
    def row(exp: str, pred: str, low: bool) -> dict:
        return {"expected": exp, "predicted": pred, "n_passages": 1,
                "passages": [{"misheard": low}, {"misheard": True}]}
    rows = [row("no_alert", "alarm", True), row("alarm", "alarm", False), row("alarm", "review", True),
            row("review", "review", False), row("alarm", "no_alert", True)]  # last one: not flagged
    t = ee.misheard_table(rows, top=1)
    assert t["n"] == 4
    assert {k: t["label"][k] for k in ("wrong_low", "wrong_ok", "right_low", "right_ok")} == \
        {"wrong_low": 2, "wrong_ok": 0, "right_low": 0, "right_ok": 2}
    assert t["flag"]["wrong_low"] == 1 and t["flag"]["right_low"] == 1
    assert ee.misheard_table(rows, top=2)["label"]["right_low"] == 2


def test_evaluate_variant_drops_holdout_dialogues():
    call = _call(["T003"])
    ev = ee.evaluate_variant("x", [_result([(14.0, 18.0)])], [call], holdout=["Stufe1_D02"], n_boot=50)
    assert ev.rows == [] and ev.dropped_holdout == ["Stufe1_D02-K1"]
    ev = ee.evaluate_variant("x", [_result([(14.0, 18.0)])], [call], n_boot=50)
    assert ev.summary["all"]["hit1"]["k"] == 1
    assert "Evidence hit rate" in ee.render_markdown([ev], 0.6)


def test_pipeline_code_never_imports_the_label_reading_evaluation():
    src = ROOT / "src" / "callguard"
    offenders = [p.relative_to(src).as_posix() for p in src.rglob("*.py")
                 if p.name not in ("eval_evidence.py", "evidence_eval.py")
                 and re.search(r"\beval_evidence\b", p.read_text(encoding="utf-8"))]
    assert offenders == []
