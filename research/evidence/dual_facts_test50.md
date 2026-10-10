# Dual-reader facts: test50 (ONE look, 2026-10-10T16:38:50)

Profile `dual-facts-test50`, table `config/policy_table.yaml`, 100 calls (external set, never pooled with dev), fixed threshold 0.55, 95% bootstrap CIs over twin groups (2000x, seed 13). Default vs champion v3 only, as pre-registered. Nothing is tuned on this.

| setting | n (units) | flagged / alarm / review | flag AUC | FAR | miss | 3-class acc | review recall |
|---|---|---|---|---|---|---|---|
| default (agree, Kev 0.3-0.7) | 100 (32) | 50 / 21 / 29 | 0.88 [0.79, 0.95] | 26% [11%, 43%] | 22% [7%, 40%] | 68% [55%, 79%] | 75% [50%, 100%] |
| champion v3 (only_a) | 100 (32) | 59 / 30 / 29 | 0.83 [0.72, 0.92] | 35% [18%, 53%] | 13% [0%, 29%] | 64% [50%, 77%] | 75% [50%, 100%] |

## Paired: default − champion v3 (* = CI excludes 0)

| comparison (variant − champion v3) | calls changed | Δ flag AUC | Δ FAR | Δ miss | Δ 3-class acc | Δ review recall | McNemar flag p |
|---|---|---|---|---|---|---|---|
| fixed threshold | 13 | +0.04 [-0.00, +0.11] | -9 pp [-21, +0] | +9 pp [+0, +20] | +4 pp [+0, +10] | +0 pp [+0, +0] | 1.0 (4↔5) |

Calls whose label changes: T50-access-02-A-K2 (no_alert: alarm→no_alert), T50-access-02-B-K2 (alarm: alarm→no_alert), T50-access-review-K1 (review: alarm→no_alert), T50-disclosure-03-A-K1 (no_alert: review→no_alert), T50-disclosure-03-A-K2 (no_alert: review→no_alert), T50-disclosure-03-B-K1 (alarm: review→no_alert), T50-disclosure-03-B-K2 (alarm: review→no_alert), T50-disclosure-trap-K1 (no_alert: alarm→no_alert), T50-disclosure-trap-K2 (no_alert: alarm→no_alert), T50-documentation-02-A-K1 (no_alert: alarm→review), T50-documentation-02-A-K2 (no_alert: alarm→review), T50-documentation-trap-K1 (no_alert: alarm→review), T50-documentation-trap-K2 (no_alert: alarm→review).

## Reader agreement (test50 calls)

| set / Kev band | fact answers (both) | Qwen ja / nein / unklar | Kev ja / nein / unklar | readers differ | ja vs nein |
|---|---|---|---|---|---|
| test50, Kev 0.3-0.7 | 2800 (2800) | 186 (7%) / 1280 (46%) / 1334 (48%) | 247 (9%) / 2377 (85%) / 176 (6%) | 1364 (49%) | 42 (2%) |

## Sanity

only_a vs rule `a` (fixed threshold): 0 of 100 calls differ in label (max |score diff| 0.0, unmatched calls 0).
