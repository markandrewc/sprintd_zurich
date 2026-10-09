"""Feedback & tuning: officer verdicts -> suggested threshold with expected false alarms / misses,
keywords to reconsider, check reliability -> save as the tuning overlay (``config/tuning.yaml``)."""

from __future__ import annotations

import streamlit as st

from callguard import feedback as fb
from callguard.ui.session import current_app, reload_everything

app = current_app()
st.title("Feedback & Tuning")
st.caption("Rückmeldungen geben Sie im Anruf (Panel *Rückmeldung*). Hier wird daraus ein Vorschlag: nur die "
           "Entscheidungsregel wird neu gerechnet, keine Transkription, kein Sprachmodell.")

items = fb.load(app.runs_dir)
pipe = app.engine.pipeline
if items:
    with st.expander(f"{len(items)} Rückmeldungen", icon=":material/rate_review:"):
        st.dataframe([{"Zeit": i.ts, "Wer": i.user, "Anruf": i.call_id, "Urteil": fb.VERDICT_DE[i.verdict],
                       "Gesehen": i.label_seen, "Passage": None if i.passage_index is None else i.passage_index + 1,
                       "Kommentar": i.comment} for i in reversed(items)], hide_index=True)

truth_mode = st.radio("Zusätzlich Sollbewertung verwenden (nur Anrufe ohne Rückmeldung)",
                      ["nein", "Dev-Dialoge", "alle (nicht für die Abgabe-Konfiguration!)"], horizontal=True,
                      help="Holdout-Disziplin: die Holdout-Dialoge dürfen nichts tunen; 'Dev-Dialoge' lässt sie weg.")
truth = None
if truth_mode != "nein":
    from callguard.ui.session import ground_truth

    gt = ground_truth(str(app.ctx.data_dir))
    truth = {cid: c.expected.label for cid, c in gt.items() if c.expected}
    if truth_mode == "Dev-Dialoge":
        from callguard import splits as sp

        s = sp.load_splits(required=False)
        if s is None:
            st.warning("Kein config/splits.yaml: Dev-Dialoge unbekannt, Sollbewertung nicht verwendet.")
            truth = None
        else:
            dev = set(s.dev_dialogues())
            truth = {k: v for k, v in truth.items() if gt[k].dialogue_id in dev}

if pipe is None:
    st.warning(f"Vorschläge brauchen die Pipeline ({app.engine.error}).")
    st.stop()

results = [app.loaded.results[c] for c in sorted(app.loaded.results)]
s = fb.suggest(pipe, results, items, truth=truth, overrides=app.settings.overrides())
st.markdown(f"**{s['n_labelled']}** bewertete Anrufe (Rückmeldung {s['sources']['feedback']}, "
            f"Sollbewertung {s['sources']['ground_truth']}).")
if s["warning"]:
    st.warning(s["warning"], icon=":material/info:")

if s["suggestion"]:
    cur, sug, d = s["current"], s["suggestion"], s["delta"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Schwelle jetzt", f"{s['current_threshold']:.2f}")
    c2.metric("Vorschlag", f"{sug['threshold']:.2f}", f"{sug['threshold'] - s['current_threshold']:+.2f}",
              delta_color="off")
    c3.metric("Fehlalarme", sug["fp"], d["fp"], delta_color="inverse")
    c4.metric("Verpasste Fälle", sug["fn"], d["fn"], delta_color="inverse")
    st.caption(sug["reason"] + f" Arbeitslast: Alarme {d['alarms']:+d}, Prüfen {d['reviews']:+d}.")
    st.dataframe([{"Schwelle": r["threshold"], "Fehlalarme": r["fp"], "Verpasst": r["fn"], "Alarme": r["alarms"],
                   "Prüfen": r["reviews"], "F1": r["f1"]} for r in s["sweep"]], hide_index=True)

    def _save(threshold: float, band: float | None, weights: dict | None, reason: str) -> None:
        fb.apply_tuning(fb.tuning_path(app.cfg), app.cfg.name, threshold=threshold, review_band=band,
                        weights=weights, runs_dir=app.runs_dir, reason=reason)
        st.session_state["cg_threshold"] = float(threshold)
        if band is not None:
            st.session_state["cg_band"] = float(band)
        reload_everything()
        st.toast("Gespeichert in tuning.yaml (gilt ab jetzt für dieses Profil).", icon=":material/save:")

    b1, b2 = st.columns(2)
    b1.button("Vorschlag als Standard speichern", icon=":material/done:", width="stretch", on_click=_save,
              args=(sug["threshold"], None, None, f"Vorschlag aus {s['n_labelled']} bewerteten Anrufen: "
                                                  f"FP {d['fp']:+d}, FN {d['fn']:+d}"))
    st_ = app.settings
    b2.button("Aktuelle Regler als Standard speichern", icon=":material/save:", width="stretch", on_click=_save,
              args=(st_.threshold, st_.review_band, dict(st_.weights) or None, "Regler aus der Seitenleiste"))
    if app.cfg.tuning:
        st.caption(f"Aktives Overlay: `{app.cfg.tuning['path']}` (Hash {app.cfg.tuning['hash']}): "
                   + ", ".join(f"{k}={v}" for k, v in app.cfg.tuning["applied"].items()))

st.subheader("Stichwörter")
kws = s["keywords"]
if kws:
    for k in kws:
        if k["suggest_disable"]:
            st.warning(k["advice"], icon=":material/label_off:")
    st.dataframe([{"Stichwort": k["keyword"], "Anrufe": k["calls"], "markierungswürdig": k["flagged"],
                   "harmlos": k["harmless"], "Präzision": k["precision"]} for k in kws], hide_index=True)
    if "keywords" in app.pages:
        st.page_link(app.pages["keywords"], label="Stichwortliste bearbeiten", icon=":material/tune:")
else:
    st.caption("Keine Stichwort-Treffer in bewerteten Anrufen.")

st.subheader("Prüfungen")
if s["checks"]:
    st.caption("Mittlerer höchster Score je Prüfung auf markierungswürdigen vs. harmlosen Anrufen; Trennung = Differenz.")
    st.dataframe(s["checks"], hide_index=True)
