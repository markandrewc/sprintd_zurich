"""Synthetic script kit (callguard.synth) + text-only data sets + the `external` split. Offline: a fake
writer LLM stands in for the served model."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from callguard import experiments as ex
from callguard import splits as sp
from callguard.data import Call, Expected, load_calls, split_dialogues
from callguard.synth import scenarios as sc
from callguard.synth import scripts as sw

ROOT = Path(__file__).resolve().parents[1]


# -- fake writer -------------------------------------------------------------------------------------


class FakeWriter:
    """Writes a valid script from the prompt's frame (speakers, opener, length, must-include words);
    rewrites change the last two turns. ``bad_first`` = number of invalid answers before valid ones."""

    model_id = "fake-writer"

    def __init__(self, bad_first: int = 0):
        self.calls = 0
        self.bad_first = bad_first

    def ping(self) -> bool:
        return True

    def list_models(self):
        return [{"id": "callguard-llm"}]

    def chat(self, messages, **kw):
        self.calls += 1
        user = messages[-1]["content"]
        if self.calls <= self.bad_first:
            return ['{"title": "x", "turns": [{"speaker": "Beratung", "text": "zu kurz"}], "evidence_turns": []}']
        if "Bestehendes Gespräch (JSON):" in user:
            base = json.loads(user.split("Bestehendes Gespräch (JSON):\n", 1)[1].split("\n\nRahmen", 1)[0])
            for t in base["turns"][-2:]:
                t["text"] = t["text"] + " Aber hüt isch alles chli andersch gloffe als planet."
            return [json.dumps(base, ensure_ascii=False)]
        customer = re.search(r'Sprecher-Bezeichnungen: "Beratung" und "(\w+)"', user).group(1)
        first = re.search(r'\(Turn 1 = "(\w+)"\)', user).group(1)
        n = int(re.search(r"ungefähr (\d+) Turns", user).group(1))
        musts = re.findall(r'"([^"]+)"', (re.search(r"wörtlich vorkommen: (.*)\.\n", user) or [None, ""])[1])
        other = customer if first == "Beratung" else "Beratung"
        turns = [{"speaker": first if i % 2 == 0 else other,
                  "text": f"Das isch de Turn {i + 1}, mir reded über {' und '.join(musts) or 'd Rechnig'} und so."}
                 for i in range(n)]
        return [json.dumps({"title": "Ein Testgespräch", "turns": turns, "evidence_turns": [3, 4]},
                           ensure_ascii=False)]


def _small_jobs(n_scen: int = 2) -> list[sc.Job]:
    scen = sc.load_scenarios()
    return sc.plan(scen[:n_scen])


# -- scenarios -------------------------------------------------------------------------------------------


def test_scenario_file_loads_and_covers_families():
    scen = sc.load_scenarios()
    jobs = sc.plan(scen)
    assert 60 <= len(jobs) <= 90
    assert len({j.dialogue_id for j in jobs}) == len(jobs)
    assert all(re.fullmatch(r"Synth_[a-z]+_\d{3}", j.dialogue_id) for j in jobs)
    summ = sc.summary(jobs)
    for fam in ("trade", "access", "disclosure", "documentation", "splitting"):
        assert summ[fam].get("alarm") and summ[fam].get("no_alert") and summ[fam].get("review"), fam
    assert set(summ["numbers"]) == {"no_alert"}
    assert all(len(s.variants) >= 2 for s in scen)
    # twins are consecutive and the first variant of each scenario is the base
    for s in scen:
        js = [j for j in jobs if j.scenario.id == s.id]
        assert js[0].base and not any(j.base for j in js[1:])
        assert all(j.dialogue_id.startswith(f"Synth_{s.family}_") for j in js)


@pytest.mark.parametrize("patch,msg", [
    ({"label": "maybe"}, "label"),
    ({"label": "review"}, "open"),
    ({"family": "numbers"}, "numbers never alarms"),
    ({"decisive": ""}, "decisive"),
])
def test_scenario_validation_errors(patch, msg):
    v = {"label": "alarm", "decisive": "x passiert", "reason": "weil"}
    raw = {"families": {"trade": [{"id": "s1", "setting": "eine Situation",
                                   "variants": {"a": {**v, **patch}, "b": {**v, "label": "no_alert"}}}]}}
    with pytest.raises(sc.ScenarioError, match=msg):
        sc.parse_scenarios(raw)


def test_scenario_needs_twins_and_unique_ids():
    v = {"label": "alarm", "decisive": "x", "reason": "y"}
    with pytest.raises(sc.ScenarioError, match="two variants"):
        sc.parse_scenarios({"families": {"trade": [{"id": "s", "setting": "z", "variants": {"a": v}}]}})
    two = {"a": v, "b": {**v, "label": "no_alert"}}
    with pytest.raises(sc.ScenarioError, match="duplicate"):
        sc.parse_scenarios({"families": {"trade": [{"id": "s", "setting": "z", "variants": two}] * 2}})


# -- validators -----------------------------------------------------------------------------------------


def _job() -> sc.Job:
    return sc.plan(sc.load_scenarios())[0]  # trade_pharma_approval / alarm, Kunde opens, 18 turns


def _data(job: sc.Job, n: int | None = None, first: str | None = None, extra: str = "") -> dict:
    s = job.scenario
    n = n or s.turns
    a = first or (s.customer if s.opens == "customer" else "Beratung")
    b = "Beratung" if a == s.customer else s.customer
    turns = [{"speaker": a if i % 2 == 0 else b, "text": f"Turn {i + 1} über d Alpstein Aktie, gell. {extra}"}
             for i in range(n)]
    return {"title": "T", "turns": turns, "evidence_turns": [5, 6]}


def test_validate_script_accepts_good_output():
    job = _job()
    script, errs = sw.validate_script(_data(job), job)
    assert errs == [] and script is not None and len(script.turns) == job.scenario.turns
    assert script.turns[0][0] == "Kunde" and script.evidence == [5, 6]


def test_validate_script_rejects_bad_output():
    job = _job()
    _, errs = sw.validate_script(_data(job, n=6), job)
    assert any("Turns, verlangt" in e for e in errs)
    _, errs = sw.validate_script(_data(job, first="Beratung"), job)
    assert any("Turn 1" in e for e in errs)
    _, errs = sw.validate_script(_data(job, extra="Das isch es Szenario."), job)
    assert any("Meta-Wort" in e for e in errs)
    d = _data(job)
    for t in d["turns"]:
        t["text"] = t["text"].replace("Alpstein", "Firma")
    _, errs = sw.validate_script(d, job)
    assert any("Alpstein" in e for e in errs)
    d = _data(job)
    d["evidence_turns"] = [99]
    _, errs = sw.validate_script(d, job)
    assert any("evidence_turns" in e for e in errs)
    d = _data(job)
    d["turns"][3]["speaker"] = "Erzähler"
    _, errs = sw.validate_script(d, job)
    assert any("unbekannter Sprecher" in e for e in errs)
    _, errs = sw.validate_script("nope", job)
    assert errs


def test_twin_must_differ_but_stay_close():
    job = _job()
    base, _ = sw.validate_script(_data(job), job)
    _, errs = sw.validate_script(_data(job), job, base)
    assert any("identisch" in e for e in errs)
    far = _data(job)
    for i, t in enumerate(far["turns"]):
        t["text"] = f"Ganz en andere Satz Nummer {i} mit Alpstein drin, wo nüt mit em Original z tue hät."
    _, errs = sw.validate_script(far, job, base)
    assert any("weicht zu stark ab" in e for e in errs)


def test_number_match_ignores_thousands_separators():
    assert sw._contains("Er zahlt 1280 Franke", "1'280")
    assert sw._contains("Er zahlt 1’280 Franke", "1'280")
    assert not sw._contains("Er zahlt 1290 Franke", "1'280")


# -- writing + text-only loading --------------------------------------------------------------------------


def test_generate_set_writes_case_layout_and_resumes(tmp_path):
    jobs = _small_jobs(2)
    w = FakeWriter(bad_first=1)
    res = sw.generate_set(jobs, w, tmp_path, workers=1)
    assert all(o.ok for o in res), [o.errors for o in res]
    assert res[0].attempts == 2 and res[0].mode == "free"  # first answer invalid -> retried with feedback
    assert {o.mode for o in res if o.job.base} == {"free"} and {o.mode for o in res if not o.job.base} == {"rewrite"}
    man = json.loads((tmp_path / "manifest.json").read_text())
    assert set(man["scripts"]) == {j.dialogue_id for j in jobs}
    assert man["scripts"][jobs[0].dialogue_id]["model"] == "fake-writer"
    assert sw.validate_set(tmp_path, jobs) == {}
    head = (tmp_path / "Skript_mit_Sollbewertung" / f"{jobs[0].dialogue_id}.txt").read_text()
    assert "Bearbeitung: alarm" in head and f"Gruppe: {jobs[0].scenario.id}" in head
    assert (tmp_path / "Transkript" / f"{jobs[0].dialogue_id}.txt").read_text().startswith("T001 · ")
    # resume: nothing is asked again
    n = w.calls
    again = sw.generate_set(jobs, w, tmp_path, workers=2)
    assert w.calls == n and all(o.mode == "existing" for o in again)
    # text-only calls
    calls = load_calls(tmp_path)
    assert [c.call_id for c in calls] == sorted(f"{j.dialogue_id}-K1" for j in jobs)
    c = next(c for c in calls if c.dialogue_id == jobs[0].dialogue_id)
    assert c.text_only and c.level == 0 and not c.noisy and c.audio_path.suffix == ".txt"
    assert c.group == jobs[0].scenario.id and c.expected.label == jobs[0].variant.label
    assert c.expected.evidence_turns == ["T003", "T004"] and len(c.turns) == jobs[0].scenario.turns


def test_generation_failure_is_reported_not_written(tmp_path):
    class Broken(FakeWriter):
        def chat(self, messages, **kw):
            self.calls += 1
            raise RuntimeError("server swapping")

    jobs = _small_jobs(1)[:1]
    o = sw.generate_one(jobs[0], Broken(), attempts=2, request_retries=1, sleep=lambda s: None)
    assert not o.ok and o.attempts == 2 and any("swapping" in e for e in o.errors)


def test_wait_for_llm_gives_up_and_succeeds():
    slept = []

    class Down:
        def ping(self):
            return False

    assert sw.wait_for_llm(Down(), budget_s=0.0, sleep=slept.append) is False
    assert sw.wait_for_llm(FakeWriter(), budget_s=10, sleep=slept.append) is True


def test_load_calls_keeps_audio_behaviour(tmp_path):
    (tmp_path / "Audio").mkdir()
    (tmp_path / "Transkript").mkdir()
    (tmp_path / "Audio" / "Stufe1_D99-K2.wav").write_bytes(b"")
    (tmp_path / "Transkript" / "Stufe1_D99.txt").write_text("T001 · Beratung\nGrüezi mitenand\n")
    (tmp_path / "Transkript" / "Stufe1_D98.txt").write_text("T001 · Beratung\nNur Text\n")
    calls = load_calls(tmp_path)  # Audio/ exists: audio calls only, as before
    assert [c.call_id for c in calls] == ["Stufe1_D99-K2"] and calls[0].noisy and not calls[0].text_only
    forced = load_calls(tmp_path, text_only=True)
    assert [c.call_id for c in forced] == ["Stufe1_D98-K1", "Stufe1_D99-K1"] and forced[0].level == 1


# -- folds, groups, external split -----------------------------------------------------------------------


def _call(d: str, label: str, group: str = "") -> Call:
    return Call(call_id=f"{d}-K1", dialogue_id=d, level=0, variant=1, noisy=False, audio_path=Path(d),
                expected=Expected(label=label, family="trade", event="", reason="", open_question=""), group=group)


def test_split_dialogues_keeps_twin_groups_together():
    calls = [_call(f"Synth_trade_{i:03d}", ["alarm", "no_alert", "review"][i % 3], group=f"g{i // 3}")
             for i in range(30)]
    folds = split_dialogues(calls, n_folds=5)
    for g in {c.group for c in calls}:
        assert len({folds[c.dialogue_id] for c in calls if c.group == g}) == 1
    assert len(set(folds.values())) == 5
    # without groups: one unit per dialogue, deterministic
    plain = [_call(f"D{i:02d}", "alarm" if i % 2 else "no_alert") for i in range(10)]
    assert split_dialogues(plain) == split_dialogues(list(plain))
    assert len(split_dialogues(plain)) == 10


def test_external_split_excludes_case_dialogues_and_is_not_logged():
    s = sp.Splits(holdout=["Stufe1_D07"], dev_folds={0: ["Stufe1_D01"], 1: ["Stufe1_D02"]})
    calls = [_call("Stufe1_D07", "alarm"), _call("Stufe1_D01", "alarm"), _call("Synth_trade_001", "alarm", "g")]
    assert [c.dialogue_id for c in s.select(calls, sp.EXTERNAL)] == ["Synth_trade_001"]
    assert [c.dialogue_id for c in ex.select_calls(calls, sp.EXTERNAL, s)] == ["Synth_trade_001"]
    assert [c.dialogue_id for c in ex.select_calls(calls, sp.EXTERNAL, None)] == [c.dialogue_id for c in calls]
    assert not ex.is_logged_split(sp.EXTERNAL) and not ex.holdout_test_folds(sp.EXTERNAL, s)
    synth = [_call(f"Synth_trade_{i:03d}", "alarm" if i % 2 else "no_alert", f"g{i // 2}") for i in range(8)]
    folds = ex.cv_fold_map(sp.EXTERNAL, s, synth)
    assert set(folds) == {c.dialogue_id for c in synth}
    assert ex.cv_fold_map("dev", s, synth) == s.dev_fold_of()


def test_synth_profile_and_spec_parse():
    from callguard.config import load_config
    cfg = load_config("synth-oracle")
    assert cfg.asr["type"] == "reference" and cfg.asr.get("scale_to_audio") is False
    assert str(cfg.paths.resolve("data_dir")).endswith("data_synth/v1")
    spec = ex.load_spec(ROOT / "experiments/synth_stress.yaml")
    assert spec.split == sp.EXTERNAL and spec.baseline == "v1"
    assert {v.name for v in spec.variants} >= {"v1", "facts_only", "judge_facts"}
    assert ex.is_oracle(spec.variants[0], ex.variant_config(spec, spec.variants[0]))


def test_offline_experiment_on_synthetic_text(tmp_path):
    """Full chain on a text-only set: reference ASR reads the scripts, fake LLM checks, external split,
    CV folds by twin group, nothing logged as a holdout look."""
    jobs = _small_jobs(4)
    data = tmp_path / "set"
    sw.generate_set(jobs, FakeWriter(), data, workers=1)
    base = [f"paths.data_dir={data}", "asr.scale_to_audio=false", f"paths.runs_dir={tmp_path / 'runs'}",
            f"paths.cache_dir={tmp_path / 'cache'}"]
    spec = ex.parse_spec({"name": "s", "base": "demo-offline", "split": "external",
                          "variants": [{"name": "all", "set": base},
                                       {"name": "rules", "refuse_from": "all", "checks": ["keywords", "patterns"]}]})
    calls = ex.select_calls(load_calls(data), spec.split, sp.load_splits(required=False))
    assert len(calls) == len(jobs)
    summary = ex.run_experiment(spec, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=200)
    a = summary["variants"]["all"]
    assert a["n_calls"] == len(jobs) and not a["errors"] and a["oracle"]
    assert a["cv"] is not None and len(a["cv_folds"]) >= 2
    rows = json.loads((tmp_path / "runs/experiments/s/all/rows.json").read_text())
    assert all(r.get("group") for r in rows["fixed"])
    for f in a["cv_folds"]:  # twins never split across folds
        groups = {next(j.scenario.id for j in jobs if j.dialogue_id == d) for d in f["dialogues"]}
        others = [g for g in a["cv_folds"] if g is not f]
        for o in others:
            assert not groups & {next(j.scenario.id for j in jobs if j.dialogue_id == d) for d in o["dialogues"]}
    assert not (tmp_path / "runs" / "holdout_log.jsonl").exists()
