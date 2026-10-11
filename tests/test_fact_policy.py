"""Fact policy (fact_policy.py): per-reader resolution, combination modes, per-fact overrides, re-decision
equals the live fusion, speed, and governance (facts need four eyes, rules are instant with undo)."""
from __future__ import annotations

import copy
import time
from types import SimpleNamespace

import pytest
import yaml

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard.checks.facts import parse_policy_table
from callguard.fusion.two_readers import TwoReadersFusion
from callguard.policy_versions import FourEyesError, VersionStore, merge_tables
from callguard.types import CallResult, CheckResult, Decision, Family, FamilyScore, Segment, Transcript

FAMILIES = [Family(id="access", label="Zugangsinformation preisgegeben")]
TABLE = {"families": {"access": {
    "facts": [{"id": "spoken", "label": "Code vorgelesen", "role": "act", "de": "Wurde ein Code vorgelesen?",
               "en": "Was a code read out?"},
              {"id": "current", "label": "Code gültig", "role": "context", "de": "Ist er gültig?", "en": "Is it valid?"}],
    "rules": [{"id": "access.alarm", "label": "alarm", "when": "spoken = yes and current = yes"},
              {"id": "access.review", "label": "review", "when": "spoken = yes and current = unclear"},
              {"id": "access.no_alert", "label": "no_alert", "when": "true"}]}}}
DEFAULT = fpol.default_policy()


def q(y: float, n: float) -> dict[str, float]:  # Qwen-like: three answers
    return {"yes": y, "no": n, "unclear": round(1 - y - n, 4)}


def k(y: float) -> dict[str, float]:  # Kev-like: p(yes) only
    return {"yes": y, "no": round(1 - y, 4), "unclear": 0.0}


# ---- resolution truth tables ----------------------------------------------------------------------


def test_three_way_and_band_resolution():
    qwen, kev = DEFAULT.a, DEFAULT.b
    assert qwen.resolve(q(0.6, 0.1)) == "yes" and qwen.resolve(q(0.1, 0.7)) == "no"
    assert qwen.resolve(q(0.45, 0.45)) == "unclear" and qwen.resolve(None) == "unclear"
    assert kev.resolve(k(0.7)) == "yes" and kev.resolve(k(0.69)) == "unclear"
    assert kev.resolve(k(0.3)) == "no" and kev.resolve(k(0.31)) == "unclear"
    wide = DEFAULT.with_reader(1, lo=0.2, hi=0.8).b
    assert wide.resolve(k(0.75)) == "unclear" and wide.resolve(k(0.25)) == "unclear"
    qband = DEFAULT.with_reader(0, mode="band", lo=0.4, hi=0.6).a  # Qwen switched to a band on p(ja)
    assert qband.resolve(q(0.55, 0.0)) == "unclear" and qband.resolve(q(0.6, 0.0)) == "yes"
    assert qband.resolve(q(0.35, 0.0)) == "no"  # band: p(nein) is not consulted


@pytest.mark.parametrize("mode,table", [
    ("only_a", {("yes", "no"): "yes", ("no", "yes"): "no", ("unclear", "yes"): "unclear", ("yes", "unclear"): "yes"}),
    ("only_b", {("yes", "no"): "no", ("no", "yes"): "yes", ("unclear", "yes"): "yes", ("yes", "unclear"): "unclear"}),
    ("agree", {("yes", "yes"): "yes", ("no", "no"): "no", ("yes", "no"): "unclear", ("yes", "unclear"): "unclear",
               ("unclear", "unclear"): "unclear", ("no", "unclear"): "unclear"}),
    ("a_checked", {("yes", "yes"): "yes", ("yes", "no"): "unclear", ("no", "yes"): "unclear",
                   ("yes", "unclear"): "yes", ("no", "unclear"): "no", ("unclear", "yes"): "unclear"}),
])
def test_combination_truth_tables(mode, table):
    for (va, vb), want in table.items():
        assert fpol.combine_values(mode, va, vb) == want, (mode, va, vb)


def test_resolve_fact_and_per_fact_override():
    rf = fpol.resolve_fact(DEFAULT, "access", "spoken", q(0.9, 0.05), k(0.5))
    assert (rf.va, rf.vb, rf.value, rf.agree) == ("yes", "unclear", "unclear", False)
    assert rf.badge() == "uneinig → unklar" and rf.p["yes"] == pytest.approx(0.7)
    pol = DEFAULT.with_override("access", "spoken", reader="kev", band=[0.4, 0.45])
    assert pol.has_override("access", "spoken") and not pol.has_override("access", "current")
    rf = fpol.resolve_fact(pol, "access", "spoken", q(0.9, 0.05), k(0.5))
    assert (rf.vb, rf.value, rf.agree) == ("yes", "yes", True)
    assert fpol.resolve_fact(pol, "access", "current", q(0.9, 0.05), k(0.5)).value == "unclear"  # global band
    pol2 = pol.with_override("access", "current", combination="only_a")
    assert fpol.resolve_fact(pol2, "access", "current", q(0.9, 0.05), k(0.5)).value == "yes"
    assert not pol2.with_override("access", "spoken", clear=True).has_override("access", "spoken")
    # round trip through YAML keeps everything
    back = fpol.parse_fact_policy(yaml.safe_load(fpol.dump_fact_policy(pol2)))
    assert back.as_dict() == pol2.as_dict() and back.key() == pol2.key()


def test_parse_errors():
    raw = DEFAULT.as_dict()
    for bad in ({**raw, "combination": "majority"}, {**raw, "readers": raw["readers"][:1]},
                {**raw, "overrides": {"access.spoken": {"nobody": {"band": [0.1, 0.9]}}}},
                {**raw, "readers": [raw["readers"][0], {**raw["readers"][1], "band": [0.8, 0.2]}]}):
        with pytest.raises(fpol.FactPolicyError):
            fpol.parse_fact_policy(bad)


# ---- re-decision == the live fusion ------------------------------------------------------------------


def transcript(cid: str) -> Transcript:
    return Transcript(call_id=cid, segments=[Segment(id=f"S{i}", start=5.0 * i, end=5.0 * i + 4, text="x")
                                             for i in range(3)])


def reader(name: str, spoken: dict[str, float], current: dict[str, float]) -> CheckResult:
    detail = {"decision": "no_alert", "facts": {"spoken": {"p": spoken, "role": "act", "question": "q1"},
                                                "current": {"p": current, "role": "context", "question": "q2"}}}
    return CheckResult(check=name, type="facts", meta={"model": name},
                       family_scores={"access": FamilyScore(score=0.0, confidence=1.0, verdict="absent",
                                                            detail=detail, segment_ids=["S1"])})


def call(cid: str, a: tuple, b: tuple) -> CallResult:
    t = transcript(cid)
    return CallResult(call_id=cid, audio_path="x.wav", transcript=t,
                      checks={"facts": reader("facts", *a), "facts_kev": reader("facts_kev", *b)},
                      decision=Decision(label="no_alert", score=0.0, uncertainty=0.0, threshold=0.55))


CALLS = {
    "c_agree_alarm": call("c_agree_alarm", (q(0.95, 0.0), q(0.9, 0.05)), (k(0.9), k(0.8))),
    "c_split": call("c_split", (q(0.95, 0.0), q(0.9, 0.05)), (k(0.9), k(0.1))),
    "c_none": call("c_none", (q(0.02, 0.95), q(0.1, 0.8)), (k(0.05), k(0.1))),
    "c_kev_unsure": call("c_kev_unsure", (q(0.9, 0.05), q(0.8, 0.1)), (k(0.9), k(0.5))),
}


@pytest.fixture
def setup(tmp_path):
    tp = tmp_path / "table.yaml"
    tp.write_text(yaml.safe_dump(TABLE))
    pp = tmp_path / "fact_policy.yaml"
    pp.write_text(fpol.dump_fact_policy(DEFAULT))
    checks = [{"name": "facts", "type": "facts", "weight": 1.0, "policy_table": str(tp)},
              {"name": "facts_kev", "type": "facts", "weight": 1.0, "policy_table": str(tp)}]
    fus = TwoReadersFusion(SimpleNamespace(cfg=SimpleNamespace(checks=checks)), rule="policy", fact_policy=str(pp))
    return fus, tp, pp


def test_redecide_equals_pipeline_fusion(setup):
    fus, _, _ = setup
    assert fus.readers == ("facts", "facts_kev") and fus.params["fact_policy"]
    live = {cid: fus.decide(r.transcript, r.checks, FAMILIES) for cid, r in CALLS.items()}
    dec = lambda r, c: fus.decide_checks(r.transcript, c, FAMILIES)  # noqa: E731
    out = fpol.redecide(CALLS, fus.tables(), fus.fact_policy(), dec, **fus.scoring)
    assert {c: o.label for c, o in out.items()} == {c: d.label for c, d in live.items()}
    assert {c: o.score for c, o in out.items()} == {c: d.score for c, d in live.items()}
    assert out["c_agree_alarm"].label == "alarm" and out["c_none"].label == "no_alert"
    # Kev says "current = no", Qwen "yes": Einigkeit -> unklar -> the review rule
    assert out["c_split"].families["access"].rule == "access.review"
    f = out["c_split"].families["access"].facts["current"]
    assert (f.va, f.vb, f.value, f.agree) == ("yes", "no", "unclear", False)
    assert any("uneinig" in r for r in live["c_split"].reasons)
    # Nur Qwen = the champion: both alarm
    only_a = fpol.redecide(CALLS, fus.tables(), DEFAULT.with_combination("only_a"), dec, **fus.scoring)
    assert only_a["c_split"].label == "alarm" and only_a["c_kev_unsure"].label == "alarm"
    eff = fpol.effect(out, only_a)
    assert {c for c, _, _ in eff["changed"]} == {"c_split", "c_kev_unsure"}
    assert fpol.effect_line(eff).startswith("ändert 2 von 4 Anrufen: +2 Alarm")
    assert fpol.effect_line(fpol.effect(out, out)) == "ändert keinen der 4 Anrufe"


def test_live_policy_file_is_reread(setup):
    fus, _, pp = setup
    r = CALLS["c_kev_unsure"]
    assert fus.decide(r.transcript, r.checks, FAMILIES).label != "alarm"
    pp.write_text(fpol.dump_fact_policy(DEFAULT.with_combination("only_a")))
    import os
    os.utime(pp, (time.time() + 5, time.time() + 5))
    assert fus.decide(r.transcript, r.checks, FAMILIES).label == "alarm"


def test_fact_answers_and_disagreements():
    ans = fpol.fact_answers(CALLS, DEFAULT)
    assert len(ans[("access", "current")]) == 4
    dis = fpol.disagreements(ans[("access", "current")], DEFAULT, "access", "current")
    assert [d.fact for d in dis] == ["c_kev_unsure", "c_split"]
    cnt = fpol.value_counts(ans[("access", "current")], DEFAULT, "access", "current")
    assert cnt["a"]["yes"] == 3 and cnt["b"]["unclear"] == 1 and cnt["combined"]["unclear"] == 2


def test_redecide_speed_160_calls(setup):
    """The officer moves a band or edits a rule: all calls must re-decide well under a second."""
    fus, _, _ = setup
    base = list(CALLS.values())
    many = {f"x{i}": base[i % 4].model_copy(update={"call_id": f"x{i}"}) for i in range(160)}
    dec = lambda r, c: fus.decide_checks(r.transcript, c, FAMILIES)  # noqa: E731
    t0 = time.perf_counter()
    fpol.redecide(many, fus.tables(), DEFAULT.with_reader(1, lo=0.2, hi=0.8), dec, **fus.scoring)
    dt = time.perf_counter() - t0
    print(f"re-decided 160 calls in {dt * 1000:.0f} ms")
    assert dt < 2.0


def test_other_two_readers_rules_keep_params():
    checks = [{"name": "facts", "type": "facts"}, {"name": "facts_kev", "type": "facts"}]
    fus = TwoReadersFusion(SimpleNamespace(cfg=SimpleNamespace(checks=checks)), rule="labels")
    assert "fact_policy" not in fus.params and "policy_table" not in fus.params


# ---- governance ----------------------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path):
    tp = tmp_path / "policy_table.yaml"
    tp.write_text(pe.dump_doc(TABLE, "# test table"))
    pp = tmp_path / "fact_policy.yaml"
    pp.write_text(fpol.dump_fact_policy(DEFAULT))
    s = VersionStore(tp, audit_dir=tmp_path, extras={"fact_policy": pp})
    s.ensure_initial()
    return s, tp, pp


def test_rules_apply_instantly_with_undo(store):
    s, tp, _ = store
    doc = pe.load_doc(tp)
    new = copy.deepcopy(doc)
    pe.set_enabled(new, "access", "access.review", False)
    v = s.apply_rules(new, "Anna")
    assert v.status == "approved" and v.meta["instant"] and v.meta["approver"] is None
    live = pe.load_doc(tp)
    assert pe.is_enabled(live["families"]["access"]["rules"][1]) is False  # live at once, no second person
    assert s.last_rule_change().n == v.n
    u = s.undo_rules("Anna")
    assert u.meta["kind"] == "rules_undo" and pe.is_enabled(pe.load_doc(tp)["families"]["access"]["rules"][1])
    assert (tp.parent / "audit.jsonl").read_text().count("policy_rules_applied") == 2
    with pytest.raises(FourEyesError):
        s.apply_rules(pe.load_doc(tp), "Anna")  # nothing changed


def test_fact_change_refused_on_the_rules_path_and_needs_four_eyes(store):
    s, tp, pp = store
    doc = pe.load_doc(tp)
    new = copy.deepcopy(doc)
    new["families"]["access"]["facts"][0]["en"] = "Did someone read out a code?"
    with pytest.raises(FourEyesError, match="Freigabe durch zweite Person"):
        s.apply_rules(new, "Anna")
    pol = DEFAULT.with_reader(1, lo=0.2, hi=0.8)
    d = s.save_draft({"policy_table": new, "fact_policy": pol.as_dict()}, "Anna")
    assert sorted(d.meta["changed_files"]) == ["fact_policy", "policy_table"]
    assert any("Kev" in line and "0.20" in line for line in d.meta["diff"])
    assert fpol.load_fact_policy(pp).b.lo == 0.3  # not live before approval
    with pytest.raises(FourEyesError, match="Vier-Augen"):
        s.approve(d.n, "anna")
    # rules applied instantly meanwhile: approval merges (draft facts + live rules)
    rules_doc = copy.deepcopy(pe.load_doc(tp))
    pe.set_enabled(rules_doc, "access", "access.review", False)
    s.apply_rules(rules_doc, "Ben")
    s.approve(d.n, "Ben")
    live = pe.load_doc(tp)
    assert live["families"]["access"]["facts"][0]["en"] == "Did someone read out a code?"
    assert pe.is_enabled(live["families"]["access"]["rules"][1]) is False
    assert fpol.load_fact_policy(pp).b.lo == 0.2


def test_merge_tables_conflict():
    base = copy.deepcopy(TABLE)
    live = copy.deepcopy(TABLE)
    draft = copy.deepcopy(TABLE)
    live["families"]["access"]["rules"][0]["when"] = "spoken = yes"
    draft["families"]["access"]["rules"][0]["when"] = "current = yes"
    assert merge_tables(base, live, draft) is None
    draft = copy.deepcopy(TABLE)
    draft["families"]["access"]["facts"][1]["en"] = "Valid?"
    m = merge_tables(base, live, draft)
    assert m["families"]["access"]["rules"][0]["when"] == "spoken = yes"
    assert m["families"]["access"]["facts"][1]["en"] == "Valid?"
    assert parse_policy_table(m)
