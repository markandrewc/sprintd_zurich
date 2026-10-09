"""UI v2 (STATUS item 11): registries, explanations ("Warum Prüfen?", "Warum kein Alarm?", criterion per
passage, evidence timeline), view tabs, the source selector (profile run vs experiment variant), the
Experiments page and the holdout line on the Quality page. Offline, fixture-based, Streamlit AppTest.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import (
    ALARM_ID,
    HARMLESS_ID,
    REVIEW_ID,
    FixtureEnv,
    add_views,
    alarm_call,
    harmless_call,
    review_call,
    write_experiment_fixture,
    write_fixture_env,
    write_holdout_log,
)

from callguard.config import ROOT
from callguard.families import load_families
from callguard.ui import backend as be
from callguard.ui import explain as ex
from callguard.ui import pages_registry as pr
from callguard.ui import panels as pn
from callguard.ui import sources as srcs

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    return e


@pytest.fixture(scope="module")
def families():
    return load_families(ROOT / "config" / "keywords.json", ROOT / "config" / "criteria.yaml")


def run_app(page: str | None = None, query: dict[str, str] | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=90)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    at.run()
    if page and page != "inbox":
        at.switch_page(f"views/{page}.py").run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def texts(at: AppTest) -> str:
    parts = [x.value for x in [*at.markdown, *at.caption, *at.warning, *at.info, *at.error, *at.success]]
    return "\n".join(str(p) for p in parts)


def metrics(at: AppTest) -> dict[str, str]:
    return {m.label: m.value for m in at.metric}


# --------------------------------------------------------------------------------------------
# registries
# --------------------------------------------------------------------------------------------


def test_pages_registry_resolves_every_builtin_page():
    keys = [p.key for p in pr.pages()]
    assert keys[:6] == ["inbox", "detail", "keywords", "process", "quality", "experiments"]
    builtin = {"inbox", "detail", "keywords", "process", "quality", "experiments"}
    assert not [p for p in pr.missing() if p.key in builtin]
    assert sum(p.default for p in pr.PAGES) == 1
    assert all(p.path().is_file() for p in pr.pages())


def test_register_page_replaces_by_key_and_skips_missing_modules(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pr, "PAGES", list(pr.PAGES))
    pr.register_page(pr.PageSpec("audit", "Audit-Log", ":material/history:", "callguard.ui.views.inbox", order=70))
    pr.register_page(pr.PageSpec("ghost", "Geist", ":material/help:", "callguard.no_such_module", order=80))
    keys = [p.key for p in pr.pages()]
    assert "audit" in keys and "ghost" not in keys and [p.key for p in pr.missing()] == ["ghost"]
    pr.register_page(pr.PageSpec("audit", "Audit", ":material/history:", "callguard.ui.views.inbox", order=5))
    assert [p.key for p in pr.pages()][0] == "audit"


def _demo_panel(result, session) -> None:
    import streamlit as st

    st.markdown(f"PANEL-OK {result.call_id} {result.decision.label} {len(session.loaded.results)}")


def _broken_panel(result, session) -> None:
    raise RuntimeError("kaputt")


def test_detail_page_draws_registered_panels_and_isolates_failures(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(pn, "PANELS", [])
    pn.register_panel("demo", "Demo-Panel", _demo_panel, order=10, expanded=True)
    pn.register_panel("broken", "Kaputtes Panel", f"{__name__}:_broken_panel", order=20)
    pn.register_panel("hidden", "Versteckt", _demo_panel, when=lambda r, s: False)

    @pn.register_panel("deco", "Dekoriert", order=30)
    def _deco(result, session) -> None:
        import streamlit as st
        st.caption("DECO-OK")

    assert [p.key for p in pn.panels()] == ["demo", "broken", "deco", "hidden"]
    at = run_app("detail", query={"call": ALARM_ID})
    body = texts(at)
    assert f"PANEL-OK {ALARM_ID} alarm 3" in body and "DECO-OK" in body
    assert any("Kaputtes Panel" in w.value and "kaputt" in w.value for w in at.warning)
    labels = [x.label for x in at.expander]
    assert "Demo-Panel" in labels and "Versteckt" not in labels


# --------------------------------------------------------------------------------------------
# explanations (pure)
# --------------------------------------------------------------------------------------------


def test_review_causes_name_band_and_open_fact_in_german():
    r = review_call(None)
    causes = ex.review_causes(r, r.decision, threshold=0.55, review_band=0.15, max_uncertainty=0.35)
    codes = [c.code for c in causes]
    assert codes[0] == "band" and "undetermined" in codes
    assert "0.47" in causes[0].text and "Prüfbereich" in causes[0].text
    assert not ex.review_causes(alarm_call(None), alarm_call(None).decision, threshold=0.55, review_band=0.15,
                                max_uncertainty=0.35)


def test_review_causes_failed_check_and_uncertainty():
    r = review_call(None)
    r.checks["llm_judge"].meta["error"] = "LLM server down"
    d = r.decision.model_copy(update={"label": "review"})
    d.families["access"].score, d.families["access"].uncertainty = 0.7, 0.6
    causes = ex.review_causes(r, d, threshold=0.55, review_band=0.15, max_uncertainty=0.35)
    codes = {c.code for c in causes}
    assert {"failed", "uncertain"} <= codes
    assert any("LLM server down" in c.text for c in causes)


def test_why_not_alarm_finds_counter_evidence_and_not_alarm_rule(families):
    r = harmless_call(None)
    w = ex.why_not_alarm(r, r.decision, families, threshold=0.55, review_band=0.15,
                         weights={"keywords": 0.35, "llm_judge": 1.0, "geval": 0.5})
    assert w is not None and w.family == "trade"
    assert w.counter is not None and w.counter.check == "llm_judge"
    assert w.rule is not None and w.rule.rule.startswith("Kaufwunsch beruht nur auf bereits veröffentlichten")
    assert w.rule_source == "match" and w.harmless_notes and len(w.hits) == 2
    assert "Quartalszahlen" in w.summary and not w.summary.endswith("..")
    keywords = next(o for o in w.opinions if o.check == "keywords")
    assert keywords.above and keywords.score == 0.7  # the loud check is shown against the threshold
    assert ex.why_not_alarm(alarm_call(None), alarm_call(None).decision, families, threshold=0.55,
                            review_band=0.15) is None


def test_why_not_alarm_prefers_fact_sheet_rule(families):
    r = harmless_call(None)
    r.checks["llm_judge"].family_scores["trade"].detail["rule"] = {"id": "r3", "label": "no_alert",
                                                                   "text": "Information ist öffentlich"}
    w = ex.why_not_alarm(r, r.decision, families, threshold=0.55, review_band=0.15)
    assert w.rule.rule == "Information ist öffentlich" and w.rule_source == "fact"


def test_passage_criterion_matches_alarm_when(families):
    r = alarm_call(None)
    trade = next(f for f in families if f.id == "trade")
    c = ex.passage_criterion(r.decision.passages[0], trade, r)
    assert c.kind == "alarm_when" and "vor der Meldung" in c.text
    blank = r.decision.passages[0].model_copy(update={"reasons": [], "text": "Grüezi"})
    assert ex.passage_criterion(blank, trade).kind == "policy"
    assert ex.passage_criterion(blank, None) is None


def test_timeline_events_place_findings_and_citations():
    r = alarm_call(None)
    ev = ex.timeline_events(r, r.decision)
    assert {e["check"] for e in ev} == {"keywords", "llm_judge", "geval"}  # geval: call-level citation
    assert all(0 <= e["start"] <= e["end"] <= 76 for e in ev)
    assert [e["start"] for e in ev] == sorted(e["start"] for e in ev)
    assert next(e for e in ev if e["check"] == "geval")["kind"] == "Zitat"
    assert ex.call_duration(r) == 76.0


def test_view_titles():
    assert ex.view_title("main") == "Transkript"
    assert ex.view_title("en_from_de") == "Englisch (en_from_de)"
    assert ex.view_title("gsw") == "Schweizerdeutsch"


# --------------------------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------------------------


def test_detail_harmless_call_explains_why_not_alarm(env: FixtureEnv):
    at = run_app("detail", query={"call": HARMLESS_ID})
    assert any(x.label.startswith("Warum kein Alarm?") for x in at.expander)
    body = texts(at)
    assert "Stärkstes Gegenargument" in body and "Kaufwunsch beruht nur auf bereits" in body
    assert "Laut Stichwortliste harmlos" in body


def test_detail_review_call_lists_causes(env: FixtureEnv):
    at = run_app("detail", query={"call": REVIEW_ID})
    w = next(w.value for w in at.warning if "an Menschen übergeben" in w.value)
    assert "Knapp unter der Schwelle" in w and "Sachverhalt offen" in w


def test_detail_shows_view_tabs_and_side_by_side_passage_texts(env: FixtureEnv):
    add_views(env)
    at = run_app("detail", query={"call": ALARM_ID})
    assert [t.label for t in at.tabs][:2] == ["Deutsch (main)", "Englisch (en_from_de)"]
    body = texts(at)
    assert "\\[EN\\]" in body  # the English view's passage text next to the German one
    assert "2 Transkript-Ansichten" in body


def test_timeline_jump_sets_the_recording_position(env: FixtureEnv):
    at = run_app("detail", query={"call": ALARM_ID})
    at.session_state[f"cg_seek_{ALARM_ID}"] = 24.5
    at.run()
    assert not at.exception
    assert any("ab 00:23" in c.value for c in at.caption)


def test_inbox_filters_by_family_and_level_and_sorts(env: FixtureEnv):
    at = run_app()
    at.multiselect(key="cg_inbox_family").set_value(["Insiderhandel"]).run()
    calls = at.dataframe[0].value["Anruf"].tolist()
    assert set(calls) == {ALARM_ID, HARMLESS_ID}
    at.multiselect(key="cg_inbox_family").set_value([]).run()
    at.multiselect(key="cg_inbox_level").set_value(["Stufe 3"]).run()
    assert at.dataframe[0].value["Anruf"].tolist() == [REVIEW_ID]
    at.multiselect(key="cg_inbox_level").set_value([]).run()
    at.selectbox(key="cg_inbox_sort").set_value("Anruf (A–Z)").run()
    calls = at.dataframe[0].value["Anruf"].tolist()
    assert calls == sorted(calls)
    assert metrics(at)["Alarm"] == "1"  # filters never change the counts


def test_experiment_variant_as_source_is_read_only(env: FixtureEnv):
    write_experiment_fixture(env)
    sources = srcs.list_sources(env.runs_dir.parent, "local")
    assert [s.key for s in sources] == ["profile:local", "exp:fx/a", "exp:fx/b"]
    cfg = srcs.source_config(sources[2], env.sets)
    assert be.fusion_defaults(cfg)["threshold"] == pytest.approx(0.3)  # the variant's own config
    loaded = srcs.load_jsonl(sources[1].path)
    assert set(loaded.results) == {ALARM_ID, HARMLESS_ID, REVIEW_ID} and not loaded.errors

    at = run_app(query={"src": "exp:fx/b"})
    assert at.selectbox(key="cg_source").value == "exp:fx/b"
    assert at.slider(key="cg_threshold").value == pytest.approx(0.3)  # knobs start from the variant
    assert "nur lesen" in "\n".join(c.value for c in at.sidebar.caption)
    at.switch_page("views/keywords.py").run()
    assert not at.exception
    assert next(b for b in at.button if b.label == "Stichwörter jetzt auf alle Anrufe anwenden").disabled
    at.switch_page("views/detail.py").run()
    assert not at.exception and at.title[0].value
    at.selectbox(key="cg_source").set_value("profile:local").run()
    assert not at.exception and at.slider(key="cg_threshold").value == pytest.approx(0.55)


def test_experiments_page_shows_variants_comparisons_and_flips(env: FixtureEnv):
    write_experiment_fixture(env)
    at = run_app("experiments")
    assert at.title[0].value == "Experimente"
    frames = [df.value for df in at.dataframe]
    table = next(f for f in frames if "Variante" in f.columns)
    assert table["Variante"].tolist() == ["a", "b"] and "0.80 [0.50, 1.00]" in table.iloc[0].tolist()
    flips = next(f for f in frames if "Markierung" in f.columns)
    assert flips["Anruf"].tolist() == [HARMLESS_ID] and flips["Markierung"].tolist() == ["kaputt gemacht"]
    assert any("McNemar" in c.value for c in at.caption)
    rows = srcs.variant_rows(srcs.load_summaries(env.runs_dir.parent)[0])
    assert rows[0]["variant"] == "a" and rows[0]["lo"] == 0.5


def test_experiments_page_without_experiments(env: FixtureEnv):
    at = run_app("experiments")
    assert any("Noch keine Experimente" in i.value for i in at.info)


def test_quality_page_shows_dev_scope_ci_and_holdout_log(env: FixtureEnv):
    write_holdout_log(env)
    at = run_app("quality")
    body = texts(at)
    assert "Dev-Split" in body and "95%-KI" in body
    assert any("nie zum Tunen" in w.value for w in at.warning)
    hold = next(df.value for df in at.dataframe if "Profil" in df.value.columns)
    assert hold["F1"].tolist() == [0.6]
    assert srcs.read_holdout_log(env.runs_dir.parent / "missing.jsonl") == []
