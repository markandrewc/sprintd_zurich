# Two readers: pre-registered evaluation (dev)

Pre-registration: research/findings/two_readers_prereg.md. Metrics on out-of-fold CV rows (threshold per fold chosen on the other folds); AUC on the fixed-threshold call scores. 95% CIs: 2000 bootstrap replicates over twin groups. n = 48 calls / 24 dialogues; 6 expected-review calls (1 call = 17 pp of review recall).

| wording | system | flag AUC [CI] | CV flag F1 [CI] | CV FAR [CI] | CV miss [CI] | review recall | 3-class acc [CI] | reviews | CV@FAR20 FAR / recall |
|---|---|---|---|---|---|---|---|---|---|
| perturbed | Qwen alone | 0.83 [0.67, 0.96] | 0.82 [0.68, 0.93] | 14% [0%, 35%] | 23% [4%, 43%] | 0% (0/6) | 73% [57%, 87%] | 1 | 14% / 77% |
| perturbed | Kev alone | 0.81 [0.60, 0.96] | 0.83 [0.63, 0.96] | 5% [0%, 15%] | 27% [7%, 50%] | 0% (0/6) | 65% [44%, 82%] | 9 | 5% / 73% |
| perturbed | R1 labels | 0.86 [0.72, 0.98] | 0.82 [0.70, 0.93] | 18% [0%, 40%] | 19% [4%, 36%] | 50% (3/6) | 62% [44%, 80%] | 16 | 18% / 81% |
| perturbed | R2 facts | 0.84 [0.65, 0.97] | 0.79 [0.62, 0.92] | 14% [0%, 35%] | 27% [5%, 50%] | 0% (0/6) | 73% [57%, 87%] | 1 | 14% / 73% |

## Paired vs Qwen alone on the same wording (B - A on CV rows; bold = CI excludes 0)

| wording | system | d AUC [CI] | d FAR [CI] | d miss [CI] | d review recall | d 3-class acc [CI] | McNemar flag (A only / B only, p) | McNemar label | flips |
|---|---|---|---|---|---|---|---|---|---|
| perturbed | Kev alone | -0.02 [-0.18, +0.09] | -9pp [-32pp, +11pp] | +4pp [-15pp, +25pp] | +0pp | -8pp [-25pp, +6pp] | 4 / 5, p=1.0 | 8 / 4, p=0.3877 | 16 |
| perturbed | R1 labels | +0.03 [-0.02, +0.09] | +5pp [+0pp, +15pp] | -4pp [-12pp, +0pp] | +50pp | -10pp [-29pp, +7pp] | 1 / 1, p=1.0 | 8 / 3, p=0.2266 | 15 |
| perturbed | R2 facts | +0.01 [-0.11, +0.12] | +0pp [+0pp, +0pp] | +4pp [+0pp, +12pp] | +0pp | +0pp [+0pp, +0pp] | 1 / 0, p=1.0 | 0 / 0, p=1.0 | 1 |

## Verdict per pre-registered criterion

### R1 labels: FAIL
- A1: not evaluable
- A2: not evaluable
- A3: not evaluable
- A4 FAIL: para: not available; para2: not available; blind: not available

### R2 facts: FAIL
- A1: not evaluable
- A2: not evaluable
- A3: not evaluable
- A4 FAIL: para: not available; para2: not available; blind: not available

Recommendation by the pre-registered tie-break: none passes - the champion stays.

## Sanity: single readers re-fused from the joined source vs the stored runs

- perturbed Qwen alone vs kev_perturbed/perturbed: fixed: 0/48 calls differ; cv: 0/48 calls differ
- perturbed Kev alone vs kev_perturbed/kev_facts: fixed: 0/48 calls differ; cv: 0/48 calls differ
