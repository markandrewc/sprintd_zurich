"""Compliance officer UI (Streamlit, German officer wording): Eingang (inbox), Anruf (call detail with evidence
timeline, passages, "Warum Prüfen?" / "Warum kein Alarm?"), Stichwörter & Kriterien, Anruf verarbeiten,
Qualität (dev split + holdout log), Experimente (runs/experiments/*/summary.json).

Launch: ``uv run callguard ui -c <profile>``. Extension points (keep stable, other teams use them):
``pages_registry.PAGES`` (add a page = one ``PageSpec`` line) and ``panels.PANELS`` (detail-page panels,
``render(result, session)``). ``backend``, ``explain``, ``sources`` and ``metrics_view`` import no
Streamlit and are unit-tested directly; ``session``/``render`` and the page scripts in ``views/`` draw.
"""
