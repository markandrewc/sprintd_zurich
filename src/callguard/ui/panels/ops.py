"""Call-detail panels of the operations features: "Weitergeleitet an" (routing), "Rückmeldung" (feedback
buttons), "Personen & Firmen" (entities) and "Herkunft" (provenance + audit trail of the call).

Each ``render(result, session)`` gets the CallResult with the *live* decision (sidebar knobs) and the
AppState. Registered in ``callguard/ui/panels/__init__.py``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from callguard import audit
from callguard import feedback as fb
from callguard.types import CallResult

_ANALYSIS: dict[tuple, Any] = {}


def notifier(session: Any):
    from callguard.sinks.notify import Notifier

    key = ("notifier", id(session.engine))
    if key not in _ANALYSIS:
        _ANALYSIS[key] = Notifier(session.ctx)
    return _ANALYSIS[key]


def live_analysis(session: Any) -> dict[str, Any] | None:
    """Cross-call patterns under the live decisions; memoized per result set + knobs."""
    from callguard import patterns as pt

    s = session.settings
    key = ("analysis", session.loaded.signature, s.threshold, s.review_band, s.max_uncertainty,
           tuple(sorted(s.weights.items())), tuple(s.families_on))
    if key not in _ANALYSIS:
        if len(_ANALYSIS) > 64:  # knob changes create new keys; keep the memo small
            _ANALYSIS.clear()
        n = notifier(session)
        try:
            summaries = [pt.summarize(r, n.directory, decision=session.decided[cid].decision)
                         for cid, r in session.loaded.results.items() if cid in session.decided]
            _ANALYSIS[key] = pt.analyze(pt.one_per_dialogue(summaries), directory=n.directory)
        except Exception as e:  # patterns are a hint; never break the detail page
            st.caption(f"Muster nicht verfügbar: {e}")
            _ANALYSIS[key] = None
    return _ANALYSIS[key]


def _people(rows: list[dict[str, Any]]) -> str:
    return "; ".join(f"**{r['name']}**" + (f" <{r['email']}>" if r.get("email") else "")
                     + (f" — {', '.join(r['why'])}" if r.get("why") else "") for r in rows)


def routed_to(result: CallResult, session: Any) -> None:
    from dataclasses import asdict

    from callguard.sinks.notify import read_outbox

    n = notifier(session)
    analysis = live_analysis(session)
    r, msg = n.message(result, result.decision, analysis)
    if msg is None:
        st.caption(f"Label **{r.label}** wird nicht weitergeleitet (config/routing.yaml `labels`).")
    else:
        st.markdown("An: " + _people([asdict(x) for x in r.to]))
        if r.cc:
            st.markdown("Cc: " + _people([asdict(x) for x in r.cc]))
        if r.patterns:
            st.markdown(f"Muster: {', '.join(r.patterns)}")
        sent = read_outbox(session.runs_dir, result.call_id)
        if any(m.get("key") == msg["key"] for m in sent):
            st.caption(":material/mark_email_read: Diese Meldung liegt bereits in der Outbox.")
        elif st.button("Jetzt melden", key=f"cg_route_send_{result.call_id}", icon=":material/send:"):
            status = n.send(msg)
            st.toast(f"Outbox: {status.get('outbox', '-')}")
        with st.popover("Nachricht ansehen", icon=":material/mail:"):
            st.markdown(f"**{msg['subject']}**")
            st.code(msg["body"], language=None, wrap_lines=True)
    if r.advisor:
        st.caption(f"Beratung: {r.advisor.get('name')}" + (f" ({r.advisor.get('unit')})" if r.advisor.get("unit") else ""))


def feedback(result: CallResult, session: Any) -> None:
    cid = result.call_id
    d = result.decision
    st.caption(f"Ihre Einschätzung zu diesem Anruf (angezeigt: **{d.label}** bei Schwelle {d.threshold:.2f}). "
               "Sie fliesst in die Vorschläge auf der Seite *Feedback & Tuning* ein.")
    opts = ["ganzer Anruf", *[f"Passage {i + 1}: {p.family_label or p.family}" for i, p in enumerate(d.passages)]]
    target = st.selectbox("Betrifft", opts, key=f"cg_fb_target_{cid}")
    comment = st.text_input("Kommentar (optional)", key=f"cg_fb_comment_{cid}")
    pidx = None if target == opts[0] else opts.index(target) - 1
    verdicts = ["confirmed", "false_alarm", "should_review"] if d.label != "no_alert" else ["confirmed", "missed", "should_review"]
    if d.label == "review":
        verdicts.append("not_review")
    cols = st.columns(len(verdicts))
    for col, v in zip(cols, verdicts):
        if col.button(fb.VERDICT_DE[v], key=f"cg_fb_{v}_{cid}", width="stretch"):
            fam = d.passages[pidx].family if pidx is not None else d.top_family
            fb.add(session.runs_dir, fb.FeedbackItem(call_id=cid, verdict=v, family=fam, passage_index=pidx,
                                                     comment=comment, label_seen=d.label,
                                                     threshold_seen=session.settings.threshold))
            st.toast(f"Rückmeldung gespeichert: {fb.VERDICT_DE[v]}", icon=":material/check:")
    past = [i for i in fb.load(session.runs_dir) if i.call_id == cid]
    for i in past[-5:]:
        st.caption(f"{i.ts} · {i.user}: {fb.VERDICT_DE.get(i.verdict, i.verdict)}"
                   + (f" (Passage {i.passage_index + 1})" if i.passage_index is not None else "")
                   + (f" — {i.comment}" if i.comment else ""))


def entities(result: CallResult, session: Any) -> None:
    from callguard.checks.entities import entities_of

    n = notifier(session)
    ent = entities_of(result, n.directory)
    adv, cus = ent.get("advisor") or {}, ent.get("customer") or {}
    c1, c2 = st.columns(2)
    c1.markdown(f"**Beratung**  \n{adv.get('name') or '–'}" + (f" ({adv['id']})" if adv.get("id") else "")
                + (f"  \n:gray[Quelle: {adv.get('source')}]" if adv else ""))
    c2.markdown(f"**Kund:in**  \n{cus.get('name') or '–'}" + (f" ({cus['id']})" if cus.get("id") else "")
                + (f"  \n:gray[Quelle: {cus.get('source')}]" if cus else ""))
    comps = ", ".join(c["name"] for c in ent.get("companies") or [])
    st.markdown(f"**Firmen / Titel:** {comps or '–'}")
    if ent.get("third_parties"):
        st.markdown(f"**Dritte:** {', '.join(ent['third_parties'])}")
    analysis = live_analysis(session)
    from callguard.routing import call_patterns

    kinds = call_patterns(result.call_id, ent, analysis)
    for f in (analysis or {}).get("flags") or []:
        if f["kind"] in kinds and (result.call_id in f.get("calls", []) or f.get("subject") in
                                   {ent.get("advisor_key"), ent.get("customer_key"), *ent.get("company_keys", [])}):
            st.warning(f["reason"], icon=":material/hub:")
    if "patterns" in session.pages:
        st.page_link(session.pages["patterns"], label="Alle Muster", icon=":material/hub:")


def provenance(result: CallResult, session: Any) -> None:
    prov = result.meta.get("provenance") or {}
    if not prov:
        st.caption("Kein Herkunftsnachweis gespeichert (Ergebnis älter als v2).")
    else:
        tun = prov.get("tuning") or {}
        rows = {"Erstellt": prov.get("created_at"), "Profil": prov.get("config_name"),
                "Konfigurations-Hash": prov.get("config_hash"), "Code-Version": prov.get("code_version"),
                "Tuning-Overlay": f"{tun.get('hash')} ({', '.join(f'{k}={v}' for k, v in (tun.get('applied') or {}).items())})"
                if tun else "keins",
                "Primäre Ansicht": prov.get("primary_view")}
        st.table({k: [str(v)] for k, v in rows.items()})
        st.json({k: prov.get(k) for k in ("views", "checks", "fusion") if prov.get(k)}, expanded=False)
    events = audit.read_events(session.runs_dir, call_id=result.call_id, limit=20)
    if events:
        st.markdown("**Audit-Spur dieses Anrufs**")
        st.dataframe([{"Zeit": e.get("ts"), "Art": e.get("kind"), "Wer": e.get("user"),
                       "Detail": ", ".join(f"{k}={e[k]}" for k in ("label", "verdict", "to") if k in e)}
                      for e in reversed(events)], hide_index=True)
