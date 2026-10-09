"""Tests for the fact sheet + policy table check (checks/facts.py): rule language, table validation,
scoring, evidence, prefix-max, caching. Everything offline against a scripted LLM."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

import pytest

from callguard import registry
from callguard.checks import fact_prompts as fp
from callguard.checks.facts import (
    PROBE_NAMESPACE,
    FactSheetCheck,
    PolicyTableError,
    discretize,
    eval_hard,
    eval_soft,
    load_policy_table,
    parse_policy_table,
    parse_rule,
    prefix_cuts,
    rule_facts,
)
from callguard.config import ROOT, AppConfig, Paths
from callguard.context import Context
from callguard.families import load_families
from callguard.plugins import LLM
from callguard.types import Family, Segment, Transcript

# --------------------------------------------------------------------------------------------
# rule language
# --------------------------------------------------------------------------------------------


def test_parse_and_hard_eval_precedence():
    node = parse_rule("a = yes and b != no or not c in [yes, unclear]")
    assert node[0] == "or"  # and binds tighter than or
    assert eval_hard(node, {"a": "yes", "b": "yes", "c": "yes"})
    assert eval_hard(node, {"a": "no", "b": "yes", "c": "no"})  # not c in [...] holds
    assert not eval_hard(node, {"a": "no", "b": "yes", "c": "unclear"})
    assert eval_hard(parse_rule("(a = yes or b = yes) and c == no"), {"a": "no", "b": "yes", "c": "no"})
    assert eval_hard(parse_rule("a not in [no]"), {"a": "unclear"})
    assert eval_hard(parse_rule("TRUE"), {})
    assert eval_hard(parse_rule("a = unclear"), {})  # a fact without a value is unclear


def test_value_aliases():
    assert parse_rule("a = ja") == parse_rule("a = yes")
    assert parse_rule("a = unklar") == parse_rule("a = unknown") == parse_rule("a = unclear")
    assert parse_rule("a = nein") == parse_rule("a = no")


@pytest.mark.parametrize("bad", [
    "", "a", "a = maybe", "a = yes and", "a = yes b = no", "(a = yes", "a in [yes", "a > yes",
    "__import__('os').system('x')", "a = yes; b = no", "and = yes", "a in yes",
])
def test_parse_errors(bad):
    with pytest.raises(PolicyTableError):
        parse_rule(bad)


def test_unknown_fact_rejected():
    with pytest.raises(PolicyTableError, match="unknown fact 'x'"):
        parse_rule("x = yes", {"a", "b"})


def test_soft_eval():
    probs = {"a": {"yes": 0.9, "no": 0.05, "unclear": 0.05}, "b": {"yes": 0.2, "no": 0.7, "unclear": 0.1}}
    assert eval_soft(parse_rule("a = yes"), probs) == pytest.approx(0.9)
    assert eval_soft(parse_rule("a = yes and b != yes"), probs) == pytest.approx(0.9 * 0.8)
    assert eval_soft(parse_rule("a = no or b = no"), probs) == pytest.approx(1 - 0.95 * 0.3)
    assert eval_soft(parse_rule("b in [yes, unclear]"), probs) == pytest.approx(0.3)
    assert eval_soft(parse_rule("c = unclear"), probs) == pytest.approx(1.0)
    assert eval_soft(parse_rule("true"), probs) == 1.0


def test_rule_facts_and_discretize():
    assert rule_facts(parse_rule("a = yes and (b = no or a = unclear) and not c = yes")) == ["a", "b", "c"]
    assert discretize({"yes": 0.5, "no": 0.4, "unclear": 0.1}) == "yes"
    assert discretize({"yes": 0.3, "no": 0.6, "unclear": 0.1}) == "no"
    assert discretize({"yes": 0.45, "no": 0.4, "unclear": 0.15}) == "unclear"
    assert discretize({"yes": 0.7, "no": 0.3}, decide_at=0.8) == "unclear"


def test_prefix_cuts():
    assert prefix_cuts(12, 3) == [3, 6, 9]
    assert prefix_cuts(2, 3) == [1]
    assert prefix_cuts(1, 3) == []


# --------------------------------------------------------------------------------------------
# policy table
# --------------------------------------------------------------------------------------------

TABLE = """
families:
  access:
    facts:
      - {id: spoken, label: Code ausgesprochen, role: act, de: "Wurde ein Code ausgesprochen? MARK_SPOKEN", en: "Was a code said? MARK_SPOKEN"}
      - {id: current, label: Code gültig, role: context, de: "Ist der Code gültig? MARK_CURRENT"}
      - {id: expired, label: Code abgelaufen, role: exculpatory, de: "Ist der Code abgelaufen? MARK_EXPIRED"}
    rules:
      - {id: access.alarm_1, label: alarm, when: spoken = yes and current = yes and expired != yes, text: Gültiger Code genannt.}
      - {id: access.review_1, label: review, when: spoken = yes and current = unclear, text: Gültigkeit offen.}
      - {id: access.no_alert, label: no_alert, when: "true"}
"""


def test_table_validation_errors():
    base = {"families": {"x": {"facts": [{"id": "a", "role": "act", "de": "Frage?"}],
                               "rules": [{"id": "r", "label": "alarm", "when": "a = yes"}]}}}
    assert parse_policy_table(base).families["x"].rules[0].id == "r"

    def broken(**patch: Any) -> dict:
        d = json.loads(json.dumps(base))
        for path, value in patch.items():
            kind, key = path.split("__")
            d["families"]["x"][kind][0][key] = value
        return d

    for bad in (broken(facts__role="actor"), broken(facts__id="a b"), broken(facts__de=""),
                broken(rules__label="maybe"), broken(rules__when="b = yes"), broken(facts__colour="x"),
                {"families": {"x": {"facts": []}}}, {"nofamilies": 1}):
        with pytest.raises(PolicyTableError):
            parse_policy_table(bad)
    dup = json.loads(json.dumps(base))
    dup["families"]["x"]["facts"].append(dict(dup["families"]["x"]["facts"][0]))
    with pytest.raises(PolicyTableError, match="duplicate fact"):
        parse_policy_table(dup)


def test_shipped_table_covers_every_alarm_family():
    table = load_policy_table("config/policy_table.yaml")
    fams = load_families(ROOT / "config/keywords.json", ROOT / "config/criteria.yaml")
    alarm_fams = {f.id for f in fams if f.can_alarm}
    assert alarm_fams <= set(table.families)
    for fid, ft in table.families.items():
        assert 3 <= len(ft.facts) <= 5, fid
        assert any(f.role == "act" for f in ft.facts), fid
        assert {r.label for r in ft.rules} >= {"alarm", "no_alert"}, fid
        assert all(f.en and f.de for f in ft.facts), fid


def test_shipped_table_decisions():
    t = load_policy_table("config/policy_table.yaml").families
    acc = t["access"]
    assert acc.decide({"spoken": "yes", "current": "yes", "expired_or_sample": "no"}).id == "access.alarm_1"
    assert acc.decide({"spoken": "yes", "current": "yes", "expired_or_sample": "yes"}).label == "no_alert"
    assert acc.decide({"spoken": "yes", "current": "unclear", "validity_open": "yes",
                       "expired_or_sample": "no"}).label == "review"
    # the model's default "unknown" on validity alone is no reason for review
    assert acc.decide({"spoken": "yes", "current": "unclear", "validity_open": "no"}).label == "no_alert"
    assert acc.decide({"spoken": "no", "current": "unclear", "validity_open": "yes"}).label == "no_alert"
    trade = t["trade"]
    assert trade.decide({"wish": "yes", "inside_info": "yes", "public": "no"}).label == "alarm"
    assert trade.decide({"wish": "yes", "inside_info": "yes", "public": "yes"}).label == "no_alert"
    dis = t["disclosure"]
    assert dis.decide({"data_given": "yes", "not_authorized": "yes"}).id == "disclosure.alarm_1"
    assert dis.decide({"data_given": "yes", "authorized": "yes", "not_authorized": "no",
                       "beyond_scope": "no"}).label == "no_alert"
    assert dis.decide({"data_given": "yes", "authorized": "unclear", "not_authorized": "no",
                       "beyond_scope": "no"}).id == "disclosure.review_1"
    assert dis.decide({"data_given": "no", "third_party_request": "yes", "authorized": "unclear",
                       "not_authorized": "unclear"}).id == "disclosure.review_2"
    assert dis.decide({"data_given": "no", "third_party_request": "yes", "authorized": "unclear",
                       "not_authorized": "yes"}).label == "no_alert"


# --------------------------------------------------------------------------------------------
# the check, against a scripted LLM
# --------------------------------------------------------------------------------------------


class FactLLM(LLM):
    """``answers``: marker in the question -> {yes, no, unknown} probabilities (default: clear no).
    A marker may map to a list: one distribution per call, in order (for prefix probes)."""

    plugin_kind = "llm"
    plugin_type = "factstub"

    def __init__(self, answers: dict[str, Any] | None = None, logprobs: bool = True,
                 samples: list[str] | None = None, evidence: dict[str, Any] | None = None):
        super().__init__(None, model="fact-stub")
        self.answers = answers or {}
        self.logprobs = logprobs
        self.samples = samples or []
        self.evidence = evidence or {"reason": "Kunde liest den Code vor.", "evidence": ["S002", "S003"]}
        self.calls: list[dict[str, Any]] = []

    def _marker(self, messages) -> str | None:
        q = messages[-1]["content"].split("Question:", 1)[1]
        return next((m for m in self.answers if m in q), None)

    def choice_probs(self, messages, choices):
        self.calls.append({"kind": "probs", "choices": list(choices), "messages": messages})
        if isinstance(self.logprobs, Exception):
            raise self.logprobs
        if not self.logprobs:
            return None
        m = self._marker(messages)
        dist = self.answers.get(m, {"yes": 0.02, "no": 0.95, "unknown": 0.03})
        if isinstance(dist, list):
            dist = dist.pop(0) if len(dist) > 1 else dist[0]
        return dict(dist)

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        self.calls.append({"kind": "chat", "json_schema": json_schema, "n": n, "messages": messages})
        if json_schema:
            ev = self.evidence
            if isinstance(ev, Exception):
                raise ev
            return [json.dumps(ev)] * n
        return list(self.samples[:n]) or ["yes"] * n

    def kinds(self) -> list[str]:
        return [c["kind"] for c in self.calls]


def transcript(n: int = 6) -> Transcript:
    texts = ["Grüezi, Bank Muster.", "Ich lese Ihnen den Code vor:", "vier sieben eins neun",
             "Danke.", "Bitte keine Codes mehr vorlesen.", "Adieu."]
    roles = ["advisor", "customer", "customer", "advisor", "advisor", "customer"]
    segs = [Segment(id=f"S{i + 1:03d}", start=i * 5.0, end=i * 5.0 + 4.0, text=texts[i % 6], role=roles[i % 6],
                    speaker=f"SPK{i % 2}") for i in range(n)]
    return Transcript(call_id="t1", segments=segs, duration=n * 5.0)


ACCESS = Family(id="access", label="Zugangsinformation preisgegeben", policy="p")
YES = {"yes": 0.9, "no": 0.05, "unknown": 0.05}
NO = {"yes": 0.03, "no": 0.95, "unknown": 0.02}
UNK = {"yes": 0.2, "no": 0.2, "unknown": 0.6}


@pytest.fixture
def table_path(tmp_path) -> Path:
    p = tmp_path / "policy_table.yaml"
    p.write_text(textwrap.dedent(TABLE))
    return p


@pytest.fixture
def ctx(tmp_path) -> Context:
    cfg = AppConfig(name="test", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    return Context(cfg)


def use(ctx: Context, monkeypatch, llm: LLM) -> LLM:
    monkeypatch.setattr(ctx, "llm", lambda name="default": llm)
    return llm


def make(ctx, table_path, **kw) -> FactSheetCheck:
    return FactSheetCheck(ctx, policy_table=str(table_path), **kw)


def test_registry_and_answer_tokens():
    assert registry.resolve("check", "facts") is FactSheetCheck
    assert list(fp.ANSWERS) == ["yes", "no", "unknown"]  # single tokens in the Qwen2.5 tokenizer
    assert fp.parse_answer("Yes.") == "yes" and fp.parse_answer(" unklar") == "unclear"
    assert fp.parse_answer("Nein, ...") == "no" and fp.parse_answer("???") is None
    assert fp.probs_from_choices({"yes": 0.2, "no": 0.2, "unknown": 0.1}) == pytest.approx(
        {"yes": 0.4, "no": 0.4, "unclear": 0.2})


def test_unknown_param_and_bad_values(ctx, table_path):
    with pytest.raises(TypeError):
        make(ctx, table_path, prefix_maks=True)
    with pytest.raises(ValueError):
        make(ctx, table_path, question_lang="fr")
    with pytest.raises(ValueError):
        make(ctx, table_path, decide_at=0.2)
    with pytest.raises(PolicyTableError):
        FactSheetCheck(ctx, policy_table=str(table_path.parent / "missing.yaml"))


def test_alarm_with_facts_rule_and_findings(ctx, monkeypatch, table_path):
    llm = use(ctx, monkeypatch, FactLLM({"MARK_SPOKEN": YES, "MARK_CURRENT": YES, "MARK_EXPIRED": NO}))
    res = make(ctx, table_path).run(transcript(), [ACCESS])
    fs = res.family_scores["access"]
    p_rule = 0.9 * 0.9 * (1 - 0.03)
    assert fs.verdict == "present"
    assert fs.score == pytest.approx(0.6 + 0.4 * p_rule, abs=1e-3)
    assert fs.confidence == pytest.approx(p_rule, abs=1e-3)
    d = fs.detail
    assert d["rule"]["id"] == "access.alarm_1" and d["decision"] == "alarm"
    assert d["facts"]["spoken"]["value"] == "yes" and d["facts"]["spoken"]["p"]["yes"] == pytest.approx(0.9)
    assert d["facts"]["spoken"]["method"] == "logprobs"
    assert "Regel: access.alarm_1" in fs.reason and "Code ausgesprochen = ja (0.90)" in fs.reason
    # evidence: one call per yes-fact (spoken, current), exculpatory "expired" is no -> none
    assert llm.kinds().count("probs") == 3 and llm.kinds().count("chat") == 2
    assert all(c["choices"] == ["yes", "no", "unknown"] for c in llm.calls if c["kind"] == "probs")
    assert fs.segment_ids == ["S002", "S003"]
    assert res.findings and res.findings[0].segment_ids == ["S002", "S003"]
    assert res.findings[0].reason.startswith("Fakt: Code ausgesprochen = ja (0.90) - Kunde liest")
    assert "(Regel: access.alarm_1)" in res.findings[0].reason
    assert res.meta["llm_calls"] == 5 and res.meta["cached_probes"] == 0
    assert res.meta["prompt_version"] == fp.PROMPT_VERSION
    # English question by default; transcript first (shared prefix), then the question
    user = llm.calls[0]["messages"][-1]["content"]
    assert user.startswith("Transcript of the call") and "Question: Was a code said?" in user
    assert "[S002 00:05 customer]" in user


def test_review_when_context_unclear(ctx, monkeypatch, table_path):
    use(ctx, monkeypatch, FactLLM({"MARK_SPOKEN": YES, "MARK_CURRENT": UNK}))
    fs = make(ctx, table_path, evidence=False).run(transcript(), [ACCESS]).family_scores["access"]
    assert fs.verdict == "undetermined" and fs.score == 0.5 and fs.confidence == 0.3
    assert fs.detail["rule"]["id"] == "access.review_1"
    assert fs.detail["facts"]["current"]["value"] == "unclear"
    assert "unklar (ja 0.20, nein 0.20)" in fs.reason


def test_exculpatory_fact_turns_alarm_into_no_alert(ctx, monkeypatch, table_path):
    llm = use(ctx, monkeypatch, FactLLM({"MARK_SPOKEN": YES, "MARK_CURRENT": YES, "MARK_EXPIRED": YES}))
    res = make(ctx, table_path).run(transcript(), [ACCESS])
    fs = res.family_scores["access"]
    assert fs.verdict == "absent" and fs.detail["rule"]["id"] == "access.no_alert"
    p_alarm = 0.9 * 0.9 * 0.1
    assert fs.score == pytest.approx(0.4 * p_alarm, abs=1e-3)
    assert fs.score < 0.4
    # evidence for all three yes-facts; the exculpatory one stays in the detail ("why not an alarm")
    assert llm.kinds().count("chat") == 3
    assert fs.detail["facts"]["expired"]["evidence"] == ["S002", "S003"]
    assert all(f.detail["fact"] != "expired" for f in res.findings)
    assert "Code abgelaufen = ja" in fs.reason


def test_clear_no_is_confident_and_low(ctx, monkeypatch, table_path):
    llm = use(ctx, monkeypatch, FactLLM())
    res = make(ctx, table_path).run(transcript(), [ACCESS])
    fs = res.family_scores["access"]
    assert fs.verdict == "absent" and fs.score < 0.01 and fs.confidence > 0.9
    assert not res.findings and llm.kinds().count("chat") == 0  # nothing above evidence_min


def test_sampling_fallback_and_logprob_errors(ctx, monkeypatch, table_path):
    use(ctx, monkeypatch, FactLLM(logprobs=False, samples=["yes", "Yes.", "no", "unknown", "yes"]))
    fs = make(ctx, table_path, evidence=False).run(transcript(), [ACCESS]).family_scores["access"]
    f = fs.detail["facts"]["spoken"]
    assert f["method"] == "sampling" and f["p"] == pytest.approx({"yes": 0.6, "no": 0.2, "unclear": 0.2})

    use(ctx, monkeypatch, FactLLM(logprobs=RuntimeError("boom"), samples=["no"] * 5))
    fs = make(ctx, table_path, evidence=False, question_lang="de").run(transcript(), [ACCESS]).family_scores["access"]
    f = fs.detail["facts"]["spoken"]
    assert f["method"] == "sampling" and "boom" in f["info"]["logprobs_error"]


def test_all_garbage_fails_family_visibly(ctx, monkeypatch, table_path):
    use(ctx, monkeypatch, FactLLM(logprobs=False, samples=["???"] * 5))
    with pytest.raises(RuntimeError, match="every family failed"):
        make(ctx, table_path).run(transcript(), [ACCESS])


def test_evidence_error_is_reported_not_fatal(ctx, monkeypatch, table_path):
    use(ctx, monkeypatch, FactLLM({"MARK_SPOKEN": YES, "MARK_CURRENT": YES}, evidence=ValueError("bad json")))
    res = make(ctx, table_path).run(transcript(), [ACCESS])
    assert res.family_scores["access"].verdict == "present" and not res.findings
    assert "spoken" in res.meta["evidence_errors"]["access"]


def test_probe_cache_makes_rule_edits_free(ctx, monkeypatch, table_path):
    llm = use(ctx, monkeypatch, FactLLM({"MARK_SPOKEN": YES, "MARK_CURRENT": UNK}))
    check = make(ctx, table_path, evidence=False)
    t = transcript()
    key1 = check.cache_key([ACCESS])
    first = check.run(t, [ACCESS]).family_scores["access"]
    assert first.detail["decision"] == "review" and llm.kinds().count("probs") == 3

    # a comment edit keeps the check key; a rule edit changes it but reuses every fact probe
    table_path.write_text(textwrap.dedent(TABLE) + "\n# officer note\n")
    assert check.cache_key([ACCESS]) == key1
    table_path.write_text(textwrap.dedent(TABLE).replace("current = unclear, text", "current = unclear and spoken = no, text"))
    import os
    os.utime(table_path, (1, 1))  # make sure the mtime differs even on coarse filesystems
    assert check.cache_key([ACCESS]) != key1
    second = check.run(t, [ACCESS])
    assert second.family_scores["access"].detail["decision"] == "no_alert"
    assert llm.kinds().count("probs") == 3  # no new LLM calls
    assert second.meta["cached_probes"] == 3 and second.meta["llm_calls"] == 0
    assert list((Path(ctx.cache.root) / PROBE_NAMESPACE).rglob("*.json"))


def test_cache_key_tracks_params_and_lang_not_speed(ctx, table_path):
    a = make(ctx, table_path).cache_key([ACCESS])
    assert make(ctx, table_path, parallel=4).cache_key([ACCESS]) == a
    assert make(ctx, table_path, question_lang="de").cache_key([ACCESS]) != a
    assert make(ctx, table_path, prefix_max=True).cache_key([ACCESS]) != a
    assert a["prompt_version"] == fp.PROMPT_VERSION


def test_prefix_max_keeps_the_act(ctx, monkeypatch, table_path):
    # full call says "no" (a later refusal), the 2nd prefix says "yes": prefix-max keeps the act
    seq = [{"yes": 0.1, "no": 0.85, "unknown": 0.05}, {"yes": 0.3, "no": 0.6, "unknown": 0.1},
           {"yes": 0.92, "no": 0.05, "unknown": 0.03}, {"yes": 0.4, "no": 0.5, "unknown": 0.1}]
    llm = use(ctx, monkeypatch, FactLLM({"MARK_SPOKEN": seq, "MARK_CURRENT": YES}))
    res = make(ctx, table_path, prefix_max=True, evidence=False).run(transcript(12), [ACCESS])
    fs = res.family_scores["access"]
    spoken = fs.detail["facts"]["spoken"]
    assert spoken["value"] == "yes" and spoken["p"]["yes"] == pytest.approx(0.92)
    assert spoken["prefix"] == {"full": pytest.approx(0.1), "3/12": 0.3, "6/12": 0.92, "9/12": 0.4}
    assert spoken["prefix_used"] == 6
    assert fs.detail["rule"]["id"] == "access.alarm_1"
    # only the act fact is asked on prefixes: 3 full + 3 prefixes
    assert llm.kinds().count("probs") == 6
    prefix_prompts = [c["messages"][-1]["content"] for c in llm.calls if c["kind"] == "probs"][3:]
    assert "[S003" in prefix_prompts[0] and "[S004" not in prefix_prompts[0]


def test_roles_false_hides_advisor_customer(ctx, monkeypatch, table_path):
    llm = use(ctx, monkeypatch, FactLLM())
    make(ctx, table_path, roles=False, evidence=False).run(transcript(), [ACCESS])
    user = llm.calls[0]["messages"][-1]["content"]
    assert "customer" not in user.split("</transcript>")[0] and "[S002 00:05 SPK1]" in user


def test_families_without_sheet_or_alarm_are_skipped(ctx, monkeypatch, table_path):
    llm = use(ctx, monkeypatch, FactLLM())
    fams = [ACCESS, Family(id="trade", label="T"), Family(id="numbers", label="N", can_alarm=False)]
    res = make(ctx, table_path).run(transcript(), fams)
    assert set(res.family_scores) == {"access"}
    assert set(res.meta["skipped_families"]) == {"trade", "numbers"}
    assert all("[access]" in c["messages"][-1]["content"] for c in llm.calls)


def test_runs_with_the_offline_fake_llm(tmp_path):
    """demo-offline path: the cue-word FakeLLM answers the single-token choices without a server."""
    cfg = AppConfig(name="test", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    ctx = Context(cfg)
    fams = load_families(ROOT / "config/keywords.json", ROOT / "config/criteria.yaml")
    segs = [Segment(id="S001", start=0, end=3, text="Grüezi.", role="advisor"),
            Segment(id="S002", start=3, end=6, text="Meine TAN ist 4711 9876.", role="customer")]
    res = FactSheetCheck(ctx).run(Transcript(call_id="x", segments=segs), fams)
    assert set(res.family_scores) == {"trade", "access", "disclosure", "documentation", "splitting"}
    assert res.family_scores["access"].detail["facts"]["spoken"]["value"] == "yes"
    assert res.family_scores["trade"].verdict == "absent"
    assert "errors" not in res.meta
