# RQ8: Clean vs noisy audio: how big is the gap, and what closes it?

**Answer in one sentence:** noise costs the default ASR about 16 points of keyword recall (79.6% clean vs 63.3% noisy).
Switching off the prompt and the conditioning, or moving to the large-v3 MIT model, closes most of it (large-v3:
87.0% vs 80.4%). Denoising adds nothing measurable. With large-v3 + facts there is **no noisy penalty left in
detection** (CV flag F1 0.88 noisy vs 0.85 clean), and the remaining clean/noisy disagreements come from the LLM,
not the audio. (confidence: medium. Keyword recall rests on the 10 level-1 dialogues, and the CIs are wide.)

## Setup
- ASR metrics: `callguard asr-eval` (runs/asr_eval/*). Keyword-spot recall = annotated keyword spots (level 1 only,
  46 per version on dev) that the fuzzy matcher still finds in the ASR text. Bootstrap over dialogues, 1000x.
  The 60-call runs include holdout dialogue D07 (6 of 98 spots, disclosed in the journal at 01:59; nothing was tuned
  on it). Dev-only (48-call) runs are preferred below.
- Detection: CV breakdown rows of runs/experiments/{checks_ablation, asr_models, llm_models, champion}, dev 48 calls
  (24 clean + 24 noisy). The breakdown table gives no per-subgroup CIs.
- Correction view: runs/view_eval/a4_qwen3-8b (4 noisy level-1 calls only).

## Result 1: ASR keyword-spot recall, clean vs noisy
| ASR setting | calls | all [95% CI] | clean | noisy | gap | GPU s / audio min |
|---|---|---|---|---|---|---|
| turbo int8, default (prompt + conditioning) | 60 | 71.4% [59.7-86.9] | 79.6% | 63.3% | 16.3 pp | 0.9 |
| turbo int8, condition_on_previous_text = false | 60 | 76.5% [65.5-90.5] | 79.6% | 73.5% | 6.1 pp | 1.4 |
| turbo int8, no initial_prompt | 60 | 77.5% [67.9-91.0] | 79.6% | 75.5% | 4.1 pp | 3.5 (*) |
| turbo int8, no conditioning (dev) | 48 | 75.0% [63.9-87.1] | 78.3% | 71.7% | 6.6 pp | 1.4 |
| turbo int8, no prompt + no conditioning (dev) | 48 | 75.0% [63.7-88.8] | 78.3% | 71.7% | 6.6 pp | 0.9 |
| turbo int8, no conditioning + **denoise** (DPDFNet2) (dev) | 48 | 76.1% [63.0-90.3] | 76.1% | 76.1% | 0 pp | 1.1 + CPU 4.5 s |
| vanilla turbo (no Swiss fine-tune) | 60 | 76.5% [66.7-87.5] | 79.6% | 73.5% | 6.1 pp | 0.8 |
| **gcoli large-v3 MIT, default (dev)** | 48 | **83.7% [77.1-93.9]** | 87.0% | 80.4% | 6.6 pp | 2.4 |
| gcoli large-v3 MIT, no prompt + no conditioning (dev) | 48 | 80.4% [72.1-90.7] | 82.6% | 78.3% | 4.3 pp | 2.4 |
| Flix large-v3 (Apache-2.0), no prompt + no conditioning (dev) | 48 | 76.1% [65.6-87.5] | 78.3% | 73.9% | 4.4 pp | 2.4 |

(*) RTF 0.059 in that run, probably GPU contention. The other turbo runs measured 0.013-0.024.
Not measured: beam size 5 (stopped at 30/60 calls to free the GPU), vanilla large-v3.

What causes the gap: with the default settings, the initial_prompt ("... Kreditkarte, Rechnung, Teilzahlungen") leaked
into Stufe1_D02-K2 (noisy) as a 25-second loop, giving 36 false K09 hits and losing the real trade keywords. Both
knobs help only on noisy audio (+10-12 pp). large-v3 does not loop, so the knobs make no difference there.

## Result 2: LLM correction view `de_fused` (ORACLE-free; 4 noisy level-1 calls, corrector Qwen3-8B)
| view | kw spots found | kw recall [95% CI] |
|---|---|---|
| de (turbo default) | 9/19 | 47.4% [21.7-80.0] |
| de_vanilla (vanilla turbo) | 13/19 | 68.4% [50.0-80.0] |
| de_large (large-v3 MIT) | 14/19 | 73.7% [61.5-89.5] |
| de_fused (LLM fuses the 3 hypotheses) | 15/19 | 79.0% [61.5-92.9] |

It repaired the D02-K2 prompt loop, but it gains only +1 spot over large-v3 alone, at the cost of 3 ASR passes plus an
LLM pass per call. Its runtime was not measured. Not used.

## Result 3: detection, clean vs noisy (CV flag F1 / FAR / miss, 24 calls each)
| system | clean | noisy | dialogues whose clean and noisy versions get different labels (CV) |
|---|---|---|---|
| v1, turbo, 7B (checks_ablation `all`) | 0.69 / 36% / 31% | 0.64 / 55% / 31% | 7 / 24 |
| v1, large-v3, 7B (asr_models) | 0.71 / 82% / 8% | 0.65 / 91% / 15% | 9 / 24 |
| facts, turbo, 7B | 0.80 / 18% / 23% | 0.75 / 18% / 31% | 4 / 24 (fixed threshold: 7 / 24) |
| facts, turbo, 14B | 0.80 / 18% / 23% | 0.83 / 9% / 23% | 5 / 24 |
| **champion: facts, large-v3, 7B** | 0.85 / 18% / 15% | **0.88 / 9% / 15%** | **2 / 24** (C12, C14; the clean version is the wrong one in both) |

The last column is counted from the stored CV rows (no CI). The fixed-threshold count of 7/24 for facts on turbo
matches ideas_round2 §0.4.

## Calls that flip (facts 7B: turbo -> large-v3, CV rows)
12 calls change label. For the flag decision 4 get better and 0 get worse:
- **D05-K2** (noisy TAN call): turbo garbled "Bestätigungscode" and the call went to no_alert; large-v3 gives alarm.
- **C06-K4** (noisy trade alarm): no_alert -> alarm. With D05-K2, these are the two calls that RQ5 counted as
  "noisy-ASR losses".
- C14-K4 (harmless): alarm -> no_alert.
- C18-K3 (open case): no_alert -> review.

The other label changes stay flagged either way. C11 x2 and C14-K3 (harmless) step down from alarm to review.
C07-K3 goes review -> alarm. C12-K3, C13 x2 and C18-K4 go alarm -> review.

## Recommendation
Use large-v3 MIT (default decoding is fine). On turbo, always switch off the keyword prompt and
condition_on_previous_text. Leave denoising and the correction view off. Claim for the jury: "noisy and clean
recordings get the same decision in 22 of 24 dev dialogues, and the noisy versions score no worse".

## Strongest counter-argument
The case noise is synthetic, added to TTS speech. Real phone lines (codec artefacts, crosstalk, real dialect speakers)
may hurt more, and denoising could matter there. Keyword recall rests on 10 dialogues: the 6.6 pp gap that remains on
large-v3 has a CI far wider than the gap itself. The "no noisy penalty" claim is a CV breakdown without its own CI.

## What would change our mind
Real call-centre recordings where noisy keyword recall falls below ~70% on large-v3. Or a denoise/beam-5 run that
improves noisy detection with a paired CI that excludes 0.
