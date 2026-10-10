# RQ6: What matters more — LLM size or the check/prompt design?

**Answer in one sentence:** the check design matters far more than the model size that fits a 12 GB GPU: switching
the free judge to fact questions + policy table moves flag AUC by +0.16 (real), while switching the model
(Qwen2.5-7B -> Qwen3-8B -> Qwen2.5-14B) moves it by -0.10 to +0.03 (no detectable gain). (confidence: medium)

## Setup
- experiments/llm_models.yaml, profile `llm-sweep` (default turbo ASR, speaker roles pinned to the cached 7B role
  decisions so only the check LLM varies), dev split 48 calls / 18 units. Each model computes every check once;
  check combinations are re-fusions. Served model ids verified per row (audit F3).
- Qwen2.5-14B-AWQ only fits a 12 GB card for the cheap `facts` probes (util 0.90, 6k context, 2 parallel requests;
  the full check set runs out of memory). Qwen3-14B-AWQ does not start at all next to the desktop (~0.5 GB).

## Result (flag AUC [95% CI])
| check set \ model | Qwen2.5-7B-AWQ | Qwen3-8B-AWQ | Qwen2.5-14B-AWQ |
|---|---|---|---|
| v1: keywords + patterns + free judge + G-Eval | 0.68 [0.53, 0.84] | 0.64 [0.44, 0.82] | does not fit |
| facts (tuned table) | **0.84** [0.70, 0.95] | 0.74 [0.59, 0.88] | **0.87** [0.76, 0.96] |
| facts (blind table, R4) | 0.73 [0.57, 0.88] | 0.67 [0.53, 0.82] | 0.77 [0.62, 0.91] |
| judge + facts | 0.76 | 0.76 | - |
| G-Eval with analysis first (geval_cot) | 0.65 | 0.67 | - |

Cost: 7B all checks 10 min / 48 calls (6 parallel calls, journal 01:43); Qwen3-8B 13 min; 14B facts only 20 min (2 parallel) = 25 s/call.

## Recommendation
Run the check design that wins (facts) on the model the hardware serves comfortably: Qwen2.5-7B-AWQ on the 12 GB card
(fast, all checks fit next to Whisper); Qwen2.5-14B-AWQ for batch scoring when the GPU is free (ASR first, then LLM),
or on bigger event GPUs. Do not expect a big jump from a bigger model.

## Strongest counter-argument
The fact wording was developed against 7B answers, which favours the 7B in this table (Qwen3-8B may be penalised by
wording it was not tuned on). 30B+ models (event GPUs) were not testable here. With n = 24 dialogues a +0.05 AUC
model effect is undetectable.
