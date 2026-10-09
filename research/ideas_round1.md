# Ideas round 1: fresh hypotheses from an outside research lead (2026-10-10)

Scope: 15 testable hypotheses that are not in `research/queue.yaml` (or are sharper versions of items
there), a top 5 ranked by expected value per GPU-hour for the ~5 GPU-hours left tonight, and 3 arguments
against the current architecture. All of them are added to the queue as `group: ideas` (ids N1-N15).

**What I read.** The brief, CASE, CLAUDE.md, v2_plan, IDEAS, QUESTIONS, queue, criteria.yaml,
keywords.json, prompts.py, llm_judge.py, geval.py, keywords.py (header and scoring), patterns.py (header)
and fusion/weighted.py. Reference scripts: Stufe1_D03, Stufe2_C01, Stufe2_C02, Stufe3_C17. **Disclosure:**
`config/splits.yaml` appeared while I was working, and **Stufe2_C02 is in the holdout**. I read its
script, not its expected label (no `Skript_mit_Sollbewertung/` file was opened). The C01/C02 contrast
shaped N4 and N8. A holdout number for a config that contains N4 or N8 carries that caveat.

**Two findings from reading the code and data (no GPU), both checked numerically:**

1. **Twin leakage across folds (see N1).** Script similarity (difflib ratio) shows that the Stufe2
   dialogues form 8 twin pairs that are 90-97% identical: C01/C02, C03/C04, C05/C06, C07/C08, C09/C10,
   C11/C12, C13/C14, C15/C16. Stufe1 and Stufe3 have no twins (best match ≤ 0.18). **All three Stufe2
   holdout dialogues (C02, C04, C06) have their twin in dev** (C01 dev3, C03 dev1, C05 dev0). Three more
   pairs are split across dev folds: C07/C08 (dev0/dev1), C11/C12 (dev2/dev1) and C15/C16 (dev0/dev1).
   So anything tuned on dev (threshold, prompt wording, criteria text, few-shot pool, learned fusion)
   has already seen about 95% of the text of half the holdout. A twin few-shot pool (queue item C6/A8)
   would put a near-copy of the call under evaluation into the prompt.
2. **The fusion penalises exactly the Stufe2 alarms (see N14).** When the keyword check finds nothing,
   it does not stay silent: it reports score 0.0 at confidence 0.25 (weight 0.35). That zero enters the
   disagreement term of `WeightedFusion._fuse_family`. I simulated it with the real code on a call with
   no keywords, where llm_judge says 0.95 (conf 0.9) and geval says 0.9:

   | geval confidence | with keyword "0" | without |
   |---|---|---|
   | 0.4 | score 0.88, unc 0.43 -> **review** | 0.93, unc 0.20 -> alarm |
   | 0.6 | 0.88, unc 0.38 -> **review** | 0.93, unc 0.15 -> alarm |
   | 0.8 | 0.88, unc 0.32 -> alarm | 0.93, unc 0.10 -> alarm |

   G-Eval's entropy-based confidence is often 0.4-0.6 (e.g. {3: .1, 4: .3, 5: .6} gives 0.44). So a
   clear alarm with no keywords is escalated to review only because no keyword fired. Stufe2 is mostly
   calls without keywords.

Statistics reminder for every item. Dev has 24 dialogues (48 calls). Clean and noisy are not
independent, so count dialogues. A paired sign test needs about **≥5:0 or ≥7:1 net dialogue flips**
for p < 0.05. Gains of 1-2 dialogues are noise. Stufe2 has 8 twin pairs (5 fully in dev). Review has 4
dialogues (3 in dev), which supports qualitative claims only. Costs assume Qwen2.5-7B-AWQ on vLLM 0.10.1
at 0.66-0.70 utilisation: about 27-35k tokens of KV cache, prompts of about 2k tokens (transcript about
1.1-1.5k tokens plus criteria), prefix caching on. **These costs are estimates; refine them from the
journal.** Implementation rule: build new behaviour as new plugin classes (`module:Class`) or new
default-off knobs, so the cache keys of the cached llm_judge, geval and keyword results stay unchanged.

---

## The hypotheses

### N1: Twin-aware evaluation; current dev-CV and holdout numbers are optimistic for tuned components
- **Idea.** Treat a twin pair like clean/noisy: as one group. Report dev-CV twice, with the current
  folds and with twin-grouped folds (pair key = the lower id). Exclude the twin of every evaluated
  dialogue from few-shot pools, synthetic-twin seeds and learned-fusion training.
- **Mechanism.** Twins differ in 1-2 turns. Example: C01 vs C02 differ only in T004, card number vs
  invoice reference; the digits read out in T011 are identical. Any tuned component (threshold, few-shot
  pool, learned fusion, prompt edits made while looking at errors) can memorise the scenario and the
  "harmless word" of a pair instead of learning the distinction.
- **Falsify.** On cached B2 results (CPU only), run leave-one-fold-out threshold selection on (a)
  current folds and (b) twin-grouped folds, and compare out-of-fold flag F1 and FAR. Run the same
  comparison for A8 twin few-shot once it exists. H0: no difference (|ΔF1| < 0.03). Expected: no effect
  for an untuned threshold. For few-shot, expect +0.05 to +0.15 apparent F1 under leaky folds that
  disappears with grouping. Detectable for few-shot (an effect concentrated on the 16 Stufe2 dialogues);
  hard to detect for the threshold.
- **Cost.** 0 GPU. About 60 LOC: a `group_key` (twin map) in `splits.py`/`eval.py`, and a
  `twins.yaml` derived from text similarity of the scripts (no labels needed).
- **Risk.** The locked split must not be regenerated (rule 3), so this changes reporting, not the
  file. If the hidden set contains the other halves of the given twins, leaky CV may actually be the
  right estimate. **Ask the organisers** whether the hidden set has new scenarios or more twins.

### N2: Threshold policy for an unseen test set; cross-family negatives plus plateau centre
- **Idea.** Each call has one target family, so every (call, other family) pair is a negative for that
  family. That gives about 200 family-level negatives on dev instead of about 22 no_alert calls. Use
  them to set **per-family thresholds** at a fixed family-level false-positive rate (e.g. ≤ 2%,
  Bonferroni-style, because the call label is a max over 5 families). Then choose the global knob at
  the **centre of the widest F1 plateau**, not at the argmax.
- **Mechanism.** The max over 5 families inflates false alarms: about 1-(1-p)^5. Argmax thresholds on
  24 dialogues sit on a cliff edge. Negatives are plentiful and stable, positives are scarce. FAR is the
  term the jury sees first.
- **Falsify.** Leave-one-fold-out over the 4 dev folds with three policies: argmax global, plateau
  centre global, and per-family FP-quantile. Metrics: mean and **worst-fold** (FA + miss), and the SD
  of the chosen threshold across folds. Expected: similar mean F1, about 30-50% lower worst-fold FAR and
  a 2x more stable threshold. This is a variance claim: report per fold and do not call it significant.
- **Cost.** 0 GPU. About 120 LOC: `fusion/perfamily.py` (subclass with `thresholds: {fam: t}`), a
  `suggest` routine in eval, and a UI slider that still moves all thresholds together through an offset.
- **Risk.** A call can incidentally touch another family, which adds label noise to the negatives.
  Per-family thresholds make "one threshold" harder to explain. Keep one slider that shifts all of them.

### N3: Quote-grounded verdicts plus "no verified passage, no alarm"
- **Idea.** The judge must return verbatim `quotes` (≤ 25 words each) with segment ids, plus the id
  of the `alarm_when` clause it applies. Code verifies every quote against the cited segment
  (rapidfuzz partial_ratio ≥ 85, on the same view). A "present" verdict without a verified quote is
  downgraded to "undetermined" at half confidence. In fusion, an alarm needs ≥ 1 verified passage of
  ≤ 60 s or a keyword/pattern hit of the top family. Otherwise it becomes review with the reason
  "kein belegbarer Abschnitt".
- **Mechanism.** 7B judges primed with long criteria produce plausible but ungrounded "present"
  answers. Grounding filters them out, and the jury requires passage + criterion for every hit anyway,
  so precision and traceability improve together.
- **Falsify.** Same view and LLM: llm_judge vs `grounded_judge`. Metrics: FAR on no_alert calls, flag
  F1, % of alarms with a verified quote, and passage hit rate vs Belege turns. Expected: FAR down 2-4
  calls, recall unchanged, verified-quote rate going from unknown to 100%. Detectable only if ≥ 3
  dialogues flip with no losses.
- **Cost.** About 10-15 min for 60 calls × 5 families (output length about +40 tokens). About 120 LOC:
  `checks/grounded_judge.py` subclassing LLMJudgeCheck with its own schema and prompt version, plus a
  `require_verified_passage` knob in fusion.
- **Risk.** On ASR text, noisy quotes may fail verification even when the judgement is right. Measure
  the false-rejection rate on true alarms. Fall back to a looser ratio (75) on noisy calls.

### N4: Anchored full-call probes instead of ±N windows
- **Idea.** For every anchor (keyword hit, pattern digit run, or segment cited by geval's locate
  call), ask one G-Eval digit question with the **whole transcript** (shared, prefix-cached), focused on
  that anchor: "Rate segment S011, using any context from anywhere in the call that decides what S011
  means." Family score = max over anchors. The passage is the anchor itself, so localisation is exact.
- **Mechanism.** In the twins the decisive context is far from the act. In C01 the context is in T004
  and the act in T011, 7 turns apart. A ±3 window (`keyword_context`, queue item C2) cuts it off, while
  a full-call question without an anchor spreads attention over the whole call and localises poorly.
  With prefix caching, anchoring costs about 1 output token per anchor.
- **Falsify.** Compare plain geval, keyword_context (±3) and anchored probes. Primary metric: **twin-pair
  AUC** on dev Stufe2 pairs (is the alarm twin scored above its harmless twin? threshold-free, about 5
  usable dev pairs × 2 audio versions). Secondary: FAR on keyword-heavy harmless calls (D03 type) and
  Stufe1 recall. Expected: the window variant loses ≥ 1 pair against plain geval, and anchored probes
  win ≥ 1-2 pairs. Only a sign across pairs is measurable here, not significance.
- **Cost.** About 5 min (single-token answers, about 3-8 anchors per call). About 150 LOC:
  `checks/anchored.py` that reuses geval `score_distribution`.
- **Risk.** No-keyword alarms have no keyword anchor, so anchors must also come from geval locate or
  from semantic windows. If geval locate is wrong, this is just a re-ask.

### N5: One-pass turn-level event log plus deterministic rules
- **Idea.** One LLM call per call (not per family) emits a JSON list of *events* for relevant turns
  only: {seg, speaker_role, act ∈ [request_trade, cite_info_source, read_value, give_third_party_data,
  ask_to_omit, ask_to_split, warn, refuse, quote_or_example, correct_note], object, mode ∈ [actual,
  hypothetical, quoted, negated], info_status ∈ [public, internal, unknown]}. Officer-readable YAML rules
  over the ordered event list decide alarm/review/no_alert per family. Example: read_value(actual,
  customer) followed by anything is an alarm unless the value was marked expired or a sample before it
  was read.
- **Mechanism.** It is family-agnostic, unlike A1, which asks per-family facts. A new family becomes a
  new rule, not a new prompt. Time order and "who" are explicit, so "a later refusal does not undo it"
  becomes a rule instead of a hope. It costs 1 request instead of 5-15.
- **Falsify.** Compare against llm_judge and A1 on dev-CV flag F1 and review recall. Count events that
  are missing on alarm calls (event recall vs Belege turns). Expected: equal F1 (±1 dialogue) at 5x
  fewer requests. It wins only if 7B extraction recall on decisive turns is ≥ 90%. Kill it if event
  recall is < 80%.
- **Cost.** About 5-8 min (600-900 output tokens per call). About 250 LOC: `checks/events.py` plus
  `config/event_rules.yaml`.
- **Risk.** Long JSON lists from a 7B model drift. The enum has to fit unseen scenarios in the hidden
  set; mitigate with `act: other` plus a free-text field that triggers review.

### N6: Log-probability fact probes (a sharper A1)
- **Idea.** Per family, 3-5 atomic yes/no/unclear questions derived from the criteria. Example for
  trade: Q1 "Äussert eine Person einen eigenen Kauf-/Verkaufswunsch?", Q2 "Wird er mit selbst erhaltener
  interner/nicht öffentlicher Information begründet?", Q3 "Ist die Information laut Gespräch bereits
  öffentlich?" Each is answered by **one token**, and `choice_probs(["Ja","Nein","Unklar"])` gives
  calibrated P per fact. Family score = noisy-AND of the required facts × (1 − P(exculpatory fact)).
  Review when a required fact has a high P(Unklar).
- **Mechanism.** It splits "is the act there" from "is the context incriminating", which is exactly the
  Stufe2 contrast. It avoids one-shot priming by the whole criteria block. It yields probabilities
  instead of an enum and almost no output tokens. Every fact maps to a criterion sentence for the UI,
  which gives traceability.
- **Falsify.** Compare against geval and llm_judge on the same view: dev-CV flag F1, twin-pair AUC,
  review recall. Expected: twin-pair AUC +0.1 and FAR −2 calls. Kill it if F1 drops more than 1
  dialogue relative to geval.
- **Cost.** About 5 min (5 families × 4 questions × 60 calls = 1200 single-token requests sharing the
  transcript prefix). About 200 LOC: `checks/fact_probes.py`, with questions in a **separate
  `config/facts.yaml`** so the policy-view cache keys of the existing LLM checks stay unchanged.
- **Risk.** The fact questions are hand-written from the dev scenarios and can overfit (see the devil's
  advocate section, argument 3). German vs English question wording matters; test both (cheap).

### N7: Two-axis decision (act × context resolution) for review
- **Idea.** Replace "undetermined = middle of one scale" with two scores per family: A = P(act
  happened), from N6 Q1 and Q2 or a dedicated digit, and C = P(decisive context unresolved). The rule:
  A high and C low gives alarm; A high and C high gives review; A low gives no_alert. The threshold
  slider moves A, and a second "Prüfband" slider moves C.
- **Mechanism.** The 1D band mixes "weak evidence" with "strong act, unknown context", and only the
  second is a Stufe3 case. C17 is the prototype: a value is read out, and whether it is valid stays
  unknown. A 1D score puts it at 0.5 next to every half-confident false alarm.
- **Falsify.** On dev: review precision and recall plus the FAR of the decided calls, against the
  current band. With only 3 dev review dialogues, statistics are not possible. Report a qualitative
  per-call table and use N13 synthetic "review twins" for a larger count.
- **Cost.** About 0-3 min on top of N6. About 120 LOC: `fusion/twoaxis.py`.
- **Risk.** Two sliders are harder to explain. The second axis can stay hidden behind defaults.

### N8: Prefix-max for act families (temporal monotonicity)
- **Idea.** Under the policy, the act cannot be undone ("frühere Warnungen oder ein späterer Abbruch
  heben eine erfolgte Preisgabe nicht auf"). For access and disclosure only, also score the transcript
  **cut right after each candidate act turn** (pattern digit runs, advisor turns after "Vollmacht")
  plus one turn. Family score = max(full call, prefixes).
- **Mechanism.** 7B judges show recency bias. The advisor's closing refusal ("Bitte kei weitere Werte
  vorzläse", "Mir mache da kei Zahlabgliich") reads as exculpatory, and the model under-scores an act
  that already happened. Prefixes share KV with the full prompt, so they are cheap.
- **Falsify.** Compare misses on access/disclosure alarm calls with FP on their harmless twins and on
  Stufe3 (full vs prefix-max). Expected: misses −1 to −3, FP +0 to +1. Keep it only if net ≥ +2
  dialogues. Do not apply it to trade: in D03 the exculpatory context (T008, "the report has been
  public since yesterday") comes *after* the keyword turn (T006), so prefix scoring would create a false
  alarm.
- **Cost.** About 3 min. About 100 LOC: `checks/prefix_max.py`, a geval subclass.
- **Risk.** Exculpatory context that comes after the act ("das isch en abgloffene Code gsi")
  produces false alarms. Include 1-2 following turns and measure.

### N9: Occlusion-based evidence and evidence concentration
- **Idea.** For each flagged (call, family), re-score G-Eval with each candidate turn masked as
  "[Segment entfernt]". The turns with the largest score drop are the passage. "Evidence
  concentration" (top-1 drop / sum of drops) becomes an uncertainty feature: diffuse evidence goes to
  review.
- **Mechanism.** Model-cited evidence ids are post-hoc and often cite whole stretches (hence the 60 s
  passage cap in fusion). Occlusion is causal for the score that actually decided. It improves snippet
  precision (traceability, 25%), and concentration may predict errors.
- **Falsify.** (a) Passage hit rate vs Belege turns: occlusion top-2 vs geval locate vs llm_judge
  evidence, on about 20 dev alarm calls. Expected +15-25 points. (b) AUROC of concentration for "the
  decision was wrong" on dev. Kill (b) if AUROC < 0.65.
- **Cost.** About 30 flagged pairs × about 20 turns = 600 prefills of about 2k tokens (little prefix
  sharing after the mask) ≈ 1.2M tokens, about 6-10 min. About 150 LOC: a post-check `checks/occlusion.py`
  or a fusion helper.
- **Risk.** Redundant evidence (the same fact said twice) shows small drops per turn; mask pairs of
  turns or use the cited runs as units.

### N10: Hot-window ASR re-decoding with n-best keyword evidence
- **Idea.** After the cheap turbo pass, re-decode only ±8 s windows around anchors and around passages
  above the review floor (about 5% of audio) with large-v3 (Swiss German fine-tune), beam 5,
  `num_hypotheses=5` (CTranslate2 `generate`). A keyword hit's confidence = the share of hypotheses that
  contain it. Re-decoded text replaces the segment text in a view `de_hot`.
- **Mechanism.** The errors that matter cluster in seconds: negations ("nöd", "kei"), "vor de Meldig"
  and digit runs. That is where noisy calls lose. A full large-v3 pass collides with vLLM on VRAM;
  windows do not.
- **Falsify.** Keyword-spot recall on noisy calls and word accuracy on negation and digit tokens
  (asr-eval), then flag F1 on the hot view vs the turbo view. Expected: noisy keyword-spot recall +5-10
  points. Detection flips are probably within noise.
- **Cost.** Under 5 min of ASR with vLLM down (or large-v3 int8 next to vLLM; check VRAM), plus one LLM
  pass of about 10 min. About 200 LOC: a refiner view plugin.
- **Risk.** Segment boundaries, and mapping re-decoded words back onto segments. Low upside if ASR is
  not the bottleneck (see devil's advocate argument 2). Run V3 (the oracle ceiling) first.

### N11: Phonetic plus ASR-confidence keyword matching
- **Idea.** Add Kölner Phonetik matching (keyword gsw/de forms vs transcript n-grams, same code plus
  fuzzy ≥ 75) to catch dialect and ASR spellings, and scale each hit by the ASR word probability
  (`Word.prob` exists). Hits on low-probability words are shown as "möglicherweise verhört" and
  contribute less.
- **Mechanism.** Officers edit the keyword list in UI without knowing the ASR's spelling variants.
  Phonetic matching makes their list robust. Confidence weighting stops misheard keywords from
  creating false alarms.
- **Falsify.** Keyword-spot recall and precision (hits outside the Keywordstellen) on dev, current
  matcher vs phonetic. Expected: recall +3-8 points on noisy calls at ≤ 2 points precision loss.
  Detection impact is probably not measurable, because keywords are weak evidence by design.
- **Cost.** 0 GPU. About 120 LOC: `checks/keywords_phonetic.py`, a subclass so the keyword cache key
  stays stable.
- **Risk.** Short phrases collide phonetically (PIN/Pinn). Keep the acronym rules.

### N12: Speaker roles: asset or liability?
- **Idea.** On the oracle view (perfect text), run the judge with (a) oracle roles, (b) neutral
  "Sprecher A/B" and (c) swapped roles. On the ASR view, compare diarizer roles vs neutral.
- **Mechanism.** Disclosure (the *advisor* reveals) and access (the *customer* reads) hinge on who
  speaks. The prompt says roles "may be wrong". If the judge trusts wrong roles, neutral labels plus
  content-based inference may beat the diarizer. Sensitivity to swapped roles measures how much the
  diarizer's accuracy matters.
- **Falsify.** If (a) vs (c) flips ≥ 3 dialogues, roles matter, so measure diarizer role accuracy and
  invest there. If (a) ≈ (b), drop roles from LLM prompts; that is simpler and robust to the hidden
  set's voices.
- **Cost.** 3 LLM passes of about 8 min on the ref view, plus 1 on ASR, about 35 min. About 40 LOC: a
  role-transform view plugin (`roles: oracle|neutral|swapped`).
- **Risk.** Only large effects are visible. The oracle view is an experiment, never the submission.

### N13: Minimal-edit counterfactual twins from dev calls (synthetic stress test)
- **Idea.** For each dev transcript (ASR view, with its noise), the LLM writes a **minimal edit of 1-2
  turns** that flips the outcome according to a named criterion clause: alarm to harmless via a
  not_alarm_when line, harmless to alarm, or to review via review_when. That gives about 100-150 paired
  texts in the case's own twin design. Use them for threshold-free pair AUC when comparing prompts and
  checks, and as extra negatives and positives for N2 and N7.
- **Mechanism.** 5 dev twin pairs cannot separate prompt variants; 100+ synthetic pairs can. Edits keep
  the ASR noise and call style, which D1's from-scratch scripts lose. Generated with one model family
  and evaluated with another, it avoids rewarding the generator's own phrasing.
- **Falsify.** (a) Validity: a human spot-checks 15 pairs (10 min). Kill if < 80% flip as intended.
  (b) Usefulness: does the ranking of 3-4 configs on synthetic pairs agree with their dev-CV ranking
  (Kendall τ > 0.5)?
- **Cost.** Generation about 5-10 min, plus about 5 min per evaluated config (single-token checks).
  About 200 LOC: `synth/counterfactual.py`.
- **Risk.** Circularity: the LLM's notion of "harmless" is what we are testing. **Seeds must exclude
  C01, C03 and C05**, whose twins are in the holdout (N1). The synthetic pairs never become evaluation
  numbers for the jury.

### N14: Absence of evidence is not evidence of absence (fusion fix)
- **Idea.** In `_fuse_family`, rule-based checks that found nothing (keywords/patterns with score 0)
  stop contributing to the **disagreement** term, and optionally to the mean as well. A knob
  `absent_rule_checks: ignore|mean_only|full` (default `full`, the current behaviour). Real
  disagreement (keyword hit vs LLM "absent") still counts.
- **Mechanism.** See finding 2 above. Today a clear no-keyword alarm with a G-Eval confidence of ≤ 0.6
  is escalated to review. That is the Stufe2 alarm profile, so this hurts misses (and review precision)
  where the case is most interesting.
- **Falsify.** Replay fusion on cached B2 results (CPU): count alarm-labelled calls decided "review"
  where the uncertainty rule fired and keywords had no hit. Then compare F1, miss rate and review
  recall with the knob on and off. Expected: +2-6 correct alarm calls (+1-3 dialogues), with possibly
  −1 Stufe3 call that was "right for the wrong reason". Detectable as a mechanism: every flip has a
  traceable cause.
- **Cost.** 0 GPU. About 30 LOC plus a test.
- **Risk.** Low. Review recall might drop if Stufe3 currently reaches review through this artefact;
  that would itself be worth knowing.

### N15: G-Eval-first cascade (a sharper F4/A2)
- **Idea.** Gate the expensive reason and evidence calls (llm_judge, geval locate) with the
  **single-token G-Eval score**, not with keywords. Run the judge only for families with geval ≥ 0.25.
- **Mechanism.** A keyword gate (as in A2) has low recall by construction on Stufe2, which mostly has
  no keywords. G-Eval with a cached prefix costs one output token per family, so the gate keeps recall
  and drops about 70-80% of output tokens. That makes a strong cost story for feasibility and the
  operating concept.
- **Falsify.** Simulate exactly from cached B2 results (CPU): the cascade's decisions and judge calls
  saved, and, for reference, the recall of the keyword gate on dev alarm calls. One GPU timing run
  (about 5 min) gives seconds per call. Expected: the same label on ≥ 58/60 calls and 3-4x fewer output
  tokens.
- **Cost.** About 5 min GPU. About 80 LOC: a `cascade:` option or a wrapper check.
- **Risk.** If G-Eval misses a family that the judge would catch, the miss is silent. Log gated-out
  families with their score.

---

## Ranked top 5: expected value per GPU-hour (about 5 GPU-hours left tonight)

All of these need the B2 baseline cache (transcripts plus llm_judge/geval/keyword results on 60 calls).

| rank | id | GPU cost | why it ranks here |
|---|---|---|---|
| 1 | **N14** absent-keyword fusion fix | 0 (CPU replay) | A mechanism-level loss on the Stufe2 alarms is already shown in simulation. A 30-LOC fix, and possibly the largest single miss-rate gain available tonight. |
| 2 | **N1** twin-aware evaluation | 0 | Protects every other decision tonight from leaky CV. Must be in place before A8 few-shot, F3 learned fusion or N13 are judged. |
| 3 | **N6** log-probability fact probes (then N7 on top) | ~0.1 h | Single-token, prefix-cached. Directly targets the twin distinction and review handling, and every fact is a criterion sentence (traceability). |
| 4 | **N4** anchored full-call probes | ~0.1 h | Cheap, exact localisation. Tests whether the planned ±3 window design (C2) is structurally wrong for twins whose context is far from the act. |
| 5 | **N3** quote-grounded judge plus passage gate | ~0.25 h | Cuts ungrounded false alarms and guarantees "every hit has passage + criterion". |

Run alongside at no GPU cost: **N2** (threshold policy, the same CPU replay as N1/N14) and **N15**
(cascade simulation; 5 min GPU for timing only). Run next if time remains: N8 (about 3 min GPU), N12
(about 35 min).

---

## Devil's advocate: 3 arguments against the current architecture

**1. The weighted-mean fusion with "uncertainty = disagreement" is wrong-footed for this case.** It
averages checks that are *designed* to disagree: context-blind keywords vs context-reading LLMs. So the
uncertainty spikes exactly on the two case-defining situations: no-keyword alarms (Stufe2, shown above)
and keyword-heavy harmless calls (D03 type). The label is then a max over 5 families of
non-probabilities, with hand-set weights (0.35 / 0.2 / 1 / 1), so the threshold has no stable meaning
on a new test set.
*Evidence that settles it:* the N14 replay (how many dev calls flip on the absent-keyword rule), plus a
reliability diagram of the fused family score (cross-family negatives give about 200 points). If
calibration error is > 0.15 or ≥ 2 dialogues flip under N14, the fusion needs restructuring
(N14 + N2 + N7). If neither happens, the current fusion is fine.

**2. Tonight's GPU plan is ASR-heavy, but ASR is probably not the bottleneck.** ASR runs at 1.5% of
realtime and the scripts are clean synthetic TTS. The queue spends many items on ASR and views (A1-A7,
V1-V4, D2-D3), while the decisions hinge on whether a 7B model can tell a quoted/negated/public act from
a real one. That is a reasoning problem that perfect text does not solve.
*Evidence that settles it:* V3 (oracle ref view) vs the ASR view with the same checks, per level. If the
gap is ≤ 1-2 dialogues, freeze ASR and put all GPU time into the judge (N3/N4/N6, L1 model size). If the
gap is ≥ 4 dialogues and concentrated on noisy calls, ASR work (N10, A6, A7) is justified.
**Run V3 before any ASR sweep.**

**3. The hidden-set estimate is contaminated and the criteria may be fitted to these 30 scenarios.**
(a) Twin leakage: half the holdout (C02, C04, C06) has its near-copy in dev. (b) `criteria.yaml` was
committed (4b363be, 00:05) **before** `splits.yaml` was locked (01:17), and its alarm_when /
not_alarm_when lines track the case's specific scenarios (Kreditstelle, "eine Rechnung in
Teilzahlungen", "nur letzte vier Stellen", "abgelaufener Wert"). If its authors had read the expected
labels, the holdout is not clean for criteria text. New scenarios on Sunday could then lose much of the
apparent gain.
*Evidence that settles it:* run the champion with **generic criteria** (only the one-line
`policy_examples` from keywords.json) vs the detailed criteria on dev, on the holdout, and on N13
synthetic twins built from *new* scenarios. If the gain of the detailed criteria shrinks by more than
half outside the case scenarios, it is fitted to those scenarios. Write the criteria more generally,
and say so in the pitch ("we report the generic-criteria number as our hidden-set expectation"). Also
record in DECISIONS.md who wrote criteria.yaml and whether they had read the Sollbewertung files.
