"""Remote GPU support, offline: the ASR server + RemoteASR round trip (wrapping the reference backend),
the served-model identity behind the LLM alias, ``callguard doctor`` and the scripts in scripts/remote/.

Nothing here loads Whisper or an LLM: the ASR server wraps the ``reference`` backend, the LLM servers
are mocks (httpx.MockTransport, or a tiny in-process OpenAI-shaped HTTP server for the doctor).
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from callguard import cli, registry
from callguard.asr.reference import ReferenceASR
from callguard.asr.remote import RemoteASR, RemoteASRError
from callguard.checks.llm_judge import LLMJudgeCheck
from callguard.config import ROOT, AppConfig, Paths, load_config
from callguard.context import Context
from callguard.llm.openai_compat import OpenAICompatLLM, served_identity
from callguard.pipeline import Pipeline
from callguard.serve import asr_server, doctor
from callguard.serve.asr_server import ASRService, make_server
from callguard.types import Family

DATA = ROOT / "data_upstream/inventx-case-study/data"
CALL = "Stufe1_D02-K1"
WAV = DATA / "Audio" / f"{CALL}.wav"
needs_data = pytest.mark.skipif(not (WAV.exists() and (DATA / "Transkript").exists()), reason="case data missing")
runner = CliRunner()


def tmp_sets(tmp_path: Path) -> list[str]:
    return [f"paths.cache_dir={tmp_path / 'cache'}", f"paths.runs_dir={tmp_path / 'runs'}"]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --------------------------------------------------------------------------------------------
# ASR server + RemoteASR
# --------------------------------------------------------------------------------------------


class Running:
    def __init__(self, service: ASRService, token: str | None = None):
        self.service = service
        self.httpd = make_server(service, "127.0.0.1", 0, token)
        self.url = self.httpd.url
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server(tmp_path: Path) -> Iterator[Running]:
    """The ASR server around the reference backend (demo-offline), with its own cache dir."""
    srv = Running(ASRService(load_config("demo-offline", tmp_sets(tmp_path / "server"))))
    yield srv
    srv.stop()


def client_cfg(tmp_path: Path, url: str, *extra: str) -> AppConfig:
    return load_config("demo-offline", [*tmp_sets(tmp_path / "client"), "asr.type=remote", f"asr.url={url}",
                                        *extra])


@needs_data
def test_round_trip_matches_the_local_backend(tmp_path: Path, server: Running) -> None:
    cfg = load_config("demo-offline", tmp_sets(tmp_path))
    local = ReferenceASR(Context(cfg, use_cache=False)).transcribe(WAV, CALL)
    asr = RemoteASR(Context(cfg, use_cache=False), url=server.url, model_tag=server.service.model_tag)
    t = asr.transcribe(WAV, CALL)
    assert [(s.id, s.start, s.end, s.text, s.role) for s in t.segments] == \
           [(s.id, s.start, s.end, s.text, s.role) for s in local.segments]
    assert t.call_id == CALL and t.audio_path == str(WAV)  # fixed locally: the server saw a temp file
    assert t.asr_backend == "reference" and t.duration == local.duration
    assert t.meta["remote"]["model_tag"] == server.service.model_tag
    assert t.meta["remote"]["url"] == server.url and t.meta["remote"]["server_config"] == "demo-offline"
    assert asr.cache_params() == {"type": "remote", "model_tag": server.service.model_tag}


@needs_data
def test_pipeline_transcribes_remotely_once_then_from_cache(tmp_path: Path, server: Running) -> None:
    pipe = Pipeline(client_cfg(tmp_path, server.url, f"asr.model_tag={server.service.model_tag}"))
    assert isinstance(pipe.asr, RemoteASR)
    t1 = pipe.transcribe(WAV, CALL)
    t2 = pipe.transcribe(WAV, CALL)
    assert server.service.served == 1  # the second call never left the laptop
    assert t1.segments == t2.segments and t2.call_id == CALL and t2.audio_path == str(WAV)
    result = pipe.process(WAV, CALL, emit=False)  # the whole chain on top (fake LLM checks)
    assert result.decision.label in ("alarm", "review", "no_alert") and result.transcript.segments
    assert server.service.served == 1


@needs_data
def test_server_shares_the_pipeline_asr_cache(tmp_path: Path) -> None:
    """A call `callguard batch` transcribed on the PC is not transcribed again for the laptop."""
    cfg = load_config("demo-offline", tmp_sets(tmp_path))
    Pipeline(cfg).transcribe(WAV, CALL)  # mode A run on the PC fills .cache/asr
    calls: list[str] = []
    service = ASRService(cfg)
    original = service.asr.transcribe
    service.asr.transcribe = lambda p, c: calls.append(c) or original(p, c)  # type: ignore[method-assign]
    t = service.transcribe(WAV.read_bytes(), CALL, "x.wav")
    assert calls == [] and t.segments and t.audio_path is None


@needs_data
def test_model_tag_is_adopted_from_the_server_when_not_configured(tmp_path: Path, server: Running) -> None:
    pipe = Pipeline(client_cfg(tmp_path, server.url))
    assert pipe.asr.cache_params()["model_tag"] == server.service.model_tag
    assert pipe.transcribe(WAV, CALL).segments


@needs_data
def test_tag_mismatch_is_refused_and_not_cached(tmp_path: Path, server: Running) -> None:
    pipe = Pipeline(client_cfg(tmp_path, server.url, "asr.model_tag=whisper-large-v3-gsw-fp16-b5-cuda"))
    with pytest.raises(RemoteASRError, match="whisper-large-v3-gsw-fp16-b5-cuda") as e:
        pipe.transcribe(WAV, CALL)
    assert "409" in str(e.value) and server.service.model_tag in str(e.value)
    assert server.service.served == 0
    assert not (tmp_path / "client" / "cache" / "asr").exists()


@needs_data
def test_token_is_required_when_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    srv = Running(ASRService(load_config("demo-offline", tmp_sets(tmp_path))), token="s3cret")
    try:
        ctx = Context(load_config("demo-offline", tmp_sets(tmp_path)), use_cache=False)
        monkeypatch.delenv("CALLGUARD_TOKEN", raising=False)
        with pytest.raises(RemoteASRError, match="401.*CALLGUARD_TOKEN"):
            RemoteASR(ctx, url=srv.url).transcribe(WAV, CALL)
        with pytest.raises(RemoteASRError, match="401"):
            RemoteASR(ctx, url=srv.url, token="wrong").health()
        assert httpx.get(f"{srv.url}/health").status_code == 401
        assert srv.service.served == 0
        assert RemoteASR(ctx, url=srv.url, token="s3cret").transcribe(WAV, CALL).segments
        monkeypatch.setenv("CALLGUARD_TOKEN", "s3cret")  # the default: read from the environment
        assert RemoteASR(ctx, url=srv.url).health()["status"] == "ok"
        monkeypatch.setenv("CG_OTHER_SECRET", "s3cret")
        assert RemoteASR(ctx, url=srv.url, token="env:CG_OTHER_SECRET").health()["status"] == "ok"
        assert "token" not in RemoteASR(ctx, url=srv.url, model_tag="t").cache_params()
    finally:
        srv.stop()


def test_unreachable_server_gives_a_hint_and_fails_fast(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = Context(load_config("demo-offline", tmp_sets(tmp_path)), use_cache=False)
    asr = RemoteASR(ctx, url=f"http://127.0.0.1:{free_port()}", model_tag="t")
    wav = tmp_path / "x.wav"
    wav.write_bytes(b"RIFF")
    with pytest.raises(RemoteASRError, match=r"not reachable - start scripts/remote/serve_models\.sh.*tailscale status"):
        asr.transcribe(wav, "x")
    monkeypatch.setattr(httpx, "request", lambda *a, **k: pytest.fail("no request during the cooldown"))
    with pytest.raises(RemoteASRError, match="failed less than"):
        asr.transcribe(wav, "x")


@needs_data
def test_server_errors_are_clear(tmp_path: Path, server: Running) -> None:
    ctx = Context(load_config("demo-offline", tmp_sets(tmp_path)), use_cache=False)
    with pytest.raises(RemoteASRError, match="422.*no script for call 'Stufe9_D99-K1'"):
        RemoteASR(ctx, url=server.url).transcribe(WAV, "Stufe9_D99-K1")
    assert httpx.post(f"{server.url}/transcribe", content=b"abc").status_code == 400  # no call_id
    assert httpx.post(f"{server.url}/transcribe?call_id=x", content=b"").status_code == 400
    assert httpx.get(f"{server.url}/nope").status_code == 404
    h = httpx.get(f"{server.url}/health").json()
    assert h["status"] == "ok" and h["asr"]["type"] == "reference" and h["model_tag"] == server.service.model_tag


def test_server_refuses_to_serve_a_remote_profile_or_all_interfaces(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="cannot be served"):
        ASRService(load_config("remote", tmp_sets(tmp_path)))
    with pytest.raises(SystemExit) as e:
        asr_server.main(["-c", "demo-offline", "--host", "0.0.0.0"])
    assert e.value.code == 2


def test_server_tag_defaults(tmp_path: Path) -> None:
    service = ASRService(load_config("demo-offline", tmp_sets(tmp_path)))
    assert service.model_tag.startswith("reference-")
    assert ASRService(load_config("demo-offline", tmp_sets(tmp_path)), model_tag="mine").model_tag == "mine"
    assert ASRService(load_config("demo-offline", [*tmp_sets(tmp_path), "asr.model_tag=cfg"])).model_tag == "cfg"


@pytest.mark.skipif(not (ROOT / "models/asr/whisper-turbo-gsw-ct2-int8/model.bin").exists(),
                    reason="local ASR model not downloaded")
def test_gpu_profile_announces_its_tag_without_loading_whisper(tmp_path: Path) -> None:
    service = ASRService(load_config("gpu-12gb", tmp_sets(tmp_path)))  # builds the plugin, loads nothing
    assert service.model_tag == load_config("remote").asr["model_tag"] == "whisper-turbo-gsw-int8-cuda"
    params = service.health()["asr"]
    assert params["device"] == "cuda" and params["compute_type"] == "int8_float16" and "model_tag" not in params


def test_registry_and_inherited_params(monkeypatch: pytest.MonkeyPatch) -> None:
    ctx = Context(load_config("demo-offline"), use_cache=False)
    asr = registry.create("asr", {"type": "remote", "url": "http://h:8010/", "model_tag": "t"}, ctx=ctx)
    assert isinstance(asr, RemoteASR) and asr.url == "http://h:8010" and asr.timeout == 900
    # --set asr.type=remote on a faster-whisper profile keeps model/device/...: ignored, typos raise
    cfg = load_config("gpu-12gb", ["asr.type=remote", "asr.url=http://h:8010"])
    asr = registry.create("asr", cfg.asr, ctx=ctx)
    assert "device" in asr.ignored_params and asr.cache_params()["model_tag"] == "whisper-turbo-gsw-int8-cuda"
    with pytest.raises(TypeError, match="urll"):
        registry.create("asr", {"type": "remote", "url": "http://h:8010", "urll": "x"}, ctx=ctx)
    with pytest.raises(ValueError, match="http"):
        registry.create("asr", {"type": "remote", "url": "gpu-pc:8010"}, ctx=ctx)
    monkeypatch.setenv("CALLGUARD_GPU_HOST", "100.101.102.103")
    remote = load_config("remote")
    assert remote.asr["url"] == "http://100.101.102.103:8010"
    assert remote.llms["default"]["base_url"] == "http://100.101.102.103:8000/v1"
    assert remote.llms["default"]["cache_tag"] is None and remote.llms["default"]["model"] == "callguard-llm"


# --------------------------------------------------------------------------------------------
# Served-model identity behind the LLM alias
# --------------------------------------------------------------------------------------------


VLLM = {"object": "list", "data": [{"id": "callguard-llm", "object": "model", "owned_by": "vllm",
                                    "root": "Qwen/Qwen2.5-7B-Instruct-AWQ", "parent": None,
                                    "max_model_len": 16384}]}
LLAMA_CPP_PYTHON = {"object": "list", "data": [{"id": "callguard-llm", "object": "model", "owned_by": "me"}]}
LLAMA_SERVER = {"object": "list", "data": [{"id": "callguard-llm", "object": "model", "owned_by": "llamacpp",
                                            "meta": {"n_params": 7615616512, "size": 4677120000}}]}


class Models:
    """Mock /models endpoint whose answer the test can swap (or turn into a connection error)."""

    def __init__(self, answer: Any):
        self.answer = answer
        self.hits = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.hits += 1
        if isinstance(self.answer, Exception):
            raise self.answer
        return httpx.Response(200, json=self.answer)


def alias_llm(models: Models, ctx: Any = None, **kw: Any) -> OpenAICompatLLM:
    llm = OpenAICompatLLM(ctx, **{"base_url": "http://gpu.test/v1", "model": "callguard-llm", **kw})
    llm._client = llm._build_client(httpx.MockTransport(models))
    return llm


def test_served_identity_shapes() -> None:
    assert served_identity(VLLM, "callguard-llm") == (True, "Qwen/Qwen2.5-7B-Instruct-AWQ")
    assert served_identity(LLAMA_CPP_PYTHON, "callguard-llm") == (True, None)
    assert served_identity(LLAMA_SERVER, "callguard-llm") == (True, "callguard-llm#gguf:7615616512p:4677120000b")
    assert served_identity({"data": [{"id": "callguard-llm:latest"}]}, "callguard-llm") == (True, None)  # Ollama
    assert served_identity(VLLM, "other") == (False, None)
    lora = {"data": [{"id": "callguard-llm", "root": "/adapters/gsw", "parent": "Qwen/Qwen2.5-7B-Instruct"}]}
    assert served_identity(lora, "callguard-llm") == (True, "/adapters/gsw@Qwen/Qwen2.5-7B-Instruct")
    unaliased = {"data": [{"id": "Qwen/Qwen2.5-7B-Instruct-AWQ", "root": "Qwen/Qwen2.5-7B-Instruct-AWQ"}]}
    assert served_identity(unaliased, "Qwen/Qwen2.5-7B-Instruct-AWQ") == (True, None)  # same as before
    assert served_identity({"error": "x"}, "m") == (False, None) and served_identity(None, "m") == (False, None)


def test_cache_key_follows_the_model_behind_the_alias() -> None:
    models = Models(VLLM)
    llm = alias_llm(models)
    assert llm.model_id == "Qwen/Qwen2.5-7B-Instruct-AWQ"
    first = llm.cache_params()
    assert first["model"] == "Qwen/Qwen2.5-7B-Instruct-AWQ" and models.hits == 1  # memoized within the TTL
    models.answer = {"data": [{**VLLM["data"][0], "root": "Qwen/Qwen3-8B-AWQ"}]}  # swapped on the PC
    assert llm.cache_params() == first
    llm.served_ttl = 0.0
    assert llm.cache_params()["model"] == "Qwen/Qwen3-8B-AWQ" and models.hits == 2


def test_servers_without_a_checkpoint_name_keep_the_old_key() -> None:
    llm = alias_llm(Models(LLAMA_CPP_PYTHON))
    assert llm.model_id == "callguard-llm" and llm.cache_params()["model"] == "callguard-llm"


def test_cache_tag_wins_without_asking_the_server() -> None:
    models = Models(VLLM)
    llm = alias_llm(models, cache_tag="qwen2.5-7b-q4km-ollama")
    assert llm.model_id == "qwen2.5-7b-q4km-ollama" and llm.cache_params()["model"] == "qwen2.5-7b-q4km-ollama"
    assert models.hits == 0
    assert alias_llm(Models(VLLM), cache_tag="").cache_tag is None  # ${CALLGUARD_LLM_TAG:-} -> unset


def test_unreachable_server_falls_back_to_the_last_identity_seen(tmp_path: Path) -> None:
    cfg = AppConfig(name="t", asr={"type": "reference"}, paths=Paths(cache_dir=str(tmp_path / "cache")))
    ctx = Context(cfg)
    assert alias_llm(Models(VLLM), ctx).model_id == "Qwen/Qwen2.5-7B-Instruct-AWQ"  # seen once, remembered
    down = Models(httpx.ConnectError("refused"))
    llm = alias_llm(down, ctx)
    assert llm.model_id == "Qwen/Qwen2.5-7B-Instruct-AWQ"  # e.g. laptop with the GPU box's pulled .cache
    assert llm.model_id == "Qwen/Qwen2.5-7B-Instruct-AWQ" and down.hits == 1  # retried only after cooldown
    assert alias_llm(Models(httpx.ConnectError("refused"))).model_id == "callguard-llm"  # never seen: name
    assert alias_llm(Models(httpx.ConnectError("x")), Context(cfg, use_cache=False)).model_id == "callguard-llm"
    # a server that now names nothing behind the alias overrides the remembered identity
    assert alias_llm(Models(LLAMA_CPP_PYTHON), ctx).model_id == "callguard-llm"
    assert alias_llm(Models(httpx.ConnectError("refused")), ctx).model_id == "callguard-llm"


def test_llm_checks_and_roles_key_on_the_served_model(tmp_path: Path) -> None:
    cfg = AppConfig(name="t", asr={"type": "reference"}, paths=Paths(cache_dir=str(tmp_path / "cache")),
                    llms={"default": {"type": "openai_compat", "base_url": "http://gpu.test/v1",
                                      "model": "callguard-llm"}})
    models = Models(VLLM)
    ctx = Context(cfg)
    llm = ctx.llm("default")
    llm._client = llm._build_client(httpx.MockTransport(models))
    fam = Family(id="trade", label="Insiderhandel", policy="p")
    key = LLMJudgeCheck(ctx).cache_key([fam])
    assert key["llm"]["model"] == "Qwen/Qwen2.5-7B-Instruct-AWQ"
    models.answer = {"data": [{**VLLM["data"][0], "root": "Qwen/Qwen3-8B-AWQ"}]}
    llm.served_ttl = 0.0
    assert LLMJudgeCheck(ctx).cache_key([fam]) != key  # new weights, new cache entries


# --------------------------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------------------------


class FakeOpenAI(BaseHTTPRequestHandler):
    """Just enough of vLLM's API for the doctor's probes."""

    def do_GET(self) -> None:
        self._send(VLLM if self.path.endswith("/models") else {"error": "not found"},
                   200 if self.path.endswith("/models") else 404)

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        logprobs = None
        if body.get("logprobs"):
            content = "3"
            logprobs = {"content": [{"token": "3", "logprob": -0.1, "top_logprobs": [
                {"token": "3", "logprob": -0.1}, {"token": "4", "logprob": -2.5}]}]}
        elif body.get("response_format"):
            content = '{"ok": true}'
        else:
            content = "ja"
        self._send({"choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                                 "finish_reason": "stop", "logprobs": logprobs}]})

    def _send(self, obj: Any, status: int = 200) -> None:
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args: Any) -> None:
        pass


@pytest.fixture
def fake_vllm() -> Iterator[str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}/v1"
    httpd.shutdown()
    httpd.server_close()


def profile(tmp_path: Path, body: str) -> str:
    p = tmp_path / "probe.yaml"
    p.write_text(f"extends: {ROOT / 'config' / 'demo-offline.yaml'}\n{body}")
    return str(p)


def by_key(rows: list[doctor.Row]) -> dict[tuple[str, str], doctor.Row]:
    return {(r.area, r.item): r for r in rows}


def test_doctor_offline_profile_is_all_green(tmp_path: Path) -> None:
    rows = doctor.run("demo-offline", tmp_sets(tmp_path))
    assert not doctor.failed(rows), [r for r in rows if r.status == doctor.FAIL]
    got = by_key(rows)
    for item in ("server", "chat", "json", "logprobs"):
        assert got[("llm:default", item)].status == doctor.OK
    assert got[("asr", "reference")].status == doctor.OK and got[("config", "demo-offline")].status == doctor.OK
    result = runner.invoke(cli.app, ["doctor", "-c", "demo-offline", *sum((["--set", s] for s in tmp_sets(tmp_path)), [])])
    assert result.exit_code == 0, result.output
    assert "FAIL" not in result.output and "OK" in result.output


def test_doctor_reports_an_unreachable_llm_and_exits_1(tmp_path: Path) -> None:
    yaml = profile(tmp_path, "llms:\n  default: {type: openai_compat, base_url: "
                             f"'http://127.0.0.1:{free_port()}/v1', model: callguard-llm}}\n")
    rows = doctor.run(yaml, tmp_sets(tmp_path))
    got = by_key(rows)
    assert got[("llm:default", "server")].status == doctor.FAIL
    assert "serve_models.sh" in got[("llm:default", "server")].hint
    assert got[("llm:default", "chat")].status == doctor.SKIP and doctor.failed(rows)
    sets = sum((["--set", s] for s in tmp_sets(tmp_path)), [])
    result = runner.invoke(cli.app, ["doctor", "-c", yaml, *sets])
    assert result.exit_code == 1 and "FAIL" in result.output


def test_doctor_probes_a_vllm_shaped_server(tmp_path: Path, fake_vllm: str) -> None:
    yaml = profile(tmp_path, f"llms:\n  default: {{type: openai_compat, base_url: '{fake_vllm}', "
                             "model: callguard-llm, json_mode: json_schema}\n")
    rows = doctor.run(yaml, tmp_sets(tmp_path))
    got = by_key(rows)
    assert not doctor.failed(rows), [r for r in rows if r.status == doctor.FAIL]
    assert got[("llm:default", "model")].detail == "callguard-llm = Qwen/Qwen2.5-7B-Instruct-AWQ"
    assert all(got[("llm:default", i)].status == doctor.OK for i in ("server", "chat", "json", "logprobs"))
    # the doctor remembered the identity for offline cache lookups
    assert list((tmp_path / "cache" / "llm_served").glob("*.json"))


@needs_data
def test_doctor_checks_the_remote_asr_and_its_tag(tmp_path: Path, server: Running) -> None:
    ok = doctor.run(profile(tmp_path, f"asr: {{type: remote, url: '{server.url}', "
                                      f"model_tag: {server.service.model_tag}}}\n"), tmp_sets(tmp_path))
    got = by_key(ok)
    assert got[("asr", "server")].status == doctor.OK and got[("asr", "model_tag")].status == doctor.OK
    bad = by_key(doctor.run(profile(tmp_path, f"asr: {{type: remote, url: '{server.url}', model_tag: other}}\n"),
                            tmp_sets(tmp_path)))
    assert bad[("asr", "model_tag")].status == doctor.FAIL
    down = by_key(doctor.run(profile(tmp_path, f"asr: {{type: remote, url: 'http://127.0.0.1:{free_port()}', "
                                               "model_tag: t}\n"), tmp_sets(tmp_path)))
    assert down[("asr", "server")].status == doctor.FAIL and "tailscale" in down[("asr", "server")].detail


def test_doctor_broken_config_is_one_fail_row(tmp_path: Path) -> None:
    p = tmp_path / "broken.yaml"
    p.write_text("asr: {type: reference}\nllms: {default: {type: fake, model: '${CG_DOCTOR_UNSET}'}}\n")
    os.environ.pop("CG_DOCTOR_UNSET", None)
    rows = doctor.run(str(p))
    assert len(rows) == 1 and rows[0].status == doctor.FAIL and "CG_DOCTOR_UNSET" in rows[0].detail


# --------------------------------------------------------------------------------------------
# scripts/remote
# --------------------------------------------------------------------------------------------

SCRIPTS = sorted((ROOT / "scripts" / "remote").glob("*.sh"))
EXPECTED = {"setup_gpu_host.sh", "serve_models.sh", "sync_to_host.sh", "pull_results.sh", "tunnel.sh"}


def test_all_remote_scripts_exist_and_are_executable() -> None:
    assert EXPECTED <= {p.name for p in SCRIPTS}
    for p in SCRIPTS:
        if p.name == "cuda_env.sh":  # generated on the GPU host, sourced, not executed
            continue
        assert os.access(p, os.X_OK), p.name
        assert "set -euo pipefail" in p.read_text(), p.name


@pytest.mark.parametrize("script", sorted(EXPECTED))
def test_script_syntax_and_help(script: str) -> None:
    path = ROOT / "scripts" / "remote" / script
    subprocess.run(["bash", "-n", str(path)], check=True)
    out = subprocess.run(["bash", str(path), "--help"], capture_output=True, text=True, timeout=30,
                         env={**os.environ, "CALLGUARD_GPU_HOST": ""})
    assert out.returncode == 0, out.stderr
    assert "Usage" in out.stdout


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_scripts_are_shellcheck_clean() -> None:
    out = subprocess.run(["shellcheck", "-x", *map(str, SCRIPTS)], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout
