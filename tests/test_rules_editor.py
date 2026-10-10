"""UI page "Regelwerk": plain-language rule editing, the LLM rule drafter, what-if from stored fact answers,
versions with four-eyes approval, `enabled: false` in the facts check. Offline (canned LLM doubles)."""

from __future__ import annotations

import copy
import itertools
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from callguard import audit
from callguard import policy_edit as pe
from callguard import rule_drafter as rd
from callguard.checks.facts import (
    FactSheetCheck,
    PolicyTableError,
    decide_family,
    eval_hard,
    load_policy_table,
    parse_policy_table,
    parse_rule,
)
from callguard.config import ROOT, AppConfig, Paths
from callguard.context import Context
from callguard.policy_versions import FourEyesError, VersionStore
from callguard.types import CallResult, CheckResult, Decision, Family, FamilyScore, Segment, Transcript
from callguard.ui import whatif as wi

SHIPPED = ROOT / "config" / "policy_table.yaml"


@pytest.fixture
def doc() -> dict:
    return pe.load_doc(SHIPPED)


# --------------------------------------------------------------------------------------------
# enabled flag + cache key stability
# --------------------------------------------------------------------------------------------


def test_shipped_table_hash_unchanged_by_basis_and_enabled_keys(doc):
    """The champion's cached results stay valid: `basis` never and `enabled: true` not in the key."""
    table = load_policy_table(SHIPPED)
    assert table.key(list(table.families)) == "1d7f4efbdef88250"  # = meta.policy_table.hash of runs/recommended
    assert table.families["trade"].basis.startswith("FinfraG Art. 142")
    d = copy.deepcopy(doc)
    for fam in d["families"].values():
        fam.pop("basis", None)
        for r in fam["rules"]:
            r["enabled"] = True
            r["basis"] = "irgendwas"
    t2 = parse_policy_table(d)
    assert t2.key(list(t2.families)) == "1d7f4efbdef88250"


def test_disabled_rule_is_skipped_and_changes_the_key(doc):
    d = copy.deepcopy(doc)
    pe.set_enabled(d, "access", "access.review_1", False)
    t = parse_policy_table(d)
    ft = t.families["access"]
    assert [r.id for r in ft.rules] == ["access.alarm_1", "access.no_alert"]
    assert [r.id for r in ft.disabled] == ["access.review_1"]
    values = {"spoken": "yes", "current": "unclear", "validity_open": "yes", "expired_or_sample": "no",
              "asked_by_advisor": "no"}
    probs = {k: {v: 1.0} for k, v in values.items()}
    assert parse_policy_table(doc).families["access"].decide(values).id == "access.review_1"
    fd = decide_family(ft, values, probs)
    assert fd.label == "no_alert" and fd.rule.id == "access.no_alert"
    assert "access.review_1" not in fd.soft  # a disabled rule does not feed the soft score either
    assert t.key(["access"]) != parse_policy_table(doc).key(["access"])
    assert t.key(["trade"]) == parse_policy_table(doc).key(["trade"])  # other families untouched
    pe.set_enabled(d, "access", "access.review_1", True)
    assert "enabled" not in d["families"]["access"]["rules"][1]
    assert parse_policy_table(d).key(["access"]) == parse_policy_table(doc).key(["access"])


def test_enabled_must_be_boolean_and_ids_unique_across_disabled(doc):
    d = copy.deepcopy(doc)
    d["families"]["access"]["rules"][0]["enabled"] = "vielleicht"
    with pytest.raises(PolicyTableError, match="enabled"):
        parse_policy_table(d)
    d = copy.deepcopy(doc)
    d["families"]["access"]["rules"][0]["enabled"] = False
    d["families"]["access"]["rules"][1]["id"] = "access.alarm_1"
    with pytest.raises(PolicyTableError, match="duplicate rule id"):
        parse_policy_table(d)


def test_facts_check_skips_disabled_rule(tmp_path, doc):
    d = copy.deepcopy(doc)
    pe.set_enabled(d, "access", "access.alarm_1", False)
    p = tmp_path / "t.yaml"
    p.write_text(pe.dump_doc(d))
    ctx = Context(AppConfig(name="t", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                            paths=Paths(cache_dir=str(tmp_path / "cache"))))
    check = FactSheetCheck(ctx, policy_table=str(p), evidence=False)
    ft = check.table().families["access"]
    assert "access.alarm_1" not in [r.id for r in ft.rules]


# --------------------------------------------------------------------------------------------
# condition builder <-> rule text, rendering
# --------------------------------------------------------------------------------------------


def _same_semantics(a: str, b: str, facts: list[str]) -> bool:
    na, nb = parse_rule(a), parse_rule(b)
    return all(eval_hard(na, dict(zip(facts, combo))) == eval_hard(nb, dict(zip(facts, combo)))
               for combo in itertools.product(pe.VALUES, repeat=len(facts)))


def test_builder_round_trip_on_every_shipped_rule(doc):
    for fam, entry in doc["families"].items():
        ids = [f["id"] for f in entry["facts"]]
        for r in entry["rules"]:
            rows = pe.builder_from_when(str(r["when"]), set(ids))
            assert rows is not None, (fam, r["id"])
            back = pe.when_from_builder(rows)
            assert _same_semantics(str(r["when"]), back, ids), (fam, r["id"], back)
            if str(r["when"]) != "true":
                assert back == str(r["when"])  # the shipped rules are already in canonical form


@pytest.mark.parametrize("when,canonical", [
    ("a = yes and b != no or c = unclear", "a = yes and b != no or c = unclear"),
    ("a == ja and b in [yes, unclear]", "a = yes and b != no"),
    ("a not in [yes, unclear]", "a = no"),
    ("not a = yes", "a != yes"),
    ("true", "true"),
])
def test_builder_canonical_forms(when, canonical):
    rows = pe.builder_from_when(when)
    assert pe.when_from_builder(rows) == canonical
    assert _same_semantics(when, canonical, ["a", "b", "c"])


@pytest.mark.parametrize("when", ["not (a = yes or b = yes)", "(a = yes or b = yes) and c = no",
                                  "a in [yes, no, unclear]"])
def test_builder_refuses_what_rows_cannot_say(when):
    assert pe.builder_from_when(when) is None


def test_builder_join_and_values():
    rows = [pe.Cond("a", "yes"), pe.Cond("b", "no", negate=True, join="or")]
    assert pe.when_from_builder(rows) == "a = yes or b != no"
    assert pe.when_from_builder([]) == "true"
    with pytest.raises(PolicyTableError):
        pe.when_from_builder([pe.Cond("a", "vielleicht")])


def test_render_uses_labels_not_ids(doc):
    labels = pe.fact_labels(doc, "trade")
    r = doc["families"]["trade"]["rules"][0]
    text = pe.render_rule(r, labels)
    assert text == ("WENN «Eigener Handelswunsch geäussert» = ja UND «Begründet mit nicht öffentlicher "
                    "Insider-Information» = ja UND «Information bereits öffentlich» ≠ ja → ALARM")
    assert pe.render_rule(doc["families"]["trade"]["rules"][-1], labels) == "SONST (immer) → KEIN ALARM"
    assert pe.render_when("a = yes or b = no and c = yes", {"a": "A", "b": "B", "c": "C"}) == \
        "«A» = ja ODER («B» = nein UND «C» = ja)"
    assert pe.render_when("not (a = yes or b = no)", {"a": "A", "b": "B"}) == "NICHT («A» = ja ODER «B» = nein)"


def test_doc_edits_and_plain_german_diff(doc):
    d = copy.deepcopy(doc)
    assert pe.move_rule(d, "access", "access.review_1", -1)
    assert not pe.move_rule(d, "access", "access.review_1", -1)  # already on top
    pe.set_enabled(d, "trade", "trade.review_1", False)
    pe.replace_rule(d, "disclosure", "disclosure.review_2",
                    {"id": "disclosure.review_2", "label": "alarm", "when": "third_party_request = yes",
                     "text": "Neu", "basis": "BankG Art. 47"})
    fid = pe.new_fact_id(d, "splitting", "Knapp unter der Meldeschwelle")
    assert fid == "knapp_unter_der_meldeschwelle"
    pe.upsert_fact(d, "splitting", {"id": fid, "label": "Knapp unter Schwelle", "role": "context", "de": "Frage?"})
    f0 = d["families"]["trade"]["facts"][0]
    f0["en"] = f0["en"] + " Really?"
    pe.validate(d)
    diff = "\n".join(pe.diff_docs(doc, d, {"access": "Zugang"}))
    assert "Zugang: Reihenfolge der Regeln geändert" in diff
    assert "trade: Regel trade.review_1 ausgeschaltet" in diff
    assert "disclosure: Regel disclosure.review_2 Bedingung vorher" in diff and "→ ALARM" in diff
    assert "neuer Fakt «Knapp unter Schwelle»" in diff
    assert "(Englisch, liest das Modell) geändert" in diff
    assert pe.changed_questions(doc, d) == {"trade": ["wish"], "splitting": [fid]}
    with pytest.raises(PolicyTableError, match="verwendet"):
        pe.delete_fact(d, "trade", "wish")
    assert pe.diff_docs(doc, copy.deepcopy(doc)) == []


# --------------------------------------------------------------------------------------------
# drafter (canned LLM)
# --------------------------------------------------------------------------------------------


class Canned:
    """Returns the queued answers in order (the last one repeats); records every call."""

    def __init__(self, *answers: str):
        self.answers = list(answers)
        self.calls: list[dict] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        self.calls.append({"messages": messages, "json_schema": json_schema})
        out = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return [out] * n


REQUEST = ("Alarm, wenn ein Kunde eine Zahlung in mehrere Beträge knapp unter 10'000 aufteilen will, um eine "
           "Meldung zu vermeiden")


def good_draft(**over) -> dict:
    obj = {"family": "splitting",
           "facts": [{"id": "below_threshold", "label": "Beträge knapp unter Meldeschwelle", "role": "context",
                      "de": "Sollen die Teilbeträge jeweils knapp unter 10'000 Franken bleiben?",
                      "en": "Are the partial amounts each meant to stay just below CHF 10,000?"},
                     {"id": "avoid_report", "label": "Meldung vermeiden", "role": "context",
                      "de": "Wird gesagt, dass so eine Meldung oder Abklärung vermieden werden soll?",
                      "en": "Is it said that this is meant to avoid a report or a clarification?"}],
           "rule": {"label": "alarm", "when": "split_request = yes and below_threshold = yes and avoid_report != no",
                    "text": "Zahlung wird aufgeteilt, um unter der Meldeschwelle zu bleiben.", "basis": "GwG Art. 6"},
           "note": "Prüfen, ob 10'000 die richtige Schwelle ist."}
    obj.update(over)
    return obj


def test_drafter_valid_draft_is_validated_and_applied(doc):
    llm = Canned(json.dumps(good_draft()))
    draft = rd.draft_rule(llm, doc, REQUEST, {"splitting": "Kontrolle umgehen"})
    assert llm.calls[0]["json_schema"]["properties"]["family"]["enum"] == list(doc["families"])
    assert REQUEST in llm.calls[0]["messages"][-1]["content"] and "split_request" in llm.calls[0]["messages"][-1]["content"]
    assert draft.family == "splitting" and [f["id"] for f in draft.facts] == ["below_threshold", "avoid_report"]
    assert draft.rule["id"] == "splitting.alarm_2" and draft.rule["basis"] == "GwG Art. 6"
    assert not draft.warnings
    new = rd.apply_draft(doc, draft)
    t = pe.validate(new)
    ft = t.families["splitting"]
    assert ft.rules[0].id == "splitting.alarm_2"  # alarm rules go on top
    assert {"below_threshold", "avoid_report"} <= {f.id for f in ft.facts}
    assert doc["families"]["splitting"]["rules"][0]["id"] == "splitting.alarm_1"  # input not mutated


def test_drafter_renames_colliding_ids_and_drops_unused_facts(doc):
    obj = good_draft()
    obj["facts"][0]["id"] = "split_request"  # collides with an existing fact
    obj["rule"]["when"] = "split_request = yes"
    draft = rd.validate_draft(obj, doc)  # a NEW fact named like an existing one: renamed, also in the condition
    assert [f["id"] for f in draft.facts] == ["split_request_2"] and draft.rule["when"] == "split_request_2 = yes"
    assert any("gibt es schon" in w for w in draft.warnings)
    assert any("Nicht verwendete Fakten verworfen: avoid_report" in w for w in draft.warnings)
    obj = good_draft()
    obj["facts"][0]["id"] = "harmless"
    obj["rule"]["when"] = "split_request = yes and harmless = yes"  # the model meant ITS new fact
    draft = rd.validate_draft(obj, doc)
    assert draft.facts[0]["id"] == "harmless_2" and draft.rule["when"] == "split_request = yes and harmless_2 = yes"


@pytest.mark.parametrize("bad,match", [
    ({"family": "weather"}, "Unbekannte Art"),
    ({"rule": {"label": "alarm", "when": "true", "text": "x", "basis": ""}}, "keine Bedingung"),
    ({"rule": {"label": "alarm", "when": "nonexistent = yes", "text": "x", "basis": ""}}, "ungültig"),
    ({"rule": {"label": "alarm", "when": "split_request = ", "text": "x", "basis": ""}}, "ungültig"),
    ({"rule": {"label": "maybe", "when": "split_request = yes", "text": "x", "basis": ""}}, "alarm / review"),
    ({"rule": "Alarm!"}, "keine Regel"),
])
def test_drafter_rejects_invalid_drafts(doc, bad, match):
    with pytest.raises(rd.DraftError, match=match):
        rd.validate_draft(good_draft(**bad), doc)


def test_drafter_malformed_output_raises_after_repair(doc):
    llm = Canned("Gerne! Hier ist meine Regel: Alarm bei Aufteilung.", "immer noch kein JSON")
    with pytest.raises(rd.DraftError, match="kein gültiges JSON"):
        rd.draft_rule(llm, doc, REQUEST)
    assert len(llm.calls) == 2  # one repair turn


def test_drafter_repairs_an_invalid_rule_once(doc):
    bad = good_draft(rule={"label": "alarm", "when": "below_threshold = yes and nonsense = yes", "text": "x",
                           "basis": ""})
    llm = Canned(json.dumps(bad), json.dumps(good_draft()))
    draft = rd.draft_rule(llm, doc, REQUEST)
    assert draft.rule["when"].startswith("split_request = yes") and len(llm.calls) == 2
    assert "nonsense" in llm.calls[1]["messages"][-1]["content"]
    with pytest.raises(rd.DraftError, match="ungültig"):
        rd.draft_rule(Canned(json.dumps(bad)), doc, REQUEST)
    with pytest.raises(rd.DraftError, match="eigenen Worten"):
        rd.draft_rule(Canned("{}"), doc, "   ")


def test_drafter_with_the_offline_fake_llm_never_crashes(doc):
    """The fake LLM fills the schema with filler: the result is a draft or a German DraftError, nothing else."""
    from callguard.llm.fake import FakeLLM

    try:
        draft = rd.draft_rule(FakeLLM(), doc, REQUEST)
    except rd.DraftError:
        return
    pe.validate(rd.apply_draft(doc, draft))


def test_translate_question():
    assert rd.translate_question(Canned('"Is a code read out?"'), "Wird ein Code vorgelesen?") == "Is a code read out?"
    with pytest.raises(rd.DraftError):
        rd.translate_question(Canned(""), "Frage?")


# --------------------------------------------------------------------------------------------
# what-if from stored fact answers
# --------------------------------------------------------------------------------------------

C17 = {"spoken": ("yes", {"yes": 0.92, "no": 0.03, "unclear": 0.05}),
       "current": ("unclear", {"yes": 0.0, "no": 0.0, "unclear": 1.0}),
       "validity_open": ("yes", {"yes": 0.99, "no": 0.0, "unclear": 0.01}),
       "expired_or_sample": ("no", {"yes": 0.0, "no": 0.9, "unclear": 0.1}),
       "asked_by_advisor": ("no", {"yes": 0.0, "no": 0.9, "unclear": 0.1})}


def stored_call(cid: str, facts: dict, table, lang: str = "en") -> CallResult:
    ft = table.families["access"]
    values = {k: v for k, (v, _) in facts.items()}
    probs = {k: p for k, (_, p) in facts.items()}
    fd = decide_family(ft, values, probs)
    detail = {"decision": fd.label, "facts": {k: {"label": ft.fact(k).label, "role": ft.fact(k).role, "value": v,
                                                  "p": p, "question": ft.fact(k).question(lang)}
                                              for k, (v, p) in facts.items()},
              "rule": {"id": fd.rule.id}}
    segs = [Segment(id="S001", start=0, end=3, text="Ich lese Ihnen die TAN vor: 4711.", role="customer")]
    return CallResult(call_id=cid, transcript=Transcript(call_id=cid, segments=segs, duration=3.0),
                      decision=Decision(label=fd.label, score=fd.score, uncertainty=0.1, threshold=0.55),
                      checks={"facts": CheckResult(check="facts", type="facts", family_scores={
                          "access": FamilyScore(score=fd.score, confidence=fd.confidence, verdict=fd.verdict,
                                                detail=detail)},
                          meta={"seconds": 4.0, "llm_calls": 8})})


def family_fusion(r: CallResult):
    """Stand-in for the fusion: the facts check's family decision is the call label."""
    label = r.checks["facts"].family_scores["access"].detail["decision"]
    return SimpleNamespace(label=label, score=r.checks["facts"].family_scores["access"].score)


@pytest.fixture
def table():
    return load_policy_table(SHIPPED)


def test_rule_only_change_redecides_instantly(table, doc):
    calls = {"C17": stored_call("C17", C17, table),
             "C01": stored_call("C01", {**C17, "spoken": ("no", {"yes": 0.0, "no": 1.0, "unclear": 0.0})}, table)}
    same = wi.preview(calls, table, table, family_fusion)
    assert same.n_calls == 2 and not same.changed
    assert same.rule_hits["access"] == {"access.review_1": 1, "access.no_alert": 1}
    d = copy.deepcopy(doc)
    pe.set_enabled(d, "access", "access.review_1", False)
    assert wi.probe_tasks(calls, pe.validate(d), "en") == []  # rules only: no LLM needed
    pv = wi.preview(calls, table, pe.validate(d), family_fusion)
    assert [(c.call_id, c.before, c.after) for c in pv.changed] == [("C17", "review", "no_alert")]
    assert pv.changed[0].changed_families() == ["access"]
    assert pv.cond_hits == {"access": {"access.review_1": 1}}
    eff = wi.label_effect(pv.calls, {"C17": "review", "C01": "no_alert"})
    assert (eff["hits_before"], eff["hits_after"], eff["false_before"], eff["false_after"]) == (1, 0, 0, 0)
    assert (eff["exact_before"], eff["exact_after"], eff["n"]) == (2, 1, 2)


def test_changed_question_needs_a_probe_then_uses_it(table, doc):
    calls = {"C17": stored_call("C17", C17, table)}
    d = copy.deepcopy(doc)
    f = next(x for x in d["families"]["access"]["facts"] if x["id"] == "current")
    f["en"] = "Is the value that was read out still valid for a current login?"
    pe.upsert_fact(d, "access", {"id": "new_fact", "label": "Neu", "role": "context", "de": "Neu?", "en": "New?"})
    draft = pe.validate(d)
    assert sorted(wi.probe_tasks(calls, draft, "en")) == [("C17", "access", "current"), ("C17", "access", "new_fact")]
    calls_de = {"C17": stored_call("C17", C17, table, lang="de")}  # a run that asked the German questions
    assert wi.probe_tasks(calls_de, draft, "de") == [("C17", "access", "new_fact")]  # German text unchanged
    pv = wi.preview(calls, table, draft, family_fusion, lang="en")
    assert not pv.changed and pv.unresolved == {("access", "current"): 1, ("access", "new_fact"): 1}
    probes = {("C17", "access", "current"): {"yes": 0.95, "no": 0.03, "unclear": 0.02}}
    pv = wi.preview(calls, table, draft, family_fusion, probes=probes, lang="en")
    assert [(c.before, c.after) for c in pv.changed] == [("review", "alarm")]
    assert pv.changed[0].families_after["access"].rule == "access.alarm_1"
    assert pv.unresolved == {("access", "new_fact"): 1}


def test_run_probes_uses_the_facts_check_and_reports_unreachable(tmp_path, table, doc):
    p = tmp_path / "t.yaml"
    shutil.copy(SHIPPED, p)
    ctx = Context(AppConfig(name="t", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                            paths=Paths(cache_dir=str(tmp_path / "cache"))))
    check = FactSheetCheck(ctx, policy_table=str(p), evidence=False, parallel=2)
    calls = {"C17": stored_call("C17", C17, table), "C18": stored_call("C18", C17, table)}
    d = copy.deepcopy(doc)
    pe.upsert_fact(d, "access", {"id": "tan", "label": "TAN", "role": "act", "de": "Wird eine TAN genannt?",
                                 "en": "Is a TAN said?"})
    draft = pe.validate(d)
    tasks = wi.probe_tasks(calls, draft, "en")
    fams = {"access": Family(id="access", label="Zugangsinformation preisgegeben", policy="p")}
    seen = []
    out, errors = wi.run_probes(check, calls, draft, tasks, fams, lambda r: r.transcript,
                                lambda i, n: seen.append((i, n)))
    assert not errors and set(out) == set(tasks) and seen[-1] == (2, 2)
    assert set(out[tasks[0]]) == {"yes", "no", "unclear"}

    class Down:
        def chat(self, *a, **k):
            raise ConnectionError("vLLM down")

        def choice_probs(self, *a, **k):
            raise ConnectionError("vLLM down")

        def cache_params(self):
            return {"type": "down"}

    ctx.llm = lambda name="default": Down()
    with pytest.raises(wi.ProbeUnavailable):
        wi.run_probes(check, calls, draft, tasks, fams, lambda r: r.transcript)
    with pytest.raises(wi.ProbeUnavailable):
        wi.run_probes(None, calls, draft, tasks, fams, lambda r: r.transcript)
    assert wi.seconds_per_probe(calls) == pytest.approx(0.5)


# --------------------------------------------------------------------------------------------
# versions + four eyes
# --------------------------------------------------------------------------------------------


@pytest.fixture
def store(tmp_path) -> VersionStore:
    active = tmp_path / "config" / "policy_table.yaml"
    active.parent.mkdir()
    shutil.copy(SHIPPED, active)
    return VersionStore(active, audit_dir=tmp_path / "runs")


def test_versions_four_eyes_and_rollback(store: VersionStore, doc):
    original = store.active_path.read_text()
    v1 = store.ensure_initial()
    assert (v1.n, v1.status, v1.meta["kind"]) == (1, "approved", "initial")
    assert store.ensure_initial().n == 1 and v1.text() == original  # comments of the file kept in v1

    d = copy.deepcopy(doc)
    pe.set_enabled(d, "access", "access.review_1", False)
    v2 = store.save_draft(d, "Anna Muster", "C17-Fälle nicht mehr prüfen")
    assert v2.status == "draft" and store.active().n == 1
    assert store.active_path.read_text() == original  # a draft is never live
    assert "access: Regel access.review_1 ausgeschaltet" in v2.meta["diff"]
    assert v2.text().startswith("# Fact sheet") and "# Regelwerk-Version 2 · verfasst von Anna Muster" in v2.text()

    for who in ("Anna Muster", "  anna   muster ", ""):
        with pytest.raises(FourEyesError):
            store.approve(2, who)
    assert store.active().n == 1
    store.approve(2, "Ben Beispiel")
    assert store.active().n == 2 and store.get(2).meta["approver"] == "Ben Beispiel"
    live = load_policy_table(store.active_path)
    assert [r.id for r in live.families["access"].disabled] == ["access.review_1"]
    with pytest.raises(FourEyesError, match="nicht Entwurf"):
        store.approve(2, "Carla")

    v3 = store.rollback(1, "Ben Beispiel")
    assert v3.status == "draft" and v3.meta["comment"] == "Zurücksetzen auf Version 1"
    with pytest.raises(FourEyesError):
        store.approve(3, "Ben Beispiel")
    store.approve(3, "Anna Muster")
    assert store.active().n == 3
    assert pe.load_doc(store.active_path) == pe.load_doc(SHIPPED)

    v4 = store.save_draft(d, "Carla")
    store.reject(v4.n, "Ben")
    assert store.get(4).status == "rejected" and store.active().n == 3

    kinds = [e["kind"] for e in audit.read_events(store.audit_dir)]
    assert kinds == ["policy_snapshot", "policy_draft", "policy_approved", "policy_draft", "policy_approved",
                     "policy_draft", "policy_rejected"]
    ev = audit.read_events(store.audit_dir, kind="policy_approved")[0]
    assert (ev["user"], ev["author"], ev["version"], ev["previous"]) == ("Ben Beispiel", "Anna Muster", 2, 1)


def test_hand_edit_of_active_file_is_recorded_and_invalid_drafts_refused(store: VersionStore, doc):
    store.ensure_initial()
    store.active_path.write_text(store.active_path.read_text().replace(
        "Kein Handelswunsch auf Basis nicht öffentlicher Information.", "Kein Insiderhandel."))
    v = store.ensure_initial()
    assert (v.n, v.meta["kind"], v.status) == (2, "external", "approved") and store.active().n == 2
    bad = copy.deepcopy(doc)
    bad["families"]["trade"]["rules"][0]["when"] = "nonsense = yes"
    with pytest.raises(PolicyTableError):
        store.save_draft(bad, "Anna")
    with pytest.raises(FourEyesError):
        store.save_draft(doc, " ")


# --------------------------------------------------------------------------------------------
# the page (Streamlit AppTest, fixture results + a tmp copy of the table)
# --------------------------------------------------------------------------------------------


def test_rules_page_smoke(tmp_path, monkeypatch, table):
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from ui_fixtures import REVIEW_ID, write_fixture_env

    from callguard.ui import backend as be

    env = write_fixture_env(tmp_path, config="recommended")
    active = tmp_path / "config" / "policy_table.yaml"
    shutil.copy(SHIPPED, active)
    facts_idx = next(i for i, c in enumerate(yaml.safe_load((ROOT / "config/recommended.yaml").read_text())["checks"])
                     if c["type"] == "facts")
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tmp_path / 'tuning.yaml'}"
                       + f" --set checks.{facts_idx}.policy_table={active}")
    monkeypatch.setenv("CALLGUARD_USER", "Anna")
    path = env.result_path(REVIEW_ID)
    r = CallResult.model_validate_json(path.read_text())
    r.checks["facts"] = stored_call(REVIEW_ID, C17, table).checks["facts"]
    path.write_text(r.model_dump_json(indent=1))

    app = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=120)
    at.run()
    at.switch_page("views/rules.py").run()
    assert not at.exception, [e.message for e in at.exception]
    assert at.title[0].value == "Regelwerk"
    md = " ".join(m.value for m in at.markdown)
    assert "«Code/Wert am Telefon vorgelesen» = ja" in md
    assert "von KI vorgeschlagen" not in md
    caps = " ".join(c.value for c in at.caption)
    assert "greift bei **1 von 1** Anrufen" in caps and "FinfraG Art\\. 142" in caps
    assert (active.parent / "policy_versions" / "policy_table_v1.yaml").is_file()

    at.toggle(key="rw_on_access_access.review_1_True").set_value(False).run()
    assert not at.exception, [e.message for e in at.exception]
    at.radio(key="rw_section").set_value("preview").run()
    md = " ".join(m.value for m in at.markdown)
    assert "Diese Änderung ändert 1 von 1 Anrufen" in md and REVIEW_ID in md
    assert "Regel access\\.review\\_1 ausgeschaltet" in md

    next(b for b in at.button if b.label.startswith("Als Entwurf speichern")).click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert (active.parent / "policy_versions" / "policy_table_v2.yaml").is_file()
    assert "access.review_1" in active.read_text() and "enabled: false" not in active.read_text()  # not live yet

    at.radio(key="rw_section").set_value("versions").run()
    at.text_input(key="rw_appr_2").set_value("Anna").run()
    next(b for b in at.button if b.key == "rw_ok_2").click().run()
    assert any("Vier-Augen-Prinzip" in e.value for e in at.error)
    assert "enabled: false" not in active.read_text()
    at.text_input(key="rw_appr_2").set_value("Ben").run()
    next(b for b in at.button if b.key == "rw_ok_2").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert "enabled: false" in active.read_text()

    # bring the stored results to the approved version (rules only, from the stored fact answers)
    next(b for b in at.button if b.label.startswith("Gespeicherte Anrufe jetzt")).click().run()
    assert not at.exception, [e.message for e in at.exception]
    stored = CallResult.model_validate_json(path.read_text()).checks["facts"]
    assert stored.family_scores["access"].detail["rule"]["id"] == "access.no_alert"
    assert stored.meta["policy_table"]["version"] == 2
    kinds = [e["kind"] for e in audit.read_events(env.runs_dir) if e["kind"].startswith("policy_")]
    assert kinds == ["policy_snapshot", "policy_draft", "policy_approved", "policy_redecided"]


def test_rules_page_ai_draft_flow(tmp_path, monkeypatch, table, doc):
    """Free text -> drafter (canned) -> badge "von KI vorgeschlagen" -> working copy (never active) -> preview."""
    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest
    from ui_fixtures import write_fixture_env

    from callguard.ui import backend as be

    env = write_fixture_env(tmp_path, config="recommended")
    active = tmp_path / "config" / "policy_table.yaml"
    shutil.copy(SHIPPED, active)
    monkeypatch.setenv(be.ENV_ARGS, env.args + f" --set paths.tuning={tmp_path / 'tuning.yaml'}"
                       + f" --set checks.2.policy_table={active}")
    asked = []

    def canned(llm, d, request, names=None):
        asked.append(request)
        return rd.validate_draft(good_draft(), d, request)

    monkeypatch.setattr(rd, "draft_rule", canned)
    app = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=120)
    at.run()
    at.switch_page("views/rules.py").run()
    at.radio(key="rw_section").set_value("ai").run()
    at.text_area(key="rw_ai_request").set_value(REQUEST).run()
    next(b for b in at.button if b.label == "Entwurf erstellen").click().run()
    assert not at.exception, [e.message for e in at.exception]
    assert asked == [REQUEST]
    md = " ".join(m.value for m in at.markdown)
    assert "von KI vorgeschlagen — bitte prüfen" in md and "So liest sich die Regel" in md
    before = active.read_text()
    at.button(key="rw_ai_apply").click().run()
    assert not at.exception, [e.message for e in at.exception]
    md = " ".join(m.value for m in at.markdown)
    assert "von KI vorgeschlagen" not in md
    at.radio(key="rw_section").set_value("preview").run()
    md = " ".join(m.value for m in at.markdown)
    assert "neue Regel splitting\\.alarm\\_2" in md and "neuer Fakt «Beträge knapp unter Meldeschwelle»" in md
    assert active.read_text() == before  # nothing is active before save + four-eyes approval
    assert audit.read_events(env.runs_dir, kind="policy_ai_draft")[-1]["family"] == "splitting"
