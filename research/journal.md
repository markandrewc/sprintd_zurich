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

## 2026-10-10T01:33 A2 (part) vanilla large-v3-turbo vs Swiss German turbo fine-tunes (ASR metrics)
- vanilla turbo kw-spot recall 76.5% [66.7-87.5] vs nebi turbo int8 71.4% vs jayr23 turbo fp16 70.4% vs gcoli large-v3 MIT 83.7%.
- Vanilla is NOT worse than the turbo fine-tunes on this TTS data (CIs overlap); the large-v3 MIT fine-tune leads.
  Caveat for the team: synthetic voices; real callers would favour fine-tunes (literature). Detection F1 decides.
- vLLM back up 01:32 (0.66 util); experiment queue: checks_ablation -> asr_models:large_v3_gsw -> oracle_views.

## 2026-10-10T01:43 B2/C1 first real baseline + check ablation (Qwen2.5-7B, default ASR, dev 48 calls)
- `callguard experiment experiments/checks_ablation.yaml --split dev` (10 min for all 4 checks on 48 calls; ~10 LLM calls/call,
  31.8 s check compute per call at 6 parallel calls).
- all: CV flag F1 0.67 [0.46, 0.83], FAR 45%, miss 31%; Stufe2 F1 0.43. Removing llm_judge: miss +46 pp (real).
- Diagnosis: G-Eval stuck at 3/5 (middle anchor); 7B judge over-triggers on documentation. -> findings/RQ4.md.
- DECISION: the LLM layer is the bottleneck -> run the LLM sweep (RQ6) BEFORE oracle/new-check experiments, so those run
  with the best model. Killed the 7B queue (oracle_views, new_checks) after asr_models:large_v3_gsw.
- Built `geval_cot` (analysis first, then digit by logprobs; no "middle = undetermined" anchor). Smoke: distributions
  spread out but on 2 calls direction still wrong with 7B (C12 disclosure 0.44, harmless D03 trade 0.73).
- config/llm-sweep.yaml: roles pinned to the cached 7B role decisions (diarization not recomputed per model; only
  the check LLM varies) — checks use LLM entry `judge`. Sweep: Qwen2.5-7B -> Qwen3-8B -> Qwen2.5-14B -> Qwen3-14B.
- condition_on_previous_text=false (turbo int8): kw-spot recall 76.5% vs 71.4%, noisy 73.5% vs 63.3%, CER 25.2 vs 27.6
  -> candidate ASR fix (cheap); confirms the hallucination/loop failure mode.

## 2026-10-10T01:50 F (fusion knobs, N14) on the 7B baseline: re-fusion only, 0 GPU
- experiments/fusion.yaml: abstain_on_empty (N14), uncertainty_from=llm, review band 0.10/0.20, max_uncertainty 0.25/0.45.
  All within noise of base (CV flag F1 0.67-0.70, CIs ~[0.5, 0.83]); N14 raises recall (miss 31->15%) at FAR 45->68%.
- METHOD PROBLEM FOUND: on dev the trivial "flag every call" policy has flag F1 = 0.70 (alarm+review prevalence ~0.54).
  Max-F1 threshold choice therefore drifts to flag-everything and flag F1 cannot rank systems. DECISION: primary metric
  becomes threshold-free ROC AUC of the call score (+ CV operating point at FAR <= 20%), flag-all baseline printed in
  every summary. Asked the harness builder to add it and rescore.
- Conclusion so far: no fusion knob rescues a weak LLM signal; fix the signal first (LLM sweep running).

## 2026-10-10T01:55 C4 facts check (fact sheet + policy table, A1/N6/N7) landed
- Builder smoke on the 24 clean dev calls (7B): alarm D02 D04 D05 D09 D10 C06 C12; review C07 C11 C13 C14 C17; rest no_alert.
  Read against the dev labels this is far better than llm_judge (all 7 alarms are expected alarms; harmless D03/D08/C05/C08
  stay no_alert) — but CAVEAT: the fact questions were worded while looking at dev ASR transcripts (dev only, no
  holdout), so dev numbers for `facts` are in-sample for the prompt wording. The holdout run is the honest test.
- Single-token answers yes/no/unknown (Qwen tokenizer), one forward pass per fact, logprobs -> p(yes/no/unclear).
- DECISION: compute facts + anchored keyword_context (weight 0) for every model in the LLM sweep and compare check
  combinations by re-fusion (llm_models.yaml `<model>__*` variants), so the LLM x check-set grid costs one pass per model.

## 2026-10-10T01:58 A3/RQ2 detection: large-v3 gsw (MIT) vs turbo int8 with the 7B checks
- experiments/asr_models.yaml (large_v3_gsw computed, turbo_gsw_int8 = cached default). Flag AUC 0.66 vs 0.68
  (diff -0.02 [-0.16, +0.11]); alarm AUC 0.78 vs 0.77 (+0.02 [-0.12, +0.15]) -> no detectable difference.
- Interpretation: with the 7B judge the LLM layer, not the ASR, limits detection; the better keyword recall of large-v3
  does not show up. Re-test with the winning LLM. Keep large-v3 MIT as licence-clean option either way.

## 2026-10-10T01:57 A6 decoding knobs on the default turbo int8 (keyword-spot recall, all 60 calls)
| variant | kw recall | clean | noisy | false hits/call | CER |
|---|---|---|---|---|---|
| default (prompt, condition_on_previous_text) | 71.4% | 79.6% | 63.3% | 0.03 | 27.6% |
| condition_on_previous_text=false | 76.5% | 79.6% | 73.5% | 0.03 | 25.2% |
| no initial_prompt | 77.5% | 79.6% | 75.5% | 0.00 | 27.6% |
- Both knobs only help on NOISY audio (+10-12 pp) where the prompt/previous text drives hallucinated loops; CIs overlap
  (n = 10 level-1 dialogues). Direction is consistent with the D02-K2 loop diagnosis. DECISION: candidate ASR settings for
  the champion = no keyword-list prompt + condition_on_previous_text=false (test together, then detection F1).
  Note: the vocabulary prompt was meant to help keywords; on this data it does the opposite.

## 2026-10-10T01:59 independent audit of the evidence code (adversarial reviewer agent)
- Verified correct: all metrics recomputed from rows (21 variants), twin-group bootstrap, McNemar p, AUC, CV threshold
  choice never sees test-fold labels, re-fusion == weight 0, no holdout dialogue in any stored experiment row.
- Findings being fixed (fixer agent): F1 leaderboard ranks FAR-cap violators above compliant variants and review rules
  give a FAR floor no threshold can lower; F2 `eval`/`experiment --split all` and `asr-eval` touch holdout unlogged;
  F3 an experiment started while vLLM is loading can silently reuse the previous model's cached results;
  F4 G-Eval step fallback cached silently; F5 re-fusion provenance; F6 cosmetic.
- HOLDOUT DISCLOSURE: asr-eval runs A1-A3/A6 used all 60 calls, incl. holdout dialogue D07 (6 of 98 keyword spots).
  Nothing was tuned on it, but the ASR numbers above include it. Dev-only recall: turbo int8 70.7%, nocond 75.0%,
  large-v3 83.7% (vs 71.4 / 76.5 / 83.7 reported) -> same conclusions. Future ASR evals: --split dev.
- F3 check for the LLM sweep: every variant's rows[].models is verified by hand after it finishes.

## 2026-10-10T02:01 C4/RQ5 facts vs free judge (re-fusion of the 7B sweep variant, 0 extra GPU)
- facts only: flag AUC 0.84 [0.70, 0.95] vs v1 0.68 (diff +0.16 [+0.05, +0.28] real), FAR 18% vs 86%, 3-class acc 73% vs 38%,
  McNemar 3-class p=0.0009. Adding judge/geval/anchored to facts makes it WORSE at 7B (they add false alarms).
- Weak spot: review recall 33% (Stufe3 C18, C20 -> no_alert). In-sample caveat on prompt wording (see RQ5).
- NEXT: hybrid "facts decides alarm/no_alert, judge undetermined -> review"; review-side fact questions.

## 2026-10-10T02:04 hybrid fusion (facts decides, llm_judge "undetermined" may escalate to review) on 7B results
- fusion/hybrid.py (new plugin). qwen25_7b__hybrid: flag AUC 0.82 vs facts_only 0.84; CV FAR 27% vs 18%; review recall
  unchanged 33%. The 7B judge's "undetermined" does not coincide with the expected-review calls. REJECTED at 7B
  (re-test on the 14B results: free). Qwen3-8B failed to start (KV cache too small next to an ASR sweep) -> re-planned:
  large-model ASR sweeps now (vLLM down), then Qwen2.5-14B (GPU exclusive), Qwen3-8B (fp8 KV), Qwen3-14B.
