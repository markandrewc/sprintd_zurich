"""dual_eval (callguard dualfacts eval): grid, champion, metric / paired block shapes, agreement counts, UI one-liners,
and the test50 guard of the CLI. Synthetic, offline, no stored runs."""
from __future__ import annotations

import pytest
from typer.testing import CliRunner

from callguard import dual_eval as de
from callguard import fact_policy as fpol

DEFAULT = fpol.default_policy()


def rows(preds: list[tuple[str, str, float]]) -> list[dict]:
    """(expected, predicted, score) -> eval rows, two calls per twin group."""
    return [{"call_id": f"D{i}-K1", "dialogue_id": f"D{i}", "group": f"g{i // 2}", "expected": e, "predicted": p,
             "score": s} for i, (e, p, s) in enumerate(preds)]


BASE = rows([("alarm", "alarm", 0.9), ("alarm", "review", 0.6), ("review", "review", 0.5), ("review", "alarm", 0.7),
             ("no_alert", "no_alert", 0.1), ("no_alert", "review", 0.4), ("no_alert", "no_alert", 0.2),
             ("no_alert", "no_alert", 0.05)])
VARIANT = rows([("alarm", "alarm", 0.9), ("alarm", "no_alert", 0.3), ("review", "review", 0.5), ("review", "review", 0.6),
                ("no_alert", "no_alert", 0.1), ("no_alert", "no_alert", 0.2), ("no_alert", "no_alert", 0.2),
                ("no_alert", "no_alert", 0.05)])


def test_grid_is_bands_times_combinations():
    g = de.grid(DEFAULT)
    assert len(g) == 12
    assert {p.combination for p in g} == set(fpol.COMBINATIONS)
    assert {(p.b.lo, p.b.hi) for p in g} == set(de.GRID_BANDS)
    assert all(p.a.mode == "three_way" for p in g)  # Qwen stays three-way
    assert len({de.setting_name(p) for p in g}) == 12


def test_champion_is_only_a_and_default_is_preregistered():
    ch = de.champion_v3()
    assert ch.combination == "only_a"
    assert ch.a == DEFAULT.a and ch.b == DEFAULT.b
    assert DEFAULT.combination == "agree" and (DEFAULT.b.mode, DEFAULT.b.lo, DEFAULT.b.hi) == ("band", 0.3, 0.7)
    flags = [de.flag_entry({}, p, DEFAULT) for p in de.grid(DEFAULT)]
    assert sum(f["default"] for f in flags) == 1
    assert sum(f["champion_v3"] for f in flags) == 1
    assert sum(f["equivalent_to_champion_v3"] for f in flags) == 3


def test_metric_block_shape():
    b = de.metric_block(BASE, n_boot=50)
    assert b["n"] == 8 and b["units"] == 4
    assert (b["flagged"], b["alarms"], b["reviews"]) == (5, 2, 3)
    for k in (*de.METRICS, "auc"):
        assert set(b[k]) == {"value", "lo", "hi"}
    assert b["false_alarm_rate"]["value"] == pytest.approx(0.25)
    assert b["miss_rate"]["value"] == pytest.approx(0.0)


def test_paired_block_shape_and_flips():
    p = de.paired_block(BASE, VARIANT, n_boot=50)
    for k in (*de.METRICS, "auc"):
        assert {"a", "b", "diff", "lo", "hi", "real"} <= set(p[k])
    assert p["changed"] == 3
    assert {f["call_id"] for f in p["flips"]} == {"D1-K1", "D3-K1", "D5-K1"}
    assert p["false_alarm_rate"]["diff"] == pytest.approx(-0.25)
    assert p["miss_rate"]["diff"] == pytest.approx(0.25)
    assert set(p["mcnemar_flag"]) >= {"a_only", "b_only", "p"}


def test_label_diff():
    d = de.label_diff(BASE, VARIANT)
    assert d["n"] == 8 and d["differ"] == 3 and d["missing"] == []
    assert de.label_diff(BASE, BASE)["differ"] == 0


def test_agreement_counts_tiny():
    q = lambda y, n: {"yes": y, "no": n, "unclear": round(1 - y - n, 4)}  # noqa: E731
    k = lambda y: {"yes": y, "no": round(1 - y, 4), "unclear": 0.0}  # noqa: E731
    answers = [("f", "a", q(0.9, 0.05), k(0.95)),   # ja / ja
               ("f", "a", q(0.05, 0.9), k(0.9)),    # nein / ja -> contradiction
               ("f", "a", q(0.3, 0.3), k(0.5)),     # unklar / unklar (band)
               ("f", "a", q(0.1, 0.8), None)]       # Kev missing
    a = de.agreement_counts(answers, DEFAULT)
    assert a["answers"] == 4 and a["both"] == 3
    assert a["a"] == {"yes": 1, "no": 2, "unclear": 1}
    assert a["b"] == {"yes": 2, "no": 0, "unclear": 1}
    assert a["disagree"] == 1 and a["contradict"] == 1
    assert a["combined"]["yes"] == 1  # agree: only both-ja stays ja
    narrow = de.agreement_counts(answers, de.kev_band(DEFAULT, 0.4, 0.6))
    assert narrow["b"]["unclear"] == 1  # 0.5 is inside [0.4, 0.6] too


def test_ui_text_keys_and_numbers():
    fixed = {**de.metric_block(BASE, n_boot=20)}
    entries = [de.flag_entry(de.grid_entry(de.setting_name(p), p, fixed, None), p, DEFAULT) for p in de.grid(DEFAULT)]
    t = de.ui_text(entries, DEFAULT)
    assert set(t["combination"]) == set(fpol.COMBINATIONS)
    assert set(t["band"]) == {"0.2-0.8", "0.3-0.7", "0.4-0.6"}
    assert "Dev (8 Anrufe): 5 markiert" in t["combination"]["agree"]
    assert "FAR 25 %" in t["band"]["0.3-0.7"]


def test_cli_refuses_test50_without_flag(monkeypatch, tmp_path):
    from callguard.cli import app

    def boom(*a, **k):
        raise AssertionError("test50 must not be loaded without --test50-look")

    monkeypatch.setattr(de, "load_set", boom)
    sub = "eval"
    r = CliRunner().invoke(app, ["dualfacts", sub, "--set", "test50", "--out", str(tmp_path)])
    assert r.exit_code == 2, r.output
    assert "--test50-look" in r.output
    (tmp_path / "dual_facts_test50.json").write_text("{}")
    r = CliRunner().invoke(app, ["dualfacts", sub, "--set", "test50", "--test50-look", "--out", str(tmp_path)])
    assert r.exit_code == 2, r.output  # the one look is done: no silent second look


def test_compare_cli_guards_test50_and_names_profiles(monkeypatch, tmp_path):
    from callguard.cli import app

    seen = []

    def fake_load(name, profile=None, threshold=0.55, **k):
        seen.append((name, profile))
        raise RuntimeError("stop after the profile choice")

    monkeypatch.setattr(de, "load_set", fake_load)
    r = CliRunner().invoke(app, ["dualfacts", "compare", "--set", "test50", "--out", str(tmp_path)])
    assert r.exit_code == 2 and "--test50-look" in r.output and not seen
    (tmp_path / "sherlock_vs_dual_test50.json").write_text("{}")
    r = CliRunner().invoke(app, ["dualfacts", "compare", "--set", "test50", "--test50-look", "--out", str(tmp_path)])
    assert r.exit_code == 2 and not seen  # one look per candidate
    CliRunner().invoke(app, ["dualfacts", "compare", "--set", "test50", "--test50-look", "--name", "x",
                             "--out", str(tmp_path)])
    assert seen == [("test50", "dual-facts-test50")]  # base first; the candidate would be sherlock-test50
    seen.clear()
    CliRunner().invoke(app, ["dualfacts", "compare", "--set", "dev", "--out", str(tmp_path)])
    assert seen == [("dev", "dual-facts")]
