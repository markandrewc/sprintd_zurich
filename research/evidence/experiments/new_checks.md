# Experiment `new_checks`

keyword_context (window / anchored full), semantic_windows, quote_judge vs the v1 champion set

RQ: RQ7, RQ4 · base profile `gpu-12gb` · split **dev** · baseline `base` · commit bff5dd70d5 · 2026-10-10T05:26:06+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| base | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 |  |
| kwctx_window | 0.67 [0.53, 0.83] | 0.75 [0.60, 0.92] | 26/22 |  |
| kwctx_full | 0.70 [0.55, 0.85] | 0.78 [0.64, 0.93] | 26/22 |  |
| quote_judge | 0.69 [0.53, 0.86] | 0.81 [0.64, 0.96] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.55 | 67% | 50% | 0.62 [0.47, 0.78] |  |
| kwctx_window | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.46 | 67% | 46% | 0.62 [0.47, 0.78] |  |
| kwctx_full | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.38 | 67% | 44% | 0.62 [0.47, 0.78] |  |
| quote_judge | 48 | 0.71 [0.52, 0.87] | 64% | 81% | 55% [30%, 77%] | 19% [0%, 41%] | 0.44 | 83% | 44% | 0.63 [0.50, 0.77] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 48 | 0.67 [0.45, 0.84] | 68% | 65% | 36% [10%, 62%] | 35% [12%, 57%] | 0.10 | 67% | 40% | 0.65 [0.48, 0.81] |  |
| kwctx_window | 48 | 0.69 [0.47, 0.86] | 69% | 69% | 36% [10%, 62%] | 31% [9%, 54%] | 0.00 | 67% | 38% | 0.66 [0.50, 0.83] |  |
| kwctx_full | 48 | 0.69 [0.47, 0.86] | 69% | 69% | 36% [10%, 62%] | 31% [9%, 54%] | 0.00 | 67% | 38% | 0.66 [0.50, 0.83] |  |
| quote_judge | 48 | 0.75 [0.59, 0.88] | 74% | 77% | 32% [14%, 50%] | 23% [4%, 45%] | 0.18 | 83% | 46% | 0.73 [0.61, 0.85] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| base | 36% (!) | 1/4 | 36% | **no** | - |
| kwctx_window | 36% (!) | 1/4 | 36% | **no** | - |
| kwctx_full | 36% (!) | 1/4 | 36% | **no** | - |
| quote_judge | 32% (!) | 0/4 | 32% | **no** | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] |  |
| kwctx_window | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] |  |
| kwctx_full | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] |  |
| quote_judge | 48 | 0.69 [0.55, 0.82] | 54% | 96% | 95% [85%, 100%] | 4% [0%, 12%] | 0.55 | 50% | 33% | 0.50 [0.45, 0.56] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| base | 0.55 | 0.45 | 0.70, 0.85, 0.65, 0.90 (FAR20: 0.95!, 0.95, 1.00!, 0.95!) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | bff5dd70d5 |
| kwctx_window | 0.55 | 0.85 | 0.80, 0.85, 0.80, 0.90 (FAR20: 1.00!, 1.00, 1.00!, 1.00!) | 1.3 | asr 0.1, diarize 0.0, checks 1.1 | 32.9 | 11.1 | 0 | 0 | bff5dd70d5 |
| kwctx_full | 0.55 | 0.70 | 0.70, 0.85, 0.70, 0.90 (FAR20: 1.00!, 1.00, 1.00!, 1.00!) | 2.2 | asr 0.1, diarize 0.0, checks 2.1 | 33.8 | 11.3 | 0 | 0 | bff5dd70d5 |
| quote_judge | 0.55 | 0.90 | 0.70, 0.80, 0.90, 0.90 (FAR20: 0.95!, 0.95!, 1.00!, 0.95!) | 18.5 | asr 0.0, diarize 0.0, checks 18.4 | 34.7 | 10.0 | 0 | 0 | bff5dd70d5 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| base | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| kwctx_window | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| kwctx_full | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| quote_judge | 0.83 / 50% / 0% | 0.50 / 57% / 40% | 0.91 / - / 17% | 0.71 / 45% / 23% | 0.71 / 64% / 15% |

## `kwctx_window` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kwctx_window - base

| metric | base | kwctx_window | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.67 | -0.009 | [-0.060, +0.038] | no detectable difference |
| alarm AUC | 0.77 | 0.75 | -0.016 | [-0.075, +0.028] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kwctx_window - base

| metric | base | kwctx_window | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.55 | 0.46 | -0.090 | [-0.224, +0.029] | no detectable difference |
| false_alarm_rate | 45% | 45% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 50% | 46% | -4pp | [-11pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.62 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-kwctx_window 0, p=1.0; 3-class only-base 2 vs only-kwctx_window 0, p=0.5.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kwctx_window - base

| metric | base | kwctx_window | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.026 | [+0.000, +0.082] | no detectable difference |
| alarm_f1 | 0.10 | 0.00 | -0.095 | [-0.286, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 36% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 35% | 31% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 40% | 38% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.66 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-kwctx_window 1, p=1.0; 3-class only-base 1 vs only-kwctx_window 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kwctx_window - base

| metric | base | kwctx_window | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.63 | +0.000 | [-0.098, +0.115] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 40% | +0pp | [-7pp, +6pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-kwctx_window 0, p=1.0; 3-class only-base 1 vs only-kwctx_window 1, p=1.0.

Flips (cv, 3 calls):

| call | expected | base | kwctx_window | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D02-K2 | alarm | alarm | review | 0.68/0.68 | same | 01:28-01:31 documentation: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es r... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D04-K2 | alarm | alarm | review | 0.82/0.73 | same | 03:34-04:24 splitting: Bevor wir über irgendeinen Aufwand weiterreden, muss ich genau verstehen, was sie von uns verlangen. Sie haben jetzt den möglichen Verkauf von der Fundsannteuer und im Verkauf d... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine potenzielle Übernahme gegeben hat, die noch nicht veröffentlicht wurde. Sie möchte diese Informationen nutzen,... |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.70 | same | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |

## `kwctx_full` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kwctx_full - base

| metric | base | kwctx_full | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.70 | +0.012 | [-0.009, +0.046] | no detectable difference |
| alarm AUC | 0.77 | 0.78 | +0.009 | [-0.009, +0.033] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kwctx_full - base

| metric | base | kwctx_full | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.55 | 0.38 | -0.167 | [-0.283, +0.000] | no detectable difference |
| false_alarm_rate | 45% | 45% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 50% | 44% | -6pp | [-15pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.62 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-kwctx_full 0, p=1.0; 3-class only-base 3 vs only-kwctx_full 0, p=0.25.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kwctx_full - base

| metric | base | kwctx_full | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.026 | [+0.000, +0.082] | no detectable difference |
| alarm_f1 | 0.10 | 0.00 | -0.095 | [-0.286, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 36% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 35% | 31% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 40% | 38% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.66 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-kwctx_full 1, p=1.0; 3-class only-base 1 vs only-kwctx_full 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kwctx_full - base

| metric | base | kwctx_full | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.63 | +0.000 | [-0.154, +0.201] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 40% | +0pp | [-9pp, +12pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-kwctx_full 0, p=1.0; 3-class only-base 2 vs only-kwctx_full 2, p=1.0.

Flips (cv, 3 calls):

| call | expected | base | kwctx_full | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D02-K2 | alarm | alarm | review | 0.68/0.68 | same | 01:28-01:31 documentation: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es r... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D04-K2 | alarm | alarm | review | 0.82/0.73 | same | 03:34-04:24 splitting: Bevor wir über irgendeinen Aufwand weiterreden, muss ich genau verstehen, was sie von uns verlangen. Sie haben jetzt den möglichen Verkauf von der Fundsannteuer und im Verkauf d... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine potenzielle Übernahme gegeben hat, die noch nicht veröffentlicht wurde. Sie möchte diese Informationen nutzen,... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.88/0.80 | same | 02:39-03:02 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen u... | llm_judge: Die Kundenin versucht, eine bestehende Rückzahlbare Verpflichtung (20'000 Franken ihrer Tante) vor der Kreditstelle zu verbergen, indem sie den Wunsch äußert, diese nicht in die Notiz zu ne... |

## `quote_judge` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = quote_judge - base

| metric | base | quote_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.69 | +0.006 | [-0.099, +0.098] | no detectable difference |
| alarm AUC | 0.77 | 0.81 | +0.039 | [-0.036, +0.123] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = quote_judge - base

| metric | base | quote_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.71 | +0.045 | [-0.090, +0.184] | no detectable difference |
| alarm_f1 | 0.55 | 0.44 | -0.107 | [-0.241, +0.019] | no detectable difference |
| false_alarm_rate | 45% | 55% | +9pp | [-14pp, +39pp] | no detectable difference |
| miss_rate | 31% | 19% | -12pp | [-31pp, +8pp] | no detectable difference |
| accuracy | 50% | 44% | -6pp | [-23pp, +10pp] | no detectable difference |
| review_recall | 67% | 83% | +17pp | [-50pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.63 | +0.012 | [-0.150, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-quote_judge 6, p=1.0; 3-class only-base 7 vs only-quote_judge 4, p=0.5488.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = quote_judge - base

| metric | base | quote_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.75 | +0.088 | [-0.052, +0.253] | no detectable difference |
| alarm_f1 | 0.10 | 0.18 | +0.087 | [+0.000, +0.214] | no detectable difference |
| false_alarm_rate | 36% | 32% | -5pp | [-36pp, +27pp] | no detectable difference |
| miss_rate | 35% | 23% | -12pp | [-31pp, +8pp] | no detectable difference |
| accuracy | 40% | 46% | +6pp | [-9pp, +25pp] | no detectable difference |
| review_recall | 67% | 83% | +17pp | [-50pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.73 | +0.080 | [-0.091, +0.263] | no detectable difference |

McNemar exact (calls): flag correct only-base 4 vs only-quote_judge 8, p=0.3877; 3-class only-base 4 vs only-quote_judge 7, p=0.5488.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = quote_judge - base

| metric | base | quote_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.009 | [-0.047, +0.064] | no detectable difference |
| alarm_f1 | 0.63 | 0.55 | -0.086 | [-0.242, +0.054] | no detectable difference |
| false_alarm_rate | 91% | 95% | +5pp | [-13pp, +28pp] | no detectable difference |
| miss_rate | 8% | 4% | -4pp | [-17pp, +9pp] | no detectable difference |
| accuracy | 40% | 33% | -6pp | [-18pp, +5pp] | no detectable difference |
| review_recall | 83% | 50% | -33pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.50 | -0.004 | [-0.107, +0.083] | no detectable difference |

McNemar exact (calls): flag correct only-base 3 vs only-quote_judge 3, p=1.0; 3-class only-base 6 vs only-quote_judge 3, p=0.5078.

Flips (cv, 15 calls):

| call | expected | base | quote_judge | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.43/0.69 | broken | 00:11-00:23 documentation: Ja, danke, ich bin gerade eine Helle, ich habe am Samstag im Internet etwas gestellt und jetzt sehe ich den Betrag zweimal. Ich weiss nicht, ob ich selber etwas doppelt ange... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktives Geheimnis ist oder ob es ... |
| Stufe1_D01-K2 | no_alert | review | alarm | 0.69/0.71 | same | 01:55-02:04 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. - quote_judge:... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D02-K2 | alarm | alarm | review | 0.68/0.75 | same | 01:28-01:39 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mich machen... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.32 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot ... | geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot etwas ändert, und fragt nach den relevanten Informationen. Dies deutet darauf hin, dass sie versucht, Informationen vor der Kreditstel... |
| Stufe1_D04-K2 | alarm | alarm | review | 0.82/0.82 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine potenzielle Übernahme gegeben hat, die noch nicht veröffentlicht wurde. Sie möchte diese Informationen nutzen,... |
| Stufe1_D05-K2 | alarm | no_alert | review | 0.55/0.71 | fixed | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - quote_judge: Die Kundin gibt d... | llm_judge: Der Kunde nennt den Bestätigungscode, der noch gültig ist, im Gespräch. |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.54/0.58 | broken | 03:50-03:59 documentation: Ich habe einen Brief vom letzten Jahr gefunden, muss ich dann noch haben, ich will nicht den falschen Brief brauchen und nachher alles spielen. - quote_judge: Der Kunde erwä... | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.52/0.59 | broken | 03:21-03:51 access: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum Teil. Ve... | llm_judge: Der Kunde spricht den Bestätigungscode 4826001 aus, der Teil des aktiven Anmeldevorgangs ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.54 | fixed | 01:55-02:17 disclosure: Da steht 4242-3242-3232-3232-3232. Wir machen da keine weiteren Zahl abweich am Telefon, für die Rückfrage stelle ich Ihnen den sicheren Kanal bereit und ich notiere den Urspru... | llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.31/0.41 | fixed | 00:58-01:01 documentation: Der Pfeili, ich habe erwartet, dass ich auf dem Telefon etwas schlugge. - geval: Der Kunde erwähnt, dass er einen Pfeil erwartet hat, der ihn zum Browser führt, während der ... | geval: Der Kunde erwähnt, dass er einen Pfeil erwartet hat, der ihn zum Browser führt, während der Advisor darauf hinweist, dass es zwei Ansichten gibt, und dass sie keine geheimen Worte teilen. Dies ... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.34/0.41 | broken | 00:30-00:46 documentation: Ich habe den Zugang noch gar nicht gestartet, ich schaue das abgelaufenen Muster in der Anleitung an, das echte Anmeldenfenster ist zu, es gibt auch keinen Countdown, die Za... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was implizit darauf hindeutet, dass er möglicherweise Informationen vor der Kreditstelle verbirgt. Ob diese Informati... |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.71 | same | 07:55-08:19 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich nehme ... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.36 | broken | 00:23-01:06 disclosure: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie ha... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C20-K3 | review | no_alert | review | 0.53/0.68 | fixed | 01:32-01:37 documentation: Ich habe keinen Betrag im System bestätigt und kenne den Zweck des Planes noch nicht. - quote_judge: Die Kunde sagt, dass sie den Zweck des Plans noch nicht kennt, und dass ... | llm_judge: Die Kunde möchte zwei verschiedene Daten (4000 für heute und 5000 für morgen) vorbeweisen, ohne dass die zugehörigen Unterlagen bereitgestellt wurden. Der Advisor bestätigt dies und wartet ... |
| Stufe3_C20-K4 | review | no_alert | review | 0.31/0.48 | fixed | 01:04-01:14 access: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - geval: Die... | geval: Der Kunde fragt nach den Daten, obwohl seine Berechtigung nicht bestätigt wurde. Der Berater antwortet, ohne die Berechtigung zu überprüfen. |

