# Dual-reader facts: DEV evaluation (2026-10-10T16:38:28)

Profile `dual-facts`, table `config/policy_table.yaml`, 48 dev calls (dev folds only, holdout excluded), fixed threshold 0.55, 95% bootstrap CIs over twin groups (2000x, seed 13). Pure re-fusion of stored answers, no model ran. Default = pre-registered (Qwen three-way, Kev band [0.3, 0.7], Einigkeit); champion v3 = Qwen alone (combination only_a).

## Fixed threshold

| setting | n (units) | flagged / alarm / review | flag AUC | FAR | miss | 3-class acc | review recall |
|---|---|---|---|---|---|---|---|
| default (agree, Kev 0.3-0.7) | 48 (18) | 26 / 11 / 15 | 0.92 [0.82, 1.00] | 14% [0%, 35%] | 12% [0%, 29%] | 75% [59%, 92%] | 100% [100%, 100%] |
| champion v3 (only_a) | 48 (18) | 27 / 15 / 12 | 0.92 [0.80, 1.00] | 14% [0%, 35%] | 8% [0%, 25%] | 83% [68%, 100%] | 100% [100%, 100%] |

## CV (out-of-fold max-F1 threshold over the 4 dev folds)

| setting | n (units) | flagged / alarm / review | flag AUC | FAR | miss | 3-class acc | review recall |
|---|---|---|---|---|---|---|---|
| default (agree, Kev 0.3-0.7) | 48 (18) | 26 / 21 / 5 | 0.92 [0.82, 1.00] | 14% [0%, 35%] | 12% [0%, 29%] | 73% [58%, 88%] | 33% [0%, 100%] |
| champion v3 (only_a) | 48 (18) | 27 / 15 / 12 | 0.92 [0.80, 1.00] | 14% [0%, 35%] | 8% [0%, 25%] | 83% [68%, 100%] | 100% [100%, 100%] |

CV thresholds per fold: default 0: 0.20, 1: 0.65, 2: 0.20, 3: 0.20; champion v3 0: 0.65, 1: 0.65, 2: 0.65, 3: 0.70.

## Paired: default − champion v3 (same calls, paired bootstrap over twin groups; * = CI excludes 0)

| comparison (variant − champion v3) | calls changed | Δ flag AUC | Δ FAR | Δ miss | Δ 3-class acc | Δ review recall | McNemar flag p |
|---|---|---|---|---|---|---|---|
| fixed threshold | 4 | +0.00 [-0.06, +0.08] | +0 pp [+0, +0] | +4 pp [+0, +12] | -8 pp [-20, +0] | +0 pp [+0, +0] | 1.0 (1↔0) |
| CV | 14 | +0.00 [-0.06, +0.08] | +0 pp [+0, +0] | +4 pp [+0, +12] | -10 pp [-31, +6] | -67 pp [-100, +0] | 1.0 (1↔0) |

Calls whose label changes (fixed threshold): Stufe1_D05-K1 (alarm: alarm→review), Stufe1_D05-K2 (alarm: alarm→review), Stufe2_C07-K3 (alarm: alarm→review), Stufe2_C07-K4 (alarm: alarm→no_alert).

Calls whose label changes (CV): Stufe1_D05-K1 (alarm: alarm→review), Stufe1_D05-K2 (alarm: alarm→review), Stufe2_C07-K3 (alarm: alarm→review), Stufe2_C07-K4 (alarm: alarm→no_alert), Stufe2_C11-K3 (no_alert: review→alarm), Stufe2_C11-K4 (no_alert: review→alarm), Stufe2_C12-K3 (alarm: review→alarm), Stufe2_C13-K3 (alarm: review→alarm), Stufe2_C13-K4 (alarm: review→alarm), Stufe2_C14-K3 (no_alert: review→alarm), Stufe3_C18-K3 (review: review→alarm), Stufe3_C18-K4 (review: review→alarm), Stufe3_C20-K3 (review: review→alarm), Stufe3_C20-K4 (review: review→alarm).

## Grid (DEV ONLY; Qwen three-way; for the officer UI, nothing is selected from it)

| setting | flagged / alarm / review | FAR | miss | 3-class acc | review recall | flag AUC | CV FAR | CV miss | CV acc | calls changed vs v3 |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| only_a/kev0.2-0.8 | 27 / 15 / 12 | 14% | 8% | 83% | 100% | 0.92 | 14% | 8% | 83% | 0 | (= v3) |
| only_b/kev0.2-0.8 | 19 / 8 / 11 | 14% | 38% | 65% | 67% | 0.84 | 14% | 15% | 65% | 15 |  |
| agree/kev0.2-0.8 | 26 / 11 / 15 | 14% | 12% | 75% | 100% | 0.92 | 14% | 12% | 73% | 4 |  |
| a_checked/kev0.2-0.8 | 27 / 13 / 14 | 14% | 8% | 79% | 100% | 0.94 | 14% | 8% | 79% | 2 |  |
| only_a/kev0.3-0.7 | 27 / 15 / 12 | 14% | 8% | 83% | 100% | 0.92 | 14% | 8% | 83% | 0 | **champion v3** |
| only_b/kev0.3-0.7 | 21 / 9 / 12 | 14% | 31% | 67% | 67% | 0.86 | 14% | 12% | 65% | 17 |  |
| agree/kev0.3-0.7 | 26 / 11 / 15 | 14% | 12% | 75% | 100% | 0.92 | 14% | 12% | 73% | 4 | **default** |
| a_checked/kev0.3-0.7 | 27 / 13 / 14 | 14% | 8% | 79% | 100% | 0.94 | 14% | 8% | 79% | 2 |  |
| only_a/kev0.4-0.6 | 27 / 15 / 12 | 14% | 8% | 83% | 100% | 0.92 | 14% | 8% | 83% | 0 | (= v3) |
| only_b/kev0.4-0.6 | 18 / 10 / 8 | 9% | 38% | 67% | 33% | 0.84 | 9% | 19% | 67% | 19 |  |
| agree/kev0.4-0.6 | 27 / 12 / 15 | 14% | 8% | 77% | 100% | 0.93 | 14% | 8% | 77% | 3 |  |
| a_checked/kev0.4-0.6 | 27 / 13 / 14 | 14% | 8% | 79% | 100% | 0.94 | 14% | 8% | 79% | 2 |  |

only_a ignores Kev, so its three rows are the champion v3 regardless of the band.

## Reader agreement (dev calls, stored answers of the table's facts)

| set / Kev band | fact answers (both) | Qwen ja / nein / unklar | Kev ja / nein / unklar | readers differ | ja vs nein |
|---|---|---|---|---|---|
| dev, Kev 0.2-0.8 | 1344 (1344) | 94 (7%) / 428 (32%) / 822 (61%) | 99 (7%) / 911 (68%) / 334 (25%) | 649 (48%) | 19 (1%) |
| dev, Kev 0.3-0.7 | 1344 (1344) | 94 (7%) / 428 (32%) / 822 (61%) | 115 (9%) / 1028 (76%) / 201 (15%) | 738 (55%) | 21 (2%) |
| dev, Kev 0.4-0.6 | 1344 (1344) | 94 (7%) / 428 (32%) / 822 (61%) | 147 (11%) / 1110 (83%) / 87 (6%) | 806 (60%) | 35 (3%) |

## Sanity

only_a vs rule `a` (fixed threshold): 0 of 48 calls differ in label (max |score diff| 0.0, unmatched calls 0).
