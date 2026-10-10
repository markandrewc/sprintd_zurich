# Experiment `llm_models`

Check LLM sweep (Qwen2.5-7B-AWQ vs Qwen3-8B-AWQ vs Qwen2.5-14B-AWQ vs Qwen3-14B-AWQ)

RQ: RQ6 · base profile `llm-sweep` · split **dev** · baseline `qwen25_7b` · commit f0b67b02fc (dirty) · 2026-10-10T04:52:45+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Warnings

- `qwen25_7b__kwpat_facts`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T01:59:06+0200): rerun this variant
- `qwen25_7b__facts_only`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T01:59:06+0200): rerun this variant
- `qwen25_7b__judge_facts`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T01:59:07+0200): rerun this variant
- `qwen25_7b__gcot`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T01:59:08+0200): rerun this variant
- `qwen25_7b__all_plus`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T01:59:09+0200): rerun this variant
- `qwen25_7b__hybrid`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T02:00:49+0200): rerun this variant
- `qwen25_7b__hybrid_kw`: source `qwen25_7b` was re-run (2026-10-10T04:00:10+0200) after this re-fusion (2026-10-10T02:00:50+0200): rerun this variant
- `qwen25_7b__facts_kwlight`: source `qwen25_7b` changed after this re-fusion (results hash 2a38db12edaf6ccb -> 6398556cb7d2afeb): rerun this variant
- `qwen25_7b__facts_kwlight_noesc`: source `qwen25_7b` changed after this re-fusion (results hash 2a38db12edaf6ccb -> 6398556cb7d2afeb): rerun this variant
- `qwen25_7b__facts_noesc`: source `qwen25_7b` changed after this re-fusion (results hash 2a38db12edaf6ccb -> 6398556cb7d2afeb): rerun this variant

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| qwen25_7b | 0.68 [0.53, 0.84] | 0.79 [0.65, 0.95] | 26/22 |  |
| qwen3_8b | 0.64 [0.44, 0.82] | 0.79 [0.64, 0.94] | 26/22 | **DEGRADED** |
| qwen25_7b__kwpat_facts | 0.79 [0.63, 0.92] | 0.87 [0.72, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_only | 0.84 [0.70, 0.95] | 0.89 [0.75, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__judge_facts | 0.76 [0.62, 0.90] | 0.84 [0.69, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__gcot | 0.65 [0.46, 0.84] | 0.76 [0.57, 0.96] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__all_plus | 0.75 [0.58, 0.92] | 0.85 [0.66, 1.00] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__kwpat_facts | 0.66 [0.48, 0.85] | 0.79 [0.60, 0.97] | 26/22 | re-fusion of qwen3_8b |
| qwen3_8b__facts_only | 0.74 [0.59, 0.88] | 0.83 [0.67, 0.97] | 26/22 | re-fusion of qwen3_8b |
| qwen3_8b__judge_facts | 0.76 [0.58, 0.92] | 0.92 [0.82, 1.00] | 26/22 | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__gcot | 0.67 [0.49, 0.83] | 0.77 [0.62, 0.91] | 26/22 | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__all_plus | 0.73 [0.55, 0.89] | 0.88 [0.75, 0.99] | 26/22 | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__hybrid | 0.82 [0.69, 0.94] | 0.88 [0.74, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__hybrid_kw | 0.76 [0.61, 0.90] | 0.85 [0.70, 0.97] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__hybrid | 0.76 [0.60, 0.92] | 0.79 [0.60, 0.95] | 26/22 | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__hybrid_kw | 0.70 [0.53, 0.89] | 0.69 [0.50, 0.88] | 26/22 | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__facts_blind_only | 0.73 [0.57, 0.88] | 0.79 [0.63, 0.93] | 26/22 | re-fusion of qwen25_7b |
| qwen3_8b__facts_blind_only | 0.67 [0.53, 0.82] | 0.69 [0.53, 0.86] | 26/22 | re-fusion of qwen3_8b |
| qwen25_14b_facts | 0.87 [0.76, 0.96] | 0.91 [0.78, 0.99] | 26/22 |  |
| qwen25_14b_facts__blind_only | 0.77 [0.62, 0.91] | 0.79 [0.62, 0.93] | 26/22 | re-fusion of qwen25_14b_facts |
| qwen25_7b__facts_kwlight | 0.80 [0.65, 0.94] | 0.87 [0.72, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_kwlight_noesc | 0.80 [0.65, 0.94] | 0.87 [0.72, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_noesc | 0.84 [0.70, 0.95] | 0.89 [0.75, 0.98] | 26/22 | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_14b_facts_l3 | 0.85 [0.73, 0.96] | 0.90 [0.77, 0.99] | 26/22 |  |
| qwen25_14b_facts_oracle | 0.90 [0.79, 1.00] | 0.91 [0.77, 1.00] | 26/22 | **ORACLE** |
| qwen25_7b_facts_l3 | 0.89 [0.77, 0.99] | 0.92 [0.78, 1.00] | 26/22 |  |
| qwen25_7b_facts_oracle | 0.76 [0.56, 0.92] | 0.81 [0.61, 0.97] | 26/22 | **ORACLE** |
| qwen25_14b_facts__blind_review | 0.87 [0.76, 0.97] | 0.88 [0.74, 0.99] | 26/22 | re-fusion of qwen25_14b_facts |
| qwen25_7b_facts_en | 0.82 [0.68, 0.95] | 0.90 [0.75, 1.00] | 26/22 |  |
| qwen25_14b_facts_l3__blind_only | 0.85 [0.72, 0.96] | 0.84 [0.69, 0.96] | 26/22 | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts_l3__both | 0.87 [0.76, 0.97] | 0.89 [0.74, 0.99] | 26/22 | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts__both | 0.88 [0.77, 0.98] | 0.90 [0.76, 1.00] | 26/22 | re-fusion of qwen25_14b_facts |
| qwen25_14b_facts_oracle__blind_only | 0.78 [0.64, 0.92] | 0.85 [0.70, 0.99] | 26/22 | **ORACLE**, re-fusion of qwen25_14b_facts_oracle |
| qwen25_7b__both | 0.82 [0.67, 0.95] | 0.85 [0.70, 0.97] | 26/22 | re-fusion of qwen25_7b |
| qwen25_7b_facts_l3__blind_only | 0.79 [0.63, 0.93] | 0.85 [0.70, 0.97] | 26/22 | re-fusion of qwen25_7b_facts_l3 |
| qwen25_7b_facts_l3__both | 0.85 [0.71, 0.98] | 0.89 [0.73, 1.00] | 26/22 | re-fusion of qwen25_7b_facts_l3 |
| qwen25_14b_para_l3 | 0.88 [0.76, 0.98] | 0.94 [0.86, 0.99] | 26/22 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen25_7b | 48 | 0.66 [0.49, 0.79] | 54% | 85% | 86% [64%, 100%] | 15% [0%, 35%] | 0.49 | 83% | 38% | 0.49 [0.42, 0.57] |  |
| qwen3_8b | 48 | 0.70 [0.56, 0.83] | 54% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.50 | 100% | 27% | 0.50 [0.50, 0.50] | **DEGRADED** |
| qwen25_7b__kwpat_facts | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.52 | 50% | 58% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_only | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.75 | 33% | 73% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__judge_facts | 48 | 0.76 [0.60, 0.89] | 69% | 85% | 45% [17%, 71%] | 15% [0%, 36%] | 0.79 | 67% | 60% | 0.70 [0.56, 0.85] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__gcot | 48 | 0.72 [0.58, 0.84] | 61% | 88% | 68% [50%, 85%] | 12% [0%, 23%] | 0.44 | 67% | 35% | 0.60 [0.51, 0.71] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__all_plus | 48 | 0.68 [0.51, 0.81] | 56% | 85% | 77% [62%, 91%] | 15% [0%, 33%] | 0.71 | 67% | 42% | 0.54 [0.45, 0.62] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__kwpat_facts | 48 | 0.63 [0.37, 0.83] | 87% | 50% | 9% [0%, 31%] | 50% [23%, 77%] | 0.46 | 0% | 54% | 0.70 [0.58, 0.84] | re-fusion of qwen3_8b |
| qwen3_8b__facts_only | 48 | 0.63 [0.37, 0.83] | 87% | 50% | 9% [0%, 31%] | 50% [23%, 77%] | 0.74 | 0% | 69% | 0.70 [0.58, 0.84] | re-fusion of qwen3_8b |
| qwen3_8b__judge_facts | 48 | 0.74 [0.59, 0.86] | 60% | 96% | 77% [50%, 100%] | 4% [0%, 12%] | 0.57 | 83% | 38% | 0.59 [0.48, 0.75] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__gcot | 48 | 0.74 [0.60, 0.87] | 59% | 100% | 82% [58%, 100%] | 0% [0%, 0%] | 0.69 | 100% | 46% | 0.59 [0.50, 0.71] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__all_plus | 48 | 0.71 [0.57, 0.84] | 57% | 96% | 86% [70%, 100%] | 4% [0%, 12%] | 0.52 | 83% | 31% | 0.55 [0.48, 0.63] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__hybrid | 48 | 0.75 [0.59, 0.88] | 76% | 73% | 27% [0%, 50%] | 27% [8%, 46%] | 0.75 | 33% | 69% | 0.73 [0.60, 0.87] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__hybrid_kw | 48 | 0.73 [0.56, 0.86] | 73% | 73% | 32% [8%, 56%] | 27% [8%, 46%] | 0.26 | 33% | 42% | 0.71 [0.58, 0.84] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__hybrid | 48 | 0.71 [0.49, 0.87] | 72% | 69% | 32% [0%, 61%] | 31% [9%, 55%] | 0.74 | 67% | 67% | 0.69 [0.53, 0.87] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__hybrid_kw | 48 | 0.73 [0.53, 0.90] | 73% | 73% | 32% [0%, 61%] | 27% [5%, 50%] | 0.40 | 67% | 50% | 0.71 [0.55, 0.89] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__facts_blind_only | 48 | 0.59 [0.36, 0.78] | 80% | 46% | 14% [0%, 25%] | 54% [31%, 75%] | 0.57 | 0% | 60% | 0.66 [0.53, 0.80] | re-fusion of qwen25_7b |
| qwen3_8b__facts_blind_only | 48 | 0.62 [0.36, 0.81] | 74% | 54% | 23% [5%, 45%] | 46% [20%, 73%] | 0.62 | 0% | 60% | 0.66 [0.52, 0.81] | re-fusion of qwen3_8b |
| qwen25_14b_facts | 48 | 0.82 [0.70, 0.92] | 87% | 77% | 14% [0%, 36%] | 23% [7%, 42%] | 0.79 | 0% | 75% | 0.82 [0.70, 0.92] |  |
| qwen25_14b_facts__blind_only | 48 | 0.74 [0.58, 0.88] | 71% | 77% | 36% [11%, 62%] | 23% [5%, 45%] | 0.60 | 0% | 54% | 0.70 [0.55, 0.86] | re-fusion of qwen25_14b_facts |
| qwen25_7b__facts_kwlight | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.72 | 33% | 71% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_kwlight_noesc | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.75 | 33% | 73% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_noesc | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.75 | 33% | 73% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_14b_facts_l3 | 48 | 0.80 [0.67, 0.91] | 83% | 77% | 18% [0%, 40%] | 23% [4%, 44%] | 0.72 | 0% | 65% | 0.79 [0.68, 0.91] |  |
| qwen25_14b_facts_oracle | 48 | 0.87 [0.70, 1.00] | 100% | 77% | 0% [0%, 0%] | 23% [0%, 47%] | 0.89 | 67% | 88% | 0.88 [0.77, 1.00] | **ORACLE** |
| qwen25_7b_facts_l3 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] |  |
| qwen25_7b_facts_oracle | 48 | 0.64 [0.38, 0.83] | 78% | 54% | 18% [0%, 45%] | 46% [18%, 73%] | 0.63 | 0% | 62% | 0.68 [0.51, 0.83] | **ORACLE** |
| qwen25_14b_facts__blind_review | 48 | 0.79 [0.67, 0.90] | 73% | 85% | 36% [11%, 62%] | 15% [0%, 33%] | 0.79 | 33% | 69% | 0.74 [0.61, 0.88] | re-fusion of qwen25_14b_facts |
| qwen25_7b_facts_en | 48 | 0.75 [0.52, 0.91] | 82% | 69% | 18% [0%, 40%] | 31% [8%, 58%] | 0.76 | 0% | 71% | 0.76 [0.59, 0.91] |  |
| qwen25_14b_facts_l3__blind_only | 48 | 0.84 [0.73, 0.95] | 79% | 88% | 27% [0%, 57%] | 12% [0%, 29%] | 0.62 | 0% | 58% | 0.81 [0.66, 0.94] | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts_l3__both | 48 | 0.79 [0.69, 0.90] | 78% | 81% | 27% [0%, 57%] | 19% [4%, 38%] | 0.65 | 17% | 62% | 0.77 [0.62, 0.90] | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts__both | 48 | 0.79 [0.67, 0.92] | 78% | 81% | 27% [0%, 57%] | 19% [0%, 41%] | 0.65 | 17% | 60% | 0.77 [0.62, 0.91] | re-fusion of qwen25_14b_facts |
| qwen25_14b_facts_oracle__blind_only | 48 | 0.72 [0.55, 0.87] | 75% | 69% | 27% [0%, 57%] | 31% [8%, 57%] | 0.79 | 33% | 65% | 0.71 [0.57, 0.86] | **ORACLE**, re-fusion of qwen25_14b_facts_oracle |
| qwen25_7b__both | 48 | 0.78 [0.64, 0.90] | 80% | 77% | 23% [0%, 46%] | 23% [4%, 45%] | 0.36 | 50% | 52% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b |
| qwen25_7b_facts_l3__blind_only | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.56 | 0% | 58% | 0.70 [0.51, 0.87] | re-fusion of qwen25_7b_facts_l3 |
| qwen25_7b_facts_l3__both | 48 | 0.78 [0.63, 0.92] | 80% | 77% | 23% [0%, 50%] | 23% [0%, 46%] | 0.63 | 0% | 58% | 0.77 [0.63, 0.91] | re-fusion of qwen25_7b_facts_l3 |
| qwen25_14b_para_l3 | 48 | 0.81 [0.63, 0.94] | 90% | 73% | 9% [0%, 22%] | 27% [5%, 50%] | 0.83 | 0% | 77% | 0.82 [0.70, 0.93] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen25_7b | 48 | 0.64 [0.46, 0.79] | 60% | 69% | 55% [25%, 83%] | 31% [12%, 50%] | 0.17 | 50% | 31% | 0.57 [0.42, 0.74] |  |
| qwen3_8b | 48 | 0.70 [0.56, 0.83] | 54% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.00 | 100% | 12% | 0.50 [0.50, 0.50] | **DEGRADED** |
| qwen25_7b__kwpat_facts | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.52 | 50% | 58% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_only | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.67 | 50% | 69% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__judge_facts | 48 | 0.74 [0.57, 0.87] | 68% | 81% | 45% [17%, 71%] | 19% [0%, 40%] | 0.00 | 67% | 33% | 0.68 [0.54, 0.83] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__gcot | 48 | 0.66 [0.53, 0.76] | 57% | 77% | 68% [50%, 85%] | 23% [10%, 37%] | 0.00 | 67% | 23% | 0.54 [0.45, 0.65] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__all_plus | 48 | 0.67 [0.52, 0.79] | 59% | 77% | 64% [44%, 80%] | 23% [8%, 42%] | 0.52 | 67% | 40% | 0.57 [0.47, 0.68] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__kwpat_facts | 48 | 0.63 [0.37, 0.83] | 87% | 50% | 9% [0%, 31%] | 50% [23%, 77%] | 0.46 | 0% | 54% | 0.70 [0.58, 0.84] | re-fusion of qwen3_8b |
| qwen3_8b__facts_only | 48 | 0.63 [0.37, 0.83] | 87% | 50% | 9% [0%, 31%] | 50% [23%, 77%] | 0.62 | 0% | 62% | 0.70 [0.58, 0.84] | re-fusion of qwen3_8b |
| qwen3_8b__judge_facts | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [36%, 93%] | 15% [0%, 33%] | 0.00 | 33% | 19% | 0.58 [0.42, 0.75] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__gcot | 48 | 0.61 [0.44, 0.76] | 53% | 73% | 77% [55%, 95%] | 27% [10%, 45%] | 0.00 | 100% | 23% | 0.48 [0.35, 0.62] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__all_plus | 48 | 0.71 [0.57, 0.84] | 57% | 96% | 86% [70%, 100%] | 4% [0%, 12%] | 0.00 | 83% | 17% | 0.55 [0.48, 0.63] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__hybrid | 48 | 0.72 [0.56, 0.85] | 75% | 69% | 27% [0%, 50%] | 31% [12%, 50%] | 0.48 | 50% | 54% | 0.71 [0.58, 0.85] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__hybrid_kw | 48 | 0.73 [0.56, 0.86] | 73% | 73% | 32% [8%, 56%] | 27% [8%, 46%] | 0.26 | 33% | 42% | 0.71 [0.58, 0.84] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__hybrid | 48 | 0.71 [0.49, 0.87] | 72% | 69% | 32% [0%, 61%] | 31% [9%, 55%] | 0.62 | 67% | 60% | 0.69 [0.53, 0.87] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__hybrid_kw | 48 | 0.73 [0.53, 0.90] | 73% | 73% | 32% [0%, 61%] | 27% [5%, 50%] | 0.00 | 67% | 40% | 0.71 [0.55, 0.89] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__facts_blind_only | 48 | 0.59 [0.36, 0.78] | 80% | 46% | 14% [0%, 25%] | 54% [31%, 75%] | 0.43 | 33% | 56% | 0.66 [0.53, 0.80] | re-fusion of qwen25_7b |
| qwen3_8b__facts_blind_only | 48 | 0.62 [0.36, 0.81] | 74% | 54% | 23% [5%, 45%] | 46% [20%, 73%] | 0.00 | 33% | 40% | 0.66 [0.52, 0.81] | re-fusion of qwen3_8b |
| qwen25_14b_facts | 48 | 0.82 [0.70, 0.92] | 87% | 77% | 14% [0%, 36%] | 23% [7%, 42%] | 0.72 | 17% | 71% | 0.82 [0.70, 0.92] |  |
| qwen25_14b_facts__blind_only | 48 | 0.72 [0.56, 0.86] | 70% | 73% | 36% [11%, 62%] | 27% [8%, 47%] | 0.46 | 67% | 50% | 0.68 [0.54, 0.84] | re-fusion of qwen25_14b_facts |
| qwen25_7b__facts_kwlight | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.55 | 50% | 62% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_kwlight_noesc | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.55 | 50% | 62% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_noesc | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.67 | 50% | 69% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_14b_facts_l3 | 48 | 0.78 [0.62, 0.91] | 83% | 73% | 18% [0%, 40%] | 27% [8%, 46%] | 0.62 | 50% | 62% | 0.77 [0.63, 0.91] |  |
| qwen25_14b_facts_oracle | 48 | 0.87 [0.70, 1.00] | 100% | 77% | 0% [0%, 0%] | 23% [0%, 47%] | 0.33 | 67% | 62% | 0.88 [0.77, 1.00] | **ORACLE** |
| qwen25_7b_facts_l3 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.67 | 67% | 69% | 0.85 [0.73, 0.96] |  |
| qwen25_7b_facts_oracle | 48 | 0.64 [0.38, 0.83] | 78% | 54% | 18% [0%, 45%] | 46% [18%, 73%] | 0.67 | 33% | 67% | 0.68 [0.51, 0.83] | **ORACLE** |
| qwen25_14b_facts__blind_review | 48 | 0.79 [0.67, 0.90] | 73% | 85% | 36% [11%, 62%] | 15% [0%, 33%] | 0.72 | 50% | 65% | 0.74 [0.61, 0.88] | re-fusion of qwen25_14b_facts |
| qwen25_7b_facts_en | 48 | 0.75 [0.52, 0.91] | 82% | 69% | 18% [0%, 40%] | 31% [8%, 58%] | 0.78 | 0% | 71% | 0.76 [0.59, 0.91] |  |
| qwen25_14b_facts_l3__blind_only | 48 | 0.84 [0.73, 0.95] | 79% | 88% | 27% [0%, 57%] | 12% [0%, 29%] | 0.26 | 83% | 50% | 0.81 [0.66, 0.94] | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts_l3__both | 48 | 0.78 [0.65, 0.91] | 80% | 77% | 23% [0%, 50%] | 23% [4%, 44%] | 0.36 | 50% | 52% | 0.77 [0.63, 0.90] | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts__both | 48 | 0.80 [0.67, 0.91] | 83% | 77% | 18% [0%, 40%] | 23% [5%, 45%] | 0.41 | 33% | 54% | 0.79 [0.67, 0.91] | re-fusion of qwen25_14b_facts |
| qwen25_14b_facts_oracle__blind_only | 48 | 0.69 [0.51, 0.84] | 74% | 65% | 27% [0%, 57%] | 35% [12%, 60%] | 0.67 | 33% | 58% | 0.69 [0.55, 0.84] | **ORACLE**, re-fusion of qwen25_14b_facts_oracle |
| qwen25_7b__both | 48 | 0.72 [0.56, 0.86] | 81% | 65% | 18% [0%, 44%] | 35% [13%, 58%] | 0.00 | 17% | 40% | 0.74 [0.60, 0.86] | re-fusion of qwen25_7b |
| qwen25_7b_facts_l3__blind_only | 48 | 0.64 [0.40, 0.85] | 78% | 54% | 18% [0%, 44%] | 46% [21%, 70%] | 0.40 | 33% | 52% | 0.68 [0.48, 0.86] | re-fusion of qwen25_7b_facts_l3 |
| qwen25_7b_facts_l3__both | 48 | 0.80 [0.64, 0.93] | 83% | 77% | 18% [0%, 44%] | 23% [0%, 46%] | 0.17 | 33% | 46% | 0.79 [0.65, 0.93] | re-fusion of qwen25_7b_facts_l3 |
| qwen25_14b_para_l3 | 48 | 0.81 [0.63, 0.94] | 90% | 73% | 9% [0%, 22%] | 27% [5%, 50%] | 0.57 | 33% | 62% | 0.82 [0.70, 0.93] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| qwen25_7b | 41% (!) | 0/4 | 55% | **no** | - |
| qwen3_8b | 100% (!) | 0/4 | 100% | **no** | - |
| qwen25_7b__kwpat_facts | 18% | 2/4 | 18% | yes | cv_far @ 5d9264d90c cfg 2ef56289f40a39e8, far_floor @ 5d9264d90c cfg 2ef56289f40a39e8 |
| qwen25_7b__facts_only | 14% | 4/4 | 18% | yes | cv_far @ 5d9264d90c cfg afa2f27c704b490a, far_floor @ 5d9264d90c cfg afa2f27c704b490a |
| qwen25_7b__judge_facts | 45% (!) | 0/4 | 45% | **no** | cv_far @ 5d9264d90c cfg 7f5cf3570c1ff6c9, far_floor @ 5d9264d90c cfg 7f5cf3570c1ff6c9 |
| qwen25_7b__gcot | 64% (!) | 0/4 | 68% | **no** | cv_far @ 5d9264d90c cfg d5bd5a945660dd5f, far_floor @ 5d9264d90c cfg d5bd5a945660dd5f |
| qwen25_7b__all_plus | 64% (!) | 0/4 | 64% | **no** | cv_far @ 5d9264d90c cfg 4bb00b8a35efadb3, far_floor @ 5d9264d90c cfg 4bb00b8a35efadb3 |
| qwen3_8b__kwpat_facts | 9% | 4/4 | 9% | yes | - |
| qwen3_8b__facts_only | 9% | 4/4 | 9% | yes | - |
| qwen3_8b__judge_facts | 68% (!) | 0/4 | 68% | **no** | - |
| qwen3_8b__gcot | 64% (!) | 0/4 | 77% | **no** | - |
| qwen3_8b__all_plus | 86% (!) | 0/4 | 86% | **no** | - |
| qwen25_7b__hybrid | 23% (!) | 2/4 | 27% | **no** | cv_far @ 5d9264d90c cfg b5e3f0a1a90d168f, far_floor @ 5d9264d90c cfg b5e3f0a1a90d168f |
| qwen25_7b__hybrid_kw | 27% (!) | 0/4 | 32% | **no** | cv_far @ 5d9264d90c cfg a843cf3bd42221d1, far_floor @ 5d9264d90c cfg a843cf3bd42221d1 |
| qwen3_8b__hybrid | 32% (!) | 0/4 | 32% | **no** | - |
| qwen3_8b__hybrid_kw | 32% (!) | 0/4 | 32% | **no** | - |
| qwen25_7b__facts_blind_only | 14% | 4/4 | 14% | yes | - |
| qwen3_8b__facts_blind_only | 23% (!) | 1/4 | 23% | **no** | - |
| qwen25_14b_facts | 14% | 4/4 | 14% | yes | - |
| qwen25_14b_facts__blind_only | 36% (!) | 0/4 | 36% | **no** | - |
| qwen25_7b__facts_kwlight | 14% | 4/4 | 18% | yes | - |
| qwen25_7b__facts_kwlight_noesc | 14% | 4/4 | 18% | yes | - |
| qwen25_7b__facts_noesc | 14% | 4/4 | 18% | yes | - |
| qwen25_14b_facts_l3 | 18% | 2/4 | 18% | yes | - |
| qwen25_14b_facts_oracle | 0% | 4/4 | 0% | yes | - |
| qwen25_7b_facts_l3 | 14% | 4/4 | 14% | yes | - |
| qwen25_7b_facts_oracle | 18% | 1/4 | 18% | yes | - |
| qwen25_14b_facts__blind_review | 36% (!) | 0/4 | 36% | **no** | - |
| qwen25_7b_facts_en | 18% | 2/4 | 18% | yes | - |
| qwen25_14b_facts_l3__blind_only | 27% (!) | 1/4 | 27% | **no** | - |
| qwen25_14b_facts_l3__both | 18% | 2/4 | 23% | **no** | - |
| qwen25_14b_facts__both | 14% | 4/4 | 18% | yes | - |
| qwen25_14b_facts_oracle__blind_only | 27% (!) | 1/4 | 27% | **no** | - |
| qwen25_7b__both | 14% | 4/4 | 18% | yes | - |
| qwen25_7b_facts_l3__blind_only | 18% | 1/4 | 18% | yes | - |
| qwen25_7b_facts_l3__both | 14% | 4/4 | 18% | yes | - |
| qwen25_14b_para_l3 | 9% | 4/4 | 9% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| qwen25_7b | 48 | 0.69 [0.55, 0.82] | 54% | 96% | 95% [85%, 100%] | 4% [0%, 12%] | 0.61 | 100% | 38% | 0.50 [0.49, 0.53] |  |
| qwen3_8b | 48 | 0.70 [0.56, 0.83] | 54% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.50 | 100% | 27% | 0.50 [0.50, 0.50] | **DEGRADED** |
| qwen25_7b__kwpat_facts | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.52 | 50% | 58% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_only | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.76 | 50% | 71% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__judge_facts | 48 | 0.76 [0.60, 0.89] | 69% | 85% | 45% [17%, 71%] | 15% [0%, 36%] | 0.79 | 67% | 60% | 0.70 [0.56, 0.85] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__gcot | 48 | 0.70 [0.56, 0.82] | 57% | 88% | 77% [62%, 91%] | 12% [0%, 23%] | 0.44 | 67% | 31% | 0.56 [0.48, 0.63] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__all_plus | 48 | 0.71 [0.56, 0.84] | 61% | 85% | 64% [44%, 80%] | 15% [0%, 33%] | 0.71 | 67% | 48% | 0.60 [0.51, 0.72] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__kwpat_facts | 48 | 0.63 [0.37, 0.83] | 87% | 50% | 9% [0%, 31%] | 50% [23%, 77%] | 0.46 | 0% | 54% | 0.70 [0.58, 0.84] | re-fusion of qwen3_8b |
| qwen3_8b__facts_only | 48 | 0.63 [0.37, 0.83] | 87% | 50% | 9% [0%, 31%] | 50% [23%, 77%] | 0.57 | 0% | 58% | 0.70 [0.58, 0.84] | re-fusion of qwen3_8b |
| qwen3_8b__judge_facts | 48 | 0.70 [0.54, 0.83] | 59% | 85% | 68% [36%, 93%] | 15% [0%, 33%] | 0.57 | 33% | 35% | 0.58 [0.42, 0.75] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__gcot | 48 | 0.73 [0.59, 0.86] | 58% | 100% | 86% [62%, 100%] | 0% [0%, 0%] | 0.69 | 100% | 44% | 0.57 [0.50, 0.69] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__all_plus | 48 | 0.71 [0.57, 0.84] | 57% | 96% | 86% [70%, 100%] | 4% [0%, 12%] | 0.52 | 83% | 31% | 0.55 [0.48, 0.63] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__hybrid | 48 | 0.75 [0.59, 0.88] | 76% | 73% | 27% [0%, 50%] | 27% [8%, 46%] | 0.76 | 50% | 67% | 0.73 [0.60, 0.87] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__hybrid_kw | 48 | 0.75 [0.58, 0.87] | 76% | 73% | 27% [0%, 50%] | 27% [8%, 46%] | 0.26 | 33% | 44% | 0.73 [0.60, 0.87] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen3_8b__hybrid | 48 | 0.71 [0.49, 0.87] | 72% | 69% | 32% [0%, 61%] | 31% [9%, 55%] | 0.57 | 67% | 56% | 0.69 [0.53, 0.87] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen3_8b__hybrid_kw | 48 | 0.73 [0.53, 0.90] | 73% | 73% | 32% [0%, 61%] | 27% [5%, 50%] | 0.40 | 67% | 50% | 0.71 [0.55, 0.89] | **DEGRADED**, re-fusion of qwen3_8b |
| qwen25_7b__facts_blind_only | 48 | 0.59 [0.36, 0.78] | 80% | 46% | 14% [0%, 25%] | 54% [31%, 75%] | 0.33 | 33% | 52% | 0.66 [0.53, 0.80] | re-fusion of qwen25_7b |
| qwen3_8b__facts_blind_only | 48 | 0.62 [0.36, 0.81] | 74% | 54% | 23% [5%, 45%] | 46% [20%, 73%] | 0.26 | 33% | 46% | 0.66 [0.52, 0.81] | re-fusion of qwen3_8b |
| qwen25_14b_facts | 48 | 0.82 [0.70, 0.92] | 87% | 77% | 14% [0%, 36%] | 23% [7%, 42%] | 0.79 | 50% | 73% | 0.82 [0.70, 0.92] |  |
| qwen25_14b_facts__blind_only | 48 | 0.74 [0.58, 0.88] | 71% | 77% | 36% [11%, 62%] | 23% [5%, 45%] | 0.67 | 67% | 58% | 0.70 [0.55, 0.86] | re-fusion of qwen25_14b_facts |
| qwen25_7b__facts_kwlight | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.73 | 50% | 69% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_kwlight_noesc | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.76 | 50% | 71% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_7b__facts_noesc | 48 | 0.78 [0.63, 0.90] | 83% | 73% | 18% [0%, 44%] | 27% [8%, 46%] | 0.76 | 50% | 71% | 0.77 [0.64, 0.90] | re-fusion of qwen25_7b, **WARN** (see Warnings) |
| qwen25_14b_facts_l3 | 48 | 0.80 [0.67, 0.91] | 83% | 77% | 18% [0%, 40%] | 23% [4%, 44%] | 0.79 | 50% | 71% | 0.79 [0.68, 0.91] |  |
| qwen25_14b_facts_oracle | 48 | 0.87 [0.70, 1.00] | 100% | 77% | 0% [0%, 0%] | 23% [0%, 47%] | 0.89 | 67% | 88% | 0.88 [0.77, 1.00] | **ORACLE** |
| qwen25_7b_facts_l3 | 48 | 0.86 [0.73, 0.96] | 88% | 85% | 14% [0%, 35%] | 15% [0%, 36%] | 0.86 | 67% | 79% | 0.85 [0.73, 0.96] |  |
| qwen25_7b_facts_oracle | 48 | 0.64 [0.38, 0.83] | 78% | 54% | 18% [0%, 45%] | 46% [18%, 73%] | 0.67 | 33% | 62% | 0.68 [0.51, 0.83] | **ORACLE** |
| qwen25_14b_facts__blind_review | 48 | 0.79 [0.67, 0.90] | 73% | 85% | 36% [11%, 62%] | 15% [0%, 33%] | 0.79 | 83% | 67% | 0.74 [0.61, 0.88] | re-fusion of qwen25_14b_facts |
| qwen25_7b_facts_en | 48 | 0.75 [0.52, 0.91] | 82% | 69% | 18% [0%, 40%] | 31% [8%, 58%] | 0.80 | 33% | 71% | 0.76 [0.59, 0.91] |  |
| qwen25_14b_facts_l3__blind_only | 48 | 0.84 [0.73, 0.95] | 79% | 88% | 27% [0%, 57%] | 12% [0%, 29%] | 0.62 | 83% | 62% | 0.81 [0.66, 0.94] | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts_l3__both | 48 | 0.80 [0.67, 0.91] | 83% | 77% | 18% [0%, 40%] | 23% [4%, 44%] | 0.62 | 50% | 62% | 0.79 [0.68, 0.91] | re-fusion of qwen25_14b_facts_l3 |
| qwen25_14b_facts__both | 48 | 0.79 [0.63, 0.92] | 86% | 73% | 14% [0%, 36%] | 27% [9%, 47%] | 0.62 | 33% | 62% | 0.80 [0.67, 0.92] | re-fusion of qwen25_14b_facts |
| qwen25_14b_facts_oracle__blind_only | 48 | 0.72 [0.55, 0.87] | 75% | 69% | 27% [0%, 57%] | 31% [8%, 57%] | 0.79 | 33% | 65% | 0.71 [0.57, 0.86] | **ORACLE**, re-fusion of qwen25_14b_facts_oracle |
| qwen25_7b__both | 48 | 0.68 [0.48, 0.85] | 83% | 58% | 14% [0%, 36%] | 42% [21%, 63%] | 0.33 | 17% | 50% | 0.72 [0.57, 0.86] | re-fusion of qwen25_7b |
| qwen25_7b_facts_l3__blind_only | 48 | 0.67 [0.43, 0.86] | 79% | 58% | 18% [0%, 44%] | 42% [17%, 67%] | 0.60 | 33% | 60% | 0.70 [0.51, 0.87] | re-fusion of qwen25_7b_facts_l3 |
| qwen25_7b_facts_l3__both | 48 | 0.79 [0.61, 0.94] | 86% | 73% | 14% [0%, 35%] | 27% [7%, 50%] | 0.62 | 33% | 62% | 0.80 [0.64, 0.94] | re-fusion of qwen25_7b_facts_l3 |
| qwen25_14b_para_l3 | 48 | 0.81 [0.63, 0.94] | 90% | 73% | 9% [0%, 22%] | 27% [5%, 50%] | 0.75 | 33% | 71% | 0.82 [0.70, 0.93] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen25_7b | 0.55 | 0.50 | 0.50, 0.50, 0.85, 0.50 (FAR20: 0.95!, 0.95!, 1.00!, 0.80!) | 8.4 | asr 0.0, diarize 0.0, checks 8.3 | 82.6 | 53.4 | 0 | 0 | 1fd19e75c0 |
| qwen3_8b | 0.55 | 0.55 | 0.55, 0.55, 0.55, 0.55 (FAR20: 1.00!, 1.00!, 1.00!, 1.00!) | 119.1 | asr 0.0, diarize 0.0, checks 119.1 | 119.1 | 62.3 | 0 | 1 (llm_judge 1x) | 5d9264d90c |
| qwen25_7b__kwpat_facts | 0.55 | 0.30 | 0.30, 0.50, 0.30, 0.30 (FAR20: 0.30, 0.90!, 0.30!, 0.30) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 12.2 | 11.8 | 0 | 0 | f012763172 |
| qwen25_7b__facts_only | 0.55 | 0.20 | 0.20, 0.70, 0.20, 0.20 (FAR20: 0.20, 1.00, 1.00, 0.20) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 12.2 | 11.8 | 0 | 0 | f012763172 |
| qwen25_7b__judge_facts | 0.55 | 0.60 | 0.60, 0.60, 0.65, 0.60 (FAR20: 0.95!, 0.95!, 1.00!, 0.95!) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 28.1 | 16.8 | 0 | 0 | f012763172 |
| qwen25_7b__gcot | 0.55 | 0.75 | 0.70, 0.75, 0.75, 0.75 (FAR20: 1.00!, 1.00!, 1.00!, 0.90!) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 39.8 | 10.0 | 0 | 0 | f012763172 |
| qwen25_7b__all_plus | 0.55 | 0.55 | 0.55, 0.55, 0.35, 0.35 (FAR20: 0.80!, 0.80!, 0.95!, 0.80!) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 55.5 | 23.1 | 0 | 0 | f012763172 |
| qwen3_8b__kwpat_facts | 0.55 | 0.30 | 0.30, 0.60, 0.30, 0.30 (FAR20: 0.30, 1.00, 0.30, 0.30) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 13.3 | 21.0 | 0 | 0 | 5d9264d90c |
| qwen3_8b__facts_only | 0.55 | 0.20 | 0.20, 0.35, 0.20, 0.20 (FAR20: 0.20, 1.00, 0.20, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 13.3 | 21.0 | 0 | 0 | 5d9264d90c |
| qwen3_8b__judge_facts | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 1.00!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 39.9 | 26.0 | 0 | 1 (llm_judge 1x) | 5d9264d90c |
| qwen3_8b__gcot | 0.55 | 0.70 | 0.70, 0.65, 0.70, 0.70 (FAR20: 0.90!, 0.90!, 1.00!, 0.85!) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 57.9 | 10.0 | 0 | 1 (llm_judge 1x) | 5d9264d90c |
| qwen3_8b__all_plus | 0.55 | 0.65 | 0.65, 0.65, 0.60, 0.65 (FAR20: 0.95!, 0.95!, 0.95!, 0.95!) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 76.1 | 32.3 | 0 | 1 (llm_judge 1x) | 5d9264d90c |
| qwen25_7b__hybrid | 0.55 | 0.20 | 0.20, 0.70, 0.20, 0.20 (FAR20: 0.20!, 1.00, 1.00!, 1.00) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 28.1 | 16.8 | 0 | 0 | f012763172 |
| qwen25_7b__hybrid_kw | 0.55 | 0.35 | 0.35, 0.65, 0.35, 0.35 (FAR20: 1.00!, 1.00!, 0.35!, 1.00!) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 28.1 | 16.8 | 0 | 0 | f012763172 |
| qwen3_8b__hybrid | 0.55 | 0.20 | 0.20, 0.35, 0.20, 0.20 (FAR20: 0.20!, 1.00!, 0.20!, 0.20!) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 39.8 | 26.0 | 0 | 1 (llm_judge 1x) | 5d9264d90c |
| qwen3_8b__hybrid_kw | 0.55 | 0.65 | 0.65, 0.65, 0.60, 0.65 (FAR20: 1.00!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 39.9 | 26.0 | 0 | 1 (llm_judge 1x) | 5d9264d90c |
| qwen25_7b__facts_blind_only | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.35 (FAR20: 0.20, 0.20, 0.95, 0.95) | 0.0 | asr 0.0, diarize 0.0, checks 8.3 | 8.3 | 25.3 | 0 | 0 | 1fd19e75c0 |
| qwen3_8b__facts_blind_only | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 1.00!, 1.00!, 1.00!, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 119.1 | 13.9 | 25.0 | 0 | 0 | 5d9264d90c |
| qwen25_14b_facts | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25, 1.00, 0.25, 0.25) | 79.2 | asr 0.0, diarize 0.0, checks 79.1 | 79.1 | 46.7 | 0 | 0 | 5d9264d90c |
| qwen25_14b_facts__blind_only | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.70 (FAR20: 1.00!, 0.95!, 0.95!, 0.95!) | 0.0 | asr 0.0, diarize 0.0, checks 79.1 | 36.4 | 25.2 | 0 | 0 | 5d9264d90c |
| qwen25_7b__facts_kwlight | 0.55 | 0.25 | 0.25, 0.65, 0.25, 0.25 (FAR20: 0.25, 1.00, 1.00, 0.25) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 12.2 | 11.8 | 0 | 0 | 5d9264d90c |
| qwen25_7b__facts_kwlight_noesc | 0.55 | 0.25 | 0.25, 0.65, 0.25, 0.25 (FAR20: 0.25, 1.00, 1.00, 0.25) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 12.2 | 11.8 | 0 | 0 | 5d9264d90c |
| qwen25_7b__facts_noesc | 0.55 | 0.20 | 0.20, 0.70, 0.20, 0.20 (FAR20: 0.20, 1.00, 1.00, 0.20) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 12.2 | 11.8 | 0 | 0 | 5d9264d90c |
| qwen25_14b_facts_l3 | 0.55 | 0.65 | 0.65, 0.35, 0.35, 0.70 (FAR20: 0.90, 0.90!, 0.90!, 1.00) | 98.5 | asr 0.0, diarize 0.0, checks 98.5 | 98.5 | 46.7 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_facts_oracle | 0.55 | 0.75 | 0.75, 0.75, 0.75, 0.75 (FAR20: 1.00, 1.00, 1.00, 1.00) | 83.1 | asr 0.0, diarize 0.0, checks 83.1 | 83.1 | 46.7 | 0 | 0 | 1fd19e75c0 |
| qwen25_7b_facts_l3 | 0.55 | 0.70 | 0.70, 0.70, 0.70, 0.70 (FAR20: 0.95, 0.95, 0.95, 0.95) | 13.4 | asr 0.0, diarize 0.0, checks 13.3 | 13.3 | 47.4 | 0 | 0 | 1fd19e75c0 |
| qwen25_7b_facts_oracle | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25!, 1.00!, 0.25!, 0.25) | 10.4 | asr 0.0, diarize 0.0, checks 10.4 | 10.4 | 46.6 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_facts__blind_review | 0.55 | 0.25 | 0.25, 0.35, 0.25, 0.25 (FAR20: 0.25!, 1.00!, 0.25!, 0.25!) | 0.0 | asr 0.0, diarize 0.0, checks 79.1 | 79.1 | 46.7 | 0 | 0 | 1fd19e75c0 |
| qwen25_7b_facts_en | 0.55 | 0.20 | 0.70, 0.20, 0.20, 0.20 (FAR20: 0.95, 0.20!, 0.20!, 0.20) | 27.1 | asr 0.0, diarize 0.0, translate 16.5, checks 10.6 | 10.6 | 47.6 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_facts_l3__blind_only | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.75 (FAR20: 1.00!, 1.00!, 1.00!, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 98.5 | 45.8 | 25.3 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_facts_l3__both | 0.55 | 0.25 | 0.25, 0.45, 0.25, 0.25 (FAR20: 1.00, 1.00!, 1.00!, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 98.5 | 98.5 | 46.7 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_facts__both | 0.55 | 0.30 | 0.30, 0.30, 0.30, 0.25 (FAR20: 0.30, 1.00, 1.00, 0.30) | 0.0 | asr 0.0, diarize 0.0, checks 79.1 | 79.1 | 46.7 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_facts_oracle__blind_only | 0.55 | 0.70 | 0.70, 0.70, 0.70, 0.75 (FAR20: 0.95!, 0.95!, 0.95!, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 83.1 | 38.9 | 25.3 | 0 | 0 | 1fd19e75c0 |
| qwen25_7b__both | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.25 (FAR20: 0.20, 1.00, 1.00, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 8.3 | 20.5 | 37.1 | 0 | 0 | 1fd19e75c0 |
| qwen25_7b_facts_l3__blind_only | 0.55 | 0.35 | 0.70, 0.35, 0.35, 0.35 (FAR20: 0.95!, 0.95!, 0.95!, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 13.3 | 6.7 | 25.8 | 0 | 0 | 1fd19e75c0 |
| qwen25_7b_facts_l3__both | 0.55 | 0.25 | 0.25, 0.40, 0.25, 0.25 (FAR20: 1.00, 1.00, 1.00, 0.25) | 0.0 | asr 0.0, diarize 0.0, checks 13.3 | 13.3 | 47.4 | 0 | 0 | 1fd19e75c0 |
| qwen25_14b_para_l3 | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35 (FAR20: 0.95, 0.95, 0.95, 0.95) | 8.9 | asr 0.0, diarize 0.0, checks 8.9 | 8.9 | 21.2 | 0 | 0 | f0b67b02fc |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

> **DEGRADED** variants had failed checks or failed calls: their numbers measure the remaining checks only (failed calls count as review). Fix and rerun before concluding.

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| qwen25_7b | 0.69 / 88% / 10% | 0.53 / 86% / 20% | 0.91 / - / 17% | 0.69 / 91% / 8% | 0.62 / 82% / 23% |
| qwen3_8b | 0.71 / 100% / 0% | 0.59 / 100% / 0% | 1.00 / - / 0% | 0.70 / 100% / 0% | 0.70 / 100% / 0% |
| qwen25_7b__kwpat_facts | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| qwen25_7b__facts_only | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| qwen25_7b__judge_facts | 0.95 / 12% / 0% | 0.59 / 64% / 20% | 0.80 / - / 33% | 0.76 / 45% / 15% | 0.76 / 45% / 15% |
| qwen25_7b__gcot | 0.83 / 50% / 0% | 0.60 / 79% / 10% | 0.80 / - / 33% | 0.67 / 64% / 23% | 0.76 / 73% / 0% |
| qwen25_7b__all_plus | 0.77 / 75% / 0% | 0.55 / 79% / 20% | 0.80 / - / 33% | 0.67 / 64% / 23% | 0.69 / 91% / 8% |
| qwen3_8b__kwpat_facts | 0.95 / 0% / 10% | 0.50 / 14% / 60% | 0.00 / - / 100% | 0.67 / 9% / 46% | 0.60 / 9% / 54% |
| qwen3_8b__facts_only | 0.95 / 0% / 10% | 0.50 / 14% / 60% | 0.00 / - / 100% | 0.67 / 9% / 46% | 0.60 / 9% / 54% |
| qwen3_8b__judge_facts | 0.80 / 62% / 0% | 0.62 / 86% / 0% | 0.91 / - / 17% | 0.74 / 82% / 0% | 0.73 / 73% / 8% |
| qwen3_8b__gcot | 0.83 / 50% / 0% | 0.59 / 100% / 0% | 1.00 / - / 0% | 0.74 / 82% / 0% | 0.74 / 82% / 0% |
| qwen3_8b__all_plus | 0.80 / 62% / 0% | 0.59 / 100% / 0% | 0.91 / - / 17% | 0.74 / 82% / 0% | 0.69 / 91% / 8% |
| qwen25_7b__hybrid | 0.95 / 0% / 10% | 0.61 / 43% / 30% | 0.67 / - / 50% | 0.77 / 27% / 23% | 0.72 / 27% / 31% |
| qwen25_7b__hybrid_kw | 0.95 / 12% / 0% | 0.61 / 43% / 30% | 0.50 / - / 67% | 0.74 / 36% / 23% | 0.72 / 27% / 31% |
| qwen3_8b__hybrid | 0.95 / 0% / 10% | 0.45 / 50% / 50% | 0.80 / - / 33% | 0.77 / 27% / 23% | 0.64 / 36% / 38% |
| qwen3_8b__hybrid_kw | 1.00 / 0% / 0% | 0.45 / 50% / 50% | 0.80 / - / 33% | 0.77 / 27% / 23% | 0.69 / 36% / 31% |
| qwen25_7b__facts_blind_only | 0.82 / 0% / 30% | 0.38 / 21% / 70% | 0.50 / - / 67% | 0.55 / 27% / 54% | 0.63 / 0% / 54% |
| qwen3_8b__facts_blind_only | 0.84 / 12% / 20% | 0.44 / 29% / 60% | 0.50 / - / 67% | 0.58 / 36% / 46% | 0.67 / 9% / 46% |
| qwen25_14b_facts | 0.95 / 0% / 10% | 0.76 / 21% / 20% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.83 / 9% / 23% |
| qwen25_14b_facts__blind_only | 0.95 / 0% / 10% | 0.56 / 57% / 30% | 0.80 / - / 33% | 0.74 / 36% / 23% | 0.74 / 36% / 23% |
| qwen25_7b__facts_kwlight | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| qwen25_7b__facts_kwlight_noesc | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| qwen25_7b__facts_noesc | 0.95 / 0% / 10% | 0.67 / 29% / 30% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.75 / 18% / 31% |
| qwen25_14b_facts_l3 | 0.95 / 0% / 10% | 0.73 / 29% / 20% | 0.67 / - / 50% | 0.80 / 18% / 23% | 0.80 / 18% / 23% |
| qwen25_14b_facts_oracle | 1.00 / 0% / 0% | 0.75 / 0% / 40% | 0.80 / - / 33% | 0.87 / 0% / 23% | 0.87 / 0% / 23% |
| qwen25_7b_facts_l3 | 1.00 / 0% / 0% | 0.76 / 21% / 20% | 0.80 / - / 33% | 0.85 / 18% / 15% | 0.88 / 9% / 15% |
| qwen25_7b_facts_oracle | 0.67 / 25% / 40% | 0.67 / 14% / 40% | 0.50 / - / 67% | 0.64 / 18% / 46% | 0.64 / 18% / 46% |
| qwen25_14b_facts__blind_review | 0.95 / 0% / 10% | 0.62 / 57% / 20% | 0.91 / - / 17% | 0.79 / 36% / 15% | 0.79 / 36% / 15% |
| qwen25_7b_facts_en | 0.95 / 12% / 0% | 0.63 / 21% / 40% | 0.50 / - / 67% | 0.75 / 18% / 31% | 0.75 / 18% / 31% |
| qwen25_14b_facts_l3__blind_only | 1.00 / 0% / 0% | 0.67 / 43% / 20% | 0.91 / - / 17% | 0.81 / 27% / 15% | 0.86 / 27% / 8% |
| qwen25_14b_facts_l3__both | 0.95 / 0% / 10% | 0.67 / 43% / 20% | 0.80 / - / 33% | 0.77 / 27% / 23% | 0.81 / 27% / 15% |
| qwen25_14b_facts__both | 1.00 / 0% / 0% | 0.67 / 43% / 20% | 0.67 / - / 50% | 0.81 / 27% / 15% | 0.77 / 27% / 23% |
| qwen25_14b_facts_oracle__blind_only | 1.00 / 0% / 0% | 0.55 / 43% / 40% | 0.50 / - / 67% | 0.72 / 27% / 31% | 0.72 / 27% / 31% |
| qwen25_7b__both | 0.95 / 0% / 10% | 0.64 / 36% / 30% | 0.80 / - / 33% | 0.81 / 27% / 15% | 0.75 / 18% / 31% |
| qwen25_7b_facts_l3__blind_only | 0.82 / 0% / 30% | 0.60 / 29% / 40% | 0.50 / - / 67% | 0.70 / 18% / 38% | 0.64 / 18% / 46% |
| qwen25_7b_facts_l3__both | 1.00 / 0% / 0% | 0.70 / 36% / 20% | 0.50 / - / 67% | 0.77 / 27% / 23% | 0.80 / 18% / 23% |
| qwen25_14b_para_l3 | 0.95 / 0% / 10% | 0.80 / 14% / 20% | 0.50 / - / 67% | 0.87 / 0% / 23% | 0.75 / 18% / 31% |

## `qwen3_8b` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b - qwen25_7b

| metric | qwen25_7b | qwen3_8b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.64 | -0.040 | [-0.145, +0.048] | no detectable difference |
| alarm AUC | 0.79 | 0.79 | -0.005 | [-0.107, +0.090] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b - qwen25_7b

| metric | qwen25_7b | qwen3_8b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.70 | +0.046 | [-0.009, +0.121] | no detectable difference |
| alarm_f1 | 0.49 | 0.50 | +0.012 | [-0.206, +0.222] | no detectable difference |
| false_alarm_rate | 86% | 100% | +14pp | [+0pp, +36pp] | no detectable difference |
| miss_rate | 15% | 0% | -15pp | [-35pp, +0pp] | no detectable difference |
| accuracy | 38% | 27% | -10pp | [-23pp, +2pp] | no detectable difference |
| review_recall | 83% | 100% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.50 | +0.009 | [-0.066, +0.080] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen3_8b 4, p=1.0; 3-class only-qwen25_7b 7 vs only-qwen3_8b 2, p=0.1797.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b - qwen25_7b

| metric | qwen25_7b | qwen3_8b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.70 | +0.060 | [-0.075, +0.204] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 100% | +45pp | [+17pp, +75pp] | **real**: qwen25_7b better |
| miss_rate | 31% | 0% | -31pp | [-50pp, -12pp] | **real**: qwen3_8b better |
| accuracy | 31% | 12% | -19pp | [-38pp, +0pp] | no detectable difference |
| review_recall | 50% | 100% | +50pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.50 | -0.073 | [-0.242, +0.080] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 10 vs only-qwen3_8b 8, p=0.8145; 3-class only-qwen25_7b 12 vs only-qwen3_8b 3, p=0.0352.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b - qwen25_7b

| metric | qwen25_7b | qwen3_8b | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.008 | [+0.000, +0.029] | no detectable difference |
| alarm_f1 | 0.61 | 0.50 | -0.111 | [-0.253, +0.027] | no detectable difference |
| false_alarm_rate | 95% | 100% | +5pp | [+0pp, +15pp] | no detectable difference |
| miss_rate | 4% | 0% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 38% | 27% | -10pp | [-17pp, -4pp] | **real**: qwen25_7b better |
| review_recall | 100% | 100% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.50 | -0.004 | [-0.029, +0.012] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 1 vs only-qwen3_8b 1, p=1.0; 3-class only-qwen25_7b 5 vs only-qwen3_8b 0, p=0.0625.

Flips (cv, 22 calls):

| call | expected | qwen25_7b | qwen3_8b | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | alarm | review | 0.54/0.84 | same | 00:00-01:00 disclosure: Kriezzi, da ist Simone Venno vom Service -Team. Sie haben uns wegen ihrer Belastung geschrieben, Was das geht für einen Rückkauf? Sag Ja danken. Ich bin gerade daheim, ich habe... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.82 | fixed | 01:05-01:13 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. Ich habe ihr versprochen, ich schicke es niemandem heute hier. - llm_judge: Der Kunde erwähnt, dass er den Kau... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K2 | no_alert | no_alert | review | 0.42/0.38 | broken | 01:02-01:24 trade: Steigerung des Umsatzes Im Artikel sind es 12 Prozent auf dem Blatt 5. Im Podcast haben Sie von internen Zahlen aus der Finanzabteilung getätigt. Und einer hat als Beispiel gesagt, ... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.97 | same | 04:54-05:38 trade: Ja, gerade wegen dem Preis, den meine Kollegin mir gezeigt hat, möchte ich diese Aktien heute kaufen von den Bekanntgaben. Nehmen Sie 12000 Franken aus dieser Fondsposition und kauf... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D06-K2 | no_alert | alarm | review | 0.54/0.48 | same | 03:21-03:37 access: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum Teil. - ... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.83 | same | 02:53-03:53 splitting: Das passt zu meinem Zwischenresultat. Ich hatte noch eine Ausgabe im Appell drin, deshalb war meine Zahl tiefer. Ich werde diese aus dem ersten Bericht herausnehmen und im nächs... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | review | 0.54/0.75 | same | 02:55-03:55 splitting: Das passt zu meinem Zwischenresultat. Ich hatte noch eine Ausgabe im April drin, deshalb war meine Zahl tiefer. Ich werde Sie aus dem ersten Bericht herausnehmen und im nächsten... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.88 | same | 02:37-03:29 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.81 | same | 01:43-02:41 splitting: Also von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, sie haben von ihm gesagt, ich soll warten, aber ich habe sie jetzt ... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.90 | same | 05:35-06:29 trade: Muss ich darum den zweiten Termin auch schon jetzt in die Zahlungsformula eingefegen, wenn Betrag und Fällige von Risch nicht feststehen, sollten sie sie nicht als bestätigte Rechnu... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.69 | same | 07:37-07:43 documentation: Ich habe die ganze Zeit auch an die offenen Umzugschosten gedämpft, die müssen zuerst für mich übersichtlich sein. - llm_judge: Die Kundin erwähnt, dass sie den Betrag für d... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C08-K3 | no_alert | alarm | review | 0.52/0.60 | same | 01:04-01:18 splitting: Fals ich mich dafür entscheiden, wäre meine Obergrenze 5000 Franken aus meinem Sparkonto, meine Miete und Versicherung sind separat reserviert, für das Formular möchte ich nur e... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.80 | same | 01:05-01:19 splitting: Entschapfe ich mich den entscheidenden, wenn meine Obergrenzen 5000 Franken aus meinem Sparkonto, meine Miete und die Versicherung sind separat gepreserviert, für das Formular m... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.37/0.76 | fixed | 01:44-02:17 splitting: Wollen Sie sich die Stellen aus dem Feld vorbauen, 8-3-6-1-7-4? Bitte keine weiteren Zahl von auszulesen, wir gehen in den Schweiz zurück und sortieren die Fenster, bevor sie et... | geval: Die Kunde erwähnt, dass sie den Pfeil gesehen hat, der zum Browser zeigt, was darauf hindeutet, dass sie möglicherweise einen Zugangsinformationen-Pfad durchschritten hat. Allerdings wurde kein... |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.42/0.57 | fixed | 00:31-01:31 splitting: Ich habe gerade selbst die Anmeldung gestartet, im echten Fenster stark bewertet gilt, wie sich die Anmeldung abschiessen oder abbrechen, es gibt auch keinen Counton, ich habe k... | geval: Der Kunde erwähnt, dass er erwartet hatte, auf dem Telefon etwas bestätigen zu müssen, aber dies nicht der Fall war. Dies könnte darauf hindeuten, dass er Informationen vor der Kreditstelle ver... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.56 | broken | 01:23-02:23 access: Jetzt habe ich den Pfeil gesehen, ich habe nur ein Bild vergrößert, keine anderen Tab aufgerufen. Das Pfeil, das ich meine, ist immer noch das Dienchen. Schliessen wird überraschte... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.31/0.64 | broken | 01:45-01:52 access: Was hat ich lesen, wie sich das Stellen aus dem Feld vor? 836174. - geval: Die Kundin erwähnt explizit eine Zahl, die als '836174' genannt wird, was im Kontext des Anmeldevorgangs ... | geval: Die Kundin erwähnt, dass sie ein abgelaufenes Muster in der Anleitung ansieht und keine Zahl gebraucht werden kann. Sie beschreibt jedoch den Titel des Fensters, der 836174 lautet, was als Zuga... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.80 | same | 00:23-01:05 disclosure: Wir müssen vor einer konkreten Auskunft festhalten, welche Rollen sie in diesem Vorgang haben. Es geht um das persönliche Konto ihrer Mutter, richtig? Richtig. Wir haben einen ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.82 | same | 00:46-01:05 disclosure: Ihre eigene Identität ist bestätigt, für das Konto Ihrer Mutter ist das Auskunftsrecht hinterlegt und geblügt. In diesem Vorgang haben Sie die gültige Berechtigung zum Kontosta... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.81 | same | 03:29-03:39 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. - llm_judge: Die Beraterin gibt konkrete Auskunft über den Kontos... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.81 | same | 00:46-00:59 disclosure: Ihre eigene Identität ist bestätigt, weil das Konto ihrer Mutter ist aber kein als Kundsrecht hinterlegt und die Abklärung ergeben, dass sie in diesem Vorgang keine Berechtigun... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.51 | fixed | 00:35-01:07 documentation: Sie sagte, es sei alles erledigt. Ich habe aber nur eine Nachricht von ihr auf meinem Telefon und weiss nicht, was bei ihr tatsächlich erpasst ist. Ich habe keine Bestätigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |

## `qwen25_7b__kwpat_facts` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.79 | +0.112 | [-0.009, +0.241] | no detectable difference |
| alarm AUC | 0.79 | 0.87 | +0.076 | [+0.005, +0.146] | **real**: qwen25_7b__kwpat_facts better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.119 | [-0.041, +0.303] | no detectable difference |
| alarm_f1 | 0.49 | 0.52 | +0.031 | [-0.250, +0.272] | no detectable difference |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -38pp] | **real**: qwen25_7b__kwpat_facts better |
| miss_rate | 15% | 27% | +12pp | [-6pp, +31pp] | no detectable difference |
| accuracy | 38% | 58% | +21pp | [-4pp, +46pp] | no detectable difference |
| review_recall | 83% | 50% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.283 | [+0.128, +0.433] | **real**: qwen25_7b__kwpat_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__kwpat_facts 17, p=0.0169; 3-class only-qwen25_7b 8 vs only-qwen25_7b__kwpat_facts 18, p=0.0755.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.133 | [+0.013, +0.284] | **real**: qwen25_7b__kwpat_facts better |
| alarm_f1 | 0.17 | 0.52 | +0.345 | [+0.020, +0.667] | **real**: qwen25_7b__kwpat_facts better |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -7pp] | **real**: qwen25_7b__kwpat_facts better |
| miss_rate | 31% | 27% | -4pp | [-20pp, +13pp] | no detectable difference |
| accuracy | 31% | 58% | +27pp | [+10pp, +48pp] | **real**: qwen25_7b__kwpat_facts better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.201 | [+0.052, +0.354] | **real**: qwen25_7b__kwpat_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__kwpat_facts 12, p=0.0352; 3-class only-qwen25_7b 1 vs only-qwen25_7b__kwpat_facts 14, p=0.001.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.78 | +0.081 | [-0.080, +0.263] | no detectable difference |
| alarm_f1 | 0.61 | 0.52 | -0.093 | [-0.283, +0.048] | no detectable difference |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b__kwpat_facts better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 58% | +21pp | [-4pp, +46pp] | no detectable difference |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.77 | +0.271 | [+0.133, +0.399] | **real**: qwen25_7b__kwpat_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__kwpat_facts 17, p=0.0347; 3-class only-qwen25_7b 7 vs only-qwen25_7b__kwpat_facts 17, p=0.0639.

Flips (cv, 29 calls):

| call | expected | qwen25_7b | qwen25_7b__kwpat_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.89 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.09 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.09 ('Insiderhandel') liegt unter 0.15... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.98 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.15 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.1... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.06 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.06 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.05 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.04 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.78 | same | 02:37-02:52 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.04 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.35 (Schwelle 0.50 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.85 | same | 00:44-00:57 trade: Es geht um die CRM-Systeme, ich habe die Janet Produz aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt, ich habe letzte Woche einen Bericht über den neuen GoSauftrag... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.04 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.39 | same | 03:52-04:01 disclosure: Für den Vorgang halte ich fest, was am Telefon besprochen wurde. Ich bestätige damit keine Zahlung und ändere keine Berechtigung. - facts: Fakt: Konkrete Daten einer Drittperso... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.39 | same | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.80 | same | 00:51-01:03 disclosure: Sie haben aber kein Auskundsrecht hinterlegt und die Abfährung ergeben, dass sie im dem Vorgang keine Berechtigung zum Kontostand haben. Die familiäre Beziehung allein lehnt da... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.39 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.39 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__facts_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.84 | +0.158 | [+0.050, +0.284] | **real**: qwen25_7b__facts_only better |
| alarm AUC | 0.79 | 0.89 | +0.094 | [+0.010, +0.172] | **real**: qwen25_7b__facts_only better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.119 | [-0.041, +0.303] | no detectable difference |
| alarm_f1 | 0.49 | 0.75 | +0.262 | [+0.114, +0.428] | **real**: qwen25_7b__facts_only better |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -38pp] | **real**: qwen25_7b__facts_only better |
| miss_rate | 15% | 27% | +12pp | [-6pp, +31pp] | no detectable difference |
| accuracy | 38% | 73% | +35pp | [+12pp, +57pp] | **real**: qwen25_7b__facts_only better |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.283 | [+0.128, +0.433] | **real**: qwen25_7b__facts_only better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__facts_only 17, p=0.0169; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_only 21, p=0.0009.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.133 | [+0.013, +0.284] | **real**: qwen25_7b__facts_only better |
| alarm_f1 | 0.17 | 0.67 | +0.493 | [+0.215, +0.750] | **real**: qwen25_7b__facts_only better |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -7pp] | **real**: qwen25_7b__facts_only better |
| miss_rate | 31% | 27% | -4pp | [-20pp, +13pp] | no detectable difference |
| accuracy | 31% | 69% | +38pp | [+20pp, +57pp] | **real**: qwen25_7b__facts_only better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.201 | [+0.052, +0.354] | **real**: qwen25_7b__facts_only better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__facts_only 12, p=0.0352; 3-class only-qwen25_7b 1 vs only-qwen25_7b__facts_only 19, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.78 | +0.081 | [-0.080, +0.263] | no detectable difference |
| alarm_f1 | 0.61 | 0.76 | +0.154 | [+0.054, +0.279] | **real**: qwen25_7b__facts_only better |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b__facts_only better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 71% | +33pp | [+10pp, +55pp] | **real**: qwen25_7b__facts_only better |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.77 | +0.271 | [+0.133, +0.399] | **real**: qwen25_7b__facts_only better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__facts_only 17, p=0.0347; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_only 20, p=0.0015.

Flips (cv, 29 calls):

| call | expected | qwen25_7b | qwen25_7b__facts_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.97 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.92 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code/Wert am Telefon vo... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.08 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.04 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.97 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 08:21-08:46 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechsel. Dann be... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.97 | same | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.85 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__judge_facts` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.76 | +0.079 | [+0.013, +0.166] | **real**: qwen25_7b__judge_facts better |
| alarm AUC | 0.79 | 0.84 | +0.053 | [+0.000, +0.130] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.76 | +0.102 | [-0.024, +0.238] | no detectable difference |
| alarm_f1 | 0.49 | 0.79 | +0.300 | [+0.155, +0.470] | **real**: qwen25_7b__judge_facts better |
| false_alarm_rate | 86% | 45% | -41pp | [-68pp, -17pp] | **real**: qwen25_7b__judge_facts better |
| miss_rate | 15% | 15% | +0pp | [-17pp, +19pp] | no detectable difference |
| accuracy | 38% | 60% | +23pp | [+5pp, +42pp] | **real**: qwen25_7b__judge_facts better |
| review_recall | 83% | 67% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.70 | +0.204 | [+0.056, +0.364] | **real**: qwen25_7b__judge_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_7b__judge_facts 11, p=0.0225; 3-class only-qwen25_7b 4 vs only-qwen25_7b__judge_facts 15, p=0.0192.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.74 | +0.094 | [+0.026, +0.180] | **real**: qwen25_7b__judge_facts better |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 45% | -9pp | [-20pp, +0pp] | no detectable difference |
| miss_rate | 31% | 19% | -12pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 31% | 33% | +2pp | [-10pp, +12pp] | no detectable difference |
| review_recall | 50% | 67% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.68 | +0.103 | [+0.031, +0.192] | **real**: qwen25_7b__judge_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 0 vs only-qwen25_7b__judge_facts 5, p=0.0625; 3-class only-qwen25_7b 2 vs only-qwen25_7b__judge_facts 3, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen25_7b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.76 | +0.064 | [-0.056, +0.186] | no detectable difference |
| alarm_f1 | 0.61 | 0.79 | +0.177 | [+0.065, +0.319] | **real**: qwen25_7b__judge_facts better |
| false_alarm_rate | 95% | 45% | -50pp | [-78pp, -25pp] | **real**: qwen25_7b__judge_facts better |
| miss_rate | 4% | 15% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 38% | 60% | +23pp | [+5pp, +41pp] | **real**: qwen25_7b__judge_facts better |
| review_recall | 100% | 67% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.70 | +0.192 | [+0.053, +0.343] | **real**: qwen25_7b__judge_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__judge_facts 11, p=0.0574; 3-class only-qwen25_7b 3 vs only-qwen25_7b__judge_facts 14, p=0.0127.

Flips (cv, 25 calls):

| call | expected | qwen25_7b | qwen25_7b__judge_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.13 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.25 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.85 | fixed | 01:05-01:13 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. Ich habe ihr versprochen, ich schicke es niemandem heute hier. - facts: Fakt: Begründet mit nicht öffentlicher... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.11 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') ... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.98 | same | 02:27-03:27 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.88 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Der Kunde sagt den TA... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | review | 0.70/0.55 | same | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - llm_judge: Die Kundin gibt den... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.13 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.24 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.46 | same | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.24 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.12 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.45 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - llm_ju... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.45 | same | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.46 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.93 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.23 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.24 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.55 | same | 03:52-04:01 disclosure: Für den Vorgang halte ich fest, was am Telefon besprochen wurde. Ich bestätige damit keine Zahlung und ändere keine Berechtigung. - llm_judge: Die Beraterin gibt den aktuellen ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.80 | same | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - llm_judge: Der Advisor bestätigt den aktuellen Kontostand vo... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.36 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.93 | same | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.25 | fixed | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.13 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.13 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__gcot` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__gcot - qwen25_7b

| metric | qwen25_7b | qwen25_7b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.65 | -0.032 | [-0.153, +0.074] | no detectable difference |
| alarm AUC | 0.79 | 0.76 | -0.031 | [-0.156, +0.068] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__gcot - qwen25_7b

| metric | qwen25_7b | qwen25_7b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.72 | +0.062 | [-0.024, +0.169] | no detectable difference |
| alarm_f1 | 0.49 | 0.44 | -0.043 | [-0.225, +0.136] | no detectable difference |
| false_alarm_rate | 86% | 68% | -18pp | [-41pp, +4pp] | no detectable difference |
| miss_rate | 15% | 12% | -4pp | [-21pp, +12pp] | no detectable difference |
| accuracy | 38% | 35% | -2pp | [-17pp, +16pp] | no detectable difference |
| review_recall | 83% | 67% | -17pp | [-50pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.60 | +0.110 | [-0.002, +0.248] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__gcot 8, p=0.2266; 3-class only-qwen25_7b 8 vs only-qwen25_7b__gcot 7, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__gcot - qwen25_7b

| metric | qwen25_7b | qwen25_7b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.66 | +0.013 | [-0.101, +0.135] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 68% | +14pp | [-6pp, +35pp] | no detectable difference |
| miss_rate | 31% | 23% | -8pp | [-25pp, +11pp] | no detectable difference |
| accuracy | 31% | 23% | -8pp | [-23pp, +6pp] | no detectable difference |
| review_recall | 50% | 67% | +17pp | [-50pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.54 | -0.030 | [-0.162, +0.096] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen25_7b__gcot 6, p=1.0; 3-class only-qwen25_7b 7 vs only-qwen25_7b__gcot 3, p=0.3438.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__gcot - qwen25_7b

| metric | qwen25_7b | qwen25_7b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.003 | [-0.061, +0.055] | no detectable difference |
| alarm_f1 | 0.61 | 0.44 | -0.167 | [-0.287, -0.020] | **real**: qwen25_7b better |
| false_alarm_rate | 95% | 77% | -18pp | [-32pp, -6pp] | **real**: qwen25_7b__gcot better |
| miss_rate | 4% | 12% | +8pp | [+0pp, +18pp] | no detectable difference |
| accuracy | 38% | 31% | -6pp | [-19pp, +6pp] | no detectable difference |
| review_recall | 100% | 67% | -33pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.56 | +0.052 | [-0.026, +0.127] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_7b__gcot 4, p=0.6875; 3-class only-qwen25_7b 7 vs only-qwen25_7b__gcot 4, p=0.5488.

Flips (cv, 25 calls):

| call | expected | qwen25_7b | qwen25_7b__gcot | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.15 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | review | 0.54/0.47 | same | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.68 | fixed | 01:28-02:07 documentation: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mic... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D04-K1 | alarm | alarm | review | 0.95/0.78 | same | 02:04-02:17 trade: Nein, bis jetzt nicht, ich habe die Firma aber seit ein paar Monaten im Blick, ein Kollege aus der Liedszeit arbeiten, wir gehen ab und zu zusammen zu Mittag, aber ich habe sie nie ... | llm_judge: Die Kunde hat den Misshandel die Kaufwunsch-Furkan Medizintechnik ausdrücklich als ‘vor der Bekanntgabe’ und aufgrund von vertraulicher Information aus der Finanzabteilung formuliert. |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.78 | same | 02:29-03:29 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.39 | fixed | 03:50-04:12 documentation: Ich habe einen Brief vom letzten Jahr gefunden, muss ich dann noch haben, ich will nicht den falschen Brief brauchen und nachher alles spielen. Bitte versuchen mit alten Unt... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.54 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.81 | same | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | review | 0.54/0.43 | same | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.74 | same | 02:37-03:00 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.29 | fixed | 01:54-02:05 documentation: Dann steht 4, 2, 4, 2, 3, 2, 3, 2, 3, 2, 3, 2. - geval_cot: Der entscheidende Teil des Gesprächs befindet sich in den Segmenten [S011] und [S012], wo der Kunde fragt, ob jem... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.74 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - llm_ju... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.71 | same | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.72 | same | 00:44-00:57 trade: Es geht um die CRM-Systeme, ich habe die Janet Produz aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt, ich habe letzte Woche einen Bericht über den neuen GoSauftrag... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.23 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.51 | same | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.42/0.28 | fixed | 00:59-01:09 trade: den Tfeil, ich habe erwartet, dass ich auf dem Telefon etwas bestätige, aber das ist nicht der Fall. da geht der Feil zum Bowser, vielleicht habe ich nur ein bisschen schnell abgesc... | geval: Der Kunde erwähnt, dass er erwartet hatte, auf dem Telefon etwas bestätigen zu müssen, aber dies nicht der Fall war. Dies könnte darauf hindeuten, dass er Informationen vor der Kreditstelle ver... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.49 | broken | 00:30-00:46 access: Ich habe den Zugang noch gar nicht gestartet, ich schaue das abgelaufenen Muster in der Anleitung an, das echte Anmeldenfenster ist zu, es gibt auch keinen Countdown, die Zahl kann... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.49 | same | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.68 | same | 03:34-03:44 access: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - geval_cot: Die Kundenin spricht in Segment [S021] den aktuell gü... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.72 | same | 02:33-02:45 disclosure: Gut, für den jeweiligen Vorgang gehört die richtige Version zum Datum. Die euremeine Sortierung beantwortet aber noch keinen Weg zu einem persönlichen Kontostand. - llm_judge: ... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.70 | same | 03:37-03:46 disclosure: Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - geval_cot: Der Gesprächsfaden zeigt, dass die Beraterin nach best... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.21 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.21 ('Relevante Angabe versc... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.52 | fixed | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.39 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |

## `qwen25_7b__all_plus` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen25_7b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.75 | +0.071 | [-0.036, +0.173] | no detectable difference |
| alarm AUC | 0.79 | 0.85 | +0.060 | [-0.031, +0.164] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen25_7b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.68 | +0.020 | [-0.067, +0.116] | no detectable difference |
| alarm_f1 | 0.49 | 0.71 | +0.222 | [-0.010, +0.435] | no detectable difference |
| false_alarm_rate | 86% | 77% | -9pp | [-29pp, +12pp] | no detectable difference |
| miss_rate | 15% | 15% | +0pp | [-15pp, +14pp] | no detectable difference |
| accuracy | 38% | 42% | +4pp | [-12pp, +22pp] | no detectable difference |
| review_recall | 83% | 67% | -17pp | [-50pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.54 | +0.045 | [-0.081, +0.171] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_7b__all_plus 6, p=0.7539; 3-class only-qwen25_7b 8 vs only-qwen25_7b__all_plus 10, p=0.8145.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen25_7b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.67 | +0.024 | [-0.086, +0.139] | no detectable difference |
| alarm_f1 | 0.17 | 0.52 | +0.345 | [+0.087, +0.625] | **real**: qwen25_7b__all_plus better |
| false_alarm_rate | 55% | 64% | +9pp | [-12pp, +33pp] | no detectable difference |
| miss_rate | 31% | 23% | -8pp | [-23pp, +6pp] | no detectable difference |
| accuracy | 31% | 40% | +8pp | [-7pp, +24pp] | no detectable difference |
| review_recall | 50% | 67% | +17pp | [-50pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.57 | -0.007 | [-0.150, +0.133] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__all_plus 5, p=1.0; 3-class only-qwen25_7b 5 vs only-qwen25_7b__all_plus 9, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen25_7b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.71 | +0.015 | [-0.069, +0.103] | no detectable difference |
| alarm_f1 | 0.61 | 0.71 | +0.099 | [-0.037, +0.257] | no detectable difference |
| false_alarm_rate | 95% | 64% | -32pp | [-50pp, -15pp] | **real**: qwen25_7b__all_plus better |
| miss_rate | 4% | 15% | +12pp | [+0pp, +23pp] | no detectable difference |
| accuracy | 38% | 48% | +10pp | [-4pp, +25pp] | no detectable difference |
| review_recall | 100% | 67% | -33pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.60 | +0.101 | [-0.003, +0.219] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__all_plus 7, p=0.3438; 3-class only-qwen25_7b 5 vs only-qwen25_7b__all_plus 10, p=0.3018.

Flips (cv, 28 calls):

| call | expected | qwen25_7b | qwen25_7b__all_plus | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.09 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | review | 0.54/0.26 | same | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.66 | fixed | 01:05-01:13 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. Ich habe ihr versprochen, ich schicke es niemandem heute hier. - facts: Fakt: Begründet mit nicht öffentlicher... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K2 | no_alert | no_alert | review | 0.42/0.25 | broken | 03:01-03:14 documentation: A, denn das Beispiel im ProK geht es nicht um einen Zusatzsinn von Wo habe. Ich will nicht von der Meldung handeln und habe auch keine Information, die noch nicht publiziert... | geval: Die Kunde möchte den Bericht verstehen, ohne dass relevante Informationen vor der Kreditstelle verborgen werden. Sie betont, dass sie den Bericht selbst lesen will und dass ihr Mann die Depoteü... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.76 | same | 02:27-03:27 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.91 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - anchored: Die Kundin gibt den Zugang... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | review | 0.70/0.66 | same | 00:47-01:30 access: Dann schaue ich zuerst, dass nicht zwei Auflagen miteinander kraten, ist im Browser noch der laufende Anmeldeschritt offen. Bestätigung, und da stark der neue Bestätigungscode ist ... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.27 | fixed | 01:35-02:20 splitting: Gerätewechsel, aber auf dem Blatt, das ich herausgerückt habe, steht der Lehrstofzugang. Ich habe also vermutlich das falsche Blatt ausgenommen und in der Mail schrieb jemand, i... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | review | 0.54/0.33 | same | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.50 | same | 03:01-03:23 documentation: Ich werde diese aus dem ersten Bericht herausnehmen und im nächsten wieder erfassen. Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung se... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | review | 0.54/0.26 | same | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.19 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.43 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - llm_ju... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.46 | same | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.54 | same | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GEOS au... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.80 | same | 00:44-00:57 trade: Es geht um die CRM-Systeme, ich habe die Janet Produz aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt, ich habe letzte Woche einen Bericht über den neuen GoSauftrag... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.82 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.15 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.29 | same | 00:35-00:53 trade: Ich habe gestern den neuen Absatzbericht auf der Merkseite der Albisoptik gelesen, der ging am Morgen an die Medien und für alle verfügbar, es wurde deutlich mehr verkauft als erwar... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.29 | broken | 00:30-00:46 access: Ich habe den Zugang noch gar nicht gestartet, ich schaue das abgelaufenen Muster in der Anleitung an, das echte Anmeldenfenster ist zu, es gibt auch keinen Countdown, die Zahl kann... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.28 | same | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.61 | same | 03:34-03:44 access: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - geval_cot: Die Kundenin spricht in Segment [S021] den aktuell gü... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.77 | same | 02:33-02:45 disclosure: Gut, für den jeweiligen Vorgang gehört die richtige Version zum Datum. Die euremeine Sortierung beantwortet aber noch keinen Weg zu einem persönlichen Kontostand. - llm_judge: ... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.67 | same | 03:32-03:46 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute am Morgen. Dank der FEP, ich schreibe es mit dem Datum auf. - geval_cot: ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.87 | same | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.25 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.25 ('Zugangsinformation pre... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.30 | fixed | 01:40-01:46 documentation: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahl... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.22 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |

## `qwen3_8b__kwpat_facts` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.66 | -0.013 | [-0.169, +0.098] | no detectable difference |
| alarm AUC | 0.79 | 0.79 | -0.001 | [-0.141, +0.099] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.63 | -0.023 | [-0.285, +0.216] | no detectable difference |
| alarm_f1 | 0.49 | 0.46 | -0.026 | [-0.278, +0.200] | no detectable difference |
| false_alarm_rate | 86% | 9% | -77pp | [-100pp, -50pp] | **real**: qwen3_8b__kwpat_facts better |
| miss_rate | 15% | 50% | +35pp | [+7pp, +62pp] | **real**: qwen25_7b better |
| accuracy | 38% | 54% | +17pp | [-10pp, +42pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.70 | +0.213 | [+0.070, +0.369] | **real**: qwen3_8b__kwpat_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 10 vs only-qwen3_8b__kwpat_facts 18, p=0.1849; 3-class only-qwen25_7b 10 vs only-qwen3_8b__kwpat_facts 18, p=0.1849.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.63 | -0.009 | [-0.244, +0.200] | no detectable difference |
| alarm_f1 | 0.17 | 0.46 | +0.288 | [+0.020, +0.572] | **real**: qwen3_8b__kwpat_facts better |
| false_alarm_rate | 55% | 9% | -45pp | [-75pp, -12pp] | **real**: qwen3_8b__kwpat_facts better |
| miss_rate | 31% | 50% | +19pp | [-5pp, +46pp] | no detectable difference |
| accuracy | 31% | 54% | +23pp | [+2pp, +44pp] | **real**: qwen3_8b__kwpat_facts better |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.70 | +0.131 | [-0.033, +0.295] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen3_8b__kwpat_facts 12, p=0.3593; 3-class only-qwen25_7b 3 vs only-qwen3_8b__kwpat_facts 14, p=0.0127.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__kwpat_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.63 | -0.060 | [-0.322, +0.174] | no detectable difference |
| alarm_f1 | 0.61 | 0.46 | -0.150 | [-0.322, +0.000] | no detectable difference |
| false_alarm_rate | 95% | 9% | -86pp | [-100pp, -64pp] | **real**: qwen3_8b__kwpat_facts better |
| miss_rate | 4% | 50% | +46pp | [+20pp, +72pp] | **real**: qwen25_7b better |
| accuracy | 38% | 54% | +17pp | [-12pp, +44pp] | no detectable difference |
| review_recall | 100% | 0% | -100pp | [-100pp, -100pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.70 | +0.201 | [+0.071, +0.344] | **real**: qwen3_8b__kwpat_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 12 vs only-qwen3_8b__kwpat_facts 19, p=0.281; 3-class only-qwen25_7b 11 vs only-qwen3_8b__kwpat_facts 19, p=0.2005.

Flips (cv, 33 calls):

| call | expected | qwen25_7b | qwen3_8b__kwpat_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.45 | fixed | 01:33-01:39 trade: Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mich machen? - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - De... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.09 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.09 ('Insiderhandel') liegt unter 0.15... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.97 | same | 02:29-03:29 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.16 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.1... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.06 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.06 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.04 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.04 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.87/0.83 | same | 00:30-00:33 documentation: Gut, dass Sie dies melden. Unsere Kreditstellung? - facts: Fakt: Verborgene Tatsache ist relevant = ja (0.79) - Der Kreditberater erwähnt, dass relevante Informationen für d... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.04 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.45 (Schwelle 0.60 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.45 (Schwelle 0.60 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.39 | same | 01:20-01:27 splitting: Sie arbeiten nicht bei dieser Firma, ich weiss nichts zu ersetzen und habe den gleichen Inhalt wie alle anderen Anweger. - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.39 | same | 01:56-02:05 splitting: Dann sollte sie das Geld für den Umzug nicht auch noch für das Depot einplanen, für welche Ausgaben haben sie schon etwas auf die Seite gelegt, - facts: Fakt: Aufteilung in Teil... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.39 | same | 00:14-00:30 splitting: Ja, aber ich möchte zwei Sachen nicht durcheinanderbringen, ich habe ein Depot und ein separates Konto für den Umzug, ich möchte mich informieren, ohne jetzt in Kauf zu verlange... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen3_8b__facts_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.74 | +0.059 | [-0.041, +0.145] | no detectable difference |
| alarm AUC | 0.79 | 0.83 | +0.035 | [-0.080, +0.128] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.63 | -0.023 | [-0.285, +0.216] | no detectable difference |
| alarm_f1 | 0.49 | 0.74 | +0.255 | [+0.026, +0.494] | **real**: qwen3_8b__facts_only better |
| false_alarm_rate | 86% | 9% | -77pp | [-100pp, -50pp] | **real**: qwen3_8b__facts_only better |
| miss_rate | 15% | 50% | +35pp | [+7pp, +62pp] | **real**: qwen25_7b better |
| accuracy | 38% | 69% | +31pp | [+5pp, +56pp] | **real**: qwen3_8b__facts_only better |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.70 | +0.213 | [+0.070, +0.369] | **real**: qwen3_8b__facts_only better |

McNemar exact (calls): flag correct only-qwen25_7b 10 vs only-qwen3_8b__facts_only 18, p=0.1849; 3-class only-qwen25_7b 8 vs only-qwen3_8b__facts_only 23, p=0.0107.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.63 | -0.009 | [-0.244, +0.200] | no detectable difference |
| alarm_f1 | 0.17 | 0.62 | +0.451 | [+0.145, +0.750] | **real**: qwen3_8b__facts_only better |
| false_alarm_rate | 55% | 9% | -45pp | [-75pp, -12pp] | **real**: qwen3_8b__facts_only better |
| miss_rate | 31% | 50% | +19pp | [-5pp, +46pp] | no detectable difference |
| accuracy | 31% | 62% | +31pp | [+9pp, +52pp] | **real**: qwen3_8b__facts_only better |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.70 | +0.131 | [-0.033, +0.295] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen3_8b__facts_only 12, p=0.3593; 3-class only-qwen25_7b 3 vs only-qwen3_8b__facts_only 18, p=0.0015.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__facts_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.63 | -0.060 | [-0.322, +0.174] | no detectable difference |
| alarm_f1 | 0.61 | 0.57 | -0.040 | [-0.182, +0.081] | no detectable difference |
| false_alarm_rate | 95% | 9% | -86pp | [-100pp, -64pp] | **real**: qwen3_8b__facts_only better |
| miss_rate | 4% | 50% | +46pp | [+20pp, +72pp] | **real**: qwen25_7b better |
| accuracy | 38% | 58% | +21pp | [-7pp, +46pp] | no detectable difference |
| review_recall | 100% | 0% | -100pp | [-100pp, -100pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.70 | +0.201 | [+0.071, +0.344] | **real**: qwen3_8b__facts_only better |

McNemar exact (calls): flag correct only-qwen25_7b 12 vs only-qwen3_8b__facts_only 19, p=0.281; 3-class only-qwen25_7b 10 vs only-qwen3_8b__facts_only 20, p=0.0987.

Flips (cv, 33 calls):

| call | expected | qwen25_7b | qwen3_8b__facts_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.50 | fixed | 01:37-01:39 trade: Können Sie den Kaufleit für mich machen? - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde äußert seinen konkreten Kaufwunsch für eine Aktie, indem er fragt: 'K... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.99 | same | 02:27-03:27 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/1.00 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - facts: Fakt: Wert gehört zum lau... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.09 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:29 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für 6000 Franken aktiv von den Seerland Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. D... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.50 | same | 03:28-03:41 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, können Sie den einmaligen Auftrag für mich entgegnen... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.50 | same | 03:31-03:43 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht will ich nicht für 5000 Franken Aktien von der Albisoptik kaufen, können Sie den einmaligen Auftrag für mich entgegennehm... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen3_8b__judge_facts` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.76 | +0.082 | [-0.027, +0.166] | no detectable difference |
| alarm AUC | 0.79 | 0.92 | +0.124 | [+0.038, +0.205] | **real**: qwen3_8b__judge_facts better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.74 | +0.079 | [+0.000, +0.191] | no detectable difference |
| alarm_f1 | 0.49 | 0.57 | +0.084 | [-0.133, +0.264] | no detectable difference |
| false_alarm_rate | 86% | 77% | -9pp | [-30pp, +0pp] | no detectable difference |
| miss_rate | 15% | 4% | -12pp | [-30pp, +0pp] | no detectable difference |
| accuracy | 38% | 38% | +0pp | [-12pp, +14pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.59 | +0.103 | [+0.000, +0.236] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 0 vs only-qwen3_8b__judge_facts 5, p=0.0625; 3-class only-qwen25_7b 4 vs only-qwen3_8b__judge_facts 4, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.70 | +0.056 | [-0.069, +0.205] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 68% | +14pp | [-8pp, +39pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-36pp, +4pp] | no detectable difference |
| accuracy | 31% | 19% | -12pp | [-27pp, +0pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.58 | +0.009 | [-0.156, +0.161] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen3_8b__judge_facts 6, p=1.0; 3-class only-qwen25_7b 7 vs only-qwen3_8b__judge_facts 1, p=0.0703.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__judge_facts - qwen25_7b

| metric | qwen25_7b | qwen3_8b__judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.70 | +0.004 | [-0.125, +0.127] | no detectable difference |
| alarm_f1 | 0.61 | 0.57 | -0.040 | [-0.182, +0.081] | no detectable difference |
| false_alarm_rate | 95% | 68% | -27pp | [-55pp, -5pp] | **real**: qwen3_8b__judge_facts better |
| miss_rate | 4% | 15% | +12pp | [-6pp, +32pp] | no detectable difference |
| accuracy | 38% | 35% | -2pp | [-19pp, +16pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.58 | +0.079 | [-0.077, +0.244] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen3_8b__judge_facts 7, p=0.5488; 3-class only-qwen25_7b 8 vs only-qwen3_8b__judge_facts 7, p=1.0.

Flips (cv, 21 calls):

| call | expected | qwen25_7b | qwen3_8b__judge_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K2 | no_alert | alarm | review | 0.54/0.45 | same | 00:24-01:24 disclosure: Wir schauen zuerst, ob beides wirklich gebraucht ist, ihre Identität ist über der VWinboat wirklich. Bezug auf bestätigt. Weiter lesen wir wieder im Code oder das ganze Zahlung... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.81 | fixed | 01:05-01:13 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. Ich habe ihr versprochen, ich schicke es niemandem heute hier. - llm_judge: Der Kunde erwähnt, dass er den Kau... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.97 | same | 02:20-03:20 trade: Und was hat jetzt der Ausschlag gegeben, dass Sie gerade diese viermal kaufen möchten? Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.92 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - facts: Fakt: Wert gehört zum lau... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | review | 0.70/0.57 | same | 01:18-01:42 access: Warte, ich sage Ihnen die Planung gerade, 7, 3, 1, 9, 4, 2, es steht immer noch geültig. Können Sie mir sagen, ob das die richtige Reihe in Folge ist? Kurs, bitte nicht mehr vorzul... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.15 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.16 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.47 | same | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | review | 0.54/0.47 | same | 02:55-03:55 splitting: Das passt zu meinem Zwischenresultat. Ich hatte noch eine Ausgabe im April drin, deshalb war meine Zahl tiefer. Ich werde Sie aus dem ersten Bericht herausnehmen und im nächsten... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.45 | same | 01:43-02:20 splitting: Also von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, sie haben von ihm gesagt, ich soll warten, aber ich habe sie jetzt ... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.80 | same | 05:22-06:22 splitting: Gut, ich habe noch die Schlussrechnung für das Zeugeln im Kopf. Der Vorschuss wäre jetzt fällig, der Rest nach dem Umzug. Ich habe das Geld für beides zusammen auf die Seite gel... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.59 | same | 05:35-06:29 trade: Muss ich darum den zweiten Termin auch schon jetzt in die Zahlungsformula eingefegen, wenn Betrag und Fällige von Risch nicht feststehen, sollten sie sie nicht als bestätigte Rechnu... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.56 | same | 07:57-08:57 splitting: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, de... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C08-K3 | no_alert | alarm | review | 0.52/0.25 | same | 01:04-01:18 splitting: Fals ich mich dafür entscheiden, wäre meine Obergrenze 5000 Franken aus meinem Sparkonto, meine Miete und Versicherung sind separat reserviert, für das Formular möchte ich nur e... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.45 | same | 01:05-01:19 splitting: Entschapfe ich mich den entscheidenden, wenn meine Obergrenzen 5000 Franken aus meinem Sparkonto, meine Miete und die Versicherung sind separat gepreserviert, für das Formular m... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.37/0.45 | fixed | 01:44-02:00 splitting: Wollen Sie sich die Stellen aus dem Feld vorbauen, 8-3-6-1-7-4? Bitte keine weiteren Zahl von auszulesen, wir gehen in den Schweiz zurück und sortieren die Fenster, bevor sie et... | geval: Die Kunde erwähnt, dass sie den Pfeil gesehen hat, der zum Browser zeigt, was darauf hindeutet, dass sie möglicherweise einen Zugangsinformationen-Pfad durchschritten hat. Allerdings wurde kein... |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.42/0.25 | fixed | 00:31-00:46 splitting: Ich habe gerade selbst die Anmeldung gestartet, im echten Fenster stark bewertet gilt, wie sich die Anmeldung abschiessen oder abbrechen, es gibt auch keinen Counton, ich habe k... | geval: Der Kunde erwähnt, dass er erwartet hatte, auf dem Telefon etwas bestätigen zu müssen, aber dies nicht der Fall war. Dies könnte darauf hindeuten, dass er Informationen vor der Kreditstelle ver... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.46 | same | 00:23-01:05 disclosure: Wir müssen vor einer konkreten Auskunft festhalten, welche Rollen sie in diesem Vorgang haben. Es geht um das persönliche Konto ihrer Mutter, richtig? Richtig. Wir haben einen ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.46 | same | 00:05-01:05 disclosure: Guten Morgen Frau Pé, da ist Marion Bure, Sie haben wegen der laufenden Wundkosten ihrer Mutter um einen Rücken zu beten. Ja, sie ist zurzeit im Spital und ich ordne mit ihr di... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.46 | same | 03:29-03:39 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. - llm_judge: Die Beraterin gibt konkrete Auskunft über den Kontos... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.49 | same | 01:05-01:17 splitting: Gutes, ich habe Ihre Erklärung gehört, ich habe noch eine allgemeine Frage zur Heimrechnung. Sie kommt immer am Abend im Postfach, aber das Zahlungsdatum ist schon zwei Tage spä... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |

## `qwen3_8b__gcot` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__gcot - qwen25_7b

| metric | qwen25_7b | qwen3_8b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.67 | -0.004 | [-0.140, +0.096] | no detectable difference |
| alarm AUC | 0.79 | 0.77 | -0.018 | [-0.158, +0.098] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__gcot - qwen25_7b

| metric | qwen25_7b | qwen3_8b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.74 | +0.086 | [+0.025, +0.182] | **real**: qwen3_8b__gcot better |
| alarm_f1 | 0.49 | 0.69 | +0.198 | [-0.029, +0.459] | no detectable difference |
| false_alarm_rate | 86% | 82% | -5pp | [-32pp, +22pp] | no detectable difference |
| miss_rate | 15% | 0% | -15pp | [-35pp, +0pp] | no detectable difference |
| accuracy | 38% | 46% | +8pp | [-8pp, +27pp] | no detectable difference |
| review_recall | 83% | 100% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.59 | +0.100 | [-0.008, +0.238] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen3_8b__gcot 7, p=0.1797; 3-class only-qwen25_7b 5 vs only-qwen3_8b__gcot 9, p=0.424.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__gcot - qwen25_7b

| metric | qwen25_7b | qwen3_8b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.61 | -0.030 | [-0.206, +0.160] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 77% | +23pp | [+5pp, +45pp] | **real**: qwen25_7b better |
| miss_rate | 31% | 27% | -4pp | [-35pp, +27pp] | no detectable difference |
| accuracy | 31% | 23% | -8pp | [-23pp, +9pp] | no detectable difference |
| review_recall | 50% | 100% | +50pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.48 | -0.094 | [-0.250, +0.068] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 12 vs only-qwen3_8b__gcot 8, p=0.5034; 3-class only-qwen25_7b 7 vs only-qwen3_8b__gcot 3, p=0.3438.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__gcot - qwen25_7b

| metric | qwen25_7b | qwen3_8b__gcot | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.73 | +0.038 | [+0.000, +0.096] | no detectable difference |
| alarm_f1 | 0.61 | 0.69 | +0.075 | [-0.101, +0.310] | no detectable difference |
| false_alarm_rate | 95% | 86% | -9pp | [-33pp, +10pp] | no detectable difference |
| miss_rate | 4% | 0% | -4pp | [-12pp, +0pp] | no detectable difference |
| accuracy | 38% | 44% | +6pp | [-7pp, +21pp] | no detectable difference |
| review_recall | 100% | 100% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.57 | +0.065 | [-0.014, +0.182] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 1 vs only-qwen3_8b__gcot 4, p=0.375; 3-class only-qwen25_7b 3 vs only-qwen3_8b__gcot 6, p=0.5078.

Flips (cv, 23 calls):

| call | expected | qwen25_7b | qwen3_8b__gcot | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.43 | fixed | 01:32-01:52 access: Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, 2, 4, 2. Dank geht das Land für die Ordnung, der Eintrag mit dem Ursymbol bei Reservation au... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | review | 0.54/0.71 | same | 00:24-01:24 disclosure: Wir schauen zuerst, ob beides wirklich gebraucht ist, ihre Identität ist über der VWinboat wirklich. Bezug auf bestätigt. Weiter lesen wir wieder im Code oder das ganze Zahlung... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.71 | fixed | 01:05-01:13 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. Ich habe ihr versprochen, ich schicke es niemandem heute hier. - llm_judge: Der Kunde erwähnt, dass er den Kau... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.86 | same | 02:20-02:45 trade: Und was hat jetzt der Ausschlag gegeben, dass Sie gerade diese viermal kaufen möchten? Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.40 | fixed | 03:20-03:49 disclosure: weil neues Gerät registrieren und der Bestätigungskode auf dem Musterbild ist 482601, das ist die abgelaufene Beispielzahl, wie meine, ich habe keinen aktuellen Code zum Teilen... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.36 | fixed | 00:28-00:28 access: Gut, nicht fehlen die zwei Sachen. Für das Passwort sagen Sie mir bitte nur, - keywords: Stichwort K10 «Passwort» (Zugangswörter) | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.72 | same | 02:40-03:30 disclosure: Für das bestätigte Vereinskonto ist der Stand am 31. März 14.200 Pfand. Die gleiche Zahl steht im Dokument, das ich Ihnen bereitstelle. Das passt zu meinem Zwischenresultat. Ic... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D09-K2 | alarm | alarm | review | 0.87/0.72 | same | 02:39-03:39 splitting: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen und d... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.70 | same | 01:43-02:20 splitting: Also von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, sie haben von ihm gesagt, ich soll warten, aber ich habe sie jetzt ... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.70 | same | 08:28-09:28 documentation: Okay, ich mache im Formular jetzt keine eigene zusätzliche Fassung. Ich werde nicht nachher zwei Anfragen im System haben, die jemand für zwei verschiedene Aufträge hält. Da... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.59 | same | 07:37-07:48 documentation: Ich habe die ganze Zeit auch an die offenen Umzugschosten gedämpft, die müssen zuerst für mich übersichtlich sein. Dann sagen Sie mir jetzt bitte genau, was Sie wollen. - ll... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.70 | same | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C08-K3 | no_alert | alarm | review | 0.52/0.54 | same | 01:04-01:18 splitting: Fals ich mich dafür entscheiden, wäre meine Obergrenze 5000 Franken aus meinem Sparkonto, meine Miete und Versicherung sind separat reserviert, für das Formular möchte ich nur e... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.71 | same | 01:05-01:19 splitting: Entschapfe ich mich den entscheidenden, wenn meine Obergrenzen 5000 Franken aus meinem Sparkonto, meine Miete und die Versicherung sind separat gepreserviert, für das Formular m... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.37/0.71 | fixed | 01:44-02:00 splitting: Wollen Sie sich die Stellen aus dem Feld vorbauen, 8-3-6-1-7-4? Bitte keine weiteren Zahl von auszulesen, wir gehen in den Schweiz zurück und sortieren die Fenster, bevor sie et... | geval: Die Kunde erwähnt, dass sie den Pfeil gesehen hat, der zum Browser zeigt, was darauf hindeutet, dass sie möglicherweise einen Zugangsinformationen-Pfad durchschritten hat. Allerdings wurde kein... |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.42/0.44 | fixed | 00:31-00:46 splitting: Ich habe gerade selbst die Anmeldung gestartet, im echten Fenster stark bewertet gilt, wie sich die Anmeldung abschiessen oder abbrechen, es gibt auch keinen Counton, ich habe k... | geval: Der Kunde erwähnt, dass er erwartet hatte, auf dem Telefon etwas bestätigen zu müssen, aber dies nicht der Fall war. Dies könnte darauf hindeuten, dass er Informationen vor der Kreditstelle ver... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.51 | broken | 01:23-02:23 access: Jetzt habe ich den Pfeil gesehen, ich habe nur ein Bild vergrößert, keine anderen Tab aufgerufen. Das Pfeil, das ich meine, ist immer noch das Dienchen. Schliessen wird überraschte... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.31/0.51 | broken | 01:24-02:24 access: Jetzt habe ich den Pfeil gesehen, ich habe nur ein Bild vergrössert, keinen anderen Tab aufgerufen, das Pfeil, das ich meine, ist immer noch das Gleiche. Schliessen wird überrascht... | geval: Die Kundin erwähnt, dass sie ein abgelaufenes Muster in der Anleitung ansieht und keine Zahl gebraucht werden kann. Sie beschreibt jedoch den Titel des Fensters, der 836174 lautet, was als Zuga... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.71 | same | 00:46-01:05 disclosure: Ihre eigene Identität ist bestätigt, für das Konto Ihrer Mutter ist das Auskunftsrecht hinterlegt und geblügt. In diesem Vorgang haben Sie die gültige Berechtigung zum Kontosta... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.70 | same | 01:05-01:17 splitting: Gutes, ich habe Ihre Erklärung gehört, ich habe noch eine allgemeine Frage zur Heimrechnung. Sie kommt immer am Abend im Postfach, aber das Zahlungsdatum ist schon zwei Tage spä... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.71 | same | 07:54-08:19 documentation: Dann lehnt ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich ... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.71 | same | 07:57-08:49 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.45 | fixed | 00:35-01:19 documentation: Sie sagte, es sei alles erledigt. Ich habe aber nur eine Nachricht von ihr auf meinem Telefon und weiss nicht, was bei ihr tatsächlich erpasst ist. Ich habe keine Bestätigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |

## `qwen3_8b__all_plus` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen3_8b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.73 | +0.052 | [-0.052, +0.133] | no detectable difference |
| alarm AUC | 0.79 | 0.88 | +0.093 | [+0.032, +0.152] | **real**: qwen3_8b__all_plus better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen3_8b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.71 | +0.058 | [+0.009, +0.129] | **real**: qwen3_8b__all_plus better |
| alarm_f1 | 0.49 | 0.52 | +0.031 | [-0.231, +0.240] | no detectable difference |
| false_alarm_rate | 86% | 86% | +0pp | [-21pp, +25pp] | no detectable difference |
| miss_rate | 15% | 4% | -12pp | [-30pp, +0pp] | no detectable difference |
| accuracy | 38% | 31% | -6pp | [-19pp, +8pp] | no detectable difference |
| review_recall | 83% | 83% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.55 | +0.058 | [-0.026, +0.150] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen3_8b__all_plus 5, p=0.4531; 3-class only-qwen25_7b 6 vs only-qwen3_8b__all_plus 3, p=0.5078.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen3_8b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.71 | +0.071 | [-0.046, +0.206] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 86% | +32pp | [+9pp, +58pp] | **real**: qwen25_7b better |
| miss_rate | 31% | 4% | -27pp | [-47pp, -8pp] | **real**: qwen3_8b__all_plus better |
| accuracy | 31% | 17% | -15pp | [-30pp, +2pp] | no detectable difference |
| review_recall | 50% | 83% | +33pp | [+0pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.55 | -0.024 | [-0.173, +0.109] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen3_8b__all_plus 7, p=1.0; 3-class only-qwen25_7b 9 vs only-qwen3_8b__all_plus 2, p=0.0654.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__all_plus - qwen25_7b

| metric | qwen25_7b | qwen3_8b__all_plus | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.71 | +0.020 | [-0.032, +0.069] | no detectable difference |
| alarm_f1 | 0.61 | 0.52 | -0.093 | [-0.281, +0.047] | no detectable difference |
| false_alarm_rate | 95% | 86% | -9pp | [-27pp, +8pp] | no detectable difference |
| miss_rate | 4% | 4% | +0pp | [-11pp, +12pp] | no detectable difference |
| accuracy | 38% | 31% | -6pp | [-17pp, +5pp] | no detectable difference |
| review_recall | 100% | 83% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.55 | +0.045 | [-0.033, +0.131] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen3_8b__all_plus 4, p=0.6875; 3-class only-qwen25_7b 6 vs only-qwen3_8b__all_plus 3, p=0.5078.

Flips (cv, 23 calls):

| call | expected | qwen25_7b | qwen3_8b__all_plus | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.26 | fixed | 01:32-01:52 access: Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, 2, 4, 2. Dank geht das Land für die Ordnung, der Eintrag mit dem Ursymbol bei Reservation au... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | review | 0.54/0.47 | same | 00:24-01:24 disclosure: Wir schauen zuerst, ob beides wirklich gebraucht ist, ihre Identität ist über der VWinboat wirklich. Bezug auf bestätigt. Weiter lesen wir wieder im Code oder das ganze Zahlung... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.71 | fixed | 01:05-01:13 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. Ich habe ihr versprochen, ich schicke es niemandem heute hier. - llm_judge: Der Kunde erwähnt, dass er den Kau... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.90 | same | 02:20-03:20 trade: Und was hat jetzt der Ausschlag gegeben, dass Sie gerade diese viermal kaufen möchten? Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K2 | alarm | alarm | review | 0.70/0.55 | same | 01:03-02:03 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. Weiter grenzen Sie der Welt selb... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.30 | fixed | 03:20-04:20 access: weil neues Gerät registrieren und der Bestätigungskode auf dem Musterbild ist 482601, das ist die abgelaufene Beispielzahl, wie meine, ich habe keinen aktuellen Code zum Teilen. Ve... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | review | 0.54/0.29 | same | 03:21-03:34 access: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. - anchored: Der Kunde nennt den Bestätigung... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | review | 0.70/0.51 | same | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | review | 0.54/0.48 | same | 02:55-03:55 splitting: Das passt zu meinem Zwischenresultat. Ich hatte noch eine Ausgabe im April drin, deshalb war meine Zahl tiefer. Ich werde Sie aus dem ersten Bericht herausnehmen und im nächsten... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.47 | same | 01:43-02:20 splitting: Also von mir selber. Der Händler hat mir keine Nachricht mit dem Wunsch nach einer Zahl geschickt. Ich weiss, sie haben von ihm gesagt, ich soll warten, aber ich habe sie jetzt ... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.68 | same | 07:58-08:17 trade: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er ist. Ich h... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.55 | same | 05:35-06:29 trade: Muss ich darum den zweiten Termin auch schon jetzt in die Zahlungsformula eingefegen, wenn Betrag und Fällige von Risch nicht feststehen, sollten sie sie nicht als bestätigte Rechnu... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.51 | same | 05:57-06:57 splitting: 800 Franken bis Ende September. Ich habe aber erst zwei Aufträte und mich noch nicht für eine Firma entschieden. Wie der zweite ist der Vorschuss anders. Dann warte ich mit eine... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C08-K3 | no_alert | alarm | review | 0.52/0.33 | same | 01:04-01:18 splitting: Fals ich mich dafür entscheiden, wäre meine Obergrenze 5000 Franken aus meinem Sparkonto, meine Miete und Versicherung sind separat reserviert, für das Formular möchte ich nur e... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.46 | same | 01:05-01:19 splitting: Entschapfe ich mich den entscheidenden, wenn meine Obergrenzen 5000 Franken aus meinem Sparkonto, meine Miete und die Versicherung sind separat gepreserviert, für das Formular m... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.37/0.46 | fixed | 01:44-02:00 splitting: Wollen Sie sich die Stellen aus dem Feld vorbauen, 8-3-6-1-7-4? Bitte keine weiteren Zahl von auszulesen, wir gehen in den Schweiz zurück und sortieren die Fenster, bevor sie et... | geval: Die Kunde erwähnt, dass sie den Pfeil gesehen hat, der zum Browser zeigt, was darauf hindeutet, dass sie möglicherweise einen Zugangsinformationen-Pfad durchschritten hat. Allerdings wurde kein... |
| Stufe2_C09-K4 | alarm | no_alert | review | 0.42/0.26 | fixed | 00:31-00:46 splitting: Ich habe gerade selbst die Anmeldung gestartet, im echten Fenster stark bewertet gilt, wie sich die Anmeldung abschiessen oder abbrechen, es gibt auch keinen Counton, ich habe k... | geval: Der Kunde erwähnt, dass er erwartet hatte, auf dem Telefon etwas bestätigen zu müssen, aber dies nicht der Fall war. Dies könnte darauf hindeuten, dass er Informationen vor der Kreditstelle ver... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.31 | broken | 01:23-02:23 access: Jetzt habe ich den Pfeil gesehen, ich habe nur ein Bild vergrößert, keine anderen Tab aufgerufen. Das Pfeil, das ich meine, ist immer noch das Dienchen. Schliessen wird überraschte... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.31/0.31 | broken | 01:24-02:24 access: Jetzt habe ich den Pfeil gesehen, ich habe nur ein Bild vergrössert, keinen anderen Tab aufgerufen, das Pfeil, das ich meine, ist immer noch das Gleiche. Schliessen wird überrascht... | geval: Die Kundin erwähnt, dass sie ein abgelaufenes Muster in der Anleitung ansieht und keine Zahl gebraucht werden kann. Sie beschreibt jedoch den Titel des Fensters, der 836174 lautet, was als Zuga... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.47 | same | 00:23-01:05 disclosure: Wir müssen vor einer konkreten Auskunft festhalten, welche Rollen sie in diesem Vorgang haben. Es geht um das persönliche Konto ihrer Mutter, richtig? Richtig. Wir haben einen ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.47 | same | 00:05-01:05 disclosure: Guten Morgen Frau Pé, da ist Marion Bure, Sie haben wegen der laufenden Wundkosten ihrer Mutter um einen Rücken zu beten. Ja, sie ist zurzeit im Spital und ich ordne mit ihr di... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.47 | same | 03:29-03:39 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute Morgen. - llm_judge: Die Beraterin gibt konkrete Auskunft über den Kontos... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.49 | same | 01:05-01:17 splitting: Gutes, ich habe Ihre Erklärung gehört, ich habe noch eine allgemeine Frage zur Heimrechnung. Sie kommt immer am Abend im Postfach, aber das Zahlungsdatum ist schon zwei Tage spä... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |

## `qwen25_7b__hybrid` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.82 | +0.142 | [+0.043, +0.263] | **real**: qwen25_7b__hybrid better |
| alarm AUC | 0.79 | 0.88 | +0.083 | [+0.005, +0.153] | **real**: qwen25_7b__hybrid better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.75 | +0.088 | [-0.056, +0.240] | no detectable difference |
| alarm_f1 | 0.49 | 0.75 | +0.262 | [+0.114, +0.428] | **real**: qwen25_7b__hybrid better |
| false_alarm_rate | 86% | 27% | -59pp | [-83pp, -33pp] | **real**: qwen25_7b__hybrid better |
| miss_rate | 15% | 27% | +12pp | [-6pp, +31pp] | no detectable difference |
| accuracy | 38% | 69% | +31pp | [+10pp, +50pp] | **real**: qwen25_7b__hybrid better |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.73 | +0.238 | [+0.099, +0.385] | **real**: qwen25_7b__hybrid better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__hybrid 15, p=0.0414; 3-class only-qwen25_7b 4 vs only-qwen25_7b__hybrid 19, p=0.0026.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.72 | +0.077 | [-0.040, +0.193] | no detectable difference |
| alarm_f1 | 0.17 | 0.48 | +0.309 | [-0.225, +0.667] | no detectable difference |
| false_alarm_rate | 55% | 27% | -27pp | [-50pp, -7pp] | **real**: qwen25_7b__hybrid better |
| miss_rate | 31% | 31% | +0pp | [-18pp, +20pp] | no detectable difference |
| accuracy | 31% | 54% | +23pp | [+4pp, +40pp] | **real**: qwen25_7b__hybrid better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.71 | +0.136 | [+0.021, +0.245] | **real**: qwen25_7b__hybrid better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_7b__hybrid 10, p=0.1796; 3-class only-qwen25_7b 3 vs only-qwen25_7b__hybrid 14, p=0.0127.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.75 | +0.051 | [-0.099, +0.199] | no detectable difference |
| alarm_f1 | 0.61 | 0.76 | +0.154 | [+0.054, +0.279] | **real**: qwen25_7b__hybrid better |
| false_alarm_rate | 95% | 27% | -68pp | [-92pp, -44pp] | **real**: qwen25_7b__hybrid better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 67% | +29pp | [+8pp, +48pp] | **real**: qwen25_7b__hybrid better |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.73 | +0.226 | [+0.096, +0.362] | **real**: qwen25_7b__hybrid better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__hybrid 15, p=0.0784; 3-class only-qwen25_7b 4 vs only-qwen25_7b__hybrid 18, p=0.0043.

Flips (cv, 28 calls):

| call | expected | qwen25_7b | qwen25_7b__hybrid | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.97 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.92 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code/Wert am Telefon vo... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.08 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.62 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Zweitm... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.04 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.97 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 08:21-08:46 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechsel. Dann be... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.97 | same | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.85 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__hybrid_kw` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.76 | +0.087 | [-0.025, +0.206] | no detectable difference |
| alarm AUC | 0.79 | 0.85 | +0.054 | [-0.007, +0.121] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.73 | +0.074 | [-0.070, +0.217] | no detectable difference |
| alarm_f1 | 0.49 | 0.26 | -0.227 | [-0.561, +0.108] | no detectable difference |
| false_alarm_rate | 86% | 32% | -55pp | [-82pp, -27pp] | **real**: qwen25_7b__hybrid_kw better |
| miss_rate | 15% | 27% | +12pp | [-5pp, +32pp] | no detectable difference |
| accuracy | 38% | 42% | +4pp | [-22pp, +28pp] | no detectable difference |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.71 | +0.215 | [+0.065, +0.363] | **real**: qwen25_7b__hybrid_kw better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__hybrid_kw 14, p=0.0636; 3-class only-qwen25_7b 12 vs only-qwen25_7b__hybrid_kw 14, p=0.845.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.73 | +0.088 | [-0.016, +0.186] | no detectable difference |
| alarm_f1 | 0.17 | 0.26 | +0.087 | [-0.364, +0.500] | no detectable difference |
| false_alarm_rate | 55% | 32% | -23pp | [-45pp, +0pp] | no detectable difference |
| miss_rate | 31% | 27% | -4pp | [-21pp, +13pp] | no detectable difference |
| accuracy | 31% | 42% | +10pp | [-7pp, +27pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.71 | +0.133 | [+0.018, +0.233] | **real**: qwen25_7b__hybrid_kw better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__hybrid_kw 9, p=0.146; 3-class only-qwen25_7b 4 vs only-qwen25_7b__hybrid_kw 9, p=0.2668.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen25_7b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.75 | +0.051 | [-0.103, +0.196] | no detectable difference |
| alarm_f1 | 0.61 | 0.26 | -0.350 | [-0.621, -0.094] | **real**: qwen25_7b better |
| false_alarm_rate | 95% | 27% | -68pp | [-92pp, -44pp] | **real**: qwen25_7b__hybrid_kw better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +42pp] | **real**: qwen25_7b better |
| accuracy | 38% | 44% | +6pp | [-21pp, +30pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.73 | +0.226 | [+0.097, +0.359] | **real**: qwen25_7b__hybrid_kw better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__hybrid_kw 15, p=0.0784; 3-class only-qwen25_7b 12 vs only-qwen25_7b__hybrid_kw 15, p=0.7011.

Flips (cv, 31 calls):

| call | expected | qwen25_7b | qwen25_7b__hybrid_kw | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.78 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.95 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K2 | alarm | alarm | review | 0.70/0.27 | same | 01:18-01:30 access: Warte, ich sage Ihnen die Planung gerade, 7, 3, 1, 9, 4, 2, es steht immer noch geültig. Können Sie mir sagen, ob das die richtige Reihe in Folge ist? - patterns: Kundschaft liest ... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.14 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.14 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.11 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.10 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.68 | same | 02:37-02:52 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.87/0.80 | same | 00:43-01:00 documentation: Es sind 20 000 Franken meiner Tante. Ich muss jetzt zurückzahlen, und wir haben jetzt einen Unterschritt nicht vereinbart. Verwescht sind meine eigenen Ersparnisse. Ich kenn... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.72 | same | 01:32-01:58 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe stellt die ganze Rechnung überhaupt sieht. Können Sie mir z... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.95/0.79 | same | 01:33-01:50 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe-Stell die ganze Rechnung überhaupt sieht. Können Sie mir ja... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.57 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Zweitm... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.72 | same | 00:44-00:57 trade: Es geht um die CRM-Systeme, ich habe die Janet Produz aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt, ich habe letzte Woche einen Bericht über den neuen GoSauftrag... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.03 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.27 | same | 03:52-04:01 disclosure: Für den Vorgang halte ich fest, was am Telefon besprochen wurde. Ich bestätige damit keine Zahlung und ändere keine Berechtigung. - facts: Fakt: Konkrete Daten einer Drittperso... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.27 | same | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.67 | same | 00:51-01:03 disclosure: Sie haben aber kein Auskundsrecht hinterlegt und die Abfährung ergeben, dass sie im dem Vorgang keine Berechtigung zum Kontostand haben. Die familiäre Beziehung allein lehnt da... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.27 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.20 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.27 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen3_8b__hybrid` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.76 | +0.085 | [-0.061, +0.231] | no detectable difference |
| alarm AUC | 0.79 | 0.79 | -0.006 | [-0.154, +0.105] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.71 | +0.049 | [-0.095, +0.193] | no detectable difference |
| alarm_f1 | 0.49 | 0.74 | +0.255 | [+0.026, +0.494] | **real**: qwen3_8b__hybrid better |
| false_alarm_rate | 86% | 32% | -55pp | [-93pp, -12pp] | **real**: qwen3_8b__hybrid better |
| miss_rate | 15% | 31% | +15pp | [-9pp, +41pp] | no detectable difference |
| accuracy | 38% | 67% | +29pp | [+8pp, +50pp] | **real**: qwen3_8b__hybrid better |
| review_recall | 83% | 67% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.69 | +0.196 | [+0.036, +0.370] | **real**: qwen3_8b__hybrid better |

McNemar exact (calls): flag correct only-qwen25_7b 8 vs only-qwen3_8b__hybrid 16, p=0.1516; 3-class only-qwen25_7b 6 vs only-qwen3_8b__hybrid 20, p=0.0094.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.71 | +0.063 | [-0.089, +0.225] | no detectable difference |
| alarm_f1 | 0.17 | 0.62 | +0.451 | [+0.145, +0.750] | **real**: qwen3_8b__hybrid better |
| false_alarm_rate | 55% | 32% | -23pp | [-50pp, +14pp] | no detectable difference |
| miss_rate | 31% | 31% | +0pp | [-29pp, +27pp] | no detectable difference |
| accuracy | 31% | 60% | +29pp | [+8pp, +50pp] | **real**: qwen3_8b__hybrid better |
| review_recall | 50% | 67% | +17pp | [-50pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.69 | +0.114 | [-0.036, +0.267] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen3_8b__hybrid 12, p=0.3593; 3-class only-qwen25_7b 3 vs only-qwen3_8b__hybrid 17, p=0.0026.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__hybrid - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.71 | +0.011 | [-0.155, +0.167] | no detectable difference |
| alarm_f1 | 0.61 | 0.57 | -0.040 | [-0.182, +0.081] | no detectable difference |
| false_alarm_rate | 95% | 32% | -64pp | [-100pp, -29pp] | **real**: qwen3_8b__hybrid better |
| miss_rate | 4% | 31% | +27pp | [+5pp, +50pp] | **real**: qwen25_7b better |
| accuracy | 38% | 56% | +19pp | [-4pp, +40pp] | no detectable difference |
| review_recall | 100% | 67% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.69 | +0.184 | [+0.017, +0.364] | **real**: qwen3_8b__hybrid better |

McNemar exact (calls): flag correct only-qwen25_7b 9 vs only-qwen3_8b__hybrid 16, p=0.2295; 3-class only-qwen25_7b 7 vs only-qwen3_8b__hybrid 16, p=0.0931.

Flips (cv, 30 calls):

| call | expected | qwen25_7b | qwen3_8b__hybrid | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.50 | fixed | 01:37-01:39 trade: Können Sie den Kaufleit für mich machen? - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde äußert seinen konkreten Kaufwunsch für eine Aktie, indem er fragt: 'K... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.99 | same | 02:27-03:27 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/1.00 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - facts: Fakt: Wert gehört zum lau... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.09 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.28 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Zweitm... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:29 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für 6000 Franken aktiv von den Seerland Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. D... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.50 | same | 03:28-03:41 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, können Sie den einmaligen Auftrag für mich entgegnen... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.50 | same | 03:31-03:43 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht will ich nicht für 5000 Franken Aktien von der Albisoptik kaufen, können Sie den einmaligen Auftrag für mich entgegennehm... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.37/0.12 | fixed | 00:58-01:08 access: Der Pfeili, ich habe erwartet, dass ich auf dem Telefon etwas schlugge. Bestätigen, aber da geht ein Pfeil zum Browser. Vielleicht habe ich nur ein bisschen zu schnell angeschaut. ... | geval: Die Kunde erwähnt, dass sie den Pfeil gesehen hat, der zum Browser zeigt, was darauf hindeutet, dass sie möglicherweise einen Zugangsinformationen-Pfad durchschritten hat. Allerdings wurde kein... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.12 | broken | 00:30-00:46 documentation: Ich habe den Zugang noch gar nicht gestartet, ich schaue das abgelaufenen Muster in der Anleitung an, das echte Anmeldenfenster ist zu, es gibt auch keinen Countdown, die Za... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.31/0.12 | broken | 00:31-00:47 access: Ich habe den Zugang noch gar nicht gestartet, ich schaue ein abgelaufener Muster in der Anleitung an, das echte Anmeldefenster ist zu, es gibt auch keinen Counton, die Zahl kann ni... | geval: Die Kundin erwähnt, dass sie ein abgelaufenes Muster in der Anleitung ansieht und keine Zahl gebraucht werden kann. Sie beschreibt jedoch den Titel des Fensters, der 836174 lautet, was als Zuga... |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |

## `qwen3_8b__hybrid_kw` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.70 | +0.027 | [-0.147, +0.217] | no detectable difference |
| alarm AUC | 0.79 | 0.69 | -0.104 | [-0.259, +0.026] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.73 | +0.074 | [-0.067, +0.212] | no detectable difference |
| alarm_f1 | 0.49 | 0.40 | -0.088 | [-0.400, +0.183] | no detectable difference |
| false_alarm_rate | 86% | 32% | -55pp | [-93pp, -12pp] | **real**: qwen3_8b__hybrid_kw better |
| miss_rate | 15% | 27% | +12pp | [-12pp, +38pp] | no detectable difference |
| accuracy | 38% | 50% | +12pp | [-10pp, +35pp] | no detectable difference |
| review_recall | 83% | 67% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.71 | +0.215 | [+0.053, +0.393] | **real**: qwen3_8b__hybrid_kw better |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen3_8b__hybrid_kw 16, p=0.0931; 3-class only-qwen25_7b 9 vs only-qwen3_8b__hybrid_kw 15, p=0.3075.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.73 | +0.088 | [-0.051, +0.235] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 32% | -23pp | [-50pp, +14pp] | no detectable difference |
| miss_rate | 31% | 27% | -4pp | [-31pp, +23pp] | no detectable difference |
| accuracy | 31% | 40% | +8pp | [-12pp, +26pp] | no detectable difference |
| review_recall | 50% | 67% | +17pp | [-50pp, +100pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.71 | +0.133 | [-0.013, +0.283] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen3_8b__hybrid_kw 12, p=0.2379; 3-class only-qwen25_7b 5 vs only-qwen3_8b__hybrid_kw 9, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__hybrid_kw - qwen25_7b

| metric | qwen25_7b | qwen3_8b__hybrid_kw | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.73 | +0.036 | [-0.126, +0.190] | no detectable difference |
| alarm_f1 | 0.61 | 0.40 | -0.211 | [-0.475, -0.006] | **real**: qwen25_7b better |
| false_alarm_rate | 95% | 32% | -64pp | [-100pp, -29pp] | **real**: qwen3_8b__hybrid_kw better |
| miss_rate | 4% | 27% | +23pp | [+0pp, +50pp] | no detectable difference |
| accuracy | 38% | 50% | +12pp | [-11pp, +35pp] | no detectable difference |
| review_recall | 100% | 67% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.71 | +0.203 | [+0.041, +0.385] | **real**: qwen3_8b__hybrid_kw better |

McNemar exact (calls): flag correct only-qwen25_7b 8 vs only-qwen3_8b__hybrid_kw 16, p=0.1516; 3-class only-qwen25_7b 9 vs only-qwen3_8b__hybrid_kw 15, p=0.3075.

Flips (cv, 31 calls):

| call | expected | qwen25_7b | qwen3_8b__hybrid_kw | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.41 | fixed | 01:33-01:39 trade: Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mich machen? - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - De... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.21 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.21 ('Insiderhandel') liegt unter 0.45... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.94 | same | 02:29-03:29 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K2 | alarm | alarm | review | 0.70/0.27 | same | 01:21-01:23 access: Warte, ich sage Ihnen die Planung gerade, 7, 3, 1, 9, 4, 2, es steht immer noch geültig. Können Sie mir sagen, ob das die richtige Reihe in Folge ist? - patterns: Kundschaft liest ... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.14 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.14 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.10 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.10 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.80 | same | 00:29-00:41 documentation: Gut, dass Sie dies melden. Unsere Kreditstelle muss die tatsächlichen Herkunft und die Rückzahlungsverpflichtung kennen. Wir müssen den Wurf also kollidieren, bevor er weite... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.87/0.72 | same | 00:30-00:33 documentation: Gut, dass Sie dies melden. Unsere Kreditstellung? - facts: Fakt: Verborgene Tatsache ist relevant = ja (0.79) - Der Kreditberater erwähnt, dass relevante Informationen für d... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | review | 0.69/0.57 | same | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Zweitm... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.27 | same | 01:20-01:27 splitting: Sie arbeiten nicht bei dieser Firma, ich weiss nichts zu ersetzen und habe den gleichen Inhalt wie alle anderen Anweger. - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.27 | same | 01:56-02:05 splitting: Dann sollte sie das Geld für den Umzug nicht auch noch für das Depot einplanen, für welche Ausgaben haben sie schon etwas auf die Seite gelegt, - facts: Fakt: Aufteilung in Teil... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.27 | same | 00:14-00:30 splitting: Ja, aber ich möchte zwei Sachen nicht durcheinanderbringen, ich habe ein Depot und ein separates Konto für den Umzug, ich möchte mich informieren, ohne jetzt in Kauf zu verlange... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C09-K3 | alarm | no_alert | review | 0.37/0.53 | fixed | 00:58-01:08 access: Der Pfeili, ich habe erwartet, dass ich auf dem Telefon etwas schlugge. Bestätigen, aber da geht ein Pfeil zum Browser. Vielleicht habe ich nur ein bisschen zu schnell angeschaut. ... | geval: Die Kunde erwähnt, dass sie den Pfeil gesehen hat, der zum Browser zeigt, was darauf hindeutet, dass sie möglicherweise einen Zugangsinformationen-Pfad durchschritten hat. Allerdings wurde kein... |
| Stufe2_C10-K3 | no_alert | no_alert | review | 0.40/0.53 | broken | 00:30-00:46 documentation: Ich habe den Zugang noch gar nicht gestartet, ich schaue das abgelaufenen Muster in der Anleitung an, das echte Anmeldenfenster ist zu, es gibt auch keinen Countdown, die Za... | geval: Der Kunde erwähnt, dass er das abgelaufene Muster in der Anleitung ansieht, was impliziert, dass er möglicherweise Informationen vor der Kreditstelle verbirgt, die für die Kreditprüfung relevan... |
| Stufe2_C10-K4 | no_alert | no_alert | review | 0.31/0.53 | broken | 00:31-00:47 access: Ich habe den Zugang noch gar nicht gestartet, ich schaue ein abgelaufener Muster in der Anleitung an, das echte Anmeldefenster ist zu, es gibt auch keinen Counton, die Zahl kann ni... | geval: Die Kundin erwähnt, dass sie ein abgelaufenes Muster in der Anleitung ansieht und keine Zahl gebraucht werden kann. Sie beschreibt jedoch den Titel des Fensters, der 836174 lautet, was als Zuga... |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |

## `qwen25_7b__facts_blind_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.73 | +0.055 | [-0.057, +0.155] | no detectable difference |
| alarm AUC | 0.79 | 0.79 | -0.003 | [-0.141, +0.092] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.59 | -0.071 | [-0.322, +0.167] | no detectable difference |
| alarm_f1 | 0.49 | 0.57 | +0.084 | [-0.210, +0.384] | no detectable difference |
| false_alarm_rate | 86% | 14% | -73pp | [-89pp, -54pp] | **real**: qwen25_7b__facts_blind_only better |
| miss_rate | 15% | 54% | +38pp | [+8pp, +65pp] | **real**: qwen25_7b better |
| accuracy | 38% | 60% | +23pp | [-5pp, +48pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.66 | +0.171 | [+0.021, +0.347] | **real**: qwen25_7b__facts_blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 12 vs only-qwen25_7b__facts_blind_only 18, p=0.3616; 3-class only-qwen25_7b 11 vs only-qwen25_7b__facts_blind_only 22, p=0.0801.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.59 | -0.058 | [-0.284, +0.162] | no detectable difference |
| alarm_f1 | 0.17 | 0.43 | +0.255 | [-0.221, +0.625] | no detectable difference |
| false_alarm_rate | 55% | 14% | -41pp | [-62pp, -18pp] | **real**: qwen25_7b__facts_blind_only better |
| miss_rate | 31% | 54% | +23pp | [-5pp, +50pp] | no detectable difference |
| accuracy | 31% | 56% | +25pp | [+2pp, +44pp] | **real**: qwen25_7b__facts_blind_only better |
| review_recall | 50% | 33% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.66 | +0.089 | [-0.061, +0.243] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 9 vs only-qwen25_7b__facts_blind_only 12, p=0.6636; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_blind_only 16, p=0.0118.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.59 | -0.109 | [-0.342, +0.103] | no detectable difference |
| alarm_f1 | 0.61 | 0.33 | -0.278 | [-0.549, -0.038] | **real**: qwen25_7b better |
| false_alarm_rate | 95% | 14% | -82pp | [-95pp, -69pp] | **real**: qwen25_7b__facts_blind_only better |
| miss_rate | 4% | 54% | +50pp | [+29pp, +71pp] | **real**: qwen25_7b better |
| accuracy | 38% | 52% | +15pp | [-14pp, +39pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.66 | +0.159 | [+0.033, +0.296] | **real**: qwen25_7b__facts_blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 13 vs only-qwen25_7b__facts_blind_only 18, p=0.4731; 3-class only-qwen25_7b 12 vs only-qwen25_7b__facts_blind_only 19, p=0.281.

Flips (cv, 38 calls):

| call | expected | qwen25_7b | qwen25_7b__facts_blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.50 | fixed | 01:28-01:31 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - facts_blind: Fakt: Eigener Handelswunsch = ja (0.96) - Der Kunde drückt seinen Wunsch, die Aktie zu kaufen, aus. (... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben'... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.83 | same | 03:14-03:32 trade: Sie hat ihnen gesagt, ob sie diese Information brauchen oder weitergeben darf. Weiter, sie hat gesagt, das bleibt unter uns. Ich habe das auch nicht weiterverzählt, aber ich möchte ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.82 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts_blind: Fakt: Zugangsgeheimnis ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.87/0.00 | broken | 02:37-03:00 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.95/0.00 | broken | 01:33-01:50 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe-Stell die ganze Rechnung überhaupt sieht. Können Sie mir ja... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15... | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | alarm | 0.69/0.50 | same | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.99) - Der Kunde gibt den Zugangsinformation 4242-3242-3232-3232-3232 aus. (Regel: acc... | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.05 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | no_alert | 0.70/0.02 | broken | 08:00-08:12 documentation: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er i... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.07 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.50 | same | 03:28-03:50 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, können Sie den einmaligen Auftrag für mich entgegnen... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.50 | same | 03:31-03:53 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht will ich nicht für 5000 Franken Aktien von der Albisoptik kaufen, können Sie den einmaligen Auftrag für mich entgegennehm... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.50 | same | 07:31-08:17 documentation: Mach gut, die auch ange und die grüne Mafierungen sind jetzt klar. Für die violetten Zeilen habe ich noch den Wunsch, den ich am Anfang an gesprochen habe. Die Farben meine ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.01 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis dahin wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Die Kunde fragt na... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 00:23-01:07 disclosure: Dann müssen wir vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hinterlegt ihr der Schwester durch den Kontakt? Sie sagte, es... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen3_8b__facts_blind_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen3_8b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.67 | -0.009 | [-0.129, +0.106] | no detectable difference |
| alarm AUC | 0.79 | 0.69 | -0.098 | [-0.254, +0.036] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.62 | -0.035 | [-0.294, +0.201] | no detectable difference |
| alarm_f1 | 0.49 | 0.62 | +0.128 | [-0.147, +0.354] | no detectable difference |
| false_alarm_rate | 86% | 23% | -64pp | [-86pp, -38pp] | **real**: qwen3_8b__facts_blind_only better |
| miss_rate | 15% | 46% | +31pp | [+0pp, +61pp] | no detectable difference |
| accuracy | 38% | 60% | +23pp | [-4pp, +48pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.66 | +0.164 | [-0.004, +0.349] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 10 vs only-qwen3_8b__facts_blind_only 16, p=0.3269; 3-class only-qwen25_7b 8 vs only-qwen3_8b__facts_blind_only 19, p=0.0522.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.62 | -0.021 | [-0.260, +0.203] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 23% | -32pp | [-66pp, +5pp] | no detectable difference |
| miss_rate | 31% | 46% | +15pp | [-15pp, +45pp] | no detectable difference |
| accuracy | 31% | 40% | +8pp | [-15pp, +32pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.66 | +0.082 | [-0.118, +0.288] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 8 vs only-qwen3_8b__facts_blind_only 11, p=0.6476; 3-class only-qwen25_7b 5 vs only-qwen3_8b__facts_blind_only 9, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen3_8b__facts_blind_only - qwen25_7b

| metric | qwen25_7b | qwen3_8b__facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.62 | -0.072 | [-0.320, +0.151] | no detectable difference |
| alarm_f1 | 0.61 | 0.26 | -0.350 | [-0.625, -0.093] | **real**: qwen25_7b better |
| false_alarm_rate | 95% | 23% | -73pp | [-92pp, -50pp] | **real**: qwen3_8b__facts_blind_only better |
| miss_rate | 4% | 46% | +42pp | [+17pp, +68pp] | **real**: qwen25_7b better |
| accuracy | 38% | 46% | +8pp | [-22pp, +36pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.66 | +0.152 | [+0.008, +0.307] | **real**: qwen3_8b__facts_blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 11 vs only-qwen3_8b__facts_blind_only 16, p=0.4421; 3-class only-qwen25_7b 12 vs only-qwen3_8b__facts_blind_only 16, p=0.5716.

Flips (cv, 31 calls):

| call | expected | qwen25_7b | qwen3_8b__facts_blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.50 | fixed | 01:28-01:39 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mich machen... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.50 | same | 04:54-05:11 trade: Ja, gerade wegen dem Preis, den meine Kollegin mir gezeigt hat, möchte ich diese Aktien heute kaufen von den Bekanntgaben. Nehmen Sie 12000 Franken aus dieser Fondsposition und kauf... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | no_alert | 0.69/0.00 | broken | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.00 ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:29 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für 6000 Franken aktiv von den Seerland Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. D... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.50 | same | 03:28-03:41 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, können Sie den einmaligen Auftrag für mich entgegnen... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.50 | same | 03:31-03:43 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht will ich nicht für 5000 Franken Aktien von der Albisoptik kaufen, können Sie den einmaligen Auftrag für mich entgegennehm... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 00:00-00:21 disclosure: Guten Tag Frau Ott, hier ist Daniela Vogt, Sie haben wegen des Haushaltskontos ihrer Schwester um einen Neukauf gewünscht. Ja, sie ist für zwei Monate im Ausland. Ich habe ihr ... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 00:00-00:08 disclosure: Guten Tag Frau Ut, hier ist Daniela Vogt, Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00)... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.87 | +0.190 | [+0.075, +0.307] | **real**: qwen25_14b_facts better |
| alarm AUC | 0.79 | 0.91 | +0.115 | [+0.026, +0.193] | **real**: qwen25_14b_facts better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.82 | +0.160 | [+0.011, +0.331] | **real**: qwen25_14b_facts better |
| alarm_f1 | 0.49 | 0.79 | +0.303 | [+0.109, +0.505] | **real**: qwen25_14b_facts better |
| false_alarm_rate | 86% | 14% | -73pp | [-94pp, -44pp] | **real**: qwen25_14b_facts better |
| miss_rate | 15% | 23% | +8pp | [-7pp, +21pp] | no detectable difference |
| accuracy | 38% | 75% | +38pp | [+10pp, +62pp] | **real**: qwen25_14b_facts better |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.82 | +0.325 | [+0.173, +0.452] | **real**: qwen25_14b_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_14b_facts 18, p=0.0043; 3-class only-qwen25_7b 5 vs only-qwen25_14b_facts 23, p=0.0009.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.82 | +0.173 | [+0.018, +0.344] | **real**: qwen25_14b_facts better |
| alarm_f1 | 0.17 | 0.72 | +0.544 | [+0.214, +0.824] | **real**: qwen25_14b_facts better |
| false_alarm_rate | 55% | 14% | -41pp | [-70pp, -11pp] | **real**: qwen25_14b_facts better |
| miss_rate | 31% | 23% | -8pp | [-25pp, +11pp] | no detectable difference |
| accuracy | 31% | 71% | +40pp | [+16pp, +62pp] | **real**: qwen25_14b_facts better |
| review_recall | 50% | 17% | -33pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.82 | +0.243 | [+0.062, +0.412] | **real**: qwen25_14b_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_facts 14, p=0.0127; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts 21, p=0.0001.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.82 | +0.122 | [-0.036, +0.302] | no detectable difference |
| alarm_f1 | 0.61 | 0.79 | +0.177 | [-0.016, +0.425] | no detectable difference |
| false_alarm_rate | 95% | 14% | -82pp | [-100pp, -59pp] | **real**: qwen25_14b_facts better |
| miss_rate | 4% | 23% | +19pp | [+7pp, +33pp] | **real**: qwen25_7b better |
| accuracy | 38% | 73% | +35pp | [+12pp, +58pp] | **real**: qwen25_14b_facts better |
| review_recall | 100% | 50% | -50pp | [-50pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.82 | +0.313 | [+0.185, +0.421] | **real**: qwen25_14b_facts better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_14b_facts 18, p=0.0106; 3-class only-qwen25_7b 5 vs only-qwen25_14b_facts 22, p=0.0015.

Flips (cv, 32 calls):

| call | expected | qwen25_7b | qwen25_14b_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.96 | fixed | 01:28-01:31 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kund sagte, er wolle Aktien kaufen. (Regel: trade.a... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | no_alert | 0.69/0.11 | broken | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.11 ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:15 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für 6000 Franken aktiv von den Seerland Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. D... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.97 | same | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.96 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.95 | same | 07:57-08:07 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts: Fakt: V... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.50 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:33-01:48 access: Bitte sagen Sie nur den Lesbauer-Tekt, die Zahl bleibt bei Ihnen. Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 00:10-00:22 disclosure: Haus, ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zugegeben, ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. - ... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | alarm | 0.43/0.50 | same | 01:49-01:55 splitting: Können Sie die 4000 für heute und die 5000 für morgen trotzdem schon vorbeweiten? - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (0.61) - Frau Gislo fragt, ob die 4000 C... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts__blind_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.77 | +0.095 | [-0.041, +0.223] | no detectable difference |
| alarm AUC | 0.79 | 0.79 | +0.001 | [-0.156, +0.110] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.74 | +0.084 | [-0.068, +0.258] | no detectable difference |
| alarm_f1 | 0.49 | 0.60 | +0.112 | [-0.214, +0.403] | no detectable difference |
| false_alarm_rate | 86% | 36% | -50pp | [-75pp, -25pp] | **real**: qwen25_14b_facts__blind_only better |
| miss_rate | 15% | 23% | +8pp | [-12pp, +30pp] | no detectable difference |
| accuracy | 38% | 54% | +17pp | [-13pp, +45pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.70 | +0.211 | [+0.050, +0.386] | **real**: qwen25_14b_facts__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_14b_facts__blind_only 13, p=0.049; 3-class only-qwen25_7b 10 vs only-qwen25_14b_facts__blind_only 18, p=0.1849.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.72 | +0.074 | [-0.044, +0.205] | no detectable difference |
| alarm_f1 | 0.17 | 0.46 | +0.288 | [-0.230, +0.710] | no detectable difference |
| false_alarm_rate | 55% | 36% | -18pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 31% | 27% | -4pp | [-21pp, +12pp] | no detectable difference |
| accuracy | 31% | 50% | +19pp | [+2pp, +35pp] | **real**: qwen25_14b_facts__blind_only better |
| review_recall | 50% | 67% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.68 | +0.110 | [-0.008, +0.237] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_facts__blind_only 8, p=0.2266; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts__blind_only 11, p=0.0225.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.74 | +0.046 | [-0.097, +0.202] | no detectable difference |
| alarm_f1 | 0.61 | 0.67 | +0.056 | [-0.265, +0.357] | no detectable difference |
| false_alarm_rate | 95% | 36% | -59pp | [-86pp, -33pp] | **real**: qwen25_14b_facts__blind_only better |
| miss_rate | 4% | 23% | +19pp | [+4pp, +38pp] | **real**: qwen25_7b better |
| accuracy | 38% | 58% | +21pp | [-5pp, +46pp] | no detectable difference |
| review_recall | 100% | 67% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.70 | +0.199 | [+0.049, +0.359] | **real**: qwen25_14b_facts__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_14b_facts__blind_only 13, p=0.0963; 3-class only-qwen25_7b 7 vs only-qwen25_14b_facts__blind_only 17, p=0.0639.

Flips (cv, 37 calls):

| call | expected | qwen25_7b | qwen25_14b_facts__blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.50 | fixed | 01:28-01:39 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mich machen... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.99 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.98 | same | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - facts_blind: Fakt: Wert gehört z... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.50 | same | 01:32-01:48 documentation: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe stellt die ganze Rechnung überhaupt sieht. Können Sie m... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.95/0.00 | broken | 01:33-01:50 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe-Stell die ganze Rechnung überhaupt sieht. Können Sie mir ja... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | alarm | 0.70/0.50 | same | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.73) - Der Kundendienstmitarbeiter liest die vollständig... | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | alarm | 0.69/0.50 | same | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.97) - Der Kundensprecher liest die vollständige Nummer laut vor. (Regel: access.revie... | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.50 | same | 01:14-01:27 trade: Der Grosse Auftrag wurde am letzten Freitag veröffentlicht und jeder kann ihn dort lesen. Sie arbeiten nicht bei dieser Firma, ich weiss nichts zu ersetzen und habe den gleichen Inh... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.50 | same | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.50 | same | 08:00-08:12 trade: Genau wegen diesem Bericht möchte ich nicht von 6000 Franken Aktien von der CRM Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er ist. - fa... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.99 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.50 | same | 00:23-00:44 disclosure: Wir müssen vor einer konkreten Auskunft festhalten, welche Rollen sie in diesem Vorgang haben. Es geht um das persönliche Konto ihrer Mutter, richtig? Richtig. Wir haben einen ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.50 | same | 00:54-01:05 disclosure: In diesem Vorgang haben Sie die gültige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten Umfang gedeckt. - facts_blind: Fakt: Anfra... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.50 | same | 03:13-03:16 disclosure: Welche Zahl fehlt Ihnen noch für die Liste? - facts_blind: Fakt: Anfrage zu Drittperson = ja (0.91) - Der Berater fragt die Kundin nach dem aktuellen Kontostand ihrer Mutter. (... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 07:54-08:04 documentation: Dann lehnt ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - fa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.96 | same | 07:57-08:07 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts_blind: F... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.50 | same | 07:58-08:07 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:39-01:48 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | alarm | 0.46/0.50 | same | 01:40-01:45 access: Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.54) - Der Kund hat die Zahlenreihe 'zwei, neun, se... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis dahin wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Der Kunde fragt na... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 01:40-01:46 disclosure: Ich weiss nicht, ob meine Schwester den Septemberbetrag schon zum Zahlen erfasst hat. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Frau Ut fragt nach dem Kontostan... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__facts_kwlight` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__facts_kwlight - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.80 | +0.126 | [-0.004, +0.267] | no detectable difference |
| alarm AUC | 0.79 | 0.87 | +0.079 | [+0.000, +0.157] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_kwlight - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.119 | [-0.041, +0.303] | no detectable difference |
| alarm_f1 | 0.49 | 0.72 | +0.230 | [+0.044, +0.414] | **real**: qwen25_7b__facts_kwlight better |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -38pp] | **real**: qwen25_7b__facts_kwlight better |
| miss_rate | 15% | 27% | +12pp | [-6pp, +31pp] | no detectable difference |
| accuracy | 38% | 71% | +33pp | [+9pp, +56pp] | **real**: qwen25_7b__facts_kwlight better |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.283 | [+0.128, +0.433] | **real**: qwen25_7b__facts_kwlight better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__facts_kwlight 17, p=0.0169; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_kwlight 20, p=0.0015.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_kwlight - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.133 | [+0.013, +0.284] | **real**: qwen25_7b__facts_kwlight better |
| alarm_f1 | 0.17 | 0.55 | +0.372 | [+0.098, +0.621] | **real**: qwen25_7b__facts_kwlight better |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -7pp] | **real**: qwen25_7b__facts_kwlight better |
| miss_rate | 31% | 27% | -4pp | [-20pp, +13pp] | no detectable difference |
| accuracy | 31% | 62% | +31pp | [+12pp, +50pp] | **real**: qwen25_7b__facts_kwlight better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.201 | [+0.052, +0.354] | **real**: qwen25_7b__facts_kwlight better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__facts_kwlight 12, p=0.0352; 3-class only-qwen25_7b 1 vs only-qwen25_7b__facts_kwlight 16, p=0.0003.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_kwlight - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.78 | +0.081 | [-0.080, +0.263] | no detectable difference |
| alarm_f1 | 0.61 | 0.73 | +0.116 | [-0.029, +0.262] | no detectable difference |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b__facts_kwlight better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 69% | +31pp | [+7pp, +54pp] | **real**: qwen25_7b__facts_kwlight better |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.77 | +0.271 | [+0.133, +0.399] | **real**: qwen25_7b__facts_kwlight better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__facts_kwlight 17, p=0.0347; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_kwlight 19, p=0.0026.

Flips (cv, 28 calls):

| call | expected | qwen25_7b | qwen25_7b__facts_kwlight | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.93 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.04 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.10... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.99 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.12 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.1... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.03 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.03 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.02 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.02 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.02 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.04 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.97 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 08:21-08:46 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechsel. Dann be... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.97 | same | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.85 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__facts_kwlight_noesc` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__facts_kwlight_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.80 | +0.126 | [-0.004, +0.267] | no detectable difference |
| alarm AUC | 0.79 | 0.87 | +0.079 | [+0.000, +0.157] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_kwlight_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.119 | [-0.041, +0.303] | no detectable difference |
| alarm_f1 | 0.49 | 0.75 | +0.262 | [+0.114, +0.428] | **real**: qwen25_7b__facts_kwlight_noesc better |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -38pp] | **real**: qwen25_7b__facts_kwlight_noesc better |
| miss_rate | 15% | 27% | +12pp | [-6pp, +31pp] | no detectable difference |
| accuracy | 38% | 73% | +35pp | [+12pp, +57pp] | **real**: qwen25_7b__facts_kwlight_noesc better |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.283 | [+0.128, +0.433] | **real**: qwen25_7b__facts_kwlight_noesc better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__facts_kwlight_noesc 17, p=0.0169; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_kwlight_noesc 21, p=0.0009.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_kwlight_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.133 | [+0.013, +0.284] | **real**: qwen25_7b__facts_kwlight_noesc better |
| alarm_f1 | 0.17 | 0.55 | +0.372 | [+0.098, +0.621] | **real**: qwen25_7b__facts_kwlight_noesc better |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -7pp] | **real**: qwen25_7b__facts_kwlight_noesc better |
| miss_rate | 31% | 27% | -4pp | [-20pp, +13pp] | no detectable difference |
| accuracy | 31% | 62% | +31pp | [+12pp, +50pp] | **real**: qwen25_7b__facts_kwlight_noesc better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.201 | [+0.052, +0.354] | **real**: qwen25_7b__facts_kwlight_noesc better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__facts_kwlight_noesc 12, p=0.0352; 3-class only-qwen25_7b 1 vs only-qwen25_7b__facts_kwlight_noesc 16, p=0.0003.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_kwlight_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_kwlight_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.78 | +0.081 | [-0.080, +0.263] | no detectable difference |
| alarm_f1 | 0.61 | 0.76 | +0.154 | [+0.054, +0.279] | **real**: qwen25_7b__facts_kwlight_noesc better |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b__facts_kwlight_noesc better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 71% | +33pp | [+10pp, +55pp] | **real**: qwen25_7b__facts_kwlight_noesc better |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.77 | +0.271 | [+0.133, +0.399] | **real**: qwen25_7b__facts_kwlight_noesc better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__facts_kwlight_noesc 17, p=0.0347; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_kwlight_noesc 20, p=0.0015.

Flips (cv, 29 calls):

| call | expected | qwen25_7b | qwen25_7b__facts_kwlight_noesc | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.93 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.04 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unter 0.10... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.99 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.85 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code/Wert am Telefon vo... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.12 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.1... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.03 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.03 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.02 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.02 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.02 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.04 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.97 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 08:21-08:46 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechsel. Dann be... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.97 | same | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.85 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__facts_noesc` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__facts_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.84 | +0.158 | [+0.050, +0.284] | **real**: qwen25_7b__facts_noesc better |
| alarm AUC | 0.79 | 0.89 | +0.094 | [+0.010, +0.172] | **real**: qwen25_7b__facts_noesc better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.119 | [-0.041, +0.303] | no detectable difference |
| alarm_f1 | 0.49 | 0.75 | +0.262 | [+0.114, +0.428] | **real**: qwen25_7b__facts_noesc better |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -38pp] | **real**: qwen25_7b__facts_noesc better |
| miss_rate | 15% | 27% | +12pp | [-6pp, +31pp] | no detectable difference |
| accuracy | 38% | 73% | +35pp | [+12pp, +57pp] | **real**: qwen25_7b__facts_noesc better |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.283 | [+0.128, +0.433] | **real**: qwen25_7b__facts_noesc better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__facts_noesc 17, p=0.0169; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_noesc 21, p=0.0009.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.133 | [+0.013, +0.284] | **real**: qwen25_7b__facts_noesc better |
| alarm_f1 | 0.17 | 0.67 | +0.493 | [+0.215, +0.750] | **real**: qwen25_7b__facts_noesc better |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -7pp] | **real**: qwen25_7b__facts_noesc better |
| miss_rate | 31% | 27% | -4pp | [-20pp, +13pp] | no detectable difference |
| accuracy | 31% | 69% | +38pp | [+20pp, +57pp] | **real**: qwen25_7b__facts_noesc better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.201 | [+0.052, +0.354] | **real**: qwen25_7b__facts_noesc better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b__facts_noesc 12, p=0.0352; 3-class only-qwen25_7b 1 vs only-qwen25_7b__facts_noesc 19, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__facts_noesc - qwen25_7b

| metric | qwen25_7b | qwen25_7b__facts_noesc | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.78 | +0.081 | [-0.080, +0.263] | no detectable difference |
| alarm_f1 | 0.61 | 0.76 | +0.154 | [+0.054, +0.279] | **real**: qwen25_7b__facts_noesc better |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b__facts_noesc better |
| miss_rate | 4% | 27% | +23pp | [+7pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 71% | +33pp | [+10pp, +55pp] | **real**: qwen25_7b__facts_noesc better |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.77 | +0.271 | [+0.133, +0.399] | **real**: qwen25_7b__facts_noesc better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b__facts_noesc 17, p=0.0347; 3-class only-qwen25_7b 4 vs only-qwen25_7b__facts_noesc 20, p=0.0015.

Flips (cv, 29 calls):

| call | expected | qwen25_7b | qwen25_7b__facts_noesc | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.97 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.92 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code/Wert am Telefon vo... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.08 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.04 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.97 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 08:21-08:46 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechsel. Dann be... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.97 | same | 07:57-08:17 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.85 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:38-03:58 disclosure: Wenn ich nicht, können sie mir ja bis dahin wenigstens sagen, ob auf ihrem Konto genug für die Wohnungskächtung liegt, nein, das kann ich ihnen erst sagen, wenn die Berechtigun... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts_l3` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.85 | +0.173 | [+0.080, +0.271] | **real**: qwen25_14b_facts_l3 better |
| alarm AUC | 0.79 | 0.90 | +0.106 | [+0.024, +0.183] | **real**: qwen25_14b_facts_l3 better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.80 | +0.143 | [-0.027, +0.334] | no detectable difference |
| alarm_f1 | 0.49 | 0.72 | +0.234 | [+0.014, +0.448] | **real**: qwen25_14b_facts_l3 better |
| false_alarm_rate | 86% | 18% | -68pp | [-90pp, -42pp] | **real**: qwen25_14b_facts_l3 better |
| miss_rate | 15% | 23% | +8pp | [-13pp, +29pp] | no detectable difference |
| accuracy | 38% | 65% | +27pp | [+2pp, +52pp] | **real**: qwen25_14b_facts_l3 better |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.79 | +0.302 | [+0.150, +0.455] | **real**: qwen25_14b_facts_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_14b_facts_l3 17, p=0.0072; 3-class only-qwen25_7b 7 vs only-qwen25_14b_facts_l3 20, p=0.0192.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.133 | [-0.014, +0.301] | no detectable difference |
| alarm_f1 | 0.17 | 0.62 | +0.447 | [+0.053, +0.800] | **real**: qwen25_14b_facts_l3 better |
| false_alarm_rate | 55% | 18% | -36pp | [-62pp, -10pp] | **real**: qwen25_14b_facts_l3 better |
| miss_rate | 31% | 27% | -4pp | [-21pp, +13pp] | no detectable difference |
| accuracy | 31% | 62% | +31pp | [+13pp, +52pp] | **real**: qwen25_14b_facts_l3 better |
| review_recall | 50% | 50% | +0pp | [-50pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.201 | [+0.038, +0.369] | **real**: qwen25_14b_facts_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_facts_l3 12, p=0.0352; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts_l3 17, p=0.0007.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.80 | +0.106 | [-0.061, +0.292] | no detectable difference |
| alarm_f1 | 0.61 | 0.79 | +0.177 | [+0.012, +0.389] | **real**: qwen25_14b_facts_l3 better |
| false_alarm_rate | 95% | 18% | -77pp | [-95pp, -55pp] | **real**: qwen25_14b_facts_l3 better |
| miss_rate | 4% | 23% | +19pp | [+4pp, +38pp] | **real**: qwen25_7b better |
| accuracy | 38% | 71% | +33pp | [+9pp, +57pp] | **real**: qwen25_14b_facts_l3 better |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.79 | +0.290 | [+0.166, +0.408] | **real**: qwen25_14b_facts_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_14b_facts_l3 17, p=0.0169; 3-class only-qwen25_7b 5 vs only-qwen25_14b_facts_l3 21, p=0.0025.

Flips (cv, 31 calls):

| call | expected | qwen25_7b | qwen25_14b_facts_l3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:37-00:43 trade: Etwa 8000 Franken. Meine Schwester arbeitet dort in der Finanzabteilung. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Frau Aibi erklärt, dass ih... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Firma gesprochen. Sie hat mir über einen Namen erzählt. Im grösseren Konzern will die Firma auch kaufen. Sie arbeitet in der Finanzabteilung und hat mir ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.98 | same | 01:08-01:24 access: Bitte gehen Sie den Wert selber im vorgesehenen Feld ein. Ich brauche nur die Rückmeldung, ob es klappt. Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.50 | same | 08:01-08:13 trade: Genau wegen diesem Bericht möchte ich nicht für sechstausend Franken Aktien von den Seelen-Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. Der Sparplan soll bleiben, wie ... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.50 | same | 08:00-08:09 trade: Genau wegen diesem Bericht möchte ich etwas von sechstausend Franken Aktien von der Seerlern Systeme kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. - facts: Fakt: Eigener Handels... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:35-00:43 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information ... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.89 | same | 00:40-00:48 trade: Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Der geht erst einmal an die Mädchen, bis dann darf das Team ihn nicht weitergeben. - facts: Fakt: Begründet mit nicht... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.50 | same | 00:34-00:40 disclosure: Richtig. Wir haben den Beleg des Heimes und die Liste der monatlichen Ausgaben. - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Kunde fragt den Berater, ob ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.50 | same | 00:00-00:08 disclosure: Guten Morgen, Frau Päi. Das ist Marion Biot. Sie haben wegen der laufenden Wohnkosten von ihrer Mutter um ein Rückwärtsbett. - facts: Fakt: Auskunft über Drittperson verlangt =... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | alarm | 0.46/0.50 | same | 01:42-01:49 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.95) - Der Kunde liest die Zahlenfolge '2, 9, 6, 4... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 00:00-00:08 disclosure: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. - facts: Fakt: Auskunft über Drittperson verlangt = ja... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:39-03:45 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kundin f... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts_oracle` vs `qwen25_7b` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.90 | +0.226 | [+0.088, +0.366] | **real**: qwen25_14b_facts_oracle better |
| alarm AUC | 0.79 | 0.91 | +0.115 | [-0.045, +0.241] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.87 | +0.213 | [+0.023, +0.408] | **real**: qwen25_14b_facts_oracle better |
| alarm_f1 | 0.49 | 0.89 | +0.401 | [+0.217, +0.600] | **real**: qwen25_14b_facts_oracle better |
| false_alarm_rate | 86% | 0% | -86pp | [-100pp, -64pp] | **real**: qwen25_14b_facts_oracle better |
| miss_rate | 15% | 23% | +8pp | [-14pp, +32pp] | no detectable difference |
| accuracy | 38% | 88% | +50pp | [+27pp, +69pp] | **real**: qwen25_14b_facts_oracle better |
| review_recall | 83% | 67% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.88 | +0.393 | [+0.242, +0.533] | **real**: qwen25_14b_facts_oracle better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_14b_facts_oracle 21, p=0.0009; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts_oracle 26, p=0.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.87 | +0.227 | [+0.066, +0.405] | **real**: qwen25_14b_facts_oracle better |
| alarm_f1 | 0.17 | 0.33 | +0.159 | [-0.364, +0.600] | no detectable difference |
| false_alarm_rate | 55% | 0% | -55pp | [-83pp, -25pp] | **real**: qwen25_14b_facts_oracle better |
| miss_rate | 31% | 23% | -8pp | [-27pp, +14pp] | no detectable difference |
| accuracy | 31% | 62% | +31pp | [+9pp, +52pp] | **real**: qwen25_14b_facts_oracle better |
| review_recall | 50% | 67% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.88 | +0.311 | [+0.139, +0.489] | **real**: qwen25_14b_facts_oracle better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_14b_facts_oracle 16, p=0.0013; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts_oracle 17, p=0.0007.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.87 | +0.175 | [-0.010, +0.369] | no detectable difference |
| alarm_f1 | 0.61 | 0.89 | +0.278 | [+0.090, +0.488] | **real**: qwen25_14b_facts_oracle better |
| false_alarm_rate | 95% | 0% | -95pp | [-100pp, -85pp] | **real**: qwen25_14b_facts_oracle better |
| miss_rate | 4% | 23% | +19pp | [+0pp, +42pp] | no detectable difference |
| accuracy | 38% | 88% | +50pp | [+25pp, +70pp] | **real**: qwen25_14b_facts_oracle better |
| review_recall | 100% | 67% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.88 | +0.381 | [+0.256, +0.500] | **real**: qwen25_14b_facts_oracle better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_14b_facts_oracle 21, p=0.0025; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts_oracle 26, p=0.0.

Flips (cv, 30 calls):

| call | expected | qwen25_7b | qwen25_14b_facts_oracle | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:38-00:53 trade: Öppe achttuusig Franke. Mini Schwöschter schaffet det i de Finanzabteilig. Sie het mir gester gseit, d Quartalszahle sind viel besser als erwartet. Die sind no nöd publiziert; die M... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.60... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:02-03:02 trade: Nei, bis jetzt nöd. Ich ha d Firma aber sit e paar Mönet im Blick. E Kollegin us de Lehrziit schaffet det. Mir gönd ab und zue zäme z Mittag, aber ich ha sie nie nach em Geschäft gf... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.96 | same | 01:16-01:40 access: Wart, ich säg Ihne die TAN grad: sibe, drü, eins, nüün, vier, zwei. Es staht immer no gültig. Chönd Sie mir säge, öb das die richtige Reihenfolg isch? Bitte nümme vorzläse. Ich cha... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.60 (Schwelle 0.75 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.60 (Schwelle 0.75 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.98 | same | 01:14-01:35 trade: Claudia leitet s Projekt bi de Firma. Si het mir de unterschriebene Grossauftrag persönlich zeigt, will mir eus privat kenne. De Inhalt bliibt bis zur Präsentation am Friitig im Pro... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:37-01:01 trade: Mini Cousine isch im Projektteam vo de Albis Optik. Si het mir gester de neue Absatzbericht persönlich zeigt. De gaht erst morn an d Medie; bis denn dörf s Team ihn nöd wiitergee. E... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:38-01:01 trade: Mini Cousine isch im Projektteam vo de Albis Optik. Si het mir gester de neue Absatzbericht persönlich zeigt. De gaht erst morn an d Medie; bis denn dörf s Team ihn nöd wiitergee. E... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.50 | fixed | 03:39-04:00 disclosure: Chönd Sie mir bis dahin wenigstens säge, ob uf ihrem Konto gnueg für d Wohnigsrechnung liit? Nei, das cha ich Ihnen erst säge, wenn d Berechtigung für die Uskunft prüeft isch. ... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b_facts_l3` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.89 | +0.210 | [+0.095, +0.338] | **real**: qwen25_7b_facts_l3 better |
| alarm AUC | 0.79 | 0.92 | +0.123 | [+0.034, +0.205] | **real**: qwen25_7b_facts_l3 better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.86 | +0.206 | [+0.050, +0.390] | **real**: qwen25_7b_facts_l3 better |
| alarm_f1 | 0.49 | 0.86 | +0.369 | [+0.179, +0.581] | **real**: qwen25_7b_facts_l3 better |
| false_alarm_rate | 86% | 14% | -73pp | [-94pp, -46pp] | **real**: qwen25_7b_facts_l3 better |
| miss_rate | 15% | 15% | +0pp | [-17pp, +19pp] | no detectable difference |
| accuracy | 38% | 79% | +42pp | [+18pp, +65pp] | **real**: qwen25_7b_facts_l3 better |
| review_recall | 83% | 67% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.85 | +0.364 | [+0.208, +0.512] | **real**: qwen25_7b_facts_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_7b_facts_l3 18, p=0.0004; 3-class only-qwen25_7b 3 vs only-qwen25_7b_facts_l3 23, p=0.0001.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.86 | +0.220 | [+0.105, +0.367] | **real**: qwen25_7b_facts_l3 better |
| alarm_f1 | 0.17 | 0.67 | +0.493 | [+0.100, +0.824] | **real**: qwen25_7b_facts_l3 better |
| false_alarm_rate | 55% | 14% | -41pp | [-70pp, -12pp] | **real**: qwen25_7b_facts_l3 better |
| miss_rate | 31% | 15% | -15pp | [-29pp, -4pp] | **real**: qwen25_7b_facts_l3 better |
| accuracy | 31% | 69% | +38pp | [+17pp, +60pp] | **real**: qwen25_7b_facts_l3 better |
| review_recall | 50% | 67% | +17pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.85 | +0.281 | [+0.126, +0.438] | **real**: qwen25_7b_facts_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 0 vs only-qwen25_7b_facts_l3 13, p=0.0002; 3-class only-qwen25_7b 1 vs only-qwen25_7b_facts_l3 19, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.86 | +0.168 | [+0.011, +0.346] | **real**: qwen25_7b_facts_l3 better |
| alarm_f1 | 0.61 | 0.86 | +0.246 | [+0.071, +0.452] | **real**: qwen25_7b_facts_l3 better |
| false_alarm_rate | 95% | 14% | -82pp | [-100pp, -60pp] | **real**: qwen25_7b_facts_l3 better |
| miss_rate | 4% | 15% | +12pp | [+0pp, +29pp] | no detectable difference |
| accuracy | 38% | 79% | +42pp | [+18pp, +64pp] | **real**: qwen25_7b_facts_l3 better |
| review_recall | 100% | 67% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.85 | +0.351 | [+0.224, +0.464] | **real**: qwen25_7b_facts_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b_facts_l3 18, p=0.0015; 3-class only-qwen25_7b 3 vs only-qwen25_7b_facts_l3 23, p=0.0001.

Flips (cv, 28 calls):

| call | expected | qwen25_7b | qwen25_7b_facts_l3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:37-00:53 trade: Etwa 8000 Franken. Meine Schwester arbeitet dort in der Finanzabteilung. Sie hat mir gestern gesagt, Quartalszahlen seien viel besser als erwartet. Diese sind noch nicht publiziert.... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 03:01-03:05 trade: Sie musste auf ihrem Laptop sagen, ich habe keinen Artikel. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Die Kunde berichtet, dass sie die Infor... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.96 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/1.00 | same | 01:09-01:23 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.97 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.84 | same | 00:35-00:44 trade: Meine Cousine ist im Projektum der Alpisoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.50 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.50 | same | 03:33-03:43 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.50 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.50 | fixed | 03:39-03:57 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b_facts_oracle` vs `qwen25_7b` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.76 | +0.078 | [-0.106, +0.238] | no detectable difference |
| alarm AUC | 0.79 | 0.81 | +0.019 | [-0.147, +0.146] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.64 | -0.020 | [-0.281, +0.211] | no detectable difference |
| alarm_f1 | 0.49 | 0.63 | +0.144 | [-0.183, +0.417] | no detectable difference |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -40pp] | **real**: qwen25_7b_facts_oracle better |
| miss_rate | 15% | 46% | +31pp | [+5pp, +58pp] | **real**: qwen25_7b better |
| accuracy | 38% | 62% | +25pp | [-7pp, +52pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.68 | +0.187 | [+0.008, +0.361] | **real**: qwen25_7b_facts_oracle better |

McNemar exact (calls): flag correct only-qwen25_7b 9 vs only-qwen25_7b_facts_oracle 16, p=0.2295; 3-class only-qwen25_7b 8 vs only-qwen25_7b_facts_oracle 20, p=0.0357.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.64 | -0.006 | [-0.274, +0.211] | no detectable difference |
| alarm_f1 | 0.17 | 0.67 | +0.493 | [+0.150, +0.800] | **real**: qwen25_7b_facts_oracle better |
| false_alarm_rate | 55% | 18% | -36pp | [-71pp, +0pp] | no detectable difference |
| miss_rate | 31% | 46% | +15pp | [-12pp, +45pp] | no detectable difference |
| accuracy | 31% | 67% | +35pp | [+12pp, +57pp] | **real**: qwen25_7b_facts_oracle better |
| review_recall | 50% | 33% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.68 | +0.105 | [-0.109, +0.295] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 8 vs only-qwen25_7b_facts_oracle 12, p=0.5034; 3-class only-qwen25_7b 2 vs only-qwen25_7b_facts_oracle 19, p=0.0002.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_oracle - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_oracle | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.64 | -0.058 | [-0.324, +0.172] | no detectable difference |
| alarm_f1 | 0.61 | 0.67 | +0.056 | [-0.283, +0.341] | no detectable difference |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b_facts_oracle better |
| miss_rate | 4% | 46% | +42pp | [+17pp, +69pp] | **real**: qwen25_7b better |
| accuracy | 38% | 62% | +25pp | [-6pp, +52pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.68 | +0.175 | [+0.004, +0.334] | **real**: qwen25_7b_facts_oracle better |

McNemar exact (calls): flag correct only-qwen25_7b 11 vs only-qwen25_7b_facts_oracle 17, p=0.3449; 3-class only-qwen25_7b 8 vs only-qwen25_7b_facts_oracle 20, p=0.0357.

Flips (cv, 31 calls):

| call | expected | qwen25_7b | qwen25_7b_facts_oracle | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:38-01:13 trade: Öppe achttuusig Franke. Mini Schwöschter schaffet det i de Finanzabteilig. Sie het mir gester gseit, d Quartalszahle sind viel besser als erwartet. Die sind no nöd publiziert; die M... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Si het am Mäntig vo ere Übernahme verzellt. En grössere Konzern wett d Firma chaufe. Si schaffet i de Finanzabteilig und het mir interne Zahlen und de vorgsehni Priis zeigt. Die Sac... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | no_alert | 0.69/0.13 | broken | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.13 ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.14 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.1... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D09-K1 | alarm | alarm | no_alert | 0.87/0.00 | broken | 02:37-03:00 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.87/0.00 | broken | 02:39-03:02 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen u... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:48-01:03 trade: Es gaht um d Seerain Systeme. Ich kenne d Produkt us minere Arbeit, aber d Aktie ha ich bis jetzt nie gha. Ich ha letschti Wuche en Bericht über de neue Grossauftrag gseh. - facts: ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:37-01:01 trade: Mini Cousine isch im Projektteam vo de Albis Optik. Si het mir gester de neue Absatzbericht persönlich zeigt. De gaht erst morn an d Medie; bis denn dörf s Team ihn nöd wiitergee. E... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:38-01:01 trade: Mini Cousine isch im Projektteam vo de Albis Optik. Si het mir gester de neue Absatzbericht persönlich zeigt. De gaht erst morn an d Medie; bis denn dörf s Team ihn nöd wiitergee. E... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:26-01:36 access: Ich weiss nöd, ob de Wert obe oder unde zueghört. De Text isch so chlii, dass ich s Bild grad vergrossere muess. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (0.99... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | alarm | 0.46/0.50 | same | 01:27-01:37 access: Ich weiss nöd, ob de Wert obe oder unde zueghört. De Text isch so chlii, dass ich s Bild grad vergrossere muess. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (0.99... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts__blind_review` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts__blind_review - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_review | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.87 | +0.192 | [+0.093, +0.311] | **real**: qwen25_14b_facts__blind_review better |
| alarm AUC | 0.79 | 0.88 | +0.090 | [+0.002, +0.170] | **real**: qwen25_14b_facts__blind_review better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__blind_review - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_review | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.79 | +0.129 | [+0.013, +0.273] | **real**: qwen25_14b_facts__blind_review better |
| alarm_f1 | 0.49 | 0.79 | +0.303 | [+0.109, +0.505] | **real**: qwen25_14b_facts__blind_review better |
| false_alarm_rate | 86% | 36% | -50pp | [-75pp, -25pp] | **real**: qwen25_14b_facts__blind_review better |
| miss_rate | 15% | 15% | +0pp | [-15pp, +15pp] | no detectable difference |
| accuracy | 38% | 69% | +31pp | [+10pp, +52pp] | **real**: qwen25_14b_facts__blind_review better |
| review_recall | 83% | 33% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.74 | +0.250 | [+0.100, +0.409] | **real**: qwen25_14b_facts__blind_review better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_14b_facts__blind_review 13, p=0.0074; 3-class only-qwen25_7b 3 vs only-qwen25_14b_facts__blind_review 18, p=0.0015.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__blind_review - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_review | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.79 | +0.143 | [+0.037, +0.273] | **real**: qwen25_14b_facts__blind_review better |
| alarm_f1 | 0.17 | 0.72 | +0.544 | [+0.214, +0.824] | **real**: qwen25_14b_facts__blind_review better |
| false_alarm_rate | 55% | 36% | -18pp | [-35pp, +0pp] | no detectable difference |
| miss_rate | 31% | 15% | -15pp | [-32pp, +0pp] | no detectable difference |
| accuracy | 31% | 65% | +33pp | [+18pp, +48pp] | **real**: qwen25_14b_facts__blind_review better |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.74 | +0.168 | [+0.051, +0.292] | **real**: qwen25_14b_facts__blind_review better |

McNemar exact (calls): flag correct only-qwen25_7b 1 vs only-qwen25_14b_facts__blind_review 9, p=0.0215; 3-class only-qwen25_7b 0 vs only-qwen25_14b_facts__blind_review 16, p=0.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__blind_review - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__blind_review | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.79 | +0.091 | [-0.016, +0.223] | no detectable difference |
| alarm_f1 | 0.61 | 0.79 | +0.177 | [-0.016, +0.425] | no detectable difference |
| false_alarm_rate | 95% | 36% | -59pp | [-86pp, -33pp] | **real**: qwen25_14b_facts__blind_review better |
| miss_rate | 4% | 15% | +12pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 38% | 67% | +29pp | [+7pp, +50pp] | **real**: qwen25_14b_facts__blind_review better |
| review_recall | 100% | 83% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.74 | +0.238 | [+0.105, +0.373] | **real**: qwen25_14b_facts__blind_review better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_facts__blind_review 13, p=0.0213; 3-class only-qwen25_7b 3 vs only-qwen25_14b_facts__blind_review 17, p=0.0026.

Flips (cv, 28 calls):

| call | expected | qwen25_7b | qwen25_14b_facts__blind_review | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.96 | fixed | 01:28-01:31 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kund sagte, er wolle Aktien kaufen. (Regel: trade.a... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | no_alert | 0.69/0.11 | broken | 00:56-01:06 access: Die LAP, und da stark der neu bestätigte WUS-Code ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.11 ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.17 | same | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.17 | same | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:15 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für 6000 Franken aktiv von den Seerland Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. D... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.97 | same | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.17 | same | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - Zweitmeinung facts_blind zu «Auskunft an Dritte»: offen (und... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.96 | same | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.95 | same | 07:57-08:07 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts: Fakt: V... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.50 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:33-01:48 access: Bitte sagen Sie nur den Lesbauer-Tekt, die Zahl bleibt bei Ihnen. Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 00:10-00:22 disclosure: Haus, ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zugegeben, ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. - ... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | alarm | 0.43/0.50 | same | 01:49-01:55 splitting: Können Sie die 4000 für heute und die 5000 für morgen trotzdem schon vorbeweiten? - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (0.61) - Frau Gislo fragt, ob die 4000 C... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b_facts_en` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b_facts_en - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.82 | +0.146 | [+0.009, +0.277] | **real**: qwen25_7b_facts_en better |
| alarm AUC | 0.79 | 0.90 | +0.108 | [+0.007, +0.188] | **real**: qwen25_7b_facts_en better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_en - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.75 | +0.093 | [-0.112, +0.291] | no detectable difference |
| alarm_f1 | 0.49 | 0.76 | +0.274 | [+0.066, +0.492] | **real**: qwen25_7b_facts_en better |
| false_alarm_rate | 86% | 18% | -68pp | [-91pp, -43pp] | **real**: qwen25_7b_facts_en better |
| miss_rate | 15% | 31% | +15pp | [-5pp, +40pp] | no detectable difference |
| accuracy | 38% | 71% | +33pp | [+7pp, +58pp] | **real**: qwen25_7b_facts_en better |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.76 | +0.264 | [+0.091, +0.425] | **real**: qwen25_7b_facts_en better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b_facts_en 16, p=0.0266; 3-class only-qwen25_7b 5 vs only-qwen25_7b_facts_en 21, p=0.0025.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_en - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.75 | +0.107 | [-0.079, +0.274] | no detectable difference |
| alarm_f1 | 0.17 | 0.78 | +0.607 | [+0.266, +0.889] | **real**: qwen25_7b_facts_en better |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -6pp] | **real**: qwen25_7b_facts_en better |
| miss_rate | 31% | 31% | +0pp | [-19pp, +23pp] | no detectable difference |
| accuracy | 31% | 71% | +40pp | [+14pp, +62pp] | **real**: qwen25_7b_facts_en better |
| review_recall | 50% | 0% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.76 | +0.182 | [+0.017, +0.364] | **real**: qwen25_7b_facts_en better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_7b_facts_en 11, p=0.0574; 3-class only-qwen25_7b 3 vs only-qwen25_7b_facts_en 22, p=0.0002.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_en - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_en | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.75 | +0.056 | [-0.162, +0.260] | no detectable difference |
| alarm_f1 | 0.61 | 0.80 | +0.189 | [-0.010, +0.420] | no detectable difference |
| false_alarm_rate | 95% | 18% | -77pp | [-95pp, -56pp] | **real**: qwen25_7b_facts_en better |
| miss_rate | 4% | 31% | +27pp | [+6pp, +54pp] | **real**: qwen25_7b better |
| accuracy | 38% | 71% | +33pp | [+5pp, +58pp] | **real**: qwen25_7b_facts_en better |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.76 | +0.252 | [+0.084, +0.409] | **real**: qwen25_7b_facts_en better |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen25_7b_facts_en 17, p=0.0639; 3-class only-qwen25_7b 5 vs only-qwen25_7b_facts_en 21, p=0.0025.

Flips (cv, 29 calls):

| call | expected | qwen25_7b | qwen25_7b_facts_en | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.99 | fixed | 01:28-01:36 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. - facts: Fakt: Eigener Handelswunsch ge... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:05-02:18 trade: Nein, bis jetzt mehr. Ich habe die Firma aber seit ein paar Monaten im Blick. Eine Kollegin muss in der Lehrzeit arbeiten dort. Wir gehen ab und zu zusammen zu Mittag, aber ich habe... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.95 | same | 01:17-01:51 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? Warte, nicht mehr vorzulesen, ich kann... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/1.00 | same | 01:09-01:23 trade: Claudia leitet das Projekt bei der Firma, sie hat mir den unterschriebenen grossen Auftrag persönlich gezeigt, weil wir uns privat kennen, der Inhalt bleibt bis zur Präsentation am ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.82 | same | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.98 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.06 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.89 | same | 01:10-01:30 documentation: Der violette Satz nennt meine alte Kontaktadresse. Diese ist falsch und für den vorgesehenen Entscheid nicht relevant. Aktuelle Adressen stehen richtig im Kontaktfeld. Die r... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - facts: Fakt: Im Gespräch offen, ob der Wert gültig ist =... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | alarm | 0.46/0.50 | same | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | no_alert | 0.69/0.00 | broken | 00:23-00:50 documentation: Dann müssen wir einmal vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hat jeder Schwester für den Kontakt hinterlegt? Sie... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts_l3__blind_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.85 | +0.176 | [+0.065, +0.303] | **real**: qwen25_14b_facts_l3__blind_only better |
| alarm AUC | 0.79 | 0.84 | +0.050 | [-0.066, +0.135] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.84 | +0.180 | [+0.057, +0.355] | **real**: qwen25_14b_facts_l3__blind_only better |
| alarm_f1 | 0.49 | 0.62 | +0.128 | [-0.208, +0.425] | no detectable difference |
| false_alarm_rate | 86% | 27% | -59pp | [-86pp, -27pp] | **real**: qwen25_14b_facts_l3__blind_only better |
| miss_rate | 15% | 12% | -4pp | [-18pp, +8pp] | no detectable difference |
| accuracy | 38% | 58% | +21pp | [-11pp, +52pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.81 | +0.315 | [+0.149, +0.477] | **real**: qwen25_14b_facts_l3__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 1 vs only-qwen25_14b_facts_l3__blind_only 15, p=0.0005; 3-class only-qwen25_7b 10 vs only-qwen25_14b_facts_l3__blind_only 20, p=0.0987.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.84 | +0.194 | [+0.080, +0.358] | **real**: qwen25_14b_facts_l3__blind_only better |
| alarm_f1 | 0.17 | 0.26 | +0.087 | [-0.364, +0.500] | no detectable difference |
| false_alarm_rate | 55% | 27% | -27pp | [-57pp, +0pp] | no detectable difference |
| miss_rate | 31% | 12% | -19pp | [-33pp, -7pp] | **real**: qwen25_14b_facts_l3__blind_only better |
| accuracy | 31% | 50% | +19pp | [+0pp, +40pp] | no detectable difference |
| review_recall | 50% | 83% | +33pp | [+0pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.81 | +0.233 | [+0.083, +0.409] | **real**: qwen25_14b_facts_l3__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 0 vs only-qwen25_14b_facts_l3__blind_only 11, p=0.001; 3-class only-qwen25_7b 2 vs only-qwen25_14b_facts_l3__blind_only 11, p=0.0225.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.84 | +0.142 | [+0.025, +0.309] | **real**: qwen25_14b_facts_l3__blind_only better |
| alarm_f1 | 0.61 | 0.62 | +0.010 | [-0.289, +0.282] | no detectable difference |
| false_alarm_rate | 95% | 27% | -68pp | [-94pp, -38pp] | **real**: qwen25_14b_facts_l3__blind_only better |
| miss_rate | 4% | 12% | +8pp | [+0pp, +18pp] | no detectable difference |
| accuracy | 38% | 62% | +25pp | [-2pp, +54pp] | no detectable difference |
| review_recall | 100% | 83% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.81 | +0.302 | [+0.150, +0.438] | **real**: qwen25_14b_facts_l3__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_14b_facts_l3__blind_only 15, p=0.0023; 3-class only-qwen25_7b 6 vs only-qwen25_14b_facts_l3__blind_only 18, p=0.0227.

Flips (cv, 37 calls):

| call | expected | qwen25_7b | qwen25_14b_facts_l3__blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:48-00:53 trade: Diese sind noch nicht publiziert. Die Medienmeldung kommt erst am Freitag. - facts_blind: Fakt: Handelswunsch mit erhaltener Information begründet = ja (0.84) - Frau Aibi erklärt, d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Firma gesprochen. Sie hat mir über einen Namen erzählt. Im grösseren Konzern will die Firma auch kaufen. Sie arbeitet in der Finanzabteilung und hat mir ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.99 | same | 01:08-01:15 access: Bitte gehen Sie den Wert selber im vorgesehenen Feld ein. Ich brauche nur die Rückmeldung, ob es klappt. - facts_blind: Fakt: Wert gehört zum laufenden Vorgang = ja (0.98) - Der Ku... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.50 | same | 01:37-01:48 documentation: So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. Können Sie mir zeigen, wie ich mehrere Zahlungen separat er... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.95/0.50 | same | 01:38-01:45 documentation: So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt sieht. - facts_blind: Fakt: Verlangt Nicht-Protokollieren = ja (0.... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.50 | same | 00:52-00:57 trade: Ich habe letzte Woche einen Bericht über den neuen Grossauftrag gesehen. - facts_blind: Fakt: Handelswunsch mit erhaltener Information begründet = ja (0.99) - Frau Keller hat einen ... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.50 | same | 00:53-01:20 trade: Ich habe letzte Woche einen Bericht über den neuen Grossauftrag gesehen. Wo haben Sie den Bericht gesehen? Im Telefonmund steht nur ein Bericht von Claudia. Ich weiss zumal noch nic... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.50 | same | 01:09-01:51 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.99 | same | 00:40-00:44 trade: Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - facts_blind: Fakt: Information noch nicht öffentlich = ja (0.99) - Frau Bühler sagte, dass ihre Cousine ihr den neu... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.50 | same | 00:15-00:21 disclosure: Ich werde ihr die ganzen Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Der Kunde fragt nac... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.50 | same | 00:23-00:29 disclosure: Wir müssen vor einer konkreten Auskunft festhalten, welche Rolle Sie in diesem Vorgang haben. - facts_blind: Fakt: Anfrage zu Drittperson = ja (0.99) - Der Berater fragt die Ku... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.50 | same | 03:16-03:18 disclosure: Ich muss für meine Liste wissen, - facts_blind: Fakt: Anfrage zu Drittperson = ja (0.77) - Der Kunde fragt nach dem aktuellen Kontostand seiner Mutter. (Regel: disclosure.revie... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.50 | same | 00:10-00:22 disclosure: Ja, sie ist zurzeit im Spital und ich habe mit ihr die Unterlagen. Ich werde ihr die ganzen Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - facts_bl... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 07:58-08:11 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit dem, was Sie am Anfang über den Satz... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:06 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts_blind: Fakt: Verlangt Nicht-Protokollieren = ja (0.93) - Frau Imhoff ... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:54-08:04 documentation: Dann lässt mir der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts_b... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.50 | same | 08:03-08:07 documentation: Ich will, dass die Finanzierung den Inhalt der genau diesen Satz nicht zu sehen bekommt. - facts_blind: Fakt: Verlangt Nicht-Protokollieren = ja (0.84) - Frau Inhoff fordert... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:41-01:43 access: 2, 9, 6, 4, 8, 1. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.66) - Der Kunde nennt die Zahlenreihe '2, 9, 6, 4, 8, 1'. (Regel: access.review_1) | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | alarm | 0.46/0.50 | same | 01:42-01:45 access: 2, 9, 6, 4, 8, 1. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.98) - Der Kund hat die Zahlenfolge '2, 9, 6, 4, 8, 1' vollständig ausgesprochen. (Regel: access.review... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 03:37-03:43 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Der Kundendienstle... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:39-03:45 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Die Kundin fragt n... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | alarm | 0.43/0.50 | same | 01:28-01:32 splitting: Ich wollte zuerst nur wissen, ob man zwei verschiedene Daten erfassen kann. - facts_blind: Fakt: Aufteilen verlangt = ja (0.60) - Der Kunde fragt, ob man zwei verschiedene Daten... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts_l3__both` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.87 | +0.195 | [+0.098, +0.317] | **real**: qwen25_14b_facts_l3__both better |
| alarm AUC | 0.79 | 0.89 | +0.094 | [+0.008, +0.175] | **real**: qwen25_14b_facts_l3__both better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.79 | +0.136 | [-0.003, +0.316] | no detectable difference |
| alarm_f1 | 0.49 | 0.65 | +0.162 | [-0.196, +0.467] | no detectable difference |
| false_alarm_rate | 86% | 27% | -59pp | [-86pp, -27pp] | **real**: qwen25_14b_facts_l3__both better |
| miss_rate | 15% | 19% | +4pp | [-14pp, +21pp] | no detectable difference |
| accuracy | 38% | 62% | +25pp | [-6pp, +52pp] | no detectable difference |
| review_recall | 83% | 17% | -67pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.276 | [+0.106, +0.442] | **real**: qwen25_14b_facts_l3__both better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_facts_l3__both 15, p=0.0075; 3-class only-qwen25_7b 9 vs only-qwen25_14b_facts_l3__both 21, p=0.0428.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.78 | +0.141 | [-0.008, +0.306] | no detectable difference |
| alarm_f1 | 0.17 | 0.36 | +0.183 | [-0.320, +0.583] | no detectable difference |
| false_alarm_rate | 55% | 23% | -32pp | [-61pp, -5pp] | **real**: qwen25_14b_facts_l3__both better |
| miss_rate | 31% | 23% | -8pp | [-25pp, +11pp] | no detectable difference |
| accuracy | 31% | 52% | +21pp | [-2pp, +42pp] | no detectable difference |
| review_recall | 50% | 50% | +0pp | [-50pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.77 | +0.198 | [+0.036, +0.373] | **real**: qwen25_14b_facts_l3__both better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_14b_facts_l3__both 11, p=0.0225; 3-class only-qwen25_7b 3 vs only-qwen25_14b_facts_l3__both 13, p=0.0213.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.80 | +0.106 | [-0.061, +0.292] | no detectable difference |
| alarm_f1 | 0.61 | 0.62 | +0.010 | [-0.289, +0.282] | no detectable difference |
| false_alarm_rate | 95% | 18% | -77pp | [-95pp, -55pp] | **real**: qwen25_14b_facts_l3__both better |
| miss_rate | 4% | 23% | +19pp | [+4pp, +38pp] | **real**: qwen25_7b better |
| accuracy | 38% | 62% | +25pp | [-2pp, +52pp] | no detectable difference |
| review_recall | 100% | 50% | -50pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.79 | +0.290 | [+0.166, +0.408] | **real**: qwen25_14b_facts_l3__both better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_14b_facts_l3__both 17, p=0.0169; 3-class only-qwen25_7b 8 vs only-qwen25_14b_facts_l3__both 20, p=0.0357.

Flips (cv, 33 calls):

| call | expected | qwen25_7b | qwen25_14b_facts_l3__both | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:37-00:43 trade: Etwa 8000 Franken. Meine Schwester arbeitet dort in der Finanzabteilung. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Frau Aibi erklärt, dass ih... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Firma gesprochen. Sie hat mir über einen Namen erzählt. Im grösseren Konzern will die Firma auch kaufen. Sie arbeitet in der Finanzabteilung und hat mir ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.98 | same | 01:08-01:24 access: Bitte gehen Sie den Wert selber im vorgesehenen Feld ein. Ich brauche nur die Rückmeldung, ob es klappt. Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. ... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.12 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.1... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.50 | same | 00:35-00:40 splitting: Es ist eine einzige Rechnung für diese eine Maschine. Es gibt nicht zwei Lieferungen. - facts: Fakt: Teilbeträge gehören zu einer einzigen Rechnung = ja (1.00) - Frau Huber best... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.95/0.50 | same | 00:21-00:29 splitting: Bei uns muss eine zusammengehende Lieferantennzahl in über zehntausend Franken vor der Ausführung in den Pfleger gegeben werden. - facts: Fakt: Teilbeträge gehören zu einer einz... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.30 (Schwelle 0.45 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.30 (Schwelle 0.45 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.13 | same | 00:52-00:57 trade: Ich habe letzte Woche einen Bericht über den neuen Grossauftrag gesehen. - facts_blind: Fakt: Handelswunsch mit erhaltener Information begründet = ja (0.99) - Frau Keller hat einen ... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:03-08:12 trade: Genau wegen diesem Bericht möchte ich heute von sechstausend Franken Aktien von den Seerlern-Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. - facts: Fakt: Eigener Handel... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.95 | same | 00:40-00:48 trade: Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Der geht erst einmal an die Mädchen, bis dann darf das Team ihn nicht weitergeben. - facts_blind: Fakt: Information n... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.68 | same | 00:00-00:09 disclosure: Guten Morgen, Frau Fey, hier ist Marion Huyon. Sie haben wegen der laufenden Wohnkosten von ihrer Mutter um den Rücklauf gebeten. - facts: Fakt: Auskunft über Drittperson verla... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.78 | same | 00:10-00:22 disclosure: Ja, sie ist zurzeit im Spital und ich habe mit ihr die Unterlagen. Ich werde ihr die ganzen Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - facts: F... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 07:54-08:11 documentation: Dann lässt mich der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehm... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:54-08:04 documentation: Dann lässt mir der Violett Machiat den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts: ... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.15 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.15 ('Zugangsinformation pre... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | alarm | 0.46/0.50 | same | 01:42-01:49 access: 2, 9, 6, 4, 8, 1. Ob es jetzt oder damals gültig ist, kann ich nicht sagen. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.95) - Der Kunde liest die Zahlenfolge '2, 9, 6, 4... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 00:00-00:08 disclosure: Guten Tag, Frau Ott, das ist Daniela Vogt. Sie haben wegen dem Haushaltskonto ihrer Schwester um einen Neukauf gewünscht. - facts: Fakt: Auskunft über Drittperson verlangt = ja... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:39-03:45 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Die Kundin f... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |

## `qwen25_14b_facts__both` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.88 | +0.205 | [+0.102, +0.325] | **real**: qwen25_14b_facts__both better |
| alarm AUC | 0.79 | 0.90 | +0.113 | [+0.039, +0.186] | **real**: qwen25_14b_facts__both better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.79 | +0.136 | [-0.019, +0.330] | no detectable difference |
| alarm_f1 | 0.49 | 0.65 | +0.161 | [-0.146, +0.436] | no detectable difference |
| false_alarm_rate | 86% | 27% | -59pp | [-86pp, -27pp] | **real**: qwen25_14b_facts__both better |
| miss_rate | 15% | 19% | +4pp | [-15pp, +25pp] | no detectable difference |
| accuracy | 38% | 60% | +23pp | [-6pp, +50pp] | no detectable difference |
| review_recall | 83% | 17% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.276 | [+0.100, +0.450] | **real**: qwen25_14b_facts__both better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_facts__both 15, p=0.0075; 3-class only-qwen25_7b 7 vs only-qwen25_14b_facts__both 18, p=0.0433.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.80 | +0.157 | [+0.019, +0.315] | **real**: qwen25_14b_facts__both better |
| alarm_f1 | 0.17 | 0.41 | +0.240 | [-0.275, +0.636] | no detectable difference |
| false_alarm_rate | 55% | 18% | -36pp | [-63pp, -10pp] | **real**: qwen25_14b_facts__both better |
| miss_rate | 31% | 23% | -8pp | [-23pp, +7pp] | no detectable difference |
| accuracy | 31% | 54% | +23pp | [+0pp, +44pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-50pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.79 | +0.220 | [+0.059, +0.379] | **real**: qwen25_14b_facts__both better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_14b_facts__both 12, p=0.0129; 3-class only-qwen25_7b 4 vs only-qwen25_14b_facts__both 15, p=0.0192.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts__both - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.79 | +0.097 | [-0.081, +0.290] | no detectable difference |
| alarm_f1 | 0.61 | 0.62 | +0.010 | [-0.300, +0.314] | no detectable difference |
| false_alarm_rate | 95% | 14% | -82pp | [-100pp, -59pp] | **real**: qwen25_14b_facts__both better |
| miss_rate | 4% | 27% | +23pp | [+8pp, +41pp] | **real**: qwen25_7b better |
| accuracy | 38% | 62% | +25pp | [-2pp, +52pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.80 | +0.294 | [+0.154, +0.419] | **real**: qwen25_14b_facts__both better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_14b_facts__both 18, p=0.0227; 3-class only-qwen25_7b 9 vs only-qwen25_14b_facts__both 21, p=0.0428.

Flips (cv, 32 calls):

| call | expected | qwen25_7b | qwen25_14b_facts__both | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.85 | fixed | 01:28-01:39 trade: Gerade warum möchte ich diese Aktie jetzt kaufen von den Meldet? Wenn alle am Freitag die Quatalszahlen sehen, ist der Preis dort schon oben. Können Sie den Kaufleit für mich machen... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.15... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.99 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.51 | same | 00:35-00:40 splitting: Es ist eine einzige Rechnung für die eine Maschine, es gibt nicht zwei Lieferungen. - facts: Fakt: Teilbeträge gehören zu einer einzigen Rechnung = ja (1.00) - Der Kunde spricht... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.95/0.50 | same | 00:35-00:47 splitting: Es ist eine einzige Rechnung für die eine Maschine, es gibt nicht zwei Lieferungen. Ich habe das Formular gefunden, aber ich habe keine Lust, dass ich jetzt noch auf die Freigab... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.12 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.12 ('Zugangsinformation preisgegeben') liegt unter 0.15 (Schwelle 0.30 minus Band 0.... | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.12 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.12 ('Zugangsinformation preisgegeben') liegt unter 0.15 (Schwelle 0.30 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.18 | same | 01:14-01:27 trade: Der Grosse Auftrag wurde am letzten Freitag veröffentlicht und jeder kann ihn dort lesen. Sie arbeiten nicht bei dieser Firma, ich weiss nichts zu ersetzen und habe den gleichen Inh... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.12 | same | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:15 trade: Ja, ich habe mich jetzt entschieden. Genau wegen diesem Bericht möchte ich heute für 6000 Franken aktiv von den Seerland Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. D... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.98 | same | 00:35-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbewerb persönlich gezeigt, dann geht erst morgen an die Mädchen, bis dann darf das Team nicht wei... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:36-00:54 trade: Meine Cousine ist im Projektium der Albisoptik, sie hat mir gestern den neuen Absatzbericht persönlich gezeigt, der gerade erst Monat Mädchen, bis dann darfst du das Team ihm nicht ... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.12 | same | 00:54-01:19 disclosure: In diesem Vorgang haben Sie die gültige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten Umfang gedeckt. Gut, ich habe Ihre Erkläru... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.19 | same | 03:16-03:39 disclosure: Ich muss für meine Liste wissen, ob ich überhaupt mit dem vorhandenen Geld rechnen kann. Das Datum der Übersicht ist alt. Welches ist jetzt der aktuelle Stand für genau ihr Kon... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.96 | same | 07:57-08:07 documentation: Dann lernt man ja den violetten Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts_blind: F... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | alarm | 0.73/0.50 | same | 07:58-08:08 documentation: Dann lernt mir ja der Violett, mache ich ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. ... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | alarm | 0.47/0.50 | same | 01:33-01:48 access: Bitte sagen Sie nur den Lesbauer-Tekt, die Zahl bleibt bei Ihnen. Ich habe es jetzt schon vor mir, zwei, neun, sechs, vier, acht, eins. Ob es jetzt oder damals gültig ist, kann ich... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.12 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 00:10-00:22 disclosure: Haus, ja, sie ist für zwei Monate im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zugegeben, ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. - ... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.15 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_facts_oracle__blind_only` vs `qwen25_7b` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_facts_oracle__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.78 | +0.101 | [+0.007, +0.206] | **real**: qwen25_14b_facts_oracle__blind_only better |
| alarm AUC | 0.79 | 0.85 | +0.058 | [-0.064, +0.162] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_oracle__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.72 | +0.063 | [-0.130, +0.279] | no detectable difference |
| alarm_f1 | 0.49 | 0.79 | +0.300 | [+0.024, +0.565] | **real**: qwen25_14b_facts_oracle__blind_only better |
| false_alarm_rate | 86% | 27% | -59pp | [-88pp, -27pp] | **real**: qwen25_14b_facts_oracle__blind_only better |
| miss_rate | 15% | 31% | +15pp | [-12pp, +43pp] | no detectable difference |
| accuracy | 38% | 65% | +27pp | [+0pp, +54pp] | no detectable difference |
| review_recall | 83% | 33% | -50pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.71 | +0.218 | [+0.037, +0.400] | **real**: qwen25_14b_facts_oracle__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_14b_facts_oracle__blind_only 15, p=0.0784; 3-class only-qwen25_7b 7 vs only-qwen25_14b_facts_oracle__blind_only 20, p=0.0192.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_oracle__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.69 | +0.051 | [-0.150, +0.257] | no detectable difference |
| alarm_f1 | 0.17 | 0.67 | +0.493 | [+0.000, +0.889] | no detectable difference |
| false_alarm_rate | 55% | 27% | -27pp | [-64pp, +17pp] | no detectable difference |
| miss_rate | 31% | 35% | +4pp | [-21pp, +32pp] | no detectable difference |
| accuracy | 31% | 58% | +27pp | [+2pp, +52pp] | **real**: qwen25_14b_facts_oracle__blind_only better |
| review_recall | 50% | 33% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.69 | +0.117 | [-0.107, +0.333] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen25_14b_facts_oracle__blind_only 12, p=0.3593; 3-class only-qwen25_7b 6 vs only-qwen25_14b_facts_oracle__blind_only 19, p=0.0146.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_facts_oracle__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_14b_facts_oracle__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.72 | +0.026 | [-0.162, +0.223] | no detectable difference |
| alarm_f1 | 0.61 | 0.79 | +0.177 | [-0.054, +0.420] | no detectable difference |
| false_alarm_rate | 95% | 27% | -68pp | [-94pp, -39pp] | **real**: qwen25_14b_facts_oracle__blind_only better |
| miss_rate | 4% | 31% | +27pp | [+5pp, +50pp] | **real**: qwen25_7b better |
| accuracy | 38% | 65% | +27pp | [+0pp, +52pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.71 | +0.206 | [+0.056, +0.357] | **real**: qwen25_14b_facts_oracle__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen25_14b_facts_oracle__blind_only 15, p=0.1338; 3-class only-qwen25_7b 6 vs only-qwen25_14b_facts_oracle__blind_only 19, p=0.0146.

Flips (cv, 35 calls):

| call | expected | qwen25_7b | qwen25_14b_facts_oracle__blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:38-00:53 trade: Öppe achttuusig Franke. Mini Schwöschter schaffet det i de Finanzabteilig. Sie het mir gester gseit, d Quartalszahle sind viel besser als erwartet. Die sind no nöd publiziert; die M... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben'... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-03:27 trade: Si het am Mäntig vo ere Übernahme verzellt. En grössere Konzern wett d Firma chaufe. Si schaffet i de Finanzabteilig und het mir interne Zahlen und de vorgsehni Priis zeigt. Die Sac... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.98 | same | 01:16-01:40 access: Wart, ich säg Ihne die TAN grad: sibe, drü, eins, nüün, vier, zwei. Es staht immer no gültig. Chönd Sie mir säge, öb das die richtige Reihenfolg isch? Bitte nümme vorzläse. Ich cha... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.50 | same | 00:33-00:49 splitting: Es isch e einzigi Rechnig für die eini Maschine. Es git nöd zwei Lieferige. Ich ha s Formular gfunde, aber ich ha kei Lust, dass ich jetzt no uf d Freigab warte. - facts_blind: ... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.50 | same | 01:13-01:33 trade: Claudia het mir de Link zum Bericht uf de Firmenwebsite gschickt. De Grossauftrag isch am letschte Friitig veröffentlicht worde, und jede cha ihn det läse. Si schaffet nöd bi dere F... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.50 | same | 00:48-01:03 trade: Es gaht um d Seerain Systeme. Ich kenne d Produkt us minere Arbeit, aber d Aktie ha ich bis jetzt nie gha. Ich ha letschti Wuche en Bericht über de neue Grossauftrag gseh. - facts_b... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:48-01:03 trade: Es gaht um d Seerain Systeme. Ich kenne d Produkt us minere Arbeit, aber d Aktie ha ich bis jetzt nie gha. Ich ha letschti Wuche en Bericht über de neue Grossauftrag gseh. - facts_b... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:37-01:01 trade: Mini Cousine isch im Projektteam vo de Albis Optik. Si het mir gester de neue Absatzbericht persönlich zeigt. De gaht erst morn an d Medie; bis denn dörf s Team ihn nöd wiitergee. E... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/1.00 | same | 00:38-01:01 trade: Mini Cousine isch im Projektteam vo de Albis Optik. Si het mir gester de neue Absatzbericht persönlich zeigt. De gaht erst morn an d Medie; bis denn dörf s Team ihn nöd wiitergee. E... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | review | 0.52/0.50 | same | 00:37-01:00 trade: Ich ha gester de neue Absatzbericht uf de Website vo de Albis Optik gläse. De isch am Morge an d Medie gange und für alli verfügbar. Es isch deutlich meh verkauft worde als erwartet... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | review | 0.54/0.50 | same | 03:33-03:46 trade: Ja, ich ha mi jetzt entschiede. Wäge dere Nachricht wett ich hüt für füünftuusig Franke Aktie vo de Albis Optik chaufe. Chönd Sie de einmaligi Auftrag für mich entgegeneh? - facts_b... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | review | 0.53/0.50 | same | 03:21-03:46 disclosure: Ich muess für mini Liste wüsse, ob ich überhaupt mit em vorhandene Geld rechne cha. S Datum vo de Übersicht isch alt. Weles isch jetzt de aktuelli Stand für genau ihres Konto? ... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.50 | same | 03:39-03:48 disclosure: Uf dem Konto sind aktuell sechstuusigvierhundert Franke verfügbar. Das isch de persönliche Stand vo Ihrer Mueter hüt am Morge. - facts_blind: Fakt: Anfrage zu Drittperson = ja ... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.50 | same | 03:19-03:44 disclosure: Ich muess für mini Liste wüsse, ob ich überhaupt mit em vorhandene Geld rechne cha. S Datum vo de Übersicht isch alt. Weles isch jetzt de aktuelli Stand für genau ihres Konto? ... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.50 | same | 00:48-01:06 disclosure: Ihre eigene Identität isch bestätigt. Für s Konto vo Ihrer Mueter isch aber kei Auskunftsrecht hinterleit, und d Abklärig het ergeben, dass Sie in dem Vorgang kei Berechtigung ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | no_alert | 0.77/0.00 | broken | 01:09-01:29 documentation: Der violette Satz sagt, dass 30 000 von meinem Bruder ein Rückzahlpass darlegen sind. Das ist richtig. Es ist ein Teil der Finanzierung, keine privaten Kontaktanlage. Der Sa... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | no_alert | 0.71/0.00 | broken | 07:47-08:17 documentation: Ja, sie meinen die violette Zeilen im aktuellen auf. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt man ja den violetten Satz aus dem Dossier heraus. I... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K4 | review | no_alert | review | 0.54/0.50 | fixed | 03:39-03:47 disclosure: Chönd Sie mir bis dahin wenigstens säge, ob uf ihrem Konto gnueg für d Wohnigsrechnung liit? - facts_blind: Fakt: Anfrage zu Drittperson = ja (0.99) - Frau Ott fragt nach dem G... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b__both` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.82 | +0.144 | [+0.037, +0.267] | **real**: qwen25_7b__both better |
| alarm AUC | 0.79 | 0.85 | +0.061 | [-0.032, +0.138] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.128 | [-0.025, +0.292] | no detectable difference |
| alarm_f1 | 0.49 | 0.36 | -0.131 | [-0.468, +0.197] | no detectable difference |
| false_alarm_rate | 86% | 23% | -64pp | [-88pp, -36pp] | **real**: qwen25_7b__both better |
| miss_rate | 15% | 23% | +8pp | [-14pp, +29pp] | no detectable difference |
| accuracy | 38% | 52% | +15pp | [-12pp, +40pp] | no detectable difference |
| review_recall | 83% | 50% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.280 | [+0.129, +0.436] | **real**: qwen25_7b__both better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_7b__both 16, p=0.0118; 3-class only-qwen25_7b 10 vs only-qwen25_7b__both 17, p=0.2478.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.72 | +0.081 | [-0.102, +0.258] | no detectable difference |
| alarm_f1 | 0.17 | 0.00 | -0.174 | [-0.500, +0.000] | no detectable difference |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -7pp] | **real**: qwen25_7b__both better |
| miss_rate | 31% | 35% | +4pp | [-18pp, +27pp] | no detectable difference |
| accuracy | 31% | 40% | +8pp | [-14pp, +30pp] | no detectable difference |
| review_recall | 50% | 17% | -33pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.74 | +0.163 | [-0.011, +0.326] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_7b__both 12, p=0.1435; 3-class only-qwen25_7b 5 vs only-qwen25_7b__both 9, p=0.424.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.68 | -0.013 | [-0.218, +0.206] | no detectable difference |
| alarm_f1 | 0.61 | 0.33 | -0.278 | [-0.549, -0.038] | **real**: qwen25_7b better |
| false_alarm_rate | 95% | 14% | -82pp | [-100pp, -59pp] | **real**: qwen25_7b__both better |
| miss_rate | 4% | 42% | +38pp | [+19pp, +57pp] | **real**: qwen25_7b better |
| accuracy | 38% | 50% | +12pp | [-18pp, +40pp] | no detectable difference |
| review_recall | 100% | 17% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.50 | 0.72 | +0.217 | [+0.065, +0.359] | **real**: qwen25_7b__both better |

McNemar exact (calls): flag correct only-qwen25_7b 10 vs only-qwen25_7b__both 18, p=0.1849; 3-class only-qwen25_7b 13 vs only-qwen25_7b__both 19, p=0.3771.

Flips (cv, 32 calls):

| call | expected | qwen25_7b | qwen25_7b__both | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | review | 0.68/0.85 | fixed | 01:05-01:09 trade: Und auch alles, sie hat mir sogar ein Foto von der Iguessicht gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.93) - Die Kunde erwähnt ein Foto d... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben'... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/0.94 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Übernahme erzählt. Ein grösserer Konzerm will viermal kaufen. Sie arbeitet in der Finanzabteilung und hat mir nur Zahlen und den vorgesehenen Preis gezei... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.88 | same | 01:17-01:28 access: Warte, ich sage Ihnen die Tarnkarte, 7, 3, 1, 9, 4, 2, es steht immer noch gültig. Können Sie mir sagen, ob das die richtige Reihenfolge ist? - facts: Fakt: Code/Wert am Telefon vo... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.04 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.39 | same | 02:37-02:52 documentation: Dann bitte nicht protokollieren, dass ich die 20 000 zurückzahlen muss. Nehmen die Zarlehe nicht in die Notiz für die Kreditstelle. Ich will, dass ich nur Eigenmittel sehe u... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.87/0.64 | same | 00:43-01:00 documentation: Es sind 20 000 Franken meiner Tante. Ich muss jetzt zurückzahlen, und wir haben jetzt einen Unterschritt nicht vereinbart. Verwescht sind meine eigenen Ersparnisse. Ich kenn... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.71 | same | 01:32-01:58 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe stellt die ganze Rechnung überhaupt sieht. Können Sie mir z... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.95/0.43 | same | 01:33-01:50 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe-Stell die ganze Rechnung überhaupt sieht. Können Sie mir ja... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15... | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.02 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:10-01:27 trade: Claudia hat mir den Link zum Bericht auf den Firmenmarkt verschickt. Der Grosse Auftrag wurde am letzten Freitag veröffentlicht, und jeder kann ihn dort lesen. Sie arbeiten nicht be... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K3 | alarm | alarm | review | 0.70/0.46 | same | 00:44-00:57 trade: Es geht um die CRM-Systeme, ich habe die Janet Produz aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt, ich habe letzte Woche einen Bericht über den neuen GoSauftrag... | llm_judge: Die Kunde möchte die aktuelle Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokollieren, was als Verschweigen einer relevanten Angabe interpretiert werden kann. |
| Stufe2_C06-K4 | alarm | review | no_alert | 0.71/0.06 | broken | 00:45-00:57 trade: Es geht um die CRN -Systeme, ich habe die Schenet -Produkte aus meiner Arbeit, aber die Aktien habe ich bisher nie gehabt, ich habe letzte Woche einen Bereich über den neuen GoSELF ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.50 | same | 03:28-03:50 trade: Ja, ich habe mich jetzt entschieden, wegen dieser Nachricht möchte ich heute für 5000 Franken Aktien von der Albis Optik kaufen, können Sie den einmaligen Auftrag für mich entgegnen... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K4 | no_alert | alarm | review | 0.70/0.17 | same | 03:34-03:44 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Der Advisor bestätigt den aktuellen Kontostand von 6400 Franken und gibt diese konkreten Daten an die Customer, ohne dass die Customer die Berechtigung für diese Auskunft bestätigt hat. |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.40 | same | 00:51-01:03 disclosure: Sie haben aber kein Auskundsrecht hinterlegt und die Abfährung ergeben, dass sie im dem Vorgang keine Berechtigung zum Kontostand haben. Die familiäre Beziehung allein lehnt da... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.12 | same | 03:32-03:41 disclosure: Auf diesem Konto sind aktuell 6400 Franken verfügbar. Das ist der persönliche Stand ihrer Mutter heute am Morgen. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C14-K3 | no_alert | review | alarm | 0.71/0.50 | same | 07:55-08:05 documentation: Dann lehnt ja der Violett, mache ja den Satz aus dem Dossier heraus. Ich will, dass die Finanzierungsstelle den Inhalt genau dieses Satzes nicht zu sehen bekommt. Ich - fact... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 00:23-01:07 disclosure: Dann müssen wir vor einer konkreten Auskunft schauen, welche sie sind und welche Auskunft sie erhalten dürfen. Was hinterlegt ihr der Schwester durch den Kontakt? Sie sagte, es... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b_facts_l3__blind_only` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.79 | +0.109 | [-0.026, +0.221] | no detectable difference |
| alarm AUC | 0.79 | 0.85 | +0.060 | [-0.081, +0.160] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.67 | +0.010 | [-0.254, +0.260] | no detectable difference |
| alarm_f1 | 0.49 | 0.56 | +0.068 | [-0.329, +0.420] | no detectable difference |
| false_alarm_rate | 86% | 18% | -68pp | [-92pp, -39pp] | **real**: qwen25_7b_facts_l3__blind_only better |
| miss_rate | 15% | 42% | +27pp | [-3pp, +57pp] | no detectable difference |
| accuracy | 38% | 58% | +21pp | [-12pp, +52pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.70 | +0.206 | [+0.000, +0.409] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 9 vs only-qwen25_7b_facts_l3__blind_only 17, p=0.1686; 3-class only-qwen25_7b 11 vs only-qwen25_7b_facts_l3__blind_only 21, p=0.1102.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.64 | -0.006 | [-0.262, +0.239] | no detectable difference |
| alarm_f1 | 0.17 | 0.40 | +0.226 | [-0.282, +0.667] | no detectable difference |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -6pp] | **real**: qwen25_7b_facts_l3__blind_only better |
| miss_rate | 31% | 46% | +15pp | [-12pp, +42pp] | no detectable difference |
| accuracy | 31% | 52% | +21pp | [-4pp, +44pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.68 | +0.105 | [-0.122, +0.317] | no detectable difference |

McNemar exact (calls): flag correct only-qwen25_7b 7 vs only-qwen25_7b_facts_l3__blind_only 11, p=0.4807; 3-class only-qwen25_7b 4 vs only-qwen25_7b_facts_l3__blind_only 14, p=0.0309.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3__blind_only - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.67 | -0.028 | [-0.281, +0.219] | no detectable difference |
| alarm_f1 | 0.61 | 0.60 | -0.011 | [-0.367, +0.256] | no detectable difference |
| false_alarm_rate | 95% | 18% | -77pp | [-100pp, -50pp] | **real**: qwen25_7b_facts_l3__blind_only better |
| miss_rate | 4% | 42% | +38pp | [+15pp, +62pp] | **real**: qwen25_7b better |
| accuracy | 38% | 60% | +23pp | [-9pp, +50pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.70 | +0.194 | [+0.006, +0.365] | **real**: qwen25_7b_facts_l3__blind_only better |

McNemar exact (calls): flag correct only-qwen25_7b 10 vs only-qwen25_7b_facts_l3__blind_only 17, p=0.2478; 3-class only-qwen25_7b 9 vs only-qwen25_7b_facts_l3__blind_only 20, p=0.0614.

Flips (cv, 33 calls):

| call | expected | qwen25_7b | qwen25_7b_facts_l3__blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.97 | fixed | 00:37-00:53 trade: Etwa 8000 Franken. Meine Schwester arbeitet dort in der Finanzabteilung. Sie hat mir gestern gesagt, Quartalszahlen seien viel besser als erwartet. Diese sind noch nicht publiziert.... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben'... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:49-03:32 trade: Diese Unterlagen haben Sie von Ihrer Kollegin persönlich bekommen. Es geht nicht um einen Artikel, den ich selber anrufen kann. Nein. Es gibt noch keinen Artikel. Sie musste auf ihr... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.96 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.91) - Der Kunde gibt die Ziffern der TAN-Card... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.50 | same | 01:11-01:23 disclosure: Am zwanzig. soll ich die Reservierung bestätigen. Dafür kann es auch jemand anderes, der Interesse hat. Ich will nicht alles verlieren, nur weil wir noch einen neuen Abschnitt ... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D09-K2 | alarm | alarm | no_alert | 0.87/0.05 | broken | 02:39-03:02 documentation: Dann bitte nicht, protokollieren, dass ich den 20'000 zurückzahlen muss. Nehmen das Arley nicht in die Notiz für die Kreditstelle. Ich will, dass Sie nur Eigenmittel sehen u... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe1_D10-K1 | alarm | alarm | no_alert | 0.95/0.00 | broken | 01:32-01:58 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe stellt die ganze Rechnung überhaupt sieht. Können Sie mir z... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | no_alert | 0.95/0.00 | broken | 01:33-01:50 splitting: Ich will 12 000 aufteilen, mit 6000 und nun 6000. So will ich die Kontrolle umgehen und verhindern, dass das Freigabe-Stell die ganze Rechnung überhaupt sieht. Können Sie mir ja... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.81 | same | 00:45-00:47 trade: Es geht um CRM -Systeme. - facts_blind: Fakt: Information noch nicht öffentlich = ja (0.62) - Der Kunde hat den Kaufwunsch von Aktien basierend auf einem Bericht, der ihm von einer ... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.89 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.50 | same | 03:33-03:39 trade: Wegen dieser Nachricht möchte ich nicht für fünftausend Franken Aktien von der Alpes Optik kaufen. - facts_blind: Fakt: Eigener Handelswunsch = ja (0.77) - Die Kunde gibt ihren konk... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C12-K3 | alarm | alarm | no_alert | 0.70/0.00 | broken | 00:10-00:21 documentation: Ja, sie ist zurzeit im Spital und ich ordne mit ihr die Unterlagen, ich will dir ganze Sachen übernehmen, aber die Heimrechnung muss rechtzeitig bezahlt werden. - Kein Alarm... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | no_alert | 0.52/0.00 | broken | 01:57-02:07 documentation: Rob, das mache ich. Mein Problem ist, dass meine Mutter alles in einem Ordner steckt, auch Werbung. Ich will nicht danach die Erinnerung mit der neuen Rechnung verwechseln. ... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 00:10-01:03 disclosure: Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann m... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:11-03:18 disclosure: Wir haben vereinbart, dass ich zuerst mit Ihnen reden und nicht selber entscheiden, welche Rechnung zu einem Strang kommt. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.0... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_7b_facts_l3__both` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_7b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.85 | +0.177 | [+0.046, +0.305] | **real**: qwen25_7b_facts_l3__both better |
| alarm AUC | 0.79 | 0.89 | +0.097 | [-0.020, +0.189] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.78 | +0.128 | [-0.058, +0.330] | no detectable difference |
| alarm_f1 | 0.49 | 0.63 | +0.141 | [-0.270, +0.500] | no detectable difference |
| false_alarm_rate | 86% | 23% | -64pp | [-88pp, -33pp] | **real**: qwen25_7b_facts_l3__both better |
| miss_rate | 15% | 23% | +8pp | [-15pp, +32pp] | no detectable difference |
| accuracy | 38% | 58% | +21pp | [-12pp, +50pp] | no detectable difference |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.77 | +0.280 | [+0.106, +0.450] | **real**: qwen25_7b_facts_l3__both better |

McNemar exact (calls): flag correct only-qwen25_7b 4 vs only-qwen25_7b_facts_l3__both 16, p=0.0118; 3-class only-qwen25_7b 11 vs only-qwen25_7b_facts_l3__both 21, p=0.1102.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.80 | +0.157 | [-0.021, +0.337] | no detectable difference |
| alarm_f1 | 0.17 | 0.17 | -0.007 | [-0.462, +0.429] | no detectable difference |
| false_alarm_rate | 55% | 18% | -36pp | [-67pp, -6pp] | **real**: qwen25_7b_facts_l3__both better |
| miss_rate | 31% | 23% | -8pp | [-27pp, +14pp] | no detectable difference |
| accuracy | 31% | 46% | +15pp | [-8pp, +37pp] | no detectable difference |
| review_recall | 50% | 33% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.79 | +0.220 | [+0.033, +0.396] | **real**: qwen25_7b_facts_l3__both better |

McNemar exact (calls): flag correct only-qwen25_7b 2 vs only-qwen25_7b_facts_l3__both 12, p=0.0129; 3-class only-qwen25_7b 4 vs only-qwen25_7b_facts_l3__both 11, p=0.1185.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_7b_facts_l3__both - qwen25_7b

| metric | qwen25_7b | qwen25_7b_facts_l3__both | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.79 | +0.097 | [-0.100, +0.308] | no detectable difference |
| alarm_f1 | 0.61 | 0.62 | +0.010 | [-0.367, +0.311] | no detectable difference |
| false_alarm_rate | 95% | 14% | -82pp | [-100pp, -59pp] | **real**: qwen25_7b_facts_l3__both better |
| miss_rate | 4% | 27% | +23pp | [+5pp, +44pp] | **real**: qwen25_7b better |
| accuracy | 38% | 62% | +25pp | [-7pp, +52pp] | no detectable difference |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.80 | +0.294 | [+0.136, +0.436] | **real**: qwen25_7b_facts_l3__both better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_7b_facts_l3__both 18, p=0.0227; 3-class only-qwen25_7b 9 vs only-qwen25_7b_facts_l3__both 21, p=0.0428.

Flips (cv, 35 calls):

| call | expected | qwen25_7b | qwen25_7b_facts_l3__both | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/0.98 | fixed | 00:37-00:53 trade: Etwa 8000 Franken. Meine Schwester arbeitet dort in der Finanzabteilung. Sie hat mir gestern gesagt, Quartalszahlen seien viel besser als erwartet. Diese sind noch nicht publiziert.... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben'... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:49-03:32 trade: Diese Unterlagen haben Sie von Ihrer Kollegin persönlich bekommen. Es geht nicht um einen Artikel, den ich selber anrufen kann. Nein. Es gibt noch keinen Artikel. Sie musste auf ihr... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.96 | same | 01:17-01:22 access: Wartet, ich sage Ihnen die TAN-Card. sieben, drei, eins, neun, vier, zwei. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.91) - Der Kunde gibt die Ziffern der TAN-Card... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe1_D09-K1 | alarm | alarm | review | 0.87/0.55 | same | 02:05-02:55 documentation: Das Darlehensamma muss also jetzt richtig drin sein. Das habe ich verstanden. Ich kann das Scher für ein Foto der Vereinbarung noch nachreichen, wenn meine Tante erst am Abe... | llm_judge: Der Kunde möchte, dass die Schuldsituation seiner Tante nicht protokolliert wird, um die Kreditstelle nicht über diese Informationen zu informieren. Dies entspricht dem Wunsch, eine relevan... |
| Stufe1_D09-K2 | alarm | alarm | review | 0.87/0.55 | same | 02:33-02:54 documentation: Ich habe Ihnen darum noch keinen Zeitpunkt für einen Entscheid zu sagen. Dann bitte nicht protokollieren, dass ich die 20.000 Franken zurückzahlen muss. Ich nehme das Zahler... | llm_judge: Die Kunden möchte, dass eine bestehende Rückzahlbare Verpflichtung (20'000 Franken) nicht protokolliert wird, um sie aus der Notiz für die Kreditstelle zu nehmen. Dies entspricht dem Wunsch... |
| Stufe1_D10-K1 | alarm | alarm | review | 0.95/0.48 | same | 01:32-01:48 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | geval: Der Kunde möchte eine einzige Rechnung in mehrere Teilzahlungen aufteilen, um die interne Freigabe zu umgehen. Er erklärt explizit, dass er die Kontrolle umgehen will, indem er die Rechnung in ... |
| Stufe1_D10-K2 | alarm | alarm | review | 0.95/0.32 | same | 01:33-01:49 splitting: Ich will zwölftausend aufteilen mit sechstausend und neunsechstausend. So möchte ich die Kontrolle umgehen und verhindern, dass die Freigabestellung die ganze Rechnung überhaupt... | geval: Der Kunde möchte eine einzige Rechnung in Teilbeträge aufteilen, um die interne Freigabe zu umgehen. Er erklärt dies explizit in S010. |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.25 (Schwelle 0.40 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.25 (Schwelle 0.40 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | review | 0.69/0.12 | same | 08:08-08:25 trade: Der Sparplan soll bleiben, wie er ist. Ich habe den Betrag, den Namen der Aktien und die Quelle zum Wunsch notiert. Ich kann Ihnen in diesem Rückkauf keine Ausführung bestätigen. Ic... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C05-K4 | no_alert | alarm | review | 0.93/0.33 | same | 00:45-00:52 trade: Es geht um CRM-Systeme. Ich stelle nicht Produkte aus meiner Arbeit, aber die Aktien habe ich bis jetzt nie gehabt. - facts_blind: Fakt: Information noch nicht öffentlich = ja (0.95... | geval: Die Kunde erwähnt einen Großauftrag, der am letzten Freitag veröffentlicht wurde, und zeigt einen Link zu einem Bericht. Trotzdem gibt sie an, dass sie den Kaufwunsch noch nicht getroffen hat, ... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.93 | same | 01:09-01:29 trade: Claudia leitet das Projekt bei der Firma. Sie hat mir den unterschriebenen Grossauftrag persönlich gezeigt, weil wir uns privat kennen. Der Inhalt bleibt bis zur Präsentation am Fre... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/0.94 | same | 00:35-00:48 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. Er geht erst morgen an die Mädchen, bis dann das Team ihn nicht weit... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C12-K3 | alarm | alarm | review | 0.70/0.12 | same | 03:29-03:38 disclosure: Auf diesem Konto sind aktuell sechstausendvierhundert Franken verfügbar. Das ist der persönliche Stand Ihrer Mutter heute Morgen. - facts: Fakt: Konkrete Daten einer Drittperso... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Heimrechnung) vor der Kreditstelle verborgen wird. Diese Aussage entspricht dem Misconduct-Definition. |
| Stufe2_C12-K4 | alarm | alarm | review | 0.52/0.47 | same | 00:56-01:03 disclosure: dass sie in diesem Vorgang keine Berechtigung zum Verkaufsverfahren hat. Die familiäre Beziehung allein lernt da nichts. - facts: Fakt: Keine Vollmacht/Berechtigung festgestell... | llm_judge: Die Kunde gibt an, dass ihre Mutter die Heimrechnungen in einem Ordner zusammenlegt, der auch Werbung enthält. Die Kunde möchte, dass diese Informationen nicht bei der Kreditprüfung berücks... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 07:38-08:11 documentation: Die Farbe meine ich auf der aktuellen weissen Version, nicht auf dem alten Blatt. Ja, Sie meinen die violetten Zeilen im aktuellen Entwurf. Sagen Sie mir bitte, was ich mit ... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:23-08:44 documentation: Gut, dann lade ich zuerst den neuen Kaufentwurf und den richtig angeschriebenen Beleg auf. Die alte Version lasse ich separat, damit ich sie nicht wieder verwechseln kann. G... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.12 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.12 ('Zugangsinformation pre... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.12 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 00:10-01:03 disclosure: Ja, sie ist vor zwei Monaten im Ausland. Ich habe ihr angeboten, auf die offenen Rechnungen zu schauen. Ich habe aber noch nie mit ihrer Bank über ihr Konto telefoniert. Dann m... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:11-03:18 disclosure: Wir haben vereinbart, dass ich zuerst mit Ihnen reden und nicht selber entscheiden, welche Rechnung zu einem Strang kommt. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.0... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

## `qwen25_14b_para_l3` vs `qwen25_7b`

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = qwen25_14b_para_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_para_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.68 | 0.88 | +0.199 | [+0.094, +0.292] | **real**: qwen25_14b_para_l3 better |
| alarm AUC | 0.79 | 0.94 | +0.147 | [+0.030, +0.245] | **real**: qwen25_14b_para_l3 better |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_para_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_para_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.66 | 0.81 | +0.152 | [-0.061, +0.363] | no detectable difference |
| alarm_f1 | 0.49 | 0.83 | +0.342 | [+0.136, +0.559] | **real**: qwen25_14b_para_l3 better |
| false_alarm_rate | 86% | 9% | -77pp | [-95pp, -55pp] | **real**: qwen25_14b_para_l3 better |
| miss_rate | 15% | 27% | +12pp | [-13pp, +36pp] | no detectable difference |
| accuracy | 38% | 77% | +40pp | [+12pp, +64pp] | **real**: qwen25_14b_para_l3 better |
| review_recall | 83% | 0% | -83pp | [-100pp, -50pp] | **real**: qwen25_7b better |
| flag_balanced_accuracy | 0.49 | 0.82 | +0.329 | [+0.172, +0.482] | **real**: qwen25_14b_para_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 5 vs only-qwen25_14b_para_l3 19, p=0.0066; 3-class only-qwen25_7b 6 vs only-qwen25_14b_para_l3 25, p=0.0009.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_para_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_para_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.64 | 0.81 | +0.166 | [-0.039, +0.348] | no detectable difference |
| alarm_f1 | 0.17 | 0.57 | +0.398 | [+0.112, +0.700] | **real**: qwen25_14b_para_l3 better |
| false_alarm_rate | 55% | 9% | -45pp | [-73pp, -17pp] | **real**: qwen25_14b_para_l3 better |
| miss_rate | 31% | 27% | -4pp | [-25pp, +21pp] | no detectable difference |
| accuracy | 31% | 62% | +31pp | [+11pp, +50pp] | **real**: qwen25_14b_para_l3 better |
| review_recall | 50% | 33% | -17pp | [-100pp, +50pp] | no detectable difference |
| flag_balanced_accuracy | 0.57 | 0.82 | +0.246 | [+0.053, +0.422] | **real**: qwen25_14b_para_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 3 vs only-qwen25_14b_para_l3 14, p=0.0127; 3-class only-qwen25_7b 2 vs only-qwen25_14b_para_l3 17, p=0.0007.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = qwen25_14b_para_l3 - qwen25_7b

| metric | qwen25_7b | qwen25_14b_para_l3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.69 | 0.81 | +0.114 | [-0.087, +0.316] | no detectable difference |
| alarm_f1 | 0.61 | 0.75 | +0.139 | [+0.011, +0.296] | **real**: qwen25_14b_para_l3 better |
| false_alarm_rate | 95% | 9% | -86pp | [-100pp, -71pp] | **real**: qwen25_14b_para_l3 better |
| miss_rate | 4% | 27% | +23pp | [+4pp, +44pp] | **real**: qwen25_7b better |
| accuracy | 38% | 71% | +33pp | [+8pp, +56pp] | **real**: qwen25_14b_para_l3 better |
| review_recall | 100% | 33% | -67pp | [-100pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.50 | 0.82 | +0.316 | [+0.197, +0.432] | **real**: qwen25_14b_para_l3 better |

McNemar exact (calls): flag correct only-qwen25_7b 6 vs only-qwen25_14b_para_l3 19, p=0.0146; 3-class only-qwen25_7b 6 vs only-qwen25_14b_para_l3 22, p=0.0037.

Flips (cv, 32 calls):

| call | expected | qwen25_7b | qwen25_14b_para_l3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D01-K1 | no_alert | review | no_alert | 0.43/0.00 | fixed | 01:24-01:39 access: Wir brauchen dafür nur die letzten vier Stellen, also nicht meine ganze Kreditkartennummer. Gut, auf der Kreditkarte, die ich beim Label hinterlegt habe, sind die letzten vier, 4, ... | geval: Die Kundin gibt die letzten vier Stellen der Kreditkartennummer vor, was als Zugangsinformation interpretiert werden könnte. Allerdings ist unklar, ob dies ein aktueller Zugangsinformation ist ... |
| Stufe1_D01-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 01:55-02:18 documentation: Und wenn der Laden die Reservation nicht löscht? Ich kann nicht so gerne, wenn etwas eine Woche lang herumhängt, gerade weil ich noch ein Hotel bezahlen muss. Ich notiere de... | llm_judge: Der Kunde wünscht, dass eine bestehende rückzahlbare Verpflichtung nicht protokolliert wird, um sie vor der Kreditstelle zu verborgen. |
| Stufe1_D02-K2 | alarm | no_alert | alarm | 0.68/1.00 | fixed | 00:48-00:53 trade: Diese sind noch nicht publiziert. Die Medienmeldung kommt erst am Freitag. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (1.00) - Frau Aibi sagte, dass ih... | llm_judge: Der Kunde drängt den Verkäufer, eine aktuelle Rückerstattung (Stimmengewirrschung) vor der Kreditstelle zu verbuchen, indem er sagt: 'Ich habe gemeint, solange ich nur für mich kaufe, ist d... |
| Stufe1_D03-K1 | no_alert | review | no_alert | 0.47/0.00 | fixed | 02:05-02:11 documentation: Ich will heute auch gar mitbestellen. Ich möchte den Bericht verstehen, bevor ich im Depot etwas ändere. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20... | llm_judge: Die Kundin erwähnt, dass sie den Bericht verstehen will, bevor sie im Depot etwas ändert, und dass sie heute keine Aufträge teilt, was darauf hindeutet, dass sie möglicherweise Informatione... |
| Stufe1_D04-K2 | alarm | review | alarm | 0.85/1.00 | same | 02:27-02:45 trade: Sie hat am Montag von ihrer Firma gesprochen. Sie hat mir über einen Namen erzählt. Im grösseren Konzern will die Firma auch kaufen. Sie arbeitet in der Finanzabteilung und hat mir ... | llm_judge: Die Kunde erwähnt, dass ihre Kollegin ihr vertrauliche Informationen über eine Übernahme gegeben hat, die noch nicht veröffentlicht ist. Sie plädiert für den Kauf der Aktien, bevor die Meld... |
| Stufe1_D05-K1 | alarm | review | alarm | 0.69/0.82 | same | 01:02-01:12 access: Der Countdown läuft noch. Es sind noch siebenundzwanzig Sekunden. Bitte gehen Sie den Wert selber im vorgesehenen Feld ein. - facts: Fakt: Wert gehört zum laufenden, gültigen Vorga... | llm_judge: Der Kunde sagt den TAN-Code laut vor, der für den laufenden Anmeldevorgang gültig ist. |
| Stufe1_D05-K2 | alarm | alarm | no_alert | 0.70/0.01 | broken | 00:57-01:08 access: Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig. Der Countdown läuft noch, es sind noch 27 Sekunden. - Kein Alarm: höchster Score 0.0... | llm_judge: Die Kundin gibt den Bestätigungscode vor, der noch in der Anmeldung gültig ist: 'Bestätigung, und da stark der neue Bestätigungscode ist für genau die jetzige Anmeldung gültig.' |
| Stufe1_D06-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 02:54-03:07 documentation: Es ist ein kleines Voten-Hilfedokument, darunter steht der Beispiel, abgelaufen, nicht verwendbar, es ist keine Welt aus meinem Zugang, ich habe heute gar keine Anfrage gest... | geval: Der Kunde möchte, dass eine abgelaufene Beispielzahl nicht protokolliert wird, während der Advisor darauf hinweist, dass dies für die Kreditprüfung relevant ist. Dies deutet darauf hin, dass de... |
| Stufe1_D06-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:21-04:21 documentation: durch neues Gerät registrieren und der Bestätigungscode auf dem Musterbild ist 4826001. Das ist die abgelaufene Beispielzahl, wie meine. Ich habe keine aktuellen Codes zum T... | llm_judge: Der Kunde möchte, dass eine relevante Tatsache (die abgelaufene Beispielzahl) vor der Kreditstelle verborgen bleibt, was von dem Advisor bestätigt wird. |
| Stufe1_D08-K1 | no_alert | alarm | no_alert | 0.70/0.00 | fixed | 03:08-03:23 documentation: Bitte nicht protokollieren, dass die April-Ausgabe im März geschehen sei. Die Buchung selbst und der wichtige April-Bericht sollten vollständig bleiben, weil mein falscher P... | llm_judge: Die Kassierin möchte, dass eine falsche Periode in der Übersicht nicht protokolliert wird, um den Vorstand nicht mit dem Alter zu verwechseln. |
| Stufe1_D08-K2 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 00:43-00:55 trade: Richtig, ich will auch gar nicht über ihn persönlich wissen, ich habe das Protokoll der Wahl und das Formulat zur Vollmacht von mir. Der Vorstand hat das letzte Woche eingeheucht, -... | llm_judge: Frau Suter äußert ihren Kaufwunsch, basierend auf Informationen, die ihr von ihrem Vorgänger und dem Vorstand zugeschickt wurden. Diese Informationen sind vertraulich und noch nicht öffentl... |
| Stufe2_C01-K3 | no_alert | review | no_alert | 0.45/0.00 | fixed | 00:38-00:50 access: Ich übernahe die Nummern der vorderseite meiner Karte, die ich online bezahle, mein Name und das Ablaufdatum stehen auch drauf, die Rechnungsreferenz steht auf dem anderen Blatt. -... | llm_judge: Der Kunde nennt die vorderseitigen Nummern seiner Kreditkarte, einschließlich des Ablaufdatums, während er versucht, eine Rechnung zu klären. Obwohl diese Informationen nicht PIN, TAN oder ... |
| Stufe2_C01-K4 | no_alert | review | no_alert | 0.70/0.00 | fixed | 01:57-02:04 access: Hier steht 4242424242424242424242424242424242424242424242424242. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Die Kundin gibt den vollen Wert 42424242424242424242424242424242 vor, was ein aktuelles Zugangsgeheimnis ist. |
| Stufe2_C02-K3 | no_alert | review | no_alert | 0.69/0.00 | fixed | 01:55-02:04 access: Da steht 4242-3242-3232-3232-3232. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15). | llm_judge: Der Kunde gibt den TAN-Code 4242-3242-3232-3232-3232 am Telefon preis. |
| Stufe2_C02-K4 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 00:11-00:21 documentation: Einen Ausdruck des Onlineheimkaufs, ich habe die Rechnung und eine Bestätigung nebeneinander, aber auf der Bestätigung steht keine Überschrift über den langen Zahl. - Kein A... | llm_judge: Der Kunde möchte, dass eine Bestellnummer, die auf der Bestätigung fehlt, nicht protokolliert wird, um die Kreditprüfung zu beeinflussen. |
| Stufe2_C05-K3 | no_alert | alarm | no_alert | 0.69/0.00 | fixed | 07:58-08:10 documentation: Genau wegen diesem Bericht will ich nicht von 6000 Franken Aktien von den CLN Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen, der Sparplan soll bleiben, wie er is... | llm_judge: Die Kunde verlangt, dass ihre rückzahlbare Verpflichtung (6000 Franken Aktien) vor der Kreditprüfung nicht protokolliert wird, indem sie erklärt, dass sie den Kaufentscheid noch nicht getro... |
| Stufe2_C06-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:03-08:12 trade: Genau wegen diesem Bericht möchte ich heute von sechstausend Franken Aktien von den Seerlern-Systemen kaufen. Nehmen Sie den Kaufwunsch bitte entgegen. - facts: Fakt: Eigener Handel... | llm_judge: Die Kundenin erwähnt, dass sie Informationen aus einer unterprivatisierten Quelle hat, die ihr die Firma direkt gezeigt hat, und möchte die CRN-Systeme kaufen, bevor die Information öffentl... |
| Stufe2_C07-K3 | alarm | review | alarm | 0.69/1.00 | same | 00:35-00:43 trade: Meine Cousine ist im Projektteam der Alpesoptik. Sie hat mir gestern den neuen Absatzbericht persönlich gezeigt. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information ... | llm_judge: Die Kundin möchte, dass ihr einmaliger Kauf nicht protokolliert wird, um ihn als eigenständigen Einzelkauf zu behandeln, während sie bereits einen bestehenden Sparauftrag hat. Dies könnte a... |
| Stufe2_C07-K4 | alarm | review | alarm | 0.71/0.50 | same | 03:33-03:39 trade: Wegen dieser Nachricht möchte ich nicht für fünftausend Franken Aktien von der Alpes Optik kaufen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Bühler sagte, da... | llm_judge: Die Kundin erwähnt, dass ihre Cousine ihr einen neuen Absatzbericht persönlich gezeigt hat, der noch nicht veröffentlicht ist und deutlich mehr verkauft worden ist als erwartet. Sie verwend... |
| Stufe2_C08-K3 | no_alert | alarm | no_alert | 0.52/0.00 | fixed | 00:12-00:25 documentation: ich hätte zuerst verstehen, wie ein einzelner Kauf neben dem Sparauftrag erfasst wird, ob ich selber etwas kaufe, habe ich noch nicht entschieden, es geht um ein Formular zu... | llm_judge: Die Kundin möchte, dass ihre Obergrenze von 5000 Franken aus ihrem Sparkonto für die Albisoptik-Aktionen nicht protokolliert wird, um eine separate Frage zu behandeln. Der Advisor akzeptier... |
| Stufe2_C08-K4 | no_alert | alarm | no_alert | 0.54/0.00 | fixed | 03:44-04:18 documentation: bestätige jetzt keine Ausführung. Ich nehme den Kaufwunsch mit den Quellen, die Sie vorher genannt haben, zum Vorgang. Gut, dann ändere ich es selber im Formulat noch mit. I... | llm_judge: Die Kunde möchte, dass eine bestehende rückzahlbare Verpflichtung (Spargelauftrag) vor der Kreditprüfung nicht protokolliert wird. Das wird durch den Bankrat Nadia Fuller angedeutet, als si... |
| Stufe2_C11-K3 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 00:52-01:05 documentation: Auskunftsrecht hinterlegt und geblüfft. In diesem Vorgang haben sie die deutige Berechtigung zum Kontostand von genau diesem Konto. Die konkrete Auskunft ist vom bestätigten... | llm_judge: Die Kunde möchte, dass ihre Mutter die Heimrechnung zeitgerecht bezahlt, und die Bankerin versichert, dass die Konkrete Auskunft vom bestätigten Umfang gedeckt ist, was impliziert, dass ein... |
| Stufe2_C13-K3 | alarm | review | alarm | 0.77/0.50 | same | 07:58-08:03 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.79) - Frau Inh... | llm_judge: Die Kunden möchte, dass der Satz mit der Rückzahlungsverpflichtung nicht protokolliert wird, um die Finanzierungsstelle nicht zu informieren. Dies entspricht dem Wunsch, eine relevante Tats... |
| Stufe2_C13-K4 | alarm | review | alarm | 0.71/0.50 | same | 08:00-08:14 documentation: Ich will, dass die Finanzierungsstelle den Inhalt von genau diesem Satz nicht zu sehen bekommt. Ich nehme Ihren Wunsch auf, zusammen mit denen, die Sie am Anfang über den Sa... | llm_judge: Frau Imhof möchte, dass der violette Satz, der eine bestehende Rückzahlbare Verpflichtung enthält, der Finanzierungsstelle nicht gezeigt wird. Sie sagt: "Ich will, dass die Finanzierungsste... |
| Stufe2_C14-K3 | no_alert | review | no_alert | 0.71/0.00 | fixed | 00:57-01:21 documentation: Wir bedienen mit den violetten Zeilen. Und welche Anlage geht es dort? Wir müssen sonst wissen, ob sie sachenlich wichtig und für den vorgesehenen Empfänger nötig ist. Der v... | llm_judge: Der Kunde möchte, dass der Inhalt eines violetten Satzes, der seine alte Kontaktadresse enthält, vor der Finanzierungsstelle nicht zu sehen ist. Diese Anmerkung ist relevant, da die aktuell... |
| Stufe2_C14-K4 | no_alert | review | no_alert | 0.73/0.00 | fixed | 07:48-08:08 documentation: Ja, sie meilen die violette Zeilen im aktuellen weinen. Sagen Sie mir bitte, was ich mit diesem Satz machen soll. Dann lernt mir ja der Violett, mache ich ja den Satz aus de... | llm_judge: Der Kunde möchte, dass die Finanzierungsstelle den Inhalt eines bestimmten Satzes nicht zu sehen bekommt. Er betont, dass diese Angabe vor der Kreditprüfung verborgen bleiben soll. |
| Stufe3_C17-K3 | review | review | no_alert | 0.47/0.00 | broken | 01:23-01:31 access: Ich weiss nicht, ob der Wert oben oder und dazu gehört. Der Text ist so klein, dass ich das Bild gerade vergrossern muss. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt ... | llm_judge: Die Kundin sagt, dass sie den Text des Codes vorliest, aber unklar ist, ob der Wert noch gültig ist oder zu welchem Vorgang er gehört. |
| Stufe3_C17-K4 | review | review | no_alert | 0.46/0.00 | broken | 00:35-00:49 access: Im Moment schaue ich nur ein Bild an, der oberen Rand ist abgeschnitten und ich kann nicht lesen, ob es noch gültig war, ich habe mich schon etwas neu gestartet, aber ich weiss nic... | llm_judge: Der Kunde sagt, dass er einen Screenshot gemacht hat und versucht, die lesbaren Zahlen für den Vorgang zu verwenden, aber er ist unsicher, ob der Wert noch gültig ist. |
| Stufe3_C18-K3 | review | review | alarm | 0.69/0.50 | same | 03:37-03:51 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungsrechnung liegt? Nein, das kann ich Ihnen erst sagen, wenn die Berechtigung für diese Auskunf... | llm_judge: Die Kunde möchte, dass ihre Schwester nicht über ihre Bankdaten informiert wird, während sie sich um das Haushaltskonto kümmert. Dies ist ein Wunsch, dass eine relevante Tatsache 'nicht pro... |
| Stufe3_C18-K4 | review | no_alert | alarm | 0.54/0.50 | fixed | 03:39-03:45 disclosure: Können Sie mir bis jetzt wenigstens sagen, ob auf Ihrem Konto genug für die Wohnungstechnung liegt? - facts: Fakt: Auskunft über Drittperson verlangt = ja (0.99) - Die Kundin f... | llm_judge: Die Kunde möchte, dass ihre Schwester den Septemberbetrag bereits zum Zahlen erfasst hat, ohne dass dies der Kreditstelle gemeldet wird. Dies ist ein Wunsch, eine relevante Tatsache vor der... |
| Stufe3_C20-K3 | review | review | no_alert | 0.43/0.00 | broken | 01:03-01:25 documentation: Das weiss ich auch nicht. Meine Kollegin hat die Daten so noziert, ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dann ... | geval: Der Kunde möchte die Daten so nennen, wie seine Kollegin es getan hat, ohne zu wissen, ob die Daten korrekt sind oder ob sie für die Kreditprüfung relevant sind. Der Advisor bestätigt, dass die... |
| Stufe3_C20-K4 | review | review | no_alert | 0.43/0.00 | broken | 01:04-01:14 documentation: Das weiss ich auch nicht, meine Kollegin hat die Daten so noziert. Ich kann nicht sagen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. - Kei... | geval: Der Kunde erwähnt, dass seine Kollegin die Daten so 'noziert' hat, ohne zu wissen, ob sie nach der Rechnung gegangen ist oder nur einen eigenen Plan gemacht hat. Dies deutet darauf hin, dass re... |

