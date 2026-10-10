"""Dashboard: Anrufe hochladen, Ergebnisse ansehen, Anrufe beurteilen (Labels für späteres Finetuning).

  python -m dashboard.app        # -> http://<diese-IP>:7860 (lauscht auf 0.0.0.0)

Braucht die zwei Dienste: transcription.api (Port 8001) und fraud_analysis.api (Port 8002). Ablauf pro Anruf:
Audio -> POST /transcribe -> Transkript -> POST /analyze -> Ergebnis, alles in dashboard/data (siehe store.py).
Beim Hochladen werden zuerst alle Dateien transkribiert, dann das ASR-Modell entladen, dann alles analysiert: So liegt
nie mehr als ein Modell gleichzeitig auf der GPU.
Die Alarm-Schwelle ist eine Einstellung des Dashboards: Sie entscheidet über gespeicherte Risiken neu, ohne neue Analyse.
Umgebungsvariablen: DASHBOARD_HOST (0.0.0.0), DASHBOARD_PORT (7860), DASHBOARD_REFRESH_SECONDS (10), TRANSCRIPTION_URL,
FRAUD_URL, DASHBOARD_DATA.
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


def passage_words():
    return store.get_setting("passage_words", questions_config().get("localization", {}).get("passage_words", 25))


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


SELECTED_ROW = "background-color: rgba(37, 99, 235, 0.16)"


def row_table(rows, headers, selected=None):
    """Tabelle, in der die geöffnete Zeile ganz hinterlegt ist. Gradio kennt nur die Auswahl einzelner Zellen; die Zeile
    wird deshalb beim Öffnen über pandas-Formatierung markiert (selected = Zeilennummer)."""
    import pandas as pd
    df = pd.DataFrame(rows, columns=headers)
    if selected is not None and 0 <= selected < len(df):
        df = df.style.apply(lambda r: [SELECTED_ROW if r.name == selected else ""] * len(r), axis=1)
    return gr.Dataframe(value=df, headers=headers)


def table(filter_, th, selected=None):
    """selected: id des geöffneten Anrufs (wird hinterlegt)."""
    calls = store.list_calls()
    if filter_ == "Nur Alarme": shown = [c for c in calls if c["status"] == "fertig" and c["risk"] >= th]
    elif filter_ == "Noch nicht beurteilt": shown = [c for c in calls if c["status"] == "fertig" and c["label"] is None]
    else: shown = calls
    rows = [[c["id"], c["created_at"].replace("T", " ")[:16], c["filename"], verdict(c, th)[0],
             "" if c["risk"] is None else f"{c['risk']:.0%}", main_reason(c) if c["risk"] is not None and c["risk"] >= th else "",
             store.LABELS.get(c["label"], "offen") if c["status"] == "fertig" else ""] for c in shown]
    ids = [c["id"] for c in shown]
    df = row_table(rows or [["", "", "Keine Anrufe", "", "", "", ""]],
                   ["Nr.", "Eingang", "Datei", "Ergebnis", "Risiko", "Hauptgrund", "Beurteilung"],
                   ids.index(selected) if selected in ids else None)
    return summary(calls, th), df, ids


def findings(call, th):
    """Die Checks ab der Schwelle (Befunde), nach Risiko sortiert."""
    return [c for c in (call["analysis"] or {}).get("checks", []) if c["p"] >= th]


MERGE_GAP = 2.0   # Sekunden: Fundstellen, die sich überlappen oder näher beieinander liegen, werden eine Stelle


def regions(call, th):
    """Fundstellen der Befunde, überlappende zu einer Stelle zusammengefasst, nach Zeit sortiert.
    -> [{"n": 1, "start", "end", "checks": [Befund, ...]}]. Befunde ohne Zeitangabe bilden je eine eigene Stelle."""
    timed = sorted((c for c in findings(call, th) if c.get("passage") and c["passage"].get("start") is not None),
                   key=lambda c: c["passage"]["start"])
    out = []
    for c in timed:
        p = c["passage"]
        if out and p["start"] <= out[-1]["end"] + MERGE_GAP:
            out[-1]["end"] = max(out[-1]["end"], p["end"]); out[-1]["checks"].append(c)
        else:
            out.append({"start": p["start"], "end": p["end"], "checks": [c]})
    for c in findings(call, th):
        if c.get("passage") and c["passage"].get("start") is None:
            out.append({"start": None, "end": None, "checks": [c], "text": c["passage"]["text"]})
    for n, r in enumerate(out, 1): r["n"] = n
    return out


def region_of(call, th):
    """{check_id: Stellennummer}."""
    return {c["id"]: r["n"] for r in regions(call, th) for c in r["checks"]}


def region_text(call, r):
    """Text der Stelle aus den Abschnitten: die Wörter, deren geschätzte Zeit in [start, end] liegt (die Wörter eines
    Abschnitts gleichmässig über seine Dauer verteilt, wie bei der Lokalisierung)."""
    if r.get("text") is not None: return r["text"]
    lines = []
    for s in call.get("segments") or []:
        words = s["text"].split()
        if not words or s.get("start") is None or s["end"] <= r["start"] or s["start"] >= r["end"]: continue
        step = (s["end"] - s["start"]) / len(words)
        keep = [w for i, w in enumerate(words) if s["start"] + (i + 0.5) * step >= r["start"] and s["start"] + (i + 0.5) * step <= r["end"]]
        if keep: lines.append((f"{s['speaker']}: " if s.get("speaker") else "") + " ".join(keep))
    return "\n".join(lines)


def span(r):
    if not r or r.get("start") is None: return ""
    return f"{clock(r['start'])}–{clock(r['end'])}"


def detail_html(call, th):
    text, color = verdict(call, th)
    head = (f'<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap">{badge(text, color)}'
            f'<b>Anruf {call["id"]} · {html.escape(call["filename"])}</b><span style="{MUTED};font-size:12px">{call["created_at"].replace("T", " ")}</span></div>')
    if call["status"] == "fehler":
        return f'<div style="{CARD}">{head}<div style="margin-top:8px">{html.escape(call["error"] or "")}</div></div>'
    if call["status"] != "fertig":
        return f'<div style="{CARD}">{head}</div>'
    found, regs = findings(call, th), regions(call, th)
    where = region_of(call, th)
    # Befunde: eine Zeile pro Befund, mit Verweis auf die Stelle
    rows = ""
    for c in found:
        stelle = f"Stelle {where[c['id']]}" if c["id"] in where else "keine Stelle"
        rows += ('<div style="display:grid;grid-template-columns:minmax(0,1fr) auto 3rem;gap:10px;align-items:baseline;line-height:24px;font-size:13px" '
                 f'title="{html.escape(c["question"], quote=True)}"><span><b>{html.escape(c["category"])}</b> '
                 f'<span style="{MUTED};font-size:12px">· {html.escape(c["source"])} · {html.escape(c["basis"])}</span></span>'
                 f'<span style="{MUTED};font-size:12px">{stelle}</span>'
                 f'<span style="text-align:right;font-weight:600;color:{RED}">{c["p"]:.0%}</span></div>')
    # Fundstellen: Text nur einmal pro Stelle
    blocks = "".join(f'<div style="margin-top:8px"><div style="font-size:12px"><b>Stelle {r["n"]}</b> '
                     f'<span style="{MUTED}">{span(r) or "ohne Zeitangabe"} · {html.escape(", ".join(dict.fromkeys(c["category"] for c in r["checks"])))}</span></div>'
                     f'<div style="margin-top:2px;padding:6px 10px;border-left:3px solid {RED};background:var(--background-fill-primary);font-size:12px">'
                     f'{html.escape(region_text(call, r)).replace(chr(10), "<br>")}</div></div>' for r in regs)
    rest = [c for c in call["analysis"]["checks"] if c["p"] < th]
    rest_rows = "".join('<div style="display:grid;grid-template-columns:minmax(0,1fr) 120px 3rem;gap:10px;align-items:center;line-height:22px;font-size:12px" '
                        f'title="{html.escape(c["question"], quote=True)}"><span>{html.escape(c["category"])} <span style="{MUTED}">· {html.escape(c["source"])}</span></span>'
                        '<span style="height:6px;border-radius:999px;background:var(--border-color-primary);position:relative;overflow:hidden">'
                        f'<span style="position:absolute;inset:0 auto 0 0;width:{c["p"] * 100:.0f}%;background:{GRAY}"></span></span>'
                        f'<span style="text-align:right">{c["p"]:.0%}</span></div>' for c in rest)
    more = f'<details style="margin-top:10px"><summary style="cursor:pointer;font-size:12px;{MUTED}">{len(rest)} Prüfpunkte unter der Schwelle</summary>{rest_rows}</details>' if rest else ""
    missing = sum(1 for c in found if not c.get("passage"))
    note = f'<div style="font-size:12px;{MUTED};margin-top:4px">{missing} Befund(e) ohne Fundstelle (Schwelle nach der Analyse gesenkt)</div>' if missing else ""
    return (f'<div style="{CARD}">{head}<div style="font-size:12px;{MUTED};margin:6px 0">Risiko {call["risk"]:.0%} · Alarm ab {th:.0%} · '
            f'{len(found)} Befund(e) an {len(regs)} Stelle(n)</div>{rows}{note}'
            + (f'<div style="margin-top:10px;font-size:12px;{MUTED}">Fundstellen</div>{blocks}' if regs else "") + f'{more}</div>')


def transcript_html(call, th):
    """Abschnitte mit Zeit und Sprecher; Abschnitte, die eine Fundstelle berühren, sind markiert."""
    segs = call.get("segments") or []
    if not segs:
        body = html.escape(call.get("transcript") or "").replace("\n", "<br>")
    else:
        regs = [r for r in regions(call, th) if r["start"] is not None]
        hit = lambda s: s.get("start") is not None and any(s["start"] < r["end"] and s["end"] > r["start"] for r in regs)   # noqa: E731
        body = "".join(f'<div style="margin-bottom:6px;padding:2px 6px;border-radius:4px;{"background:rgba(198,40,40,0.12);" if hit(s) else ""}">'
                       f'<span style="{MUTED};font-variant-numeric:tabular-nums">{clock(s["start"])}</span> '
                       + (f'<b>{html.escape(s["speaker"])}:</b> ' if s.get("speaker") else "")
                       + f'{html.escape(s["text"])}</div>' for s in segs)
    return f'<div style="{CARD}max-height:420px;overflow:auto;font-size:13px;line-height:1.5">{body}</div>'


# ------------------------------------------------------------------ Handler

def refresh(filter_, selected=None):
    s, df, ids = table(filter_, threshold(), selected)
    return status_line(), s, df, ids


REFRESH_SECONDS = float(os.environ.get("DASHBOARD_REFRESH_SECONDS", "10"))


def snapshot():
    """Was die Anrufliste und die Statuszeile bestimmt; ändert es sich, wird neu gezeichnet."""
    calls = tuple((c["id"], c["status"], c["risk"], c["label"]) for c in store.list_calls())
    return repr((calls, threshold(), status_line()))


def auto_refresh(filter_, selected, last):
    """Alle REFRESH_SECONDS: nur neu zeichnen, wenn sich etwas geändert hat (sonst springt die Tabelle nicht)."""
    now = snapshot()
    if now == last: return gr.skip(), gr.skip(), gr.skip(), gr.skip(), last
    return (*refresh(filter_, selected), now)


def open_call(ids, filter_, evt: gr.SelectData):
    if not ids or evt.index[0] >= len(ids):
        return (None, gr.Column(visible=False), "", None, "", None, gr.CheckboxGroup(choices=[], value=[]), [], "", "",
                gr.Dropdown(choices=[], value=None), None, gr.Dataframe())
    call = store.get_call(ids[evt.index[0]])
    th = threshold()
    found = findings(call, th) if call["status"] == "fertig" else []
    regs = regions(call, th) if call["status"] == "fertig" else []
    where = {c["id"]: r["n"] for r in regs for c in r["checks"]}
    ok = [cid for cid, good in (call["label_checks"] or {}).items() if good]
    label = lambda c: f"{c['category']} ({c['id']})" + (f" · Stelle {where[c['id']]}" if c["id"] in where else "")   # noqa: E731
    return (call["id"], gr.Column(visible=True), detail_html(call, th),
            call["audio_path"] if Path(call["audio_path"]).is_file() else None, transcript_html(call, th), call["label"],
            gr.CheckboxGroup(choices=[(label(c), c["id"]) for c in found], value=[i for i in ok if i in {c["id"] for c in found}]),
            gr.CheckboxGroup(choices=categories(), value=call["label_missed"] or []), call["label_comment"] or "", call["labeled_by"] or "",
            gr.Dropdown(choices=[(f"Stelle {r['n']} · {span(r)} · " + ", ".join(dict.fromkeys(c["category"] for c in r["checks"])), r["n"])
                                 for r in regs if r["start"] is not None], value=None), None,
            table(filter_, th, call["id"])[1])


def play_snippet(cid, n):
    if cid is None or not n: return None
    call = store.get_call(cid)
    r = next((r for r in regions(call, threshold()) if r["n"] == n), None)
    if not r or r["start"] is None: raise gr.Error("Diese Fundstelle hat keine Zeitangabe.")
    try: return store.snippet(call, r["start"], r["end"])
    except Exception as e: raise gr.Error(f"Ausschnitt konnte nicht erstellt werden: {e}") from None


def save_label(cid, label, ok_ids, missed, comment, name, filter_):
    if cid is None: raise gr.Error("Kein Anruf geöffnet.")
    if not label: raise gr.Error("Bitte eine Beurteilung wählen.")
    if not (name or "").strip(): raise gr.Error("Bitte Ihren Namen angeben.")
    call = store.get_call(cid)
    found = findings(call, threshold()) if call["status"] == "fertig" else []
    checks = {c["id"]: c["id"] in (ok_ids or []) for c in found}
    categories = sorted({c["category"] for c in found if checks[c["id"]]} | set(missed or []))
    store.save_label(cid, label, checks, missed, categories, comment, name.strip())
    st, s, df, ids = refresh(filter_, cid)
    return f'<span style="color:{GREEN}">Beurteilung für Anruf {cid} gespeichert.</span>', s, df, ids


def process(files):
    """Erst alle Dateien speichern und transkribieren, dann das ASR-Modell entladen, dann alle analysieren.
    Gibt nach jedem Schritt den Zwischenstand aus."""
    if not files: raise gr.Error("Bitte mindestens eine Aufnahme auswählen.")
    th, lines = threshold(), []

    def render(current=""):
        return (f'<div style="{CARD}font-size:13px">' + "".join(f"<div>{l}</div>" for l in lines)
                + (f'<div style="{MUTED}">{current}</div>' if current else "") + "</div>")

    def failed(cid, name, e):
        store.save_error(cid, str(e))
        lines.append(f"{badge('Fehler', GRAY)} Anruf {cid} · {html.escape(name)}: {html.escape(str(e))}")

    transcribed = []   # (id, dateiname, transkription)
    for i, f in enumerate(files, 1):
        path = Path(getattr(f, "name", f))
        cid = store.add_call(path.name, path.read_bytes())
        yield render(f"Transkription {i}/{len(files)}: {path.name} …")
        try: transcribed.append((cid, path.name, asr.transcribe(store.get_call(cid)["audio_path"])))
        except Exception as e: failed(cid, path.name, e)
    asr.unload()   # VRAM frei für die Analyse

    for i, (cid, name, t) in enumerate(transcribed, 1):
        yield render(f"Analyse {i}/{len(transcribed)}: {name} …")
        try:
            # Fundstellen für die Dashboard-Schwelle und die eingestellte Länge
            a = fraud.analyze(t["text"], segments=t["segments"], threshold=th, passage_words=passage_words())
            store.save_result(cid, t, a)
            text, color = verdict(store.get_call(cid), th)
            lines.append(f"{badge(text, color)} Anruf {cid} · {html.escape(name)} · Risiko {a['risk']:.0%}")
        except Exception as e: failed(cid, name, e)
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


# ------------------------------------------------------------------ Prüfpunkte (Kev-Fragen)
# Gespeichert wird über den Fraud-Analyse-Dienst (PUT /questions): er prüft die Eingaben, zählt die Version hoch und
# sichert die vorherige Fassung. Neue Prüfpunkte gelten für neu geprüfte Anrufe.

LISTS = ["gesetzlich", "intern"]
NEW = "(neu)"


def checks_table(selected=None):
    """selected: ID des geöffneten Prüfpunkts (wird hinterlegt)."""
    cfg = questions_config()
    rows = [[source, q.get("category", ""), qid, q.get("instructions", ""), q.get("basis", "")]
            for source, qs in cfg["questions"].items() if isinstance(qs, dict) for qid, q in qs.items()]
    head = f"Version {cfg.get('version', 1)} · {len(rows)} Prüfpunkte. Klicken Sie auf einen Prüfpunkt, um ihn zu bearbeiten."
    ids = [r[2] for r in rows]
    return (head, row_table(rows, ["Liste", "Kategorie", "ID", "Frage an das Modell", "Rechtsgrundlage"],
                            ids.index(selected) if selected in ids else None), ids)


def open_check(ids, evt: gr.SelectData):
    if not ids or evt.index[0] >= len(ids): return empty_check()
    qid = ids[evt.index[0]]
    for source, qs in questions_config()["questions"].items():
        if isinstance(qs, dict) and qid in qs:
            q, crit = qs[qid], qs[qid].get("criteria") or {}
            return (qid, source, q.get("category", ""), qid, q.get("basis", ""), q.get("instructions", ""),
                    crit.get("true", ""), crit.get("false", ""), "")
    return empty_check()


def empty_check():
    return NEW, "gesetzlich", "", "", "", "", "", "", ""


def save_check(original, source, category, qid, basis, question, yes, no):
    qid = (qid or "").strip()
    cfg = questions_config()
    questions = {s: dict(qs) for s, qs in cfg["questions"].items() if isinstance(qs, dict)}
    for s in LISTS: questions.setdefault(s, {})
    if original != NEW:                                   # bearbeiten: alten Eintrag entfernen (auch bei neuer ID/Liste)
        for qs in questions.values(): qs.pop(original, None)
    elif any(qid in qs for qs in questions.values()):
        raise gr.Error(f"Die ID '{qid}' gibt es schon.")
    crit = {k: v.strip() for k, v in (("true", yes or ""), ("false", no or "")) if v.strip()}
    questions[source][qid] = {"category": (category or "").strip(), "basis": (basis or "").strip(), "type": "noul",
                              "instructions": (question or "").strip(), **({"criteria": crit} if crit else {})}
    try: res = fraud.save_questions(questions)
    except RuntimeError as e: raise gr.Error(str(e)) from None
    head, df, ids = checks_table(qid)
    return (f'<span style="color:{GREEN}">Gespeichert als Version {res["version"]}. Gilt für neu geprüfte Anrufe.</span>',
            head, df, ids, qid, gr.CheckboxGroup(choices=categories()))


def delete_check(original):
    if original == NEW: raise gr.Error("Erst einen Prüfpunkt in der Tabelle auswählen.")
    questions = {s: {k: v for k, v in qs.items() if k != original} for s, qs in questions_config()["questions"].items() if isinstance(qs, dict)}
    try: res = fraud.save_questions(questions)
    except RuntimeError as e: raise gr.Error(str(e)) from None
    head, df, ids = checks_table()
    return (f'<span style="color:{GREEN}">Prüfpunkt {html.escape(original)} gelöscht (Version {res["version"]}).</span>',
            head, df, ids, *empty_check()[:8], gr.CheckboxGroup(choices=categories()))


# ------------------------------------------------------------------ UI

CSS = """
#wrap { max-width: 1180px; margin: 0 auto; }
/* Tabellen, deren Zeilen man anklickt: Gradio markiert sonst nur die angeklickte Zelle mit einem Rahmen */
.row-table .body-cell.cell-selected { --ring-color: transparent !important; box-shadow: inset 1px 0 0 var(--border-color-primary) !important; }
.row-table .body-cell:focus, .row-table .body-cell:focus-visible { outline: none !important; }   /* Fokus-Rahmen beim Klick */
.row-table .selection-button { display: none !important; }      /* Laschen zum Verschieben der Auswahl */
.row-table .body-cell.flash { animation: none !important; }      /* Gradio färbt sonst die angeklickte Zelle kurz ein */
.row-table .cell-menu-button { display: none !important; }
.row-table tbody tr { cursor: pointer; }
.row-table tbody tr:hover td { background-color: rgba(37, 99, 235, 0.07) !important; }
/* die ganze Zeile sofort beim Klick hinterlegen (ohne auf den Server zu warten); gleiche Farbe wie SELECTED_ROW */
.row-table tbody tr:has(.cell-selected) td { background-color: rgba(37, 99, 235, 0.16) !important; }
"""

with gr.Blocks(title="Anruf-Prüfung") as demo:
    with gr.Column(elem_id="wrap"):
        gr.Markdown("## Anruf-Prüfung")
        status_html = gr.HTML()
        with gr.Tabs():
            with gr.Tab("Anrufe"):
                ids_state, current_id = gr.State([]), gr.State(None)
                with gr.Row(equal_height=True):
                    filter_radio = gr.Radio(FILTERS, value="Alle", label="Anzeigen")
                snapshot_state, refresh_timer = gr.State(""), gr.Timer(REFRESH_SECONDS)   # neue Anrufe erscheinen von selbst
                summary_html = gr.HTML()
                calls_df = gr.Dataframe(interactive=False, wrap=True, elem_classes="row-table")
                gr.Markdown("Klicken Sie auf einen Anruf, um ihn zu öffnen.")
                with gr.Column(visible=False) as detail_col:
                    detail = gr.HTML()
                    with gr.Row():
                        audio = gr.Audio(type="filepath", label="Ganze Aufnahme", interactive=False)
                        with gr.Column():
                            snippet_dd = gr.Dropdown([], label="Fundstelle anhören (mit 10 s davor und danach)")
                            snippet_audio = gr.Audio(type="filepath", label="Ausschnitt", interactive=False)
                    with gr.Row():
                        with gr.Column(scale=3):
                            gr.Markdown("**Transkript** (Abschnitte einer Fundstelle sind markiert)")
                            transcript = gr.HTML()
                        with gr.Column(scale=2):
                            gr.Markdown("**Ihre Beurteilung**")
                            label_radio = gr.Radio([(v, k) for k, v in store.LABELS.items()], label="Liegt ein Verstoss vor?")
                            findings_box = gr.CheckboxGroup([], label="Welche Befunde sind korrekt? (nicht angehakt = falsch)")
                            missed_box = gr.CheckboxGroup(categories(), label="Übersehene Kategorien (Verstoss ohne Befund)")
                            comment_box = gr.Textbox(label="Kommentar", lines=3)
                            name_box = gr.Textbox(label="Ihr Name")
                            save_btn = gr.Button("Beurteilung speichern", variant="primary")
                            saved_html = gr.HTML()

            with gr.Tab("Neue Anrufe prüfen"):
                files_in = gr.File(file_count="multiple", file_types=["audio"], label="Aufnahmen (WAV, MP3, M4A …)")
                start_btn = gr.Button("Prüfung starten", variant="primary")
                progress_html = gr.HTML()

            with gr.Tab("Prüfpunkte"):
                gr.Markdown("Die Fragen, die das Modell zu jedem Anruf beantwortet. Jede Frage ist ein Prüfpunkt; "
                            "erreicht ihr Wert die Alarm-Schwelle, gibt es einen Befund.")
                checks_head = gr.Markdown()
                checks_df = gr.Dataframe(interactive=False, wrap=True, elem_classes="row-table")
                check_ids, check_original = gr.State([]), gr.State(NEW)
                with gr.Row():
                    with gr.Column(scale=1):
                        ck_source = gr.Radio(LISTS, value="gesetzlich", label="Liste")
                        ck_category = gr.Textbox(label="Kategorie", placeholder="z.B. Insiderhandel")
                        ck_id = gr.Textbox(label="ID", placeholder="z.B. insider_trading (Kleinbuchstaben, Ziffern, _)")
                        ck_basis = gr.Textbox(label="Rechtsgrundlage", placeholder="z.B. FinfraG Art. 154 oder interne Policy")
                    with gr.Column(scale=2):
                        ck_question = gr.Textbox(label="Frage an das Modell (Ja/Nein)", lines=3,
                                                 placeholder="Englisch funktioniert am besten, z.B. Does someone reveal a valid access credential?")
                        ck_yes = gr.Textbox(label="„Ja“ bedeutet (optional)", placeholder="leer lassen, wenn die Frage für sich reicht")
                        ck_no = gr.Textbox(label="„Nein“ bedeutet (optional)", placeholder="leer lassen, wenn die Frage für sich reicht")
                with gr.Row():
                    ck_save = gr.Button("Speichern", variant="primary")
                    ck_new = gr.Button("Neuer Prüfpunkt")
                    ck_delete = gr.Button("Löschen", variant="stop")
                ck_msg = gr.HTML()

            with gr.Tab("Einstellungen"):
                gr.Markdown("**Alarm-Schwelle**: Ab welchem Risiko ein Anruf als Alarm markiert wird. "
                            "Tiefer = mehr Alarme, weniger übersehene Fälle. Höher = weniger Fehlalarme.")
                th_slider = gr.Slider(0, 1, step=0.01, label="Alarm ab Risiko")
                th_preview = gr.Markdown()
                th_save = gr.Button("Schwelle speichern", variant="primary")
                th_saved = gr.Markdown()
                gr.Markdown("**Länge der Fundstelle**: Wie viel Text (und Audio) als Fundstelle angezeigt wird. "
                            "Gilt für neu geprüfte Anrufe.")
                pw_slider = gr.Slider(5, 100, step=1, label="Wörter pro Fundstelle")
                pw_save = gr.Button("Länge speichern", variant="primary")
                pw_saved = gr.Markdown()

    list_outputs = [status_html, summary_html, calls_df, ids_state]
    demo.load(refresh, filter_radio, list_outputs).then(lambda: (threshold(), passage_words()), None, [th_slider, pw_slider]) \
        .then(checks_table, None, [checks_head, checks_df, check_ids])
    form = [check_original, ck_source, ck_category, ck_id, ck_basis, ck_question, ck_yes, ck_no, ck_msg]
    checks_df.select(open_check, check_ids, form).then(lambda o: checks_table(o)[1], check_original, checks_df)
    ck_new.click(empty_check, None, form)
    ck_save.click(save_check, [check_original, ck_source, ck_category, ck_id, ck_basis, ck_question, ck_yes, ck_no],
                  [ck_msg, checks_head, checks_df, check_ids, check_original, missed_box])
    ck_delete.click(delete_check, check_original, [ck_msg, checks_head, checks_df, check_ids, *form[:8], missed_box])
    refresh_timer.tick(auto_refresh, [filter_radio, current_id, snapshot_state], [*list_outputs, snapshot_state], show_progress="hidden")
    filter_radio.change(refresh, filter_radio, list_outputs)
    calls_df.select(open_call, [ids_state, filter_radio], [current_id, detail_col, detail, audio, transcript, label_radio, findings_box, missed_box,
                                           comment_box, name_box, snippet_dd, snippet_audio, calls_df])
    snippet_dd.change(play_snippet, [current_id, snippet_dd], snippet_audio)
    save_btn.click(save_label, [current_id, label_radio, findings_box, missed_box, comment_box, name_box, filter_radio],
                   [saved_html, summary_html, calls_df, ids_state])
    start_btn.click(process, files_in, progress_html).then(refresh, filter_radio, list_outputs)
    th_slider.change(preview_threshold, th_slider, th_preview, show_progress="hidden")
    th_save.click(save_threshold, [th_slider, filter_radio], [th_saved, summary_html, calls_df, ids_state])
    pw_save.click(lambda n: (store.set_setting("passage_words", int(n)), f"Gespeichert: **{int(n)} Wörter** pro Fundstelle.")[1],
                  pw_slider, pw_saved)

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=CSS, allowed_paths=[str(store.DATA_DIR)],
                server_name=os.environ.get("DASHBOARD_HOST", "0.0.0.0"), server_port=int(os.environ.get("DASHBOARD_PORT", "7860")))
