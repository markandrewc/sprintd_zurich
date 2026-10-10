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
from callguard.types import CallResult, Family
from callguard.ui import backend as be
from callguard.ui import sources as srcs
from callguard.ui.backend import Decided, Engine, Loaded, UIArgs
from callguard.ui.sources import Source

APP_KEY = "_callguard_app"
VIEWS = Path(__file__).resolve().parent / "views"


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
    source: Source | None = None  # where the results come from (profile run or experiment variant)
    sources: list[Source] = field(default_factory=list)

    @property
    def ctx(self):
        return self.engine.ctx

    @property
    def runs_dir(self) -> Path:
        """Folder of the shown results: runs/<profile>, or the experiment variant's folder."""
        if self.source is not None and self.source.kind == "experiment":
            return self.source.path
        return self.engine.ctx.runs_dir

    @property
    def runs_root(self) -> Path:
        return self.cfg.paths.resolve("runs_dir")

    @property
    def read_only(self) -> bool:
        """Experiment variants are shown, never rewritten (keyword re-runs / processing: profile runs only)."""
        return self.source is not None and self.source.read_only

    def result_dir(self, call_id: str) -> Path:
        return self.loaded.paths[call_id].parent

    def live_result(self, call_id: str) -> CallResult:
        """The stored result with its decision replaced by the live one (what panels get)."""
        r = self.loaded.results[call_id]
        return r.model_copy(update={"decision": self.decided[call_id].decision})

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
    def misheard_below(self) -> float | None:
        """ASR confidence under which a passage is shown as «möglicherweise verhört» (None = off)."""
        from callguard.misheard import threshold_of

        return threshold_of(self.cfg.snippets)

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

    def family(self, fid: str) -> Family | None:
        return next((f for f in self.all_families if f.id == fid), None)

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
        st.error("Bitte die UI über ihren Einstieg starten: `uv run callguard ui -c local`")
        st.stop()
    return app


@st.cache_resource(show_spinner="Konfiguration und Plugins werden geladen …")
def _engine(config: str, sets: tuple[str, ...], no_cache: bool) -> tuple[AppConfig, Engine]:
    cfg = load_config(config, list(sets))
    return cfg, Engine(cfg, use_cache=not no_cache)


@st.cache_resource(show_spinner="Konfiguration der Quelle wird geladen …")
def _source_engine(key: str, runs_root: str, sets: tuple[str, ...], no_cache: bool) -> tuple[AppConfig, Engine]:
    cfg = srcs.source_config(srcs.source_from_key(key, Path(runs_root)), sets)
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

SOURCE_KEY = "cg_source"


def _wkey(check: str) -> str:
    return f"cg_w_{check}"


def _fkey(fid: str) -> str:
    return f"cg_fam_{fid}"


def _reset(defaults: dict[str, float], weights: dict[str, float], families: list[Family]) -> None:
    st.session_state["cg_threshold"] = min(1.0, max(0.0, defaults["threshold"]))
    st.session_state["cg_band"] = defaults["review_band"]
    st.session_state["cg_maxunc"] = min(1.0, max(0.0, defaults["max_uncertainty"]))
    for name, w in weights.items():
        st.session_state[_wkey(name)] = max(0.0, w)
    for f in families:
        st.session_state[_fkey(f.id)] = True


def _pick_source(sources: list[Source]) -> Source:
    """Sidebar "Quelle": the launch profile's run, other profile runs, experiment variants."""
    ss = st.session_state
    keys = [x.key for x in sources]
    by_key = {x.key: x for x in sources}
    wanted = st.query_params.get("src")
    if wanted in by_key and ss.get(SOURCE_KEY) != wanted and not ss.get("_cg_src_from_url"):
        ss[SOURCE_KEY] = wanted  # deep link ?src=exp:<experiment>/<variant>, applied once
        ss["_cg_src_from_url"] = True
    if ss.get(SOURCE_KEY) not in by_key:
        ss[SOURCE_KEY] = keys[0]
    if len(sources) > 1:
        st.sidebar.selectbox("Quelle", keys, key=SOURCE_KEY, format_func=lambda k: by_key[k].label,
                             help="Welche Ergebnisse angezeigt werden: der Lauf eines Profils "
                                  "(runs/<profil>) oder eine Variante eines Experiments "
                                  "(runs/experiments/<experiment>/<variante>, nur lesen).")
    return by_key[ss[SOURCE_KEY]]


def _sidebar(cfg: AppConfig, engine: Engine, defaults: dict[str, float], weights: dict[str, float],
             families: list[Family], n_calls: int, source: Source) -> Settings:
    ss = st.session_state
    defaults = {**defaults, "threshold": min(1.0, max(0.0, defaults["threshold"])),
                "max_uncertainty": min(1.0, max(0.0, defaults["max_uncertainty"]))}
    weights = {k: max(0.0, w) for k, w in weights.items()}
    if ss.get("_cg_knobs_for") not in (None, source.key):  # new source: start from its own config
        _reset(defaults, weights, families)
    ss["_cg_knobs_for"] = source.key
    ss.setdefault("cg_threshold", defaults["threshold"])
    ss.setdefault("cg_band", defaults["review_band"])
    ss.setdefault("cg_maxunc", defaults["max_uncertainty"])
    for name, w in weights.items():
        ss.setdefault(_wkey(name), w)
    for f in families:
        ss.setdefault(_fkey(f.id), True)

    with st.sidebar:
        st.caption(f"{source.label} · {n_calls} Anruf{'e' if n_calls != 1 else ''}"
                   + (" · nur lesen" if source.read_only else ""))
        if engine.error:
            st.warning(f"Notbetrieb: {engine.error}. Wo nötig werden die gespeicherten Entscheide gezeigt.",
                       icon=":material/warning:")

        st.markdown("#### Entscheidung")
        thr = st.slider("Alarmschwelle", 0.0, 1.0, step=0.01, key="cg_threshold", persist_state="session",
                        help="Ab diesem Score löst ein Anruf Alarm aus. Tiefer = mehr Alarme. Wirkt sofort auf "
                             "alle Anrufe (nur Neu-Bewertung, keine Spracherkennung, kein LLM).")
        band = st.slider("Prüfbereich unter der Schwelle", 0.0, max(0.5, defaults["review_band"]), step=0.01,
                         key="cg_band", persist_state="session",
                         help="Anrufe, die so knapp unter der Schwelle liegen, gehen zur Prüfung an einen Menschen.")
        max_unc = st.slider("Max. Unsicherheit", 0.0, 1.0, step=0.01, key="cg_maxunc", persist_state="session",
                            help="Sind sich die Prüfungen uneinig oder unsicher über diesen Wert hinaus, geht der "
                                 "Anruf zur Prüfung statt automatisch entschieden zu werden.")
        floor = max(0.0, thr - band)
        st.caption(f"Alarm ab **{thr:.2f}** · Prüfen ab **{floor:.2f}** · Standard des Profils "
                   f"{defaults['threshold']:.2f}")

        w_out: dict[str, float] = {}
        with st.expander("Gewichte der Prüfungen", icon=":material/balance:"):
            st.caption("Wie stark jede Prüfung im Gesamtscore zählt. 0 = Prüfung ignorieren.")
            for name in weights:
                w_out[name] = st.slider(name, 0.0, max(2.0, round(2 * weights[name], 2)), step=0.05,
                                        key=_wkey(name), persist_state="session")
        on: list[str] = []
        with st.expander("Arten von Fehlverhalten", icon=":material/category:"):
            st.caption("Eine Art ausschalten = sie zählt in keinem Entscheid mehr.")
            for f in families:
                if st.toggle(be.short_label(f.label), key=_fkey(f.id), persist_state="session",
                             help=f"{f.id}" + ("" if f.can_alarm else " · nur Hinweis, löst nie Alarm aus")):
                    on.append(f.id)

        c1, c2 = st.columns(2)
        c1.button("Zurücksetzen", icon=":material/restart_alt:", on_click=_reset,
                  args=(defaults, weights, families), help="Zurück auf die Werte des Profils.", width="stretch")
        if c2.button("Neu laden", icon=":material/refresh:", help="Konfiguration und Ergebnisse neu einlesen.",
                     width="stretch"):
            reload_everything()
            st.rerun()
    return Settings(threshold=float(thr), review_band=float(band), max_uncertainty=float(max_unc),
                    weights=w_out, families_on=on)


# --------------------------------------------------------------------------------------------
# Bootstrap
# --------------------------------------------------------------------------------------------


def _pages() -> dict[str, Any]:
    """st.Page per entry of ``pages_registry`` (key -> page), in navigation order."""
    from callguard.ui.pages_registry import pages

    return {p.key: st.Page(p.path(), title=p.title, icon=p.icon, url_path=p.url, default=p.default)
            for p in pages()}


def bootstrap() -> AppState:
    args = be.parse_args()
    try:
        cfg, engine = _engine(args.config, args.sets, args.no_cache)
    except Exception as e:
        st.error(f"Konfiguration **{args.config}** konnte nicht geladen werden: {type(e).__name__}: {e}")
        st.caption("Start mit `uv run callguard ui -c local` (Profile liegen in `config/`).")
        st.stop()

    st.sidebar.markdown("### :material/shield: callguard")
    sources = srcs.list_sources(cfg.paths.resolve("runs_dir"), cfg.name)
    source = _pick_source(sources)
    if source.key != sources[0].key:
        try:
            cfg, engine = _source_engine(source.key, str(cfg.paths.resolve("runs_dir")), args.sets, args.no_cache)
        except Exception as e:
            st.sidebar.error(f"Konfiguration der Quelle konnte nicht geladen werden ({type(e).__name__}: {e}); "
                             "es gilt das Startprofil.", icon=":material/error:")
    loaded = srcs.load_jsonl(source.path) if source.kind == "experiment" else be.load_results(engine.ctx.runs_dir)

    defaults = be.fusion_defaults(cfg)
    default_weights = be.check_weights(cfg)
    all_families = engine.families()
    settings = _sidebar(cfg, engine, defaults, default_weights, all_families, len(loaded.results), source)
    families = [f for f in all_families if f.id in set(settings.families_on)]
    if not all_families:  # unreadable keyword list/criteria: say so instead of deciding "nothing found"
        st.sidebar.error(f"Stichwortliste oder Kriterien unlesbar ({engine.ctx.path('keywords')}, "
                         f"{engine.ctx.path('criteria')}); es gelten die gespeicherten Entscheide.",
                         icon=":material/error:")
    decided = be.decide_all(engine, loaded, settings.overrides(), families if all_families else None)
    baseline = be.decide_all(engine, loaded, None, all_families or None)
    app = AppState(args=args, cfg=cfg, engine=engine, defaults=defaults, default_weights=default_weights,
                   settings=settings, all_families=all_families, families=families, loaded=loaded,
                   decided=decided, baseline=baseline, pages=_pages(), source=source, sources=sources)
    st.session_state[APP_KEY] = app
    return app
