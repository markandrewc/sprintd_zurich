"""``${VAR}`` / ``${VAR:-default}`` expansion in YAML profiles (config.expand_env, load_config)."""

from __future__ import annotations

from pathlib import Path

import pytest

from callguard.config import ConfigError, expand_env, load_config


def test_plain_and_default_references() -> None:
    env = {"HOST": "gpu-pc", "EMPTY": ""}
    assert expand_env("http://${HOST}:8000/v1", env) == "http://gpu-pc:8000/v1"
    assert expand_env("http://${MISSING:-127.0.0.1}:8000/v1", env) == "http://127.0.0.1:8000/v1"
    assert expand_env("${EMPTY:-fallback}", env) == "fallback"  # shell ":-": unset OR empty
    assert expand_env("${HOST:-other}", env) == "gpu-pc"
    assert expand_env("${A}/${B:-b}/${A}", {"A": "a"}) == "a/b/a"
    assert expand_env("${MISSING:-}", env) == ""
    assert expand_env("x${EMPTY}y", env) == "xy"  # set but empty, no default: "" as in the shell


def test_defaults_may_contain_colons_slashes_and_dashes() -> None:
    assert expand_env("${URL:-http://127.0.0.1:8000/v1}", {}) == "http://127.0.0.1:8000/v1"
    assert expand_env("${X:-a:-b}", {}) == "a:-b"


def test_unset_without_default_raises_with_name_and_file() -> None:
    with pytest.raises(ConfigError, match=r"CALLGUARD_GPU_HOST is not set in remote\.yaml"):
        expand_env({"llms": {"default": {"base_url": "http://${CALLGUARD_GPU_HOST}:8000"}}}, {},
                   source="remote.yaml")


@pytest.mark.parametrize("bad", ["${}", "${1X}", "${A B}", "${A:-${B}}"])
def test_malformed_and_nested_references_raise(bad: str) -> None:
    with pytest.raises(ConfigError):
        expand_env(bad, {"A": "a", "B": "b"})


def test_escape_gives_a_literal_reference() -> None:
    assert expand_env("$${HOME}", {"HOME": "/root"}) == "${HOME}"
    assert expand_env("a $${X} b ${Y:-y}", {}) == "a ${X} b y"


def test_whole_value_references_are_typed_embedded_ones_stay_text() -> None:
    env = {"T": "0.45", "N": "8", "ON": "true", "OFF": "False", "PIN": "0123", "NO": "no", "NIL": "null"}
    assert expand_env("${T}", env) == 0.45
    assert expand_env("${N}", env) == 8
    assert expand_env("${ON}", env) is True and expand_env("${OFF}", env) is False
    assert expand_env("${NIL}", env) is None
    assert expand_env("${PIN}", env) == "0123"  # leading zero: a code, not a number
    assert expand_env("${NO}", env) == "no"  # narrower than YAML 1.1 on purpose
    assert expand_env("${MISSING:-180}", env) == 180
    assert expand_env("t=${T}", env) == "t=0.45"
    assert expand_env("$${T}", env) == "${T}"  # an escape is never typed


def test_walks_dicts_and_lists_but_not_keys_or_non_strings() -> None:
    env = {"V": "v"}
    raw = {"${V}": "${V}", "n": 3, "flag": True, "none": None,
           "list": ["${V}", {"deep": "x${V}"}, 1.5], "plain": "no reference $V"}
    out = expand_env(raw, env)
    assert out == {"${V}": "v", "n": 3, "flag": True, "none": None,
                   "list": ["v", {"deep": "xv"}, 1.5], "plain": "no reference $V"}
    assert raw["list"][0] == "${V}"  # the input is not mutated


def test_load_config_expands_after_extends_and_before_set(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "parent.yaml").write_text(
        "asr: {type: reference}\n"
        "llms: {default: {type: fake, base_url: 'http://${CG_TEST_HOST:-parent-default}:8000/v1'}}\n"
        "fusion: {type: weighted, threshold: '${CG_TEST_THRESHOLD:-0.55}'}\n")
    (tmp_path / "child.yaml").write_text(
        "extends: parent.yaml\n"
        "description: 'on ${CG_TEST_HOST:-nowhere}'\n")
    monkeypatch.setenv("CG_TEST_HOST", "gpu-pc")
    monkeypatch.delenv("CG_TEST_THRESHOLD", raising=False)
    cfg = load_config(tmp_path / "child.yaml", ["sinks=[]", "app.base_url=http://${NOT_EXPANDED}"])
    assert cfg.llms["default"]["base_url"] == "http://gpu-pc:8000/v1"  # parent value, child's env
    assert cfg.description == "on gpu-pc"
    assert cfg.fusion["threshold"] == 0.55 and isinstance(cfg.fusion["threshold"], float)
    assert cfg.app["base_url"] == "http://${NOT_EXPANDED}"  # --set is applied literally, after expansion

    monkeypatch.delenv("CG_TEST_HOST")
    assert load_config(tmp_path / "child.yaml").llms["default"]["base_url"] == "http://parent-default:8000/v1"


def test_load_config_unset_variable_names_the_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CG_TEST_REQUIRED", raising=False)
    p = tmp_path / "needs.yaml"
    p.write_text("asr: {type: reference}\nllms: {default: {type: fake, model: '${CG_TEST_REQUIRED}'}}\n")
    with pytest.raises(ConfigError, match=r"CG_TEST_REQUIRED is not set in needs\.yaml"):
        load_config(p)
    monkeypatch.setenv("CG_TEST_REQUIRED", "m")
    assert load_config(p).llms["default"]["model"] == "m"


def test_shipped_profiles_load_without_any_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every reference in the shipped profiles has a default: no profile needs an env var to load."""
    for var in ("CALLGUARD_GPU_HOST", "CALLGUARD_LLM_URL", "CALLGUARD_TOKEN", "CALLGUARD_LLM_TAG",
                "CALLGUARD_UI_HOST"):
        monkeypatch.delenv(var, raising=False)
    root = Path(__file__).resolve().parents[1] / "config"
    for p in sorted(root.glob("*.yaml")):
        if p.name in ("criteria.yaml", "splits.yaml", "policy_table.yaml", "routing.yaml", "directory.yaml",
                      "tuning.yaml", "synth_scenarios.yaml", "open_facts.yaml", "pruefmodi.yaml", "fact_policy.yaml")\
                or p.name.startswith(("policy_table", "general_questions")):
            continue  # data files, not profiles
        cfg = load_config(p)
        assert "${" not in repr(cfg.model_dump()), p.name
