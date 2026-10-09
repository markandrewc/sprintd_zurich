"""A check that failed at processing time (LLM server stopped mid-batch) must stay visible downstream.

Seen on real data: with the LLM server down, a local call came out ``no_alert`` on keywords alone and an
oracle eval reported "Fehler 0" although both LLM checks had failed on every call.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, write_fixture_env

from callguard import eval as ev
from callguard.config import load_config
from callguard.types import CallResult, CheckResult, Decision, FamilyScore, Segment, Transcript
from callguard.ui import backend as be

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
DOWN = "RuntimeError('LLM server at http://127.0.0.1:8001/v1 not reachable')"


def result(call_id: str, **check_meta: dict) -> CallResult:
    t = Transcript(call_id=call_id, segments=[Segment(id="S000", start=0, end=5, text="Hallo")])
    checks = {"keywords": CheckResult(check="keywords", type="keywords",
                                      family_scores={"trade": FamilyScore(score=0.0)})}
    checks |= {name: CheckResult(check=name, type=name, meta=meta) for name, meta in check_meta.items()}
    return CallResult(call_id=call_id, transcript=t, checks=checks,
                      decision=Decision(label="no_alert", score=0, uncertainty=0.4, threshold=0.55))


def test_eval_rows_metrics_and_report_name_failed_checks():
    rows = [ev.make_row(result("A-K1", llm_judge={"error": DOWN}, geval={"error": DOWN}), "no_alert"),
            ev.make_row(result("B-K1", geval={"errors": {"trade": "timeout"}}), "alarm"),
            ev.make_row(result("C-K1"), "no_alert")]
    assert [r["failed_checks"] for r in rows] == [["geval", "llm_judge"], ["geval"], []]
    m = ev.metrics(rows)
    assert m["errors"] == 0  # the calls themselves did not fail ...
    assert m["check_failures"] == {"calls": 2, "by_check": {"geval": 2, "llm_judge": 1}}  # ... their checks did
    md = ev.render_markdown(m, rows)
    assert "**Achtung:** In 2 von 3 Anrufen ist mindestens eine Prüfung ausgefallen (geval 2x, llm_judge 1x)" in md
    assert "| ok (ohne geval, llm_judge) |" in md
    clean = ev.render_markdown(ev.metrics(rows[2:]), rows[2:])
    assert "Achtung" not in clean and "ohne" not in clean


def test_error_rows_and_hand_built_rows_have_no_failed_checks():
    assert ev.error_row("A-K1", "alarm", "boom")["failed_checks"] == []
    legacy = {"call_id": "A-K1", "expected": "alarm", "predicted": "alarm", "error": None}  # no key at all
    assert ev.metrics([legacy])["check_failures"] == {"calls": 0, "by_check": {}}


@pytest.fixture
def broken_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = write_fixture_env(tmp_path)
    path = env.result_path(HARMLESS_ID)
    r = CallResult.model_validate_json(path.read_text())
    r.checks["llm_judge"] = CheckResult(check="llm_judge", type="llm_judge", meta={"error": DOWN})
    path.write_text(r.model_dump_json(indent=1))
    monkeypatch.setenv(be.ENV_ARGS, env.args)
    return env


def test_inbox_rows_say_which_check_is_missing(broken_env):
    engine = be.Engine(load_config(broken_env.config, broken_env.sets))
    loaded = be.load_results(broken_env.runs_dir)
    fams = engine.families()
    rows = {r["call_id"]: r for r in be.inbox_rows(loaded, be.decide_all(engine, loaded, None, fams), fams)}
    assert rows[HARMLESS_ID]["failed_checks"] == ["llm_judge"]
    assert rows[HARMLESS_ID]["reason"].startswith("Checks failed: llm_judge · ")
    assert rows[ALARM_ID]["failed_checks"] == [] and not rows[ALARM_ID]["reason"].startswith("Checks failed")


def test_inbox_warns_about_calls_decided_without_a_check(broken_env):
    at = AppTest.from_file(str(APP), default_timeout=90).run()
    assert not at.exception, [e.message for e in at.exception]
    warning = next(w.value for w in at.warning if "decided without" in w.value)
    assert "1 call(s) were decided without llm_judge" in warning and HARMLESS_ID in warning
