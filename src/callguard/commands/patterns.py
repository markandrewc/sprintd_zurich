"""``callguard patterns``: advisors / customers / companies across calls, with flags.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("patterns")
    def patterns_cmd(results: Annotated[Optional[Path], typer.Option(
                         "--results", help="An experiment variant dir or its results.jsonl instead of runs/<profile>/.")] = None,
                     all_recordings: Annotated[bool, typer.Option(
                         "--all-recordings", help="Count clean and noisy recordings of a case dialogue separately.")] = False,
                     min_calls: Annotated[int, typer.Option("--min-calls", help="Calls before an advisor can be flagged.")] = 3,
                     out: Annotated[Optional[Path], typer.Option("--out", help="Write a markdown report here.")] = None,
                     as_json: Annotated[bool, typer.Option("--json", help="Print the analysis as JSON.")] = False,
                     config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Who stands out across calls: flag rate per advisor (Wilson bound vs population), companies across customers."""
        from callguard import patterns as pt
        from callguard.context import Context
        from callguard.eval import load_results

        cli._setup_logging(verbose)
        cfg = cli.load_config(config, set_ or [])
        rs = pt.load_variant_results(results) if results else load_results(Context(cfg).runs_dir)
        if not rs:
            cli.console.print("[yellow]No results found.[/yellow]")
            raise typer.Exit(1)
        if not all_recordings:
            rs = pt.one_per_dialogue(rs)
        a = pt.analyze(rs, min_calls=min_calls)
        if as_json:
            cli.console.print_json(json.dumps({k: v for k, v in a.items() if k != "calls"}, ensure_ascii=False))
            return
        cli.console.print(f"{a['n_calls']} calls, {a['flagged']} flagged ({a['population_flag_rate']:.0%}); "
                          f"advisor unknown in {a['unidentified']['advisor']}, customer unknown in "
                          f"{a['unidentified']['customer']}.")
        for title, rows in (("Advisors", a["advisors"]), ("Companies", a["companies"])):
            t = Table(title=title)
            for col in ("name", "calls", "alarms", "reviews", "flag rate (95% lower)", "mean score", "families"):
                t.add_column(col)
            for r in rows[:15]:
                t.add_row(r["name"], str(r["calls"]), str(r["alarms"]), str(r["reviews"]),
                          f"{r['flag_rate']:.0%} ({r['flag_rate_lower']:.0%})", f"{r['mean_score']:.2f}",
                          ", ".join(f"{k} {v}" for k, v in r["families"].items()) or "-")
            cli.console.print(t)
        if a["flags"]:
            for f in a["flags"]:
                cli.console.print(f"[bold red]{f['kind']}[/bold red] {f['reason']} ({', '.join(f['calls'])})")
        else:
            cli.console.print("[green]No cross-call flags.[/green]")
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(pt.render_markdown(a))
            cli.console.print(f"[dim]-> {cli._rel(out)}[/dim]")
