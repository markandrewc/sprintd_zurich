"""Entscheidungshilfe ("was bringt was"): what each component contributes, from the stored experiment results.

Reads ``runs/contrib/contrib.json`` (``callguard contrib``) when it matches the data folder and nothing changed
since; otherwise computes the same analysis on the fly from ``runs/experiments/*/<variant>/rows.json``
(:mod:`callguard.contrib`, statistics only: no ASR, no LLM). Sections: paired deltas per factor (forest plot +
takeaways + the path as a waterfall), generalisation (dev vs paraphrase vs blind vs re-recorded vs synthetic),
metric guide with reference rows, per-family heat map, quality next to cost. New experiments (e.g. Kev) light
up as soon as their rows appear in the data folder.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from callguard import contrib as cb
from callguard.ui import contrib_view as cv
from callguard.ui import render as ui
from callguard.ui.session import current_app

app = current_app()

st.title("Entscheidungshilfe: was bringt was")
st.caption("Jede Zeile vergleicht zwei gespeicherte Experiment-Varianten **auf denselben Anrufen** (gepaart): "
           "Differenz B − A mit 95%-Bootstrap-Intervall über Zwillingsgruppen/Dialoge. **Grün = belegter Gewinn, "
           "rot = belegter Verlust, grau = Rauschen** (Intervall enthält 0). Nur Dev-Split; der Holdout ist "
           "verbraucht. Es läuft kein Modell: alles wird aus den gespeicherten Ergebnissen gerechnet.")

default_root = os.environ.get(cb.ENV_DATA) or str(app.runs_root / "experiments")
with st.expander("Datenquelle", icon=":material/folder_open:"):
    root_txt = st.text_input("Ordner mit Experiment-Ergebnissen (<experiment>/<variante>/rows.json)",
                             value=default_root, key="cg_dec_root")
    if st.button("Neu berechnen", icon=":material/refresh:", key="cg_dec_refresh"):
        st.cache_data.clear()
data_root = cb.resolve_data_root(root_txt or default_root)
out_dir = app.runs_root / "contrib"

try:
    spec = cb.load_spec()
except (FileNotFoundError, cb.SpecError) as e:
    st.error(f"Spezifikation fehlt oder ist ungültig: {e}", icon=":material/error:")
    st.stop()
if not data_root.exists():
    st.info(f"Keine Experiment-Ergebnisse in `{data_root}`. Experimente laufen auf dem GPU-Rechner "
            "(`callguard experiment`); die Ergebnisse hierher kopieren oder oben einen anderen Ordner wählen.",
            icon=":material/science:")
    st.stop()


@st.cache_data(show_spinner=False)
def _load(spec_path: str, root: str, out: str, stamp: tuple[float, float]) -> tuple[dict, str]:
    return cb.load_or_compute(spec_path, root, out)


json_path = out_dir / "contrib.json"
stamp = (cb.fingerprint(data_root, Path(spec["_path"])), json_path.stat().st_mtime if json_path.exists() else 0.0)
with st.spinner("Gepaarte Vergleiche werden gerechnet …"):
    result, origin = _load(spec["_path"], str(data_root), str(out_dir), stamp)

if not any(p.get("deltas") for p in cb.iter_pairs(result)):
    st.info(f"In `{data_root}` liegt keine der in `{spec['_path']}` genannten Varianten.", icon=":material/science:")
    st.stop()

st.caption(f":gray[Quelle: {'runs/contrib/contrib.json' if origin == 'file' else 'live berechnet'} · Daten "
           f"`{result['data_root']}` · {result['n_boot']} Bootstrap-Stichproben · Schwelle: "
           f"{'out-of-fold CV' if result['basis'] == 'cv' else result['basis']} · {result['created']}]")

# -- a. forest plot ---------------------------------------------------------------------------------

st.subheader("Beitrag der Bausteine")
factors = [f for f in result["factors"] if any(p.get("deltas") for p in f["pairs"])]
c1, c3, c4 = st.columns([5, 2, 2], vertical_alignment="bottom")
metric_label = c1.pills("Mass", list(cv.METRICS), default="Flag-AUC", key="cg_dec_metric") or "Flag-AUC"
metric = cv.METRICS[metric_label]
sort = c3.segmented_control("Sortierung", ["size", "factor"], default="size", key="cg_dec_sort",
                            format_func=lambda s: "nach Grösse" if s == "size" else "nach Faktor") or "size"
confounded = c4.toggle("Verzerrte zeigen", value=True, key="cg_dec_confounded",
                       help="Vergleiche, bei denen sich ausser dem Faktor noch etwas anderes ändert.")
picked = st.pills("Faktoren", [f["id"] for f in factors], selection_mode="multi", default=[f["id"] for f in factors],
                  format_func=lambda i: next(f["short"] for f in factors if f["id"] == i), key="cg_dec_factors") or []
fdf = cv.forest_frame(result, metric, picked, confounded, sort)
if len(fdf):
    st.altair_chart(cv.forest_chart(fdf, metric), width="stretch")
    st.caption(f"Oben die grössten Gewinne für **{metric_label}** (bei Fehlalarmen und Verpassten ist weniger "
               "besser). Form und Farbe: ▲ belegter Gewinn, ▼ belegter Verlust, ● Rauschen. „(verzerrt)“ = ausser "
               "dem Faktor ändert sich noch etwas; die Tabelle unten sagt was.")
else:
    st.caption("Keine Vergleiche für diese Auswahl.")

st.markdown("**Was jeder Faktor bedeutet** (eine Zeile pro Faktor, aus den Zahlen erzeugt)")
for f in factors:
    if f["id"] not in picked:
        continue
    st.markdown(f"{cv.factor_icon(f)} **{ui.esc(f['title'])}**: {f['summary']['line']}")
with st.expander("Alle Vergleiche als Tabelle", icon=":material/table:"):
    st.dataframe(cv.pairs_table(result), hide_index=True, width="stretch", column_config={
        "Was sonst anders ist": st.column_config.TextColumn(width="large"),
        "meta.json-Diff": st.column_config.TextColumn(width="large")})

path = result.get("path") or {}
wdf = cv.waterfall_frame(result, metric)
if len(wdf):
    st.subheader("Der Weg zum Kandidaten")
    st.caption(f"{ui.esc(path.get('title') or '')}: jeder Schritt ist ein gepaarter Vergleich ({metric_label}; "
               "Balken von A nach B, Beschriftung = Differenz mit 95%-Intervall). Blau = Stand am Anfang und Ende.")
    st.altair_chart(cv.waterfall_chart(wdf, metric), width="stretch")
    for ln in path.get("links") or []:
        st.caption(f":material/link: `{ln['a']}` und `{ln['b']}`: "
                   + ("gleiche Entscheide und Scores, die Kette ist lückenlos." if ln["identical"] else
                      f"{ln['label_differs']} Entscheide / {ln['score_differs']} Scores verschieden von {ln['n_common']}."))

# -- b. generalisation ------------------------------------------------------------------------------

PCT_COLS = ("Fehlalarme", "Verpasst", "Exakt", "Prüf-Recall", "CV@FAR20 Recall", "FAR-Boden")


def _pct_table(df, **extra) -> None:
    """Dataframe with rates shown as whole percent (stored as fractions)."""
    cols = [c for c in PCT_COLS if c in df.columns]
    df = df.copy()
    for c in cols:
        df[c] = df[c].astype(float) * 100
    st.dataframe(df, hide_index=True, width="stretch", column_config={
        **{c: st.column_config.NumberColumn(format="%.0f%%") for c in cols}, **extra})


gdf = cv.generalisation_frame(result)
if len(gdf):
    st.subheader("Hält es ausserhalb der Dev-Daten?")
    st.caption("Dasselbe System unter anderen Bedingungen. Die Fakt-Fragen wurden beim Lesen der Dev-Transkripte "
               "geschrieben: Paraphrasen, eine blinde Tabelle, neu aufgenommenes Audio und synthetische Anrufe zeigen, "
               "wie viel davon Anpassung an Dev ist. Synthetische Anrufe sind andere Anrufe (nicht gepaart, "
               "Referenztext statt ASR, teils vom selben LLM geschrieben).")
    st.altair_chart(cv.generalisation_chart(gdf), width="stretch")
    _pct_table(gdf[["Spur", "Bedingung", "Variante", "n", "AUC [95%-KI]", "Fehlalarme", "Verpasst", "Exakt",
                    "gegen Basis"]], **{"gegen Basis": st.column_config.TextColumn(width="large")})

# -- c. metric guide --------------------------------------------------------------------------------

st.subheader("Welche Masse für Entscheide?")
st.table(pd.DataFrame([{"Mass": g["metric"], "Für Entscheide?": g["use"], "Warum": g["why"],
                        "Unsere Zahl": g["number"]} for g in result.get("guide") or []]).set_index("Mass"))
bdf = cv.baselines_table(result)
if len(bdf):
    st.markdown("**Referenzzeilen** (auf denselben Dev-Anrufen): ein System muss diese klar schlagen.")
    _pct_table(bdf, **{"Flag-AUC": st.column_config.NumberColumn(format="%.2f"),
                       "Flag-F1": st.column_config.NumberColumn(format="%.2f")})

# -- d. per family + e. cost -------------------------------------------------------------------------

systems = [s for s in result.get("systems") or [] if s.get("available")]
if systems:
    st.subheader("Wo ist welches System schwach? Und was kostet es?")
    refs = st.multiselect("Systeme", [s["ref"] for s in systems], default=[s["ref"] for s in systems],
                          format_func=lambda r: next(s["label"] for s in systems if s["ref"] == r), key="cg_dec_systems")
    hdf = cv.heatmap_frame(result, refs)
    if len(hdf):
        st.altair_chart(cv.heatmap_chart(hdf), width="stretch")
        st.caption("Anteil exakt richtiger Entscheide (Alarm / Prüfen / Kein Alarm) je erwarteter Art; Anrufe pro Zelle "
                   "im Tooltip. Wenige Anrufe pro Zelle (4–14): eine Zelle kippt mit einem Dialog.")
    sdf = cv.systems_table(result, refs)
    if len(sdf):
        st.markdown("**Qualität und Kosten** (Dev, out-of-fold CV-Schwelle; Kosten = gemessene Rechenzeit der "
                    "Prüfungen ohne ASR und LLM-Aufrufe pro Anruf)")
        _pct_table(sdf, **{"s/Anruf": st.column_config.NumberColumn(
            format="%.1f", help="Rechenzeit der Prüfungen pro Anruf (ohne ASR)."),
            "LLM-Aufrufe/Anruf": st.column_config.NumberColumn(format="%.1f")})

pending = cv.pending_items(result)
if pending:
    with st.expander(f"Ausstehend ({len(pending)}): erscheint automatisch, sobald die Ergebnisse da sind",
                     icon=":material/hourglass_empty:"):
        st.markdown("\n".join(f"- {p}" for p in pending))
