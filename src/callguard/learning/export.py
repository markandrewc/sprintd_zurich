"""``callguard learn export``: officer labels -> learning datasets (no model is trained here).

Written to ``<out>/`` (default ``runs/<profile>/learning/export/``)::

    manifest.json                  counts per file and use, hygiene result, label sources, versions seen
    calls.jsonl                    (b) one row per labelled call: officer label, system label + score,
                                       per-family scores: input for threshold / calibration fits
    passages.jsonl                 (c) trifft zu / trifft nicht zu per shown passage: localisation
    facts.jsonl                    (a) every per-fact label as a flat row (all uses, incl. evaluation)
    kev_noul.<use>.jsonl           (a) Kev training requests, one per call ("state" = transcript):
                                       {"state", "questions": {qid: {"type": "noul", "instructions",
                                       "label": true|false}}, "meta"}; "unclear" answers left out
    kev_choice.<use>.jsonl         (a) the same as a Kev choice over yes / no / unknown ("label": name)
    qwen_sft.<use>.jsonl           (a) one chat per fact, exactly the facts check's prompt
                                       (fact_prompts.fact_messages) + the officer's one-word answer

``<use>`` is ``train`` (may be trained on), ``shadow_test`` (held back for the shadow evaluation of a
retrained model) or ``eval_dev`` (case dev calls: evaluation only, e.g. a zero-shot baseline). Case
holdout calls appear in ``calls.jsonl`` / ``facts.jsonl`` marked ``eval_case_holdout`` and nowhere else;
simulated demo labels are never in a model file. :func:`callguard.learning.hygiene.enforce` re-checks
every model file before it is written and the export fails rather than leak.

The Kev instruction is ``"Topic: <family label> [<family id>]\\n<question>"``, the string
``callguard.llm.kev.KevLLM`` sends at serving time (``include_topic``), and the state is the transcript as
the facts check renders it, so training and serving see the same text.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from callguard import audit
from callguard.checks import fact_prompts as fp
from callguard.checks import prompts
from callguard.learning import hygiene as hy
from callguard.learning.records import FactLabel, LabelSet
from callguard.splits import Splits
from callguard.types import CallResult

KEV_CHOICE = {"yes": "the call shows it",
              "no": "the call shows it is not so, or it does not happen in the call",
              "unknown": "the call raises the matter but does not let you decide"}
_KEV_ANSWER = {"yes": "yes", "no": "no", "unclear": "unknown"}
FILE_USE = {hy.TRAIN: "train", hy.SHADOW: "shadow_test", hy.EVAL_DEV: "eval_dev"}
DEFAULT_MAX_CHARS = 24000


def _check_params(result: CallResult, check: str) -> dict[str, Any]:
    prov = (result.meta.get("provenance") or {}).get("checks") or {}
    return dict((prov.get(check) or {}).get("params") or {})


def _view_of(result: CallResult, check: str) -> str | None:
    prov = (result.meta.get("provenance") or {}).get("checks") or {}
    return (prov.get(check) or {}).get("view")


def rendered_state(result: CallResult, check: str) -> tuple[str, str | None]:
    """(transcript as the facts check rendered it, transcript language)."""
    params = _check_params(result, check)
    t = result.view(_view_of(result, check))
    if params.get("roles") is False:
        t = t.model_copy(update={"segments": [s.model_copy(update={"role": "unknown"}) for s in t.segments]})
    text, _ = prompts.render_transcript(t, int(params.get("max_transcript_chars") or DEFAULT_MAX_CHARS))
    return text, t.lang


def family_label(result: CallResult, fid: str) -> str:
    fam = result.decision.families.get(fid) if result.decision.families else None
    return (fam.label if fam and fam.label else fid)


def kev_instructions(result: CallResult, f: FactLabel) -> str:
    return f"Topic: {family_label(result, f.family)} [{f.family}]\n{' '.join(str(f.question or f.fact_label).split())}"


def _meta(f: FactLabel) -> dict[str, Any]:
    return {"call_id": f.call_id, "family": f.family, "fact": f.fact, "use": f.use, "source": f.source,
            "user": f.user, "ts": f.ts, "model_value": f.model_value, "policy_table_hash": f.policy_table_hash}


def kev_records(facts: list[FactLabel], results: Mapping[str, CallResult], kind: str) -> list[dict[str, Any]]:
    """One Kev request per call with every labelled fact of the call as a question (Kev answers many
    questions about one state in a single pass). ``kind``: ``noul`` (yes/no, unclear left out) or ``choice``."""
    by_call: dict[str, list[FactLabel]] = {}
    for f in facts:
        if kind == "noul" and f.answer == "unclear":
            continue
        by_call.setdefault(f.call_id, []).append(f)
    out = []
    for cid, fs in sorted(by_call.items()):
        r = results.get(cid)
        if r is None:
            continue
        state, _ = rendered_state(r, fs[0].check)
        qs: dict[str, Any] = {}
        for f in fs:
            q: dict[str, Any] = {"type": kind, "instructions": kev_instructions(r, f)}
            if kind == "noul":
                q["label"] = f.answer == "yes"
            else:
                q.update(criteria=KEV_CHOICE, label=_KEV_ANSWER[f.answer])
            qs[f"{f.family}.{f.fact}"] = q
        uses = {f.use for f in fs}
        assert len(uses) == 1, f"{cid}: facts of one call with different uses {uses}"
        out.append({"state": state, "questions": qs,
                    "meta": {"call_id": cid, "use": fs[0].use, "source": fs[0].source,
                             "facts": [_meta(f) for f in fs]}})
    return out


def qwen_records(facts: list[FactLabel], results: Mapping[str, CallResult]) -> list[dict[str, Any]]:
    """One supervised chat per fact: the facts check's own prompt + the officer's answer as one word."""
    out = []
    states: dict[tuple[str, str], tuple[str, str | None]] = {}
    for f in facts:
        r = results.get(f.call_id)
        if r is None:
            continue
        key = (f.call_id, f.check)
        if key not in states:
            states[key] = rendered_state(r, f.check)
        state, lang = states[key]
        msgs = fp.fact_messages(state, family_label(r, f.family), f.family, str(f.question or f.fact_label),
                                transcript_lang=lang)
        out.append({"messages": [*msgs, {"role": "assistant", "content": _KEV_ANSWER[f.answer]}],
                    "meta": {**_meta(f), "prompt_version": fp.PROMPT_VERSION}})
    return out


def call_rows(labels: LabelSet, results: Mapping[str, CallResult]) -> list[dict[str, Any]]:
    rows = []
    for cid, c in sorted(labels.calls.items()):
        r = results.get(cid)
        fams = {fid: round(f.score, 4) for fid, f in (r.decision.families or {}).items()} if r else {}
        rows.append({**c.row(), "score": round(r.decision.score, 4) if r else None, "family_scores": fams})
    return rows


def build(labels: LabelSet, results: Mapping[str, CallResult], splits: Splits | None) -> dict[str, list[dict[str, Any]]]:
    """Every file's records (name -> rows), hygiene-checked. Raises HygieneError on any leak."""
    out: dict[str, list[dict[str, Any]]] = {
        "calls.jsonl": call_rows(labels, results),
        "passages.jsonl": [p.row() for p in labels.passages],
        "facts.jsonl": [f.row() for f in labels.facts],
    }
    for use, suffix in FILE_USE.items():
        fs = [f for f in labels.facts if f.use == use]
        if not fs:
            continue
        for name, recs in ((f"kev_noul.{suffix}.jsonl", kev_records(fs, results, "noul")),
                           (f"kev_choice.{suffix}.jsonl", kev_records(fs, results, "choice")),
                           (f"qwen_sft.{suffix}.jsonl", qwen_records(fs, results))):
            flat = [{"call_id": m["call_id"], "use": m["use"], "source": m["source"]}
                    for m in (r["meta"] for r in recs)]
            hy.enforce(flat, splits, training=use == hy.TRAIN)
            if any(m["use"] != use for m in flat):
                raise hy.HygieneError(f"{name}: record of another use")
            if recs:
                out[name] = recs
    hy.enforce([{"call_id": c["call_id"], "use": c["use"], "source": c["source"]} for c in out["calls.jsonl"]],
               splits, training=False)
    return out


def manifest(built: Mapping[str, list[dict[str, Any]]], labels: LabelSet, splits: Splits | None) -> dict[str, Any]:
    facts = labels.facts
    return {
        "created_at": audit.now_iso(), "store": labels.store,
        "files": {name: len(rows) for name, rows in built.items()},
        "uses": {"calls": dict(Counter(c.use for c in labels.calls.values())),
                 "facts": dict(Counter(f.use for f in facts)),
                 "passages": dict(Counter(p.use for p in labels.passages))},
        "trainable_fact_labels": sum(1 for f in facts if f.use in hy.TRAINABLE),
        "fact_sources": dict(Counter(f.source for f in facts)),
        "answers": dict(Counter(f.answer for f in facts)),
        "reason_codes": dict(Counter(r.get("code") for c in labels.calls.values() for r in c.reasons)),
        "officer_agrees": dict(Counter(str(c.agrees).lower() for c in labels.calls.values() if c.agrees is not None)),
        "policy_table_hashes": sorted({f.policy_table_hash for f in facts if f.policy_table_hash}),
        "config_hashes": sorted({c.provenance.get("config_hash") for c in labels.calls.values()
                                 if c.provenance.get("config_hash")}),
        "split_file": str(splits.path) if splits is not None and splits.path else None,
        "hygiene": "ok (case dev/holdout calls evaluation-only, demo labels never trainable, twin units on one side)",
        "formats": {"kev_noul": "Kev /v1/systemone request + label (bool) per noul question",
                    "kev_choice": "Kev choice over yes/no/unknown + label (option name)",
                    "qwen_sft": "chat messages (fact_prompts.fact_messages) + assistant answer"},
    }


def write(out_dir: str | Path, built: Mapping[str, list[dict[str, Any]]], man: Mapping[str, Any]) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jsonl"):  # a re-export replaces the previous one completely
        old.unlink()
    for name, rows in built.items():
        with (out / name).open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    (out / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=2, default=str))
    return out
