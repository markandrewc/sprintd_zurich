"""``callguard evidence-eval``: do our passages land on the annotated evidence turns (``Belege``)? Plus the
«möglicherweise verhört» 2x2 (wrong decisions vs low-confidence passages). Logic in
:mod:`callguard.eval_evidence`; evaluation only, dev dialogues only.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer


def results_summary(results_dir: Path, calls, holdout, n_boot: int = 2000, seed: int = 13) -> Optional[dict]:
    """Overall evidence hit rate of one stored variant (``results.jsonl`` folder), for ``callguard candidates``."""
    from callguard import eval_evidence as ee
    from callguard.experiments import load_results

    results = load_results(results_dir)
    if not results:
        return None
    ev = ee.evaluate_variant(str(results_dir), results, calls, holdout=holdout, n_boot=n_boot, seed=seed)
    a = ev.summary.get("all") or {}
    return {k: a.get(k) for k in ("n", "no_passage", "chance1", "median_len1", "hit1", "hit3")}


def register(app: typer.Typer) -> None:
    from callguard import cli

    @app.command("evidence-eval")
    def evidence_eval(
            variant: Annotated[Optional[list[str]], typer.Option(
                "--variant", "-V", help="Experiment variant <experiment>/<variant> under runs/experiments "
                                        "(repeatable; default: kev_vs_facts/champion, kev_facts, kev_general).")] = None,
            config: cli.ConfigOpt = "local", set_: cli.SetOpt = None,
            out: Annotated[Optional[Path], typer.Option(
                "--out", help="Output dir (default runs/evidence_eval).")] = None,
            show_alignments: Annotated[int, typer.Option(
                "--show-alignments", help="Print N evidence-turn alignments (script vs ASR) for a hand check.")] = 0,
            n_boot: Annotated[int, typer.Option("--n-boot", help="Bootstrap replicates.")] = 2000,
            seed: Annotated[int, typer.Option("--seed")] = 13) -> None:
        """Evidence hit rate @1/@3 of the shown passages vs the annotated Belege turns (dev), with bootstrap
        CIs, and whether wrong decisions rest on «möglicherweise verhört» passages more often."""
        from callguard import eval_evidence as ee
        from callguard import splits as sp
        from callguard.data import load_calls
        from callguard.misheard import threshold_of

        cli._setup_logging(False)
        cfg = cli.load_config(config, set_ or [])
        calls = load_calls(cfg.paths.resolve("data_dir"))
        locked = sp.load_splits(required=False)
        holdout = locked.holdout if locked else []
        root = cfg.paths.resolve("runs_dir") / "experiments"
        thr = threshold_of(cfg.snippets)
        evals, all_results = [], []
        for ref in variant or list(ee.DEFAULT_VARIANTS):
            results = ee.load_variant(root, ref)
            if not results:
                cli.console.print(f"[yellow]{ref}: no results.jsonl under {root / ref}, skipped[/yellow]")
                continue
            ev = ee.evaluate_variant(ref, results, calls, holdout=holdout, misheard_below=thr,
                                     n_boot=n_boot, seed=seed)
            if ev.dropped_holdout:
                cli.console.print(f"[yellow]{ref}: {len(ev.dropped_holdout)} holdout calls ignored (dev only)[/yellow]")
            evals.append(ev)
            all_results.extend(r for r in results if r.call_id.split("-K")[0] not in set(holdout))
            if show_alignments and len(evals) == 1:
                by_id = {c.call_id: c for c in calls}
                shown = 0
                for res in results:
                    c = by_id.get(res.call_id)
                    if shown >= show_alignments or c is None or c.expected is None or res.call_id.split("-K")[0] in holdout:
                        continue
                    al = ee.align(c.turns, res.transcript.segments)
                    for line in ee.spot_check_lines(res, c, al, c.expected.evidence_turns[:1]):
                        cli.console.print(line, markup=False, highlight=False, soft_wrap=True)
                        shown += 1
        if not evals:
            raise typer.Exit(1)
        md = ee.render_markdown(evals, ee.dev_threshold(all_results))
        out_dir = out or cfg.paths.resolve("runs_dir") / "evidence_eval"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "evidence.md").write_text(md)
        (out_dir / "evidence.json").write_text(json.dumps(
            {ev.name: {"summary": ev.summary, "misheard": ev.misheard, "anchors": ee.anchor_summary(ev.anchors),
                       "rows": ev.rows} for ev in evals}, ensure_ascii=False, indent=1, default=str))
        cli.console.print(md, markup=False, highlight=False, soft_wrap=True)
        cli.console.print(f"[dim]-> {cli._rel(out_dir / 'evidence.md')}[/dim]")
