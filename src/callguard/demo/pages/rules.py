"""Regeln: pure logic over the facts (UND / ODER / NICHT over ja / nein / unklar), first matching rule decides.

Top: «Wie streng?» (Alarmschwelle). Then per Prüfart the rule cards (on/off, order, delete) with live «greift bei N
Anrufen» and the hit list, a rule builder (fact chips with ja / nein / unklar and NICHT, joined by UND / ODER, outcome)
whose hits update while editing, and «Regel mit KI formulieren» (may only use existing facts; a new fact goes the
«Fakten» route with approval). «Übernehmen» applies instantly: version entry + audit event + one-click undo, no second
person. Facts are NOT edited here (tab «Fakten», four eyes).
"""

from __future__ import annotations

import copy

import streamlit as st

from callguard import audit
from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard import rule_drafter as rd
from callguard.checks.facts import PolicyTableError, eval_hard, parse_rule
from callguard.demo import controls as ctl
from callguard.demo import facts_ui as fu
from callguard.policy_versions import FourEyesError
from callguard.types import LABELS
from callguard.ui import render as ui
from callguard.ui.backend import label_counts, short_label
from callguard.ui.session import current_app, reload_everything

ss = st.session_state
app = current_app()
LABEL_DE = fu.LABEL_DE
LABEL_COLOR = {"alarm": "red", "review": "orange", "no_alert": "green"}
VALUE_OPTS = ["yes", "no", "unclear"]

st.title("Regeln")
for msg in ss.pop("dm_rg_messages", []):
    st.toast(msg, icon=":material/check_circle:")
st.info("**Regeln** verknüpfen die Fakten (ja / nein / unklar) mit UND / ODER / NICHT zu **Alarm / Prüfen / Kein "
        "Alarm**; von oben nach unten gilt die erste zutreffende Regel. Regeln brauchen keine KI: jede Änderung rechnet "
        "alle verarbeiteten Anrufe sofort neu. **«Übernehmen» gilt sofort** (ohne Freigabe; protokolliert, als Version "
        "gespeichert, mit einem Klick rückgängig). **Fakten** (die Fragen an die KI) ändern Sie im Tab «Fakten» — dort "
        "braucht es eine zweite Person.", icon=":material/lightbulb:")


def _flash(msg: str) -> None:
    ss.setdefault("dm_rg_messages", []).append(msg)


vs = fu.store(app)
try:
    act = vs.ensure_initial()
except Exception as e:
    st.error(f"Das aktive Regelwerk ist unlesbar: {type(e).__name__}: {e}")
    st.stop()
live = fu.live_doc(app)
live_key = pe.dump_doc(live)
if ss.get("dm_rg_live") != live_key or "dm_rg_doc" not in ss:  # working copy follows the live table
    ss["dm_rg_doc"], ss["dm_rg_live"] = copy.deepcopy(live), live_key
work = ss["dm_rg_doc"]
ss.setdefault("dm_user", audit.current_user())
pol = fu.try_policy(app)
has_policy = fu.fusion(app) is not None

# ================================================================================================================
# how strict
# ================================================================================================================

st.header("Wie streng?", anchor="wie-streng", divider="gray")
counts, base = label_counts(app.decided), label_counts(app.baseline)
c1, c2 = st.columns([1, 1], gap="large")
with c1:
    ctl.threshold_slider(app)
    st.markdown(" · ".join(f"{LABEL_DE[lbl]} **{counts[lbl]}**"
                           + (f" ({counts[lbl] - base[lbl]:+d})" if counts[lbl] != base[lbl] else "")
                           for lbl in LABELS) + f" von {len(app.decided)} Anrufen")
with c2:
    if has_policy:
        st.markdown(f"**Zwei KI-Leser:** {pol.a.label} ({pol.a.describe()}), {pol.b.label} ({pol.b.describe()}), "
                    f"zusammen **{pol.combination_de()}**.")
        st.page_link(app.pages["facts"], label="Bänder und Kombination im Tab «Fakten» einstellen",
                     icon=":material/fact_check:")
        st.caption("Breiteres Band oder «Einigkeit» = mehr «unklar» = mehr Prüfen (mehr Arbeit, weniger übersehen).")
    else:
        ctl.mode_control(app, details=True)

if not has_policy:
    st.warning("Dieses Profil entscheidet nicht mit der Fakten-Einstellung zweier Leser; Regeln bearbeiten Sie hier im "
               "Profil `dual-facts` (`uv run callguard demo -c dual-facts`).", icon=":material/info:")
    st.stop()

# ================================================================================================================
# status: active version, undo, pending working copy
# ================================================================================================================

outs_live = fu.outcomes(app, pol, live)
try:
    work_table = pe.validate(work)
except PolicyTableError as e:
    st.error(f"Arbeitskopie ungültig: {e}")
    ss["dm_rg_doc"] = copy.deepcopy(live)
    st.stop()
outs_work = fu.outcomes(app, pol, work_table)
pending = pe.diff_docs(live, work, {f.id: short_label(f.label) for f in app.all_families})


def _apply(doc: dict, comment: str = "") -> None:
    try:
        v = vs.apply_rules(doc, ss.get("dm_user", ""), comment=comment,
                           family_names={f.id: short_label(f.label) for f in app.all_families})
    except (FourEyesError, PolicyTableError) as e:
        ss["dm_rg_error"] = str(e)
        return
    ss.pop("dm_rg_error", None)
    reload_everything()
    ss.pop("dm_rg_live", None)
    _flash(f"Regeln übernommen: Version {v.n} gilt sofort.")


def _undo() -> None:
    try:
        v = vs.undo_rules(ss.get("dm_user", ""), {f.id: short_label(f.label) for f in app.all_families})
    except (FourEyesError, PolicyTableError) as e:
        ss["dm_rg_error"] = str(e)
        return
    reload_everything()
    ss.pop("dm_rg_live", None)
    _flash(f"Rückgängig gemacht: Version {v.n} gilt sofort.")


def _discard() -> None:
    ss.pop("dm_rg_live", None)


with st.container(border=True):
    c1, c2, c3 = st.columns([3, 1.3, 1.2], vertical_alignment="bottom")
    last = vs.last_rule_change()
    c1.markdown(f":material/verified: Aktiv: **Version {act.n}** · {ui.esc(str(act.meta.get('comment') or ''))} · "
                f"{ui.esc(act.author)} · {str(act.meta.get('approved_at', ''))[:16]}")
    c2.text_input("Ihr Name", key="dm_user", help="Wird im Audit-Log und in der Version vermerkt.")
    c3.button("Letzte Regeländerung rückgängig", icon=":material/undo:", on_click=_undo, disabled=last is None,
              width="stretch", help=(f"Setzt die Regeln von Version {last.meta.get('parent')} wieder ein (sofort)."
                                     if last else "Die aktive Version ist keine sofortige Regeländerung."))
    if pending:
        line, changed = fu.effect_md(outs_live, outs_work)
        st.markdown(f":material/edit_note: **{len(pending)} Änderung{'en' if len(pending) != 1 else ''} ausprobiert, "
                    f"noch nicht übernommen** — {line}")
        st.markdown("\n".join(f"- {ui.esc(p)}" for p in pending))
        b1, b2 = st.columns(2)
        b1.button("Übernehmen (gilt sofort, ohne Freigabe)", type="primary", icon=":material/check:",
                  on_click=_apply, args=(work,), width="stretch")
        b2.button("Verwerfen", icon=":material/delete:", on_click=_discard, width="stretch")
    if ss.get("dm_rg_error"):
        st.error(ss["dm_rg_error"], icon=":material/error:")

# ================================================================================================================
# rule cards per Prüfart
# ================================================================================================================


def _edit(fn, *args) -> None:
    cand = copy.deepcopy(ss["dm_rg_doc"])
    try:
        fn(cand, *args)
        pe.validate(cand)
    except (PolicyTableError, KeyError, ValueError) as e:
        ss["dm_rg_error"] = str(e)
        return
    ss["dm_rg_doc"] = cand


def _toggle(fam: str, rid: str, key: str) -> None:
    _edit(pe.set_enabled, fam, rid, bool(ss[key]))


def rule_card(fam: str, i: int, rule: dict, n: int, labels: dict[str, str], hits: dict, would: dict) -> None:
    rid = str(rule.get("id"))
    on = pe.is_enabled(rule)
    with st.container(border=True):
        c1, c2 = st.columns([7, 2.2], vertical_alignment="top")
        lab = str(rule.get("label"))
        c1.markdown(f"**{i + 1}.** :{LABEL_COLOR.get(lab, 'gray')}-badge[{LABEL_DE.get(lab, lab)}] "
                    f"{'' if on else ':gray-badge[aus]'} `{rid}`  \n{ui.esc(pe.render_rule(rule, labels))}")
        if rule.get("text"):
            c1.caption(ui.esc(str(rule["text"])))
        calls = hits.get(rid, []) if on else would.get(rid, [])
        c1.markdown(f":material/bolt: **{'greift bei' if on else 'wäre erfüllt bei'} {len(calls)} Anruf"
                    f"{'en' if len(calls) != 1 else ''}**" + ("" if on else " (ausgeschaltet)"))
        if calls:
            with c1.expander("Trefferliste"):
                st.markdown(" · ".join(f"{fu.call_link(c)} ({LABEL_DE[outs_work[c].label]})" for c in calls))
        tkey = f"dm_rg_on_{fam}_{rid}"
        ss[tkey] = on
        with c2:
            st.toggle("an", key=tkey, on_change=_toggle, args=(fam, rid, tkey))
            b1, b2, b3 = st.columns(3)
            b1.button("", icon=":material/arrow_upward:", key=f"dm_rg_up_{fam}_{rid}", disabled=i == 0,
                      on_click=_edit, args=(pe.move_rule, fam, rid, -1), help="nach oben")
            b2.button("", icon=":material/arrow_downward:", key=f"dm_rg_dn_{fam}_{rid}", disabled=i == n - 1,
                      on_click=_edit, args=(pe.move_rule, fam, rid, 1), help="nach unten")
            b3.button("", icon=":material/delete:", key=f"dm_rg_del_{fam}_{rid}", on_click=_edit,
                      args=(pe.delete_rule, fam, rid), help="löschen", disabled=str(rule.get("when")) == "true")


def builder(fam: str, labels: dict[str, str]) -> None:
    """Tick facts as chips, give each ja / nein / unklar (and NICHT), join with UND / ODER, pick the outcome."""
    k = f"dm_rb_{fam}"
    facts = list(labels)
    chosen = st.pills("Fakten (anklicken)", facts, selection_mode="multi", key=f"{k}_facts",
                      format_func=lambda f: labels[f])
    conds: list[tuple[str, str, bool]] = []
    for fid in chosen or []:
        c1, c2, c3 = st.columns([3, 3, 1.2], vertical_alignment="center")
        c1.markdown(f"«{ui.esc(labels[fid])}»")
        v = c2.segmented_control("Wert", VALUE_OPTS, key=f"{k}_v_{fid}", required=True, default="yes",
                                 format_func=fpol.VALUE_DE.get, label_visibility="collapsed")
        neg = c3.checkbox("NICHT", key=f"{k}_n_{fid}")
        conds.append((fid, v or "yes", bool(neg)))
    c1, c2, c3 = st.columns([1.2, 2, 3])
    join = c1.segmented_control("Verknüpfung", ["and", "or"], key=f"{k}_join", required=True, default="and",
                                format_func=pe.JOIN_DE.get)
    label = c2.segmented_control("Ergebnis", list(LABELS), key=f"{k}_label", required=True, default="review",
                                 format_func=LABEL_DE.get)
    text = c3.text_input("Erklärung für die Fallbearbeitung", key=f"{k}_text",
                         placeholder="z.B. Code vorgelesen, Gültigkeit offen.")
    if not conds:
        st.caption("Wählen Sie oben mindestens einen Fakt.")
        return
    when = fu.build_when(conds, join or "and")
    rule = {"id": pe.new_rule_id(work, fam, label or "review"), "label": label or "review", "when": when,
            "text": text.strip()}
    try:
        cand, pos = fu.with_rule(work, fam, rule)
        cand_table = pe.validate(cand)
    except PolicyTableError as e:
        st.error(str(e))
        return
    st.markdown(f"**Vorschau:** {ui.esc(pe.render_rule(rule, labels))} (an Position {pos + 1})")
    outs_new = fu.outcomes(app, pol, cand_table)
    calls = fu.rule_hits(outs_new, fam).get(rule["id"], [])
    line, changed = fu.effect_md(outs_work, outs_new)
    with st.container(border=True):
        st.markdown(f":material/bolt: Diese Regel **greift bei {len(calls)} Anruf{'en' if len(calls) != 1 else ''}** "
                    f"und {line}.")
        if calls:
            st.markdown("Treffer: " + " · ".join(f"{fu.call_link(c)} ({LABEL_DE[outs_new[c].label]})" for c in calls[:30]))
    b1, b2 = st.columns(2)
    if b1.button("Hinzufügen und übernehmen (gilt sofort)", type="primary", icon=":material/check:", key=f"{k}_apply"):
        _apply(cand, comment=f"Neue Regel {rule['id']}")
        for x in [x for x in ss if str(x).startswith(k)]:
            del ss[x]
        st.rerun()
    if b2.button("Nur ausprobieren (in die Arbeitskopie)", icon=":material/science:", key=f"{k}_try"):
        ss["dm_rg_doc"] = cand
        for x in [x for x in ss if str(x).startswith(k)]:
            del ss[x]
        st.rerun()


def ai_builder(fam_names: dict[str, str]) -> None:
    st.markdown("Beschreiben Sie die Regel in eigenen Worten. Die KI darf **nur bestehende Fakten** verwenden; braucht "
                "die Regel eine neue Frage, geht sie als Entwurf in den Tab «Fakten» (Freigabe durch zweite Person).")
    st.text_area("Regel in eigenen Worten", key="dm_ai_request", height=80,
                 placeholder="Prüfen, wenn ein Code vorgelesen wurde und unklar ist, ob er noch gilt.")
    if st.button("Regel mit KI formulieren", icon=":material/auto_awesome:", type="primary",
                 disabled=not str(ss.get("dm_ai_request") or "").strip()):
        try:
            llm = app.ctx.llm("default")
            ss["dm_ai"], ss["dm_ai_error"] = rd.draft_rule(llm, work, ss["dm_ai_request"], fam_names), None
        except rd.DraftError as e:
            ss["dm_ai"], ss["dm_ai_error"] = None, str(e)
        except Exception as e:
            ss["dm_ai"], ss["dm_ai_error"] = None, (f"Sprachmodell nicht erreichbar ({type(e).__name__}: "
                                                    f"{str(e)[:160]}). Der Regel-Baukasten oben braucht keine KI.")
    if ss.get("dm_ai_error"):
        st.warning(ss["dm_ai_error"], icon=":material/cloud_off:")
    draft: rd.Draft | None = ss.get("dm_ai")
    if draft is None:
        return
    labels = {**pe.fact_labels(work, draft.family), **{f["id"]: f["label"] for f in draft.facts}}
    with st.container(border=True):
        st.markdown(f":orange-badge[:material/smart_toy: von KI vorgeschlagen — bitte prüfen] "
                    f"Prüfart **{ui.esc(fam_names.get(draft.family, draft.family))}**  \n"
                    f"{ui.esc(pe.render_rule(draft.rule, labels))}")
        if draft.facts:
            st.warning("Diese Regel braucht **neue Fakten**: " + ", ".join(f"«{f['label']}»" for f in draft.facts)
                       + ". Neue Fragen muss die KI erst beantworten, und eine zweite Person muss sie freigeben.",
                       icon=":material/fact_check:")
            if st.button("Als Fakten-Entwurf in den Tab «Fakten»", icon=":material/arrow_forward:"):
                base_doc = ss.get("rw_doc") or copy.deepcopy(live)
                ss["rw_doc"] = rd.apply_draft(base_doc, draft)
                audit.log_event(app.runs_dir, "policy_ai_draft", user=ss.get("dm_user"), request=draft.request,
                                family=draft.family, rule=draft.rule, facts=draft.facts, via="demo-regeln")
                ss["dm_ai"] = None
                st.switch_page(app.pages["facts"])
            return
        try:
            cand = rd.apply_draft(work, draft)
            outs_new = fu.outcomes(app, pol, pe.validate(cand))
        except (PolicyTableError, KeyError) as e:
            st.error(f"Entwurf ungültig: {e}")
            return
        line, _ = fu.effect_md(outs_work, outs_new)
        st.markdown(f":material/bolt: {line}")
        b1, b2 = st.columns(2)
        if b1.button("Übernehmen (gilt sofort)", type="primary", icon=":material/check:", key="dm_ai_apply"):
            _apply(cand, comment=f"KI-Regel: {draft.request[:80]}")
            ss["dm_ai"] = None
            st.rerun()
        if b2.button("Verwerfen", key="dm_ai_discard"):
            ss["dm_ai"] = None
            st.rerun()


st.header("Regeln je Prüfart", anchor="regeln", divider="gray")
fam_names = {f.id: short_label(f.label) for f in app.all_families}
fam_ids = list((work.get("families") or {}).keys())
for tab, fam in zip(st.tabs([fam_names.get(f, f) for f in fam_ids]), fam_ids):
    with tab:
        fdoc = pe.family_doc(work, fam)
        labels = pe.fact_labels(work, fam)
        hits = fu.rule_hits(outs_work, fam)
        would: dict[str, list[str]] = {}
        for r in fdoc["rules"]:
            if not pe.is_enabled(r):
                node = parse_rule(str(r.get("when", "true")))
                would[str(r["id"])] = [cid for cid, o in sorted(outs_work.items()) if fam in o.families and eval_hard(
                    node, {fid: x.value for fid, x in o.families[fam].facts.items()})]
        for i, r in enumerate(fdoc["rules"]):
            rule_card(fam, i, r, len(fdoc["rules"]), labels, hits, would)
        with st.expander("Neue Regel bauen", icon=":material/add_circle:", expanded=False):
            builder(fam, labels)

st.header("Regel mit KI formulieren", anchor="ki", divider="gray")
ai_builder(fam_names)

with st.expander("Verlauf der Regeländerungen", icon=":material/history:"):
    for v in list(reversed(vs.versions()))[:12]:
        kind = "sofort (Regeln)" if v.meta.get("instant") else ("Freigabe " + str(v.meta.get("approver") or "–"))
        st.markdown(f"**Version {v.n}** · {ui.esc(v.status)} · {kind} · {ui.esc(v.author)} · "
                    f"{str(v.meta.get('created', ''))[:16]}  \n:small[{ui.esc(str(v.meta.get('comment') or ''))}]")
