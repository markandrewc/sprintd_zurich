# test50: pre-registration (written 2026-10-10 ~14:00, before any test50 result)

**Data.** The teammate's held-out test50 set (sprintd_zurich `data/test50`, commit 954446c, author Paul): 50
dialogues, clean + noisy = 100 calls, 17 alarm / 6 review / 27 no_alert, FHNW STT4SG TTS with 8 dialect voices
(the case data uses one TTS voice). Its README: "never use these texts or this audio to train or tune anything".
Imported as its own dataset `data_test50/v1` (`dataset.yaml: external: true`), runs in `runs/test50/`, split
`external`. **Never pooled** with dev / holdout / synthetic numbers.

**Fixed candidate list** (experiments/test50.yaml): champion (Qwen2.5-7B, table v1), champion_v3, qwen_general,
kev_facts, kev_general, q38q6_facts, q38q6_general (+ facts_only re-fusion). Each runs once with its dev-frozen
configuration and threshold; CV thresholds are fitted within test50 folds by the harness (twin groups together) and
reported next to the fixed-threshold numbers.

**Rules.** No config, question, rule or threshold change is made because of a test50 result. If something is
changed later for another reason, any re-run on test50 is listed here with time and reason (look log).
**Primary read-outs:** flag AUC, fixed-threshold FAR / miss / 3-class accuracy, review recall, per-type (pair /
trap / review / numbers / multi) and clean vs noisy; paired comparisons against the champion over twin groups.

## Look log
| time | what | why |
|---|---|---|
