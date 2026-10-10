#!/usr/bin/env bash
# After the 14B queue: back to Qwen2.5-7B for blind table, large-v3 ASR, ORACLE and English view with facts.
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
log() { echo "$* $(date +%T)" >> runs/logs/llm_sweep.log; }
until grep -q Q14_DONE runs/logs/llm_sweep.log; do sleep 10; done
log "== swap Qwen2.5-7B-AWQ"; EXTRA="--max-num-seqs 24" scripts/remote/swap_llm.sh Qwen/Qwen2.5-7B-Instruct-AWQ 0.80 16384 >> runs/logs/llm_sweep.log 2>&1 || exit 1
for v in qwen25_7b qwen25_7b_facts_l3 qwen25_7b_facts_oracle qwen25_7b_facts_en; do
  log "== $v"; uv run callguard experiment experiments/llm_models.yaml --split dev --jobs 8 --variants $v >> runs/logs/exp_llm_models.log 2>&1; log "   done $v rc=$?"
done
log "P7B_DONE"
