# callguard Evaluation - demo-offline

config: demo-offline, threshold: 0.55, calls: 6, filters: limit=6, created: 2026-10-09 23:52:03

## Kennzahlen

Markiert = Alarm oder Prüfen (ein Mensch hört den Anruf an).

| Kennzahl | Wert |
|---|---|
| Anrufe (mit Sollbewertung) | 6 |
| Fehler | 0 |
| Accuracy (3 Klassen) | 67% |
| Fehlalarmquote (harmlos, aber markiert) | 50% (2/4) |
| Verpasste Fälle (markierungswürdig, aber kein Alarm) | 0% (0/2) |
| Markiert: Precision / Recall / F1 | 50% / 100% / 0.67 |
| Nur Alarm: Precision / Recall / F1 | 50% / 100% / 0.67 |
| Soll-Prüffälle eskaliert | 0/0 (davon als Prüfen: 0) |
| Familie getroffen (Soll-Alarme) | 2/2 |
| Arbeitslast: Alarme / Prüfen | 4 / 0 |

## Konfusionsmatrix (Zeilen = Soll, Spalten = Ist)

| Soll \ Ist | alarm | review | no_alert |
|---|---|---|---|
| alarm | 2 | 0 | 0 |
| review | 0 | 0 | 0 |
| no_alert | 2 | 0 | 2 |

## Aufschlüsselung

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| Stufe 1 | 6 | 67% | 50% | 100% | 0.67 | 50% | 0% | 0.67 |
| clean | 3 | 67% | 50% | 100% | 0.67 | 50% | 0% | 0.67 |
| noisy | 3 | 67% | 50% | 100% | 0.67 | 50% | 0% | 0.67 |

## Schwellen-Sweep

| Schwelle | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 | Accuracy |
|---|---|---|---|---|---|---|---|
| 0.20 | 33% | 100% | 0.50 | 100% | 0% | 0.67 | 33% |
| 0.25 | 33% | 100% | 0.50 | 100% | 0% | 0.67 | 33% |
| 0.30 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.35 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.40 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.45 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.50 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.55 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.60 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.65 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.70 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.75 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.80 | 50% | 100% | 0.67 | 50% | 0% | 0.67 | 67% |
| 0.85 | 50% | 100% | 0.67 | 50% | 0% | 0.00 | 33% |
| 0.90 | 50% | 100% | 0.67 | 50% | 0% | 0.00 | 33% |

**Vorschlag:** Schwelle 0.55 maximiert F1 der Markierungen (67%) bei Recall 100% und Fehlalarmquote 50%. Schwellen, die alle oder keinen Anruf markieren wurden nicht berücksichtigt.

## Kreuzvalidierung (Schwelle je Fold nur auf den übrigen Folds gewählt)

| Fold | Schwelle | Anrufe | Dialoge |
|---|---|---|---|
| 0 | 0.60 | 2 | Stufe1_D02 |
| 1 | 0.50 | 2 | Stufe1_D01 |
| 2 | 0.55 | 2 | Stufe1_D03 |

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| out-of-fold | 6 | 67% | 50% | 100% | 0.67 | 50% | 0% | 0.67 |

## Anrufe

| Anruf | Stufe | Rauschen | Soll | Ist | Score | Unsicherheit | Familie | Soll-Familie |  |
|---|---|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | 1 | nein | no_alert | no_alert | 0.12 | 0.28 | trade | numbers | ok |
| Stufe1_D01-K2 | 1 | ja | no_alert | no_alert | 0.12 | 0.28 | trade | numbers | ok |
| Stufe1_D02-K1 | 1 | nein | alarm | alarm | 0.83 | 0.33 | trade | trade | ok |
| Stufe1_D02-K2 | 1 | ja | alarm | alarm | 0.83 | 0.33 | trade | trade | ok |
| Stufe1_D03-K1 | 1 | nein | no_alert | alarm | 0.83 | 0.33 | trade | trade | x |
| Stufe1_D03-K2 | 1 | ja | no_alert | alarm | 0.83 | 0.33 | trade | trade | x |
