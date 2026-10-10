#!/usr/bin/env bash
# Large-model ASR sweeps while vLLM is down (02:05). Marker: LARGE_ASR_DONE in runs/logs/asr_queue5.log
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
run() { local tag=$1; shift; echo "== $tag $(date +%T)"; uv run python scripts/research/asr_sweep.py -c gpu-12gb --tag "$tag" "$@" > runs/logs/asr_$tag.log 2>&1; echo "   done $tag $(date +%T) rc=$?"; }
L="--set asr.compute_type=float16 --set asr.condition_on_previous_text=false --set asr.initial_prompt=null"
run large-v3-gsw-clean --set asr.model=models/asr/whisper-large-v3-gsw-ct2 $L
run turbo-gsw-int8-clean --set asr.condition_on_previous_text=false --set asr.initial_prompt=null
run flix-gsw-clean --set asr.model=models/asr/flix-gsw-ct2 $L
run vanilla-large-v3-clean --set asr.model=models/asr/vanilla-large-v3-ct2 $L
echo LARGE_ASR_DONE
