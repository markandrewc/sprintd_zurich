"""Prüfmodi (sidebar operating modes) and the «Was heisst das für Ihr Team?» workload panel. Offline: tiny
fixture calls with a second reader's results, a fake LLM, Streamlit AppTest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, REVIEW_ID, FixtureEnv, write_fixture_env

from callguard import agreement as ag
from callguard import audit
from callguard.config import load_config
from callguard.types import CallResult, CheckResult, FamilyScore
from callguard.ui import backend as be
from callguard.ui import modes as md
from callguard.ui import workload as wl

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
READERS = ("llm_judge", "llm_judge_kev")

SPEC_YAML = """
experiment: two_readers
default: ausgewogen
readers: [llm_judge, llm_judge_kev]
reader_labels: [Qwen, Kev]
second_reader: Kev
modes:
  - {id: zurueckhaltend, label: Zurückhaltend, text: nur Kev, rule: b, needs_second: true, metrics: kev, threshold: suggested}
  - {id: ausgewogen, label: Ausgewogen, text: nur Qwen, rule: a, needs_second: false, metrics: champion, threshold: profile}
  - {id: vorsichtig, label: Vorsichtig, text: zwei Leser, rule: labels, needs_second: true, metrics: r1, threshold: profile}
"""


def _reader_b(a: CheckResult, score: float) -> CheckResult:
    """Reader B: same families as reader A, one flat opinion, no findings."""
    verdict = "present" if score >= 0.5 else "absent"
    return CheckResult(check=READERS[1], type=a.type, findings=[], meta={"model": "kev-4b"}, family_scores={
        f: FamilyScore(score=score, confidence=0.9, verdict=verdict, reason=f"Kev {score}")
        for f in a.family_scores})


def _with_b(r: CallResult, score: float) -> CallResult:
    checks = dict(r.checks)
    checks[READERS[1]] = _reader_b(r.checks[READERS[0]], score)
    return r.model_copy(update={"checks": checks})


B_SCORE = {ALARM_ID: 0.02, HARMLESS_ID: 0.95, REVIEW_ID: 0.5}  # B contradicts A on the alarm and the harmless call


def add_reader_b(env: FixtureEnv, skip: tuple[str, ...] = ()) -> None:
    for cid, score in B_SCORE.items():
        if cid in skip:
            continue
        p = env.result_path(cid)
        r = CallResult.model_validate_json(p.read_text())
        p.write_text(_with_b(r, score).model_dump_json(indent=1))


@pytest.fixture
def spec_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    p = tmp_path / "pruefmodi.yaml"
    p.write_text(SPEC_YAML)
    monkeypatch.setattr(md, "MODES_FILE", p)
    return p


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_fixture_env(tmp_path / "fx")
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    return e


# --------------------------------------------------------------------------------------------
# spec, metrics, wording
# --------------------------------------------------------------------------------------------


def test_shipped_spec_and_snapshot_load():
    spec = md.load_spec()
    assert spec.default == "ausgewogen" and spec.ids == ["zurueckhaltend", "ausgewogen", "vorsichtig"]
    assert [m.rule for m in spec.modes] == ["b", "a", "labels"]
    metrics = md.load_metrics(spec, None)  # committed snapshot (runs/ absent)
    assert set(metrics) == set(spec.ids)
    for m in metrics.values():
        assert m.n_calls > 0 and 0 <= m.far.lo <= m.far.value <= m.far.hi <= 1
        assert 0 <= m.recall.lo <= m.recall.value <= m.recall.hi <= 1


def test_spec_validation():
    with pytest.raises(ValueError, match="default mode must not need"):
        md.parse_spec({"default": "x", "modes": [{"id": "x", "rule": "b"}]})
    with pytest.raises(ValueError, match="rule must be"):
        md.parse_spec({"modes": [{"id": "x", "rule": "facts"}]})
    with pytest.raises(ValueError, match="not a mode"):
        md.parse_spec({"default": "y", "modes": [{"id": "x", "rule": "a"}]})


def _summary(tmp: Path) -> Path:
    def cv(tp, fn, fp, tn, far_ci, rec_ci):
        return {"n": tp + fn + fp + tn, "tp": tp, "fn": fn, "fp": fp, "tn": tn,
                "false_alarm_rate": fp / (fp + tn), "flag_recall": tp / (tp + fn), "review_recall": 0.5,
                "accuracy": 0.7, "ci": {"false_alarm_rate": {"lo": far_ci[0], "hi": far_ci[1]},
                                        "flag_recall": {"lo": rec_ci[0], "hi": rec_ci[1]}}}
    spec = md.load_spec()  # variant names come from config/pruefmodi.yaml (they follow the adopted table)
    kv, ch, r1 = (spec.get(i).metrics for i in ("zurueckhaltend", "ausgewogen", "vorsichtig"))
    exp = tmp / "runs" / "experiments" / "two_readers"
    exp.mkdir(parents=True)
    (exp / "summary.json").write_text(json.dumps({"split": "dev", "created": "2026-10-10", "variants": {
        kv: {"cv": cv(7, 3, 0, 10, (0.0, 0.0), (0.4, 0.9)), "suggestion": {"threshold": 0.2}},
        ch: {"cv": cv(8, 2, 2, 8, (0.0, 0.4), (0.6, 1.0)), "suggestion": {"threshold": 0.65}},
        r1: {"cv": cv(9, 1, 2, 8, (0.0, 0.4), (0.7, 1.0))},
    }}))
    (exp / kv).mkdir()
    rows = [{"expected": "review", "predicted": "review"}, {"expected": "review", "predicted": "no_alert"},
            {"expected": "alarm", "predicted": "alarm"}]
    (exp / kv / "rows.json").write_text(json.dumps({"cv": rows}))
    return tmp / "runs"


def test_metrics_from_experiment_and_consequence_text(tmp_path: Path):
    spec = md.load_spec()
    runs = _summary(tmp_path)
    m = md.load_metrics(spec, runs)
    kev = m["zurueckhaltend"]
    assert kev.far.value == 0.0 and kev.far.method == "wilson"  # bootstrap CI collapsed at 0/10
    assert kev.far.hi == pytest.approx(md.wilson(0, 10)[1], abs=1e-4) and kev.far.hi > 0.2
    assert (kev.recall.lo, kev.recall.hi, kev.recall.method) == (0.4, 0.9, "bootstrap")
    assert (kev.review_k, kev.review_n, kev.n_alarm, kev.n_review) == (1, 2, 1, 1)
    assert kev.suggested_threshold == 0.2
    text = md.consequence(kev)
    assert "~0 % Fehlalarme (0 von 10 harmlosen" in text and "aber 3 von 10 auffälligen Fällen verpasst (3 von 10)" in text
    assert md.consequence_short(kev).startswith("Testdaten: ~0 % Fehlalarme, aber 3 von 10 Fällen verpasst")
    assert "n = 20, Unsicherheit gross" in md.uncertainty_note(kev)
    assert ", aber " not in md.consequence(m["ausgewogen"])  # 20 % false alarms: no "but"
    assert md.mode_threshold(spec.get("zurueckhaltend"), kev, 0.55) == 0.2
    assert md.mode_threshold(spec.get("ausgewogen"), m["ausgewogen"], 0.55) == 0.55


def test_wilson_interval():
    lo, hi = md.wilson(0, 22)
    assert lo == 0.0 and hi == pytest.approx(0.1487, abs=1e-3)
    lo, hi = md.wilson(11, 22)
    assert lo < 0.5 < hi and hi - 0.5 == pytest.approx(0.5 - lo)


# --------------------------------------------------------------------------------------------
# re-deciding under a mode
# --------------------------------------------------------------------------------------------


@pytest.fixture
def engine(env: FixtureEnv):
    cfg = load_config(env.config, env.sets)
    return be.Engine(cfg, use_cache=False)


def _calls(env: FixtureEnv) -> dict[str, CallResult]:
    return {cid: _with_b(CallResult.model_validate_json(env.result_path(cid).read_text()), s)
            for cid, s in B_SCORE.items()}


def test_mode_switching_redecides_from_stored_results(env: FixtureEnv, engine, spec_file: Path):
    spec = md.load_spec()
    calls = _calls(env)
    assert md.engine_for(engine, spec, "ausgewogen", second_present=False) is engine  # no Kev: the profile itself
    a_eng = md.engine_for(engine, spec, "ausgewogen")  # Kev present: rule a drops reader B (weighted would count it)
    b_eng = md.engine_for(engine, spec, "zurueckhaltend")
    r1_eng = md.engine_for(engine, spec, "vorsichtig")
    assert isinstance(b_eng, md.ModeEngine) and len({engine.key, a_eng.key, b_eng.key, r1_eng.key}) == 4
    assert b_eng.pipeline is engine.pipeline  # pages that re-run checks keep the profile's pipeline
    changed = 0
    for cid, r in calls.items():
        da = engine.decide(r.model_copy(update={"checks": {k: v for k, v in r.checks.items() if k != READERS[1]}}))
        assert a_eng.decide(r).label == da.label
        # reader B alone = the weighted fusion with B's opinion in reader A's place
        as_b = {k: v for k, v in r.checks.items() if k not in READERS}
        as_b[READERS[0]] = r.checks[READERS[1]]
        db = engine.decide(r.model_copy(update={"checks": as_b}))
        assert b_eng.decide(r).label == db.label
        # R1: agreement decides, disagreement -> review
        d1 = r1_eng.decide(r)
        assert d1.label == ag.label_agreement(da.label, db.label)
        assert d1.reasons[0].startswith("Zwei Leser: Qwen")
        changed += da.label != db.label
    assert changed >= 1  # the fixtures really disagree somewhere
    assert r1_eng.decide(calls[ALARM_ID]).label == "review"  # A: alarm, B: nothing -> a human listens


def test_call_without_second_reader_falls_back_to_default(env: FixtureEnv, engine, spec_file: Path):
    spec = md.load_spec()
    r = CallResult.model_validate_json(env.result_path(ALARM_ID).read_text())  # no reader B
    d = md.engine_for(engine, spec, "vorsichtig").decide(r)
    assert d.label == engine.decide(r).label
    assert "keine Kev-Ergebnisse für diesen Anruf" in d.reasons[0] and "«Ausgewogen»" in d.reasons[0]


def test_availability_disables_modes_without_second_reader(env: FixtureEnv, spec_file: Path):
    spec = md.load_spec()
    cfg = load_config(env.config, env.sets)
    plain = {cid: CallResult.model_validate_json(env.result_path(cid).read_text()) for cid in B_SCORE}
    av = md.availability(spec, cfg, plain)
    assert av["ausgewogen"].ok and not av["zurueckhaltend"].ok and not av["vorsichtig"].ok
    assert "Kev-Dienst nicht aktiv" in av["vorsichtig"].reason and "keiner der 3 Anrufe" in av["vorsichtig"].reason
    some = {**plain, ALARM_ID: _with_b(plain[ALARM_ID], 0.1)}
    av = md.availability(spec, cfg, some)
    assert av["vorsichtig"].ok and "2 von 3 Anrufen ohne Kev-Ergebnis" in av["vorsichtig"].reason
    assert not md.availability(spec, cfg, some, can_decide=False)["vorsichtig"].ok
    other = cfg.model_copy(update={"fusion": {"type": "calibrated"}})
    assert "kennt keine Zweitmeinung" in md.availability(spec, other, some)["vorsichtig"].reason
    assert not md.availability(spec, cfg, {})["vorsichtig"].ok


def test_choice_persists_per_profile(tmp_path: Path):
    assert md.load_choice(tmp_path, "profile:a") is None
    md.save_choice(tmp_path, "profile:a", "vorsichtig", user="officer")
    md.save_choice(tmp_path, "profile:b", "zurueckhaltend", user="officer")
    assert md.load_choice(tmp_path, "profile:a") == "vorsichtig"
    assert md.load_choice(tmp_path, "profile:b") == "zurueckhaltend"
    (tmp_path / md.PREFS_FILE).write_text("{kaputt")
    assert md.load_choice(tmp_path, "profile:a") is None


# --------------------------------------------------------------------------------------------
# workload arithmetic
# --------------------------------------------------------------------------------------------


def _mm(far=(0.1, 0.0, 0.3), rec=(0.8, 0.6, 1.0)) -> md.ModeMetrics:
    return md.ModeMetrics(variant="x", n_calls=48, far=md.Rate(*far, k=2, n=20), recall=md.Rate(*rec, k=8, n=10))


def test_workload_arithmetic_and_ranges():
    w = wl.workload(_mm(), calls=2000, prevalence=0.01, minutes=6, workdays=21, hours=8)
    assert w.reviews.value == pytest.approx(2000 * (0.01 * 0.8 + 0.99 * 0.1))  # 214
    assert w.reviews.lo == pytest.approx(2000 * (0.01 * 0.6 + 0.99 * 0.0))  # 12
    assert w.reviews.hi == pytest.approx(2000 * (0.01 * 1.0 + 0.99 * 0.3))  # 614
    assert w.true_cases.value == pytest.approx(16) and (w.true_cases.lo, w.true_cases.hi) == pytest.approx((12, 20))
    assert w.false_alarms.value == pytest.approx(198)
    assert w.missed_month.value == pytest.approx(2000 * 0.01 * 0.2 * 21)  # 84
    assert (w.missed_month.lo, w.missed_month.hi) == pytest.approx((0.0, 2000 * 0.01 * 0.4 * 21))
    assert w.person_days.value == pytest.approx(214 * 6 / 60 / 8)
    assert w.reviews.lo <= w.reviews.value <= w.reviews.hi
    with pytest.raises(ValueError):
        wl.workload(_mm(), calls=10, prevalence=1.5, minutes=6)


def test_workload_matches_brief_example_and_sentence():
    m = _mm(far=(0.1364, 0.0, 0.3502), rec=(0.8462, 0.6364, 1.0))
    w = wl.workload(m, calls=2000, prevalence=0.01, minutes=6, mode="ausgewogen", label="Ausgewogen")
    assert round(w.reviews.value) == 287 and round(w.true_cases.value) == 17
    s = wl.sentence(w, 0.01)
    assert s.startswith("Bei 1 % Anteil bedeutet «Ausgewogen» etwa **290 Prüfungen pro Tag**")
    assert "davon ~17 echte Fälle" in s
    assert [wl.approx(x) for x in (0.0, 0.34, 2.0, 16.9, 287.0, 12345.0)] == ["0", "0.3", "2", "17", "290", "12'340"]


# --------------------------------------------------------------------------------------------
# AppTest: sidebar + panel
# --------------------------------------------------------------------------------------------


def run_app() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=90)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _sidebar_text(at: AppTest) -> str:
    return "\n".join(c.value for c in at.sidebar.caption)


def test_app_without_second_reader_shows_modes_disabled_and_panel(env: FixtureEnv, spec_file: Path):
    at = run_app()
    radio = at.radio(key="cg_mode")
    assert radio.value == "ausgewogen" and radio.options == ["Ausgewogen"]
    side = _sidebar_text(at)
    assert "**Zurückhaltend**: nicht verfügbar" in side and "Kev-Dienst nicht aktiv" in side
    assert "n = 48, Unsicherheit gross" in side
    md_text = "\n".join(m.value for m in at.markdown)
    assert "Prüfungen pro Tag" in md_text and "echte Fälle" in md_text
    assert any("synthetischen Dev-Anrufen" in c.value for c in at.caption)
    table = next(df.value for df in at.dataframe if "Prüfmodus" in df.value.columns)
    assert len(table) == 3 and "hier nicht verfügbar" in table["Prüfmodus"].iloc[0]
    at.slider(key="cg_wl_share").set_value(5.0).run()
    assert not at.exception
    assert any("Bei 5 % Anteil" in m.value for m in at.markdown)


def test_app_mode_switch_redecides_persists_and_audits(env: FixtureEnv, spec_file: Path):
    add_reader_b(env)
    at = run_app()
    radio = at.radio(key="cg_mode")
    assert radio.options == ["Zurückhaltend", "Ausgewogen", "Vorsichtig"] and radio.value == "ausgewogen"
    before = {m.label: m.value for m in at.metric}
    at.radio(key="cg_mode").set_value("vorsichtig").run()
    assert not at.exception
    after = {m.label: m.value for m in at.metric}
    assert after != before and int(after["Prüfen"]) >= int(before["Prüfen"])
    assert "Prüfmodus **Vorsichtig**" in "\n".join(c.value for c in at.caption)
    # persisted per profile + audit-logged like a tuning change
    assert md.load_choice(env.runs_dir.parent, "profile:local") == "vorsichtig"
    ev = audit.read_events(env.runs_dir, kind="mode_change")
    assert ev and ev[-1]["before"] == "ausgewogen" and ev[-1]["after"] == "vorsichtig"
    assert "Testdaten" in ev[-1]["consequences"]
    # «Zurückhaltend» starts from its own suggested threshold (from the measurements, not hardcoded)
    at.radio(key="cg_mode").set_value("zurueckhaltend").run()
    sug = md.load_metrics(md.load_spec(), None)["zurueckhaltend"].suggested_threshold
    assert at.slider(key="cg_threshold").value == pytest.approx(sug)
    # a new session starts in the saved mode
    at2 = run_app()
    assert at2.radio(key="cg_mode").value == "zurueckhaltend"


def test_app_partial_second_reader_notes_fallback(env: FixtureEnv, spec_file: Path):
    add_reader_b(env, skip=(REVIEW_ID,))
    md.save_choice(env.runs_dir.parent, "profile:local", "vorsichtig")
    at = run_app()
    assert at.radio(key="cg_mode").value == "vorsichtig"
    assert "1 von 3 Anrufen ohne Kev-Ergebnis" in _sidebar_text(at)
