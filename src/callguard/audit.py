"""Append-only audit trail: ``runs/<profile>/audit.jsonl`` (docs/design/v2_plan.md §5).

One JSON object per line: ``{ts, kind, user, call_id?, ...data}``. Kinds used by the code base:

* ``decision``      a call was decided (``audit`` sink): label, score, threshold, family, config/tuning hash
* ``notification``  a routed message left through a channel (``notify`` sink, ``callguard route --send``)
* ``feedback``      an officer verdict on a call (``callguard feedback add``, UI buttons)
* ``tuning_save``   fusion knobs written to the tuning overlay (``callguard feedback apply``, UI)
* ``keywords_save`` / ``criteria_save``  the officer edited what is looked for (UI editor)

The UI calls :func:`log_event` directly, e.g. ``audit.log_event(app.runs_dir, "keywords_save",
family="trade", keyword_ids=[...])``. Writing never raises (an audit hiccup must not cost a decision);
failures go to the log. Lines are written with a single ``write`` in append mode, so concurrent writers
(UI + batch) do not interleave within a line on POSIX.
"""

from __future__ import annotations

import datetime as _dt
import getpass
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from callguard.plugins import Sink
from callguard.types import CallResult

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard")

AUDIT_FILE = "audit.jsonl"


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def current_user() -> str:
    """Who acts: ``CALLGUARD_USER`` (set by the UI login / reverse proxy), else the OS user."""
    env = os.environ.get("CALLGUARD_USER")
    if env:
        return env
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def audit_path(runs_dir: str | Path) -> Path:
    return Path(runs_dir) / AUDIT_FILE


def file_hash(path: str | Path) -> str | None:
    """Short sha256 of a file's bytes (None if it does not exist): what a save changed, provably."""
    p = Path(path)
    if not p.is_file():
        return None
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def append_jsonl(path: str | Path, obj: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, default=str) + "\n"
    with p.open("a", encoding="utf-8") as f:
        f.write(line)


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Every parseable line (a torn last line from a crash is skipped, not fatal)."""
    p = Path(path)
    if not p.is_file():
        return []
    out = []
    for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("%s:%d: unreadable line skipped", p, i)
    return out


def log_event(runs_dir: str | Path, kind: str, *, user: str | None = None, call_id: str | None = None,
              **data: Any) -> dict[str, Any]:
    """Append one event and return it. Never raises."""
    event: dict[str, Any] = {"ts": now_iso(), "kind": kind, "user": user or current_user()}
    if call_id is not None:
        event["call_id"] = call_id
    event.update(data)
    try:
        append_jsonl(audit_path(runs_dir), event)
    except Exception as e:
        log.warning("audit event %s not written: %s", kind, e)
    return event


def read_events(runs_dir: str | Path, kind: str | None = None, call_id: str | None = None,
                limit: int | None = None) -> list[dict[str, Any]]:
    """Events oldest first, filtered; ``limit`` keeps the newest N."""
    ev = [e for e in read_jsonl(audit_path(runs_dir))
          if (kind is None or e.get("kind") == kind) and (call_id is None or e.get("call_id") == call_id)]
    return ev[-limit:] if limit else ev


def decision_event(result: CallResult) -> dict[str, Any]:
    d = result.decision
    prov = result.meta.get("provenance") or {}
    return {"label": d.label, "score": round(d.score, 4), "uncertainty": round(d.uncertainty, 4),
            "threshold": d.threshold, "top_family": d.top_family,
            "passages": [{"family": p.family, "start": round(p.start, 1), "end": round(p.end, 1)}
                         for p in d.passages],
            "config_name": result.config_name, "config_hash": prov.get("config_hash"),
            "tuning_hash": (prov.get("tuning") or {}).get("hash"), "code_version": prov.get("code_version")}


class AuditSink(Sink):
    """Sink ``audit``: one ``decision`` event per processed call (who/what/which config decided)."""

    def __init__(self, ctx: "Context", *, enabled: bool = True, user: str | None = None):
        super().__init__(ctx, enabled=enabled, user=user)
        self.user = user

    def emit(self, result: CallResult) -> None:
        log_event(self.ctx.runs_dir, "decision", user=self.user or "pipeline", call_id=result.call_id,
                  **decision_event(result))
