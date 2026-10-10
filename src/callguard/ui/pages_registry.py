"""Pages of the officer UI. **Add a page = add one ``PageSpec`` line** (or call ``register_page``).

A page is a Streamlit *page script*: a module whose top-level code draws the page and runs on every
rerun. It gets the shared state (config, engine, sidebar knobs, every loaded + re-decided call) with::

    from callguard.ui.session import current_app
    app = current_app()          # AppState: app.loaded.results, app.decided, app.settings, app.cfg, ...

``module`` is a dotted module path (``callguard.ui.views.inbox``) or a file path; the module is NOT
imported by the registry (scripts would run at import), only located. Pages are shown in ``order``.
Keep this API stable: other teams (routing / feedback / patterns / audit) add their pages here.

Example (ops team)::

    PageSpec("audit", "Audit-Log", ":material/history:", "callguard.ops.ui_audit", order=70)
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageSpec:
    key: str  # stable id, also used by AppState.pages[key] and goto links
    title: str  # German officer wording, short
    icon: str  # ":material/<name>:"
    module: str  # dotted module path of the page script, or a path to a .py file
    order: int = 100  # position in the top navigation (lower = further left)
    url_path: str | None = None  # defaults to key
    default: bool = False  # the landing page (exactly one)
    section: str | None = None  # optional navigation group; None = top level

    @property
    def url(self) -> str:
        return self.url_path or self.key

    def path(self) -> Path:
        """Locate the page script without importing it."""
        if self.module.endswith(".py") or "/" in self.module:
            return Path(self.module).resolve()
        spec = importlib.util.find_spec(self.module)
        if spec is None or not spec.origin:
            raise ModuleNotFoundError(f"UI page module not found: {self.module}")
        return Path(spec.origin)


_V = "callguard.ui.views."

PAGES: list[PageSpec] = [
    PageSpec("inbox", "Eingang", ":material/inbox:", _V + "inbox", order=10, default=True),
    PageSpec("detail", "Anruf", ":material/graphic_eq:", _V + "detail", order=20, url_path="call"),
    PageSpec("keywords", "Stichwörter & Kriterien", ":material/tune:", _V + "keywords", order=30),
    PageSpec("process", "Anruf verarbeiten", ":material/upload_file:", _V + "process", order=40),
    PageSpec("quality", "Qualität", ":material/insights:", _V + "quality", order=50),
    PageSpec("experiments", "Experimente", ":material/science:", _V + "experiments", order=60),
    PageSpec("decisions", "Entscheidungshilfe", ":material/balance:", _V + "decisions", order=62),
    PageSpec("team", "Team-Entscheidungen", ":material/groups:", _V + "team", order=63),
    # other teams: add your PageSpec lines below (order 70+), e.g. routing / feedback / patterns / audit
    PageSpec("notifications", "Meldungen", ":material/notifications:", _V + "notifications", order=70),
    PageSpec("feedback", "Feedback & Tuning", ":material/rate_review:", _V + "feedback", order=72),
    PageSpec("patterns", "Muster", ":material/hub:", _V + "patterns", order=74),
    PageSpec("audit", "Audit-Log", ":material/history:", _V + "audit", order=76),
]


def register_page(spec: PageSpec) -> PageSpec:
    """Add (or replace by key) a page at runtime, e.g. from a plugin package imported before the app runs."""
    PAGES[:] = [p for p in PAGES if p.key != spec.key] + [spec]
    return spec


def pages() -> list[PageSpec]:
    """All pages in navigation order; specs whose module cannot be found are skipped (see ``missing``)."""
    out = []
    for p in sorted(PAGES, key=lambda p: (p.order, p.key)):
        try:
            p.path()
        except (ModuleNotFoundError, ImportError, ValueError):
            continue
        out.append(p)
    return out


def missing() -> list[PageSpec]:
    bad = []
    for p in PAGES:
        try:
            if not p.path().exists():
                bad.append(p)
        except (ModuleNotFoundError, ImportError, ValueError):
            bad.append(p)
    return bad
