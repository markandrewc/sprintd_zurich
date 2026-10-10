"""The demo app (``callguard demo``): AppTest smoke of every page on fixture data, the synchronised
transcript component's HTML (segments, passages, start time, escaping), the decision card, the review's
reason codes through the feedback store into the learning export, the keyword-edit effect and the quality
rates. Offline: fixture results (tests/ui_fixtures.py), fake LLM, no model."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest
from ui_fixtures import ALARM_ID, HARMLESS_ID, REVIEW_ID, FixtureEnv, write_fixture_env

from callguard import audit
from callguard import feedback as fb
from callguard.checks.facts import decide_family, load_policy_table
from callguard.config import load_config
from callguard.demo import card as cd
from callguard.demo import keywords as kw
from callguard.demo import media
from callguard.demo import quality as qd
from callguard.demo import review as rv
from callguard.demo.transcript import keyword_terms, mark_terms, player_html, start_segment
from callguard.learning import export, records
from callguard.splits import Splits
from callguard.types import (CallResult, CheckResult, Decision, FamilyScore, FusedFamily, Keyword, Passage, Segment,
                             Transcript)
from callguard.ui import backend as be

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "demo" / "app.py"
PAGES = {"cases": None, "call": "pages/call.py", "settings": "pages/rules.py", "quality": "pages/quality.py",
         "process": "pages/process.py", "facts": "pages/facts.py", "keywords": "pages/keywords.py"}



@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    return e


def run_demo(page: str | None = None, query: dict[str, str] | None = None) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    for k, v in (query or {}).items():
        at.query_params[k] = v
    at.run()
    if page:
        at.switch_page(page).run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def texts(at: AppTest) -> str:
    parts = [x.value for x in [*at.markdown, *at.caption, *at.warning, *at.info, *at.error, *at.success]]
    return "\n".join(str(p) for p in parts)


def iframes(at: AppTest) -> list[str]:
    """The HTML documents of st.components.v1.html elements."""
    out = []
    for el in at.main:  # walk the element tree
        out += _find_html(el)
    return out


def _find_html(node) -> list[str]:
    found = []
    proto = getattr(node, "proto", None)
    if proto is not None and hasattr(proto, "srcdoc") and proto.srcdoc:
        found.append(proto.srcdoc)
    for child in getattr(node, "children", {}).values() if isinstance(getattr(node, "children", None), dict) else []:
        found += _find_html(child)
    return found


# --------------------------------------------------------------------------------------------
# pages (AppTest)
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("page", [p for p in PAGES if p not in ("settings", "facts")])
def test_every_demo_page_renders(env: FixtureEnv, page: str):
    at = run_demo(PAGES[page])
    assert at.title, f"{page} has no title"


def test_facts_and_rules_tabs_single_reader_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Profile with ONE reader (recommended): «Regeln» keeps «Wie streng?» (threshold + Prüfmodus) and points to the
    dual-reader profile for rule editing; «Fakten» shows the questions and the four-eyes governance (Regelwerk
    sections, embedded layout) on a tmp copy of the table, so its version store never writes into the repo."""
    import shutil

    import yaml

    from callguard.config import ROOT

    repo_versions = sorted(p.name for p in (ROOT / "config" / "policy_versions").glob("*"))
    env = write_fixture_env(tmp_path, config="recommended")
    active = tmp_path / "config" / "policy_table.yaml"
    shutil.copy(ROOT / "config" / "policy_table.yaml", active)
    idx = next(i for i, c in enumerate(yaml.safe_load((ROOT / "config/recommended.yaml").read_text())["checks"])
               if c["type"] == "facts")
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tmp_path / 'tuning.yaml'}"
                       + f" --set checks.{idx}.policy_table={active}")
    at = run_demo(PAGES["settings"])
    assert at.title[0].value == "Regeln"
    assert [h.value for h in at.header] == ["Wie streng?"]
    assert at.slider(key="dm_threshold") is not None
    assert "dual-facts" in texts(at)
    at = run_demo(PAGES["facts"])
    assert at.title[0].value == "Fakten"
    assert [h.value for h in at.header] == ["Fakten je Prüfart", "Fakten ändern: Freigabe durch zweite Person nötig"]
    body = texts(at)
    assert "Aktiv: **Version" in body and "einem** KI-Leser" in body
    assert (active.parent / "policy_versions").is_dir()
    assert sorted(p.name for p in (ROOT / "config" / "policy_versions").glob("*")) == repo_versions


def test_worklist_orders_alarm_then_review_and_threshold_moves_counts(env: FixtureEnv):
    at = run_demo()
    assert at.title[0].value == "Fälle"
    shown = {m.label: m.value for m in at.metric}
    assert shown == {"Alarm": "1", "Prüfen": "1", "Kein Alarm": "1", "Mensch nötig": "2"}  # boxes as on 8501
    assert at.slider(key="dm_threshold") is not None  # full-width Alarmschwelle under the boxes
    df = at.dataframe[0].value
    data = df.data if hasattr(df, "data") else df
    assert list(data["Anruf"])[:2] == [ALARM_ID, REVIEW_ID]
    assert set(data["Bearbeitung"]) == {"offen"}
    at.slider(key="dm_threshold").set_value(0.05).run()
    assert not at.exception
    engine = be.Engine(load_config(env.config, env.sets))
    loaded = be.load_results(env.runs_dir)
    d = be.fusion_defaults(engine.cfg)
    want = be.label_counts(be.decide_all(engine, loaded, {"threshold": 0.05, "review_band": d["review_band"],
                                                          "max_uncertainty": d["max_uncertainty"],
                                                          "weights": be.check_weights(engine.cfg)}, engine.families()))
    shown = {m.label: m.value for m in at.metric}
    want_shown = {be.LABEL_TEXT[k]: str(v) for k, v in want.items()}
    want_shown["Mensch nötig"] = str(want["alarm"] + want["review"])
    assert shown == want_shown and shown["Alarm"] != "1"


def test_deep_link_opens_call_page_with_synced_player(env: FixtureEnv):
    at = run_demo(query={"call": ALARM_ID, "t": "48"})
    assert at.title[0].value == ALARM_ID
    body = texts(at)
    assert "Über einen Alarm-Link geöffnet" in body and "00:48" in body
    assert "Ihre Beurteilung" in [h.value for h in at.subheader]


def test_card_explains_each_fact_and_seeks_the_player_to_its_passage(env: FixtureEnv):
    table = load_policy_table("config/policy_table.yaml")
    path = env.result_path(ALARM_ID)
    r = CallResult.model_validate_json(path.read_text())
    fx = facts_result(table, ALARM_ID, "trade", {"wish": "yes", "inside_info": "yes", "public": "no"},
                      evidence={"wish": ["S007"]})
    r.checks["facts"] = fx.checks["facts"]
    path.write_text(r.model_dump_json(indent=1))
    at = run_demo(PAGES["call"], query={"call": ALARM_ID})
    body = texts(at)
    assert "Alle Bedingungen erfüllt → diese Regel entscheidet (erste passende Regel von oben)." in body
    assert "Frage an die KI:" in body and "keine einzelne Stelle markiert" in body  # public: no evidence
    assert any("ja 0.97" in c.value for c in at.caption)
    seek = next(b for b in at.button if b.label.startswith("Stelle anhören"))
    assert seek.label == "Stelle anhören (ab 00:48)"  # S007 starts 58.5 s, minus 10 s
    seek.click().run()
    assert not at.exception
    assert any("Aufnahme bei 00:48" in c.value for c in at.caption)
    assert at.session_state[f"dm_seek_{ALARM_ID}"][0] == pytest.approx(48.5)


def test_review_call_shows_open_point_and_harmless_call_explains_keyword_trap(env: FixtureEnv):
    at = run_demo(query={"call": REVIEW_ID})
    assert "Warum Prüfen?" in texts(at) or "Offen:" in texts(at)
    at = run_demo(query={"call": HARMLESS_ID})
    assert "**Warum kein Alarm?**" in texts(at), "no «Warum kein Alarm?»"
    assert "Stichwort-Falle" in texts(at) and "Quartalszahlen" in texts(at)


def test_review_form_saves_a_data_point_and_marks_the_case_done(env: FixtureEnv):
    at = run_demo(PAGES["call"], query={"call": ALARM_ID})
    assert at.get("button_group"), "segmented controls missing"
    at.session_state[f"dm_rv_verdict_{ALARM_ID}_0"] = "violation"
    at.session_state[f"dm_rv_agree_{ALARM_ID}_0"] = "yes"
    at.session_state[f"dm_rv_context_harmless_{ALARM_ID}_0"] = True
    at.text_input(key="dm_name").set_value("Anna")
    at.run()
    save = next(b for b in at.button if b.label == "Beurteilung speichern")
    save.click().run()
    assert not at.exception, [e.message for e in at.exception]
    items = fb.load(env.runs_dir)
    assert items and items[0].call_id == ALARM_ID and items[0].verdict == "violation"
    call_item = next(i for i in items if i.target == "call")
    assert call_item.agrees is True and [r.code for r in call_item.reasons] == ["context_harmless"]
    assert any("Datenpunkt #1" in s.value for s in at.success), (texts(at)[-3000:], at.session_state["dm_saved"] if "dm_saved" in at.session_state else None)
    assert audit.read_events(env.runs_dir, kind="feedback")
    at = run_demo()
    data = at.dataframe[0].value
    data = data.data if hasattr(data, "data") else data
    row = data[data["Anruf"] == ALARM_ID].iloc[0]
    assert row["Bearbeitung"].endswith("bearbeitet")


def test_quality_page_without_test50_says_so(env: FixtureEnv):
    at = run_demo(PAGES["quality"])
    assert at.title[0].value == "Qualität"


def test_outcept_down_and_models_unreachable_are_messages_not_crashes():
    from callguard.demo import common, readiness

    sent, err = common.send_outcept([{"url": "x", "title": "t", "description": "d"}], url="http://127.0.0.1:9/triggers",
                                    timeout=1.0)
    assert sent == 0 and "nicht erreichbar" in err
    r = readiness.check("no-such-profile-xyz")
    assert r.ok is False and "nicht ladbar" in r.summary


def test_outcept_bodies_link_back_into_the_demo(env: FixtureEnv, monkeypatch: pytest.MonkeyPatch):
    from callguard.demo import common
    from callguard.ui.session import AppState  # noqa: F401  (type only)

    monkeypatch.setenv("CALLGUARD_DEMO_URL", "http://demo.local:8502")

    class App:  # the two attributes outcept_bodies reads
        ctx = be.Engine(load_config(env.config, env.sets)).ctx
        link_pad = 10.0

    r = be.load_results(env.runs_dir).results[ALARM_ID]
    bodies = common.outcept_bodies(App(), r)
    assert len(bodies) == 2 and bodies[0]["url"] == f"http://demo.local:8502/?call={ALARM_ID}&t=48"


def test_demo_command_line():
    from callguard.commands.demo import command

    cmd = command(8502, "recommended", ["a.b=c"])
    assert cmd[cmd.index("--server.port") + 1] == "8502" and cmd[-4:] == ["--config", "recommended", "--set", "a.b=c"]
    assert "--theme.primaryColor" in cmd and str(APP) in cmd


# --------------------------------------------------------------------------------------------
# transcript component
# --------------------------------------------------------------------------------------------


def _transcript() -> Transcript:
    return Transcript(call_id="X-K1", duration=40.0, segments=[
        Segment(id="S001", start=0.0, end=8.0, role="advisor", text="Grüezi, wie kann ich helfen?", confidence=0.9),
        Segment(id="S002", start=8.5, end=20.0, role="customer",
                text="Die Quartalszahlen sind <b>nicht</b> publiziert & \"vertraulich\" __ROWS__", confidence=0.4),
        Segment(id="S003", start=20.5, end=30.0, role="customer", text="Ich will vor der Meldung kaufen.",
                confidence=0.95),
        Segment(id="S004", start=31.0, end=39.0, role="unknown", speaker="SPK2", text="</script><script>alert(1)</script>"),
    ])


def test_player_html_segments_passages_start_and_escaping():
    tr = _transcript()
    passages = [Passage(family="trade", family_label="Insiderhandel (Info)", start=8.5, end=30.0,
                        segment_ids=["S002", "S003"], score=0.9, misheard=True)]
    doc = player_html(tr, passages, audio_src="data:audio/mpeg;base64,AAAA", colors={"trade": "#2a78d6"},
                      labels={"trade": "Insiderhandel"}, start_at=21.0, link_pad=10.0, misheard_below=0.6,
                      terms={"S002": ["Quartalszahlen"]})
    # every segment, with role and timestamp, in order
    assert [m for m in re.findall(r'id="seg-(S\d+)"', doc)] == ["S001", "S002", "S003", "S004"]
    assert "Beratung" in doc and "Kunde" in doc and "SPK2" in doc and ">00:08<" in doc
    # passage: tinted, labelled once, jump button 10 s early and pausing 10 s after
    assert doc.count("in-passage") == 2 + doc.count(".cg-seg.in-passage")
    assert "Passage 1 · Insiderhandel" in doc
    assert 'data-seek="0.00"' in doc and 'data-stop="40.00"' in doc  # 8.5-10 clamps to 0; 30+10
    assert "Passage 1 (00:08)" in doc and "möglicherweise verhört" in doc
    # start time: config + the segment playing at 21 s is current
    cfg = json.loads(re.search(r'data-config="([^"]*)"', doc).group(1).replace("&quot;", '"'))
    assert cfg["startAt"] == 21.0 and cfg["hasAudio"] is True
    assert re.search(r'class="[^"]*is-current[^"]*" id="seg-S003"', doc)
    # escaping: no raw markup from the transcript, keyword marked, slot names not substituted twice
    assert "<b>nicht</b>" not in doc and "&lt;b&gt;nicht&lt;/b&gt;" in doc
    assert "<script>alert(1)" not in doc and "&lt;/script&gt;" in doc
    assert '<mark class="cg-kw">Quartalszahlen</mark>' in doc
    assert "__ROWS__" in doc  # the transcript's literal text survives
    assert doc.count("<script>") == 1  # only the component's own script
    assert "http" not in doc.split("<script>")[1]  # no CDN, no network


def test_player_without_audio_and_without_passages():
    doc = player_html(_transcript(), [], audio_src=None, audio_note="Datei fehlt")
    assert "<audio" not in doc and "Aufnahme auf diesem Rechner nicht verfügbar: Datei fehlt" in doc
    assert "cg-jump" not in doc.split("<script>")[0].split('class="cg-jumps">')[1].split("</div>")[0]
    cfg = json.loads(re.search(r'data-config="([^"]*)"', doc).group(1).replace("&quot;", '"'))
    assert cfg["startAt"] is None and cfg["hasAudio"] is False


def test_start_segment_and_mark_terms():
    tr = _transcript()
    assert start_segment(tr, None) is None and start_segment(tr, 0.0) == "S001"
    assert start_segment(tr, 7.9) == "S001" and start_segment(tr, 8.4) == "S002"  # pause: the next one
    assert start_segment(tr, 25.0) == "S003" and start_segment(tr, 100) == "S004"
    assert mark_terms("A <b> a", ["a"]) == '<mark class="cg-kw">A</mark> &lt;b&gt; <mark class="cg-kw">a</mark>'


def test_keyword_terms_from_fixture(env: FixtureEnv):
    r = be.load_results(env.runs_dir).results[HARMLESS_ID]
    assert keyword_terms(r)["S000"] == ["Quartalszahlen"]


def test_media_transcodes_once_and_degrades(env: FixtureEnv, tmp_path: Path):
    r = be.load_results(env.runs_dir).results[ALARM_ID]
    a = media.player_audio(r.audio_path, tmp_path / "run")
    assert a.src and a.src.startswith("data:audio/")
    assert media.player_audio(None, tmp_path).src is None
    assert media.player_audio(str(tmp_path / "nope.wav"), tmp_path).note


# --------------------------------------------------------------------------------------------
# decision card
# --------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def table():
    return load_policy_table("config/policy_table.yaml")


def facts_result(table, call_id: str, family: str, values: dict[str, str], label: str = "alarm",
                 score: float = 0.9, evidence: dict[str, list[str]] | None = None) -> CallResult:
    ft = table.families[family]
    probs = {k: {"yes": 0.0, "no": 0.0, "unclear": 0.0, v: 0.97} for k, v in values.items()}
    full = {f.id: values.get(f.id, "unclear") for f in ft.facts}
    fprobs = {f.id: probs.get(f.id, {"unclear": 1.0}) for f in ft.facts}
    fd = decide_family(ft, full, fprobs)
    detail = {"decision": fd.label, "facts": {k: {"label": ft.fact(k).label, "role": ft.fact(k).role, "value": full[k],
                                                  "p": fprobs[k], "question": ft.fact(k).question("en"),
                                                  **({"evidence": evidence[k]} if evidence and k in evidence else {})}
                        for k in full},
              "rule": {"id": fd.rule.id if fd.rule else None, "label": fd.label,
                       "when": fd.rule.when if fd.rule else "true", "text": fd.rule.text if fd.rule else ""}}
    t = Transcript(call_id=call_id, segments=[
        Segment(id="S001", start=0, end=5, role="advisor", text="Grüezi."),
        Segment(id="S002", start=5, end=12, role="customer", text="Die Quartalszahlen sind publiziert.")])
    kwr = CheckResult(check="keywords", type="keywords", findings=[], family_scores={})
    d = Decision(label=label, score=score, uncertainty=0.1, threshold=0.55, top_family=family if label != "no_alert" else None,
                 passages=[] if label == "no_alert" else [Passage(family=family, start=5, end=12, score=score,
                                                                   segment_ids=["S002"])],
                 families={family: FusedFamily(family=family, label=family, score=score, uncertainty=0.1)})
    return CallResult(call_id=call_id, transcript=t, decision=d, checks={
        "facts": CheckResult(check="facts", type="facts", meta={"policy_table": {"path": "config/policy_table.yaml"}},
                             family_scores={family: FamilyScore(score=fd.score, confidence=fd.confidence,
                                                                detail=detail, reason=fd.summary)}),
        "keywords": kwr}, meta={"provenance": {"checks": {"facts": {"params": {}}}}})


def test_card_alarm_names_rule_facts_and_basis(table):
    r = facts_result(table, "T-K1", "trade", {"wish": "yes", "inside_info": "yes", "public": "no"},
                     evidence={"wish": ["S002"]})
    c = cd.build_card(r, r.decision, [], table=table)
    assert c.label_de == "Alarm" and c.rule_id and c.rule_plain.startswith("WENN") and c.rule_plain.endswith("ALARM")
    assert [f.fact for f in c.facts if f.decisive][:3] == ["wish", "inside_info", "public"]
    wish = c.facts[0]
    assert wish.text == f"{table.families['trade'].fact('wish').label}: ja (0.97)"
    # the explanation behind a fact: the full German question (not the English one the model read, no model
    # instructions), the probabilities, the segments the answer rests on
    assert wish.question_de == cd.plain_question(table.families["trade"].fact("wish").question("de"))
    assert "Antworte" not in wish.question_de and wish.question_de != wish.question
    assert wish.p == {"yes": 0.97, "no": 0.0, "unclear": 0.0} and wish.evidence == ["S002"]
    assert c.facts[1].evidence == []
    assert "FinfraG" in c.basis and cd.short_basis(c.basis) == "FinfraG Art. 142"
    assert c.why_not is None and c.failed_rules == []
    assert cd.plain_question('Ist es so? Antworte "unknown", wenn offen.') == "Ist es so?"


def test_card_keyword_trap_explains_what_blocks_the_alarm(table):
    r = facts_result(table, "T-K2", "trade", {"wish": "no", "inside_info": "no", "public": "yes"}, label="no_alert",
                     score=0.02)
    from callguard.types import Finding

    r.checks["keywords"].findings = [Finding(check="keywords", family="trade", score=0.3, segment_ids=["S002"],
                                             reason="K03", detail={"keyword_id": "K03", "matched_text": "Quartalszahlen"})]
    r.checks["keywords"].family_scores = {"trade": FamilyScore(score=0.5, confidence=0.4, reason="Stichwort K03")}
    r.decision.families["trade"].per_check = {"keywords": 0.5, "facts": 0.0}
    from callguard.families import load_families

    fams = load_families("config/keywords.json", "config/criteria.yaml")
    c = cd.build_card(r, r.decision, fams, table=table)
    assert c.label == "no_alert" and c.why_not is not None and c.why_not.is_trap
    assert c.why_not.keywords == ["Quartalszahlen"]
    blocking = {f.fact for f in c.why_not.blocking}
    assert {"wish", "public"} <= blocking
    assert "kein Verstoss" in c.why_not.summary and cd.one_liner(c).startswith("Stichwort-Falle")
    # which condition of each alarm rule failed, in words
    public = table.families["trade"].fact("public").label
    assert c.failed_rules and any(f"«{public}» = ja" in conds for _, _, conds in c.failed_rules)


def test_blocking_and_failing_facts(table):
    ft = table.families["trade"]
    vals = {"wish": "yes", "inside_info": "unclear", "public": "yes"}
    assert set(cd.blocking_facts(ft, vals)) >= {"public"}
    assert cd.failing_facts(ft.rules[0].node, {"wish": "yes", "inside_info": "yes", "public": "no"}) == []


# --------------------------------------------------------------------------------------------
# reason codes: review form -> feedback store -> learning export
# --------------------------------------------------------------------------------------------


def test_reason_codes_round_trip_into_the_learning_export(tmp_path: Path, table):
    r = facts_result(table, "Stufe2_C01-K3", "trade", {"wish": "yes", "inside_info": "yes", "public": "no"})
    c = cd.build_card(r, r.decision, [], table=table)
    reasons = rv.collect_reasons(c, facts={"public": "yes", "wish": "yes"}, passages={0: "passage_not_applies"},
                                 flags=["context_harmless", "rule_too_strict", "bogus"], other_families=["access"])
    assert [x.code for x in reasons] == ["fact_wrong", "passage_not_applies", "context_harmless", "rule_too_strict",
                                         "other_family"]  # unchanged fact and unknown flag dropped
    assert reasons[0].describe().startswith("Fakt falsch erkannt: public (nein → ja)")
    items = fb.items_from_review(r, user="Anna", verdict="no_violation", agrees=False, reasons=reasons, comment="öffentlich")
    assert [i.target for i in items] == ["call", "passage", "fact"]  # other_family only with a violation
    assert items[0].agrees is False and len(items[0].reasons) == 5 and len({i.batch for i in items}) == 1
    fact = items[2]
    assert (fact.fact, fact.model_value, fact.answer, fact.agrees) == ("public", "no", "yes", False)
    fb.add_many(tmp_path, items)
    loaded = fb.load(tmp_path)
    assert [x.code for x in loaded[0].reasons] == [x.code for x in reasons]  # survives the JSONL store
    assert fb.batch_count(loaded) == 1 and fb.judged_calls(loaded) == {"Stufe2_C01-K3"}
    ev = audit.read_events(tmp_path, kind="feedback")
    assert ev[0]["reasons"] == [x.code for x in reasons] and ev[0]["agrees"] is False
    # learning export: call row carries agree + reasons, the fact correction is a fact label
    splits = Splits(holdout=[], dev_folds={0: ["Stufe1_D01"]}, groups={})
    labels = records.collect(tmp_path, {r.call_id: r}, splits)
    call = labels.calls[r.call_id]
    assert call.agrees is False and [x["code"] for x in call.reasons][0] == "fact_wrong"
    assert call.reasons[0]["fact"] == "public" and call.reasons[0]["after"] == "yes"
    built = export.build(labels, {r.call_id: r}, splits)
    row = built["calls.jsonl"][0]
    assert row["agrees"] is False and len(row["reasons"]) == 5
    assert built["facts.jsonl"][0]["fact"] == "public" and built["facts.jsonl"][0]["answer"] == "yes"
    assert built["passages.jsonl"][0]["applies"] is False
    man = export.manifest(built, labels, splits)
    assert man["reason_codes"]["fact_wrong"] == 1 and man["officer_agrees"] == {"false": 1}
    # a stored line from before reason codes still loads
    (tmp_path / "old").mkdir()
    (tmp_path / "old" / fb.FEEDBACK_FILE).write_text(json.dumps({"call_id": "a-K1", "verdict": "violation"}) + "\n")
    assert fb.load(tmp_path / "old")[0].reasons == []


def test_review_refuses_unknown_codes_and_needs_a_verdict(table):
    r = facts_result(table, "T-K1", "trade", {"wish": "yes", "inside_info": "yes", "public": "no"})
    with pytest.raises(ValueError):
        fb.items_from_review(r, user="A", verdict="violation", reasons=[{"code": "nope"}])
    with pytest.raises(ValueError):
        fb.items_from_review(r, user="A", verdict=None, reasons=[{"code": "context_harmless"}])
    items = fb.items_from_review(r, user="A", verdict="violation", reasons=[{"code": "other_family", "family": "access"}])
    assert [i.target for i in items] == ["call", "family"]


def test_confirmation_is_honest_about_use():
    items = [fb.FeedbackItem(call_id="x", verdict="fact", fact="a", answer="yes"),
             fb.FeedbackItem(call_id="x", verdict="applies", passage_index=0)]
    assert rv.confirmation(3, items, "train") == "Datenpunkt #3 für Training gespeichert (Fakten-Labels: 1, Passagen-Labels: 1)"
    assert "nur Evaluation" in rv.confirmation(3, items, "eval_case_dev")


# --------------------------------------------------------------------------------------------
# keyword effect, quality
# --------------------------------------------------------------------------------------------


def test_keyword_effect_counts_hits_before_and_after(env: FixtureEnv):
    engine = be.Engine(load_config(env.config, env.sets))
    loaded = be.load_results(env.runs_dir)
    fams = engine.families()
    decided = be.decide_all(engine, loaded, None, fams)
    trade = next(f for f in fams if f.id == "trade")
    same = kw.keyword_effect(engine, loaded.results, decided, fams, None, None, "trade", trade.keywords)
    assert same is not None and same.hits_before == same.hits_after and not same.changed
    extra = [*trade.keywords, Keyword(id="K99", label="Bericht", de=["Bericht"])]
    more = kw.keyword_effect(engine, loaded.results, decided, fams, None, None, "trade", extra)
    assert more.family_hits_after > more.family_hits_before and more.calls_after >= more.calls_before
    none = kw.keyword_effect(engine, loaded.results, decided, fams, None, None, "trade", [])
    assert none.family_hits_after == 0
    # rerunning one family and merging = running the whole list (the check scores families independently)
    check = kw.keyword_check(engine)
    new_fams = kw.with_keywords(fams, "trade", extra)
    for r in loaded.results.values():
        tr = be.check_view_transcript(engine.pipeline, check, r)
        full = check.run(tr, new_fams)
        merged = kw.merge_family(check.run(tr, fams), check.run(tr, [new_fams[[f.id for f in fams].index("trade")]]),
                                 "trade")
        assert sorted(f.reason for f in merged.findings) == sorted(f.reason for f in full.findings)
        assert {k: v.score for k, v in merged.family_scores.items()} == {k: v.score for k, v in full.family_scores.items()}


def test_quality_rates_per_dataset_and_chart(tmp_path: Path):
    rows = []
    for i in range(20):
        exp = "alarm" if i % 2 else "no_alert"
        pred = exp if i % 5 else ("no_alert" if exp == "alarm" else "review")
        rows.append({"call_id": f"T50-trade-{i:02d}-A-K1", "dialogue_id": f"T50-trade-{i:02d}-A", "group": f"g{i // 2}",
                     "expected": exp, "predicted": pred, "score": 0.5})
    d = tmp_path / "test50" / "experiments" / "test50" / "champion"
    d.mkdir(parents=True)
    (d / "rows.json").write_text(json.dumps({"fixed": rows}))
    r = qd.test50_rates(tmp_path, n_boot=300)
    assert r is not None and r.n_calls == 20 and r.key == "test50"
    assert (r.far.k, r.far.n) == (2, 10) and (r.miss.k, r.miss.n) == (2, 10)
    assert r.far.lo <= r.far.value <= r.far.hi and "nie zum Tunen" in r.note
    assert qd.find_test50(tmp_path, "missing") is None
    from callguard.ui.modes import ModeMetrics, Rate

    m = ModeMetrics(variant="champion", n_calls=48, far=Rate(0.1, 0.0, 0.3, 2, 22), recall=Rate(0.8, 0.6, 0.95, 21, 26))
    dev = qd.dev_rates(m, "Ausgewogen")
    assert (dev.miss.k, dev.miss.n) == (5, 26) and dev.miss.lo == pytest.approx(0.05) and dev.miss.hi == pytest.approx(0.4)
    spec = qd.chart([dev, r]).to_dict()
    assert spec["facet"]["column"]["field"] == "Datensatz"
    names = {row["Datensatz"] for row in qd.chart_rows([dev, r])}
    assert len(names) == 2  # two panels, never pooled
