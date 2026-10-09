"""Compliance officer UI: backend logic, metrics and every page rendered with Streamlit's AppTest.

Offline and fast: results are hand-built fixtures (tests/ui_fixtures.py), the LLM is the fake one, no
ASR model is loaded (the "process a call" flow uses the reference backend on a fixture script).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, REVIEW_ID, UNPROCESSED_ID, FixtureEnv, write_fixture_env

from callguard.config import load_config
from callguard.families import load_families
from callguard.types import Decision
from callguard.ui import backend as be
from callguard.ui import metrics_view as mv

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
PAGES = ["inbox", "detail", "keywords", "process", "quality", "experiments"]


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    return e


def engine_for(env: FixtureEnv, *extra: str) -> be.Engine:
    return be.Engine(load_config(env.config, [*env.sets, *extra]))


def ui_overrides(engine: be.Engine, threshold: float) -> dict:
    d = be.fusion_defaults(engine.cfg)
    return {"threshold": threshold, "review_band": d["review_band"], "max_uncertainty": d["max_uncertainty"],
            "weights": be.check_weights(engine.cfg)}


def run_app(page: str | None = None, query: dict[str, str] | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=90)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    at.run()
    if page and page != "inbox":
        at.switch_page(f"views/{page}.py").run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def metrics(at: AppTest) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


def texts(at: AppTest) -> str:
    parts = [x.value for x in [*at.markdown, *at.caption, *at.warning, *at.info, *at.error, *at.success]]
    return "\n".join(str(p) for p in parts)


# --------------------------------------------------------------------------------------------
# launch arguments
# --------------------------------------------------------------------------------------------


def test_parse_args_env_wins_over_argv_and_defaults_to_local():
    assert be.parse_args([], environ={}) == be.UIArgs("local", (), False)
    a = be.parse_args(["--config", "gpu", "--set", "fusion.threshold=0.4"], environ={})
    assert a.config == "gpu" and a.sets == ("fusion.threshold=0.4",)
    env = {be.ENV_ARGS: "-c oracle --set 'llms.default={type: fake}' --no-cache"}
    a = be.parse_args(["-c", "pytest.ini"], environ=env)  # pytest's own -c must not leak in
    assert a == be.UIArgs("oracle", ("llms.default={type: fake}",), True)
    assert be.parse_args(["--config"], environ={"CALLGUARD_CONFIG": "gpu"}).config == "gpu"  # broken -> default
    assert be.parse_args(["--weird", "x"], environ={}).config == "local"


@pytest.mark.parametrize("raw,expected", [("83", 83.0), ("83.5", 83.5), ("01:23", 83.0), (["7", "12"], 12.0),
                                          ("-4", 0.0), ("abc", None), (None, None), ("nan", None)])
def test_parse_seconds(raw, expected):
    assert be.parse_seconds(raw) == expected


# --------------------------------------------------------------------------------------------
# results and live re-decision
# --------------------------------------------------------------------------------------------


def test_load_results_parses_once_and_reports_broken_files(env: FixtureEnv):
    (env.runs_dir / "broken").mkdir()
    (env.runs_dir / "broken" / "result.json").write_text("{not json")
    (env.runs_dir / "uploads").mkdir()  # no result.json: ignored
    loaded = be.load_results(env.runs_dir)
    assert set(loaded.results) == {ALARM_ID, HARMLESS_ID, REVIEW_ID}
    assert len(loaded.errors) == 1 and loaded.errors[0].startswith("broken")
    again = be.load_results(env.runs_dir)
    assert again.results[ALARM_ID] is loaded.results[ALARM_ID] and again.signature == loaded.signature
    be.write_result(loaded.paths[HARMLESS_ID], loaded.results[HARMLESS_ID].model_copy(update={"timings": {"x": 1.0}}))
    assert be.load_results(env.runs_dir).signature != loaded.signature
    assert be.load_results(env.root / "missing").results == {}


def test_redecide_falls_back_to_stored_decision():
    from ui_fixtures import alarm_call

    r = alarm_call(None)
    d = be.redecide(None, r, {"threshold": 0.1}, None)
    assert not d.live and d.decision is r.decision and d.error

    class Broken:
        can_decide, error = True, None

        def decide(self, *a, **k) -> Decision:
            raise ValueError("fusion exploded")

    d = be.redecide(Broken(), r, None, None)  # type: ignore[arg-type]
    assert not d.live and d.decision.label == "alarm" and "fusion exploded" in d.error


def test_threshold_moves_labels_without_touching_asr_or_llm(env: FixtureEnv):
    engine = engine_for(env)
    assert engine.pipeline is not None and engine.error is None
    loaded = be.load_results(env.runs_dir)
    fams = engine.families()
    low = be.label_counts(be.decide_all(engine, loaded, ui_overrides(engine, 0.05), fams))
    default = be.label_counts(be.decide_all(engine, loaded, ui_overrides(engine, 0.55), fams))
    high = be.label_counts(be.decide_all(engine, loaded, ui_overrides(engine, 0.95), fams))
    assert default == {"alarm": 1, "review": 1, "no_alert": 1}
    assert low["no_alert"] < default["no_alert"] and high["alarm"] < default["alarm"]
    assert engine.pipeline._asr is None and engine.pipeline._diarizer is None  # never built
    decided = be.decide_all(engine, loaded, ui_overrides(engine, 0.55), fams)
    assert all(d.live for d in decided.values())
    # stored snippet survives re-deciding
    assert decided[ALARM_ID].decision.passages[0].snippet_path


def test_family_toggle_removes_family_from_decision(env: FixtureEnv):
    engine = engine_for(env)
    loaded = be.load_results(env.runs_dir)
    no_trade = [f for f in engine.families() if f.id != "trade"]
    d = be.decide_all(engine, loaded, ui_overrides(engine, 0.55), no_trade)[ALARM_ID].decision
    assert "trade" not in d.families and d.label != "alarm"


def test_inbox_rows_sorted_and_explained(env: FixtureEnv):
    engine = engine_for(env)
    loaded = be.load_results(env.runs_dir)
    fams = engine.families()
    decided = be.decide_all(engine, loaded, ui_overrides(engine, 0.55), fams)
    baseline = be.decide_all(engine, loaded, ui_overrides(engine, 0.45), fams)
    rows = be.inbox_rows(loaded, decided, fams, baseline, be.check_weights(engine.cfg))
    assert [r["call_id"] for r in rows] == [ALARM_ID, REVIEW_ID, HARMLESS_ID]
    assert rows[0]["family"] == "Insiderhandel" and rows[0]["passages"] >= 1
    harmless = rows[2]["reason"]
    assert harmless.startswith("Insiderhandel:") and "veröffentlichten Quartalszahlen" in harmless  # not "G-Eval"
    assert rows[1]["changed"] == "Alarm → Prüfen"  # review case was an alarm at threshold 0.45


def test_checks_said_and_linked_passage(env: FixtureEnv):
    r = be.load_results(env.runs_dir).results[ALARM_ID]
    said = be.checks_said(r, r.decision, {"llm_judge": 1.0})
    trade = [x for x in said if x["family"] == "Insiderhandel"]
    assert {x["check"] for x in trade} == {"keywords", "llm_judge", "geval"}
    assert next(x for x in trade if x["check"] == "llm_judge")["verdict"] == "present"
    ps = r.decision.passages  # 58.5-68.0 and 24.5-50.0
    assert be.linked_passage(ps, 48.0, 10.0) == 0
    assert be.linked_passage(ps, 14.5, 10.0) == 1
    assert be.linked_passage(ps, None) is None and be.linked_passage(ps, 300.0) is None


# --------------------------------------------------------------------------------------------
# audio
# --------------------------------------------------------------------------------------------


def test_passage_clip_prefers_snippet_then_cuts_then_gives_up(env: FixtureEnv):
    loaded = be.load_results(env.runs_dir)
    r = loaded.results[ALARM_ID]
    first, second = r.decision.passages
    clip = be.passage_clip(r, first, loaded.paths[ALARM_ID].parent)
    assert clip and clip.path == first.snippet_path
    clip = be.passage_clip(r, second, loaded.paths[ALARM_ID].parent, pad=1.0)
    assert clip and Path(clip.path).is_file() and "ui_trade" in clip.path
    import soundfile as sf

    assert sf.info(clip.path).duration == pytest.approx(second.end - second.start + 2.0, abs=0.05)
    gone = r.model_copy(update={"audio_path": str(env.root / "nope.wav")})
    assert be.passage_clip(gone, second.model_copy(update={"snippet_path": None}), env.root) is None


# --------------------------------------------------------------------------------------------
# keyword list and criteria
# --------------------------------------------------------------------------------------------


def test_rows_to_keywords_assigns_ids_and_drops_empty_rows():
    rows = [
        {"enabled": True, "id": "K01", "label": "Alt", "de": "nicht öffentlich, noch nicht publiziert",
         "gsw": "nöd öffentlich", "harmless": "", "case_sensitive": False},
        {"enabled": None, "id": None, "label": None, "de": "Insidertipp; Geheimtipp", "gsw": math.nan,
         "harmless": "Nur zitiert.", "case_sensitive": math.nan},
        {"enabled": True, "id": "", "label": "", "de": "", "gsw": "", "harmless": "", "case_sensitive": False},
        {"enabled": False, "id": "K03", "label": "Leer", "de": " , ", "gsw": None, "harmless": None},
        {"enabled": True, "id": "K01", "label": "Dup", "de": "x", "gsw": "", "harmless": ""},
    ]
    kws, warnings = be.rows_to_keywords(rows, {"K01", "K11"})
    assert [k.id for k in kws] == ["K01", "K12"]
    assert kws[0].de == ["nicht öffentlich", "noch nicht publiziert"] and kws[0].harmless is None
    new = kws[1]
    assert new.label == "Insidertipp" and new.de == ["Insidertipp", "Geheimtipp"] and new.gsw == []
    assert new.enabled is True and new.case_sensitive is False and new.harmless == "Nur zitiert."
    assert len(warnings) == 2 and "K03" in warnings[0] and "twice" in warnings[1]


def test_save_family_keywords_keeps_other_families(env: FixtureEnv):
    before = {f.id: f for f in load_families(env.keywords, env.criteria)}
    rows = be.keyword_rows(before["trade"])
    next(r for r in rows if r["id"] == "K03")["enabled"] = False
    rows.append({"de": "Insidertipp", "gsw": "Insidertipp"})  # a new row as the data editor returns it
    kws, warnings = be.rows_to_keywords(rows, be.all_keyword_ids(env.keywords))
    assert not warnings
    be.save_family_keywords(env.keywords, env.criteria, "trade", kws)
    after = {f.id: f for f in load_families(env.keywords, env.criteria)}
    trade = {k.id: k for k in after["trade"].keywords}
    assert not trade["K03"].enabled and trade["K12"].de == ["Insidertipp"]
    for fid in before:
        if fid != "trade":
            assert after[fid].keywords == before[fid].keywords
    raw = json.loads(env.keywords.read_text())
    assert raw["status"] == "provisional_not_official"  # untouched top-level fields survive


def test_save_criteria_keeps_header_and_other_families(env: FixtureEnv):
    old = yaml.safe_load(env.criteria.read_text())["families"]
    be.save_criteria(env.criteria, "access", {"policy": "  Neue Regel.  ", "alarm_when": "eins\n\n zwei \n",
                                              "enabled": False, "label": "Zugang  (neu)"})
    text = env.criteria.read_text()
    assert text.startswith("# What each check family means")
    fams = yaml.safe_load(text)["families"]
    assert fams["access"]["policy"] == "Neue Regel." and fams["access"]["alarm_when"] == ["eins", "zwei"]
    assert fams["access"]["enabled"] is False and fams["access"]["label"] == "Zugang (neu)"
    assert fams["access"]["not_alarm_when"] == old["access"]["not_alarm_when"]
    assert fams["trade"] == old["trade"] and fams["numbers"]["can_alarm"] is False
    disabled = [f for f in load_families(env.keywords, env.criteria) if f.id == "access"][0]
    assert disabled.enabled is False and "Zugang (neu)" == disabled.label


def test_backup_file(tmp_path: Path):
    src = tmp_path / "keywords.json"
    assert be.backup_file(src, tmp_path / "b") is None
    src.write_text("{}")
    out = be.backup_file(src, tmp_path / "b")
    assert out and out.read_text() == "{}" and out.suffix == ".json"


def test_rerun_checks_after_keyword_edit(env: FixtureEnv):
    engine = engine_for(env)
    loaded = be.load_results(env.runs_dir)
    fams = load_families(env.keywords, env.criteria)
    trade = next(f for f in fams if f.id == "trade")
    be.save_family_keywords(env.keywords, env.criteria, "trade",
                            [k.model_copy(update={"enabled": False}) for k in trade.keywords])
    seen: list[str] = []
    report = be.rerun_checks(engine.pipeline, loaded, progress=lambda i, n, cid: seen.append(cid))
    assert report.calls == 3 and not report.failed and seen[-1] == ""
    assert report.kept == 6  # llm_judge + geval per call: criteria cache empty, kept as stored
    after = be.load_results(env.runs_dir)
    kw = after.results[HARMLESS_ID].checks["keywords"]
    assert not [f for f in kw.findings if f.family == "trade"]  # trade keywords are off now
    assert after.results[HARMLESS_ID].checks["llm_judge"].meta.get("stale")
    assert after.results[ALARM_ID].checks["llm_judge"].family_scores["trade"].score == 0.92


def test_process_call_offline_with_reference_asr(env: FixtureEnv):
    engine = engine_for(env, "asr={type: reference}", "diarizer={type: none}")
    msgs: list[str] = []
    audio = env.data_dir / "Audio" / f"{UNPROCESSED_ID}.wav"
    r = be.process_call(engine.pipeline, audio, UNPROCESSED_ID, notify=msgs.append)
    assert r.transcript.segments and r.decision.label in ("alarm", "review", "no_alert")
    assert env.result_path(UNPROCESSED_ID).is_file()
    assert msgs[0].startswith("Spracherkennung") and any("Prüfung 'keywords'" in m for m in msgs)
    assert msgs[-1] == "Ergebnis speichern"


def test_upload_helpers(tmp_path: Path):
    assert be.safe_call_id("Anruf 12 (Kunde).WAV") == "Anruf_12_Kunde"
    assert be.safe_call_id("../..") == "upload"
    p = be.save_upload(tmp_path, "my call.wav", b"RIFF")
    assert p == tmp_path / "uploads" / "my_call.wav" and p.read_bytes() == b"RIFF"
    with pytest.raises(ValueError):
        be.save_upload(tmp_path, "notes.txt", b"x")
    assert be.estimate_seconds(load_config("local"), 240) > 240  # CPU: realtime ASR + LLM checks
    assert be.default_thresholds()[0] == 0.05 and be.default_thresholds()[-1] == 0.95


# --------------------------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------------------------


def test_flag_metrics_counts_review_as_flagged():
    pairs = [("alarm", "alarm"), ("alarm", "review"), ("review", "no_alert"), ("no_alert", "alarm"),
             ("no_alert", "no_alert"), ("no_alert", "no_alert")]
    m = mv.flag_metrics(pairs)
    assert (m.tp, m.fp, m.fn, m.tn) == (2, 1, 1, 2)
    assert m.precision == pytest.approx(2 / 3) and m.recall == pytest.approx(2 / 3)
    assert m.f1 == pytest.approx(2 / 3) and m.false_alarm_rate == pytest.approx(1 / 3)
    assert m.miss_rate == pytest.approx(1 / 3) and m.accuracy == pytest.approx(3 / 6)
    empty = mv.flag_metrics([("no_alert", "no_alert")])
    assert empty.precision is None and empty.recall is None and empty.f1 is None and empty.false_alarm_rate == 0
    assert mv.flag_metrics([("alarm", "no_alert")]).f1 == 0.0


def test_confusion_matrix_and_charts_build():
    pairs = [("alarm", "alarm"), ("review", "alarm"), ("no_alert", "review")]
    cm = mv.confusion(pairs)
    assert list(cm.index) == ["Alarm", "Prüfen", "Kein Alarm"] and cm.loc["Prüfen", "Alarm"] == 1
    assert int(cm.values.sum()) == 3
    mv.confusion_chart(cm).to_dict()
    rows = mv.sweep({0.3: {"a": "alarm", "b": "review"}, 0.6: {"a": "alarm", "b": "no_alert"}},
                    {"a": "alarm", "b": "no_alert"})
    mv.sweep_chart(rows, 0.3, 0.6).to_dict()
    mv.sweep_chart(rows, 0.6, 0.6).to_dict()
    mv.sweep_chart(rows, 0.6, 0.3, [{"value": 0.5, "what": "Holdout-F1"}]).to_dict()


def test_suggest_threshold_prefers_f1_then_fewer_false_alarms_and_skips_flag_everything():
    rows = [
        {"threshold": 0.1, "f1": 0.8, "false_alarm_rate": 1.0},  # flags everything
        {"threshold": 0.4, "f1": 0.7, "false_alarm_rate": 0.3},
        {"threshold": 0.5, "f1": 0.7, "false_alarm_rate": 0.1},
        {"threshold": 0.6, "f1": 0.7, "false_alarm_rate": 0.1},
        {"threshold": 0.9, "f1": None, "false_alarm_rate": 0.0},
    ]
    assert mv.suggest_threshold(rows, current=0.62) == 0.6
    assert mv.suggest_threshold(rows, current=0.45) == 0.5
    assert mv.suggest_threshold(rows[:1]) == 0.1  # nothing better: still say something
    assert mv.suggest_threshold([{"threshold": 0.5, "f1": None}]) is None


# --------------------------------------------------------------------------------------------
# rendering helpers
# --------------------------------------------------------------------------------------------


def test_transcript_markdown_escapes_and_highlights(env: FixtureEnv):
    from callguard.ui import render

    r = be.load_results(env.runs_dir).results[ALARM_ID]
    md = render.transcript_markdown(r.transcript, r.decision.passages, r)
    assert ":orange-background[" in md and ":blue-badge[Insiderhandel]" in md
    assert "**noch nicht publiziert**" in md and "**Beratung**" in md
    assert render.esc("$5 [a]* :x:") == r"\$5 \[a\]\* \:x\:"
    assert render._bold_terms("Die Quartalszahlen, quartalszahlen.", ["Quartalszahlen"]).count("**") == 4


# --------------------------------------------------------------------------------------------
# pages (Streamlit AppTest)
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("page", PAGES)
def test_every_page_renders(env: FixtureEnv, page: str):
    at = run_app(page)
    assert at.title, f"{page} has no title"


def test_inbox_counts_follow_the_threshold_slider(env: FixtureEnv):
    at = run_app()
    assert metrics(at) == {"Alarm": "1", "Prüfen": "1", "Kein Alarm": "1", "Mensch nötig": "2"}
    assert all(m.delta in (None, "") for m in at.metric)
    engine = engine_for(env)
    loaded = be.load_results(env.runs_dir)
    for t in (0.45, 0.05, 0.95):
        at.slider(key="cg_threshold").set_value(t).run()
        assert not at.exception
        want = be.label_counts(be.decide_all(engine, loaded, ui_overrides(engine, t), engine.families()))
        shown = metrics(at)
        assert {k: shown[be.LABEL_TEXT[k]] for k in want} == {k: str(v) for k, v in want.items()}
        assert any(m.delta and "zum Profil" in m.delta for m in at.metric)
    reset = next(b for b in at.sidebar.button if b.label == "Zurücksetzen")
    reset.click().run()
    assert at.slider(key="cg_threshold").value == pytest.approx(0.55)
    assert metrics(at)["Alarm"] == "1"


def test_check_weight_zero_and_family_toggle_change_decisions(env: FixtureEnv):
    at = run_app()
    at.toggle(key="cg_fam_trade").set_value(False).run()
    assert metrics(at)["Alarm"] == "0"
    at.toggle(key="cg_fam_trade").set_value(True).run()
    for name in ("llm_judge", "geval"):
        at.slider(key=f"cg_w_{name}").set_value(0.0)
    at.run()
    assert not at.exception  # keywords + patterns alone still decide


def test_deep_link_opens_call_at_passage(env: FixtureEnv):
    at = run_app(query={"call": ALARM_ID, "t": "48"})
    assert at.title[0].value.startswith(ALARM_ID)
    body = texts(at)
    assert "aus dem Alarm-Link" in body and "Geöffnet über einen Alarm-Link bei 00:48" in body
    assert "Verdächtige Passagen (2)" in [h.value for h in at.subheader]
    assert len(at.get("audio")) >= 3  # two snippets + full call
    assert "Beweis-Zeitachse" in [h.value for h in at.subheader]
    assert "Kriterium" in body and "llm\\_judge 0.92" in body  # matched criterion + supporting check score


def test_review_call_hands_over_to_a_human(env: FixtureEnv):
    at = run_app("detail", query={"call": REVIEW_ID})
    assert any("Unsicher → an Menschen übergeben" in w.value for w in at.warning)


def test_unknown_call_falls_back_with_warning(env: FixtureEnv):
    at = run_app("detail", query={"call": "Stufe9_X99-K1"})
    assert any("Stufe9_X99-K1" in w.value for w in at.warning)
    assert at.title[0].value.startswith(ALARM_ID)  # riskiest call instead


def test_detail_next_button_walks_calls_by_score(env: FixtureEnv):
    at = run_app("detail", query={"call": ALARM_ID})
    next(b for b in at.button if b.label == "Weiter").click().run()
    assert at.title[0].value.startswith(REVIEW_ID)
    assert at.selectbox(key="cg_detail_pick").value == REVIEW_ID and at.query_params["call"] == REVIEW_ID
    at.selectbox(key="cg_detail_pick").set_value(HARMLESS_ID).run()
    assert at.title[0].value.startswith(HARMLESS_ID) and not at.warning


def test_empty_runs_dir_shows_guidance(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env = write_fixture_env(tmp_path)
    for p in env.runs_dir.glob("*/result.json"):
        p.unlink()
    monkeypatch.setenv(be.ENV_ARGS, env.args)
    for page in PAGES:
        at = run_app(page)
        assert at.title


def test_fallback_when_fusion_cannot_be_built(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(be.ENV_ARGS, env.args + " --set fusion.type=no_such_fusion")
    at = run_app()
    assert any("Notbetrieb" in w.value for w in at.sidebar.warning)
    assert any("gespeicherten Entscheid" in w.value for w in at.warning)
    assert metrics(at)["Alarm"] == "1"
    at.slider(key="cg_threshold").set_value(0.1).run()
    assert not at.exception and metrics(at)["Alarm"] == "1"  # stored decisions don't move
    for page in PAGES[1:]:
        at.switch_page(f"views/{page}.py").run()
        assert not at.exception, page


def test_broken_check_plugin_still_redecides_with_fusion_only(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(be.ENV_ARGS, env.args + " --set checks.0.type=no_such_check")
    at = run_app()
    assert any("Notbetrieb" in w.value for w in at.sidebar.warning)
    at.slider(key="cg_threshold").set_value(0.05).run()
    assert metrics(at)["Kein Alarm"] == "0"


def test_unknown_config_is_reported(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(be.ENV_ARGS, "--config does_not_exist")
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    assert not at.exception and "konnte nicht geladen werden" in at.error[0].value


def test_keywords_page_save_and_rerun_cheap_checks(env: FixtureEnv):
    at = run_app("keywords")
    before = env.keywords.read_text()
    next(b for b in at.button if b.label == "Stichwörter speichern").click().run()
    assert not at.exception
    old, new = json.loads(before), json.loads(env.keywords.read_text())  # unchanged table -> same content

    def by_id(raw: dict) -> dict:  # save_keywords writes the case_sensitive default explicitly
        return {k["id"]: {"case_sensitive": False, **k} for k in raw["keywords"]}

    assert by_id(new) == by_id(old)
    assert new["families"] == old["families"]
    assert list((env.runs_dir / "_backups").glob("keywords.*.json"))
    next(b for b in at.button if b.label == "Stichwörter jetzt auf alle Anrufe anwenden").click().run()
    assert not at.exception
    shown = metrics(at)
    assert {"Alarm", "Prüfen", "Kein Alarm", "Stichwort-Treffer"} <= set(shown)
    assert at.session_state["cg_kw_report"]["report"]["calls"] == 3


def test_criteria_form_saves_yaml(env: FixtureEnv):
    at = run_app("keywords")
    policy = next(t for t in at.text_area if t.label.startswith("Richtlinie"))  # first tab: trade
    policy.set_value("Neue Richtlinie für Insiderhandel.")
    next(b for b in at.button if b.label == "Kriterien speichern").click().run()
    assert not at.exception
    fams = yaml.safe_load(env.criteria.read_text())["families"]
    assert fams["trade"]["policy"] == "Neue Richtlinie für Insiderhandel."
    assert env.criteria.read_text().startswith("#")


def test_try_a_sentence_against_keywords(env: FixtureEnv):
    at = run_app("keywords")
    at.text_input(key="cg_kw_try").set_value("Ich will vor der Meldung kaufen, die Quartalszahlen sind gut.").run()
    assert not at.exception
    assert at.dataframe and "trade" in at.dataframe[-1].value["Art"].tolist()


def test_quality_view_and_apply_suggested_threshold(env: FixtureEnv):
    at = run_app()
    at.slider(key="cg_threshold").set_value(0.05).run()  # harmless call becomes a false alarm
    at.switch_page("views/quality.py").run()
    assert not at.exception
    assert {"Präzision", "Recall", "F1", "Fehlalarmquote", "Verpasst", "Exakter Status"} <= set(metrics(at))
    assert "95%-KI" in texts(at)
    apply = next(b for b in at.button if b.label == "Vorschlag übernehmen")
    apply.click().run()
    assert not at.exception
    assert at.slider(key="cg_threshold").value > 0.05
    assert metrics(at)["Fehlalarmquote"] == "0%"


def test_process_page_runs_a_dataset_call_offline(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(be.ENV_ARGS, env.args + " --set 'asr={type: reference}' --set 'diarizer={type: none}'")
    at = run_app("process")
    at.multiselect(key="cg_proc_pick").set_value([UNPROCESSED_ID]).run()
    at.button(key="cg_proc_go").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert env.result_path(UNPROCESSED_ID).is_file()
    assert UNPROCESSED_ID in at.session_state["cg_processed"]
    assert any(b.label == "Öffnen" for b in at.button)


@pytest.mark.slow
def test_process_real_audio_excerpt_on_cpu(tmp_path: Path):
    """Real Whisper on a 25 s excerpt of a case recording (CPU, ~1x realtime), fake LLM."""
    pytest.importorskip("faster_whisper")
    from callguard.audio import cut
    from callguard.config import ROOT

    wav = ROOT / "data_upstream/inventx-case-study/data/Audio/Stufe1_D02-K1.wav"
    if not (ROOT / "models/asr/whisper-turbo-gsw-ct2-int8/model.bin").is_file() or not wav.is_file():
        pytest.skip("local Whisper model or case audio not available")
    env = write_fixture_env(tmp_path)
    excerpt = cut(wav, 30.0, 55.0, tmp_path / "excerpt.wav")
    engine = engine_for(env, "diarizer={type: none}")
    msgs: list[str] = []
    r = be.process_call(engine.pipeline, excerpt, "excerpt_D02", notify=msgs.append)
    assert r.transcript.segments and r.transcript.asr_backend
    assert env.result_path("excerpt_D02").is_file()
    assert "excerpt_D02" in be.load_results(env.runs_dir).results


def test_unreadable_keyword_list_shows_stored_decisions(env: FixtureEnv):
    env.keywords.write_text("{broken")
    at = run_app()
    assert any("unlesbar" in e.value for e in at.sidebar.error)
    assert metrics(at)["Alarm"] == "1"  # stored decisions, not "nothing found"
    for page in PAGES[1:]:
        at.switch_page(f"views/{page}.py").run()
        assert not at.exception, page

