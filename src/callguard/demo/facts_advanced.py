"""Einstellungen › Fakten › «Erweitert: KI-Leser & Bänder»: how the two AI readers' answers become ja / nein / unklar
(combination, per-reader rule and band), per fact both readers' p(ja) over all calls (strip, band shaded), a per-fact
exception and the calls where the readers disagree. Trying out is instant and session-only; a new default goes to
the four-eyes proposals («Als neue Voreinstellung vorschlagen»)."""

from __future__ import annotations

from typing import Any

import streamlit as st

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard.demo import facts_ui as fu
from callguard.policy_versions import FourEyesError
from callguard.ui import render as ui


def _flash(msg: str) -> None:
    st.session_state.setdefault("dm_set_messages", []).append(msg)


def _set_comb(app: Any) -> None:
    fu.set_try(fu.try_policy(app).with_combination(st.session_state["dm_fk_comb"]))


def _set_band(app: Any, i: int, key: str) -> None:
    lo, hi = st.session_state[key]
    fu.set_try(fu.try_policy(app).with_reader(i, mode="band", lo=float(lo), hi=float(hi)))


def _set_mode(app: Any, i: int, key: str) -> None:
    p = fu.try_policy(app)
    fu.set_try(p.with_reader(i, mode="band" if st.session_state[key] == "band" else "three_way"))


def _set_override(app: Any, fam: str, fid: str, which: str) -> None:
    ss = st.session_state
    p = fu.try_policy(app)
    if which == "band":
        lo, hi = ss[f"dm_fo_band_{fam}_{fid}"]
        p = p.with_override(fam, fid, reader=p.b.id, band=[float(lo), float(hi)])
    elif which == "comb":
        c = ss[f"dm_fo_comb_{fam}_{fid}"]
        ov = p.overrides.get(f"{fam}.{fid}")
        if c != "global":
            p = p.with_override(fam, fid, combination=c)
        elif ov is not None and ov.readers:  # keep the band, drop the combination
            p = fpol.FactPolicy(p.readers, p.combination, {**p.overrides, f"{fam}.{fid}": fpol.FactOverride(
                readers=ov.readers)}, p.source)
        else:
            p = p.with_override(fam, fid, clear=True)
    else:
        p = p.with_override(fam, fid, clear=True)
    fu.set_try(p)


def _propose(app: Any, pol: fpol.FactPolicy, names: dict[str, str]) -> None:
    try:
        v = fu.store(app).save_draft({"fact_policy": pol.as_dict()}, st.session_state.get("dm_user", ""),
                                     comment="Neue Voreinstellung der KI-Leser", family_names=names)
    except (FourEyesError, fpol.FactPolicyError, ValueError) as e:
        st.session_state["dm_fk_error"] = str(e)
        return
    fu.set_try(None)
    _flash(f"Neue Voreinstellung vorgeschlagen (Version {v.n}); eine zweite Person gibt sie oben frei.")


def readers_section(app: Any, names: dict[str, str], doc: dict[str, Any]) -> None:
    ss = st.session_state
    base = fu.session_policy(app)
    pol = fu.try_policy(app)
    trying = pol.key() != base.key()
    if trying:
        st.markdown(":orange-badge[:material/science: Sie probieren gerade aus — nur für Sie sichtbar]")
    ss["dm_fk_comb"] = pol.combination
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.segmented_control("Wie die zwei Leser zusammen entscheiden", list(fpol.COMBINATIONS), key="dm_fk_comb",
                             required=True, format_func=lambda m: pol.combination_de(m), on_change=_set_comb,
                             args=(app,))
        for m in fpol.COMBINATIONS:
            mark = "**" if m == pol.combination else ""
            note = fu.knob_text("combination", m)
            st.markdown(f"{mark}{pol.combination_de(m)}{mark}  \n:small[{fpol.combination_help(m, pol.a.label, pol.b.label)}"
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
                                 on_change=_set_mode, args=(app, i, mkey), label_visibility="collapsed")
            if r.mode == "band":
                c2.slider("unklar zwischen", 0.0, 1.0, step=0.05, key=bkey, on_change=_set_band, args=(app, i, bkey))
            else:
                c2.caption(f"ja wenn p(ja) ≥ {r.decide_at:.2f}, nein wenn p(nein) ≥ {r.decide_at:.2f}, sonst unklar")
    line, changed = fu.effect_md(fu.outcomes(app, base, doc), fu.outcomes(app, pol, doc))
    with st.container(border=True):
        st.markdown(f":material/bolt: **Wirkung gegenüber Ihrer jetzigen Einstellung:** {line}")
        if changed:
            st.markdown(" · ".join(f"{fu.call_link(c)} {fu.LABEL_DE[a]} → **{fu.LABEL_DE[b]}**" for c, a, b in changed))
        c1, c2 = st.columns(2)
        c1.button("Als neue Voreinstellung vorschlagen", icon=":material/how_to_reg:", disabled=not trying,
                  on_click=_propose, args=(app, pol, names), width="stretch", key="dm_fk_propose",
                  help="Fakten-Einstellungen ändern braucht die Freigabe durch eine zweite Person.")
        c2.button("Zurück", icon=":material/undo:", disabled=not trying, on_click=fu.set_try, args=(None,),
                  width="stretch", key="dm_fk_reset")


def fact_card(app: Any, pol: fpol.FactPolicy, fam: str, f: dict[str, Any], answers: dict, outs: dict) -> None:
    ss = st.session_state
    fid = str(f["id"])
    ra, rb_ = pol.reader(0, fam, fid), pol.reader(1, fam, fid)
    with st.container(border=True):
        st.markdown(f"**{ui.esc(str(f.get('label') or fid))}**"
                    + (" · :violet-badge[eigene Einstellung]" if pol.has_override(fam, fid) else "")
                    + f"  \n:small[{ra.label}: {ra.describe()} · {rb_.label}: {rb_.describe()} · zusammen: "
                      f"{pol.combination_de(pol.combination_for(fam, fid))}]")
        ans = answers.get((fam, fid)) or []
        if not ans:
            st.caption(":material/sync_problem: Noch keine gespeicherten Antworten für diese Frage.")
            return
        st.altair_chart(fu.strip_chart(ans, pol, fam, fid), width="stretch")
        cnt = fpol.value_counts(ans, pol, fam, fid)
        fmt = lambda d: " · ".join(f"{fpol.VALUE_DE[v]} {d[v]}" for v in fpol.VALUES)  # noqa: E731
        st.caption(f"{ra.label}: {fmt(cnt['a'])} | {rb_.label}: {fmt(cnt['b'])} | **zusammen: {fmt(cnt['combined'])}**")
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
                               "Anruf jetzt": fu.LABEL_DE[outs[d.fact].label] if d.fact in outs else ""}
                              for d in dis], hide_index=True,
                             column_config={"Anruf": st.column_config.LinkColumn("Anruf", display_text=r"call=(.*)")})
        with c2.expander("Eigene Einstellung für diesen Fakt", icon=":material/tune:"):
            bkey, ckey = f"dm_fo_band_{fam}_{fid}", f"dm_fo_comb_{fam}_{fid}"
            ss[bkey] = (float(rb_.lo), float(rb_.hi))
            ov = pol.overrides.get(f"{fam}.{fid}")
            ss[ckey] = (ov.combination if ov and ov.combination else "global")
            st.slider(f"{rb_.label}: unklar zwischen", 0.0, 1.0, step=0.05, key=bkey, on_change=_set_override,
                      args=(app, fam, fid, "band"))
            st.selectbox("Kombination", ["global", *fpol.COMBINATIONS], key=ckey, on_change=_set_override,
                         args=(app, fam, fid, "comb"),
                         format_func=lambda m: f"wie allgemein ({pol.combination_de()})" if m == "global"
                         else pol.combination_de(m))
            if pol.has_override(fam, fid):
                st.button("Ausnahme entfernen", key=f"dm_fo_clear_{fam}_{fid}", on_click=_set_override,
                          args=(app, fam, fid, "clear"))


def render(app: Any, doc: dict[str, Any], names: dict[str, str]) -> None:
    st.caption("Wie aus den Wahrscheinlichkeiten der zwei KI-Leser ja / nein / unklar wird. Ausprobieren wirkt sofort "
               "und nur für Sie; eine neue Voreinstellung braucht die Freigabe durch eine zweite Person.")
    readers_section(app, names, doc)
    pol = fu.try_policy(app)
    answers = fpol.fact_answers(app.loaded.results, pol)
    outs = fu.outcomes(app, pol, doc)
    fams = list((doc.get("families") or {}).keys())
    for tab, fam in zip(st.tabs([names.get(f, f) for f in fams]), fams):
        with tab:
            for f in pe.family_doc(doc, fam)["facts"]:
                fact_card(app, pol, fam, f, answers, outs)
