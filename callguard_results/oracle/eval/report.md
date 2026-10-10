# callguard Evaluation - oracle

config: oracle, threshold: 0.55, calls: 5, filters: calls=Stufe1_D02-K1,Stufe1_D03-K1,Stufe2_C06-K3,Stufe2_C05-K3,Stufe3_C17-K3, created: 2026-10-09 23:39:17, rerendered: from stored result.json (fusion only) to show the failed LLM checks

**Achtung:** In 5 von 5 Anrufen ist mindestens eine Prüfung ausgefallen (geval 5x, llm_judge 5x). Diese Anrufe wurden ohne sie entschieden; die Zahlen messen dann nur die übrigen Prüfungen.

## Kennzahlen

Markiert = Alarm oder Prüfen (ein Mensch hört den Anruf an).

| Kennzahl | Wert |
|---|---|
| Anrufe (mit Sollbewertung) | 5 |
| Fehler | 0 |
| Accuracy (3 Klassen) | 40% |
| Fehlalarmquote (harmlos, aber markiert) | 50% (1/2) |
| Verpasste Fälle (markierungswürdig, aber kein Alarm) | 67% (2/3) |
| Markiert: Precision / Recall / F1 | 50% / 33% / 0.40 |
| Nur Alarm: Precision / Recall / F1 | 50% / 50% / 0.50 |
| Soll-Prüffälle eskaliert | 0/1 (davon als Prüfen: 0) |
| Familie getroffen (Soll-Alarme) | 1/2 |
| Arbeitslast: Alarme / Prüfen | 2 / 0 |

## Konfusionsmatrix (Zeilen = Soll, Spalten = Ist)

| Soll \ Ist | alarm | review | no_alert |
|---|---|---|---|
| alarm | 1 | 0 | 1 |
| review | 0 | 0 | 1 |
| no_alert | 1 | 0 | 1 |

## Aufschlüsselung

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| Stufe 1 | 2 | 50% | 50% | 100% | 0.67 | 100% | 0% | 0.67 |
| Stufe 2 | 2 | 50% | - | 0% | 0.00 | 0% | 100% | 0.00 |
| Stufe 3 | 1 | 0% | - | 0% | 0.00 | - | 100% | - |
| clean | 5 | 40% | 50% | 33% | 0.40 | 50% | 67% | 0.50 |

## Schwellen-Sweep

| Schwelle | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 | Accuracy |
|---|---|---|---|---|---|---|---|
| 0.20 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.25 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.30 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.35 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.40 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.45 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.50 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.55 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.60 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.65 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.70 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.75 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.80 | 50% | 33% | 0.40 | 50% | 67% | 0.50 | 40% |
| 0.85 | 50% | 33% | 0.40 | 50% | 67% | 0.67 | 40% |
| 0.90 | 50% | 33% | 0.40 | 50% | 67% | 0.00 | 20% |

**Vorschlag:** Schwelle 0.85 maximiert F1 der Markierungen (40%) bei Recall 33% und Fehlalarmquote 50%.

## Kreuzvalidierung (Schwelle je Fold nur auf den übrigen Folds gewählt)

| Fold | Schwelle | Anrufe | Dialoge |
|---|---|---|---|
| 0 | 0.55 | 1 | Stufe1_D02 |
| 1 | 0.85 | 1 | Stufe2_C06 |
| 2 | 0.55 | 1 | Stufe1_D03 |
| 3 | 0.85 | 1 | Stufe2_C05 |
| 4 | 0.85 | 1 | Stufe3_C17 |

| Gruppe | n | Accuracy | Precision | Recall | F1 | Fehlalarme | Verpasst | Alarm-F1 |
|---|---|---|---|---|---|---|---|---|
| out-of-fold | 5 | 40% | 50% | 33% | 0.40 | 50% | 67% | 0.50 |

## Anrufe

| Anruf | Stufe | Rauschen | Soll | Ist | Score | Unsicherheit | Familie | Soll-Familie |  |
|---|---|---|---|---|---|---|---|---|---|
| Stufe1_D02-K1 | 1 | nein | alarm | alarm | 0.88 | 0.30 | trade | trade | ok (ohne geval, llm_judge) |
| Stufe1_D03-K1 | 1 | nein | no_alert | alarm | 0.84 | 0.30 | trade | trade | x (ohne geval, llm_judge) |
| Stufe2_C05-K3 | 2 | nein | no_alert | no_alert | 0.00 | 0.38 | - | trade | ok (ohne geval, llm_judge) |
| Stufe2_C06-K3 | 2 | nein | alarm | no_alert | 0.00 | 0.38 | - | trade | x (ohne geval, llm_judge) |
| Stufe3_C17-K3 | 3 | nein | review | no_alert | 0.00 | 0.38 | - | access | x (ohne geval, llm_judge) |
