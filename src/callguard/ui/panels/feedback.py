"""Call-detail panel "Rückmeldung" (schema 2, docs/LEARNING.md): the officer's judgement as labels.

One form per call: verdict on the call (Verstoss bestätigt / kein Verstoss / unklar), per shown passage
"trifft zu / trifft nicht zu", per fact of the facts check "stimmt / stimmt nicht / unklar" (the button
names the value it records), missed categories, a comment and the officer's name. Saved append-only to
``runs/<profile>/feedback.jsonl`` with provenance (config, policy table, models, transcript hash) and one
audit event per item. Answers given in the "Offene Fakten" panel are per-fact labels already (audit
``fact_answer``) and are shown here, not asked twice. Registered in ``callguard/ui/panels/__init__.py``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from callguard import audit
from callguard import feedback as fb
from callguard.types import CallResult, fmt_ts
from callguard.ui import render as ui

NAME_KEY = "cg_officer_name"


def officer_name(container: Any, key: str, label: str = "Ihr Name") -> str:
    """The acting officer's name, remembered across pages in ``st.session_state[NAME_KEY]`` (plain state,
    never a widget key; each page / call uses its own widget ``key``)."""
    st.session_state.setdefault(NAME_KEY, audit.current_user())
    st.session_state.setdefault(key, st.session_state[NAME_KEY])
    val = container.text_input(label, key=key, help="Wird mit jeder Rückmeldung / Freigabe gespeichert "
                               "(Audit-Log, Vier-Augen-Prinzip).")
    st.session_state[NAME_KEY] = val
    return " ".join(str(val or "").split())


def judged_families(result: CallResult) -> list[tuple[str, str, dict[str, Any], dict[str, Any]]]:
    """(check, family, family detail, facts) of the facts check worth asking about: families the check
    did not leave at no_alert, plus the families of shown passages and the top family."""
    from callguard.learning.records import facts_check_of

    check = facts_check_of(result)
    if check is None:
        return []
    d = result.decision
    wanted = {p.family for p in d.passages} | ({d.top_family} if d.top_family else set())
    out = []
    for fid, fs in result.checks[check].family_scores.items():
        detail = fs.detail or {}
        facts = detail.get("facts") or {}
        if facts and (detail.get("decision") not in (None, "no_alert") or fid in wanted):
            out.append((check, fid, detail, facts))
    return out


def _open_answers(result: CallResult, session: Any) -> dict[str, dict[str, str]]:
    return st.session_state.get(f"cg_open_facts_{session.runs_dir}_{result.call_id}") or {}


def render(result: CallResult, session: Any) -> None:
    cid = result.call_id
    d = result.decision
    st.caption(f"Ihre Beurteilung wird zum Label (angezeigt: **{ui.label_text(d.label)}** bei Schwelle "
               f"{d.threshold:.2f}). Gespeichert mit Herkunft (Konfiguration, Regelwerk, Modelle, Transkript), "
               "nur anhängend. Sie fliesst in *Feedback & Tuning* und *Lernen* ein; trainiert wird damit nichts "
               "automatisch.")
    if session.read_only:
        st.info("Experiment-Variante (nur lesen): hier werden keine Rückmeldungen gespeichert.",
                icon=":material/visibility:")
        return
    name = officer_name(st, key=f"cg_fb_name_{cid}")
    fams = judged_families(result)
    open_ans = _open_answers(result, session)
    with st.form(f"cg_fb2_{cid}", border=False):
        verdict = st.radio("Urteil zum Anruf", list(fb.CALL_VERDICTS), index=None, horizontal=True,
                           format_func=fb.VERDICT_DE.get, key=f"cg_fb2_v_{cid}")
        passage_v: dict[int, str | None] = {}
        if d.passages:
            st.markdown("**Gezeigte Passagen**")
            for i, p in enumerate(d.passages):
                passage_v[i] = st.radio(
                    f"Passage {i + 1} · {p.family_label or session.family_label(p.family)} · {ui.span(p.start, p.end)}",
                    list(fb.PASSAGE_VERDICTS), index=None, horizontal=True, format_func=fb.VERDICT_DE.get,
                    key=f"cg_fb2_p_{cid}_{i}", help=(p.text[:300] or None))
        fact_v: dict[tuple[str, str, str], str | None] = {}
        if fams:
            st.markdown("**Fakten** (was das Modell gelesen hat)")
            for check, fid, detail, facts in fams:
                rule = (detail.get("rule") or {}).get("id")
                st.caption(f"{session.family_label(fid)} · Modell: {ui.label_text(detail.get('decision') or 'no_alert')}"
                           + (f" · Regel {rule}" if rule else ""))
                answered = open_ans.get(fid) or {}
                for fact_id, entry in facts.items():
                    mv = entry.get("value")
                    label = entry.get("label") or fact_id
                    if fact_id in answered:
                        st.caption(f"{label}: im Panel «Offene Fakten» beantwortet "
                                   f"({fb._VALUE_DE.get(answered[fact_id], answered[fact_id])}).")
                        continue
                    choices = dict(fb.fact_choices(mv))
                    fact_v[(check, fid, fact_id)] = st.radio(
                        f"{label} — Modell: {fb._VALUE_DE.get(mv, mv or '–')}", list(choices), index=None,
                        horizontal=True, format_func=choices.get, key=f"cg_fb2_f_{cid}_{fid}_{fact_id}",
                        help=entry.get("question"))
        shown = {p.family for p in d.passages} | ({d.top_family} if d.label != "no_alert" and d.top_family else set())
        options = [f.id for f in session.all_families if f.id not in shown]
        missed = st.multiselect("Übersehene Kategorie", options, format_func=session.family_label,
                                placeholder="keine",
                                key=f"cg_fb2_m_{cid}", help="Ein Verstoss dieser Art liegt vor, das System hat ihn "
                                                            "nicht gezeigt.")
        comment = st.text_input("Kommentar (optional)", key=f"cg_fb2_c_{cid}")
        submitted = st.form_submit_button("Rückmeldung speichern", icon=":material/save:")
    if submitted:
        if not name:
            st.error("Bitte Ihren Namen angeben.", icon=":material/badge:")
        else:
            try:
                items = fb.items_from_form(
                    result, user=name, verdict=verdict, passages={k: v for k, v in passage_v.items() if v},
                    facts={k: v for k, v in fact_v.items() if v}, missed=missed, comment=comment,
                    threshold=session.settings.threshold)
            except ValueError as e:
                st.warning(str(e), icon=":material/info:")
            else:
                fb.add_many(session.runs_dir, items)
                st.toast(f"{len(items)} Label gespeichert", icon=":material/check:")
    past = [i for i in fb.load(session.runs_dir) if i.call_id == cid]
    if past:
        st.markdown("**Bisherige Rückmeldungen**")
        st.dataframe([{"Zeit": i.ts, "Wer": i.user, "Urteil": fb.VERDICT_DE.get(i.verdict, i.verdict),
                       "Betrifft": _target(i, session), "Kommentar": i.comment} for i in reversed(past[-30:])],
                     hide_index=True)


def _target(i: fb.FeedbackItem, session: Any) -> str:
    if i.target == "fact":
        return f"{session.family_label(i.family or '')}: {i.fact} = {fb._VALUE_DE.get(i.answer or '', i.answer)}"
    if i.target == "passage":
        snap = i.passage or {}
        return f"Passage {(i.passage_index or 0) + 1}" + (f" ({fmt_ts(snap['start'])})" if snap.get("start") is not None else "")
    if i.target == "family":
        return f"übersehen: {session.family_label(i.family or '')}"
    return "ganzer Anruf"
