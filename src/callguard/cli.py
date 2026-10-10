"""``callguard`` command line: run calls, batch the case data, evaluate, watch a folder, start the UI.

Every command takes the same profile options (``-c local|gpu|oracle|path.yaml``, ``--set a.b=c``,
``--no-cache``, ``-v``) so switching laptop -> event GPU is a flag, never a code change.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated, Any, Optional

import typer
from rich.console import Console, Group
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from callguard import registry
from callguard.config import ROOT, load_config
from callguard.data import Call, dialogue_of, load_calls, split_dialogues
from callguard.pipeline import Pipeline
from callguard.types import CallResult, Decision, fmt_ts

app = typer.Typer(name="callguard", no_args_is_help=True, add_completion=False,
                  help="Swiss German bank-call compliance checks: transcribe, check, fuse, alert.")
console = Console()
log = logging.getLogger("callguard")

LABEL_STYLE = {"alarm": "bold white on red", "review": "bold black on yellow", "no_alert": "bold white on green"}
LABEL_TEXT = {"alarm": "ALARM", "review": "PRÜFEN", "no_alert": "KEIN ALARM"}
AUDIO_SUFFIXES = (".wav", ".flac", ".mp3", ".m4a", ".ogg")

ConfigOpt = Annotated[str, typer.Option("--config", "-c", envvar="CALLGUARD_CONFIG",
                                        help="Profile name (config/<name>.yaml) or path to a YAML file.")]
SetOpt = Annotated[Optional[list[str]], typer.Option(
    "--set", help="Override a config value, e.g. --set fusion.threshold=0.4 (repeatable).")]
NoCacheOpt = Annotated[bool, typer.Option("--no-cache", help="Recompute every stage instead of using .cache/.")]
VerboseOpt = Annotated[bool, typer.Option("--verbose", "-v", help="Log pipeline progress (INFO).")]
LevelOpt = Annotated[Optional[int], typer.Option("--level", "-l", help="Only calls of this level (1, 2, 3).")]
CleanOpt = Annotated[bool, typer.Option("--clean-only", help="Only the clean recordings (no noise variants).")]
LimitOpt = Annotated[Optional[int], typer.Option("--limit", "-n", help="Process at most N calls.")]
CallsOpt = Annotated[Optional[str], typer.Option("--calls", help="Comma-separated call ids, e.g. Stufe1_D02-K1.")]


# --------------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------------


def _setup_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    root = logging.getLogger()
    if not any(isinstance(h, RichHandler) for h in root.handlers):
        root.addHandler(RichHandler(console=Console(stderr=True), show_path=False, rich_tracebacks=False))
    root.setLevel(level)
    log.setLevel(level)


def _pipeline(config: str, set_: list[str] | None, no_cache: bool, verbose: bool) -> Pipeline:
    _setup_logging(verbose)
    try:
        cfg = load_config(config, set_ or [])
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(2) from e
    return Pipeline(cfg, use_cache=not no_cache)


def _label(label: str) -> Text:
    return Text(f" {LABEL_TEXT.get(label, label)} ", style=LABEL_STYLE.get(label, "bold"))


def _num(x: float | None, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def _pct(x: float | None) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def _rel(p: str | Path | None) -> str:
    if not p:
        return "-"
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def _select_calls(pipe: Pipeline, level: int | None = None, clean_only: bool = False, limit: int | None = None,
                  call_ids: str | None = None, folds: str | None = None) -> list[Call]:
    calls = load_calls(pipe.ctx.data_dir)
    if not calls:
        console.print(f"[red]No calls found in {pipe.ctx.data_dir}/Audio[/red]")
        raise typer.Exit(1)
    if folds:
        wanted = set(_numbers(folds, "--folds", int))
        fold_of = split_dialogues(calls)  # computed on the full set so folds are stable under filters
        calls = [c for c in calls if fold_of.get(c.dialogue_id) in wanted]
    if call_ids:
        ids = [c.strip() for c in call_ids.split(",") if c.strip()]
        unknown = set(ids) - {c.call_id for c in calls}
        if unknown:
            console.print(f"[yellow]Unknown call ids ignored: {', '.join(sorted(unknown))}[/yellow]")
        calls = [c for c in calls if c.call_id in ids]
    if level is not None:
        calls = [c for c in calls if c.level == level]
    if clean_only:
        calls = [c for c in calls if not c.noisy]
    return calls[:limit] if limit is not None else calls


def _numbers(text: str, option: str, kind: type = float) -> list:
    try:
        return [kind(x) for x in text.split(",") if x.strip()]
    except ValueError as e:
        raise typer.BadParameter(f"expected comma-separated numbers, got {text!r}", param_hint=option) from e


def _families_table(d: Decision) -> Table:
    t = Table(box=None, pad_edge=False, show_header=True, header_style="dim")
    for col in ("Familie", "Score", "Unsicherheit", "pro Prüfung"):
        t.add_column(col)
    for f in sorted(d.families.values(), key=lambda f: -f.score):
        per = ", ".join(f"{k} {v:.2f}{'?' if f.verdicts.get(k) == 'undetermined' else ''}"
                        for k, v in f.per_check.items())
        t.add_row(f.label, _num(f.score), _num(f.uncertainty), per or "-")
    return t


def render_result(r: CallResult) -> Panel:
    d = r.decision
    head = Text.assemble(_label(d.label), f"  Score {d.score:.2f}  ·  Unsicherheit {d.uncertainty:.2f}  ·  "
                                          f"Schwelle {d.threshold:.2f}")
    parts: list[Any] = [head, ""]
    parts += [Text(f"• {reason}") for reason in d.reasons]
    if d.passages:
        parts += ["", Text("Verdächtige Passagen", style="bold")]
        for i, p in enumerate(d.passages, 1):
            parts.append(Text.assemble((f"{i}. {fmt_ts(p.start)}-{fmt_ts(p.end)} ", "bold cyan"),
                                       f"{p.family_label or p.family}  (Score {p.score:.2f}; {', '.join(p.checks)})"))
            parts += [Text(f"   - {reason}") for reason in p.reasons]
            if p.text:
                txt = p.text if len(p.text) <= 300 else p.text[:299] + "…"
                parts.append(Text(f'   "{txt}"', style="italic"))
            if p.snippet_path:
                parts.append(Text(f"   Audio: {_rel(p.snippet_path)}", style="dim"))
    for warning in r.meta.get("warnings", []):
        parts += ["", Text(f"Warnung: {warning}", style="yellow")]
    errors = {k: v.meta["error"] for k, v in r.checks.items() if v.meta.get("error")}
    if errors:
        parts += ["", Text("Ausgefallene Prüfungen: " + "; ".join(f"{k}: {v}" for k, v in errors.items()),
                           style="red")]
    if d.families:
        parts += ["", _families_table(d)]
    if r.timings:
        parts += ["", Text("Zeiten: " + ", ".join(f"{k} {v:.1f}s" for k, v in r.timings.items()), style="dim")]
    return Panel(Group(*parts), title=f"[bold]{r.call_id}[/bold]", subtitle=r.config_name, expand=True)


# --------------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------------


@app.command()
def plugins(config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
            verbose: VerboseOpt = False) -> None:
    """List every plugin type, whether its module is installed and which ones the profile uses."""
    _setup_logging(verbose)
    used: dict[str, set[str]] = {k: set() for k in registry.KINDS}
    try:
        cfg = load_config(config, set_ or [])
        used["asr"].add(cfg.asr.get("type", ""))
        pre = cfg.asr.get("preprocess")
        if pre:
            used["preprocess"].add(pre if isinstance(pre, str) else pre.get("type", ""))
        used["diarizer"].add(cfg.diarizer.get("type", ""))
        used["fusion"].add(cfg.fusion.get("type", ""))
        used["check"] |= {c.get("type", "") for c in cfg.checks if c.get("enabled", True)}
        used["sink"] |= {s.get("type", "") for s in cfg.sinks if s.get("enabled", True)}
        used["llm"] |= {spec.get("type", "") for spec in cfg.llms.values()}
    except Exception as e:  # listing plugins must work even with a broken profile
        console.print(f"[yellow]config {config!r} not loaded: {e}[/yellow]")

    t = Table(title=f"callguard plugins (profile: {config})")
    for col in ("kind", "type", "class", "status", "used"):
        t.add_column(col)
    for kind, names in registry.available().items():
        for name in names:
            path = registry.BUILTINS[kind].get(name)
            if path:
                module = path.partition(":")[0]
                try:
                    ok = find_spec(module) is not None
                except (ImportError, ValueError):
                    ok = False
                status = "[green]ok[/green]" if ok else "[red]missing[/red]"
            else:
                path, status = "(registered)", "[green]ok[/green]"
            t.add_row(kind, name, path, status, "[bold]yes[/bold]" if name in used[kind] else "")
    console.print(t)


@app.command()
def transcribe(audio: Annotated[Path, typer.Argument(exists=True, dir_okay=False, help="Audio file.")],
               diarize: Annotated[bool, typer.Option(help="Also run speaker separation / roles.")] = True,
               config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
               verbose: VerboseOpt = False) -> None:
    """Transcribe one audio file and print it line by line."""
    pipe = _pipeline(config, set_, no_cache, verbose)
    t = pipe.transcribe(audio, audio.stem)
    if diarize:
        t = pipe.diarize(audio, t)
    console.print(f"[dim]{t.asr_backend} · {len(t.segments)} Segmente · {fmt_ts(t.duration or 0)}[/dim]")
    console.print(t.render(), markup=False, highlight=False)


@app.command()
def run(audio: Annotated[list[Path], typer.Argument(exists=True, dir_okay=False, help="Audio file(s).")],
        as_json: Annotated[bool, typer.Option("--json", help="Print the CallResult JSON instead.")] = False,
        config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
        verbose: VerboseOpt = False) -> None:
    """Check call(s) end to end: transcribe, run all checks, decide, cut snippets, notify sinks."""
    pipe = _pipeline(config, set_, no_cache, verbose)
    failed = 0
    for a in audio:
        try:
            r = pipe.process(a)
        except Exception as e:
            log.error("call %s failed", a, exc_info=verbose)
            console.print(f"[red]{a.name}: {type(e).__name__}: {e}[/red]")
            failed += 1
            continue
        if as_json:
            print(r.model_dump_json(indent=1))
        else:
            console.print(render_result(r))
    if failed:
        raise typer.Exit(1)


@app.command()
def batch(level: LevelOpt = None, clean_only: CleanOpt = False, limit: LimitOpt = None, calls: CallsOpt = None,
          config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
          verbose: VerboseOpt = False) -> None:
    """Process the case dataset calls and write each result via the sinks (UI files, triggers)."""
    pipe = _pipeline(config, set_, no_cache, verbose)
    selected = _select_calls(pipe, level, clean_only, limit, calls)
    t = Table(title=f"{len(selected)} Anrufe · Profil {pipe.cfg.name}")
    for col in ("Anruf", "Ergebnis", "Score", "Unsicherheit", "Passagen", "Soll", "Zeit"):
        t.add_column(col)
    counts: dict[str, int] = {}
    with _progress() as prog:
        task = prog.add_task("batch", total=len(selected))
        for call in selected:
            prog.update(task, description=call.call_id)
            t0 = time.time()
            try:
                r = pipe.process(call.audio_path, call.call_id)
            except Exception as e:
                log.error("call %s failed: %s: %s", call.call_id, type(e).__name__, e, exc_info=verbose)
                t.add_row(call.call_id, Text("FEHLER", style="red"), "-", "-", "-",
                          call.expected.label if call.expected else "-", f"{time.time() - t0:.0f}s")
                counts["error"] = counts.get("error", 0) + 1
            else:
                d = r.decision
                counts[d.label] = counts.get(d.label, 0) + 1
                exp = call.expected.label if call.expected else "-"
                mark = "" if exp == "-" else (" ✓" if exp == d.label else " ✗")
                t.add_row(call.call_id, _label(d.label), _num(d.score), _num(d.uncertainty), str(len(d.passages)),
                          exp + mark, f"{time.time() - t0:.0f}s")
            prog.advance(task)
    console.print(t)
    console.print("  ".join(f"{LABEL_TEXT.get(k, k)}: {v}" for k, v in sorted(counts.items())))
    console.print(f"[dim]Ergebnisse: {_rel(pipe.ctx.runs_dir)}[/dim]")


@app.command("eval")
def eval_cmd(level: LevelOpt = None, clean_only: CleanOpt = False, limit: LimitOpt = None, calls: CallsOpt = None,
             folds: Annotated[Optional[str], typer.Option(
                 "--folds", help="Only dialogues in these folds (5 dialogue-level folds), e.g. 0,1.")] = None,
             do_sweep: Annotated[bool, typer.Option("--sweep/--no-sweep", help="Try other thresholds.")] = True,
             thresholds: Annotated[Optional[str], typer.Option(
                 "--thresholds", help="Comma-separated thresholds for the sweep (default 0.20..0.90).")] = None,
             write_results: Annotated[bool, typer.Option(
                 "--write-results/--no-write-results", help="Also write result.json per call for the UI.")] = True,
             cv: Annotated[bool, typer.Option(
                 "--cv/--no-cv", help="Cross-validate the suggested threshold over dialogue-level folds.")] = True,
             split: Annotated[str, typer.Option(
                 "--split", help="dev (default; tuning: CV over the dev folds of config/splits.yaml), holdout "
                                 "(final number, logged to runs/holdout_log.jsonl) or all (dev + holdout; also "
                                 "logged as a holdout look; thresholds are still fitted on dev only).")] = "dev",
             config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
             verbose: VerboseOpt = False) -> None:
    """Measure false alarms and misses on the case calls, sweep the threshold, write a report."""
    from callguard import eval as ev
    from callguard import splits as sp
    from callguard.sinks.json_dir import JsonDirSink

    if split not in sp.SPLIT_CHOICES:
        raise typer.BadParameter(f"expected one of {', '.join(sp.SPLIT_CHOICES)}", param_hint="--split")
    ts = _numbers(thresholds, "--thresholds", float) if thresholds else None  # fail before the long run
    pipe = _pipeline(config, set_, no_cache, verbose)
    selected = _select_calls(pipe, level, clean_only, limit, calls, folds)
    locked = sp.load_splits(required=split != "all")
    cv_folds = None
    test_only: set[int] = set()
    if locked is not None:
        selected = locked.select(selected, split)
        cv_folds = locked.dev_fold_of() if split == "dev" else locked.all_fold_of()
        if split == "all" and locked.holdout:  # holdout is scored, never fitted on
            test_only = {max(locked.dev_folds, default=-1) + 1}
    if split == "all":
        console.print(f"[bold yellow]--split all includes the holdout dialogues: this run is logged as a "
                      f"holdout look (earlier looks: {sp.holdout_looks(pipe.cfg)}); thresholds are fitted on "
                      f"dev only. Do not tune on these numbers (use --split dev).[/bold yellow]")
    if split == sp.HOLDOUT:
        do_sweep = cv = False  # the holdout scores the config as it is; tuning on it would be peeking
        console.print(f"[bold]Holdout run[/bold] ({len(selected)} calls); this look is logged "
                      f"(earlier looks: {sp.holdout_looks(pipe.cfg)}).")
    if not selected:
        console.print("[red]No calls selected.[/red]")
        raise typer.Exit(1)
    with _progress() as prog:
        task = prog.add_task("eval", total=len(selected))

        def on_call(i: int, n: int, call: Call, row: dict) -> None:
            prog.update(task, completed=i, description=f"{call.call_id} -> {row['predicted']}")

        rows, results = ev.evaluate(pipe, selected, progress=on_call)

    if write_results:
        for s in pipe.sinks:
            if isinstance(s, JsonDirSink) and s.enabled:
                for r in results:
                    s.emit(r)

    m = ev.metrics(rows)
    console.print(_metrics_table(m, pipe.cfg.fusion.get("threshold")))
    console.print(_confusion_table(m))
    groups = {**{f"Stufe {k}": v for k, v in m["by_level"].items()}, **m["by_noise"]}
    if groups:
        console.print(_groups_table(groups))

    swept, suggestion, cvr = None, None, None
    fit_results = results
    if split == "all" and locked is not None:  # the suggestion must not see holdout labels
        dev = set(locked.dev_dialogues())
        fit_results = [r for r in results if dialogue_of(r.call_id) in dev]
    if do_sweep and fit_results:
        swept = ev.sweep(pipe, fit_results, selected, ts)
        suggestion = ev.suggest_threshold(swept)
        console.print(_sweep_table(swept, suggestion, pipe.cfg.fusion.get("threshold")))
        if suggestion:
            console.print(f"[bold]Vorschlag:[/bold] {suggestion['reason']}  "
                          f"[dim](--set fusion.threshold={suggestion['threshold']:.2f})[/dim]")
        if cv:
            cvr = ev.cross_validate(pipe, results, selected, thresholds=ts, fold_of=cv_folds, test_only=test_only)
            if cvr:
                console.print(_cv_table(cvr))

    meta = {"config": pipe.cfg.name, "threshold": pipe.cfg.fusion.get("threshold"), "calls": len(selected),
            "split": split,
            "filters": {"level": level, "clean_only": clean_only, "limit": limit, "calls": calls, "folds": folds},
            "overrides": set_ or [], "created": time.strftime("%Y-%m-%d %H:%M:%S")}
    if split in (sp.HOLDOUT, "all"):
        lp = sp.log_holdout_run(pipe.cfg, m, len(selected), kind="eval" if split == sp.HOLDOUT else "eval (split all)",
                                overrides=set_ or [], extra={"split": split})
        console.print(f"[dim]Holdout look logged: {_rel(lp)} (looks so far: {sp.holdout_looks(pipe.cfg)})[/dim]")
    j, md = ev.write_report(pipe.ctx.runs_dir / ("eval" if split == "all" else f"eval_{split}"), m, rows, swept,
                            suggestion, meta, cvr)
    console.print(f"[dim]Bericht: {_rel(md)} · {_rel(j)}[/dim]")


@app.command()
def watch(folder: Annotated[Path, typer.Argument(file_okay=False, help="Folder the call recorder drops audio into.")],
          interval: Annotated[float, typer.Option(help="Seconds between folder scans.")] = 5.0,
          state: Annotated[Optional[Path], typer.Option(
              help="State file of processed calls (default <runs_dir>/watch_state.json).")] = None,
          settle: Annotated[float, typer.Option(help="Seconds a file must be unchanged before processing.")] = 2.0,
          once: Annotated[bool, typer.Option("--once", help="Process what is there now, then exit.")] = False,
          retry_failed: Annotated[bool, typer.Option("--retry-failed", help="Retry files that failed before.")] = False,
          config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
          verbose: VerboseOpt = False) -> None:
    """Check every new recording in a folder exactly once (no manual step per call)."""
    pipe = _pipeline(config, set_, no_cache, verbose)
    folder.mkdir(parents=True, exist_ok=True)
    state_path = state or pipe.ctx.runs_dir / "watch_state.json"
    done = _load_state(state_path)
    if retry_failed:
        done = {k: v for k, v in done.items() if v.get("status") != "error"}
    console.print(f"Beobachte {folder} (alle {interval:g}s, Status: {_rel(state_path)}). Abbrechen mit Ctrl+C.")
    try:
        while True:
            for f in _ready_files(folder, done, settle, once):
                key = str(f.resolve())
                try:
                    r = pipe.process(f)
                except Exception as e:
                    log.error("watch: %s failed", f, exc_info=verbose)
                    done[key] = {"status": "error", "error": f"{type(e).__name__}: {e}", "at": time.time()}
                    console.print(f"[red]{f.name}: {type(e).__name__}: {e}[/red]")
                else:
                    d = r.decision
                    done[key] = {"status": "done", "call_id": r.call_id, "label": d.label,
                                 "score": round(d.score, 4), "at": time.time()}
                    first = f" · {fmt_ts(d.passages[0].start)} {d.passages[0].family}" if d.passages else ""
                    console.print(Text.assemble(time.strftime("%H:%M:%S "), _label(d.label),
                                                f" {r.call_id}  Score {d.score:.2f}{first}"))
                _save_state(state_path, done)
            if once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("gestoppt.")


def _load_state(path: Path) -> dict[str, dict[str, Any]]:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except (OSError, ValueError):
        log.warning("watch state %s unreadable, starting fresh", path)
        return {}


def _save_state(path: Path, state: dict[str, dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    tmp.replace(path)


def _ready_files(folder: Path, done: dict[str, Any], settle: float, once: bool) -> list[Path]:
    """New audio files that are no longer being written (unchanged for ``settle`` seconds)."""
    now = time.time()
    out = []
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in AUDIO_SUFFIXES or not f.is_file() or str(f.resolve()) in done:
            continue
        st = f.stat()
        if st.st_size > 0 and (once or now - st.st_mtime >= settle):
            out.append(f)
    return out


@app.command()
def ui(port: Annotated[Optional[int], typer.Option(help="Streamlit port (default 8501).")] = None,
       config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
       verbose: VerboseOpt = False) -> None:
    """Start the compliance officer UI (Streamlit)."""
    app_path = ROOT / "src" / "callguard" / "ui" / "app.py"
    if not app_path.exists():
        console.print(f"[red]UI not found: {app_path}[/red]")
        raise typer.Exit(1)
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    if port:
        cmd += ["--server.port", str(port)]
    cmd += ["--", "--config", config]
    for s in set_ or []:
        cmd += ["--set", s]
    console.print(f"[dim]{' '.join(cmd)}[/dim]")
    try:
        code = subprocess.run(cmd, cwd=ROOT).returncode
    except KeyboardInterrupt:
        code = 0
    raise typer.Exit(code)


DOCTOR_STYLE = {"OK": "green", "WARN": "yellow", "FAIL": "bold red", "SKIP": "dim"}


@app.command()
def doctor(config: ConfigOpt = "local", set_: SetOpt = None, no_cache: NoCacheOpt = False,
           verbose: VerboseOpt = False) -> None:
    """Check that the profile can run: servers reachable, models present, CUDA usable (loads no model).

    Exit code 1 if any row is FAIL. Run it on the GPU host (-c gpu-12gb) and from the laptop (-c remote).
    """
    from callguard.serve import doctor as doc

    _setup_logging(verbose)
    rows = doc.run(config, set_ or [], use_cache=not no_cache)
    t = Table(title=f"callguard doctor (profile: {config})")
    for col in ("area", "check", "status", "detail", "hint"):
        t.add_column(col, overflow="fold")
    for r in rows:
        t.add_row(r.area, r.item, Text(r.status, style=DOCTOR_STYLE.get(r.status, "")), r.detail, r.hint,
                  end_section=False)
    console.print(t)
    counts = {s: sum(r.status == s for r in rows) for s in DOCTOR_STYLE}
    console.print("  ".join(f"[{DOCTOR_STYLE[s]}]{s} {n}[/]" for s, n in counts.items() if n))
    if doc.failed(rows):
        raise typer.Exit(1)


# --------------------------------------------------------------------------------------------
# tables
# --------------------------------------------------------------------------------------------


def _progress() -> Progress:
    return Progress(TextColumn("{task.description}"), BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(),
                    console=console, transient=True)


def _metrics_table(m: dict[str, Any], threshold: float | None) -> Table:
    flag, alarm, rh = m["flag"], m["alarm"], m["review_handling"]
    t = Table(title=f"Erkennungsqualität ({m['n']} Anrufe, Schwelle {_num(threshold)})", show_header=False)
    t.add_column("Kennzahl")
    t.add_column("Wert", justify="right")
    t.add_row("Fehlalarmquote (harmlos, aber markiert)",
              f"{_pct(flag['false_alarm_rate'])}  ({flag['fp']}/{flag['fp'] + flag['tn']})")
    t.add_row("Verpasste Fälle (markierungswürdig, kein Alarm)",
              f"{_pct(flag['miss_rate'])}  ({flag['fn']}/{flag['tp'] + flag['fn']})")
    t.add_row("Markiert: Precision / Recall / F1",
              f"{_pct(flag['precision'])} / {_pct(flag['recall'])} / {_num(flag['f1'])}")
    t.add_row("Nur Alarm: Precision / Recall / F1",
              f"{_pct(alarm['precision'])} / {_pct(alarm['recall'])} / {_num(alarm['f1'])}")
    t.add_row("Accuracy (3 Klassen)", _pct(m["accuracy"]))
    t.add_row("Soll-Prüffälle eskaliert", f"{rh['escalated']}/{rh['n']} (als Prüfen: {rh['as_review']})")
    t.add_row("Familie getroffen (Soll-Alarme)", f"{m['family_hit']['hits']}/{m['family_hit']['n']}")
    if m["errors"]:
        t.add_row("[red]Fehler (als Prüfen gezählt)[/red]", str(m["errors"]))
    return t


def _confusion_table(m: dict[str, Any]) -> Table:
    t = Table(title="Konfusionsmatrix", caption="Zeile = Soll, Spalte = Ist")
    t.add_column("Soll \\ Ist")
    labels = list(m["confusion"])
    for p in labels:
        t.add_column(LABEL_TEXT.get(p, p), justify="right")
    for e in labels:
        t.add_row(LABEL_TEXT.get(e, e), *(f"[bold]{m['confusion'][e][p]}[/bold]" if e == p else str(m["confusion"][e][p])
                                          for p in labels))
    return t


def _groups_table(groups: dict[str, dict[str, Any]]) -> Table:
    t = Table(title="Aufschlüsselung")
    for col in ("Gruppe", "n", "Accuracy", "Precision", "Recall", "F1", "Fehlalarme", "Verpasst"):
        t.add_column(col, justify="left" if col == "Gruppe" else "right")
    for k, s in groups.items():
        t.add_row(k, str(s["n"]), _pct(s["accuracy"]), _pct(s["flag_precision"]), _pct(s["flag_recall"]),
                  _num(s["flag_f1"]), _pct(s["false_alarm_rate"]), _pct(s["miss_rate"]))
    return t


def _cv_table(cvr: dict[str, Any]) -> Table:
    f = cvr["metrics"]["flag"]
    thresholds = ", ".join(f"{x['threshold']:.2f}" for x in cvr["folds"])
    t = Table(title=f"Kreuzvalidierung ({cvr['n_folds']} Dialog-Folds, Schwelle je Fold auf den übrigen gewählt)",
              show_header=False)
    t.add_column("Kennzahl")
    t.add_column("Wert", justify="right")
    t.add_row("Gewählte Schwellen", thresholds)
    t.add_row("Fehlalarmquote (out-of-fold)", f"{_pct(f['false_alarm_rate'])}  ({f['fp']}/{f['fp'] + f['tn']})")
    t.add_row("Verpasste Fälle (out-of-fold)", f"{_pct(f['miss_rate'])}  ({f['fn']}/{f['tp'] + f['fn']})")
    t.add_row("Markiert: Precision / Recall / F1",
              f"{_pct(f['precision'])} / {_pct(f['recall'])} / {_num(f['f1'])}")
    t.add_row("Accuracy (3 Klassen)", _pct(cvr["metrics"]["accuracy"]))
    return t


def _sweep_table(swept: list[dict[str, Any]], suggestion: dict[str, Any] | None, current: float | None) -> Table:
    t = Table(title="Schwellen-Sweep (nur Fusion neu berechnet)")
    for col in ("Schwelle", "Precision", "Recall", "F1", "Fehlalarme", "Verpasst", "Alarm-F1", "Accuracy", ""):
        t.add_column(col, justify="right")
    best = suggestion["threshold"] if suggestion else None
    for s in swept:
        f, a = s["metrics"]["flag"], s["metrics"]["alarm"]
        tags = []
        if current is not None and abs(s["threshold"] - float(current)) < 1e-9:
            tags.append("aktuell")
        if best is not None and abs(s["threshold"] - best) < 1e-9:
            tags.append("[bold green]Vorschlag[/bold green]")
        t.add_row(f"{s['threshold']:.2f}", _pct(f["precision"]), _pct(f["recall"]), _num(f["f1"]),
                  _pct(f["false_alarm_rate"]), _pct(f["miss_rate"]), _num(a["f1"]), _pct(s["metrics"]["accuracy"]),
                  " ".join(tags))
    return t



# commands living in callguard/commands/<name>.py, each with register(app)
from callguard.commands import agreement as _agreement  # noqa: E402
from callguard.commands import asr_eval as _asr_eval  # noqa: E402
from callguard.commands import candidates as _candidates  # noqa: E402
from callguard.commands import contrib as _contrib  # noqa: E402
from callguard.commands import evidence_eval as _evidence_eval  # noqa: E402
from callguard.commands import experiment as _experiment  # noqa: E402
from callguard.commands import feedback as _feedback  # noqa: E402
from callguard.commands import fit_fusion as _fit_fusion  # noqa: E402
from callguard.commands import leaderboard as _leaderboard  # noqa: E402
from callguard.commands import patterns as _patterns  # noqa: E402
from callguard.commands import report as _report  # noqa: E402
from callguard.commands import route as _route  # noqa: E402
from callguard.commands import splits as _splits  # noqa: E402
from callguard.commands import synth as _synth  # noqa: E402
from callguard.commands import triggers as _triggers  # noqa: E402

for _mod in (_asr_eval, _splits, _experiment, _leaderboard, _report, _fit_fusion,
             _route, _feedback, _patterns, _synth, _contrib, _evidence_eval, _agreement, _triggers,
             _candidates):
    _mod.register(app)

from callguard.commands import learn as _learn  # noqa: E402  (learning from officer feedback)

_learn.register(app)

from callguard.commands import demo as _demo  # noqa: E402  (the showcase app, `callguard demo`)

_demo.register(app)


if __name__ == "__main__":
    app()
