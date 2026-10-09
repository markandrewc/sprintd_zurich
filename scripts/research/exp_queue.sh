#!/usr/bin/env bash
# Run experiment specs one after another (waits for vLLM). Usage: exp_queue.sh <spec> [<spec>[:variants]] ...
# Logs: runs/logs/exp_<name>.log ; a line per finished spec in runs/logs/exp_queue.log
cd "$(dirname "$0")/../.." && source scripts/remote/cuda_env.sh
until curl -sf localhost:8000/v1/models | grep -q callguard-llm; do sleep 10; done
for item in "$@"; do
  spec=${item%%:*}; vars=""; [[ "$item" == *:* ]] && vars="--variants ${item#*:}"
  name=$(basename "$spec" .yaml)
  echo "== $name ${vars} $(date +%T)" >> runs/logs/exp_queue.log
  uv run callguard experiment "$spec" --split dev --jobs ${JOBS:-6} $vars >> "runs/logs/exp_$name.log" 2>&1
  echo "   done $name rc=$? $(date +%T)" >> runs/logs/exp_queue.log
done
echo "QUEUE_DONE $(date +%T)" >> runs/logs/exp_queue.log
