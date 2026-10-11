"""Cross rules (policy table section ``cross_rules``): rules over facts of several Prüfarten (``family.fact``),
evaluated after every family resolved its facts; the first match decides the virtual family «Eigene Regeln».
Parser / validator, evaluation order, the virtual family in the fusion, re-decision == live fusion, governance
(instant + undo), speed, and stable cache keys for tables without the section."""
from __future__ import annotations

import copy
import time
from types import SimpleNamespace

import pytest
import yaml

from callguard import fact_policy as fpol
from callguard import policy_edit as pe
from callguard.checks.facts import CROSS_FAMILY, PolicyTableError, parse_policy_table
from callguard.fusion.two_readers import TwoReadersFusion
from callguard.policy_versions import VersionStore
from callguard.types import CallResult, CheckResult, Decision, Family, FamilyScore, Segment, Transcript

FAMILIES = [Family(id="access", label="Zugangsinformation preisgegeben"), Family(id="disclosure", label="Auskunft an Dritte")]
BASE = {"families": {
    "access": {"facts": [{"id": "spoken", "label": "Code vorgelesen", "role": "act", "de": "Code vorgelesen?"},
                         {"id": "current", "label": "Code gültig", "role": "context", "de": "Gültig?"}],
               "rules": [{"id": "access.alarm", "label": "alarm", "when": "spoken = yes and current = yes"},
                         {"id": "access.no_alert", "label": "no_alert", "when": "true"}]},
    "disclosure": {"facts": [{"id": "data_given", "label": "Daten herausgegeben", "role": "act", "de": "Daten?"},
                             {"id": "authorized", "label": "Vollmacht", "role": "authorization", "de": "Vollmacht?"}],
                   "rules": [{"id": "disclosure.alarm", "label": "alarm", "when": "data_given = yes and authorized = no"},
                             {"id": "disclosure.no_alert", "label": "no_alert", "when": "true"}]}}}
CROSS = [{"id": "eigene.alarm_1", "title": "Code und Daten im selben Gespräch", "label": "alarm",
          "when": "access.spoken = yes and disclosure.data_given = yes", "text": "Code vorgelesen und Daten herausgegeben.",
          "report_as": "access"}]


def table(cross: list | None = CROSS) -> dict:
    t = copy.deepcopy(BASE)
    if cross is not None:
        t["cross_rules"] = copy.deepcopy(cross)
    return t


# ---- parser / validator -------------------------------------------------------------------------


def test_parse_qualified_names_and_errors():
    t = parse_policy_table(table())
    assert t.cross is not None and [r.id for r in t.cross.rules] == ["eigene.alarm_1"]
    assert [f.id for f in t.cross.facts] == ["access.spoken", "disclosure.data_given"]
    assert t.cross.rules[0].report_as == "access" and t.cross.rules[0].title.startswith("Code und Daten")
    assert parse_policy_table(table(None)).cross is None
    for bad, msg in ((["x"], "not a mapping"),
                     ([{**CROSS[0], "when": "access.nope = yes"}], "nope"),
                     ([{**CROSS[0], "when": "spoken = yes"}], "family.fact"),  # unqualified
                     ([{**CROSS[0], "report_as": "weather"}], "report_as"),
                     ([{**CROSS[0], "when": "true"}], "needs a condition"),
                     ([{**CROSS[0], "color": "red"}], "unknown keys")):
        with pytest.raises(PolicyTableError, match=msg):
            parse_policy_table(table(bad))
    with pytest.raises(PolicyTableError):  # family rules still may not use qualified names
        bad = table(None)
        bad["families"]["access"]["rules"][0]["when"] = "disclosure.data_given = yes"
        parse_policy_table(bad)


def test_cache_key_unchanged_by_the_section():
    a, b = parse_policy_table(table(None)), parse_policy_table(table())
    assert a.key(["access", "disclosure"]) == b.key(["access", "disclosure"])


def test_render_with_pruefart_prefix():
    labels = pe.cross_labels(table(), {"access": "Zugang", "disclosure": "Weitergabe"})
    assert pe.render_rule(CROSS[0], labels) == ("WENN Zugang: «Code vorgelesen» = ja UND Weitergabe: «Daten herausgegeben» "
                                               "= ja → ALARM")


# ---- evaluation ---------------------------------------------------------------------------------


def q(y: float, n: float) -> dict[str, float]:
    return {"yes": y, "no": n, "unclear": round(1 - y - n, 4)}


def k(y: float) -> dict[str, float]:
    return {"yes": y, "no": round(1 - y, 4), "unclear": 0.0}


def reader(name: str, answers: dict[str, dict[str, dict[str, float]]]) -> CheckResult:
    fss = {fam: FamilyScore(score=0.0, confidence=1.0, verdict="absent",
                            detail={"facts": {fid: {"p": p, "question": fid, "evidence": [f"S{i}"]}
                                              for i, (fid, p) in enumerate(facts.items())}})
           for fam, facts in answers.items()}
    return CheckResult(check=name, type="facts", family_scores=fss, meta={"model": name})


def call(cid: str, spoken: float, data: float, current: float = 0.05, auth: float = 0.9) -> CallResult:
    ans_q = {"access": {"spoken": q(spoken, 1 - spoken), "current": q(current, 1 - current)},
             "disclosure": {"data_given": q(data, 1 - data), "authorized": q(auth, 1 - auth)}}
    ans_k = {fam: {fid: k(p["yes"]) for fid, p in facts.items()} for fam, facts in ans_q.items()}
    t = Transcript(call_id=cid, segments=[Segment(id=f"S{i}", start=5.0 * i, end=5.0 * i + 4, text="x") for i in range(3)])
    return CallResult(call_id=cid, audio_path="x.wav", transcript=t,
                      checks={"facts": reader("facts", ans_q), "facts_kev": reader("facts_kev", ans_k)},
                      decision=Decision(label="no_alert", score=0.0, uncertainty=0.0, threshold=0.55))


CALLS = {"both": call("both", 0.95, 0.95), "code_only": call("code_only", 0.95, 0.05),
         "none": call("none", 0.05, 0.05), "data_only": call("data_only", 0.05, 0.95)}


@pytest.fixture
def fus(tmp_path):
    tp = tmp_path / "table.yaml"
    tp.write_text(yaml.safe_dump(table()))
    pp = tmp_path / "fact_policy.yaml"
    pp.write_text(fpol.dump_fact_policy(fpol.default_policy()))
    checks = [{"name": "facts", "type": "facts", "weight": 1.0, "policy_table": str(tp)},
              {"name": "facts_kev", "type": "facts", "weight": 1.0, "policy_table": str(tp)}]
    return TwoReadersFusion(SimpleNamespace(cfg=SimpleNamespace(checks=checks)), rule="policy", fact_policy=str(pp))


def test_cross_rule_decides_the_virtual_family_in_the_fusion(fus):
    d = fus.decide(CALLS["both"].transcript, CALLS["both"].checks, FAMILIES)
    assert d.label == "alarm" and d.top_family == CROSS_FAMILY
    assert d.families[CROSS_FAMILY].label == "Eigene Regeln · Zugangsinformation preisgegeben"  # report_as
    assert any("Code und Daten im selben Gespräch" in r for r in d.reasons)
    for cid in ("code_only", "none", "data_only"):  # no cross match: decided exactly as without the section
        d = fus.decide(CALLS[cid].transcript, CALLS[cid].checks, FAMILIES)
        assert CROSS_FAMILY not in d.families and d.label == "no_alert", cid
    comb = fpol.combined_result(fus.table(), CALLS["both"].checks["facts"], CALLS["both"].checks["facts_kev"],
                                fus.fact_policy(), family_names={"access": "Zugang"})
    fs = comb.family_scores[CROSS_FAMILY]
    assert fs.detail["cross"] and fs.detail["rule"]["id"] == "eigene.alarm_1"
    assert fs.detail["facts"]["access.spoken"]["label"] == "Zugang: Code vorgelesen"
    assert fs.segment_ids == ["S0"]  # the decisive facts' evidence


def test_cross_rules_see_resolved_values_after_bands(fus):
    """Evaluated after the per-family resolution: an unclear fact (Kev unsure) does not satisfy «= ja»."""
    shaky = call("shaky", 0.95, 0.95)
    shaky.checks["facts_kev"].family_scores["disclosure"].detail["facts"]["data_given"]["p"] = k(0.5)
    d = fus.decide(shaky.transcript, shaky.checks, FAMILIES)
    assert CROSS_FAMILY not in d.families


def test_redecide_equals_the_live_fusion(fus):
    live = {cid: fus.decide(r.transcript, r.checks, FAMILIES) for cid, r in CALLS.items()}
    out = fpol.redecide(CALLS, fus.table(), fus.fact_policy(),
                        lambda r, c: fus.decide_checks(r.transcript, c, FAMILIES), **fus.scoring)
    assert {c: (o.label, o.score) for c, o in out.items()} == {c: (d.label, d.score) for c, d in live.items()}
    assert out["both"].families[CROSS_FAMILY].rule == "eigene.alarm_1"
    # a draft without the cross rule (what-if): the call is no alarm any more
    out2 = fpol.redecide(CALLS, parse_policy_table(table(None)), fus.fact_policy(),
                         lambda r, c: fus.decide_checks(r.transcript, c, FAMILIES), **fus.scoring)
    assert out2["both"].label == "no_alert"


def test_speed_with_cross_rules(fus):
    base = list(CALLS.values())
    many = {f"x{i}": base[i % 4].model_copy(update={"call_id": f"x{i}"}) for i in range(160)}
    t0 = time.perf_counter()
    fpol.redecide(many, fus.table(), fus.fact_policy(), lambda r, c: fus.decide_checks(r.transcript, c, FAMILIES),
                  **fus.scoring)
    assert time.perf_counter() - t0 < 2.0


# ---- governance: cross rules are rules (instant, undo) ---------------------------------------------


def test_cross_rule_apply_instant_and_undo(tmp_path):
    tp = tmp_path / "policy_table.yaml"
    tp.write_text(pe.dump_doc(table(None)))
    s = VersionStore(tp, audit_dir=tmp_path)
    s.ensure_initial()
    doc = pe.load_doc(tp)
    pe.add_cross_rule(doc, {**CROSS[0]})
    v = s.apply_rules(doc, "Anna", comment="Neue übergreifende Regel")
    assert v.meta["instant"] and pe.load_doc(tp)["cross_rules"][0]["id"] == "eigene.alarm_1"
    assert any("Eigene Regeln (übergreifend): neue Regel" in line for line in v.meta["diff"])
    doc = pe.load_doc(tp)
    pe.set_cross_enabled(doc, "eigene.alarm_1", False)
    s.apply_rules(doc, "Anna")
    assert pe.load_doc(tp)["cross_rules"][0]["enabled"] is False
    s.undo_rules("Anna")
    assert "enabled" not in pe.load_doc(tp)["cross_rules"][0]
    s.undo_rules("Anna")  # undo of the undo restores the switched-off state
    doc = pe.load_doc(tp)
    pe.delete_cross_rule(doc, "eigene.alarm_1")
    s.apply_rules(doc, "Anna")
    assert "cross_rules" not in pe.load_doc(tp)
    assert fpol.only_rules_changed(table(None), table())
    assert not fpol.only_rules_changed(table(None), {**table(), "extra": 1})
