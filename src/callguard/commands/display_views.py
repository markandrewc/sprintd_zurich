"""``callguard display-views``: add the DISPLAY-ONLY views (config ``display_views``, e.g. the automatic Swiss
German transcript) to stored results, as a separate stage (e.g. on a 12 GB card once the translating LLM is up).

Only the key ``display_views`` of each ``result.json`` changes; transcript, checks and decision are written back
exactly as read. Translations are cached like every other view (``.cache/translate``).

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
import time
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def add_to_file(pipe, path: Path, *, names=None, force: bool = False) -> tuple[list[str], float]:
    """Add the missing display views to one ``result.json`` in place. Returns (names added, seconds)."""
    from callguard.config import ROOT
    from callguard.types import CallResult
    from callguard.ui.backend import reroot

    raw = json.loads(path.read_text())
    result = CallResult.model_validate(raw)
    # results made on another machine: find the recording under this checkout (in memory only; the stored
    # audio_path stays as written)
    local = reroot(result.audio_path, ROOT)
    for t in [result.transcript, *result.views.values()]:
        t.audio_path = reroot(t.audio_path, ROOT) or local
    result.audio_path = local
    t0 = time.time()
    added = pipe.add_display_views(result, names=names, force=force)
    if added:
        for n in added:  # stored like the rest of the file: the recording path as written there
            result.display_views[n].audio_path = raw.get("audio_path")
        raw["display_views"] = {**(raw.get("display_views") or {}),
                                **{n: result.display_views[n].model_dump(mode="json") for n in added}}
        tmp = path.with_suffix(".json.tmp")  # write-then-rename: the UI may be reading this folder
        tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=1))
        tmp.replace(path)
    return added, time.time() - t0


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("display-views")
    def display_views_cmd(
            runs_dir: Annotated[Optional[Path], typer.Option(
                "--runs-dir", help="Folder with <call_id>/result.json (default: runs dir of the profile).")] = None,
            calls: cli.CallsOpt = None,
            only: Annotated[Optional[str], typer.Option("--only", help="Comma-separated display view names.")] = None,
            force: Annotated[bool, typer.Option("--force", help="Recompute views that are already stored.")] = False,
            config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, no_cache: cli.NoCacheOpt = False,
            verbose: cli.VerboseOpt = False) -> None:
        """Add display-only views (e.g. automatic Swiss German) to stored result.json files; nothing else changes."""
        pipe = cli._pipeline(config, set_, no_cache, verbose)
        if not pipe.display_specs:
            cli.console.print(f"[yellow]Profil {pipe.cfg.name}: keine display_views konfiguriert.[/yellow]")
            raise typer.Exit(1)
        root = runs_dir or pipe.ctx.runs_dir
        files = sorted(root.glob("*/result.json"))
        if calls:
            wanted = {c.strip() for c in calls.split(",") if c.strip()}
            files = [f for f in files if f.parent.name in wanted]
        names = [n.strip() for n in only.split(",")] if only else None
        t = Table(title=f"display views · {len(files)} Anrufe · {cli._rel(root)}")
        for col in ("Anruf", "neu", "Zeit"):
            t.add_column(col)
        n_added = 0
        with cli._progress() as prog:
            task = prog.add_task("display-views", total=len(files))
            for f in files:
                prog.update(task, description=f.parent.name)
                try:
                    added, secs = add_to_file(pipe, f, names=names, force=force)
                except Exception as e:
                    cli.log.error("%s: %s: %s", f.parent.name, type(e).__name__, e, exc_info=verbose)
                    t.add_row(f.parent.name, "FEHLER", "-")
                else:
                    n_added += bool(added)
                    t.add_row(f.parent.name, ", ".join(added) or "-", f"{secs:.1f}s")
                prog.advance(task)
        cli.console.print(t)
        cli.console.print(f"{n_added} von {len(files)} Anrufen ergänzt.")
