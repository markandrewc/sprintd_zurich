"""``callguard agreement``: the pre-registered two-readers evaluation (research/findings/two_readers_prereg.md).

``run``   joins the stored single-reader variants per wording (agreement.PAIRS), re-fuses them with the
          ``two_readers`` fusion through the standard experiment runner (experiments/two_readers*.yaml) and
          writes the acceptance report (<runs>/experiments/two_readers/acceptance.md/.json). No model runs.
``merge`` joins two arbitrary stored variants into one source a ``refuse_from`` variant can read.

No ``from __future__ import annotations`` (typer resolves the annotations at runtime)."""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer


def register(app: typer.Typer) -> None:
    from callguard import cli

    grp = typer.Typer(help="Two readers (Qwen + Kev on one fact sheet): join stored runs, re-fuse, verdict.",
                      no_args_is_help=True)
    app.add_typer(grp, name="agreement")

    @grp.command("merge")
    def merge_cmd(a: Annotated[Path, typer.Argument(help="Reader A variant dir (its checks are kept).")],
                  b: Annotated[Path, typer.Argument(help="Reader B variant dir (its facts check is added).")],
                  out: Annotated[Path, typer.Argument(help="Output variant dir (results.jsonl + meta.json).")],
                  source_check: Annotated[str, typer.Option("--source-check", help="B's check to take.")] = "facts",
                  reader_b: Annotated[str, typer.Option("--as", help="Name of B's check in the output.")] = "facts_kev"
                  ) -> None:
        """Join two stored variants (same calls, one reader each) for a two-readers re-fusion."""
        from callguard import agreement as ag

        try:
            rep = ag.merge_variants(a, b, out, source_check=source_check, reader_b=reader_b)
        except FileNotFoundError as e:
            cli.console.print(f"[red]{e}[/red]")
            raise typer.Exit(2) from e
        cli.console.print(_merge_line(out.name, rep))

    @grp.command("run")
    def run_cmd(only: Annotated[Optional[str], typer.Option(
                    "--only", help=f"Comma-separated wordings (default: all of tuned, para, para2, blind, perturbed).")] = None,
                n_boot: Annotated[int, typer.Option("--n-boot", help="Bootstrap resamples.")] = 2000,
                seed: Annotated[int, typer.Option("--seed", help="Bootstrap seed.")] = 13,
                verbose: cli.VerboseOpt = False) -> None:
        """Join + re-fuse every available pair, then the pre-registered acceptance report."""
        from callguard import agreement as ag
        from callguard import experiments as ex
        from callguard import splits as sp
        from callguard.data import load_calls

        cli._setup_logging(verbose)
        wordings = [w.strip() for w in only.split(",")] if only else list(ag.PAIRS)
        bad = [w for w in wordings if w not in ag.PAIRS]
        if bad:
            raise typer.BadParameter(f"unknown wording(s) {bad} (have {list(ag.PAIRS)})", param_hint="--only")
        data: dict[str, dict[str, dict]] = {}
        sanity: dict[str, str] = {}
        by_spec: dict[str, list[str]] = {}
        for w in wordings:
            by_spec.setdefault(ag.PAIRS[w][0], []).append(w)
        report_dir = None
        for spec_name, ws in by_spec.items():
            spec = ex.load_spec(spec_name)
            base_cfg = ex.variant_config(spec, spec.variants[0])
            runs = base_cfg.paths.resolve("runs_dir") / "experiments"
            out = ex.experiment_dir(spec, base_cfg.paths.resolve("runs_dir"))
            report_dir = report_dir or out
            todo: list[str] = []
            for w in ws:
                _, src, ref_a, ref_b = ag.PAIRS[w]
                try:
                    rep = ag.merge_variants(runs / ref_a, runs / ref_b, out / src)
                except FileNotFoundError as e:
                    cli.console.print(f"[yellow]{w}: skipped ({e})[/yellow]")
                    continue
                cli.console.print(_merge_line(f"{w} ({ref_a} + {ref_b})", rep))
                todo += list(ag.pair_variants(spec, src).values())
            if not todo:
                continue
            data_dir = base_cfg.paths.resolve("data_dir")
            calls = ex.select_calls(load_calls(data_dir), spec.split, sp.load_splits(required=False))
            if not calls:
                cli.console.print(f"[yellow]{spec_name}: no labelled calls under {data_dir}: skipped[/yellow]")
                continue
            ex.run_experiment(spec, calls, variants=todo, jobs=1, runs_dir=base_cfg.paths.resolve("runs_dir"),
                              n_boot=n_boot, seed=seed)
            for w in ws:
                _, src, ref_a, ref_b = ag.PAIRS[w]
                roles = ag.pair_variants(spec, src)
                rows = {role: ex._read_rows(out / name) for role, name in roles.items() if (out / name / "rows.json").exists()}
                if not rows:
                    continue
                data[w] = rows
                for role, ref in (("a", ref_a), ("b", ref_b)):
                    stored = ex._read_rows(runs / ref)
                    if role in rows and stored:
                        chk = {k: ag.same_decisions(rows[role].get(k) or [], stored.get(k) or []) for k in ("fixed", "cv")}
                        sanity[f"{w} {ag.RULE_NAMES[role]} vs {ref}"] = "; ".join(
                            f"{k}: {len(c['differ'])}/{c['n']} calls differ" + (f" {c['differ'][:5]}" if c["differ"] else "")
                            for k, c in chk.items())
        if not data or report_dir is None:
            cli.console.print("[red]nothing to evaluate[/red]")
            raise typer.Exit(1)
        res = ag.acceptance(data, n_boot, seed)
        target = report_dir  # the first spec's experiment dir (two_readers unless --only perturbed)
        target.mkdir(parents=True, exist_ok=True)
        (target / "acceptance.md").write_text(ag.render_acceptance(res, sanity))
        (target / "acceptance.json").write_text(json.dumps({**res, "sanity": sanity}, ensure_ascii=False, indent=1,
                                                           default=str))
        for k, s in sanity.items():
            cli.console.print(f"[dim]sanity {k}: {s}[/dim]")
        for rule, v in res["verdict"].items():
            cli.console.print(f"[bold]{ag.RULE_NAMES[rule]}: {'PASS' if v['pass'] else 'FAIL'}[/bold]")
            for k in ("A1", "A2", "A3", "A4"):
                c = v["criteria"].get(k)
                cli.console.print(f"  {k} " + ("not evaluable" if c is None else f"{'pass' if c['pass'] else 'FAIL'}: {c['text']}"))
        cli.console.print(f"[dim]{cli._rel(target / 'acceptance.md')}[/dim]")


def _merge_line(name: str, rep: dict) -> str:
    warn = []
    for k in ("only_a", "only_b", "transcript_differs", "missing_b_check"):
        if rep.get(k):
            warn.append(f"{k}: {len(rep[k])}")
    for n, ids in (rep.get("shared_check_differs") or {}).items():
        warn.append(f"{n} differs: {len(ids)}")
    if rep.get("policy_table_mismatch"):
        warn.append(f"policy tables differ {rep['policy_tables']}")
    return f"joined {name}: {rep['n_merged']} calls" + (f" [yellow]({'; '.join(warn)})[/yellow]" if warn else "")
