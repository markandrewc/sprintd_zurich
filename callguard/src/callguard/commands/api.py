"""``callguard api``: the HTTP backend for the frontends (FastAPI + uvicorn). Contract: docs/API.md.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

from typing import Annotated, Optional

import typer

DEFAULT_PORT = 8600
DEFAULT_PROFILE = "sherlock"  # the production profile (config/sherlock.yaml)


def build_app(config: str = DEFAULT_PROFILE, sets: Optional[list[str]] = None, start_empty_rules: bool = False):
    from callguard.api.app import create_app
    from callguard.api.service import Service
    from callguard.config import load_config

    cfg = load_config(config, sets or [])
    svc = Service(cfg)
    if start_empty_rules:
        svc.set_rulebook("default", "demo")
    return create_app(svc)


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("api")
    def api_cmd(config: cli.ConfigOpt = DEFAULT_PROFILE, set_: cli.SetOpt = None,
                port: Annotated[int, typer.Option("--port", help="Port (frontends expect 8600).")] = DEFAULT_PORT,
                host: Annotated[str, typer.Option("--host", help="Bind address (0.0.0.0: reachable on the LAN).")]
                = "127.0.0.1",
                start_empty_rules: Annotated[bool, typer.Option(
                    "--start-empty-rules",
                    help="Start with the EMPTY demo rule book (in memory; config/policy_table.yaml is untouched). "
                         "The dashboard's «Apply our rule book» switches to the full rule book.")] = False) -> None:
        """HTTP API for the frontends on port 8600 (docs/API.md). Uses stored results only; runs no model.

        Another run folder: --set paths.runs_dir=<folder> (results are read from <folder>/<profile>/*/result.json).
        """
        import uvicorn

        application = build_app(config, set_ or [], start_empty_rules)
        svc = application.state.service
        svc.warm()
        import threading

        threading.Thread(target=svc.prewarm, name="api-prewarm", daemon=True).start()  # slider grid, background
        cli.console.print(f"[bold]Sherlock Phones API[/bold] · profile {svc.cfg.name} · {len(svc.results)} calls "
                          f"from {svc.runs_dir} · http://{host}:{port}/docs")
        if svc.demo_mode:
            cli.console.print("[yellow]Demo: empty rule book (in memory). «Apply our rule book» in the dashboard "
                              "or PUT /api/rulebook {\"mode\": \"production\"} switches to the full rule book.[/yellow]")
        if not svc.results:
            cli.console.print(f"[yellow]No result.json under {svc.runs_dir}: check -c and --set paths.runs_dir[/yellow]")
        uvicorn.run(application, host=host, port=port, log_level="info")
