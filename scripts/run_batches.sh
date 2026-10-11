#!/usr/bin/env bash
# Several batches of calls on ONE GPU host, one after another, the CPU-only Swiss German view of batch k running while
# batch k+1 uses the GPU. Each batch is a normal scripts/run_testset.sh run (same stages, same results layout).
#
# Usage: scripts/run_batches.sh <name> <batch-folder-1> [<batch-folder-2> ...]
#        -> runs/testset-<name>-<k>/ per batch (k = 1, 2, ...), runs/batches-<name>.tsv (batch, calls, seconds)
# Env:   as run_testset.sh (CACHE_DIR, LLAMA_SERVER, KEV_REPO, ...). NO_GSW=1 skips the Swiss German view entirely.
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:$PATH"   # uv (the background Swiss German step needs it too)
NAME="${1:?usage: scripts/run_batches.sh <name> <batch-folder> [...]}"; shift
(( $# )) || { echo "no batch folders given"; exit 1; }
LOG="runs/batches-$NAME.tsv"; mkdir -p runs; echo -e "batch\tcalls\tgpu_seconds\tstarted\tfinished" > "$LOG"
CSETS=(); [[ -n "${CACHE_DIR:-}" ]] && CSETS=(--set "paths.cache_dir=$CACHE_DIR")
GSW_PIDS=()
k=0
for B in "$@"; do
  k=$((k + 1)); OUT="runs/testset-$NAME-$k"
  n=$(find "$B" -maxdepth 1 -iname '*.wav' | wc -l)
  s=$(date +%s)
  NO_GSW=1 scripts/run_testset.sh "$B" "$NAME-$k"
  e=$(date +%s); echo -e "$k\t$n\t$((e - s))\t$s\t$e" >> "$LOG"
  if [[ "${NO_GSW:-0}" != 1 && -f models/asr/wav2vec2-gsw-swissdial-onnx/model.onnx ]]; then
    ( for d in "$OUT/sherlock" "$OUT/qwen/sherlock-qwen"; do
        [[ -d "$d" ]] && uv run callguard display-views -c sherlock --runs-dir "$d" \
          --set "paths.data_dir=$OUT/.no_case_data" "${CSETS[@]}" > "$OUT/gsw_$(basename "$d").log" 2>&1 || true
      done; echo "gsw done $(date +%s)" > "$OUT/gsw.done" ) &
    GSW_PIDS+=($!)
  fi
done
for p in "${GSW_PIDS[@]}"; do wait "$p" || true; done
echo "all batches done $(date +%s)" >> "$LOG"
cat "$LOG"
