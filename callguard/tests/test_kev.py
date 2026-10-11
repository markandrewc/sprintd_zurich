"""Kev-4B integration, offline: a fake Kev HTTP service stands in for scripts/remote/serve_kev.py.

Covers the wire format, the max-p(yes) rule of the `questions` check, Kev as the facts backend (choice_probs
seam), cache keys (questions / model), identity resolution (audit F3) and failure handling (a dead or broken
service degrades the check instead of scoring 0). No model, no torch, no network beyond 127.0.0.1.
"""

from __future__ import annotations

import json
import socket
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable

import httpx
import pytest
import yaml

from callguard import eval as ev
from callguard import experiments as ex
from callguard import registry
from callguard.checks import fact_prompts as fp
from callguard.checks.facts import FactSheetCheck
from callguard.checks.questions import QuestionSetCheck, load_question_set, windows
from callguard.config import ROOT, AppConfig, Paths, load_config
from callguard.context import Context
from callguard.llm.kev import KevError, KevLLM, parse_fact_prompt
from callguard.llm.openai_compat import LLMIdentityError
from callguard.llm.pinned import PinnedLLM, PinnedLLMError
from callguard.pipeline import Pipeline
from callguard.plugins import Translator
from callguard.types import Segment, Transcript

GENERAL = ROOT / "config" / "general_questions.yaml"


# --------------------------------------------------------------------------------------------
# fake Kev service
# --------------------------------------------------------------------------------------------


class FakeKev:
    """State of one fake service: what it answers and what it was asked."""

    def __init__(self) -> None:
        self.requests: list[dict[str, Any]] = []
        self.model = "jaredpalmer/kev-4b"
        self.dtype = "bf16"
        self.fail_status: int | None = None
        # p(yes) per (state, qid); default: 0.9 if the state mentions a PIN and the question is about credentials
        self.answer: Callable[[str, str, dict[str, Any]], float] = \
            lambda state, qid, q: 0.9 if "PIN" in state and "credential" in qid else 0.05 + 0.01 * len(qid) / 10

    def handler(self) -> type[BaseHTTPRequestHandler]:
        fake = self

        class H(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/health":
                    self._send({"status": "ok", "model": fake.model, "dtype": fake.dtype, "loaded": True})
                else:
                    self._send({"detail": "not found"}, 404)

            def do_POST(self) -> None:
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fake.requests.append({"path": self.path, "body": body})
                if self.path != "/v1/systemone":
                    return self._send({"detail": "not found"}, 404)
                if fake.fail_status:
                    return self._send({"detail": "boom"}, fake.fail_status)
                answers = {}
                for qid, q in body["questions"].items():
                    p = fake.answer(body["state"], qid, q)
                    if q["type"] == "choice":
                        rest = (1 - p) / (len(q["criteria"]) - 1)
                        probs = {k: (p if k == "yes" else rest) for k in q["criteria"]}
                        answers[qid] = {"type": "choice", "choice": max(probs, key=probs.get), "probabilities": probs}
                    else:
                        answers[qid] = {"type": "noul", "noul": round(p, 4)}
                self._send({"model": fake.model, "answers": answers,
                            "usage": {"input_tokens": len(body["state"]) // 4, "output_tokens": 3}, "latency_ms": 1.5})

            def _send(self, obj: Any, status: int = 200) -> None:
                data = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args: Any) -> None:
                pass

        return H


@pytest.fixture
def kev() -> Iterator[tuple[FakeKev, str]]:
    fake = FakeKev()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), fake.handler())
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield fake, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def cfg_for(tmp_path: Path, url: str, checks: list[dict[str, Any]], **kev: Any) -> AppConfig:
    return AppConfig(name="t", asr={"type": "reference"},
                     paths=Paths(cache_dir=str(tmp_path / "cache"), runs_dir=str(tmp_path / "runs"), tuning=None),
                     llms={"kev": {"type": "kev", "base_url": url, "max_retries": 0, "timeout": 5, **kev},
                           "fake": {"type": "fake"}},
                     checks=checks, fusion={"type": "weighted", "threshold": 0.7})


GENERAL_CHECK = {"name": "general", "type": "questions", "llm": "kev", "questions": str(GENERAL)}


def call(texts: list[str] | None = None) -> Transcript:
    texts = texts or ["Grüezi, wie chan ich helfe?", "Ich möcht mis Konto aaluege.",
                      "Klar, ich bruche no de Bestätigungscode.", "Mini PIN isch 4711.", "Danke, adieu."]
    return Transcript(call_id="t1", segments=[
        Segment(id=f"S{i + 1:03d}", start=5.0 * i, end=5.0 * i + 4, text=t, speaker=f"SPK{i % 2}",
                role="advisor" if i % 2 == 0 else "customer") for i, t in enumerate(texts)])


# --------------------------------------------------------------------------------------------
# questions check on Kev: request shape, max p(yes)
# --------------------------------------------------------------------------------------------


def test_general_questions_file_is_the_teammates_list():
    qs = load_question_set(GENERAL)
    assert len(qs.questions) == 15 and qs.threshold == 0.7
    assert {q.list for q in qs.questions} == {"gesetzlich", "intern"}
    fams = {f.id: f for f in Context(load_config("recommended")).families()}
    assert all(q.family in fams and fams[q.family].can_alarm for q in qs.questions)  # max over families = max over all
    para = load_question_set(ROOT / "config/general_questions_para.yaml")
    assert [(q.id, q.family) for q in para.questions] == [(q.id, q.family) for q in qs.questions]
    assert all(a.instructions != b.instructions for a, b in zip(para.questions, qs.questions))


def test_one_request_per_call_with_all_questions_and_score_is_max_p(tmp_path, kev):
    fake, url = kev
    pipe = Pipeline(cfg_for(tmp_path, url, [GENERAL_CHECK]))
    res = pipe.process_transcript(call())

    assert len(fake.requests) == 1
    req = fake.requests[0]
    assert req["path"] == "/v1/systemone"
    body = req["body"]
    assert set(body) == {"state", "questions", "calibrated"} and body["calibrated"] is False
    assert body["state"] == call().render()  # our rendered transcript: [S004 00:15 customer] Mini PIN isch 4711.
    qs = load_question_set(GENERAL).questions
    assert set(body["questions"]) == {q.id for q in qs}
    assert all(set(q) == {"type", "instructions"} and q["type"] == "noul" for q in body["questions"].values())
    assert body["questions"]["insider_trading"]["instructions"] == next(q.instructions for q in qs if q.id == "insider_trading")

    c = res.checks["general"]
    assert c.meta["model"] == "jaredpalmer/kev-4b" and c.meta["backend"] == "noul_batch" and c.meta["llm_calls"] == 1
    assert c.meta["top_question"] in ("credential_disclosure", "credential_request")
    assert c.meta["call_score"] == 0.9
    assert c.family_scores["access"].score == 0.9 and c.family_scores["access"].detail["top_question"].startswith("credential")
    # family score = max of its questions; call score = max over all 15 questions
    for fid, fs in c.family_scores.items():
        assert fs.score == max(v["p"] for v in fs.detail["questions"].values())
    assert res.decision.score == pytest.approx(0.9) and res.decision.label == "alarm"
    assert res.decision.top_family == "access"


def test_max_rule_counts_questions_of_every_family(tmp_path, kev):
    fake, url = kev
    fake.answer = lambda state, qid, q: {"bribery": 0.66, "aml_source_of_funds": 0.4}.get(qid, 0.1)
    res = Pipeline(cfg_for(tmp_path, url, [GENERAL_CHECK])).process_transcript(call())
    assert res.decision.score == pytest.approx(0.66) and res.decision.top_family == "splitting"
    assert res.decision.label == "review"  # 0.66 within the 0.15 band below their 0.7
    assert res.checks["general"].family_scores["documentation"].score == 0.4


def test_localisation_finds_the_window_with_the_evidence(tmp_path, kev):
    fake, url = kev
    texts = [f"Satz {i} über das Wetter." for i in range(20)]
    texts[13] = "Mini PIN isch 4711."
    fake.answer = lambda state, qid, q: 0.9 if "PIN" in state and qid == "credential_disclosure" else 0.1
    check = dict(GENERAL_CHECK, localize=True, window_segments=4)
    res = Pipeline(cfg_for(tmp_path, url, [check])).process_transcript(call(texts))
    c = res.checks["general"]
    n_windows = len(windows(20, 4))
    assert len(fake.requests) == 1 + n_windows and c.meta["llm_calls"] == 1 + n_windows
    window_qs = [set(r["body"]["questions"]) for r in fake.requests[1:]]
    assert all(q == {"credential_disclosure"} for q in window_qs)  # only fired questions are localised
    (f,) = c.findings
    assert "S014" in f.segment_ids and len(f.segment_ids) == 4 and f.family == "access"
    assert res.decision.passages and "S014" in res.decision.passages[0].segment_ids


class UpperTranslator(Translator):
    """Test double for a translated view: same segments, upper-cased text, so the view read is visible."""

    def translate(self, transcript: Transcript, target_lang: str) -> Transcript:
        segs = [s.model_copy(update={"text": s.text.upper(), "words": []}) for s in transcript.segments]
        return transcript.model_copy(update={"segments": segs, "lang": target_lang})


def test_kev_check_reads_its_configured_view(tmp_path, kev):
    fake, url = kev
    cfg = cfg_for(tmp_path, url, [{"name": "keywords", "type": "keywords"}, dict(GENERAL_CHECK, view="en_from_de")])
    cfg = cfg.model_copy(update={"views": {
        "de": {"lang": "de"},
        "en_from_de": {"lang": "en", "from": "de", "translator": {"type": "test_kev:UpperTranslator"}}},
        "primary_view": "de"})
    res = Pipeline(cfg).process_transcript(call())
    assert res.checks["general"].view == "en_from_de" and res.checks["keywords"].view == "de"
    assert fake.requests[0]["body"]["state"] == res.views["en_from_de"].render()
    assert "MINI PIN ISCH 4711." in fake.requests[0]["body"]["state"]
    assert res.decision.families["access"].per_check["general"] == 0.9  # a check on another view still decides


def test_english_view_translations_are_shared_between_vllm_and_kev_profiles(tmp_path):
    sets = [f"paths.cache_dir={tmp_path / 'cache'}"]
    live_cfg, kev_cfg = load_config("recommended-views", sets), load_config("kev-views", sets)
    assert live_cfg.views == kev_cfg.views and live_cfg.primary_view == kev_cfg.primary_view
    vllm = {"object": "list", "data": [{"id": "callguard-llm", "root": "Qwen/Qwen2.5-7B-Instruct-AWQ"}]}
    live = Pipeline(live_cfg)
    live.ctx.llm("default")._client = live.ctx.llm("default")._build_client(
        httpx.MockTransport(lambda r: httpx.Response(200, json=vllm)))
    kevp = Pipeline(kev_cfg)
    # the translation cache key component that depends on the profile: identical
    assert live.translator_for("en_from_de").cache_params() == kevp.translator_for("en_from_de").cache_params()
    assert ex.is_oracle(ex.Variant(name="x"), load_config("kev-oracle", sets))


def test_windows_cover_the_call_with_half_overlap():
    assert windows(0, 8) == [] and windows(5, 8) == [(0, 5)]
    w = windows(20, 8)
    assert w[0] == (0, 8) and w[-1][1] == 20 and all(j - i == 8 for i, j in w)
    assert all(b[0] - a[0] == 4 for a, b in zip(w, w[1:-1]))


# --------------------------------------------------------------------------------------------
# cache keys
# --------------------------------------------------------------------------------------------


def test_cache_key_follows_questions_and_model_not_display_fields(tmp_path, kev):
    _, url = kev
    raw = yaml.safe_load(GENERAL.read_text())
    path = tmp_path / "q.yaml"

    def key(edit: Callable[[dict], None] | None = None, **llm: Any) -> str:
        r = json.loads(json.dumps(raw))
        if edit:
            edit(r)
        path.write_text(yaml.safe_dump(r))
        import os
        os.utime(path, (1, 1 + len(key.seen)))  # the question-set memo re-reads on mtime change
        key.seen.append(1)
        ctx = Context(cfg_for(tmp_path, url, [], **llm))
        c = registry.create("check", dict(GENERAL_CHECK, questions=str(path)), ctx=ctx)
        from callguard.cache import stable_hash
        return stable_hash(c.cache_key(ctx.families()))

    key.seen = []
    base = key()
    assert key() == base
    assert key(lambda r: r["questions"]["bribery"].update(instructions="Does anyone bribe anyone?")) != base
    assert key(lambda r: r["questions"]["bribery"].update(family="trade")) != base
    assert key(lambda r: r["questions"].pop("bribery")) != base
    assert key(lambda r: r["questions"]["bribery"].update(basis="StGB Art. 322ter")) == base  # display only
    assert key(model="jaredpalmer/kev-0.8b") != base
    assert key(calibrated=True) != base
    assert key(timeout=99, max_concurrency=3) == base  # speed / transport only


def test_kev_and_fake_llm_never_share_results(tmp_path, kev):
    _, url = kev
    ctx = Context(cfg_for(tmp_path, url, []))
    a = registry.create("check", GENERAL_CHECK, ctx=ctx).cache_key(ctx.families())
    b = registry.create("check", dict(GENERAL_CHECK, llm="fake"), ctx=ctx).cache_key(ctx.families())
    assert a["llm"] != b["llm"] and a["questions"] == b["questions"]


# --------------------------------------------------------------------------------------------
# failures: degraded, never a silent 0
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["down", "http500", "wrong_answers"])
def test_dead_or_broken_service_degrades_the_check(tmp_path, kev, mode):
    fake, url = kev
    if mode == "down":
        url = f"http://127.0.0.1:{free_port()}"
    elif mode == "http500":
        fake.fail_status = 500
    else:
        fake.answer = lambda state, qid, q: 7.0  # not a probability
    pipe = Pipeline(cfg_for(tmp_path, url, [GENERAL_CHECK]))
    res = pipe.process_transcript(call())
    c = res.checks["general"]
    assert c.meta.get("error") and not c.family_scores
    assert ev.failed_checks(res) == ["general"]  # the experiment marks the variant DEGRADED
    assert res.decision.label == "review" and "ausgefallen" in " ".join(res.decision.reasons)
    # nothing was cached: the next run asks again
    fake.fail_status, fake.answer = None, FakeKev().answer
    if mode != "down":
        again = Pipeline(cfg_for(tmp_path, url, [GENERAL_CHECK])).process_transcript(call())
        assert not again.checks["general"].meta.get("error") and again.decision.score == pytest.approx(0.9)


def test_unreachable_service_fails_fast_after_the_first_error(tmp_path):
    llm = KevLLM(Context(cfg_for(tmp_path, "http://x", [])), base_url=f"http://127.0.0.1:{free_port()}", max_retries=3)
    llm.backoff = 0.0
    with pytest.raises(KevError, match="not reachable"):
        llm.noul_batch("state", {"q": "Is it?"})
    assert llm._down_at is not None


# --------------------------------------------------------------------------------------------
# identity (audit F3)
# --------------------------------------------------------------------------------------------


def test_identity_is_confirmed_live_and_mismatches_abort(tmp_path, kev):
    fake, url = kev
    ids = ex.resolve_llm_identities(Context(cfg_for(tmp_path, url, [])))
    assert ids["kev"]["model_id"] == "jaredpalmer/kev-4b" and ids["kev"]["type"] == "kev"
    fake.model = "jaredpalmer/kev-0.8b"
    with pytest.raises(ex.LLMIdentityError, match="'kev'"):
        ex.resolve_llm_identities(Context(cfg_for(tmp_path, url, [])))
    fake.model, fake.dtype = "jaredpalmer/kev-4b", "fp32"
    with pytest.raises(ex.LLMIdentityError, match="fp32"):
        ex.resolve_llm_identities(Context(cfg_for(tmp_path, url, [])))
    with pytest.raises(LLMIdentityError, match="down or still loading"):
        KevLLM(Context(cfg_for(tmp_path, url, [])), base_url=f"http://127.0.0.1:{free_port()}").resolve_served(timeout=2)


def test_pinned_llm_keys_like_the_live_vllm_client_and_answers_nothing(tmp_path):
    sets = [f"paths.cache_dir={tmp_path / 'cache'}"]
    live = Context(load_config("recommended", sets)).llm("default")
    vllm = {"object": "list", "data": [{"id": "callguard-llm", "root": "Qwen/Qwen2.5-7B-Instruct-AWQ"}]}
    live._client = live._build_client(httpx.MockTransport(lambda r: httpx.Response(200, json=vllm)))
    kev_cfg = load_config("kev", sets)
    pinned = Context(kev_cfg).llm("default")
    assert isinstance(pinned, PinnedLLM)
    # the diarizer's role_llm key component: identical, so the roles cached with vLLM are found
    assert pinned.cache_params() == live.cache_params()
    assert kev_cfg.diarizer == load_config("recommended", sets).diarizer
    with pytest.raises(PinnedLLMError):
        pinned.chat([{"role": "user", "content": "hi"}])
    with pytest.raises(PinnedLLMError):
        pinned.choice_probs([{"role": "user", "content": "hi"}], ["yes", "no"])
    assert ex.resolve_llm_identities(Context(load_config("recommended", sets).model_copy(
        update={"llms": {"default": kev_cfg.llms["default"]}})))["default"]["model_id"] == "Qwen/Qwen2.5-7B-Instruct-AWQ"


# --------------------------------------------------------------------------------------------
# Kev as the facts backend (choice_probs seam, facts.py unchanged)
# --------------------------------------------------------------------------------------------


def test_fact_prompt_round_trip_and_refusal():
    msgs = fp.fact_messages("[S001 00:00 customer] Mini PIN isch 4711.", "Zugangsinformation", "access",
                            "Is a complete code   said?", transcript_lang="de")
    transcript, question, topic = parse_fact_prompt(msgs)
    assert transcript == "[S001 00:00 customer] Mini PIN isch 4711."
    assert question == "Is a complete code said?" and topic == "Zugangsinformation [access]"
    with pytest.raises(ValueError, match="not a fact prompt"):
        parse_fact_prompt([{"role": "user", "content": "Antworte mit einer Ziffer: 2+1?"}])


FACTS_KEV = {"name": "facts", "type": "facts", "llm": "kev", "evidence": False}


def test_facts_check_on_kev_noul(tmp_path, kev):
    fake, url = kev
    fake.answer = lambda state, qid, q: 0.8 if "PIN" in state and "code" in q["instructions"].lower() else 0.1
    pipe = Pipeline(cfg_for(tmp_path, url, [FACTS_KEV]))
    res = pipe.process_transcript(call())
    c = res.checks["facts"]
    assert not c.meta.get("errors") and c.meta["model"] == "jaredpalmer/kev-4b"
    table = pipe.checks[0].table()
    n_facts = sum(len(table.families[f].facts) for f in c.family_scores)
    assert len(fake.requests) == n_facts == c.meta["llm_calls"]  # one Kev request per fact
    for r in fake.requests:
        b = r["body"]
        assert b["state"] == call().render() and list(b["questions"]) == ["fact"]
        q = b["questions"]["fact"]
        assert q["type"] == "noul" and q["instructions"].startswith("Topic: ") and "\nQuestion" not in q["instructions"]
    access = c.family_scores["access"].detail["facts"]
    spoken = next(v for v in access.values() if v["p"]["yes"] == 0.8)
    assert spoken["p"] == {"yes": 0.8, "no": 0.2, "unclear": 0.0} and spoken["method"] == "logprobs"
    # probes are cached per prompt + Kev identity: a second check instance asks nothing
    fake.requests.clear()
    Pipeline(cfg_for(tmp_path, url, [dict(FACTS_KEV, unclear_band=[0.2, 0.6])])).process_transcript(call())
    assert fake.requests == []


def test_facts_check_on_kev_choice_keeps_unclear(tmp_path, kev):
    fake, url = kev
    fake.answer = lambda state, qid, q: 0.5
    res = Pipeline(cfg_for(tmp_path, url, [FACTS_KEV], fact_answer="choice")).process_transcript(call())
    q = fake.requests[0]["body"]["questions"]["fact"]
    assert q["type"] == "choice" and list(q["criteria"]) == ["yes", "no", "unknown"]
    fact = next(iter(res.checks["facts"].family_scores["access"].detail["facts"].values()))
    assert fact["p"] == {"yes": 0.5, "no": 0.25, "unclear": 0.25}


def test_facts_check_with_kev_down_is_degraded_with_the_cause(tmp_path):
    url = f"http://127.0.0.1:{free_port()}"
    res = Pipeline(cfg_for(tmp_path, url, [FACTS_KEV])).process_transcript(call())
    c = res.checks["facts"]
    assert c.meta.get("error") and "not reachable" in c.meta["error"] and not c.family_scores
    assert ev.failed_checks(res) == ["facts"]


def test_kev_cannot_write_evidence_text(tmp_path, kev):
    _, url = kev
    llm = Context(cfg_for(tmp_path, url, [])).llm("kev")
    with pytest.raises(NotImplementedError, match="evidence: false"):
        llm.chat([{"role": "user", "content": "x"}])


# --------------------------------------------------------------------------------------------
# questions check on a normal LLM (qwen_general path), the experiment spec
# --------------------------------------------------------------------------------------------


def test_questions_check_on_an_llm_asks_one_prompt_per_question(tmp_path):
    cfg = cfg_for(tmp_path, "http://unused", [dict(GENERAL_CHECK, llm="fake", parallel=4)])
    res = Pipeline(cfg).process_transcript(call())
    c = res.checks["general"]
    assert c.meta["backend"] == "single_prompts" and c.meta["llm_calls"] == 15 and not c.meta.get("errors")
    assert res.decision.score == pytest.approx(max(fs.score for fs in c.family_scores.values()))
    # single-question probes are cached: a second instance (other fusion-only params) asks nothing
    again = Pipeline(cfg_for(tmp_path, "http://unused", [dict(GENERAL_CHECK, llm="fake", weight=0.5)]))
    assert isinstance(again.checks[0], QuestionSetCheck)
    meta = again.checks[0].run(call(), again.ctx.families()).meta
    assert meta["llm_calls"] == 0 and meta["cached_probes"] == 15


def test_experiment_spec_builds_offline():
    spec = ex.load_spec("experiments/kev_vs_facts.yaml")
    assert spec.split == "dev" and spec.baseline == "champion"
    names = {v.name for v in spec.variants}
    assert {"kev_general", "kev_facts", "qwen_general", "champion"} <= names
    for v in spec.variants:
        cfg = ex.variant_config(spec, v)
        ctx = Context(cfg)
        checks = [registry.create("check", c, ctx=ctx) for c in cfg.checks]
        if v.name.startswith("kev_") and not v.refuse_from:
            assert any(ctx.llm(getattr(c, "llm_name", "")).plugin_type == "kev" for c in checks
                       if getattr(c, "llm_name", None)), v.name
            assert cfg.llms["default"]["type"] == "pinned"  # no vLLM needed while Kev holds the GPU
        if v.name.startswith("qwen_") or v.name == "champion":
            assert set(cfg.llms) == {"default"} and cfg.llms["default"]["type"] == "openai_compat"
        if any(isinstance(c, FactSheetCheck) and c.llm_name.startswith("kev") for c in checks):
            assert not next(c for c in checks if isinstance(c, FactSheetCheck)).evidence
    en = ex.variant_config(spec, spec.variant("kev_general_en"))
    assert next(c for c in en.checks if c["name"] == "general")["view"] == "en_from_de" and "en_from_de" in en.views
    qen = ex.variant_config(spec, spec.variant("qwen_general_en"))
    assert next(c for c in qen.checks if c["name"] == "general")["view"] == "en_from_de"
    assert qen.views == en.views  # same translations
    assert ex.is_oracle(spec.variant("kev_general_oracle"), ex.variant_config(spec, spec.variant("kev_general_oracle")))
    assert not ex.is_oracle(spec.variant("kev_general_en"), en)
    first = [v.name for v in spec.variants[:4]]
    assert first == ["kev_general", "kev_general_en", "kev_facts", "qwen_general"]
    for name in ("kev_perturbed",):
        s = ex.load_spec(f"experiments/{name}.yaml")
        for v in s.variants:
            ex.variant_config(s, v)
