"""A4 transcript correction (``llm_correct``, multi-source views): time alignment of alternative
hypotheses, the LLM fallback + support guard, multi-source view DAG / pipeline, and cache keys
(single-source translation keys unchanged, multi-source keys follow every source)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf

from callguard import registry
from callguard.cache import Cache, stable_hash
from callguard.config import AppConfig, Paths, load_config
from callguard.context import Context
from callguard.pipeline import Pipeline
from callguard.plugins import LLM, ASRBackend
from callguard.translate.correct import LLMCorrector, align, support, timed_units
from callguard.types import Segment, Transcript, Word
from callguard.views import ViewConfigError, build_order, parse_views, root_of

# --------------------------------------------------------------------------------------------
# stubs
# --------------------------------------------------------------------------------------------

HYPS = {
    "a": [Segment(id="S001", start=0.0, end=4.0, text="Guten Tag, wie kann ich helfen?"),
          Segment(id="S002", start=5.0, end=10.0, text="Ich will die Aktie vor der Melodie kaufen."),
          Segment(id="S003", start=11.0, end=14.0, text="Kreditkarte Rechnung Kreditkarte Rechnung")],
    "b": [Segment(id="S001", start=0.0, end=4.0, text="Guten Tag, wie kann ich helfen?"),
          Segment(id="S002", start=5.2, end=10.0, text="Ich will die Aktie vor der Meldung kaufen.")],
}
CALLS: dict[str, int] = {"asr": 0}


@registry.register("asr", "test_correct_fixed")
class FixedASR(ASRBackend):
    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        CALLS["asr"] += 1
        segs = [s.model_copy(deep=True) for s in HYPS[self.params.get("variant", "a")]]
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=15.0, segments=segs,
                          asr_backend=f"test:{self.params.get('variant', 'a')}")


@registry.register("llm", "test_correct_scripted")
class ScriptedLLM(LLM):
    """Answers with hypothesis B where it has text, else A. In batches of > 1 the second id is dropped
    and an id is invented; "erfinde" in A -> an answer no hypothesis supports; ``broken`` = server down."""

    instances: list["ScriptedLLM"] = []

    def __init__(self, ctx, broken: bool = False, **kw):
        super().__init__(ctx, broken=broken)
        self.broken = broken
        self.requests: list[list[str]] = []
        ScriptedLLM.instances.append(self)

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        if self.broken:
            raise ConnectionError("server down")
        user = messages[-1]["content"]
        items = json.loads(user[user.index("[", user.index("Segments to correct")):])
        self.requests.append([i["id"] for i in items])
        out = []
        for i in items:
            if "erfinde" in i["A"]:
                out.append({"id": i["id"], "text": "Der Kunde bestätigt Insiderwissen über Fusion"})
            elif "Kreditkarte Rechnung" in i["A"]:
                out.append({"id": i["id"], "text": ""})
            else:
                out.append({"id": i["id"], "text": i.get("B") or i["A"]})
        if len(items) > 1:
            out = [o for o in out if o["id"] != items[1]["id"]] + [{"id": "S999", "text": "invented"}]
        return [json.dumps({"corrections": out})] * n


@pytest.fixture(autouse=True)
def _reset():
    CALLS["asr"] = 0
    ScriptedLLM.instances.clear()


@pytest.fixture
def wav(tmp_path: Path) -> Path:
    p = tmp_path / "call.wav"
    sf.write(p, np.zeros(16000 * 15, dtype=np.float32), 16000)
    return p


def make_cfg(tmp_path: Path, **kw: Any) -> AppConfig:
    base: dict[str, Any] = dict(
        name="correct-test", paths=Paths(cache_dir=str(tmp_path / "cache"), runs_dir=str(tmp_path / "runs")),
        asr={"type": "test_correct_fixed"}, diarizer={"type": "none"},
        llms={"default": {"type": "test_correct_scripted"}},
        checks=[{"name": "keywords", "type": "keywords", "weight": 0.35}])
    base.update(kw)
    return AppConfig(**base)


VIEWS = {
    "de": {"lang": "de"},
    "alt": {"lang": "de", "asr": {"variant": "b"}},
    "fused": {"lang": "de", "from": ["de", "alt"], "translator": {"type": "llm_correct", "llm": "default"}},
    "en": {"lang": "en", "from": "de", "translator": {"type": "identity"}},
}


def corrector(tmp_path: Path, **kw: Any) -> tuple[LLMCorrector, ScriptedLLM]:
    ctx = Context(make_cfg(tmp_path), use_cache=False)
    c = LLMCorrector(ctx, **kw)
    c.plugin_type = "llm_correct"
    return c, ctx.llm("default")  # type: ignore[return-value]


def tr(segs: list[Segment], view: str = "x") -> Transcript:
    return Transcript(call_id="c", segments=segs, view=view, lang="de")


# --------------------------------------------------------------------------------------------
# alignment
# --------------------------------------------------------------------------------------------


def test_alignment_uses_word_midpoints_and_splits_segments_without_words():
    primary = [Segment(id="P1", start=0, end=5, text="x"), Segment(id="P2", start=5, end=10, text="y"),
               Segment(id="P3", start=20, end=22, text="z")]
    words = [Word(start=3.0, end=4.0, text=" eins"), Word(start=4.5, end=5.9, text=" zwei"),
             Word(start=6.0, end=7.0, text=" drei")]
    alt = tr([Segment(id="A1", start=3, end=7, text="eins zwei drei", words=words),
              Segment(id="A2", start=0, end=10, text="a b c d"),        # no words: 2.5 s per token
              Segment(id="A3", start=10.5, end=11.0, text="nah"),       # 0.75 s after P2: nearest
              Segment(id="A4", start=14.0, end=15.0, text="weit")])     # 4.5 s from anything: dropped
    texts, dropped = align(primary, alt, max_gap=1.5)
    assert texts == {"P1": "a eins b", "P2": "zwei c drei d nah", "P3": ""}
    assert dropped == 1
    assert len(timed_units(alt)) == 9


def test_words_that_do_not_match_the_segment_text_are_not_trusted():
    seg = Segment(id="A", start=0, end=4, text="ganz anderer Text",
                  words=[Word(start=0, end=1, text="alt")])
    assert [u[2] for u in timed_units(tr([seg]))] == ["ganz", "anderer", "Text"]


def test_support_counts_content_words_found_in_some_hypothesis():
    hyps = ["vor der Melodie kaufen", "vor der Meldung chaufe"]
    assert support("vor der Meldung kaufen", hyps) == 1.0
    assert support("Insiderwissen über Fusion bestätigt", hyps) < 0.5
    assert support("", hyps) == 1.0


# --------------------------------------------------------------------------------------------
# the corrector
# --------------------------------------------------------------------------------------------


def _pair(n: int, bad: set[int] = frozenset()) -> tuple[Transcript, Transcript]:  # type: ignore[assignment]
    a = [Segment(id=f"S{i:03d}", start=i * 3.0, end=i * 3.0 + 2.5, speaker="SPK0",
                 role="advisor" if i % 2 else "customer", confidence=0.8,
                 text=("erfinde " if i in bad else "") + f"Satz nummer {i} falsch")
         for i in range(1, n + 1)]
    b = [Segment(id=f"B{i}", start=i * 3.0 + 0.2, end=i * 3.0 + 2.4, text=f"Satz nummer {i} richtig")
         for i in range(1, n + 1)]
    return tr(a, "de"), tr(b, "alt")


def test_corrector_keeps_structure_retries_dropped_ids_and_ignores_invented(tmp_path):
    c, llm = corrector(tmp_path, batch_size=4, context=1, concurrency=2)
    a, b = _pair(9)
    out = c.translate_multi(a, [b], "de")
    assert [s.id for s in out.segments] == [s.id for s in a.segments]
    for x, y in zip(a.segments, out.segments):
        assert (x.start, x.end, x.speaker, x.role, x.confidence) == (y.start, y.end, y.speaker, y.role, y.confidence)
    assert [s.text for s in out.segments] == [f"Satz nummer {i} richtig" for i in range(1, 10)]
    m = out.meta["translation"]
    assert m["retried_segments"] == ["S002", "S006"] and m["changed"] == 9 and m["alternatives"] == ["alt"]
    assert "degraded" not in out.meta and out.lang == "de"
    assert sorted(len(r) for r in llm.requests if len(r) > 1) == [4, 4]


def test_agreeing_segments_are_not_sent_and_keep_their_words(tmp_path):
    c, llm = corrector(tmp_path)
    w = [Word(start=0, end=1, text="Guten"), Word(start=1, end=2, text="Tag.")]
    a = tr([Segment(id="S1", start=0, end=2, text="Guten Tag.", words=w),
            Segment(id="S2", start=3, end=6, text="vor der Melodie")], "de")
    b = tr([Segment(id="X", start=0, end=2, text="guten tag"), Segment(id="Y", start=3, end=6, text="vor der Meldung")])
    out = c.translate_multi(a, [b], "de")
    assert llm.requests == [["S2"]] and out.meta["translation"]["agreeing"] == 1
    assert out.segments[0].words == w and out.segments[1].words == [] and out.segments[1].text == "vor der Meldung"


def test_single_source_passes_through_without_llm(tmp_path):
    c, llm = corrector(tmp_path)
    a, _ = _pair(2)
    out = c.translate(a, "de")
    assert [s.text for s in out.segments] == [s.text for s in a.segments] and llm.requests == []
    c2, llm2 = corrector(tmp_path, correct_alone=True)
    c2.translate(a, "de")
    assert llm2.requests  # single-hypothesis clean-up asks


def test_support_guard_keeps_the_primary_text(tmp_path):
    c, _ = corrector(tmp_path, batch_size=1)
    a, b = _pair(2, bad={2})
    out = c.translate_multi(a, [b], "de")
    assert out.segments[1].text == "erfinde Satz nummer 2 falsch"
    assert out.meta["translation"]["unsupported_segments"] == ["S002"] and "degraded" not in out.meta
    c0, _ = corrector(tmp_path, batch_size=1, min_support=0)
    assert "Insiderwissen" in c0.translate_multi(a, [b], "de").segments[1].text


def test_empty_answer_only_when_a_hypothesis_is_empty(tmp_path):
    c, _ = corrector(tmp_path, batch_size=1)
    a = tr([Segment(id="S1", start=0, end=3, text="Kreditkarte Rechnung Kreditkarte Rechnung")], "de")
    loop_alone = c.translate_multi(a, [tr([Segment(id="B", start=10, end=11, text="Hallo")])], "de")
    assert loop_alone.segments[0].text == ""  # B heard nothing there: the loop goes
    a2 = tr([*a.segments, Segment(id="S2", start=5, end=7, text="vor der Melodie")], "de")
    b2 = tr([Segment(id="B", start=0, end=3, text="Kreditkarte Rechnung"),
             Segment(id="C", start=5, end=7, text="vor der Meldung")])
    both = c.translate_multi(a2, [b2], "de")
    assert both.segments[0].text.startswith("Kreditkarte")  # empty answer refused, A kept
    assert both.meta["translation"]["unsupported_segments"] == ["S1"] and "degraded" not in both.meta
    assert both.segments[1].text == "vor der Meldung"


def test_corrector_raises_when_the_llm_is_down(tmp_path):
    ctx = Context(make_cfg(tmp_path, llms={"default": {"type": "test_correct_scripted", "broken": True}}),
                  use_cache=False)
    c = LLMCorrector(ctx)
    a, b = _pair(3)
    with pytest.raises(RuntimeError, match="no segment"):
        c.translate_multi(a, [b], "de")


def test_cache_params_name_the_model_not_the_speed_knobs(tmp_path):
    c, _ = corrector(tmp_path, concurrency=4)
    p = c.cache_params()
    assert "concurrency" not in p and p["llm"]["type"] == "test_correct_scripted"
    assert p["prompt_version"] and p["min_support"] == 0.6


# --------------------------------------------------------------------------------------------
# multi-source views
# --------------------------------------------------------------------------------------------


def test_multi_source_from_parses_and_orders_sources(tmp_path):
    specs = parse_views(make_cfg(tmp_path, views=VIEWS))
    assert specs["fused"].source == "de" and specs["fused"].sources == ("de", "alt")
    assert specs["fused"].alternatives == ("alt",) and specs["en"].sources == ("de",)
    assert specs["en"].alternatives == ()
    assert build_order(specs, ["fused"]) == ["de", "alt", "fused"]
    assert root_of(specs, "fused") == "de"
    one = parse_views(make_cfg(tmp_path, views={"de": {}, "x": {"lang": "en", "from": ["de"], "translator": "identity"}}))
    assert one["x"].source == "de" and one["x"].alternatives == ()


def test_multi_source_config_errors(tmp_path):
    bad = {**VIEWS, "fused": {**VIEWS["fused"], "from": ["de", "nope"]}}
    with pytest.raises(ViewConfigError, match="not defined"):
        parse_views(make_cfg(tmp_path, views=bad))
    with pytest.raises(ViewConfigError, match="twice"):
        parse_views(make_cfg(tmp_path, views={**VIEWS, "fused": {**VIEWS["fused"], "from": ["de", "de"]}}))
    with pytest.raises(ViewConfigError, match="non-empty list"):
        parse_views(make_cfg(tmp_path, views={**VIEWS, "fused": {**VIEWS["fused"], "from": []}}))
    cyc = {"de": {}, "a": {"lang": "de", "from": ["de", "b"], "translator": "llm_correct"},
           "b": {"lang": "de", "from": ["a"], "translator": "identity"}}
    with pytest.raises(ViewConfigError, match="cycle"):
        build_order(parse_views(make_cfg(tmp_path, views=cyc)), ["a"])
    one_source_translator = {**VIEWS, "fused": {**VIEWS["fused"], "translator": "identity"}}
    with pytest.raises(ViewConfigError, match="takes one source"):
        Pipeline(make_cfg(tmp_path, views=one_source_translator, extra_views=["fused"]))


def test_pipeline_builds_and_caches_the_fused_view(tmp_path, wav):
    checks = [{"name": "kw", "type": "keywords", "view": "fused"}]
    r = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks)).process(wav, "c1", emit=False)
    fused, de = r.views["fused"], r.views["de"]
    assert set(r.views) == {"de", "alt", "fused"} and fused.view == "fused" and fused.lang == "de"
    assert [s.id for s in fused.segments] == [s.id for s in de.segments]
    assert "vor der Meldung" in fused.segments[1].text and fused.segments[2].text == ""
    assert r.checks["kw"].view == "fused"
    assert r.meta["provenance"]["views"]["fused"]["params"]["from"] == ["de", "alt"]
    asked = {sid for llm in ScriptedLLM.instances for q in llm.requests for sid in q}
    assert asked == {"S002", "S003"}  # S001: both recognisers agree, not sent
    ScriptedLLM.instances.clear()
    Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks)).process(wav, "c1", emit=False)
    assert not any(llm.requests for llm in ScriptedLLM.instances) and CALLS["asr"] == 2


def test_missing_alternative_still_builds_from_the_primary(tmp_path):
    checks = [{"name": "kw", "type": "keywords", "view": "fused"}]
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks))
    r = pipe.process_transcript(Transcript(call_id="x", segments=[s.model_copy() for s in HYPS["a"]]))
    assert "fused" in r.views and any("alt missing" in w for w in r.meta["warnings"])
    assert r.views["fused"].meta["translation"]["alternatives"] == []


class KeyCache(Cache):
    def __init__(self, root: Path):
        super().__init__(root, enabled=False)
        self.keys: list[tuple[str, dict]] = []

    def get_or_compute(self, namespace, key, model, fn, store=None):  # type: ignore[override]
        self.keys.append((namespace, key))
        return fn(), False


def test_single_source_translation_key_is_unchanged_and_multi_source_keys_follow_all_sources(tmp_path):
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, extra_views=["fused", "en"]))
    pipe.ctx.cache = KeyCache(tmp_path / "c")
    a = Transcript(call_id="c", segments=[s.model_copy() for s in HYPS["a"]], view="de", lang="de")
    b = Transcript(call_id="c", segments=[s.model_copy() for s in HYPS["b"]], view="alt", lang="de")
    pipe.translate(a, "en")
    pipe.translate(a, "fused", [b])
    (ns1, k1), (ns2, k2) = pipe.ctx.cache.keys
    assert ns1 == ns2 == "translate"
    assert k1 == {"source": stable_hash(a.segments), "source_lang": "de",
                  "translator": pipe.translator_for("en").cache_params(), "target": "en"}  # v2 formula
    assert k2["alternatives"] == [{"segments": stable_hash(b.segments), "lang": "de"}]
    assert {k: v for k, v in k2.items() if k != "alternatives"}["source"] == k1["source"]
    b2 = b.model_copy(deep=True)
    b2.segments[1].text = "anders"
    pipe.translate(a, "fused", [b2])
    assert pipe.ctx.cache.keys[-1][1] != k2  # an alternative's text changes the key


def test_gpu_views_de_fused_profile():
    specs = parse_views(load_config("gpu-views"))
    f = specs["de_fused"]
    assert f.sources == ("de", "de_large", "de_vanilla") and f.translator["type"] == "llm_correct"
    assert specs["de_vanilla"].asr["model"] == "models/asr/vanilla-turbo-ct2"
    assert specs["de_vanilla"].asr["compute_type"] == "float16"
    assert build_order(specs, ["de_fused"]) == ["de", "de_large", "de_vanilla", "de_fused"]
