"""Audit log: every decision, notification, feedback and configuration save (``runs/<profile>/audit.jsonl``)."""

from __future__ import annotations

import streamlit as st

from callguard import audit
from callguard.ui.session import current_app

app = current_app()
st.title("Audit-Log")
st.caption(f"Nur anhängend geschrieben: `{audit.audit_path(app.runs_dir)}`. Wer hat wann was entschieden, "
           "gemeldet, bewertet oder umkonfiguriert.")
events = audit.read_events(app.runs_dir)
kinds = sorted({e.get("kind", "?") for e in events})
c1, c2 = st.columns([2, 1])
pick = c1.multiselect("Art", kinds, default=kinds)
call = c2.text_input("Anruf-ID enthält")
rows = [e for e in reversed(events) if e.get("kind") in pick and (not call or call in str(e.get("call_id", "")))]
st.metric("Einträge", len(rows))
core = ("ts", "kind", "user", "call_id")
st.dataframe([{"Zeit": e.get("ts"), "Art": e.get("kind"), "Wer": e.get("user"), "Anruf": e.get("call_id"),
               "Detail": ", ".join(f"{k}={v}" for k, v in e.items() if k not in core)[:300]} for e in rows[:2000]],
             hide_index=True)
