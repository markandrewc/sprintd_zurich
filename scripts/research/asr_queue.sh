#!/usr/bin/env bash
# Sequential ASR sweeps over all 60 calls (cached per model). Logs: runs/logs/asr_<tag>.log
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
run() { local tag=$1; shift; echo "== $tag $(date +%T)"; uv run python scripts/research/asr_sweep.py -c gpu-12gb --tag "$tag" "$@" > runs/logs/asr_$tag.log 2>&1; echo "   done $tag $(date +%T) rc=$?"; }
run large-v3-gsw-b1 --set asr.model=models/asr/whisper-large-v3-gsw-ct2 --set asr.compute_type=float16
run turbo-gsw-fp16 --set asr.model=models/asr/turbo-gsw-ct2-fp16 --set asr.compute_type=float16
run vanilla-large-v3 --set asr.model=models/asr/vanilla-large-v3-ct2 --set asr.compute_type=float16
run vanilla-turbo --set asr.model=models/asr/vanilla-turbo-ct2 --set asr.compute_type=float16
run large-v3-gsw-b5 --set asr.model=models/asr/whisper-large-v3-gsw-ct2 --set asr.compute_type=float16 --set asr.beam_size=5
run turbo-gsw-int8-noprompt --set asr.initial_prompt=null
run turbo-gsw-int8-b5 --set asr.beam_size=5
echo ALL_ASR_DONE
