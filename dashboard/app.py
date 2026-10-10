"""Dashboard: Anrufe hochladen, Ergebnisse ansehen, Anrufe beurteilen (Labels für späteres Finetuning).

  python -m dashboard.app        # -> http://<diese-IP>:7860 (lauscht auf 0.0.0.0)

Braucht die zwei Dienste: transcription.api (Port 8001) und fraud_analysis.api (Port 8002). Ablauf pro Anruf:
Audio -> POST /transcribe -> Transkript -> POST /analyze -> Ergebnis, alles in dashboard/data (siehe store.py).
Die Alarm-Schwelle ist eine Einstellung des Dashboards: Sie entscheidet über gespeicherte Risiken neu, ohne neue Analyse.
Umgebungsvariablen: DASHBOARD_HOST (0.0.0.0), DASHBOARD_PORT (7860), TRANSCRIPTION_URL, FRAUD_URL, DASHBOARD_DATA.
"""
import html
import json
import os
from pathlib import Path

import gradio as gr

from fraud_analysis import client as fraud
from transcription import client as asr

from . import store

QUESTIONS_FILE = Path(__file__).resolve().parent.parent / "fraud_analysis" / "questions.json"
FILTERS = ["Alle", "Nur Alarme", "Noch nicht beurteilt"]
RED, GREEN, GRAY = "#c62828", "#2e7d32", "#757575"
MUTED = "color:var(--body-text-color-subdued)"
CARD = "border:1px solid var(--border-color-primary);border-radius:10px;padding:12px 14px;background:var(--background-fill-secondary);"


def questions_config():
    """Fragen und Default-Schwelle vom Analyse-Dienst; ist er nicht erreichbar, direkt aus der Datei."""
    try:
        return fraud.config()
    except Exception:
        return json.loads(QUESTIONS_FILE.read_text(encoding="utf-8"))


def categories():
    cfg = questions_config()
    return sorted({q.get("category", qid) for qs in cfg["questions"].values() if isinstance(qs, dict)
                   for qid, q in qs.items() if isinstance(q, dict)})


def threshold():
    return store.get_setting("threshold", questions_config().get("threshold", 0.7))


# ------------------------------------------------------------------ Anzeige-Bausteine

def verdict(call, th):
    if call["status"] == "in_arbeit": return "in Arbeit", GRAY
    if call["status"] == "fehler": return "Fehler", GRAY
    return ("ALARM", RED) if call["risk"] >= th else ("kein Alarm", GREEN)


def main_reason(call):
    a = call["analysis"]
    if not a: return ""
    top = a["checks"][0]
    return f"{top['category']} ({top['source']})" if top.get("source") else top["category"]


def clock(seconds):
    if seconds is None: return "--:--"
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


def badge(text, color):
    return f'<span style="background:{color};color:#fff;border-radius:4px;padding:2px 8px;font-weight:700;font-size:12px">{html.escape(text)}</span>'


def status_line():
    parts = []
    for name, h in (("Transkription", asr.health()), ("Analyse", fraud.health())):
        ok = h.get("status") == "ok"
        parts.append(f'{name}: <b style="color:{GREEN if ok else RED}">{"bereit" if ok else "nicht erreichbar" if h.get("status") == "offline" else "startet"}</b>')
    return f'<div style="font-size:12px;{MUTED}">' + " · ".join(parts) + "</div>"


def summary(calls, th):
    done = [c for c in calls if c["status"] == "fertig"]
    alarms = sum(c["risk"] >= th for c in done)
    open_ = sum(c["label"] is None for c in done)
    tile = lambda label, value: (f'<div style="{CARD}"><div style="font-size:12px;{MUTED}">{label}</div>'   # noqa: E731
                                 f'<div style="font-size:24px;font-weight:600">{value}</div></div>')
    return ('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px">'
            + tile("Anrufe", len(calls)) + tile("Alarme", alarms) + tile("Noch nicht beurteilt", open_) + "</div>")


def table(filter_, th):
    calls = store.list_calls()
    if filter_ == "Nur Alarme": shown = [c for c in calls if c["status"] == "fertig" and c["risk"] >= th]
    elif filter_ == "Noch nicht beurteilt": shown = [c for c in calls if c["status"] == "fertig" and c["label"] is None]
    else: shown = calls
    rows = [[c["id"], c["created_at"].replace("T", " ")[:16], c["filename"], verdict(c, th)[0],
             "" if c["risk"] is None else f"{c['risk']:.0%}", main_reason(c) if c["risk"] is not None and c["risk"] >= th else "",
             store.LABELS.get(c["label"], "offen") if c["status"] == "fertig" else ""] for c in shown]
    df = gr.Dataframe(value=rows or [["", "", "Keine Anrufe", "", "", "", ""]],
                      headers=["Nr.", "Eingang", "Datei", "Ergebnis", "Risiko", "Hauptgrund", "Beurteilung"])
    return summary(calls, th), df, [c["id"] for c in shown]


def detail_html(call, th):
    text, color = verdict(call, th)
    head = (f'<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">{badge(text, color)}'
            f'<b>Anruf {call["id"]} · {html.escape(call["filename"])}</b><span style="{MUTED};font-size:12px">{call["created_at"].replace("T", " ")}</span></div>')
    if call["status"] == "fehler":
        return f'<div style="{CARD}">{head}<div style="margin-top:8px">{html.escape(call["error"] or "")}</div></div>'
    if call["status"] != "fertig":
        return f'<div style="{CARD}">{head}</div>'
    rows = []
    for c in call["analysis"]["checks"]:
        on = c["p"] >= th
        rows.append('<div style="display:grid;grid-template-columns:minmax(0,1fr) 120px 3rem;gap:10px;align-items:center;line-height:24px;font-size:13px" '
                    f'title="{html.escape(c["question"], quote=True)}"><span style="font-weight:{600 if on else 400}">{html.escape(c["category"])} '
                    f'<span style="{MUTED};font-weight:400">· {html.escape(c["source"])} · {html.escape(c["basis"])}</span></span>'
                    '<span style="height:6px;border-radius:999px;background:var(--border-color-primary);position:relative;overflow:hidden">'
                    f'<span style="position:absolute;inset:0 auto 0 0;width:{c["p"] * 100:.0f}%;background:{RED if on else GRAY}"></span></span>'
                    f'<span style="text-align:right;font-weight:{600 if on else 400}">{c["p"]:.0%}</span></div>')
    n_on = sum(c["p"] >= th for c in call["analysis"]["checks"])
    shown, rest = rows[:max(n_on, 3)], rows[max(n_on, 3):]
    more = f'<details><summary style="cursor:pointer;font-size:12px;{MUTED}">{len(rest)} weitere Prüfpunkte</summary>{"".join(rest)}</details>' if rest else ""
    return (f'<div style="{CARD}">{head}<div style="font-size:12px;{MUTED};margin:6px 0">Risiko {call["risk"]:.0%} · '
            f'Alarm ab {th:.0%} · {n_on} Prüfpunkt(e) über der Schwelle</div>{"".join(shown)}{more}</div>')


def transcript_html(call):
    segs = call.get("segments") or []
    if not segs:
        body = html.escape(call.get("transcript") or "").replace("\n", "<br>")
    else:
        body = "".join(f'<div style="margin-bottom:6px"><span style="{MUTED};font-variant-numeric:tabular-nums">{clock(s["start"])}</span> '
                       f'{html.escape(s["text"])}</div>' for s in segs)
    return f'<div style="{CARD}max-height:420px;overflow:auto;font-size:13px;line-height:1.5">{body}</div>'


# ------------------------------------------------------------------ Handler

def refresh(filter_):
    s, df, ids = table(filter_, threshold())
    return status_line(), s, df, ids


def open_call(ids, evt: gr.SelectData):
    if not ids or evt.index[0] >= len(ids):
        return None, gr.Column(visible=False), "", None, "", None, [], "", ""
    call = store.get_call(ids[evt.index[0]])
    th = threshold()
    return (call["id"], gr.Column(visible=True), detail_html(call, th),
            call["audio_path"] if Path(call["audio_path"]).is_file() else None, transcript_html(call),
            call["label"], call["label_categories"] or [], call["label_comment"] or "", call["labeled_by"] or "")


def save_label(cid, label, cats, comment, name, filter_):
    if cid is None: raise gr.Error("Kein Anruf geöffnet.")
    if not label: raise gr.Error("Bitte eine Beurteilung wählen.")
    if not (name or "").strip(): raise gr.Error("Bitte Ihren Namen angeben.")
    store.save_label(cid, label, cats, comment, name.strip())
    st, s, df, ids = refresh(filter_)
    return f'<span style="color:{GREEN}">Beurteilung für Anruf {cid} gespeichert.</span>', s, df, ids


def process(files):
    """Pro Datei: speichern, transkribieren, analysieren. Gibt nach jedem Schritt den Zwischenstand aus."""
    if not files: raise gr.Error("Bitte mindestens eine Aufnahme auswählen.")
    th, lines = threshold(), []

    def render(current=""):
        return (f'<div style="{CARD}font-size:13px">' + "".join(f"<div>{l}</div>" for l in lines)
                + (f'<div style="{MUTED}">{current}</div>' if current else "") + "</div>")

    for f in files:
        path = Path(getattr(f, "name", f))
        cid = store.add_call(path.name, path.read_bytes())
        try:
            yield render(f"{path.name}: Transkription läuft …")
            t = asr.transcribe(store.get_call(cid)["audio_path"])
            yield render(f"{path.name}: Analyse läuft …")
            a = fraud.analyze(t["text"])
            store.save_result(cid, t, a)
            text, color = verdict(store.get_call(cid), th)
            lines.append(f"{badge(text, color)} Anruf {cid} · {html.escape(path.name)} · Risiko {a['risk']:.0%}")
        except Exception as e:
            store.save_error(cid, str(e))
            lines.append(f"{badge('Fehler', GRAY)} Anruf {cid} · {html.escape(path.name)}: {html.escape(str(e))}")
        yield render()
    lines.append(f'<div style="margin-top:6px;{MUTED}">Fertig. Die Ergebnisse stehen im Tab „Anrufe“.</div>')
    yield render()


def preview_threshold(th):
    done = [c for c in store.list_calls() if c["status"] == "fertig"]
    n = sum(c["risk"] >= th for c in done)
    return f"Mit dieser Schwelle hätten **{n} von {len(done)}** geprüften Anrufen einen Alarm."


def save_threshold(th, filter_):
    store.set_setting("threshold", th)
    st, s, df, ids = refresh(filter_)
    return f"Gespeichert: Alarm ab **{th:.0%}** Risiko.", s, df, ids


# ------------------------------------------------------------------ UI

CSS = "#wrap { max-width: 1180px; margin: 0 auto; }"

with gr.Blocks(title="Anruf-Prüfung") as demo:
    with gr.Column(elem_id="wrap"):
        gr.Markdown("## Anruf-Prüfung")
        status_html = gr.HTML()
        with gr.Tabs():
            with gr.Tab("Anrufe"):
                ids_state, current_id = gr.State([]), gr.State(None)
                with gr.Row(equal_height=True):
                    filter_radio = gr.Radio(FILTERS, value="Alle", label="Anzeigen", scale=4)
                    refresh_btn = gr.Button("Aktualisieren", scale=1)
                summary_html = gr.HTML()
                calls_df = gr.Dataframe(interactive=False, wrap=True)
                gr.Markdown("Klicken Sie auf einen Anruf, um ihn zu öffnen.")
                with gr.Column(visible=False) as detail_col:
                    detail = gr.HTML()
                    audio = gr.Audio(type="filepath", label="Aufnahme", interactive=False)
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.Markdown("**Transkript**")
                            transcript = gr.HTML()
                        with gr.Column(scale=2):
                            gr.Markdown("**Ihre Beurteilung**")
                            label_radio = gr.Radio([(v, k) for k, v in store.LABELS.items()], label="Liegt ein Verstoss vor?")
                            cats_box = gr.CheckboxGroup(categories(), label="Betroffene Kategorien (bei Verstoss)")
                            comment_box = gr.Textbox(label="Kommentar", lines=3)
                            name_box = gr.Textbox(label="Ihr Name")
                            save_btn = gr.Button("Beurteilung speichern", variant="primary")
                            saved_html = gr.HTML()

            with gr.Tab("Neue Anrufe prüfen"):
                files_in = gr.File(file_count="multiple", file_types=["audio"], label="Aufnahmen (WAV, MP3, M4A …)")
                start_btn = gr.Button("Prüfung starten", variant="primary")
                progress_html = gr.HTML()

            with gr.Tab("Einstellungen"):
                gr.Markdown("**Alarm-Schwelle**: Ab welchem Risiko ein Anruf als Alarm markiert wird. "
                            "Tiefer = mehr Alarme, weniger übersehene Fälle. Höher = weniger Fehlalarme.")
                th_slider = gr.Slider(0, 1, step=0.01, label="Alarm ab Risiko")
                th_preview = gr.Markdown()
                th_save = gr.Button("Schwelle speichern", variant="primary")
                th_saved = gr.Markdown()

    list_outputs = [status_html, summary_html, calls_df, ids_state]
    demo.load(refresh, filter_radio, list_outputs).then(lambda: threshold(), None, th_slider)
    refresh_btn.click(refresh, filter_radio, list_outputs)
    filter_radio.change(refresh, filter_radio, list_outputs)
    calls_df.select(open_call, ids_state,
                    [current_id, detail_col, detail, audio, transcript, label_radio, cats_box, comment_box, name_box])
    save_btn.click(save_label, [current_id, label_radio, cats_box, comment_box, name_box, filter_radio],
                   [saved_html, summary_html, calls_df, ids_state])
    start_btn.click(process, files_in, progress_html).then(refresh, filter_radio, list_outputs)
    th_slider.change(preview_threshold, th_slider, th_preview, show_progress="hidden")
    th_save.click(save_threshold, [th_slider, filter_radio], [th_saved, summary_html, calls_df, ids_state])

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=CSS, allowed_paths=[str(store.DATA_DIR)],
                server_name=os.environ.get("DASHBOARD_HOST", "0.0.0.0"), server_port=int(os.environ.get("DASHBOARD_PORT", "7860")))
