"""Call-detail panel "Offene Fakten" (research/ideas_round3.md S6): the open fact of a review becomes a
question the officer answers with Ja / Nein / Weiss nicht.

The answer replaces the model's value in memory only (the stored result.json stays as it is), the policy
table is re-read with the facts check's own rule evaluator (``callguard.ui.fact_answers``, no LLM) and the
call is re-fused with the live sidebar knobs. Every answer is an audit event ``fact_answer`` (user
"officer", fact id, answer, labels before / after, policy-table hash). Registered in
``callguard/ui/panels/__init__.py``.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from callguard import audit
from callguard.types import CallResult
from callguard.ui import fact_answers as fa
from callguard.ui import render as ui

USER = "officer"


def _state_key(result: CallResult, session: Any) -> str:
    return f"cg_open_facts_{session.runs_dir}_{result.call_id}"


def _answers(result: CallResult, session: Any) -> dict[str, dict[str, str]]:
    return st.session_state.setdefault(_state_key(result, session), {})


def _redecide(result: CallResult, session: Any, fams: list[fa.OpenFamily], answers: dict[str, dict[str, str]],
              options: dict) -> Any:
    params = {f.check: fa.check_params(session.engine, f.check) for f in fams}
    mod = fa.override_result(result, fams, answers, params, options)
    families = session.families if session.all_families else None
    return session.engine.decide(mod, session.settings.overrides(), families), params


def _on_answer(result: CallResult, session: Any, fam: fa.OpenFamily, fact: str, answer: str) -> None:
    answers = _answers(result, session)
    answers.setdefault(fam.family, {})[fact] = answer
    if session.read_only:
        return
    options = fa.load_options()
    fams = fa.open_families(result)
    try:
        decision, params = _redecide(result, session, fams, answers, options)
        call_after = decision.label
    except Exception as e:  # the audit entry must not depend on the fusion
        call_after, params = f"error: {type(e).__name__}", {}
    fd, _, _ = fa.redecide_family(fam, answers[fam.family], params.get(fam.check), options)
    conf = options.get(fam.family, {}).get(fact, {}).get(answer)
    meta = (result.checks[fam.check].meta or {}).get("policy_table") or {}
    audit.log_event(session.runs_dir, "fact_answer", user=USER, call_id=result.call_id, check=fam.check,
                    family=fam.family, fact=fact, answer=answer, also=(conf.also if conf else {}),
                    model_value=fam.values.get(fact), model_p=fam.probs.get(fact),
                    family_label_before=fam.label, family_label=fd.label, rule=fd.rule.id if fd.rule else None,
                    label_before=result.decision.label, label=call_after,
                    threshold=session.settings.threshold, policy_table=meta.get("path"),
                    policy_table_hash=meta.get("hash"))


def _on_reset(result: CallResult, session: Any) -> None:
    st.session_state[_state_key(result, session)] = {}
    if not session.read_only:
        audit.log_event(session.runs_dir, "fact_answer_reset", user=USER, call_id=result.call_id)


def _probs(p: dict[str, float]) -> str:
    return f"ja {p.get('yes', 0):.2f} · nein {p.get('no', 0):.2f} · unklar {p.get('unclear', 0):.2f}"


def render(result: CallResult, session: Any) -> None:
    fams = fa.open_families(result)
    if not fams:
        st.caption("Keine offenen Fakten in diesem Anruf.")
        return
    options = fa.load_options()
    answers = _answers(result, session)
    st.caption("Das Modell konnte diese Fakten nicht klären. Ihre Antwort ersetzt den Wert des Modells, die "
               "Regeln der Policy-Tabelle werden neu gelesen (kein LLM). Das gespeicherte Ergebnis bleibt "
               "unverändert; die Antwort wird im Audit-Protokoll festgehalten.")
    for fam in fams:
        ans = answers.get(fam.family) or {}
        st.markdown(f"**{ui.esc(session.family_label(fam.family))}** · Modell: {ui.label_md(fam.label)}"
                    + (f" · Regel `{fam.rule_id}`" if fam.rule_id else ""))
        for fid in fam.facts:
            fact = fam.table.fact(fid)
            value = fam.values.get(fid, "unclear")
            st.markdown(f":material/help: **Offen: {ui.esc(fact.label)}**  \n{ui.esc(fact.question('de'))}")
            st.caption(f"Modell: {fa.VALUE_DE.get(value, value)} ({_probs(fam.probs.get(fid) or {})})")
            opts = fa.options_for(fam.family, fid, options)
            for col, opt in zip(st.columns(len(opts)), opts):
                col.button(opt.label, key=f"cg_of_{result.call_id}_{fam.family}_{fid}_{opt.answer}",
                           type="primary" if ans.get(fid) == opt.answer else "secondary", width="stretch",
                           on_click=_on_answer, args=(result, session, fam, fid, opt.answer))
        if ans:
            fd, _, _ = fa.redecide_family(fam, ans, fa.check_params(session.engine, fam.check), options)
            rule = fd.rule
            text = (f"Mit Ihren Antworten: {ui.label_md(fd.label)} · Regel `{rule.id if rule else '–'}`"
                    + (f": {ui.esc(rule.text)}" if rule and rule.text else ""))
            {"alarm": st.error, "review": st.warning}.get(fd.label, st.success)(text)
    if any(answers.get(f.family) for f in fams):
        try:
            decision, _ = _redecide(result, session, fams, answers, options)
            st.markdown(f"**Anruf gesamt:** {ui.label_md(decision.label)} · Score {decision.score:.2f} bei "
                        f"Schwelle {decision.threshold:.2f} (vorher {ui.label_md(result.decision.label)}, "
                        f"Score {result.decision.score:.2f})")
        except Exception as e:
            st.caption(f"Neu-Fusion nicht möglich ({type(e).__name__}: {e}); gezeigt ist nur das Regel-Ergebnis.")
        st.button("Zurücksetzen", key=f"cg_of_reset_{result.call_id}", icon=":material/restart_alt:",
                  on_click=_on_reset, args=(result, session), help="Zurück zu den Werten des Modells.")
    if session.read_only:
        st.caption("Experiment-Variante (nur lesen): Antworten werden nicht protokolliert.")
