"""A new Prüfart as pure configuration (organisers' deep dive: "a new kind of check is added as a definition"),
checks switched on/off with governance, the family drafter, bundle versioning. Offline (canned LLM doubles)."""

from __future__ import annotations

import copy
import json
import shlex
import shutil
from pathlib import Path

import pytest
import yaml

from callguard import audit, registry
from callguard import policy_edit as pe
from callguard import rule_drafter as rd
from callguard import rulebook as rb
from callguard.checks.facts import FactSheetCheck, PolicyTableError, load_policy_table
from callguard.config import ROOT, load_config
from callguard.context import Context
from callguard.families import load_families
from callguard.policy_versions import FourEyesError, VersionStore
from callguard.routing import RoutingConfig, route
from callguard.types import CallResult, Segment, Transcript
from callguard.ui import whatif as wi

SHIPPED = ROOT / "config" / "policy_table.yaml"

BRIBERY = {
    "id": "bestechung", "label": "Bestechung",
    "policy": "Eine Person bietet der Beratung einen persönlichen Vorteil gegen eine Gegenleistung an.",
    "alarm_when": ["Geld oder Geschenk gegen Freigabe einer Zahlung angeboten"],
    "not_alarm_when": ["Beratung lehnt sofort ab und meldet es", "übliche kleine Aufmerksamkeit"],
    "review_when": ["Zweck des Geschenks bleibt offen"],
    "keywords": ["Gegenleistung", "unter der Hand", "kleines Dankeschön"], "keywords_gsw": ["under de Hand"],
    "basis": "StGB Art. 322octies (Vorschlag)", "team": "compliance_desk",
    "facts": [{"id": "offer", "label": "Persönlicher Vorteil angeboten", "role": "act",
               "de": "Bietet eine Person der Beratung Geld, ein Geschenk oder eine Einladung an?",
               "en": "Does a person offer the advisor money, a gift or an invitation?"},
              {"id": "quid_pro_quo", "label": "Gegenleistung verlangt", "role": "context",
               "de": "Ist das Angebot an eine Gegenleistung der Beratung geknüpft?",
               "en": "Is the offer tied to something the advisor should do in return?"},
              {"id": "refused", "label": "Sofort abgelehnt und gemeldet", "role": "exculpatory",
               "de": "Lehnt die Beratung sofort ab und kündigt eine Meldung an?",
               "en": "Does the advisor refuse at once and announce a report?"}],
    "rules": [{"id": "bestechung.alarm_1", "label": "alarm", "when": "offer = yes and quid_pro_quo = yes",
               "text": "Persönlicher Vorteil gegen Gegenleistung angeboten."},
              {"id": "bestechung.review_1", "label": "review", "when": "offer = yes and quid_pro_quo = unclear",
               "text": "Vorteil angeboten, Zweck unklar."}],
}


def live_bundle(tmp_path: Path) -> tuple[VersionStore, dict]:
    cfg = tmp_path / "config"
    cfg.mkdir(exist_ok=True)
    for name in ("policy_table.yaml", "criteria.yaml", "keywords.json", "routing.yaml"):
        shutil.copy(ROOT / "config" / name, cfg / name)
    store = VersionStore(cfg / "policy_table.yaml", audit_dir=tmp_path / "runs",
                         extras={"criteria": cfg / "criteria.yaml", "keywords": cfg / "keywords.json",
                                 "routing": cfg / "routing.yaml", "tuning": cfg / "tuning.yaml"})
    return store, store.live_bundle()


# --------------------------------------------------------------------------------------------
# rulebook: add a family, switches, diff
# --------------------------------------------------------------------------------------------


def test_add_family_touches_every_file_and_validates(tmp_path):
    _, b = live_bundle(tmp_path)
    new = rb.add_family(b, BRIBERY)
    assert "bestechung" not in b["criteria"]["families"]  # input not mutated
    assert new["criteria"]["families"]["bestechung"]["label"] == "Bestechung"
    fam = new["keywords"]["families"]["bestechung"]
    kw = next(k for k in new["keywords"]["keywords"] if k["id"] == fam["keywords"][0])
    assert kw["de"] == ["Gegenleistung", "unter der Hand", "kleines Dankeschön"] and kw["gsw"] == ["under de Hand"]
    assert new["routing"]["rules"][0] == {"when": {"family": "bestechung"}, "notify": ["compliance_desk"]}
    ft = pe.validate(new["policy_table"]).families["bestechung"]
    assert [r.id for r in ft.rules] == ["bestechung.alarm_1", "bestechung.review_1", "bestechung.no_alert"]
    assert ft.basis.startswith("StGB Art. 322octies")
    with pytest.raises(PolicyTableError, match="gibt es schon"):
        rb.add_family(new, BRIBERY)
    with pytest.raises(PolicyTableError, match="Team"):
        rb.add_family(b, {**BRIBERY, "team": "nobody"})
    with pytest.raises(PolicyTableError, match="Kennung"):
        rb.add_family(b, {**BRIBERY, "id": "Bad Id"})
    assert rb.new_family_id(new, "Bestechung") == "bestechung_2"
    diff = rb.diff_bundle(b, new, profile="recommended")
    assert diff[0] == "Neue Prüfart «Bestechung» (bestechung)"
    assert any(d.startswith("Stichwörter «Bestechung»: + Gegenleistung") for d in diff)
    assert any(d.startswith("Meldeweg «Bestechung» → Compliance Desk") for d in diff)


def test_switches_family_and_check_kind(tmp_path):
    _, b = live_bundle(tmp_path)
    new = copy.deepcopy(b)
    rb.set_family_enabled(new, "access", False)
    rb.set_check_enabled(new, "recommended", "keywords", False)
    assert not rb.family_enabled(new, "access") and rb.checks_off(new, "recommended") == {"keywords"}
    assert rb.checks_off(new, "local") == set()  # profile-scoped
    diff = rb.diff_bundle(b, new, {"access": "Zugang"}, "recommended", {"keywords": "Stichwörter"})
    assert "Prüfart «Zugang» ausgeschaltet" in diff
    assert "Prüfung «Stichwörter» ausgeschaltet (Profil recommended)" in diff
    rb.set_family_enabled(new, "access", True)
    rb.set_check_enabled(new, "recommended", "keywords", True)
    assert new["criteria"] == b["criteria"] and new.get("tuning") in ({}, None)
    # the tuning overlay is what the pipeline reads: weight 0 for this profile
    t = tmp_path / "tuning.yaml"
    rb.set_check_enabled(new, "recommended", "keywords", False)
    t.write_text(rb.dump_text("tuning", new["tuning"]))
    cfg = load_config("recommended", [f"paths.tuning={t}"])
    assert next(c for c in cfg.checks if c["name"] == "keywords")["weight"] == 0.0


# --------------------------------------------------------------------------------------------
# the end-to-end promise: a family that exists only in config flows through facts -> fusion -> routing -> UI
# --------------------------------------------------------------------------------------------


class BriberyLLM:
    """Answers "yes" to every fact question of the bestechung family, "no" elsewhere."""

    def __init__(self):
        self.asked: list[str] = []

    def choice_probs(self, messages, choices):
        user = messages[-1]["content"]
        self.asked.append(user)
        yes = "[bestechung]" in user and "Lehnt" not in user and "refuse" not in user
        return {"yes": 0.95, "no": 0.03, "unknown": 0.02} if yes else {"yes": 0.02, "no": 0.95, "unknown": 0.03}

    def chat(self, messages, **kw):
        return [json.dumps({"reason": "Kunde bietet Geld für eine schnelle Freigabe.", "evidence": ["S002"]})]

    def cache_params(self):
        return {"type": "bribery-test"}

    model_id = "bribery-test"


def bribery_transcript(cid: str) -> Transcript:
    rows = [("advisor", "Grüezi, wie kann ich helfen?"),
            ("customer", "Wenn Sie die Zahlung heute ohne Rückfragen freigeben, gibt es ein kleines Dankeschön unter "
                         "der Hand, tausend Franken."),
            ("advisor", "Das kann ich so nicht machen.")]
    segs = [Segment(id=f"S{i + 1:03d}", start=i * 5.0, end=i * 5.0 + 4.5, role=r, speaker=f"SPK{i % 2}", text=t)
            for i, (r, t) in enumerate(rows)]
    return Transcript(call_id=cid, segments=segs, duration=15.0, language="de")


def test_new_family_defined_only_in_config_flows_through_facts_fusion_routing_and_ui(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from ui_fixtures import REVIEW_ID, write_fixture_env

    from callguard.ui import backend as be

    env = write_fixture_env(tmp_path, config="recommended")
    cfg_dir = tmp_path / "config"
    for name in ("policy_table.yaml", "routing.yaml"):
        shutil.copy(ROOT / "config" / name, cfg_dir / name)
    store = VersionStore(cfg_dir / "policy_table.yaml", audit_dir=env.runs_dir,
                         extras={"criteria": env.criteria, "keywords": env.keywords, "routing": cfg_dir / "routing.yaml"})
    store.ensure_initial()
    v = store.save_draft(rb.add_family(store.live_bundle(), BRIBERY), "Anna", "Neue Prüfart Bestechung")
    assert set(v.meta["changed_files"]) == {"policy_table", "criteria", "keywords", "routing"}
    store.approve(v.n, "Ben")  # only now the pipeline's files contain the family

    sets = [*env.sets, f"checks.2.policy_table={cfg_dir / 'policy_table.yaml'}", f"paths.tuning={tmp_path / 't.yaml'}"]
    cfg = load_config("recommended", sets)
    ctx = Context(cfg)
    fams = ctx.families()
    assert "bestechung" in [f.id for f in fams]  # families.py: criteria + keyword list, no code
    llm = BriberyLLM()
    monkeypatch.setattr(ctx, "llm", lambda name="default": llm)
    check = FactSheetCheck(ctx, policy_table=str(cfg_dir / "policy_table.yaml"))
    t = bribery_transcript(REVIEW_ID)
    res = check.run(t, fams)
    fs = res.family_scores["bestechung"]
    assert fs.detail["rule"]["id"] == "bestechung.alarm_1" and fs.verdict == "present"
    assert any("[bestechung]" in a for a in llm.asked)
    kw_check = registry.create("check", next(c for c in cfg.checks if c["type"] == "keywords"), ctx=ctx)
    kw = kw_check.run(t, fams)
    assert kw.family_scores["bestechung"].score > 0  # the new keyword family is searched too

    fusion = registry.create("fusion", cfg.fusion, ctx=ctx)
    decision = fusion.decide(t, {"facts": res, "keywords": kw}, fams,
                             {"weights": {c["name"]: c.get("weight", 1.0) for c in cfg.checks}})
    assert decision.label == "alarm" and decision.top_family == "bestechung"
    result = CallResult(call_id=REVIEW_ID, transcript=t, checks={"facts": res, "keywords": kw}, decision=decision,
                        config_name="recommended")
    r = route(result, RoutingConfig.load(cfg_dir / "routing.yaml"))
    assert "compliance_desk" in [x.id for x in r.to] and "bestechung" in r.families

    env.result_path(REVIEW_ID).write_text(result.model_dump_json(indent=1))
    monkeypatch.setenv(be.ENV_ARGS, " ".join(["--config", "recommended", *(f"--set {shlex.quote(s)}" for s in sets)]))
    app = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=120)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    assert any(tg.label == "Bestechung" for tg in at.sidebar.toggle)  # sidebar family switches
    inbox = at.dataframe[0].value
    row = inbox[inbox["Anruf"] == REVIEW_ID].iloc[0]
    assert "Bestechung" in str(row.to_dict())
    at.switch_page("views/rules.py").run()
    assert not at.exception, [e.message for e in at.exception]
    at.radio(key="rw_section").set_value("switches").run()
    assert any("Bestechung" in m.value for m in at.markdown)


# --------------------------------------------------------------------------------------------
# family drafter (canned LLM)
# --------------------------------------------------------------------------------------------


class Canned:
    def __init__(self, *answers: str):
        self.answers = list(answers)
        self.calls: list[dict] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        self.calls.append({"messages": messages, "json_schema": json_schema})
        return [self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]] * n


def llm_family(**over) -> dict:
    """What Qwen2.5-7B answered live (shortened), incl. its typical slips."""
    obj = {"id": "bestechung", "label": "bestechung", "policy": "Eine Person bietet einen Vorteil an.",
           "alarm_when": ["Vorteil gegen Freigabe"], "not_alarm_when": ["Beratung lehnt ab"], "review_when": [],
           "keywords": ["Gegenleistung", "Dankeschön"], "basis": "StGB Art. 322ter ff. (Bestechung)",
           "team": "compliance_desk",
           "facts": [{"id": "act", "label": "persönlicher_vorteil_angeboten", "role": "act",
                      "de": "Bietet eine Person der Beratung einen persönlichen Vorteil an?",
                      "en": "Does a person offer the advisor a personal benefit?"},
                     {"id": "context", "label": "Gegenleistung verlangt", "role": "context",
                      "de": "Ist das Angebot an eine Gegenleistung geknüpft?", "en": "Is it tied to a favour?"}],
           "rules": [{"label": "alarm", "when": "act = yes and context = yes", "text": "Bestechung."},
                     {"label": "review", "when": "act = yes and context = unclear", "text": "Zweck unklar."},
                     {"label": "no_alert", "when": "act = no", "text": "Keine Bestechung."}],
           "note": "Schwelle für kleine Geschenke prüfen."}
    obj.update(over)
    return obj


def test_family_drafter_valid(tmp_path):
    _, b = live_bundle(tmp_path)
    teams = {"compliance_desk": "Compliance Desk", "aml_desk": "AML"}
    llm = Canned(json.dumps(llm_family()))
    d = rd.draft_family(llm, b, "Alarm, wenn jemand dem Berater einen Vorteil anbietet", None, teams, name="Bestechung")
    assert llm.calls[0]["json_schema"]["properties"]["team"]["enum"] == list(teams)
    assert "StGB Art. 322ter" in llm.calls[0]["messages"][0]["content"]
    s = d.spec
    assert (s["id"], s["label"], s["team"]) == ("bestechung", "Bestechung", "compliance_desk")
    assert s["facts"][0]["label"] == "Persönlicher vorteil angeboten"  # no snake_case reaches the officer
    assert s["basis"] == "StGB Art. 322ter ff. (Bestechung) (Vorschlag)"
    assert [r["id"] for r in s["rules"]] == ["bestechung.alarm_1", "bestechung.review_1", "bestechung.no_alert_1"]
    pe.validate(rb.add_family(b, s)["policy_table"])


def test_family_drafter_repairs_and_rejects(tmp_path):
    _, b = live_bundle(tmp_path)
    bad = llm_family(rules=[{"label": "alarm", "when": "nonsense = yes", "text": "x"}])
    d = rd.draft_family(Canned(json.dumps(bad), json.dumps(llm_family())), b, "Bestechung")
    assert d.spec["rules"]
    with pytest.raises(rd.DraftError, match="Keine gültige Regel"):
        rd.draft_family(Canned(json.dumps(bad)), b, "Bestechung")
    with pytest.raises(rd.DraftError, match="kein gültiges JSON"):
        rd.draft_family(Canned("Hier ist die Prüfart: Bestechung"), b, "Bestechung")
    with pytest.raises(rd.DraftError, match="keine Fakten"):
        rd.validate_family(llm_family(facts=[]), b)
    d = rd.validate_family(llm_family(id="trade", team="ghost"), b)  # existing id renamed, unknown team dropped
    assert d.spec["id"] == "trade_2" and d.spec["team"] == "" and d.warnings
    assert rd.blank_family(b, "Marktmanipulation").spec["id"] == "marktmanipulation"
    pe.validate(rb.add_family(b, rd.blank_family(b, "Marktmanipulation").spec)["policy_table"])


# --------------------------------------------------------------------------------------------
# what-if for a new family + bundle versioning
# --------------------------------------------------------------------------------------------


def test_whatif_new_family_needs_probes_then_decides(tmp_path):
    from test_rules_editor import C17, family_fusion, stored_call

    table = load_policy_table(SHIPPED)
    _, b = live_bundle(tmp_path)
    draft = pe.validate(rb.add_family(b, BRIBERY)["policy_table"])
    calls = {"C17": stored_call("C17", C17, table)}
    assert wi.probe_tasks(calls, draft, "en") == []  # not asked to look for new families: nothing
    tasks = wi.probe_tasks(calls, draft, "en", {"bestechung"})
    assert tasks == [("C17", "bestechung", f) for f in ("offer", "quid_pro_quo", "refused")]
    _, out = wi.redecide_result(calls["C17"], draft)
    assert "bestechung" not in out  # no answers yet: the new family is not decided (not "unclear" everywhere)
    yes, no = {"yes": 0.9, "no": 0.05, "unclear": 0.05}, {"yes": 0.05, "no": 0.9, "unclear": 0.05}
    probes = {tasks[0]: yes, tasks[1]: yes, tasks[2]: no}
    r, out = wi.redecide_result(calls["C17"], draft, probes=probes, lang="en")
    assert out["bestechung"].rule == "bestechung.alarm_1"
    assert r.checks["facts"].family_scores["bestechung"].detail["new_family"] is True


def test_bundle_versions_write_only_changed_files_and_detect_conflicts(tmp_path):
    store, b = live_bundle(tmp_path)
    v1 = store.ensure_initial()
    assert v1.stored("keywords") and "tuning" in v1.meta["absent"]
    kw_before = store.paths["keywords"].read_text()
    off = copy.deepcopy(b)
    rb.set_check_enabled(off, "recommended", "patterns", False)
    v2 = store.save_draft(off, "Anna", "Muster aus")
    assert v2.meta["changed_files"] == ["tuning"] and not store.paths["tuning"].exists()
    store.approve(2, "Ben")
    assert yaml.safe_load(store.paths["tuning"].read_text()) == {
        "profiles": {"recommended": {"weights": {"patterns": 0.0}}}}
    assert store.paths["keywords"].read_text() == kw_before  # untouched file: byte-identical
    assert store.ensure_initial().n == 2  # live == version: no "external" snapshot

    v3 = store.save_draft(rb.add_family(store.live_bundle(), BRIBERY), "Anna")
    store.paths["keywords"].write_text(kw_before.replace("Nicht öffentliche Information", "Nicht öffentlich"))
    with pytest.raises(FourEyesError, match="Stichwortliste"):
        store.approve(v3.n, "Ben")  # the keyword page saved meanwhile: no silent overwrite
    assert "bestechung" not in store.paths["criteria"].read_text()
    v4 = store.ensure_initial()
    assert v4.meta["kind"] == "external" and v4.meta["changed_files"] == ["keywords"]
    v5 = store.save_draft(rb.add_family(store.live_bundle(), BRIBERY), "Anna")
    store.approve(v5.n, "Ben")
    fams = load_families(store.paths["keywords"], store.paths["criteria"])
    assert "bestechung" in [f.id for f in fams]
    assert "Nicht öffentlich\"" in store.paths["keywords"].read_text()  # the external edit survived

    v6 = store.rollback(2, "Ben")  # back to before the new family (still four eyes)
    with pytest.raises(FourEyesError):
        store.approve(v6.n, "Ben")
    store.approve(v6.n, "Anna")
    assert "bestechung" not in store.paths["criteria"].read_text()
    kinds = [e["kind"] for e in audit.read_events(store.audit_dir)]
    assert kinds.count("policy_approved") == 3 and "policy_snapshot" in kinds


def test_rules_page_switches_and_new_family_wizard(tmp_path, monkeypatch):
    """Regelwerk: check kind + Prüfart switches with live preview, «Neue Prüfart» without LLM, four-eyes approval."""
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from test_rules_editor import C17, stored_call
    from ui_fixtures import REVIEW_ID, write_fixture_env

    from callguard.ui import backend as be

    env = write_fixture_env(tmp_path, config="recommended")
    active = tmp_path / "config" / "policy_table.yaml"
    shutil.copy(SHIPPED, active)
    tuning = tmp_path / "tuning.yaml"
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tuning} --set checks.2.policy_table={active}")
    monkeypatch.setenv("CALLGUARD_USER", "Anna")
    path = env.result_path(REVIEW_ID)
    r = CallResult.model_validate_json(path.read_text())
    r.checks["facts"] = stored_call(REVIEW_ID, C17, load_policy_table(SHIPPED)).checks["facts"]
    path.write_text(r.model_dump_json(indent=1))

    app = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=120)
    at.run()
    at.switch_page("views/rules.py").run()
    at.radio(key="rw_section").set_value("switches").run()
    assert not at.exception, [e.message for e in at.exception]
    at.toggle(key="rw_famon_access_True").set_value(False).run()
    at.toggle(key="rw_chkon_patterns_True").set_value(False).run()
    assert not at.exception, [e.message for e in at.exception]
    md = " ".join(m.value for m in at.markdown)
    assert "Mit der Arbeitskopie ändern sich" in md

    at.radio(key="rw_section").set_value("family").run()
    at.text_input(key="rw_fam_name").set_value("Marktmanipulation").run()
    at.button(key="rw_fam_blank_btn").click().run()
    assert any("Vorlage ohne KI" in m.value for m in at.markdown)
    at.text_area(key="rw_fd_kw").set_value("Kurs pushen, Scheingeschäft").run()
    at.button(key="rw_fd_apply").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.radio(key="rw_section").value == "preview"
    md = " ".join(m.value for m in at.markdown)
    assert "Neue Prüfart «Marktmanipulation»" in md and "Prüfart «Zugangsinformation preisgegeben» ausgeschaltet" in md
    assert "Prüfung «Muster \\(Ziffernfolgen, Codes\\)» ausgeschaltet" in md
    assert "marktmanipulation" not in env.criteria.read_text()  # nothing live yet

    next(b for b in at.button if b.label.startswith("Als Entwurf speichern")).click().run()
    at.radio(key="rw_section").set_value("versions").run()
    at.text_input(key="rw_appr_2").set_value("Ben").run()
    next(b for b in at.button if b.key == "rw_ok_2").click().run()
    assert not at.exception, [e.message for e in at.exception]
    crit = yaml.safe_load(env.criteria.read_text())["families"]
    assert crit["marktmanipulation"]["label"] == "Marktmanipulation" and crit["access"]["enabled"] is False
    assert "marktmanipulation" in json.loads(env.keywords.read_text())["families"]
    assert "marktmanipulation" in load_policy_table(active).families
    assert yaml.safe_load(tuning.read_text()) == {"profiles": {"recommended": {"weights": {"patterns": 0.0}}}}
    ev = audit.read_events(env.runs_dir, kind="policy_approved")[-1]
    assert set(ev["files"]) == {"policy_table", "criteria", "keywords", "tuning"}
