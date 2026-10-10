# Experiment `qwen38_q6`

Qwen3.8-27B Q6_K (llama.cpp, A5000 24 GB) as the facts / general-questions backend, wording probes

RQ: RQ6, RQ10 · base profile `recommended` · split **dev** · baseline `q38q6_facts` · commit 34fd1c424f · 2026-10-10T12:06:19+0000 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| q38q6_facts | 0.85 [0.65, 1.00] | 0.97 [0.90, 1.00] | 26/22 |  |
| q38q6_general | 0.86 [0.69, 0.99] | 0.92 [0.81, 1.00] | 26/22 |  |
| q38q6_facts_alone | 0.88 [0.71, 1.00] | 0.98 [0.93, 1.00] | 26/22 | re-fusion of q38q6_facts |
| q38q6_general_alone | 0.88 [0.73, 0.99] | 0.93 [0.83, 1.00] | 26/22 | re-fusion of q38q6_general |
| q38q6_facts_para | 0.86 [0.66, 1.00] | 0.98 [0.93, 1.00] | 26/22 |  |
| q38q6_facts_blind | 0.85 [0.64, 1.00] | 0.97 [0.91, 1.00] | 26/22 |  |
| q38q6_general_para | 0.86 [0.69, 1.00] | 0.94 [0.83, 1.00] | 26/22 |  |
| q38q6_general_para_alone | 0.90 [0.75, 1.00] | 0.94 [0.84, 1.00] | 26/22 | re-fusion of q38q6_general_para |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q38q6_facts | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [7%, 50%] | 0.84 | 0% | 79% | 0.87 [0.75, 0.97] |  |
| q38q6_general | 48 | 0.80 [0.65, 0.92] | 76% | 85% | 32% [10%, 58%] | 15% [0%, 33%] | 0.84 | 17% | 71% | 0.76 [0.61, 0.90] |  |
| q38q6_facts_alone | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [7%, 50%] | 0.84 | 0% | 79% | 0.87 [0.75, 0.97] | re-fusion of q38q6_facts |
| q38q6_general_alone | 48 | 0.81 [0.67, 0.94] | 79% | 85% | 27% [5%, 55%] | 15% [0%, 33%] | 0.84 | 17% | 73% | 0.79 [0.63, 0.93] | re-fusion of q38q6_general |
| q38q6_facts_para | 48 | 0.89 [0.74, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.74 | 0% | 73% | 0.90 [0.79, 1.00] |  |
| q38q6_facts_blind | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [6%, 50%] | 0.81 | 0% | 77% | 0.87 [0.75, 0.97] |  |
| q38q6_general_para | 48 | 0.84 [0.68, 0.96] | 88% | 81% | 14% [0%, 36%] | 19% [0%, 41%] | 0.86 | 0% | 77% | 0.84 [0.69, 0.96] |  |
| q38q6_general_para_alone | 48 | 0.86 [0.73, 0.98] | 88% | 85% | 14% [0%, 36%] | 15% [0%, 36%] | 0.84 | 0% | 77% | 0.85 [0.72, 0.97] | re-fusion of q38q6_general_para |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q38q6_facts | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [7%, 50%] | 0.78 | 0% | 75% | 0.87 [0.75, 0.97] |  |
| q38q6_general | 48 | 0.75 [0.59, 0.89] | 74% | 77% | 32% [10%, 58%] | 23% [4%, 43%] | 0.81 | 17% | 69% | 0.73 [0.58, 0.87] |  |
| q38q6_facts_alone | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [7%, 50%] | 0.78 | 0% | 75% | 0.87 [0.75, 0.97] | re-fusion of q38q6_facts |
| q38q6_general_alone | 48 | 0.77 [0.60, 0.91] | 77% | 77% | 27% [5%, 55%] | 23% [4%, 43%] | 0.81 | 17% | 71% | 0.75 [0.60, 0.89] | re-fusion of q38q6_general |
| q38q6_facts_para | 48 | 0.89 [0.74, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.74 | 0% | 73% | 0.90 [0.79, 1.00] |  |
| q38q6_facts_blind | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [6%, 50%] | 0.81 | 0% | 77% | 0.87 [0.75, 0.97] |  |
| q38q6_general_para | 48 | 0.84 [0.68, 0.96] | 88% | 81% | 14% [0%, 36%] | 19% [0%, 41%] | 0.86 | 0% | 77% | 0.84 [0.69, 0.96] |  |
| q38q6_general_para_alone | 48 | 0.84 [0.68, 0.96] | 88% | 81% | 14% [0%, 36%] | 19% [0%, 41%] | 0.86 | 0% | 77% | 0.84 [0.69, 0.96] | re-fusion of q38q6_general_para |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| q38q6_facts | 0% | 4/4 | 0% | yes | - |
| q38q6_general | 5% | 4/4 | 32% | **no** | - |
| q38q6_facts_alone | 0% | 4/4 | 0% | yes | - |
| q38q6_general_alone | 5% | 4/4 | 27% | **no** | - |
| q38q6_facts_para | 0% | 4/4 | 0% | yes | - |
| q38q6_facts_blind | 0% | 4/4 | 0% | yes | - |
| q38q6_general_para | 9% | 4/4 | 14% | yes | - |
| q38q6_general_para_alone | 9% | 4/4 | 14% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| q38q6_facts | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [7%, 50%] | 0.89 | 33% | 83% | 0.87 [0.75, 0.97] |  |
| q38q6_general | 48 | 0.79 [0.62, 0.93] | 86% | 73% | 14% [0%, 36%] | 27% [6%, 50%] | 0.77 | 0% | 71% | 0.80 [0.65, 0.93] |  |
| q38q6_facts_alone | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [7%, 50%] | 0.89 | 33% | 83% | 0.87 [0.75, 0.97] | re-fusion of q38q6_facts |
| q38q6_general_alone | 48 | 0.79 [0.62, 0.93] | 86% | 73% | 14% [0%, 36%] | 27% [6%, 50%] | 0.77 | 0% | 71% | 0.80 [0.65, 0.93] | re-fusion of q38q6_general |
| q38q6_facts_para | 48 | 0.82 [0.59, 0.96] | 100% | 69% | 0% [0%, 0%] | 31% [8%, 58%] | 0.79 | 33% | 77% | 0.85 [0.71, 0.96] |  |
| q38q6_facts_blind | 48 | 0.84 [0.67, 0.97] | 100% | 73% | 0% [0%, 0%] | 27% [6%, 50%] | 0.82 | 33% | 79% | 0.87 [0.75, 0.97] |  |
| q38q6_general_para | 48 | 0.81 [0.63, 0.95] | 90% | 73% | 9% [0%, 29%] | 27% [6%, 50%] | 0.79 | 17% | 75% | 0.82 [0.69, 0.95] |  |
| q38q6_general_para_alone | 48 | 0.81 [0.63, 0.95] | 90% | 73% | 9% [0%, 29%] | 27% [6%, 50%] | 0.79 | 17% | 75% | 0.82 [0.69, 0.95] | re-fusion of q38q6_general_para |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| q38q6_facts | 0.55 | 0.25 | 0.70, 0.25, 0.25, 0.25 (FAR20: 0.95, 0.25, 0.25, 0.25) | 133.3 | asr 0.0, diarize 0.0, checks 133.2 | 135.6 | 20.0 | 0 | 0 | 191690b426 |
| q38q6_general | 0.70 | 0.30 | 0.25, 0.30, 0.30, 0.30 (FAR20: 0.25, 0.30, 0.30, 0.70) | 102.6 | asr 0.0, diarize 0.0, checks 102.5 | 102.6 | 15.0 | 0 | 0 | 191690b426 |
| q38q6_facts_alone | 0.55 | 0.25 | 0.70, 0.25, 0.25, 0.25 (FAR20: 1.00, 0.25, 0.25, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 133.2 | 135.5 | 20.0 | 0 | 0 | 191690b426 |
| q38q6_general_alone | 0.70 | 0.30 | 0.25, 0.30, 0.30, 0.30 (FAR20: 0.25, 0.30, 0.30, 0.70) | 0.0 | asr 0.0, diarize 0.0, checks 102.5 | 102.5 | 15.0 | 0 | 0 | 191690b426 |
| q38q6_facts_para | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 139.8 | asr 0.0, diarize 0.0, checks 139.7 | 139.8 | 20.0 | 0 | 0 | 34fd1c424f |
| q38q6_facts_blind | 0.55 | 0.25 | 0.70, 0.25, 0.25, 0.25 (FAR20: 0.95, 0.25, 0.25, 0.25) | 160.1 | asr 0.0, diarize 0.0, checks 160.0 | 160.1 | 24.0 | 0 | 0 | 34fd1c424f |
| q38q6_general_para | 0.70 | 0.25 | 0.25, 0.25, 0.30, 0.25 (FAR20: 0.25, 0.25, 0.30, 0.25) | 101.9 | asr 0.0, diarize 0.0, checks 101.9 | 101.9 | 15.0 | 0 | 0 | 34fd1c424f |
| q38q6_general_para_alone | 0.70 | 0.25 | 0.25, 0.25, 0.25, 0.25 (FAR20: 0.25, 0.25, 0.30, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 101.9 | 101.9 | 15.0 | 0 | 0 | 34fd1c424f |

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| q38q6_facts | 1.00 / 0% / 0% | 0.82 / 0% / 30% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.82 / 0% / 31% |
| q38q6_general | 0.87 / 38% / 0% | 0.78 / 29% / 10% | 0.67 / - / 50% | 0.85 / 18% / 15% | 0.76 / 45% / 15% |
| q38q6_facts_alone | 1.00 / 0% / 0% | 0.82 / 0% / 30% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.82 / 0% / 31% |
| q38q6_general_alone | 0.91 / 25% / 0% | 0.78 / 29% / 10% | 0.67 / - / 50% | 0.85 / 18% / 15% | 0.79 / 36% / 15% |
| q38q6_facts_para | 1.00 / 0% / 0% | 0.95 / 0% / 10% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.92 / 0% / 15% |
| q38q6_facts_blind | 0.89 / 0% / 20% | 0.95 / 0% / 10% | 0.50 / - / 67% | 0.82 / 0% / 31% | 0.87 / 0% / 23% |
| q38q6_general_para | 1.00 / 0% / 0% | 0.82 / 21% / 10% | 0.50 / - / 67% | 0.83 / 9% / 23% | 0.85 / 18% / 15% |
| q38q6_general_para_alone | 1.00 / 0% / 0% | 0.87 / 21% / 0% | 0.50 / - / 67% | 0.88 / 9% / 15% | 0.85 / 18% / 15% |

## `q38q6_general` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_general - q38q6_facts

| metric | q38q6_facts | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.86 | +0.010 | [-0.137, +0.197] | no detectable difference |
| alarm AUC | 0.97 | 0.92 | -0.052 | [-0.159, +0.030] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general - q38q6_facts

| metric | q38q6_facts | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.80 | -0.044 | [-0.170, +0.113] | no detectable difference |
| alarm_f1 | 0.84 | 0.84 | -0.005 | [-0.157, +0.150] | no detectable difference |
| false_alarm_rate | 0% | 32% | +32pp | [+10pp, +58pp] | **real**: q38q6_facts better |
| miss_rate | 27% | 15% | -12pp | [-32pp, +5pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-20pp, +2pp] | no detectable difference |
| review_recall | 0% | 17% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.76 | -0.101 | [-0.239, +0.024] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 8 vs only-q38q6_general 4, p=0.3877; 3-class only-q38q6_facts 8 vs only-q38q6_general 4, p=0.3877.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general - q38q6_facts

| metric | q38q6_facts | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.75 | -0.090 | [-0.256, +0.090] | no detectable difference |
| alarm_f1 | 0.78 | 0.81 | +0.032 | [-0.190, +0.281] | no detectable difference |
| false_alarm_rate | 0% | 32% | +32pp | [+10pp, +58pp] | **real**: q38q6_facts better |
| miss_rate | 27% | 23% | -4pp | [-30pp, +20pp] | no detectable difference |
| accuracy | 75% | 69% | -6pp | [-21pp, +9pp] | no detectable difference |
| review_recall | 0% | 17% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.73 | -0.140 | [-0.277, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 10 vs only-q38q6_general 4, p=0.1796; 3-class only-q38q6_facts 9 vs only-q38q6_general 6, p=0.6072.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general - q38q6_facts

| metric | q38q6_facts | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.79 | -0.053 | [-0.225, +0.132] | no detectable difference |
| alarm_f1 | 0.89 | 0.77 | -0.120 | [-0.321, +0.023] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-29pp, +27pp] | no detectable difference |
| accuracy | 83% | 71% | -12pp | [-24pp, -2pp] | **real**: q38q6_facts better |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.80 | -0.068 | [-0.205, +0.077] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 7 vs only-q38q6_general 4, p=0.5488; 3-class only-q38q6_facts 8 vs only-q38q6_general 2, p=0.1094.

Flips (cv, 15 calls):

| call | expected | q38q6_facts | q38q6_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.11 | broken | Prüfen (knapp unter Schwelle): Score 0.11 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.12 | broken | Prüfen (knapp unter Schwelle): Score 0.12 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.11 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.01/0.27 | broken | Prüfen (knapp unter Schwelle): Score 0.27 für 'Zugangsinformation preisgegeben' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.03/0.64 | fixed | Alarm: Score 0.64 für 'Zugangsinformation preisgegeben' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.01/0.55 | broken | Alarm: Score 0.55 für 'Zugangsinformation preisgegeben' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C12-K4 | alarm | alarm | review | 0.97/0.19 | same | Prüfen (knapp unter Schwelle): Score 0.19 für 'Auskunft an Dritte' liegt zwischen 0.15 und der Schwelle 0.30. | Alarm: Score 0.97 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.04 (max. 0.35). |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.93 | same | Alarm: Score 0.93 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Prüfen (offener Sachverhalt): facts bewertet 'Relevante Angabe verschweigen' als unbestimmt (Score 0.50 >= 0.25). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.11/0.92 | fixed | Alarm: Score 0.92 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.04/0.95 | broken | Alarm: Score 0.95 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.03/0.73 | broken | Alarm: Score 0.73 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | review | 0.50/0.16 | same | Prüfen (knapp unter Schwelle): Score 0.16 für 'Zugangsinformation preisgegeben' liegt zwischen 0.15 und der Schwelle 0.30. | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.03 | broken | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.15 (Schwelle 0.30 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.77 | fixed | Alarm: Score 0.77 für 'Auskunft an Dritte' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.96 | fixed | Alarm: Score 0.96 für 'Auskunft an Dritte' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `q38q6_facts_alone` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_facts_alone - q38q6_facts

| metric | q38q6_facts | q38q6_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.88 | +0.028 | [+0.000, +0.087] | no detectable difference |
| alarm AUC | 0.97 | 0.98 | +0.011 | [+0.000, +0.048] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_alone - q38q6_facts

| metric | q38q6_facts | q38q6_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 0 vs only-q38q6_facts_alone 0, p=1.0; 3-class only-q38q6_facts 0 vs only-q38q6_facts_alone 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_alone - q38q6_facts

| metric | q38q6_facts | q38q6_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.78 | 0.78 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 75% | 75% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 0 vs only-q38q6_facts_alone 0, p=1.0; 3-class only-q38q6_facts 0 vs only-q38q6_facts_alone 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_alone - q38q6_facts

| metric | q38q6_facts | q38q6_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.89 | 0.89 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 0 vs only-q38q6_facts_alone 0, p=1.0; 3-class only-q38q6_facts 0 vs only-q38q6_facts_alone 0, p=1.0.

No call changes its label (cv).

## `q38q6_general_alone` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_general_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.88 | +0.029 | [-0.119, +0.220] | no detectable difference |
| alarm AUC | 0.97 | 0.93 | -0.039 | [-0.135, +0.032] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.81 | -0.030 | [-0.155, +0.121] | no detectable difference |
| alarm_f1 | 0.84 | 0.84 | -0.005 | [-0.157, +0.150] | no detectable difference |
| false_alarm_rate | 0% | 27% | +27pp | [+5pp, +55pp] | **real**: q38q6_facts better |
| miss_rate | 27% | 15% | -12pp | [-32pp, +5pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-17pp, +2pp] | no detectable difference |
| review_recall | 0% | 17% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.79 | -0.079 | [-0.220, +0.047] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 7 vs only-q38q6_general_alone 4, p=0.5488; 3-class only-q38q6_facts 7 vs only-q38q6_general_alone 4, p=0.5488.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.77 | -0.075 | [-0.239, +0.103] | no detectable difference |
| alarm_f1 | 0.78 | 0.81 | +0.032 | [-0.190, +0.281] | no detectable difference |
| false_alarm_rate | 0% | 27% | +27pp | [+5pp, +55pp] | **real**: q38q6_facts better |
| miss_rate | 27% | 23% | -4pp | [-30pp, +20pp] | no detectable difference |
| accuracy | 75% | 71% | -4pp | [-19pp, +11pp] | no detectable difference |
| review_recall | 0% | 17% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.75 | -0.117 | [-0.258, +0.025] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 9 vs only-q38q6_general_alone 4, p=0.2668; 3-class only-q38q6_facts 8 vs only-q38q6_general_alone 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.79 | -0.053 | [-0.225, +0.132] | no detectable difference |
| alarm_f1 | 0.89 | 0.77 | -0.120 | [-0.321, +0.023] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-29pp, +27pp] | no detectable difference |
| accuracy | 83% | 71% | -12pp | [-24pp, -2pp] | **real**: q38q6_facts better |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.80 | -0.068 | [-0.205, +0.077] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 7 vs only-q38q6_general_alone 4, p=0.5488; 3-class only-q38q6_facts 8 vs only-q38q6_general_alone 2, p=0.1094.

Flips (cv, 14 calls):

| call | expected | q38q6_facts | q38q6_general_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.11 | broken | Prüfen (knapp unter Schwelle): Score 0.11 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.12 | broken | Prüfen (knapp unter Schwelle): Score 0.12 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.01/0.27 | broken | Prüfen (knapp unter Schwelle): Score 0.27 für 'Zugangsinformation preisgegeben' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.03/0.64 | fixed | Alarm: Score 0.64 für 'Zugangsinformation preisgegeben' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.01/0.55 | broken | Alarm: Score 0.55 für 'Zugangsinformation preisgegeben' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C12-K4 | alarm | alarm | review | 0.97/0.19 | same | Prüfen (knapp unter Schwelle): Score 0.19 für 'Auskunft an Dritte' liegt zwischen 0.15 und der Schwelle 0.30. | Alarm: Score 0.97 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.04 (max. 0.35). |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.93 | same | Alarm: Score 0.93 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Prüfen (offener Sachverhalt): facts bewertet 'Relevante Angabe verschweigen' als unbestimmt (Score 0.50 >= 0.25). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.11/0.92 | fixed | Alarm: Score 0.92 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.04/0.95 | broken | Alarm: Score 0.95 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.03/0.73 | broken | Alarm: Score 0.73 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | review | 0.50/0.16 | same | Prüfen (knapp unter Schwelle): Score 0.16 für 'Zugangsinformation preisgegeben' liegt zwischen 0.15 und der Schwelle 0.30. | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.03 | broken | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.15 (Schwelle 0.30 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.77 | fixed | Alarm: Score 0.77 für 'Auskunft an Dritte' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.96 | fixed | Alarm: Score 0.96 für 'Auskunft an Dritte' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `q38q6_facts_para` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_facts_para - q38q6_facts

| metric | q38q6_facts | q38q6_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.86 | +0.012 | [+0.000, +0.044] | no detectable difference |
| alarm AUC | 0.97 | 0.98 | +0.011 | [-0.007, +0.043] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_para - q38q6_facts

| metric | q38q6_facts | q38q6_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.89 | +0.049 | [+0.000, +0.133] | no detectable difference |
| alarm_f1 | 0.84 | 0.74 | -0.099 | [-0.280, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 19% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-17pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.90 | +0.038 | [+0.000, +0.091] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 0 vs only-q38q6_facts_para 2, p=0.5; 3-class only-q38q6_facts 3 vs only-q38q6_facts_para 0, p=0.25.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_para - q38q6_facts

| metric | q38q6_facts | q38q6_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.89 | +0.049 | [+0.000, +0.133] | no detectable difference |
| alarm_f1 | 0.78 | 0.74 | -0.035 | [-0.114, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 19% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 75% | 73% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.90 | +0.038 | [+0.000, +0.091] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 0 vs only-q38q6_facts_para 2, p=0.5; 3-class only-q38q6_facts 1 vs only-q38q6_facts_para 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_para - q38q6_facts

| metric | q38q6_facts | q38q6_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.026 | [-0.098, +0.000] | no detectable difference |
| alarm_f1 | 0.89 | 0.79 | -0.101 | [-0.290, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 31% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 83% | 77% | -6pp | [-17pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.85 | -0.019 | [-0.062, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 1 vs only-q38q6_facts_para 0, p=1.0; 3-class only-q38q6_facts 3 vs only-q38q6_facts_para 0, p=0.25.

Flips (cv, 5 calls):

| call | expected | q38q6_facts | q38q6_facts_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | alarm | review | 0.84/0.78 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» |
| Stufe1_D09-K1 | alarm | alarm | review | 0.94/0.79 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.76 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.03/0.05 | fixed | Prüfen (knapp unter Schwelle): Score 0.05 für 'Zugangsinformation preisgegeben' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | review | 0.11/0.07 | fixed | Prüfen (knapp unter Schwelle): Score 0.07 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |

## `q38q6_facts_blind` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_facts_blind - q38q6_facts

| metric | q38q6_facts | q38q6_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.85 | +0.002 | [-0.018, +0.029] | no detectable difference |
| alarm AUC | 0.97 | 0.97 | +0.002 | [-0.036, +0.034] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_blind - q38q6_facts

| metric | q38q6_facts | q38q6_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [-0.142, +0.116] | no detectable difference |
| alarm_f1 | 0.84 | 0.81 | -0.031 | [-0.203, +0.092] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-16pp, +21pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-14pp, +6pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.87 | +0.000 | [-0.104, +0.078] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 2 vs only-q38q6_facts_blind 2, p=1.0; 3-class only-q38q6_facts 2 vs only-q38q6_facts_blind 1, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_blind - q38q6_facts

| metric | q38q6_facts | q38q6_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [-0.142, +0.116] | no detectable difference |
| alarm_f1 | 0.78 | 0.81 | +0.033 | [+0.000, +0.127] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-16pp, +21pp] | no detectable difference |
| accuracy | 75% | 77% | +2pp | [+0pp, +6pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.87 | +0.000 | [-0.104, +0.078] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 2 vs only-q38q6_facts_blind 2, p=1.0; 3-class only-q38q6_facts 0 vs only-q38q6_facts_blind 1, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_facts_blind - q38q6_facts

| metric | q38q6_facts | q38q6_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [-0.142, +0.116] | no detectable difference |
| alarm_f1 | 0.89 | 0.82 | -0.065 | [-0.244, +0.000] | no detectable difference |
| false_alarm_rate | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-16pp, +21pp] | no detectable difference |
| accuracy | 83% | 79% | -4pp | [-14pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.87 | +0.000 | [-0.104, +0.078] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 2 vs only-q38q6_facts_blind 2, p=1.0; 3-class only-q38q6_facts 2 vs only-q38q6_facts_blind 0, p=0.5.

Flips (cv, 4 calls):

| call | expected | q38q6_facts | q38q6_facts_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.94/0.11 | broken | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwell... | keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.13 | broken | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - Kein Alarm: höchster Score 0.13 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwell... | keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.03/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C13-K4 | alarm | no_alert | review | 0.11/0.50 | fixed | Prüfen (offener Sachverhalt): facts bewertet 'Relevante Angabe verschweigen' als unbestimmt (Score 0.50 >= 0.25). | Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |

## `q38q6_general_para` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_general_para - q38q6_facts

| metric | q38q6_facts | q38q6_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.86 | +0.011 | [-0.173, +0.206] | no detectable difference |
| alarm AUC | 0.97 | 0.94 | -0.034 | [-0.137, +0.043] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_para - q38q6_facts

| metric | q38q6_facts | q38q6_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | -0.004 | [-0.142, +0.160] | no detectable difference |
| alarm_f1 | 0.84 | 0.86 | +0.015 | [-0.147, +0.187] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 27% | 19% | -8pp | [-32pp, +15pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-6pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.84 | -0.030 | [-0.151, +0.096] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 5 vs only-q38q6_general_para 4, p=1.0; 3-class only-q38q6_facts 4 vs only-q38q6_general_para 3, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_para - q38q6_facts

| metric | q38q6_facts | q38q6_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | -0.004 | [-0.142, +0.160] | no detectable difference |
| alarm_f1 | 0.78 | 0.86 | +0.079 | [-0.114, +0.325] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 27% | 19% | -8pp | [-32pp, +15pp] | no detectable difference |
| accuracy | 75% | 77% | +2pp | [-6pp, +13pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.84 | -0.030 | [-0.151, +0.096] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 5 vs only-q38q6_general_para 4, p=1.0; 3-class only-q38q6_facts 4 vs only-q38q6_general_para 5, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_para - q38q6_facts

| metric | q38q6_facts | q38q6_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.81 | -0.036 | [-0.220, +0.150] | no detectable difference |
| alarm_f1 | 0.89 | 0.79 | -0.099 | [-0.282, +0.033] | no detectable difference |
| false_alarm_rate | 0% | 9% | +9pp | [+0pp, +29pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-29pp, +27pp] | no detectable difference |
| accuracy | 83% | 75% | -8pp | [-20pp, +2pp] | no detectable difference |
| review_recall | 33% | 17% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.82 | -0.045 | [-0.187, +0.100] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 6 vs only-q38q6_general_para 4, p=0.7539; 3-class only-q38q6_facts 7 vs only-q38q6_general_para 3, p=0.3438.

Flips (cv, 11 calls):

| call | expected | q38q6_facts | q38q6_general_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.03/0.65 | fixed | Alarm: Score 0.65 für 'Zugangsinformation preisgegeben' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.01/0.25 | broken | Prüfen (knapp unter Schwelle): Score 0.25 für 'Zugangsinformation preisgegeben' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C12-K4 | alarm | alarm | review | 0.97/0.16 | same | Prüfen (knapp unter Schwelle): Score 0.16 für 'Auskunft an Dritte' liegt zwischen 0.10 und der Schwelle 0.25. | Alarm: Score 0.97 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.04 (max. 0.35). |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.94 | same | Alarm: Score 0.94 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Prüfen (offener Sachverhalt): facts bewertet 'Relevante Angabe verschweigen' als unbestimmt (Score 0.50 >= 0.25). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.11/0.84 | fixed | Alarm: Score 0.84 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.04/0.96 | broken | Alarm: Score 0.96 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.03/0.87 | broken | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.02 | broken | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.01 | broken | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.58 | fixed | Alarm: Score 0.58 für 'Auskunft an Dritte' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.85 | fixed | Alarm: Score 0.85 für 'Auskunft an Dritte' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `q38q6_general_para_alone` vs `q38q6_facts`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = q38q6_general_para_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.85 | 0.90 | +0.045 | [-0.127, +0.250] | no detectable difference |
| alarm AUC | 0.97 | 0.94 | -0.027 | [-0.125, +0.045] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_para_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.86 | +0.018 | [-0.123, +0.196] | no detectable difference |
| alarm_f1 | 0.84 | 0.84 | -0.005 | [-0.157, +0.150] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 27% | 15% | -12pp | [-38pp, +14pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-6pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.85 | -0.011 | [-0.143, +0.121] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 5 vs only-q38q6_general_para_alone 5, p=1.0; 3-class only-q38q6_facts 4 vs only-q38q6_general_para_alone 3, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_para_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | -0.004 | [-0.142, +0.160] | no detectable difference |
| alarm_f1 | 0.78 | 0.86 | +0.079 | [-0.114, +0.325] | no detectable difference |
| false_alarm_rate | 0% | 14% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 27% | 19% | -8pp | [-32pp, +15pp] | no detectable difference |
| accuracy | 75% | 77% | +2pp | [-6pp, +13pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.84 | -0.030 | [-0.151, +0.096] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 5 vs only-q38q6_general_para_alone 4, p=1.0; 3-class only-q38q6_facts 4 vs only-q38q6_general_para_alone 5, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = q38q6_general_para_alone - q38q6_facts

| metric | q38q6_facts | q38q6_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.81 | -0.036 | [-0.220, +0.150] | no detectable difference |
| alarm_f1 | 0.89 | 0.79 | -0.099 | [-0.282, +0.033] | no detectable difference |
| false_alarm_rate | 0% | 9% | +9pp | [+0pp, +29pp] | no detectable difference |
| miss_rate | 27% | 27% | +0pp | [-29pp, +27pp] | no detectable difference |
| accuracy | 83% | 75% | -8pp | [-20pp, +2pp] | no detectable difference |
| review_recall | 33% | 17% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.87 | 0.82 | -0.045 | [-0.187, +0.100] | no detectable difference |

McNemar exact (calls): flag correct only-q38q6_facts 6 vs only-q38q6_general_para_alone 4, p=0.7539; 3-class only-q38q6_facts 7 vs only-q38q6_general_para_alone 3, p=0.3438.

Flips (cv, 12 calls):

| call | expected | q38q6_facts | q38q6_general_para_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe2_C09-K3 | alarm | no_alert | review | 0.02/0.12 | fixed | Prüfen (knapp unter Schwelle): Score 0.12 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.03/0.65 | fixed | Alarm: Score 0.65 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.01/0.25 | broken | Alarm: Score 0.25 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C12-K4 | alarm | alarm | review | 0.97/0.16 | same | Prüfen (knapp unter Schwelle): Score 0.16 für 'Auskunft an Dritte' liegt zwischen 0.10 und der Schwelle 0.25. | Alarm: Score 0.97 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.04 (max. 0.35). |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.94 | same | Alarm: Score 0.94 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Prüfen (offener Sachverhalt): facts bewertet 'Relevante Angabe verschweigen' als unbestimmt (Score 0.50 >= 0.25). |
| Stufe2_C13-K4 | alarm | no_alert | alarm | 0.11/0.84 | fixed | Alarm: Score 0.84 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K3 | no_alert | no_alert | alarm | 0.04/0.96 | broken | Alarm: Score 0.96 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.03/0.87 | broken | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.02 | broken | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.01 | broken | Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.58 | fixed | Alarm: Score 0.58 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.00/0.85 | fixed | Alarm: Score 0.85 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

