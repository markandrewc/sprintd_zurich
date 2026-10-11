"""Tests for speaker separation: turn -> word mapping, re-splitting, re-clustering, roles.

Everything runs offline with synthetic transcripts, synthetic turns and stub LLMs/embedders, except
the ``slow`` tests: real sherpa-onnx diarization of a case call, and one role question to the shared
local LLM server (both skipped when models / audio / server are missing).
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pytest

from callguard import registry
from callguard.config import ROOT, AppConfig, Paths, load_config
from callguard.context import Context
from callguard.diarization import (FIRST_SPEAKER_CONFIDENCE, Turn, TurnIndex, apply_turns, assign_roles,
                                   drop_inherited, role_context, role_messages, runs, smooth_labels)
from callguard.diarization.none import NoDiarizer
from callguard.diarization.sherpa import SherpaDiarizer, cluster_embeddings, name_turns, recluster_turns
from callguard.plugins import LLM
from callguard.types import Segment, Transcript, Word

DATA = ROOT / "data_upstream" / "inventx-case-study" / "data"
LIVE_URL = "http://127.0.0.1:8001/v1"
LIVE_MODEL = "qwen2.5-1.5b-instruct"


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------


def words(start: float, end: float, step: float = 0.5, prefix: str = "w") -> list[Word]:
    out, t = [], start
    while t + step <= end + 1e-9:
        out.append(Word(start=round(t, 3), end=round(t + step * 0.8, 3), text=f"{prefix}{len(out)}"))
        t += step
    return out


def seg(seg_id: str, ws: list[Word], **kw: Any) -> Segment:
    return Segment(id=seg_id, start=ws[0].start, end=ws[-1].end, text=" ".join(w.text for w in ws),
                   words=ws, **kw)


def dialogue(lines: list[tuple[str, str]], seconds: float = 5.0) -> Transcript:
    """Segments with speakers but no roles, as a diarizer leaves them before role assignment."""
    segs = [Segment(id=f"S{i + 1:03d}", start=i * seconds, end=(i + 1) * seconds - 0.5, text=text, speaker=spk)
            for i, (spk, text) in enumerate(lines)]
    return Transcript(call_id="synthetic", segments=segs, duration=len(lines) * seconds)


BANK_CALL = [
    ("SPK0", "Grüezi Frau Aebi, hier ist Claudia Frei von der Bank. Wie kann ich Ihnen helfen?"),
    ("SPK1", "Ich möchte mich über einzelne Aktien informieren, einen Auftrag habe ich noch nicht erteilt."),
    ("SPK0", "Gerne. Haben Sie schon einen Betrag im Kopf?"),
    ("SPK1", "Etwa achttausend Franken aus meinem Sparkonto."),
]


class StubLLM(LLM):
    """Scripted LLM: ``reply(messages, json_schema) -> str`` (or an Exception to raise)."""

    plugin_kind = "llm"
    plugin_type = "stub"

    def __init__(self, reply: Callable[..., Any]):
        super().__init__(None, model="stub")
        self.reply = reply
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        self.calls.append({"messages": messages, "json_schema": json_schema, "max_tokens": max_tokens})
        out = self.reply(messages, json_schema)
        if isinstance(out, Exception):
            raise out
        return [out] * n


def answer(advisor: str, confidence: float, reason: str = "Begrüsst im Namen der Bank.") -> str:
    return json.dumps({"reason": reason, "advisor": advisor, "confidence": confidence})


_BLOCK = re.compile(r"Speaker (\S+) says:\n((?:- .*(?:\n|$))+)")


def reads(marker: str, confidence: float = 0.9) -> Callable[..., str]:
    """A stub that reads the content: names the speaker whose lines contain ``marker``."""
    def reply(messages, schema):
        for spk, body in _BLOCK.findall(messages[-1]["content"]):
            if marker in body:
                return answer(spk, confidence)
        raise AssertionError("marker not in prompt")
    return reply


class FakeEmbedder:
    """Stands in for sherpa's SpeakerEmbeddingExtractor: the 'voice' is the mean sample value."""

    class Stream:
        def __init__(self):
            self.samples = np.zeros(0, dtype=np.float32)

        def accept_waveform(self, sr, samples):
            self.samples = np.concatenate([self.samples, samples])

        def input_finished(self):
            pass

    def create_stream(self):
        return self.Stream()

    def is_ready(self, stream):
        return len(stream.samples) > 0

    def compute(self, stream):
        m = float(stream.samples.mean())
        return [m, 0.2, 0.0]


@pytest.fixture
def ctx(tmp_path) -> Context:
    cfg = AppConfig(name="test", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    return Context(cfg)


def use_llm(ctx: Context, monkeypatch, llm: LLM) -> LLM:
    monkeypatch.setattr(ctx, "llm", lambda name="default": llm)
    return llm


# --------------------------------------------------------------------------------------------
# turns -> words -> segments
# --------------------------------------------------------------------------------------------


def test_turn_index_max_overlap_then_nearest():
    idx = TurnIndex([Turn(0.0, 5.0, "SPK0"), Turn(6.0, 10.0, "SPK1"), Turn(10.0, 12.0, "SPK0")])
    assert idx.speaker(1.0, 2.0) == "SPK0"
    assert idx.speaker(4.5, 6.8) == "SPK1"  # 0.5 s with SPK0, 0.8 s with SPK1
    assert idx.speaker(9.0, 11.5) == "SPK0"  # 1.0 s SPK1 vs 1.5 s SPK0
    assert idx.speaker(5.2, 5.4) == "SPK0"  # in the pause, nearer to the end of SPK0's turn
    assert idx.speaker(5.7, 5.9) == "SPK1"
    assert idx.speaker(7.0, 7.0) == "SPK1"  # zero-length word inside a turn
    assert idx.speaker(30.0, 31.0) == "SPK0"  # after the last turn
    assert TurnIndex([]).speaker(0, 1) is None


def test_resplit_splits_segment_at_speaker_change_and_renumbers():
    first = seg("S001", words(0.0, 4.0), confidence=0.9)
    mixed_words = words(4.0, 8.0, prefix="a") + words(8.0, 12.0, prefix="b")
    mixed = seg("S002", mixed_words, confidence=0.6)
    last = seg("S003", words(12.0, 14.0, prefix="c"), confidence=0.8)
    turns = [Turn(0.0, 7.9, "SPK0"), Turn(8.1, 12.0, "SPK1"), Turn(12.2, 14.0, "SPK0")]

    out = apply_turns([first, mixed, last], turns)

    assert [s.id for s in out] == ["S001", "S002", "S003", "S004"]
    assert [s.speaker for s in out] == ["SPK0", "SPK0", "SPK1", "SPK0"]
    a, b = out[1], out[2]
    assert a.text == " ".join(f"a{i}" for i in range(8)) and b.text == " ".join(f"b{i}" for i in range(8))
    assert [w.text for w in a.words + b.words] == [w.text for w in mixed_words]
    assert a.start == mixed.start and b.end == mixed.end  # outer bounds kept
    assert a.end == mixed_words[7].end and b.start == mixed_words[8].start  # split on word times
    assert a.confidence == b.confidence == 0.6
    assert all(s.role == "unknown" for s in out)
    assert out[0].text == first.text and out[0].words == first.words


def test_no_split_keeps_ids_text_and_bounds():
    segs = [seg("T001", words(0.0, 4.0), role="advisor", speaker="Beratung"), seg("T002", words(5.0, 9.0))]
    out = apply_turns(segs, [Turn(0.0, 4.5, "SPK0"), Turn(4.8, 9.0, "SPK1")])
    assert [s.id for s in out] == ["T001", "T002"]
    assert [(s.speaker, s.role) for s in out] == [("SPK0", "unknown"), ("SPK1", "unknown")]
    assert [(s.start, s.end, s.text) for s in out] == [(x.start, x.end, x.text) for x in segs]
    assert segs[0].speaker == "Beratung" and segs[0].role == "advisor"  # input untouched


def test_segments_without_words_or_resplit_off_use_majority_overlap():
    no_words = Segment(id="S001", start=0.0, end=10.0, text="ganzer Satz")
    with_words = seg("S002", words(10.0, 12.0) + words(12.0, 20.0, prefix="b"))
    turns = [Turn(0.0, 3.0, "SPK0"), Turn(3.0, 12.0, "SPK1"), Turn(12.0, 20.0, "SPK0")]

    out = apply_turns([no_words, with_words], turns, resplit=False)
    assert [(s.id, s.speaker) for s in out] == [("S001", "SPK1"), ("S002", "SPK0")]

    out = apply_turns([no_words, with_words], turns, resplit=True)
    assert [(s.id, s.speaker) for s in out] == [("S001", "SPK1"), ("S002", "SPK1"), ("S003", "SPK0")]


def test_empty_pieces_are_dropped():
    ws = words(0.0, 4.0) + [Word(start=5.0, end=5.5, text=" "), Word(start=5.5, end=6.0, text="")]
    out = apply_turns([seg("S001", ws)], [Turn(0.0, 4.2, "SPK0"), Turn(4.8, 6.0, "SPK1")])
    assert [(s.id, s.speaker, s.text) for s in out] == [("S001", "SPK0", " ".join(f"w{i}" for i in range(8)))]


def test_short_interior_flip_is_smoothed_but_edges_and_long_runs_survive():
    starts = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    ends = [s + 0.2 for s in starts]
    assert smooth_labels(starts, ends, list("AABAAA"), 0.3) == list("AAAAAA")
    assert smooth_labels(starts, ends, list("BAAAAA"), 0.3) == list("BAAAAA")  # edge: real speaker change
    assert smooth_labels(starts, ends, list("AABBAA"), 0.3) == list("AABBAA")  # two words, 0.7 s: real
    assert smooth_labels(starts, ends, list("AABBAA"), 1.0) == list("AAAAAA")  # ... unless below min_duration
    assert smooth_labels(starts, ends, list("AABCCC"), 0.3) == list("AABCCC")  # not enclosed by one speaker
    assert smooth_labels(starts, ends, list("AABAAA"), 0.0, max_words=0) == list("AABAAA")
    assert runs("aabba") == [(0, 2, "a"), (2, 4, "b"), (4, 5, "a")] and runs([]) == []


def test_resplit_ignores_single_word_jitter():
    ws = words(0.0, 6.0)
    out = apply_turns([seg("S001", ws)], [Turn(0.0, 2.0, "SPK0"), Turn(2.0, 2.3, "SPK1"),
                                         Turn(2.3, 6.0, "SPK0")], min_run=0.3)
    assert [(s.id, s.speaker) for s in out] == [("S001", "SPK0")]


# --------------------------------------------------------------------------------------------
# re-clustering
# --------------------------------------------------------------------------------------------


def test_cluster_embeddings_separates_close_voices_and_ignores_outlier():
    rng = np.random.default_rng(1)
    base = rng.normal(size=16)
    a, b = base + 0.35 * rng.normal(size=16), base + 0.35 * rng.normal(size=16)  # similar voices
    truth = [0, 1] * 8
    emb = np.stack([(a if t == 0 else b) + 0.05 * rng.normal(size=16) for t in truth])
    emb = np.vstack([emb, rng.normal(size=16)])  # one odd short turn
    emb /= np.linalg.norm(emb, axis=1, keepdims=True)
    w = np.array([5.0] * 16 + [0.3])

    labels, margins = cluster_embeddings(emb, w, 2)
    first = labels[:16]
    assert len(set(first)) == 2
    assert all((first[i] == first[0]) == (truth[i] == 0) for i in range(16))
    assert np.median(margins[:16]) > 0
    again, _ = cluster_embeddings(emb, w, 2)
    assert (again == labels).all()  # seeded: same input, same answer

    one, m1 = cluster_embeddings(emb[:1], w[:1], 2)
    assert one.tolist() == [0] and m1.tolist() == [1.0]


def test_recluster_turns_with_stub_embedder_drops_unembeddable_turns():
    sr = 16000
    audio = np.zeros(20 * sr, dtype=np.float32)
    raw = [(0.0, 3.0, 0), (4.0, 7.0, 0), (8.0, 8.1, 0), (9.0, 12.0, 0), (13.0, 16.0, 0)]
    for (start, end, _), level in zip(raw, [0.5, -0.5, 0.5, 0.5, -0.5]):
        audio[int(start * sr):int(end * sr)] = level

    labels, info = recluster_turns(FakeEmbedder(), audio, raw, 2)

    assert labels[2] is None and info["dropped_turns"] == 1  # 0.1 s: too short to embed
    assert labels[0] == labels[3] != labels[1] == labels[4]
    turns = name_turns(raw, labels)
    assert [t.speaker for t in turns] == ["SPK0", "SPK1", "SPK0", "SPK1"]
    assert turns[1] == Turn(4.0, 7.0, "SPK1")


def test_name_turns_numbers_speakers_by_first_appearance():
    raw = [(0.0, 1.0, 7), (1.0, 2.0, 3), (2.0, 3.0, 7)]
    assert [t.speaker for t in name_turns(raw, [5, 2, 5])] == ["SPK0", "SPK1", "SPK0"]


# --------------------------------------------------------------------------------------------
# roles
# --------------------------------------------------------------------------------------------


def test_first_speaker_is_advisor_and_extra_speakers_are_customers():
    t = dialogue([("SPK1", "Bank, guten Tag"), ("SPK0", "Hallo"), ("SPK2", "Ich bin der Ehemann")])
    info = assign_roles(t.segments, "first_speaker_advisor")
    assert [s.role for s in t.segments] == ["advisor", "customer", "customer"]
    assert info["role_method"] == "first_speaker_advisor"
    assert info["role_confidence"] == FIRST_SPEAKER_CONFIDENCE
    assert info["roles"] == {"SPK1": "advisor", "SPK0": "customer", "SPK2": "customer"}


def test_single_speaker_and_disabled_roles_stay_unknown():
    t = dialogue([("SPK0", "a"), ("SPK0", "b")])
    t.segments[0].role = "advisor"
    info = assign_roles(t.segments, "first_speaker_advisor")
    assert {s.role for s in t.segments} == {"unknown"} and info["role_method"] == "none"
    assert "1 speaker" in info["role_reason"]
    assert assign_roles(dialogue(BANK_CALL).segments, "none")["role_method"] == "none"
    with pytest.raises(ValueError):
        assign_roles(t.segments, "guess")


def test_llm_roles_prompt_schema_and_parse():
    t = dialogue([("SPK1", "Grüezi, hier ist die Bank, Claudia Frei."), ("SPK0", "Ich möchte Aktien kaufen."),
                  ("SPK1", "Gerne, welchen Betrag?"), ("SPK0", "Achttausend Franken.")])
    llm = StubLLM(reads("hier ist die Bank"))

    info = assign_roles(t.segments, "llm", llm=lambda: llm, context_segments=3)

    assert info["role_method"] == "llm" and info["role_confidence"] == 0.9
    assert info["role_reason"] == "Begrüsst im Namen der Bank."
    assert info["roles"] == {"SPK1": "advisor", "SPK0": "customer"}
    assert [s.role for s in t.segments] == ["advisor", "customer", "advisor", "customer"]
    assert len(llm.calls) == 2  # asked again with the labels rotated
    first, second = (c["messages"][-1]["content"] for c in llm.calls)
    assert "Speaker SPK0 says:\n- Ich möchte Aktien kaufen.\n\nSpeaker SPK1 says:\n- Grüezi, hier ist die Bank" in first
    assert "- Gerne, welchen Betrag?" in first and "Achttausend" not in first  # first 3 segments only
    assert "Speaker SPK0 says:\n- Grüezi, hier ist die Bank" in second
    schema = llm.calls[0]["json_schema"]
    assert schema["properties"]["advisor"]["enum"] == ["SPK0", "SPK1"]
    assert set(schema["required"]) == {"advisor", "confidence", "reason"}
    assert "Beratung" in llm.calls[0]["messages"][0]["content"]


@pytest.mark.parametrize("reply, why", [
    (reads("Wie kann ich Ihnen helfen", confidence=0.3), "LLM unsure"),
    (lambda m, s: answer("SPK1", 0.95), "follows the speaker labels"),  # position/label bias
    (lambda m, s: RuntimeError("server down"), "server down"),
    (lambda m, s: "keine Ahnung", "LLM failed"),
    (lambda m, s: answer("SPK7", 0.9), "LLM failed"),
])
def test_llm_roles_fall_back_to_first_speaker(reply, why):
    t = dialogue(BANK_CALL)
    info = assign_roles(t.segments, "llm", llm=lambda: StubLLM(reply))
    assert info["role_method"] == "first_speaker_advisor"
    assert why in info["role_reason"] and "SPK0 taken as advisor" in info["role_reason"]
    assert [s.role for s in t.segments] == ["advisor", "customer", "advisor", "customer"]


def test_swap_check_can_be_disabled():
    llm = StubLLM(lambda m, s: answer("SPK1", 0.95))
    t = dialogue(BANK_CALL)
    info = assign_roles(t.segments, "llm", llm=lambda: llm, swap_check=False)
    assert info["role_method"] == "llm" and len(llm.calls) == 1
    assert info["roles"] == {"SPK0": "customer", "SPK1": "advisor"}


def test_role_context_includes_every_speaker():
    t = dialogue([("SPK0", f"Monolog {i}") for i in range(20)] + [("SPK1", "Ja."), ("SPK1", "Gut.")])
    ctx_segs = role_context(t.segments, 12)
    assert len(ctx_segs) == 14 and [s.text for s in ctx_segs[-2:]] == ["Ja.", "Gut."]


def test_llm_factory_failure_falls_back():
    def missing():
        raise KeyError("LLM 'default' not configured")

    t = dialogue(BANK_CALL)
    assert assign_roles(t.segments, "llm", llm=missing)["role_method"] == "first_speaker_advisor"


def test_role_prompt_truncates_long_lines():
    t = dialogue([("SPK0", "Wort " * 400), ("SPK1", "kurz")])
    user = role_messages(t.segments, 12)[-1]["content"]
    assert len(user) < 2000 and "kurz" in user


# --------------------------------------------------------------------------------------------
# SherpaDiarizer without models (speaker_turns patched) and failure paths
# --------------------------------------------------------------------------------------------


def coarse_transcript() -> Transcript:
    """ASR-like: one segment runs across the speaker change at 8 s."""
    s1 = seg("S001", words(0.0, 4.0) + words(4.0, 8.0, prefix="x") + words(8.0, 12.0, prefix="y"), confidence=0.7)
    s2 = seg("S002", words(12.5, 16.0, prefix="z"), confidence=0.9)
    return Transcript(call_id="c1", segments=[s1, s2], duration=16.0, meta={"asr": "x"})


TURNS = [Turn(0.0, 7.9, "SPK0"), Turn(8.1, 12.1, "SPK1"), Turn(12.4, 16.0, "SPK0")]


def make_sherpa(ctx, monkeypatch, turns=TURNS, **params) -> SherpaDiarizer:
    d = SherpaDiarizer(ctx, **params)
    monkeypatch.setattr(d, "speaker_turns", lambda audio: (list(turns), {"clustering": "stub"}))
    monkeypatch.setattr("callguard.diarization.sherpa.load_audio", lambda path, sr=16000: np.zeros(sr))
    return d


def test_diarize_end_to_end_with_stub_turns_and_llm(ctx, monkeypatch, tmp_path):
    llm = use_llm(ctx, monkeypatch, StubLLM(reads("w0", confidence=0.8)))
    d = make_sherpa(ctx, monkeypatch)
    t = coarse_transcript()

    out = d.diarize(tmp_path / "call.wav", t)

    assert [(s.id, s.speaker, s.role) for s in out.segments] == [
        ("S001", "SPK0", "advisor"), ("S002", "SPK1", "customer"), ("S003", "SPK0", "advisor")]
    meta = out.meta["diarization"]
    assert meta["num_turns"] == 3 and meta["speakers"] == ["SPK0", "SPK1"]
    assert meta["role_method"] == "llm" and meta["role_confidence"] == 0.8 and meta["role_reason"]
    assert meta["seconds"] >= 0 and "error" not in meta and meta["clustering"] == "stub"
    assert meta["speaker_seconds"] == {"SPK0": 11.5, "SPK1": 4.0}
    assert out.meta["asr"] == "x"
    assert Transcript.model_validate_json(out.model_dump_json()) == out  # the pipeline caches it as JSON
    assert len(llm.calls) == 2
    assert [s.id for s in t.segments] == ["S001", "S002"] and "diarization" not in t.meta  # input untouched


def test_diarize_without_resplit_and_roles(ctx, monkeypatch, tmp_path):
    d = make_sherpa(ctx, monkeypatch, resplit=False, roles="none")
    out = d.diarize(tmp_path / "call.wav", coarse_transcript())
    assert [(s.id, s.speaker, s.role) for s in out.segments] == [("S001", "SPK0", "unknown"),
                                                                 ("S002", "SPK0", "unknown")]
    assert out.meta["diarization"]["role_method"] == "none"


def test_missing_model_degrades_with_error_and_keeps_transcript(ctx, tmp_path):
    d = SherpaDiarizer(ctx, segmentation_model="models/diar/nope.onnx")
    t = coarse_transcript()
    out = d.diarize(tmp_path / "missing.wav", t)
    meta = out.meta["diarization"]
    assert "error" in meta and meta["num_turns"] == 0 and meta["role_method"] == "none"
    assert [s.model_dump() for s in out.segments] == [s.model_dump() for s in t.segments]


def test_failure_uses_heuristic_only_for_existing_speakers_without_roles(ctx, tmp_path):
    d = SherpaDiarizer(ctx, segmentation_model="models/diar/nope.onnx")

    out = d.diarize(tmp_path / "missing.wav", dialogue(BANK_CALL))
    meta = out.meta["diarization"]
    assert "error" in meta and meta["role_method"] == "first_speaker_advisor"
    assert [s.role for s in out.segments] == ["advisor", "customer", "advisor", "customer"]

    scripted = dialogue(BANK_CALL)
    for s in scripted.segments:
        s.role = "customer" if s.speaker == "SPK0" else "advisor"
    out = d.diarize(None, scripted)
    assert "no audio" in out.meta["diarization"]["error"]
    assert [s.role for s in out.segments] == [s.role for s in scripted.segments]


def test_no_turns_found_is_reported_as_error(ctx, monkeypatch, tmp_path):
    d = make_sherpa(ctx, monkeypatch, turns=[])
    out = d.diarize(tmp_path / "silence.wav", coarse_transcript())
    assert "no speech turns" in out.meta["diarization"]["error"]
    assert all(s.speaker is None for s in out.segments)


# --------------------------------------------------------------------------------------------
# config / registry
# --------------------------------------------------------------------------------------------


def test_registry_builds_sherpa_from_base_config_lazily(ctx):
    cfg = load_config("local")
    d = registry.create("diarizer", cfg.diarizer, ctx=ctx)
    assert isinstance(d, SherpaDiarizer) and d._sd is None  # models load on first diarize
    assert d.cache_params()["type"] == "sherpa_onnx" and d.cache_params()["num_speakers"] == 2
    assert d.cache_params()["role_llm"] == ctx.llm("default").cache_params()  # roles depend on the model
    assert "role_llm" not in SherpaDiarizer(ctx, roles="first_speaker_advisor").cache_params()
    assert d.num_threads >= 1
    with pytest.raises(ValueError):
        SherpaDiarizer(ctx, roles="guess")
    with pytest.raises(TypeError):
        registry.create("diarizer", {"type": "sherpa_onnx", "num_speaker": 2}, ctx=ctx)


def test_none_diarizer_passes_through_and_tolerates_inherited_params(ctx):
    assert load_config("oracle").diarizer == {"type": "none"}  # a type swap in a profile inherits nothing
    cfg = load_config("local", ["diarizer.type=none"])  # --set applies after the merge: sherpa keys stay
    assert cfg.diarizer["type"] == "none" and "segmentation_model" in cfg.diarizer
    d = registry.create("diarizer", cfg.diarizer, ctx=ctx)
    assert isinstance(d, NoDiarizer) and d.cache_params() == {"type": "none"}
    t = coarse_transcript()
    assert d.diarize(None, t) is t
    with pytest.raises(TypeError, match="num_speaker"):
        registry.create("diarizer", {"type": "none", "num_speaker": 2}, ctx=ctx)
    assert drop_inherited("none", {}) == {}


def test_roles_through_the_fake_llm_plugin(ctx, monkeypatch, tmp_path):
    d = make_sherpa(ctx, monkeypatch)  # ctx.llm("default") is the registry's offline fake
    out = d.diarize(tmp_path / "call.wav", coarse_transcript())
    meta = out.meta["diarization"]
    assert meta["role_method"] in ("llm", "first_speaker_advisor")
    assert {s.role for s in out.segments} == {"advisor", "customer"}


# --------------------------------------------------------------------------------------------
# slow: real models / live LLM
# --------------------------------------------------------------------------------------------


def synthetic_asr(duration: float, seg_s: float = 10.0, word_s: float = 0.4) -> Transcript:
    """ASR-shaped transcript of fixed 10 s segments with a 'word' every 0.4 s: no real ASR needed to
    see how diarization re-splits segments."""
    segs, t = [], 0.0
    while t < duration - word_s:
        end = min(t + seg_s, duration)
        ws = words(t, end, step=word_s)
        if ws:
            segs.append(seg(f"S{len(segs) + 1:03d}", ws, confidence=0.9))
        t = end
    return Transcript(call_id="Stufe1_D02-K1", segments=segs, duration=duration)


@pytest.mark.slow
def test_real_diarization_finds_two_speakers_and_the_turns(ctx):
    pytest.importorskip("sherpa_onnx")
    from callguard.audio import duration
    from callguard.data import parse_turns

    wav = DATA / "Audio" / "Stufe1_D02-K1.wav"
    d = SherpaDiarizer(ctx, roles="first_speaker_advisor")
    if not wav.exists() or not all((ROOT / p).exists() for p in (d.segmentation_model, d.embedding_model)):
        pytest.skip("case audio or diarization models missing")
    ref_turns = parse_turns((DATA / "Transkript" / "Stufe1_D02.txt").read_text())  # evaluation only

    t0 = time.time()
    out = d.diarize(wav, synthetic_asr(duration(wav)))
    secs = time.time() - t0

    meta = out.meta["diarization"]
    speaker_runs = runs([s.speaker for s in out.segments])
    print(f"\n[diarization] {secs:.1f}s for {duration(wav):.0f}s audio; turns={meta['num_turns']} "
          f"runs={len(speaker_runs)} (script turns={len(ref_turns)}) meta={meta}")
    assert "error" not in meta and meta["speakers"] == ["SPK0", "SPK1"]
    assert meta["clustering"] == "turn_embeddings"
    assert abs(meta["num_turns"] - len(ref_turns)) <= 5
    assert abs(len(speaker_runs) - len(ref_turns)) <= 3
    assert out.segments[0].role == "advisor" and {s.role for s in out.segments} == {"advisor", "customer"}
    assert min(meta["speaker_seconds"].values()) > 30  # both voices hold a real share of the call


@pytest.mark.slow
def test_live_llm_picks_the_advisor(tmp_path):
    cfg = AppConfig(name="live", asr={"type": "reference"},
                    llms={"default": {"type": "openai_compat", "base_url": LIVE_URL, "model": LIVE_MODEL,
                                      "json_mode": "json_object_schema", "timeout": 300}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    live_ctx = Context(cfg)
    llm = live_ctx.llm()
    if not llm.ping():
        pytest.skip("local LLM server not reachable")
    t = dialogue([("SPK0", BANK_CALL[1][1]), ("SPK1", BANK_CALL[0][1]),
                  ("SPK0", BANK_CALL[3][1]), ("SPK1", BANK_CALL[2][1])])  # customer speaks first

    t0 = time.time()
    info = assign_roles(t.segments, "llm", llm=lambda: llm)
    print(f"\n[live roles] {time.time() - t0:.1f}s {info}")
    assert info["role_method"] in ("llm", "first_speaker_advisor")
    assert {s.role for s in t.segments} == {"advisor", "customer"}
