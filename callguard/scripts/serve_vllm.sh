#!/usr/bin/env bash
# GPU LLM server: vLLM behind an OpenAI-compatible API on :8000 (config/gpu.yaml points here).
# Same API as the local llama.cpp server, so the checks run unchanged; gpu.yaml only switches
# json_mode to json_schema (vLLM structured outputs) and raises concurrency.
#
# Usage: scripts/serve_vllm.sh [hf-model-id]        (default: Qwen/Qwen3-30B-A3B-Instruct-2507)
# Env:   PORT (8000), MAX_LEN (16384), GPU_UTIL (0.90), TP (tensor-parallel GPUs, 1), EXTRA (more vllm flags)
# Install vLLM in its own environment on the GPU box (e.g. `uv tool install vllm` or `pip install vllm`);
# it pins its own torch and is not a callguard dependency.
#
# Which model for which GPU (weights only; the rest of the memory becomes KV cache):
#   Qwen/Qwen3-30B-A3B-Instruct-2507        MoE, 3B active -> fast. bf16 = 61 GB: one 80 GB GPU (A100/H100).
#     ...-Instruct-2507-FP8                 31 GB: fits a 48 GB GPU (L40S, A6000) with room for KV cache.
#   Qwen/Qwen2.5-32B-Instruct-AWQ           4-bit, 19 GB: a 24 GB GPU (L4, 4090) with MAX_LEN 8192,
#                                           comfortable on 40-48 GB. Dense, slower than the MoE.
#   casperhansen/llama-3.3-70b-instruct-awq 4-bit, 40 GB: 80 GB GPU, or TP=2 on two 48 GB GPUs.
#                                           Strongest German of the three, slowest.
# Whatever you serve, tell the profile its name:  --set llms.default.model=<hf-model-id>
#
# MAX_LEN 16384: the longest case call renders to ~8k characters (~3k tokens); prompts add ~1.5k.
# Prefix caching reuses the shared system prompt and repeated samples (self-consistency, G-Eval).
set -euo pipefail

MODEL="${1:-Qwen/Qwen3-30B-A3B-Instruct-2507}"

# shellcheck disable=SC2086
exec vllm serve "$MODEL" \
  --host 127.0.0.1 --port "${PORT:-8000}" \
  --max-model-len "${MAX_LEN:-16384}" \
  --gpu-memory-utilization "${GPU_UTIL:-0.90}" \
  --tensor-parallel-size "${TP:-1}" \
  --enable-prefix-caching \
  ${EXTRA:-}
