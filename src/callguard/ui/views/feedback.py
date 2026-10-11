"""Feedback & Tuning: officer labels -> a threshold re-fit with dialogue-fold cross-validation and a CI ->
a *proposal* that a second person approves (four-eyes) or rejects, with rollback. Nothing is applied
automatically. Below: the threshold sweep, keywords to reconsider and check reliability (same labels).
Learning statistics and readiness are on the page "Lernen" (``views/learning.py``)."""

from __future__ import annotations

import streamlit as st

from callguard import feedback as fb
from callguard.learning import proposals as pr
from callguard.learning import recalibrate
from callguard.ui import learning_view as lv
from callguard.ui.panels.feedback import officer_name
from callguard.ui.session import current_app, reload_everything

app = current_app()
st.title("Feedback & Tuning")
st.caption("Rückmeldungen geben Sie im Anruf (Panel *Rückmeldung*). Hier wird daraus ein Vorschlag für die "
           "Alarmschwelle: nur die Entscheidungsregel wird neu gerechnet, keine Transkription, kein Sprachmodell. "
           "Ein Vorschlag gilt erst, wenn eine zweite Person ihn genehmigt.")

store = lv.store_picker(st, app.runs_dir)
results = app.loaded.results
ls = lv.labels(app.runs_dir, results, app.loaded.signature, store)
items = ls.items
if items:
    with st.expander(f"{len(items)} Rückmeldungen ({len(ls.calls)} Anrufe mit Urteil)", icon=":material/rate_review:"):
        st.dataframe([{"Zeit": i.ts, "Wer": i.user, "Anruf": i.call_id, "Urteil": fb.VERDICT_DE.get(i.verdict, i.verdict),
                       "Betrifft": {"call": "Anruf", "passage": "Passage", "fact": f"Fakt {i.fact}",
                                    "family": f"übersehen: {i.family}"}[i.target],
                       "Gesehen": i.label_seen, "Kommentar": i.comment} for i in reversed(items)], hide_index=True)
else:
    st.info("Noch keine Rückmeldungen in dieser Quelle. Für die Vorführung: Seite *Lernen* -> Demo-Feedback erzeugen.",
            icon=":material/info:")

pipe = app.engine.pipeline
if pipe is None:
    st.warning(f"Vorschläge brauchen die Pipeline ({app.engine.error}).")
    st.stop()

name = officer_name(st.sidebar, key="cg_fb_page_name", label="Ihr Name (Freigaben)")
overrides = app.settings.overrides()

# -- 1. threshold re-fit -----------------------------------------------------------------------
st.subheader("Alarmschwelle aus Rückmeldungen")
rec = lv.refit(pipe, results, ls, app.loaded.signature, overrides)
st.caption(f"{rec['n_calls']} nutzbare bewertete Anrufe aus {rec['n_units']} unabhängigen Gesprächsgruppen "
           f"(Alarm {rec['label_counts'].get('alarm', 0)}, Prüfen {rec['label_counts'].get('review', 0)}, "
           f"kein Alarm {rec['label_counts'].get('no_alert', 0)})"
           + (f"; {len(rec['dropped'])} Holdout-Anrufe nicht verwendet" if rec["dropped"] else "") + ".")
if rec["proposed_threshold"] is None:
    st.info(rec.get("message") or recalibrate.VERDICT_DE["too_few"], icon=":material/hourglass_empty:")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Schwelle jetzt", f"{rec['current_threshold']:.2f}")
    c2.metric("Neu gewählt", f"{rec['proposed_threshold']:.2f}",
              f"{rec['proposed_threshold'] - rec['current_threshold']:+.2f}", delta_color="off")
    f1 = rec["effect"].get("flag_f1") or {}
    far = rec["effect"].get("false_alarm_rate") or {}
    c3.metric("F1-Differenz (CV)", "–" if f1.get("diff") is None else f"{f1['diff']:+.3f}",
              help=f"95%-KI {lv._ci(f1.get('lo'), f1.get('hi'))}", delta_color="off")
    c4.metric("Fehlalarmquote-Differenz (CV)", "–" if far.get("diff") is None else f"{far['diff']:+.3f}",
              help=f"95%-KI {lv._ci(far.get('lo'), far.get('hi'))}", delta_color="off")
    box = {"better": st.success, "worse": st.error}.get(rec["verdict"], st.info)
    box(recalibrate.VERDICT_DE[rec["verdict"]], icon=":material/query_stats:")
    with st.expander("Wie geschätzt?", icon=":material/science:"):
        st.markdown(
            "Die Schwelle wird in jeder Runde auf den **anderen** Gesprächs-Folds gewählt und auf dem "
            "ausgelassenen Fold angewendet (Kreuzvalidierung; saubere und verrauschte Aufnahme eines Gesprächs "
            "immer im selben Fold). Verglichen wird mit der aktuellen Schwelle auf denselben Anrufen, das "
            "Konfidenzintervall kommt aus einem gepaarten Bootstrap über Gesprächsgruppen. Holdout-Anrufe "
            "werden nie verwendet.")
        if rec.get("cv"):
            st.caption("Schwelle pro Fold: " + ", ".join(f"Fold {f['fold']}: {f['threshold']:.2f}" for f in rec["cv"]["folds"]))
        st.dataframe(lv.effect_rows(rec["effect"]), hide_index=True)

    def _propose(change: dict, reason: str, evidence: dict) -> None:
        try:
            p = pr.propose(app.runs_dir, app.cfg.name, change, user=name, reason=reason, evidence=evidence,
                           label_source=store)
            st.toast(f"{p.id} eingereicht: wartet auf Freigabe durch eine zweite Person.", icon=":material/outbox:")
        except (pr.FourEyesError, ValueError) as e:
            st.toast(str(e), icon=":material/error:")

    b1, b2 = st.columns(2)
    can_fit = rec["verdict"] not in ("keep", "too_few") and rec["proposed_threshold"] is not None
    b1.button("Neu gewählte Schwelle als Vorschlag einreichen", icon=":material/outbox:", width="stretch",
              disabled=not can_fit or not name, on_click=_propose,
              args=({"threshold": rec["proposed_threshold"]},
                    f"Re-Fit aus {rec['n_calls']} bewerteten Anrufen ({store}): {rec['verdict']}", lv.evidence_of(rec)),
              help=None if can_fit else recalibrate.VERDICT_DE.get(rec["verdict"]))
    s_ = app.settings
    b2.button("Aktuelle Regler als Vorschlag einreichen", icon=":material/tune:", width="stretch",
              disabled=not name, on_click=_propose,
              args=({"threshold": s_.threshold, "review_band": s_.review_band}, "Regler aus der Seitenleiste",
                    lv.evidence_of(rec)))

# -- 2. proposals (four-eyes) ------------------------------------------------------------------
st.subheader("Vorschläge (Vier-Augen-Prinzip)")
props = [p for p in pr.load(app.runs_dir) if p.profile == app.cfg.name]
if not props:
    st.caption("Keine Vorschläge für dieses Profil.")
else:
    st.dataframe(lv.proposal_rows(props), hide_index=True)
tp = fb.tuning_path(app.cfg)


def _act(kind: str, pid: str) -> None:
    try:
        if kind == "approve":
            pr.approve(app.runs_dir, pid, user=name, tuning_path=tp)
            st.session_state.pop("cg_threshold", None)
            st.session_state.pop("cg_band", None)
            reload_everything()
        elif kind == "reject":
            pr.reject(app.runs_dir, pid, user=name)
        else:
            pr.rollback(app.runs_dir, pid, user=name, tuning_path=tp)
            st.session_state.pop("cg_threshold", None)
            st.session_state.pop("cg_band", None)
            reload_everything()
        st.toast(f"{pid}: {pr.STATUS_DE[pr.get(app.runs_dir, pid).status]}", icon=":material/check:")
    except (pr.FourEyesError, pr.ProposalStateError, KeyError, ValueError) as e:
        st.toast(str(e), icon=":material/block:")


for p in props:
    if p.status not in ("open", "approved"):
        continue
    with st.container(border=True):
        ev = p.evidence or {}
        st.markdown(f"**{p.id}** · {', '.join(f'{k} = {v:.2f}' for k, v in p.change.items())} · vorgeschlagen von "
                    f"**{p.proposed_by}** · {pr.STATUS_DE[p.status]}"
                    + (" · :orange-badge[Demo-Labels]" if p.label_source == "demo" else ""))
        if ev.get("n_calls"):
            st.caption(f"Grundlage: {ev['n_calls']} Anrufe, {ev.get('n_units')} Gruppen; "
                       f"{recalibrate.VERDICT_DE.get(ev.get('verdict'), '')}")
        if p.reason:
            st.caption(f"Begründung: {p.reason}")
        own = bool(name) and pr._norm(name) == pr._norm(p.proposed_by)
        cols = st.columns(3)
        if p.status == "open":
            cols[0].button("Genehmigen", key=f"cg_pr_ok_{p.id}", icon=":material/verified:", type="primary",
                           disabled=own or not name, on_click=_act, args=("approve", p.id),
                           help="Vier-Augen-Prinzip: nicht durch die vorschlagende Person." if own else None)
            cols[1].button("Ablehnen", key=f"cg_pr_no_{p.id}", icon=":material/block:", disabled=own or not name,
                           on_click=_act, args=("reject", p.id))
            if own:
                cols[2].caption("Ihr eigener Vorschlag: eine zweite Person muss ihn freigeben.")
        else:
            cols[0].button("Zurückrollen", key=f"cg_pr_rb_{p.id}", icon=":material/undo:", disabled=not name,
                           on_click=_act, args=("rollback", p.id),
                           help="Stellt den Stand vor der Freigabe wieder her (protokolliert).")
            st.caption(f"Genehmigt von {p.approved_by} am {p.approved_at}.")
if app.cfg.tuning:
    st.caption(f"Aktives Overlay: `{app.cfg.tuning['path']}` (Hash {app.cfg.tuning['hash']}): "
               + ", ".join(f"{k}={v}" for k, v in app.cfg.tuning["applied"].items()))

# -- 3. details on the same labels --------------------------------------------------------------
s = fb.suggest(pipe, [results[c] for c in sorted(results)], items, overrides=overrides)
with st.expander("Schwellen-Sweep auf den bewerteten Anrufen (ohne Kreuzvalidierung)", icon=":material/table_chart:"):
    if s["warning"]:
        st.caption(s["warning"])
    if s["sweep"]:
        st.dataframe([{"Schwelle": r["threshold"], "Fehlalarme": r["fp"], "Verpasst": r["fn"], "Alarme": r["alarms"],
                       "Prüfen": r["reviews"], "F1": r["f1"]} for r in s["sweep"]], hide_index=True)

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
