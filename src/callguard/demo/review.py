"""The officer's review on «Anruf prüfen»: verdict, agree / disagree with the system and WHY as reason codes
(modelled on the teammate's «Anruf-Prüfung» dashboard, richer: per decisive fact, per passage, plus
context / transcript / rule / category / missing-information codes). Saved through the learning feedback
store (:func:`callguard.feedback.items_from_review`: schema 2, provenance, audit log); the confirmation
names the data point and its label counts. After a confirmed violation: the routing target and
«An Outcept melden».

The form is a fragment: ticking boxes reruns only the form, never the audio player.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

from callguard import audit
from callguard import feedback as fb
from callguard.demo import card as cd
from callguard.demo import common as cm
from callguard.demo import state as ds
from callguard.learning import hygiene as hy
from callguard.types import CallResult, fmt_ts
from callguard.ui import render as ui

FLAG_CODES = ("context_harmless", "transcript_error", "rule_too_strict", "rule_too_lax", "missing_info")
FLAG_HELP = {
    "context_harmless": "Die Stelle stimmt, aber der Zusammenhang macht sie harmlos (z.B. öffentlich, Beispiel, Warnung).",
    "transcript_error": "Die Spracherkennung hat sich verhört; das Transkript gibt das Gespräch falsch wieder.",
    "rule_too_strict": "Die Regel schlägt in solchen Fällen zu früh an.",
    "rule_too_lax": "Die Regel müsste hier anschlagen, tut es aber nicht.",
    "missing_info": "Das Gespräch enthält nicht genug Information für ein sicheres Urteil.",
}
AGREE_DE = {"yes": "Ja, stimmt", "no": "Nein"}
VALUE_ICON = {"yes": ":material/check_circle:", "no": ":material/cancel:", "unclear": ":material/help:"}
FLIP = {"yes": "no", "no": "yes"}


def fact_lines(rows: Sequence[cd.FactRow]) -> str:
    """Markdown list: «✓ Eigener Handelswunsch geäussert: **ja** (0.98)»."""
    out = []
    for f in rows:
        conf = f" ({f.confidence:.2f})" if f.confidence is not None else ""
        out.append(f"{VALUE_ICON.get(f.value, '')} {ui.esc(f.label)}: **{cd.VALUE_DE.get(f.value, f.value)}**{conf}")
    return "  \n".join(out)


def collect_reasons(card: cd.Card, *, facts: Mapping[str, str] | None = None,
                    passages: Mapping[int, str] | None = None, flags: Sequence[str] = (),
                    other_families: Sequence[str] = (), other_text: str = "") -> list[fb.Reason]:
    """The ticked boxes as reason codes. ``facts``: fact id -> the value the officer says is right (only facts
    of the card; unchanged values are ignored); ``passages``: index -> passage_applies / passage_not_applies;
    ``flags``: codes of :data:`FLAG_CODES`; ``other_families``: «Andere Kategorie»."""
    by_id = {f.fact: f for f in card.facts}
    out: list[fb.Reason] = []
    for fid, after in (facts or {}).items():
        f = by_id.get(fid)
        if f is None or after not in fb.FACT_ANSWERS or after == f.value:
            continue
        out.append(fb.Reason(code="fact_wrong", family=card.family, fact=fid, before=f.value, after=after,
                             text=f.label))
    for idx, code in sorted((passages or {}).items()):
        if code in ("passage_applies", "passage_not_applies"):
            out.append(fb.Reason(code=code, passage_index=int(idx), family=card.family))
    for code in flags:
        if code in FLAG_CODES:
            out.append(fb.Reason(code=code, rule=card.rule_id if code.startswith("rule_") else None,
                                 family=card.family if code.startswith("rule_") else None))
    for fam in other_families:
        out.append(fb.Reason(code="other_family", family=fam, text=other_text))
    return out


def confirmation(n: int, items: Sequence[fb.FeedbackItem], use: str) -> str:
    """«Datenpunkt #12 für Training gespeichert (Fakten-Labels: 2, Passagen-Labels: 1)»; case calls are honest
    about being evaluation-only."""
    k = sum(1 for i in items if i.target == "fact")
    m = sum(1 for i in items if i.target == "passage")
    counts = f"(Fakten-Labels: {k}, Passagen-Labels: {m})"
    if use in hy.TRAINABLE:
        return f"Datenpunkt #{n} für Training gespeichert {counts}"
    return f"Datenpunkt #{n} gespeichert {counts} · Verwendung: {hy.USE_DE.get(use, use)}"


def _use(call_id: str) -> str:
    return hy.use_of(call_id, hy.splits_or_none())


def _k(cid: str, name: str) -> str:
    ver = st.session_state.get(f"dm_rv_ver_{cid}", 0)
    return f"dm_rv_{name}_{cid}_{ver}"


@st.fragment
def form(app: Any, live: CallResult, card: cd.Card, call_id: str) -> None:
    ss = st.session_state
    st.subheader("Ihre Beurteilung", anchor=False)
    saved = ss.get("dm_saved")
    if saved and saved.get("call_id") == call_id:
        st.success(saved["text"], icon=":material/task_alt:")
        if saved.get("verdict") == "violation":
            _after_violation(app, live, call_id)
    st.caption("Ihr Urteil und Ihre Gründe werden ein Datenpunkt zum Lernen, mit Herkunft (Modell, Regelwerk, "
               "Transkript) und im Audit-Log. Trainiert wird damit nichts automatisch.")

    verdict = st.segmented_control("Liegt ein Verstoss vor?", list(fb.CALL_VERDICTS), format_func=fb.VERDICT_DE.get,
                                   key=_k(call_id, "verdict"))
    agree = st.segmented_control(f"Stimmt die Einschätzung des Systems («{card.label_de}»)?", list(AGREE_DE),
                                 format_func=AGREE_DE.get, key=_k(call_id, "agree"))

    st.markdown("**Warum?** · alles Zutreffende ankreuzen")
    fact_choice: dict[str, str] = {}
    decisive = [f for f in card.facts if f.decisive] or card.facts[:3]
    for f in decisive:
        if f.value in FLIP:
            after = FLIP[f.value]
            if st.checkbox(f"Fakt falsch erkannt: {f.label} ({cd.VALUE_DE[f.value]} → {cd.VALUE_DE[after]})",
                           key=_k(call_id, f"fact_{f.fact}")):
                fact_choice[f.fact] = after
        else:
            pick = st.pills(f"Fakt war unklar: {f.label} – im Gespräch ist es …", ["yes", "no"],
                            format_func=cd.VALUE_DE.get, key=_k(call_id, f"fact_{f.fact}"))
            if pick:
                fact_choice[f.fact] = pick
    passage_choice: dict[int, str] = {}
    for i, p in enumerate(live.decision.passages):
        v = st.segmented_control(
            f"Passage {i + 1} ({fmt_ts(p.start)}) · {(p.family_label or p.family).split(' (')[0]}",
            ["passage_applies", "passage_not_applies"], format_func=lambda c: fb.REASON_DE[c].replace("Passage ", "").capitalize(),
            key=_k(call_id, f"passage_{i}"))
        if v:
            passage_choice[i] = v
    c1, c2 = st.columns(2)
    flags = []
    for j, code in enumerate(FLAG_CODES):
        if (c1 if j % 2 == 0 else c2).checkbox(fb.REASON_DE[code], key=_k(call_id, code), help=FLAG_HELP[code]):
            flags.append(code)
    options = [f.id for f in app.all_families if f.id != card.family]
    other = st.multiselect("Andere Kategorie", options, format_func=app.family_label, placeholder="keine",
                           key=_k(call_id, "other"),
                           help="Es liegt ein Verstoss einer anderen Art vor, als das System zeigt.")
    comment = st.text_area("Kommentar (optional)", key=_k(call_id, "comment"), height=80)
    ss.setdefault(ds.NAME_KEY, audit.current_user())
    ss.setdefault("dm_name", ss[ds.NAME_KEY])
    name = st.text_input("Ihr Name", key="dm_name", help="Wird mit der Beurteilung gespeichert (Audit-Log).")
    ss[ds.NAME_KEY] = name
    if st.button("Beurteilung speichern", type="primary", icon=":material/save:", key=_k(call_id, "save"),
                 width="stretch"):
        name = " ".join(str(name or "").split())
        if not verdict:
            st.error("Bitte zuerst ein Urteil wählen: Verstoss bestätigt, kein Verstoss oder unklar.",
                     icon=":material/rule:")
            return
        if not name:
            st.error("Bitte Ihren Namen angeben.", icon=":material/badge:")
            return
        reasons = collect_reasons(card, facts=fact_choice, passages=passage_choice, flags=flags,
                                  other_families=other)
        try:
            items = fb.items_from_review(live, user=name, verdict=verdict,
                                         agrees=None if agree is None else agree == "yes", reasons=reasons,
                                         comment=comment or "", threshold=app.settings.threshold)
            fb.add_many(app.runs_dir, items)
        except Exception as e:
            st.error(f"Speichern fehlgeschlagen: {type(e).__name__}: {e}", icon=":material/error:")
            return
        n = fb.batch_count(fb.load(app.runs_dir))
        ss["dm_saved"] = {"call_id": call_id, "text": confirmation(n, items, _use(call_id)), "verdict": verdict}
        ss[f"dm_rv_ver_{call_id}"] = ss.get(f"dm_rv_ver_{call_id}", 0) + 1  # a fresh, empty form
        st.rerun(scope="app")  # the case status (offen -> bearbeitet) lives outside the fragment

    past = [i for i in ds.feedback_items(app) if i.call_id == call_id and i.target == "call"]
    if past:
        with st.expander(f"Bisherige Beurteilungen ({len(past)})", icon=":material/history:"):
            for i in reversed(past[-10:]):
                why = "; ".join(r.describe() for r in i.reasons) or "–"
                st.markdown(f"**{ui.esc(i.user)}** · {i.ts[:16].replace('T', ' ')} · "
                            f"{fb.VERDICT_DE.get(i.verdict, i.verdict)}"
                            + ("" if i.agrees is None else (" · stimmt dem System zu" if i.agrees
                                                            else " · widerspricht dem System"))
                            + f"  \n:small[{ui.esc(why)}]" + (f"  \n:small[«{ui.esc(i.comment)}»]" if i.comment else ""))


def _after_violation(app: Any, live: CallResult, call_id: str) -> None:
    teams = cm.routed_to(app, live)
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.markdown(f":material/alt_route: Geht an: **{ui.esc(', '.join(teams) or 'Compliance Desk')}**")
    if c2.button("An Outcept melden", icon=":material/send:", key=f"dm_outcept_{call_id}", width="stretch"):
        bodies = cm.outcept_bodies(app, live)
        if not bodies:
            st.info("Für diesen Anruf gibt es nichts zu melden (Kein Alarm).", icon=":material/info:")
            return
        sent, err = cm.send_outcept(bodies)
        if err:
            st.warning(f"{err}. Die Meldung ist nicht verloren: später erneut senden oder "
                       f"`uv run callguard triggers` verwenden.", icon=":material/cloud_off:")
        else:
            st.success(f"{sent} Meldung{'en' if sent != 1 else ''} an Outcept gesendet (mit Link zurück zur Stelle "
                       "im Gespräch).", icon=":material/send:")
