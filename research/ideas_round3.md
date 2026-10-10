# Ideas round 3: last review before submission (2026-10-10, Saturday)

Scope: the frozen champion (`config/recommended.yaml`: large-v3 MIT ASR, Qwen2.5-7B, tuned `facts` table v1,
light keywords/patterns, threshold 0.55). Sunday: hidden set of about 18 new calls (about 30% more), run once.

**What I read:** MORNING_REPORT, DECISIONS, DEMO, journal (last 400 lines), ideas_round1/2, findings RQ5/RQ9/RQ10,
recommended.yaml, policy_table.yaml, facts.py (knobs only), sim_rules.py, run_staged.sh, the queue.
**What I did not do:** look at any holdout call or result beyond the logged summary, or run any experiment.
Everything marked "expected" below is a hypothesis.

---

## 1. Biggest hidden-set risk: new wording leads to silent misses, because the default rule clears every call

**The risk.** The champion fails in one direction. When a call is phrased in a way the tuned questions do not
expect, a decisive fact moves from `yes`/`unclear` to `no`. The family then falls through to the last rule,
`true -> no_alert`. The officer sees "Kein Alarm" with high certainty, with no review and no warning.

| evidence | false alarms | misses / direction |
|---|---|---|
| holdout (12 calls, frozen champion) | **0%** | **50% miss** (C16 splitting, C19 open documentation) |
| synthetic, 7B facts v1 (74 scripts, fresh scenarios) | 7% | **43-48% miss**; access 3/12 flagged (14B) |
| paraphrased questions R3 (same meaning) | 23% | **all 11/48 flips worse**; 7 of them lose a flag or the review (D05-K1, C07-K4 alarm -> no_alert; C17 x2, C18 x2 review -> no_alert) |
| dev champion, decided calls (RQ9) | | 4 wrong of 38, **all 4 are misses** (C09 x2, C20 x2) |

**Mechanism (measured in R3):** 217 of 256 fact disagreements under rewording are `no <-> unclear` flips. The mean
|dp(yes)| is only 0.038. The review rules that test `= unclear` (disclosure.review_2, trade.review_1,
documentation.review_1, splitting.review_1) therefore depend on noise. When `unclear` tips to `no`, the review
disappears and the call is cleared.

The expected hidden-set AUC of about 0.75-0.80 (instead of 0.87) is mostly **lost recall, not extra false alarms**.
That is the costly error in compliance, and it is what "detection quality" will punish. No knob can fix it on
Sunday: the scores are near-discrete, so the threshold slider is flat from 0.45 to 0.65.

**Cheapest mitigation (Saturday, 0 GPU to test, about 1-2 h of work).** This is S1.
Use the paraphrase runs that are already cached as a **wording-shift simulator**, and harden only the review side
against it.

1. **Asymmetric "no" (new 10-LOC default-off knob in `facts`: `no_at`, roles context and authorization only).** A
   fact counts as `no` only if p(no) >= 0.8. `yes` stays at p(yes) >= 0.5. A shaky "no" becomes `unclear`, so the
   existing `= unclear` review rules fire instead of the call being cleared. Alarm rules are untouched.
2. **Add the table v3 "open" facts.** They are already built and criteria-derived. On dev and synthetic they cost
   0 false alarms (DECISIONS D2b).
3. Variant (b), for comparison: **wording disagreement -> review.** Keep the champion label. Escalate only
   no_alert -> review when the cached `para` or `para2` answers would flag the call. On Sunday this costs about 2x
   fact probes (about +0.5 s per call).

**How to test without the holdout.** Extend `scripts/research/sim_rules.py` to read any `results.jsonl`, then
re-decide on the cached fact probabilities:
- dev: `runs/experiments/champion/{champion,para,para2,table_v3}/results.jsonl`
- synthetic: `runs/experiments/synth_stress/{facts7b_v1,facts7b_para,facts7b_para2,facts7b_v3}/results.jsonl`

For the para runs, take the v3 "open" facts from the table_v3 or facts7b_v3 results of the same call.

**Pre-register these acceptance rules in the journal before running:**
- (a) Dev champion cache, fixed t = 0.55: at most +1 harmless dialogue newly flagged (FAR <= 5/22). CV FAR <= 20%.
- (b) Synthetic 7B: FAR rises by at most 7 pp.
- (c) Wording-shift bench (dev para/para2 and synthetic para/para2): mean miss drops by at least 10 pp, and the
  label flips vs champion drop.
- If any rule fails, keep the frozen champion and show the hardened table only as the UI's "strengere Prüfung"
  policy.

If it passes, it is still an unvalidated rule-only change. v3 was also designed knowing that splitting failed on
the holdout. Say "nicht auf dem Holdout validiert" on the slide, and log the decision in DECISIONS D2b.

Known trap: a generic "act = yes, not cleared -> review" net equals `table_v2` in the access family. That flagged the
harmless "4242..." test card numbers (C01/C02) and pushed FAR to 36%. Keep access out of any generic net.

**Two zero-risk operational items, found while reading:**
- **`runs/recommended/` contains the E2E test calls `call_a/b/c`.** The UI globs every `*/result.json`, so the Inbox
  shows **63 calls, 18/12/33**, not DEMO.md's 60 calls, 17/11/32. The demo item 2 numbers will be off on stage.
  Move the three folders out (for example to `runs/e2e_new/`) before rehearsing.
- **Sunday run-once hygiene.**
  - Write the hidden set into a fresh directory: `--set paths.runs_dir=runs/hidden`, and point `paths.data_dir` at
    the delivered folder.
  - Rehearse the exact `scripts/run_staged.sh` procedure on about 12 re-encoded dev calls, not 3 as in the 04:50
    E2E run. Expect at least 11/12 labels to match the cached ones.
  - Then run `callguard doctor -c recommended`. A vLLM hiccup turns calls into "failed check -> review", which looks
    exactly like the v1 "flag everything" failure.

---

## 2. Six ideas the night did not try

| id | idea | value | cost | expected effect |
|---|---|---|---|---|
| S1 | Wording-shift bench + review hardening (section 1) | **score** | 0 GPU, 1-2 h | fewer silent misses under new wording; FAR cost unknown, test decides |
| S2 | Contrastive twin few-shot inside fact probes | score | 2-3 h, about 30 GPU-min | lower wording sensitivity; AUC within noise |
| S3 | "No silent clearance": verified exculpation quote | **score + pitch** | about 2 h, about 3 GPU-min dev | catches act-yes misses; strong traceability story |
| S4 | `prefix_max` (built, never evaluated) + anchored re-ask of boundary facts | score | config flip + about 1 h, about 10 GPU-min | 1-3 dialogues, not detectable |
| S5 | Audio test-time augmentation: facts over 3 re-decodes | score (robustness) | 1-2 h, about 30 GPU-min | fewer clean/noisy flips at the p≈0.5 boundary |
| S6 | Fact-level officer feedback ("answer the open fact") | **pitch** (usability, impact, creativity) | 2-3 h UI, 0 GPU | no score effect; best live moment of the demo |

### S1. Wording-shift bench + review-boundary hardening

See section 1. It is new in two ways:
- It uses the R3/R6 paraphrase caches as a **test bench for any rule change**. The night used them only to measure
  fragility.
- The asymmetric "no" is not the rejected `unclear_band`. ens3_band decided from p(yes) alone and turned 469
  unclear values into `no`. This knob moves only shaky `no` values to `unclear`.

**Falsification:** the acceptance rules (a)-(c) in section 1.

### S2. Contrastive few-shot from the case's own twin pairs

- **Idea.** Per family, put one minimal pair before each fact question: the 2-4 decisive turns of a dev alarm twin
  and of its harmless twin, with the correct fact answers. Example: C12 vs C11 for disclosure. The block is a fixed
  prefix, so it stays prefix-cached.
- **Mechanism.** The examples define what a fact means beyond its wording. R3 shows that this wording dependence is
  the fragility. The examples also give the hedging 7B a calibrated picture of a clear "yes" and a clear "no"
  (today p(unknown) is 0.8-1.0 on most context facts).
- **Falsification.** Fold-aware CV: the exemplars come only from the training folds, and the exemplar dialogue is
  never scored. That means 4 prompt sets. Never use holdout twins (C03/C04, C15/C16).
  - Primary: the flip rate between champion wording and `para` wording, with vs without exemplars. Baseline 11/48.
    Success if it is 5/48 or lower.
  - Secondary: dev AUC no worse than -0.03; synthetic 7B AUC at least 0.80; FAR at most 20%.
  - Kill if the flips do not drop.
- **Cost.** About 2-3 h: an exemplar block in `fact_prompts.py` (default off, so cache keys stay stable) and per-fold
  selection. About 5 GPU-min per fold per wording, so about 30-40 GPU-min.
- **Expected.** Halves the wording sensitivity at best. AUC changes will not be detectable at n = 24.
- **Risk.** Twin leakage, if a fold's own twin is used as its exemplar.
- **Value.** Score. Pitch angle: "the bank teaches the system with its own example calls".

### S3. "No silent clearance": a harmless verdict needs a verified exculpation quote

- **Idea.** When a family has act = yes (or a non-negated keyword hit) but ends as no_alert, ask once for the
  **verbatim sentence** that clears it, with its segment id. Then fuzzy-verify that sentence against the transcript.
  If no quote verifies, the call goes to review with the reason "Handlung festgestellt, Entlastung nicht belegt".
  A verified quote goes into "Warum kein Alarm?" with a timestamp and a play button.
- **Mechanism.** The champion clears a call when a context fact drifts to `no`. That needs no evidence at all.
  Real harmless twins state their exculpation explicitly: C05 public = 1.00, C10 expired = 0.93, D03 "seit gestern
  Morgen öffentlich". So requiring proof is cheap for true negatives and expensive for drift.
- **Falsification.**
  - Dev: every harmless dialogue with act = yes must produce a verified quote. Kill if 2 or more harmless dialogues
    lose their clearance.
  - Synthetic 7B: miss must drop by at least 5 pp at FAR +7 pp or less.
  - Also check on the `para` caches whether the gate fires on the 7 calls that rewording turned to no_alert. Only the
    one new probe per call is needed.
- **Cost.** About 2 h (a default-off option on `facts`, or a small `exculpation` check plugin). About 1-2
  generations per call, about 3 GPU-min on dev.
- **Expected.** Catches act-yes misses (D05-K1 and C07-K4 type, the trade inside-info drift). It does not catch
  act-unclear cases (C20), which are v3's job.
- **Value.** Score and pitch: it turns "Warum kein Alarm?" from a model score into a quoted, playable alibi
  (traceability, 25%).

### S4. Evaluate `prefix_max` and re-ask boundary facts anchored to the act

- **Idea.** `facts.prefix_max: true` (N8) is already implemented: act facts are asked on growing prefixes and the
  maximum p(yes) is kept. `experiments/facts.yaml` has a variant, but **no result exists** in `runs/experiments/`.
  - Add a re-ask of context facts with p in [0.3, 0.7], restricted to the transcript up to 3 turns after the act's
    evidence segment.
  - Exculpatory facts always read the whole call. D03's late clarification must still count.
- **Mechanism.** Recency bias from a closing refusal ("Bitte keine weiteren Werte"), and long calls where the
  decisive context sits far from the act (C06-K4, 54 segments).
- **Falsification.**
  - Label-free first: clean/noisy pair consistency on dev, against the champion's current inconsistency count.
  - Then dev AUC and FAR.
  - Kill if any harmless twin flips or FAR rises.
- **Cost.** Config flip plus about 1 h for the anchored re-ask. About 10 GPU-min.
- **Expected.** Fixes 1-3 dialogues at most. Not detectable. Do it only if S1 and S3 are done.

### S5. Audio test-time augmentation: majority over re-decodes

- **Idea.** Transcribe each call 3x:
  1. the original;
  2. speed 0.97 / 1.03 (the 04:50 E2E used sox speed 1.04 with identical labels on 3 calls);
  3. a telephone band-pass plus light noise.

  Run facts on each, average the fact probabilities, and send label disagreement to review.
- **Mechanism.** The night found that 4 of 7 clean/noisy disagreements had the **clean** version wrong, with
  answers near p = 0.5 (ideas_round2 §0.4). That is LLM instability at the boundary, so a natural perturbation
  ensemble should help. Unlike the paraphrase ensemble, it does not dilute the tuned wording.
- **Falsification.**
  - Primary: dev clean/noisy pair consistency (label-free, 24 pairs).
  - Secondary: AUC and miss.
  - Kill if dev AUC drops by more than 0.03 or the clean miss rate rises. Text-only synthetic cannot test it.
- **Cost.** ASR at 2.4 GPU-s per audio minute, about 20 GPU-min for 2 extra dev decodes, plus about 10 GPU-min of
  facts. 1-2 h of code (a perturbation preprocess plus new views, so cache keys stay stable). On Sunday it adds
  about 2 min for 18 calls.
- **Expected.** Fewer boundary flips. The AUC change is within noise.
- **Value.** Score/robustness. Pitch line: "we listen 3 times".

### S6. Fact-level officer feedback: the review card asks the open question

- **Idea.** The review card states the open fact as a question, for example: "Offen: Gehört der vorgelesene Wert zum
  laufenden Vorgang? Modell: unklar (0.30)". The officer clicks Ja or Nein.
  - The call is re-decided instantly from the policy table (no LLM).
  - The answer is logged in `feedback.jsonl` with the table hash. Today feedback is only call-level.
  - The Feedback page shows per fact how often officers overrule the model, which tells the team which question
    needs better wording.
  - Optionally, confirmed calls become S2 exemplars, which closes the loop.
- **Demo.** On C17-K3, answer "gültig = ja": the card turns into Alarm with an audit entry.
- **Falsification.**
  - Usability: a teammate who has not seen the UI resolves 3 review cards in under 60 s each.
  - Correctness: the re-decision equals the `sim_rules.py` output.
- **Cost.** 2-3 h of UI (`ui/views/feedback.py` and the `feedback.py` model exist). 0 GPU.
- **Expected.** No score effect. It answers the "a review is just a dumping ground" objection with a 10-second
  interaction.
- **Value.** Pitch: usability 25%, impact 20%, creativity 20%. "The system learns the bank's facts, not opaque
  scores."

Considered, not ranked:
- Role-aware probes for advisor misconduct (synthetic misses: advisor as the inside source, unsolicited advisor
  disclosure). Better handled by adding one criteria-derived fact per family to v3 than by per-turn probing.
- Quote-grounded judge (N3) and learned fusion (F3) are superseded by facts.

**Saturday order:** S1 (bench, 0 GPU) -> S3 -> S6 (in parallel, UI person) -> S4 -> S2 / S5 only if time remains.

---

## 3. Q&A cheat sheet: defending each architecture step

1. **ASR: Whisper large-v3 Swiss German (MIT).**
   - **Counter:** "Your keyword-recall CIs overlap and with the old checks ASR made no difference (0.66 vs 0.68).
     Turbo is 3x faster."
   - **Answer:**
     - With the old checks the LLM was the bottleneck. With facts, the better ASR shows: 7B 0.84 -> 0.89 AUC (CIs
       overlap; we say so).
     - Its lead is consistent: dev keyword recall 83.7% vs 70.7% (default turbo), noisy 80.4% vs about 63%, no false
       hits.
     - Perfect transcripts add only about 0.03, so ASR is no longer the bottleneck.
     - Licence: MIT vs a CC BY-NC origin for the turbo fine-tunes, so it is deployable in a bank.
     - Measured single-pass fallback: turbo clean 0.85.
     - Caveat: the case audio is TTS. Real callers are untested.
2. **Standard German view.**
   - **Counter:** "Translating dialect away loses information. Why not judge the dialect text?"
   - **Answer:** measured:
     - The 7B on *perfect* dialect text gets 0.76, vs 0.89 on Standard German ASR output.
     - The 14B copes with dialect (0.90 vs 0.85), so with a bigger GPU dialect becomes an option.
     - English adds nothing (0.82 vs 0.84).
     - The keyword list keeps gsw and de forms, and negations are marked ("kein PIN" at 00:22 in D05, score 0.10).
3. **Facts + policy table vs a free LLM judge.**
   - **Counter:** "20 hand-written questions tuned on 24 dialogues is overfitting. Rewording drops you to 0.72."
   - **Answer:** we ran that test ourselves and report it.
     - Tuned 0.87, paraphrased 0.72-0.74, blind table 0.73-0.85.
     - The false-alarm advantage survives every out-of-sample test: synthetic 14% vs 61% (-46 pp, real); holdout 0%
       vs 100%.
     - Facts vs judge on dev: +0.16 AUC (real), 3-class McNemar p = 0.0009.
     - Our honest expectation for new calls is 0.75-0.80, still above v1's 0.68 with 86% false alarms.
     - The table is officer-editable: tuning it on example calls is the compliance team's job, not a bug.
   - (Follow-up "the judge finds unlisted misconduct": as review-only escalation it set a FAR floor of 23-36%.)
4. **7B vs 14B.**
   - **Counter:** "Bigger is better. Why ship the small one?"
   - **Answer:**
     - Model size is not detectable here: 14B 0.87 vs 7B 0.84 on turbo, 0.85 vs 0.89 on large-v3; Qwen3-8B 0.74.
     - Check design moved AUC by +0.16, model size by ±0.1 within noise.
     - The 7B fits one 12 GB card next to everything; the 14B OOMs with the full set.
     - On ≥24 GB event GPUs the 14B is a free, safe upgrade (more robust on dialect: 0.90 vs 0.76 ORACLE).
5. **Threshold 0.55.**
   - **Counter:** "You picked it on dev. Why not optimise it?"
   - **Answer:**
     - It is not tuned. The facts scores are near-discrete, so flag decisions are identical anywhere from 0.45 to
       0.65, and 3-class labels from 0.55 to 0.65.
     - CV max-F1 picks the plateau edge 0.20, which turns every rule review (score 0.50) into an alarm. That is an
       artefact, so we pin the plateau centre.
     - The slider is an officer policy knob: 0.50 means "accept open facts as alarms" (Alarm 17 -> 28). The real
       levers are the named rules.
6. **Review handling.**
   - **Counter:** "Review recall 67% on 6 calls, and the holdout review case C19 was missed. Isn't review a dumping
     ground?"
   - **Answer:**
     - Every review names its rule and facts (C17: access.review_1, "Code vorgelesen = ja 0.92, offen ob gültig =
       ja 1.00").
     - On dev, 10/48 calls went to review and 7 of them needed a human. 38/48 were decided automatically with 4
       errors.
     - Generic uncertainty escalation was tested: FAR floor 36-41%, rejected.
     - Stricter modes exist with measured cost: blind second opinion gives review recall 83% at FAR 36%; open-fact
       table v3 gives dev review recall 100% at unchanged FAR (not holdout-validated).
     - A failed check is never cleared: it goes to review.
     - We say openly that n = 6 review calls cannot carry a reliability claim.
