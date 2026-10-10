"""``callguard synth scripts|validate``: synthetic text scripts from config/synth_scenarios.yaml.

Logic in :mod:`callguard.synth`. No ``from __future__ import annotations``: typer must resolve the option
annotations, which reference ``cli`` inside ``register``.
"""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    synth = typer.Typer(no_args_is_help=True, help="Synthetic calls: LLM-written scripts in the case layout "
                                                   "(text only; evaluate with the ORACLE profile synth-oracle).")
    app.add_typer(synth, name="synth")

    ScenOpt = Annotated[Optional[Path], typer.Option("--scenarios", help="Scenario file (default "
                                                                         "config/synth_scenarios.yaml).")]
    OutOpt = Annotated[Path, typer.Option("--out", help="Output set directory.")]

    def _jobs(scenarios, only, family):
        from callguard.synth import scenarios as sc
        try:
            jobs = sc.plan(sc.load_scenarios(scenarios))
        except (sc.ScenarioError, FileNotFoundError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        if only:
            want = {x.strip() for x in only.split(",") if x.strip()}
            jobs = [j for j in jobs if j.scenario.id in want or j.dialogue_id in want]
        if family:
            jobs = [j for j in jobs if j.scenario.family == family]
        return jobs

    def _plan_table(jobs) -> Table:
        from callguard.synth import scenarios as sc
        t = Table(title=f"synthetic scripts: {len(jobs)}")
        for col in ("family", "alarm", "review", "no_alert", "scenarios"):
            t.add_column(col)
        summ = sc.summary(jobs)
        for fam, counts in summ.items():
            t.add_row(fam, *(str(counts.get(k, 0)) for k in ("alarm", "review", "no_alert")),
                      str(len({j.scenario.id for j in jobs if j.family == fam})))
        return t

    @synth.command("scripts")
    def scripts_cmd(out: OutOpt = Path("data_synth/v1"), scenarios: ScenOpt = None,
                    only: Annotated[Optional[str], typer.Option(
                        "--only", help="Comma-separated scenario ids or Synth_* ids.")] = None,
                    family: Annotated[Optional[str], typer.Option("--family", help="Only this scenario family.")] = None,
                    jobs: Annotated[int, typer.Option("--jobs", "-j", help="Scenarios in parallel (max 4).")] = 4,
                    force: Annotated[bool, typer.Option("--force", help="Rewrite scripts that exist already.")] = False,
                    attempts: Annotated[int, typer.Option("--attempts", help="Tries per script.")] = 4,
                    temperature: Annotated[float, typer.Option("--temperature")] = 0.8,
                    wait: Annotated[float, typer.Option(
                        "--wait", help="Minutes to wait for the LLM server to come up.")] = 40.0,
                    llm_name: Annotated[str, typer.Option("--llm", help="LLM entry of the profile.")] = "default",
                    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show the plan only.")] = False,
                    config: cli.ConfigOpt = "gpu-12gb", set_: cli.SetOpt = None,
                    verbose: cli.VerboseOpt = False) -> None:
        """Write the scenario scripts with the profile's LLM (expected labels come from the scenarios)."""
        from callguard.config import ROOT, load_config
        from callguard.context import Context
        from callguard.synth import scripts as sw

        cli._setup_logging(verbose)
        todo = _jobs(scenarios, only, family)
        cli.console.print(_plan_table(todo))
        if dry_run or not todo:
            return
        out_dir = out if out.is_absolute() else ROOT / out
        cfg = load_config(config, set_ or [])
        llm = Context(cfg).llm(llm_name)
        if not sw.wait_for_llm(llm, wait * 60, on_wait=lambda s: cli.console.print(
                f"[yellow]LLM {getattr(llm, 'base_url', '')} not ready, waited {s / 60:.1f} min[/yellow]")):
            cli.console.print(f"[red]LLM not reachable after {wait:g} min; nothing generated.[/red]")
            raise typer.Exit(1)
        cli.console.print(f"LLM: {sw._model_name(llm)} -> {cli._rel(out_dir)}")

        def show(o) -> None:
            mark = "[green]ok[/green]" if o.ok else "[red]FAILED[/red]"
            cli.console.print(f"{o.job.dialogue_id} {o.job.scenario.id}/{o.job.variant.name} "
                              f"({o.job.variant.label}): {mark} {o.mode} attempts={o.attempts} {o.seconds}s"
                              + ("" if o.ok else f" {o.errors[-1] if o.errors else ''}"))

        res = sw.generate_set(todo, llm, out_dir, workers=max(1, min(4, jobs)), force=force, attempts=attempts,
                              temperature=temperature, progress=show)
        failed = [o for o in res if not o.ok]
        modes = {m: sum(1 for o in res if o.ok and o.mode == m) for m in ("existing", "free", "rewrite")}
        cli.console.print(f"{len(res) - len(failed)}/{len(res)} scripts ok ({modes}); "
                          f"manifest {cli._rel(out_dir / 'manifest.json')}")
        if failed:
            cli.console.print(f"[red]failed: {', '.join(o.job.dialogue_id for o in failed)}[/red] - rerun to retry "
                              f"(existing scripts are kept)")
            raise typer.Exit(1)

    @synth.command("validate")
    def validate_cmd(out: OutOpt = Path("data_synth/v1"), scenarios: ScenOpt = None) -> None:
        """Offline check of a written set against the scenario plan (no LLM)."""
        from callguard.config import ROOT
        from callguard.data import load_calls
        from callguard.synth import scripts as sw

        out_dir = out if out.is_absolute() else ROOT / out
        todo = _jobs(scenarios, None, None)
        problems = sw.validate_set(out_dir, todo)
        calls = load_calls(out_dir)
        cli.console.print(_plan_table(todo))
        cli.console.print(f"{len(calls)} text-only calls load from {cli._rel(out_dir)}; "
                          f"{len({c.group for c in calls})} twin groups")
        for d, errs in problems.items():
            cli.console.print(f"[red]{d}: {'; '.join(errs)}[/red]")
        if problems:
            raise typer.Exit(1)
        cli.console.print("[green]all scripts valid[/green]")
