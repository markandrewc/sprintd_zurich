# Experiment `champion14_holdout`

HOLDOUT run of config/recommended-14b.yaml (logged; run once)

RQ: RQ6 · base profile `recommended-14b` · split **holdout** · baseline `champion14` · commit f0b67b02fc (dirty) · 2026-10-10T05:00:56+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

> **HOLDOUT run**: logged in runs/holdout_log.jsonl. Do not tune on these numbers.

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 12 calls** (prevalence of alarm|review 50%): flag-all = flag F1 0.67, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 33%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 50%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.67 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| champion14 | 0.58 [0.06, 1.00] | 0.67 [0.12, 1.00] | 6/6 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion14 | 12 | 0.40 [0.00, 0.67] | 50% | 33% | 33% [0%, 100%] | 67% [50%, 100%] | 0.00 | 0% | 33% | 0.50 [0.12, 0.75] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| champion14 | 0.55 | 0.35 | - | 19.2 | asr 7.2, diarize 7.0, checks 4.9 | 4.9 | 20.4 | 0 | 0 | f0b67b02fc |

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| champion14 | 0.67 / - / 50% | 0.40 / 33% / 50% | 0.00 / - / 100% | 0.67 / 33% / 33% | 0.00 / 33% / 100% |

