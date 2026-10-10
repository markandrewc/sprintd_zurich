# RQ3: Dialect-text output or Standard German output?

**Answer in one sentence:** transcribe straight to Standard German. No public ASR writes Swiss German dialect, so a
dialect view would need our own fine-tune. Even *perfect* dialect text (ORACLE reference scripts) does not help the
7B LLM we can run (flag AUC 0.76 vs 0.89 on large-v3 Standard German ASR) and helps the 14B only slightly
(0.90 vs 0.85). (confidence: medium. CIs overlap pairwise, but the test favours dialect: it gets perfect words, ASR
does not.)

## Setup
- experiments/llm_models.yaml (summary commit `1fd19e7`, dirty). Same `facts` check, same fact questions. Only the
  input text varies. Dev split: 24 dialogues / 48 calls / 18 units. Holdout untouched.
- Dialect input = ORACLE `ref_gsw` (the case's dialect reference scripts, no ASR). This is an experiment, never a
  submission path. Standard German input = Swiss German Whisper output (large-v3 MIT, or turbo int8).
- Why there is no "dialect ASR" row: the model survey (docs/research/dialect_asr.md) found that **no public model
  outputs Swiss German dialect spelling**. Every Swiss German Whisper fine-tune writes Standard German, and Whisper
  "exclusively produces outputs in standardized languages" (STT4SG-350 paper, quoted in
  docs/research/whisper_finetune_12gb.md). The only untested candidate is the CTC model omniASR (no language model,
  so it might write what it hears). So the ASR side of RQ3 (keyword recall with dialect vs Standard German keyword
  forms) is **not measured**.

## Result (journal 04:04 + llm_models summary)
| input text | Qwen2.5-7B flag AUC [95% CI] | 7B CV FAR / miss | Qwen2.5-14B flag AUC [95% CI] | 14B CV FAR / miss |
|---|---|---|---|---|
| dialect reference script (ORACLE, perfect words) | 0.76 [0.56, 0.92] | 18% / 46% | **0.90 [0.79, 1.00]** | 0% / 23% |
| Standard German ASR, large-v3 MIT | **0.89 [0.77, 0.99]** | 14% / 15% | 0.85 [0.73, 0.96] | 18% / 23% |
| Standard German ASR, turbo int8 | 0.84 [0.70, 0.95] | 18% / 27% | 0.87 [0.76, 0.96] | 14% / 23% |

Control for wording bias. The tuned fact questions were written while reading dev *Standard German ASR* transcripts,
which could favour Standard German. The **blind** policy table (never saw a transcript) shows the same direction with
14B: dialect ORACLE 0.78 [0.64, 0.92] vs large-v3 Standard German 0.85 [0.72, 0.96].

Paired differences (ORACLE vs ASR) were not computed. Marginal CIs overlap, so there is **no detectable difference at
n = 24**. The claim is "dialect is not better", not "dialect is worse".

## Calls that flip (Standard German large-v3 -> dialect ORACLE, CV rows)
**7B:** 16 calls change label. For the flag decision 1 gets better and 10 get worse. The 7B loses clear alarms on
dialect text:

| call | expected | large-v3 de | ORACLE gsw | what the 7B did with the dialect |
|---|---|---|---|---|
| Stufe1_D05-K1/K2 | alarm | alarm | no_alert | TAN read out as "sibe, drü, eins, nüün, vier, zwei": "code read out" not recognised (score 0.13) |
| Stufe1_D09-K1/K2 | alarm | alarm | no_alert | "bitte nöd protokolliere, dass ich die zwanzigtuusig zruggzahle muess": no fact fires |
| Stufe1_D08-K1/K2 | no_alert | no_alert | alarm | "vierzehntuusigzweihundert Franke" misread as third-party data (it read 1420 Fr.) |
| Stufe2_C13-K3/K4 | alarm | review | no_alert | documentation alarm lost |
| Stufe3_C18-K3/K4 | review | review | no_alert | open case lost |

**14B:** 13 calls change label. For the flag decision 6 get better and 2 get worse. The 14B reads the same D05 passage
correctly ("Der Kunde liest den Bestätigungscode 'sibe, drü, eins, nüün, vier, zwei' aus", rule access.alarm_1) and
fixes the C11/C14 harmless-twin reviews. It loses C13 (alarm -> no_alert) on both versions.

## Recommendation
Keep Standard German output from the Swiss German Whisper model (large-v3 MIT). It is available off the shelf, the
7B model that fits next to Whisper on 12 GB reads it best, and it is what the keyword list and the fact questions are
written in. Do not spend weekend time training a dialect-output ASR.

## Strongest counter-argument
With a 14B+ LLM, dialect text scores highest of all (0.90, FAR 0%). A future dialect ASR plus a bigger LLM might beat
Standard German, because translation-like ASR loses nuance such as hedges and particles. Our dialect text is the
*script* the TTS read from, which is cleaner than any real dialect ASR would be, so the ORACLE row is an upper bound
that no real dialect pipeline would reach.

## What would change our mind
A dialect-output ASR (own LoRA or omniASR CTC) whose transcripts, with the LLM we can afford, beat large-v3 Standard
German with a paired CI that excludes 0. Or event GPUs that make 14B+ the default and show the dialect advantage on
more than 24 dialogues.
