"""Reports flagged calls to the Outcept trigger API (``POST /triggers {url, title, description}``).

Each trigger links back into the callguard UI at the suspicious passage (``?call=<id>&t=<seconds>``,
starting ``link_pad`` seconds early), so the officer lands on the audio, not on a 20-minute call.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import quote

import httpx

from callguard.fusion import top_family
from callguard.fusion.weighted import short_label
from callguard.plugins import Sink
from callguard.types import CallResult, Passage, fmt_ts

if TYPE_CHECKING:
    from callguard.context import Context

log = logging.getLogger("callguard")

MAX_TITLE = 200
MAX_DESCRIPTION = 2000


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


class OutceptTriggerSink(Sink):
    def __init__(self, ctx: "Context", *, url: str = "http://localhost:8080/triggers",
                 labels: list[str] | tuple[str, ...] = ("alarm", "review"), per_passage: bool = True,
                 timeout: float = 5.0, enabled: bool = True):
        super().__init__(ctx, enabled=enabled, url=url, labels=list(labels), per_passage=per_passage,
                         timeout=timeout)
        self.url = url
        self.labels = list(labels)
        self.per_passage = per_passage
        self.timeout = float(timeout)

    def link(self, call_id: str, start: float) -> str:
        base = str(self.ctx.cfg.app.get("base_url", "http://localhost:8501")).rstrip("/")
        pad = float(self.ctx.cfg.snippets.get("link_pad", 10.0))
        return f"{base}/?call={quote(call_id, safe='')}&t={max(0, int(start - pad))}"

    def triggers(self, result: CallResult) -> list[dict[str, str]]:
        """The request bodies this call produces (empty if its label is not reported)."""
        d = result.decision
        if d.label not in self.labels:
            return []
        if self.per_passage and d.passages:
            return [self._body(result, p) for p in d.passages]
        return [self._body(result, d.passages[0] if d.passages else None)]

    def _body(self, result: CallResult, p: Passage | None) -> dict[str, str]:
        d = result.decision
        if p is not None:
            fam_label, start = p.family_label or p.family, p.start
        else:
            fid = top_family(d)
            fam_label = d.families[fid].label if fid else "Unklarer Anruf"
            start = 0.0
        title = f"[{d.label.upper()}] {short_label(fam_label)} - {result.call_id} @ {fmt_ts(start)}"

        lines = [f"{d.label.upper()}: Score {d.score:.2f} (Schwelle {d.threshold:.2f}), "
                 f"Unsicherheit {d.uncertainty:.2f}."]
        if p is not None:
            lines.append(f"Passage {fmt_ts(p.start)}-{fmt_ts(p.end)} ({short_label(fam_label)}, "
                         f"Score {p.score:.2f}):")
            lines += [f"- {r}" for r in p.reasons]
            if p.text:
                lines.append(f'Wortlaut: "{_truncate(p.text, 400)}"')
        lines.append("Entscheid:")
        lines += [f"- {r}" for r in d.reasons]
        return {"url": self.link(result.call_id, start), "title": _truncate(title, MAX_TITLE),
                "description": _truncate("\n".join(lines), MAX_DESCRIPTION)}

    def emit(self, result: CallResult) -> None:
        for body in self.triggers(result):
            try:
                r = httpx.post(self.url, json=body, timeout=self.timeout)
            except Exception as e:  # trigger API down must never cost us the call result
                log.warning("outcept trigger for %s not sent (%s: %s)", result.call_id, type(e).__name__, e)
                return  # the API is unreachable: don't wait out a timeout per passage
            if r.status_code >= 300:
                log.warning("outcept trigger for %s rejected: HTTP %s %s", result.call_id, r.status_code,
                            r.text[:200])
