"""Quality numbers for the officer: confusion matrix, flag precision/recall/F1, false alarms, misses and
the threshold sweep with a suggested threshold.

"Flag" is the case's headline view: a call counts as flagged when a human has to listen to it
(``alarm`` or ``review``). Kept local to the UI (the eval module is developed in parallel) and pure:
labels in, numbers and Altair charts out.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass

import altair as alt
import pandas as pd

from callguard.types import LABELS

FLAG_LABELS = ("alarm", "review")
LABEL_TEXT = {"alarm": "Alarm", "review": "Review", "no_alert": "No alert"}
METRIC_COLORS = {"Precision": "#4e79a7", "Recall": "#f28e2b", "F1": "#2f2f2f", "False-alarm rate": "#c44e52"}


def is_flag(label: str | None) -> bool:
    return label in FLAG_LABELS


def _div(a: float, b: float) -> float | None:
    return a / b if b else None


@dataclass
class FlagMetrics:
    n: int = 0
    tp: int = 0  # flagged and should be flagged
    fp: int = 0  # flagged although harmless (false alarm)
    fn: int = 0  # passed although it should be flagged (miss)
    tn: int = 0
    exact: int = 0  # predicted label == expected label (3 classes)
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    false_alarm_rate: float | None = None  # harmless calls flagged / harmless calls
    miss_rate: float | None = None  # flaggable calls passed / flaggable calls
    accuracy: float | None = None  # exact label accuracy

    def as_dict(self) -> dict:
        return asdict(self)


def flag_metrics(pairs: Iterable[tuple[str, str]]) -> FlagMetrics:
    """``pairs`` = (expected label, predicted label) per call. Undefined ratios stay None, not 0."""
    m = FlagMetrics()
    for expected, predicted in pairs:
        m.n += 1
        m.exact += expected == predicted
        e, p = is_flag(expected), is_flag(predicted)
        if e and p:
            m.tp += 1
        elif p:
            m.fp += 1
        elif e:
            m.fn += 1
        else:
            m.tn += 1
    m.precision = _div(m.tp, m.tp + m.fp)
    m.recall = _div(m.tp, m.tp + m.fn)
    if m.precision is not None and m.recall is not None:
        m.f1 = 0.0 if m.precision + m.recall == 0 else 2 * m.precision * m.recall / (m.precision + m.recall)
    elif m.tp + m.fn > 0:  # nothing flagged although something should have been
        m.f1 = 0.0
    m.false_alarm_rate = _div(m.fp, m.fp + m.tn)
    m.miss_rate = _div(m.fn, m.tp + m.fn)
    m.accuracy = _div(m.exact, m.n)
    return m


def confusion(pairs: Iterable[tuple[str, str]]) -> pd.DataFrame:
    """Rows = expected, columns = predicted, in alarm/review/no_alert order."""
    counts = {e: {p: 0 for p in LABELS} for e in LABELS}
    for expected, predicted in pairs:
        if expected in counts and predicted in counts[expected]:
            counts[expected][predicted] += 1
    df = pd.DataFrame(counts).T.loc[list(LABELS), list(LABELS)]
    df.index = [LABEL_TEXT[x] for x in df.index]
    df.columns = [LABEL_TEXT[x] for x in df.columns]
    df.index.name = "Expected"
    return df


def sweep(labels_by_threshold: Mapping[float, Mapping[str, str]], truth: Mapping[str, str]) -> list[dict]:
    """Flag metrics per threshold; only calls with ground truth count."""
    rows = []
    for t in sorted(labels_by_threshold):
        labels = labels_by_threshold[t]
        m = flag_metrics((truth[cid], lbl) for cid, lbl in labels.items() if cid in truth)
        flagged = sum(1 for lbl in labels.values() if is_flag(lbl))
        rows.append({"threshold": t, "precision": m.precision, "recall": m.recall, "f1": m.f1,
                     "false_alarm_rate": m.false_alarm_rate, "miss_rate": m.miss_rate,
                     "accuracy": m.accuracy, "flagged": flagged, "alarms": sum(lbl == "alarm" for lbl in labels.values())})
    return rows


def suggest_threshold(rows: list[dict], current: float | None = None) -> float | None:
    """Highest F1; ties -> fewer false alarms, then closest to the current setting (least surprise).

    Thresholds that flag every call are skipped when any other exists: with many positive test calls
    "listen to everything" scores a deceptively good F1 but is no threshold an officer can use.
    """
    scored = [r for r in rows if r.get("f1") is not None]
    useful = [r for r in scored if r.get("false_alarm_rate") is None or r["false_alarm_rate"] < 1.0]
    scored = useful or scored
    if not scored:
        return None

    def key(r: dict) -> tuple:
        far = r.get("false_alarm_rate")
        return (-round(r["f1"], 6), far if far is not None else 1.0,
                abs(r["threshold"] - current) if current is not None else 0.0, r["threshold"])

    return min(scored, key=key)["threshold"]


# --------------------------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------------------------


def sweep_chart(rows: list[dict], current: float, suggested: float | None) -> alt.LayerChart:
    long = []
    for r in rows:
        for name, k in (("Precision", "precision"), ("Recall", "recall"), ("F1", "f1"),
                        ("False-alarm rate", "false_alarm_rate")):
            if r.get(k) is not None:
                long.append({"Threshold": r["threshold"], "Metric": name, "Value": r[k]})
    data = pd.DataFrame(long, columns=["Threshold", "Metric", "Value"])
    names = list(METRIC_COLORS)
    color = alt.Color("Metric:N", scale=alt.Scale(domain=names, range=[METRIC_COLORS[n] for n in names]),
                      legend=alt.Legend(orient="bottom", title=None))
    dash = alt.condition(alt.datum.Metric == "False-alarm rate", alt.value([4, 3]), alt.value([1, 0]))
    x = alt.X("Threshold:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format=".2f"))
    lines = alt.Chart(data).mark_line(point=alt.OverlayMarkDef(size=28)).encode(
        x=x, y=alt.Y("Value:Q", scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%", title=None)),
        color=color, strokeDash=dash,
        tooltip=[alt.Tooltip("Threshold:Q", format=".2f"), "Metric:N", alt.Tooltip("Value:Q", format=".0%")],
    )
    if suggested is not None and abs(suggested - current) < 1e-9:
        marks = [{"Threshold": current, "What": "current = suggested"}]
    else:
        marks = [{"Threshold": current, "What": "current"}]
        if suggested is not None:
            marks.append({"Threshold": suggested, "What": "suggested (max F1)"})
    rule_data = pd.DataFrame(marks)
    rule_color = alt.Color("What:N", scale=alt.Scale(domain=["current", "suggested (max F1)", "current = suggested"],
                                                     range=["#6c6c6c", "#2e8b57", "#2e8b57"]), legend=None)
    rules = alt.Chart(rule_data).mark_rule(strokeWidth=2).encode(
        x="Threshold:Q", color=rule_color,
        strokeDash=alt.condition(alt.datum.What == "suggested (max F1)", alt.value([6, 4]), alt.value([1, 0])),
        tooltip=["What:N", alt.Tooltip("Threshold:Q", format=".2f")],
    )
    text = alt.Chart(rule_data).mark_text(align="left", dx=4, dy=0, fontSize=11).encode(
        x="Threshold:Q", y=alt.value(-8), text="What:N", color=rule_color)
    return alt.layer(lines, rules, text).resolve_scale(color="independent").properties(height=320)


def confusion_chart(matrix: pd.DataFrame) -> alt.LayerChart:
    data = matrix.reset_index().melt(id_vars="Expected", var_name="Predicted", value_name="Calls")
    data["Cell"] = [("correct" if e == p else "wrong") if n else "none"
                    for e, p, n in zip(data["Expected"], data["Predicted"], data["Calls"])]
    order = [LABEL_TEXT[x] for x in LABELS]
    top = max(1, int(data["Calls"].max()) if len(data) else 1)
    base = alt.Chart(data).encode(
        x=alt.X("Predicted:N", sort=order, axis=alt.Axis(orient="top", labelAngle=0, title="Predicted")),
        y=alt.Y("Expected:N", sort=order, title="Expected"),
    )
    heat = base.mark_rect(stroke="white", strokeWidth=2).encode(
        color=alt.Color("Cell:N", scale=alt.Scale(domain=["correct", "wrong", "none"],
                                                  range=["#3f9c5f", "#d64545", "#eeeeee"]), legend=None),
        opacity=alt.Opacity("Calls:Q", scale=alt.Scale(domain=[0, top], range=[0.35, 0.9]), legend=None),
        tooltip=["Expected:N", "Predicted:N", "Calls:Q"],
    )
    text = base.mark_text(fontSize=16, fontWeight="bold", color="#1f1f1f").encode(text="Calls:Q")
    return alt.layer(heat, text).properties(height=220)
