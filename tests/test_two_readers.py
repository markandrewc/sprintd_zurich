"""Two readers (agreement.py + fusion/two_readers.py) on tiny synthetic results: no models, no data."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
import yaml

from callguard import agreement as ag
from callguard import registry
from callguard.checks.facts import parse_policy_table
from callguard.fusion.two_readers import TwoReadersFusion
from callguard.fusion.weighted import WeightedFusion
from callguard.types import CallResult, CheckResult, Decision, Family, FamilyScore, Segment, Transcript

FAMILIES = [Family(id="access", label="Zugangsinformation preisgegeben")]
TABLE = {"families": {"access": {
    "facts": [{"id": "spoken", "label": "Code vorgelesen", "role": "act", "en": "Was a code read out?"},
              {"id": "current", "label": "Code gültig", "role": "context", "en": "Is it valid?"}],
    "rules": [{"id": "access.alarm", "label": "alarm", "when": "spoken = yes and current = yes"},
              {"id": "access.review", "label": "review", "when": "spoken = yes and current = unclear"},
              {"id": "access.no_alert", "label": "no_alert", "when": "true"}]}}}


def transcript() -> Transcript:
    return Transcript(call_id="C1", segments=[Segment(id=f"S{i}", start=5.0 * i, end=5.0 * i + 4, text="x")
                                              for i in range(4)])


def yes(p: float) -> dict[str, float]:
    return {"yes": p, "no": round(1 - p, 4), "unclear": 0.0}


def facts_result(name: str, spoken: dict[str, float], current: dict[str, float], decision: str = "no_alert",
                 score: float = 0.0, verdict: str = "absent", conf: float = 1.0) -> CheckResult:
    detail = {"decision": decision, "facts": {"spoken": {"p": spoken, "role": "act", "question": "q1"},
                                              "current": {"p": current, "role": "context", "question": "q2"}}}
    return CheckResult(check=name, type="facts", meta={"policy_table": {"path": "t.yaml"}},
                       family_scores={"access": FamilyScore(score=score, confidence=conf, verdict=verdict,
                                                            detail=detail, segment_ids=["S1"])})


@pytest.fixture
def table_path(tmp_path):
    p = tmp_path / "table.yaml"
    p.write_text(yaml.safe_dump(TABLE))
    return str(p)


def fusion(rule: str, table: str | None = None, **kw) -> TwoReadersFusion:
    checks = [{"name": "facts", "type": "facts", "weight": 1.0, **({"policy_table": table} if table else {})},
              {"name": "facts_kev", "type": "facts", "weight": 1.0, **({"policy_table": table} if table else {})}]
    return TwoReadersFusion(SimpleNamespace(cfg=SimpleNamespace(checks=checks)), rule=rule, **kw)


# ---- pure rules ----------------------------------------------------------------------------------


def test_label_agreement_table():
    assert ag.label_agreement("alarm", "alarm") == "alarm"
    assert ag.label_agreement("no_alert", "no_alert") == "no_alert"
    for a, b in [("alarm", "no_alert"), ("no_alert", "alarm"), ("review", "review"), ("alarm", "review"),
                 ("review", "no_alert"), ("alarm", None), (None, None)]:
        assert ag.label_agreement(a, b) == "review"


def test_combine_fact_agree_disagree_missing():
    v, m, g, dis = ag.combine_fact(yes(0.9), yes(0.7))
    assert (v, dis) == ("yes", False) and g == pytest.approx(0.2) and m["yes"] == pytest.approx(0.8)
    v, _, g, dis = ag.combine_fact(yes(0.95), yes(0.2))  # gap 0.75 > 0.5
    assert (v, dis) == ("unclear", True) and g == pytest.approx(0.75)
    v, _, g, dis = ag.combine_fact(yes(0.9), yes(0.4))  # gap exactly 0.5 is NOT a disagreement
    assert dis is False and g == pytest.approx(0.5) and v == "yes"
    v, m, g, dis = ag.combine_fact(yes(0.3), None)  # missing reader = fully unclear
    assert m["unclear"] == pytest.approx(0.5) and g == pytest.approx(0.3) and not dis and v == "unclear"


def test_combine_family_disagreement_opens_review_rule():
    ft = parse_policy_table(TABLE).families["access"]
    a = facts_result("facts", yes(0.95), yes(0.9)).family_scores["access"]
    b_agree = facts_result("facts_kev", yes(0.9), yes(0.8)).family_scores["access"]
    b_split = facts_result("facts_kev", yes(0.9), yes(0.1)).family_scores["access"]
    out = ag.combine_family(ft, a, b_agree, names=("Qwen", "Kev"))
    assert out.detail["decision"] == "alarm" and out.verdict == "present" and out.segment_ids == ["S1"]
    out = ag.combine_family(ft, a, b_split, names=("Qwen", "Kev"))
    assert out.detail["decision"] == "review" and out.verdict == "undetermined"
    assert out.detail["facts"]["current"]["value"] == "unclear" and out.detail["two_readers"]["disagree"] == ["current"]
    assert "Leser uneinig" in out.reason and out.detail["facts"]["current"]["readers"]["Kev"]["yes"] == 0.1


# ---- fusion --------------------------------------------------------------------------------------


def test_registered_and_validates():
    assert registry.resolve("fusion", "two_readers") is TwoReadersFusion
    with pytest.raises(ValueError):
        fusion("majority")
    with pytest.raises(ValueError):
        fusion("labels", readers=["facts", "facts"])


def test_r2_needs_one_table(tmp_path, table_path):
    other = tmp_path / "other.yaml"
    other.write_text(yaml.safe_dump(TABLE))
    checks = [{"name": "facts", "policy_table": table_path}, {"name": "facts_kev", "policy_table": str(other)}]
    with pytest.raises(ValueError, match="one policy table"):
        TwoReadersFusion(SimpleNamespace(cfg=SimpleNamespace(checks=checks)), rule="facts")


def _results(a: CheckResult | None, b: CheckResult | None) -> dict[str, CheckResult]:
    out = {"keywords": CheckResult(check="keywords", type="keywords",
                                   family_scores={"access": FamilyScore(score=0.0, confidence=0.25)})}
    if a is not None:
        out["facts"] = a
    if b is not None:
        out["facts_kev"] = b.model_copy(update={"check": "facts_kev"})
    return out


ALARM = dict(decision="alarm", score=0.95, verdict="present")
CLEAR = dict(decision="no_alert", score=0.0, verdict="absent")


def test_r1_labels():
    f = fusion("labels", reader_labels=["Qwen", "Kev"], abstain_on_empty=True)
    a, b = facts_result("facts", yes(1), yes(1), **ALARM), facts_result("facts", yes(1), yes(1), **ALARM)
    d = f.decide(transcript(), _results(a, b), FAMILIES)
    assert d.label == "alarm" and "einig" in d.reasons[0]
    b2 = facts_result("facts", yes(0), yes(0), **CLEAR)
    d = f.decide(transcript(), _results(a, b2), FAMILIES)
    assert d.label == "review" and "uneinig" in d.reasons[0]
    da = WeightedFusion(f.ctx, abstain_on_empty=True).decide(transcript(), _results(a, None), FAMILIES)
    db = WeightedFusion(f.ctx, abstain_on_empty=True).decide(
        transcript(), {"keywords": _results(a, None)["keywords"], "facts": b2}, FAMILIES)
    assert d.score == pytest.approx((da.score + db.score) / 2, abs=1e-4)
    d = f.decide(transcript(), _results(b2, b2), FAMILIES)
    assert d.label == "no_alert"
    d = f.decide(transcript(), _results(b2, None), FAMILIES)  # reader B missing: never a silent clearance
    assert d.label == "review" and "fehlt" in d.reasons[0]
    failed = CheckResult(check="facts_kev", type="facts", meta={"error": "server down"})
    assert f.decide(transcript(), {**_results(b2, None), "facts_kev": failed}, FAMILIES).label == "review"


def test_single_reader_rules_equal_weighted_fusion():
    a = facts_result("facts", yes(1), yes(1), **ALARM)
    b = facts_result("facts", yes(0), yes(0), **CLEAR)
    w = WeightedFusion(SimpleNamespace(cfg=None))
    for rule, mine in (("a", a), ("b", b)):
        d = fusion(rule).decide(transcript(), _results(a, b), FAMILIES)
        ref = w.decide(transcript(), {"keywords": _results(a, b)["keywords"], "facts": mine}, FAMILIES)
        assert (d.label, d.score) == (ref.label, ref.score)


def test_r2_facts(table_path):
    f = fusion("facts", table=table_path, reader_labels=["Qwen", "Kev"], abstain_on_empty=True)
    a = facts_result("facts", yes(0.95), yes(0.9), **ALARM)
    d = f.decide(transcript(), _results(a, facts_result("facts", yes(0.9), yes(0.85))), FAMILIES)
    assert d.label == "alarm"
    d = f.decide(transcript(), _results(a, facts_result("facts", yes(0.9), yes(0.05))), FAMILIES)
    assert d.label == "review" and any("Zwei Leser uneinig" in r for r in d.reasons)
    d = f.decide(transcript(), _results(facts_result("facts", yes(0.02), yes(0.1)),
                                        facts_result("facts", yes(0.05), yes(0.2))), FAMILIES)
    assert d.label == "no_alert"


# ---- joining stored variants ------------------------------------------------------------------------


def _call(cid: str, facts: CheckResult, kw_score: float = 0.0) -> CallResult:
    kw = CheckResult(check="keywords", type="keywords", family_scores={"access": FamilyScore(score=kw_score)})
    return CallResult(call_id=cid, transcript=transcript(), checks={"keywords": kw, "facts": facts},
                      decision=Decision(label="no_alert", score=0.0, uncertainty=0.0, threshold=0.55))


def test_merge_results_and_report():
    fa, fb = facts_result("facts", yes(1), yes(1)), facts_result("facts", yes(0), yes(0))
    res_a = [_call("C1", fa), _call("C2", fa)]
    res_b = [_call("C1", fb), _call("C3", fb, kw_score=0.5)]
    merged, rep = ag.merge_results(res_a, res_b)
    assert [r.call_id for r in merged] == ["C1"] and rep["only_a"] == ["C2"] and rep["only_b"] == ["C3"]
    assert merged[0].checks["facts_kev"].check == "facts_kev"
    assert merged[0].checks["facts"].family_scores["access"].detail["facts"]["spoken"]["p"]["yes"] == 1
    assert not rep["shared_check_differs"]
    _, rep = ag.merge_results([_call("C3", fa)], res_b)
    assert rep["shared_check_differs"] == {"keywords": ["C3"]}


def test_merge_variants_roundtrip(tmp_path):
    from callguard import experiments as ex

    for name, res in (("a", [_call("C1", facts_result("facts", yes(1), yes(1)))]),
                      ("b", [_call("C1", facts_result("facts", yes(0), yes(0)))])):
        d = tmp_path / name
        d.mkdir()
        (d / "results.jsonl").write_text(res[0].model_dump_json() + "\n")
    rep = ag.merge_variants(tmp_path / "a", tmp_path / "b", tmp_path / "src")
    assert rep["n_merged"] == 1 and not rep["policy_table_mismatch"]
    back = ex.load_results(tmp_path / "src")
    assert set(back[0].checks) == {"keywords", "facts", "facts_kev"}
    with pytest.raises(FileNotFoundError):
        ag.merge_variants(tmp_path / "a", tmp_path / "missing", tmp_path / "x")


# ---- acceptance logic --------------------------------------------------------------------------------


def _rows(preds: list[tuple[str, str, float]]) -> list[dict]:
    return [{"call_id": f"C{i}", "dialogue_id": f"D{i // 2}", "group": f"G{i // 2}", "expected": e, "predicted": p,
             "score": s} for i, (e, p, s) in enumerate(preds)]


def test_acceptance_pass_and_fail():
    truth = ["alarm", "alarm", "review", "review", "no_alert", "no_alert", "no_alert", "no_alert"]
    good = _rows([(e, e, {"alarm": 0.9, "review": 0.5, "no_alert": 0.1}[e]) for e in truth])
    champ = _rows([(e, "no_alert" if e == "review" else e, {"alarm": 0.9, "review": 0.3, "no_alert": 0.2}[e])
                   for e in truth])
    weak = _rows([(e, "alarm" if i % 2 else "no_alert", 0.5) for i, e in enumerate(truth)])  # AUC 0.5
    flagall = _rows([(e, "review", 0.5) for e in truth])
    pack = lambda r: {"fixed": r, "cv": r, "cv_far": r}  # noqa: E731
    data = {"tuned": {"a": pack(champ), "labels": pack(good), "facts": pack(flagall)},
            **{w: {"a": pack(weak), "labels": pack(good), "facts": pack(flagall)} for w in ag.REWORDED}}
    res = ag.acceptance(data, n_boot=200)
    v = res["verdict"]
    assert v["labels"]["pass"] and res["recommend"] == "labels"
    assert not v["facts"]["pass"] and not v["facts"]["criteria"]["A1"]["pass"]  # flag-all: FAR 100%
    assert not v["facts"]["criteria"]["A4"]["pass"]
    md = ag.render_acceptance(res, {"x": "ok"})
    assert "R1 labels: PASS" in md and "R2 facts: FAIL" in md


def test_rule_of_and_pair_variants():
    from callguard.experiments import load_spec

    assert ag.rule_of(["a=b", "fusion.rule=labels"]) == "labels" and ag.rule_of([]) is None
    spec = load_spec("two_readers")
    assert ag.pair_variants(spec, "tuned_src") == {"a": "champion", "b": "kev", "labels": "r1", "facts": "r2"}
    for w, (exp, src, _, _) in ag.PAIRS.items():
        assert set(ag.pair_variants(load_spec(exp), src)) == {"a", "b", "labels", "facts"}, w


def test_profile_builds_offline():
    from callguard.config import load_config
    from callguard.pipeline import Pipeline

    pipe = Pipeline(load_config("two-readers", overrides=["fusion.rule=facts"]))
    assert isinstance(pipe.fusion, TwoReadersFusion) and pipe.fusion.rule == "facts"
    assert [c.name for c in pipe.checks] == ["keywords", "patterns", "facts", "facts_kev"]
