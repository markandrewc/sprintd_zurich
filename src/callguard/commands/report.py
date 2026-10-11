"""``callguard report``: markdown + PNG charts from runs/experiments/*/summary.json -> research/report/.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

from pathlib import Path
from typing import Annotated, Optional

import typer


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("report")
    def report_cmd(experiments: Annotated[Optional[str], typer.Option(
                       "--experiments", help="Comma-separated experiment names (default: all).")] = None,
                   out: Annotated[Optional[Path], typer.Option(
                       "--out", help="Output dir (default research/report).")] = None,
                   runs_dir: Annotated[Optional[Path], typer.Option(
                       "--runs-dir", help="Where runs/experiments lives (default runs/).")] = None) -> None:
        """Charts (F1/FAR/miss with CIs, cost vs F1, clean vs noisy, levels, thresholds) + report.md."""
        from callguard import report

        names = [n.strip() for n in experiments.split(",") if n.strip()] if experiments else None
        missing = [n for n in names or [] if not (report.experiments_root(runs_dir) / n / "summary.json").exists()]
        if missing:
            cli.console.print(f"[yellow]no summary.json for: {', '.join(missing)}[/yellow]")
        p = report.build_report(names, out, runs_dir)
        cli.console.print(f"Report: {cli._rel(p)}")
