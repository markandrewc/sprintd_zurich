# Experiment `two_readers`

Two readers (Qwen2.5-7B + Kev-4B facts) - agreement decides, disagreement -> review

RQ: RQ10 · base profile `two-readers` · split **dev** · baseline `champion` · commit 7957d36fb3 · 2026-10-10T12:09:33+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| champion | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of tuned_src |
| kev | 0.86 [0.67, 0.98] | 0.97 [0.91, 1.00] | 26/22 | re-fusion of tuned_src |
| r1 | 0.93 [0.82, 1.00] | 0.95 [0.86, 1.00] | 26/22 | re-fusion of tuned_src |
| r2 | 0.84 [0.65, 0.98] | 0.94 [0.84, 1.00] | 26/22 | re-fusion of tuned_src |
| qwen_para | 0.72 [0.52, 0.88] | 0.88 [0.74, 0.99] | 26/22 | re-fusion of para_src |
| kev_para | 0.90 [0.73, 1.00] | 0.99 [0.96, 1.00] | 26/22 | re-fusion of para_src |
| r1_para | 0.86 [0.68, 0.97] | 0.97 [0.90, 1.00] | 26/22 | re-fusion of para_src |
| r2_para | 0.80 [0.60, 0.94] | 0.93 [0.83, 1.00] | 26/22 | re-fusion of para_src |
| qwen_para2 | 0.74 [0.54, 0.90] | 0.90 [0.76, 0.99] | 26/22 | re-fusion of para2_src |
| kev_para2 | 0.90 [0.71, 1.00] | 0.99 [0.96, 1.00] | 26/22 | re-fusion of para2_src |
| r1_para2 | 0.85 [0.68, 0.99] | 0.98 [0.93, 1.00] | 26/22 | re-fusion of para2_src |
| r2_para2 | 0.79 [0.59, 0.93] | 0.93 [0.82, 1.00] | 26/22 | re-fusion of para2_src |
| qwen_blind | 0.73 [0.53, 0.90] | 0.81 [0.62, 0.96] | 26/22 | re-fusion of blind_src |
| kev_blind | 0.85 [0.68, 1.00] | 0.92 [0.80, 1.00] | 26/22 | re-fusion of blind_src |
| r1_blind | 0.84 [0.71, 0.96] | 0.89 [0.76, 0.99] | 26/22 | re-fusion of blind_src |
| r2_blind | 0.75 [0.59, 0.90] | 0.86 [0.74, 0.98] | 26/22 | re-fusion of blind_src |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of tuned_src |
| kev | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 56%] | 0.69 | 0% | 69% | 0.85 [0.72, 0.95] | re-fusion of tuned_src |
| r1 | 48 | 0.88 [0.78, 0.98] | 88% | 88% | 14% [0%, 35%] | 12% [0%, 29%] | 0.60 | 50% | 65% | 0.87 [0.76, 0.98] | re-fusion of tuned_src |
| r2 | 48 | 0.82 [0.65, 0.94] | 87% | 77% | 14% [0%, 35%] | 23% [0%, 47%] | 0.74 | 0% | 69% | 0.82 [0.68, 0.94] | re-fusion of tuned_src |
| qwen_para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.75 | 0% | 67% | 0.69 [0.55, 0.83] | re-fusion of para_src |
| kev_para | 48 | 0.87 [0.71, 0.98] | 100% | 77% | 0% [0%, 0%] | 23% [5%, 45%] | 0.73 | 0% | 71% | 0.88 [0.77, 0.98] | re-fusion of para_src |
| r1_para | 48 | 0.78 [0.63, 0.91] | 80% | 77% | 23% [0%, 50%] | 23% [5%, 45%] | 0.62 | 17% | 56% | 0.77 [0.61, 0.91] | re-fusion of para_src |
| r2_para | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 44%] | 38% [14%, 64%] | 0.74 | 0% | 67% | 0.72 [0.58, 0.86] | re-fusion of para_src |
| qwen_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.81 | 0% | 71% | 0.73 [0.58, 0.88] | re-fusion of para2_src |
| kev_para2 | 48 | 0.89 [0.73, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.81 | 0% | 77% | 0.90 [0.79, 1.00] | re-fusion of para2_src |
| r1_para2 | 48 | 0.83 [0.69, 0.95] | 81% | 85% | 23% [0%, 50%] | 15% [0%, 38%] | 0.79 | 33% | 67% | 0.81 [0.66, 0.95] | re-fusion of para2_src |
| r2_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.81 | 0% | 71% | 0.73 [0.58, 0.88] | re-fusion of para2_src |
| qwen_blind | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.56 | 0% | 58% | 0.70 [0.51, 0.87] | re-fusion of blind_src |
| kev_blind | 48 | 0.83 [0.65, 0.96] | 95% | 73% | 5% [0%, 14%] | 27% [6%, 50%] | 0.57 | 33% | 65% | 0.84 [0.72, 0.96] | re-fusion of blind_src |
| r1_blind | 48 | 0.83 [0.69, 0.95] | 81% | 85% | 23% [0%, 50%] | 15% [0%, 38%] | 0.46 | 67% | 56% | 0.81 [0.66, 0.94] | re-fusion of blind_src |
| r2_blind | 48 | 0.71 [0.53, 0.86] | 77% | 65% | 23% [0%, 50%] | 35% [11%, 62%] | 0.61 | 0% | 58% | 0.71 [0.57, 0.86] | re-fusion of blind_src |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of tuned_src |
| kev | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 56%] | 0.69 | 0% | 69% | 0.85 [0.72, 0.95] | re-fusion of tuned_src |
| r1 | 48 | 0.86 [0.74, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 33%] | 0.46 | 67% | 60% | 0.85 [0.73, 0.96] | re-fusion of tuned_src |
| r2 | 48 | 0.77 [0.57, 0.92] | 86% | 69% | 14% [0%, 35%] | 31% [8%, 57%] | 0.52 | 33% | 58% | 0.78 [0.64, 0.91] | re-fusion of tuned_src |
| qwen_para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.72 | 0% | 65% | 0.69 [0.55, 0.83] | re-fusion of para_src |
| kev_para | 48 | 0.84 [0.67, 0.96] | 100% | 73% | 0% [0%, 0%] | 27% [8%, 50%] | 0.73 | 0% | 71% | 0.87 [0.75, 0.96] | re-fusion of para_src |
| r1_para | 48 | 0.76 [0.60, 0.89] | 79% | 73% | 23% [0%, 50%] | 27% [8%, 50%] | 0.40 | 17% | 48% | 0.75 [0.60, 0.88] | re-fusion of para_src |
| r2_para | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 44%] | 38% [14%, 64%] | 0.70 | 0% | 65% | 0.72 [0.58, 0.86] | re-fusion of para_src |
| qwen_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.00 | 0% | 35% | 0.73 [0.58, 0.88] | re-fusion of para2_src |
| kev_para2 | 48 | 0.89 [0.73, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.81 | 0% | 77% | 0.90 [0.79, 1.00] | re-fusion of para2_src |
| r1_para2 | 48 | 0.83 [0.69, 0.95] | 81% | 85% | 23% [0%, 50%] | 15% [0%, 38%] | 0.00 | 33% | 40% | 0.81 [0.66, 0.95] | re-fusion of para2_src |
| r2_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.40 | 0% | 46% | 0.73 [0.58, 0.88] | re-fusion of para2_src |
| qwen_blind | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.56 | 0% | 58% | 0.70 [0.51, 0.87] | re-fusion of blind_src |
| kev_blind | 48 | 0.83 [0.65, 0.96] | 95% | 73% | 5% [0%, 14%] | 27% [6%, 50%] | 0.57 | 33% | 65% | 0.84 [0.72, 0.96] | re-fusion of blind_src |
| r1_blind | 48 | 0.83 [0.69, 0.95] | 81% | 85% | 23% [0%, 50%] | 15% [0%, 38%] | 0.18 | 67% | 48% | 0.81 [0.66, 0.94] | re-fusion of blind_src |
| r2_blind | 48 | 0.71 [0.53, 0.86] | 77% | 65% | 23% [0%, 50%] | 35% [11%, 62%] | 0.61 | 0% | 58% | 0.71 [0.57, 0.86] | re-fusion of blind_src |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| champion | 14% | 4/4 | 14% | yes | - |
| kev | 0% | 4/4 | 0% | yes | - |
| r1 | 14% | 4/4 | 14% | yes | - |
| r2 | 14% | 4/4 | 14% | yes | - |
| qwen_para | 23% (!) | 2/4 | 23% | **no** | - |
| kev_para | 0% | 4/4 | 0% | yes | - |
| r1_para | 23% (!) | 2/4 | 23% | **no** | - |
| r2_para | 18% | 2/4 | 18% | yes | - |
| qwen_para2 | 23% (!) | 2/4 | 23% | **no** | - |
| kev_para2 | 0% | 4/4 | 0% | yes | - |
| r1_para2 | 23% (!) | 2/4 | 23% | **no** | - |
| r2_para2 | 23% (!) | 2/4 | 23% | **no** | - |
| qwen_blind | 18% | 1/4 | 18% | yes | - |
| kev_blind | 0% | 4/4 | 5% | yes | - |
| r1_blind | 18% | 1/4 | 23% | **no** | - |
| r2_blind | 23% (!) | 1/4 | 23% | **no** | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of tuned_src |
| kev | 48 | 0.70 [0.44, 0.88] | 100% | 54% | 0% [0%, 0%] | 46% [21%, 72%] | 0.67 | 17% | 69% | 0.77 [0.64, 0.90] | re-fusion of tuned_src |
| r1 | 48 | 0.88 [0.78, 0.98] | 88% | 88% | 14% [0%, 35%] | 12% [0%, 29%] | 0.62 | 67% | 67% | 0.87 [0.76, 0.98] | re-fusion of tuned_src |
| r2 | 48 | 0.82 [0.65, 0.94] | 87% | 77% | 14% [0%, 35%] | 23% [0%, 47%] | 0.79 | 33% | 71% | 0.82 [0.68, 0.94] | re-fusion of tuned_src |
| qwen_para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.67 | 0% | 56% | 0.69 [0.55, 0.83] | re-fusion of para_src |
| kev_para | 48 | 0.73 [0.52, 0.88] | 100% | 58% | 0% [0%, 0%] | 42% [22%, 65%] | 0.67 | 17% | 69% | 0.79 [0.68, 0.89] | re-fusion of para_src |
| r1_para | 48 | 0.78 [0.63, 0.91] | 80% | 77% | 23% [0%, 50%] | 23% [5%, 45%] | 0.40 | 17% | 48% | 0.77 [0.61, 0.91] | re-fusion of para_src |
| r2_para | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 44%] | 38% [14%, 64%] | 0.62 | 0% | 56% | 0.72 [0.58, 0.86] | re-fusion of para_src |
| qwen_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.71 | 0% | 58% | 0.73 [0.58, 0.88] | re-fusion of para2_src |
| kev_para2 | 48 | 0.87 [0.70, 0.98] | 100% | 77% | 0% [0%, 0%] | 23% [4%, 46%] | 0.79 | 33% | 77% | 0.88 [0.77, 0.98] | re-fusion of para2_src |
| r1_para2 | 48 | 0.83 [0.69, 0.95] | 81% | 85% | 23% [0%, 50%] | 15% [0%, 38%] | 0.57 | 33% | 56% | 0.81 [0.66, 0.95] | re-fusion of para2_src |
| r2_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.75 | 0% | 60% | 0.73 [0.58, 0.88] | re-fusion of para2_src |
| qwen_blind | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.60 | 33% | 60% | 0.70 [0.51, 0.87] | re-fusion of blind_src |
| kev_blind | 48 | 0.56 [0.24, 0.78] | 100% | 38% | 0% [0%, 0%] | 62% [36%, 87%] | 0.57 | 0% | 62% | 0.69 [0.57, 0.82] | re-fusion of blind_src |
| r1_blind | 48 | 0.72 [0.54, 0.88] | 81% | 65% | 18% [0%, 44%] | 35% [11%, 59%] | 0.46 | 33% | 54% | 0.74 [0.59, 0.88] | re-fusion of blind_src |
| r2_blind | 48 | 0.59 [0.36, 0.75] | 72% | 50% | 23% [0%, 50%] | 50% [25%, 77%] | 0.46 | 0% | 48% | 0.64 [0.51, 0.77] | re-fusion of blind_src |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| champion | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 19.7 | 21.6 | 0 | 0 | 7957d36fb3 |
| kev | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.25 (FAR20: 0.20, 0.20, 0.20, 0.25) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 19.7 | 21.6 | 0 | 0 | 7957d36fb3 |
| r1 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 19.7 | 21.6 | 0 | 0 | 7957d36fb3 |
| r2 | 0.55 | 0.65 | 0.65, 0.35, 0.65, 0.35 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 19.7 | 21.6 | 0 | 0 | 7957d36fb3 |
| qwen_para | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25, 1.00!, 0.25!, 0.25) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 21.4 | 41.4 | 0 | 0 | 7957d36fb3 |
| kev_para | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.25) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 21.4 | 41.4 | 0 | 0 | 7957d36fb3 |
| r1_para | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.85, 1.00!, 0.85!, 0.85) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 21.4 | 41.4 | 0 | 0 | 7957d36fb3 |
| r2_para | 0.55 | 0.20 | 0.20, 0.35, 0.20, 0.20 (FAR20: 0.20, 0.90!, 0.20!, 0.20) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 21.4 | 41.4 | 0 | 0 | 7957d36fb3 |
| qwen_para2 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 1.00, 1.00!, 1.00!, 1.00) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.4 | 0 | 0 | 7957d36fb3 |
| kev_para2 | 0.55 | 0.25 | 0.30, 0.25, 0.25, 0.25 (FAR20: 0.35, 0.25, 0.25, 0.25) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.4 | 0 | 0 | 7957d36fb3 |
| r1_para2 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 1.00, 1.00!, 1.00!, 1.00) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.4 | 0 | 0 | 7957d36fb3 |
| r2_para2 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.95, 0.95!, 0.95!, 0.95) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 20.9 | 41.4 | 0 | 0 | 7957d36fb3 |
| qwen_blind | 0.55 | 0.20 | 0.70, 0.20, 0.20, 0.20 (FAR20: 0.95!, 0.20!, 0.20!, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 3.5 | 22.5 | 25.8 | 0 | 0 | 7957d36fb3 |
| kev_blind | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 3.5 | 22.5 | 25.8 | 0 | 0 | 7957d36fb3 |
| r1_blind | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20!, 1.00!, 1.00!, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 3.5 | 22.5 | 25.8 | 0 | 0 | 7957d36fb3 |
| r2_blind | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20!, 0.20!, 0.20!, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 3.5 | 22.5 | 25.8 | 0 | 0 | 7957d36fb3 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| champion | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| kev | 0.89 / 0% / 20% | 0.95 / 0% / 10% | 0.29 / - / 83% | 0.76 / 0% / 38% | 0.87 / 0% / 23% |
| r1 | 1.00 / 0% / 0% | 0.82 / 21% / 10% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.92 / 9% / 8% |
| r2 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.50 / - / 67% | 0.80 / 18% / 23% | 0.83 / 9% / 23% |
| qwen_para | 0.90 / 12% / 10% | 0.67 / 29% / 30% | 0.00 / - / 100% | 0.67 / 27% / 38% | 0.70 / 18% / 38% |
| kev_para | 1.00 / 0% / 0% | 0.95 / 0% / 10% | 0.29 / - / 83% | 0.87 / 0% / 23% | 0.87 / 0% / 23% |
| r1_para | 0.95 / 12% / 0% | 0.78 / 29% / 10% | 0.29 / - / 83% | 0.77 / 27% / 23% | 0.80 / 18% / 23% |
| r2_para | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.00 / - / 100% | 0.70 / 18% / 38% | 0.70 / 18% / 38% |
| qwen_para2 | 1.00 / 0% / 0% | 0.70 / 36% / 20% | 0.00 / - / 100% | 0.72 / 27% / 31% | 0.75 / 18% / 31% |
| kev_para2 | 1.00 / 0% / 0% | 0.95 / 0% / 10% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.92 / 0% / 15% |
| r1_para2 | 1.00 / 0% / 0% | 0.80 / 36% / 0% | 0.50 / - / 67% | 0.81 / 27% / 15% | 0.85 / 18% / 15% |
| r2_para2 | 1.00 / 0% / 0% | 0.70 / 36% / 20% | 0.00 / - / 100% | 0.72 / 27% / 31% | 0.75 / 18% / 31% |
| qwen_blind | 0.82 / 0% / 30% | 0.60 / 29% / 40% | 0.50 / - / 67% | 0.70 / 18% / 38% | 0.64 / 18% / 46% |
| kev_blind | 1.00 / 0% / 0% | 0.78 / 7% / 30% | 0.50 / - / 67% | 0.78 / 9% / 31% | 0.87 / 0% / 23% |
| r1_blind | 1.00 / 0% / 0% | 0.70 / 36% / 20% | 0.80 / - / 33% | 0.81 / 27% / 15% | 0.85 / 18% / 15% |
| r2_blind | 0.95 / 0% / 10% | 0.70 / 36% / 20% | 0.00 / - / 100% | 0.67 / 27% / 38% | 0.75 / 18% / 31% |

## `kev` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev - champion

| metric | champion | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.86 | -0.010 | [-0.206, +0.144] | no detectable difference |
| alarm AUC | 0.90 | 0.97 | +0.061 | [-0.019, +0.179] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev - champion

| metric | champion | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.044 | [-0.252, +0.104] | no detectable difference |
| alarm_f1 | 0.86 | 0.69 | -0.170 | [-0.513, +0.069] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [-6pp, +41pp] | no detectable difference |
| accuracy | 79% | 69% | -10pp | [-36pp, +9pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | -0.009 | [-0.172, +0.132] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev 4, p=1.0; 3-class only-champion 10 vs only-kev 5, p=0.3018.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev - champion

| metric | champion | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.022 | [-0.213, +0.114] | no detectable difference |
| alarm_f1 | 0.67 | 0.69 | +0.021 | [-0.280, +0.318] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-7pp, +32pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [-24pp, +21pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.011 | [-0.136, +0.141] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev 4, p=1.0; 3-class only-champion 7 vs only-kev 7, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev - champion

| metric | champion | kev | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.163 | [-0.426, +0.033] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.529, +0.042] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+4pp, +59pp] | **real**: champion better |
| accuracy | 79% | 69% | -10pp | [-34pp, +8pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.086 | [-0.250, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev 4, p=0.2668; 3-class only-champion 9 vs only-kev 4, p=0.2668.

Flips (cv, 15 calls):

| call | expected | champion | kev | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.16 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.16 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.79 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.79 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.93/0.05 | broken | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.80/0.09 | broken | 01:35-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.99 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.99 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.04 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `r1` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r1 - champion

| metric | champion | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.93 | +0.060 | [-0.002, +0.160] | no detectable difference |
| alarm AUC | 0.90 | 0.95 | +0.047 | [-0.008, +0.133] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1 - champion

| metric | champion | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.88 | +0.022 | [+0.000, +0.082] | no detectable difference |
| alarm_f1 | 0.86 | 0.60 | -0.257 | [-0.581, -0.044] | **real**: champion better |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 79% | 65% | -15pp | [-32pp, -2pp] | **real**: champion better |
| review_recall | 67% | 50% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.87 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-r1 1, p=1.0; 3-class only-champion 7 vs only-r1 0, p=0.0156.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1 - champion

| metric | champion | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.86 | +0.023 | [+0.000, +0.085] | no detectable difference |
| alarm_f1 | 0.67 | 0.46 | -0.205 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 15% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 69% | 60% | -8pp | [-19pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-r1 1, p=1.0; 3-class only-champion 4 vs only-r1 0, p=0.125.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1 - champion

| metric | champion | r1 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.88 | +0.022 | [+0.000, +0.082] | no detectable difference |
| alarm_f1 | 0.86 | 0.62 | -0.236 | [-0.556, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 79% | 67% | -12pp | [-30pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.87 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-r1 1, p=1.0; 3-class only-champion 6 vs only-r1 0, p=0.0312.

Flips (cv, 8 calls):

| call | expected | champion | r1 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.53 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.53 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.85 | same | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.86 | same | 02:48-02:54 documentation: Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde m... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.49 | same | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.45 | same | 01:35-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.25 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert ... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |

## `r2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r2 - champion

| metric | champion | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.84 | -0.022 | [-0.204, +0.115] | no detectable difference |
| alarm AUC | 0.90 | 0.94 | +0.039 | [+0.000, +0.131] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2 - champion

| metric | champion | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.046 | [-0.172, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.74 | -0.120 | [-0.309, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 79% | 69% | -10pp | [-28pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.82 | -0.038 | [-0.125, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-r2 0, p=0.5; 3-class only-champion 6 vs only-r2 1, p=0.125.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2 - champion

| metric | champion | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.77 | -0.074 | [-0.217, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.52 | -0.148 | [-0.444, +0.085] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [+0pp, +30pp] | no detectable difference |
| accuracy | 69% | 58% | -10pp | [-25pp, +0pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.78 | -0.058 | [-0.150, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-r2 0, p=0.25; 3-class only-champion 6 vs only-r2 1, p=0.125.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2 - champion

| metric | champion | r2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.046 | [-0.172, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.244, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-22pp, +0pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.82 | -0.038 | [-0.125, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-r2 0, p=0.5; 3-class only-champion 4 vs only-r2 0, p=0.125.

Flips (cv, 9 calls):

| call | expected | champion | r2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.77 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.76 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.50 | same | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wer... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert ... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Zuständigkeit/Kontrolle umgehen') liegt ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `qwen_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_para - champion

| metric | champion | qwen_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.72 | -0.147 | [-0.313, -0.025] | **real**: champion better |
| alarm AUC | 0.90 | 0.88 | -0.025 | [-0.081, +0.033] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_para - champion

| metric | champion | qwen_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.182 | [-0.361, -0.059] | **real**: champion better |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.287, +0.039] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-31pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.161 | [-0.288, -0.057] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_para 0, p=0.0078; 3-class only-champion 9 vs only-qwen_para 3, p=0.146.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_para - champion

| metric | champion | qwen_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.68 | -0.159 | [-0.344, -0.014] | **real**: champion better |
| alarm_f1 | 0.67 | 0.72 | +0.051 | [-0.167, +0.318] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-4pp, +43pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-24pp, +14pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.69 | -0.142 | [-0.276, -0.021] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_para 1, p=0.0391; 3-class only-champion 8 vs only-qwen_para 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_para - champion

| metric | champion | qwen_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.182 | [-0.361, -0.059] | **real**: champion better |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.444, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-38pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.161 | [-0.288, -0.057] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_para 0, p=0.0078; 3-class only-champion 11 vs only-qwen_para 0, p=0.001.

Flips (cv, 15 calls):

| call | expected | champion | qwen_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:25-01:37 disclosure: Ich muss nur die letzten vier Stellen. Also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier. - facts: ... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | alarm | no_alert | 0.91/0.13 | broken | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Kein Alarm: höchster Score 0.13 ('Zugangsinformation preisgegeben') liegt unter 0.20 (Schwelle 0.35 min... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.78 | same | 01:18-01:25 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt de... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.00 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.95) - Die Kunde fragt nach der Berechtigung ihres Mutterkontos... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.55) - Der Kunde fragt nach der Identität für das Konto seiner ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:10-02:10 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Die aktuelle Adresse steht richtig im Kontaktfeld. Die... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_para - champion

| metric | champion | kev_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.90 | +0.036 | [-0.130, +0.181] | no detectable difference |
| alarm AUC | 0.90 | 0.99 | +0.084 | [-0.017, +0.242] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_para - champion

| metric | champion | kev_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.007 | [-0.149, +0.133] | no detectable difference |
| alarm_f1 | 0.86 | 0.73 | -0.130 | [-0.414, +0.121] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-33pp, +12pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.88 | +0.030 | [-0.114, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_para 4, p=1.0; 3-class only-champion 10 vs only-kev_para 6, p=0.4545.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_para - champion

| metric | champion | kev_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.004 | [-0.161, +0.133] | no detectable difference |
| alarm_f1 | 0.67 | 0.73 | +0.061 | [-0.199, +0.350] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 69% | 71% | +2pp | [-23pp, +24pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.87 | +0.030 | [-0.114, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_para 5, p=1.0; 3-class only-champion 8 vs only-kev_para 9, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_para - champion

| metric | champion | kev_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.131 | [-0.352, +0.037] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.524, +0.070] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+4pp, +50pp] | **real**: champion better |
| accuracy | 79% | 69% | -10pp | [-34pp, +10pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.79 | -0.066 | [-0.223, +0.075] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-kev_para 4, p=0.3877; 3-class only-champion 10 vs only-kev_para 5, p=0.3018.

Flips (cv, 16 calls):

| call | expected | champion | kev_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.74 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.77 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.74 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.08 | same | 01:02-01:03 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.13 | same | 01:35-01:36 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C07-K3 | alarm | alarm | review | 0.97/0.15 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C09-K3 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.99 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.99 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.75 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.02 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.02 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.03 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.01 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `r1_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r1_para - champion

| metric | champion | r1_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.86 | -0.011 | [-0.159, +0.118] | no detectable difference |
| alarm AUC | 0.90 | 0.97 | +0.064 | [+0.000, +0.172] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_para - champion

| metric | champion | r1_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.078 | [-0.214, +0.032] | no detectable difference |
| alarm_f1 | 0.86 | 0.62 | -0.236 | [-0.635, +0.058] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 79% | 56% | -23pp | [-43pp, -7pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.084 | [-0.207, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-r1_para 1, p=0.2188; 3-class only-champion 13 vs only-r1_para 2, p=0.0074.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_para - champion

| metric | champion | r1_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.76 | -0.080 | [-0.235, +0.056] | no detectable difference |
| alarm_f1 | 0.67 | 0.40 | -0.267 | [-0.623, +0.043] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-12pp, +31pp] | no detectable difference |
| accuracy | 69% | 48% | -21pp | [-37pp, -7pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.75 | -0.084 | [-0.214, +0.030] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-r1_para 2, p=0.2891; 3-class only-champion 11 vs only-r1_para 1, p=0.0063.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_para - champion

| metric | champion | r1_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.078 | [-0.214, +0.032] | no detectable difference |
| alarm_f1 | 0.86 | 0.40 | -0.457 | [-0.824, -0.153] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 79% | 48% | -31pp | [-50pp, -16pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.084 | [-0.207, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-r1_para 1, p=0.2188; 3-class only-champion 15 vs only-r1_para 0, p=0.0001.

Flips (cv, 16 calls):

| call | expected | champion | r1_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.25 | broken | 01:25-01:37 disclosure: Ich muss nur die letzten vier Stellen. Also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier. - facts: ... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.44 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.50 | same | 01:18-01:25 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt de... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.86 | same | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.80 | same | 02:50-03:00 documentation: und die Vereinbarung meiner Tante gar nicht erfahre. Dem Wunsch kann ich nicht folgen. Wir müssen die Anlage zur Hälfte der Kreditstelle verfolgen. - facts: Fakt: Verborgene... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.51 | same | 01:32-01:47 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.55 | same | 01:33-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C07-K3 | alarm | alarm | review | 0.97/0.50 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.37 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.25 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.74 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.62 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.26 | broken | 01:10-02:10 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Die aktuelle Adresse steht richtig im Kontaktfeld. Die... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Zwei Leser: Qwen Kein Alarm, Kev Kein Alarm (einig). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Zwei Leser: Qwen Kein Alarm, Kev Kein Alarm (einig). | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `r2_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r2_para - champion

| metric | champion | r2_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.80 | -0.067 | [-0.248, +0.090] | no detectable difference |
| alarm AUC | 0.90 | 0.93 | +0.024 | [-0.045, +0.141] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_para - champion

| metric | champion | r2_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.167 | [-0.342, -0.043] | **real**: champion better |
| alarm_f1 | 0.86 | 0.74 | -0.120 | [-0.301, +0.036] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-31pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.138 | [-0.250, -0.038] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 7 vs only-r2_para 0, p=0.0156; 3-class only-champion 9 vs only-r2_para 3, p=0.146.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_para - champion

| metric | champion | r2_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.70 | -0.144 | [-0.327, +0.005] | no detectable difference |
| alarm_f1 | 0.67 | 0.70 | +0.036 | [-0.209, +0.333] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-4pp, +43pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-23pp, +14pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.72 | -0.119 | [-0.243, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 7 vs only-r2_para 1, p=0.0703; 3-class only-champion 8 vs only-r2_para 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_para - champion

| metric | champion | r2_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.167 | [-0.342, -0.043] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.236 | [-0.506, -0.047] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-38pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.138 | [-0.250, -0.038] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 7 vs only-r2_para 0, p=0.0156; 3-class only-champion 11 vs only-r2_para 0, p=0.001.

Flips (cv, 15 calls):

| call | expected | champion | r2_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | no_alert | 0.91/0.19 | broken | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Kein Alarm: höchster Score 0.19 ('Zugangsinformation preisgegeben') liegt unter 0.20 (Schwelle 0.35 min... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.75 | same | 01:18-01:25 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt de... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.80 | same | 02:50-03:00 documentation: und die Vereinbarung meiner Tante gar nicht erfahre. Dem Wunsch kann ich nicht folgen. Wir müssen die Anlage zur Hälfte der Kreditstelle verfolgen. - facts: Fakt: Verborgene... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.07 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.07 ('Insiderhandel') liegt unter 0.20 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.95) - Die Kunde fragt nach der Berechtigung ihres Mutterkontos... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.55) - Der Kunde fragt nach der Identität für das Konto seiner ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:10-02:10 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Die aktuelle Adresse steht richtig im Kontaktfeld. Die... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `qwen_para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_para2 - champion

| metric | champion | qwen_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.74 | -0.130 | [-0.290, -0.011] | **real**: champion better |
| alarm AUC | 0.90 | 0.90 | -0.003 | [-0.042, +0.040] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_para2 - champion

| metric | champion | qwen_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.81 | -0.048 | [-0.132, +0.065] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-24pp, +4pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-qwen_para2 0, p=0.0312; 3-class only-champion 7 vs only-qwen_para2 3, p=0.3438.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_para2 - champion

| metric | champion | qwen_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.73 | -0.105 | [-0.275, +0.030] | no detectable difference |
| alarm_f1 | 0.67 | 0.00 | -0.667 | [-0.875, -0.364] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-9pp, +36pp] | no detectable difference |
| accuracy | 69% | 35% | -33pp | [-52pp, -17pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.73 | -0.103 | [-0.227, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-qwen_para2 1, p=0.125; 3-class only-champion 16 vs only-qwen_para2 0, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_para2 - champion

| metric | champion | qwen_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.71 | -0.147 | [-0.269, -0.038] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 58% | -21pp | [-35pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-qwen_para2 0, p=0.0312; 3-class only-champion 10 vs only-qwen_para2 0, p=0.002.

Flips (cv, 13 calls):

| call | expected | champion | qwen_para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.75 | same | 00:55-00:59 documentation: Ich kenne den Unterschied, aber ich habe Angst, dass es darum länger geht. - facts: Fakt: Verborgene Tatsache ist relevant = ja (0.51) - Die Kunde möchte, dass ihre Tante ni... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:05-08:08 trade: Nehmen Sie den Kaufwunsch bitte entgegen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde sagt explizit, dass er Aktien kaufen möchte: „Nehmen Sie den Kaufwun... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.93) - Die Kunde fragt nach der gültigen Berechtigung zum Konto... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.56) - Die Kunde fragt nach der Berechtigung zum Kontostand ihr... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:49 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 02:51-03:51 documentation: Die Rechnung für den Notarieatsvorschuss ist nicht Teil des Kaufpreises. Genau diese habe ich auch dazu gelegt. Warum war meine Summe höher? Der Vorschuss ist separat fällig... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_para2 - champion

| metric | champion | kev_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.90 | +0.031 | [-0.166, +0.188] | no detectable difference |
| alarm AUC | 0.90 | 0.99 | +0.085 | [-0.007, +0.238] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_para2 - champion

| metric | champion | kev_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.89 | +0.031 | [-0.131, +0.176] | no detectable difference |
| alarm_f1 | 0.86 | 0.81 | -0.046 | [-0.348, +0.213] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 19% | +4pp | [-20pp, +27pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-28pp, +20pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.90 | +0.049 | [-0.093, +0.179] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_para2 5, p=0.7266; 3-class only-champion 8 vs only-kev_para2 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_para2 - champion

| metric | champion | kev_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.89 | +0.054 | [-0.112, +0.206] | no detectable difference |
| alarm_f1 | 0.67 | 0.81 | +0.144 | [-0.197, +0.506] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [-25pp, +25pp] | no detectable difference |
| accuracy | 69% | 77% | +8pp | [-18pp, +33pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.90 | +0.068 | [-0.071, +0.206] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_para2 6, p=0.5078; 3-class only-champion 7 vs only-kev_para2 11, p=0.4807.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_para2 - champion

| metric | champion | kev_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.007 | [-0.164, +0.162] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.326, +0.127] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-17pp, +31pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-24pp, +17pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.88 | +0.030 | [-0.115, +0.164] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_para2 5, p=1.0; 3-class only-champion 6 vs only-kev_para2 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | champion | kev_para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.80 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.21 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.74 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.68 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C09-K3 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/1.00 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 1.00 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.50/0.13 | broken | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.77 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.05 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.05 ('Relevante Angabe verschweigen') liegt unter 0.15 (Schwelle 0.30 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.50 | same | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.01 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `r1_para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r1_para2 - champion

| metric | champion | r1_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.85 | -0.011 | [-0.190, +0.142] | no detectable difference |
| alarm AUC | 0.90 | 0.98 | +0.074 | [+0.000, +0.207] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_para2 - champion

| metric | champion | r1_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.033 | [-0.170, +0.112] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.326, +0.127] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [-22pp, +23pp] | no detectable difference |
| accuracy | 79% | 67% | -12pp | [-30pp, +0pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.81 | -0.045 | [-0.174, +0.091] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-r1_para2 2, p=0.6875; 3-class only-champion 8 vs only-r1_para2 2, p=0.1094.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_para2 - champion

| metric | champion | r1_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.83 | -0.010 | [-0.158, +0.149] | no detectable difference |
| alarm_f1 | 0.67 | 0.00 | -0.667 | [-0.875, -0.364] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 19% | 15% | -4pp | [-27pp, +19pp] | no detectable difference |
| accuracy | 69% | 40% | -29pp | [-48pp, -14pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.81 | -0.026 | [-0.163, +0.112] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-r1_para2 3, p=1.0; 3-class only-champion 14 vs only-r1_para2 0, p=0.0001.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_para2 - champion

| metric | champion | r1_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.033 | [-0.170, +0.112] | no detectable difference |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.533, -0.089] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [-22pp, +23pp] | no detectable difference |
| accuracy | 79% | 56% | -23pp | [-39pp, -10pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.81 | -0.045 | [-0.174, +0.091] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-r1_para2 2, p=0.6875; 3-class only-champion 11 vs only-r1_para2 0, p=0.001.

Flips (cv, 12 calls):

| call | expected | champion | r1_para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.85 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt den TAN-Code sieben, drei, ei... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.56 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.83 | same | 03:11-03:23 documentation: Ich will meine Tante nicht aus den Sachen rauslassen und ich werde nur die Wohnung nicht verlieren. Den Druck kann ich aufnehmen, aber ich löse ihn nicht mit einer falschen ... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.72 | same | 00:55-00:59 documentation: Ich kenne den Unterschied, aber ich habe Angst, dass es darum länger geht. - facts: Fakt: Verborgene Tatsache ist relevant = ja (0.51) - Die Kunde möchte, dass ihre Tante ni... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.25 | broken | 08:05-08:08 trade: Nehmen Sie den Kaufwunsch bitte entgegen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde sagt explizit, dass er Aktien kaufen möchte: „Nehmen Sie den Kaufwun... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.25 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.25 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.75 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.63 | same | 08:23-08:49 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.27 | broken | 02:51-03:51 documentation: Die Rechnung für den Notarieatsvorschuss ist nicht Teil des Kaufpreises. Genau diese habe ich auch dazu gelegt. Warum war meine Summe höher? Der Vorschuss ist separat fällig... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Zwei Leser: Qwen Kein Alarm, Kev Kein Alarm (einig). | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `r2_para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r2_para2 - champion

| metric | champion | r2_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.79 | -0.081 | [-0.261, +0.061] | no detectable difference |
| alarm AUC | 0.90 | 0.93 | +0.021 | [-0.029, +0.103] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_para2 - champion

| metric | champion | r2_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.81 | -0.048 | [-0.132, +0.065] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-24pp, +4pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-r2_para2 0, p=0.0312; 3-class only-champion 7 vs only-r2_para2 3, p=0.3438.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_para2 - champion

| metric | champion | r2_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.73 | -0.105 | [-0.275, +0.030] | no detectable difference |
| alarm_f1 | 0.67 | 0.40 | -0.267 | [-0.525, -0.058] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-9pp, +36pp] | no detectable difference |
| accuracy | 69% | 46% | -23pp | [-38pp, -10pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.73 | -0.103 | [-0.227, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-r2_para2 1, p=0.125; 3-class only-champion 11 vs only-r2_para2 0, p=0.001.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_para2 - champion

| metric | champion | r2_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.222, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 60% | -19pp | [-33pp, -7pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-r2_para2 0, p=0.0312; 3-class only-champion 9 vs only-r2_para2 0, p=0.0039.

Flips (cv, 13 calls):

| call | expected | champion | r2_para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.72 | same | 00:55-00:59 documentation: Ich kenne den Unterschied, aber ich habe Angst, dass es darum länger geht. - facts: Fakt: Verborgene Tatsache ist relevant = ja (0.51) - Die Kunde möchte, dass ihre Tante ni... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:05-08:08 trade: Nehmen Sie den Kaufwunsch bitte entgegen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde sagt explizit, dass er Aktien kaufen möchte: „Nehmen Sie den Kaufwun... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.93) - Die Kunde fragt nach der gültigen Berechtigung zum Konto... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.56) - Die Kunde fragt nach der Berechtigung zum Kontostand ihr... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:49 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 02:51-03:51 documentation: Die Rechnung für den Notarieatsvorschuss ist nicht Teil des Kaufpreises. Genau diese habe ich auch dazu gelegt. Warum war meine Summe höher? Der Vorschuss ist separat fällig... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `qwen_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_blind - champion

| metric | champion | qwen_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.73 | -0.141 | [-0.323, -0.008] | **real**: champion better |
| alarm AUC | 0.90 | 0.81 | -0.094 | [-0.260, +0.017] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_blind - champion

| metric | champion | qwen_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.390, -0.034] | **real**: champion better |
| alarm_f1 | 0.86 | 0.56 | -0.301 | [-0.556, -0.095] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 58% | -21pp | [-40pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.70 | -0.157 | [-0.312, -0.016] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-qwen_blind 1, p=0.0215; 3-class only-champion 11 vs only-qwen_blind 1, p=0.0063.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_blind - champion

| metric | champion | qwen_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.67 | -0.173 | [-0.349, -0.023] | **real**: champion better |
| alarm_f1 | 0.67 | 0.56 | -0.111 | [-0.359, +0.106] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [+5pp, +45pp] | **real**: champion better |
| accuracy | 69% | 58% | -10pp | [-29pp, +6pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.70 | -0.138 | [-0.281, -0.004] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_blind 1, p=0.0391; 3-class only-champion 8 vs only-qwen_blind 3, p=0.2266.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_blind - champion

| metric | champion | qwen_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.390, -0.034] | **real**: champion better |
| alarm_f1 | 0.86 | 0.60 | -0.257 | [-0.534, -0.078] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 60% | -19pp | [-36pp, -4pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.70 | -0.157 | [-0.312, -0.016] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-qwen_blind 1, p=0.0215; 3-class only-champion 10 vs only-qwen_blind 1, p=0.0117.

Flips (cv, 15 calls):

| call | expected | champion | qwen_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.50 | same | 01:11-01:23 disclosure: Am zwanzig. soll ich die Reservierung bestätigen. Dafür kann es auch jemand anderes, der Interesse hat. Ich will nicht alles verlieren, nur weil wir noch einen neuen Abschnitt ... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.07 | broken | 02:48-02:54 documentation: Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.93/0.04 | broken | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.80/0.04 | broken | 01:35-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:08-08:25 trade: Der Sparplan soll bleiben, wie er ist. Ich habe den Betrag, den Namen der Aktien und die Quelle zum Wunsch notiert. Ich kann Ihnen in diesem Rückkauf keine Ausführung bestätigen. Ic... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.85 | broken | 01:09-01:22 trade: Claudia hat mir den Link zum Bericht auf der Firmenseite geschickt. Der Grossauftrag wurde am letzten Freitag veröffentlicht und jeder kann ihn dort lesen. Sie arbeiten nicht bei di... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Anfrage zu Drittperson = ja (0.... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten der Drittperson ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | no_alert | 0.50/0.00 | broken | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.00 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte'... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.00 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 02:04-03:04 disclosure: Oder als Rechnungsperiode. Ich kann sie heute Abend erreichen und ihr die richtige Rechnung benennen. Ich möchte mit Ihrem Familienstaat ein Bild Ihres Kontos verteilen. Sie ka... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.50 | same | 03:11-03:18 disclosure: Wir haben vereinbart, dass ich zuerst mit Ihnen reden und nicht selber entscheiden, welche Rechnung zu einem Strang kommt. - facts: Fakt: Anfrage zu Drittperson = ja (1.00) - D... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_blind - champion

| metric | champion | kev_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.85 | -0.012 | [-0.207, +0.157] | no detectable difference |
| alarm AUC | 0.90 | 0.92 | +0.015 | [-0.057, +0.090] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_blind - champion

| metric | champion | kev_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.037 | [-0.244, +0.139] | no detectable difference |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.675, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-30pp, +0pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [-13pp, +40pp] | no detectable difference |
| accuracy | 79% | 65% | -15pp | [-40pp, +9pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.84 | -0.012 | [-0.177, +0.158] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_blind 4, p=1.0; 3-class only-champion 12 vs only-kev_blind 5, p=0.1435.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_blind - champion

| metric | champion | kev_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.83 | -0.014 | [-0.231, +0.173] | no detectable difference |
| alarm_f1 | 0.67 | 0.57 | -0.095 | [-0.434, +0.214] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-30pp, +0pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-20pp, +37pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-28pp, +21pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.84 | +0.007 | [-0.161, +0.183] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_blind 5, p=1.0; 3-class only-champion 8 vs only-kev_blind 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_blind - champion

| metric | champion | kev_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.56 | -0.307 | [-0.656, -0.063] | **real**: champion better |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.675, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 62% | +46pp | [+18pp, +75pp] | **real**: champion better |
| accuracy | 79% | 62% | -17pp | [-41pp, +5pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.163 | [-0.333, +0.010] | no detectable difference |

McNemar exact (calls): flag correct only-champion 12 vs only-kev_blind 3, p=0.0352; 3-class only-champion 12 vs only-kev_blind 4, p=0.0768.

Flips (cv, 17 calls):

| call | expected | champion | kev_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.68 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.64 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.07 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.07 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.07 | same | 01:02-01:03 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.07 | same | 01:35-01:36 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C07-K3 | alarm | alarm | no_alert | 0.97/0.05 | broken | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.05 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Prüfen (knapp unter Schwelle): Score 0.05 für 'Insiderhandel' liegt ... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.96 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.96 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Zuständigkeit/Kontrolle umgehen') liegt ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.08 | fixed | Prüfen (knapp unter Schwelle): Score 0.08 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.05 | fixed | Prüfen (knapp unter Schwelle): Score 0.05 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `r1_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r1_blind - champion

| metric | champion | r1_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.84 | -0.025 | [-0.167, +0.105] | no detectable difference |
| alarm AUC | 0.90 | 0.89 | -0.016 | [-0.096, +0.060] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_blind - champion

| metric | champion | r1_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.033 | [-0.177, +0.109] | no detectable difference |
| alarm_f1 | 0.86 | 0.46 | -0.396 | [-0.769, -0.122] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +31pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [-21pp, +21pp] | no detectable difference |
| accuracy | 79% | 56% | -23pp | [-43pp, -4pp] | **real**: champion better |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.81 | -0.045 | [-0.191, +0.083] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-r1_blind 2, p=0.6875; 3-class only-champion 13 vs only-r1_blind 2, p=0.0074.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_blind - champion

| metric | champion | r1_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.83 | -0.010 | [-0.162, +0.143] | no detectable difference |
| alarm_f1 | 0.67 | 0.18 | -0.485 | [-0.811, -0.174] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +31pp] | no detectable difference |
| miss_rate | 19% | 15% | -4pp | [-27pp, +20pp] | no detectable difference |
| accuracy | 69% | 48% | -21pp | [-40pp, -2pp] | **real**: champion better |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.81 | -0.026 | [-0.182, +0.114] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-r1_blind 3, p=1.0; 3-class only-champion 12 vs only-r1_blind 2, p=0.0129.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r1_blind - champion

| metric | champion | r1_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.72 | -0.139 | [-0.321, -0.006] | **real**: champion better |
| alarm_f1 | 0.86 | 0.46 | -0.396 | [-0.769, -0.122] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 15% | 35% | +19pp | [+0pp, +42pp] | no detectable difference |
| accuracy | 79% | 54% | -25pp | [-44pp, -8pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.74 | -0.119 | [-0.271, +0.009] | no detectable difference |

McNemar exact (calls): flag correct only-champion 7 vs only-r1_blind 1, p=0.0703; 3-class only-champion 13 vs only-r1_blind 1, p=0.0018.

Flips (cv, 15 calls):

| call | expected | champion | r1_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.80 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.91) - Der Kunde gibt die Ziffern der TAN-Card aus, ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.72 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Zuga... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.29 | same | 01:11-01:23 disclosure: Am zwanzig. soll ich die Reservierung bestätigen. Dafür kann es auch jemand anderes, der Interesse hat. Ich will nicht alles verlieren, nur weil wir noch einen neuen Abschnitt ... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.07 | same | 02:33-02:54 documentation: Ich habe Ihnen darum noch keinen Zeitpunkt für einen Entscheid zu sagen. Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. Ich nehme das Zahler... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.05 | same | 01:02-01:03 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.05 | same | 01:35-01:36 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.25 | broken | 08:08-08:25 trade: Der Sparplan soll bleiben, wie er ist. Ich habe den Betrag, den Namen der Aktien und die Quelle zum Wunsch notiert. Ich kann Ihnen in diesem Rückkauf keine Ausführung bestätigen. Ic... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | review | 0.00/0.43 | broken | 01:09-01:22 trade: Claudia hat mir den Link zum Bericht auf der Firmenseite geschickt. Der Grossauftrag wurde am letzten Freitag veröffentlicht und jeder kann ihn dort lesen. Sie arbeiten nicht bei di... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K3 | alarm | alarm | review | 0.97/0.47 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.28 | same | 03:33-03:43 trade: Wegen dieser Nachricht möchte ich nicht für fünftausend Franken Aktien von der Alpes Optik kaufen. Können Sie den einmaligen Auftrag für mich entgegennehmen? - facts: Fakt: Eigener ... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.47 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bi... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Zwei Leser: Qwen Kein Alarm, Kev Kein Alarm (einig). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Zwei Leser: Qwen Kein Alarm, Kev Kein Alarm (einig). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.04 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Prüfen -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.03 | fixed | Zwei Leser: Qwen Kein Alarm, Kev Prüfen -> uneinig, bitte prüfen. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `r2_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = r2_blind - champion

| metric | champion | r2_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.75 | -0.115 | [-0.285, +0.048] | no detectable difference |
| alarm AUC | 0.90 | 0.86 | -0.045 | [-0.133, +0.039] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_blind - champion

| metric | champion | r2_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.71 | -0.154 | [-0.328, -0.031] | **real**: champion better |
| alarm_f1 | 0.86 | 0.61 | -0.246 | [-0.536, +0.019] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +31pp] | no detectable difference |
| miss_rate | 15% | 35% | +19pp | [+0pp, +42pp] | no detectable difference |
| accuracy | 79% | 58% | -21pp | [-45pp, +0pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.71 | -0.142 | [-0.286, -0.031] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 7 vs only-r2_blind 0, p=0.0156; 3-class only-champion 13 vs only-r2_blind 3, p=0.0213.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_blind - champion

| metric | champion | r2_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.71 | -0.132 | [-0.297, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.61 | -0.056 | [-0.320, +0.222] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +31pp] | no detectable difference |
| miss_rate | 19% | 35% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 69% | 58% | -10pp | [-32pp, +8pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.71 | -0.122 | [-0.263, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 7 vs only-r2_blind 1, p=0.0703; 3-class only-champion 9 vs only-r2_blind 4, p=0.2668.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = r2_blind - champion

| metric | champion | r2_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.59 | -0.272 | [-0.524, -0.100] | **real**: champion better |
| alarm_f1 | 0.86 | 0.46 | -0.396 | [-0.769, -0.122] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +31pp] | no detectable difference |
| miss_rate | 15% | 50% | +35pp | [+11pp, +62pp] | **real**: champion better |
| accuracy | 79% | 48% | -31pp | [-50pp, -15pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.64 | -0.218 | [-0.368, -0.083] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 11 vs only-r2_blind 0, p=0.001; 3-class only-champion 15 vs only-r2_blind 0, p=0.0001.

Flips (cv, 19 calls):

| call | expected | champion | r2_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.79 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.91) - Der Kunde gibt die Ziffern der TAN-Card aus, ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.72 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Zuga... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.08 | same | 02:05-02:55 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.07 | same | 02:33-02:54 documentation: Ich habe Ihnen darum noch keinen Zeitpunkt für einen Entscheid zu sagen. Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. Ich nehme das Zahler... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.93/0.05 | broken | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.05 | same | 01:33-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:08-08:25 trade: Der Sparplan soll bleiben, wie er ist. Ich habe den Betrag, den Namen der Aktien und die Quelle zum Wunsch notiert. Ich kann Ihnen in diesem Rückkauf keine Ausführung bestätigen. Ic... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:09-01:22 trade: Claudia hat mir den Link zum Bericht auf der Firmenseite geschickt. Der Grossauftrag wurde am letzten Freitag veröffentlicht und jeder kann ihn dort lesen. Sie arbeiten nicht bei di... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.09 | same | 03:33-03:43 trade: Wegen dieser Nachricht möchte ich nicht für fünftausend Franken Aktien von der Alpes Optik kaufen. Können Sie den einmaligen Auftrag für mich entgegennehmen? - facts: Fakt: Eigener ... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Anfrage zu Drittperson = ja (0.... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten der Drittperson ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.50 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-08:03 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - facts: Fakt: Verlangt Nicht-Protokollieren = ja (0.83) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsst... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

