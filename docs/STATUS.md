# Status board

Update this file whenever a component changes state (and say who/which session). Priorities: P0 = needed
before the research loop, P1 = research-critical, P2 = strengthens results/demo, P3 = stretch goal.
Spec references point into `docs/design/v2_plan.md`.

Last update: 2026-10-10 00:40, laptop session (v2 build starting; stages are pushed as they land).

## Done (on `main`)

| component | notes |
|---|---|
| Core contracts | types, plugins, registry (`module:Class` drop-in), config profiles (`extends`, `--set`, `${ENV:-default}`), cache, pipeline, dataset + dialogue folds |
| ASR | `faster_whisper` (Swiss German turbo int8 default), `hf_whisper` (untested, needs torch), `reference` (oracle) |
| Diarization | `sherpa_onnx` (pyannote seg 3.0 + wespeaker, CPU) + advisor/customer roles (LLM, fallback first speaker) |
| LLM clients | `openai_compat` (vLLM / llama.cpp / Ollama), `llama_cpp` in-process, `fake` (offline) |
| Checks | `keywords` (fuzzy, negation, word timestamps), `patterns` (spoken digits, codes), `llm_judge` (self-consistency), `geval` (G-Eval, logprob-weighted) |
| Fusion | `weighted`: threshold, review band, uncertainty escalation, passages with reasons |
| Sinks | `json_dir`, `outcept_trigger` (deep links `?call=..&t=..`) |
| Eval | 3-class confusion, flag/alarm P/R/F1, false-alarm + miss rate, threshold sweep + suggestion, dialogue-fold CV |
| CLI | plugins, transcribe, run, batch, eval, watch, ui, doctor |
| UI | Inbox (live threshold), Call detail (passages first, snippets, deep link), Keywords & criteria editor, Process a call, Quality |
| First results | CPU chain on 4 calls (plumbing only, 1.5B LLM useless as judge); rule-checks floor on reference scripts: out-of-fold flag F1 0.46 (README "Measured so far") |

## In progress (laptop)

| component | prio | notes |
|---|---|---|
| GPU host setup: `config/gpu-12gb.yaml`, `config/remote.yaml`, remote ASR server, `scripts/remote/*`, `docs/REMOTE_GPU.md`, `callguard doctor` | P0 | agent `remote-gpu`; doctor already in CLI |
| Model research notes `docs/research/*.md` | P0 | translation + fine-tuning done; dialect ASR + synthetic/TTS running |

## To build (v2), in priority order

**Laptop build in progress (started 2026-10-10 ~00:55, ETA ~03:30), in 4 pushed stages:** stage 1 = items 1, 2, 16 + scaffolds/stubs for
everything else; stage 2 = items 3-10; stage 3 = items 11-15; stage 4 = integration + review. The column
`owner` says who builds it. A GPU-host session must NOT build items owned by `laptop` unless the last
push to `main` is more than 90 minutes old (`git log -1 --format=%cr origin/main`): then the laptop build
is presumed dead - set owner to `gpu-host` here, push, and build it yourself.

| # | component | prio | spec | owner |
|---|---|---|---|---|
| 1 | Views (gsw/de/translated/en_speech/ref_*), `translator` plugin kind (`llm_translate`, `hf_mt`, `identity`), multi-view pipeline, check `view` param, `check_view`, language-aware keywords (+ English forms), `faster_whisper task: translate`, provenance | P0 | §1, §5 | laptop |
| 2 | Holdout lock `config/splits.yaml`, `eval --split dev/holdout`, holdout log | P0 | §1c | laptop |
| 3 | Experiment runner `callguard experiment`, `experiments/*.yaml`, dev-fold CV per variant, cost tracking | P0 | §2 | laptop |
| 4 | ASR eval `callguard asr-eval`: WER/CER, pseudo-references, keyword-spot recall, vanilla baselines | P0 | §2 | laptop |
| 5 | Statistics + report: paired bootstrap CIs, McNemar, per-call flip tables, charts, `callguard report`, `callguard leaderboard` | P0 | §9 | laptop |
| 6 | `keyword_context` check (G-Eval on keyword windows) | P1 | §1b | laptop |
| 7 | `semantic_windows` check (embeddings) | P1 | §1b | laptop |
| 8 | Fact sheet + policy table (A1), role-aware LLM checks (A7), twin few-shot (A8) | P1 | §7 | laptop |
| 9 | Calibrated / conformal fusion (A5), learned fusion, `fit-fusion` | P1 | §7, §3 | laptop |
| 10 | Cascade (A2), debate (A6), transcript correction view (A4), audio-LLM check (A3), denoise preprocess (A10) | P2 | §7 | laptop |
| 11 | UI: view tabs + side-by-side passages, evidence timeline, "why not an alarm", Experiments page | P2 | §7 UX | laptop |
| 12 | Synthetic kit: scenarios, LLM script writer, TTS plugins, render, telephone augmentation | P2 | §4 | laptop |
| 13 | Fine-tune kit `finetune/` (data prep with dialogue folds, LoRA training for 12 GB, CT2 conversion) | P2 | §3, research note | laptop |
| 14 | Routing + notify sink, feedback loop + tuning overlay, cross-call patterns + entities, audit log | P3 | §3, §5 | laptop |
| 15 | `docs/OPERATING_CONCEPT.md`, `docs/ARCHITECTURE.md` | P3 | §3 | laptop |
| 16 | Overnight harness: `research/` protocol, questions, queue, templates (written), saved workflow `.claude/workflows/overnight-research.js` | P0 | §8 | laptop |
