"""``callguard experiment experiments/<name>.yaml``: run a variant matrix, write summary.json/.md.

Logic in :mod:`callguard.experiments`. No ``from __future__ import annotations``: typer must be able to
resolve the option annotations, which reference ``cli`` inside ``register``.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("experiment")
    def experiment_cmd(
            spec: Annotated[Path, typer.Argument(help="Spec file, e.g. experiments/smoke.yaml (or just 'smoke').")],
            dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be computed; run nothing.")] = False,
            split: Annotated[Optional[str], typer.Option(
                "--split", help="dev (default) | holdout | all. holdout and all include holdout dialogues: "
                                "every variant run is logged to runs/holdout_log.jsonl, and they must be "
                                "given here explicitly even if the spec names them.")] = None,
            variants: Annotated[Optional[str], typer.Option(
                "--variants", help="Comma-separated variant names (default: all).")] = None,
            jobs: Annotated[int, typer.Option("--jobs", "-j", help="Calls processed in parallel.")] = 6,
            calls: cli.CallsOpt = None, level: cli.LevelOpt = None, clean_only: cli.CleanOpt = False,
            limit: cli.LimitOpt = None,
            rescore: Annotated[bool, typer.Option(
                "--rescore", help="Only rebuild summary.json/.md from stored rows (no ASR, no checks).")] = False,
            n_boot: Annotated[int, typer.Option("--n-boot", help="Bootstrap resamples (>= 2000).")] = 2000,
            seed: Annotated[int, typer.Option("--seed", help="Bootstrap seed.")] = 13,
            no_cache: cli.NoCacheOpt = False, verbose: cli.VerboseOpt = False) -> None:
        """Run every variant of an experiment spec on the same calls; paired stats vs the baseline."""
        from callguard import experiments as ex
        from callguard import splits as sp
        from callguard.data import load_calls

        cli._setup_logging(verbose)
        try:
            s = ex.load_spec(spec)
        except (FileNotFoundError, ex.SpecError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        if split:
            if split not in sp.SPLIT_CHOICES:
                raise typer.BadParameter(f"expected one of {', '.join(sp.SPLIT_CHOICES)}", param_hint="--split")
            s.split = split
        elif s.split not in ("dev", sp.EXTERNAL) and not (rescore or dry_run):
            cli.console.print(f"[red]{s.name}: the spec asks for split {s.split!r}, which includes holdout "
                              f"dialogues and is logged as a holdout look. Pass --split {s.split} explicitly "
                              f"(or --split dev).[/red]")
            raise typer.Exit(2)
        names = [n.strip() for n in variants.split(",") if n.strip()] if variants else None
        try:
            for n in names or []:
                s.variant(n)
            base_cfg = ex.variant_config(s, s.variants[0])
        except ex.SpecError as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        runs_dir = base_cfg.paths.resolve("runs_dir")
        out = ex.experiment_dir(s, runs_dir)
        if rescore:
            summary = ex.summarize(s, out, n_boot=n_boot, seed=seed)
            _print_summary(cli, summary)
            cli.console.print(f"[dim]{cli._rel(out / 'summary.md')}[/dim]")
            return

        all_calls = load_calls(base_cfg.paths.resolve("data_dir"))
        try:
            selected = ex.select_calls(all_calls, s.split, sp.load_splits(required=False),
                                       [c.strip() for c in calls.split(",")] if calls else None,
                                       level, clean_only, limit)
        except sp.SplitsMissing as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        if not selected:
            cli.console.print("[red]No calls selected.[/red]")
            raise typer.Exit(1)
        if s.split in (sp.HOLDOUT, "all"):
            cli.console.print(f"[bold yellow]{s.split.upper()} experiment (includes holdout dialogues): every "
                              f"variant is logged as a look (earlier looks: {sp.holdout_looks(base_cfg)})"
                              f"{'; CV fits thresholds on dev folds only' if s.split == 'all' else ''}."
                              f"[/bold yellow]")

        if dry_run:
            plan = ex.dry_run(s, selected, names, runs_dir)
            t = Table(title=f"experiment {s.name}: {len(selected)} calls, split {s.split} (dry run)")
            for col in ("variant", "profile", "set", "checks", "thr", "oracle", "cache / to compute", "done"):
                t.add_column(col, overflow="fold")
            for p in plan:
                t.add_row(p["variant"], p["profile"] + (f" <- {p['refuse_from']}" if p["refuse_from"] else ""),
                          " ".join(p["set"]) or "-", ", ".join(p["checks"]), cli._num(p["threshold"]),
                          "ORACLE" if p["oracle"] else "", str(p["cache"]), "yes" if p["done_before"] else "")
            cli.console.print(t)
            return

        with cli._progress() as prog:
            tasks: dict[str, int] = {}

            def on_call(variant: str, i: int, n: int, call_id: str, row: dict) -> None:
                if variant not in tasks:
                    tasks[variant] = prog.add_task(variant, total=n)
                prog.update(tasks[variant], completed=i, description=f"{variant}: {call_id} -> {row['predicted']}")

            try:
                summary = ex.run_experiment(s, selected, variants=names, jobs=jobs, use_cache=not no_cache,
                                            runs_dir=runs_dir, progress=on_call, n_boot=n_boot, seed=seed)
            except (ex.SpecError, ex.LLMIdentityError) as e:
                cli.console.print(f"[red]{e}[/red]")
                raise typer.Exit(2) from e
        _print_summary(cli, summary)
        cli.console.print(f"[dim]{cli._rel(out / 'summary.md')} · {cli._rel(out / 'summary.json')}[/dim]")


def _print_summary(cli, summary: dict) -> None:
    t = Table(title=f"experiment {summary['experiment']} (split {summary['split']}, baseline {summary['compare_to']})")
    for col in ("variant", "n", "flag AUC [CI]", "FAR20 F1/R/FAR", "CV flag F1 [CI]", "CV FAR", "CV miss",
                "fixed flag F1", "fixed FAR", "review rec.", "acc", "s/call", "LLM/call", "tags"):
        t.add_column(col, justify="left" if col in ("variant", "tags") else "right")
    from callguard import experiments as ex
    for name, v in summary["variants"].items():
        cv, fx = v.get("cv") or {}, v["fixed"]
        far20 = v.get("cv_far") or {}
        t.add_row(name, str(v["n_calls"]), ex._auc_cell(v, "flag"),
                  f"{cli._num(far20.get('flag_f1'))}/{cli._pct(far20.get('flag_recall'))}/"
                  f"{cli._pct(far20.get('false_alarm_rate'))}" if far20 else "-",
                  ex._ci(cv, "flag_f1") if cv else "-",
                  cli._pct(cv.get("false_alarm_rate")), cli._pct(cv.get("miss_rate")), ex._ci(fx, "flag_f1"),
                  cli._pct(fx["false_alarm_rate"]), cli._pct(fx["review_recall"]), cli._pct(fx["accuracy"]),
                  cli._num(v["cost"].get("wall_s_per_call"), 1), cli._num(v["cost"].get("llm_calls_per_call"), 1),
                  ex._tags(v).replace("*", ""))
    cli.console.print(t)
    for c in summary.get("comparisons") or []:
        block = c.get("cv") or c["fixed"]
        d = block["paired"]["flag_f1"]
        verdict = "[bold]real[/bold]" if d.get("real") else "no detectable difference"
        pa = ((c.get("fixed") or {}).get("auc") or {}).get("flag") or {}
        if pa.get("diff") is not None:
            cli.console.print(f"{c['b']} vs {c['a']}: flag AUC diff {ex._signed(pa['diff'])} "
                              f"[{ex._signed(pa.get('lo'))}, {ex._signed(pa.get('hi'))}]"
                              f"{' (real)' if pa.get('real') else ''}")
        cli.console.print(f"{c['b']} vs {c['a']}: flag F1 diff {ex._signed(d.get('diff'))} "
                          f"[{ex._signed(d.get('lo'))}, {ex._signed(d.get('hi'))}] -> {verdict}; "
                          f"McNemar p={block['mcnemar_flag']['p']}; {len(block['flips'])} flips")
