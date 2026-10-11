"""Sink ``notify``: route a flagged call to the right desk and deliver the message (v2_plan §3).

Channels (``channels: [outbox, webhook, smtp]``):

* ``outbox``  always safe: appends to ``runs/<profile>/outbox.jsonl`` (the UI's Notifications page reads it).
  The same decision is not queued twice (``key`` = call + label + score + families + recipients), so
  re-running a batch does not spam the desks.
* ``webhook`` generic JSON POST of the message to ``webhook_url`` (Teams/Slack bridge, ticketing, SIEM).
* ``smtp``    plain-text mail per recipient (``smtp: {host, port, sender, starttls, user, password}``);
  optional and untested against a real relay (MailHog: ``host: localhost, port: 1025``).

Every delivered message also leaves a ``notification`` event in ``audit.jsonl``. Failures are logged,
never raised: a down mail relay must not cost the call result.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from callguard import audit
from callguard.cache import stable_hash
from callguard.plugins import Sink
from callguard.routing import Directory, Route, RoutingConfig, build_message, route
from callguard.types import CallResult, Decision

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard")

OUTBOX_FILE = "outbox.jsonl"
CHANNELS = ("outbox", "webhook", "smtp")


def outbox_path(runs_dir: str | Path) -> Path:
    return Path(runs_dir) / OUTBOX_FILE


def read_outbox(runs_dir: str | Path, call_id: str | None = None) -> list[dict[str, Any]]:
    return [m for m in audit.read_jsonl(outbox_path(runs_dir)) if call_id is None or m.get("call_id") == call_id]


def message_key(msg: dict[str, Any]) -> str:
    return stable_hash({"call_id": msg["call_id"], "label": msg["label"], "score": msg["score"],
                        "families": msg["families"], "to": sorted(r["id"] for r in msg["to"]),
                        "cc": sorted(r["id"] for r in msg["cc"])})


class Notifier:
    """Routing + delivery, usable without a pipeline (``callguard route --send``, UI)."""

    def __init__(self, ctx: "Context", *, routing: str | None = None, directory: str | None = None,
                 channels: list[str] | tuple[str, ...] = ("outbox",), webhook_url: str | None = None,
                 smtp: dict[str, Any] | None = None, patterns: bool = True, min_calls: int = 3,
                 timeout: float = 5.0):
        bad = sorted(set(channels) - set(CHANNELS))
        if bad:
            raise ValueError(f"unknown notify channels {bad}; known: {list(CHANNELS)}")
        self.ctx = ctx
        self.routing_cfg = RoutingConfig.load(routing)
        self.directory = Directory.load(directory)
        self.channels = list(channels)
        self.webhook_url = webhook_url
        self.smtp = dict(smtp or {})
        self.patterns = patterns
        self.min_calls = int(min_calls)
        self.timeout = float(timeout)
        self._summaries: dict[str, tuple[tuple[int, int], str, Any]] = {}

    def analysis(self, extra: CallResult | None = None) -> dict[str, Any] | None:
        """Cross-call patterns over the profile's stored results (+ ``extra``, the call being emitted).
        Each result file is parsed and summarized once per version (mtime + size), so a 60-call batch
        does not re-read every result for every call."""
        if not self.patterns:
            return None
        from callguard import patterns

        try:
            summaries: dict[str, Any] = {}
            for f in sorted(Path(self.ctx.runs_dir).glob("*/result.json")):
                st = f.stat()
                version = (st.st_mtime_ns, st.st_size)
                hit = self._summaries.get(str(f))
                if hit is None or hit[0] != version:
                    r = CallResult.model_validate_json(f.read_text())
                    hit = (version, r.call_id, patterns.summarize(r, self.directory))
                    self._summaries[str(f)] = hit
                summaries[hit[1]] = hit[2]
            if extra is not None:
                summaries[extra.call_id] = patterns.summarize(extra, self.directory)
            return patterns.analyze(patterns.one_per_dialogue(list(summaries.values())),
                                    min_calls=self.min_calls, directory=self.directory)
        except Exception as e:
            log.warning("patterns for routing skipped: %s", e)
            return None

    def route(self, result: CallResult, decision: Decision | None = None,
              analysis: dict[str, Any] | None = None) -> Route:
        from callguard.checks.entities import entities_of

        return route(result, self.routing_cfg, self.directory, decision=decision,
                     entities=entities_of(result, self.directory), analysis=analysis)

    def message(self, result: CallResult, decision: Decision | None = None,
                analysis: dict[str, Any] | None = None) -> tuple[Route, dict[str, Any] | None]:
        r = self.route(result, decision, analysis)
        if not r.routed:
            return r, None
        msg = build_message(result, r, self.ctx.cfg, decision=decision)
        msg["key"] = message_key(msg)
        return r, msg

    def send(self, msg: dict[str, Any], *, force: bool = False) -> dict[str, str]:
        """Deliver through every channel; returns channel -> "sent" / "duplicate" / "error: ..."."""
        status: dict[str, str] = {}
        msg = {"ts": audit.now_iso(), **msg}
        for ch in self.channels:
            try:
                status[ch] = getattr(self, f"_send_{ch}")(msg, force)
            except Exception as e:
                log.warning("notify %s for %s failed: %s", ch, msg.get("call_id"), e)
                status[ch] = f"error: {type(e).__name__}: {e}"
        if any(v == "sent" for v in status.values()):
            audit.log_event(self.ctx.runs_dir, "notification", user="pipeline", call_id=msg["call_id"],
                            label=msg["label"], to=[r["id"] for r in msg["to"]], cc=[r["id"] for r in msg["cc"]],
                            channels=status, key=msg.get("key"))
        return status

    def _send_outbox(self, msg: dict[str, Any], force: bool) -> str:
        p = outbox_path(self.ctx.runs_dir)
        if not force and any(m.get("key") == msg.get("key") for m in audit.read_jsonl(p)):
            return "duplicate"
        audit.append_jsonl(p, msg)
        return "sent"

    def _send_webhook(self, msg: dict[str, Any], force: bool) -> str:
        if not self.webhook_url:
            return "skipped: no webhook_url"
        r = httpx.post(self.webhook_url, json=msg, timeout=self.timeout)
        return "sent" if r.status_code < 300 else f"error: HTTP {r.status_code}"

    def _send_smtp(self, msg: dict[str, Any], force: bool) -> str:
        s = self.smtp
        to = [r["email"] for r in msg["to"] if r.get("email")]
        cc = [r["email"] for r in msg["cc"] if r.get("email")]
        if not to and not cc:
            return "skipped: no addresses"
        mail = EmailMessage()
        mail["Subject"], mail["From"] = msg["subject"], s.get("sender", "sherlock-phones@bank.example")
        mail["To"] = ", ".join(to)
        if cc:
            mail["Cc"] = ", ".join(cc)
        mail.set_content(msg["body"])
        with smtplib.SMTP(s.get("host", "localhost"), int(s.get("port", 25)), timeout=self.timeout) as server:
            if s.get("starttls"):
                server.starttls()
            if s.get("user"):
                server.login(s["user"], s.get("password", ""))
            server.send_message(mail)
        return "sent"


class NotifySink(Sink):
    def __init__(self, ctx: "Context", *, enabled: bool = True, routing: str | None = None,
                 directory: str | None = None, channels: list[str] | tuple[str, ...] = ("outbox",),
                 webhook_url: str | None = None, smtp: dict[str, Any] | None = None, patterns: bool = True,
                 min_calls: int = 3, timeout: float = 5.0):
        super().__init__(ctx, enabled=enabled, routing=routing, directory=directory, channels=list(channels),
                         webhook_url=webhook_url, smtp=smtp, patterns=patterns, min_calls=min_calls,
                         timeout=timeout)
        self.notifier = Notifier(ctx, routing=routing, directory=directory, channels=channels,
                                 webhook_url=webhook_url, smtp=smtp, patterns=patterns, min_calls=min_calls,
                                 timeout=timeout)

    def emit(self, result: CallResult) -> None:
        n = self.notifier
        _, msg = n.message(result, analysis=n.analysis(result))
        if msg is not None:
            n.send(msg)
