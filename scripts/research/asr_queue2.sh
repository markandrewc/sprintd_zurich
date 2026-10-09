#!/usr/bin/env bash
# Essential ASR model sweeps (GPU exclusive, vLLM down), then restart vLLM. Waits for PID $1 first.
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
while kill -0 "$1" 2>/dev/null; do sleep 5; done
run() { local tag=$1; shift; echo "== $tag $(date +%T)"; uv run python scripts/research/asr_sweep.py -c gpu-12gb --tag "$tag" "$@" > runs/logs/asr_$tag.log 2>&1; echo "   done $tag $(date +%T) rc=$?"; }
run turbo-gsw-fp16 --set asr.model=models/asr/turbo-gsw-ct2-fp16 --set asr.compute_type=float16
run vanilla-turbo --set asr.model=models/asr/vanilla-turbo-ct2 --set asr.compute_type=float16
echo "vLLM restart $(date +%T)"; GPU_UTIL=0.66 EXTRA="--max-num-seqs 24" scripts/remote/serve_llm.sh
echo ESSENTIAL_ASR_DONE
