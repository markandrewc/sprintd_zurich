"""Einstellungen: what callguard looks for and how it decides, in three tabs.

* Regeln: all rules (instant, with undo) and the «+ Neue Regel» wizard with the KI-Assistent.
* Fakten: the questions to the AI, «+ Neuer Fakt» wizard, four-eyes proposals; advanced reader settings on demand.
* Stichwörter: the keyword list (unchanged).
Below: «Erweitert» with the score Alarmschwelle (the main knob on «Fälle» is the Sicherheit der KI).
"""

from __future__ import annotations

import streamlit as st

from callguard import audit
from callguard.demo import controls as ctl
from callguard.demo import keyword_editor, settings_facts, settings_rules
from callguard.ui.session import current_app

app = current_app()
ss = st.session_state
ss.setdefault("dm_user", audit.current_user())

head, name = st.columns([4, 1.4], vertical_alignment="bottom")
head.title("Einstellungen")
name.text_input("Ihr Name", key="dm_user", help="Wird bei jeder Änderung im Audit-Log vermerkt (Autor / Freigabe).")
for msg in ss.pop("dm_set_messages", []):
    st.toast(msg, icon=":material/check_circle:")

opener = st.query_params.get("neu")  # deep link: ?neu=regel / ?neu=fakt opens the wizard
if opener in ("regel", "fakt"):
    del st.query_params["neu"]
    if opener == "regel":
        settings_rules._open()
    else:
        settings_facts._open(None, None, settings_facts.fu.live_policy(app))

t_rules, t_facts, t_kw = st.tabs([":material/rule: Regeln", ":material/fact_check: Fakten", ":material/label: Stichwörter"])
with t_rules:
    settings_rules.render(app)
with t_facts:
    settings_facts.render(app)
with t_kw:
    keyword_editor.keywords_section(app)

st.divider()
with st.expander("Erweitert: Score-Alarmschwelle", icon=":material/tune:"):
    st.caption("Die Hauptsteuerung ist die «Sicherheit der KI» auf «Fälle». Die Alarmschwelle wirkt danach auf den "
               "Gesamtscore (Fakten + leichte Stichwort-/Muster-Hinweise); meist nicht nötig.")
    ctl.threshold_slider(app)
