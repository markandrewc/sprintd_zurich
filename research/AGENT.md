# Research protocol for the overnight agent

Goal: produce evidence the team can use to choose and defend the Sunday configuration. One clear,
honest comparison beats ten sloppy ones.

## 1. What we optimize

Primary (on **dev folds**, cross-validated):
- **flag F1**: positive = the system sends the call to a human (alarm or review) and the call should be
  looked at (expected alarm or review). This is "few false alarms, few missed cases".
- with **false-alarm rate <= 20%** (FP / expected no_alert) as a soft cap.

Always also report: alarm-only P/R/F1, review recall (expected review -> predicted review), 3-class
accuracy, miss rate, per level (Stufe1/2/3), clean vs noisy, family hit rate, cost (GPU seconds per call
minute, LLM calls per call), and for ASR: WER/CER + keyword-spot recall.

Until the organizers answer how `review` is scored (see `docs/CASE.md`), report both the flag view and
the alarm view; never optimize one silently at the expense of the other.

## 2. Data discipline

- 30 dialogues x (clean, noisy). The fold assignment is `config/splits.yaml` (or `data.split_dialogues`
  if the lock file does not exist yet: 5 folds, seed 13, stratified). **Fold `holdout` is locked.**
- Tune prompts, weights, thresholds, few-shot pools and learned fusion on dev folds only, with
  cross-validation across dev folds for anything fitted (threshold, weights, calibration).
- The holdout is evaluated **once per final candidate** (`callguard eval --split holdout`), at the end;
  every holdout run is appended to `runs/holdout_log.jsonl`. If you look at it, it is logged; looking
  more than twice makes it worthless - say so in the report if it happened.
- Synthetic calls are extra dev/training data, never part of any reported test number.
- Never feed call ids / file names / scripts / expected labels into the pipeline (case rule). Oracle
  experiments with reference scripts are fine *as experiments* and must be labelled ORACLE.

## 3. Statistics (30 dialogues is small)

- Unit of resampling = dialogue (its clean + noisy call together).
- For every comparison of option A vs B: paired bootstrap over dialogues (>= 2000 resamples) of the
  difference in flag F1 (and FAR, miss rate) -> 95% CI; McNemar exact test on per-call correctness.
- Call a difference "real" only if the 95% CI of the difference excludes 0. Otherwise write
  "no detectable difference at n=30" and decide on cost / simplicity / traceability instead.
- Always list the calls that flip between A and B (call id, expected, A, B, the decisive passage, both
  reasons). Teammates will argue with examples, not with F1.

## 4. Experiment hygiene

- One hypothesis = one queue item = one experiment spec `experiments/<queue-id>.yaml`.
- Record the git commit, config, model ids/versions, served LLM, and cache state in the finding.
- Change one thing at a time against the current best ("champion") config; ablations go both ways
  (add to the baseline, remove from the champion).
- Expensive stages are cached (ASR per model, translations, LLM checks per prompt version). Do not
  delete `.cache/`. If you change a prompt, bump its PROMPT_VERSION so caches don't lie.
- Before a long run: `callguard experiment ... --dry-run` to see what will be computed; estimate time
  from the journal's timings. Prefer finishing a smaller experiment over starting a huge one at 06:00.
- GPU memory: vLLM (~70%) + one Whisper fits; do not run two Whisper large models next to vLLM. To
  switch the LLM model, restart vLLM with the same `--served-model-name callguard-llm`; LLM-check caches
  are keyed on the real model id, so results don't mix.

## 5. Accept / reject

A change becomes the new champion when on dev-CV: flag F1 improves with the CI of the difference
excluding 0, **or** it is not worse (CI includes 0) and it is clearly cheaper / simpler / more
traceable, **and** FAR stays under the cap. Code changes that implement an accepted idea go to `main`
(tests green); research artifacts go to `overnight`. Rejected ideas stay documented (that is evidence too).

## 6. Writing findings (`research/findings/RQ<n>.md`, template `_TEMPLATE.md`)

Question; setup (commit, config, split, n); result table with CIs; per-call flips; cost; 2-3
qualitative examples (passage + reasons); **recommendation**; **strongest counter-argument** (when
would the other option win? what did we not test?); what would change our mind. Plain language, short.
Update `research/DECISIONS.md` when a finding settles a decision; keep dissent recorded.

## 7. Journal (`research/journal.md`, append-only)

Every entry: `## <ISO time> <queue-id> <title>` then what you did, the command, the result in one
line, the decision, and anything that broke. Also log autonomous decisions ("vLLM would not start,
switched to llama.cpp because ...").

## 8. Cadence

Each round (30-90 min): pull -> pick -> run -> analyse -> write -> `callguard report` + leaderboard ->
update MORNING_REPORT.md -> commit + push to `overnight`. MORNING_REPORT.md must be readable and
current after **every** round, so the user can stop you at any time and still have the result.

## 9. When the queue runs dry

Look at the latest per-call flips and misses: which calls does the champion still get wrong and why
(ASR error at the decisive word? wrong role? the LLM misses the "later refusal does not undo it"
rule? keyword-only reasoning?). Turn each failure pattern into a hypothesis with a cheap test, add it to
`research/queue.yaml` with priority, and continue. Also consider: bigger/other LLM if VRAM allows,
prompt variants (criteria in English vs German, more/less context), view ensembles, alternative
thresholds per family, synthetic hard cases for the weakest family, ASR fine-tune trial (finetune/).

## 10. Morning (by 07:30)

Freeze the champion -> `config/recommended.yaml` -> one holdout run -> finalize MORNING_REPORT.md,
DECISIONS.md, report charts -> push. Leave services running and write how to stop them.
