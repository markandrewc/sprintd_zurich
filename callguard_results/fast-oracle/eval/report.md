# callguard Evaluation - fast-oracle

config: fast-oracle, threshold: 0.55, calls: 60, filters: -, overrides: asr.type=reference name=fast-oracle, created: 2026-10-09 23:52:10

## Kennzahlen

Markiert = Alarm oder Prüfen (ein Mensch hört den Anruf an).

| Kennzahl | Wert |
|---|---|
| Anrufe (mit Sollbewertung) | 60 |
| Fehler | 0 |
| Accuracy (3 Klassen) | 53% |
| Fehlalarmquote (harmlos, aber markiert) | 7% (2/28) |
| Verpasste Fälle (markierungswürdig, aber kein Alarm) | 75% (24/32) |
| Markiert: Precision / Recall / F1 | 80% / 25% / 0.38 |
| Nur Alarm: Precision / Recall / F1 | 75% / 25% / 0.38 |
| Soll-Prüffälle eskaliert | 0/8 (davon als Prüfen: 0) |
| Familie getroffen (Soll-Alarme) | 12/24 |
| Arbeitslast: Alarme / Prüfen | 8 / 2 |

## Konfusionsmatrix (Zeilen = Soll, Spalten = Ist)

| Soll \ Ist | alarm | review | no_alert |
|---|---|---|---|
| alarm | 6 | 2 | 16 |
| review | 0 | 0 | 8 |
| no_alert | 2 | 0 | 26 |

## Aufschlüsselung

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| Stufe 1 | 20 | 60% | 80% | 67% | 0.73 | 25% | 33% | 0.60 |
| Stufe 2 | 32 | 62% | - | 0% | 0.00 | 0% | 100% | 0.00 |
| Stufe 3 | 8 | 0% | - | 0% | 0.00 | - | 100% | - |
| clean | 30 | 53% | 80% | 25% | 0.38 | 7% | 75% | 0.38 |
| noisy | 30 | 53% | 80% | 25% | 0.38 | 7% | 75% | 0.38 |

## Schwellen-Sweep

| Schwelle | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 | Accuracy |
|---|---|---|---|---|---|---|---|
| 0.20 | 64% | 44% | 0.52 | 29% | 56% | 0.55 | 53% |
| 0.25 | 64% | 44% | 0.52 | 29% | 56% | 0.55 | 53% |
| 0.30 | 64% | 44% | 0.52 | 29% | 56% | 0.55 | 53% |
| 0.35 | 64% | 44% | 0.52 | 29% | 56% | 0.50 | 50% |
| 0.40 | 64% | 44% | 0.52 | 29% | 56% | 0.38 | 43% |
| 0.45 | 64% | 44% | 0.52 | 29% | 56% | 0.38 | 43% |
| 0.50 | 67% | 38% | 0.48 | 21% | 62% | 0.38 | 47% |
| 0.55 | 80% | 25% | 0.38 | 7% | 75% | 0.38 | 53% |
| 0.60 | 80% | 25% | 0.38 | 7% | 75% | 0.27 | 50% |
| 0.65 | 80% | 25% | 0.38 | 7% | 75% | 0.27 | 50% |
| 0.70 | 80% | 25% | 0.38 | 7% | 75% | 0.27 | 50% |
| 0.75 | 75% | 19% | 0.30 | 7% | 81% | 0.27 | 50% |
| 0.80 | 75% | 19% | 0.30 | 7% | 81% | 0.27 | 50% |
| 0.85 | 75% | 19% | 0.30 | 7% | 81% | 0.29 | 50% |
| 0.90 | 75% | 19% | 0.30 | 7% | 81% | 0.00 | 43% |

**Vorschlag:** Schwelle 0.25 maximiert F1 der Markierungen (52%) bei Recall 44% und Fehlalarmquote 29%.

## Kreuzvalidierung (Schwelle je Fold nur auf den übrigen Folds gewählt)

| Fold | Schwelle | Anrufe | Dialoge |
|---|---|---|---|
| 0 | 0.25 | 12 | Stufe1_D04 Stufe2_C08 Stufe2_C09 Stufe2_C11 Stufe2_C15 Stufe2_C16 |
| 1 | 0.25 | 12 | Stufe1_D06 Stufe1_D09 Stufe2_C05 Stufe2_C06 Stufe2_C07 Stufe3_C17 |
| 2 | 0.50 | 12 | Stufe1_D02 Stufe1_D03 Stufe2_C03 Stufe2_C04 Stufe2_C12 Stufe3_C19 |
| 3 | 0.25 | 12 | Stufe1_D01 Stufe1_D07 Stufe1_D08 Stufe2_C10 Stufe2_C13 Stufe3_C20 |
| 4 | 0.25 | 12 | Stufe1_D05 Stufe1_D10 Stufe2_C01 Stufe2_C02 Stufe2_C14 Stufe3_C18 |

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| out-of-fold | 60 | 50% | 60% | 38% | 0.46 | 29% | 62% | 0.48 |

## Anrufe

| Anruf | Stufe | Rauschen | Soll | Ist | Score | Unsicherheit | Familie | Soll-Familie |  |
|---|---|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | 1 | nein | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe1_D01-K2 | 1 | ja | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe1_D02-K1 | 1 | nein | alarm | alarm | 0.88 | 0.30 | trade | trade | ok |
| Stufe1_D02-K2 | 1 | ja | alarm | alarm | 0.88 | 0.30 | trade | trade | ok |
| Stufe1_D03-K1 | 1 | nein | no_alert | alarm | 0.84 | 0.30 | trade | trade | x |
| Stufe1_D03-K2 | 1 | ja | no_alert | alarm | 0.84 | 0.30 | trade | trade | x |
| Stufe1_D04-K1 | 1 | nein | alarm | alarm | 0.88 | 0.30 | trade | trade | ok |
| Stufe1_D04-K2 | 1 | ja | alarm | alarm | 0.88 | 0.30 | trade | trade | ok |
| Stufe1_D05-K1 | 1 | nein | alarm | review | 0.43 | 0.43 | access | access | x |
| Stufe1_D05-K2 | 1 | ja | alarm | review | 0.43 | 0.43 | access | access | x |
| Stufe1_D06-K1 | 1 | nein | no_alert | no_alert | 0.35 | 0.30 | splitting | access | ok |
| Stufe1_D06-K2 | 1 | ja | no_alert | no_alert | 0.35 | 0.30 | splitting | access | ok |
| Stufe1_D07-K1 | 1 | nein | alarm | no_alert | 0.35 | 0.30 | disclosure | disclosure | x |
| Stufe1_D07-K2 | 1 | ja | alarm | no_alert | 0.35 | 0.30 | disclosure | disclosure | x |
| Stufe1_D08-K1 | 1 | nein | no_alert | no_alert | 0.35 | 0.30 | disclosure | disclosure | ok |
| Stufe1_D08-K2 | 1 | ja | no_alert | no_alert | 0.35 | 0.30 | disclosure | disclosure | ok |
| Stufe1_D09-K1 | 1 | nein | alarm | no_alert | 0.35 | 0.30 | documentation | documentation | x |
| Stufe1_D09-K2 | 1 | ja | alarm | no_alert | 0.35 | 0.30 | documentation | documentation | x |
| Stufe1_D10-K1 | 1 | nein | alarm | alarm | 0.58 | 0.30 | splitting | splitting | ok |
| Stufe1_D10-K2 | 1 | ja | alarm | alarm | 0.58 | 0.30 | splitting | splitting | ok |
| Stufe2_C01-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C01-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C02-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C02-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C03-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C03-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C04-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C04-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | numbers | ok |
| Stufe2_C05-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | trade | ok |
| Stufe2_C05-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | trade | ok |
| Stufe2_C06-K3 | 2 | nein | alarm | no_alert | 0.00 | 0.38 | - | trade | x |
| Stufe2_C06-K4 | 2 | ja | alarm | no_alert | 0.00 | 0.38 | - | trade | x |
| Stufe2_C07-K3 | 2 | nein | alarm | no_alert | 0.00 | 0.38 | - | trade | x |
| Stufe2_C07-K4 | 2 | ja | alarm | no_alert | 0.00 | 0.38 | - | trade | x |
| Stufe2_C08-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | trade | ok |
| Stufe2_C08-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | trade | ok |
| Stufe2_C09-K3 | 2 | nein | alarm | no_alert | 0.00 | 0.38 | - | access | x |
| Stufe2_C09-K4 | 2 | ja | alarm | no_alert | 0.00 | 0.38 | - | access | x |
| Stufe2_C10-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | access | ok |
| Stufe2_C10-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | access | ok |
| Stufe2_C11-K3 | 2 | nein | no_alert | no_alert | 0.33 | 0.30 | trade | disclosure | ok |
| Stufe2_C11-K4 | 2 | ja | no_alert | no_alert | 0.33 | 0.30 | trade | disclosure | ok |
| Stufe2_C12-K3 | 2 | nein | alarm | no_alert | 0.33 | 0.30 | trade | disclosure | x |
| Stufe2_C12-K4 | 2 | ja | alarm | no_alert | 0.33 | 0.30 | trade | disclosure | x |
| Stufe2_C13-K3 | 2 | nein | alarm | no_alert | 0.00 | 0.38 | - | documentation | x |
| Stufe2_C13-K4 | 2 | ja | alarm | no_alert | 0.00 | 0.38 | - | documentation | x |
| Stufe2_C14-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | documentation | ok |
| Stufe2_C14-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | documentation | ok |
| Stufe2_C15-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | splitting | ok |
| Stufe2_C15-K4 | 2 | ja | no_alert | no_alert | 0.00 | 0.38 | - | splitting | ok |
| Stufe2_C16-K3 | 2 | nein | alarm | no_alert | 0.00 | 0.38 | - | splitting | x |
| Stufe2_C16-K4 | 2 | ja | alarm | no_alert | 0.00 | 0.38 | - | splitting | x |
| Stufe3_C17-K3 | 3 | nein | review | no_alert | 0.00 | 0.38 | - | access | x |
| Stufe3_C17-K4 | 3 | ja | review | no_alert | 0.00 | 0.38 | - | access | x |
| Stufe3_C18-K3 | 3 | nein | review | no_alert | 0.00 | 0.38 | - | disclosure | x |
| Stufe3_C18-K4 | 3 | ja | review | no_alert | 0.00 | 0.38 | - | disclosure | x |
| Stufe3_C19-K3 | 3 | nein | review | no_alert | 0.00 | 0.38 | - | documentation | x |
| Stufe3_C19-K4 | 3 | ja | review | no_alert | 0.00 | 0.38 | - | documentation | x |
| Stufe3_C20-K3 | 3 | nein | review | no_alert | 0.00 | 0.38 | - | splitting | x |
| Stufe3_C20-K4 | 3 | ja | review | no_alert | 0.00 | 0.38 | - | splitting | x |
