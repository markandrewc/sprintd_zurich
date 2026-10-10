"""Small Streamlit/Altair building blocks shared by the pages: label badges, passage cards, the evidence
timeline, the transcript, score charts. One place for colours and wording so every page reads the same.

Colours: status colours are reserved for the three labels and always come with an icon and the German
word (Alarm = red, Prüfen = orange, Kein Alarm = grey: no red/green pair for colour-blind officers).
Families take the categorical slots in a fixed order (never cycled); their lane / label carries the
identity too, so colour is never the only cue.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from callguard import misheard as mh
from callguard.types import CallResult, Decision, Family, Passage, Transcript, fmt_ts
from callguard.ui import explain as ex
from callguard.ui.backend import LABEL_TEXT, passage_clip, short_label

LABEL_BADGE = {"alarm": "red", "review": "orange", "no_alert": "gray"}
LABEL_ICON = {"alarm": ":material/notifications_active:", "review": ":material/person_search:",
              "no_alert": ":material/check_circle:"}
LABEL_HEX = {"alarm": "#c62828", "review": "#e69f00", "no_alert": "#7f8790"}
LABEL_TINT = {"alarm": ("#fde2e1", "#8e1b1b"), "review": ("#fff0cc", "#7a4d00"), "no_alert": ("#eceff1", "#37474f")}
ROLE_TEXT = {"advisor": "Beratung", "customer": "Kunde"}
SCORE_BAR = "#6b7a8f"  # neutral slate: the status column carries the colour, not every bar
# categorical slots (dataviz reference palette), status hues (red / orange / yellow) left out on purpose
FAMILY_PALETTE = ["#2a78d6", "#1baf7a", "#e87ba4", "#6250d6", "#008300", "#8c6d31", "#17becf"]
ANNOTATE_ONLY_HEX = "#a3a3a3"
CHECK_PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#6250d6", "#e87ba4", "#008300", "#8c6d31", "#52514e"]
CHECK_SHAPES = ["circle", "square", "triangle-up", "diamond", "cross", "triangle-down", "wedge", "stroke"]
KIND_TEXT = {"alarm_when": "Alarm-Regel", "review_when": "Prüf-Regel", "policy": "Richtlinie",
             "rule": "Regel der Faktentabelle"}

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
    """Tinted status cells; the word itself stays in the cell, so colour is never the only cue."""
    inv = {label_text(k): k for k in LABEL_TINT}

    def css(v: Any) -> str:
        key = inv.get(v, v)
        if key not in LABEL_TINT:
            return ""
        bg, fg = LABEL_TINT[key]
        return f"background-color: {bg}; color: {fg}; font-weight: 600"

    return df.style.map(css, subset=list(columns))


def family_colors(families: Sequence[Family]) -> dict[str, str]:
    """family id -> colour, fixed by the order in the criteria (never by rank or by what is on screen)."""
    out, i = {}, 0
    for f in families:
        if not f.can_alarm:
            out[f.id] = ANNOTATE_ONLY_HEX
            continue
        out[f.id] = FAMILY_PALETTE[i % len(FAMILY_PALETTE)]
        i += 1
    return out


# --------------------------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------------------------


def _rules(threshold: float, floor: float, y_text: float = 6) -> alt.LayerChart:
    """Solid threshold line, dashed review-band start; labels on opposite sides so they never collide."""
    data = pd.DataFrame([{"x": threshold, "what": f"Alarm ab {threshold:.2f}", "side": "right"},
                         {"x": floor, "what": f"Prüfen ab {floor:.2f}", "side": "left"}])
    rule = alt.Chart(data).mark_rule(color="#555", strokeWidth=1.5).encode(
        x="x:Q", strokeDash=alt.condition(alt.datum.side == "right", alt.value([1, 0]), alt.value([4, 3])))
    right = alt.Chart(data[data["side"] == "right"]).mark_text(align="left", dx=4, fontSize=11, color="#444").encode(
        x="x:Q", y=alt.value(y_text), text="what:N")
    left = alt.Chart(data[data["side"] == "left"]).mark_text(align="right", dx=-4, fontSize=11, color="#777").encode(
        x="x:Q", y=alt.value(y_text), text="what:N")
    return alt.layer(rule, right, left)


_TICKS = [round(0.1 * i, 1) for i in range(11)]
_X_AXIS = alt.Axis(values=_TICKS, format=".1f", grid=True)


def score_bars(rows: list[dict], threshold: float, floor: float, step: float = 0.05) -> alt.LayerChart:
    """How many calls fall in each score band (0..1 in ``step`` bins), stacked by their current label, with the
    threshold and review-band lines: moving the threshold recolours bars, so the officer sees what shifts."""
    data = pd.DataFrame(rows or [], columns=["call_id", "label", "score"])
    n_bins = int(round(1 / step))
    data["bin"] = [min(int(float(s or 0) / step), n_bins - 1) for s in data["score"]]
    data["Status"] = [label_text(x) for x in data["label"]]
    agg = data.groupby(["bin", "Status"]).size().reset_index(name="Anrufe")
    agg["von"] = agg["bin"] * step
    agg["bis"] = agg["von"] + step
    agg["Bereich"] = [f"{a:.2f}–{b:.2f}" for a, b in zip(agg["von"], agg["bis"])]
    order = [label_text(x) for x in LABEL_HEX]
    agg["ord"] = [order.index(s) for s in agg["Status"]]
    bars = alt.Chart(agg).mark_bar(stroke="white", strokeWidth=1.5, cornerRadiusTopLeft=3,
                                   cornerRadiusTopRight=3).encode(
        x=alt.X("von:Q", scale=alt.Scale(domain=[0, 1]), title="Score des Anrufs", axis=_X_AXIS),
        x2="bis:Q",
        y=alt.Y("Anrufe:Q", stack="zero", title="Anrufe", axis=alt.Axis(tickMinStep=1, grid=True)),
        color=alt.Color("Status:N", scale=alt.Scale(domain=order, range=list(LABEL_HEX.values())),
                        legend=alt.Legend(orient="top", title=None, symbolType="square")),
        order=alt.Order("ord:Q"),
        tooltip=[alt.Tooltip("Bereich:N", title="Score"), alt.Tooltip("Status:N"),
                 alt.Tooltip("Anrufe:Q")])
    return alt.layer(bars, _rules(threshold, floor)).properties(height=220)


def score_strip(rows: list[dict], threshold: float, floor: float) -> alt.LayerChart:
    """Every call as a dot on the 0..1 score axis, one lane per label: moving the threshold visibly moves
    dots between lanes."""
    data = pd.DataFrame(rows or [], columns=["call_id", "label", "score", "family", "uncertainty"])
    data["Status"] = [label_text(x) for x in data["label"]]
    order = [label_text(x) for x in LABEL_HEX]
    dots = alt.Chart(data).mark_circle(size=90, opacity=0.9, stroke="white", strokeWidth=1).encode(
        x=alt.X("score:Q", scale=alt.Scale(domain=[0, 1]), title="Score des Anrufs", axis=_X_AXIS),
        y=alt.Y("Status:N", sort=order, title=None, scale=alt.Scale(domain=order)),  # lanes stay put when empty
        yOffset=alt.YOffset("jitter:Q"),
        color=alt.Color("Status:N", scale=alt.Scale(domain=order, range=list(LABEL_HEX.values())), legend=None),
        tooltip=[alt.Tooltip("call_id:N", title="Anruf"), "Status:N", alt.Tooltip("score:Q", title="Score", format=".2f"),
                 alt.Tooltip("uncertainty:Q", title="Unsicherheit", format=".2f"),
                 alt.Tooltip("family:N", title="Art")],
    ).transform_calculate(jitter="(random() - 0.5) * 22")
    return alt.layer(dots, _rules(threshold, floor, y_text=-8)).properties(height=alt.Step(48))


def family_chart(decision: Decision, threshold: float, floor: float, can_alarm: set[str] | None = None) -> alt.LayerChart:
    """Fused score per family (bar) with each check's own score (point): which check pushed where."""
    bars, ticks = [], []
    for f in decision.families.values():
        name = short_label(f.label)
        status = ("alarm" if f.score >= threshold else "review" if f.score >= floor else "no_alert")
        if can_alarm is not None and f.family not in can_alarm:
            status = "info"
        hexc = {"alarm": LABEL_HEX["alarm"], "review": LABEL_HEX["review"], "no_alert": LABEL_HEX["no_alert"]}
        bars.append({"Art": name, "Score": f.score, "Unsicherheit": f.uncertainty, "status": status,
                     "fill": hexc.get(status, "#d0d0d0")})
        for check, s in f.per_check.items():
            ticks.append({"Art": name, "Prüfung": check, "Score": s,
                          "Urteil": ex.VERDICT_DE.get(f.verdicts.get(check), "–")})
    bdf = pd.DataFrame(bars, columns=["Art", "Score", "Unsicherheit", "status", "fill"])
    tdf = pd.DataFrame(ticks, columns=["Art", "Prüfung", "Score", "Urteil"])
    order = list(bdf.sort_values("Score", ascending=False)["Art"])
    y = alt.Y("Art:N", sort=order, title=None, axis=alt.Axis(labelLimit=220))
    bar = alt.Chart(bdf).mark_bar(height=alt.RelativeBandSize(0.6), opacity=0.35, cornerRadiusEnd=4).encode(
        x=alt.X("Score:Q", scale=alt.Scale(domain=[0, 1]), title="Score", axis=_X_AXIS), y=y,
        fill=alt.Fill("fill:N", scale=None),  # status colour (own channel: the check legend stays clean)
        tooltip=["Art:N", alt.Tooltip("Score:Q", format=".2f"), alt.Tooltip("Unsicherheit:Q", format=".2f")],
    )
    fused = alt.Chart(bdf).mark_tick(thickness=3, size=22, color="#222").encode(
        x="Score:Q", y=y, tooltip=["Art:N", alt.Tooltip("Score:Q", title="Gesamt", format=".2f")])
    checks = sorted(tdf["Prüfung"].unique()) if len(tdf) else []
    tick = alt.Chart(tdf).mark_point(filled=True, size=80, opacity=0.95, stroke="white", strokeWidth=1).encode(
        x="Score:Q", y=y,
        color=alt.Color("Prüfung:N", scale=alt.Scale(domain=checks, range=CHECK_PALETTE[:max(1, len(checks))]),
                        legend=alt.Legend(orient="bottom", title="Prüfung")),
        shape=alt.Shape("Prüfung:N", scale=alt.Scale(domain=checks, range=CHECK_SHAPES[:max(1, len(checks))]),
                        legend=alt.Legend(orient="bottom", title="Prüfung")),
        tooltip=["Art:N", "Prüfung:N", alt.Tooltip("Score:Q", format=".2f"), "Urteil:N"],
    )
    return alt.layer(bar, fused, tick, _rules(threshold, floor, y_text=-8)).properties(height=alt.Step(34))


_MMSS = "utcFormat(datum.value * 1000, '%M:%S')"


FAMILY_SHAPES = ["circle", "square", "diamond", "triangle-up", "triangle-down", "cross", "wedge"]


def timeline_chart(events: list[dict[str, Any]], passages: list[Passage], duration: float,
                   colors: Mapping[str, str], family_order: Sequence[str], seek: float | None = None,
                   labels: Mapping[str, str] | None = None) -> alt.LayerChart:
    """Evidence timeline: the call as a time axis, one lane per check, a marker per piece of evidence
    (colour + shape = family, size = score) and the passages as numbered shaded bands across all lanes.
    Clicking a marker selects it (selection parameter ``mark``, field ``start``)."""
    labels = labels or {}
    lane = lambda fid: labels.get(fid, fid)  # noqa: E731
    ev = pd.DataFrame(events or [], columns=["check", "family", "family_label", "start", "end", "score", "reason",
                                             "kind", "time"])
    ev["Art"] = [lane(f) for f in ev["family"]]
    used = [f for f in family_order if f in set(ev["family"]) | {p.family for p in passages}]
    dom_f = [lane(f) for f in used] or ["–"]
    rng_f = [colors.get(f, ANNOTATE_ONLY_HEX) for f in used] or [ANNOTATE_ONLY_HEX]
    shp_f = [FAMILY_SHAPES[i % len(FAMILY_SHAPES)] for i in range(len(dom_f))]
    checks = sorted(ev["check"].unique()) if len(ev) else ["–"]
    x_scale = alt.Scale(domain=[0, max(duration, 1.0)], nice=False)
    x_axis = alt.Axis(labelExpr=_MMSS, title="Zeit im Anruf (mm:ss)", tickCount=10, grid=True)
    y = alt.Y("check:N", sort=checks, scale=alt.Scale(domain=checks), title="Prüfung",
              axis=alt.Axis(labelLimit=160))
    fam_color = alt.Color("Art:N", title="Art", scale=alt.Scale(domain=dom_f, range=rng_f),
                          legend=alt.Legend(orient="bottom", symbolOpacity=1))

    pdf = pd.DataFrame([{"Art": lane(p.family), "start": p.start, "end": max(p.end, p.start + 1.0), "n": str(i + 1),
                         "von": fmt_ts(p.start), "bis": fmt_ts(p.end)}
                        for i, p in enumerate(passages)], columns=["Art", "start", "end", "n", "von", "bis"])
    bands = alt.Chart(pdf).mark_rect(opacity=0.15, cornerRadius=4).encode(
        x=alt.X("start:Q", scale=x_scale, axis=x_axis), x2="end:Q",
        color=fam_color,
        tooltip=[alt.Tooltip("n:N", title="Passage"), alt.Tooltip("Art:N", title="Art"),
                 alt.Tooltip("von:N", title="von"), alt.Tooltip("bis:N", title="bis")])
    band_labels = alt.Chart(pdf).mark_text(align="left", baseline="top", dx=4, dy=3, fontSize=11,
                                           fontWeight="bold", color="#52514e").encode(
        x="start:Q", y=alt.value(0), text="n:N")

    pick = alt.selection_point(name="mark", fields=["start"], on="click", clear="dblclick")
    marks = alt.Chart(ev).mark_point(filled=True, opacity=0.95, stroke="white", strokeWidth=1.2).encode(
        x=alt.X("start:Q", scale=x_scale, axis=x_axis), y=y, color=fam_color,
        shape=alt.Shape("Art:N", title="Art", scale=alt.Scale(domain=dom_f, range=shp_f),
                        legend=alt.Legend(orient="bottom", symbolOpacity=1)),
        size=alt.Size("score:Q", scale=alt.Scale(domain=[0, 1], range=[60, 320]), legend=None),
        tooltip=[alt.Tooltip("time:N", title="Zeit"), alt.Tooltip("Art:N", title="Art"),
                 alt.Tooltip("check:N", title="Prüfung"), alt.Tooltip("score:Q", title="Score", format=".2f"),
                 alt.Tooltip("reason:N", title="Begründung")],
    ).add_params(pick)
    layers = [bands, band_labels, marks]
    if seek is not None:
        layers.append(alt.Chart(pd.DataFrame([{"t": seek}])).mark_rule(color="#0b0b0b", strokeWidth=1.5,
                                                                      strokeDash=[3, 2]).encode(x="t:Q"))
    return alt.layer(*layers).properties(height=alt.Step(34))


# --------------------------------------------------------------------------------------------
# Passages and transcript
# --------------------------------------------------------------------------------------------


def play_clip(result: CallResult, passage: Passage, result_dir: Path, pad: float) -> None:
    clip = passage_clip(result, passage, result_dir, pad)
    if clip is None:
        st.caption(":material/volume_off: Aufnahme auf diesem Rechner nicht verfügbar.")
        return
    try:
        st.audio(clip.path, start_time=int(clip.start), end_time=int(clip.end) + 1 if clip.end else None)
    except Exception as e:
        st.caption(f":material/volume_off: Audio konnte nicht geladen werden ({type(e).__name__}).")
        return
    if clip.note:
        st.caption(clip.note)


def _check_support(result: CallResult, p: Passage) -> list[tuple[str, float | None, str | None]]:
    """(check, its family score, its verdict) for every check behind a passage."""
    out = []
    for c in p.checks:
        cr = result.checks.get(c)
        fs = cr.family_scores.get(p.family) if cr else None
        out.append((c, float(fs.score) if fs else None, fs.verdict if fs else None))
    return out


def _split_reason(reason: str, checks: Iterable[str]) -> tuple[str, str]:
    for c in checks:
        if reason.startswith(f"{c}: "):
            return c, reason[len(c) + 2:]
    return "", reason


def passage_card(index: int, p: Passage, result: CallResult, result_dir: Path, pad: float, *,
                 linked: bool = False, family: Family | None = None, color: str | None = None,
                 view_titles: Mapping[str, str] | None = None, misheard_below: float | None = None) -> None:
    """One suspicious passage: family + matched criterion, which checks support it with which score, the
    reasons, what each transcript view says, and the audio snippet. A passage whose lowest ASR segment
    confidence is under ``misheard_below`` gets «möglicherweise verhört — bitte anhören»: its text (and the
    reasons quoting it) may be wrong, the recording decides."""
    conf, low_seg = mh.passage_confidence(result.transcript, p)
    misheard = mh.is_misheard(conf, misheard_below)
    with st.container(border=True):
        left, right = st.columns([3, 2], gap="medium")
        with left:
            fam = short_label(p.family_label or (family.label if family else p.family))
            dot = f"<span style='color:{color}'>●</span> " if color else ""
            st.markdown(f"#### {dot}{index}. {esc(fam)} · `{span(p.start, p.end)}`", unsafe_allow_html=True)
            tags = [f":gray-badge[Stärke {p.score:.2f}]"]
            for c, s, v in _check_support(result, p):
                verdict = f" · {ex.VERDICT_DE.get(v, v)}" if v else ""
                tags.append(f":blue-badge[{esc(c)} {num(s)}{esc(verdict)}]")
            if linked:
                tags.insert(0, ":violet-badge[:material/link: aus dem Alarm-Link]")
            if misheard:
                tags.append(":gray-badge[:material/hearing: möglicherweise verhört]")
            st.markdown(" ".join(tags))
            if misheard:
                st.markdown(f":material/hearing: **Möglicherweise verhört — bitte anhören.** Die Spracherkennung war "
                            f"bei `{low_seg}` unsicher (Sicherheit {conf:.2f}, unter {misheard_below:.2f}); "
                            "der Text unten und die Begründung können falsch sein, die Aufnahme entscheidet.")
            crit = ex.passage_criterion(p, family, result)
            if crit is not None:
                hint = "" if crit.kind in ("rule", "policy") else " (beste Übereinstimmung)"
                st.markdown(f"**Kriterium** · {KIND_TEXT.get(crit.kind, crit.kind)}{hint}: {esc(crit.text)}")
            if p.reasons:
                lines = []
                for r in p.reasons:
                    c, text = _split_reason(r, p.checks)
                    lines.append(f"- **{esc(c)}**: {esc(text)}" if c else f"- {esc(text)}")
                st.markdown("**Begründung**\n" + "\n".join(lines))
            texts = {k: v for k, v in (p.texts or {}).items() if v and v.strip()}
            if len(texts) > 1:
                cols = st.columns(len(texts))
                for col, (view, text) in zip(cols, texts.items()):
                    col.caption((view_titles or {}).get(view, view))
                    col.markdown("> " + esc(text.strip()))
            elif p.text:
                st.markdown("> " + esc(p.text.strip()))
        with right:
            st.caption(f"Ausschnitt {span(max(0.0, p.start - pad), p.end + pad)} (inkl. {pad:.0f} s Kontext)")
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


def transcript_markdown(transcript: Transcript, passages: list[Passage], result: CallResult,
                        by_time: bool = False) -> str:
    """Line per segment; segments of a suspicious passage highlighted with the family badge, keyword hits
    bold. ``by_time``: match passages by audio time (other views have their own segment ids)."""
    fam_of: dict[str, list[str]] = {}
    for p in passages:
        name = short_label(p.family_label or p.family)
        ids = ([s.id for s in transcript.segments if s.end > p.start and s.start < max(p.end, p.start + 1e-3)]
               if by_time else p.segment_ids)
        for sid in ids:
            fam_of.setdefault(sid, [])
            if name not in fam_of[sid]:
                fam_of[sid].append(name)
    hits = {} if by_time else _hits_by_segment(result)
    lines = []
    for s in transcript.segments:
        role = ROLE_TEXT.get(s.role) or (s.speaker or "Sprecher ?")
        text = _bold_terms(s.text.strip(), hits.get(s.id, []))
        prefix = f"`{fmt_ts(s.start)}` **{esc(role)}**"
        if s.id in fam_of:
            badges = " ".join(f":blue-badge[{esc(n)}]" for n in fam_of[s.id])
            lines.append(f"{prefix} {badges} :orange-background[{text}]")
        else:
            lines.append(f"{prefix} {text}")
    return "\n\n".join(lines)


def kv_table(items: Mapping[str, Any]) -> None:
    st.dataframe(pd.DataFrame({"": list(items.keys()), "Wert": [str(v) for v in items.values()]}),
                 hide_index=True, width="stretch")
