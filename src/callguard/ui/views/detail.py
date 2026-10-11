"""Call detail: why the call got its label (and, if it is "Prüfen", why the system is unsure), the evidence
timeline (click a marker -> the recording jumps there), the suspicious passages with criterion, supporting
checks, reasons, every view's text and the audio snippet, "Warum kein Alarm?" for keyword-heavy calls
that stayed quiet, what each check said, extra panels from ``callguard.ui.panels``, and the transcript per
view.

Deep link: ``?call=<id>&t=<seconds>`` (alert triggers) opens the call with the recording at ``t``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from callguard.types import fmt_ts
from callguard.ui import explain as ex
from callguard.ui import render as ui
from callguard.ui.backend import (
    LABEL_TEXT,
    check_problems,
    checks_said,
    headline_reason,
    linked_passage,
    parse_seconds,
    short_label,
    top_family,
)
from callguard.ui.panels import panels
from callguard.ui.session import current_app, ground_truth

app = current_app()
s = app.settings

if not app.loaded.results:
    st.title("Anruf")
    st.info(f"Noch keine verarbeiteten Anrufe in `{app.runs_dir}`. Einen Anruf verarbeiten: Seite "
            "**Anruf verarbeiten**.", icon=":material/inbox:")
    st.stop()

order = [r["call_id"] for r in app.rows()]
wanted = st.query_params.get("call") or st.session_state.get("cg_last_call") or order[0]
missing = wanted not in app.loaded.results
call_id = order[0] if missing else wanted
st.session_state["cg_last_call"] = call_id
if not missing and st.query_params.get("call") != call_id:  # keep the URL shareable
    st.query_params["call"] = call_id
t = parse_seconds(st.query_params.get("t")) if not missing else None


def _pick() -> None:
    st.query_params.clear()
    st.query_params["call"] = st.session_state["cg_detail_pick"]


def _step(delta: int) -> None:
    i = (order.index(call_id) + delta) % len(order)
    st.query_params.clear()
    st.query_params["call"] = order[i]


def _fmt(cid: str) -> str:
    d = app.decided[cid].decision
    return f"{cid}  ·  {LABEL_TEXT[d.label]}  ·  {d.score:.2f}"


st.session_state["cg_detail_pick"] = call_id  # the URL is the source of truth, the picker follows it
nav1, nav2, nav3 = st.columns([6, 1, 1], vertical_alignment="bottom")
nav1.selectbox("Anruf", order, format_func=_fmt, key="cg_detail_pick", on_change=_pick,
               help="Anrufe nach Score sortiert, riskantester zuerst.")
nav2.button("Zurück", icon=":material/arrow_back:", on_click=_step, args=(-1,), width="stretch")
nav3.button("Weiter", icon=":material/arrow_forward:", on_click=_step, args=(1,), width="stretch")
if missing:
    st.warning(f"Für Anruf `{wanted}` gibt es kein Ergebnis in `{app.runs_dir}` (nicht mit dieser Quelle "
               f"verarbeitet?). Stattdessen: `{call_id}`.", icon=":material/search_off:")

result = app.loaded.results[call_id]
dd = app.decided[call_id]
d = dd.decision
result_dir = app.result_dir(call_id)
top = top_family(d, app.can_alarm)
colors = ui.family_colors(app.all_families)
views = result.all_views()
view_titles = {name: ex.view_title(name, tr) for name, tr in views.items()}
thr = d.threshold if dd.live else s.threshold  # per-family thresholds may shift the decision's own
floor = max(0.0, round(thr - s.review_band, 6))

# -- header ------------------------------------------------------------------------------------

st.title(f"{call_id} {ui.label_md(d.label)}", anchor=False)
fam_line = f"**{ui.esc(top.label)}**" if top else "Keine Art von Fehlverhalten über null"
dur = ex.call_duration(result)
st.markdown(f"{fam_line} · {len(d.passages)} verdächtige Passage{'n' if len(d.passages) != 1 else ''}"
            f" · Anruf {fmt_ts(dur)}" + (f" · {len(views)} Transkript-Ansichten" if len(views) > 1 else ""))

headline = headline_reason(d, result, s.weights, app.can_alarm)
causes = ex.review_causes(result, d, threshold=thr, review_band=s.review_band, max_uncertainty=s.max_uncertainty,
                          min_score_for_review=float(app.defaults.get("min_score_for_review", 0.25)),
                          can_alarm=app.can_alarm, weights=s.weights)
if d.label == "alarm":
    st.error(f"**Alarm.** {ui.esc(headline)}  \nHören Sie die Passagen unten an und eskalieren Sie, wenn sich "
             "der Verdacht bestätigt.", icon=":material/notifications_active:")
elif d.label == "review":
    body = "\n".join(f"- **{ui.esc(c.title)}:** {ui.esc(c.text)}" for c in causes) or f"- {ui.esc(headline)}"
    st.warning("**Prüfen: Unsicher → an Menschen übergeben.** Das System entscheidet diesen Anruf nicht "
               f"allein. Warum:\n{body}\n\nBitte die Passagen anhören und selbst entscheiden.",
               icon=":material/person_search:")
else:
    st.info(f"**Kein Alarm.** {ui.esc(headline) if headline else 'Nichts Verdächtiges genug gefunden.'}",
            icon=":material/check_circle:")
    for c in causes:  # failed checks: a "Kein Alarm" is then not a full assessment
        st.warning(f"**{ui.esc(c.title)}:** {ui.esc(c.text)}", icon=":material/report:")

m = st.columns(3)
m[0].metric("Score", f"{d.score:.2f}", delta=f"{d.score - thr:+.2f} zur Schwelle {thr:.2f}",
            delta_color="inverse", border=True,
            help="Gesamtrisiko der stärksten Art von Fehlverhalten. Ab der Schwelle = Alarm.")
m[1].metric("Unsicherheit", f"{d.uncertainty:.2f}", delta=f"Prüfen über {s.max_uncertainty:.2f}",
            delta_color="off", delta_arrow="off", border=True,
            help="Wie stark sich die Prüfungen widersprechen oder selbst zweifeln. Über dem Maximum entscheidet "
                 "ein Mensch.")
m[2].metric("Prüfbereich", f"{floor:.2f} – {thr:.2f}", border=True,
            help="Scores in diesem Bereich gehen zur Prüfung an einen Menschen (Seitenleiste).")

with st.expander("Entscheid im Wortlaut (Fusion)", icon=":material/gavel:"):
    st.markdown("\n".join(f"- {ui.esc(r)}" for r in d.reasons) or "–")

if not dd.live:
    st.warning(f"Gezeigt wird der bei der Verarbeitung gespeicherte Entscheid; die Neu-Bewertung schlug fehl "
               f"({dd.error}). Die Regler der Seitenleiste wirken hier nicht.", icon=":material/history:")
elif dd.stored.label != d.label:
    st.info(f"Bei der Verarbeitung war dieser Anruf **{LABEL_TEXT[dd.stored.label]}** (Schwelle "
            f"{dd.stored.threshold:.2f}). Mit den aktuellen Reglern ist er **{LABEL_TEXT[d.label]}**.",
            icon=":material/tune:")
stale = [n for n, cr in result.checks.items() if cr.meta.get("stale")]
if stale:
    st.caption(f":material/history: Seit der letzten Kriterien-Änderung nicht neu gelaufen: {', '.join(stale)}.")

# -- evidence timeline ---------------------------------------------------------------------------

st.subheader("Beweis-Zeitachse")
events = ex.timeline_events(result, d)
seek_key = f"cg_seek_{call_id}"
link_i = linked_passage(d.passages, t, app.link_pad)
if seek_key not in st.session_state:
    st.session_state[seek_key] = float(t) if t is not None else None
tl_key = f"cg_timeline_{call_id}"


def _on_mark() -> None:
    ev = st.session_state.get(tl_key)
    try:
        sel = ev["selection"].get("mark") or []
    except (KeyError, TypeError, AttributeError):
        sel = []
    if sel and isinstance(sel[0], dict) and sel[0].get("start") is not None:
        st.session_state[seek_key] = float(sel[0]["start"])


def _on_jump() -> None:
    i = st.session_state.get(f"cg_jump_{call_id}")
    if i is not None and 0 <= i < len(d.passages):
        st.session_state[seek_key] = float(d.passages[i].start)


if events or d.passages:
    fam_order = [f.id for f in app.all_families] + [e["family"] for e in events]
    labels = {f.id: short_label(f.label) for f in app.all_families}
    st.altair_chart(ui.timeline_chart(events, d.passages, dur, colors, list(dict.fromkeys(fam_order)),
                                      st.session_state.get(seek_key), labels),
                    width="stretch", key=tl_key, on_select=_on_mark, selection_mode="mark")
    st.caption("Jede Markierung ist ein Fund einer Prüfung (Form = Prüfung, Grösse = Score); schattierte "
               "Bänder sind die Passagen. **Markierung anklicken**: die Aufnahme unten springt an diese Stelle.")
    if d.passages:
        st.pills("Zu Passage springen", list(range(len(d.passages))), key=f"cg_jump_{call_id}",
                 format_func=lambda i: f"{i + 1} · {fmt_ts(d.passages[i].start)} · "
                                       f"{short_label(d.passages[i].family_label or d.passages[i].family)}",
                 on_change=_on_jump)
else:
    st.caption("Keine Prüfung hat in diesem Anruf eine Stelle markiert.")

seek = st.session_state.get(seek_key)
if result.audio_path and Path(result.audio_path).is_file():
    start = int(max(0.0, (seek or 0.0) - 1.0)) if seek is not None else 0
    picked = next((e for e in events if seek is not None and abs(e["start"] - seek) < 1e-6), None)
    st.caption(f":material/play_circle: Ganze Aufnahme, ab {fmt_ts(start)}"
               + (f" · {ui.esc(picked['check'])}: {ui.esc(picked['reason'][:160])}" if picked else ""))
    try:
        st.audio(result.audio_path, start_time=start, autoplay=seek is not None and t is None)
    except Exception as e:
        st.caption(f":material/volume_off: Aufnahme konnte nicht geladen werden ({type(e).__name__}).")
else:
    st.caption(":material/volume_off: Aufnahme auf diesem Rechner nicht verfügbar.")

# -- why not an alarm --------------------------------------------------------------------------------

why = ex.why_not_alarm(result, d, app.all_families, threshold=thr, review_band=s.review_band, weights=s.weights)
if why is not None:
    with st.expander(f"Warum kein Alarm? ({short_label(why.family_label)})", icon=":material/help:",
                     expanded=d.label == "no_alert"):
        st.markdown(ui.esc(why.summary) or "–")
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**Stärkstes Gegenargument**")
            if why.counter is not None:
                o = why.counter
                st.markdown(f"«{ui.esc(o.check)}» · Score **{o.score:.2f}** · Sicherheit {ui.pct(o.confidence)}"
                            + (f" · Urteil: {ex.VERDICT_DE.get(o.verdict, o.verdict)}" if o.verdict else "")
                            + (f"\n\n> {ui.esc(o.reason)}" if o.reason else ""))
            else:
                st.caption("Keine Prüfung spricht klar dagegen; der Score bleibt einfach unter der Schwelle.")
        with c2:
            st.markdown("**Entlastungsregel (criteria.yaml, «kein Alarm, wenn …»)**")
            if why.rule is not None:
                st.markdown(f"> {ui.esc(why.rule.rule)}")
                st.caption("Von der Faktenprüfung genannt." if why.rule_source == "fact" else
                           f"Zuordnung über gemeinsame Begriffe ({', '.join(why.rule.shared[:5])}): ein Hinweis, "
                           "kein Beweis.")
            else:
                st.caption("Keine Regel passt eindeutig zur Gegenbegründung.")
            for note in why.harmless_notes:
                st.markdown(f":material/info: Laut Stichwortliste harmlos, wenn: *{ui.esc(note)}*")
        if why.hits:
            st.markdown("**Stichwort-Treffer** " + " ".join(
                f":gray-badge[{ui.esc(h.phrase)}{' · ' + fmt_ts(h.start) if h.start is not None else ''}"
                f"{' · verneint' if h.negated else ''}]" for h in why.hits[:12]))
        st.markdown(f"**Jede Prüfung gegen die Schwelle** · Gesamt {why.score:.2f} · Prüfen ab {why.floor:.2f} · "
                    f"Alarm ab {why.threshold:.2f}")
        st.dataframe(pd.DataFrame([{
            "Prüfung": o.check, "Gewicht": o.weight, "Score": o.score, "≥ Schwelle": o.above,
            "Sicherheit": o.confidence, "Urteil": ex.VERDICT_DE.get(o.verdict, o.verdict or "–"), "Begründung": o.reason,
        } for o in why.opinions]), hide_index=True, width="stretch", column_config={
            "Score": ui.score_column(), "Gewicht": st.column_config.NumberColumn(format="%.2f"),
            "Sicherheit": st.column_config.NumberColumn(format="%.2f"),
            "≥ Schwelle": st.column_config.CheckboxColumn(help="Score dieser Prüfung allein erreicht die Schwelle."),
            "Begründung": st.column_config.TextColumn(width="large")})

# -- passages ----------------------------------------------------------------------------------

st.subheader(f"Verdächtige Passagen ({len(d.passages)})")
if t is not None:
    st.caption(f":material/link: Geöffnet über einen Alarm-Link bei {fmt_ts(t)}"
               + (f"; er zeigt auf Passage {link_i + 1}." if link_i is not None else "."))
if not d.passages:
    st.success("Keine Passage erreicht mit den aktuellen Einstellungen den Prüfbereich.", icon=":material/check:")
for i, p in enumerate(d.passages):
    ui.passage_card(i + 1, p, result, result_dir, app.snippet_pad, linked=(i == link_i), family=app.family(p.family),
                    color=colors.get(p.family), view_titles=view_titles, misheard_below=app.misheard_below)

# -- per family / per check ---------------------------------------------------------------------

st.subheader("Was die Prüfungen sagen")
c1, c2 = st.columns([3, 2], gap="large")
with c1:
    if d.families:
        st.altair_chart(ui.family_chart(d, thr, floor, app.can_alarm), width="stretch")
        st.caption("Balken = Gesamtscore je Art, schwarzer Strich = Gesamtwert, Symbole = Score jeder Prüfung. "
                   "Durchgezogene Linie: Alarmschwelle, gestrichelt: Beginn des Prüfbereichs.")
    else:
        st.info("Keine Art von Fehlverhalten wurde bewertet.")
with c2:
    fam_rows = [{"Art": short_label(f.label), "Score": f.score, "Unsicherheit": f.uncertainty}
                for f in sorted(d.families.values(), key=lambda f: -f.score)]
    st.dataframe(pd.DataFrame(fam_rows, columns=["Art", "Score", "Unsicherheit"]),
                 hide_index=True, width="stretch",
                 column_config={"Score": ui.score_column(),
                                "Unsicherheit": st.column_config.NumberColumn(format="%.2f")})

said = checks_said(result, d, s.weights)
with st.expander("Was jede Prüfung gesagt hat", icon=":material/fact_check:", expanded=d.label != "no_alert"):
    only_top = st.toggle("Nur relevante Arten", value=True, key="cg_detail_only_scored",
                         help="Die stärkste Art und jede Art mit mindestens der Hälfte des Prüfbereichs.")
    if only_top:
        bar = 0.5 * floor
        relevant = {short_label(f.label) for f in d.families.values() if f.score >= bar and f.score > 0}
        if top:
            relevant.add(short_label(top.label))
        said = [r for r in said if r["family"] in relevant]
    st.dataframe(pd.DataFrame([{
        "Art": r["family"], "Prüfung": r["check"], "Gewicht": r["weight"], "Score": r["score"],
        "Sicherheit": r["confidence"], "Urteil": ex.VERDICT_DE.get(r["verdict"], r["verdict"]), "Begründung": r["reason"],
    } for r in said], columns=["Art", "Prüfung", "Gewicht", "Score", "Sicherheit", "Urteil", "Begründung"]),
        hide_index=True, width="stretch",
        column_config={"Score": ui.score_column(),
                       "Sicherheit": st.column_config.NumberColumn(format="%.2f"),
                       "Gewicht": st.column_config.NumberColumn(format="%.2f"),
                       "Begründung": st.column_config.TextColumn(width="large")})

# -- extra panels (other teams: callguard.ui.panels) ---------------------------------------------

extra = [p for p in panels()]
if extra:
    live = app.live_result(call_id)
    for panel in extra:
        if not panel.visible(live, app):
            continue
        with st.expander(panel.title, icon=panel.icon, expanded=panel.expanded):
            try:
                panel.resolve()(live, app)
            except Exception as e:  # one broken panel must not take the page down
                st.warning(f"Panel «{panel.title}» ist fehlgeschlagen: {type(e).__name__}: {e}",
                           icon=":material/extension_off:")

# -- transcript per view ---------------------------------------------------------------------------

st.subheader("Transkript")
primary = result.transcript.view


def _transcript(name: str) -> None:
    tr = views[name]
    if not tr.segments:
        st.info("Dieses Transkript ist leer (Stille, oder die Spracherkennung ist fehlgeschlagen).")
        return
    if tr.asr_backend:
        st.caption(f"Quelle: {tr.asr_backend}" + (f" · Sprache {tr.lang}" if tr.lang else ""))
    with st.container(height=560 if len(tr.segments) > 12 else "content", border=True):
        st.markdown(ui.transcript_markdown(tr, d.passages, result, by_time=name != primary))


st.caption("Hervorgehoben: Abschnitte einer verdächtigen Passage. Fett: Stichwort-Treffer.")
if len(views) > 1:
    names = [primary] + [n for n in views if n != primary]
    for tab, name in zip(st.tabs([view_titles[n] for n in names]), names):
        with tab:
            _transcript(name)
else:
    _transcript(next(iter(views)))

# -- provenance and evaluation ------------------------------------------------------------------

with st.expander("Details der Verarbeitung", icon=":material/info:"):
    tr = result.transcript
    ui.kv_table({
        "Profil": result.config_name or "–", "Quelle": app.source.label if app.source else "–",
        "Spracherkennung": tr.asr_backend or "–", "Sprache": tr.language or "–",
        "Dauer": fmt_ts(tr.duration) if tr.duration else "–", "Abschnitte": len(tr.segments),
        "Ansichten": ", ".join(views), "Aufnahme": result.audio_path or "–",
        "Ergebnisdatei": str(app.loaded.paths[call_id]),
        **{f"Zeit {k}": f"{v:.1f} s" for k, v in result.timings.items()},
    })
    meta = [{"Prüfung": n, "Typ": cr.type, "Ansicht": cr.view or "–", **{k: str(v)[:120] for k, v in cr.meta.items()}}
            for n, cr in result.checks.items()]
    if meta:
        st.dataframe(pd.DataFrame(meta).fillna(""), hide_index=True, width="stretch")
    for name, err in check_problems(result).items():
        st.caption(f":material/error: {name}: {err[:300]}")

truth = ground_truth(str(app.ctx.data_dir)).get(call_id)
if truth is not None and truth.expected is not None:
    with st.expander("Nur zur Auswertung: erwartete Bewertung aus den Falldaten", icon=":material/school:"):
        exp = truth.expected
        ok = exp.label == d.label
        st.markdown(f"Erwartet {ui.label_md(exp.label)} · Art `{exp.family}` · "
                    + (":blue[stimmt überein]" if ok else ":red[weicht vom aktuellen Entscheid ab]"))
        if exp.reason:
            st.markdown(f"> {ui.esc(exp.reason)}")
        st.caption("Wird von der Pipeline nie verwendet; nur hier gezeigt, um die Auswertung zu erklären.")
