# Finetuning

Die Beurteilungen aus dem Dashboard sind unsere eigenen Labels. Daraus sollen später Trainingsdaten für Kev (und
allenfalls das Transkriptionsmodell) werden.

## Stand

- `export_labels.py` exportiert alle beurteilten Anrufe nach `outputs/finetuning/labels.jsonl`, mit Ja/Nein-Label pro
  Check (Details im Kopf der Datei).
- `synthetic_data_instructions.md` ist die Anweisung für ein LLM, das synthetische Bankgespräche (Schweizer Hochdeutsch)
  erzeugt. Sie verlangt noch Labels für die früheren 15 Prüfpunkte und muss auf die Fakten umgestellt werden. Ausgabe: JSON Lines, ein Gespräch pro Zeile, abgelegt als
  `data/synthetic/batch_<NNN>.jsonl` (im Git). Die spätere Vertonung gehört nach `outputs/synthetic_audio/` (nicht im Git).

## Kev nachtrainieren

```powershell
.venv\Scripts\python.exe -m finetuning.build_dataset     # Beispiele -> outputs/finetuning/kev_train.jsonl, kev_val.jsonl
.venv\Scripts\python.exe -m finetuning.train --name v1   # Delta-Finetuning ab jaredpalmer/kev-4b -> outputs/finetuning/runs/v1
.venv\Scripts\python.exe -m finetuning.evaluate outputs/finetuning/runs/v1   # Kev-4B gegen nachtrainiert, Validierung
```

- **Daten** (`build_dataset.py`): synthetische Gespräche aus `data/synthetic/` und die Beurteilungen aus dem Dashboard,
  mit den Fakten aus `fraud_analysis/facts.json` als Fragen (hierarchische Prüfung: Fakten -> UND-Regeln -> Alarm).
  Pro Gespräch nur die gelabelten Fakten; Fakten mit nur einer Klasse in den Daten werden weggelassen. Der Text wird
  gleich gebaut wie bei der Analyse. 15 % gehen fest in die Validierung.
- **Training** (`train.py`): `kev.train` aus github.com/jaredpalmer/kev (Installation siehe `requirements.txt`), Warmstart
  vom fertigen Kev-4B, Lernrate 2e-5, bf16 und Gradient-Checkpointing für 12 GB. Die GPU muss frei sein.
  `--max_steps 2` ist ein Kurztest.
- **Einsatz**: den Fraud-Dienst mit `KEV_MODEL=outputs/finetuning/runs/<name>` starten.
- **Test**: `python -m finetuning.evaluate <run>` misst auf dem zurückgehaltenen Teil unserer Daten (`kev_val.jsonl`,
  15 %, nie trainiert): pro Fakt und pro Anruf (Regeln gegen Sollurteil).

## Offen

- Mindestmenge an Labels pro Fakt, bevor ein Finetuning sinnvoll ist.
