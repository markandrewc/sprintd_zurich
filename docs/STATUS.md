# Status board

Update this file whenever a component changes state (and say who/which session). Priorities: P0 = needed
before the research loop, P1 = research-critical, P2 = strengthens results/demo, P3 = stretch goal.
Spec references point into `docs/design/v2_plan.md`.

Last update: 2026-10-10 morning, documentation handover after the overnight GPU-host session (statuses checked
against `src/`, `runs/experiments/` and `research/journal.md`). Research results: `research/MORNING_REPORT.md`.

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

## Laptop hand-off items (state after the night)

| component | status | notes |
|---|---|---|
| GPU host setup | partly (owner gpu-host) | `docs/REMOTE_GPU.md` and `scripts/remote/serve_models.sh` / `tunnel.sh` never landed. The GPU-host session set the host up inline and wrote `scripts/remote/{cuda_env,serve_llm,swap_llm}.sh` and `scripts/run_staged.sh` (setup facts: README "GPU host setup"). `config/gpu-12gb.yaml` and `callguard doctor` work. `config/remote.yaml` + `callguard.serve.asr_server` exist but are untested |
| Model research notes `docs/research/*.md` | partly | `dialect_asr.md`, `translation.md`, `whisper_finetune_12gb.md` exist; the synthetic/TTS note does not |

## v2 items (built by the GPU-host session overnight)

Status: **done** = built, tested offline and used in the research; **partly** = built in part or never run on
real data; **not built**. Owner of every row: `gpu-host` (the overnight session). The long implementation notes
that used to be here are in git history (`git show 3d6c7bc:docs/STATUS.md`) and in `research/journal.md`.

| # | component | prio | spec | status | note |
|---|---|---|---|---|---|
| 1 | Views, `translator` plugins (`llm_translate`, `hf_mt`, `identity`), multi-view pipeline, check `view`, language-aware keywords | P0 | §1, §5 | done | `views.py`, `translate/`; en_from_de (RQ1: no gain) and ORACLE ref_gsw (RQ3) were run. en_speech never ran (vanilla large-v3 does not fit next to vLLM), `hf_mt` untested |
| 2 | Holdout lock `config/splits.yaml`, `--split dev/holdout/all`, holdout log | P0 | §1c | done | `--split` defaults to `dev` everywhere. Holdout looked at three times (7B champion, v1 reference, 14B candidate B), all in `runs/holdout_log.jsonl`; now spent |
| 3 | Experiment runner `callguard experiment`, `experiments/*.yaml`, dev-fold CV, cost | P0 | §2 | done | 16 specs in `experiments/`, results in `runs/experiments/*/summary.md`; `--dry-run`, `--rescore`, re-fusion variants |
| 4 | ASR eval `callguard asr-eval` (WER/CER, keyword-spot recall), `asr-eval-compare` | P0 | §2 | done | `eval_asr.py`, `commands/asr_eval.py`. 8 ASR models/settings compared (findings/RQ2.md) |
| 5 | Statistics + report (paired bootstrap, McNemar, flips, charts), `report`, `leaderboard` | P0 | §9 | done | `stats.py`, `report.py`; flag AUC + CV@FAR20 as the primary metric (DECISIONS D0); audited (stats verified) |
| 6 | `keyword_context` check (+ `anchored` full-call probe) | P1 | §1b | partly | Built (`checks/keyword_context.py`). Only ran inside the `all_plus` variant of `llm_models`; `experiments/new_checks.yaml` never ran, so it was not measured on its own (findings/RQ7.md) |
| 7 | `semantic_windows` check (embeddings) | P1 | §1b | partly | Built (`checks/semantic.py`). Never run with a real embedder (needs a bge-m3 server on :8001); `min_similarity` untuned |
| 7b | `quote_judge` (N3, rapidfuzz-verified quotes) | P1 | ideas N3 | partly | Built (`checks/quote_judge.py`). Its variant in `experiments/new_checks.yaml` never ran (no `runs/experiments/new_checks`) |
| 8 | Fact sheet + policy table (A1), role-aware LLM checks (A7), twin few-shot (A8) | P1 | §7 | partly | `facts` done and is the decision core of `recommended` (see the extra rows below). A7 per-role turn filtering and A8 twin few-shot not built |
| 9 | Calibrated / conformal fusion (A5), learned fusion, `fit-fusion`, `fusion-cv` | P1 | §7, §3 | partly | Built (`fusion/{calibrated,learned,fit,fitted}.py`, tests). `fit-fusion` / `fusion-cv` never run on real check results (findings/RQ9.md). The weighted knobs (`abstain_on_empty`, `uncertainty_from`) were used |
| 10 | Cascade (A2), debate (A6), transcript correction view (A4), audio-LLM check (A3), denoise preprocess (A10) | P2 | §7 | partly | A4 `llm_correct` and A10 `denoise_sherpa` done (see the extra rows below). **A2 cascade, A3 audio-LLM check and A6 debate not built** (no module in `src/`) |
| 11 | UI: view tabs, side-by-side passages, evidence timeline, "why not an alarm", Experiments page | P2 | §7 UX | done | German officer UI, source selector (profile runs / experiment variants), Quality page with dev CIs + holdout table. Checked with Streamlit AppTest on `runs/recommended` (research/DEMO.md) |
| 12 | Synthetic kit: scenarios, LLM script writer, TTS, render, telephone augmentation | P2 | §4 | partly | Text only: `synth/`, `callguard synth`, `config/synth_scenarios.yaml`, 74 scripts in `data_synth/v1`, evaluated with `synth-oracle` (RQ10). TTS plugins, audio rendering and telephone augmentation not built |
| 13 | Fine-tune kit `finetune/` (data prep, LoRA for 12 GB, CT2 conversion) | P2 | §3 | not built | No `finetune/` directory. Only the research note `docs/research/whisper_finetune_12gb.md` exists |
| 14 | Routing + notify sink, feedback loop + tuning overlay, cross-call patterns + entities, audit log | P3 | §3, §5 | done | `routing.py`, sinks `notify` + `audit`, `entities` check (weight 0, in no profile), `patterns.py`, `feedback.py`, UI pages. SMTP untested; no four-eyes gate or role-based access in the UI |
| 15 | `docs/OPERATING_CONCEPT.md`, `docs/ARCHITECTURE.md` | P3 | §3 | done | Sizing table (§8) filled with measured GPU numbers |
| 16 | Overnight harness: `research/` protocol, questions, queue, templates, saved workflow | P0 | §8 | partly | `research/` files used all night (journal, queue, findings RQ1-RQ12, leaderboard, report). `.claude/workflows/overnight-research.js` was not written; the loop ran by hand |

## Built overnight beyond the list

| component | status | note |
|---|---|---|
| `facts` check + officer-editable `config/policy_table.yaml` | done | `checks/facts.py`, `fact_prompts.py`: atomic yes/no/unknown questions scored by single-token logprobs, first-match rules, per-fact probe cache (rule edits rerun no LLM). Dev champion flag AUC 0.87. Table variants for research: `policy_table_blind` (R4), `_para` / `_para2` (R3 paraphrases), `_v2` (stricter access, rejected), `_v3` (open-fact review rules, an option that was never run on the holdout) |
| `geval_cot` check | done | `checks/geval_cot.py` (analysis first, then a logprob digit; no middle anchor). No gain at 7B (findings/RQ4.md, RQ6.md) |
| `quote_judge` check | partly | See row 7b: built, not evaluated |
| `hybrid` fusion | done | `fusion/hybrid.py`: one core check decides, a second opinion may only escalate to review. Rejected at 7B; the blind-table second opinion is the optional "strict review" mode (FAR 14% -> 36%) |
| `preprocess` plugin kind + `denoise_sherpa` (A10) | done | `preprocess/denoise.py` (sherpa-onnx DPDFNet2 / GTCRN, CPU), denoised audio cached. No detectable keyword-recall gain (journal 02:29); off by default |
| `llm_correct` view (A4, multi-hypothesis transcript repair) | done | `translate/correct.py`, view `de_fused` in `gpu-views`. Smoke on 4 noisy calls only (15/19 keyword spots vs 14/19 for large-v3 alone); not worth the cost for Sunday |
| Synthetic script kit | partly | See row 12 (text only, no audio) |
| Audit fixes F1-F6 | done | FAR-cap-first leaderboard ranking, split default `dev` + holdout logging everywhere, live LLM identity check, visible G-Eval fallback, re-fusion provenance (commit `5d9264d`, `tests/test_audit_fixes.py`) |
| `config/recommended.yaml` + `scripts/run_staged.sh` + `scripts/remote/*.sh` | done | Frozen champion profile and the staged ASR-then-LLM runner for one 12 GB GPU |
| Research profiles | done | `llm-sweep` (+ `-oracle`, `-views`), `oracle-gpu`, `oracle-views-gpu`, `gpu-views`, `synth-oracle`, `demo-views` |
