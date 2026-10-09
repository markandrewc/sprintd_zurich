"""Compliance officer UI (Streamlit): inbox, call detail with passages, keyword/criteria editor,
processing and quality view.

Launch: ``uv run streamlit run src/callguard/ui/app.py -- --config local`` (or ``callguard ui``).
``backend`` and ``metrics_view`` hold the logic and import no Streamlit, so they are unit-tested
directly; ``session``/``render`` and the page scripts in ``views/`` only draw.
"""
