#!/usr/bin/env bash
# Turbo-class ASR sweeps (~2 GB VRAM) that fit next to vLLM. Starts after asr_queue2 finished.
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
until grep -q ESSENTIAL_ASR_DONE runs/logs/asr_queue2.log 2>/dev/null; do sleep 10; done
sleep 60   # let vLLM finish its own allocation first
run() { local tag=$1; shift; echo "== $tag $(date +%T)"; uv run python scripts/research/asr_sweep.py -c gpu-12gb --tag "$tag" "$@" > runs/logs/asr_$tag.log 2>&1; echo "   done $tag $(date +%T) rc=$?"; }
run turbo-gsw-int8-nocond --set asr.condition_on_previous_text=false
run turbo-gsw-int8-noprompt --set asr.initial_prompt=null
run ost-turbo-gsw --set asr.model=models/asr/ost-turbo-gsw-ct2 --set asr.compute_type=int8_float16
run gcoli-turbo-gsw --set asr.model=models/asr/gcoli-turbo-gsw/ct2 --set asr.compute_type=int8_float16
run turbo-gsw-int8-b5 --set asr.beam_size=5
echo TURBO_ASR_DONE
