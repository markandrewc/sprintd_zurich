"""Small Streamlit/Altair building blocks shared by the pages: label badges, passage cards, the transcript,
score charts. One place for colours and wording so every page reads the same."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from callguard.types import CallResult, Decision, Passage, Transcript, fmt_ts
from callguard.ui.backend import LABEL_TEXT, passage_clip, short_label

LABEL_BADGE = {"alarm": "red", "review": "orange", "no_alert": "green"}
LABEL_ICON = {"alarm": ":material/notifications_active:", "review": ":material/person_search:",
              "no_alert": ":material/check_circle:"}
LABEL_HEX = {"alarm": "#d64545", "review": "#e09b2d", "no_alert": "#3f9c5f"}
LABEL_TINT = {"alarm": ("#fde4e4", "#9b1c1c"), "review": ("#fff1d6", "#8a5300"), "no_alert": ("#e3f4e8", "#1e6b3a")}
ROLE_TEXT = {"advisor": "Advisor", "customer": "Customer"}
SCORE_BAR = "#6b7a8f"  # neutral slate: the status column carries the red/amber/green, not every bar
CHECK_PALETTE = ["#4e79a7", "#f28e2b", "#59a14f", "#b07aa1", "#76b7b2", "#edc948", "#9c755f", "#bab0ac"]

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]<>()#+\-.!|$~:])")


def esc(text: str) -> str:
    """Escape Markdown (and Streamlit's ``$`` LaTeX / ``:directive[]`` syntax) in transcript text."""
    return _MD_SPECIAL.sub(r"\\\1", text or "")


def score_column(label: str | None = None, **kw: Any) -> Any:
    return st.column_config.ProgressColumn(label, format="%.2f", min_value=0.0, max_value=1.0, color=SCORE_BAR, **kw)


def label_text(label: str) -> str:
    return LABEL_TEXT.get(label, label)


def label_md(label: str) -> str:
    """Inline badge for st.markdown, e.g. in captions and lists."""
    return f":{LABEL_BADGE.get(label, 'gray')}-badge[{LABEL_ICON.get(label, '')} {label_text(label)}]"


def label_badge(label: str) -> None:
    st.badge(label_text(label).upper(), icon=LABEL_ICON.get(label), color=LABEL_BADGE.get(label, "gray"))


def span(start: float, end: float) -> str:
    return f"{fmt_ts(start)}–{fmt_ts(end)}"


def pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def num(x: float | None, nd: int = 2) -> str:
    return "–" if x is None else f"{x:.{nd}f}"


def style_labels(df: pd.DataFrame, *columns: str) -> Any:
    """Tinted status cells (red/amber/green); text stays readable for colour-blind officers."""
    inv = {label_text(k): k for k in LABEL_TINT}

    def css(v: Any) -> str:
        key = inv.get(v, v)
        if key not in LABEL_TINT:
            return ""
        bg, fg = LABEL_TINT[key]
        return f"background-color: {bg}; color: {fg}; font-weight: 600"

    return df.style.map(css, subset=list(columns))


# --------------------------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------------------------


def _rules(threshold: float, floor: float, y_text: float = 6) -> alt.LayerChart:
    """Solid threshold line, dashed review-band start; labels on opposite sides so they never collide."""
    data = pd.DataFrame([{"x": threshold, "what": f"alarm ≥ {threshold:.2f}", "side": "right"},
                         {"x": floor, "what": f"review ≥ {floor:.2f}", "side": "left"}])
    rule = alt.Chart(data).mark_rule(color="#555", strokeWidth=1.5).encode(
        x="x:Q", strokeDash=alt.condition(alt.datum.side == "right", alt.value([1, 0]), alt.value([4, 3])))
    right = alt.Chart(data[data["side"] == "right"]).mark_text(align="left", dx=4, fontSize=11, color="#444").encode(
        x="x:Q", y=alt.value(y_text), text="what:N")
    left = alt.Chart(data[data["side"] == "left"]).mark_text(align="right", dx=-4, fontSize=11, color="#777").encode(
        x="x:Q", y=alt.value(y_text), text="what:N")
    return alt.layer(rule, right, left)


_TICKS = [round(0.1 * i, 1) for i in range(11)]
_X_AXIS = alt.Axis(values=_TICKS, format=".1f", grid=True)


def score_strip(rows: list[dict], threshold: float, floor: float) -> alt.LayerChart:
    """Every call as a dot on the 0..1 score axis, one lane per label: moving the threshold visibly moves
    dots between lanes."""
    data = pd.DataFrame(rows or [], columns=["call_id", "label", "score", "family", "uncertainty"])
    data["Status"] = [label_text(x) for x in data["label"]]
    order = [label_text(x) for x in LABEL_HEX]
    dots = alt.Chart(data).mark_circle(size=90, opacity=0.85, stroke="white", strokeWidth=0.8).encode(
        x=alt.X("score:Q", scale=alt.Scale(domain=[0, 1]), title="Call score", axis=_X_AXIS),
        y=alt.Y("Status:N", sort=order, title=None, scale=alt.Scale(domain=order)),  # lanes stay put when empty
        yOffset=alt.YOffset("jitter:Q"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=order, range=list(LABEL_HEX.values())), legend=None),
        tooltip=[alt.Tooltip("call_id:N", title="Call"), "Status:N", alt.Tooltip("score:Q", format=".2f"),
                 alt.Tooltip("uncertainty:Q", format=".2f"), alt.Tooltip("family:N", title="Family")],
    ).transform_calculate(jitter="(random() - 0.5) * 22")
    return alt.layer(dots, _rules(threshold, floor, y_text=-8)).properties(height=alt.Step(48))


def family_chart(decision: Decision, threshold: float, floor: float, can_alarm: set[str] | None = None) -> alt.LayerChart:
    """Fused score per family (bar) with each check's own score (tick): which check pushed where."""
    fams = [f for f in decision.families.values()]
    bars, ticks = [], []
    for f in fams:
        name = short_label(f.label)
        status = ("alarm" if f.score >= threshold else "review" if f.score >= floor else "no_alert")
        if can_alarm is not None and f.family not in can_alarm:
            status = "info"
        bars.append({"Family": name, "Fused score": f.score, "Uncertainty": f.uncertainty, "status": status})
        for check, s in f.per_check.items():
            ticks.append({"Family": name, "Check": check, "Score": s, "Verdict": f.verdicts.get(check) or "–"})
    bdf = pd.DataFrame(bars, columns=["Family", "Fused score", "Uncertainty", "status"])
    tdf = pd.DataFrame(ticks, columns=["Family", "Check", "Score", "Verdict"])
    order = list(bdf.sort_values("Fused score", ascending=False)["Family"])
    y = alt.Y("Family:N", sort=order, title=None, axis=alt.Axis(labelLimit=220))
    bar = alt.Chart(bdf).mark_bar(height=alt.RelativeBandSize(0.6), opacity=0.35, cornerRadiusEnd=2).encode(
        x=alt.X("Fused score:Q", scale=alt.Scale(domain=[0, 1]), title="Score", axis=_X_AXIS), y=y,
        color=alt.Color("status:N", scale=alt.Scale(domain=["alarm", "review", "no_alert", "info"],
                                                    range=[LABEL_HEX["alarm"], LABEL_HEX["review"],
                                                           LABEL_HEX["no_alert"], "#9e9e9e"]), legend=None),
        tooltip=["Family:N", alt.Tooltip("Fused score:Q", format=".2f"), alt.Tooltip("Uncertainty:Q", format=".2f")],
    )
    fused = alt.Chart(bdf).mark_tick(thickness=3, size=22, color="#222").encode(
        x="Fused score:Q", y=y, tooltip=["Family:N", alt.Tooltip("Fused score:Q", format=".2f")])
    checks = sorted(tdf["Check"].unique()) if len(tdf) else []
    tick = alt.Chart(tdf).mark_point(filled=True, size=70, opacity=0.95).encode(
        x="Score:Q", y=y,
        color=alt.Color("Check:N", scale=alt.Scale(domain=checks, range=CHECK_PALETTE[:max(1, len(checks))]),
                        legend=alt.Legend(orient="bottom", title="Check")),
        shape=alt.Shape("Check:N", scale=alt.Scale(domain=checks), legend=alt.Legend(orient="bottom", title="Check")),
        tooltip=["Family:N", "Check:N", alt.Tooltip("Score:Q", format=".2f"), "Verdict:N"],
    )
    return alt.layer(bar, fused, tick, _rules(threshold, floor, y_text=-8)).resolve_scale(
        color="independent").properties(height=alt.Step(34))


# --------------------------------------------------------------------------------------------
# Passages and transcript
# --------------------------------------------------------------------------------------------


def play_clip(result: CallResult, passage: Passage, result_dir: Path, pad: float) -> None:
    clip = passage_clip(result, passage, result_dir, pad)
    if clip is None:
        st.caption(":material/volume_off: Recording not available on this machine.")
        return
    try:
        st.audio(clip.path, start_time=int(clip.start), end_time=int(clip.end) + 1 if clip.end else None)
    except Exception as e:
        st.caption(f":material/volume_off: Audio could not be loaded ({type(e).__name__}).")
        return
    if clip.note:
        st.caption(clip.note)


def passage_card(index: int, p: Passage, result: CallResult, result_dir: Path, pad: float, *,
                 linked: bool = False) -> None:
    with st.container(border=True):
        left, right = st.columns([3, 2], gap="medium")
        with left:
            fam = short_label(p.family_label or p.family)
            st.markdown(f"#### {index}. `{span(p.start, p.end)}` · {esc(fam)}")
            tags = [f":gray-badge[Score {p.score:.2f}]"] + [f":blue-badge[{esc(c)}]" for c in p.checks]
            if linked:
                tags.insert(0, ":violet-badge[:material/link: linked from alert]")
            st.markdown(" ".join(tags))
            if p.text:
                st.markdown("> " + esc(p.text.strip()))
            if p.reasons:
                st.markdown("\n".join(f"- {esc(r)}" for r in p.reasons))
        with right:
            st.caption(f"Snippet {span(max(0.0, p.start - pad), p.end + pad)} (incl. {pad:.0f} s context)")
            play_clip(result, p, result_dir, pad)


def _hits_by_segment(result: CallResult) -> dict[str, list[str]]:
    """Matched keyword text per segment, to bold it in the transcript."""
    out: dict[str, list[str]] = {}
    for cr in result.checks.values():
        for f in cr.findings:
            matched = f.detail.get("matched_text") if isinstance(f.detail, dict) else None
            if matched and isinstance(matched, str):
                for sid in f.segment_ids:
                    out.setdefault(sid, []).append(matched)
    return out


def _bold_terms(text: str, terms: Iterable[str]) -> str:
    low = text.lower()
    spans: list[tuple[int, int]] = []
    for term in {t.strip().lower() for t in terms if t and t.strip()}:
        start = 0
        while (i := low.find(term, start)) >= 0:
            spans.append((i, i + len(term)))
            start = i + len(term)
    if not spans:
        return esc(text)
    spans.sort()
    merged = [list(spans[0])]
    for a, b in spans[1:]:
        if a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    out, pos = [], 0
    for a, b in merged:
        out.append(esc(text[pos:a]))
        out.append(f"**{esc(text[a:b])}**")
        pos = b
    out.append(esc(text[pos:]))
    return "".join(out)


def transcript_markdown(transcript: Transcript, passages: list[Passage], result: CallResult) -> str:
    fam_of: dict[str, list[str]] = {}
    for p in passages:
        for sid in p.segment_ids:
            fam_of.setdefault(sid, [])
            name = short_label(p.family_label or p.family)
            if name not in fam_of[sid]:
                fam_of[sid].append(name)
    hits = _hits_by_segment(result)
    lines = []
    for s in transcript.segments:
        role = ROLE_TEXT.get(s.role) or (s.speaker or "Speaker ?")
        text = _bold_terms(s.text.strip(), hits.get(s.id, []))
        prefix = f"`{fmt_ts(s.start)}` **{esc(role)}**"
        if s.id in fam_of:
            badges = " ".join(f":red-badge[{esc(n)}]" for n in fam_of[s.id])
            lines.append(f"{prefix} {badges} :orange-background[{text}]")
        else:
            lines.append(f"{prefix} {text}")
    return "\n\n".join(lines)


def kv_table(items: Mapping[str, Any]) -> None:
    st.dataframe(pd.DataFrame({"": list(items.keys()), "Value": [str(v) for v in items.values()]}),
                 hide_index=True, width="stretch")
