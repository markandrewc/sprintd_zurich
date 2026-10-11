"""«Was heisst das für Ihr Team?»: each Prüfmodus's measured rates turned into daily workload.

Inputs (officer): calls per day N, expected share of conspicuous calls p, minutes per review. Per mode, with the
CV false-alarm rate FAR and flag recall R (each with its 95 % interval, see :mod:`callguard.ui.modes`)::

    Prüfungen / Tag        = N * (p * R + (1 - p) * FAR)       (every flagged call: alarm or review)
    davon echte Fälle      = N * p * R
    Fehlalarme / Tag       = N * (1 - p) * FAR
    verpasst / Monat       = N * p * (1 - R) * Arbeitstage
    Personentage / Tag     = Prüfungen * Minuten / 60 / Stunden pro Tag

Ranges: the lower end uses the lower ends of R and FAR, the upper end the upper ends (for misses: the upper end
of R gives the lower end). The rates come from 48 synthetic dev calls with 54 % positives; the officer's
prevalence differs, which is exactly why the mode is a choice. Arithmetic is pure; :func:`render` draws the panel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from callguard.ui.modes import ModeMetrics, ModeState

if TYPE_CHECKING:
    import altair as alt

WORKDAYS_PER_MONTH = 21
HOURS_PER_DAY = 8.0


@dataclass(frozen=True)
class Range:
    value: float
    lo: float
    hi: float


@dataclass(frozen=True)
class Workload:
    mode: str
    label: str
    reviews: Range  # calls flagged per day (alarm + review)
    true_cases: Range  # of which truly conspicuous
    false_alarms: Range
    missed_month: Range
    person_days: Range  # full-time reviewers needed


def workload(m: ModeMetrics, *, calls: float, prevalence: float, minutes: float, mode: str = "", label: str = "",
             workdays: int = WORKDAYS_PER_MONTH, hours: float = HOURS_PER_DAY) -> Workload:
    if not 0.0 <= prevalence <= 1.0:
        raise ValueError(f"prevalence must be within 0..1, got {prevalence}")
    if calls < 0 or minutes < 0 or hours <= 0:
        raise ValueError("calls and minutes must be >= 0, hours > 0")
    p, r, f = prevalence, m.recall, m.far

    def rev(rec: float, far: float) -> float:
        return calls * (p * rec + (1 - p) * far)

    reviews = Range(rev(r.value, f.value), rev(r.lo, f.lo), rev(r.hi, f.hi))
    true = Range(calls * p * r.value, calls * p * r.lo, calls * p * r.hi)
    fa = Range(calls * (1 - p) * f.value, calls * (1 - p) * f.lo, calls * (1 - p) * f.hi)
    missed = Range(*(calls * p * (1 - rec) * workdays for rec in (r.value, r.hi, r.lo)))
    pdays = Range(*(x * minutes / 60.0 / hours for x in (reviews.value, reviews.lo, reviews.hi)))
    return Workload(mode=mode, label=label, reviews=reviews, true_cases=true, false_alarms=fa, missed_month=missed,
                    person_days=pdays)


def all_workloads(state: ModeState, **kw: Any) -> list[Workload]:
    return [workload(state.metrics[m.id], mode=m.id, label=m.label, **kw) for m in state.spec.modes
            if m.id in state.metrics]


def approx(x: float) -> str:
    """Round for prose: 287 -> 290, 16.9 -> 17, 2.34 -> 2.3."""
    if x < 0.05:
        return "0"
    if x >= 100:
        return f"{int(round(x, -1)):,}".replace(",", "'")
    if x >= 10:
        return f"{round(x):.0f}"
    return f"{x:.1f}".replace(".0", "") if x >= 1 else f"{x:.1f}"


def span(r: Range) -> str:
    return f"{approx(r.lo)}–{approx(r.hi)}"


def sentence(w: Workload, prevalence: float) -> str:
    share = f"{100 * prevalence:.1f}".rstrip("0").rstrip(".")
    return (f"Bei {share} % Anteil bedeutet «{w.label}» etwa **{approx(w.reviews.value)} Prüfungen pro Tag** "
            f"(Spanne {span(w.reviews)}), davon ~{approx(w.true_cases.value)} echte Fälle; rund "
            f"{approx(w.missed_month.value)} auffällige Anrufe pro Monat bleiben unentdeckt "
            f"(Spanne {span(w.missed_month)}). Das sind ~{approx(w.person_days.value)} Personentage pro Tag.")


# --------------------------------------------------------------------------------------------
# chart + panel
# --------------------------------------------------------------------------------------------

SELECTED, OTHER, INK, INK_2 = "#2a78d6", "#b8b7b1", "#0b0b0b", "#52514e"


def chart(rows: list[Workload], current: str) -> "alt.Chart":
    """Horizontal bars (Prüfungen pro Tag) with 95 % range whiskers; the chosen mode in the accent colour and
    named «(gewählt)» on the axis, so the highlight is never colour alone."""
    import altair as alt
    import pandas as pd

    df = pd.DataFrame([{
        "Modus": w.label + (" (gewählt)" if w.mode == current else ""), "gewählt": w.mode == current,
        "Prüfungen": round(w.reviews.value, 1), "von": round(w.reviews.lo, 1), "bis": round(w.reviews.hi, 1),
        "echte Fälle": round(w.true_cases.value, 1), "Fehlalarme": round(w.false_alarms.value, 1),
        "verpasst/Monat": round(w.missed_month.value, 1), "Personentage": round(w.person_days.value, 2),
        "Text": approx(w.reviews.value),
    } for w in rows])
    order = list(df["Modus"])
    y = alt.Y("Modus:N", sort=order, title=None, axis=alt.Axis(labelLimit=260, labelFontSize=12, ticks=False,
                                                                 domain=False))
    tip = ["Modus:N", alt.Tooltip("Prüfungen:Q", title="Prüfungen pro Tag", format=",.0f"),
           alt.Tooltip("von:Q", title="95 %-Spanne von", format=",.0f"),
           alt.Tooltip("bis:Q", title="95 %-Spanne bis", format=",.0f"),
           alt.Tooltip("echte Fälle:Q", title="davon echte Fälle", format=",.1f"),
           alt.Tooltip("Fehlalarme:Q", title="Fehlalarme pro Tag", format=",.0f"),
           alt.Tooltip("verpasst/Monat:Q", title="verpasst pro Monat", format=",.1f"),
           alt.Tooltip("Personentage:Q", title="Personentage pro Tag", format=",.1f")]
    xmax = max([float(df["bis"].max() or 0.0), 1.0]) * 1.12
    x = alt.X("Prüfungen:Q", title="Prüfungen pro Tag (Balken) mit 95 %-Spanne",
              scale=alt.Scale(domain=[0, xmax]), axis=alt.Axis(format=",.0f", grid=True, gridOpacity=0.35))
    bars = alt.Chart(df).mark_bar(height=alt.RelativeBandSize(0.55), cornerRadiusEnd=4).encode(
        x=x, y=y, tooltip=tip,
        color=alt.condition("datum.gewählt", alt.value(SELECTED), alt.value(OTHER)))
    err = alt.Chart(df).mark_errorbar(ticks=alt.MarkConfig(size=10), color=INK, thickness=1.5).encode(
        x=alt.X("von:Q", title=""), x2="bis:Q", y=y, tooltip=tip)
    text = alt.Chart(df).mark_text(align="left", dx=6, dy=-10, fontSize=11, color=INK_2).encode(
        x="bis:Q", y=y, text="Text:N")
    return alt.layer(bars, err, text).properties(height=alt.Step(44))


def render(app: Any) -> None:
    """The panel (Streamlit). ``app`` is the UI AppState; nothing is drawn without mode metrics."""
    import pandas as pd
    import streamlit as st

    state: ModeState | None = getattr(app, "modes", None)
    with st.expander("Was heisst das für Ihr Team?", icon=":material/groups:"):
        if state is None or not state.metrics:
            st.caption("Keine Messwerte zu den Prüfmodi gefunden (Experiment fehlt und kein Schnappschuss).")
            return
        c1, c2, c3 = st.columns(3)
        calls = c1.number_input("Anrufe pro Tag", min_value=0, max_value=1_000_000, value=2000, step=100,
                                key="cg_wl_calls")
        share = c2.slider("Erwarteter Anteil auffälliger Anrufe", 0.1, 10.0, value=1.0, step=0.1, format="%.1f %%",
                          key="cg_wl_share", help="Wie viele Anrufe im Betrieb wirklich auffällig sind (geschätzt).")
        minutes = c3.number_input("Minuten pro Prüfung", min_value=1, max_value=120, value=6, step=1,
                                  key="cg_wl_minutes")
        p = float(share) / 100.0
        rows = all_workloads(state, calls=float(calls), prevalence=p, minutes=float(minutes))
        current = next((w for w in rows if w.mode == state.current), rows[0] if rows else None)
        if current is None:
            return
        st.markdown(sentence(current, p))
        st.altair_chart(chart(rows, state.current), width="stretch")
        unavailable = {mid for mid, a in state.avail.items() if not a.ok}
        st.dataframe(pd.DataFrame([{
            "Prüfmodus": w.label + (" (gewählt)" if w.mode == state.current else "")
                         + (" · hier nicht verfügbar" if w.mode in unavailable else ""),
            "Prüfungen/Tag": approx(w.reviews.value), "Spanne": span(w.reviews),
            "echte Fälle/Tag": approx(w.true_cases.value), "Fehlalarme/Tag": approx(w.false_alarms.value),
            "verpasst/Monat": f"{approx(w.missed_month.value)} ({span(w.missed_month)})",
            "Personentage/Tag": f"{approx(w.person_days.value)} ({span(w.person_days)})",
        } for w in rows]), hide_index=True, width="stretch")
        ref = state.metrics.get(state.current) or next(iter(state.metrics.values()))
        wilson = any(m.far.method == "wilson" or m.recall.method == "wilson" for m in state.metrics.values())
        st.caption(
            f"Raten gemessen auf {ref.n_calls} synthetischen Dev-Anrufen mit {100 * ref.prevalence:.0f} % auffälligen "
            f"Fällen (Kreuzvalidierung, Schwelle je Fold auf den anderen Folds gewählt; 95 %-Intervalle"
            + (", bei 0 Fehlern Wilson-Intervall statt Bootstrap" if wilson else "") + "). "
            "Im Betrieb ist der Anteil auffälliger Anrufe ein anderer – genau deshalb wählt die Compliance-Stelle "
            f"den Modus. Prüfungen = Alarme + Prüfen-Fälle. Annahmen: {WORKDAYS_PER_MONTH} Arbeitstage pro Monat, "
            f"{HOURS_PER_DAY:.0f} Stunden pro Personentag. Quelle: {ref.source}.")
