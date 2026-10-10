"""S6 "Offene Fakten": the officer answers an open fact, the policy table is re-read (no LLM), the call is
re-fused and the answer lands in the audit trail. Offline: shipped policy table + UI fixtures + AppTest."""

from __future__ import annotations

from pathlib import Path

import pytest
from ui_fixtures import REVIEW_ID, write_fixture_env

from callguard import audit
from callguard.checks.facts import decide_family, load_policy_table
from callguard.types import CallResult, CheckResult, FamilyScore
from callguard.ui import backend as be
from callguard.ui import fact_answers as fa
from callguard.ui import panels as pn

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"

# what Qwen2.5-7B answered on Stufe3_C17-K3 (runs/recommended): a value was read out, validity stays open
C17_ACCESS = {
    "spoken": ("yes", {"yes": 0.9188, "no": 0.0261, "unclear": 0.0552}),
    "current": ("unclear", {"yes": 0.0, "no": 0.0, "unclear": 1.0}),
    "validity_open": ("yes", {"yes": 0.9999, "no": 0.0, "unclear": 0.0001}),
    "expired_or_sample": ("no", {"yes": 0.0, "no": 0.8991, "unclear": 0.1009}),
    "asked_by_advisor": ("no", {"yes": 0.0, "no": 0.9046, "unclear": 0.0954}),
}


def _facts_check(table) -> CheckResult:
    ft = table.families["access"]
    values = {k: v for k, (v, _) in C17_ACCESS.items()}
    probs = {k: p for k, (_, p) in C17_ACCESS.items()}
    fd = decide_family(ft, values, probs)
    detail = {"decision": fd.label, "summary": fd.summary,
              "facts": {k: {"label": ft.fact(k).label, "role": ft.fact(k).role, "value": v, "p": p}
                        for k, (v, p) in C17_ACCESS.items()},
              "rule": {"id": fd.rule.id, "label": fd.rule.label, "when": fd.rule.when, "text": fd.rule.text}}
    fss = {"access": FamilyScore(score=fd.score, confidence=fd.confidence, verdict=fd.verdict, reason=fd.summary,
                                 detail=detail)}
    return CheckResult(check="facts", type="facts", family_scores=fss,
                       meta={"policy_table": {"path": "config/policy_table.yaml",
                                              "hash": table.key(["access"])}})


@pytest.fixture
def table():
    return load_policy_table("config/policy_table.yaml")


@pytest.fixture
def c17(table) -> fa.OpenFamily:
    r = CallResult.model_construct(call_id="x", checks={"facts": _facts_check(table)})
    fams = fa.open_families(r)
    assert len(fams) == 1
    return fams[0]


def test_open_fact_of_c17_is_validity(c17):
    assert c17.family == "access" and c17.label == "review" and c17.rule_id == "access.review_1"
    assert c17.facts == ["current"]  # the unclear fact that blocks access.alarm_1


def test_rule_reevaluation_with_officer_answer(c17):
    opts = fa.load_options()
    fd, values, probs = fa.redecide_family(c17, {"current": "yes"}, None, opts)
    assert (fd.label, fd.rule.id, fd.verdict) == ("alarm", "access.alarm_1", "present")
    assert values["current"] == "yes" and probs["current"]["yes"] == 1.0
    assert fd.score == pytest.approx(0.6 + 0.4 * 0.9188 * 1.0 * 1.0, abs=1e-3)
    # "Nein": the officer settled validity, so "im Gespräch offen" no longer holds (config/open_facts.yaml)
    fd, values, _ = fa.redecide_family(c17, {"current": "no"}, None, opts)
    assert (fd.label, fd.rule.id, values["validity_open"]) == ("no_alert", "access.no_alert", "no")
    assert fa.redecide_family(c17, {"current": "unclear"}, None, opts)[0].label == "review"
    # without the `also` mapping only the answered fact changes: review_1 still fires
    assert fa.redecide_family(c17, {"current": "no"}, None, {})[0].rule.id == "access.review_1"
    # a direct answer beats an implied one
    values, _ = fa.apply_answers(c17.table, c17.values, c17.probs,
                                 {"current": "no", "validity_open": "yes"}, opts)
    assert values["validity_open"] == "yes"


def test_options_and_defaults():
    opts = fa.load_options()
    labels = [o.label for o in fa.options_for("access", "current", opts)]
    assert labels[0].startswith("Ja") and labels[1].startswith("Nein") and labels[2] == "Weiss nicht"
    assert [o.label for o in fa.options_for("trade", "inside_info", opts)] == ["Ja", "Nein", "Weiss nicht"]
    assert fa.load_options("does/not/exist.yaml") == {}


def test_open_facts_skips_settled_and_irrelevant(table):
    ft = table.families["access"]
    clear = {"spoken": "yes", "current": "yes", "validity_open": "no", "expired_or_sample": "no",
             "asked_by_advisor": "no"}
    assert fa.open_facts(ft, clear) == []  # alarm, nothing unclear
    nothing = {**clear, "spoken": "no", "current": "unclear"}
    assert fa.open_facts(ft, nothing) == []  # no value read out: validity cannot change the label


def test_override_result_refuses_the_family(table, c17):
    r = CallResult.model_construct(call_id="x", checks={"facts": _facts_check(table)})
    out = fa.override_result(r, [c17], {"access": {"current": "yes"}}, None, fa.load_options())
    fs = out.checks["facts"].family_scores["access"]
    assert fs.verdict == "present" and fs.score > 0.9 and fs.detail["rule"]["id"] == "access.alarm_1"
    assert fs.detail["officer_answers"] == {"current": "yes"}
    assert r.checks["facts"].family_scores["access"].verdict == "undetermined"  # original untouched


def test_panel_is_registered():
    p = next(p for p in pn.panels() if p.key == "open_facts")
    assert p.title == "Offene Fakten" and callable(p.resolve())


def test_panel_renders_for_review_call_and_audits(tmp_path, monkeypatch, table):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    env = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tmp_path / 'tuning.yaml'}")
    path = env.result_path(REVIEW_ID)
    r = CallResult.model_validate_json(path.read_text())
    r.checks["facts"] = _facts_check(table)
    path.write_text(r.model_dump_json(indent=1))

    at = AppTest.from_file(str(APP), default_timeout=90)
    at.query_params["call"] = REVIEW_ID
    at.run()
    at.switch_page("views/detail.py").run()
    assert not at.exception, [e.message for e in at.exception]
    assert any(e.label == "Offene Fakten" for e in at.expander)
    md = " ".join(m.value for m in at.markdown)
    assert "Wert gehört zum laufenden, gültigen Vorgang" in md

    next(b for b in at.button if b.label == "Ja (gültig)").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert any("access.alarm_1" in e.value for e in at.error)
    assert "Anruf gesamt" in " ".join(m.value for m in at.markdown)
    ev = audit.read_events(env.runs_dir, kind="fact_answer")[-1]
    assert (ev["user"], ev["call_id"], ev["family"], ev["fact"], ev["answer"]) == \
        ("officer", REVIEW_ID, "access", "current", "yes")
    assert ev["family_label"] == "alarm" and ev["rule"] == "access.alarm_1"

    next(b for b in at.button if b.label.startswith("Nein")).click().run()
    assert any("access.no_alert" in e.value for e in at.success)

    next(b for b in at.button if b.label == "Zurücksetzen" and "cg_of_reset" in (b.key or "")).click().run()
    assert not any("Mit Ihren Antworten" in m.value for m in [*at.error, *at.success, *at.warning])
    assert audit.read_events(env.runs_dir, kind="fact_answer_reset")
