"""Frames + the Altair chart for the page "Team-Entscheidungen" (``callguard.ui.views.team``), built from the result
of :func:`callguard.candidates.analyse` (``runs/candidates/candidates.json``). Pure functions, testable without
Streamlit.

Chart (dataviz method): "tuned vs other condition per candidate" is a before -> after per item, so a **dumbbell**
in one hue, two shades: tuned = blue step 600 ``#184f95`` (filled circle), the other condition = blue step 300
``#6da7ec`` (diamond), 95% intervals as thin rules in the same shades, a gray connector, the chance line at 0.5.
Validator (light surface): CVD dE 28.8, normal 28.5, contrast WARN for the light shade (2.44:1) -> relief by the
second shape, the legend and the matrix as table view. Text stays in ink colours.
"""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd

from callguard import candidates as cd

DARK, LIGHT, CONNECT, GRID, INK = "#184f95", "#6da7ec", "#a3a3a3", "#e4e3df", "#0b0b0b"
GEN_BG = "background-color: #f0efec"  # recessive surface tint that groups the generalisation columns
TUNED = "abgestimmt (Dev)"
CONDITIONS = {"reworded": "umformulierte Fragen", "blind": "blinde Tabelle", "rerecorded": "neu aufgenommenes Audio"}

GEN_PREFIX = "Generalisierung · "
NUM_COLS = {  # sortable view: column -> (key, percent)
    "Flag-AUC": ("auc", False), "Fehlalarme (CV)": ("false_alarm_rate", True), "Verpasst (CV)": ("miss_rate", True),
    "Prüf-Recall": ("review_recall", True), "Exakt 3 Klassen": ("accuracy", True),
    GEN_PREFIX + "AUC umformuliert": ("reworded", False), GEN_PREFIX + "AUC blinde Tabelle": ("blind", False),
    GEN_PREFIX + "AUC neu aufgenommen": ("rerecorded", False), "Beleg hit@1": ("hit1", True),
    "s/Anruf": ("cost", False),
}
DROP_COLS = {GEN_PREFIX + "Δ umformuliert": "reworded", GEN_PREFIX + "Δ blind": "blind",
             GEN_PREFIX + "Δ neu aufgenommen": "rerecorded"}
TEXT_COLS = ["Kandidat", "Flag-AUC [KI]", "Fehlalarme (CV)", "Verpasst (CV)", "Prüf-Recall", "Exakt 3 Klassen",
             "gepaart vs. Champion", GEN_PREFIX + "AUC umformuliert", GEN_PREFIX + "Δ umformuliert",
             GEN_PREFIX + "AUC blinde Tabelle", GEN_PREFIX + "Δ blind", GEN_PREFIX + "AUC neu aufgenommen",
             GEN_PREFIX + "Δ neu aufgenommen", "Beleg hit@1", "Passagen", "s/Anruf", "Hardware", "Lizenz",
             "E2E getestet"]


def _strip_md(s: str) -> str:
    return s.replace("**", "")


def text_frame(result: dict[str, Any]) -> pd.DataFrame:
    """The matrix as in docs/TEAM_OPTIONS.md: values with CIs, "≈ Champion", pending states as text."""
    rows = cd.matrix_rows(result, bold=False)
    df = pd.DataFrame([[_strip_md(x) for x in r] for r in rows], columns=TEXT_COLS)
    df.insert(1, "Gruppe", [c.get("group") or "" for c in cd.visible(result)])
    return df


def number_frame(result: dict[str, Any]) -> pd.DataFrame:
    """Sortable view: plain numbers (percent as 0-100), empty where pending; a status column says why."""
    out = []
    for c in cd.visible(result):
        row: dict[str, Any] = {"Kandidat": c.get("label") or c["id"], "Gruppe": c.get("group") or ""}
        for col, (key, pct) in NUM_COLS.items():
            v = (cd.value(c, key) or {}).get("value")
            row[col] = None if v is None else (100 * v if pct else v)
        for col, slot in DROP_COLS.items():
            d = ((c.get("gen") or {}).get(slot) or {}).get("drop") or {}
            row[col] = d.get("diff")
        row["gepaart vs. Champion"] = "Referenz" if c["id"] == result.get("reference") else cd.vs_text(c)
        missing = [f"{cd.SLOT_LABELS[s]}: {cd.STATUS_TEXT[st]}" for s, _, st in cd.slot_states(c)
                   if st in ("running", "pending")]
        row["Daten"] = "; ".join(missing) or "vollständig"
        out.append(row)
    return pd.DataFrame(out)


def best_cells(result: dict[str, Any], df: pd.DataFrame) -> dict[str, list[int]]:
    """Row positions of the best value per column (as :func:`candidates.best_marks`) for the styler."""
    best = result.get("best") or {}
    labels = [c.get("label") or c["id"] for c in cd.visible(result)]
    ids = [c["id"] for c in cd.visible(result)]
    key_to_cols = {"auc": ["Flag-AUC", "Flag-AUC [KI]"]}
    for col, (key, _) in NUM_COLS.items():
        key_to_cols.setdefault(key, []).append(col)
    out: dict[str, list[int]] = {}
    for key, m in best.items():
        rows = [i for i, cid in enumerate(ids) if cid in m["ids"] and labels[i] in set(df["Kandidat"])]
        for col in key_to_cols.get(key, []):
            if col in df.columns:
                out[col] = rows
    return out


def style(df: pd.DataFrame, result: dict[str, Any]) -> Any:
    """Bold the best value per column, tint the generalisation columns (visual group)."""
    best = best_cells(result, df)
    gen = [c for c in df.columns if c.startswith(GEN_PREFIX)]

    def col_style(s: pd.Series) -> list[str]:
        css = []
        for i in range(len(s)):
            parts = []
            if s.name in gen:
                parts.append(GEN_BG)
            if i in best.get(s.name, []):
                parts.append("font-weight: 700")
            css.append("; ".join(parts))
        return css

    return df.style.apply(col_style, axis=0)


def dumbbell_frame(result: dict[str, Any], condition: str = "reworded") -> pd.DataFrame:
    """Two rows per candidate with a tuned AUC: tuned and ``condition`` (missing condition -> status text only)."""
    rows = []
    for c in cd.visible(result):
        if c.get("kind") not in ("candidate", None) or not c.get("tuned"):
            continue
        lab = c.get("short") or c.get("label") or c["id"]
        a = c["tuned"]["auc"]
        g = (c.get("gen") or {}).get(condition) or {}
        drop = cd.fmt_delta(g.get("drop")) if g.get("drop") else cd.slot_text(c, condition)
        base = {"Kandidat": lab, "Zustand": cd.slot_text(c, condition) if not g.get("auc") else "da",
                "Δ zum eigenen Dev": drop, "gegen Champion": cd.fmt_delta(g.get("vs_ref")) if g.get("vs_ref") else "–"}
        rows.append({**base, "Bedingung": TUNED, "AUC": a.get("value"), "von": a.get("lo"), "bis": a.get("hi")})
        x = g.get("auc") or {}
        if x.get("value") is not None:
            rows.append({**base, "Bedingung": CONDITIONS[condition], "AUC": x["value"], "von": x.get("lo"),
                         "bis": x.get("hi")})
    df = pd.DataFrame(rows)
    if len(df):
        df["AUC [95%-KI]"] = df.apply(lambda r: cd.fmt_ci({"value": r["AUC"], "lo": r["von"], "hi": r["bis"]}), axis=1)
    return df


def dumbbell_chart(df: pd.DataFrame, condition: str = "reworded") -> alt.LayerChart:
    order = list(dict.fromkeys(df["Kandidat"]))
    cond = CONDITIONS[condition]
    y = alt.Y("Kandidat:N", sort=order, title=None, axis=alt.Axis(labelLimit=260))
    x_scale = alt.Scale(domain=[0.4, 1.0], zero=False, clamp=True)
    color = alt.Color("Bedingung:N", scale=alt.Scale(domain=[TUNED, cond], range=[DARK, LIGHT]),
                      legend=alt.Legend(orient="bottom", title=None))
    shape = alt.Shape("Bedingung:N", scale=alt.Scale(domain=[TUNED, cond], range=["circle", "diamond"]),
                      legend=alt.Legend(orient="bottom", title=None))
    tip = ["Kandidat:N", "Bedingung:N", "AUC [95%-KI]:N", "Δ zum eigenen Dev:N", "gegen Champion:N", "Zustand:N"]
    wide = df.pivot_table(index="Kandidat", columns="Bedingung", values="AUC", aggfunc="first").reset_index()
    connect_df = wide.dropna() if cond in wide.columns else wide.iloc[0:0]
    chance = alt.Chart(pd.DataFrame({"x": [0.5]})).mark_rule(color=GRID, strokeWidth=1).encode(
        x=alt.X("x:Q", scale=x_scale))
    layers = [chance]
    if len(connect_df):
        layers.append(alt.Chart(connect_df.rename(columns={TUNED: "a", cond: "b"})).mark_rule(
            color=CONNECT, strokeWidth=2).encode(x=alt.X("a:Q", scale=x_scale), x2="b:Q", y=y))
    marks = []
    for name, off in ((TUNED, -5), (cond, 5)):  # each condition on its own sub-line, the connector in between
        part = df[df["Bedingung"] == name]
        if not len(part):
            continue
        marks.append(alt.Chart(part.dropna(subset=["von", "bis"])).mark_rule(strokeWidth=2, yOffset=off).encode(
            x=alt.X("von:Q", scale=x_scale, title="Flag-AUC mit 95%-Intervall (0.5 = Zufall)"), x2="bis:Q",
            y=y, color=color, tooltip=tip))
        marks.append(alt.Chart(part).mark_point(filled=True, size=110, stroke="#fcfcfb", strokeWidth=2, opacity=1,
                                                yOffset=off).encode(
            x=alt.X("AUC:Q", scale=x_scale, title="Flag-AUC mit 95%-Intervall (0.5 = Zufall)"), y=y, color=color,
            shape=shape, tooltip=tip))
    pending = df.drop_duplicates("Kandidat")
    pending = pending[pending["Zustand"] != "da"]
    layers += marks
    if len(pending):
        layers.append(alt.Chart(pending.assign(x=1.0)).mark_text(align="right", dx=-2, yOffset=6, fontSize=11, color="#52514e")
                      .encode(x=alt.X("x:Q", scale=x_scale), y=y, text="Zustand:N"))
    return alt.layer(*layers).properties(height=alt.Step(30))


def decision_options(d: dict[str, Any]) -> list[str]:
    return [o.get("name") or f"Option {i + 1}" for i, o in enumerate(d.get("options") or [])]


def comparison_frame(comp: dict[str, Any]) -> pd.DataFrame:
    return pd.DataFrame([{"Thema": r.get("topic", ""), "Unser Ansatz": r.get("ours", ""),
                          "sprintd_zurich": r.get("theirs", ""), "Messung / Beleg": r.get("evidence", ""),
                          "Wirkung": r.get("impact", ""), "Empfehlung": r.get("recommendation", "offen"),
                          "Begründung": r.get("why", "")} for r in comp.get("rows") or []])


def pending_lines(result: dict[str, Any]) -> list[str]:
    return [f"{p['label']}: {cd.SLOT_LABELS[p['slot']]} `{p['ref']}` ({cd.STATUS_TEXT[p['status']]})"
            for p in result.get("pending") or []]
