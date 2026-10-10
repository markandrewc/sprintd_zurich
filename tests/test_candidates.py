"""callguard.candidates (candidate matrix for the team decisions), `callguard candidates` and the page
"Team-Entscheidungen". Offline: synthetic rows only, no models."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml
from streamlit.testing.v1 import AppTest
from typer.testing import CliRunner
from ui_fixtures import FixtureEnv, contrib_rows, write_contrib_variant, write_fixture_env

from callguard import candidates as cd
from callguard import cli, stats
from callguard import contrib as cb
from callguard import datasets as ds
from callguard.ui import backend as be
from callguard.ui import team_view as tv

APP = Path(__file__).resolve().parents[1] / "src" / "callguard" / "ui" / "app.py"


def _good(rows: list[dict]) -> list[dict]:
    return [{**r, "predicted": r["expected"], "score": 0.9 if r["expected"] != "no_alert" else 0.05} for r in rows]


@pytest.fixture
def world(tmp_path: Path) -> dict:
    """Two data roots, an experiments dir that plans some variants, and a spec over them."""
    root, pert, exps = tmp_path / "experiments_out", tmp_path / "perturbed", tmp_path / "exp_specs"
    base = contrib_rows(0.6, seed=1)
    write_contrib_variant(root, "e/champ", base)
    write_contrib_variant(root, "e/champ_para", contrib_rows(0.5, seed=2))
    write_contrib_variant(root, "e/champ_para2", contrib_rows(0.5, seed=3))
    write_contrib_variant(root, "e/good", _good(base))
    write_contrib_variant(root, "e/good_para", _good(base))
    write_contrib_variant(pert, "p/champ", contrib_rows(0.55, seed=4))
    (root / "e" / "good_running").mkdir(parents=True)  # folder exists, rows not yet: "läuft noch"
    exps.mkdir()
    (exps / "e.yaml").write_text(yaml.safe_dump({"name": "e", "variants": [{"name": "good_blind"}, {"name": "x_v3"}]}))
    spec = {
        "reference": "champ", "n_boot": 300, "seed": 13, "rows": "cv",
        "data_roots": {"default": str(root), "perturbed": str(pert)}, "experiments_dir": str(exps),
        "candidates": [
            {"id": "champ", "label": "Champ", "group": "A", "tuned": "e/champ", "reworded": ["e/champ_para", "e/champ_para2"],
             "blind": "na", "rerecorded": "perturbed:p/champ", "passages": "ja"},
            {"id": "good", "label": "Good", "group": "A", "tuned": "e/good", "reworded": ["e/good_para", "e/good_running"],
             "blind": "e/good_blind", "rerecorded": "perturbed:p/nothing", "passages": "nein"},
            {"id": "v3", "label": "V3", "group": "B", "tuned": "e/x_v3"},
            {"id": "hid", "label": "Hidden", "hidden": True, "kind": "oracle", "tuned": "e/champ"},
            {"id": "all", "label": "All", "kind": "trivial", "trivial": "flag_all"},
        ],
    }
    p = tmp_path / "candidates.yaml"
    p.write_text(yaml.safe_dump(spec))
    return {"spec_path": p, "root": root, "pert": pert, "exps": exps, "base": base, "tmp": tmp_path}


# --------------------------------------------------------------------------------------------
# mapping + pending logic
# --------------------------------------------------------------------------------------------


def test_slot_status_ok_running_pending_missing_na(world: dict):
    s = cd.load_spec(world["spec_path"])
    data = cd.Data(s["data_roots"], s["experiments_dir"])
    assert data.status("e/champ") == "ok" and data.status("perturbed:p/champ") == "ok"
    assert data.status("e/good_running") == "running"
    assert data.status("e/good_blind") == "pending"  # planned in exp_specs/e.yaml
    assert data.status("perturbed:p/nothing") == "missing"
    assert cd.resolve(data, "na")["status"] == "na" and cd.resolve(data, None)["status"] == "na"
    # fallbacks: first available wins, else the most advanced state
    assert cd.resolve(data, ["e/nope", "e/champ"])["ref"] == "e/champ"
    assert cd.resolve(data, ["e/nope", "e/good_running"])["status"] == "running"
    with pytest.raises(cd.SpecError):
        cd.parse_ref("no-slash")
    with pytest.raises(cd.SpecError):
        data.status("elsewhere:e/champ")


def test_analyse_marks_pending_partial_and_lights_up(world: dict):
    s = cd.load_spec(world["spec_path"])
    res = cd.analyse(s)
    C = {c["id"]: c for c in res["candidates"]}
    assert C["v3"]["tuned"] is None and C["v3"]["slots"]["tuned"]["status"] == "pending"
    assert cd.cell(C["v3"], "auc") == "ausstehend" and cd.vs_text(C["v3"]) == "ausstehend"
    g = C["good"]["gen"]
    assert g["reworded"]["status"] == "partial" and g["reworded"]["n_sets"] == 1
    assert cd.cell(C["good"], "reworded").endswith("(teilweise)")
    assert cd.cell(C["good"], "blind") == "ausstehend" and cd.cell(C["good"], "rerecorded") == "nicht geplant"
    assert cd.cell(C["champ"], "blind") == "n/a"
    pend = {(p["candidate"], p["slot"], p["status"]) for p in res["pending"]}
    assert ("good", "reworded", "running") in pend and ("good", "blind", "pending") in pend
    assert ("v3", "tuned", "pending") in pend and not any(p[0] == "champ" for p in pend)
    # the planned blind run arrives -> it lights up on the next analyse
    write_contrib_variant(world["root"], "e/good_blind", _good(world["base"]))
    C2 = {c["id"]: c for c in cd.analyse(s)["candidates"]}
    assert C2["good"]["gen"]["blind"]["auc"]["value"] == 1.0
    assert ("good", "blind", "pending") not in {(p["candidate"], p["slot"], p["status"]) for p in cd.pending_items(
        cd.analyse(s))}


def test_paired_against_reference_best_marks_and_hidden(world: dict):
    res = cd.analyse(cd.load_spec(world["spec_path"]))
    C = {c["id"]: c for c in res["candidates"]}
    vr = C["good"]["vs_ref"]
    assert vr["auc"]["b"] == 1.0 and vr["auc"]["diff"] > 0 and vr["n_common"] == 24
    assert "champ" not in C["champ"].get("vs_ref", {})
    # reworded mean of the reference: two paraphrase sets
    assert C["champ"]["gen"]["reworded"]["n_sets"] == 2
    assert C["champ"]["gen"]["reworded"]["drop"]["n"] == 24
    assert res["best"]["auc"]["ids"] == ["good"]
    rows = cd.matrix_rows(res)
    labels = [r[0] for r in rows]
    assert "Hidden" not in labels and labels[-1] == "All"  # hidden only feeds placeholders
    good = rows[labels.index("Good")]
    assert good[1].startswith("**1.00") and (" belegt" in good[1] or "(≈ Champion)" in good[1])
    triv = C["all"]
    assert triv["tuned"]["auc"]["value"] == 0.5 and triv["tuned"]["metrics"]["false_alarm_rate"]["value"] == 1.0
    assert cd.vs_text(triv) == "Untergrenze" and triv["id"] not in res["best"]["auc"]["ids"]


def test_noise_difference_is_shown_as_approx_champion():
    rows = contrib_rows(0.6, seed=7)
    d = {"diff": 0.02, "lo": -0.05, "hi": 0.08, "real": False}
    assert cd.fmt_delta(d).endswith("≈") and "belegt" in cd.fmt_delta({**d, "lo": 0.01, "real": True})
    c = {"id": "x", "kind": "candidate", "tuned": {"auc": {"value": 0.8}}, "vs_ref": {"auc": d}}
    assert cd.vs_text(c) == "≈ Champion"
    assert stats.labeled(rows)  # fixture sanity


def test_mean_auc_delta_matches_paired_auc_for_single_sets():
    a, b = contrib_rows(0.5, seed=11, n_dialogues=16), contrib_rows(0.8, seed=12, n_dialogues=16)
    m = cd.mean_auc_delta([a], [b], n_boot=400, seed=13)
    p = stats.paired_auc(a, b, n_boot=400, seed=13)["flag"]
    assert m["diff"] == p["diff"] and m["lo"] == p["lo"] and m["hi"] == p["hi"] and m["real"] == p["real"]
    same = cd.mean_auc_delta([a], [a, a], n_boot=200)
    assert same["diff"] == 0 and same["lo"] == 0 and same["hi"] == 0 and not same["real"]
    lo, hi = cd.mean_auc_ci([a, b], n_boot=200)
    assert lo is not None and lo <= (stats.auc(a) + stats.auc(b)) / 2 <= hi


def test_evidence_cache_is_keyed_by_results_mtime(world: dict, tmp_path: Path):
    s = cd.load_spec(world["spec_path"])
    data = cd.Data(s["data_roots"], s["experiments_dir"])
    (world["root"] / "e" / "champ" / "results.jsonl").write_text("{}\n")
    calls = []

    def compute(p: Path) -> dict:
        calls.append(p)
        return {"n": 10, "no_passage": 2, "chance1": 0.2, "hit1": {"value": 0.7, "lo": 0.5, "hi": 0.9}}

    cache = tmp_path / "cache" / "ev.json"
    ev = cd.evidence_for(data, ["e/champ", "e/good"], cache, compute)
    assert set(ev) == {"e/champ"} and len(calls) == 1 and cache.exists()
    assert cd.evidence_for(data, ["e/champ"], cache, None) == ev and len(calls) == 1  # from cache, no compute
    res = cd.analyse(s, evidence=ev)
    champ = next(c for c in res["candidates"] if c["id"] == "champ")
    assert cd.cell(champ, "hit1") == "70% [50, 90], Zufall 20%, 2/10 ohne Passage"
    good = next(c for c in res["candidates"] if c["id"] == "good")
    assert cd.cell(good, "hit1") == "keine Passagen"


# --------------------------------------------------------------------------------------------
# texts: placeholders, team decisions, teammate repo
# --------------------------------------------------------------------------------------------


def test_placeholders_fill_values_deltas_and_pending(world: dict):
    res = cd.analyse(cd.load_spec(world["spec_path"]))
    txt = cd.fill({"a": ["AUC {{champ.auc}}", "{{good.vs_auc}} / {{v3.auc}} / {{good.drop_reworded}}"],
                   "b": "{{nope.auc}} {{champ.bogus}} {{hid.auc}} {{champ.reviews}}"}, res)
    assert txt["a"][0].startswith("AUC 0.") and "[" in txt["a"][0]
    assert txt["a"][1].split(" / ")[1] == "ausstehend" and txt["a"][1].split(" / ")[0].startswith("+")
    assert "[? nope]" in txt["b"] and "[? bogus]" in txt["b"] and "Soll-Prüfen getroffen" in txt["b"]


def test_shipped_texts_only_use_known_candidates_and_keys():
    spec = cd.load_spec()
    ids = {c["id"] for c in spec["candidates"]}
    assert spec["reference"] == "champion" and {"champion", "champion_v3", "kev", "q38q6", "r1", "flag_all"} <= ids
    fake = {"candidates": [{"id": i, "label": i, "kind": "candidate", "tuned": None, "slots": {}} for i in ids]}
    for path in (cd.DEFAULT_DECISIONS, cd.DEFAULT_COMPARISON):
        d = cd.load_yaml(None, path)
        assert not d.get("_missing"), path
        assert "[?" not in json.dumps(cd.fill(d, fake), ensure_ascii=False), path
    dec = cd.load_yaml(None, cd.DEFAULT_DECISIONS)["decisions"]
    assert [d["id"] for d in dec] == ["policy_table", "backend", "hardware", "github", "teammate", "organisers"]
    assert all(d.get("recommendation") and d.get("options") for d in dec)
    comp = cd.load_yaml(None, cd.DEFAULT_COMPARISON)
    assert len(comp["written_against"]) == 40
    assert {r["recommendation"] for r in comp["rows"]} <= {"übernehmen", "behalten", "kombinieren", "offen"}


def test_team_decision_roundtrip(tmp_path: Path):
    p = tmp_path / "team.yaml"
    cd.save_team_decision("policy_table", {"choice": "v3", "who": "Beni", "note": ""}, p)
    cd.save_team_decision("github", {"choice": "PR", "who": "Team", "when": "2026-10-10 14:00"}, p)
    t = cd.load_team(p)
    assert t["policy_table"]["choice"] == "v3" and "note" not in t["policy_table"] and t["policy_table"]["when"]
    assert t["github"]["when"] == "2026-10-10 14:00"
    md = "\n".join(cd.decision_markdown({"id": "github", "title": "G"}, t["github"]))
    assert "**Entscheid des Teams:** PR (Team, 2026-10-10 14:00)" in md
    assert cd.load_team(tmp_path / "missing.yaml") == {}


def test_zurich_status_flags_a_moved_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    repo = tmp_path / "z"
    repo.mkdir()
    git = ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / "a").write_text("1")
    subprocess.run([*git, "add", "a"], check=True)
    subprocess.run([*git, "commit", "-qm", "one"], check=True)
    head = cd.git_head(repo)
    monkeypatch.setenv(cd.ENV_ZURICH, str(repo))
    assert cd.zurich_status({"written_against": head})["stale"] is False
    assert cd.zurich_status({"written_against": head[:7]})["stale"] is False
    (repo / "a").write_text("2")
    subprocess.run([*git, "commit", "-qam", "two"], check=True)
    z = cd.zurich_status({"written_against": head})
    assert z["stale"] and z["head"] != head
    md = "\n".join(cd.comparison_markdown({"written_against": head, "rows": [{"topic": "ASR"}]}, z))
    assert "Achtung" in md and "| ASR |" in md
    monkeypatch.setenv(cd.ENV_ZURICH, str(tmp_path / "nope"))
    assert cd.zurich_status({"written_against": head}) == {
        "repo": str(tmp_path / "nope"), "available": False, "head": None, "written_against": head, "stale": False}


# --------------------------------------------------------------------------------------------
# outputs + CLI
# --------------------------------------------------------------------------------------------


def test_outputs_and_load_or_compute(world: dict):
    s = cd.load_spec(world["spec_path"])
    res = cd.analyse(s)
    out = world["tmp"] / "out"
    dec = {"decisions": [{"id": "d1", "title": "D1", "options": [{"name": "A", "pros": ["AUC {{champ.auc}}"]}],
                          "recommendation": "A"}]}
    pj, pm = cd.write_outputs(res, out, world["tmp"] / "TEAM.md", dec, None, {"d1": {"choice": "A", "who": "x"}})
    md = pm.read_text()
    assert "## Kandidaten-Matrix" in md and "| Champ |" in md and "Hidden" not in md.split("## Offene")[0]
    assert "Ausstehend / läuft noch" in md and "**Entscheid des Teams:** A (x" in md and "pro: AUC 0." in md
    got, origin = cd.load_or_compute(world["spec_path"], out)
    assert origin == "file" and got["created"] == res["created"]
    write_contrib_variant(world["root"], "e/x_v3", contrib_rows(0.7, seed=9))
    got, origin = cd.load_or_compute(world["spec_path"], out)
    assert origin == "live" and next(c for c in got["candidates"] if c["id"] == "v3")["tuned"] is not None


def test_cli_candidates_writes_json_and_doc(world: dict):
    out, doc = world["tmp"] / "o", world["tmp"] / "doc.md"
    r = CliRunner().invoke(cli.app, ["candidates", "--spec", str(world["spec_path"]), "--out", str(out),
                                     "--doc", str(doc), "--no-evidence", "--n-boot", "200"])
    assert r.exit_code == 0, r.output
    assert (out / "candidates.json").exists() and doc.exists() and "pending" in r.output
    r = CliRunner().invoke(cli.app, ["candidates", "--spec", str(world["tmp"] / "nope.yaml")])
    assert r.exit_code == 2


# --------------------------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------------------------


def test_frames_and_chart(world: dict):
    res = cd.analyse(cd.load_spec(world["spec_path"]))
    t = tv.text_frame(res)
    assert list(t.columns)[:2] == ["Kandidat", "Gruppe"] and "Hidden" not in t["Kandidat"].tolist()
    n = tv.number_frame(res)
    good = n[n["Kandidat"] == "Good"].iloc[0]
    assert good["Flag-AUC"] == 1.0 and "läuft noch" in good["Daten"] and "ausstehend" in good["Daten"]
    assert tv.best_cells(res, n)["Flag-AUC"] == [n["Kandidat"].tolist().index("Good")]
    d = tv.dumbbell_frame(res, "reworded")
    assert set(d["Bedingung"]) == {tv.TUNED, tv.CONDITIONS["reworded"]}
    assert tv.dumbbell_chart(d, "reworded").to_dict()["layer"]
    d2 = tv.dumbbell_frame(res, "blind")
    assert (d2[d2["Kandidat"] == "Good"]["Zustand"] == "ausstehend").all()
    assert tv.dumbbell_chart(d2, "blind").to_dict()["layer"]


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> FixtureEnv:
    e = write_fixture_env(tmp_path)
    monkeypatch.setenv(be.ENV_ARGS, e.args)
    monkeypatch.delenv(cb.ENV_DATA, raising=False)
    monkeypatch.setenv("CALLGUARD_TEAM_DECISIONS", str(tmp_path / "team_decisions.yaml"))
    monkeypatch.setenv(cd.ENV_ZURICH, str(tmp_path / "no_repo"))
    return e


def _run_team() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=120)
    at.run()
    at.switch_page("views/team.py").run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def test_team_page_renders_matrix_chart_decisions_and_records_a_choice(env: FixtureEnv, tmp_path: Path):
    root = env.runs_dir.parent / "experiments"
    write_contrib_variant(root, "champion/champion", contrib_rows(0.8, seed=2))
    write_contrib_variant(root, "kev_vs_facts/qwen_facts_para", contrib_rows(0.6, seed=3))
    write_contrib_variant(root, "kev_vs_facts/kev_facts", contrib_rows(0.7, seed=4))
    write_contrib_variant(root, "kev_vs_facts/kev_facts_para", contrib_rows(0.75, seed=5))
    at = _run_team()
    assert at.title[0].value == "Team-Entscheidungen"
    heads = [s.value for s in at.subheader]
    assert heads[:4] == ["Optionen für das Team: Kandidaten-Matrix",
                         "Abgestimmt gegen andere Bedingungen: wie viel ist Dev-Anpassung?",
                         f"Externer Testsatz {cd.T50_TITLE}", "Offene Entscheidungen"]
    assert "Unser Ansatz vs. sprintd_zurich (Teamkollege)" in heads
    matrix = at.dataframe[0].value
    assert "Champion: Qwen2.5-7B Fakten, Tabelle v1" in matrix["Kandidat"].tolist()
    assert any("ausstehend" in str(x) for x in matrix.to_numpy().ravel())
    labels = [e.label for e in at.expander]
    assert any(lab.startswith("1. Policy-Tabelle") and lab.endswith("· offen") for lab in labels)
    assert any(lab.startswith("Ausstehend (") for lab in labels)
    at.segmented_control(key="cg_team_view").set_value("Sortierbar (Zahlen)").run()
    assert not at.exception
    at.pills(key="cg_team_condition").set_value("rerecorded").run()
    assert not at.exception
    at.selectbox(key="cg_team_choice_policy_table").set_value("v3")
    at.text_input(key="cg_team_who_policy_table").set_value("Beni")
    next(b for b in at.button if b.label == "Entscheid speichern").click().run()
    assert not at.exception
    team = cd.load_team(tmp_path / "team_decisions.yaml")
    assert team["policy_table"]["choice"] == "v3" and team["policy_table"]["who"] == "Beni"


def test_team_page_without_data(env: FixtureEnv):
    at = _run_team()
    assert any("Keine der Kandidaten-Varianten" in i.value for i in at.info)
    assert [s.value for s in at.subheader][1:3] == [f"Externer Testsatz {cd.T50_TITLE}", "Offene Entscheidungen"]
    assert any(cd.T50_BANNER in w.value for w in at.warning)
    assert any("Noch keine test50-Ergebnisse" in i.value for i in at.info)


def test_team_page_is_registered_next_to_entscheidungshilfe():
    from callguard.ui import pages_registry as pr

    keys = [p.key for p in pr.pages()]
    assert keys.index("team") == keys.index("decisions") + 1
    assert next(p for p in pr.pages() if p.key == "team").path().name == "team.py"


# --------------------------------------------------------------------------------------------
# test50: own dataset, never pooled
# --------------------------------------------------------------------------------------------


def t50_rows(quality: float, seed: int = 0) -> list[dict]:
    """test50-like rows: 6 A/B pairs (twin group per pair), 2 traps, 2 reviews, 1 numbers pair, 2 multi;
    each dialogue clean (K1) + noisy (K2)."""
    import numpy as np

    rng = np.random.default_rng(seed)
    dlgs = []
    for i in range(1, 7):
        fam = ("trade", "access", "disclosure")[i % 3]
        dlgs += [(f"T50-{fam}-{i:02d}-A", "alarm", f"T50-{fam}-{i:02d}"),
                 (f"T50-{fam}-{i:02d}-B", "no_alert", f"T50-{fam}-{i:02d}")]
    dlgs += [("T50-trade-trap", "no_alert", "T50-trade-trap"), ("T50-access-trap", "no_alert", "T50-access-trap"),
             ("T50-trade-review", "review", "T50-trade-review"), ("T50-access-review", "review", "T50-access-review"),
             ("T50-numbers-01-A", "no_alert", "T50-numbers-01"), ("T50-numbers-01-B", "no_alert", "T50-numbers-01"),
             ("T50-multi-01", "alarm", "T50-multi-01"), ("T50-multi-02", "no_alert", "T50-multi-02")]
    rows = []
    for dlg, exp, grp in dlgs:
        for k in (1, 2):
            right = rng.random() < quality
            flag = exp != "no_alert"
            pred = exp if right else ("no_alert" if flag else "alarm")
            high = flag if right else not flag
            score = round(float(0.6 + 0.35 * rng.random()) if high else float(0.4 * rng.random()), 4)
            rows.append({"call_id": f"{dlg}-K{k}", "dialogue_id": dlg, "group": grp, "level": 2, "noisy": k == 2,
                         "expected": exp, "expected_family": "trade", "predicted": pred, "score": score,
                         "llm_calls": 1, "check_seconds": {"facts": 1.0}})
    return rows


@pytest.fixture
def world50(world: dict) -> dict:
    t50 = world["tmp"] / "t50"
    write_contrib_variant(t50, "test50/champion", t50_rows(0.6, seed=1))
    write_contrib_variant(t50, "test50/good", _good(t50_rows(0.6, seed=1)))
    (world["exps"] / "test50.yaml").write_text(yaml.safe_dump({"name": "test50", "variants": [{"name": "v3x"}]}))
    spec = yaml.safe_load(world["spec_path"].read_text())
    spec["data_roots"]["test50"] = str(t50)
    for c in spec["candidates"]:
        c["test50"] = {"champ": "test50:test50/champion", "good": "test50:test50/good", "v3": "test50:test50/v3x"}.get(c["id"])
    world["spec_path"].write_text(yaml.safe_dump(spec))
    world["t50"] = t50
    return world


def test_dataset_keys_and_guard_never_pool():
    case, t50, syn = contrib_rows(0.6, seed=1), t50_rows(0.6, seed=2), contrib_rows(0.6, seed=3, prefix="Synth_x_")
    assert ds.rows_dataset(case) == "case" and ds.rows_dataset(t50) == "test50" and ds.rows_dataset(syn) == "synth"
    assert ds.row_dataset({"call_id": "Stufe1_D01-K1", "dataset": "test50"}) == "test50"
    with pytest.raises(ds.DatasetMixError):
        ds.rows_dataset(case + t50)  # one pooled set
    with pytest.raises(ds.DatasetMixError):
        ds.same_dataset([case, t50])
    with pytest.raises(ds.DatasetMixError):
        cd.mean_auc_delta([case], [t50], n_boot=50)
    with pytest.raises(ds.DatasetMixError):
        cd.mean_auc_ci([case, t50], n_boot=50)
    c = cb.compare_rows({"fixed": case}, {"fixed": t50}, n_boot=50)
    assert c["paired"] is False and c["datasets"] == ["case", "test50"] and "deltas" not in c
    with pytest.raises(ds.DatasetMixError):
        cb.compare_rows({"fixed": case + t50}, {"fixed": case}, n_boot=50)
    d = cd.unpaired_auc_delta(case, t50, n_boot=200)
    assert d["paired"] is False and d["datasets"] == ["case", "test50"] and d["diff"] is not None


def test_spec_and_roots_keep_test50_in_its_own_slot(world50: dict, tmp_path: Path):
    spec = yaml.safe_load(world50["spec_path"].read_text())
    bad = dict(spec, candidates=[dict(spec["candidates"][0], tuned="test50:test50/champion")])
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(cd.SpecError, match="never in a dev slot"):
        cd.load_spec(p)
    bad = dict(spec, candidates=[dict(spec["candidates"][0], test50="e/champ")])
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(cd.SpecError):
        cd.load_spec(p)
    # case rows copied into the test50 root by mistake are refused, not silently mixed
    write_contrib_variant(world50["t50"], "test50/wrong", contrib_rows(0.6, seed=1))
    data = cd.Data({"default": world50["root"], "test50": world50["t50"]})
    with pytest.raises(ds.DatasetMixError):
        data.get("test50:test50/wrong")


def test_test50_record_paired_over_pairs_unpaired_drop_breakdown_and_pending(world50: dict):
    res = cd.analyse(cd.load_spec(world50["spec_path"]))
    C = {c["id"]: c for c in res["candidates"]}
    ch, good = C["champ"]["test50"], C["good"]["test50"]
    assert ch["dataset"] == "test50" and ch["n_calls"] == 40 and ch["n_units"] == 13  # 6 pairs + 2 traps + 2 reviews + 1 numbers pair + 2 multi
    assert ch["fixed"]["accuracy"]["value"] is not None and "cv" in ch and "vs_ref" not in ch
    assert good["auc"]["value"] == 1.0 and good["vs_ref"]["auc"]["diff"] > 0 and good["vs_ref"]["units"] == 13
    assert good["dev_drop"]["paired"] is False and good["dev_drop"]["datasets"] == ["case", "test50"]
    assert set(ch["breakdown"]["types"]) == {"pair", "trap", "review", "numbers", "multi"}
    assert ch["breakdown"]["types"]["pair"]["n"] == 24 and ch["breakdown"]["audio"]["verrauscht"]["n"] == 20
    assert C["all"]["test50"]["auc"]["value"] == 0.5  # flag-all on the champion's test50 calls
    # the dev columns are untouched by test50 (same numbers as without the slot)
    assert C["good"]["tuned"]["n_calls"] == 24
    assert cd.cell(C["v3"], "t50_auc") == "ausstehend" and cd.cell(C["hid"], "t50_auc") == "nicht geplant"
    assert ("v3", "test50", "pending") in {(p["candidate"], p["slot"], p["status"]) for p in res["pending"]}
    assert "t50_auc" in res["best"] and res["best"]["t50_auc"]["ids"] == ["good"]
    txt = cd.fill("{{good.t50_auc}} | {{good.vs_t50_acc}} | {{good.t50_drop}} | {{v3.t50_far}}", res)
    parts = txt.split(" | ")
    assert parts[0].startswith("1.00") and parts[2].endswith("(ungepaart)") and parts[3] == "ausstehend"
    md = cd.render_markdown(res)
    sec = md.split(f"## {cd.T50_TITLE}")[1]
    assert cd.T50_BANNER in sec and "| Good | **1.00" in sec and "Stichwort-Falle" in sec
    t = tv.text_frame(res)
    assert tv.T50_PREFIX + "Flag-AUC [KI]" in t.columns
    n = tv.number_frame(res)
    assert n.loc[n["Kandidat"] == "Good", tv.T50_PREFIX + "Flag-AUC"].iloc[0] == 1.0
    assert len(tv.breakdown_frame(res)) == 3  # Champ, Good, All


def test_team_page_shows_test50_section(env: FixtureEnv):
    root = env.runs_dir.parent / "experiments"
    write_contrib_variant(root, "champion/champion", contrib_rows(0.8, seed=2))
    t50 = env.runs_dir.parent / "test50" / "experiments"
    write_contrib_variant(t50, "test50/champion", t50_rows(0.7, seed=3))
    write_contrib_variant(t50, "test50/kev_facts", t50_rows(0.6, seed=4))
    at = _run_team()
    assert any(cd.T50_BANNER in w.value for w in at.warning)
    frames = [df.value for df in at.dataframe]
    bd = next(f for f in frames if "Stichwort-Falle" in f.columns)
    assert "Champion: Qwen2.5-7B Fakten, Tabelle v1" in bd["Kandidat"].tolist()
    assert tv.T50_PREFIX + "Flag-AUC [KI]" in frames[0].columns
