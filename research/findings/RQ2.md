# RQ2: Do Swiss German Whisper fine-tunes beat vanilla Whisper, and which one?

**Answer in one sentence (provisional, ASR metrics only):** the MIT-licensed `gcoli/whisper-large-v3-swiss-german-mit`
finds clearly more of the annotated keyword spots than the default turbo int8 (83.7% vs 71.4%, noisy 79.6% vs 63.3%)
at ~2.7x the (still tiny) ASR cost; in detection the gain shows only with the facts check (see Detection). (confidence: medium)

## Setup
- `callguard asr-eval -c gpu-12gb --cached-only` per model, all 60 calls. These include holdout dialogue D07 (6 of 98
  spots; disclosed in the journal at 01:59, nothing tuned on it). Dev-only: turbo int8 70.7%, large-v3 83.7%.
- Keyword-spot recall = annotated `Keywordstellen` (49 spots x clean/noisy, **level 1 only, 10 dialogues**) that the
  keyword matcher (fuzzy 90) still finds in the ASR text. WER/CER are against the *dialect* script, so they are
  inflated for every Standard German output model and only comparable between models of the same output style.

## Result (ASR)
| model | licence | kw-spot recall [95% CI] | clean | noisy | CER vs gsw | false kw hits/call | GPU s / audio min |
|---|---|---|---|---|---|---|---|
| turbo gsw int8 (nebi, default) | CC BY-NC origin (Flurin17) | 71.4% [59.7-86.9] | 79.6% | 63.3% | 27.6% | 0.03 | 0.9 |
| turbo gsw fp16 (jayr23) | CC BY-NC origin (Flurin17) | 70.4% [59.8-81.2] | 73.5% | 67.3% | 28.3% | 0.00 | 1.0 |
| vanilla large-v3-turbo fp16 (no Swiss fine-tune) | MIT | 76.5% [66.7-87.5] | 79.6% | 73.5% | 23.4% | 0.00 | 0.8 |
| large-v3 gsw fp16 (gcoli, MIT) | MIT | **83.7% [77.5-93.2]** | 87.8% | 79.6% | 25.5% | 0.00 | 2.5 |

Full table (dev split, 48 calls; journal 02:30): gcoli large-v3 MIT 83.7% (no prompt/no cond 80.4%), Flix large-v3
(Apache-2.0) 76.1%, vanilla turbo ~76% (60-call run), gcoli turbo MIT 75.0%, nebi turbo int8 with no prompt/no cond
75.0%, OST turbo 73.9%, nebi turbo int8 default 70.7%. Vanilla large-v3 and beam 5 were skipped (GPU time).

Surprise: **vanilla turbo is not worse** than the Swiss German turbo fine-tunes on these (synthetic-voice) calls: higher
keyword-spot recall (76.5% vs 71.4%, CIs overlap) and lower CER vs the script. Likely because the case audio is TTS
(clean prosody, standardised dialect); real phone calls with real dialect speakers are where the published fine-tune
gains come from (docs/research/dialect_asr.md). Don't over-generalise the vanilla result to production.

## Failure pattern found
Stufe1_D02-K2 (noisy), default model: the `initial_prompt` ("... Kreditkarte, Rechnung, Teilzahlungen") leaks into the
transcript as a 25-second loop -> 36 false keyword hits and the real trade keywords lost. Prompt biasing can hurt.

## Detection
experiments/asr_models.yaml (v1 checks, 7B): flag AUC large-v3 0.66 vs turbo 0.68, diff -0.02 [-0.16, +0.11], no
detectable difference. With 7B `facts` (llm_models): turbo 0.84 -> large-v3 0.89 (no paired test, CIs overlap).

## Strongest counter-argument
Keyword-spot recall rests on 10 level-1 dialogues; level-2/3 calls (no keywords, context decides) may be insensitive to
these ASR differences because the LLM reads through errors. Only the detection experiment settles it.
