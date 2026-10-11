"""HybridFusion: the core check decides; second-opinion checks can only escalate no_alert -> review."""
from types import SimpleNamespace

from callguard.fusion.hybrid import HybridFusion, _majority_verdict
from callguard.types import CheckResult, FamilyScore


def test_majority_verdict_from_votes():
    fs = FamilyScore(score=0.5, confidence=0.5, verdict="absent", detail={"votes": {"undetermined": 2, "absent": 1}})
    assert _majority_verdict(fs) == "undetermined"
    assert _majority_verdict(FamilyScore(score=0.1, confidence=0.9, verdict="absent")) == "absent"


def test_hybrid_registered():
    from callguard import registry
    assert "hybrid" in registry.available()["fusion"]
    assert registry.resolve("fusion", "hybrid") is HybridFusion


def test_params_record_core_and_second_opinion():
    ctx = SimpleNamespace(cfg=SimpleNamespace(checks=[]))
    f = HybridFusion(ctx, core=["facts"], second_opinion=["llm_judge"])
    assert f.params["core"] == ["facts"] and f.params["second_opinion"] == ["llm_judge"]
    assert isinstance(CheckResult(check="x", type="y"), CheckResult)
