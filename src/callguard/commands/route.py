"""``callguard route``: who is told about a call (config/routing.yaml + directory.yaml), optionally send it.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("route")
    def route_cmd(call_id: Annotated[Optional[str], typer.Argument(
                      help="Call id (runs/<profile>/<call_id>/result.json). Omit with --all.")] = None,
                  all_: Annotated[bool, typer.Option("--all", help="Route every stored call (overview table).")] = False,
                  send: Annotated[bool, typer.Option("--send", help="Deliver through the channels (default: outbox).")] = False,
                  channel: Annotated[Optional[list[str]], typer.Option(
                      "--channel", help="outbox | webhook | smtp (repeatable; default outbox).")] = None,
                  webhook_url: Annotated[Optional[str], typer.Option("--webhook-url")] = None,
                  force: Annotated[bool, typer.Option("--force", help="Queue even if the same message is already in the outbox.")] = False,
                  redecide: Annotated[bool, typer.Option(
                      "--redecide", help="Re-run fusion under the current profile/tuning/--set instead of the stored label.")] = False,
                  as_json: Annotated[bool, typer.Option("--json", help="Print the message as JSON.")] = False,
                  config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Route a decided call to the right desk(s): teams by family/label/pattern, supervisor cc, deep link."""
        from callguard.context import Context
        from callguard.eval import load_results
        from callguard.sinks.notify import Notifier

        cli._setup_logging(verbose)
        try:
            cfg = cli.load_config(config, set_ or [])
        except FileNotFoundError as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        ctx = Context(cfg)
        results = {r.call_id: r for r in load_results(ctx.runs_dir)}
        if not all_ and not call_id:
            cli.console.print("[red]Give a call id or --all.[/red]")
            raise typer.Exit(2)
        ids = sorted(results) if all_ else [call_id]
        missing = [c for c in ids if c not in results]
        if missing:
            cli.console.print(f"[red]No result for {', '.join(missing)} in {cli._rel(ctx.runs_dir)} "
                              f"(run `callguard run`/`batch -c {cfg.name}` first).[/red]")
            raise typer.Exit(1)
        n = Notifier(ctx, channels=channel or ["outbox"], webhook_url=webhook_url)
        pipe = cli.Pipeline(cfg) if redecide else None
        analysis = n.analysis()
        table = Table(title=f"Routing ({cfg.name})") if all_ else None
        if table is not None:
            for col in ("call", "label", "families", "to", "cc", "patterns", "sent"):
                table.add_column(col, overflow="fold")
        for cid in ids:
            res = results[cid]
            dec = pipe.decide(res.transcript, res.checks, None, views=res.views or None) if pipe else None
            r, msg = n.message(res, dec, analysis)
            status = n.send(msg, force=force) if (send and msg) else {}
            if table is not None:
                table.add_row(cid, r.label, ", ".join(r.families) or "-", ", ".join(x.name for x in r.to) or "-",
                              ", ".join(x.name for x in r.cc) or "-", ", ".join(r.patterns) or "-",
                              ", ".join(f"{k}:{v}" for k, v in status.items()) or "-")
                continue
            if msg is None:
                cli.console.print(f"{cid}: label [bold]{r.label}[/bold] is not routed (routing.yaml labels).")
                continue
            if as_json:
                cli.console.print_json(json.dumps(msg, ensure_ascii=False, default=str))
            else:
                cli.console.print(f"[bold]{msg['subject']}[/bold]")
                cli.console.print("An: " + "; ".join(f"{x['name']} <{x['email']}> ({'; '.join(x['why'])})" for x in msg["to"]))
                if msg["cc"]:
                    cli.console.print("Cc: " + "; ".join(f"{x['name']} <{x['email']}> ({'; '.join(x['why'])})" for x in msg["cc"]))
                cli.console.print(msg["body"], markup=False, highlight=False)
            if status:
                cli.console.print("Versand: " + ", ".join(f"{k} {v}" for k, v in status.items()))
        if table is not None:
            cli.console.print(table)
