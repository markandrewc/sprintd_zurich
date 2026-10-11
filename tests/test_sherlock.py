"""The production profile `sherlock` (config/sherlock.yaml): staged Qwen3.8-27B (llama-server) + Kev-4B.

Offline only: the profiles parse and build, stage B's `pinned` stand-in keys exactly like the live llama-server
client of stage A (and like the q38 client the Qwen3.8 research runs cached under), so roles, fact answers and
evidence computed in stage A are found in stage B; and the test-set runner is valid bash."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from callguard.checks.facts import FactSheetCheck
from callguard.config import ROOT, load_config
from callguard.context import Context
from callguard.llm.pinned import PinnedLLM, PinnedLLMError
from callguard.pipeline import Pipeline

Q38_TAG = "qwen3.8-27b-ud-iq3_xxs"


def _sets(tmp_path):
    return [f"paths.cache_dir={tmp_path / 'cache'}"]


def test_sherlock_profiles_parse_and_build(tmp_path):
    for name in ("sherlock", "sherlock-qwen", "sherlock-test50"):
        cfg = load_config(name, _sets(tmp_path))
        assert cfg.asr["model"] == "models/asr/whisper-large-v3-gsw-ct2"  # ASR as recommended
        pipe = Pipeline(cfg)
        facts = next(c for c in pipe.checks if c.name == "facts")
        assert isinstance(facts, FactSheetCheck) and facts.evidence and facts.llm_name == "default"
        assert "gsw" in cfg.display_views and cfg.display_views["gsw"]["in_pipeline"] is False
    b = load_config("sherlock", _sets(tmp_path))
    assert [c["name"] for c in b.checks] == ["keywords", "patterns", "facts", "facts_kev"]
    assert b.fusion["type"] == "two_readers" and b.fusion["rule"] == "policy"
    assert b.fusion["fact_policy"] == "config/fact_policy.yaml" and b.fusion["readers"] == ["facts", "facts_kev"]
    assert b.paths.runs_dir.endswith("runs/sherlock")
    a = load_config("sherlock-qwen", _sets(tmp_path))
    assert [c["name"] for c in a.checks] == ["keywords", "patterns", "facts"]
    assert a.fusion["type"] == "weighted" and a.llms["default"]["type"] == "openai_compat"
    assert "identity" not in a.llms["default"]  # the pinned block is replaced whole, not merged
    t = load_config("sherlock-test50", _sets(tmp_path))
    assert t.paths.data_dir.endswith("data_test50/v1")
    assert t.paths.runs_dir.endswith("runs/test50/sherlock")


def test_stage_b_pinned_identity_equals_stage_a_live_qwen38(tmp_path):
    live = Context(load_config("sherlock-qwen", _sets(tmp_path))).llm("default")
    pinned = Context(load_config("sherlock", _sets(tmp_path))).llm("default")
    assert isinstance(pinned, PinnedLLM)
    assert live.cache_tag == Q38_TAG and live.model_id == Q38_TAG  # no server needed: the tag is the identity
    assert pinned.cache_params() == live.cache_params()
    # ... and equal to the q38 client of the Qwen3.8 research (experiments/qwen38.yaml): its fact probes are reused
    q38 = Context(load_config("qwen38", _sets(tmp_path))).llm("q38")
    assert pinned.cache_params() == q38.cache_params()
    with pytest.raises(PinnedLLMError):
        pinned.chat([{"role": "user", "content": "hi"}])


def test_stage_a_and_b_facts_share_the_cache_key(tmp_path):
    """Stage B finds stage A's facts result (with evidence) in the check cache: same params, same LLM identity."""
    a = Pipeline(load_config("sherlock-qwen", _sets(tmp_path)))
    b = Pipeline(load_config("sherlock", _sets(tmp_path)))
    fa = next(c for c in a.checks if c.name == "facts")
    fb = next(c for c in b.checks if c.name == "facts")
    fams = a.ctx.families()
    assert fa.cache_key(fams) == fb.cache_key(fams)
    assert a.cfg.diarizer == b.cfg.diarizer  # roles keyed by llms.default: same identity on both sides
    kw = {c.name: c.cache_params() for c in a.checks if c.name != "facts"}
    assert kw == {c.name: c.cache_params() for c in b.checks if c.name in kw}


@pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")
def test_run_testset_is_valid_bash():
    for script in ("scripts/run_testset.sh", "scripts/remote/serve_llamacpp.sh"):
        r = subprocess.run(["bash", "-n", str(ROOT / script)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
    text = (ROOT / "scripts/run_testset.sh").read_text()
    assert "sherlock-qwen" in text and "-c sherlock" in text and "Qwen3.8-27B-UD-IQ3_XXS.gguf" in text
    for opt in ("NO_KEV", "NO_GSW", "CACHE_DIR", "LLAMA_SERVER"):
        assert opt in text
