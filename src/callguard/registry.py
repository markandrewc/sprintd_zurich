"""Plugin registry: every swappable component is looked up here by ``kind`` + ``type`` name.

Three ways to make a plugin available, in lookup order:

1. ``@register("check", "my_check")`` on a class in any module you import.
2. The ``BUILTINS`` table below (lazy: the module is only imported when the plugin is used,
   so e.g. faster-whisper is never imported when you run the reference ASR).
3. A dotted import path as the type: ``type: "my_team.checks.sentiment:SentimentCheck"``.
   Drop a file anywhere on PYTHONPATH and point the YAML at it - no registry edit needed.

Kinds: asr, diarizer, check, fusion, llm, sink, translator, preprocess.
"""

from __future__ import annotations

import importlib
from typing import Any

KINDS = ("asr", "diarizer", "check", "fusion", "llm", "sink", "translator", "preprocess")

_REGISTERED: dict[str, dict[str, type]] = {k: {} for k in KINDS}

# kind -> type name -> "module:Class". Keep this table in sync when adding built-in plugins.
BUILTINS: dict[str, dict[str, str]] = {
    "asr": {
        "faster_whisper": "callguard.asr.faster_whisper:FasterWhisperASR",
        "hf_whisper": "callguard.asr.hf_whisper:HFWhisperASR",
        "reference": "callguard.asr.reference:ReferenceASR",
        "remote": "callguard.asr.remote:RemoteASR",
    },
    "diarizer": {
        "none": "callguard.diarization.none:NoDiarizer",
        "sherpa_onnx": "callguard.diarization.sherpa:SherpaDiarizer",
    },
    "check": {
        "keywords": "callguard.checks.keywords:KeywordCheck",
        "patterns": "callguard.checks.patterns:PatternCheck",
        "llm_judge": "callguard.checks.llm_judge:LLMJudgeCheck",
        "geval": "callguard.checks.geval:GEvalCheck",
        "geval_cot": "callguard.checks.geval_cot:GEvalCoTCheck",
        "entities": "callguard.checks.entities:EntityCheck",
        "facts": "callguard.checks.facts:FactSheetCheck",
        "keyword_context": "callguard.checks.keyword_context:KeywordContextCheck",
        "anchored": "callguard.checks.keyword_context:AnchoredProbeCheck",
        "semantic_windows": "callguard.checks.semantic:SemanticWindowCheck",
        "quote_judge": "callguard.checks.quote_judge:QuoteJudgeCheck",
    },
    "fusion": {
        "weighted": "callguard.fusion.weighted:WeightedFusion",
        "calibrated": "callguard.fusion.calibrated:CalibratedFusion",
        "learned": "callguard.fusion.learned:LearnedFusion",
        "hybrid": "callguard.fusion.hybrid:HybridFusion",
    },
    "llm": {
        "openai_compat": "callguard.llm.openai_compat:OpenAICompatLLM",
        "llama_cpp": "callguard.llm.llama_cpp:LlamaCppLLM",
        "fake": "callguard.llm.fake:FakeLLM",
    },
    "sink": {
        "json_dir": "callguard.sinks.json_dir:JsonDirSink",
        "outcept_trigger": "callguard.sinks.outcept:OutceptTriggerSink",
        "notify": "callguard.sinks.notify:NotifySink",
        "audit": "callguard.audit:AuditSink",
    },
    "translator": {
        "llm_translate": "callguard.translate.llm:LLMTranslator",
        "hf_mt": "callguard.translate.hf_mt:HFTranslator",
        "identity": "callguard.translate.identity:IdentityTranslator",
        "llm_correct": "callguard.translate.correct:LLMCorrector",
    },
    "preprocess": {
        "none": "callguard.preprocess:NoPreprocessor",
        "denoise_sherpa": "callguard.preprocess.denoise:SherpaDenoiser",
    },
}


def register(kind: str, name: str):
    """Class decorator: ``@register("check", "sentiment")``."""
    if kind not in KINDS:
        raise ValueError(f"unknown plugin kind {kind!r}; expected one of {KINDS}")

    def deco(cls: type) -> type:
        _REGISTERED[kind][name] = cls
        cls.plugin_kind = kind
        cls.plugin_type = name
        return cls

    return deco


def _import(path: str) -> type:
    module, _, attr = path.partition(":")
    if not attr:
        raise ValueError(f"plugin path {path!r} must look like 'package.module:ClassName'")
    return getattr(importlib.import_module(module), attr)


def resolve(kind: str, type_name: str) -> type:
    if kind not in KINDS:
        raise ValueError(f"unknown plugin kind {kind!r}; expected one of {KINDS}")
    if type_name in _REGISTERED[kind]:
        return _REGISTERED[kind][type_name]
    if type_name in BUILTINS[kind]:
        cls = _import(BUILTINS[kind][type_name])
        _REGISTERED[kind].setdefault(type_name, cls)
        return cls
    if ":" in type_name:
        return _import(type_name)
    known = sorted(set(_REGISTERED[kind]) | set(BUILTINS[kind]))
    raise KeyError(f"no {kind} plugin named {type_name!r}. Known: {known} (or use 'module:Class')")


def create(kind: str, spec: dict[str, Any] | str, **deps: Any) -> Any:
    """Instantiate a plugin from a config spec.

    ``spec`` is ``{"type": "<name>", **params}`` (or just the type name). Params become keyword
    arguments of the plugin constructor; ``deps`` are shared resources such as ``ctx``.
    """
    if isinstance(spec, str):
        spec = {"type": spec}
    spec = dict(spec)
    type_name = spec.pop("type")
    # Every check reads one transcript view (config ``views``). Handled here, not in each check's
    # constructor, so it never enters cache_params(): the view's segments are in the check key anyway.
    view = spec.pop("view", None) if kind == "check" else None
    # Same for the audio pre-processor of an ASR (``asr.preprocess``): applied by the pipeline, keyed
    # separately and only when set, so ASR cache keys without it stay the v1 keys.
    preprocess = spec.pop("preprocess", None) if kind == "asr" else None
    cls = resolve(kind, type_name)
    obj = cls(**deps, **spec)
    obj.plugin_kind = kind
    obj.plugin_type = type_name
    if kind == "check":
        obj.view = view
    if kind == "asr":
        obj.preprocess = {"type": preprocess} if isinstance(preprocess, str) else preprocess
    return obj


def available() -> dict[str, list[str]]:
    return {k: sorted(set(_REGISTERED[k]) | set(BUILTINS[k])) for k in KINDS}
