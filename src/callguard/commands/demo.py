"""``callguard demo``: the showcase app for the compliance officer (Streamlit, default port 8502).

Separate from the officer UI (``callguard ui``, 8501, unchanged): German, calm, only what the jury should
see. Both read the same results (runs/<profile>) and stores (feedback, audit log, Regelwerk versions).

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import os
import subprocess
import sys
from typing import Annotated, Optional

import typer

ACCENT = "#2a78d6"
THEME = {"base": "light", "primaryColor": ACCENT, "backgroundColor": "#ffffff",
         "secondaryBackgroundColor": "#f6f7f9", "textColor": "#1b1f24", "font": "sans-serif"}


def command(port: int, config: str, sets: list[str], no_cache: bool = False, headless: bool = False) -> list[str]:
    """The streamlit command line (tested without starting a server)."""
    from callguard.config import ROOT

    app_path = ROOT / "src" / "callguard" / "demo" / "app.py"
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path), "--server.port", str(port),
           "--browser.gatherUsageStats", "false", "--client.toolbarMode", "minimal"]
    for k, v in THEME.items():
        cmd += [f"--theme.{k}", v]
    if headless:
        cmd += ["--server.headless", "true"]
    cmd += ["--", "--config", config]
    for s in sets:
        cmd += ["--set", s]
    if no_cache:
        cmd.append("--no-cache")
    return cmd


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("demo")
    def demo_cmd(port: Annotated[int, typer.Option(help="Streamlit port.")] = 8502,
                 config: cli.ConfigOpt = "recommended", set_: cli.SetOpt = None, no_cache: cli.NoCacheOpt = False,
                 headless: Annotated[bool, typer.Option(help="Do not open a browser.")] = False,
                 url: Annotated[Optional[str], typer.Option(
                     help="Public base URL of the demo (Outcept backlinks); default http://localhost:<port>.")] = None
                 ) -> None:
        """Start the demo app (Fälle, Anruf prüfen, Einstellungen, Regelwerk, Qualität, Anruf verarbeiten)."""
        from callguard.config import ROOT
        from callguard.demo import DEMO_URL_ENV

        cmd = command(port, config, set_ or [], no_cache, headless)
        env = {**os.environ, DEMO_URL_ENV: url or f"http://localhost:{port}"}
        cli.console.print(f"[dim]{' '.join(cmd)}[/dim]")
        try:
            code = subprocess.run(cmd, cwd=ROOT, env=env).returncode
        except KeyboardInterrupt:
            code = 0
        raise typer.Exit(code)
