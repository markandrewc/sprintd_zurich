# callguard Evaluation - demo-views

config: demo-views, threshold: 0.55, calls: 4, split: all, filters: limit=4, created: 2026-10-10 01:21:47

## Kennzahlen

Markiert = Alarm oder Prüfen (ein Mensch hört den Anruf an).

| Kennzahl | Wert |
|---|---|
| Anrufe (mit Sollbewertung) | 4 |
| Fehler | 0 |
| Accuracy (3 Klassen) | 50% |
| Fehlalarmquote (harmlos, aber markiert) | 0% (0/2) |
| Verpasste Fälle (markierungswürdig, aber kein Alarm) | 0% (0/2) |
| Markiert: Precision / Recall / F1 | 100% / 100% / 1.00 |
| Nur Alarm: Precision / Recall / F1 | - / 0% / 0.00 |
| Soll-Prüffälle eskaliert | 0/0 (davon als Prüfen: 0) |
| Familie getroffen (Soll-Alarme) | 2/2 |
| Arbeitslast: Alarme / Prüfen | 0 / 2 |

## Konfusionsmatrix (Zeilen = Soll, Spalten = Ist)

| Soll \ Ist | alarm | review | no_alert |
|---|---|---|---|
| alarm | 0 | 2 | 0 |
| review | 0 | 0 | 0 |
| no_alert | 0 | 0 | 2 |

## Aufschlüsselung

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| Stufe 1 | 4 | 50% | 100% | 100% | 1.00 | 0% | 0% | 0.00 |
| clean | 2 | 50% | 100% | 100% | 1.00 | 0% | 0% | 0.00 |
| noisy | 2 | 50% | 100% | 100% | 1.00 | 0% | 0% | 0.00 |

## Schwellen-Sweep

| Schwelle | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 | Accuracy |
|---|---|---|---|---|---|---|---|
| 0.20 | 50% | 100% | 0.67 | 100% | 0% | 0.00 | 0% |
| 0.25 | 50% | 100% | 0.67 | 100% | 0% | 0.00 | 0% |
| 0.30 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.35 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.40 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.45 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.50 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.55 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.60 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.65 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.70 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.75 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.80 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.85 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |
| 0.90 | 100% | 100% | 1.00 | 0% | 0% | 0.00 | 50% |

**Vorschlag:** Schwelle 0.60 maximiert F1 der Markierungen (100%) bei Recall 100% und Fehlalarmquote 0%. Schwellen, die alle oder keinen Anruf markieren wurden nicht berücksichtigt.

## Kreuzvalidierung (Schwelle je Fold nur auf den übrigen Folds gewählt)

| Fold | Schwelle | Anrufe | Dialoge |
|---|---|---|---|
| 1 | 0.60 | 2 | Stufe1_D02 |
| 3 | 0.55 | 2 | Stufe1_D01 |

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| out-of-fold | 4 | 50% | 100% | 100% | 1.00 | 0% | 0% | 0.00 |

## Anrufe

| Anruf | Stufe | Rauschen | Soll | Ist | Score | Unsicherheit | Familie | Soll-Familie |  |
|---|---|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | 1 | nein | no_alert | no_alert | 0.11 | 0.30 | trade | numbers | ok |
| Stufe1_D01-K2 | 1 | ja | no_alert | no_alert | 0.11 | 0.30 | trade | numbers | ok |
| Stufe1_D02-K1 | 1 | nein | alarm | review | 0.80 | 0.42 | trade | trade | x |
| Stufe1_D02-K2 | 1 | ja | alarm | review | 0.80 | 0.42 | trade | trade | x |
