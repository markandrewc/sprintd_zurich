"""Integration seams of the core: config merging, what the pipeline caches (and what it must not),
stage hooks, snippets, profiles. Everything runs offline on synthetic audio and stub plugins."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from callguard import audio as audio_mod
from callguard import registry
from callguard.cache import Cache
from callguard.config import ROOT, AppConfig, Paths, load_config
from callguard.families import load_families, save_keywords
from callguard.fusion import top_family
from callguard.pipeline import Pipeline
from callguard.plugins import ASRBackend, Check, Diarizer, Fusion, LLM, Preprocessor, Sink, Translator
from callguard.types import CheckResult, FamilyScore, Finding, Segment, Transcript

BASES = {"asr": ASRBackend, "diarizer": Diarizer, "check": Check, "fusion": Fusion, "llm": LLM, "sink": Sink,
         "translator": Translator, "preprocess": Preprocessor}
PROFILES = ["local", "gpu", "oracle", "fast", "demo-offline"]
DATA = ROOT / "data_upstream/inventx-case-study/data"


# --------------------------------------------------------------------------------------------
# stub plugins (registered under test-only names)
# --------------------------------------------------------------------------------------------

CALLS = {"asr": 0, "diar": 0, "check": 0}


@registry.register("asr", "test_core_fixed")
class FixedASR(ASRBackend):
    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        CALLS["asr"] += 1
        segs = [
            Segment(id="S001", start=0.5, end=4.0, text="Guten Tag, wie kann ich helfen?"),
            Segment(id="S002", start=5.0, end=11.0,
                    text="Ich möchte die Aktie vor der Meldung kaufen, die Quartalszahlen sind nicht publiziert."),
            Segment(id="S003", start=12.0, end=15.0, text="Das kann ich so nicht ausführen."),
        ]
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=20.0, segments=segs,
                          asr_backend="test")


@registry.register("diarizer", "test_core_degraded")
class DegradedDiarizer(Diarizer):
    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript:
        CALLS["diar"] += 1
        t = transcript.model_copy(deep=True)
        t.meta["diarization"] = {"error": "model missing"}
        return t


@registry.register("diarizer", "test_core_broken")
class BrokenDiarizer(Diarizer):
    def diarize(self, audio_path: Path | None, transcript: Transcript) -> Transcript:
        raise RuntimeError("sherpa exploded")


@registry.register("check", "test_core_partial")
class PartialCheck(Check):
    """Like an LLM check whose server hiccuped on one family."""

    def run(self, transcript: Transcript, families) -> CheckResult:
        CALLS["check"] += 1
        return CheckResult(check=self.name, type=self.plugin_type,
                           family_scores={"trade": FamilyScore(score=0.9, confidence=0.9)},
                           findings=[Finding(check=self.name, family="trade", score=0.9, segment_ids=["S002"],
                                             reason="Kaufwunsch vor der Meldung")],
                           meta={"errors": {"access": "timeout"}, "cacheable": False})


@pytest.fixture(autouse=True)
def _reset_counts():
    for k in CALLS:
        CALLS[k] = 0


@pytest.fixture
def wav(tmp_path) -> Path:
    p = tmp_path / "call.wav"
    t = np.arange(20 * audio_mod.SR) / audio_mod.SR
    sf.write(str(p), (0.1 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), audio_mod.SR, subtype="PCM_16")
    return p


def make_cfg(tmp_path: Path, **over) -> AppConfig:
    spec = dict(name="t", asr={"type": "test_core_fixed"}, diarizer={"type": "none"},
                checks=[{"name": "keywords", "type": "keywords", "weight": 0.35}], sinks=[],
                paths=Paths(cache_dir=str(tmp_path / "cache"), runs_dir=str(tmp_path / "runs")))
    spec.update(over)
    return AppConfig(**spec)


# --------------------------------------------------------------------------------------------
# registry + profiles
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind,name", [(k, n) for k, names in registry.BUILTINS.items() for n in names])
def test_every_builtin_plugin_imports(kind, name):
    assert issubclass(registry.resolve(kind, name), BASES[kind])


@pytest.mark.parametrize("profile", PROFILES)
def test_profiles_build_without_loading_models(profile):
    cfg = load_config(profile)
    pipe = Pipeline(cfg, use_cache=False)
    assert pipe.fusion and pipe.checks
    for name in cfg.llms:
        pipe.ctx.llm(name)  # clients are lazy: no request is sent
    model = cfg.asr.get("model")
    if model and not (ROOT / model).exists():
        pytest.skip(f"ASR model {model} not downloaded")  # gpu profile on a laptop
    assert pipe.asr.cache_params()["type"] == cfg.asr["type"]
    assert pipe.diarizer.cache_params()["type"] == cfg.diarizer["type"]


def test_fast_and_demo_profiles_are_what_they_claim():
    fast, demo = load_config("fast"), load_config("demo-offline")
    assert [c["type"] for c in fast.checks] == ["keywords", "patterns"] and fast.diarizer == {"type": "none"}
    assert fast.asr == load_config("local").asr  # shares the local ASR cache
    assert demo.asr == {"type": "reference"} and demo.llms["default"]["type"] == "fake"
    assert set(demo.llms["default"]) == {"type", "cues"}  # nothing inherited from the server block
    assert {c["type"] for c in demo.checks} == {"keywords", "patterns", "llm_judge", "geval"}


def test_profile_swapping_a_plugin_type_inherits_nothing(tmp_path):
    (tmp_path / "parent.yaml").write_text(
        "asr: {type: faster_whisper, model: m, beam_size: 5}\nllms: {default: {type: openai_compat, timeout: 9}}\n")
    (tmp_path / "child.yaml").write_text(
        "extends: parent.yaml\nasr: {type: reference}\nllms: {default: {type: openai_compat, model: x}}\n")
    cfg = load_config(tmp_path / "child.yaml")
    assert cfg.asr == {"type": "reference"}
    assert cfg.llms["default"] == {"type": "openai_compat", "timeout": 9, "model": "x"}  # same type: merged


# --------------------------------------------------------------------------------------------
# caching
# --------------------------------------------------------------------------------------------


def test_cache_store_predicate_keeps_degraded_values_out(tmp_path):
    cache = Cache(tmp_path)
    t = Transcript(call_id="x", meta={"degraded": "yes"})
    _, hit = cache.get_or_compute("ns", {"k": 1}, Transcript, lambda: t, store=lambda v: False)
    assert not hit and cache.get("ns", {"k": 1}, Transcript) is None
    cache.get_or_compute("ns", {"k": 1}, Transcript, lambda: t)
    assert cache.get("ns", {"k": 1}, Transcript) is not None


def test_partially_failed_check_is_not_cached(tmp_path, wav):
    pipe = Pipeline(make_cfg(tmp_path, checks=[{"name": "judge", "type": "test_core_partial"}]))
    t = pipe.transcribe(wav, "c1")
    fams = pipe.ctx.families()
    for _ in range(2):
        r = pipe.run_check(pipe.checks[0], t, fams)
        assert r.family_scores["trade"].score == 0.9
    assert CALLS["check"] == 2 and pipe.cached_check(pipe.checks[0], t, fams) is None


def test_complete_check_and_transcript_are_cached(tmp_path, wav):
    pipe = Pipeline(make_cfg(tmp_path))
    t = pipe.transcribe(wav, "c1")
    pipe.transcribe(wav, "c1")
    assert CALLS["asr"] == 1
    fams = pipe.ctx.families()
    r = pipe.run_check(pipe.checks[0], t, fams)
    assert pipe.cached_check(pipe.checks[0], t, fams) == r


def test_degraded_diarization_is_not_cached(tmp_path, wav):
    pipe = Pipeline(make_cfg(tmp_path, diarizer={"type": "test_core_degraded"}))
    t = pipe.transcribe(wav, "c1")
    pipe.diarize(wav, t)
    pipe.diarize(wav, t)
    assert CALLS["diar"] == 2


def test_asr_cache_key_ignores_thread_count(tmp_path):
    ct2 = tmp_path / "ct2"
    ct2.mkdir()
    for f in ("model.bin", "tokenizer.json"):
        (ct2 / f).write_text("x")
    keys = [Pipeline(make_cfg(tmp_path, asr={"type": "faster_whisper", "model": str(ct2), "cpu_threads": n}))
            .asr.cache_params() for n in (0, 8)]
    assert keys[0] == keys[1] and "cpu_threads" not in keys[0]


# --------------------------------------------------------------------------------------------
# whole call
# --------------------------------------------------------------------------------------------


def test_process_stages_snippets_and_top_family(tmp_path, wav, monkeypatch):
    loads = []
    real_load = audio_mod.load_audio
    monkeypatch.setattr(audio_mod, "load_audio", lambda p, sr=audio_mod.SR: loads.append(p) or real_load(p, sr))
    pipe = Pipeline(make_cfg(tmp_path, checks=[{"name": "keywords", "type": "keywords", "weight": 0.35},
                                                {"name": "judge", "type": "test_core_partial", "weight": 1.0}]))
    stages: list[str] = []
    r = pipe.process(wav, "c1", on_stage=stages.append)
    assert stages == ["asr", "diarize", "checks", "decide", "snippets", "emit"]
    d = r.decision
    assert d.top_family == "trade" == top_family(d) and d.passages
    assert len(loads) == 1  # one decode for all passages
    pad = float(pipe.cfg.snippets["pad"])
    for p in d.passages:
        info = sf.info(p.snippet_path)
        assert info.samplerate == audio_mod.SR
        expected = min(20.0, p.end + pad) - max(0.0, p.start - pad)
        assert abs(info.duration - expected) < 0.01
        assert "S002" in p.segment_ids and p.reasons
    assert set(r.timings) == {"asr", "diarize", "checks"}


def test_broken_diarizer_does_not_kill_the_call(tmp_path, wav):
    r = Pipeline(make_cfg(tmp_path, diarizer={"type": "test_core_broken"})).process(wav, "c1", emit=False)
    assert r.decision.label in ("alarm", "review", "no_alert")
    assert "sherpa exploded" in r.meta["warnings"][0]


def test_result_json_without_new_fields_still_loads():
    from callguard.types import CallResult, Decision

    d = Decision(label="no_alert", score=0.0, uncertainty=0.0, threshold=0.5).model_dump()
    d.pop("top_family")
    r = CallResult.model_validate({"call_id": "x", "transcript": {"call_id": "x"}, "decision": d})
    assert r.meta == {} and r.decision.top_family is None


# --------------------------------------------------------------------------------------------
# keyword list round trip
# --------------------------------------------------------------------------------------------


def test_save_keywords_noop_is_byte_identical_and_edits_stay_local(tmp_path):
    kw = tmp_path / "keywords.json"
    shutil.copy(ROOT / "config/keywords.json", kw)
    crit = ROOT / "config/criteria.yaml"
    before = kw.read_text()
    fams = load_families(kw, crit)
    save_keywords(fams, kw)
    assert kw.read_text() == before

    trade = next(f for f in fams if f.id == "trade")
    trade.keywords[0].de = [*trade.keywords[0].de, "unter uns gesagt"]
    save_keywords(fams, kw)
    old, new = json.loads(before)["keywords"], json.loads(kw.read_text())["keywords"]
    assert [k["id"] for k in new] == [k["id"] for k in old]
    changed = [k["id"] for k, o in zip(new, old, strict=True) if k != o]
    assert changed == [trade.keywords[0].id]


# --------------------------------------------------------------------------------------------
# offline end to end on the case data (reference scripts + fake LLM)
# --------------------------------------------------------------------------------------------


@pytest.mark.skipif(not (DATA / "Audio/Stufe1_D02-K1.wav").exists(), reason="case data not present")
def test_demo_offline_profile_runs_the_whole_chain(tmp_path):
    cfg = load_config("demo-offline", [f"paths.runs_dir={tmp_path}/runs", f"paths.cache_dir={tmp_path}/cache"])
    pipe = Pipeline(cfg)
    r = pipe.process(DATA / "Audio/Stufe1_D02-K1.wav")
    assert r.transcript.asr_backend == "reference" and {s.role for s in r.transcript.segments} >= {"advisor"}
    assert set(r.checks) == {"keywords", "patterns", "llm_judge", "geval"}
    assert not any(c.meta.get("error") for c in r.checks.values())
    assert r.decision.passages and all(Path(p.snippet_path).exists() for p in r.decision.passages)
    out = tmp_path / "runs/demo-offline/Stufe1_D02-K1/result.json"
    assert json.loads(out.read_text())["decision"]["label"] == r.decision.label


# --------------------------------------------------------------------------------------------
# the README's "add a plugin" example: a module:Class type, no registry edit
# --------------------------------------------------------------------------------------------


def test_readme_example_check_plugs_in_by_import_path(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT))
    cfg = make_cfg(tmp_path, checks=[
        {"name": "keywords", "type": "keywords", "weight": 0.35},
        {"name": "pressure", "type": "examples.pressure_check:PressureCheck", "weight": 0.2,
         "families": ["trade", "splitting"]}])
    pipe = Pipeline(cfg)
    t = Transcript(call_id="x", segments=[
        Segment(id="S001", start=0, end=4, text="Das muss heute noch passieren, sofort."),
        Segment(id="S002", start=5, end=9, text="Bitte niemandem sagen, das bleibt unter uns.")])
    r = pipe.process_transcript(t)
    p = r.checks["pressure"]
    assert set(p.family_scores) == {"trade", "splitting"} and p.meta["hits"] == 4
    assert p.family_scores["trade"].score == pytest.approx(1 - 0.8 ** 4, abs=1e-4)
    assert "pressure" in r.decision.families["trade"].per_check
    assert pipe.checks[1].cache_params()["families"] == ["trade", "splitting"]
    with pytest.raises(TypeError):
        Pipeline(make_cfg(tmp_path, checks=[{"name": "p", "type": "examples.pressure_check:PressureCheck",
                                             "famlies": ["trade"]}]))
