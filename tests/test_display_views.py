"""Display-only views (config ``display_views``) and the automatic Swiss German transcript in the demo player.

* config: specs parsed and validated; configs without display views keep their hash; dual-facts has ``gsw``;
* pipeline: the view is computed after the decision, stored in ``CallResult.display_views`` (not ``views``), cached,
  and NEVER given to a check or to fusion; a failing translator only drops the view; ``in_pipeline: false`` leaves
  it to ``callguard display-views``, which adds it to a stored result.json and changes nothing else;
* ``ctc_dialect``: greedy CTC decoding, cosmetics, segment cutting (end pad capped at the next start), audio in the
  cache key, missing recording -> no view;
* demo: the switch shows the generated view synchronised by segment, labelled honestly; disabled without it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, write_fixture_env

from callguard import audio as audio_mod
from callguard import registry
from callguard.commands.display_views import add_to_file
from callguard.config import hash_dump, load_config
from callguard.demo.transcript import NO_DIALECT_DE, VIEW_CH, VIEW_DE, dialect_view, player_html
from callguard.pipeline import Pipeline, config_hash
from callguard.plugins import ASRBackend, Translator
from callguard.translate import translated_copy
from callguard.translate.ctc_dialect import CTCDialect, ctc_greedy, tidy
from callguard.types import CallResult, Passage, Segment, Transcript
from callguard.ui import backend as be
from callguard.views import ViewConfigError, parse_display_views

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "src" / "callguard" / "demo" / "app.py"
MARK = "DIALEKTMARKER"

SEGMENTS = [
    Segment(id="S001", start=0.4, end=6.0, role="advisor", text="Grüezi Frau Aebi, hier ist Claudia Frei."),
    Segment(id="S002", start=6.5, end=11.0, role="customer", text="Meine Schwester arbeitet in der Finanzabteilung."),
    Segment(id="S003", start=11.2, end=19.0, role="customer", text="Ich möchte die Aktie vor der Meldung kaufen."),
    Segment(id="S004", start=19.5, end=24.0, role="advisor", text="Den Auftrag nehme ich so nicht entgegen."),
]


def _wav(path: Path, seconds: float = 26.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    t = np.arange(int(seconds * audio_mod.SR)) / audio_mod.SR
    sf.write(str(path), (0.05 * np.sin(2 * np.pi * 200 * t)).astype(np.float32), audio_mod.SR, subtype="PCM_16")
    return path


@registry.register("asr", "test_display_asr")
class _FixedASR(ASRBackend):
    def transcribe(self, audio_path: Path, call_id: str) -> Transcript:
        return Transcript(call_id=call_id, audio_path=str(audio_path), duration=25.0,
                          segments=[s.model_copy() for s in SEGMENTS], asr_backend="test")


CALLS: list[str] = []


@registry.register("translator", "test_gsw_marker")
class _MarkerTranslator(Translator):
    def __init__(self, ctx, fail: bool = False):
        super().__init__(ctx, fail=fail)
        self.fail = fail

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        CALLS.append(transcript.call_id)
        if self.fail:
            raise ConnectionError("no model here")
        return translated_copy(transcript, {s.id: f"{MARK} {s.text}" for s in transcript.segments}, target_lang,
                               "test_gsw_marker")


def _cfg(tmp_path: Path, *extra: str):
    return load_config("demo-offline", [f"paths.runs_dir={tmp_path}/runs", f"paths.cache_dir={tmp_path}/cache",
                                        f"paths.data_dir={tmp_path}/data", "asr.type=test_display_asr",
                                        "diarizer.type=none",
                                        "display_views={gsw: {lang: gsw, translator: {type: test_gsw_marker}}}",
                                        *extra])


# --------------------------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------------------------


def test_display_view_specs_are_validated(tmp_path: Path):
    cfg = _cfg(tmp_path)
    specs = parse_display_views(cfg, ["main"])
    assert specs["gsw"].lang == "gsw" and specs["gsw"].source is None and specs["gsw"].in_pipeline
    assert specs["gsw"].as_view("main").source == "main"
    for bad, msg in [("{gsw: {lang: gsw}}", "translator"), ("{gsw: {translator: identity}}", "lang"),
                     ("{gsw: {lang: gsw, translator: identity, colour: red}}", "unknown keys"),
                     ("{main: {lang: gsw, translator: identity}}", "already a view"),
                     ("{gsw: {lang: gsw, from: nope, translator: identity}}", "from")]:
        with pytest.raises(ViewConfigError, match=msg):
            parse_display_views(load_config("demo-offline", [f"display_views={bad}"]), ["main"])


def test_configs_without_display_views_keep_their_hash():
    cfg = load_config("demo-offline")
    assert "display_views" not in hash_dump(cfg)
    assert "display_views" in hash_dump(load_config("demo-offline", ["display_views={gsw: {lang: gsw, translator: identity}}"]))
    assert config_hash(cfg) == config_hash(load_config("demo-offline"))


def test_dual_facts_profile_has_the_display_only_gsw_view():
    for profile in ("dual-facts", "dual-facts-test50"):
        cfg = load_config(profile)
        g = cfg.display_views["gsw"]
        assert g["lang"] == "gsw" and g["translator"]["type"] == "ctc_dialect" and g["in_pipeline"] is False
        assert "gsw" not in cfg.views and "gsw" not in cfg.extra_views and cfg.check_view is None
        assert all(c.get("view") in (None, "main") for c in cfg.checks), "no check may read the display view"


# --------------------------------------------------------------------------------------------
# pipeline
# --------------------------------------------------------------------------------------------


def test_view_is_stored_after_the_decision_and_never_reaches_checks_or_fusion(tmp_path: Path,
                                                                                monkeypatch: pytest.MonkeyPatch):
    pipe = Pipeline(_cfg(tmp_path))
    seen: list[str] = []
    real_run_check, real_decide = Pipeline.run_check, pipe.fusion.decide

    def spy_run_check(self, check, transcript, families):
        seen.append(transcript.model_dump_json())
        return real_run_check(self, check, transcript, families)

    def spy_decide(transcript, results, families, overrides=None, views=None):
        seen.append(transcript.model_dump_json())
        seen.extend(v.model_dump_json() for v in (views or {}).values())
        return real_decide(transcript, results, families, overrides, views=views) if views else \
            real_decide(transcript, results, families, overrides)

    monkeypatch.setattr(Pipeline, "run_check", spy_run_check)
    monkeypatch.setattr(pipe.fusion, "decide", spy_decide)
    r = pipe.process(_wav(tmp_path / "data" / "Audio" / "X-K1.wav"), "X-K1", emit=False)
    g = r.display_views["gsw"]
    assert [(s.id, s.start, s.end, s.role) for s in g.segments] == [(s.id, s.start, s.end, s.role) for s in SEGMENTS]
    assert all(s.text.startswith(MARK) for s in g.segments) and g.lang == "gsw"
    assert "gsw" not in r.views and seen and not any(MARK in x for x in seen)
    stored = json.loads(r.model_dump_json())
    assert MARK not in json.dumps({k: v for k, v in stored.items() if k != "display_views"})
    assert CallResult.model_validate(stored).display_views["gsw"].segments[0].text.startswith(MARK)


def test_failing_translator_only_drops_the_view(tmp_path: Path):
    cfg = _cfg(tmp_path, "display_views.gsw.translator.fail=true")
    r = Pipeline(cfg).process(_wav(tmp_path / "a.wav"), "A-K1", emit=False)
    assert r.display_views == {} and r.decision.label in ("alarm", "review", "no_alert")
    assert any("display view gsw" in w for w in r.meta.get("warnings", []))


def test_staged_view_is_added_to_a_stored_result_and_nothing_else_changes(tmp_path: Path):
    wav = _wav(tmp_path / "data" / "Audio" / "B-K1.wav")
    staged = Pipeline(_cfg(tmp_path, "display_views.gsw.in_pipeline=false"))
    r = staged.process(wav, "B-K1", emit=False)
    assert r.display_views == {}
    path = tmp_path / "runs" / "B-K1" / "result.json"
    path.parent.mkdir(parents=True)
    path.write_text(r.model_dump_json(indent=1))
    before = json.loads(path.read_text())
    CALLS.clear()
    added, _ = add_to_file(staged, path)
    after = json.loads(path.read_text())
    assert added == ["gsw"] and CALLS == ["B-K1"]
    assert {k: v for k, v in after.items() if k != "display_views"} == \
        {k: v for k, v in before.items() if k != "display_views"}
    assert after["display_views"]["gsw"]["segments"][0]["text"].startswith(MARK)
    assert after["display_views"]["gsw"]["audio_path"] == before["audio_path"]
    assert add_to_file(staged, path)[0] == []  # already there: nothing to do
    path.write_text(json.dumps(before))
    assert add_to_file(staged, path, force=True)[0] == ["gsw"] and CALLS == ["B-K1"]  # translation from the cache


# --------------------------------------------------------------------------------------------
# ctc_dialect
# --------------------------------------------------------------------------------------------


def test_ctc_greedy_and_cosmetics():
    vocab = {0: "o", 1: "j", 2: "|", 3: "a", 4: "[PAD]", 5: "[UNK]"}
    assert ctc_greedy(np.array([1, 1, 4, 0, 0, 2, 2, 3, 4, 3, 5]), vocab, blank=4) == "jo aa"
    assert tidy("jo guete tag", "Ja, guten Tag?") == "Jo guete tag?" and tidy("", "x.") == ""
    assert tidy("so", "ohne Satzzeichen") == "So"


def test_ctc_dialect_cuts_each_segment_with_capped_end_pad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    wav = _wav(tmp_path / "c.wav")
    pipe = Pipeline(_cfg(tmp_path, "display_views.gsw.translator={type: ctc_dialect, pad_end: 0.6}"))
    tr = pipe.translator_for("gsw")
    assert isinstance(tr, CTCDialect) and tr.reads_audio
    lengths: list[float] = []
    monkeypatch.setattr(CTCDialect, "recognize", lambda self, x: lengths.append(len(x) / 16000) or "grüezi mitenand")
    src = Transcript(call_id="C-K1", audio_path=str(wav), duration=25.0, segments=[s.model_copy() for s in SEGMENTS])
    out = pipe.translate(src, "gsw")
    # S001 ends 6.0, next starts 6.5 -> +0.5 (cap); S002 11.0 -> 11.2 (cap); S003 19.0 -> 19.5 (cap); S004 +0.6
    assert lengths == pytest.approx([6.1, 4.7, 8.3, 5.1], abs=0.01)
    assert [s.text for s in out.segments] == ["Grüezi mitenand."] * 4 and out.lang == "gsw"
    assert out.meta["translation"]["backend"].startswith("ctc_dialect")
    # the recording is part of the cache key: other audio, same segments -> computed again
    other = _wav(tmp_path / "d.wav", seconds=27.0)
    pipe.translate(src.model_copy(update={"audio_path": str(other)}), "gsw")
    assert len(lengths) == 8
    pipe.translate(src, "gsw")
    assert len(lengths) == 8  # cached


def test_ctc_dialect_without_recording_gives_no_view(tmp_path: Path):
    pipe = Pipeline(_cfg(tmp_path, "display_views.gsw.translator={type: ctc_dialect}"))
    res = CallResult(call_id="Z", audio_path=None, decision={"label": "no_alert", "score": 0.0, "uncertainty": 0.0, "threshold": 0.5},
                     transcript=Transcript(call_id="Z", segments=[s.model_copy() for s in SEGMENTS]))
    assert pipe.add_display_views(res) == [] and res.display_views == {}


# --------------------------------------------------------------------------------------------
# demo player
# --------------------------------------------------------------------------------------------


def _de() -> Transcript:
    return Transcript(call_id="Stufe1_D02-K1", duration=25.0, segments=[s.model_copy() for s in SEGMENTS])


def _gsw() -> Transcript:
    texts = {"S001": "Grüezi <b>Frau</b> Aebi", "S002": "Mini Schwöschter schaffet", "S003": "",
             "S004": "De Uftrag nimm ich nöd."}
    t = translated_copy(_de(), texts, "gsw", "ctc_dialect:wav2vec2-gsw-swissdial-onnx")
    return t


def test_switch_renders_the_generated_view_in_sync_with_passages():
    passages = [Passage(family="trade", family_label="Insiderhandel", start=11.2, end=19.0, segment_ids=["S003"],
                        score=0.9)]
    doc = player_html(_de(), passages, audio_src="data:audio/mpeg;base64,AAAA", colors={"trade": "#d64a2a"},
                      labels={"trade": "Insiderhandel"}, start_at=11.1, dialect=_gsw())
    assert VIEW_DE in doc and VIEW_CH == "Schweizerdeutsch (automatisch)" and VIEW_CH in doc
    assert re.findall(r'id="ch-(S\d+)"', doc) == ["S001", "S002", "S003", "S004"]
    assert re.findall(r'id="seg-(S\d+)"', doc) == ["S001", "S002", "S003", "S004"]
    # same segments, same times, same current-segment rule, same passage marks
    assert re.search(r'class="[^"]*is-current[^"]*" id="seg-S003"', doc)
    assert re.search(r'class="[^"]*is-current[^"]*" id="ch-S003"', doc)
    assert re.search(r'id="ch-S003" data-start="11.20" data-end="19.00"[^>]*--fam:#d64a2a', doc)
    assert re.search(r'id="ch-S003".*?Passage 1 · Insiderhandel', doc, re.S) and "nicht erkannt" in doc
    # honest label, escaped text, ASR pane first
    assert "Automatisch erzeugt (Dialekt-Spracherkennung aus der Aufnahme" in doc
    assert "nicht wortgenau" in doc and "Wird von der KI nicht ausgewertet" in doc
    assert "&lt;b&gt;Frau&lt;/b&gt;" in doc and "<b>Frau</b>" not in doc
    assert re.search(r'class="cg-transcript" data-view="ch" hidden', doc) and 'id="cg-orignote" hidden' in doc
    cfg = json.loads(re.search(r'data-config="([^"]*)"', doc).group(1).replace("&quot;", '"'))
    assert cfg["view"] == "de" and cfg["hasDialect"] is True
    doc = player_html(_de(), passages, audio_src=None, dialect=_gsw(), view="ch")  # deep link ?ansicht=ch
    assert re.search(r'id="cg-transcript" data-view="de" hidden>', doc) and 'id="cg-orignote">' in doc
    assert re.search(r'class="cg-view is-on" data-view="ch"', doc)


def test_switch_without_generated_view_is_disabled_and_says_why():
    doc = player_html(_de(), [], audio_src=None, dialect=None, view="ch")
    assert re.search(r'data-view="ch" disabled aria-disabled="true"', doc)
    body = doc.split("<body>")[1].split("<script>")[0]
    assert NO_DIALECT_DE in body and 'class="cg-transcript" data-view="ch"' not in body and "cg-orignote" not in body
    assert re.search(r'class="cg-view is-on" data-view="de"', doc)
    res = CallResult(call_id="Z", decision={"label": "no_alert", "score": 0.0, "uncertainty": 0.0, "threshold": 0.5}, transcript=_de())
    assert dialect_view(res) is None
    res.display_views["gsw"] = _gsw()
    assert dialect_view(res) is not None


def _iframes(at: AppTest) -> list[str]:
    out, stack = [], list(at.main)
    while stack:
        node = stack.pop()
        proto = getattr(node, "proto", None)
        if proto is not None and getattr(proto, "srcdoc", "") and proto.srcdoc not in out:
            out.append(proto.srcdoc)
        children = getattr(node, "children", None)
        if isinstance(children, dict):
            stack += list(children.values())
    return out


def test_call_page_shows_the_generated_view_where_it_exists(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = write_fixture_env(tmp_path)
    p = env.result_path(ALARM_ID)
    raw = json.loads(p.read_text())
    tr = Transcript.model_validate(raw["transcript"])
    raw["display_views"] = {"gsw": translated_copy(tr, {s.id: f"{MARK} {i}" for i, s in enumerate(tr.segments)},
                                                   "gsw", "ctc_dialect:x").model_dump(mode="json")}
    p.write_text(json.dumps(raw))
    monkeypatch.setenv(be.ENV_ARGS, env.args)
    for cid, available in ((ALARM_ID, True), (HARMLESS_ID, False)):
        at = AppTest.from_file(str(APP), default_timeout=120)
        at.query_params["call"] = cid
        at.query_params["ansicht"] = "ch"
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        docs = [d for d in _iframes(at) if "cg-views" in d]
        assert len(docs) == 1, cid
        doc = docs[0]
        if available:
            assert re.search(r'class="cg-view is-on" data-view="ch"', doc) and f'id="ch-{tr.segments[0].id}"' in doc
            assert MARK in doc and "Automatisch erzeugt" in doc
        else:
            assert 'disabled aria-disabled="true"' in doc and NO_DIALECT_DE in doc and 'id="ch-' not in doc
