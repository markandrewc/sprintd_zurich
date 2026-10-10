# Experiment `champion`

Recommended profile (large-v3 MIT + Qwen2.5-7B facts + light keywords/patterns) and its neighbours

RQ: RQ2, RQ4, RQ5, RQ9 · base profile `recommended` · split **holdout** · baseline `champion` · commit 795bb55852 (dirty) · 2026-10-10T04:08:36+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

> **HOLDOUT run**: logged in runs/holdout_log.jsonl. Do not tune on these numbers.

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 12 calls** (prevalence of alarm|review 50%): flag-all = flag F1 0.67, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 33%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 50%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.67 with FAR near 100% has learned nothing.

## Warnings

- `facts_only`: source `champion` changed after this re-fusion (results hash de6abbdaa6a9cb61 -> 3b8103f0541fc115): rerun this variant
- `t045`: source `champion` changed after this re-fusion (results hash de6abbdaa6a9cb61 -> 3b8103f0541fc115): rerun this variant
- `t065`: source `champion` changed after this re-fusion (results hash de6abbdaa6a9cb61 -> 3b8103f0541fc115): rerun this variant
- `noesc`: source `champion` changed after this re-fusion (results hash de6abbdaa6a9cb61 -> 3b8103f0541fc115): rerun this variant
- `band025`: source `champion` changed after this re-fusion (results hash de6abbdaa6a9cb61 -> 3b8103f0541fc115): rerun this variant

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| champion | 0.83 [0.50, 1.00] | 1.00 [1.00, 1.00] | 6/6 |  |
| facts_only | 0.89 [0.77, 0.99] | 0.92 [0.78, 1.00] | 26/22 | re-fusion of champion, **WARN** (see Warnings) |
| t045 | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion, **WARN** (see Warnings) |
| t065 | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion, **WARN** (see Warnings) |
| noesc | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion, **WARN** (see Warnings) |
| band025 | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion, **WARN** (see Warnings) |
| table_v2 | 0.87 [0.71, 0.98] | 0.95 [0.86, 1.00] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| t045 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| t065 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| noesc | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| band025 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| table_v2 | 48 | 0.83 [0.67, 0.96] | 75% | 92% | 36% [6%, 67%] | 8% [0%, 25%] | 0.73 | 33% | 65% | 0.78 [0.61, 0.94] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.67 | 67% | 69% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| t045 | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of champion, **WARN** (see Warnings) |
| t065 | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of champion, **WARN** (see Warnings) |
| noesc | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of champion, **WARN** (see Warnings) |
| band025 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.18 | 67% | 52% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| table_v2 | 48 | 0.81 [0.64, 0.94] | 74% | 88% | 36% [6%, 67%] | 12% [0%, 30%] | 0.67 | 67% | 58% | 0.76 [0.59, 0.93] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| champion | 0% | - | - | - | - |
| facts_only | 14% | 4/4 | 14% | yes | - |
| t045 | 14% | 4/4 | 14% | yes | - |
| t065 | 14% | 4/4 | 14% | yes | - |
| noesc | 14% | 4/4 | 14% | yes | - |
| band025 | 14% | 4/4 | 14% | yes | - |
| table_v2 | 36% (!) | 0/4 | 36% | **no** | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 12 | 0.67 [0.00, 1.00] | 100% | 50% | 0% [0%, 0%] | 50% [0%, 100%] | 0.67 | 0% | 67% | 0.75 [0.50, 1.00] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| t045 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.80 | 0% | 77% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| t065 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| noesc | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| band025 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion, **WARN** (see Warnings) |
| table_v2 | 48 | 0.83 [0.67, 0.96] | 75% | 92% | 36% [6%, 67%] | 8% [0%, 25%] | 0.86 | 67% | 69% | 0.78 [0.61, 0.94] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| champion | 0.55 | 0.25 | - | 28.0 | asr 12.6, diarize 11.0, checks 4.4 | 4.4 | 21.1 | 0 | 0 | 795bb55852 |
| facts_only | 0.55 | 0.70 | 0.70, 0.70, 0.70, 0.70 (FAR20: 0.95, 0.95, 0.95, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.0 | 4.0 | 1.6 | 0 | 0 | 795bb55852 |
| t045 | 0.45 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| t065 | 0.65 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| noesc | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| band025 | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 1.00, 1.00, 1.00, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 4.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| table_v2 | 0.55 | 0.65 | 0.65, 0.35, 0.65, 0.70 (FAR20: 0.90!, 0.90!, 0.90!, 0.95!) | 4.1 | asr 0.0, diarize 0.0, checks 4.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| champion | 1.00 / - / 0% | 0.67 / 0% / 50% | 0.00 / - / 100% | 0.50 / 0% / 67% | 0.80 / 0% / 33% |
| facts_only | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| t045 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| t065 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| noesc | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| band025 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| table_v2 | 1.00 / 0% / 0% | 0.71 / 57% / 0% | 0.80 / - / 33% | 0.80 / 45% / 8% | 0.86 / 27% / 8% |

## `facts_only` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 0 calls; difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | - | - | - | [-, -] | no detectable difference |
| alarm AUC | - | - | - | [-, -] | no detectable difference |

**Fixed threshold** - 0 calls / 0 dialogues (0 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | - | - | - | [-, -] | no detectable difference |
| alarm_f1 | - | - | - | [-, -] | no detectable difference |
| false_alarm_rate | - | - | - | [-, -] | no detectable difference |
| miss_rate | - | - | - | [-, -] | no detectable difference |
| accuracy | - | - | - | [-, -] | no detectable difference |
| review_recall | - | - | - | [-, -] | no detectable difference |
| flag_balanced_accuracy | - | - | - | [-, -] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 0, p=1.0; 3-class only-champion 0 vs only-facts_only 0, p=1.0.

No call changes its label (fixed).

## `t045` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 0 calls; difference = t045 - champion

| metric | champion | t045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | - | - | - | [-, -] | no detectable difference |
| alarm AUC | - | - | - | [-, -] | no detectable difference |

**Fixed threshold** - 0 calls / 0 dialogues (0 resampling units: twins together); difference = t045 - champion

| metric | champion | t045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | - | - | - | [-, -] | no detectable difference |
| alarm_f1 | - | - | - | [-, -] | no detectable difference |
| false_alarm_rate | - | - | - | [-, -] | no detectable difference |
| miss_rate | - | - | - | [-, -] | no detectable difference |
| accuracy | - | - | - | [-, -] | no detectable difference |
| review_recall | - | - | - | [-, -] | no detectable difference |
| flag_balanced_accuracy | - | - | - | [-, -] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t045 0, p=1.0; 3-class only-champion 0 vs only-t045 0, p=1.0.

No call changes its label (fixed).

## `t065` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 0 calls; difference = t065 - champion

| metric | champion | t065 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | - | - | - | [-, -] | no detectable difference |
| alarm AUC | - | - | - | [-, -] | no detectable difference |

**Fixed threshold** - 0 calls / 0 dialogues (0 resampling units: twins together); difference = t065 - champion

| metric | champion | t065 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | - | - | - | [-, -] | no detectable difference |
| alarm_f1 | - | - | - | [-, -] | no detectable difference |
| false_alarm_rate | - | - | - | [-, -] | no detectable difference |
| miss_rate | - | - | - | [-, -] | no detectable difference |
| accuracy | - | - | - | [-, -] | no detectable difference |
| review_recall | - | - | - | [-, -] | no detectable difference |
| flag_balanced_accuracy | - | - | - | [-, -] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t065 0, p=1.0; 3-class only-champion 0 vs only-t065 0, p=1.0.

No call changes its label (fixed).

## `noesc` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 0 calls; difference = noesc - champion

| metric | champion | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | - | - | - | [-, -] | no detectable difference |
| alarm AUC | - | - | - | [-, -] | no detectable difference |

**Fixed threshold** - 0 calls / 0 dialogues (0 resampling units: twins together); difference = noesc - champion

| metric | champion | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | - | - | - | [-, -] | no detectable difference |
| alarm_f1 | - | - | - | [-, -] | no detectable difference |
| false_alarm_rate | - | - | - | [-, -] | no detectable difference |
| miss_rate | - | - | - | [-, -] | no detectable difference |
| accuracy | - | - | - | [-, -] | no detectable difference |
| review_recall | - | - | - | [-, -] | no detectable difference |
| flag_balanced_accuracy | - | - | - | [-, -] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-noesc 0, p=1.0; 3-class only-champion 0 vs only-noesc 0, p=1.0.

No call changes its label (fixed).

## `band025` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 0 calls; difference = band025 - champion

| metric | champion | band025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | - | - | - | [-, -] | no detectable difference |
| alarm AUC | - | - | - | [-, -] | no detectable difference |

**Fixed threshold** - 0 calls / 0 dialogues (0 resampling units: twins together); difference = band025 - champion

| metric | champion | band025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | - | - | - | [-, -] | no detectable difference |
| alarm_f1 | - | - | - | [-, -] | no detectable difference |
| false_alarm_rate | - | - | - | [-, -] | no detectable difference |
| miss_rate | - | - | - | [-, -] | no detectable difference |
| accuracy | - | - | - | [-, -] | no detectable difference |
| review_recall | - | - | - | [-, -] | no detectable difference |
| flag_balanced_accuracy | - | - | - | [-, -] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-band025 0, p=1.0; 3-class only-champion 0 vs only-band025 0, p=1.0.

No call changes its label (fixed).

## `table_v2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 0 calls; difference = table_v2 - champion

| metric | champion | table_v2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | - | - | - | [-, -] | no detectable difference |
| alarm AUC | - | - | - | [-, -] | no detectable difference |

**Fixed threshold** - 0 calls / 0 dialogues (0 resampling units: twins together); difference = table_v2 - champion

| metric | champion | table_v2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | - | - | - | [-, -] | no detectable difference |
| alarm_f1 | - | - | - | [-, -] | no detectable difference |
| false_alarm_rate | - | - | - | [-, -] | no detectable difference |
| miss_rate | - | - | - | [-, -] | no detectable difference |
| accuracy | - | - | - | [-, -] | no detectable difference |
| review_recall | - | - | - | [-, -] | no detectable difference |
| flag_balanced_accuracy | - | - | - | [-, -] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-table_v2 0, p=1.0; 3-class only-champion 0 vs only-table_v2 0, p=1.0.

No call changes its label (fixed).

