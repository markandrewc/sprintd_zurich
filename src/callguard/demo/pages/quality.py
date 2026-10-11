"""Qualität: how often callguard raises a false alarm and how often it misses a case, with 95 % intervals, on
the case's dev calls and on the external test set test50 (shown side by side, never pooled), and what that
means for the team's daily workload."""

from __future__ import annotations

import streamlit as st

from callguard.demo import quality as qd
from callguard.ui import workload as wl
from callguard.ui.session import current_app

app = current_app()


@st.cache_data(show_spinner="Testsatz wird ausgewertet …", ttl=600)
def _test50(runs_root: str) -> qd.Rates | None:
    return qd.test50_rates(runs_root)


st.title("Qualität")
st.caption("Markiert heisst: Alarm oder Prüfen, ein Mensch hört zu. **Fehlalarme** = harmlose Anrufe, die trotzdem "
           "markiert wurden. **Verpasst** = auffällige Anrufe, die ohne Markierung durchgingen. Die Balken zeigen "
           "das 95 %-Intervall: so genau wissen wir es bei dieser Anzahl Anrufe.")

modes = app.modes
mode_id = app.settings.mode or (modes.spec.default if modes else None)
dev_metrics = modes.metrics.get(mode_id) if modes is not None and mode_id else None
mode_label = modes.spec.get(mode_id).label if modes is not None and mode_id in modes.spec.ids else ""
dev = qd.dev_rates(dev_metrics, mode_label) if dev_metrics is not None else None
ext = _test50(str(app.runs_root))
sets = [x for x in (dev, ext) if x is not None]

if not sets:
    st.info("Auf diesem Rechner liegen keine Messwerte (weder Experimente noch der externe Testsatz).",
            icon=":material/info:")
else:
    cols = st.columns(len(sets), gap="large")
    for col, r in zip(cols, sets):
        with col, st.container(border=True):
            st.markdown(f"#### {r.title}")
            st.caption(f"{r.n_calls} Anrufe · {r.note}")
            a, b = st.columns(2)
            a.metric("Fehlalarme", qd.pct(r.far.value), border=False,
                     help=f"{r.far.k} von {r.far.n} harmlosen Anrufen markiert.")
            a.caption(f"95 %-KI {100 * r.far.lo:.0f}–{100 * r.far.hi:.0f} % · {r.far.k} von {r.far.n}")
            b.metric("Verpasst", qd.pct(r.miss.value), border=False,
                     help=f"{r.miss.k} von {r.miss.n} auffälligen Anrufen nicht markiert.")
            b.caption(f"95 %-KI {100 * r.miss.lo:.0f}–{100 * r.miss.hi:.0f} % · {r.miss.k} von {r.miss.n}")
            if r.key == "test50":
                st.markdown(":blue-badge[:material/lock: externer Testsatz, nie zum Tunen verwendet]")
    st.altair_chart(qd.chart(sets), width="content")
    st.caption("Punkt = gemessener Wert, Linie = 95 %-Intervall (Bootstrap über Dialoge; Wilson-Intervall, wo "
               "null Fehler auftreten). Die zwei Datensätze werden nie zusammengezählt.")
    if ext is None:
        st.caption(":material/hourglass_empty: Der externe Testsatz test50 ist auf diesem Rechner noch nicht "
                   "ausgewertet (runs/test50/experiments/test50/…).")

if dev_metrics is not None:
    w = wl.workload(dev_metrics, calls=2000, prevalence=0.01, minutes=6, mode=mode_id or "", label=mode_label)
    with st.container(border=True):
        st.markdown("**Was heisst das für Ihr Team?**")
        st.markdown(wl.sentence(w, 0.01))
        st.caption("Annahmen: 2000 Anrufe pro Tag, 1 % davon auffällig, 6 Minuten pro Prüfung. Raten aus den "
                   "Fallanrufen (Kreuzvalidierung); im Betrieb ist der Anteil auffälliger Anrufe ein anderer.")

with st.expander("Woher die Zahlen stammen", icon=":material/source:"):
    for r in sets:
        st.markdown(f"- **{r.title}**: {r.source}")
    st.markdown("- Fallanrufe: synthetische Gespräche des Falls, nur der Dev-Teil; der Holdout wird pro Kandidat "
                "einmal ausgewertet und protokolliert.\n- test50: 100 Anrufe (50 Dialoge, sauber und verrauscht, "
                "8 Dialekt-Stimmen), vorregistriert, feste Schwelle aus den Dev-Daten.")
