"""Analyse-Oberfläche für Entwickler: einzelne Transkripte prüfen und gegen die Inventx-Sollbewertung auswerten.

  python -m analysis_ui.app      # -> http://<diese-IP>:7861 (lauscht auf 0.0.0.0)

Nutzt den Fraud-Analyse-Dienst (muss laufen: python -m fraud_analysis.api) und lädt selbst kein Modell.
Tab "Analyse": ein Skript/Transkript laden, mit den Fragen aus dem Editor prüfen, daneben die Sollbewertung.
Tab "Auswertung": TP/FP/FN/TN, Precision/Recall/F1, pro Testziel, Schwellen-Sweep über den ganzen Datensatz.
Umgebungsvariablen: ANALYSIS_UI_HOST (0.0.0.0), ANALYSIS_UI_PORT (7861), FRAUD_URL.
"""
import html
import json
import os
import re

import gradio as gr

from fraud_analysis import client as fraud

from . import evaluate as ev

SOURCES = {"Skript": ev.SCRIPT_DIR, "ASR": ev.ASR_DIR}   # Dropdown-Präfix -> Ordner
EXPECTED_DIR = ev.EXPECTED_DIR
CONFIG_FILE = ev.ROOT / "fraud_analysis" / "questions.json"


def config():
    """Fragen und Schwelle, frisch aus fraud_analysis/questions.json (Änderungen gelten sofort)."""
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ rendering

CARD = "border:1px solid var(--border-color-primary);border-radius:10px;padding:12px 14px;margin-bottom:10px;background:var(--background-fill-secondary);"
TRACK = "position:relative;display:block;height:6px;border-radius:999px;background:var(--border-color-primary);overflow:hidden;"


def render_answers(res):
    """Eine Zeile pro Check, nach Risiko sortiert; ab der Schwelle rot. Frage als Tooltip."""
    th = res["threshold"]
    hits = sum(c["p"] >= th for c in res["checks"])
    verdict, color = ("ALERT", "#c62828") if res["alert"] else ("KEIN ALERT", "#2e7d32")
    parts = [f'<div style="{CARD}border-left:4px solid {color};font-size:12px">'
             '<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:8px">'
             f'<span style="background:{color};color:#fff;border-radius:4px;padding:1px 7px;font-weight:700;font-size:11px">KEV: {verdict}</span>'
             f'<span style="{MUTED}">{hits} Check(s) ≥ {th:.2f} · {res["input_tokens"]} Tokens · {res["latency_ms"]:.0f} ms</span></div>']
    for c in res["checks"]:
        p, on = c["p"], c["p"] >= th
        cat = " · ".join(x for x in (c.get("source", ""), c.get("category", "")) if x)
        parts.append('<div style="display:grid;grid-template-columns:minmax(0,15rem) minmax(0,1fr) 2.6rem;align-items:center;gap:0 10px;line-height:22px" '
                     f'title="{html.escape(c.get("question", ""), quote=True)}"><span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
                     f'<span style="{MUTED}">{html.escape(cat)}</span> · <span style="font-family:var(--font-mono);font-weight:{600 if on else 400}">{html.escape(c["id"])}</span></span>'
                     f'<span style="{TRACK}"><span style="position:absolute;top:0;bottom:0;left:0;border-radius:999px;'
                     f'background:{"#c62828" if on else "var(--body-text-color-subdued)"};width:{max(0.0, min(1.0, p)) * 100:.1f}%"></span></span>'
                     f'<span style="text-align:right;font-variant-numeric:tabular-nums;font-weight:{600 if on else 400}">{p:.2f}</span></div>')
        if c.get("passage"):   # Fundstelle des gleitenden Kev (nur für Checks ab der Schwelle)
            pa = c["passage"]
            parts.append(f'<details style="margin:0 0 6px 12px"><summary style="cursor:pointer;{MUTED}">Fundstelle (p {pa["p"]:.2f}, '
                         f'Zeilen {pa["units"][0] + 1}–{pa["units"][1] + 1})</summary><div style="white-space:pre-wrap;font-size:12px">'
                         f'{html.escape(pa["text"])}</div></details>')
    return "".join(parts) + "</div>"


# ------------------------------------------------------------------ handlers

def decide(state_text, questions_json):
    """Das Transkript mit den Fragen aus dem Editor an POST /analyze."""
    if not (state_text or "").strip(): raise gr.Error("Kein Transkript.")
    try: questions = json.loads(questions_json or "")
    except json.JSONDecodeError as e: raise gr.Error(f"Fragen sind kein gültiges JSON: {e}") from None
    try: return render_answers(fraud.analyze(state_text, questions=questions))
    except RuntimeError as e: raise gr.Error(str(e)) from None


def transcripts():
    return [f"{src} · {p.stem}" for src, d in SOURCES.items() if d.is_dir() for p in sorted(d.glob("*.txt"))]


VERDICT = {"alarm": ("ALERT", "#c62828"), "review": ("ALERT · review", "#c62828"), "no_alert": ("KEIN ALERT", "#2e7d32")}
MUTED = "color:var(--body-text-color-subdued)"


def sollbewertung(stem):
    """Kompakte Karte mit der Sollbewertung zu Stufe1_D01 bzw. Stufe1_D01-K1: Urteil, Titel, Begründung in wenigen
    Zeilen; Belegstellen im Wortlaut und Keywordstellen zum Aufklappen."""
    f = EXPECTED_DIR / f"{stem.split('-', 1)[0]}.txt"
    if not f.is_file(): return f'<div style="font-size:12px;{MUTED}">Keine Sollbewertung zu diesem Transkript.</div>'
    head, _, body = f.read_text(encoding="utf-8").partition("\nT001 ·")
    lines = head.strip().splitlines()
    fields = dict(re.match(r"^([^:]+):\s*(.*)$", l).groups() for l in lines[2:] if re.match(r"^[^:]+:", l))
    m = re.search(r"Belege:\s*(.+)$", head, re.M)   # "Prüfpräfix bis T008; Belege: T004, T008"
    belege = re.findall(r"T\d{3}", m[1]) if m else []
    turns = {m[1]: (m[2], " ".join(m[3].split())) for m in re.finditer(r"^(T\d{3}) · (.+?)\s*\n(.*?)(?=\n\s*\nT\d{3} ·|\Z)", "T001 ·" + body, re.M | re.S)}
    label, color = VERDICT.get(fields.get("Bearbeitung", ""), (fields.get("Bearbeitung", "?"), "gray"))
    e = html.escape
    meta = " · ".join(e(fields[k]) for k in ("Testziel", "Ereignis") if fields.get(k))
    offen = fields.get("Offen", "")
    out = [f'<div style="{CARD}border-left:4px solid {color};font-size:12px;line-height:1.45">',
           '<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap">'
           f'<span style="background:{color};color:#fff;border-radius:4px;padding:1px 7px;font-weight:700;font-size:11px">SOLL: {label}</span>'
           f'<b style="font-size:13px">{e(lines[0])}</b><span style="{MUTED}">{meta}</span></div>',
           f'<div style="margin-top:4px">{e(fields.get("Begründung", ""))}</div>']
    if offen and not offen.startswith("keine"):
        out.append(f'<div style="margin-top:2px;{MUTED}"><b>Offen:</b> {e(offen)}</div>')
    if belege:
        quotes = "".join(f'<div style="margin-top:4px"><b>{t} · {e(turns[t][0])}:</b> {e(turns[t][1])}</div>' if t in turns else f"<div>{t}</div>" for t in belege)
        kw = fields.get("Keywordstellen", "")
        out.append(f'<details style="margin-top:4px"><summary style="cursor:pointer;{MUTED}">Belegstellen {", ".join(belege)}</summary>{quotes}'
                   + (f'<div style="margin-top:4px;{MUTED}"><b>Keywords:</b> {e(kw)}</div>' if kw else "") + "</details>")
    return "".join(out) + "</div>"


def load_transcript(choice):
    if not choice: raise gr.Error("Kein Transkript gewählt.")
    src, _, stem = choice.partition(" · ")
    text = (SOURCES[src] / f"{stem}.txt").read_text(encoding="utf-8")
    questions = config()["questions"]   # frisch: Änderungen an der Config gelten sofort
    return text, json.dumps(questions, indent=2, ensure_ascii=False), sollbewertung(stem)


# ------------------------------------------------------------------ Auswertung (Tab)
# Gleiche Analyse und Ablage wie analysis_ui.evaluate (outputs/kev/scripts | asr): was das Skript gerechnet hat, lädt der
# Tab, und umgekehrt. Die Ergebnisse werden einmal gerechnet; die Schwelle entscheidet danach neu, ohne Dienst.

EVAL_SOURCES = {"Skripte (30 Dialoge)": "scripts", "ASR (Whisper-Transkripte)": "asr"}


def cached_results(source):
    return ev.cached(EVAL_SOURCES[source])


def run_all(source, progress=gr.Progress()):
    """Alle Transkripte der Quelle durch den Dienst; der liest questions.json frisch, Änderungen gelten also."""
    if not any(ev.SOURCES[EVAL_SOURCES[source]].glob("*.txt")):
        raise gr.Error(f"Keine Transkripte in {ev.SOURCES[EVAL_SOURCES[source]]}")
    try: return ev.run(EVAL_SOURCES[source], on_progress=lambda i, n, stem, res: progress((i, n), desc=f"Analyse {stem}"))
    except RuntimeError as e: raise gr.Error(str(e)) from None


def tile(label, value, hint=""):
    return (f'<div style="{CARD}margin:0;padding:10px 12px;min-width:0"><div style="font-size:11px;{MUTED}">{label}</div>'
            f'<div style="font-size:22px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.3">{value}</div>'
            f'<div style="font-size:11px;{MUTED}">{hint}</div></div>')


def pct(x): return "–" if x != x else f"{x:.0%}"


def evaluate(results, threshold):
    if not results:
        empty = f'<div style="font-size:13px;{MUTED}">Noch keine Ergebnisse für diese Quelle. Klicke <b>Alle berechnen</b>.</div>'
        return empty, None, None, None
    rows = [r for r in ev.rows_for(results, threshold) if r["soll"]]
    c = ev.counts(rows)
    grid = 'display:grid;grid-template-columns:repeat(auto-fit,minmax(118px,1fr));gap:8px;margin-bottom:8px'
    tiles = (f'<div style="font-size:12px;{MUTED};margin-bottom:6px">{len(rows)} Anrufe · Alert ab Risk ≥ {threshold:.2f} · '
             f'Soll-Alert = Inventx alarm oder review</div>'
             f'<div style="{grid}">' + tile("TP", c["TP"], "richtig gemeldet") + tile("FP", c["FP"], "Fehlalarm")
             + tile("FN", c["FN"], "verpasst") + tile("TN", c["TN"], "richtig still") + "</div>"
             f'<div style="{grid}">' + tile("Precision", pct(c["Precision"])) + tile("Recall", pct(c["Recall"])) + tile("F1", pct(c["F1"]))
             + tile("Specificity", pct(c["Specificity"])) + tile("Accuracy", pct(c["Accuracy"])) + "</div>")
    by_target = []
    for t in sorted({r["testziel"] for r in rows}):
        s = ev.counts([r for r in rows if r["testziel"] == t])
        by_target.append([t, s["TP"], s["FP"], s["FN"], s["TN"]])
    check_names = list(rows[0]["scores"]) if rows else []
    per_call = [[r["call"], r["testziel"], f"{r['soll']} ({r['soll_original']})", r["ist"], "✓" if r["soll"] == r["ist"] else "✗",
                 round(r["risk"], 2), r["top_check"]] + [round(r["scores"].get(q, 0.0), 2) for q in check_names]
                for r in sorted(rows, key=lambda r: (r["soll"] == r["ist"], r["call"]))]   # Fehler zuerst
    sweep = []
    for t in ev.SWEEP:
        s = ev.counts([{**r, "ist": ev.decide(r["risk"], t)} for r in rows])
        sweep.append([t] + [s[k] for k in ("TP", "FP", "FN", "TN")] + [pct(s[k]) for k in ("Precision", "Recall", "F1")])
    return (tiles,
            gr.Dataframe(value=by_target, headers=["Testziel", "TP", "FP", "FN", "TN"]),
            gr.Dataframe(value=per_call, headers=["Anruf", "Testziel", "Soll", "Ist", "", "Risk", "Top-Check", *check_names]),
            gr.Dataframe(value=sweep, headers=["Schwelle", "TP", "FP", "FN", "TN", "Precision", "Recall", "F1"]))


# ------------------------------------------------------------------ UI

QUESTIONS_JSON = json.dumps(config()["questions"], indent=2, ensure_ascii=False)

PLACEHOLDER = ('<div style="border:1px dashed var(--border-color-primary);border-radius:10px;padding:28px 16px;text-align:center;'
               'color:var(--body-text-color-subdued);font-size:13px">Transkript laden, dann Prüfen.</div>')

EVAL_HELP = """**Positiv** = Alert (geht zur manuellen Prüfung). Soll-Alert sind Inventx' *alarm* und *review*.
**FP** = Fehlalarm (soll kein Alert, ist Alert), **FN** = verpasst (soll Alert, ist kein Alert). Die Sollbewertung wird nur hier zur Auswertung gelesen, nie als Eingabe für Kev."""

CSS = """
#col-container { max-width: 1180px; margin: 0 auto; }
#questions .cm-editor { max-height: 420px; }
"""

with gr.Blocks(title="Kev Analyse") as demo:
    with gr.Column(elem_id="col-container"):
        gr.Markdown(f"## Kev Analyse (Entwickler) · Fraud-Dienst: {fraud.URL}")

        with gr.Tabs():
            with gr.Tab("Analyse"):
                with gr.Row(equal_height=True):
                    transcript_dd = gr.Dropdown(transcripts(), label="Transkript (Skript = Case-Skript, ASR = Whisper)", scale=4)
                    refresh_btn = gr.Button("↻", scale=0, min_width=48)
                    load_btn = gr.Button("Laden", scale=1)
                    run_btn = gr.Button("Prüfen", variant="primary", scale=1, min_width=120)

                with gr.Row():
                    with gr.Column(scale=1):
                        state_box = gr.Textbox(label="Transkript", lines=6, max_lines=14)
                        questions_box = gr.Code(label="Fragen (JSON)", language="json", lines=14, value=QUESTIONS_JSON, elem_id="questions")
                    with gr.Column(scale=1):
                        soll_md = gr.HTML()
                        answers_html = gr.HTML(value=PLACEHOLDER)

            with gr.Tab("Auswertung"):
                results_state = gr.State({})
                with gr.Row(equal_height=True):
                    source_radio = gr.Radio(list(EVAL_SOURCES), value=next(iter(EVAL_SOURCES)), label="Datensatz", scale=2)
                    run_all_btn = gr.Button("Alle berechnen", variant="primary", scale=1, min_width=160)
                threshold_sl = gr.Slider(0, 1, value=config()["threshold"], step=0.01, label="Schwelle (Risk ≥ Schwelle → Alert)")
                tiles_html = gr.HTML()
                with gr.Row():
                    with gr.Column(scale=1):
                        target_df = gr.Dataframe(label="Pro Testziel", interactive=False)
                    with gr.Column(scale=1):
                        sweep_df = gr.Dataframe(label="Schwellen-Sweep", interactive=False)
                calls_df = gr.Dataframe(label="Pro Anruf (Fehler zuerst)", interactive=False, wrap=True)
                with gr.Accordion("Was die Zahlen bedeuten", open=False): gr.Markdown(EVAL_HELP)

    run_btn.click(fn=decide, inputs=[state_box, questions_box], outputs=answers_html, api_name="decide")
    refresh_btn.click(fn=lambda: gr.Dropdown(choices=transcripts()), outputs=transcript_dd)
    load_btn.click(fn=load_transcript, inputs=transcript_dd, outputs=[state_box, questions_box, soll_md])

    eval_inputs = [results_state, threshold_sl]
    eval_outputs = [tiles_html, target_df, calls_df, sweep_df]
    run_all_btn.click(fn=run_all, inputs=source_radio, outputs=results_state).then(
        fn=evaluate, inputs=eval_inputs, outputs=eval_outputs)
    for trigger in (source_radio.change, demo.load):
        trigger(fn=cached_results, inputs=source_radio, outputs=results_state).then(fn=evaluate, inputs=eval_inputs, outputs=eval_outputs)
    threshold_sl.release(fn=evaluate, inputs=eval_inputs, outputs=eval_outputs, show_progress="hidden")

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Monochrome(), css=CSS,
                server_name=os.environ.get("ANALYSIS_UI_HOST", "0.0.0.0"), server_port=int(os.environ.get("ANALYSIS_UI_PORT", "7861")))
