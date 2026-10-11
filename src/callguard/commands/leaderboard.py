"""``callguard leaderboard``: every experiment variant ranked by FAR-cap compliance, then CV@FAR20
recall -> research/leaderboard.md.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

from pathlib import Path
from typing import Annotated, Optional

import typer


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("leaderboard")
    def leaderboard_cmd(out: Annotated[Optional[Path], typer.Option(
                            "--out", help="Markdown file (default research/leaderboard.md).")] = None,
                        runs_dir: Annotated[Optional[Path], typer.Option(
                            "--runs-dir", help="Where runs/experiments lives (default runs/).")] = None,
                        top: Annotated[int, typer.Option("--top", help="Rows printed to the terminal.")] = 15) -> None:
        """Rank all variants of runs/experiments/*/summary.json (FAR-cap compliant first, by CV@FAR20 recall)."""
        from callguard import report

        p, rows = report.leaderboard(out, runs_dir)
        cli.console.print(report.render_leaderboard(rows[:top]), markup=False, highlight=False)
        cli.console.print(f"[dim]{len(rows)} variants -> {cli._rel(p)}[/dim]")
