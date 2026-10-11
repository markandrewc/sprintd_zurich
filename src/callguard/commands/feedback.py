"""``callguard feedback add/list/suggest/apply``: officer verdicts -> threshold + keyword suggestions ->
``config/tuning.yaml`` overlay.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    from callguard import cli

    fb_app = typer.Typer(no_args_is_help=True, help="Officer feedback: record verdicts, get and apply tuning suggestions.")
    app.add_typer(fb_app, name="feedback")

    def _ctx(config: str, set_: Optional[list[str]], verbose: bool):
        from callguard.context import Context

        cli._setup_logging(verbose)
        try:
            return Context(cli.load_config(config, set_ or []))
        except FileNotFoundError as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e

    @fb_app.command("add")
    def add_cmd(call_id: Annotated[str, typer.Argument(help="Call id.")],
                verdict: Annotated[str, typer.Argument(
                    help="confirmed | false_alarm | missed | should_review | not_review")],
                family: Annotated[Optional[str], typer.Option("--family")] = None,
                passage: Annotated[Optional[int], typer.Option("--passage", help="Passage index (0-based).")] = None,
                comment: Annotated[str, typer.Option("--comment", "-m")] = "",
                user: Annotated[Optional[str], typer.Option("--user", envvar="CALLGUARD_USER")] = None,
                config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Record a verdict on a call (or one passage of it)."""
        from callguard import feedback as fb
        from callguard.eval import load_results

        ctx = _ctx(config, set_, verbose)
        if verdict not in fb.VERDICTS:
            cli.console.print(f"[red]verdict must be one of {', '.join(fb.VERDICTS)}[/red]")
            raise typer.Exit(2)
        stored = {r.call_id: r for r in load_results(ctx.runs_dir)}
        res = stored.get(call_id)
        if res is None:
            cli.console.print(f"[yellow]No stored result for {call_id}; feedback recorded anyway.[/yellow]")
        item = fb.FeedbackItem(call_id=call_id, verdict=verdict, family=family, passage_index=passage, comment=comment,
                               label_seen=res.decision.label if res else None,
                               threshold_seen=res.decision.threshold if res else None,
                               **({"user": user} if user else {}))
        fb.add(ctx.runs_dir, item)
        cli.console.print(f"[green]{call_id}: {fb.VERDICT_DE[verdict]}[/green] -> {cli._rel(fb.feedback_path(ctx.runs_dir))}")

    @fb_app.command("list")
    def list_cmd(call: Annotated[Optional[str], typer.Option("--call")] = None,
                 config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Show recorded feedback."""
        from callguard import feedback as fb

        ctx = _ctx(config, set_, verbose)
        items = [i for i in fb.load(ctx.runs_dir) if call is None or i.call_id == call]
        t = Table(title=f"Feedback ({len(items)})")
        for col in ("ts", "user", "call", "verdict", "seen", "family", "passage", "comment"):
            t.add_column(col, overflow="fold")
        for i in items:
            t.add_row(i.ts, i.user, i.call_id, i.verdict, i.label_seen or "-", i.family or "-",
                      "-" if i.passage_index is None else str(i.passage_index), i.comment)
        cli.console.print(t)

    def _suggest(config: str, set_: Optional[list[str]], verbose: bool, truth: str, max_far: Optional[float]):
        from callguard import feedback as fb
        from callguard.eval import load_results

        cli._setup_logging(verbose)
        pipe = cli._pipeline(config, set_, False, verbose)
        results = load_results(pipe.ctx.runs_dir)
        gt = _truth(pipe, truth)
        return pipe, fb.suggest(pipe, results, fb.load(pipe.ctx.runs_dir), truth=gt, max_false_alarm_rate=max_far)

    def _truth(pipe, mode: str) -> Optional[dict]:
        if mode == "none":
            return None
        from callguard.data import load_calls

        calls = [c for c in load_calls(pipe.ctx.data_dir) if c.expected]
        if mode == "dev":  # holdout discipline: the holdout's labels never tune anything
            from callguard import splits as sp

            s = sp.load_splits(required=False)
            if s is None:
                cli.console.print("[red]--truth dev needs config/splits.yaml (callguard splits --make).[/red]")
                raise typer.Exit(1)
            dev = set(s.dev_dialogues())
            calls = [c for c in calls if c.dialogue_id in dev]
        elif mode != "all":
            raise typer.BadParameter("none | dev | all", param_hint="--truth")
        return {c.call_id: c.expected.label for c in calls}

    TruthOpt = Annotated[str, typer.Option(
        "--truth", help="Also use the case's expected labels for calls without feedback: none | dev | all.")]
    FarOpt = Annotated[Optional[float], typer.Option("--max-far", help="Cap the false-alarm rate of the suggestion.")]

    @fb_app.command("suggest")
    def suggest_cmd(truth: TruthOpt = "none", max_far: FarOpt = None,
                    as_json: Annotated[bool, typer.Option("--json")] = False,
                    config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Suggested threshold (with expected false-alarm / miss change), keywords to reconsider, check reliability."""
        _, s = _suggest(config, set_, verbose, truth, max_far)
        if as_json:
            cli.console.print_json(json.dumps(s, ensure_ascii=False, default=str))
            return
        cli.console.print(f"{s['n_labelled']} labelled calls (feedback {s['sources']['feedback']}, "
                          f"ground truth {s['sources']['ground_truth']}); {s['n_feedback']} feedback items.")
        if s["warning"]:
            cli.console.print(f"[yellow]{s['warning']}[/yellow]")
        if s["suggestion"]:
            c, b, d = s["current"], s["suggestion"], s["delta"]
            cli.console.print(f"Current threshold {s['current_threshold']:.2f}: FP {c['fp']}, FN {c['fn']} | "
                              f"suggested [bold]{b['threshold']:.2f}[/bold]: FP {b['fp']} ({d['fp']:+d}), "
                              f"FN {b['fn']} ({d['fn']:+d}), alarms {d['alarms']:+d}, reviews {d['reviews']:+d}")
            cli.console.print(b["reason"])
            cli.console.print(f"[dim]Apply: callguard feedback apply --suggested -c {config}[/dim]")
        kws = [k for k in s["keywords"] if k["suggest_disable"]]
        for k in kws:
            cli.console.print(f"[yellow]{k['advice']}[/yellow]")
        if s["keywords"]:
            t = Table(title="Keyword precision on labelled calls")
            for col in ("keyword", "calls", "flag-worthy", "harmless", "precision"):
                t.add_column(col)
            for k in s["keywords"]:
                t.add_row(k["keyword"], str(k["calls"]), str(k["flagged"]), str(k["harmless"]), f"{k['precision']:.0%}")
            cli.console.print(t)
        if s["checks"]:
            t = Table(title="Check reliability")
            for col in ("check", "n", "mean score flag-worthy", "mean score harmless", "separation", "agreement"):
                t.add_column(col)
            for c in s["checks"]:
                t.add_row(c["check"], str(c["n"]), *(cli._num(c[k]) for k in
                          ("mean_score_flagworthy", "mean_score_harmless", "separation", "agreement")))
            cli.console.print(t)

    @fb_app.command("apply")
    def apply_cmd(threshold: Annotated[Optional[float], typer.Option("--threshold")] = None,
                  suggested: Annotated[bool, typer.Option("--suggested", help="Use the threshold `suggest` proposes.")] = False,
                  review_band: Annotated[Optional[float], typer.Option("--review-band")] = None,
                  weight: Annotated[Optional[list[str]], typer.Option("--weight", help="check=weight (repeatable).")] = None,
                  clear: Annotated[bool, typer.Option("--clear", help="Remove this profile's overlay.")] = False,
                  reason: Annotated[str, typer.Option("--reason", "-m")] = "",
                  truth: TruthOpt = "none", max_far: FarOpt = None,
                  config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, verbose: cli.VerboseOpt = False) -> None:
        """Write the tuning overlay (config/tuning.yaml, per profile): threshold, review band, check weights."""
        from callguard import feedback as fb

        ctx = _ctx(config, set_, verbose)
        if suggested:
            _, s = _suggest(config, set_, verbose, truth, max_far)
            if not s["suggestion"]:
                cli.console.print(f"[red]No suggestion: {s['warning'] or 'nothing to sweep'}[/red]")
                raise typer.Exit(1)
            threshold = s["suggestion"]["threshold"]
            reason = reason or (f"feedback suggest: {s['n_labelled']} labelled calls, FP {s['delta']['fp']:+d}, "
                                f"FN {s['delta']['fn']:+d}")
        weights = {}
        for w in weight or []:
            k, _, v = w.partition("=")
            try:
                weights[k.strip()] = float(v)
            except ValueError as e:
                raise typer.BadParameter(f"expected check=weight, got {w!r}", param_hint="--weight") from e
        if not clear and threshold is None and review_band is None and not weights:
            cli.console.print("[red]Nothing to apply: give --threshold / --suggested / --review-band / --weight / --clear.[/red]")
            raise typer.Exit(2)
        info = fb.apply_tuning(fb.tuning_path(ctx.cfg), ctx.cfg.name, threshold=threshold, review_band=review_band,
                               weights=weights, runs_dir=ctx.runs_dir, reason=reason, clear=clear)
        cli.console.print(f"[green]{'Cleared' if clear else 'Wrote'} {cli._rel(info['path'])}[/green] "
                          f"(profile {ctx.cfg.name}): {info['after'] if not clear else '-'}")
        cli.console.print("[dim]Re-decide stored calls: callguard route --all --redecide, or reload the UI.[/dim]")
