"""Glue for the demo tabs «Fakten» and «Regeln»: the live fact policy + rule table, the officer's try-outs (session
only, never written until applied), instant re-decision of every stored call (:func:`callguard.fact_policy.redecide`,
memoised), the version store, and the per-fact strip chart.

Governance, made explicit in both tabs:
* RULES change instantly: «Übernehmen» writes the live table at once (:meth:`VersionStore.apply_rules`: version entry,
  audit event, one-click undo). No second person.
* FACTS (questions, new / removed facts, readers, default bands and combination) need the AI to answer again and a
  second person's approval (draft -> :meth:`VersionStore.approve`).
* Trying out a band, a combination or a rule is always instant and only visible to the officer trying it.
"""

from __future__ import annotations

import copy
from collections import OrderedDict
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard.cache import stable_hash
from callguard.checks.facts import DEFAULT_TABLE, PolicyTable
from callguard.config import ROOT
from callguard.policy_versions import VersionStore
from callguard.ui.session import AppState

TRY_KEY = "dm_fp_try"  # the officer's try-out fact policy (dict), session only
LABEL_DE = {"alarm": "Alarm", "review": "Prüfen", "no_alert": "Kein Alarm"}
VALUE_DE = fpol.VALUE_DE
GRID_JSON = ROOT / "research" / "evidence" / "dual_facts_grid.json"

# dataviz reference palette (light): categorical slot 1 / 2 for the two readers, neutral band
READER_COLORS = ("#2a78d6", "#eb6834")
BAND_FILL = "#d9d8d3"
INK_MUTED = "#52514e"


# --------------------------------------------------------------------------------------------
# live state
# --------------------------------------------------------------------------------------------


def fusion(app: AppState) -> Any:
    """The two_readers fusion with rule ``policy`` of this profile, else None (other profiles: tabs explain)."""
    pipe = getattr(app.engine, "pipeline", None)
    f = getattr(pipe, "fusion", None) if pipe is not None else getattr(app.engine, "fusion", None)
    return f if getattr(f, "rule", None) == "policy" else None


def table_path(app: AppState) -> Path:
    f = fusion(app)
    rel = str(getattr(f, "policy_table", None) or next(
        (c.get("policy_table") for c in app.cfg.checks if c.get("type") == "facts" and c.get("policy_table")),
        DEFAULT_TABLE))
    return Path(rel) if Path(rel).is_absolute() else ROOT / rel


def live_doc(app: AppState) -> dict[str, Any]:
    return pe.load_doc(table_path(app))


def live_policy(app: AppState) -> fpol.FactPolicy:
    f = fusion(app)
    return f.fact_policy() if f is not None else fpol.default_policy()


def try_policy(app: AppState) -> fpol.FactPolicy:
    """The policy the officer is trying out (session), else the live one."""
    raw = st.session_state.get(TRY_KEY)
    if raw:
        try:
            return fpol.parse_fact_policy(raw)
        except fpol.FactPolicyError:
            st.session_state.pop(TRY_KEY, None)
    return live_policy(app)


def set_try(policy: fpol.FactPolicy | None) -> None:
    if policy is None:
        st.session_state.pop(TRY_KEY, None)
    else:
        st.session_state[TRY_KEY] = policy.as_dict()


def extra_paths(app: AppState) -> dict[str, Path]:
    from callguard.routing import DEFAULT_ROUTING

    notify = next((s for s in app.cfg.sinks if s.get("type") == "notify"), {})
    routing = Path(str(notify.get("routing") or DEFAULT_ROUTING))
    out = {"criteria": app.ctx.path("criteria"), "keywords": app.ctx.path("keywords"),
           "routing": routing if routing.is_absolute() else ROOT / routing}
    tuning = app.cfg.paths.tuning
    if tuning:
        out["tuning"] = Path(tuning) if Path(tuning).is_absolute() else ROOT / tuning
    f = fusion(app)
    if f is not None:
        out["fact_policy"] = fpol.resolve_path(f.fact_policy_path)
    return out


def store(app: AppState) -> VersionStore:
    """Same files as the Regelwerk page's store (ui/views/rules.py), so versions stay one history."""
    return VersionStore(table_path(app), audit_dir=app.runs_dir, extras=extra_paths(app))


# --------------------------------------------------------------------------------------------
# instant re-decision (memoised per policy + table + knobs + loaded results)
# --------------------------------------------------------------------------------------------

_MEMO: OrderedDict[str, dict[str, fpol.CallOutcome]] = OrderedDict()


def outcomes(app: AppState, policy: fpol.FactPolicy, doc: dict[str, Any] | PolicyTable | None = None
             ) -> dict[str, fpol.CallOutcome]:
    """Every stored call decided under ``policy`` and the rule table ``doc`` (default: live), with the live knobs
    (threshold, Prüfarten on/off). No LLM; ~0.1 s for 60 calls, memoised."""
    f = fusion(app)
    if f is None:
        return {}
    doc = live_doc(app) if doc is None else doc
    table = doc if isinstance(doc, PolicyTable) else pe.validate(doc)
    overrides = app.settings.overrides()
    fams = app.families if app.all_families else None
    key = stable_hash({"p": policy.key(), "t": {k: v.raw for k, v in table.families.items()},
                       "sig": app.loaded.signature, "o": overrides, "f": [x.id for x in fams or []]})
    hit = _MEMO.get(key)
    if hit is not None:
        _MEMO.move_to_end(key)
        return hit
    families = fams or app.engine.families()
    out = fpol.redecide(app.loaded.results, table.families, policy,
                        lambda r, c: f.decide_checks(r.transcript, c, families, overrides), **f.scoring)
    _MEMO[key] = out
    while len(_MEMO) > 48:
        _MEMO.popitem(last=False)
    return out


def rule_hits(outs: dict[str, fpol.CallOutcome], family: str) -> dict[str | None, list[str]]:
    """rule id -> calls where that rule decided the family (first match)."""
    hits: dict[str | None, list[str]] = {}
    for cid, o in sorted(outs.items()):
        v = o.families.get(family)
        if v is not None:
            hits.setdefault(v.rule, []).append(cid)
    return hits


def effect_md(before: dict[str, fpol.CallOutcome], after: dict[str, fpol.CallOutcome]) -> tuple[str, list]:
    eff = fpol.effect(before, after)
    return fpol.effect_line(eff), eff["changed"]


def changed_table(changed: list[tuple[str, str, str]]) -> pd.DataFrame:
    return pd.DataFrame([{"Anruf": c, "vorher": LABEL_DE[a], "nachher": LABEL_DE[b]} for c, a, b in changed])


def call_link(call_id: str) -> str:
    return f"[{call_id}](anruf?call={call_id})"


# --------------------------------------------------------------------------------------------
# the dev grid (research/evidence/dual_facts_grid.json, written by `callguard dualfacts eval`)
# --------------------------------------------------------------------------------------------


@st.cache_data(show_spinner=False, ttl=60)
def _grid(path: str, mtime: float) -> dict[str, Any]:
    import json

    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return {}


def grid() -> dict[str, Any]:
    p = GRID_JSON
    return _grid(str(p), p.stat().st_mtime) if p.is_file() else {}


def knob_text(kind: str, key: str) -> str | None:
    """A measured one-liner for a knob setting (dev only) from the grid's ``ui_text``, if present."""
    t = (grid().get("ui_text") or {})
    if isinstance(t.get(kind), dict):
        return t[kind].get(key)
    return t.get(key) if isinstance(t.get(key), str) else None


# --------------------------------------------------------------------------------------------
# the strip chart: each reader's p(ja) over all calls, the band shaded (dataviz: one value axis, thin dots,
# readers named on the rows, band = neutral fill, text in ink colours, hover tooltip per dot)
# --------------------------------------------------------------------------------------------


def strip_chart(answers: list[fpol.FactAnswer], policy: fpol.FactPolicy, family: str, fact: str) -> Any:
    """Two rows (reader A on top, reader B below) on one p(ja) axis; rows are a quantitative position (0, 1) plus a
    small deterministic jitter, so the layers share one y scale."""
    import altair as alt

    ra, rb_ = policy.reader(0, family, fact), policy.reader(1, family, fact)
    rows = []
    for i, a in enumerate(answers):
        rf = fpol.resolve_fact(policy, family, fact, a.pa, a.pb)
        jitter = ((i * 37) % 11 - 5) / 22  # deterministic, keeps dots of one reader apart (±0.23 of a row)
        for row, (r, py, v) in enumerate(((ra, a.ya, rf.va), (rb_, a.yb, rf.vb))):
            if py is not None:
                rows.append({"Leser": r.label, "row": row + jitter, "p": py, "Anruf": a.call_id,
                             "Wert": VALUE_DE[v], "Ergebnis": VALUE_DE[rf.value]})
    df = pd.DataFrame(rows)
    bands = pd.DataFrame([{"Leser": r.label, "lo": r.lo, "hi": r.hi, "y0": i - 0.38, "y1": i + 0.38}
                          for i, r in enumerate((ra, rb_)) if r.mode == "band"])
    three = pd.DataFrame([{"Leser": r.label, "x": r.decide_at, "y0": i - 0.38, "y1": i + 0.38}
                          for i, r in enumerate((ra, rb_)) if r.mode != "band"])
    xs = alt.Scale(domain=[0, 1])
    ys = alt.Scale(domain=[1.55, -0.55], nice=False)  # reader A on top
    label_expr = f"datum.value == 0 ? '{ra.label}' : datum.value == 1 ? '{rb_.label}' : ''"
    y_axis = alt.Axis(values=[0, 1], labelExpr=label_expr, labelColor="#0b0b0b", labelFontWeight="bold",
                      labelFontSize=12, ticks=False, domain=False, grid=False, title=None)
    layers = []
    if not bands.empty:
        layers.append(alt.Chart(bands).mark_rect(color=BAND_FILL, opacity=0.7, cornerRadius=4).encode(
            x=alt.X("lo:Q", scale=xs), x2="hi:Q", y=alt.Y("y0:Q", scale=ys, axis=y_axis), y2="y1:Q",
            tooltip=[alt.Tooltip("Leser:N"), alt.Tooltip("lo:Q", title="nein bis", format=".2f"),
                     alt.Tooltip("hi:Q", title="ja ab", format=".2f")]))
    if not three.empty:
        layers.append(alt.Chart(three).mark_rule(color=INK_MUTED, strokeWidth=1, strokeDash=[3, 2]).encode(
            x=alt.X("x:Q", scale=xs), y=alt.Y("y0:Q", scale=ys, axis=y_axis), y2="y1:Q",
            tooltip=[alt.Tooltip("Leser:N"), alt.Tooltip("x:Q", title="ja ab p(ja) / nein ab p(nein)", format=".2f")]))
    if not df.empty:
        layers.append(alt.Chart(df).mark_circle(size=64, opacity=0.9, stroke="#fcfcfb", strokeWidth=1).encode(
            x=alt.X("p:Q", scale=xs, title="p(ja)",
                    axis=alt.Axis(values=[0, 0.25, 0.5, 0.75, 1], format=".2f", grid=False, labelColor=INK_MUTED,
                                  titleColor=INK_MUTED, tickColor=BAND_FILL, domainColor=BAND_FILL)),
            y=alt.Y("row:Q", scale=ys, axis=y_axis),
            color=alt.Color("Leser:N", scale=alt.Scale(domain=[ra.label, rb_.label], range=list(READER_COLORS)),
                            legend=None),
            tooltip=[alt.Tooltip("Anruf:N"), alt.Tooltip("Leser:N"), alt.Tooltip("p:Q", title="p(ja)", format=".2f"),
                     alt.Tooltip("Wert:N", title="Wert dieses Lesers"), alt.Tooltip("Ergebnis:N", title="zusammen")]))
    return alt.layer(*layers).properties(height=110).configure_view(stroke=None)


# --------------------------------------------------------------------------------------------
# rule builder helpers (pure)
# --------------------------------------------------------------------------------------------


def cond_text(fact: str, value: str, negate: bool) -> str:
    return f"{fact} {'!=' if negate else '='} {value}"


def build_when(conds: list[tuple[str, str, bool]], join: str) -> str:
    if not conds:
        return "true"
    j = " and " if join == "and" else " or "
    return j.join(cond_text(*c) for c in conds)


def with_rule(doc: dict[str, Any], family: str, rule: dict[str, Any], position: int | None = None
              ) -> tuple[dict[str, Any], int]:
    cand = copy.deepcopy(doc)
    pos = pe.add_rule(cand, family, rule, position)
    return cand, pos
