#!/usr/bin/env bash
# Staged run on ONE 12 GB GPU (Sunday scoring): 1) Whisper transcribes every call with vLLM stopped,
# 2) the LLM is served alone and diarization roles + checks + fusion + snippets + sinks run on the cached transcripts.
# Lets large-v3 ASR + the LLM share a card that cannot hold both at once. Everything is cached: re-runs are cheap.
#
# Usage: scripts/run_staged.sh [profile=recommended] [llm=Qwen/Qwen2.5-7B-Instruct-AWQ] [audio-folder]
#   audio-folder: any folder of .wav files (ANY file names; default: the profile's data_dir/Audio). Results:
#   runs/<profile>/<file-stem>/result.json (+ snippets), UI: uv run callguard ui -c <profile>
#   e.g. scripts/run_staged.sh recommended Qwen/Qwen2.5-7B-Instruct-AWQ /data/hidden_test/Audio
# Note: `callguard batch` only picks up case-style names (Stufe1_D02-K1.wav); this script uses `transcribe` + `run`
# per file, so arbitrary names work. File names are only used as call ids, never as hints to the checks.
set -euo pipefail
cd "$(dirname "$0")/.."
PROFILE="${1:-recommended}"; MODEL="${2:-Qwen/Qwen2.5-7B-Instruct-AWQ}"; FOLDER="${3:-}"
source scripts/remote/cuda_env.sh
if [[ -z "$FOLDER" ]]; then
  FOLDER=$(uv run python -c "from callguard.config import load_config; print(load_config('$PROFILE').paths.resolve('data_dir'))")/Audio
fi
mapfile -t FILES < <(find "$FOLDER" -maxdepth 1 -name '*.wav' | sort)
echo "${#FILES[@]} audio files in $FOLDER -> profile $PROFILE, LLM $MODEL"
[[ ${#FILES[@]} -gt 0 ]] || { echo "no .wav files found" >&2; exit 1; }
if [[ -f runs/logs/vllm.pid ]] && kill -0 "$(cat runs/logs/vllm.pid)" 2>/dev/null; then
  echo "stage 0: stopping vLLM to free the GPU for Whisper"; kill "$(cat runs/logs/vllm.pid)"; sleep 15
fi
echo "stage 1: ASR (cached per audio file)"
for f in "${FILES[@]}"; do uv run callguard transcribe "$f" -c "$PROFILE" --no-diarize > /dev/null; echo "  asr ok  $(basename "$f")"; done
case "$MODEL" in
  *14B*) EXTRA="--kv-cache-dtype fp8 --enforce-eager --max-num-seqs 2 --enable-chunked-prefill --max-num-batched-tokens 1024" \
           scripts/remote/swap_llm.sh "$MODEL" 0.90 6144 ;;
  *)     EXTRA="--max-num-seqs 24" scripts/remote/swap_llm.sh "$MODEL" 0.80 16384 ;;
esac
echo "stage 2: roles + checks + fusion + snippets + sinks"
uv run callguard run "${FILES[@]}" -c "$PROFILE"
echo "done: results in runs/$PROFILE/ (UI: uv run callguard ui -c $PROFILE)"
