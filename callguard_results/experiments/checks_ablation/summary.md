# Experiment `checks_ablation`

Which checks carry the decision (keywords, patterns, llm_judge, geval; add and remove)

RQ: RQ4 · base profile `gpu-12gb` · split **dev** · baseline `all` · commit 2cc04e7f41 (dirty) · 2026-10-10T02:13:48+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| all | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 |  |
| keywords | 0.55 [0.38, 0.73] | 0.64 [0.47, 0.83] | 26/22 | re-fusion of all |
| kw_patterns | 0.55 [0.38, 0.73] | 0.64 [0.47, 0.83] | 26/22 | re-fusion of all |
| kw_pat_judge | 0.67 [0.53, 0.83] | 0.75 [0.60, 0.92] | 26/22 | re-fusion of all |
| kw_pat_geval | 0.57 [0.37, 0.76] | 0.67 [0.45, 0.89] | 26/22 | re-fusion of all |
| llm_only | 0.66 [0.51, 0.82] | 0.75 [0.60, 0.91] | 26/22 | re-fusion of all |
| all_minus_keywords | 0.69 [0.55, 0.84] | 0.78 [0.64, 0.93] | 26/22 | re-fusion of all |
| all_minus_patterns | 0.65 [0.49, 0.81] | 0.74 [0.59, 0.90] | 26/22 | re-fusion of all |
| all_minus_llm_judge | 0.57 [0.37, 0.76] | 0.67 [0.45, 0.89] | 26/22 | re-fusion of all |
| all_minus_geval | 0.67 [0.53, 0.83] | 0.75 [0.60, 0.92] | 26/22 | re-fusion of all |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.55 | 67% | 50% | 0.62 [0.47, 0.78] |  |
| keywords | 48 | 0.47 [0.20, 0.71] | 59% | 38% | 32% [7%, 61%] | 62% [33%, 87%] | 0.50 | 0% | 50% | 0.53 [0.37, 0.70] | re-fusion of all |
| kw_patterns | 48 | 0.37 [0.07, 0.61] | 58% | 27% | 23% [0%, 50%] | 73% [50%, 94%] | 0.34 | 0% | 46% | 0.52 [0.37, 0.67] | re-fusion of all |
| kw_pat_judge | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.44 | 83% | 27% | 0.51 [0.45, 0.59] | re-fusion of all |
| kw_pat_geval | 48 | 0.36 [0.09, 0.62] | 86% | 23% | 5% [0%, 15%] | 77% [54%, 95%] | 0.33 | 0% | 52% | 0.59 [0.49, 0.72] | re-fusion of all |
| llm_only | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.70 | 33% | 50% | 0.58 [0.46, 0.72] | re-fusion of all |
| all_minus_keywords | 48 | 0.69 [0.54, 0.81] | 58% | 85% | 73% [50%, 93%] | 15% [4%, 29%] | 0.64 | 33% | 46% | 0.56 [0.46, 0.66] | re-fusion of all |
| all_minus_patterns | 48 | 0.66 [0.48, 0.80] | 57% | 77% | 68% [41%, 91%] | 23% [4%, 44%] | 0.63 | 33% | 44% | 0.54 [0.40, 0.69] | re-fusion of all |
| all_minus_llm_judge | 48 | 0.36 [0.09, 0.62] | 86% | 23% | 5% [0%, 15%] | 77% [54%, 95%] | 0.33 | 0% | 52% | 0.59 [0.49, 0.72] | re-fusion of all |
| all_minus_geval | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.44 | 83% | 27% | 0.51 [0.45, 0.59] | re-fusion of all |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 48 | 0.67 [0.45, 0.84] | 68% | 65% | 36% [10%, 62%] | 35% [12%, 57%] | 0.10 | 67% | 40% | 0.65 [0.48, 0.81] |  |
| keywords | 48 | 0.20 [0.00, 0.44] | 75% | 12% | 5% [0%, 15%] | 88% [71%, 100%] | 0.25 | 0% | 50% | 0.53 [0.45, 0.63] | re-fusion of all |
| kw_patterns | 48 | 0.31 [0.00, 0.57] | 83% | 19% | 5% [0%, 15%] | 81% [58%, 100%] | 0.25 | 0% | 50% | 0.57 [0.47, 0.69] | re-fusion of all |
| kw_pat_judge | 48 | 0.67 [0.52, 0.79] | 52% | 92% | 100% [100%, 100%] | 8% [0%, 18%] | 0.43 | 83% | 23% | 0.46 [0.41, 0.50] | re-fusion of all |
| kw_pat_geval | 48 | 0.36 [0.09, 0.62] | 86% | 23% | 5% [0%, 15%] | 77% [54%, 95%] | 0.18 | 0% | 48% | 0.59 [0.49, 0.72] | re-fusion of all |
| llm_only | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.26 | 0% | 44% | 0.58 [0.45, 0.73] | re-fusion of all |
| all_minus_keywords | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.26 | 0% | 44% | 0.58 [0.45, 0.73] | re-fusion of all |
| all_minus_patterns | 48 | 0.64 [0.43, 0.80] | 71% | 58% | 27% [10%, 43%] | 42% [20%, 65%] | 0.10 | 33% | 40% | 0.65 [0.53, 0.78] | re-fusion of all |
| all_minus_llm_judge | 48 | 0.36 [0.09, 0.62] | 86% | 23% | 5% [0%, 15%] | 77% [54%, 95%] | 0.18 | 0% | 48% | 0.59 [0.49, 0.72] | re-fusion of all |
| all_minus_geval | 48 | 0.67 [0.52, 0.79] | 52% | 92% | 100% [100%, 100%] | 8% [0%, 18%] | 0.43 | 83% | 23% | 0.46 [0.41, 0.50] | re-fusion of all |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| all | 36% (!) | 1/4 | 36% | **no** | cv_far @ 2cc04e7f41 cfg c8c60e398c2fe3c8 (config changed since run), far_floor @ 2cc04e7f41 cfg c8c60e398c2fe3c8 (config changed since run) |
| keywords | 0% | 4/4 | 5% | yes | cv_far @ 2cc04e7f41 cfg e72e3a157b11f0e8 (config changed since run), far_floor @ 2cc04e7f41 cfg e72e3a157b11f0e8 (config changed since run) |
| kw_patterns | 0% | 4/4 | 5% | yes | cv_far @ 2cc04e7f41 cfg c1cc0991d0442f2e (config changed since run), far_floor @ 2cc04e7f41 cfg c1cc0991d0442f2e (config changed since run) |
| kw_pat_judge | 86% (!) | 0/4 | 100% | **no** | cv_far @ 2cc04e7f41 cfg d87519b636e1172a (config changed since run), far_floor @ 2cc04e7f41 cfg d87519b636e1172a (config changed since run) |
| kw_pat_geval | 5% | 4/4 | 5% | yes | cv_far @ 2cc04e7f41 cfg 57a0914e8abb1ac1 (config changed since run), far_floor @ 2cc04e7f41 cfg 57a0914e8abb1ac1 (config changed since run) |
| llm_only | 18% | 3/4 | 18% | yes | cv_far @ 2cc04e7f41 cfg 9b22b09d0048a96c (config changed since run), far_floor @ 2cc04e7f41 cfg 9b22b09d0048a96c (config changed since run) |
| all_minus_keywords | 18% | 3/4 | 18% | yes | cv_far @ 2cc04e7f41 cfg 8069d322218a9dee (config changed since run), far_floor @ 2cc04e7f41 cfg 8069d322218a9dee (config changed since run) |
| all_minus_patterns | 27% (!) | 1/4 | 27% | **no** | cv_far @ 2cc04e7f41 cfg 18a36795b50ebbaa (config changed since run), far_floor @ 2cc04e7f41 cfg 18a36795b50ebbaa (config changed since run) |
| all_minus_llm_judge | 5% | 4/4 | 5% | yes | cv_far @ 2cc04e7f41 cfg 57a0914e8abb1ac1 (config changed since run), far_floor @ 2cc04e7f41 cfg 57a0914e8abb1ac1 (config changed since run) |
| all_minus_geval | 86% (!) | 0/4 | 100% | **no** | cv_far @ 2cc04e7f41 cfg d87519b636e1172a (config changed since run), far_floor @ 2cc04e7f41 cfg d87519b636e1172a (config changed since run) |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] |  |
| keywords | 48 | 0.30 [0.00, 0.55] | 71% | 19% | 9% [0%, 30%] | 81% [60%, 100%] | 0.38 | 0% | 52% | 0.55 [0.42, 0.68] | re-fusion of all |
| kw_patterns | 48 | 0.40 [0.10, 0.64] | 78% | 27% | 9% [0%, 30%] | 73% [50%, 94%] | 0.38 | 0% | 52% | 0.59 [0.45, 0.73] | re-fusion of all |
| kw_pat_judge | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.50 | 83% | 29% | 0.51 [0.45, 0.59] | re-fusion of all |
| kw_pat_geval | 48 | 0.70 [0.56, 0.83] | 54% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.40 | 100% | 23% | 0.50 [0.50, 0.50] | re-fusion of all |
| llm_only | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.62 | 0% | 42% | 0.51 [0.45, 0.59] | re-fusion of all |
| all_minus_keywords | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.62 | 0% | 42% | 0.51 [0.45, 0.59] | re-fusion of all |
| all_minus_patterns | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.56 | 50% | 35% | 0.51 [0.45, 0.59] | re-fusion of all |
| all_minus_llm_judge | 48 | 0.70 [0.56, 0.83] | 54% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.40 | 100% | 23% | 0.50 [0.50, 0.50] | re-fusion of all |
| all_minus_geval | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.50 | 83% | 29% | 0.51 [0.45, 0.59] | re-fusion of all |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 0.55 | 0.45 | 0.70, 0.85, 0.65, 0.90 (FAR20: 0.95!, 0.95, 1.00!, 0.95!) | 71.6 | asr 21.5, diarize 18.3, checks 31.8 | 31.8 | 10.0 | 0 | 0 | e1954e9ab6 |
| keywords | 0.55 | 0.25 | 0.25, 0.25, 0.25, 0.25 (FAR20: 0.70, 0.70, 0.70, 0.95) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 0.0 | 0.0 | 0 | 0 | e1954e9ab6 |
| kw_patterns | 0.55 | 0.25 | 0.70, 0.25, 0.50, 0.25 (FAR20: 0.70, 0.70, 0.70, 0.95) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 0.0 | 0.0 | 0 | 0 | e1954e9ab6 |
| kw_pat_judge | 0.55 | 0.60 | 0.60, 0.75, 0.50, 0.60 (FAR20: 0.75!, 1.00!, 0.20!, 0.75!) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 15.6 | 5.0 | 0 | 0 | e1954e9ab6 |
| kw_pat_geval | 0.55 | 0.65 | 0.65, 0.65, 0.80, 0.65 (FAR20: 0.65, 0.65, 1.00, 0.65) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 16.3 | 5.0 | 0 | 0 | e1954e9ab6 |
| llm_only | 0.55 | 0.70 | 0.75, 0.75, 0.70, 0.70 (FAR20: 0.95!, 0.90, 1.00, 0.95) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 31.8 | 10.0 | 0 | 0 | e1954e9ab6 |
| all_minus_keywords | 0.55 | 0.70 | 0.70, 0.75, 0.70, 0.70 (FAR20: 0.95!, 0.90, 1.00, 0.95) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 31.8 | 10.0 | 0 | 0 | e1954e9ab6 |
| all_minus_patterns | 0.55 | 0.45 | 0.70, 0.85, 0.65, 0.45 (FAR20: 0.95!, 0.95, 1.00!, 0.95!) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 31.8 | 10.0 | 0 | 0 | e1954e9ab6 |
| all_minus_llm_judge | 0.55 | 0.65 | 0.65, 0.65, 0.80, 0.65 (FAR20: 0.65, 0.65, 1.00, 0.65) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 16.3 | 5.0 | 0 | 0 | e1954e9ab6 |
| all_minus_geval | 0.55 | 0.60 | 0.60, 0.75, 0.50, 0.60 (FAR20: 0.75!, 1.00!, 0.20!, 0.75!) | 0.0 | asr 21.5, diarize 18.3, checks 31.8 | 15.6 | 5.0 | 0 | 0 | e1954e9ab6 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| all | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| keywords | 0.77 / 75% / 0% | 0.00 / 7% / 100% | 0.00 / - / 100% | 0.45 / 36% / 62% | 0.48 / 27% / 62% |
| kw_patterns | 0.67 / 50% / 30% | 0.00 / 7% / 100% | 0.00 / - / 100% | 0.40 / 27% / 69% | 0.33 / 18% / 77% |
| kw_pat_judge | 0.71 / 100% / 0% | 0.58 / 86% / 10% | 0.91 / - / 17% | 0.69 / 91% / 8% | 0.69 / 91% / 8% |
| kw_pat_geval | 0.75 / 0% / 40% | 0.00 / 7% / 100% | 0.00 / - / 100% | 0.47 / 0% / 69% | 0.25 / 9% / 85% |
| llm_only | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |
| all_minus_keywords | 0.75 / 62% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.69 / 73% / 15% | 0.69 / 73% / 15% |
| all_minus_patterns | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.50 / - / 67% | 0.67 / 64% / 23% | 0.65 / 73% / 23% |
| all_minus_llm_judge | 0.75 / 0% / 40% | 0.00 / 7% / 100% | 0.00 / - / 100% | 0.47 / 0% / 69% | 0.25 / 9% / 85% |
| all_minus_geval | 0.71 / 100% / 0% | 0.58 / 86% / 10% | 0.91 / - / 17% | 0.69 / 91% / 8% | 0.69 / 91% / 8% |

## `keywords` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = keywords - all

| metric | all | keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.55 | -0.136 | [-0.339, +0.042] | no detectable difference |
| alarm AUC | 0.77 | 0.64 | -0.129 | [-0.299, +0.039] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = keywords - all

| metric | all | keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.47 | -0.202 | [-0.467, +0.019] | no detectable difference |
| alarm_f1 | 0.55 | 0.50 | -0.052 | [-0.228, +0.111] | no detectable difference |
| false_alarm_rate | 45% | 32% | -14pp | [-54pp, +36pp] | no detectable difference |
| miss_rate | 31% | 62% | +31pp | [+4pp, +60pp] | **real**: all better |
| accuracy | 50% | 50% | +0pp | [-27pp, +21pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.53 | -0.086 | [-0.341, +0.138] | no detectable difference |

McNemar exact (calls): flag correct only-all 14 vs only-keywords 9, p=0.4049; 3-class only-all 9 vs only-keywords 9, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = keywords - all

| metric | all | keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.20 | -0.467 | [-0.741, -0.167] | **real**: all better |
| alarm_f1 | 0.10 | 0.25 | +0.155 | [-0.200, +0.483] | no detectable difference |
| false_alarm_rate | 36% | 5% | -32pp | [-61pp, -6pp] | **real**: keywords better |
| miss_rate | 35% | 88% | +54pp | [+27pp, +81pp] | **real**: all better |
| accuracy | 40% | 50% | +10pp | [-13pp, +33pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.54 | -0.110 | [-0.295, +0.077] | no detectable difference |

McNemar exact (calls): flag correct only-all 15 vs only-keywords 8, p=0.21; 3-class only-all 5 vs only-keywords 10, p=0.3018.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = keywords - all

| metric | all | keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.30 | -0.383 | [-0.655, -0.121] | **real**: all better |
| alarm_f1 | 0.63 | 0.38 | -0.247 | [-0.515, -0.022] | **real**: all better |
| false_alarm_rate | 91% | 9% | -82pp | [-100pp, -55pp] | **real**: keywords better |
| miss_rate | 8% | 81% | +73pp | [+50pp, +92pp] | **real**: all better |
| accuracy | 40% | 52% | +12pp | [-15pp, +38pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: all better |
| flag_balanced_accuracy | 0.51 | 0.55 | +0.044 | [-0.096, +0.183] | no detectable difference |

McNemar exact (calls): flag correct only-all 19 vs only-keywords 18, p=1.0; 3-class only-all 12 vs only-keywords 18, p=0.3616.

Flips (cv, 25 calls):

| call | expected | all | keywords | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | no_alert | 0.69/0.00 | fixed | 00:11-00:23 documentation: Sag Ja danken. Ich bin gerade daheim, ich habe am Samstag im Internet etwas gestellt, jetzt sehe ich den Betrag zweimal. Ich weiss nicht, ob ich selber etwas doppelt angekri... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D03-K1 | no_alert | review | alarm | 0.47/0.75 | same | 01:09-01:12 trade: Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung gesprochen, und einer hat als Beispiel gesagt, bevor die Bekanntgaben handeln, wer in der Tatrin? - keywords: Stichw... | geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot etwas ändert, und fragt nach den relevanten Informationen. Dies deutet darauf hin, dass sie versucht, Informationen vor der Kreditstel... |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.45/0.47 | broken | 01:10-01:13 trade: Steigerung des Umsatzes Im Artikel sind es 12 Prozent auf dem Blatt 5. Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung getätigt. Und einer hat als Beispiel gesagt, ... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D05-K2 | alarm | no_alert | alarm | 0.55/0.35 | fixed | 00:59-01:01 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - keywords: Stichwort K10 «Bestä... | llm_judge: Der Kunde nennt den Bestätigungscode, der noch gültig ist, im Gespräch. |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.54/0.35 | broken | 00:27-00:28 access: Gut, wir beginnen die zwei Sachen. Für das Passwort sagen Sie mir bitte nur, dass es nicht mehr ist. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.52/0.35 | broken | 00:28-00:28 access: Gut, nicht fehlen die zwei Sachen. Für das Passwort sagen Sie mir bitte nur, - keywords: Stichwort K10 «Passwort» (Zugangswörter) | llm_judge: Der Kunde spricht den Bestätigungscode 4826001 aus, der Teil des aktiven Anmeldevorgangs ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.35 | broken | 00:49-00:50 disclosure: Richtig, ich will auch gar nicht darüber ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. - keywords: Stichwort K11 «Vollmacht» (D... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.35 | broken | 00:50-00:51 disclosure: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheuc... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C01-K3 | no_alert | review | alarm | 0.43/0.33 | same | 00:38-00:38 trade: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. - ... | geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise für die Aufteilung einer Rechnung verwendet werden könnten, ohne dass die Mitarbeiter dies bestätigen oder ablehnen. Dies könnte darauf ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als Preisgabe eines aktiven Geheimnisses zählt. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 00:35-00:50 access: Im Formulat war das die Rechnungsreferenz. Ich habe die Nummer aus dem Rechnungsfeld des Händlers übernommen, es ist der Bezug zu dieser Bestellung, nicht zu meiner Karte. Die Fahr... | llm_judge: Die Kundin sagt die Zahlen 'vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier' vor, die sie aus dem Rechnungsfeld des Händlers... |
| Stufe2_C05-K4 | no_alert | review | no_alert | 0.85/0.00 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C07-K3 | alarm | review | no_alert | 0.68/0.00 | broken | 00:00-00:10 documentation: Guten Tag Frau Bühler, da ist Nadia Fuller, Sie wollen die Erfassung ihres Sparauftrags ändern, geht es um den Monat oder um den Betrag, - Kein Alarm: höchster Score 0.00 ('... | llm_judge: Die Kundin möchte, dass ihre bestehenden finanziellen Verpflichtungen (wie der monatliche Sparauftrag) nicht in die Notiz für die Kreditprüfung eingeordnet werden. Das ist ein klarer Fall v... |
| Stufe2_C07-K4 | alarm | review | no_alert | 0.70/0.00 | broken | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kunde erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Diese Informationen wer... |
| Stufe2_C08-K4 | no_alert | review | no_alert | 0.69/0.00 | fixed | 03:30-03:42 documentation: Ja, ich habe mich jetzt entschieden. Wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albisoptik kaufen. Können Sie den einmaligen Auftrag für mich en... | llm_judge: Die Kunde möchte absichtlich, dass eine bestehende rückzahlbare Verpflichtung für die Kreditprüfung nicht protokolliert wird. Dies wird in S019 durch den Wunsch der Kunde deutlich: 'Wegen d... |
| Stufe2_C09-K4 | alarm | review | no_alert | 0.43/0.00 | broken | 00:59-01:09 access: den Tfeil, ich habe erwartet, dass ich auf dem Telefon etwas bestätige, aber das ist nicht der Fall. da geht der Feil zum Bowser, vielleicht habe ich nur ein bisschen schnell abges... | geval: Die Kundin erwähnt, dass sie erwartet hatte, dass sie auf dem Telefon etwas bestätigen würde, was jedoch nicht der Fall war. Dies deutet darauf hin, dass sie möglicherweise Zugangsinformationen... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.74/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.73/0.00 | broken | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K3 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.75/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.00 | broken | 01:39-02:02 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. Weitere Kei weite Rebeta von aufzulesen. Für die näc... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C17-K4 | review | review | no_alert | 0.58/0.00 | broken | 01:40-01:49 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') ... | llm_judge: Der Kunde gibt einen Teil des Codes vor, nämlich die ersten zehn Ziffern, was als Preisgabe eines Zugangsgeheimnisses zu interpretieren ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | no_alert | 0.70/0.00 | broken | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 min... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `kw_patterns` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kw_patterns - all

| metric | all | kw_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.55 | -0.133 | [-0.333, +0.042] | no detectable difference |
| alarm AUC | 0.77 | 0.64 | -0.125 | [-0.295, +0.044] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_patterns - all

| metric | all | kw_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.37 | -0.298 | [-0.588, -0.042] | **real**: all better |
| alarm_f1 | 0.55 | 0.34 | -0.207 | [-0.459, -0.015] | **real**: all better |
| false_alarm_rate | 45% | 23% | -23pp | [-56pp, +19pp] | no detectable difference |
| miss_rate | 31% | 73% | +42pp | [+14pp, +73pp] | **real**: all better |
| accuracy | 50% | 46% | -4pp | [-30pp, +17pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.52 | -0.098 | [-0.321, +0.099] | no detectable difference |

McNemar exact (calls): flag correct only-all 15 vs only-kw_patterns 9, p=0.3075; 3-class only-all 10 vs only-kw_patterns 8, p=0.8145.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_patterns - all

| metric | all | kw_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.31 | -0.354 | [-0.706, -0.022] | **real**: all better |
| alarm_f1 | 0.10 | 0.25 | +0.155 | [-0.200, +0.483] | no detectable difference |
| false_alarm_rate | 36% | 5% | -32pp | [-61pp, -6pp] | **real**: kw_patterns better |
| miss_rate | 35% | 81% | +46pp | [+14pp, +79pp] | **real**: all better |
| accuracy | 40% | 50% | +10pp | [-13pp, +33pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.57 | -0.072 | [-0.274, +0.134] | no detectable difference |

McNemar exact (calls): flag correct only-all 14 vs only-kw_patterns 9, p=0.4049; 3-class only-all 5 vs only-kw_patterns 10, p=0.3018.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_patterns - all

| metric | all | kw_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.40 | -0.286 | [-0.568, -0.037] | **real**: all better |
| alarm_f1 | 0.63 | 0.38 | -0.247 | [-0.515, -0.022] | **real**: all better |
| false_alarm_rate | 91% | 9% | -82pp | [-100pp, -55pp] | **real**: kw_patterns better |
| miss_rate | 8% | 73% | +65pp | [+42pp, +88pp] | **real**: all better |
| accuracy | 40% | 52% | +12pp | [-15pp, +38pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: all better |
| flag_balanced_accuracy | 0.51 | 0.59 | +0.082 | [-0.068, +0.229] | no detectable difference |

McNemar exact (calls): flag correct only-all 17 vs only-kw_patterns 18, p=1.0; 3-class only-all 12 vs only-kw_patterns 18, p=0.3616.

Flips (cv, 26 calls):

| call | expected | all | kw_patterns | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | no_alert | 0.69/0.00 | fixed | 00:11-00:23 documentation: Sag Ja danken. Ich bin gerade daheim, ich habe am Samstag im Internet etwas gestellt, jetzt sehe ich den Betrag zweimal. Ich weiss nicht, ob ich selber etwas doppelt angekri... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D02-K2 | alarm | alarm | no_alert | 0.68/0.34 | broken | 01:33-01:34 trade: Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. - keywords: Stichwort K03 «Quartalszahlen» (Marktrelevanter Inhalt) – ähnlich: «Quatalszahlen» (96 %) | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D03-K1 | no_alert | review | alarm | 0.47/0.75 | same | 01:09-01:12 trade: Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung gesprochen, und einer hat als Beispiel gesagt, bevor die Bekanntgaben handeln, wer in der Tatrin? - keywords: Stichw... | geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot etwas ändert, und fragt nach den relevanten Informationen. Dies deutet darauf hin, dass sie versucht, Informationen vor der Kreditstel... |
| Stufe1_D03-K2 | no_alert | no_alert | review | 0.45/0.47 | broken | 01:10-01:13 trade: Steigerung des Umsatzes Im Artikel sind es 12 Prozent auf dem Blatt 5. Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung getätigt. Und einer hat als Beispiel gesagt, ... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D05-K2 | alarm | no_alert | review | 0.55/0.43 | fixed | 01:21-01:23 access: Warte, ich sage Ihnen die Planung gerade, 7, 3, 1, 9, 4, 2, es steht immer noch geültig. Können Sie mir sagen, ob das die richtige Reihe in Folge ist? - patterns: Kundschaft liest ... | llm_judge: Der Kunde nennt den Bestätigungscode, der noch gültig ist, im Gespräch. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.35 | broken | 00:49-00:50 disclosure: Richtig, ich will auch gar nicht darüber ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. - keywords: Stichwort K11 «Vollmacht» (D... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.35 | broken | 00:50-00:51 disclosure: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheuc... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.92/0.35 | broken | 02:38-02:39 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Die Kunde möchte, dass die 20'000 Franken von ihrer Tante als eigenes Eigenmittel dargestellt werden, um die interne Prüfung zu umgehen. Diese Aussage zeigt, dass sie versucht, die Kontroll... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.88/0.35 | broken | 02:40-02:41 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht protokoll... | llm_judge: Die Kundenin versucht, eine bestehende Rückzahlbare Verpflichtung (20'000 Franken ihrer Tante) vor der Kreditstelle zu verbergen, indem sie den Wunsch äußert, diese nicht in die Notiz zu ne... |
| Stufe2_C01-K3 | no_alert | review | alarm | 0.43/0.33 | same | 00:38-00:38 trade: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. - ... | geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise für die Aufteilung einer Rechnung verwendet werden könnten, ohne dass die Mitarbeiter dies bestätigen oder ablehnen. Dies könnte darauf ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als Preisgabe eines aktiven Geheimnisses zählt. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 00:35-00:50 access: Im Formulat war das die Rechnungsreferenz. Ich habe die Nummer aus dem Rechnungsfeld des Händlers übernommen, es ist der Bezug zu dieser Bestellung, nicht zu meiner Karte. Die Fahr... | llm_judge: Die Kundin sagt die Zahlen 'vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier' vor, die sie aus dem Rechnungsfeld des Händlers... |
| Stufe2_C05-K4 | no_alert | review | no_alert | 0.85/0.00 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C07-K3 | alarm | review | no_alert | 0.68/0.00 | broken | 00:00-00:10 documentation: Guten Tag Frau Bühler, da ist Nadia Fuller, Sie wollen die Erfassung ihres Sparauftrags ändern, geht es um den Monat oder um den Betrag, - Kein Alarm: höchster Score 0.00 ('... | llm_judge: Die Kundin möchte, dass ihre bestehenden finanziellen Verpflichtungen (wie der monatliche Sparauftrag) nicht in die Notiz für die Kreditprüfung eingeordnet werden. Das ist ein klarer Fall v... |
| Stufe2_C07-K4 | alarm | review | no_alert | 0.70/0.00 | broken | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kunde erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Diese Informationen wer... |
| Stufe2_C08-K4 | no_alert | review | no_alert | 0.69/0.00 | fixed | 03:30-03:42 documentation: Ja, ich habe mich jetzt entschieden. Wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albisoptik kaufen. Können Sie den einmaligen Auftrag für mich en... | llm_judge: Die Kunde möchte absichtlich, dass eine bestehende rückzahlbare Verpflichtung für die Kreditprüfung nicht protokolliert wird. Dies wird in S019 durch den Wunsch der Kunde deutlich: 'Wegen d... |
| Stufe2_C09-K4 | alarm | review | no_alert | 0.43/0.00 | broken | 00:59-01:09 access: den Tfeil, ich habe erwartet, dass ich auf dem Telefon etwas bestätige, aber das ist nicht der Fall. da geht der Feil zum Bowser, vielleicht habe ich nur ein bisschen schnell abges... | geval: Die Kundin erwähnt, dass sie erwartet hatte, dass sie auf dem Telefon etwas bestätigen würde, was jedoch nicht der Fall war. Dies deutet darauf hin, dass sie möglicherweise Zugangsinformationen... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.74/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.73/0.00 | broken | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K3 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.75/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.00 | broken | 01:39-02:02 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. Weitere Kei weite Rebeta von aufzulesen. Für die näc... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C17-K4 | review | review | no_alert | 0.58/0.00 | broken | 01:40-01:49 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') ... | llm_judge: Der Kunde gibt einen Teil des Codes vor, nämlich die ersten zehn Ziffern, was als Preisgabe eines Zugangsgeheimnisses zu interpretieren ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | no_alert | 0.70/0.00 | broken | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.35 (Schwelle 0.50 min... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `kw_pat_judge` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kw_pat_judge - all

| metric | all | kw_pat_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.67 | -0.009 | [-0.051, +0.036] | no detectable difference |
| alarm AUC | 0.77 | 0.75 | -0.019 | [-0.070, +0.027] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_pat_judge - all

| metric | all | kw_pat_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.019 | [-0.105, +0.160] | no detectable difference |
| alarm_f1 | 0.55 | 0.44 | -0.107 | [-0.245, +0.013] | no detectable difference |
| false_alarm_rate | 45% | 91% | +45pp | [+21pp, +75pp] | **real**: all better |
| miss_rate | 31% | 8% | -23pp | [-45pp, -5pp] | **real**: kw_pat_judge better |
| accuracy | 50% | 27% | -23pp | [-38pp, -9pp] | **real**: all better |
| review_recall | 67% | 83% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.51 | -0.112 | [-0.268, +0.017] | no detectable difference |

McNemar exact (calls): flag correct only-all 10 vs only-kw_pat_judge 6, p=0.4545; 3-class only-all 12 vs only-kw_pat_judge 1, p=0.0034.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_pat_judge - all

| metric | all | kw_pat_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.67 | +0.000 | [-0.140, +0.150] | no detectable difference |
| alarm_f1 | 0.10 | 0.43 | +0.333 | [+0.087, +0.561] | **real**: kw_pat_judge better |
| false_alarm_rate | 36% | 100% | +64pp | [+38pp, +90pp] | **real**: all better |
| miss_rate | 35% | 8% | -27pp | [-50pp, -8pp] | **real**: kw_pat_judge better |
| accuracy | 40% | 23% | -17pp | [-36pp, +7pp] | no detectable difference |
| review_recall | 67% | 83% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.46 | -0.184 | [-0.341, -0.026] | **real**: all better |

McNemar exact (calls): flag correct only-all 14 vs only-kw_pat_judge 7, p=0.1892; 3-class only-all 14 vs only-kw_pat_judge 6, p=0.1153.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_pat_judge - all

| metric | all | kw_pat_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.50 | -0.132 | [-0.357, +0.088] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 29% | -10pp | [-22pp, +2pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-kw_pat_judge 0, p=1.0; 3-class only-all 6 vs only-kw_pat_judge 1, p=0.125.

Flips (cv, 19 calls):

| call | expected | all | kw_pat_judge | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.43/0.32 | broken | 01:41-02:39 documentation: Dank geht das Land für die Ordnung, der Eintrag mit dem Ursymbol bei Reservation auf den Zahlungsmitteln, keine zweite definitive Belastung. Und wenn der Laden die Reservati... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktives Geheimnis ist oder ob es ... |
| Stufe1_D02-K2 | alarm | alarm | review | 0.68/0.87 | same | 01:28-01:31 documentation: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es r... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D03-K2 | no_alert | no_alert | review | 0.45/0.40 | broken | 01:10-01:13 trade: Steigerung des Umsatzes Im Artikel sind es 12 Prozent auf dem Blatt 5. Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung getätigt. Und einer hat als Beispiel gesagt, ... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D05-K2 | alarm | no_alert | review | 0.55/0.61 | fixed | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Der Kunde nennt den... | llm_judge: Der Kunde nennt den Bestätigungscode, der noch gültig ist, im Gespräch. |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.54/0.59 | broken | 01:35-02:02 documentation: Gerätewechsel, aber auf dem Blatt, das ich herausgerückt habe, steht der Lehrstofzugang. Ich habe also vermutlich das falsche Blatt ausgenommen und in der Mail schrieb jeman... | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.52/0.55 | broken | 03:21-03:37 access: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum Teil. - ... | llm_judge: Der Kunde spricht den Bestätigungscode 4826001 aus, der Teil des aktiven Anmeldevorgangs ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.89 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.54/0.59 | broken | 00:12-00:27 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe1_D09-K1 | alarm | alarm | review | 0.92/0.89 | same | 02:37-03:00 splitting: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und d... | llm_judge: Die Kunde möchte, dass die 20'000 Franken von ihrer Tante als eigenes Eigenmittel dargestellt werden, um die interne Prüfung zu umgehen. Diese Aussage zeigt, dass sie versucht, die Kontroll... |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.70/0.89 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C06-K3 | alarm | no_alert | review | 0.70/0.88 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | review | 0.70/0.89 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.54/0.59 | broken | 03:27-04:09 documentation: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, könnte sie den einmaligen Auftrag für mich e... | llm_judge: Die Kunde erwähnt, dass sie den Absatzbericht der Albisoptik gelesen hat, der noch nicht offiziell bekanntgegeben wurde. Der Advisor bestätigt, dass der Kaufwunsch mit den genannten Quellen... |
| Stufe2_C11-K3 | no_alert | no_alert | review | 0.69/0.87 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | review | 0.70/0.89 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | review | 0.70/0.89 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | review | 0.70/0.89 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.89 | same | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe3_C20-K3 | review | no_alert | review | 0.53/0.57 | fixed | 01:49-02:11 documentation: Können Sie die 4000 für heute und die 5000 für morgen trotzdem schon vorbeweiten? Ich kann Ihnen noch nicht sagen, warum das getrennt plant ist oder welche Belege zusammenge... | llm_judge: Die Kunde möchte zwei verschiedene Daten (4000 für heute und 5000 für morgen) vorbeweisen, ohne dass die zugehörigen Unterlagen bereitgestellt wurden. Der Advisor bestätigt dies und wartet ... |

## `kw_pat_geval` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kw_pat_geval - all

| metric | all | kw_pat_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.57 | -0.118 | [-0.292, +0.045] | no detectable difference |
| alarm AUC | 0.77 | 0.67 | -0.097 | [-0.278, +0.052] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_pat_geval - all

| metric | all | kw_pat_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.36 | -0.303 | [-0.545, -0.065] | **real**: all better |
| alarm_f1 | 0.55 | 0.33 | -0.218 | [-0.454, +0.000] | no detectable difference |
| false_alarm_rate | 45% | 5% | -41pp | [-69pp, -11pp] | **real**: kw_pat_geval better |
| miss_rate | 31% | 77% | +46pp | [+23pp, +68pp] | **real**: all better |
| accuracy | 50% | 52% | +2pp | [-23pp, +26pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.59 | -0.026 | [-0.172, +0.127] | no detectable difference |

McNemar exact (calls): flag correct only-all 12 vs only-kw_pat_geval 9, p=0.6636; 3-class only-all 8 vs only-kw_pat_geval 9, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_pat_geval - all

| metric | all | kw_pat_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.36 | -0.303 | [-0.571, -0.048] | **real**: all better |
| alarm_f1 | 0.10 | 0.18 | +0.087 | [+0.000, +0.214] | no detectable difference |
| false_alarm_rate | 36% | 5% | -32pp | [-60pp, -6pp] | **real**: kw_pat_geval better |
| miss_rate | 35% | 77% | +42pp | [+19pp, +67pp] | **real**: all better |
| accuracy | 40% | 48% | +8pp | [-11pp, +29pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.59 | -0.052 | [-0.208, +0.118] | no detectable difference |

McNemar exact (calls): flag correct only-all 11 vs only-kw_pat_geval 7, p=0.4807; 3-class only-all 4 vs only-kw_pat_geval 8, p=0.3877.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kw_pat_geval - all

| metric | all | kw_pat_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.017 | [-0.006, +0.058] | no detectable difference |
| alarm_f1 | 0.63 | 0.40 | -0.232 | [-0.506, +0.000] | no detectable difference |
| false_alarm_rate | 91% | 100% | +9pp | [+0pp, +30pp] | no detectable difference |
| miss_rate | 8% | 0% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 40% | 23% | -17pp | [-30pp, -2pp] | **real**: all better |
| review_recall | 83% | 100% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.50 | -0.007 | [-0.089, +0.054] | no detectable difference |

McNemar exact (calls): flag correct only-all 2 vs only-kw_pat_geval 2, p=1.0; 3-class only-all 9 vs only-kw_pat_geval 1, p=0.0215.

Flips (cv, 23 calls):

| call | expected | all | kw_pat_geval | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | no_alert | 0.69/0.46 | fixed | 01:42-01:53 disclosure: So, danke, dass sie lern für die Ordnung. Der Eintrag mit dem Ursymbol ist eine Reservation auf den Zahlungsmitteln keine zweite definitive Belastung. - geval: Der Advisor gibt... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D02-K2 | alarm | alarm | no_alert | 0.68/0.51 | broken | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - geval: Der Kunde erwähnt, dass er Informationen aus einer privaten Quelle hat, die er der Beraterin zeigt, u... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.53 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot ... | geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot etwas ändert, und fragt nach den relevanten Informationen. Dies deutet darauf hin, dass sie versucht, Informationen vor der Kreditstel... |
| Stufe1_D04-K2 | alarm | alarm | no_alert | 0.82/0.63 | broken | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine potenzielle Übernahme gegeben hat, die noch nicht veröffentlicht wurde. Sie möchte diese Informationen nutzen,... |
| Stufe1_D05-K1 | alarm | review | no_alert | 0.70/0.47 | broken | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - patterns: Kundschaft liest möglichen... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D09-K1 | alarm | alarm | review | 0.92/0.87 | same | 02:37-03:00 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Die Kunde möchte, dass die 20'000 Franken von ihrer Tante als eigenes Eigenmittel dargestellt werden, um die interne Prüfung zu umgehen. Diese Aussage zeigt, dass sie versucht, die Kontroll... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.88/0.75 | same | 02:39-03:02 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen u... | llm_judge: Die Kundenin versucht, eine bestehende Rückzahlbare Verpflichtung (20'000 Franken ihrer Tante) vor der Kreditstelle zu verbergen, indem sie den Wunsch äußert, diese nicht in die Notiz zu ne... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.43/0.48 | fixed | 01:54-02:10 disclosure: Dann steht 4, 2, 4, 2, 3, 2, 3, 2, 3, 2, 3, 2. Wir machen hier keine weiteren Zahl abweich am Telefon. - geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise zu eine... | geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise für die Aufteilung einer Rechnung verwendet werden könnten, ohne dass die Mitarbeiter dies bestätigen oder ablehnen. Dies könnte darauf ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.69/0.46 | fixed | 01:57-02:11 disclosure: Hier steht 4242424242424242424242424242424242424242424242424242. Wir machen hier keine weiteren Zahl abweich am Telefon. - geval: Der Kunde gibt eine lange Reihe von Zahlen, di... | llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als Preisgabe eines aktiven Geheimnisses zählt. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.46 | fixed | 01:55-02:17 disclosure: Da steht 4242-3242-3232-3232-3232. Wir machen da keine weiteren Zahl abweich am Telefon, für die Rückfrage stelle ich Ihnen den sicheren Kanal bereit und ich notiere den Urspru... | llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | review | no_alert | 0.70/0.46 | fixed | 01:43-02:13 disclosure: Also von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, sie haben von ihm gesagt, ich soll warten, aber ich habe sie jetzt... | llm_judge: Die Kundin sagt die Zahlen 'vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier' vor, die sie aus dem Rechnungsfeld des Händlers... |
| Stufe2_C07-K3 | alarm | review | no_alert | 0.68/0.46 | broken | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihre bestehenden finanziellen Verpflichtungen (wie der monatliche Sparauftrag) nicht in die Notiz für die Kreditprüfung eingeordnet werden. Das ist ein klarer Fall v... |
| Stufe2_C07-K4 | alarm | review | no_alert | 0.70/0.46 | broken | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kunde erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Diese Informationen wer... |
| Stufe2_C08-K4 | no_alert | review | no_alert | 0.69/0.46 | fixed | 00:35-00:53 trade: Ich habe gestern den neuen Absatzbericht auf der Merkseite der Albisoptik gelesen, der ging am Morgen an die Medien und für alle verfügbar, es wurde deutlich mehr verkauft als erwar... | llm_judge: Die Kunde möchte absichtlich, dass eine bestehende rückzahlbare Verpflichtung für die Kreditprüfung nicht protokolliert wird. Dies wird in S019 durch den Wunsch der Kunde deutlich: 'Wegen d... |
| Stufe2_C09-K4 | alarm | review | no_alert | 0.43/0.46 | broken | 00:59-01:09 access: den Tfeil, ich habe erwartet, dass ich auf dem Telefon etwas bestätige, aber das ist nicht der Fall. da geht der Feil zum Bowser, vielleicht habe ich nur ein bisschen schnell abges... | geval: Die Kundin erwähnt, dass sie erwartet hatte, dass sie auf dem Telefon etwas bestätigen würde, was jedoch nicht der Fall war. Dies deutet darauf hin, dass sie möglicherweise Zugangsinformationen... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.74/0.48 | broken | 07:54-08:14 documentation: Dann lehnt ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich ... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.73/0.47 | broken | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K3 | no_alert | alarm | no_alert | 0.70/0.46 | fixed | 01:09-01:21 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Aktuelle Adresse steht richtig im Kontaktfeld. - geval... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.75/0.49 | fixed | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.46 | broken | 00:34-00:42 trade: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war. - geval: Der Kunde erwähnt, dass er ein Screenshot gemacht h... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C17-K4 | review | review | no_alert | 0.58/0.46 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde gibt einen Teil des Codes vor, nämlich die ersten zehn Ziffern, was als Preisgabe eines Zugangsgeheimnisses zu interpretieren ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.46 | broken | 00:23-01:06 disclosure: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie ha... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | no_alert | 0.70/0.46 | broken | 00:23-00:32 disclosure: Dann müssen wir vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hinterlegt ihr der Schwester durch den Kontakt? - geval: Die ... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `llm_only` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = llm_only - all

| metric | all | llm_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.66 | -0.024 | [-0.092, +0.020] | no detectable difference |
| alarm AUC | 0.77 | 0.75 | -0.021 | [-0.083, +0.016] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = llm_only - all

| metric | all | llm_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.70 | +0.146 | [-0.079, +0.410] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 50% | +0pp | [-17pp, +14pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-all 5 vs only-llm_only 4, p=1.0; 3-class only-all 7 vs only-llm_only 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = llm_only - all

| metric | all | llm_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: all better |
| alarm_f1 | 0.10 | 0.26 | +0.166 | [+0.000, +0.323] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: all better |
| accuracy | 40% | 44% | +4pp | [-13pp, +18pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-all 8 vs only-llm_only 4, p=0.3877; 3-class only-all 4 vs only-llm_only 6, p=0.7539.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = llm_only - all

| metric | all | llm_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.62 | -0.011 | [-0.224, +0.220] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 42% | +2pp | [-18pp, +18pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: all better |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-llm_only 0, p=1.0; 3-class only-all 5 vs only-llm_only 6, p=1.0.

Flips (cv, 17 calls):

| call | expected | all | llm_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | review | alarm | 0.70/0.75 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Die Kundin sagt den T... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.73 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.54/0.57 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.73 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.90 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.72 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.74 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.74/0.77 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.77 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.73 | same | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.75/0.78 | same | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.72 | same | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | alarm | 0.70/0.73 | same | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `all_minus_keywords` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = all_minus_keywords - all

| metric | all | all_minus_keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.69 | +0.010 | [-0.001, +0.027] | no detectable difference |
| alarm AUC | 0.77 | 0.78 | +0.008 | [-0.002, +0.022] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_keywords - all

| metric | all | all_minus_keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.021 | [-0.096, +0.149] | no detectable difference |
| alarm_f1 | 0.55 | 0.64 | +0.085 | [-0.127, +0.322] | no detectable difference |
| false_alarm_rate | 45% | 73% | +27pp | [+5pp, +55pp] | **real**: all better |
| miss_rate | 31% | 15% | -15pp | [-39pp, +5pp] | no detectable difference |
| accuracy | 50% | 46% | -4pp | [-23pp, +10pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.56 | -0.059 | [-0.196, +0.050] | no detectable difference |

McNemar exact (calls): flag correct only-all 7 vs only-all_minus_keywords 5, p=0.7744; 3-class only-all 9 vs only-all_minus_keywords 7, p=0.8036.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_keywords - all

| metric | all | all_minus_keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: all better |
| alarm_f1 | 0.10 | 0.26 | +0.166 | [+0.000, +0.323] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: all better |
| accuracy | 40% | 44% | +4pp | [-13pp, +18pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-all 8 vs only-all_minus_keywords 4, p=0.3877; 3-class only-all 4 vs only-all_minus_keywords 6, p=0.7539.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_keywords - all

| metric | all | all_minus_keywords | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.62 | -0.011 | [-0.224, +0.220] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 42% | +2pp | [-18pp, +18pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: all better |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-all_minus_keywords 0, p=1.0; 3-class only-all 5 vs only-all_minus_keywords 6, p=1.0.

Flips (cv, 19 calls):

| call | expected | all | all_minus_keywords | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | alarm | 0.69/0.72 | same | 00:11-00:23 documentation: Sag Ja danken. Ich bin gerade daheim, ich habe am Samstag im Internet etwas gestellt, jetzt sehe ich den Betrag zweimal. Ich weiss nicht, ob ich selber etwas doppelt angekri... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.54/0.57 | broken | 01:35-02:02 documentation: Gerätewechsel, aber auf dem Blatt, das ich herausgerückt habe, steht der Lehrstofzugang. Ich habe also vermutlich das falsche Blatt ausgenommen und in der Mail schrieb jeman... | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.73 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.54/0.57 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.73 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.90 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.72 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.74 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.73 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.74/0.77 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.77 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.75/0.78 | same | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.59 | broken | 01:39-02:02 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. Weitere Kei weite Rebeta von aufzulesen. Für die näc... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.72 | same | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | alarm | 0.70/0.73 | same | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |
| Stufe3_C20-K3 | review | no_alert | review | 0.53/0.56 | fixed | 01:49-02:11 documentation: Können Sie die 4000 für heute und die 5000 für morgen trotzdem schon vorbeweiten? Ich kann Ihnen noch nicht sagen, warum das getrennt plant ist oder welche Belege zusammenge... | llm_judge: Die Kunde möchte zwei verschiedene Daten (4000 für heute und 5000 für morgen) vorbeweisen, ohne dass die zugehörigen Unterlagen bereitgestellt wurden. Der Advisor bestätigt dies und wartet ... |

## `all_minus_patterns` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = all_minus_patterns - all

| metric | all | all_minus_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.65 | -0.035 | [-0.111, +0.006] | no detectable difference |
| alarm AUC | 0.77 | 0.74 | -0.029 | [-0.099, +0.007] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_patterns - all

| metric | all | all_minus_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.66 | -0.011 | [-0.160, +0.128] | no detectable difference |
| alarm_f1 | 0.55 | 0.63 | +0.080 | [-0.084, +0.298] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 23% | -8pp | [-33pp, +18pp] | no detectable difference |
| accuracy | 50% | 44% | -6pp | [-21pp, +4pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.54 | -0.075 | [-0.226, +0.048] | no detectable difference |

McNemar exact (calls): flag correct only-all 7 vs only-all_minus_patterns 4, p=0.5488; 3-class only-all 7 vs only-all_minus_patterns 4, p=0.5488.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_patterns - all

| metric | all | all_minus_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.64 | -0.028 | [-0.165, +0.065] | no detectable difference |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 27% | -9pp | [-25pp, +0pp] | no detectable difference |
| miss_rate | 35% | 42% | +8pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 40% | 40% | +0pp | [-12pp, +12pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.65 | +0.007 | [-0.101, +0.100] | no detectable difference |

McNemar exact (calls): flag correct only-all 2 vs only-all_minus_patterns 2, p=1.0; 3-class only-all 2 vs only-all_minus_patterns 2, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_patterns - all

| metric | all | all_minus_patterns | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.56 | -0.073 | [-0.201, +0.000] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 35% | -4pp | [-14pp, +0pp] | no detectable difference |
| review_recall | 83% | 50% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-all_minus_patterns 0, p=1.0; 3-class only-all 2 vs only-all_minus_patterns 0, p=0.5.

Flips (cv, 11 calls):

| call | expected | all | all_minus_patterns | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.58 | broken | 01:39-02:02 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. Weitere Kei weite Rebeta von aufzulesen. Für die näc... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C17-K4 | review | review | no_alert | 0.58/0.59 | broken | 01:40-01:49 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - llm_judge: Der Kunde gibt einen Teil des Codes vor... | llm_judge: Der Kunde gibt einen Teil des Codes vor, nämlich die ersten zehn Ziffern, was als Preisgabe eines Zugangsgeheimnisses zu interpretieren ist. |

## `all_minus_llm_judge` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = all_minus_llm_judge - all

| metric | all | all_minus_llm_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.57 | -0.118 | [-0.292, +0.045] | no detectable difference |
| alarm AUC | 0.77 | 0.67 | -0.097 | [-0.278, +0.052] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_llm_judge - all

| metric | all | all_minus_llm_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.36 | -0.303 | [-0.545, -0.065] | **real**: all better |
| alarm_f1 | 0.55 | 0.33 | -0.218 | [-0.454, +0.000] | no detectable difference |
| false_alarm_rate | 45% | 5% | -41pp | [-69pp, -11pp] | **real**: all_minus_llm_judge better |
| miss_rate | 31% | 77% | +46pp | [+23pp, +68pp] | **real**: all better |
| accuracy | 50% | 52% | +2pp | [-23pp, +26pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.59 | -0.026 | [-0.172, +0.127] | no detectable difference |

McNemar exact (calls): flag correct only-all 12 vs only-all_minus_llm_judge 9, p=0.6636; 3-class only-all 8 vs only-all_minus_llm_judge 9, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_llm_judge - all

| metric | all | all_minus_llm_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.36 | -0.303 | [-0.571, -0.048] | **real**: all better |
| alarm_f1 | 0.10 | 0.18 | +0.087 | [+0.000, +0.214] | no detectable difference |
| false_alarm_rate | 36% | 5% | -32pp | [-60pp, -6pp] | **real**: all_minus_llm_judge better |
| miss_rate | 35% | 77% | +42pp | [+19pp, +67pp] | **real**: all better |
| accuracy | 40% | 48% | +8pp | [-11pp, +29pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.59 | -0.052 | [-0.208, +0.118] | no detectable difference |

McNemar exact (calls): flag correct only-all 11 vs only-all_minus_llm_judge 7, p=0.4807; 3-class only-all 4 vs only-all_minus_llm_judge 8, p=0.3877.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_llm_judge - all

| metric | all | all_minus_llm_judge | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.017 | [-0.006, +0.058] | no detectable difference |
| alarm_f1 | 0.63 | 0.40 | -0.232 | [-0.506, +0.000] | no detectable difference |
| false_alarm_rate | 91% | 100% | +9pp | [+0pp, +30pp] | no detectable difference |
| miss_rate | 8% | 0% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 40% | 23% | -17pp | [-30pp, -2pp] | **real**: all better |
| review_recall | 83% | 100% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.50 | -0.007 | [-0.089, +0.054] | no detectable difference |

McNemar exact (calls): flag correct only-all 2 vs only-all_minus_llm_judge 2, p=1.0; 3-class only-all 9 vs only-all_minus_llm_judge 1, p=0.0215.

Flips (cv, 23 calls):

| call | expected | all | all_minus_llm_judge | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | no_alert | 0.69/0.46 | fixed | 01:42-01:53 disclosure: So, danke, dass sie lern für die Ordnung. Der Eintrag mit dem Ursymbol ist eine Reservation auf den Zahlungsmitteln keine zweite definitive Belastung. - geval: Der Advisor gibt... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D02-K2 | alarm | alarm | no_alert | 0.68/0.51 | broken | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - geval: Der Kunde erwähnt, dass er Informationen aus einer privaten Quelle hat, die er der Beraterin zeigt, u... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.53 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot ... | geval: Die Kunde möchte den Bericht verstehen, bevor sie im Depot etwas ändert, und fragt nach den relevanten Informationen. Dies deutet darauf hin, dass sie versucht, Informationen vor der Kreditstel... |
| Stufe1_D04-K2 | alarm | alarm | no_alert | 0.82/0.63 | broken | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine potenzielle Übernahme gegeben hat, die noch nicht veröffentlicht wurde. Sie möchte diese Informationen nutzen,... |
| Stufe1_D05-K1 | alarm | review | no_alert | 0.70/0.47 | broken | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - patterns: Kundschaft liest möglichen... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D09-K1 | alarm | alarm | review | 0.92/0.87 | same | 02:37-03:00 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Die Kunde möchte, dass die 20'000 Franken von ihrer Tante als eigenes Eigenmittel dargestellt werden, um die interne Prüfung zu umgehen. Diese Aussage zeigt, dass sie versucht, die Kontroll... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.88/0.75 | same | 02:39-03:02 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen u... | llm_judge: Die Kundenin versucht, eine bestehende Rückzahlbare Verpflichtung (20'000 Franken ihrer Tante) vor der Kreditstelle zu verbergen, indem sie den Wunsch äußert, diese nicht in die Notiz zu ne... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.43/0.48 | fixed | 01:54-02:10 disclosure: Dann steht 4, 2, 4, 2, 3, 2, 3, 2, 3, 2, 3, 2. Wir machen hier keine weiteren Zahl abweich am Telefon. - geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise zu eine... | geval: Der Kunde gibt eine Reihe von Zahlen, die möglicherweise für die Aufteilung einer Rechnung verwendet werden könnten, ohne dass die Mitarbeiter dies bestätigen oder ablehnen. Dies könnte darauf ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.69/0.46 | fixed | 01:57-02:11 disclosure: Hier steht 4242424242424242424242424242424242424242424242424242. Wir machen hier keine weiteren Zahl abweich am Telefon. - geval: Der Kunde gibt eine lange Reihe von Zahlen, di... | llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als Preisgabe eines aktiven Geheimnisses zählt. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.46 | fixed | 01:55-02:17 disclosure: Da steht 4242-3242-3232-3232-3232. Wir machen da keine weiteren Zahl abweich am Telefon, für die Rückfrage stelle ich Ihnen den sicheren Kanal bereit und ich notiere den Urspru... | llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | review | no_alert | 0.70/0.46 | fixed | 01:43-02:13 disclosure: Also von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, sie haben von ihm gesagt, ich soll warten, aber ich habe sie jetzt... | llm_judge: Die Kundin sagt die Zahlen 'vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier' vor, die sie aus dem Rechnungsfeld des Händlers... |
| Stufe2_C07-K3 | alarm | review | no_alert | 0.68/0.46 | broken | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihre bestehenden finanziellen Verpflichtungen (wie der monatliche Sparauftrag) nicht in die Notiz für die Kreditprüfung eingeordnet werden. Das ist ein klarer Fall v... |
| Stufe2_C07-K4 | alarm | review | no_alert | 0.70/0.46 | broken | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kunde erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Diese Informationen wer... |
| Stufe2_C08-K4 | no_alert | review | no_alert | 0.69/0.46 | fixed | 00:35-00:53 trade: Ich habe gestern den neuen Absatzbericht auf der Merkseite der Albisoptik gelesen, der ging am Morgen an die Medien und für alle verfügbar, es wurde deutlich mehr verkauft als erwar... | llm_judge: Die Kunde möchte absichtlich, dass eine bestehende rückzahlbare Verpflichtung für die Kreditprüfung nicht protokolliert wird. Dies wird in S019 durch den Wunsch der Kunde deutlich: 'Wegen d... |
| Stufe2_C09-K4 | alarm | review | no_alert | 0.43/0.46 | broken | 00:59-01:09 access: den Tfeil, ich habe erwartet, dass ich auf dem Telefon etwas bestätige, aber das ist nicht der Fall. da geht der Feil zum Bowser, vielleicht habe ich nur ein bisschen schnell abges... | geval: Die Kundin erwähnt, dass sie erwartet hatte, dass sie auf dem Telefon etwas bestätigen würde, was jedoch nicht der Fall war. Dies deutet darauf hin, dass sie möglicherweise Zugangsinformationen... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.74/0.48 | broken | 07:54-08:14 documentation: Dann lehnt ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich ... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.73/0.47 | broken | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K3 | no_alert | alarm | no_alert | 0.70/0.46 | fixed | 01:09-01:21 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Aktuelle Adresse steht richtig im Kontaktfeld. - geval... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.75/0.49 | fixed | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.46 | broken | 00:34-00:42 trade: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war. - geval: Der Kunde erwähnt, dass er ein Screenshot gemacht h... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C17-K4 | review | review | no_alert | 0.58/0.46 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde gibt einen Teil des Codes vor, nämlich die ersten zehn Ziffern, was als Preisgabe eines Zugangsgeheimnisses zu interpretieren ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.46 | broken | 00:23-01:06 disclosure: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie ha... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | no_alert | 0.70/0.46 | broken | 00:23-00:32 disclosure: Dann müssen wir vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hinterlegt ihr der Schwester durch den Kontakt? - geval: Die ... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `all_minus_geval` vs `all`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = all_minus_geval - all

| metric | all | all_minus_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.67 | -0.009 | [-0.051, +0.036] | no detectable difference |
| alarm AUC | 0.77 | 0.75 | -0.019 | [-0.070, +0.027] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_geval - all

| metric | all | all_minus_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.019 | [-0.105, +0.160] | no detectable difference |
| alarm_f1 | 0.55 | 0.44 | -0.107 | [-0.245, +0.013] | no detectable difference |
| false_alarm_rate | 45% | 91% | +45pp | [+21pp, +75pp] | **real**: all better |
| miss_rate | 31% | 8% | -23pp | [-45pp, -5pp] | **real**: all_minus_geval better |
| accuracy | 50% | 27% | -23pp | [-38pp, -9pp] | **real**: all better |
| review_recall | 67% | 83% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.51 | -0.112 | [-0.268, +0.017] | no detectable difference |

McNemar exact (calls): flag correct only-all 10 vs only-all_minus_geval 6, p=0.4545; 3-class only-all 12 vs only-all_minus_geval 1, p=0.0034.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_geval - all

| metric | all | all_minus_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.67 | +0.000 | [-0.140, +0.150] | no detectable difference |
| alarm_f1 | 0.10 | 0.43 | +0.333 | [+0.087, +0.561] | **real**: all_minus_geval better |
| false_alarm_rate | 36% | 100% | +64pp | [+38pp, +90pp] | **real**: all better |
| miss_rate | 35% | 8% | -27pp | [-50pp, -8pp] | **real**: all_minus_geval better |
| accuracy | 40% | 23% | -17pp | [-36pp, +7pp] | no detectable difference |
| review_recall | 67% | 83% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.46 | -0.184 | [-0.341, -0.026] | **real**: all better |

McNemar exact (calls): flag correct only-all 14 vs only-all_minus_geval 7, p=0.1892; 3-class only-all 14 vs only-all_minus_geval 6, p=0.1153.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_minus_geval - all

| metric | all | all_minus_geval | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.50 | -0.132 | [-0.357, +0.088] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 29% | -10pp | [-22pp, +2pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-all_minus_geval 0, p=1.0; 3-class only-all 6 vs only-all_minus_geval 1, p=0.125.

Flips (cv, 19 calls):

| call | expected | all | all_minus_geval | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.43/0.32 | broken | 01:41-02:39 documentation: Dank geht das Land für die Ordnung, der Eintrag mit dem Ursymbol bei Reservation auf den Zahlungsmitteln, keine zweite definitive Belastung. Und wenn der Laden die Reservati... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktives Geheimnis ist oder ob es ... |
| Stufe1_D02-K2 | alarm | alarm | review | 0.68/0.87 | same | 01:28-01:31 documentation: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es r... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D03-K2 | no_alert | no_alert | review | 0.45/0.40 | broken | 01:10-01:13 trade: Steigerung des Umsatzes Im Artikel sind es 12 Prozent auf dem Blatt 5. Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung getätigt. Und einer hat als Beispiel gesagt, ... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D05-K2 | alarm | no_alert | review | 0.55/0.61 | fixed | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Der Kunde nennt den... | llm_judge: Der Kunde nennt den Bestätigungscode, der noch gültig ist, im Gespräch. |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.54/0.59 | broken | 01:35-02:02 documentation: Gerätewechsel, aber auf dem Blatt, das ich herausgerückt habe, steht der Lehrstofzugang. Ich habe also vermutlich das falsche Blatt ausgenommen und in der Mail schrieb jeman... | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.52/0.55 | broken | 03:21-03:37 access: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum Teil. - ... | llm_judge: Der Kunde spricht den Bestätigungscode 4826001 aus, der Teil des aktiven Anmeldevorgangs ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.89 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.54/0.59 | broken | 00:12-00:27 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe1_D09-K1 | alarm | alarm | review | 0.92/0.89 | same | 02:37-03:00 splitting: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und d... | llm_judge: Die Kunde möchte, dass die 20'000 Franken von ihrer Tante als eigenes Eigenmittel dargestellt werden, um die interne Prüfung zu umgehen. Diese Aussage zeigt, dass sie versucht, die Kontroll... |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.70/0.89 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C06-K3 | alarm | no_alert | review | 0.70/0.88 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | review | 0.70/0.89 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.54/0.59 | broken | 03:27-04:09 documentation: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, könnte sie den einmaligen Auftrag für mich e... | llm_judge: Die Kunde erwähnt, dass sie den Absatzbericht der Albisoptik gelesen hat, der noch nicht offiziell bekanntgegeben wurde. Der Advisor bestätigt, dass der Kaufwunsch mit den genannten Quellen... |
| Stufe2_C11-K3 | no_alert | no_alert | review | 0.69/0.87 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | review | 0.70/0.89 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | review | 0.70/0.89 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | review | 0.70/0.89 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.89 | same | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe3_C20-K3 | review | no_alert | review | 0.53/0.57 | fixed | 01:49-02:11 documentation: Können Sie die 4000 für heute und die 5000 für morgen trotzdem schon vorbeweiten? Ich kann Ihnen noch nicht sagen, warum das getrennt plant ist oder welche Belege zusammenge... | llm_judge: Die Kunde möchte zwei verschiedene Daten (4000 für heute und 5000 für morgen) vorbeweisen, ohne dass die zugehörigen Unterlagen bereitgestellt wurden. Der Advisor bestätigt dies und wartet ... |

