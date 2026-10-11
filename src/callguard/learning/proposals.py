"""Change proposals for the decision knobs with a four-eyes approval and rollback. Never auto-applied.

``runs/<profile>/learning/proposals.jsonl`` is an append-only event log; a proposal's state is the fold
of its events::

    proposed  (id, profile, change {threshold?, review_band?}, evidence, label_source, reason, user)
    approved  (user != proposer; the change is written to the tuning overlay; the overlay entry before
               the change is stored for the rollback)
    rejected  (user != proposer, reason)
    rolled_back (any user, reason; the overlay entry is restored exactly as it was before the approval)

Every event is also an audit event (``proposal_*``) and the overlay writes are ``tuning_save`` events
(``callguard.feedback.apply_tuning`` / ``restore_tuning``), so the audit log shows who proposed, who
approved, what changed (file hashes) and on which evidence. Proposals from simulated demo feedback carry
``label_source: demo`` and say so everywhere.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from callguard import audit
from callguard import feedback as fb

PROPOSALS_FILE = "learning/proposals.jsonl"
STATUS_DE = {"open": "offen", "approved": "genehmigt (aktiv)", "rejected": "abgelehnt",
             "rolled_back": "zurückgerollt", "superseded": "ersetzt"}
CHANGE_KEYS = ("threshold", "review_band")


class FourEyesError(PermissionError):
    """The approver is the proposer (or no name was given)."""


class ProposalStateError(ValueError):
    """The action does not fit the proposal's state (e.g. approving a rejected proposal)."""


@dataclass
class Proposal:
    id: str
    profile: str
    change: dict[str, float]
    proposed_by: str
    proposed_at: str
    reason: str = ""
    label_source: str = "real"  # real | demo
    evidence: dict[str, Any] = field(default_factory=dict)
    status: str = "open"
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rolled_back_by: str | None = None
    before: dict[str, Any] | None = None  # overlay entry of the profile before the approval
    after: dict[str, Any] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


def path(runs_dir: str | Path) -> Path:
    return Path(runs_dir) / PROPOSALS_FILE


def _norm(user: str | None) -> str:
    return " ".join(str(user or "").split()).casefold()


def _event(runs_dir: str | Path, event: dict[str, Any]) -> dict[str, Any]:
    event = {"ts": audit.now_iso(), **event}
    audit.append_jsonl(path(runs_dir), event)
    audit.log_event(runs_dir, f"proposal_{event['event']}", user=event.get("user"),
                    **{k: v for k, v in event.items() if k not in ("ts", "user", "event")})
    return event


def load(runs_dir: str | Path) -> list[Proposal]:
    """All proposals, newest first, with their current state."""
    props: dict[str, Proposal] = {}
    for e in audit.read_jsonl(path(runs_dir)):
        kind, pid = e.get("event"), e.get("id")
        if kind == "proposed" and pid:
            props[pid] = Proposal(id=pid, profile=e.get("profile", ""), change=dict(e.get("change") or {}),
                                  proposed_by=e.get("user", ""), proposed_at=e.get("ts", ""),
                                  reason=e.get("reason", ""), label_source=e.get("label_source", "real"),
                                  evidence=dict(e.get("evidence") or {}))
        p = props.get(pid)
        if p is None:
            continue
        p.history.append({k: e.get(k) for k in ("ts", "event", "user", "reason")})
        if kind == "approved":
            p.status, p.approved_by, p.approved_at = "approved", e.get("user"), e.get("ts")
            p.before, p.after = e.get("before"), e.get("after")
        elif kind == "rejected":
            p.status, p.rejected_by = "rejected", e.get("user")
        elif kind == "rolled_back":
            p.status, p.rolled_back_by = "rolled_back", e.get("user")
        elif kind == "superseded":
            p.status = "superseded"
    return sorted(props.values(), key=lambda p: p.proposed_at, reverse=True)


def get(runs_dir: str | Path, pid: str) -> Proposal:
    p = next((x for x in load(runs_dir) if x.id == pid), None)
    if p is None:
        raise KeyError(f"no proposal {pid!r}")
    return p


def propose(runs_dir: str | Path, profile: str, change: dict[str, float], *, user: str, reason: str = "",
            evidence: dict[str, Any] | None = None, label_source: str = "real") -> Proposal:
    if not _norm(user):
        raise FourEyesError("Vorschlagende Person fehlt (Name angeben).")
    change = {k: round(float(v), 4) for k, v in change.items() if k in CHANGE_KEYS and v is not None}
    if not change:
        raise ValueError(f"nothing to propose: give one of {CHANGE_KEYS}")
    for k, v in change.items():
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"{k} must be within 0..1, got {v}")
    pid = "P-" + uuid.uuid4().hex[:8]
    _event(runs_dir, {"event": "proposed", "id": pid, "user": user, "profile": profile, "change": change,
                      "reason": reason, "label_source": label_source, "evidence": evidence or {}})
    return get(runs_dir, pid)


def _require(p: Proposal, status: str, action: str) -> None:
    if p.status != status:
        raise ProposalStateError(f"{p.id} ist {STATUS_DE.get(p.status, p.status)}: {action} nicht möglich.")


def _four_eyes(p: Proposal, user: str) -> None:
    if not _norm(user):
        raise FourEyesError("Name der genehmigenden Person fehlt.")
    if _norm(user) == _norm(p.proposed_by):
        raise FourEyesError(f"Vier-Augen-Prinzip: {p.proposed_by} hat {p.id} vorgeschlagen und kann ihn nicht "
                            "selbst genehmigen oder ablehnen.")


def approve(runs_dir: str | Path, pid: str, *, user: str, tuning_path: str | Path, reason: str = "") -> Proposal:
    """Second person approves: the change goes into the tuning overlay of the proposal's profile. An
    earlier approved proposal of the same profile is marked ``superseded`` (its rollback point stays in
    the log; roll back the newest first)."""
    p = get(runs_dir, pid)
    _require(p, "open", "Genehmigen")
    _four_eyes(p, user)
    before = fb.read_tuning(tuning_path).get("profiles", {}).get(p.profile)
    why = (f"{p.id} vorgeschlagen von {p.proposed_by}, genehmigt von {user}"
           + (" (Demo-Feedback)" if p.label_source == "demo" else "") + (f": {reason}" if reason else ""))
    info = fb.apply_tuning(tuning_path, p.profile, threshold=p.change.get("threshold"),
                           review_band=p.change.get("review_band"), runs_dir=runs_dir, user=user, reason=why)
    for other in load(runs_dir):
        if other.id != pid and other.profile == p.profile and other.status == "approved":
            _event(runs_dir, {"event": "superseded", "id": other.id, "user": user, "by": pid})
    _event(runs_dir, {"event": "approved", "id": pid, "user": user, "reason": reason, "profile": p.profile,
                      "before": before, "after": info["after"], "old_hash": info["old_hash"],
                      "new_hash": info["new_hash"]})
    return get(runs_dir, pid)


def reject(runs_dir: str | Path, pid: str, *, user: str, reason: str = "") -> Proposal:
    p = get(runs_dir, pid)
    _require(p, "open", "Ablehnen")
    _four_eyes(p, user)
    _event(runs_dir, {"event": "rejected", "id": pid, "user": user, "reason": reason})
    return get(runs_dir, pid)


def rollback(runs_dir: str | Path, pid: str, *, user: str, tuning_path: str | Path, reason: str = "") -> Proposal:
    """Restore the overlay entry from before the approval (any named user; it is a safety action)."""
    p = get(runs_dir, pid)
    _require(p, "approved", "Zurückrollen")
    if not _norm(user):
        raise FourEyesError("Name fehlt.")
    info = fb.restore_tuning(tuning_path, p.profile, p.before, runs_dir=runs_dir, user=user,
                             reason=f"Rollback {p.id}" + (f": {reason}" if reason else ""))
    _event(runs_dir, {"event": "rolled_back", "id": pid, "user": user, "reason": reason,
                      "old_hash": info["old_hash"], "new_hash": info["new_hash"]})
    return get(runs_dir, pid)
