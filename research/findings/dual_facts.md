# Dual-reader facts: Qwen + Kev on every fact vs Qwen alone (2026-10-10, pre-registered)

Pre-registration: research/findings/dual_facts_prereg.md (written before any dual-reader result). Evidence:
research/evidence/dual_facts_dev.md/.json, dual_facts_grid.json (dev grid + UI strings), dual_facts_test50.md/.json.
The test50 look is logged in research/findings/test50_prereg.md (one look, 2026-10-10 16:38).

## Setup

- **Readers.** Qwen2.5-7B (check `facts`, p(ja / nein / unklar)) and Kev-4B (check `facts_kev`, p(ja)) each answered
  every fact of the active policy table (v3, `config/policy_table.yaml`, 28 facts per call). Stored results:
  runs/dual-facts/dual-facts (case set, 60 calls) and runs/test50/dual-facts/dual-facts-test50 (100 calls).
- **Pure re-fusion.** No model ran for this evaluation: each fact policy recombines the stored answers
  (`fact_policy.combined_checks`), then the profile's fusion decides (`two_readers`, rule `policy`). Same rules,
  same weights (keywords 0.15, patterns 0.10, facts 1.0), same review band.
- **Default (pre-registered, not tuned):** Qwen three-way, Kev band [0.3, 0.7], combination «Einigkeit» (agree:
  both ja → ja, both nein → nein, else unklar → the review rules fire).
- **Champion v3:** Qwen alone on the same table = combination `only_a`. Sanity: `only_a` gives the same label
  as the fusion's rule `a` (reader A's stored result) on **0 of 48** dev calls and **0 of 100** test50 calls
  differ (max |score diff| 0.0).
- **Sets, never pooled.** Dev = the 48 calls of the 4 locked dev folds (24 dialogues, 18 twin-group units; holdout
  not touched). test50 = the external set (100 calls, 50 dialogues, 32 twin-group units from its dataset.yaml),
  fixed threshold, default vs v3 only, one look.
- **Statistics.** 95% percentile bootstrap CIs (2000x, seed 13) resampling twin groups (clean + noisy and twins
  together); paired deltas = default − champion v3 on the same calls with the same resamples; `*` = CI excludes 0.
  McNemar counts are per call (clean + noisy count twice), read next to the bootstrap, not instead of it.
  Fixed threshold 0.55; CV = out-of-fold max-F1 threshold over the 4 dev folds.

## Dev (48 calls: 20 alarm, 6 review, 22 no_alert)

Fixed threshold 0.55:

| setting | flagged / alarm / review | flag AUC | FAR | miss | 3-class acc | review recall |
|---|---|---|---|---|---|---|
| default (agree, Kev 0.3-0.7) | 26 / 11 / 15 | 0.92 [0.82, 1.00] | 14% [0%, 35%] | 12% [0%, 29%] | 75% [59%, 92%] | 100% [100%, 100%] |
| champion v3 (only_a) | 27 / 15 / 12 | 0.92 [0.80, 1.00] | 14% [0%, 35%] | 8% [0%, 25%] | 83% [68%, 100%] | 100% [100%, 100%] |

CV (out-of-fold threshold; default folds chose 0.20 / 0.65 / 0.20 / 0.20, v3 0.65 / 0.65 / 0.65 / 0.70):

| setting | flagged / alarm / review | flag AUC | FAR | miss | 3-class acc | review recall |
|---|---|---|---|---|---|---|
| default (agree, Kev 0.3-0.7) | 26 / 21 / 5 | 0.92 [0.82, 1.00] | 14% [0%, 35%] | 12% [0%, 29%] | 73% [58%, 88%] | 33% [0%, 100%] |
| champion v3 (only_a) | 27 / 15 / 12 | 0.92 [0.80, 1.00] | 14% [0%, 35%] | 8% [0%, 25%] | 83% [68%, 100%] | 100% [100%, 100%] |

Paired, default − champion v3:

| | calls changed | Δ flag AUC | Δ FAR | Δ miss | Δ 3-class acc | Δ review recall | McNemar flag (v3-only ↔ default-only right) |
|---|---|---|---|---|---|---|---|
| fixed | 4 | +0.00 [-0.06, +0.08] | +0 pp [+0, +0] | +4 pp [+0, +12] | -8 pp [-20, +0] | +0 pp [+0, +0] | 1 ↔ 0, p = 1.0 |
| CV | 14 | +0.00 [-0.06, +0.08] | +0 pp [+0, +0] | +4 pp [+0, +12] | -10 pp [-31, +6] | -67 pp [-100, +0] | 1 ↔ 0, p = 1.0 |

Fixed-threshold changes: D05 K1/K2 and C07-K3 alarm → review, C07-K4 alarm → no_alert (one more miss). Under CV
the default's score scale moves: Einigkeit pushes true alarms into the review band, so the max-F1 tie-break
(alarm-F1) picks 0.20 in three folds, which turns the true reviews (C18, C20) and some harmless calls into alarms.
The flag decisions (FAR, miss) do not change; only alarm vs review does.

## test50 (one look; 100 calls: 34 alarm, 12 review, 54 no_alert; fixed threshold 0.55)

| setting | flagged / alarm / review | flag AUC | FAR | miss | 3-class acc | review recall |
|---|---|---|---|---|---|---|
| default (agree, Kev 0.3-0.7) | 50 / 21 / 29 | 0.88 [0.79, 0.95] | 26% [11%, 43%] (14/54) | 22% [7%, 40%] (10/46) | 68% [55%, 79%] | 75% [50%, 100%] |
| champion v3 (only_a) | 59 / 30 / 29 | 0.83 [0.72, 0.92] | 35% [18%, 53%] (19/54) | 13% [0%, 29%] (6/46) | 64% [50%, 77%] | 75% [50%, 100%] |

Paired, default − champion v3: 13 calls change label; Δ flag AUC +0.04 [-0.00, +0.11], Δ FAR -9 pp [-21, +0],
Δ miss +9 pp [+0, +20], Δ 3-class acc +4 pp [+0, +10], Δ review recall +0 pp [+0, +0]; McNemar flag 4 ↔ 5
(p = 1.0). No CI excludes 0. The changed flags: 5 false alarms removed (access-02-A-K2, disclosure-03-A K1/K2,
disclosure-trap K1/K2) against 4 new misses (access-02-B-K2, access-review-K1, disclosure-03-B K1/K2); 4 more
harmless calls move from alarm to review (documentation-02-A, documentation-trap).

## Dev grid (DEV ONLY, Qwen three-way, fixed threshold 0.55; for the officer UI, nothing selected from it)

| setting | flagged / alarm / review | FAR | miss | 3-class acc | review recall | flag AUC | CV acc | calls changed vs v3 |
|---|---|---|---|---|---|---|---|---|
| only_a (any Kev band) = **champion v3** | 27 / 15 / 12 | 14% | 8% | 83% | 100% | 0.92 | 83% | 0 |
| only_b / Kev 0.2-0.8 | 19 / 8 / 11 | 14% | 38% | 65% | 67% | 0.84 | 65% | 15 |
| only_b / Kev 0.3-0.7 | 21 / 9 / 12 | 14% | 31% | 67% | 67% | 0.86 | 65% | 17 |
| only_b / Kev 0.4-0.6 | 18 / 10 / 8 | 9% | 38% | 67% | 33% | 0.84 | 67% | 19 |
| agree / Kev 0.2-0.8 | 26 / 11 / 15 | 14% | 12% | 75% | 100% | 0.92 | 73% | 4 |
| agree / Kev 0.3-0.7 = **default** | 26 / 11 / 15 | 14% | 12% | 75% | 100% | 0.92 | 73% | 4 |
| agree / Kev 0.4-0.6 | 27 / 12 / 15 | 14% | 8% | 77% | 100% | 0.93 | 77% | 3 |
| a_checked / Kev 0.2-0.8, 0.3-0.7, 0.4-0.6 (identical) | 27 / 13 / 14 | 14% | 8% | 79% | 100% | 0.94 | 79% | 2 |

CIs per setting are in dual_facts_grid.json (`ci`); at 48 calls / 18 units they are wide (miss e.g. [0%, 25%]
for v3, FAR [0%, 35%] for nearly all settings, accuracy about ±15 pp), so the grid shows directions, not winners.
The one clear signal: Kev alone (only_b) misses about 4x as many cases as Qwen on dev (31-38% vs 8%; its miss CI
[10%, 55%] at band 0.3-0.7 does not overlap v3's point estimate, but no paired test was pre-registered for it).

## Reader agreement (stored answers of the table's facts, per set)

| set / Kev band | fact answers | Qwen ja / nein / unklar | Kev ja / nein / unklar | readers differ | hard ja vs nein |
|---|---|---|---|---|---|
| dev, Kev 0.2-0.8 | 1344 | 7% / 32% / 61% | 7% / 68% / 25% | 48% | 19 (1%) |
| dev, Kev 0.3-0.7 | 1344 | 7% / 32% / 61% | 9% / 76% / 15% | 55% | 21 (2%) |
| dev, Kev 0.4-0.6 | 1344 | 7% / 32% / 61% | 11% / 83% / 6% | 60% | 35 (3%) |
| test50, Kev 0.3-0.7 | 2800 | 7% / 46% / 48% | 9% / 85% / 6% | 49% | 42 (2%) |

The readers rarely contradict each other outright (1-3% ja vs nein). Most disagreement is Qwen «unklar» against
Kev «nein»: Qwen leaves about half of all facts open, Kev almost never does. Under Einigkeit every such fact
stays unklar, which is exactly where the review rules fire.

## Verdict (no spin)

- **No evidence of a difference** between the pre-registered default and champion v3 on either set: every paired
  CI includes 0, on dev (48 calls, 24 dialogues) and on test50 (100 calls, 50 dialogues). With 18 and 32
  resampling units, differences of 5-10 pp are inside the noise.
- **Point estimates point in opposite directions on the two sets.** Dev: the default costs one more miss
  (C07-K4) and 4 alarms become reviews, no false alarm saved (3-class acc -8 pp [-20, +0]). test50: the default
  saves 5 false alarms and costs 4 misses (FAR -9 pp [-21, +0], miss +9 pp [+0, +20]), AUC +0.04 [-0.00, +0.11].
- **What the default costs / buys.** It trades alarms for reviews and false alarms for misses: fewer alarms
  (dev 11 vs 15, test50 21 vs 30), more reviews on dev (15 vs 12), the same on test50 (29 vs 29). It does not raise
  review recall (equal on both sets). Under CV on dev, its shifted score scale makes the threshold choice unstable
  (0.20 in 3 of 4 folds) and review recall falls to 33% [0%, 100%].
- **Recommendation.** Nothing here justifies replacing champion v3; nothing here rules the default out either.
  For a compliance tool where a miss costs more than a review, Qwen alone (only_a) or «Qwen, Kev als Kontrolle»
  (a_checked: same misses as v3 on dev, two alarms become reviews) are the defensible settings; this is a team
  decision, and test50 must not be used to choose among grid settings (only default and v3 were looked at).

## Für die Oberfläche

Dev-Zahlen (48 Anrufe, Schwelle 0.55); gleiche Texte in research/evidence/dual_facts_grid.json unter `ui_text`.
Kombination (bei Kev-Band 0.3-0.7):

- **Nur Qwen** (only_a): Nur Qwen entscheidet (= Champion v3), Kev wird nur angezeigt. Dev (48 Anrufe): 27 markiert (15 Alarm, 12 Prüfen), FAR 14 %, Miss 8 %.
- **Nur Kev** (only_b): Nur Kev entscheidet, Qwen wird nur angezeigt. Dev (48 Anrufe): 21 markiert (9 Alarm, 12 Prüfen), FAR 14 %, Miss 31 %.
- **Einigkeit** (agree): Einigkeit: zählt nur, wenn beide gleich antworten, sonst «unklar» → Prüfen. Dev (48 Anrufe): 26 markiert (11 Alarm, 15 Prüfen), FAR 14 %, Miss 12 %.
- **Qwen, Kev als Kontrolle** (a_checked): Qwen entscheidet; sagt Kev klar das Gegenteil, wird es «unklar» → Prüfen. Dev (48 Anrufe): 27 markiert (13 Alarm, 14 Prüfen), FAR 14 %, Miss 8 %.

Kev-Band (bei Einigkeit):

- **0.2-0.8**: Kev muss sehr sicher sein (ja ab 80 %, nein bis 20 %), sonst «unklar». Dev (48 Anrufe): 26 markiert (11 Alarm, 15 Prüfen), FAR 14 %, Miss 12 %.
- **0.3-0.7**: Kev muss recht sicher sein (ja ab 70 %, nein bis 30 %), sonst «unklar» (Standard). Dev (48 Anrufe): 26 markiert (11 Alarm, 15 Prüfen), FAR 14 %, Miss 12 %.
- **0.4-0.6**: Kev darf knapp entscheiden (ja ab 60 %, nein bis 40 %), seltener «unklar». Dev (48 Anrufe): 27 markiert (12 Alarm, 15 Prüfen), FAR 14 %, Miss 8 %.

## Reproduce

```bash
uv run callguard dualfacts eval --set dev                    # dev report + grid (no model runs, ~30 s)
uv run callguard dualfacts eval --set test50 --test50-look   # the one look (refuses if the result exists)
uv run pytest -q tests/test_dual_eval.py tests/test_fact_policy.py tests/test_two_readers.py
```
