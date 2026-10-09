"""Qualität: how the current settings do against the case's expected assessments on the DEV split (tuning
data), with 95% bootstrap intervals over dialogues, the threshold curve with the current threshold marked,
and the logged holdout results (runs/holdout_log.jsonl) as a clearly separate reference. Holdout calls are
never scored live here: the holdout is looked at once per final candidate, via ``callguard eval``.
Ground truth is read for display only; it never reaches the pipeline.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from callguard.data import dialogue_of
from callguard.ui import metrics_view as mv
from callguard.ui import render as ui
from callguard.ui import sources as srcs
from callguard.ui.backend import LABEL_TEXT, default_thresholds, short_label, sweep_labels, top_family
from callguard.ui.session import current_app, ground_truth

app = current_app()
s = app.settings

st.title("Qualität")
truth_calls = ground_truth(str(app.ctx.data_dir))
labelled = sorted(cid for cid in app.loaded.results if cid in truth_calls and truth_calls[cid].expected is not None)
if not labelled:
    st.info("Keiner der verarbeiteten Anrufe hat eine Sollbewertung in den Falldaten; es gibt nichts zu vergleichen. "
            "Zuerst Fallaufnahmen auf **Anruf verarbeiten** verarbeiten.", icon=":material/school:")
    st.stop()


@st.cache_data(show_spinner=False)
def _splits() -> tuple[list[str], list[str]] | None:
    from callguard.splits import load_splits

    sp = load_splits(required=False)
    return (sp.dev_dialogues(), sp.holdout_dialogues()) if sp else None


split = _splits()
if split is not None:
    dev, holdout = set(split[0]), set(split[1])
    ids = [c for c in labelled if dialogue_of(c) in dev]
    hidden = [c for c in labelled if dialogue_of(c) in holdout]
    scope = f"**Dev-Split** ({len(ids)} Anrufe, {len({dialogue_of(c) for c in ids})} Dialoge)"
else:
    ids, hidden = labelled, []
    scope = f"**alle Anrufe mit Sollbewertung** ({len(ids)}; keine config/splits.yaml gefunden)"
if not ids:
    st.info("Keiner der verarbeiteten Anrufe gehört zum Dev-Split.", icon=":material/school:")
    st.stop()

truth = {cid: truth_calls[cid].expected.label for cid in ids}
pairs = [(truth[c], app.decided[c].decision.label) for c in ids]
base_pairs = [(truth[c], app.baseline[c].decision.label) for c in ids]
m, mb = mv.flag_metrics(pairs), mv.flag_metrics(base_pairs)

st.caption(f"Auswertung auf {scope} · Schwelle **{s.threshold:.2f}** · *markiert* = Alarm oder Prüfen (ein Mensch "
           "hört zu). Sollbewertungen werden nur auf dieser Seite verwendet."
           + (f" {len(hidden)} Holdout-Anrufe sind ausgeblendet: der Holdout wird nur einmal pro Kandidat "
              "ausgewertet (unten, aus dem Protokoll)." if hidden else ""))


@st.cache_data(show_spinner=False)
def _ci(rows: tuple[tuple[str, str, str], ...]) -> dict:
    from callguard.stats import bootstrap_ci

    return bootstrap_ci([{"call_id": c, "expected": e, "predicted": p} for c, e, p in rows], n_boot=1000)


ci = _ci(tuple((c, truth[c], app.decided[c].decision.label) for c in ids))


def _delta(cur: float | None, base: float | None) -> str | None:
    if not app.customized or cur is None or base is None:
        return None
    return f"{100 * (cur - base):+.0f} Pkt. zum Profil"


def _ci_text(key: str) -> str:
    c = ci.get(key) or {}
    return f"95%-KI {ui.pct(c.get('lo'))}–{ui.pct(c.get('hi'))}" if c.get("lo") is not None else "KI –"


cols = st.columns(6)
cards = [
    ("Präzision", m.precision, mb.precision, "normal", "flag_precision",
     "Von den markierten Anrufen: wie viele hätten markiert werden sollen."),
    ("Recall", m.recall, mb.recall, "normal", "flag_recall", "Von den zu markierenden Anrufen: wie viele markiert sind."),
    ("F1", m.f1, mb.f1, "normal", "flag_f1", "Ausgleich von Präzision und Recall."),
    ("Fehlalarmquote", m.false_alarm_rate, mb.false_alarm_rate, "inverse", "false_alarm_rate",
     "Harmlose Anrufe, die trotzdem markiert wurden."),
    ("Verpasst", m.miss_rate, mb.miss_rate, "inverse", "miss_rate", "Zu markierende Anrufe, die durchgingen."),
    ("Exakter Status", m.accuracy, mb.accuracy, "normal", "accuracy",
     "Alarm / Prüfen / Kein Alarm stimmt genau mit der Sollbewertung."),
]
for col, (name, cur, base, color, key, help_text) in zip(cols, cards):
    col.metric(name, ui.pct(cur), delta=_delta(cur, base), delta_color=color, border=True, help=help_text)
    col.caption(_ci_text(key))
st.caption(f":material/info: Die Intervalle stammen aus 1000 Bootstrap-Stichproben über Dialoge. Bei {len(ids)} "
           "Anrufen sind kleine Unterschiede Rauschen: überlappen sich die Intervalle zweier Einstellungen, ist "
           "kein Unterschied belegt.")

overrides = s.overrides()
thresholds = default_thresholds(0.05)
with st.spinner("Alle Anrufe werden bei jeder Schwelle neu bewertet …"):
    labels_by_t = sweep_labels(app.engine, app.loaded, overrides, app.families, thresholds, ids)
rows = mv.sweep(labels_by_t, truth)
suggested = mv.suggest_threshold(rows, s.threshold)

log_path = app.runs_root / "holdout_log.jsonl"
hold = srcs.read_holdout_log(log_path)
mine = [h for h in hold if h.get("config") == app.cfg.name and (h.get("metrics") or {}).get("flag_f1") is not None]
hold_lines = [{"value": mine[-1]["metrics"]["flag_f1"],
               "what": f"Holdout-F1 {ui.pct(mine[-1]['metrics']['flag_f1'])} ({str(mine[-1].get('time', ''))[:10]}, "
                       "geloggt, nicht zum Tunen)"}] if mine else []

left, right = st.columns([2, 3], gap="large")
with left:
    st.subheader("Wahrheitsmatrix")
    st.altair_chart(mv.confusion_chart(mv.confusion(pairs)), width="stretch")
    st.caption(f"Richtig markiert {m.tp} · Fehlalarme {m.fp} · verpasst {m.fn} · richtig durchgelassen {m.tn}")
with right:
    st.subheader("Schwellen-Kurve")
    st.altair_chart(mv.sweep_chart(rows, s.threshold, suggested, hold_lines), width="stretch")
    st.caption("Jeder Dev-Anruf neu bewertet bei Schwellen 0.05 … 0.95, übrige Regler unverändert. Schwarze Linie: "
               "aktuelle Schwelle." + (" Rote gepunktete Linie: zuletzt geloggter Holdout-F1 dieses Profils (feste "
                                        "Schwelle des Kandidaten, nur zur Einordnung)." if hold_lines else ""))

if suggested is not None:
    best = next(r for r in rows if r["threshold"] == suggested)
    c1, c2 = st.columns([3, 1], vertical_alignment="center")
    c1.markdown(f"**Vorgeschlagene Schwelle {suggested:.2f}** (höchster F1 {ui.pct(best['f1'])}: Präzision "
                f"{ui.pct(best['precision'])}, Recall {ui.pct(best['recall'])}, Fehlalarme "
                f"{ui.pct(best['false_alarm_rate'])}, {best['flagged']} Anrufe markiert).  \n"
                f":gray[Nur auf diesen {len(ids)} Dev-Anrufen bestimmt: ein Hinweis, keine Kalibrierung.]")

    def _apply() -> None:
        st.session_state["cg_threshold"] = float(suggested)

    c2.button("Vorschlag übernehmen", on_click=_apply, icon=":material/done:", width="stretch",
              disabled=abs(suggested - s.threshold) < 1e-9)

st.subheader("Pro Anruf")
table = []
for cid in ids:
    call, d = truth_calls[cid], app.decided[cid].decision
    top = top_family(d, app.can_alarm)
    exp = call.expected
    table.append({
        "Anruf": cid, "Stufe": call.level, "Verrauscht": call.noisy, "Erwartet": LABEL_TEXT[exp.label],
        "System": LABEL_TEXT[d.label], "Markierung richtig": mv.is_flag(exp.label) == mv.is_flag(d.label),
        "Erwartete Art": app.family_label(exp.family) if exp.family else "",
        "Stärkste Art": short_label(top.label) if top else "", "Score": d.score,
    })
df = pd.DataFrame(table)
only_wrong = st.toggle("Nur falsche Markierungen", key="cg_quality_wrong")
if only_wrong:
    df = df[~df["Markierung richtig"]]
st.dataframe(ui.style_labels(df, "Erwartet", "System"), hide_index=True, width="stretch",
             column_config={"Score": ui.score_column(),
                            "Markierung richtig": st.column_config.CheckboxColumn()})

by_level = []
for level in sorted({truth_calls[c].level for c in ids}):
    sub = [(truth[c], app.decided[c].decision.label) for c in ids if truth_calls[c].level == level]
    lm = mv.flag_metrics(sub)
    by_level.append({"Stufe": f"Stufe {level}", "Anrufe": lm.n, "Recall": ui.pct(lm.recall),
                     "Fehlalarmquote": ui.pct(lm.false_alarm_rate), "Exakter Status": ui.pct(lm.accuracy)})
with st.expander("Nach Stufe", icon=":material/stacked_bar_chart:"):
    st.dataframe(pd.DataFrame(by_level), hide_index=True, width="stretch")

st.subheader("Holdout (Protokoll)")
if not hold:
    st.caption(f"Noch kein Holdout-Lauf protokolliert ({log_path}). Der Holdout wird einmal pro finalem Kandidaten "
               "mit `uv run callguard eval -c <profil> --split holdout` ausgewertet; jeder Lauf wird geloggt.")
else:
    st.warning(f"**Holdout: nur zur Information, nie zum Tunen.** {len(hold)} protokollierte Blicke auf den Holdout "
               f"(alle Profile). Jeder weitere Blick schwächt seine Aussagekraft.", icon=":material/lock:")
    st.dataframe(pd.DataFrame([{
        "Zeit": h.get("time"), "Profil": h.get("config"), "Art": h.get("kind"), "Anrufe": h.get("n_calls"),
        "F1": (h.get("metrics") or {}).get("flag_f1"), "Präzision": (h.get("metrics") or {}).get("flag_precision"),
        "Recall": (h.get("metrics") or {}).get("flag_recall"),
        "Fehlalarmquote": (h.get("metrics") or {}).get("false_alarm_rate"),
        "Verpasst": (h.get("metrics") or {}).get("miss_rate"),
        "Commit": ((h.get("git") or {}).get("sha") or "") + ("*" if (h.get("git") or {}).get("dirty") else ""),
    } for h in reversed(hold)]), hide_index=True, width="stretch",
        column_config={k: st.column_config.NumberColumn(format="percent") for k in
                       ("F1", "Präzision", "Recall", "Fehlalarmquote", "Verpasst")})
