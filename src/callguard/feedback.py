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

FeedbackVerdict = Literal["confirmed", "false_alarm", "missed", "should_review", "not_review"]
VERDICTS: tuple[str, ...] = ("confirmed", "false_alarm", "missed", "should_review", "not_review")
VERDICT_DE = {"confirmed": "Bestätigt", "false_alarm": "Fehlalarm", "missed": "Verpasst (hätte Alarm sein müssen)",
              "should_review": "Hätte geprüft werden müssen", "not_review": "Prüfung unnötig"}
FEEDBACK_FILE = "feedback.jsonl"
FLAG = ("alarm", "review")


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


def feedback_path(runs_dir: str | Path) -> Path:
    return Path(runs_dir) / FEEDBACK_FILE


def add(runs_dir: str | Path, item: FeedbackItem) -> FeedbackItem:
    audit.append_jsonl(feedback_path(runs_dir), item.model_dump(mode="json"))
    audit.log_event(runs_dir, "feedback", user=item.user, call_id=item.call_id, verdict=item.verdict,
                    family=item.family, passage_index=item.passage_index, label_seen=item.label_seen,
                    comment=item.comment[:200])
    return item


def load(runs_dir: str | Path) -> list[FeedbackItem]:
    out = []
    for d in audit.read_jsonl(feedback_path(runs_dir)):
        try:
            out.append(FeedbackItem.model_validate(d))
        except Exception:
            continue
    return out


def derive_label(item: FeedbackItem, stored_label: str | None = None) -> str | None:
    """The label the officer says is right. ``confirmed`` keeps what they saw."""
    if item.verdict == "confirmed":
        return item.label_seen or stored_label
    return {"false_alarm": "no_alert", "missed": "alarm", "should_review": "review",
            "not_review": "no_alert"}[item.verdict]


def labels_from_feedback(items: Sequence[FeedbackItem],
                         stored: Mapping[str, str] | None = None) -> dict[str, str]:
    """call_id -> label. Per call the latest call-level verdict wins; without one, passage-level verdicts
    count: any non-false-alarm verdict decides (latest), only false alarms -> no_alert."""
    stored = stored or {}
    by_call: dict[str, list[FeedbackItem]] = {}
    for it in sorted(items, key=lambda i: i.ts):
        by_call.setdefault(it.call_id, []).append(it)
    out: dict[str, str] = {}
    for cid, its in by_call.items():
        call_level = [i for i in its if i.passage_index is None]
        if call_level:
            lab = derive_label(call_level[-1], stored.get(cid))
        else:
            positive = [i for i in its if i.verdict != "false_alarm"]
            lab = derive_label(positive[-1] if positive else its[-1], stored.get(cid))
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
