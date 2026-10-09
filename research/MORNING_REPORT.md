# Morning report

_Updated after every research round. Last update: 2026-10-10 01:58 (round 1 of the GPU-host session)._

## TL;DR (so far)
- **The LLM layer is the bottleneck, not the ASR.** With Qwen2.5-7B the full system's call score separates
  "needs a human" from harmless calls only weakly: flag AUC 0.68 [0.54, 0.83] (0.50 = chance). Keywords/patterns
  alone are at chance (0.55). Running now: the LLM-size sweep (Qwen3-8B, Qwen2.5-14B, Qwen3-14B) and new checks.
- **Flag F1 is a trap on this data**: flagging every call already gives flag F1 0.70 (54% of dev calls should be
  flagged). We now rank by threshold-free AUC and report F1/recall at a capped false-alarm rate (FAR <= 20%).
- **ASR**: the MIT-licensed `gcoli/whisper-large-v3-swiss-german-mit` finds 84% of the annotated keyword spots vs 71%
  for the default turbo (noisy 80% vs 63%), but with the 7B checks this does not change detection (AUC diff -0.02
  [-0.16, +0.11]). Vanilla Whisper turbo is surprisingly competitive on these TTS voices (77%).
- Recommended config for Sunday: _not yet frozen_ (`config/recommended.yaml` comes at the end).
- Holdout: _not run yet_ (runs once, at the end, on the frozen config).

## What we tried tonight
| queue id | what | result | decision |
|---|---|---|---|
| B1 | bring-up on the 4070 | vLLM 0.10.1.1 (driver 535 can't run CUDA 13), ASR 1.5% realtime | done |
| A1-A3 | ASR keyword-spot recall, 5 models | large-v3 MIT 84%, vanilla turbo 77%, nebi turbo 71%, jayr23 70% | large-v3 MIT = candidate |
| A6a | `condition_on_previous_text=false` | kw recall 77% vs 71% (noisy 74% vs 63%) | adopt (cheap) |
| C1 | check ablation (7B) | only llm_judge lifts AUC above chance; G-Eval stuck at 3/5 | fix LLM layer |
| F | fusion knobs (abstain, uncertainty, band) | no knob beats noise; uncertainty escalation floors FAR | signal first |
| RQ2-det | large-v3 vs turbo, same 7B checks | AUC 0.66 vs 0.68, no difference | re-test with best LLM |

## Answers so far
| RQ | answer | confidence | finding |
|---|---|---|---|
| RQ2 | large-v3 MIT best on keyword recall; detection difference not visible with 7B | medium | findings/RQ2.md |
| RQ4 | LLM judge carries recall; keywords/patterns alone at chance; G-Eval uninformative with 7B | medium | findings/RQ4.md |

## Still open / next steps
LLM sweep (RQ6) -> facts / anchored keyword-context / geval_cot re-fusions per model -> views (English translation)
-> ORACLE ceiling -> threshold policy on the champion -> freeze -> holdout once.

## Demo picks (call ids + timestamps)
_pending_

## How to use what is running
- vLLM: `scripts/remote/swap_llm.sh <hf-id> [util] [max_len]`; stop: `kill $(cat runs/logs/vllm.pid)`.
- Experiments: `uv run callguard experiment experiments/<name>.yaml --split dev`; `callguard leaderboard`; `callguard report`.
