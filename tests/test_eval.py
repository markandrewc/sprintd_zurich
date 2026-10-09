from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from callguard import eval as ev
from callguard import registry
from callguard.config import load_config
from callguard.data import Call, Expected, load_calls
from callguard.pipeline import Pipeline
from callguard.plugins import Diarizer
from callguard.types import CallResult, CheckResult, Decision, FamilyScore, Segment, Transcript

DATA = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/data"


def row(call_id, expected, predicted, level=1, noisy=False, top=None, exp_fam=None, score=0.5, error=None):
    return {"call_id": call_id, "dialogue_id": call_id.split("-K")[0], "level": level, "noisy": noisy,
            "expected": expected, "predicted": predicted, "score": score, "uncertainty": 0.1,
            "top_family": top, "expected_family": exp_fam, "error": error}


def call(call_id: str, label: str, family: str = "trade", level: int = 1, noisy: bool = False) -> Call:
    return Call(call_id=call_id, dialogue_id=call_id.split("-K")[0], level=level, variant=2 if noisy else 1,
                noisy=noisy, audio_path=Path(f"/nonexistent/{call_id}.wav"),
                expected=Expected(label=label, family=family, event="", reason="", open_question=""))


def pipeline(tmp_path: Path) -> Pipeline:
    """Real pipeline with real families and fusion but no checks: decide() is all we exercise."""
    cfg = load_config("base", ["checks=[]", "sinks=[]", f"paths.runs_dir={tmp_path / 'runs'}",
                               f"paths.cache_dir={tmp_path / 'cache'}"])
    return Pipeline(cfg)


def result(call_id: str, trade: float) -> CallResult:
    t = Transcript(call_id=call_id, segments=[Segment(id="S000", start=0, end=5, text="Hallo")])
    checks = {"llm": CheckResult(check="llm", type="fake", family_scores={"trade": FamilyScore(score=trade)})}
    return CallResult(call_id=call_id, transcript=t, checks=checks,
                      decision=Decision(label="no_alert", score=0, uncertainty=0, threshold=0.55))


# -- metrics -------------------------------------------------------------------------------------


def test_metrics_counts_and_rates():
    rows = [
        row("A-K1", "alarm", "alarm", top="trade", exp_fam="trade"),
        row("A-K2", "alarm", "review", noisy=True, top="access", exp_fam="trade"),
        row("B-K1", "alarm", "no_alert", level=2, exp_fam="splitting"),
        row("C-K1", "review", "review", level=3),
        row("D-K1", "review", "no_alert", level=3),
        row("E-K1", "no_alert", "alarm", level=2),
        row("F-K1", "no_alert", "no_alert"),
        row("G-K1", "no_alert", "no_alert", noisy=True),
        row("H-K1", None, "alarm"),  # no ground truth -> not scored
    ]
    m = ev.metrics(rows)
    assert m["n"] == 8 and m["unlabeled"] == 1
    assert m["confusion"]["alarm"] == {"alarm": 1, "review": 1, "no_alert": 1}
    assert m["accuracy"] == pytest.approx(4 / 8)
    f = m["flag"]  # positives: 3 alarm + 2 review expected; flagged: A, A2, C, E
    assert (f["tp"], f["fp"], f["fn"], f["tn"]) == (3, 1, 2, 2)
    assert f["precision"] == pytest.approx(0.75) and f["recall"] == pytest.approx(0.6)
    assert f["false_alarm_rate"] == pytest.approx(1 / 3, abs=1e-4) and f["miss_rate"] == pytest.approx(0.4)
    assert f["f1"] == pytest.approx(2 * 3 / (2 * 3 + 1 + 2), abs=1e-4)
    a = m["alarm"]
    assert (a["tp"], a["fp"], a["fn"]) == (1, 1, 2)
    assert m["review_handling"] == {"n": 2, "escalated": 1, "as_review": 1, "escalation_rate": 0.5}
    assert m["family_hit"] == {"n": 3, "hits": 1, "rate": pytest.approx(1 / 3, abs=1e-4)}
    assert set(m["by_level"]) == {"1", "2", "3"} and m["by_level"]["3"]["n"] == 2
    assert m["by_noise"]["noisy"]["n"] == 2 and m["by_noise"]["clean"]["n"] == 6
    assert m["workload"] == {"alarms": 2, "reviews": 2, "flag_rate": 0.5}


def test_metrics_undefined_rates_are_none_not_crash():
    m = ev.metrics([row("A-K1", "no_alert", "no_alert")])
    assert m["flag"]["precision"] is None and m["flag"]["recall"] is None and m["flag"]["f1"] is None
    assert m["flag"]["false_alarm_rate"] == 0.0
    assert ev.metrics([])["n"] == 0


def test_errors_count_as_review():
    r = ev.error_row("A-K1", call("A-K1", "alarm"), "RuntimeError: x")
    assert r["predicted"] == "review" and r["error"]
    assert ev.metrics([r])["errors"] == 1


# -- sweep / suggestion --------------------------------------------------------------------------


def test_sweep_reruns_only_fusion_and_suggests_middle_of_best_plateau(tmp_path):
    pipe = pipeline(tmp_path)
    calls = [call("A-K1", "alarm"), call("B-K1", "review"), call("C-K1", "no_alert"), call("D-K1", "no_alert")]
    results = [result("A-K1", 0.8), result("B-K1", 0.45), result("C-K1", 0.3), result("D-K1", 0.1)]
    ts = [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]
    swept = ev.sweep(pipe, results, calls, ts)
    by_t = {s["threshold"]: s["metrics"] for s in swept}
    assert by_t[0.55]["accuracy"] == 1.0
    assert by_t[0.45]["flag"]["fp"] == 1  # 0.30 falls into the band [0.30, 0.45)
    assert by_t[0.65]["flag"]["fn"] == 1  # 0.45 drops below the band [0.50, 0.65)
    s = ev.suggest_threshold(swept)
    assert s["tied"] == [0.5, 0.55, 0.6]
    assert s["threshold"] == 0.55
    assert "0.55" in s["reason"]
    # cached results are untouched
    assert all(r.decision.label == "no_alert" for r in results)


def test_sweep_accepts_officer_feedback_mapping(tmp_path):
    pipe = pipeline(tmp_path)
    results = [result("X-K1", 0.7), result("Y-K1", 0.5)]
    swept = ev.sweep(pipe, results, {"X-K1": "alarm", "Y-K1": "no_alert"}, [0.5, 0.6, 0.8])
    best = ev.suggest_threshold(swept)
    # 0.5 alarms Y, 0.6 still reviews Y (band [0.45, 0.6)); 0.8 reviews X (still flagged) and clears Y
    assert best["threshold"] == 0.8
    assert best["flag_f1"] == 1.0


def test_cross_validate_picks_each_threshold_without_the_held_out_dialogue(tmp_path):
    pipe = pipeline(tmp_path)
    labels = {"A": "alarm", "B": "alarm", "C": "alarm", "D": "no_alert", "E": "no_alert", "F": "no_alert"}
    scores = {"A": 0.9, "B": 0.8, "C": 0.7, "D": 0.3, "E": 0.2, "F": 0.1}
    calls, results = [], []
    for d, lbl in labels.items():
        for k, noisy in (("K1", False), ("K2", True)):
            calls.append(call(f"Stufe1_{d}01-{k}", lbl, noisy=noisy))
            results.append(result(f"Stufe1_{d}01-{k}", scores[d]))
    cv = ev.cross_validate(pipe, results, calls, n_folds=3, thresholds=[0.2, 0.4, 0.5, 0.6, 0.8])
    assert cv["n_folds"] == 3 and sum(f["n_test"] for f in cv["folds"]) == len(results)
    held_out = [set(f["dialogues"]) for f in cv["folds"]]
    assert all(a.isdisjoint(b) for i, a in enumerate(held_out) for b in held_out[i + 1:])  # K1+K2 share a fold
    assert cv["metrics"]["n"] == 12 and cv["metrics"]["flag"]["f1"] == 1.0
    assert ev.cross_validate(pipe, results[:2], calls) is None  # one dialogue: nothing to hold out


def test_suggest_prefers_recall_on_f1_tie():
    def entry(t, f1, recall, far):
        return {"threshold": t, "metrics": {"n": 4, "flag": {"f1": f1, "recall": recall, "precision": 0.5,
                                                               "false_alarm_rate": far, "miss_rate": 1 - recall}}}
    s = ev.suggest_threshold([entry(0.3, 0.8, 1.0, 0.5), entry(0.5, 0.8, 0.67, 0.0), entry(0.7, 0.5, 0.3, 0.0)])
    assert s["threshold"] == 0.3
    assert ev.suggest_threshold([]) is None


def test_suggest_skips_flag_everything_and_respects_false_alarm_cap():
    def entry(t, f1, recall, far, flag_rate):
        return {"threshold": t, "metrics": {"n": 10, "workload": {"flag_rate": flag_rate},
                                            "flag": {"f1": f1, "recall": recall, "precision": 0.5,
                                                     "false_alarm_rate": far, "miss_rate": 1 - recall}}}
    swept = [entry(0.2, 0.7, 1.0, 1.0, 1.0), entry(0.4, 0.6, 0.8, 0.4, 0.6), entry(0.6, 0.5, 0.5, 0.1, 0.3)]
    s = ev.suggest_threshold(swept)
    assert s["threshold"] == 0.4 and "nicht berücksichtigt" in s["reason"]
    assert ev.suggest_threshold(swept, max_false_alarm_rate=0.2)["threshold"] == 0.6
    assert ev.suggest_threshold(swept, max_false_alarm_rate=0.0)["threshold"] == 0.4  # unreachable cap ignored
    assert ev.suggest_threshold(swept[:1])["threshold"] == 0.2  # nothing else to offer


# -- evaluate / report ---------------------------------------------------------------------------


def test_evaluate_catches_per_call_errors(tmp_path):
    pipe = pipeline(tmp_path)
    calls = [call("A-K1", "alarm"), call("B-K1", "no_alert")]

    def process(audio_path, call_id=None, *, emit=True, overrides=None):
        assert emit is False
        if call_id == "B-K1":
            raise RuntimeError("ASR exploded")
        r = result(call_id, 0.9)
        r.decision = pipe.decide(r.transcript, r.checks, overrides)
        return r

    pipe.process = process
    seen = []
    rows, results = ev.evaluate(pipe, calls, progress=lambda i, n, c, r: seen.append((i, n, c.call_id)))
    assert [r["predicted"] for r in rows] == ["alarm", "review"]
    assert rows[0]["top_family"] == "trade" and rows[0]["expected_family"] == "trade"
    assert "ASR exploded" in rows[1]["error"]
    assert len(results) == 1
    assert seen == [(1, 2, "A-K1"), (2, 2, "B-K1")]


def test_write_report(tmp_path):
    rows = [row("A-K1", "alarm", "alarm", top="trade", exp_fam="trade"), row("B-K1", "no_alert", "review", level=2)]
    m = ev.metrics(rows)
    swept = [{"threshold": 0.5, "metrics": m}]
    sug = ev.suggest_threshold(swept)
    j, md = ev.write_report(tmp_path / "eval", m, rows, swept, sug, {"config": "oracle"})
    data = json.loads(j.read_text())
    assert data["metrics"]["n"] == 2 and data["suggestion"]["threshold"] == 0.5 and len(data["rows"]) == 2
    text = md.read_text()
    for needle in ("# callguard Evaluation - oracle", "Fehlalarmquote", "Konfusionsmatrix", "| alarm | 1 | 0 | 0 |",
                   "Schwellen-Sweep", "**Vorschlag:**", "| A-K1 |", "Stufe 2"):
        assert needle in text


# -- integration with the oracle profile (only once teammates' plugins exist) --------------------

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


@pytest.mark.skipif(not all(map(_have, ORACLE_MODULES)) or not DATA.exists(),
                    reason="oracle plugins (reference ASR, checks, fake LLM) not available yet")
def test_evaluate_oracle_end_to_end(tmp_path, oracle_plugins):
    cfg = load_config("oracle", ["llms.default.type=fake", f"paths.runs_dir={tmp_path / 'runs'}",
                                 f"paths.cache_dir={tmp_path / 'cache'}"])
    pipe = Pipeline(cfg)
    calls = [c for c in load_calls(DATA) if c.call_id in ("Stufe1_D02-K1", "Stufe2_C05-K3")]
    rows, results = ev.evaluate(pipe, calls)
    assert len(rows) == 2 and all(r["error"] is None for r in rows), rows
    swept = ev.sweep(pipe, results, calls, [0.3, 0.5, 0.7])
    assert len(swept) == 3 and ev.suggest_threshold(swept) is not None


def test_load_results_skips_broken_files(tmp_path):
    good = result("A-K1", 0.9)
    (tmp_path / "A-K1").mkdir()
    (tmp_path / "A-K1/result.json").write_text(good.model_dump_json())
    (tmp_path / "B-K1").mkdir()
    (tmp_path / "B-K1/result.json").write_text("{not json")
    (tmp_path / "eval").mkdir()  # report folder next to call folders is ignored
    assert [r.call_id for r in ev.load_results(tmp_path)] == ["A-K1"]
