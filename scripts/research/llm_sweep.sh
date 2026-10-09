#!/usr/bin/env bash
# RQ6 LLM sweep: one experiments/llm_models.yaml variant per served model. Log: runs/logs/llm_sweep.log
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
log() { echo "$* $(date +%T)" >> runs/logs/llm_sweep.log; }
exp() { uv run callguard experiment experiments/llm_models.yaml --split dev --jobs 8 --variants "$1" >> runs/logs/exp_llm_models.log 2>&1; log "   done $1 rc=$?"; }
while ps -eo args | grep -q "[c]allguard experiment experiments/asr_models.yaml"; do sleep 10; done
log "== qwen25_7b"; exp qwen25_7b
log "== swap Qwen3-8B-AWQ"; EXTRA="--max-num-seqs 24" scripts/remote/swap_llm.sh Qwen/Qwen3-8B-AWQ 0.66 16384 >> runs/logs/llm_sweep.log 2>&1 && { log "== qwen3_8b"; exp qwen3_8b; }
until grep -q TURBO_ASR_DONE runs/logs/asr_queue3.log 2>/dev/null; do sleep 10; done
log "== swap Qwen2.5-14B-AWQ"; EXTRA="--kv-cache-dtype fp8 --enforce-eager --max-num-seqs 8" scripts/remote/swap_llm.sh Qwen/Qwen2.5-14B-Instruct-AWQ 0.90 12288 >> runs/logs/llm_sweep.log 2>&1 && { log "== qwen25_14b"; exp qwen25_14b; }
log "== swap Qwen3-14B-AWQ"; EXTRA="--kv-cache-dtype fp8 --enforce-eager --max-num-seqs 8" scripts/remote/swap_llm.sh Qwen/Qwen3-14B-AWQ 0.90 12288 >> runs/logs/llm_sweep.log 2>&1 && { log "== qwen3_14b"; exp qwen3_14b; }
log "LLM_SWEEP_DONE"
