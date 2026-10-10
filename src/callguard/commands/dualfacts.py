"""``callguard dualfacts eval``: the pre-registered dual-reader facts evaluation
(research/findings/dual_facts_prereg.md; logic in :mod:`callguard.dual_eval`). Pure re-fusion of the stored answers
of both readers (Qwen ``facts``, Kev ``facts_kev``); no model runs.

``--set dev``     dev folds only (never the holdout): default vs champion v3, fixed-threshold + CV rows, paired
                  deltas, the 12-setting grid (Kev band x combination) for the officer UI, reader agreement, sanity.
                  -> research/evidence/dual_facts_dev.md/.json + dual_facts_grid.json
``--set test50``  the external set, ONE look, only with ``--test50-look``: default vs champion v3 at the fixed
                  threshold. -> research/evidence/dual_facts_test50.md/.json (log the look in test50_prereg.md).

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from pathlib import Path
from typing import Annotated, Any

import typer

EVIDENCE = Path("research/evidence")


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")


def register(app: typer.Typer) -> None:
    from callguard import cli

    grp = typer.Typer(help="Dual-reader facts (Qwen + Kev answer every fact): pre-registered evaluation.",
                      no_args_is_help=True)
    app.add_typer(grp, name="dualfacts")

    @grp.command("eval")
    def eval_cmd(set_: Annotated[str, typer.Option("--set", help="dev (dev folds only) or test50 (one look).")] = "dev",
                 n_boot: Annotated[int, typer.Option("--n-boot", help="Bootstrap resamples (twin groups).")] = 2000,
                 seed: Annotated[int, typer.Option("--seed", help="Bootstrap seed.")] = 13,
                 threshold: Annotated[float, typer.Option("--threshold", help="Fixed fusion threshold.")] = 0.55,
                 test50_look: Annotated[bool, typer.Option(
                     "--test50-look", help="Required for --set test50: this IS the one pre-registered look.")] = False,
                 relook: Annotated[bool, typer.Option(
                     "--relook", help="Overwrite an existing test50 result (a new look: log it with a reason).")] = False,
                 out: Annotated[Path, typer.Option("--out", help="Evidence directory.")] = EVIDENCE,
                 verbose: cli.VerboseOpt = False) -> None:
        """Default (Einigkeit, Kev band 0.3-0.7) vs champion v3 (Qwen alone) on stored answers."""
        from callguard import dual_eval as de

        cli._setup_logging(verbose)
        if set_ not in de.SETS:
            raise typer.BadParameter(f"must be one of {tuple(de.SETS)}", param_hint="--set")
        if set_ == "test50":
            if not test50_look:
                cli.console.print("[red]test50 is the external held-out set: evaluated once, only with "
                                  "--test50-look (research/findings/test50_prereg.md).[/red]")
                raise typer.Exit(2)
            if (out / "dual_facts_test50.json").exists() and not relook:
                cli.console.print(f"[red]{out / 'dual_facts_test50.json'} exists: the one look is done. --relook "
                                  "only with a logged reason.[/red]")
                raise typer.Exit(2)
        es = de.load_set(set_, threshold=threshold)
        if not es.results:
            cli.console.print(f"[red]no stored results in {es.runs_dir}[/red]")
            raise typer.Exit(1)
        if es.missing:
            cli.console.print(f"[yellow]{len(es.missing)} calls without a stored result: {es.missing}[/yellow]")
        if set_ == "dev":
            rep = de.evaluate_dev(es, n_boot, seed)
            md = de.dev_markdown(rep)
            _write(out / "dual_facts_dev.md", md)
            _write(out / "dual_facts_dev.json", rep)
            _write(out / "dual_facts_grid.json", {
                "meta": rep["meta"], "note": "DEV ONLY (dev folds, holdout excluded); nothing is selected from it",
                "default": rep["policies"]["default"], "champion_v3": rep["policies"]["champion_v3"],
                "ui_text": rep["ui_text"], "entries": rep["grid"]})
            written = ["dual_facts_dev.md", "dual_facts_dev.json", "dual_facts_grid.json"]
        else:
            rep = de.evaluate_test50(es, n_boot, seed)
            md = de.test50_markdown(rep)
            _write(out / "dual_facts_test50.md", md)
            _write(out / "dual_facts_test50.json", rep)
            written = ["dual_facts_test50.md", "dual_facts_test50.json"]
        cli.console.print(md, markup=False, highlight=False)
        cli.console.print("wrote " + ", ".join(str(out / w) for w in written))
