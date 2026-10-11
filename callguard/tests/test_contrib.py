"""callguard.contrib (paired factor comparisons over stored rows), `callguard contrib` and the
"Entscheidungshilfe" page. Offline: synthetic rows only, no models."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest
from typer.testing import CliRunner
from ui_fixtures import FixtureEnv, contrib_rows, write_contrib_fixture, write_contrib_variant, write_fixture_env

from callguard import cli
from callguard import contrib as cb
from callguard.ui import backend as be
from callguard.ui import contrib_view as cv

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"


def _spec(tmp: Path, **extra) -> dict:
    spec = {
        "name": "t", "rows": "cv", "n_boot": 300, "seed": 13, "reference": "e/base",
        "factors": [
            {"id": "design", "short": "Design", "title": "Design", "pairs": [
                {"label": "base → good", "a": "e/base", "b": "e/good", "status": "exact"},
                {"label": "base → same", "a": "e/base", "b": "e/same"},
                {"label": "base → other calls", "a": "e/base", "b": "x/other"},
            ]},
            {"id": "kev", "short": "Kev", "title": "Kev", "pending": True, "pairs": [
                {"label": "q → kev", "a": "kev_vs_facts/qwen_general", "b": "kev_vs_facts/kev_general", "pending": True},
            ]},
        ],
        "path": {"title": "p", "steps": [{"label": "s1", "a": "e/base", "b": "e/same"},
                                         {"label": "s2", "a": "e/copy", "b": "e/good"}]},
        "generalisation": [{"title": "T", "entries": [{"label": "dev", "ref": "e/base"},
                                                      {"label": "other", "ref": "x/other"},
                                                      {"label": "kev", "ref": "kev_vs_facts/kev_general", "pending": True}]}],
        "systems": [{"label": "Base", "ref": "e/base"}, {"label": "Good", "ref": "e/good"},
                    {"label": "Kev", "ref": "kev_vs_facts/kev_general", "pending": True}],
        "baselines": {"reference": "e/base", "keyword_only": "e/same",
                      "rerun": {"label": "rerun", "a": "e/base", "b": "e/same"}},
        "holdout": ["h/v"],
        **extra,
    }
    p = tmp / "contrib.yaml"
    p.write_text(yaml.safe_dump(spec, allow_unicode=True))
    return cb.load_spec(p)


@pytest.fixture
def data(tmp_path: Path) -> Path:
    root = tmp_path / "experiments"
    base = contrib_rows(0.5, seed=1)
    write_contrib_variant(root, "e/base", base)
    write_contrib_variant(root, "e/copy", base)
    write_contrib_variant(root, "e/same", base)
    # "good": every call right, flaggable calls score high -> AUC 1.0
    good = [{**r, "predicted": r["expected"], "score": 0.9 if r["expected"] != "no_alert" else 0.05} for r in base]
    write_contrib_variant(root, "e/good", good, check_weights={"facts": 1.0, "keywords": 0.15})
    write_contrib_variant(root, "x/other", contrib_rows(0.8, seed=2, prefix="Synth_o_"))
    write_contrib_variant(root, "h/v", contrib_rows(0.6, seed=3, n_dialogues=6))
    return root


# --------------------------------------------------------------------------------------------
# pairing and deltas
# --------------------------------------------------------------------------------------------


def test_identical_variants_give_zero_deltas_no_flips_and_noise():
    rows = contrib_rows(0.6, seed=7)
    c = cb.compare_rows({"fixed": rows, "cv": rows}, {"fixed": rows, "cv": rows}, n_boot=200)
    assert c["paired"] and c["n_common"] == len(rows) and c["flips"]["n"] == 0
    assert all(d["diff"] == 0 and not d["real"] for d in c["deltas"].values())
    assert c["verdict"] == "noise"


def test_perfect_variant_is_a_real_gain_with_counted_flips():
    a = contrib_rows(0.4, seed=8, n_dialogues=16)
    b = [{**r, "predicted": r["expected"], "score": 0.9 if r["expected"] != "no_alert" else 0.05} for r in a]
    c = cb.compare_rows({"fixed": a}, {"fixed": b}, basis="cv", n_boot=500)
    assert c["basis"] == "fixed"  # no cv rows -> falls back to fixed for both
    auc = c["deltas"]["auc"]
    assert auc["b"] == 1.0 and auc["diff"] > 0 and auc["real"] and auc["better"] == "b"
    wrong = sum(r["predicted"] != r["expected"] for r in a)
    assert c["flips"]["n"] == wrong and c["flips"]["label_fixed"] == wrong and c["flips"]["label_broken"] == 0
    assert c["deltas"]["false_alarm_rate"]["better"] in ("b", None)
    assert c["verdict"] == "gain"


def test_pairing_uses_only_common_calls_and_unpaired_when_disjoint():
    a = contrib_rows(0.6, seed=9)
    c = cb.compare_rows({"fixed": a}, {"fixed": a[:-4]}, n_boot=100)
    assert c["n_common"] == len(a) - 4 and c["only_a"] == 4 and c["only_b"] == 0
    other = contrib_rows(0.6, seed=9, prefix="Synth_")
    assert cb.compare_rows({"fixed": a}, {"fixed": other}, n_boot=100) == {
        "basis": "cv", "n_common": 0, "only_a": len(a), "only_b": len(other), "paired": False,
        "datasets": ["case", "synth"]}  # different datasets: never paired (callguard.datasets)


def test_verdict_and_lower_is_better():
    real = {"diff": -0.2, "lo": -0.3, "hi": -0.1, "real": True}
    assert cb.verdict({"false_alarm_rate": real}) == "gain"  # fewer false alarms = better
    assert cb.verdict({"accuracy": real}) == "loss"
    assert cb.verdict({"false_alarm_rate": real, "accuracy": real}) == "mixed"
    assert cb.verdict({"review_recall": real}) == "noise"  # shown, but too few calls to decide
    assert cv.classify(real, "miss_rate") == cv.CLASS_GAIN and cv.classify(real, "auc") == cv.CLASS_LOSS
    assert cv.classify({**real, "real": False}, "auc") == cv.CLASS_NOISE


def test_meta_diff_names_what_differs():
    d = cb.meta_diff({"profile": "p", "asr_model": "turbo", "git": {"sha": "a"}},
                     {"profile": "p", "asr_model": "large", "git": {"sha": "b"}})
    assert d == {"asr_model": ["turbo", "large"], "commit": ["a", "b"]}
    assert cb.meta_diff({}, {"profile": "p"}) == {}


def test_spec_rejects_bad_references(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump({"factors": [{"id": "f", "pairs": [{"a": "no-slash", "b": "e/v"}]}]}))
    with pytest.raises(cb.SpecError):
        cb.load_spec(p)


# --------------------------------------------------------------------------------------------
# whole analysis + outputs
# --------------------------------------------------------------------------------------------


def test_analyse_pairs_pending_unpaired_path_baselines_and_guide(tmp_path: Path, data: Path):
    spec = _spec(tmp_path)
    res = cb.analyse(spec, data)
    design, kev = res["factors"]
    good, same, other = design["pairs"]
    assert good["verdict"] == "gain" and good["deltas"]["auc"]["b"] == 1.0
    assert good["meta_diff"]["check_weights"] == [{"facts": 1.0}, {"facts": 1.0, "keywords": 0.15}]
    assert same["verdict"] == "noise" and same["flips"]["n"] == 0
    assert other["verdict"] == "unpaired" and other["status"] == "unpaired" and "deltas" not in other
    assert kev["pairs"][0]["verdict"] == "missing" and kev["pairs"][0]["status"] == "pending"
    assert "1× belegter Gewinn" in design["summary"]["line"]
    # path: s1.b (e/same) != s2.a (e/copy) -> link check finds identical rows
    assert res["path"]["links"] == [{"a": "e/same", "b": "e/copy", "n_common": 24, "label_differs": 0,
                                     "score_differs": 0, "identical": True}]
    entries = res["generalisation"][0]["entries"]
    assert entries[1]["vs_base"] == {"paired": False} and not entries[2]["available"]
    assert res["baselines"]["flag_all"]["false_alarm_rate"] == 1.0 and res["baselines"]["flag_all"]["flag_f1"] > 0.5
    assert res["holdout"]["refs"] == ["h/v"]
    guide = {g["metric"]: g for g in res["guide"]}
    assert guide["Flag-F1 allein"]["use"] == "nein"
    assert f"F1 {res['baselines']['flag_all']['flag_f1']:.2f}" in guide["Flag-F1 allein"]["number"]
    assert "12 Anrufe / 6 Dialoge" in guide["Holdout-Zahlen"]["number"]
    fam = res["variants"]["e/good"]["families"]
    assert all(x["label_acc"] == 1.0 for x in fam.values())
    assert res["variants"]["e/base"]["cost"] == {"s_per_call": 1.5, "llm_calls_per_call": 2.0, "wall_s_per_call": None}


def test_pending_pair_lights_up_when_rows_appear(tmp_path: Path, data: Path):
    spec = _spec(tmp_path)
    assert cb.analyse(spec, data)["factors"][1]["pairs"][0]["verdict"] == "missing"
    write_contrib_variant(data, "kev_vs_facts/qwen_general", contrib_rows(0.5, seed=1))
    write_contrib_variant(data, "kev_vs_facts/kev_general", contrib_rows(0.7, seed=4))
    p = cb.analyse(spec, data)["factors"][1]["pairs"][0]
    assert p["verdict"] in ("gain", "loss", "mixed", "noise") and p["n_common"] == 24


def test_outputs_and_load_or_compute_staleness(tmp_path: Path, data: Path):
    spec = _spec(tmp_path)
    res = cb.analyse(spec, data)
    pj, pm = cb.write_outputs(res, tmp_path / "out")
    md = pm.read_text()
    assert "| Design | base → good | exact | 24 |" in md and "Pending / missing" in md and "## Metric guide" in md
    assert json.loads(pj.read_text())["factors"][0]["id"] == "design"
    got, origin = cb.load_or_compute(spec["_path"], data, tmp_path / "out")
    assert origin == "file" and got["created"] == res["created"]
    later = time.time() + 5
    os.utime(data / "e" / "good" / "rows.json", (later, later))
    assert cb.load_or_compute(spec["_path"], data, tmp_path / "out")[1] == "live"


def test_cli_contrib_writes_json_and_markdown(tmp_path: Path, data: Path):
    spec = _spec(tmp_path)
    r = CliRunner().invoke(cli.app, ["contrib", "--spec", spec["_path"], "--data-root", str(data),
                                     "--out", str(tmp_path / "o"), "--n-boot", "200"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "o" / "contrib.json").exists() and (tmp_path / "o" / "contrib.md").exists()
    assert "pending" in r.output
    r = CliRunner().invoke(cli.app, ["contrib", "--spec", spec["_path"], "--data-root", str(tmp_path / "nope")])
    assert r.exit_code == 2


def test_shipped_spec_loads_and_names_kev_placeholders():
    spec = cb.load_spec()
    ids = {f["id"] for f in spec["factors"]}
    assert {"check_design", "asr", "llm_size", "wording", "kev_scorer", "kev_questions"} <= ids
    kev = [p for f in spec["factors"] for p in f["pairs"] if p["a"].startswith("kev_vs_facts/")]
    assert kev and all(p.get("pending") for p in kev)
    assert all(p.get("status") in (None, "exact", "caveat", "confounded") or p.get("unpaired")
               for f in spec["factors"] for p in f["pairs"])


# --------------------------------------------------------------------------------------------
# UI page (AppTest)
# --------------------------------------------------------------------------------------------


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    monkeypatch.delenv(cb.ENV_DATA, raising=False)
    return e


def _run(page: str) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    at.switch_page(f"views/{page}.py").run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_decisions_page_renders_factors_guide_heatmap_and_pending(env: FixtureEnv):
    write_contrib_fixture(env)
    at = _run("decisions")
    assert at.title[0].value == "Entscheidungshilfe: was bringt was"
    body = "\n".join(str(x.value) for x in [*at.markdown, *at.caption])
    assert "Prüfungsdesign" in body and "live berechnet" in body
    heads = [s.value for s in at.subheader]
    assert "Beitrag der Bausteine" in heads and "Welche Masse für Entscheide?" in heads
    assert "Hält es ausserhalb der Dev-Daten?" in heads and "Wo ist welches System schwach? Und was kostet es?" in heads
    frames = [df.value for df in at.dataframe]
    guide = at.table[0].value
    assert "Flag-F1 allein" in guide.index.tolist() and "Für Entscheide?" in guide.columns
    costs = next(f for f in frames if "LLM-Aufrufe/Anruf" in f.columns)
    assert "champion/champion" in costs["Variante"].tolist()
    assert any("Ausstehend" in x.label for x in at.expander)
    at.button(key="cg_dec_refresh").click().run()
    assert not at.exception


def test_decisions_page_without_data(env: FixtureEnv):
    at = _run("decisions")
    assert any("Keine Experiment-Ergebnisse" in i.value for i in at.info)
