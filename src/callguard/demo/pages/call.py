"""Anruf prüfen: audio and transcript side by side and in sync (left), the decision card and the officer's
review (right). The review is saved as a labelled data point (schema-2 feedback with reason codes,
provenance, audit log). Deep link ``?call=<id>&t=<seconds>`` starts the recording at ``t``."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from callguard import misheard
from callguard.demo import card as cd
from callguard.demo import common as cm
from callguard.demo import media
from callguard.demo import review
from callguard.demo import state as ds
from callguard.demo.transcript import ROLE_DE, dialect_view, keyword_terms, player_html
from callguard.fact_policy import combination_label
from callguard.types import fmt_ts
from callguard.ui import render as ui
from callguard.ui.backend import LABEL_RANK, parse_seconds, short_label
from callguard.ui.session import current_app

PLAYER_HEIGHT = 700

app = current_app()
s = app.settings


@st.cache_data(show_spinner="Aufnahme wird vorbereitet …", max_entries=12)
def _audio(audio_path: str | None, run_dir: str, mtime: float) -> tuple[str | None, str]:
    a = media.player_audio(audio_path, run_dir)
    return a.src, a.note


def _order() -> list[str]:
    def key(cid: str) -> tuple:
        d = app.decided[cid].decision
        return (LABEL_RANK.get(d.label, 9), -(d.uncertainty if d.label == "review" else d.score), -d.score, cid)

    return sorted(app.decided, key=key)


if not app.loaded.results:
    st.title("Anruf prüfen")
    st.info("Noch keine verarbeiteten Anrufe. Einen Anruf auf **Anruf verarbeiten** hochladen.",
            icon=":material/inbox:")
    st.stop()

order = _order()
wanted = st.query_params.get("call") or st.session_state.get("dm_last_call") or order[0]
missing = wanted not in app.loaded.results
call_id = order[0] if missing else wanted
st.session_state["dm_last_call"] = call_id
if st.query_params.get("call") != call_id:
    st.query_params["call"] = call_id
t = parse_seconds(st.query_params.get("t")) if not missing else None


def _pick() -> None:
    st.query_params.clear()
    st.query_params["call"] = st.session_state["dm_pick"]


def _step(delta: int) -> None:
    i = (order.index(call_id) + delta) % len(order)
    st.query_params.clear()
    st.query_params["call"] = order[i]


judged = {i.call_id for i in ds.feedback_items(app)}
st.session_state["dm_pick"] = call_id
n1, n2, n3, n4 = st.columns([2, 7, 1, 1], vertical_alignment="bottom")
n1.page_link(app.pages["cases"], label="Zur Fallliste", icon=":material/arrow_back:")
n2.selectbox("Anruf", order, key="dm_pick", on_change=_pick, label_visibility="collapsed",
             format_func=lambda c: f"{c} · {cd.LABEL_DE[app.decided[c].decision.label]}"
                                   + (" · bearbeitet" if c in judged else ""))
n3.button("Zurück", icon=":material/chevron_left:", on_click=_step, args=(-1,), width="stretch")
n4.button("Weiter", icon=":material/chevron_right:", on_click=_step, args=(1,), width="stretch")
if missing:
    st.warning(f"Den Anruf «{wanted}» gibt es hier nicht; stattdessen: {call_id}.", icon=":material/search_off:")

result = app.loaded.results[call_id]
decision = app.decided[call_id].decision.model_copy(deep=True)
live = result.model_copy(update={"decision": decision})
misheard.annotate(live, app.misheard_below)
card = cm.card_for(app, call_id, decision)
colors = ui.family_colors(app.all_families)
labels = {f.id: short_label(f.label) for f in app.all_families}
dur = max([float(result.transcript.duration or 0.0)] + [x.end for x in result.transcript.segments])

st.title(f"{call_id}", anchor=False)
bits = [cm.badge(card.label)]
if card.family_label and (card.label != "no_alert" or (card.why_not and card.why_not.is_trap)):
    bits.append(f"**{ui.esc(card.family_label)}**")
bits.append(f"{card.passages} verdächtige Passage{'n' if card.passages != 1 else ''}")
bits.append(f"Dauer {fmt_ts(dur)}")
bits.append(":green-badge[:material/task_alt: bearbeitet]" if call_id in judged else ":gray-badge[offen]")
st.markdown(" · ".join(bits))

left, right = st.columns([7, 5], gap="large")
seek_key = f"dm_seek_{call_id}"
seek = st.session_state.get(seek_key)  # (seconds, nonce) set by a fact's «Stelle anhören»
segs_by_id = {x.id: x for x in result.transcript.segments}


def _seek(seconds: float) -> None:
    prev = st.session_state.get(seek_key)
    st.session_state[seek_key] = (max(0.0, float(seconds)), (prev[1] + 1) if prev else 1)


def fact_explained(f: cd.FactRow, where: str) -> None:
    """One fact: the answer in the title; inside the full question, the probabilities and the passage of the
    call the answer rests on, with a button that plays it (10 s early)."""
    agreement = f.agreement
    title = f"{f.label}: **{cd.VALUE_DE.get(f.value, f.value)}**"
    if agreement is None:
        title += f" ({f.confidence:.2f})" if f.confidence is not None else ""
    else:
        title += f" · {agreement}"
    with st.expander(title, icon=review.VALUE_ICON.get(f.value)):
        st.markdown(f"**Frage an die KI:** {ui.esc(f.question_de or f.question or f.label)}")
        if f.readers:  # two readers side by side: p(ja), the rule that turns it into a value, the value
            cols = st.columns(len(f.readers) + 1)
            for col, rd_ in zip(cols, f.readers.values()):
                p = rd_.get("p") or {}
                col.metric(f"{rd_.get('label', '?')} p(ja)", "–" if not p else f"{float(p.get('yes', 0.0)):.2f}",
                           help=f"Regel dieses Lesers: {rd_.get('rule', '')}")
                col.markdown(f"→ **{cd.VALUE_DE.get(str(rd_.get('value')), '?')}**  \n:small[{rd_.get('rule', '')}]")
            badge = {"einig": ":green-badge[einig]", "uneinig → unklar": ":orange-badge[uneinig → unklar]"}.get(
                agreement or "", f":orange-badge[{agreement}]")
            cols[-1].metric("zusammen", cd.VALUE_DE.get(f.value, f.value))
            names = [str(r.get("label") or "?") for r in f.readers.values()] + ["A", "B"]
            comb = combination_label(str(f.combination or ""), names[0], names[1]) if f.combination else ""
            cols[-1].markdown(f"{badge}  \n:small[{ui.esc(comb)}]")
        elif f.p:
            st.caption("Antwort der KI: " + " · ".join(
                f"{'**' if k == f.value else ''}{cd.VALUE_DE[k]} {f.p.get(k, 0.0):.2f}{'**' if k == f.value else ''}"
                for k in ("yes", "no", "unclear")))
        found = [segs_by_id[sid] for sid in f.evidence if sid in segs_by_id]
        if not found:
            st.caption(":material/description: Die KI hat das ganze Gespräch gelesen; keine einzelne Stelle markiert.")
            return
        st.markdown("**Stelle im Gespräch:**  \n" + "  \n".join(
            f"`{fmt_ts(x.start)}` {ui.esc(ROLE_DE.get(x.role or '', x.speaker or 'Sprecher'))}: "
            f"«{ui.esc(x.text.strip()[:220])}»" for x in found[:3])
            + ("  \n…" if len(found) > 3 else ""))
        start = min(x.start for x in found)
        st.button(f"Stelle anhören (ab {fmt_ts(max(0.0, start - app.link_pad))})", icon=":material/play_arrow:",
                  key=f"dm_seekbtn_{call_id}_{where}_{f.fact}", on_click=_seek, args=(start - app.link_pad,))


with left:
    run_dir = app.result_dir(call_id)
    ap = result.audio_path
    mtime = Path(ap).stat().st_mtime if ap and Path(ap).is_file() else 0.0
    src, note = _audio(ap, str(run_dir), mtime)
    start_at = seek[0] if seek else t
    tr = result.transcript
    doc = player_html(tr, live.decision.passages, audio_src=src, colors=colors, labels=labels,
                      start_at=start_at, link_pad=app.link_pad, misheard_below=app.misheard_below,
                      terms=keyword_terms(result), height=PLAYER_HEIGHT - 8, audio_note=note,
                      autoplay=bool(seek), nonce=seek[1] if seek else 0, dialect=dialect_view(result),
                      view="ch" if st.query_params.get("ansicht") == "ch" else "de")
    st.iframe(doc, height=PLAYER_HEIGHT)
    if seek:
        st.caption(f":material/play_circle: Aufnahme bei {fmt_ts(seek[0])} (Stelle eines Fakts, 10 s davor).")
    elif t is not None:
        st.caption(f":material/link: Über einen Alarm-Link geöffnet: die Aufnahme beginnt bei {fmt_ts(t)}.")

with right:
    with st.container(border=True):
        st.markdown(f"#### {cm.badge(card.label)} {ui.esc(card.family_label) if card.label != 'no_alert' else ''}")
        st.markdown(f"**{ui.esc(card.reason)}**")
        st.caption(card.sentence)
        if card.open_facts:
            for label, question in card.open_facts:
                st.warning(f"**Offen: {ui.esc(label)}?**  \n{ui.esc(question)}", icon=":material/help:")
        elif card.open_causes:
            st.warning("**Warum Prüfen?**  \n" + "  \n".join(f"- {ui.esc(c)}" for c in card.open_causes),
                       icon=":material/person_search:")
        if card.rule_plain and card.label != "no_alert":
            st.markdown(f":material/rule: **Regel** `{(card.rule_id or '').replace('`', '')}`  \n"
                        f"{ui.esc(card.rule_plain)}")
            st.caption("So zu lesen: Alle Bedingungen erfüllt → diese Regel entscheidet (erste passende Regel "
                       "von oben).")
        decisive = [f for f in card.facts if f.decisive]
        if decisive and card.label != "no_alert":
            st.markdown("**Fakten** · was die KI im Gespräch erkannt hat (aufklappen: Frage, Antwort, Stelle)")
            for f in decisive:
                fact_explained(f, "d")
        if card.why_not is not None:
            w = card.why_not
            st.markdown("**Warum kein Alarm?**" if card.label == "no_alert" else "**Warum (noch) kein Alarm?**")
            if w.is_trap:
                st.markdown(":orange-badge[:material/warning: Stichwort-Falle] "
                            + " ".join(f":gray-badge[{ui.esc(k)}]" for k in w.keywords[:8]))
            st.markdown(ui.esc(w.lead or w.summary))
            for rid, text, conds in card.failed_rules[:3]:
                st.markdown(f":material/block: Alarm-Regel `{rid}` greift nicht: "
                            + "; ".join(f"{ui.esc(c)}" for c in conds) + " → kein Alarm"
                            + (f"  \n:small[{ui.esc(text)}]" if text else ""))
            if card.label == "no_alert":
                for f in w.blocking:
                    fact_explained(f, "w")
            if w.rule and card.label == "no_alert":
                st.caption(f":material/rule: Entschieden hat: {ui.esc(w.rule)}")
            for n in w.harmless_notes[:2]:
                st.caption(f":material/info: Laut Stichwortliste harmlos, wenn: {ui.esc(n)}")
        shown = {f.fact for f in decisive} if card.label != "no_alert" else {
            f.fact for f in (card.why_not.blocking if card.why_not else [])}
        rest = [f for f in card.facts if f.fact not in shown]
        if rest and st.toggle(f"Weitere Fakten zeigen ({len(rest)})", key=f"dm_more_{call_id}"):
            for f in rest:
                fact_explained(f, "o")
        if card.basis:
            st.caption(f":material/gavel: **Rechtsgrundlage:** {ui.esc(card.basis)}")
        teams = cm.routed_to(app, live) if card.label != "no_alert" else []
        if teams:
            st.caption(f":material/alt_route: Geht an: **{ui.esc(', '.join(teams))}**")
        st.caption(f"Score {card.score:.2f} · Alarmschwelle {card.threshold:.2f} · Unsicherheit "
                   f"{card.uncertainty:.2f}")

    review.form(app, live, card, call_id)
