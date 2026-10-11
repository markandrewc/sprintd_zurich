"""Lernen: what the officers' labels say and what they are enough for (docs/LEARNING.md).

KPI row (labels, agreement officer vs system with CI), confusion table, labels per family / fact, the
most-corrected fact questions ("Formulierung prüfen" -> rule book) and rules, readiness meters for the
four learning steps with honest thresholds, the dataset export (split hygiene enforced) and the
shadow-evaluation contract for later fine-tunes. Demo feedback can be generated here (separate store)."""

from __future__ import annotations

import json

import streamlit as st

from callguard.learning import demo as dm
from callguard.learning import export as ex
from callguard.learning import hygiene as hy
from callguard.learning import insights
from callguard.ui import learning_view as lv
from callguard.ui import render as ui
from callguard.ui.session import current_app, ground_truth

app = current_app()
st.title("Lernen aus Prüfer-Urteilen")
st.caption("Jede Beurteilung einer Prüferin ist ein Label. Heute nutzbar: Kalibrierung der Schwelle (mit "
           "Freigabe). Später: Feintuning des Faktenlesers, nur über einen Schatten-Test. Nichts lernt automatisch.")

store = lv.store_picker(st, app.runs_dir)
if store == "demo" and not app.read_only:
    with st.expander("Demo-Feedback verwalten", icon=":material/science:",
                     expanded=not lv.fb.load(app.runs_dir, "demo")):
        st.caption("Simuliert für die Dev-Anrufe aus der Sollbewertung: Urteil pro Anruf, Passagen, übersehene "
                   "Kategorie und die kleinste Fakten-Korrektur, mit der das Regelwerk die Sollbewertung ergibt. "
                   "Eigene Datei (feedback_demo.jsonl), nie im Training, nie mit echten Rückmeldungen gemischt.")

        def _seed() -> None:
            splits = hy.splits_or_none()
            if splits is None:
                st.toast("config/splits.yaml fehlt: Dev-Anrufe unbekannt.", icon=":material/error:")
                return
            gt = ground_truth(str(app.ctx.data_dir))
            n = dm.seed(app.runs_dir, app.loaded.results, list(gt.values()), splits)
            st.toast(f"{n} simulierte Labels erzeugt.", icon=":material/science:")

        c1, c2 = st.columns(2)
        c1.button("Demo-Feedback erzeugen / neu erzeugen", icon=":material/auto_fix_high:", on_click=_seed,
                  width="stretch")
        c2.button("Demo-Feedback löschen", icon=":material/delete:", on_click=dm.clear, args=(app.runs_dir,),
                  width="stretch")

ls = lv.labels(app.runs_dir, app.loaded.results, app.loaded.signature, store)
ov = insights.overview(ls)
cm = ov["confusion"]

# -- KPI row ------------------------------------------------------------------------------------
k1, k2, k3, k4 = st.columns(4)
k1.metric("Labels", ov["items"], help="Alle gespeicherten Einzelurteile (Anruf, Passage, Fakt, übersehen).")
k2.metric("Bewertete Anrufe", ov["calls"])
k3.metric("Fakten-Labels", ov["facts"], help="Aus dem Panel Rückmeldung und aus «Offene Fakten».")
k4.metric("Prüfer = System", ui.pct(cm["agreement"]),
          help=f"{cm['agree']} von {cm['n']} Anrufen gleiches Label; 95%-KI {ui.pct(cm['ci'][0])}–{ui.pct(cm['ci'][1])}"
               f" (Wilson). Markieren ja/nein: {ui.pct(cm['flag_agreement'])}.")
if not ov["items"]:
    st.info("Noch keine Labels in dieser Quelle. Rückmeldungen geben Sie im Anruf (Panel *Rückmeldung*); für die "
            "Vorführung: Quelle «Demo-Feedback» wählen und erzeugen.", icon=":material/info:")
    st.stop()

# -- agreement ------------------------------------------------------------------------------------
st.subheader("Prüfer:in vs. System")
st.caption(f"Zeilen: Urteil der Prüfer:in, Spalten: was das System gezeigt hat. {cm['false_alarms']} Fehlalarme "
           f"(System markiert, Prüfer:in sagt kein Alarm), {cm['missed']} übersehene Fälle. Übereinstimmung "
           f"{ui.pct(cm['agreement'])} (95%-KI {ui.pct(cm['ci'][0])}–{ui.pct(cm['ci'][1])}) bei n = {cm['n']}: "
           "kleine Zahlen, breites Intervall.")
st.dataframe(lv.confusion_rows(cm), hide_index=True)
if ov["disagreements"]:
    st.warning(f"Prüfer:innen sind sich uneinig bei: {', '.join(ov['disagreements'])}", icon=":material/groups:")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**Labels pro Familie**")
    st.dataframe([{"Familie": app.family_label(f), "Anrufe": n} for f, n in ov["per_family"].items()], hide_index=True)
with c2:
    st.markdown("**Fakten-Labels pro Frage**")
    st.dataframe([{"Frage": k, "Labels": n} for k, n in ov["per_fact"].items()], hide_index=True, height=240)

# -- corrections ------------------------------------------------------------------------------------
st.subheader("Was wird am häufigsten korrigiert?")
corr = insights.corrections(ls.facts)
rule_page = lv.regelwerk_page(app.pages)
for c in corr:
    if c["advice"]:
        st.warning(c["advice"], icon=":material/edit_note:")
if any(c["advice"] for c in corr):
    if rule_page is not None:
        st.page_link(rule_page, label="Zum Regelwerk (Fragen und Regeln bearbeiten)", icon=":material/gavel:")
    else:
        st.caption("Fragen und Regeln stehen in `config/policy_table.yaml` (Regelwerk).")
if corr:
    st.dataframe([{"Familie": app.family_label(c["family"]), "Frage": c["fact_label"], "Labels": c["n"],
                   "korrigiert": c["corrected"], "Quote": c["rate"], "95%-KI": f"{ui.pct(c['ci'][0])}–{ui.pct(c['ci'][1])}",
                   "Richtung": ", ".join(f"{k} ×{v}" for k, v in c["directions"].items())} for c in corr],
                 hide_index=True, column_config={"Quote": ui.score_column("Quote")})
rules = insights.rule_corrections(ls.calls, ls.facts)
if rules:
    with st.expander("Regeln, deren Ergebnis die Prüfer:innen ändern", icon=":material/rule:"):
        st.dataframe([{"Regel": r["rule"], "Anrufe": r["n"], "Urteil anders": r["corrected"], "Quote": r["rate"],
                       "95%-KI": f"{ui.pct(r['ci'][0])}–{ui.pct(r['ci'][1])}"} for r in rules],
                     hide_index=True, column_config={"Quote": ui.score_column("Quote")})

# -- readiness -------------------------------------------------------------------------------------
st.subheader("Wofür reichen die Labels?")
for r in insights.readiness(ls):
    with st.container(border=True):
        badge = (":green-badge[:material/check: bereit]" if r["ready"] else
                 ":orange-badge[:material/block: gemessen: hilft nicht]" if r["key"] == "fewshot" else
                 ":gray-badge[:material/schedule: noch nicht]")
        st.markdown(f"**{r['title']}** · {badge}" + ("" if r["key"] == "fewshot" else f" · {r['stage']}"))
        st.progress(float(r["progress"]), text=f"{r['have']:g} von {r['need']:g} {r['unit']}")
        st.caption(r["note"])
        if r["key"] == "calibration" and r["detail"]["per_family"]:
            st.caption("Pro Familie (Ziel ~30): " + ", ".join(
                f"{app.family_label(f)} {n}" for f, n in r["detail"]["per_family"].items()))
if "feedback" in app.pages:
    st.page_link(app.pages["feedback"], label="Schwelle neu kalibrieren (Feedback & Tuning)", icon=":material/tune:")

# -- export -----------------------------------------------------------------------------------------
st.subheader("Lern-Datensatz exportieren")
st.caption("Fakten-Labels im Format für Kev (noul / choice) und für ein Qwen-LoRA (Chat mit dem Prompt des "
           "Faktenchecks), Anruf-Labels für die Kalibrierung, Passagen-Labels für die Lokalisierung. Fall-Anrufe "
           "(dev / Holdout) sind nur Evaluation, Demo-Labels nie Training; der Export bricht ab statt zu lecken.")
use_counts = ov["fact_uses"]
st.markdown(" · ".join(f"{hy.USE_DE.get(u, u)}: **{n}**" for u, n in sorted(use_counts.items())) or "–")
if st.button("Exportieren", icon=":material/download:", disabled=app.read_only):
    try:
        built = ex.build(ls, app.loaded.results, hy.splits_or_none())
        man = ex.manifest(built, ls, hy.splits_or_none())
        out = ex.write(app.runs_dir / "learning" / ("export_demo" if store == "demo" else "export"), built, man)
        st.success(f"Geschrieben nach `{out}`", icon=":material/check:")
        st.json(man["files"])
        st.download_button("manifest.json", json.dumps(man, ensure_ascii=False, indent=2), "manifest.json",
                           mime="application/json")
    except hy.HygieneError as e:
        st.error(f"Export verweigert (Split-Hygiene): {e}", icon=":material/gpp_bad:")

# -- shadow evaluation ------------------------------------------------------------------------------
st.subheader("Bevor ein neues Modell live geht")
st.markdown(lv.SHADOW_DE)
st.info(lv.PITCH_DE, icon=":material/verified_user:")
st.caption("Ablauf und Skripte (nicht ausgeführt): `finetune/README.md`, `finetune/kev_lora.sh`, "
           "`finetune/qwen_lora.sh`; Details in `docs/LEARNING.md`.")
