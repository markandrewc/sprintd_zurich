# Status board

Update this file whenever a component changes state (and say who/which session). Priorities: P0 = needed
before the research loop, P1 = research-critical, P2 = strengthens results/demo, P3 = stretch goal.
Spec references point into `docs/design/v2_plan.md`.

Last update: 2026-10-10 01:05, laptop session (v2 build handed to the GPU-host session).

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

## In progress (laptop, finishing; pushed to main when done)

| component | prio | notes |
|---|---|---|
| GPU host setup: `config/gpu-12gb.yaml`, `config/remote.yaml`, remote ASR server, `scripts/remote/*`, `docs/REMOTE_GPU.md`, `callguard doctor` | P0 | agent `remote-gpu`; doctor already in CLI |
| Model research notes `docs/research/*.md` | P0 | translation + fine-tuning + dialect ASR written; synthetic/TTS running |

If these are not on `main` when you start, the laptop session died: follow START_HERE Step 1 (inline
setup) and treat missing research notes as your own research item.

## To build (v2), in priority order

**The GPU-host session builds all of this** (the laptop build was cancelled on purpose: everything
happens on the GPU host). Order and pacing: `START_HERE.md` Step 3. If your harness supports Claude Code
workflows, `.claude/workflows/v2-build.js` builds it in 4 pushed stages with per-stage engineering
prompts (run it with args `{root: "<abs path of this repo>"}`); otherwise use those prompts as the
spec for building by hand. Set `owner` to `gpu-host` when you start an item, `done` when it landed.

| # | component | prio | spec | status |
|---|---|---|---|---|
| 1 | Views (gsw/de/translated/en_speech/ref_*), `translator` plugin kind (`llm_translate`, `hf_mt`, `identity`), multi-view pipeline, check `view` param, `check_view`, language-aware keywords (+ English forms), `faster_whisper task: translate`, provenance | P0 | §1, §5 | **done** (owner gpu-host): `callguard/views.py`, `callguard/translate/`, `Pipeline.build_views`; profiles `demo-views` (offline, runs), `gpu-views`, `oracle-views` (both UNTESTED: need GPU / LLM); v1 cache keys pinned in `tests/test_views.py`. Not done here: `hf_mt` untested, `eval.py` still calls `decide()` without `views` (labels unaffected, passages of other-view findings re-anchor only with views) |
| 2 | Holdout lock `config/splits.yaml`, `eval --split dev/holdout`, holdout log | P0 | §1c | done (gpu-host): `callguard splits [--make]`, `eval --split dev\|holdout\|all`, runs/holdout_log.jsonl |
| 3 | Experiment runner `callguard experiment`, `experiments/*.yaml`, dev-fold CV per variant, cost tracking | P0 | §2 | done (gpu-host): spec format in `callguard/experiments.py` docstring; `--dry-run`, `--variants`, `--jobs`, `--rescore`, re-fusion variants (`refuse_from`); smoke/checks_ablation/thresholds specs |
| 4 | ASR eval `callguard asr-eval`: WER/CER, pseudo-references, keyword-spot recall, vanilla baselines | P0 | §2 | todo |
| 5 | Statistics + report: paired bootstrap CIs, McNemar, per-call flip tables, charts, `callguard report`, `callguard leaderboard` | P0 | §9 | done (gpu-host): `callguard/stats.py`, `report.py`; research/leaderboard.md, research/report/ |
| 6 | `keyword_context` check (G-Eval on keyword windows) | P1 | §1b | **done** (owner gpu-host): `checks/keyword_context.py` (+ `checks/window_prompts.py`), keyword + pattern hits -> +-`window` passages, G-Eval digit probs per passage, max over passages, one evidence call for the best; `context: full` = N4 anchored full-call probe (also as type `anchored`, window 0). No hit -> no opinion (`empty: skip`). Experiment `experiments/new_checks.yaml` (RQ7) NOT RUN yet; GPU smoke on D02/D03 only |
| 7 | `semantic_windows` check (embeddings) | P1 | §1b | **done** (owner gpu-host): `checks/semantic.py`, embedders `openai` (/v1/embeddings), `sentence_transformers` (lazy, NOT in the app env: pulls CUDA torch), `fake`; candidates verified by the keyword_context G-Eval prompt. Needs a bge-m3 server at :8001 (not running); smoke ran with the fake embedder only, `min_similarity` untuned |
| 7b | `quote_judge` (N3): judge must quote verbatim, rapidfuzz-verified; "present" without verified quote -> undetermined (<= 0.5) | P1 | ideas N3 | **done** (owner gpu-host): `checks/quote_judge.py`; variant `quote_judge` in `experiments/new_checks.yaml`; fusion-side "no verified passage, no alarm" knob not built |
| 8 | Fact sheet + policy table (A1), role-aware LLM checks (A7), twin few-shot (A8) | P1 | §7 | **facts part done** (owner gpu-host): check `facts` (`checks/facts.py`, `fact_prompts.py`), officer-editable `config/policy_table.yaml` (3-5 yes/no/unknown facts per family, first-match rules, safe rule parser), single-token logprob probes (`yes`/`no`/`unknown` are single Qwen2.5 tokens; sampling fallback), per-fact probe cache (rule edits rerun no LLM), optional evidence call, `prefix_max` (N8, default off), `roles: false` (N12 neutral). Spec `experiments/facts.yaml` (RQ5/RQ9), not run yet. GPU smoke on dev calls OK (~2-8 s/call). Open: A7 per-role turn filtering, A8 twin few-shot |
| 9 | Calibrated / conformal fusion (A5), learned fusion, `fit-fusion` | P1 | §7, §3 | **done** (owner gpu-host): weighted knobs `abstain_on_empty` (N14), `uncertainty_from: llm`, `family_thresholds` (N2; default off = v1 numbers, verified identical on stored results); fusions `calibrated` (Platt per check x family + 3- or 2-label split-conformal -> review) and `learned` (L2 logistic regression), `callguard fit-fusion --kind calibrated\|learned\|thresholds` (dev folds only) and `callguard fusion-cv` (nested CV over dev folds, rows + paired comparison vs the weighted CV rows) in `callguard/fusion/{fit,fitted,calibrated,learned}.py`, `commands/fit_fusion.py`; spec `experiments/fusion.yaml`; tests `tests/test_fusion_variants.py`. NOT RUN on real check results yet (smoke data only) |
| 10 | Cascade (A2), debate (A6), transcript correction view (A4), audio-LLM check (A3), denoise preprocess (A10) | P2 | §7 | todo |
| 11 | UI: view tabs + side-by-side passages, evidence timeline, "why not an alarm", Experiments page | P2 | §7 UX | **done** (owner gpu-host): German officer copy, colour-blind-safe labels (Alarm rot / Prüfen orange / Kein Alarm grau); registries `ui/pages_registry.py` + `ui/panels/__init__.py`; `ui/explain.py` (review causes, why-not-alarm with counter-evidence + best-matching `not_alarm_when`, criterion per passage, timeline events), `ui/sources.py` (source selector: profile runs / experiment variants, read-only; summaries, holdout log); detail timeline (click -> recording seeks), view tabs, side-by-side `Passage.texts`; inbox family/level filters + sort; Quality on the dev split with bootstrap CIs + holdout log line; Experiments page (CI bars, paired diffs, McNemar, flips, report PNGs, leaderboard). Tests `tests/test_ui.py`, `tests/test_ui_v2.py`. Gaps: criterion / not_alarm_when matching is word-stem overlap (labelled "Hinweis" in the UI) unless the facts check names its rule; no browser screenshot taken (headless server) |
| 12 | Synthetic kit: scenarios, LLM script writer, TTS plugins, render, telephone augmentation | P2 | §4 | todo |
| 13 | Fine-tune kit `finetune/` (data prep with dialogue folds, LoRA training for 12 GB, CT2 conversion) | P2 | §3, research note | todo |
| 14 | Routing + notify sink, feedback loop + tuning overlay, cross-call patterns + entities, audit log | P3 | §3, §5 | **done** (owner gpu-host): `routing.py` + `config/routing.yaml` + `config/directory.yaml` (fictional, advisor names from the scripts), sinks `notify` (outbox/webhook/smtp; smtp untested) + `audit` (both in base.yaml), check `entities` (weight 0; not in any profile yet, patterns extract on the fly), `patterns.py`, `feedback.py`, tuning overlay `paths.tuning` (per profile, after profile before --set, hash in provenance); CLI `route`, `feedback add/list/suggest/apply`, `patterns`; UI pages Meldungen / Feedback & Tuning / Muster / Audit-Log + detail panels; tests/test_ops.py. Not done: four-eyes gate in the UI, role-based access |
| 15 | `docs/OPERATING_CONCEPT.md`, `docs/ARCHITECTURE.md` | P3 | §3 | **done** (owner gpu-host); sizing table `<!-- SIZING -->` waits for LLM cost numbers from the experiments |
| 16 | Overnight harness: `research/` protocol, questions, queue, templates (written), saved workflow `.claude/workflows/overnight-research.js` | P0 | §8 | todo |
