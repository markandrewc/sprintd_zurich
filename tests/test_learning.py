"""Learning from officer decisions (docs/LEARNING.md), offline: schema-2 feedback capture + legacy
compatibility, split hygiene of the learning export (case calls evaluation-only, twins together, demo never
trainable), readiness math, threshold re-fit with CV + CI, the four-eyes proposal path with rollback, the
CLI and an AppTest smoke of the panel and both pages."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from callguard import audit
from callguard import feedback as fb
from callguard.checks.facts import decide_family, load_policy_table
from callguard.config import load_config
from callguard.data import Call, Expected
from callguard.learning import demo, export, hygiene, insights, recalibrate, records
from callguard.learning import proposals as pr
from callguard.pipeline import Pipeline
from callguard.splits import Splits
from callguard.types import (
    CallResult,
    CheckResult,
    Decision,
    FamilyScore,
    FusedFamily,
    Passage,
    Segment,
    Transcript,
)

C17_ACCESS = {
    "spoken": ("yes", {"yes": 0.92, "no": 0.03, "unclear": 0.05}),
    "current": ("unclear", {"yes": 0.0, "no": 0.0, "unclear": 1.0}),
    "validity_open": ("yes", {"yes": 0.99, "no": 0.0, "unclear": 0.01}),
    "expired_or_sample": ("no", {"yes": 0.0, "no": 0.9, "unclear": 0.1}),
    "asked_by_advisor": ("no", {"yes": 0.0, "no": 0.9, "unclear": 0.1}),
}

# a small synthetic split: dev folds 0/1, holdout H1; twin group C01+C02
SPLITS = Splits(holdout=["Stufe1_D09"], dev_folds={0: ["Stufe1_D01", "Stufe2_C01", "Stufe2_C02"], 1: ["Stufe1_D02"]},
                groups={"Stufe2_C01+Stufe2_C02": ["Stufe2_C01", "Stufe2_C02"]})


def sets(tmp_path: Path, *extra: str) -> list[str]:
    return [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}",
            f"paths.tuning={tmp_path / 'tuning.yaml'}", *extra]


@pytest.fixture(scope="module")
def table():
    return load_policy_table("config/policy_table.yaml")


def facts_check(table, values: dict | None = None) -> CheckResult:
    ft = table.families["access"]
    vals = {k: v for k, (v, _) in C17_ACCESS.items()}
    vals.update(values or {})
    probs = {k: p for k, (_, p) in C17_ACCESS.items()}
    fd = decide_family(ft, vals, probs)
    detail = {"decision": fd.label, "facts": {k: {"label": ft.fact(k).label, "role": ft.fact(k).role, "value": vals[k],
                                                  "p": probs[k], "question": ft.fact(k).question("en")} for k in vals},
              "rule": {"id": fd.rule.id if fd.rule else None, "label": fd.label}}
    return CheckResult(check="facts", type="facts", meta={"model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
                                                          "policy_table": {"path": "config/policy_table.yaml",
                                                                           "hash": "abc123"}},
                       family_scores={"access": FamilyScore(score=fd.score, confidence=fd.confidence, detail=detail)})


def make_result(call_id: str, table, label: str = "review", score: float = 0.5, values: dict | None = None) -> CallResult:
    t = Transcript(call_id=call_id, segments=[
        Segment(id="S001", start=0, end=4, role="advisor", text="Grüezi, wie kann ich helfen?"),
        Segment(id="S002", start=4, end=9, role="customer", text="Mein Code ist 4711, ob der noch gilt weiss ich nicht.")])
    passages = [] if label == "no_alert" else [Passage(family="access", family_label="Zugang", start=4, end=9,
                                                       score=score, text="Mein Code ist 4711")]
    d = Decision(label=label, score=score, uncertainty=0.1, threshold=0.55, passages=passages,
                 top_family="access" if label != "no_alert" else None,
                 families={"access": FusedFamily(family="access", label="Zugangsinformation preisgegeben", score=score,
                                                 uncertainty=0.1)})
    return CallResult(call_id=call_id, transcript=t, checks={"facts": facts_check(table, values)}, decision=d,
                      config_name="base", meta={"provenance": {"config_hash": "cfg1", "code_version": "v1",
                                                               "checks": {"facts": {"view": None, "params": {}}}}})


# --------------------------------------------------------------------------------------------
# capture
# --------------------------------------------------------------------------------------------


def test_schema2_capture_with_provenance_and_legacy_lines_still_load(tmp_path, table):
    r = make_result("Stufe1_D01-K1", table)
    (tmp_path / fb.FEEDBACK_FILE).write_text(json.dumps({"call_id": "old-K1", "ts": "1", "user": "a",
                                                         "verdict": "false_alarm"}) + "\n")
    items = fb.items_from_form(r, user="Anna", verdict="violation", passages={0: "applies"},
                               facts={("facts", "access", "current"): "yes"}, missed=["trade"], comment="klar")
    assert [i.target for i in items] == ["call", "passage", "fact", "family"]
    assert len({i.batch for i in items}) == 1 and all(i.schema_version == 2 for i in items)
    prov = items[0].provenance
    assert prov["config_hash"] == "cfg1" and prov["policy_table"]["hash"] == "abc123"
    assert prov["models"] == {"facts": "Qwen/Qwen2.5-7B-Instruct-AWQ"} and len(prov["transcript_hash"]) == 16
    fact = items[2]
    assert (fact.model_value, fact.answer, fact.agrees) == ("unclear", "yes", False) and fact.question
    assert items[1].passage["text"] == "Mein Code ist 4711"
    fb.add_many(tmp_path, items)
    loaded = fb.load(tmp_path)
    assert loaded[0].schema_version == 1 and loaded[0].target == "call"  # legacy line
    assert [i.verdict for i in loaded[1:]] == ["violation", "applies", "fact", "missed_family"]
    ev = audit.read_events(tmp_path, kind="feedback")
    assert ev[-2]["fact"] == "current" and ev[-2]["policy_table_hash"] == "abc123"
    with pytest.raises(ValueError):
        fb.items_from_form(r, user="Anna", comment="nur Kommentar")


def test_demo_and_real_stores_never_mix(tmp_path):
    with pytest.raises(ValueError):
        fb.add(tmp_path, fb.FeedbackItem(call_id="a", verdict="violation", source="demo"))
    with pytest.raises(ValueError):
        fb.add(tmp_path, fb.FeedbackItem(call_id="a", verdict="violation"), store="demo")
    fb.add(tmp_path, fb.FeedbackItem(call_id="a", verdict="violation", source="demo"), store="demo")
    assert fb.load(tmp_path) == [] and len(fb.load(tmp_path, "demo")) == 1
    assert not audit.read_events(tmp_path, kind="feedback")  # demo items are not audit events


def test_new_verdicts_map_to_labels():
    F = fb.FeedbackItem
    items = [F(call_id="a", verdict="violation"), F(call_id="b", verdict="no_violation"), F(call_id="c", verdict="unclear"),
             F(call_id="d", verdict="not_applies", passage_index=0),
             F(call_id="e", verdict="applies", passage_index=0, label_seen="review"),
             F(call_id="f", verdict="missed_family", family="trade"),
             F(call_id="g", verdict="fact", fact="x", family="access", answer="yes")]
    assert fb.labels_from_feedback(items) == {"a": "alarm", "b": "no_alert", "c": "review", "d": "no_alert",
                                              "e": "review", "f": "alarm"}


def test_fact_choices_name_the_recorded_value():
    assert fb.fact_choices("yes") == [("yes", "stimmt (ja)"), ("no", "stimmt nicht (nein)"), ("unclear", "unklar")]
    assert fb.fact_choices("no")[1] == ("yes", "stimmt nicht (ja)")
    assert [a for a, _ in fb.fact_choices("unclear")] == ["yes", "no", "unclear"]


# --------------------------------------------------------------------------------------------
# hygiene + export
# --------------------------------------------------------------------------------------------


def test_use_of_marks_case_calls_evaluation_only_and_keeps_twins_together():
    assert hygiene.use_of("Stufe1_D01-K2", SPLITS) == hygiene.EVAL_DEV
    assert hygiene.use_of("Stufe1_D09-K1", SPLITS) == hygiene.EVAL_HOLDOUT
    assert hygiene.use_of("Stufe3_C19-K3", SPLITS) == hygiene.EVAL_HOLDOUT  # case-style id missing from the split
    assert hygiene.use_of("Stufe1_D01-K1", SPLITS, demo=True) == hygiene.DEMO
    news = [f"live_{i:03d}" for i in range(200)]
    uses = {hygiene.use_of(f"{c}-K1", None) for c in news}
    assert uses == {hygiene.TRAIN, hygiene.SHADOW}
    for c in news:  # clean and noisy recording of one conversation always on one side
        assert hygiene.use_of(f"{c}-K1", None) == hygiene.use_of(f"{c}-K2", None)
    share = sum(hygiene.use_of(f"{c}-K1", None) == hygiene.SHADOW for c in news) / len(news)
    assert 0.1 < share < 0.3
    folds = hygiene.cv_fold_of(["Stufe1_D01-K1", "Stufe1_D09-K1", "Stufe2_C01-K3", "live_001-K1"], SPLITS)
    assert "Stufe1_D09" not in folds and folds["Stufe1_D01"] == 0 and folds["Stufe2_C01"] == 0


def test_check_detects_leaks():
    ok = [{"call_id": "live_001-K1", "use": hygiene.use_of("live_001-K1", None), "source": "officer"}]
    assert hygiene.check(ok, None, training=False) == []
    bad = [{"call_id": "Stufe1_D01-K1", "use": hygiene.TRAIN, "source": "officer"}]
    assert hygiene.check(bad, SPLITS, training=True)
    demo_row = [{"call_id": "live_001-K1", "use": hygiene.TRAIN, "source": "demo"}]
    assert hygiene.check(demo_row, None, training=True)
    with pytest.raises(hygiene.HygieneError):
        hygiene.enforce(bad, SPLITS, training=True)


def _new_call_ids(n: int) -> tuple[list[str], list[str]]:
    train = [c for c in (f"live_{i:03d}-K1" for i in range(400)) if hygiene.use_of(c, None) == hygiene.TRAIN][:n]
    shadow = [c for c in (f"live_{i:03d}-K1" for i in range(400)) if hygiene.use_of(c, None) == hygiene.SHADOW][:n]
    return train, shadow


def test_export_formats_and_split_hygiene(tmp_path, table):
    train, shadow = _new_call_ids(2)
    case_dev, case_hold = "Stufe1_D01-K1", "Stufe1_D09-K1"
    results = {c: make_result(c, table) for c in [*train, *shadow, case_dev, case_hold]}
    for cid, r in results.items():
        fb.add_many(tmp_path, fb.items_from_form(r, user="Anna", verdict="violation",
                                                 facts={("facts", "access", "current"): "yes",
                                                        ("facts", "access", "spoken"): "yes",
                                                        ("facts", "access", "validity_open"): "unclear"}))
    ls = records.collect(tmp_path, results, SPLITS)
    built = export.build(ls, results, SPLITS)
    tr = built["kev_noul.train.jsonl"]
    assert {r["meta"]["call_id"] for r in tr} == set(train)
    q = tr[0]["questions"]["access.current"]
    assert q == {"type": "noul", "instructions": q["instructions"], "label": True}
    assert q["instructions"].startswith("Topic: Zugangsinformation preisgegeben [access]\n")
    assert "access.validity_open" not in tr[0]["questions"]  # unclear has no noul label
    assert "S002" in tr[0]["state"] and "4711" in tr[0]["state"]
    ch = built["kev_choice.train.jsonl"][0]["questions"]["access.validity_open"]
    assert ch["label"] == "unknown" and set(ch["criteria"]) == {"yes", "no", "unknown"}
    sft = built["qwen_sft.train.jsonl"][0]["messages"]
    assert [m["role"] for m in sft] == ["system", "user", "assistant"] and "<transcript>" in sft[1]["content"]
    assert {r["meta"]["call_id"] for r in built["kev_noul.shadow_test.jsonl"]} == set(shadow)
    assert {r["meta"]["call_id"] for r in built["kev_noul.eval_dev.jsonl"]} == {case_dev}
    model_files = [n for n in built if n.startswith(("kev_", "qwen_"))]
    assert all(case_hold not in json.dumps(built[n]) for n in model_files)  # holdout: in no model file
    assert all(case_dev not in json.dumps(built[n]) for n in model_files if ".train." in n or ".shadow_test." in n)
    uses = {c["call_id"]: c["use"] for c in built["calls.jsonl"]}
    assert uses[case_hold] == hygiene.EVAL_HOLDOUT and uses[case_dev] == hygiene.EVAL_DEV
    man = export.manifest(built, ls, SPLITS)
    assert man["trainable_fact_labels"] == 3 * len(train)
    out = export.write(tmp_path / "exp", built, man)
    assert (out / "manifest.json").is_file() and (out / "kev_noul.train.jsonl").is_file()


def test_export_refuses_a_leak(tmp_path, table, monkeypatch):
    train, _ = _new_call_ids(1)
    results = {train[0]: make_result(train[0], table)}
    fb.add_many(tmp_path, fb.items_from_form(results[train[0]], user="A", facts={("facts", "access", "current"): "yes"}))
    ls = records.collect(tmp_path, results, None)
    ls.facts[0].use = hygiene.TRAIN
    monkeypatch.setattr(hygiene, "use_of", lambda cid, splits, demo=False, **k: hygiene.EVAL_DEV)
    with pytest.raises(hygiene.HygieneError):
        export.build(ls, results, None)


def test_demo_store_is_never_trainable(tmp_path, table):
    train, _ = _new_call_ids(1)
    results = {train[0]: make_result(train[0], table)}
    items = [i.model_copy(update={"source": "demo"}) for i in fb.items_from_form(
        results[train[0]], user="Demo", verdict="violation", facts={("facts", "access", "current"): "yes"})]
    fb.add_many(tmp_path, items, store="demo")
    ls = records.collect(tmp_path, results, None, store="demo")
    built = export.build(ls, results, None)
    assert not [n for n in built if ".train." in n or ".shadow_test." in n]
    assert ls.facts[0].use == hygiene.DEMO and ls.calls[train[0]].use == hygiene.DEMO
    assert insights.readiness(ls)[2]["have"] == 0  # LoRA readiness counts no demo label


def test_open_fact_answers_count_as_fact_labels(tmp_path, table):
    r = make_result("Stufe1_D01-K1", table)
    audit.log_event(tmp_path, "fact_answer", user="officer", call_id=r.call_id, check="facts", family="access",
                    fact="current", answer="no", model_value="unclear", policy_table_hash="abc123")
    facts = records.fact_labels([], {r.call_id: r}, SPLITS, records.load_events(tmp_path))
    assert [(f.fact, f.answer, f.source, f.corrected, f.use) for f in facts] == \
        [("current", "no", "open_facts", True, hygiene.EVAL_DEV)]
    audit.log_event(tmp_path, "fact_answer_reset", user="officer", call_id=r.call_id)
    assert records.fact_labels([], {r.call_id: r}, SPLITS, records.load_events(tmp_path)) == []


# --------------------------------------------------------------------------------------------
# insights + readiness
# --------------------------------------------------------------------------------------------


def _fact(call: str, fact: str, mv: str, ans: str, use: str = hygiene.TRAIN, agrees: bool | None = None) -> records.FactLabel:
    return records.FactLabel(call_id=call, check="facts", family="access", fact=fact, fact_label=fact, role=None,
                             question="Q?", answer=ans, model_value=mv, model_p=None,
                             agrees=(ans == mv) if agrees is None else agrees, rule_id="access.review_1", user="u",
                             ts="1", source="officer", policy_table_hash=None, use=use)


def test_corrections_and_wilson():
    lo, hi = insights.wilson(2, 4)
    assert 0.14 < lo < 0.16 and 0.84 < hi < 0.86
    facts = [_fact(f"c{i}", "current", "unclear", "yes" if i < 4 else "unclear") for i in range(10)]
    facts += [_fact(f"c{i}", "spoken", "yes", "yes") for i in range(10)]
    rows = {r["fact"]: r for r in insights.corrections(facts)}
    assert rows["current"]["rate"] == 0.4 and rows["current"]["flag"] and rows["current"]["strong"]
    assert "40%" in rows["current"]["advice"] and "Formulierung prüfen" in rows["current"]["advice"]
    assert not rows["spoken"]["flag"] and rows["spoken"]["advice"] == ""
    weak = insights.corrections(facts[:3])[0]
    assert weak["flag"] and not weak["strong"] and "noch keine Messung" in weak["advice"]


def test_readiness_thresholds():
    calls = {f"c{i}": records.CallLabel(call_id=f"c{i}", label="alarm", system_label="alarm", system_family="access",
                                        families=["access"], verdict="violation", user="u", ts="1", officers=["u"],
                                        disagreement=False, use=hygiene.TRAIN, source="officer", call_use=hygiene.TRAIN)
             for i in range(31)}
    facts = [_fact(f"c{i}", "current", "yes", "yes") for i in range(6)]
    facts += [_fact(f"h{i}", "current", "yes", "yes", use=hygiene.EVAL_DEV) for i in range(500)]
    ls = records.LabelSet(store="real", items=[], calls=calls, facts=facts, passages=[])
    r = {x["key"]: x for x in insights.readiness(ls)}
    assert r["calibration"]["ready"] and r["calibration"]["detail"]["families_ready"] == 1
    assert r["fewshot"]["have"] == 1 and not r["fewshot"]["ready"]  # measured as not helpful: never "ready"
    assert r["lora"]["have"] == 6 and r["lora"]["need"] == 1000 and r["lora"]["progress"] == pytest.approx(0.006)
    assert not r["whisper"]["ready"]
    cm = insights.confusion(calls)
    assert cm["agreement"] == 1.0 and cm["matrix"]["alarm"]["alarm"] == 31


# --------------------------------------------------------------------------------------------
# re-fit + proposals
# --------------------------------------------------------------------------------------------


def _scored(call_id: str, score: float) -> CallResult:
    t = Transcript(call_id=call_id, segments=[Segment(id="T1", start=0, end=2, role="customer", text="x")])
    d = Decision(label="alarm" if score >= 0.55 else "no_alert", score=score, uncertainty=0.1, threshold=0.55)
    return CallResult(call_id=call_id, transcript=t, decision=d, config_name="base",
                      checks={"llm": CheckResult(check="llm", type="fake", family_scores={"trade": FamilyScore(score=score)})})


def test_refit_uses_folds_never_the_holdout_and_reports_a_ci(tmp_path):
    pipe = Pipeline(load_config("base", sets(tmp_path, "checks=[]", "sinks=[]")))
    rows = {"Stufe1_D01": (0.35, "alarm"), "Stufe2_C01": (0.4, "alarm"), "Stufe2_C02": (0.1, "no_alert"),
            "Stufe1_D02": (0.45, "alarm"), "Stufe1_D09": (0.9, "no_alert")}
    results, labels = [], {}
    for d, (s, lab) in rows.items():
        for k in ("K1", "K2"):
            results.append(_scored(f"{d}-{k}", s))
            labels[f"{d}-{k}"] = lab
    for i in range(6):  # new calls, hashed into folds
        results.append(_scored(f"live_{i}-K1", 0.3 if i % 2 else 0.05))
        labels[f"live_{i}-K1"] = "alarm" if i % 2 else "no_alert"
    rec = recalibrate.propose_threshold(pipe, results, labels, SPLITS, thresholds=[0.2, 0.3, 0.55], n_boot=200)
    assert rec["dropped"] == ["Stufe1_D09-K1", "Stufe1_D09-K2"]
    assert rec["n_calls"] == 14 and rec["proposed_threshold"] in (0.2, 0.3)
    assert rec["cv"]["n_folds"] >= 2 and set(rec["effect"]) == set(recalibrate.EFFECT_METRICS)
    assert rec["effect"]["miss_rate"]["diff"] < 0  # lower threshold: fewer misses out of fold
    assert rec["verdict"] in ("better", "no_difference")
    few = recalibrate.propose_threshold(pipe, results[:4], {k: labels[k] for k in list(labels)[:4]}, SPLITS)
    assert few["verdict"] == "too_few" and few["proposed_threshold"] is None


def test_verdict_rule():
    real_up = {"flag_f1": {"diff": 0.1, "lo": 0.02, "hi": 0.2, "real": True},
               "false_alarm_rate": {"diff": 0.0, "lo": -0.1, "hi": 0.1, "real": False}}
    assert recalibrate.verdict_of(real_up) == "better"
    more_fa = {**real_up, "false_alarm_rate": {"diff": 0.1, "lo": 0.01, "hi": 0.2, "real": True}}
    assert recalibrate.verdict_of(more_fa) == "worse"
    assert recalibrate.verdict_of({"flag_f1": {"diff": 0.05, "lo": -0.1, "hi": 0.2, "real": False}}) == "no_difference"


def test_four_eyes_approval_and_rollback(tmp_path):
    runs, tp = tmp_path / "runs", tmp_path / "tuning.yaml"
    fb.apply_tuning(tp, "base", review_band=0.1)
    p = pr.propose(runs, "base", {"threshold": 0.42}, user="Anna", reason="CV", evidence={"verdict": "no_difference"})
    assert p.status == "open" and fb.read_tuning(tp)["profiles"]["base"]["fusion"] == {"review_band": 0.1}  # not applied
    with pytest.raises(pr.FourEyesError):
        pr.approve(runs, p.id, user=" anna ", tuning_path=tp)  # same person (case / spaces ignored)
    with pytest.raises(pr.FourEyesError):
        pr.reject(runs, p.id, user="Anna")
    with pytest.raises(pr.FourEyesError):
        pr.approve(runs, p.id, user="", tuning_path=tp)
    a = pr.approve(runs, p.id, user="Bruno", tuning_path=tp)
    assert a.status == "approved" and a.approved_by == "Bruno"
    assert load_config("base", sets(tmp_path)).fusion["threshold"] == 0.42
    with pytest.raises(pr.ProposalStateError):
        pr.approve(runs, p.id, user="Carla", tuning_path=tp)
    rb = pr.rollback(runs, p.id, user="Carla", tuning_path=tp)
    assert rb.status == "rolled_back"
    assert fb.read_tuning(tp)["profiles"]["base"]["fusion"] == {"review_band": 0.1}  # exactly as before
    kinds = [e["kind"] for e in audit.read_events(runs)]
    assert ["proposal_proposed", "tuning_save", "proposal_approved", "tuning_save", "proposal_rolled_back"] == \
        [k for k in kinds if k.startswith(("proposal_", "tuning_save"))]
    r = pr.reject(runs, pr.propose(runs, "base", {"threshold": 0.6}, user="Anna").id, user="Bruno", reason="nein")
    assert r.status == "rejected"
    with pytest.raises(ValueError):
        pr.propose(runs, "base", {"threshold": 1.4}, user="Anna")


def test_second_approval_supersedes_first(tmp_path):
    runs, tp = tmp_path / "runs", tmp_path / "tuning.yaml"
    p1 = pr.approve(runs, pr.propose(runs, "base", {"threshold": 0.5}, user="A").id, user="B", tuning_path=tp)
    p2 = pr.approve(runs, pr.propose(runs, "base", {"threshold": 0.6}, user="A").id, user="B", tuning_path=tp)
    st = {p.id: p.status for p in pr.load(runs)}
    assert st[p1.id] == "superseded" and st[p2.id] == "approved"
    pr.rollback(runs, p2.id, user="C", tuning_path=tp)
    assert fb.read_tuning(tp)["profiles"]["base"]["fusion"]["threshold"] == 0.5


# --------------------------------------------------------------------------------------------
# demo simulation
# --------------------------------------------------------------------------------------------


def _call(cid: str, label: str, family: str = "access") -> Call:
    c = Call(call_id=cid, dialogue_id=cid.split("-K")[0], level=1, variant=1, noisy=False, audio_path=Path("/x.wav"))
    c.expected = Expected(label=label, family=family, event="present", reason="", open_question="")
    return c


def test_demo_simulation_dev_only_and_minimal_fact_flip(tmp_path, table):
    results = {"Stufe1_D01-K1": make_result("Stufe1_D01-K1", table),  # system: review (access.review_1)
               "Stufe1_D09-K1": make_result("Stufe1_D09-K1", table)}  # holdout: never simulated
    calls = [_call("Stufe1_D01-K1", "alarm"), _call("Stufe1_D09-K1", "alarm")]
    n = demo.seed(tmp_path, results, calls, SPLITS)
    items = fb.load(tmp_path, "demo")
    assert n == len(items) and {i.call_id for i in items} == {"Stufe1_D01-K1"}
    assert all(i.source == "demo" and i.comment == fb.DEMO_NOTE for i in items)
    assert fb.load(tmp_path) == []
    call = next(i for i in items if i.target == "call")
    assert call.verdict == "violation"
    corrected = [i for i in items if i.target == "fact" and not i.agrees]
    assert [(i.fact, i.model_value, i.answer) for i in corrected] == [("current", "unclear", "yes")]
    ft = table.families["access"]
    vals = {k: v for k, (v, _) in C17_ACCESS.items()}
    assert demo.minimal_flip(ft, vals, {k: p for k, (_, p) in C17_ACCESS.items()}, "alarm") == {"current": "yes"}


# --------------------------------------------------------------------------------------------
# CLI + UI
# --------------------------------------------------------------------------------------------


def test_cli_learn(tmp_path, table, monkeypatch):
    from callguard import cli
    from callguard.context import Context
    from callguard.sinks.json_dir import JsonDirSink

    monkeypatch.setattr(hygiene, "splits_or_none", lambda: SPLITS)
    runner = CliRunner()
    opts = ["-c", "base", *(x for s in sets(tmp_path) for x in ("--set", s))]
    ctx = Context(load_config("base", sets(tmp_path)))
    r = make_result("Stufe1_D01-K1", table)
    JsonDirSink(ctx).emit(r)
    fb.add_many(ctx.runs_dir, fb.items_from_form(r, user="Anna", verdict="violation",
                                                 facts={("facts", "access", "current"): "yes"}))
    out = runner.invoke(cli.app, ["learn", "status", *opts])
    assert out.exit_code == 0, out.output
    assert "Readiness" in out.output
    out = runner.invoke(cli.app, ["learn", "export", "--out", str(tmp_path / "exp"), *opts])
    assert out.exit_code == 0, out.output
    assert json.loads((tmp_path / "exp" / "manifest.json").read_text())["files"]["calls.jsonl"] == 1
    out = runner.invoke(cli.app, ["learn", "propose", "--threshold", "0.5", "-u", "Anna", "--set", "checks=[]", *opts])
    assert out.exit_code == 0, out.output
    pid = pr.load(ctx.runs_dir)[0].id
    assert runner.invoke(cli.app, ["learn", "approve", pid, "-u", "Anna", *opts]).exit_code == 1
    out = runner.invoke(cli.app, ["learn", "approve", pid, "-u", "Bruno", *opts])
    assert out.exit_code == 0, out.output
    assert load_config("base", sets(tmp_path)).fusion["threshold"] == 0.5
    assert runner.invoke(cli.app, ["learn", "rollback", pid, "-u", "Carla", *opts]).exit_code == 0
    assert runner.invoke(cli.app, ["learn", "proposals", *opts]).exit_code == 0


def test_ui_panel_and_pages_smoke(tmp_path, monkeypatch, table):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from ui_fixtures import REVIEW_ID, write_fixture_env

    from callguard.ui import backend as be

    env = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tmp_path / 'tuning.yaml'}")
    monkeypatch.setenv("CALLGUARD_USER", "Anna")
    path = env.result_path(REVIEW_ID)
    r = CallResult.model_validate_json(path.read_text())
    r.checks["facts"] = facts_check(table)
    path.write_text(r.model_dump_json(indent=1))
    app = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"

    def run(page: str | None = None, query: dict | None = None) -> AppTest:
        at = AppTest.from_file(str(app), default_timeout=90)
        for k, v in (query or {}).items():
            at.query_params[k] = v
        at.run()
        if page:
            at.switch_page(f"views/{page}.py").run()
        assert not at.exception, [e.message for e in at.exception]
        return at

    at = run("detail", {"call": REVIEW_ID})
    assert any(e.label == "Rückmeldung" for e in at.expander)
    next(x for x in at.radio if x.key == f"cg_fb2_v_{REVIEW_ID}").set_value("violation")
    next(x for x in at.radio if x.key == f"cg_fb2_f_{REVIEW_ID}_access_current").set_value("yes")
    next(b for b in at.button if b.label == "Rückmeldung speichern").click().run()
    assert not at.exception, [e.message for e in at.exception]
    saved = fb.load(env.runs_dir)
    assert [i.verdict for i in saved] == ["violation", "fact"] and saved[0].user == "Anna"
    assert saved[1].answer == "yes" and saved[1].provenance.get("policy_table", {}).get("hash") == "abc123"

    at = run("learning")
    assert at.title[0].value.startswith("Lernen")
    assert "Prüfer = System" in [m.label for m in at.metric]
    at = run("feedback")
    assert at.title[0].value == "Feedback & Tuning"
