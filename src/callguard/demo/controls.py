"""«Wie streng?»: Alarmschwelle + Prüfmodus, shared by «Fälle» and «Regeln & Einstellungen» (same widget keys,
values kept for the session), plus the measured consequences of each mode and the workload sentence."""

from __future__ import annotations

from typing import Any

import streamlit as st

from callguard.demo import state as ds
from callguard.ui import modes as md
from callguard.ui import workload as wl

WORKLOAD = {"calls": 2000, "prevalence": 0.01, "minutes": 6}


def threshold_slider(app: Any) -> None:
    s = app.settings
    st.slider("Alarmschwelle", 0.0, 1.0, step=0.01, key=ds.THRESHOLD_KEY, persist_state="session",
              help="Ab diesem Score löst ein Anruf Alarm aus; knapp darunter geht er zur Prüfung an einen Menschen. "
                   "Wirkt sofort auf alle Anrufe (keine Spracherkennung, kein Sprachmodell).")
    st.caption(f"Alarm ab **{s.threshold:.2f}** · Prüfen ab **{max(0.0, s.review_floor):.2f}** · Standard "
               f"{app.defaults['threshold']:.2f}")


def mode_control(app: Any, *, details: bool = False) -> None:
    """The Prüfmodus picker; ``details``: every mode's measured consequence and the unavailable ones' reason."""
    modes = app.modes
    if modes is None:
        st.caption("Prüfmodi sind in diesem Profil nicht eingerichtet.")
        return
    by = {m.id: m for m in modes.spec.modes}
    st.segmented_control(
        "Prüfmodus", ds.available_modes(modes), key=ds.MODE_KEY, required=True, format_func=lambda k: by[k].label,
        persist_state="session", on_change=ds.on_mode_change,
        args=(str(app.runs_root), app.source.key, str(app.runs_dir), ds.profile_threshold(app)),
        help="Wie streng Sherlock Phones entscheidet. Die Wahl gilt für dieses Profil und wird im Audit-Log vermerkt.")
    cur = by.get(app.settings.mode or modes.spec.default)
    if cur is not None and not details:
        note = md.consequence_short(modes.metrics.get(cur.id))
        st.caption(cur.text + (f" Gemessen: {note}." if note else ""))
    off = [m for m in modes.spec.modes if not modes.avail.get(m.id, md.Availability(True)).ok]
    if details:
        for m in modes.spec.modes:
            mm = modes.metrics.get(m.id)
            mark = "**" if cur is not None and m.id == cur.id else ""
            st.markdown(f"{mark}{m.label}{mark}" + (" · :gray-badge[hier nicht verfügbar]" if m in off else "")
                        + f"  \n:small[{m.text} {md.consequence(mm)}]")
        some = next(iter(modes.metrics.values()), None)
        if some is not None:
            st.caption(f"Gemessen auf {some.n_calls} Dev-Anrufen (Kreuzvalidierung). Quelle: {some.source}.")
    if off:
        st.caption(":material/block: " + ", ".join(f"«{m.label}»" for m in off) + " brauchen die Zweitmeinung "
                   "eines zweiten Modells; für diese Anrufe nicht verfügbar.")


def workload_sentence(app: Any) -> str | None:
    modes = app.modes
    mode_id = app.settings.mode or (modes.spec.default if modes else None)
    m = modes.metrics.get(mode_id) if modes is not None and mode_id else None
    if m is None:
        return None
    w = wl.workload(m, calls=WORKLOAD["calls"], prevalence=WORKLOAD["prevalence"], minutes=WORKLOAD["minutes"],
                    mode=mode_id, label=modes.spec.get(mode_id).label)
    return wl.sentence(w, WORKLOAD["prevalence"])


WORKLOAD_NOTE = ("Annahmen: 2000 Anrufe pro Tag, 1 % davon auffällig, 6 Minuten pro Prüfung; Raten aus den Fallanrufen "
                 "(Kreuzvalidierung). Im Betrieb ist der Anteil auffälliger Anrufe ein anderer.")
