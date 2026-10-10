"""«Qualität» of the demo: false-alarm rate and miss rate with 95 % intervals, per dataset, never pooled.

* Fallanrufe (dev): the out-of-fold cross-validated numbers of the chosen Prüfmodus (the same
  :class:`callguard.ui.modes.ModeMetrics` the workload panel uses; ``runs/`` or the committed snapshot).
* test50 (extern): the teammate's external held-out set, ``runs/test50/experiments/test50/<variant>/rows.json``
  at the dev-frozen threshold (``fixed`` rows), bootstrap over twin groups / dialogues
  (:func:`callguard.stats.bootstrap_ci`), Wilson where the bootstrap collapses (0 of n). Never used for tuning.

"Flagged" = Alarm or Prüfen (a human listens). Pure functions + one Altair chart; no Streamlit.
"""

from __future__ import annotations

import json
import os
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from callguard import stats
from callguard.ui.modes import ModeMetrics, Rate

TEST50_ENV = "CALLGUARD_DEMO_TEST50"  # variant to show; default: the first of TEST50_PREFERRED that exists
TEST50_PREFERRED = ("champion_v3", "champion")
TEST50_NOTE = "externer Testsatz, nie zum Tunen verwendet"
FLAG = ("alarm", "review")
ACCENT, INK, INK_2, GRID = "#2a78d6", "#1b1f24", "#5f6670", "#e1e0d9"


@dataclass(frozen=True)
class Rates:
    key: str  # "dev" / "test50"
    title: str
    n_calls: int
    far: Rate  # harmless calls flagged / harmless calls
    miss: Rate  # flaggable calls not flagged / flaggable calls
    source: str
    note: str = ""


def miss_from_recall(recall: Rate) -> Rate:
    return Rate(round(1.0 - recall.value, 6), round(1.0 - recall.hi, 6), round(1.0 - recall.lo, 6),
                recall.n - recall.k, recall.n, recall.method)


def dev_rates(m: ModeMetrics, mode_label: str = "") -> Rates:
    return Rates(key="dev", title="Fallanrufe (Dev)", n_calls=m.n_calls, far=m.far, miss=miss_from_recall(m.recall),
                 source=m.source, note=("Prüfmodus «" + mode_label + "», " if mode_label else "")
                 + "Kreuzvalidierung: jede Schwelle auf den anderen Dialogen gewählt")


def rates_from_rows(rows: Sequence[dict[str, Any]], *, key: str, title: str, source: str, note: str = "",
                    n_boot: int = 2000, seed: int = 13) -> Rates | None:
    lab = stats.labeled(rows)
    if not lab:
        return None
    fp = sum(r["expected"] not in FLAG and r["predicted"] in FLAG for r in lab)
    tn = sum(r["expected"] not in FLAG and r["predicted"] not in FLAG for r in lab)
    fn = sum(r["expected"] in FLAG and r["predicted"] not in FLAG for r in lab)
    tp = sum(r["expected"] in FLAG and r["predicted"] in FLAG for r in lab)
    ci = stats.bootstrap_ci(lab, n_boot=n_boot, seed=seed, metrics=["false_alarm_rate", "miss_rate"])
    far = Rate.build(fp / (fp + tn) if fp + tn else 0.0, ci.get("false_alarm_rate"), fp, fp + tn)
    miss = Rate.build(fn / (fn + tp) if fn + tp else 0.0, ci.get("miss_rate"), fn, fn + tp)
    return Rates(key=key, title=title, n_calls=len(lab), far=far, miss=miss, source=source, note=note)


def test50_dir(runs_root: str | Path) -> Path:
    return Path(runs_root) / "test50" / "experiments" / "test50"


def find_test50(runs_root: str | Path, variant: str | None = None) -> tuple[str, Path] | None:
    """(variant, rows.json) of the test50 run to show: ``variant`` / $CALLGUARD_DEMO_TEST50, else the
    first of :data:`TEST50_PREFERRED` that exists. None when no test50 results are on this machine."""
    base = test50_dir(runs_root)
    wanted = variant or os.environ.get(TEST50_ENV)
    for v in ([wanted] if wanted else list(TEST50_PREFERRED)):
        f = base / v / "rows.json"
        if f.is_file():
            return v, f
    return None


def test50_rates(runs_root: str | Path, variant: str | None = None, n_boot: int = 2000) -> Rates | None:
    found = find_test50(runs_root, variant)
    if found is None:
        return None
    v, f = found
    try:
        data = json.loads(f.read_text())
    except Exception:
        return None
    rows = data.get("fixed") or []
    meta: dict[str, Any] = {}
    mf = f.parent / "meta.json"
    if mf.is_file():
        try:
            meta = json.loads(mf.read_text())
        except Exception:
            meta = {}
    desc = str(meta.get("description") or "")
    return rates_from_rows(rows, key="test50", title="Externer Testsatz test50", n_boot=n_boot,
                           source=f"runs/test50/experiments/test50/{v}" + (f" ({desc})" if desc else ""),
                           note=f"{TEST50_NOTE}; feste Schwelle aus den Dev-Daten")


def pct(x: float | None) -> str:
    return "–" if x is None else f"{100 * x:.0f} %"


def rate_text(r: Rate) -> str:
    """«12 % (95 %-KI 4–25 %, 3 von 25)»."""
    return f"{pct(r.value)} (95 %-KI {100 * r.lo:.0f}–{100 * r.hi:.0f} %, {r.k} von {r.n})"


def chart_rows(sets: Sequence[Rates]) -> list[dict[str, Any]]:
    out = []
    for s in sets:
        for name, r, what in (("Fehlalarme", s.far, "harmlose Anrufe markiert"),
                              ("Verpasst", s.miss, "auffällige Anrufe durchgelassen")):
            out.append({"Datensatz": f"{s.title} · {s.n_calls} Anrufe", "Kennzahl": name, "Wert": r.value,
                        "von": r.lo, "bis": r.hi, "k": r.k, "n": r.n, "was": what,
                        "Text": f"{100 * r.value:.0f} %"})
    return out


def chart(sets: Sequence[Rates]) -> Any:
    """Dot (point value) + 95 % interval per rate; one panel per dataset (side by side, never pooled), shared
    0–100 % axis so the panels compare honestly. One hue: the rows already name the measure."""
    import altair as alt
    import pandas as pd

    df = pd.DataFrame(chart_rows(sets))
    x = alt.X("Wert:Q", title=None, scale=alt.Scale(domain=[0, 1]),
              axis=alt.Axis(format="%", values=[0, 0.25, 0.5, 0.75, 1], grid=True, gridColor=GRID, domain=False,
                            ticks=False, labelColor=INK_2))
    y = alt.Y("Kennzahl:N", title=None, sort=["Fehlalarme", "Verpasst"],
              axis=alt.Axis(labelColor=INK, labelFontSize=13, ticks=False, domain=False, labelPadding=8))
    tip = [alt.Tooltip("Datensatz:N"), alt.Tooltip("Kennzahl:N"), alt.Tooltip("was:N", title="d.h."),
           alt.Tooltip("Wert:Q", format=".0%", title="Wert"), alt.Tooltip("von:Q", format=".0%", title="95 %-KI von"),
           alt.Tooltip("bis:Q", format=".0%", title="95 %-KI bis"), alt.Tooltip("k:Q", title="Anzahl"),
           alt.Tooltip("n:Q", title="von")]
    base = alt.Chart(df)
    interval = base.mark_rule(strokeWidth=3, strokeCap="round", color="#9ec5f4").encode(
        x=alt.X("von:Q", scale=alt.Scale(domain=[0, 1])), x2="bis:Q", y=y, tooltip=tip)
    dot = base.mark_point(filled=True, size=150, color=ACCENT, stroke="#ffffff", strokeWidth=2, opacity=1).encode(
        x=x, y=y, tooltip=tip)
    label = base.mark_text(align="left", dx=10, dy=-12, fontSize=13, fontWeight=600, color=INK).encode(
        x="Wert:Q", y=y, text="Text:N")
    return (alt.layer(interval, dot, label, data=df)
            .properties(width=300, height=alt.Step(56))
            .facet(column=alt.Column("Datensatz:N", title=None, sort=list(dict.fromkeys(df["Datensatz"])),
                                     header=alt.Header(labelFontSize=14, labelFontWeight=600, labelColor=INK,
                                                       labelAnchor="start", labelPadding=6)))
            .resolve_scale(x="shared")
            .configure_view(stroke=None)
            .configure_axis(labelFont="system-ui", titleFont="system-ui"))
