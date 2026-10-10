# Experiment `two_readers`

Two readers (Qwen2.5-7B + Kev-4B facts) - agreement decides, disagreement -> review

RQ: RQ10 · base profile `two-readers` · split **dev** · baseline `champion` · commit 55af68993a · 2026-10-10T15:01:58+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| qwen_v3 | 0.92 [0.80, 1.00] | 0.90 [0.73, 1.00] | 26/22 | re-fusion of v3_src |
| kev_v3 | 0.83 [0.65, 0.96] | 0.95 [0.89, 1.00] | 26/22 | re-fusion of v3_src |
| r1_v3 | 0.95 [0.88, 1.00] | 0.94 [0.84, 1.00] | 26/22 | re-fusion of v3_src |
| r2_v3 | 0.94 [0.85, 1.00] | 0.92 [0.79, 1.00] | 26/22 | re-fusion of v3_src |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen_v3 | 48 | 0.91 [0.80, 1.00] | 89% | 92% | 14% [0%, 35%] | 8% [0%, 25%] | 0.86 | 100% | 83% | 0.89 [0.78, 1.00] | re-fusion of v3_src |
| kev_v3 | 48 | 0.80 [0.60, 0.93] | 95% | 69% | 5% [0%, 15%] | 31% [9%, 56%] | 0.67 | 0% | 67% | 0.82 [0.70, 0.94] | re-fusion of v3_src |
| r1_v3 | 48 | 0.91 [0.84, 0.98] | 86% | 96% | 18% [0%, 40%] | 4% [0%, 12%] | 0.60 | 83% | 67% | 0.89 [0.79, 0.98] | re-fusion of v3_src |
| r2_v3 | 48 | 0.91 [0.80, 1.00] | 89% | 92% | 14% [0%, 35%] | 8% [0%, 25%] | 0.79 | 100% | 79% | 0.89 [0.78, 1.00] | re-fusion of v3_src |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen_v3 | 48 | 0.88 [0.77, 0.98] | 88% | 88% | 14% [0%, 35%] | 12% [0%, 30%] | 0.67 | 100% | 73% | 0.87 [0.76, 0.98] | re-fusion of v3_src |
| kev_v3 | 48 | 0.80 [0.60, 0.93] | 95% | 69% | 5% [0%, 15%] | 31% [9%, 56%] | 0.67 | 0% | 67% | 0.82 [0.70, 0.94] | re-fusion of v3_src |
| r1_v3 | 48 | 0.89 [0.81, 0.96] | 86% | 92% | 18% [0%, 40%] | 8% [0%, 19%] | 0.46 | 100% | 62% | 0.87 [0.76, 0.96] | re-fusion of v3_src |
| r2_v3 | 48 | 0.86 [0.72, 0.97] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 38%] | 0.52 | 100% | 67% | 0.85 [0.72, 0.97] | re-fusion of v3_src |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| qwen_v3 | 14% | 4/4 | 14% | yes | - |
| kev_v3 | 5% | 4/4 | 5% | yes | - |
| r1_v3 | 18% | 2/4 | 18% | yes | - |
| r2_v3 | 14% | 4/4 | 14% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen_v3 | 48 | 0.91 [0.80, 1.00] | 89% | 92% | 14% [0%, 35%] | 8% [0%, 25%] | 0.86 | 100% | 83% | 0.89 [0.78, 1.00] | re-fusion of v3_src |
| kev_v3 | 48 | 0.71 [0.49, 0.87] | 94% | 58% | 5% [0%, 15%] | 42% [19%, 67%] | 0.67 | 17% | 67% | 0.77 [0.65, 0.88] | re-fusion of v3_src |
| r1_v3 | 48 | 0.91 [0.84, 0.98] | 86% | 96% | 18% [0%, 40%] | 4% [0%, 12%] | 0.62 | 100% | 69% | 0.89 [0.79, 0.98] | re-fusion of v3_src |
| r2_v3 | 48 | 0.91 [0.80, 1.00] | 89% | 92% | 14% [0%, 35%] | 8% [0%, 25%] | 0.79 | 100% | 79% | 0.89 [0.78, 1.00] | re-fusion of v3_src |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen_v3 | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.9 | 11.2 | 18.0 | 0 | 0 | 55af68993a |
| kev_v3 | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.25 (FAR20: 0.20, 0.20, 0.20, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 4.9 | 11.2 | 18.0 | 0 | 0 | 55af68993a |
| r1_v3 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.70 (FAR20: 0.90, 0.90!, 0.90!, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.9 | 11.2 | 18.0 | 0 | 0 | 55af68993a |
| r2_v3 | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 4.9 | 11.2 | 18.0 | 0 | 0 | 55af68993a |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| qwen_v3 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 1.00 / - / 0% | 0.89 / 18% / 8% | 0.92 / 9% / 8% |
| kev_v3 | 0.89 / 0% / 20% | 0.90 / 7% / 10% | 0.29 / - / 83% | 0.76 / 0% / 38% | 0.83 / 9% / 23% |
| r1_v3 | 1.00 / 0% / 0% | 0.78 / 29% / 10% | 1.00 / - / 0% | 0.89 / 18% / 8% | 0.93 / 18% / 0% |
| r2_v3 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 1.00 / - / 0% | 0.89 / 18% / 8% | 0.92 / 9% / 8% |

