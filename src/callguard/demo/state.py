"""Shared state of the demo app: the same :class:`callguard.ui.session.AppState` the officer UI builds (so its
pages, panels and backend work unchanged), but without the officer UI's sidebar. The knobs live on the
pages: Alarmschwelle + Prüfmodus on «Fälle» and «Regeln & Einstellungen»; their values persist for
the session (``persist_state="session"``) and are read here before any page draws.

Mode changes are saved per profile and audit-logged exactly like in the officer UI (``ui_prefs.json``,
``mode_change`` event).
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import streamlit as st

from callguard import audit
from callguard import feedback as fb
from callguard.config import AppConfig
from callguard.ui import backend as be
from callguard.ui import modes as md
from callguard.ui import session as ses
from callguard.ui import sources as srcs
from callguard.ui.session import APP_KEY, AppState, Settings

THRESHOLD_KEY = "dm_threshold"
MODE_KEY = "dm_mode"
FAMILY_PREFIX = "dm_fam_"
NAME_KEY = "cg_officer_name"  # shared with the officer UI's feedback panel
from callguard.demo import DEMO_URL_ENV  # noqa: E402,F401  (re-exported for the pages)


def family_key(fid: str) -> str:
    return f"{FAMILY_PREFIX}{fid}"


def mode_threshold(modes: md.ModeState | None, mode: str | None, profile_threshold: float) -> float:
    if modes is None or mode is None:
        return profile_threshold
    m = modes.spec.get(mode)
    return min(1.0, max(0.0, md.mode_threshold(m, modes.metrics.get(mode), profile_threshold)))


def available_modes(modes: md.ModeState) -> list[str]:
    return [m.id for m in modes.spec.modes if modes.avail.get(m.id, md.Availability(True)).ok]


def _initial_mode(modes: md.ModeState, runs_root: Path, source_key: str) -> str:
    ok = available_modes(modes)
    saved = md.load_choice(runs_root, source_key)
    if saved in ok:
        return saved
    return modes.spec.default if modes.spec.default in ok or not ok else ok[0]


def on_mode_change(runs_root: str, source_key: str, audit_dir: str, profile_threshold: float) -> None:
    """Callback of the Prüfmodus control: threshold to the mode's own, save the choice, audit-log it."""
    ss = st.session_state
    app: AppState | None = ss.get(APP_KEY)
    modes = app.modes if app is not None else None
    new, old = ss.get(MODE_KEY), ss.get("_dm_mode_prev")
    if modes is None or new is None or new == old:
        return
    ss[THRESHOLD_KEY] = mode_threshold(modes, new, profile_threshold)
    md.save_choice(runs_root, source_key, new, user=ss.get(NAME_KEY) or None)
    m = modes.spec.get(new)
    audit.log_event(audit_dir, "mode_change", user=ss.get(NAME_KEY) or None, profile=source_key, before=old,
                    after=new, label=m.label, rule=m.rule, consequences=md.consequence(modes.metrics.get(new)),
                    uncertainty=md.uncertainty_note(modes.metrics.get(new)), via="demo")
    ss["_dm_mode_prev"] = new


def bootstrap(pages: Mapping[str, Any]) -> AppState:
    """Build the AppState for this script run and store it where ``current_app()`` finds it."""
    ss = st.session_state
    args = be.parse_args()
    try:
        cfg, engine = ses._engine(args.config, args.sets, args.no_cache)
    except Exception as e:
        st.error(f"Konfiguration **{args.config}** konnte nicht geladen werden: {type(e).__name__}: {e}")
        st.stop()
    runs_root = cfg.paths.resolve("runs_dir")
    source = srcs.list_sources(runs_root, cfg.name)[0]  # the launch profile's own run
    loaded = be.load_results(engine.ctx.runs_dir)
    defaults = be.fusion_defaults(cfg)
    default_weights = be.check_weights(cfg)
    all_families = engine.families()
    try:
        # fact policy profiles (two_readers rule policy): the combination of the two readers per fact
        # (tab «Fakten») replaces the Prüfmodus
        modes = None if uses_fact_policy(cfg) else ses._mode_state(cfg, engine, loaded, runs_root)
    except Exception:  # a broken mode spec must not take the demo down
        modes = None

    mode = None
    if modes is not None:
        ok = available_modes(modes)
        if ss.get(MODE_KEY) not in ok:
            ss[MODE_KEY] = _initial_mode(modes, runs_root, source.key)
        mode = ss[MODE_KEY]
        ss.setdefault("_dm_mode_prev", mode)
        modes.current = mode
    profile_thr = min(1.0, max(0.0, defaults["threshold"]))
    if THRESHOLD_KEY not in ss:
        ss[THRESHOLD_KEY] = mode_threshold(modes, mode, profile_thr)
    for f in all_families:
        ss.setdefault(family_key(f.id), True)
    on = [f.id for f in all_families if ss.get(family_key(f.id), True)]
    settings = Settings(threshold=float(ss[THRESHOLD_KEY]), review_band=defaults["review_band"],
                        max_uncertainty=min(1.0, max(0.0, defaults["max_uncertainty"])),
                        weights=dict(default_weights), families_on=on, mode=mode)

    base_engine = engine
    if modes is not None:
        try:
            engine = modes.engine(base_engine, mode)
        except Exception:
            engine = base_engine
        defaults = {**defaults, "threshold": mode_threshold(modes, mode, profile_thr)}
    families = [f for f in all_families if f.id in set(on)]
    decided = be.decide_all(engine, loaded, settings.overrides(), families if all_families else None)
    baseline_engine = base_engine
    if modes is not None:
        try:
            baseline_engine = modes.engine(base_engine, modes.spec.default)
        except Exception:
            baseline_engine = base_engine
    baseline = be.decide_all(baseline_engine, loaded, None, all_families or None)
    app = AppState(args=args, cfg=cfg, engine=engine, defaults=defaults, default_weights=default_weights,
                   settings=settings, all_families=all_families, families=families, loaded=loaded,
                   decided=decided, baseline=baseline, pages=dict(pages), source=source, sources=[source],
                   modes=modes, base_engine=base_engine)
    ss[APP_KEY] = app
    return app


# --------------------------------------------------------------------------------------------
# small shared helpers for the pages
# --------------------------------------------------------------------------------------------


def uses_fact_policy(cfg: AppConfig) -> bool:
    f = cfg.fusion or {}
    return f.get("type") == "two_readers" and f.get("rule") == "policy"


def profile_threshold(app: AppState) -> float:
    return min(1.0, max(0.0, be.fusion_defaults(app.cfg)["threshold"]))


def audit_dir(app: AppState) -> Path:
    return app.runs_dir


@st.cache_data(show_spinner=False, ttl=5)
def _feedback(runs_dir: str, mtime: float) -> list[dict[str, Any]]:
    return [i.model_dump(mode="json") for i in fb.load(runs_dir)]


def feedback_items(app: AppState) -> list[fb.FeedbackItem]:
    """The officers' stored judgements of the shown run (real store only), cheap to call per rerun."""
    p = fb.feedback_path(app.runs_dir)
    mtime = p.stat().st_mtime if p.is_file() else 0.0
    return [fb.FeedbackItem.model_validate(d) for d in _feedback(str(app.runs_dir), mtime)]


def models_in_use(cfg: AppConfig, results: Mapping[str, Any]) -> dict[str, str]:
    """For the footer: the LLM and the ASR the shown results were made with (else what the profile names).
    The model choice is open in the team: always read, never hardcoded."""
    llm_seen: dict[str, int] = {}
    asr_seen: dict[str, int] = {}
    for r in results.values():
        for cr in r.checks.values():
            m = (cr.meta or {}).get("model")
            if m and cr.type in ("facts", "llm_judge", "questions", "geval"):
                llm_seen[str(m)] = llm_seen.get(str(m), 0) + 1
        b = r.transcript.asr_backend
        if b:
            asr_seen[b] = asr_seen.get(b, 0) + 1
    llm = max(llm_seen, key=llm_seen.get) if llm_seen else ""
    if not llm:
        spec = (cfg.llms or {}).get("default") or {}
        llm = str(spec.get("cache_tag") or spec.get("model") or spec.get("type") or "–")
    asr = max(asr_seen, key=asr_seen.get) if asr_seen else str(cfg.asr.get("model_tag") or cfg.asr.get("model")
                                                                  or cfg.asr.get("type") or "–")
    return {"profile": cfg.name, "llm": llm, "asr": asr.split(":", 1)[-1]}
