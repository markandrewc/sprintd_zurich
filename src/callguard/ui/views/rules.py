"""Regelwerk: the officer reads and changes the policy table (``config/policy_table.yaml``) in plain language.

Tabs per family show every rule as a card ("WENN «Fakt» = ja UND … → ALARM", explanation, legal basis,
on/off, order, how often it decided among the processed calls), with a condition builder (dropdowns, no
syntax) and the fact questions. "Neue Regel in eigenen Worten" drafts a rule with the configured LLM
(``callguard.rule_drafter``, never active by itself). "Vorschau & Speichern" re-decides the stored calls
with the working copy (``callguard.ui.whatif``: rule changes instantly from the stored fact answers, new
questions through the LLM) and saves a draft version. "Versionen & Freigabe": four-eyes approval (the
approver is not the author), rollback, plain-German diffs (``callguard.policy_versions``). Only approval
writes the active file, so the pipeline only ever runs approved versions. Every step is in the audit log.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import streamlit as st

from callguard import audit
from callguard import policy_edit as pe
from callguard import rulebook as rb
from callguard import rule_drafter as rd
from callguard.cache import stable_hash
from callguard.checks.facts import DEFAULT_TABLE, FACT_ROLES, RULE_LABELS, PolicyTableError, discretize
from callguard.config import ROOT
from callguard.data import dialogue_of
from callguard.policy_versions import STATUS_DE, FourEyesError, VersionStore
from callguard.ui import backend as be
from callguard.ui import fact_answers as fa
from callguard.ui import render as ui
from callguard.ui import whatif as wi
from callguard.ui.session import current_app, ground_truth, reload_everything

app = current_app()
ss = st.session_state

# --------------------------------------------------------------------------------------------
# where the table lives, which check reads it
# --------------------------------------------------------------------------------------------


def _facts_check() -> Any:
    pipeline = app.engine.pipeline
    return next((c for c in (getattr(pipeline, "checks", None) or []) if c.plugin_type == "facts"), None)


check = _facts_check()
spec = next((c for c in app.cfg.checks if c.get("type") == "facts"), {})
table_rel = str(getattr(check, "policy_table", None) or spec.get("policy_table") or DEFAULT_TABLE)
table_path = Path(table_rel) if Path(table_rel).is_absolute() else ROOT / table_rel
lang = str(getattr(check, "question_lang", None) or spec.get("question_lang") or "en")
decide_fact = getattr(check, "_decide", None) or discretize
params = fa.check_params(app.engine, getattr(check, "name", "facts"))
profile = app.cfg.name


def _extra_paths() -> dict[str, Path]:
    """The other files of the rulebook bundle, as this profile reads them."""
    from callguard.routing import DEFAULT_ROUTING

    notify = next((s for s in app.cfg.sinks if s.get("type") == "notify"), {})
    routing = Path(str(notify.get("routing") or DEFAULT_ROUTING))
    out = {"criteria": app.ctx.path("criteria"), "keywords": app.ctx.path("keywords"),
           "routing": routing if routing.is_absolute() else ROOT / routing}
    tuning = app.cfg.paths.tuning
    if tuning:
        out["tuning"] = Path(tuning) if Path(tuning).is_absolute() else ROOT / tuning
    return out


store = VersionStore(table_path, audit_dir=app.runs_dir, extras=_extra_paths())
families_by_id = {f.id: f for f in app.all_families}
CHECK_KIND = {str(c.get("name") or c.get("type")): rb.CHECK_KIND_DE.get(str(c.get("type")), str(c.get("type")))
              for c in app.cfg.checks}

st.title("Regelwerk")
st.caption("Was als Alarm, Prüffall oder unbedenklich gilt: pro **Prüfart** (Art von Fehlverhalten) beantwortet das "
           "Sprachmodell einfache Ja/Nein-Fragen (**Fakten**) zum Gespräch, die **Regeln** machen daraus den "
           "Entscheid; die erste zutreffende Regel entscheidet. Neue Prüfarten, Regeln und Schalter entstehen in einer "
           "Arbeitskopie, werden in der Vorschau an den verarbeiteten Anrufen geprüft, als Entwurf gespeichert und "
           f"gelten erst nach Freigabe durch eine zweite Person. Regeltabelle: `{table_rel}`, Versionen: "
           f"`{store.dir.name}/` (zusammen mit Kriterien, Stichwortliste, Meldewegen und Prüfungs-Schaltern).")

try:
    active_v = store.ensure_initial()
except Exception as e:
    st.error(f"Das aktive Regelwerk ist unlesbar: {type(e).__name__}: {e}")
    st.stop()
active_doc = active_v.doc()
active_table = pe.validate(active_doc)
active_bundle = store.live_bundle()

# --------------------------------------------------------------------------------------------
# working copy (session) + the officer's name
# --------------------------------------------------------------------------------------------

if ss.get("rw_for") != str(table_path) or "rw_doc" not in ss:
    ss.update(rw_for=str(table_path), rw_doc=copy.deepcopy(active_doc), rw_base=active_v.n, rw_probes={},
              rw_extra={k: v for k, v in copy.deepcopy(active_bundle).items() if k != "policy_table"})
ss.setdefault("rw_user", audit.current_user())
ss.setdefault("rw_rid", 0)


def _rid() -> str:
    ss["rw_rid"] += 1
    return f"r{ss['rw_rid']}"


def doc() -> dict[str, Any]:
    return ss["rw_doc"]


def bundle() -> dict[str, dict[str, Any]]:
    return {"policy_table": ss["rw_doc"], **ss["rw_extra"]}


def _flash(msg: str, icon: str = ":material/check_circle:") -> None:
    ss.setdefault("rw_msgs", []).append((msg, icon))


for msg, icon in ss.pop("rw_msgs", []):
    st.toast(msg, icon=icon)


def _set_doc(new: dict[str, Any], msg: str | None = None) -> bool:
    try:
        pe.validate(new)
    except PolicyTableError as e:
        st.error(f"Nicht übernommen: {e}")
        return False
    ss["rw_doc"] = new
    if msg:
        _flash(msg)
    return True


def _set_bundle(new: dict[str, dict[str, Any]], msg: str | None = None) -> bool:
    if not _set_doc(new["policy_table"]):
        return False
    ss["rw_extra"] = {k: v for k, v in new.items() if k != "policy_table"}
    if msg:
        _flash(msg)
    return True


def _discard() -> None:
    live = store.live_bundle()
    ss.update(rw_doc=live["policy_table"], rw_base=store.active().n, rw_probes={}, rw_edit=None,
              rw_extra={k: v for k, v in live.items() if k != "policy_table"})
    _flash("Arbeitskopie verworfen.")


def _family_list(b: dict[str, dict[str, Any]], enabled_only: bool = True) -> list[Any]:
    from callguard.families import families_from_raw

    fams = families_from_raw(b.get("keywords") or {}, (b.get("criteria") or {}).get("families") or {},
                             only=app.cfg.families)
    return [f for f in fams if f.enabled or not enabled_only]


work_families = _family_list(bundle(), enabled_only=False)
fam_names = {**{f.id: be.short_label(f.label) for f in work_families},
             **{f.id: be.short_label(f.label) for f in app.all_families}}
new_family_ids = {f.id for f in work_families} - {f.id for f in _family_list(active_bundle, enabled_only=False)}
changes = rb.diff_bundle(active_bundle, bundle(), fam_names, profile, CHECK_KIND)
c1, c2, c3 = st.columns([3, 2, 1.3])
with c1:
    act = store.active()
    who = (f"freigegeben von **{act.meta.get('approver')}**, verfasst von **{act.author}**" if act.meta.get("approver")
           else f"**{act.meta.get('comment') or act.author}**")
    st.markdown(f":material/verified: Aktiv: **Version {act.n}** · {who} · {str(act.meta.get('approved_at', ''))[:16]}")
    if changes:
        st.markdown(f":material/edit_note: Arbeitskopie: **{len(changes)} Änderung{'en' if len(changes) != 1 else ''}**, "
                    "noch nicht gespeichert → **Vorschau & Speichern**")
    drafts = store.drafts()
    if drafts:
        st.markdown(f":material/pending_actions: {len(drafts)} Entwurf/Entwürfe warten auf Freigabe → "
                    "**Versionen & Freigabe**")
c2.text_input("Ihr Name", key="rw_user", help="Wird als Autor oder Freigeber protokolliert (Audit-Log).")
if changes:
    c3.button("Änderungen verwerfen", icon=":material/undo:", on_click=_discard, width="stretch")
if app.read_only:
    st.info("Angezeigt wird eine Experiment-Variante (nur lesen): die Vorschau rechnet mit diesen Ergebnissen, "
            "Speichern und Freigeben ist nur mit einem Profil-Lauf als Quelle möglich.", icon=":material/lock:")

# --------------------------------------------------------------------------------------------
# preview of the working copy (shared by the cards' statistics and the preview tab)
# --------------------------------------------------------------------------------------------


def _valid_probes(table) -> dict[wi.Key, dict[str, float]]:
    """Probes of this session whose question is still the current wording."""
    out = {}
    for (cid, fam, fid), (question, p) in ss.get("rw_probes", {}).items():
        ft = table.families.get(fam)
        if ft is not None and any(f.id == fid and f.question(lang) == question for f in ft.facts):
            out[(cid, fam, fid)] = p
    return out


def _decide_call(r):
    return app.engine.decide(r, app.settings.overrides(), app.families if app.all_families else None)


@st.cache_data(show_spinner=False)
def _untuned_weights(config: str, sets: tuple[str, ...]) -> dict[str, float]:
    """Check weights of the profile without the tuning overlay (what "wieder einschalten" restores)."""
    from callguard.config import load_config

    try:
        return be.check_weights(load_config(config, [*sets, "paths.tuning="]))
    except Exception:
        return {}


def _draft_overrides() -> dict[str, Any]:
    """The sidebar knobs with the working copy's check switches applied."""
    o = app.settings.overrides()
    weights = dict(o.get("weights") or {})
    off_now, off_draft = rb.checks_off(active_bundle, profile), rb.checks_off(bundle(), profile)
    base = _untuned_weights(app.args.config, tuple(app.args.sets))
    for name in off_draft:
        weights[name] = 0.0
    for name in off_now - off_draft:
        weights[name] = base.get(name, 1.0)
    return {**o, "weights": weights}


def _draft_families() -> list[Any] | None:
    if not app.all_families:
        return None
    on = set(app.settings.families_on)
    return [f for f in _family_list(bundle()) if f.id in on or f.id not in families_by_id]


def _decide_draft(r):
    return app.engine.decide(r, _draft_overrides(), _draft_families())


try:
    work_table = pe.validate(doc())
    work_error = None
except PolicyTableError as e:  # cannot happen through the editor; a hand-loaded draft might
    work_table, work_error = active_table, str(e)
probes = _valid_probes(work_table)
memo_key = stable_hash({"doc": bundle(), "sig": app.loaded.signature, "knobs": app.settings.overrides(),
                        "fams": app.settings.families_on, "probes": sorted(map(str, probes)), "lang": lang})
if ss.get("rw_preview_key") != memo_key:
    ss["rw_preview"] = wi.preview(app.loaded.results, active_table, work_table, _decide_call, params, probes, lang,
                                  decide_fact, decide_after=_decide_draft) if app.engine.can_decide else None
    ss["rw_preview_key"] = memo_key
pv: wi.Preview | None = ss["rw_preview"]
if work_error:
    st.error(f"Die Arbeitskopie ist ungültig: {work_error}")

# --------------------------------------------------------------------------------------------
# condition builder
# --------------------------------------------------------------------------------------------

VALUE_OPTS = list(pe.VALUES)
LABEL_OPTS = list(RULE_LABELS)


def _rows_init(key: str, when: str, facts: set[str]) -> bool:
    """Builder rows for ``when`` into session state; False if the rows cannot express it."""
    if key in ss:
        return ss[key] is not None
    try:
        conds = pe.builder_from_when(when, facts)
    except PolicyTableError:
        conds = None
    ss[key] = None if conds is None else [{"rid": _rid(), **c.__dict__} for c in conds]
    return ss[key] is not None


def _rows_read(key: str) -> list[pe.Cond]:
    out = []
    for i, row in enumerate(ss[key] or []):
        k = f"{key}_{row['rid']}"
        out.append(pe.Cond(fact=ss.get(f"{k}_f", row["fact"]), value=ss.get(f"{k}_v", row["value"]),
                           negate=ss.get(f"{k}_n", "ist nicht" if row["negate"] else "ist") == "ist nicht",
                           join=ss.get(f"{k}_j", row["join"]) if i else "and"))
    return out


def _row_add(key: str, fact: str) -> None:
    ss[key] = [*(ss[key] or []), {"rid": _rid(), "fact": fact, "value": "yes", "negate": False, "join": "and"}]


def _row_del(key: str, rid: str) -> None:
    ss[key] = [r for r in ss[key] if r["rid"] != rid]


def builder(key: str, when: str, labels: dict[str, str]) -> str:
    """Draw the condition builder; returns the condition text it currently describes."""
    facts = list(labels)
    if not _rows_init(key, when, set(facts)):
        st.caption("Diese Bedingung hat Klammern oder NICHT; sie bleibt in der Regelsprache bearbeitbar.")
        return st.text_input("Bedingung (Regelsprache)", value=when, key=f"{key}_raw",
                             help="Fakt = yes / no / unclear, Fakt != yes, verknüpft mit and / or, Klammern erlaubt.")
    rows = ss[key]
    if not rows:
        st.caption("Keine Bedingung: die Regel greift immer (Standardregel am Ende).")
    for i, row in enumerate(rows):
        k = f"{key}_{row['rid']}"
        cols = st.columns([1.1, 4, 1.4, 1.4, 0.5], vertical_alignment="bottom")
        if i == 0:
            cols[0].markdown("**WENN**")
        else:
            cols[0].selectbox("Verknüpfung", ["and", "or"], index=["and", "or"].index(row["join"]), key=f"{k}_j",
                              format_func=pe.JOIN_DE.get, label_visibility="collapsed")
        cols[1].selectbox("Fakt", facts, index=facts.index(row["fact"]) if row["fact"] in facts else 0, key=f"{k}_f",
                          format_func=lambda f: labels.get(f, f), label_visibility="collapsed")
        cols[2].selectbox("ist", ["ist", "ist nicht"], index=int(row["negate"]), key=f"{k}_n",
                          label_visibility="collapsed")
        cols[3].selectbox("Wert", VALUE_OPTS, index=VALUE_OPTS.index(row["value"]), key=f"{k}_v",
                          format_func=pe.VALUE_DE.get, label_visibility="collapsed")
        cols[4].button("", icon=":material/close:", key=f"{k}_x", on_click=_row_del, args=(key, row["rid"]),
                       help="Bedingung entfernen")
    st.button("Bedingung hinzufügen", icon=":material/add:", key=f"{key}_add", on_click=_row_add,
              args=(key, facts[0]), disabled=not facts)
    st.caption("UND bindet stärker als ODER: «A UND B ODER C» heisst «(A und B) oder C».")
    return pe.when_from_builder(_rows_read(key))


def rule_form(key: str, rule: dict[str, Any], labels: dict[str, str]) -> dict[str, Any]:
    """Builder + result + explanation + basis; returns the rule as currently entered."""
    when = builder(f"{key}_rows", str(rule.get("when", "true")), labels)
    c1, c2 = st.columns([1, 3])
    label = c1.selectbox("Ergebnis", LABEL_OPTS, index=LABEL_OPTS.index(rule.get("label", "review")),
                         format_func=pe.LABEL_DE.get, key=f"{key}_label")
    basis = c2.text_input("Rechtsgrundlage (optional)", value=str(rule.get("basis") or ""), key=f"{key}_basis")
    text = st.text_area("Erklärung für die Fachstelle", value=str(rule.get("text") or ""), key=f"{key}_text", height=68)
    out = {**rule, "label": label, "when": when, "text": text, "basis": basis}
    st.markdown(f"**So liest sich die Regel:** {ui.esc(pe.render_rule(out, labels))}")
    return out


# --------------------------------------------------------------------------------------------
# family tab: rule cards + facts
# --------------------------------------------------------------------------------------------

LABEL_COLOR = {"alarm": "red", "review": "orange", "no_alert": "green"}


def _stats(fam: str, rule: dict[str, Any]) -> str:
    if pv is None or not pv.family_calls(fam):
        return "noch keine verarbeiteten Anrufe mit Fakten"
    n = pv.family_calls(fam)
    rid = str(rule.get("id"))
    if not pe.is_enabled(rule):
        k = pv.cond_hits.get(fam, {}).get(rid, 0)
        return f"ausgeschaltet · Bedingung träfe auf {k} von {n} Anrufen zu"
    return f"greift bei **{pv.rule_hits.get(fam, {}).get(rid, 0)} von {n}** Anrufen"


def _move(fam: str, rid: str, delta: int) -> None:
    new = copy.deepcopy(doc())
    if pe.move_rule(new, fam, rid, delta):
        ss["rw_doc"] = new


def _toggle(fam: str, rid: str, key: str) -> None:
    new = copy.deepcopy(doc())
    pe.set_enabled(new, fam, rid, bool(ss[key]))
    ss["rw_doc"] = new


def _delete(fam: str, rid: str) -> None:
    new = copy.deepcopy(doc())
    pe.delete_rule(new, fam, rid)
    ss["rw_doc"] = new
    _flash(f"Regel {rid} aus der Arbeitskopie gelöscht.")


def _edit(target: tuple[str, str] | None) -> None:
    ss["rw_edit"] = target
    for k in [k for k in ss if str(k).startswith("rw_ed_")]:
        del ss[k]


def rule_card(fam: str, i: int, rule: dict[str, Any], n_rules: int, labels: dict[str, str]) -> None:
    rid = str(rule.get("id"))
    on = pe.is_enabled(rule)
    with st.container(border=True):
        left, right = st.columns([5, 2])
        badge = f":{LABEL_COLOR.get(rule.get('label'), 'gray')}-badge[{pe.LABEL_UPPER.get(rule.get('label'), '?')}]"
        left.markdown(f"**{i + 1}.** {badge} {'' if on else ':gray-badge[ausgeschaltet]'}  \n"
                      f"{ui.esc(pe.render_rule(rule, labels))}")
        if rule.get("text"):
            left.markdown(f":material/chat: {ui.esc(str(rule['text']))}")
        basis = rule.get("basis") or pe.family_doc(doc(), fam).get("basis")
        left.caption(f"Regel `{rid}` · {_stats(fam, rule)}"
                     + (f" · Rechtsgrundlage: {ui.esc(str(basis))}" if basis else ""))
        tkey = f"rw_on_{fam}_{rid}_{on}"
        right.toggle("aktiv", value=on, key=tkey, on_change=_toggle, args=(fam, rid, tkey), disabled=app.read_only,
                     help="Ausgeschaltete Regeln bleiben in der Tabelle, entscheiden aber nie.")
        b = right.columns(4)
        b[0].button("", icon=":material/arrow_upward:", key=f"rw_up_{fam}_{rid}", on_click=_move, args=(fam, rid, -1),
                    disabled=i == 0, help="Nach oben (wird früher geprüft)")
        b[1].button("", icon=":material/arrow_downward:", key=f"rw_dn_{fam}_{rid}", on_click=_move,
                    args=(fam, rid, 1), disabled=i == n_rules - 1, help="Nach unten")
        b[2].button("", icon=":material/edit:", key=f"rw_edbtn_{fam}_{rid}", on_click=_edit, args=((fam, rid),),
                    help="Bearbeiten")
        b[3].button("", icon=":material/delete:", key=f"rw_del_{fam}_{rid}", on_click=_delete, args=(fam, rid),
                    help="Löschen (nur in der Arbeitskopie)")
        if ss.get("rw_edit") == (fam, rid):
            new = rule_form(f"rw_ed_{fam}_{rid}", rule, labels)
            c1, c2 = st.columns(2)
            if c1.button("Übernehmen", type="primary", icon=":material/check:", key=f"rw_ok_{fam}_{rid}"):
                cand = copy.deepcopy(doc())
                try:
                    pe.replace_rule(cand, fam, rid, new)
                except PolicyTableError as e:
                    st.error(str(e))
                else:
                    if _set_doc(cand, f"Regel {rid} geändert (Arbeitskopie)."):
                        _edit(None)
                        st.rerun()
            c2.button("Abbrechen", key=f"rw_cancel_{fam}_{rid}", on_click=_edit, args=(None,))


def _translate(src_key: str, dst_key: str) -> None:
    try:
        llm = app.ctx.llm(getattr(check, "llm_name", "default"))
        ss[dst_key] = rd.translate_question(llm, ss.get(src_key, ""))
        _flash("Englische Fassung aus dem Deutschen übernommen (KI-Übersetzung, bitte lesen).")
    except Exception as e:
        _flash(f"Übersetzung nicht möglich ({type(e).__name__}: {str(e)[:120]}); englische Fassung bleibt.",
               ":material/error:")


QUESTION_HELP = ("Umformulieren ändert Entscheide, auch wenn der Sinn gleich bleibt: gemessen mit Qwen2.5-7B auf dem "
                 "Dev-Split AUC 0.87 mit den abgestimmten Fragen, 0.72 mit umformulierten. Deshalb wird jede "
                 "geänderte Frage zuerst in der Vorschau an den verarbeiteten Anrufen geprüft.")


def fact_editor(fam: str, fact: dict[str, Any] | None) -> None:
    """Edit one fact (or create one when ``fact`` is None)."""
    fid = str(fact["id"]) if fact else ""
    k = f"rw_fx_{fam}_{fid or 'new'}"
    ss.setdefault(f"{k}_en", str((fact or {}).get("en") or ""))
    label = st.text_input("Bezeichnung (kurz)", value=str((fact or {}).get("label") or ""), key=f"{k}_label")
    role = st.selectbox("Rolle", list(FACT_ROLES), index=list(FACT_ROLES).index((fact or {}).get("role", "context")),
                        format_func=pe.ROLE_DE.get, key=f"{k}_role")
    de = st.text_area("Frage (Deutsch)", value=str((fact or {}).get("de") or ""), key=f"{k}_de", height=90,
                      help=QUESTION_HELP)
    st.text_area("Frage (Englisch)", key=f"{k}_en", height=90,
                 help=f"Das Modell liest die {'englische' if lang == 'en' else 'deutsche'} Fassung "
                      f"(question_lang: {lang}). " + QUESTION_HELP)
    st.button("Englisch aus Deutsch übernehmen (KI)", icon=":material/translate:", key=f"{k}_tr",
              on_click=_translate, args=(f"{k}_de", f"{k}_en"),
              help="Übersetzt die deutsche Frage mit dem konfigurierten Sprachmodell. Ohne Klick bleibt die bisherige "
                   "englische Fassung.")
    old_q = (fact or {}).get("en" if lang == "en" else "de")
    new_q = ss.get(f"{k}_en") if lang == "en" else de
    if fact and " ".join(str(old_q or "").split()) != " ".join(str(new_q or "").split()):
        st.warning("Diese Frage liest das Modell anders als bisher: die Antworten für diesen Fakt müssen neu berechnet "
                   "werden (Vorschau: «Neue Fragen abfragen», sonst beim nächsten Lauf).", icon=":material/sync_problem:")
    elif fact and de.split() != str(fact.get("de") or "").split() and lang == "en":
        st.info("Nur die deutsche Fassung geändert: das Modell liest Englisch, Entscheide ändern sich erst, wenn die "
                "englische Fassung angepasst ist.", icon=":material/info:")
    if st.button("Übernehmen", type="primary", key=f"{k}_ok", icon=":material/check:"):
        if not de.strip():
            st.error("Die deutsche Frage darf nicht leer sein.")
            return
        cand = copy.deepcopy(doc())
        new_id = fid or pe.new_fact_id(cand, fam, label or de)
        try:
            pe.upsert_fact(cand, fam, {"id": new_id, "label": label or new_id, "role": role, "de": de,
                                       "en": ss.get(f"{k}_en", "")})
        except PolicyTableError as e:
            st.error(str(e))
            return
        if _set_doc(cand, f"Fakt «{label or new_id}» {'geändert' if fid else 'angelegt'} (Arbeitskopie)."):
            for key in [x for x in ss if str(x).startswith(k)]:
                del ss[key]
            ss["rw_fact_edit"] = None
            st.rerun()


def family_tab(fam: str) -> None:
    fdoc = pe.family_doc(doc(), fam)
    labels = pe.fact_labels(doc(), fam)
    rules = fdoc["rules"]
    bkey = f"rw_basis_{fam}"
    c1, c2 = st.columns([4, 1], vertical_alignment="bottom")
    basis = c1.text_input("Rechtsgrundlage dieser Art (Vorschlag, bitte durch Compliance bestätigen)",
                          value=str(fdoc.get("basis") or ""), key=bkey)
    if c2.button("Speichern", key=f"{bkey}_ok", disabled=basis == str(fdoc.get("basis") or "")):
        cand = copy.deepcopy(doc())
        pe.family_doc(cand, fam)["basis"] = basis.strip()
        if not basis.strip():
            pe.family_doc(cand, fam).pop("basis", None)
        _set_doc(cand, "Rechtsgrundlage geändert (Arbeitskopie).")
        st.rerun()

    st.markdown("##### Regeln (von oben nach unten geprüft, die erste zutreffende entscheidet)")
    for i, r in enumerate(rules):
        rule_card(fam, i, r, len(rules), labels)

    with st.expander("Regel von Hand hinzufügen", icon=":material/add_circle:"):
        k = f"rw_newrule_{fam}"
        new = rule_form(k, {"id": "", "label": "review", "when": f"{next(iter(labels))} = yes" if labels else "true",
                            "text": ""}, labels)
        if st.button("In Arbeitskopie übernehmen", key=f"{k}_ok", type="primary", icon=":material/check:"):
            cand = copy.deepcopy(doc())
            new["id"] = pe.new_rule_id(cand, fam, new["label"])
            pos = pe.add_rule(cand, fam, new)
            if _set_doc(cand, f"Regel {new['id']} an Position {pos + 1} angelegt (Arbeitskopie)."):
                for key in [x for x in ss if str(x).startswith(k)]:
                    del ss[key]
                st.rerun()

    st.markdown("##### Fakten (Fragen an das Sprachmodell)")
    used = pe.facts_in_use(doc(), fam)
    for f in fdoc["facts"]:
        fid = str(f["id"])
        with st.expander(f"{f.get('label')} · {pe.ROLE_DE.get(str(f.get('role')), f.get('role'))}"
                         + ("" if fid in used else " · in keiner Regel verwendet"), icon=":material/help:"):
            if ss.get("rw_fact_edit") == (fam, fid):
                fact_editor(fam, f)
                st.button("Abbrechen", key=f"rw_fx_cancel_{fam}_{fid}",
                          on_click=lambda: ss.update(rw_fact_edit=None))
            else:
                st.markdown(f"**Frage:** {ui.esc(str(f.get('de') or ''))}")
                st.caption(f"Englisch (liest das Modell{'' if lang == 'en' else ' nicht'}): {ui.esc(str(f.get('en') or '–'))}"
                           f" · Id `{fid}`")
                st.button("Frage bearbeiten", key=f"rw_fx_btn_{fam}_{fid}", icon=":material/edit:",
                          on_click=lambda t=(fam, fid): ss.update(rw_fact_edit=t))
    with st.expander("Neuen Fakt anlegen", icon=":material/add:"):
        fact_editor(fam, None)


# --------------------------------------------------------------------------------------------
# tab: new rule in own words (LLM draft)
# --------------------------------------------------------------------------------------------


def _make_draft() -> None:
    request = ss.get("rw_ai_request", "")
    try:
        llm = app.ctx.llm(getattr(check, "llm_name", "default"))
        ss["rw_ai"] = rd.draft_rule(llm, doc(), request, fam_names)
        ss["rw_ai_error"] = None
        for k in [k for k in ss if str(k).startswith("rw_aid_")]:
            del ss[k]
    except rd.NeedsNewFamily as e:
        ss["rw_ai"], ss["rw_ai_error"], ss["rw_ai_newfam"] = None, None, e.request
    except rd.DraftError as e:
        ss["rw_ai"], ss["rw_ai_error"] = None, str(e)
    except Exception as e:
        ss["rw_ai"], ss["rw_ai_error"] = None, (f"Sprachmodell nicht erreichbar ({type(e).__name__}: {str(e)[:160]}). "
                                                "Entwürfe brauchen das konfigurierte LLM (GPU-Rechner).")


def ai_tab() -> None:
    st.markdown("Beschreiben Sie die Regel so, wie Sie sie einer Kollegin erklären würden. Das Sprachmodell schlägt "
                "die passenden Ja/Nein-Fragen und die Regel vor; **nichts davon wird automatisch aktiv**.")
    st.text_area("Regel in eigenen Worten (Deutsch oder Englisch)", key="rw_ai_request", height=90,
                 placeholder="Alarm, wenn ein Kunde eine Zahlung in mehrere Beträge knapp unter 10'000 aufteilen will, "
                             "um eine Meldung zu vermeiden.")
    st.button("Entwurf erstellen", type="primary", icon=":material/auto_awesome:", on_click=_make_draft,
              disabled=not str(ss.get("rw_ai_request") or "").strip())
    if ss.get("rw_ai_error"):
        st.error(ss["rw_ai_error"], icon=":material/error:")
    if ss.get("rw_ai_newfam"):
        st.info("Diese Regel passt laut Sprachmodell zu **keiner bestehenden Prüfart**. Legen Sie dafür eine neue "
                "Prüfart an; Ihre Beschreibung wird übernommen.", icon=":material/add_circle:")
        st.button("Als neue Prüfart anlegen", icon=":material/category:", key="rw_ai_to_family",
                  on_click=lambda: ss.update(rw_section="family", rw_fam_request=ss.pop("rw_ai_newfam", "")))
    draft: rd.Draft | None = ss.get("rw_ai")
    if draft is None:
        return
    with st.container(border=True):
        st.markdown(":orange-badge[:material/smart_toy: von KI vorgeschlagen — bitte prüfen]  "
                    f"Art: **{ui.esc(fam_names.get(draft.family, draft.family))}**")
        if draft.note:
            st.caption(f"Hinweis der KI: {ui.esc(draft.note)}")
        for w in draft.warnings:
            st.warning(w, icon=":material/warning:")
        facts = []
        for i, f in enumerate(draft.facts):
            k = f"rw_aid_f{i}"
            st.markdown(f"**Neuer Fakt {i + 1}** `{f['id']}`")
            c1, c2 = st.columns([3, 2])
            label = c1.text_input("Bezeichnung", value=f["label"], key=f"{k}_label")
            role = c2.selectbox("Rolle", list(FACT_ROLES), index=list(FACT_ROLES).index(f["role"]),
                                format_func=pe.ROLE_DE.get, key=f"{k}_role")
            de = st.text_area("Frage (Deutsch)", value=f["de"], key=f"{k}_de", height=70)
            en = st.text_area("Frage (Englisch, liest das Modell)" if lang == "en" else "Frage (Englisch)",
                              value=f.get("en", ""), key=f"{k}_en", height=70)
            facts.append({"id": f["id"], "label": label, "role": role, "de": de, "en": en})
        labels = {**pe.fact_labels(doc(), draft.family), **{f["id"]: f["label"] for f in facts}}
        st.markdown("**Regel**")
        rule = rule_form("rw_aid_rule", draft.rule, labels)
        c1, c2 = st.columns(2)
        if c1.button("In Arbeitskopie übernehmen", type="primary", icon=":material/playlist_add:", key="rw_ai_apply"):
            try:
                edited = rd.Draft(draft.family, [pe.clean_fact(f) for f in facts], rule, draft.note, [], draft.request)
                cand = rd.apply_draft(doc(), edited)
            except (PolicyTableError, KeyError) as e:
                st.error(f"Nicht übernommen: {e}")
            else:
                if _set_doc(cand, "KI-Entwurf in die Arbeitskopie übernommen (nicht aktiv). Weiter: Vorschau & Speichern."):
                    audit.log_event(app.runs_dir, "policy_ai_draft", user=ss["rw_user"], request=draft.request,
                                    family=draft.family, rule=rule, facts=facts, raw=draft.raw)
                    ss["rw_ai"] = None
                    st.rerun()
        if c2.button("Verwerfen", icon=":material/delete:", key="rw_ai_discard"):
            ss["rw_ai"] = None
            st.rerun()


# --------------------------------------------------------------------------------------------
# tab: preview + save
# --------------------------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def _dev_dialogues() -> set[str] | None:
    from callguard.splits import load_splits

    sp = load_splits(required=False)
    return set(sp.dev_dialogues()) if sp else None


def _run_probes(tasks: list[wi.Key]) -> None:
    bar = st.progress(0.0, text="Neue Fragen werden dem Sprachmodell gestellt …")

    def progress(i: int, n: int) -> None:
        bar.progress(i / n, text=f"{i} von {n} Antworten")

    try:
        out, errors = wi.run_probes(check, app.loaded.results, work_table, tasks,
                                    {**{f.id: f for f in work_families}, **families_by_id},
                                    lambda r: be.check_view_transcript(app.engine.pipeline, check, r), progress)
    except wi.ProbeUnavailable as e:
        bar.empty()
        ss["rw_probe_error"] = str(e)
        return
    for (cid, fam, fid), p in out.items():
        ss["rw_probes"][(cid, fam, fid)] = (work_table.families[fam].fact(fid).question(lang), p)
    ss["rw_probe_error"] = None
    if errors:
        _flash(f"{len(errors)} Antworten fehlgeschlagen, z.B. {errors[0][:120]}", ":material/error:")
    st.rerun()


def preview_tab() -> None:
    if not changes:
        st.info("Die Arbeitskopie entspricht der aktiven Version. Änderungen in den Tabs der Arten oder über "
                "«Neue Regel in eigenen Worten» erscheinen hier.", icon=":material/info:")
    else:
        st.markdown(f"**Änderungen gegenüber Version {store.active().n}**")
        st.markdown("\n".join(f"- {ui.esc(c)}" for c in changes))
    if pv is None:
        st.warning("Keine Fusion verfügbar: die Vorschau kann nicht rechnen.")
        return
    if not pv.n_calls:
        st.info("Keine verarbeiteten Anrufe mit Fakten-Ergebnissen in dieser Quelle: nichts zum Vergleichen.")

    tasks = [t for t in wi.probe_tasks(app.loaded.results, work_table, lang, new_family_ids) if t not in probes]
    if new_family_ids:
        st.info("Neue Prüfart in der Arbeitskopie: für die schon verarbeiteten Anrufe gibt es noch keine Antworten auf "
                "ihre Fragen. Erst nach «Neue Fragen jetzt abfragen» zeigt die Vorschau, welche Anrufe sie markiert; "
                "Stichwort-Treffer der neuen Prüfart kommen mit dem nächsten Lauf (oder «Günstige Prüfungen neu "
                "ausführen» auf der Stichwort-Seite nach der Freigabe).", icon=":material/category:")
    if tasks:
        n_facts = len({(f, x) for _, f, x in tasks})
        sec = wi.seconds_per_probe(app.loaded.results)
        par = max(1, int(getattr(check, "parallel", 1) or 1))
        est = len(tasks) * sec / par
        st.warning(f"**{n_facts} neue oder geänderte Frage{'n' if n_facts != 1 else ''}**: dafür fehlen "
                   f"{len(tasks)} Antworten des Sprachmodells. Bis sie berechnet sind, zählen diese Fakten als "
                   "«unklar»; betroffene Anrufe sind unten als *vorläufig* markiert.", icon=":material/sync_problem:")
        st.caption(f"Geschätzte Dauer ≈ {est:.0f} s ({len(tasks)} Abfragen × {sec:.2f} s, gemessen in den bisherigen "
                   f"Läufen, {par} parallel). Die Antworten werden zwischengespeichert und vom nächsten Lauf "
                   "wiederverwendet.")
        if st.button("Neue Fragen jetzt abfragen", icon=":material/play_arrow:", type="primary"):
            _run_probes(tasks)
        if ss.get("rw_probe_error"):
            st.warning("Vorschau nur für Regeländerungen möglich; neue Fragen werden beim nächsten Lauf berechnet. "
                       f"(Sprachmodell nicht erreichbar: {ss['rw_probe_error'][:200]})", icon=":material/cloud_off:")

    changed = pv.changed
    provisional = {c.call_id for c in changed
                   if any(c.families_after[f].unresolved for f in c.changed_families() if f in c.families_after)}
    if changes and pv.n_calls:
        if not changed:
            st.success(f"Diese Änderung ändert **keinen** der {pv.n_calls} verarbeiteten Anrufe (bei den aktuellen "
                       "Einstellungen der Seitenleiste).", icon=":material/check_circle:")
        else:
            st.markdown(f"#### Diese Änderung ändert {len(changed)} von {pv.n_calls} Anrufen")
            if provisional:
                st.caption(f"{len(provisional)} davon vorläufig: sie hängen an einer noch unbeantworteten neuen Frage "
                           "(gezählt als «unklar») und können sich nach dem Abfragen wieder ändern.")
            for c in changed:
                fams = c.changed_families()
                why = "; ".join(
                    f"{fam_names.get(f, f)}: {c.families_before[f].rule or '–'} → {c.families_after[f].rule or '–'}"
                    for f in fams if f in c.families_before)
                cols = st.columns([5, 2], vertical_alignment="center")
                cols[0].markdown(f"**{c.call_id}** {ui.label_md(c.before)} → {ui.label_md(c.after)}"
                                 + (" :gray-badge[vorläufig: neue Frage unbeantwortet]" if c.call_id in provisional
                                    else "") + f"  \n:small[{ui.esc(why)}]")
                if "detail" in app.pages:
                    cols[1].page_link(app.pages["detail"], label="Anruf öffnen", icon=":material/open_in_new:",
                                      query_params={"call": c.call_id})
        _effect(changed)
    if pv.errors:
        st.caption(f"{len(pv.errors)} Anrufe nicht vergleichbar, z.B. {pv.errors[0][:160]}")

    st.divider()
    st.markdown("#### Als Entwurf speichern")
    st.caption("Speichern macht nichts aktiv: der Entwurf bekommt eine Versionsnummer und muss von einer zweiten "
               "Person freigegeben werden (Bereich «Versionen & Freigabe»).")
    comment = st.text_input("Kommentar (warum diese Änderung?)", key="rw_comment")
    if st.button(f"Als Entwurf speichern (Version {store.next_n()})", type="primary", icon=":material/save:",
                 disabled=not changes or app.read_only or bool(work_error)):
        try:
            v = store.save_draft(bundle(), ss["rw_user"], comment, family_names=fam_names, profile=profile,
                                 check_kinds=CHECK_KIND)
        except (FourEyesError, PolicyTableError) as e:
            st.error(str(e))
        else:
            ss["rw_base"] = v.n
            _flash(f"Version {v.n} als Entwurf gespeichert. Freigabe durch eine zweite Person nötig.")
            st.rerun()


def _effect(changed: list[wi.CallPreview]) -> None:
    truth_calls = ground_truth(str(app.ctx.data_dir))
    dev = _dev_dialogues()
    truth = {cid: c.expected.label for cid, c in truth_calls.items() if c.expected is not None
             and cid in app.loaded.results and (dev is None or dialogue_of(cid) in dev)}
    if not truth:
        return
    eff = wi.label_effect(pv.calls, truth)
    if not eff["n"]:
        return
    d_hits, d_false = eff["hits_after"] - eff["hits_before"], eff["false_after"] - eff["false_before"]
    d_exact = eff["exact_after"] - eff["exact_before"]
    st.markdown("**Wirkung auf Anrufe mit bekannter Sollbewertung** "
                f"({'Dev-Split' if dev is not None else 'alle'}, n = {eff['n']})")
    m = st.columns(3)
    m[0].metric("Treffer (Soll Alarm/Prüfen markiert)", eff["hits_after"], f"{d_hits:+d}")
    m[1].metric("Fehlalarme (Soll Kein Alarm markiert)", eff["false_after"], f"{d_false:+d}", delta_color="inverse")
    m[2].metric("Exakt richtig", eff["exact_after"], f"{d_exact:+d}")
    st.caption(f"{'+' if d_hits >= 0 else ''}{d_hits} Treffer, {'+' if d_false >= 0 else ''}{d_false} Fehlalarme. "
               f"Achtung kleine Zahl: bei {eff['n']} Anrufen (je zwei pro Dialog) sind ±1–2 Anrufe Rauschen; "
               "Holdout-Anrufe werden hier nie gezeigt. Sollbewertungen dienen nur dieser Auswertung.")


# --------------------------------------------------------------------------------------------
# tab: versions + four-eyes approval
# --------------------------------------------------------------------------------------------


def _redecide_stored(v_n: int) -> None:
    """Write the stored results re-decided with the active table (rules only, cached fact answers)."""
    table = pe.validate(store.active().doc())
    known = _valid_probes(table)  # answers asked in this session's preview (new questions / Prüfarten)
    parent = store.get(v_n).meta.get("parent")
    before = set((store.get(parent).doc().get("families") or {}) if parent else table.families)
    added = set(table.families) - before  # Prüfarten new in this version: every call needs their answers
    n = skipped = 0
    for cid, r in app.loaded.results.items():
        if wi.facts_check_name(r) is None:
            continue
        if [t for t in wi.probe_tasks({cid: r}, table, lang, added) if t not in known]:
            skipped += 1
            continue
        new, _ = wi.redecide_result(r, table, params, known, lang, decide_fact)
        name = wi.facts_check_name(new)
        meta = dict(new.checks[name].meta or {})
        meta["policy_table"] = {**(meta.get("policy_table") or {}), "hash": table.key(list(new.checks[name].family_scores)),
                                "version": v_n, "redecided": True}
        new.checks[name] = new.checks[name].model_copy(update={"meta": meta})
        decided = be.redecide(app.engine, new, None, app.all_families or None)  # profile defaults, like a run
        if not decided.live:
            skipped += 1
            continue
        be.write_result(app.loaded.paths[cid], new.model_copy(update={"decision": decided.decision}))
        n += 1
    audit.log_event(app.runs_dir, "policy_redecided", user=ss["rw_user"], version=v_n, calls=n, skipped=skipped)
    reload_everything()
    ss["rw_just_approved"] = None
    _flash(f"{n} gespeicherte Anrufe mit Version {v_n} neu entschieden"
           + (f"; {skipped} brauchen neue Antworten und folgen beim nächsten Lauf." if skipped else "."))


def versions_tab() -> None:
    versions = list(reversed(store.versions()))
    act = store.active()
    st.dataframe([{"Version": v.n, "Status": STATUS_DE.get(v.status, v.status) + (" · aktiv" if act and v.n == act.n
                                                                               else ""),
                   "Verfasst von": v.author, "Freigegeben von": v.meta.get("approver") or "",
                   "Erstellt": str(v.meta.get("created", ""))[:16], "Kommentar": v.meta.get("comment") or ""}
                  for v in versions], hide_index=True)
    st.caption("Vier-Augen-Prinzip: wer einen Entwurf verfasst hat, kann ihn nicht selbst freigeben. Nur freigegebene "
               "Versionen werden in die aktive Datei geschrieben und vom Pipeline-Lauf verwendet.")
    for v in [v for v in versions if v.status == "draft"]:
        with st.container(border=True):
            st.markdown(f"**Version {v.n}** · :orange-badge[Entwurf] von **{ui.esc(v.author)}** · "
                        f"{str(v.meta.get('created', ''))[:16]}"
                        + (f"  \n:material/chat: {ui.esc(str(v.meta['comment']))}" if v.meta.get("comment") else ""))
            base = store.active()
            live = store.live_bundle()
            diff = rb.diff_bundle(live, {**live, **v.bundle()}, fam_names, profile, CHECK_KIND) if base else []
            st.markdown("\n".join(f"- {ui.esc(c)}" for c in diff) or "_keine Änderung gegenüber der aktiven Version_")
            c1, c2, c3, c4 = st.columns([2, 1.2, 1, 1.2], vertical_alignment="bottom")
            approver = c1.text_input("Freigabe durch (Name)", key=f"rw_appr_{v.n}",
                                     value="" if pe_same(ss["rw_user"], v.author) else ss["rw_user"])
            if c2.button("Freigeben", key=f"rw_ok_{v.n}", type="primary", icon=":material/verified:",
                         disabled=app.read_only):
                try:
                    store.approve(v.n, approver)
                except FourEyesError as e:
                    st.error(str(e), icon=":material/group:")
                else:
                    live = store.live_bundle()
                    ss.update(rw_doc=live["policy_table"], rw_base=v.n, rw_just_approved=v.n,
                              rw_extra={k: x for k, x in live.items() if k != "policy_table"})
                    reload_everything()
                    _flash(f"Version {v.n} freigegeben und aktiv.")
                    st.rerun()
            if c3.button("Verwerfen", key=f"rw_rej_{v.n}", disabled=app.read_only):
                store.reject(v.n, ss["rw_user"])
                st.rerun()
            if c4.button("In Arbeitskopie laden", key=f"rw_load_{v.n}"):
                loaded = {**store.live_bundle(), **v.bundle()}
                ss.update(rw_doc=loaded["policy_table"], rw_base=v.n, rw_edit=None,
                          rw_extra={k: x for k, x in loaded.items() if k != "policy_table"})
                _flash(f"Version {v.n} in die Arbeitskopie geladen.")
                st.rerun()

    just = ss.get("rw_just_approved")
    if just and act and act.n == just and not app.read_only:
        st.info(f"Version {just} ist aktiv und gilt für jeden neuen Lauf. Die schon verarbeiteten Anrufe zeigen noch "
                "die Entscheide ihres Laufs.", icon=":material/info:")
        st.button("Gespeicherte Anrufe jetzt mit dieser Version neu entscheiden (nur Regeln, kein LLM)",
                  icon=":material/published_with_changes:", on_click=_redecide_stored, args=(just,))

    others = [v for v in versions if v.status == "approved" and act and v.n != act.n]
    if others:
        st.markdown("#### Zurücksetzen")
        c1, c2 = st.columns([2, 2], vertical_alignment="bottom")
        n = c1.selectbox("Frühere freigegebene Version", [v.n for v in others], format_func=lambda n: f"Version {n}")
        if c2.button(f"Zurücksetzen auf Version {n} (als Entwurf)", icon=":material/history:", disabled=app.read_only):
            try:
                v = store.rollback(n, ss["rw_user"], fam_names, profile)
            except (FourEyesError, PolicyTableError) as e:
                st.error(str(e))
            else:
                _flash(f"Entwurf Version {v.n} = Inhalt von Version {n}. Freigabe durch eine zweite Person nötig.")
                st.rerun()
        with st.expander("Unterschied zur Vorgängerversion anzeigen"):
            for v in versions:
                prev = next((p for p in store.versions() if p.n == (v.meta.get("parent") or 0)), None)
                if prev is None:
                    continue
                d = rb.diff_bundle(prev.bundle(), {**prev.bundle(), **v.bundle()}, fam_names, profile, CHECK_KIND)
                st.markdown(f"**Version {v.n}** (gegenüber {prev.n}, {STATUS_DE.get(v.status, v.status)})")
                st.markdown("\n".join(f"- {ui.esc(c)}" for c in d) or "_keine Änderung_")


def pe_same(a: str, b: str) -> bool:
    from callguard.policy_versions import same_person

    return same_person(a, b)


# --------------------------------------------------------------------------------------------
# section: Prüfarten & Prüfungen on/off
# --------------------------------------------------------------------------------------------


def _fam_toggle(fid: str, key: str) -> None:
    b = copy.deepcopy(bundle())
    rb.set_family_enabled(b, fid, bool(ss[key]))
    ss["rw_extra"] = {k: v for k, v in b.items() if k != "policy_table"}


def _check_toggle(name: str, key: str) -> None:
    b = copy.deepcopy(bundle())
    rb.set_check_enabled(b, profile, name, bool(ss[key]))
    ss["rw_extra"] = {k: v for k, v in b.items() if k != "policy_table"}


def _goto(section: str) -> None:
    ss["rw_section"] = section


def _preview_line() -> None:
    if pv is None or not changes:
        return
    n = len(pv.changed)
    st.markdown(f":material/preview: Mit der Arbeitskopie ändern sich **{n} von {pv.n_calls}** verarbeiteten Anrufen "
                "(bei den Einstellungen der Seitenleiste).")
    st.button("Zur Vorschau", icon=":material/arrow_forward:", key=f"rw_goto_preview_{section}",
              on_click=_goto, args=("preview",))


def switches_tab() -> None:
    b = bundle()
    teams = (b.get("routing") or {}).get("teams") or {}
    st.markdown("##### Prüfarten")
    st.caption("Ausgeschaltet = diese Art von Fehlverhalten wird nicht mehr gesucht und zählt in keinem Entscheid "
               "(Kriterien: `enabled: false`). Anders als der Schalter in der Seitenleiste (nur Ihre Ansicht, sofort) "
               "gilt dieser Schalter für alle und erst nach Freigabe.")
    for f in work_families:
        on = rb.family_enabled(b, f.id)
        n_rules = len((((b["policy_table"].get("families") or {}).get(f.id)) or {}).get("rules") or [])
        to = rb.family_team(b, f.id)
        with st.container(border=True):
            cols = st.columns([4, 1.3, 4], vertical_alignment="center")
            cols[0].markdown(f"**{ui.esc(be.short_label(f.label))}**"
                             + (" :blue-badge[neu]" if f.id in new_family_ids else "")
                             + ("" if f.can_alarm else " :gray-badge[nur Hinweis]"))
            key = f"rw_famon_{f.id}_{on}"
            cols[1].toggle("aktiv", value=on, key=key, on_change=_fam_toggle, args=(f.id, key), disabled=app.read_only)
            cols[2].caption(f"`{f.id}` · {len(f.keywords)} Stichwortgruppe(n) · {n_rules} Regel(n) · Meldung an "
                            + (", ".join(str((teams.get(t) or {}).get("name") or t) for t in to) or "Standard-Meldeweg"))
    st.markdown("##### Prüfungen")
    st.caption(f"Ausgeschaltet = Gewicht 0 im Profil **{profile}** (`tuning.yaml`): die Prüfung zählt in keinem "
               "Entscheid mehr. Wie der Gewichts-Regler in der Seitenleiste, aber dauerhaft und mit Freigabe.")
    off = rb.checks_off(b, profile)
    weights = app.default_weights
    for c in app.cfg.checks:
        name = str(c.get("name") or c.get("type"))
        on = name not in off
        cols = st.columns([4, 1.3, 4], vertical_alignment="center")
        cols[0].markdown(f"**{ui.esc(CHECK_KIND.get(name, name))}**")
        key = f"rw_chkon_{name}_{on}"
        cols[1].toggle("aktiv", value=on, key=key, on_change=_check_toggle, args=(name, key), disabled=app.read_only)
        cols[2].caption(f"`{name}` ({c.get('type')}) · Gewicht jetzt {weights.get(name, c.get('weight', 1.0)):.2f}")
    _preview_line()


# --------------------------------------------------------------------------------------------
# section: new Prüfart (wizard)
# --------------------------------------------------------------------------------------------


def _teams() -> dict[str, str]:
    return {str(k): str((v or {}).get("name") or k) for k, v in ((bundle().get("routing") or {}).get("teams") or {}).items()}


def _clear_fd() -> None:
    for k in [k for k in ss if str(k).startswith("rw_fd_")]:
        del ss[k]


def _make_family_draft() -> None:
    try:
        llm = app.ctx.llm(getattr(check, "llm_name", "default"))
        ss["rw_fam_draft"] = rd.draft_family(llm, bundle(), ss.get("rw_fam_request", ""), fam_names, _teams(),
                                             ss.get("rw_fam_name", ""))
        ss["rw_fam_ai"], ss["rw_fam_error"] = True, None
        _clear_fd()
    except rd.DraftError as e:
        ss["rw_fam_draft"], ss["rw_fam_error"] = None, str(e)
    except Exception as e:
        ss["rw_fam_draft"], ss["rw_fam_error"] = None, (
            f"Sprachmodell nicht erreichbar ({type(e).__name__}: {str(e)[:160]}). Entwürfe brauchen das konfigurierte "
            "LLM (GPU-Rechner); «Ohne KI beginnen» geht immer.")


def _blank_family() -> None:
    ss["rw_fam_draft"] = rd.blank_family(bundle(), ss.get("rw_fam_name", "") or "Neue Prüfart",
                                         ss.get("rw_fam_request", ""))
    ss["rw_fam_ai"], ss["rw_fam_error"] = False, None
    _clear_fd()


def _fd_add(kind: str) -> None:
    fd: rd.FamilyDraft = ss["rw_fam_draft"]
    spec = fd.spec
    if kind == "fact":
        n = len(spec["facts"]) + 1
        while any(f["id"] == f"fakt_{n}" for f in spec["facts"]):
            n += 1
        spec["facts"].append({"id": f"fakt_{n}", "label": f"Fakt {n}", "role": "context", "de": "", "en": ""})
    else:
        first = spec["facts"][0]["id"] if spec["facts"] else "act"
        spec["rules"].append({"id": f"{spec['id']}.review_{len(spec['rules']) + 1}", "label": "review",
                              "when": f"{first} = yes", "text": ""})


def _lines(text: str) -> list[str]:
    return [" ".join(x.split()) for x in str(text or "").splitlines() if x.strip()]


def family_wizard() -> None:
    st.markdown("Eine neue Prüfart ist reine Konfiguration: Name und Beschreibung (Kriterien), Stichwörter, "
                "Ja/Nein-Fragen und Regeln, Rechtsgrundlage und Meldeweg. Beschreiben Sie, was gesucht werden soll; "
                "das Sprachmodell schlägt alles vor, Sie prüfen und ändern. **Aktiv wird nichts vor der Vorschau und "
                "der Freigabe durch eine zweite Person.**")
    c1, c2 = st.columns([1, 2])
    c1.text_input("Name der Prüfart", key="rw_fam_name", placeholder="z.B. Bestechung")
    c2.text_area("Beschreibung in eigenen Worten", key="rw_fam_request", height=90,
                 placeholder="Alarm, wenn jemand dem Berater einen persönlichen Vorteil anbietet, damit er eine Zahlung "
                             "ohne Prüfung freigibt. Harmlos: der Berater lehnt ab und meldet es.")
    b1, b2, _ = st.columns([1.2, 1, 2])
    b1.button("Entwurf mit KI erstellen", type="primary", icon=":material/auto_awesome:", key="rw_fam_ai_btn",
              on_click=_make_family_draft, disabled=not str(ss.get("rw_fam_request") or "").strip())
    b2.button("Ohne KI beginnen", icon=":material/edit_note:", key="rw_fam_blank_btn", on_click=_blank_family)
    if ss.get("rw_fam_error"):
        st.error(ss["rw_fam_error"], icon=":material/error:")
    fd: rd.FamilyDraft | None = ss.get("rw_fam_draft")
    if fd is None:
        return
    spec = fd.spec
    teams = _teams()
    with st.container(border=True):
        st.markdown((":orange-badge[:material/smart_toy: von KI vorgeschlagen — bitte prüfen]" if ss.get("rw_fam_ai")
                     else ":gray-badge[Vorlage ohne KI]") + f"  Neue Prüfart **{ui.esc(spec['label'])}**")
        if fd.note:
            st.caption(f"Hinweis: {ui.esc(fd.note)}")
        for w in fd.warnings:
            st.warning(w, icon=":material/warning:")
        c1, c2 = st.columns([2, 1])
        label = c1.text_input("Name", value=spec["label"], key="rw_fd_label")
        fid = c2.text_input("Kennung (intern)", value=spec["id"], key="rw_fd_id",
                            help="Kleinbuchstaben, Ziffern, _ ; erscheint in Regeln, Meldungen und im Audit-Log.")
        policy = st.text_area("Beschreibung (Kriterien, lesen die KI-Prüfungen)", value=spec["policy"], key="rw_fd_policy",
                              height=90)
        c1, c2, c3 = st.columns(3)
        alarm_when = c1.text_area("Alarm, wenn … (eine Zeile pro Fall)", value="\n".join(spec["alarm_when"]),
                                  key="rw_fd_alarm", height=110)
        not_alarm = c2.text_area("Harmlos, wenn …", value="\n".join(spec["not_alarm_when"]), key="rw_fd_notalarm",
                                 height=110)
        review = c3.text_area("Prüfen, wenn …", value="\n".join(spec["review_when"]), key="rw_fd_review", height=110)
        c1, c2 = st.columns(2)
        keywords = c1.text_area("Stichwörter Hochdeutsch (durch Komma getrennt)", value=", ".join(spec["keywords"]),
                                key="rw_fd_kw", height=68)
        keywords_gsw = c2.text_area("Stichwörter Schweizerdeutsch (optional)", value=", ".join(spec["keywords_gsw"]),
                                    key="rw_fd_kwgsw", height=68)
        c1, c2 = st.columns([2, 1])
        basis = c1.text_input("Rechtsgrundlage (Vorschlag, durch Compliance zu bestätigen)", value=spec["basis"],
                              key="rw_fd_basis")
        team_opts = ["", *teams]
        team = c2.selectbox("Meldung an", team_opts, index=team_opts.index(spec["team"]) if spec["team"] in team_opts
                            else 0, format_func=lambda t: teams.get(t, "Standard-Meldeweg"), key="rw_fd_team")

        st.markdown("**Fakten (Ja/Nein-Fragen an das Sprachmodell)**")
        facts = []
        for i, f in enumerate(spec["facts"]):
            k = f"rw_fd_f_{f['id']}"
            cols = st.columns([0.6, 2.4, 2], vertical_alignment="bottom")
            use = cols[0].checkbox("nutzen", value=True, key=f"{k}_use")
            flabel = cols[1].text_input(f"Fakt `{f['id']}`", value=f["label"], key=f"{k}_label")
            role = cols[2].selectbox("Rolle", list(FACT_ROLES), index=list(FACT_ROLES).index(f["role"]),
                                     format_func=pe.ROLE_DE.get, key=f"{k}_role")
            de = st.text_input("Frage (Deutsch)", value=f["de"], key=f"{k}_de")
            en = st.text_input("Frage (Englisch, liest das Modell)" if lang == "en" else "Frage (Englisch)",
                               value=f.get("en", ""), key=f"{k}_en")
            if use:
                facts.append({"id": f["id"], "label": flabel, "role": role, "de": de, "en": en})
        st.button("Fakt hinzufügen", icon=":material/add:", key="rw_fd_addfact", on_click=_fd_add, args=("fact",))
        labels = {f["id"]: f["label"] for f in facts}
        st.markdown("**Regeln** (von oben nach unten; am Ende gilt automatisch «sonst kein Alarm»)")
        rules = []
        for i, r in enumerate(spec["rules"]):
            with st.container(border=True):
                rules.append(rule_form(f"rw_fd_r{i}", r, labels) if labels else r)
        st.button("Regel hinzufügen", icon=":material/add:", key="rw_fd_addrule", on_click=_fd_add, args=("rule",))

        c1, c2 = st.columns(2)
        if c1.button("In Arbeitskopie übernehmen", type="primary", icon=":material/playlist_add:", key="rw_fd_apply"):
            new_spec = {"id": fid.strip(), "label": label, "policy": policy, "alarm_when": _lines(alarm_when),
                        "not_alarm_when": _lines(not_alarm), "review_when": _lines(review), "keywords": keywords,
                        "keywords_gsw": keywords_gsw, "basis": basis, "team": team, "facts": facts,
                        "rules": [{**r, "id": f"{fid.strip()}.{r['label']}_{i + 1}"} for i, r in enumerate(rules)]}
            try:
                cand = rb.add_family(bundle(), new_spec)
            except (PolicyTableError, KeyError) as e:
                st.error(f"Nicht übernommen: {e}")
            else:
                if _set_bundle(cand, f"Prüfart «{label}» in der Arbeitskopie (nicht aktiv). Weiter: Vorschau."):
                    audit.log_event(app.runs_dir, "policy_family_draft", user=ss["rw_user"], family=fid.strip(),
                                    label=label, ai=bool(ss.get("rw_fam_ai")), request=fd.request, raw=fd.raw)
                    ss["rw_fam_draft"] = None
                    _clear_fd()
                    ss["rw_goto"] = "preview"
                    st.rerun()
        if c2.button("Verwerfen", icon=":material/delete:", key="rw_fd_discard"):
            ss["rw_fam_draft"] = None
            _clear_fd()
            st.rerun()


# --------------------------------------------------------------------------------------------
# layout
# --------------------------------------------------------------------------------------------

fam_ids = list((doc().get("families") or {}).keys())
SECTIONS = {"rules": ":material/rule: Regeln", "switches": ":material/toggle_on: Prüfarten & Prüfungen",
            "ai": ":material/auto_awesome: Neue Regel", "family": ":material/category: Neue Prüfart",
            "preview": ":material/preview: Vorschau & Speichern", "versions": ":material/verified: Versionen & Freigabe"}
if "rw_goto" in ss:  # set by a button after the radio was drawn: applied on the next run
    ss["rw_section"] = ss.pop("rw_goto")
n_drafts = len(store.drafts())
section = st.radio("Bereich", list(SECTIONS), key="rw_section", horizontal=True, label_visibility="collapsed",
                   format_func=lambda k: SECTIONS[k] + (f" ({len(changes)})" if k == "preview" and changes else "")
                   + (f" ({n_drafts})" if k == "versions" and n_drafts else ""))
if section == "rules":
    for tab, fam in zip(st.tabs([fam_names.get(f, f) + (" (neu)" if f in new_family_ids else "") for f in fam_ids]),
                        fam_ids):
        with tab:
            family_tab(fam)
elif section == "switches":
    switches_tab()
elif section == "ai":
    ai_tab()
elif section == "family":
    family_wizard()
elif section == "preview":
    preview_tab()
else:
    versions_tab()
