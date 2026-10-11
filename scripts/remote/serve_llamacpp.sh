#!/usr/bin/env bash
# Serve a GGUF model with llama.cpp's llama-server as `callguard-llm` on :8004 (OpenAI API with logprobs).
# For models the host's vLLM 0.10.1 cannot load (Qwen3.5 / Qwen3.8 hybrid attention needs a newer vLLM, which
# needs a newer driver than 535). Built on the GPU host with CUDA 12.1:
#   git clone --depth 1 https://github.com/ggml-org/llama.cpp ~/repos/llama.cpp && cd ~/repos/llama.cpp
#   cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=89 -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.1/bin/nvcc \
#         -DLLAMA_CURL=OFF -DCMAKE_BUILD_TYPE=Release && cmake --build build -j 12 --target llama-server
# Usage: scripts/remote/serve_llamacpp.sh <model.gguf> [NGL=99] [CTX=24576] [SLOTS=2]
# Stop vLLM / Kev first: one model on the 12 GB card at a time. Stop this one: kill $(cat runs/logs/llamacpp.pid)
set -euo pipefail
cd "$(dirname "$0")/../.."
MODEL="$1"; NGL="${2:-99}"; CTX="${3:-24576}"; SLOTS="${4:-2}"
BIN="${LLAMA_SERVER:-$HOME/repos/llama.cpp/build/bin/llama-server}"
[[ -f "$MODEL" ]] || { echo "no such model: $MODEL"; exit 1; }
mkdir -p runs/logs
nohup "$BIN" -m "$MODEL" --alias callguard-llm --host 127.0.0.1 --port "${PORT:-8004}" \
  -ngl "$NGL" -c "$CTX" -np "$SLOTS" -fa on --cache-type-k q8_0 --cache-type-v q8_0 --jinja \
  ${EXTRA:-} > runs/logs/llamacpp.log 2>&1 &
echo $! > runs/logs/llamacpp.pid
for _ in $(seq 1 120); do
  if curl -sf "localhost:${PORT:-8004}/v1/models" | grep -q callguard-llm; then echo "UP $MODEL (ngl $NGL, ctx $CTX, slots $SLOTS)"; exit 0; fi
  kill -0 "$(cat runs/logs/llamacpp.pid)" 2>/dev/null || { echo "DIED $MODEL"; tail -30 runs/logs/llamacpp.log; exit 1; }
  sleep 5
done
echo "TIMEOUT $MODEL"; exit 1
