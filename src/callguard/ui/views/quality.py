"""Quality: how the current settings do against the case's expected assessments, and which threshold
would do best. Ground truth is read here for display only; it never reaches the pipeline."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard.ui import metrics_view as mv
from callguard.ui import render as ui
from callguard.ui.backend import LABEL_TEXT, default_thresholds, short_label, sweep_labels, top_family
from callguard.ui.session import current_app, ground_truth

app = current_app()
s = app.settings

st.title("Quality")
truth_calls = ground_truth(str(app.ctx.data_dir))
ids = sorted(cid for cid in app.loaded.results
             if cid in truth_calls and truth_calls[cid].expected is not None)
if not ids:
    st.info("None of the processed calls has an expected assessment in the case data, so there is nothing to "
            "compare against. Process case recordings on **Process a call** first.", icon=":material/school:")
    st.stop()

truth = {cid: truth_calls[cid].expected.label for cid in ids}
pairs = [(truth[c], app.decided[c].decision.label) for c in ids]
base_pairs = [(truth[c], app.baseline[c].decision.label) for c in ids]
m, mb = mv.flag_metrics(pairs), mv.flag_metrics(base_pairs)

st.caption(f"{len(ids)} processed calls with an expected assessment · threshold **{s.threshold:.2f}** · "
           "*flagged* = alarm or review (a human listens). Expected labels are used for this page only.")


def _delta(cur: float | None, base: float | None) -> str | None:
    if not app.customized or cur is None or base is None:
        return None
    return f"{100 * (cur - base):+.0f} pts vs default"


cols = st.columns(6)
cards = [
    ("Precision", m.precision, mb.precision, "normal", "Of the flagged calls, how many should be flagged."),
    ("Recall", m.recall, mb.recall, "normal", "Of the calls that should be flagged, how many are."),
    ("F1", m.f1, mb.f1, "normal", "Balance of precision and recall."),
    ("False-alarm rate", m.false_alarm_rate, mb.false_alarm_rate, "inverse",
     "Harmless calls that were flagged anyway."),
    ("Miss rate", m.miss_rate, mb.miss_rate, "inverse", "Calls that should be flagged but were passed."),
    ("Exact label", m.accuracy, mb.accuracy, "normal", "Predicted alarm/review/no alert equals the expected one."),
]
for col, (name, cur, base, color, help_text) in zip(cols, cards):
    col.metric(name, ui.pct(cur), delta=_delta(cur, base), delta_color=color, border=True, help=help_text)

overrides = s.overrides()
thresholds = default_thresholds(0.05)
with st.spinner("Re-deciding all calls at every threshold …"):
    labels_by_t = sweep_labels(app.engine, app.loaded, overrides, app.families, thresholds, ids)
rows = mv.sweep(labels_by_t, truth)
suggested = mv.suggest_threshold(rows, s.threshold)

left, right = st.columns([2, 3], gap="large")
with left:
    st.subheader("Confusion matrix")
    st.altair_chart(mv.confusion_chart(mv.confusion(pairs)), width="stretch")
    st.caption(f"Flagged correctly {m.tp} · false alarms {m.fp} · misses {m.fn} · correctly passed {m.tn}")
with right:
    st.subheader("Threshold sweep")
    st.altair_chart(mv.sweep_chart(rows, s.threshold, suggested), width="stretch")
    st.caption("Every call re-decided at thresholds 0.05 … 0.95 with the other sidebar settings unchanged.")

if suggested is not None:
    best = next(r for r in rows if r["threshold"] == suggested)
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.markdown(f"**Suggested threshold {suggested:.2f}** (highest F1 {ui.pct(best['f1'])}: precision "
                f"{ui.pct(best['precision'])}, recall {ui.pct(best['recall'])}, false alarms "
                f"{ui.pct(best['false_alarm_rate'])}, {best['flagged']} calls flagged).  \n"
                f":gray[Fitted on these {len(ids)} calls only: a hint, not a calibration.]")

    def _apply() -> None:
        st.session_state["cg_threshold"] = float(suggested)

    c2.button("Apply suggested threshold", on_click=_apply, icon=":material/done:", width="stretch",
              disabled=abs(suggested - s.threshold) < 1e-9)

st.subheader("Per call")
table = []
for cid in ids:
    call, d = truth_calls[cid], app.decided[cid].decision
    top = top_family(d, app.can_alarm)
    exp = call.expected
    table.append({
        "Call": cid, "Level": call.level, "Noisy": call.noisy, "Expected": LABEL_TEXT[exp.label],
        "Predicted": LABEL_TEXT[d.label], "Flag correct": mv.is_flag(exp.label) == mv.is_flag(d.label),
        "Expected family": app.family_label(exp.family) if exp.family else "", "Top family": short_label(top.label) if top else "", "Score": d.score,
    })
df = pd.DataFrame(table)
only_wrong = st.toggle("Only wrong flags", key="cg_quality_wrong")
if only_wrong:
    df = df[~df["Flag correct"]]
st.dataframe(ui.style_labels(df, "Expected", "Predicted"), hide_index=True, width="stretch",
             column_config={"Score": ui.score_column(),
                            "Flag correct": st.column_config.CheckboxColumn()})

by_level = []
for level in sorted({truth_calls[c].level for c in ids}):
    sub = [(truth[c], app.decided[c].decision.label) for c in ids if truth_calls[c].level == level]
    lm = mv.flag_metrics(sub)
    by_level.append({"Level": f"Stufe {level}", "Calls": lm.n, "Recall": ui.pct(lm.recall),
                     "False-alarm rate": ui.pct(lm.false_alarm_rate), "Exact label": ui.pct(lm.accuracy)})
with st.expander("By level", icon=":material/stacked_bar_chart:"):
    st.dataframe(pd.DataFrame(by_level), hide_index=True, width="stretch")
