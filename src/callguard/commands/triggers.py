"""``callguard triggers``: report stored results to the Outcept trigger API (case stretch goal).

The pipeline's ``outcept_trigger`` sink reports new calls as they are processed. This command does the same
for calls that are already decided (a run folder), e.g. to fill the Outcept list for the demo or after the
API was down. One trigger per suspicious passage; its link opens the callguard UI at the passage, 10 s early
(``snippets.link_pad``).

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

from pathlib import Path
from typing import Annotated, Optional

import typer


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("triggers")
    def triggers_cmd(config: cli.ConfigOpt = "local",
                     runs: Annotated[Optional[Path], typer.Option(
                         "--runs", help="Run folder with <call>/result.json (default: the profile's runs dir).")] = None,
                     url: Annotated[str, typer.Option(
                         "--url", help="Trigger endpoint.")] = "http://localhost:8080/triggers",
                     clear: Annotated[bool, typer.Option(
                         "--clear", help="DELETE all triggers first (fresh list for a demo).")] = False,
                     dry_run: Annotated[bool, typer.Option(
                         "--dry-run", help="Only print what would be sent.")] = False,
                     set_: cli.SetOpt = None) -> None:
        """Send alarm/review calls of a run folder to the Outcept trigger API (POST /triggers)."""
        import httpx

        from callguard.config import load_config
        from callguard.context import Context
        from callguard.eval import load_results
        from callguard.sinks.outcept import OutceptTriggerSink

        ctx = Context(load_config(config, set_ or []))
        sink = OutceptTriggerSink(ctx, url=url)
        folder = runs or ctx.runs_dir
        results = load_results(folder)
        bodies = [(r.call_id, b) for r in results for b in sink.triggers(r)]
        if dry_run:
            for cid, b in bodies:
                cli.console.print(f"{cid}: {b['title']}  ->  {b['url']}")
            cli.console.print(f"{len(bodies)} triggers from {len(results)} calls (dry run, nothing sent)")
            return
        base = url.rsplit("/triggers", 1)[0]
        try:
            httpx.get(f"{base}/health", timeout=5).raise_for_status()
            if clear:
                httpx.delete(url, timeout=5)
        except Exception as e:
            cli.console.print(f"[red]trigger API not reachable at {base}: {e}[/red]")
            raise typer.Exit(1) from e
        sent = failed = 0
        for cid, body in bodies:
            r = httpx.post(url, json=body, timeout=10)
            if r.status_code < 300:
                sent += 1
            else:
                failed += 1
                cli.console.print(f"[yellow]{cid}: HTTP {r.status_code} {r.text[:200]}[/yellow]")
        cli.console.print(f"{sent} triggers sent ({failed} rejected) from {len(results)} calls in {folder} "
                          f"-> {base}/triggers")
