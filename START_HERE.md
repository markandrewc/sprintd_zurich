# START HERE: overnight session on the GPU host

You are an autonomous agent running on the team's GPU host (RTX 4070, 12 GB VRAM) inside a clone of
this repo. The user is away and **will not answer questions**. Work through the night until the user
returns (plan for **Saturday 2026-10-10, ~08:00 local time**; check `date`). Make reasonable decisions,
write them down in `research/journal.md`, and keep going. Do not stop because one thing is blocked:
log it, skip it, take the next item.

## The mission

By morning the team (3 people) must be able to **compare the options and defend the choices** for the
Sunday submission with evidence, not opinions:

- Which transcript view is best for detection: Swiss German dialect text (`gsw`), Standard German (`de`),
  translations (`de_from_gsw`, `en_from_de`, `en_from_gsw`), Whisper speech-to-English, or an ensemble?
- Which ASR model (Swiss German fine-tunes vs vanilla Whisper baseline, dialect-output models)?
- Which checks carry the decision (keywords, patterns, keyword-context G-Eval, semantic windows,
  LLM judge, G-Eval, fact sheet + policy table, debate, ...) and which LLM size?
- How well does the system know when it is unsure (review), and what threshold policy should we use?

The deliverables are in `research/` (see "Morning deliverables"). Quality of evidence matters more
than the number of experiments: confidence intervals, per-call disagreement tables, honest caveats.

## Step 0: orient (every time you start or resume)

```bash
git pull --rebase            # the laptop build may have pushed new code / docs
date; nvidia-smi
```

Read, in this order: `CLAUDE.md` (rules), `docs/CASE.md` (what the jury wants), `docs/STATUS.md` (what
exists, what is still to build), `research/AGENT.md` (the research protocol), `research/QUESTIONS.md`,
`research/queue.yaml`, the tail of `research/journal.md`. Then continue from where the journal says the
last session stopped. All state lives in files, so a fresh session (after a crash or a full context)
picks up exactly where the last one left off.

## Step 1: bring-up (once; skip if the journal says it is done)

Follow `docs/REMOTE_GPU.md`, **mode C** (agent runs on the GPU host). If that file is missing, the short
version:

1. `uv sync --extra asr --extra diarize --extra ui --extra dev`; clone the case data:
   `git clone --depth 1 https://github.com/Outcept/inventx-case-study data_upstream/inventx-case-study`.
2. CUDA libs for CTranslate2 (faster-whisper): `uv pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*"`
   and export `LD_LIBRARY_PATH` to their `lib/` dirs (`scripts/remote/cuda_env.sh` if present).
3. Models: `scripts/download_models.sh local` (Swiss German Whisper turbo int8 + diarization; the
   laptop's 1.5B GGUF is not needed here).
4. LLM: separate venv so torch/vllm never touch the app env:
   `uv venv .venv-vllm --python 3.12 && uv pip install --python .venv-vllm vllm`, then serve
   `Qwen/Qwen2.5-7B-Instruct-AWQ` as `--served-model-name callguard-llm --max-model-len 16384
   --gpu-memory-utilization 0.70 --enable-prefix-caching --port 8000` (`scripts/remote/serve_models.sh`
   if present). Leave ~3 GB VRAM for Whisper.
5. `uv run callguard doctor -c gpu-12gb` must be all OK. Then one call end to end:
   `uv run callguard run data_upstream/inventx-case-study/data/Audio/Stufe1_D02-K1.wav -c gpu-12gb`.
6. Journal: what worked, timings (seconds per call per stage), VRAM use.

Troubleshooting: vLLM OOM -> lower `--gpu-memory-utilization` / `--max-model-len`, or use the llama.cpp
path in `docs/REMOTE_GPU.md`; `libcudnn` errors -> LD_LIBRARY_PATH; Windows host -> work inside WSL2.
If vLLM cannot be made to work in 45 minutes, switch to llama.cpp server (OpenAI-compatible, GGUF
Q4_K_M) and move on; set `json_mode: json_object_schema` for llama-cpp-python.

## Step 2: transcription sweep (the slowest GPU work; start it early, in the background)

Transcripts are cached per (audio, ASR params), so each model transcribes each call once and every
later experiment reuses it. Transcribe **all 60 calls** with each ASR candidate in `research/queue.yaml`
(group `asr`): the default Swiss German turbo int8, the larger Swiss German fine-tunes, the vanilla
Whisper baseline, the dialect-output model(s) and Whisper `task: translate` (English). Model ids and
licences: `docs/research/dialect_asr.md`. Run them one after another in `tmux` with logs in
`runs/logs/`; while they run, do Step 3.

## Step 3: build the v2 components (you own this; nobody else is building)

`docs/STATUS.md` "To build" lists every component in priority order with its spec section in
`docs/design/v2_plan.md`. You build them on this host while the transcription sweep (Step 2) runs.
Two ways:
- **Workflow** (if your harness supports Claude Code workflows): run `.claude/workflows/v2-build.js`
  with args `{root: "<abs path of this repo>"}`. It builds in stages (1: views, translators, holdout
  lock, hooks, scaffolds, stats + overnight harness; 2: experiment runner, asr-eval, report, new
  checks, fusion variants; 3: UI, routing/feedback/audit, patterns, synth + fine-tune kits, docs;
  then integration, review, fixes) and commits + pushes `main` after each stage.
- **By hand**: same order; the workflow file's per-stage prompts are the detailed spec. For each item:
  implement, offline tests, `uv run pytest -q -m "not slow"` green, update `docs/STATUS.md`, commit to
  `main`, push.

Pacing (the research is the point of the night): items 1-5 (views, holdout lock, experiment runner,
asr-eval, statistics/report) and the harness first - **start the research loop (Step 4) as soon as
those exist, at the latest ~03:00**, using whatever checks exist then. Build items 6-10 between research
rounds (each new check becomes a research item when it lands). Items 11-15 (UI polish, stretch goals,
kits) only if time remains after the core research questions have answers; note in the journal what
was skipped. Builds and tests run offline (demo profiles, fake LLM) - GPU time belongs to experiments.

## Step 4: the research loop (the main job of the night)

Follow `research/AGENT.md`. In short, repeat until the morning:

1. `git pull`; read the leaderboard and the journal tail; pick the highest-priority `todo` item in
   `research/queue.yaml` whose dependencies exist (mark it `running`).
2. Write the experiment spec (`experiments/<id>.yaml`), run it on **dev folds only**
   (`callguard experiment ...`), with logs.
3. Analyse: metrics with 95% CIs (paired bootstrap over dialogues), per-call flips, cost, examples.
4. Write/update `research/findings/RQ<n>.md` for every research question it informs; append to the
   journal; regenerate the report (`callguard report`) and `research/MORNING_REPORT.md`.
5. Mark the item `done` (or `rejected` with why); add up to 3 new hypotheses it suggested.
6. `git add research experiments docs; git commit; git push origin HEAD:overnight`.

If `/loop` is available in your harness, run the loop with it so you pace yourself and never stop:
`/loop Follow START_HERE.md: orient, then run the next research step, then schedule the next one.`
Otherwise just keep iterating. When the queue is empty, generate new hypotheses from the weakest
spots in the latest results (`research/AGENT.md` "When the queue runs dry").

## Step 5: morning deliverables (keep them current after every round, finalize by 07:30)

- `research/MORNING_REPORT.md` - one page for the team: what was tried, what won and by how much (CIs),
  what is still open, the recommended config for Sunday, the **single holdout run** of that config.
- `research/findings/RQ*.md` - one per research question, each with the strongest counter-argument.
- `research/DECISIONS.md` - decision records (ASR model, view, checks, LLM, fusion, threshold policy).
- `research/report/` - charts + tables (`callguard report`), `research/leaderboard.md`.
- `config/recommended.yaml` - the winning profile, runnable as is.
- Leave vLLM and the ASR server running so the team can use them in the morning; note how to stop them.

## Starting this session (for the human)

On the GPU host: `git clone git@github.com:be-lang/sprintd.git ~/sprintd && cd ~/sprintd`, open a
Claude Code / T3 Code session there (in `tmux` so it survives disconnects, power-save off), and paste:

> Read START_HERE.md and follow it. You are the overnight research agent on this GPU host. Work
> autonomously until 07:30, never wait for me, log every decision in research/journal.md, and push
> results to the `overnight` branch after every round.

or, with self-pacing: `/loop Read START_HERE.md and continue the overnight research from the current state.`
