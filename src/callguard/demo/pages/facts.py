"""Fakten: what the AI is asked, how the two AI readers' answers become ja / nein / unklar, and where they disagree.

Top: how the two readers decide together (combination) and each reader's band, with the instant effect on every
processed call («ändert 4 von 60 Anrufen: +3 Prüfen, −1 Alarm»). Trying out is session-only. Below, per Prüfart, each
fact: full question, both readers' p(ja) over all calls (strip, band shaded), an optional per-fact setting, and the
calls where the readers disagree. Changing facts (questions, new facts, default bands / combination) needs the AI to
answer again and a second person's approval: the Regelwerk machinery (``ui/views/rules.py``, embedded) does the draft,
preview, versions and four-eyes approval.
"""

from __future__ import annotations

import copy
import runpy
from pathlib import Path

import streamlit as st

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard import rulebook as rb
from callguard.demo import facts_ui as fu
from callguard.policy_versions import merge_tables
from callguard.ui import render as ui
from callguard.ui.backend import short_label
from callguard.ui.session import current_app

RULES = Path(__file__).resolve().parents[2] / "ui" / "views" / "rules.py"
ss = st.session_state
app = current_app()
fus = fu.fusion(app)

st.title("Fakten")
for msg in ss.pop("dm_fk_messages", []):
    st.toast(msg, icon=":material/check_circle:")

# -- keep the Regelwerk working copy on top of rules applied instantly (tab «Regeln») -------------------------------
vs = fu.store(app)
try:
    act = vs.ensure_initial()
except Exception as e:
    st.error(f"Das aktive Regelwerk ist unlesbar: {type(e).__name__}: {e}")
    st.stop()
if "rw_doc" in ss and ss.get("rw_base") not in (None, act.n):
    try:
        base = vs.get(int(ss["rw_base"]))
        merged = merge_tables(base.doc(), act.doc(), ss["rw_doc"])
        if merged is not None:
            base_b, live_b = base.bundle(), vs.live_bundle()
            ss["rw_doc"] = merged
            ss["rw_extra"] = {k: (live_b.get(k) if v == base_b.get(k) else v) for k, v in ss.get("rw_extra", {}).items()}
            for k in set(live_b) - set(ss["rw_extra"]) - {"policy_table"}:
                ss["rw_extra"][k] = live_b[k]
            ss["rw_base"] = act.n
    except Exception:
        pass

rw = runpy.run_path(str(RULES), init_globals={"RW_LAYOUT": "embedded"})  # loads state, draws nothing yet
names = rw["fam_names"]
doc = live_doc = fu.live_doc(app)
table = pe.validate(doc)

if fus is None:
    st.info("Dieses Profil liest die Fakten mit **einem** KI-Leser. Die Einstellungen für zwei Leser (Bänder, "
            "Einigkeit) gibt es mit dem Profil `dual-facts` (`uv run callguard demo -c dual-facts`). Fragen ändern und "
            "freigeben geht auch hier.", icon=":material/info:")

live_pol = fu.live_policy(app)
pol = fu.try_policy(app)
trying = pol.key() != live_pol.key()
A, B = pol.a, pol.b

st.info(f"**Fakten** sind kleine Ja/Nein-Fragen pro Prüfart. Zwei KI-Leser beantworten jede Frage für jeden Anruf mit "
        f"einer Wahrscheinlichkeit: **{A.label}** ({A.model or A.check}) und **{B.label}** ({B.model or B.check}). "
        "Hier legen Sie fest, ab wann eine Antwort als *ja / nein / unklar* gilt und wie die beiden zusammen entscheiden. "
        "**Ausprobieren wirkt sofort und nur für Sie.** Als neue Voreinstellung oder mit geänderten Fragen gilt es erst "
        "nach **Freigabe durch eine zweite Person** (unten). Die **Regeln** (Tab «Regeln») machen aus den Fakten "
        "Alarm / Prüfen / Kein Alarm.", icon=":material/lightbulb:")

# ================================================================================================================
# 1 · how the two readers decide together (global)
# ================================================================================================================

if fus is not None:
    st.header("Wie die zwei KI-Leser zusammen entscheiden", anchor="leser", divider="gray")
    if trying:
        st.markdown(":orange-badge[:material/science: Sie probieren gerade aus — nur für Sie sichtbar, ändert nichts "
                    "für andere]")

    def _set_comb() -> None:
        fu.set_try(fu.try_policy(app).with_combination(ss["dm_fk_comb"]))

    def _set_band(i: int, key: str) -> None:
        lo, hi = ss[key]
        fu.set_try(fu.try_policy(app).with_reader(i, mode="band", lo=float(lo), hi=float(hi)))

    def _set_mode(i: int, key: str) -> None:
        p = fu.try_policy(app)
        fu.set_try(p.with_reader(i, mode="band" if ss[key] == "band" else "three_way"))

    ss["dm_fk_comb"] = pol.combination
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.segmented_control("Kombination", list(fpol.COMBINATIONS), key="dm_fk_comb", required=True,
                             format_func=lambda m: pol.combination_de(m), on_change=_set_comb,
                             help="Wie aus den zwei Antworten ein Wert wird, der in die Regeln geht.")
        for m in fpol.COMBINATIONS:
            mark = "**" if m == pol.combination else ""
            note = fu.knob_text("combination", m)
            st.markdown(f"{mark}{pol.combination_de(m)}{mark}" + (" · :gray-badge[vorregistrierter Standard]"
                                                                   if m == "agree" else "")
                        + f"  \n:small[{fpol.combination_help(m, A.label, B.label)}"
                        + (f" *Gemessen (Dev):* {note}" if note else "") + "]")
    with right:
        for i, r in enumerate(pol.readers):
            st.markdown(f"**{r.label}** ({r.model or r.check})")
            mkey, bkey = f"dm_fk_mode_{i}", f"dm_fk_band_{i}"
            ss[mkey] = r.mode
            ss[bkey] = (float(r.lo), float(r.hi))
            c1, c2 = st.columns([1, 1.6], vertical_alignment="bottom")
            c1.segmented_control("Regel für ja/nein", ["three_way", "band"], key=mkey, required=True,
                                 format_func=lambda m: {"three_way": "drei Antworten", "band": "Band"}[m],
                                 on_change=_set_mode, args=(i, mkey), label_visibility="collapsed")
            if r.mode == "band":
                c2.slider("unklar zwischen", 0.0, 1.0, step=0.05, key=bkey, on_change=_set_band, args=(i, bkey),
                          help="p(ja) ab dem oberen Wert = ja, bis zum unteren Wert = nein, dazwischen unklar. "
                               "Breiteres Band = mehr «unklar» = mehr Prüfen (mehr Arbeit, weniger übersehen).")
                note = fu.knob_text("band", f"{r.lo:.1f}-{r.hi:.1f}") if i == 1 else None
                if note:
                    st.caption(f"Gemessen (Dev): {note}")
            else:
                c2.caption(f"ja wenn p(ja) ≥ {r.decide_at:.2f}, nein wenn p(nein) ≥ {r.decide_at:.2f}, sonst unklar")

    before = fu.outcomes(app, live_pol, live_doc)
    after = fu.outcomes(app, pol, live_doc)
    line, changed = fu.effect_md(before, after)
    with st.container(border=True):
        st.markdown(f":material/bolt: **Wirkung gegenüber der aktiven Einstellung:** {line}")
        if changed:
            with st.expander(f"Welche Anrufe ({len(changed)})"):
                st.markdown(" · ".join(f"{fu.call_link(c)} {fu.LABEL_DE[a]} → **{fu.LABEL_DE[b]}**"
                                       for c, a, b in changed))
        c1, c2 = st.columns(2)
        if c1.button("Als neue Voreinstellung vorschlagen", icon=":material/how_to_reg:", disabled=not trying,
                     help="Fakten-Einstellungen ändern: Freigabe durch zweite Person nötig. Landet als Änderung in der "
                          "Arbeitskopie; unten speichern und freigeben lassen.", width="stretch"):
            ss.setdefault("rw_extra", {})["fact_policy"] = pol.as_dict()
            ss.setdefault("dm_fk_messages", []).append(
                "In die Arbeitskopie übernommen. Unten «Entwurf prüfen & speichern», dann gibt eine zweite Person frei.")
            st.rerun()
        if c2.button("Zurück zur aktiven Einstellung", icon=":material/undo:", disabled=not trying, width="stretch"):
            fu.set_try(None)
            st.rerun()
        st.caption("Ausprobieren rechnet alle verarbeiteten Anrufe sofort neu (gespeicherte Antworten beider Leser, "
                   "kein Sprachmodell).")

# ================================================================================================================
# 2 · per Prüfart: the facts
# ================================================================================================================

st.header("Fakten je Prüfart", anchor="fakten", divider="gray")
answers = fpol.fact_answers(app.loaded.results, pol) if fus is not None else {}
outs_try = fu.outcomes(app, pol, live_doc) if fus is not None else {}


def _set_override(fam: str, fid: str, which: str) -> None:
    p = fu.try_policy(app)
    if which == "band":
        lo, hi = ss[f"dm_fo_band_{fam}_{fid}"]
        p = p.with_override(fam, fid, reader=p.b.id, band=[float(lo), float(hi)])
    elif which == "comb":
        c = ss[f"dm_fo_comb_{fam}_{fid}"]
        p = p.with_override(fam, fid, combination=None if c == "global" else c)
        if c == "global":
            ov = p.overrides.get(f"{fam}.{fid}")
            p = p.with_override(fam, fid, clear=True) if ov is not None and not ov.readers else p
            if ov is not None and ov.readers:  # keep the band, drop the combination
                p = fpol.FactPolicy(p.readers, p.combination, {**p.overrides, f"{fam}.{fid}": fpol.FactOverride(
                    readers=ov.readers)}, p.source)
    else:
        p = p.with_override(fam, fid, clear=True)
    fu.set_try(p)


def fact_card(fam: str, f: dict) -> None:
    fid = str(f["id"])
    ra, rb_ = pol.reader(0, fam, fid), pol.reader(1, fam, fid)
    comb = pol.combination_for(fam, fid)
    with st.container(border=True):
        if ss.get("rw_fact_edit") == (fam, fid):
            st.markdown(":orange-badge[Fakten ändern: Freigabe durch zweite Person nötig]")
            rw["fact_editor"](fam, f)
            st.button("Abbrechen", key=f"dm_fx_cancel_{fam}_{fid}", on_click=lambda: ss.update(rw_fact_edit=None))
            return
        head, btn = st.columns([6, 1], vertical_alignment="top")
        head.markdown(f"**{ui.esc(str(f.get('label') or fid))}** · "
                      f":gray-badge[{ui.esc(pe.ROLE_DE.get(str(f.get('role')), str(f.get('role'))).split(' (')[0])}]"
                      + (" · :violet-badge[eigene Einstellung]" if pol.has_override(fam, fid) else "")
                      + f"  \n{ui.esc(str(f.get('de') or ''))}")
        btn.button("Frage ändern", key=f"dm_fx_btn_{fam}_{fid}", icon=":material/edit:", width="stretch",
                   on_click=lambda t=(fam, fid): ss.update(rw_fact_edit=t),
                   help="Fakten ändern: Freigabe durch zweite Person nötig; die KI muss neu antworten.")
        if fus is None:
            return
        head.caption(f"Beantwortet von **{ra.label}** ({ra.describe()}) und **{rb_.label}** ({rb_.describe()}) · "
                     f"zusammen: **{pol.combination_de(comb)}**")
        ans = answers.get((fam, fid)) or []
        if not ans:
            st.caption(":material/sync_problem: Noch keine gespeicherten Antworten für diese Frage.")
            return
        st.altair_chart(fu.strip_chart(ans, pol, fam, fid), width="stretch")
        cnt = fpol.value_counts(ans, pol, fam, fid)
        fmt = lambda d: " · ".join(f"{fpol.VALUE_DE[v]} {d[v]}" for v in fpol.VALUES)  # noqa: E731
        st.caption(f"Über {len(ans)} Anrufe — {ra.label}: {fmt(cnt['a'])} | {rb_.label}: {fmt(cnt['b'])} | "
                   f"**zusammen: {fmt(cnt['combined'])}**")
        dis = fpol.disagreements(ans, pol, fam, fid)
        c1, c2 = st.columns(2)
        with c1.expander(f"Uneinigkeiten ({len(dis)})", icon=":material/call_split:"):
            if not dis:
                st.caption("Beide Leser kommen bei allen Anrufen zum gleichen Wert.")
            else:
                st.dataframe([{"Anruf": f"anruf?call={d.fact}", f"{ra.label} p(ja)": round((d.pa or {}).get("yes", 0), 2),
                               f"{rb_.label} p(ja)": round((d.pb or {}).get("yes", 0), 2),
                               ra.label: fpol.VALUE_DE[d.va], rb_.label: fpol.VALUE_DE[d.vb],
                               "zusammen": fpol.VALUE_DE[d.value],
                               "Anruf jetzt": fu.LABEL_DE[outs_try[d.fact].label] if d.fact in outs_try else ""}
                              for d in dis], hide_index=True,
                             column_config={"Anruf": st.column_config.LinkColumn("Anruf", display_text=r"call=(.*)")})
                st.caption("Ein Klick auf den Anruf öffnet ihn in «Anruf prüfen».")
        with c2.expander("Eigene Einstellung für diesen Fakt", icon=":material/tune:"):
            bkey, ckey = f"dm_fo_band_{fam}_{fid}", f"dm_fo_comb_{fam}_{fid}"
            ss[bkey] = (float(rb_.lo), float(rb_.hi))
            ov = pol.overrides.get(f"{fam}.{fid}")
            ss[ckey] = (ov.combination if ov and ov.combination else "global")
            st.slider(f"{rb_.label}: unklar zwischen", 0.0, 1.0, step=0.05, key=bkey, on_change=_set_override,
                      args=(fam, fid, "band"))
            st.selectbox("Kombination", ["global", *fpol.COMBINATIONS], key=ckey, on_change=_set_override,
                         args=(fam, fid, "comb"),
                         format_func=lambda m: f"wie allgemein ({pol.combination_de()})" if m == "global"
                         else pol.combination_de(m))
            if pol.has_override(fam, fid):
                no_ov = pol.with_override(fam, fid, clear=True)
                line, _ = fu.effect_md(fu.outcomes(app, no_ov, live_doc), outs_try)
                st.markdown(f":material/bolt: Diese Ausnahme {line}.")
                st.button("Ausnahme entfernen", key=f"dm_fo_clear_{fam}_{fid}", on_click=_set_override,
                          args=(fam, fid, "clear"))


fam_ids = list((doc.get("families") or {}).keys())
if fam_ids:
    for tab, fam in zip(st.tabs([names.get(f, short_label(f)) for f in fam_ids]), fam_ids):
        with tab:
            fdoc = pe.family_doc(copy.deepcopy(doc), fam)
            for f in fdoc["facts"]:
                fact_card(fam, f)
            with st.expander("Neue Frage anlegen (Freigabe durch zweite Person nötig)", icon=":material/add:"):
                rw["fact_editor"](fam, None)

# ================================================================================================================
# 3 · governance: facts need a second person
# ================================================================================================================

st.header("Fakten ändern: Freigabe durch zweite Person nötig", anchor="freigabe", divider="gray")
st.caption("Neue oder umformulierte Fragen, neue Prüfarten und neue Voreinstellungen der Leser (Bänder, Kombination) "
           "landen zuerst in einer Arbeitskopie. Die Vorschau zeigt, welche Anrufe sich ändern würden (neue Fragen muss "
           "die KI zuerst beantworten, bis dahin gelten sie als «unklar»). Gespeichert wird ein Entwurf; er gilt erst, "
           "wenn eine **zweite Person** ihn freigibt. Regeln dagegen ändern Sie im Tab «Regeln» sofort.")
rw["status_row"]()
n_changes, n_drafts = len(rw["changes"]), rw["n_drafts"]
t1, t2, t3 = st.tabs([f"Entwurf prüfen & speichern{f' ({n_changes})' if n_changes else ''}",
                      f"Versionen & Freigabe{f' ({n_drafts})' if n_drafts else ''}", "Neue Prüfart"])
with t1:
    rw["preview_tab"]()
with t2:
    rw["versions_tab"]()
with t3:
    rw["family_wizard"]()
if "fact_policy" in (ss.get("rw_extra") or {}) and fus is not None:
    diff = rb.diff_fact_policy(vs.live_bundle().get("fact_policy") or {}, ss["rw_extra"]["fact_policy"], names)
    if diff:
        st.caption(":material/edit_note: In der Arbeitskopie: " + "; ".join(diff))
