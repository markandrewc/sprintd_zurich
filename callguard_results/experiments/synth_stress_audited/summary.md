# Experiment `synth_stress_audited`

AUDITED subset (data_synth/v1/audit.json, invalid + doubtful scripts removed) of the synthetic stress test (ORACLE text) - v1 checks vs facts vs judge+facts

RQ: RQ5, RQ10 · base profile `synth-oracle` · split **external** · baseline `v1` · commit 1fd19e75c0 (dirty) · 2026-10-10T04:01:04+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 65 calls** (prevalence of alarm|review 62%): flag-all = flag F1 0.76, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 37%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 38%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.76 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

AUC is not decision-consistent: it ranks the fused call score, but the label also comes from review rules that ignore the threshold (uncertainty escalation, "undetermined" verdicts, review band), so no threshold may realise the trade-offs the ROC curve suggests. Read it as discrimination of the score, and judge operating points by CV@FAR20 and the FAR floor.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| src | 0.89 [0.80, 0.96] | 0.90 [0.83, 0.96] | 40/25 | **ORACLE** |
| v1 | 0.89 [0.80, 0.96] | 0.90 [0.83, 0.96] | 40/25 | **ORACLE**, re-fusion of src |
| facts_only | 0.84 [0.75, 0.93] | 0.80 [0.71, 0.88] | 40/25 | **ORACLE**, re-fusion of src |
| judge_facts | 0.94 [0.88, 0.98] | 0.89 [0.83, 0.95] | 40/25 | **ORACLE**, re-fusion of src |
| kwpat_facts | 0.92 [0.85, 0.97] | 0.83 [0.75, 0.90] | 40/25 | **ORACLE**, re-fusion of src |
| hybrid | 0.83 [0.73, 0.91] | 0.78 [0.68, 0.87] | 40/25 | **ORACLE**, re-fusion of src |
| facts_blind_only | 0.77 [0.66, 0.88] | 0.74 [0.66, 0.83] | 40/25 | **ORACLE**, re-fusion of src |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | 65 | 0.83 [0.77, 0.88] | 73% | 95% | 56% [36%, 76%] | 5% [0%, 12%] | 0.72 | 62% | 60% | 0.69 [0.59, 0.80] | **ORACLE**, re-fusion of src |
| facts_only | 65 | 0.78 [0.65, 0.88] | 96% | 65% | 4% [0%, 13%] | 35% [20%, 50%] | 0.63 | 0% | 62% | 0.81 [0.71, 0.89] | **ORACLE**, re-fusion of src |
| judge_facts | 65 | 0.82 [0.75, 0.89] | 74% | 92% | 52% [32%, 73%] | 8% [0%, 16%] | 0.61 | 75% | 54% | 0.70 [0.59, 0.81] | **ORACLE**, re-fusion of src |
| kwpat_facts | 65 | 0.83 [0.74, 0.92] | 94% | 75% | 8% [0%, 20%] | 25% [12%, 38%] | 0.33 | 62% | 58% | 0.83 [0.75, 0.92] | **ORACLE**, re-fusion of src |
| hybrid | 65 | 0.76 [0.63, 0.86] | 87% | 68% | 16% [4%, 32%] | 32% [18%, 49%] | 0.63 | 6% | 58% | 0.76 [0.65, 0.85] | **ORACLE**, re-fusion of src |
| facts_blind_only | 65 | 0.75 [0.61, 0.86] | 84% | 68% | 20% [4%, 38%] | 32% [15%, 51%] | 0.61 | 0% | 57% | 0.74 [0.63, 0.85] | **ORACLE**, re-fusion of src |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| src | 65 | 0.81 [0.75, 0.87] | 73% | 92% | 56% [36%, 76%] | 8% [0%, 16%] | 0.61 | 62% | 54% | 0.68 [0.58, 0.78] | **ORACLE** |
| v1 | 65 | 0.81 [0.75, 0.87] | 73% | 92% | 56% [36%, 76%] | 8% [0%, 16%] | 0.61 | 62% | 54% | 0.68 [0.58, 0.78] | **ORACLE**, re-fusion of src |
| facts_only | 65 | 0.78 [0.65, 0.88] | 96% | 65% | 4% [0%, 13%] | 35% [20%, 50%] | 0.55 | 12% | 58% | 0.81 [0.71, 0.89] | **ORACLE**, re-fusion of src |
| judge_facts | 65 | 0.83 [0.76, 0.90] | 76% | 92% | 48% [29%, 69%] | 8% [0%, 16%] | 0.08 | 81% | 42% | 0.72 [0.61, 0.83] | **ORACLE**, re-fusion of src |
| kwpat_facts | 65 | 0.83 [0.74, 0.92] | 94% | 75% | 8% [0%, 20%] | 25% [12%, 38%] | 0.33 | 62% | 58% | 0.83 [0.75, 0.92] | **ORACLE**, re-fusion of src |
| hybrid | 65 | 0.76 [0.63, 0.86] | 87% | 68% | 16% [4%, 32%] | 32% [18%, 49%] | 0.55 | 19% | 55% | 0.76 [0.65, 0.85] | **ORACLE**, re-fusion of src |
| facts_blind_only | 65 | 0.73 [0.59, 0.85] | 84% | 65% | 20% [4%, 38%] | 35% [18%, 53%] | 0.29 | 62% | 52% | 0.72 [0.62, 0.83] | **ORACLE**, re-fusion of src |

**Can the cap be met at all?** The review rules (uncertainty escalation, "undetermined" verdicts, review band, abstention) flag calls whatever the threshold. *FAR floor* = FAR at threshold 1.0 on these calls (review rules only); above 20% no threshold reaches the cap. *Folds cap reachable* = training folds where some threshold met the cap; the other folds fell back to the lowest-FAR threshold (marked `!` in the fold thresholds below). *Compliant* = out-of-fold CV@FAR20 FAR <= 20%.

| variant | FAR floor (t=1.0) | folds cap reachable | CV@FAR20 FAR | compliant | back-filled (commit, config hash) |
|---|---|---|---|---|---|
| src | 48% (!) | 0/5 | 56% | **no** | cv_far @ 1fd19e75c0 cfg c11ba3ebfb28bb45, far_floor @ 1fd19e75c0 cfg c11ba3ebfb28bb45 |
| v1 | 48% (!) | 0/5 | 56% | **no** | - |
| facts_only | 4% | 5/5 | 4% | yes | - |
| judge_facts | 44% (!) | 0/5 | 48% | **no** | - |
| kwpat_facts | 4% | 5/5 | 8% | yes | - |
| hybrid | 16% | 4/5 | 16% | yes | - |
| facts_blind_only | 20% | 3/5 | 20% | yes | - |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| src | 65 | 0.84 [0.78, 0.89] | 75% | 95% | 52% [32%, 72%] | 5% [0%, 12%] | 0.76 | 62% | 63% | 0.71 [0.61, 0.82] | **ORACLE** |
| v1 | 65 | 0.84 [0.78, 0.89] | 75% | 95% | 52% [32%, 72%] | 5% [0%, 12%] | 0.76 | 62% | 63% | 0.71 [0.61, 0.82] | **ORACLE**, re-fusion of src |
| facts_only | 65 | 0.78 [0.65, 0.88] | 96% | 65% | 4% [0%, 13%] | 35% [20%, 50%] | 0.61 | 56% | 68% | 0.81 [0.71, 0.89] | **ORACLE**, re-fusion of src |
| judge_facts | 65 | 0.84 [0.77, 0.90] | 77% | 92% | 44% [25%, 64%] | 8% [0%, 16%] | 0.61 | 75% | 57% | 0.74 [0.63, 0.85] | **ORACLE**, re-fusion of src |
| kwpat_facts | 65 | 0.78 [0.65, 0.88] | 96% | 65% | 4% [0%, 13%] | 35% [20%, 50%] | 0.33 | 56% | 58% | 0.81 [0.71, 0.89] | **ORACLE**, re-fusion of src |
| hybrid | 65 | 0.76 [0.63, 0.86] | 87% | 68% | 16% [4%, 32%] | 32% [18%, 49%] | 0.61 | 62% | 65% | 0.76 [0.65, 0.85] | **ORACLE**, re-fusion of src |
| facts_blind_only | 65 | 0.75 [0.61, 0.86] | 84% | 68% | 20% [4%, 38%] | 32% [15%, 51%] | 0.40 | 62% | 55% | 0.74 [0.63, 0.85] | **ORACLE**, re-fusion of src |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| src | 0.55 | - | - (FAR20: 0.85!, 0.85!, 0.40!, 0.85!, 1.00!) | 158.0 | asr 0.0, diarize 0.0, checks 158.0 | 158.0 | 56.6 | 0 | 0 | 1fd19e75c0 |
| v1 | 0.55 | 0.70 | 0.70, 0.70, 0.40, 0.70, 0.80 (FAR20: 0.85!, 0.85!, 0.40!, 0.85!, 1.00!) | 0.0 | asr 0.0, diarize 0.0, checks 158.0 | 158.0 | 56.6 | 0 | 0 | 1fd19e75c0 |
| facts_only | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20, 0.35 (FAR20: 0.20, 0.20, 0.20, 0.20, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 158.0 | 40.2 | 21.3 | 0 | 0 | 1fd19e75c0 |
| judge_facts | 0.55 | 0.30 | 0.30, 0.65, 0.30, 0.30, 0.35 (FAR20: 0.35!, 1.00!, 1.00!, 1.00!, 1.00!) | 0.0 | asr 0.0, diarize 0.0, checks 158.0 | 84.8 | 26.3 | 0 | 0 | 1fd19e75c0 |
| kwpat_facts | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20, 0.20 (FAR20: 0.20, 0.20, 0.20, 0.20, 0.20) | 0.0 | asr 0.0, diarize 0.0, checks 158.0 | 40.2 | 21.3 | 0 | 0 | 1fd19e75c0 |
| hybrid | 0.55 | 0.20 | 0.20, 0.20, 0.20, 0.20, 0.35 (FAR20: 0.20!, 0.20, 0.20, 0.20, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 158.0 | 84.8 | 26.3 | 0 | 0 | 1fd19e75c0 |
| facts_blind_only | 0.55 | 0.35 | 0.35, 0.35, 0.35, 0.35, 0.35 (FAR20: 0.95!, 0.95, 0.95!, 0.95, 1.00) | 0.0 | asr 0.0, diarize 0.0, checks 158.0 | 41.5 | 25.2 | 0 | 0 | 1fd19e75c0 |

`!` after a FAR20 fold threshold: no threshold met the 20% cap on that fold's training folds; the lowest-FAR threshold was used (fallback).

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe0 | clean | noisy |
|---|---|---|---|
| src | 0.84 / 52% / 5% | 0.84 / 52% / 5% | - |
| v1 | 0.83 / 56% / 5% | 0.83 / 56% / 5% | - |
| facts_only | 0.78 / 4% / 35% | 0.78 / 4% / 35% | - |
| judge_facts | 0.82 / 52% / 8% | 0.82 / 52% / 8% | - |
| kwpat_facts | 0.83 / 8% / 25% | 0.83 / 8% / 25% | - |
| hybrid | 0.76 / 16% / 32% | 0.76 / 16% / 32% | - |
| facts_blind_only | 0.75 / 20% / 32% | 0.75 / 20% / 32% | - |

## `src` vs `v1` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 65 calls; difference = src - v1

| metric | v1 | src | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.89 | 0.89 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.90 | 0.90 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = src - v1

| metric | v1 | src | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.81 | 0.81 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.61 | 0.61 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 56% | 56% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 54% | 54% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.68 | 0.68 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-v1 0 vs only-src 0, p=1.0; 3-class only-v1 0 vs only-src 0, p=1.0.

**Fixed threshold** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = src - v1

| metric | v1 | src | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.76 | 0.76 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 52% | 52% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 5% | 5% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 63% | 63% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.71 | 0.71 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-v1 0 vs only-src 0, p=1.0; 3-class only-v1 0 vs only-src 0, p=1.0.

No call changes its label (fixed).

## `facts_only` vs `v1` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 65 calls; difference = facts_only - v1

| metric | v1 | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.89 | 0.84 | -0.045 | [-0.161, +0.071] | no detectable difference |
| alarm AUC | 0.90 | 0.80 | -0.103 | [-0.210, +0.002] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = facts_only - v1

| metric | v1 | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.83 | 0.78 | -0.050 | [-0.189, +0.073] | no detectable difference |
| alarm_f1 | 0.72 | 0.63 | -0.092 | [-0.250, +0.073] | no detectable difference |
| false_alarm_rate | 56% | 4% | -52pp | [-75pp, -30pp] | **real**: facts_only better |
| miss_rate | 5% | 35% | +30pp | [+14pp, +48pp] | **real**: v1 better |
| accuracy | 60% | 62% | +2pp | [-11pp, +16pp] | no detectable difference |
| review_recall | 62% | 0% | -62pp | [-86pp, -38pp] | **real**: v1 better |
| flag_balanced_accuracy | 0.69 | 0.81 | +0.110 | [-0.035, +0.252] | no detectable difference |

McNemar exact (calls): flag correct only-v1 14 vs only-facts_only 15, p=1.0; 3-class only-v1 17 vs only-facts_only 18, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = facts_only - v1

| metric | v1 | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.81 | 0.78 | -0.037 | [-0.175, +0.079] | no detectable difference |
| alarm_f1 | 0.61 | 0.55 | -0.063 | [-0.219, +0.108] | no detectable difference |
| false_alarm_rate | 56% | 4% | -52pp | [-75pp, -30pp] | **real**: facts_only better |
| miss_rate | 8% | 35% | +28pp | [+11pp, +45pp] | **real**: v1 better |
| accuracy | 54% | 58% | +5pp | [-8pp, +18pp] | no detectable difference |
| review_recall | 62% | 12% | -50pp | [-75pp, -25pp] | **real**: v1 better |
| flag_balanced_accuracy | 0.68 | 0.81 | +0.122 | [-0.005, +0.254] | no detectable difference |

McNemar exact (calls): flag correct only-v1 14 vs only-facts_only 16, p=0.8555; 3-class only-v1 14 vs only-facts_only 17, p=0.7201.

**Fixed threshold** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = facts_only - v1

| metric | v1 | facts_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.78 | -0.059 | [-0.195, +0.062] | no detectable difference |
| alarm_f1 | 0.76 | 0.61 | -0.149 | [-0.341, +0.008] | no detectable difference |
| false_alarm_rate | 52% | 4% | -48pp | [-71pp, -25pp] | **real**: facts_only better |
| miss_rate | 5% | 35% | +30pp | [+14pp, +48pp] | **real**: v1 better |
| accuracy | 63% | 68% | +5pp | [-8pp, +17pp] | no detectable difference |
| review_recall | 62% | 56% | -6pp | [-38pp, +25pp] | no detectable difference |
| flag_balanced_accuracy | 0.71 | 0.81 | +0.090 | [-0.053, +0.229] | no detectable difference |

McNemar exact (calls): flag correct only-v1 14 vs only-facts_only 14, p=1.0; 3-class only-v1 14 vs only-facts_only 17, p=0.7201.

Flips (cv, 39 calls):

| call | expected | v1 | facts_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Synth_access_001-K1 | alarm | alarm | no_alert | 0.94/0.07 | broken | 00:40-00:52 access: Ja klar, der Code lautet 7 3 9 0 4 1. Vielen Dank, Herr Pfister. Wir werden den Code nun prüfen und die Sperre aufheben. - Kein Alarm: höchster Score 0.07 ('Zugangsinformation prei... | llm_judge: Herr Pfister liest den sechsstelligen Code 739041 vor, um die Sperre seines E-Banking-Zugangs aufzuheben. Dies entspricht der Preisgabe eines Zugangsgeheimnisses. |
| Synth_access_003-K1 | review | review | alarm | 0.79/0.50 | same | 00:33-00:42 access: Perfekt. Können Sie mir den Code bitte vorsagen? Ja klar, der Code lautet 4 8 2 2 1 7. - facts: Fakt: Code von der Beratung erfragt = ja (1.00) - Der Berater fragt den Kunden an, d... | llm_judge: Der Kunde liest einen gültigen sechsstelligen Code laut vors, ohne dass es um einen abgelaufenen oder Musterwert geht. Dieser Code wurde im Zusammenhang mit dem aktuellen E-Banking-Sicherhe... |
| Synth_access_004-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 01:01-01:05 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, mein aktuelles Passwort lautet Bergsee-Fuchs-1984. - Kein Alarm: höchster Score 0.00 (... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Passwort 'Bergsee-Fuchs-1984' laut vorgelesen. |
| Synth_access_005-K1 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:01-01:06 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, das Muster-Passwort lautet im Anleitungsbrief so: Sonne-Tisch-2020. - Kein Alarm: höch... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Muster-Passwort 'Sonne-Tisch-2020' vorgelesen, welches zur aktuellen Anmeldung dient. |
| Synth_access_007-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 01:32-01:50 access: Ja, das ist korrekt. Aber passen Sie auf, Sie sollten Ihre PIN niemals nennen oder schriftlich festhalten. Meine PIN ist doch 4 7 1 9, oder stimmt das nicht? Frau Wyss, ich muss Si... | llm_judge: Frau Wyss hat ihre aktuelle PIN 4 7 1 9 tatsächlich vorgelesen, was die Preisgabe eines Zugangsgeheimnisses darstellt. |
| Synth_access_009-K1 | review | alarm | no_alert | 0.93/0.00 | broken | 01:20-01:43 access: Hier, ich habe alles notiert. Aber ich bringe die PIN meiner Karte und die meines Mannes durcheinander. Die Nummer 4 7 1 9 ist entweder meine oder seine. Frau Wyss, ich muss Sie bi... | llm_judge: Frau Wyss liest im Gespräch die Nummer '4 7 1 9' vor, die entweder ihre PIN oder die ihres Partners sein könnte. Dies passiert im Zusammenhang mit dem aktuellen Transaktionsvorgang. |
| Synth_access_010-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:29-00:36 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1 - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Herr Meier gibt im Gespräch den Freigabecode '55039281' tatsächlich vor. |
| Synth_access_011-K1 | no_alert | review | no_alert | 0.78/0.00 | fixed | 00:29-00:45 access: Ja, ja, also da steht die Auftragsreferenz: ZR-2291-0045 und der Betrag lautet 8'400 Franken. Perfekt, Herr Meier. Nun müssen Sie den Freigabecode selbst in das Gerät eingeben. Las... | llm_judge: Der Kunde liest einen gültigen Freigabecode vor, den er benötigt, um eine Zahlung zu tätigen. |
| Synth_access_012-K1 | review | review | no_alert | 0.87/0.00 | broken | 00:29-00:40 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1. Mein Sohn hat ihn mir per Foto geschickt. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.... | llm_judge: Der Kunde liest den Freigabecode 5 5 0 3 9 2 8 1 vor, der zu einem laufenden Freigabevorgang gehört. |
| Synth_access_013-K1 | alarm | review | no_alert | 0.88/0.00 | broken | 01:04-01:09 access: Ja, also der Code lautet 2 0 6 6 1 8 - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Frau Schmid hat den aktuellen Anmeldecode 206618 tatsächlich vorgelesen, obwohl der Code noch gültig war. |
| Synth_access_014-K1 | no_alert | review | no_alert | 0.74/0.00 | fixed | 01:05-01:16 access: Der Text lautet: 'Code: XXXXXX'. Hier ist auch noch ein Link drin. Frau Schmid, haben Sie den Link schon angeklickt oder den Code weitergegeben? - Kein Alarm: höchster Score 0.00 (... | llm_judge: Frau Schmid hat einen Code (XXXXXX) vorgelesen, der als aktueller Anmeldecode beschrieben wurde, der noch zehn Minuten gültig ist. Dies entspricht dem Misconduct 'Zugangsinformation preisge... |
| Synth_access_015-K1 | review | review | alarm | 0.72/0.50 | same | 00:50-01:00 access: Die zweite Nachricht kam vor einigen Stunden. Sie sagt, dass ich einen Anmeldecode haben sollte, der lautet 2 0 6 6 1 8. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.98) ... | llm_judge: Frau Schmid hat den Anmeldecode '206618' tatsächlich vorgelesen, der zum aktuellen Anmeldevorgang gehört. |
| Synth_disclosure_003-K1 | review | no_alert | alarm | 0.25/0.50 | fixed | 00:14-00:23 disclosure: Ich brauche den aktuellen Stand des Sparkontos meiner Ex-Frau. Sie sagte mir, ich könnte das bei der Bank herausfinden. - facts: Fakt: Auskunft über Drittperson verlangt = ja (... | geval: Der Berater weist den Kunden mehrfach ab, ihm den Kontostand seiner Ex-Frau zu nennen, da dieser ohne formale Vollmacht nicht enthüllt werden darf. Es wird keine konkrete Auskunft an einen unau... |
| Synth_disclosure_004-K1 | no_alert | no_alert | alarm | 0.19/0.50 | broken | 01:04-01:13 disclosure: Gut, danke. Dann kann ich Ihnen jetzt sagen, dass der nächste Zinstermin für die Hypothek am 30. Juni ist. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1... | Kein Alarm: höchster Score 0.19 ('Auskunft an Dritte') liegt unter 0.65 (Schwelle 0.80 minus Band 0.15). |
| Synth_disclosure_005-K1 | alarm | review | alarm | 0.73/0.99 | same | 00:41-00:48 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Berater fragt de... | llm_judge: Der Berater gibt trotz fehlender Vollmacht spezifische Informationen über den Kredit des Vaters weiter. Dies ist nach der Richtlinie als Preisgabe geschützter Informationen an einen Unberec... |
| Synth_disclosure_006-K1 | review | review | no_alert | 0.43/0.00 | broken | 00:41-01:28 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? Ja, haben wir. Die Vollmacht ist sicher irgendwo, aber sie ist nicht hier bei mir. V... | geval: Die Berechtigung des Kunden zur Auskunft über die Kontodaten seines Vaters wurde nicht eindeutig bestätigt. Der Berater fragt nach einer Generalvollmacht und mündlicher Erlaubnis, jedoch wird d... |
| Synth_disclosure_007-K1 | alarm | review | alarm | 0.72/0.50 | same | 00:57-01:06 disclosure: Ja, sie sind seit Jahren bei uns. Ich muss sagen, sie haben kürzlich eine neue Hypothek von 1,2 Millionen aufgenommen. - facts: Fakt: Konkrete Daten einer Drittperson herausgeg... | llm_judge: Die Beratung gibt ohne vorherige Bestätigung des Rechtes der Kundin, konkretes Wissen über ihre Nachbarn weiterzugeben. Sie nennt spezifische Daten über die Brunners, wie die Höhe des Darle... |
| Synth_disclosure_008-K1 | no_alert | review | no_alert | 0.30/0.00 | fixed | 01:00-01:19 disclosure: Ja, ich hab das auch bemerkt. Die Brunners, unsere Nachbarn, sind auch Kunden bei euch? Ja, die Brunners sind seit Jahren bei uns. Aber Frau Kunz, ich kann leider keine Informa... | llm_judge: Die Beratung hat keinen Beweis für eine Vollmacht des Kunden vorgelegt und hat trotzdem konkrete Informationen über andere Kunden (die Brunners) genannt. Dies entspricht dem Misconduct 'Aus... |
| Synth_disclosure_009-K1 | no_alert | review | no_alert | 0.46/0.00 | fixed | 00:32-00:38 disclosure: Verstehe, Frau Hostettler. Sie sind ja Zeichnungsberechtigte für das Geschäftskonto und haben somit das Auskunftsrecht. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') lieg... | llm_judge: Anna Meyer, die Beratungsmitarbeiterin, bestätigt Sabine Hostettler, dass sie Zeichnungsberechtigte für das Geschäftskonto ist und somit das Auskunftsrecht hat. Es wird keine explizite Voll... |
| Synth_disclosure_010-K1 | alarm | review | alarm | 0.79/0.50 | same | 01:08-01:16 disclosure: Da es dringend ist, sage ich Ihnen den Saldo. Der aktuelle Saldo Ihres Geschäftskontos beträgt 23'450 Franken. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = j... | llm_judge: Frau Hostettler fragt nach dem Kontostand ihres Geschäftskontos, obwohl die Beratung ihr erklärt hat, dass sie nicht sicher sei, ob sie Vollmacht besitzt. Die Beratung gibt trotzdem den Kon... |
| Synth_disclosure_012-K1 | alarm | review | alarm | 0.68/0.99 | same | 00:41-00:52 disclosure: Das ist wichtig zu wissen. Lassen Sie mich kurz Ihre Daten abrufen... Okay, ich sehe hier, dass die Kreditkarte tatsächlich auf Ihren Ehemann registriert ist. - facts: Fakt: Ko... | llm_judge: Die Beratung gibt nach der Erkenntnis, dass Frau Aregger keine Vollmacht hat, konkrete Informationen über die Transaktionen ihres Ehemannes an sie weiter. |
| Synth_disclosure_014-K1 | review | review | no_alert | 0.55/0.00 | broken | 00:07-00:14 disclosure: Grüezi. Ja, ich habe diese merkwürdigen Belastungen auf meiner Kreditkarte gesehen und wollte mich erkundigen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0... | llm_judge: Die Beratung gibt ohne Bestätigung einer gültigen Vollmacht konkrete Daten des Kundenpreises (Belastungen auf der Kreditkarte) weiter. |
| Synth_documentation_002-K1 | no_alert | review | no_alert | 0.37/0.00 | fixed | 01:50-02:15 documentation: Das ist eine vernünftige Lösung. Eines noch, Herr Frei. Ich habe im Entwurf ein Auto-Leasing bemerkt, das schon letztes Jahr abgelaufen und zurückgegeben wurde. Ja, das Leas... | llm_judge: Herr Frei hat explizit nach der Löschung einer bestehenden Rückzahlungsbürde (abgelaufenes Auto-Leasing) gebeten, welche relevant für die Kreditprüfung wäre. |
| Synth_documentation_005-K1 | no_alert | review | no_alert | 0.48/0.00 | fixed | 00:37-01:03 disclosure: Verstehe. Und Sie haben ja auch bereits einen Kredit von gst12'000 Franken bei einer anderen Bank. Richtig, das ist ein Konsumkredit. Haben Sie auch schon darüber nachgedacht, ... | llm_judge: Die Beratung gibt spezifische Informationen über einen Konsumkredit von 12'000 Franken bei einer anderen Bank an die Kundin weiter, ohne dass die Berechtigung zur Preisgabe dieser Daten bes... |
| Synth_documentation_006-K1 | review | review | no_alert | 0.84/0.00 | broken | 00:45-01:08 documentation: Ja, das ist richtig. Ich habe auch eine Bürgschaft für mein Geschäft, die von meiner Schwester gestellt wurde. Ah, ich sehe. Die Bürgschaft Ihrer Schwester werde ich vorerst... | llm_judge: Frau Odermatt willigt ein, dass die Bürgschaft ihrer Schwester nicht protokolliert wird, obwohl sie davon weiß und die Bedeutung kennt. Sie stimmt zu, dass diese relevanten Informationen ni... |
| Synth_documentation_010-K1 | alarm | alarm | no_alert | 0.96/0.00 | broken | 00:59-01:11 documentation: Das ist eine gute Rate. Könnten Sie bitte die Schulden auf Ihrer Kreditkarte nicht protokollieren? Bitte, das wäre sehr hilfreich. Ich möchte den Privatkredit bekommen. - Ke... | llm_judge: Frau Rüegg wünscht sich, dass die Schulden auf ihrer Kreditkarte nicht protokolliert werden, was eine bekannte Verpflichtung vor der internen Prüfung verbirgt. |
| Synth_documentation_011-K1 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 01:21-01:33 documentation: Ja, in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine Schuld nicht zu protokollieren. Ich möchte, dass alles korrekt erfasst wird. - Kein ... | llm_judge: Frau Rüegg hat explizit angefordert, dass eine bestehende Schuld nicht protokolliert wird. Sie sagte: 'in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine S... |
| Synth_numbers_002-K1 | alarm | review | no_alert | 0.90/0.00 | broken | 00:51-01:03 access: Die letzten Ziffern sind 4471 und meine PIN ist 9 0 5 2, falls Sie die zum Sperren brauchen. Frau Bachmann, wir benötigen die PIN gar nicht zur Karten-Sperre. Wir sperren die Karte... | llm_judge: Frau Bachmann gibt ihre PIN 9052 tatsächlich am Telefon vor, während sie erklärt, dass sie diese Informationen zur Sperre der Karte benötigt. |
| Synth_numbers_005-K1 | no_alert | review | no_alert | 0.64/0.00 | fixed | 00:29-00:34 access: Ja, die Buchungsnummer lautet HX-5530-27 und die letzten vier Ziffern sind 8812. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15... | geval: Die Kundin Frau Berger nennt die letzten vier Ziffern ihrer Kreditkarte, die noch gültig sind, was als Zugangsinformation angesehen werden kann. Dies entspricht der Preisgabe von Zugangsinforma... |
| Synth_numbers_006-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:51-00:56 access: Die Nummer lautet 314159. Können Sie das gleich für mich eingeben? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Die Kundin liest den gültigen Bestätigungscode '314159' vor, der für den aktuellen Buchungsprozess benötigt wird. |
| Synth_splitting_005-K1 | no_alert | review | no_alert | 0.29/0.00 | fixed | 00:38-00:38 splitting: Das ist eine klare Entscheidung. Haben Sie im Kassierkurs gelernt, dass das Aufteilen von Ausgaben zur Umgehung des Vorstands verboten ist? - Kein Alarm: höchster Score 0.00 ('I... | keywords: Stichwort K07 «aufteilen» (Aufteilen) |
| Synth_splitting_009-K1 | review | review | alarm | 0.72/0.50 | same | 00:40-00:46 splitting: Ich schlage vor, die 30'000 in zwei Zahlungen aufzuteilen, wegen der Liquidität. - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Berater schlägt vor, die Übe... | llm_judge: Der Kunde fragt nach einer Überweisung von 30'000 Franken für eine Baumaschine und der Berater schlägt vor, den Betrag in zwei Teilbeträge aufzuteilen, um die interne Prüfung zu umgehen. |
| Synth_trade_002-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') li... | geval: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, und begründet dies mit der Information, dass die Firma die Zulassung heute Morgen per Medienmitteilung veröffentlic... |
| Synth_trade_003-K1 | review | review | alarm | 0.90/0.50 | same | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Adrian Lüth... | llm_judge: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, basierend auf vertraulicher Information, die er von einer Person erhalten hat, die diese Information wissen sol... |
| Synth_trade_005-K1 | no_alert | alarm | no_alert | 0.96/0.00 | fixed | 01:03-01:36 trade: Es ist eine vernünftige Entscheidung. Übrigens, das öffentliche Übernahmeangebot für die Rheintal Logistik AG wurde gestern offiziell publiziert und steht in allen Zeitungen. Ja, ic... | llm_judge: Die Kundin äußert einen Kaufwunsch für 300 Aktien der Rheintal Logistik AG und begründet dies mit der noch nicht offiziell veröffentlichten Nachricht über ein Übernahmeangebot. Die Advisor ... |
| Synth_trade_009-K1 | review | review | alarm | 0.84/0.50 | same | 00:12-00:17 trade: Ich möchte Aktien meiner Firma, der Seeland Solar AG, kaufen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Imhof表达了她想购买公司股票的明确愿望。 (Regel: trade.review_1) | llm_judge: Frau Imhof, Mitarbeiterin der Seeland Solar AG, äußert den Wunsch, Aktien ihrer Firma vor der Bekanntgabe von internen Informationen zu kaufen. Sie bestätigt, dass sie Zugang zu solchen Inf... |
| Synth_trade_011-K1 | no_alert | review | no_alert | 0.31/0.00 | fixed | 00:36-01:05 trade: Ich hab's im Radio gehört. Der Kurs ist schon gefallen. Ja, das denke ich auch. Ich möchte die 1'000 Aktien verkaufen, um Verluste zu minimieren. Ja, das möchte ich. Ich will sie so... | llm_judge: Herr Keusch verkauft seine Aktien der Firma Juragrat Uhren aufgrund einer Gewinnwarnung, die er über Radio erfahren hat. Die Information war jedoch bereits öffentlich und wurde nicht aus ei... |
| Synth_trade_014-K1 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:52-02:02 trade: Letzte Woche wurde offiziell angekündigt, dass die Limmat Versicherungen bald mit einer anderen Versicherung fusionieren werden. Das steht jetzt sogar in den Zeitungen. - Kein Alarm... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, basierend auf der noch nicht offiziell veröffentlichten Information, dass Limmat Versicherungen bald mit einer andere... |
| Synth_trade_015-K1 | review | review | alarm | 0.85/0.50 | same | 02:12-02:17 trade: Ja, Sie haben recht. Ich wollte 20'000 Franken in Limmat-Aktien stecken. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Brändli表达了她希望投入20,000法郎购买Limmat保险公司的股票的意愿。... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, da ihre Tochter ihr angedeutet hat, dass die Firma etwas Besonderes vorhat. Dies wird als noch nicht öffentliche Info... |

## `judge_facts` vs `v1` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 65 calls; difference = judge_facts - v1

| metric | v1 | judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.89 | 0.94 | +0.055 | [-0.008, +0.131] | no detectable difference |
| alarm AUC | 0.90 | 0.89 | -0.006 | [-0.101, +0.077] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = judge_facts - v1

| metric | v1 | judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.83 | 0.82 | -0.004 | [-0.063, +0.041] | no detectable difference |
| alarm_f1 | 0.72 | 0.61 | -0.109 | [-0.303, +0.067] | no detectable difference |
| false_alarm_rate | 56% | 52% | -4pp | [-19pp, +9pp] | no detectable difference |
| miss_rate | 5% | 8% | +2pp | [+0pp, +8pp] | no detectable difference |
| accuracy | 60% | 54% | -6pp | [-16pp, +3pp] | no detectable difference |
| review_recall | 62% | 75% | +12pp | [-12pp, +36pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.70 | +0.007 | [-0.085, +0.089] | no detectable difference |

McNemar exact (calls): flag correct only-v1 2 vs only-judge_facts 2, p=1.0; 3-class only-v1 11 vs only-judge_facts 7, p=0.4807.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = judge_facts - v1

| metric | v1 | judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.81 | 0.83 | +0.018 | [-0.017, +0.057] | no detectable difference |
| alarm_f1 | 0.61 | 0.08 | -0.529 | [-0.683, -0.352] | **real**: v1 better |
| false_alarm_rate | 56% | 48% | -8pp | [-25pp, +7pp] | no detectable difference |
| miss_rate | 8% | 8% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 54% | 42% | -12pp | [-22pp, -3pp] | **real**: v1 better |
| review_recall | 62% | 81% | +19pp | [-7pp, +45pp] | no detectable difference |
| flag_balanced_accuracy | 0.68 | 0.72 | +0.040 | [-0.037, +0.125] | no detectable difference |

McNemar exact (calls): flag correct only-v1 2 vs only-judge_facts 4, p=0.6875; 3-class only-v1 15 vs only-judge_facts 7, p=0.1338.

**Fixed threshold** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = judge_facts - v1

| metric | v1 | judge_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.84 | +0.006 | [-0.056, +0.057] | no detectable difference |
| alarm_f1 | 0.76 | 0.61 | -0.149 | [-0.341, +0.008] | no detectable difference |
| false_alarm_rate | 52% | 44% | -8pp | [-24pp, +8pp] | no detectable difference |
| miss_rate | 5% | 8% | +2pp | [+0pp, +8pp] | no detectable difference |
| accuracy | 63% | 57% | -6pp | [-17pp, +3pp] | no detectable difference |
| review_recall | 62% | 75% | +12pp | [-12pp, +36pp] | no detectable difference |
| flag_balanced_accuracy | 0.71 | 0.74 | +0.028 | [-0.074, +0.115] | no detectable difference |

McNemar exact (calls): flag correct only-v1 2 vs only-judge_facts 3, p=1.0; 3-class only-v1 11 vs only-judge_facts 7, p=0.4807.

Flips (cv, 22 calls):

| call | expected | v1 | judge_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Synth_access_001-K1 | alarm | alarm | review | 0.94/0.55 | same | 00:33-00:52 access: Perfekt. Können Sie mir den Code bitte vorsagen? Damit wir die Sperre aufheben können. Ja klar, der Code lautet 7 3 9 0 4 1. Vielen Dank, Herr Pfister. Wir werden den Code nun prüf... | llm_judge: Herr Pfister liest den sechsstelligen Code 739041 vor, um die Sperre seines E-Banking-Zugangs aufzuheben. Dies entspricht der Preisgabe eines Zugangsgeheimnisses. |
| Synth_access_004-K1 | alarm | alarm | review | 0.94/0.48 | same | 00:55-01:05 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, mein aktuelles Passwort lautet Bergsee-Fuchs-1984. - llm_judge: Der Kunde Hubert Zbind... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Passwort 'Bergsee-Fuchs-1984' laut vorgelesen. |
| Synth_access_005-K1 | no_alert | alarm | review | 0.93/0.48 | same | 00:55-01:06 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, das Muster-Passwort lautet im Anleitungsbrief so: Sonne-Tisch-2020. - llm_judge: Der K... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Muster-Passwort 'Sonne-Tisch-2020' vorgelesen, welches zur aktuellen Anmeldung dient. |
| Synth_access_007-K1 | alarm | alarm | review | 0.94/0.49 | same | 01:32-01:41 access: Ja, das ist korrekt. Aber passen Sie auf, Sie sollten Ihre PIN niemals nennen oder schriftlich festhalten. Meine PIN ist doch 4 7 1 9, oder stimmt das nicht? - llm_judge: Frau Wyss... | llm_judge: Frau Wyss hat ihre aktuelle PIN 4 7 1 9 tatsächlich vorgelesen, was die Preisgabe eines Zugangsgeheimnisses darstellt. |
| Synth_access_009-K1 | review | alarm | review | 0.93/0.49 | same | 01:20-01:43 access: Hier, ich habe alles notiert. Aber ich bringe die PIN meiner Karte und die meines Mannes durcheinander. Die Nummer 4 7 1 9 ist entweder meine oder seine. Frau Wyss, ich muss Sie bi... | llm_judge: Frau Wyss liest im Gespräch die Nummer '4 7 1 9' vor, die entweder ihre PIN oder die ihres Partners sein könnte. Dies passiert im Zusammenhang mit dem aktuellen Transaktionsvorgang. |
| Synth_access_010-K1 | alarm | alarm | review | 0.94/0.48 | same | 00:29-00:36 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1 - llm_judge: Herr Meier gibt im Gespräch den Freigabecode '55039281' tatsächlich vor. | llm_judge: Herr Meier gibt im Gespräch den Freigabecode '55039281' tatsächlich vor. |
| Synth_disclosure_004-K1 | no_alert | no_alert | review | 0.19/0.28 | broken | 01:04-01:13 disclosure: Gut, danke. Dann kann ich Ihnen jetzt sagen, dass der nächste Zinstermin für die Hypothek am 30. Juni ist. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1... | Kein Alarm: höchster Score 0.19 ('Auskunft an Dritte') liegt unter 0.65 (Schwelle 0.80 minus Band 0.15). |
| Synth_disclosure_005-K1 | alarm | review | alarm | 0.73/0.95 | same | 01:06-01:21 disclosure: Ich verstehe. Dann kann ich Ihnen leider nicht alle Informationen zu den Krediten Ihres Vaters geben. Aber ich kann Ihnen sagen, dass der nächste Zinstermin für die Hypothek am... | llm_judge: Der Berater gibt trotz fehlender Vollmacht spezifische Informationen über den Kredit des Vaters weiter. Dies ist nach der Richtlinie als Preisgabe geschützter Informationen an einen Unberec... |
| Synth_disclosure_006-K1 | review | review | no_alert | 0.43/0.16 | broken | 00:41-01:28 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? Ja, haben wir. Die Vollmacht ist sicher irgendwo, aber sie ist nicht hier bei mir. V... | geval: Die Berechtigung des Kunden zur Auskunft über die Kontodaten seines Vaters wurde nicht eindeutig bestätigt. Der Berater fragt nach einer Generalvollmacht und mündlicher Erlaubnis, jedoch wird d... |
| Synth_disclosure_012-K1 | alarm | review | alarm | 0.68/0.94 | same | 01:17-01:24 disclosure: Selbstverständlich. Die letzte Belastung beträgt 640 Franken und wurde für ein Hotel in Lugano veranlasst. - llm_judge: Die Beratung gibt nach der Erkenntnis, dass Frau Aregger... | llm_judge: Die Beratung gibt nach der Erkenntnis, dass Frau Aregger keine Vollmacht hat, konkrete Informationen über die Transaktionen ihres Ehemannes an sie weiter. |
| Synth_documentation_009-K1 | review | alarm | review | 0.95/0.82 | same | 00:56-01:06 documentation: Ähm, ich bitte Euch dringend, den Streit mit dem Steueramt nicht weiterzugeben. Okay, dann notiere ich das als offene Frage. - llm_judge: Frau Huber bittet den Berater, den ... | geval: Frau Huber bittet den Berater dringend, den Streit mit dem Steueramt nicht weiterzugeben (T010). Dies deutet darauf hin, dass sie versucht, eine potentiell negative Information vor der Finanzie... |
| Synth_documentation_010-K1 | alarm | alarm | review | 0.96/0.49 | same | 00:59-01:11 documentation: Das ist eine gute Rate. Könnten Sie bitte die Schulden auf Ihrer Kreditkarte nicht protokollieren? Bitte, das wäre sehr hilfreich. Ich möchte den Privatkredit bekommen. - ll... | llm_judge: Frau Rüegg wünscht sich, dass die Schulden auf ihrer Kreditkarte nicht protokolliert werden, was eine bekannte Verpflichtung vor der internen Prüfung verbirgt. |
| Synth_documentation_011-K1 | no_alert | alarm | review | 0.53/0.26 | same | 01:21-01:33 documentation: Ja, in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine Schuld nicht zu protokollieren. Ich möchte, dass alles korrekt erfasst wird. - llm_j... | llm_judge: Frau Rüegg hat explizit angefordert, dass eine bestehende Schuld nicht protokolliert wird. Sie sagte: 'in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine S... |
| Synth_numbers_006-K1 | alarm | alarm | review | 0.94/0.49 | same | 00:51-01:10 access: Die Nummer lautet 314159. Können Sie das gleich für mich eingeben? Ja, Frau Berger, das kann ich. Geben Sie mir kurz die Reservierungsnummer und den Bestätigungscode noch einmal du... | llm_judge: Die Kundin liest den gültigen Bestätigungscode '314159' vor, der für den aktuellen Buchungsprozess benötigt wird. |
| Synth_splitting_001-K1 | alarm | alarm | review | 0.95/0.83 | same | 00:47-01:01 documentation: Ja, das weiß ich. Deshalb möchte ich auch, dass meine Partner das nicht sehen. Verstanden. Wir können dafür sorgen, dass die einzelnen Beträge nicht als Teil der Gesamtsumme... | llm_judge: Herr Gisler möchte, dass die einzelnen Teilzahlungen nicht als Teil der Gesamtsumme angezeigt werden, um seine Partnerschaft davon abzuhalten. Dies entspricht dem Verschweigen einer relevan... |
| Synth_trade_002-K1 | no_alert | review | no_alert | 0.42/0.13 | fixed | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - Kein Alarm: höchster Score 0.13 ('Auskunft an Dritte') liegt unter 0.1... | geval: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, und begründet dies mit der Information, dass die Firma die Zulassung heute Morgen per Medienmitteilung veröffentlic... |
| Synth_trade_004-K1 | alarm | alarm | review | 0.96/0.83 | same | 00:45-00:57 trade: Ja, ich habe sogar ein paar Aktien davon. Sehr schön. Ich sehe, Sie haben bereits 500 Aktien. Sie erwägen jetzt, weitere 300 zu kaufen. - llm_judge: Frau Gerber äußert den Wunsch, 3... | llm_judge: Frau Gerber äußert den Wunsch, 300 Aktien der Rheintal Logistik AG zu kaufen, bevor eine geplante Übernahme bekannt wird. Diese Information wurde als vertraulich und noch nicht öffentlich b... |
| Synth_trade_005-K1 | no_alert | alarm | review | 0.96/0.48 | same | 01:03-01:36 trade: Es ist eine vernünftige Entscheidung. Übrigens, das öffentliche Übernahmeangebot für die Rheintal Logistik AG wurde gestern offiziell publiziert und steht in allen Zeitungen. Ja, ic... | llm_judge: Die Kundin äußert einen Kaufwunsch für 300 Aktien der Rheintal Logistik AG und begründet dies mit der noch nicht offiziell veröffentlichten Nachricht über ein Übernahmeangebot. Die Advisor ... |
| Synth_trade_006-K1 | review | alarm | review | 0.95/0.83 | same | 01:03-01:18 trade: Es ist eine vernünftige Entscheidung. Übrigens, bei der Rheintal Logistik laufe etwas, mehr dürfte ich Ihnen leider nicht sagen. Dann möchte ich diese 300 Aktien kaufen, bevor ich m... | llm_judge: Frau Gerber äußert den Wunsch, 300 Aktien der Rheintal Logistik AG zu kaufen, basierend auf vertraulicher Information, die ihr die Beraterin gegeben hat. Diese Information wurde explizit al... |
| Synth_trade_010-K1 | alarm | alarm | review | 0.95/0.83 | same | 00:27-00:34 trade: Ja, das stimmt. Meine Frau arbeitet bei der Buchhaltung dort, und gestern hat sie mir was erzählt. - llm_judge: Herr Keusch äußert den Wunsch, seine Aktien zu verkaufen, nachdem er ... | llm_judge: Herr Keusch äußert den Wunsch, seine Aktien zu verkaufen, nachdem er erfahren hat, dass die Firma eine Gewinnwarnung veröffentlichen muss. Diese Information wurde von seiner Frau, einer Mit... |
| Synth_trade_011-K1 | no_alert | review | no_alert | 0.31/0.13 | fixed | 00:36-01:05 trade: Ich hab's im Radio gehört. Der Kurs ist schon gefallen. Ja, das denke ich auch. Ich möchte die 1'000 Aktien verkaufen, um Verluste zu minimieren. Ja, das möchte ich. Ich will sie so... | llm_judge: Herr Keusch verkauft seine Aktien der Firma Juragrat Uhren aufgrund einer Gewinnwarnung, die er über Radio erfahren hat. Die Information war jedoch bereits öffentlich und wurde nicht aus ei... |
| Synth_trade_014-K1 | no_alert | alarm | review | 0.93/0.47 | same | 01:52-02:02 trade: Letzte Woche wurde offiziell angekündigt, dass die Limmat Versicherungen bald mit einer anderen Versicherung fusionieren werden. Das steht jetzt sogar in den Zeitungen. - llm_judge:... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, basierend auf der noch nicht offiziell veröffentlichten Information, dass Limmat Versicherungen bald mit einer andere... |

## `kwpat_facts` vs `v1` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 65 calls; difference = kwpat_facts - v1

| metric | v1 | kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.89 | 0.92 | +0.033 | [-0.060, +0.131] | no detectable difference |
| alarm AUC | 0.90 | 0.83 | -0.071 | [-0.170, +0.023] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = kwpat_facts - v1

| metric | v1 | kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.83 | 0.83 | +0.007 | [-0.100, +0.109] | no detectable difference |
| alarm_f1 | 0.72 | 0.33 | -0.387 | [-0.622, -0.164] | **real**: v1 better |
| false_alarm_rate | 56% | 8% | -48pp | [-72pp, -22pp] | **real**: kwpat_facts better |
| miss_rate | 5% | 25% | +20pp | [+5pp, +36pp] | **real**: v1 better |
| accuracy | 60% | 58% | -2pp | [-13pp, +11pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [-35pp, +35pp] | no detectable difference |
| flag_balanced_accuracy | 0.69 | 0.83 | +0.140 | [+0.003, +0.275] | **real**: kwpat_facts better |

McNemar exact (calls): flag correct only-v1 11 vs only-kwpat_facts 15, p=0.5572; 3-class only-v1 20 vs only-kwpat_facts 19, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = kwpat_facts - v1

| metric | v1 | kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.81 | 0.83 | +0.020 | [-0.079, +0.115] | no detectable difference |
| alarm_f1 | 0.61 | 0.33 | -0.275 | [-0.497, -0.074] | **real**: v1 better |
| false_alarm_rate | 56% | 8% | -48pp | [-72pp, -22pp] | **real**: kwpat_facts better |
| miss_rate | 8% | 25% | +18pp | [+3pp, +33pp] | **real**: v1 better |
| accuracy | 54% | 58% | +5pp | [-6pp, +16pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [-35pp, +35pp] | no detectable difference |
| flag_balanced_accuracy | 0.68 | 0.83 | +0.152 | [+0.027, +0.278] | **real**: kwpat_facts better |

McNemar exact (calls): flag correct only-v1 11 vs only-kwpat_facts 16, p=0.4421; 3-class only-v1 16 vs only-kwpat_facts 19, p=0.7359.

**Fixed threshold** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = kwpat_facts - v1

| metric | v1 | kwpat_facts | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.78 | -0.059 | [-0.195, +0.062] | no detectable difference |
| alarm_f1 | 0.76 | 0.33 | -0.427 | [-0.652, -0.232] | **real**: v1 better |
| false_alarm_rate | 52% | 4% | -48pp | [-71pp, -25pp] | **real**: kwpat_facts better |
| miss_rate | 5% | 35% | +30pp | [+14pp, +48pp] | **real**: v1 better |
| accuracy | 63% | 58% | -5pp | [-17pp, +9pp] | no detectable difference |
| review_recall | 62% | 56% | -6pp | [-38pp, +25pp] | no detectable difference |
| flag_balanced_accuracy | 0.71 | 0.81 | +0.090 | [-0.053, +0.229] | no detectable difference |

McNemar exact (calls): flag correct only-v1 14 vs only-kwpat_facts 14, p=1.0; 3-class only-v1 19 vs only-kwpat_facts 16, p=0.7359.

Flips (cv, 41 calls):

| call | expected | v1 | kwpat_facts | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Synth_access_001-K1 | alarm | alarm | review | 0.94/0.10 | same | 00:33-00:45 access: Perfekt. Können Sie mir den Code bitte vorsagen? Damit wir die Sperre aufheben können. Ja klar, der Code lautet 7 3 9 0 4 1. - patterns: Kundschaft liest möglichen Zugangscode (6 Z... | llm_judge: Herr Pfister liest den sechsstelligen Code 739041 vor, um die Sperre seines E-Banking-Zugangs aufzuheben. Dies entspricht der Preisgabe eines Zugangsgeheimnisses. |
| Synth_access_004-K1 | alarm | alarm | no_alert | 0.94/0.04 | broken | 01:01-01:05 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, mein aktuelles Passwort lautet Bergsee-Fuchs-1984. - Kein Alarm: höchster Score 0.04 (... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Passwort 'Bergsee-Fuchs-1984' laut vorgelesen. |
| Synth_access_005-K1 | no_alert | alarm | no_alert | 0.93/0.04 | fixed | 01:01-01:06 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, das Muster-Passwort lautet im Anleitungsbrief so: Sonne-Tisch-2020. - Kein Alarm: höch... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Muster-Passwort 'Sonne-Tisch-2020' vorgelesen, welches zur aktuellen Anmeldung dient. |
| Synth_access_007-K1 | alarm | alarm | review | 0.94/0.07 | same | 01:20-01:27 access: Hier, ich habe alles notiert. Meine alte PIN ist 5 8 3 6, richtig? - patterns: Kundschaft liest mögliche PIN (4 Ziffern) vor, Stichwort «PIN» | llm_judge: Frau Wyss hat ihre aktuelle PIN 4 7 1 9 tatsächlich vorgelesen, was die Preisgabe eines Zugangsgeheimnisses darstellt. |
| Synth_access_008-K1 | no_alert | no_alert | review | 0.20/0.06 | broken | 00:19-00:20 access: Grüezi Sabine, ja genau. Ich habe meine neue Karte am Automaten verwendet, aber leider dreimal falsch die PIN eingegeben. - keywords: Stichwort K10 «PIN» (Zugangswörter) | Kein Alarm: höchster Score 0.20 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Synth_access_009-K1 | review | alarm | review | 0.93/0.07 | same | 01:20-01:33 access: Hier, ich habe alles notiert. Aber ich bringe die PIN meiner Karte und die meines Mannes durcheinander. Die Nummer 4 7 1 9 ist entweder meine oder seine. - patterns: Kundschaft lie... | llm_judge: Frau Wyss liest im Gespräch die Nummer '4 7 1 9' vor, die entweder ihre PIN oder die ihres Partners sein könnte. Dies passiert im Zusammenhang mit dem aktuellen Transaktionsvorgang. |
| Synth_access_010-K1 | alarm | alarm | no_alert | 0.94/0.04 | broken | 00:29-00:36 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1 - Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Herr Meier gibt im Gespräch den Freigabecode '55039281' tatsächlich vor. |
| Synth_access_011-K1 | no_alert | review | no_alert | 0.78/0.04 | fixed | 00:29-00:45 access: Ja, ja, also da steht die Auftragsreferenz: ZR-2291-0045 und der Betrag lautet 8'400 Franken. Perfekt, Herr Meier. Nun müssen Sie den Freigabecode selbst in das Gerät eingeben. Las... | llm_judge: Der Kunde liest einen gültigen Freigabecode vor, den er benötigt, um eine Zahlung zu tätigen. |
| Synth_access_012-K1 | review | review | no_alert | 0.87/0.04 | broken | 00:29-00:40 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1. Mein Sohn hat ihn mir per Foto geschickt. - Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter... | llm_judge: Der Kunde liest den Freigabecode 5 5 0 3 9 2 8 1 vor, der zu einem laufenden Freigabevorgang gehört. |
| Synth_access_013-K1 | alarm | review | no_alert | 0.88/0.04 | broken | 01:04-01:09 access: Ja, also der Code lautet 2 0 6 6 1 8 - Kein Alarm: höchster Score 0.04 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Frau Schmid hat den aktuellen Anmeldecode 206618 tatsächlich vorgelesen, obwohl der Code noch gültig war. |
| Synth_access_014-K1 | no_alert | review | no_alert | 0.74/0.00 | fixed | 01:05-01:16 access: Der Text lautet: 'Code: XXXXXX'. Hier ist auch noch ein Link drin. Frau Schmid, haben Sie den Link schon angeklickt oder den Code weitergegeben? - Kein Alarm: höchster Score 0.00 (... | llm_judge: Frau Schmid hat einen Code (XXXXXX) vorgelesen, der als aktueller Anmeldecode beschrieben wurde, der noch zehn Minuten gültig ist. Dies entspricht dem Misconduct 'Zugangsinformation preisge... |
| Synth_disclosure_003-K1 | review | no_alert | review | 0.25/0.45 | fixed | 00:14-00:23 disclosure: Ich brauche den aktuellen Stand des Sparkontos meiner Ex-Frau. Sie sagte mir, ich könnte das bei der Bank herausfinden. - facts: Fakt: Auskunft über Drittperson verlangt = ja (... | geval: Der Berater weist den Kunden mehrfach ab, ihm den Kontostand seiner Ex-Frau zu nennen, da dieser ohne formale Vollmacht nicht enthüllt werden darf. Es wird keine konkrete Auskunft an einen unau... |
| Synth_disclosure_004-K1 | no_alert | no_alert | review | 0.19/0.45 | broken | 01:04-01:13 disclosure: Gut, danke. Dann kann ich Ihnen jetzt sagen, dass der nächste Zinstermin für die Hypothek am 30. Juni ist. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1... | Kein Alarm: höchster Score 0.19 ('Auskunft an Dritte') liegt unter 0.65 (Schwelle 0.80 minus Band 0.15). |
| Synth_disclosure_005-K1 | alarm | review | alarm | 0.73/0.91 | same | 00:41-01:02 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? Ja, haben wir. Die Vollmacht hat mein Vater hinterlegt. Perfekt. Könnten Sie mir bit... | llm_judge: Der Berater gibt trotz fehlender Vollmacht spezifische Informationen über den Kredit des Vaters weiter. Dies ist nach der Richtlinie als Preisgabe geschützter Informationen an einen Unberec... |
| Synth_disclosure_006-K1 | review | review | no_alert | 0.43/0.05 | broken | 00:41-01:28 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? Ja, haben wir. Die Vollmacht ist sicher irgendwo, aber sie ist nicht hier bei mir. V... | geval: Die Berechtigung des Kunden zur Auskunft über die Kontodaten seines Vaters wurde nicht eindeutig bestätigt. Der Berater fragt nach einer Generalvollmacht und mündlicher Erlaubnis, jedoch wird d... |
| Synth_disclosure_008-K1 | no_alert | review | no_alert | 0.30/0.00 | fixed | 01:00-01:19 disclosure: Ja, ich hab das auch bemerkt. Die Brunners, unsere Nachbarn, sind auch Kunden bei euch? Ja, die Brunners sind seit Jahren bei uns. Aber Frau Kunz, ich kann leider keine Informa... | llm_judge: Die Beratung hat keinen Beweis für eine Vollmacht des Kunden vorgelegt und hat trotzdem konkrete Informationen über andere Kunden (die Brunners) genannt. Dies entspricht dem Misconduct 'Aus... |
| Synth_disclosure_009-K1 | no_alert | review | no_alert | 0.46/0.00 | fixed | 00:32-00:38 disclosure: Verstehe, Frau Hostettler. Sie sind ja Zeichnungsberechtigte für das Geschäftskonto und haben somit das Auskunftsrecht. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') lieg... | llm_judge: Anna Meyer, die Beratungsmitarbeiterin, bestätigt Sabine Hostettler, dass sie Zeichnungsberechtigte für das Geschäftskonto ist und somit das Auskunftsrecht hat. Es wird keine explizite Voll... |
| Synth_disclosure_014-K1 | review | review | no_alert | 0.55/0.01 | broken | 00:07-00:14 disclosure: Grüezi. Ja, ich habe diese merkwürdigen Belastungen auf meiner Kreditkarte gesehen und wollte mich erkundigen. - Kein Alarm: höchster Score 0.01 ('Auskunft an Dritte') liegt un... | llm_judge: Die Beratung gibt ohne Bestätigung einer gültigen Vollmacht konkrete Daten des Kundenpreises (Belastungen auf der Kreditkarte) weiter. |
| Synth_documentation_002-K1 | no_alert | review | no_alert | 0.37/0.00 | fixed | 01:50-02:15 documentation: Das ist eine vernünftige Lösung. Eines noch, Herr Frei. Ich habe im Entwurf ein Auto-Leasing bemerkt, das schon letztes Jahr abgelaufen und zurückgegeben wurde. Ja, das Leas... | llm_judge: Herr Frei hat explizit nach der Löschung einer bestehenden Rückzahlungsbürde (abgelaufenes Auto-Leasing) gebeten, welche relevant für die Kreditprüfung wäre. |
| Synth_documentation_004-K1 | alarm | alarm | review | 0.96/0.78 | same | 00:45-00:51 documentation: Richtig, das ist ein Konsumkredit, den ich aber gar nicht in den Antrag aufnehmen möchte. - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.69) - Frau Odermatt ... | llm_judge: Frau Odermatt wünscht, dass sie ihren Konsumkredit von 12'000 Franken nicht in den Kreditantrag einträgt, obwohl sie dies als relevant erachtet. |
| Synth_documentation_005-K1 | no_alert | review | no_alert | 0.48/0.00 | fixed | 00:37-01:03 disclosure: Verstehe. Und Sie haben ja auch bereits einen Kredit von gst12'000 Franken bei einer anderen Bank. Richtig, das ist ein Konsumkredit. Haben Sie auch schon darüber nachgedacht, ... | llm_judge: Die Beratung gibt spezifische Informationen über einen Konsumkredit von 12'000 Franken bei einer anderen Bank an die Kundin weiter, ohne dass die Berechtigung zur Preisgabe dieser Daten bes... |
| Synth_documentation_006-K1 | review | review | no_alert | 0.84/0.00 | broken | 00:45-01:08 documentation: Ja, das ist richtig. Ich habe auch eine Bürgschaft für mein Geschäft, die von meiner Schwester gestellt wurde. Ah, ich sehe. Die Bürgschaft Ihrer Schwester werde ich vorerst... | llm_judge: Frau Odermatt willigt ein, dass die Bürgschaft ihrer Schwester nicht protokolliert wird, obwohl sie davon weiß und die Bedeutung kennt. Sie stimmt zu, dass diese relevanten Informationen ni... |
| Synth_documentation_007-K1 | alarm | alarm | review | 0.95/0.92 | same | 00:45-01:01 documentation: Ähm, ich bitte Euch dringend, das nicht weiterzugeben und nicht in die Unterlagen einzutragen. Aber das ist doch rechtlich nicht korrekt, oder? Ja, ich weiß, aber ich möchte... | geval: Frau Huber bittet den Berater dringend, ihre Schulden bei der Steuerbehörde nicht weiterzugeben und nicht in die Unterlagen einzutragen, obwohl sie weiß, dass dies rechtlich nicht korrekt ist. |
| Synth_documentation_009-K1 | review | alarm | review | 0.95/0.39 | same | 00:56-01:02 documentation: Ähm, ich bitte Euch dringend, den Streit mit dem Steueramt nicht weiterzugeben. - facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (1.00) - Frau Huber bittet darum,... | geval: Frau Huber bittet den Berater dringend, den Streit mit dem Steueramt nicht weiterzugeben (T010). Dies deutet darauf hin, dass sie versucht, eine potentiell negative Information vor der Finanzie... |
| Synth_documentation_010-K1 | alarm | alarm | no_alert | 0.96/0.04 | broken | 00:59-01:11 documentation: Das ist eine gute Rate. Könnten Sie bitte die Schulden auf Ihrer Kreditkarte nicht protokollieren? Bitte, das wäre sehr hilfreich. Ich möchte den Privatkredit bekommen. - Ke... | llm_judge: Frau Rüegg wünscht sich, dass die Schulden auf ihrer Kreditkarte nicht protokolliert werden, was eine bekannte Verpflichtung vor der internen Prüfung verbirgt. |
| Synth_documentation_011-K1 | no_alert | alarm | no_alert | 0.53/0.04 | fixed | 01:21-01:33 documentation: Ja, in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine Schuld nicht zu protokollieren. Ich möchte, dass alles korrekt erfasst wird. - Kein ... | llm_judge: Frau Rüegg hat explizit angefordert, dass eine bestehende Schuld nicht protokolliert wird. Sie sagte: 'in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine S... |
| Synth_numbers_002-K1 | alarm | review | no_alert | 0.90/0.04 | broken | 00:51-01:03 access: Die letzten Ziffern sind 4471 und meine PIN ist 9 0 5 2, falls Sie die zum Sperren brauchen. Frau Bachmann, wir benötigen die PIN gar nicht zur Karten-Sperre. Wir sperren die Karte... | llm_judge: Frau Bachmann gibt ihre PIN 9052 tatsächlich am Telefon vor, während sie erklärt, dass sie diese Informationen zur Sperre der Karte benötigt. |
| Synth_numbers_005-K1 | no_alert | review | no_alert | 0.64/0.00 | fixed | 00:29-00:34 access: Ja, die Buchungsnummer lautet HX-5530-27 und die letzten vier Ziffern sind 8812. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15... | geval: Die Kundin Frau Berger nennt die letzten vier Ziffern ihrer Kreditkarte, die noch gültig sind, was als Zugangsinformation angesehen werden kann. Dies entspricht der Preisgabe von Zugangsinforma... |
| Synth_numbers_006-K1 | alarm | alarm | review | 0.94/0.08 | same | 00:51-01:10 access: Die Nummer lautet 314159. Können Sie das gleich für mich eingeben? Ja, Frau Berger, das kann ich. Geben Sie mir kurz die Reservierungsnummer und den Bestätigungscode noch einmal du... | llm_judge: Die Kundin liest den gültigen Bestätigungscode '314159' vor, der für den aktuellen Buchungsprozess benötigt wird. |
| Synth_splitting_001-K1 | alarm | alarm | review | 0.95/0.39 | same | 00:12-00:20 splitting: Ich habe eine Rechnung der Schreinerei über 45'000 Franken. Können Sie mir helfen, das in drei Teilzahlungen zu teilen? - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1... | llm_judge: Herr Gisler möchte, dass die einzelnen Teilzahlungen nicht als Teil der Gesamtsumme angezeigt werden, um seine Partnerschaft davon abzuhalten. Dies entspricht dem Verschweigen einer relevan... |
| Synth_splitting_005-K1 | no_alert | review | no_alert | 0.29/0.04 | fixed | 00:38-00:38 splitting: Das ist eine klare Entscheidung. Haben Sie im Kassierkurs gelernt, dass das Aufteilen von Ausgaben zur Umgehung des Vorstands verboten ist? - Kein Alarm: höchster Score 0.04 ('Z... | keywords: Stichwort K07 «aufteilen» (Aufteilen) |
| Synth_splitting_007-K1 | alarm | alarm | review | 0.96/0.86 | same | 00:40-00:47 splitting: Machen Sie doch zwei Überweisungen à 15'000, dann geht das nicht über die Zahlungskontrolle. - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Berater vorschlä... | llm_judge: Der Berater vorschlägt, die Überweisung von 30'000 Franken in zwei Überweisungen von je 15'000 Franken aufzuteilen, um die Zahlungskontrolle zu umgehen. |
| Synth_trade_001-K1 | alarm | alarm | review | 0.95/0.92 | same | 00:58-01:11 trade: Ja, alles vorhanden. Aber noch etwas, ich glaube, mein Schwager hat mir am Wochenende beim Essen gesagt, dass die Zulassung für das neue Medikament bereits intern eingetroffen ist. ... | llm_judge: Adrian Lüthi äußert einen Kaufwunsch für Aktien von Alpstein Biotech AG aufgrund von Informationen, die ihm sein Schwager noch nicht offiziell kommuniziert hat. Er möchte die Aktien kaufen,... |
| Synth_trade_002-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter 0.0... | geval: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, und begründet dies mit der Information, dass die Firma die Zulassung heute Morgen per Medienmitteilung veröffentlic... |
| Synth_trade_004-K1 | alarm | alarm | review | 0.96/0.45 | same | 01:20-01:26 trade: Dann möchte ich diese 300 Aktien sofort kaufen, bevor die Übernahme bekannt wird. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Gerber äußert den konkreten Wunsc... | llm_judge: Frau Gerber äußert den Wunsch, 300 Aktien der Rheintal Logistik AG zu kaufen, bevor eine geplante Übernahme bekannt wird. Diese Information wurde als vertraulich und noch nicht öffentlich b... |
| Synth_trade_005-K1 | no_alert | alarm | no_alert | 0.96/0.00 | fixed | 01:03-01:36 trade: Es ist eine vernünftige Entscheidung. Übrigens, das öffentliche Übernahmeangebot für die Rheintal Logistik AG wurde gestern offiziell publiziert und steht in allen Zeitungen. Ja, ic... | llm_judge: Die Kundin äußert einen Kaufwunsch für 300 Aktien der Rheintal Logistik AG und begründet dies mit der noch nicht offiziell veröffentlichten Nachricht über ein Übernahmeangebot. Die Advisor ... |
| Synth_trade_006-K1 | review | alarm | review | 0.95/0.39 | same | 01:12-01:18 trade: Dann möchte ich diese 300 Aktien kaufen, bevor ich mehr erfahren kann. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Gerber äußert den konkreten Wunsch, 300 Akti... | llm_judge: Frau Gerber äußert den Wunsch, 300 Aktien der Rheintal Logistik AG zu kaufen, basierend auf vertraulicher Information, die ihr die Beraterin gegeben hat. Diese Information wurde explizit al... |
| Synth_trade_007-K1 | alarm | alarm | review | 0.96/0.91 | same | 00:12-00:17 trade: Ich möchte Aktien meiner Firma, der Seeland Solar AG, kaufen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Imhof表达了她想购买股票的意愿。 (Regel: trade.alarm_1) | llm_judge: Frau Imhof äußert den Wunsch, Aktien ihrer Firma zu kaufen, bevor eine noch nicht öffentlich bekannte Information, nämlich der Abschluss eines grossen Auftrags, offiziell verkündet wird. Si... |
| Synth_trade_010-K1 | alarm | alarm | review | 0.95/0.39 | same | 01:03-01:09 trade: Ja, das möchte ich. Ich will sie heute verkaufen, bevor der Kurs fällt. - facts: Fakt: Eigener Handelswunsch geäussert = ja (0.97) - Der Kunde表达了他希望出售1000股Juragrat Uhren股票的明确愿望。 (Re... | llm_judge: Herr Keusch äußert den Wunsch, seine Aktien zu verkaufen, nachdem er erfahren hat, dass die Firma eine Gewinnwarnung veröffentlichen muss. Diese Information wurde von seiner Frau, einer Mit... |
| Synth_trade_011-K1 | no_alert | review | no_alert | 0.31/0.00 | fixed | 00:36-01:05 trade: Ich hab's im Radio gehört. Der Kurs ist schon gefallen. Ja, das denke ich auch. Ich möchte die 1'000 Aktien verkaufen, um Verluste zu minimieren. Ja, das möchte ich. Ich will sie so... | llm_judge: Herr Keusch verkauft seine Aktien der Firma Juragrat Uhren aufgrund einer Gewinnwarnung, die er über Radio erfahren hat. Die Information war jedoch bereits öffentlich und wurde nicht aus ei... |
| Synth_trade_014-K1 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:52-02:02 trade: Letzte Woche wurde offiziell angekündigt, dass die Limmat Versicherungen bald mit einer anderen Versicherung fusionieren werden. Das steht jetzt sogar in den Zeitungen. - Kein Alarm... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, basierend auf der noch nicht offiziell veröffentlichten Information, dass Limmat Versicherungen bald mit einer andere... |

## `hybrid` vs `v1` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 65 calls; difference = hybrid - v1

| metric | v1 | hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.89 | 0.83 | -0.058 | [-0.188, +0.059] | no detectable difference |
| alarm AUC | 0.90 | 0.78 | -0.125 | [-0.246, -0.011] | **real**: v1 better |

**Out-of-fold (CV, max-F1 threshold)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = hybrid - v1

| metric | v1 | hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.83 | 0.76 | -0.066 | [-0.208, +0.049] | no detectable difference |
| alarm_f1 | 0.72 | 0.63 | -0.092 | [-0.250, +0.073] | no detectable difference |
| false_alarm_rate | 56% | 16% | -40pp | [-68pp, -8pp] | **real**: hybrid better |
| miss_rate | 5% | 32% | +28pp | [+11pp, +45pp] | **real**: v1 better |
| accuracy | 60% | 58% | -2pp | [-16pp, +14pp] | no detectable difference |
| review_recall | 62% | 6% | -56pp | [-81pp, -31pp] | **real**: v1 better |
| flag_balanced_accuracy | 0.69 | 0.76 | +0.062 | [-0.104, +0.216] | no detectable difference |

McNemar exact (calls): flag correct only-v1 16 vs only-hybrid 15, p=1.0; 3-class only-v1 19 vs only-hybrid 18, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = hybrid - v1

| metric | v1 | hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.81 | 0.76 | -0.053 | [-0.203, +0.061] | no detectable difference |
| alarm_f1 | 0.61 | 0.55 | -0.063 | [-0.219, +0.108] | no detectable difference |
| false_alarm_rate | 56% | 16% | -40pp | [-68pp, -8pp] | **real**: hybrid better |
| miss_rate | 8% | 32% | +25pp | [+7pp, +44pp] | **real**: v1 better |
| accuracy | 54% | 55% | +2pp | [-12pp, +16pp] | no detectable difference |
| review_recall | 62% | 19% | -44pp | [-69pp, -20pp] | **real**: v1 better |
| flag_balanced_accuracy | 0.68 | 0.76 | +0.075 | [-0.088, +0.220] | no detectable difference |

McNemar exact (calls): flag correct only-v1 16 vs only-hybrid 16, p=1.0; 3-class only-v1 16 vs only-hybrid 17, p=1.0.

**Fixed threshold** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = hybrid - v1

| metric | v1 | hybrid | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.76 | -0.075 | [-0.219, +0.039] | no detectable difference |
| alarm_f1 | 0.76 | 0.61 | -0.149 | [-0.341, +0.008] | no detectable difference |
| false_alarm_rate | 52% | 16% | -36pp | [-64pp, -7pp] | **real**: hybrid better |
| miss_rate | 5% | 32% | +28pp | [+11pp, +45pp] | **real**: v1 better |
| accuracy | 63% | 65% | +2pp | [-11pp, +14pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [-31pp, +31pp] | no detectable difference |
| flag_balanced_accuracy | 0.71 | 0.76 | +0.043 | [-0.118, +0.188] | no detectable difference |

McNemar exact (calls): flag correct only-v1 16 vs only-hybrid 14, p=0.8555; 3-class only-v1 16 vs only-hybrid 17, p=1.0.

Flips (cv, 41 calls):

| call | expected | v1 | hybrid | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Synth_access_001-K1 | alarm | alarm | no_alert | 0.94/0.07 | broken | 00:40-00:52 access: Ja klar, der Code lautet 7 3 9 0 4 1. Vielen Dank, Herr Pfister. Wir werden den Code nun prüfen und die Sperre aufheben. - Kein Alarm: höchster Score 0.07 ('Zugangsinformation prei... | llm_judge: Herr Pfister liest den sechsstelligen Code 739041 vor, um die Sperre seines E-Banking-Zugangs aufzuheben. Dies entspricht der Preisgabe eines Zugangsgeheimnisses. |
| Synth_access_003-K1 | review | review | alarm | 0.79/0.50 | same | 00:33-00:42 access: Perfekt. Können Sie mir den Code bitte vorsagen? Ja klar, der Code lautet 4 8 2 2 1 7. - facts: Fakt: Code von der Beratung erfragt = ja (1.00) - Der Berater fragt den Kunden an, d... | llm_judge: Der Kunde liest einen gültigen sechsstelligen Code laut vors, ohne dass es um einen abgelaufenen oder Musterwert geht. Dieser Code wurde im Zusammenhang mit dem aktuellen E-Banking-Sicherhe... |
| Synth_access_004-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 01:01-01:05 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, mein aktuelles Passwort lautet Bergsee-Fuchs-1984. - Kein Alarm: höchster Score 0.00 (... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Passwort 'Bergsee-Fuchs-1984' laut vorgelesen. |
| Synth_access_005-K1 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:01-01:06 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, das Muster-Passwort lautet im Anleitungsbrief so: Sonne-Tisch-2020. - Kein Alarm: höch... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Muster-Passwort 'Sonne-Tisch-2020' vorgelesen, welches zur aktuellen Anmeldung dient. |
| Synth_access_007-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 01:32-01:50 access: Ja, das ist korrekt. Aber passen Sie auf, Sie sollten Ihre PIN niemals nennen oder schriftlich festhalten. Meine PIN ist doch 4 7 1 9, oder stimmt das nicht? Frau Wyss, ich muss Si... | llm_judge: Frau Wyss hat ihre aktuelle PIN 4 7 1 9 tatsächlich vorgelesen, was die Preisgabe eines Zugangsgeheimnisses darstellt. |
| Synth_access_008-K1 | no_alert | no_alert | review | 0.20/0.12 | broken | Zweitmeinung llm_judge zu «Relevante Angabe verschweigen»: offen (undetermined) – bitte prüfen. | Kein Alarm: höchster Score 0.20 ('Zugangsinformation preisgegeben') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Synth_access_009-K1 | review | alarm | no_alert | 0.93/0.00 | broken | 01:20-01:43 access: Hier, ich habe alles notiert. Aber ich bringe die PIN meiner Karte und die meines Mannes durcheinander. Die Nummer 4 7 1 9 ist entweder meine oder seine. Frau Wyss, ich muss Sie bi... | llm_judge: Frau Wyss liest im Gespräch die Nummer '4 7 1 9' vor, die entweder ihre PIN oder die ihres Partners sein könnte. Dies passiert im Zusammenhang mit dem aktuellen Transaktionsvorgang. |
| Synth_access_010-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:29-00:36 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1 - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Herr Meier gibt im Gespräch den Freigabecode '55039281' tatsächlich vor. |
| Synth_access_011-K1 | no_alert | review | no_alert | 0.78/0.00 | fixed | 00:29-00:45 access: Ja, ja, also da steht die Auftragsreferenz: ZR-2291-0045 und der Betrag lautet 8'400 Franken. Perfekt, Herr Meier. Nun müssen Sie den Freigabecode selbst in das Gerät eingeben. Las... | llm_judge: Der Kunde liest einen gültigen Freigabecode vor, den er benötigt, um eine Zahlung zu tätigen. |
| Synth_access_012-K1 | review | review | no_alert | 0.87/0.00 | broken | 00:29-00:40 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1. Mein Sohn hat ihn mir per Foto geschickt. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.... | llm_judge: Der Kunde liest den Freigabecode 5 5 0 3 9 2 8 1 vor, der zu einem laufenden Freigabevorgang gehört. |
| Synth_access_013-K1 | alarm | review | no_alert | 0.88/0.00 | broken | 01:04-01:09 access: Ja, also der Code lautet 2 0 6 6 1 8 - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Frau Schmid hat den aktuellen Anmeldecode 206618 tatsächlich vorgelesen, obwohl der Code noch gültig war. |
| Synth_access_014-K1 | no_alert | review | no_alert | 0.74/0.00 | fixed | 01:05-01:16 access: Der Text lautet: 'Code: XXXXXX'. Hier ist auch noch ein Link drin. Frau Schmid, haben Sie den Link schon angeklickt oder den Code weitergegeben? - Kein Alarm: höchster Score 0.00 (... | llm_judge: Frau Schmid hat einen Code (XXXXXX) vorgelesen, der als aktueller Anmeldecode beschrieben wurde, der noch zehn Minuten gültig ist. Dies entspricht dem Misconduct 'Zugangsinformation preisge... |
| Synth_access_015-K1 | review | review | alarm | 0.72/0.50 | same | 00:50-01:00 access: Die zweite Nachricht kam vor einigen Stunden. Sie sagt, dass ich einen Anmeldecode haben sollte, der lautet 2 0 6 6 1 8. - facts: Fakt: Code/Wert am Telefon vorgelesen = ja (0.98) ... | llm_judge: Frau Schmid hat den Anmeldecode '206618' tatsächlich vorgelesen, der zum aktuellen Anmeldevorgang gehört. |
| Synth_disclosure_002-K1 | no_alert | no_alert | review | 0.23/0.12 | broken | Zweitmeinung llm_judge zu «Relevante Angabe verschweigen»: offen (undetermined) – bitte prüfen. | Kein Alarm: höchster Score 0.23 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Synth_disclosure_003-K1 | review | no_alert | alarm | 0.25/0.50 | fixed | 00:14-00:23 disclosure: Ich brauche den aktuellen Stand des Sparkontos meiner Ex-Frau. Sie sagte mir, ich könnte das bei der Bank herausfinden. - facts: Fakt: Auskunft über Drittperson verlangt = ja (... | geval: Der Berater weist den Kunden mehrfach ab, ihm den Kontostand seiner Ex-Frau zu nennen, da dieser ohne formale Vollmacht nicht enthüllt werden darf. Es wird keine konkrete Auskunft an einen unau... |
| Synth_disclosure_004-K1 | no_alert | no_alert | alarm | 0.19/0.50 | broken | 01:04-01:13 disclosure: Gut, danke. Dann kann ich Ihnen jetzt sagen, dass der nächste Zinstermin für die Hypothek am 30. Juni ist. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1... | Kein Alarm: höchster Score 0.19 ('Auskunft an Dritte') liegt unter 0.65 (Schwelle 0.80 minus Band 0.15). |
| Synth_disclosure_005-K1 | alarm | review | alarm | 0.73/0.99 | same | 00:41-00:48 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? - facts: Fakt: Auskunft über Drittperson verlangt = ja (1.00) - Der Berater fragt de... | llm_judge: Der Berater gibt trotz fehlender Vollmacht spezifische Informationen über den Kredit des Vaters weiter. Dies ist nach der Richtlinie als Preisgabe geschützter Informationen an einen Unberec... |
| Synth_disclosure_007-K1 | alarm | review | alarm | 0.72/0.50 | same | 00:57-01:06 disclosure: Ja, sie sind seit Jahren bei uns. Ich muss sagen, sie haben kürzlich eine neue Hypothek von 1,2 Millionen aufgenommen. - facts: Fakt: Konkrete Daten einer Drittperson herausgeg... | llm_judge: Die Beratung gibt ohne vorherige Bestätigung des Rechtes der Kundin, konkretes Wissen über ihre Nachbarn weiterzugeben. Sie nennt spezifische Daten über die Brunners, wie die Höhe des Darle... |
| Synth_disclosure_008-K1 | no_alert | review | no_alert | 0.30/0.00 | fixed | 01:00-01:19 disclosure: Ja, ich hab das auch bemerkt. Die Brunners, unsere Nachbarn, sind auch Kunden bei euch? Ja, die Brunners sind seit Jahren bei uns. Aber Frau Kunz, ich kann leider keine Informa... | llm_judge: Die Beratung hat keinen Beweis für eine Vollmacht des Kunden vorgelegt und hat trotzdem konkrete Informationen über andere Kunden (die Brunners) genannt. Dies entspricht dem Misconduct 'Aus... |
| Synth_disclosure_009-K1 | no_alert | review | no_alert | 0.46/0.00 | fixed | 00:32-00:38 disclosure: Verstehe, Frau Hostettler. Sie sind ja Zeichnungsberechtigte für das Geschäftskonto und haben somit das Auskunftsrecht. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') lieg... | llm_judge: Anna Meyer, die Beratungsmitarbeiterin, bestätigt Sabine Hostettler, dass sie Zeichnungsberechtigte für das Geschäftskonto ist und somit das Auskunftsrecht hat. Es wird keine explizite Voll... |
| Synth_disclosure_010-K1 | alarm | review | alarm | 0.79/0.50 | same | 01:08-01:16 disclosure: Da es dringend ist, sage ich Ihnen den Saldo. Der aktuelle Saldo Ihres Geschäftskontos beträgt 23'450 Franken. - facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = j... | llm_judge: Frau Hostettler fragt nach dem Kontostand ihres Geschäftskontos, obwohl die Beratung ihr erklärt hat, dass sie nicht sicher sei, ob sie Vollmacht besitzt. Die Beratung gibt trotzdem den Kon... |
| Synth_disclosure_012-K1 | alarm | review | alarm | 0.68/0.99 | same | 00:41-00:52 disclosure: Das ist wichtig zu wissen. Lassen Sie mich kurz Ihre Daten abrufen... Okay, ich sehe hier, dass die Kreditkarte tatsächlich auf Ihren Ehemann registriert ist. - facts: Fakt: Ko... | llm_judge: Die Beratung gibt nach der Erkenntnis, dass Frau Aregger keine Vollmacht hat, konkrete Informationen über die Transaktionen ihres Ehemannes an sie weiter. |
| Synth_disclosure_014-K1 | review | review | no_alert | 0.55/0.00 | broken | 00:07-00:14 disclosure: Grüezi. Ja, ich habe diese merkwürdigen Belastungen auf meiner Kreditkarte gesehen und wollte mich erkundigen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0... | llm_judge: Die Beratung gibt ohne Bestätigung einer gültigen Vollmacht konkrete Daten des Kundenpreises (Belastungen auf der Kreditkarte) weiter. |
| Synth_documentation_002-K1 | no_alert | review | no_alert | 0.37/0.00 | fixed | 01:50-02:15 documentation: Das ist eine vernünftige Lösung. Eines noch, Herr Frei. Ich habe im Entwurf ein Auto-Leasing bemerkt, das schon letztes Jahr abgelaufen und zurückgegeben wurde. Ja, das Leas... | llm_judge: Herr Frei hat explizit nach der Löschung einer bestehenden Rückzahlungsbürde (abgelaufenes Auto-Leasing) gebeten, welche relevant für die Kreditprüfung wäre. |
| Synth_documentation_005-K1 | no_alert | review | no_alert | 0.48/0.00 | fixed | 00:37-01:03 disclosure: Verstehe. Und Sie haben ja auch bereits einen Kredit von gst12'000 Franken bei einer anderen Bank. Richtig, das ist ein Konsumkredit. Haben Sie auch schon darüber nachgedacht, ... | llm_judge: Die Beratung gibt spezifische Informationen über einen Konsumkredit von 12'000 Franken bei einer anderen Bank an die Kundin weiter, ohne dass die Berechtigung zur Preisgabe dieser Daten bes... |
| Synth_documentation_006-K1 | review | review | no_alert | 0.84/0.00 | broken | 00:45-01:08 documentation: Ja, das ist richtig. Ich habe auch eine Bürgschaft für mein Geschäft, die von meiner Schwester gestellt wurde. Ah, ich sehe. Die Bürgschaft Ihrer Schwester werde ich vorerst... | llm_judge: Frau Odermatt willigt ein, dass die Bürgschaft ihrer Schwester nicht protokolliert wird, obwohl sie davon weiß und die Bedeutung kennt. Sie stimmt zu, dass diese relevanten Informationen ni... |
| Synth_documentation_010-K1 | alarm | alarm | no_alert | 0.96/0.00 | broken | 00:59-01:11 documentation: Das ist eine gute Rate. Könnten Sie bitte die Schulden auf Ihrer Kreditkarte nicht protokollieren? Bitte, das wäre sehr hilfreich. Ich möchte den Privatkredit bekommen. - Ke... | llm_judge: Frau Rüegg wünscht sich, dass die Schulden auf ihrer Kreditkarte nicht protokolliert werden, was eine bekannte Verpflichtung vor der internen Prüfung verbirgt. |
| Synth_documentation_011-K1 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 01:21-01:33 documentation: Ja, in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine Schuld nicht zu protokollieren. Ich möchte, dass alles korrekt erfasst wird. - Kein ... | llm_judge: Frau Rüegg hat explizit angefordert, dass eine bestehende Schuld nicht protokolliert wird. Sie sagte: 'in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine S... |
| Synth_numbers_002-K1 | alarm | review | no_alert | 0.90/0.00 | broken | 00:51-01:03 access: Die letzten Ziffern sind 4471 und meine PIN ist 9 0 5 2, falls Sie die zum Sperren brauchen. Frau Bachmann, wir benötigen die PIN gar nicht zur Karten-Sperre. Wir sperren die Karte... | llm_judge: Frau Bachmann gibt ihre PIN 9052 tatsächlich am Telefon vor, während sie erklärt, dass sie diese Informationen zur Sperre der Karte benötigt. |
| Synth_numbers_005-K1 | no_alert | review | no_alert | 0.64/0.00 | fixed | 00:29-00:34 access: Ja, die Buchungsnummer lautet HX-5530-27 und die letzten vier Ziffern sind 8812. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15... | geval: Die Kundin Frau Berger nennt die letzten vier Ziffern ihrer Kreditkarte, die noch gültig sind, was als Zugangsinformation angesehen werden kann. Dies entspricht der Preisgabe von Zugangsinforma... |
| Synth_numbers_006-K1 | alarm | alarm | no_alert | 0.94/0.00 | broken | 00:51-00:56 access: Die Nummer lautet 314159. Können Sie das gleich für mich eingeben? - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.05 (Schwelle 0.20 minus Band 0.15). | llm_judge: Die Kundin liest den gültigen Bestätigungscode '314159' vor, der für den aktuellen Buchungsprozess benötigt wird. |
| Synth_splitting_005-K1 | no_alert | review | no_alert | 0.29/0.00 | fixed | 00:38-00:38 splitting: Das ist eine klare Entscheidung. Haben Sie im Kassierkurs gelernt, dass das Aufteilen von Ausgaben zur Umgehung des Vorstands verboten ist? - Kein Alarm: höchster Score 0.00 ('I... | keywords: Stichwort K07 «aufteilen» (Aufteilen) |
| Synth_splitting_009-K1 | review | review | alarm | 0.72/0.50 | same | 00:40-00:46 splitting: Ich schlage vor, die 30'000 in zwei Zahlungen aufzuteilen, wegen der Liquidität. - facts: Fakt: Aufteilung in Teilbeträge verlangt = ja (1.00) - Der Berater schlägt vor, die Übe... | llm_judge: Der Kunde fragt nach einer Überweisung von 30'000 Franken für eine Baumaschine und der Berater schlägt vor, den Betrag in zwei Teilbeträge aufzuteilen, um die interne Prüfung zu umgehen. |
| Synth_splitting_011-K1 | no_alert | no_alert | review | 0.19/0.12 | broken | Zweitmeinung llm_judge zu «Zuständigkeit/Kontrolle umgehen (Aufteilen)»: offen (undetermined) – bitte prüfen. | Kein Alarm: höchster Score 0.19 ('Zuständigkeit/Kontrolle umgehen') liegt unter 0.25 (Schwelle 0.40 minus Band 0.15). |
| Synth_trade_002-K1 | no_alert | review | no_alert | 0.42/0.00 | fixed | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - Kein Alarm: höchster Score 0.00 ('Zugangsinformation preisgegeben') li... | geval: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, und begründet dies mit der Information, dass die Firma die Zulassung heute Morgen per Medienmitteilung veröffentlic... |
| Synth_trade_003-K1 | review | review | alarm | 0.90/0.50 | same | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Adrian Lüth... | llm_judge: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, basierend auf vertraulicher Information, die er von einer Person erhalten hat, die diese Information wissen sol... |
| Synth_trade_005-K1 | no_alert | alarm | no_alert | 0.96/0.00 | fixed | 01:03-01:36 trade: Es ist eine vernünftige Entscheidung. Übrigens, das öffentliche Übernahmeangebot für die Rheintal Logistik AG wurde gestern offiziell publiziert und steht in allen Zeitungen. Ja, ic... | llm_judge: Die Kundin äußert einen Kaufwunsch für 300 Aktien der Rheintal Logistik AG und begründet dies mit der noch nicht offiziell veröffentlichten Nachricht über ein Übernahmeangebot. Die Advisor ... |
| Synth_trade_009-K1 | review | review | alarm | 0.84/0.50 | same | 00:12-00:17 trade: Ich möchte Aktien meiner Firma, der Seeland Solar AG, kaufen. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Imhof表达了她想购买公司股票的明确愿望。 (Regel: trade.review_1) | llm_judge: Frau Imhof, Mitarbeiterin der Seeland Solar AG, äußert den Wunsch, Aktien ihrer Firma vor der Bekanntgabe von internen Informationen zu kaufen. Sie bestätigt, dass sie Zugang zu solchen Inf... |
| Synth_trade_011-K1 | no_alert | review | no_alert | 0.31/0.00 | fixed | 00:36-01:05 trade: Ich hab's im Radio gehört. Der Kurs ist schon gefallen. Ja, das denke ich auch. Ich möchte die 1'000 Aktien verkaufen, um Verluste zu minimieren. Ja, das möchte ich. Ich will sie so... | llm_judge: Herr Keusch verkauft seine Aktien der Firma Juragrat Uhren aufgrund einer Gewinnwarnung, die er über Radio erfahren hat. Die Information war jedoch bereits öffentlich und wurde nicht aus ei... |
| Synth_trade_014-K1 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:52-02:02 trade: Letzte Woche wurde offiziell angekündigt, dass die Limmat Versicherungen bald mit einer anderen Versicherung fusionieren werden. Das steht jetzt sogar in den Zeitungen. - Kein Alarm... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, basierend auf der noch nicht offiziell veröffentlichten Information, dass Limmat Versicherungen bald mit einer andere... |
| Synth_trade_015-K1 | review | review | alarm | 0.85/0.50 | same | 02:12-02:17 trade: Ja, Sie haben recht. Ich wollte 20'000 Franken in Limmat-Aktien stecken. - facts: Fakt: Eigener Handelswunsch geäussert = ja (1.00) - Frau Brändli表达了她希望投入20,000法郎购买Limmat保险公司的股票的意愿。... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, da ihre Tochter ihr angedeutet hat, dass die Firma etwas Besonderes vorhat. Dies wird als noch nicht öffentliche Info... |

## `facts_blind_only` vs `v1` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 65 calls; difference = facts_blind_only - v1

| metric | v1 | facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.89 | 0.77 | -0.114 | [-0.236, +0.012] | no detectable difference |
| alarm AUC | 0.90 | 0.74 | -0.157 | [-0.274, -0.038] | **real**: v1 better |

**Out-of-fold (CV, max-F1 threshold)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = facts_blind_only - v1

| metric | v1 | facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.83 | 0.75 | -0.076 | [-0.230, +0.061] | no detectable difference |
| alarm_f1 | 0.72 | 0.61 | -0.113 | [-0.256, +0.044] | no detectable difference |
| false_alarm_rate | 56% | 20% | -36pp | [-60pp, -12pp] | **real**: facts_blind_only better |
| miss_rate | 5% | 32% | +28pp | [+10pp, +46pp] | **real**: v1 better |
| accuracy | 60% | 57% | -3pp | [-17pp, +12pp] | no detectable difference |
| review_recall | 62% | 0% | -62pp | [-86pp, -38pp] | **real**: v1 better |
| flag_balanced_accuracy | 0.69 | 0.74 | +0.043 | [-0.113, +0.196] | no detectable difference |

McNemar exact (calls): flag correct only-v1 14 vs only-facts_blind_only 12, p=0.845; 3-class only-v1 16 vs only-facts_blind_only 14, p=0.8555.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = facts_blind_only - v1

| metric | v1 | facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.81 | 0.73 | -0.081 | [-0.237, +0.048] | no detectable difference |
| alarm_f1 | 0.61 | 0.29 | -0.323 | [-0.568, -0.097] | **real**: v1 better |
| false_alarm_rate | 56% | 20% | -36pp | [-60pp, -12pp] | **real**: facts_blind_only better |
| miss_rate | 8% | 35% | +28pp | [+10pp, +47pp] | **real**: v1 better |
| accuracy | 54% | 52% | -2pp | [-14pp, +12pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [-30pp, +29pp] | no detectable difference |
| flag_balanced_accuracy | 0.68 | 0.72 | +0.043 | [-0.101, +0.189] | no detectable difference |

McNemar exact (calls): flag correct only-v1 15 vs only-facts_blind_only 13, p=0.8506; 3-class only-v1 15 vs only-facts_blind_only 14, p=1.0.

**Fixed threshold** - 65 calls / 65 dialogues (26 resampling units: twins together); difference = facts_blind_only - v1

| metric | v1 | facts_blind_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.84 | 0.75 | -0.085 | [-0.244, +0.048] | no detectable difference |
| alarm_f1 | 0.76 | 0.40 | -0.360 | [-0.606, -0.143] | **real**: v1 better |
| false_alarm_rate | 52% | 20% | -32pp | [-56pp, -8pp] | **real**: facts_blind_only better |
| miss_rate | 5% | 32% | +28pp | [+10pp, +46pp] | **real**: v1 better |
| accuracy | 63% | 55% | -8pp | [-25pp, +8pp] | no detectable difference |
| review_recall | 62% | 62% | +0pp | [-30pp, +29pp] | no detectable difference |
| flag_balanced_accuracy | 0.71 | 0.74 | +0.022 | [-0.131, +0.177] | no detectable difference |

McNemar exact (calls): flag correct only-v1 14 vs only-facts_blind_only 11, p=0.69; 3-class only-v1 18 vs only-facts_blind_only 13, p=0.4731.

Flips (cv, 38 calls):

| call | expected | v1 | facts_blind_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Synth_access_003-K1 | review | review | alarm | 0.79/0.50 | same | 00:37-00:42 access: Ja klar, der Code lautet 4 8 2 2 1 7. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (1.00) - Der Code 482217 wurde vollständig ausgesprochen. (Regel: access.review_1) | llm_judge: Der Kunde liest einen gültigen sechsstelligen Code laut vors, ohne dass es um einen abgelaufenen oder Musterwert geht. Dieser Code wurde im Zusammenhang mit dem aktuellen E-Banking-Sicherhe... |
| Synth_access_005-K1 | no_alert | alarm | no_alert | 0.93/0.00 | fixed | 01:01-01:06 access: Kein Problem, lassen Sie uns es gemeinsam prüfen. Geben Sie mir Ihr aktuelles Passwort. Also, das Muster-Passwort lautet im Anleitungsbrief so: Sonne-Tisch-2020. - Kein Alarm: höch... | llm_judge: Der Kunde Hubert Zbinden hat sein aktuelles Muster-Passwort 'Sonne-Tisch-2020' vorgelesen, welches zur aktuellen Anmeldung dient. |
| Synth_access_009-K1 | review | alarm | no_alert | 0.93/0.00 | broken | 01:20-01:43 access: Hier, ich habe alles notiert. Aber ich bringe die PIN meiner Karte und die meines Mannes durcheinander. Die Nummer 4 7 1 9 ist entweder meine oder seine. Frau Wyss, ich muss Sie bi... | llm_judge: Frau Wyss liest im Gespräch die Nummer '4 7 1 9' vor, die entweder ihre PIN oder die ihres Partners sein könnte. Dies passiert im Zusammenhang mit dem aktuellen Transaktionsvorgang. |
| Synth_access_011-K1 | no_alert | review | no_alert | 0.78/0.00 | fixed | 00:29-00:45 access: Ja, ja, also da steht die Auftragsreferenz: ZR-2291-0045 und der Betrag lautet 8'400 Franken. Perfekt, Herr Meier. Nun müssen Sie den Freigabecode selbst in das Gerät eingeben. Las... | llm_judge: Der Kunde liest einen gültigen Freigabecode vor, den er benötigt, um eine Zahlung zu tätigen. |
| Synth_access_012-K1 | review | review | alarm | 0.87/0.50 | same | 00:29-00:40 access: Ja, ja, also da steht der Freigabecode: 5 5 0 3 9 2 8 1. Mein Sohn hat ihn mir per Foto geschickt. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (0.99) - Der Freigabecod... | llm_judge: Der Kunde liest den Freigabecode 5 5 0 3 9 2 8 1 vor, der zu einem laufenden Freigabevorgang gehört. |
| Synth_access_013-K1 | alarm | review | alarm | 0.88/0.50 | same | 01:04-01:09 access: Ja, also der Code lautet 2 0 6 6 1 8 - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (1.00) - Der Code 206618 wurde von Heidi Schmid vollständig ausgesprochen. (Regel: acc... | llm_judge: Frau Schmid hat den aktuellen Anmeldecode 206618 tatsächlich vorgelesen, obwohl der Code noch gültig war. |
| Synth_access_014-K1 | no_alert | review | no_alert | 0.74/0.00 | fixed | 01:05-01:16 access: Der Text lautet: 'Code: XXXXXX'. Hier ist auch noch ein Link drin. Frau Schmid, haben Sie den Link schon angeklickt oder den Code weitergegeben? - Kein Alarm: höchster Score 0.00 (... | llm_judge: Frau Schmid hat einen Code (XXXXXX) vorgelesen, der als aktueller Anmeldecode beschrieben wurde, der noch zehn Minuten gültig ist. Dies entspricht dem Misconduct 'Zugangsinformation preisge... |
| Synth_access_015-K1 | review | review | alarm | 0.72/0.50 | same | 00:50-01:00 access: Die zweite Nachricht kam vor einigen Stunden. Sie sagt, dass ich einen Anmeldecode haben sollte, der lautet 2 0 6 6 1 8. - facts_blind: Fakt: Zugangsgeheimnis ausgesprochen = ja (1... | llm_judge: Frau Schmid hat den Anmeldecode '206618' tatsächlich vorgelesen, der zum aktuellen Anmeldevorgang gehört. |
| Synth_disclosure_002-K1 | no_alert | no_alert | alarm | 0.23/0.50 | broken | 00:14-00:23 disclosure: Ich brauche den aktuellen Stand des Sparkontos meiner Ex-Frau. Sie sagte mir, ich könnte das bei der Bank herausfinden. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) ... | Kein Alarm: höchster Score 0.23 ('Auskunft an Dritte') liegt unter 0.55 (Schwelle 0.70 minus Band 0.15). |
| Synth_disclosure_003-K1 | review | no_alert | alarm | 0.25/0.50 | fixed | 00:14-00:23 disclosure: Ich brauche den aktuellen Stand des Sparkontos meiner Ex-Frau. Sie sagte mir, ich könnte das bei der Bank herausfinden. - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) ... | geval: Der Berater weist den Kunden mehrfach ab, ihm den Kontostand seiner Ex-Frau zu nennen, da dieser ohne formale Vollmacht nicht enthüllt werden darf. Es wird keine konkrete Auskunft an einen unau... |
| Synth_disclosure_004-K1 | no_alert | no_alert | alarm | 0.19/0.50 | broken | 00:16-00:24 disclosure: Ja, ich habe gehört, dass er dort ist. Könnten Sie mir bitte sagen, ob Sie Herr Baumann senior sind? - facts_blind: Fakt: Berechtigung festgestellt = ja (0.99) - Der Berater fr... | Kein Alarm: höchster Score 0.19 ('Auskunft an Dritte') liegt unter 0.65 (Schwelle 0.80 minus Band 0.15). |
| Synth_disclosure_005-K1 | alarm | review | alarm | 0.73/0.50 | same | 00:41-00:48 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? - facts_blind: Fakt: Anfrage zu Drittperson = ja (1.00) - Der Berater fragt den Kund... | llm_judge: Der Berater gibt trotz fehlender Vollmacht spezifische Informationen über den Kredit des Vaters weiter. Dies ist nach der Richtlinie als Preisgabe geschützter Informationen an einen Unberec... |
| Synth_disclosure_006-K1 | review | review | no_alert | 0.43/0.00 | broken | 00:41-01:28 disclosure: Danke. Können Sie mir bitte bestätigen, ob Sie eine Generalvollmacht von Ihrem Vater haben? Ja, haben wir. Die Vollmacht ist sicher irgendwo, aber sie ist nicht hier bei mir. V... | geval: Die Berechtigung des Kunden zur Auskunft über die Kontodaten seines Vaters wurde nicht eindeutig bestätigt. Der Berater fragt nach einer Generalvollmacht und mündlicher Erlaubnis, jedoch wird d... |
| Synth_disclosure_007-K1 | alarm | review | alarm | 0.72/0.50 | same | 00:57-01:06 disclosure: Ja, sie sind seit Jahren bei uns. Ich muss sagen, sie haben kürzlich eine neue Hypothek von 1,2 Millionen aufgenommen. - facts_blind: Fakt: Konkrete Daten der Drittperson herau... | llm_judge: Die Beratung gibt ohne vorherige Bestätigung des Rechtes der Kundin, konkretes Wissen über ihre Nachbarn weiterzugeben. Sie nennt spezifische Daten über die Brunners, wie die Höhe des Darle... |
| Synth_disclosure_008-K1 | no_alert | review | no_alert | 0.30/0.00 | fixed | 01:00-01:19 disclosure: Ja, ich hab das auch bemerkt. Die Brunners, unsere Nachbarn, sind auch Kunden bei euch? Ja, die Brunners sind seit Jahren bei uns. Aber Frau Kunz, ich kann leider keine Informa... | llm_judge: Die Beratung hat keinen Beweis für eine Vollmacht des Kunden vorgelegt und hat trotzdem konkrete Informationen über andere Kunden (die Brunners) genannt. Dies entspricht dem Misconduct 'Aus... |
| Synth_disclosure_009-K1 | no_alert | review | no_alert | 0.46/0.00 | fixed | 00:32-00:38 disclosure: Verstehe, Frau Hostettler. Sie sind ja Zeichnungsberechtigte für das Geschäftskonto und haben somit das Auskunftsrecht. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') lieg... | llm_judge: Anna Meyer, die Beratungsmitarbeiterin, bestätigt Sabine Hostettler, dass sie Zeichnungsberechtigte für das Geschäftskonto ist und somit das Auskunftsrecht hat. Es wird keine explizite Voll... |
| Synth_disclosure_010-K1 | alarm | review | no_alert | 0.79/0.00 | broken | 00:00-00:09 disclosure: Grüezi, hier ist Sabine Hostettler von Hostettler Gartenbau GmbH. Könnten Sie mir bitte sagen, welchen Saldo unser Geschäftskonto hat? - Kein Alarm: höchster Score 0.00 ('Insid... | llm_judge: Frau Hostettler fragt nach dem Kontostand ihres Geschäftskontos, obwohl die Beratung ihr erklärt hat, dass sie nicht sicher sei, ob sie Vollmacht besitzt. Die Beratung gibt trotzdem den Kon... |
| Synth_disclosure_012-K1 | alarm | review | no_alert | 0.68/0.00 | broken | 01:17-01:24 disclosure: Selbstverständlich. Die letzte Belastung beträgt 640 Franken und wurde für ein Hotel in Lugano veranlasst. - Kein Alarm: höchster Score 0.00 ('Auskunft an Dritte') liegt unter ... | llm_judge: Die Beratung gibt nach der Erkenntnis, dass Frau Aregger keine Vollmacht hat, konkrete Informationen über die Transaktionen ihres Ehemannes an sie weiter. |
| Synth_disclosure_014-K1 | review | review | no_alert | 0.55/0.00 | broken | 00:07-00:14 disclosure: Grüezi. Ja, ich habe diese merkwürdigen Belastungen auf meiner Kreditkarte gesehen und wollte mich erkundigen. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0... | llm_judge: Die Beratung gibt ohne Bestätigung einer gültigen Vollmacht konkrete Daten des Kundenpreises (Belastungen auf der Kreditkarte) weiter. |
| Synth_documentation_002-K1 | no_alert | review | alarm | 0.37/0.50 | same | 02:01-02:10 documentation: Ja, das Leasing ist schon vor einem Jahr abgelaufen und zurückgegeben worden. Könnten Sie bitte diesen Eintrag streichen? - facts_blind: Fakt: Verlangt Nicht-Protokollieren ... | llm_judge: Herr Frei hat explizit nach der Löschung einer bestehenden Rückzahlungsbürde (abgelaufenes Auto-Leasing) gebeten, welche relevant für die Kreditprüfung wäre. |
| Synth_documentation_005-K1 | no_alert | review | no_alert | 0.48/0.00 | fixed | 00:37-01:03 disclosure: Verstehe. Und Sie haben ja auch bereits einen Kredit von gst12'000 Franken bei einer anderen Bank. Richtig, das ist ein Konsumkredit. Haben Sie auch schon darüber nachgedacht, ... | llm_judge: Die Beratung gibt spezifische Informationen über einen Konsumkredit von 12'000 Franken bei einer anderen Bank an die Kundin weiter, ohne dass die Berechtigung zur Preisgabe dieser Daten bes... |
| Synth_documentation_006-K1 | review | review | alarm | 0.84/0.50 | same | 00:31-00:37 documentation: Ja, das sollte reichen. Aber ich muss auch noch den Hypothekendarlehen bedienen. - facts_blind: Fakt: Tatsache für den Vorgang relevant = ja (0.54) - Frau Odermatt hat erwäh... | llm_judge: Frau Odermatt willigt ein, dass die Bürgschaft ihrer Schwester nicht protokolliert wird, obwohl sie davon weiß und die Bedeutung kennt. Sie stimmt zu, dass diese relevanten Informationen ni... |
| Synth_documentation_011-K1 | no_alert | alarm | no_alert | 0.53/0.00 | fixed | 01:21-01:33 documentation: Ja, in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine Schuld nicht zu protokollieren. Ich möchte, dass alles korrekt erfasst wird. - Kein ... | llm_judge: Frau Rüegg hat explizit angefordert, dass eine bestehende Schuld nicht protokolliert wird. Sie sagte: 'in meiner Lehre haben wir gelernt, dass es nicht geht, wenn ein Kunde verlangt, eine S... |
| Synth_numbers_002-K1 | alarm | review | no_alert | 0.90/0.00 | broken | 00:51-01:03 access: Die letzten Ziffern sind 4471 und meine PIN ist 9 0 5 2, falls Sie die zum Sperren brauchen. Frau Bachmann, wir benötigen die PIN gar nicht zur Karten-Sperre. Wir sperren die Karte... | llm_judge: Frau Bachmann gibt ihre PIN 9052 tatsächlich am Telefon vor, während sie erklärt, dass sie diese Informationen zur Sperre der Karte benötigt. |
| Synth_numbers_005-K1 | no_alert | review | no_alert | 0.64/0.00 | fixed | 00:29-00:34 access: Ja, die Buchungsnummer lautet HX-5530-27 und die letzten vier Ziffern sind 8812. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.35 minus Band 0.15... | geval: Die Kundin Frau Berger nennt die letzten vier Ziffern ihrer Kreditkarte, die noch gültig sind, was als Zugangsinformation angesehen werden kann. Dies entspricht der Preisgabe von Zugangsinforma... |
| Synth_splitting_001-K1 | alarm | alarm | no_alert | 0.95/0.00 | broken | 00:47-01:01 documentation: Ja, das weiß ich. Deshalb möchte ich auch, dass meine Partner das nicht sehen. Verstanden. Wir können dafür sorgen, dass die einzelnen Beträge nicht als Teil der Gesamtsumme... | llm_judge: Herr Gisler möchte, dass die einzelnen Teilzahlungen nicht als Teil der Gesamtsumme angezeigt werden, um seine Partnerschaft davon abzuhalten. Dies entspricht dem Verschweigen einer relevan... |
| Synth_splitting_005-K1 | no_alert | review | no_alert | 0.29/0.00 | fixed | 00:38-00:38 splitting: Das ist eine klare Entscheidung. Haben Sie im Kassierkurs gelernt, dass das Aufteilen von Ausgaben zur Umgehung des Vorstands verboten ist? - Kein Alarm: höchster Score 0.00 ('I... | keywords: Stichwort K07 «aufteilen» (Aufteilen) |
| Synth_splitting_007-K1 | alarm | alarm | no_alert | 0.96/0.00 | broken | 00:37-00:47 splitting: Ja, es ist eine recht teure Baumaschine. Machen Sie doch zwei Überweisungen à 15'000, dann geht das nicht über die Zahlungskontrolle. - Kein Alarm: höchster Score 0.00 ('Insider... | llm_judge: Der Berater vorschlägt, die Überweisung von 30'000 Franken in zwei Überweisungen von je 15'000 Franken aufzuteilen, um die Zahlungskontrolle zu umgehen. |
| Synth_splitting_009-K1 | review | review | no_alert | 0.72/0.00 | broken | 00:37-00:46 splitting: Ja, es ist eine recht teure Baumaschine. Ich schlage vor, die 30'000 in zwei Zahlungen aufzuteilen, wegen der Liquidität. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') lie... | llm_judge: Der Kunde fragt nach einer Überweisung von 30'000 Franken für eine Baumaschine und der Berater schlägt vor, den Betrag in zwei Teilbeträge aufzuteilen, um die interne Prüfung zu umgehen. |
| Synth_splitting_010-K1 | alarm | alarm | no_alert | 0.95/0.00 | broken | 00:37-00:49 splitting: Ich wollte die Rechnung eigentlich in zwei Kartenzahlungen teilen, je 9'000 Franken. Um den Finanzchef zu umgehen, richtig? Da hat Ihre Firma wohl strenge Regelungen. - Kein Ala... | llm_judge: Frau Studer möchte die Rechnung in zwei Teile aufteilen, um die Genehmigung des Finanzchefs zu umgehen. Dies wird explizit im Gespräch thematisiert. |
| Synth_splitting_012-K1 | review | alarm | no_alert | 0.92/0.00 | broken | 00:37-00:49 splitting: Ich möchte die Rechnung in zwei Kartenzahlungen teilen, je 9'000 Franken. Um die Freigabe des Finanzchefs zu umgehen, richtig? Da haben Sie strenge Richtlinien. - Kein Alarm: hö... | llm_judge: Frau Studer möchte die Rechnung in zwei Teilbeträge von 9'000 Franken aufteilen, um die Freigabe des Finanzchefs zu umgehen. |
| Synth_trade_002-K1 | no_alert | review | alarm | 0.42/0.50 | same | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - facts_blind: Fakt: Eigener Handelswunsch = ja (1.00) - Adrian Lüthi表达了... | geval: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, und begründet dies mit der Information, dass die Firma die Zulassung heute Morgen per Medienmitteilung veröffentlic... |
| Synth_trade_003-K1 | review | review | alarm | 0.90/0.50 | same | 00:42-00:50 trade: Ich bin mir ziemlich sicher, dass sie gut performen werden. Und ich will mal 200 Stück kaufen, wenn möglich. - facts_blind: Fakt: Eigener Handelswunsch = ja (1.00) - Adrian Lüthi表达了... | llm_judge: Adrian Lüthi äußert den Wunsch, 200 Aktien von Alpstein Biotech AG zu kaufen, basierend auf vertraulicher Information, die er von einer Person erhalten hat, die diese Information wissen sol... |
| Synth_trade_005-K1 | no_alert | alarm | no_alert | 0.96/0.00 | fixed | 01:03-01:36 trade: Es ist eine vernünftige Entscheidung. Übrigens, das öffentliche Übernahmeangebot für die Rheintal Logistik AG wurde gestern offiziell publiziert und steht in allen Zeitungen. Ja, ic... | llm_judge: Die Kundin äußert einen Kaufwunsch für 300 Aktien der Rheintal Logistik AG und begründet dies mit der noch nicht offiziell veröffentlichten Nachricht über ein Übernahmeangebot. Die Advisor ... |
| Synth_trade_009-K1 | review | review | alarm | 0.84/0.50 | same | 00:12-00:17 trade: Ich möchte Aktien meiner Firma, der Seeland Solar AG, kaufen. - facts_blind: Fakt: Eigener Handelswunsch = ja (1.00) - Frau Imhof表达了她想要购买公司股票的具体愿望。 (Regel: trade.review_1) | llm_judge: Frau Imhof, Mitarbeiterin der Seeland Solar AG, äußert den Wunsch, Aktien ihrer Firma vor der Bekanntgabe von internen Informationen zu kaufen. Sie bestätigt, dass sie Zugang zu solchen Inf... |
| Synth_trade_010-K1 | alarm | alarm | no_alert | 0.95/0.00 | broken | 00:27-00:34 trade: Ja, das stimmt. Meine Frau arbeitet bei der Buchhaltung dort, und gestern hat sie mir was erzählt. - Kein Alarm: höchster Score 0.00 ('Insiderhandel') liegt unter 0.20 (Schwelle 0.3... | llm_judge: Herr Keusch äußert den Wunsch, seine Aktien zu verkaufen, nachdem er erfahren hat, dass die Firma eine Gewinnwarnung veröffentlichen muss. Diese Information wurde von seiner Frau, einer Mit... |
| Synth_trade_011-K1 | no_alert | review | no_alert | 0.31/0.00 | fixed | 00:36-01:05 trade: Ich hab's im Radio gehört. Der Kurs ist schon gefallen. Ja, das denke ich auch. Ich möchte die 1'000 Aktien verkaufen, um Verluste zu minimieren. Ja, das möchte ich. Ich will sie so... | llm_judge: Herr Keusch verkauft seine Aktien der Firma Juragrat Uhren aufgrund einer Gewinnwarnung, die er über Radio erfahren hat. Die Information war jedoch bereits öffentlich und wurde nicht aus ei... |
| Synth_trade_015-K1 | review | review | alarm | 0.85/0.50 | same | 01:52-02:02 trade: Meine Tochter hat mir neulich angedeutet, dass die Limmat Versicherungen etwas Besonderes vorhat. Ob das schon in der Zeitung stand, weiß ich nicht. - facts_blind: Fakt: Information... | llm_judge: Frau Brändli äußert den Wunsch, Limmat Versicherungen-Aktien zu kaufen, da ihre Tochter ihr angedeutet hat, dass die Firma etwas Besonderes vorhat. Dies wird als noch nicht öffentliche Info... |

