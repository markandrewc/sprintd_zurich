# Evidence hit rate (dev)

True flags (predicted alarm|review, expected alarm|review). Hit = passage overlaps an aligned `Belege` turn in time. 95% bootstrap CIs over twin groups / dialogues. Small n: read the CIs.

| variant | true flags | no passage | hit@1 | hit@1 ±2 s | hit@3 | hit@all | chance@1 | median top-passage s | median miss s @1 | misses @1 w/ dist |
|---|---|---|---|---|---|---|---|---|---|---|
| kev_vs_facts/champion | 22 | 0 | 73% [45–91] (16/22) | 77% [50–100] (17/22) | 95% [86–100] (21/22) | 100% [100–100] (22/22) | 24% | 12.4 | 14.4 | 6 |
| kev_vs_facts/kev_facts | 14 | 8 | 43% [12–75] (6/14) | 43% [12–75] (6/14) | 43% [12–75] (6/14) | 43% [12–75] (6/14) | 17% | 1.5 | – | 0 |
| kev_vs_facts/kev_general | 15 | 0 | 87% [60–100] (13/15) | 87% [60–100] (13/15) | 100% [100–100] (15/15) | 100% [100–100] (15/15) | 55% | 48.0 | 110.6 | 2 |

hit@1 ±2 s = the top passage's snippet as played (2 s context each side) reaches an evidence turn. chance@1 = mean probability that a top passage of the same length, placed at a random point of the call, overlaps an evidence turn (what luck would give).

## kev_vs_facts/champion: per family

| family | true flags | no passage | hit@1 | hit@3 | chance@1 | median miss s @1 |
|---|---|---|---|---|---|---|
| access | 4 | 0 | 50% [0–100] (2/4) | 100% [100–100] (4/4) | 24% | 12.6 |
| disclosure | 4 | 0 | 100% [100–100] (4/4) | 100% [100–100] (4/4) | 20% | – |
| documentation | 4 | 0 | 50% [50–50] (2/4) | 100% [100–100] (4/4) | 16% | 10.7 |
| splitting | 2 | 0 | 100% [100–100] (2/2) | 100% [100–100] (2/2) | 44% | – |
| trade | 8 | 0 | 75% [25–100] (6/8) | 88% [62–100] (7/8) | 26% | 22.5 |

## kev_vs_facts/kev_facts: per family

| family | true flags | no passage | hit@1 | hit@3 | chance@1 | median miss s @1 |
|---|---|---|---|---|---|---|
| access | 2 | 2 | 0% [0–0] (0/2) | 0% [0–0] (0/2) | – | – |
| disclosure | 2 | 2 | 0% [0–0] (0/2) | 0% [0–0] (0/2) | – | – |
| documentation | 2 | 0 | 100% [100–100] (2/2) | 100% [100–100] (2/2) | 14% | – |
| trade | 8 | 4 | 50% [0–100] (4/8) | 50% [0–100] (4/8) | 18% | – |

## kev_vs_facts/kev_general: per family

| family | true flags | no passage | hit@1 | hit@3 | chance@1 | median miss s @1 |
|---|---|---|---|---|---|---|
| access | 2 | 0 | 100% [100–100] (2/2) | 100% [100–100] (2/2) | 62% | – |
| disclosure | 3 | 0 | 100% [100–100] (3/3) | 100% [100–100] (3/3) | 47% | – |
| documentation | 2 | 0 | 100% [100–100] (2/2) | 100% [100–100] (2/2) | 22% | – |
| splitting | 2 | 0 | 100% [100–100] (2/2) | 100% [100–100] (2/2) | 83% | – |
| trade | 6 | 0 | 67% [0–100] (4/6) | 100% [100–100] (6/6) | 58% | 110.6 |

## Alignment check (keyword anchors, first variant's transcripts)

39 keyword findings whose keyword id has exactly one annotated turn: aligned to that turn 39/39 (100%), within ±1 turn 39/39 (100%).

## «Möglicherweise verhört» vs wrong decisions

Threshold 0.6 (label-free dev p10 of segment confidences; recomputed on these transcripts: 0.597).

### kev_vs_facts/champion

7/59 shown passages flagged, 2/25 top passages.

top1, wrong = 3-class label wrong (n = 25 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 0 | 6 | 0.0 |
| right | 2 | 17 | 0.105 |

Fisher exact p = 1.0

top1, wrong = false flag (expected no_alert) (n = 25 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 0 | 3 | 0.0 |
| right | 2 | 20 | 0.091 |

Fisher exact p = 1.0

top3, wrong = 3-class label wrong (n = 25 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 1 | 5 | 0.167 |
| right | 5 | 14 | 0.263 |

Fisher exact p = 1.0

top3, wrong = false flag (expected no_alert) (n = 25 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 1 | 2 | 0.333 |
| right | 5 | 17 | 0.227 |

Fisher exact p = 1.0

### kev_vs_facts/kev_facts

0/18 shown passages flagged, 0/6 top passages.

top1, wrong = 3-class label wrong (n = 6 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 0 | 2 | 0.0 |
| right | 0 | 4 | 0.0 |

Fisher exact p = 1.0

top1, wrong = false flag (expected no_alert) (n = 6 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 0 | 0 | None |
| right | 0 | 6 | 0.0 |

Fisher exact p = 1.0

top3, wrong = 3-class label wrong (n = 6 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 0 | 2 | 0.0 |
| right | 0 | 4 | 0.0 |

Fisher exact p = 1.0

top3, wrong = false flag (expected no_alert) (n = 6 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 0 | 0 | None |
| right | 0 | 6 | 0.0 |

Fisher exact p = 1.0

### kev_vs_facts/kev_general

16/45 shown passages flagged, 9/17 top passages.

top1, wrong = 3-class label wrong (n = 17 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 5 | 1 | 0.833 |
| right | 4 | 7 | 0.364 |

Fisher exact p = 0.131

top1, wrong = false flag (expected no_alert) (n = 17 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 1 | 1 | 0.5 |
| right | 8 | 7 | 0.533 |

Fisher exact p = 1.0

top3, wrong = 3-class label wrong (n = 17 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 5 | 1 | 0.833 |
| right | 6 | 5 | 0.545 |

Fisher exact p = 0.333

top3, wrong = false flag (expected no_alert) (n = 17 flagged calls with passages):

|  | low-confidence passage | no low-confidence passage | share low |
|---|---|---|---|
| wrong | 1 | 1 | 0.5 |
| right | 10 | 5 | 0.667 |

Fisher exact p = 1.0
