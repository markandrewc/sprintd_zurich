"""Demo app on the dual-reader fixture (profile dual-facts, tmp table + tmp fact policy): the top bar, «Einstellungen»
(Regeln list + wizard + KI-Assistent, Fakten list + wizard + four-eyes proposals, Stichwörter), the «Sicherheit der KI»
slider on «Fälle» and the call card's side-by-side readers. Offline: fake LLM, no model."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, REVIEW_ID, FixtureEnv, write_dual_env

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard.config import ROOT
from callguard.demo import settings_rules as sr
from callguard.policy_versions import VersionStore
from callguard.ui import backend as be

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "demo" / "app.py"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_dual_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    monkeypatch.setattr(sr, "AI_DELAY", 0.0)
    return e


def run(page: str | None = None, query: dict[str, str] | None = None, user: str | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    if user:
        at.session_state["dm_user"] = user
    at.run()
    if page:
        at.switch_page(page).run()
    ok(at)
    return at


def ok(at: AppTest) -> None:
    assert not at.exception, [e.message for e in at.exception]


def body(at: AppTest) -> str:
    return "\n".join(str(x.value) for x in [*at.markdown, *at.caption, *at.warning, *at.info, *at.error, *at.success])


def table(env: FixtureEnv) -> dict:
    return pe.load_doc(env.root / "config" / "policy_table.yaml")


# --------------------------------------------------------------------------------------------
# navigation
# --------------------------------------------------------------------------------------------


def test_top_bar_has_four_entries_and_process_is_reachable_from_cases(env: FixtureEnv):
    src = APP.read_text()
    pages = re.findall(r'st\.Page\(PAGES / "(\w+)\.py", title="([^"]+)"(.*?)\),?\n', src, flags=re.S)
    visible = [title for _, title, rest in pages if 'visibility="hidden"' not in rest]
    assert visible == ["Fälle", "Anruf prüfen", "Einstellungen", "Qualität"]
    assert any(t == "Anruf verarbeiten" and 'visibility="hidden"' in rest for _, t, rest in pages)
    at = run()
    assert at.title[0].value == "Fälle"
    links = at.get("page_link")
    assert any(getattr(x.proto, "label", "") == "Neuen Anruf prüfen" for x in links)


def test_settings_has_three_tabs(env: FixtureEnv):
    at = run("pages/settings.py")
    assert at.title[0].value == "Einstellungen"
    assert [t.label for t in at.tabs][:3] == [":material/rule: Regeln", ":material/fact_check: Fakten",
                                              ":material/label: Stichwörter"]
    text = body(at)
    assert "WENN" in text and "ALARM" in text  # rule list (hits sit on each row's «greift bei N» popover)
    assert "Ein **Fakt** ist eine kleine Ja/Nein-Frage" in text and "einig bei" in text  # fact list
    assert any(b.label == "Neue Regel" for b in at.button) and any(b.label == "Neuer Fakt" for b in at.button)


# --------------------------------------------------------------------------------------------
# rule wizard
# --------------------------------------------------------------------------------------------


def test_rule_wizard_steps_save_and_decide(env: FixtureEnv):
    at = run("pages/settings.py", user="Anna")
    at.button(key="dm_rg_new").click().run()
    ok(at)
    at.checkbox(key="dm_rw_f_access.spoken_0").check().run()
    ok(at)
    assert "Diese Regel greift bei" in body(at)
    at.button(key="dm_rw_next").click().run()
    ok(at)
    assert "unklar = " in body(at)  # the band shown per fact
    at.segmented_control(key="dm_rw_v_access.spoken_0").set_value("yes").run()
    at.button(key="dm_rw_next").click().run()
    ok(at)
    at.segmented_control(key="dm_rw_lab_0").set_value("alarm").run()
    at.text_input(key="dm_rw_title_0").input("Code am Telefon").run()
    at.text_area(key="dm_rw_text_0").input("Ein Code wurde vorgelesen.").run()
    m = re.search(r"Diese Regel greift bei (\d+) von 3 Anrufen", body(at))
    assert m and int(m.group(1)) >= 1
    at.button(key="dm_rw_save").click().run()
    ok(at)
    rules = table(env)["families"]["access"]["rules"]
    new = next(r for r in rules if r.get("title") == "Code am Telefon")
    assert new["label"] == "alarm" and new["when"] == "spoken = yes" and new["text"] == "Ein Code wurde vorgelesen."
    assert "Code am Telefon" in body(at)  # appears in the list
    # it decides calls: the review fixture call (code read out) is now an alarm
    labels = {m.label: m.value for m in at.metric}
    assert labels  # page still renders its counts
    from callguard.config import load_config

    eng = be.Engine(load_config(env.config, env.sets))
    d = be.redecide(eng, be.load_results(env.runs_dir).results[REVIEW_ID], None, eng.families()).decision
    assert d.label == "alarm"
    v = VersionStore(env.root / "config" / "policy_table.yaml").active()
    assert v.meta["instant"] and v.meta["author"] == "Anna"


def test_rule_wizard_one_pruefart_only(env: FixtureEnv):
    st_ = sr.new_state()
    st_["facts"] = ["access.spoken", "trade.wish"]
    assert sr.state_family(st_) is None and sr.state_rule(st_, table(env)) is None
    st_["facts"] = ["access.spoken", "access.current"]
    st_["conds"] = {"access.current": {"value": "unclear", "neg": False}}
    st_["join"] = "or"
    fam, rule = sr.state_rule(st_, table(env))
    assert fam == "access" and rule["when"] == "spoken = yes or current = unclear"


def canned(monkeypatch: pytest.MonkeyPatch, obj: dict) -> None:
    """The fake LLM answers the drafter's JSON request with ``obj`` (everything else as usual)."""
    from callguard.llm.fake import FakeLLM

    orig = FakeLLM.chat

    def chat(self, messages, **kw):
        return [json.dumps(obj)] if kw.get("json_schema") else orig(self, messages, **kw)

    monkeypatch.setattr(FakeLLM, "chat", chat)


def test_ai_assistant_fills_the_wizard_with_the_fake_llm(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    canned(monkeypatch, {"family": "access", "facts": [], "note": "",
                         "rule": {"label": "review", "when": "spoken = yes and validity_open = yes",
                                  "text": "Code vorgelesen, Gültigkeit offen. Bitte anhören.", "basis": ""}})
    at = run("pages/settings.py", user="Anna")
    at.button(key="dm_rg_new").click().run()
    at.text_area(key="dm_rw_ai_req").input("Prüfen, wenn ein Code vorgelesen wird und offen ist, ob er gilt.").run()
    at.button(key="dm_rw_ai_go").click().run()
    ok(at)
    state = at.session_state[sr.WIZ]
    assert "Von der KI ausgefüllt" in state["ai_note"]
    assert state["facts"] == ["access.spoken", "access.validity_open"] and state["label"] == "review"
    assert state["title"] == "Code vorgelesen, Gültigkeit offen"
    # the chips are ticked; the officer still clicks through and saves
    assert state["step"] == 1 and all(at.checkbox(key=f"dm_rw_f_{k}_{state['nonce']}").value for k in state["facts"])
    assert not any(b.key == "dm_rw_save" for b in at.button)
    at.button(key="dm_rw_next").click().run()
    at.button(key="dm_rw_next").click().run()
    at.button(key="dm_rw_save").click().run()
    ok(at)
    assert any(r.get("when") == "spoken = yes and validity_open = yes" for r in table(env)["families"]["access"]["rules"])


def test_ai_assistant_new_fact_goes_to_approval(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    canned(monkeypatch, {"family": "access", "note": "",
                         "facts": [{"id": "from_third", "label": "Code von Dritten", "role": "context",
                                    "de": "Hat die Kundin den Code von einer anderen Person erhalten?",
                                    "en": "Did the customer get the code from someone else?"}],
                         "rule": {"label": "alarm", "when": "spoken = yes and from_third = yes",
                                  "text": "Code von Dritten vorgelesen.", "basis": ""}})
    at = run("pages/settings.py", user="Anna")
    at.button(key="dm_rg_new").click().run()
    at.text_area(key="dm_rw_ai_req").input("Alarm, wenn der Code von jemand anderem stammt.").run()
    at.button(key="dm_rw_ai_go").click().run()
    ok(at)
    assert at.session_state[sr.WIZ]["ai_missing"]
    at.button(key="dm_rw_ai_newfact").click().run()
    ok(at)
    drafts = VersionStore(env.root / "config" / "policy_table.yaml").drafts()
    assert len(drafts) == 1 and drafts[0].author == "Anna"
    assert any(f["label"] == "Code von Dritten" for f in drafts[0].doc()["families"]["access"]["facts"])
    assert not any(f.get("label") == "Code von Dritten" for f in table(env)["families"]["access"]["facts"])


def test_ai_assistant_llm_down_is_graceful(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    from callguard import rule_drafter as rd

    def down(*a, **k):
        raise ConnectionError("refused")

    monkeypatch.setattr(rd, "draft_rule", down)
    at = run("pages/settings.py", user="Anna")
    at.button(key="dm_rg_new").click().run()
    at.text_area(key="dm_rw_ai_req").input("irgendwas").run()
    at.button(key="dm_rw_ai_go").click().run()
    ok(at)
    assert "nicht erreichbar" in at.session_state[sr.WIZ]["ai_note"]


# --------------------------------------------------------------------------------------------
# fact wizard + four eyes
# --------------------------------------------------------------------------------------------


def test_fact_wizard_ends_in_a_proposal_the_author_cannot_approve(env: FixtureEnv):
    at = run("pages/settings.py", user="Anna")
    at.button(key="dm_fk_new").click().run()
    ok(at)
    at.selectbox(key="dm_fw_fam_0").set_value("access").run()
    at.text_area(key="dm_fw_q_0").input("Sagt die Kundin, dass sie den Code von einer anderen Person erhalten hat?").run()
    at.button(key="dm_fw_next").click().run()
    ok(at)
    at.button(key="dm_fw_next").click().run()
    at.text_input(key="dm_fw_l_0").input("Code von Dritten").run()
    at.button(key="dm_fw_submit").click().run()
    ok(at)
    assert not any(f.get("label") == "Code von Dritten" for f in table(env)["families"]["access"]["facts"])
    drafts = VersionStore(env.root / "config" / "policy_table.yaml").drafts()
    assert len(drafts) == 1 and drafts[0].author == "Anna"
    assert "Wartet auf Freigabe" in body(at)
    n = drafts[0].n
    at.text_input(key=f"dm_fk_appr_{n}").input("anna").run()  # same person, other spelling
    at.button(key=f"dm_fk_ok_{n}").click().run()
    assert any("Vier-Augen" in str(e.value) for e in at.error)
    assert not any(f.get("label") == "Code von Dritten" for f in table(env)["families"]["access"]["facts"])
    at.text_input(key=f"dm_fk_appr_{n}").input("Ben").run()
    at.button(key=f"dm_fk_ok_{n}").click().run()
    ok(at)
    assert any(f.get("label") == "Code von Dritten" for f in table(env)["families"]["access"]["facts"])
    assert "Kev beim nächsten GPU-Lauf" in body(at)


# --------------------------------------------------------------------------------------------
# «Sicherheit der KI» on Fälle
# --------------------------------------------------------------------------------------------


def test_certainty_slider_moves_fact_and_call_counts_like_the_engine(env: FixtureEnv):
    from callguard.config import load_config
    from callguard.demo import facts_ui as fu

    at = run()
    assert at.slider(key="dm_certainty").value == pytest.approx(0.7)  # fixture file: Kev band 0.3-0.7
    for c in (0.9, 0.55):
        at.slider(key="dm_certainty").set_value(c).run()
        ok(at)
        eng = be.Engine(load_config(env.config, env.sets))
        fus, fams = eng.pipeline.fusion, eng.families()
        live = fus.fact_policy()
        pol = live.with_certainty(c, "both" if live.a.mode == "band" else "b")
        results = be.load_results(env.runs_dir).results
        outs = fpol.redecide(results, fus.tables(), pol, lambda r, ch: fus.decide_checks(
            r.transcript, ch, fams, {"threshold": 0.55}), **fus.scoring)
        want = {k: sum(o.label == k for o in outs.values()) for k in ("alarm", "review", "no_alert")}
        shown = {m.label: m.value for m in at.metric}
        assert shown["Alarm"] == str(want["alarm"]) and shown["Prüfen"] == str(want["review"])
        comb = fu.answer_spread(results, pol, fus.tables())["combined"]
        assert f"ja **{comb['yes']}** · unklar **{comb['unclear']}** · nein **{comb['no']}**" in body(at)
        assert f"ja ab {c:.2f} · nein bis {1 - c:.2f}" in body(at)
    # higher certainty -> more «unklar»
    at.slider(key="dm_certainty").set_value(0.9).run()
    high = int(re.search(r"unklar \*\*(\d+)\*\*", body(at)).group(1))
    at.slider(key="dm_certainty").set_value(0.55).run()
    low = int(re.search(r"unklar \*\*(\d+)\*\*", body(at)).group(1))
    assert high > low


def test_shipped_default_is_the_dev_choice():
    rep = json.loads((ROOT / "research" / "evidence" / "dual_facts_certainty.json").read_text())
    pol = fpol.load_fact_policy(ROOT / "config" / "fact_policy.yaml")
    assert pol.certainty() == pytest.approx(rep["chosen"]["c"])
    assert (pol.a.mode == "band") == (rep["chosen"]["readers"] == "both") and pol.b.mode == "band"
    assert pol.b.lo == pytest.approx(1 - rep["chosen"]["c"])
    chosen = next(e for e in rep["entries"] if e["setting"] == rep["chosen"]["setting"])
    assert chosen["accuracy"] == max(e["accuracy"] for e in rep["entries"] if e["c"] is not None)


# --------------------------------------------------------------------------------------------
# call card
# --------------------------------------------------------------------------------------------


def test_fixture_decides_with_the_fact_policy(env: FixtureEnv):
    from callguard.config import load_config

    eng = be.Engine(load_config(env.config, env.sets))
    assert getattr(eng.pipeline.fusion, "rule", None) == "policy"
    loaded = be.load_results(env.runs_dir)
    labels = {c: be.redecide(eng, r, None, eng.families()).decision.label for c, r in loaded.results.items()}
    assert labels[ALARM_ID] == "alarm" and labels[REVIEW_ID] == "review" and labels[HARMLESS_ID] == "no_alert"


def test_call_card_shows_both_readers(env: FixtureEnv):
    at = run("pages/call.py", {"call": REVIEW_ID})
    text = body(at) + "\n".join(e.label for e in at.expander)
    assert "uneinig → unklar" in text and "Einigkeit" in text
    metrics = [(m.label, m.value) for m in at.metric]
    assert ("Qwen p(ja)", "0.80") in metrics and ("Kev p(ja)", "0.50") in metrics
    assert ("zusammen", "unklar") in metrics
