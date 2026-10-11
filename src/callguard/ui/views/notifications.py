"""Notifications: what was sent to which desk (``runs/<profile>/outbox.jsonl``), plus a routing preview of
every flagged call under the current sidebar threshold, with "send" for the ones not yet in the outbox."""

from __future__ import annotations

import streamlit as st

from callguard.sinks.notify import read_outbox
from callguard.ui.panels.ops import live_analysis, notifier
from callguard.ui.session import current_app

app = current_app()
n = notifier(app)
st.title("Meldungen")
st.caption("Wer über welchen Anruf informiert wurde (Regeln: `config/routing.yaml`, Personen: "
           "`config/directory.yaml`). Gesendet wird an die Outbox; Webhook/E-Mail per Profil.")

outbox = list(reversed(read_outbox(app.runs_dir)))
teams = sorted({r["name"] for m in outbox for r in m.get("to", [])})
c1, c2 = st.columns([2, 1])
team = c1.selectbox("Stelle", ["alle", *teams])
c2.metric("Meldungen in der Outbox", len(outbox))
shown = [m for m in outbox if team == "alle" or team in {r["name"] for r in m.get("to", [])}]
if not shown:
    st.info("Noch keine Meldungen. Sie entstehen beim Verarbeiten (Sink `notify`) oder unten per *Melden*.",
            icon=":material/inbox:")
for i, m in enumerate(shown[:200]):
    to = ", ".join(r["name"] for r in m.get("to", []))
    cc = ", ".join(r["name"] for r in m.get("cc", []))
    with st.expander(f"{m.get('ts', '')[:16]} · {m['subject']} → {to}" + (f" (cc {cc})" if cc else "")):
        st.code(m.get("body", ""), language=None, wrap_lines=True)
        first = (m.get("passages") or [{}])[0].get("start")
        if m["call_id"] in app.loaded.results and st.button("Anruf öffnen", key=f"cg_nt_open_{i}",
                                                            icon=":material/graphic_eq:"):
            app.goto_call(m["call_id"], first)

st.subheader("Vorschau: Weiterleitung bei aktueller Schwelle")
analysis = live_analysis(app)
sent_keys = {m.get("key") for m in outbox}
rows, pending = [], []
for cid in sorted(app.loaded.results):
    if cid not in app.decided:
        continue
    res = app.live_result(cid)
    r, msg = n.message(res, res.decision, analysis)
    if msg is None:
        continue
    is_sent = msg["key"] in sent_keys
    rows.append({"Anruf": cid, "Label": r.label, "Familien": ", ".join(r.families),
                 "An": ", ".join(x.name for x in r.to), "Cc": ", ".join(x.name for x in r.cc),
                 "Muster": ", ".join(r.patterns), "In Outbox": "ja" if is_sent else "nein"})
    if not is_sent:
        pending.append(msg)
if rows:
    st.dataframe(rows, hide_index=True)
    if pending and st.button(f"{len(pending)} offene Meldung(en) senden", icon=":material/send:"):
        for msg in pending:
            n.send(msg)
        st.rerun()
else:
    st.caption("Bei dieser Schwelle wird kein Anruf weitergeleitet.")
