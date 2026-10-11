"""``callguard contrib``: which component contributes what (paired factor comparisons over stored results)
-> runs/contrib/contrib.json + contrib.md. Logic in :mod:`callguard.contrib`; no models run.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("contrib")
    def contrib_cmd(spec: Annotated[Optional[Path], typer.Option(
                        "--spec", help="Factor spec (default experiments/contrib/contrib.yaml).")] = None,
                    data_root: Annotated[Optional[Path], typer.Option(
                        "--data-root", help="Folder with <experiment>/<variant>/rows.json (default: "
                                            "$CALLGUARD_CONTRIB_DATA, else the spec's data_root, runs/experiments).")] = None,
                    out: Annotated[Optional[Path], typer.Option(
                        "--out", help="Output folder (default runs/contrib).")] = None,
                    n_boot: Annotated[Optional[int], typer.Option("--n-boot", help="Bootstrap resamples.")] = None,
                    seed: Annotated[Optional[int], typer.Option("--seed", help="Bootstrap seed.")] = None) -> None:
        """Paired deltas with 95% CIs per factor (check design, ASR, LLM size, wording, ...) from stored rows."""
        from callguard import contrib as cb

        try:
            s = cb.load_spec(spec)
        except (FileNotFoundError, cb.SpecError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        root = cb.resolve_data_root(data_root or s.get("data_root"))
        if not root.exists():
            cli.console.print(f"[red]data root {root} does not exist (pass --data-root)[/red]")
            raise typer.Exit(2)
        result = cb.analyse(s, root, n_boot=n_boot, seed=seed)
        pj, pm = cb.write_outputs(result, out)
        t = Table(title=f"contrib: B - A, 95% CI ({result['n_boot']} resamples); bold = real")
        for col in ("factor", "comparison", "status", "n", "d AUC", "d FAR", "d miss", "d acc", "flips", "verdict"):
            t.add_column(col, justify="left" if col in ("factor", "comparison", "status", "verdict") else "right",
                         overflow="fold")
        missing = 0
        for f in result["factors"]:
            for p in f["pairs"]:
                if p["verdict"] == "missing":
                    missing += 1
                    continue
                d = p.get("deltas") or {}

                def cell(k: str, pct: bool) -> str:
                    x = d.get(k) or {}
                    if x.get("diff") is None:
                        return "-"
                    v = f"{100 * x['diff']:+.0f}pp" if pct else f"{x['diff']:+.2f}"
                    return f"[bold]{v}[/bold]" if x.get("real") else v

                t.add_row(f["id"], p["label"], p["status"], str(p.get("n_common") or "-"), cell("auc", False),
                          cell("false_alarm_rate", True), cell("miss_rate", True), cell("accuracy", True),
                          str((p.get("flips") or {}).get("n", "-")), p["verdict"])
        cli.console.print(t)
        if missing:
            cli.console.print(f"[dim]{missing} comparisons pending/missing (no rows.json yet); listed in contrib.md[/dim]")
        cli.console.print(f"[dim]{cli._rel(pm)} · {cli._rel(pj)}[/dim]")
