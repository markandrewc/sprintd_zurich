"""Patterns across calls: advisors who stand out (flag rate, Wilson lower bound vs. population), companies
behind several customers' trade flags, customers flagged repeatedly. Live under the sidebar threshold."""

from __future__ import annotations

import streamlit as st

from callguard import patterns as pt
from callguard.ui.panels.ops import notifier
from callguard.ui.session import current_app

app = current_app()
st.title("Muster über Anrufe")
st.caption("Wer fällt wiederholt auf? Beratung und Kund:in werden aus der Begrüssung erkannt (oder aus den "
           "Metadaten der Aufnahme, falls vorhanden). Ein Muster ist ein Hinweis für Compliance, kein Beweis.")

if not app.loaded.results:
    st.info("Noch keine verarbeiteten Anrufe.", icon=":material/inbox:")
    st.stop()

c1, c2 = st.columns(2)
per_dialogue = c1.toggle("Eine Aufnahme pro Dialog", value=True,
                         help="Die Falldaten enthalten jeden Dialog zweimal (sauber + verrauscht).")
min_calls = c2.number_input("Mindestanzahl Anrufe je Beratung", 2, 20, 3)
n = notifier(app)
summaries = [pt.summarize(r, n.directory, decision=app.decided[cid].decision)
             for cid, r in app.loaded.results.items() if cid in app.decided]
if per_dialogue:
    summaries = pt.one_per_dialogue(summaries)
a = pt.analyze(summaries, min_calls=int(min_calls), directory=n.directory)

m1, m2, m3 = st.columns(3)
m1.metric("Anrufe", a["n_calls"])
m2.metric("Markiert (Alarm/Prüfen)", f"{a['flagged']} ({a['population_flag_rate']:.0%})")
m3.metric("Beratung nicht erkannt", a["unidentified"]["advisor"])

st.subheader("Auffälligkeiten")
if a["flags"]:
    for i, f in enumerate(a["flags"]):
        with st.container(border=True):
            st.markdown(f"**{f['kind']}** · {f['reason']}")
            cols = st.columns(min(len(f["calls"]), 6) or 1)
            for j, cid in enumerate(f["calls"][:6]):
                if cols[j].button(cid, key=f"cg_pt_{i}_{j}"):
                    app.goto_call(cid)
else:
    st.success("Keine Auffälligkeiten über mehrere Anrufe.", icon=":material/check_circle:")

for title, rows in (("Beratung", a["advisors"]), ("Kund:innen", a["customers"]), ("Firmen / Titel", a["companies"])):
    st.subheader(title)
    if not rows:
        st.caption("–")
        continue
    st.dataframe([{"Name": r["name"], "Anrufe": r["calls"], "Alarme": r["alarms"], "Prüfen": r["reviews"],
                   "Quote": r["flag_rate"], "Quote (95%-Untergrenze)": r["flag_rate_lower"],
                   "Ø Score": r["mean_score"], "Familien": ", ".join(f"{k} {v}" for k, v in r["families"].items()),
                   "Anrufe (IDs)": ", ".join(r["call_ids"])} for r in rows], hide_index=True,
                 column_config={"Quote": st.column_config.NumberColumn(format="percent"),
                                "Quote (95%-Untergrenze)": st.column_config.NumberColumn(format="percent")})
