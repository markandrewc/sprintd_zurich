# Experiment `smoke`

Plumbing check on demo-offline (reference scripts + fake LLM); numbers are meaningless.

RQ: - · base profile `demo-offline` · split **dev** · baseline `all` · commit a72e6a6f84 (dirty) · 2026-10-10T01:49:15+0200 · bootstrap 2000x over twin groups / dialogues (seed 13)

Flag = alarm or review (a human listens). FAR = flagged harmless / harmless. miss = unflagged flaggable / flaggable. CV = threshold chosen on the other dev folds (primary number); fixed = the variant's configured threshold. With ~24 dev dialogues (~18 independent units once the Stufe2 twins are paired), CIs are wide: a difference counts only if its CI excludes 0.

**Floor on these 48 calls** (prevalence of alarm|review 54%): flag-all = flag F1 0.70, FAR 100%, miss 0%, bal. acc 0.50, 3-class acc 42%; flag-none = flag F1 0.00, FAR 0%, miss 100%, 3-class acc 46%; any constant score: AUC 0.50. A variant whose flag F1 is near 0.70 with FAR near 100% has learned nothing.

## Discrimination (threshold-free) - ROC AUC of the call score

Does the score rank flaggable calls above harmless ones at all? 0.5 = no better than a coin (and than every constant policy). Same scores for every threshold-only variant.

| variant | flag AUC [95% CI] | alarm-vs-rest AUC [95% CI] | pos/neg (flag) |  |
|---|---|---|---|---|
| all | 0.58 [0.38, 0.76] | 0.69 [0.50, 0.87] | 26/22 | **ORACLE** |
| rules_only | 0.58 [0.39, 0.76] | 0.69 [0.51, 0.88] | 26/22 | **ORACLE** |
| all_t040 | 0.58 [0.38, 0.76] | 0.69 [0.50, 0.87] | 26/22 | **ORACLE**, re-fusion of all |

## Out-of-fold (CV) - primary

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 48 | 0.48 [0.20, 0.72] | 62% | 38% | 27% [0%, 60%] | 62% [33%, 87%] | 0.31 | 0% | 42% | 0.56 [0.38, 0.74] | **ORACLE** |
| rules_only | 48 | 0.52 [0.24, 0.73] | 60% | 46% | 36% [9%, 71%] | 54% [25%, 81%] | 0.53 | 0% | 50% | 0.55 [0.38, 0.73] | **ORACLE** |
| all_t040 | 48 | 0.48 [0.20, 0.72] | 62% | 38% | 27% [0%, 60%] | 62% [33%, 87%] | 0.31 | 0% | 42% | 0.56 [0.38, 0.74] | **ORACLE**, re-fusion of all |

## Out-of-fold at the FAR cap (CV@FAR20)

Threshold per fold = highest flag recall with FAR <= 20% on the other dev folds (lowest FAR if none meets the cap). Unlike max-F1 it cannot drift to flag-everything.

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 48 | 0.33 [0.00, 0.60] | 60% | 23% | 18% [0%, 45%] | 77% [50%, 100%] | 0.00 | 0% | 38% | 0.52 [0.36, 0.68] | **ORACLE** |
| rules_only | 48 | 0.35 [0.00, 0.62] | 75% | 23% | 9% [0%, 30%] | 77% [53%, 100%] | 0.31 | 0% | 50% | 0.57 [0.43, 0.71] | **ORACLE** |
| all_t040 | 48 | 0.33 [0.00, 0.60] | 60% | 23% | 18% [0%, 45%] | 77% [50%, 100%] | 0.00 | 0% | 38% | 0.52 [0.36, 0.68] | **ORACLE**, re-fusion of all |

## Fixed threshold

| variant | n | flag F1 [95% CI] | P | R | FAR [CI] | miss [CI] | alarm F1 | review recall | 3-class acc | flag bal. acc [CI] |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | 48 | 0.48 [0.20, 0.72] | 62% | 38% | 27% [0%, 60%] | 62% [33%, 87%] | 0.31 | 0% | 42% | 0.56 [0.38, 0.74] | **ORACLE** |
| rules_only | 48 | 0.44 [0.12, 0.70] | 80% | 31% | 9% [0%, 30%] | 69% [43%, 92%] | 0.43 | 0% | 54% | 0.61 [0.46, 0.75] | **ORACLE** |
| all_t040 | 48 | 0.48 [0.20, 0.72] | 62% | 38% | 27% [0%, 60%] | 62% [33%, 87%] | 0.31 | 0% | 42% | 0.56 [0.38, 0.74] | **ORACLE**, re-fusion of all |

## Threshold, cost, errors

| variant | threshold | suggested | CV fold thresholds | wall s/call | stage s/call (this run) | check compute s/call | LLM calls/call | errors | calls w/ failed checks | commit |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 0.55 | 0.55 | 0.55, 0.55, 0.60, 0.55 (FAR20: 1.00, 1.00, 1.00, 1.00) | 0.2 | asr 0.1, diarize 0.0, checks 0.0 | 0.1 | 10.0 | 0 | 0 | 8e00d1ef66 |
| rules_only | 0.55 | 0.25 | 0.25, 0.25, 0.25, 0.30 (FAR20: 0.70, 0.70, 0.70, 1.00) | 0.1 | asr 0.1, diarize 0.0, checks 0.0 | 0.0 | 0.0 | 0 | 0 | 8e00d1ef66 |
| all_t040 | 0.40 | 0.55 | 0.55, 0.55, 0.60, 0.55 (FAR20: 1.00, 1.00, 1.00, 1.00) | 0.0 | asr 0.1, diarize 0.0, checks 0.0 | 0.1 | 10.0 | 0 | 0 | 8e00d1ef66 |

## Breakdown (CV, flag F1 / FAR / miss)

| variant | Stufe1 | Stufe2 | Stufe3 | clean | noisy |
|---|---|---|---|---|---|
| all | 0.77 / 75% / 0% | 0.00 / 0% / 100% | 0.00 / - / 100% | 0.48 / 27% / 62% | 0.48 / 27% / 62% |
| rules_only | 0.77 / 75% / 0% | 0.29 / 14% / 80% | 0.00 / - / 100% | 0.52 / 36% / 54% | 0.52 / 36% / 54% |
| all_t040 | 0.77 / 75% / 0% | 0.00 / 0% / 100% | 0.00 / - / 100% | 0.48 / 27% / 62% | 0.48 / 27% / 62% |

## `rules_only` vs `all` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = rules_only - all

| metric | all | rules_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.58 | 0.58 | +0.004 | [-0.019, +0.043] | no detectable difference |
| alarm AUC | 0.69 | 0.69 | +0.004 | [-0.020, +0.044] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = rules_only - all

| metric | all | rules_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.48 | 0.52 | +0.045 | [+0.000, +0.162] | no detectable difference |
| alarm_f1 | 0.31 | 0.53 | +0.219 | [-0.050, +0.524] | no detectable difference |
| false_alarm_rate | 27% | 36% | +9pp | [+0pp, +30pp] | no detectable difference |
| miss_rate | 62% | 54% | -8pp | [-25pp, +0pp] | no detectable difference |
| accuracy | 42% | 50% | +8pp | [+0pp, +23pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.56 | 0.55 | -0.007 | [-0.058, +0.024] | no detectable difference |

McNemar exact (calls): flag correct only-all 2 vs only-rules_only 2, p=1.0; 3-class only-all 2 vs only-rules_only 6, p=0.2891.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = rules_only - all

| metric | all | rules_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.33 | 0.35 | +0.020 | [-0.353, +0.400] | no detectable difference |
| alarm_f1 | 0.00 | 0.31 | +0.308 | [+0.000, +0.615] | no detectable difference |
| false_alarm_rate | 18% | 9% | -9pp | [-42pp, +22pp] | no detectable difference |
| miss_rate | 77% | 77% | +0pp | [-31pp, +31pp] | no detectable difference |
| accuracy | 38% | 50% | +12pp | [-4pp, +33pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.52 | 0.57 | +0.045 | [-0.162, +0.273] | no detectable difference |

McNemar exact (calls): flag correct only-all 6 vs only-rules_only 8, p=0.7905; 3-class only-all 2 vs only-rules_only 8, p=0.1094.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = rules_only - all

| metric | all | rules_only | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.48 | 0.44 | -0.032 | [-0.214, +0.101] | no detectable difference |
| alarm_f1 | 0.31 | 0.43 | +0.121 | [+0.000, +0.393] | no detectable difference |
| false_alarm_rate | 27% | 9% | -18pp | [-45pp, +0pp] | no detectable difference |
| miss_rate | 62% | 69% | +8pp | [+0pp, +25pp] | no detectable difference |
| accuracy | 42% | 54% | +12pp | [+0pp, +29pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.56 | 0.61 | +0.052 | [-0.071, +0.200] | no detectable difference |

McNemar exact (calls): flag correct only-all 2 vs only-rules_only 4, p=0.6875; 3-class only-all 0 vs only-rules_only 6, p=0.0312.

Flips (cv, 12 calls):

| call | expected | all | rules_only | score a/b | flag | decisive passage / reason (b) | reason (a) |
|---|---|---|---|---|---|---|---|
| Stufe1_D06-K1 | no_alert | review | alarm | 0.75/0.35 | same | 01:57-01:58 splitting: Und im Mail het öpper gschribe, ich söll zum Gerätewechsel e Prüefig umgah. Das han ich nöd gmacht. D Absenderadresse gseht anders us als bi Ihren normale Nachricht, drum lüte i... | llm_judge: Verdächtige Formulierung «Passwort» in [T003]: Guet, mir trenned die zwei Sache. Für s Passwort säged Sie mir bitte nume, öb Sie sich dra erinnered. De Wert selber bli |
| Stufe1_D06-K2 | no_alert | review | alarm | 0.75/0.35 | same | 01:58-01:59 splitting: Und im Mail het öpper gschribe, ich söll zum Gerätewechsel e Prüefig umgah. Das han ich nöd gmacht. D Absenderadresse gseht anders us als bi Ihren normale Nachricht, drum lüte i... | llm_judge: Verdächtige Formulierung «Passwort» in [T003]: Guet, mir trenned die zwei Sache. Für s Passwort säged Sie mir bitte nume, öb Sie sich dra erinnered. De Wert selber bli |
| Stufe1_D08-K1 | no_alert | review | alarm | 0.77/0.35 | same | 00:54-00:54 disclosure: Richtig. Ich will au gar nüt über ihn persönlich wüsse. Ich ha s Protokoll vo de Wahl und s Formular zur Vollmacht vor mir. De Vorstand het das letzte Wuche iigreicht. - keywor... | llm_judge: Verdächtige Formulierung «nöd protokolliere» in [T015]: Bitte nöd protokolliere, dass die Apriluusgab im März passiert sei. Die Buechig selber und de richtige Aprilbericht sött |
| Stufe1_D08-K2 | no_alert | review | alarm | 0.77/0.35 | same | 00:54-00:55 disclosure: Richtig. Ich will au gar nüt über ihn persönlich wüsse. Ich ha s Protokoll vo de Wahl und s Formular zur Vollmacht vor mir. De Vorstand het das letzte Wuche iigreicht. - keywor... | llm_judge: Verdächtige Formulierung «nöd protokolliere» in [T015]: Bitte nöd protokolliere, dass die Apriluusgab im März passiert sei. Die Buechig selber und de richtige Aprilbericht sött |
| Stufe1_D09-K1 | alarm | review | alarm | 0.77/0.35 | same | 02:37-02:38 documentation: Denn bitte nöd protokolliere, dass ich die zwanzigtuusig zruggzahle muess. Nähmed s Darlehe nöd i d Notiz für d Kreditstell. Ich will, dass sie nume Eigenmittel gseht und di... | llm_judge: Verdächtige Formulierung «nöd protokolliere» in [T012]: Denn bitte nöd protokolliere, dass ich die zwanzigtuusig zruggzahle muess. Nähmed s Darlehe nöd i d Notiz für d Kreditst |
| Stufe1_D09-K2 | alarm | review | alarm | 0.77/0.35 | same | 02:39-02:40 documentation: Denn bitte nöd protokolliere, dass ich die zwanzigtuusig zruggzahle muess. Nähmed s Darlehe nöd i d Notiz für d Kreditstell. Ich will, dass sie nume Eigenmittel gseht und di... | llm_judge: Verdächtige Formulierung «nöd protokolliere» in [T012]: Denn bitte nöd protokolliere, dass ich die zwanzigtuusig zruggzahle muess. Nähmed s Darlehe nöd i d Notiz für d Kreditst |
| Stufe1_D10-K1 | alarm | review | alarm | 0.80/0.58 | same | 01:02-01:03 splitting: D Prüefig umgah würd ich nöd unterstütze. Mir erfassed de tatsächliche Gesamtvorgang und de Termin; de Ziitdruck isch kei Freigab, de Zusammenhang z verberge. - keywords: Stichw... | llm_judge: Verdächtige Formulierung «ufteile» in [T009]: Ich will d zwölftuusig ufteile, hüt sechstuusig und morn sechstuusig. So wett ich d Kontrolle umgah und verhindre, dass |
| Stufe1_D10-K2 | alarm | review | alarm | 0.80/0.58 | same | 01:03-01:04 splitting: D Prüefig umgah würd ich nöd unterstütze. Mir erfassed de tatsächliche Gesamtvorgang und de Termin; de Ziitdruck isch kei Freigab, de Zusammenhang z verberge. - keywords: Stichw... | llm_judge: Verdächtige Formulierung «ufteile» in [T009]: Ich will d zwölftuusig ufteile, hüt sechstuusig und morn sechstuusig. So wett ich d Kontrolle umgah und verhindre, dass |
| Stufe2_C11-K3 | no_alert | no_alert | alarm | 0.15/0.33 | broken | 03:00-03:00 trade: Genau. Ich will nume d Heimrechnig richtig behandle und nöd grad jede Uusgab us em alte Ordner übernäh. Für mini eigene Erstattig vom Taxifahrt-Beleg muess ich separat mit ihr rede.... | Kein Alarm: höchster Score 0.15 ('Insiderhandel') liegt unter 0.40 (Schwelle 0.55 minus Band 0.15). |
| Stufe2_C11-K4 | no_alert | no_alert | alarm | 0.15/0.33 | broken | 03:02-03:02 trade: Genau. Ich will nume d Heimrechnig richtig behandle und nöd grad jede Uusgab us em alte Ordner übernäh. Für mini eigene Erstattig vom Taxifahrt-Beleg muess ich separat mit ihr rede.... | Kein Alarm: höchster Score 0.15 ('Insiderhandel') liegt unter 0.40 (Schwelle 0.55 minus Band 0.15). |
| Stufe2_C12-K3 | alarm | no_alert | alarm | 0.15/0.33 | fixed | 02:58-02:59 trade: Genau. Ich will nume d Heimrechnig richtig behandle und nöd grad jede Uusgab us em alte Ordner übernäh. Für mini eigene Erstattig vom Taxifahrt-Beleg muess ich separat mit ihr rede.... | Kein Alarm: höchster Score 0.15 ('Insiderhandel') liegt unter 0.40 (Schwelle 0.55 minus Band 0.15). |
| Stufe2_C12-K4 | alarm | no_alert | alarm | 0.15/0.33 | fixed | 03:00-03:00 trade: Genau. Ich will nume d Heimrechnig richtig behandle und nöd grad jede Uusgab us em alte Ordner übernäh. Für mini eigene Erstattig vom Taxifahrt-Beleg muess ich separat mit ihr rede.... | Kein Alarm: höchster Score 0.15 ('Insiderhandel') liegt unter 0.40 (Schwelle 0.55 minus Band 0.15). |

## `all_t040` vs `all` (ORACLE involved)

**Threshold-free (ROC AUC of the call score)** - 48 calls; difference = all_t040 - all

| metric | all | all_t040 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag AUC | 0.58 | 0.58 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm AUC | 0.69 | 0.69 | +0.000 | [+0.000, +0.000] | no detectable difference |

**Out-of-fold (CV, max-F1 threshold)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_t040 - all

| metric | all | all_t040 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.48 | 0.48 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.31 | 0.31 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 27% | 27% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 62% | 62% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 42% | 42% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.56 | 0.56 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-all_t040 0, p=1.0; 3-class only-all 0 vs only-all_t040 0, p=1.0.

**Out-of-fold (CV@FAR20: max recall with FAR <= 20%)** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_t040 - all

| metric | all | all_t040 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.33 | 0.33 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.00 | 0.00 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 18% | 18% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 77% | 77% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 38% | 38% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.52 | 0.52 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-all_t040 0, p=1.0; 3-class only-all 0 vs only-all_t040 0, p=1.0.

**Fixed threshold** - 48 calls / 24 dialogues (18 resampling units: twins together); difference = all_t040 - all

| metric | all | all_t040 | diff | 95% CI |  |
|---|---|---|---|---|---|
| flag_f1 | 0.48 | 0.48 | +0.000 | [+0.000, +0.000] | no detectable difference |
| alarm_f1 | 0.31 | 0.31 | +0.000 | [+0.000, +0.000] | no detectable difference |
| false_alarm_rate | 27% | 27% | +0pp | [+0pp, +0pp] | no detectable difference |
| miss_rate | 62% | 62% | +0pp | [+0pp, +0pp] | no detectable difference |
| accuracy | 42% | 42% | +0pp | [+0pp, +0pp] | no detectable difference |
| review_recall | 0% | 0% | +0pp | [+0pp, +0pp] | no detectable difference |
| flag_balanced_accuracy | 0.56 | 0.56 | +0.000 | [+0.000, +0.000] | no detectable difference |

McNemar exact (calls): flag correct only-all 0 vs only-all_t040 0, p=1.0; 3-class only-all 0 vs only-all_t040 0, p=1.0.

No call changes its label (cv).

