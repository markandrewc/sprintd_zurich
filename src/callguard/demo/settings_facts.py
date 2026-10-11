"""Einstellungen › Fakten: the questions the AI answers, as a simple list (grouped by Prüfart), «+ Neuer Fakt» wizard,
and the four-eyes proposals on top. The advanced view (both readers' bands and combination, distribution strips,
disagreements) is tucked away in «Erweitert: KI-Leser & Bänder».

Changing facts is NOT instant (unlike rules): a new or changed question needs the AI to answer it for every call and a
second person's approval (``VersionStore.save_draft`` -> ``approve``: approver ≠ author). After approval Qwen can answer
right away if it is reachable; Kev answers on the next GPU batch. Until then the new fact counts as «unklar».
"""

from __future__ import annotations

import copy
from typing import Any

import streamlit as st

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard import rule_drafter as rd
from callguard import rulebook as rb
from callguard.checks.facts import FACT_ROLES, PolicyTableError, parse_rule, rule_facts
from callguard.demo import facts_ui as fu
from callguard.policy_versions import FourEyesError, same_person
from callguard.ui import render as ui
from callguard.ui import whatif as wi
from callguard.ui.backend import short_label
from callguard.ui.session import reload_everything

FW = "dm_fw"  # session key of the fact wizard
ROLE_SHORT = {"act": "Handlung", "context": "Umstand", "exculpatory": "Entlastung", "authorization": "Vollmacht"}
ROLE_HELP = {"act": "das Fehlverhalten selbst (z.B. Code vorgelesen)",
             "context": "macht es verdächtig (z.B. Information nicht öffentlich)",
             "exculpatory": "macht es harmlos (z.B. Code abgelaufen)",
             "authorization": "ob eine Vollmacht vorliegt"}
READERS = ("both", "a", "b")


def _flash(msg: str) -> None:
    st.session_state.setdefault("dm_set_messages", []).append(msg)


def fam_names(app: Any) -> dict[str, str]:
    return {f.id: short_label(f.label) for f in app.all_families}


# --------------------------------------------------------------------------------------------
# wizard (pure helpers)
# --------------------------------------------------------------------------------------------


def new_state(family: str | None = None, fact: dict[str, Any] | None = None,
              policy: fpol.FactPolicy | None = None) -> dict[str, Any]:
    pol = policy or fpol.default_policy()
    out = {"step": 1, "family": family, "fact_id": None, "question": "", "readers": "both",
           "band": (pol.b.lo, pol.b.hi), "label": "", "description": "", "role": "context", "nonce": 0,
           "ai_note": None}
    if fact and family:
        fid = str(fact["id"])
        rb_ = pol.reader(1, family, fid)
        comb = pol.combination_for(family, fid)
        out.update(fact_id=fid, question=str(fact.get("de") or ""), label=str(fact.get("label") or ""),
                   description=str(fact.get("description") or ""), role=str(fact.get("role") or "context"),
                   band=(rb_.lo, rb_.hi), readers={"only_a": "a", "only_b": "b"}.get(comb, "both"))
    return out


def proposal(state: dict[str, Any], doc: dict[str, Any], pol: fpol.FactPolicy
             ) -> tuple[dict[str, Any], fpol.FactPolicy, str]:
    """(table with the new / changed fact, fact policy with its per-fact reader settings, fact id)."""
    fam = state["family"]
    cand = copy.deepcopy(doc)
    fid = state["fact_id"] or pe.new_fact_id(cand, fam, state["label"] or state["question"])
    old = next((f for f in pe.family_doc(cand, fam)["facts"] if str(f.get("id")) == fid), {})
    en = old.get("en") if " ".join(str(old.get("de") or "").split()) == " ".join(state["question"].split()) else ""
    pe.upsert_fact(cand, fam, {"id": fid, "label": state["label"].strip() or fid, "role": state["role"],
                               "de": state["question"], "en": en or "", "description": state["description"]})
    newpol = pol.with_override(fam, fid, clear=True)
    lo, hi = state["band"]
    if (round(lo, 4), round(hi, 4)) != (round(pol.b.lo, 4), round(pol.b.hi, 4)):
        newpol = newpol.with_override(fam, fid, reader=pol.b.id, band=[lo, hi])
    if state["readers"] in ("a", "b"):
        newpol = newpol.with_override(fam, fid, combination="only_a" if state["readers"] == "a" else "only_b")
    return cand, newpol, fid


def _state() -> dict[str, Any]:
    return st.session_state.setdefault(FW, new_state())


def _close() -> None:
    st.session_state.pop(FW, None)
    st.session_state["dm_fw_open"] = False


def _set(field: str, wkey: str) -> None:
    v = st.session_state.get(wkey)
    _state()[field] = tuple(v) if field == "band" else v


def _step(delta: int) -> None:
    s = _state()
    s["step"] = max(1, min(3, s["step"] + delta))


def _ai_phrase(app: Any, names: dict[str, str]) -> None:
    ss = st.session_state
    state = _state()
    if not fu.assistant_enabled(app):  # no LLM is constructed or called
        st.caption(f":material/smart_toy: {fu.ASSISTANT_OFF}")
        return
    st.markdown("##### :material/smart_toy: KI-Assistent")
    st.caption("Beschreiben Sie, was die KI im Gespräch herausfinden soll. Sie formuliert daraus eine klare "
               "Ja/Nein-Frage; Sie können sie danach frei ändern.")
    st.text_area("Was soll die KI herausfinden?", key="dm_fw_ai_req", height=110, label_visibility="collapsed",
                 placeholder="z.B. ob die Kundin sagt, dass sie den Code von jemand anderem bekommen hat")
    if st.button("Als Ja/Nein-Frage formulieren", icon=":material/auto_awesome:", type="primary", width="stretch",
                 disabled=not str(ss.get("dm_fw_ai_req") or "").strip(), key="dm_fw_ai_go"):
        try:
            llm = app.ctx.llm(str(app.cfg.app.get("assistant_llm", "default")))  # live LLM for the KI-Assistent
            with st.status("Die KI formuliert die Frage …", expanded=True) as status:
                q = rd.phrase_question(llm, ss["dm_fw_ai_req"], names.get(state.get("family") or "", ""))
                st.write(f"«{q}»")
                status.update(label="Frage formuliert — bitte prüfen", state="complete")
        except Exception as e:  # LLM down / refused
            state["ai_note"] = (f"Sprachmodell nicht erreichbar ({type(e).__name__}). Formulieren Sie die Frage "
                                "selbst: eine Sache, mit Ja oder Nein beantwortbar.")
            return
        state.update(question=q, nonce=state["nonce"] + 1, ai_note="Von der KI formuliert — bitte lesen und anpassen.")
        st.rerun()  # the dialog stays open (its flag is in the session)
    if state.get("ai_note"):
        st.info(state["ai_note"], icon=":material/smart_toy:")


@st.dialog("Neuer Fakt", width="large", on_dismiss=_close)
def fact_wizard(app: Any) -> None:
    ss = st.session_state
    names = fam_names(app)
    doc = fu.live_doc(app)
    pol = fu.live_policy(app)
    state = _state()
    left, right = st.columns([2.1, 1], gap="large")
    if state["step"] == 1:
        with right:
            _ai_phrase(app, names)
    state = _state()
    n = state["nonce"]
    fams = list((doc.get("families") or {}).keys())
    with left:
        st.markdown(" → ".join(f"**{i}. {t}**" if state["step"] == i else f"{i}. {t}"
                               for i, t in ((1, "Prüfart & Frage"), (2, "KI-Leser"), (3, "Bezeichnung"))))
        if state["fact_id"]:
            st.caption(f"Sie ändern den bestehenden Fakt `{state['fact_id']}`.")
        if state["step"] == 1:
            st.selectbox("Prüfart", fams, index=fams.index(state["family"]) if state["family"] in fams else None,
                         format_func=lambda f: names.get(f, f), key=f"dm_fw_fam_{n}", on_change=_set,
                         args=("family", f"dm_fw_fam_{n}"), disabled=bool(state["fact_id"]),
                         placeholder="Prüfart wählen")
            st.text_area("Frage an die KI (Ja/Nein, auf Deutsch)", value=state["question"], key=f"dm_fw_q_{n}",
                         on_change=_set, args=("question", f"dm_fw_q_{n}"), height=110,
                         placeholder="Sagt die Kundin, dass sie den Code von einer anderen Person erhalten hat?")
        elif state["step"] == 2:
            st.radio("Wer beantwortet die Frage?", list(READERS), index=READERS.index(state["readers"]),
                     key=f"dm_fw_r_{n}", on_change=_set, args=("readers", f"dm_fw_r_{n}"),
                     format_func=lambda r: {"both": f"Beide: {pol.a.label} und {pol.b.label} (empfohlen; zählt, wenn "
                                                    f"sie sich einig sind: {pol.combination_de()})",
                                            "a": f"Nur {pol.a.label} ({pol.a.model})",
                                            "b": f"Nur {pol.b.label} ({pol.b.model})"}[r])
            st.slider(f"{pol.b.label}: «unklar», wenn die KI-Sicherheit zwischen diesen Werten liegt", 0.0, 1.0,
                      value=tuple(state["band"]), step=0.05, key=f"dm_fw_b_{n}", on_change=_set,
                      args=("band", f"dm_fw_b_{n}"),
                      help="Breiter = öfter «unklar» = öfter Prüfen (mehr Arbeit, weniger übersehen).")
            st.caption(f"{pol.a.label}: {pol.a.describe()}. Standard für {pol.b.label}: Band {pol.b.lo:.1f}–{pol.b.hi:.1f}.")
        else:
            st.text_input("Kurze Bezeichnung (erscheint in Regeln und auf der Fallkarte)", value=state["label"],
                          key=f"dm_fw_l_{n}", on_change=_set, args=("label", f"dm_fw_l_{n}"),
                          placeholder="z.B. Code von Dritten erhalten")
            st.text_area("Beschreibung (optional, für Kolleginnen)", value=state["description"], key=f"dm_fw_d_{n}",
                         on_change=_set, args=("description", f"dm_fw_d_{n}"), height=80)
            st.selectbox("Art des Fakts", list(FACT_ROLES), index=list(FACT_ROLES).index(state["role"]),
                         format_func=lambda r: f"{ROLE_SHORT[r]} – {ROLE_HELP[r]}", key=f"dm_fw_role_{n}",
                         on_change=_set, args=("role", f"dm_fw_role_{n}"))
            st.info("**Fakten ändern braucht eine Freigabe durch eine zweite Person.** Nach der Freigabe beantwortet "
                    f"{pol.a.label} die neue Frage für alle Anrufe (sofort, wenn erreichbar), {pol.b.label} beim nächsten "
                    "Lauf auf dem GPU-Rechner. Bis dahin gilt sie als «unklar».", icon=":material/group:")
        b1, _, b3 = st.columns(3)
        b1.button("Zurück", icon=":material/arrow_back:", on_click=_step, args=(-1,), disabled=state["step"] == 1,
                  key="dm_fw_back", width="stretch")
        if state["step"] < 3:
            ok = bool(state["family"]) and len(state["question"].strip()) > 8
            b3.button("Weiter", icon=":material/arrow_forward:", on_click=_step, args=(1,), type="primary",
                      disabled=not ok, key="dm_fw_next", width="stretch")
        elif b3.button("Zur Freigabe einreichen", icon=":material/how_to_reg:", type="primary", key="dm_fw_submit",
                       disabled=not state["label"].strip(), width="stretch"):
            try:
                cand, newpol, fid = proposal(state, doc, pol)
                bundle = {"policy_table": cand}
                if newpol.as_dict() != pol.as_dict():
                    bundle["fact_policy"] = newpol.as_dict()
                v = fu.store(app).save_draft(bundle, ss.get("dm_user", ""), family_names=names,
                                             comment=f"{'Fakt geändert' if state['fact_id'] else 'Neuer Fakt'}: "
                                                     f"{state['label'].strip()}")
            except (FourEyesError, PolicyTableError, fpol.FactPolicyError) as e:
                st.error(str(e))
                return
            _flash(f"Vorschlag «{state['label'].strip()}» eingereicht (Version {v.n}). Eine zweite Person gibt ihn "
                   "oben bei «Wartet auf Freigabe» frei.")
            _close()
            st.rerun()


# --------------------------------------------------------------------------------------------
# proposals (four eyes)
# --------------------------------------------------------------------------------------------


def _ask_qwen(app: Any) -> None:
    """After approval: Qwen answers the new / changed questions for every stored call (cached for the next run)."""
    check = next((c for c in getattr(app.engine.pipeline, "checks", []) if getattr(c, "name", "") == "facts"), None)
    try:
        table = pe.validate(fu.live_doc(app))
        tasks = wi.probe_tasks(app.loaded.results, table, getattr(check, "question_lang", "en"))
        if not tasks:
            st.session_state["dm_fk_probe"] = "Keine offenen Fragen: alle Antworten sind schon da."
            return
        out, errors = wi.run_probes(check, app.loaded.results, table, tasks, {f.id: f for f in app.all_families},
                                    lambda r: r.transcript)
        st.session_state["dm_fk_probe"] = (f"{len(out)} Antworten von Qwen berechnet und zwischengespeichert; sie "
                                           "fliessen beim nächsten Lauf ein." + (f" {len(errors)} fehlgeschlagen." if errors else ""))
    except Exception as e:
        st.session_state["dm_fk_probe"] = (f"Qwen ist gerade nicht erreichbar ({type(e).__name__}); die neue Frage wird "
                                           "beim nächsten Lauf auf dem GPU-Rechner beantwortet.")


def proposals(app: Any) -> None:
    ss = st.session_state
    vs = fu.store(app)
    drafts = vs.drafts()
    names = fam_names(app)
    if ss.get("dm_fk_approved"):
        st.success(f"Version {ss['dm_fk_approved']} ist freigegeben und aktiv. Die KI beantwortet neue oder geänderte "
                   "Fragen: Qwen jetzt (wenn erreichbar), Kev beim nächsten GPU-Lauf. Bis dahin gelten sie als «unklar».",
                   icon=":material/verified:")
        if fu.assistant_enabled(app):
            st.button("Qwen jetzt fragen", icon=":material/play_arrow:", on_click=_ask_qwen, args=(app,),
                      key="dm_fk_qwen")
        else:
            st.caption("Die neue Frage wird beim nächsten Lauf auf dem GPU-Rechner beantwortet (KI-Aufrufe sind in "
                       "diesem Profil ausgeschaltet).")
        if ss.get("dm_fk_probe"):
            st.caption(ss["dm_fk_probe"])
    if not drafts:
        return
    st.markdown(f"#### :material/pending_actions: Wartet auf Freigabe ({len(drafts)})")
    live = vs.live_bundle()
    for v in drafts:
        with st.container(border=True):
            diff = rb.diff_bundle(live, {**live, **v.bundle()}, names)
            st.markdown(f"**{ui.esc(str(v.meta.get('comment') or f'Version {v.n}'))}** · vorgeschlagen von "
                        f"**{ui.esc(v.author)}** · {str(v.meta.get('created', ''))[:16]}")
            if diff:
                st.markdown("\n".join(f"- {ui.esc(d)}" for d in diff))
            c1, c2, c3 = st.columns([2, 1, 1], vertical_alignment="bottom")
            me = ss.get("dm_user", "")
            approver = c1.text_input("Freigabe durch (Ihr Name)", key=f"dm_fk_appr_{v.n}",
                                     value="" if same_person(me, v.author) else me,
                                     help="Vier-Augen-Prinzip: wer vorgeschlagen hat, kann nicht selbst freigeben.")
            if c2.button("Freigeben", type="primary", icon=":material/verified:", key=f"dm_fk_ok_{v.n}",
                         width="stretch"):
                try:
                    vs.approve(v.n, approver)
                except FourEyesError as e:
                    st.error(str(e), icon=":material/group:")
                else:
                    reload_everything()
                    ss["dm_fk_approved"] = v.n
                    ss.pop("dm_fk_probe", None)
                    st.rerun()
            if c3.button("Ablehnen", icon=":material/block:", key=f"dm_fk_no_{v.n}", width="stretch"):
                vs.reject(v.n, approver or me or "?")
                _flash(f"Vorschlag Version {v.n} abgelehnt.")
                st.rerun()


# --------------------------------------------------------------------------------------------
# the list
# --------------------------------------------------------------------------------------------


def _open(family: str | None = None, fact: dict[str, Any] | None = None, policy: fpol.FactPolicy | None = None) -> None:
    st.session_state["dm_fw_open"] = True
    st.session_state[FW] = new_state(family, fact, policy)


def _propose_delete(app: Any, fam: str, fid: str, label: str) -> None:
    cand = fu.live_doc(app)
    try:
        pe.delete_fact(cand, fam, fid)
        v = fu.store(app).save_draft({"policy_table": cand}, st.session_state.get("dm_user", ""),
                                     comment=f"Fakt entfernen: {label}", family_names=fam_names(app))
    except (FourEyesError, PolicyTableError, KeyError, ValueError) as e:
        st.session_state["dm_fk_error"] = str(e)
        return
    _flash(f"Entfernen von «{label}» vorgeschlagen (Version {v.n}); eine zweite Person gibt frei.")


def _used_in(doc: dict[str, Any], fam: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in pe.family_doc(doc, fam)["rules"]:
        try:
            for f in rule_facts(parse_rule(str(r.get("when", "true")))):
                out[f] = out.get(f, 0) + 1
        except PolicyTableError:
            pass
    return out


def render(app: Any) -> None:
    ss = st.session_state
    names = fam_names(app)
    vs = fu.store(app)
    vs.ensure_initial()
    doc = fu.live_doc(app)
    pol = fu.live_policy(app)
    spol = fu.session_policy(app)  # what the counts use: the session's «Sicherheit der KI»
    has_policy = fu.fusion(app) is not None
    st.markdown("Ein **Fakt** ist eine kleine Ja/Nein-Frage, die die KI zu jedem Gespräch beantwortet. Neue oder "
                "geänderte Fakten gelten erst nach **Freigabe durch eine zweite Person**.")
    proposals(app)
    st.button("Neuer Fakt", icon=":material/add:", type="primary", on_click=_open, args=(None, None, pol),
              key="dm_fk_new")
    if ss.get("dm_fk_error"):
        st.error(ss.pop("dm_fk_error"), icon=":material/error:")
    answers = fpol.fact_answers(app.loaded.results, spol) if has_policy else {}
    for fam in (doc.get("families") or {}):
        fdoc = pe.family_doc(doc, fam)
        used = _used_in(doc, fam)
        st.markdown(f"#### {ui.esc(names.get(fam, fam))}")
        for f in fdoc["facts"]:
            fid = str(f["id"])
            label = str(f.get("label") or fid)
            comb = pol.combination_for(fam, fid)
            readers = {"only_a": pol.a.label, "only_b": pol.b.label}.get(comb, f"{pol.a.label} + {pol.b.label}")
            ans = answers.get((fam, fid)) or []
            with st.container(border=True):
                a, b, c = st.columns([6, 2.4, 1.2], vertical_alignment="center")
                a.markdown(f"**{ui.esc(label)}** :gray-badge[{ROLE_SHORT.get(str(f.get('role')), '')}]  \n"
                           f":small[{ui.esc(str(f.get('de') or ''))}]")
                if ans:
                    cnt = fpol.value_counts(ans, spol, fam, fid)["combined"]
                    agree = sum(1 for x in ans if fpol.resolve_fact(spol, fam, fid, x.pa, x.pb).agree)
                    b.markdown(f":small[{ui.esc(readers)}]  \n**ja {cnt['yes']}** · nein {cnt['no']} · unklar "
                               f"{cnt['unclear']}  \n:small[einig bei {agree}/{len(ans)}]")
                else:
                    b.markdown(f":small[{ui.esc(readers)}]  \n:small[noch keine Antworten]")
                with c.popover("", icon=":material/more_horiz:", width="stretch"):
                    st.button("Ändern", icon=":material/edit:", key=f"dm_fk_edit_{fam}_{fid}", on_click=_open,
                              args=(fam, f, pol), width="stretch")
                    st.button("Entfernen vorschlagen", icon=":material/delete:", key=f"dm_fk_del_{fam}_{fid}",
                              on_click=_propose_delete, args=(app, fam, fid, label), width="stretch",
                              disabled=bool(used.get(fid)),
                              help=f"in {used.get(fid)} Regel(n) verwendet" if used.get(fid) else None)
    if has_policy:  # a toggle, not an expander: the advanced view has expanders of its own and is only built on demand
        st.divider()
        if st.toggle("Erweitert: KI-Leser & Bänder", key="dm_fk_adv",
                     help="Wie die zwei KI-Leser zusammen entscheiden, ihre Bänder, Verteilungen und Uneinigkeiten."):
            from callguard.demo import facts_advanced

            with st.container(border=True):
                facts_advanced.render(app, doc, names)
    if ss.get("dm_fw_open"):
        fact_wizard(app)
