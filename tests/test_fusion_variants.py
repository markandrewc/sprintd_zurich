"""Fusion variants: N14 abstention, LLM-only uncertainty, per-family thresholds (N2), calibrated +
conformal fusion (A5), learned fusion, and the nested CV that evaluates the fitted ones honestly."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from callguard import registry
from callguard.data import Call, Expected
from callguard.fusion import fit as F
from callguard.fusion.calibrated import CalibratedFusion
from callguard.fusion.learned import LearnedFusion
from callguard.fusion.weighted import WeightedFusion
from callguard.types import CallResult, CheckResult, Decision, Family, FamilyScore, Finding, Segment, Transcript

FAMILIES = [
    Family(id="trade", label="Insiderhandel (Information und Kaufwunsch)"),
    Family(id="access", label="Zugangsinformation preisgegeben"),
    Family(id="numbers", label="Zahlenobjekte", can_alarm=False),
]
CTX = SimpleNamespace(cfg=None, families=lambda: list(FAMILIES))
W = {"keywords": 0.35, "patterns": 0.2, "llm_judge": 1.0, "geval": 1.0}


def transcript(call_id: str = "C1", n: int = 6) -> Transcript:
    return Transcript(call_id=call_id, segments=[
        Segment(id=f"S{i:03d}", start=10.0 * i, end=10.0 * i + 8.0, text=f"Satz {i}.") for i in range(n)])


def fs(score: float, conf: float = 1.0, verdict: str | None = None, reason: str = "", segs=()) -> FamilyScore:
    return FamilyScore(score=score, confidence=conf, verdict=verdict, reason=reason, segment_ids=list(segs))


def res(name: str, typ: str | None = None, findings=(), **scores: FamilyScore) -> CheckResult:
    return CheckResult(check=name, type=typ or name, family_scores=scores, findings=list(findings))


def decide(results: list[CheckResult], overrides=None, **kw) -> Decision:
    o = {"weights": dict(W), **(overrides or {})}
    return WeightedFusion(CTX, **kw).decide(transcript(), {r.check: r for r in results}, FAMILIES, o)


def no_keyword_alarm(geval_conf: float | None = None) -> list[CheckResult]:
    """research/ideas_round1.md finding 2: LLM sure of an alarm, keyword check found nothing."""
    out = [res("keywords", trade=fs(0.0, 0.25, reason="Keine Stichwörter gefunden"), access=fs(0.0, 0.25)),
           res("llm_judge", trade=fs(0.95, 0.9, "present", "Kunde will vor der Meldung kaufen.", ["S002"]),
               access=fs(0.05, 0.9, "absent"))]
    if geval_conf is not None:
        out.append(res("geval", trade=fs(0.9, geval_conf), access=fs(0.1, geval_conf)))
    return out


# -- N14: abstain_on_empty -------------------------------------------------------------------------


def test_n14_known_answer_llm_alarm_without_keywords():
    calls = no_keyword_alarm()
    d0 = decide(calls)
    # v1: the keyword "0" pulls the mean to 0.87 and the disagreement to 0.54 -> uncertainty 0.40 > 0.35
    assert d0.label == "review" and d0.score == pytest.approx(0.8658, abs=1e-3)
    assert d0.uncertainty == pytest.approx(0.404, abs=2e-3)
    d1 = decide(calls, abstain_on_empty=True)
    assert d1.label == "alarm"
    assert d1.score == pytest.approx(0.95) and d1.uncertainty == pytest.approx(0.05, abs=1e-4)
    assert "keywords" not in d1.families["trade"].per_check and "keywords" in d0.families["trade"].per_check


@pytest.mark.parametrize("conf,v1", [(0.4, "review"), (0.6, "review"), (0.8, "alarm")])
def test_n14_table_from_ideas(conf, v1):
    calls = no_keyword_alarm(conf)
    assert decide(calls).label == v1
    assert decide(calls, abstain_on_empty=True).label == "alarm"


def test_abstain_keeps_rule_hits_and_llm_zeros():
    hit = Finding(check="keywords", family="trade", score=0.6, segment_ids=["S001"], start=10.0, end=12.0,
                  reason="Stichwort K04")
    calls = [res("keywords", findings=[hit], trade=fs(0.6, 0.6, segs=["S001"])),
             res("llm_judge", trade=fs(0.0, 0.9, "absent"))]
    assert decide(calls, abstain_on_empty=True).families["trade"] == decide(calls).families["trade"]


def test_abstain_when_only_empty_rule_checks_changes_nothing():
    calls = [res("keywords", trade=fs(0.0, 0.25)), res("patterns", trade=fs(0.0, 0.3))]
    assert decide(calls, abstain_on_empty=True).model_dump() == decide(calls).model_dump()


def test_rule_checks_by_type_or_name():
    calls = [res("kw_de", "keywords", trade=fs(0.0, 0.25)), res("llm_judge", trade=fs(0.95, 0.9))]
    d = decide(calls, {"weights": {"kw_de": 0.35}}, abstain_on_empty=True)
    assert d.score == pytest.approx(0.95)
    d2 = decide([res("mykw", trade=fs(0.0, 0.25)), res("llm_judge", trade=fs(0.95, 0.9))],
                {"weights": {"mykw": 0.35}}, abstain_on_empty=True, rule_checks=["mykw"])
    assert d2.score == pytest.approx(0.95)


def test_uncertainty_from_llm_ignores_rule_disagreement_but_not_in_score():
    hit = Finding(check="keywords", family="trade", score=0.8, segment_ids=["S001"], reason="K04")
    calls = [res("keywords", findings=[hit], trade=fs(0.8, 0.6)), res("llm_judge", trade=fs(0.1, 0.9)),
             res("geval", trade=fs(0.2, 0.8))]
    d0, d1 = decide(calls), decide(calls, uncertainty_from="llm")
    assert d1.families["trade"].score == d0.families["trade"].score
    # llm 0.1 (eff 0.9) and geval 0.2 (eff 0.8): mean 0.147, std 0.05 -> disagreement 0.0998;
    # mean confidence (0.9 + 0.8) / 2 = 0.85 -> uncertainty 0.5 * 0.0998 + 0.5 * 0.15
    assert d1.families["trade"].uncertainty == pytest.approx(0.5 * 0.0998 + 0.075, abs=1e-3)
    assert d1.families["trade"].uncertainty < d0.families["trade"].uncertainty
    with pytest.raises(ValueError, match="uncertainty_from"):
        WeightedFusion(CTX, uncertainty_from="rules")


def test_defaults_keep_v1_params_and_numbers():
    f = WeightedFusion(CTX)
    assert set(f.params) == {"threshold", "review_band", "max_uncertainty", "min_score_for_review",
                             "max_passages", "merge_gap", "max_passage_seconds"}
    explicit = WeightedFusion(CTX, abstain_on_empty=False, uncertainty_from="all", family_thresholds=None)
    assert explicit.params == f.params
    calls = no_keyword_alarm(0.5)
    o = {"weights": W}
    assert f.decide(transcript(), {r.check: r for r in calls}, FAMILIES, o).model_dump() == \
        explicit.decide(transcript(), {r.check: r for r in calls}, FAMILIES, o).model_dump()
    assert WeightedFusion(CTX, abstain_on_empty=True).params["abstain_on_empty"] is True


# -- N2: per-family thresholds ---------------------------------------------------------------------


def test_family_thresholds_margin_slider_shift_and_reason(tmp_path):
    calls = [res("llm_judge", trade=fs(0.5, 1.0, reason="Kaufwunsch"), access=fs(0.45, 1.0, reason="PIN"))]
    d = decide(calls, threshold=0.55, family_thresholds={"access": 0.4})
    # access is 0.05 over its own line, trade 0.05 under the global 0.55 -> access decides, alarm
    assert d.top_family == "access" and d.label == "alarm" and d.threshold == pytest.approx(0.4)
    assert any("Schwelle je Familie" in r and "0.40" in r for r in d.reasons)
    # the officer slider (+0.1) moves every family threshold: access 0.50 -> 0.45 is in the band -> review
    d2 = decide(calls, {"threshold": 0.65}, threshold=0.55, family_thresholds={"access": 0.4})
    assert d2.label == "review" and d2.threshold == pytest.approx(0.5)
    # same from a fitted file; overrides can replace the block
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"kind": "thresholds", "family_thresholds": {"access": 0.4}}))
    assert decide(calls, threshold=0.55, family_thresholds=str(p)).label == "alarm"
    assert decide(calls, {"family_thresholds": {"access": 0.9}}, threshold=0.55).label == "review"


def test_fit_family_thresholds_controls_family_fpr():
    feats, truth = [], {}
    rng = np.random.default_rng(0)
    for i in range(80):
        cid = f"Stufe1_X{i:02d}-K1"
        pos = i < 10
        truth[cid] = mk_call(cid, "alarm" if pos else "no_alert", "trade")
        f = F.CallFeatures(call_id=cid, fams=["trade", "access"])
        f.fused = {"trade": (float(rng.uniform(0.6, 0.9) if pos else rng.uniform(0.0, 0.5)), 0.1),
                   "access": (float(rng.uniform(0.0, 0.3)), 0.1)}
        feats.append(f)
    m = F.fit_model("thresholds", feats, truth, max_fpr=0.05)
    t = m["family_thresholds"]["trade"]
    negs = np.array([f.fused["trade"][0] for f in feats[10:]])
    assert np.mean(negs >= t) <= 0.05 and 0.3 < t <= 0.6
    assert m["family_stats"]["trade"]["pos_recall"] == 1.0
    assert m["train_dialogues"] and m["kind"] == "thresholds"


# -- numerics: logistic, Platt, softmax, conformal ---------------------------------------------------


def test_logreg_and_platt_recover_known_parameters():
    rng = np.random.default_rng(1)
    s = rng.uniform(0, 1, 6000)
    y = (rng.uniform(0, 1, len(s)) < F.sigmoid(8 * s - 4)).astype(float)
    a, b = F.platt_fit(s, y, l2=0.0)
    assert a == pytest.approx(8.0, rel=0.15) and b == pytest.approx(-4.0, rel=0.15)
    # calibrated: in each score bin the predicted probability matches the observed rate
    p = F.sigmoid(a * s + b)
    for lo in np.arange(0, 1, 0.2):
        m = (s >= lo) & (s < lo + 0.2)
        assert abs(p[m].mean() - y[m].mean()) < 0.05


def test_platt_stays_finite_on_separable_scores():
    a, b = F.platt_fit([0, 0, 0, 0, 0.6, 0.7], [0, 0, 0, 0, 1, 1])
    p0, p1 = F.sigmoid(b), F.sigmoid(0.6 * a + b)
    assert np.isfinite(a) and 0.05 < p0 < 0.3 and 0.6 < p1 < 0.95  # Platt targets 1/6 and 3/4


def test_softmax_fits_ordinal_classes():
    rng = np.random.default_rng(2)
    z = rng.normal(0, 2, 900)
    cls = np.digitize(z + rng.normal(0, 0.5, len(z)), [-1.0, 1.0])  # 0 low, 1 middle, 2 high
    X = np.column_stack([np.ones_like(z), z, z * z / 10])
    Wm = F.fit_softmax(X, np.eye(3)[cls], l2=0.01)
    P = F.softmax(X @ Wm.T)
    assert np.allclose(P.sum(axis=1), 1)
    assert (P.argmax(axis=1) == cls).mean() > 0.8
    mid = np.argmin(np.abs(z))
    assert P[mid].argmax() == 1  # the square term lets the middle class win in the middle


def test_conformal_quantile_known_answers():
    s = [i / 10 for i in range(1, 11)]
    assert F.conformal_qhat(s, 0.1) == pytest.approx(1.0)  # ceil(11 * 0.9) = 10th smallest
    assert F.conformal_qhat(s, 0.2) == pytest.approx(0.9)  # ceil(11 * 0.8) = 9th
    assert F.conformal_qhat([], 0.1) == 1.0
    assert F.conformal_qhat([0.5] * 5, 0.1) == 1.0  # too few points for alpha 0.1: everything plausible


def test_conformal_sets_cover_at_level():
    rng = np.random.default_rng(3)

    def draw(n):
        q = rng.uniform(0, 1, n)
        return q, np.where(rng.uniform(0, 1, n) < q, "alarm", "no_alert")
    model = {"conformal": {"labels": 2}}
    qc, yc = draw(500)
    model["conformal"].update(alpha=0.1, scores=sorted(F.nonconformity(model, q, y) for q, y in zip(qc, yc)))
    qt, yt = draw(4000)
    sets = [F.prediction_set(model, F.class_probs(model, q)) for q in qt]
    coverage = np.mean([y in s for y, s in zip(yt, sets)])
    assert 0.87 <= coverage <= 0.95
    sizes = {len(s) for s in sets}
    assert 2 in sizes and 1 in sizes  # unsure middle, sure ends
    both = [q for q, s in zip(qt, sets) if len(s) == 2]
    assert 0.05 < min(both) and max(both) < 0.95  # the "review" region is an interval around 0.5


# -- synthetic calls for the fitted fusions -------------------------------------------------------


def mk_call(cid: str, label: str, family: str) -> Call:
    did = cid.split("-K")[0]
    return Call(call_id=cid, dialogue_id=did, level=int(did[5]) if did[5].isdigit() else 1, variant=1,
                noisy=cid.endswith("K2"), audio_path=Path(f"/nonexistent/{cid}.wav"),
                expected=Expected(label=label, family=family, event="", reason="", open_question=""))


def synth(n_folds: int = 4, per_fold: int = 6, seed: int = 4, holdout: int = 2):
    """Dialogues (clean + noisy) with LLM scores that separate alarm / review / no_alert reasonably, and
    keywords that fire on half of the trade calls (alarms and harmless explanations alike)."""
    rng = np.random.default_rng(seed)
    calls, results, fold_of, holdout_d = [], [], {}, []
    kinds = [("alarm", "trade"), ("no_alert", "trade"), ("alarm", "access"), ("no_alert", "access"),
             ("review", "access"), ("no_alert", "numbers")]
    idx = 0
    for k in range(n_folds + 1):
        for j in range(per_fold if k < n_folds else holdout):
            label, fam = kinds[j % len(kinds)]
            did = f"Stufe1_D{idx:02d}"
            idx += 1
            if k < n_folds:
                fold_of[did] = k
            else:
                holdout_d.append(did)
            for v in (1, 2):
                cid = f"{did}-K{v}"
                calls.append(mk_call(cid, label, fam))
                level = {"alarm": 0.85, "review": 0.5, "no_alert": 0.15}[label]
                llm = {}
                for f in ("trade", "access"):
                    mu = level if f == fam else 0.08
                    llm[f] = fs(float(np.clip(mu + rng.normal(0, 0.08), 0, 1)), 0.8)
                kw_hit = fam == "trade" and rng.uniform() < 0.5
                kw_find = [Finding(check="keywords", family="trade", score=0.6, segment_ids=["S001"],
                                   start=10.0, end=12.0, reason="K04")] if kw_hit else []
                checks = {
                    "keywords": res("keywords", findings=kw_find, trade=fs(0.6 if kw_hit else 0.0, 0.6 if kw_hit else 0.25),
                                    access=fs(0.0, 0.25)),
                    "llm_judge": res("llm_judge", **llm),
                    "geval": res("geval", **{f: fs(float(np.clip(x.score + rng.normal(0, 0.1), 0, 1)), 0.5)
                                             for f, x in llm.items()}),
                }
                t = transcript(cid)
                d = WeightedFusion(CTX).decide(t, checks, FAMILIES, {"weights": W})
                results.append(CallResult(call_id=cid, transcript=t, checks=checks, decision=d))
    return calls, results, fold_of, holdout_d


def feats_truth(results, calls, base=None):
    wf = WeightedFusion(CTX, **(base or {}))
    return [F.features_of(wf, r, FAMILIES, W) for r in results], {c.call_id: c for c in calls}


@pytest.fixture(scope="module")
def data():
    return synth()


def test_calibrated_fit_decide_matches_pure_rule_and_threshold_moves_cut(data):
    calls, results, fold_of, holdout = data
    dev = [r for r in results if r.call_id.split("-K")[0] in fold_of]
    feats, truth = feats_truth(dev, calls)
    model = F.fit_model("calibrated", feats, truth, fold_of, checks=list(W), weights=W, labels=2)
    assert model["conformal"]["n"] == len(dev) and "cross-conformal" in model["conformal"]["source"]
    assert not set(model["train_dialogues"]) & set(holdout)
    fusion = CalibratedFusion(CTX, model=model)
    test = [r for r in results if r.call_id.split("-K")[0] in holdout]
    for r in test + dev[:6]:
        d = fusion.decide(r.transcript, r.checks, FAMILIES, {"weights": W})
        f = F.features_of(WeightedFusion(CTX), r, FAMILIES, W)
        v = F.fitted_verdict(model, f, 0.5, 0.15)
        assert d.label == v.label and d.score == pytest.approx(v.score, abs=1e-4)
        assert 0 <= d.score <= 1 and d.threshold == 0.5
    # alarms get high calibrated probability, harmless calls low
    q = {r.call_id: fusion.decide(r.transcript, r.checks, FAMILIES).score for r in dev}
    alarms = [q[c.call_id] for c in calls if c.call_id in q and c.expected.label == "alarm"]
    harmless = [q[c.call_id] for c in calls if c.call_id in q and c.expected.label == "no_alert"]
    assert np.mean(alarms) > 0.6 and np.mean(harmless) < 0.3
    # the officer threshold moves the alarm cut: a sure alarm stops being one at threshold 0.99
    sure = max(dev, key=lambda r: q[r.call_id])
    model_noconf = {**model, "conformal": {**model["conformal"], "scores": [0.5] * 40}}  # sets = {argmax}
    f2 = CalibratedFusion(CTX, model=model_noconf)
    assert f2.decide(sure.transcript, sure.checks, FAMILIES).label == "alarm"
    assert f2.decide(sure.transcript, sure.checks, FAMILIES, {"threshold": 0.99}).label != "alarm"


def test_calibrated_conformal_review_reason():
    model = {"kind": "calibrated", "checks": ["llm_judge"], "weights": {"llm_judge": 1.0}, "base": {},
             "platt": {"llm_judge": {"_pooled": [1.0, 0.0]}}, "pool": [4.0, -2.0],
             "conformal": {"alpha": 0.1, "labels": 2, "scores": [0.6] * 30}}
    calls = [res("llm_judge", trade=fs(0.5, 0.8), access=fs(0.0, 0.8))]
    d = CalibratedFusion(CTX, model=model).decide(transcript(), {r.check: r for r in calls}, FAMILIES)
    # q = sigmoid(4 * 0.5 - 2) = 0.5: both 1 - q and q are <= qhat 0.6 -> {alarm, no_alert}
    assert d.label == "review" and d.score == pytest.approx(0.5, abs=1e-3)
    assert d.reasons[0].startswith("Prüfen (unsicher: {alarm, no_alert} beide plausibel)")
    # alpha from the config: a looser level (fewer points needed) does not change these equal scores
    assert CalibratedFusion(CTX, model=model, alpha=0.5).decide(
        transcript(), {r.check: r for r in calls}, FAMILIES).label == "review"


def test_fitted_fusion_falls_back_to_weighted_without_model(caplog):
    with caplog.at_level(logging.WARNING, logger="callguard"):
        f = CalibratedFusion(CTX, model="runs/fusion/does-not-exist.json", threshold=0.55)
    assert "falling back" in caplog.text
    calls = no_keyword_alarm()
    d = f.decide(transcript(), {r.check: r for r in calls}, FAMILIES, {"weights": W})
    ref = decide(calls)
    assert d.label == ref.label and d.score == ref.score
    assert "kein angepasstes Fusionsmodell" in d.reasons[-1]
    with pytest.raises(FileNotFoundError):
        F.load_model("runs/fusion/does-not-exist.json")


def test_learned_fusion_fits_and_explains(data):
    calls, results, fold_of, _ = data
    dev = [r for r in results if r.call_id.split("-K")[0] in fold_of]
    feats, truth = feats_truth(dev, calls)
    model = F.fit_model("learned", feats, truth, fold_of, checks=list(W), weights=W, l2=1.0)
    assert len(model["coef"]) == len(model["feature_names"]) == 2 + 2 * len(W)
    fusion = LearnedFusion(CTX, model=model)
    labels = {r.call_id: fusion.decide(r.transcript, r.checks, FAMILIES).label for r in dev}
    acc = np.mean([labels[c.call_id] == c.expected.label for c in calls if c.call_id in labels])
    assert acc > 0.6
    alarm = next(r for r in dev if truth[r.call_id].expected.label == "alarm" and r.checks["keywords"].findings)
    d = fusion.decide(alarm.transcript, alarm.checks, FAMILIES)
    assert any(x.startswith("Stärkste Beiträge") for x in d.reasons)
    assert d.passages and d.families["numbers"].score == alarm.decision.families["numbers"].score


def test_registry_knows_fitted_fusions():
    assert registry.resolve("fusion", "calibrated") is CalibratedFusion
    assert registry.resolve("fusion", "learned") is LearnedFusion


# -- nested CV ------------------------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["calibrated", "learned", "thresholds"])
def test_nested_cv_never_fits_on_test_fold_or_holdout(data, kind):
    calls, results, fold_of, holdout = data
    seen: list[set[str]] = []

    def spy(k, feats, truth, sub_fold, **kw):
        seen.append({f.dialogue for f in feats})
        assert set(sub_fold) == {f.dialogue for f in feats}  # the inner folds are the training folds
        return F.fit_model(k, feats, truth, sub_fold, **kw)

    out = F.nested_cv(kind, results, calls, fold_of, CTX, base={"threshold": 0.55}, weights=W, fit_fn=spy,
                      thresholds=[0.3, 0.4, 0.5, 0.6, 0.7])
    hold = set(holdout)
    folds = {k: {d for d, j in fold_of.items() if j == k} for k in set(fold_of.values())}
    assert len(seen) == len(out["fits"]) == 4 * (1 + 3)  # per outer fold: 3 inner + 1 outer fit
    for s, fit in zip(seen, out["fits"]):
        assert not s & hold
        assert not s & folds[fit["test_fold"]]
        assert s == set(fit["train_dialogues"])
    # every dev call predicted exactly once per row set, by a model that never saw its fold
    dev_calls = {c.call_id for c in calls if c.dialogue_id in fold_of}
    assert {r["call_id"] for r in out["cv"]} == dev_calls == {r["call_id"] for r in out["fixed"]}
    for r in out["cv"]:
        assert r["cv_fold"] == fold_of[r["dialogue_id"]] and r["cv_threshold"] in [0.3, 0.4, 0.5, 0.6, 0.7]
        assert r["dialogue_id"] not in out["cv_folds"][r["cv_fold"]]["train_dialogues"]
        assert {"passage", "reason", "predicted", "expected", "score"} <= set(r)
    # rows pair with weighted CV rows in stats
    from callguard import stats
    comp = stats.compare(out["fixed"], out["cv"], n_boot=200)
    assert comp["paired"]["_n"]["calls"] == len(dev_calls)


def test_nested_cv_refuses_a_model_that_saw_the_test_fold(data):
    calls, results, fold_of, _ = data

    def leaky(k, feats, truth, sub_fold, **kw):
        m = F.fit_model(k, feats, truth, sub_fold, **kw)
        m["train_dialogues"] = sorted(fold_of)  # claims to have seen everything
        return m

    with pytest.raises(F.LeakError):
        F.nested_cv("learned", results, calls, fold_of, CTX, base={}, weights=W, fit_fn=leaky, thresholds=[0.5])


# -- experiment plumbing (case data) ----------------------------------------------------------------


DATA = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/data"
SPLITS = Path(__file__).resolve().parents[1] / "config/splits.yaml"


@pytest.mark.skipif(not DATA.exists() or not SPLITS.exists(), reason="case data / splits not available")
def test_refuse_variants_and_fusion_cv_on_offline_experiment(tmp_path):
    from callguard import experiments as ex
    from callguard.commands.fit_fusion import fit_from_experiment, fusion_cv_from_experiment
    from callguard.data import load_calls

    raw = {"name": "fz", "base": "demo-offline", "split": "dev", "compare_to": "all", "variants": [
        {"name": "all", "set": [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}"]},
        {"name": "abstain", "refuse_from": "all", "set": ["fusion.abstain_on_empty=true",
                                                           "fusion.uncertainty_from=llm"]}]}
    spec = ex.parse_spec(raw)
    ids = ["Stufe1_D01-K1", "Stufe1_D02-K1", "Stufe1_D04-K1", "Stufe1_D05-K1", "Stufe2_C03-K3", "Stufe2_C05-K3",
           "Stufe2_C09-K3", "Stufe3_C17-K1", "Stufe3_C18-K1", "Stufe1_D06-K1", "Stufe1_D08-K1"]
    calls = [c for c in load_calls(DATA) if c.call_id in ids]
    summary = ex.run_experiment(spec, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=200)
    assert set(summary["variants"]) == {"all", "abstain"}
    path, model, src = fit_from_experiment("thresholds", "fz", "all", runs_dir=tmp_path / "runs", spec=spec)
    assert path.exists() and "Stufe2_C03" not in model["train_dialogues"]  # holdout dropped
    assert src["dropped_holdout"] == ["Stufe2_C03-K3"]
    out = fusion_cv_from_experiment("learned", "fz", "abstain", runs_dir=tmp_path / "runs", spec=spec,
                                    n_boot=200, l2=1.0, review_target=0.5)
    vdir = out["dir"]
    assert (vdir / "rows.json").exists() and (vdir / "compare_abstain.md").exists()
    rows = json.loads((vdir / "rows.json").read_text())
    assert rows["cv"] and all(r["call_id"] != "Stufe2_C03-K3" for r in rows["cv"])
    assert out["comparison"]["cv"]["paired"]["_n"]["calls"] == len(rows["cv"])
