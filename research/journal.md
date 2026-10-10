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

## 2026-10-10T02:10 ideas round 2 (independent ideator, research/ideas_round2.md, queue R1-R8)
- From stored 7B fact probabilities (0 GPU): all 4 facts false alarms = harmless twins C11, C14; C09 alarm missed
  ("8-3-6-1-7-4" read out, model says no code read); 4 of 7 clean/noisy disagreements have the CLEAN version wrong
  (answers near p=0.5, not ASR noise); review recall 33% partly a CV artefact (score nearly discrete; CV picked 0.20).
- Rule fixes simulated (scripts/research/sim_rules.py): misses 7->3/26, FAR unchanged 4/22, review recall 50->67% —
  but fitted on these errors -> hypothesis only.
- DECISION: run R4 first = BLIND policy table written by an agent that sees only criteria.yaml + case README (no
  transcripts, not the tuned table) -> honest estimate of how much of the facts gain is wording overfit.

## 2026-10-10T02:13 A6 on large-v3 gsw (dev split, 48 calls): no prompt + condition_on_previous_text=false
- kw-spot recall 80.4% vs 83.7% (prompted, conditioned), CER 23.4% vs 25.8%. Within noise; the knobs fix the turbo's
  hallucination loops but large-v3 has none. DECISION: keep the knobs only for turbo; large-v3 either way.
- R4 blind policy table written (config/policy_table_blind.yaml; agent saw criteria.yaml + README + facts.py code only;
  it glimpsed one docstring example rule that restates the access criteria). Added as `facts_blind` (weight 0) to the
  llm-sweep profile so the 14B/Qwen3 passes compute it.

## 2026-10-10T02:30 A3 complete: ASR model table (dev split, 48 calls, keyword-spot recall + CER vs dialect script)
| model (settings) | licence | kw recall | clean | noisy | CER | GPU s / audio min |
|---|---|---|---|---|---|---|
| gcoli large-v3 gsw (prompt, cond) | MIT | **83.7%** | 87.0% | 80.4% | 25.8% | 2.4 |
| gcoli large-v3 gsw (no prompt, no cond) | MIT | 80.4% | 82.6% | 78.3% | 23.4% | 2.4 |
| Flix large-v3 (no prompt, no cond) | Apache-2.0 | 76.1% | 78.3% | 73.9% | 23.3% | 2.4 |
| vanilla turbo | MIT | ~76% (60-call run) | | | 23.4% | 0.8 |
| gcoli turbo gsw MIT | MIT | 75.0% | 80.4% | 69.6% | 24.7% | 1.4 |
| nebi turbo int8 (no prompt, no cond) | CC BY-NC origin | 75.0% | 78.3% | 71.7% | 25.0% | 0.9 |
| OST turbo gsw | ? | 73.9% | 73.9% | 73.9% | 28.5% | 2.5 |
| nebi turbo int8 default (prompt, cond) | CC BY-NC origin | 70.7% | | | 27.6% | 0.9 |
- DECISION: gcoli large-v3 MIT = ASR candidate (best keyword recall, licence-clean). CIs overlap with most others
  (10 level-1 dialogues carry all keyword spots) -> argue it on licence + consistent lead, not significance.
- Skipped (GPU time to the LLM sweep): vanilla large-v3 clean, turbo beam 5 (stopped at 30/60, partial cache kept).

## 2026-10-10T02:29 A7/RQ8 denoise front end (DPDFNet2 via sherpa-onnx, CPU 4.5 s per audio min) before turbo int8 (no cond)
- dev kw-spot recall 76.1% vs 75.0% without; noisy 76.1% vs 71.7%, clean 76.1% vs 78.3%; CER 25.5% vs 25.4%.
- No detectable effect (CIs ~[63, 90]); small noisy gain offset by a small clean loss. DECISION: denoise stays an
  option (plugin kept, off by default); no detection run spent on it. The clean/noisy gap is closed more by decoding
  settings (no prompt, no conditioning) and by the large-v3 model than by denoising.
- 02:29 Qwen2.5-14B-AWQ starting (GPU exclusive, fp8 KV, 12k ctx).

## 2026-10-10T02:35 V4/A4 LLM transcript correction view `de_fused` (fuses turbo + large-v3 + vanilla turbo hypotheses)
- 4 noisy level-1 calls (D02/D04/D05/D09-K2), corrector Qwen3-8B: kw spots de 9/19, de_large 14/19, de_vanilla 13/19,
  **de_fused 15/19**; repaired the D02-K2 prompt loop (insider passage restored). +1 spot over large-v3 alone ->
  most of the gain is the large-v3 model. DECISION: not worth 3 ASR passes + an LLM pass per call for Sunday; use
  large-v3 directly. Keep de_fused as an option/creativity story (multi-hypothesis repair) — not on the critical path.

## 2026-10-10T02:44 L1 Qwen3-8B-AWQ (thinking off, fp8 KV) — 13 min for all checks on 48 dev calls
- Verified rows[].models = Qwen/Qwen3-8B-AWQ only (audit F3). 1 call DEGRADED (llm_judge truncated JSON once).
- flag AUC: v1 set 0.64 (7B: 0.68); facts_only 0.74 (7B: 0.84); judge+facts 0.76; hybrid 0.76; blind table 0.67.
- Qwen3-8B is not better than Qwen2.5-7B here. Caveat: the tuned fact wording was developed against 7B answers.
- Qwen2.5-14B-AWQ failed to start at 0.90 util / 12k ctx / fp8 KV (root cause lost: log overwritten -> per-model
  logs now). Qwen3-14B starting; 14B retry with smaller context afterwards.
- Re-fusion-only runs abort while vLLM is swapping (F3 identity check); run them when a model is up or only refuse variants.

## 2026-10-10T02:50 L1 14B on 12 GB + product variant facts_kwlight
- Qwen2.5-14B-AWQ: full check set OOMs at runtime (11.2/11.7 GB in use after load; 0.95 util, 8k ctx, 4 seqs).
  Qwen3-14B OOMs at startup. Running a facts-only pass at util 0.90 / 6k ctx / 2 seqs (fact probes are single-token,
  prefix-cached) to answer "does a bigger model improve the check we ship?".
- facts_kwlight (facts w1 + keywords w0.15 + patterns w0.1, abstain_on_empty): same CV operating point as facts only
  (FAR 18%, miss 27%, cap reachable 4/4 folds, FAR floor 14%), AUC 0.80 vs 0.84. Keeps the officer's keyword list
  live in the decision (jury: "adjust keyword list without code ... visible effect") at a small, not significant cost.

## 2026-10-10T03:10 L1 Qwen2.5-14B-AWQ facts-only pass (util 0.90, 6k ctx, 2 seqs; 20 min / 48 calls = 25 s per call)
- facts (tuned table): flag AUC 0.87 [0.76, 0.96] vs 7B 0.84 [0.70, 0.95], Qwen3-8B 0.74; CV FAR 14%, miss 23%, 3-class acc 75%.
- R4 BLIND table: 14B 0.77 [0.62, 0.91], Qwen3-8B 0.67 vs tuned 0.87 / 0.74 -> ~0.07-0.10 AUC of the tuned table's
  advantage may be dev-fitted wording; the blind table still beats the free 7B judge (0.68). Honest range for an
  unseen-call facts system: AUC ~0.77-0.87.
- 14B vs 7B on facts: +0.03 AUC, CIs overlap heavily -> no detectable difference at n=24 dialogues; 3x cost.
- Queued with the 14B up: facts on large-v3 ASR transcripts, facts on ORACLE dialect scripts.

## 2026-10-10T03:17 R2-ish: blind table as review-only second opinion (14B, re-fusion, 0 GPU)
- hybrid(core=facts, second_opinion=facts_blind): review recall 50% -> 83% (fixed thr), miss 23% -> 15%, but FAR 14% -> 36%
  (over the 20% cap); AUC unchanged 0.87. A trade-off, not a win -> offer as an officer-selectable "strict review"
  policy (more reviews, fewer misses), default off.

## 2026-10-10T03:38 facts x ASR x table (Qwen2.5-14B, dev 48 calls, flag AUC [CI] / CV FAR / CV miss)
| transcripts | tuned table | blind table | tuned + blind (mean) |
|---|---|---|---|
| default turbo int8 | 0.87 [0.76, 0.96] / 14% / 23% | 0.77 [0.62, 0.91] / 36% / 23% | 0.88 [0.77, 0.98] / 27% / 19% |
| gcoli large-v3 MIT | 0.85 [0.73, 0.96] / 18% / 23% | **0.85** [0.72, 0.96] / 27% / 12% | 0.87 [0.76, 0.97] / 27% / 19% |
- KEY: with the better ASR the BLIND table (never saw a call) matches the tuned one (0.85 vs 0.85); on turbo it lags
  (0.77). The tuned wording's edge was largely compensation for turbo ASR errors -> large-v3 + a criteria-derived
  table is the most defensible combination (least dev-fitting). Tuned+blind ensemble (two independent wordings):
  0.87-0.88, no detectable difference, more robust to wording.
- Verified served model ids for the l3 run.

## 2026-10-10T03:59 V3 ORACLE ceiling with facts (Qwen2.5-14B, dialect reference scripts = ref_gsw, no ASR)
- tuned table: flag AUC 0.90 [0.79, 1.00], CV FAR 0% , miss 23%, 3-class acc 88%, review recall 67% (ORACLE).
- blind table: 0.78 [0.64, 0.92] (vs 0.85 on large-v3 Standard German ASR text).
- Reading: perfect transcripts add only ~0.03-0.05 AUC over large-v3 ASR (0.85-0.87) -> ASR is no longer the bottleneck
  once large-v3 + facts are used. Dialect text is not easier for the LLM than Standard German ASR output (blind table
  0.78 dialect vs 0.85 Standard German) -> supports transcribing to Standard German (RQ3), CIs overlap.

## 2026-10-10T04:01 R4 on 7B (turbo transcripts): blind table 0.73 [0.57, 0.88] vs tuned 0.84; ensemble 0.82.
- Same pattern as 14B/Qwen3-8B on turbo transcripts: the blind table lags by ~0.1 AUC. Waiting for 7B on large-v3.

## 2026-10-10T04:15 D1 / RQ10 synthetic out-of-sample stress test of `facts` (Qwen2.5-14B-AWQ judge, ORACLE text)
- Set: data_synth/v1, 74 text scripts, 26 scenarios x twins (alarm / harmless / review; 44 twins are minimal-pair
  rewrites of their base), written FRESH from config/synth_scenarios.yaml by Qwen3-8B-AWQ (generator) in Swiss Standard
  German (the 8B's dialect was broken pseudo-dialect with loops -> dropped). Labels from the scenario file, never the LLM.
  Judge = Qwen2.5-14B-AWQ (a different model than the generator). Split `external` (no holdout look), CV folds and
  bootstrap units = scenario (26). Label audit by Claude BEFORE results: 4 invalid + 5 doubtful -> audited subset 65.
- experiments/synth_stress.yaml (74) | synth_stress_audited.yaml (65):
  v1 (kw+pat+judge+geval) flag AUC 0.83 | 0.89; CV FAR 61% | 56%; miss 4% | 5%; review recall 52% | 62%
  facts_only               0.82 | 0.84;        14% | 4%;        33% | 35%;      0% (CV; fixed 57%)
  judge_facts              0.90 | 0.94;        57% | 52%;        7% | 8%;       71% | 75%
  kwpat_facts              0.86 | 0.92;        18% | 8%;        24% | 25%;      67% | 62%
  facts_blind_only         0.76 | 0.77;        21% | 20%;       30% | 32%
- Same model on dev ORACLE (V3 above): tuned facts 0.90 -> 0.82 synthetic (-0.08; alarm AUC 0.91 -> 0.75), blind table
  0.78 -> 0.76 (-0.02). The tuned wording loses more out of sample (consistent with dev-fitting) but still edges the
  blind table. CIs overlap everywhere except FAR/miss/review; diff-in-diff has no CI (indicative only).
- facts keeps its FAR advantage out of sample (14% vs 61%, real) but its extra misses concentrate in ACCESS: 3/12
  flagged (blind table 10/12): `current` comes back "unknown" for every read-out code (even "noch zehn Minuten gültig"),
  and no rule catches spoken=yes & current=unclear & validity_open=no -> no_alert. Other families: 28/34 flagged.
- Other systematic facts errors: advisor as the inside source (trade `inside_info` examples only list family/employer
  -> unknown -> review instead of alarm); unsolicited advisor disclosure (no "you have no POA" sentence ->
  not_authorized=no -> review); advisor's leading question "um den Finanzchef zu umgehen, richtig?" -> avoid_control=yes
  although the customer denies it (review -> alarm).
- Caveats: synthetic, LLM-written (Qwen family on both sides), more explicit than the case calls (the free judge does
  much better here than on dev: 0.83-0.89 vs 0.68); 26 units -> wide CIs. Not the case holdout.

## 2026-10-10T04:03 champion candidate: large-v3 MIT ASR + Qwen2.5-7B + tuned facts (dev, 48 calls)
- qwen25_7b_facts_l3: flag AUC 0.89 [0.77, 0.99], CV flag F1 0.86, FAR 14%, miss 15%, alarm F1 0.86, review recall 67%,
  3-class acc 79% — best non-ORACLE result of the night; fits 12 GB (staged: ASR then LLM). Blind table on it 0.79.
- vs v1 (turbo + free judge, 7B): AUC 0.68 -> 0.89. Both ASR (+keyword recall) and check design contribute;
  with facts the ASR upgrade now shows (7B facts: turbo 0.84 -> large-v3 0.89; CIs overlap).
- DECISION: freeze config/recommended.yaml = large-v3 MIT fp16 + Qwen2.5-7B-AWQ + facts (w1) + keywords (w0.15) +
  patterns (w0.1), abstain_on_empty; experiments/champion.yaml queued (dev) after the 7B phase; scripts/run_staged.sh
  for new calls on one 12 GB GPU. 14B = optional upgrade for bigger GPUs (no detectable gain here).

## 2026-10-10T04:04 RQ3 dialect vs Standard German input, facts check
| input text | Qwen2.5-7B | Qwen2.5-14B |
|---|---|---|
| dialect reference script (ORACLE ref_gsw, perfect words) | 0.76 [0.56, 0.92] | 0.90 [0.79, 1.00] |
| Standard German ASR (large-v3 MIT) | **0.89** [0.77, 0.99] | 0.85 [0.73, 0.96] |
| Standard German ASR (turbo int8) | 0.84 | 0.87 |
- The 7B reads Standard German ASR output better than PERFECT dialect text; the 14B copes with dialect. For a
  12 GB / 7B deployment "transcribe straight to Standard German" is the right view (RQ3). CIs overlap pairwise.

## 2026-10-10T04:08 D1/RQ10 synthetic out-of-sample stress test (74 fresh twin scripts, text only, judged by Qwen2.5-14B)
- Scripts written by Qwen3-8B from fresh scenarios (labels from the scenario file, never from the LLM), audited blind by
  a different model family before results (9 doubtful/contradicting -> results on 74 and on 65 clean).
- flag AUC (74 / 65): v1 0.83/0.89, facts 0.82/0.84, judge+facts 0.90/0.94, kw+pat+facts 0.86/0.92, blind table 0.76/0.77.
  FAR: v1 61%/56% vs facts 14%/4% (real -46 pp); miss: facts 33% vs v1 4% (real +28 pp).
- Out of sample, facts keeps its false-alarm advantage but no longer out-ranks the free judge; the tuned table drops
  0.90 -> 0.82 (14B, dev ORACLE -> synthetic), the blind one 0.78 -> 0.76 => some dev-fitting confirmed.
- Misses concentrate in ACCESS (facts flags 3/12): "code spoken, validity unknown" falls to no_alert — a rule gap vs
  criteria ("validity cannot be established" = undetermined). DECISION: policy_table_v2.yaml adds access.review_2
  (spoken = yes and current = unclear -> review); evaluated on dev as champion variant `table_v2` (fact answers cached).
- kw+pat+facts (closest to the recommended profile) is the best balance on synthetic: AUC 0.86/0.92, FAR 18%/8%.

## 2026-10-10T04:06 V1/RQ1 English view (LLM translation of the de ASR view, 7B) with facts
- facts on en_from_de: flag AUC 0.82 [0.68, 0.95] vs 0.84 on de (same 7B, same turbo transcripts); CV FAR 18% both.
- No detectable difference; translation costs an extra LLM pass per call and loses a little. DECISION: keep the
  Standard German view. (en_speech = Whisper speech translation not run: vanilla large-v3 next to vLLM does not fit
  and the de/en comparison already shows no gain.)

## 2026-10-10T04:09 champion on its own profile (experiments/champion.yaml, dev) + FREEZE
- champion (config/recommended.yaml): flag AUC 0.87 [0.72, 0.99], CV flag F1 0.86 [0.73, 0.96], FAR 14% [0, 35],
  miss 15% [0, 36], alarm F1 0.86, review recall 67%, 3-class acc 79%. Identical for thresholds 0.45-0.65 and with
  review band 0.25 / no uncertainty escalation (facts scores are near-discrete -> robust threshold plateau).
- table_v2 (access.review_2): miss 15% -> 8% but FAR 14% -> 36% (C01/C02 harmless "4242..." test card numbers count as
  a spoken code; C10). REJECTED for the default; documented as a stricter access policy option.
- DECISION 04:09: FREEZE champion = config/recommended.yaml (table v1, threshold 0.55). Run the holdout ONCE now
  (12 calls / 6 dialogues). Also one logged holdout look at the v1 baseline (gpu-12gb, all 4 checks) purely as a
  reference point for "how much better than v1" — not a candidate, nothing is tuned on it. Total holdout looks: 2.

## 2026-10-10T04:12 Z1 HOLDOUT (logged in runs/holdout_log.jsonl; 2 looks in total, both listed here)
Holdout = 6 dialogues / 12 calls (D07, C03, C04, C15, C16, C19): alarm 4 calls, no_alert 6, review 2.
| system | flag F1 | flag recall | FAR | miss | alarm F1 | 3-class acc |
|---|---|---|---|---|---|---|
| **champion** (config/recommended.yaml, frozen 04:09) | 0.67 | 50% | **0%** | 50% | **0.67** | **67%** |
| v1 baseline (gpu-12gb, reference only) | 0.67 | 100% | 100% | 0% | 0.00 | 17% |
- champion per call: D07 disclosure alarm K1/K2 -> alarm (both); harmless C03, C04, C15 (both versions) -> no_alert;
  C16 splitting alarm -> K3 no_alert (score 0.17), K4 review; C19 documentation review -> no_alert (both).
- v1 sends all 12 calls to review (scores 0.43-0.71): "flag everything" — same flag F1, useless for an officer.
- Weak spots on unseen calls = the dev weak spots: open review cases (Stufe3) and the splitting family. n = 6
  dialogues: every number here has a huge CI; it is a sanity check, not a measurement.
- Holdout results kept in runs/experiments/champion_holdout/ and runs/experiments/holdout_v1/ (the experiment runner
  writes holdout variants into the dev directory; moved and the dev champion re-run from cache).

## 2026-10-10T04:25 R3 paraphrase robustness (champion profile, 7B, large-v3 transcripts, dev 48 calls)
- config/policy_table_para.yaml (scripts/research/make_para_table.py): every fact question (en + de) reworded blind
  (no transcripts read), ids/roles/rules identical. Variant `para` in experiments/champion.yaml.
- para vs champion: flag AUC 0.72 [0.52, 0.88] vs 0.87 [0.72, 0.99], paired diff -0.15 [-0.31, -0.03] (real);
  CV flag F1 0.68 vs 0.86 (McNemar p=0.008); CV FAR 23% vs 14%; miss 38% vs 15%; review recall 0% vs 67%;
  3-class acc 67% vs 79%. FAR<=20% cap reachable in 2/4 folds (champion 4/4).
- Label flips (fixed threshold): 11/48 3-class (23%), 8/48 flag; ALL 11 worse: D05-K1 alarm->no_alert, D05-K2,
  C06-K3/K4 alarm->review, C07-K4 alarm->no_alert, C17-K3/K4 + C18-K3/K4 review->no_alert, D01-K1 + C14-K4
  no_alert->review.
- Fact answers (960): value agreement 73.3%, but mean |dp(yes)| only 0.038. 217/256 disagreements are no<->unclear
  (p(no) near 0.5); yes-involving changes 39/960; yes-agreement 54/93. Worst facts: documentation.omit_request 31%,
  trade.inside_info 33% (no/yes->unclear), disclosure.authorized 38% / trade.public 38% / access.validity_open 42%
  (unclear->no), access.spoken 58% (7 yes->no: C17 lost, the wording tuned on C17 earlier).
- Mechanism: rules that test `= unclear` (disclosure.review_2, trade.review_1) and the hand-tuned act wordings
  (access.spoken, trade.inside_info) carry the dev result; the no/unclear boundary is wording-noise.
- Falsification criteria from ideas_round2 R3 (>15% flips or AUC drop >0.10) both met -> the tuned wording is
  FRAGILE on rephrasing; consistent with R4/D1 dev-fitting. Expect hidden-set AUC nearer 0.72-0.79 than 0.87.
  Next: average p over wordings (W3 ensemble) and make review rules depend on p(yes) bands, not on `unclear`.

## 2026-10-10T04:17 R2 review facts (table v3): explicit "decisive fact is open" facts per family (NOT the champion)
- config/policy_table_v3.yaml = tuned table v1 unchanged + per family an explicit "open" fact worded ONLY from
  criteria.yaml review_when (trade source_open, access process_open (+ existing validity_open), disclosure
  authorization_open, documentation relevance_open, splitting link_open + motive_open) with review rules
  `act in [yes, unclear] and open = yes (and exculpatory != yes) -> review`, + splitting re-check facts from the criteria
  policy text (split_connected, approval_avoided) with an OR-ed splitting.alarm_2. No transcripts read while writing.
- DEV (experiments/champion.yaml `table_v3` vs `champion`, 48 calls, paired): flag AUC 0.92 [0.80, 1.00] vs 0.87
  (diff +0.05 [0.00, +0.17]); CV FAR 14% vs 14%; CV miss 8% vs 15%; review recall 100% vs 67%; 3-class acc 83% vs 79%;
  CV@FAR20 compliant, FAR floor 14% unchanged. 2 flips, both correct: C20-K3/K4 review (splitting.review_open via
  link_open; was no_alert). McNemar p=0.5. No difference is detectable (1 dialogue moved; dev has 3 review dialogues).
- SYNTHETIC (synth_stress `facts7b_v1` vs `facts7b_v3`, both Qwen2.5-7B computed now, ORACLE text, 74 calls / 26
  scenarios, fixed threshold): flag AUC 0.80 -> 0.83 (diff +0.025 [0.00, +0.06]); FAR 7% -> 7%; miss 48% -> 41%;
  review recall 38% -> 48%; 3-class 58% -> 61%. Audited 65: AUC 0.80 -> 0.82, FAR 8% -> 8%, miss 45% -> 40%, review
  recall 38% -> 50%. 3 flips, none harmful: disclosure_003 and trade_015 review (review_open), splitting_003
  review -> alarm (alarm_2: flagged, wrong class). No harmless call flipped anywhere (dev or synthetic).
- Splitting re-check: alarm_2 rescued no missed splitting alarm (synthetic splitting_001 stays review; 3 of 4 synthetic
  splitting review cases still no_alert). Splitting gain comes only from the open-fact review rule.
- Cost: ~8 extra single-token fact probes per call (~+35-40% fact LLM calls; +~0.3 s/call with prefix caching).
- RECOMMENDATION for the team: v3 only adds review/alarm paths, cost 0 false alarms on 48 dev + 74 synthetic calls,
  and moves review recall the right way on both sets, but every gain is within noise (dev: 1 dialogue; synthetic:
  +2-3 of 21 review cases) and it CANNOT be validated on the used holdout. Option A (conservative, default): keep the
  frozen champion (table v1) as the scored submission and show v3 in the officer UI as the "strict review" policy
  (officer-editable table, same facts). Option B: adopt v3 for Sunday only if the team accepts an unvalidated rule-only
  change with a 0-FAR-cost record on dev+synthetic; if so, say "no holdout validation" on the slide. I lean A+demo:
  the pitch claim is "the officer adds review rules without code", and v3 is the live proof, without touching the
  number we report.

## 2026-10-10T04:20 lead decision on table v3 (review facts) — NOT a holdout candidate
- v3 dev: AUC 0.92 vs 0.87 (diff +0.05 [0.00, +0.17]), FAR 14% = 14%, miss 8% vs 15%, review recall 100% vs 67%;
  synthetic (7B): AUC 0.83 vs 0.80, review recall 48% vs 38%, FAR unchanged. No harmless call flipped anywhere.
- CONTAMINATION NOTE: the v3 builder's brief mentioned that the splitting family was missed on the holdout (C16), i.e.
  v3 was designed with knowledge of a holdout failure mode -> a holdout run of v3 would be biased; not run.
- DECISION: submission numbers stay with the frozen champion (table v1). v3 is offered to the team as a low-risk
  option ("strict review": more reviews, no extra false alarms on dev/synthetic), clearly labelled "no holdout
  validation". Final pick for Sunday = team decision (see DECISIONS.md D2b).

## 2026-10-10T04:22 CORRECTION to the 04:08/04:15 synthetic entries
- data_synth/v1/manifest.json: 71 of 74 synthetic scripts were written by Qwen2.5-14B-AWQ (the vLLM model had swapped
  during generation), i.e. the SAME model that judged them, not Qwen3-8B as logged. The circularity risk of RQ10 is
  therefore higher than stated; labels still come from the scenario file and were audited blind by another family.
- Findings RQ1, RQ3, RQ7, RQ8, RQ9, RQ10, RQ11, RQ12 written (writer agent; numbers copied from summaries/journal).

## 2026-10-10T04:35 R6 paraphrase ensemble (facts averages p(yes/no/unclear) over wordings of the SAME fact)
- Built (checks/facts.py, backward compatible; recommended.yaml facts cache key pinned in tests/test_facts.py):
  `paraphrase_tables: [path, ...]` (every fact id of the main table found in a paraphrase table is asked once per
  wording, probabilities averaged before thresholding, main table's rules decide, per-wording p in
  `facts.<id>.wordings`); `unclear_band: [lo, hi]` = fact value from averaged p(yes) alone (yes >= hi, no < lo,
  else unclear). The literal "yes if p(yes) >= hi, no if p(no) >= hi, else unclear" already exists as `decide_at`
  (run as ens3_d06). config/policy_table_para2.yaml = second blind paraphrase set (scripts/research/make_para2_table.py,
  no transcript or result read, different style from para). Variants in experiments/champion.yaml + synth_stress.yaml.
- DEV (48 calls, 7B, large-v3; flag AUC [CI] | CV FAR / miss | review recall | 3-class acc | label flips vs champion):
  | champion (tuned) | 0.87 [0.72, 0.99] | 14% / 15% | 67% | 79% | - |
  | para (R3)        | 0.72 [0.52, 0.88] | 23% / 38% | 0%  | 67% | 11/48 |
  | para2 alone      | 0.74 [0.54, 0.90] | 23% / 31% | 0%  | 71% | 10/48 (all worse) |
  | ens2 tuned+para  | 0.81 [0.65, 0.94] | 14% / 27% | 0%  | 73% | 4/48 |
  | ens2b tuned+para2| 0.78 [0.59, 0.94] | 18% / 27% | 0%  | 69% | 4/48 |
  | ens3 all three   | 0.74 [0.54, 0.92] | 18% / 31% | 0%  | 75% | 7/48 (all worse) |
  | ens3_d06         | 0.77 [0.59, 0.93] | 18% / 27% | 0%  | 75% | 6/48 |
  | ens3_band [.2,.6]| 0.73 [0.55, 0.90] |  9% / 38% | 0%  | 71% | 11/48 |
  | ens_blind para+para2 | 0.75 [0.55, 0.92] | 18% / 31% | 0% | 73% | 8/48 |
  Paired AUC diff vs champion: para2 -0.13 [-0.29, -0.01] (real), ens3 -0.12 [-0.28, -0.00] (real), ens3_d06 -0.10
  (real), ens3_band -0.13 (real), ens2 -0.06 [-0.14, 0.00], ens2b -0.09 [-0.22, 0.00] (no detectable difference).
- Wording sensitivity (label flips when ONE wording is swapped): single tables champion<->para 11/48, champion<->para2
  10/48, para<->para2 8/48; 2-wording ensembles ens2<->ens2b 4/48, para<->ens_blind 5/48. Fact value agreement
  73-77% (single) -> 86.7% (ens2 vs ens2b), mean |dp(yes)| 0.027-0.038 -> 0.013. => averaging roughly HALVES the
  wording noise, as intended.
- But on dev every ensemble scores below the tuned wording alone: review recall 67% -> 0% (C17/C18 review calls lost
  in every variant: the tuned access.spoken wording carries them), alarms C06-K4/C07-K4 drop to review. The dev edge
  of the champion IS its tuned wording; averaging in blind wordings removes the dev-fitting along with the noise.
  ens3_band (decide from p(yes) only) makes the no/unclear mass irrelevant but turns 469 unclear->no, killing the
  `= unclear` review rules: FAR 9% but miss 38%. Rejected.
- SYNTHETIC out-of-sample (74 scripts, 26 scenarios, ORACLE text, 7B, facts alone; flag AUC | CV FAR / miss | flips vs tuned):
  tuned (facts7b_v1) 0.80 [0.71, 0.89] | 7% / 43% | - ; para 0.70 [0.59, 0.80] | 21% / 54% | 16/74;
  para2 0.84 [0.74, 0.92] | 11% / 39% | 14/74; ens3 0.81 [0.71, 0.89] | 11% / 43% | 11/74; ens3_band 0.78 | 11% / 46%.
  para<->para2 15/74 flips. Out of sample the tuned wording has no edge (para2, written blind, is as good or better;
  para is clearly worse): wording quality varies +-0.07 AUC per table, ens3 lands at/above the median wording and
  never at the worst one. CIs overlap everywhere; no paired CI between facts7b_* variants (summary compares to v1).
- Second fragility datapoint: para2 alone on dev 0.74 (vs 0.87), 10/48 flips, all worse -> R3 replicated with an
  independent paraphrase set. Expect the champion's hidden-set AUC nearer 0.75-0.80 than 0.87.
- DECISION: keep the frozen champion (tuned table, no ensemble) as the Sunday default: it is the only variant with
  review recall > 0 on dev, its holdout look is already spent on it, and ens3 shows no detectable gain out of
  sample (0.81 vs 0.80). ens3 is the documented robustness option (`paraphrase_tables`) — it halves wording
  sensitivity at ~3x the fact probes; worth switching to only with a new, non-dev-tuned table where no single
  wording is privileged.

## 2026-10-10T04:45 single-pass fallback: champion checks on turbo int8 ASR (no prompt, no conditioning)
- experiments/champion.yaml variant turbo_clean (dev): flag AUC 0.85 [0.70, 0.98] vs champion 0.87; CV FAR 14% both;
  miss 23% vs 15%; review recall 0% vs 67% (CV) ; 3-class 73% vs 79%. Fits next to vLLM on 12 GB (no staging).
- DECISION: config/recommended-turbo.yaml = fallback for live processing (UI "Anruf verarbeiten", `callguard run`);
  the staged large-v3 champion stays the scoring config.

## 2026-10-10T04:50 E2E on NEW audio files (the Sunday procedure, no cache): staged recommended profile
- 3 dev calls re-encoded (sox speed 1.04, gain -2 dB -> new audio hashes, nothing cached) with neutral names
  call_a/b/c (no hints). Stage 1 `callguard transcribe -c recommended` (vLLM stopped): 45 s for 3 calls (~13 min audio,
  incl. model load); vLLM 7B restart 28 s; stage 2 `callguard run -c recommended`: 20 s for 3 calls.
- Results: call_a (= D02-K1 insider trade) ALARM 0.99 "Regel trade.alarm_1, Fakt Insider-Information = ja";
  call_b (= D03-K2 harmless keyword call) KEIN ALARM 0.05; call_c (= C17-K3 open access case) PRÜFEN 0.50 — all as
  expected. Chain runs without manual steps per call (case requirement). Log: runs/logs/e2e_new.log.
- Note: `callguard transcribe` with vLLM down also diarizes and falls back to first-speaker roles (not cached since the
  audit fix) -> roles recomputed in stage 2 with the LLM.

## 2026-10-10T04:55 R3 on 14B: wording fragility is a 7B problem
- qwen25_14b_para_l3 (paraphrased table, large-v3 ASR, 14B): flag AUC 0.88 [0.76, 0.98], CV FAR 9%, miss 27%, 3-class 77%
  vs tuned table 0.85 [0.73, 0.96] and blind table 0.85 on the same transcripts. 7B with the paraphrased table: 0.72.
- => with the 14B the facts decision is robust to the question wording (three independent wordings 0.85-0.88); with the
  7B it is not (0.72-0.89). For unseen calls this robustness matters more than the 7B's dev score.
- DECISION: candidate B = config/recommended-14b.yaml (same ASR/checks/table, LLM Qwen2.5-14B-AWQ). Chosen on DEV
  evidence only (paraphrase robustness), not on holdout results. Run dev (experiments/champion14.yaml), then ONE holdout
  run (experiments/champion14_holdout.yaml) -> third logged holdout look in total (2nd candidate).

## 2026-10-10T05:05 candidate B (14B) dev + its single HOLDOUT run (3rd logged holdout look; all looks listed)
- dev (experiments/champion14.yaml): flag AUC 0.82 [0.68, 0.95], CV FAR 18%, miss 23%, 3-class 71% (fixed thr)
  vs champion (7B) 0.87 / 14% / 15% / 79%.
- HOLDOUT (12 calls): flag F1 0.40, flag recall 33%, FAR 33%, miss 67%, alarm F1 0.00, 3-class acc 33%
  (D07 alarm -> review K1 / no_alert K2; C15 harmless -> review both; C16 -> review K3 / no_alert K4; C19 -> no_alert).
  vs champion (7B) on the same calls: FAR 0%, recall 50%, alarm F1 0.67, 3-class 67%.
- Holdout looks so far: (1) champion 7B 04:08, (2) v1 reference 04:11, (3) candidate B 05:04. Holdout is now spent;
  n = 6 dialogues, so the 7B-vs-14B holdout difference is not significant either way.
- DECISION: submission stays the frozen champion (config/recommended.yaml, 7B). The 14B's wording robustness on dev
  (paraphrase test) did not show on the holdout. recommended-14b.yaml kept as a documented option for bigger GPUs.

## 2026-10-10T05:03 S1 pre-registration (review hardening: shaky "no" -> unclear; ideas_round3 S1)
- Knob: existing `checks.facts.decide_at` (no src edit). NOTE: in facts.py `discretize` it is SYMMETRIC
  (yes if p(yes) >= d, no if p(no) >= d, else unclear), so decide_at=0.8 also raises the "yes" bar to 0.8 (the S1
  design wants yes at 0.5, only no at 0.8). The asymmetric version is simulated offline on the cached fact
  probabilities (same rules, yes >= 0.5, no >= 0.8) as a secondary, clearly labelled analysis.
- Variants: experiments/champion.yaml `s1_v1_08` (table v1, decide_at 0.8), `s1_v3_08` (table v3), `s1_para_08`
  (table para); experiments/synth_stress.yaml `facts7b_s1_v1_08`, `facts7b_s1_v3_08` (7B, facts only).
- PASS rules (all must hold, fixed before seeing any result):
  (a) dev vs champion: at most +1 harmless dialogue flagged (fixed threshold) and CV FAR <= 20%;
  (b) synthetic 7B vs facts7b_v1 / facts7b_v3 (same table): FAR up by at most 7 pp;
  (c) paraphrased-table runs (`para` style, dev): miss down by >= 10 pp vs `para` (s1_para_08 vs para).
- If any rule fails: keep the frozen champion; the hardened setting is at most the UI's "strengere Prüfung" option.
  Holdout is spent and is not touched.

## 2026-10-10T05:09 S1 result: decide_at 0.8 (review hardening) — FAIL, not adopted
- Runs: experiments/champion.yaml `s1_v1_08`, `s1_v3_08`, `s1_para_08`; experiments/synth_stress.yaml
  `facts7b_s1_v1_08`, `facts7b_s1_v3_08` (all fact probes cached; 0 new probes; ~2.3 + 1.2 min). decide_at is
  symmetric (yes AND no need p >= 0.8). Logs runs/logs/s1_dev.log, runs/logs/s1_synth.log.
- DEV (48 calls; flag AUC [CI] | CV FAR / miss | CV review recall | CV 3-class | fixed-thr harmless dialogues flagged):
  | champion   | 0.87 [0.72, 0.99] | 14% / 15% | 67% | 79% | 2 (C11, C14) |
  | s1_v1_08   | 0.86 [0.72, 0.98] | 18% / 19% | 33% | 77% | 3 (+D08)     |
  | table_v3   | 0.92 [0.80, 1.00] | 14% /  8% | 100% | 83% | 2           |
  | s1_v3_08   | 0.91 [0.80, 1.00] | 18% / 12% | 33% | 77% | 3 (+D08)     |
  | para       | 0.72 [0.52, 0.88] | 23% / 38% |  0% | 67% | 3 (D01, C11, C14) |
  | s1_para_08 | 0.74 [0.57, 0.89] | 18% / 35% |  0% | 65% | 2           |
  Fixed-threshold flips vs champion (s1_v1_08): D08-K2 no_alert->review (worse), C07-K4 alarm->no_alert (worse; the
  higher yes-bar removes an act "yes"). s1_v3_08 = those two + C20-K3/K4 review (the v3 gain, already in table_v3).
  s1_para_08 vs para: fixed miss 38% -> 38% (10/26 both); flips D01-K1 review->no_alert and C18-K3 ->review (better),
  D09-K2 alarm->review, C07-K3 alarm->no_alert (worse).
- SYNTHETIC (7B, ORACLE, 74 calls; flag AUC | CV FAR / miss | fixed review recall | fixed 3-class):
  facts7b_v1 0.80 [0.71, 0.89] | 7% / 43% | 38% | 58%  vs  facts7b_s1_v1_08 0.76 [0.65, 0.86] | 14% / 43% | 43% | 53%;
  facts7b_v3 0.83 [0.74, 0.91] | 7% / 37% | 48% | 61%  vs  facts7b_s1_v3_08 0.79 [0.69, 0.88] | 14% / 37% | 52% | 55%.
  FAR 2/28 -> 4/28 (+7.1 pp; new harmless flags disclosure_004, splitting_002) in both tables.
- PRE-REGISTERED RULES: (a) dev: +1 harmless dialogue (D08), CV FAR 18% <= 20% -> PASS (at the limit);
  (b) synthetic FAR +7.1 pp > 7 pp -> FAIL (by 0.1 pp = 2 extra harmless calls of 28; read it as "at the limit");
  (c) para miss 38% -> 35% CV / 38% fixed, -3 pp / 0 pp (needed -10 pp) -> FAIL. => S1 (decide_at 0.8) FAILS.
- SECONDARY (offline, pre-announced): asymmetric yes >= 0.5 / no >= 0.8 re-decided on the cached fact probabilities
  (facts-only labels; the script reproduces champion and s1_v1_08 fixed labels exactly at 0.5/0.5 and 0.8/0.8):
  dev v1 and v3: IDENTICAL to champion / table_v3 (no call changes); wording-shift miss: dev para 10/26 -> 9/26,
  dev para2 8 -> 7, synthetic para 25/46 -> 21/46, para2 18 -> 18 (mean about -4 pp, needed -10 pp); synthetic FAR
  v1 2/28 -> 3/28 (+3.6 pp), dev para FAR 5/22 -> 6/22. => the asymmetric knob is harmless on the tuned tables but does
  not fix the wording fragility either (rule (c) fails). The paraphrase misses are mostly lost act "yes" answers /
  alarm->review drops, not shaky "no" in context facts, so moving no->unclear cannot recover them.
- DECISION: keep the frozen champion (table v1, decide_at 0.5). Do not offer decide_at 0.8 (costs FAR on synthetic,
  lowers review recall on dev, no robustness gain). The table v3 option (D2b) stays as it was. Wording robustness needs
  a different lever (S2 contrastive exemplars or 14B), not a threshold.

## 2026-10-10T05:20 S6 officer answers an open fact (UI panel "Offene Fakten") + S1 result
- New detail panel: open facts with Ja / Nein / Weiss nicht; re-evaluates the policy table in memory (facts.py
  decide_family, no LLM), shows new label + rule + re-fused call label; audit events fact_answer / fact_answer_reset.
  C17-K3: Ja (gültig) -> Alarm via access.alarm_1 (score 0.97); Nein -> Kein Alarm; Weiss nicht -> Prüfen.
  UI-only coupling file config/open_facts.yaml (button texts; which facts an answer settles) — pipeline never reads it.
  Panel appears on 24/62 recommended calls (also alarms with an open exculpatory fact) — team may restrict to review.
- S1 (confident clearance, decide_at 0.8): FAILED 2 of 3 pre-registered rules -> not adopted (journal 05:09).

## 2026-10-10T05:30 S2 pre-registration (contrastive few-shot in fact probes; ideas_round3 S2)
- Hypothesis: 1-2 short contrast examples per fact (an excerpt where the fact is "yes" and one where it is "no",
  <= 6 ASR segments each, with the answer) make the 7B fact answers robust to question wording.
- Build: optional `checks.facts.fewshot: <json>` (default off; cache keys of existing configs unchanged). Example
  pool per dev fold k = dev dialogues of folds != k only (fold-aware CV in the experiment layer; the pipeline never
  sees a fold). Excerpts from the champion's cached large-v3 transcripts; "yes" window = the champion's evidence
  segments for that fact in a pool dialogue whose family decision was correct; "no" window = best-aligned window in
  the twin (or another same-family pool dialogue) where the champion value is "no". Holdout dialogues never used.
  Same excerpts/answers for both wordings (fact ids identical). Driver: scripts/research/s2_fewshot.py (4 fold runs
  per table merged into one variant: champion.yaml `fs_tuned`, `fs_para`, built from rows, --rescore).
- PASS (all must hold, fixed before any result): (1) label flips fs_tuned vs fs_para (3-class, fixed threshold)
  <= 5/48 (baseline champion vs para 11/48); (2) fs_para dev flag AUC >= 0.80; (3) fs_tuned CV FAR <= 20%.
  Otherwise FAIL -> champion stays. Holdout is spent and not touched.

## 2026-10-10T05:50 S2 result: contrastive few-shot in fact probes (fold-aware) — FAIL, not adopted
- Built: `checks.facts.fewshot: <json>` in checks/facts.py + `examples` in fact_prompts.fact_messages (default off;
  cache keys unchanged, pinned test green, 705 offline tests pass). Driver scripts/research/s2_fewshot.py: per dev
  fold k a few-shot file from dev folds != k (runs/research/s2/fewshot_fold<k>.json, provenance inside), 4 fold runs
  per table (runs/experiments/s2_folds/), merged into champion.yaml `fs_tuned` / `fs_para`, --rescore. 7B, large-v3
  transcripts, 48 dev calls, 0 errors, ~10 min total. Log runs/logs/s2_fewshot.log.
- Coverage: 11-14 of ~21 facts per fold got examples; "yes" from champion evidence segments in correctly decided
  pool dialogues, "no" only where the champion value is "no" (twin or best-aligned same-family window) -> many facts
  got a "yes" example only (the 7B hedges to "unclear" on twins); fold 0 had no documentation examples (all
  documentation dialogues are in fold 0).
- DEV (flag AUC [CI] | CV FAR / miss | CV review recall | CV 3-class):
  | champion (no few-shot) | 0.87 [0.72, 0.99] | 14% / 15% | 67% | 79% |
  | para (no few-shot)     | 0.72 [0.52, 0.88] | 23% / 38% |  0% | 67% |
  | fs_tuned               | 0.80 [0.62, 0.94] | 14% / 27% |  0% | 71% |
  | fs_para                | 0.70 [0.52, 0.87] | 18% / 42% |  0% | 65% |
  Paired AUC vs champion: fs_tuned -0.07 [-0.20, +0.01] (not detectable), fs_para -0.17 [-0.33, -0.03] (real).
- Wording sensitivity: label flips fs_tuned<->fs_para 8/48 (6 flag; all in the "worse" direction for para: D04-K1,
  D05-K1, C07-K3/K4 alarm->no_alert, C06-K3/K4 alarm->review, C14-K4 no_alert->review, C18-K3 review->no_alert) vs
  champion<->para 11/48. Fact value agreement 73.3% -> 80.8%, mean |dp(yes)| 0.038 -> 0.023 (n=960): the examples
  do reduce fact-level wording noise, but not enough to stop label flips.
- Few-shot vs no few-shot, same wording: champion->fs_tuned 4 flips (D05-K2 alarm->review, C17-K3/K4 and C18-K4
  review->no_alert: the examples remove the tuned table's review hits); para->fs_para 3 flips (D01-K1 fixed, D04-K1
  and C07-K3 alarm->no_alert).
- PRE-REGISTERED RULES: (1) flips <= 5/48: 8/48 -> FAIL; (2) fs_para AUC >= 0.80: 0.70 -> FAIL; (3) fs_tuned CV FAR
  <= 20%: 14% -> PASS. => S2 FAILS. Champion stays (table v1, no few-shot). Holdout untouched.
- Learned: with the 7B, examples move answers toward the examples' "yes" (act facts) and away from "unclear",
  which kills the `= unclear` review rules (review recall 67% -> 0%, as every robustness lever so far) and does not
  rescue the paraphrase misses. Wording robustness on dev only came from the 14B (R3 on 14B). Possible but untested
  follow-up: balanced yes/no examples for every fact (needs human-labelled fact answers, not champion silver labels).
