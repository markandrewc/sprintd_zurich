"""Extra panels on the call-detail page. **Add a panel = add one ``Panel`` line** (or ``register_panel``).

A panel is a function ``render(result, session) -> None`` that draws with Streamlit:

- ``result``: the ``CallResult`` of the open call, with ``result.decision`` replaced by the *live*
  decision under the current sidebar knobs (threshold, band, weights, families). The decision the
  pipeline stored is ``session.decided[result.call_id].stored``.
- ``session``: the ``AppState`` (``callguard.ui.session``): ``.cfg``, ``.ctx``, ``.settings``,
  ``.all_families``, ``.loaded``, ``.decided``, ``.family_label(fid)``, ``.result_dir(call_id)``,
  ``.goto_call(call_id, t)``.

``render`` may be a callable or a ``"module:function"`` string (imported lazily, so a panel module may
import Streamlit and the UI helpers freely without import cycles). Panels are drawn in ``order`` below
the built-in sections, each in its own expander; an exception in one panel is shown in that panel only.
Keep this API stable: other teams (routing / feedback / patterns / audit) add their panels here.

Example (ops team)::

    Panel("feedback", "Rückmeldung", "callguard.ops.ui_feedback:render", icon=":material/rate_review:", order=60)
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

RenderFn = Callable[[Any, Any], None]


@dataclass(frozen=True)
class Panel:
    key: str  # stable id
    title: str  # German officer wording, short
    render: RenderFn | str  # callable or "module:function"
    icon: str | None = None  # ":material/<name>:"
    order: int = 100  # lower = higher on the page
    expanded: bool = False  # expander open by default
    when: Callable[[Any, Any], bool] | None = None  # optional (result, session) -> show this panel?

    def resolve(self) -> RenderFn:
        if callable(self.render):
            return self.render
        mod, _, fn = str(self.render).partition(":")
        if not fn:
            raise ValueError(f"panel {self.key}: render must be 'module:function', got {self.render!r}")
        return getattr(importlib.import_module(mod), fn)

    def visible(self, result: Any, session: Any) -> bool:
        if self.when is None:
            return True
        try:
            return bool(self.when(result, session))
        except Exception:
            return False


PANELS: list[Panel] = [
    # built-in sections of the detail page are drawn by views/detail.py itself.
    # other teams: add your Panel lines below, e.g.
    # Panel("routing", "Weiterleitung", "callguard.ops.ui_routing:render", icon=":material/alt_route:", order=50),
    Panel("routing", "Weitergeleitet an", "callguard.ui.panels.ops:routed_to", icon=":material/alt_route:", order=50,
          when=lambda r, s: r.decision.label != "no_alert"),
    Panel("feedback", "Rückmeldung", "callguard.ui.panels.ops:feedback", icon=":material/rate_review:", order=55,
          expanded=True),
    Panel("entities", "Personen & Firmen", "callguard.ui.panels.ops:entities", icon=":material/badge:", order=60),
    Panel("provenance", "Herkunft & Audit", "callguard.ui.panels.ops:provenance", icon=":material/fingerprint:",
          order=90),
]


def register_panel(key: str, title: str, render: RenderFn | str | None = None, *, icon: str | None = None,
                   order: int = 100, expanded: bool = False,
                   when: Callable[[Any, Any], bool] | None = None) -> Any:
    """Register a panel; usable directly or as a decorator::

        @register_panel("notes", "Notizen", icon=":material/edit_note:")
        def render(result, session): ...
    """

    def add(fn: RenderFn | str) -> RenderFn | str:
        PANELS[:] = [p for p in PANELS if p.key != key] + [
            Panel(key, title, fn, icon=icon, order=order, expanded=expanded, when=when)]
        return fn

    return add(render) if render is not None else add


def panels() -> list[Panel]:
    return sorted(PANELS, key=lambda p: (p.order, p.key))
