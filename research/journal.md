# Research journal (append-only)

Format: `## <ISO time> <queue-id> <title>`, then what was done, command, result in one line, decision,
problems. Autonomous decisions are logged here too.

## 2026-10-10T00:45 setup Harness created (laptop session)
Repo pushed to github.com/be-lang/sprintd. v1 pipeline on main; v2 build running on the laptop and
pushing stages as they land (see docs/STATUS.md). First CPU-only numbers in README "Measured so far"
(plumbing only). Next: the GPU host session starts with START_HERE.md, step 1 (bring-up).

## 2026-10-10T01:15 B1 Bring-up started (GPU-host session)
- Host: RTX 4070 12 GB, 30 GB RAM, 16 cores, Debian 12, driver 535 / CUDA 12.2. No uv on host -> installed uv 0.13.
- docs/REMOTE_GPU.md and scripts/remote/* do not exist (laptop session never pushed them) -> inline setup per START_HERE Step 1.
- Case data cloned; `uv sync` (asr, diarize, ui, dev) OK; models: local set (turbo gsw int8 + diar) done, gpu set (gcoli large-v3 MIT CT2) downloading; vLLM installing into .venv-vllm.
- DECISION: build the v2 items by hand with parallel background subagents (views | harness+stats+report | asr-eval)
  instead of the saved v2-build workflow: the workflow spawns ~18 agents across 4 serial stages + review and
  would hold the tree for hours; the research loop must start by ~03:00. Lower-priority items (UI polish,
  routing, synth audio, finetune kit) get built only when the core research questions are running.

## 2026-10-10T01:15 B1 Bring-up: findings + autonomous decisions
- vLLM latest (0.31, torch cu130) does NOT run on driver 535 (CUDA 12.2) -> pinned **vLLM 0.10.1.1 (torch 2.7.1 cu126)**
  + transformers 4.55.4 (4.56+ breaks Qwen2Tokenizer in this vLLM). User decided not to update the driver tonight.
- CTranslate2 CUDA libs (cuBLAS 12 + cuDNN 9) installed with `uv pip install --target .cuda-libs` (outside .venv,
  because `uv sync` would remove them); `source scripts/remote/cuda_env.sh` sets LD_LIBRARY_PATH.
- Machine was set to GNOME auto-suspend after 20 min idle -> set to 'nothing' + systemd-inhibit (would have killed the night).
- Default ASR (Swiss German turbo int8_float16, beam 1, VAD, prompt) on the 4070: **all 60 calls (4h40 audio) in ~3 min**,
  ~1.5% of realtime (2-10 s per call). ASR is cheap -> we can afford to compare many ASR models; the LLM is the cost.
- vLLM Qwen2.5-7B-AWQ at 0.60 util: KV cache only 1.42 GiB (26.6k tokens). Whisper large-v3 fp16 next to it -> CUDA OOM.
  DECISION: ASR model sweeps run with the GPU to themselves (vLLM down), then vLLM comes back at 0.66 util.
- Previous session's builder agents were stopped by a session restart; new builder agents continue from their
  partial edits (views | experiments+stats+report | asr-eval) + a model-research agent (docs/research/dialect_asr.md).
- Lesson: `pgrep -f <pattern> | xargs kill` killed my own shell (CLAUDE.md rule 7) - kill by PID only.

## 2026-10-10T01:35 A1 asr-eval of the default ASR (turbo gsw int8_float16, beam 1, VAD, initial_prompt)
- `callguard asr-eval -c gpu-12gb --cached-only --tag turbo-gsw-int8` (all 60 calls).
- Keyword-spot recall **71.4% [59.7-86.9]** (70/98 spots; clean 79.6%, noisy 63.3%), false keyword hits 0.03/call,
  WER vs dialect script 64% (inflated by dialect spelling vs Standard German output, not comparable across output styles), RTF 0.015.
- Spots exist only in level-1 calls (49 spots x 2 versions, 10 dialogues) -> keyword-recall CIs are wide.
- Weakest: K10 access words (PIN/TAN/Passwort/Bestätigungscode) 9/18, K05 3/8, K04 4/8. "PIN" -> "BI-Inwand".
- FAILURE PATTERN: Stufe1_D02-K2 (noisy) loops "Kreditkarte, Rechnung, ..." for 25 s = **the initial_prompt leaking into the
  transcript** (prompt lists "Kreditkarte, Rechnung, Teilzahlungen") -> 36 false K09 hits + lost the real trade keywords.
  NEW HYPOTHESIS A6a: initial_prompt hurts on noisy audio (hallucinated keywords) -> test no-prompt / condition_on_previous_text=false.

## 2026-10-10T01:40 research note docs/research/dialect_asr.md landed (model-research agent)
- No public dialect-OUTPUT Swiss German ASR exists (all fine-tunes write Standard German) -> view `gsw` from audio is
  not available off the shelf. DECISION: RQ3 answered by ORACLE only (ref_gsw vs ref_de) + optional omniASR CTC trial later.
- jayr23 turbo CT2 ships without tokenizer.json/preprocessor_config.json (would decode with 80 mels + tiny tokenizer).
  Copied both from vanilla turbo (vocabulary.json identical in content) -> models/asr/turbo-gsw-ct2-fp16 usable.
- New ASR candidates being fetched: malaxy/flix-swissgerman-ct2 (Apache-2.0), OSTswiss turbo CT2, gcoli turbo MIT.
- Apertus not loadable in vLLM 0.10.1.1; LLM sweep candidates: Qwen3-8B-AWQ, Qwen2.5-7B-AWQ, Qwen3-4B-2507, Qwen2.5-14B-AWQ (alone on GPU), Mistral-Nemo AWQ.
- Licence note: nebi/jayr23 are derived from Flurin17 (CC BY-NC 4.0) -> a bank deployment needs the MIT (gcoli) or Apache (flix) models.

## 2026-10-10T01:30 ideas round 1 (independent ideator agent) -> research/ideas_round1.md, queue N1-N15
- Top 5 by value/GPU-hour: N14 fusion fix (keywords' "nothing found" counts as disagreement -> clear Stufe2 LLM alarms
  become review; replay on cache), N1 twin-aware evaluation, N6/N7 atomic fact questions scored by logprob,
  N4 anchor-wise G-Eval with whole-call context, N3 verified verbatim quotes.
- DECISION (N1): Stufe2/Stufe1 twin pairs are ~95% identical text -> folds and holdout must contain whole twin groups,
  bootstrap resamples twin groups. Asked the harness builder to regenerate config/splits.yaml before first use.
- HOLDOUT CAVEAT (logged honestly): the ideator read the *script* (not the expected label) of Stufe2_C02 before the
  split existed; the split may change with twin grouping. Any config that uses N4/N8 carries that caveat.
- Views landed (STATUS 1). Prompts now describe the transcript language per view (de wording byte-identical -> caches valid).

## 2026-10-10T01:26 A3 (part) gcoli whisper-large-v3 Swiss German (MIT, fp16, beam 1) vs default turbo int8
- kw-spot recall **83.7% [77.5-93.2]** vs 71.4% [59.7-86.9]; noisy 79.6% vs 63.3%; CER 25.5% vs 27.6%; false hits 0.00 vs 0.03/call;
  RTF 0.041 vs 0.015 (still ~2.5 GPU-s per audio minute). Licence MIT vs CC BY-NC origin.
- Early signal: large-v3 MIT is better on exactly what the checks need (keywords on noisy audio) AND licence-clean.
  Paired test + detection F1 pending (needs LLM). Candidate for the champion ASR.
