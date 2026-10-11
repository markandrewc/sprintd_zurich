from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from callguard import cli
from callguard import experiments as ex
from callguard.data import load_calls

DATA = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/data"
needs_data = pytest.mark.skipif(not DATA.exists(), reason="case data not available")
runner = CliRunner()

CALLS = ["Stufe1_D01-K1", "Stufe1_D01-K2", "Stufe1_D02-K1", "Stufe1_D02-K2", "Stufe1_D04-K1", "Stufe1_D04-K2",
         "Stufe1_D05-K1", "Stufe2_C03-K1", "Stufe2_C05-K1", "Stufe2_C09-K1", "Stufe3_C17-K1", "Stufe3_C18-K1"]


def spec(tmp_path: Path, variants: list[dict], **kw) -> ex.Spec:
    raw = {"name": "t", "base": "demo-offline", "split": "dev", "variants": variants, **kw}
    s = ex.parse_spec(raw)
    for v in s.variants:  # keep the test's caches and runs out of the repo
        if not v.refuse_from:
            v.set = [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}", *v.set]
    return s


# -- spec + config ---------------------------------------------------------------------------------


def test_parse_spec_validates():
    with pytest.raises(ex.SpecError, match="base"):
        ex.parse_spec({"variants": [{"name": "a"}]})
    with pytest.raises(ex.SpecError, match="duplicate"):
        ex.parse_spec({"base": "base", "variants": [{"name": "a"}, {"name": "a"}]})
    with pytest.raises(ex.SpecError, match="unknown keys"):
        ex.parse_spec({"base": "base", "variants": [{"name": "a", "sett": []}]})
    with pytest.raises(ex.SpecError, match="no variant"):
        ex.parse_spec({"base": "base", "compare_to": "x", "variants": [{"name": "a"}]})
    with pytest.raises(ex.SpecError, match="no variant"):
        ex.parse_spec({"base": "base", "variants": [{"name": "a", "refuse_from": "zz"}]})
    s = ex.parse_spec({"base": "base", "variants": [{"name": "a"}, {"name": "b", "refuse_from": "a"}]})
    assert s.baseline == "a" and s.split == "dev"


def test_select_checks_by_name():
    checks = [{"name": "keywords"}, {"name": "patterns"}, {"name": "llm_judge"}, {"name": "geval"}]
    assert [c["name"] for c in ex.select_checks(checks, ["geval", "keywords"])] == ["keywords", "geval"]
    assert [c["name"] for c in ex.select_checks(checks, drop=["geval"])] == ["keywords", "patterns", "llm_judge"]
    out = ex.select_checks(checks, ["keywords"], add=[{"name": "kwctx", "type": "keyword_context"}])
    assert [c["name"] for c in out] == ["keywords", "kwctx"]
    with pytest.raises(ex.SpecError, match="unknown check"):
        ex.select_checks(checks, drop=["nope"])


def test_set_addresses_list_items_by_name(tmp_path):
    s = spec(tmp_path, [{"name": "a", "drop_checks": ["patterns"],
                         "set": ["checks.llm_judge.samples=3", "fusion.threshold=0.4"]}])
    cfg = ex.variant_config(s, s.variants[0])
    judge = next(c for c in cfg.checks if c["name"] == "llm_judge")
    assert judge["samples"] == 3 and cfg.fusion["threshold"] == 0.4
    assert "patterns" not in [c["name"] for c in cfg.checks]
    assert ex.is_oracle(s.variants[0], cfg)  # demo-offline reads the reference scripts
    s2 = spec(tmp_path, [{"name": "a", "set": ["checks.nope.samples=3"]}])
    with pytest.raises(ex.SpecError, match="nope"):
        ex.variant_config(s2, s2.variants[0])


def test_oracle_flag_and_views():
    from callguard.config import load_config
    cfg = load_config("base")
    v = ex.Variant(name="x")
    assert not ex.is_oracle(v, cfg)
    assert ex.is_oracle(ex.Variant(name="x", oracle=True), cfg)


def test_spec_files_parse():
    for p in sorted((ex.EXPERIMENTS_DIR).glob("*.yaml")):
        s = ex.load_spec(p)
        assert s.variants, p


# -- running ---------------------------------------------------------------------------------------


@needs_data
def test_offline_experiment_end_to_end(tmp_path):
    s = spec(tmp_path, [{"name": "all"}, {"name": "rules", "checks": ["keywords", "patterns"]},
                        {"name": "all_t03", "refuse_from": "all", "set": ["fusion.threshold=0.3"]},
                        {"name": "no_geval", "refuse_from": "all", "drop_checks": ["geval"]}],
             compare_to="all")
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS]
    seen = []
    summary = ex.run_experiment(s, calls, jobs=3, runs_dir=tmp_path / "runs", n_boot=300,
                                progress=lambda v, i, n, cid, row: seen.append((v, cid)))
    out = tmp_path / "runs/experiments/t"
    assert {v for v, _ in seen} == {"all", "rules", "all_t03", "no_geval"}
    for v in ("all", "rules", "all_t03", "no_geval"):
        assert (out / v / "results.jsonl").exists() and (out / v / "rows.json").exists()
    assert (out / "summary.json").exists() and (out / "summary.md").exists()
    V = summary["variants"]
    assert set(V) == {"all", "rules", "all_t03", "no_geval"}
    a = V["all"]
    assert a["oracle"] and not a["degraded"] and a["n_calls"] == len(calls)
    assert a["cv"] is not None and len(a["cv_folds"]) >= 2
    assert a["fixed"]["ci"]["flag_f1"]["n_valid"] > 0
    assert a["auc"]["flag"]["value"] is not None and a["auc"]["flag"]["n_pos"] + a["auc"]["flag"]["n_neg"] == len(calls)
    assert a["cv_far"] is not None and len(a["cv_far_folds"]) == len(a["cv_folds"])
    assert a["fixed"]["flag_balanced_accuracy"] is not None
    assert summary["baselines"]["flag_all"]["false_alarm_rate"] == 1.0
    assert a["cost"]["llm_calls_per_call"] > 0 and V["rules"]["cost"]["llm_calls_per_call"] == 0
    assert V["all_t03"]["meta"]["threshold"] == 0.3 and V["all_t03"]["meta"]["refuse_from"] == "all"
    assert V["no_geval"]["meta"]["checks"] == ["keywords", "patterns", "llm_judge"]
    # stored results load back without word timestamps, re-fusion dropped the geval results
    res = ex.load_results(out / "no_geval")
    assert res and all("geval" not in r.checks for r in res)
    assert all(not seg.words for r in res for seg in r.transcript.segments)
    comps = {c["b"]: c for c in summary["comparisons"]}
    assert set(comps) == {"rules", "all_t03", "no_geval"}
    assert {"paired", "mcnemar_flag", "mcnemar_label", "flips"} <= set(comps["rules"]["cv"])
    rows = json.loads((out / "rules/rows.json").read_text())
    assert all("passage" in r and "reason" in r for r in rows["fixed"])
    md = (out / "summary.md").read_text()
    assert "ORACLE" in md and "`rules` vs `all`" in md
    assert "Floor on these" in md and "ROC AUC" in md and "CV@FAR20" in md
    # an older run without CV@FAR20 rows gets them back-filled on rescore
    data = json.loads((out / "rules/rows.json").read_text())
    data.pop("cv_far"), data.pop("cv_far_folds")
    (out / "rules/rows.json").write_text(json.dumps(data))
    ex.summarize(s, out, n_boot=100)
    assert "cv_far" in json.loads((out / "rules/rows.json").read_text())
    # rescore from disk only
    again = ex.summarize(s, out, n_boot=300)
    assert again["variants"]["rules"]["fixed"]["flag_f1"] == V["rules"]["fixed"]["flag_f1"]
    # leaderboard + chart report from the same runs dir
    from callguard import report
    lb, rows = report.leaderboard(tmp_path / "lb.md", tmp_path / "runs")
    assert len(rows) == 4 and "ORACLE" in lb.read_text()
    md = report.build_report(["t"], tmp_path / "report", tmp_path / "runs")
    pngs = sorted(p.name for p in (tmp_path / "report/t").glob("*.png"))
    assert pngs == ["auc.png", "clean_vs_noisy.png", "cost_vs_f1.png", "levels.png", "metrics.png",
                    "thresholds.png"]
    assert "flag AUC" in lb.read_text() and "CV@FAR20" in lb.read_text()
    assert "failed" not in md.read_text()


@needs_data
def test_failed_checks_mark_variant_degraded(tmp_path):
    # an LLM check pointing at an LLM that is not configured fails on every call
    s = spec(tmp_path, [{"name": "broken", "checks": ["keywords"],
                         "add_checks": [{"name": "judge2", "type": "llm_judge", "llm": "missing"}]}])
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS[:4]]
    summary = ex.run_experiment(s, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=200)
    v = summary["variants"]["broken"]
    assert v["degraded"] and v["check_failures"]["by_check"] == {"judge2": 4}
    assert "DEGRADED" in (tmp_path / "runs/experiments/t/summary.md").read_text()


@needs_data
def test_refuse_needs_source(tmp_path):
    s = spec(tmp_path, [{"name": "all"}, {"name": "t", "refuse_from": "all"}])
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS[:2]]
    with pytest.raises(ex.SpecError, match="run that variant first"):
        ex.run_experiment(s, calls, variants=["t"], runs_dir=tmp_path / "runs", n_boot=100)


# -- CLI ------------------------------------------------------------------------------------------


@needs_data
def test_cli_dry_run_and_run(tmp_path):
    spec_path = tmp_path / "mini.yaml"
    sets = [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}"]
    spec_path.write_text(json.dumps({"name": "mini", "base": "demo-offline", "variants": [
        {"name": "a", "set": sets}, {"name": "b", "set": sets, "checks": ["keywords"]}]}))
    calls = ",".join(CALLS[:6])
    r = runner.invoke(cli.app, ["experiment", str(spec_path), "--dry-run", "--calls", calls])
    assert r.exit_code == 0, r.output
    assert "dry run" in r.output
    r = runner.invoke(cli.app, ["experiment", str(spec_path), "--calls", calls, "--jobs", "2", "--n-boot", "200"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "runs/experiments/mini/summary.md").exists()
    r = runner.invoke(cli.app, ["experiment", str(spec_path), "--rescore", "--n-boot", "200"])
    assert r.exit_code == 0, r.output


@needs_data
def test_eval_split_holdout_is_logged(tmp_path):
    from callguard import splits as sp
    s = sp.load_splits()
    hold = [c.call_id for c in load_calls(DATA) if c.dialogue_id in s.holdout and not c.noisy][:2]
    args = ["eval", "-c", "demo-offline", "--set", f"paths.runs_dir={tmp_path / 'runs'}",
            "--set", f"paths.cache_dir={tmp_path / 'cache'}", "--no-write-results"]
    r = runner.invoke(cli.app, [*args, "--split", "holdout", "--calls", ",".join(hold + ["Stufe1_D02-K1"])])
    assert r.exit_code == 0, r.output
    log = (tmp_path / "runs/holdout_log.jsonl").read_text().splitlines()
    assert len(log) == 1 and json.loads(log[0])["n_calls"] == 2  # the dev call was filtered out
    r = runner.invoke(cli.app, [*args, "--split", "dev", "--calls", ",".join(hold + ["Stufe1_D02-K1"])])
    assert r.exit_code == 0, r.output
    assert len((tmp_path / "runs/holdout_log.jsonl").read_text().splitlines()) == 1
    rep = json.loads((tmp_path / "runs/demo-offline/eval_dev/report.json").read_text())
    assert rep["metrics"]["n"] == 1 and rep["meta"]["split"] == "dev"
    r = runner.invoke(cli.app, [*args, "--split", "nope"])
    assert r.exit_code != 0


def _swept(points):
    """[(threshold, recall, far, f1)] -> eval.sweep-like entries."""
    return [{"threshold": t, "metrics": {"n": 10, "flag": {"recall": r, "false_alarm_rate": f, "f1": f1}}}
            for t, r, f, f1 in points]


def test_pick_recall_at_far():
    sw = _swept([(0.3, 1.0, 1.0, 0.7), (0.5, 0.8, 0.3, 0.7), (0.6, 0.6, 0.2, 0.65), (0.7, 0.6, 0.1, 0.66),
                 (0.8, 0.2, 0.0, 0.3)])
    p = ex.pick_recall_at_far(sw)
    assert p["threshold"] == 0.7 and "cap" in p["reason"]  # recall 0.6 at FAR 0.1 beats 0.6 at 0.2
    none_ok = _swept([(0.3, 1.0, 1.0, 0.7), (0.5, 0.9, 0.5, 0.7), (0.6, 0.7, 0.5, 0.6)])
    p = ex.pick_recall_at_far(none_ok)
    assert p["threshold"] == 0.5 and "lowest FAR" in p["reason"]
    assert ex.pick_recall_at_far([]) is None


def test_tuning_overlay_off_unless_spec_asks(tmp_path):
    tuning = tmp_path / "tuning.yaml"
    tuning.write_text("fusion: {threshold: 0.31}\nweights: {keywords: 0.9}\n")
    variants = [{"name": "a", "set": [f"paths.tuning={tuning}"]}]
    off = ex.parse_spec({"base": "demo-offline", "variants": variants})
    cfg = ex.variant_config(off, off.variants[0])
    assert cfg.fusion["threshold"] != 0.31 and cfg.tuning is None
    plain = ex.parse_spec({"base": "demo-offline", "variants": [{"name": "a"}]})
    assert ex.variant_config(plain, plain.variants[0]).paths.tuning is None  # default overlay disabled
    on = ex.parse_spec({"base": "demo-offline", "use_tuning": True, "variants": variants})
    cfg = ex.variant_config(on, on.variants[0])
    assert cfg.fusion["threshold"] == 0.31 and cfg.tuning["applied"]["fusion.threshold"] == 0.31
    assert next(c for c in cfg.checks if c["name"] == "keywords")["weight"] == 0.9
    # --set still wins over the overlay
    on.variants[0].set.append("fusion.threshold=0.6")
    assert ex.variant_config(on, on.variants[0]).fusion["threshold"] == 0.6
