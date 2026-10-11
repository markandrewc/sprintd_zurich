"""``callguard learn status/export/propose/proposals/approve/reject/rollback/demo-seed``: officer labels ->
learning datasets, readiness, and the four-eyes threshold proposal (docs/LEARNING.md).

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    learn_app = typer.Typer(no_args_is_help=True,
                            help="Learn from officer feedback: status, dataset export, threshold proposals (four-eyes).")
    app.add_typer(learn_app, name="learn")

    DemoOpt = Annotated[bool, typer.Option("--demo", help="Use the simulated demo feedback store (never trainable).")]
    UserOpt = Annotated[Optional[str], typer.Option("--user", "-u", envvar="CALLGUARD_USER", help="Who acts.")]

    def _ctx(config: str, set_: Optional[list[str]], verbose: bool):
        from callguard.context import Context

        cli._setup_logging(verbose)
        try:
            return Context(cli.load_config(config, set_ or []))
        except FileNotFoundError as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e

    def _labels(ctx, demo: bool):
        from callguard.eval import load_results
        from callguard.learning import hygiene, records

        results = {r.call_id: r for r in load_results(ctx.runs_dir)}
        splits = hygiene.splits_or_none()
        return results, splits, records.collect(ctx.runs_dir, results, splits, "demo" if demo else "real")

    def _user(user: Optional[str]) -> str:
        from callguard import audit

        return user or audit.current_user()

    @learn_app.command("status")
    def status_cmd(demo: DemoOpt = False, as_json: Annotated[bool, typer.Option("--json")] = False,
                   config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Labels per kind / family / fact, officer-vs-system agreement, most corrected facts, readiness."""
        from callguard.learning import insights

        ctx = _ctx(config, set_, verbose)
        _, _, labels = _labels(ctx, demo)
        ov, corr, ready = insights.overview(labels), insights.corrections(labels.facts), insights.readiness(labels)
        if as_json:
            cli.console.print_json(json.dumps({"overview": ov, "corrections": corr, "readiness": ready},
                                              ensure_ascii=False, default=str))
            return
        cm = ov["confusion"]
        cli.console.print(f"{'[yellow]DEMO (simuliert)[/yellow] ' if demo else ''}{ov['items']} items, "
                          f"{ov['calls']} call labels, {ov['facts']} fact labels, {ov['passages']} passage labels; "
                          f"officer = system on {cm['agree']}/{cm['n']} calls "
                          f"({cli._pct(cm['agreement'])}, 95% CI {cli._pct(cm['ci'][0])}-{cli._pct(cm['ci'][1])})")
        for c in corr:
            if c["advice"]:
                cli.console.print(f"[yellow]{c['advice']}[/yellow]")
        t = Table(title="Readiness")
        for col in ("step", "stage", "have", "need", "ready"):
            t.add_column(col)
        for r in ready:
            t.add_row(r["title"], r["stage"], str(r["have"]), str(r["need"]), "yes" if r["ready"] else "no")
        cli.console.print(t)

    @learn_app.command("export")
    def export_cmd(out: Annotated[Optional[str], typer.Option("--out", help="Folder (default runs/<profile>/learning/export[_demo]).")] = None,
                   demo: DemoOpt = False,
                   config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Write Kev / Qwen fact records, call labels and passage labels with split hygiene enforced."""
        from pathlib import Path

        from callguard.learning import export, hygiene

        ctx = _ctx(config, set_, verbose)
        results, splits, labels = _labels(ctx, demo)
        try:
            built = export.build(labels, results, splits)
        except hygiene.HygieneError as e:
            cli.console.print(f"[red]Export refused (split hygiene): {e}[/red]")
            raise typer.Exit(1) from e
        man = export.manifest(built, labels, splits)
        target = Path(out) if out else Path(ctx.runs_dir) / "learning" / ("export_demo" if demo else "export")
        export.write(target, built, man)
        for name, n in man["files"].items():
            cli.console.print(f"  {name}: {n}")
        cli.console.print(f"[green]-> {cli._rel(target)}[/green] (trainable fact labels: {man['trainable_fact_labels']})")

    @learn_app.command("propose")
    def propose_cmd(threshold: Annotated[Optional[float], typer.Option("--threshold", help="Propose this value instead of the fitted one.")] = None,
                    demo: DemoOpt = False, user: UserOpt = None, reason: Annotated[str, typer.Option("--reason", "-m")] = "",
                    max_far: Annotated[Optional[float], typer.Option("--max-far")] = None,
                    config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Fit the threshold on officer labels (dialogue-fold CV + paired bootstrap) and file a proposal."""
        from callguard.learning import proposals, recalibrate

        pipe = cli._pipeline(config, set_, False, verbose)
        results, splits, labels = _labels(pipe.ctx, demo)
        rec = recalibrate.propose_threshold(pipe, list(results.values()), {c: x.label for c, x in labels.calls.items()},
                                            splits, max_false_alarm_rate=max_far)
        cli.console.print(f"{rec['n_calls']} usable labelled calls ({rec['n_units']} units); current "
                          f"{rec['current_threshold']:.2f}, fitted {cli._num(rec['proposed_threshold'])}: "
                          f"{recalibrate.VERDICT_DE[rec['verdict']]}")
        for k, e in rec["effect"].items():
            cli.console.print(f"  {k}: {cli._num(e['a'], 3)} -> {cli._num(e['b'], 3)} (diff {cli._num(e['diff'], 3)}, "
                              f"95% CI {cli._num(e['lo'], 3)}..{cli._num(e['hi'], 3)})")
        value = threshold if threshold is not None else rec["proposed_threshold"]
        if value is None or (threshold is None and rec["verdict"] in ("keep", "too_few")):
            cli.console.print("[yellow]Nothing proposed.[/yellow]")
            return
        evidence = {k: rec[k] for k in ("n_calls", "n_units", "current_threshold", "proposed_threshold", "verdict",
                                        "effect", "cv", "label_counts")}
        p = proposals.propose(pipe.ctx.runs_dir, pipe.cfg.name, {"threshold": value}, user=_user(user),
                              reason=reason, evidence=evidence, label_source="demo" if demo else "real")
        cli.console.print(f"[green]{p.id}[/green] proposed by {p.proposed_by}: threshold {value:.2f} "
                          f"(needs approval by someone else: callguard learn approve {p.id} -u <name>)")

    @learn_app.command("proposals")
    def proposals_cmd(config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """List proposals and their state."""
        from callguard.learning import proposals

        ctx = _ctx(config, set_, verbose)
        t = Table(title="Proposals")
        for col in ("id", "profile", "change", "status", "proposed by", "approved by", "labels"):
            t.add_column(col)
        for p in proposals.load(ctx.runs_dir):
            t.add_row(p.id, p.profile, json.dumps(p.change), p.status, p.proposed_by, p.approved_by or "-", p.label_source)
        cli.console.print(t)

    def _act(action: str, pid: str, user: Optional[str], reason: str, config: str, set_, verbose: bool) -> None:
        from callguard import feedback as fb
        from callguard.learning import proposals

        ctx = _ctx(config, set_, verbose)
        try:
            if action == "approve":
                p = proposals.approve(ctx.runs_dir, pid, user=_user(user), tuning_path=fb.tuning_path(ctx.cfg), reason=reason)
            elif action == "reject":
                p = proposals.reject(ctx.runs_dir, pid, user=_user(user), reason=reason)
            else:
                p = proposals.rollback(ctx.runs_dir, pid, user=_user(user), tuning_path=fb.tuning_path(ctx.cfg), reason=reason)
        except (proposals.FourEyesError, proposals.ProposalStateError, KeyError) as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(1) from e
        cli.console.print(f"[green]{p.id}: {proposals.STATUS_DE[p.status]}[/green]")

    ReasonOpt = Annotated[str, typer.Option("--reason", "-m")]

    @learn_app.command("approve")
    def approve_cmd(pid: str, user: UserOpt = None, reason: ReasonOpt = "", config: cli.ConfigOpt = "local",
                    set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Approve a proposal (not by its proposer): written to the tuning overlay, audit-logged."""
        _act("approve", pid, user, reason, config, set_, verbose)

    @learn_app.command("reject")
    def reject_cmd(pid: str, user: UserOpt = None, reason: ReasonOpt = "", config: cli.ConfigOpt = "local",
                   set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Reject a proposal (not by its proposer)."""
        _act("reject", pid, user, reason, config, set_, verbose)

    @learn_app.command("rollback")
    def rollback_cmd(pid: str, user: UserOpt = None, reason: ReasonOpt = "", config: cli.ConfigOpt = "local",
                     set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Undo an approved proposal: the overlay entry from before the approval is restored."""
        _act("rollback", pid, user, reason, config, set_, verbose)

    @learn_app.command("demo-seed")
    def demo_seed_cmd(clear: Annotated[bool, typer.Option("--clear", help="Delete the demo store instead.")] = False,
                      config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Simulate officer feedback for the dev calls from the expected labels (separate demo store)."""
        from callguard.data import load_calls
        from callguard.eval import load_results
        from callguard.learning import demo, hygiene

        ctx = _ctx(config, set_, verbose)
        if clear:
            demo.clear(ctx.runs_dir)
            cli.console.print("[green]Demo feedback deleted.[/green]")
            return
        splits = hygiene.splits_or_none()
        if splits is None:
            cli.console.print("[red]config/splits.yaml missing: the dev calls are unknown.[/red]")
            raise typer.Exit(1)
        results = {r.call_id: r for r in load_results(ctx.runs_dir)}
        n = demo.seed(ctx.runs_dir, results, load_calls(ctx.data_dir), splits)
        cli.console.print(f"[green]{n} simulated items -> {cli._rel(ctx.runs_dir)}/feedback_demo.jsonl[/green] "
                          "(Demo-Feedback, simuliert aus Sollbewertung; never trainable)")
