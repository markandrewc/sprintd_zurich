"""``callguard fit-fusion`` and ``callguard fusion-cv``: fitted fusions from stored experiment results.

    callguard fit-fusion --kind calibrated --experiment fusion --variant base
        -> runs/fusion/fusion-base-calibrated.json, fitted on the DEV dialogues of that variant's
           results.jsonl only (holdout and unassigned calls are dropped; a holdout experiment is refused).
           Use it with --set fusion.type=calibrated --set fusion.model=runs/fusion/fusion-base-calibrated.json
    callguard fusion-cv --kind calibrated --experiment fusion --variant base
        -> nested CV over the dev folds (fusion.fit.nested_cv), written like an experiment variant to
           runs/experiments/fusion/base__cv_calibrated/ (rows.json with "fixed" and "cv" rows, metrics,
           meta, results.jsonl) plus compare_<baseline>.md/.json: paired bootstrap + McNemar + flips of the
           fitted fusion's CV rows against the source variant's CV rows (weighted fusion, threshold chosen
           on the other folds), i.e. both numbers are out-of-fold.

Kinds: calibrated (A5), learned (logistic regression), thresholds (N2 per-family thresholds for the
weighted fusion). Logic in :mod:`callguard.fusion.fit`; this module only loads, writes and prints.

No ``from __future__ import annotations``: typer resolves the option annotations at runtime.
"""

import json
import time
from pathlib import Path
from typing import Annotated, Any, Optional

import typer


class SourceError(ValueError):
    pass


def load_source(experiment: str, variant: str, runs_dir: Optional[Path] = None, spec: Any = None) -> dict[str, Any]:
    """Everything a fit needs from a finished experiment variant, restricted to the dev folds. ``spec``: the
    experiment spec (default: the copy in the experiment dir, else experiments/<experiment>.yaml)."""
    import yaml

    from callguard import experiments as ex
    from callguard import splits as sp
    from callguard.config import ROOT
    from callguard.context import Context
    from callguard.data import dialogue_of, load_calls
    from callguard.fusion import fit as F

    exp_dir = (runs_dir or ROOT / "runs") / "experiments" / experiment
    vdir = exp_dir / variant
    if not (vdir / "results.jsonl").exists():
        raise SourceError(f"{vdir}/results.jsonl not found: run `callguard experiment {experiment} "
                          f"--variants {variant}` first")
    spec_path = exp_dir / "spec.yaml"
    if spec is not None:
        pass
    elif spec_path.exists():
        spec = ex.parse_spec(yaml.safe_load(spec_path.read_text()) or {}, name=experiment, path=spec_path)
    else:
        spec = ex.load_spec(experiment)
    try:
        cfg = ex.variant_config(spec, spec.variant(variant))
    except ex.SpecError as e:
        raise SourceError(str(e)) from e
    meta = json.loads((vdir / "meta.json").read_text()) if (vdir / "meta.json").exists() else {}
    if meta.get("split") == sp.HOLDOUT:
        raise SourceError(f"{experiment}/{variant} was run on the holdout: fitted fusions never train on it")
    splits = sp.load_splits(required=True)
    fold_of = splits.dev_fold_of()
    holdout = set(splits.holdout_dialogues())
    results = ex.load_results(vdir)
    dev = [r for r in results if dialogue_of(r.call_id) in fold_of]
    dropped_holdout = sorted({r.call_id for r in results if dialogue_of(r.call_id) in holdout})
    dropped_other = sorted({r.call_id for r in results
                            if dialogue_of(r.call_id) not in fold_of and dialogue_of(r.call_id) not in holdout})
    rows = ex._read_rows(vdir)
    calls = load_calls(cfg.paths.resolve("data_dir"))
    return {"exp_dir": exp_dir, "vdir": vdir, "spec": spec, "cfg": cfg, "meta": meta, "splits": splits,
            "fold_of": fold_of, "results": dev, "rows": rows, "calls": calls, "ctx": Context(cfg),
            "weights": F.check_weights(cfg), "base": F.base_params(cfg),
            "dropped_holdout": dropped_holdout, "dropped_other": dropped_other}


def _opts(kind: str, alpha: float, review_target: float, l2: float, max_fpr: float, labels: int = 3
          ) -> dict[str, Any]:
    if kind == "calibrated":
        return {"alpha": alpha, "review_target": review_target, "labels": labels}
    if kind == "learned":
        return {"l2": l2, "review_target": review_target}
    return {"max_fpr": max_fpr}


def fit_from_experiment(kind: str, experiment: str, variant: str, *, name: Optional[str] = None,
                        runs_dir: Optional[Path] = None, spec: Any = None,
                        **opts: Any) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    from callguard import splits as sp
    from callguard.fusion import fit as F
    from callguard.fusion.weighted import WeightedFusion

    src = load_source(experiment, variant, runs_dir, spec)
    if not src["results"]:
        raise SourceError(f"{experiment}/{variant} has no results on dev dialogues")
    base = dict(src["base"])
    if kind == "thresholds":
        base.pop("family_thresholds", None)
    fams = src["ctx"].families()
    wf = WeightedFusion(src["ctx"], **{k: v for k, v in base.items() if k != "family_thresholds"})
    feats = [F.features_of(wf, r, fams, src["weights"]) for r in src["results"]]
    truth = {c.call_id: c for c in src["calls"]}
    checks = list(dict.fromkeys(n for r in src["results"] for n in r.checks))
    model = F.fit_model(kind, feats, truth, src["fold_of"], base=base, checks=checks, weights=src["weights"], **opts)
    model["provenance"] = {"experiment": experiment, "variant": variant, "config": src["cfg"].name,
                           "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "git": sp.git_info(),
                           "splits": str(src["splits"].path), "fit_on": "dev folds only",
                           "dropped_holdout_calls": src["dropped_holdout"], "dropped_unassigned": src["dropped_other"]}
    root = runs_dir or src["cfg"].paths.resolve("runs_dir")
    path = F.save_model(model, root / "fusion" / f"{name or f'{experiment}-{variant}-{kind}'}.json")
    return path, model, src


def fusion_cv_from_experiment(kind: str, experiment: str, variant: str, *, compare_to: Optional[str] = None,
                              name: Optional[str] = None, runs_dir: Optional[Path] = None,
                              threshold: Optional[float] = None, n_boot: int = 2000, seed: int = 13,
                              spec: Any = None, **opts: Any) -> dict[str, Any]:
    from callguard import eval as ev
    from callguard import experiments as ex
    from callguard import splits as sp
    from callguard import stats
    from callguard.fusion import fit as F

    src = load_source(experiment, variant, runs_dir, spec)
    base = dict(src["base"])
    if kind == "thresholds":
        base.pop("family_thresholds", None)
    errors = [r for r in (src["rows"].get("fixed") or []) if r.get("error")]
    passage = {k: base[k] for k in ("max_passages", "merge_gap", "max_passage_seconds") if k in base}
    out = F.nested_cv(kind, src["results"], src["calls"], src["fold_of"], src["ctx"], base=base,
                      weights=src["weights"], threshold=threshold, thresholds=src["spec"].thresholds,
                      error_rows=errors, passage_params=passage, **opts)
    vname = name or f"{variant}__cv_{kind}"
    vdir = src["exp_dir"] / vname
    vdir.mkdir(parents=True, exist_ok=True)
    with (vdir / "results.jsonl").open("w") as f:
        for r in out["results_cv"]:
            f.write(json.dumps(ex.strip_words(r), ensure_ascii=False) + "\n")
    (vdir / "rows.json").write_text(json.dumps(
        {"fixed": out["fixed"], "cv": out["cv"], "cv_folds": out["cv_folds"], "sweep": [], "suggestion": None,
         "fits": out["fits"]}, ensure_ascii=False, indent=1, default=str))
    (vdir / "metrics.json").write_text(json.dumps(
        {"fixed": ev.metrics(out["fixed"]), "cv": ev.metrics(out["cv"])}, ensure_ascii=False, indent=1, default=str))
    m = src["meta"]
    meta = {"variant": vname, "experiment": src["spec"].name, "split": "dev", "refuse_from": variant,
            "description": f"nested CV of the {kind} fusion on {variant}'s stored check results",
            "fusion": kind, "threshold": out["threshold_fixed"], "oracle": bool(m.get("oracle")),
            "profile": m.get("profile"), "checks": m.get("checks"), "config_name": m.get("config_name"),
            "nested_cv": {"kind": kind, "base": base, **opts, "n_fits": len(out["fits"]),
                          "threshold": "chosen per outer fold on inner out-of-fold predictions"},
            "git": sp.git_info(), "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "n_calls": len(out["fixed"]), "calls": [r["call_id"] for r in out["fixed"]],
            "dropped_holdout_calls": src["dropped_holdout"]}
    (vdir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1, default=str))

    base_name = compare_to or variant
    base_rows = ex._read_rows(src["exp_dir"] / base_name)
    if not base_rows:
        raise SourceError(f"no rows.json for comparison variant {base_name!r}")
    dev_ids = {r["call_id"] for r in out["cv"]}
    comp: dict[str, Any] = {"a": base_name, "b": vname}
    for key in ("cv", "fixed"):
        a_rows = [r for r in base_rows.get(key) or [] if r["call_id"] in dev_ids]
        if a_rows:
            comp[key] = stats.compare(a_rows, out[key], n_boot, seed)
    V = {base_name: ex.variant_summary(base_name, src["exp_dir"] / base_name, n_boot, seed),
         vname: ex.variant_summary(vname, vdir, n_boot, seed)}
    md = [f"# Nested CV: `{vname}` vs `{base_name}`", "",
          f"Experiment `{src['spec'].name}`, fitted fusion **{kind}** on the stored check results of `{variant}`. "
          f"Per dev fold: fit on the other dev folds, threshold chosen on out-of-fold predictions inside them, "
          f"predict the fold. The holdout is never used. Baseline CV rows: `{base_name}` with its threshold "
          f"chosen on the other folds. {len(out['fits'])} fits.", "",
          "## Out-of-fold (CV) - primary", "", *ex._metric_table(V, "cv"), "",
          "## Fixed threshold", "", *ex._metric_table(V, "fixed"), "",
          "## Folds", "", *ex._table(["fold", "threshold", "test dialogues", "model"],
                                     [[f["fold"], f["threshold"], " ".join(f["dialogues"]),
                                       json.dumps(f["model_summary"], ensure_ascii=False)[:300]]
                                      for f in out["cv_folds"]]), "",
          *ex._render_comparison(comp, V)]
    (vdir / f"compare_{base_name}.md").write_text("\n".join(md) + "\n")
    (vdir / f"compare_{base_name}.json").write_text(json.dumps(
        {"comparison": comp, "variants": V}, ensure_ascii=False, indent=1, default=str))
    return {"dir": vdir, "comparison": comp, "variants": V, "out": out}


def register(app: typer.Typer) -> None:
    from callguard import cli

    KindOpt = Annotated[str, typer.Option("--kind", help="calibrated | learned | thresholds")]
    ExpOpt = Annotated[str, typer.Option("--experiment", "-e", help="Experiment name (runs/experiments/<name>/).")]
    VarOpt = Annotated[str, typer.Option("--variant", help="Variant whose results.jsonl is the training data.")]
    AlphaOpt = Annotated[float, typer.Option("--alpha", help="calibrated: conformal miscoverage (sets at 1-alpha).")]
    RTOpt = Annotated[float, typer.Option("--review-target", help="Target for review-labelled calls (0..1).")]
    L2Opt = Annotated[float, typer.Option("--l2", help="learned: L2 penalty on standardized coefficients.")]
    FprOpt = Annotated[float, typer.Option("--max-fpr", help="thresholds: family-level false-positive rate.")]
    RunsOpt = Annotated[Optional[Path], typer.Option("--runs-dir", help="Default: runs/.")]
    NameOpt = Annotated[Optional[str], typer.Option("--name", help="Output name (default derived).")]
    LabelsOpt = Annotated[int, typer.Option(
        "--labels", help="calibrated: conformal sets over 3 labels or 2 (alarm / no_alert).")]

    def _check_kind(kind: str) -> None:
        from callguard.fusion.fit import KINDS
        if kind not in KINDS:
            raise typer.BadParameter(f"expected one of {', '.join(KINDS)}", param_hint="--kind")

    @app.command("fit-fusion")
    def fit_fusion_cmd(kind: KindOpt, experiment: ExpOpt, variant: VarOpt, name: NameOpt = None,
                       alpha: AlphaOpt = 0.1, review_target: RTOpt = 0.5, l2: L2Opt = 1.0, max_fpr: FprOpt = 0.05,
                       labels: LabelsOpt = 3, runs_dir: RunsOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Fit a calibrated / learned fusion or per-family thresholds on DEV results of an experiment variant."""
        from callguard import splits as sp
        from callguard.fusion import fit as F

        cli._setup_logging(verbose)
        _check_kind(kind)
        try:
            path, model, src = fit_from_experiment(kind, experiment, variant, name=name, runs_dir=runs_dir,
                                                   **_opts(kind, alpha, review_target, l2, max_fpr, labels))
        except (SourceError, sp.SplitsMissing, FileNotFoundError, ValueError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        cli.console.print(f"[green]Wrote {cli._rel(path)}[/green]: {kind}, {model['n_calls']} dev calls / "
                          f"{len(model['train_dialogues'])} dialogues"
                          + (f"; ignored {len(src['dropped_holdout'])} holdout calls" if src["dropped_holdout"] else ""))
        cli.console.print(json.dumps(F.summarize_model(model), ensure_ascii=False))
        rel = cli._rel(path)
        if kind == "thresholds":
            cli.console.print(f"Use: --set fusion.family_thresholds={rel}   (or paste the block into the profile)")
        else:
            cli.console.print(f"Use: --set fusion.type={kind} --set fusion.model={rel} --set fusion.threshold=0.5")
        cli.console.print("[dim]Numbers on dev with this file are in-sample; evaluate with `callguard fusion-cv`.[/dim]")

    @app.command("fusion-cv")
    def fusion_cv_cmd(kind: KindOpt, experiment: ExpOpt, variant: VarOpt, name: NameOpt = None,
                      compare_to: Annotated[Optional[str], typer.Option(
                          "--compare-to", help="Variant whose CV rows are the baseline (default: --variant).")] = None,
                      threshold: Annotated[Optional[float], typer.Option(
                          "--threshold", help="Fixed-threshold rows (default 0.5; thresholds kind: config).")] = None,
                      alpha: AlphaOpt = 0.1, review_target: RTOpt = 0.5, l2: L2Opt = 1.0, max_fpr: FprOpt = 0.05,
                      labels: LabelsOpt = 3, n_boot: Annotated[int, typer.Option("--n-boot")] = 2000,
                      seed: Annotated[int, typer.Option("--seed")] = 13,
                      runs_dir: RunsOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Honest numbers for a fitted fusion: nested CV over the dev folds, compared to the weighted CV rows."""
        from callguard import experiments as ex
        from callguard import splits as sp

        cli._setup_logging(verbose)
        _check_kind(kind)
        try:
            res = fusion_cv_from_experiment(kind, experiment, variant, compare_to=compare_to, name=name,
                                            runs_dir=runs_dir, threshold=threshold, n_boot=n_boot, seed=seed,
                                            **_opts(kind, alpha, review_target, l2, max_fpr, labels))
        except (SourceError, sp.SplitsMissing, FileNotFoundError, ValueError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        comp = res["comparison"]
        for key in ("cv", "fixed"):
            if key not in comp:
                continue
            d = comp[key]["paired"]["flag_f1"]
            verdict = "[bold]real[/bold]" if d.get("real") else "no detectable difference"
            cli.console.print(f"{key}: {comp['b']} vs {comp['a']}: flag F1 {ex._f(d.get('a'))} -> {ex._f(d.get('b'))}, "
                              f"diff {ex._signed(d.get('diff'))} [{ex._signed(d.get('lo'))}, {ex._signed(d.get('hi'))}]"
                              f" -> {verdict}; McNemar p={comp[key]['mcnemar_flag']['p']}; "
                              f"{len(comp[key]['flips'])} flips")
        cli.console.print(f"[dim]{cli._rel(res['dir'])}/compare_{comp['a']}.md[/dim]")
