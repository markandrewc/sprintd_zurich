#!/usr/bin/env bash
# Warm the caches of a profile over all 60 calls with N parallel `callguard batch` workers (disjoint call sets).
# Usage: scripts/research/warm.sh <profile> <N> <tag> [--set ...]    logs: runs/logs/warm_<tag>_<i>.log
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
prof=$1; n=$2; tag=$3; shift 3
ids=$(uv run python -c "
from callguard.data import load_calls
cs=sorted(c.call_id for c in load_calls('data_upstream/inventx-case-study/data'))
print(' '.join(','.join(cs[i::$n]) for i in range($n)))")
i=0; pids=()
for chunk in $ids; do
  uv run callguard batch -c "$prof" --calls "$chunk" "$@" > "runs/logs/warm_${tag}_$i.log" 2>&1 &
  pids+=($!); i=$((i+1))
done
for p in "${pids[@]}"; do wait "$p"; done
echo "WARM_DONE $tag $(date +%T)"
