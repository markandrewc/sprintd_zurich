"""Demo tabs «Fakten» and «Regeln» on the dual-reader fixture (profile dual-facts, tmp table + tmp fact policy):
both readers per fact, the combination / band knobs with their instant effect, disagreements, rule cards with live
hits, the rule builder, instant apply with undo, and the call card's side-by-side readers. Offline, no model."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, REVIEW_ID, FixtureEnv, write_dual_env

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard.ui import backend as be

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "demo" / "app.py"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_dual_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    return e


def run(page: str, query: dict[str, str] | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    at.run()
    at.switch_page(page).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def body(at: AppTest) -> str:
    return "\n".join(str(x.value) for x in [*at.markdown, *at.caption, *at.warning, *at.info, *at.error])


def test_fixture_decides_with_the_fact_policy(env: FixtureEnv):
    from callguard.config import load_config

    eng = be.Engine(load_config(env.config, env.sets))
    assert getattr(eng.pipeline.fusion, "rule", None) == "policy"
    loaded = be.load_results(env.runs_dir)
    labels = {c: be.redecide(eng, r, None, eng.families()).decision.label for c, r in loaded.results.items()}
    assert labels[ALARM_ID] == "alarm"
    assert labels[REVIEW_ID] == "review"  # Kev unsure on «current» -> unklar -> review rule
    assert labels[HARMLESS_ID] == "no_alert"  # readers split on «wish», but no inside information: no rule fires


def test_facts_tab(env: FixtureEnv):
    at = run("pages/facts.py")
    assert at.title[0].value == "Fakten"
    heads = [h.value for h in at.header]
    assert heads == ["Wie die zwei KI-Leser zusammen entscheiden", "Fakten je Prüfart",
                     "Fakten ändern: Freigabe durch zweite Person nötig"]
    text = body(at)
    assert "Einigkeit" in text and "Uneinigkeiten" in "\n".join(e.label for e in at.expander)
    assert "ändert keinen der 3 Anrufe" in text
    # try «Nur Qwen»: instant effect, session only (the file is untouched)
    at.segmented_control(key="dm_fk_comb").set_value("only_a").run()
    assert not at.exception, [e.message for e in at.exception]
    text = body(at)
    assert "ändert 1 von 3 Anrufen" in text and "nur für Sie sichtbar" in text
    assert fpol.load_fact_policy(env.root / "config" / "fact_policy.yaml").combination == "agree"


def test_rules_tab_builder_apply_and_undo(env: FixtureEnv):
    at = run("pages/rules.py")
    assert at.title[0].value == "Regeln"
    assert [h.value for h in at.header][:2] == ["Wie streng?", "Regeln je Prüfart"]
    text = body(at)
    assert "greift bei" in text and "WENN" in text
    assert at.slider(key="dm_threshold") is not None
    # switch a rule off: tried out (working copy), then applied instantly, then undone
    table_path = env.root / "config" / "policy_table.yaml"
    rid = pe.load_doc(table_path)["families"]["access"]["rules"][0]["id"]
    at.toggle(key=f"dm_rg_on_access_{rid}").set_value(False).run()
    assert not at.exception, [e.message for e in at.exception]
    assert "noch nicht übernommen" in body(at)
    next(b for b in at.button if b.label.startswith("Übernehmen")).click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert pe.is_enabled(pe.load_doc(table_path)["families"]["access"]["rules"][0]) is False
    next(b for b in at.button if b.label.startswith("Letzte Regeländerung")).click().run()
    assert pe.is_enabled(pe.load_doc(table_path)["families"]["access"]["rules"][0]) is True


def test_rule_builder_live_hits(env: FixtureEnv):
    at = run("pages/rules.py")
    at.pills(key="dm_rb_trade_facts").set_value(["wish"]).run()
    assert not at.exception, [e.message for e in at.exception]
    text = body(at)
    assert "Vorschau:" in text and "greift bei" in text


def test_call_card_shows_both_readers(env: FixtureEnv):
    at = run("pages/call.py", {"call": REVIEW_ID})
    text = body(at) + "\n".join(e.label for e in at.expander)
    assert "Qwen" in text and "Kev" in text and "uneinig" in text


def test_keywords_tab(env: FixtureEnv):
    at = run("pages/keywords.py")
    assert at.title[0].value == "Stichwörter"
