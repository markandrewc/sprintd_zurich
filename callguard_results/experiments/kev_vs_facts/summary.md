# Experiment `kev_vs_facts`

Kev-4B and general (untuned) questions vs our tuned facts, de/en views, wording-robustness probes

RQ: RQ10 · base profile `recommended` · split **dev** · baseline `champion` · commit 96ec3da9c3 (dirty) · 2026-10-10T12:57:52+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| kev_general | 0.79 [0.62, 0.93] | 0.81 [0.64, 0.96] | 26/22 |  |
| kev_general_en | 0.71 [0.52, 0.89] | 0.79 [0.61, 0.95] | 26/22 |  |
| kev_facts | 0.86 [0.67, 0.98] | 0.97 [0.91, 1.00] | 26/22 |  |
| qwen_general | 0.72 [0.55, 0.88] | 0.73 [0.54, 0.91] | 26/22 |  |
| champion | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 |  |
| facts_only | 0.89 [0.77, 0.99] | 0.92 [0.78, 1.00] | 26/22 | re-fusion of champion |
| qwen_general_en | 0.68 [0.52, 0.85] | 0.73 [0.55, 0.91] | 26/22 |  |
| kev_general_oracle | 0.89 [0.69, 0.99] | 0.93 [0.75, 1.00] | 26/22 | **ORACLE** |
| kev_general_alone | 0.79 [0.62, 0.93] | 0.81 [0.63, 0.96] | 26/22 | re-fusion of kev_general |
| kev_general_en_alone | 0.71 [0.52, 0.89] | 0.79 [0.61, 0.95] | 26/22 | re-fusion of kev_general_en |
| kev_facts_alone | 0.91 [0.77, 1.00] | 0.98 [0.93, 1.00] | 26/22 | re-fusion of kev_facts |
| qwen_general_alone | 0.72 [0.54, 0.88] | 0.73 [0.53, 0.91] | 26/22 | re-fusion of qwen_general |
| qwen_general_en_alone | 0.69 [0.53, 0.85] | 0.74 [0.55, 0.92] | 26/22 | re-fusion of qwen_general_en |
| kev_general_oracle_alone | 0.89 [0.69, 0.99] | 0.93 [0.75, 1.00] | 26/22 | **ORACLE**, re-fusion of kev_general_oracle |
| kev_facts_choice | 0.85 [0.69, 0.99] | 0.90 [0.77, 1.00] | 26/22 |  |
| kev_facts_band | 0.86 [0.68, 0.98] | 0.94 [0.84, 1.00] | 26/22 |  |
| kev_facts_blind | 0.85 [0.68, 1.00] | 0.92 [0.80, 1.00] | 26/22 |  |
| kev_facts_para | 0.90 [0.73, 1.00] | 0.99 [0.96, 1.00] | 26/22 |  |
| kev_facts_para2 | 0.90 [0.71, 1.00] | 0.99 [0.96, 1.00] | 26/22 |  |
| kev_general_para | 0.88 [0.74, 1.00] | 0.83 [0.67, 0.96] | 26/22 |  |
| kev_general_para_alone | 0.88 [0.76, 1.00] | 0.84 [0.68, 0.97] | 26/22 | re-fusion of kev_general_para |
| qwen_facts_blind | 0.73 [0.53, 0.90] | 0.81 [0.62, 0.96] | 26/22 |  |
| qwen_facts_para | 0.72 [0.52, 0.88] | 0.88 [0.74, 0.99] | 26/22 |  |
| qwen_facts_para2 | 0.74 [0.54, 0.90] | 0.90 [0.76, 0.99] | 26/22 |  |
| qwen_general_para | 0.71 [0.50, 0.89] | 0.69 [0.48, 0.87] | 26/22 |  |
| qwen_general_para_alone | 0.70 [0.49, 0.89] | 0.69 [0.47, 0.87] | 26/22 | re-fusion of qwen_general_para |
| kev_facts_v3 | 0.83 [0.65, 0.96] | 0.95 [0.89, 1.00] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| kev_general | 48 | 0.63 [0.45, 0.78] | 56% | 73% | 68% [44%, 89%] | 27% [7%, 50%] | 0.74 | 17% | 50% | 0.52 [0.39, 0.66] |  |
| kev_general_en | 48 | 0.66 [0.47, 0.81] | 57% | 77% | 68% [36%, 93%] | 23% [0%, 47%] | 0.62 | 17% | 48% | 0.54 [0.40, 0.70] |  |
| kev_facts | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 56%] | 0.69 | 0% | 69% | 0.85 [0.72, 0.95] |  |
| qwen_general | 48 | 0.75 [0.60, 0.88] | 63% | 92% | 64% [38%, 88%] | 8% [0%, 25%] | 0.63 | 33% | 54% | 0.64 [0.54, 0.77] |  |
| champion | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| qwen_general_en | 48 | 0.68 [0.49, 0.84] | 63% | 73% | 50% [25%, 75%] | 27% [5%, 50%] | 0.62 | 0% | 54% | 0.62 [0.48, 0.76] |  |
| kev_general_oracle | 48 | 0.80 [0.67, 0.93] | 71% | 92% | 45% [14%, 80%] | 8% [0%, 25%] | 0.80 | 33% | 62% | 0.73 [0.54, 0.91] | **ORACLE** |
| kev_general_alone | 48 | 0.63 [0.45, 0.78] | 56% | 73% | 68% [44%, 89%] | 27% [7%, 50%] | 0.74 | 17% | 50% | 0.52 [0.39, 0.66] | re-fusion of kev_general |
| kev_general_en_alone | 48 | 0.66 [0.47, 0.81] | 57% | 77% | 68% [36%, 93%] | 23% [0%, 47%] | 0.62 | 17% | 48% | 0.54 [0.40, 0.70] | re-fusion of kev_general_en |
| kev_facts_alone | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 56%] | 0.76 | 0% | 73% | 0.85 [0.72, 0.95] | re-fusion of kev_facts |
| qwen_general_alone | 48 | 0.75 [0.60, 0.88] | 63% | 92% | 64% [38%, 88%] | 8% [0%, 25%] | 0.63 | 33% | 54% | 0.64 [0.54, 0.77] | re-fusion of qwen_general |
| qwen_general_en_alone | 48 | 0.68 [0.49, 0.84] | 63% | 73% | 50% [25%, 75%] | 27% [5%, 50%] | 0.62 | 0% | 54% | 0.62 [0.48, 0.76] | re-fusion of qwen_general_en |
| kev_general_oracle_alone | 48 | 0.80 [0.67, 0.93] | 71% | 92% | 45% [14%, 80%] | 8% [0%, 25%] | 0.80 | 33% | 62% | 0.73 [0.54, 0.91] | **ORACLE**, re-fusion of kev_general_oracle |
| kev_facts_choice | 48 | 0.78 [0.58, 0.92] | 83% | 73% | 18% [0%, 45%] | 27% [7%, 50%] | 0.71 | 0% | 62% | 0.77 [0.62, 0.92] |  |
| kev_facts_band | 48 | 0.87 [0.70, 0.98] | 100% | 77% | 0% [0%, 0%] | 23% [4%, 46%] | 0.67 | 0% | 69% | 0.88 [0.77, 0.98] |  |
| kev_facts_blind | 48 | 0.83 [0.65, 0.96] | 95% | 73% | 5% [0%, 14%] | 27% [6%, 50%] | 0.57 | 33% | 65% | 0.84 [0.72, 0.96] |  |
| kev_facts_para | 48 | 0.87 [0.71, 0.98] | 100% | 77% | 0% [0%, 0%] | 23% [5%, 45%] | 0.73 | 0% | 71% | 0.88 [0.77, 0.98] |  |
| kev_facts_para2 | 48 | 0.89 [0.73, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.81 | 0% | 77% | 0.90 [0.79, 1.00] |  |
| kev_general_para | 48 | 0.84 [0.70, 0.97] | 77% | 92% | 32% [0%, 58%] | 8% [0%, 25%] | 0.67 | 33% | 62% | 0.80 [0.67, 0.95] |  |
| kev_general_para_alone | 48 | 0.84 [0.70, 0.97] | 77% | 92% | 32% [0%, 58%] | 8% [0%, 25%] | 0.67 | 33% | 62% | 0.80 [0.67, 0.95] | re-fusion of kev_general_para |
| qwen_facts_blind | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.56 | 0% | 58% | 0.70 [0.51, 0.87] |  |
| qwen_facts_para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.75 | 0% | 67% | 0.69 [0.55, 0.83] |  |
| qwen_facts_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.81 | 0% | 71% | 0.73 [0.58, 0.88] |  |
| qwen_general_para | 48 | 0.68 [0.44, 0.85] | 67% | 69% | 41% [12%, 73%] | 31% [8%, 58%] | 0.59 | 0% | 52% | 0.64 [0.44, 0.83] |  |
| qwen_general_para_alone | 48 | 0.68 [0.44, 0.85] | 67% | 69% | 41% [12%, 73%] | 31% [8%, 58%] | 0.55 | 0% | 50% | 0.64 [0.44, 0.83] | re-fusion of qwen_general_para |
| kev_facts_v3 | 48 | 0.80 [0.60, 0.93] | 95% | 69% | 5% [0%, 15%] | 31% [9%, 56%] | 0.67 | 0% | 67% | 0.82 [0.70, 0.94] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| kev_general | 48 | 0.62 [0.36, 0.82] | 74% | 54% | 23% [0%, 50%] | 46% [20%, 73%] | 0.67 | 33% | 62% | 0.66 [0.49, 0.81] |  |
| kev_general_en | 48 | 0.67 [0.42, 0.86] | 88% | 54% | 9% [0%, 29%] | 46% [20%, 73%] | 0.65 | 0% | 65% | 0.72 [0.58, 0.87] |  |
| kev_facts | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 56%] | 0.69 | 0% | 69% | 0.85 [0.72, 0.95] |  |
| qwen_general | 48 | 0.62 [0.42, 0.80] | 68% | 58% | 32% [7%, 61%] | 42% [19%, 67%] | 0.60 | 17% | 58% | 0.63 [0.48, 0.78] |  |
| champion | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.67 | 67% | 69% | 0.85 [0.73, 0.96] | re-fusion of champion |
| qwen_general_en | 48 | 0.61 [0.35, 0.80] | 70% | 54% | 27% [0%, 57%] | 46% [19%, 73%] | 0.56 | 0% | 54% | 0.63 [0.47, 0.79] |  |
| kev_general_oracle | 48 | 0.76 [0.50, 0.93] | 100% | 62% | 0% [0%, 0%] | 38% [12%, 67%] | 0.79 | 0% | 73% | 0.81 [0.67, 0.94] | **ORACLE** |
| kev_general_alone | 48 | 0.62 [0.36, 0.82] | 74% | 54% | 23% [0%, 50%] | 46% [20%, 73%] | 0.67 | 33% | 62% | 0.66 [0.49, 0.81] | re-fusion of kev_general |
| kev_general_en_alone | 48 | 0.67 [0.42, 0.86] | 88% | 54% | 9% [0%, 29%] | 46% [20%, 73%] | 0.65 | 0% | 65% | 0.72 [0.58, 0.87] | re-fusion of kev_general_en |
| kev_facts_alone | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 56%] | 0.76 | 0% | 73% | 0.85 [0.72, 0.95] | re-fusion of kev_facts |
| qwen_general_alone | 48 | 0.62 [0.42, 0.80] | 68% | 58% | 32% [7%, 61%] | 42% [19%, 67%] | 0.60 | 17% | 58% | 0.63 [0.48, 0.78] | re-fusion of qwen_general |
| qwen_general_en_alone | 48 | 0.61 [0.35, 0.80] | 70% | 54% | 27% [0%, 57%] | 46% [19%, 73%] | 0.59 | 0% | 56% | 0.63 [0.47, 0.79] | re-fusion of qwen_general_en |
| kev_general_oracle_alone | 48 | 0.76 [0.50, 0.93] | 100% | 62% | 0% [0%, 0%] | 38% [12%, 67%] | 0.79 | 0% | 73% | 0.81 [0.67, 0.94] | **ORACLE**, re-fusion of kev_general_oracle |
| kev_facts_choice | 48 | 0.78 [0.58, 0.92] | 83% | 73% | 18% [0%, 45%] | 27% [7%, 50%] | 0.71 | 0% | 62% | 0.77 [0.62, 0.92] |  |
| kev_facts_band | 48 | 0.82 [0.62, 0.95] | 100% | 69% | 0% [0%, 0%] | 31% [9%, 55%] | 0.67 | 0% | 69% | 0.85 [0.73, 0.95] |  |
| kev_facts_blind | 48 | 0.83 [0.65, 0.96] | 95% | 73% | 5% [0%, 14%] | 27% [6%, 50%] | 0.57 | 33% | 65% | 0.84 [0.72, 0.96] |  |
| kev_facts_para | 48 | 0.84 [0.67, 0.96] | 100% | 73% | 0% [0%, 0%] | 27% [8%, 50%] | 0.73 | 0% | 71% | 0.87 [0.75, 0.96] |  |
| kev_facts_para2 | 48 | 0.89 [0.73, 1.00] | 100% | 81% | 0% [0%, 0%] | 19% [0%, 42%] | 0.81 | 0% | 77% | 0.90 [0.79, 1.00] |  |
| kev_general_para | 48 | 0.90 [0.79, 1.00] | 92% | 88% | 9% [0%, 29%] | 12% [0%, 29%] | 0.70 | 67% | 77% | 0.90 [0.78, 1.00] |  |
| kev_general_para_alone | 48 | 0.90 [0.79, 1.00] | 92% | 88% | 9% [0%, 29%] | 12% [0%, 29%] | 0.70 | 67% | 77% | 0.90 [0.78, 1.00] | re-fusion of kev_general_para |
| qwen_facts_blind | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.56 | 0% | 58% | 0.70 [0.51, 0.87] |  |
| qwen_facts_para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.72 | 0% | 65% | 0.69 [0.55, 0.83] |  |
| qwen_facts_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.00 | 0% | 35% | 0.73 [0.58, 0.88] |  |
| qwen_general_para | 48 | 0.65 [0.40, 0.83] | 75% | 58% | 23% [0%, 50%] | 42% [17%, 70%] | 0.47 | 0% | 54% | 0.67 [0.53, 0.82] |  |
| qwen_general_para_alone | 48 | 0.62 [0.35, 0.82] | 74% | 54% | 23% [0%, 50%] | 46% [18%, 75%] | 0.47 | 0% | 54% | 0.66 [0.51, 0.81] | re-fusion of qwen_general_para |
| kev_facts_v3 | 48 | 0.80 [0.60, 0.93] | 95% | 69% | 5% [0%, 15%] | 31% [9%, 56%] | 0.67 | 0% | 67% | 0.82 [0.70, 0.94] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| kev_general | 0% | 4/4 | 23% | **no** | - |
| kev_general_en | 0% | 4/4 | 9% | yes | - |
| kev_facts | 0% | 4/4 | 0% | yes | - |
| qwen_general | 27% (!) | 1/4 | 32% | **no** | - |
| champion | 14% | 4/4 | 14% | yes | - |
| facts_only | 14% | 4/4 | 14% | yes | - |
| qwen_general_en | 18% | 1/4 | 27% | **no** | - |
| kev_general_oracle | 0% | 4/4 | 0% | yes | - |
| kev_general_alone | 0% | 4/4 | 23% | **no** | - |
| kev_general_en_alone | 0% | 4/4 | 9% | yes | - |
| kev_facts_alone | 0% | 4/4 | 0% | yes | - |
| qwen_general_alone | 27% (!) | 1/4 | 32% | **no** | - |
| qwen_general_en_alone | 18% | 1/4 | 27% | **no** | - |
| kev_general_oracle_alone | 0% | 4/4 | 0% | yes | - |
| kev_facts_choice | 0% | 4/4 | 18% | yes | - |
| kev_facts_band | 0% | 4/4 | 0% | yes | - |
| kev_facts_blind | 0% | 4/4 | 5% | yes | - |
| kev_facts_para | 0% | 4/4 | 0% | yes | - |
| kev_facts_para2 | 0% | 4/4 | 0% | yes | - |
| kev_general_para | 9% | 4/4 | 9% | yes | - |
| kev_general_para_alone | 9% | 4/4 | 9% | yes | - |
| qwen_facts_blind | 18% | 1/4 | 18% | yes | - |
| qwen_facts_para | 23% (!) | 2/4 | 23% | **no** | - |
| qwen_facts_para2 | 23% (!) | 2/4 | 23% | **no** | - |
| qwen_general_para | 18% | 2/4 | 23% | **no** | - |
| qwen_general_para_alone | 18% | 2/4 | 23% | **no** | - |
| kev_facts_v3 | 5% | 4/4 | 5% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| kev_general | 48 | 0.70 [0.45, 0.86] | 88% | 58% | 9% [0%, 23%] | 42% [17%, 69%] | 0.62 | 33% | 65% | 0.74 [0.62, 0.87] |  |
| kev_general_en | 48 | 0.67 [0.42, 0.86] | 88% | 54% | 9% [0%, 29%] | 46% [20%, 73%] | 0.67 | 17% | 67% | 0.72 [0.58, 0.87] |  |
| kev_facts | 48 | 0.70 [0.44, 0.88] | 100% | 54% | 0% [0%, 0%] | 46% [21%, 72%] | 0.67 | 17% | 69% | 0.77 [0.64, 0.90] |  |
| qwen_general | 48 | 0.61 [0.38, 0.79] | 70% | 54% | 27% [0%, 57%] | 46% [21%, 70%] | 0.60 | 0% | 58% | 0.63 [0.48, 0.79] |  |
| champion | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| qwen_general_en | 48 | 0.62 [0.40, 0.81] | 68% | 58% | 32% [8%, 60%] | 42% [17%, 68%] | 0.62 | 0% | 56% | 0.63 [0.48, 0.78] |  |
| kev_general_oracle | 48 | 0.78 [0.55, 0.96] | 90% | 69% | 9% [0%, 30%] | 31% [8%, 57%] | 0.79 | 33% | 73% | 0.80 [0.61, 0.96] | **ORACLE** |
| kev_general_alone | 48 | 0.68 [0.43, 0.85] | 83% | 58% | 14% [0%, 30%] | 42% [17%, 69%] | 0.62 | 33% | 62% | 0.72 [0.58, 0.85] | re-fusion of kev_general |
| kev_general_en_alone | 48 | 0.67 [0.42, 0.86] | 88% | 54% | 9% [0%, 29%] | 46% [20%, 73%] | 0.67 | 17% | 67% | 0.72 [0.58, 0.87] | re-fusion of kev_general_en |
| kev_facts_alone | 48 | 0.70 [0.44, 0.88] | 100% | 54% | 0% [0%, 0%] | 46% [21%, 72%] | 0.75 | 17% | 73% | 0.77 [0.64, 0.90] | re-fusion of kev_facts |
| qwen_general_alone | 48 | 0.61 [0.38, 0.79] | 70% | 54% | 27% [0%, 57%] | 46% [21%, 70%] | 0.60 | 0% | 58% | 0.63 [0.48, 0.79] | re-fusion of qwen_general |
| qwen_general_en_alone | 48 | 0.62 [0.40, 0.81] | 68% | 58% | 32% [8%, 60%] | 42% [17%, 68%] | 0.62 | 0% | 56% | 0.63 [0.48, 0.78] | re-fusion of qwen_general_en |
| kev_general_oracle_alone | 48 | 0.78 [0.55, 0.96] | 90% | 69% | 9% [0%, 30%] | 31% [8%, 57%] | 0.79 | 33% | 73% | 0.80 [0.61, 0.96] | **ORACLE**, re-fusion of kev_general_oracle |
| kev_facts_choice | 48 | 0.70 [0.42, 0.90] | 100% | 54% | 0% [0%, 0%] | 46% [18%, 73%] | 0.75 | 33% | 75% | 0.77 [0.63, 0.91] |  |
| kev_facts_band | 48 | 0.73 [0.49, 0.89] | 100% | 58% | 0% [0%, 0%] | 42% [19%, 68%] | 0.67 | 33% | 71% | 0.79 [0.66, 0.90] |  |
| kev_facts_blind | 48 | 0.56 [0.24, 0.78] | 100% | 38% | 0% [0%, 0%] | 62% [36%, 87%] | 0.57 | 0% | 62% | 0.69 [0.57, 0.82] |  |
| kev_facts_para | 48 | 0.73 [0.52, 0.88] | 100% | 58% | 0% [0%, 0%] | 42% [22%, 65%] | 0.67 | 17% | 69% | 0.79 [0.68, 0.89] |  |
| kev_facts_para2 | 48 | 0.87 [0.70, 0.98] | 100% | 77% | 0% [0%, 0%] | 23% [4%, 46%] | 0.79 | 33% | 77% | 0.88 [0.77, 0.98] |  |
| kev_general_para | 48 | 0.90 [0.79, 1.00] | 92% | 88% | 9% [0%, 29%] | 12% [0%, 29%] | 0.70 | 67% | 77% | 0.90 [0.78, 1.00] |  |
| kev_general_para_alone | 48 | 0.90 [0.79, 1.00] | 92% | 88% | 9% [0%, 29%] | 12% [0%, 29%] | 0.70 | 67% | 77% | 0.90 [0.78, 1.00] | re-fusion of kev_general_para |
| qwen_facts_blind | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.60 | 33% | 60% | 0.70 [0.51, 0.87] |  |
| qwen_facts_para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.67 | 0% | 56% | 0.69 [0.55, 0.83] |  |
| qwen_facts_para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.71 | 0% | 58% | 0.73 [0.58, 0.88] |  |
| qwen_general_para | 48 | 0.60 [0.36, 0.78] | 76% | 50% | 18% [0%, 41%] | 50% [25%, 75%] | 0.50 | 0% | 56% | 0.66 [0.53, 0.79] |  |
| qwen_general_para_alone | 48 | 0.60 [0.36, 0.78] | 76% | 50% | 18% [0%, 41%] | 50% [25%, 75%] | 0.50 | 0% | 56% | 0.66 [0.53, 0.79] | re-fusion of qwen_general_para |
| kev_facts_v3 | 48 | 0.71 [0.49, 0.87] | 94% | 58% | 5% [0%, 15%] | 42% [19%, 67%] | 0.67 | 17% | 67% | 0.77 [0.65, 0.88] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| kev_general | 0.70 | 0.40 | 0.50, 0.35, 0.40, 0.35 (FAR20: 0.50, 0.70, 0.70, 0.75) | 2.3 | asr 0.0, diarize 0.0, checks 2.2 | 2.4 | 7.8 | 0 | 0 | 96ec3da9c3 |
| kev_general_en | 0.70 | 0.25 | 0.60, 0.25, 0.65, 0.25 (FAR20: 0.65, 0.75, 0.65, 0.65) | 2.2 | asr 0.0, diarize 0.0, translate 0.0, checks 2.1 | 2.2 | 7.6 | 0 | 0 | 96ec3da9c3 |
| kev_facts | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.25 (FAR20: 0.20, 0.20, 0.20, 0.25) | 15.6 | asr 0.0, diarize 0.0, checks 15.6 | 15.7 | 20.0 | 0 | 0 | 96ec3da9c3 |
| qwen_general | 0.70 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.60, 0.65!, 0.65!, 0.60!) | 3.0 | asr 0.0, diarize 0.0, checks 2.9 | 3.0 | 15.0 | 0 | 0 | 96ec3da9c3 |
| champion | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 96ec3da9c3 |
| facts_only | 0.55 | 0.70 | 0.70, 0.70, 0.70, 0.70 (FAR20: 0.95, 0.95, 0.95, 0.95) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 4.0 | 1.6 | 0 | 0 | 96ec3da9c3 |
| qwen_general_en | 0.70 | 0.20 | 0.20, 0.50, 0.20, 0.20 (FAR20: 0.80, 0.95!, 0.80!, 0.95!) | 13.0 | asr 0.0, diarize 0.0, translate 12.0, checks 1.0 | 1.0 | 15.0 | 0 | 0 | 96ec3da9c3 |
| kev_general_oracle | 0.70 | 0.45 | 0.45, 0.50, 0.45, 0.45 (FAR20: 0.70, 0.70, 0.80, 0.70) | 1.4 | asr 0.0, diarize 0.0, checks 1.4 | 1.4 | 3.0 | 0 | 0 | 96ec3da9c3 |
| kev_general_alone | 0.70 | 0.40 | 0.50, 0.35, 0.40, 0.35 (FAR20: 0.50, 0.70, 0.70, 0.75) | 0.0 | asr 0.0, diarize 0.0, checks 2.2 | 2.3 | 7.8 | 0 | 0 | 96ec3da9c3 |
| kev_general_en_alone | 0.70 | 0.25 | 0.60, 0.25, 0.65, 0.25 (FAR20: 0.65, 0.75, 0.65, 0.65) | 0.0 | asr 0.0, diarize 0.0, translate 0.0, checks 2.1 | 2.2 | 7.6 | 0 | 0 | 96ec3da9c3 |
| kev_facts_alone | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.25 (FAR20: 0.20, 0.20, 0.20, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 15.6 | 15.6 | 20.0 | 0 | 0 | 96ec3da9c3 |
| qwen_general_alone | 0.70 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.60, 0.65!, 0.65!, 0.60!) | 0.0 | asr 0.0, diarize 0.0, checks 2.9 | 2.9 | 15.0 | 0 | 0 | 96ec3da9c3 |
| qwen_general_en_alone | 0.70 | 0.20 | 0.20, 0.50, 0.20, 0.20 (FAR20: 0.80, 0.95!, 0.80!, 0.95!) | 0.0 | asr 0.0, diarize 0.0, translate 12.0, checks 1.0 | 1.0 | 15.0 | 0 | 0 | 96ec3da9c3 |
| kev_general_oracle_alone | 0.70 | 0.45 | 0.45, 0.50, 0.45, 0.45 (FAR20: 0.70, 0.70, 0.80, 0.70) | 0.0 | asr 0.0, diarize 0.0, checks 1.4 | 1.4 | 3.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_choice | 0.55 | 0.20 | 0.25, 0.20, 0.20, 0.20 (FAR20: 0.25, 0.25, 0.25, 0.20) | 15.8 | asr 0.0, diarize 0.0, checks 15.8 | 15.9 | 20.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_band | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.30) | 0.0 | asr 0.0, diarize 0.0, checks 0.0 | 0.1 | 0.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_blind | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20) | 19.0 | asr 0.0, diarize 0.0, checks 18.9 | 19.0 | 24.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_para | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.25) | 15.6 | asr 0.0, diarize 0.0, checks 15.6 | 15.7 | 20.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_para2 | 0.55 | 0.25 | 0.30, 0.25, 0.25, 0.25 (FAR20: 0.35, 0.25, 0.25, 0.25) | 15.7 | asr 0.0, diarize 0.0, checks 15.6 | 15.7 | 20.0 | 0 | 0 | 96ec3da9c3 |
| kev_general_para | 0.70 | 0.65 | 0.65, 0.55, 0.65, 0.70 (FAR20: 0.70, 0.70, 0.70, 0.70) | 2.6 | asr 0.0, diarize 0.0, checks 2.5 | 2.6 | 9.4 | 0 | 0 | 96ec3da9c3 |
| kev_general_para_alone | 0.70 | 0.65 | 0.65, 0.55, 0.65, 0.70 (FAR20: 0.70, 0.70, 0.70, 0.70) | 0.0 | asr 0.0, diarize 0.0, checks 2.5 | 2.5 | 9.4 | 0 | 0 | 96ec3da9c3 |
| qwen_facts_blind | 0.55 | 0.20 | 0.70, 0.20, 0.20, 0.20 (FAR20: 0.95!, 0.20!, 0.20!, 0.20) | 3.5 | asr 0.0, diarize 0.0, checks 3.5 | 3.6 | 1.8 | 0 | 0 | 96ec3da9c3 |
| qwen_facts_para | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25, 1.00!, 0.25!, 0.25) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 5.8 | 21.4 | 0 | 0 | 96ec3da9c3 |
| qwen_facts_para2 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 1.00, 1.00!, 1.00!, 1.00) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 5.3 | 21.4 | 0 | 0 | 96ec3da9c3 |
| qwen_general_para | 0.70 | 0.20 | 0.20, 0.25, 0.20, 0.20 (FAR20: 0.30, 0.60!, 0.60, 0.70!) | 3.1 | asr 0.0, diarize 0.0, checks 3.0 | 3.1 | 15.0 | 0 | 0 | 96ec3da9c3 |
| qwen_general_para_alone | 0.70 | 0.30 | 0.30, 0.30, 0.20, 0.20 (FAR20: 0.30, 1.00!, 0.70, 0.70!) | 0.0 | asr 0.0, diarize 0.0, checks 3.0 | 3.0 | 15.0 | 0 | 0 | 96ec3da9c3 |
| kev_facts_v3 | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.25 (FAR20: 0.20, 0.20, 0.20, 0.25) | 6.3 | asr 0.0, diarize 0.0, checks 6.3 | 6.3 | 8.0 | 0 | 0 | 96ec3da9c3 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| kev_general | 0.70 / 62% / 20% | 0.57 / 71% / 20% | 0.67 / - / 50% | 0.65 / 73% / 23% | 0.62 / 64% / 31% |
| kev_general_en | 0.76 / 38% / 20% | 0.53 / 86% / 20% | 0.80 / - / 33% | 0.65 / 73% / 23% | 0.67 / 64% / 23% |
| kev_facts | 0.89 / 0% / 20% | 0.95 / 0% / 10% | 0.29 / - / 83% | 0.76 / 0% / 38% | 0.87 / 0% / 23% |
| qwen_general | 0.83 / 50% / 0% | 0.57 / 71% / 20% | 1.00 / - / 0% | 0.75 / 64% / 8% | 0.75 / 64% / 8% |
| champion | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| facts_only | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| qwen_general_en | 0.80 / 62% / 0% | 0.55 / 43% / 40% | 0.67 / - / 50% | 0.64 / 55% / 31% | 0.71 / 45% / 23% |
| kev_general_oracle | 0.83 / 50% / 0% | 0.77 / 43% / 0% | 0.80 / - / 33% | 0.80 / 45% / 8% | 0.80 / 45% / 8% |
| kev_general_alone | 0.70 / 62% / 20% | 0.57 / 71% / 20% | 0.67 / - / 50% | 0.65 / 73% / 23% | 0.62 / 64% / 31% |
| kev_general_en_alone | 0.76 / 38% / 20% | 0.53 / 86% / 20% | 0.80 / - / 33% | 0.65 / 73% / 23% | 0.67 / 64% / 23% |
| kev_facts_alone | 0.89 / 0% / 20% | 0.95 / 0% / 10% | 0.29 / - / 83% | 0.76 / 0% / 38% | 0.87 / 0% / 23% |
| qwen_general_alone | 0.83 / 50% / 0% | 0.57 / 71% / 20% | 1.00 / - / 0% | 0.75 / 64% / 8% | 0.75 / 64% / 8% |
| qwen_general_en_alone | 0.80 / 62% / 0% | 0.55 / 43% / 40% | 0.67 / - / 50% | 0.64 / 55% / 31% | 0.71 / 45% / 23% |
| kev_general_oracle_alone | 0.83 / 50% / 0% | 0.77 / 43% / 0% | 0.80 / - / 33% | 0.80 / 45% / 8% | 0.80 / 45% / 8% |
| kev_facts_choice | 0.91 / 25% / 0% | 0.74 / 14% / 30% | 0.50 / - / 67% | 0.75 / 18% / 31% | 0.80 / 18% / 23% |
| kev_facts_band | 1.00 / 0% / 0% | 0.89 / 0% / 20% | 0.50 / - / 67% | 0.82 / 0% / 31% | 0.92 / 0% / 15% |
| kev_facts_blind | 1.00 / 0% / 0% | 0.78 / 7% / 30% | 0.50 / - / 67% | 0.78 / 9% / 31% | 0.87 / 0% / 23% |
| kev_facts_para | 1.00 / 0% / 0% | 0.95 / 0% / 10% | 0.29 / - / 83% | 0.87 / 0% / 23% | 0.87 / 0% / 23% |
| kev_facts_para2 | 1.00 / 0% / 0% | 0.95 / 0% / 10% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.92 / 0% / 15% |
| kev_general_para | 1.00 / 0% / 0% | 0.64 / 50% / 20% | 1.00 / - / 0% | 0.83 / 36% / 8% | 0.86 / 27% / 8% |
| kev_general_para_alone | 1.00 / 0% / 0% | 0.64 / 50% / 20% | 1.00 / - / 0% | 0.83 / 36% / 8% | 0.86 / 27% / 8% |
| qwen_facts_blind | 0.82 / 0% / 30% | 0.60 / 29% / 40% | 0.50 / - / 67% | 0.70 / 18% / 38% | 0.64 / 18% / 46% |
| qwen_facts_para | 0.90 / 12% / 10% | 0.67 / 29% / 30% | 0.00 / - / 100% | 0.67 / 27% / 38% | 0.70 / 18% / 38% |
| qwen_facts_para2 | 1.00 / 0% / 0% | 0.70 / 36% / 20% | 0.00 / - / 100% | 0.72 / 27% / 31% | 0.75 / 18% / 31% |
| qwen_general_para | 0.67 / 75% / 20% | 0.63 / 21% / 40% | 0.80 / - / 33% | 0.67 / 45% / 31% | 0.69 / 36% / 31% |
| qwen_general_para_alone | 0.67 / 75% / 20% | 0.63 / 21% / 40% | 0.80 / - / 33% | 0.67 / 45% / 31% | 0.69 / 36% / 31% |
| kev_facts_v3 | 0.89 / 0% / 20% | 0.90 / 7% / 10% | 0.29 / - / 83% | 0.76 / 0% / 38% | 0.83 / 9% / 23% |

## `kev_general` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.79 | -0.078 | [-0.238, +0.059] | no detectable difference |
| alarm AUC | 0.90 | 0.81 | -0.092 | [-0.235, +0.002] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.63 | -0.229 | [-0.393, -0.111] | **real**: champion better |
| alarm_f1 | 0.86 | 0.74 | -0.113 | [-0.350, +0.063] | no detectable difference |
| false_alarm_rate | 14% | 68% | +55pp | [+30pp, +75pp] | **real**: champion better |
| miss_rate | 15% | 27% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 79% | 50% | -29pp | [-50pp, -10pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.52 | -0.330 | [-0.486, -0.191] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 15 vs only-kev_general 0, p=0.0001; 3-class only-champion 17 vs only-kev_general 3, p=0.0026.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.62 | -0.218 | [-0.456, -0.041] | **real**: champion better |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [-0.374, +0.335] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [-20pp, +38pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [+0pp, +54pp] | no detectable difference |
| accuracy | 69% | 62% | -6pp | [-29pp, +15pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.66 | -0.180 | [-0.354, -0.022] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 12 vs only-kev_general 3, p=0.0352; 3-class only-champion 10 vs only-kev_general 7, p=0.6291.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.165 | [-0.387, -0.015] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.236 | [-0.511, -0.051] | **real**: champion better |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 65% | -15pp | [-31pp, -2pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.74 | -0.112 | [-0.261, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-kev_general 2, p=0.1094; 3-class only-champion 9 vs only-kev_general 2, p=0.0654.

Flips (cv, 22 calls):

| call | expected | champion | kev_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.41 | broken | Prüfen (knapp unter Schwelle): Score 0.41 für 'Relevante Angabe verschweigen' liegt zwischen 0.35 und der Schwelle 0.50. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.55 | broken | 01:42-02:15 access: Ich habe also vermutlich das falsche Blatt herausgenommen. Und im Mail hat jemand geschrieben, ich solle zum Gerätewechsel die Prüfung umgehen. Das habe ich nicht gemacht. Die Abse... | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.44 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.02/0.59 | broken | 00:42-01:25 access: Richtig. Ich will auch gar nicht über ihn persönlich wissen. Ich habe das Protokoll der Wahl und das Formular zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingereicht. ... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.03/0.53 | broken | 00:34-01:13 access: Es geht ausschliesslich um das Vereinskonto, nicht um ein persönliches Konto des Vorgängers. Richtig? Richtig. Ich will auch gar nichts über ihn persönlich wissen. Ich habe das Pro... | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.90/0.24 | broken | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.29 | broken | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.22 | broken | Prüfen (knapp unter Schwelle): Score 0.22 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | review | 0.00/0.22 | broken | Prüfen (knapp unter Schwelle): Score 0.22 für 'Insiderhandel' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.00/0.34 | broken | Prüfen (knapp unter Schwelle): Score 0.34 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | review | 0.00/0.32 | broken | Prüfen (knapp unter Schwelle): Score 0.32 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.39 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.39 für 'Insiderhandel' >= Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.45 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.45 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.61 | same | 07:22-08:03 documentation: Ich habe einen unvollständigen Entwurf, nur damit der Frühe noch da ist. Gut, die O-Ange und die grüne Markierung sind jetzt klar. Für die violetten Zeilen habe ich noch den... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.61 | same | 07:57-08:34 documentation: Dann lässt mir der Violette Machio den Satz. Ja, das ist gut. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.68 | same | 07:28-08:04 documentation: Gut. Diese Angen und die grünen Markierung sind jetzt klar. Für diese violetten Zeilen habe ich noch den Wunsch, den ich am Anfang anders getroffen habe. Die Farbe meine ich... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.45 | broken | Prüfen (knapp unter Schwelle): Score 0.45 für 'Relevante Angabe verschweigen' liegt zwischen 0.35 und der Schwelle 0.50. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.19 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.19 ('Relevante Angabe verschweigen') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.69 | same | 00:00-00:49 disclosure: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.65 | same | 00:00-00:50 disclosure: Guten Tag, Frau Ott, das ist Daniela Gott. Sie haben wegen dem Haushaltskonto von Ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist für zwei Monate im Ausland. Ich habe i... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_general_en` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_en - champion

| metric | champion | kev_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.71 | -0.153 | [-0.331, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.79 | -0.112 | [-0.291, +0.035] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_en - champion

| metric | champion | kev_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.66 | -0.207 | [-0.368, -0.082] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.232 | [-0.467, -0.020] | **real**: champion better |
| false_alarm_rate | 14% | 68% | +55pp | [+23pp, +81pp] | **real**: champion better |
| miss_rate | 15% | 23% | +8pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 79% | 48% | -31pp | [-52pp, -12pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.54 | -0.311 | [-0.477, -0.139] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 14 vs only-kev_general_en 0, p=0.0001; 3-class only-champion 17 vs only-kev_general_en 2, p=0.0007.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_en - champion

| metric | champion | kev_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.67 | -0.173 | [-0.407, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.65 | -0.020 | [-0.350, +0.315] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [+0pp, +54pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-25pp, +15pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.72 | -0.112 | [-0.250, +0.025] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_general_en 3, p=0.146; 3-class only-champion 9 vs only-kev_general_en 7, p=0.8036.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_en - champion

| metric | champion | kev_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.415, -0.050] | **real**: champion better |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.499, +0.033] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+8pp, +56pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-29pp, +2pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.131 | [-0.256, -0.016] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_general_en 2, p=0.0654; 3-class only-champion 10 vs only-kev_general_en 4, p=0.1796.

Flips (cv, 22 calls):

| call | expected | champion | kev_general_en | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.48 | broken | 00:27-00:28 access: Gut, wir kennen diese zwei Sachen. Für das Passwort sagen Sie mir bitte nur, - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.18 | broken | 03:57-03:58 splitting: Wir haben also mehrere Zahlungen für verschiedene, echte Hallenwöchungen gemacht. - keywords: Stichwort K07 «mehrere Zahlungen» (Aufteilen) | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.20 | broken | 03:59-04:00 splitting: Wir haben also mehrere Zahlungen für verschiedene echte Hallenwächende gemacht. - keywords: Stichwort K07 «mehrere Zahlungen» (Aufteilen) | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.90/0.28 | broken | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.23 | broken | 02:48-02:54 documentation: Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - Kein Alarm: höchster Score 0.23 ('Relevante Angabe verschweigen') liegt unter ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C01-K3 | no_alert | no_alert | alarm | 0.00/0.39 | broken | Alarm: Score 0.39 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | alarm | 0.00/0.40 | broken | Alarm: Score 0.40 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.44 | broken | Alarm: Score 0.44 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.45 | broken | Alarm: Score 0.45 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.23 | broken | Prüfen (knapp unter Schwelle): Score 0.23 für 'Insiderhandel' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.29 | broken | Alarm: Score 0.29 für 'Insiderhandel' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.42 | broken | Alarm: Score 0.42 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.39 | broken | Alarm: Score 0.39 für 'Insiderhandel' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.35 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.35 für 'Insiderhandel' >= Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.40 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.40 für 'Insiderhandel' >= Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.81 | same | 07:44-08:25 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machiat den Satz aus dem Doss... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.75 | same | 07:57-08:34 documentation: Dann lässt mir der Violette Machio den Satz. Ja, das ist gut. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.77 | same | 07:45-08:27 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machiat den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.58 | broken | 07:52-08:30 documentation: Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machio den Satz aus dem Dossier heraus. Ich will, dass die Finanzierung das Ganze ausmac... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.36 | same | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.71 | same | 00:00-00:49 splitting: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr a... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.67 | same | 03:04-03:53 disclosure: Gut, wenn ich aus meinem Konto bezahle, möchte ich wenigstens nicht die gleiche Rechnung zweimal bezahlen. Wir haben vereinbart, dass ich zuerst mit Ihnen reden und nicht selbe... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_facts` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.86 | -0.010 | [-0.206, +0.144] | no detectable difference |
| alarm AUC | 0.90 | 0.97 | +0.061 | [-0.019, +0.179] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.044 | [-0.252, +0.104] | no detectable difference |
| alarm_f1 | 0.86 | 0.69 | -0.170 | [-0.513, +0.069] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [-6pp, +41pp] | no detectable difference |
| accuracy | 79% | 69% | -10pp | [-36pp, +9pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | -0.009 | [-0.172, +0.132] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts 4, p=1.0; 3-class only-champion 10 vs only-kev_facts 5, p=0.3018.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.022 | [-0.213, +0.114] | no detectable difference |
| alarm_f1 | 0.67 | 0.69 | +0.021 | [-0.280, +0.318] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-7pp, +32pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [-24pp, +21pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.011 | [-0.136, +0.141] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_facts 4, p=1.0; 3-class only-champion 7 vs only-kev_facts 7, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.163 | [-0.426, +0.033] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.529, +0.042] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+4pp, +59pp] | **real**: champion better |
| accuracy | 79% | 69% | -10pp | [-34pp, +8pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.086 | [-0.250, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_facts 4, p=0.2668; 3-class only-champion 9 vs only-kev_facts 4, p=0.2668.

Flips (cv, 15 calls):

| call | expected | champion | kev_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `qwen_general` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.72 | -0.144 | [-0.301, +0.011] | no detectable difference |
| alarm AUC | 0.90 | 0.73 | -0.171 | [-0.303, -0.050] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.75 | -0.113 | [-0.277, +0.037] | no detectable difference |
| alarm_f1 | 0.86 | 0.63 | -0.230 | [-0.421, -0.069] | **real**: champion better |
| false_alarm_rate | 14% | 64% | +50pp | [+17pp, +80pp] | **real**: champion better |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 54% | -25pp | [-45pp, -7pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.64 | -0.211 | [-0.371, -0.041] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 12 vs only-qwen_general 3, p=0.0352; 3-class only-champion 15 vs only-qwen_general 3, p=0.0075.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.62 | -0.215 | [-0.433, -0.029] | **real**: champion better |
| alarm_f1 | 0.67 | 0.60 | -0.067 | [-0.325, +0.214] | no detectable difference |
| false_alarm_rate | 14% | 32% | +18pp | [-14pp, +50pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [-4pp, +50pp] | no detectable difference |
| accuracy | 69% | 58% | -10pp | [-34pp, +12pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.63 | -0.206 | [-0.395, -0.027] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 14 vs only-qwen_general 4, p=0.0309; 3-class only-champion 12 vs only-qwen_general 7, p=0.3593.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.61 | -0.254 | [-0.452, -0.106] | **real**: champion better |
| alarm_f1 | 0.86 | 0.60 | -0.257 | [-0.500, -0.063] | **real**: champion better |
| false_alarm_rate | 14% | 27% | +14pp | [-18pp, +46pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+9pp, +55pp] | **real**: champion better |
| accuracy | 79% | 58% | -21pp | [-41pp, -4pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.63 | -0.222 | [-0.389, -0.071] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general 2, p=0.0074; 3-class only-champion 14 vs only-qwen_general 4, p=0.0309.

Flips (cv, 22 calls):

| call | expected | champion | qwen_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K1 | no_alert | no_alert | alarm | 0.04/0.86 | broken | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.98 | broken | Alarm: Score 0.98 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.94 | broken | 01:51-01:52 splitting: Und im Mail hat jemand geschrieben, ich solle zum Gerätewechsel die Prüfung umgehen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.94 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.11 | broken | Prüfen (knapp unter Schwelle): Score 0.11 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.10 | broken | Prüfen (knapp unter Schwelle): Score 0.10 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.21 | broken | Alarm: Score 0.21 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.07 | broken | Prüfen (knapp unter Schwelle): Score 0.07 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.46 | broken | Alarm: Score 0.46 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.36 | broken | Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.29 | broken | Alarm: Score 0.29 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.21 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.21 für 'Relevante Angabe vers... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.01 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.01 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.10 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Prüfen (knapp unter Schwelle): Score 0.10 für 'Releva... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/1.00 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.99 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.99 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Alarm: Score 0.99 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.95 | broken | Alarm: Score 0.95 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.88 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Alarm: Score 0.88 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.98 | same | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.26 | fixed | Alarm: Score 0.26 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.53 | fixed | Alarm: Score 0.53 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `facts_only` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.89 | +0.021 | [+0.000, +0.064] | no detectable difference |
| alarm AUC | 0.90 | 0.92 | +0.011 | [+0.000, +0.042] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 0, p=1.0; 3-class only-champion 0 vs only-facts_only 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.86 | +0.023 | [+0.000, +0.079] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [-0.118, +0.149] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 15% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [-7pp, +7pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 1, p=1.0; 3-class only-champion 1 vs only-facts_only 1, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 0, p=1.0; 3-class only-champion 0 vs only-facts_only 0, p=1.0.

No call changes its label (cv).

## `qwen_general_en` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general_en - champion

| metric | champion | qwen_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.68 | -0.184 | [-0.330, -0.052] | **real**: champion better |
| alarm AUC | 0.90 | 0.73 | -0.172 | [-0.312, -0.054] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_en - champion

| metric | champion | qwen_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.184 | [-0.378, -0.021] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.232 | [-0.467, -0.056] | **real**: champion better |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +68pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [-8pp, +33pp] | no detectable difference |
| accuracy | 79% | 54% | -25pp | [-48pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.62 | -0.239 | [-0.412, -0.029] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 14 vs only-qwen_general_en 3, p=0.0127; 3-class only-champion 17 vs only-qwen_general_en 5, p=0.0169.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_en - champion

| metric | champion | qwen_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.61 | -0.231 | [-0.467, -0.047] | **real**: champion better |
| alarm_f1 | 0.67 | 0.56 | -0.111 | [-0.436, +0.214] | no detectable difference |
| false_alarm_rate | 14% | 27% | +14pp | [-18pp, +46pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [+0pp, +55pp] | no detectable difference |
| accuracy | 69% | 54% | -15pp | [-37pp, +7pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.63 | -0.203 | [-0.379, -0.027] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_en 3, p=0.0213; 3-class only-champion 13 vs only-qwen_general_en 6, p=0.1671.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_en - champion

| metric | champion | qwen_general_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.62 | -0.238 | [-0.429, -0.096] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.242 | [-0.514, -0.039] | **real**: champion better |
| false_alarm_rate | 14% | 32% | +18pp | [-14pp, +50pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-43pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.63 | -0.226 | [-0.382, -0.070] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_en 2, p=0.0074; 3-class only-champion 15 vs only-qwen_general_en 4, p=0.0192.

Flips (cv, 24 calls):

| call | expected | champion | qwen_general_en | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K1 | no_alert | no_alert | alarm | 0.04/0.70 | broken | Alarm: Score 0.70 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.71 | broken | Alarm: Score 0.71 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.92 | broken | 01:51-01:52 splitting: Und im Mail hat jemand geschrieben, ich solle zum Gerätewechsel die Prüfung umgehen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.88 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.08 | broken | 03:08-03:09 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März passiert sei. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.56 | broken | Alarm: Score 0.56 für 'Relevante Angabe verschweigen' >= Schwelle 0.50 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.54 | broken | Alarm: Score 0.54 für 'Relevante Angabe verschweigen' >= Schwelle 0.50 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.31 | broken | Alarm: Score 0.31 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.48 | broken | Alarm: Score 0.48 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K3 | alarm | alarm | no_alert | 0.97/0.12 | broken | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.09 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.09 ('Relevante Angabe verschweigen') li... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.04 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.04 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.40 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.40 für 'Relevante Angabe vers... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.07 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Prüfen (knapp unter Schwelle): Score 0.07 für 'Releva... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/1.00 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/1.00 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/1.00 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Alarm: Score 1.00 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.97 | broken | Alarm: Score 0.97 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.07 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.03 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.85 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Alarm: Score 0.85 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.97 | same | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.36 | fixed | Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_general_oracle` vs `champion` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_oracle - champion

| metric | champion | kev_general_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.89 | +0.022 | [-0.143, +0.154] | no detectable difference |
| alarm AUC | 0.90 | 0.93 | +0.021 | [-0.095, +0.121] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_oracle - champion

| metric | champion | kev_general_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.80 | -0.063 | [-0.248, +0.106] | no detectable difference |
| alarm_f1 | 0.86 | 0.80 | -0.057 | [-0.194, +0.059] | no detectable difference |
| false_alarm_rate | 14% | 45% | +32pp | [-8pp, +72pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-33pp, +17pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-41pp, +8pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.121 | [-0.348, +0.088] | no detectable difference |

McNemar exact (calls): flag correct only-champion 11 vs only-kev_general_oracle 6, p=0.3323; 3-class only-champion 13 vs only-kev_general_oracle 5, p=0.0963.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_oracle - champion

| metric | champion | kev_general_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.76 | -0.078 | [-0.308, +0.092] | no detectable difference |
| alarm_f1 | 0.67 | 0.79 | +0.121 | [-0.172, +0.404] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-5pp, +46pp] | no detectable difference |
| accuracy | 69% | 73% | +4pp | [-17pp, +26pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.81 | -0.028 | [-0.181, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_general_oracle 4, p=0.7539; 3-class only-champion 6 vs only-kev_general_oracle 8, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_oracle - champion

| metric | champion | kev_general_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.080 | [-0.256, +0.066] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.267, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-31pp, +25pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-23pp, +10pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.054 | [-0.207, +0.107] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_general_oracle 3, p=0.5078; 3-class only-champion 6 vs only-kev_general_oracle 3, p=0.5078.

Flips (cv, 20 calls):

| call | expected | champion | kev_general_oracle | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.43 | broken | Prüfen (knapp unter Schwelle): Score 0.43 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.35 | broken | 00:29-00:30 access: Guet, mir trenned die zwei Sache. Für s Passwort säged Sie mir bitte nume, öb Sie sich dra erinnered. De Wert selber bliibt bi Ihnen. - keywords: Stichwort K10 «Passwort» (Zugangsw... | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.35 | broken | 00:29-00:30 access: Guet, mir trenned die zwei Sache. Für s Passwort säged Sie mir bitte nume, öb Sie sich dra erinnered. De Wert selber bliibt bi Ihnen. - keywords: Stichwort K10 «Passwort» (Zugangsw... | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Insiderhandel' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Insiderhandel' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.43 | fixed | Prüfen (knapp unter Schwelle): Score 0.43 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.40 | fixed | Prüfen (knapp unter Schwelle): Score 0.40 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K3 | no_alert | no_alert | alarm | 0.00/0.57 | broken | 00:49-01:49 access: Danke. Bitte lönd d Zahl bi Ihnen und beschriibed nume de Text rund ums Feld. Was het Sie am Schritt irritiert? De Pfeil. Ich ha erwartet, dass ich uf em Telefon öppis bestätige, a... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.00/0.56 | broken | 00:49-01:49 access: Danke. Bitte lönd d Zahl bi Ihnen und beschriibed nume de Text rund ums Feld. Was het Sie am Schritt irritiert? De Pfeil. Ich ha erwartet, dass ich uf em Telefon öppis bestätige, a... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.09 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.09 ('Insiderhan... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.10 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.10 ('Insiderhan... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.69 | same | 00:00-01:00 disclosure: Guete Morge Frau Frei, da isch d Marion Gloor. Sie händ wäge de laufende Wohnkoste vo Ihrer Mueter um en Rückruf bätte. Ja. Sie isch zurziit im Spital, und ich ordne mit ihr d ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.42 | broken | Prüfen (knapp unter Schwelle): Score 0.42 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.34 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.34 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.34 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.34 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.59 | same | 00:00-01:00 disclosure: Guete Tag Frau Ott, da isch d Daniela Vogt. Sie händ wäge em Haushaltskonto vo Ihrer Schwester um en Rückruf gwünscht. Ja. Si isch für zwei Mönet im Uusland. Ich ha ihr aabote,... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.58 | same | 00:00-01:00 disclosure: Guete Tag Frau Ott, da isch d Daniela Vogt. Sie händ wäge em Haushaltskonto vo Ihrer Schwester um en Rückruf gwünscht. Ja. Si isch für zwei Mönet im Uusland. Ich ha ihr aabote,... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.41 | fixed | Prüfen (knapp unter Schwelle): Score 0.41 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.39 | fixed | Prüfen (knapp unter Schwelle): Score 0.39 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_general_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_alone - champion

| metric | champion | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.79 | -0.080 | [-0.241, +0.057] | no detectable difference |
| alarm AUC | 0.90 | 0.81 | -0.096 | [-0.242, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_alone - champion

| metric | champion | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.63 | -0.229 | [-0.393, -0.111] | **real**: champion better |
| alarm_f1 | 0.86 | 0.74 | -0.113 | [-0.350, +0.063] | no detectable difference |
| false_alarm_rate | 14% | 68% | +55pp | [+30pp, +75pp] | **real**: champion better |
| miss_rate | 15% | 27% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 79% | 50% | -29pp | [-50pp, -10pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.52 | -0.330 | [-0.486, -0.191] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 15 vs only-kev_general_alone 0, p=0.0001; 3-class only-champion 17 vs only-kev_general_alone 3, p=0.0026.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_alone - champion

| metric | champion | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.62 | -0.218 | [-0.456, -0.041] | **real**: champion better |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [-0.374, +0.335] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [-20pp, +38pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [+0pp, +54pp] | no detectable difference |
| accuracy | 69% | 62% | -6pp | [-29pp, +15pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.66 | -0.180 | [-0.354, -0.022] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 12 vs only-kev_general_alone 3, p=0.0352; 3-class only-champion 10 vs only-kev_general_alone 7, p=0.6291.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_alone - champion

| metric | champion | kev_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.181 | [-0.404, -0.031] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.236 | [-0.511, -0.051] | **real**: champion better |
| false_alarm_rate | 14% | 14% | +0pp | [-25pp, +20pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 62% | -17pp | [-33pp, -4pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.135 | [-0.294, +0.006] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_general_alone 2, p=0.0654; 3-class only-champion 10 vs only-kev_general_alone 2, p=0.0386.

Flips (cv, 22 calls):

| call | expected | champion | kev_general_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.41 | broken | Prüfen (knapp unter Schwelle): Score 0.41 für 'Relevante Angabe verschweigen' liegt zwischen 0.35 und der Schwelle 0.50. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.57 | broken | 01:42-02:15 access: Ich habe also vermutlich das falsche Blatt herausgenommen. Und im Mail hat jemand geschrieben, ich solle zum Gerätewechsel die Prüfung umgehen. Das habe ich nicht gemacht. Die Abse... | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.45 | broken | Prüfen (knapp unter Schwelle): Score 0.45 für 'Zugangsinformation preisgegeben' liegt zwischen 0.35 und der Schwelle 0.50. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | alarm | 0.02/0.59 | broken | 00:42-01:25 access: Richtig. Ich will auch gar nicht über ihn persönlich wissen. Ich habe das Protokoll der Wahl und das Formular zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingereicht. ... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | alarm | 0.03/0.53 | broken | 00:34-01:13 access: Es geht ausschliesslich um das Vereinskonto, nicht um ein persönliches Konto des Vorgängers. Richtig? Richtig. Ich will auch gar nichts über ihn persönlich wissen. Ich habe das Pro... | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.90/0.24 | broken | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.29 | broken | 02:48-02:54 documentation: Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - Kein Alarm: höchster Score 0.29 ('Relevante Angabe verschweigen') liegt unter ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.22 | broken | Prüfen (knapp unter Schwelle): Score 0.22 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | review | 0.00/0.22 | broken | Prüfen (knapp unter Schwelle): Score 0.22 für 'Insiderhandel' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.00/0.34 | broken | Prüfen (knapp unter Schwelle): Score 0.34 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | review | 0.00/0.32 | broken | Prüfen (knapp unter Schwelle): Score 0.32 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.39 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.39 für 'Insiderhandel' >= Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.45 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.45 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.61 | same | 07:22-08:03 documentation: Ich habe einen unvollständigen Entwurf, nur damit der Frühe noch da ist. Gut, die O-Ange und die grüne Markierung sind jetzt klar. Für die violetten Zeilen habe ich noch den... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.61 | same | 07:57-08:34 documentation: Dann lässt mir der Violette Machio den Satz. Ja, das ist gut. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.68 | same | 07:28-08:04 documentation: Gut. Diese Angen und die grünen Markierung sind jetzt klar. Für diese violetten Zeilen habe ich noch den Wunsch, den ich am Anfang anders getroffen habe. Die Farbe meine ich... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.45 | broken | Prüfen (knapp unter Schwelle): Score 0.45 für 'Relevante Angabe verschweigen' liegt zwischen 0.35 und der Schwelle 0.50. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.19 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.19 ('Relevante Angabe verschweigen') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.69 | same | 00:00-00:49 disclosure: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.65 | same | 00:00-00:50 disclosure: Guten Tag, Frau Ott, das ist Daniela Gott. Sie haben wegen dem Haushaltskonto von Ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist für zwei Monate im Ausland. Ich habe i... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_general_en_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_en_alone - champion

| metric | champion | kev_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.71 | -0.155 | [-0.333, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.79 | -0.113 | [-0.295, +0.034] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_en_alone - champion

| metric | champion | kev_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.66 | -0.207 | [-0.368, -0.082] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.232 | [-0.467, -0.020] | **real**: champion better |
| false_alarm_rate | 14% | 68% | +55pp | [+23pp, +81pp] | **real**: champion better |
| miss_rate | 15% | 23% | +8pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 79% | 48% | -31pp | [-52pp, -12pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.54 | -0.311 | [-0.477, -0.139] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 14 vs only-kev_general_en_alone 0, p=0.0001; 3-class only-champion 17 vs only-kev_general_en_alone 2, p=0.0007.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_en_alone - champion

| metric | champion | kev_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.67 | -0.173 | [-0.407, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.65 | -0.020 | [-0.350, +0.315] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [+0pp, +54pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-25pp, +15pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.72 | -0.112 | [-0.250, +0.025] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_general_en_alone 3, p=0.146; 3-class only-champion 9 vs only-kev_general_en_alone 7, p=0.8036.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_en_alone - champion

| metric | champion | kev_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.415, -0.050] | **real**: champion better |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.499, +0.033] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+8pp, +56pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-29pp, +2pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.131 | [-0.256, -0.016] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_general_en_alone 2, p=0.0654; 3-class only-champion 10 vs only-kev_general_en_alone 4, p=0.1796.

Flips (cv, 22 calls):

| call | expected | champion | kev_general_en_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.49 | broken | Prüfen (knapp unter Schwelle): Score 0.49 für 'Zugangsinformation preisgegeben' liegt zwischen 0.45 und der Schwelle 0.60. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.18 | broken | Prüfen (knapp unter Schwelle): Score 0.18 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.20 | broken | Prüfen (knapp unter Schwelle): Score 0.20 für 'Zugangsinformation preisgegeben' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.90/0.28 | broken | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.23 | broken | 02:48-02:54 documentation: Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - Kein Alarm: höchster Score 0.23 ('Relevante Angabe verschweigen') liegt unter ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C01-K3 | no_alert | no_alert | alarm | 0.00/0.39 | broken | Alarm: Score 0.39 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | alarm | 0.00/0.40 | broken | Alarm: Score 0.40 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.44 | broken | Alarm: Score 0.44 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.45 | broken | Alarm: Score 0.45 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.23 | broken | Prüfen (knapp unter Schwelle): Score 0.23 für 'Insiderhandel' liegt zwischen 0.10 und der Schwelle 0.25. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.29 | broken | Alarm: Score 0.29 für 'Insiderhandel' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.42 | broken | Alarm: Score 0.42 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.39 | broken | Alarm: Score 0.39 für 'Insiderhandel' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.35 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.35 für 'Insiderhandel' >= Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.40 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.40 für 'Insiderhandel' >= Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.81 | same | 07:44-08:25 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machiat den Satz aus dem Doss... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.75 | same | 07:57-08:34 documentation: Dann lässt mir der Violette Machio den Satz. Ja, das ist gut. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.77 | same | 07:45-08:27 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machiat den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.58 | broken | 07:52-08:30 documentation: Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machio den Satz aus dem Dossier heraus. Ich will, dass die Finanzierung das Ganze ausmac... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.36 | same | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.71 | same | 00:00-00:49 splitting: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr a... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.67 | same | 03:04-03:53 disclosure: Gut, wenn ich aus meinem Konto bezahle, möchte ich wenigstens nicht die gleiche Rechnung zweimal bezahlen. Wir haben vereinbart, dass ich zuerst mit Ihnen reden und nicht selbe... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_facts_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_alone - champion

| metric | champion | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.91 | +0.043 | [-0.134, +0.215] | no detectable difference |
| alarm AUC | 0.90 | 0.98 | +0.071 | [-0.019, +0.213] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_alone - champion

| metric | champion | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.044 | [-0.252, +0.104] | no detectable difference |
| alarm_f1 | 0.86 | 0.76 | -0.092 | [-0.360, +0.111] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [-6pp, +41pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-31pp, +12pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | -0.009 | [-0.172, +0.132] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts_alone 4, p=1.0; 3-class only-champion 8 vs only-kev_facts_alone 5, p=0.5811.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_alone - champion

| metric | champion | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.022 | [-0.213, +0.114] | no detectable difference |
| alarm_f1 | 0.67 | 0.76 | +0.098 | [-0.095, +0.333] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-7pp, +32pp] | no detectable difference |
| accuracy | 69% | 73% | +4pp | [-18pp, +24pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.011 | [-0.136, +0.141] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_facts_alone 4, p=1.0; 3-class only-champion 5 vs only-kev_facts_alone 7, p=0.7744.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_alone - champion

| metric | champion | kev_facts_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.163 | [-0.426, +0.033] | no detectable difference |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.376, +0.076] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+4pp, +59pp] | **real**: champion better |
| accuracy | 79% | 73% | -6pp | [-28pp, +11pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.086 | [-0.250, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_facts_alone 4, p=0.2668; 3-class only-champion 7 vs only-kev_facts_alone 4, p=0.5488.

Flips (cv, 13 calls):

| call | expected | champion | kev_facts_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.12 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Prüfen (knapp unter Schwelle): Score 0.12 für 'Zugangsinformation preisgegeben' liegt zwischen 0.05 und... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.12 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - Prüfen (knapp unt... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.93/0.04 | broken | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.80/0.06 | broken | 01:35-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.99 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.99 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.04 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `qwen_general_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general_alone - champion

| metric | champion | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.72 | -0.149 | [-0.312, +0.010] | no detectable difference |
| alarm AUC | 0.90 | 0.73 | -0.172 | [-0.309, -0.048] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_alone - champion

| metric | champion | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.75 | -0.113 | [-0.277, +0.037] | no detectable difference |
| alarm_f1 | 0.86 | 0.63 | -0.230 | [-0.421, -0.069] | **real**: champion better |
| false_alarm_rate | 14% | 64% | +50pp | [+17pp, +80pp] | **real**: champion better |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 54% | -25pp | [-45pp, -7pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.64 | -0.211 | [-0.371, -0.041] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 12 vs only-qwen_general_alone 3, p=0.0352; 3-class only-champion 15 vs only-qwen_general_alone 3, p=0.0075.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_alone - champion

| metric | champion | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.62 | -0.215 | [-0.433, -0.029] | **real**: champion better |
| alarm_f1 | 0.67 | 0.60 | -0.067 | [-0.325, +0.214] | no detectable difference |
| false_alarm_rate | 14% | 32% | +18pp | [-14pp, +50pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [-4pp, +50pp] | no detectable difference |
| accuracy | 69% | 58% | -10pp | [-34pp, +12pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.63 | -0.206 | [-0.395, -0.027] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 14 vs only-qwen_general_alone 4, p=0.0309; 3-class only-champion 12 vs only-qwen_general_alone 7, p=0.3593.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_alone - champion

| metric | champion | qwen_general_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.61 | -0.254 | [-0.452, -0.106] | **real**: champion better |
| alarm_f1 | 0.86 | 0.60 | -0.257 | [-0.500, -0.063] | **real**: champion better |
| false_alarm_rate | 14% | 27% | +14pp | [-18pp, +46pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+9pp, +55pp] | **real**: champion better |
| accuracy | 79% | 58% | -21pp | [-41pp, -4pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.63 | -0.222 | [-0.389, -0.071] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_alone 2, p=0.0074; 3-class only-champion 14 vs only-qwen_general_alone 4, p=0.0309.

Flips (cv, 22 calls):

| call | expected | champion | qwen_general_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K1 | no_alert | no_alert | alarm | 0.04/0.86 | broken | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.98 | broken | Alarm: Score 0.98 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.97 | broken | Alarm: Score 0.97 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/1.00 | broken | Alarm: Score 1.00 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.11 | broken | Prüfen (knapp unter Schwelle): Score 0.11 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.10 | broken | Prüfen (knapp unter Schwelle): Score 0.10 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.21 | broken | Alarm: Score 0.21 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.07 | broken | Prüfen (knapp unter Schwelle): Score 0.07 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.46 | broken | Alarm: Score 0.46 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C08-K3 | no_alert | no_alert | alarm | 0.00/0.36 | broken | Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | alarm | 0.00/0.29 | broken | Alarm: Score 0.29 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.21 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.21 für 'Relevante Angabe vers... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.01 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.01 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.10 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Prüfen (knapp unter Schwelle): Score 0.10 für 'Releva... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/1.00 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.99 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.99 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Alarm: Score 0.99 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.95 | broken | Alarm: Score 0.95 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.88 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Alarm: Score 0.88 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.98 | same | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.26 | fixed | Alarm: Score 0.26 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.53 | fixed | Alarm: Score 0.53 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `qwen_general_en_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general_en_alone - champion

| metric | champion | qwen_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.69 | -0.172 | [-0.321, -0.037] | **real**: champion better |
| alarm AUC | 0.90 | 0.74 | -0.160 | [-0.302, -0.042] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_en_alone - champion

| metric | champion | qwen_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.184 | [-0.378, -0.021] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.232 | [-0.467, -0.056] | **real**: champion better |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +68pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [-8pp, +33pp] | no detectable difference |
| accuracy | 79% | 54% | -25pp | [-48pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.62 | -0.239 | [-0.412, -0.029] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 14 vs only-qwen_general_en_alone 3, p=0.0127; 3-class only-champion 17 vs only-qwen_general_en_alone 5, p=0.0169.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_en_alone - champion

| metric | champion | qwen_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.61 | -0.231 | [-0.467, -0.047] | **real**: champion better |
| alarm_f1 | 0.67 | 0.59 | -0.072 | [-0.376, +0.232] | no detectable difference |
| false_alarm_rate | 14% | 27% | +14pp | [-18pp, +46pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [+0pp, +55pp] | no detectable difference |
| accuracy | 69% | 56% | -12pp | [-36pp, +9pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.63 | -0.203 | [-0.379, -0.027] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_en_alone 3, p=0.0213; 3-class only-champion 13 vs only-qwen_general_en_alone 7, p=0.2632.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_en_alone - champion

| metric | champion | qwen_general_en_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.62 | -0.238 | [-0.429, -0.096] | **real**: champion better |
| alarm_f1 | 0.86 | 0.62 | -0.242 | [-0.514, -0.039] | **real**: champion better |
| false_alarm_rate | 14% | 32% | +18pp | [-14pp, +50pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-43pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.63 | -0.226 | [-0.382, -0.070] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_en_alone 2, p=0.0074; 3-class only-champion 15 vs only-qwen_general_en_alone 4, p=0.0192.

Flips (cv, 24 calls):

| call | expected | champion | qwen_general_en_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K1 | no_alert | no_alert | alarm | 0.04/0.70 | broken | Alarm: Score 0.70 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.71 | broken | Alarm: Score 0.71 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.95 | broken | Alarm: Score 0.95 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.94 | broken | Alarm: Score 0.94 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.06 | broken | Prüfen (knapp unter Schwelle): Score 0.06 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.56 | broken | Alarm: Score 0.56 für 'Relevante Angabe verschweigen' >= Schwelle 0.50 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.54 | broken | Alarm: Score 0.54 für 'Relevante Angabe verschweigen' >= Schwelle 0.50 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | alarm | 0.00/0.31 | broken | Alarm: Score 0.31 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.48 | broken | Alarm: Score 0.48 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K3 | alarm | alarm | no_alert | 0.97/0.12 | broken | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.09 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.09 ('Relevante Angabe verschweigen') li... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.04 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.04 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.40 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.40 für 'Relevante Angabe vers... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.07 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Prüfen (knapp unter Schwelle): Score 0.07 für 'Releva... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/1.00 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/1.00 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/1.00 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Alarm: Score 1.00 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.97 | broken | Alarm: Score 0.97 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.07 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.03 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.03 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.85 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Alarm: Score 0.85 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.97 | same | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.36 | fixed | Alarm: Score 0.36 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_general_oracle_alone` vs `champion` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_oracle_alone - champion

| metric | champion | kev_general_oracle_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.89 | +0.022 | [-0.143, +0.154] | no detectable difference |
| alarm AUC | 0.90 | 0.93 | +0.021 | [-0.095, +0.121] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_oracle_alone - champion

| metric | champion | kev_general_oracle_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.80 | -0.063 | [-0.248, +0.106] | no detectable difference |
| alarm_f1 | 0.86 | 0.80 | -0.057 | [-0.194, +0.059] | no detectable difference |
| false_alarm_rate | 14% | 45% | +32pp | [-8pp, +72pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-33pp, +17pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-41pp, +8pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.121 | [-0.348, +0.088] | no detectable difference |

McNemar exact (calls): flag correct only-champion 11 vs only-kev_general_oracle_alone 6, p=0.3323; 3-class only-champion 13 vs only-kev_general_oracle_alone 5, p=0.0963.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_oracle_alone - champion

| metric | champion | kev_general_oracle_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.76 | -0.078 | [-0.308, +0.092] | no detectable difference |
| alarm_f1 | 0.67 | 0.79 | +0.121 | [-0.172, +0.404] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-5pp, +46pp] | no detectable difference |
| accuracy | 69% | 73% | +4pp | [-17pp, +26pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.81 | -0.028 | [-0.181, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_general_oracle_alone 4, p=0.7539; 3-class only-champion 6 vs only-kev_general_oracle_alone 8, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_oracle_alone - champion

| metric | champion | kev_general_oracle_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.080 | [-0.256, +0.066] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.267, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-31pp, +25pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-23pp, +10pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.054 | [-0.207, +0.107] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_general_oracle_alone 3, p=0.5078; 3-class only-champion 6 vs only-kev_general_oracle_alone 3, p=0.5078.

Flips (cv, 20 calls):

| call | expected | champion | kev_general_oracle_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D01-K2 | no_alert | no_alert | review | 0.00/0.43 | broken | Prüfen (knapp unter Schwelle): Score 0.43 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K1 | no_alert | no_alert | review | 0.03/0.35 | broken | Prüfen (knapp unter Schwelle): Score 0.35 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | review | 0.03/0.35 | broken | Prüfen (knapp unter Schwelle): Score 0.35 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C05-K3 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Insiderhandel' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C05-K4 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Insiderhandel' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.43 | fixed | Prüfen (knapp unter Schwelle): Score 0.43 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.40 | fixed | Prüfen (knapp unter Schwelle): Score 0.40 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K3 | no_alert | no_alert | alarm | 0.00/0.57 | broken | 00:49-01:49 access: Danke. Bitte lönd d Zahl bi Ihnen und beschriibed nume de Text rund ums Feld. Was het Sie am Schritt irritiert? De Pfeil. Ich ha erwartet, dass ich uf em Telefon öppis bestätige, a... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | alarm | 0.00/0.56 | broken | 00:49-01:49 access: Danke. Bitte lönd d Zahl bi Ihnen und beschriibed nume de Text rund ums Feld. Was het Sie am Schritt irritiert? De Pfeil. Ich ha erwartet, dass ich uf em Telefon öppis bestätige, a... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.08 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.08 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.09 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.09 ('Insiderhan... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.69 | same | 00:00-01:00 disclosure: Guete Morge Frau Frei, da isch d Marion Gloor. Sie händ wäge de laufende Wohnkoste vo Ihrer Mueter um en Rückruf bätte. Ja. Sie isch zurziit im Spital, und ich ordne mit ihr d ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.42 | broken | Prüfen (knapp unter Schwelle): Score 0.42 für 'Relevante Angabe verschweigen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.34 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.34 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.34 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.34 ('Relevante Angabe verschweigen') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.59 | same | 00:00-01:00 disclosure: Guete Tag Frau Ott, da isch d Daniela Vogt. Sie händ wäge em Haushaltskonto vo Ihrer Schwester um en Rückruf gwünscht. Ja. Si isch für zwei Mönet im Uusland. Ich ha ihr aabote,... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.58 | same | 00:00-01:00 disclosure: Guete Tag Frau Ott, da isch d Daniela Vogt. Sie händ wäge em Haushaltskonto vo Ihrer Schwester um en Rückruf gwünscht. Ja. Si isch für zwei Mönet im Uusland. Ich ha ihr aabote,... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.41 | fixed | Prüfen (knapp unter Schwelle): Score 0.41 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.39 | fixed | Prüfen (knapp unter Schwelle): Score 0.39 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.30 und der Schwelle 0.45. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_facts_choice` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_choice - champion

| metric | champion | kev_facts_choice | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.85 | -0.016 | [-0.167, +0.096] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [-0.078, +0.069] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_choice - champion

| metric | champion | kev_facts_choice | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.235, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.71 | -0.151 | [-0.436, +0.039] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [-12pp, +28pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +30pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-39pp, +0pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.217, +0.010] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts_choice 1, p=0.2188; 3-class only-champion 10 vs only-kev_facts_choice 2, p=0.0386.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_choice - champion

| metric | champion | kev_facts_choice | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.78 | -0.065 | [-0.219, +0.043] | no detectable difference |
| alarm_f1 | 0.67 | 0.71 | +0.039 | [-0.167, +0.267] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [-12pp, +28pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 69% | 62% | -6pp | [-27pp, +10pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.77 | -0.061 | [-0.205, +0.045] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts_choice 2, p=0.4531; 3-class only-champion 7 vs only-kev_facts_choice 4, p=0.5488.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_choice - champion

| metric | champion | kev_facts_choice | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.163 | [-0.425, +0.013] | no detectable difference |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.376, +0.076] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+8pp, +57pp] | **real**: champion better |
| accuracy | 79% | 75% | -4pp | [-25pp, +13pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.086 | [-0.238, +0.061] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-kev_facts_choice 3, p=0.2266; 3-class only-champion 6 vs only-kev_facts_choice 4, p=0.7539.

Flips (cv, 13 calls):

| call | expected | champion | kev_facts_choice | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.13 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.13 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.08 | broken | 00:49-00:50 disclosure: Richtig. Ich will auch gar nicht über ihn persönlich wissen. Ich habe das Protokoll der Wahl und das Formular zur Vollmacht von mir. - keywords: Stichwort K11 «Vollmacht» (Drit... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.07 | broken | 00:50-00:51 disclosure: Ich habe das Protokoll der Wahl und das Formular zur Vollmacht von mir. - keywords: Stichwort K11 «Vollmacht» (Drittperson und Berechtigung) | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.07 | same | 01:02-01:03 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.09 | same | 01:35-01:36 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.98 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.98 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.50/0.08 | broken | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.05 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.05 ('Relevante Angabe verschweigen') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.50 | same | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.01 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `kev_facts_band` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_band - champion

| metric | champion | kev_facts_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.86 | -0.010 | [-0.199, +0.139] | no detectable difference |
| alarm AUC | 0.90 | 0.94 | +0.031 | [-0.051, +0.133] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_band - champion

| metric | champion | kev_facts_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.007 | [-0.149, +0.130] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.513, +0.053] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-8pp, +29pp] | no detectable difference |
| accuracy | 79% | 69% | -10pp | [-37pp, +10pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.88 | +0.030 | [-0.110, +0.162] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_facts_band 4, p=1.0; 3-class only-champion 10 vs only-kev_facts_band 5, p=0.3018.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_band - champion

| metric | champion | kev_facts_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.022 | [-0.209, +0.115] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [-0.311, +0.281] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-5pp, +32pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [-25pp, +22pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.011 | [-0.136, +0.140] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_facts_band 4, p=1.0; 3-class only-champion 7 vs only-kev_facts_band 7, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_band - champion

| metric | champion | kev_facts_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.131 | [-0.391, +0.057] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.524, +0.070] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+4pp, +54pp] | **real**: champion better |
| accuracy | 79% | 71% | -8pp | [-33pp, +12pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.79 | -0.066 | [-0.235, +0.094] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-kev_facts_band 4, p=0.3877; 3-class only-champion 10 vs only-kev_facts_band 6, p=0.4545.

Flips (cv, 16 calls):

| call | expected | champion | kev_facts_band | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.16 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.16 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.79 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.79 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.05 | same | 01:02-01:03 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.09 | same | 01:35-01:36 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.99 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.99 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.73 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.04 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt un... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_facts_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_blind - champion

| metric | champion | kev_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.85 | -0.012 | [-0.207, +0.157] | no detectable difference |
| alarm AUC | 0.90 | 0.92 | +0.015 | [-0.057, +0.090] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_blind - champion

| metric | champion | kev_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.037 | [-0.244, +0.139] | no detectable difference |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.675, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-30pp, +0pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [-13pp, +40pp] | no detectable difference |
| accuracy | 79% | 65% | -15pp | [-40pp, +9pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.84 | -0.012 | [-0.177, +0.158] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts_blind 4, p=1.0; 3-class only-champion 12 vs only-kev_facts_blind 5, p=0.1435.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_blind - champion

| metric | champion | kev_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.83 | -0.014 | [-0.231, +0.173] | no detectable difference |
| alarm_f1 | 0.67 | 0.57 | -0.095 | [-0.434, +0.214] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-30pp, +0pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-20pp, +37pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-28pp, +21pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.84 | +0.007 | [-0.161, +0.183] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts_blind 5, p=1.0; 3-class only-champion 8 vs only-kev_facts_blind 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_blind - champion

| metric | champion | kev_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.56 | -0.307 | [-0.656, -0.063] | **real**: champion better |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.675, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 62% | +46pp | [+18pp, +75pp] | **real**: champion better |
| accuracy | 79% | 62% | -17pp | [-41pp, +5pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.163 | [-0.333, +0.010] | no detectable difference |

McNemar exact (calls): flag correct only-champion 12 vs only-kev_facts_blind 3, p=0.0352; 3-class only-champion 12 vs only-kev_facts_blind 4, p=0.0768.

Flips (cv, 17 calls):

| call | expected | champion | kev_facts_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `kev_facts_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_para - champion

| metric | champion | kev_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.90 | +0.036 | [-0.130, +0.181] | no detectable difference |
| alarm AUC | 0.90 | 0.99 | +0.084 | [-0.017, +0.242] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_para - champion

| metric | champion | kev_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.007 | [-0.149, +0.133] | no detectable difference |
| alarm_f1 | 0.86 | 0.73 | -0.130 | [-0.414, +0.121] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-33pp, +12pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.88 | +0.030 | [-0.114, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_facts_para 4, p=1.0; 3-class only-champion 10 vs only-kev_facts_para 6, p=0.4545.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_para - champion

| metric | champion | kev_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.004 | [-0.161, +0.133] | no detectable difference |
| alarm_f1 | 0.67 | 0.73 | +0.061 | [-0.199, +0.350] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-9pp, +28pp] | no detectable difference |
| accuracy | 69% | 71% | +2pp | [-23pp, +24pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.87 | +0.030 | [-0.114, +0.156] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_facts_para 5, p=1.0; 3-class only-champion 8 vs only-kev_facts_para 9, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_para - champion

| metric | champion | kev_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.131 | [-0.352, +0.037] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.524, +0.070] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+4pp, +50pp] | **real**: champion better |
| accuracy | 79% | 69% | -10pp | [-34pp, +10pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.79 | -0.066 | [-0.223, +0.075] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-kev_facts_para 4, p=0.3877; 3-class only-champion 10 vs only-kev_facts_para 5, p=0.3018.

Flips (cv, 16 calls):

| call | expected | champion | kev_facts_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `kev_facts_para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_para2 - champion

| metric | champion | kev_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.90 | +0.031 | [-0.166, +0.188] | no detectable difference |
| alarm AUC | 0.90 | 0.99 | +0.085 | [-0.007, +0.238] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_para2 - champion

| metric | champion | kev_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.89 | +0.031 | [-0.131, +0.176] | no detectable difference |
| alarm_f1 | 0.86 | 0.81 | -0.046 | [-0.348, +0.213] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 19% | +4pp | [-20pp, +27pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-28pp, +20pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.90 | +0.049 | [-0.093, +0.179] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_facts_para2 5, p=0.7266; 3-class only-champion 8 vs only-kev_facts_para2 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_para2 - champion

| metric | champion | kev_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.89 | +0.054 | [-0.112, +0.206] | no detectable difference |
| alarm_f1 | 0.67 | 0.81 | +0.144 | [-0.197, +0.506] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [-25pp, +25pp] | no detectable difference |
| accuracy | 69% | 77% | +8pp | [-18pp, +33pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.90 | +0.068 | [-0.071, +0.206] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-kev_facts_para2 6, p=0.5078; 3-class only-champion 7 vs only-kev_facts_para2 11, p=0.4807.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_para2 - champion

| metric | champion | kev_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.007 | [-0.164, +0.162] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.326, +0.127] | no detectable difference |
| false_alarm_rate | 14% | 0% | -14pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [-17pp, +31pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-24pp, +17pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.88 | +0.030 | [-0.115, +0.164] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-kev_facts_para2 5, p=1.0; 3-class only-champion 6 vs only-kev_facts_para2 5, p=1.0.

Flips (cv, 16 calls):

| call | expected | champion | kev_facts_para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `kev_general_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_para - champion

| metric | champion | kev_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.88 | +0.010 | [-0.110, +0.178] | no detectable difference |
| alarm AUC | 0.90 | 0.83 | -0.079 | [-0.159, +0.006] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_para - champion

| metric | champion | kev_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.84 | -0.021 | [-0.177, +0.129] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.430, -0.016] | **real**: champion better |
| false_alarm_rate | 14% | 32% | +18pp | [-18pp, +50pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-40pp, +5pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.052 | [-0.215, +0.140] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_general_para 4, p=0.7539; 3-class only-champion 14 vs only-kev_general_para 6, p=0.1153.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_para - champion

| metric | champion | kev_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.90 | +0.062 | [-0.054, +0.206] | no detectable difference |
| alarm_f1 | 0.67 | 0.70 | +0.036 | [-0.237, +0.312] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 19% | 12% | -8pp | [-27pp, +8pp] | no detectable difference |
| accuracy | 69% | 77% | +8pp | [-10pp, +28pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.90 | +0.061 | [-0.062, +0.211] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-kev_general_para 5, p=0.4531; 3-class only-champion 5 vs only-kev_general_para 9, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_para - champion

| metric | champion | kev_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.90 | +0.039 | [-0.067, +0.173] | no detectable difference |
| alarm_f1 | 0.86 | 0.70 | -0.154 | [-0.383, +0.011] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-22pp, +10pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-18pp, +12pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.90 | +0.042 | [-0.069, +0.186] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-kev_general_para 4, p=0.6875; 3-class only-champion 7 vs only-kev_general_para 6, p=1.0.

Flips (cv, 21 calls):

| call | expected | champion | kev_general_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.56 | same | 02:37-03:10 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. Ich nehme das Zahler nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmit... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.61 | same | 02:44-03:12 documentation: Ich nehme das Zahlerlehrer mit in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. Dem Wunsch kan... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.45 | broken | Prüfen (knapp unter Schwelle): Score 0.45 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.48 | broken | Prüfen (knapp unter Schwelle): Score 0.48 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.43 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Prüfen (knapp unter Schwelle): Score 0.43 für 'Relevante Angabe vers... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.00/0.41 | broken | Prüfen (knapp unter Schwelle): Score 0.41 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | review | 0.00/0.40 | broken | Prüfen (knapp unter Schwelle): Score 0.40 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.25 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.25 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.23 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.23 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.66 | same | 00:29-01:11 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? Richtig. Wir haben den Beleg des Heimes und eine Liste der monatlichen Ausgaben. Ich frage wegen ihrem Konto, nicht wege... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.98 | same | 07:44-08:25 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machiat den Satz aus dem Doss... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.98 | same | 07:57-08:34 documentation: Dann lässt mir der Violette Machio den Satz. Ja, das ist gut. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.97 | same | 07:45-08:27 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machiat den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.94 | broken | 07:52-08:30 documentation: Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machio den Satz aus dem Dossier heraus. Ich will, dass die Finanzierung das Ganze ausmac... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.65 | same | 00:00-00:52 documentation: Grüezi, hier ist Esther von Kauser. Sie haben um Hilfe mit einer Anzeige im Online-Zugang gebeten. Was sehen Sie? Ich habe einen Screenshot auf meinem Telefon. Ich wollte ge... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.63 | same | 00:20-00:57 documentation: Jetzt bin ich nicht sicher, was davon noch zum laufenden Vorgang gehört. Sind Sie aktuell im echten Fenster oder schauen Sie nur den Screenshot an? Ja, Witzenteile keine Zah... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.80 | same | 00:00-00:49 disclosure: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.84 | same | 00:00-00:50 disclosure: Guten Tag, Frau Ott, das ist Daniela Gott. Sie haben wegen dem Haushaltskonto von Ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist für zwei Monate im Ausland. Ich habe i... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.57 | fixed | 00:00-00:50 splitting: Grüezi Frau Gislo, hier ist die eigene Waldo vom Firmenservice. Sie haben eine Frage zu Beträgen, die an den gleichen Lieferanten gehen sollten. Ja, in meiner Liste sind viertau... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.59 | fixed | 01:44-02:23 documentation: Für jeden konkreten Vorgang braucht es aber die Unterlagen und eine klare Zuordnung. Können Sie diese viertausend verhüten? Ich kann Ihnen noch nicht sagen, warum das geplan... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_general_para_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_general_para_alone - champion

| metric | champion | kev_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.88 | +0.018 | [-0.096, +0.178] | no detectable difference |
| alarm AUC | 0.90 | 0.84 | -0.069 | [-0.150, +0.015] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_para_alone - champion

| metric | champion | kev_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.84 | -0.021 | [-0.177, +0.129] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.430, -0.016] | **real**: champion better |
| false_alarm_rate | 14% | 32% | +18pp | [-18pp, +50pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-40pp, +5pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.052 | [-0.215, +0.140] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_general_para_alone 4, p=0.7539; 3-class only-champion 14 vs only-kev_general_para_alone 6, p=0.1153.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_para_alone - champion

| metric | champion | kev_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.90 | +0.062 | [-0.054, +0.206] | no detectable difference |
| alarm_f1 | 0.67 | 0.70 | +0.036 | [-0.237, +0.312] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 19% | 12% | -8pp | [-27pp, +8pp] | no detectable difference |
| accuracy | 69% | 77% | +8pp | [-10pp, +28pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.90 | +0.061 | [-0.062, +0.211] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-kev_general_para_alone 5, p=0.4531; 3-class only-champion 5 vs only-kev_general_para_alone 9, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_general_para_alone - champion

| metric | champion | kev_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.90 | +0.039 | [-0.067, +0.173] | no detectable difference |
| alarm_f1 | 0.86 | 0.70 | -0.154 | [-0.383, +0.011] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-27pp, +12pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-22pp, +10pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-18pp, +12pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [-100pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.90 | +0.042 | [-0.069, +0.186] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-kev_general_para_alone 4, p=0.6875; 3-class only-champion 7 vs only-kev_general_para_alone 6, p=1.0.

Flips (cv, 21 calls):

| call | expected | champion | kev_general_para_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.58 | same | 02:37-03:10 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. Ich nehme das Zahler nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmit... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.62 | same | 02:44-03:12 documentation: Ich nehme das Zahlerlehrer mit in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. Dem Wunsch kan... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.45 | broken | Prüfen (knapp unter Schwelle): Score 0.45 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.48 | broken | Prüfen (knapp unter Schwelle): Score 0.48 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.44 | broken | Prüfen (knapp unter Schwelle): Score 0.44 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.43 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Prüfen (knapp unter Schwelle): Score 0.43 für 'Relevante Angabe vers... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C08-K3 | no_alert | no_alert | review | 0.00/0.41 | broken | Prüfen (knapp unter Schwelle): Score 0.41 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C08-K4 | no_alert | no_alert | review | 0.00/0.40 | broken | Prüfen (knapp unter Schwelle): Score 0.40 für 'Relevante Angabe verschweigen' liegt zwischen 0.40 und der Schwelle 0.55. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.25 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.25 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.23 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.23 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | review | 0.94/0.66 | same | 00:29-01:11 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? Richtig. Wir haben den Beleg des Heimes und eine Liste der monatlichen Ausgaben. Ich frage wegen ihrem Konto, nicht wege... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.98 | same | 07:44-08:25 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mich der Violett Machiat den Satz aus dem Doss... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.98 | same | 07:57-08:34 documentation: Dann lässt mir der Violette Machio den Satz. Ja, das ist gut. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.97 | same | 07:45-08:27 documentation: Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machiat den Satz aus dem Dossi... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.94 | broken | 07:52-08:30 documentation: Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lässt mir der Violett Machio den Satz aus dem Dossier heraus. Ich will, dass die Finanzierung das Ganze ausmac... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.65 | same | 00:00-00:52 documentation: Grüezi, hier ist Esther von Kauser. Sie haben um Hilfe mit einer Anzeige im Online-Zugang gebeten. Was sehen Sie? Ich habe einen Screenshot auf meinem Telefon. Ich wollte ge... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.63 | same | 00:20-00:57 documentation: Jetzt bin ich nicht sicher, was davon noch zum laufenden Vorgang gehört. Sind Sie aktuell im echten Fenster oder schauen Sie nur den Screenshot an? Ja, Witzenteile keine Zah... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.80 | same | 00:00-00:49 disclosure: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.84 | same | 00:00-00:50 disclosure: Guten Tag, Frau Ott, das ist Daniela Gott. Sie haben wegen dem Haushaltskonto von Ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist für zwei Monate im Ausland. Ich habe i... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.57 | fixed | 00:00-00:50 splitting: Grüezi Frau Gislo, hier ist die eigene Waldo vom Firmenservice. Sie haben eine Frage zu Beträgen, die an den gleichen Lieferanten gehen sollten. Ja, in meiner Liste sind viertau... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.59 | fixed | 01:44-02:23 documentation: Für jeden konkreten Vorgang braucht es aber die Unterlagen und eine klare Zuordnung. Können Sie diese viertausend verhüten? Ich kann Ihnen noch nicht sagen, warum das geplan... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `qwen_facts_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_facts_blind - champion

| metric | champion | qwen_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.73 | -0.141 | [-0.323, -0.008] | **real**: champion better |
| alarm AUC | 0.90 | 0.81 | -0.094 | [-0.260, +0.017] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_blind - champion

| metric | champion | qwen_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.390, -0.034] | **real**: champion better |
| alarm_f1 | 0.86 | 0.56 | -0.301 | [-0.556, -0.095] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 58% | -21pp | [-40pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.70 | -0.157 | [-0.312, -0.016] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-qwen_facts_blind 1, p=0.0215; 3-class only-champion 11 vs only-qwen_facts_blind 1, p=0.0063.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_blind - champion

| metric | champion | qwen_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.67 | -0.173 | [-0.349, -0.023] | **real**: champion better |
| alarm_f1 | 0.67 | 0.56 | -0.111 | [-0.359, +0.106] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [+5pp, +45pp] | **real**: champion better |
| accuracy | 69% | 58% | -10pp | [-29pp, +6pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.70 | -0.138 | [-0.281, -0.004] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_facts_blind 1, p=0.0391; 3-class only-champion 8 vs only-qwen_facts_blind 3, p=0.2266.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_blind - champion

| metric | champion | qwen_facts_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.390, -0.034] | **real**: champion better |
| alarm_f1 | 0.86 | 0.60 | -0.257 | [-0.534, -0.078] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-13pp, +29pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 79% | 60% | -19pp | [-36pp, -4pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.70 | -0.157 | [-0.312, -0.016] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-qwen_facts_blind 1, p=0.0215; 3-class only-champion 10 vs only-qwen_facts_blind 1, p=0.0117.

Flips (cv, 15 calls):

| call | expected | champion | qwen_facts_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `qwen_facts_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_facts_para - champion

| metric | champion | qwen_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.72 | -0.147 | [-0.313, -0.025] | **real**: champion better |
| alarm AUC | 0.90 | 0.88 | -0.025 | [-0.081, +0.033] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_para - champion

| metric | champion | qwen_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.182 | [-0.361, -0.059] | **real**: champion better |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.287, +0.039] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-31pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.161 | [-0.288, -0.057] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_facts_para 0, p=0.0078; 3-class only-champion 9 vs only-qwen_facts_para 3, p=0.146.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_para - champion

| metric | champion | qwen_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.68 | -0.159 | [-0.344, -0.014] | **real**: champion better |
| alarm_f1 | 0.67 | 0.72 | +0.051 | [-0.167, +0.318] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-4pp, +43pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-24pp, +14pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.69 | -0.142 | [-0.276, -0.021] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_facts_para 1, p=0.0391; 3-class only-champion 8 vs only-qwen_facts_para 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_para - champion

| metric | champion | qwen_facts_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.182 | [-0.361, -0.059] | **real**: champion better |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.444, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-38pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.161 | [-0.288, -0.057] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-qwen_facts_para 0, p=0.0078; 3-class only-champion 11 vs only-qwen_facts_para 0, p=0.001.

Flips (cv, 15 calls):

| call | expected | champion | qwen_facts_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `qwen_facts_para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_facts_para2 - champion

| metric | champion | qwen_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.74 | -0.130 | [-0.290, -0.011] | **real**: champion better |
| alarm AUC | 0.90 | 0.90 | -0.003 | [-0.042, +0.040] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_para2 - champion

| metric | champion | qwen_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.81 | -0.048 | [-0.132, +0.065] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-24pp, +4pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-qwen_facts_para2 0, p=0.0312; 3-class only-champion 7 vs only-qwen_facts_para2 3, p=0.3438.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_para2 - champion

| metric | champion | qwen_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.73 | -0.105 | [-0.275, +0.030] | no detectable difference |
| alarm_f1 | 0.67 | 0.00 | -0.667 | [-0.875, -0.364] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-9pp, +36pp] | no detectable difference |
| accuracy | 69% | 35% | -33pp | [-52pp, -17pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.73 | -0.103 | [-0.227, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-qwen_facts_para2 1, p=0.125; 3-class only-champion 16 vs only-qwen_facts_para2 0, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_facts_para2 - champion

| metric | champion | qwen_facts_para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.71 | -0.147 | [-0.269, -0.038] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 58% | -21pp | [-35pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-qwen_facts_para2 0, p=0.0312; 3-class only-champion 10 vs only-qwen_facts_para2 0, p=0.002.

Flips (cv, 13 calls):

| call | expected | champion | qwen_facts_para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `qwen_general_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general_para - champion

| metric | champion | qwen_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.71 | -0.156 | [-0.364, +0.032] | no detectable difference |
| alarm AUC | 0.90 | 0.69 | -0.218 | [-0.393, -0.064] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_para - champion

| metric | champion | qwen_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.183 | [-0.410, -0.003] | **real**: champion better |
| alarm_f1 | 0.86 | 0.59 | -0.272 | [-0.522, -0.078] | **real**: champion better |
| false_alarm_rate | 14% | 41% | +27pp | [+0pp, +61pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [-13pp, +46pp] | no detectable difference |
| accuracy | 79% | 52% | -27pp | [-50pp, -10pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.64 | -0.213 | [-0.425, -0.036] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_para 3, p=0.0213; 3-class only-champion 16 vs only-qwen_general_para 3, p=0.0044.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_para - champion

| metric | champion | qwen_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.65 | -0.188 | [-0.448, +0.037] | no detectable difference |
| alarm_f1 | 0.67 | 0.47 | -0.193 | [-0.513, +0.141] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [-19pp, +39pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [-9pp, +57pp] | no detectable difference |
| accuracy | 69% | 54% | -15pp | [-37pp, +7pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.67 | -0.161 | [-0.356, +0.020] | no detectable difference |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_para 5, p=0.0963; 3-class only-champion 13 vs only-qwen_general_para 6, p=0.1671.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_para - champion

| metric | champion | qwen_general_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.60 | -0.258 | [-0.493, -0.080] | **real**: champion better |
| alarm_f1 | 0.86 | 0.50 | -0.357 | [-0.673, -0.114] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-21pp, +27pp] | no detectable difference |
| miss_rate | 15% | 50% | +35pp | [+8pp, +63pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-41pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.66 | -0.196 | [-0.343, -0.051] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_para 3, p=0.0213; 3-class only-champion 15 vs only-qwen_general_para 4, p=0.0192.

Flips (cv, 23 calls):

| call | expected | champion | qwen_general_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K1 | no_alert | no_alert | review | 0.04/0.06 | broken | Prüfen (knapp unter Schwelle): Score 0.06 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.85 | broken | Alarm: Score 0.85 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | alarm | no_alert | 0.91/0.05 | broken | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Kein Alarm: höchster Score 0.05 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle 0.25 min... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.90/0.08 | broken | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - Kein Alarm: höchs... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.95 | broken | 01:51-01:52 splitting: Und im Mail hat jemand geschrieben, ich solle zum Gerätewechsel die Prüfung umgehen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.45 | broken | 00:28-00:28 access: Für das Passwort sagen Sie mir bitte nur, ob Sie sich da erinnern. - keywords: Stichwort K10 «Passwort» (Zugangswörter) | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.09 | broken | 03:08-03:09 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März passiert sei. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.10 | broken | 03:10-03:11 documentation: Weiter nicht protokollieren, dass die Appelausgabe im März passiert sei. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C06-K4 | alarm | alarm | review | 1.00/0.07 | same | 01:09-01:23 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Der Kunde erwähnt, dass er den Bericht von Claudia persönlich bekommen hat, die das Projekt leitet. (Regel: trade.alarm_... |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.19 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Prüfen (knapp unter Schwelle): Score 0.19 für 'Insiderhandel' liegt ... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.02 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.02 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | no_alert | 0.50/0.00 | broken | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.00 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe ve... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/1.00 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.99 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/1.00 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Alarm: Score 1.00 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.89 | broken | Alarm: Score 0.89 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.98 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Alarm: Score 0.98 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherhe... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.96 | same | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.44 | fixed | Alarm: Score 0.44 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.92 | fixed | Alarm: Score 0.92 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `qwen_general_para_alone` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen_general_para_alone - champion

| metric | champion | qwen_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.70 | -0.162 | [-0.370, +0.028] | no detectable difference |
| alarm AUC | 0.90 | 0.69 | -0.217 | [-0.399, -0.062] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_para_alone - champion

| metric | champion | qwen_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.183 | [-0.410, -0.003] | **real**: champion better |
| alarm_f1 | 0.86 | 0.55 | -0.307 | [-0.562, -0.106] | **real**: champion better |
| false_alarm_rate | 14% | 41% | +27pp | [+0pp, +61pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [-13pp, +46pp] | no detectable difference |
| accuracy | 79% | 50% | -29pp | [-52pp, -12pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.64 | -0.213 | [-0.425, -0.036] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_para_alone 3, p=0.0213; 3-class only-champion 17 vs only-qwen_general_para_alone 3, p=0.0026.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_para_alone - champion

| metric | champion | qwen_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.62 | -0.218 | [-0.503, +0.026] | no detectable difference |
| alarm_f1 | 0.67 | 0.47 | -0.193 | [-0.513, +0.141] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [-19pp, +39pp] | no detectable difference |
| miss_rate | 19% | 46% | +27pp | [-7pp, +62pp] | no detectable difference |
| accuracy | 69% | 54% | -15pp | [-37pp, +7pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.66 | -0.180 | [-0.375, +0.010] | no detectable difference |

McNemar exact (calls): flag correct only-champion 14 vs only-qwen_general_para_alone 5, p=0.0636; 3-class only-champion 13 vs only-qwen_general_para_alone 6, p=0.1671.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen_general_para_alone - champion

| metric | champion | qwen_general_para_alone | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.60 | -0.258 | [-0.493, -0.080] | **real**: champion better |
| alarm_f1 | 0.86 | 0.50 | -0.357 | [-0.673, -0.114] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [-21pp, +27pp] | no detectable difference |
| miss_rate | 15% | 50% | +35pp | [+8pp, +63pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-41pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.66 | -0.196 | [-0.343, -0.051] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 13 vs only-qwen_general_para_alone 3, p=0.0213; 3-class only-champion 15 vs only-qwen_general_para_alone 4, p=0.0192.

Flips (cv, 24 calls):

| call | expected | champion | qwen_general_para_alone | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D03-K1 | no_alert | no_alert | review | 0.04/0.06 | broken | Prüfen (knapp unter Schwelle): Score 0.06 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D03-K2 | no_alert | no_alert | alarm | 0.04/0.85 | broken | Alarm: Score 0.85 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D05-K1 | alarm | alarm | no_alert | 0.91/0.02 | broken | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.15 (Schwelle 0.30 min... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.90/0.08 | broken | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - Kein Alarm: höchs... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D06-K1 | no_alert | no_alert | alarm | 0.03/0.98 | broken | Alarm: Score 0.98 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D06-K2 | no_alert | no_alert | alarm | 0.03/0.46 | broken | Alarm: Score 0.46 für 'Zugangsinformation preisgegeben' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.03 ('Zugangsinformation preisgegeben') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.07 | broken | Prüfen (knapp unter Schwelle): Score 0.07 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.08 | broken | Prüfen (knapp unter Schwelle): Score 0.08 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.24 | same | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe2_C06-K4 | alarm | alarm | review | 1.00/0.07 | same | 01:09-01:23 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Der Kunde erwähnt, dass er den Bericht von Claudia persönlich bekommen hat, die das Projekt leitet. (Regel: trade.alarm_... |
| Stufe2_C07-K4 | alarm | alarm | review | 0.84/0.19 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Prüfen (knapp unter Schwelle): Score 0.19 für 'Insiderhandel' liegt ... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.02 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.02 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | no_alert | 0.50/0.00 | broken | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.00 ('Relevante ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe ve... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.86) - Der Advisor sagt explizit, dass die Klientin keine Berechtigung zum Verkaufsverfahren hat. (Regel: disclosure.alarm_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/1.00 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.99 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/1.00 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Alarm: Score 1.00 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.89 | broken | Alarm: Score 0.89 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.15 (Schwelle 0.30 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.15 (Schwelle 0.30 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.98 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Alarm: Score 0.98 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherhe... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.96 | same | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.44 | fixed | Alarm: Score 0.44 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.92 | fixed | Alarm: Score 0.92 für 'Relevante Angabe verschweigen' >= Schwelle 0.30 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `kev_facts_v3` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = kev_facts_v3 - champion

| metric | champion | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.83 | -0.038 | [-0.231, +0.119] | no detectable difference |
| alarm AUC | 0.90 | 0.95 | +0.045 | [-0.040, +0.167] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_v3 - champion

| metric | champion | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.80 | -0.063 | [-0.267, +0.091] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.514, +0.056] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-33pp, +11pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [-6pp, +41pp] | no detectable difference |
| accuracy | 79% | 67% | -12pp | [-38pp, +8pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.82 | -0.032 | [-0.200, +0.117] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-kev_facts_v3 4, p=0.7539; 3-class only-champion 11 vs only-kev_facts_v3 5, p=0.2101.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_v3 - champion

| metric | champion | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.80 | -0.040 | [-0.221, +0.100] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [-0.303, +0.307] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-33pp, +11pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-7pp, +32pp] | no detectable difference |
| accuracy | 69% | 67% | -2pp | [-26pp, +20pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.82 | -0.012 | [-0.170, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-kev_facts_v3 4, p=1.0; 3-class only-champion 8 vs only-kev_facts_v3 7, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = kev_facts_v3 - champion

| metric | champion | kev_facts_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.71 | -0.148 | [-0.381, +0.026] | no detectable difference |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.529, +0.042] | no detectable difference |
| false_alarm_rate | 14% | 5% | -9pp | [-33pp, +11pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+3pp, +54pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-36pp, +7pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.089 | [-0.250, +0.060] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_facts_v3 4, p=0.2668; 3-class only-champion 10 vs only-kev_facts_v3 4, p=0.1796.

Flips (cv, 16 calls):

| call | expected | champion | kev_facts_v3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.49 | same | 01:18-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.16 | same | 01:19-01:23 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | 0.90/0.79 | same | 02:37-02:39 documentation: Dann bitte nicht protokollieren, dass ich die zwanzigtausend zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.79 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.93/0.05 | broken | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.80/0.09 | broken | 01:35-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C05-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | Alarm: Score 0.50 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.25 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | alarm | 0.00/0.50 | fixed | Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C11-K3 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | no_alert | 0.50/0.03 | fixed | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Kein Alarm: höchster Score 0.03 ('Auskunft a... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.99 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - Alarm: Score 0.99 für 'Auskunft an Dritte' >... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.04 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.04 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.01 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Alarm: Score 0.50 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Zuständigkeit/Kontrolle umgehen') liegt ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

