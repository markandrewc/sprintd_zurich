"""Offline tests of the passage-level checks (keyword_context, anchored, semantic_windows) and the
quote-grounded judge. LLM = the deterministic fake (llm/fake.py) or a scripted stub."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from callguard import registry
from callguard.checks import window_prompts
from callguard.checks.keyword_context import AnchoredProbeCheck, KeywordContextCheck
from callguard.checks.quote_judge import DOWNGRADE_NOTE, QuoteJudgeCheck, verify_quote
from callguard.checks.semantic import FakeEmbedder, OpenAIEmbedder, SemanticWindowCheck, make_embedder
from callguard.config import AppConfig, Paths
from callguard.context import Context
from callguard.llm.fake import FakeLLM
from callguard.plugins import LLM
from callguard.types import Family, Keyword, Segment, Transcript


def make_transcript(lines: list[tuple[str, str]], call_id: str = "c1", lang: str | None = None) -> Transcript:
    segs = [Segment(id=f"S{i + 1:03d}", start=i * 5.0, end=i * 5.0 + 4.5, text=t, role=r)
            for i, (r, t) in enumerate(lines)]
    return Transcript(call_id=call_id, segments=segs, duration=len(lines) * 5.0, lang=lang)


FILLER = [("advisor", "Haben Sie sonst noch Fragen zu Ihrem Konto?"), ("customer", "Nein, das wäre alles soweit.")]


def insider_call() -> Transcript:
    return make_transcript([
        ("advisor", "Guten Tag, Bank Meier, wie kann ich helfen?"),
        ("customer", "Ich möchte Aktien der Novatec kaufen."),
        ("customer", "Mein Schwager in der Finanzabteilung hat mir die Quartalszahlen gezeigt, unter uns."),
        ("customer", "Darum will ich unbedingt vor der Meldung am Freitag kaufen."),
        ("advisor", "Ich nehme den Auftrag auf."),
        *FILLER * 4,
    ], call_id="insider")


def harmless_call() -> Transcript:
    return make_transcript([
        ("advisor", "Guten Tag, Bank Meier."),
        ("customer", "Ich habe eine Frage zu den Quartalszahlen der Novatec, die gestern publiziert wurden."),
        ("advisor", "Die Quartalszahlen sind öffentlich, die Medienmitteilung finden Sie online."),
        *FILLER * 3,
        ("customer", "Und was bedeutet eigentlich Insiderhandel genau?"),
        ("advisor", "Das ist der Handel mit vertraulichen Informationen, das ist verboten."),
    ], call_id="harmless")


def trade_family() -> Family:
    return Family(
        id="trade", label="Insiderhandel", policy="Kaufwunsch mit nicht öffentlicher Information.",
        alarm_when=["Kaufwunsch vor der Meldung wegen interner Information"],
        not_alarm_when=["Begriffe werden nur erklärt"], review_when=["Herkunft unklar"],
        keywords=[
            Keyword(id="K03", label="Marktrelevanter Inhalt", de=["Quartalszahlen", "Insiderhandel"],
                    en=["quarterly figures"], harmless="Öffentliche Meldungen werden sachlich erläutert."),
            Keyword(id="K04", label="Zeitpunkt", de=["vor der Meldung"], harmless="Zitat oder Verneinung."),
        ])


def access_family() -> Family:
    return Family(id="access", label="Zugangsinformation", policy="Gültige Codes werden vorgelesen.",
                  alarm_when=["Kunde liest TAN vor"], keywords=[Keyword(id="K10", label="Code", de=["TAN"])])


@pytest.fixture
def ctx(tmp_path) -> Context:
    cfg = AppConfig(name="test", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                    paths=Paths(cache_dir=str(tmp_path / "cache")))
    return Context(cfg)


class Spy(LLM):
    """Wraps a real LLM and records every prompt."""

    plugin_kind = "llm"
    plugin_type = "spy"

    def __init__(self, inner: LLM, fail_probs: bool | int = False):
        super().__init__(None)
        self.inner = inner
        self.prompts: list[tuple[str, str]] = []
        self.fail_probs = fail_probs

    def chat(self, messages, **kw):
        self.prompts.append(("chat", messages[-1]["content"]))
        return self.inner.chat(messages, **kw)

    def choice_probs(self, messages, choices):
        self.prompts.append(("probs", messages[-1]["content"]))
        if self.fail_probs is True or (self.fail_probs and len([p for p in self.prompts if p[0] == "probs"]) == self.fail_probs):
            raise RuntimeError("server down")
        return self.inner.choice_probs(messages, choices)

    @property
    def model_id(self) -> str:
        return "spy"


def use(ctx, monkeypatch, llm: LLM) -> LLM:
    monkeypatch.setattr(ctx, "llm", lambda name="default": llm)
    return llm


def fake(ctx) -> FakeLLM:
    return FakeLLM(ctx)


# --------------------------------------------------------------------------------------------
# registry / params
# --------------------------------------------------------------------------------------------


def test_registry_resolves_new_checks(ctx):
    for name, cls in (("keyword_context", KeywordContextCheck), ("anchored", AnchoredProbeCheck),
                      ("semantic_windows", SemanticWindowCheck), ("quote_judge", QuoteJudgeCheck)):
        assert registry.resolve("check", name) is cls
    c = registry.create("check", {"type": "keyword_context", "view": "de", "window": 2}, ctx=ctx)
    assert c.view == "de" and c.window == 2 and "view" not in c.cache_params()
    a = registry.create("check", {"type": "anchored"}, ctx=ctx)
    assert a.context == "full" and a.window == 0


@pytest.mark.parametrize("cls,bad", [
    (KeywordContextCheck, {"context": "nope"}), (KeywordContextCheck, {"window": -1}),
    (KeywordContextCheck, {"typo_param": 1}), (KeywordContextCheck, {"empty": "maybe"}),
    (SemanticWindowCheck, {"embedder": {"type": "nope"}}), (SemanticWindowCheck, {"sim_ceil": 0.1}),
    (QuoteJudgeCheck, {"min_ratio": 0}),
])
def test_bad_params_raise(ctx, cls, bad):
    with pytest.raises((ValueError, TypeError)):
        cls(ctx, **({"embedder": {"type": "fake"}} if cls is SemanticWindowCheck and "embedder" not in bad else {}), **bad)


# --------------------------------------------------------------------------------------------
# keyword_context
# --------------------------------------------------------------------------------------------


def test_keyword_context_flags_insider_window_and_pins_findings(ctx, monkeypatch):
    spy = use(ctx, monkeypatch, Spy(fake(ctx)))
    check = KeywordContextCheck(ctx, window=1)
    res = check.run(insider_call(), [trade_family()])
    fs = res.family_scores["trade"]
    assert fs.score > 0.5
    # hits in S003 (Quartalszahlen) and S004 (vor der Meldung) share one passage S002-S005
    assert fs.detail["passages"] == 1
    assert fs.detail["windows"][0]["segment_ids"] == ["S002", "S003", "S004", "S005"]
    assert res.findings and all(set(f.segment_ids) <= {"S002", "S003", "S004", "S005"} for f in res.findings)
    probe = next(p for kind, p in spy.prompts if kind == "probs")
    assert "S009" not in probe  # window mode: only the passage is shown
    assert "harmless when: Öffentliche Meldungen" in probe and "Passage to rate (segments S002-S005" in probe
    assert res.meta["llm_calls"] == len(spy.prompts) and res.meta["llm_calls"] >= 2
    assert res.meta["window_prompt_version"] == window_prompts.PROMPT_VERSION
    assert not res.meta.get("errors")


def test_keyword_context_scores_harmless_keyword_call_low(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))
    res = KeywordContextCheck(ctx).run(harmless_call(), [trade_family()])
    fs = res.family_scores["trade"]
    assert fs.detail["hits"] >= 3 and fs.score < 0.3
    assert res.findings == []  # nothing above evidence_min_score -> no passages for the fusion
    assert all(w["score"] < 0.3 for w in fs.detail["windows"])


def test_full_context_is_anchored_on_the_passage(ctx, monkeypatch):
    spy = use(ctx, monkeypatch, Spy(fake(ctx)))
    res = KeywordContextCheck(ctx, window=0, context="full").run(insider_call(), [trade_family()])
    probe = next(p for kind, p in spy.prompts if kind == "probs")
    assert probe.startswith("Transcript of the call")
    assert "[S011 " in probe  # the whole call is in the prompt
    assert "Consider the passage S003-S004. Given the whole call" in probe
    assert res.family_scores["trade"].detail["windows"][0]["mode"] == "full"
    assert res.meta["context"] == "full"


def test_no_hits_means_no_opinion_or_zero(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))
    t = make_transcript(FILLER * 3)
    res = KeywordContextCheck(ctx).run(t, [trade_family()])
    assert "trade" not in res.family_scores and res.meta["no_anchor_families"] == ["trade"]
    assert res.meta["llm_calls"] == 0
    res = KeywordContextCheck(ctx, empty="zero").run(t, [trade_family()])
    assert res.family_scores["trade"].score == 0.0 and res.family_scores["trade"].confidence < 0.5


def test_max_hits_caps_probes_strongest_first(ctx, monkeypatch):
    spy = use(ctx, monkeypatch, Spy(fake(ctx)))
    lines = []
    for i in range(6):
        lines += [("customer", "Die Quartalszahlen sind da."), *FILLER * 3]
    lines[-1] = ("customer", "Wegen der Quartalszahlen will ich vor der Meldung kaufen.")
    res = KeywordContextCheck(ctx, window=1, max_hits=2, locate_evidence=False, use_steps=False).run(
        make_transcript(lines), [trade_family()])
    fs = res.family_scores["trade"]
    assert fs.detail["passages"] == 2 and fs.detail["passages_dropped"] == 5
    assert sum(1 for k, _ in spy.prompts if k == "probs") == 2
    assert fs.score > 0.5  # the "vor der Meldung" passage (two distinct keywords) was probed first


def test_patterns_anchor_access_family(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))
    t = make_transcript([("advisor", "Bitte lesen Sie mir den Code vor."),
                         ("customer", "Der Code ist vier sieben eins zwei acht drei."), *FILLER])
    res = KeywordContextCheck(ctx).run(t, [access_family()])
    fs = res.family_scores["access"]
    assert fs.detail["hits"] >= 1 and "patterns" in fs.detail["windows"][0]["source"]


def test_view_language_selects_keyword_forms(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))
    t = make_transcript([("customer", "I saw the quarterly figures before anybody else."), *FILLER], lang="en")
    res = KeywordContextCheck(ctx).run(t, [trade_family()])
    assert res.family_scores["trade"].detail["hits"] == 1
    t_de = t.model_copy(update={"lang": "de"})
    assert "trade" not in KeywordContextCheck(ctx).run(t_de, [trade_family()]).family_scores
    assert KeywordContextCheck.lang_sensitive


def test_choice_probs_failure_falls_back_to_sampling(ctx, monkeypatch):
    use(ctx, monkeypatch, Spy(fake(ctx), fail_probs=1))
    lines = [("customer", "Die Quartalszahlen sind da."), *FILLER * 4, ("customer", "Insiderhandel? Nein.")]
    res = KeywordContextCheck(ctx, window=1, use_steps=False, locate_evidence=False).run(
        make_transcript(lines), [trade_family()])
    # choice_probs failed once -> geval falls back to sampling (no error); the family is still scored
    windows = res.family_scores["trade"].detail["windows"]
    assert len(windows) == 2 and {w["method"] for w in windows} == {"logprobs", "sampling"}
    assert not res.meta.get("errors")


def test_all_windows_failing_marks_errors(ctx, monkeypatch):
    class Down(LLM):
        def chat(self, *a, **k):
            raise RuntimeError("connection refused")

        def choice_probs(self, *a, **k):
            raise RuntimeError("connection refused")

    use(ctx, monkeypatch, Down(None))
    with pytest.raises(RuntimeError, match="every family failed"):
        KeywordContextCheck(ctx, use_steps=False).run(insider_call(), [trade_family()])
    res = KeywordContextCheck(ctx, use_steps=False).run(insider_call(), [trade_family(), access_family()])
    # access has no hit (skipped, no LLM call); trade failed -> visible error, not cacheable
    assert "trade" in res.meta["errors"] and res.meta["cacheable"] is False


def test_one_failing_window_of_several_is_an_error(ctx, monkeypatch):
    calls = {"n": 0}
    inner = fake(ctx)

    class Flaky(LLM):
        def chat(self, messages, **kw):
            if kw.get("max_tokens") == 4:  # the sampling fallback of the failing probe
                raise RuntimeError("timeout")
            return inner.chat(messages, **kw)

        def choice_probs(self, messages, choices):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("timeout")
            return inner.choice_probs(messages, choices)

    use(ctx, monkeypatch, Flaky(None))
    lines = [("customer", "Die Quartalszahlen sind da."), *FILLER * 4, ("customer", "Ich will vor der Meldung kaufen.")]
    res = KeywordContextCheck(ctx, window=1, use_steps=False).run(make_transcript(lines), [trade_family()])
    assert "trade" in res.family_scores and "trade" in res.meta["errors"]
    assert res.meta["cacheable"] is False
    assert len(res.family_scores["trade"].detail["window_errors"]) == 1


def test_keyword_context_cache_key(ctx):
    fam = trade_family()
    k = KeywordContextCheck(ctx).cache_key([fam])
    assert k["window_prompt_version"] == window_prompts.PROMPT_VERSION
    assert k == KeywordContextCheck(ctx, parallel=4).cache_key([fam])  # speed-only
    assert k != KeywordContextCheck(ctx, window=2).cache_key([fam])
    assert k != KeywordContextCheck(ctx, context="full").cache_key([fam])
    edited = fam.model_copy(deep=True)
    edited.keywords[0].harmless = "anders"
    assert k != KeywordContextCheck(ctx).cache_key([edited])  # harmless notes are in the prompt


# --------------------------------------------------------------------------------------------
# semantic_windows
# --------------------------------------------------------------------------------------------


def no_keyword_alarm_call() -> Transcript:
    return make_transcript([
        *FILLER * 3,
        ("customer", ("Können wir die Rechnung in drei Zahlungen aufteilen, damit die Freigabe der "
                      "Gesamtrechnung nicht greift?")),
        ("advisor", "Gut, ich mache drei Zahlungen."),
        *FILLER * 2,
    ], call_id="split")


def split_family() -> Family:
    return Family(id="splitting", label="Aufteilen", policy="Eine Rechnung in Teilzahlungen aufteilen, um "
                  "die interne Freigabe zu umgehen.",
                  alarm_when=["Rechnung in Teilzahlungen aufteilen damit die Freigabe der Gesamtrechnung nicht greift"])


def test_fake_embedder_is_deterministic_and_similarity_tracks_overlap():
    e = FakeEmbedder()
    a, b, c = e.embed(["Rechnung aufteilen Freigabe", "Rechnung aufteilen Freigabe umgehen", "Wetter heute schön"])
    assert e.embed(["Rechnung aufteilen Freigabe"])[0] == a
    from callguard.checks.semantic import cosine
    assert cosine(a, b) > 0.6 > cosine(a, c)


def test_semantic_windows_find_and_verify_no_keyword_alarm(ctx, monkeypatch):
    spy = use(ctx, monkeypatch, Spy(fake(ctx)))
    check = SemanticWindowCheck(ctx, embedder={"type": "fake"}, min_similarity=0.2, top_k=2)
    res = check.run(no_keyword_alarm_call(), [split_family()])
    fs = res.family_scores["splitting"]
    cands = fs.detail["candidates"]
    assert cands and "S007" in cands[0]["segment_ids"]
    assert fs.score > 0.5 and res.findings  # fake verifies: "aufteilen" cue in the passage
    assert res.meta["embed_calls"] == 1 and res.meta["windows"] == len(check.make_windows(no_keyword_alarm_call()))
    probe = next(p for k, p in spy.prompts if k == "probs")
    assert "semantic similarity" in probe


def test_semantic_windows_unverified_maps_similarity(ctx, monkeypatch):
    spy = use(ctx, monkeypatch, Spy(fake(ctx)))
    res = SemanticWindowCheck(ctx, embedder={"type": "fake"}, min_similarity=0.2, sim_ceil=0.6,
                              verify=False).run(no_keyword_alarm_call(), [split_family()])
    fs = res.family_scores["splitting"]
    assert 0 < fs.score <= 0.9 and fs.detail["verified"] is False and res.meta["llm_calls"] == 0
    assert spy.prompts == []


def test_semantic_windows_no_candidate_is_no_opinion(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))
    res = SemanticWindowCheck(ctx, embedder={"type": "fake"}, min_similarity=0.95, sim_ceil=0.99).run(
        no_keyword_alarm_call(), [split_family()])
    assert res.family_scores == {} and res.meta["no_anchor_families"] == ["splitting"]


def test_windows_cover_the_tail():
    check = SemanticWindowCheck.__new__(SemanticWindowCheck)
    check.size, check.stride = 4, 3
    t = make_transcript(FILLER * 4 + [("advisor", "x")])  # 9 segments
    ws = check.make_windows(t)
    assert ws[0] == ["S001", "S002", "S003", "S004"] and ws[-1][-1] == "S009"
    t2 = make_transcript(FILLER[:1])
    assert check.make_windows(t2) == [["S001"]]


def test_embedding_server_down_fails_clearly(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))

    def boom(*a, **k):
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(httpx, "post", boom)
    check = SemanticWindowCheck(ctx, embedder={"type": "openai", "base_url": "http://127.0.0.1:9/v1", "model": "m"})
    with pytest.raises(RuntimeError, match="embedding failed.*unreachable"):
        check.run(no_keyword_alarm_call(), [split_family()])


def test_openai_embedder_batches_and_orders(monkeypatch):
    sent: list[dict[str, Any]] = []

    def post(url, json=None, headers=None, timeout=None):
        sent.append({"url": url, "json": json, "headers": headers})
        data = [{"index": i, "embedding": [float(len(t)), 1.0]} for i, t in enumerate(json["input"])][::-1]
        return httpx.Response(200, json={"data": data})

    monkeypatch.setattr(httpx, "post", post)
    e = make_embedder({"type": "openai", "base_url": "http://h/v1/", "model": "bge", "api_key": "tok", "batch_size": 2})
    assert isinstance(e, OpenAIEmbedder)
    out = e.embed(["a", "bb", "ccc"])
    assert [v[0] for v in out] == [1.0, 2.0, 3.0]
    assert len(sent) == 2 and sent[0]["url"] == "http://h/v1/embeddings" and sent[0]["json"]["model"] == "bge"
    assert sent[0]["headers"] == {"Authorization": "Bearer tok"}


def test_sentence_transformers_missing_is_a_clear_error(monkeypatch):
    import builtins
    real = builtins.__import__

    def fake_import(name, *a, **k):
        if name.startswith("sentence_transformers"):
            raise ImportError("no module")
        return real(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    e = make_embedder({"type": "sentence_transformers", "model": "x"})  # constructing never imports
    with pytest.raises(RuntimeError, match="sentence-transformers package"):
        e.embed(["hallo"])


def test_semantic_cache_key_has_embedder_but_no_secrets(ctx):
    a = SemanticWindowCheck(ctx, embedder={"type": "openai", "model": "bge-m3", "api_key": "secret",
                                           "base_url": "http://a/v1"})
    b = SemanticWindowCheck(ctx, embedder={"type": "openai", "model": "bge-m3", "base_url": "http://b/v1"})
    c = SemanticWindowCheck(ctx, embedder={"type": "openai", "model": "e5"})
    fam = [split_family()]
    assert "secret" not in json.dumps(a.cache_key(fam))
    assert a.cache_key(fam) == b.cache_key(fam) != c.cache_key(fam)


# --------------------------------------------------------------------------------------------
# quote_judge
# --------------------------------------------------------------------------------------------


def test_verify_quote_cited_elsewhere_and_invented():
    t = insider_call()
    ok = verify_quote("will ich unbedingt vor der Meldung", "S004", t, 85, 25)
    assert ok["verified"] and ok["where"] == "cited" and "S004" in ok["found_in"]
    moved = verify_quote("will ich unbedingt vor der Meldung", "S001", t, 85, 25)
    assert moved["verified"] and moved["where"] == "elsewhere" and "S004" in moved["found_in"]
    folded = verify_quote("Mein Schwager in der Finanzabteilung hat mir die Quartalszahlen gezeigt", "S3", t, 85, 25)
    assert folded["verified"]  # "S3" -> S003
    invented = verify_quote("Ich habe den PIN 1234 schon dem Berater gesagt", "S004", t, 85, 25)
    assert not invented["verified"] and invented["where"] == "not_found"
    padded = verify_quote("Ich nehme den Auftrag auf. Und dann habe ich ihm alle Geheimzahlen und Passwörter "
                          "vorgelesen", "S005", t, 85, 25)
    assert not padded["verified"]  # a long invented quote that merely contains the segment
    assert verify_quote("ja", "S001", t, 85, 25)["where"] == "too_short"
    long = verify_quote(" ".join(["wort"] * 40), None, t, 85, 25)
    assert long["truncated"] and len(long["quote"].split()) == 25


def test_quote_judge_with_fake_llm_verifies_quotes(ctx, monkeypatch):
    use(ctx, monkeypatch, fake(ctx))
    res = QuoteJudgeCheck(ctx).run(insider_call(), [trade_family()])
    fs = res.family_scores["trade"]
    assert fs.verdict == "present" and fs.score > 0.5 and fs.detail["downgraded"] == 0
    assert res.findings and {"S003", "S004"} & set(fs.segment_ids)
    assert "«" in res.findings[0].reason and res.findings[0].detail["grounded"]
    assert res.meta["quotes"]["verified"] >= 1 and res.meta["llm_calls"] == 1


class ScriptedJudge(LLM):
    def __init__(self, answer: dict[str, Any]):
        super().__init__(None)
        self.answer = answer
        self.schemas: list[Any] = []

    def chat(self, messages, *, temperature=0.0, max_tokens=512, n=1, json_schema=None, stop=None):
        self.schemas.append(json_schema)
        return [json.dumps(self.answer)] * n


def test_quote_judge_downgrades_present_without_verified_quote(ctx, monkeypatch):
    llm = use(ctx, monkeypatch, ScriptedJudge({
        "reason": "Der Kunde nennt seine PIN.", "verdict": "present", "confidence": 0.9,
        "quotes": [{"segment_id": "S004", "quote": "meine PIN ist eins zwei drei vier"}]}))
    res = QuoteJudgeCheck(ctx).run(insider_call(), [trade_family()])
    fs = res.family_scores["trade"]
    assert fs.verdict == "undetermined" and fs.score <= 0.5 and DOWNGRADE_NOTE in fs.reason
    assert fs.detail["downgraded"] == 1 and res.findings == []
    assert "quotes" in llm.schemas[0]["properties"]


def test_quote_judge_absent_and_undetermined_pass_through(ctx, monkeypatch):
    use(ctx, monkeypatch, ScriptedJudge({"reason": "Nur Erklärung.", "verdict": "absent", "confidence": 0.8,
                                         "quotes": []}))
    fs = QuoteJudgeCheck(ctx).run(harmless_call(), [trade_family()]).family_scores["trade"]
    assert fs.verdict == "absent" and fs.score < 0.2 and fs.detail["downgraded"] == 0


def test_quote_judge_cache_key(ctx):
    fam = [trade_family()]
    k = QuoteJudgeCheck(ctx).cache_key(fam)
    assert k["window_prompt_version"] == window_prompts.PROMPT_VERSION
    assert k != QuoteJudgeCheck(ctx, min_ratio=75).cache_key(fam)
