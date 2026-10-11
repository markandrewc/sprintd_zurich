#!/usr/bin/env bash
# Swap the served LLM (alias stays callguard-llm) and wait until it answers.
# Usage: scripts/remote/swap_llm.sh <hf-model-id> [GPU_UTIL] [MAX_LEN]   (env EXTRA passed through)
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ -f runs/logs/vllm.pid ]] && kill -0 "$(cat runs/logs/vllm.pid)" 2>/dev/null; then
  kill "$(cat runs/logs/vllm.pid)"
  for _ in $(seq 1 60); do kill -0 "$(cat runs/logs/vllm.pid)" 2>/dev/null || break; sleep 1; done
fi
sleep 3
GPU_UTIL="${2:-0.66}" MAX_LEN="${3:-16384}" scripts/remote/serve_llm.sh "$1"
for _ in $(seq 1 120); do
  if curl -sf localhost:8000/v1/models | grep -q callguard-llm; then echo "UP $1"; exit 0; fi
  kill -0 "$(cat runs/logs/vllm.pid)" 2>/dev/null || { echo "DIED $1"; tail -20 runs/logs/vllm.log; exit 1; }
  sleep 5
done
echo "TIMEOUT $1"; exit 1
