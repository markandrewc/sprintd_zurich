# Slide numbers (copy these, each with its source)

All numbers are on the **dev split** (48 calls / 24 dialogues, cross-validated threshold) unless marked otherwise.
Brackets are 95% bootstrap CIs over 18 twin-group units.

| claim for the slide | number | source |
|---|---|---|
| Detection, recommended system | flag AUC **0.87** [0.72, 0.99]; false alarms **14%**; missed **15%**; 3-class accuracy **79%** | runs/experiments/champion/summary.md |
| Same task, v1 design (keywords + free LLM judge + G-Eval) | AUC 0.68; false alarms 45-86% (not reproducible run to run) | checks_ablation, llm_models summaries |
| Check design vs model size | fact questions vs free judge **+0.16 AUC** (real); 7B ↔ 8B ↔ 14B: no detectable difference | findings/RQ5.md, RQ6.md |
| Harmless keyword calls (e.g. D03) | false-alarm rate 86% → 18% with fact questions; D03 → "Kein Alarm" with the reason | findings/RQ7.md |
| ASR | MIT large-v3 Swiss German finds **84%** of annotated keyword spots (default turbo 71%); perfect transcripts add only ~0.03 AUC | findings/RQ2.md, journal 03:59 |
| Robustness to recording conditions | re-recorded audio: AUC 0.83, false alarms unchanged (14%) | experiments/perturbed |
| Unseen held-out calls (12 calls, sanity check) | **0 false alarms**, alarm F1 0.67, 3-class 67%; v1 sent all 12 to review | runs/holdout_log.jsonl, journal 04:12 |
| Honest expectation on new calls | ~0.75-0.80 AUC (wording tuned on dev; paraphrased questions 0.72) | MORNING_REPORT caveats |
| Cost | ASR 1-2.5 GPU-s per audio minute; fact checks ~4.5 s per call; ~2,000 calls/day on one 12 GB GPU | docs/OPERATING_CONCEPT.md |
| Traceability | every alarm names the facts (with probabilities), the policy rule and the audio passage; officer can edit the rule table and answer open facts in the UI (audited) | config/policy_table.yaml, research/DEMO.md |
| Self-hosted | Whisper (MIT) + Qwen2.5-7B (Apache-2.0) on one RTX 4070; no cloud call anywhere | config/recommended.yaml |

Do **not** put on a slide: flag F1 alone (flagging everything already scores 0.70), holdout numbers as "test results"
(n = 6 dialogues, 3 looks), or any 14B/7B difference as a win.
