"""Team-Entscheidungen: every option for the open team decisions side by side, for the team review.

Candidate matrix (``callguard candidates`` -> ``runs/candidates/candidates.json``, or computed live from the stored
rows when that file is missing or older than the data: statistics only, no ASR, no LLM), the dev-fitting chart
(tuned vs reworded / blind / re-recorded AUC), one card per open decision (texts: experiments/contrib/decisions.yaml,
numbers filled in from the matrix) with a form that records the team's choice in
experiments/contrib/team_decisions.yaml, and the comparison with the teammate's prototype
(experiments/contrib/comparison_zurich.yaml, warns when the teammate repo moved on). Pending cells
("läuft noch" / "ausstehend") fill in on reload as soon as their rows.json appear.
"""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import streamlit as st

from callguard import candidates as cd
from callguard.ui import render as ui
from callguard.ui import team_view as tv
from callguard.ui.session import current_app

ENV_TEAM = "CALLGUARD_TEAM_DECISIONS"

app = current_app()

st.title("Team-Entscheidungen")
st.caption("Alle Optionen für die offenen Team-Entscheide nebeneinander, mit denselben Zahlen: Dev-Split (48 Anrufe, "
           "24 Dialoge), 95%-Bootstrap-Intervalle, gepaart gegen den Champion. **Fett** = bester Wert der Spalte; "
           "ein Unterschied gilt nur als belegt, wenn das gepaarte Intervall 0 ausschliesst, sonst „≈ Champion“. "
           "Es läuft kein Modell. Fehlende Zellen („läuft noch“, „ausstehend“) füllen sich beim Neuladen.")
if "decisions" in app.pages:
    st.page_link(app.pages["decisions"], label="Welche Komponente bringt was? → Entscheidungshilfe (Faktoren)",
                 icon=":material/balance:")

roots = {"default": app.runs_root / "experiments", "perturbed": app.runs_root / "perturbed" / "experiments",
         "test50": app.runs_root / "test50" / "experiments"}
out_dir = app.runs_root / "candidates"
team_path = Path(os.environ.get(ENV_TEAM) or cd.DEFAULT_TEAM)
with st.expander("Datenquelle", icon=":material/folder_open:"):
    st.markdown(f"Ergebnisse: `{roots['default']}` und `{roots['perturbed']}` · Zuordnung "
                f"`experiments/contrib/candidates.yaml` · Texte `experiments/contrib/decisions.yaml`, "
                f"`comparison_zurich.yaml` · Team-Entscheide `{team_path}`.")
    st.markdown("Neu rechnen mit Beleg-Trefferquote und Markdown-Bericht: `uv run callguard candidates`.")
    if st.button("Neu berechnen", icon=":material/refresh:", key="cg_team_refresh"):
        st.cache_data.clear()

try:
    spec = cd.load_spec()
except (FileNotFoundError, cd.SpecError) as e:
    st.error(f"Kandidaten-Spezifikation fehlt oder ist ungültig: {e}", icon=":material/error:")
    st.stop()


@st.cache_data(show_spinner=False)
def _load(spec_path: str, roots_key: tuple[tuple[str, str], ...], out: str, stamp: tuple[float, float]) -> tuple[dict, str]:
    return cd.load_or_compute(spec_path, out, dict(roots_key))


json_path = out_dir / "candidates.json"
data = cd.Data({**cd.DEFAULT_ROOTS, **roots}, spec.get("experiments_dir"), cd.root_datasets(spec))
stamp = (data.fingerprint(spec["_path"]), json_path.stat().st_mtime if json_path.exists() else 0.0)
with st.spinner("Kandidaten werden gerechnet …"):
    result, origin = _load(spec["_path"], tuple(sorted((k, str(v)) for k, v in roots.items())), str(out_dir), stamp)

decisions = cd.load_yaml(None, cd.DEFAULT_DECISIONS)
comparison = cd.load_yaml(None, cd.DEFAULT_COMPARISON)
team = cd.load_team(team_path)
visible = cd.visible(result)
have = [c for c in visible if c.get("tuned")]

st.caption(f":gray[Quelle: {'runs/candidates/candidates.json' if origin == 'file' else 'live berechnet'} · "
           f"{result['n_boot']} Bootstrap-Stichproben · {result['created']} · Beleg-Trefferquote nur nach "
           f"`callguard candidates` (Cache)]")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Kandidaten mit Daten", f"{len(have)} / {len(visible)}")
c2.metric("Zellen ausstehend / läuft noch", len(result.get("pending") or []))
c3.metric("Offene Entscheide", sum(1 for d in decisions.get("decisions") or [] if d.get("id") not in team))
c4.metric("Entschieden", sum(1 for d in decisions.get("decisions") or [] if d.get("id") in team))

# -- 1. matrix --------------------------------------------------------------------------------------

st.subheader("Optionen für das Team: Kandidaten-Matrix")
if not have:
    st.info(f"Keine der Kandidaten-Varianten liegt in `{roots['default']}`. Experimente laufen auf den GPU-Rechnern; "
            "die Ergebnisse hierher kopieren.", icon=":material/science:")
else:
    v1, v2 = st.columns([3, 4], vertical_alignment="bottom")
    view = v1.segmented_control("Ansicht", ["Werte mit KI", "Sortierbar (Zahlen)"], default="Werte mit KI",
                                key="cg_team_view") or "Werte mit KI"
    groups = list(dict.fromkeys(c.get("group") or "" for c in visible))
    picked = v2.pills("Gruppen", groups, selection_mode="multi", default=groups, key="cg_team_groups") or groups
    if view == "Werte mit KI":
        df = tv.text_frame(result)
        df = df[df["Gruppe"].isin(picked)].reset_index(drop=True)
        cfg = {c: st.column_config.TextColumn(c, width="medium") for c in df.columns}
        cfg["gepaart vs. Champion"] = st.column_config.TextColumn(width="large")
    else:
        df = tv.number_frame(result)
        df = df[df["Gruppe"].isin(picked)].reset_index(drop=True)
        cfg = {col: st.column_config.NumberColumn(format="%.0f%%" if pct else ("%.1f" if key == "cost" else "%.2f"))
               for col, (key, pct) in tv.NUM_COLS.items()}
        cfg.update({col: st.column_config.NumberColumn(format="%+.2f", help="Gepaarte AUC-Differenz zum eigenen "
                                                       "abgestimmten Lauf (gleiche Anrufe).") for col in tv.DROP_COLS})
        cfg.update({col: st.column_config.NumberColumn(format="%.0f%%" if pct else "%.2f")
                    for col, (key, pct) in tv.T50_NUM_COLS.items()})
        cfg[tv.T50_PREFIX + "Dev → test50 (ungepaart)"] = st.column_config.NumberColumn(
            format="%+.2f", help="AUC test50 minus AUC Dev: verschiedene Anrufe, getrennt gebootet, nie gepoolt.")
        cfg["Daten"] = st.column_config.TextColumn(width="large")
    st.dataframe(tv.style(df, result), hide_index=True, width="stretch", column_config=cfg)
    st.caption("Blau hinterlegt = **test50**: eigener, externer Datensatz (fixe Schwelle = auf Dev eingefroren; CV "
               "innerhalb test50 nur zum Vergleich), nie mit den Dev-Spalten gepoolt. "
               "Grau hinterlegt = Generalisierung (dasselbe System ausserhalb der Dev-Bedingungen): umformulierte "
               "Fragen (Mittel der Paraphrasen-Sätze), blinde Tabelle (Fragen und Regeln nur aus den Kriterien), neu "
               "aufgenommenes Audio (Tempo 0.96, −3 dB). Δ = gepaarte Differenz zum eigenen abgestimmten Lauf. "
               "Beleg hit@1 immer mit „Zufall“ lesen: lange Passagen treffen schon zufällig. n/a = nicht anwendbar.")
    notes = [c for c in visible if c.get("note")]
    if notes:
        with st.expander("Anmerkungen je Kandidat", icon=":material/info:"):
            st.markdown("\n".join(f"- **{ui.esc(c.get('label') or c['id'])}**: {ui.esc(c['note'])}" for c in notes))

    # -- 2. chart --------------------------------------------------------------------------------------

    st.subheader("Abgestimmt gegen andere Bedingungen: wie viel ist Dev-Anpassung?")
    cond = st.pills("Bedingung", list(tv.CONDITIONS), default="reworded", format_func=lambda k: tv.CONDITIONS[k],
                    key="cg_team_condition") or "reworded"
    ddf = tv.dumbbell_frame(result, cond)
    if len(ddf):
        st.altair_chart(tv.dumbbell_chart(ddf, cond), width="stretch")
        st.caption(f"● dunkel = abgestimmte Dev-Fragen, ◆ hell = {tv.CONDITIONS[cond]}; Linien = 95%-Intervalle. "
                   "Ein langer Abstand heisst: das Ergebnis hängt an der auf Dev geschriebenen Formulierung bzw. am "
                   "Audio. Rechts steht, wo die Bedingung noch fehlt. Zahlen im Tooltip und in der Matrix.")

# -- 2b. test50 (external held-out set) -----------------------------------------------------------

st.subheader(f"Externer Testsatz {cd.T50_TITLE}")
st.warning(cd.T50_BANNER, icon=":material/shield:")
bdf = tv.breakdown_frame(result)
if len(bdf):
    st.markdown("**Exakt richtig je Anruf-Typ und Aufnahme** (fixe Schwelle; Anzahl Anrufe in Klammern). Typen: "
                "Paar = A/B-Zwillinge, die sich nur im entscheidenden Detail unterscheiden; Stichwort-Falle = "
                "harmloser Anruf mit Reizwörtern; Prüfen-Fall; Zahlen-Paar (nie Alarm); mehrere Themen.")
    st.dataframe(bdf, hide_index=True, width="stretch")
    st.caption("Die Kennzahlen mit Intervallen und der gepaarte Vergleich gegen den Champion (über A/B-Paare) stehen "
               "in den blauen Spalten der Matrix oben. Sehr wenige Anrufe je Typ (10-60): eine Zelle kippt mit einem Paar.")
else:
    t50p = tv.t50_pending(result)
    st.info("Noch keine test50-Ergebnisse. Erwartet unter `runs/test50/experiments/test50/<variante>/` "
            f"(experiments/test50.yaml): {len(t50p)} Varianten ausstehend.", icon=":material/hourglass_empty:")

# -- 3. decisions -----------------------------------------------------------------------------------

st.subheader("Offene Entscheidungen")
if decisions.get("_missing"):
    st.info(f"Keine Entscheidungstexte gefunden (`{decisions['_path']}`).", icon=":material/description:")
if decisions.get("intro"):
    st.caption(cd.fill(decisions["intro"], result))
for raw in decisions.get("decisions") or []:
    d = cd.fill(raw, result)
    did = d.get("id") or d.get("title")
    chosen = team.get(did)
    badge = f" · entschieden: {chosen.get('choice')}" if chosen else " · offen"
    with st.expander(f"{d.get('title') or did}{badge}", icon=":material/how_to_vote:" if not chosen
                     else ":material/task_alt:"):
        if d.get("question"):
            st.markdown(f"**Frage:** {d['question']}")
        if d.get("context"):
            st.markdown(d["context"])
        opts = d.get("options") or []
        for i in range(0, len(opts), 3):
            cols = st.columns(min(3, len(opts) - i))
            for col, o in zip(cols, opts[i:i + 3]):
                with col.container(border=True):
                    st.markdown(f"**{o.get('name')}**")
                    if o.get("summary"):
                        st.caption(o["summary"])
                    lines = [f"- :green[pro] {x}" for x in cd._as_list(o.get("pros"))]
                    lines += [f"- :red[contra] {x}" for x in cd._as_list(o.get("cons"))]
                    if lines:
                        st.markdown("\n".join(lines))
                    if o.get("cost"):
                        st.caption(f"Aufwand: {o['cost']}")
        if d.get("recommendation"):
            st.info(f"**Unsere Empfehlung:** {d['recommendation']}", icon=":material/recommend:")
        if d.get("would_change"):
            st.markdown("**Was die Empfehlung ändern würde:**\n" + "\n".join(f"- {x}" for x in cd._as_list(d["would_change"])))
        if d.get("sources"):
            st.caption("Quellen: " + ", ".join(f"`{s}`" for s in cd._as_list(d["sources"])))
        if chosen:
            st.success(f"**Entscheid des Teams:** {chosen.get('choice')} ({chosen.get('who', '?')}, "
                       f"{chosen.get('when', '?')})" + (f": {chosen['note']}" if chosen.get("note") else ""),
                       icon=":material/task_alt:")
        with st.form(f"cg_team_form_{did}", border=False):
            names = tv.decision_options(d) + ["anderes (Notiz)", "vertagt"]
            cur = names.index(chosen["choice"]) if chosen and chosen.get("choice") in names else 0
            f1, f2 = st.columns([3, 2])
            choice = f1.selectbox("Entscheid des Teams", names, index=cur, key=f"cg_team_choice_{did}")
            who = f2.text_input("Wer", value=(chosen or {}).get("who", ""), key=f"cg_team_who_{did}")
            note = st.text_area("Notiz / Begründung", value=(chosen or {}).get("note", ""), height=68,
                                key=f"cg_team_note_{did}")
            if st.form_submit_button("Entscheid speichern", icon=":material/save:"):
                if not who.strip():
                    st.warning("Bitte angeben, wer entschieden hat.", icon=":material/person:")
                else:
                    p = cd.save_team_decision(did, {"choice": choice, "who": who.strip(), "note": note.strip()},
                                              team_path)
                    st.toast(f"Gespeichert in {p.name}", icon=":material/save:")
                    st.rerun()

# -- 4. teammate comparison -------------------------------------------------------------------------

if comparison.get("rows"):
    st.subheader("Unser Ansatz vs. sprintd_zurich (Teamkollege)")
    z = cd.zurich_status(comparison)
    want = str(comparison.get("written_against") or "?")
    if z["stale"]:
        st.warning(f"Das Repo des Teamkollegen steht jetzt auf `{(z['head'] or '?')[:7]}`, der Vergleich wurde gegen "
                   f"`{want[:7]}` geschrieben: geänderte Dateien lesen und `experiments/contrib/comparison_zurich.yaml` "
                   "aktualisieren.", icon=":material/sync_problem:")
    elif not z["available"]:
        st.caption(f":gray[Repo `{z['repo']}` hier nicht vorhanden: Stand nicht prüfbar (geschrieben gegen `{want[:7]}`).]")
    else:
        st.caption(f":gray[Geschrieben gegen `{want[:7]}` = aktueller Stand von `{z['repo']}`.]")
    comp = cd.fill(comparison, result)
    if comp.get("intro"):
        st.caption(comp["intro"])
    cdf = tv.comparison_frame(comp)
    recs = list(dict.fromkeys(cdf["Empfehlung"]))
    sel = st.pills("Empfehlung", recs, selection_mode="multi", default=recs, key="cg_team_rec") or recs
    st.dataframe(cdf[cdf["Empfehlung"].isin(sel)], hide_index=True, width="stretch", column_config={
        c: st.column_config.TextColumn(width="large") for c in ("Unser Ansatz", "sprintd_zurich", "Messung / Beleg")})
    counts = pd.Series(cdf["Empfehlung"]).value_counts()
    st.caption(" · ".join(f"{k}: {v}" for k, v in counts.items()))

pending = tv.pending_lines(result)
if pending:
    with st.expander(f"Ausstehend ({len(pending)}): erscheint automatisch, sobald die Ergebnisse da sind",
                     icon=":material/hourglass_empty:"):
        st.markdown("\n".join(f"- {p}" for p in pending))
