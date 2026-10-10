"""The demo app (``callguard demo``, port 8502): the officer's showcase, separate from the internal UI.

``app.py`` (entry, navigation, footer) · ``state.py`` (the officer UI's AppState without its sidebar) ·
``pages/`` (Fälle, Anruf prüfen, Einstellungen, Qualität, Anruf verarbeiten; the Regelwerk page is the
officer UI's ``ui/views/rules.py``) · pure, tested building blocks: ``transcript.py`` (synchronised
audio + transcript component), ``card.py`` (decision card), ``review.py`` (reason codes -> labels),
``keywords.py`` (keyword edit effect), ``quality.py`` (rates per dataset), ``media.py`` (audio for the
browser), ``readiness.py`` (are the models reachable).
"""

DEMO_URL_ENV = "CALLGUARD_DEMO_URL"  # base URL of the running demo (Outcept backlinks); set by `callguard demo`
