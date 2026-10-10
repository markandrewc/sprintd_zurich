# Experiment `champion`

Recommended profile (large-v3 MIT + Qwen2.5-7B facts + light keywords/patterns) and its neighbours

RQ: RQ2, RQ4, RQ5, RQ9 · base profile `recommended` · split **dev** · baseline `champion` · commit 480479c79d (dirty) · 2026-10-10T05:59:04+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| champion | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 |  |
| facts_only | 0.89 [0.77, 0.99] | 0.92 [0.78, 1.00] | 26/22 | re-fusion of champion |
| t045 | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion |
| t065 | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion |
| noesc | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion |
| band025 | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 | re-fusion of champion |
| table_v2 | 0.87 [0.71, 0.98] | 0.95 [0.86, 1.00] | 26/22 |  |
| para | 0.72 [0.52, 0.88] | 0.88 [0.74, 0.99] | 26/22 |  |
| table_v3 | 0.92 [0.80, 1.00] | 0.90 [0.73, 1.00] | 26/22 |  |
| para2 | 0.74 [0.54, 0.90] | 0.90 [0.76, 0.99] | 26/22 |  |
| ens2 | 0.81 [0.65, 0.94] | 0.90 [0.76, 1.00] | 26/22 |  |
| ens3 | 0.74 [0.54, 0.92] | 0.91 [0.76, 1.00] | 26/22 |  |
| ens3_d06 | 0.77 [0.59, 0.93] | 0.90 [0.75, 1.00] | 26/22 |  |
| ens3_band | 0.73 [0.55, 0.90] | 0.89 [0.75, 1.00] | 26/22 |  |
| ens2b | 0.78 [0.59, 0.94] | 0.91 [0.76, 1.00] | 26/22 |  |
| ens_blind | 0.75 [0.55, 0.92] | 0.91 [0.77, 1.00] | 26/22 |  |
| turbo_clean | 0.85 [0.70, 0.98] | 0.87 [0.71, 0.98] | 26/22 |  |
| s1_v1_08 | 0.86 [0.72, 0.98] | 0.89 [0.73, 0.99] | 26/22 |  |
| s1_v3_08 | 0.91 [0.80, 1.00] | 0.88 [0.72, 0.99] | 26/22 |  |
| s1_para_08 | 0.74 [0.57, 0.89] | 0.85 [0.71, 0.97] | 26/22 |  |
| fs_tuned | 0.80 [0.62, 0.94] | 0.92 [0.78, 1.00] | 26/22 |  |
| fs_para | 0.70 [0.52, 0.87] | 0.85 [0.71, 0.98] | 26/22 |  |
| qlang_de | 0.73 [0.54, 0.91] | 0.90 [0.76, 1.00] | 26/22 |  |
| noroles | 0.81 [0.64, 0.95] | 0.83 [0.65, 0.97] | 26/22 |  |
| prefixmax | 0.87 [0.72, 0.99] | 0.90 [0.74, 1.00] | 26/22 |  |
| s3 | 0.89 [0.74, 0.99] | 0.94 [0.84, 1.00] | 26/22 | re-fusion of champion |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| t045 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| t065 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| noesc | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| band025 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| table_v2 | 48 | 0.83 [0.67, 0.96] | 75% | 92% | 36% [6%, 67%] | 8% [0%, 25%] | 0.73 | 33% | 65% | 0.78 [0.61, 0.94] |  |
| para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.75 | 0% | 67% | 0.69 [0.55, 0.83] |  |
| table_v3 | 48 | 0.91 [0.80, 1.00] | 89% | 92% | 14% [0%, 35%] | 8% [0%, 25%] | 0.86 | 100% | 83% | 0.89 [0.78, 1.00] |  |
| para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.81 | 0% | 71% | 0.73 [0.58, 0.88] |  |
| ens2 | 48 | 0.79 [0.65, 0.91] | 86% | 73% | 14% [0%, 35%] | 27% [8%, 46%] | 0.78 | 0% | 73% | 0.80 [0.68, 0.91] |  |
| ens3 | 48 | 0.75 [0.55, 0.90] | 82% | 69% | 18% [0%, 44%] | 31% [8%, 58%] | 0.86 | 0% | 75% | 0.76 [0.60, 0.91] |  |
| ens3_d06 | 48 | 0.78 [0.60, 0.91] | 83% | 73% | 18% [0%, 44%] | 27% [6%, 50%] | 0.84 | 0% | 75% | 0.77 [0.62, 0.91] |  |
| ens3_band | 48 | 0.73 [0.48, 0.90] | 89% | 62% | 9% [0%, 30%] | 38% [12%, 67%] | 0.78 | 0% | 71% | 0.76 [0.62, 0.91] |  |
| ens2b | 48 | 0.78 [0.60, 0.91] | 83% | 73% | 18% [0%, 44%] | 27% [6%, 50%] | 0.83 | 0% | 69% | 0.77 [0.63, 0.92] |  |
| ens_blind | 48 | 0.75 [0.55, 0.90] | 82% | 69% | 18% [0%, 44%] | 31% [8%, 58%] | 0.83 | 0% | 73% | 0.76 [0.60, 0.91] |  |
| turbo_clean | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 44%] | 0.74 | 0% | 73% | 0.82 [0.70, 0.93] |  |
| s1_v1_08 | 48 | 0.82 [0.68, 0.94] | 84% | 81% | 18% [0%, 40%] | 19% [0%, 40%] | 0.81 | 33% | 77% | 0.81 [0.69, 0.93] |  |
| s1_v3_08 | 48 | 0.87 [0.75, 0.96] | 85% | 88% | 18% [0%, 40%] | 12% [0%, 29%] | 0.77 | 33% | 77% | 0.85 [0.75, 0.95] |  |
| s1_para_08 | 48 | 0.72 [0.56, 0.86] | 81% | 65% | 18% [0%, 44%] | 35% [12%, 58%] | 0.68 | 0% | 65% | 0.74 [0.60, 0.87] |  |
| fs_tuned | 48 | 0.79 [0.62, 0.92] | 86% | 73% | 14% [0%, 35%] | 27% [6%, 50%] | 0.79 | 0% | 71% | 0.80 [0.67, 0.92] |  |
| fs_para | 48 | 0.67 [0.45, 0.83] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 68%] | 0.70 | 0% | 65% | 0.70 [0.56, 0.84] |  |
| qlang_de | 48 | 0.68 [0.45, 0.84] | 83% | 58% | 14% [0%, 35%] | 42% [17%, 69%] | 0.79 | 0% | 71% | 0.72 [0.59, 0.86] |  |
| noroles | 48 | 0.78 [0.61, 0.92] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.70 | 0% | 67% | 0.77 [0.62, 0.92] |  |
| prefixmax | 48 | 0.85 [0.71, 0.96] | 85% | 85% | 18% [0%, 40%] | 15% [0%, 36%] | 0.86 | 67% | 77% | 0.83 [0.71, 0.95] |  |
| s3 | 48 | 0.79 [0.62, 0.93] | 69% | 92% | 50% [19%, 80%] | 8% [0%, 25%] | 0.86 | 67% | 62% | 0.71 [0.55, 0.89] | re-fusion of champion |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.67 | 67% | 69% | 0.85 [0.73, 0.96] | re-fusion of champion |
| t045 | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of champion |
| t065 | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of champion |
| noesc | 48 | 0.84 [0.70, 0.95] | 88% | 81% | 14% [0%, 35%] | 19% [0%, 40%] | 0.67 | 67% | 69% | 0.84 [0.71, 0.95] | re-fusion of champion |
| band025 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.18 | 67% | 52% | 0.85 [0.73, 0.96] | re-fusion of champion |
| table_v2 | 48 | 0.81 [0.64, 0.94] | 74% | 88% | 36% [6%, 67%] | 12% [0%, 30%] | 0.67 | 67% | 58% | 0.76 [0.59, 0.93] |  |
| para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.72 | 0% | 65% | 0.69 [0.55, 0.83] |  |
| table_v3 | 48 | 0.88 [0.77, 0.98] | 88% | 88% | 14% [0%, 35%] | 12% [0%, 30%] | 0.67 | 100% | 73% | 0.87 [0.76, 0.98] |  |
| para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.00 | 0% | 35% | 0.73 [0.58, 0.88] |  |
| ens2 | 48 | 0.79 [0.65, 0.91] | 86% | 73% | 14% [0%, 35%] | 27% [8%, 46%] | 0.74 | 17% | 71% | 0.80 [0.68, 0.91] |  |
| ens3 | 48 | 0.75 [0.55, 0.90] | 82% | 69% | 18% [0%, 44%] | 31% [8%, 58%] | 0.33 | 0% | 46% | 0.76 [0.60, 0.91] |  |
| ens3_d06 | 48 | 0.78 [0.60, 0.91] | 83% | 73% | 18% [0%, 44%] | 27% [6%, 50%] | 0.33 | 17% | 48% | 0.77 [0.62, 0.91] |  |
| ens3_band | 48 | 0.70 [0.44, 0.87] | 88% | 58% | 9% [0%, 30%] | 42% [17%, 69%] | 0.33 | 0% | 50% | 0.74 [0.60, 0.88] |  |
| ens2b | 48 | 0.75 [0.58, 0.89] | 82% | 69% | 18% [0%, 44%] | 31% [9%, 54%] | 0.57 | 17% | 56% | 0.76 [0.61, 0.89] |  |
| ens_blind | 48 | 0.72 [0.53, 0.88] | 81% | 65% | 18% [0%, 44%] | 35% [11%, 62%] | 0.46 | 0% | 50% | 0.74 [0.58, 0.88] |  |
| turbo_clean | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 44%] | 0.78 | 33% | 77% | 0.82 [0.70, 0.93] |  |
| s1_v1_08 | 48 | 0.82 [0.68, 0.94] | 84% | 81% | 18% [0%, 40%] | 19% [0%, 40%] | 0.78 | 33% | 75% | 0.81 [0.69, 0.93] |  |
| s1_v3_08 | 48 | 0.87 [0.75, 0.96] | 85% | 88% | 18% [0%, 40%] | 12% [0%, 29%] | 0.74 | 33% | 75% | 0.85 [0.75, 0.95] |  |
| s1_para_08 | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 44%] | 38% [14%, 63%] | 0.68 | 0% | 65% | 0.72 [0.58, 0.85] |  |
| fs_tuned | 48 | 0.77 [0.59, 0.90] | 86% | 69% | 14% [0%, 35%] | 31% [9%, 54%] | 0.67 | 17% | 62% | 0.78 [0.65, 0.90] |  |
| fs_para | 48 | 0.67 [0.45, 0.83] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 68%] | 0.70 | 0% | 65% | 0.70 [0.56, 0.84] |  |
| qlang_de | 48 | 0.68 [0.45, 0.84] | 83% | 58% | 14% [0%, 35%] | 42% [17%, 69%] | 0.79 | 0% | 71% | 0.72 [0.59, 0.86] |  |
| noroles | 48 | 0.78 [0.61, 0.92] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.56 | 0% | 58% | 0.77 [0.62, 0.92] |  |
| prefixmax | 48 | 0.82 [0.68, 0.94] | 84% | 81% | 18% [0%, 40%] | 19% [0%, 40%] | 0.67 | 67% | 67% | 0.81 [0.68, 0.93] |  |
| s3 | 48 | 0.79 [0.62, 0.93] | 69% | 92% | 50% [19%, 80%] | 8% [0%, 25%] | 0.18 | 67% | 35% | 0.71 [0.55, 0.89] | re-fusion of champion |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| champion | 14% | 4/4 | 14% | yes | - |
| facts_only | 14% | 4/4 | 14% | yes | - |
| t045 | 14% | 4/4 | 14% | yes | - |
| t065 | 14% | 4/4 | 14% | yes | - |
| noesc | 14% | 4/4 | 14% | yes | - |
| band025 | 14% | 4/4 | 14% | yes | - |
| table_v2 | 36% (!) | 0/4 | 36% | **no** | - |
| para | 23% (!) | 2/4 | 23% | **no** | - |
| table_v3 | 14% | 4/4 | 14% | yes | - |
| para2 | 23% (!) | 2/4 | 23% | **no** | - |
| ens2 | 14% | 4/4 | 14% | yes | - |
| ens3 | 18% | 2/4 | 18% | yes | - |
| ens3_d06 | 18% | 2/4 | 18% | yes | - |
| ens3_band | 9% | 4/4 | 9% | yes | - |
| ens2b | 18% | 2/4 | 18% | yes | - |
| ens_blind | 18% | 2/4 | 18% | yes | - |
| turbo_clean | 14% | 4/4 | 14% | yes | - |
| s1_v1_08 | 18% | 2/4 | 18% | yes | - |
| s1_v3_08 | 18% | 2/4 | 18% | yes | - |
| s1_para_08 | 18% | 2/4 | 18% | yes | - |
| fs_tuned | 14% | 4/4 | 14% | yes | - |
| fs_para | 18% | 2/4 | 18% | yes | - |
| qlang_de | 14% | 4/4 | 14% | yes | - |
| noroles | 18% | 2/4 | 18% | yes | - |
| prefixmax | 18% | 2/4 | 18% | yes | - |
| s3 | 50% (!) | 0/4 | 50% | **no** | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] |  |
| facts_only | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| t045 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.80 | 0% | 77% | 0.85 [0.73, 0.96] | re-fusion of champion |
| t065 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| noesc | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| band025 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] | re-fusion of champion |
| table_v2 | 48 | 0.83 [0.67, 0.96] | 75% | 92% | 36% [6%, 67%] | 8% [0%, 25%] | 0.86 | 67% | 69% | 0.78 [0.61, 0.94] |  |
| para | 48 | 0.68 [0.48, 0.84] | 76% | 62% | 23% [0%, 50%] | 38% [14%, 64%] | 0.67 | 0% | 56% | 0.69 [0.55, 0.83] |  |
| table_v3 | 48 | 0.91 [0.80, 1.00] | 89% | 92% | 14% [0%, 35%] | 8% [0%, 25%] | 0.86 | 100% | 83% | 0.89 [0.78, 1.00] |  |
| para2 | 48 | 0.73 [0.55, 0.88] | 78% | 69% | 23% [0%, 50%] | 31% [8%, 58%] | 0.71 | 0% | 58% | 0.73 [0.58, 0.88] |  |
| ens2 | 48 | 0.79 [0.65, 0.91] | 86% | 73% | 14% [0%, 35%] | 27% [8%, 46%] | 0.79 | 33% | 71% | 0.80 [0.68, 0.91] |  |
| ens3 | 48 | 0.75 [0.55, 0.90] | 82% | 69% | 18% [0%, 44%] | 31% [8%, 58%] | 0.79 | 0% | 65% | 0.76 [0.60, 0.91] |  |
| ens3_d06 | 48 | 0.78 [0.60, 0.91] | 83% | 73% | 18% [0%, 44%] | 27% [6%, 50%] | 0.79 | 17% | 67% | 0.77 [0.62, 0.91] |  |
| ens3_band | 48 | 0.73 [0.48, 0.90] | 89% | 62% | 9% [0%, 30%] | 38% [12%, 67%] | 0.71 | 0% | 65% | 0.76 [0.62, 0.91] |  |
| ens2b | 48 | 0.78 [0.60, 0.91] | 83% | 73% | 18% [0%, 44%] | 27% [6%, 50%] | 0.86 | 17% | 71% | 0.77 [0.63, 0.92] |  |
| ens_blind | 48 | 0.75 [0.55, 0.90] | 82% | 69% | 18% [0%, 44%] | 31% [8%, 58%] | 0.75 | 0% | 62% | 0.76 [0.60, 0.91] |  |
| turbo_clean | 48 | 0.82 [0.68, 0.93] | 87% | 77% | 14% [0%, 35%] | 23% [4%, 44%] | 0.75 | 67% | 73% | 0.82 [0.70, 0.93] |  |
| s1_v1_08 | 48 | 0.82 [0.68, 0.94] | 84% | 81% | 18% [0%, 40%] | 19% [0%, 40%] | 0.82 | 67% | 75% | 0.81 [0.69, 0.93] |  |
| s1_v3_08 | 48 | 0.87 [0.75, 0.96] | 85% | 88% | 18% [0%, 40%] | 12% [0%, 29%] | 0.82 | 100% | 79% | 0.85 [0.75, 0.95] |  |
| s1_para_08 | 48 | 0.70 [0.50, 0.85] | 80% | 62% | 18% [0%, 44%] | 38% [14%, 63%] | 0.57 | 17% | 56% | 0.72 [0.58, 0.85] |  |
| fs_tuned | 48 | 0.79 [0.62, 0.92] | 86% | 73% | 14% [0%, 35%] | 27% [6%, 50%] | 0.82 | 17% | 71% | 0.80 [0.67, 0.92] |  |
| fs_para | 48 | 0.64 [0.42, 0.80] | 78% | 54% | 18% [0%, 44%] | 46% [20%, 71%] | 0.57 | 0% | 54% | 0.68 [0.54, 0.82] |  |
| qlang_de | 48 | 0.68 [0.45, 0.84] | 83% | 58% | 14% [0%, 35%] | 42% [17%, 69%] | 0.79 | 0% | 67% | 0.72 [0.59, 0.86] |  |
| noroles | 48 | 0.78 [0.61, 0.92] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.79 | 67% | 73% | 0.77 [0.62, 0.92] |  |
| prefixmax | 48 | 0.85 [0.71, 0.96] | 85% | 85% | 18% [0%, 40%] | 15% [0%, 36%] | 0.86 | 67% | 77% | 0.83 [0.71, 0.95] |  |
| s3 | 48 | 0.79 [0.62, 0.93] | 69% | 92% | 50% [19%, 80%] | 8% [0%, 25%] | 0.86 | 67% | 62% | 0.71 [0.55, 0.89] | re-fusion of champion |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| champion | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.2 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| facts_only | 0.55 | 0.70 | 0.70, 0.70, 0.70, 0.70 (FAR20: 0.95, 0.95, 0.95, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 4.0 | 1.6 | 0 | 0 | 795bb55852 |
| t045 | 0.45 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| t065 | 0.65 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| noesc | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| band025 | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 1.00, 1.00, 1.00, 1.00) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| table_v2 | 0.55 | 0.65 | 0.65, 0.35, 0.65, 0.70 (FAR20: 0.90!, 0.90!, 0.90!, 0.95!) | 0.2 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 795bb55852 |
| para | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25, 1.00!, 0.25!, 0.25) | 5.7 | asr 0.0, diarize 0.0, checks 5.7 | 5.8 | 21.4 | 0 | 0 | 3757224ef0 |
| table_v3 | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90, 0.90, 0.95) | 4.9 | asr 0.0, diarize 0.0, checks 4.9 | 4.9 | 10.0 | 0 | 0 | 3757224ef0 |
| para2 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 1.00, 1.00!, 1.00!, 1.00) | 5.2 | asr 0.0, diarize 0.0, checks 5.2 | 5.3 | 21.4 | 0 | 0 | 3d6c7bc1ac |
| ens2 | 0.55 | 0.20 | 0.20, 0.35, 0.20, 0.20 (FAR20: 0.20, 0.95, 0.20, 0.20) | 2.4 | asr 0.0, diarize 0.0, checks 2.4 | 2.5 | 1.4 | 0 | 0 | 3d6c7bc1ac |
| ens3 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.95, 0.95!, 0.95!, 0.95) | 2.1 | asr 0.0, diarize 0.0, checks 2.1 | 2.2 | 1.4 | 0 | 0 | 3d6c7bc1ac |
| ens3_d06 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.95, 0.95!, 0.95!, 0.95) | 2.2 | asr 0.0, diarize 0.0, checks 2.2 | 2.3 | 1.4 | 0 | 0 | 3d6c7bc1ac |
| ens3_band | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.95, 1.00, 0.95, 0.95) | 2.2 | asr 0.0, diarize 0.0, checks 2.2 | 2.3 | 1.4 | 0 | 0 | 3d6c7bc1ac |
| ens2b | 0.55 | 0.65 | 0.65, 0.35, 0.65, 0.65 (FAR20: 0.90, 0.95!, 0.90!, 0.90) | 2.4 | asr 0.0, diarize 0.0, checks 2.4 | 2.5 | 1.5 | 0 | 0 | 3d6c7bc1ac |
| ens_blind | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.90, 0.90!, 0.90!, 0.95) | 2.3 | asr 0.0, diarize 0.0, checks 2.3 | 2.4 | 1.3 | 0 | 0 | 3d6c7bc1ac |
| turbo_clean | 0.55 | 0.20 | 0.20, 0.35, 0.20, 0.20 (FAR20: 0.20, 0.90, 0.20, 0.20) | 32.7 | asr 15.0, diarize 12.9, checks 4.8 | 4.8 | 21.8 | 0 | 0 | afe1ba3164 |
| s1_v1_08 | 0.55 | 0.20 | 0.20, 0.65, 0.20, 0.20 (FAR20: 0.35, 0.90!, 0.35!, 0.35) | 1.9 | asr 0.0, diarize 0.0, checks 1.8 | 1.9 | 1.6 | 0 | 0 | 2a156c452d |
| s1_v3_08 | 0.55 | 0.20 | 0.20, 0.65, 0.20, 0.20 (FAR20: 0.35, 0.90!, 0.35!, 0.35) | 1.9 | asr 0.0, diarize 0.0, checks 1.9 | 2.0 | 2.0 | 0 | 0 | 2a156c452d |
| s1_para_08 | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25, 1.00!, 0.25!, 0.25) | 1.8 | asr 0.0, diarize 0.0, checks 1.7 | 1.8 | 1.4 | 0 | 0 | 2a156c452d |
| fs_tuned | 0.55 | 0.35 | 0.65, 0.35, 0.35, 0.35 (FAR20: 0.90, 0.90, 0.90, 0.95) | 7.8 | asr 0.0, diarize 0.0, checks 7.8 | 7.9 | 13.6 | 0 | 0 | fcffca5bee |
| fs_para | 0.55 | 0.20 | 0.20, 0.20, 0.25, 0.20 (FAR20: 0.20, 0.20!, 0.25!, 0.20) | 7.5 | asr 0.0, diarize 0.0, checks 7.4 | 7.5 | 13.2 | 0 | 0 | fcffca5bee |
| qlang_de | 0.55 | 0.20 | 0.20, 0.70, 0.20, 0.20 (FAR20: 0.20, 0.95, 0.20, 0.20) | 7.1 | asr 0.0, diarize 0.0, checks 7.1 | 7.1 | 21.2 | 0 | 0 | eed87b681e |
| noroles | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.70 (FAR20: 0.35, 0.35!, 0.35!, 1.00) | 7.4 | asr 0.0, diarize 0.0, checks 7.4 | 7.5 | 21.8 | 0 | 0 | eed87b681e |
| prefixmax | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 0.90, 0.90!, 0.90!, 0.95) | 6.5 | asr 0.0, diarize 0.0, checks 6.5 | 6.6 | 16.7 | 0 | 0 | eed87b681e |
| s3 | 0.55 | 0.65 | 0.65, 0.65, 0.65, 0.70 (FAR20: 1.00!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 0.2, diarize 0.0, checks 0.0 | 4.1 | 1.6 | 0 | 0 | 480479c79d |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| champion | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| facts_only | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| t045 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| t065 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| noesc | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| band025 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| table_v2 | 1.00 / 0% / 0% | 0.71 / 57% / 0% | 0.80 / - / 33% | 0.80 / 45% / 8% | 0.86 / 27% / 8% |
| para | 0.90 / 12% / 10% | 0.67 / 29% / 30% | 0.00 / - / 100% | 0.67 / 27% / 38% | 0.70 / 18% / 38% |
| table_v3 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 1.00 / - / 0% | 0.89 / 18% / 8% | 0.92 / 9% / 8% |
| para2 | 1.00 / 0% / 0% | 0.70 / 36% / 20% | 0.00 / - / 100% | 0.72 / 27% / 31% | 0.75 / 18% / 31% |
| ens2 | 1.00 / 0% / 0% | 0.70 / 21% / 30% | 0.50 / - / 67% | 0.80 / 18% / 23% | 0.78 / 9% / 31% |
| ens3 | 1.00 / 0% / 0% | 0.73 / 29% / 20% | 0.00 / - / 100% | 0.75 / 18% / 31% | 0.75 / 18% / 31% |
| ens3_d06 | 1.00 / 0% / 0% | 0.73 / 29% / 20% | 0.29 / - / 83% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| ens3_band | 1.00 / 0% / 0% | 0.67 / 14% / 40% | 0.00 / - / 100% | 0.73 / 9% / 38% | 0.73 / 9% / 38% |
| ens2b | 1.00 / 0% / 0% | 0.73 / 29% / 20% | 0.29 / - / 83% | 0.75 / 18% / 31% | 0.80 / 18% / 23% |
| ens_blind | 1.00 / 0% / 0% | 0.73 / 29% / 20% | 0.00 / - / 100% | 0.75 / 18% / 31% | 0.75 / 18% / 31% |
| turbo_clean | 0.95 / 0% / 10% | 0.70 / 21% / 30% | 0.80 / - / 33% | 0.83 / 9% / 23% | 0.80 / 18% / 23% |
| s1_v1_08 | 0.95 / 12% / 0% | 0.70 / 21% / 30% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.80 / 18% / 23% |
| s1_v3_08 | 0.95 / 12% / 0% | 0.70 / 21% / 30% | 1.00 / - / 0% | 0.89 / 18% / 8% | 0.85 / 18% / 15% |
| s1_para_08 | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.29 / - / 83% | 0.75 / 18% / 31% | 0.70 / 18% / 38% |
| fs_tuned | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.29 / - / 83% | 0.80 / 18% / 23% | 0.78 / 9% / 31% |
| fs_para | 0.95 / 0% / 10% | 0.60 / 29% / 40% | 0.00 / - / 100% | 0.64 / 18% / 46% | 0.70 / 18% / 38% |
| qlang_de | 0.82 / 0% / 30% | 0.76 / 21% / 20% | 0.00 / - / 100% | 0.70 / 18% / 38% | 0.67 / 9% / 46% |
| noroles | 0.95 / 0% / 10% | 0.60 / 29% / 40% | 0.80 / - / 33% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| prefixmax | 0.95 / 12% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.81 / 27% / 15% | 0.88 / 9% / 15% |
| s3 | 0.91 / 25% / 0% | 0.69 / 64% / 0% | 0.80 / - / 33% | 0.77 / 55% / 8% | 0.80 / 45% / 8% |

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

## `t045` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = t045 - champion

| metric | champion | t045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = t045 - champion

| metric | champion | t045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t045 0, p=1.0; 3-class only-champion 0 vs only-t045 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = t045 - champion

| metric | champion | t045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t045 0, p=1.0; 3-class only-champion 0 vs only-t045 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = t045 - champion

| metric | champion | t045 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.80 | -0.057 | [-0.226, +0.085] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-20pp, +11pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t045 0, p=1.0; 3-class only-champion 4 vs only-t045 3, p=1.0.

No call changes its label (cv).

## `t065` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = t065 - champion

| metric | champion | t065 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = t065 - champion

| metric | champion | t065 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t065 0, p=1.0; 3-class only-champion 0 vs only-t065 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = t065 - champion

| metric | champion | t065 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t065 0, p=1.0; 3-class only-champion 0 vs only-t065 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = t065 - champion

| metric | champion | t065 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-t065 0, p=1.0; 3-class only-champion 0 vs only-t065 0, p=1.0.

No call changes its label (cv).

## `noesc` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = noesc - champion

| metric | champion | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc - champion

| metric | champion | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-noesc 0, p=1.0; 3-class only-champion 0 vs only-noesc 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc - champion

| metric | champion | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 69% | 69% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-noesc 0, p=1.0; 3-class only-champion 0 vs only-noesc 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noesc - champion

| metric | champion | noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-noesc 0, p=1.0; 3-class only-champion 0 vs only-noesc 0, p=1.0.

No call changes its label (cv).

## `band025` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = band025 - champion

| metric | champion | band025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band025 - champion

| metric | champion | band025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-band025 0, p=1.0; 3-class only-champion 0 vs only-band025 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band025 - champion

| metric | champion | band025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.86 | +0.023 | [+0.000, +0.079] | no detectable difference |
| alarm_f1 | 0.67 | 0.18 | -0.485 | [-0.811, -0.174] | **real**: champion better |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 15% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 69% | 52% | -17pp | [-34pp, -5pp] | **real**: champion better |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.019 | [+0.000, +0.062] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-band025 1, p=1.0; 3-class only-champion 8 vs only-band025 0, p=0.0078.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = band025 - champion

| metric | champion | band025 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-band025 0, p=1.0; 3-class only-champion 0 vs only-band025 0, p=1.0.

No call changes its label (cv).

## `table_v2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = table_v2 - champion

| metric | champion | table_v2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.87 | +0.004 | [-0.104, +0.118] | no detectable difference |
| alarm AUC | 0.90 | 0.95 | +0.042 | [-0.035, +0.166] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v2 - champion

| metric | champion | table_v2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.035 | [-0.186, +0.077] | no detectable difference |
| alarm_f1 | 0.86 | 0.73 | -0.125 | [-0.330, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 36% | +23pp | [+0pp, +54pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 65% | -15pp | [-35pp, +0pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.78 | -0.075 | [-0.235, +0.038] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-table_v2 2, p=0.4531; 3-class only-champion 7 vs only-table_v2 0, p=0.0156.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v2 - champion

| metric | champion | table_v2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.81 | -0.033 | [-0.183, +0.084] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 36% | +23pp | [+0pp, +54pp] | no detectable difference |
| miss_rate | 19% | 12% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 69% | 58% | -10pp | [-27pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.76 | -0.075 | [-0.235, +0.038] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-table_v2 2, p=0.4531; 3-class only-champion 5 vs only-table_v2 0, p=0.0625.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v2 - champion

| metric | champion | table_v2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.83 | -0.035 | [-0.186, +0.077] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 36% | +23pp | [+0pp, +54pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 69% | -10pp | [-27pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.78 | -0.075 | [-0.235, +0.038] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-table_v2 2, p=0.4531; 3-class only-champion 5 vs only-table_v2 0, p=0.0625.

Flips (cv, 9 calls):

| call | expected | champion | table_v2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe2_C01-K3 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:55-02:03 access: Hier steht vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei vier zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt di... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 00:35-00:44 access: Im Formular war das Zahlungsmittel. Ich habe die Nummern von der Vorderseite meiner Karte übernommen, die ich online bezahle. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:55-02:03 access: Da steht vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.99... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:57-02:05 access: Da steht vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, vier, zwei, zwei, zwei, zwei. - facts: Fakt: Code/Wert am Telefon vorgelese... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.50 | fixed | 01:47-01:50 access: acht, drei, sechs, eins, sieben, vier - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Die Kundenin liest die Ziffern des Kundungsfelds laut. (Regel: access.review_2) | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.50 | fixed | 01:49-01:51 access: acht, drei, sechs, eins, sieben, vier. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.98) - Der Kunde las die Ziffern acht, drei, sechs, eins, sieben, vier laut. (Regel: ac... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.00/0.50 | broken | 01:44-01:50 access: Warte, ich lese Ihnen, wie ich es aus diesem Feld vorstelle. acht, drei, sechs, eins, sieben, vier. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.89) - Die Kundenin liest ... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.50 | same | 01:24-01:48 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. Bitte sagen Sie nur den Lesbowertakt. Die Zahl bleibt bei... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert ... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |

## `para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = para - champion

| metric | champion | para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.72 | -0.147 | [-0.313, -0.025] | **real**: champion better |
| alarm AUC | 0.90 | 0.88 | -0.025 | [-0.081, +0.033] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = para - champion

| metric | champion | para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.182 | [-0.361, -0.059] | **real**: champion better |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.287, +0.039] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-31pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.161 | [-0.288, -0.057] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-para 0, p=0.0078; 3-class only-champion 9 vs only-para 3, p=0.146.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = para - champion

| metric | champion | para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.68 | -0.159 | [-0.344, -0.014] | **real**: champion better |
| alarm_f1 | 0.67 | 0.72 | +0.051 | [-0.167, +0.318] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-4pp, +43pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-24pp, +14pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.69 | -0.142 | [-0.276, -0.021] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-para 1, p=0.0391; 3-class only-champion 8 vs only-para 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = para - champion

| metric | champion | para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.182 | [-0.361, -0.059] | **real**: champion better |
| alarm_f1 | 0.86 | 0.67 | -0.190 | [-0.444, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +23pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-38pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.69 | -0.161 | [-0.288, -0.057] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-para 0, p=0.0078; 3-class only-champion 11 vs only-para 0, p=0.001.

Flips (cv, 15 calls):

| call | expected | champion | para | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `table_v3` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = table_v3 - champion

| metric | champion | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.92 | +0.052 | [+0.000, +0.172] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | -0.009 | [-0.033, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v3 - champion

| metric | champion | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.91 | +0.043 | [+0.000, +0.142] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 83% | +4pp | [+0pp, +14pp] | no detectable difference |
| review_recall | 67% | 100% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.89 | +0.038 | [+0.000, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-table_v3 2, p=0.5; 3-class only-champion 0 vs only-table_v3 2, p=0.5.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v3 - champion

| metric | champion | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.88 | +0.045 | [+0.000, +0.156] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 12% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 69% | 73% | +4pp | [+0pp, +14pp] | no detectable difference |
| review_recall | 67% | 100% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.87 | +0.038 | [+0.000, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-table_v3 2, p=0.5; 3-class only-champion 0 vs only-table_v3 2, p=0.5.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = table_v3 - champion

| metric | champion | table_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.91 | +0.043 | [+0.000, +0.142] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 83% | +4pp | [+0pp, +14pp] | no detectable difference |
| review_recall | 67% | 100% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.89 | +0.038 | [+0.000, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-table_v3 2, p=0.5; 3-class only-champion 0 vs only-table_v3 2, p=0.5.

Flips (cv, 2 calls):

| call | expected | champion | table_v3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe3_C20-K3 | review | no_alert | review | 0.00/0.50 | fixed | 00:33-00:38 splitting: Wissen Sie, ob es eine einzige Lieferung oder unabhängige Rechnungen sind? - facts: Fakt: Im Gespräch offen, ob die Teilbeträge zusammengehören = ja (1.00) - Die Kunde sagt, das... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | review | 0.00/0.50 | fixed | 00:59-01:14 splitting: Sind das bestätigte Fälligkeiten? Das weiss ich auch nicht. Meine Kollegin hat die Daten so notiert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen e... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `para2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = para2 - champion

| metric | champion | para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.74 | -0.130 | [-0.290, -0.011] | **real**: champion better |
| alarm AUC | 0.90 | 0.90 | -0.003 | [-0.042, +0.040] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = para2 - champion

| metric | champion | para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.81 | -0.048 | [-0.132, +0.065] | no detectable difference |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-24pp, +4pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-para2 0, p=0.0312; 3-class only-champion 7 vs only-para2 3, p=0.3438.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = para2 - champion

| metric | champion | para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.73 | -0.105 | [-0.275, +0.030] | no detectable difference |
| alarm_f1 | 0.67 | 0.00 | -0.667 | [-0.875, -0.364] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-9pp, +36pp] | no detectable difference |
| accuracy | 69% | 35% | -33pp | [-52pp, -17pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.73 | -0.103 | [-0.227, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-para2 1, p=0.125; 3-class only-champion 16 vs only-para2 0, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = para2 - champion

| metric | champion | para2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.128 | [-0.286, -0.016] | **real**: champion better |
| alarm_f1 | 0.86 | 0.71 | -0.147 | [-0.269, -0.038] | **real**: champion better |
| false_alarm_rate | 14% | 23% | +9pp | [+0pp, +22pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 58% | -21pp | [-35pp, -9pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.73 | -0.122 | [-0.237, -0.019] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-para2 0, p=0.0312; 3-class only-champion 10 vs only-para2 0, p=0.002.

Flips (cv, 13 calls):

| call | expected | champion | para2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
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

## `ens2` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = ens2 - champion

| metric | champion | ens2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.81 | -0.058 | [-0.137, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [-0.023, +0.025] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens2 - champion

| metric | champion | ens2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.79 | -0.071 | [-0.154, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.78 | -0.077 | [-0.228, +0.076] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-24pp, +8pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.058 | [-0.125, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-ens2 0, p=0.25; 3-class only-champion 6 vs only-ens2 3, p=0.5078.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens2 - champion

| metric | champion | ens2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.79 | -0.048 | [-0.150, +0.044] | no detectable difference |
| alarm_f1 | 0.67 | 0.74 | +0.070 | [-0.167, +0.341] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-7pp, +23pp] | no detectable difference |
| accuracy | 69% | 71% | +2pp | [-17pp, +20pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.80 | -0.038 | [-0.115, +0.036] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-ens2 1, p=0.625; 3-class only-champion 5 vs only-ens2 6, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens2 - champion

| metric | champion | ens2 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.79 | -0.071 | [-0.154, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.171, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-17pp, -2pp] | **real**: champion better |
| review_recall | 67% | 33% | -33pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.058 | [-0.125, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-ens2 0, p=0.25; 3-class only-champion 4 vs only-ens2 0, p=0.125.

Flips (cv, 12 calls):

| call | expected | champion | ens2 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.77 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.08 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.08 ('Insiderhandel') liegt unter 0.20 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.72) - Die Kunde fragt nach der Gültigkeit ihrer Berechtigung z... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:54-08:03 documentation: Dann lässt mich der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts:... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:38 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (0.99) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert ... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fr... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `ens3` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = ens3 - champion

| metric | champion | ens3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.74 | -0.121 | [-0.284, -0.004] | **real**: champion better |
| alarm AUC | 0.90 | 0.91 | +0.006 | [-0.023, +0.044] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3 - champion

| metric | champion | ens3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.75 | -0.113 | [-0.277, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [-0.041, +0.086] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 75% | -4pp | [-20pp, +7pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.76 | -0.100 | [-0.214, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-ens3 0, p=0.0625; 3-class only-champion 5 vs only-ens3 3, p=0.7266.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3 - champion

| metric | champion | ens3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.75 | -0.090 | [-0.267, +0.042] | no detectable difference |
| alarm_f1 | 0.67 | 0.33 | -0.333 | [-0.667, -0.071] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-9pp, +36pp] | no detectable difference |
| accuracy | 69% | 46% | -23pp | [-38pp, -10pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.76 | -0.081 | [-0.203, +0.027] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-ens3 1, p=0.2188; 3-class only-champion 11 vs only-ens3 0, p=0.001.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3 - champion

| metric | champion | ens3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.75 | -0.113 | [-0.277, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.172, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 65% | -15pp | [-27pp, -4pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.76 | -0.100 | [-0.214, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-ens3 0, p=0.0625; 3-class only-champion 7 vs only-ens3 0, p=0.0156.

Flips (cv, 11 calls):

| call | expected | champion | ens3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.79) - Die Kunde fragt nach der Gültigkeit ihrer Berechtigung z... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.51) - Die Kunde fragt nach der Gültigkeit der Berechtigung zum... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:54-08:03 documentation: Dann lässt mich der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts:... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finan... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:02-08:07 documentation: Ich will, dass die Finanzierung das Ganze ausmacht. Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. - facts: Fakt: Verlangt, etwas n... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `ens3_d06` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = ens3_d06 - champion

| metric | champion | ens3_d06 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.77 | -0.095 | [-0.227, -0.004] | **real**: champion better |
| alarm AUC | 0.90 | 0.90 | +0.000 | [-0.026, +0.030] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3_d06 - champion

| metric | champion | ens3_d06 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.213, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.84 | -0.020 | [-0.097, +0.069] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 79% | 75% | -4pp | [-20pp, +7pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.179, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-ens3_d06 0, p=0.125; 3-class only-champion 5 vs only-ens3_d06 3, p=0.7266.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3_d06 - champion

| metric | champion | ens3_d06 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.78 | -0.065 | [-0.206, +0.045] | no detectable difference |
| alarm_f1 | 0.67 | 0.33 | -0.333 | [-0.667, -0.071] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [-9pp, +29pp] | no detectable difference |
| accuracy | 69% | 48% | -21pp | [-34pp, -8pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.77 | -0.061 | [-0.165, +0.031] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-ens3_d06 1, p=0.375; 3-class only-champion 10 vs only-ens3_d06 0, p=0.002.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3_d06 - champion

| metric | champion | ens3_d06 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.213, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.172, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 79% | 67% | -12pp | [-23pp, -4pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.179, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-ens3_d06 0, p=0.125; 3-class only-champion 6 vs only-ens3_d06 0, p=0.0312.

Flips (cv, 11 calls):

| call | expected | champion | ens3_d06 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.79) - Die Kunde fragt nach der Gültigkeit ihrer Berechtigung z... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = unklar (ja 0.51, nein 0.24) - Die Kunde fragt nach der Berechtigung ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.94) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finan... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:02-08:07 documentation: Ich will, dass die Finanzierung das Ganze ausmacht. Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. - facts: Fakt: Verlangt, etwas n... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fr... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `ens3_band` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = ens3_band - champion

| metric | champion | ens3_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.73 | -0.134 | [-0.294, -0.008] | **real**: champion better |
| alarm AUC | 0.90 | 0.89 | -0.017 | [-0.082, +0.038] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3_band - champion

| metric | champion | ens3_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.135 | [-0.337, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.78 | -0.079 | [-0.254, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-14pp, +0pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+0pp, +47pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-28pp, +4pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.76 | -0.093 | [-0.208, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-ens3_band 1, p=0.125; 3-class only-champion 6 vs only-ens3_band 2, p=0.2891.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3_band - champion

| metric | champion | ens3_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.70 | -0.142 | [-0.362, +0.020] | no detectable difference |
| alarm_f1 | 0.67 | 0.33 | -0.333 | [-0.667, -0.071] | **real**: champion better |
| false_alarm_rate | 14% | 9% | -5pp | [-14pp, +0pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [+0pp, +50pp] | no detectable difference |
| accuracy | 69% | 50% | -19pp | [-36pp, -4pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.74 | -0.093 | [-0.214, +0.019] | no detectable difference |

McNemar exact (calls): flag correct only-champion 7 vs only-ens3_band 2, p=0.1797; 3-class only-champion 10 vs only-ens3_band 1, p=0.0117.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens3_band - champion

| metric | champion | ens3_band | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.73 | -0.135 | [-0.337, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.71 | -0.147 | [-0.349, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 9% | -5pp | [-14pp, +0pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+0pp, +47pp] | no detectable difference |
| accuracy | 79% | 65% | -15pp | [-32pp, -2pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.76 | -0.093 | [-0.208, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-ens3_band 1, p=0.125; 3-class only-champion 8 vs only-ens3_band 1, p=0.0391.

Flips (cv, 12 calls):

| call | expected | champion | ens3_band | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D10-K1 | alarm | alarm | review | 0.93/0.30 | same | 01:02-01:03 splitting: Die Prüfung umgehen würde ich nicht unterstützen. - keywords: Stichwort K08 «Prüfung umgehen» (Kontrollumgehung) | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe1_D10-K2 | alarm | alarm | review | 0.80/0.37 | same | 01:35-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. (Regel: sp... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.79) - Die Kunde fragt nach der Gültigkeit ihrer Berechtigung z... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:10-00:16 disclosure: Ja, sie ist zurzeit im Spital und ich ordne mir dort Unterlagen. - facts: Fakt: Auskunft über Drittperson verlangt = unklar (ja 0.51, nein 0.24) - Die Kunde fragt nach der Heim... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.50/0.01 | broken | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.50/0.01 | broken | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.00 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `ens2b` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = ens2b - champion

| metric | champion | ens2b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.78 | -0.088 | [-0.220, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.91 | +0.009 | [-0.014, +0.036] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens2b - champion

| metric | champion | ens2b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.217, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.83 | -0.024 | [-0.090, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +30pp] | no detectable difference |
| accuracy | 79% | 69% | -10pp | [-24pp, +0pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.178, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-ens2b 0, p=0.125; 3-class only-champion 5 vs only-ens2b 0, p=0.0625.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens2b - champion

| metric | champion | ens2b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.75 | -0.090 | [-0.234, +0.028] | no detectable difference |
| alarm_f1 | 0.67 | 0.57 | -0.095 | [-0.268, +0.092] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [-7pp, +32pp] | no detectable difference |
| accuracy | 69% | 56% | -12pp | [-25pp, -2pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.76 | -0.081 | [-0.191, +0.021] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-ens2b 1, p=0.2188; 3-class only-champion 7 vs only-ens2b 1, p=0.0703.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens2b - champion

| metric | champion | ens2b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.217, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +30pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-20pp, +0pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.178, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-ens2b 0, p=0.125; 3-class only-champion 4 vs only-ens2b 0, p=0.125.

Flips (cv, 5 calls):

| call | expected | champion | ens2b | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe2_C14-K4 | no_alert | no_alert | review | 0.00/0.50 | broken | 08:02-08:07 documentation: Ich will, dass die Finanzierung das Ganze ausmacht. Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. - facts: Fakt: Verlangt, etwas n... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert ... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `ens_blind` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = ens_blind - champion

| metric | champion | ens_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.75 | -0.115 | [-0.275, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.91 | +0.008 | [-0.022, +0.046] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens_blind - champion

| metric | champion | ens_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.75 | -0.113 | [-0.277, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.83 | -0.028 | [-0.108, +0.075] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-23pp, +6pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.76 | -0.100 | [-0.214, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-ens_blind 0, p=0.0625; 3-class only-champion 6 vs only-ens_blind 3, p=0.5078.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens_blind - champion

| metric | champion | ens_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.72 | -0.117 | [-0.285, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.46 | -0.205 | [-0.470, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 35% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 69% | 50% | -19pp | [-33pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.74 | -0.100 | [-0.214, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 6 vs only-ens_blind 1, p=0.125; 3-class only-champion 9 vs only-ens_blind 0, p=0.0039.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = ens_blind - champion

| metric | champion | ens_blind | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.75 | -0.113 | [-0.277, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.217, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 31% | +15pp | [+0pp, +38pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-30pp, -6pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.76 | -0.100 | [-0.214, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 5 vs only-ens_blind 0, p=0.0625; 3-class only-champion 8 vs only-ens_blind 0, p=0.0078.

Flips (cv, 12 calls):

| call | expected | champion | ens_blind | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.77 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt laut den Ziffern der TAN-Card... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.94) - Die Kunde fragt nach der Berechtigung ihres Mutterkontos... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.55) - Der Kunde fragt nach der Heimrechnung und gibt an, dass ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:40 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:02-08:14 documentation: Ich will, dass die Finanzierung das Ganze ausmacht. Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusa... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `turbo_clean` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = turbo_clean - champion

| metric | champion | turbo_clean | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.85 | -0.017 | [-0.051, +0.018] | no detectable difference |
| alarm AUC | 0.90 | 0.87 | -0.033 | [-0.087, +0.002] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = turbo_clean - champion

| metric | champion | turbo_clean | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.046 | [-0.120, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.74 | -0.113 | [-0.302, +0.047] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [+0pp, +19pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-24pp, +8pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.82 | -0.038 | [-0.094, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-turbo_clean 1, p=0.625; 3-class only-champion 7 vs only-turbo_clean 4, p=0.5488.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = turbo_clean - champion

| metric | champion | turbo_clean | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.024 | [-0.112, +0.060] | no detectable difference |
| alarm_f1 | 0.67 | 0.78 | +0.114 | [-0.103, +0.384] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 23% | +4pp | [-9pp, +17pp] | no detectable difference |
| accuracy | 69% | 77% | +8pp | [-9pp, +25pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.82 | -0.019 | [-0.083, +0.047] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-turbo_clean 2, p=1.0; 3-class only-champion 4 vs only-turbo_clean 8, p=0.3877.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = turbo_clean - champion

| metric | champion | turbo_clean | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.046 | [-0.120, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.75 | -0.107 | [-0.268, +0.046] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 23% | +8pp | [+0pp, +19pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-14pp, +2pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.82 | -0.038 | [-0.094, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-turbo_clean 1, p=0.625; 3-class only-champion 5 vs only-turbo_clean 2, p=0.4531.

Flips (cv, 13 calls):

| call | expected | champion | turbo_clean | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.90/0.04 | broken | 02:05-02:17 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vollständigere Eigenmittelangabe zu erhalten. (Regel: document... |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.06 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.06 ('Insiderhandel') liegt unter 0.20 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:10-00:21 disclosure: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - facts: Fakt: ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:35-00:41 disclosure: Richtig, wir haben den Beleg des Heims und eine Liste der monatlichen Ausgaben. - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.87) - Die Kunde fragt nach den monatli... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 00:10-00:21 disclosure: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - facts: Fakt: ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:49-08:04 documentation: Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernte ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau die... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.95 | same | 07:48-08:14 documentation: Ja, sie meilen die violette Zeilen im aktuellen Zuf Sagen Sie mir bitte, was ich mit diesem Satz machen soll! Dann lernt man ja der Violette Mache ja den Satz aus dem Dossie... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.50/0.00 | fixed | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:07-08:22 documentation: Ich nehme ihren Wunsch auf, zusammen mit jener, als sie am Abend über den Satz gesagt haben. Der Entwurf geht jetzt nicht ungeprüft weiter, ich ändere am Telefon auch keine ... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.50 | same | 01:23-01:27 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sagen kann, ob der Wert... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder um dazugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert o... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 03:37-03:56 disclosure: Können Sie mir bis dahin wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.50 | same | 03:42-03:46 disclosure: Ob auf jedem Konto genug für die Wohnungskächtung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.99) - Die Kunde fragt nach, ob auf jedem Konto genug für die ... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `s1_v1_08` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = s1_v1_08 - champion

| metric | champion | s1_v1_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.86 | -0.007 | [-0.025, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.89 | -0.014 | [-0.050, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_v1_08 - champion

| metric | champion | s1_v1_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.039 | [-0.105, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.81 | -0.048 | [-0.197, +0.099] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 15% | 19% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-17pp, +11pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.81 | -0.042 | [-0.104, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-s1_v1_08 0, p=0.5; 3-class only-champion 4 vs only-s1_v1_08 3, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_v1_08 - champion

| metric | champion | s1_v1_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.017 | [-0.094, +0.055] | no detectable difference |
| alarm_f1 | 0.67 | 0.78 | +0.114 | [-0.073, +0.375] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [-12pp, +11pp] | no detectable difference |
| accuracy | 69% | 75% | +6pp | [-10pp, +23pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.81 | -0.023 | [-0.091, +0.038] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-s1_v1_08 1, p=1.0; 3-class only-champion 3 vs only-s1_v1_08 6, p=0.5078.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_v1_08 - champion

| metric | champion | s1_v1_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.82 | -0.039 | [-0.105, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.82 | -0.034 | [-0.111, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 15% | 19% | +4pp | [+0pp, +12pp] | no detectable difference |
| accuracy | 79% | 75% | -4pp | [-10pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.81 | -0.042 | [-0.104, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-s1_v1_08 0, p=0.5; 3-class only-champion 2 vs only-s1_v1_08 0, p=0.5.

Flips (cv, 10 calls):

| call | expected | champion | s1_v1_08 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.47 | broken | 00:12-00:21 disclosure: Ja, ich bin Seite Generalversammlung Kassierin. Ich habe eine Liste von Zahlen gegeben, aber mein Vorgänger hat noch den Ordner mit dem Beleg. - facts: Fakt: Vollmacht/Auskunft... | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.24 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.24 ('Insiderhandel') liegt unter 0.50 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:54-08:03 documentation: Dann lässt mich der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts:... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fr... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.50 | same | 02:07-02:12 disclosure: Rechnungsperiode. Ich kann sie heute Abend erreichen und in die richtige Rechnung benennen. - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `s1_v3_08` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = s1_v3_08 - champion

| metric | champion | s1_v3_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.91 | +0.045 | [-0.019, +0.166] | no detectable difference |
| alarm AUC | 0.90 | 0.88 | -0.027 | [-0.078, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_v3_08 - champion

| metric | champion | s1_v3_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.005 | [-0.084, +0.120] | no detectable difference |
| alarm_f1 | 0.86 | 0.77 | -0.084 | [-0.267, +0.071] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-22pp, +10pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-17pp, +11pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | -0.004 | [-0.085, +0.093] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-s1_v3_08 2, p=1.0; 3-class only-champion 4 vs only-s1_v3_08 3, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_v3_08 - champion

| metric | champion | s1_v3_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.87 | +0.028 | [-0.076, +0.153] | no detectable difference |
| alarm_f1 | 0.67 | 0.74 | +0.077 | [-0.144, +0.338] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 19% | 12% | -8pp | [-27pp, +8pp] | no detectable difference |
| accuracy | 69% | 75% | +6pp | [-10pp, +23pp] | no detectable difference |
| review_recall | 67% | 33% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.85 | +0.016 | [-0.076, +0.117] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-s1_v3_08 3, p=1.0; 3-class only-champion 3 vs only-s1_v3_08 6, p=0.5078.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_v3_08 - champion

| metric | champion | s1_v3_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.87 | +0.005 | [-0.084, +0.120] | no detectable difference |
| alarm_f1 | 0.86 | 0.82 | -0.034 | [-0.111, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-22pp, +10pp] | no detectable difference |
| accuracy | 79% | 79% | +0pp | [-9pp, +11pp] | no detectable difference |
| review_recall | 67% | 100% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.85 | -0.004 | [-0.085, +0.093] | no detectable difference |

McNemar exact (calls): flag correct only-champion 2 vs only-s1_v3_08 2, p=1.0; 3-class only-champion 2 vs only-s1_v3_08 2, p=1.0.

Flips (cv, 12 calls):

| call | expected | champion | s1_v3_08 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.47 | broken | 00:12-00:21 disclosure: Ja, ich bin Seite Generalversammlung Kassierin. Ich habe eine Liste von Zahlen gegeben, aber mein Vorgänger hat noch den Ordner mit dem Beleg. - facts: Fakt: Vollmacht/Auskunft... | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.24 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.24 ('Insiderhandel') liegt unter 0.50 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:54-08:03 documentation: Dann lässt mich der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts:... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finan... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 00:45-00:49 disclosure: Ich kann keine bestätigte Berechtigung für genau ihr Konto vorweisen. - facts: Fakt: Im Gespräch offen, ob eine Berechtigung besteht = ja (0.99) - Die Kunde sagt, sie kann kein... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.50 | same | 00:45-00:50 disclosure: Ich habe keine Bestätigung der Berechtigung für genau Ihr Konto vorweisen. - facts: Fakt: Im Gespräch offen, ob eine Berechtigung besteht = ja (1.00) - Die Kunde sagt, sie habe... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |
| Stufe3_C20-K3 | review | no_alert | alarm | 0.00/0.50 | fixed | 00:33-00:38 splitting: Wissen Sie, ob es eine einzige Lieferung oder unabhängige Rechnungen sind? - facts: Fakt: Im Gespräch offen, ob die Teilbeträge zusammengehören = ja (1.00) - Die Kunde sagt, das... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C20-K4 | review | no_alert | alarm | 0.00/0.50 | fixed | 00:59-01:14 splitting: Sind das bestätigte Fälligkeiten? Das weiss ich auch nicht. Meine Kollegin hat die Daten so notiert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen e... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## `s1_para_08` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = s1_para_08 - champion

| metric | champion | s1_para_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.74 | -0.129 | [-0.260, -0.016] | **real**: champion better |
| alarm AUC | 0.90 | 0.85 | -0.052 | [-0.133, +0.020] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_para_08 - champion

| metric | champion | s1_para_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.72 | -0.139 | [-0.281, -0.039] | **real**: champion better |
| alarm_f1 | 0.86 | 0.68 | -0.173 | [-0.413, +0.014] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 35% | +19pp | [+4pp, +38pp] | **real**: champion better |
| accuracy | 79% | 65% | -15pp | [-33pp, +0pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.74 | -0.119 | [-0.212, -0.036] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 6 vs only-s1_para_08 0, p=0.0312; 3-class only-champion 10 vs only-s1_para_08 3, p=0.0923.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_para_08 - champion

| metric | champion | s1_para_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.70 | -0.144 | [-0.326, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.68 | +0.018 | [-0.226, +0.312] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 38% | +19pp | [-3pp, +43pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-23pp, +14pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.72 | -0.119 | [-0.237, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 7 vs only-s1_para_08 1, p=0.0703; 3-class only-champion 8 vs only-s1_para_08 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s1_para_08 - champion

| metric | champion | s1_para_08 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.70 | -0.167 | [-0.339, -0.043] | **real**: champion better |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.602, -0.057] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 38% | +23pp | [+4pp, +45pp] | **real**: champion better |
| accuracy | 79% | 56% | -23pp | [-38pp, -10pp] | **real**: champion better |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.138 | [-0.247, -0.038] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 7 vs only-s1_para_08 0, p=0.0156; 3-class only-champion 11 vs only-s1_para_08 0, p=0.001.

Flips (cv, 16 calls):

| call | expected | champion | s1_para_08 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | no_alert | 0.91/0.13 | broken | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Kein Alarm: höchster Score 0.13 ('Zugangsinformation preisgegeben') liegt unter 0.20 (Schwelle 0.35 min... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.28 | same | 01:18-01:25 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort ... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K2 | alarm | alarm | review | 0.93/0.30 | same | 02:39-02:41 documentation: Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C07-K3 | alarm | alarm | review | 0.97/0.26 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.00 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Richtig? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.95) - Die Kunde fragt nach der Berechtigung ihres Mutterkontos... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Es geht um das persönliche Konto ihrer Mutter. Wichtig? - facts: Fakt: Auskunft über Drittperson verlangt = unklar (ja 0.55, nein 0.35) - Der Kunde fragt nach der Berechtigung ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:43-03:53 documentation: Dann sollte im Entwurf nicht stehen. Der Termin sei schon abgemacht. Wir können notieren, welche Woche Sie gerne hätten und lassen den Termin offen. - facts: Fakt: Verlangt,... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:44 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:02-08:14 documentation: Ich will, dass die Finanzierung das Ganze ausmacht. Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusa... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 00:10-00:33 disclosure: Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann m... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `fs_tuned` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = fs_tuned - champion

| metric | champion | fs_tuned | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.80 | -0.067 | [-0.198, +0.014] | no detectable difference |
| alarm AUC | 0.90 | 0.92 | +0.017 | [+0.000, +0.049] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = fs_tuned - champion

| metric | champion | fs_tuned | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.79 | -0.071 | [-0.201, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.068 | [-0.157, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-24pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.058 | [-0.146, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-fs_tuned 0, p=0.25; 3-class only-champion 5 vs only-fs_tuned 1, p=0.2188.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = fs_tuned - champion

| metric | champion | fs_tuned | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.77 | -0.074 | [-0.208, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 31% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 69% | 62% | -6pp | [-17pp, +0pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.78 | -0.058 | [-0.146, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-fs_tuned 0, p=0.25; 3-class only-champion 3 vs only-fs_tuned 0, p=0.25.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = fs_tuned - champion

| metric | champion | fs_tuned | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.79 | -0.071 | [-0.201, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.82 | -0.034 | [-0.111, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 79% | 71% | -8pp | [-20pp, +0pp] | no detectable difference |
| review_recall | 67% | 17% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.80 | -0.058 | [-0.146, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 3 vs only-fs_tuned 0, p=0.25; 3-class only-champion 4 vs only-fs_tuned 0, p=0.125.

Flips (cv, 8 calls):

| call | expected | champion | fs_tuned | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.79 | same | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Wert... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fr... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `fs_para` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = fs_para - champion

| metric | champion | fs_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.70 | -0.167 | [-0.333, -0.027] | **real**: champion better |
| alarm AUC | 0.90 | 0.85 | -0.056 | [-0.168, +0.036] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = fs_para - champion

| metric | champion | fs_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.67 | -0.196 | [-0.401, -0.054] | **real**: champion better |
| alarm_f1 | 0.86 | 0.70 | -0.154 | [-0.391, +0.040] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+7pp, +53pp] | **real**: champion better |
| accuracy | 79% | 65% | -15pp | [-33pp, +0pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.70 | -0.157 | [-0.281, -0.046] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-fs_para 0, p=0.0078; 3-class only-champion 10 vs only-fs_para 3, p=0.0923.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = fs_para - champion

| metric | champion | fs_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.67 | -0.173 | [-0.389, -0.014] | **real**: champion better |
| alarm_f1 | 0.67 | 0.70 | +0.036 | [-0.199, +0.333] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [+0pp, +50pp] | no detectable difference |
| accuracy | 69% | 65% | -4pp | [-24pp, +13pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.70 | -0.138 | [-0.273, -0.018] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 8 vs only-fs_para 1, p=0.0391; 3-class only-champion 8 vs only-fs_para 6, p=0.7905.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = fs_para - champion

| metric | champion | fs_para | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.64 | -0.226 | [-0.437, -0.082] | **real**: champion better |
| alarm_f1 | 0.86 | 0.57 | -0.286 | [-0.589, -0.062] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 46% | +31pp | [+10pp, +56pp] | **real**: champion better |
| accuracy | 79% | 54% | -25pp | [-40pp, -11pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.68 | -0.177 | [-0.295, -0.068] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 9 vs only-fs_para 0, p=0.0039; 3-class only-champion 12 vs only-fs_para 0, p=0.0005.

Flips (cv, 16 calls):

| call | expected | champion | fs_para | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D04-K1 | alarm | alarm | no_alert | 0.99/0.09 | broken | 03:13-03:24 trade: Hat sie Ihnen gesagt, dass sie diese Informationen brauchen oder weitergeben dürfen? Sie hat gesagt, das bleibe unter uns. Ich habe das auch nicht weiter erzählt. - Kein Alarm: höch... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass sie die Informationen von ihrer Kollegin persönlich erhalten hat, die unter uns bleiben sollen. ... |
| Stufe1_D05-K1 | alarm | alarm | review | 0.91/0.13 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «TAN» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | review | 0.90/0.71 | same | 01:18-01:25 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.72) - Der Kunde gibt de... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe2_C07-K3 | alarm | alarm | no_alert | 0.97/0.02 | broken | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der erst morgen an das Team wei... |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.00 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') ... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:52 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 08:23-08:49 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 01:02-01:38 documentation: Wir müssen zuerst wissen, ob diese Sache wichtig und für den vorgesehenen Empfänger nötig ist. Der violette Satz hat meine alte Kontaktadresse. Die ist falsch und für den vo... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 08:02-08:07 documentation: Ich will, dass die Finanzierung das Ganze ausmacht. Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. - facts: Fakt: Verlangt, etwas n... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `qlang_de` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qlang_de - champion

| metric | champion | qlang_de | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.73 | -0.134 | [-0.294, -0.010] | **real**: champion better |
| alarm AUC | 0.90 | 0.90 | -0.006 | [-0.058, +0.047] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qlang_de - champion

| metric | champion | qlang_de | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.181 | [-0.404, -0.035] | **real**: champion better |
| alarm_f1 | 0.86 | 0.79 | -0.068 | [-0.255, +0.106] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+5pp, +50pp] | **real**: champion better |
| accuracy | 79% | 71% | -8pp | [-29pp, +7pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.135 | [-0.250, -0.025] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 7 vs only-qlang_de 0, p=0.0156; 3-class only-champion 7 vs only-qlang_de 3, p=0.3438.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qlang_de - champion

| metric | champion | qlang_de | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.68 | -0.158 | [-0.392, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.79 | +0.123 | [-0.094, +0.400] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 19% | 42% | +23pp | [+0pp, +50pp] | no detectable difference |
| accuracy | 69% | 71% | +2pp | [-20pp, +20pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.72 | -0.115 | [-0.250, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 7 vs only-qlang_de 1, p=0.0703; 3-class only-champion 6 vs only-qlang_de 7, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qlang_de - champion

| metric | champion | qlang_de | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.68 | -0.181 | [-0.404, -0.035] | **real**: champion better |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.267, +0.082] | no detectable difference |
| false_alarm_rate | 14% | 14% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 15% | 42% | +27pp | [+5pp, +50pp] | **real**: champion better |
| accuracy | 79% | 67% | -12pp | [-30pp, +0pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.72 | -0.135 | [-0.250, -0.025] | **real**: champion better |

McNemar exact (calls): flag correct only-champion 7 vs only-qlang_de 0, p=0.0156; 3-class only-champion 7 vs only-qlang_de 1, p=0.0703.

Flips (cv, 13 calls):

| call | expected | champion | qlang_de | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | no_alert | 0.91/0.08 | broken | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - Kein Alarm: höchster Score 0.08 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 min... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Regel: access.alarm_1) |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.90/0.24 | broken | 01:18-01:29 access: Warte, ich sage Ihnen den TAN-Card. Sieben, drei, eins, neun, vier, zwei. Es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - Kein Alarm: höchs... | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.93/0.02 | broken | 02:48-02:54 documentation: Ich will, dass ich nur Eigenmittel sehe und die Vereinbarung meiner Tante gar nicht erfahre. - Kein Alarm: höchster Score 0.02 ('Relevante Angabe verschweigen') liegt unter ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird und dass er nur Eigenmittel sieht. (Regel: documentation.al... |
| Stufe2_C11-K3 | no_alert | review | alarm | 0.50/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C11-K4 | no_alert | review | alarm | 0.50/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an die Klientin weiter. (Regel: disclosure.review_1) |
| Stufe2_C12-K3 | alarm | review | alarm | 0.50/0.85 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Konto hat. Die familiäre Beziehung allein lernt da nichts. - facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (1.00... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Franken an die Anruferin preis. (Regel: disclosure.review_1) |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-08:03 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | alarm | 0.50/0.50 | same | 07:41-07:55 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Regula Bachmann bittet die Finanzierungsstelle, den Inhalt eines bestimmt... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe3_C17-K3 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | no_alert | 0.50/0.00 | broken | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | no_alert | 0.50/0.00 | broken | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwel... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | no_alert | 0.50/0.00 | broken | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `noroles` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = noroles - champion

| metric | champion | noroles | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.81 | -0.060 | [-0.151, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.83 | -0.076 | [-0.174, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noroles - champion

| metric | champion | noroles | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.185, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.70 | -0.157 | [-0.332, -0.037] | **real**: champion better |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +23pp] | no detectable difference |
| accuracy | 79% | 67% | -12pp | [-27pp, -2pp] | **real**: champion better |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.168, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-noroles 0, p=0.125; 3-class only-champion 7 vs only-noroles 1, p=0.0703.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noroles - champion

| metric | champion | noroles | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.78 | -0.065 | [-0.157, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.56 | -0.111 | [-0.364, +0.084] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 19% | 27% | +8pp | [+0pp, +19pp] | no detectable difference |
| accuracy | 69% | 58% | -10pp | [-26pp, +2pp] | no detectable difference |
| review_recall | 67% | 0% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.77 | -0.061 | [-0.154, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-noroles 1, p=0.375; 3-class only-champion 7 vs only-noroles 2, p=0.1797.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = noroles - champion

| metric | champion | noroles | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.78 | -0.087 | [-0.185, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.79 | -0.069 | [-0.172, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +14pp] | no detectable difference |
| miss_rate | 15% | 27% | +12pp | [+0pp, +23pp] | no detectable difference |
| accuracy | 79% | 73% | -6pp | [-12pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.77 | -0.080 | [-0.168, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 4 vs only-noroles 0, p=0.125; 3-class only-champion 3 vs only-noroles 0, p=0.25.

Flips (cv, 10 calls):

| call | expected | champion | noroles | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.93/0.20 | broken | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu umgehen. (Regel: splitting.alarm_1) |
| Stufe2_C07-K4 | alarm | alarm | no_alert | 0.84/0.01 | broken | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - Kein Alarm: höchster Score 0.01 ('Insiderhandel') liegt unter 0.05 (... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.99) - Die Kunde erwähnt, dass ihre Cousine ihr den neuen Absatzbericht persönlich gezeigt hat, der noch nicht öffentlich ist. ... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.50/0.50 | same | 07:38-07:58 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Regula Bachmann fordert, dass ein bestimmter Satz aus dem Dossier herausgelassen wird. (Regel: documentation.review_1) |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.50/0.00 | broken | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. (Regel: documentation.revie... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.50/0.50 | same | 00:40-00:41 documentation: Haben Sie diese zwei von sich? - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.96) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finan... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.86) - Regula Bachmann möchte, dass der Inhalt eines bestimmten Satzes vom Finanzierungsstelle nicht zu sehen ist. (Regel: documentation.rev... |
| Stufe2_C14-K4 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:10-01:30 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Die aktuelle Adresse steht richtig im Kontaktfeld. Die... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C17-K3 | review | review | alarm | 0.50/0.50 | same | 01:24-01:27 access: Ich weiss nicht, ob der Wert oben oder unten dazugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wer... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten dazugehört und ob der Wert jetzt oder damals gültig ist. (Reg... |
| Stufe3_C17-K4 | review | review | alarm | 0.50/0.50 | same | 01:24-01:28 access: Ich weiss nicht, ob der Wert oben oder unten zugehört. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Gesprächspartner sagt, dass er nicht sicher ist, o... | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten zugehört, und dass er nicht weiß, ob der Wert jetzt oder dama... |
| Stufe3_C18-K3 | review | review | alarm | 0.50/0.50 | same | 00:29-00:33 disclosure: Was hat ihre Schwester für den Kontakt hinterlegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Gesprächspartnerin fragt nach der Berechtigung für eine A... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand ihrer Schwester, was als Auskunft an Dritte zählt. (Regel: disclosure.review_2) |
| Stufe3_C18-K4 | review | review | alarm | 0.50/0.50 | same | 02:43-02:48 disclosure: Es könnte ja sein, dass ich im Notfall eine Rechnung für Sie vorstecke. - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Gesprächspartnerin fragt nach dem Ko... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kunde fragt nach dem Kontostand für die Wohnungstechnik, was eine Auskunft an Dritte ist. (Regel: disclosure.review_2) |

## `prefixmax` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = prefixmax - champion

| metric | champion | prefixmax | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.87 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = prefixmax - champion

| metric | champion | prefixmax | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.85 | -0.017 | [-0.062, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.83 | -0.023 | [-0.075, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 1 vs only-prefixmax 0, p=1.0; 3-class only-champion 1 vs only-prefixmax 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = prefixmax - champion

| metric | champion | prefixmax | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.82 | -0.017 | [-0.061, +0.000] | no detectable difference |
| alarm_f1 | 0.67 | 0.67 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 19% | 19% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 69% | 67% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.81 | -0.023 | [-0.075, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 1 vs only-prefixmax 0, p=1.0; 3-class only-champion 1 vs only-prefixmax 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = prefixmax - champion

| metric | champion | prefixmax | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.85 | -0.017 | [-0.062, +0.000] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 18% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 79% | 77% | -2pp | [-7pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.83 | -0.023 | [-0.075, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 1 vs only-prefixmax 0, p=1.0; 3-class only-champion 1 vs only-prefixmax 0, p=1.0.

Flips (cv, 1 calls):

| call | expected | champion | prefixmax | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.47 | broken | 02:40-02:51 disclosure: Für das bestätigte Vereinskonto ist der Stand am 31. März 14.200 Franken. Die gleiche Zahl steht im Dokument, das ich Ihnen bereitstelle. - facts: Fakt: Konkrete Daten einer Dr... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |

## `s3` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = s3 - champion

| metric | champion | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.87 | 0.89 | +0.023 | [-0.031, +0.098] | no detectable difference |
| alarm AUC | 0.90 | 0.94 | +0.037 | [+0.000, +0.118] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s3 - champion

| metric | champion | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.79 | -0.076 | [-0.223, +0.022] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +70pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-36pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.71 | -0.143 | [-0.300, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-s3 2, p=0.1094; 3-class only-champion 8 vs only-s3 0, p=0.0078.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s3 - champion

| metric | champion | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.79 | -0.053 | [-0.202, +0.059] | no detectable difference |
| alarm_f1 | 0.67 | 0.18 | -0.485 | [-0.811, -0.174] | **real**: champion better |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +70pp] | no detectable difference |
| miss_rate | 19% | 8% | -12pp | [-30pp, +0pp] | no detectable difference |
| accuracy | 69% | 35% | -33pp | [-55pp, -15pp] | **real**: champion better |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.84 | 0.71 | -0.124 | [-0.280, +0.018] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-s3 3, p=0.2266; 3-class only-champion 16 vs only-s3 0, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = s3 - champion

| metric | champion | s3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.86 | 0.79 | -0.076 | [-0.223, +0.022] | no detectable difference |
| alarm_f1 | 0.86 | 0.86 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 14% | 50% | +36pp | [+0pp, +70pp] | no detectable difference |
| miss_rate | 15% | 8% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 79% | 62% | -17pp | [-36pp, +0pp] | no detectable difference |
| review_recall | 67% | 67% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.85 | 0.71 | -0.143 | [-0.300, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 8 vs only-s3 2, p=0.1094; 3-class only-champion 8 vs only-s3 0, p=0.0078.

Flips (cv, 10 calls):

| call | expected | champion | s3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D08-K1 | no_alert | no_alert | review | 0.02/0.62 | broken | «Auskunft an Dritte»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Stichwort K11; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe1_D08-K2 | no_alert | no_alert | review | 0.03/0.62 | broken | «Auskunft an Dritte»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Konkrete Daten einer Drittperson herausgegeben» p(ja) = 0.91; Stichwort K11; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Stufe2_C01-K3 | no_alert | no_alert | review | 0.00/0.57 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C01-K4 | no_alert | no_alert | review | 0.00/0.57 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K3 | no_alert | no_alert | review | 0.00/0.57 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.99; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C02-K4 | no_alert | no_alert | review | 0.00/0.57 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.00/0.57 | fixed | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 1.00; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.00/0.57 | fixed | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.98; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.00/0.57 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.89; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.00/0.57 | broken | «Zugangsinformation preisgegeben»: Handlung möglich, aber nicht entkräftet – bitte prüfen (Fakt «Code/Wert am Telefon vorgelesen» p(ja) = 0.42; keine entlastende Tatsache). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

