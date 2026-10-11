"""Tests for the LLM-based checks (llm_judge, geval) and their prompt/parsing helpers.

Everything runs offline against a scripted stub LLM, except ``test_live_*`` (marked slow), which
talks to the shared local llama.cpp server and is skipped when it is not reachable.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any, Callable

import httpx
import pytest

from callguard import registry
from callguard.checks import prompts
from callguard.checks.geval import STEPS_NAMESPACE, GEvalCheck
from callguard.checks.llm_judge import LLMJudgeCheck, aggregate_samples, contiguous_runs
from callguard.config import AppConfig, Paths
from callguard.context import Context
from callguard.plugins import LLM
from callguard.types import Family, Keyword, Segment, Transcript

LIVE_URL = "http://127.0.0.1:8001/v1"
LIVE_MODEL = "qwen2.5-1.5b-instruct"


# --------------------------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------------------------


def insider_transcript() -> Transcript:
    lines = [
        ("advisor", "Guten Tag, Sie sprechen mit Herrn Meier von der Bank. Wie kann ich helfen?"),
        ("customer", "Grüezi, ich möchte heute noch Aktien der Novatec AG kaufen, für etwa fünfzigtausend Franken."),
        ("advisor", "Gerne. Darf ich fragen, was der Hintergrund für den Kauf ist?"),
        ("customer", "Mein Schwager arbeitet in der Finanzabteilung von Novatec. Er hat mir gestern unter "
                     "uns die Quartalszahlen gezeigt, die sind viel besser als erwartet."),
        ("customer", "Gerade darum möchte ich die Aktie jetzt kaufen, vor der Meldung am Freitag. "
                     "Dann steigt der Kurs sicher."),
        ("advisor", "Ich verstehe. Ich nehme den Auftrag so auf."),
    ]
    segs = [Segment(id=f"S{i + 1:03d}", start=i * 7.0, end=i * 7.0 + 6.0, text=t, role=r)
            for i, (r, t) in enumerate(lines)]
    return Transcript(call_id="synthetic_insider", segments=segs, duration=42.0)


def fam(fid: str, *, can_alarm: bool = True, policy: str = "Regel", keywords: list[Keyword] | None = None) -> Family:
    return Family(id=fid, label=f"Label {fid}", policy=policy, alarm_when=[f"alarm {fid}"],
                  not_alarm_when=[f"harmlos {fid}"], review_when=[f"unklar {fid}"],
                  can_alarm=can_alarm, keywords=keywords or [])


class StubLLM(LLM):
    """Scripted LLM: ``reply(messages, n, temperature, json_schema) -> str | list[str]``."""

    plugin_kind = "llm"
    plugin_type = "stub"

    def __init__(self, reply: Callable[..., Any] | None = None,
                 probs: dict[str, float] | Callable[..., Any] | None = None, model: str = "stub-model"):
        super().__init__(None, model=model)
        self.reply = reply or (lambda *a, **k: "")
        self.probs = probs
        self.calls: list[dict[str, Any]] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        self.calls.append({"kind": "chat", "messages": messages, "temperature": temperature, "n": n,
                           "json_schema": json_schema, "max_tokens": max_tokens})
        out = self.reply(messages, n=n, temperature=temperature, json_schema=json_schema)
        if isinstance(out, Exception):
            raise out
        return out if isinstance(out, list) else [out] * n

    def choice_probs(self, messages, choices):
        self.calls.append({"kind": "probs", "messages": messages, "choices": choices})
        out = self.probs(messages, choices) if callable(self.probs) else self.probs
        if isinstance(out, Exception):
            raise out
        return out

    def kinds(self) -> list[str]:
        return [c["kind"] for c in self.calls]


def family_of(messages: list[dict[str, str]]) -> str:
    """Family id from the "[id]" tag the prompts put after the label."""
    user = messages[-1]["content"]
    return user.split("Misconduct family: ", 1)[1].split("[", 1)[1].split("]", 1)[0]


def judge_answer(verdict: str, confidence: float, evidence: list[str], reason: str = "Grund.") -> str:
    return json.dumps({"reason": reason, "evidence": evidence, "verdict": verdict, "confidence": confidence})


@pytest.fixture
def ctx(tmp_path) -> Context:
    cfg = AppConfig(name="test", asr={"type": "reference"},
                    llms={"default": {"type": "fake", "model": "stub-model"},
                          "other": {"type": "fake", "model": "other-model"}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    return Context(cfg)


def use(ctx: Context, monkeypatch, llm: LLM) -> LLM:
    monkeypatch.setattr(ctx, "llm", lambda name="default": llm)
    return llm


# --------------------------------------------------------------------------------------------
# prompts.py helpers
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", [
    '{"verdict": "present", "confidence": 0.9}',
    'Sure! Here is the answer:\n```json\n{"verdict": "present", "confidence": 0.9}\n```\nBye',
    'prefix {"verdict": "present", "confidence": 0.9,} suffix',
    "{'verdict': 'present', 'confidence': 0.9}",
])
def test_parse_json_object_tolerates_wrapping(text):
    assert prompts.parse_json_object(text) == {"verdict": "present", "confidence": 0.9}


def test_parse_json_object_repairs_truncation():
    cut = '{"reason": "Kunde nennt Zahlen", "evidence": ["S002", "S00'
    assert prompts.parse_json_object(cut) == {"reason": "Kunde nennt Zahlen", "evidence": ["S002", "S00"]}
    cut2 = '{"reason": "x {not a brace}", "evidence": [], "verdict":'
    assert prompts.parse_json_object(cut2) == {"reason": "x {not a brace}", "evidence": []}
    assert prompts.parse_json_object("no json here") is None
    assert prompts.parse_json_object("") is None
    assert prompts.parse_json_object("[1, 2]") is None


def test_parse_verdict_confidence_digit():
    assert prompts.parse_verdict(" Present ") == "present"
    assert prompts.parse_verdict("unklar") == "undetermined"
    assert prompts.parse_verdict("maybe") is None
    assert prompts.parse_confidence("80%") == 0.8
    assert prompts.parse_confidence(85) == 0.85
    assert prompts.parse_confidence(-3) == 0.0
    assert prompts.parse_confidence("n/a") == 0.5
    assert prompts.parse_digit(" 4", 5) == 4
    assert prompts.parse_digit("Score: 7", 5) is None
    assert prompts.parse_digit("", 5) is None


def test_clean_evidence_keeps_only_real_ids_in_order():
    t = insider_transcript()
    raw = ["S005", "S2", "[S004 00:21 customer]", "S099", 1, "bogus", None, "S005"]
    assert prompts.clean_evidence(raw, t) == ["S001", "S002", "S004", "S005"]
    assert prompts.clean_evidence("S003-S005", t) == ["S003", "S004", "S005"]
    assert prompts.clean_evidence(None, t) == []


def test_parse_steps_variants():
    text = ("Here are the steps:\n1. Read the call.\n2) Find the request.\n**3. Decide** \n- extra bullet\n"
            "5. **Identify the source**: internal or public?\n")
    assert prompts.parse_steps(text) == ["Read the call.", "Find the request.", "Decide", "extra bullet",
                                         "Identify the source: internal or public?"]
    assert prompts.normalize_steps("1. a\n2. b") == ["a", "b"]
    assert prompts.normalize_steps(["1. a", "b"]) == ["a", "b"]


def test_render_transcript_truncates_middle_at_line_boundaries():
    segs = [Segment(id=f"S{i:03d}", start=i, end=i + 1, text="wort " * 20) for i in range(200)]
    t = Transcript(call_id="long", segments=segs)
    full = t.render()
    text, omitted = prompts.render_transcript(t, 2000)
    assert omitted > 0 and len(text) <= 2000
    lines = text.split("\n")
    assert lines[0] == full.split("\n")[0] and lines[-1] == full.split("\n")[-1]
    assert any("omitted" in line for line in lines)
    assert all(line in full.split("\n") for line in lines if "omitted" not in line)
    assert prompts.render_transcript(insider_transcript(), 24000) == (insider_transcript().render(), 0)


def test_prompts_contain_rules_criteria_and_language():
    f = Family(id="trade", label="Insiderhandel", policy="Kaufwunsch mit Insiderwissen.",
               alarm_when=["Kauf vor der Meldung"], not_alarm_when=["öffentliche Zahlen"],
               review_when=["Herkunft unklar"])
    t = insider_transcript()
    sys_msg, user = prompts.judge_messages(f, t.render(), "de")
    for needle in ("Swiss German", "Standard German", "recognition errors", "roles", "ONLY",
                   "undetermined", "refus", "expired", "Write every reason in German"):
        assert needle in sys_msg["content"], needle
    for needle in ("Kaufwunsch mit Insiderwissen.", "Kauf vor der Meldung", "öffentliche Zahlen",
                   "Herkunft unklar", "[S005 00:28 customer] Gerade darum", '"reason"',
                   "The reason must be written in German."):
        assert needle in user["content"], needle
    assert user["content"].index('"reason"') < user["content"].index('"verdict"')
    g = prompts.geval_messages(f, t.render(), ["a", "b"], 5, "en")
    assert g[-1]["content"].endswith("Risk score (1-5), answer with the digit only:")
    assert "1. a\n2. b" in g[-1]["content"] and "middle of the scale" in g[0]["content"]
    assert "Write every reason in English" in g[0]["content"]
    assert list(prompts.judge_schema()["properties"]) == ["reason", "evidence", "verdict", "confidence"]


# --------------------------------------------------------------------------------------------
# LLM judge
# --------------------------------------------------------------------------------------------


def test_registry_resolves_both_checks():
    assert registry.resolve("check", "llm_judge") is LLMJudgeCheck
    assert registry.resolve("check", "geval") is GEvalCheck


def test_unknown_param_raises(ctx):
    with pytest.raises(TypeError):
        LLMJudgeCheck(ctx, sampels=3)
    with pytest.raises(ValueError):
        GEvalCheck(ctx, scale=12)


def test_judge_present_findings_per_contiguous_run(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, StubLLM(lambda m, **k: judge_answer(
        "present", 0.8, ["S004", "S005", "S002", "S042"], "Kunde will vor der Meldung kaufen.")))
    check = LLMJudgeCheck(ctx)
    t = insider_transcript()
    res = check.run(t, [fam("trade")])

    fs = res.family_scores["trade"]
    assert fs.verdict == "present" and fs.score == pytest.approx(0.9) and fs.confidence == pytest.approx(0.8)
    assert fs.segment_ids == ["S002", "S004", "S005"]
    assert fs.reason == "Kunde will vor der Meldung kaufen."
    assert [f.segment_ids for f in res.findings] == [["S002"], ["S004", "S005"]]
    second = res.findings[1]
    assert (second.start, second.end) == t.span(["S004", "S005"])
    assert second.score == pytest.approx(0.9) and second.check == "llm_judge" and second.family == "trade"
    call = llm.calls[0]
    assert call["json_schema"]["required"] == ["reason", "evidence", "verdict", "confidence"]
    assert call["n"] == 1 and call["temperature"] == 0.0
    assert res.meta["model"] == "stub-model" and "errors" not in res.meta


def test_judge_absent_has_no_findings_and_undetermined_has(ctx, monkeypatch):
    answers = {"trade": judge_answer("absent", 0.9, ["S002"]),
               "access": judge_answer("undetermined", 0.4, ["S004"], "Unklar, ob öffentlich.")}
    use(ctx, monkeypatch, StubLLM(lambda m, **k: answers[family_of(m)]))
    res = LLMJudgeCheck(ctx).run(insider_transcript(), [fam("trade"), fam("access")])
    assert res.family_scores["trade"].score == pytest.approx(0.05)
    assert res.family_scores["access"].score == pytest.approx(0.5)
    assert res.family_scores["access"].verdict == "undetermined"
    assert [(f.family, f.segment_ids, f.score) for f in res.findings] == [("access", ["S004"], 0.5)]


def test_judge_self_consistency(ctx, monkeypatch):
    replies = [judge_answer("present", 0.8, ["S005"], "A"), judge_answer("present", 0.6, ["S004"], "B"),
               judge_answer("absent", 0.9, [], "C")]
    llm = use(ctx, monkeypatch, StubLLM(lambda m, n, **k: replies[:n]))
    res = LLMJudgeCheck(ctx, samples=3, temperature=0.7).run(insider_transcript(), [fam("trade")])
    fs = res.family_scores["trade"]
    assert llm.calls[0]["n"] == 3 and llm.calls[0]["temperature"] == 0.7
    assert fs.verdict == "present"
    assert fs.score == pytest.approx((0.9 + 0.8 + 0.05) / 3, abs=1e-4)
    assert fs.confidence == pytest.approx(2 / 3 * 0.7, abs=1e-4)
    assert fs.reason == "A" and fs.segment_ids == ["S004", "S005"]
    assert len(fs.detail["samples"]) == 3 and fs.detail["votes"] == {"present": 2, "absent": 1}
    assert [(f.segment_ids, f.reason) for f in res.findings] == [(["S004", "S005"], "A")]


def test_aggregate_tie_is_undetermined():
    samples = [{"verdict": "present", "confidence": 0.9, "p": 0.95},
               {"verdict": "absent", "confidence": 0.7, "p": 0.15}]
    score, verdict, conf, majority = aggregate_samples(samples)
    assert verdict == "undetermined" and score == pytest.approx(0.55)
    assert conf == pytest.approx(0.5 * 0.8) and majority == [0, 1]


def test_contiguous_runs_ignores_unknown_ids():
    t = insider_transcript()
    assert contiguous_runs(t, ["S006", "S001", "S002", "S004", "X"]) == [["S001", "S002"], ["S004"], ["S006"]]


def test_judge_family_failure_is_isolated(ctx, monkeypatch):
    def reply(m, **k):
        if family_of(m) == "access":
            return RuntimeError("server hiccup")
        return judge_answer("present", 1.0, ["S005"])
    use(ctx, monkeypatch, StubLLM(reply))
    res = LLMJudgeCheck(ctx).run(insider_transcript(), [fam("trade"), fam("access")])
    assert set(res.family_scores) == {"trade"}
    assert "server hiccup" in res.meta["errors"]["access"]


def test_judge_retries_once_on_garbage_then_reports(ctx, monkeypatch):
    replies = iter(["not json at all", judge_answer("absent", 0.7, [])])
    llm = use(ctx, monkeypatch, StubLLM(lambda m, **k: next(replies)))
    res = LLMJudgeCheck(ctx).run(insider_transcript(), [fam("trade")])
    fs = res.family_scores["trade"]
    assert fs.verdict == "absent" and fs.detail["retried"] and fs.detail["invalid"] == ["not json at all"]
    assert [c["temperature"] for c in llm.calls] == [0.0, 0.5]

    use(ctx, monkeypatch, StubLLM(lambda m, **k: "garbage"))
    with pytest.raises(RuntimeError, match="every family failed"):
        LLMJudgeCheck(ctx).run(insider_transcript(), [fam("trade")])


def test_judge_skips_non_alarm_families_unless_asked(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, StubLLM(lambda m, **k: judge_answer("absent", 0.9, [])))
    fams = [fam("trade"), fam("numbers", can_alarm=False)]
    res = LLMJudgeCheck(ctx).run(insider_transcript(), fams)
    assert set(res.family_scores) == {"trade"} and res.meta["skipped_families"] == ["numbers"]
    assert len(llm.calls) == 1
    res2 = LLMJudgeCheck(ctx, include_non_alarm=True).run(insider_transcript(), fams)
    assert set(res2.family_scores) == {"trade", "numbers"}


def test_empty_transcript_makes_no_calls(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, StubLLM())
    res = LLMJudgeCheck(ctx).run(Transcript(call_id="empty"), [fam("trade")])
    assert res.family_scores == {} and res.meta["skipped"] == "empty transcript" and llm.calls == []


def test_cache_key_tracks_criteria_model_params_not_keywords(ctx):
    check = LLMJudgeCheck(ctx)
    base = check.cache_key([fam("trade")])
    kw = Keyword(id="K01", label="Quartalszahlen", de=["Quartalszahlen"])
    assert check.cache_key([fam("trade", keywords=[kw])]) == base
    assert check.cache_key([fam("trade", policy="Neue Regel")]) != base
    assert check.cache_key([fam("trade"), fam("numbers", can_alarm=False)]) == base
    assert LLMJudgeCheck(ctx, llm="other").cache_key([fam("trade")])["llm"] == ctx.llm("other").cache_params()
    assert LLMJudgeCheck(ctx, samples=3).cache_key([fam("trade")]) != base
    assert LLMJudgeCheck(ctx, parallel=4).cache_key([fam("trade")]) == base
    assert LLMJudgeCheck(ctx, name="judge2", weight=0.3).cache_key([fam("trade")]) == base
    assert base["prompt_version"] == prompts.PROMPT_VERSION
    json.dumps(base)  # must be hashable by the pipeline cache


def test_cache_key_separates_fake_from_real_llm_with_same_model_name(tmp_path):
    def key(llm_type: str) -> dict:
        cfg = AppConfig(name="t", asr={"type": "reference"}, paths=Paths(cache_dir=str(tmp_path)),
                        llms={"default": {"type": llm_type, "base_url": "http://127.0.0.1:9/v1",
                                          "model": "qwen2.5-1.5b-instruct"}})
        return LLMJudgeCheck(Context(cfg)).cache_key([fam("trade")])

    assert key("fake") != key("openai_compat")


def test_prompts_share_the_transcript_as_prefix():
    """llama.cpp reuses the KV cache of the previous prompt's common prefix (vLLM: prefix caching), so
    the transcript must open the user message of every family's call."""
    import os

    rendered = insider_transcript().render()
    judge = [prompts.judge_messages(fam(f), rendered, "de") for f in ("trade", "access")]
    geval = [prompts.geval_messages(fam("trade"), rendered, ["Schritt"], 5, "de"),
             prompts.evidence_messages(fam("trade"), rendered, 3.0, 5, "de")]
    for a, b in (judge, geval):
        assert a[0] == b[0]  # same system prompt
        shared = os.path.commonprefix([a[1]["content"], b[1]["content"]])
        assert rendered in shared


def test_parallel_families_keep_order(ctx, monkeypatch):
    def reply(m, **k):
        time.sleep(0.01)
        return judge_answer("present", 0.5, ["S001"] if family_of(m) == "a" else ["S006"])
    use(ctx, monkeypatch, StubLLM(reply))
    res = LLMJudgeCheck(ctx, parallel=3).run(insider_transcript(), [fam("a"), fam("b"), fam("c")])
    assert list(res.family_scores) == ["a", "b", "c"]
    assert [f.family for f in res.findings] == ["a", "b", "c"]


# --------------------------------------------------------------------------------------------
# G-Eval
# --------------------------------------------------------------------------------------------


def geval_reply(steps_text: str = "1. Lies.\n2. Prüfe.\n3. Bewerte.", evidence: list[str] | None = None,
                reason: str = "Kauf vor der Meldung.", digits: list[str] | None = None):
    def reply(messages, n=1, json_schema=None, **k):
        user = messages[-1]["content"]
        if "numbered evaluation steps" in user:
            return steps_text
        if json_schema is not None:
            return json.dumps({"reason": reason, "evidence": evidence or []})
        return (digits or ["4"] * n)[:n]
    return reply


def test_geval_probability_weighted_score(ctx, monkeypatch):
    probs = {"1": 0.05, "2": 0.05, "3": 0.1, "4": 0.3, "5": 0.3}  # 0.8 mass, rest on other tokens
    llm = use(ctx, monkeypatch, StubLLM(geval_reply(evidence=["S004", "S005"]), probs=probs))
    t = insider_transcript()
    res = GEvalCheck(ctx).run(t, [fam("trade")])
    fs = res.family_scores["trade"]
    dist = {k: v / 0.8 for k, v in probs.items()}
    expected = sum(int(k) * p for k, p in dist.items())
    entropy = -sum(p * math.log(p) for p in dist.values())
    assert fs.detail["expected"] == pytest.approx(expected, abs=1e-3)
    assert fs.score == pytest.approx((expected - 1) / 4, abs=1e-3)
    assert fs.confidence == pytest.approx(1 - entropy / math.log(5), abs=1e-3)
    assert fs.verdict is None and fs.detail["method"] == "logprobs" and fs.detail["coverage"] == 0.8
    assert fs.detail["steps"] == ["Lies.", "Prüfe.", "Bewerte."] and fs.detail["steps_source"] == "auto"
    assert fs.segment_ids == ["S004", "S005"] and fs.reason.startswith("Kauf vor der Meldung.")
    assert len(res.findings) == 1 and res.findings[0].score == fs.score
    assert (res.findings[0].start, res.findings[0].end) == t.span(["S004", "S005"])
    assert llm.kinds() == ["chat", "probs", "chat"]  # steps, score, evidence
    score_msgs = llm.calls[1]["messages"]
    assert llm.calls[1]["choices"] == ["1", "2", "3", "4", "5"]
    assert "1. Lies.\n2. Prüfe.\n3. Bewerte." in score_msgs[-1]["content"]


def test_geval_steps_are_generated_once_and_cached(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, StubLLM(geval_reply(), probs={"1": 1.0}))
    GEvalCheck(ctx).run(insider_transcript(), [fam("trade")])
    assert llm.kinds() == ["chat", "probs"]  # score 0 -> below evidence_min_score, no evidence call
    assert len(list((ctx.cache.root / STEPS_NAMESPACE).glob("*.json"))) == 1

    llm2 = use(ctx, monkeypatch, StubLLM(geval_reply(), probs={"1": 1.0}))
    kw = Keyword(id="K01", label="x", de=["x"])
    res = GEvalCheck(ctx, name="fresh").run(insider_transcript(), [fam("trade", keywords=[kw])])
    assert llm2.kinds() == ["probs"]
    assert res.family_scores["trade"].detail["steps_source"] == "auto_cached"
    assert res.family_scores["trade"].score == 0.0 and res.family_scores["trade"].confidence == 1.0

    llm3 = use(ctx, monkeypatch, StubLLM(geval_reply(), probs={"1": 1.0}))
    GEvalCheck(ctx).run(insider_transcript(), [fam("trade", policy="geändert")])
    assert llm3.kinds() == ["chat", "probs"]


def test_geval_configured_and_default_steps(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, StubLLM(geval_reply(), probs={"3": 1.0}))
    res = GEvalCheck(ctx, steps={"trade": "1. Eigener Schritt\n2. Zweiter"}, locate_evidence=False
                     ).run(insider_transcript(), [fam("trade"), fam("access")])
    assert res.family_scores["trade"].detail["steps"] == ["Eigener Schritt", "Zweiter"]
    assert res.family_scores["trade"].detail["steps_source"] == "config"
    assert res.family_scores["access"].detail["steps_source"] == "auto"
    assert res.family_scores["trade"].score == pytest.approx(0.5)

    llm = use(ctx, monkeypatch, StubLLM(geval_reply(), probs={"3": 1.0}))
    res = GEvalCheck(ctx, auto_steps=False, locate_evidence=False).run(insider_transcript(), [fam("trade")])
    assert res.family_scores["trade"].detail["steps"] == prompts.DEFAULT_STEPS
    assert llm.kinds() == ["probs"]


def test_geval_step_generation_failure_falls_back_uncached(ctx, monkeypatch):
    use(ctx, monkeypatch, StubLLM(geval_reply(steps_text="I cannot help."), probs={"2": 1.0}))
    res = GEvalCheck(ctx, locate_evidence=False).run(insider_transcript(), [fam("trade")])
    d = res.family_scores["trade"].detail
    assert d["steps_source"] == "default" and "no numbered steps" in d["steps_error"]
    assert not (ctx.cache.root / STEPS_NAMESPACE).exists()


def test_geval_sampling_fallback_without_logprobs(ctx, monkeypatch):
    digits = ["5", "4", " 5.", "five", "5"]
    llm = use(ctx, monkeypatch, StubLLM(geval_reply(digits=digits), probs=None))
    res = GEvalCheck(ctx, steps={"trade": ["x"]}, locate_evidence=False, fallback_samples=5
                     ).run(insider_transcript(), [fam("trade")])
    fs = res.family_scores["trade"]
    assert fs.detail["method"] == "sampling" and fs.detail["valid"] == 4
    assert fs.detail["distribution"]["5"] == 0.75 and fs.detail["distribution"]["4"] == 0.25
    assert fs.detail["expected"] == pytest.approx(4.75)
    sample_call = llm.calls[-1]
    assert sample_call["n"] == 5 and sample_call["temperature"] == 1.0


def test_geval_logprob_errors_fall_back_and_evidence_errors_degrade(ctx, monkeypatch):
    def reply(messages, n=1, json_schema=None, **k):
        if json_schema is not None:
            return "{{{ broken"
        return ["5"] * n
    use(ctx, monkeypatch, StubLLM(reply, probs=lambda m, c: RuntimeError("no logprobs")))
    res = GEvalCheck(ctx, steps={"trade": ["x"]}).run(insider_transcript(), [fam("trade")])
    fs = res.family_scores["trade"]
    assert fs.score == 1.0 and fs.detail["method"] == "sampling"
    assert "no logprobs" in fs.detail["logprobs_error"]
    assert "evidence_error" in fs.detail and res.findings == []


def test_geval_scale_and_evidence_threshold(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, StubLLM(geval_reply(evidence=["S005"]), probs={"1": 0.5, "2": 0.5, "3": 0.0}))
    res = GEvalCheck(ctx, scale=3, steps={"trade": ["x"]}, evidence_min_score=0.3
                     ).run(insider_transcript(), [fam("trade")])
    assert llm.calls[0]["choices"] == ["1", "2", "3"]
    assert res.family_scores["trade"].score == pytest.approx(0.25)
    assert res.findings == [] and llm.kinds() == ["probs"]


def test_geval_cache_key_ignores_keywords(ctx):
    check = GEvalCheck(ctx)
    base = check.cache_key([fam("trade")])
    assert check.cache_key([fam("trade", keywords=[Keyword(id="K", label="k")])]) == base
    assert GEvalCheck(ctx, steps={"trade": ["a"]}).cache_key([fam("trade")]) != base
    assert check.steps_key(fam("trade")) == check.steps_key(fam("trade", keywords=[Keyword(id="K", label="k")]))


# --------------------------------------------------------------------------------------------
# Live (slow): the shared local llama.cpp server
# --------------------------------------------------------------------------------------------


class LiveLLM(LLM):
    """Minimal OpenAI-compatible client for the llama-cpp-python server dialect."""

    plugin_kind = "llm"
    plugin_type = "live_stub"

    def __init__(self, base_url: str = LIVE_URL, model: str = LIVE_MODEL):
        super().__init__(None, model=model)
        self.http = httpx.Client(base_url=base_url, timeout=300)

    def _post(self, body: dict) -> dict:
        r = self.http.post("/chat/completions", json={"model": self.model_id, **body})
        r.raise_for_status()
        return r.json()

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        body: dict[str, Any] = {"messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        if json_schema is not None:
            body["response_format"] = {"type": "json_object", "schema": json_schema}
        return [self._post(body)["choices"][0]["message"]["content"] for _ in range(n)]

    def choice_probs(self, messages, choices):
        data = self._post({"messages": messages, "temperature": 0.0, "max_tokens": 1,
                           "logprobs": True, "top_logprobs": 20})
        top = data["choices"][0]["logprobs"]["content"][0]["top_logprobs"]
        out = {c: 0.0 for c in choices}
        for t in top:
            tok = t["token"].strip()
            if tok in out:
                out[tok] += math.exp(t["logprob"])
        return out


@pytest.fixture
def live_ctx(tmp_path, monkeypatch) -> Context:
    try:
        httpx.get(f"{LIVE_URL}/models", timeout=2).raise_for_status()
    except Exception:
        pytest.skip("local LLM server not reachable")
    cfg = AppConfig(name="live", asr={"type": "reference"}, llms={"default": {"type": "fake", "model": LIVE_MODEL}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    c = Context(cfg)
    llm = LiveLLM()
    monkeypatch.setattr(c, "llm", lambda name="default": llm)
    return c


@pytest.mark.slow
def test_live_both_checks_on_insider_call(live_ctx):
    trade = next(f for f in live_ctx.families() if f.id == "trade")
    t = insider_transcript()

    t0 = time.time()
    judge = LLMJudgeCheck(live_ctx).run(t, [trade])
    t_judge = time.time() - t0
    t0 = time.time()
    geval = GEvalCheck(live_ctx).run(t, [trade])
    t_geval = time.time() - t0

    for name, res, secs in (("llm_judge", judge, t_judge), ("geval", geval, t_geval)):
        fs = res.family_scores.get("trade")
        print(f"\n[{name}] {secs:.1f}s meta={res.meta}")
        print(f"  score={fs and fs.score} confidence={fs and fs.confidence} verdict={fs and fs.verdict}")
        print(f"  reason={fs and fs.reason!r} segments={fs and fs.segment_ids}")
        if fs and "distribution" in fs.detail:
            print(f"  distribution={fs.detail['distribution']} steps={fs.detail['steps']}")
        for f in res.findings:
            print(f"  finding {f.segment_ids} {f.start}-{f.end}s score={f.score} reason={f.reason!r}")

    assert "trade" in judge.family_scores and "trade" in geval.family_scores
    assert judge.family_scores["trade"].verdict in prompts.VERDICTS
    assert 0.0 <= geval.family_scores["trade"].score <= 1.0
