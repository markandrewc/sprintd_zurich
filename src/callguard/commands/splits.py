"""``callguard splits``: show the locked dialogue split, or create it once with ``--make``.

No ``from __future__ import annotations`` here: typer evaluates the option annotations, and they must
resolve inside ``register`` (where ``cli`` is a local, not a module global).
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli
    from callguard import splits as sp

    @app.command("splits")
    def splits_cmd(make: Annotated[bool, typer.Option(
                       "--make", help="Create config/splits.yaml (refuses to overwrite an existing one).")] = False,
                   dev_folds: Annotated[int, typer.Option("--dev-folds", help="Number of dev folds (with --make).")] = 4,
                   seed: Annotated[int, typer.Option("--seed", help="Shuffle seed (with --make).")] = 13,
                   path: Annotated[Optional[Path], typer.Option(
                       "--path", help="Split file (default config/splits.yaml).")] = None,
                   config: cli.ConfigOpt = "local", set_: cli.SetOpt = None,
                   verbose: cli.VerboseOpt = False) -> None:
        """Show the locked holdout + dev folds (stratified by label and level; clean+noisy together)."""
        from callguard.config import load_config
        from callguard.data import load_calls

        cli._setup_logging(verbose)
        cfg = load_config(config, set_ or [])
        calls = load_calls(cfg.paths.resolve("data_dir"))
        if not calls:
            cli.console.print(f"[red]No calls found in {cfg.paths.resolve('data_dir')}/Audio[/red]")
            raise typer.Exit(1)
        if make:
            try:
                p = sp.write_splits(sp.make_splits(calls, dev_folds, seed), calls, path)
            except FileExistsError as e:
                cli.console.print(f"[red]{e}[/red]")
                raise typer.Exit(1) from e
            cli.console.print(f"[green]Wrote {cli._rel(p)}[/green] - commit it; it is now locked.")
        try:
            s = sp.load_splits(path)
        except sp.SplitsMissing as e:
            cli.console.print(f"[yellow]{e}[/yellow]")
            raise typer.Exit(1) from e
        t = Table(title=f"Dialogue split ({cli._rel(s.path)})")
        for col in ("fold", "dialogues", "labels", "levels", "ids"):
            t.add_column(col, overflow="fold")
        groups = {sp.HOLDOUT: s.holdout, **{f"dev{k}": v for k, v in sorted(s.dev_folds.items())}}
        desc = sp.describe(s, calls)
        for name, ids in groups.items():
            d = desc[name]
            t.add_row(name, str(d["n"]), ", ".join(f"{k} {v}" for k, v in d["labels"].items()),
                      ", ".join(f"S{k} {v}" for k, v in d["levels"].items()), " ".join(ids))
        cli.console.print(t)
        if s.groups:
            cli.console.print(f"Twin groups (same fold, one bootstrap unit): {' '.join(s.groups)}")
        known = {c.dialogue_id for c in calls}
        missing = sorted(known - set(s.fold_of()))
        if missing:
            cli.console.print(f"[yellow]{len(missing)} dialogue(s) not in the split (never dev, never holdout): "
                              f"{' '.join(missing)}[/yellow]")
        looks = sp.holdout_looks(cfg)
        cli.console.print(f"Holdout looks logged so far: {looks} ({cli._rel(sp.holdout_log_path(cfg))})")
