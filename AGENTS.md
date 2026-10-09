# callguard: notes for any coding agent (mirror of CLAUDE.md for Codex-style harnesses)

**New session? Read `START_HERE.md` first.** It says what to do next (setup, build, overnight research).
Live state of every component: `docs/STATUS.md`. The case brief: `docs/CASE.md`.

## What this is

Hackathon prototype (sprintd Zurich, 9-11 Oct 2026, Inventx/Outcept case) that checks every Swiss
German bank phone call for compliance problems and turns it into alarm / review / no_alert with audio
snippets, timestamps and reasons. Team of 3. Final submission **Sunday 2026-10-11 08:30**, pitch 09:00.

Pipeline: audio -> ASR (views: gsw / de / en) -> diarization + advisor/customer roles -> pluggable checks
(keywords, patterns, LLM judge, G-Eval, ...) -> fusion (threshold, review band, uncertainty) -> passages
+ snippets -> sinks (result.json, Outcept trigger API) -> Streamlit officer UI, CLI, eval.

## Commands

```bash
uv sync --extra asr --extra diarize --extra ui --extra dev   # app env (GPU host: see docs/REMOTE_GPU.md)
uv run pytest -q -m "not slow"         # offline tests, must stay green (~1 min)
uv run callguard --help                # plugins, transcribe, run, batch, eval, watch, ui, doctor, ...
uv run callguard doctor -c <profile>   # checks LLM / ASR / models / data before a long run
uv run callguard batch -c demo-offline # full chain with zero models (reference scripts + fake LLM)
```

Profiles in `config/`: `local` (laptop CPU), `gpu-12gb` (RTX 4070 host), `remote` (laptop app, models on
the GPU host over Tailscale), `gpu` (event GPUs), `oracle` (reference scripts instead of ASR),
`fast` (rule checks only), `demo-offline` (no models at all). `--set a.b=c` overrides anything.

## Layout

- `src/callguard/` core: `types.py` (data model), `plugins.py` (base classes), `registry.py` (plugin
  lookup; `type: "module:Class"` works without registering), `config.py`, `context.py`, `pipeline.py`,
  `cache.py` (content-addressed: only changed stages rerun), `data.py` (case dataset + dialogue folds),
  `families.py` (keyword list + criteria). Plugins in `asr/ diarization/ checks/ llm/ fusion/ sinks/`.
- `config/criteria.yaml` (per-family rules the LLM checks judge against), `config/keywords.json`
  (the case's keyword list, editable in the UI).
- `docs/design/v2_plan.md` the build spec (views, experiments, new checks, stretch goals, harness).
- `docs/research/*.md` model research (dialect ASR, translation, TTS/synthetic, fine-tuning on 12 GB).
- `research/` the overnight research harness: protocol, questions, queue, journal, findings, report.

## Rules (non-negotiable)

1. **Self-hosted only.** No cloud APIs (OpenAI, ElevenLabs, Deepgram, ...) in transcription or checks.
   Open models on our own GPUs only.
2. **No hidden hints.** Never feed file names, call ids, reference scripts or expected labels into the
   audio pipeline. The `reference` ASR / `ref_*` views are oracle experiments, never the submission.
3. **Holdout discipline.** Tune only on dev folds (`config/splits.yaml`). The holdout is evaluated once
   per candidate final config and every holdout run is logged. Clean and noisy versions of one dialogue
   always stay in the same fold.
4. **Evidence over vibes.** Every claim about "better" needs numbers from `callguard experiment` with
   confidence intervals; 30 dialogues means small differences are noise. Say so.
5. **Don't break the seams.** New models / checks / views are plugins + config, not edits to the core.
   Keep `uv run pytest -q -m "not slow"` green. Keep cache keys stable (transcripts are expensive).
6. Commit small, descriptive commits; push research results to branch `overnight` (code fixes that
   should reach the team: `main`). Never commit data_upstream/, models/, .cache/, runs/ or secrets.
7. Don't run `pkill -f <pattern>` (it matches your own shell); kill by PID.
