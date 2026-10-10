# Finetuning

Die Beurteilungen aus dem Dashboard sind unsere eigenen Labels. Daraus sollen später Trainingsdaten für Kev (und
allenfalls das Transkriptionsmodell) werden.

## Stand

- `export_labels.py` exportiert alle beurteilten Anrufe nach `outputs/finetuning/labels.jsonl`, mit Ja/Nein-Label pro
  Check (Details im Kopf der Datei).

## Offen

- Format für das Kev-Training festlegen: Kev wird mit `kev.train` aus github.com/jaredpalmer/kev trainiert
  (LoRA auf Qwen3.5). Die Labels pro Check passen zu Kevs `noul`-Fragen.
- Mindestmenge an Labels pro Check, bevor ein Finetuning sinnvoll ist.
- Trennung Training / Test: Die Inventx-Dialoge bleiben reines Testset.
