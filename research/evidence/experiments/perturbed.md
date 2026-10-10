# Experiment `perturbed`

champion on re-recorded dev audio (speed 0.96, -3 dB)

RQ: RQ8 · base profile `recommended-perturbed` · split **dev** · baseline `perturbed` · commit 480479c79d (dirty) · 2026-10-10T05:59:03+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| perturbed | 0.83 [0.67, 0.96] | 0.89 [0.74, 0.99] | 26/22 |  |
| table_v3 | 0.88 [0.76, 0.98] | 0.88 [0.72, 0.99] | 26/22 |  |
| s3 | 0.84 [0.67, 0.97] | 0.93 [0.83, 0.99] | 26/22 | re-fusion of perturbed |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.76 | 0% | 73% | 0.82 [0.70, 0.93] |  |
| table_v3 | 48 | 0.86 [0.75, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 33%] | 0.73 | 0% | 73% | 0.85 [0.75, 0.95] |  |
| s3 | 48 | 0.77 [0.58, 0.91] | 68% | 88% | 50% [18%, 79%] | 12% [0%, 30%] | 0.69 | 0% | 48% | 0.69 [0.50, 0.88] | re-fusion of perturbed |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.74 | 33% | 73% | 0.82 [0.70, 0.93] |  |
| table_v3 | 48 | 0.86 [0.75, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 33%] | 0.70 | 33% | 73% | 0.85 [0.75, 0.95] |  |
| s3 | 48 | 0.77 [0.58, 0.91] | 68% | 88% | 50% [18%, 79%] | 12% [0%, 30%] | 0.00 | 50% | 29% | 0.69 [0.50, 0.88] | re-fusion of perturbed |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| perturbed | 14% | 4/4 | 14% | yes | - |
| table_v3 | 14% | 4/4 | 14% | yes | - |
| s3 | 50% (!) | 0/4 | 50% | **no** | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.75 | 50% | 71% | 0.82 [0.70, 0.93] |  |
| table_v3 | 48 | 0.86 [0.75, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 33%] | 0.75 | 83% | 75% | 0.85 [0.75, 0.95] |  |
| s3 | 48 | 0.77 [0.58, 0.91] | 68% | 88% | 50% [18%, 79%] | 12% [0%, 30%] | 0.75 | 50% | 54% | 0.69 [0.50, 0.88] | re-fusion of perturbed |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 1.00, 0.30, 0.30) | 33.4 | asr 14.0, diarize 14.3, checks 5.1 | 5.1 | 21.5 | 0 | 0 | 0320090fc5 |
| table_v3 | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 1.00, 0.30, 0.30) | 6.5 | asr 0.0, diarize 0.0, checks 6.5 | 6.5 | 9.9 | 0 | 0 | 60e402c62e |
| s3 | 0.55 | 0.35 | 0.70, 0.35, 0.35, 0.70 (FAR20: 1.00!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 14.0, diarize 14.3, checks 5.1 | 5.1 | 21.5 | 0 | 0 | 480479c79d |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| perturbed | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.67 / - / 50% | 0.75 / 18% / 31% | 0.88 / 9% / 15% |
| table_v3 | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.91 / - / 17% | 0.80 / 18% / 23% | 0.92 / 9% / 8% |
| s3 | 0.83 / 50% / 0% | 0.74 / 50% / 0% | 0.67 / - / 50% | 0.73 / 55% / 15% | 0.80 / 45% / 8% |

## `table_v3` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = table_v3 - perturbed

| metric | perturbed | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.88 | +0.054 | [+0.000, +0.177] | no detectable difference |
| alarm AUC | 0.89 | 0.88 | -0.014 | [-0.049, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v3 - perturbed

| metric | perturbed | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.86 | +0.046 | [+0.000, +0.160] | no detectable difference |
| alarm_f1 | 0.76 | 0.73 | -0.035 | [-0.119, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 15% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.85 | +0.038 | [+0.000, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 0 vs only-table_v3 2, p=0.5; 3-class only-perturbed 0 vs only-table_v3 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v3 - perturbed

| metric | perturbed | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.86 | +0.046 | [+0.000, +0.160] | no detectable difference |
| alarm_f1 | 0.74 | 0.70 | -0.037 | [-0.126, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 15% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.85 | +0.038 | [+0.000, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 0 vs only-table_v3 2, p=0.5; 3-class only-perturbed 0 vs only-table_v3 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v3 - perturbed

| metric | perturbed | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.86 | +0.046 | [+0.000, +0.160] | no detectable difference |
| alarm_f1 | 0.75 | 0.75 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 15% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 71% | 75% | +4pp | [+0pp, +14pp] | no detectable difference |
| review_recall | 50% | 83% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.85 | +0.038 | [+0.000, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 0 vs only-table_v3 2, p=0.5; 3-class only-perturbed 0 vs only-table_v3 2, p=0.5.

Flips (cv, 2 calls):

| call | expected | perturbed | table_v3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.50 | fixed | 01:07-01:16 splitting: Meine Kollegin hat die Daten so notiert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - facts: Fakt: Im Gespräch offen, o... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.50 | fixed | 01:11-01:17 splitting: Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - facts: Fakt: Im Gespräch offen, ob die Teilbeträge zusammengehören = ja (0... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `s3` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = s3 - perturbed

| metric | perturbed | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.84 | +0.012 | [-0.064, +0.118] | no detectable difference |
| alarm AUC | 0.89 | 0.93 | +0.034 | [-0.021, +0.138] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s3 - perturbed

| metric | perturbed | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.050 | [-0.226, +0.103] | no detectable difference |
| alarm_f1 | 0.76 | 0.69 | -0.076 | [-0.245, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +69pp] | no detectable difference |
| miss_rate | 23% | 12% | -12pp | [-29pp, +0pp] | no detectable difference |
| accuracy | 73% | 48% | -25pp | [-44pp, -8pp] | **real**: perturbed better |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.69 | -0.124 | [-0.318, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 8 vs only-s3 3, p=0.2266; 3-class only-perturbed 12 vs only-s3 0, p=0.0005.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s3 - perturbed

| metric | perturbed | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.050 | [-0.226, +0.103] | no detectable difference |
| alarm_f1 | 0.74 | 0.00 | -0.737 | [-0.898, -0.500] | **real**: perturbed better |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +69pp] | no detectable difference |
| miss_rate | 23% | 12% | -12pp | [-29pp, +0pp] | no detectable difference |
| accuracy | 73% | 29% | -44pp | [-65pp, -23pp] | **real**: perturbed better |
| review_recall | 33% | 50% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.69 | -0.124 | [-0.318, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 8 vs only-s3 3, p=0.2266; 3-class only-perturbed 22 vs only-s3 1, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s3 - perturbed

| metric | perturbed | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.050 | [-0.226, +0.103] | no detectable difference |
| alarm_f1 | 0.75 | 0.75 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +69pp] | no detectable difference |
| miss_rate | 23% | 12% | -12pp | [-29pp, +0pp] | no detectable difference |
| accuracy | 71% | 54% | -17pp | [-38pp, +0pp] | no detectable difference |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.69 | -0.124 | [-0.318, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 8 vs only-s3 3, p=0.2266; 3-class only-perturbed 8 vs only-s3 0, p=0.0078.

Flips (cv, 18 calls):

| call | expected | perturbed | s3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.62 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.39; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.62 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.74; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.62 | broken | «Auskunft an Dritte»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Stichwort K11; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.02/0.62 | broken | «Auskunft an Dritte»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Stichwort K11; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.28 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.28 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.28 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.28 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C07-K3 | alarm | no_alert | review | 0.16/0.28 | fixed | «Insiderhandel (Information und Kaufwunsch)»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Eigener Handelswunsch geäussert» p(ja) = 0.40; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.28 | fixed | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.94; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.28 | fixed | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.98; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.50/0.50 | same | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatli... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.50/0.50 | same | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | alarm | review | 0.50/0.50 | same | 03:38-03:48 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.50/0.50 | same | 03:40-03:50 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | alarm | review | 0.50/0.50 | same | 01:12-01:33 documentation: Der violette Satz sagt, dass dreissigtausend von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, kein privater Kontaktanrat.... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.98) - Regula Bachmann möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht in den Entwurf aufgenommen wird. (Regel: documentation.... |
| Stufe2_C13-K4 | alarm | alarm | review | 0.50/0.50 | same | 08:07-08:34 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machia den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.50/0.50 | same | 00:59-01:59 documentation: Bedienen wir mit den violetten Zeilen. Um welche Anlage geht es dort? Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der viol... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation... |

