# Experiment `kev_perturbed`

Kev / general questions vs champion on re-recorded dev audio (speed 0.96, -3 dB)

RQ: RQ8, RQ10 · base profile `recommended-perturbed` · split **dev** · baseline `perturbed` · commit 96ec3da9c3 (dirty) · 2026-10-10T13:00:27+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| perturbed | 0.83 [0.67, 0.96] | 0.89 [0.74, 0.99] | 26/22 |  |
| perturbed_facts_only | 0.85 [0.73, 0.96] | 0.90 [0.76, 0.99] | 26/22 | re-fusion of perturbed |
| qwen_general | 0.76 [0.58, 0.91] | 0.76 [0.56, 0.93] | 26/22 |  |
| qwen_general_alone | 0.76 [0.58, 0.91] | 0.76 [0.56, 0.93] | 26/22 | re-fusion of qwen_general |
| kev_general | 0.76 [0.56, 0.92] | 0.83 [0.64, 0.97] | 26/22 |  |
| kev_general_alone | 0.76 [0.56, 0.92] | 0.83 [0.64, 0.96] | 26/22 | re-fusion of kev_general |
| kev_facts | 0.81 [0.60, 0.96] | 0.94 [0.81, 1.00] | 26/22 |  |
| kev_facts_alone | 0.86 [0.70, 0.98] | 0.94 [0.83, 1.00] | 26/22 | re-fusion of kev_facts |
| kev_facts_v3 | 0.79 [0.58, 0.95] | 0.94 [0.81, 1.00] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.76 | 0% | 73% | 0.82 [0.70, 0.93] |  |
| perturbed_facts_only | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.79 | 0% | 75% | 0.82 [0.70, 0.93] | re-fusion of perturbed |
| qwen_general | 48 | 0.70 [0.52, 0.86] | 65% | 77% | 50% [20%, 75%] | 23% [5%, 46%] | 0.64 | 17% | 56% | 0.63 [0.49, 0.79] |  |
| qwen_general_alone | 48 | 0.70 [0.52, 0.86] | 65% | 77% | 50% [20%, 75%] | 23% [5%, 46%] | 0.64 | 17% | 56% | 0.63 [0.49, 0.79] | re-fusion of qwen_general |
| kev_general | 48 | 0.69 [0.50, 0.85] | 58% | 85% | 73% [45%, 94%] | 15% [0%, 36%] | 0.70 | 33% | 50% | 0.56 [0.42, 0.72] |  |
| kev_general_alone | 48 | 0.69 [0.50, 0.85] | 58% | 85% | 73% [45%, 94%] | 15% [0%, 36%] | 0.70 | 33% | 50% | 0.56 [0.42, 0.72] | re-fusion of kev_general |
| kev_facts | 48 | 0.83 [0.63, 0.96] | 95% | 73% | 5% [0%, 15%] | 27% [7%, 50%] | 0.65 | 0% | 65% | 0.84 [0.70, 0.96] |  |
| kev_facts_alone | 48 | 0.74 [0.52, 0.91] | 94% | 62% | 5% [0%, 15%] | 38% [15%, 64%] | 0.76 | 0% | 71% | 0.78 [0.64, 0.92] | re-fusion of kev_facts |
| kev_facts_v3 | 48 | 0.83 [0.63, 0.96] | 95% | 73% | 5% [0%, 15%] | 27% [7%, 50%] | 0.65 | 0% | 65% | 0.84 [0.70, 0.96] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.74 | 33% | 73% | 0.82 [0.70, 0.93] |  |
| perturbed_facts_only | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.74 | 33% | 73% | 0.82 [0.70, 0.93] | re-fusion of perturbed |
| qwen_general | 48 | 0.64 [0.35, 0.83] | 78% | 54% | 18% [0%, 41%] | 46% [18%, 75%] | 0.46 | 17% | 56% | 0.68 [0.53, 0.82] |  |
| qwen_general_alone | 48 | 0.64 [0.35, 0.83] | 78% | 54% | 18% [0%, 41%] | 46% [18%, 75%] | 0.50 | 17% | 58% | 0.68 [0.53, 0.82] | re-fusion of qwen_general |
| kev_general | 48 | 0.67 [0.47, 0.82] | 73% | 62% | 27% [6%, 56%] | 38% [18%, 61%] | 0.55 | 17% | 52% | 0.67 [0.51, 0.81] |  |
| kev_general_alone | 48 | 0.67 [0.47, 0.82] | 73% | 62% | 27% [6%, 56%] | 38% [18%, 61%] | 0.55 | 17% | 52% | 0.67 [0.51, 0.81] | re-fusion of kev_general |
| kev_facts | 48 | 0.83 [0.63, 0.96] | 95% | 73% | 5% [0%, 15%] | 27% [7%, 50%] | 0.65 | 0% | 65% | 0.84 [0.70, 0.96] |  |
| kev_facts_alone | 48 | 0.74 [0.52, 0.91] | 94% | 62% | 5% [0%, 15%] | 38% [15%, 64%] | 0.76 | 0% | 71% | 0.78 [0.64, 0.92] | re-fusion of kev_facts |
| kev_facts_v3 | 48 | 0.83 [0.63, 0.96] | 95% | 73% | 5% [0%, 15%] | 27% [7%, 50%] | 0.65 | 0% | 65% | 0.84 [0.70, 0.96] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| perturbed | 14% | 4/4 | 14% | yes | - |
| perturbed_facts_only | 14% | 4/4 | 14% | yes | - |
| qwen_general | 14% | 4/4 | 18% | yes | - |
| qwen_general_alone | 14% | 4/4 | 18% | yes | - |
| kev_general | 0% | 4/4 | 27% | **no** | - |
| kev_general_alone | 0% | 4/4 | 27% | **no** | - |
| kev_facts | 5% | 4/4 | 5% | yes | - |
| kev_facts_alone | 5% | 4/4 | 5% | yes | - |
| kev_facts_v3 | 5% | 4/4 | 5% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.75 | 50% | 71% | 0.82 [0.70, 0.93] |  |
| perturbed_facts_only | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 43%] | 0.79 | 50% | 73% | 0.82 [0.70, 0.93] | re-fusion of perturbed |
| qwen_general | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 41%] | 38% [17%, 61%] | 0.58 | 0% | 60% | 0.72 [0.58, 0.84] |  |
| qwen_general_alone | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 41%] | 38% [17%, 61%] | 0.58 | 0% | 60% | 0.72 [0.58, 0.84] | re-fusion of qwen_general |
| kev_general | 48 | 0.68 [0.46, 0.84] | 83% | 58% | 14% [0%, 30%] | 42% [19%, 67%] | 0.55 | 17% | 58% | 0.72 [0.59, 0.84] |  |
| kev_general_alone | 48 | 0.68 [0.46, 0.84] | 83% | 58% | 14% [0%, 30%] | 42% [19%, 67%] | 0.55 | 17% | 58% | 0.72 [0.59, 0.84] | re-fusion of kev_general |
| kev_facts | 48 | 0.65 [0.39, 0.84] | 93% | 50% | 5% [0%, 15%] | 50% [25%, 75%] | 0.62 | 0% | 62% | 0.73 [0.60, 0.86] |  |
| kev_facts_alone | 48 | 0.65 [0.39, 0.84] | 93% | 50% | 5% [0%, 15%] | 50% [25%, 75%] | 0.75 | 0% | 69% | 0.73 [0.60, 0.86] | re-fusion of kev_facts |
| kev_facts_v3 | 48 | 0.65 [0.39, 0.84] | 93% | 50% | 5% [0%, 15%] | 50% [25%, 75%] | 0.62 | 0% | 62% | 0.73 [0.60, 0.86] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| perturbed | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 1.00, 0.30, 0.30) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 5.1 | 21.5 | 0 | 0 | 96ec3da9c3 |
| perturbed_facts_only | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.30, 1.00, 0.30, 0.30) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 5.0 | 21.5 | 0 | 0 | 96ec3da9c3 |
| qwen_general | 0.70 | 0.55 | 0.55, 0.20, 0.55, 0.55 (FAR20: 0.55, 1.00, 0.70, 1.00) | 3.0 | asr 0.0, diarize 0.0, checks 3.0 | 3.0 | 15.0 | 0 | 0 | 96ec3da9c3 |
| qwen_general_alone | 0.70 | 0.55 | 0.55, 0.20, 0.55, 0.55 (FAR20: 0.55, 1.00, 0.70, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 3.0 | 3.0 | 15.0 | 0 | 0 | 96ec3da9c3 |
| kev_general | 0.70 | 0.30 | 0.55, 0.30, 0.40, 0.30 (FAR20: 0.60, 0.70, 0.70, 0.70) | 2.5 | asr 0.0, diarize 0.0, checks 2.5 | 2.5 | 9.0 | 0 | 0 | 96ec3da9c3 |
| kev_general_alone | 0.70 | 0.30 | 0.55, 0.30, 0.40, 0.30 (FAR20: 0.60, 0.70, 0.70, 0.70) | 0.0 | asr 0.0, diarize 0.0, checks 2.5 | 2.5 | 9.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 15.9 | asr 0.0, diarize 0.0, checks 15.8 | 15.9 | 20.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_alone | 0.55 | 0.20 | 0.20, 0.25, 0.20, 0.20 (FAR20: 0.20, 0.25, 0.20, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 15.8 | 15.8 | 20.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_v3 | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 6.4 | asr 0.0, diarize 0.0, checks 6.3 | 6.4 | 8.0 | 0 | 0 | 96ec3da9c3 |

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| perturbed | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.67 / - / 50% | 0.75 / 18% / 31% | 0.88 / 9% / 15% |
| perturbed_facts_only | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.67 / - / 50% | 0.75 / 18% / 31% | 0.88 / 9% / 15% |
| qwen_general | 0.87 / 38% / 0% | 0.50 / 57% / 40% | 0.80 / - / 33% | 0.69 / 55% / 23% | 0.71 / 45% / 23% |
| qwen_general_alone | 0.87 / 38% / 0% | 0.50 / 57% / 40% | 0.80 / - / 33% | 0.69 / 55% / 23% | 0.71 / 45% / 23% |
| kev_general | 0.80 / 62% / 0% | 0.55 / 79% / 20% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.67 / 82% / 15% |
| kev_general_alone | 0.80 / 62% / 0% | 0.55 / 79% / 20% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.67 / 82% / 15% |
| kev_facts | 1.00 / 0% / 0% | 0.90 / 7% / 10% | 0.00 / - / 100% | 0.87 / 0% / 23% | 0.78 / 9% / 31% |
| kev_facts_alone | 0.82 / 0% / 30% | 0.90 / 7% / 10% | 0.00 / - / 100% | 0.76 / 0% / 38% | 0.73 / 9% / 38% |
| kev_facts_v3 | 1.00 / 0% / 0% | 0.90 / 7% / 10% | 0.00 / - / 100% | 0.87 / 0% / 23% | 0.78 / 9% / 31% |

## `perturbed_facts_only` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = perturbed_facts_only - perturbed

| metric | perturbed | perturbed_facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.85 | +0.026 | [+0.000, +0.076] | no detectable difference |
| alarm AUC | 0.89 | 0.90 | +0.011 | [+0.000, +0.042] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = perturbed_facts_only - perturbed

| metric | perturbed | perturbed_facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.76 | 0.79 | +0.029 | [+0.000, +0.097] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 23% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 73% | 75% | +2pp | [+0pp, +7pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 0 vs only-perturbed_facts_only 0, p=1.0; 3-class only-perturbed 0 vs only-perturbed_facts_only 1, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = perturbed_facts_only - perturbed

| metric | perturbed | perturbed_facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.74 | 0.74 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 23% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 73% | 73% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 0 vs only-perturbed_facts_only 0, p=1.0; 3-class only-perturbed 0 vs only-perturbed_facts_only 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = perturbed_facts_only - perturbed

| metric | perturbed | perturbed_facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.75 | 0.79 | +0.038 | [+0.000, +0.127] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 23% | 23% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 71% | 73% | +2pp | [+0pp, +7pp] | no detectable difference |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.82 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 0 vs only-perturbed_facts_only 0, p=1.0; 3-class only-perturbed 0 vs only-perturbed_facts_only 1, p=1.0.

Flips (cv, 1 calls):

| call | expected | perturbed | perturbed_facts_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | review | alarm | 0.83/0.89 | same | 01:20-01:28 access: Wartet, ich sage Ihnen die Tarngrad. sieben, drei, eins, neun, vier, zwei. Es steht immer noch. Sie sind noch gültig. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - D... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern des Tarngrades laut. (Regel: access.alarm_1) |

## `qwen_general` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general - perturbed

| metric | perturbed | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.76 | -0.071 | [-0.257, +0.118] | no detectable difference |
| alarm AUC | 0.89 | 0.76 | -0.130 | [-0.276, -0.014] | **real**: perturbed better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general - perturbed

| metric | perturbed | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.115 | [-0.332, +0.068] | no detectable difference |
| alarm_f1 | 0.76 | 0.64 | -0.124 | [-0.353, +0.042] | no detectable difference |
| false_alarm_rate | 14% | 50% | +36pp | [-5pp, +73pp] | no detectable difference |
| miss_rate | 23% | 23% | +0pp | [-25pp, +27pp] | no detectable difference |
| accuracy | 73% | 56% | -17pp | [-39pp, +5pp] | no detectable difference |
| review_recall | 0% | 17% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.63 | -0.182 | [-0.388, +0.046] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 14 vs only-qwen_general 6, p=0.1153; 3-class only-perturbed 13 vs only-qwen_general 5, p=0.0963.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general - perturbed

| metric | perturbed | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.64 | -0.180 | [-0.463, +0.045] | no detectable difference |
| alarm_f1 | 0.74 | 0.46 | -0.280 | [-0.562, -0.083] | **real**: perturbed better |
| false_alarm_rate | 14% | 18% | +5pp | [-22pp, +33pp] | no detectable difference |
| miss_rate | 23% | 46% | +23pp | [-9pp, +57pp] | no detectable difference |
| accuracy | 73% | 56% | -17pp | [-34pp, -2pp] | **real**: perturbed better |
| review_recall | 33% | 17% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.68 | -0.138 | [-0.336, +0.044] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 12 vs only-qwen_general 5, p=0.1435; 3-class only-perturbed 11 vs only-qwen_general 3, p=0.0574.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general - perturbed

| metric | perturbed | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.121 | [-0.340, +0.047] | no detectable difference |
| alarm_f1 | 0.75 | 0.58 | -0.171 | [-0.445, +0.048] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [-22pp, +33pp] | no detectable difference |
| miss_rate | 23% | 38% | +15pp | [-8pp, +42pp] | no detectable difference |
| accuracy | 71% | 60% | -10pp | [-31pp, +8pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.72 | -0.100 | [-0.278, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 10 vs only-qwen_general 5, p=0.3018; 3-class only-perturbed 10 vs only-qwen_general 5, p=0.3018.

Flips (cv, 22 calls):

| call | expected | perturbed | qwen_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.71 | broken | Alarm: Score 0.71 für 'Relevante Angabe verschweigen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | review | alarm | 0.83/0.35 | same | 01:20-01:28 access: Wartet, ich sage Ihnen die Tarngrad. sieben, drei, eins, neun, vier, zwei. Es steht immer noch. Sie sind noch gültig. - Alarm: Score 0.35 für 'Relevante Angabe verschweigen' >= Sch... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern des Tarngrades laut. (Regel: access.alarm_1) |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.94 | broken | 01:56-01:57 splitting: Mail hat jemand geschrieben, ich solle zum Gerätewechsel eine Prüfung umgehen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.02/0.93 | broken | 00:29-00:29 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C01-K3 | no_alert | no_alert | alarm | 0.00/0.36 | broken | Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | alarm | 0.00/0.25 | broken | Alarm: Score 0.25 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.34 | broken | Alarm: Score 0.34 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.18 | broken | Prüfen (knapp unter Schwelle): Score 0.18 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.51 | broken | Prüfen (knapp unter Schwelle): Score 0.51 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C06-K3 | alarm | alarm | no_alert | 0.98/0.29 | broken | 01:12-01:26 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.95) - Die Kunde erwähnt, dass sie den Bericht von Claudia, die das Projekt leitet, persönlich erhalten hat. (Regel: trade.alar... |
| Stufe2_C06-K4 | alarm | alarm | review | 1.00/0.50 | same | 00:46-00:55 trade: Es geht um CRM -Systeme. Ich kenne die Produkte aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt. - Prüfen (knapp unter Schwelle): Score 0.50 für 'Relevante Angabe v... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kundin erwähnt einen unterzeichneten Großauftrag, den sie privat von der Firma gekannt hat. (Regel: trade.alarm_1) |
| Stufe2_C07-K3 | alarm | no_alert | alarm | 0.16/0.72 | fixed | Alarm: Score 0.72 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.22 | broken | Alarm: Score 0.22 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.20 | broken | Alarm: Score 0.20 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.50/0.15 | fixed | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - Kein Alarm: höchster Score 0.15 ('Relevante Angabe verschweigen') liegt unter 0.40 (Schwelle 0... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.00 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.50/0.05 | broken | 03:40-03:50 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.05 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.04 | broken | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.03 | broken | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minu... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.87 | fixed | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.86 | fixed | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.41 | fixed | Prüfen (knapp unter Schwelle): Score 0.41 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `qwen_general_alone` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general_alone - perturbed

| metric | perturbed | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.76 | -0.069 | [-0.257, +0.118] | no detectable difference |
| alarm AUC | 0.89 | 0.76 | -0.130 | [-0.276, -0.014] | **real**: perturbed better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_alone - perturbed

| metric | perturbed | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.115 | [-0.332, +0.068] | no detectable difference |
| alarm_f1 | 0.76 | 0.64 | -0.124 | [-0.353, +0.042] | no detectable difference |
| false_alarm_rate | 14% | 50% | +36pp | [-5pp, +73pp] | no detectable difference |
| miss_rate | 23% | 23% | +0pp | [-25pp, +27pp] | no detectable difference |
| accuracy | 73% | 56% | -17pp | [-39pp, +5pp] | no detectable difference |
| review_recall | 0% | 17% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.63 | -0.182 | [-0.388, +0.046] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 14 vs only-qwen_general_alone 6, p=0.1153; 3-class only-perturbed 13 vs only-qwen_general_alone 5, p=0.0963.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_alone - perturbed

| metric | perturbed | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.64 | -0.180 | [-0.463, +0.045] | no detectable difference |
| alarm_f1 | 0.74 | 0.50 | -0.237 | [-0.465, -0.078] | **real**: perturbed better |
| false_alarm_rate | 14% | 18% | +5pp | [-22pp, +33pp] | no detectable difference |
| miss_rate | 23% | 46% | +23pp | [-9pp, +57pp] | no detectable difference |
| accuracy | 73% | 58% | -15pp | [-30pp, -2pp] | **real**: perturbed better |
| review_recall | 33% | 17% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.68 | -0.138 | [-0.336, +0.044] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 12 vs only-qwen_general_alone 5, p=0.1435; 3-class only-perturbed 10 vs only-qwen_general_alone 3, p=0.0923.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_alone - perturbed

| metric | perturbed | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.70 | -0.121 | [-0.340, +0.047] | no detectable difference |
| alarm_f1 | 0.75 | 0.58 | -0.171 | [-0.445, +0.048] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [-22pp, +33pp] | no detectable difference |
| miss_rate | 23% | 38% | +15pp | [-8pp, +42pp] | no detectable difference |
| accuracy | 71% | 60% | -10pp | [-31pp, +8pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.72 | -0.100 | [-0.278, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 10 vs only-qwen_general_alone 5, p=0.3018; 3-class only-perturbed 10 vs only-qwen_general_alone 5, p=0.3018.

Flips (cv, 22 calls):

| call | expected | perturbed | qwen_general_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.71 | broken | Alarm: Score 0.71 für 'Relevante Angabe verschweigen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | review | alarm | 0.83/0.35 | same | 01:20-01:28 access: Wartet, ich sage Ihnen die Tarngrad. sieben, drei, eins, neun, vier, zwei. Es steht immer noch. Sie sind noch gültig. - Alarm: Score 0.35 für 'Relevante Angabe verschweigen' >= Sch... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern des Tarngrades laut. (Regel: access.alarm_1) |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.98 | broken | Alarm: Score 0.98 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.02/0.97 | broken | Alarm: Score 0.97 für 'Zugangsinformation preisgegeben' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C01-K3 | no_alert | no_alert | alarm | 0.00/0.36 | broken | Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | alarm | 0.00/0.25 | broken | Alarm: Score 0.25 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.34 | broken | Alarm: Score 0.34 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.18 | broken | Prüfen (knapp unter Schwelle): Score 0.18 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.51 | broken | Prüfen (knapp unter Schwelle): Score 0.51 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C06-K3 | alarm | alarm | no_alert | 0.98/0.29 | broken | 01:12-01:26 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.95) - Die Kunde erwähnt, dass sie den Bericht von Claudia, die das Projekt leitet, persönlich erhalten hat. (Regel: trade.alar... |
| Stufe2_C06-K4 | alarm | alarm | review | 1.00/0.50 | same | 00:46-00:55 trade: Es geht um CRM -Systeme. Ich kenne die Produkte aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt. - Prüfen (knapp unter Schwelle): Score 0.50 für 'Relevante Angabe v... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kundin erwähnt einen unterzeichneten Großauftrag, den sie privat von der Firma gekannt hat. (Regel: trade.alarm_1) |
| Stufe2_C07-K3 | alarm | no_alert | alarm | 0.16/0.72 | fixed | Alarm: Score 0.72 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.22 | broken | Alarm: Score 0.22 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.20 | broken | Alarm: Score 0.20 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.50/0.15 | fixed | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - Kein Alarm: höchster Score 0.15 ('Relevante Angabe verschweigen') liegt unter 0.40 (Schwelle 0... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.00 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.50/0.05 | broken | 03:40-03:50 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.05 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.04 | broken | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.03 | broken | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minu... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.87 | fixed | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.86 | fixed | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.55 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.41 | fixed | Prüfen (knapp unter Schwelle): Score 0.41 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `kev_general` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general - perturbed

| metric | perturbed | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.76 | -0.066 | [-0.235, +0.084] | no detectable difference |
| alarm AUC | 0.89 | 0.83 | -0.061 | [-0.170, +0.031] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general - perturbed

| metric | perturbed | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.69 | -0.129 | [-0.287, +0.010] | no detectable difference |
| alarm_f1 | 0.76 | 0.70 | -0.066 | [-0.272, +0.114] | no detectable difference |
| false_alarm_rate | 14% | 73% | +59pp | [+15pp, +90pp] | **real**: perturbed better |
| miss_rate | 23% | 15% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 73% | 50% | -23pp | [-48pp, +2pp] | no detectable difference |
| review_recall | 0% | 33% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.56 | -0.257 | [-0.417, -0.042] | **real**: perturbed better |

McNemar exact (calls): flag correct only-perturbed 15 vs only-kev_general 4, p=0.0192; 3-class only-perturbed 17 vs only-kev_general 6, p=0.0347.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general - perturbed

| metric | perturbed | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.67 | -0.150 | [-0.324, -0.018] | **real**: perturbed better |
| alarm_f1 | 0.74 | 0.55 | -0.185 | [-0.476, +0.067] | no detectable difference |
| false_alarm_rate | 14% | 27% | +14pp | [-17pp, +44pp] | no detectable difference |
| miss_rate | 23% | 38% | +15pp | [-3pp, +35pp] | no detectable difference |
| accuracy | 73% | 52% | -21pp | [-39pp, -4pp] | **real**: perturbed better |
| review_recall | 33% | 17% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.67 | -0.145 | [-0.320, +0.006] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 10 vs only-kev_general 3, p=0.0923; 3-class only-perturbed 14 vs only-kev_general 4, p=0.0309.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general - perturbed

| metric | perturbed | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.68 | -0.135 | [-0.341, +0.010] | no detectable difference |
| alarm_f1 | 0.75 | 0.55 | -0.198 | [-0.509, +0.024] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [-25pp, +20pp] | no detectable difference |
| miss_rate | 23% | 42% | +19pp | [+0pp, +42pp] | no detectable difference |
| accuracy | 71% | 58% | -12pp | [-31pp, +4pp] | no detectable difference |
| review_recall | 50% | 17% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.72 | -0.096 | [-0.253, +0.037] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 8 vs only-kev_general 3, p=0.2266; 3-class only-perturbed 9 vs only-kev_general 3, p=0.146.

Flips (cv, 24 calls):

| call | expected | perturbed | kev_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.48 | broken | Prüfen (knapp unter Schwelle): Score 0.48 für 'Zugangsinformation preisgegeben' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | review | alarm | 0.83/0.59 | same | 01:20-01:45 documentation: Wartet, ich sage Ihnen die Tarngrad. sieben, drei, eins, neun, vier, zwei. Es steht immer noch. Sie sind noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge i... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern des Tarngrades laut. (Regel: access.alarm_1) |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.45 | broken | 00:28-00:29 access: Gut, wir können diese zwei Sachen. Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.02/0.57 | broken | 01:58-02:30 access: Das habe ich nicht gemacht. Die Senderadresse sieht anders aus als bei Ihrer normalen Nachricht. Darum rufe ich direkt auf der bekannten Service-Nummer an. Gut, dass Sie nicht auf ... | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.02/0.51 | broken | 00:44-01:28 access: Richtig. Ich will auch gar nicht darüber persönlich wissen. Ich habe das Protokoll der Wahl und das Formular zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingereicht. I... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.02/0.64 | broken | 00:59-01:32 access: Identität und gültige Vollmacht für Auskunft zu genau diesem Voreinskonto sind in diesem Vorgang bestätigt. Diese Berechtigung umfasst den Kontostand und die Buchungen. Für die Zah... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | review | 0.96/0.41 | same | 02:44-02:46 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.98) - Die Kunde möchte, dass die Verpflichtung ihrer Tante nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.alarm_1... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.89/0.48 | same | 02:46-02:48 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Der Kunde möchte, dass die Tante nicht auf die Kreditstelle geht und die Herkunft und Pflichtenrichtung nicht erfährt. (Regel: docume... |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.20 | broken | Prüfen (knapp unter Schwelle): Score 0.20 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.23 | broken | Prüfen (knapp unter Schwelle): Score 0.23 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.19 | broken | Prüfen (knapp unter Schwelle): Score 0.19 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.31 | broken | Alarm: Score 0.31 für 'Insiderhandel' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.54 | broken | 08:18-08:56 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für sechstausend Franken Aktien von den Seelen-Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entg... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C07-K3 | alarm | no_alert | alarm | 0.16/0.69 | fixed | 00:00-00:56 access: Guten Tag, Frau Bühler, da ist Nadia Fuller. Sie will die Erfassung Ihres Sparauftrags ändern. Geht es um den Monat oder um den Betrag? Ich möchte zuerst verstehen, wie ein einzeln... | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.33 | broken | Alarm: Score 0.33 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.37 | broken | Alarm: Score 0.37 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.00/0.34 | broken | Prüfen (knapp unter Schwelle): Score 0.34 für 'Relevante Angabe verschweigen' liegt zwischen 0.25 und der Schwelle 0.40. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.50/0.14 | fixed | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - Kein Alarm: höchster Score 0.14 ('Relevante Angabe verschweigen') liegt unter 0.15 (Schwelle 0... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.50/0.14 | fixed | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.14 ('Insiderhan... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.48 | broken | Prüfen (knapp unter Schwelle): Score 0.48 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | review | 0.50/0.25 | same | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Prüfen (knapp unter Schwelle): Score 0.25 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | review | 0.50/0.29 | same | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Prüfen (knapp unter Schwelle): Score 0.29 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.47 | fixed | Alarm: Score 0.47 für 'Auskunft an Dritte' >= Schwelle 0.40 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `kev_general_alone` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_alone - perturbed

| metric | perturbed | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.76 | -0.069 | [-0.236, +0.080] | no detectable difference |
| alarm AUC | 0.89 | 0.83 | -0.064 | [-0.173, +0.025] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_alone - perturbed

| metric | perturbed | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.69 | -0.129 | [-0.287, +0.010] | no detectable difference |
| alarm_f1 | 0.76 | 0.70 | -0.066 | [-0.272, +0.114] | no detectable difference |
| false_alarm_rate | 14% | 73% | +59pp | [+15pp, +90pp] | **real**: perturbed better |
| miss_rate | 23% | 15% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 73% | 50% | -23pp | [-48pp, +2pp] | no detectable difference |
| review_recall | 0% | 33% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.56 | -0.257 | [-0.417, -0.042] | **real**: perturbed better |

McNemar exact (calls): flag correct only-perturbed 15 vs only-kev_general_alone 4, p=0.0192; 3-class only-perturbed 17 vs only-kev_general_alone 6, p=0.0347.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_alone - perturbed

| metric | perturbed | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.67 | -0.150 | [-0.324, -0.018] | **real**: perturbed better |
| alarm_f1 | 0.74 | 0.55 | -0.185 | [-0.476, +0.067] | no detectable difference |
| false_alarm_rate | 14% | 27% | +14pp | [-17pp, +44pp] | no detectable difference |
| miss_rate | 23% | 38% | +15pp | [-3pp, +35pp] | no detectable difference |
| accuracy | 73% | 52% | -21pp | [-39pp, -4pp] | **real**: perturbed better |
| review_recall | 33% | 17% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.67 | -0.145 | [-0.320, +0.006] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 10 vs only-kev_general_alone 3, p=0.0923; 3-class only-perturbed 14 vs only-kev_general_alone 4, p=0.0309.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_alone - perturbed

| metric | perturbed | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.68 | -0.135 | [-0.341, +0.010] | no detectable difference |
| alarm_f1 | 0.75 | 0.55 | -0.198 | [-0.509, +0.024] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [-25pp, +20pp] | no detectable difference |
| miss_rate | 23% | 42% | +19pp | [+0pp, +42pp] | no detectable difference |
| accuracy | 71% | 58% | -12pp | [-31pp, +4pp] | no detectable difference |
| review_recall | 50% | 17% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.72 | -0.096 | [-0.253, +0.037] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 8 vs only-kev_general_alone 3, p=0.2266; 3-class only-perturbed 9 vs only-kev_general_alone 3, p=0.146.

Flips (cv, 24 calls):

| call | expected | perturbed | kev_general_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.48 | broken | Prüfen (knapp unter Schwelle): Score 0.48 für 'Zugangsinformation preisgegeben' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | review | alarm | 0.83/0.59 | same | 01:20-01:45 documentation: Wartet, ich sage Ihnen die Tarngrad. sieben, drei, eins, neun, vier, zwei. Es steht immer noch. Sie sind noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge i... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern des Tarngrades laut. (Regel: access.alarm_1) |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.46 | broken | Prüfen (knapp unter Schwelle): Score 0.46 für 'Zugangsinformation preisgegeben' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.02/0.59 | broken | 01:58-02:30 access: Das habe ich nicht gemacht. Die Senderadresse sieht anders aus als bei Ihrer normalen Nachricht. Darum rufe ich direkt auf der bekannten Service-Nummer an. Gut, dass Sie nicht auf ... | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.02/0.51 | broken | 00:44-01:28 access: Richtig. Ich will auch gar nicht darüber persönlich wissen. Ich habe das Protokoll der Wahl und das Formular zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingereicht. I... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.02/0.64 | broken | 00:59-01:32 access: Identität und gültige Vollmacht für Auskunft zu genau diesem Voreinskonto sind in diesem Vorgang bestätigt. Diese Berechtigung umfasst den Kontostand und die Buchungen. Für die Zah... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | review | 0.96/0.41 | same | 02:49-02:59 documentation: Nehmen Sie das Darlehen nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - Prüfen (knapp... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.98) - Die Kunde möchte, dass die Verpflichtung ihrer Tante nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.alarm_1... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.89/0.49 | same | 02:55-03:01 documentation: Ich will, dass sie nur Eigenmittel sieht und die Vereinbarung meiner Tante gar nicht erfährt. - Prüfen (knapp unter Schwelle): Score 0.49 für 'Relevante Angabe verschweigen'... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Der Kunde möchte, dass die Tante nicht auf die Kreditstelle geht und die Herkunft und Pflichtenrichtung nicht erfährt. (Regel: docume... |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.20 | broken | Prüfen (knapp unter Schwelle): Score 0.20 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.23 | broken | Prüfen (knapp unter Schwelle): Score 0.23 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.19 | broken | Prüfen (knapp unter Schwelle): Score 0.19 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.31 | broken | Alarm: Score 0.31 für 'Insiderhandel' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.54 | broken | 08:18-08:56 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für sechstausend Franken Aktien von den Seelen-Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entg... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C07-K3 | alarm | no_alert | alarm | 0.16/0.69 | fixed | 00:00-00:56 access: Guten Tag, Frau Bühler, da ist Nadia Fuller. Sie will die Erfassung Ihres Sparauftrags ändern. Geht es um den Monat oder um den Betrag? Ich möchte zuerst verstehen, wie ein einzeln... | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.33 | broken | Alarm: Score 0.33 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.37 | broken | Alarm: Score 0.37 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.00/0.34 | broken | Prüfen (knapp unter Schwelle): Score 0.34 für 'Relevante Angabe verschweigen' liegt zwischen 0.25 und der Schwelle 0.40. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.50/0.14 | fixed | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - Kein Alarm: höchster Score 0.14 ('Relevante Angabe verschweigen') liegt unter 0.15 (Schwelle 0... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.50/0.14 | fixed | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.14 ('Insiderhan... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.48 | broken | Prüfen (knapp unter Schwelle): Score 0.48 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe3_C17-K3 | review | alarm | review | 0.50/0.25 | same | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Prüfen (knapp unter Schwelle): Score 0.25 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und der Schwelle 0.30. | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | review | 0.50/0.29 | same | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Prüfen (knapp unter Schwelle): Score 0.29 für 'Relevante Angabe verschweigen' liegt zwischen 0.15 und ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K3 | review | no_alert | alarm | 0.00/0.47 | fixed | Alarm: Score 0.47 für 'Auskunft an Dritte' >= Schwelle 0.40 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |

## `kev_facts` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts - perturbed

| metric | perturbed | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.81 | -0.022 | [-0.176, +0.094] | no detectable difference |
| alarm AUC | 0.89 | 0.94 | +0.048 | [+0.000, +0.120] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts - perturbed

| metric | perturbed | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.83 | +0.010 | [-0.156, +0.139] | no detectable difference |
| alarm_f1 | 0.76 | 0.65 | -0.117 | [-0.429, +0.148] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-25pp, +6pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.84 | +0.026 | [-0.115, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 4 vs only-kev_facts 5, p=1.0; 3-class only-perturbed 8 vs only-kev_facts 4, p=0.3877.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts - perturbed

| metric | perturbed | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.83 | +0.010 | [-0.156, +0.139] | no detectable difference |
| alarm_f1 | 0.74 | 0.65 | -0.092 | [-0.424, +0.168] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-27pp, +8pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.84 | +0.026 | [-0.115, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 4 vs only-kev_facts 5, p=1.0; 3-class only-perturbed 9 vs only-kev_facts 5, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts - perturbed

| metric | perturbed | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.65 | -0.166 | [-0.407, +0.015] | no detectable difference |
| alarm_f1 | 0.75 | 0.62 | -0.129 | [-0.490, +0.167] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 50% | +27pp | [+3pp, +54pp] | **real**: perturbed better |
| accuracy | 71% | 62% | -8pp | [-32pp, +14pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.73 | -0.089 | [-0.225, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 9 vs only-kev_facts 4, p=0.2668; 3-class only-perturbed 9 vs only-kev_facts 5, p=0.424.

Flips (cv, 16 calls):

| call | expected | perturbed | kev_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `kev_facts_alone` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_alone - perturbed

| metric | perturbed | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.86 | +0.031 | [-0.104, +0.161] | no detectable difference |
| alarm AUC | 0.89 | 0.94 | +0.052 | [+0.000, +0.135] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_alone - perturbed

| metric | perturbed | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.74 | -0.072 | [-0.309, +0.094] | no detectable difference |
| alarm_f1 | 0.76 | 0.76 | +0.003 | [-0.238, +0.215] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 38% | +15pp | [-8pp, +42pp] | no detectable difference |
| accuracy | 73% | 71% | -2pp | [-15pp, +9pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.79 | -0.031 | [-0.201, +0.114] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 7 vs only-kev_facts_alone 5, p=0.7744; 3-class only-perturbed 5 vs only-kev_facts_alone 4, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_alone - perturbed

| metric | perturbed | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.74 | -0.072 | [-0.309, +0.094] | no detectable difference |
| alarm_f1 | 0.74 | 0.76 | +0.028 | [-0.226, +0.255] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 38% | +15pp | [-8pp, +42pp] | no detectable difference |
| accuracy | 73% | 71% | -2pp | [-19pp, +13pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.79 | -0.031 | [-0.201, +0.114] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 7 vs only-kev_facts_alone 5, p=0.7744; 3-class only-perturbed 7 vs only-kev_facts_alone 6, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_alone - perturbed

| metric | perturbed | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.65 | -0.166 | [-0.407, +0.015] | no detectable difference |
| alarm_f1 | 0.75 | 0.75 | +0.000 | [-0.248, +0.231] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 50% | +27pp | [+3pp, +54pp] | **real**: perturbed better |
| accuracy | 71% | 69% | -2pp | [-24pp, +19pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.73 | -0.089 | [-0.225, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 9 vs only-kev_facts_alone 4, p=0.2668; 3-class only-perturbed 6 vs only-kev_facts_alone 5, p=1.0.

Flips (cv, 14 calls):

| call | expected | perturbed | kev_facts_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | review | no_alert | 0.83/0.08 | broken | 01:20-01:28 access: Wartet, ich sage Ihnen die Tarngrad. sieben, drei, eins, neun, vier, zwei. Es steht immer noch. Sie sind noch gültig. - Kein Alarm: höchster Score 0.08 ('Zugangsinformation preisge... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern des Tarngrades laut. (Regel: access.alarm_1) |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.88/0.04 | broken | 01:36-01:52 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde erklärt, dass er die Zahlung aufteilen will, um die Freigabestellung der ganzen Rechnung zu umgehen. (Regel: splittin... |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.97/0.03 | broken | 00:36-00:40 splitting: Es ist eine einzige Rechnung für die eine Maschine. - Kein Alarm: höchster Score 0.03 ('Zuständigkeit/Kontrolle umgehen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Teilbeträge gehören zu einer einzigen Rechnung = ja (0.73) - Die Kundenin erklärt, dass es eine einzige Rechnung für die Maschine ist. (Regel: splitting.alarm_1) |
| Stufe2_C07-K3 | alarm | no_alert | review | 0.16/0.15 | fixed | Prüfen (knapp unter Schwelle): Score 0.15 für 'Insiderhandel' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.16 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 00:36-00:42 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus B... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.97) - Die Kunde fragt nach den monatlichen Ausgaben und den Belegen des Heims. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 03:43-03:52 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Beraterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | alarm | review | 0.50/0.11 | same | 01:12-01:33 documentation: Der violette Satz sagt, dass dreissigtausend von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, kein privater Kontaktanrat.... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.98) - Regula Bachmann möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht in den Entwurf aufgenommen wird. (Regel: documentation.... |
| Stufe2_C13-K4 | alarm | alarm | review | 0.50/0.12 | same | 08:07-08:34 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machia den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 00:59-01:59 documentation: Bedienen wir mit den violetten Zeilen. Um welche Anlage geht es dort? Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der viol... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation... |
| Stufe3_C17-K3 | review | alarm | no_alert | 0.50/0.01 | broken | 01:26-01:30 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | alarm | no_alert | 0.50/0.01 | broken | 01:46-01:54 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 mi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99) - Der Kunde gibt die Ziffern 2, 9, 6, 4, 8, 1 laut. (Regel: access.review_1) |
| Stufe3_C18-K4 | review | alarm | no_alert | 0.50/0.00 | broken | 00:10-00:31 disclosure: Ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann mü... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach der Berechtigung für Auskunft zum Konto ihrer Schwester. (Regel: disclosure.review_2) |

## `kev_facts_v3` vs `perturbed`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_v3 - perturbed

| metric | perturbed | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.83 | 0.79 | -0.042 | [-0.203, +0.083] | no detectable difference |
| alarm AUC | 0.89 | 0.94 | +0.047 | [+0.000, +0.119] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_v3 - perturbed

| metric | perturbed | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.83 | +0.010 | [-0.156, +0.139] | no detectable difference |
| alarm_f1 | 0.76 | 0.65 | -0.117 | [-0.429, +0.148] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-25pp, +6pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.84 | +0.026 | [-0.115, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 4 vs only-kev_facts_v3 5, p=1.0; 3-class only-perturbed 8 vs only-kev_facts_v3 4, p=0.3877.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_v3 - perturbed

| metric | perturbed | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.83 | +0.010 | [-0.156, +0.139] | no detectable difference |
| alarm_f1 | 0.74 | 0.65 | -0.092 | [-0.424, +0.168] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 27% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 73% | 65% | -8pp | [-27pp, +8pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.84 | +0.026 | [-0.115, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 4 vs only-kev_facts_v3 5, p=1.0; 3-class only-perturbed 9 vs only-kev_facts_v3 5, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_v3 - perturbed

| metric | perturbed | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.82 | 0.65 | -0.166 | [-0.407, +0.015] | no detectable difference |
| alarm_f1 | 0.75 | 0.62 | -0.129 | [-0.490, +0.167] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-32pp, +11pp] | no detectable difference |
| miss_rate | 23% | 50% | +27pp | [+3pp, +54pp] | **real**: perturbed better |
| accuracy | 71% | 62% | -8pp | [-32pp, +14pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.82 | 0.73 | -0.089 | [-0.225, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-perturbed 9 vs only-kev_facts_v3 4, p=0.2668; 3-class only-perturbed 9 vs only-kev_facts_v3 5, p=0.424.

Flips (cv, 16 calls):

| call | expected | perturbed | kev_facts_v3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

