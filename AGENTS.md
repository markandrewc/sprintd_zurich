# Sherlock Phones (`callguard`): notes for a coding agent working in this repo

Start with `GUIDE.md` (install, run a folder of .wav files, dashboard, scoring) and `RESULTS.md` (what we measured
and how). The case brief is `docs/CASE.md`.

Production chain = profile `sherlock` (`config/sherlock.yaml`): Whisper large-v3 Swiss German -> sherpa-onnx speakers
-> Qwen3.8-27B 3-bit roles + reader A -> Kev-4B reader B + masking passages -> fact policy -> policy table rules ->
keywords/patterns -> fusion. `scripts/run_testset.sh <wavs> <name>` runs it staged on one GPU.

`fraud_analysis/` (+ `shared/`) is the Kev-4B service code from our first prototype: reader B runs it with its own env
`.venv-kev` via `scripts/remote/serve_kev.py` (GUIDE.md §3). The rest of the prototype is at tag `prototype`.

## Commands
```bash
uv sync --extra asr --extra diarize --extra ui --extra dev
uv run pytest -q -m "not slow"                   # offline tests, must stay green
scripts/run_testset.sh /path/to/wavs NAME         # new calls -> runs/testset-NAME/
uv run callguard api -c sherlock --set paths.runs_dir=runs/testset-NAME --set paths.data_dir=runs/testset-NAME/.no_case_data --port 8600   # dashboard API
(cd frontends/swiss && npm ci && npm run dev -- --port 8605)                          # dashboard
```

## Rules
1. Self-hosted models only; no cloud API in transcription or checks.
2. Never feed file names, call ids, reference scripts or expected labels into the audio pipeline. `oracle` /
   `demo-offline` profiles read scripts instead of audio: tests and UI work only, never results.
3. Results are only what the pipeline produces from the .wav files; label numbers come from `scripts/score_results.py`
   after the run.
4. Never commit `data_upstream/`, `models/`, `.cache/`, `runs/` or secrets. Stop processes by PID, never `pkill -f`.
