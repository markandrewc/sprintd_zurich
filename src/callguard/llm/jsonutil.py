"""Tolerant JSON handling for LLM output.

Even with constrained decoding, small local models wrap JSON in prose or code fences, add trailing
commas, write ``"confidence": 85`` for a 0..1 field, ``"Present"`` for ``"present"``, or stop
mid-object when ``max_tokens`` runs out. Checks should not each reinvent that cleanup, and they
must never mistake a half-parsed answer for a verdict: ``validate_minimal`` coerces obvious
formatting slips but never invents a missing value.
"""

from __future__ import annotations

import ast
import json
import logging
import math
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from callguard.plugins import LLM

log = logging.getLogger("callguard.llm")

_FENCE = re.compile(r"```[A-Za-z0-9_-]*[ \t]*\n?(.*?)```", re.S)
_THINK = re.compile(r"<think>.*?</think>", re.S)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")
_TRUE = {"true", "yes", "ja", "1", "y", "wahr"}
_FALSE = {"false", "no", "nein", "0", "n", "falsch"}


def strip_reasoning(text: str | None) -> str:
    """Drop ``<think>`` blocks of reasoning models (Qwen3, DeepSeek-R1): they often contain draft
    JSON or digits that must not be mistaken for the answer."""
    text = _THINK.sub("", text or "")
    if "</think>" in text:  # chat template opened the block inside the prompt
        text = text.rsplit("</think>", 1)[1]
    if "<think>" in text:  # max_tokens hit while still thinking: no answer at all
        text = text.split("<think>", 1)[0]
    return text.strip()


def _snippet(text: str | None, n: int = 200) -> str:
    text = (text or "").strip().replace("\n", " ")
    return repr(text if len(text) <= n else text[:n] + "...")


def _scan(s: str, start: int) -> tuple[int | None, list[str], bool]:
    """From the ``{`` at ``start``: index of its matching close, else the open-bracket stack and
    whether the text ended inside a string (truncated output)."""
    stack: list[str] = []
    in_str = esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            stack.pop()
            if not stack:
                return i, [], False
    return None, stack, in_str


def _loads_dict(chunk: str) -> dict[str, Any] | None:
    for attempt in (chunk, _TRAILING_COMMA.sub(r"\1", chunk)):
        try:
            obj = json.loads(attempt)
        except ValueError:
            continue
        return obj if isinstance(obj, dict) else None
    try:  # {'verdict': 'present'} - Python literals from models that ignore the JSON instruction
        obj = ast.literal_eval(chunk)
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        return None
    return obj if isinstance(obj, dict) else None


def _close_truncated(chunk: str, stack: list[str], in_str: bool) -> dict[str, Any] | None:
    """Best effort for output cut off by ``max_tokens``: close the open string and brackets,
    dropping a dangling key or separator. Returns None rather than guessing harder."""
    if in_str:
        chunk += '"'
    closers = "".join("}" if b == "{" else "]" for b in reversed(stack))
    body = chunk.rstrip()
    variants = (
        body,
        re.sub(r"[,:]\s*$", "", body),  # {"a": 1,
        re.sub(r',?\s*"[^"]*"\s*:?\s*$', "", body),  # {"a": 1, "rea   /   {"a": 1, "b":
        re.sub(r',?\s*"[^"]*"\s*:\s*[^\s,{}\[\]"]+$', "", body),  # {"a": 1, "b": tru
    )
    for variant in variants:
        obj = _loads_dict(variant + closers)
        if obj is not None:
            return obj
    return None


def _first_object(text: str) -> dict[str, Any] | None:
    obj = _loads_dict(text.strip())
    if obj is not None:
        return obj
    pos = text.find("{")
    while pos != -1:
        end, stack, in_str = _scan(text, pos)
        if end is None:  # truncated output, or a stray "{" in prose before the real object
            obj = _close_truncated(text[pos:], stack, in_str)
        else:
            obj = _loads_dict(text[pos:end + 1])
        if obj is not None:
            return obj
        pos = text.find("{", pos + 1)
    return None


def parse_json(text: str | None) -> dict[str, Any]:
    """First JSON object in an LLM answer. Raises ValueError (with a snippet of the output, for the
    check's meta) when there is none."""
    if not text or not text.strip():
        raise ValueError("empty LLM output, expected a JSON object")
    body = strip_reasoning(text)
    for cand in [*(m.group(1) for m in _FENCE.finditer(body)), body]:
        obj = _first_object(cand)
        if obj is not None:
            return obj
    raise ValueError(f"no JSON object found in LLM output: {_snippet(text)}")


# ---------------------------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------------------------


def deref_schema(sch: Any, root: dict) -> dict:
    """Resolve local ``$ref`` (pydantic's ``model_json_schema`` emits ``#/$defs/...``)."""
    seen = 0
    while isinstance(sch, dict) and "$ref" in sch and seen < 32:
        ref = sch["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise ValueError(f"unsupported $ref {ref!r} (only local refs)")
        target: Any = root
        try:
            for part in ref[2:].split("/"):
                target = target[part.replace("~1", "/").replace("~0", "~")]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"cannot resolve $ref {ref!r} against the root schema") from e
        extra = {k: v for k, v in sch.items() if k != "$ref"}
        sch = {**target, **extra}
        seen += 1
    if isinstance(sch, dict) and isinstance(sch.get("allOf"), list) and len(sch["allOf"]) == 1:
        extra = {k: v for k, v in sch.items() if k != "allOf"}
        sch = {**deref_schema(sch["allOf"][0], root), **extra}
    return sch if isinstance(sch, dict) else {}


def _norm_token(s: str) -> str:
    return re.sub(r"[\s_-]+", "_", s.strip().strip(".,;:!\"'`").casefold())


def _match_enum(value: Any, enum: list, path: str) -> Any:
    if value in enum:
        return value
    if isinstance(value, str):
        norm = _norm_token(value)
        for e in enum:
            if isinstance(e, str) and _norm_token(e) == norm:
                return e
        for e in enum:  # "3" for an integer enum
            if not isinstance(e, (str, bool)) and isinstance(e, (int, float)):
                try:
                    if float(value.strip()) == e:
                        return e
                except ValueError:
                    break
    raise ValueError(f"{path}: {value!r} not one of {enum}")


def _coerce_number(value: Any, sch: dict, integer: bool, path: str) -> int | float:
    percent = False
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{path}: expected a number, got {value!r}")
    if isinstance(value, str):
        s = value.strip()
        percent = s.endswith("%")
        s = s.rstrip("%").strip().replace(",", ".")  # German decimal comma
        try:
            num = float(s)
        except ValueError as e:
            raise ValueError(f"{path}: expected a number, got {value!r}") from e
    elif isinstance(value, (int, float)):
        num = float(value)
    else:
        raise ValueError(f"{path}: expected a number, got {value!r}")
    if not math.isfinite(num):
        raise ValueError(f"{path}: expected a finite number, got {value!r}")
    lo = sch.get("minimum", sch.get("exclusiveMinimum"))
    hi = sch.get("maximum", sch.get("exclusiveMaximum"))
    if lo == 0 and hi == 1 and (percent or 1 < num <= 100):
        num /= 100.0  # "confidence": 85 / "85%" for a 0..1 field
    if lo is not None:
        num = max(float(lo), num)
    if hi is not None:
        num = min(float(hi), num)
    return int(round(num)) if integer else num


def _coerce_bool(value: Any, path: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        s = _norm_token(value)
        if s in _TRUE:
            return True
        if s in _FALSE:
            return False
    raise ValueError(f"{path}: expected a boolean, got {value!r}")


def _validate(value: Any, sch: Any, root: dict, path: str) -> Any:
    sch = deref_schema(sch, root)
    if not sch:
        return value
    if "const" in sch:
        return _match_enum(value, [sch["const"]], path)
    for key in ("anyOf", "oneOf"):
        if isinstance(sch.get(key), list):
            errors = []
            for opt in sch[key]:
                try:
                    return _validate(value, opt, root, path)
                except ValueError as e:
                    errors.append(str(e))
            raise ValueError(f"{path}: {value!r} matches no allowed option ({'; '.join(errors)})")
    if "enum" in sch:
        if value is None and "null" in schema_types(sch):
            return None
        return _match_enum(value, list(sch["enum"]), path)

    types = schema_types(sch)
    if value is None:
        if "null" in types or not types:
            return None
        raise ValueError(f"{path}: value is null")
    errors = []
    for t in [t for t in types if t != "null"] or [None]:
        try:
            return _validate_type(value, t, sch, root, path)
        except ValueError as e:
            errors.append(str(e))
    raise ValueError(errors[0] if len(errors) == 1 else f"{path}: {'; '.join(errors)}")


def schema_types(sch: dict) -> list[str]:
    t = sch.get("type")
    if isinstance(t, list):
        return [str(x) for x in t]
    if isinstance(t, str):
        return [t]
    if "properties" in sch or "required" in sch or "additionalProperties" in sch:
        return ["object"]
    if "items" in sch:
        return ["array"]
    return []


def _validate_type(value: Any, t: str | None, sch: dict, root: dict, path: str) -> Any:
    if t == "object":
        if not isinstance(value, dict):
            raise ValueError(f"{path}: expected an object, got {type(value).__name__}")
        props = sch.get("properties", {}) or {}
        missing = [k for k in sch.get("required", []) if k not in value]
        if missing:
            raise ValueError(f"{path}: missing required key(s) {missing}")
        extra_sch = sch.get("additionalProperties")
        out = {}
        for k, v in value.items():
            if k in props:
                out[k] = _validate(v, props[k], root, f"{path}.{k}")
            elif isinstance(extra_sch, dict):
                out[k] = _validate(v, extra_sch, root, f"{path}.{k}")
            else:
                out[k] = v  # keep unknown keys: they may carry useful detail for meta
        return out
    if t == "array":
        if not isinstance(value, list):
            value = [value]  # "segment_ids": "S004"
        items = sch.get("items")
        out = [_validate(v, items, root, f"{path}[{i}]") for i, v in enumerate(value)] if items else list(value)
        if len(out) < int(sch.get("minItems", 0)):
            raise ValueError(f"{path}: needs at least {sch['minItems']} item(s), got {len(out)}")
        if "maxItems" in sch:
            out = out[:int(sch["maxItems"])]
        return out
    if t == "string":
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        raise ValueError(f"{path}: expected a string, got {type(value).__name__}")
    if t in ("number", "integer"):
        return _coerce_number(value, sch, t == "integer", path)
    if t == "boolean":
        return _coerce_bool(value, path)
    if t == "null":
        raise ValueError(f"{path}: expected null, got {value!r}")
    return value


def validate_minimal(obj: Any, schema: dict) -> dict[str, Any]:
    """Check ``obj`` against the parts of ``schema`` checks rely on and return a cleaned copy.

    Checked: required keys, enums (case/format-tolerant: ``"Present."`` -> ``"present"``), types.
    Coerced: numeric strings, ``"0,8"``, percent values for ``[0, 1]`` fields (``85`` -> ``0.85``),
    clamping to ``minimum``/``maximum``, a scalar where a list is expected. Nothing is filled in:
    a missing required key raises ValueError, so callers can mark the answer undetermined.
    """
    if not isinstance(schema, dict):
        raise ValueError("schema must be a JSON schema object")
    out = _validate(obj, schema, schema, "$")
    if not isinstance(out, dict):
        raise ValueError(f"$: expected a JSON object, got {type(out).__name__}")
    return out


def chat_json(llm: "LLM", messages: list[dict[str, str]], schema: dict, *, temperature: float = 0.0,
              max_tokens: int = 512, n: int = 1, repair: bool = True) -> list[dict[str, Any]]:
    """``llm.chat`` + :func:`parse_json` + :func:`validate_minimal` for ``n`` samples.

    An invalid sample gets one repair turn (its own output plus the error, temperature 0); samples
    still invalid are dropped with a warning. Raises ValueError only if no sample survives, so the
    caller can report the family as undetermined with the error in its meta.
    """
    outs = llm.chat(messages, temperature=temperature, max_tokens=max_tokens, n=n, json_schema=schema)
    results: list[dict[str, Any]] = []
    errors: list[str] = []
    for text in outs:
        try:
            results.append(validate_minimal(parse_json(text), schema))
            continue
        except ValueError as e:
            err = str(e)
        if repair:
            fix = [*messages, {"role": "assistant", "content": text or ""},
                   {"role": "user", "content": (
                       f"Deine Antwort war ungültig ({err[:300]}). Antworte jetzt NUR mit einem "
                       "einzigen JSON-Objekt, das dem verlangten Schema entspricht.")}]
            try:
                fixed = llm.chat(fix, temperature=0.0, max_tokens=max_tokens, n=1, json_schema=schema)[0]
                results.append(validate_minimal(parse_json(fixed), schema))
                continue
            except (ValueError, IndexError) as e:
                err = f"{err}; after repair: {e}"
        log.warning("dropping invalid LLM JSON sample: %s", err)
        errors.append(err)
    if not results:
        raise ValueError(f"no valid JSON in {len(outs)} LLM sample(s): {errors[0] if errors else 'no output'}")
    return results
