"""Transcript views (docs/design/v2_plan.md §1): config parsing + DAG, per-view checks, check_view,
translators (identity, LLM with fallback), fusion across views, provenance, and the guarantee that a
config without views keeps every v1 cache key byte-identical."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import soundfile as sf

from callguard import pipeline as pipeline_mod
from callguard import registry
from callguard.cache import Cache, stable_hash
from callguard.config import AppConfig, Paths, load_config
from callguard.context import Context
from callguard.fusion.weighted import WeightedFusion
from callguard.pipeline import Pipeline
from callguard.plugins import LLM, ASRBackend, Translator
from callguard.translate.llm import LLMTranslator
from callguard.types import CheckResult, Family, FamilyScore, Finding, Keyword, Segment, Transcript
from callguard.views import ViewConfigError, build_order, parse_views

# --------------------------------------------------------------------------------------------
# stub plugins
# --------------------------------------------------------------------------------------------

SEGS = {
    "a": [Segment(id="S001", start=0.5, end=4.0, text="Guten Tag, wie kann ich helfen?"),
          Segment(id="S002", start=5.0, end=11.0, text="Ich will die Aktie vor der Meldung kaufen."),
          Segment(id="S003", start=12.0, end=15.0, text="Das kann ich so nicht ausführen.")],
    "b": [Segment(id="S001", start=0.5, end=8.0, text="Grüezi, wie chan ich helfe? Ich wott d Aktie"),
          Segment(id="S002", start=8.0, end=15.0, text="vor de Meldig chaufe. Das gaht nöd.")],
}
EN = {"vor der Meldung": "before the announcement"}
CALLS: dict[str, int] = {"asr": 0, "translate": 0}


@registry.register("asr", "test_views_fixed")
class FixedASR(ASRBackend):
    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        CALLS["asr"] += 1
        segs = [s.model_copy(deep=True) for s in SEGS[self.params.get("variant", "a")]]
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=20.0, segments=segs,
                          asr_backend=f"test:{self.params.get('variant', 'a')}")


@registry.register("translator", "test_views_dict")
class DictTranslator(Translator):
    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        CALLS["translate"] += 1
        segs = []
        for s in transcript.segments:
            text = s.text
            for de, en in EN.items():
                text = text.replace(de, en)
            segs.append(s.model_copy(update={"text": text, "words": []}))
        return Transcript(call_id=transcript.call_id, segments=segs, asr_backend="dict", lang=target_lang)


@pytest.fixture(autouse=True)
def _reset():
    for k in CALLS:
        CALLS[k] = 0


@pytest.fixture
def wav(tmp_path: Path) -> Path:
    p = tmp_path / "call.wav"
    sf.write(p, np.zeros(16000 * 20, dtype=np.float32), 16000)
    return p


def make_cfg(tmp_path: Path, **kw: Any) -> AppConfig:
    base: dict[str, Any] = dict(
        name="views-test", paths=Paths(cache_dir=str(tmp_path / "cache"), runs_dir=str(tmp_path / "runs")),
        asr={"type": "test_views_fixed"}, diarizer={"type": "none"},
        checks=[{"name": "keywords", "type": "keywords", "weight": 0.35}])
    base.update(kw)
    return AppConfig(**base)


VIEWS = {
    "de": {"lang": "de"},
    "gsw": {"lang": "gsw", "asr": {"variant": "b"}},
    "en_from_de": {"lang": "en", "from": "de", "translator": {"type": "test_views_dict"}},
}

# --------------------------------------------------------------------------------------------
# v1 cache keys: pinned to the values the code before views produced (HEAD 8e00d1e). If one of these
# changes, 60 cached transcripts / diarizations / check results are silently recomputed.
# --------------------------------------------------------------------------------------------

V1_KEYS = [("asr", "dc2f87bf79b9e2da"), ("diarize", "e0d9bd70f40fdfb7"),
           ("check/keywords", "a1d70d40ab401358"), ("check/patterns", "18d0dae4b8e8c83f")]
PIN_ASR = {"type": "faster_whisper", "model": "tiny", "device": "cpu", "compute_type": "int8", "language": "de",
           "beam_size": 1, "vad_filter": True, "word_timestamps": True,
           "initial_prompt": "Telefongespräch einer Schweizer Bank."}
PIN_T = Transcript(call_id="pin", duration=20.0, segments=[
    Segment(id="S001", start=0.5, end=4.0, text="Guten Tag, wie kann ich helfen?"),
    Segment(id="S002", start=5.0, end=11.0, text="Ich möchte die Aktie vor der Meldung kaufen, meine PIN ist 4 2 4 2."),
    Segment(id="S003", start=12.0, end=15.0, text="Das kann ich so nicht ausführen.")], asr_backend="pin")
PIN_FAMS = [Family(id="trade", label="Insiderhandel", policy="p", keywords=[
                Keyword(id="K04", label="vor der Meldung", de=["vor der Meldung"], gsw=["vor de Meldig"])]),
            Family(id="access", label="Zugangsdaten", keywords=[Keyword(id="K10", label="PIN", de=["PIN"], gsw=["PIN"])]),
            Family(id="numbers", label="Zahlen", can_alarm=False)]


class RecordingCache(Cache):
    """Records (namespace, key hash); serves the pinned transcript for ASR without loading Whisper."""

    def __init__(self, root: Path):
        super().__init__(root, enabled=False)
        self.keys: list[tuple[str, str]] = []

    def get_or_compute(self, namespace, key, model, fn, store=None):  # type: ignore[override]
        self.keys.append((namespace, stable_hash(key)))
        if namespace == "asr":
            return PIN_T.model_copy(deep=True), False
        return fn(), False


def pin_pipeline(tmp_path: Path, monkeypatch, **kw: Any) -> tuple[Pipeline, RecordingCache]:
    monkeypatch.setattr(pipeline_mod, "file_hash", lambda p: "a" * 16)
    cfg = make_cfg(tmp_path, asr=PIN_ASR, checks=[{"name": "keywords", "type": "keywords", "weight": 0.35, "fuzzy": 90},
                                                  {"name": "patterns", "type": "patterns", "weight": 0.2}], **kw)
    pipe = Pipeline(cfg)
    rec = RecordingCache(tmp_path / "cache")
    pipe.ctx.cache = rec
    return pipe, rec


def test_v1_cache_keys_are_byte_identical(tmp_path, monkeypatch):
    pipe, rec = pin_pipeline(tmp_path, monkeypatch)
    t = pipe.transcribe(Path("/nonexistent.wav"), "pin")
    t = pipe.diarize(Path("/nonexistent.wav"), t)
    for c in pipe.checks:
        pipe.run_check(c, t, PIN_FAMS)
    assert rec.keys == V1_KEYS


def test_v1_process_uses_the_stage_keys(tmp_path, monkeypatch, wav):
    """process() (now via build_views) asks the cache with exactly the keys of the v1 stage methods."""
    pipe, rec = pin_pipeline(tmp_path, monkeypatch)
    monkeypatch.setattr(pipe.ctx, "families", lambda: PIN_FAMS)
    r = pipe.process(wav, "pin", emit=False)
    assert rec.keys == V1_KEYS
    assert r.views == {} and r.transcript.view == "main" and r.transcript.lang is None
    assert {c.view for c in r.checks.values()} == {"main"}
    assert all(not p.texts for p in r.decision.passages)  # v1 decisions: no per-view texts


def test_same_asr_view_shares_the_v1_transcript_key(tmp_path, monkeypatch):
    """A views config whose view uses the top-level asr hits the transcripts cached by v1 runs."""
    pipe, rec = pin_pipeline(tmp_path, monkeypatch, views={"de": {"lang": "de"}})
    t = pipe.transcribe(Path("/nonexistent.wav"), "pin", view="de")
    pipe.diarize(Path("/nonexistent.wav"), t)
    assert rec.keys[:2] == V1_KEYS[:2] and t.view == "de" and t.lang == "de"


def test_faster_whisper_task_enters_the_key_only_when_not_default(tmp_path):
    from callguard.asr.faster_whisper import FasterWhisperASR

    ctx = Context(make_cfg(tmp_path), use_cache=False)
    plain = FasterWhisperASR(ctx, model="tiny")
    assert "task" not in plain.cache_params() and "task" not in plain.options
    tr = FasterWhisperASR(ctx, model="tiny", task="translate", initial_prompt="Bank")
    assert tr.cache_params()["task"] == "translate" and tr.options["task"] == "translate"
    assert tr.options["initial_prompt"] is None
    with pytest.raises(ValueError):
        FasterWhisperASR(ctx, model="tiny", task="summarise")


def test_keyword_cache_key_ignores_empty_english_forms():
    from callguard.plugins import family_cache_view

    fam = PIN_FAMS[0]
    assert "en" not in family_cache_view(fam)["keywords"][0]
    with_en = fam.model_copy(update={"keywords": [fam.keywords[0].model_copy(update={"en": ["before the news"]})]})
    assert family_cache_view(with_en)["keywords"][0]["en"] == ["before the news"]


# --------------------------------------------------------------------------------------------
# Keyword.forms + English keyword list
# --------------------------------------------------------------------------------------------


def test_keyword_forms_per_language():
    kw = Keyword(id="K", label="x", de=["vor der Meldung"], gsw=["vor de Meldig"], en=["before the announcement"])
    assert kw.forms("de") == ["vor der Meldung", "vor de Meldig"]
    assert kw.forms("gsw") == ["vor de Meldig", "vor der Meldung"]
    assert kw.forms("en") == ["before the announcement"]
    assert kw.forms(None) == kw.phrases


def test_every_case_keyword_has_english_forms():
    from callguard.config import ROOT
    from callguard.families import load_families

    fams = load_families(ROOT / "config/keywords.json", ROOT / "config/criteria.yaml")
    missing = [k.id for f in fams for k in f.keywords if not k.en]
    assert not missing


# --------------------------------------------------------------------------------------------
# config + DAG
# --------------------------------------------------------------------------------------------


def test_no_views_is_a_single_main_view(tmp_path):
    pipe = Pipeline(make_cfg(tmp_path))
    assert list(pipe.view_specs) == ["main"] and pipe.primary_view == "main" and not pipe.multi_view
    assert pipe.needed_views() == ["main"]


def test_view_asr_is_merged_onto_top_level_asr(tmp_path):
    specs = parse_views(make_cfg(tmp_path, asr={"type": "test_views_fixed", "beam_size": 1}, views=VIEWS))
    assert specs["gsw"].asr == {"type": "test_views_fixed", "beam_size": 1, "variant": "b"}
    assert specs["de"].asr == {"type": "test_views_fixed", "beam_size": 1}
    assert specs["en_from_de"].kind == "translate" and specs["en_from_de"].source == "de"


def test_needed_views_follow_checks_extra_views_and_sources(tmp_path):
    checks = [{"name": "kw", "type": "keywords"}, {"name": "kw_en", "type": "keywords", "view": "en_from_de"}]
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks))
    assert pipe.primary_view == "de"
    assert pipe.needed_views() == ["de", "en_from_de"]  # gsw is read by nobody
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks, primary_view="gsw", extra_views=["de"]))
    assert pipe.needed_views() == ["gsw", "de", "en_from_de"]


def test_dag_rejects_cycles_unknown_views_and_bad_specs(tmp_path):
    cyc = {"a": {"lang": "en", "from": "b", "translator": "identity"},
           "b": {"lang": "de", "from": "a", "translator": "identity"}}
    with pytest.raises(ViewConfigError, match="cycle"):
        build_order(parse_views(make_cfg(tmp_path, views=cyc)), ["a"])
    with pytest.raises(ViewConfigError, match="not defined"):
        parse_views(make_cfg(tmp_path, views={"x": {"lang": "en", "from": "nope", "translator": "identity"}}))
    with pytest.raises(ViewConfigError, match="translator"):
        parse_views(make_cfg(tmp_path, views={"de": {}, "x": {"lang": "en", "from": "de"}}))
    with pytest.raises(ViewConfigError, match="unknown keys"):
        parse_views(make_cfg(tmp_path, views={"de": {"lnag": "de"}}))
    with pytest.raises(ViewConfigError, match="not defined"):
        Pipeline(make_cfg(tmp_path, views=VIEWS, checks=[{"name": "k", "type": "keywords", "view": "fr"}]))
    with pytest.raises(ViewConfigError, match="primary_view"):
        Pipeline(make_cfg(tmp_path, views=VIEWS, primary_view="fr"))


def test_check_view_overrides_every_check(tmp_path, wav):
    checks = [{"name": "kw", "type": "keywords"}, {"name": "kw_gsw", "type": "keywords", "view": "gsw"}]
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks, check_view="en_from_de"))
    assert [pipe.view_of(c) for c in pipe.checks] == ["en_from_de", "en_from_de"]
    r = pipe.process(wav, "c1", emit=False)
    assert {c.view for c in r.checks.values()} == {"en_from_de"}
    assert set(r.views) == {"de", "en_from_de"} and r.transcript.view == "de"


# --------------------------------------------------------------------------------------------
# multi-view processing
# --------------------------------------------------------------------------------------------


def test_multi_view_process_runs_each_check_on_its_view(tmp_path, wav):
    checks = [{"name": "kw", "type": "keywords", "weight": 0.35},
              {"name": "kw_gsw", "type": "keywords", "view": "gsw", "weight": 0.35},
              {"name": "kw_en", "type": "keywords", "view": "en_from_de", "weight": 0.35}]
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks))
    stages: list[str] = []
    r = pipe.process(wav, "c1", emit=False, on_stage=stages.append)
    assert stages == ["asr", "diarize", "translate", "checks", "decide", "snippets"]
    assert set(r.views) == {"de", "gsw", "en_from_de"} and CALLS["asr"] == 2
    en = r.views["en_from_de"]
    assert en.lang == "en" and en.view == "en_from_de"
    assert [s.id for s in en.segments] == [s.id for s in r.views["de"].segments]
    assert "before the announcement" in en.segments[1].text
    for name, view in (("kw", "de"), ("kw_gsw", "gsw"), ("kw_en", "en_from_de")):
        assert r.checks[name].view == view
        assert r.checks[name].family_scores["trade"].score > 0.2, name  # each view found K04 in its language
    assert r.checks["kw_en"].findings[0].detail  # English form matched on the English view
    p = next(p for p in r.decision.passages if p.family == "trade")
    assert set(p.texts) == {"de", "gsw", "en_from_de"} and "before the announcement" in p.texts["en_from_de"]
    assert all(sid in {s.id for s in r.transcript.segments} for sid in p.segment_ids)
    prov = r.meta["provenance"]
    assert set(prov["views"]) == {"de", "gsw", "en_from_de"} and prov["checks"]["kw_en"]["view"] == "en_from_de"
    assert prov["views"]["gsw"]["params"]["asr"]["variant"] == "b"
    assert prov["config_hash"] and prov["code_version"] and prov["created_at"]
    # result.json round trip keeps the views
    from callguard.types import CallResult
    again = CallResult.model_validate_json(r.model_dump_json())
    assert set(again.views) == set(r.views) and again.view("gsw").lang == "gsw"


def test_translations_are_cached(tmp_path, wav):
    checks = [{"name": "kw_en", "type": "keywords", "view": "en_from_de"}]
    Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks)).process(wav, "c1", emit=False)
    Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks)).process(wav, "c1", emit=False)
    assert CALLS["translate"] == 1 and CALLS["asr"] == 1


def test_process_transcript_binds_root_view_and_derives_translations(tmp_path):
    checks = [{"name": "kw", "type": "keywords"}, {"name": "kw_en", "type": "keywords", "view": "en_from_de"},
              {"name": "kw_gsw", "type": "keywords", "view": "gsw"}]
    pipe = Pipeline(make_cfg(tmp_path, views=VIEWS, checks=checks))
    t = Transcript(call_id="x", segments=[s.model_copy() for s in SEGS["a"]])
    r = pipe.process_transcript(t)
    assert set(r.views) == {"de", "en_from_de"} and CALLS["asr"] == 0
    assert r.checks["kw_en"].family_scores["trade"].score > 0.2
    assert "not available" in r.checks["kw_gsw"].meta["error"]  # an ASR view needs audio
    assert any("gsw" in w for w in r.meta["warnings"])


def test_failed_translation_leaves_the_view_out(tmp_path, wav):
    views = {**VIEWS, "en_from_de": {"lang": "en", "from": "de",
                                     "translator": {"type": "llm_translate", "llm": "default"}}}
    cfg = make_cfg(tmp_path, views=views, llms={"default": {"type": "test_views_scripted", "broken": True}},
                   checks=[{"name": "kw", "type": "keywords"}, {"name": "kw_en", "type": "keywords", "view": "en_from_de"}])
    r = Pipeline(cfg).process(wav, "c1", emit=False)
    assert "en_from_de" not in r.views and r.checks["kw_en"].meta["error"]
    assert r.checks["kw"].family_scores and any("translation failed" in w for w in r.meta["warnings"])


def test_demo_views_profile_loads_and_validates():
    pipe = Pipeline(load_config("demo-views"), use_cache=False)
    assert pipe.multi_view and pipe.needed_views() == ["main", "en_from_de"]
    for name in ("gpu-views", "oracle-views"):
        cfg = load_config(name)
        specs = parse_views(cfg)
        assert build_order(specs, list(specs))
    gv = parse_views(load_config("gpu-views"))
    assert gv["en_speech"].asr["task"] == "translate" and gv["de_large"].asr["compute_type"] == "float16"


# --------------------------------------------------------------------------------------------
# translators
# --------------------------------------------------------------------------------------------


@registry.register("llm", "test_views_scripted")
class ScriptedLLM(LLM):
    """Translates "X" to "EN(X)". Batch answers drop their second id and invent one; segments whose
    text contains "kaputt" never get a valid answer; ``broken`` = server down."""

    def __init__(self, ctx, broken: bool = False, **kw):
        super().__init__(ctx, broken=broken)
        self.broken = broken
        self.requests: list[list[str]] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        if self.broken:
            raise ConnectionError("server down")
        user = messages[-1]["content"]
        items = json.loads(user[user.index("[", user.index("Segments to translate")):]) if "Segments to translate" in user else []
        self.requests.append([i["id"] for i in items])
        out = [{"id": i["id"], "text": f"EN({i['text']})"} for i in items if "kaputt" not in i["text"]]
        if len(items) > 1:
            out = [o for o in out if o["id"] != items[1]["id"]] + [{"id": "S999", "text": "invented"}]
        return [json.dumps({"translations": out}) if out else "{}"] * n


def _translator(tmp_path: Path, **kw: Any) -> tuple[LLMTranslator, ScriptedLLM]:
    ctx = Context(make_cfg(tmp_path, llms={"default": {"type": "test_views_scripted"}}), use_cache=False)
    tr = LLMTranslator(ctx, **kw)
    tr.plugin_type = "llm_translate"
    return tr, ctx.llm("default")  # type: ignore[return-value]


def _source(n: int, bad: set[int] = frozenset()) -> Transcript:  # type: ignore[assignment]
    segs = [Segment(id=f"S{i:03d}", start=i * 2.0, end=i * 2.0 + 1.5, text=("kaputt " if i in bad else "") + f"Satz {i}",
                    speaker="SPK0", role="advisor" if i % 2 else "customer", confidence=0.9,
                    words=[{"start": i * 2.0, "end": i * 2.0 + 1, "text": "Satz"}])
            for i in range(1, n + 1)]
    return Transcript(call_id="c", segments=segs, lang="de", view="de")


def test_llm_translator_keeps_structure_and_falls_back_per_segment(tmp_path):
    tr, llm = _translator(tmp_path, batch_size=4, context=2, concurrency=2)
    src = _source(9)
    out = tr.translate(src, "en")
    assert [s.id for s in out.segments] == [s.id for s in src.segments]
    for a, b in zip(src.segments, out.segments):
        assert (a.start, a.end, a.speaker, a.role, a.confidence) == (b.start, b.end, b.speaker, b.role, b.confidence)
        assert b.words == [] and b.text == f"EN({a.text})"
    assert out.lang == "en" and out.meta["translation"]["from_lang"] == "de"
    assert out.meta["translation"]["retried_segments"] == ["S002", "S006"]  # dropped by the batch answers
    assert "degraded" not in out.meta and "S999" not in {s.id for s in out.segments}
    assert sorted(len(r) for r in llm.requests if len(r) > 1) == [4, 4]  # 9 segments / batch 4: 4+4+1
    assert "concurrency" not in tr.cache_params() and tr.cache_params()["llm"]["type"] == "test_views_scripted"


def test_llm_translator_context_is_not_translated(tmp_path):
    tr, _ = _translator(tmp_path, batch_size=2, context=2)
    msgs = tr.messages(_source(4).segments[2:4], _source(4).segments[:2], "gsw", "en")
    user = msgs[1]["content"]
    assert "Context (do not translate)" in user and "[S001 advisor] Satz 1" in user
    assert json.loads(user[user.index("[", user.index("Segments to translate")):])[0]["id"] == "S003"
    assert "Swiss German" in msgs[0]["content"] and "verbatim" in msgs[0]["content"]


def test_llm_translator_degrades_then_fails(tmp_path):
    tr, _ = _translator(tmp_path, batch_size=3)
    out = tr.translate(_source(3, bad={3}), "en")
    assert out.meta["degraded"] and out.meta["translation"]["untranslated_segments"] == ["S003"]
    assert out.segments[2].text == "kaputt Satz 3"  # source text kept
    with pytest.raises(RuntimeError, match="no segment"):
        tr.translate(_source(2, bad={1, 2}), "en")


def test_identity_translator(tmp_path):
    from callguard.translate.identity import IdentityTranslator

    out = IdentityTranslator(Context(make_cfg(tmp_path), use_cache=False)).translate(_source(2), "en")
    assert [s.text for s in out.segments] == ["Satz 1", "Satz 2"] and out.lang == "en"
    assert all(not s.words for s in out.segments)


# --------------------------------------------------------------------------------------------
# fusion across views
# --------------------------------------------------------------------------------------------


def test_fusion_reanchors_other_view_findings_by_time(tmp_path):
    primary = Transcript(call_id="c", view="de", lang="de", segments=[
        Segment(id="A1", start=0, end=5, text="eins"), Segment(id="A2", start=5, end=10, text="zwei"),
        Segment(id="A3", start=20, end=25, text="drei")])
    other = Transcript(call_id="c", view="gsw", lang="gsw", segments=[
        Segment(id="A1", start=0, end=3, text="ois"), Segment(id="B2", start=3, end=10, text="zwöi")])
    fam = Family(id="trade", label="Insiderhandel")
    res = CheckResult(check="llm_gsw", type="llm_judge", view="gsw",
                      family_scores={"trade": FamilyScore(score=0.9, confidence=0.9)},
                      findings=[Finding(check="llm_gsw", family="trade", score=0.9, segment_ids=["B2"])])
    d = WeightedFusion(None).decide(primary, {"llm_gsw": res}, [fam], {"weights": {"llm_gsw": 1.0}},
                                    views={"de": primary, "gsw": other})
    p = d.passages[0]
    assert (p.start, p.end) == (3, 10) and p.segment_ids == ["A1", "A2"] and p.text == "eins zwei"
    assert p.texts == {"de": "eins zwei", "gsw": "zwöi"}
    # without views (v1 call): the same ids would be looked up in the primary transcript
    d1 = WeightedFusion(None).decide(primary, {"llm_gsw": res}, [fam], {"weights": {"llm_gsw": 1.0}})
    assert d1.passages == [] or not d1.passages[0].texts
