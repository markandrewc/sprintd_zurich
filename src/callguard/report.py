"""Research outputs from ``runs/experiments/*/summary.json``: the leaderboard and the chart report.

* :func:`leaderboard` -> ``research/leaderboard.md``: every variant of every experiment. Variants whose
  CV@FAR20 operating point keeps the out-of-fold FAR within the 20% cap come first (by CV@FAR20 recall,
  then F1), cap violators after them (by FAR), variants without CV@FAR20 last; AUC is a column, not the
  sort key (review rules flag calls independent of the threshold, so AUC can rank a variant high that no
  threshold makes usable). Plus CI, FAR floor, miss rate, review recall, cost, commit, ORACLE/DEGRADED.
* :func:`build_report` -> ``research/report/report.md`` + PNG charts per experiment: flag F1 / FAR /
  miss with 95% CI error bars, cost vs F1, clean vs noisy, per-level heat map, threshold curves.

Charts use matplotlib's Agg backend (no display) and a validated colorblind-safe categorical order.
Titles state the takeaway; with ~24 dev dialogues most differences are inside the CIs, and the
titles say so instead of crowning a winner.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Sequence

from callguard.config import ROOT

# validated categorical order (dataviz reference palette, light surface)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]  # one hue, light->dark


def experiments_root(runs_dir: Path | None = None) -> Path:
    return (runs_dir or ROOT / "runs") / "experiments"


def load_summaries(names: Sequence[str] | None = None, runs_dir: Path | None = None) -> list[dict[str, Any]]:
    root = experiments_root(runs_dir)
    paths = [root / n / "summary.json" for n in names] if names else sorted(root.glob("*/summary.json"))
    out = []
    for p in paths:
        if p.exists():
            s = json.loads(p.read_text())
            s["_path"] = str(p)
            out.append(s)
    return out


# --------------------------------------------------------------------------------------------
# leaderboard
# --------------------------------------------------------------------------------------------


def _get(block: dict[str, Any] | None, k: str) -> Any:
    return (block or {}).get(k)


def _ci(block: dict[str, Any] | None, k: str) -> tuple[Any, Any]:
    c = ((block or {}).get("ci") or {}).get(k) or {}
    return c.get("lo"), c.get("hi")


def leaderboard_rows(summaries: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for s in summaries:
        for name, v in s["variants"].items():
            primary = v.get("cv") or v["fixed"]
            lo, hi = _ci(primary, "flag_f1")
            auc_f = (v.get("auc") or {}).get("flag") or {}
            auc_a = (v.get("auc") or {}).get("alarm") or {}
            far20 = v.get("cv_far") or {}
            rows.append({
                "auc": auc_f.get("value"), "auc_lo": auc_f.get("lo"), "auc_hi": auc_f.get("hi"),
                "auc_alarm": auc_a.get("value"),
                "far20_f1": far20.get("flag_f1"), "far20_recall": far20.get("flag_recall"),
                "far20_far": far20.get("false_alarm_rate"),
                "balanced_accuracy": _get(primary, "flag_balanced_accuracy"),
                "experiment": s["experiment"], "variant": name, "split": s.get("split"),
                "basis": "cv" if v.get("cv") else "fixed",
                "flag_f1": _get(primary, "flag_f1"), "lo": lo, "hi": hi,
                "fixed_flag_f1": _get(v["fixed"], "flag_f1"),
                "far": _get(primary, "false_alarm_rate"), "miss": _get(primary, "miss_rate"),
                "review_recall": _get(primary, "review_recall"), "alarm_f1": _get(primary, "alarm_f1"),
                "accuracy": _get(primary, "accuracy"), "n": v.get("n_calls"),
                "s_per_call": (v.get("cost") or {}).get("check_compute_s_total_per_call"),
                "wall_s_per_call": (v.get("cost") or {}).get("wall_s_per_call"),
                "llm_calls": (v.get("cost") or {}).get("llm_calls_per_call"),
                "commit": v.get("commit"), "dirty": v.get("dirty"), "oracle": v.get("oracle"),
                "degraded": v.get("degraded"), "refuse_from": (v.get("meta") or {}).get("refuse_from"),
                "created": (v.get("meta") or {}).get("created"),
                "compliant": _compliant(v, s.get("far_cap") or FAR_CAP),
                "far_floor": ((v.get("cap") or {}).get("floor") or {}).get("false_alarm_rate"),
                "cap_folds": (v.get("cap") or {}).get("folds_reachable"),
                "n_folds": (v.get("cap") or {}).get("folds"),
                "warnings": v.get("warnings") or [],
            })
    rows.sort(key=rank_key)
    return rows


FAR_CAP = 0.2


def _compliant(v: dict[str, Any], cap: float) -> bool | None:
    """CV@FAR20 out-of-fold FAR within the cap (None: no CV@FAR20 numbers)."""
    far = (v.get("cv_far") or {}).get("false_alarm_rate")
    return None if far is None else far <= cap


def rank_key(r: dict[str, Any]) -> tuple[Any, ...]:
    """Cap-compliant variants first (CV@FAR20 recall, then F1, then AUC), then cap violators (lowest
    CV@FAR20 FAR first, then recall), then variants without CV@FAR20 (by CV flag F1)."""
    if r["compliant"] is True:
        return (0, -(r["far20_recall"] or 0), -(r["far20_f1"] or 0), -(r["auc"] or 0))
    if r["compliant"] is False:
        return (1, r["far20_far"], -(r["far20_recall"] or 0), -(r["far20_f1"] or 0))
    return (2, -(r["flag_f1"] or 0), 0, 0)


def _p(x: Any) -> str:
    return "-" if x is None else f"{100 * x:.0f}%"


def _f(x: Any, nd: int = 2) -> str:
    return "-" if x is None else f"{x:.{nd}f}"


def render_leaderboard(rows: Sequence[dict[str, Any]], far_cap: float = 0.2) -> str:
    out = ["# Leaderboard", "",
           f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `callguard leaderboard` from "
           "runs/experiments/*/summary.json. **Ranking**: variants whose CV@FAR20 operating point stays within "
           f"the {far_cap:.0%} false-alarm cap out-of-fold come first, by CV@FAR20 flag recall, then F1; then "
           "the cap violators (lowest FAR first); then variants without CV@FAR20. CV@FAR20 = threshold chosen "
           "on the other dev folds for max recall with FAR <= 20% (lowest FAR if no threshold meets it). "
           "*FAR floor* = FAR at threshold 1.0 (calls the review rules flag on their own: uncertainty "
           "escalation, \"undetermined\" verdicts, review band); above the cap no threshold can meet it. "
           "*cap folds* = training folds where some threshold met the cap (the rest fell back). flag AUC (ROC "
           "AUC of the call score, 0.5 = chance) is shown but is not the sort key: it is not "
           "decision-consistent, the review rules flag calls the score ranks low. Why not flag F1: on dev ~54% "
           "of calls are flaggable, so flag-everything already reaches flag F1 ~0.70. CV flag F1 / FAR / miss / "
           "bal. acc = max-F1 CV threshold. Brackets: 95% bootstrap CI over twin groups/dialogues; overlapping "
           f"CIs = no detectable difference. FAR above the {far_cap:.0%} cap is marked (!). ORACLE rows read "
           "the reference scripts and are never submission candidates; DEGRADED rows had failed checks; WARN "
           "rows have provenance warnings (see the experiment's summary.md).", ""]
    head = ["#", "experiment / variant", "split", "n", "CV@FAR20 R / F1 / FAR", "cap", "FAR floor",
            "cap folds", "flag AUC [95% CI]", "alarm AUC", "CV flag F1 [95% CI]", "FAR", "miss", "bal. acc",
            "review recall", "alarm F1", "acc", "check s/call", "LLM calls/call", "commit", "tags"]
    out += ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    for i, r in enumerate(rows, 1):
        auc = _f(r["auc"]) + (f" [{_f(r['auc_lo'])}, {_f(r['auc_hi'])}]" if r["auc_lo"] is not None else "")
        far20 = "-" if r["far20_f1"] is None and r["far20_recall"] is None else \
            f"{_p(r['far20_recall'])} / {_f(r['far20_f1'])} / {_p(r['far20_far'])}" + \
            (" (!)" if r["far20_far"] is not None and r["far20_far"] > far_cap else "")
        cap = {True: "ok", False: "**over**", None: "-"}[r.get("compliant")]
        floor = _p(r.get("far_floor")) + (" (!)" if (r.get("far_floor") or 0) > far_cap else "")
        cap_folds = "-" if r.get("cap_folds") is None else f"{r['cap_folds']}/{r.get('n_folds')}"
        f1 = _f(r["flag_f1"]) + (f" [{_f(r['lo'])}, {_f(r['hi'])}]" if r["lo"] is not None else "")
        if r["basis"] == "fixed":
            f1 += " (fixed)"
        tags = [t for t, on in (("ORACLE", r["oracle"]), ("DEGRADED", r["degraded"])) if on]
        if r["refuse_from"]:
            tags.append(f"re-fusion of {r['refuse_from']}")
        if r.get("warnings"):
            tags.append("WARN")
        far = _p(r["far"]) + (" (!)" if r["far"] is not None and r["far"] > far_cap else "")
        out.append("| " + " | ".join(str(c) for c in [
            i, f"{r['experiment']} / **{r['variant']}**", r["split"], r["n"], far20, cap, floor, cap_folds,
            auc, _f(r["auc_alarm"]), f1, far, _p(r["miss"]), _f(r["balanced_accuracy"]), _p(r["review_recall"]), _f(r["alarm_f1"]), _p(r["accuracy"]), _f(r["s_per_call"], 1),
            _f(r["llm_calls"], 1), (r["commit"] or "-") + ("*" if r["dirty"] else ""), ", ".join(tags)]) + " |")
    if not rows:
        out.append("\nNo experiments yet: `callguard experiment experiments/<name>.yaml`.")
    out += ["", "`*` = uncommitted changes in the tree when the variant ran."]
    return "\n".join(out) + "\n"


def leaderboard(out: Path | None = None, runs_dir: Path | None = None) -> tuple[Path, list[dict[str, Any]]]:
    rows = leaderboard_rows(load_summaries(runs_dir=runs_dir))
    out = out or ROOT / "research" / "leaderboard.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_leaderboard(rows))
    return out, rows


# --------------------------------------------------------------------------------------------
# charts
# --------------------------------------------------------------------------------------------


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
        "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 9, "axes.titlesize": 10,
        "axes.titleweight": "bold", "axes.titlelocation": "left", "figure.titleweight": "bold",
        "figure.titlesize": 11, "legend.frameon": False,
    })
    return plt


def _label(name: str, v: dict[str, Any]) -> str:
    tags = [t for t, on in (("ORACLE", v.get("oracle")), ("DEGRADED", v.get("degraded"))) if on]
    return name + (f"  [{', '.join(tags)}]" if tags else "")


def _primary(v: dict[str, Any]) -> dict[str, Any]:
    return v.get("cv") or v["fixed"]


def _ci_err(block: dict[str, Any], k: str) -> tuple[float, float, float]:
    val = block.get(k)
    lo, hi = _ci(block, k)
    if val is None:
        return float("nan"), 0.0, 0.0
    return val, max(0.0, val - (lo if lo is not None else val)), max(0.0, (hi if hi is not None else val) - val)


def _overlap_note(V: dict[str, Any], k: str = "flag_f1") -> str:
    """Takeaway for the F1 chart: the best variant, and whether its lead is beyond the CI of the rest."""
    scored = [(n, _primary(v)) for n, v in V.items() if _primary(v).get(k) is not None]
    if not scored:
        return "no scored variants"
    best_n, best = max(scored, key=lambda x: x[1][k])
    lo_best = _ci(best, k)[0]
    rivals = [n for n, b in scored if n != best_n and (_ci(b, k)[1] or 0) >= (lo_best or 0)]
    if not rivals:
        return f"{best_n} leads ({best[k]:.2f}), CIs do not overlap"
    return f"{best_n} highest ({best[k]:.2f}), but CIs overlap with {len(rivals)} other(s): no clear winner at this n"


def chart_metrics(s: dict[str, Any], out: Path) -> Path:
    """Three small multiples (flag F1, FAR, miss), horizontal bars with 95% CI whiskers."""
    plt = _plt()
    V = s["variants"]
    names = list(V)
    basis = "CV" if any(v.get("cv") for v in V.values()) else "fixed threshold"
    fig, axes = plt.subplots(1, 3, figsize=(11, 0.45 * len(names) + 1.8), sharey=True)
    for ax, (k, title, pct) in zip(axes, (("flag_f1", "flag F1 (higher is better)", False),
                                          ("false_alarm_rate", "false-alarm rate (lower is better)", True),
                                          ("miss_rate", "miss rate (lower is better)", True))):
        vals = [_ci_err(_primary(V[n]), k) for n in names]
        y = list(range(len(names)))
        ax.barh(y, [v[0] for v in vals], height=0.6, color=SERIES[0], edgecolor=SURFACE, linewidth=2,
                hatch=None)
        for i, n in enumerate(names):  # ORACLE bars get a texture so the label is not the only cue
            if V[n].get("oracle"):
                ax.barh(i, vals[i][0], height=0.6, color="none", edgecolor=SURFACE, hatch="//", linewidth=0)
        ax.errorbar([v[0] for v in vals], y, xerr=[[v[1] for v in vals], [v[2] for v in vals]], fmt="none",
                    ecolor=INK, elinewidth=1.2, capsize=3)
        for i, v in enumerate(vals):  # value just past the upper whisker, in ink (never on the bar)
            if v[0] == v[0]:
                end = v[0] + v[2]
                ax.text(end + 0.02, i, f"{100 * v[0]:.0f}%" if pct else f"{v[0]:.2f}", va="center",
                        ha="left", color=INK, fontsize=8)
        ax.set_xlim(0, 1.17)  # room for the value right of a whisker that reaches 1
        ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_title(title, fontsize=9)
        ax.grid(axis="y", visible=False)
        if pct:
            ax.xaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
        if k == "false_alarm_rate":
            ax.axvline(0.2, color=INK2, linestyle="--", linewidth=1)
            ax.set_title("false-alarm rate (lower better; -- cap 20%)", fontsize=9)
    axes[0].set_yticks(range(len(names)), [_label(n, V[n]) for n in names])
    axes[0].invert_yaxis()
    fig.suptitle(f"{s['experiment']}: {_overlap_note(V)}", x=0.01, ha="left")
    fig.text(0.01, 0.005, f"{basis} predictions, split {s['split']}; whiskers = 95% bootstrap CI over dialogues",
             color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    p = out / "metrics.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def chart_auc(s: dict[str, Any], out: Path) -> Path | None:
    """Threshold-free discrimination: flag AUC and alarm-vs-rest AUC with 95% CIs, chance line at 0.5."""
    plt = _plt()
    V = s["variants"]
    names = [n for n in V if ((V[n].get("auc") or {}).get("flag") or {}).get("value") is not None]
    if not names:
        return None
    fig, axes = plt.subplots(1, 2, figsize=(10, 0.45 * len(names) + 1.8), sharey=True)
    for ax, (t, title) in zip(axes, (("flag", "flag AUC (alarm|review vs no_alert)"),
                                     ("alarm", "alarm-vs-rest AUC"))):
        vals = []
        for n in names:
            a = (V[n].get("auc") or {}).get(t) or {}
            v = a.get("value")
            vals.append((float("nan"), 0, 0) if v is None else
                        (v, max(0.0, v - (a.get("lo") if a.get("lo") is not None else v)),
                         max(0.0, (a.get("hi") if a.get("hi") is not None else v) - v)))
        y = list(range(len(names)))
        ax.barh(y, [v[0] for v in vals], height=0.6, color=SERIES[0], edgecolor=SURFACE, linewidth=2)
        for i, n in enumerate(names):
            if V[n].get("oracle"):
                ax.barh(i, vals[i][0], height=0.6, color="none", edgecolor=SURFACE, hatch="//", linewidth=0)
        ax.errorbar([v[0] for v in vals], y, xerr=[[v[1] for v in vals], [v[2] for v in vals]], fmt="none",
                    ecolor=INK, elinewidth=1.2, capsize=3)
        for i, v in enumerate(vals):
            if v[0] == v[0]:
                ax.text(v[0] + v[2] + 0.02, i, f"{v[0]:.2f}", va="center", ha="left", color=INK, fontsize=8)
        ax.axvline(0.5, color=INK2, linestyle="--", linewidth=1)
        ax.set_xlim(0, 1.17)
        ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_title(f"{title}; -- chance", fontsize=9)
        ax.grid(axis="y", visible=False)
    axes[0].set_yticks(range(len(names)), [_label(n, V[n]) for n in names])
    axes[0].invert_yaxis()
    best = max(names, key=lambda n: V[n]["auc"]["flag"]["value"])
    lo = V[best]["auc"]["flag"].get("lo")
    verdict = ("its CI stays above chance" if lo is not None and lo > 0.5 else "its CI still reaches chance (0.5)")
    fig.suptitle(f"{s['experiment']}: best flag AUC {best} {V[best]['auc']['flag']['value']:.2f}; {verdict}",
                 x=0.01, ha="left")
    fig.text(0.01, 0.005, "ROC AUC of the call score; whiskers = 95% bootstrap CI over twin groups/dialogues",
             color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    p = out / "auc.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def chart_cost(s: dict[str, Any], out: Path) -> Path | None:
    plt = _plt()
    V = s["variants"]
    pts = []
    for n, v in V.items():
        c = v.get("cost") or {}
        x = c.get("check_compute_s_total_per_call")
        if (v.get("meta") or {}).get("refuse_from"):
            continue  # re-fusions cost what their source cost: same point, hidden label
        if x is None:
            continue
        f1, lo, hi = _ci_err(_primary(v), "flag_f1")
        pts.append((n, x + (c.get("asr_compute_s_per_call") or 0), f1, lo, hi, c.get("llm_calls_per_call")))
    if not pts:
        return None
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.errorbar([p[1] for p in pts], [p[2] for p in pts], yerr=[[p[3] for p in pts], [p[4] for p in pts]],
                fmt="o", color=SERIES[0], ecolor=INK2, elinewidth=1, capsize=3, markersize=8,
                markeredgecolor=SURFACE, markeredgewidth=2)
    for n, x, y, *_ in pts:
        if y == y:
            ax.annotate(n, (x, y), xytext=(6, 4), textcoords="offset points", fontsize=8, color=INK)
    ax.set_xlabel("compute seconds per call (checks + ASR, as computed; cache hits keep their cost)")
    ax.set_ylabel("flag F1 (CV)")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(left=0)
    cheapest = min(pts, key=lambda p: p[1])
    best = max(pts, key=lambda p: p[2] if p[2] == p[2] else -1)
    title = (f"{best[0]} scores best; it is also the cheapest" if best[0] == cheapest[0] else
             f"{best[0]} scores best at {best[1]:.1f}s/call; cheapest is {cheapest[0]} ({cheapest[1]:.1f}s)")
    ax.set_title(f"{s['experiment']}: {title}")
    fig.tight_layout()
    p = out / "cost_vs_f1.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def chart_noise(s: dict[str, Any], out: Path) -> Path | None:
    plt = _plt()
    V = s["variants"]
    names = [n for n in V if (_primary(V[n]).get("by_noise") or {})]
    if not names:
        return None
    fig, ax = plt.subplots(figsize=(7.5, 0.5 * len(names) + 1.6))
    h = 0.36
    gaps = []
    for j, (g, color) in enumerate((("clean", SERIES[0]), ("noisy", SERIES[1]))):
        vals = [((_primary(V[n]).get("by_noise") or {}).get(g) or {}).get("flag_f1") for n in names]
        ys = [i + (j - 0.5) * (h + 0.04) for i in range(len(names))]
        ax.barh(ys, [v if v is not None else 0 for v in vals], height=h, color=color, label=g,
                edgecolor=SURFACE, linewidth=2)
        for y, v in zip(ys, vals):
            ax.text((v or 0) + 0.01, y, "-" if v is None else f"{v:.2f}", va="center", fontsize=7.5, color=INK2)
    for n in names:
        bn = _primary(V[n]).get("by_noise") or {}
        c, z = (bn.get("clean") or {}).get("flag_f1"), (bn.get("noisy") or {}).get("flag_f1")
        if c is not None and z is not None:
            gaps.append(c - z)
    ax.set_yticks(range(len(names)), [_label(n, V[n]) for n in names])
    ax.invert_yaxis()
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("flag F1 (CV)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right", ncols=2)
    mean_gap = sum(gaps) / len(gaps) if gaps else 0
    ax.set_title(f"{s['experiment']}: clean minus noisy flag F1 = {mean_gap:+.2f} on average"
                 if gaps else f"{s['experiment']}: clean vs noisy")
    fig.tight_layout()
    p = out / "clean_vs_noisy.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def chart_levels(s: dict[str, Any], out: Path) -> Path | None:
    plt = _plt()
    from matplotlib.colors import LinearSegmentedColormap

    V = s["variants"]
    levels = sorted({lv for v in V.values() for lv in (_primary(v).get("by_level") or {})})
    if not levels:
        return None
    names = list(V)
    import numpy as np
    grid = np.full((len(names), len(levels)), np.nan)
    for i, n in enumerate(names):
        for j, lv in enumerate(levels):
            m = (_primary(V[n]).get("by_level") or {}).get(lv) or {}
            # Stufe 3 has only review cases: flag F1 is defined, FAR is not
            if m.get("flag_f1") is not None:
                grid[i, j] = m["flag_f1"]
    cmap = LinearSegmentedColormap.from_list("seq", SEQ).with_extremes(bad=GRID)
    fig, ax = plt.subplots(figsize=(1.4 * len(levels) + 3.5, 0.45 * len(names) + 1.6))
    im = ax.imshow(np.ma.masked_invalid(grid), cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(len(names)):
        for j in range(len(levels)):
            v = grid[i, j]
            ax.text(j, i, "-" if v != v else f"{v:.2f}", ha="center", va="center", fontsize=8,
                    color=SURFACE if v == v and v > 0.55 else INK)
    ax.set_xticks(range(len(levels)), levels)
    ax.set_yticks(range(len(names)), [_label(n, V[n]) for n in names])
    ax.grid(False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.colorbar(im, ax=ax, fraction=0.04, pad=0.02, label="flag F1 (CV)")
    col_mean = np.nanmean(grid, axis=0) if np.isfinite(grid).any() else []
    worst = levels[int(np.nanargmin(col_mean))] if len(col_mean) and np.isfinite(col_mean).any() else None
    ax.set_title(f"{s['experiment']}: {worst} is the hardest level" if worst else s["experiment"])
    fig.tight_layout()
    p = out / "levels.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


def chart_thresholds(s: dict[str, Any], out: Path) -> Path | None:
    plt = _plt()
    V = s["variants"]
    curves = {n: v["sweep"] for n, v in V.items() if v.get("sweep") and not (v.get("meta") or {}).get("refuse_from")}
    if not curves:
        curves = {n: v["sweep"] for n, v in V.items() if v.get("sweep")}
    if not curves:
        return None
    # at most 8 series (fixed categorical order, never cycled): the best by CV flag F1
    order = sorted(curves, key=lambda n: -(_primary(V[n]).get("flag_f1") or 0))[:8]
    order = [n for n in V if n in order]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), sharex=True)
    for idx, n in enumerate(order):
        sw = curves[n]
        t = [x["threshold"] for x in sw]
        c = SERIES[idx]
        axes[0].plot(t, [x["flag_f1"] if x["flag_f1"] is not None else float("nan") for x in sw], color=c,
                     linewidth=2, label=_label(n, V[n]))
        axes[1].plot(t, [x["false_alarm_rate"] if x["false_alarm_rate"] is not None else float("nan") for x in sw],
                     color=c, linewidth=2, label=_label(n, V[n]))
        sug = (V[n].get("suggestion") or {}).get("threshold")
        if sug is not None:
            y = next((x["flag_f1"] for x in sw if abs(x["threshold"] - sug) < 1e-9), None)
            if y is not None:
                axes[0].plot([sug], [y], "o", color=c, markersize=8, markeredgecolor=SURFACE, markeredgewidth=2)
    axes[0].set_ylabel("flag F1 (all selected calls, in-sample)")
    axes[1].set_ylabel("false-alarm rate")
    axes[1].axhline(0.2, color=INK2, linestyle="--", linewidth=1)
    axes[1].yaxis.set_major_formatter(lambda x, _: f"{100 * x:.0f}%")
    for ax in axes:
        ax.set_xlabel("fusion threshold")
        ax.set_ylim(0, 1.05)
    axes[1].legend(loc="upper right", fontsize=7.5)
    best = order[0] if order else ""
    sug = (V.get(best, {}).get("suggestion") or {}).get("threshold")
    fig.suptitle(f"{s['experiment']}: F1 vs threshold (dot = suggested); "
                 f"{best} (best CV F1) suggests {sug:.2f}" if sug is not None else f"{s['experiment']}: threshold curves",
                 x=0.01, ha="left")
    fig.text(0.01, 0.005, "In-sample sweep: optimistic. The CV numbers choose the threshold on other folds.",
             color=INK2, fontsize=7.5)
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    p = out / "thresholds.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return p


# --------------------------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------------------------


def build_report(names: Sequence[str] | None = None, out: Path | None = None,
                 runs_dir: Path | None = None) -> Path:
    out = out or ROOT / "research" / "report"
    out.mkdir(parents=True, exist_ok=True)
    summaries = load_summaries(names, runs_dir)
    md = ["# callguard research report", "",
          f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `callguard report` from "
          f"{len(summaries)} experiment(s). Primary numbers are out-of-fold (CV) on the dev split; whiskers "
          "and brackets are 95% bootstrap CIs over dialogues (clean+noisy resampled together). With ~24 dev "
          "dialogues, differences inside the CIs are noise.", "",
          "AUC is not decision-consistent: it ranks the fused call score, but review rules (uncertainty "
          "escalation, \"undetermined\" verdicts, review band) flag calls whatever the threshold, so for many "
          "variants no threshold reaches FAR <= 20% (see each variant's FAR floor). The top variants are "
          "ranked by cap compliance and CV@FAR20 recall, not by AUC.", ""]
    lb_rows = leaderboard_rows(summaries)
    if lb_rows:
        md += ["## Top variants", "", *render_leaderboard(lb_rows[:10]).splitlines()[4:], ""]
    for s in summaries:
        d = out / s["experiment"]
        d.mkdir(parents=True, exist_ok=True)
        md += [f"## {s['experiment']}", ""]
        if s.get("description"):
            md += [s["description"], ""]
        md += [f"RQ: {', '.join(s.get('rq') or []) or '-'} · split {s['split']} · baseline `{s['compare_to']}` · "
               f"details: `{Path(s['_path']).parent.relative_to(ROOT) if Path(s['_path']).is_relative_to(ROOT) else s['_path']}/summary.md`", ""]
        b = s.get("baselines") or {}
        if b.get("flag_all"):
            md += [f"Floor on these calls: flag-all flag F1 {_f(b['flag_all']['flag_f1'])} (FAR 100%), "
                   f"flag-none 0.00, constant score AUC 0.50.", ""]
        for fn in (chart_auc, chart_metrics, chart_cost, chart_noise, chart_levels, chart_thresholds):
            try:
                p = fn(s, d)
            except Exception as e:  # one broken chart must not lose the report
                md += [f"_({fn.__name__} failed: {type(e).__name__}: {e})_", ""]
                continue
            if p is not None:
                md += [f"![{fn.__name__}]({p.relative_to(out)})", ""]
        for c in s.get("comparisons") or []:
            block = c.get("cv") or c["fixed"]
            d1 = block["paired"]["flag_f1"]
            far = block["paired"]["false_alarm_rate"]
            verdict = ("**real difference**" if d1.get("real") else "no detectable difference")
            pa = ((c.get("fixed") or {}).get("auc") or {}).get("flag") or {}
            auc_txt = (f"flag AUC {_sg(pa.get('diff'))} [{_sg(pa.get('lo'))}, {_sg(pa.get('hi'))}]"
                       f"{' (real)' if pa.get('real') else ''}; ") if pa.get("diff") is not None else ""
            md.append(f"- `{c['b']}` vs `{c['a']}`: {auc_txt}flag F1 {_sg(d1.get('diff'))} "
                      f"[{_sg(d1.get('lo'))}, {_sg(d1.get('hi'))}] ({verdict}); FAR {_sg(far.get('diff'), True)}; "
                      f"McNemar p={block['mcnemar_flag']['p']}; {len(block['flips'])} calls flip")
        md.append("")
    (out / "report.md").write_text("\n".join(md) + "\n")
    return out / "report.md"


def _sg(x: Any, pct: bool = False) -> str:
    if x is None:
        return "-"
    return f"{100 * x:+.0f}pp" if pct else f"{x:+.2f}"
