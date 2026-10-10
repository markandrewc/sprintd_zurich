"""Officer feedback -> better threshold and keyword list (docs/design/v2_plan.md §3).

* ``runs/<profile>/feedback.jsonl``: one :class:`FeedbackItem` per line (append-only; latest wins).
* :func:`suggest`: labels derived from feedback (+ case ground truth where no feedback exists, optional),
  then the eval's threshold sweep re-runs **only the fusion** on the stored check results ->
  suggested threshold with the expected change in false alarms / misses; per-keyword precision
  ("consider disabling K05"); per-check reliability.
* :func:`apply_tuning`: writes ``config/tuning.yaml`` (``profiles.<profile>.fusion.threshold`` /
  ``review_band`` / ``weights``), which :func:`callguard.config.load_config` lays over the profile and
  provenance records by hash. Every add / apply leaves an audit event.

Small numbers warning: with tens of labelled calls a suggested threshold is a hint, not a measurement;
``suggest`` reports n and the CLI/UI say so.

Schema 2 (docs/LEARNING.md): besides the call verdicts of schema 1 (``confirmed`` / ``false_alarm`` /
``missed`` / ``should_review`` / ``not_review``) an item may be

* a call verdict ``violation`` / ``no_violation`` / ``unclear`` (Verstoss bestätigt / kein Verstoss /
  unklar -> alarm / no_alert / review),
* a passage verdict ``applies`` / ``not_applies`` (trifft zu / trifft nicht zu, ``passage_index`` plus a
  snapshot of the passage in ``passage``),
* a fact verdict ``fact`` (``check`` / ``family`` / ``fact`` + the officer's ``answer`` yes / no / unclear,
  ``model_value`` and ``agrees``),
* ``missed_family`` (übersehene Kategorie, ``family``).

Every schema-2 item carries ``provenance`` (config / policy-table / tuning hashes, model ids, ASR backend,
transcript hash, the decision shown) so a label stays interpretable after rules or models change, and a
``batch`` id (one form submission). Old lines load unchanged (``schema_version`` 1). Simulated demo
feedback lives in its own file (``feedback_demo.jsonl``, ``source: demo``) and is never mixed with the
officers' labels (``add`` / ``load`` refuse the other kind).
"""

from __future__ import annotations

import datetime as _dt
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, Field

from callguard import audit
from callguard.config import ROOT, TUNING_FUSION_KEYS, AppConfig
from callguard.types import CallResult, Label

if TYPE_CHECKING:
    from callguard.pipeline import Pipeline

FeedbackVerdict = Literal["confirmed", "false_alarm", "missed", "should_review", "not_review",
                          "violation", "no_violation", "unclear", "applies", "not_applies", "fact",
                          "missed_family"]
LEGACY_VERDICTS: tuple[str, ...] = ("confirmed", "false_alarm", "missed", "should_review", "not_review")
CALL_VERDICTS: tuple[str, ...] = ("violation", "no_violation", "unclear")
PASSAGE_VERDICTS: tuple[str, ...] = ("applies", "not_applies")
VERDICTS: tuple[str, ...] = LEGACY_VERDICTS + CALL_VERDICTS + PASSAGE_VERDICTS + ("fact", "missed_family")
VERDICT_DE = {"confirmed": "Bestätigt", "false_alarm": "Fehlalarm", "missed": "Verpasst (hätte Alarm sein müssen)",
              "should_review": "Hätte geprüft werden müssen", "not_review": "Prüfung unnötig",
              "violation": "Verstoss bestätigt", "no_violation": "Kein Verstoss", "unclear": "Unklar",
              "applies": "Trifft zu", "not_applies": "Trifft nicht zu", "fact": "Fakt beurteilt",
              "missed_family": "Übersehene Kategorie"}
# verdict -> the call label the officer says is right ("confirmed" / "applies": what they saw)
CALL_LABEL = {"violation": "alarm", "no_violation": "no_alert", "unclear": "review",
              "false_alarm": "no_alert", "missed": "alarm", "should_review": "review", "not_review": "no_alert",
              "not_applies": "no_alert", "missed_family": "alarm"}
NEGATIVE = ("false_alarm", "not_applies")
FACT_ANSWERS = ("yes", "no", "unclear")
FEEDBACK_FILE = "feedback.jsonl"
DEMO_FILE = "feedback_demo.jsonl"  # simulated feedback (demo only): never mixed with officers' labels
STORES = ("real", "demo")
DEMO_NOTE = "Demo-Feedback (simuliert aus Sollbewertung)"
FLAG = ("alarm", "review")
Target = Literal["call", "passage", "fact", "family"]


class FeedbackItem(BaseModel):
    call_id: str
    ts: str = Field(default_factory=audit.now_iso)
    user: str = Field(default_factory=audit.current_user)
    verdict: FeedbackVerdict
    family: str | None = None
    passage_index: int | None = None  # None = about the whole call
    comment: str = ""
    label_seen: Label | None = None  # what the officer was shown (labels move with the threshold)
    threshold_seen: float | None = None
    # schema 2 ---------------------------------------------------------------------------------
    schema_version: int = 1  # lines written before schema 2 have no field -> 1
    batch: str | None = None  # one form submission (all items of it share the id)
    check: str | None = None  # facts check name (verdict "fact")
    fact: str | None = None  # fact id of the policy table (verdict "fact")
    question: str | None = None  # the fact question as the model was asked (snapshot)
    answer: Literal["yes", "no", "unclear"] | None = None  # the officer's value of the fact
    model_value: str | None = None  # the model's value when the officer judged it
    agrees: bool | None = None  # stimmt (True) / stimmt nicht (False)
    passage: dict[str, Any] | None = None  # snapshot of the judged passage: family, start, end, text
    provenance: dict[str, Any] = Field(default_factory=dict)
    source: Literal["officer", "demo"] = "officer"

    @property
    def target(self) -> Target:
        if self.verdict == "fact":
            return "fact"
        if self.verdict == "missed_family":
            return "family"
        return "call" if self.passage_index is None else "passage"


def feedback_path(runs_dir: str | Path, store: str = "real") -> Path:
    if store not in STORES:
        raise ValueError(f"store must be one of {STORES}, got {store!r}")
    return Path(runs_dir) / (DEMO_FILE if store == "demo" else FEEDBACK_FILE)


def add(runs_dir: str | Path, item: FeedbackItem, *, store: str = "real") -> FeedbackItem:
    if (store == "demo") != (item.source == "demo"):  # the two stores never mix
        raise ValueError(f"item source {item.source!r} does not belong in the {store!r} feedback store")
    audit.append_jsonl(feedback_path(runs_dir, store), item.model_dump(mode="json"))
    if store == "real":
        audit.log_event(runs_dir, "feedback", user=item.user, call_id=item.call_id, verdict=item.verdict,
                        family=item.family, passage_index=item.passage_index, label_seen=item.label_seen,
                        fact=item.fact, answer=item.answer, batch=item.batch, comment=item.comment[:200],
                        config_hash=item.provenance.get("config_hash"),
                        policy_table_hash=(item.provenance.get("policy_table") or {}).get("hash"))
    return item


def add_many(runs_dir: str | Path, items: Sequence[FeedbackItem], *, store: str = "real") -> list[FeedbackItem]:
    return [add(runs_dir, i, store=store) for i in items]


def load(runs_dir: str | Path, store: str = "real") -> list[FeedbackItem]:
    out = []
    for d in audit.read_jsonl(feedback_path(runs_dir, store)):
        try:
            item = FeedbackItem.model_validate(d)
        except Exception:
            continue
        if (store == "demo") == (item.source == "demo"):  # a stray line of the other kind is dropped
            out.append(item)
    return out


_VALUE_DE = {"yes": "ja", "no": "nein", "unclear": "unklar"}


def fact_choices(model_value: str | None) -> list[tuple[str, str]]:
    """The officer's three options for one fact as (answer, button text): "stimmt / stimmt nicht / unklar"
    relative to the model's value, each naming the value it records (so "stimmt nicht" is unambiguous).
    A model value of ``unclear`` -> Ja / Nein / stimmt (unklar)."""
    mv = model_value if model_value in FACT_ANSWERS else "unclear"
    if mv == "unclear":
        return [("yes", "Ja"), ("no", "Nein"), ("unclear", "stimmt (unklar)")]
    other = "no" if mv == "yes" else "yes"
    return [(mv, f"stimmt ({_VALUE_DE[mv]})"), (other, f"stimmt nicht ({_VALUE_DE[other]})"), ("unclear", "unklar")]


def new_batch() -> str:
    import uuid

    return uuid.uuid4().hex[:12]


def transcript_hash(result: CallResult) -> str:
    """Hash of what the checks read (segment ids, times, roles, text of the primary view)."""
    from callguard.cache import stable_hash

    t = result.transcript
    return stable_hash([[s.id, round(s.start, 2), round(s.end, 2), s.role, s.text] for s in t.segments])[:16]


def provenance_of(result: CallResult) -> dict[str, Any]:
    """What produced the call the officer judged: config / tuning / policy-table hashes, code version,
    model ids per check, ASR backend per view, transcript hash and the decision shown."""
    prov = result.meta.get("provenance") or {}
    models = {name: c.meta.get("model") for name, c in result.checks.items() if (c.meta or {}).get("model")}
    policy = next(((c.meta or {}).get("policy_table") for c in result.checks.values()
                   if c.type == "facts" and (c.meta or {}).get("policy_table")), None)
    d = result.decision
    return {"config_name": result.config_name or prov.get("config_name"), "config_hash": prov.get("config_hash"),
            "code_version": prov.get("code_version"), "tuning_hash": (prov.get("tuning") or {}).get("hash"),
            "policy_table": policy, "models": models,
            "asr": {name: t.asr_backend for name, t in result.all_views().items()},
            "transcript_hash": transcript_hash(result),
            "decision": {"label": d.label, "score": round(d.score, 4), "threshold": d.threshold,
                         "top_family": d.top_family}}


def items_from_form(result: CallResult, *, user: str, verdict: str | None = None,
                    passages: Mapping[int, str] | None = None,
                    facts: Mapping[tuple[str, str, str], str] | None = None,
                    missed: Sequence[str] = (), comment: str = "", threshold: float | None = None,
                    source: str = "officer") -> list[FeedbackItem]:
    """One officer submission (call detail panel) -> schema-2 items sharing a batch id and provenance.
    ``result`` carries the decision the officer saw; ``passages``: index -> applies / not_applies;
    ``facts``: (check, family, fact) -> yes / no / unclear (the model value and question are read from
    the stored facts check). Empty parts are skipped; the comment goes on every item."""
    if verdict is not None and verdict not in CALL_VERDICTS:
        raise ValueError(f"call verdict must be one of {CALL_VERDICTS}, got {verdict!r}")
    d = result.decision
    common: dict[str, Any] = dict(call_id=result.call_id, user=user, label_seen=d.label,
                                  threshold_seen=d.threshold if threshold is None else threshold, schema_version=2,
                                  batch=new_batch(), provenance=provenance_of(result), comment=comment,
                                  source=source)
    out: list[FeedbackItem] = []
    if verdict:
        out.append(FeedbackItem(verdict=verdict, family=d.top_family if verdict != "no_violation" else None, **common))
    for idx, v in sorted((passages or {}).items()):
        if v not in PASSAGE_VERDICTS or idx >= len(d.passages):
            continue
        p = d.passages[idx]
        out.append(FeedbackItem(verdict=v, family=p.family, passage_index=idx,
                                passage={"family": p.family, "start": p.start, "end": p.end, "text": p.text},
                                **common))
    for (check, family, fact), answer in sorted((facts or {}).items()):
        if answer not in FACT_ANSWERS:
            continue
        cr = result.checks.get(check)
        fs = cr.family_scores.get(family) if cr else None
        entry = ((fs.detail or {}).get("facts") or {}).get(fact) or {} if fs else {}
        mv = entry.get("value")
        out.append(FeedbackItem(verdict="fact", check=check, family=family, fact=fact, question=entry.get("question"),
                                answer=answer, model_value=mv, agrees=None if mv is None else answer == mv, **common))
    for fam in missed:
        out.append(FeedbackItem(verdict="missed_family", family=fam, **common))
    if not out:  # a comment alone is not a label
        raise ValueError("Bitte mindestens ein Urteil wählen (Anruf, Passage, Fakt oder übersehene Kategorie).")
    return out


def derive_label(item: FeedbackItem, stored_label: str | None = None) -> str | None:
    """The label the officer says is right. ``confirmed`` / ``applies`` keep what they saw; fact items
    say nothing about the call label."""
    if item.verdict in ("confirmed", "applies"):
        return item.label_seen or stored_label
    return CALL_LABEL.get(item.verdict)


def labels_from_feedback(items: Sequence[FeedbackItem],
                         stored: Mapping[str, str] | None = None) -> dict[str, str]:
    """call_id -> label. Per call the latest call-level verdict wins; without one, passage-level (and
    missed-category) verdicts count: any non-false-alarm verdict decides (latest), only false alarms ->
    no_alert. Fact items never decide a call label."""
    stored = stored or {}
    by_call: dict[str, list[FeedbackItem]] = {}
    for it in sorted(items, key=lambda i: i.ts):
        by_call.setdefault(it.call_id, []).append(it)
    out: dict[str, str] = {}
    for cid, its in by_call.items():
        call_level = [i for i in its if i.target == "call"]
        rest = [i for i in its if i.target in ("passage", "family")]
        if call_level:
            lab = derive_label(call_level[-1], stored.get(cid))
        elif rest:
            positive = [i for i in rest if i.verdict not in NEGATIVE]
            lab = derive_label(positive[-1] if positive else rest[-1], stored.get(cid))
        else:
            continue
        if lab:
            out[cid] = lab
    return out


# --------------------------------------------------------------------------------------------
# Suggestions
# --------------------------------------------------------------------------------------------


def keyword_hits(result: CallResult) -> set[str]:
    """Keyword ids the keyword check(s) found (not negated) in this call."""
    out = set()
    for c in result.checks.values():
        if c.type != "keywords":
            continue
        for f in c.findings:
            kid = f.detail.get("keyword_id")
            if kid and not f.detail.get("negated"):
                out.add(str(kid))
    return out


def keyword_precision(results: Sequence[CallResult], labels: Mapping[str, str], *, min_calls: int = 3,
                      max_precision: float = 0.25) -> list[dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for r in results:
        lab = labels.get(r.call_id)
        if lab is None:
            continue
        for kid in keyword_hits(r):
            row = rows.setdefault(kid, {"keyword": kid, "calls": 0, "flagged": 0, "harmless": 0, "call_ids": []})
            row["calls"] += 1
            row["flagged" if lab in FLAG else "harmless"] += 1
            row["call_ids"].append(r.call_id)
    out = []
    for row in rows.values():
        row["precision"] = round(row["flagged"] / row["calls"], 4)
        row["suggest_disable"] = row["calls"] >= min_calls and row["precision"] <= max_precision
        row["advice"] = (f"{row['keyword']} deaktivieren erwägen: in {row['calls']} bewerteten Anrufen getroffen, "
                         f"nur {row['flagged']} davon markierungswürdig ({row['precision']:.0%})."
                         if row["suggest_disable"] else "")
        out.append(row)
    return sorted(out, key=lambda r: (r["precision"], -r["calls"], r["keyword"]))


def check_reliability(results: Sequence[CallResult], labels: Mapping[str, str], threshold: float,
                      can_alarm: set[str] | None = None) -> list[dict[str, Any]]:
    """Per check: mean of its highest family score on flag-worthy vs harmless calls, and how often
    "score >= threshold" alone agrees with the label. Weight-0 / family-less checks are skipped."""
    per: dict[str, dict[str, list[float]]] = {}
    agree: dict[str, list[bool]] = {}
    for r in results:
        lab = labels.get(r.call_id)
        if lab is None:
            continue
        for name, c in r.checks.items():
            scores = [fs.score for fid, fs in c.family_scores.items() if can_alarm is None or fid in can_alarm]
            if not scores:
                continue
            s = max(scores)
            per.setdefault(name, {"pos": [], "neg": []})["pos" if lab in FLAG else "neg"].append(s)
            agree.setdefault(name, []).append((s >= threshold) == (lab in FLAG))
    out = []
    for name, d in per.items():
        mp = statistics.fmean(d["pos"]) if d["pos"] else None
        mn = statistics.fmean(d["neg"]) if d["neg"] else None
        out.append({"check": name, "n": len(d["pos"]) + len(d["neg"]),
                    "mean_score_flagworthy": None if mp is None else round(mp, 3),
                    "mean_score_harmless": None if mn is None else round(mn, 3),
                    "separation": None if mp is None or mn is None else round(mp - mn, 3),
                    "agreement": round(sum(agree[name]) / len(agree[name]), 3)})
    return sorted(out, key=lambda r: -(r["separation"] or -9))


def _counts(m: dict[str, Any]) -> dict[str, Any]:
    f = m["flag"]
    return {"fp": f["fp"], "fn": f["fn"], "tp": f["tp"], "tn": f["tn"], "false_alarm_rate": f["false_alarm_rate"],
            "miss_rate": f["miss_rate"], "f1": f["f1"], "alarms": m["workload"]["alarms"],
            "reviews": m["workload"]["reviews"]}


def suggest(pipeline: "Pipeline", results: Sequence[CallResult], items: Sequence[FeedbackItem], *,
            truth: Mapping[str, str] | None = None, thresholds: Sequence[float] | None = None,
            overrides: dict[str, Any] | None = None, min_keyword_calls: int = 3,
            max_false_alarm_rate: float | None = None) -> dict[str, Any]:
    """Everything the "Feedback & tuning" page shows. ``truth`` (call_id -> label, e.g. the case's
    Sollbewertung) fills calls without feedback; feedback always wins. ``overrides``: the knobs to
    compare against (default: the profile, incl. any tuning overlay)."""
    from callguard import eval as ev

    stored = {r.call_id: r.decision.label for r in results}
    fb = labels_from_feedback(items, stored)
    labels = {**{k: v for k, v in (truth or {}).items() if k in stored}, **{k: v for k, v in fb.items() if k in stored}}
    labelled = [r for r in results if r.call_id in labels]
    current_t = float((overrides or {}).get("threshold", pipeline.cfg.fusion.get("threshold", 0.55)))
    families = pipeline.ctx.families()
    can_alarm = {f.id for f in families if f.can_alarm}
    out: dict[str, Any] = {
        "n_feedback": len(items), "n_labelled": len(labelled),
        "sources": {"feedback": sum(1 for k in fb if k in stored),
                    "ground_truth": sum(1 for k in labels if k not in fb)},
        "current_threshold": current_t, "current": None, "suggestion": None, "delta": None, "sweep": [],
        "keywords": keyword_precision(labelled, labels, min_calls=min_keyword_calls),
        "checks": check_reliability(labelled, labels, current_t, can_alarm),
        "warning": None,
    }
    if not labelled:
        out["warning"] = "Keine bewerteten Anrufe: erst Feedback geben (oder Sollbewertung einbeziehen)."
        return out
    if len(labelled) < 20:
        out["warning"] = (f"Nur {len(labelled)} bewertete Anrufe: der Vorschlag ist ein Hinweis, keine Messung "
                          f"(ein Anruf mehr oder weniger kann ihn verschieben).")
    grid = sorted({*(thresholds or ev.DEFAULT_THRESHOLDS), round(current_t, 4)})
    swept = ev.sweep(pipeline, labelled, labels, grid, overrides)
    cur = next(s for s in swept if abs(s["threshold"] - current_t) < 1e-9)
    pick = ev.suggest_threshold(swept, max_false_alarm_rate)
    out["sweep"] = [{"threshold": s["threshold"], **_counts(s["metrics"])} for s in swept]
    out["current"] = _counts(cur["metrics"])
    if pick:
        best = next(s for s in swept if abs(s["threshold"] - pick["threshold"]) < 1e-9)
        out["suggestion"] = {**pick, **_counts(best["metrics"])}
        c, b = out["current"], out["suggestion"]
        out["delta"] = {"fp": b["fp"] - c["fp"], "fn": b["fn"] - c["fn"],
                        "alarms": b["alarms"] - c["alarms"], "reviews": b["reviews"] - c["reviews"]}
    return out


# --------------------------------------------------------------------------------------------
# Tuning overlay
# --------------------------------------------------------------------------------------------

HEADER = ("# Officer tuning overlay: laid over the profile by callguard.config.load_config (after the profile,\n"
          "# before --set). Written by `callguard feedback apply` / the UI page 'Feedback & tuning'.\n"
          "# Only fusion.threshold, fusion.review_band and check weights are read. Delete to revert.\n")


def tuning_path(cfg: AppConfig) -> Path:
    p = Path(cfg.paths.tuning or "config/tuning.yaml")
    return p if p.is_absolute() else ROOT / p


def read_tuning(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    return (yaml.safe_load(p.read_text()) or {}) if p.is_file() else {}


def apply_tuning(path: str | Path, profile: str, *, threshold: float | None = None,
                 review_band: float | None = None, weights: Mapping[str, float] | None = None,
                 runs_dir: str | Path | None = None, user: str | None = None, reason: str = "",
                 clear: bool = False) -> dict[str, Any]:
    """Set (or ``clear``) the overlay of ``profile``; other profiles' entries are kept. Returns
    ``{path, profile, before, after, old_hash, new_hash}`` and logs a ``tuning_save`` audit event."""
    p = Path(path)
    data = read_tuning(p)
    old_hash = audit.file_hash(p)
    profiles = data.setdefault("profiles", {})
    before = dict(profiles.get(profile) or {})
    if clear:
        profiles.pop(profile, None)
    else:
        entry = profiles.setdefault(profile, {})
        fusion = entry.setdefault("fusion", {})
        for k, v in (("threshold", threshold), ("review_band", review_band)):
            if v is not None:
                if not 0.0 <= float(v) <= 1.0:
                    raise ValueError(f"{k} must be within 0..1, got {v}")
                fusion[k] = round(float(v), 4)
        if weights:
            entry.setdefault("weights", {}).update({k: round(float(v), 4) for k, v in weights.items()})
        entry["updated_at"] = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        entry["updated_by"] = user or audit.current_user()
        if reason:
            entry["reason"] = reason
        assert set(fusion) <= set(TUNING_FUSION_KEYS)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    tmp.replace(p)
    info = {"path": str(p), "profile": profile, "before": before, "after": profiles.get(profile),
            "old_hash": old_hash, "new_hash": audit.file_hash(p)}
    if runs_dir is not None:
        audit.log_event(runs_dir, "tuning_save", user=user, **info, reason=reason)
    return info


def restore_tuning(path: str | Path, profile: str, entry: Mapping[str, Any] | None, *,
                   runs_dir: str | Path | None = None, user: str | None = None, reason: str = "") -> dict[str, Any]:
    """Put one profile's overlay entry back exactly as it was (``None`` = no entry): the rollback of an
    approved proposal. Same atomic write and ``tuning_save`` audit event as :func:`apply_tuning`."""
    p = Path(path)
    data = read_tuning(p)
    old_hash = audit.file_hash(p)
    profiles = data.setdefault("profiles", {})
    before = dict(profiles.get(profile) or {})
    if entry:
        unknown = set((entry.get("fusion") or {})) - set(TUNING_FUSION_KEYS)
        if unknown:
            raise ValueError(f"unknown fusion keys in the restored entry: {sorted(unknown)}")
        profiles[profile] = dict(entry)
    else:
        profiles.pop(profile, None)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(HEADER + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    tmp.replace(p)
    info = {"path": str(p), "profile": profile, "before": before, "after": profiles.get(profile),
            "old_hash": old_hash, "new_hash": audit.file_hash(p)}
    if runs_dir is not None:
        audit.log_event(runs_dir, "tuning_save", user=user, **info, reason=reason or "rollback")
    return info
