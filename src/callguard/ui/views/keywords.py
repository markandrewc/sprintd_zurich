"""Keywords & criteria: the officer edits what the system looks for, without code.

Keywords (``keywords.json``) feed the cheap keyword check: an edit plus "Re-run cheap checks" changes the
hit counts within seconds. Criteria (``criteria.yaml``) are read by the LLM checks; changing them
invalidates cached LLM results, so those rerun only on request (slow on CPU).
"""

from __future__ import annotations

import time
from dataclasses import asdict

import pandas as pd
import streamlit as st

from callguard.families import load_families
from callguard.types import LABELS, Segment, Transcript
from callguard.ui import render as ui
from callguard.ui.backend import (
    KEYWORD_COLUMNS,
    LABEL_TEXT,
    all_keyword_ids,
    backup_file,
    decide_all,
    keyword_rows,
    label_counts,
    load_results,
    rerun_checks,
    rows_to_keywords,
    save_criteria,
    save_family_keywords,
    short_label,
)
from callguard.ui.session import current_app

app = current_app()
kw_path, crit_path = app.ctx.path("keywords"), app.ctx.path("criteria")
backup_dir = app.runs_dir / "_backups"
pipeline = app.engine.pipeline

st.title("Keywords & criteria")
st.caption(f"Keywords are matched literally in the transcript (cheap, instant). Criteria tell the LLM checks "
           f"when a family is an alarm. Files: `{kw_path.name}`, `{crit_path.name}`; every save keeps a backup "
           f"in `{backup_dir}`.")

for msg in st.session_state.pop("cg_kw_messages", []):
    st.toast(msg, icon=":material/check_circle:")

try:
    families = sorted(load_families(kw_path, crit_path), key=lambda f: not f.can_alarm)  # misconduct first
except Exception as e:
    st.error(f"The keyword list or criteria could not be read: {type(e).__name__}: {e}")
    st.stop()

version = st.session_state.setdefault("cg_kw_version", 0)


def _saved(msg: str) -> None:
    st.session_state["cg_kw_version"] = version + 1  # fresh editors showing the file as saved
    st.session_state.setdefault("cg_kw_messages", []).append(msg)
    st.session_state["cg_kw_dirty"] = True
    st.rerun()


KW_CONFIG = {
    "enabled": st.column_config.CheckboxColumn("On", width="small", default=True,
                                               help="Switch a keyword off without deleting it."),
    "id": st.column_config.TextColumn("Id", width="small", help="Leave empty for a new keyword."),
    "label": st.column_config.TextColumn("Label", help="Short name shown in reasons."),
    "de": st.column_config.TextColumn("Standard German phrases", width="large",
                                      help="Comma-separated. The speech recognition writes Standard German."),
    "gsw": st.column_config.TextColumn("Swiss German spellings", width="large", help="Comma-separated."),
    "en": st.column_config.TextColumn("English phrases", width="large",
                                      help="Comma-separated. Only matched on English transcript views."),
    "harmless": st.column_config.TextColumn("Harmless when …", width="large",
                                            help="When a hit is NOT suspicious; also shown to the LLM checks."),
    "case_sensitive": st.column_config.CheckboxColumn("Aa", width="small", default=False,
                                                      help="Match upper/lower case exactly (e.g. PIN, TAN)."),
}

tabs = st.tabs([short_label(f.label) + ("" if f.enabled else " (off)") for f in families])
for tab, fam in zip(tabs, families):
    with tab:
        st.markdown(f"**{ui.esc(fam.label)}** · `{fam.id}`"
                    + ("" if fam.can_alarm else " · :gray-badge[annotates only, never alarms]")
                    + ("" if fam.enabled else " · :red-badge[switched off]"))

        st.markdown("##### Keywords")
        df = pd.DataFrame(keyword_rows(fam), columns=list(KEYWORD_COLUMNS))
        edited = st.data_editor(df, key=f"cg_kw_{fam.id}_{version}", num_rows="dynamic", hide_index=True,
                                width="stretch", column_config=KW_CONFIG)
        st.caption("Add a keyword in the empty last row; phrases are comma-separated. Prefer switching a keyword "
                   "off over deleting it.")
        if st.button("Save keywords", key=f"cg_kw_save_{fam.id}", icon=":material/save:", type="primary"):
            keywords, warnings = rows_to_keywords(edited.to_dict("records"), all_keyword_ids(kw_path))
            for w in warnings:
                st.warning(w)
            try:
                backup_file(kw_path, backup_dir)
                save_family_keywords(kw_path, crit_path, fam.id, keywords)
            except Exception as e:
                st.error(f"Saving failed: {type(e).__name__}: {e}")
            else:
                _saved(f"Keywords of '{short_label(fam.label)}' saved ({len(keywords)} keywords).")

        st.markdown("##### Criteria (read by the LLM checks)")
        with st.form(f"cg_crit_{fam.id}_{version}", border=True):
            c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
            label = c1.text_input("Label", value=fam.label)
            enabled = c2.toggle("Check this family", value=fam.enabled)
            policy = st.text_area("Policy: when is this an alarm?", value=fam.policy, height=110)
            a, b, c = st.columns(3)
            alarm_when = a.text_area("Alarm when … (one per line)", "\n".join(fam.alarm_when), height=180)
            not_alarm = b.text_area("Not an alarm when … (one per line)", "\n".join(fam.not_alarm_when), height=180)
            review_when = c.text_area("Hand to a human when … (one per line)", "\n".join(fam.review_when), height=180)
            st.caption(":material/info: Saving changes the LLM prompts: cached LLM results for this profile become "
                       "outdated and the LLM checks re-run the next time a call is processed (slow on CPU).")
            if st.form_submit_button("Save criteria", icon=":material/save:"):
                try:
                    backup_file(crit_path, backup_dir)
                    save_criteria(crit_path, fam.id, {"label": label, "policy": policy, "alarm_when": alarm_when,
                                                      "not_alarm_when": not_alarm, "review_when": review_when,
                                                      "enabled": enabled})
                except Exception as e:
                    st.error(f"Saving failed: {type(e).__name__}: {e}")
                else:
                    _saved(f"Criteria of '{short_label(label)}' saved.")

# -- try a sentence ----------------------------------------------------------------------------

kw_check = next((c for c in (pipeline.checks if pipeline else []) if c.plugin_type == "keywords"), None)
with st.expander("Try a sentence against the keyword list", icon=":material/science:"):
    sample = st.text_input("Sentence", placeholder="z.B. Ich möchte die Aktie vor der Meldung kaufen.",
                           key="cg_kw_try")
    if sample.strip():
        if kw_check is None:
            st.info("No keyword check is configured in this profile.")
        else:
            try:
                tr = Transcript(call_id="try", segments=[Segment(id="S001", start=0.0, end=5.0, text=sample)])
                res = kw_check.run(tr, app.engine.families())
            except Exception as e:
                st.warning(f"The keyword check failed: {type(e).__name__}: {e}")
            else:
                if res.findings:
                    st.dataframe(pd.DataFrame([{
                        "Family": f.family, "Hit": str(f.detail.get("matched_text", "")), "Score": f.score,
                        "Reason": f.reason} for f in res.findings]), hide_index=True, width="stretch")
                else:
                    st.caption("No keyword matches.")

# -- apply to processed calls ------------------------------------------------------------------

st.divider()
st.subheader("Apply to processed calls")
st.caption("Re-runs the keyword and pattern checks on every processed call (seconds) and re-decides with the "
           "current sidebar settings. LLM checks come from the cache; if their criteria changed they keep their "
           "previous result (marked as not re-run) unless you include them below.")
if st.session_state.get("cg_kw_dirty"):
    st.info("You changed the keywords or criteria. Re-run the checks to see the effect on the processed calls.",
            icon=":material/sync_problem:")
include_llm = st.checkbox("Also re-run LLM checks whose criteria changed (slow: about a minute per call and "
                          "check on CPU; uses the shared LLM server)", key="cg_kw_include_llm")
disabled = pipeline is None or not app.loaded.results
if pipeline is None:
    st.caption(f":material/block: Not available: {app.engine.error}")
elif not app.loaded.results:
    st.caption(":material/block: No processed calls yet.")


def _keyword_hits(results) -> int:
    return sum(len(cr.findings) for r in results.values() for cr in r.checks.values() if cr.type == "keywords")


if st.button("Re-run cheap checks on all calls", type="primary", icon=":material/sync:", disabled=disabled):
    before, hits_before = label_counts(app.decided), _keyword_hits(app.loaded.results)
    bar = st.progress(0.0, text="Re-running checks …")

    def _progress(i: int, n: int, cid: str) -> None:
        bar.progress(min(1.0, i / max(n, 1)), text=f"{cid} ({i + 1}/{n})" if cid else "done")

    t0 = time.time()
    report = rerun_checks(pipeline, app.loaded, include_llm=include_llm, progress=_progress)
    loaded = load_results(app.runs_dir)
    after = label_counts(decide_all(app.engine, loaded, app.settings.overrides(), app.families))
    st.session_state["cg_kw_report"] = {
        "before": before, "after": after, "hits_before": hits_before, "hits_after": _keyword_hits(loaded.results),
        "report": asdict(report), "seconds": time.time() - t0, "threshold": app.settings.threshold,
    }
    st.session_state["cg_kw_dirty"] = False
    st.rerun()

rep = st.session_state.get("cg_kw_report")
if rep:
    r = rep["report"]
    st.markdown(f"**Last re-run** · {r['calls']} calls in {rep['seconds']:.1f} s · threshold {rep['threshold']:.2f}")
    cols = st.columns(4)
    for col, label in zip(cols, LABELS):
        col.metric(LABEL_TEXT[label], rep["after"][label], delta=f"{rep['after'][label] - rep['before'][label]:+d}",
                   delta_color="off", border=True)
    cols[3].metric("Keyword hits", rep["hits_after"], delta=f"{rep['hits_after'] - rep['hits_before']:+d}",
                   delta_color="off", border=True)
    st.caption(f"Check runs: {r['rerun']} executed, {r['reused']} from cache, {r['kept']} LLM results kept "
               f"(criteria changed, not re-run).")
    for f in r["failed"]:
        st.warning(f"Failed: {f}")
