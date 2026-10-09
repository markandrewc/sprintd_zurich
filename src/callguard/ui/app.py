"""callguard compliance officer UI.

    uv run streamlit run src/callguard/ui/app.py -- --config local [--set paths.runs_dir=...]

or ``CALLGUARD_ARGS="--config local"`` in the environment. Reads the CallResults the ``json_dir`` sink
writes to ``runs/<profile>/<call_id>/result.json`` and re-decides them live under the sidebar knobs;
ASR and LLM checks never rerun for a threshold change.

Deep links from alert triggers: ``/?call=<call_id>&t=<seconds>`` open the call at that moment.
"""

from __future__ import annotations

import streamlit as st

from callguard.ui.session import bootstrap

st.set_page_config(layout="wide", page_title="callguard", page_icon=":material/shield:")

app = bootstrap()
page = st.navigation(list(app.pages.values()), position="top")
if page.url_path == app.pages["inbox"].url_path and st.query_params.get("call"):
    st.switch_page(app.pages["detail"], query_params=st.query_params.to_dict())
page.run()
