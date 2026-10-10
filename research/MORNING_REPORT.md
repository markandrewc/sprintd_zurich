# Morning report

_Updated after every research round. Last update: 2026-10-10 03:15 (round 3 of the GPU-host session)._

## TL;DR (so far)
- **Biggest win of the night: fact questions + policy table (`facts`) instead of a free LLM judge.** Same 7B model,
  same transcripts: flag AUC 0.84 vs 0.68 (diff +0.16 [+0.05, +0.28], real), false-alarm rate 18% vs 86%,
  3-class accuracy 73% vs 38% (McNemar p = 0.0009). Every alarm names the facts and the rule (officer-editable
  `config/policy_table.yaml`). Weak spot: open Stufe3 cases (review recall 33-50%).
- **Honesty check (blind table):** a table written from the criteria only, without reading any call, scores AUC 0.77
  on the 14B (tuned table 0.87). So part of the gain is dev-fitted wording, but a blind version still clearly beats
  the free judge. Expect ~0.77-0.87 on unseen calls; the single holdout run will tell.
- **Model size matters less than check design**: Qwen2.5-7B 0.84, Qwen3-8B 0.74, Qwen2.5-14B 0.87 (facts, AUC);
  no detectable difference between 7B and 14B at n = 24 dialogues. 14B fits 12 GB only for the fact probes.
- **Flag F1 is a trap on this data** (flag-all = 0.70): we rank by AUC + the CV operating point at FAR <= 20%.
- **ASR**: `gcoli/whisper-large-v3-swiss-german-mit` (MIT) has the best keyword-spot recall (84% vs 71% default
  turbo, dev); default turbo improves to 75% without the keyword prompt and with `condition_on_previous_text: false`
  (the prompt leaked into a transcript as a 25 s loop). Denoising: no effect. LLM transcript repair of 3 ASR
  hypotheses: +1 keyword spot over large-v3 alone on 4 calls -> not worth it.
- Recommended config for Sunday: _not yet frozen_ (`config/recommended.yaml` at the end). Holdout: _not run yet_.

## What we tried tonight
| queue id | what | result | decision |
|---|---|---|---|
| B1 | bring-up on the 4070 | vLLM 0.10.1.1 (driver 535 can't run CUDA 13), ASR 1-2.5 GPU-s per audio min | done |
| A1-A3 | ASR keyword-spot recall, 8 models/settings | large-v3 MIT 84%, Flix 76%, vanilla turbo ~76%, gcoli turbo 75%, default turbo 71% | large-v3 MIT |
| A6 | decoding knobs | no prompt / no conditioning: turbo noisy +10-12 pp; large-v3 unaffected | turbo only |
| A7 | denoise (DPDFNet2, CPU) | 76.1% vs 75.0% kw recall | off |
| V4 | LLM repair of 3 ASR hypotheses | 15/19 vs large-v3 14/19 spots (4 calls) | option only |
| C1 | check ablation (7B) | only the free judge lifts AUC above chance; G-Eval stuck at 3/5 | -> facts |
| C4 | facts + policy table | AUC 0.84 vs 0.68, FAR 18% vs 86% | **core check** |
| R4 | blind policy table | 0.77 (14B), 0.67 (Qwen3-8B) vs tuned 0.87 / 0.74 | overfit sized |
| L1 | LLM sweep | 7B 0.84, Qwen3-8B 0.74, 14B 0.87 (facts) | 7B fast / 14B batch |
| F | fusion knobs, hybrid, geval_cot | none beats noise; escalation sets a FAR floor | simple fusion |
| audit | independent review of the evidence code | stats correct; 6 fixes (FAR-cap ranking, holdout logging, LLM identity) | fixed |

## Answers so far
| RQ | answer | confidence | finding |
|---|---|---|---|
| RQ2 | large-v3 MIT best keyword recall; detection gain not visible with 7B checks | medium | findings/RQ2.md |
| RQ4 | free judge carries recall but most false alarms; keywords alone at chance | medium | findings/RQ4.md |
| RQ5 | facts + policy table >> free judge >> G-Eval (7B) | medium-high | findings/RQ5.md |
| RQ6 | check design >> model size (within 12 GB) | medium | findings/RQ6.md |

## Still open / next steps
facts on large-v3 transcripts + ORACLE ceiling (running, 14B) -> same with 7B -> English view -> synthetic
stress test of the fact wording -> freeze -> single holdout run.

## Demo picks (call ids + timestamps)
_pending_

## How to use what is running
- vLLM: `scripts/remote/swap_llm.sh <hf-id> [util] [max_len]` (logs `runs/logs/vllm_<model>.log`); stop: `kill $(cat runs/logs/vllm.pid)`.
- Experiments: `uv run callguard experiment experiments/<name>.yaml --split dev`; `callguard leaderboard`; `callguard report`.
- UI: `uv run callguard ui -c <profile>`; experiment variants are selectable as a source in the sidebar.
