"""Per-run app state shared by all pages: launch args, the cached engine, the sidebar knobs and the live
re-decision of every loaded call under those knobs.

``app.py`` builds it once per script run and hands it to the page scripts in ``views/`` through
``st.session_state`` (per browser session, unlike module globals).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import streamlit as st

from callguard.config import AppConfig, load_config
from callguard.types import Family
from callguard.ui import backend as be
from callguard.ui.backend import Decided, Engine, Loaded, UIArgs

APP_KEY = "_callguard_app"
VIEWS = Path(__file__).resolve().parent / "views"
PAGES = {  # key -> (file, title, icon, url_path)
    "inbox": ("inbox.py", "Inbox", ":material/inbox:", "inbox"),
    "detail": ("detail.py", "Call detail", ":material/graphic_eq:", "call"),
    "keywords": ("keywords.py", "Keywords & criteria", ":material/tune:", "keywords"),
    "process": ("process.py", "Process a call", ":material/upload_file:", "process"),
    "quality": ("quality.py", "Quality", ":material/insights:", "quality"),
}


@dataclass
class Settings:
    threshold: float
    review_band: float
    max_uncertainty: float
    weights: dict[str, float] = field(default_factory=dict)
    families_on: list[str] = field(default_factory=list)

    @property
    def review_floor(self) -> float:
        return round(self.threshold - self.review_band, 6)

    def overrides(self) -> dict[str, Any]:
        return {"threshold": self.threshold, "review_band": self.review_band,
                "max_uncertainty": self.max_uncertainty, "weights": dict(self.weights)}


@dataclass
class AppState:
    args: UIArgs
    cfg: AppConfig
    engine: Engine
    defaults: dict[str, float]
    default_weights: dict[str, float]
    settings: Settings
    all_families: list[Family]  # enabled in the criteria
    families: list[Family]  # additionally switched on in the sidebar
    loaded: Loaded
    decided: dict[str, Decided]  # under the sidebar settings
    baseline: dict[str, Decided]  # under the config defaults (for the deltas)
    pages: dict[str, Any] = field(default_factory=dict)

    @property
    def ctx(self):
        return self.engine.ctx

    @property
    def runs_dir(self) -> Path:
        return self.engine.ctx.runs_dir

    @property
    def can_alarm(self) -> set[str]:
        return {f.id for f in self.all_families if f.can_alarm}

    @property
    def snippet_pad(self) -> float:
        try:
            return float(self.cfg.snippets.get("pad", 2.0))
        except (TypeError, ValueError):
            return 2.0

    @property
    def link_pad(self) -> float:
        try:
            return float(self.cfg.snippets.get("link_pad", 10.0))
        except (TypeError, ValueError):
            return 10.0

    @property
    def customized(self) -> bool:
        """True when any sidebar knob differs from the configuration profile."""
        s, d = self.settings, self.defaults
        knobs = ((s.threshold, d["threshold"]), (s.review_band, d["review_band"]),
                 (s.max_uncertainty, d["max_uncertainty"]))
        if any(abs(a - b) > 1e-9 for a, b in knobs):
            return True
        if any(abs(s.weights.get(k, v) - v) > 1e-9 for k, v in self.default_weights.items()):
            return True
        return len(self.families) != len(self.all_families)

    def rows(self) -> list[dict[str, Any]]:
        return be.inbox_rows(self.loaded, self.decided, self.all_families, self.baseline, self.settings.weights)

    def family_label(self, fid: str) -> str:
        return next((be.short_label(f.label) for f in self.all_families if f.id == fid), fid)

    def goto_call(self, call_id: str, t: float | None = None) -> None:
        params = {"call": call_id}
        if t is not None:
            params["t"] = str(int(t))
        st.switch_page(self.pages["detail"], query_params=params)


def current_app() -> AppState:
    app = st.session_state.get(APP_KEY)
    if app is None:
        st.error("Start the UI through its entry point: `uv run streamlit run src/callguard/ui/app.py -- --config local`")
        st.stop()
    return app


@st.cache_resource(show_spinner="Loading configuration and plugins…")
def _engine(config: str, sets: tuple[str, ...], no_cache: bool) -> tuple[AppConfig, Engine]:
    cfg = load_config(config, list(sets))
    return cfg, Engine(cfg, use_cache=not no_cache)


@st.cache_data(show_spinner=False, ttl=600)
def ground_truth(data_dir: str) -> dict[str, Any]:
    return be.ground_truth(data_dir)


def reload_everything() -> None:
    st.cache_resource.clear()
    st.cache_data.clear()
    be._DECIDE_MEMO.clear()
    be._SWEEP_MEMO.clear()


# --------------------------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------------------------


def _wkey(check: str) -> str:
    return f"cg_w_{check}"


def _fkey(fid: str) -> str:
    return f"cg_fam_{fid}"


def _reset(defaults: dict[str, float], weights: dict[str, float], families: list[Family]) -> None:
    st.session_state["cg_threshold"] = defaults["threshold"]
    st.session_state["cg_band"] = defaults["review_band"]
    st.session_state["cg_maxunc"] = defaults["max_uncertainty"]
    for name, w in weights.items():
        st.session_state[_wkey(name)] = w
    for f in families:
        st.session_state[_fkey(f.id)] = True


def _sidebar(cfg: AppConfig, engine: Engine, defaults: dict[str, float], weights: dict[str, float],
             families: list[Family], n_calls: int) -> Settings:
    ss = st.session_state
    defaults = {**defaults, "threshold": min(1.0, max(0.0, defaults["threshold"])),
                "max_uncertainty": min(1.0, max(0.0, defaults["max_uncertainty"]))}
    weights = {k: max(0.0, w) for k, w in weights.items()}
    ss.setdefault("cg_threshold", defaults["threshold"])
    ss.setdefault("cg_band", defaults["review_band"])
    ss.setdefault("cg_maxunc", defaults["max_uncertainty"])
    for name, w in weights.items():
        ss.setdefault(_wkey(name), w)
    for f in families:
        ss.setdefault(_fkey(f.id), True)

    with st.sidebar:
        st.markdown("### :material/shield: callguard")
        st.caption(f"Profile **{cfg.name}** · {n_calls} processed call{'s' if n_calls != 1 else ''}")
        if engine.error:
            st.warning(f"Running in fallback mode: {engine.error}. Showing stored decisions where needed.",
                       icon=":material/warning:")

        st.markdown("#### Decision")
        thr = st.slider("Alarm threshold", 0.0, 1.0, step=0.01, key="cg_threshold", persist_state="session",
                        help="A call whose score reaches this value raises an alarm. Lower = more alarms.")
        band = st.slider("Review band", 0.0, max(0.5, defaults["review_band"]), step=0.01, key="cg_band",
                         persist_state="session",
                         help="Calls scoring this far below the threshold go to a human for review.")
        max_unc = st.slider("Max. uncertainty", 0.0, 1.0, step=0.01, key="cg_maxunc", persist_state="session",
                            help="If the checks disagree or are unsure beyond this, the call goes to review "
                                 "instead of being decided automatically.")
        floor = max(0.0, thr - band)
        st.caption(f"Alarm ≥ **{thr:.2f}** · Review ≥ **{floor:.2f}** · config default {defaults['threshold']:.2f}")

        w_out: dict[str, float] = {}
        with st.expander("Check weights", icon=":material/balance:"):
            st.caption("How much each check counts in the fused score. 0 = ignore the check.")
            for name in weights:
                w_out[name] = st.slider(name, 0.0, max(2.0, round(2 * weights[name], 2)), step=0.05,
                                        key=_wkey(name), persist_state="session")
        on: list[str] = []
        with st.expander("Families", icon=":material/category:"):
            st.caption("Switch off a kind of misconduct to leave it out of every decision.")
            for f in families:
                if st.toggle(be.short_label(f.label), key=_fkey(f.id), persist_state="session",
                             help=f"{f.id}" + ("" if f.can_alarm else " · annotates only, never alarms")):
                    on.append(f.id)

        c1, c2 = st.columns(2)
        c1.button("Reset", icon=":material/restart_alt:", on_click=_reset, args=(defaults, weights, families),
                  help="Back to the values of the configuration profile.", width="stretch")
        if c2.button("Reload", icon=":material/refresh:", help="Re-read configuration files and results.",
                     width="stretch"):
            reload_everything()
            st.rerun()
    return Settings(threshold=float(thr), review_band=float(band), max_uncertainty=float(max_unc),
                    weights=w_out, families_on=on)


# --------------------------------------------------------------------------------------------
# Bootstrap
# --------------------------------------------------------------------------------------------


def _pages() -> dict[str, Any]:
    out = {}
    for key, (file, title, icon, url) in PAGES.items():
        out[key] = st.Page(VIEWS / file, title=title, icon=icon, url_path=url, default=(key == "inbox"))
    return out


def bootstrap() -> AppState:
    args = be.parse_args()
    try:
        cfg, engine = _engine(args.config, args.sets, args.no_cache)
    except Exception as e:
        st.error(f"Configuration **{args.config}** could not be loaded: {type(e).__name__}: {e}")
        st.caption("Start with `uv run streamlit run src/callguard/ui/app.py -- --config local` "
                   "(profiles live in `config/`).")
        st.stop()

    defaults = be.fusion_defaults(cfg)
    default_weights = be.check_weights(cfg)
    all_families = engine.families()
    loaded = be.load_results(engine.ctx.runs_dir)
    settings = _sidebar(cfg, engine, defaults, default_weights, all_families, len(loaded.results))
    families = [f for f in all_families if f.id in set(settings.families_on)]
    if not all_families:  # unreadable keyword list/criteria: say so instead of deciding "nothing found"
        st.sidebar.error(f"Keyword list or criteria could not be read ({engine.ctx.path('keywords')}, "
                         f"{engine.ctx.path('criteria')}); showing stored decisions.", icon=":material/error:")
    decided = be.decide_all(engine, loaded, settings.overrides(), families if all_families else None)
    baseline = be.decide_all(engine, loaded, None, all_families or None)
    app = AppState(args=args, cfg=cfg, engine=engine, defaults=defaults, default_weights=default_weights,
                   settings=settings, all_families=all_families, families=families, loaded=loaded,
                   decided=decided, baseline=baseline, pages=_pages())
    st.session_state[APP_KEY] = app
    return app
