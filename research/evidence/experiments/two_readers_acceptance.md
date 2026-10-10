# Two readers: pre-registered evaluation (dev)

Pre-registration: research/findings/two_readers_prereg.md. Metrics on out-of-fold CV rows (threshold per fold chosen on the other folds); AUC on the fixed-threshold call scores. 95% CIs: 2000 bootstrap replicates over twin groups. n = 48 calls / 24 dialogues; 6 expected-review calls (1 call = 17 pp of review recall).

| wording | system | flag AUC [CI] | CV flag F1 [CI] | CV FAR [CI] | CV miss [CI] | review recall | 3-class acc [CI] | reviews | CV@FAR20 FAR / recall |
|---|---|---|---|---|---|---|---|---|---|
| tuned | Qwen alone | 0.87 [0.72, 0.99] | 0.86 [0.73, 0.96] | 14% [0%, 35%] | 15% [0%, 36%] | 67% (4/6) | 79% [63%, 95%] | 10 | 14% / 81% |
| tuned | Kev alone | 0.86 [0.67, 0.98] | 0.82 [0.62, 0.95] | 0% [0%, 0%] | 31% [9%, 56%] | 0% (0/6) | 69% [48%, 86%] | 6 | 0% / 69% |
| tuned | R1 labels | 0.93 [0.82, 1.00] | 0.88 [0.78, 0.98] | 14% [0%, 35%] | 12% [0%, 29%] | 50% (3/6) | 65% [45%, 83%] | 16 | 14% / 85% |
| tuned | R2 facts | 0.84 [0.65, 0.98] | 0.82 [0.65, 0.94] | 14% [0%, 35%] | 23% [0%, 47%] | 0% (0/6) | 69% [50%, 87%] | 5 | 14% / 69% |
| para | Qwen alone | 0.72 [0.52, 0.88] | 0.68 [0.48, 0.84] | 23% [0%, 50%] | 38% [14%, 64%] | 0% (0/6) | 67% [50%, 83%] | 1 | 23% / 62% |
| para | Kev alone | 0.90 [0.73, 1.00] | 0.87 [0.71, 0.98] | 0% [0%, 0%] | 23% [5%, 45%] | 0% (0/6) | 71% [52%, 86%] | 7 | 0% / 73% |
| para | R1 labels | 0.86 [0.68, 0.97] | 0.78 [0.63, 0.91] | 23% [0%, 50%] | 23% [5%, 45%] | 17% (1/6) | 56% [38%, 74%] | 16 | 23% / 73% |
| para | R2 facts | 0.80 [0.60, 0.94] | 0.70 [0.50, 0.85] | 18% [0%, 44%] | 38% [14%, 64%] | 0% (0/6) | 67% [50%, 82%] | 2 | 18% / 62% |
| para2 | Qwen alone | 0.74 [0.54, 0.90] | 0.73 [0.55, 0.88] | 23% [0%, 50%] | 31% [8%, 58%] | 0% (0/6) | 71% [56%, 85%] | 1 | 23% / 69% |
| para2 | Kev alone | 0.90 [0.71, 1.00] | 0.89 [0.73, 1.00] | 0% [0%, 0%] | 19% [0%, 42%] | 0% (0/6) | 77% [57%, 92%] | 4 | 0% / 81% |
| para2 | R1 labels | 0.85 [0.68, 0.99] | 0.83 [0.69, 0.95] | 23% [0%, 50%] | 15% [0%, 38%] | 33% (2/6) | 67% [50%, 84%] | 14 | 23% / 85% |
| para2 | R2 facts | 0.79 [0.59, 0.93] | 0.73 [0.55, 0.88] | 23% [0%, 50%] | 31% [8%, 58%] | 0% (0/6) | 71% [56%, 85%] | 1 | 23% / 69% |
| blind | Qwen alone | 0.73 [0.53, 0.90] | 0.67 [0.43, 0.86] | 18% [0%, 44%] | 42% [17%, 67%] | 0% (0/6) | 58% [39%, 77%] | 3 | 18% / 58% |
| blind | Kev alone | 0.85 [0.68, 1.00] | 0.83 [0.65, 0.96] | 5% [0%, 14%] | 27% [6%, 50%] | 33% (2/6) | 65% [44%, 83%] | 12 | 5% / 73% |
| blind | R1 labels | 0.84 [0.71, 0.96] | 0.83 [0.69, 0.95] | 23% [0%, 50%] | 15% [0%, 38%] | 67% (4/6) | 56% [38%, 75%] | 21 | 23% / 85% |
| blind | R2 facts | 0.75 [0.59, 0.90] | 0.71 [0.53, 0.86] | 23% [0%, 50%] | 35% [11%, 62%] | 0% (0/6) | 58% [41%, 74%] | 6 | 23% / 65% |

## Paired vs Qwen alone on the same wording (B - A on CV rows; bold = CI excludes 0)

| wording | system | d AUC [CI] | d FAR [CI] | d miss [CI] | d review recall | d 3-class acc [CI] | McNemar flag (A only / B only, p) | McNemar label | flips |
|---|---|---|---|---|---|---|---|---|---|
| tuned | Kev alone | -0.01 [-0.21, +0.14] | -14pp [-35pp, +0pp] | +15pp [-6pp, +41pp] | -67pp | -10pp [-36pp, +9pp] | 5 / 4, p=1.0 | 10 / 5, p=0.3018 | 15 |
| tuned | R1 labels | +0.06 [-0.00, +0.16] | +0pp [+0pp, +0pp] | -4pp [-12pp, +0pp] | -17pp | **-15pp [-32pp, -2pp]** | 0 / 1, p=1.0 | 7 / 0, p=0.0156 | 8 |
| tuned | R2 facts | -0.02 [-0.20, +0.12] | +0pp [+0pp, +0pp] | +8pp [+0pp, +25pp] | -67pp | -10pp [-28pp, +2pp] | 2 / 0, p=0.5 | 6 / 1, p=0.125 | 9 |
| para | Kev alone | **+0.18 [+0.06, +0.31]** | -23pp [-50pp, +0pp] | **-15pp [-29pp, -4pp]** | +0pp | +4pp [-14pp, +19pp] | 0 / 9, p=0.0039 | 6 / 8, p=0.7905 | 16 |
| para | R1 labels | **+0.14 [+0.06, +0.22]** | +0pp [+0pp, +0pp] | **-15pp [-29pp, -4pp]** | +17pp | -10pp [-25pp, +2pp] | 0 / 4, p=0.125 | 6 / 1, p=0.125 | 15 |
| para | R2 facts | **+0.08 [+0.01, +0.17]** | -5pp [-15pp, +0pp] | +0pp [+0pp, +0pp] | +0pp | +0pp [-6pp, +7pp] | 0 / 1, p=1.0 | 1 / 1, p=1.0 | 2 |
| para2 | Kev alone | **+0.16 [+0.02, +0.33]** | -23pp [-50pp, +0pp] | -12pp [-36pp, +8pp] | +0pp | +6pp [-10pp, +19pp] | 1 / 9, p=0.0215 | 4 / 7, p=0.5488 | 13 |
| para2 | R1 labels | **+0.12 [+0.01, +0.25]** | +0pp [+0pp, +0pp] | -15pp [-38pp, +0pp] | +33pp | -4pp [-17pp, +9pp] | 0 / 4, p=0.125 | 4 / 2, p=0.6875 | 13 |
| para2 | R2 facts | +0.05 [-0.01, +0.13] | +0pp [+0pp, +0pp] | +0pp [+0pp, +0pp] | +0pp | +0pp [+0pp, +0pp] | 0 / 0, p=1.0 | 0 / 0, p=1.0 | 0 |
| blind | Kev alone | +0.13 [-0.08, +0.35] | -14pp [-43pp, +11pp] | -15pp [-46pp, +15pp] | +33pp | +6pp [-16pp, +30pp] | 4 / 11, p=0.1185 | 5 / 8, p=0.5811 | 18 |
| blind | R1 labels | **+0.12 [+0.03, +0.25]** | +5pp [+0pp, +14pp] | **-27pp [-53pp, -6pp]** | +67pp | -2pp [-17pp, +16pp] | 1 / 7, p=0.0703 | 5 / 4, p=1.0 | 18 |
| blind | R2 facts | +0.03 [-0.14, +0.18] | +5pp [+0pp, +14pp] | -8pp [-31pp, +17pp] | +0pp | +0pp [-14pp, +12pp] | 3 / 4, p=1.0 | 4 / 4, p=1.0 | 12 |

## Verdict per pre-registered criterion

### R1 labels: FAIL
- A1 pass: CV FAR 14% vs champion 14% (limit 19%)
- A2 FAIL: CV review recall 50% (3/6) vs champion 67% (4/6)
- A3 FAIL: CV 3-class acc 65% vs champion 79%: diff -15pp [-32pp, -2pp]
- A4 FAIL: para: AUC 0.86 vs Qwen 0.72 (need >= 0.82) ok, CV acc 56% vs Qwen 67% (need >= 72%) NO; para2: AUC 0.85 vs Qwen 0.74 (need >= 0.84) ok, CV acc 67% vs Qwen 71% (need >= 76%) NO; blind: AUC 0.84 vs Qwen 0.73 (need >= 0.83) ok, CV acc 56% vs Qwen 58% (need >= 63%) NO

### R2 facts: FAIL
- A1 pass: CV FAR 14% vs champion 14% (limit 19%)
- A2 FAIL: CV review recall 0% (0/6) vs champion 67% (4/6)
- A3 pass: CV 3-class acc 69% vs champion 79%: diff -10pp [-28pp, +2pp]
- A4 FAIL: para: AUC 0.80 vs Qwen 0.72 (need >= 0.82) NO, CV acc 67% vs Qwen 67% (need >= 72%) NO; para2: AUC 0.79 vs Qwen 0.74 (need >= 0.84) NO, CV acc 71% vs Qwen 71% (need >= 76%) NO; blind: AUC 0.75 vs Qwen 0.73 (need >= 0.83) NO, CV acc 58% vs Qwen 58% (need >= 63%) NO

Recommendation by the pre-registered tie-break: none passes - the champion stays.

## Flips vs Qwen alone (= champion), tuned table: R1 labels

| call | expected | Qwen | rule | flag | label | rule's first reason |
|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | same | broken | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Re |
| Stufe1_D05-K2 | alarm | alarm | review | same | broken | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe1_D09-K1 | alarm | alarm | review | same | broken | facts: Fakt: Verborgene Tatsache ist relevant = ja (0.97) - Die Kunde möchte die Existenz des Darlehens ihrer Tante verschleiern, um eine vo |
| Stufe1_D09-K2 | alarm | alarm | review | same | broken | facts: Fakt: Verlangt, etwas nicht zu protokollieren = ja (0.95) - Der Kunde möchte, dass seine Tante nicht aus den Sachen rausgelassen wird |
| Stufe1_D10-K1 | alarm | alarm | review | same | broken | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Zahlung aufteilen, um die Freigabestellung zu  |
| Stufe1_D10-K2 | alarm | alarm | review | same | broken | facts: Fakt: Zweck ist, Kontrolle oder Freigabe zu umgehen = ja (1.00) - Der Kunde möchte die Kontrolle umgehen und verhindern, dass die Fre |
| Stufe2_C09-K4 | alarm | no_alert | review | fixed | same | Zwei Leser: Qwen Kein Alarm, Kev Alarm -> uneinig, bitte prüfen. |
| Stufe3_C17-K4 | review | review | alarm | same | broken | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten z |

## Flips vs Qwen alone (= champion), tuned table: R2 facts

| call | expected | Qwen | rule | flag | label | rule's first reason |
|---|---|---|---|---|---|---|
| Stufe1_D05-K1 | alarm | alarm | review | same | broken | facts: Fakt: Code/Wert am Telefon vorgelesen = ja (1.00) - Der Kunde las die Ziffern der TAN-Card vor, obwohl die Gültigkeit unklar war. (Re |
| Stufe1_D05-K2 | alarm | alarm | review | same | broken | facts: Fakt: Code von der Beratung erfragt = ja (0.56) - Der Kunde gibt den TAN-Code laut aus. (Regel: access.alarm_1) |
| Stufe2_C11-K3 | no_alert | review | alarm | same | same | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an  |
| Stufe2_C11-K4 | no_alert | review | alarm | same | same | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Der Berater gibt die aktuelle Kontostandsumme von 6400 Franken an  |
| Stufe2_C12-K3 | alarm | review | alarm | same | fixed | facts: Fakt: Konkrete Daten einer Drittperson herausgegeben = ja (1.00) - Die Mitarbeiterin gibt die aktuelle Kontostandsumme von 6400 Frank |
| Stufe3_C17-K3 | review | review | alarm | same | broken | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten d |
| Stufe3_C17-K4 | review | review | alarm | same | broken | facts: Fakt: Im Gespräch offen, ob der Wert gültig ist = ja (1.00) - Der Kunde sagt, dass er nicht sicher ist, ob der Wert oben oder unten z |
| Stufe3_C18-K3 | review | review | no_alert | broken | broken | Kein Alarm: höchster Score 0.00 ('Zuständigkeit/Kontrolle umgehen') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |
| Stufe3_C18-K4 | review | review | no_alert | broken | broken | Kein Alarm: höchster Score 0.00 ('Relevante Angabe verschweigen') liegt unter 0.50 (Schwelle 0.65 minus Band 0.15). |

## Sanity: single readers re-fused from the joined source vs the stored runs

- tuned Qwen alone vs kev_vs_facts/champion: fixed: 0/48 calls differ; cv: 0/48 calls differ
- tuned Kev alone vs kev_vs_facts/kev_facts: fixed: 0/48 calls differ; cv: 0/48 calls differ
- para Qwen alone vs kev_vs_facts/qwen_facts_para: fixed: 0/48 calls differ; cv: 0/48 calls differ
- para Kev alone vs kev_vs_facts/kev_facts_para: fixed: 0/48 calls differ; cv: 0/48 calls differ
- para2 Qwen alone vs kev_vs_facts/qwen_facts_para2: fixed: 0/48 calls differ; cv: 0/48 calls differ
- para2 Kev alone vs kev_vs_facts/kev_facts_para2: fixed: 0/48 calls differ; cv: 0/48 calls differ
- blind Qwen alone vs kev_vs_facts/qwen_facts_blind: fixed: 0/48 calls differ; cv: 0/48 calls differ
- blind Kev alone vs kev_vs_facts/kev_facts_blind: fixed: 0/48 calls differ; cv: 0/48 calls differ
