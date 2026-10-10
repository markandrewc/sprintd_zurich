# Decision records

One record per decision. Status: proposed | accepted | superseded. Evidence links point to
`research/findings/`. Keep dissent: if a teammate disagrees, write their argument down.
Last update: 2026-10-10 04:35 (GPU-host overnight session). Champion frozen 04:09 = `config/recommended.yaml`.

## D0 How we measure (method) — accepted
- Dev = 24 dialogues (48 calls), 4 folds, Stufe2 twin pairs share a fold; holdout = 6 dialogues, locked, looked at
  twice (champion + v1 reference), both logged in `runs/holdout_log.jsonl`.
- Primary: threshold-free **flag AUC** + the CV operating point at **FAR <= 20%**; flag F1 is misleading here
  (flag-all = 0.70 on dev; on the holdout v1 "flag everything" and the champion both have flag F1 0.67).
- Paired bootstrap over twin groups (18 units), McNemar, flip tables; independent audit of the code (all metric math
  verified; ranking / holdout-logging / LLM-identity issues fixed).

## D1 ASR model and transcript view — accepted
- **`gcoli/whisper-large-v3-swiss-german-mit`** (MIT), fp16, beam 1, view `de` (Standard German).
- Evidence (RQ2, RQ3, RQ8): best keyword-spot recall (84% vs 71% default turbo, dev); with facts the ASR gain shows in
  detection (7B: 0.84 -> 0.89 AUC, CIs overlap); perfect transcripts add only ~0.03 (ORACLE); the 7B reads Standard German ASR
  at least as well as perfect dialect text (0.89 vs 0.76, CIs overlap); English translation no gain (0.82 vs 0.84).
- Licence: the turbo fine-tunes derive from a CC BY-NC model; large-v3 MIT is bank-deployable.
- Cost: needs a staged run on 12 GB (ASR first, then LLM): `scripts/run_staged.sh`.
- Dissent: turbo (with no prompt + condition_on_previous_text=false) is 3x faster and fits next to the LLM; on these
  TTS voices vanilla Whisper is competitive — real callers would favour fine-tunes.

## D2 Check set — accepted (with a known fragility)
- **`facts`** (atomic yes/no/unknown questions by log-probability + officer-editable `config/policy_table.yaml`) decides;
  keywords (w 0.15) + patterns (w 0.1) stay in the score with abstain-on-empty so the officer's keyword list has a
  visible effect.
- Evidence (RQ4, RQ5, RQ7): facts vs free judge +0.16 AUC (real), FAR 18% vs 86%; D03 and most harmless twins cleared (not C11/C14: review in the champion);
  free judge / G-Eval / quote judge / hybrids add false alarms at 7-8B.
- Fragility (R3, R4, RQ10): paraphrasing the questions drops dev AUC 0.87 -> 0.72 (real); blind table 0.73-0.85;
  synthetic out-of-sample: FAR advantage holds (14% vs 61%) but misses rise (33%). Expect ~0.75-0.80 AUC on new calls (estimate after R3/R6, not measured).
- Dissent: the free judge is more open-ended for misconduct the fact list does not ask about.

## D2b Policy table variant for Sunday — team decision
- Frozen champion uses table v1 (holdout-run). Options, none holdout-validated:
  - **v3** (+ criteria-derived "decisive fact open" questions): dev review recall 67% -> 100%, miss 15% -> 8%, FAR
    unchanged; synthetic same direction. Designed with knowledge that splitting was missed on the holdout.
  - v2 (+ access validity-unknown -> review): miss 15% -> 8% but FAR 14% -> 36%. Not recommended.
  - paraphrase ensemble (R6): halves label flips under rewording but dev AUC 0.73-0.81 vs 0.87, synthetic 0.81 vs 0.80
    -> not adopted (built: facts `paraphrase_tables`, off by default).

## D3 LLM — accepted
- **Qwen2.5-7B-Instruct-AWQ** on vLLM (fits next to everything, fast). Evidence (RQ6): Qwen3-8B lower (0.74, CIs overlap),
  Qwen2.5-14B facts 0.87 vs 0.84 (no detectable difference; 14B only fits for facts at 2 parallel requests, OOM for the
  full set); check design >> model size.
- Event GPUs >= 24 GB: 14B or larger is a safe upgrade (more robust on dialect text: ORACLE 0.90 vs 0.76, CIs overlap).

## D4 Fusion and uncertainty — accepted
- Weighted fusion over facts (+ light keywords/patterns, abstain_on_empty). Uncertainty escalation kept at default
  (no effect with facts: scores are near-discrete; escalation with the free judge set a FAR floor of 36-41%).
- Rejected: hybrid judge escalation, blind-table review mode as default (FAR 36%), calibrated/conformal fusion (built,
  not evaluated on real results).

## D5 Threshold for Sunday — accepted
- **0.55** with review band 0.15: flag decisions identical for 0.45-0.65 on dev, 3-class labels for 0.55-0.65 (plateau). Facts "open" calls score exactly
  0.50 -> review at 0.55; the slider demo at 0.50 turns them into alarms (explain it as "officer accepts open facts").
