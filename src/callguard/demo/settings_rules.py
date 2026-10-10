"""Einstellungen › Regeln: one calm list of all rules (grouped by Prüfart) and the «+ Neue Regel» wizard.

The wizard is a pop-up (``st.dialog``) in three steps: 1 Fakten wählen, 2 Bedingungen (ja / nein / unklar, «nicht»,
UND or ODER), 3 Ergebnis (Alarm / Prüfen, title, description). A live line shows on how many processed calls the rule
would decide. On the right a KI-Assistent (the rule drafter, configured LLM) fills the wizard while the officer watches;
the officer still clicks through and saves. Saving applies instantly (version + audit + undo, no approval): rules are
pure logic over facts. A rule that needs a NEW fact sends that fact to «Fakten» for approval instead.
"""

from __future__ import annotations

import copy
import time
from typing import Any

import streamlit as st

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard import rule_drafter as rd
from callguard.checks.facts import PolicyTableError, eval_hard, parse_rule
from callguard.demo import facts_ui as fu
from callguard.policy_versions import FourEyesError
from callguard.ui import render as ui
from callguard.ui.backend import short_label
from callguard.ui.session import reload_everything

LABEL_DE = fu.LABEL_DE
LABEL_COLOR = {"alarm": "red", "review": "orange", "no_alert": "green"}
OUTCOMES = ("alarm", "review")
VALUE_OPTS = ("yes", "no", "unclear")
WIZ = "dm_rw"  # session key of the wizard state
AI_DELAY = 0.35  # seconds between the assistant's visible steps


def _flash(msg: str) -> None:
    st.session_state.setdefault("dm_set_messages", []).append(msg)


def fam_names(app: Any) -> dict[str, str]:
    return {f.id: short_label(f.label) for f in app.all_families}


def rule_title(rule: dict[str, Any]) -> str:
    return str(rule.get("title") or rule.get("text") or rule.get("id") or "").strip()


# --------------------------------------------------------------------------------------------
# wizard state (pure helpers, unit-tested)
# --------------------------------------------------------------------------------------------


def new_state() -> dict[str, Any]:
    return {"step": 1, "facts": [], "conds": {}, "join": "and", "label": "review", "title": "", "text": "",
            "nonce": 0, "ai_note": None, "ai_missing": [], "ai_family": None}


def state_family(state: dict[str, Any]) -> str | None:
    fams = {f.split(".", 1)[0] for f in state["facts"]}
    return next(iter(fams)) if len(fams) == 1 else None


def state_rule(state: dict[str, Any], doc: dict[str, Any]) -> tuple[str, dict[str, Any]] | None:
    """(family, rule) the wizard describes, or None while it cannot be a rule yet (no fact / several Prüfarten)."""
    fam = state_family(state)
    if fam is None:
        return None
    conds = []
    for key in state["facts"]:
        c = state["conds"].get(key) or {}
        conds.append((key.split(".", 1)[1], str(c.get("value") or "yes"), bool(c.get("neg"))))
    label = state["label"] if state["label"] in OUTCOMES else "review"
    rule = {"id": pe.new_rule_id(doc, fam, label), "label": label, "when": fu.build_when(conds, state["join"]),
            "text": state["text"].strip(), "title": state["title"].strip()}
    return fam, rule


def state_from_draft(draft: rd.Draft, doc: dict[str, Any]) -> dict[str, Any]:
    """The wizard state for an AI draft that only uses existing facts."""
    labels = pe.fact_labels(doc, draft.family)
    conds = pe.builder_from_when(str(draft.rule.get("when") or "true"), set(labels)) or []
    st_ = new_state()
    st_["facts"] = [f"{draft.family}.{c.fact}" for c in conds]
    st_["conds"] = {f"{draft.family}.{c.fact}": {"value": c.value, "neg": c.negate} for c in conds}
    st_["join"] = "or" if any(c.join == "or" for c in conds[1:]) else "and"
    label = str(draft.rule.get("label") or "review")
    st_["label"] = label if label in OUTCOMES else "review"
    text = str(draft.rule.get("text") or "").strip()
    st_["title"] = text.split(".")[0][:70] if text else ""
    st_["text"] = text
    return st_


def _state() -> dict[str, Any]:
    ss = st.session_state
    if WIZ not in ss:
        ss[WIZ] = new_state()
    return ss[WIZ]


def _close() -> None:
    st.session_state.pop(WIZ, None)
    st.session_state["dm_rw_open"] = False


# --------------------------------------------------------------------------------------------
# the dialog
# --------------------------------------------------------------------------------------------


def _hits_line(app: Any, pol: fpol.FactPolicy, work: dict[str, Any], state: dict[str, Any],
               base: dict[str, fpol.CallOutcome]) -> tuple[dict[str, Any] | None, str]:
    built = state_rule(state, work)
    if built is None:
        st.caption(":material/bolt: Diese Regel greift bei … — zuerst Fakten einer Prüfart wählen.")
        return None, ""
    fam, rule = built
    try:
        cand, _ = fu.with_rule(work, fam, rule)
        outs = fu.outcomes(app, pol, pe.validate(cand))
    except PolicyTableError as e:
        st.error(str(e))
        return None, ""
    calls = fu.rule_hits(outs, fam).get(rule["id"], [])
    line, changed = fu.effect_md(base, outs)
    with st.container(border=True):
        st.markdown(f":material/bolt: **Diese Regel greift bei {len(calls)} von {len(outs)} Anrufen** · {line}")
        if calls:
            with st.expander("Trefferliste"):
                st.markdown(" · ".join(f"{fu.call_link(c)} ({LABEL_DE[outs[c].label]})" for c in calls))
    return cand, fam


def _toggle_fact(key: str, wkey: str) -> None:
    state = _state()
    on = bool(st.session_state.get(wkey))
    if on and key not in state["facts"]:
        state["facts"].append(key)
        state["conds"].setdefault(key, {"value": "yes", "neg": False})
    elif not on and key in state["facts"]:
        state["facts"].remove(key)


def _set_cond(key: str, field: str, wkey: str) -> None:
    c = _state()["conds"].setdefault(key, {"value": "yes", "neg": False})
    c[field] = st.session_state.get(wkey) if field == "value" else bool(st.session_state.get(wkey))
    if field == "value" and c["value"] is None:
        c["value"] = "yes"


def _set(field: str, wkey: str) -> None:
    v = st.session_state.get(wkey)
    _state()[field] = ("or" if v else "and") if field == "join" else v


def _step(delta: int) -> None:
    s = _state()
    s["step"] = max(1, min(3, s["step"] + delta))


def _band_text(pol: fpol.FactPolicy, fam: str, fid: str) -> str:
    ra, rb_ = pol.reader(0, fam, fid), pol.reader(1, fam, fid)

    def one(r: fpol.ReaderSpec) -> str:
        if r.mode == "band":
            return f"{r.label}: KI-Sicherheit zwischen {r.lo:.1f} und {r.hi:.1f}"
        return f"{r.label}: weder ja noch nein mit Sicherheit ≥ {r.decide_at:.1f}"

    return f"unklar = {one(ra)}; {one(rb_)} · zusammen: {pol.combination_de(pol.combination_for(fam, fid))}"


def _ai_panel(app: Any, work: dict[str, Any], names: dict[str, str]) -> None:
    ss = st.session_state
    state = _state()
    st.markdown("##### :material/smart_toy: KI-Assistent")
    st.caption("Beschreiben Sie die Regel in eigenen Worten. Die KI wählt die Fakten und füllt den Assistenten aus; "
               "Sie prüfen jeden Schritt und speichern selbst.")
    st.text_area("Ihre Regel in eigenen Worten", key="dm_rw_ai_req", height=120, label_visibility="collapsed",
                 placeholder="z.B. Prüfen, wenn ein Code vorgelesen wurde und offen bleibt, ob er noch gilt.")
    if st.button("Assistent ausfüllen lassen", icon=":material/auto_awesome:", type="primary", width="stretch",
                 disabled=not str(ss.get("dm_rw_ai_req") or "").strip(), key="dm_rw_ai_go"):
        try:
            llm = app.ctx.llm("default")
            with st.spinner("Die KI liest Ihre Beschreibung …"):
                draft = rd.draft_rule(llm, work, ss["dm_rw_ai_req"], names)
        except rd.NeedsNewFamily:
            state["ai_note"] = ("Diese Regel passt zu keiner bestehenden Prüfart. Eine neue Prüfart braucht neue Fakten "
                                "und eine Freigabe (Tab «Fakten»).")
            st.rerun()
        except rd.DraftError as e:
            state["ai_note"] = f"Die KI konnte keinen gültigen Vorschlag machen: {e}"
            st.rerun()
        except Exception as e:  # LLM down / refused: the wizard works without it
            state["ai_note"] = (f"Sprachmodell nicht erreichbar ({type(e).__name__}). Der Assistent links funktioniert "
                                "auch ohne KI.")
            st.rerun()
        labels = pe.fact_labels(work, draft.family)
        with st.status("Die KI füllt den Assistenten aus …", expanded=True) as status:
            st.write(f"Prüfart: **{names.get(draft.family, draft.family)}**")
            time.sleep(AI_DELAY)
            if draft.facts:
                for f in draft.facts:
                    st.write(f":orange-badge[neu] «{f['label']}» gibt es noch nicht")
                    time.sleep(AI_DELAY)
                status.update(label="Die KI braucht einen neuen Fakt", state="error")
                new = new_state()
                new.update(ai_missing=[dict(f) for f in draft.facts], ai_family=draft.family,
                           ai_note="Für diese Regel fehlt ein Fakt. Schlagen Sie ihn als neuen Fakt vor (Freigabe "
                                   "durch eine zweite Person im Tab «Fakten»); danach lässt sich die Regel bauen.",
                           nonce=state["nonce"] + 1, ai_request=draft.request, ai_rule=dict(draft.rule))
                ss[WIZ] = new
                st.rerun()
            filled = state_from_draft(draft, work)
            for key in filled["facts"]:
                c = filled["conds"][key]
                fid = key.split(".", 1)[1]
                st.write(f":blue-badge[{labels.get(fid, fid)}] = **{'nicht ' if c['neg'] else ''}"
                         f"{fpol.VALUE_DE[c['value']]}**")
                time.sleep(AI_DELAY)
            st.write(f"Verknüpfung: **{pe.JOIN_DE[filled['join']]}** · Ergebnis: **{LABEL_DE[filled['label']]}**")
            time.sleep(AI_DELAY)
            st.write(f"Titel: «{filled['title']}»")
            status.update(label="Ausgefüllt — bitte mit «Weiter» prüfen", state="complete")
        filled.update(nonce=state["nonce"] + 1, ai_note="Von der KI ausgefüllt. Bitte jeden Schritt prüfen und am "
                                                        "Ende selbst speichern.")
        ss[WIZ] = filled
        time.sleep(AI_DELAY)
        st.rerun()  # the dialog stays open (its flag is in the session)
    if state.get("ai_note"):
        st.info(state["ai_note"], icon=":material/smart_toy:")
    if state.get("ai_missing"):
        for f in state["ai_missing"]:
            st.markdown(f"**Vorschlag neuer Fakt:** «{ui.esc(f['label'])}»  \n:small[{ui.esc(f.get('de') or '')}]")
        if st.button("Als neuen Fakt vorschlagen", icon=":material/fact_check:", key="dm_rw_ai_newfact",
                     width="stretch"):
            fam = state["ai_family"]
            cand = copy.deepcopy(work)
            for f in state["ai_missing"]:
                pe.upsert_fact(cand, fam, {**f, "id": pe.new_fact_id(cand, fam, f.get("id") or f["label"])})
            try:
                v = fu.store(app).save_draft({"policy_table": cand}, ss.get("dm_user", ""),
                                             comment=f"Neuer Fakt für eine Regel (KI-Vorschlag): {state.get('ai_request', '')}"[:200],
                                             family_names=names)
            except (FourEyesError, PolicyTableError) as e:
                st.error(str(e))
                return
            _flash(f"Fakt als Vorschlag (Version {v.n}) eingereicht: eine zweite Person gibt ihn im Tab «Fakten» frei.")
            _close()
            st.rerun()


@st.dialog("Neue Regel", width="large", on_dismiss=_close)
def rule_wizard(app: Any) -> None:
    ss = st.session_state
    state = _state()
    names = fam_names(app)
    work = fu.live_doc(app)
    pol = fu.try_policy(app)
    base = fu.outcomes(app, pol, work)
    left, right = st.columns([2.1, 1], gap="large")
    with right:
        _ai_panel(app, work, names)
    state = _state()
    n = state["nonce"]
    with left:
        st.markdown(" → ".join(f"**{i}. {t}**" if state["step"] == i else f"{i}. {t}"
                               for i, t in ((1, "Fakten wählen"), (2, "Bedingungen"), (3, "Ergebnis"))))
        fams = list((work.get("families") or {}).keys())
        sel_fam = state_family(state)
        sel_labels = pe.fact_labels(work, sel_fam) if sel_fam else {}
        if state["facts"]:
            st.markdown("Gewählt: " + " ".join(
                f":blue-badge[{ui.esc(sel_labels.get(k.split('.', 1)[1], k.split('.', 1)[1]))}]" for k in state["facts"]))
        # live effect + navigation on top, so they stay in view while the list below is long
        cand, fam = _hits_line(app, pol, work, state, base)
        b1, _, b3 = st.columns(3)
        b1.button("Zurück", icon=":material/arrow_back:", on_click=_step, args=(-1,), disabled=state["step"] == 1,
                  key="dm_rw_back", width="stretch")
        if state["step"] < 3:
            ok = bool(state["facts"]) and sel_fam is not None
            b3.button("Weiter", icon=":material/arrow_forward:", on_click=_step, args=(1,), type="primary",
                      disabled=not ok, key="dm_rw_next", width="stretch")
        else:
            ready = cand is not None and bool(state["title"].strip())
            if b3.button("Speichern (gilt sofort)", icon=":material/check:", type="primary", disabled=not ready,
                         key="dm_rw_save", width="stretch",
                         help="Regeln gelten sofort, ohne Freigabe; jede Änderung wird protokolliert und lässt sich "
                              "rückgängig machen." if ready else "Titel fehlt."):
                try:
                    v = fu.store(app).apply_rules(cand, ss.get("dm_user", ""), comment=f"Neue Regel: {state['title']}",
                                                  family_names=names)
                except (FourEyesError, PolicyTableError) as e:
                    st.error(str(e))
                    return
                reload_everything()
                _flash(f"Regel «{state['title']}» gespeichert: Version {v.n} gilt sofort.")
                _close()
                st.rerun()
        if state["step"] == 1:
            q = st.text_input("Suchen", key="dm_rw_q", placeholder="Fakten suchen, z.B. Code, Handelswunsch, Vollmacht …",
                              label_visibility="collapsed")
            if len({k.split('.', 1)[0] for k in state["facts"]}) > 1:
                st.warning("Eine Regel gehört zu genau einer Prüfart: bitte Fakten nur einer Prüfart wählen.")
            for fam_id in fams:
                facts = [f for f in pe.family_doc(work, fam_id)["facts"]
                         if not q or q.lower() in f"{f.get('label')} {f.get('de')}".lower()]
                if not facts:
                    continue
                st.markdown(f"**{ui.esc(names.get(fam_id, fam_id))}**")
                cols = st.columns(2)
                for i, f in enumerate(facts):
                    key = f"{fam_id}.{f['id']}"
                    cols[i % 2].checkbox(str(f.get("label") or f["id"]), value=key in state["facts"],
                                         key=f"dm_rw_f_{key}_{n}", on_change=_toggle_fact,
                                         args=(key, f"dm_rw_f_{key}_{n}"), help=str(f.get("de") or ""),
                                         disabled=sel_fam is not None and fam_id != sel_fam and key not in state["facts"])
        elif state["step"] == 2:
            for key in state["facts"]:
                fid = key.split(".", 1)[1]
                c = state["conds"].setdefault(key, {"value": "yes", "neg": False})
                with st.container(border=True):
                    a, b, d = st.columns([3, 3, 1], vertical_alignment="center")
                    a.markdown(f"«{ui.esc(sel_labels.get(fid, fid))}»")
                    b.segmented_control("Wert", list(VALUE_OPTS), default=c["value"], key=f"dm_rw_v_{key}_{n}",
                                        format_func=fpol.VALUE_DE.get, label_visibility="collapsed", required=True,
                                        on_change=_set_cond, args=(key, "value", f"dm_rw_v_{key}_{n}"))
                    d.checkbox("nicht", value=c["neg"], key=f"dm_rw_n_{key}_{n}", on_change=_set_cond,
                               args=(key, "neg", f"dm_rw_n_{key}_{n}"))
                    st.caption(_band_text(pol, sel_fam, fid))
            st.toggle("ODER statt UND (eine der Bedingungen genügt)", value=state["join"] == "or",
                      key=f"dm_rw_join_{n}", on_change=_set, args=("join", f"dm_rw_join_{n}"))
        else:
            st.segmented_control("Ergebnis", list(OUTCOMES), default=state["label"], key=f"dm_rw_lab_{n}",
                                 format_func=LABEL_DE.get, required=True, on_change=_set,
                                 args=("label", f"dm_rw_lab_{n}"))
            st.text_input("Titel", value=state["title"], key=f"dm_rw_title_{n}", on_change=_set,
                          args=("title", f"dm_rw_title_{n}"), placeholder="z.B. Code vorgelesen, Gültigkeit offen")
            st.text_area("Beschreibung (sieht die Fallbearbeitung als Begründung)", value=state["text"],
                         key=f"dm_rw_text_{n}", on_change=_set, args=("text", f"dm_rw_text_{n}"), height=90)
            built = state_rule(state, work)
            if built:
                st.markdown(f"**{ui.esc(pe.render_rule(built[1], sel_labels))}**")




# --------------------------------------------------------------------------------------------
# the list
# --------------------------------------------------------------------------------------------


def _apply(app: Any, doc: dict[str, Any], comment: str) -> None:
    try:
        v = fu.store(app).apply_rules(doc, st.session_state.get("dm_user", ""), comment=comment,
                                      family_names=fam_names(app))
    except (FourEyesError, PolicyTableError) as e:
        st.session_state["dm_rg_error"] = str(e)
        return
    st.session_state.pop("dm_rg_error", None)
    reload_everything()
    _flash(f"{comment}: Version {v.n} gilt sofort.")


def _toggle_rule(app: Any, fam: str, rid: str, key: str) -> None:
    doc = fu.live_doc(app)
    on = bool(st.session_state.get(key))
    pe.set_enabled(doc, fam, rid, on)
    _apply(app, doc, f"Regel {rid} {'eingeschaltet' if on else 'ausgeschaltet'}")


def _delete_rule(app: Any, fam: str, rid: str) -> None:
    doc = fu.live_doc(app)
    pe.delete_rule(doc, fam, rid)
    _apply(app, doc, f"Regel {rid} gelöscht")


def _undo(app: Any) -> None:
    try:
        v = fu.store(app).undo_rules(st.session_state.get("dm_user", ""), fam_names(app))
    except (FourEyesError, PolicyTableError) as e:
        st.session_state["dm_rg_error"] = str(e)
        return
    reload_everything()
    _flash(f"Rückgängig gemacht: Version {v.n} gilt sofort.")


def _open() -> None:
    st.session_state["dm_rw_open"] = True
    st.session_state[WIZ] = new_state()


def render(app: Any) -> None:
    ss = st.session_state
    names = fam_names(app)
    if fu.fusion(app) is None:
        st.info("Dieses Profil entscheidet nicht mit den Fakten zweier KI-Leser; Regeln bearbeiten Sie hier im Profil "
                "`dual-facts` (`uv run callguard demo -c dual-facts`).", icon=":material/info:")
        return
    vs = fu.store(app)
    vs.ensure_initial()
    doc = fu.live_doc(app)
    pol = fu.try_policy(app)
    outs = fu.outcomes(app, pol, doc)
    top, undo = st.columns([3, 1.4], vertical_alignment="center")
    top.markdown("Eine Regel verknüpft Fakten zu **Alarm** oder **Prüfen**; von oben nach unten gilt die erste "
                 "zutreffende. Regeln gelten **sofort** (protokolliert, rückgängig machbar).")
    last = vs.last_rule_change()
    undo.button("Letzte Änderung rückgängig", icon=":material/undo:", on_click=_undo, args=(app,),
                disabled=last is None, width="stretch", key="dm_rg_undo")
    st.button("Neue Regel", icon=":material/add:", type="primary", on_click=_open, key="dm_rg_new")
    if ss.get("dm_rg_error"):
        st.error(ss["dm_rg_error"], icon=":material/error:")
    for fam in (doc.get("families") or {}):
        fdoc = pe.family_doc(doc, fam)
        labels = pe.fact_labels(doc, fam)
        hits = fu.rule_hits(outs, fam)
        rules = [r for r in fdoc["rules"] if str(r.get("when")) != "true"]
        st.markdown(f"#### {ui.esc(names.get(fam, fam))}")
        if not rules:
            st.caption("Noch keine Regel — ohne Regel gilt «Kein Alarm».")
        for r in rules:
            rid = str(r["id"])
            on = pe.is_enabled(r)
            lab = str(r.get("label"))
            if on:
                calls = hits.get(rid, [])
                hit_txt = f"greift bei {len(calls)} Anruf{'en' if len(calls) != 1 else ''}"
            else:
                node = parse_rule(str(r.get("when", "true")))
                calls = [cid for cid, o in sorted(outs.items()) if fam in o.families and eval_hard(
                    node, {fid: x.value for fid, x in o.families[fam].facts.items()})]
                hit_txt = f"aus · wäre erfüllt bei {len(calls)}"
            with st.container(border=True):
                a, b, c, d = st.columns([7, 1.6, 0.8, 0.6], vertical_alignment="center")
                a.markdown(f":{LABEL_COLOR.get(lab, 'gray')}-badge[{LABEL_DE.get(lab, lab)}] "
                           f"**{ui.esc(rule_title(r))}**  \n:small[{ui.esc(pe.render_rule(r, labels))}]")
                with b.popover(hit_txt, width="stretch"):
                    st.markdown(" · ".join(f"{fu.call_link(x)} ({LABEL_DE[outs[x].label]})" for x in calls)
                                or "keine Anrufe")
                key = f"dm_rg_on_{fam}_{rid}"
                ss[key] = on
                c.toggle("an", key=key, on_change=_toggle_rule, args=(app, fam, rid, key), label_visibility="collapsed")
                d.button("", icon=":material/delete:", key=f"dm_rg_del_{fam}_{rid}", on_click=_delete_rule,
                         args=(app, fam, rid), help="Regel löschen (sofort, rückgängig machbar)")
    with st.expander("Verlauf der Regeländerungen", icon=":material/history:"):
        for v in list(reversed(vs.versions()))[:10]:
            kind = "sofort" if v.meta.get("instant") else ("Freigabe " + str(v.meta.get("approver") or "–"))
            st.markdown(f"**Version {v.n}** · {kind} · {ui.esc(v.author)} · {str(v.meta.get('created', ''))[:16]}  \n"
                        f":small[{ui.esc(str(v.meta.get('comment') or ''))}]")
    if ss.get("dm_rw_open"):
        rule_wizard(app)
