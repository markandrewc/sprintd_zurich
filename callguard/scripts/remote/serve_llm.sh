#!/usr/bin/env bash
# GPU host (RTX 4070 12 GB, driver 535 -> vLLM 0.10.1.1 / torch cu126 in .venv-vllm; newest vLLM needs CUDA 13).
# Usage: scripts/remote/serve_llm.sh [hf-model-id]   Env: GPU_UTIL (0.70), MAX_LEN (16384), PORT (8000), EXTRA
# Always served as `callguard-llm`; check caches key on the real model id (llms.*.model_id / doctor).
# Log: runs/logs/vllm_<model>.log (runs/logs/vllm.log links to the latest). Stop: kill $(cat runs/logs/vllm.pid)
set -euo pipefail
cd "$(dirname "$0")/../.."
MODEL="${1:-Qwen/Qwen2.5-7B-Instruct-AWQ}"
mkdir -p runs/logs
LOG="runs/logs/vllm_$(basename "$MODEL").log"
# shellcheck disable=SC2086
nohup .venv-vllm/bin/vllm serve "$MODEL" --served-model-name callguard-llm \
  --host 0.0.0.0 --port "${PORT:-8000}" --max-model-len "${MAX_LEN:-16384}" \
  --gpu-memory-utilization "${GPU_UTIL:-0.70}" --enable-prefix-caching ${EXTRA:-} \
  > "$LOG" 2>&1 &
echo $! > runs/logs/vllm.pid
ln -sfn "$(basename "$LOG")" runs/logs/vllm.log
echo "vLLM $MODEL starting, pid $(cat runs/logs/vllm.pid), log $LOG"
