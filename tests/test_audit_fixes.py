"""Regression tests for the research-harness audit (F1..F6): FAR-cap aware leaderboard, split protocol,
live LLM identity in experiments, G-Eval steps fallback, re-fusion provenance, twin-group bootstrap and
weight-aware DEGRADED. Known-answer where possible."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
import soundfile as sf
from typer.testing import CliRunner

from callguard import cli
from callguard import eval as ev
from callguard import experiments as ex
from callguard import report
from callguard.checks import prompts
from callguard.checks.geval import BASE_STEPS_PROMPT_VERSION, GEvalCheck
from callguard.checks.llm_judge import LLMCheck
from callguard.config import AppConfig, Paths, load_config
from callguard.context import Context
from callguard.data import Call, Expected, load_calls
from callguard.llm.openai_compat import LLMIdentityError, OpenAICompatLLM
from callguard.types import CallResult, CheckResult, Decision, Family, FamilyScore, Segment, Transcript

DATA = Path(__file__).resolve().parents[1] / "data_upstream/inventx-case-study/data"
needs_data = pytest.mark.skipif(not DATA.exists(), reason="case data not available")
runner = CliRunner()
CALLS = ["Stufe1_D01-K1", "Stufe1_D01-K2", "Stufe1_D02-K1", "Stufe1_D02-K2", "Stufe1_D04-K1", "Stufe1_D04-K2",
         "Stufe1_D05-K1", "Stufe2_C05-K1", "Stufe2_C09-K1", "Stufe3_C17-K1", "Stufe3_C18-K1"]


def spec(tmp_path: Path, variants: list[dict], **kw: Any) -> ex.Spec:
    s = ex.parse_spec({"name": "t", "base": "demo-offline", "split": "dev", "variants": variants, **kw})
    for v in s.variants:
        if not v.refuse_from:
            v.set = [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}", *v.set]
    return s


# --------------------------------------------------------------------------------------------
# F1: FAR floor, cap reachability, leaderboard ranking
# --------------------------------------------------------------------------------------------


def _swept(points):
    return [{"threshold": t, "metrics": {"n": 10, "flag": {"recall": r, "false_alarm_rate": f, "f1": f1}}}
            for t, r, f, f1 in points]


def test_pick_recall_at_far_reports_cap_reachability():
    assert ex.pick_recall_at_far(_swept([(0.5, 0.8, 0.1, 0.7)]))["cap_reachable"] is True
    p = ex.pick_recall_at_far(_swept([(0.5, 0.9, 0.5, 0.7), (1.0, 0.6, 0.4, 0.6)]))
    assert p["cap_reachable"] is False and p["threshold"] == 1.0 and "lowest FAR" in p["reason"]


class ReviewRulePipe:
    """Fusion stand-in: calls whose id is in ``always_review`` are labelled review whatever the threshold
    (like uncertainty escalation); the rest are alarm iff their score >= threshold."""

    def __init__(self, always_review: set[str]):
        self.always_review = always_review
        self.cfg = AppConfig(name="stub", asr={"type": "reference"})
        fam = Family(id="trade", label="Insider", keywords=[], can_alarm=True)
        self.ctx = type("Ctx", (), {"families": staticmethod(lambda: [fam])})()
        self.checks: list[Any] = []

    def decide(self, transcript, checks, overrides, families):
        t = (overrides or {}).get("threshold", 0.5)
        score = transcript.meta["score"]
        if transcript.call_id in self.always_review:
            label = "review"
        else:
            label = "alarm" if score >= t else "no_alert"
        return Decision(label=label, score=score, uncertainty=0.0, threshold=t)


NO_DECISION = Decision(label="no_alert", score=0.0, uncertainty=0.0, threshold=0.5)


def _result(call_id: str, score: float) -> CallResult:
    t = Transcript(call_id=call_id, segments=[Segment(id="S001", start=0, end=1, text="x")], meta={"score": score})
    return CallResult(call_id=call_id, transcript=t, decision=NO_DECISION)


def _calls(labels: dict[str, str]) -> list[Call]:
    return [Call(call_id=c, dialogue_id=c.split("-K")[0], level=1, variant=1, noisy=False, audio_path=Path(c),
                 expected=Expected(label=lab, family="trade", event="", reason="", open_question=""))
            for c, lab in labels.items()]


def test_far_floor_and_fold_fallback_known_answer():
    # 4 harmless calls in 4 folds, two of them escalated by a review rule: FAR >= 50% at every threshold
    labels = {"A1-K1": "no_alert", "A2-K1": "no_alert", "A3-K1": "no_alert", "A4-K1": "no_alert",
              "B1-K1": "alarm", "B2-K1": "alarm", "B3-K1": "alarm", "B4-K1": "alarm"}
    scores = {"A1-K1": 0.1, "A2-K1": 0.2, "A3-K1": 0.1, "A4-K1": 0.2,
              "B1-K1": 0.9, "B2-K1": 0.8, "B3-K1": 0.9, "B4-K1": 0.8}
    results = [_result(c, s) for c, s in scores.items()]
    pipe = ReviewRulePipe({"A1-K1", "A2-K1"})
    calls = _calls(labels)
    floor = ex.far_floor(pipe, results, calls)
    assert floor["false_alarm_rate"] == 0.5 and floor["cap_reachable"] is False and floor["fp"] == 2
    fold_of = {"A1": 0, "B1": 0, "A2": 1, "B2": 1, "A3": 2, "B3": 2, "A4": 3, "B4": 3}
    rows, folds = ex.cv_predict(pipe, results, calls, fold_of, policy="recall_at_far")
    assert len(folds) == 4
    # training folds always contain at least one escalated harmless call out of 3: FAR >= 1/3 > 20%
    assert all(f["fallback"] and not f["cap_reachable"] for f in folds)
    # without the review rule the cap is reachable everywhere
    _, folds2 = ex.cv_predict(ReviewRulePipe(set()), results, calls, fold_of, policy="recall_at_far")
    assert not any(f["fallback"] for f in folds2)


def test_cv_predict_never_fits_on_test_only_folds():
    # fold 2 (the "holdout": three harmless calls at 0.9, an alarm at 0.95) pulls the max-F1 threshold
    # of fold 0 from 0.5 to 0.95 if it is used for fitting
    labels = {"A1-K1": "no_alert", "B1-K1": "alarm", "A2-K1": "no_alert", "B2-K1": "alarm",
              "A3-K1": "no_alert", "A5-K1": "no_alert", "A6-K1": "no_alert", "B3-K1": "alarm"}
    scores = {"A1-K1": 0.3, "B1-K1": 0.6, "A2-K1": 0.3, "B2-K1": 0.6, "A3-K1": 0.9, "A5-K1": 0.9,
              "A6-K1": 0.9, "B3-K1": 0.95}
    results, calls = [_result(c, x) for c, x in scores.items()], _calls(labels)
    fold_of = {"A1": 0, "B1": 0, "A2": 1, "B2": 1, "A3": 2, "A5": 2, "A6": 2, "B3": 2}
    pipe = ReviewRulePipe(set())
    _, leaky = ex.cv_predict(pipe, results, calls, fold_of, thresholds=[0.5, 0.95])
    assert {f["fold"]: f["threshold"] for f in leaky}[0] == 0.95
    _, folds = ex.cv_predict(pipe, results, calls, fold_of, thresholds=[0.5, 0.95], test_only={2})
    by = {f["fold"]: f for f in folds}
    assert by[0]["threshold"] == 0.5 and by[2].get("test_only") and not by[0].get("test_only")
    _, none = ex.cv_predict(pipe, results[:2] + results[4:], calls, fold_of, test_only={2})
    assert none == []  # one trainable fold left: no CV


def _summary(name: str, variants: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"experiment": name, "split": "dev", "far_cap": 0.2, "variants": variants}


def _v(auc: float, far20_far: float, far20_recall: float, far20_f1: float, floor: float | None = None):
    return {"auc": {"flag": {"value": auc}}, "fixed": {"flag_f1": 0.7}, "cv": {"flag_f1": 0.7},
            "cv_far": {"flag_f1": far20_f1, "flag_recall": far20_recall, "false_alarm_rate": far20_far},
            "cap": {"floor": {"false_alarm_rate": floor}, "folds_reachable": 0 if floor and floor > 0.2 else 4,
                    "folds": 4}, "meta": {}}


def test_leaderboard_ranks_cap_compliant_variants_first():
    s = _summary("fusion", {
        "unc025": _v(0.90, 0.95, 1.0, 0.70, floor=0.9),   # best AUC, violates the cap
        "llmunc": _v(0.70, 0.18, 0.50, 0.55, floor=0.1),
        "abstain": _v(0.60, 0.15, 0.60, 0.58, floor=0.05),
        "band020": _v(0.80, 0.40, 0.90, 0.65, floor=0.3),
    })
    rows = report.leaderboard_rows([s])
    assert [r["variant"] for r in rows] == ["abstain", "llmunc", "band020", "unc025"]
    assert rows[0]["compliant"] is True and rows[-1]["compliant"] is False
    md = report.render_leaderboard(rows)
    assert "**over**" in md and "FAR floor" in md and "not decision-consistent" in md


# --------------------------------------------------------------------------------------------
# F2: split protocol
# --------------------------------------------------------------------------------------------


@needs_data
def test_eval_defaults_to_dev_and_split_all_is_logged(tmp_path):
    from callguard import splits as sp
    s = sp.load_splits()
    hold = [c.call_id for c in load_calls(DATA) if c.dialogue_id in s.holdout and not c.noisy][:1]
    args = ["eval", "-c", "demo-offline", "--set", f"paths.runs_dir={tmp_path / 'runs'}",
            "--set", f"paths.cache_dir={tmp_path / 'cache'}", "--no-write-results",
            "--calls", ",".join(hold + ["Stufe1_D02-K1", "Stufe1_D03-K1"])]
    r = runner.invoke(cli.app, args)
    assert r.exit_code == 0, r.output
    rep = json.loads((tmp_path / "runs/demo-offline/eval_dev/report.json").read_text())
    assert rep["meta"]["split"] == "dev" and rep["metrics"]["n"] == 2  # holdout call left out by default
    assert not (tmp_path / "runs/holdout_log.jsonl").exists()
    r = runner.invoke(cli.app, [*args, "--split", "all"])
    assert r.exit_code == 0, r.output
    log = [json.loads(x) for x in (tmp_path / "runs/holdout_log.jsonl").read_text().splitlines()]
    assert len(log) == 1 and log[0]["kind"] == "eval (split all)" and log[0]["n_calls"] == 3


@needs_data
def test_experiment_cli_needs_explicit_holdout_split(tmp_path):
    spec_path = tmp_path / "h.yaml"
    sets = [f"paths.runs_dir={tmp_path / 'runs'}", f"paths.cache_dir={tmp_path / 'cache'}"]
    spec_path.write_text(json.dumps({"name": "h", "base": "demo-offline", "split": "holdout",
                                     "variants": [{"name": "a", "set": sets}]}))
    r = runner.invoke(cli.app, ["experiment", str(spec_path), "--n-boot", "100"])
    assert r.exit_code == 2 and "explicitly" in r.output
    assert not (tmp_path / "runs/holdout_log.jsonl").exists()


@needs_data
def test_experiment_split_all_is_logged_and_fits_on_dev_only(tmp_path):
    from callguard import splits as sp
    hold = sp.load_splits().holdout
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS or (c.dialogue_id in hold and not c.noisy)]
    s = spec(tmp_path, [{"name": "a"}], split="all")
    summary = ex.run_experiment(s, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=100)
    log = [json.loads(x) for x in (tmp_path / "runs/holdout_log.jsonl").read_text().splitlines()]
    assert len(log) == 1 and "split all" in log[0]["kind"]
    folds = summary["variants"]["a"]["cv_far_folds"]
    assert sum(1 for f in folds if f.get("test_only")) == 1  # the holdout: scored, never fitted on


def _asr_case(root: Path) -> Path:
    from test_eval_asr import HEADER, LINE_D05, SCRIPT, _case
    d = _case(root)  # Stufe1_D02 (dev)
    sf.write(str(d / "Audio" / "Stufe1_D07-K1.wav"), np.zeros(32000, dtype=np.float32), 16000)  # holdout
    (d / "Transkript" / "Stufe1_D07.txt").write_text(SCRIPT, encoding="utf-8")
    (d / "Skript_mit_Sollbewertung" / "Stufe1_D07.txt").write_text(HEADER.format(spots=LINE_D05) + SCRIPT,
                                                                    encoding="utf-8")
    return d


def test_asr_eval_split_defaults_to_dev_and_logs_holdout(tmp_path):
    sets = [x for o in [f"paths.data_dir={_asr_case(tmp_path)}", f"paths.cache_dir={tmp_path / 'cache'}",
                        f"paths.runs_dir={tmp_path / 'runs'}", "llms.default.type=fake"] for x in ("--set", o)]
    r = runner.invoke(cli.app, ["asr-eval", "-c", "oracle", *sets, "--tag", "dev", "--no-per-call"])
    assert r.exit_code == 0, r.output
    meta = json.loads((tmp_path / "runs/asr_eval/dev/summary.json").read_text())["meta"]
    assert meta["split"] == "dev" and meta["n_evaluated"] == 2  # D02 K1+K2, not the holdout D07
    assert not (tmp_path / "runs/holdout_log.jsonl").exists()
    r = runner.invoke(cli.app, ["asr-eval", "-c", "oracle", *sets, "--tag", "ho", "--split", "holdout",
                                "--no-per-call"])
    assert r.exit_code == 0, r.output
    assert json.loads((tmp_path / "runs/asr_eval/ho/summary.json").read_text())["meta"]["n_evaluated"] == 1
    log = [json.loads(x) for x in (tmp_path / "runs/holdout_log.jsonl").read_text().splitlines()]
    assert len(log) == 1 and log[0]["kind"] == "asr-eval ho" and log[0]["asr"]["n_calls"] == 1


# --------------------------------------------------------------------------------------------
# F3: live LLM identity
# --------------------------------------------------------------------------------------------

VLLM = {"object": "list", "data": [{"id": "callguard-llm", "root": "Qwen/Qwen3-8B-AWQ"}]}


class Models:
    def __init__(self, answer: Any):
        self.answer = answer

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if isinstance(self.answer, Exception):
            raise self.answer
        return httpx.Response(200, json=self.answer)


def _llm(tmp_path: Path, models: Models) -> OpenAICompatLLM:
    ctx = Context(AppConfig(name="t", asr={"type": "reference"}, paths=Paths(cache_dir=str(tmp_path / "cache"))))
    llm = OpenAICompatLLM(ctx, base_url="http://gpu.test/v1", model="callguard-llm")
    llm._client = llm._build_client(httpx.MockTransport(models))
    return llm


def test_resolve_served_never_uses_the_persisted_identity(tmp_path):
    old = _llm(tmp_path, Models({"object": "list", "data": [{"id": "callguard-llm", "root": "Qwen/Qwen2.5-7B"}]}))
    assert old.model_id == "Qwen/Qwen2.5-7B"  # persisted to .cache/llm_served
    loading = _llm(tmp_path, Models(httpx.ConnectError("refused")))
    assert loading.served_model() == "Qwen/Qwen2.5-7B"  # the non-strict fallback the audit found
    with pytest.raises(LLMIdentityError, match="cannot be confirmed"):
        _llm(tmp_path, Models(httpx.ConnectError("refused"))).resolve_served()
    with pytest.raises(LLMIdentityError, match="does not serve"):
        _llm(tmp_path, Models({"data": [{"id": "other"}]})).resolve_served()
    models = Models(VLLM)
    live = _llm(tmp_path, models)
    assert live.resolve_served() == "Qwen/Qwen3-8B-AWQ"
    models.answer = httpx.ConnectError("gone")
    live.served_ttl = live.down_cooldown = 0.0
    assert live.model_id == "Qwen/Qwen3-8B-AWQ"  # pinned to the live answer, not a file


def test_resolve_llm_identities_names_the_unreachable_llm(tmp_path):
    cfg = AppConfig(name="t", asr={"type": "reference"}, paths=Paths(cache_dir=str(tmp_path / "cache")),
                    llms={"default": {"type": "fake"},
                          "judge": {"type": "openai_compat", "base_url": "http://127.0.0.1:9/v1", "model": "m",
                                    "timeout": 2}})
    with pytest.raises(ex.LLMIdentityError, match="'judge'"):
        ex.resolve_llm_identities(Context(cfg))
    ok = ex.resolve_llm_identities(Context(AppConfig(name="t", asr={"type": "reference"},
                                                     llms={"default": {"type": "fake"}})))
    assert ok["default"]["type"] == "fake" and ok["default"]["model_id"]


@needs_data
def test_experiment_aborts_before_running_when_an_llm_is_down(tmp_path):
    s = spec(tmp_path, [{"name": "a", "set": ["llms.judge.type=openai_compat", "llms.judge.model=m",
                                              "llms.judge.base_url=http://127.0.0.1:9/v1", "llms.judge.timeout=2"]}])
    assert ex.variant_config(s, s.variants[0]).llms["judge"]["type"] == "openai_compat"
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS[:2]]
    with pytest.raises(ex.LLMIdentityError):
        ex.run_experiment(s, calls, runs_dir=tmp_path / "runs", n_boot=50)
    assert not (tmp_path / "runs/experiments/t/a/rows.json").exists()


@needs_data
def test_meta_records_identities_and_summary_warns_on_model_mismatch(tmp_path):
    s = spec(tmp_path, [{"name": "a"}])
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS[:4]]
    summary = ex.run_experiment(s, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=100)
    out = tmp_path / "runs/experiments/t"
    meta = json.loads((out / "a/meta.json").read_text())
    assert meta["llm_resolved"]["default"]["model_id"] and not summary["variants"]["a"]["warnings"]
    meta["llm_resolved"]["default"]["model_id"] = "some-other-model"
    (out / "a/meta.json").write_text(json.dumps(meta))
    again = ex.summarize(s, out, n_boot=100)
    assert any("not resolved live" in w for w in again["variants"]["a"]["warnings"])
    assert "## Warnings" in (out / "summary.md").read_text()


def test_role_assignment_records_model_and_flags_errors():
    from test_diarization import BANK_CALL, StubLLM, answer, dialogue

    from callguard.diarization import assign_roles
    t = dialogue(BANK_CALL)
    ok = assign_roles(t.segments, "llm", llm=lambda: StubLLM(lambda m, s: answer("SPK0", 0.9)), swap_check=False)
    assert ok["role_method"] == "llm" and ok["role_llm_model"] == "stub" and "role_error" not in ok
    bad = assign_roles(t.segments, "llm", llm=lambda: StubLLM(lambda m, s: RuntimeError("server down")))
    assert bad["role_method"] == "first_speaker_advisor" and "server down" in bad["role_error"]
    unsure = assign_roles(t.segments, "llm", llm=lambda: StubLLM(lambda m, s: answer("SPK0", 0.1)),
                          swap_check=False)
    assert "role_error" not in unsure  # a low-confidence answer is an answer, not an error: cacheable


def test_pipeline_does_not_cache_role_error_fallbacks(tmp_path):
    from callguard.pipeline import Pipeline

    pipe = Pipeline(load_config("demo-offline", [f"paths.cache_dir={tmp_path / 'cache'}",
                                                 f"paths.runs_dir={tmp_path / 'runs'}"]))

    class Diar:
        calls = 0
        error: str | None = "RuntimeError: down"

        def cache_params(self):
            return {"type": "stub"}

        def diarize(self, audio_path, transcript):
            Diar.calls += 1
            out = transcript.model_copy(deep=True)
            out.meta["diarization"] = {"role_error": Diar.error} if Diar.error else {"role_method": "llm"}
            return out

    pipe._diarizer = Diar()
    t = Transcript(call_id="x", segments=[Segment(id="S001", start=0, end=1, text="hallo")])
    pipe.diarize(None, t)
    pipe.diarize(None, t)
    assert Diar.calls == 2  # the error fallback was not cached
    Diar.error = None
    pipe.diarize(None, t)
    pipe.diarize(None, t)
    assert Diar.calls == 3  # a clean answer is cached (same key as before)


# --------------------------------------------------------------------------------------------
# F4: G-Eval steps
# --------------------------------------------------------------------------------------------


def _geval(tmp_path: Path, llm: Any, monkeypatch) -> tuple[GEvalCheck, list[Family]]:
    ctx = Context(AppConfig(name="t", asr={"type": "reference"}, llms={"default": {"type": "fake"}},
                            paths=Paths(cache_dir=str(tmp_path / "cache"))))
    monkeypatch.setattr(ctx, "llm", lambda name="default": llm)
    fam = Family(id="trade", label="Insiderhandel", policy="Kauf vor der Meldung mit Insiderwissen.")
    return GEvalCheck(ctx, locate_evidence=False), [fam]


def test_geval_steps_fallback_is_degraded_and_not_cached(tmp_path, monkeypatch):
    from callguard.llm.fake import FakeLLM

    class NoSteps(FakeLLM):
        def chat(self, messages, **kw):
            if "numbered evaluation steps" in messages[-1]["content"]:
                raise RuntimeError("server hiccup")
            return super().chat(messages, **kw)

    check, fams = _geval(tmp_path, NoSteps(None), monkeypatch)
    t = Transcript(call_id="x", segments=[Segment(id="S001", start=0, end=1, text="vor der Meldung kaufen")])
    res = check.run(t, fams)
    assert res.family_scores["trade"].detail["steps_source"] == "default"
    assert "trade:steps" in res.meta["errors"] and res.meta["cacheable"] is False
    assert ev.failed_checks(CallResult(call_id="x", transcript=t, checks={"geval": res},
                                       decision=NO_DECISION)) == ["geval"]
    good, _ = _geval(tmp_path / "ok", FakeLLM(None), monkeypatch)
    ok = good.run(t, fams)
    assert ok.family_scores["trade"].detail["steps_source"] == "auto" and not ok.meta.get("errors")


def test_geval_cache_key_unchanged_until_steps_prompt_moves(tmp_path, monkeypatch):
    from callguard.llm.fake import FakeLLM

    check, fams = _geval(tmp_path, FakeLLM(None), monkeypatch)
    assert prompts.STEPS_PROMPT_VERSION == BASE_STEPS_PROMPT_VERSION
    assert check.cache_key(fams) == LLMCheck.cache_key(check, fams)  # existing caches keep their keys
    monkeypatch.setattr(prompts, "STEPS_PROMPT_VERSION", "geval-steps-2")
    key = check.cache_key(fams)
    assert key["steps_prompt_version"] == "geval-steps-2" and key != LLMCheck.cache_key(check, fams)


# --------------------------------------------------------------------------------------------
# F5: re-fusion provenance, back-fill stamps
# --------------------------------------------------------------------------------------------


@needs_data
def test_refusion_is_tied_to_its_source_and_backfill_is_stamped(tmp_path):
    s = spec(tmp_path, [{"name": "all"}, {"name": "t03", "refuse_from": "all", "set": ["fusion.threshold=0.3"]}])
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS[:6]]
    summary = ex.run_experiment(s, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=100)
    out = tmp_path / "runs/experiments/t"
    src = summary["variants"]["t03"]["meta"]["source"]
    assert src["results_hash"] == ex.results_hash(out / "all") and src["git"] is not None
    assert not summary["variants"]["t03"]["warnings"]
    with (out / "all/results.jsonl").open("a") as f:  # the source is re-run after the re-fusion
        f.write("\n")
    again = ex.summarize(s, out, n_boot=100)
    assert any("changed after this re-fusion" in w for w in again["variants"]["t03"]["warnings"])
    # an old run without FAR floor / fold flags is back-filled and stamped
    data = json.loads((out / "all/rows.json").read_text())
    data.pop("far_floor")
    (out / "all/rows.json").write_text(json.dumps(data))
    ex.summarize(s, out, n_boot=100)
    data = json.loads((out / "all/rows.json").read_text())
    stamp = data["backfill"]["far_floor"]
    assert data["far_floor"] is not None and stamp["config_hash"] and stamp["config_matches_run"] is True
    assert "far_floor @ " in (out / "summary.md").read_text()


# --------------------------------------------------------------------------------------------
# F6: twin-group bootstrap, weight-aware DEGRADED
# --------------------------------------------------------------------------------------------


def test_asr_bootstrap_resamples_twin_groups_together():
    from callguard import eval_asr as ea
    rows = [{"dialogue_id": d} for d in ("Stufe2_C01", "Stufe2_C02", "Stufe1_D01", "Stufe1_D02")]

    def twins_together(rs):
        n1 = sum(r["dialogue_id"] == "Stufe2_C01" for r in rs)
        n2 = sum(r["dialogue_id"] == "Stufe2_C02" for r in rs)
        return 1.0 if n1 == n2 else 0.0

    assert ea.bootstrap_ci(rows, twins_together, n=300) == (1.0, 1.0)


def test_failed_checks_ignore_zero_weight_checks():
    t = Transcript(call_id="x", segments=[])
    bad = CheckResult(check="judge", type="llm_judge", meta={"error": "down"})
    res = CallResult(call_id="x", transcript=t, checks={"judge": bad, "kw": CheckResult(check="kw", type="keywords")},
                     decision=NO_DECISION)
    assert ev.failed_checks(res) == ["judge"]
    assert ev.failed_checks(res, {"judge": 0.0, "kw": 1.0}) == []
    assert ev.failed_checks(res, {"judge": 0.5}) == ["judge"]


@needs_data
def test_zero_weight_failing_check_does_not_degrade_the_variant(tmp_path):
    s = spec(tmp_path, [{"name": "w0", "checks": ["keywords"],
                         "add_checks": [{"name": "judge2", "type": "llm_judge", "llm": "missing", "weight": 0}]}])
    calls = [c for c in load_calls(DATA) if c.call_id in CALLS[:4]]
    v = ex.run_experiment(s, calls, jobs=2, runs_dir=tmp_path / "runs", n_boot=100)["variants"]["w0"]
    assert not v["degraded"] and v["check_failures"]["calls"] == 0
    assert v["meta"]["check_weights"]["judge2"] == 0.0
