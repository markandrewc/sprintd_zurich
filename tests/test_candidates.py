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
    assert heads[:3] == ["Optionen für das Team: Kandidaten-Matrix",
                         "Abgestimmt gegen andere Bedingungen: wie viel ist Dev-Anpassung?", "Offene Entscheidungen"]
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
    assert [s.value for s in at.subheader][1] == "Offene Entscheidungen"


def test_team_page_is_registered_next_to_entscheidungshilfe():
    from callguard.ui import pages_registry as pr

    keys = [p.key for p in pr.pages()]
    assert keys.index("team") == keys.index("decisions") + 1
    assert next(p for p in pr.pages() if p.key == "team").path().name == "team.py"
