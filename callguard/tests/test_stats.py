from __future__ import annotations

import math

import numpy as np
import pytest

from callguard import stats


def row(call_id, expected, predicted, score=0.5, reason=None, passage=None):
    return {"call_id": call_id, "dialogue_id": call_id.split("-K")[0], "expected": expected,
            "predicted": predicted, "score": score, "reason": reason, "passage": passage}


def pair(d, expected, predicted):
    """Clean + noisy call of one dialogue with the same outcome."""
    return [row(f"{d}-K1", expected, predicted), row(f"{d}-K2", expected, predicted)]


# -- point metrics ---------------------------------------------------------------------------------


def test_point_metrics_known_answer():
    rows = [row("A-K1", "alarm", "alarm"), row("B-K1", "alarm", "review"), row("C-K1", "alarm", "no_alert"),
            row("D-K1", "review", "review"), row("E-K1", "review", "no_alert"), row("F-K1", "no_alert", "alarm"),
            row("G-K1", "no_alert", "no_alert"), row("H-K1", "no_alert", "no_alert"),
            row("X-K1", None, "alarm")]  # unlabelled: ignored
    p = stats.point(rows)
    # flag: tp = A, B, D = 3; fn = C, E = 2; fp = F = 1; tn = G, H = 2
    assert p["flag_f1"] == pytest.approx(round(6 / 9, 4))
    assert p["flag_precision"] == 0.75 and p["flag_recall"] == 0.6
    assert p["false_alarm_rate"] == pytest.approx(round(1 / 3, 4)) and p["miss_rate"] == 0.4
    # alarm: tp = A; fp = F; fn = B, C -> 2/(2+1+2)
    assert p["alarm_f1"] == 0.4
    assert p["review_recall"] == 0.5  # D yes, E no
    assert p["accuracy"] == 0.5  # A, D, G, H


def test_undefined_metrics_are_none():
    p = stats.point([row("A-K1", "no_alert", "no_alert")])
    assert p["flag_f1"] is None and p["miss_rate"] is None and p["false_alarm_rate"] == 0.0


# -- bootstrap -------------------------------------------------------------------------------------


def test_bootstrap_ci_degenerate_when_all_dialogues_alike():
    rows = [r for i in range(10) for r in pair(f"D{i:02d}", "alarm", "alarm")]
    ci = stats.bootstrap_ci(rows, n_boot=500)
    assert ci["flag_f1"] == {"value": 1.0, "lo": 1.0, "hi": 1.0, "n_valid": 500}
    assert ci["false_alarm_rate"]["value"] is None and ci["false_alarm_rate"]["n_valid"] == 0


def test_bootstrap_ci_brackets_point_and_is_seeded():
    rows = []
    for i in range(12):
        rows += pair(f"P{i:02d}", "alarm", "alarm" if i % 3 else "no_alert")
        rows += pair(f"N{i:02d}", "no_alert", "review" if i % 4 == 0 else "no_alert")
    a = stats.bootstrap_ci(rows, n_boot=2000, seed=1)
    b = stats.bootstrap_ci(rows, n_boot=2000, seed=1)
    assert a == b
    for k in ("flag_f1", "false_alarm_rate", "miss_rate", "accuracy"):
        assert a[k]["lo"] <= a[k]["value"] <= a[k]["hi"]
    assert a["flag_f1"]["hi"] - a["flag_f1"]["lo"] > 0.05


def test_resampling_unit_is_the_dialogue():
    rows = pair("A", "alarm", "alarm") + pair("B", "no_alert", "alarm")
    ids, per = stats._by_dialogue(rows)
    assert ids == ["A", "B"] and per.shape[0] == 2
    assert per[:, stats._I["n"]].tolist() == [2, 2]


# -- paired comparison ---------------------------------------------------------------------------


def test_paired_bootstrap_identical_variants_has_zero_diff():
    rows = []
    for i in range(10):
        rows += pair(f"D{i:02d}", "alarm" if i < 5 else "no_alert", "alarm" if i % 2 else "no_alert")
    p = stats.paired_bootstrap(rows, [dict(r) for r in rows], n_boot=1000)
    assert p["flag_f1"]["diff"] == 0 and p["flag_f1"]["lo"] == 0 and p["flag_f1"]["hi"] == 0
    assert not p["flag_f1"]["real"]
    assert p["_n"] == {"calls": 20, "units": 10, "dialogues": 10}


def test_paired_bootstrap_detects_a_clear_win():
    a, b = [], []
    for i in range(15):
        exp = "alarm" if i < 8 else "no_alert"
        a += pair(f"D{i:02d}", exp, "no_alert" if exp == "alarm" else "alarm")  # always wrong
        b += pair(f"D{i:02d}", exp, exp)  # always right
    p = stats.paired_bootstrap(a, b, n_boot=2000)
    assert p["flag_f1"]["diff"] == 1.0 and p["flag_f1"]["real"] and p["flag_f1"]["better"] == "b"
    assert p["false_alarm_rate"]["diff"] == -1.0 and p["false_alarm_rate"]["better"] == "b"
    assert p["false_alarm_rate"]["hi"] < 0


def test_paired_bootstrap_pairs_by_call_id_only():
    a = pair("A", "alarm", "alarm") + pair("B", "no_alert", "no_alert")
    b = pair("B", "no_alert", "alarm")  # only B evaluated in the other variant
    p = stats.paired_bootstrap(a, b, n_boot=200)
    assert p["_n"] == {"calls": 2, "units": 1, "dialogues": 1}


# -- McNemar ----------------------------------------------------------------------------------------


def test_binom_two_sided_known_values():
    assert stats.binom_two_sided(0, 0) == 1.0
    assert stats.binom_two_sided(0, 5) == pytest.approx(2 / 32)
    assert stats.binom_two_sided(1, 5) == pytest.approx(2 * 6 / 32)
    assert stats.binom_two_sided(5, 5) == pytest.approx(2 / 32)
    assert stats.binom_two_sided(3, 6) == 1.0
    # 0 of 10 discordant pairs in favour of one side: 2 / 1024
    assert stats.binom_two_sided(0, 10) == pytest.approx(2 / 1024)


def test_mcnemar_counts_and_p():
    a = [row("A-K1", "alarm", "alarm"), row("B-K1", "alarm", "no_alert"), row("C-K1", "no_alert", "alarm"),
         row("D-K1", "no_alert", "no_alert"), row("E-K1", "review", "alarm")]
    b = [row("A-K1", "alarm", "no_alert"), row("B-K1", "alarm", "review"), row("C-K1", "no_alert", "no_alert"),
         row("D-K1", "no_alert", "no_alert"), row("E-K1", "review", "review")]
    m = stats.mcnemar(a, b, stats.flag_correct)
    assert (m["a_only"], m["b_only"], m["both"], m["neither"]) == (1, 2, 2, 0)
    assert m["p"] == pytest.approx(1.0)
    ml = stats.mcnemar(a, b, stats.label_correct)  # 3-class: A right on A-K1, D; B right on C, D, E
    assert (ml["a_only"], ml["b_only"], ml["both"]) == (1, 2, 1)


def test_flips_lists_changed_calls_with_reasons():
    a = [row("A-K1", "alarm", "no_alert", 0.3, "a: nothing"), row("B-K1", "no_alert", "no_alert", 0.1)]
    b = [row("A-K1", "alarm", "alarm", 0.8, "b: Kauf vor Meldung", "00:12-00:20 trade: ..."),
         row("B-K1", "no_alert", "no_alert", 0.1)]
    f = stats.flips(a, b)
    assert len(f) == 1
    assert f[0]["call_id"] == "A-K1" and f[0]["flag_change"] == "fixed" and f[0]["label_change"] == "fixed"
    assert f[0]["b_reason"] == "b: Kauf vor Meldung" and f[0]["b_passage"].startswith("00:12")
    assert f[0]["a_score"] == 0.3 and f[0]["b_score"] == 0.8


def test_compare_bundle():
    a = pair("A", "alarm", "no_alert") + pair("B", "no_alert", "no_alert")
    b = pair("A", "alarm", "alarm") + pair("B", "no_alert", "no_alert")
    c = stats.compare(a, b, n_boot=300)
    assert set(c) == {"paired", "auc", "mcnemar_flag", "mcnemar_label", "flips"}
    assert c["mcnemar_flag"]["b_only"] == 2 and len(c["flips"]) == 2
    assert not math.isnan(c["paired"]["accuracy"]["diff"])


def test_metric_functions_vectorised():
    c = np.array([stats._counts(row("A-K1", "alarm", "alarm")), stats._counts(row("B-K1", "no_alert", "alarm"))])
    f1 = stats.METRICS["flag_f1"](c)  # per row: 1.0 and 0.0
    assert f1.tolist() == [1.0, 0.0]


def test_bootstrap_resamples_twin_groups():
    rows = [{**r, "group": "T1"} for r in pair("C01", "alarm", "alarm") + pair("C02", "no_alert", "alarm")]
    rows += pair("D05", "alarm", "no_alert")
    ids, per = stats._by_dialogue(rows)
    assert ids == ["T1", "D05"] and per[:, stats._I["n"]].tolist() == [4, 2]
    p = stats.paired_bootstrap(rows, rows, n_boot=50)
    assert p["_n"] == {"calls": 6, "units": 2, "dialogues": 3}


def test_case_twins_share_a_unit_via_splits_yaml():
    from callguard import splits as sp
    s = sp.load_splits(required=False)
    if not s or not s.groups:
        pytest.skip("no twin groups in config/splits.yaml")
    g, ds = next(iter(s.groups.items()))
    assert stats._dialogue(row(f"{ds[0]}-K1", "alarm", "alarm")) == stats._dialogue(row(f"{ds[1]}-K2", "alarm", "alarm")) == g


# -- AUC, balanced accuracy, floor -------------------------------------------------------------------


def scored(call_id, expected, score):
    return row(call_id, expected, "alarm", score)


def test_auc_known_answer():
    rows = [scored("A-K1", "alarm", 0.9), scored("B-K1", "review", 0.6), scored("C-K1", "no_alert", 0.7),
            scored("D-K1", "no_alert", 0.1), scored("E-K1", "alarm", 0.5)]
    # flag: pos .9 .6 .5 vs neg .7 .1 -> 4 of 6 pairs ordered right
    assert stats.auc(rows) == pytest.approx(0.6667, abs=1e-4)
    # alarm: pos .9 .5 vs neg .6 .7 .1 -> 4 of 6
    assert stats.auc(rows, "alarm") == pytest.approx(0.6667, abs=1e-4)
    ties = [scored("A-K1", "alarm", 0.5), scored("B-K1", "no_alert", 0.5)]
    assert stats.auc(ties) == 0.5
    perfect = [scored(f"P{i}-K1", "alarm", 0.8 + i / 100) for i in range(5)] + \
              [scored(f"N{i}-K1", "no_alert", 0.1 + i / 100) for i in range(5)]
    b = stats.bootstrap_auc(perfect, n_boot=300)
    assert b["flag"]["value"] == 1.0 and b["flag"]["lo"] == 1.0 and b["flag"]["n_pos"] == 5
    assert b["alarm"]["value"] == 1.0
    assert stats.auc([row("A-K1", "alarm", "review", None)]) is None  # error rows have no score


def test_paired_auc_detects_better_ranking():
    a, b = [], []
    for i in range(12):
        exp = "alarm" if i % 2 else "no_alert"
        for k in (1, 2):
            a.append(scored(f"D{i:02d}-K{k}", exp, 0.5))  # constant score: AUC 0.5
            b.append(scored(f"D{i:02d}-K{k}", exp, 0.9 if exp == "alarm" else 0.1))
    p = stats.paired_auc(a, b, n_boot=500)
    assert p["flag"]["a"] == 0.5 and p["flag"]["b"] == 1.0 and p["flag"]["diff"] == 0.5
    assert p["flag"]["real"] and p["flag"]["better"] == "b" and p["flag"]["lo"] > 0
    same = stats.paired_auc(b, b, n_boot=200)
    assert same["flag"]["diff"] == 0 and not same["flag"]["real"]


def test_balanced_accuracy_and_trivial_baselines():
    rows = [row("A-K1", "alarm", "alarm"), row("B-K1", "review", "no_alert"), row("C-K1", "no_alert", "alarm"),
            row("D-K1", "no_alert", "no_alert")]
    assert stats.point(rows)["flag_balanced_accuracy"] == 0.5  # recall 1/2, specificity 1/2
    t = stats.trivial_baselines(rows)
    assert t["flag_all"]["flag_f1"] == pytest.approx(round(2 * 2 / (2 * 2 + 2), 4))
    assert t["flag_all"]["false_alarm_rate"] == 1.0 and t["flag_all"]["flag_balanced_accuracy"] == 0.5
    assert t["flag_none"]["flag_f1"] == 0.0 and t["flag_none"]["miss_rate"] == 1.0
    assert t["_n"] == {"calls": 4, "prevalence_flag": 0.5}
