# Ideas round 2: skeptical review of the `facts` system (2026-10-10)

Scope: the current best system is `facts` alone (fact questions + `config/policy_table.yaml`), run on Qwen2.5-7B,
default turbo ASR, dev split (48 calls / 24 dialogues). This note covers its 3 weakest spots, the threshold policy
for Sunday, product ideas, queue items R1-R8, and a devil's-advocate case.

**What I read.** Journal, findings RQ2/4/5, ideas_round1, queue, the experiment and ASR summaries, policy_table.yaml,
facts.py, fact_prompts.py, hybrid.py, criteria.yaml (review_when) and splits.yaml. I also read the per-call fact
probabilities in `runs/experiments/llm_models/qwen25_7b/results.jsonl` (dev calls only) and the ASR transcripts of
the dev calls D05-K2, C06-K4, C09-K3, C18-K3 and C20-K3. I did not open any `Skript_mit_Sollbewertung` file and
nothing from the holdout (D07, C03, C04, C15, C16, C19).

**New 0-GPU tool.** `/tmp/r2scripts/sim_rules.py` (outside the repo) re-runs any policy-table variant on the
**cached** fact probabilities, in milliseconds, without the LLM. Every "sim" number below comes from it. Caveat: the
decision is the max of the per-family rule labels at the fixed threshold. That matches `facts_only` at the
configured threshold (FAR 4/22, miss 7/26, review recall 50%), not the CV row. Section 2 explains why the two differ.

**Statistics.** Dev has 24 dialogues, and only 3 of them are review cases (C17, C18, C20). A one-sided sign test
needs a net of **5:0 dialogues** for p < 0.05. Every rule change below was found by looking at dev errors, so it is
**in-sample** until R4/R5 or the holdout confirms it.

---

## 0. Facts about the current system that change the plan

1. **Errors at the fixed threshold:** 14 of 48 calls in 10 dialogues.
   - Missed alarms (`no_alert`): D05-K2, C06-K4, **C09-K3, C09-K4** (both versions).
   - Alarms rated only `review`: C07-K3, C12-K4, C13-K3.
   - False flags: **C11-K3, C11-K4, C14-K3 and C14-K4. These are all 4 false alarms**, all on two Stufe2 harmless twins.
   - Review cases rated `no_alert`: C18-K3, C20-K3, C20-K4.
   - C09 is a clean-audio miss that RQ5 does not list. The customer reads "8-3-6-1-7-4" (S011), but the model answers
     `spoken = no` (p(no) 0.80 / 0.85). The `patterns` check did find the digit run (numbers score 0.2).
2. **No cross-family false alarms: 0 of 198 (call, other family) pairs.** By the rule of three, the upper bound is
   about 1.5% per pair. Every false alarm of `facts` is a within-family twin confusion. The free judge, by contrast,
   produced documentation false alarms across families.
3. **The 7B model hedges.** p(unknown) is the default answer: 0.8-1.0 for most context, authorization and
   exculpatory facts on most calls. For `current` (access) it is above 0.97 on almost every call. The model gives a
   confident "no" on act facts in only 14% of (call, family) pairs (p(no) >= 0.9 on every gate fact). A cascade
   that skips context facts after a confident "no" would save only 14% of prompts. Prefix caching is the real saving.
4. **Clean vs noisy:** 7 of 24 dialogues get a different 3-class decision on the two audio versions (D05, C06, C07,
   C12, C13, C14, C18). **In 4 of the 7, the clean version is the wrong one** (C07, C13, C18; C14 is wrong both
   times). The flips sit on facts with p close to 0.5: C07-K3 inside_info yes 0.44 / unknown 0.44, C13-K3 relevant
   yes 0.49, C18-K3 authorized no 0.73. **Most of what looks like "noisy-audio flips" is LLM instability at the
   decision boundary, not ASR.** Only D05-K2 and C06-K4 are noisy-only failures.
5. **The `facts` score is nearly discrete,** so its operating point is **flat from threshold 0.25 to 0.80** (FAR
   18%, miss 27%). The threshold slider barely matters. What decides is `decide_at`, the rules and the constant
   review score of 0.5.

---

## 1. The three weakest spots, with cheap fixes

### W1. Open cases (review): wrong rule logic plus a threshold artefact, more than "the model can't see it"

**Evidence**

| call | expected | decision | why |
|---|---|---|---|
| C17-K3/K4 | review | review (2/2) | The access table has an **explicit** fact `validity_open` ("does someone *say* it is unclear whether the value is valid?"), and it fires at p = 1.00. This is the only family where review works. |
| C18-K3 | review | no_alert | `third_party_request` = yes (0.99). `authorized` = **no** (0.73) and `not_authorized` = no (0.53). Rule `disclosure.review_2` requires both to be *unclear*. "Neither confirmed nor denied" is exactly the open case, but the rule reads it as cleared. |
| C18-K4 | review | review | Same call. Here both facts happen to land on unclear (0.62 / 0.68). This is a boundary coin flip. |
| C20-K3/K4 | review | no_alert | Every splitting fact is unclear (split_request unknown 0.76; avoid_control unknown 0.95), and p(yes) = 0 everywhere. Every splitting rule needs `split_request = yes`. In C20 the act itself is what stays open ("ich kann nicht sagen, ob sie nach der Rechnung gegangen ist"). No fact asks "does someone say that the link or purpose is unknown?" |
| CV row | | | Review recall 33% (CV) vs 50% (fixed) is an **artefact**. The max-F1 threshold landed on the plateau edge t = 0.20 in 3 of 4 folds. At t = 0.20, every facts review (score 0.5) becomes an **alarm** (C11, C13-K3, C14-K3, C18-K4, C12-K4 in the CV rows). |

The `p(unknown)` mass is not a usable review signal on its own. The max-family mean p(unknown) over act and context
facts has review-vs-rest AUC 0.84, but every value lies between 0.83 and 0.92. The top 12 calls contain all 6 review
calls together with 6 alarms or harmless calls. A rule "act not ruled out (p(no) < 0.35) -> review" gives review
recall 100% at **FAR 68%** (sim). That is useless.

**Fixes**

1. **Translate the criteria's `review_when` line by line into the table (0 GPU).** For disclosure, criteria.yaml
   already says "Die Berechtigung bleibt ungeklärt, auch wenn keine konkreten Daten herausgegeben wurden". As a
   rule: `third_party_request = yes and authorized != yes -> review`. This is not tuned to a call; it is the
   criteria text. Sim: C18-K3 becomes review, no new false flag. Miss 7 -> 6, review recall 50% -> 67%, FAR
   unchanged at 4/22.
2. **Add one explicit "open" fact per family, modelled on `validity_open` (about 1-2 GPU-min).** Each one asks
   "does someone in the call *say* that X is unknown or still to be clarified?", taken from `review_when`:
   - trade `source_open`
   - disclosure `authorization_open`
   - documentation `relevance_open`
   - splitting `purpose_open` (the amounts' link or the reason for the split)

   Gate each one with "act or request in [yes, unclear]".
   *Mechanism:* it asks about an observable utterance ("someone says it is unknown") instead of asking the model
   to resolve the open fact, which it can't. That is why access works and splitting doesn't.
   *Falsify:* review recall on the 6 dev review calls, and new flags on the 42 others.
   *Expected:* C20 becomes review on both versions, and at most 1 new falsely flagged dialogue. Kill it if 2 or more
   harmless dialogues get flagged.
   *n = 24 can only show this as a mechanism* (3 review dialogues). Count the statistics on R5 synthetic review cases.
3. **Make the rule label immune to the slider (0 GPU).** A `review` from a policy rule stays `review` at every
   threshold. It never becomes an alarm because t < 0.5, and never `no_alert` because t - band > 0.5. Either
   derive review_score from the threshold (t - band/2) or let the fusion keep the rule label for `facts`.
   *Falsify:* CV review recall must equal fixed review recall (33% -> 50%, already shown above). This is not a
   claim of improvement; it removes an evaluation artefact.

### W2. Twin discrimination in documentation and disclosure, and whether the fact wording generalises

**Evidence.** All 4 false alarms come from the C11 (disclosure) and C14 (documentation) harmless twins. Their alarm
twins C12/C13 land on review on one version (C12-K4, C13-K3). The deciding facts are near-coin-flips:
- C11: `authorized` unknown 0.97 / 0.98.
- C14-K4: `correction_or_private` unknown 0.68 while `relevant` = yes 0.77.
- C13-K3: `relevant` yes 0.49.

The 7B model cannot tell "old contact address" (C14) from "repayable obligation" (C13) when the content of the
"violetter Satz" is said far from the omit request.

On top of that, the wording was **written while looking at dev ASR transcripts**. The YAML comments cite dev calls
(C17 for `spoken`, C11/C12 for splitting the authorization fact). `validity_open` itself was added because
`current` came out unknown on C17.

**Fixes and tests**

1. **Paraphrase robustness (R3, about 3-5 GPU-min).** Re-ask every fact with 2 paraphrases written **blind**: from
   criteria.yaml only, by an agent that has not seen transcripts. Run them on all 48 dev calls.
   - Metrics: per-fact value agreement and mean |Δp(yes)| (about 960 fact answers per set, so these CIs are tight);
     the call-decision flip rate; flag AUC per paraphrase set.
   - Falsified (the wording is fragile) if more than 15% of calls flip or flag AUC drops by more than 0.10.
     n = 24 detects only an AUC drop of 0.12 or more; fact-level agreement is the sensitive number.
   - By-product: averaging p over the 3 wordings is a cheap ensemble (see W3).
2. **Blind policy table (R4, about 2-3 GPU-min).** A full table (facts and rules) written only from criteria.yaml
   and the case brief, with no transcripts, compared against the tuned table on dev.
   - This is the minimal refutation of "overfit". If blind AUC is within 0.05 and FAR at most 27%, the gain comes
     from the *method* (atomic questions plus logprobs plus rules), not from the wording.
   - It also gives an honest **hidden-set expectation** for the pitch.
3. **Pre-registered synthetic twins (R5).** Freeze the table hash *before* the synthetic scripts are scored, and
   write it into the journal. Measure pair-AUC (is the alarm twin scored above the harmless twin?) for facts vs
   judge, and review recall on the synthetic review cases.
   - Seeds must not include holdout scenarios (C03/C04, C15/C16, D07, C19).
   - The synthetic numbers are a stress test and never a jury number. If the builder uses a Qwen model, the
     "generator = judge" circularity favours both checks equally, so compare facts vs judge, not absolute values.
4. **Anchored context questions (part of R6).** The act fact already returns evidence segment ids (`evidence: true`).
   Re-ask the context and exculpatory facts with "the request in S0xx" spelled out in the question, so the model
   links the far-away "violetter Satz" content to the request. This targets C13/C14 and C06-K4 (a 54-segment call
   where the trade wish sits at S004-S008 and S047).
   - Expected: the twin-pair ranking improves on the C11/C12 and C13/C14 pairs (4 within-pair comparisons).
   - Only a sign is measurable on dev.

### W3. Act and context facts that flip at the boundary (noise, long calls, odd phrasing)

**Evidence.** All four failures below are single facts that the rule treats as decisive:
- **D05-K2** (noisy): `expired_or_sample` = yes 0.68. The ASR text mentions "die alte Anfrage von vor fünf Minuten",
  and the model attaches "expired" to the code that was read out, which kills `access.alarm_1`. Clean D05-K1 has
  expired = no 0.79.
- **C06-K4** (noisy, long): `inside_info` = no 0.52, although S007 says "persönlich gezeigt ... bleibt bis zur
  Präsentation am Freitag". The clean version has yes 0.85. The later "Bericht" turns probably read as "public".
- **C09-K3/K4** (clean and noisy): `spoken` = no, even though 6 digits are read out after an odd lead-in
  ("Wollen Sie sich die Stellen aus dem Feld vorbauen, 8-3-6-1-7-4?").
- More generally, 7 of 24 dialogues are inconsistent between clean and noisy, mostly at p close to 0.5 (section 0.4).

**Fixes**

1. **Conflict -> review, never conflict -> no_alert (0 GPU).** When the act and context facts of an alarm rule are
   yes, but the exculpatory fact is yes with p < 0.9, the call goes to review. A real exculpation is said explicitly
   and gets p >= 0.9 (C05-K4 public = 1.00; C10 expired = 0.93 / 0.94).
   - Sim: D05-K2 alarm -> review (now flagged), no new false flag.
   - Policy argument: two decisive facts that contradict each other are, by definition, a case for a human.
   - Needs the rule language to read probabilities (a `p(fact) < x` atom) or a fusion knob.
2. **Deterministic anchor disagreement -> review (0 GPU), or re-ask on the anchor segment (about 1 GPU-min).**
   `patterns` found a digit run (score >= 0.2) but `spoken != yes`: then either go to review, or better, re-ask
   `spoken` restricted to that segment.
   - Sim (review variant): both C09 calls become review. No new false flag; C01/C02/C10 are unaffected because
     either their `spoken` is yes or their digit run scores below 0.2.
   - The bar of >= 0.2 matters: with > 0, C05 is falsely flagged and C20 is flagged under the wrong family.
     The bar is tuned on dev; say so.
3. **Perturbation ensemble (R6, about 10 GPU-min).** Average the fact p over K cheap perturbations of the same call:
   (a) the 3 wordings from R3, (b) 2 ASR hypotheses (turbo with nocond/noprompt, which is +10 pp noisy keyword
   recall, and large-v3 MIT, whose dev transcripts are already cached from asr_models). This is valid in production,
   because only one recording is needed.
   - Metric: **clean/noisy pair consistency**. It needs no labels and has 24 pairs. Baseline: 7/24 inconsistent at
     3-class level, 3/24 at flag level.
   - Target: at most 3/24 at 3-class level. Going from 7 to 3 is a 4:0 shift, which is borderline (sign test
     p = 0.06). Report it as a direction.
   - Secondary: miss rate on noisy calls.
   - Kill it if the miss rate on clean calls rises.

**Combined sim of the three 0-GPU fixes** (W1-1, W3-1, W3-2), in-sample:

| | base | combined |
|---|---|---|
| miss | 7/26 | 3/26 |
| FAR | 4/22 | 4/22 (unchanged) |
| 3-class accuracy | 71% | 73% |
| review recall | 50% | 67% |

The net gain is 3 dialogues (C09, D05, C18) against 0 losses: sign test p = 0.125, not significant. **And it was
fitted on these very errors.** This shows how cheap in-sample gains are (see section 5). Treat it as a hypothesis
for R4/R5 and the 14B run (re-simulating on any model's cached facts is free).

---

## 2. Threshold policy for Sunday

1. **The threshold is not the lever for `facts`.** The flag decision is flat over t in [0.25, 0.80]. The max-F1 CV
   chose the plateau edge (0.20) because of a one-call difference, which is a cliff-edge argmax. On Sunday, set
   **t = 0.55, band 0.15** (the configured values, in the middle of the plateau) and **pin the rule labels** (W1-3).
   A review from a rule must never become an alarm or no_alert through the slider.
2. **The real knob is `decide_at`** (the p at which a fact counts as yes or no).
   - Sim: 0.5 and 0.6 are equivalent: 0.6 moves C06-K4 from no_alert to review, with no new false flag.
   - 0.7 loses D09-K1.
   - Choose **0.55** as the plateau centre; at n = 24 its edge over 0.5 is not detectable.
   - Choose it by **worst-fold** 3-class accuracy over the 4 dev folds, not by pooled max-F1.
   - **Re-check it for the model that wins the LLM sweep:** fact calibration changes with the model, and 14B
     probably hedges less.
3. **No per-family thresholds.** There are 0 cross-family false flags in 198 pairs, so per-family false-positive
   control has nothing to fix. Each family has only 2-5 positive dialogues, so a per-family threshold would be fitted
   noise. Keep one global setting.
4. **Hidden set (about +30% calls, same generator).** Expect the same families and levels. The risk is new
   *wordings* of the same scenarios (W2), not new families. Concrete steps:
   - Freeze `decide_at`, the rules and the table hash before the single holdout run, and log the hash with the run.
   - In the pitch, report the **blind-table number (R4)** next to the tuned one as the honest range for the hidden set.
   - The holdout contains two complete twin groups that are **unseen in dev** (C03/C04, C15/C16). They are the only
     real generalisation test of the twin wording. They are 4 of the 6 holdout dialogues, so a single run can only
     detect gross failure (3 or more wrong out of 8 calls).
5. **Safety asymmetry.** In compliance a miss costs more than a review. When unsure, prefer the rule set that turns
   conflicts and anchor disagreements into *review* (W3-1, W3-2), not into no_alert. State the FAR cost of that
   openly (here: +0 calls on dev).

---

## 3. Product and demo ideas that also strengthen the jury story

1. **"Gegenprobe" / why not an alarm (0 LLM).** From the rule table, compute the smallest set of fact changes that
   would change the label: "Wäre *Information bereits öffentlich* = nein, wäre das ein Alarm (Regel trade.alarm_1)".
   It is pure logic over `eval_hard`, and every harmless twin (D03, C05, C10) gets a one-line counterfactual next to
   the exculpatory fact's evidence segment. Traceability (25%) and creativity (20%).
2. **Live policy editing with an impact preview.** The officer edits a rule in the UI (today only criteria.yaml is
   editable, in `ui/views/keywords.py`), and all cached calls are re-decided instantly from the stored fact
   probabilities, as sim_rules.py does. The UI shows a diff: "3 Anrufe ändern sich: C18-K3 Kein Alarm -> Prüfen ...".
   - Adding a *new fact* costs one LLM pass (about 0.5 s per call with prefix caching), and the UI shows that estimate.
   - Every result.json stores the table hash, so the audit trail shows which policy version decided each call.
   - Pitch moment: paste the disclosure `review_when` sentence as a rule live and watch C18 move to "Prüfen".
3. **The open question as the officer's task.** A review card states the open fact as a question ("Offen: Ist die
   Vollmacht bestätigt? Modell: unklar 0.62"), and the officer answers it in the UI. The answer is a **fact-level
   label**, which is far more data-efficient feedback than a call label. It can feed later decide_at calibration and
   wording fixes (`feedback.py` exists). This is the impact story: the system learns the bank's facts, not opaque
   scores.
4. **Cost per call, as a number on a slide.** Measured at 7B: `facts` alone needs 11.8 LLM calls and 12.2 s of check
   compute per call, against 28 calls and 74 s for the v1 four-check stack. ASR runs at 0.9 GPU-s per audio minute.
   Calls average about 4.7 minutes of audio. A rough, to-be-measured (P1) estimate is 3-4 GPU-s per audio minute,
   which means thousands of calls per day on one consumer GPU. Note the honest negative too: the act-gated cascade
   saves only 14% at 7B because the model rarely says a confident "no".
5. **Fact timeline in the call view.** Each fact with p(yes) > 0.5 is a marker on the audio timeline (evidence
   segments), coloured by role: act red, context orange, exculpatory green. The officer sees "act at 01:17,
   exculpation at 02:05" and plays both. Usability (25%).

---

## 4. Queue items (appended to research/queue.yaml, group ideas2)

| id | prio | GPU | title |
|---|---|---|---|
| R1 | 1 | 0 | Criteria-derived rule fixes (disclosure `review_when` as a rule, conflict -> review, digit-run anchor -> review) plus pinned rule labels; re-simulate on every model's cached facts |
| R2 | 1 | ~2 min | Explicit `*_open` facts per family from `review_when` (modelled on `validity_open`) |
| R3 | 2 | ~5 min | Paraphrase robustness: 2 blind paraphrase sets, fact agreement and decision flips |
| R4 | 1 | ~3 min | Blind policy table (written without transcripts) vs tuned table: the overfit test |
| R5 | 2 | ~5 min | Pre-registered synthetic-twin evaluation (frozen table hash): facts vs judge pair-AUC, review recall |
| R6 | 3 | ~10 min | Perturbation ensemble (wordings x ASR views) plus anchored context questions; clean/noisy pair consistency |
| R7 | 1 | 0 | Threshold/decide_at policy: plateau centre, worst-fold, review-score invariant, per LLM |
| R8 | 3 | 0 | Product: Gegenprobe counterfactuals plus a policy editor with impact preview and table-hash audit |

---

## 5. Devil's advocate: `facts` is overfit

**The strongest argument.** `facts` is a hand-built decision tree whose *features* (about 20 questions) and
*splits* (about 15 rules) were chosen by people looking at the same 24 dev dialogues it is scored on.
- Its degrees of freedom are about the same as the number of independent units (18 resampling units).
- The YAML comments record specific fixes for specific dev calls (C17, C11/C12).
- The free judge's prompt was written blind, so "facts 0.84 vs judge 0.68" compares a tuned model with an untuned one.
- I showed how easy this is: in about ten minutes, without any new information, three rule edits cut the misses
  from 7 to 3 on dev (section 1).
- The near-discrete score also makes the AUC lumpy: a few calls move it a lot.
- Finally, generator-specific phrasing ("Kreditstelle", "Finanzierungsstelle", "nur die letzten vier Stellen")
  sits inside the questions.

**Counter-evidence that already exists.**
- 0 of 198 cross-family false flags. Overfitting to twins would not explain why the other families stay silent.
- The judge's false alarms are a *structural* problem (documentation over-triggering), not a wording problem.
- The McNemar 3-class result (21 vs 4 calls) is far larger than what a few wording tweaks plausibly buy.

**Minimal evidence that would refute the overfit claim** (any 2 of these 3):
1. **R4 blind table:** dev flag AUC at least 0.79 (within 0.05) and FAR at most 27%. The method carries the gain.
2. **R3 paraphrases:** at least 90% fact-value agreement and at most 10% call-decision flips. The wording is not
   a knife edge.
3. **R5 pre-registered synthetic twins:** facts beats judge on pair-AUC with a CI that excludes 0.

The holdout (unseen twins C03/C04, C15/C16) is the final but low-power check. If R4 fails (blind AUC <= 0.74), the
honest Sunday claim is "atomic facts, *tuned by compliance on example calls*". That is still a legitimate product
story, because the officer-editable table is the feature, but report the blind number as the hidden-set expectation.

---

## Top 5 actions by value per GPU-minute

1. **R1 + R7 (0 GPU):** pin rule labels, set t = 0.55 with decide_at chosen by worst-fold, add the criteria-derived
   disclosure review rule plus conflict -> review plus the anchor rule. Re-simulate on the 14B cache when it lands.
2. **R4 (about 3 GPU-min):** the blind table decides whether `facts` is the Sunday core and gives the hidden-set number.
3. **R2 (about 2 GPU-min):** `*_open` facts, the only cheap path to the splitting and disclosure review cases (C20).
4. **R3 (about 5 GPU-min):** the paraphrase stability test; its averaged p is also the first piece of R6.
5. **R5 (about 5 GPU-min, needs the synthetic builder):** a pre-registered twin stress test of facts vs judge.
