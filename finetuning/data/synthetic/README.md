# Trainingsgespräche: batch_<NNN>.jsonl

Format: eine Zeile pro Gespräch, `{"turns": [{"speaker": "bank|kunde", "text"}], "labels": {fakt: bool}, "alarm": bool|null}`.
`labels` enthält nur die Fakten aus ../../../fraud_analysis/facts.json, die für das Gespräch bekannt sind; `alarm` ist das
Sollurteil des Anrufs (null = review oder unbekannt).

| Batch | Quelle | Gespräche | Fakten-Labels |
|---|---|---:|---|
| 003 | ChatGPT nach der Anweisung (15 Prüfpunkte) | 20 | aus den 15 Labels abgeleitet |
| 004 | data/test50 (Team-Generator), hochdeutsche Originaltexte (`turns[].de`) | 50 | Gold-Fakten des Generators (alle Familien) + abgeleitet |
| 005 | inventx-case-study, 30 Skripte, aus dem Schweizerdeutschen übersetzt | 30 | Gold-Fakten aus data/test50/kit/families-v3.json (getestete Familie) + abgeleitet |

Vorrang pro Fakt:
1. Gold-Fakt des Generators (ja/nein). „unklar“ bleibt bewusst ohne Label.
2. Aus den früheren 15 Prüfpunkt-Labels (archive/batch_<NNN>_checks15.jsonl): Prüfpunkt true -> alle Fakten seiner
   Regel true; false -> nur bei Regeln mit einem einzigen Fakt false.
3. Von Hand für die Generator-Gespräche: `advantage_offered` nur in T50-documentation-02-A/B (Brot als Dank, ohne
   Gegenleistung), `beneficiary_hidden` überall nein, `deception_signs` überall nein ausser Stufe1_D06.
4. Folgerung: Fakten, deren Frage einen anderen voraussetzt (z.B. `credential_valid` setzt `credential_read_out`
   voraus), sind nein, wenn die Voraussetzung nein ist.

Die 15-Prüfpunkt-Fassungen bleiben in `archive/` (batch_<NNN>_checks15.jsonl).

`archive/`: batch_001 (ältere Regeln) und batch_002 (9 Prüfpunkte); werden nicht mehr verwendet.
