# Experiment `fusion`

Weighted-fusion knobs (N14 abstention, uncertainty source, review band, uncertainty cap) as re-fusions of one check run; fitted fusions via `callguard fusion-cv`

RQ: RQ9, RQ4 · base profile `gpu-12gb` · split **dev** · baseline `base` · commit 2cc04e7f41 (dirty) · 2026-10-10T02:14:18+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| base | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 |  |
| abstain | 0.65 [0.48, 0.82] | 0.73 [0.57, 0.91] | 26/22 | re-fusion of base |
| abstain_llmunc | 0.65 [0.48, 0.82] | 0.73 [0.57, 0.91] | 26/22 | re-fusion of base |
| llmunc | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| band010 | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| band020 | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| unc025 | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| unc045 | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| noesc | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| noesc_noband | 0.68 [0.54, 0.83] | 0.77 [0.63, 0.92] | 26/22 | re-fusion of base |
| abstain_noesc | 0.65 [0.48, 0.82] | 0.73 [0.57, 0.91] | 26/22 | re-fusion of base |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.55 | 67% | 50% | 0.62 [0.47, 0.78] |  |
| abstain | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.67 | 33% | 48% | 0.58 [0.46, 0.72] | re-fusion of base |
| abstain_llmunc | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.67 | 33% | 48% | 0.58 [0.46, 0.72] | re-fusion of base |
| llmunc | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.67 | 33% | 50% | 0.58 [0.46, 0.72] | re-fusion of base |
| band010 | 48 | 0.67 [0.46, 0.83] | 64% | 69% | 45% [18%, 72%] | 31% [9%, 54%] | 0.53 | 67% | 50% | 0.62 [0.47, 0.78] | re-fusion of base |
| band020 | 48 | 0.69 [0.52, 0.82] | 58% | 85% | 73% [44%, 95%] | 15% [0%, 33%] | 0.65 | 67% | 46% | 0.56 [0.43, 0.70] | re-fusion of base |
| unc025 | 48 | 0.69 [0.55, 0.82] | 54% | 96% | 95% [85%, 100%] | 4% [0%, 12%] | 0.33 | 100% | 23% | 0.50 [0.45, 0.56] | re-fusion of base |
| unc045 | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.67 | 33% | 50% | 0.58 [0.46, 0.72] | re-fusion of base |
| noesc | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.67 | 33% | 50% | 0.58 [0.46, 0.72] | re-fusion of base |
| noesc_noband | 48 | 0.66 [0.48, 0.80] | 57% | 77% | 68% [41%, 91%] | 23% [4%, 44%] | 0.65 | 0% | 50% | 0.54 [0.40, 0.69] | re-fusion of base |
| abstain_noesc | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [41%, 91%] | 15% [0%, 33%] | 0.67 | 33% | 48% | 0.58 [0.46, 0.72] | re-fusion of base |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 48 | 0.67 [0.45, 0.84] | 68% | 65% | 36% [10%, 62%] | 35% [12%, 57%] | 0.10 | 67% | 40% | 0.65 [0.48, 0.81] |  |
| abstain | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.10 | 0% | 40% | 0.58 [0.45, 0.73] | re-fusion of base |
| abstain_llmunc | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.10 | 0% | 40% | 0.58 [0.45, 0.73] | re-fusion of base |
| llmunc | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.10 | 0% | 40% | 0.58 [0.45, 0.73] | re-fusion of base |
| band010 | 48 | 0.67 [0.45, 0.84] | 68% | 65% | 36% [10%, 62%] | 35% [12%, 57%] | 0.40 | 67% | 48% | 0.65 [0.48, 0.81] | re-fusion of base |
| band020 | 48 | 0.69 [0.47, 0.86] | 69% | 69% | 36% [10%, 62%] | 31% [9%, 54%] | 0.00 | 67% | 38% | 0.66 [0.50, 0.83] | re-fusion of base |
| unc025 | 48 | 0.69 [0.55, 0.82] | 54% | 96% | 95% [85%, 100%] | 4% [0%, 12%] | 0.00 | 100% | 15% | 0.50 [0.45, 0.56] | re-fusion of base |
| unc045 | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.10 | 0% | 40% | 0.58 [0.45, 0.73] | re-fusion of base |
| noesc | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.10 | 0% | 40% | 0.58 [0.45, 0.73] | re-fusion of base |
| noesc_noband | 48 | 0.42 [0.18, 0.64] | 67% | 31% | 18% [0%, 35%] | 69% [50%, 88%] | 0.38 | 0% | 48% | 0.56 [0.44, 0.70] | re-fusion of base |
| abstain_noesc | 48 | 0.46 [0.21, 0.68] | 69% | 35% | 18% [0%, 35%] | 65% [42%, 87%] | 0.10 | 0% | 40% | 0.58 [0.45, 0.73] | re-fusion of base |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| base | 36% (!) | 1/4 | 36% | **no** | cv_far @ 2cc04e7f41 cfg c8c60e398c2fe3c8 (config changed since run), far_floor @ 2cc04e7f41 cfg c8c60e398c2fe3c8 (config changed since run) |
| abstain | 18% | 3/4 | 18% | yes | - |
| abstain_llmunc | 18% | 3/4 | 18% | yes | - |
| llmunc | 18% | 3/4 | 18% | yes | - |
| band010 | 36% (!) | 1/4 | 36% | **no** | - |
| band020 | 36% (!) | 1/4 | 36% | **no** | - |
| unc025 | 91% (!) | 0/4 | 95% | **no** | - |
| unc045 | 18% | 3/4 | 18% | yes | - |
| noesc | 18% | 3/4 | 18% | yes | cv_far @ 2cc04e7f41 cfg f12e45ad1fda1dd8 (config changed since run), far_floor @ 2cc04e7f41 cfg f12e45ad1fda1dd8 (config changed since run) |
| noesc_noband | 14% | 4/4 | 18% | yes | cv_far @ 2cc04e7f41 cfg 15cd12f3112a20f1 (config changed since run), far_floor @ 2cc04e7f41 cfg 15cd12f3112a20f1 (config changed since run) |
| abstain_noesc | 18% | 3/4 | 18% | yes | cv_far @ 2cc04e7f41 cfg 799b97ad354b3817 (config changed since run), far_floor @ 2cc04e7f41 cfg 799b97ad354b3817 (config changed since run) |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] |  |
| abstain | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.57 | 0% | 38% | 0.51 [0.45, 0.59] | re-fusion of base |
| abstain_llmunc | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.60 | 0% | 40% | 0.51 [0.45, 0.59] | re-fusion of base |
| llmunc | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.64 | 17% | 42% | 0.51 [0.45, 0.59] | re-fusion of base |
| band010 | 48 | 0.70 [0.54, 0.83] | 56% | 92% | 86% [62%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 42% | 0.53 [0.46, 0.62] | re-fusion of base |
| band020 | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.63 | 83% | 40% | 0.51 [0.45, 0.59] | re-fusion of base |
| unc025 | 48 | 0.70 [0.56, 0.83] | 54% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.33 | 100% | 21% | 0.50 [0.50, 0.50] | re-fusion of base |
| unc045 | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.64 | 17% | 42% | 0.51 [0.45, 0.59] | re-fusion of base |
| noesc | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.64 | 17% | 42% | 0.51 [0.45, 0.59] | re-fusion of base |
| noesc_noband | 48 | 0.71 [0.55, 0.84] | 61% | 85% | 64% [36%, 88%] | 15% [0%, 33%] | 0.64 | 0% | 52% | 0.60 [0.48, 0.75] | re-fusion of base |
| abstain_noesc | 48 | 0.69 [0.53, 0.81] | 55% | 92% | 91% [70%, 100%] | 8% [0%, 18%] | 0.60 | 0% | 40% | 0.51 [0.45, 0.59] | re-fusion of base |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| base | 0.55 | 0.45 | 0.70, 0.85, 0.65, 0.90 (FAR20: 0.95!, 0.95, 1.00!, 0.95!) | 0.2 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | a72e6a6f84 |
| abstain | 0.55 | 0.75 | 0.75, 0.75, 0.65, 0.65 (FAR20: 0.95!, 0.90, 1.00, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| abstain_llmunc | 0.55 | 0.75 | 0.75, 0.75, 0.65, 0.65 (FAR20: 0.95!, 0.90, 1.00, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| llmunc | 0.55 | 0.45 | 0.70, 0.70, 0.65, 0.45 (FAR20: 0.95!, 0.95, 1.00, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| band010 | 0.55 | 0.40 | 0.65, 0.80, 0.60, 0.85 (FAR20: 0.90!, 0.90, 0.95!, 0.90!) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| band020 | 0.55 | 0.50 | 0.80, 0.90, 0.65, 0.50 (FAR20: 1.00!, 1.00, 1.00!, 1.00!) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| unc025 | 0.55 | 0.65 | 0.65, 0.80, 0.80, 0.65 (FAR20: 0.65!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| unc045 | 0.55 | 0.45 | 0.70, 0.70, 0.65, 0.45 (FAR20: 0.95!, 0.95, 1.00, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | 2cc04e7f41 |
| noesc | 0.55 | 0.45 | 0.70, 0.70, 0.65, 0.45 (FAR20: 0.95!, 0.95, 1.00, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | a72e6a6f84 |
| noesc_noband | 0.55 | 0.30 | 0.55, 0.60, 0.50, 0.30 (FAR20: 0.90, 0.80, 0.85, 0.80) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | a72e6a6f84 |
| abstain_noesc | 0.55 | 0.75 | 0.75, 0.75, 0.65, 0.65 (FAR20: 0.95!, 0.90, 1.00, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 31.8 | 10.0 | 0 | 0 | a72e6a6f84 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| base | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| abstain | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |
| abstain_llmunc | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |
| llmunc | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |
| band010 | 0.86 / 25% / 10% | 0.43 / 57% / 50% | 0.80 / - / 33% | 0.69 / 36% / 31% | 0.64 / 55% / 31% |
| band020 | 0.75 / 62% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.67 / 82% / 15% |
| unc025 | 0.69 / 88% / 10% | 0.59 / 100% / 0% | 1.00 / - / 0% | 0.70 / 100% / 0% | 0.69 / 91% / 8% |
| unc045 | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |
| noesc | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |
| noesc_noband | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.50 / - / 67% | 0.67 / 64% / 23% | 0.65 / 73% / 23% |
| abstain_noesc | 0.78 / 50% / 10% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.71 / 64% / 15% | 0.69 / 73% / 15% |

## `abstain` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = abstain - base

| metric | base | abstain | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.65 | -0.034 | [-0.120, +0.035] | no detectable difference |
| alarm AUC | 0.77 | 0.73 | -0.038 | [-0.122, +0.026] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain - base

| metric | base | abstain | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.67 | +0.115 | [-0.100, +0.367] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 48% | -2pp | [-19pp, +11pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-abstain 4, p=1.0; 3-class only-base 7 vs only-abstain 6, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain - base

| metric | base | abstain | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: base better |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: base better |
| accuracy | 40% | 40% | +0pp | [-17pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-base 8 vs only-abstain 4, p=0.3877; 3-class only-base 4 vs only-abstain 4, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain - base

| metric | base | abstain | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.57 | -0.060 | [-0.253, +0.139] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 38% | -2pp | [-21pp, +13pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: base better |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-abstain 0, p=1.0; 3-class only-base 5 vs only-abstain 4, p=1.0.

Flips (cv, 16 calls):

| call | expected | base | abstain | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
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

## `abstain_llmunc` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = abstain_llmunc - base

| metric | base | abstain_llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.65 | -0.034 | [-0.120, +0.035] | no detectable difference |
| alarm AUC | 0.77 | 0.73 | -0.038 | [-0.122, +0.026] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain_llmunc - base

| metric | base | abstain_llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.67 | +0.115 | [-0.100, +0.367] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 48% | -2pp | [-19pp, +11pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-abstain_llmunc 4, p=1.0; 3-class only-base 7 vs only-abstain_llmunc 6, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain_llmunc - base

| metric | base | abstain_llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: base better |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: base better |
| accuracy | 40% | 40% | +0pp | [-17pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-base 8 vs only-abstain_llmunc 4, p=0.3877; 3-class only-base 4 vs only-abstain_llmunc 4, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain_llmunc - base

| metric | base | abstain_llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.60 | -0.035 | [-0.237, +0.169] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 40% | +0pp | [-19pp, +15pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: base better |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-abstain_llmunc 0, p=1.0; 3-class only-base 5 vs only-abstain_llmunc 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | base | abstain_llmunc | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
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

## `llmunc` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = llmunc - base

| metric | base | llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = llmunc - base

| metric | base | llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.67 | +0.115 | [-0.107, +0.368] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 50% | +0pp | [-17pp, +14pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-llmunc 4, p=1.0; 3-class only-base 7 vs only-llmunc 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = llmunc - base

| metric | base | llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: base better |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: base better |
| accuracy | 40% | 40% | +0pp | [-17pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-base 8 vs only-llmunc 4, p=0.3877; 3-class only-base 4 vs only-llmunc 4, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = llmunc - base

| metric | base | llmunc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.64 | +0.010 | [-0.197, +0.238] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 42% | +2pp | [-17pp, +17pp] | no detectable difference |
| review_recall | 83% | 17% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-llmunc 0, p=1.0; 3-class only-base 4 vs only-llmunc 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | base | llmunc | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | review | alarm | 0.70/0.70 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Die Kundin sagt den T... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.85 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.74/0.74 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.73 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.75/0.75 | same | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.69 | same | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | alarm | 0.70/0.70 | same | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `band010` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = band010 - base

| metric | base | band010 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band010 - base

| metric | base | band010 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.55 | 0.53 | -0.018 | [-0.074, +0.000] | no detectable difference |
| false_alarm_rate | 45% | 45% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.62 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-band010 0, p=1.0; 3-class only-base 0 vs only-band010 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band010 - base

| metric | base | band010 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.10 | 0.40 | +0.305 | [+0.105, +0.476] | **real**: band010 better |
| false_alarm_rate | 36% | 36% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 35% | 35% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 48% | +8pp | [+2pp, +18pp] | **real**: band010 better |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.65 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-band010 0, p=1.0; 3-class only-base 0 vs only-band010 4, p=0.125.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band010 - base

| metric | base | band010 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.010 | [+0.000, +0.035] | no detectable difference |
| alarm_f1 | 0.63 | 0.63 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 91% | 86% | -5pp | [-15pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 42% | +2pp | [+0pp, +7pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.53 | +0.023 | [+0.000, +0.077] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-band010 1, p=1.0; 3-class only-base 0 vs only-band010 1, p=1.0.

Flips (cv, 1 calls):

| call | expected | base | band010 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | alarm | 0.69/0.69 | same | 00:11-00:23 documentation: Sag Ja danken. Ich bin gerade daheim, ich habe am Samstag im Internet etwas gestellt, jetzt sehe ich den Betrag zweimal. Ich weiss nicht, ob ich selber etwas doppelt angekri... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |

## `band020` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = band020 - base

| metric | base | band020 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band020 - base

| metric | base | band020 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.021 | [-0.074, +0.136] | no detectable difference |
| alarm_f1 | 0.55 | 0.65 | +0.097 | [-0.074, +0.311] | no detectable difference |
| false_alarm_rate | 45% | 73% | +27pp | [+6pp, +55pp] | **real**: base better |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 46% | -4pp | [-16pp, +4pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.56 | -0.059 | [-0.188, +0.037] | no detectable difference |

McNemar exact (calls): flag correct only-base 6 vs only-band020 4, p=0.7539; 3-class only-base 6 vs only-band020 4, p=0.7539.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band020 - base

| metric | base | band020 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.026 | [+0.000, +0.082] | no detectable difference |
| alarm_f1 | 0.10 | 0.00 | -0.095 | [-0.286, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 36% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 35% | 31% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 40% | 38% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.66 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-band020 1, p=1.0; 3-class only-base 1 vs only-band020 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band020 - base

| metric | base | band020 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.63 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 40% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-band020 0, p=1.0; 3-class only-base 0 vs only-band020 0, p=1.0.

Flips (cv, 11 calls):

| call | expected | base | band020 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K2 | no_alert | no_alert | review | 0.45/0.45 | broken | 03:01-03:14 documentation: A, denn das Beispiel im ProK geht es nicht um einen Zusatzsinn von Wo habe. Ich will nicht von der Meldung handeln und habe auch keine Information, die noch nicht publiziert... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.70 | same | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |

## `unc025` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = unc025 - base

| metric | base | unc025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = unc025 - base

| metric | base | unc025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.028 | [-0.103, +0.176] | no detectable difference |
| alarm_f1 | 0.55 | 0.33 | -0.218 | [-0.454, +0.000] | no detectable difference |
| false_alarm_rate | 45% | 95% | +50pp | [+23pp, +80pp] | **real**: base better |
| miss_rate | 31% | 4% | -27pp | [-50pp, -6pp] | **real**: unc025 better |
| accuracy | 50% | 23% | -27pp | [-45pp, -9pp] | **real**: base better |
| review_recall | 67% | 100% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.50 | -0.115 | [-0.280, +0.038] | no detectable difference |

McNemar exact (calls): flag correct only-base 11 vs only-unc025 7, p=0.4807; 3-class only-base 15 vs only-unc025 2, p=0.0023.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = unc025 - base

| metric | base | unc025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.69 | +0.028 | [-0.126, +0.189] | no detectable difference |
| alarm_f1 | 0.10 | 0.00 | -0.095 | [-0.286, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 95% | +59pp | [+30pp, +88pp] | **real**: base better |
| miss_rate | 35% | 4% | -31pp | [-54pp, -9pp] | **real**: unc025 better |
| accuracy | 40% | 15% | -25pp | [-42pp, -7pp] | **real**: base better |
| review_recall | 67% | 100% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.50 | -0.142 | [-0.317, +0.024] | no detectable difference |

McNemar exact (calls): flag correct only-base 13 vs only-unc025 8, p=0.3833; 3-class only-base 14 vs only-unc025 2, p=0.0042.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = unc025 - base

| metric | base | unc025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.017 | [-0.006, +0.058] | no detectable difference |
| alarm_f1 | 0.63 | 0.33 | -0.298 | [-0.533, -0.061] | **real**: base better |
| false_alarm_rate | 91% | 100% | +9pp | [+0pp, +30pp] | no detectable difference |
| miss_rate | 8% | 0% | -8pp | [-18pp, +0pp] | no detectable difference |
| accuracy | 40% | 21% | -19pp | [-32pp, -4pp] | **real**: base better |
| review_recall | 83% | 100% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.50 | -0.007 | [-0.089, +0.054] | no detectable difference |

McNemar exact (calls): flag correct only-base 2 vs only-unc025 2, p=1.0; 3-class only-base 10 vs only-unc025 1, p=0.0117.

Flips (cv, 23 calls):

| call | expected | base | unc025 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.43/0.43 | broken | 01:28-01:39 access: also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, 2, 4, 2. - geval: Die Kundin gibt die letzten vie... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktives Geheimnis ist oder ob es ... |
| Stufe1_D02-K2 | alarm | alarm | review | 0.68/0.68 | same | 01:28-01:31 documentation: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es r... | llm_judge: Der Kunde möchte die Aktie kaufen und das Foto der Iguessicht nicht protokollieren, obwohl es relevant ist. |
| Stufe1_D04-K2 | alarm | alarm | review | 0.82/0.82 | same | 02:27-03:27 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine potenzielle Übernahme gegeben hat, die noch nicht veröffentlicht wurde. Sie möchte diese Informationen nutzen,... |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.54/0.54 | broken | 01:35-02:02 documentation: Gerätewechsel, aber auf dem Blatt, das ich herausgerückt habe, steht der Lehrstofzugang. Ich habe also vermutlich das falsche Blatt ausgenommen und in der Mail schrieb jeman... | llm_judge: Der Kunde möchte, dass seine alte Anleitung nicht protokolliert wird, um eine mögliche bestehende Verpflichtung vor der Kreditstelle zu verbergen. |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.52/0.52 | broken | 03:21-03:37 access: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum Teil. - ... | llm_judge: Der Kunde spricht den Bestätigungscode 4826001 aus, der Teil des aktiven Anmeldevorgangs ist. |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe1_D09-K1 | alarm | alarm | review | 0.92/0.92 | same | 02:37-03:00 splitting: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und d... | llm_judge: Die Kunde möchte, dass die 20'000 Franken von ihrer Tante als eigenes Eigenmittel dargestellt werden, um die interne Prüfung zu umgehen. Diese Aussage zeigt, dass sie versucht, die Kontroll... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.88/0.88 | same | 02:39-03:02 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen u... | llm_judge: Die Kundenin versucht, eine bestehende Rückzahlbare Verpflichtung (20'000 Franken ihrer Tante) vor der Kreditstelle zu verbergen, indem sie den Wunsch äußert, diese nicht in die Notiz zu ne... |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C06-K3 | alarm | no_alert | review | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | review | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.54/0.54 | broken | 00:35-00:53 trade: Ich habe gestern den neuen Absatzbericht auf der Merzseite der Albisoptik gelesen, der am Morgen an die Medien ging und für alle verfügbar, es wurde dort mehr verkauft als erwartet,... | llm_judge: Die Kunde erwähnt, dass sie den Absatzbericht der Albisoptik gelesen hat, der noch nicht offiziell bekanntgegeben wurde. Der Advisor bestätigt, dass der Kaufwunsch mit den genannten Quellen... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.31/0.31 | fixed | 00:58-01:01 documentation: Der Pfeili, ich habe erwartet, dass ich auf dem Telefon etwas schlugge. - geval: Der Kunde erwähnt, dass er einen Pfeil erwartet hat, der ihn zum Browser führt, während der ... | geval: Der Kunde erwähnt, dass er einen Pfeil erwartet hat, der ihn zum Browser führt, während der Advisor darauf hinweist, dass es zwei Ansichten gibt, und dass sie keine geheimen Worte teilen. Dies ... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.34/0.34 | broken | 00:30-00:46 documentation: Ich habe den Zugang noch gar nicht gestartet, ich schaue das abgelaufenen Muster in der Anleitung an, das echte Anmeldenfenster ist zu, es gibt auch keinen Countdown, die Za... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was implizit darauf hindeutet, dass er möglicherweise Informationen vor der Kreditstelle verbirgt. Ob diese Informati... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.29/0.29 | broken | 00:31-00:57 documentation: Ich habe den Zugang noch gar nicht gestartet, ich schaue ein abgelaufener Muster in der Anleitung an, das echte Anmeldefenster ist zu, es gibt auch keinen Counton, die Zahl ... | geval: Der Kunde erwähnt eine abgelaufene Muster-Zahlung in der Anleitung, die nicht protokolliert werden soll, was einen Versuch zur Verschweigung relevanter Informationen darstellt. |
| Stufe2_C11-K3 | no_alert | no_alert | review | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | review | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | review | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | review | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C14-K3 | no_alert | alarm | review | 0.70/0.70 | same | 04:27-04:38 splitting: Danke, ich habe noch den Lohnnachweis vom August, aber dann vom September kommt die erste Ende Woche. Soll ich den August schon aufladen oder gibt es einen grossen zweiten Stape... | llm_judge: Die Kunde verlangt, dass eine einzige Rechnung in mehrere Teilbeträge aufgeteilt wird, um eine interne Kontrolle zu vermeiden. Dies wird explizit durch den Satz 'Ich schreibe den August in ... |
| Stufe3_C20-K3 | review | no_alert | review | 0.53/0.53 | fixed | 01:49-02:11 documentation: Können Sie die 4000 für heute und die 5000 für morgen trotzdem schon vorbeweiten? Ich kann Ihnen noch nicht sagen, warum das getrennt plant ist oder welche Belege zusammenge... | llm_judge: Die Kunde möchte zwei verschiedene Daten (4000 für heute und 5000 für morgen) vorbeweisen, ohne dass die zugehörigen Unterlagen bereitgestellt wurden. Der Advisor bestätigt dies und wartet ... |
| Stufe3_C20-K4 | review | no_alert | review | 0.31/0.31 | fixed | 00:40-00:51 disclosure: Nein, auf der Liste steht beim einen Teil eins und beim anderen Material. Das kann zur gleichen Baustelle kommen, muss aber nicht gleiche wie die Wunsch sind. - geval: Der Kund... | geval: Der Kunde fragt nach den Daten, obwohl seine Berechtigung nicht bestätigt wurde. Der Berater antwortet, ohne die Berechtigung zu überprüfen. |

## `unc045` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = unc045 - base

| metric | base | unc045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = unc045 - base

| metric | base | unc045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.67 | +0.115 | [-0.107, +0.368] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 50% | +0pp | [-17pp, +14pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-unc045 4, p=1.0; 3-class only-base 7 vs only-unc045 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = unc045 - base

| metric | base | unc045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: base better |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: base better |
| accuracy | 40% | 40% | +0pp | [-17pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-base 8 vs only-unc045 4, p=0.3877; 3-class only-base 4 vs only-unc045 4, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = unc045 - base

| metric | base | unc045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.64 | +0.010 | [-0.197, +0.238] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 42% | +2pp | [-17pp, +17pp] | no detectable difference |
| review_recall | 83% | 17% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-unc045 0, p=1.0; 3-class only-base 4 vs only-unc045 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | base | unc045 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | review | alarm | 0.70/0.70 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Die Kundin sagt den T... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.85 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.74/0.74 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.73 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.75/0.75 | same | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.69 | same | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | alarm | 0.70/0.70 | same | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `noesc` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = noesc - base

| metric | base | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc - base

| metric | base | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.67 | +0.115 | [-0.107, +0.368] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 50% | +0pp | [-17pp, +14pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-noesc 4, p=1.0; 3-class only-base 7 vs only-noesc 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc - base

| metric | base | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: base better |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: base better |
| accuracy | 40% | 40% | +0pp | [-17pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-base 8 vs only-noesc 4, p=0.3877; 3-class only-base 4 vs only-noesc 4, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc - base

| metric | base | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.64 | +0.010 | [-0.197, +0.238] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 42% | +2pp | [-17pp, +17pp] | no detectable difference |
| review_recall | 83% | 17% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-noesc 0, p=1.0; 3-class only-base 4 vs only-noesc 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | base | noesc | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | review | alarm | 0.70/0.70 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Die Kundin sagt den T... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.85 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.74/0.74 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.73 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.75/0.75 | same | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.69 | same | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | alarm | 0.70/0.70 | same | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `noesc_noband` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = noesc_noband - base

| metric | base | noesc_noband | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.77 | 0.77 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc_noband - base

| metric | base | noesc_noband | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.66 | -0.011 | [-0.160, +0.128] | no detectable difference |
| alarm_f1 | 0.55 | 0.65 | +0.102 | [-0.179, +0.404] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 23% | -8pp | [-33pp, +18pp] | no detectable difference |
| accuracy | 50% | 50% | +0pp | [-22pp, +16pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.54 | -0.075 | [-0.226, +0.048] | no detectable difference |

McNemar exact (calls): flag correct only-base 7 vs only-noesc_noband 4, p=0.5488; 3-class only-base 9 vs only-noesc_noband 9, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc_noband - base

| metric | base | noesc_noband | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.42 | -0.246 | [-0.485, -0.044] | **real**: base better |
| alarm_f1 | 0.10 | 0.38 | +0.289 | [+0.093, +0.476] | **real**: noesc_noband better |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 69% | +35pp | [+10pp, +62pp] | **real**: base better |
| accuracy | 40% | 48% | +8pp | [-9pp, +23pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.56 | -0.082 | [-0.208, +0.035] | no detectable difference |

McNemar exact (calls): flag correct only-base 9 vs only-noesc_noband 4, p=0.2668; 3-class only-base 4 vs only-noesc_noband 8, p=0.3877.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc_noband - base

| metric | base | noesc_noband | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.71 | +0.024 | [-0.053, +0.108] | no detectable difference |
| alarm_f1 | 0.63 | 0.64 | +0.010 | [-0.197, +0.238] | no detectable difference |
| false_alarm_rate | 91% | 64% | -27pp | [-50pp, -8pp] | **real**: noesc_noband better |
| miss_rate | 8% | 15% | +8pp | [+0pp, +18pp] | no detectable difference |
| accuracy | 40% | 52% | +12pp | [-9pp, +32pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: base better |
| flag_balanced_accuracy | 0.51 | 0.60 | +0.098 | [-0.006, +0.225] | no detectable difference |

McNemar exact (calls): flag correct only-base 2 vs only-noesc_noband 6, p=0.2891; 3-class only-base 5 vs only-noesc_noband 11, p=0.2101.

Flips (cv, 25 calls):

| call | expected | base | noesc_noband | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | review | alarm | 0.69/0.69 | same | 00:11-00:23 documentation: Sag Ja danken. Ich bin gerade daheim, ich habe am Samstag im Internet etwas gestellt, jetzt sehe ich den Betrag zweimal. Ich weiss nicht, ob ich selber etwas doppelt angekri... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um eine mögliche doppelte Belastung zu vermeiden. |
| Stufe1_D05-K1 | alarm | review | alarm | 0.70/0.70 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Die Kundin sagt den T... | llm_judge: Die Kundin sagt den TAN-Code '7, 3, 1, 9, 4, 2' vor, der noch im laufenden Anmeldevorgang gültig ist. |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.54/0.54 | broken | 00:12-00:41 documentation: Kameral, ja, ich bin seit der Generalversammlung Kassierungen, ich habe eine Liste von Zahlungen, aber mein Vorgänger hat mir den Ordnung mit den Belegern, ich will vor dem ... | llm_judge: Der Kunde möchte eine falsche Periode für die Kasse zusammenzählen und versucht, dies dem Vorstand vorzuenthalten. |
| Stufe2_C01-K4 | no_alert | review | alarm | 0.69/0.69 | same | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als ... | llm_judge: Die Kundin gibt den Wert 4242424242424242424242424242424242424242424242424242 am Telefon vor, was als Preisgabe eines aktiven Geheimnisses zählt. |
| Stufe2_C02-K3 | no_alert | review | alarm | 0.69/0.69 | same | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. | llm_judge: Der Kunde gibt die TAN 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | review | alarm | 0.70/0.70 | same | 00:35-00:50 access: Im Formulat war das die Rechnungsreferenz. Ich habe die Nummer aus dem Rechnungsfeld des Händlers übernommen, es ist der Bezug zu dieser Bestellung, nicht zu meiner Karte. Die Fahr... | llm_judge: Die Kundin sagt die Zahlen 'vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier' vor, die sie aus dem Rechnungsfeld des Händlers... |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Frau Keller versucht, dass ihre Absicht, keine 6000 Franken für Aktien von den CLN-Systemen zu kaufen, vor der Kreditstelle verborgen bleibt. Sie sagt: 'Genau wegen diesem Bericht will ich ... |
| Stufe2_C05-K4 | no_alert | review | alarm | 0.85/0.85 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | llm_judge: Frau Keller gibt an, dass sie eine selbst erhaltene, noch nicht öffentliche Information aus einem Bericht verwendet, um einen Kaufwunsch für Aktien zu formulieren. Diese Information stammt ... |
| Stufe2_C06-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte, dass die 6000 Franken für die Aktien von der CRM-Systeme nicht in die Notiz für die Kreditprüfung protokolliert werden, um den Sparplan unberührt zu lassen. |
| Stufe2_C06-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erklärt, dass sie Informationen aus einer unternehmensinternen Quelle hat und möchte sich informieren, ohne jetzt im Kauf zu verlangen. Sie zeigt Dokumente und Zahlen, die ande... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.68/0.68 | same | 00:00-00:10 documentation: Guten Tag Frau Bühler, da ist Nadia Fuller, Sie wollen die Erfassung ihres Sparauftrags ändern, geht es um den Monat oder um den Betrag, - llm_judge: Die Kundin möchte, dass... | llm_judge: Die Kundin möchte, dass ihre bestehenden finanziellen Verpflichtungen (wie der monatliche Sparauftrag) nicht in die Notiz für die Kreditprüfung eingeordnet werden. Das ist ein klarer Fall v... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.70/0.70 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kunde erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Diese Informationen wer... |
| Stufe2_C08-K4 | no_alert | review | alarm | 0.69/0.69 | same | 03:30-03:42 documentation: Ja, ich habe mich jetzt entschieden. Wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albisoptik kaufen. Können Sie den einmaligen Auftrag für mich en... | llm_judge: Die Kunde möchte absichtlich, dass eine bestehende rückzahlbare Verpflichtung für die Kreditprüfung nicht protokolliert wird. Dies wird in S019 durch den Wunsch der Kunde deutlich: 'Wegen d... |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.69/0.69 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - llm_judge:... | llm_judge: Die Kunde möchte, dass ihre Mutter für die Heimrechnung keine bereits existierende rückzahlbare Verpflichtung in der Notiz für die Kreditprüfung nicht berücksichtigt wird. |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Die Beratung gibt den aktuellen Kontostand von 64... | llm_judge: Die Beratung gibt den aktuellen Kontostand von 6400 Franken an die Klientin aus, ohne dass die Berechtigung zur Preisgabe bestätigt wurde. |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:29-03:59 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. Dank Fett, ich schreibe es mit dem Datum auf. Ich kann nicht vor,... | llm_judge: Die Kunde erhielt eine Bestätigung des Kontostands von 6400 Franken, ohne dass die Berechtigung für diese Auskunft bestätigt wurde. Der Advisor bestätigte die Zahlung ohne Vorbehalt. |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.70/0.70 | fixed | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Fra... | llm_judge: Der Advisor gibt den aktuellen Kontostand von 6400 Franken an die Customer, ohne dass diese Berechtigung dazu hat. Dies entspricht der Definition der Preisgabe an Dritte. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.74/0.74 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunde möchte, dass der Satz mit der Rückzahlbarkeit von 30.000 Franken ihres Bruders nicht in die Notiz für die Finanzierungsstelle eingeht. Der Advisor akzeptiert diesen Wunsch, indem ... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.73/0.73 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Die Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl es eine relevante Tatsache ist. Dies entspricht dem Wunsch, eine relevante A... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.75/0.75 | same | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Frau Inhoff möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt, obwohl sie bereits weiß, dass dieser Satz relevant ist. |
| Stufe3_C17-K3 | review | review | no_alert | 0.56/0.56 | broken | 01:39-02:02 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. Weitere Kei weite Rebeta von aufzulesen. Für die näc... | llm_judge: Die Kundin gibt den vorgelesenen Text 'zwei, neun, sechs, vier, acht, eins' tatsächlich vor, obwohl sie nicht sicher ist, ob der Wert noch gültig ist. |
| Stufe3_C17-K4 | review | review | no_alert | 0.58/0.58 | broken | 01:40-01:49 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - llm_judge: Der Kunde gibt einen Teil des Codes vor... | llm_judge: Der Kunde gibt einen Teil des Codes vor, nämlich die ersten zehn Ziffern, was als Preisgabe eines Zugangsgeheimnisses zu interpretieren ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.69 | same | 00:23-01:06 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über das Konto informiert wird, während sie noch keine offizielle Berechtigung vorlegt. Sie versucht, die Wohnungsrechnung zu lösen, ohne dass ih... |
| Stufe3_C18-K4 | review | review | alarm | 0.70/0.70 | same | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies vor der Kreditstelle protokolliert wird. Dies entspricht dem Wunsch, eine relevante ... |

## `abstain_noesc` vs `base`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = abstain_noesc - base

| metric | base | abstain_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.65 | -0.034 | [-0.120, +0.035] | no detectable difference |
| alarm AUC | 0.77 | 0.73 | -0.038 | [-0.122, +0.026] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain_noesc - base

| metric | base | abstain_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.70 | +0.032 | [-0.056, +0.145] | no detectable difference |
| alarm_f1 | 0.55 | 0.67 | +0.115 | [-0.100, +0.367] | no detectable difference |
| false_alarm_rate | 45% | 68% | +23pp | [+0pp, +50pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +0pp] | no detectable difference |
| accuracy | 50% | 48% | -2pp | [-19pp, +11pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.62 | 0.58 | -0.037 | [-0.158, +0.057] | no detectable difference |

McNemar exact (calls): flag correct only-base 5 vs only-abstain_noesc 4, p=1.0; 3-class only-base 7 vs only-abstain_noesc 6, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain_noesc - base

| metric | base | abstain_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.67 | 0.46 | -0.205 | [-0.456, -0.010] | **real**: base better |
| alarm_f1 | 0.10 | 0.10 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 36% | 18% | -18pp | [-34pp, +0pp] | no detectable difference |
| miss_rate | 35% | 65% | +31pp | [+8pp, +58pp] | **real**: base better |
| accuracy | 40% | 40% | +0pp | [-17pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.65 | 0.58 | -0.063 | [-0.192, +0.052] | no detectable difference |

McNemar exact (calls): flag correct only-base 8 vs only-abstain_noesc 4, p=0.3877; 3-class only-base 4 vs only-abstain_noesc 4, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = abstain_noesc - base

| metric | base | abstain_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.63 | 0.60 | -0.035 | [-0.237, +0.169] | no detectable difference |
| false_alarm_rate | 91% | 91% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 40% | 40% | +0pp | [-19pp, +15pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: base better |
| flag_balanced_accuracy | 0.51 | 0.51 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-base 0 vs only-abstain_noesc 0, p=1.0; 3-class only-base 5 vs only-abstain_noesc 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | base | abstain_noesc | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.70/0.70 | broken | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass die April-Ausgabe im März geschehen sei nicht protokolliert wird, was als Verschweigen einer relevanten Tatsache interpretiert werden kann. |
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

