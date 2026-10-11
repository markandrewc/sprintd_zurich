"""callguard demo app: the showcase for the compliance officer (German, calm, no developer pages).

    uv run callguard demo -c recommended            # http://localhost:8502

Pages: Fälle (worklist + Alarmschwelle + Prüfmodus), Anruf prüfen (audio and transcript in sync, decision
card with both AI readers per fact, review -> training data point), Fakten (the questions to the AI, how the two
readers' answers become ja / nein / unklar: bands + combination with instant effect, disagreements; changing facts
needs four-eyes approval), Regeln (how strict; rule cards, rule builder, AI drafter; applied instantly with undo),
Stichwörter, Qualität (false alarms / misses, dev and external test set separately), Anruf verarbeiten (upload -> decision; needs the GPU host). The internal officer UI
(``callguard ui``, port 8501) is unchanged; both read the same results and stores.

Deep links (Outcept trigger backlinks): ``/?call=<id>&t=<seconds>`` open «Anruf prüfen» at that moment.
"""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from callguard.demo import state as dstate

HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
ACCENT = "#2a78d6"

st.set_page_config(layout="wide", page_title="Sherlock Phones · Anrufprüfung", page_icon=":material/verified_user:",
                   initial_sidebar_state="collapsed")

pages = {
    "cases": st.Page(PAGES / "cases.py", title="Fälle", icon=":material/inbox:", url_path="faelle", default=True),
    "detail": st.Page(PAGES / "call.py", title="Anruf prüfen", icon=":material/graphic_eq:", url_path="anruf"),
    "settings": st.Page(PAGES / "settings.py", title="Einstellungen", icon=":material/tune:", url_path="einstellungen"),
    "quality": st.Page(PAGES / "quality.py", title="Qualität", icon=":material/insights:", url_path="qualitaet"),
    # not in the top bar: reached from «Fälle» («Neuen Anruf prüfen»)
    "process": st.Page(PAGES / "process.py", title="Anruf verarbeiten", icon=":material/upload_file:",
                       url_path="verarbeiten", visibility="hidden"),
}
app = dstate.bootstrap(pages)
page = st.navigation(list(pages.values()), position="top")

info = dstate.models_in_use(app.cfg, app.loaded.results)
st.html(f"""<style>
  .block-container {{ padding-top: 3.2rem; padding-bottom: 4.5rem; max-width: 1480px; }}
  h1 {{ font-weight: 650; letter-spacing: -0.01em; }}
  [data-testid="stMetricValue"] {{ font-weight: 650; }}
  [data-testid="stSidebarCollapsedControl"] {{ display: none; }}
  .cg-footer {{ position: fixed; left: 0; right: 0; bottom: 0; z-index: 999; padding: 6px 24px;
               font: 12px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color: #5f6670;
               background: rgba(255,255,255,0.94); border-top: 1px solid #e3e5e8; text-align: right; }}
  .cg-footer b {{ color: #1b1f24; font-weight: 600; }}
</style>
<div class="cg-footer">Profil <b>{html.escape(info['profile'])}</b> · Sprachmodell <b>{html.escape(info['llm'])}</b>
 · Spracherkennung <b>{html.escape(info['asr'])}</b> · alle Modelle laufen auf eigener Hardware</div>""")

if page.url_path == pages["cases"].url_path and st.query_params.get("call"):
    st.switch_page(pages["detail"], query_params=st.query_params.to_dict())
page.run()
