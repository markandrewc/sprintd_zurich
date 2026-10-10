# Anruf-Prüfung (sprintd Zürich, Inventx-Case)

Bankanrufe auf Schweizerdeutsch automatisch transkribieren, auf Compliance-Verstösse prüfen und im Dashboard
beurteilen. Die Beurteilungen sind Labels für späteres Finetuning.

```
Audio ──► transcription (API :8001) ──► Transkript ──► fraud_analysis (API :8002) ──► Alarm + Gründe
                                                                                         │
                                         dashboard (:7860): ansehen, beurteilen ◄────────┘
                                                │
                                                └──► finetuning: Labels exportieren
```

| Ordner | Inhalt |
|---|---|
| `transcription/` | Schweizerdeutsch → Hochdeutsch (Flix-AI/flix-swissgerman-full). Dienst `api.py`, Batch `batch.py` |
| `fraud_analysis/` | Kev-4B (jaredpalmer/kev-4b) beantwortet die Checks aus `questions.json`. Dienst `api.py` |
| `dashboard/` | Gradio-App für Endnutzer. Daten (SQLite, Audio) in `dashboard/data/` |
| `finetuning/` | Export der Beurteilungen als Trainingsdaten |
| `analysis_ui/` | Entwickler-Oberfläche und Auswertung gegen die Inventx-Sollbewertung |
| `SwissDial/` | TTS für Schweizer Dialekte (Testdaten erzeugen) |

## Starten

```powershell
.\start.ps1             # Transkription, Fraud-Analyse, Dashboard -> http://localhost:7860
.\start.ps1 -Analyse    # zusätzlich die Entwickler-Oberfläche -> http://localhost:7861
```

Einzeln: `.venv\Scripts\python.exe -m transcription.api` (bzw. `fraud_analysis.api`, `dashboard.app`, `analysis_ui.app`).
API-Doku der Dienste: http://127.0.0.1:8001/docs und http://127.0.0.1:8002/docs.

## Konfiguration

- **Checks:** `fraud_analysis/questions.json`, zwei Listen (`gesetzlich`, `intern`). Wird bei jeder Analyse neu gelesen.
- **Alarm-Schwelle:** im Dashboard unter „Einstellungen“.
- **GPU:** Kev braucht ~8 GB, die Transkription ~3 GB. Auf einer 12-GB-Karte passen beide knapp; `ASR_BATCH_SIZE`
  (Default 4) senkt den Bedarf der Transkription.

## Geplante Erweiterungen

Jeder Teil ist ein eigener Dienst bzw. Ordner und soll unabhängig wachsen:

| Erweiterung | Wo | Andockpunkt heute |
|---|---|---|
| Sprechererkennung (Diarization, z.B. Nemotron) | `transcription/` | Abschnitte in der Antwort von `POST /transcribe` (`segments`) bekommen ein Feld `speaker` |
| Lokalisierung: Kev über gleitende Fenster zusätzlich zum Kev über das ganze Transkript | `fraud_analysis/` | `analysis.py` (heute nur ganzes Transkript); die Fundstellen mit Zeitstempel kommen aus den `segments` |
| Finetuning von Kev mit den Dashboard-Labels | `finetuning/` | `export_labels.py` (Ja/Nein pro Check) |

## Installation

Python 3.11, dann `pip install torch --index-url https://download.pytorch.org/whl/cu128` und
`pip install -r requirements.txt`. ffmpeg muss im PATH sein.
