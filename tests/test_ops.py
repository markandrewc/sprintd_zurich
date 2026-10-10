"""Operations stretch goals, offline: audit log, routing + notify sink, entities, cross-call patterns,
officer feedback -> suggestions -> tuning overlay (config + provenance), and their CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from callguard import audit, registry, routing
from callguard import feedback as fb
from callguard import patterns as pt
from callguard.checks.entities import EntityCheck, entities_of, extract_entities
from callguard.config import load_config
from callguard.context import Context
from callguard.pipeline import Pipeline
from callguard.sinks.json_dir import JsonDirSink
from callguard.sinks.notify import NotifySink, read_outbox
from callguard.types import (
    CallResult,
    CheckResult,
    Decision,
    FamilyScore,
    Finding,
    FusedFamily,
    Passage,
    Segment,
    Transcript,
)

DIRECTORY = {
    "supervisors": {"SUP-ANL": {"name": "Beat Zürcher", "unit": "Anlageberatung"}},
    "advisors": {"A02": {"name": "Claudia Frei", "unit": "Anlageberatung", "supervisor": "SUP-ANL"},
                 "A06": {"name": "Sonja Hess", "unit": "Online-Service", "supervisor": "SUP-ANL"}},
}


def sets(tmp_path: Path, *extra: str) -> list[str]:
    return [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}",
            f"paths.tuning={tmp_path / 'tuning.yaml'}", *extra]


def directory(tmp_path: Path) -> routing.Directory:
    p = tmp_path / "directory.yaml"
    p.write_text(yaml.safe_dump(DIRECTORY, allow_unicode=True))
    return routing.Directory.load(p)


def transcript(call_id: str, advisor: str = "Claudia Frei", customer: str = "Aebi", company: str = "Rigi Sensorik",
               extra: str = "Ich möchte vor der Meldung kaufen.") -> Transcript:
    return Transcript(call_id=call_id, segments=[
        Segment(id="T001", start=0, end=4, role="advisor", text=f"Grüezi Frau {customer}, da isch d {advisor}. Was händ Sie?"),
        Segment(id="T002", start=4, end=9, role="customer", text=f"Es gaht um d {company}. {extra}"),
    ])


def make_result(call_id: str, label: str = "alarm", family: str = "trade", score: float = 0.9,
                t: Transcript | None = None, keyword: str | None = None, audio_path: str | None = None) -> CallResult:
    t = t or transcript(call_id)
    passages = [] if label == "no_alert" else [
        Passage(family=family, family_label="Insiderhandel (Information und Kaufwunsch)", start=4, end=9,
                segment_ids=["T002"], score=score, reasons=["llm_judge: Kaufwunsch vor der Meldung"],
                checks=["llm_judge"], text="Ich möchte vor der Meldung kaufen.", snippet_path="/x/00_trade_4s.wav")]
    d = Decision(label=label, score=score, uncertainty=0.1, threshold=0.55, passages=passages,
                 top_family=family if label != "no_alert" else None, reasons=[f"{label}: Score {score:.2f}"],
                 families={family: FusedFamily(family=family, label="Insiderhandel (Information und Kaufwunsch)",
                                               score=score, uncertainty=0.1)})
    checks = {"llm": CheckResult(check="llm", type="fake", family_scores={family: FamilyScore(score=score)})}
    if keyword:
        checks["keywords"] = CheckResult(check="keywords", type="keywords", findings=[
            Finding(check="keywords", family=family, score=0.6, segment_ids=["T002"],
                    detail={"keyword_id": keyword, "negated": False})])
    return CallResult(call_id=call_id, transcript=t, checks=checks, decision=d, config_name="base",
                      audio_path=audio_path)


# --------------------------------------------------------------------------------------------
# audit
# --------------------------------------------------------------------------------------------


def test_audit_log_and_sink(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLGUARD_USER", "officer.a")
    ev = audit.log_event(tmp_path, "keywords_save", family="trade", keyword_ids=["K01"])
    assert ev["user"] == "officer.a" and ev["kind"] == "keywords_save"
    (tmp_path / audit.AUDIT_FILE).open("a").write('{"torn line\n')  # a crash mid-write is skipped
    ctx = Context(load_config("base", sets(tmp_path)))
    registry.create("sink", {"type": "audit"}, ctx=ctx).emit(make_result("X-K1"))
    events = audit.read_events(ctx.runs_dir)
    assert [e["kind"] for e in events] == ["decision"]
    assert events[0]["label"] == "alarm" and events[0]["user"] == "pipeline" and events[0]["call_id"] == "X-K1"
    assert audit.read_events(tmp_path, kind="keywords_save")[0]["keyword_ids"] == ["K01"]


# --------------------------------------------------------------------------------------------
# routing + notify
# --------------------------------------------------------------------------------------------


def test_route_family_review_supervisor_and_pattern(tmp_path):
    cfg, d = routing.RoutingConfig.load(), directory(tmp_path)
    ent = entities_of(make_result("A-K1"), d)
    r = routing.route(make_result("A-K1"), cfg, d, entities=ent)
    assert [x.id for x in r.to] == ["market_surveillance"]
    assert [x.name for x in r.cc] == ["Beat Zürcher"] and r.advisor["id"] == "A02"

    rev = routing.route(make_result("B-K1", label="review", family="access"), cfg, d, entities=ent)
    assert {x.id for x in rev.to} == {"fraud_desk", "compliance_desk"} and rev.cc == []  # no cc on review

    assert not routing.route(make_result("C-K1", label="no_alert"), cfg, d, entities=ent).routed

    flags = {"flags": [{"kind": "repeat_advisor", "subject_type": "advisor", "subject": "A02", "calls": []}]}
    rp = routing.route(make_result("D-K1", label="review", family="numbers"), cfg, d, entities=ent, analysis=flags)
    assert rp.patterns == ["repeat_advisor"] and "compliance_desk" in {x.id for x in rp.to}
    assert rp.cc and "rule pattern=repeat_advisor" in rp.cc[0].why[0]

    fb_cfg = routing.RoutingConfig.from_dict({"teams": {"desk": {"name": "Desk"}}, "rules": [], "fallback": ["desk"]})
    assert [x.id for x in routing.route(make_result("E-K1"), fb_cfg).to] == ["desk"]
    with pytest.raises(ValueError, match="unknown teams"):
        routing.RoutingConfig.from_dict({"teams": {}, "rules": [{"when": {"family": "trade"}, "notify": ["nope"]}]})


def test_message_has_link_passages_and_snippets(tmp_path):
    cfg = load_config("base", sets(tmp_path, "app.base_url=http://cg.local:8501/", "snippets.link_pad=10"))
    res = make_result("Stufe1_D02-K1")
    r = routing.route(res, routing.RoutingConfig.load(), directory(tmp_path), entities=entities_of(res))
    msg = routing.build_message(res, r, cfg)
    assert msg["link"] == "http://cg.local:8501/?call=Stufe1_D02-K1&t=0"
    p = msg["passages"][0]
    assert p["time"] == "00:04-00:09" and p["reasons"] and p["snippet_path"] == "/x/00_trade_4s.wav"
    assert msg["subject"].startswith("[ALARM] Insiderhandel") and "Claudia Frei" in msg["body"]


def test_notify_sink_outbox_dedupe_and_audit(tmp_path, monkeypatch):
    ctx = Context(load_config("base", sets(tmp_path)))
    posted = []
    monkeypatch.setattr("callguard.sinks.notify.httpx.post",
                        lambda url, json, timeout: posted.append((url, json)) or type("R", (), {"status_code": 200})())
    sink = NotifySink(ctx, channels=["outbox", "webhook"], webhook_url="http://hook.local/x")
    res = make_result("A-K1")
    JsonDirSink(ctx).emit(res)
    sink.emit(res)
    sink.emit(res)  # same decision again (re-run batch): not queued twice
    sink.emit(make_result("N-K1", label="no_alert"))  # not routed
    out = read_outbox(ctx.runs_dir)
    assert len(out) == 1 and out[0]["call_id"] == "A-K1" and out[0]["to"][0]["id"] == "market_surveillance"
    assert len(posted) == 2 and posted[0][0] == "http://hook.local/x"
    assert [e["kind"] for e in audit.read_events(ctx.runs_dir)] == ["notification", "notification"]
    with pytest.raises(ValueError, match="channels"):
        NotifySink(ctx, channels=["pigeon"])


# --------------------------------------------------------------------------------------------
# entities
# --------------------------------------------------------------------------------------------


def test_entities_greetings_directory_companies_and_sidecar(tmp_path):
    d = directory(tmp_path)
    e = extract_entities(transcript("A-K1"), d)
    assert e["advisor"]["name"] == "Claudia Frei" and e["advisor"]["id"] == "A02"
    assert e["customer"]["name"] == "Frau Aebi" and e["company_keys"] == ["rigi sensorik"]

    asr = Transcript(call_id="B", segments=[  # Standard German ASR output, no roles: first speaker = advisor
        Segment(id="S0", start=0, end=2, speaker="SPK0", text="Guten Tag, hier ist die Andrea Moser."),
        Segment(id="S1", start=2, end=4, speaker="SPK1", text="Mein Name ist Peter Wyss, es geht um die Limmat Energie."),
    ])
    e = extract_entities(asr, d)
    assert e["advisor"]["name"] == "Andrea Moser" and e["advisor"]["id"] is None
    assert e["customer"]["name"] == "Peter Wyss" and e["company_keys"] == ["limmat energie"]

    no_greeting = Transcript(call_id="C", segments=[
        Segment(id="T001", start=0, end=2, role="advisor", text="Grüezi, Online-Service, Sonja Hess. Was cha ich mache?")])
    assert extract_entities(no_greeting, d)["advisor"]["id"] == "A06"

    wav = tmp_path / "call.wav"
    (tmp_path / "call.meta.json").write_text(json.dumps({"advisor_id": "A06", "customer_id": "C-77", "line": "+41"}))
    res = make_result("A-K1", audio_path=str(wav))
    ent = entities_of(res, d)
    assert ent["advisor"]["source"] == "sidecar" and ent["advisor_key"] == "A06" and ent["customer_key"] == "C-77"


def test_entity_check_scores_nothing_and_is_registered(tmp_path):
    assert registry.resolve("check", "entities") is EntityCheck
    r = EntityCheck(None, name="entities", weight=0).run(transcript("A-K1"), [])
    assert r.family_scores == {} and r.findings == [] and r.meta["entities"]["advisor"]["name"] == "Claudia Frei"
    assert r.meta["cacheable"] is False


# --------------------------------------------------------------------------------------------
# patterns
# --------------------------------------------------------------------------------------------


def test_wilson_lower():
    assert pt.wilson_lower(0, 0) == 0.0
    assert pt.wilson_lower(1, 1) == pytest.approx(0.2065, abs=1e-3)
    assert pt.wilson_lower(4, 4) == pytest.approx(0.5101, abs=1e-3)


def test_patterns_flags_repeat_advisor_and_company_chain(tmp_path):
    d = directory(tmp_path)
    names = ["Aebi", "Wyss", "Roth", "Huber", "Keller", "Gerber", "Suter", "Meier", "Graf", "Ott"]
    rs = [make_result(f"Bad{i}-K1", t=transcript(f"Bad{i}", customer=names[i])) for i in range(5)]
    rs += [make_result(f"Ok{i}-K1", label="no_alert", score=0.1,
                       t=transcript(f"Ok{i}", advisor="Sonja Hess", customer=names[i], company="Albis Optik"))
           for i in range(10)]
    a = pt.analyze(rs, directory=d)
    kinds = {(f["kind"], f["subject"]) for f in a["flags"]}
    assert ("repeat_advisor", "A02") in kinds and not any(s == "A06" for _, s in kinds)
    assert ("company_across_customers", "rigi sensorik") in kinds
    adv = {r["key"]: r for r in a["advisors"]}
    assert adv["A02"]["calls"] == 5 and adv["A02"]["alarms"] == 5 and adv["A06"]["flagged"] == 0
    # one flagged call is never a pattern (min_calls), clean + noisy recordings count once
    assert pt.analyze(rs[:1] + rs[5:], directory=d)["flags"] == []
    assert len(pt.one_per_dialogue([make_result("X-K1"), make_result("X-K2"), make_result("Y-K1")])) == 2
    assert "repeat_advisor" in pt.render_markdown(a)


# --------------------------------------------------------------------------------------------
# feedback -> suggestion -> tuning overlay
# --------------------------------------------------------------------------------------------


def test_feedback_labels():
    F = fb.FeedbackItem
    items = [F(call_id="a", verdict="false_alarm", ts="1"), F(call_id="a", verdict="confirmed", ts="2", label_seen="alarm"),
             F(call_id="b", verdict="missed"), F(call_id="c", verdict="should_review"),
             F(call_id="d", verdict="not_review"),
             F(call_id="e", verdict="false_alarm", passage_index=0, ts="1"),
             F(call_id="e", verdict="confirmed", passage_index=1, ts="2"),
             F(call_id="f", verdict="false_alarm", passage_index=0)]
    labels = fb.labels_from_feedback(items, {"e": "alarm"})
    assert labels == {"a": "alarm", "b": "alarm", "c": "review", "d": "no_alert", "e": "alarm", "f": "no_alert"}


def _pipe(tmp_path: Path, *extra: str) -> Pipeline:
    return Pipeline(load_config("base", sets(tmp_path, "checks=[]", "sinks=[]", *extra)))


def test_suggest_threshold_and_keyword_precision(tmp_path):
    pipe = _pipe(tmp_path)
    scores = {"p1": 0.35, "p2": 0.3, "p3": 0.6, "n1": 0.1, "n2": 0.05, "n3": 0.12}
    results = [make_result(f"{k}-K1", label="alarm" if v >= 0.55 else "no_alert", score=v,
                           keyword="K05" if k.startswith("n") else "K01") for k, v in scores.items()]
    items = [fb.FeedbackItem(call_id=f"{k}-K1", verdict="missed" if k.startswith("p") else "confirmed",
                             label_seen="no_alert" if k.startswith("n") else None) for k in scores]
    s = fb.suggest(pipe, results, items, thresholds=[0.3, 0.4, 0.55, 0.7])
    assert s["n_labelled"] == 6 and s["sources"] == {"feedback": 6, "ground_truth": 0} and s["warning"]
    assert s["current"]["fn"] >= 2 and s["suggestion"]["fn"] == 0 and s["suggestion"]["fp"] == 0
    assert s["suggestion"]["threshold"] < 0.55 and s["delta"]["fn"] < 0
    kw = {k["keyword"]: k for k in s["keywords"]}
    assert kw["K05"]["suggest_disable"] and "K05" in kw["K05"]["advice"] and not kw["K01"]["suggest_disable"]
    assert s["checks"][0]["check"] == "llm" and s["checks"][0]["separation"] > 0
    assert fb.suggest(pipe, results, [])["warning"]  # nothing labelled: says so, no crash


def test_tuning_overlay_roundtrip(tmp_path):
    tp = tmp_path / "tuning.yaml"
    base = load_config("base", sets(tmp_path))
    assert base.tuning is None and base.fusion["threshold"] == 0.55  # absent file: no change
    info = fb.apply_tuning(tp, "base", threshold=0.42, weights={"keywords": 0.5}, runs_dir=tmp_path / "runs",
                           reason="test")
    assert info["new_hash"] and info["after"]["fusion"] == {"threshold": 0.42}
    cfg = load_config("base", sets(tmp_path))
    assert cfg.fusion["threshold"] == 0.42 and cfg.tuning["hash"] == info["new_hash"]
    assert next(c for c in cfg.checks if c["name"] == "keywords")["weight"] == 0.5
    assert load_config("base", sets(tmp_path, "fusion.threshold=0.6")).fusion["threshold"] == 0.6  # --set wins
    assert load_config("local", sets(tmp_path)).tuning is None  # scoped to its profile
    prov = Pipeline(load_config("base", sets(tmp_path, "checks=[]", "sinks=[]"))).provenance({})
    assert prov["tuning"]["hash"] == info["new_hash"]
    ev = audit.read_events(tmp_path / "runs", kind="tuning_save")
    assert ev and ev[0]["reason"] == "test" and ev[0]["new_hash"] == info["new_hash"]
    fb.apply_tuning(tp, "base", clear=True)
    assert load_config("base", sets(tmp_path)).tuning is None
    with pytest.raises(ValueError):
        fb.apply_tuning(tp, "base", threshold=1.5)


# --------------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------------


def test_cli_route_feedback_patterns(tmp_path):
    from callguard import cli

    runner = CliRunner()
    opts = ["-c", "base", *(x for s in sets(tmp_path) for x in ("--set", s))]
    ctx = Context(load_config("base", sets(tmp_path)))
    for r in [make_result("Stufe1_D02-K1"), make_result("Stufe1_D03-K1", label="no_alert", score=0.1)]:
        JsonDirSink(ctx).emit(r)

    out = runner.invoke(cli.app, ["route", "Stufe1_D02-K1", "--send", *opts])
    assert out.exit_code == 0, out.output
    assert "Market Surveillance" in out.output and len(read_outbox(ctx.runs_dir)) == 1
    out = runner.invoke(cli.app, ["route", "--all", *opts])
    assert out.exit_code == 0 and "Stufe1_D03" in out.output
    assert runner.invoke(cli.app, ["route", "Nope-K1", *opts]).exit_code == 1

    out = runner.invoke(cli.app, ["feedback", "add", "Stufe1_D03-K1", "missed", "-m", "Kaufwunsch überhört", *opts])
    assert out.exit_code == 0, out.output
    assert fb.load(ctx.runs_dir)[0].label_seen == "no_alert"
    assert runner.invoke(cli.app, ["feedback", "add", "Stufe1_D03-K1", "maybe", *opts]).exit_code == 2
    out = runner.invoke(cli.app, ["feedback", "list", *opts])
    assert out.exit_code == 0 and "missed" in out.output
    out = runner.invoke(cli.app, ["feedback", "suggest", "--set", "checks=[]", *opts])
    assert out.exit_code == 0, out.output
    out = runner.invoke(cli.app, ["feedback", "apply", "--threshold", "0.4", "-m", "pilot", *opts])
    assert out.exit_code == 0, out.output
    assert load_config("base", sets(tmp_path)).fusion["threshold"] == 0.4

    out = runner.invoke(cli.app, ["patterns", "--out", str(tmp_path / "p.md"), *opts])
    assert out.exit_code == 0, out.output
    assert "Claudia Frei" in (tmp_path / "p.md").read_text()


# --------------------------------------------------------------------------------------------
# UI pages + detail panels (Streamlit AppTest on the UI fixtures)
# --------------------------------------------------------------------------------------------


def test_ops_pages_and_detail_panels_render(tmp_path, monkeypatch):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from ui_fixtures import ALARM_ID, write_fixture_env

    from callguard.ui import backend as be

    env = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tmp_path / 'tuning.yaml'}")
    app = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
    fb.add(env.runs_dir, fb.FeedbackItem(call_id=ALARM_ID, verdict="confirmed", label_seen="alarm"))

    def run(page=None, query=None):
        at = AppTest.from_file(str(app), default_timeout=90)
        for k, v in (query or {}).items():
            at.query_params[k] = v
        at.run()
        if page:
            at.switch_page(f"views/{page}.py").run()
        assert not at.exception, [e.message for e in at.exception]
        return at

    for page in ("notifications", "feedback", "patterns", "audit"):
        at = run(page)
        assert at.title, page
    at = run("notifications")
    send = [b for b in at.button if "offene Meldung" in b.label]
    if send:
        send[0].click().run()
        assert read_outbox(env.runs_dir)
    at = run("detail", query={"call": ALARM_ID})
    expanders = " | ".join(e.label for e in at.expander)
    assert "Rückmeldung" in expanders and "Herkunft" in expanders and "Personen" in expanders, expanders
    # schema-2 form (callguard.ui.panels.feedback): verdict on the call + first passage, one submit
    next(x for x in at.radio if x.key == f"cg_fb2_v_{ALARM_ID}").set_value("no_violation")
    next(x for x in at.radio if x.key == f"cg_fb2_p_{ALARM_ID}_0").set_value("not_applies")
    next(b for b in at.button if b.label == "Rückmeldung speichern").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert [i.verdict for i in fb.load(env.runs_dir)][-2:] == ["no_violation", "not_applies"]
    assert fb.labels_from_feedback(fb.load(env.runs_dir))[ALARM_ID] == "no_alert"
