from __future__ import annotations

import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import numpy as np
import pytest
import soundfile as sf
from typer.testing import CliRunner

from callguard import cli, registry
from callguard.config import load_config
from callguard.context import Context
from callguard.pipeline import Pipeline
from callguard.plugins import Diarizer
from callguard.sinks.json_dir import JsonDirSink
from callguard.sinks.outcept import OutceptTriggerSink
from callguard.types import (CallResult, CheckResult, Decision, FamilyScore, Finding, FusedFamily, Passage, Segment,
                             Transcript)

runner = CliRunner()
DATA = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/data"

# dialogue -> (family, score, verdict): one alarm, one harmless, one open case
CANNED = {"Stufe1_D02": ("trade", 0.9, "present"), "Stufe1_D03": ("trade", 0.05, "absent"),
          "Stufe3_C17": ("access", 0.3, "undetermined")}


class StubPipeline(Pipeline):
    """Real config, families, fusion, snippets and sinks; the checks are replaced by canned scores so
    the CLI can be tested before (and independently of) the ASR/check plugins."""

    instances: list["StubPipeline"] = []

    def __init__(self, cfg, *, use_cache=True):
        super().__init__(cfg.model_copy(update={"checks": []}), use_cache=use_cache)
        self.processed: list[str] = []
        StubPipeline.instances.append(self)

    def process(self, audio_path, call_id=None, *, emit=True, overrides=None):
        audio_path = Path(audio_path)
        call_id = call_id or audio_path.stem
        if "broken" in call_id:
            raise RuntimeError("ASR exploded")
        self.processed.append(call_id)
        fam, score, verdict = CANNED.get(call_id.split("-K")[0], ("trade", 0.9, "present"))
        t = Transcript(call_id=call_id, audio_path=str(audio_path), segments=[
            Segment(id="S000", start=0.0, end=1.0, text="Grüezi."),
            Segment(id="S001", start=1.0, end=2.0, text="Ich möchte vor der Meldung kaufen.")])
        checks = {"stub": CheckResult(check="stub", type="stub", family_scores={
            fam: FamilyScore(score=score, verdict=verdict, reason="Kaufwunsch vor der Meldung")},
            findings=[Finding(check="stub", family=fam, score=score, segment_ids=["S001"],
                              reason="Kaufwunsch vor der Meldung")])}
        result = CallResult(call_id=call_id, audio_path=str(audio_path), transcript=t, checks=checks,
                            decision=self.decide(t, checks, overrides), config_name=self.cfg.name,
                            timings={"asr": 0.0})
        self.make_snippets(result)
        if emit:
            self.emit(result)
        return result


@pytest.fixture
def stub(monkeypatch):
    StubPipeline.instances.clear()
    monkeypatch.setattr(cli, "Pipeline", StubPipeline)
    return StubPipeline


def opts(tmp_path: Path, config: str = "base") -> list[str]:
    return ["-c", config, "--set", f"paths.runs_dir={tmp_path / 'runs'}",
            "--set", f"paths.cache_dir={tmp_path / 'cache'}"]


def wav(path: Path, seconds: float = 3.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), np.zeros(int(16000 * seconds), dtype=np.float32), 16000)
    return path


def test_plugins_lists_every_kind():
    r = runner.invoke(cli.app, ["plugins", "-c", "oracle"])
    assert r.exit_code == 0, r.output
    for needle in ("asr", "diarizer", "check", "fusion", "llm", "sink", "weighted", "json_dir"):
        assert needle in r.output


def test_unknown_config_is_a_clean_error(stub):
    r = runner.invoke(cli.app, ["batch", "-c", "does-not-exist"])
    assert r.exit_code == 2
    assert "not found" in r.output


def test_run_prints_decision_and_writes_result(stub, tmp_path):
    audio = wav(tmp_path / "in" / "Stufe1_D02-K1.wav")
    r = runner.invoke(cli.app, ["run", str(audio), *opts(tmp_path)])
    assert r.exit_code == 0, r.output
    assert "ALARM" in r.output and "00:01-00:02" in r.output and "Kaufwunsch vor der Meldung" in r.output
    res = json.loads((tmp_path / "runs/base/Stufe1_D02-K1/result.json").read_text())
    assert res["decision"]["label"] == "alarm"
    snippet = res["decision"]["passages"][0]["snippet_path"]
    assert Path(snippet).exists()


def test_run_json_and_failure_exit_code(stub, tmp_path):
    good = wav(tmp_path / "Stufe1_D03-K1.wav")
    r = runner.invoke(cli.app, ["run", str(good), "--json", *opts(tmp_path)])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["decision"]["label"] == "no_alert"
    bad = wav(tmp_path / "broken.wav")
    r = runner.invoke(cli.app, ["run", str(bad), *opts(tmp_path)])
    assert r.exit_code == 1 and "ASR exploded" in r.output


@pytest.mark.skipif(not DATA.exists(), reason="case data not available")
def test_batch_filters_and_summarizes(stub, tmp_path):
    r = runner.invoke(cli.app, ["batch", "--calls", "Stufe1_D02-K1,Stufe1_D03-K1,Stufe3_C17-K3,nope",
                                "--level", "1", *opts(tmp_path)])
    assert r.exit_code == 0, r.output
    assert stub.instances[-1].processed == ["Stufe1_D02-K1", "Stufe1_D03-K1"]
    assert "Unknown call ids ignored: nope" in r.output
    assert (tmp_path / "runs/base/Stufe1_D03-K1/result.json").exists()


@pytest.mark.skipif(not DATA.exists(), reason="case data not available")
def test_eval_writes_report_and_suggests_threshold(stub, tmp_path):
    r = runner.invoke(cli.app, ["eval", "--calls", "Stufe1_D02-K1,Stufe1_D03-K1,Stufe3_C17-K3",
                                "--thresholds", "0.3,0.5,0.7", *opts(tmp_path)])
    assert r.exit_code == 0, r.output
    assert stub.instances[-1].processed == ["Stufe1_D02-K1", "Stufe1_D03-K1", "Stufe3_C17-K3"]
    report = json.loads((tmp_path / "runs/base/eval/report.json").read_text())
    assert report["metrics"]["accuracy"] == 1.0
    assert [s["threshold"] for s in report["sweep"]] == [0.3, 0.5, 0.7]
    assert report["suggestion"]["threshold"] in (0.3, 0.5, 0.7)
    assert "Vorschlag" in r.output and "Fehlalarmquote" in r.output
    assert (tmp_path / "runs/base/eval/report.md").exists()
    assert (tmp_path / "runs/base/Stufe3_C17-K3/result.json").exists()  # UI can show eval calls


@pytest.mark.skipif(not DATA.exists(), reason="case data not available")
def test_eval_folds_filter(stub, tmp_path):
    r = runner.invoke(cli.app, ["eval", "--folds", "2", "--clean-only", "--level", "1", "--no-sweep",
                                "--no-write-results", *opts(tmp_path)])
    assert r.exit_code == 0, r.output
    assert stub.instances[-1].processed == ["Stufe1_D02-K1", "Stufe1_D03-K1"]  # fold 2 of level 1


def test_bad_number_lists_fail_fast(stub, tmp_path):
    r = runner.invoke(cli.app, ["eval", "--thresholds", "0.3,abc", *opts(tmp_path)])
    assert r.exit_code == 2 and not stub.instances  # rejected before any pipeline is built
    r = runner.invoke(cli.app, ["eval", "--folds", "x", *opts(tmp_path)])
    assert r.exit_code == 2


def test_watch_processes_each_file_once(stub, tmp_path):
    inbox = tmp_path / "inbox"
    wav(inbox / "Stufe1_D02-K1.wav")
    wav(inbox / "Stufe1_D03-K1.wav")
    (inbox / "notes.txt").write_text("not audio")
    state = tmp_path / "state.json"
    args = ["watch", str(inbox), "--once", "--state", str(state), *opts(tmp_path)]

    r = runner.invoke(cli.app, args)
    assert r.exit_code == 0, r.output
    assert stub.instances[-1].processed == ["Stufe1_D02-K1", "Stufe1_D03-K1"]
    r = runner.invoke(cli.app, args)
    assert stub.instances[-1].processed == []

    wav(inbox / "Stufe3_C17-K3.wav")
    wav(inbox / "broken.wav")
    r = runner.invoke(cli.app, args)
    assert stub.instances[-1].processed == ["Stufe3_C17-K3"]
    saved = json.loads(state.read_text())
    assert {Path(k).name: v["status"] for k, v in saved.items()} == {
        "Stufe1_D02-K1.wav": "done", "Stufe1_D03-K1.wav": "done", "Stufe3_C17-K3.wav": "done",
        "broken.wav": "error"}
    assert saved[str((inbox / "Stufe1_D02-K1.wav").resolve())]["label"] == "alarm"


def test_watch_skips_files_still_being_written(stub, tmp_path):
    inbox = tmp_path / "inbox"
    wav(inbox / "Stufe1_D02-K1.wav")
    assert cli._ready_files(inbox, {}, settle=60.0, once=False) == []
    assert len(cli._ready_files(inbox, {}, settle=0.0, once=False)) == 1


def test_ui_launches_streamlit_with_profile(monkeypatch, tmp_path):
    app_file = tmp_path / "src/callguard/ui/app.py"
    app_file.parent.mkdir(parents=True)
    app_file.write_text("")
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    calls = []

    class Done:
        returncode = 0

    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: calls.append(cmd) or Done())
    r = runner.invoke(cli.app, ["ui", "-c", "oracle", "--port", "8600"])
    assert r.exit_code == 0, r.output
    cmd = calls[0]
    assert cmd[1:4] == ["-m", "streamlit", "run"] and cmd[4] == str(app_file)
    assert cmd[cmd.index("--") + 1:] == ["--config", "oracle"]
    assert "--server.port" in cmd

    monkeypatch.setattr(cli, "ROOT", tmp_path / "nowhere")
    assert runner.invoke(cli.app, ["ui"]).exit_code == 1


# -- real plugins, oracle profile (skipped until teammates' modules exist) -----------------------

ORACLE_MODULES = ["callguard.asr.reference", "callguard.checks.keywords", "callguard.checks.patterns",
                  "callguard.checks.llm_judge", "callguard.checks.geval", "callguard.llm.fake"]


def _have(mod: str) -> bool:
    try:
        return importlib.util.find_spec(mod) is not None
    except ImportError:
        return False


class PassThroughDiarizer(Diarizer):
    """Stand-in for the 'none' diarizer until that module lands; transcripts keep their script roles."""

    def diarize(self, audio_path, transcript):
        return transcript


@pytest.fixture
def oracle_plugins(monkeypatch):
    if not _have("callguard.diarization.none"):
        monkeypatch.setitem(registry._REGISTERED["diarizer"], "none", PassThroughDiarizer)


oracle_ready = pytest.mark.skipif(not all(map(_have, ORACLE_MODULES)) or not DATA.exists(),
                                  reason="oracle plugins (reference ASR, checks, fake LLM) not available yet")


@oracle_ready
def test_run_oracle_with_fake_llm(tmp_path, oracle_plugins):
    audio = DATA / "Audio" / "Stufe1_D02-K1.wav"
    r = runner.invoke(cli.app, ["run", str(audio), *opts(tmp_path, "oracle"), "--set", "llms.default.type=fake"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "runs/oracle/Stufe1_D02-K1/result.json").exists()


@oracle_ready
def test_eval_oracle_with_fake_llm(tmp_path, oracle_plugins):
    r = runner.invoke(cli.app, ["eval", "--calls", "Stufe1_D02-K1,Stufe1_D03-K1", "--thresholds", "0.4,0.6",
                                *opts(tmp_path, "oracle"), "--set", "llms.default.type=fake"])
    assert r.exit_code == 0, r.output
    report = json.loads((tmp_path / "runs/oracle/eval/report.json").read_text())
    assert report["metrics"]["n"] == 2 and report["metrics"]["errors"] == 0


# -- sinks ---------------------------------------------------------------------------------------

SERVER = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/server.py"


def ctx(tmp_path: Path) -> Context:
    return Context(load_config("base", [f"paths.runs_dir={tmp_path / 'runs'}", "app.base_url=http://cg.local:8501/",
                                        "snippets.link_pad=10"]))


def call_result(label: str = "alarm", passages: int = 2, reason: str = "Kaufwunsch vor der Meldung") -> CallResult:
    ps = [Passage(family="trade", family_label="Insiderhandel (Information und Kaufwunsch)", start=87.4 + 60 * i,
                  end=95.0 + 60 * i, score=0.9 - 0.1 * i, reasons=[f"llm_judge: {reason}"], checks=["llm_judge"],
                  text="Ich möchte vor der Meldung kaufen.") for i in range(passages)]
    d = Decision(label=label, score=0.82, uncertainty=0.1, threshold=0.55, passages=ps,
                 reasons=["Alarm: Score 0.82 für 'Insiderhandel' >= Schwelle 0.55."],
                 families={"trade": FusedFamily(family="trade", label="Insiderhandel (Information und Kaufwunsch)",
                                                score=0.82, uncertainty=0.1),
                           "numbers": FusedFamily(family="numbers", label="Zahlenobjekte", score=0.2,
                                                  uncertainty=0.1)})
    return CallResult(call_id="Stufe1_D02-K1", transcript=Transcript(call_id="Stufe1_D02-K1"), decision=d)


def test_json_dir_sink_writes_where_the_ui_reads(tmp_path):
    c = ctx(tmp_path)
    JsonDirSink(c).emit(call_result())
    out = tmp_path / "runs/base/Stufe1_D02-K1/result.json"
    assert CallResult.model_validate_json(out.read_text()).decision.label == "alarm"
    assert out.read_text().startswith("{\n \"call_id\"")  # indent=1
    JsonDirSink(c, dir=str(tmp_path / "elsewhere")).emit(call_result())
    assert (tmp_path / "elsewhere/Stufe1_D02-K1/result.json").exists()


def test_outcept_trigger_bodies(tmp_path):
    sink = OutceptTriggerSink(ctx(tmp_path))
    bodies = sink.triggers(call_result())
    assert len(bodies) == 2
    b = bodies[0]
    assert b["url"] == "http://cg.local:8501/?call=Stufe1_D02-K1&t=77"
    assert b["title"] == "[ALARM] Insiderhandel - Stufe1_D02-K1 @ 01:27"
    assert "llm_judge: Kaufwunsch vor der Meldung" in b["description"]
    assert "Alarm: Score 0.82" in b["description"]
    assert sink.triggers(call_result("no_alert")) == []
    assert OutceptTriggerSink(ctx(tmp_path), labels=["alarm"]).triggers(call_result("review")) == []

    one = OutceptTriggerSink(ctx(tmp_path), per_passage=False).triggers(call_result())
    assert len(one) == 1 and one[0]["url"].endswith("&t=77")
    empty = sink.triggers(call_result("review", passages=0))
    assert empty[0]["url"].endswith("&t=0") and empty[0]["title"].startswith("[REVIEW] Insiderhandel")

    long = sink.triggers(call_result(reason="x" * 5000))[0]
    assert len(long["description"]) <= 2000 and len(long["title"]) <= 200


def test_outcept_sink_never_raises_when_api_is_down(tmp_path, monkeypatch, caplog):
    attempts = []

    def post(*a, **kw):
        attempts.append(a)
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", post)
    OutceptTriggerSink(ctx(tmp_path)).emit(call_result())
    assert len(attempts) == 1  # gives up after the first failure instead of timing out per passage
    assert "not sent" in caplog.text


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.mark.skipif(not SERVER.exists(), reason="case trigger server not available")
def test_outcept_sink_against_case_trigger_server(tmp_path):
    port = _free_port()
    proc = subprocess.Popen([sys.executable, str(SERVER)], env={**os.environ, "PORT": str(port), "HOST": "127.0.0.1"},
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                if httpx.get(f"{base}/health", timeout=0.5).status_code == 200:
                    break
            except httpx.HTTPError:
                time.sleep(0.1)
        OutceptTriggerSink(ctx(tmp_path), url=f"{base}/triggers").emit(call_result())
        got = httpx.get(f"{base}/triggers?format=json").json()
        assert got["count"] == 2
        assert got["triggers"][0]["title"] == "[ALARM] Insiderhandel - Stufe1_D02-K1 @ 01:27"
        assert got["triggers"][1]["url"].endswith("&t=137")
    finally:
        proc.terminate()
        proc.wait(timeout=5)
