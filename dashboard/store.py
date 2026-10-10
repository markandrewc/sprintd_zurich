"""Ablage des Dashboards: SQLite-Datenbank mit Anrufen, Ergebnissen und Labels, Audio-Kopien daneben.

Ordner über DASHBOARD_DATA (Default dashboard/data, nicht im Git).
"""
import json
import os
import sqlite3
import subprocess
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(os.environ.get("DASHBOARD_DATA", Path(__file__).parent / "data")).resolve()
AUDIO_DIR = DATA_DIR / "audio"
SNIPPET_DIR = DATA_DIR / "snippets"
SNIPPET_MARGIN = 10.0   # Sekunden Audio vor und nach einer Fundstelle
DB = DATA_DIR / "calls.db"

LABELS = {"fraud": "Verstoss bestätigt", "no_fraud": "Kein Verstoss", "unclear": "Unklar"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    filename TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    status TEXT NOT NULL,              -- in_arbeit | fertig | fehler
    error TEXT,
    transcript TEXT,
    segments TEXT,                     -- JSON [{start, end, speaker, text}]
    analysis TEXT,                     -- JSON, Antwort von POST /analyze (Fakten mit p, Regeln)
    risk REAL,                         -- nur noch bei Anrufen aus der Zeit der früheren Prüfpunkte
    label TEXT,                        -- fraud | no_fraud | unclear | NULL (noch nicht geprüft)
    label_categories TEXT,             -- JSON [Regelname, ...]: bestätigte und übersehene Regeln
    label_checks TEXT,                 -- JSON {fakt_id: true|false}: Fakt einer ausgelösten Regel stimmt / stimmt nicht
    label_missed TEXT,                 -- JSON [Regelname, ...]: übersehen (kein Alarm, aber Verstoss)
    label_comment TEXT,
    labeled_by TEXT,
    labeled_at TEXT
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def now():
    return datetime.now().isoformat(timespec="seconds")


MIGRATIONS = {"label_checks": "TEXT", "label_missed": "TEXT"}   # Spalten, die ältere Datenbanken noch nicht haben


def connect():
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    have = {r["name"] for r in con.execute("PRAGMA table_info(calls)")}
    for col, typ in MIGRATIONS.items():
        if col not in have: con.execute(f"ALTER TABLE calls ADD COLUMN {col} {typ}")
    return con


def row_to_call(row):
    if row is None: return None
    c = dict(row)
    for key in ("segments", "analysis", "label_categories", "label_checks", "label_missed"):
        c[key] = json.loads(c[key]) if c[key] else None
    return c


def add_call(filename, audio_bytes):
    """Legt den Anruf an und speichert eine Kopie des Audios. -> id."""
    with connect() as con:
        cur = con.execute("INSERT INTO calls (created_at, filename, audio_path, status) VALUES (?, ?, '', 'in_arbeit')", (now(), filename))
        cid = cur.lastrowid
        path = AUDIO_DIR / f"{cid:06d}_{Path(filename).name}"
        path.write_bytes(audio_bytes)
        con.execute("UPDATE calls SET audio_path = ? WHERE id = ?", (str(path), cid))
    return cid


def save_result(cid, transcription, analysis):
    with connect() as con:
        con.execute("UPDATE calls SET status = 'fertig', error = NULL, transcript = ?, segments = ?, analysis = ?, risk = ? WHERE id = ?",
                    (transcription["text"], json.dumps(transcription["segments"], ensure_ascii=False),
                     json.dumps(analysis, ensure_ascii=False), analysis.get("risk"), cid))


def set_status(cid, status):
    with connect() as con:
        con.execute("UPDATE calls SET status = ? WHERE id = ?", (status, cid))


def save_error(cid, message):
    with connect() as con:
        con.execute("UPDATE calls SET status = 'fehler', error = ? WHERE id = ?", (message, cid))


def save_label(cid, label, checks, missed, categories, comment, labeled_by):
    """checks: {fakt_id: stimmt?} für die Fakten der ausgelösten Regeln; missed: übersehene Regeln (Namen);
    categories: alle Regeln mit Verstoss (bestätigte + übersehene)."""
    with connect() as con:
        con.execute("UPDATE calls SET label = ?, label_checks = ?, label_missed = ?, label_categories = ?, label_comment = ?, "
                    "labeled_by = ?, labeled_at = ? WHERE id = ?",
                    (label, json.dumps(checks or {}), json.dumps(missed or [], ensure_ascii=False),
                     json.dumps(categories or [], ensure_ascii=False), comment or "", labeled_by or "", now(), cid))


def get_call(cid):
    with connect() as con:
        return row_to_call(con.execute("SELECT * FROM calls WHERE id = ?", (cid,)).fetchone())


def list_calls():
    with connect() as con:
        return [row_to_call(r) for r in con.execute("SELECT * FROM calls ORDER BY id DESC")]


def get_setting(key, default=None):
    with connect() as con:
        row = con.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_setting(key, value):
    with connect() as con:
        con.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(value)))


def snippet(call, start, end):
    """Audio-Ausschnitt [start - SNIPPET_MARGIN, end + SNIPPET_MARGIN] als WAV (mit ffmpeg, zwischengespeichert). -> Pfad."""
    SNIPPET_DIR.mkdir(parents=True, exist_ok=True)
    a, b = max(0.0, (start or 0.0) - SNIPPET_MARGIN), (end or start or 0.0) + SNIPPET_MARGIN
    out = SNIPPET_DIR / f"{call['id']:06d}_{a:.1f}_{b:.1f}.wav"
    if not out.is_file():
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{a:.2f}", "-to", f"{b:.2f}", "-i", call["audio_path"], str(out)],
                       check=True)
    return str(out)


def delete_call(cid):
    """Löscht den Anruf endgültig: Eintrag (mit Ergebnis und Beurteilung), Audio-Kopie und Ausschnitte."""
    call = get_call(cid)
    if call is None: return False
    with connect() as con:
        con.execute("DELETE FROM calls WHERE id = ?", (cid,))
    Path(call["audio_path"]).unlink(missing_ok=True)
    for f in SNIPPET_DIR.glob(f"{cid:06d}_*"): f.unlink(missing_ok=True)
    return True
