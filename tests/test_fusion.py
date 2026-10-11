from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from callguard import registry
from callguard.fusion import top_family
from callguard.fusion.weighted import WeightedFusion
from callguard.types import CheckResult, Family, FamilyScore, Finding, Segment, Transcript

FAMILIES = [
    Family(id="trade", label="Insiderhandel (Information und Kaufwunsch)"),
    Family(id="access", label="Zugangsinformation preisgegeben"),
    Family(id="numbers", label="Zahlenobjekte", can_alarm=False),
]


def transcript(n: int = 12) -> Transcript:
    return Transcript(call_id="C1", segments=[
        Segment(id=f"S{i:03d}", start=10.0 * i, end=10.0 * i + 8.0, text=f"Satz {i}.") for i in range(n)])


def fs(score: float, conf: float = 1.0, verdict: str | None = None, reason: str = "", segs=()) -> FamilyScore:
    return FamilyScore(score=score, confidence=conf, verdict=verdict, reason=reason, segment_ids=list(segs))


def res(name: str, findings=(), meta=None, **scores: FamilyScore) -> CheckResult:
    return CheckResult(check=name, type=name, family_scores=scores, findings=list(findings), meta=meta or {})


def fusion(**kw) -> WeightedFusion:
    return WeightedFusion(SimpleNamespace(cfg=None), **kw)


def decide(results: list[CheckResult], overrides=None, **kw):
    return fusion(**kw).decide(transcript(), {r.check: r for r in results}, FAMILIES, overrides)


# -- family math ---------------------------------------------------------------------------------


def test_weighted_mean_disagreement_and_uncertainty():
    d = decide([res("llm", trade=fs(0.8, 1.0)), res("kw", trade=fs(0.2, 0.5))],
               {"weights": {"llm": 1.0, "kw": 0.5}})
    tr = d.families["trade"]
    # effective weights 1.0 and 0.25 -> mean 0.68; weighted std 0.24 -> disagreement 0.48
    assert tr.score == pytest.approx(0.68, abs=1e-4)
    mean_conf = (1.0 * 1.0 + 0.5 * 0.5) / 1.5
    assert tr.uncertainty == pytest.approx(0.5 * 0.48 + 0.5 * (1 - mean_conf), abs=1e-3)
    assert tr.per_check == {"llm": 0.8, "kw": 0.2}
    assert d.score == tr.score and d.uncertainty == tr.uncertainty


def test_low_confidence_counts_little_but_not_zero():
    d = decide([res("a", trade=fs(1.0, 0.0)), res("b", trade=fs(0.0, 1.0))])
    assert d.families["trade"].score == pytest.approx(0.05 / 1.05, abs=1e-4)


def test_reason_from_highest_weight_check_with_text():
    d = decide([res("kw", trade=fs(0.9, reason="Stichwort Quartalszahlen")),
                res("llm", trade=fs(0.7, reason="")),
                res("judge", trade=fs(0.6, reason="Kaufwunsch vor der Meldung"))],
               {"weights": {"kw": 0.3, "llm": 1.0, "judge": 0.8}})
    assert d.families["trade"].reason == "Kaufwunsch vor der Meldung"


def test_reason_prefers_an_explanation_over_a_bare_score_at_equal_weight():
    d = decide([res("geval", trade=fs(0.4, reason="G-Eval 2.60/5")),
                res("judge", trade=fs(0.1, reason="Die Kundin erklärt nur die Begriffe, kein Kaufwunsch."))],
               {"weights": {"geval": 1.0, "judge": 1.0}})
    assert d.families["trade"].reason.startswith("Die Kundin")


def test_family_without_any_score_is_unknown_not_safe():
    d = decide([res("llm", trade=fs(0.1))])
    assert d.families["access"].score == 0.0
    assert d.families["access"].uncertainty == 1.0
    assert top_family(d, {"trade", "access"}) == "trade"


# -- labels --------------------------------------------------------------------------------------


def test_alarm_above_threshold():
    d = decide([res("llm", trade=fs(0.9, reason="Kauf vor Bekanntgabe")), res("kw", trade=fs(0.8))])
    assert d.label == "alarm"
    assert d.reasons[0].startswith("Alarm: Score 0.8")
    assert any("Kauf vor Bekanntgabe" in r for r in d.reasons)


def test_unsure_alarm_becomes_review():
    d = decide([res("llm", trade=fs(0.95, 0.3)), res("kw", trade=fs(0.9, 0.3))])
    assert d.score >= 0.55 and d.uncertainty > 0.35
    assert d.label == "review"
    assert "unsicher" in d.reasons[0]


def test_review_band_just_below_threshold():
    d = decide([res("llm", trade=fs(0.45))])
    assert d.label == "review"
    assert "knapp unter Schwelle" in d.reasons[0]
    assert decide([res("llm", trade=fs(0.39))]).label == "no_alert"


def test_undetermined_verdict_from_strong_check_opens_review():
    d = decide([res("llm", access=fs(0.3, verdict="undetermined", reason="Gültigkeit des Codes unklar"))])
    assert d.label == "review"
    assert "offener Sachverhalt" in d.reasons[0]
    assert any("Gültigkeit des Codes unklar" in r for r in d.reasons)
    # the same hint from a weak check (weight < 0.5) does not escalate
    weak = decide([res("kw", access=fs(0.3, verdict="undetermined"))], {"weights": {"kw": 0.3}})
    assert weak.label == "no_alert"
    # and not below min_score_for_review
    assert decide([res("llm", access=fs(0.2, verdict="undetermined"))]).label == "no_alert"


def test_high_uncertainty_below_band_goes_to_review():
    d = decide([res("llm", trade=fs(0.3, 0.2))])
    assert d.uncertainty > 0.35
    assert d.label == "review"
    assert "Unsicherheit" in d.reasons[0]


def test_clear_no_alert():
    d = decide([res("llm", trade=fs(0.05), access=fs(0.0)), res("kw", trade=fs(0.1), access=fs(0.0))])
    assert d.label == "no_alert"
    assert d.reasons[0].startswith("Kein Alarm")
    assert d.passages == []


def test_numbers_family_never_alarms_and_makes_no_passages():
    f = Finding(check="kw", family="numbers", score=1.0, segment_ids=["S002"], reason="Kartennummer")
    d = decide([res("kw", [f], numbers=fs(1.0, verdict="undetermined"), trade=fs(0.0))])
    assert d.families["numbers"].score == 1.0
    assert d.label == "no_alert" and d.score == 0.0
    assert d.passages == []


def test_threshold_override_changes_label_only():
    results = [res("llm", trade=fs(0.6))]
    assert decide(results).label == "alarm"
    assert decide(results, {"threshold": 0.7}).label == "review"  # 0.6 in [0.55, 0.7)
    d = decide(results, {"threshold": 0.9, "review_band": 0.1})
    assert d.label == "no_alert" and d.threshold == 0.9


def test_weights_and_disabled_checks_overrides():
    results = [res("llm", trade=fs(0.9)), res("kw", trade=fs(0.1))]
    base = decide(results)
    assert base.families["trade"].score == pytest.approx(0.5)
    assert decide(results, {"weights": {"kw": 0.0}}).families["trade"].score == pytest.approx(0.9)
    off = decide(results, {"disabled_checks": ["llm"]})
    assert off.families["trade"].score == pytest.approx(0.1)
    assert "llm" not in off.families["trade"].per_check
    assert any("Deaktivierte Prüfungen: llm" in r for r in off.reasons)


def test_partial_weight_override_keeps_config_weights():
    ctx = SimpleNamespace(cfg=SimpleNamespace(checks=[{"name": "llm", "weight": 1.0}, {"name": "kw", "weight": 0.25}]))
    f = WeightedFusion(ctx)
    results = {"llm": res("llm", trade=fs(0.8)), "kw": res("kw", trade=fs(0.0))}
    d = f.decide(transcript(), results, FAMILIES, {"weights": {"llm": 1.0}})
    assert d.families["trade"].score == pytest.approx(0.8 / 1.25)


def test_failed_check_is_ignored_and_reported():
    d = decide([res("llm", meta={"error": "ConnectError('down')"}), res("kw", trade=fs(0.8))])
    assert d.families["trade"].per_check == {"kw": 0.8}
    assert d.label == "alarm"
    assert any("'llm' ist ausgefallen" in r for r in d.reasons)


def test_all_checks_failed_is_review_not_silence():
    d = decide([res("llm", meta={"error": "boom"}), res("kw", meta={"error": "boom"})])
    assert d.label == "review"
    assert "Keine Prüfung lieferte" in d.reasons[0]
    assert decide([]).label == "review"


def test_nan_scores_are_ignored():
    d = decide([res("llm", trade=fs(float("nan"))), res("kw", trade=fs(0.2))])
    assert d.families["trade"].score == pytest.approx(0.2)


# -- passages ------------------------------------------------------------------------------------


def test_passages_merge_resolve_and_rank():
    t = transcript()
    findings_kw = [
        Finding(check="kw", family="trade", score=0.6, segment_ids=["S002"], reason="Quartalszahlen"),
        Finding(check="kw", family="trade", score=0.7, segment_ids=["S003"], reason="vor der Meldung"),
        Finding(check="kw", family="trade", score=0.4, start=100.0, end=102.0, reason="vertraulich"),
    ]
    findings_llm = [Finding(check="llm", family="trade", score=0.9, segment_ids=["S003"],
                            reason="Kaufwunsch wegen interner Info"),
                    Finding(check="llm", family="trade", score=0.9, segment_ids=["S003"],
                            reason="Kaufwunsch wegen interner Info")]
    results = {"kw": res("kw", findings_kw, trade=fs(0.7)), "llm": res("llm", findings_llm, trade=fs(0.9))}
    d = fusion().decide(t, results, FAMILIES, None)
    assert d.label == "alarm"
    assert len(d.passages) == 2
    p = d.passages[0]
    # S002 (20-28 s) and S003 (30-38 s) are 2 s apart -> one passage with resolved times
    assert (p.start, p.end) == (20.0, 38.0)
    assert p.segment_ids == ["S002", "S003"]
    assert p.score == 0.9
    assert p.reasons == ["llm: Kaufwunsch wegen interner Info", "kw: vor der Meldung", "kw: Quartalszahlen"]
    assert p.checks == ["llm", "kw"]
    assert p.text == "Satz 2. Satz 3."
    assert p.family_label.startswith("Insiderhandel")
    # time-only finding gets the overlapping segment attached
    assert d.passages[1].segment_ids == ["S010"] and d.passages[1].score == 0.4


def test_passages_respect_max_and_disabled_checks():
    t = transcript(40)
    findings = [Finding(check="kw", family="trade", score=0.5 + i / 100, segment_ids=[f"S{3 * i:03d}"],
                        reason=f"r{i}") for i in range(10)]
    results = {"kw": res("kw", findings, trade=fs(0.8)),
               "llm": res("llm", [Finding(check="llm", family="trade", score=1.0, segment_ids=["S001"])],
                          trade=fs(0.8))}
    d = fusion(max_passages=3).decide(t, results, FAMILIES, {"disabled_checks": ["llm"]})
    assert [p.score for p in d.passages] == [0.59, 0.58, 0.57]
    assert all("llm" not in p.checks for p in d.passages)


def test_passages_of_the_top_family_come_first():
    kw = Finding(check="kw", family="trade", score=0.35, segment_ids=["S002"], reason="Finanzabteilung")
    llm = Finding(check="llm", family="access", score=1.0, segment_ids=["S008"], reason="Code vorgelesen")
    d = decide([res("kw", [kw], trade=fs(0.9)), res("llm", [llm], access=fs(0.6))], max_passages=1)
    assert d.top_family == "trade" and [p.family for p in d.passages] == ["trade"]


def test_overlong_passage_is_cut_to_a_window_around_short_evidence():
    t = transcript(40)  # segments every 10 s
    llm = Finding(check="llm", family="trade", score=1.0, segment_ids=[f"S{i:03d}" for i in range(2, 30)],
                  reason="Kaufwunsch")
    kw = Finding(check="kw", family="trade", score=0.35, start=152.0, end=153.0, reason="vor der Meldung")
    d = fusion(max_passage_seconds=60).decide(
        t, {"llm": res("llm", [llm], trade=fs(0.9)), "kw": res("kw", [kw], trade=fs(0.7))}, FAMILIES, None)
    p = d.passages[0]
    assert (p.start, p.end) == (152.0, 212.0) and p.segment_ids[0] == "S015"
    assert any("gekürzt" in r and "00:20-04:58" in r for r in p.reasons)
    uncut = fusion(max_passage_seconds=0).decide(t, {"llm": res("llm", [llm], trade=fs(0.9))}, FAMILIES, None)
    assert uncut.passages[0].end - uncut.passages[0].start > 250
    no_anchor = fusion().decide(t, {"llm": res("llm", [llm], trade=fs(0.9))}, FAMILIES,
                                {"max_passage_seconds": 30})
    assert (no_anchor.passages[0].start, no_anchor.passages[0].end) == (20.0, 50.0)


def test_passage_fallback_from_family_score_segments():
    d = decide([res("llm", trade=fs(0.9, segs=["S004", "S005"], reason="Kaufwunsch"))])
    assert len(d.passages) == 1
    p = d.passages[0]
    assert (p.start, p.end, p.segment_ids) == (40.0, 58.0, ["S004", "S005"])
    assert p.reasons == ["llm: Kaufwunsch"]


def test_no_passages_for_families_below_floor():
    f = Finding(check="kw", family="trade", score=0.9, segment_ids=["S001"], reason="Stichwort")
    assert decide([res("kw", [f], trade=fs(0.1))]).passages == []
    assert len(decide([res("kw", [f], trade=fs(0.3))]).passages) == 1  # review-relevant: officer can listen


# -- contract ------------------------------------------------------------------------------------


def test_pure_and_fast():
    t = transcript()
    results = {"llm": res("llm", [Finding(check="llm", family="trade", score=0.8, segment_ids=["S001"])],
                          trade=fs(0.7, 0.8), access=fs(0.1)),
               "kw": res("kw", trade=fs(0.5), access=fs(0.0))}
    before = {k: v.model_dump() for k, v in results.items()}
    f = fusion()
    t0 = time.perf_counter()
    for i in range(500):
        f.decide(t, results, FAMILIES, {"threshold": 0.3 + i / 1000})
    assert time.perf_counter() - t0 < 2.0
    assert {k: v.model_dump() for k, v in results.items()} == before
    assert f.decide(t, results, FAMILIES).model_dump() == f.decide(t, results, FAMILIES).model_dump()


def test_registry_builds_it_with_params():
    f = registry.create("fusion", {"type": "weighted", "threshold": 0.4}, ctx=SimpleNamespace(cfg=None))
    assert isinstance(f, WeightedFusion)
    assert f.threshold == 0.4
    assert f.cache_params()["threshold"] == 0.4
    with pytest.raises(TypeError):
        registry.create("fusion", {"type": "weighted", "treshold": 0.4}, ctx=None)
