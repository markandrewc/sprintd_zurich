# Experiment `holdout_v1`

v1 baseline on the holdout (reference point for the champion's holdout run)

RQ: RQ4, RQ5 · base profile `gpu-12gb` · split **holdout** · baseline `v1` · commit 795bb55852 (dirty) · 2026-10-10T04:10:50+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

> **HOLDOUT run**: logged in runs/holdout_log.jsonl. Do not tune on these numbers.

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 12 calls** (prevalence of alarm|review 50%): flag-all = flag F1 0.67, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 33%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 50%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.67 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| v1 | 0.61 [0.50, 0.90] | 0.69 [0.50, 1.00] | 6/6 | **DEGRADED** |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 12 | 0.67 [0.25, 1.00] | 50% | 100% | 100% [100%, 100%] | 0% [0%, 0%] | 0.00 | 100% | 17% | 0.50 [0.50, 0.50] | **DEGRADED** |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 0.55 | 0.80 | - | 43.1 | asr 13.1, diarize 12.5, checks 17.6 | 16.4 | 9.6 | 0 | 1 (llm_judge 1x) | 795bb55852 |

> **DEGRADED** variants had failed checks or failed calls: their numbers measure the remaining checks only (failed calls count as review). Fix and rerun before concluding.

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| v1 | 1.00 / - / 0% | 0.40 / 100% / 0% | 1.00 / - / 0% | 0.67 / 100% / 0% | 0.67 / 100% / 0% |

