from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from callguard import splits as sp
from callguard.config import load_config
from callguard.data import Call, Expected, load_calls

DATA = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/data"


def calls_like_case() -> list[Call]:
    """30 dialogues x (clean, noisy) with the case's label/level mix."""
    mix = [("alarm", 1)] * 6 + [("no_alert", 1)] * 4 + [("alarm", 2)] * 6 + [("no_alert", 2)] * 10 + \
          [("review", 3)] * 4
    out = []
    for i, (label, level) in enumerate(mix):
        d = f"Stufe{level}_X{i:02d}"
        for k in (1, 2):
            out.append(Call(call_id=f"{d}-K{k}", dialogue_id=d, level=level, variant=k, noisy=k == 2,
                            audio_path=Path(f"/nonexistent/{d}-K{k}.wav"),
                            expected=Expected(label=label, family="trade", event="", reason="", open_question="")))
    return out


def test_make_splits_shape_and_stratification():
    calls = calls_like_case()
    s = sp.make_splits(calls, n_dev_folds=4, seed=13)
    assert len(s.holdout) == 6 and sorted(len(v) for v in s.dev_folds.values()) == [6, 6, 6, 6]
    every = s.holdout + [d for v in s.dev_folds.values() for d in v]
    assert len(every) == len(set(every)) == 30
    label = {c.dialogue_id: c.expected.label for c in calls}
    level = {c.dialogue_id: c.level for c in calls}
    hl = Counter(label[d] for d in s.holdout)
    assert hl["alarm"] in (2, 3) and hl["no_alert"] in (2, 3) and hl["review"] == 1
    assert Counter(level[d] for d in s.holdout)[3] == 1
    for fold in s.dev_folds.values():  # every dev fold sees alarms and harmless calls
        labels = Counter(label[d] for d in fold)
        assert labels["alarm"] >= 2 and labels["no_alert"] >= 2


def test_make_splits_deterministic():
    calls = calls_like_case()
    assert sp.make_splits(calls).holdout == sp.make_splits(calls).holdout


def test_write_refuses_overwrite_and_roundtrips(tmp_path):
    calls = calls_like_case()
    p = tmp_path / "splits.yaml"
    s = sp.make_splits(calls)
    sp.write_splits(s, calls, p)
    with pytest.raises(FileExistsError):
        sp.write_splits(s, calls, p)
    back = sp.load_splits(p)
    assert back.holdout == s.holdout and back.dev_folds == s.dev_folds
    assert p.read_text().startswith("# LOCKED")


def test_select_keeps_clean_and_noisy_together(tmp_path):
    calls = calls_like_case()
    s = sp.make_splits(calls)
    dev, hold = s.select(calls, "dev"), s.select(calls, "holdout")
    assert len(dev) == 48 and len(hold) == 12 and len(s.select(calls, "all")) == 60
    assert {c.dialogue_id for c in dev}.isdisjoint({c.dialogue_id for c in hold})
    assert set(Counter(c.dialogue_id for c in hold).values()) == {2}
    assert set(s.dev_fold_of().values()) == {0, 1, 2, 3}
    assert set(s.all_fold_of().values()) == {0, 1, 2, 3, 4}
    assert s.fold_of()[s.holdout[0]] == sp.HOLDOUT
    with pytest.raises(ValueError):
        s.select(calls, "test")


def test_load_rejects_dialogue_in_two_folds(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("holdout: [A]\ndev_folds:\n  0: [A, B]\n  1: [C]\n")
    with pytest.raises(ValueError, match="more than one fold"):
        sp.load_splits(p)
    with pytest.raises(sp.SplitsMissing):
        sp.load_splits(tmp_path / "missing.yaml")
    assert sp.load_splits(tmp_path / "missing.yaml", required=False) is None


def test_module_helpers_read_the_file(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("holdout: [H1]\ndev_folds:\n  0: [A]\n  1: [B]\n")
    assert sp.dev_dialogues(p) == ["A", "B"] and sp.holdout_dialogues(p) == ["H1"]
    assert sp.fold_of(p) == {"H1": "holdout", "A": 0, "B": 1}


def test_holdout_log_appends(tmp_path):
    cfg = load_config("base", [f"paths.runs_dir={tmp_path}"])
    m = {"flag": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "false_alarm_rate": 0.2, "miss_rate": 0.5},
         "alarm": {"f1": 0.4}, "accuracy": 0.6, "errors": 0}
    assert sp.holdout_looks(cfg) == 0
    sp.log_holdout_run(cfg, m, 12)
    sp.log_holdout_run(cfg, m, 12, kind="experiment x/y")
    assert sp.holdout_looks(cfg) == 2
    import json
    first = json.loads((tmp_path / "holdout_log.jsonl").read_text().splitlines()[0])
    assert first["config"] == "base" and first["metrics"]["flag_f1"] == 0.5 and first["config_hash"]
    assert "sha" in first["git"]


@pytest.mark.skipif(not DATA.exists(), reason="case data not available")
def test_committed_split_covers_the_case_data():
    s = sp.load_splits()
    calls = load_calls(DATA)
    dialogues = {c.dialogue_id for c in calls}
    assert set(s.fold_of()) == dialogues and len(s.holdout) == 6 and len(s.dev_folds) == 4
    labels = Counter(c.expected.label for c in calls if c.dialogue_id in s.holdout and not c.noisy)
    assert set(labels) == {"alarm", "review", "no_alert"}


def calls_with_twins() -> list[Call]:
    """Case-like set where the Stufe2 dialogues come in twin pairs (same title + family)."""
    out = []
    for c in calls_like_case():
        if c.level == 2:
            i = int(c.dialogue_id[-2:])
            c.title = f"C{i:02d} · Twin story {i // 2}"
        else:
            c.title = f"D{c.dialogue_id[-2:]} · Story {c.dialogue_id}"
        out.append(c)
    return out


def test_twins_found_and_kept_in_one_fold():
    calls = calls_with_twins()
    twins = sp.find_twins(calls)
    assert len(twins) == 8 and all(len(v) == 2 for v in twins.values())
    s = sp.make_splits(calls)
    fold = s.fold_of()
    for ds in twins.values():
        assert fold[ds[0]] == fold[ds[1]]
    assert len(s.holdout) == 6 and sorted(len(v) for v in s.dev_folds.values()) == [6, 6, 6, 6]
    g = next(iter(twins))
    assert s.group_of(twins[g][0] + "-K2") == g and s.group_of("Stufe1_X00-K1") == "Stufe1_X00"


def test_twin_group_split_across_folds_is_rejected(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text("holdout: [A]\ndev_folds:\n  0: [B]\n  1: [C]\ngroups:\n  A+B: [A, B]\n")
    with pytest.raises(ValueError, match="split across folds"):
        sp.load_splits(p)


def test_group_of_falls_back_to_dialogue(tmp_path):
    assert sp.group_of("X_D01-K1", tmp_path / "missing.yaml") == "X_D01"
    p = tmp_path / "s.yaml"
    p.write_text("holdout: [A]\ndev_folds:\n  0: [B, C]\ngroups:\n  B+C: [B, C]\n")
    assert sp.group_of("C-K2", p) == "B+C" and sp.group_of("A-K1", p) == "A"


@pytest.mark.skipif(not DATA.exists(), reason="case data not available")
def test_committed_split_keeps_case_twins_together():
    s = sp.load_splits()
    assert len(s.groups) == 8
    assert sp.find_twins(load_calls(DATA)) == s.groups
