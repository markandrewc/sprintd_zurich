"""LLM clients: tolerant JSON, the OpenAI-compatible client against a mock server, the offline
FakeLLM, and (slow) a few real requests against the local server / in-process llama.cpp."""

from __future__ import annotations

import json
import os
import re
import threading
from pathlib import Path
from typing import Any, Literal

import httpx
import pytest
from pydantic import BaseModel, Field

from callguard import registry
from callguard.config import ROOT, load_config
from callguard.context import Context
from callguard.llm import (SCHEMA_INSTRUCTION, chat_json, choice_distribution, parse_json, request_seeds,
                           validate_minimal, with_schema_instruction)
from callguard.llm.fake import FakeLLM
from callguard.llm.openai_compat import LLMRequestError, OpenAICompatLLM
from callguard.types import Segment, Transcript

# ---------------------------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------------------------


class Evidence(BaseModel):
    segment_id: str
    quote: str


class Judgement(BaseModel):
    verdict: Literal["present", "absent", "undetermined"]
    confidence: float = Field(ge=0, le=1)
    segment_ids: list[str]
    evidence: list[Evidence] = Field(default_factory=list)
    reason: str


class PerFamily(BaseModel):
    trade: Judgement
    access: Judgement
    disclosure: Judgement


SCHEMA = Judgement.model_json_schema()


def transcript() -> Transcript:
    return Transcript(call_id="t", segments=[
        Segment(id="S001", start=0.0, end=3.0, text="Grüezi, was kann ich für Sie tun?", role="advisor"),
        Segment(id="S002", start=3.0, end=9.0, role="customer",
                text="Ich möchte die Aktie jetzt kaufen, vor der Meldung am Freitag."),
        Segment(id="S003", start=9.0, end=12.0, text="Meine TAN ist 4711.", role="customer"),
        Segment(id="S004", start=12.0, end=15.0, text="Danke, auf Wiederhören.", role="advisor"),
    ])


def judge_messages(family: str | None, t: Transcript | None = None) -> list[dict[str, str]]:
    t = t or transcript()
    system = f"Du prüfst Bankgespräche auf die Familie {family}." if family else "Du prüfst Bankgespräche."
    return [{"role": "system", "content": system},
            {"role": "user", "content": f"Policy: Kaufwunsch vor der Meldung ist verboten.\n\n"
                                        f"Transkript:\n{t.render()}\n\nAntworte als JSON."}]


def ok(content: str | None = "hi", **extra: Any) -> httpx.Response:
    choice = {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop", **extra}
    return httpx.Response(200, json={"choices": [choice]})


class Server:
    """Scripted mock server: records request bodies, answers with the next scripted response."""

    def __init__(self, *responses: Any):
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        self.headers: list[httpx.Headers] = []
        self.lock = threading.Lock()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        with self.lock:
            self.requests.append(body)
            self.headers.append(request.headers)
            r = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(r, Exception):
            raise r
        return r(body) if callable(r) else r


def make_llm(server: Server, **kw: Any) -> OpenAICompatLLM:
    llm = OpenAICompatLLM(None, **{"base_url": "http://llm.test/v1", "model": "m", **kw})
    llm.backoff = 0.0
    llm._client = llm._build_client(httpx.MockTransport(server))
    return llm


# ---------------------------------------------------------------------------------------------
# jsonutil
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("text", [
    '{"verdict": "present"}',
    '```json\n{"verdict": "present"}\n```',
    'Hier ist meine Antwort:\n```\n{"verdict": "present"}\n```\nIch hoffe das hilft.',
    'Sure! {"verdict": "present"} - done',
    '{"verdict": "present",}',
    "{'verdict': 'present'}",
    '<think>maybe {"verdict": "absent"}</think>{"verdict": "present"}',
    'Note the { brace. {"verdict": "present"}',
    '{"verdict": "present", "reason": "Kunde nennt die TA',
    '{"verdict": "present", "reason":',
])
def test_parse_json_tolerates_llm_noise(text: str) -> None:
    assert parse_json(text)["verdict"] == "present"


def test_parse_json_nested_and_braces_in_strings() -> None:
    obj = parse_json('Answer: {"a": {"b": [1, 2]}, "s": "x } y {"} trailing {"other": 1}')
    assert obj == {"a": {"b": [1, 2]}, "s": "x } y {"}


@pytest.mark.parametrize("text", ["", "   ", "no json here", "[1, 2, 3]", "<think>{\"a\": 1}"])
def test_parse_json_raises_with_snippet(text: str) -> None:
    with pytest.raises(ValueError) as e:
        parse_json(text)
    assert "JSON" in str(e.value)


def test_validate_minimal_coerces_obvious_slips() -> None:
    raw = {"verdict": "Present.", "confidence": "85%", "segment_ids": "S002",
           "evidence": [{"segment_id": "S002", "quote": 7}], "reason": "x", "extra": [1]}
    out = validate_minimal(raw, SCHEMA)
    assert out["verdict"] == "present"
    assert out["confidence"] == pytest.approx(0.85)
    assert out["segment_ids"] == ["S002"]
    assert out["evidence"][0]["quote"] == "7"
    assert out["extra"] == [1]  # unknown keys survive for meta
    assert raw["segment_ids"] == "S002"  # input untouched


@pytest.mark.parametrize("value,expected", [(0.4, 0.4), (85, 0.85), ("0,7", 0.7), (-1, 0.0), (250, 1.0)])
def test_validate_minimal_unit_interval(value: Any, expected: float) -> None:
    schema = {"type": "object", "properties": {"p": {"type": "number", "minimum": 0, "maximum": 1}}}
    assert validate_minimal({"p": value}, schema)["p"] == pytest.approx(expected)


def test_validate_minimal_misc_types() -> None:
    schema = {"type": "object", "required": ["n", "b"], "properties": {
        "n": {"type": "integer", "minimum": 1, "maximum": 5},
        "b": {"type": "boolean"},
        "label": {"enum": ["alarm", "review", "no_alert"]},
        "opt": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "fams": {"type": "object", "additionalProperties": {"enum": ["present", "absent"]}},
    }}
    out = validate_minimal({"n": "4.4", "b": "ja", "label": "No Alert", "opt": None,
                            "fams": {"trade": "PRESENT"}}, schema)
    assert out == {"n": 4, "b": True, "label": "no_alert", "opt": None, "fams": {"trade": "present"}}


@pytest.mark.parametrize("obj,msg", [
    ({"confidence": 0.5, "segment_ids": [], "reason": ""}, "missing required"),
    ({"verdict": "maybe", "confidence": 0.5, "segment_ids": [], "reason": ""}, "not one of"),
    ({"verdict": "present", "confidence": "high", "segment_ids": [], "reason": ""}, "number"),
    ({"verdict": "present", "confidence": None, "segment_ids": [], "reason": ""}, "null"),
    ({"verdict": "present", "confidence": 0.5, "segment_ids": [], "reason": "",
      "evidence": [{"quote": "x"}]}, "evidence[0]"),
])
def test_validate_minimal_never_invents(obj: dict, msg: str) -> None:
    with pytest.raises(ValueError, match=msg.replace("[", r"\[")):
        validate_minimal(obj, SCHEMA)


def test_validate_minimal_resolves_pydantic_refs() -> None:
    schema = PerFamily.model_json_schema()
    good = {f: {"verdict": "absent", "confidence": 1, "segment_ids": [], "reason": ""}
            for f in ("trade", "access", "disclosure")}
    assert validate_minimal(good, schema)["access"]["verdict"] == "absent"
    good["access"]["verdict"] = "nope"
    with pytest.raises(ValueError, match=r"\$\.access\.verdict"):
        validate_minimal(good, schema)


class ScriptedLLM:
    def __init__(self, *outputs: str):
        self.outputs = list(outputs)
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages: list[dict[str, str]], **kw: Any) -> list[str]:
        self.calls.append(messages)
        n = kw.get("n", 1)
        out, self.outputs = self.outputs[:n], self.outputs[n:]
        return out


def test_chat_json_repairs_once_then_drops() -> None:
    valid = json.dumps({"verdict": "absent", "confidence": 0.9, "segment_ids": [], "reason": "ok"})
    llm = ScriptedLLM(valid, "kaputt", valid)  # sample 2 repaired
    out = chat_json(llm, [{"role": "user", "content": "x"}], SCHEMA, n=2)  # type: ignore[arg-type]
    assert [o["verdict"] for o in out] == ["absent", "absent"]
    assert "ungültig" in llm.calls[-1][-1]["content"] and llm.calls[-1][-2]["content"] == "kaputt"
    llm = ScriptedLLM(valid, "kaputt", '{"verdict": "present"}')  # repair still incomplete -> dropped
    assert len(chat_json(llm, [{"role": "user", "content": "x"}], SCHEMA, n=2)) == 1  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="no valid JSON"):
        chat_json(ScriptedLLM("nope", "still nope"), [{"role": "user", "content": "x"}], SCHEMA)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------------------------


def test_choice_distribution() -> None:
    top = [("1", -0.5), (" 4", -1.0), ("4", -2.0), ("Based", -0.1), ("five", -3.0)]
    probs = choice_distribution(top, ["1", "2", "3", "4", "5"])
    assert probs is not None and sum(probs.values()) == pytest.approx(1.0)
    assert probs["2"] == 0.0 and probs["1"] > probs["4"] > 0
    assert choice_distribution([("Yes", -0.1), ("no", -2.0)], ["yes", "no"])["yes"] > 0.8  # type: ignore[index]
    assert choice_distribution([("Based", -0.1)], ["1", "2"]) is None
    assert choice_distribution([("1", -30.0)], ["1", "2"], min_mass=1e-6) is None


def test_request_seeds_and_schema_instruction() -> None:
    import random
    rng = random.Random(0)
    assert request_seeds(3, 0.0, 7, rng) == [7, 8, 9]
    assert request_seeds(2, 0.0, None, rng) == [None, None]
    sampled = request_seeds(5, 0.7, None, rng)
    assert len(set(sampled)) == 5 and all(isinstance(s, int) for s in sampled)
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    out = with_schema_instruction(msgs, {"type": "object"})
    assert msgs[1]["content"] == "u" and out[1]["content"].startswith("u\n\n" + SCHEMA_INSTRUCTION)


# ---------------------------------------------------------------------------------------------
# OpenAICompatLLM against a mock server
# ---------------------------------------------------------------------------------------------


def test_registry_creates_openai_compat_and_rejects_typos() -> None:
    llm = registry.create("llm", {"type": "openai_compat", "base_url": "http://x/v1", "model": "qwen"}, ctx=None)
    assert isinstance(llm, OpenAICompatLLM) and llm.model_id == "qwen"
    assert "api_key" not in llm.cache_params()
    with pytest.raises(TypeError):
        registry.create("llm", {"type": "openai_compat", "base_url": "x", "model": "m", "jsonmode": "none"}, ctx=None)
    with pytest.raises(ValueError, match="json_mode"):
        OpenAICompatLLM(None, base_url="x", model="m", json_mode="grammar")


@pytest.mark.parametrize("mode,expected", [
    ("json_schema", {"type": "json_schema", "json_schema": {"name": "output", "schema": SCHEMA, "strict": True}}),
    ("json_object_schema", {"type": "json_object", "schema": SCHEMA}),
    ("json_object", {"type": "json_object"}),
    ("none", None),
])
def test_json_modes(mode: str, expected: dict | None) -> None:
    server = Server(ok('{"verdict": "absent"}'))
    llm = make_llm(server, json_mode=mode, extra_body={"top_k": 20, "temperature": 9})
    messages = [{"role": "user", "content": "frage"}]
    assert llm.chat(messages, json_schema=SCHEMA, stop=["\n\n"]) == ['{"verdict": "absent"}']
    body = server.requests[0]
    assert body.get("response_format") == expected
    assert body["model"] == "m" and body["top_k"] == 20 and body["temperature"] == 0.0
    assert body["stop"] == ["\n\n"] and "seed" not in body and "n" not in body
    prompt_has_schema = SCHEMA_INSTRUCTION in body["messages"][-1]["content"]
    assert prompt_has_schema == (mode in ("json_object", "none"))
    assert messages == [{"role": "user", "content": "frage"}]


def test_falls_back_to_prompt_schema_when_server_rejects_response_format() -> None:
    # exactly what llama-cpp-python's server answers to type=json_schema
    rejected = httpx.Response(500, json={"error": {"message": "1 validation error: ('body', 'response_format', "
                                                              "'type') Input should be 'text' or 'json_object'"}})
    server = Server(rejected, ok('{"a": 1}'))
    llm = make_llm(server, json_mode="json_schema")
    assert llm.chat([{"role": "user", "content": "q"}], json_schema={"type": "object"}) == ['{"a": 1}']
    assert len(server.requests) == 2  # no retries of the rejected format
    assert "response_format" not in server.requests[1]
    llm.chat([{"role": "user", "content": "q"}], json_schema={"type": "object"})
    assert len(server.requests) == 3 and "response_format" not in server.requests[2]  # remembered


def test_unsupported_schema_falls_back_for_that_request_only() -> None:
    bad_schema = httpx.Response(400, json={"error": {"message": "The provided JSON schema contains features "
                                                                "not supported by xgrammar."}})
    server = Server(bad_schema, ok('{"a": 1}'), ok('{"b": 2}'))
    llm = make_llm(server, json_mode="json_schema")
    assert llm.chat([{"role": "user", "content": "q"}], json_schema={"type": "object"}) == ['{"a": 1}']
    assert SCHEMA_INSTRUCTION in server.requests[1]["messages"][-1]["content"]
    llm.chat([{"role": "user", "content": "q"}], json_schema={"type": "object"})
    assert server.requests[2]["response_format"]["type"] == "json_schema"


def test_retries_5xx_then_succeeds_and_gives_up_on_4xx() -> None:
    server = Server(httpx.Response(503, text="busy"), httpx.Response(502, text="gw"), ok("fine"))
    assert make_llm(server).chat([{"role": "user", "content": "q"}]) == ["fine"]
    assert len(server.requests) == 3

    server = Server(httpx.Response(404, json={"error": "model 'm' not found"}))
    with pytest.raises(LLMRequestError, match="HTTP 404") as e:
        make_llm(server).chat([{"role": "user", "content": "q"}])
    assert e.value.status == 404 and len(server.requests) == 1

    server = Server(httpx.Response(500, text="boom"))
    with pytest.raises(LLMRequestError, match="HTTP 500"):
        make_llm(server, max_retries=1).chat([{"role": "user", "content": "q"}])
    assert len(server.requests) == 2


def test_unreachable_server_hint_and_fast_fail() -> None:
    server = Server(httpx.ConnectError("connection refused"))
    llm = make_llm(server, max_retries=2)
    with pytest.raises(RuntimeError, match="not reachable - start scripts/serve_llm_local.sh"):
        llm.chat([{"role": "user", "content": "q"}])
    assert len(server.requests) == 3
    with pytest.raises(RuntimeError, match="not reachable"):
        llm.chat([{"role": "user", "content": "q"}])
    assert len(server.requests) == 4  # within the cooldown: no retries

    server = Server(httpx.ReadTimeout("slow"))
    with pytest.raises(LLMRequestError, match="timed out"):
        make_llm(server, max_retries=1, timeout=5).chat([{"role": "user", "content": "q"}])
    assert len(server.requests) == 2


def test_n_samples_loop_with_distinct_seeds() -> None:
    server = Server(lambda body: ok(f"seed={body.get('seed')}"))
    llm = make_llm(server, seed=10)
    assert llm.chat([{"role": "user", "content": "q"}], n=3, temperature=0.7) == ["seed=10", "seed=11", "seed=12"]
    server = Server(lambda body: ok(str(body.get("seed"))))
    out = make_llm(server, max_concurrency=4).chat([{"role": "user", "content": "q"}], n=4, temperature=1.0)
    assert len(set(out)) == 4 and "None" not in out
    server = Server(lambda body: ok(str(body.get("seed"))))
    assert make_llm(server).chat([{"role": "user", "content": "q"}], n=2) == ["None", "None"]  # greedy


def test_supports_n_single_request_and_top_up() -> None:
    def answer(body: dict) -> httpx.Response:
        k = min(body.get("n", 1), 2)  # server caps n at 2
        return httpx.Response(200, json={"choices": [
            {"index": i, "message": {"content": f"c{i}"}} for i in range(k)]})
    server = Server(answer)
    out = make_llm(server, supports_n=True).chat([{"role": "user", "content": "q"}], n=3, temperature=0.5)
    assert out == ["c0", "c1", "c0"]
    assert server.requests[0]["n"] == 3 and "n" not in server.requests[1]


def test_content_cleanup_and_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    server = Server(ok("<think>hmm 1</think>\n4"), ok(None))
    llm = make_llm(server)
    assert llm.chat([{"role": "user", "content": "q"}]) == ["4"]
    assert llm.chat([{"role": "user", "content": "q"}]) == [""]
    assert "authorization" not in server.headers[0]
    monkeypatch.setenv("CG_TEST_KEY", "sekret")
    server = Server(ok("x"))
    make_llm(server, api_key="env:CG_TEST_KEY").chat([{"role": "user", "content": "q"}])
    assert server.headers[0]["authorization"] == "Bearer sekret"


@pytest.mark.parametrize("answer,alive", [
    (httpx.Response(200, json={"data": []}), True),
    (httpx.ReadTimeout("busy generating"), True),
    (httpx.ConnectError("refused"), False),
    (httpx.Response(503, text="down"), False),
])
def test_ping(answer: Any, alive: bool) -> None:
    assert make_llm(Server(answer)).ping() is alive


def _logprobs_response(top: list[tuple[str, float]]) -> httpx.Response:
    return ok(top[0][0], logprobs={"content": [{"token": top[0][0], "logprob": top[0][1], "top_logprobs": [
        {"token": t, "logprob": lp, "bytes": None} for t, lp in top]}]})


def test_choice_probs_from_top_logprobs() -> None:
    server = Server(_logprobs_response([("1", -1.1), ("2", -1.4), (" 4", -2.1), ("4", -3.0), ("Based", -6.8)]))
    llm = make_llm(server, seed=3)
    probs = llm.choice_probs([{"role": "user", "content": "Rate 1-5"}], ["1", "2", "3", "4", "5"])
    assert probs is not None and sum(probs.values()) == pytest.approx(1.0)
    assert probs["1"] > probs["2"] > probs["4"] > probs["3"] == 0.0
    body = server.requests[0]
    assert body["max_tokens"] == 1 and body["temperature"] == 0.0 and body["logprobs"] is True
    assert body["top_logprobs"] == 20 and body["seed"] == 3 and "response_format" not in body

    server = Server(_logprobs_response([("Based", -0.1), ("The", -2.0)]))
    assert make_llm(server).choice_probs([{"role": "user", "content": "x"}], ["1", "2"]) is None


def test_choice_probs_unsupported_is_remembered() -> None:
    server = Server(ok("1"))  # no logprobs in the response
    llm = make_llm(server)
    assert llm.choice_probs([{"role": "user", "content": "x"}], ["1", "2"]) is None
    assert llm.choice_probs([{"role": "user", "content": "x"}], ["1", "2"]) is None
    assert len(server.requests) == 1

    server = Server(httpx.Response(400, json={"error": "logprobs are not supported"}))
    llm = make_llm(server)
    assert llm.choice_probs([{"role": "user", "content": "x"}], ["1", "2"]) is None
    assert llm._logprobs_ok is False


# ---------------------------------------------------------------------------------------------
# FakeLLM
# ---------------------------------------------------------------------------------------------


def test_fake_scopes_cues_per_family() -> None:
    fake = FakeLLM(None)
    got = {f: json.loads(fake.chat(judge_messages(f), json_schema=SCHEMA)[0])
           for f in ("trade", "access", "splitting")}
    assert got["trade"]["verdict"] == "present" and got["trade"]["segment_ids"] == ["S002"]
    assert "vor der Meldung" in got["trade"]["reason"]
    assert got["trade"]["evidence"] == [{"segment_id": "S002", "quote": transcript().segments[1].text}]
    assert got["access"]["verdict"] == "present" and got["access"]["segment_ids"] == ["S003"]
    assert got["splitting"] == {"verdict": "absent", "confidence": 0.8, "segment_ids": [], "evidence": [],
                                "reason": "Keine verdächtigen Hinweise im Gespräch gefunden."}
    for g in got.values():
        validate_minimal(g, SCHEMA)
    unscoped = json.loads(fake.chat([{"role": "user", "content": transcript().render()}], json_schema=SCHEMA)[0])
    assert unscoped["verdict"] == "present" and unscoped["segment_ids"] == ["S002", "S003"]
    # a label word in the instructions ("Kaufwunsch") is enough to scope to that family
    by_label = json.loads(fake.chat(judge_messages(None), json_schema=SCHEMA)[0])
    assert by_label["segment_ids"] == ["S002"]


def test_fake_policy_text_outside_transcript_is_not_a_cue() -> None:
    clean = Transcript(call_id="c", segments=[Segment(id="S001", start=0, end=2, text="Ich möchte Geld überweisen.")])
    out = json.loads(FakeLLM(None).chat(judge_messages("trade", clean), json_schema=SCHEMA)[0])
    assert out["verdict"] == "absent" and out["segment_ids"] == []


def test_fake_multi_family_schemas() -> None:
    fake = FakeLLM(None)
    multi = PerFamily.model_json_schema()
    out = json.loads(fake.chat([{"role": "user", "content": transcript().render()}], json_schema=multi)[0])
    assert {f: v["verdict"] for f, v in out.items()} == {"trade": "present", "access": "present",
                                                         "disclosure": "absent"}
    assert out["access"]["segment_ids"] == ["S003"]
    validate_minimal(out, multi)

    listed = {"type": "object", "properties": {"families": {"type": "array", "items": {
        "type": "object", "properties": {"family": {"enum": ["trade", "documentation"]},
                                         "score": {"type": "number", "minimum": 0, "maximum": 1},
                                         "label": {"enum": ["alarm", "review", "no_alert"]}}}}}}
    out = json.loads(fake.chat([{"role": "user", "content": transcript().render()}], json_schema=listed)[0])
    assert out["families"] == [{"family": "trade", "score": 0.8, "label": "alarm"},
                               {"family": "documentation", "score": 0.2, "label": "no_alert"}]


def test_fake_scalars_roles_and_scales() -> None:
    fake = FakeLLM(None)
    schema = {"type": "object", "properties": {
        "advisor": {"enum": ["SPK1", "SPK0"]}, "speaker": {"type": "string"},
        "rating": {"type": "integer", "minimum": 1, "maximum": 5}, "risk": {"type": "integer"},
        "negated": {"type": "boolean"}, "suspicious": {"type": "boolean"},
        "ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 1}}}
    msgs = [{"role": "user", "content": "Wer berät?\n[S001 00:00 SPK0] Grüezi\n[S002 00:04 SPK1] Mein Passwort ist x"}]
    out = json.loads(fake.chat(msgs, json_schema=schema)[0])
    assert out == {"advisor": "SPK1", "speaker": "SPK0", "rating": 4, "risk": 4, "negated": False,
                   "suspicious": True, "ids": ["S002"]}


def test_fake_plain_text_scores_and_choice_probs() -> None:
    fake = FakeLLM(None)
    t = transcript().render()
    ask = "\n\nBewerte auf einer Skala von 1 bis 5. Antworte nur mit einer Ziffer."
    assert fake.chat([{"role": "user", "content": t + ask}]) == ["4"]
    clean = "[S001 00:00 advisor] Guten Tag."
    assert fake.chat([{"role": "user", "content": clean + ask}]) == ["1"]
    assert fake.chat([{"role": "user", "content": clean + "\nScore 0-10:"}]) == ["0"]
    assert "vor der Meldung" in fake.chat([{"role": "user", "content": "Fasse zusammen:\n" + t}])[0]
    assert fake.chat([{"role": "user", "content": "Fasse zusammen:\n" + t}], stop=["«"]) == ["Verdächtige Formulierung "]
    probs = fake.choice_probs([{"role": "user", "content": t + ask}], ["1", "2", "3", "4", "5"])
    assert probs is not None and max(probs, key=probs.get) == "4" and sum(probs.values()) == pytest.approx(1.0)
    probs = fake.choice_probs([{"role": "user", "content": clean}], ["1", "2", "3", "4", "5"])
    assert probs is not None and max(probs, key=probs.get) == "1"
    probs = fake.choice_probs([{"role": "user", "content": t}], ["ja", "nein"])
    assert probs == {"ja": 0.7, "nein": pytest.approx(0.3)}


def test_fake_is_deterministic_and_jitters_only_extra_samples() -> None:
    a, b = FakeLLM(None, seed=1), FakeLLM(None, seed=1)
    schema = {"type": "object", "properties": {"score": {"type": "number", "minimum": 0, "maximum": 1},
                                               "verdict": {"enum": ["present", "absent"]}}}
    msgs = judge_messages("trade")
    assert a.chat(msgs, json_schema=schema, n=3, temperature=0.7) == b.chat(msgs, json_schema=schema, n=3,
                                                                            temperature=0.7)
    samples = [json.loads(s) for s in a.chat(msgs, json_schema=schema, n=4, temperature=0.7)]
    assert samples[0]["score"] == 0.8 and len({s["score"] for s in samples}) > 1
    assert {s["verdict"] for s in samples} == {"present"}
    assert all(abs(s["score"] - 0.8) <= 0.05 + 1e-9 for s in samples)
    greedy = a.chat(msgs, json_schema=schema, n=3)
    assert len(set(greedy)) == 1
    assert a.calls[-1]["n"] == 3 and a.model_id == "fake-v3-s1"


def test_fake_from_config_ignores_inherited_server_params() -> None:
    cfg = load_config("local", overrides=["llms.default.type=fake"])
    ctx = Context(cfg, use_cache=False)
    llm = ctx.llm()
    assert isinstance(llm, FakeLLM) and "base_url" in llm.ignored_params
    assert "base_url" not in llm.cache_params()
    # labels from config/criteria.yaml name a family even without its id
    msgs = [{"role": "system", "content": "Prüfe: Zugangsinformation preisgegeben"},
            {"role": "user", "content": transcript().render()}]
    out = json.loads(llm.chat(msgs, json_schema=SCHEMA)[0])
    assert out["segment_ids"] == ["S003"]
    assert chat_json(llm, msgs, SCHEMA)[0]["verdict"] == "present"


# ---------------------------------------------------------------------------------------------
# live (slow): the shared local server and in-process llama.cpp
# ---------------------------------------------------------------------------------------------

LOCAL_URL = os.environ.get("CALLGUARD_LLM_URL", "http://127.0.0.1:8001/v1")
LOCAL_MODEL = os.environ.get("CALLGUARD_LLM_MODEL", "qwen2.5-1.5b-instruct")
GGUF = ROOT / "models/llm/qwen2.5-1.5b-instruct-q4_k_m.gguf"


@pytest.fixture(scope="module")
def live_llm() -> OpenAICompatLLM:
    llm = OpenAICompatLLM(None, base_url=LOCAL_URL, model=LOCAL_MODEL, timeout=600, json_mode="json_schema",
                          max_retries=0)
    if not llm.ping():
        pytest.skip(f"no LLM server at {LOCAL_URL}")
    return llm


TINY_SCHEMA = {"type": "object", "properties": {"verdict": {"type": "string", "enum": ["present", "absent"]}},
               "required": ["verdict"]}
TINY_PROMPT = [{"role": "user", "content": 'Satz: "Ich kaufe die Aktie vor der Meldung." Enthält der Satz einen '
                                          'Kaufwunsch? Antworte als JSON {"verdict": "present"|"absent"}.'}]


@pytest.mark.slow
def test_live_json_schema_falls_back_and_json_object_schema_works(live_llm: OpenAICompatLLM) -> None:
    # json_schema is rejected by llama-cpp-python (HTTP 500) -> prompt fallback, remembered
    out = chat_json(live_llm, TINY_PROMPT, TINY_SCHEMA, max_tokens=24)
    assert out[0]["verdict"] in ("present", "absent")
    if "CALLGUARD_LLM_URL" not in os.environ:  # the local llama-cpp-python server
        assert live_llm._active_json_mode == "none"
    strict = OpenAICompatLLM(None, base_url=LOCAL_URL, model=LOCAL_MODEL, timeout=600,
                             json_mode="json_object_schema", max_retries=0)
    text = strict.chat(TINY_PROMPT, json_schema=TINY_SCHEMA, max_tokens=24)[0]
    assert validate_minimal(parse_json(text), TINY_SCHEMA)["verdict"] in ("present", "absent")


@pytest.mark.slow
def test_live_choice_probs(live_llm: OpenAICompatLLM) -> None:
    msgs = [{"role": "user", "content": "Wie verdächtig ist: 'Ich kaufe vor der Meldung.' Skala 1-5, "
                                        "antworte nur mit einer Ziffer."}]
    probs = live_llm.choice_probs(msgs, ["1", "2", "3", "4", "5"])
    assert probs is not None and sum(probs.values()) == pytest.approx(1.0)


def _mem_available_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1e6
    except OSError:
        pass
    return 0.0


@pytest.mark.slow
@pytest.mark.skipif(os.environ.get("CALLGUARD_TEST_INPROC") != "1",
                    reason="loads a 1.1 GB model in-process; set CALLGUARD_TEST_INPROC=1")
def test_live_llama_cpp_inprocess() -> None:
    pytest.importorskip("llama_cpp")
    if not GGUF.exists():
        pytest.skip(f"{GGUF} missing")
    if _mem_available_gb() < 2.5:
        pytest.skip("not enough free RAM for an in-process model")
    llm = registry.create("llm", {"type": "llama_cpp", "model_path": str(GGUF.relative_to(ROOT)),
                                  "n_ctx": 1024, "n_threads": 4}, ctx=None)
    assert llm.model_id == "qwen2.5-1.5b-instruct-q4_k_m"
    text = llm.chat(TINY_PROMPT, json_schema=TINY_SCHEMA, max_tokens=24)[0]
    assert validate_minimal(parse_json(text), TINY_SCHEMA)["verdict"] in ("present", "absent")
    probs = llm.choice_probs([{"role": "user", "content": "Skala 1-5, antworte nur mit einer Ziffer: "
                                                          "Wie verdächtig ist 'Kauf vor der Meldung'?"}],
                             ["1", "2", "3", "4", "5"])
    assert probs is not None and sum(probs.values()) == pytest.approx(1.0)


def test_fake_scope_prefers_the_tagged_family_over_english_words():
    from callguard.checks import prompts
    from callguard.types import Family, Segment, Transcript

    t = Transcript(call_id="x", segments=[Segment(id="S001", start=0, end=3, text="Ich kaufe vor der Meldung.")])
    fake = FakeLLM()
    for fid, expect in (("trade", "present"), ("access", "absent")):
        msgs = prompts.judge_messages(Family(id=fid, label=fid.title()), t.render(), "de")
        assert re.search(r"\bnumbers\b", msgs[0]["content"])  # the word that used to defeat the scoping
        out = json.loads(fake.chat(msgs, json_schema={"type": "object", "properties": {
            "verdict": {"type": "string", "enum": ["present", "absent", "undetermined"]}}})[0])
        assert out["verdict"] == expect
