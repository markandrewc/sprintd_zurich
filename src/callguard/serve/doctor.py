"""Readiness probes behind ``callguard doctor -c <profile>``: is everything the profile needs present
and reachable, before a 60-call batch finds out on call 1?

Never loads a model: servers are asked over HTTP (``GET /models``, a 1-token chat, ``/health``), local
models are checked as files, CUDA through ``ctranslate2.get_cuda_device_count()`` and by loading the
cuBLAS library. Every probe yields rows (OK / WARN / FAIL / SKIP, detail, hint) and a broken probe
never stops the others. FAIL means "this run will fail"; WARN means "works, but worse or slower".
"""

from __future__ import annotations

import ctypes
import sys
import time
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

from callguard import registry
from callguard.config import ROOT, AppConfig, load_config
from callguard.context import Context
from callguard.llm import parse_json

OK, WARN, FAIL, SKIP = "OK", "WARN", "FAIL", "SKIP"

SERVE_HINT = ("on the GPU host: scripts/remote/serve_models.sh start; from the laptop: `tailscale status`, "
              "or scripts/remote/tunnel.sh + CALLGUARD_GPU_HOST=127.0.0.1")
CUDA_LIB_HINT = "source scripts/remote/cuda_env.sh (written by scripts/remote/setup_gpu_host.sh)"
JSON_SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"],
               "additionalProperties": False}


@dataclass
class Row:
    area: str
    item: str
    status: str
    detail: str = ""
    hint: str = ""


def _rel(p: str | Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _root_path(p: str) -> Path:
    path = Path(p).expanduser()
    return path if path.is_absolute() else ROOT / path


def failed(rows: list[Row]) -> bool:
    return any(r.status == FAIL for r in rows)


def _err(e: BaseException) -> str:
    text = " ".join(f"{type(e).__name__}: {e}".split())
    return text if len(text) <= 300 else text[:297] + "..."


def run(config: str, overrides: list[str] | None = None, *, use_cache: bool = True) -> list[Row]:
    """All probes for one profile, in display order."""
    try:
        cfg = load_config(config, overrides)
    except Exception as e:
        return [Row("config", str(config), FAIL, _err(e), "fix the profile, its environment variables or --set")]
    rows = [Row("config", cfg.name, OK, f"{_rel(cfg.source_path or '')}"
                + (f" - {cfg.description}" if cfg.description else ""))]
    ctx = Context(cfg, use_cache=use_cache)
    for area, probe in (("llm", lambda: _llms(cfg, ctx)), ("asr", lambda: _asr(cfg, ctx)),
                        ("diarizer", lambda: _diarizer(cfg, ctx)), ("checks", lambda: _checks(cfg, ctx)),
                        ("data", lambda: _data(cfg, ctx)), ("sinks", lambda: _sinks(cfg, ctx))):
        rows += _guard(area, probe)
    return rows


def _guard(area: str, probe: Callable[[], list[Row]]) -> list[Row]:
    try:
        return probe()
    except Exception as e:  # a probe bug must not hide the other rows
        return [Row(area, "probe", FAIL, _err(e), "unexpected error in the doctor itself")]


# --------------------------------------------------------------------------------------------
# LLMs
# --------------------------------------------------------------------------------------------


def _llms(cfg: AppConfig, ctx: Context) -> list[Row]:
    if not cfg.llms:
        return [Row("llm", "-", SKIP, "no LLM configured")]
    rows: list[Row] = []
    for name, spec in cfg.llms.items():
        rows += _guard("llm", lambda name=name, spec=spec: _llm(name, dict(spec), ctx))
    return rows


def _llm(name: str, spec: dict[str, Any], ctx: Context) -> list[Row]:
    area, kind = f"llm:{name}", str(spec.get("type", ""))
    if kind == "openai_compat":  # probes must fail fast, not after the profile's retries and timeouts
        spec = {**spec, "timeout": min(float(spec.get("timeout", 120)), 60.0), "max_retries": 0}
    try:
        llm = registry.create("llm", spec, ctx=ctx)
    except Exception as e:
        return [Row(area, "plugin", FAIL, _err(e), f"fix llms.{name} in the profile")]

    rows: list[Row] = []
    if kind == "openai_compat":
        try:
            entries = llm.list_models()
        except Exception as e:
            return [Row(area, "server", FAIL, f"{llm.base_url}: {_err(e)}", SERVE_HINT),
                    *(Row(area, item, SKIP, "server not reachable") for item in ("chat", "json", "logprobs"))]
        ids = [str(e.get("id")) for e in entries]
        rows.append(Row(area, "server", OK, f"{llm.base_url} serves {', '.join(ids) or '(nothing listed)'}"))
        served = llm.served_model()
        if llm.model in ids or f"{llm.model}:latest" in ids:
            ident = llm.cache_tag or served
            rows.append(Row(area, "model", OK, f"{llm.model}" + (f" = {ident}" if ident else "")
                            + (" (cache_tag)" if llm.cache_tag else ""),
                            "" if ident or llm.cache_tag else
                            "server names no checkpoint behind the alias: set cache_tag (env CALLGUARD_LLM_TAG) "
                            "so a model swap does not reuse cached LLM results"))
        else:
            rows.append(Row(area, "model", WARN, f"{llm.model!r} not among the served ids {ids}",
                            "serve it under that name (vLLM --served-model-name, llama.cpp -a) or set "
                            f"llms.{name}.model; single-model llama.cpp servers may answer anyway"))
    elif kind == "fake":
        rows.append(Row(area, "server", OK, f"fake LLM ({llm.model_id}): offline cue heuristic, no server"))
    elif kind == "llama_cpp":
        path = Path(getattr(llm, "model_path", ""))
        ok = path.is_file()
        rows.append(Row(area, "model file", OK if ok else FAIL, _rel(path),
                        "" if ok else "download the GGUF or fix llms.<name>.model_path"))
        has = find_spec("llama_cpp") is not None
        rows.append(Row(area, "llama_cpp", OK if has else FAIL, "installed" if has else "not installed",
                        "" if has else "uv sync --extra llm-local"))
        return rows + [Row(area, "chat", SKIP, "in-process model: probing would load the weights")]
    else:
        return rows + [Row(area, "plugin", OK, f"{kind} built; not probed (may load weights in-process)")]
    return rows + _llm_probes(area, llm)


def _llm_probes(area: str, llm: Any) -> list[Row]:
    rows: list[Row] = []
    t0 = time.time()
    try:
        out = llm.chat([{"role": "user", "content": "Antworte nur mit: ja"}], max_tokens=1)
        rows.append(Row(area, "chat", OK, f"1-token answer {(out or [''])[0][:40]!r} in {time.time() - t0:.1f}s"))
    except Exception as e:
        return rows + [Row(area, "chat", FAIL, _err(e), "check the model name and the server log"),
                       Row(area, "json", SKIP, "chat failed"), Row(area, "logprobs", SKIP, "chat failed")]

    try:
        raw = llm.chat([{"role": "user", "content": 'Antworte nur mit diesem JSON: {"ok": true}'}],
                       max_tokens=32, json_schema=JSON_SCHEMA)
        obj = parse_json((raw or [""])[0])
        configured, active = getattr(llm, "json_mode", None), getattr(llm, "_active_json_mode", None)
        if not isinstance(obj, dict) or not isinstance(obj.get("ok"), bool):
            rows.append(Row(area, "json", FAIL, f"no valid JSON object: {str(raw)[:120]!r}",
                            "the LLM checks need JSON: try another json_mode or a stronger model"))
        elif configured and active and active != configured:
            rows.append(Row(area, "json", WARN, f"server rejected json_mode={configured}; schema now goes "
                                                f"into the prompt (json_mode={active})",
                            "json_schema: vLLM / llama-server; json_object_schema: llama-cpp-python"))
        else:
            rows.append(Row(area, "json", OK, f"constrained JSON works (json_mode={configured or 'n/a'})"))
    except Exception as e:
        rows.append(Row(area, "json", FAIL, _err(e), "the LLM checks need JSON output"))

    try:
        probs = llm.choice_probs([{"role": "user", "content": "Antworte mit einer Ziffer: Wie viel ist 2+1?"}],
                                 ["1", "2", "3", "4", "5"])
        if probs:
            top = max(probs, key=probs.get)
            rows.append(Row(area, "logprobs", OK, f"top_logprobs available (P({top})={probs[top]:.2f})"))
        else:
            rows.append(Row(area, "logprobs", WARN, "no logprobs from this server",
                            "G-Eval falls back to sampling (slower, coarser scores); vLLM returns them"))
    except Exception as e:
        rows.append(Row(area, "logprobs", WARN, _err(e), "G-Eval falls back to sampling"))
    return rows


# --------------------------------------------------------------------------------------------
# ASR (+ CUDA)
# --------------------------------------------------------------------------------------------


def _asr(cfg: AppConfig, ctx: Context) -> list[Row]:
    spec = dict(cfg.asr)
    kind = str(spec.get("type", ""))
    if kind == "remote":
        return _remote_asr(spec, ctx)
    rows: list[Row] = []
    if kind == "faster_whisper":
        has = find_spec("faster_whisper") is not None
        rows.append(Row("asr", "faster_whisper", OK if has else FAIL, "installed" if has else "not installed",
                        "" if has else "uv sync --extra asr"))
        rows.append(_ct2_dir(str(spec.get("model", ""))))
        device = str(spec.get("device", "cpu"))
        if device in ("cuda", "auto"):
            rows += _cuda(str(spec.get("compute_type", "default")), required=device == "cuda")
    elif kind == "hf_whisper":
        missing = [m for m in ("torch", "transformers") if find_spec(m) is None]
        rows.append(Row("asr", "hf_whisper", FAIL if missing else OK,
                        f"missing: {', '.join(missing)}" if missing else "torch + transformers installed",
                        "uv pip install transformers torch accelerate" if missing else ""))
    elif kind == "reference":
        scripts = ctx.data_dir / "Transkript"
        ok = scripts.is_dir()
        rows.append(Row("asr", "reference", OK if ok else FAIL,
                        f"oracle: reads the case scripts in {_rel(scripts)} (never for the submission)",
                        "" if ok else "clone the case data (scripts/remote/setup_gpu_host.sh does)"))
    try:
        asr = registry.create("asr", spec, ctx=ctx)  # cheap: models load on first transcribe
        rows.append(Row("asr", "plugin", OK, f"{kind} {asr.cache_params().get('model', '')}".strip()))
    except Exception as e:
        rows.append(Row("asr", "plugin", FAIL, _err(e), "fix the asr block of the profile"))
    return rows


def _ct2_dir(model: str) -> Row:
    from callguard.asr import resolve_model
    from callguard.asr.faster_whisper import check_ct2_dir

    try:
        path, is_local = resolve_model(model)
        if not is_local:
            return Row("asr", "model", WARN, f"{model}: Hugging Face id, downloaded on first use",
                       "prefer a local CTranslate2 dir (scripts/download_models.sh)")
        check_ct2_dir(Path(path))
    except Exception as e:
        return Row("asr", "model", FAIL, _err(e), "scripts/download_models.sh local (or gpu)")
    return Row("asr", "model", OK, f"{_rel(path)}: model.bin + tokenizer.json")


def _cuda(compute_type: str, *, required: bool) -> list[Row]:
    bad = FAIL if required else WARN
    try:
        import ctranslate2
    except ImportError as e:
        return [Row("asr", "cuda", bad, _err(e), "uv sync --extra asr")]
    n = ctranslate2.get_cuda_device_count()
    if n < 1:
        return [Row("asr", "cuda", bad, f"CTranslate2 {ctranslate2.__version__} sees no CUDA device",
                    "nvidia-smi must work; WSL2: install only the Windows NVIDIA driver; or asr.device=cpu")]
    rows = [Row("asr", "cuda", OK, f"CTranslate2 {ctranslate2.__version__}: {n} CUDA device(s)")]
    types = sorted(ctranslate2.get_supported_compute_types("cuda"))
    ok = compute_type in types or compute_type in ("default", "auto")
    rows.append(Row("asr", "compute_type", OK if ok else FAIL, f"{compute_type} (GPU supports {', '.join(types)})",
                    "" if ok else "pick one of the supported types"))
    rows.append(_shared_lib("cublas", ["cublas64_12.dll"] if sys.platform == "win32" else ["libcublas.so.12"],
                            FAIL))
    rows.append(_shared_lib("cudnn", ["cudnn64_9.dll"] if sys.platform == "win32" else ["libcudnn.so.9"], WARN))
    return rows


def _shared_lib(item: str, names: list[str], missing_status: str) -> Row:
    """Loading the library is what CTranslate2 does on the first GPU call; failing here is the classic
    'Library libcublas.so.12 is not found' at transcription time."""
    errors = []
    for name in names:
        try:
            ctypes.CDLL(name)
            return Row("asr", item, OK, f"{name} loads")
        except OSError as e:
            errors.append(_err(e))
    note = " (CTranslate2 >= 4.7 may not need it)" if item == "cudnn" else ""
    return Row("asr", item, missing_status, f"{', '.join(names)} not loadable{note}", CUDA_LIB_HINT)


def _remote_asr(spec: dict[str, Any], ctx: Context) -> list[Row]:
    try:
        asr = registry.create("asr", spec, ctx=ctx)
    except Exception as e:
        return [Row("asr", "plugin", FAIL, _err(e), "fix the asr block (url, model_tag, timeout, token)")]
    try:
        h = asr.health()
    except Exception as e:  # RemoteASRError messages carry their own hint
        return [Row("asr", "server", FAIL, _err(e), "" if "serve_models.sh" in str(e) else SERVE_HINT)]
    remote = h.get("asr") or {}
    setup = " ".join(str(remote.get(k)) for k in ("type", "model", "device", "compute_type") if remote.get(k))
    rows = [Row("asr", "server", OK, f"{asr.url}: {setup or 'ASR'} (profile {h.get('config')}, "
                                     f"busy {h.get('busy')}, served {h.get('served')})")]
    served = h.get("model_tag")
    if asr.model_tag and served != asr.model_tag:
        rows.append(Row("asr", "model_tag", FAIL, f"server runs {served!r}, profile expects {asr.model_tag!r}",
                        "align asr.model_tag with the server (asr_server --model-tag / its profile)"))
    else:
        rows.append(Row("asr", "model_tag", OK, f"{served}" + ("" if asr.model_tag else " (adopted from server)")))
    return rows


# --------------------------------------------------------------------------------------------
# diarization, checks, data, sinks
# --------------------------------------------------------------------------------------------


def _diarizer(cfg: AppConfig, ctx: Context) -> list[Row]:
    spec = dict(cfg.diarizer)
    kind = str(spec.get("type", "none"))
    rows: list[Row] = []
    if kind == "sherpa_onnx":
        from callguard.diarization import sherpa

        has = find_spec("sherpa_onnx") is not None
        rows.append(Row("diarizer", "sherpa_onnx", OK if has else FAIL, "installed" if has else "not installed",
                        "" if has else "uv sync --extra diarize"))
        for key, default in (("segmentation_model", sherpa.DEFAULT_SEGMENTATION),
                             ("embedding_model", sherpa.DEFAULT_EMBEDDING)):
            path = _root_path(str(spec.get(key, default)))
            ok = path.is_file()
            rows.append(Row("diarizer", key, OK if ok else FAIL, _rel(path),
                            "" if ok else "scripts/download_models.sh local"))
        if spec.get("roles", "llm") == "llm":
            llm = str(spec.get("llm", "default"))
            ok = llm in cfg.llms
            rows.append(Row("diarizer", "roles", OK if ok else FAIL, f"advisor/customer by LLM {llm!r}",
                            "" if ok else f"configure llms.{llm} or set diarizer.roles=first_speaker_advisor"))
    try:
        registry.create("diarizer", spec, ctx=ctx)
        rows.append(Row("diarizer", "plugin", OK, kind))
    except Exception as e:
        rows.append(Row("diarizer", "plugin", FAIL, _err(e), "fix the diarizer block of the profile"))
    return rows


def _checks(cfg: AppConfig, ctx: Context) -> list[Row]:
    rows: list[Row] = []
    for spec in cfg.checks:
        name = str(spec.get("name") or spec.get("type"))
        try:
            check = registry.create("check", spec, ctx=ctx)
        except Exception as e:
            rows.append(Row("checks", name, FAIL, _err(e), "fix this entry of `checks`"))
            continue
        llm = spec.get("llm")
        if llm is not None and llm not in cfg.llms:
            rows.append(Row("checks", name, FAIL, f"uses LLM {llm!r}, configured: {list(cfg.llms)}",
                            f"configure llms.{llm}"))
            continue
        state = "" if check.enabled else " (disabled)"
        rows.append(Row("checks", name, OK, f"{spec.get('type')}, weight {check.weight}{state}"
                        + (f", llm {llm}" if llm else "")))
    try:
        registry.create("fusion", cfg.fusion, ctx=ctx)
        rows.append(Row("checks", "fusion", OK, f"{cfg.fusion.get('type')}, threshold {cfg.fusion.get('threshold')}"))
    except Exception as e:
        rows.append(Row("checks", "fusion", FAIL, _err(e), "fix the fusion block"))
    return rows or [Row("checks", "-", WARN, "no checks configured")]


def _data(cfg: AppConfig, ctx: Context) -> list[Row]:
    from callguard.data import load_calls

    rows: list[Row] = []
    data_dir = ctx.data_dir
    if (data_dir / "Audio").is_dir():
        calls = load_calls(data_dir)
        labelled = sum(1 for c in calls if c.expected)
        rows.append(Row("data", "data_dir", OK if calls else WARN,
                        f"{_rel(data_dir)}: {len(calls)} calls, {labelled} with expected labels"))
    else:
        rows.append(Row("data", "data_dir", WARN, f"{_rel(data_dir)}/Audio missing (batch/eval need it)",
                        "git clone --depth 1 https://github.com/Outcept/inventx-case-study data_upstream/"
                        "inventx-case-study"))
    for key in ("keywords", "criteria"):
        path = ctx.path(key)
        rows.append(Row("data", key, OK if path.is_file() else FAIL, _rel(path),
                        "" if path.is_file() else f"restore {key} (paths.{key})"))
    try:
        fams = ctx.families()
        rows.append(Row("data", "families", OK if fams else FAIL, ", ".join(f.id for f in fams) or "none enabled"))
    except Exception as e:
        rows.append(Row("data", "families", FAIL, _err(e), "keywords.json / criteria.yaml do not parse"))
    return rows


def _sinks(cfg: AppConfig, ctx: Context) -> list[Row]:
    rows: list[Row] = []
    for spec in cfg.sinks:
        kind = str(spec.get("type"))
        if not spec.get("enabled", True):
            rows.append(Row("sinks", kind, SKIP, "disabled"))
            continue
        try:
            registry.create("sink", spec, ctx=ctx)
        except Exception as e:
            rows.append(Row("sinks", kind, FAIL, _err(e), "fix this entry of `sinks`"))
            continue
        if kind == "outcept_trigger":
            rows.append(_reachable("sinks", kind, str(spec.get("url", "http://localhost:8080/triggers"))))
        elif kind == "json_dir":
            rows.append(Row("sinks", kind, OK, f"results in {_rel(ctx.runs_dir)}"))
        else:
            rows.append(Row("sinks", kind, OK, "built"))
    return rows or [Row("sinks", "-", WARN, "no sinks: results are not written anywhere")]


def _reachable(area: str, item: str, url: str) -> Row:
    """Any HTTP answer from the origin counts (nothing is POSTed: no stray triggers)."""
    u = urlparse(url)
    origin = f"{u.scheme}://{u.netloc}/"
    try:
        r = httpx.get(origin, timeout=httpx.Timeout(3.0))
    except httpx.HTTPError as e:
        return Row(area, item, FAIL, f"{origin}: {_err(e)}",
                   "start the case's trigger server (docker compose up in data_upstream/inventx-case-study) "
                   "or set the sink's enabled: false")
    return Row(area, item, OK, f"{url} reachable (GET / -> HTTP {r.status_code})")
