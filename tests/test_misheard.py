"""«Möglicherweise verhört»: passage ASR confidence, the label-free threshold, the pipeline annotation and
the officer UI badge. Offline."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, write_fixture_env

from callguard import misheard as mh
from callguard.config import AppConfig, Paths
from callguard.pipeline import Pipeline
from callguard.types import CallResult, Decision, Passage, Segment, Transcript
from callguard.ui import backend as be

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"


def _t(confs: list[float | None]) -> Transcript:
    return Transcript(call_id="c", segments=[Segment(id=f"S{i:03d}", start=10.0 * i, end=10.0 * i + 8, text=f"s{i}",
                                                     confidence=c) for i, c in enumerate(confs)])


def _p(ids: list[str], start: float = 0.0, end: float = 1.0) -> Passage:
    return Passage(family="trade", start=start, end=end, segment_ids=ids, score=0.9)


def test_passage_confidence_is_the_lowest_segment_and_falls_back_to_time():
    t = _t([0.9, 0.42, 0.8, None])
    assert mh.passage_confidence(t, _p(["S000", "S001"])) == (0.42, "S001")
    assert mh.passage_confidence(t, _p([], start=21.0, end=25.0)) == (0.8, "S002")  # no ids: by time
    assert mh.passage_confidence(t, _p(["S003"])) == (None, None)  # ASR without confidences never flags
    assert not mh.is_misheard(None, 0.6) and not mh.is_misheard(0.1, None)
    assert mh.is_misheard(0.59, 0.6) and not mh.is_misheard(0.6, 0.6)


def test_threshold_default_custom_and_off():
    assert mh.threshold_of({}) == mh.DEFAULT_THRESHOLD == 0.60
    assert mh.threshold_of({"misheard_below": 0.5}) == 0.5
    assert mh.threshold_of({"misheard_below": 0}) is None and mh.threshold_of({"misheard_below": None}) is None
    assert mh.bottom_quantile([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, None]) == pytest.approx(0.19)
    assert mh.bottom_quantile([]) is None


def test_annotate_marks_passages_in_the_result():
    t = _t([0.9, 0.3])
    d = Decision(label="alarm", score=0.9, uncertainty=0.1, threshold=0.55,
                 passages=[_p(["S000"]), _p(["S000", "S001"])])
    r = CallResult(call_id="c", transcript=t, decision=d)
    assert mh.annotate(r, 0.6) == 1
    assert [(p.asr_confidence, p.misheard) for p in r.decision.passages] == [(0.9, False), (0.3, True)]
    dumped = CallResult.model_validate_json(r.model_dump_json())
    assert dumped.decision.passages[1].misheard  # it is in result.json


def test_pipeline_annotates_passages(tmp_path):
    cfg = AppConfig(name="t", asr={"type": "reference"}, diarizer={"type": "none"}, sinks=[],
                    checks=[{"name": "keywords", "type": "keywords", "weight": 0.35}],
                    paths=Paths(cache_dir=str(tmp_path / "cache"), runs_dir=str(tmp_path / "runs")),
                    snippets={"pad": 2.0, "misheard_below": 0.6})
    t = Transcript(call_id="x", segments=[
        Segment(id="S001", start=0, end=4, text="Guten Tag.", confidence=0.95),
        Segment(id="S002", start=5, end=11, confidence=0.31,
                text="Ich möchte die Aktie vor der Meldung kaufen, die Quartalszahlen sind nicht publiziert.")])
    r = Pipeline(cfg).process_transcript(t)
    assert r.decision.passages
    p = next(p for p in r.decision.passages if "S002" in p.segment_ids)
    assert p.asr_confidence == pytest.approx(0.31) and p.misheard


def test_detail_page_shows_misheard_badge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, env.args)
    path = env.result_path(ALARM_ID)
    r = CallResult.model_validate_json(path.read_text())
    for s in r.transcript.segments:
        if s.id == "S007":  # the buy-before-the-announcement sentence
            s.confidence = 0.31
    path.write_text(r.model_dump_json(indent=1))

    at = AppTest.from_file(str(APP), default_timeout=90)
    at.query_params["call"] = ALARM_ID
    at.run()
    at.switch_page("views/detail.py").run()
    assert not at.exception, [e.message for e in at.exception]
    body = "\n".join(str(m.value) for m in at.markdown)
    assert "Möglicherweise verhört — bitte anhören" in body and "`S007`" in body and "0.31" in body
    assert body.count("möglicherweise verhört]") == 1  # only the passage with S007 gets the badge
