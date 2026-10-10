#!/usr/bin/env bash
# Staged batch run on ONE 12 GB GPU (Sunday scoring): 1) Whisper transcribes every call with vLLM stopped,
# 2) the LLM is served alone and the checks run on the cached transcripts. Lets a large-v3 ASR + a 14B LLM share
# a card that cannot hold both at once. Everything is cached, so re-running is cheap.
# Usage: scripts/run_staged.sh [profile=recommended] [llm-model=Qwen/Qwen2.5-7B-Instruct-AWQ] [extra callguard batch args...]
#   e.g. scripts/run_staged.sh recommended Qwen/Qwen2.5-14B-Instruct-AWQ
set -euo pipefail
cd "$(dirname "$0")/.."
PROFILE="${1:-recommended}"; MODEL="${2:-Qwen/Qwen2.5-7B-Instruct-AWQ}"; shift $(( $# > 2 ? 2 : $# ))
source scripts/remote/cuda_env.sh
if [[ -f runs/logs/vllm.pid ]] && kill -0 "$(cat runs/logs/vllm.pid)" 2>/dev/null; then
  echo "stage 0: stopping vLLM to free the GPU for Whisper"; kill "$(cat runs/logs/vllm.pid)"; sleep 15
fi
echo "stage 1: ASR (all calls, cached)"; uv run python scripts/research/asr_sweep.py -c "$PROFILE" --tag "staged-$PROFILE"
case "$MODEL" in
  *14B*) EXTRA="--kv-cache-dtype fp8 --enforce-eager --max-num-seqs 2 --enable-chunked-prefill --max-num-batched-tokens 1024" \
           scripts/remote/swap_llm.sh "$MODEL" 0.90 6144 ;;
  *)     EXTRA="--max-num-seqs 24" scripts/remote/swap_llm.sh "$MODEL" 0.80 16384 ;;
esac
echo "stage 2: diarization roles + checks + fusion + sinks"; uv run callguard batch -c "$PROFILE" "$@"
echo "done: results in runs/$PROFILE/ (UI: uv run callguard ui -c $PROFILE)"
