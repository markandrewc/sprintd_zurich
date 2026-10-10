#!/usr/bin/env bash
# Serve RedHatAI/Qwen3.8-27B-INT4 with a recent vLLM as `callguard-llm` on :8000 (24 GB GPU, driver >= 580).
# Text only: image/video limits 0 so the vision tower is not used. Env: MODEL, MAX_LEN, UTIL, PORT.
set -euo pipefail
cd "$(dirname "$0")/../.."
MODEL="${MODEL:-RedHatAI/Qwen3.8-27B-INT4}"
mkdir -p runs/logs
nohup .venv-vllm/bin/vllm serve "$MODEL" --served-model-name callguard-llm --host 127.0.0.1 --port "${PORT:-8000}" \
  --max-model-len "${MAX_LEN:-16384}" --gpu-memory-utilization "${UTIL:-0.92}" --enable-prefix-caching \
  --limit-mm-per-prompt '{"image": 0, "video": 0}' --max-num-seqs "${SEQS:-16}" ${EXTRA:-} \
  > runs/logs/vllm.log 2>&1 &
echo $! > runs/logs/vllm.pid
for _ in $(seq 1 180); do
  if curl -sf "localhost:${PORT:-8000}/v1/models" | grep -q callguard-llm; then echo "UP $MODEL"; exit 0; fi
  kill -0 "$(cat runs/logs/vllm.pid)" 2>/dev/null || { echo "DIED $MODEL"; tail -40 runs/logs/vllm.log; exit 1; }
  sleep 5
done
echo "TIMEOUT $MODEL"; exit 1
