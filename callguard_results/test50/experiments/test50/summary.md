# Experiment `test50`

External held-out test50 (FHNW TTS, 8 dialects) - fixed candidate list, one run each

RQ: RQ10 · base profile `recommended-test50` · split **external** · baseline `champion` · commit 98bd55751a · 2026-10-10T15:33:28+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 100 calls** (prevalence of alarm|review 46%): flag-all = flag F1 0.63, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 34%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 54%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.63 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| champion | 0.80 [0.68, 0.90] | 0.80 [0.65, 0.92] | 46/54 |  |
| champion_v3 | 0.83 [0.72, 0.92] | 0.81 [0.67, 0.92] | 46/54 |  |
| facts_only | 0.78 [0.64, 0.89] | 0.81 [0.67, 0.92] | 46/54 | re-fusion of champion |
| qwen_general | 0.70 [0.59, 0.81] | 0.64 [0.51, 0.78] | 46/54 |  |
| kev_facts | 0.85 [0.74, 0.94] | 0.85 [0.73, 0.94] | 46/54 |  |
| kev_general | 0.75 [0.65, 0.84] | 0.72 [0.59, 0.84] | 46/54 |  |
| q38q6_facts | 0.87 [0.76, 0.96] | 0.90 [0.78, 0.98] | 46/54 |  |
| q38q6_general | 0.83 [0.72, 0.92] | 0.81 [0.67, 0.93] | 46/54 |  |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 100 | 0.70 [0.59, 0.80] | 63% | 78% | 39% [22%, 57%] | 22% [6%, 39%] | 0.65 | 33% | 61% | 0.70 [0.58, 0.80] |  |
| champion_v3 | 100 | 0.75 [0.64, 0.85] | 66% | 87% | 39% [22%, 57%] | 13% [0%, 29%] | 0.65 | 67% | 65% | 0.74 [0.63, 0.84] |  |
| facts_only | 100 | 0.71 [0.59, 0.80] | 64% | 78% | 37% [20%, 55%] | 22% [6%, 39%] | 0.63 | 0% | 62% | 0.71 [0.59, 0.81] | re-fusion of champion |
| qwen_general | 100 | 0.66 [0.53, 0.77] | 61% | 72% | 39% [22%, 58%] | 28% [10%, 48%] | 0.53 | 0% | 55% | 0.66 [0.56, 0.77] |  |
| kev_facts | 100 | 0.67 [0.51, 0.81] | 72% | 63% | 20% [4%, 37%] | 37% [18%, 57%] | 0.53 | 0% | 59% | 0.71 [0.59, 0.83] |  |
| kev_general | 100 | 0.70 [0.61, 0.79] | 58% | 89% | 56% [38%, 74%] | 11% [0%, 24%] | 0.55 | 25% | 51% | 0.67 [0.59, 0.75] |  |
| q38q6_facts | 100 | 0.76 [0.62, 0.88] | 84% | 70% | 11% [0%, 24%] | 30% [13%, 50%] | 0.76 | 17% | 74% | 0.79 [0.69, 0.89] |  |
| q38q6_general | 100 | 0.73 [0.62, 0.83] | 66% | 83% | 37% [20%, 56%] | 17% [4%, 33%] | 0.62 | 0% | 62% | 0.73 [0.63, 0.83] |  |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 100 | 0.68 [0.55, 0.78] | 65% | 72% | 33% [18%, 50%] | 28% [12%, 46%] | 0.30 | 50% | 48% | 0.69 [0.58, 0.79] |  |
| champion_v3 | 100 | 0.73 [0.62, 0.83] | 67% | 80% | 33% [18%, 50%] | 20% [6%, 36%] | 0.30 | 83% | 52% | 0.74 [0.63, 0.83] |  |
| facts_only | 100 | 0.69 [0.56, 0.80] | 65% | 74% | 33% [18%, 50%] | 26% [10%, 45%] | 0.30 | 50% | 48% | 0.70 [0.58, 0.81] | re-fusion of champion |
| qwen_general | 100 | 0.59 [0.43, 0.72] | 62% | 57% | 30% [15%, 48%] | 43% [24%, 64%] | 0.26 | 42% | 49% | 0.63 [0.54, 0.74] |  |
| kev_facts | 100 | 0.74 [0.56, 0.86] | 78% | 70% | 17% [4%, 33%] | 30% [14%, 50%] | 0.53 | 8% | 62% | 0.76 [0.64, 0.87] |  |
| kev_general | 100 | 0.52 [0.34, 0.67] | 70% | 41% | 15% [4%, 30%] | 59% [39%, 77%] | 0.48 | 0% | 59% | 0.63 [0.54, 0.72] |  |
| q38q6_facts | 100 | 0.78 [0.63, 0.89] | 85% | 72% | 11% [0%, 24%] | 28% [11%, 48%] | 0.76 | 17% | 74% | 0.80 [0.69, 0.90] |  |
| q38q6_general | 100 | 0.75 [0.62, 0.85] | 79% | 72% | 17% [4%, 33%] | 28% [11%, 46%] | 0.66 | 8% | 70% | 0.78 [0.67, 0.87] |  |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| champion | 31% (!) | 0/5 | 33% | **no** | - |
| champion_v3 | 31% (!) | 0/5 | 33% | **no** | - |
| facts_only | 31% (!) | 0/5 | 33% | **no** | - |
| qwen_general | 26% (!) | 0/5 | 30% | **no** | - |
| kev_facts | 11% | 5/5 | 17% | yes | - |
| kev_general | 7% | 5/5 | 15% | yes | - |
| q38q6_facts | 6% | 5/5 | 11% | yes | - |
| q38q6_general | 15% | 4/5 | 17% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| champion | 100 | 0.71 [0.60, 0.81] | 65% | 78% | 35% [18%, 53%] | 22% [6%, 39%] | 0.62 | 42% | 60% | 0.72 [0.60, 0.82] |  |
| champion_v3 | 100 | 0.76 [0.65, 0.86] | 68% | 87% | 35% [18%, 53%] | 13% [0%, 29%] | 0.62 | 75% | 64% | 0.76 [0.65, 0.86] |  |
| facts_only | 100 | 0.71 [0.60, 0.81] | 65% | 78% | 35% [18%, 53%] | 22% [6%, 39%] | 0.62 | 42% | 60% | 0.72 [0.60, 0.82] | re-fusion of champion |
| qwen_general | 100 | 0.65 [0.51, 0.78] | 65% | 65% | 30% [15%, 48%] | 35% [15%, 56%] | 0.49 | 8% | 58% | 0.68 [0.58, 0.78] |  |
| kev_facts | 100 | 0.65 [0.46, 0.80] | 81% | 54% | 11% [0%, 25%] | 46% [26%, 66%] | 0.51 | 0% | 61% | 0.72 [0.60, 0.82] |  |
| kev_general | 100 | 0.55 [0.39, 0.68] | 62% | 50% | 26% [11%, 43%] | 50% [31%, 69%] | 0.52 | 17% | 58% | 0.62 [0.52, 0.72] |  |
| q38q6_facts | 100 | 0.72 [0.55, 0.86] | 88% | 61% | 7% [0%, 19%] | 39% [20%, 59%] | 0.72 | 17% | 73% | 0.77 [0.66, 0.87] |  |
| q38q6_general | 100 | 0.72 [0.58, 0.83] | 72% | 72% | 24% [10%, 42%] | 28% [11%, 47%] | 0.69 | 0% | 68% | 0.74 [0.62, 0.85] |  |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| champion | 0.55 | 0.20 | 0.20, 0.85, 0.20, 0.20, 0.20 (FAR20: 0.95!, 1.00!, 1.00!, 1.00!, 1.00!) | 16.1 | asr 8.1, diarize 5.5, checks 2.5 | 2.5 | 21.6 | 0 | 0 | 4d318d2b77 |
| champion_v3 | 0.55 | 0.20 | 0.20, 0.85, 0.85, 0.20, 0.20 (FAR20: 0.95!, 1.00!, 1.00!, 1.00!, 1.00!) | 3.7 | asr 0.0, diarize 0.0, checks 3.7 | 3.7 | 9.9 | 0 | 0 | 4d318d2b77 |
| facts_only | 0.55 | 0.25 | 0.25, 0.45, 0.25, 0.25, 0.25 (FAR20: 0.95!, 1.00!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 8.1, diarize 5.5, checks 2.5 | 2.5 | 21.6 | 0 | 0 | 4d318d2b77 |
| qwen_general | 0.70 | 0.20 | 0.20, 0.40, 0.20, 0.20, 0.20 (FAR20: 0.80!, 1.00!, 1.00!, 1.00!, 1.00!) | 1.8 | asr 0.0, diarize 0.0, checks 1.8 | 1.8 | 15.0 | 0 | 0 | 4d318d2b77 |
| kev_facts | 0.55 | 0.20 | 0.20, 0.25, 0.20, 0.20, 0.20 (FAR20: 0.25, 0.20, 0.25, 0.25, 0.20) | 7.2 | asr 0.0, diarize 0.0, checks 7.1 | 7.2 | 20.0 | 0 | 0 | 4d318d2b77 |
| kev_general | 0.70 | 0.35 | 0.35, 0.35, 0.35, 0.45, 0.35 (FAR20: 0.90, 0.75, 0.80, 0.80, 0.85) | 1.0 | asr 0.0, diarize 0.0, checks 1.0 | 1.0 | 3.2 | 0 | 0 | 4d318d2b77 |
| q38q6_facts | 0.55 | 0.25 | 0.25, 0.20, 0.30, 0.25, 0.25 (FAR20: 0.25, 0.20, 0.20, 0.20, 0.20) | 110.6 | asr 0.0, diarize 0.0, checks 110.5 | 110.5 | 20.0 | 0 | 0 | 9b3cbfd28d |
| q38q6_general | 0.70 | 0.25 | 0.25, 0.25, 0.25, 0.65, 0.25 (FAR20: 0.95!, 0.65, 0.65, 0.95, 0.95) | 96.8 | asr 0.0, diarize 0.0, checks 96.7 | 96.7 | 15.0 | 0 | 0 | 9b3cbfd28d |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| champion | 0.00 / 50% / - | 0.72 / 36% / 19% | 0.82 / - / 30% | 0.72 / 41% / 17% | 0.68 / 37% / 26% |
| champion_v3 | 0.00 / 50% / - | 0.73 / 36% / 17% | 1.00 / - / 0% | 0.74 / 41% / 13% | 0.75 / 37% / 13% |
| facts_only | 0.00 / 40% / - | 0.72 / 36% / 19% | 0.82 / - / 30% | 0.72 / 41% / 17% | 0.69 / 33% / 26% |
| qwen_general | 0.00 / 60% / - | 0.66 / 34% / 31% | 0.89 / - / 20% | 0.64 / 41% / 30% | 0.68 / 37% / 26% |
| kev_facts | 0.00 / 20% / - | 0.71 / 20% / 31% | 0.57 / - / 60% | 0.70 / 19% / 35% | 0.65 / 22% / 39% |
| kev_general | 0.00 / 50% / - | 0.67 / 57% / 14% | 1.00 / - / 0% | 0.70 / 52% / 13% | 0.70 / 59% / 9% |
| q38q6_facts | - / 0% / - | 0.80 / 14% / 22% | 0.57 / - / 60% | 0.73 / 11% / 35% | 0.79 / 11% / 26% |
| q38q6_general | 0.00 / 20% / - | 0.71 / 41% / 17% | 0.89 / - / 20% | 0.73 / 37% / 17% | 0.73 / 37% / 17% |

## `champion_v3` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = champion_v3 - champion

| metric | champion | champion_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.83 | +0.031 | [+0.002, +0.072] | **real**: champion_v3 better |
| alarm AUC | 0.80 | 0.81 | +0.007 | [-0.021, +0.053] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = champion_v3 - champion

| metric | champion | champion_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.75 | +0.049 | [+0.000, +0.117] | no detectable difference |
| alarm_f1 | 0.65 | 0.65 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 39% | 39% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 22% | 13% | -9pp | [-20pp, +0pp] | no detectable difference |
| accuracy | 61% | 65% | +4pp | [+0pp, +10pp] | no detectable difference |
| review_recall | 33% | 67% | +33pp | [+0pp, +67pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.74 | +0.043 | [+0.000, +0.098] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-champion_v3 4, p=0.125; 3-class only-champion 0 vs only-champion_v3 4, p=0.125.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = champion_v3 - champion

| metric | champion | champion_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.73 | +0.052 | [+0.000, +0.127] | no detectable difference |
| alarm_f1 | 0.30 | 0.30 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 28% | 20% | -9pp | [-20pp, +0pp] | no detectable difference |
| accuracy | 48% | 52% | +4pp | [+0pp, +10pp] | no detectable difference |
| review_recall | 50% | 83% | +33pp | [+0pp, +67pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.74 | +0.043 | [+0.000, +0.098] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-champion_v3 4, p=0.125; 3-class only-champion 0 vs only-champion_v3 4, p=0.125.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = champion_v3 - champion

| metric | champion | champion_v3 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.76 | +0.049 | [+0.000, +0.118] | no detectable difference |
| alarm_f1 | 0.62 | 0.62 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 35% | 35% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 22% | 13% | -9pp | [-20pp, +0pp] | no detectable difference |
| accuracy | 60% | 64% | +4pp | [+0pp, +10pp] | no detectable difference |
| review_recall | 42% | 75% | +33pp | [+0pp, +67pp] | no detectable difference |
| flag_balanced_accuracy | 0.72 | 0.76 | +0.043 | [+0.000, +0.098] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-champion_v3 4, p=0.125; 3-class only-champion 0 vs only-champion_v3 4, p=0.125.

Flips (cv, 4 calls):

| call | expected | champion | champion_v3 | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-review-K2 | review | no_alert | review | 0.17/0.51 | fixed | 00:59-01:05 access: Ich lese Ihnen zuerst die Ziffern vom Zettel vor. 492806. Vielleicht hilft Ihnen das ja. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | Kein Alarm: höchster Score 0.17 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-disclosure-review-K1 | review | no_alert | review | 0.02/0.47 | fixed | 00:21-00:25 disclosure: Haben Sie von Frau Ackermann eine schriftliche Erlaubnis für solche Auskünfte? - facts: Fakt: Auskunft über den Umfang der Vollmacht hinaus = ja (0.62) - Die Mitarbeiterin sagt... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-disclosure-review-K2 | review | no_alert | review | 0.02/0.47 | fixed | 00:30-00:36 disclosure: Der Zettel ist bei uns angekommen, prüft unseren Rechtsdienst noch und das ist nicht entschieden. Das dauert ein paar Tage. - facts: Fakt: Im Gespräch offen, ob eine Berechtigu... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-multi-04-K2 | review | no_alert | review | 0.04/0.47 | fixed | 00:58-01:15 disclosure: Ob Ihre Kranke Kasse bezahlt ist. Sie hat mir den Vorfahrerwochen eine Vollmacht unterschrieben. Die Vollmacht ist angekommen, aber unsere Rechtsabteilung prüft sie noch. Und b... | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |

## `facts_only` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.78 | -0.018 | [-0.050, +0.015] | no detectable difference |
| alarm AUC | 0.80 | 0.81 | +0.009 | [-0.020, +0.044] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.71 | +0.007 | [+0.000, +0.024] | no detectable difference |
| alarm_f1 | 0.65 | 0.63 | -0.019 | [-0.106, +0.066] | no detectable difference |
| false_alarm_rate | 39% | 37% | -2pp | [-6pp, +0pp] | no detectable difference |
| miss_rate | 22% | 22% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 61% | 62% | +1pp | [-7pp, +8pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-67pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.71 | +0.009 | [+0.000, +0.031] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 1, p=1.0; 3-class only-champion 4 vs only-facts_only 5, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.69 | +0.013 | [+0.000, +0.045] | no detectable difference |
| alarm_f1 | 0.30 | 0.30 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 33% | 33% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 28% | 26% | -2pp | [-7pp, +0pp] | no detectable difference |
| accuracy | 48% | 48% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 50% | 50% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.70 | +0.011 | [+0.000, +0.036] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 1, p=1.0; 3-class only-champion 0 vs only-facts_only 0, p=1.0.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = facts_only - champion

| metric | champion | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.71 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.62 | 0.62 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 35% | 35% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 22% | 22% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 60% | 60% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 42% | 42% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.72 | 0.72 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-champion 0 vs only-facts_only 0, p=1.0; 3-class only-champion 0 vs only-facts_only 0, p=1.0.

Flips (cv, 16 calls):

| call | expected | champion | facts_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-03-A-K2 | alarm | review | alarm | 0.47/0.50 | same | 01:06-01:18 access: Die vier Ziffern aus dem Brief von vorhin lauten sechs, eins, neun, drei. Ist das die richtige Zahl für den Laden? Bitte sagt ihr mir solche Zahlen nie am Telefon. Ihr könnt den Bi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt die vier Ziffern aus dem Brief zum Laden am Telefon preis. (Regel: access.review_1) |
| T50-access-review-K1 | review | review | alarm | 0.81/0.82 | same | 00:59-01:05 access: Ich lese Ihnen zuerst die Ziffern des Zettels vor. vier, neun, zwei, acht, null, sechs. Vielleicht hilft Ihnen das ja. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - ... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Ziffernreihen des Zettels vor, obwohl es unklar war, ob es der aktuelle PIN ist. (Regel: access.alarm_1) |
| T50-access-trap-K2 | no_alert | review | no_alert | 0.06/0.04 | fixed | 00:03-00:10 access: Guten Tag, Frau Stalder, hier ist der Daniel Vogt. Sie haben Ihr Passwort vergessen, habe ich gelesen. Ja, schlicht. Ich habe es aus letzter Woche geändert und jetzt fällt es mir n... | keywords: Stichwort K10 «Passwort» (Zugangswörter) |
| T50-disclosure-01-B-K1 | no_alert | review | alarm | 0.47/0.50 | same | 00:05-01:03 disclosure: Guten Tag, hier ist Sandra Rohner. Ich rufe wegen dem Konto meiner Mutter an. Sie lebt seit dem Sommer im Pflegeheim. Die Heim schickt jeden Monat Rechnungen und ich möchte wis... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.72) - Die Kunde fragt nach den Rechnungen ihres Mütters vom Pflegeheim. (Regel: disclosure.review_1) |
| T50-disclosure-01-B-K2 | no_alert | review | alarm | 0.47/0.50 | same | 00:56-01:00 disclosure: dem Konto ihrer Mutter liegen im Moment noch einundvierzigtausend Franken. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Assistentin gibt Sand... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Assistentin gibt Sandra Runger die aktuelle Kontostandsumme ihrer Mutter. (Regel: disclosure.review_1) |
| T50-documentation-01-A-K1 | alarm | review | alarm | 0.47/0.50 | same | 00:57-01:03 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. Hört auf, die soll das nicht sehen. Streichen Sie die Zeilen einfach. - facts: Fakt: Verlangt, etw... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-A-K2 | alarm | review | alarm | 0.47/0.50 | same | 00:57-01:03 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. Nein, ich soll das nicht sehen. Streichen Sie die Zeilen einfach. - facts: Fakt: Verlangt, etwas n... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die dritte Zeile nicht in die Notiz für die Kreditstelle zu schreiben. (Regel: documentation.review... |
| T50-documentation-01-B-K1 | no_alert | review | alarm | 0.47/0.50 | same | 00:56-01:02 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. Die soll das nicht sehen. Streichen Sie die Zeilen einfach. - facts: Fakt: Verlangt, etwas nic... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-B-K2 | no_alert | review | alarm | 0.47/0.50 | same | 00:56-01:02 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. Ich soll das nicht sehen. Streichen Sie die Zeilen einfach. - facts: Fakt: Verlangt, etwas nic... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-02-A-K2 | no_alert | review | alarm | 0.78/0.78 | same | 00:58-01:05 documentation: Die Zeile mit der Bürgschaft lassen Sie bitte in die Unterlagen für die Kreditprüfung weg. Das muss dort niemand wissen. Der Rest kann so bleiben. - facts: Fakt: Verlangt, e... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die Zeile mit der Bürgschaft in die Unterlagen für die Kreditprüfung nicht einzufügen. (Regel: docu... |
| T50-multi-03-K1 | no_alert | review | alarm | 0.47/0.50 | same | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also der... - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) -... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostand von Herrn Wüttrichs Konto preis. (Regel: disclosure.review_1) |
| T50-multi-03-K2 | no_alert | review | alarm | 0.47/0.50 | same | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also dick. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme des Mannes der Anruferin mit. (Regel: disclosure.review_1) |
| T50-multi-04-K1 | review | review | alarm | 0.47/0.50 | same | 01:09-01:18 disclosure: Können Sie mir nicht wissend sagen, ob die Rechnung bezahlt ist? Die Kranke Kasse hat Ihnen schon eine Mahnung geschickt. Das kann ich Ihnen erst sagen, wenn die Prüfung abgesc... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Kunde fragt nach der Zahlung einer Rechnung für sein Altersheim-Verwandtes, ohne dass diese Information an ihn weitergegeben wird. (Re... |
| T50-splitting-03-A-K2 | alarm | review | alarm | 0.84/0.86 | same | 00:25-00:33 splitting: Bei Ihnen werden Überweisungen über fünfzigtausend Franken intergenau angeschaut. Und ich möchte die Kontrolle umgehen. Will man das zu lange dauern? Das habe ich von einem Koll... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass Überweisungen über fünfzigtausend Franken genau kontrolliert werden und er die Kontrolle umgehen möchte. (... |
| T50-trade-review-K1 | review | review | alarm | 0.84/0.84 | same | 00:06-00:11 trade: Ja, guten Tag. Ich habe am Samstag im Fitnesscenter ein bisschen über die Firma Kelsa gehört. - facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die K... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die Kunde berichtet von Informationen, die ihr Freundin aus dem Fitnesscenter mitgeteilt hat. (Regel: trade.alarm_1) |
| T50-trade-review-K2 | review | review | alarm | 0.50/0.50 | same | 01:03-01:10 trade: Wegen der Neuigkeit, unserem Fitnesscenter will ich jetzt für fünftausend Franken Aktien von Kelsa kaufen. Bitte nehmen Sie das auf. - facts: Fakt: Eigener Handelswunsch geäussert =... | facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde möchte Aktien von Kelsa für 5'000 Franken kaufen. (Regel: trade.review_1) |

## `qwen_general` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.70 | -0.102 | [-0.203, -0.001] | **real**: champion better |
| alarm AUC | 0.80 | 0.64 | -0.164 | [-0.282, -0.056] | **real**: champion better |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.66 | -0.039 | [-0.141, +0.074] | no detectable difference |
| alarm_f1 | 0.65 | 0.53 | -0.118 | [-0.252, +0.000] | no detectable difference |
| false_alarm_rate | 39% | 39% | +0pp | [-23pp, +23pp] | no detectable difference |
| miss_rate | 22% | 28% | +7pp | [-12pp, +25pp] | no detectable difference |
| accuracy | 61% | 55% | -6pp | [-18pp, +6pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-67pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.66 | -0.033 | [-0.141, +0.087] | no detectable difference |

McNemar exact (calls): flag correct only-champion 18 vs only-qwen_general 15, p=0.7283; 3-class only-champion 21 vs only-qwen_general 15, p=0.405.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.59 | -0.089 | [-0.200, +0.022] | no detectable difference |
| alarm_f1 | 0.30 | 0.26 | -0.045 | [-0.348, +0.261] | no detectable difference |
| false_alarm_rate | 33% | 30% | -4pp | [-24pp, +17pp] | no detectable difference |
| miss_rate | 28% | 43% | +15pp | [-2pp, +34pp] | no detectable difference |
| accuracy | 48% | 49% | +1pp | [-12pp, +14pp] | no detectable difference |
| review_recall | 50% | 42% | -8pp | [-57pp, +38pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.63 | -0.058 | [-0.143, +0.037] | no detectable difference |

McNemar exact (calls): flag correct only-champion 18 vs only-qwen_general 13, p=0.4731; 3-class only-champion 15 vs only-qwen_general 16, p=1.0.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = qwen_general - champion

| metric | champion | qwen_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.65 | -0.061 | [-0.165, +0.053] | no detectable difference |
| alarm_f1 | 0.62 | 0.49 | -0.132 | [-0.274, +0.022] | no detectable difference |
| false_alarm_rate | 35% | 30% | -6pp | [-26pp, +14pp] | no detectable difference |
| miss_rate | 22% | 35% | +13pp | [-7pp, +33pp] | no detectable difference |
| accuracy | 60% | 58% | -2pp | [-13pp, +9pp] | no detectable difference |
| review_recall | 42% | 8% | -33pp | [-75pp, +12pp] | no detectable difference |
| flag_balanced_accuracy | 0.72 | 0.68 | -0.037 | [-0.127, +0.067] | no detectable difference |

McNemar exact (calls): flag correct only-champion 16 vs only-qwen_general 13, p=0.7111; 3-class only-champion 17 vs only-qwen_general 15, p=0.8601.

Flips (cv, 43 calls):

| call | expected | champion | qwen_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-01-B-K1 | no_alert | no_alert | review | 0.00/0.06 | broken | Prüfen (knapp unter Schwelle): Score 0.06 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-02-A-K1 | no_alert | review | no_alert | 0.15/0.02 | fixed | 00:54-01:02 access: Ich lese Ihnen die sechs Ziffern, die ich vorhin vor mir hatte, einfach vor. Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Kein Alarm: höchs... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die sechs Ziffern vor, die er vorher vor sich hatte. (Regel: access.no_alert) |
| T50-access-02-A-K2 | no_alert | alarm | no_alert | 0.85/0.00 | fixed | 00:57-01:02 access: Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Wert von sechs Ziffern vor, obwohl der Berater ihn nicht benötigte. (Regel: access.alarm_1) |
| T50-access-03-A-K2 | alarm | review | alarm | 0.47/1.00 | same | 01:06-01:18 access: Die vier Ziffern aus dem Brief von vorhin lauten sechs, eins, neun, drei. Ist das die richtige Zahl für den Laden? Bitte sagt ihr mir solche Zahlen nie am Telefon. Ihr könnt den Bi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt die vier Ziffern aus dem Brief zum Laden am Telefon preis. (Regel: access.review_1) |
| T50-access-03-B-K1 | no_alert | no_alert | alarm | 0.02/1.00 | broken | Alarm: Score 1.00 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-03-B-K2 | no_alert | no_alert | alarm | 0.02/1.00 | broken | Alarm: Score 1.00 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-review-K1 | review | review | no_alert | 0.81/0.07 | broken | 00:59-01:05 access: Ich lese Ihnen zuerst die Ziffern des Zettels vor. vier, neun, zwei, acht, null, sechs. Vielleicht hilft Ihnen das ja. - Kein Alarm: höchster Score 0.07 ('Relevante Angabe verschwe... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Ziffernreihen des Zettels vor, obwohl es unklar war, ob es der aktuelle PIN ist. (Regel: access.alarm_1) |
| T50-access-trap-K1 | no_alert | no_alert | review | 0.02/0.09 | broken | Prüfen (knapp unter Schwelle): Score 0.09 für 'Relevante Angabe verschweigen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-disclosure-01-A-K1 | alarm | alarm | no_alert | 0.85/0.01 | broken | 00:20-00:26 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingetragen, sie haben dort also keinen Zugang. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt un... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.78) - Die Mitarbeiterin sagt explizit, dass keine Vollmacht für die Klientin eingetragen ist. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-A-K2 | alarm | alarm | no_alert | 0.90/0.01 | broken | 00:20-00:26 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingefragen. Sie haben dort also keinen Zugang. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt un... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.87) - Die Kunde sagt, dass sie keine Vollmacht für das Konto ihrer Mutter eingefragen hat. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-B-K1 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:05-01:03 disclosure: Guten Tag, hier ist Sandra Rohner. Ich rufe wegen dem Konto meiner Mutter an. Sie lebt seit dem Sommer im Pflegeheim. Die Heim schickt jeden Monat Rechnungen und ich möchte wis... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.72) - Die Kunde fragt nach den Rechnungen ihres Mütters vom Pflegeheim. (Regel: disclosure.review_1) |
| T50-disclosure-01-B-K2 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:56-01:00 disclosure: dem Konto ihrer Mutter liegen im Moment noch einundvierzigtausend Franken. - Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Assistentin gibt Sandra Runger die aktuelle Kontostandsumme ihrer Mutter. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K2 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Sch... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.95) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit 'Firma Konto von Nevalta ist seit letzter Woche... mit vier... |
| T50-disclosure-02-B-K1 | alarm | alarm | no_alert | 0.50/0.01 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.01 ('Relevante Angabe verschweigen') liegt unter 0.05 (Sc... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.98) - Die Mitarbeiterin gibt den Kunden die aktuelle Kontostand von -4'000 Franken. (Regel: disclosure.review_1) |
| T50-disclosure-02-B-K2 | alarm | alarm | no_alert | 0.50/0.00 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.89) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-03-A-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschwei... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über ein Konto oder Kredit, insbesondere die noch stehende Hypothek ... |
| T50-disclosure-03-A-K2 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unte... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über den Hypothekenschuldner, insbesondere den Betrag der Hypothek. ... |
| T50-disclosure-03-B-K1 | alarm | alarm | no_alert | 0.50/0.00 | broken | 01:00-01:03 disclosure: Er legt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus Ban... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von zweihunderttausend Franken. ... |
| T50-disclosure-03-B-K2 | alarm | alarm | no_alert | 0.50/0.00 | broken | 01:00-01:03 disclosure: Er schickt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.05 (Schwelle 0.20 minus ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von 200'000 Franken. (Regel: dis... |
| T50-disclosure-review-K1 | review | no_alert | alarm | 0.02/0.67 | fixed | Alarm: Score 0.67 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-disclosure-review-K2 | review | no_alert | alarm | 0.02/0.86 | fixed | Alarm: Score 0.86 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-documentation-01-A-K1 | alarm | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-A-K2 | alarm | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die dritte Zeile nicht in die Notiz für die Kreditstelle zu schreiben. (Regel: documentation.review... |
| T50-documentation-01-B-K1 | no_alert | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-B-K2 | no_alert | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-02-A-K2 | no_alert | review | alarm | 0.78/0.98 | same | 00:58-01:05 documentation: Die Zeile mit der Bürgschaft lassen Sie bitte in die Unterlagen für die Kreditprüfung weg. Das muss dort niemand wissen. Der Rest kann so bleiben. - Alarm: Score 0.98 für 'R... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die Zeile mit der Bürgschaft in die Unterlagen für die Kreditprüfung nicht einzufügen. (Regel: docu... |
| T50-documentation-03-B-K2 | no_alert | no_alert | alarm | 0.00/1.00 | broken | Alarm: Score 1.00 für 'Relevante Angabe verschweigen' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-multi-01-K2 | alarm | no_alert | review | 0.05/0.34 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. Brechen Sie die Zahlung ab und starten Sie sie neu auf. ... | Kein Alarm: höchster Score 0.05 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-03-K1 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also der... - Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.25 (... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostand von Herrn Wüttrichs Konto preis. (Regel: disclosure.review_1) |
| T50-multi-03-K2 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also dick. - Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.25 (S... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme des Mannes der Anruferin mit. (Regel: disclosure.review_1) |
| T50-multi-04-K1 | review | review | alarm | 0.47/0.88 | same | 00:35-00:36 access: 916305. Dann wissen Sie, welcher es war. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Kunde fragt nach der Zahlung einer Rechnung für sein Altersheim-Verwandtes, ohne dass diese Information an ihn weitergegeben wird. (Re... |
| T50-multi-04-K2 | review | no_alert | alarm | 0.04/0.95 | fixed | 00:33-00:36 access: neun eins sechs drei null fünf. Dann wissen Sie, welcher es war. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-01-A-K1 | no_alert | no_alert | alarm | 0.00/0.84 | broken | Alarm: Score 0.84 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-01-A-K2 | no_alert | no_alert | alarm | 0.00/0.70 | broken | Alarm: Score 0.70 für 'Zugangsinformation preisgegeben' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-02-B-K1 | no_alert | alarm | no_alert | 0.50/0.01 | fixed | 00:58-01:06 disclosure: zwei, null, neun, zwei, sechs. Man steht dort nicht. Danke. Ich sehe eine Gutschrift vom Hotel über dreihundertvierzig Franken von gestern. - Kein Alarm: höchster Score 0.01 ('... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.82) - Der Berater gibt die Zahlungsumfrage des Hotels vor, die zu einem Betrag von 345 Franken beträgt. (Regel: disclosure.review_1) |
| T50-splitting-03-A-K2 | alarm | review | alarm | 0.84/0.98 | same | 00:29-00:30 splitting: Bei Ihnen werden Überweisungen über fünfzigtausend Franken intergenau angeschaut. Und ich möchte die Kontrolle umgehen. - keywords: Stichwort K08 «Kontrolle umgehen» (Kontrollum... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass Überweisungen über fünfzigtausend Franken genau kontrolliert werden und er die Kontrolle umgehen möchte. (... |
| T50-trade-02-A-K1 | no_alert | no_alert | review | 0.00/0.18 | broken | Prüfen (knapp unter Schwelle): Score 0.18 für 'Insiderhandel' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-02-A-K2 | no_alert | no_alert | alarm | 0.00/0.94 | broken | Alarm: Score 0.94 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-03-B-K1 | no_alert | no_alert | alarm | 0.00/0.53 | broken | Alarm: Score 0.53 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-03-B-K2 | no_alert | no_alert | alarm | 0.00/0.91 | broken | Alarm: Score 0.91 für 'Insiderhandel' >= Schwelle 0.20 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-review-K1 | review | review | alarm | 0.84/0.83 | same | 00:06-00:11 trade: Ja, guten Tag. Ich habe am Samstag im Fitnesscenter ein bisschen über die Firma Kelsa gehört. - Alarm: Score 0.83 für 'Insiderhandel' >= Schwelle 0.40 bei Unsicherheit 0.00 (max. 0.... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die Kunde berichtet von Informationen, die ihr Freundin aus dem Fitnesscenter mitgeteilt hat. (Regel: trade.alarm_1) |
| T50-trade-review-K2 | review | review | alarm | 0.50/0.77 | same | 01:03-01:10 trade: Wegen der Neuigkeit, unserem Fitnesscenter will ich jetzt für fünftausend Franken Aktien von Kelsa kaufen. Bitte nehmen Sie das auf. - Alarm: Score 0.77 für 'Insiderhandel' >= Schwe... | facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde möchte Aktien von Kelsa für 5'000 Franken kaufen. (Regel: trade.review_1) |

## `kev_facts` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.85 | +0.047 | [-0.058, +0.166] | no detectable difference |
| alarm AUC | 0.80 | 0.85 | +0.046 | [-0.080, +0.189] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.67 | -0.025 | [-0.168, +0.105] | no detectable difference |
| alarm_f1 | 0.65 | 0.53 | -0.115 | [-0.271, +0.007] | no detectable difference |
| false_alarm_rate | 39% | 20% | -19pp | [-38pp, -2pp] | **real**: kev_facts better |
| miss_rate | 22% | 37% | +15pp | [+0pp, +31pp] | no detectable difference |
| accuracy | 61% | 59% | -2pp | [-13pp, +9pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-67pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.71 | +0.017 | [-0.107, +0.141] | no detectable difference |

McNemar exact (calls): flag correct only-champion 10 vs only-kev_facts 13, p=0.6776; 3-class only-champion 14 vs only-kev_facts 12, p=0.845.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.74 | +0.055 | [-0.090, +0.184] | no detectable difference |
| alarm_f1 | 0.30 | 0.53 | +0.233 | [-0.049, +0.500] | no detectable difference |
| false_alarm_rate | 33% | 17% | -17pp | [-36pp, +0pp] | no detectable difference |
| miss_rate | 28% | 30% | +2pp | [-15pp, +20pp] | no detectable difference |
| accuracy | 48% | 62% | +14pp | [-1pp, +29pp] | no detectable difference |
| review_recall | 50% | 8% | -42pp | [-86pp, +6pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.76 | +0.072 | [-0.059, +0.202] | no detectable difference |

McNemar exact (calls): flag correct only-champion 9 vs only-kev_facts 17, p=0.1686; 3-class only-champion 10 vs only-kev_facts 24, p=0.0243.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = kev_facts - champion

| metric | champion | kev_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.65 | -0.064 | [-0.232, +0.074] | no detectable difference |
| alarm_f1 | 0.62 | 0.51 | -0.115 | [-0.310, +0.042] | no detectable difference |
| false_alarm_rate | 35% | 11% | -24pp | [-44pp, -5pp] | **real**: kev_facts better |
| miss_rate | 22% | 46% | +24pp | [+8pp, +41pp] | **real**: champion better |
| accuracy | 60% | 61% | +1pp | [-12pp, +15pp] | no detectable difference |
| review_recall | 42% | 0% | -42pp | [-75pp, -12pp] | **real**: champion better |
| flag_balanced_accuracy | 0.72 | 0.72 | +0.001 | [-0.124, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-champion 13 vs only-kev_facts 15, p=0.8506; 3-class only-champion 14 vs only-kev_facts 15, p=1.0.

Flips (cv, 33 calls):

| call | expected | champion | kev_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-02-A-K2 | no_alert | alarm | review | 0.85/0.06 | same | 00:57-01:02 access: Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Prüfen (knapp unter Schwelle): Score 0.06 für 'Zugangsinformation preisgegeben' liegt zwischen... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Wert von sechs Ziffern vor, obwohl der Berater ihn nicht benötigte. (Regel: access.alarm_1) |
| T50-access-03-A-K1 | alarm | alarm | review | 0.50/0.47 | same | 00:23-00:23 access: Die neue Karte ist letzte Woche gekommen und ich benutze sie seit gestern mit der PIN aus dem Brief, - keywords: Stichwort K10 «PIN» (Zugangswörter) | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.52) - Der Advisor gibt die vier Ziffern aus dem Brief an, die zu einer anderen Karte gehören. (Regel: disclosure.review_1) |
| T50-access-review-K1 | review | review | no_alert | 0.81/0.06 | broken | 00:59-01:05 access: Ich lese Ihnen zuerst die Ziffern des Zettels vor. vier, neun, zwei, acht, null, sechs. Vielleicht hilft Ihnen das ja. - Kein Alarm: höchster Score 0.06 ('Zugangsinformation preisg... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Ziffernreihen des Zettels vor, obwohl es unklar war, ob es der aktuelle PIN ist. (Regel: access.alarm_1) |
| T50-access-trap-K2 | no_alert | review | no_alert | 0.06/0.02 | fixed | 00:03-00:10 access: Guten Tag, Frau Stalder, hier ist der Daniel Vogt. Sie haben Ihr Passwort vergessen, habe ich gelesen. Ja, schlicht. Ich habe es aus letzter Woche geändert und jetzt fällt es mir n... | keywords: Stichwort K10 «Passwort» (Zugangswörter) |
| T50-disclosure-02-A-K1 | no_alert | alarm | no_alert | 0.50/0.05 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.05 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K2 | no_alert | alarm | no_alert | 0.50/0.04 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.04 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.95) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit 'Firma Konto von Nevalta ist seit letzter Woche... mit vier... |
| T50-disclosure-02-B-K1 | alarm | alarm | review | 0.50/0.10 | same | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... mit viertausend Franken im Minus. - Prüfen (knapp unter Schwelle): Score 0.10 für 'Auskunft an Dritte' liegt zwischen 0.05... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.98) - Die Mitarbeiterin gibt den Kunden die aktuelle Kontostand von -4'000 Franken. (Regel: disclosure.review_1) |
| T50-disclosure-02-B-K2 | alarm | alarm | review | 0.50/0.07 | same | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Prüfen (knapp unter Schwelle): Score 0.07 für 'Auskunft an Dritte' liegt zwischen 0... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.89) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-03-A-K1 | no_alert | alarm | no_alert | 0.50/0.02 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über ein Konto oder Kredit, insbesondere die noch stehende Hypothek ... |
| T50-disclosure-03-A-K2 | no_alert | alarm | no_alert | 0.50/0.03 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über den Hypothekenschuldner, insbesondere den Betrag der Hypothek. ... |
| T50-disclosure-03-B-K1 | alarm | alarm | review | 0.50/0.72 | same | 01:00-01:03 disclosure: Er legt bei uns noch eine Hypothek von zweihunderttausend Franken. - Prüfen (unsicher): Score 0.72 für 'Auskunft an Dritte' erreicht die Schwelle 0.20, aber die Unsicherheit 0.... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von zweihunderttausend Franken. ... |
| T50-disclosure-trap-K1 | no_alert | alarm | no_alert | 0.96/0.02 | fixed | 00:04-00:20 disclosure: Guten Tag, hier ist Monika Eggimann. Ich möchte wissen, ob mein früherer Mann den Unterhalt schon überwiesen hat. Er hat sein Konto auch bei Ihnen. Haben Sie eine Vollmacht für... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (1.00) - Der Kunde gibt an, keine Vollmacht für das Konto seines früheren Mannes zu haben. (Regel: disclosure.alarm_1) |
| T50-disclosure-trap-K2 | no_alert | alarm | no_alert | 0.96/0.02 | fixed | 00:04-00:58 disclosure: Guten Tag, hier ist Monika Eggimann. Ich möchte wissen, ob mein früherer Mann den Unterhalt schon überwiesen hat. Er hat sein Konto auch bei Ihnen. Haben Sie eine Vollmacht für... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.99) - Der Kunde gibt an, dass er keine Vollmacht hat, und der Berater bestätigt, dass der Kunde zu dem Konto keine Angaben bekommen darf.... |
| T50-documentation-01-B-K1 | no_alert | review | no_alert | 0.47/0.03 | fixed | 00:56-01:02 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. Die soll das nicht sehen. Streichen Sie die Zeilen einfach. - Kein Alarm: höchster Score 0.03 ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-B-K2 | no_alert | review | no_alert | 0.47/0.04 | fixed | 00:56-01:02 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. Ich soll das nicht sehen. Streichen Sie die Zeilen einfach. - Kein Alarm: höchster Score 0.04 ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-02-A-K2 | no_alert | review | alarm | 0.78/0.50 | same | 00:58-01:05 documentation: Die Zeile mit der Bürgschaft lassen Sie bitte in die Unterlagen für die Kreditprüfung weg. Das muss dort niemand wissen. Der Rest kann so bleiben. - Alarm: Score 0.50 für 'A... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die Zeile mit der Bürgschaft in die Unterlagen für die Kreditprüfung nicht einzufügen. (Regel: docu... |
| T50-documentation-03-A-K2 | alarm | alarm | review | 0.98/0.14 | same | 01:06-01:14 documentation: Punkt fünf möchte ich nicht in den Unterlagen für die Kreditabteilung haben. Bitte streichen Sie ihn, bevor Sie alles weiterleiten. Die Abteilung soll ihn nicht lesen. - Prü... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte, dass der Darlehen von seinem Onkel nicht in den Unterlagen für die Kreditabteilung aufgeführt wird. (Regel: documen... |
| T50-documentation-03-B-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 01:06-01:14 documentation: Den Punkt fünf möchte ich nicht in den Unterlagen für die Kreditabteilung haben. Bitte streichen Sie ihn, bevor Sie alles weiterleiten. Die Abteilung soll ihn nicht lesen. -... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte den Punkt fünf, der eine private Angelegenheit erwähnt, nicht in den Unterlagen für die Kreditabteilung haben und bi... |
| T50-documentation-trap-K1 | no_alert | alarm | review | 0.95/0.07 | same | 00:18-00:26 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. Mein Lohn ist 7800 Franken im Monat. - Prüfen (knapp unter Schwelle): Score 0.07 für '... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-multi-03-K1 | no_alert | review | no_alert | 0.47/0.05 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also der... - Kein Alarm: höchster Score 0.05 ('Auskunft an Dritte') liegt unter 0.10 (... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostand von Herrn Wüttrichs Konto preis. (Regel: disclosure.review_1) |
| T50-multi-03-K2 | no_alert | review | no_alert | 0.47/0.07 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also dick. - Kein Alarm: höchster Score 0.07 ('Auskunft an Dritte') liegt unter 0.10 (S... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme des Mannes der Anruferin mit. (Regel: disclosure.review_1) |
| T50-multi-04-K1 | review | review | no_alert | 0.47/0.04 | broken | 01:09-01:18 disclosure: Können Sie mir nicht wissend sagen, ob die Rechnung bezahlt ist? Die Kranke Kasse hat Ihnen schon eine Mahnung geschickt. Das kann ich Ihnen erst sagen, wenn die Prüfung abgesc... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Kunde fragt nach der Zahlung einer Rechnung für sein Altersheim-Verwandtes, ohne dass diese Information an ihn weitergegeben wird. (Re... |
| T50-numbers-02-A-K2 | no_alert | no_alert | alarm | 0.00/0.50 | broken | Alarm: Score 0.50 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-02-B-K2 | no_alert | no_alert | alarm | 0.00/0.50 | broken | Alarm: Score 0.50 für 'Auskunft an Dritte' >= Schwelle 0.20 bei Unsicherheit 0.35 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-01-A-K1 | alarm | alarm | no_alert | 0.86/0.03 | broken | 00:28-00:33 splitting: uns muss der Verwaltungsrat jede Zahlung ab 20 000 Franken freigeben. Und diese Freigabe bitte ich umzugehen, weil es eilt. - Kein Alarm: höchster Score 0.03 ('Zuständigkeit/Kon... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (0.95) - Der Kunde erklärt, dass der Verwaltungsrat jede Zahlung ab 20'000 Franken freigeben muss, und bittet um die Überweisung, um die... |
| T50-splitting-01-A-K2 | alarm | alarm | no_alert | 0.95/0.02 | broken | 00:27-00:33 splitting: uns muss der Verwaltungsrat jede Zahlung ab 20 .000 Franken freigeben. Und diese Freigabe möchte ich diesmal umgehen, weil es eilt. - Kein Alarm: höchster Score 0.02 ('Zuständig... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde erklärt, dass der Verwaltungsrat jede Zahlung ab 20.000 Franken freigeben muss, und möchte diese Freigabe umgehen, da... |
| T50-splitting-02-B-K1 | alarm | no_alert | review | 0.00/0.10 | fixed | Prüfen (knapp unter Schwelle): Score 0.10 für 'Zuständigkeit/Kontrolle umgehen' liegt zwischen 0.05 und der Schwelle 0.20. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-03-A-K1 | alarm | alarm | no_alert | 0.91/0.06 | broken | 00:25-00:33 splitting: Bei Ihnen werden Überweisungen über fünfzigtausend Franken intergenau angeschaut. Und ich will die Kontrolle umgehen, weil mir das zu lange dauert. Das habe ich von einem Kolleg... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass ihm das Überweisen über 50'000 Franken zu lang sei und er das umgehen wolle. (Regel: splitting.alarm_1) |
| T50-splitting-03-A-K2 | alarm | review | no_alert | 0.84/0.07 | broken | 00:25-00:33 splitting: Bei Ihnen werden Überweisungen über fünfzigtausend Franken intergenau angeschaut. Und ich möchte die Kontrolle umgehen. Will man das zu lange dauern? Das habe ich von einem Koll... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass Überweisungen über fünfzigtausend Franken genau kontrolliert werden und er die Kontrolle umgehen möchte. (... |
| T50-splitting-review-K1 | review | alarm | no_alert | 0.50/0.03 | broken | 00:37-00:44 splitting: Bitte teilen Sie die Rechnung für das Zelt in zwei gleiche Teile auf. Eine Zahlung heute und eine nächste Woche. So ist es mir lieber. - Kein Alarm: höchster Score 0.03 ('Zustän... | facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Kunde möchte die Rechnung für das Zelt in zwei gleiche Teile aufteilen. (Regel: splitting.review_1) |
| T50-splitting-review-K2 | review | alarm | no_alert | 0.50/0.02 | broken | 00:37-00:42 splitting: Bitte teilen Sie die Rechnung für das Zelt in zwei gleiche Teile auf. Eine Zahlung heute und eine nächste Woche. - Kein Alarm: höchster Score 0.02 ('Zuständigkeit/Kontrolle umge... | facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Kunde möchte die Rechnung für das Zelt in zwei gleiche Teile aufteilen. (Regel: splitting.review_1) |
| T50-trade-review-K1 | review | review | alarm | 0.84/0.99 | same | 00:06-00:11 trade: Ja, guten Tag. Ich habe am Samstag im Fitnesscenter ein bisschen über die Firma Kelsa gehört. - Alarm: Score 0.99 für 'Insiderhandel' >= Schwelle 0.25 bei Unsicherheit 0.02 (max. 0.... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die Kunde berichtet von Informationen, die ihr Freundin aus dem Fitnesscenter mitgeteilt hat. (Regel: trade.alarm_1) |
| T50-trade-review-K2 | review | review | alarm | 0.50/0.98 | same | 01:03-01:10 trade: Wegen der Neuigkeit, unserem Fitnesscenter will ich jetzt für fünftausend Franken Aktien von Kelsa kaufen. Bitte nehmen Sie das auf. - Alarm: Score 0.98 für 'Insiderhandel' >= Schwe... | facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde möchte Aktien von Kelsa für 5'000 Franken kaufen. (Regel: trade.review_1) |

## `kev_general` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.75 | -0.051 | [-0.157, +0.075] | no detectable difference |
| alarm AUC | 0.80 | 0.72 | -0.089 | [-0.204, +0.050] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.70 | +0.002 | [-0.113, +0.138] | no detectable difference |
| alarm_f1 | 0.65 | 0.55 | -0.103 | [-0.242, +0.040] | no detectable difference |
| false_alarm_rate | 39% | 56% | +17pp | [-8pp, +41pp] | no detectable difference |
| miss_rate | 22% | 11% | -11pp | [-33pp, +10pp] | no detectable difference |
| accuracy | 61% | 51% | -10pp | [-21pp, +2pp] | no detectable difference |
| review_recall | 33% | 25% | -8pp | [-50pp, +25pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.67 | -0.029 | [-0.152, +0.110] | no detectable difference |

McNemar exact (calls): flag correct only-champion 24 vs only-kev_general 20, p=0.6516; 3-class only-champion 28 vs only-kev_general 18, p=0.1839.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.52 | -0.160 | [-0.335, +0.000] | no detectable difference |
| alarm_f1 | 0.30 | 0.48 | +0.181 | [-0.169, +0.512] | no detectable difference |
| false_alarm_rate | 33% | 15% | -19pp | [-37pp, -2pp] | **real**: kev_general better |
| miss_rate | 28% | 59% | +30pp | [+7pp, +54pp] | **real**: champion better |
| accuracy | 48% | 59% | +11pp | [-3pp, +24pp] | no detectable difference |
| review_recall | 50% | 0% | -50pp | [-86pp, -17pp] | **real**: champion better |
| flag_balanced_accuracy | 0.69 | 0.63 | -0.060 | [-0.157, +0.046] | no detectable difference |

McNemar exact (calls): flag correct only-champion 21 vs only-kev_general 17, p=0.6271; 3-class only-champion 13 vs only-kev_general 24, p=0.0989.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = kev_general - champion

| metric | champion | kev_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.55 | -0.159 | [-0.319, -0.013] | **real**: champion better |
| alarm_f1 | 0.62 | 0.52 | -0.100 | [-0.291, +0.100] | no detectable difference |
| false_alarm_rate | 35% | 26% | -9pp | [-31pp, +12pp] | no detectable difference |
| miss_rate | 22% | 50% | +28pp | [+6pp, +50pp] | **real**: champion better |
| accuracy | 60% | 58% | -2pp | [-14pp, +11pp] | no detectable difference |
| review_recall | 42% | 17% | -25pp | [-50pp, +17pp] | no detectable difference |
| flag_balanced_accuracy | 0.72 | 0.62 | -0.095 | [-0.219, +0.031] | no detectable difference |

McNemar exact (calls): flag correct only-champion 24 vs only-kev_general 16, p=0.2682; 3-class only-champion 20 vs only-kev_general 18, p=0.8714.

Flips (cv, 59 calls):

| call | expected | champion | kev_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-01-A-K1 | alarm | no_alert | review | 0.01/0.21 | fixed | Prüfen (knapp unter Schwelle): Score 0.21 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-01-A-K2 | alarm | no_alert | review | 0.01/0.25 | fixed | Prüfen (knapp unter Schwelle): Score 0.25 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-01-B-K2 | no_alert | no_alert | review | 0.00/0.24 | broken | Prüfen (knapp unter Schwelle): Score 0.24 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-02-A-K1 | no_alert | review | alarm | 0.15/0.45 | same | 00:54-01:02 access: Ich lese Ihnen die sechs Ziffern, die ich vorhin vor mir hatte, einfach vor. Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Alarm: Score 0.45... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die sechs Ziffern vor, die er vorher vor sich hatte. (Regel: access.no_alert) |
| T50-access-03-A-K2 | alarm | review | alarm | 0.47/0.49 | same | 01:06-01:18 access: Die vier Ziffern aus dem Brief von vorhin lauten sechs, eins, neun, drei. Ist das die richtige Zahl für den Laden? Bitte sagt ihr mir solche Zahlen nie am Telefon. Ihr könnt den Bi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt die vier Ziffern aus dem Brief zum Laden am Telefon preis. (Regel: access.review_1) |
| T50-access-03-B-K1 | no_alert | no_alert | alarm | 0.02/0.58 | broken | 00:42-01:20 documentation: Die Zahlung wurde wegen einer falschen E-GAP abgelehnt. Habt ihr vielleicht die Zahl verwechselt? Das kann sein. Ich bin mit der Karte durcheinander gekommen. Ich habe die B... | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-03-B-K2 | no_alert | no_alert | alarm | 0.02/0.67 | broken | 00:42-01:20 documentation: Die Zahlung wurde wegen einer falschen E-GAP abgelehnt. Habt ihr vielleicht die Zahl verwechselt? Das kann sein. Ich bin mit der Karte durcheinander gekommen. Ich habe die B... | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-review-K1 | review | review | alarm | 0.81/0.38 | same | 01:02-01:04 access: vier, neun, zwei, acht, null, sechs. Vielleicht hilft Ihnen das ja. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Ziffernreihen des Zettels vor, obwohl es unklar war, ob es der aktuelle PIN ist. (Regel: access.alarm_1) |
| T50-access-review-K2 | review | no_alert | review | 0.17/0.29 | fixed | 01:03-01:04 access: 492806. Vielleicht hilft Ihnen das ja. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | Kein Alarm: höchster Score 0.17 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-access-trap-K1 | no_alert | no_alert | alarm | 0.02/0.52 | broken | 00:00-00:32 documentation: Guten Tag, Frau Stalder, hier ist der Daniel Fock. Sie haben Ihr Passwort vergessen, habe ich gelesen. Ja, schlicht. Ich habe es aus letzter Woche geändert und jetzt fällt e... | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-trap-K2 | no_alert | review | alarm | 0.06/0.54 | same | 00:00-00:36 documentation: Guten Tag, Frau Stalder, hier ist der Daniel Vogt. Sie haben Ihr Passwort vergessen, habe ich gelesen. Ja, schlicht. Ich habe es aus letzter Woche geändert und jetzt fällt e... | keywords: Stichwort K10 «Passwort» (Zugangswörter) |
| T50-disclosure-01-A-K1 | alarm | alarm | no_alert | 0.85/0.12 | broken | 00:20-00:26 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingetragen, sie haben dort also keinen Zugang. - Kein Alarm: höchster Score 0.12 ('Relevante Angabe verschweigen... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.78) - Die Mitarbeiterin sagt explizit, dass keine Vollmacht für die Klientin eingetragen ist. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-A-K2 | alarm | alarm | no_alert | 0.90/0.20 | broken | 00:20-00:26 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingefragen. Sie haben dort also keinen Zugang. - Kein Alarm: höchster Score 0.20 ('Auskunft an Dritte') liegt un... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.87) - Die Kunde sagt, dass sie keine Vollmacht für das Konto ihrer Mutter eingefragen hat. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-B-K1 | no_alert | review | no_alert | 0.47/0.10 | fixed | 00:05-01:03 disclosure: Guten Tag, hier ist Sandra Rohner. Ich rufe wegen dem Konto meiner Mutter an. Sie lebt seit dem Sommer im Pflegeheim. Die Heim schickt jeden Monat Rechnungen und ich möchte wis... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.72) - Die Kunde fragt nach den Rechnungen ihres Mütters vom Pflegeheim. (Regel: disclosure.review_1) |
| T50-disclosure-01-B-K2 | no_alert | review | no_alert | 0.47/0.11 | fixed | 00:56-01:00 disclosure: dem Konto ihrer Mutter liegen im Moment noch einundvierzigtausend Franken. - Kein Alarm: höchster Score 0.11 ('Relevante Angabe verschweigen') liegt unter 0.30 (Schwelle 0.45 m... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Assistentin gibt Sandra Runger die aktuelle Kontostandsumme ihrer Mutter. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K1 | no_alert | alarm | no_alert | 0.50/0.11 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.11 ('Insiderhandel') liegt unter 0.30 (Schwelle 0.45 minus Band ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K2 | no_alert | alarm | no_alert | 0.50/0.10 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.10 ('Insiderhandel') liegt unter 0.30 (Schwelle 0.45 minus... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.95) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit 'Firma Konto von Nevalta ist seit letzter Woche... mit vier... |
| T50-disclosure-02-B-K1 | alarm | alarm | no_alert | 0.50/0.25 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.25 ('Relevante Angabe verschweigen') liegt unter 0.30 (Sc... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.98) - Die Mitarbeiterin gibt den Kunden die aktuelle Kontostand von -4'000 Franken. (Regel: disclosure.review_1) |
| T50-disclosure-02-B-K2 | alarm | alarm | review | 0.50/0.37 | same | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Prüfen (knapp unter Schwelle): Score 0.37 für 'Relevante Angabe verschweigen' liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.89) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-03-A-K1 | no_alert | alarm | no_alert | 0.50/0.04 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.04 ('Insiderhandel') liegt unte... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über ein Konto oder Kredit, insbesondere die noch stehende Hypothek ... |
| T50-disclosure-03-A-K2 | no_alert | alarm | no_alert | 0.50/0.05 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.05 ('Insiderhandel') liegt unte... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über den Hypothekenschuldner, insbesondere den Betrag der Hypothek. ... |
| T50-disclosure-03-B-K1 | alarm | alarm | no_alert | 0.50/0.10 | broken | 01:00-01:03 disclosure: Er legt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.10 ('Insiderhandel') liegt unter 0.30 (Schwelle 0.45 minus Band 0.15). | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von zweihunderttausend Franken. ... |
| T50-disclosure-03-B-K2 | alarm | alarm | no_alert | 0.50/0.07 | broken | 01:00-01:03 disclosure: Er schickt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.07 ('Insiderhandel') liegt unter 0.30 (Schwelle 0.45 minus Band 0.15). | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von 200'000 Franken. (Regel: dis... |
| T50-disclosure-review-K1 | review | no_alert | alarm | 0.02/0.53 | fixed | 00:00-00:42 access: Guten Tag, hier ist Sonja Tanner vom Kundendienst. Wie kann ich Ihnen helfen? Guten Tag, mein Name ist Nussbau. Ich rufe für meine Nachbarin an, Frau Ackermann, sie ist neunzig und... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-disclosure-review-K2 | review | no_alert | alarm | 0.02/0.58 | fixed | 00:43-01:22 documentation: Die Kontodaten sind vertraulich, darum kann ich Ihnen im Moment nichts dazu sagen. Ich kann aber die Frau Ackermann direkt anrufen. Sie gehört am Telefon sehr schlecht. Könn... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-documentation-01-A-K1 | alarm | review | alarm | 0.47/0.92 | same | 00:48-01:30 documentation: Ich möchte unbedingt die Wohnung. Sie ist perfekt für uns. Ich hatte Angst, dass es knapp wird. Die Lage ist ideal für die Schule. Das verstehe ich. Was möchten Sie mir noch... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-A-K2 | alarm | review | alarm | 0.47/0.84 | same | 00:52-01:18 documentation: Die Lage ist ideal für die Schule. Das verstehe ich. Was möchten Sie mir noch sagen? Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. Nein, ich sol... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die dritte Zeile nicht in die Notiz für die Kreditstelle zu schreiben. (Regel: documentation.review... |
| T50-documentation-01-B-K1 | no_alert | review | alarm | 0.47/0.91 | same | 00:53-01:17 documentation: Das verstehe ich. Was möchten Sie mir noch sagen? Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. Die soll das nicht sehen. Streichen Sie die ... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-B-K2 | no_alert | review | alarm | 0.47/0.91 | same | 00:36-01:29 documentation: Ja, das ist klar. Die Kreditstelle schaut sich das alles genau an. Nehmen wir an. Ja, die Kreditstelle bekommt das ganze Formular und meine Notiz zum Gespräch. Danach entsch... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-02-A-K2 | no_alert | review | alarm | 0.78/0.55 | same | 00:58-01:31 documentation: Die Zeile mit der Bürgschaft lassen Sie bitte in die Unterlagen für die Kreditprüfung weg. Das muss dort niemand wissen. Der Rest kann so bleiben. Ich habe Ihren Wunsch noti... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die Zeile mit der Bürgschaft in die Unterlagen für die Kreditprüfung nicht einzufügen. (Regel: docu... |
| T50-documentation-03-B-K1 | no_alert | alarm | review | 0.50/0.25 | same | 01:06-01:14 documentation: Den Punkt fünf möchte ich nicht in den Unterlagen für die Kreditabteilung haben. Bitte streichen Sie ihn, bevor Sie alles weiterleiten. Die Abteilung soll ihn nicht lesen. -... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte den Punkt fünf, der eine private Angelegenheit erwähnt, nicht in den Unterlagen für die Kreditabteilung haben und bi... |
| T50-documentation-03-B-K2 | no_alert | no_alert | review | 0.00/0.34 | broken | Prüfen (knapp unter Schwelle): Score 0.34 für 'Relevante Angabe verschweigen' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-documentation-trap-K1 | no_alert | alarm | no_alert | 0.95/0.17 | fixed | 00:18-00:26 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. Mein Lohn ist 7800 Franken im Monat. - Kein Alarm: höchster Score 0.17 ('Relevante Ang... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-documentation-trap-K2 | no_alert | alarm | review | 0.91/0.28 | same | 00:21-00:22 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. - keywords: Stichwort K06 «nicht protokollieren» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-multi-01-K1 | alarm | no_alert | review | 0.04/0.33 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. - patterns: Kundschaft liest möglichen Zugangscode (6 Zi... | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-01-K2 | alarm | no_alert | review | 0.05/0.30 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. Brechen Sie die Zahlung ab und starten Sie sie neu auf. ... | Kein Alarm: höchster Score 0.05 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-03-K1 | no_alert | review | no_alert | 0.47/0.06 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also der... - Kein Alarm: höchster Score 0.06 ('Zuständigkeit/Kontrolle umgehen') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostand von Herrn Wüttrichs Konto preis. (Regel: disclosure.review_1) |
| T50-multi-03-K2 | no_alert | review | no_alert | 0.47/0.07 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also dick. - Kein Alarm: höchster Score 0.07 ('Zuständigkeit/Kontrolle umgehen') liegt ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme des Mannes der Anruferin mit. (Regel: disclosure.review_1) |
| T50-multi-04-K2 | review | no_alert | review | 0.04/0.24 | fixed | 00:33-00:36 access: neun eins sechs drei null fünf. Dann wissen Sie, welcher es war. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-01-A-K1 | no_alert | no_alert | review | 0.00/0.25 | broken | Prüfen (knapp unter Schwelle): Score 0.25 für 'Zugangsinformation preisgegeben' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-01-A-K2 | no_alert | no_alert | alarm | 0.00/0.63 | broken | 00:33-01:08 access: Einen Moment, ich muss sie suchen. Wann war diese Buchung noch einmal? Am zwölf. September. Zweimal einhundertneunundachtzig Franken. Beide Buchungen sind am gleichen Abend gekomme... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-02-B-K1 | no_alert | alarm | no_alert | 0.50/0.08 | fixed | 00:58-01:06 disclosure: zwei, null, neun, zwei, sechs. Man steht dort nicht. Danke. Ich sehe eine Gutschrift vom Hotel über dreihundertvierzig Franken von gestern. - Kein Alarm: höchster Score 0.08 ('... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.82) - Der Berater gibt die Zahlungsumfrage des Hotels vor, die zu einem Betrag von 345 Franken beträgt. (Regel: disclosure.review_1) |
| T50-numbers-03-A-K1 | no_alert | no_alert | review | 0.00/0.21 | broken | Prüfen (knapp unter Schwelle): Score 0.21 für 'Zugangsinformation preisgegeben' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-03-A-K2 | no_alert | no_alert | review | 0.00/0.26 | broken | Prüfen (knapp unter Schwelle): Score 0.26 für 'Zugangsinformation preisgegeben' liegt zwischen 0.20 und der Schwelle 0.35. | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-A-K1 | no_alert | no_alert | alarm | 0.00/0.55 | broken | 00:52-01:22 splitting: Wie sollen die Zahlungen danach erfassen? Erfassen Sie, dass drei Zahlungen unter 10'000 Franken, damit die Bank keine zusätzliche Prüfung macht. Das ist mir am liebsten. Ich ha... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-A-K2 | no_alert | no_alert | alarm | 0.00/0.78 | broken | 00:36-01:10 splitting: Ja, die Angaben stehen alle auf dem Papier, das ich hier vor mir habe. Möchten Sie das Geld vom Sparkonto aufs Privatkonto verschieben, damit Sie zahlen können? Ja, bitte, das w... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-B-K1 | alarm | no_alert | alarm | 0.00/0.75 | fixed | 00:53-01:22 splitting: Ich kann die Zahlung danach erfassen. Erfassen Sie, dass drei Zahlungen unter 10'000 Franken, damit die Bank keine zusätzliche Prüfung macht. Das ist mir am liebsten. Ich habe d... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-B-K2 | alarm | no_alert | alarm | 0.00/0.78 | fixed | 00:33-01:10 splitting: Gut, haben Sie die Zahlungsangaben vor sich gehabt? Ja, die Angaben stehen alle auf dem Papier, das ich hier vor mir habe. Möchten Sie das Geld vom Sparkonto aufs Privatkonto ve... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-03-A-K2 | alarm | review | alarm | 0.84/0.97 | same | 00:00-00:36 splitting: Guten Tag, Herr Sutter, hier ist Rautgasser. Sie wollten eine Überweisung für einen Kauf besprechen. Ja, guten Tag. Ich kaufe ein Brauchsegelbud von einem Privatmann. Es kostet ... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass Überweisungen über fünfzigtausend Franken genau kontrolliert werden und er die Kontrolle umgehen möchte. (... |
| T50-splitting-03-B-K1 | no_alert | no_alert | review | 0.03/0.20 | broken | 00:54-00:55 splitting: Ich möchte das Boot aufteilen. Heute die Hälfte und morgen die andere Hälfte. Beide Male an das gleiche Konto des Verkäufers. - keywords: Stichwort K07 «aufteilen» (Aufteilen) | Kein Alarm: höchster Score 0.03 ('Zuständigkeit/Kontrolle umgehen') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-splitting-03-B-K2 | no_alert | no_alert | review | 0.03/0.25 | broken | 00:54-00:55 splitting: Darum möchte ich die Schaufsumme für das Boot aufteilen. Heute die Hälfte und morgen die andere Hälfte. Beide Malen als gleiches Konto des Verkäufers. - keywords: Stichwort K07 ... | Kein Alarm: höchster Score 0.03 ('Zuständigkeit/Kontrolle umgehen') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-trade-01-B-K1 | no_alert | no_alert | alarm | 0.00/0.71 | broken | 01:09-01:32 trade: Genau wegen der Nachricht von vorher möchte ich jetzt für zwölftausend Franken Aktien von Orimed kaufen. Bitte nehmen Sie den Auftrag heute noch auf. Ich habe Ihren Wunsch mit Betra... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-01-B-K2 | no_alert | no_alert | alarm | 0.00/0.70 | broken | 01:04-01:29 trade: Gut, das ist klar. Sagen Sie mir bitte genau, was ich für Sie aufnehmen soll. Genau wegen der Nachricht von vorher möchte ich jetzt für zwölftausend Franken aktive Orimed kaufen. We... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-02-A-K1 | no_alert | no_alert | alarm | 0.00/0.53 | broken | 00:00-00:40 trade: Guten Tag, Frau Brändli, hier spricht Marco Steiner. Sie wollten wegen einer Anlage und wegen Ihrer Tochter mit mir sprechen. Ja, genau. Meine Tochter wird bald sechzehn und ich wil... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-02-A-K2 | no_alert | no_alert | alarm | 0.00/0.50 | broken | 01:06-01:46 trade: Gut, dann sagen Sie mir bitte, was Sie bei Tavena konkret tun wollen. Wegen dem Ergebnis, das ich vorhin gesagt habe, will ich jetzt für neuntausend Franken Aktien von Tavena kaufen... | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-03-B-K1 | no_alert | no_alert | alarm | 0.00/0.62 | broken | 00:00-00:36 trade: Guten Tag, Herr Welty, hier ist Nina Kaduff. Sie haben heute Morgen angerufen, als ich in einer Sitzung war. Was kann ich für Sie machen? Guten Tag, Frau Kaduff. Es geht um zwei Sac... | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-03-B-K2 | no_alert | no_alert | alarm | 0.00/0.60 | broken | 00:00-00:36 trade: Guten Tag, Herr Welty, hier ist Nina Kadob. Sie haben heute Morgen angerufen, als ich in einer Sitzung war. Was kann ich für Sie machen? Guten Tag, Frau Kadob. Es geht um zwei Sache... | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-trade-review-K1 | review | review | alarm | 0.84/0.98 | same | 00:15-00:46 trade: Ein Freund der Garderube hat erzählt, dass die Kelsa ein neues Hörgerät herausbringt, das viel kleiner ist als alle anderen. Die Aktie soll darum stark steigen. Wissen Sie, wie er d... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die Kunde berichtet von Informationen, die ihr Freundin aus dem Fitnesscenter mitgeteilt hat. (Regel: trade.alarm_1) |
| T50-trade-review-K2 | review | review | alarm | 0.50/0.98 | same | 00:15-00:40 trade: Ein Freund der Garderube hat erzählt, dass die Kelsa ein neues Hörgerät herausbringt, das viel kleiner ist als alle anderen. Die Aktie soll darum stark steigen. Wissen Sie, wie er d... | facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde möchte Aktien von Kelsa für 5'000 Franken kaufen. (Regel: trade.review_1) |

## `q38q6_facts` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = q38q6_facts - champion

| metric | champion | q38q6_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.87 | +0.065 | [-0.048, +0.183] | no detectable difference |
| alarm AUC | 0.80 | 0.90 | +0.097 | [-0.028, +0.246] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = q38q6_facts - champion

| metric | champion | q38q6_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.76 | +0.063 | [-0.102, +0.227] | no detectable difference |
| alarm_f1 | 0.65 | 0.76 | +0.113 | [-0.068, +0.309] | no detectable difference |
| false_alarm_rate | 39% | 11% | -28pp | [-45pp, -13pp] | **real**: q38q6_facts better |
| miss_rate | 22% | 30% | +9pp | [-14pp, +31pp] | no detectable difference |
| accuracy | 61% | 74% | +13pp | [+2pp, +25pp] | **real**: q38q6_facts better |
| review_recall | 33% | 17% | -17pp | [-60pp, +25pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.79 | +0.095 | [-0.035, +0.230] | no detectable difference |

McNemar exact (calls): flag correct only-champion 10 vs only-q38q6_facts 21, p=0.0708; 3-class only-champion 10 vs only-q38q6_facts 23, p=0.0351.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = q38q6_facts - champion

| metric | champion | q38q6_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.78 | +0.096 | [-0.065, +0.269] | no detectable difference |
| alarm_f1 | 0.30 | 0.76 | +0.462 | [+0.186, +0.740] | **real**: q38q6_facts better |
| false_alarm_rate | 33% | 11% | -22pp | [-40pp, -8pp] | **real**: q38q6_facts better |
| miss_rate | 28% | 28% | +0pp | [-25pp, +24pp] | no detectable difference |
| accuracy | 48% | 74% | +26pp | [+12pp, +39pp] | **real**: q38q6_facts better |
| review_recall | 50% | 17% | -33pp | [-86pp, +33pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.80 | +0.111 | [-0.021, +0.246] | no detectable difference |

McNemar exact (calls): flag correct only-champion 10 vs only-q38q6_facts 22, p=0.0501; 3-class only-champion 8 vs only-q38q6_facts 34, p=0.0001.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = q38q6_facts - champion

| metric | champion | q38q6_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.72 | +0.005 | [-0.159, +0.161] | no detectable difference |
| alarm_f1 | 0.62 | 0.72 | +0.099 | [-0.053, +0.278] | no detectable difference |
| false_alarm_rate | 35% | 7% | -28pp | [-44pp, -13pp] | **real**: q38q6_facts better |
| miss_rate | 22% | 39% | +17pp | [-2pp, +38pp] | no detectable difference |
| accuracy | 60% | 73% | +13pp | [+1pp, +25pp] | **real**: q38q6_facts better |
| review_recall | 42% | 17% | -25pp | [-75pp, +33pp] | no detectable difference |
| flag_balanced_accuracy | 0.72 | 0.77 | +0.052 | [-0.065, +0.177] | no detectable difference |

McNemar exact (calls): flag correct only-champion 11 vs only-q38q6_facts 18, p=0.2649; 3-class only-champion 8 vs only-q38q6_facts 21, p=0.0241.

Flips (cv, 39 calls):

| call | expected | champion | q38q6_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-01-A-K2 | alarm | no_alert | review | 0.01/0.18 | fixed | Prüfen (knapp unter Schwelle): Score 0.18 für 'Zugangsinformation preisgegeben' liegt zwischen 0.15 und der Schwelle 0.30. | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-02-A-K1 | no_alert | review | no_alert | 0.15/0.00 | fixed | 00:54-01:02 access: Ich lese Ihnen die sechs Ziffern, die ich vorhin vor mir hatte, einfach vor. Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Kein Alarm: höchs... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die sechs Ziffern vor, die er vorher vor sich hatte. (Regel: access.no_alert) |
| T50-access-02-A-K2 | no_alert | alarm | no_alert | 0.85/0.00 | fixed | 00:57-01:02 access: Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.10 (Schwelle... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Wert von sechs Ziffern vor, obwohl der Berater ihn nicht benötigte. (Regel: access.alarm_1) |
| T50-access-02-B-K2 | alarm | alarm | review | 0.99/0.18 | same | 00:54-01:01 access: lese Ihnen die sechs Ziffern, die ich vorhin vor mir hatte, einfach vor. 5, 3, 8, 0, 1, 7. Das ist das zweite Feld gehört. - Prüfen (knapp unter Schwelle): Score 0.18 für 'Zugangsi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Aktivierungscode vor, der für das Online-Banking verwendet wird. (Regel: access.alarm_1) |
| T50-access-03-A-K1 | alarm | alarm | no_alert | 0.50/0.07 | broken | 01:06-01:13 disclosure: Die vier Ziffern aus dem Brief von vorhin lauten sechs, eins, neun, drei. Ist das die richtige Zahl für den Laden? - Kein Alarm: höchster Score 0.07 ('Zugangsinformation preisg... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.52) - Der Advisor gibt die vier Ziffern aus dem Brief an, die zu einer anderen Karte gehören. (Regel: disclosure.review_1) |
| T50-access-03-A-K2 | alarm | review | no_alert | 0.47/0.09 | broken | 01:06-01:18 access: Die vier Ziffern aus dem Brief von vorhin lauten sechs, eins, neun, drei. Ist das die richtige Zahl für den Laden? Bitte sagt ihr mir solche Zahlen nie am Telefon. Ihr könnt den Bi... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt die vier Ziffern aus dem Brief zum Laden am Telefon preis. (Regel: access.review_1) |
| T50-access-review-K2 | review | no_alert | review | 0.17/0.51 | fixed | 01:03-01:04 access: 492806. Vielleicht hilft Ihnen das ja. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | Kein Alarm: höchster Score 0.17 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-access-trap-K2 | no_alert | review | no_alert | 0.06/0.02 | fixed | 00:03-00:10 access: Guten Tag, Frau Stalder, hier ist der Daniel Vogt. Sie haben Ihr Passwort vergessen, habe ich gelesen. Ja, schlicht. Ich habe es aus letzter Woche geändert und jetzt fällt es mir n... | keywords: Stichwort K10 «Passwort» (Zugangswörter) |
| T50-disclosure-01-A-K1 | alarm | alarm | review | 0.85/0.85 | same | 00:22-00:23 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingetragen, sie haben dort also keinen Zugang. - keywords: Stichwort K11 «Vollmacht» (Drittperson und Berechtigu... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.78) - Die Mitarbeiterin sagt explizit, dass keine Vollmacht für die Klientin eingetragen ist. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-A-K2 | alarm | alarm | review | 0.90/0.84 | same | 00:22-00:23 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingefragen. Sie haben dort also keinen Zugang. - keywords: Stichwort K11 «Vollmacht» (Drittperson und Berechtigu... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.87) - Die Kunde sagt, dass sie keine Vollmacht für das Konto ihrer Mutter eingefragen hat. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-B-K1 | no_alert | review | no_alert | 0.47/0.04 | fixed | 00:05-01:03 disclosure: Guten Tag, hier ist Sandra Rohner. Ich rufe wegen dem Konto meiner Mutter an. Sie lebt seit dem Sommer im Pflegeheim. Die Heim schickt jeden Monat Rechnungen und ich möchte wis... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.72) - Die Kunde fragt nach den Rechnungen ihres Mütters vom Pflegeheim. (Regel: disclosure.review_1) |
| T50-disclosure-01-B-K2 | no_alert | review | no_alert | 0.47/0.04 | fixed | 00:56-01:00 disclosure: dem Konto ihrer Mutter liegen im Moment noch einundvierzigtausend Franken. - Kein Alarm: höchster Score 0.04 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Assistentin gibt Sandra Runger die aktuelle Kontostandsumme ihrer Mutter. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus Band ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K2 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 minus... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.95) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit 'Firma Konto von Nevalta ist seit letzter Woche... mit vier... |
| T50-disclosure-02-B-K1 | alarm | alarm | no_alert | 0.50/0.00 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.98) - Die Mitarbeiterin gibt den Kunden die aktuelle Kontostand von -4'000 Franken. (Regel: disclosure.review_1) |
| T50-disclosure-02-B-K2 | alarm | alarm | no_alert | 0.50/0.00 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.10 (Schwelle 0.25 m... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.89) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-03-B-K1 | alarm | alarm | no_alert | 0.50/0.00 | broken | 01:00-01:03 disclosure: Er legt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.10 (Schwelle 0.25 minus Band 0.15). | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von zweihunderttausend Franken. ... |
| T50-disclosure-trap-K1 | no_alert | alarm | no_alert | 0.96/0.02 | fixed | 00:04-00:20 disclosure: Guten Tag, hier ist Monika Eggimann. Ich möchte wissen, ob mein früherer Mann den Unterhalt schon überwiesen hat. Er hat sein Konto auch bei Ihnen. Haben Sie eine Vollmacht für... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (1.00) - Der Kunde gibt an, keine Vollmacht für das Konto seines früheren Mannes zu haben. (Regel: disclosure.alarm_1) |
| T50-disclosure-trap-K2 | no_alert | alarm | no_alert | 0.96/0.02 | fixed | 00:04-00:58 disclosure: Guten Tag, hier ist Monika Eggimann. Ich möchte wissen, ob mein früherer Mann den Unterhalt schon überwiesen hat. Er hat sein Konto auch bei Ihnen. Haben Sie eine Vollmacht für... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.99) - Der Kunde gibt an, dass er keine Vollmacht hat, und der Berater bestätigt, dass der Kunde zu dem Konto keine Angaben bekommen darf.... |
| T50-documentation-01-A-K1 | alarm | review | alarm | 0.47/0.87 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-A-K2 | alarm | review | alarm | 0.47/0.85 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die dritte Zeile nicht in die Notiz für die Kreditstelle zu schreiben. (Regel: documentation.review... |
| T50-documentation-01-B-K1 | no_alert | review | alarm | 0.47/0.84 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-02-A-K1 | no_alert | alarm | review | 0.86/0.06 | same | 00:59-01:05 documentation: Die Zeile mit der Bürgschaft lassen Sie bitte in den Unterlagen für die Kreditprüfung weg. Das muss dort niemand wissen. Der Rest kann so bleiben. - Prüfen (knapp unter Schw... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die Zeile mit der Bürgschaft in den Unterlagen für die Kreditprüfung wegzulassen. (Regel: documenta... |
| T50-documentation-03-B-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 01:06-01:14 documentation: Den Punkt fünf möchte ich nicht in den Unterlagen für die Kreditabteilung haben. Bitte streichen Sie ihn, bevor Sie alles weiterleiten. Die Abteilung soll ihn nicht lesen. -... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde möchte den Punkt fünf, der eine private Angelegenheit erwähnt, nicht in den Unterlagen für die Kreditabteilung haben und bi... |
| T50-documentation-trap-K1 | no_alert | alarm | no_alert | 0.95/0.02 | fixed | 00:18-00:26 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. Mein Lohn ist 7800 Franken im Monat. - Kein Alarm: höchster Score 0.02 ('Relevante Ang... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-documentation-trap-K2 | no_alert | alarm | no_alert | 0.91/0.02 | fixed | 00:18-00:23 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. - Kein Alarm: höchster Score 0.02 ('Relevante Angabe verschweigen') liegt unter 0.10 (... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-multi-01-K1 | alarm | no_alert | alarm | 0.04/0.20 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. - patterns: Kundschaft liest möglichen Zugangscode (6 Zi... | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-01-K2 | alarm | no_alert | alarm | 0.05/0.20 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. Brechen Sie die Zahlung ab und starten Sie sie neu auf. ... | Kein Alarm: höchster Score 0.05 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-03-K1 | no_alert | review | no_alert | 0.47/0.03 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also der... - Kein Alarm: höchster Score 0.03 ('Zuständigkeit/Kontrolle umgehen') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostand von Herrn Wüttrichs Konto preis. (Regel: disclosure.review_1) |
| T50-multi-03-K2 | no_alert | review | no_alert | 0.47/0.03 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also dick. - Kein Alarm: höchster Score 0.03 ('Auskunft an Dritte') liegt unter 0.05 (S... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme des Mannes der Anruferin mit. (Regel: disclosure.review_1) |
| T50-multi-04-K1 | review | review | no_alert | 0.47/0.04 | broken | 01:09-01:18 disclosure: Können Sie mir nicht wissend sagen, ob die Rechnung bezahlt ist? Die Kranke Kasse hat Ihnen schon eine Mahnung geschickt. Das kann ich Ihnen erst sagen, wenn die Prüfung abgesc... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Kunde fragt nach der Zahlung einer Rechnung für sein Altersheim-Verwandtes, ohne dass diese Information an ihn weitergegeben wird. (Re... |
| T50-numbers-02-B-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:58-01:06 disclosure: zwei, null, neun, zwei, sechs. Man steht dort nicht. Danke. Ich sehe eine Gutschrift vom Hotel über dreihundertvierzig Franken von gestern. - Kein Alarm: höchster Score 0.00 ('... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.82) - Der Berater gibt die Zahlungsumfrage des Hotels vor, die zu einem Betrag von 345 Franken beträgt. (Regel: disclosure.review_1) |
| T50-splitting-02-B-K1 | alarm | no_alert | alarm | 0.00/0.90 | fixed | Alarm: Score 0.90 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.30 bei Unsicherheit 0.13 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-B-K2 | alarm | no_alert | alarm | 0.00/0.76 | fixed | Alarm: Score 0.76 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.30 bei Unsicherheit 0.30 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-03-A-K2 | alarm | review | alarm | 0.84/0.84 | same | 00:29-00:30 splitting: Bei Ihnen werden Überweisungen über fünfzigtausend Franken intergenau angeschaut. Und ich möchte die Kontrolle umgehen. - keywords: Stichwort K08 «Kontrolle umgehen» (Kontrollum... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass Überweisungen über fünfzigtausend Franken genau kontrolliert werden und er die Kontrolle umgehen möchte. (... |
| T50-splitting-review-K1 | review | alarm | no_alert | 0.50/0.00 | broken | 00:37-00:44 splitting: Bitte teilen Sie die Rechnung für das Zelt in zwei gleiche Teile auf. Eine Zahlung heute und eine nächste Woche. So ist es mir lieber. - Kein Alarm: höchster Score 0.00 ('Zustän... | facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Kunde möchte die Rechnung für das Zelt in zwei gleiche Teile aufteilen. (Regel: splitting.review_1) |
| T50-splitting-review-K2 | review | alarm | no_alert | 0.50/0.00 | broken | 00:37-00:42 splitting: Bitte teilen Sie die Rechnung für das Zelt in zwei gleiche Teile auf. Eine Zahlung heute und eine nächste Woche. - Kein Alarm: höchster Score 0.00 ('Zuständigkeit/Kontrolle umge... | facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Kunde möchte die Rechnung für das Zelt in zwei gleiche Teile aufteilen. (Regel: splitting.review_1) |
| T50-trade-review-K1 | review | review | no_alert | 0.84/0.00 | broken | 00:06-00:11 trade: Ja, guten Tag. Ich habe am Samstag im Fitnesscenter ein bisschen über die Firma Kelsa gehört. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 min... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die Kunde berichtet von Informationen, die ihr Freundin aus dem Fitnesscenter mitgeteilt hat. (Regel: trade.alarm_1) |
| T50-trade-review-K2 | review | review | no_alert | 0.50/0.00 | broken | 01:03-01:10 trade: Wegen der Neuigkeit, unserem Fitnesscenter will ich jetzt für fünftausend Franken Aktien von Kelsa kaufen. Bitte nehmen Sie das auf. - Kein Alarm: höchster Score 0.00 ('Insiderhande... | facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde möchte Aktien von Kelsa für 5'000 Franken kaufen. (Regel: trade.review_1) |

## `q38q6_general` vs `champion`

**Threshold-free (ROC AUC of the call score)** - 100 calls; difference = q38q6_general - champion

| metric | champion | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.80 | 0.83 | +0.024 | [-0.069, +0.130] | no detectable difference |
| alarm AUC | 0.80 | 0.81 | +0.006 | [-0.125, +0.148] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = q38q6_general - champion

| metric | champion | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.70 | 0.73 | +0.032 | [-0.093, +0.170] | no detectable difference |
| alarm_f1 | 0.65 | 0.62 | -0.026 | [-0.187, +0.142] | no detectable difference |
| false_alarm_rate | 39% | 37% | -2pp | [-26pp, +21pp] | no detectable difference |
| miss_rate | 22% | 17% | -4pp | [-30pp, +21pp] | no detectable difference |
| accuracy | 61% | 62% | +1pp | [-10pp, +12pp] | no detectable difference |
| review_recall | 33% | 0% | -33pp | [-67pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.70 | 0.73 | +0.031 | [-0.091, +0.159] | no detectable difference |

McNemar exact (calls): flag correct only-champion 19 vs only-q38q6_general 22, p=0.7552; 3-class only-champion 21 vs only-q38q6_general 22, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = q38q6_general - champion

| metric | champion | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.68 | 0.75 | +0.070 | [-0.083, +0.230] | no detectable difference |
| alarm_f1 | 0.30 | 0.66 | +0.357 | [+0.114, +0.611] | **real**: q38q6_general better |
| false_alarm_rate | 33% | 17% | -17pp | [-35pp, +2pp] | no detectable difference |
| miss_rate | 28% | 28% | +0pp | [-27pp, +26pp] | no detectable difference |
| accuracy | 48% | 70% | +22pp | [+8pp, +34pp] | **real**: q38q6_general better |
| review_recall | 50% | 8% | -42pp | [-86pp, +6pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.78 | +0.083 | [-0.037, +0.208] | no detectable difference |

McNemar exact (calls): flag correct only-champion 15 vs only-q38q6_general 24, p=0.1996; 3-class only-champion 10 vs only-q38q6_general 32, p=0.0009.

**Fixed threshold** - 100 calls / 50 dialogues (32 resampling units: twins together); difference = q38q6_general - champion

| metric | champion | q38q6_general | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.71 | 0.72 | +0.004 | [-0.126, +0.153] | no detectable difference |
| alarm_f1 | 0.62 | 0.69 | +0.067 | [-0.077, +0.240] | no detectable difference |
| false_alarm_rate | 35% | 24% | -11pp | [-33pp, +10pp] | no detectable difference |
| miss_rate | 22% | 28% | +7pp | [-18pp, +30pp] | no detectable difference |
| accuracy | 60% | 68% | +8pp | [-4pp, +20pp] | no detectable difference |
| review_recall | 42% | 0% | -42pp | [-75pp, -12pp] | **real**: champion better |
| flag_balanced_accuracy | 0.72 | 0.74 | +0.023 | [-0.092, +0.152] | no detectable difference |

McNemar exact (calls): flag correct only-champion 17 vs only-q38q6_general 20, p=0.7428; 3-class only-champion 14 vs only-q38q6_general 22, p=0.243.

Flips (cv, 53 calls):

| call | expected | champion | q38q6_general | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| T50-access-01-A-K1 | alarm | no_alert | alarm | 0.01/0.99 | fixed | Alarm: Score 0.99 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-01-A-K2 | alarm | no_alert | alarm | 0.01/0.99 | fixed | Alarm: Score 0.99 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.01 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-01-B-K1 | no_alert | no_alert | alarm | 0.00/0.42 | broken | Alarm: Score 0.42 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-01-B-K2 | no_alert | no_alert | alarm | 0.00/0.74 | broken | Alarm: Score 0.74 für 'Auskunft an Dritte' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-02-A-K2 | no_alert | alarm | review | 0.85/0.14 | same | 00:57-01:02 access: Fünf, drei, acht, null, eins, sieben. Sagen Sie mir, ob das ins zweite Feld gehört. - Prüfen (knapp unter Schwelle): Score 0.14 für 'Zugangsinformation preisgegeben' liegt zwischen... | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Wert von sechs Ziffern vor, obwohl der Berater ihn nicht benötigte. (Regel: access.alarm_1) |
| T50-access-03-A-K2 | alarm | review | alarm | 0.47/0.76 | same | 00:23-00:23 access: Die neue Karte ist letzte Woche gekommen und ich benutze sie seit gestern mit der PIN aus dem Brief, - keywords: Stichwort K10 «PIN» (Zugangswörter) | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde gibt die vier Ziffern aus dem Brief zum Laden am Telefon preis. (Regel: access.review_1) |
| T50-access-03-B-K1 | no_alert | no_alert | alarm | 0.02/0.69 | broken | 00:21-00:22 access: Die alte Scharte ist seit letztem Monat gesperrt und die PIN aus dem Brief, der hier vor mir liegt, gilt nicht mehr. - keywords: Stichwort K10 «PIN» (Zugangswörter) | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-03-B-K2 | no_alert | no_alert | alarm | 0.02/0.76 | broken | 00:21-00:22 access: Die alte Scharte ist seit letztem Monat gesperrt und die PIN aus dem Brief, der hier vor mir liegt, gilt nicht mehr. - keywords: Stichwort K10 «PIN» (Zugangswörter) | Kein Alarm: höchster Score 0.02 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-access-review-K1 | review | review | alarm | 0.81/0.54 | same | 01:02-01:04 access: vier, neun, zwei, acht, null, sechs. Vielleicht hilft Ihnen das ja. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las den Ziffernreihen des Zettels vor, obwohl es unklar war, ob es der aktuelle PIN ist. (Regel: access.alarm_1) |
| T50-access-review-K2 | review | no_alert | alarm | 0.17/0.38 | fixed | 01:03-01:04 access: 492806. Vielleicht hilft Ihnen das ja. - patterns: Kundschaft liest möglichen Zugangscode (6 Ziffern) vor, Stichwort «Code» | Kein Alarm: höchster Score 0.17 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-access-trap-K2 | no_alert | review | no_alert | 0.06/0.02 | fixed | 00:03-00:10 access: Guten Tag, Frau Stalder, hier ist der Daniel Vogt. Sie haben Ihr Passwort vergessen, habe ich gelesen. Ja, schlicht. Ich habe es aus letzter Woche geändert und jetzt fällt es mir n... | keywords: Stichwort K10 «Passwort» (Zugangswörter) |
| T50-disclosure-01-A-K1 | alarm | alarm | no_alert | 0.85/0.15 | broken | 00:20-00:26 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingetragen, sie haben dort also keinen Zugang. - Kein Alarm: höchster Score 0.15 ('Auskunft an Dritte') liegt un... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.78) - Die Mitarbeiterin sagt explizit, dass keine Vollmacht für die Klientin eingetragen ist. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-A-K2 | alarm | alarm | no_alert | 0.90/0.14 | broken | 00:20-00:26 disclosure: Für das Konto ihrer Mutter ist bei uns keine Vollmacht für sie eingefragen. Sie haben dort also keinen Zugang. - Kein Alarm: höchster Score 0.14 ('Auskunft an Dritte') liegt un... | facts: Fakt: Keine Vollmacht/Berechtigung festgestellt = ja (0.87) - Die Kunde sagt, dass sie keine Vollmacht für das Konto ihrer Mutter eingefragen hat. (Regel: disclosure.alarm_1) |
| T50-disclosure-01-B-K1 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:05-01:03 disclosure: Guten Tag, hier ist Sandra Rohner. Ich rufe wegen dem Konto meiner Mutter an. Sie lebt seit dem Sommer im Pflegeheim. Die Heim schickt jeden Monat Rechnungen und ich möchte wis... | facts: Fakt: Auskunft über Drittperson verlangt = ja (0.72) - Die Kunde fragt nach den Rechnungen ihres Mütters vom Pflegeheim. (Regel: disclosure.review_1) |
| T50-disclosure-01-B-K2 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:56-01:00 disclosure: dem Konto ihrer Mutter liegen im Moment noch einundvierzigtausend Franken. - Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Assistentin gibt Sandra Runger die aktuelle Kontostandsumme ihrer Mutter. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K1 | no_alert | alarm | no_alert | 0.50/0.01 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-02-A-K2 | no_alert | alarm | no_alert | 0.50/0.01 | fixed | 00:55-01:00 disclosure: Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 ... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.95) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit 'Firma Konto von Nevalta ist seit letzter Woche... mit vier... |
| T50-disclosure-02-B-K1 | alarm | alarm | no_alert | 0.50/0.01 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.01 ('Zuständigkeit/Kontrolle umgehen') liegt unter 0.50 (... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.98) - Die Mitarbeiterin gibt den Kunden die aktuelle Kontostand von -4'000 Franken. (Regel: disclosure.review_1) |
| T50-disclosure-02-B-K2 | alarm | alarm | no_alert | 0.50/0.00 | broken | 00:55-01:00 disclosure: Die Firma Konto von Nevalta ist seit letzter Woche... ...mit viertausend Franken im Minus. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.89) - Die Mitarbeiterin gibt dem Kunden die aktuelle Kontostandsumme mit minus 4000 Franken preis. (Regel: disclosure.review_1) |
| T50-disclosure-03-A-K1 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über ein Konto oder Kredit, insbesondere die noch stehende Hypothek ... |
| T50-disclosure-03-A-K2 | no_alert | alarm | no_alert | 0.50/0.00 | fixed | 00:55-01:01 disclosure: Ihr Vater hatte auf dem Spanken und auf dem Haus liegt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Die Mitarbeiterin gibt dem Anrufer konkrete Informationen über den Hypothekenschuldner, insbesondere den Betrag der Hypothek. ... |
| T50-disclosure-03-B-K1 | alarm | alarm | no_alert | 0.50/0.01 | broken | 01:00-01:03 disclosure: Er legt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von zweihunderttausend Franken. ... |
| T50-disclosure-03-B-K2 | alarm | alarm | no_alert | 0.50/0.00 | broken | 01:00-01:03 disclosure: Er schickt bei uns noch eine Hypothek von zweihunderttausend Franken. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.99) - Der Berater gibt konkrete Informationen über ein Konto oder Kredit, insbesondere die Hypothek von 200'000 Franken. (Regel: dis... |
| T50-disclosure-review-K1 | review | no_alert | alarm | 0.02/0.84 | fixed | 01:17-01:18 disclosure: Dann schicken wir ein Formular für eine richtige Vollmacht, das Frau Ackermann unterschrieben kann. Damit geht es dann sicher. - keywords: Stichwort K11 «Vollmacht» (Drittperso... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-disclosure-review-K2 | review | no_alert | alarm | 0.02/0.72 | fixed | 01:17-01:18 disclosure: Dann schicken wir Ihnen ein Formular für eine richtige Vollmacht, das die Frau Ackermann unterschrieben kann. Damit geht es Ihnen sicher. - keywords: Stichwort K11 «Vollmacht» ... | Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-documentation-01-A-K1 | alarm | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-A-K2 | alarm | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die dritte Zeile nicht in die Notiz für die Kreditstelle zu schreiben. (Regel: documentation.review... |
| T50-documentation-01-B-K1 | no_alert | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-01-B-K2 | no_alert | review | alarm | 0.47/0.96 | same | 00:58-00:59 documentation: Bitte nehmen Sie die dritte Zeile nicht in die Notiz für die Kreditstelle auf. - keywords: Stichwort K06 «nicht in die Notiz» (Dokumentation auslassen) | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass die dritte Zeile nicht in die Notiz für die Kreditstelle aufgenommen wird. (Regel: documentation.rev... |
| T50-documentation-02-A-K2 | no_alert | review | alarm | 0.78/1.00 | same | 00:58-01:05 documentation: Die Zeile mit der Bürgschaft lassen Sie bitte in die Unterlagen für die Kreditprüfung weg. Das muss dort niemand wissen. Der Rest kann so bleiben. - Alarm: Score 1.00 für 'R... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde bittet den Mitarbeiter, die Zeile mit der Bürgschaft in die Unterlagen für die Kreditprüfung nicht einzufügen. (Regel: docu... |
| T50-documentation-03-B-K2 | no_alert | no_alert | alarm | 0.00/0.49 | broken | Alarm: Score 0.49 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-documentation-trap-K1 | no_alert | alarm | no_alert | 0.95/0.07 | fixed | 00:18-00:26 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. Mein Lohn ist 7800 Franken im Monat. - Kein Alarm: höchster Score 0.07 ('Relevante Ang... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-documentation-trap-K2 | no_alert | alarm | no_alert | 0.91/0.08 | fixed | 00:18-00:23 documentation: Nein, das war ein Versprechen. Bitte nicht protokollieren, was ich vorhin gesagt habe. - Kein Alarm: höchster Score 0.08 ('Relevante Angabe verschweigen') liegt unter 0.10 (... | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Der Kunde fordert explizit, dass ein Versprechen nicht protokolliert wird. (Regel: documentation.alarm_1) |
| T50-multi-01-K1 | alarm | no_alert | alarm | 0.04/0.94 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. - patterns: Kundschaft liest möglichen Zugangscode (6 Zi... | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-01-K2 | alarm | no_alert | alarm | 0.05/0.95 | fixed | 00:59-01:05 access: Ich lese Ihnen die TAN von vorhin einfach vor. drei, acht, eins, sieben, vier, zwei. Bitte lassen Sie mir nie eine TAN vor. Brechen Sie die Zahlung ab und starten Sie sie neu auf. ... | Kein Alarm: höchster Score 0.05 ('Zugangsinformation preisgegeben') liegt unter 0.70 (Schwelle 0.85 minus Band 0.15). |
| T50-multi-03-K1 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also der... - Kein Alarm: höchster Score 0.02 ('Zuständigkeit/Kontrolle umgehen') liegt... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostand von Herrn Wüttrichs Konto preis. (Regel: disclosure.review_1) |
| T50-multi-03-K2 | no_alert | review | no_alert | 0.47/0.02 | fixed | 00:31-00:37 disclosure: Auf dem Konto Ihres Mannes liegen momentan neuntausendzweihundert Franken. Die Miete ist also dick. - Kein Alarm: höchster Score 0.02 ('Auskunft an Dritte') liegt unter 0.10 (S... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme des Mannes der Anruferin mit. (Regel: disclosure.review_1) |
| T50-multi-04-K1 | review | review | alarm | 0.47/0.30 | same | 00:58-01:02 disclosure: Ob Ihre Kranke Kasse bezahlt ist. Sie hat mir dafür vor einer Woche eine Vollmacht unterschrieben. Die Vollmacht ist angekommen, aber unsere Rechtsabteilung prüft sie noch. - k... | facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Kunde fragt nach der Zahlung einer Rechnung für sein Altersheim-Verwandtes, ohne dass diese Information an ihn weitergegeben wird. (Re... |
| T50-multi-04-K2 | review | no_alert | alarm | 0.04/0.40 | fixed | 00:58-01:01 disclosure: Ob Ihre Kranke Kasse bezahlt ist. Sie hat mir den Vorfahrerwochen eine Vollmacht unterschrieben. Die Vollmacht ist angekommen, aber unsere Rechtsabteilung prüft sie noch. - key... | Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-01-A-K1 | no_alert | no_alert | alarm | 0.00/0.59 | broken | Alarm: Score 0.59 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-01-A-K2 | no_alert | no_alert | alarm | 0.00/0.71 | broken | Alarm: Score 0.71 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-02-B-K1 | no_alert | alarm | no_alert | 0.50/0.01 | fixed | 00:58-01:06 disclosure: zwei, null, neun, zwei, sechs. Man steht dort nicht. Danke. Ich sehe eine Gutschrift vom Hotel über dreihundertvierzig Franken von gestern. - Kein Alarm: höchster Score 0.01 ('... | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (0.82) - Der Berater gibt die Zahlungsumfrage des Hotels vor, die zu einem Betrag von 345 Franken beträgt. (Regel: disclosure.review_1) |
| T50-numbers-03-A-K1 | no_alert | no_alert | alarm | 0.00/0.28 | broken | Alarm: Score 0.28 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-numbers-03-A-K2 | no_alert | no_alert | alarm | 0.00/0.49 | broken | Alarm: Score 0.49 für 'Zugangsinformation preisgegeben' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-A-K1 | no_alert | no_alert | alarm | 0.00/0.89 | broken | Alarm: Score 0.89 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-A-K2 | no_alert | no_alert | alarm | 0.00/0.95 | broken | Alarm: Score 0.95 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-B-K1 | alarm | no_alert | alarm | 0.00/0.87 | fixed | Alarm: Score 0.87 für 'Relevante Angabe verschweigen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-02-B-K2 | alarm | no_alert | alarm | 0.00/0.51 | fixed | Alarm: Score 0.51 für 'Zuständigkeit/Kontrolle umgehen' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.35). | Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). |
| T50-splitting-03-A-K2 | alarm | review | alarm | 0.84/0.97 | same | 00:29-00:30 splitting: Bei Ihnen werden Überweisungen über fünfzigtausend Franken intergenau angeschaut. Und ich möchte die Kontrolle umgehen. - keywords: Stichwort K08 «Kontrolle umgehen» (Kontrollum... | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde sagt, dass Überweisungen über fünfzigtausend Franken genau kontrolliert werden und er die Kontrolle umgehen möchte. (... |
| T50-splitting-review-K1 | review | alarm | no_alert | 0.50/0.47 | broken | 00:37-00:44 splitting: Bitte teilen Sie die Rechnung für das Zelt in zwei gleiche Teile auf. Eine Zahlung heute und eine nächste Woche. So ist es mir lieber. - Kein Alarm: höchster Score 0.47 ('Releva... | facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Kunde möchte die Rechnung für das Zelt in zwei gleiche Teile aufteilen. (Regel: splitting.review_1) |
| T50-splitting-review-K2 | review | alarm | no_alert | 0.50/0.36 | broken | 00:37-00:42 splitting: Bitte teilen Sie die Rechnung für das Zelt in zwei gleiche Teile auf. Eine Zahlung heute und eine nächste Woche. - Kein Alarm: höchster Score 0.36 ('Relevante Angabe verschweige... | facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Kunde möchte die Rechnung für das Zelt in zwei gleiche Teile aufteilen. (Regel: splitting.review_1) |
| T50-trade-review-K1 | review | review | alarm | 0.84/0.91 | same | 00:06-00:11 trade: Ja, guten Tag. Ich habe am Samstag im Fitnesscenter ein bisschen über die Firma Kelsa gehört. - Alarm: Score 0.91 für 'Insiderhandel' >= Schwelle 0.25 bei Unsicherheit 0.00 (max. 0.... | facts: Fakt: Begründet mit nicht öffentlicher Insider-Information = ja (0.60) - Die Kunde berichtet von Informationen, die ihr Freundin aus dem Fitnesscenter mitgeteilt hat. (Regel: trade.alarm_1) |
| T50-trade-review-K2 | review | review | alarm | 0.50/0.83 | same | 01:03-01:10 trade: Wegen der Neuigkeit, unserem Fitnesscenter will ich jetzt für fünftausend Franken Aktien von Kelsa kaufen. Bitte nehmen Sie das auf. - Alarm: Score 0.83 für 'Insiderhandel' >= Schwe... | facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Der Kunde möchte Aktien von Kelsa für 5'000 Franken kaufen. (Regel: trade.review_1) |

