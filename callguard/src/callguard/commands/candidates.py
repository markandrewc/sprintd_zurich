"""``callguard candidates``: every candidate system side by side with the same numbers (dev, paired against the
champion) + the open team decisions -> runs/candidates/candidates.json + docs/TEAM_OPTIONS.md.
Logic in :mod:`callguard.candidates`; no models run (evidence hit rate: alignment of stored results only).

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("candidates")
    def candidates_cmd(spec: Annotated[Optional[Path], typer.Option(
                           "--spec", help="Candidate spec (default experiments/contrib/candidates.yaml).")] = None,
                       out: Annotated[Optional[Path], typer.Option(
                           "--out", help="Output folder (default runs/candidates).")] = None,
                       doc: Annotated[Optional[Path], typer.Option(
                           "--doc", help="Markdown report (default docs/TEAM_OPTIONS.md).")] = None,
                       no_doc: Annotated[bool, typer.Option("--no-doc", help="Write only the JSON.")] = False,
                       evidence: Annotated[bool, typer.Option(
                           "--evidence/--no-evidence", help="Passage hit@1 per candidate from stored results.jsonl "
                                                            "(needs the labelled case data; cached per file).")] = True,
                       config: cli.ConfigOpt = "local", set_: cli.SetOpt = None,
                       n_boot: Annotated[Optional[int], typer.Option("--n-boot", help="Bootstrap resamples.")] = None,
                       seed: Annotated[Optional[int], typer.Option("--seed", help="Bootstrap seed.")] = None) -> None:
        """Candidate matrix for the team decisions (AUC, CV FAR/miss, review recall, 3-class accuracy,
        generalisation, evidence, cost, hardware) from stored experiment rows; pending cells fill in on re-run."""
        from callguard import candidates as cd

        try:
            s = cd.load_spec(spec)
        except (FileNotFoundError, cd.SpecError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        roots = {**cd.DEFAULT_ROOTS, **(s.get("data_roots") or {})}
        data = cd.Data(roots, s.get("experiments_dir"), cd.root_datasets(s))
        out_dir = out or cd.DEFAULT_OUT
        ev: dict = {}
        if evidence:
            ev = _evidence(cd, cli, data, s, Path(out_dir), config, set_ or [], n_boot, seed)
        result = cd.analyse(s, roots, n_boot=n_boot, seed=seed, evidence=ev)
        decisions = cd.load_yaml(None, cd.DEFAULT_DECISIONS)
        comparison = cd.load_yaml(None, cd.DEFAULT_COMPARISON)
        zurich = cd.zurich_status(comparison) if not comparison.get("_missing") else None
        pj, pm = cd.write_outputs(result, out_dir, False if no_doc else doc, decisions, comparison,
                                  cd.load_team(), zurich)
        t = Table(title=f"candidates (dev, {result['n_boot']} resamples; paired vs {result['reference']})")
        for col in ("candidate", "AUC", "FAR", "miss", "acc", "reworded", "blind", "re-rec.", "hit@1", "vs champion"):
            t.add_column(col, overflow="fold")
        for c in cd.visible(result):
            t.add_row(c.get("short") or c["id"], cd.cell(c, "auc"), cd.cell(c, "false_alarm_rate"),
                      cd.cell(c, "miss_rate"), cd.cell(c, "accuracy"), cd.cell(c, "reworded"), cd.cell(c, "blind"),
                      cd.cell(c, "rerecorded"), cd.cell(c, "hit1"),
                      "reference" if c["id"] == result["reference"] else cd.vs_text(c))
        cli.console.print(t)
        if result["pending"]:
            cli.console.print(f"[dim]{len(result['pending'])} cells pending / running (fill in on re-run):[/dim]")
            for p in result["pending"]:
                cli.console.print(f"[dim]  {p['candidate']}: {p['slot']} {p['ref']} ({p['status']})[/dim]")
        if zurich and zurich.get("stale"):
            cli.console.print(f"[yellow]teammate repo moved: {zurich['written_against'][:7]} -> "
                              f"{(zurich['head'] or '?')[:7]}; update experiments/contrib/comparison_zurich.yaml[/yellow]")
        cli.console.print(f"[dim]{cli._rel(pj)}" + (f" · {cli._rel(pm)}" if pm else "") + "[/dim]")


def _evidence(cd, cli, data, spec, out_dir: Path, config: str, sets: list, n_boot, seed) -> dict:
    """Evidence summaries for every candidate's tuned (or evidence_ref) variant; computed once per results file."""
    refs = [r for c in spec["candidates"] if not c.get("trivial")
            for r in [c.get("evidence_ref") or cd.resolve(data, c.get("tuned"))["ref"]] if r]
    state: dict = {}

    def compute(path: Path):
        if "calls" not in state:
            from callguard import splits as sp
            from callguard.data import load_calls

            try:
                cfg = cli.load_config(config, sets)
                state["calls"] = load_calls(cfg.paths.resolve("data_dir"))
            except Exception as e:  # noqa: BLE001 - no labelled data on this machine: skip evidence, say so
                cli.console.print(f"[yellow]evidence skipped: case data not loadable ({e})[/yellow]")
                state["calls"] = None
            locked = sp.load_splits(required=False)
            state["holdout"] = locked.holdout if locked else []
        if not state["calls"]:
            return None
        from callguard.commands.evidence_eval import results_summary

        return results_summary(path.parent, state["calls"], state["holdout"], int(n_boot or spec.get("n_boot") or 2000),
                               int(seed if seed is not None else spec.get("seed", 13)))

    return cd.evidence_for(data, refs, out_dir / "evidence_cache.json", compute)
