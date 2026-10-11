"""Experimente: the research results (``runs/experiments/*/summary.json`` from ``callguard experiment``)
for the team and the jury: variants with 95% bootstrap intervals, a bar chart with the intervals, paired
comparisons with the calls that flipped, the charts of ``research/report/<experiment>/`` and the
leaderboard. Any variant can be opened in the inbox (sidebar source) to listen to its decisions.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from callguard.config import ROOT
from callguard.ui import render as ui
from callguard.ui import sources as srcs
from callguard.ui.session import SOURCE_KEY, current_app

app = current_app()

st.title("Experimente")
summaries = srcs.load_summaries(app.runs_root)
leaderboard = srcs.read_text(ROOT / "research" / "leaderboard.md")
if not summaries:
    st.info(f"Noch keine Experimente in `{app.runs_root / 'experiments'}`. Starten mit "
            "`uv run callguard experiment experiments/<name>.yaml`.", icon=":material/science:")
    if leaderboard:
        with st.expander("Leaderboard (research/leaderboard.md)", icon=":material/leaderboard:"):
            st.markdown(leaderboard)
    st.stop()

st.caption("Jede Variante wird über die Dev-Dialoge ausgewertet; Hauptmass ist der F1 der Markierungen (Alarm "
           "oder Prüfen) **out-of-fold** (CV: Schwelle jeweils auf den anderen Folds gewählt). Klammern = 95%-"
           "Bootstrap-Intervall über Dialoge: **überlappende Intervalle = kein belegter Unterschied**. ORACLE-"
           "Varianten lesen die Referenz-Skripte und sind nie Abgabe-Kandidaten.")

summaries.sort(key=lambda x: str(x.get("created", "")), reverse=True)
names = [x["experiment"] for x in summaries]
by_name = {x["experiment"]: x for x in summaries}
c1, c2 = st.columns([2, 3], vertical_alignment="bottom")
name = c1.selectbox("Experiment", names, key="cg_exp_pick",
                    format_func=lambda n: f"{n} · {str(by_name[n].get('created', ''))[:16]}")
METRICS = {"F1 Markierung": "flag_f1", "Fehlalarmquote": "false_alarm_rate", "Verpasst": "miss_rate",
           "Alarm-F1": "alarm_f1", "Prüf-Recall": "review_recall", "Exakter Status": "accuracy"}
metric_label = c2.pills("Mass", list(METRICS), default="F1 Markierung", key="cg_exp_metric") or "F1 Markierung"
metric = METRICS[metric_label]
S = by_name[name]
git = S.get("git") or {}
st.markdown(f"**{ui.esc(S.get('description') or name)}**  \n"
            f":gray[Basis-Profil `{S.get('base')}` · Split `{S.get('split')}` · Vergleich gegen "
            f"`{S.get('compare_to') or '–'}` · {S.get('n_boot')} Bootstrap-Stichproben · Commit "
            f"`{git.get('sha', '–')}{'*' if git.get('dirty') else ''}` · {S.get('created', '')}]"
            + (f"  \nForschungsfragen: {', '.join(S.get('rq') or [])}" if S.get("rq") else ""))
if S.get("split") == "holdout":
    st.warning("**Holdout-Lauf**: protokolliert in runs/holdout_log.jsonl. Nicht auf diesen Zahlen tunen.",
               icon=":material/lock:")

rows = srcs.variant_rows(S, metric)
lower_better = metric in ("false_alarm_rate", "miss_rate")
rows.sort(key=lambda r: (r["value"] is None, (r["value"] or 0.0) * (1 if lower_better else -1)))

# -- chart: metric per variant with CI error bars ---------------------------------------------------

cdf = pd.DataFrame([{
    "Variante": r["variant"], "Wert": r["value"], "von": r["lo"] if r["lo"] is not None else r["value"],
    "bis": r["hi"] if r["hi"] is not None else r["value"],
    "Typ": "ORACLE (nur Experiment)" if "ORACLE" in r["tags"] else "Kandidat", "Basis": r["basis"],
    "Text": "–" if r["value"] is None else f"{r['value']:.2f}",
} for r in rows if r["value"] is not None])
if len(cdf):
    order = list(cdf["Variante"])
    y = alt.Y("Variante:N", sort=order, title=None, axis=alt.Axis(labelLimit=260))
    color = alt.Color("Typ:N", scale=alt.Scale(domain=["Kandidat", "ORACLE (nur Experiment)"],
                                               range=["#2a78d6", "#a3a3a3"]),
                      legend=alt.Legend(orient="bottom", title=None))
    tip = ["Variante:N", alt.Tooltip("Wert:Q", format=".2f"), alt.Tooltip("von:Q", title="95%-KI von", format=".2f"),
           alt.Tooltip("bis:Q", title="95%-KI bis", format=".2f"), "Basis:N", "Typ:N"]
    bars = alt.Chart(cdf).mark_bar(height=alt.RelativeBandSize(0.55), cornerRadiusEnd=4).encode(
        x=alt.X("Wert:Q", scale=alt.Scale(domain=[0, 1]), title=f"{metric_label} (Balken) mit 95%-Intervall",
                axis=alt.Axis(format=".1f")), y=y, color=color, tooltip=tip)
    err = alt.Chart(cdf).mark_errorbar(ticks=alt.MarkConfig(size=10), color="#0b0b0b", thickness=1.5).encode(
        x=alt.X("von:Q", title=""), x2="bis:Q", y=y, tooltip=tip)
    text = alt.Chart(cdf).mark_text(align="left", dx=6, dy=-9, fontSize=11, color="#52514e").encode(
        x="bis:Q", y=y, text="Text:N")
    st.altair_chart(alt.layer(bars, err, text).properties(height=alt.Step(40)), width="stretch")

# -- table -----------------------------------------------------------------------------------------


def _ci(r: dict) -> str:
    v = "–" if r["value"] is None else f"{r['value']:.2f}"
    return v + (f" [{r['lo']:.2f}, {r['hi']:.2f}]" if r["lo"] is not None and r["hi"] is not None else "")


tdf = pd.DataFrame([{
    "Variante": r["variant"], f"{metric_label} [95%-KI]": _ci(r), "Basis": r["basis"], "n": r["n"],
    "F1": r["flag_f1"], "Fehlalarme": r["far"], "Verpasst": r["miss"], "Prüf-Recall": r["review_recall"],
    "Alarm-F1": r["alarm_f1"], "Exakt": r["accuracy"], "Schwelle": r["threshold"], "s/Anruf": r["s_per_call"],
    "LLM-Aufrufe/Anruf": r["llm_calls"], "Tags": r["tags"], "Beschreibung": r["description"], "Commit": r["commit"],
} for r in rows])
pct_cols = ("F1", "Fehlalarme", "Verpasst", "Prüf-Recall", "Alarm-F1", "Exakt")
st.dataframe(tdf, hide_index=True, width="stretch", column_config={
    **{k: st.column_config.NumberColumn(format="percent") for k in pct_cols},
    "Schwelle": st.column_config.NumberColumn(format="%.2f", help="Vorgeschlagene Schwelle (max. F1 auf Dev)."),
    "s/Anruf": st.column_config.NumberColumn(format="%.1f", help="Rechenzeit der Prüfungen pro Anruf."),
    "LLM-Aufrufe/Anruf": st.column_config.NumberColumn(format="%.1f"),
    "Beschreibung": st.column_config.TextColumn(width="large")})

o1, o2 = st.columns([3, 2], vertical_alignment="bottom")
variant = o1.selectbox("Variante", [r["variant"] for r in rows], key="cg_exp_variant")
key = f"exp:{name}/{variant}"
has_results = any(x.key == key for x in app.sources)


def _open() -> None:
    st.session_state[SOURCE_KEY] = key


if o2.button("Im Eingang öffnen", icon=":material/inbox:", disabled=not has_results, width="stretch",
             help="Zeigt die Entscheide dieser Variante im Eingang (Quelle in der Seitenleiste)."
             if has_results else "Für diese Variante gibt es keine results.jsonl.", on_click=_open):
    st.switch_page(app.pages["inbox"])

# -- paired comparisons ---------------------------------------------------------------------------------

comps = S.get("comparisons") or []
if comps:
    st.subheader("Paarweise Vergleiche")
    pairs = [(c.get("a"), c.get("b")) for c in comps]
    p1, p2 = st.columns([3, 2], vertical_alignment="bottom")
    pair = p1.selectbox("Vergleich", pairs, key="cg_exp_pair", format_func=lambda ab: f"{ab[1]} gegen {ab[0]}")
    basis = p2.segmented_control("Grundlage", ["cv", "fixed"], default="cv", key="cg_exp_basis",
                                 format_func=lambda b: "CV (out-of-fold)" if b == "cv" else "feste Schwelle") or "cv"
    a, b = pair
    comp_rows = [r for r in srcs.comparison_rows(S, basis) if r["a"] == a and r["b"] == b]
    diff_rows = [r for r in comp_rows if r["diff"] is not None]
    if diff_rows:
        st.dataframe(pd.DataFrame([{
            "Mass": r["metric"], a: r["a_value"], b: r["b_value"], f"Differenz {b} − {a}": r["diff"],
            "95%-KI": f"[{r['lo']:+.2f}, {r['hi']:+.2f}]" if r["lo"] is not None else "–",
            "Belegt?": "ja" if r["real"] else "nein (Rauschen möglich)", "Besser": r["better"] or "–",
        } for r in diff_rows]), hide_index=True, width="stretch",
            column_config={a: st.column_config.NumberColumn(format="%.2f"),
                           b: st.column_config.NumberColumn(format="%.2f"),
                           f"Differenz {b} − {a}": st.column_config.NumberColumn(format="%+.2f")})
    mc = next((r for r in comp_rows if r["metric"].startswith("McNemar")), None)
    if mc:
        st.caption(f"McNemar-Test auf korrekte Markierung: nur {a} richtig {mc['a_value']}×, nur {b} richtig "
                   f"{mc['b_value']}×, p = {mc.get('p', float('nan')):.3f}"
                   + (" (unter 0.05)" if mc["real"] else " (kein belegter Unterschied)") + ".")
    flips = srcs.flip_rows(S, a, b, basis)
    st.markdown(f"**Anrufe, deren Entscheid sich ändert** ({len(flips)})")
    if flips:
        CHANGE = {"fixed": "repariert", "broken": "kaputt gemacht", "same": "gleich richtig/falsch"}
        fdf = pd.DataFrame([{
            "Anruf": f.get("call_id"), "Erwartet": ui.label_text(f.get("expected") or ""),
            a: ui.label_text(f.get("a") or ""), b: ui.label_text(f.get("b") or ""),
            "Markierung": CHANGE.get(f.get("flag_change"), f.get("flag_change") or ""),
            f"Score {a}": f.get("a_score"), f"Score {b}": f.get("b_score"),
            f"Grund {b}": f.get("b_reason") or "", f"Grund {a}": f.get("a_reason") or "",
        } for f in flips])
        st.dataframe(ui.style_labels(fdf, "Erwartet", a, b), hide_index=True, width="stretch", column_config={
            f"Score {a}": st.column_config.NumberColumn(format="%.2f"),
            f"Score {b}": st.column_config.NumberColumn(format="%.2f"),
            f"Grund {a}": st.column_config.TextColumn(width="large"),
            f"Grund {b}": st.column_config.TextColumn(width="large")})
    else:
        st.caption("Keine Anrufe mit anderem Entscheid.")

# -- report charts and leaderboard ----------------------------------------------------------------------

images = srcs.report_images(name)
if images:
    st.subheader("Grafiken aus dem Bericht")
    st.caption(f"research/report/{name}/ (erzeugt von `callguard report`)")
    cols = st.columns(2)
    for i, img in enumerate(images):
        cols[i % 2].image(str(img), caption=img.stem, width="stretch")

if leaderboard:
    with st.expander("Leaderboard über alle Experimente (research/leaderboard.md)", icon=":material/leaderboard:"):
        st.markdown(leaderboard)
