"""on_split: what a family becomes when Qwen alone and Kev alone would reach different verdicts.

Re-decides stored production results (results/overnight-60, profile sherlock) under the fact policy with
on_split rules / review / alarm; no model runs."""

from __future__ import annotations


import pytest

from callguard.checks.facts import load_policy_table
from callguard.config import ROOT
from callguard.fact_policy import FactPolicyError, combined_result, load_fact_policy, parse_fact_policy
from callguard.types import CallResult

RUNS = ROOT / "results" / "overnight-60" / "sherlock"


@pytest.fixture(scope="module")
def setup():
    if not RUNS.exists():
        pytest.skip("results/overnight-60 not present")
    return load_fact_policy(ROOT / "config" / "fact_policy.yaml"), load_policy_table(ROOT / "config" / "policy_table.yaml")


def _trade(call: str, pol, tab):
    r = CallResult.model_validate_json((RUNS / call / "result.json").read_text())
    return combined_result(tab, r.checks.get(pol.a.check), r.checks.get(pol.b.check), pol).family_scores["trade"]


def test_default_is_rules_and_key_unchanged(setup):
    pol, _ = setup
    assert pol.on_split == "rules"
    assert "on_split" not in pol.as_dict()  # existing policies keep their key (caches stay valid)
    assert pol.with_on_split("review").key() != pol.key()


def test_split_verdict_escalates(setup):
    pol, tab = setup
    # n31: Qwen alone -> Alarm, Kev alone -> Kein Alarm (wish p(ja) 0.51 inside Kev's band): today Kein Alarm
    assert _trade("n31", pol, tab).detail["decision"] == "no_alert"
    rev = _trade("n31", pol.with_on_split("review"), tab)
    assert rev.detail["decision"] == "review" and rev.detail["verdict_split"]["a"] == "alarm"
    assert rev.reason.startswith("Prüfen: Qwen allein Alarm, Kev allein Kein Alarm")
    alarm = _trade("n31", pol.with_on_split("alarm"), tab)
    assert alarm.detail["decision"] == "alarm" and alarm.score >= 0.6


def test_agreeing_readers_unchanged(setup):
    pol, tab = setup
    for call, want in (("n04", "alarm"), ("n39", "no_alert")):  # D02 alarm, D03 harmless with keywords
        for mode in ("rules", "review", "alarm"):
            fs = _trade(call, pol.with_on_split(mode), tab)
            assert fs.detail["decision"] == want and "verdict_split" not in fs.detail


def test_parse(setup):
    pol, _ = setup
    raw = {**pol.as_dict(), "on_split": "review"}
    assert parse_fact_policy(raw).on_split == "review"
    with pytest.raises(FactPolicyError):
        parse_fact_policy({**pol.as_dict(), "on_split": "maybe"})
    with pytest.raises(FactPolicyError):
        pol.with_on_split("maybe")
    assert pol.with_on_split("alarm").with_combination("a_checked").on_split == "alarm"
