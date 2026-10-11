"""Audio pre-processors (plugin kind ``preprocess``, docs/design/v2_plan.md §7 A10): the ``none`` path,
ASR cache keys (v1 keys unchanged unless a pre-processor is set), the on-disk cache of processed audio,
original audio for transcripts/snippets, and the sherpa-onnx denoiser on synthetic noise."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf

from callguard import pipeline as pipeline_mod
from callguard import preprocess, registry
from callguard.audio import load_audio
from callguard.cache import Cache, stable_hash
from callguard.config import ROOT, AppConfig, Paths
from callguard.context import Context
from callguard.pipeline import Pipeline
from callguard.plugins import ASRBackend, Preprocessor
from callguard.types import Segment, Transcript

SR = 16000
DPDFNET = ROOT / "models/denoise/dpdfnet2.onnx"
GTCRN = ROOT / "models/denoise/gtcrn_simple.onnx"
CASE_AUDIO = ROOT / "data_upstream/inventx-case-study/data/Audio"

# v1 ASR key of PIN_ASR with file_hash "a"*16 (same pin as tests/test_views.py V1_KEYS[0])
V1_ASR_KEY = "dc2f87bf79b9e2da"
PIN_ASR = {"type": "faster_whisper", "model": "tiny", "device": "cpu", "compute_type": "int8", "language": "de",
           "beam_size": 1, "vad_filter": True, "word_timestamps": True,
           "initial_prompt": "Telefongespräch einer Schweizer Bank."}
SEEN: dict[str, list[Any]] = {"asr_paths": [], "asr_rms": [], "processed": []}


@pytest.fixture(autouse=True)
def _reset():
    for v in SEEN.values():
        v.clear()


@registry.register("asr", "test_pre_probe")
class ProbeASR(ASRBackend):
    """Records which file it was given and how loud it is (the halving pre-processor halves it)."""

    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        x = load_audio(audio_path)
        SEEN["asr_paths"].append(Path(audio_path))
        SEEN["asr_rms"].append(float(np.sqrt((x ** 2).mean())))
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=len(x) / SR,
                          segments=[Segment(id="S001", start=0.0, end=1.0, text="Grüezi")], asr_backend="probe")


@registry.register("preprocess", "test_pre_half")
class HalfPre(Preprocessor):
    def __init__(self, ctx, gain: float = 0.5):
        super().__init__(ctx, gain=gain)

    def process(self, samples: np.ndarray, sr: int) -> np.ndarray:
        SEEN["processed"].append(len(samples))
        return (samples * self.params["gain"])[:-7]  # a few samples short, like frame-based models


@pytest.fixture
def wav(tmp_path: Path) -> Path:
    p = tmp_path / "call.wav"
    t = np.arange(3 * SR) / SR
    sf.write(p, (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32), SR, subtype="PCM_16")
    return p


def make_cfg(tmp_path: Path, asr: dict[str, Any], **kw: Any) -> AppConfig:
    base: dict[str, Any] = dict(
        name="pre-test", paths=Paths(cache_dir=str(tmp_path / "cache"), runs_dir=str(tmp_path / "runs")),
        asr=asr, diarizer={"type": "none"}, checks=[{"name": "keywords", "type": "keywords", "weight": 0.35}],
        sinks=[])
    base.update(kw)
    return AppConfig(**base)


class KeyCache(Cache):
    def __init__(self, root: Path):
        super().__init__(root, enabled=False)
        self.keys: list[tuple[str, str, Any]] = []

    def get_or_compute(self, namespace, key, model, fn, store=None):
        self.keys.append((namespace, stable_hash(key), key))
        return Transcript(call_id="pin", segments=[], asr_backend="pin"), True


def asr_key(tmp_path: Path, monkeypatch, asr: dict[str, Any], **kw: Any) -> tuple[str, Any]:
    monkeypatch.setattr(pipeline_mod, "file_hash", lambda p: "a" * 16)
    pipe = Pipeline(make_cfg(tmp_path, asr, **kw))
    pipe.ctx.cache = KeyCache(tmp_path / "cache")
    pipe.transcribe(Path("/nonexistent.wav"), "pin", view=kw.get("primary_view"))
    (ns, h, key), = pipe.ctx.cache.keys
    assert ns == "asr"
    return h, key


# --------------------------------------------------------------------------------------------
# cache keys
# --------------------------------------------------------------------------------------------


def test_no_preprocess_keeps_the_v1_asr_key(tmp_path, monkeypatch):
    assert asr_key(tmp_path, monkeypatch, PIN_ASR)[0] == V1_ASR_KEY


@pytest.mark.parametrize("pre", [None, "none", {"type": "none"}])
def test_none_preprocess_keeps_the_v1_asr_key(tmp_path, monkeypatch, pre):
    h, key = asr_key(tmp_path, monkeypatch, {**PIN_ASR, "preprocess": pre})
    assert h == V1_ASR_KEY and "preprocess" not in key


def test_preprocess_enters_the_key_only_when_set(tmp_path, monkeypatch):
    h, key = asr_key(tmp_path, monkeypatch, {**PIN_ASR, "preprocess": {"type": "test_pre_half", "gain": 0.5}})
    assert h != V1_ASR_KEY
    assert key["preprocess"] == {"type": "test_pre_half", "gain": 0.5}
    assert "preprocess" not in key["asr"]  # the ASR plugin never sees the block
    h2, _ = asr_key(tmp_path, monkeypatch, {**PIN_ASR, "preprocess": {"type": "test_pre_half", "gain": 0.4}})
    assert h2 != h


def test_view_can_switch_an_inherited_preprocess_off(tmp_path, monkeypatch):
    views = {"de": {"lang": "de", "asr": {"preprocess": {"type": "none"}}}}
    h, key = asr_key(tmp_path, monkeypatch, {**PIN_ASR, "preprocess": {"type": "test_pre_half"}},
                     views=views, primary_view="de")
    assert h == V1_ASR_KEY and "preprocess" not in key


def test_asr_plugins_accept_the_block_and_keep_their_params(tmp_path):
    ctx = Context(make_cfg(tmp_path, PIN_ASR), use_cache=False)
    asr = registry.create("asr", {**PIN_ASR, "preprocess": {"type": "denoise_sherpa"}}, ctx=ctx)
    assert asr.preprocess == {"type": "denoise_sherpa"}
    assert asr.cache_params() == registry.create("asr", PIN_ASR, ctx=ctx).cache_params()
    assert registry.create("asr", PIN_ASR, ctx=ctx).preprocess is None


def test_none_preprocessor_is_identity_and_rejects_params(tmp_path):
    ctx = Context(make_cfg(tmp_path, PIN_ASR), use_cache=False)
    pre = registry.create("preprocess", "none", ctx=ctx)
    x = np.ones(10, dtype=np.float32)
    assert pre.identity and pre.process(x, SR) is x and not preprocess.is_active(pre)
    with pytest.raises(TypeError):
        registry.create("preprocess", {"type": "none", "model": "x"}, ctx=ctx)


# --------------------------------------------------------------------------------------------
# pipeline: processed audio for the ASR only, cached on disk
# --------------------------------------------------------------------------------------------


def test_asr_hears_processed_audio_cached_on_disk(tmp_path, wav):
    asr = {"type": "test_pre_probe", "preprocess": {"type": "test_pre_half"}}
    pipe = Pipeline(make_cfg(tmp_path, asr))
    t = pipe.transcribe(wav, "c1")
    processed = SEEN["asr_paths"][0]
    assert processed.parent == tmp_path / "cache" / "preprocess"
    assert processed.name.endswith(".wav") and "-" in processed.name
    assert sf.info(str(processed)).frames == sf.info(str(wav)).frames  # padded back to full length
    assert SEEN["asr_rms"][0] == pytest.approx(0.2 / np.sqrt(2) / 2, rel=0.02)
    assert t.audio_path == str(wav)  # timestamps / snippets refer to the original
    assert t.meta["preprocess"]["params"] == {"type": "test_pre_half", "gain": 0.5}
    assert t.meta["preprocess"]["cached"] is False

    # another ASR config on the same audio + pre-processor: the processed file is reused
    pipe2 = Pipeline(make_cfg(tmp_path, {**asr, "variant": "other"}))
    pipe2.transcribe(wav, "c1")
    assert SEEN["processed"] == [3 * SR] and SEEN["asr_paths"][1] == processed
    # the transcript itself is cached under the preprocess-aware key
    Pipeline(make_cfg(tmp_path, asr)).transcribe(wav, "c1")
    assert len(SEEN["asr_paths"]) == 2


def test_cache_lookups_elsewhere_use_the_preprocess_aware_key(tmp_path, wav):
    """asr-eval and the experiment dry run look transcripts up by Pipeline.asr_key, not a hand-built key."""
    from callguard.eval_asr import asr_cache_key

    asr = {"type": "test_pre_probe", "preprocess": {"type": "test_pre_half"}}
    pipe = Pipeline(make_cfg(tmp_path, asr))
    pipe.transcribe(wav, "c1")
    key = pipe.asr_key(wav)
    assert "preprocess" in key and asr_cache_key(pipe, wav) == key
    assert pipe.ctx.cache.get("asr", key, Transcript) is not None


def test_process_keeps_original_audio_for_snippets(tmp_path, wav):
    asr = {"type": "test_pre_probe", "preprocess": {"type": "test_pre_half"}}
    pipe = Pipeline(make_cfg(tmp_path, asr))
    r = pipe.process(wav, "c1", emit=False)
    assert r.audio_path == str(wav) and r.transcript.audio_path == str(wav)
    assert r.meta["provenance"]["views"]["main"]["params"]["preprocess"] == {"type": "test_pre_half", "gain": 0.5}
    plain = Pipeline(make_cfg(tmp_path / "plain", {"type": "test_pre_probe"})).process(wav, "c1", emit=False)
    assert "preprocess" not in plain.meta["provenance"]["views"]["main"]["params"]


def test_no_cache_uses_a_temp_file(tmp_path, wav):
    asr = {"type": "test_pre_probe", "preprocess": {"type": "test_pre_half"}}
    Pipeline(make_cfg(tmp_path, asr), use_cache=False).transcribe(wav, "c1")
    assert not (tmp_path / "cache" / "preprocess").exists()
    assert not SEEN["asr_paths"][0].exists()


# --------------------------------------------------------------------------------------------
# sherpa-onnx denoiser (model files are not in git: scripts/download_models.sh denoise)
# --------------------------------------------------------------------------------------------


def noisy_bursts(seconds: int = 6) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(SR * seconds) / SR
    gate = ((t % 2) < 1).astype(np.float32)  # 1 s tone, 1 s pause
    rng = np.random.default_rng(0)
    x = (0.3 * np.sin(2 * np.pi * 440 * t) * gate + 0.03 * rng.standard_normal(len(t))).astype(np.float32)
    return x, gate


@pytest.mark.parametrize("model", [DPDFNET, GTCRN], ids=["dpdfnet", "gtcrn"])
def test_sherpa_denoiser_removes_noise(tmp_path, model):
    if not model.exists():
        pytest.skip(f"{model.name} not downloaded (scripts/download_models.sh denoise)")
    ctx = Context(make_cfg(tmp_path, PIN_ASR), use_cache=False)
    pre = registry.create("preprocess", {"type": "denoise_sherpa", "model": str(model), "num_threads": 2}, ctx=ctx)
    x, gate = noisy_bursts()
    y = pre.process(x, SR)
    assert y.dtype == np.float32 and len(y) == len(x) and np.isfinite(y).all()
    gap = gate == 0
    rms = lambda a: float(np.sqrt((a ** 2).mean()))  # noqa: E731
    assert rms(y[gap]) < rms(x[gap]) / 10  # > 20 dB less noise in the pauses
    assert "num_threads" not in pre.cache_params() and pre.cache_params()["arch"] in ("dpdfnet", "gtcrn")


def test_sherpa_denoiser_mix_blends_with_the_original(tmp_path):
    if not DPDFNET.exists():
        pytest.skip("dpdfnet2.onnx not downloaded (scripts/download_models.sh denoise)")
    ctx = Context(make_cfg(tmp_path, PIN_ASR), use_cache=False)
    x, _ = noisy_bursts(2)
    full = registry.create("preprocess", {"type": "denoise_sherpa"}, ctx=ctx).process(x, SR)
    half = registry.create("preprocess", {"type": "denoise_sherpa", "mix": 0.5}, ctx=ctx).process(x, SR)
    np.testing.assert_allclose(half, 0.5 * full + 0.5 * x, atol=1e-5)


def test_sherpa_denoiser_param_errors(tmp_path):
    ctx = Context(make_cfg(tmp_path, PIN_ASR), use_cache=False)
    with pytest.raises(FileNotFoundError, match="download_models.sh denoise"):
        registry.create("preprocess", {"type": "denoise_sherpa", "model": "models/denoise/nope.onnx"}, ctx=ctx)
    if DPDFNET.exists():
        with pytest.raises(ValueError):
            registry.create("preprocess", {"type": "denoise_sherpa", "mix": 1.5}, ctx=ctx)
        with pytest.raises(TypeError):
            registry.create("preprocess", {"type": "denoise_sherpa", "atten": 12}, ctx=ctx)


@pytest.mark.slow
def test_sherpa_denoiser_keeps_clean_speech(tmp_path):
    clean = CASE_AUDIO / "Stufe1_D01-K1.wav"
    if not (DPDFNET.exists() and clean.exists()):
        pytest.skip("needs dpdfnet2.onnx and the case audio")
    ctx = Context(make_cfg(tmp_path, PIN_ASR), use_cache=False)
    x = load_audio(clean)[: 30 * SR]
    y = registry.create("preprocess", {"type": "denoise_sherpa"}, ctx=ctx).process(x, SR)
    removed = float(np.sqrt(((x - y) ** 2).mean()) / np.sqrt((x ** 2).mean()))
    assert removed < 0.1  # clean TTS speech: < -20 dB change
