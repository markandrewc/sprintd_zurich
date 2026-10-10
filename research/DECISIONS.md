# Decision records

One record per decision. Status: proposed | accepted | superseded. Evidence links point to
`research/findings/`. Keep dissent: if a teammate disagrees, write their argument down.
Last update: 2026-10-10 02:20 (GPU-host overnight session).

## D0 How we measure (method)
- Status: accepted (02:00)
- Context: 30 dialogues; dev = 24 dialogues (48 calls), holdout = 6 dialogues, locked. Stufe2 twin pairs share a fold.
- Decision: primary = threshold-free **flag AUC** (does the score rank "needs a human" above harmless?) plus the
  CV operating point at **FAR <= 20%**; flag F1 only as a secondary number, because flagging every call already
  scores flag F1 0.70 on dev. Paired bootstrap over twin groups (18 units), McNemar, flip tables.
- Consequence: a fusion knob that only moves calls into review cannot look good by "flagging everything".
- Dissent / caveat: AUC ranks the score, not the final label (review rules can flag below the threshold); the
  leaderboard therefore ranks FAR-cap-compliant variants first (audit F1).

## D1 ASR model and transcript view
- Status: proposed — `gcoli/whisper-large-v3-swiss-german-mit` (MIT, fp16, beam 1), view `de`.
- Evidence: findings/RQ2.md. Keyword-spot recall (dev) 83.7% vs 70.7% default turbo int8 (noisy 80% vs 63%);
  licence MIT vs CC BY-NC origin of the turbo fine-tunes; cost 2.4 vs 0.9 GPU-s per audio minute (both negligible
  next to the LLM). Detection difference not visible with the 7B checks (AUC 0.66 vs 0.68) -> re-check with the
  final LLM.
- If we stay on turbo: drop the keyword-list `initial_prompt` and set `condition_on_previous_text: false`
  (noisy keyword recall +10-12 pp; the prompt leaked into a transcript as a 25 s loop).
- Dissent: vanilla Whisper turbo is competitive on these TTS voices (77%); real callers would favour fine-tunes.

## D2 Check set
- Status: proposed — **`facts`** (atomic yes/no/unknown fact questions + officer-editable `config/policy_table.yaml`)
  as the decision core; keywords + patterns stay for traceability and the officer's keyword list (shown, low weight).
- Evidence: findings/RQ5.md (7B: flag AUC 0.84 vs 0.68 free judge, real; FAR 18% vs 86%), findings/RQ4.md.
- Open: blind-table control (R4) to size the wording-overfit; review side (Stufe3) is facts' weak spot.
- Dissent: the free judge is more open-ended for misconduct phrased in ways the fact list does not ask about.

## D3 LLM
- Status: proposed (Qwen2.5-7B-Instruct-AWQ until the sweep answers RQ6: Qwen2.5-14B / Qwen3-8B / Qwen3-14B).
- Note: on 12 GB a 14B AWQ only fits with Whisper unloaded -> batch processing in stages (ASR all calls, then LLM).

## D4 Fusion and uncertainty policy
- Status: proposed — weighted fusion over the core check; uncertainty escalation off or LLM-only (escalation sets a
  FAR floor no threshold can lower: audit F1); hybrid "judge undetermined -> review" rejected at 7B.
- Evidence: runs/experiments/fusion, llm_models `*__hybrid`.

## D5 Threshold for Sunday
- Status: proposed (CV-chosen on dev folds at FAR <= 20%; facts scores are nearly discrete, so the label is stable
  over a wide threshold range 0.25-0.80 -> pick the middle of the plateau, not the CV optimum; one holdout check).
