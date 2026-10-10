# Experiment `two_readers_perturbed`

Two readers on re-recorded dev audio (speed 0.96, -3 dB)

RQ: RQ8, RQ10 · base profile `two-readers-perturbed` · split **dev** · baseline `perturbed` · commit 1e21a86ee6 · 2026-10-10T13:23:47+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| perturbed | 0.83 [0.67, 0.96] | 0.89 [0.74, 0.99] | 26/22 | re-fusion of perturbed_src |
| kev | 0.81 [0.60, 0.96] | 0.94 [0.81, 1.00] | 26/22 | re-fusion of perturbed_src |
| r1 | 0.86 [0.72, 0.98] | 0.93 [0.80, 1.00] | 26/22 | re-fusion of perturbed_src |
| r2 | 0.84 [0.65, 0.97] | 0.93 [0.81, 1.00] | 26/22 | re-fusion of perturbed_src |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.76 | 0% | 73% | 0.82 [0.70, 0.93] | re-fusion of perturbed_src |
| kev | 48 | 0.83 [0.63, 0.96] | 95% | 73% | 5% [0%, 15%] | 27% [7%, 50%] | 0.65 | 0% | 65% | 0.84 [0.70, 0.96] | re-fusion of perturbed_src |
| r1 | 48 | 0.82 [0.70, 0.93] | 84% | 81% | 18% [0%, 40%] | 19% [4%, 36%] | 0.62 | 50% | 62% | 0.81 [0.69, 0.93] | re-fusion of perturbed_src |
| r2 | 48 | 0.79 [0.62, 0.92] | 86% | 73% | 14% [0%, 35%] | 27% [5%, 50%] | 0.78 | 0% | 73% | 0.80 [0.67, 0.92] | re-fusion of perturbed_src |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.74 | 33% | 73% | 0.82 [0.70, 0.93] | re-fusion of perturbed_src |
| kev | 48 | 0.83 [0.63, 0.96] | 95% | 73% | 5% [0%, 15%] | 27% [7%, 50%] | 0.65 | 0% | 65% | 0.84 [0.70, 0.96] | re-fusion of perturbed_src |
| r1 | 48 | 0.82 [0.70, 0.93] | 84% | 81% | 18% [0%, 40%] | 19% [4%, 36%] | 0.57 | 50% | 60% | 0.81 [0.69, 0.93] | re-fusion of perturbed_src |
| r2 | 48 | 0.79 [0.62, 0.92] | 86% | 73% | 14% [0%, 35%] | 27% [5%, 50%] | 0.76 | 33% | 73% | 0.80 [0.67, 0.92] | re-fusion of perturbed_src |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| perturbed | 14% | 4/4 | 14% | yes | - |
| kev | 5% | 4/4 | 5% | yes | - |
| r1 | 18% | 3/4 | 18% | yes | - |
| r2 | 14% | 4/4 | 14% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.75 | 50% | 71% | 0.82 [0.70, 0.93] | re-fusion of perturbed_src |
| kev | 48 | 0.65 [0.39, 0.84] | 93% | 50% | 5% [0%, 15%] | 50% [25%, 75%] | 0.62 | 0% | 62% | 0.73 [0.60, 0.86] | re-fusion of perturbed_src |
| r1 | 48 | 0.82 [0.70, 0.93] | 84% | 81% | 18% [0%, 40%] | 19% [4%, 36%] | 0.52 | 50% | 58% | 0.81 [0.69, 0.93] | re-fusion of perturbed_src |
| r2 | 48 | 0.79 [0.62, 0.92] | 86% | 73% | 14% [0%, 35%] | 27% [5%, 50%] | 0.75 | 33% | 69% | 0.80 [0.67, 0.92] | re-fusion of perturbed_src |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 1.00, 0.30, 0.30) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.5 | 0 | 0 | 1e21a86ee6 |
| kev | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.5 | 0 | 0 | 1e21a86ee6 |
| r1 | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 1.00!, 0.30, 0.30) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.5 | 0 | 0 | 1e21a86ee6 |
| r2 | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 0.90, 0.30, 0.30) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.5 | 0 | 0 | 1e21a86ee6 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| perturbed | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.67 / - / 50% | 0.75 / 18% / 31% | 0.88 / 9% / 15% |
| kev | 1.00 / 0% / 0% | 0.90 / 7% / 10% | 0.00 / - / 100% | 0.87 / 0% / 23% | 0.78 / 9% / 31% |
| r1 | 1.00 / 0% / 0% | 0.73 / 29% / 20% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.85 / 18% / 15% |
| r2 | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.50 / - / 67% | 0.75 / 18% / 31% | 0.83 / 9% / 23% |

## `kev` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev - perturbed

| metric | perturbed | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.81 | -0.022 | [-0.176, +0.094] | no detectable difference |
| alarm AUC | 0.89 | 0.94 | +0.048 | [+0.000, +0.120] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev - perturbed

| metric | perturbed | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.83 | +0.010 | [-0.156, +0.139] | no detectable difference |
| alarm_f1 | 0.76 | 0.65 | -0.117 | [-0.429, +0.148] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-25pp, +6pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.84 | +0.026 | [-0.115, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 4 vs only-kev 5, p=1.0; 3-class only-perturbed 8 vs only-kev 4, p=0.3877.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev - perturbed

| metric | perturbed | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.83 | +0.010 | [-0.156, +0.139] | no detectable difference |
| alarm_f1 | 0.74 | 0.65 | -0.092 | [-0.424, +0.168] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-27pp, +8pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.84 | +0.026 | [-0.115, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 4 vs only-kev 5, p=1.0; 3-class only-perturbed 9 vs only-kev 5, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev - perturbed

| metric | perturbed | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.65 | -0.166 | [-0.407, +0.015] | no detectable difference |
| alarm_f1 | 0.75 | 0.62 | -0.129 | [-0.490, +0.167] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 50% | +27pp | [+3pp, +54pp] | **real**: perturbed better |
| accuracy | 71% | 62% | -8pp | [-32pp, +14pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.73 | -0.089 | [-0.225, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 9 vs only-kev 4, p=0.2668; 3-class only-perturbed 9 vs only-kev 5, p=0.424.

Flips (cv, 16 calls):

| call | expected | perturbed | kev | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | alarm | review | 0.87/0.79 | same | 01:02-01:03 access: Und hier steht, der neue Bestätigungskode ist für genau die jetzige Anmeldung gültig. - keywords: Stichwort K10 «Bestätigungscode» (Zugangswörter) – ähnlich: «Bestätigungskode» (94... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die TAN-Ziffern laut vor, obwohl der Berater ihn daran erinnerte, das nicht zu tun. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.96/0.80 | same | 02:44-02:46 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.98) - Die Kunde möchte, dass die Verpflichtung ihrer Tante nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.alarm_1... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.89/0.76 | same | 02:46-02:48 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Der Kunde möchte, dass die Tante nicht auf die Kreditstelle geht und die Herkunft und Pflichtenrichtung nicht erfährt. (Regel: docume... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.88/0.05 | same | 01:04-01:05 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde erklärt, dass er die Zahlung aufteilen will, um die Freigabestellung der ganzen Rechnung zu umgehen. (Regel: splittin... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.97/0.06 | same | 01:39-01:40 splitting: ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | facts: Fakt: Teilbeträge gehören zu einer einzigen Rechnung = ja (0.73) - Die Kundenin erklärt, dass es eine einzige Rechnung für die Maschine ist. (Regel: splitting.alarm_1) |
| Stufe2_C07-K3 | alarm | no_alert | review | 0.16/0.15 | fixed | Prüfen (knapp unter Schwelle): Score 0.15 für 'Insiderhandel' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus B... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | alarm | review | 0.50/0.11 | same | 01:12-01:33 documentation: Der violette Satz sagt, dass dreissigtausend von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, kein privater Kontaktanrat.... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.98) - Regula Bachmann möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht in den Entwurf aufgenommen wird. (Regel: documentation.... |
| Stufe2_C13-K4 | alarm | alarm | review | 0.50/0.12 | same | 08:07-08:34 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machia den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 00:59-01:59 documentation: Bedienen wir mit den violetten Zeilen. Um welche Anlage geht es dort? Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der viol... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation... |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.01 | broken | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.01 | broken | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 mi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K4 | review | alarm | no_alert | 0.50/0.00 | broken | 00:10-00:31 disclosure: Ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann mü... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach der Berechtigung für Auskunft zum Konto ihrer Schwester. (Regel: disclosure.review_2) |

## `r1` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r1 - perturbed

| metric | perturbed | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.86 | +0.030 | [-0.022, +0.092] | no detectable difference |
| alarm AUC | 0.89 | 0.93 | +0.037 | [+0.000, +0.095] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1 - perturbed

| metric | perturbed | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.007 | [+0.000, +0.035] | no detectable difference |
| alarm_f1 | 0.76 | 0.62 | -0.141 | [-0.481, +0.129] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 23% | 19% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 73% | 62% | -10pp | [-29pp, +7pp] | no detectable difference |
| review_recall | 0% | 50% | +50pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.81 | -0.004 | [-0.029, +0.012] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 1 vs only-r1 1, p=1.0; 3-class only-perturbed 8 vs only-r1 3, p=0.2266.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1 - perturbed

| metric | perturbed | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.007 | [+0.000, +0.035] | no detectable difference |
| alarm_f1 | 0.74 | 0.57 | -0.165 | [-0.519, +0.087] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 23% | 19% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 73% | 60% | -12pp | [-28pp, +0pp] | no detectable difference |
| review_recall | 33% | 50% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.81 | -0.004 | [-0.029, +0.012] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 1 vs only-r1 1, p=1.0; 3-class only-perturbed 7 vs only-r1 1, p=0.0703.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1 - perturbed

| metric | perturbed | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.007 | [+0.000, +0.035] | no detectable difference |
| alarm_f1 | 0.75 | 0.52 | -0.232 | [-0.547, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 23% | 19% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 71% | 58% | -12pp | [-27pp, -2pp] | **real**: perturbed better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.81 | -0.004 | [-0.029, +0.012] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 1 vs only-r1 1, p=1.0; 3-class only-perturbed 6 vs only-r1 0, p=0.0312.

Flips (cv, 15 calls):

| call | expected | perturbed | r1 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | alarm | review | 0.87/0.83 | same | 01:21-01:27 access: Warte, ich sage Ihnen den Tandrat. sieben drei eins neun vier zwei - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die TAN-Ziffern laut vor, obwohl der B... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die TAN-Ziffern laut vor, obwohl der Berater ihn daran erinnerte, das nicht zu tun. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.96/0.88 | same | 02:49-02:59 documentation: Nehmen Sie das Darlehen nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - facts: Fakt: ... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.98) - Die Kunde möchte, dass die Verpflichtung ihrer Tante nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.alarm_1... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.89/0.83 | same | 02:55-03:01 documentation: Ich will, dass sie nur Eigenmittel sieht und die Vereinbarung meiner Tante gar nicht erfährt. - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Der Kunde ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Der Kunde möchte, dass die Tante nicht auf die Kreditstelle geht und die Herkunft und Pflichtenrichtung nicht erfährt. (Regel: docume... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.88/0.47 | same | 01:36-01:52 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde erklärt, dass er die Zahlung aufteilen will, um die Freigabestellung der ganzen Rechnung zu umgehen. (Regel: splittin... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.97/0.52 | same | 00:36-00:40 splitting: Es ist eine einzige Rechnung für die eine Maschine. - facts: Fakt: Teilbeträge gehören zu einer einzigen Rechnung = ja (0.73) - Die Kundenin erklärt, dass es eine einzige Rechnu... | facts: Fakt: Teilbeträge gehören zu einer einzigen Rechnung = ja (0.73) - Die Kundenin erklärt, dass es eine einzige Rechnung für die Maschine ist. (Regel: splitting.alarm_1) |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.25 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.00/0.25 | broken | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.50/0.26 | same | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatli... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.50/0.26 | same | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | alarm | review | 0.50/0.31 | same | 01:12-01:33 documentation: Der violette Satz sagt, dass dreissigtausend von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, kein privater Kontaktanrat.... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.98) - Regula Bachmann möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht in den Entwurf aufgenommen wird. (Regel: documentation.... |
| Stufe2_C13-K4 | alarm | alarm | review | 0.50/0.31 | same | 08:07-08:34 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machia den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.50/0.26 | same | 00:59-01:59 documentation: Bedienen wir mit den violetten Zeilen. Um welche Anlage geht es dort? Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der viol... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation... |
| Stufe3_C17-K3 | review | alarm | review | 0.50/0.25 | same | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wer... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | review | 0.50/0.26 | same | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K4 | review | alarm | review | 0.50/0.25 | same | 00:10-00:31 disclosure: Ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann mü... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach der Berechtigung für Auskunft zum Konto ihrer Schwester. (Regel: disclosure.review_2) |

## `r2` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r2 - perturbed

| metric | perturbed | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.84 | +0.011 | [-0.112, +0.125] | no detectable difference |
| alarm AUC | 0.89 | 0.93 | +0.036 | [+0.000, +0.120] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2 - perturbed

| metric | perturbed | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.79 | -0.025 | [-0.097, +0.000] | no detectable difference |
| alarm_f1 | 0.76 | 0.78 | +0.019 | [+0.000, +0.074] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.80 | -0.019 | [-0.062, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 1 vs only-r2 0, p=1.0; 3-class only-perturbed 0 vs only-r2 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2 - perturbed

| metric | perturbed | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.79 | -0.025 | [-0.097, +0.000] | no detectable difference |
| alarm_f1 | 0.74 | 0.76 | +0.020 | [+0.000, +0.078] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.80 | -0.019 | [-0.062, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 1 vs only-r2 0, p=1.0; 3-class only-perturbed 0 vs only-r2 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2 - perturbed

| metric | perturbed | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.79 | -0.025 | [-0.097, +0.000] | no detectable difference |
| alarm_f1 | 0.75 | 0.75 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 71% | 69% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.80 | -0.019 | [-0.062, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 1 vs only-r2 0, p=1.0; 3-class only-perturbed 1 vs only-r2 0, p=1.0.

Flips (cv, 1 calls):

| call | expected | perturbed | r2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe3_C18-K4 | review | alarm | no_alert | 0.50/0.00 | broken | 00:10-00:31 disclosure: Ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann mü... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach der Berechtigung für Auskunft zum Konto ihrer Schwester. (Regel: disclosure.review_2) |

