"""Fail closed: when a fact reader is missing or failed, a call is never cleared to «Kein Alarm».

Re-decides stored production results (results/cleanroom-10, profile sherlock) with one or both readers replaced by an
error result; no model runs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from callguard import registry
from callguard.config import ROOT, load_config
from callguard.context import Context
from callguard.types import CallResult, CheckResult

RUNS = ROOT / "results" / "cleanroom-10" / "sherlock"


def _load(call: str) -> CallResult:
    return CallResult.model_validate(json.loads((RUNS / call / "result.json").read_text()))


@pytest.fixture(scope="module")
def fusion_ctx():
    if not RUNS.exists():
        pytest.skip("results/cleanroom-10 not present")
    cfg = load_config("sherlock")
    ctx = Context(cfg)
    return registry.create("fusion", cfg.fusion, ctx=ctx), ctx


def _decide(fusion_ctx, r: CallResult, down: tuple[str, ...]):
    fusion, ctx = fusion_ctx
    checks = dict(r.checks)
    for name in down:
        checks[name] = CheckResult(check=name, type=checks[name].type, meta={"error": "server down (test)"})
    return fusion.decide(r.transcript, checks, ctx.families())


@pytest.mark.parametrize("call", ["c08", "c09", "c02", "c05"])
@pytest.mark.parametrize("down", [("facts",), ("facts_kev",), ("facts", "facts_kev")])
def test_missing_reader_never_clears_a_call(fusion_ctx, call, down):
    r = _load(call)
    full = _decide(fusion_ctx, r, ())
    assert full.label == r.decision.label  # the stored decision is reproduced from the stored answers
    d = _decide(fusion_ctx, r, down)
    assert d.label != "no_alert"
    assert "ausgefallen" in d.reasons[0]


def test_both_readers_present_is_unchanged(fusion_ctx):
    for call in ("c01", "c08"):
        r = _load(call)
        d = _decide(fusion_ctx, r, ())
        assert d.label == r.decision.label and not any("ausgefallen" in x for x in d.reasons)


def test_api_path_decide_checks_also_fails_closed(fusion_ctx):
    """The dashboard re-decides combined checks with decide_checks: same guarantee."""
    from callguard import fact_policy as fpol
    fusion, ctx = fusion_ctx
    r = _load("c08")
    checks = dict(r.checks)
    checks["facts_kev"] = CheckResult(check="facts_kev", type="kev_facts", meta={"error": "down (test)"})
    combined = fpol.combined_checks(checks, fusion.table(), fusion.fact_policy())
    d = fusion.decide_checks(r.transcript, combined, ctx.families())
    assert d.label != "no_alert" and "ausgefallen" in d.reasons[0]
    both = fpol.combined_checks({k: v for k, v in r.checks.items() if k not in ("facts", "facts_kev")},
                                fusion.table(), fusion.fact_policy())
    assert fusion.decide_checks(r.transcript, both, ctx.families()).label != "no_alert"
