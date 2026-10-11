"""``callguard asr-eval`` and ``callguard asr-eval-compare``: ASR quality on the case data
(WER/CER vs the gsw scripts, keyword-spot recall, speed). Logic in :mod:`callguard.eval_asr`."""

# no ``from __future__ import annotations``: typer resolves the option annotations at runtime and
# ``cli`` is a local import inside register()
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table


def register(app: typer.Typer) -> None:
    # cli helpers imported here, not at module level: cli.py imports this module at its end
    from callguard import cli
    from callguard import eval_asr as ea

    @app.command("asr-eval")
    def asr_eval(config: cli.ConfigOpt = "local", set_: cli.SetOpt = None, level: cli.LevelOpt = None,
                 clean_only: cli.CleanOpt = False, limit: cli.LimitOpt = None, calls: cli.CallsOpt = None,
                 out: Annotated[Optional[Path], typer.Option(
                     "--out", help="Output dir (default runs/asr_eval/<tag>).")] = None,
                 tag: Annotated[Optional[str], typer.Option(
                     "--tag", help="Run name (default: ASR model dir name + compute type).")] = None,
                 cached_only: Annotated[bool, typer.Option(
                     "--cached-only", help="Skip calls whose transcript is not in the ASR cache (never run ASR).")] = False,
                 ref_dir: Annotated[Optional[Path], typer.Option(
                     "--ref-dir", file_okay=False,
                     help="Pseudo-references <call_id>.txt or <dialogue_id>.txt (e.g. de translation).")] = None,
                 sweep_log: Annotated[Optional[Path], typer.Option(
                     "--sweep-log", dir_okay=False,
                     help="Timing log of scripts/research/asr_sweep.py (default runs/logs/asr_sweep_<tag>.jsonl"
                          " if present); used where the transcript has no elapsed_s.")] = None,
                 per_call: Annotated[bool, typer.Option("--per-call/--no-per-call",
                                                        help="Print the per-call table.")] = True,
                 split: Annotated[str, typer.Option(
                     "--split", help="dev (default: the dev dialogues of config/splits.yaml), holdout or all; "
                                     "holdout and all include holdout dialogues and are logged to "
                                     "runs/holdout_log.jsonl.")] = "dev",
                 no_cache: cli.NoCacheOpt = False, verbose: cli.VerboseOpt = False) -> None:
        """WER/CER vs the reference scripts + keyword-spot recall + ASR speed, per call/level/clean-noisy."""
        from callguard import splits as sp

        if split not in sp.SPLIT_CHOICES:
            raise typer.BadParameter(f"expected one of {', '.join(sp.SPLIT_CHOICES)}", param_hint="--split")
        pipe = cli._pipeline(config, set_, no_cache, verbose)
        selected = cli._select_calls(pipe, level, clean_only, limit, calls)
        try:
            locked = sp.load_splits(required=split != "all")
        except sp.SplitsMissing as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        if locked is not None:
            selected = locked.select(selected, split)
        if not selected:
            cli.console.print(f"[red]No calls selected (split {split}).[/red]")
            raise typer.Exit(1)
        if split in (sp.HOLDOUT, "all"):
            cli.console.print(f"[bold yellow]asr-eval on split {split} (includes holdout dialogues): this run is "
                              f"logged as a holdout look (earlier looks: {sp.holdout_looks(pipe.cfg)}).[/bold yellow]")
        run_tag = tag or ea.default_tag(pipe.cfg.asr)
        out_dir = out or pipe.ctx.path("runs_dir") / "asr_eval" / run_tag
        if sweep_log is None and (cli.ROOT / "runs" / "logs" / f"asr_sweep_{run_tag}.jsonl").exists():
            sweep_log = cli.ROOT / "runs" / "logs" / f"asr_sweep_{run_tag}.jsonl"
        with cli._progress() as progress:
            task = progress.add_task("asr-eval", total=len(selected))

            def on_call(c: cli.Call) -> None:
                progress.update(task, description=f"asr-eval {c.call_id}")
                progress.advance(task)

            res = ea.run_asr_eval(pipe, selected, tag=run_tag, cached_only=cached_only, ref_dir=ref_dir,
                                  profile=config, overrides=set_, sweep_log=sweep_log,
                                  on_call=on_call)
        res.summary["meta"]["split"] = split
        ea.write_outputs(res, out_dir)
        if split in (sp.HOLDOUT, "all"):
            g = res.summary["groups"].get("all") or {}
            lp = sp.log_holdout_run(pipe.cfg, {}, len(res.rows), kind=f"asr-eval {run_tag}", overrides=set_ or [],
                                    extra={"split": split, "asr": {k: g.get(k) for k in
                                                                   ("wer", "cer", "kw_recall", "n_calls")}})
            cli.console.print(f"[dim]Holdout look logged: {cli._rel(lp)}[/dim]")
        render(res, per_call)
        cli.console.print(f"\n[dim]{ea.WER_GSW_LABEL}. Brackets: 95% dialogue bootstrap CI.[/dim]")
        if res.skipped:
            why = "not cached" if cached_only else "no reference script"
            cli.console.print(f"[yellow]{len(res.skipped)} call(s) skipped ({why}).[/yellow]")
        cli.console.print(f"Wrote {cli._rel(out_dir)}/{{per_call.csv, summary.json, summary.md}}")

    @app.command("asr-eval-compare")
    def asr_eval_compare(tags: Annotated[list[str], typer.Argument(help="Run tags under runs/asr_eval/ (or dirs).")],
                         root: Annotated[Path, typer.Option(help="Where the runs live.")] = Path("runs/asr_eval"),
                         out: Annotated[Optional[Path], typer.Option(help="Also write the markdown here.")] = None
                         ) -> None:
        """Side-by-side table of several asr-eval runs (WER, CER, kw-spot recall, false hits, speed)."""
        root = root if root.is_absolute() else cli.ROOT / root
        md = ea.compare(tags, root)
        if out:
            out.write_text(md)
        cli.console.print(md, markup=False, highlight=False, soft_wrap=True)

    def render(res: ea.AsrEvalResult, per_call: bool) -> None:
        t = Table(title=f"ASR eval {res.tag}", title_justify="left")
        for c in ea.GROUP_COLUMNS:
            t.add_column(c, justify="left" if c == "group" else "right", no_wrap=c == "group")
        for name, g in res.summary["groups"].items():
            t.add_row(*ea.group_cells(name, g))
        cli.console.print(t)
        kw = Table(title="Keyword spots", title_justify="left")
        for c in ("keyword", "spots", "found ASR", "found script", "false-hit calls"):
            kw.add_column(c, justify="right")
        for k, d in res.summary["per_keyword"].items():
            kw.add_row(k, str(d["annotated"]), str(d["matched"]), str(d["ref_matched"]), str(d["false_hit_calls"]))
        cli.console.print(kw)
        if per_call and res.rows:
            pc = Table(title="Per call", title_justify="left")
            for c in ("call", "WER", "CER", "kw", "missed", "false hits", "RTF"):
                pc.add_column(c, justify="left" if c in ("call", "missed", "false hits") else "right")
            for r in res.rows:
                pc.add_row(r["call_id"], ea.fmt_pct(r["wer"]), ea.fmt_pct(r["cer"]),
                           f"{r['kw_matched']}/{r['kw_annotated']}", r["kw_missed_ids"] or "-",
                           r["kw_false_hit_ids"] or "-", ea.fmt_num(r["rtf"], 3))
            cli.console.print(pc)
