# Experiment `qwen38`

Qwen3.8-27B (~3 bit GGUF, llama.cpp) as the facts / general-questions backend, wording probes

RQ: RQ6, RQ10 · base profile `recommended` · split **dev** · baseline `q38_facts` · commit 96ec3da9c3 (dirty) · 2026-10-10T12:54:59+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| q38_facts | 0.85 [0.64, 1.00] | 0.97 [0.89, 1.00] | 26/22 |  |
| q38_general | 0.83 [0.65, 0.96] | 0.86 [0.70, 0.98] | 26/22 |  |
| q38_facts_alone | 0.88 [0.71, 1.00] | 0.99 [0.94, 1.00] | 26/22 | re-fusion of q38_facts |
| q38_general_alone | 0.85 [0.68, 0.97] | 0.88 [0.74, 0.98] | 26/22 | re-fusion of q38_general |
| q38_facts_para | 0.87 [0.66, 1.00] | 0.98 [0.93, 1.00] | 26/22 |  |
| q38_facts_blind | 0.83 [0.63, 0.97] | 0.97 [0.90, 1.00] | 26/22 |  |
| q38_general_para | 0.83 [0.67, 0.96] | 0.89 [0.78, 0.98] | 26/22 |  |
| q38_general_para_alone | 0.87 [0.72, 0.98] | 0.91 [0.80, 0.99] | 26/22 | re-fusion of q38_general_para |
| q38_facts_v3 | 0.85 [0.64, 1.00] | 0.97 [0.89, 1.00] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q38_facts | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.81 | 0% | 77% | 0.85 [0.71, 0.96] |  |
| q38_general | 48 | 0.73 [0.54, 0.88] | 73% | 73% | 32% [6%, 64%] | 27% [6%, 50%] | 0.71 | 0% | 62% | 0.71 [0.52, 0.87] |  |
| q38_facts_alone | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.84 | 0% | 79% | 0.85 [0.71, 0.96] | re-fusion of q38_facts |
| q38_general_alone | 48 | 0.71 [0.52, 0.87] | 67% | 77% | 45% [17%, 73%] | 23% [4%, 43%] | 0.71 | 0% | 58% | 0.66 [0.50, 0.82] | re-fusion of q38_general |
| q38_facts_para | 48 | 0.89 [0.73, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.81 | 0% | 77% | 0.90 [0.79, 1.00] |  |
| q38_facts_blind | 48 | 0.70 [0.40, 0.90] | 100% | 54% | 0% [0%, 0%] | 46% [19%, 75%] | 0.79 | 0% | 73% | 0.77 [0.62, 0.91] |  |
| q38_general_para | 48 | 0.77 [0.56, 0.92] | 86% | 69% | 14% [0%, 36%] | 31% [8%, 56%] | 0.80 | 0% | 73% | 0.78 [0.63, 0.92] |  |
| q38_general_para_alone | 48 | 0.77 [0.56, 0.92] | 86% | 69% | 14% [0%, 36%] | 31% [8%, 56%] | 0.80 | 0% | 73% | 0.78 [0.63, 0.92] | re-fusion of q38_general_para |
| q38_facts_v3 | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.81 | 0% | 77% | 0.85 [0.71, 0.96] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q38_facts | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.74 | 0% | 73% | 0.85 [0.71, 0.96] |  |
| q38_general | 48 | 0.72 [0.50, 0.88] | 75% | 69% | 27% [5%, 56%] | 31% [8%, 56%] | 0.77 | 0% | 65% | 0.71 [0.53, 0.88] |  |
| q38_facts_alone | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.81 | 0% | 77% | 0.85 [0.71, 0.96] | re-fusion of q38_facts |
| q38_general_alone | 48 | 0.72 [0.50, 0.88] | 75% | 69% | 27% [5%, 56%] | 31% [8%, 56%] | 0.77 | 0% | 65% | 0.71 [0.53, 0.88] | re-fusion of q38_general |
| q38_facts_para | 48 | 0.89 [0.73, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.81 | 0% | 77% | 0.90 [0.79, 1.00] |  |
| q38_facts_blind | 48 | 0.70 [0.40, 0.90] | 100% | 54% | 0% [0%, 0%] | 46% [19%, 75%] | 0.79 | 0% | 73% | 0.77 [0.62, 0.91] |  |
| q38_general_para | 48 | 0.78 [0.58, 0.93] | 90% | 69% | 9% [0%, 29%] | 31% [8%, 56%] | 0.80 | 0% | 75% | 0.80 [0.66, 0.93] |  |
| q38_general_para_alone | 48 | 0.78 [0.58, 0.93] | 90% | 69% | 9% [0%, 29%] | 31% [8%, 56%] | 0.80 | 0% | 75% | 0.80 [0.66, 0.93] | re-fusion of q38_general_para |
| q38_facts_v3 | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.74 | 0% | 73% | 0.85 [0.71, 0.96] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| q38_facts | 0% | 4/4 | 0% | yes | - |
| q38_general | 9% | 4/4 | 27% | **no** | - |
| q38_facts_alone | 0% | 4/4 | 0% | yes | - |
| q38_general_alone | 9% | 4/4 | 27% | **no** | - |
| q38_facts_para | 0% | 4/4 | 0% | yes | - |
| q38_facts_blind | 0% | 4/4 | 0% | yes | - |
| q38_general_para | 5% | 4/4 | 9% | yes | - |
| q38_general_para_alone | 5% | 4/4 | 9% | yes | - |
| q38_facts_v3 | 0% | 4/4 | 0% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q38_facts | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.86 | 33% | 81% | 0.85 [0.71, 0.96] |  |
| q38_general | 48 | 0.77 [0.56, 0.93] | 86% | 69% | 14% [0%, 36%] | 31% [8%, 56%] | 0.77 | 0% | 71% | 0.78 [0.62, 0.93] |  |
| q38_facts_alone | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.89 | 33% | 83% | 0.85 [0.71, 0.96] | re-fusion of q38_facts |
| q38_general_alone | 48 | 0.77 [0.56, 0.93] | 86% | 69% | 14% [0%, 36%] | 31% [8%, 56%] | 0.77 | 0% | 71% | 0.78 [0.62, 0.93] | re-fusion of q38_general |
| q38_facts_para | 48 | 0.79 [0.56, 0.94] | 100% | 65% | 0% [0%, 0%] | 35% [11%, 62%] | 0.86 | 33% | 81% | 0.83 [0.69, 0.94] |  |
| q38_facts_blind | 48 | 0.70 [0.40, 0.90] | 100% | 54% | 0% [0%, 0%] | 46% [19%, 75%] | 0.79 | 0% | 73% | 0.77 [0.62, 0.91] |  |
| q38_general_para | 48 | 0.78 [0.58, 0.93] | 90% | 69% | 9% [0%, 29%] | 31% [8%, 56%] | 0.77 | 0% | 73% | 0.80 [0.66, 0.93] |  |
| q38_general_para_alone | 48 | 0.78 [0.58, 0.93] | 90% | 69% | 9% [0%, 29%] | 31% [8%, 56%] | 0.77 | 0% | 73% | 0.80 [0.66, 0.93] | re-fusion of q38_general_para |
| q38_facts_v3 | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.86 | 33% | 81% | 0.85 [0.71, 0.96] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| q38_facts | 0.55 | 0.20 | 0.70, 0.20, 0.20, 0.20 (FAR20: 0.95, 0.20, 0.20, 0.20) | 25.2 | asr 0.0, diarize 0.0, checks 25.2 | 26.3 | 20.0 | 0 | 0 | 96ec3da9c3 |
| q38_general | 0.70 | 0.65 | 0.20, 0.65, 0.65, 0.65 (FAR20: 0.45, 0.65, 0.70, 0.65) | 20.3 | asr 0.0, diarize 0.0, checks 20.3 | 20.4 | 15.0 | 0 | 0 | 96ec3da9c3 |
| q38_facts_alone | 0.55 | 0.20 | 0.70, 0.20, 0.20, 0.20 (FAR20: 0.95, 0.20, 0.20, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 25.2 | 26.2 | 20.0 | 0 | 0 | 96ec3da9c3 |
| q38_general_alone | 0.70 | 0.65 | 0.20, 0.25, 0.65, 0.65 (FAR20: 0.45, 0.65, 0.70, 0.65) | 0.0 | asr 0.0, diarize 0.0, checks 20.3 | 20.3 | 15.0 | 0 | 0 | 96ec3da9c3 |
| q38_facts_para | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 24.6 | asr 0.0, diarize 0.0, checks 24.6 | 24.7 | 20.0 | 0 | 0 | 96ec3da9c3 |
| q38_facts_blind | 0.55 | 0.20 | 0.50, 0.20, 0.20, 0.20 (FAR20: 0.95, 0.20, 0.20, 0.20) | 29.1 | asr 0.0, diarize 0.0, checks 29.1 | 29.2 | 24.0 | 0 | 0 | 96ec3da9c3 |
| q38_general_para | 0.70 | 0.50 | 0.35, 0.50, 0.55, 0.50 (FAR20: 0.50, 0.50, 0.80, 0.50) | 19.4 | asr 0.0, diarize 0.0, checks 19.4 | 19.5 | 15.0 | 0 | 0 | 96ec3da9c3 |
| q38_general_para_alone | 0.70 | 0.50 | 0.35, 0.50, 0.55, 0.50 (FAR20: 0.50, 0.50, 0.80, 0.50) | 0.0 | asr 0.0, diarize 0.0, checks 19.4 | 19.4 | 15.0 | 0 | 0 | 96ec3da9c3 |
| q38_facts_v3 | 0.55 | 0.20 | 0.70, 0.20, 0.20, 0.20 (FAR20: 0.95, 0.20, 0.20, 0.20) | 11.8 | asr 0.0, diarize 0.0, checks 11.8 | 11.9 | 8.0 | 0 | 0 | 96ec3da9c3 |

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| q38_facts | 1.00 / 0% / 0% | 0.75 / 0% / 40% | 0.50 / - / 67% | 0.82 / 0% / 31% | 0.82 / 0% / 31% |
| q38_general | 0.83 / 50% / 0% | 0.70 / 21% / 30% | 0.50 / - / 67% | 0.72 / 27% / 31% | 0.74 / 36% / 23% |
| q38_facts_alone | 1.00 / 0% / 0% | 0.75 / 0% / 40% | 0.50 / - / 67% | 0.82 / 0% / 31% | 0.82 / 0% / 31% |
| q38_general_alone | 0.83 / 50% / 0% | 0.61 / 43% / 30% | 0.67 / - / 50% | 0.74 / 36% / 23% | 0.69 / 55% / 23% |
| q38_facts_para | 1.00 / 0% / 0% | 0.95 / 0% / 10% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.92 / 0% / 15% |
| q38_facts_blind | 0.89 / 0% / 20% | 0.75 / 0% / 40% | 0.00 / - / 100% | 0.70 / 0% / 46% | 0.70 / 0% / 46% |
| q38_general_para | 0.95 / 12% / 0% | 0.67 / 14% / 40% | 0.50 / - / 67% | 0.78 / 9% / 31% | 0.75 / 18% / 31% |
| q38_general_para_alone | 0.95 / 12% / 0% | 0.67 / 14% / 40% | 0.50 / - / 67% | 0.78 / 9% / 31% | 0.75 / 18% / 31% |
| q38_facts_v3 | 1.00 / 0% / 0% | 0.75 / 0% / 40% | 0.50 / - / 67% | 0.82 / 0% / 31% | 0.82 / 0% / 31% |

## `q38_general` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_general - q38_facts

| metric | q38_facts | q38_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.83 | -0.021 | [-0.190, +0.170] | no detectable difference |
| alarm AUC | 0.97 | 0.86 | -0.113 | [-0.261, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general - q38_facts

| metric | q38_facts | q38_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.73 | -0.087 | [-0.297, +0.125] | no detectable difference |
| alarm_f1 | 0.81 | 0.71 | -0.097 | [-0.331, +0.103] | no detectable difference |
| false_alarm_rate | 0% | 32% | +32pp | [+6pp, +64pp] | **real**: q38_facts better |
| miss_rate | 31% | 27% | -4pp | [-36pp, +27pp] | no detectable difference |
| accuracy | 77% | 62% | -15pp | [-28pp, -2pp] | **real**: q38_facts better |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.71 | -0.140 | [-0.325, +0.030] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 11 vs only-q38_general 5, p=0.2101; 3-class only-q38_facts 10 vs only-q38_general 3, p=0.0923.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general - q38_facts

| metric | q38_facts | q38_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.72 | -0.098 | [-0.300, +0.112] | no detectable difference |
| alarm_f1 | 0.74 | 0.77 | +0.026 | [-0.232, +0.306] | no detectable difference |
| false_alarm_rate | 0% | 27% | +27pp | [+5pp, +56pp] | **real**: q38_facts better |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-23pp, +8pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.71 | -0.136 | [-0.304, +0.022] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 10 vs only-q38_general 4, p=0.1796; 3-class only-q38_facts 9 vs only-q38_general 5, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general - q38_facts

| metric | q38_facts | q38_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.052 | [-0.248, +0.153] | no detectable difference |
| alarm_f1 | 0.86 | 0.77 | -0.088 | [-0.301, +0.086] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 81% | 71% | -10pp | [-23pp, +0pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.78 | -0.068 | [-0.199, +0.083] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 7 vs only-q38_general 4, p=0.5488; 3-class only-q38_facts 8 vs only-q38_general 3, p=0.2266.

Flips (cv, 18 calls):

| call | expected | q38_facts | q38_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | alarm | 0.00/0.44 | broken | Alarm: Score 0.44 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | alarm | 0.00/0.33 | broken | Alarm: Score 0.33 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D05-K2 | alarm | review | alarm | 0.79/0.93 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.11 | broken | 00:27-00:28 access: Gut, wir kennen diese zwei Sachen. Für das Passwort sagen Sie mir bitte nur, - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.32 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K4 | alarm | alarm | review | 0.97/0.60 | same | Prüfen (knapp unter Schwelle): Score 0.60 für 'Insiderhandel' liegt zwischen 0.50 und der Schwelle 0.65. | Alarm: Score 0.97 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.03 (max. 0.35). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.02/0.54 | fixed | Prüfen (knapp unter Schwelle): Score 0.54 für 'Zugangsinformation preisgegeben' liegt zwischen 0.50 und der Schwelle 0.65. | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.00/0.59 | broken | Prüfen (knapp unter Schwelle): Score 0.59 für 'Zugangsinformation preisgegeben' liegt zwischen 0.50 und der Schwelle 0.65. | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.94/0.12 | broken | Kein Alarm: höchster Score 0.12 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | Alarm: Score 0.94 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.07 (max. 0.35). |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.91/0.13 | broken | Kein Alarm: höchster Score 0.13 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | Alarm: Score 0.91 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.12 (max. 0.35). |
| Stufe2_C13-K3 | alarm | no_alert | alarm | 0.07/0.92 | fixed | Alarm: Score 0.92 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.06/0.87 | fixed | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.06 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.01/0.93 | broken | Alarm: Score 0.93 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.01/0.88 | broken | Alarm: Score 0.88 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.35 | broken | Kein Alarm: höchster Score 0.35 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.08 | broken | Kein Alarm: höchster Score 0.08 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.98 | fixed | Alarm: Score 0.98 für 'Auskunft an Dritte' >= Schwelle 0.65 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.98 | fixed | Alarm: Score 0.98 für 'Auskunft an Dritte' >= Schwelle 0.65 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |

## `q38_facts_alone` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_facts_alone - q38_facts

| metric | q38_facts | q38_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.88 | +0.035 | [+0.000, +0.103] | no detectable difference |
| alarm AUC | 0.97 | 0.99 | +0.018 | [+0.000, +0.071] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_alone - q38_facts

| metric | q38_facts | q38_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.81 | 0.84 | +0.031 | [+0.000, +0.101] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 77% | 79% | +2pp | [+0pp, +7pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_alone 0, p=1.0; 3-class only-q38_facts 0 vs only-q38_facts_alone 1, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_alone - q38_facts

| metric | q38_facts | q38_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.74 | 0.81 | +0.068 | [+0.000, +0.184] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 73% | 77% | +4pp | [+0pp, +11pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_alone 0, p=1.0; 3-class only-q38_facts 0 vs only-q38_facts_alone 2, p=0.5.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_alone - q38_facts

| metric | q38_facts | q38_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.89 | +0.032 | [+0.000, +0.103] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 81% | 83% | +2pp | [+0pp, +7pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_alone 0, p=1.0; 3-class only-q38_facts 0 vs only-q38_facts_alone 1, p=1.0.

Flips (cv, 1 calls):

| call | expected | q38_facts | q38_facts_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | review | alarm | 0.79/0.85 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - Alarm: Score 0.85 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |

## `q38_general_alone` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_general_alone - q38_facts

| metric | q38_facts | q38_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.85 | -0.001 | [-0.170, +0.192] | no detectable difference |
| alarm AUC | 0.97 | 0.88 | -0.089 | [-0.227, +0.010] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_alone - q38_facts

| metric | q38_facts | q38_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.71 | -0.104 | [-0.298, +0.100] | no detectable difference |
| alarm_f1 | 0.81 | 0.71 | -0.100 | [-0.321, +0.079] | no detectable difference |
| false_alarm_rate | 0% | 45% | +45pp | [+17pp, +73pp] | **real**: q38_facts better |
| miss_rate | 31% | 23% | -8pp | [-36pp, +19pp] | no detectable difference |
| accuracy | 77% | 58% | -19pp | [-36pp, -2pp] | **real**: q38_facts better |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.66 | -0.189 | [-0.341, -0.031] | **real**: q38_facts better |

McNemar exact (calls): flag correct only-q38_facts 13 vs only-q38_general_alone 5, p=0.0963; 3-class only-q38_facts 12 vs only-q38_general_alone 3, p=0.0352.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_alone - q38_facts

| metric | q38_facts | q38_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.72 | -0.098 | [-0.300, +0.112] | no detectable difference |
| alarm_f1 | 0.74 | 0.77 | +0.026 | [-0.232, +0.306] | no detectable difference |
| false_alarm_rate | 0% | 27% | +27pp | [+5pp, +56pp] | **real**: q38_facts better |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-23pp, +8pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.71 | -0.136 | [-0.304, +0.022] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 10 vs only-q38_general_alone 4, p=0.1796; 3-class only-q38_facts 9 vs only-q38_general_alone 5, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_alone - q38_facts

| metric | q38_facts | q38_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.052 | [-0.248, +0.153] | no detectable difference |
| alarm_f1 | 0.86 | 0.77 | -0.088 | [-0.301, +0.086] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 81% | 71% | -10pp | [-23pp, +0pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.78 | -0.068 | [-0.199, +0.083] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 7 vs only-q38_general_alone 4, p=0.5488; 3-class only-q38_facts 8 vs only-q38_general_alone 3, p=0.2266.

Flips (cv, 19 calls):

| call | expected | q38_facts | q38_general_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | alarm | 0.00/0.44 | broken | Alarm: Score 0.44 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | alarm | 0.00/0.33 | broken | Alarm: Score 0.33 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D05-K2 | alarm | review | alarm | 0.79/0.98 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - Alarm: Score 0.98 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.09 | broken | Prüfen (knapp unter Schwelle): Score 0.09 für 'Zugangsinformation preisgegeben' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.32 | broken | Alarm: Score 0.32 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | alarm | 0.00/0.25 | broken | Alarm: Score 0.25 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.11 | broken | Prüfen (knapp unter Schwelle): Score 0.11 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.18 | broken | Prüfen (knapp unter Schwelle): Score 0.18 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.02/0.54 | fixed | Prüfen (knapp unter Schwelle): Score 0.54 für 'Zugangsinformation preisgegeben' liegt zwischen 0.50 und der Schwelle 0.65. | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.00/0.59 | broken | Prüfen (knapp unter Schwelle): Score 0.59 für 'Zugangsinformation preisgegeben' liegt zwischen 0.50 und der Schwelle 0.65. | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.94/0.12 | broken | Kein Alarm: höchster Score 0.12 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | Alarm: Score 0.94 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.07 (max. 0.35). |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.91/0.13 | broken | Kein Alarm: höchster Score 0.13 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | Alarm: Score 0.91 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.12 (max. 0.35). |
| Stufe2_C13-K3 | alarm | no_alert | alarm | 0.07/0.92 | fixed | Alarm: Score 0.92 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.06/0.87 | fixed | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.06 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.01/0.93 | broken | Alarm: Score 0.93 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.01/0.88 | broken | Alarm: Score 0.88 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.08 | broken | Kein Alarm: höchster Score 0.08 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.98 | fixed | Alarm: Score 0.98 für 'Auskunft an Dritte' >= Schwelle 0.65 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.98 | fixed | Alarm: Score 0.98 für 'Auskunft an Dritte' >= Schwelle 0.65 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |

## `q38_facts_para` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_facts_para - q38_facts

| metric | q38_facts | q38_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.87 | +0.017 | [+0.000, +0.069] | no detectable difference |
| alarm AUC | 0.97 | 0.98 | +0.014 | [-0.019, +0.070] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_para - q38_facts

| metric | q38_facts | q38_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.89 | +0.075 | [+0.000, +0.216] | no detectable difference |
| alarm_f1 | 0.81 | 0.81 | +0.000 | [-0.099, +0.092] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 19% | -12pp | [-29pp, +0pp] | no detectable difference |
| accuracy | 77% | 77% | +0pp | [-6pp, +6pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.90 | +0.058 | [+0.000, +0.146] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_para 3, p=0.25; 3-class only-q38_facts 1 vs only-q38_facts_para 1, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_para - q38_facts

| metric | q38_facts | q38_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.89 | +0.075 | [+0.000, +0.216] | no detectable difference |
| alarm_f1 | 0.74 | 0.81 | +0.068 | [-0.076, +0.267] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 19% | -12pp | [-29pp, +0pp] | no detectable difference |
| accuracy | 73% | 77% | +4pp | [-5pp, +16pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.90 | +0.058 | [+0.000, +0.146] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_para 3, p=0.25; 3-class only-q38_facts 1 vs only-q38_facts_para 3, p=0.625.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_para - q38_facts

| metric | q38_facts | q38_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.79 | -0.028 | [-0.095, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [-0.101, +0.097] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 35% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 81% | 81% | +0pp | [-6pp, +6pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.83 | -0.019 | [-0.062, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 1 vs only-q38_facts_para 0, p=1.0; 3-class only-q38_facts 1 vs only-q38_facts_para 1, p=1.0.

Flips (cv, 5 calls):

| call | expected | q38_facts | q38_facts_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | review | alarm | 0.79/0.84 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |
| Stufe1_D10-K2 | alarm | alarm | review | 0.91/0.20 | same | 01:35-01:36 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | keywords: Stichwort K07 «aufteilen» (Aufteilen) |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.01/0.06 | fixed | Prüfen (knapp unter Schwelle): Score 0.06 für 'Zugangsinformation preisgegeben' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.02/0.08 | fixed | Prüfen (knapp unter Schwelle): Score 0.08 für 'Zugangsinformation preisgegeben' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | review | 0.06/0.06 | fixed | Prüfen (knapp unter Schwelle): Score 0.06 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.06 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |

## `q38_facts_blind` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_facts_blind - q38_facts

| metric | q38_facts | q38_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.83 | -0.025 | [-0.139, +0.061] | no detectable difference |
| alarm AUC | 0.97 | 0.97 | +0.004 | [-0.033, +0.052] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_blind - q38_facts

| metric | q38_facts | q38_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.118 | [-0.318, +0.000] | no detectable difference |
| alarm_f1 | 0.81 | 0.79 | -0.023 | [-0.208, +0.128] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 46% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 77% | 73% | -4pp | [-14pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.077 | [-0.188, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 4 vs only-q38_facts_blind 0, p=0.125; 3-class only-q38_facts 2 vs only-q38_facts_blind 0, p=0.5.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_blind - q38_facts

| metric | q38_facts | q38_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.118 | [-0.318, +0.000] | no detectable difference |
| alarm_f1 | 0.74 | 0.79 | +0.045 | [+0.000, +0.151] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 46% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.077 | [-0.188, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 4 vs only-q38_facts_blind 0, p=0.125; 3-class only-q38_facts 0 vs only-q38_facts_blind 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_blind - q38_facts

| metric | q38_facts | q38_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.118 | [-0.318, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.256, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 46% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 81% | 73% | -8pp | [-22pp, +0pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.077 | [-0.188, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 4 vs only-q38_facts_blind 0, p=0.125; 3-class only-q38_facts 4 vs only-q38_facts_blind 0, p=0.125.

Flips (cv, 4 calls):

| call | expected | q38_facts | q38_facts_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.90/0.05 | broken | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - Kein Alarm: höchster Score 0.05 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwell... | keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.92/0.05 | broken | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - Kein Alarm: höchster Score 0.05 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwell... | keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.00 | broken | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.00 | broken | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |

## `q38_general_para` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_general_para - q38_facts

| metric | q38_facts | q38_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.83 | -0.018 | [-0.202, +0.188] | no detectable difference |
| alarm AUC | 0.97 | 0.89 | -0.073 | [-0.178, +0.008] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_para - q38_facts

| metric | q38_facts | q38_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.052 | [-0.248, +0.151] | no detectable difference |
| alarm_f1 | 0.81 | 0.80 | -0.011 | [-0.224, +0.175] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 77% | 73% | -4pp | [-15pp, +5pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.78 | -0.068 | [-0.208, +0.076] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 7 vs only-q38_general_para 4, p=0.5488; 3-class only-q38_facts 5 vs only-q38_general_para 3, p=0.7266.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_para - q38_facts

| metric | q38_facts | q38_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.78 | -0.036 | [-0.229, +0.168] | no detectable difference |
| alarm_f1 | 0.74 | 0.80 | +0.057 | [-0.191, +0.317] | no detectable difference |
| false_alarm_rate | 0% | 9% | +9pp | [+0pp, +29pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 73% | 75% | +2pp | [-9pp, +15pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.045 | [-0.171, +0.095] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 6 vs only-q38_general_para 4, p=0.7539; 3-class only-q38_facts 4 vs only-q38_general_para 5, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_para - q38_facts

| metric | q38_facts | q38_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.78 | -0.036 | [-0.229, +0.168] | no detectable difference |
| alarm_f1 | 0.86 | 0.77 | -0.088 | [-0.301, +0.086] | no detectable difference |
| false_alarm_rate | 0% | 9% | +9pp | [+0pp, +29pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 81% | 73% | -8pp | [-21pp, +2pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.045 | [-0.171, +0.095] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 6 vs only-q38_general_para 4, p=0.7539; 3-class only-q38_facts 7 vs only-q38_general_para 3, p=0.3438.

Flips (cv, 12 calls):

| call | expected | q38_facts | q38_general_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | review | alarm | 0.79/0.93 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.27 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.94/0.02 | broken | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.94 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.07 (max. 0.35). |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.91/0.03 | broken | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.91 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.12 (max. 0.35). |
| Stufe2_C13-K3 | alarm | no_alert | alarm | 0.07/0.85 | fixed | Alarm: Score 0.85 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.06/0.86 | fixed | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.06 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.01/0.93 | broken | Alarm: Score 0.93 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.01/0.80 | broken | Alarm: Score 0.80 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.00 | broken | Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.00 | broken | Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.83 | fixed | Alarm: Score 0.83 für 'Auskunft an Dritte' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.93 | fixed | Alarm: Score 0.93 für 'Auskunft an Dritte' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |

## `q38_general_para_alone` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_general_para_alone - q38_facts

| metric | q38_facts | q38_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.87 | +0.017 | [-0.170, +0.232] | no detectable difference |
| alarm AUC | 0.97 | 0.91 | -0.057 | [-0.158, +0.022] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_para_alone - q38_facts

| metric | q38_facts | q38_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.77 | -0.052 | [-0.248, +0.151] | no detectable difference |
| alarm_f1 | 0.81 | 0.80 | -0.011 | [-0.224, +0.175] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 77% | 73% | -4pp | [-15pp, +5pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.78 | -0.068 | [-0.208, +0.076] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 7 vs only-q38_general_para_alone 4, p=0.5488; 3-class only-q38_facts 5 vs only-q38_general_para_alone 3, p=0.7266.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_para_alone - q38_facts

| metric | q38_facts | q38_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.78 | -0.036 | [-0.229, +0.168] | no detectable difference |
| alarm_f1 | 0.74 | 0.80 | +0.057 | [-0.191, +0.317] | no detectable difference |
| false_alarm_rate | 0% | 9% | +9pp | [+0pp, +29pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 73% | 75% | +2pp | [-9pp, +15pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.045 | [-0.171, +0.095] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 6 vs only-q38_general_para_alone 4, p=0.7539; 3-class only-q38_facts 4 vs only-q38_general_para_alone 5, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_general_para_alone - q38_facts

| metric | q38_facts | q38_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.78 | -0.036 | [-0.229, +0.168] | no detectable difference |
| alarm_f1 | 0.86 | 0.77 | -0.088 | [-0.301, +0.086] | no detectable difference |
| false_alarm_rate | 0% | 9% | +9pp | [+0pp, +29pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-30pp, +30pp] | no detectable difference |
| accuracy | 81% | 73% | -8pp | [-21pp, +2pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.045 | [-0.171, +0.095] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 6 vs only-q38_general_para_alone 4, p=0.7539; 3-class only-q38_facts 7 vs only-q38_general_para_alone 3, p=0.3438.

Flips (cv, 12 calls):

| call | expected | q38_facts | q38_general_para_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | review | alarm | 0.79/0.98 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - Alarm: Score 0.98 für 'Zugangsinformation preisgegeben' >= Schwelle 0.50 bei... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.27 | broken | Prüfen (knapp unter Schwelle): Score 0.27 für 'Zugangsinformation preisgegeben' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.94/0.02 | broken | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.94 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.07 (max. 0.35). |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.91/0.03 | broken | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.91 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.12 (max. 0.35). |
| Stufe2_C13-K3 | alarm | no_alert | alarm | 0.07/0.85 | fixed | Alarm: Score 0.85 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.06/0.86 | fixed | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.06 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.01/0.93 | broken | Alarm: Score 0.93 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.01/0.80 | broken | Alarm: Score 0.80 für 'Relevante Angabe verschweigen' >= Schwelle 0.35 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.00 | broken | Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.00 | broken | Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.83 | fixed | Alarm: Score 0.83 für 'Auskunft an Dritte' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.93 | fixed | Alarm: Score 0.93 für 'Auskunft an Dritte' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |

## `q38_facts_v3` vs `q38_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38_facts_v3 - q38_facts

| metric | q38_facts | q38_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.97 | 0.97 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_v3 - q38_facts

| metric | q38_facts | q38_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.81 | 0.81 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 77% | 77% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_v3 0, p=1.0; 3-class only-q38_facts 0 vs only-q38_facts_v3 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_v3 - q38_facts

| metric | q38_facts | q38_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.74 | 0.74 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_v3 0, p=1.0; 3-class only-q38_facts 0 vs only-q38_facts_v3 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38_facts_v3 - q38_facts

| metric | q38_facts | q38_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 81% | 81% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38_facts 0 vs only-q38_facts_v3 0, p=1.0; 3-class only-q38_facts 0 vs only-q38_facts_v3 0, p=1.0.

No call changes its label (cv).

