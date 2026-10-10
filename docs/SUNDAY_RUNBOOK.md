# Sunday runbook (hidden test set, demo)

Written at the end of the overnight session (2026-10-10 05:40). Evidence for every choice: `research/MORNING_REPORT.md`.

## 0. Pre-flight (5 min)
```bash
cd ~/repos/sprintd && git pull
source scripts/remote/cuda_env.sh            # cuBLAS/cuDNN for faster-whisper (GPU host)
scripts/remote/swap_llm.sh Qwen/Qwen2.5-7B-Instruct-AWQ 0.80 16384   # if vLLM is not running
uv run callguard doctor -c recommended       # expect: OK 29  SKIP 1 (Outcept trigger disabled)
uv run pytest -q -m "not slow"               # ~35 s, must be green
```

## 1. Process the hidden test set (any file names, one 12 GB GPU)
```bash
scripts/run_staged.sh recommended Qwen/Qwen2.5-7B-Instruct-AWQ /path/to/hidden/Audio
```
- **Stage 1:** stops vLLM and transcribes every `.wav` with Whisper large-v3 (MIT, ~2.4 GPU-s per audio minute).
- **Stage 2:** restarts the 7B and runs diarization roles, facts, keywords, patterns, fusion and snippets.
- **Speed:** about 30 s per call for small batches (3 calls took 44 s, restarts included). ~18 calls ≈ 6-10 min.
- **Results:** `runs/recommended/<file-stem>/result.json` plus `snippets/*.wav`.
- **File names:** they are only call ids; nothing in the checks reads them (case rule).
- **Don't use `callguard batch` for this:** it only picks up case-style names (`Stufe1_D02-K1.wav`) and silently
  skips the rest.
- **If they hand over transcripts or audio in a different layout:** convert to a folder of 16 kHz mono `.wav` first
  (`sox in.ext -r 16000 -c 1 out.wav`).

**Fallback (single pass, no restarts, e.g. if the GPU is shared):**
```bash
uv run callguard run /path/to/hidden/Audio/*.wav -c recommended-turbo
```
On dev this scores AUC 0.85 vs 0.87, FAR 14%, miss 23% vs 15%. Results go to `runs/recommended-turbo/`.

## 2. Score against labels (if the organisers give them)
```bash
# labels.csv: call_id,expected   (alarm | review | no_alert; call_id = wav file stem)
uv run python scripts/score_results.py runs/recommended labels.csv
```
- **Output:** flag P/R/F1, false-alarm rate, miss rate, alarm F1, review recall, 3-class accuracy, and a per-call table.
- **Check:** on our dev labels it reproduces the experiment numbers exactly.
- **Report AUC/FAR, not flag F1:** flagging everything scores flag F1 0.70 on our data.

## 3. Show it (demo: `research/DEMO.md`)
```bash
uv run callguard ui -c recommended            # http://localhost:8501 ; works without GPU (re-fusion only)
```
Demo calls:
- **Alarm with snippet:** Stufe1_D02-K1.
- **Harmless call with keywords + "Warum kein Alarm?":** Stufe1_D03-K1.
- **Review + "Offene Fakten" panel:** Stufe3_C17-K3. Answering "Ja (gültig)" turns it into an alarm.
- **Threshold demo:** move from 0.55 to 0.50 or 0.95.
- **Keyword demo:** K10 off.

Back up `config/keywords.json` before the keyword click: `cp config/keywords.json /tmp/`.

## 4. What to say about quality (honest numbers)
- **Dev (48 calls, cross-validated):** flag AUC 0.87 [0.72, 0.99], false alarms 14%, misses 15%, 3-class 79%.
  The v1 keyword + free-LLM system scored 0.68 with 86% false alarms.
- **Holdout (12 calls):** 0 false alarms and alarm F1 0.67, but 3 logged looks in total, so it is a sanity check.
- **Expected on new calls:** ~0.75-0.80 AUC, because the fact wording was tuned on dev; paraphrased questions drop
  to 0.72.
- **Weak spots:** open review cases and the splitting family. Table v3 (`config/policy_table_v3.yaml`) is the optional
  "strict review" policy.

## 5. Stop / clean up
- **Stop vLLM:** `kill $(cat runs/logs/vllm.pid)`. Never use `pkill -f` (it matches its own shell).
- **Logs:** `runs/logs/`.
- **Never commit:** `runs/`, `.cache/`, `models/`, `data_upstream/`.
