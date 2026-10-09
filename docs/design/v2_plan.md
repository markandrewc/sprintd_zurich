# callguard v2: views, experiments and stretch goals (build spec)

This is the shared contract for the v2 build. Names, signatures and file ownership below are fixed so
several engineers can build in parallel. Everything heavy (LLM, Whisper, TTS, training) runs on the
GPU host (RTX 4070 12 GB over Tailscale, later event GPUs). The laptop only runs offline paths
(`demo-offline`, fake LLM, reference ASR, identity translator, fake TTS).

Research notes with model picks: `docs/research/*.md` (dialect ASR, translation, synthetic calls/TTS,
Whisper fine-tuning on 12 GB). Use them for model ids and defaults; mark untested GPU paths as untested.

## 1. Transcript views (the core idea)

A **view** is one textual rendering of a call. We compare which one gives the best detection:

| view | lang | how it is produced |
|---|---|---|
| `de` | de | Swiss German speech -> Standard German text (today's Whisper fine-tunes) |
| `gsw` | gsw | Swiss German speech -> dialect text (dialect ASR model, see research) |
| `de_from_gsw` | de | `gsw` translated to Standard German by a translator |
| `en_from_de` | en | `de` translated to English |
| `en_from_gsw` | en | `gsw` translated to English |
| `en_speech` | en | Whisper `task: translate` straight from audio |
| `ref_gsw` | gsw | ORACLE: reference script (dialect) - experiments only |
| `ref_de`, `ref_en` | de/en | ORACLE: reference script translated - experiments + pseudo-reference for WER |

### Config

```yaml
views:                 # optional; absent -> single view "main" = top-level asr + diarizer (v1 behaviour)
  de:
    lang: de
    asr: {...}         # optional; default = top-level `asr`
    diarize: true      # run the top-level diarizer on this ASR view
  gsw:
    lang: gsw
    asr: {type: faster_whisper, model: models/asr/<dialect-model>, ...}
    diarize: true
  en_from_de:
    lang: en
    from: de
    translator: {type: llm_translate, llm: default}
primary_view: de       # passages, snippets, UI default transcript
check_view: null       # if set, overrides every check's `view` (experiments: "run all checks on en")
extra_views: []        # views to compute even if no check reads them (UI comparison)
```

Every check accepts `view: <name>` (default: `primary_view`). Several instances of one check type on
different views form a **multi-view ensemble** (e.g. `llm_judge_de` + `llm_judge_gsw`); fusion merges
their findings by audio time, and agreement across views lowers uncertainty.

### Types (additions; all optional/defaulted so v1 results still load)

- `Transcript.view: str = "main"`, `Transcript.lang: str | None`
- `CallResult.views: dict[str, Transcript]` (all computed views; `CallResult.transcript` stays the primary view)
- `CheckResult.view: str | None`
- `Passage.texts: dict[str, str]` (what each computed view says in the passage's time range)
- `Keyword.en: list[str]` (English forms; `Keyword.forms(lang)` returns the phrases to match for a view language:
  gsw -> gsw + de, de -> de + gsw, en -> en)
- `CallResult.meta["provenance"]` (see 5.)

### Plugin kind `translator`

```python
class Translator(Plugin):
    def translate(self, transcript: Transcript, target_lang: str) -> Transcript: ...
```

Keeps segment ids, start/end, speaker, role, confidence (words dropped). Built-ins:
`llm_translate` (callguard.translate.llm:LLMTranslator, any LLM client, batches of segments as JSON
`{translations: [{id, text}]}` with a few segments of context, keeps numbers/codes verbatim, falls back
per segment on id mismatch), `hf_mt` (callguard.translate.hf_mt:HFTranslator, NLLB/MADLAD via
transformers, lazy import, untested), `identity` (callguard.translate.identity:IdentityTranslator, tests).
Translation cached on (source segments hash, translator cache_params, target lang).

### Pipeline

`Pipeline.build_views(audio_path, call_id) -> dict[str, Transcript]` computes the needed views as a
small DAG (cycle check): needed = primary + views read by enabled checks + extra_views (+ their sources).
ASR views: own ASR plugin each (lazy, cached per audio hash + asr params), diarized if `diarize: true`.
Translated views: copy speaker/role from source. `process()` runs each check on its view and passes
all views to fusion: `Fusion.decide(transcript, results, families, overrides, views=None)`.

`faster_whisper` gains `task: transcribe|translate`.

## 1b. New checks ("in between" keywords and full-call LLM)

- `keyword_context` (callguard/checks/keyword_context.py:KeywordContextCheck): for every keyword /
  pattern hit, cut a window of +-N segments (default 3) around it and ask the LLM G-Eval style
  (probability-weighted 1-5 via `choice_probs`, sampling fallback) whether THIS passage is the family's
  misconduct, giving the keyword's `harmless` note and the family criteria. Score per hit, family score =
  max over hits, findings pinned to the window. Cheap (short prompts, only where keywords fire) and
  directly targets the borderline demo case (harmless call full of keywords). Params: `window`,
  `view`, `llm`, `min_hit_score`.
- `semantic_windows` (callguard/checks/semantic.py:SemanticWindowCheck): sliding windows of the call
  embedded with a multilingual embedding model (served via an OpenAI-compatible `/v1/embeddings`
  endpoint, e.g. vLLM/llama.cpp with bge-m3 or multilingual-e5; `fake` embedder for tests), compared to
  per-family "misconduct descriptions" from criteria.yaml; top windows above a similarity threshold
  become candidates, then optionally verified by the same G-Eval window prompt. Finds level-2 cases
  that contain no keyword at all.

## 1c. Data discipline

- 30 dialogues x (clean, noisy). Clean and noisy of one dialogue never split (`data.split_dialogues`).
- `config/splits.yaml` locks a HOLDOUT fold (6 dialogues, stratified by label) that prompt / weight /
  threshold tuning never sees; `eval --split dev` (default for tuning, CV over the remaining folds) vs
  `eval --split holdout` (final honest number, logged to `runs/holdout_log.jsonl` every time it is
  run so peeking is visible). Few-shot pools and learned fusion fit only on dev dialogues.
- Synthetic calls are extra dev/training data, never mixed into the holdout.

## 2. Evaluation of views

- `callguard asr-eval -c <profile> [--views gsw,de] [--calls ...]` (callguard/eval_asr.py): WER/CER
  per view against references, normalized (lowercase, punctuation, umlaut fold, numbers as written).
  gsw views vs reference scripts; de/en views vs `ref_de`/`ref_en` pseudo-references (flagged as
  pseudo). Uses `jiwer`. Breakdown clean/noisy, per level. Plus **keyword-spot recall**: the
  expected-assessment files list every annotated keyword spot (`Keywordstellen: K04 'vor de Meldig'
  T008 ...`); per view, how many of those spots the keyword matcher still finds in the ASR output -
  an ASR metric that measures exactly what the checks need, independent of dialect spelling.
  Baseline rows: vanilla `openai/whisper-large-v3` and `-turbo` (CT2 via faster-whisper) next to the
  Swiss German fine-tunes.
- `callguard experiment experiments/<name>.yaml` (callguard/experiments.py + commands/experiment.py):
  a matrix of variants (each = profile + `--set` overrides), shares all caches, per variant: detection
  metrics (flag P/R/F1, false-alarm rate, miss rate, alarm F1, review recall), dialogue-fold CV,
  suggested threshold, ASR metrics of the views involved, cost (seconds per call by stage, LLM calls).
  Writes `runs/experiments/<name>/{summary.json,summary.md,<variant>/report.*}`. `--dry-run` lists what
  would be computed. UI page "Experiments" compares variants.
- Shipped specs: `experiments/smoke.yaml` (demo-offline, runs on the laptop), `views.yaml` (de vs gsw vs
  de_from_gsw vs en_from_de vs en_from_gsw vs en_speech vs multi-view ensemble), `oracle_views.yaml`
  (ref_gsw vs ref_de vs ref_en: ceiling, no audio), `checks_ablation.yaml` (keywords / +patterns /
  +llm_judge / +geval / all), `asr_models.yaml` (Swiss German Whisper variants), `llm_models.yaml`.

## 3. Stretch goals

| goal | modules | CLI | UI |
|---|---|---|---|
| Speaker separation | done (diarization/sherpa + roles) | | role labels |
| Notify the right person | callguard/routing.py, sinks/notify.py, config/routing.yaml, config/directory.yaml | `callguard route <call>` | page Notifications + detail panel "Routed to" |
| Feedback -> better thresholds/keywords | callguard/feedback.py | `callguard feedback add/list/suggest` | detail panel buttons + page "Feedback & tuning" (apply threshold -> config/tuning.yaml overlay) |
| Patterns across calls | checks/entities.py (advisor/customer/companies via LLM + regex), callguard/patterns.py, optional sidecar `<audio>.meta.json` | `callguard patterns` | page Patterns + detail panel "Entities" |
| Operating concept | docs/OPERATING_CONCEPT.md, docs/ARCHITECTURE.md | | |
| Outcept trigger API | done (sinks/outcept.py) | | deep links |
| Audit trail | provenance in CallResult.meta + runs/<profile>/audit.jsonl | | detail expander "Provenance" |
| Learned fusion | fusion/learned.py (numpy logistic regression on cached CheckResults) | `callguard fit-fusion` | |
| Few-shot judge | llm_judge `few_shot: {k, pool_dialogues}`; eval excludes pool dialogues | | |
| Synthetic calls | callguard/synth/ (scenarios, LLM script writer, TTS plugins, render, augment) | `callguard synth scripts/audio`, `callguard augment` | |
| ASR fine-tuning | finetune/ (prepare_data, train_whisper, convert_ct2, README), extra `train` | `python finetune/...` on GPU host | |

### Routing (`config/routing.yaml`)

```yaml
teams:
  market_surveillance: {name: Market Surveillance, email: market-surveillance@bank.example}
  fraud_desk: {name: Fraud & Security, email: fraud@bank.example}
  data_protection: {name: Data Protection, email: dpo@bank.example}
  compliance_desk: {name: Compliance Desk, email: compliance@bank.example}
rules:                                   # first match per family; all matching rules' teams get notified
  - {when: {family: trade}, notify: [market_surveillance]}
  - {when: {family: access}, notify: [fraud_desk]}
  - {when: {family: disclosure}, notify: [data_protection]}
  - {when: {label: review}, notify: [compliance_desk]}
  - {when: {pattern: repeat_advisor}, notify: [compliance_desk], cc_supervisor: true}
supervisor_cc_on: [alarm]
```
`config/directory.yaml`: fictional advisors (names as they appear in the case calls) -> supervisor, team.
NotifySink channels: `outbox` (runs/<profile>/outbox.jsonl, always), `webhook` (generic JSON POST),
`smtp` (optional; MailHog-friendly). Message = label, family, deep link (`?call=..&t=..`), passages with
times + reasons, snippet paths.

### Feedback (`runs/<profile>/feedback.jsonl`)

`FeedbackItem(call_id, ts, user, verdict: confirmed|false_alarm|missed|should_review|not_review, family?,
passage_index?, comment)`. `suggest()`: derive labels from feedback (+ ground truth where present),
re-run fusion sweep -> suggested threshold with expected FP/FN change; per-keyword precision
(hits on confirmed vs false-alarm calls) -> "consider disabling K05"; per-check reliability.
Applying writes `config/tuning.yaml` (overlay with fusion threshold/weights; loaded by load_config
after the profile when `paths.tuning` exists; shown in provenance).

### Patterns

`EntityCheck` (type `entities`, weight 0, scores no family): advisor name, customer name, companies /
securities, third parties; regex for greetings ("da isch d Simone Wenger", "hier ist ...") + optional LLM
JSON. Sidecar `<audio>.meta.json` (advisor_id, customer_id, started_at, line) wins when present
(target picture: the recording system provides it). `patterns.analyze(results)`: per advisor / customer
/ company: calls, alarms, reviews, mean score, families; flags: advisor flag-rate Wilson lower bound
above population rate (min 3 calls), same company in trade-flagged calls of different customers,
repeated family per customer. Feeds routing rule `pattern: repeat_advisor`.

## 4. Synthetic data kit (`callguard/synth/`)

- `config/synth_scenarios.yaml`: per family, scenario seeds with **twins** (alarm / harmless / review
  variants differing only in context, like the case's Stufe2 pairs), dialect region, length, speakers.
- `synth/scripts.py`: LLM writes scripts in the case layout (`Transkript/`, `Skript_mit_Sollbewertung/`
  header: Testziel, Ereignis, Bearbeitung, Begründung, Belege) under `data_synth/<set>/`; validated with
  `data.parse_turns` / `parse_expected`. Call ids `Synth_<family>_<nnn>-K1`.
- Plugin kind `tts`: `TTS.synthesize(text, voice) -> np.ndarray (16 kHz float32)`; backends per research
  (`fake` for tests). `synth/render.py`: script -> two voices -> turns with pauses -> `Audio/*.wav`.
- `synth/augment.py`: telephone channel (8 kHz band-limit 300-3400 Hz, G.711 mu-law/A-law in numpy,
  optional ffmpeg GSM/AMR, noise at SNR, gain, packet loss) -> `K2`-style noisy variants.
- `data.load_calls` accepts several data dirs and non-case call ids (level 0).

## 5. Audit / provenance

`CallResult.meta["provenance"] = {created_at, config_name, config_hash, tuning_hash, code_version,
plugins: {views: {...}, checks: {...}, fusion: {...}}, models: {...}}` and an append-only
`runs/<profile>/audit.jsonl` (decision events, feedback events, keyword/criteria/tuning saves).

## 6. Extension points to keep (so the team can plug in more)

- CLI: `callguard/commands/<name>.py` modules each define `register(app: typer.Typer)`; `cli.py` imports
  the list `COMMAND_MODULES`.
- UI: pages listed in `callguard/ui/pages_registry.py` (title, icon, module); detail-page panels listed
  in `callguard/ui/panels/__init__.py` (`render(result, session)` functions).
- New plugin kinds: `translator`, `tts` (plus asr, diarizer, check, fusion, llm, sink).

## 7. Architecture experiments (all wired so the overnight run can switch them by config)

| id | idea | module / config | hypothesis | measured by |
|---|---|---|---|---|
| A1 | **Fact sheet + policy table** | checks/facts.py:FactSheetCheck + `config/policy_table.yaml` | LLM extracts per-family facts (enum yes/no/unclear + evidence ids), an officer-editable decision table maps facts -> alarm/review/no_alert. Mirrors the case's present/absent/undetermined + "Offen:" structure; unclear facts become review | dev-CV flag F1, review recall, traceability |
| A2 | **Cascade** | `cascade:` block in config, pipeline stage gating | cheap recall stage (keywords, patterns, semantic windows, per-call triage prompt "which families could apply?") gates the expensive checks per family | F1 vs cost (LLM calls / call) |
| A3 | **Audio-LLM verification** | checks/audio_llm.py:AudioLLMCheck (OpenAI-compatible audio input via vLLM; Voxtral Mini 3B / Qwen2.5-Omni-7B) | listening to the suspicious window avoids ASR error propagation; Swiss German understanding UNKNOWN | F1 on candidate windows, agreement with text judges |
| A4 | **LLM transcript correction** | translate/correct.py:LLMCorrector as a view (`from: [de, gsw, de_vanilla]`, multi-source) | an LLM fusing 2-3 ASR hypotheses repairs key-word errors | keyword-spot recall, detection F1 |
| A5 | **Calibrated + conformal abstention** | fusion/calibrated.py (Platt per check, split-conformal over dev folds) | prediction set with >1 label -> review: principled "knows when unsure" | review recall, error rate on non-abstained, coverage |
| A6 | **Prosecutor / defender / judge** | checks/debate.py:DebateCheck | adversarial argumentation cuts false alarms on harmless twins | FP on twins (D03, C05, C08, C10, C11, C14, C15) |
| A7 | **Role-aware checks** | check param `roles: [customer]` (keywords exists; add to LLM checks: only those turns + context) | less confusion who did what | per-family precision |
| A8 | **Twin few-shot** | llm_judge `few_shot: {k, pool: dev, twins: true}` | contrastive pairs teach the decisive context | dev-CV F1 (pool dialogues excluded from scoring) |
| A9 | **Sweeps** | experiments/llm_models.yaml, criteria language de/en, views | prompts vs model size vs view | leaderboard |
| A10 | **Denoise front end** | audio pre-processor plugin kind `preprocess` (DeepFilterNet, untested) before ASR | closes clean/noisy gap | noisy-vs-clean F1 / keyword-spot recall |

UX: **evidence timeline** (call-length bar, markers per check/family, click -> snippet) and **"why not an
alarm"** explanation for keyword-heavy harmless calls (the strongest counter-evidence + which
`harmless` note / not_alarm_when rule applied).

## 8. Overnight autonomous research harness (`research/`)

Goal: an agent runs the experiment backlog all night, implements new hypotheses, keeps what improves
dev-CV, and writes a morning report. **Default: the agent runs ON the GPU host** (Claude Code / T3 Code
in `~/sprintd`, a clone of github.com/be-lang/sprintd), so a sleeping laptop or a dropped connection
cannot kill the night; the laptop only monitors (ssh, UI over the tailnet, `git pull` of branch
`overnight`, which the agent pushes after every round). Remote mode (laptop agent driving the GPU via
`run_on_host.sh`) stays supported for daytime work. Pieces:

- `research/AGENT.md` - operating manual: objective (maximize dev-CV flag F1 with false-alarm rate cap,
  review recall, keep traceability), the rules (holdout never touched except one final run, logged;
  one hypothesis per git branch `exp/<id>`, merge into `overnight` only if dev-CV improves beyond noise:
  >= 1 more correct dialogue AND no FAR increase above cap; every run's numbers to the journal; never
  delete caches; stop GPU jobs cleanly), how to run things remotely, how to read results.
- `research/queue.yaml` - prioritized hypothesis backlog (A1-A10, view comparisons, ablations, ASR model
  sweeps, fine-tune trial, synthetic-data generation) with status (todo/running/done/rejected),
  experiment spec path, expected cost; the agent appends new hypotheses it invents.
- `research/journal.md` (append-only, timestamped) and `research/leaderboard.md` (generated by
  `callguard leaderboard` from runs/experiments/*/summary.json: variant, dev-CV F1, FAR, miss, review
  recall, cost/call, commit).
- `scripts/remote/run_on_host.sh "<command>"` - sync code to the GPU host, run the command there in the
  project env (with cuda_env), stream logs, pull `runs/` + `.cache/` back.
- A saved workflow `.claude/workflows/overnight-research.js` (args: {rounds, deadline_iso, gpu_host}):
  each round = planner (reads leaderboard/journal/queue, picks the next hypothesis, writes a precise
  experiment plan) -> researcher (implements on a branch, runs offline tests, runs the experiment on the
  GPU via run_on_host, records results, merges or rejects) -> ideator in parallel (reads results,
  proposes up to 3 new hypotheses into the queue) -> repeat; stops at deadline_iso or rounds; final
  round writes `research/MORNING_REPORT.md` (what was tried, what won, numbers, recommended config,
  next steps) and runs the holdout exactly once on the recommended config.

## 9. Research outputs for the team (compare, decide, defend)

The point of the overnight run is not one best number but **evidence the team can argue with**.

- `research/QUESTIONS.md` - the research questions, each answered in `research/findings/RQ<n>.md`:
  RQ1 which view (gsw / de / de_from_gsw / en_from_de / en_from_gsw / en_speech / ensemble) detects best;
  RQ2 Swiss German Whisper fine-tunes vs vanilla Whisper (WER/CER, keyword-spot recall, detection);
  RQ3 does dialect output need less fine-tuning than Standard German output;
  RQ4 which checks carry the decision (ablation: keywords, patterns, keyword_context, semantic_windows,
  llm_judge, geval, facts, debate);
  RQ5 fact sheet + policy table vs free judge vs G-Eval (accuracy, review handling, traceability);
  RQ6 model size (7B vs 14B, later 30B+) vs prompt/criteria language;
  RQ7 does keyword_context fix the harmless keyword calls (D03 & twins) without losing level-1 alarms;
  RQ8 clean vs noisy gap, does denoising help;
  RQ9 calibrated/conformal abstention: review recall vs error rate on decided calls;
  RQ10 do synthetic calls help (few-shot pools, learned fusion);
  RQ11 does a LoRA fine-tune on dev-fold case audio help on held-out folds;
  RQ12 cost per call minute (GPU seconds) -> production sizing.
- Every finding file has the same shape: question, setup (commit, config, data split), result table,
  **uncertainty** (paired bootstrap over dialogues: 95% CI of the F1 difference between options;
  McNemar on per-call correctness; with 30 dialogues small differences are noise - say so),
  **per-call disagreement table** (which calls flip between options, with the passage and both
  reasons), cost, qualitative examples, recommendation, **strongest counter-argument** (devil's
  advocate: when would the other option be the better choice), what would change our mind.
- `callguard report` builds `research/report/` (markdown + PNG charts: F1 / FAR / miss per option with
  CIs, cost vs quality scatter, clean vs noisy, per-level heat map, threshold curves) from
  `runs/experiments/*/summary.json`; the UI "Experiments" page shows the same interactively.
- `research/DECISIONS.md` - ADR-style decision records (context, options, evidence links, decision,
  consequences, dissent) for: ASR model, view, check set, LLM, fusion, threshold policy.
- `research/MORNING_REPORT.md` - one page for teammates: what was tried, what won and by how much
  (with CIs), what is still open, recommended config for Sunday, the one holdout number.
