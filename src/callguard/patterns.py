"""Patterns across calls: the advisor who stands out repeatedly, the same company behind several
customers' trade flags (docs/design/v2_plan.md §3).

``analyze(results)`` -> per advisor / customer / company: calls, alarms, reviews, mean score, families;
plus ``flags``:

* ``repeat_advisor``: the advisor's flag rate (alarm + review) is above the population's even at the
  **Wilson 95% lower bound** (so 1 flag out of 1 call is not a pattern), with at least ``min_calls`` calls.
* ``company_across_customers``: one company appears in trade-flagged calls of >= 2 different customers
  (or of unknown customers in >= 2 calls), the classic tip-chain picture.
* ``repeat_family_customer``: one customer flagged >= 2 times for the same family.

Flags feed routing rules (``pattern: repeat_advisor`` -> compliance desk, cc supervisor). Everything here
reads finished results only; nothing flows back into a decision. On the case data clean and noisy
recordings are the same dialogue, so :func:`one_per_dialogue` keeps one recording each by default.
"""

from __future__ import annotations

import json
import logging
import math
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from callguard.checks.entities import _key, entities_of
from callguard.data import dialogue_of
from callguard.routing import Directory, flagged_families
from callguard.types import CallResult, Decision

log = logging.getLogger("callguard")

FLAG_LABELS = ("alarm", "review")


def wilson_lower(k: int, n: int, z: float = 1.96) -> float:
    """Lower end of the Wilson score interval for k successes in n trials (0 for n = 0)."""
    if n <= 0:
        return 0.0
    p = k / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / denom)


@dataclass
class CallSummary:
    call_id: str
    label: str
    score: float
    families: list[str]
    advisor: str | None = None  # grouping key (directory id or folded name)
    advisor_name: str | None = None
    customer: str | None = None
    customer_name: str | None = None
    companies: dict[str, str] = field(default_factory=dict)  # key -> display name

    @property
    def flagged(self) -> bool:
        return self.label in FLAG_LABELS


def summarize(result: CallResult, directory: Directory | None = None, decision: Decision | None = None) -> CallSummary:
    d = decision or result.decision
    ent = entities_of(result, directory)
    adv, cus = ent.get("advisor") or {}, ent.get("customer") or {}
    return CallSummary(call_id=result.call_id, label=d.label, score=round(d.score, 4),
                       families=flagged_families(d) if d.label in FLAG_LABELS else [],
                       advisor=ent.get("advisor_key"), advisor_name=adv.get("name"),
                       customer=ent.get("customer_key"), customer_name=cus.get("name"),
                       companies={_key(c["name"]): c["name"] for c in ent.get("companies") or [] if c.get("name")})


def one_per_dialogue(results: Sequence[Any]) -> list[Any]:
    """First recording (by call id: K1 before K2) of each case dialogue; other ids pass unchanged.
    Works on CallResults and CallSummaries."""
    seen: set[str] = set()
    out = []
    for r in sorted(results, key=lambda r: r.call_id):
        dlg = dialogue_of(r.call_id)
        if dlg in seen:
            continue
        seen.add(dlg)
        out.append(r)
    return out


def _group(calls: list[CallSummary], key: str, names: dict[str, str]) -> list[dict[str, Any]]:
    by: dict[str, list[CallSummary]] = {}
    for c in calls:
        ks = list(c.companies) if key == "company" else [getattr(c, key)]
        for k in ks:
            if k:
                by.setdefault(k, []).append(c)
    rows = []
    for k, cs in by.items():
        fams: dict[str, int] = {}
        for c in cs:
            for f in c.families:
                fams[f] = fams.get(f, 0) + 1
        flagged = sum(c.flagged for c in cs)
        rows.append({"key": k, "name": names.get(k, k), "calls": len(cs),
                     "alarms": sum(c.label == "alarm" for c in cs), "reviews": sum(c.label == "review" for c in cs),
                     "flagged": flagged, "flag_rate": round(flagged / len(cs), 4),
                     "flag_rate_lower": round(wilson_lower(flagged, len(cs)), 4),
                     "mean_score": round(statistics.fmean(c.score for c in cs), 4), "families": fams,
                     "call_ids": [c.call_id for c in cs],
                     "customers": sorted({c.customer for c in cs if c.customer})})
    return sorted(rows, key=lambda r: (-r["flagged"], -r["mean_score"], r["key"]))


def analyze(items: Iterable[CallResult | CallSummary], *, min_calls: int = 3,
            directory: Directory | None = None) -> dict[str, Any]:
    directory = directory or Directory.load()
    calls = [x if isinstance(x, CallSummary) else summarize(x, directory) for x in items]
    n = len(calls)
    flagged = sum(c.flagged for c in calls)
    pop_rate = flagged / n if n else 0.0
    names: dict[str, str] = {}
    for c in calls:
        if c.advisor and c.advisor_name:
            names.setdefault(c.advisor, c.advisor_name)
        if c.customer and c.customer_name:
            names.setdefault(c.customer, c.customer_name)
        names.update({k: v for k, v in c.companies.items() if k not in names})

    advisors = _group(calls, "advisor", names)
    customers = _group(calls, "customer", names)
    companies = _group(calls, "company", names)
    flags: list[dict[str, Any]] = []
    for a in advisors:
        if a["calls"] >= min_calls and a["flag_rate_lower"] > pop_rate:
            flags.append({"kind": "repeat_advisor", "subject_type": "advisor", "subject": a["key"],
                          "name": a["name"], "calls": a["call_ids"],
                          "reason": f"{a['name']}: {a['flagged']}/{a['calls']} Anrufe markiert; Wilson-Untergrenze "
                                    f"{a['flag_rate_lower']:.0%} > Gesamtquote {pop_rate:.0%}."})
    for co in companies:
        trade = [c for c in calls if co["key"] in c.companies and c.flagged and "trade" in c.families]
        custs = {c.customer for c in trade if c.customer}
        unknown = sum(1 for c in trade if not c.customer)
        if len(custs) + (1 if unknown >= 2 else 0) >= 2:
            flags.append({"kind": "company_across_customers", "subject_type": "company", "subject": co["key"],
                          "name": co["name"], "calls": [c.call_id for c in trade],
                          "reason": f"{co['name']} in Insider-markierten Anrufen von {len(custs)} Kund:innen"
                                    + (f" (+{unknown} unbekannt)" if unknown else "") + "."})
    for cu in customers:
        for fam, k in cu["families"].items():
            if k >= 2:
                flags.append({"kind": "repeat_family_customer", "subject_type": "customer", "subject": cu["key"],
                              "name": cu["name"], "family": fam,
                              "calls": [c.call_id for c in calls if c.customer == cu["key"] and fam in c.families],
                              "reason": f"{cu['name']}: {k}x markiert für {fam}."})
    return {"n_calls": n, "flagged": flagged, "population_flag_rate": round(pop_rate, 4), "min_calls": min_calls,
            "advisors": advisors, "customers": customers, "companies": companies, "flags": flags,
            "unidentified": {"advisor": sum(1 for c in calls if not c.advisor),
                             "customer": sum(1 for c in calls if not c.customer)},
            "calls": [asdict(c) for c in calls]}


def load_variant_results(path: str | Path) -> list[CallResult]:
    """An experiment variant's ``results.jsonl`` (or its directory)."""
    p = Path(path)
    if p.is_dir():
        p = p / "results.jsonl"
    out = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        if line.strip():
            try:
                out.append(CallResult.model_validate(json.loads(line)))
            except Exception as e:
                log.warning("%s:%d skipped: %s", p, i, e)
    return out


def render_markdown(a: dict[str, Any], top: int = 10) -> str:
    lines = [f"# Muster über {a['n_calls']} Anrufe", "",
             f"Markiert (Alarm/Prüfen): {a['flagged']} ({a['population_flag_rate']:.0%}). "
             f"Ohne erkannte Beratung: {a['unidentified']['advisor']}, ohne Kund:in: {a['unidentified']['customer']}.", ""]
    lines += ["## Auffälligkeiten", ""]
    lines += [f"- **{f['kind']}** {f['reason']} ({', '.join(f['calls'])})" for f in a["flags"]] or ["- keine"]
    for title, rows in (("Beratung", a["advisors"]), ("Kund:innen", a["customers"]), ("Firmen", a["companies"])):
        lines += ["", f"## {title}", "", "| Name | Anrufe | Alarme | Prüfen | Quote (95%-Untergrenze) | Ø Score | Familien |",
                  "|---|---|---|---|---|---|---|"]
        lines += [f"| {r['name']} | {r['calls']} | {r['alarms']} | {r['reviews']} | {r['flag_rate']:.0%} "
                  f"({r['flag_rate_lower']:.0%}) | {r['mean_score']:.2f} | "
                  f"{', '.join(f'{k} {v}' for k, v in r['families'].items()) or '-'} |" for r in rows[:top]]
    return "\n".join(lines)
