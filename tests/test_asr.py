from __future__ import annotations

import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import callguard.asr as asr_pkg
from callguard import registry
from callguard.asr import clean_text, clean_words, resolve_model
from callguard.asr import faster_whisper as fw
from callguard.asr.hf_whisper import INSTALL_HINT, HFWhisperASR, group_chunks, require_transformers
from callguard.asr.reference import ReferenceASR
from callguard.config import ROOT, load_config
from callguard.context import Context
from callguard.types import Transcript

DATA = ROOT / "data_upstream/inventx-case-study/data"
LOCAL_MODEL = ROOT / "models/asr/whisper-turbo-gsw-ct2-int8"


def make_ctx(data_dir: Path | None = None) -> Context:
    overrides = [f"paths.data_dir={data_dir}"] if data_dir else []
    return Context(load_config("base", overrides), use_cache=False)


def write_wav(path: Path, seconds: float) -> Path:
    sf.write(str(path), np.zeros(int(seconds * 16000), dtype=np.float32), 16000, subtype="PCM_16")
    return path


@pytest.fixture
def ct2_dir(tmp_path: Path) -> Path:
    d = tmp_path / "fake-ct2"
    d.mkdir()
    (d / "model.bin").write_bytes(b"")
    (d / "tokenizer.json").write_text("{}")
    return d


# -- shared helpers ------------------------------------------------------------------------------


@pytest.mark.parametrize("raw, expected", [
    (" «Grüße Frau Eibi», Claudia Frey, Sie haben nur einen Rückruf gebeten. Was möchten Sie?»",
     "Grüße Frau Eibi, Claudia Frey, Sie haben nur einen Rückruf gebeten. Was möchten Sie?"),
    ('Er sagte „Kauf das“ und "jetzt" .', "Er sagte Kauf das und jetzt."),
    ("Wie geht's? ‚Gut‘", "Wie geht's? Gut"),
    ("  viel \n\t Platz  ", "viel Platz"),
    (" «» ", ""),
])
def test_clean_text(raw: str, expected: str) -> None:
    assert clean_text(raw) == expected


def test_clean_words_glues_punctuation_and_drops_quotes() -> None:
    words = clean_words([(0.0, 0.5, " «Was", 0.9), (0.5, 0.9, " möchten", 0.8), (0.9, 1.2, " Sie", 1.0),
                         (1.2, 1.4, "?»", 0.7), (1.4, 1.5, " »", 0.5), (1.6, None, " Ja", None)])
    assert [w.text for w in words] == ["Was", "möchten", "Sie?", "Ja"]
    assert words[2].end == 1.4 and words[2].prob == 1.0
    assert words[3].end == words[3].start == 1.6 and words[3].prob is None


def test_clean_words_drops_leading_punctuation() -> None:
    assert clean_words([(0.0, 0.1, "»,", 0.9)]) == []


def test_resolve_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(asr_pkg, "ROOT", tmp_path)
    (tmp_path / "models" / "asr" / "mine").mkdir(parents=True)
    assert resolve_model("models/asr/mine") == (str(tmp_path / "models/asr/mine"), True)
    assert resolve_model(str(tmp_path / "models/asr/mine"))[1] is True
    assert resolve_model("large-v3") == ("large-v3", False)
    assert resolve_model("Systran/faster-whisper-small") == ("Systran/faster-whisper-small", False)
    for missing in ("models/asr/missing", "models/missing", "./x", str(tmp_path / "nope")):
        with pytest.raises(FileNotFoundError, match="not found"):
            resolve_model(missing)


# -- faster-whisper --------------------------------------------------------------------------------


def test_check_ct2_dir(tmp_path: Path, ct2_dir: Path) -> None:
    fw.check_ct2_dir(ct2_dir)
    (ct2_dir / "tokenizer.json").unlink()
    with pytest.raises(FileNotFoundError, match="tokenizer.json"):
        fw.check_ct2_dir(ct2_dir)
    hf = tmp_path / "hf-ckpt"
    hf.mkdir()
    (hf / "model.safetensors").write_bytes(b"")
    with pytest.raises(ValueError, match="ct2-transformers-converter"):
        fw.check_ct2_dir(hf)
    with pytest.raises(FileNotFoundError, match="model.bin"):
        fw.check_ct2_dir(tmp_path)


def test_segment_confidence() -> None:
    assert fw.segment_confidence(math.log(0.8), 0.0, []) == pytest.approx(0.8)
    assert fw.segment_confidence(math.log(0.8), 0.5, []) == pytest.approx(0.4)
    # word probabilities are per segment and win over the per-window avg_logprob
    assert fw.segment_confidence(math.log(0.8), 0.0, [0.25, 1.0]) == pytest.approx(0.5)
    assert fw.segment_confidence(0.3, -0.1, []) == 1.0
    assert fw.segment_confidence(-50.0, 1.0, [0.0]) == 0.0


def fw_word(start: float, end: float, word: str, p: float) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, word=word, probability=p)


def fw_segment(start: float, end: float, text: str, words: list[SimpleNamespace] | None = None,
               avg_logprob: float = -0.3, no_speech_prob: float = 0.0) -> SimpleNamespace:
    return SimpleNamespace(start=start, end=end, text=text, words=words, avg_logprob=avg_logprob,
                           no_speech_prob=no_speech_prob)


class FakeWhisper:
    """Stands in for faster_whisper.WhisperModel; ``fail`` raises for matching option sets."""

    def __init__(self, segments: list[SimpleNamespace], fail=lambda opts: False):
        self.segments = segments
        self.fail = fail
        self.calls: list[tuple[object, dict]] = []

    def transcribe(self, audio, **opts):
        self.calls.append((audio, opts))

        def gen():  # like faster-whisper, errors surface while iterating
            if self.fail(opts):
                raise RuntimeError("boom")
            yield from self.segments

        info = SimpleNamespace(language="de", language_probability=0.98, duration=2.0, duration_after_vad=1.5)
        return gen(), info


def install_fake(monkeypatch: pytest.MonkeyPatch, fake: FakeWhisper) -> None:
    monkeypatch.setattr(fw, "_load_model", lambda *a, **k: fake)


SEGMENTS = [
    fw_segment(0.08, 1.4, " «Was möchten Sie?»",
               [fw_word(0.08, 0.5, " «Was", 0.9), fw_word(0.5, 0.9, " möchten", 0.8),
                fw_word(0.9, 1.2, " Sie", 1.0), fw_word(1.2, 1.4, "?»", 0.7)]),
    fw_segment(1.5, 1.6, " «» ", []),
    fw_segment(1.7, 2.0, ' "Die Aktie kaufen."', None, avg_logprob=math.log(0.5), no_speech_prob=0.2),
]


def test_faster_whisper_maps_segments(tmp_path: Path, ct2_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeWhisper(SEGMENTS)
    install_fake(monkeypatch, fake)
    asr = registry.create("asr", {"type": "faster_whisper", "model": str(ct2_dir),
                                  "initial_prompt": "Bank.\n  Konto, Depot."}, ctx=make_ctx())
    wav = write_wav(tmp_path / "call.wav", 2.0)
    t = asr.transcribe(wav, "call-1")

    audio, opts = fake.calls[0]
    assert isinstance(audio, np.ndarray) and audio.dtype == np.float32 and len(audio) == 32000
    assert opts["language"] == "de" and opts["beam_size"] == 1 and opts["word_timestamps"] is True
    assert opts["initial_prompt"] == "Bank. Konto, Depot."

    assert [s.id for s in t.segments] == ["S001", "S002"]
    assert [s.text for s in t.segments] == ["Was möchten Sie?", "Die Aktie kaufen."]
    assert [w.text for w in t.segments[0].words] == ["Was", "möchten", "Sie?"]
    assert t.segments[0].confidence == pytest.approx((0.9 * 0.8 * 1.0 * 0.7) ** 0.25, abs=1e-4)
    assert t.segments[1].confidence == pytest.approx(0.4)
    assert t.segments[1].words == []
    assert (t.call_id, t.audio_path, t.duration, t.language) == ("call-1", str(wav), 2.0, "de")
    assert t.asr_backend == "faster_whisper:fake-ct2"
    assert t.meta["language_probability"] == 0.98 and t.meta["model"] == str(ct2_dir)
    assert {"elapsed_s", "params", "mean_confidence"} <= set(t.meta) and "degraded" not in t.meta
    assert Transcript.model_validate_json(t.model_dump_json()) == t  # must survive the JSON cache


def test_faster_whisper_falls_back_without_vad_and_words(tmp_path: Path, ct2_dir: Path,
                                                         monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeWhisper(SEGMENTS, fail=lambda opts: opts["word_timestamps"])
    install_fake(monkeypatch, fake)
    asr = fw.FasterWhisperASR(make_ctx(), model=str(ct2_dir))
    t = asr.transcribe(write_wav(tmp_path / "call.wav", 2.0), "call-1")
    assert len(fake.calls) == 2
    assert "boom" in t.meta["degraded"]
    assert t.meta["params"]["word_timestamps"] is False and t.meta["params"]["vad_filter"] is False
    assert [s.text for s in t.segments] == ["Was möchten Sie?", "Die Aktie kaufen."]


def test_faster_whisper_raises_when_fallback_fails_too(tmp_path: Path, ct2_dir: Path,
                                                       monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake(monkeypatch, FakeWhisper(SEGMENTS, fail=lambda opts: True))
    asr = fw.FasterWhisperASR(make_ctx(), model=str(ct2_dir))
    with pytest.raises(RuntimeError, match="fallback"):
        asr.transcribe(write_wav(tmp_path / "call.wav", 2.0), "call-1")


def test_faster_whisper_no_speech(tmp_path: Path, ct2_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake(monkeypatch, FakeWhisper([]))
    t = fw.FasterWhisperASR(make_ctx(), model=str(ct2_dir)).transcribe(write_wav(tmp_path / "s.wav", 1.0), "c")
    assert t.segments == [] and t.meta["warnings"] == ["no speech recognised"]
    assert t.meta["mean_confidence"] is None


def test_asr_params_typos_raise_but_inherited_params_are_ignored(ct2_dir: Path) -> None:
    ctx = make_ctx()
    with pytest.raises(TypeError, match="beam_sise"):
        registry.create("asr", {"type": "faster_whisper", "model": str(ct2_dir), "beam_sise": 5}, ctx=ctx)
    # base.yaml's faster-whisper keys survive the deep merge into a profile that switches asr.type
    asr = registry.create("asr", {"type": "faster_whisper", "model": str(ct2_dir), "batch_size": 8}, ctx=ctx)
    assert asr.ignored_params == {"batch_size": 8} and "batch_size" not in asr.cache_params()


def test_oracle_profile_builds_reference_asr() -> None:
    cfg = load_config("oracle")  # a profile that swaps asr.type inherits none of the parent's params
    asr = registry.create("asr", cfg.asr, ctx=Context(cfg, use_cache=False))
    assert isinstance(asr, ReferenceASR) and asr.ignored_params == {}


def test_type_switched_by_override_tolerates_inherited_params() -> None:
    cfg = load_config("local", ["asr.type=reference"])  # --set applies after the merge: keys stay
    asr = registry.create("asr", cfg.asr, ctx=Context(cfg, use_cache=False))
    assert isinstance(asr, ReferenceASR) and "model" in asr.ignored_params
    assert "model" not in asr.cache_params()


# -- reference (oracle) -------------------------------------------------------------------------


SCRIPT = """T001 · Beratung
Grüezi mitenand, wie chan ich hälfe?

T002 · Kundin
Ich möcht d Aktie chaufe.

T003 · Beratung
Guet.
"""


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "Transkript").mkdir()
    (tmp_path / "Transkript" / "Stufe9_D01.txt").write_text(SCRIPT, encoding="utf-8")
    (tmp_path / "Audio").mkdir()
    return tmp_path


def test_reference_synthetic_timings(data_dir: Path) -> None:
    asr = ReferenceASR(make_ctx(data_dir), words_per_second=2.0)
    t = asr.transcribe(data_dir / "Audio" / "missing.wav", "Stufe9_D01-K2")
    assert [s.id for s in t.segments] == ["T001", "T002", "T003"]
    assert [s.role for s in t.segments] == ["advisor", "customer", "advisor"]
    assert [s.speaker for s in t.segments] == ["Beratung", "Kundin", "Beratung"]
    assert t.segments[1].text == "Ich möcht d Aktie chaufe."
    # 6 words / 2 wps = 3 s, gap 0.4 s, 5 words = 2.5 s, gap, 1 word = 0.5 s
    assert [(s.start, s.end) for s in t.segments] == [(0.0, 3.0), (3.4, 5.9), (6.3, 6.8)]
    assert all(s.confidence == 1.0 for s in t.segments)
    assert [w.text for w in t.segments[2].words] == ["Guet."]
    assert t.asr_backend == "reference" and t.meta["oracle"] is True and t.meta["time_scale"] == 1.0
    assert t.duration == 6.8


def test_reference_scales_to_audio(data_dir: Path) -> None:
    wav = write_wav(data_dir / "Audio" / "Stufe9_D01-K1.wav", 13.6)
    t = registry.create("asr", {"type": "reference", "words_per_second": 2.0}, ctx=make_ctx(data_dir)) \
        .transcribe(wav, "Stufe9_D01-K1")
    assert t.meta["time_scale"] == 2.0 and t.duration == 13.6
    assert t.segments[-1].end == pytest.approx(13.6)
    assert t.segments[1].start == pytest.approx(6.8)
    unscaled = ReferenceASR(make_ctx(data_dir), words_per_second=2.0, scale_to_audio=False)
    assert unscaled.transcribe(wav, "Stufe9_D01-K1").segments[-1].end == 6.8


def test_reference_missing_script_is_a_clear_error(data_dir: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Stufe9_D99-K1"):
        ReferenceASR(make_ctx(data_dir)).transcribe(None, "Stufe9_D99-K1")


@pytest.mark.skipif(not (DATA / "Transkript" / "Stufe1_D02.txt").exists(), reason="case data missing")
def test_reference_on_case_data() -> None:
    wav = DATA / "Audio" / "Stufe1_D02-K1.wav"
    t = ReferenceASR(make_ctx()).transcribe(wav, "Stufe1_D02-K1")
    assert t.segments[0].id == "T001" and t.segments[0].role == "advisor"
    assert t.segments[-1].end == pytest.approx(t.duration, abs=0.01)
    assert 0.5 < t.meta["time_scale"] < 2.0  # 2.2 words/s is close to the case's speaking rate


# -- transformers backend --------------------------------------------------------------------------


def chunk(text: str, start: float, end: float | None) -> dict:
    return {"text": text, "timestamp": (start, end)}


def test_group_chunks_words() -> None:
    chunks = [chunk(" «Grüezi", 0.0, 0.4), chunk(" Frau", 0.4, 0.7), chunk(" Aebi.»", 0.7, 1.0),
              chunk(" Ich", 1.1, 1.3), chunk(" möchte", 1.3, 1.6),  # no punctuation, then a pause
              chunk(" Aktien", 2.6, 3.0), chunk(" kaufen", 3.0, 3.4), chunk("?", 3.4, None)]
    segs = group_chunks(chunks, duration=10.0)
    assert [s.text for s in segs] == ["Grüezi Frau Aebi.", "Ich möchte", "Aktien kaufen?"]
    assert [s.id for s in segs] == ["S001", "S002", "S003"]
    assert (segs[1].start, segs[1].end) == (1.1, 1.6)
    assert segs[2].end == 3.4  # the trailing "?" has no end time; the word before it does
    assert segs[0].confidence is None


def test_group_chunks_open_last_word_and_max_words() -> None:
    segs = group_chunks([chunk(f" w{i}", i * 0.3, i * 0.3 + 0.3) for i in range(5)] + [chunk(" Ende", 9.8, None)],
                        max_words=3, duration=10.0)
    assert [len(s.words) for s in segs] == [3, 2, 1]
    assert (segs[-1].start, segs[-1].end) == (9.8, 9.8)


def test_group_chunks_segment_level() -> None:
    segs = group_chunks([chunk(" «Grüezi Frau Aebi.»", 0.0, 2.0), chunk(" «»", 2.0, 2.5),
                         chunk(" Ich möchte kaufen.", 2.5, None)], word_level=False, duration=7.0)
    assert [(s.id, s.text, s.start, s.end) for s in segs] == [
        ("S001", "Grüezi Frau Aebi.", 0.0, 2.0), ("S002", "Ich möchte kaufen.", 2.5, 7.0)]
    assert segs[0].words == []


def test_hf_whisper_import_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "transformers", None)
    monkeypatch.setitem(sys.modules, "torch", None)
    with pytest.raises(ImportError, match=INSTALL_HINT):
        require_transformers()
    asr = registry.create("asr", {"type": "hf_whisper", "model": "Flix-AI/flix-swissgerman-full"}, ctx=make_ctx())
    assert isinstance(asr, HFWhisperASR) and asr.name == "Flix-AI/flix-swissgerman-full"
    with pytest.raises(ImportError, match="uv pip install transformers torch accelerate"):
        asr.transcribe(write_wav(tmp_path / "x.wav", 0.5), "x")


# -- real model (slow) ---------------------------------------------------------------------------


@pytest.mark.slow
def test_faster_whisper_real_excerpt(tmp_path: Path) -> None:
    pytest.importorskip("faster_whisper")
    src = DATA / "Audio" / "Stufe1_D02-K1.wav"
    if not (LOCAL_MODEL / "model.bin").exists() or not src.exists():
        pytest.skip("local Whisper model or case audio missing")
    from callguard.audio import cut

    excerpt = cut(src, 0.0, 25.0, tmp_path / "excerpt.wav")
    cfg = load_config("local")  # the real profile, including the initial_prompt
    asr = registry.create("asr", cfg.asr, ctx=Context(cfg, use_cache=False))
    t = asr.transcribe(excerpt, "excerpt")

    assert t.asr_backend == "faster_whisper:whisper-turbo-gsw-ct2-int8"
    assert t.language == "de" and t.duration == pytest.approx(25.0, abs=0.01)
    assert t.segments and t.segments[0].id == "S001"
    text = t.text().lower()
    assert not any(q in text for q in "«»\"")
    assert sum(k in text for k in ("rückruf", "fonds", "auftrag", "sparplan", "aktie")) >= 2
    for s in t.segments:
        assert 0.0 <= s.start <= s.end <= 25.5 and 0.0 < s.confidence <= 1.0
        assert s.words and all(s.start - 0.5 <= w.start <= w.end <= s.end + 0.5 for w in s.words)
    assert "degraded" not in t.meta and t.meta["elapsed_s"] > 0
