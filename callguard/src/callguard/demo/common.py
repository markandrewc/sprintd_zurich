"""Helpers the demo pages share: the decision card per call (live decision), the worklist rows, routing and
the Outcept report. Thin glue over :mod:`callguard.demo.card`, the officer UI's backend and the sinks."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from callguard.checks.facts import DEFAULT_TABLE, PolicyTable, load_policy_table
from callguard.config import ROOT
from callguard.demo import card as cd
from callguard.demo.state import DEMO_URL_ENV
from callguard.types import CallResult, Decision
from callguard.ui import fact_answers as fa
from callguard.ui.backend import LABEL_RANK
from callguard.ui.session import AppState

log = logging.getLogger("callguard.demo")

LABEL_BADGE = {"alarm": "red", "review": "orange", "no_alert": "gray"}
LABEL_ICON = {"alarm": ":material/notifications_active:", "review": ":material/person_search:",
              "no_alert": ":material/check_circle:"}
DEFAULT_DEMO_URL = "http://localhost:8502"
OUTCEPT_URL = "http://localhost:8080/triggers"


def badge(label: str, text: str | None = None) -> str:
    return f":{LABEL_BADGE.get(label, 'gray')}-badge[{LABEL_ICON.get(label, '')} {text or cd.LABEL_DE.get(label, label)}]"


def active_table(app: AppState) -> PolicyTable | None:
    try:
        return load_policy_table(active_table_path(app))
    except Exception:
        return None


def active_table_path(app: AppState) -> Path:
    spec = next((c for c in app.cfg.checks if c.get("type") == "facts"), {})
    rel = str(spec.get("policy_table") or DEFAULT_TABLE)
    return Path(rel) if Path(rel).is_absolute() else ROOT / rel


def policy_status(app: AppState) -> dict[str, Any]:
    """Which Regelwerk the shown decisions come from: the active version number and how many calls were decided
    with exactly the active table (per-family hash, as the facts check records it) vs an older one."""
    from callguard.policy_versions import VersionStore

    out: dict[str, Any] = {"version": None, "same": 0, "other": [], "without": 0}
    path = active_table_path(app)
    try:
        table = load_policy_table(path)
        act = VersionStore(path).active()
        out["version"] = act.n if act is not None else None
    except Exception:
        return out
    for cid, r in app.loaded.results.items():
        cr = next((c for c in r.checks.values() if c.type == "facts" and not (c.meta or {}).get("error")), None)
        stored = ((cr.meta or {}).get("policy_table") or {}).get("hash") if cr is not None else None
        if not stored:
            out["without"] += 1
        elif stored == table.key(list(cr.family_scores)):
            out["same"] += 1
        else:
            out["other"].append(cid)
    return out


def table_for(app: AppState, result: CallResult) -> PolicyTable | None:
    """The policy table the call's facts check read (its rule ids and facts), else the profile's."""
    check = next((n for n, c in result.checks.items() if c.type == "facts" and not (c.meta or {}).get("error")), None)
    if check:
        try:
            return fa.table_of(result, check)
        except Exception:
            pass
    return active_table(app)


def with_fact_policy(app: AppState, result: CallResult) -> CallResult:
    """Profiles deciding with the fact policy (two readers): the call with both readers replaced by the combined
    facts result the live fusion decides on (per fact both readers' p, their values, the band, agreement)."""
    from callguard.demo import facts_ui as fu
    from callguard.fact_policy import combined_checks, has_both

    fus = fu.fusion(app)
    if fus is None:
        return result
    try:
        pol = fu.session_policy(app)
        if not has_both(result, pol):
            return result
        checks = combined_checks(result, fus.table(), pol, family_names=fus._names(app.all_families), **fus.scoring)
        return result.model_copy(update={"checks": checks})
    except Exception as e:  # the card falls back to the stored first reader
        log.warning("card: fact policy view of %s failed: %s", result.call_id, e)
        return result


def card_for(app: AppState, call_id: str, decision: Decision | None = None) -> cd.Card:
    result = with_fact_policy(app, app.loaded.results[call_id])
    d = decision or app.decided[call_id].decision
    s = app.settings
    try:
        opened = fa.open_families(result) if d.label == "review" else []
    except Exception:
        opened = []
    return cd.build_card(result, d, app.all_families, table=table_for(app, result), can_alarm=app.can_alarm or None,
                         weights=s.weights, threshold=d.threshold, review_band=s.review_band,
                         max_uncertainty=s.max_uncertainty, open_families=opened)


def sort_key(row: dict[str, Any]) -> tuple:
    """Alarms first (riskiest first), then reviews (most uncertain first), then the rest by score."""
    rank = LABEL_RANK.get(row["label"], 9)
    second = -row["uncertainty"] if row["label"] == "review" else -row["score"]
    return (rank, second, -row["score"], row["call_id"])


def case_rows(app: AppState, judged: set[str]) -> list[dict[str, Any]]:
    rows = []
    for cid in app.loaded.results:
        dd = app.decided.get(cid)
        if dd is None:
            continue
        c = card_for(app, cid, dd.decision)
        rows.append({"call_id": cid, "label": c.label, "score": round(c.score, 3),
                     "uncertainty": round(c.uncertainty, 3), "family": c.family_label if c.label != "no_alert"
                     or (c.why_not and c.why_not.is_trap) else "", "reason": cd.one_liner(c),
                     "basis": cd.short_basis(c.basis) if c.basis and c.label != "no_alert" else "",
                     "status": "bearbeitet" if cid in judged else "offen", "passages": c.passages})
    rows.sort(key=sort_key)
    return rows


def routed_to(app: AppState, result: CallResult) -> list[str]:
    """Team names a flagged call goes to (config/routing.yaml), [] if it is not routed."""
    try:
        from callguard.ui.panels.ops import notifier

        r = notifier(app).route(result, result.decision)
        return [x.name for x in r.to] if r.routed else []
    except Exception as e:
        log.warning("demo: routing %s failed: %s", result.call_id, e)
        return []


def demo_url() -> str:
    return os.environ.get(DEMO_URL_ENV, DEFAULT_DEMO_URL).rstrip("/")


def outcept_bodies(app: AppState, result: CallResult) -> list[dict[str, str]]:
    """The trigger bodies of the Outcept sink for this call, linking back into the demo app."""
    from urllib.parse import quote

    from callguard.sinks.outcept import OutceptTriggerSink

    pad = app.link_pad

    class DemoSink(OutceptTriggerSink):
        def link(self, call_id: str, start: float) -> str:
            return f"{demo_url()}/?call={quote(call_id, safe='')}&t={max(0, int(start - pad))}"

    return DemoSink(app.ctx, url=OUTCEPT_URL, labels=("alarm", "review")).triggers(result)


def send_outcept(bodies: list[dict[str, str]], url: str = OUTCEPT_URL, timeout: float = 4.0) -> tuple[int, str | None]:
    """POST each trigger; (sent, error). Never raises: the Outcept API being down is a message, not a crash."""
    import httpx

    sent = 0
    for b in bodies:
        try:
            r = httpx.post(url, json=b, timeout=timeout)
        except Exception as e:
            return sent, f"Outcept nicht erreichbar ({type(e).__name__})"
        if r.status_code >= 300:
            return sent, f"Outcept lehnt ab: HTTP {r.status_code}"
        sent += 1
    return sent, None
