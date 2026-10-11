"""Frames + Altair charts for the "Entscheidungshilfe" page (``callguard.ui.views.decisions``), built from the
result of :func:`callguard.contrib.analyse` (``runs/contrib/contrib.json``). Pure functions, testable without
Streamlit.

Colour jobs (dataviz method): the forest plot and the waterfall steps carry **status** (real gain / real loss /
noise) -> the fixed status steps good ``#0ca30c`` / critical ``#d03b3b`` plus a recessive gray, always paired with
a shape (triangle up / down / circle) and the German label, because red-green alone fails deuteranopia
(validator: CVD dE 4.1). Level bars of the waterfall and the base condition of the generalisation plot use
categorical slot 1 (blue) as emphasis, the rest gray. The family heat map is sequential (one blue ramp).
"""

from __future__ import annotations

from typing import Any

import altair as alt
import pandas as pd

from callguard import contrib as cb

GOOD, BAD, NOISE = "#0ca30c", "#d03b3b", "#a3a3a3"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
EMPH, MUTED = "#2a78d6", "#8a8984"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

CLASS_GAIN, CLASS_LOSS, CLASS_NOISE = "Gewinn belegt", "Verlust belegt", "Rauschen"
CLASSES = [CLASS_GAIN, CLASS_LOSS, CLASS_NOISE]
CLASS_COLOR = alt.Scale(domain=CLASSES, range=[GOOD, BAD, NOISE])
CLASS_SHAPE = alt.Scale(domain=CLASSES, range=["triangle-up", "triangle-down", "circle"])
METRICS = {"Flag-AUC": "auc", "Fehlalarmquote": "false_alarm_rate", "Verpasst": "miss_rate",
           "Exakter Status": "accuracy", "Prüf-Recall": "review_recall"}
PCT = {"false_alarm_rate", "miss_rate", "accuracy", "review_recall", "flag_f1"}
FAMILY_TEXT = {"trade": "Insiderhandel", "access": "Zugangsdaten", "disclosure": "Auskunft an Dritte",
               "documentation": "Dokumentation", "splitting": "Aufteilen", "numbers": "Zahlen (nie Alarm)"}
STATUS_TEXT = cb.STATUS_LABELS
VERDICT_TEXT = cb.VERDICT_LABELS


def classify(d: dict[str, Any] | None, metric: str) -> str:
    """Gain / loss / noise of one metric delta (B - A): real and better for B = gain."""
    if not d or not d.get("real") or d.get("diff") in (None, 0):
        return CLASS_NOISE
    better_b = (d["diff"] < 0) == (metric in cb.LOWER_IS_BETTER)
    return CLASS_GAIN if better_b else CLASS_LOSS


def gain_sign(metric: str) -> int:
    return -1 if metric in cb.LOWER_IS_BETTER else 1


def fmt_delta(d: dict[str, Any] | None, metric: str) -> str:
    if not d or d.get("diff") is None:
        return "–"
    if metric in PCT:
        s = f"{100 * d['diff']:+.0f} Pkt."
        return s + (f" [{100 * d['lo']:+.0f}, {100 * d['hi']:+.0f}]" if d.get("lo") is not None else "")
    s = f"{d['diff']:+.2f}"
    return s + (f" [{d['lo']:+.2f}, {d['hi']:+.2f}]" if d.get("lo") is not None else "")


def fmt_value(x: Any, metric: str) -> str:
    if x is None:
        return "–"
    return f"{100 * x:.0f}%" if metric in PCT else f"{x:.2f}"


def _scale(metric: str) -> float:
    return 100.0 if metric in PCT else 1.0


# --------------------------------------------------------------------------------------------
# a. forest plot of paired deltas
# --------------------------------------------------------------------------------------------


def forest_frame(result: dict[str, Any], metric: str, factors: list[str] | None = None,
                 show_confounded: bool = True, sort: str = "size") -> pd.DataFrame:
    """One row per paired comparison with data for ``metric``; ``sort`` = size (gain first) | factor."""
    rows = []
    order = 0
    for f in result.get("factors") or []:
        if factors is not None and f["id"] not in factors:
            continue
        for p in f["pairs"]:
            d = (p.get("deltas") or {}).get(metric)
            if not d or d.get("diff") is None:
                continue
            if not show_confounded and p.get("status") == "confounded":
                continue
            k = _scale(metric)
            lab = f"{f.get('short') or f['id']} · {p['label']}" + (" (verzerrt)" if p.get("status") == "confounded" else "")
            rows.append({
                "Vergleich": lab, "Faktor": f["title"], "A": p["a"], "B": p["b"],
                "Wert A": fmt_value(d.get("a"), metric), "Wert B": fmt_value(d.get("b"), metric),
                "Differenz": d["diff"] * k, "von": (d["lo"] if d.get("lo") is not None else d["diff"]) * k,
                "bis": (d["hi"] if d.get("hi") is not None else d["diff"]) * k,
                "Text": fmt_delta(d, metric), "Klasse": classify(d, metric),
                "Status": STATUS_TEXT.get(p.get("status"), p.get("status")), "n": p.get("n_common"),
                "Flips": (p.get("flips") or {}).get("n"), "Urteil": VERDICT_TEXT.get(p.get("verdict"), p.get("verdict")),
                "Gewinn": d["diff"] * gain_sign(metric), "Reihenfolge": order,
            })
            order += 1
    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values("Gewinn" if sort == "size" else "Reihenfolge", ascending=sort != "size",
                            kind="stable").reset_index(drop=True)
    return df


def forest_chart(df: pd.DataFrame, metric: str) -> alt.LayerChart:
    label = next((k for k, v in METRICS.items() if v == metric), metric)
    unit = " (Prozentpunkte)" if metric in PCT else ""
    order = list(df["Vergleich"])
    y = alt.Y("Vergleich:N", sort=order, title=None, axis=alt.Axis(labelLimit=420))
    tip = ["Vergleich:N", "Faktor:N", "A:N", "B:N", "Wert A:N", "Wert B:N",
           alt.Tooltip("Text:N", title="B − A [95%-KI]"), "Klasse:N", "Status:N", "n:Q", "Flips:Q", "Urteil:N"]
    zero = alt.Chart(pd.DataFrame({"x": [0.0]})).mark_rule(color=INK, strokeWidth=1).encode(x="x:Q")
    ci = alt.Chart(df).mark_rule(strokeWidth=2).encode(
        x=alt.X("von:Q", title=f"Differenz B − A: {label}{unit}, mit 95%-Intervall"), x2="bis:Q", y=y,
        color=alt.Color("Klasse:N", scale=CLASS_COLOR, legend=None), tooltip=tip)
    pts = alt.Chart(df).mark_point(filled=True, size=150, stroke="#fcfcfb", strokeWidth=2).encode(
        x="Differenz:Q", y=y,
        color=alt.Color("Klasse:N", scale=CLASS_COLOR, legend=alt.Legend(orient="bottom", title=None)),
        shape=alt.Shape("Klasse:N", scale=CLASS_SHAPE, legend=alt.Legend(orient="bottom", title=None)), tooltip=tip)
    return alt.layer(zero, ci, pts).properties(height=alt.Step(26))


def factor_icon(f: dict[str, Any]) -> str:
    c = (f.get("summary") or {}).get("counts") or {}
    if c.get("gain") and not c.get("loss"):
        return ":material/trending_up:"
    if c.get("loss") and not c.get("gain"):
        return ":material/trending_down:"
    if c.get("gain") or c.get("mixed") or c.get("loss"):
        return ":material/balance:"
    if set(c) <= {"missing"}:
        return ":material/hourglass_empty:"
    return ":material/remove:"


def pairs_table(result: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for f in result.get("factors") or []:
        for p in f["pairs"]:
            d = p.get("deltas") or {}
            md = p.get("meta_diff") or {}
            rows.append({
                "Faktor": f.get("short") or f["id"], "Vergleich": p["label"], "A": p["a"], "B": p["b"],
                "Status": STATUS_TEXT.get(p.get("status"), p.get("status")), "n": p.get("n_common"),
                "Δ Flag-AUC": fmt_delta(d.get("auc"), "auc"),
                "Δ Fehlalarme": fmt_delta(d.get("false_alarm_rate"), "false_alarm_rate"),
                "Δ Verpasst": fmt_delta(d.get("miss_rate"), "miss_rate"),
                "Δ Exakt": fmt_delta(d.get("accuracy"), "accuracy"),
                "Δ Prüf-Recall": fmt_delta(d.get("review_recall"), "review_recall"),
                "Flips": (p.get("flips") or {}).get("n"), "Urteil": VERDICT_TEXT.get(p["verdict"], p["verdict"]),
                "Was sonst anders ist": " ".join(x for x in (p.get("differs"), p.get("note")) if x),
                "meta.json-Diff": "; ".join(f"{k}: {v[0]} → {v[1]}" for k, v in md.items()),
                "Basis": p.get("basis"),
            })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------------------------
# path waterfall
# --------------------------------------------------------------------------------------------


def waterfall_frame(result: dict[str, Any], metric: str) -> pd.DataFrame:
    path = result.get("path") or {}
    steps = [s for s in path.get("steps") or [] if (s.get("deltas") or {}).get(metric)]
    if not steps:
        return pd.DataFrame()
    k = _scale(metric)
    floor = 0.5 * k if metric == "auc" else 0.0
    rows = []
    first, last = steps[0]["deltas"][metric], steps[-1]["deltas"][metric]
    rows.append({"Schritt": path.get("start_label") or f"Start: {steps[0]['a']}", "von": floor, "bis": first["a"] * k, "Klasse": "Stand",
                 "Text": fmt_value(first["a"], metric), "Detail": steps[0]["a"]})
    for s in steps:
        d = s["deltas"][metric]
        rows.append({"Schritt": s["label"], "von": d["a"] * k, "bis": d["b"] * k, "Klasse": classify(d, metric),
                     "Text": fmt_delta(d, metric), "Detail": f"{s['a']} → {s['b']} · {STATUS_TEXT.get(s.get('status'), '')}"})
    rows.append({"Schritt": path.get("end_label") or f"Ende: {steps[-1]['b']}", "von": floor, "bis": last["b"] * k, "Klasse": "Stand",
                 "Text": fmt_value(last["b"], metric), "Detail": steps[-1]["b"]})
    df = pd.DataFrame(rows)
    df["oben"] = df[["von", "bis"]].max(axis=1)
    return df


def waterfall_chart(df: pd.DataFrame, metric: str) -> alt.LayerChart:
    label = next((k for k, v in METRICS.items() if v == metric), metric)
    order = list(df["Schritt"])
    lo = 0.5 if metric == "auc" else 0.0
    hi = 1.0 * _scale(metric)
    color = alt.Color("Klasse:N", scale=alt.Scale(domain=["Stand", *CLASSES], range=[EMPH, GOOD, BAD, NOISE]),
                      legend=alt.Legend(orient="bottom", title=None))
    x = alt.X("Schritt:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelLimit=180))
    tip = ["Schritt:N", "Detail:N", alt.Tooltip("Text:N", title="Wert / Differenz [95%-KI]"), "Klasse:N"]
    bars = alt.Chart(df).mark_bar(size=24, cornerRadius=4).encode(
        x=x, y=alt.Y("von:Q", title=label + (" (%)" if metric in PCT else ""),
                     scale=alt.Scale(domain=[lo * _scale(metric), hi])),
        y2="bis:Q", color=color, tooltip=tip)
    text = alt.Chart(df).mark_text(dy=-8, fontSize=11, color=INK2).encode(x=x, y="oben:Q", text="Text:N")
    return alt.layer(bars, text).properties(height=300)


# --------------------------------------------------------------------------------------------
# b. generalisation
# --------------------------------------------------------------------------------------------


def generalisation_frame(result: dict[str, Any]) -> pd.DataFrame:
    V = result.get("variants") or {}
    rows = []
    for tr in result.get("generalisation") or []:
        for i, e in enumerate(tr["entries"]):
            r = V.get(e["ref"])
            if r is None or (r.get("auc") or {}).get("value") is None:
                continue
            a, m = r["auc"], r.get("metrics") or {}
            vs = e.get("vs_base")
            if vs is None:
                vs_txt = "Basis"
            elif not vs.get("paired"):
                vs_txt = "andere Anrufe: nur nebeneinander"
            else:
                vs_txt = (f"Δ AUC {fmt_delta(vs['deltas']['auc'], 'auc')} · "
                          f"{VERDICT_TEXT.get(vs['verdict'], vs['verdict'])} · {vs['flips']} Flips")
            rows.append({
                "Zeile": f"{tr['title']} · {e['label']}", "Spur": tr["title"], "Bedingung": e["label"],
                "Variante": e["ref"], "Rolle": "Basis (Dev, abgestimmt)" if i == 0 else "andere Bedingung",
                "AUC": a["value"], "von": a.get("lo") if a.get("lo") is not None else a["value"],
                "bis": a.get("hi") if a.get("hi") is not None else a["value"], "n": r.get("n_calls"),
                "AUC [95%-KI]": f"{a['value']:.2f} [{a['lo']:.2f}, {a['hi']:.2f}]" if a.get("lo") is not None else f"{a['value']:.2f}",
                "Fehlalarme": (m.get("false_alarm_rate") or {}).get("value"),
                "Verpasst": (m.get("miss_rate") or {}).get("value"), "Exakt": (m.get("accuracy") or {}).get("value"),
                "gegen Basis": vs_txt, "Hinweis": e.get("note") or "",
            })
    return pd.DataFrame(rows)


def generalisation_chart(df: pd.DataFrame) -> alt.LayerChart:
    order = list(df["Zeile"])
    y = alt.Y("Zeile:N", sort=order, title=None, axis=alt.Axis(labelLimit=420))
    color = alt.Color("Rolle:N", scale=alt.Scale(domain=["Basis (Dev, abgestimmt)", "andere Bedingung"],
                                                 range=[EMPH, MUTED]), legend=alt.Legend(orient="bottom", title=None))
    tip = ["Spur:N", "Bedingung:N", "Variante:N", "AUC [95%-KI]:N", "n:Q",
           alt.Tooltip("Fehlalarme:Q", format=".0%"), alt.Tooltip("Verpasst:Q", format=".0%"), "gegen Basis:N"]
    chance = alt.Chart(pd.DataFrame({"x": [0.5]})).mark_rule(color=GRID, strokeWidth=1).encode(x="x:Q")
    ci = alt.Chart(df).mark_rule(strokeWidth=2).encode(
        x=alt.X("von:Q", scale=alt.Scale(domain=[0.4, 1.0]), title="Flag-AUC mit 95%-Intervall (0.5 = Zufall)"),
        x2="bis:Q", y=y, color=color, tooltip=tip)
    pts = alt.Chart(df).mark_point(filled=True, size=100, stroke="#fcfcfb", strokeWidth=2).encode(
        x="AUC:Q", y=y, color=color, tooltip=tip)
    return alt.layer(chance, ci, pts).properties(height=alt.Step(26))


# --------------------------------------------------------------------------------------------
# d. per-family heat map, e. quality + cost
# --------------------------------------------------------------------------------------------


def heatmap_frame(result: dict[str, Any], refs: list[str]) -> pd.DataFrame:
    V = result.get("variants") or {}
    labels = {s["ref"]: s["label"] for s in result.get("systems") or []}
    rows = []
    for ref in refs:
        r = V.get(ref)
        if r is None:
            continue
        for fam in cb.FAMILIES:
            x = (r.get("families") or {}).get(fam)
            if not x:
                continue
            rows.append({"System": labels.get(ref, ref), "Art": FAMILY_TEXT.get(fam, fam), "Exakt": x["label_acc"],
                         "Markierung richtig": x["flag_acc"], "Anrufe": x["n"],
                         "Text": f"{100 * x['label_acc']:.0f}%"})
    return pd.DataFrame(rows)


def heatmap_chart(df: pd.DataFrame) -> alt.LayerChart:
    systems = list(dict.fromkeys(df["System"]))
    fams = [FAMILY_TEXT[f] for f in cb.FAMILIES if FAMILY_TEXT[f] in set(df["Art"])]
    x = alt.X("Art:N", sort=fams, title=None, axis=alt.Axis(labelAngle=0, orient="top", labelLimit=160))
    y = alt.Y("System:N", sort=systems, title=None, axis=alt.Axis(labelLimit=320))
    tip = ["System:N", "Art:N", alt.Tooltip("Exakt:Q", format=".0%", title="Exakter Status"),
           alt.Tooltip("Markierung richtig:Q", format=".0%"), "Anrufe:Q"]
    rect = alt.Chart(df).mark_rect(cornerRadius=4, stroke="#fcfcfb", strokeWidth=2).encode(
        x=x, y=y, color=alt.Color("Exakt:Q", scale=alt.Scale(domain=[0, 1], range=SEQ),
                                  legend=alt.Legend(format=".0%", title="Exakter Status", orient="bottom")),
        tooltip=tip)
    text = alt.Chart(df).mark_text(fontSize=12).encode(
        x=x, y=y, text="Text:N", tooltip=tip,
        color=alt.condition(alt.datum.Exakt >= 0.55, alt.value("#ffffff"), alt.value(INK)))
    return alt.layer(rect, text).properties(height=alt.Step(34))


def systems_table(result: dict[str, Any], refs: list[str]) -> pd.DataFrame:
    V = result.get("variants") or {}
    labels = {s["ref"]: s["label"] for s in result.get("systems") or []}
    rows = []
    for ref in refs:
        r = V.get(ref)
        if r is None:
            continue
        a, m, c = r["auc"], r.get("metrics") or {}, r.get("cost") or {}
        rows.append({
            "System": labels.get(ref, ref), "Variante": ref, "n": r.get("n_calls"),
            "Flag-AUC [95%-KI]": f"{a['value']:.2f} [{a['lo']:.2f}, {a['hi']:.2f}]" if a.get("lo") is not None else fmt_value(a.get("value"), "auc"),
            "Fehlalarme": (m.get("false_alarm_rate") or {}).get("value"), "Verpasst": (m.get("miss_rate") or {}).get("value"),
            "Exakt": (m.get("accuracy") or {}).get("value"), "Prüf-Recall": (m.get("review_recall") or {}).get("value"),
            "CV@FAR20 Recall": (r.get("far20") or {}).get("flag_recall"), "FAR-Boden": r.get("far_floor"),
            "s/Anruf": c.get("s_per_call"), "LLM-Aufrufe/Anruf": c.get("llm_calls_per_call"),
            "Tags": ", ".join(r.get("tags") or []),
        })
    return pd.DataFrame(rows)


def baselines_table(result: dict[str, Any]) -> pd.DataFrame:
    V = result.get("variants") or {}
    bl = result.get("baselines") or {}
    rows = []

    def add(name: str, auc: Any, m: dict[str, Any]) -> None:
        rows.append({"Referenz": name, "Flag-AUC": auc, "Flag-F1": m.get("flag_f1"),
                     "Fehlalarme": m.get("false_alarm_rate"), "Verpasst": m.get("miss_rate"), "Exakt": m.get("accuracy")})

    def val(r: dict[str, Any]) -> dict[str, Any]:
        return {k: (v or {}).get("value") for k, v in (r.get("metrics") or {}).items()}

    ref = V.get(bl.get("reference") or "")
    if ref:
        add(f"Referenz: {ref['ref']}", ref["auc"]["value"], val(ref))
    if bl.get("flag_all"):
        add("Alles markieren (immer Alarm)", 0.5, bl["flag_all"])
    if bl.get("flag_none"):
        add("Nichts markieren (immer Kein Alarm)", 0.5, bl["flag_none"])
    for key, name in (("keyword_only", "Nur Stichwörter"), ("v1", "v1 (freier Richter)")):
        r = V.get(bl.get(key) or "")
        if r:
            add(f"{name}: {r['ref']}", r["auc"]["value"], val(r))
    return pd.DataFrame(rows)


def pending_items(result: dict[str, Any]) -> list[str]:
    out = []
    for f in result.get("factors") or []:
        for p in f["pairs"]:
            if p["verdict"] == "missing":
                out.append(f"{f.get('short') or f['id']}: {p['label']} (`{p['a']}` → `{p['b']}`; fehlt: "
                           f"{', '.join(p.get('missing_refs') or [])})")
    for tr in result.get("generalisation") or []:
        for e in tr["entries"]:
            if not e.get("available"):
                out.append(f"Generalisierung {tr['title']}: {e['label']} (`{e['ref']}`)")
    for s in result.get("systems") or []:
        if not s.get("available"):
            out.append(f"System {s['label']} (`{s['ref']}`)")
    return out
