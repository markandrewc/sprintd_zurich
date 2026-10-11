#!/usr/bin/env bash
# Local CPU LLM: llama.cpp behind an OpenAI-compatible API on :8001 (same API as vLLM on the GPU box).
# Usage: scripts/serve_llm_local.sh [path/to/model.gguf] [alias]
set -euo pipefail
cd "$(dirname "$0")/.."
MODEL="${1:-models/llm/qwen2.5-1.5b-instruct-q4_k_m.gguf}"
ALIAS="${2:-qwen2.5-1.5b-instruct}"
exec uv run python -m llama_cpp.server \
  --model "$MODEL" --model_alias "$ALIAS" \
  --host 127.0.0.1 --port "${PORT:-8001}" \
  --n_ctx "${N_CTX:-8192}" --n_threads "${THREADS:-6}" --n_batch 512
