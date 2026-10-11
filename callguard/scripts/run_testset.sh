#!/usr/bin/env bash
# Hidden test set (or any folder of .wav files) -> its own run folder -> dashboard with only these calls.
# The production chain (config/sherlock.yaml), staged for ONE 12 GB GPU, one model on the card at a time:
#   1) Whisper large-v3 transcribes every call (no LLM loaded)                                   ~4 GB VRAM
#   2) Qwen3.8-27B 3-bit on llama-server: roles + fact answers + evidence                          ~11 GB VRAM
#      (result: Qwen-only decision = the fallback, profile sherlock-qwen)
#   3) Kev-4B answers every fact too and finds the passages by masking; Qwen's answers come from the cache  ~8 GB VRAM
#      (result: two-reader decision under the fact policy = what the demo shows, profile sherlock)
#   4) Swiss German display transcript (dialect speech model on the CPU; display only, never analysed)
# Uses only the audio: file names are never read as hints.
#
# Usage: scripts/run_testset.sh <folder-with-wavs> [name]            (name default: date-time)
# Env:   NO_KEV=1        skip stage 3 (Qwen-only results; no Kev environment needed)
#        NO_GSW=1        skip stage 4 (Swiss German view; CPU, ~0.1x audio length)
#        CACHE_DIR=...   use a separate cache (e.g. a fresh one for timing); default: the repo's .cache
#        Q38_GGUF=...    the Qwen3.8 GGUF (default models/llm/qwen38-27b-gguf/Qwen3.8-27B-UD-IQ3_XXS.gguf; another
#                        file needs CALLGUARD_Q38_TAG=<its name>, it keys the cache)
#        LLAMA_SERVER=.. llama-server binary (default ~/repos/llama.cpp/build/bin/llama-server, built with CUDA)
#        Q38_CTX=24576 Q38_SLOTS=2   llama-server context (all slots) and parallel slots
#        KEV_REPO=...    checkout of sprintd_zurich with .venv-kev (default: .. = the repo this folder is in, ../sprintd_zurich, ~/repos/sprintd_zurich)
#        OUTCEPT_URL=... send the triggers to Outcept at the end
# Result: runs/testset-<name>/   audio/ (copies), qwen/sherlock-qwen/<call>/result.json (Qwen only),
#         sherlock/<call>/result.json (two readers), timings.tsv (seconds per stage); then it prints the dashboard /
#         scoring commands.
set -euo pipefail
cd "$(dirname "$0")/.."
IN="${1:?usage: scripts/run_testset.sh <folder-with-wavs> [name]}"; NAME="${2:-$(date +%Y%m%d-%H%M)}"
OUT="runs/testset-$NAME"; mkdir -p "$OUT/audio" runs/logs
export PATH="$HOME/.local/bin:$PATH"
source scripts/remote/cuda_env.sh 2>/dev/null || true
Q38_GGUF="${Q38_GGUF:-models/llm/qwen38-27b-gguf/Qwen3.8-27B-UD-IQ3_XXS.gguf}"
export LLAMA_SERVER="${LLAMA_SERVER:-$HOME/repos/llama.cpp/build/bin/llama-server}"
T="$OUT/timings.tsv"; : > "$T"
# no case data in reach: data_dir points at an empty folder, so nothing (UI, API, eval) can look up an
# expected label by file name for these calls
NODATA="$OUT/.no_case_data"; mkdir -p "$NODATA"
CSETS=(--set "paths.data_dir=$NODATA"); [[ -n "${CACHE_DIR:-}" ]] && CSETS+=(--set "paths.cache_dir=$CACHE_DIR")
stamp() { date +%s; }
log() { echo "[$(date +%H:%M:%S)] $*"; }
mark() { echo -e "$1\t$(( $(stamp) - $2 ))" >> "$T"; log "$1 took $(( $(stamp) - $2 )) s"; }
# stop a server THIS script (or serve_llamacpp.sh) started: the pid file names the server process itself
stop_pid() {
  local f=$1 p
  [[ -f $f ]] || return 0; p=$(cat "$f")
  if kill -0 "$p" 2>/dev/null; then
    kill "$p"; for _ in $(seq 1 60); do kill -0 "$p" 2>/dev/null || break; sleep 1; done
    sleep 2  # let the driver release the memory
  fi
}
gpu_free() { nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null | head -1 || true; }
cleanup() { stop_pid runs/logs/llamacpp.pid; stop_pid runs/logs/kev.pid; }
trap cleanup EXIT

[[ "${NO_KEV:-0}" == 1 || -n "${KEV_REPO:-}" ]] || for c in .. ../sprintd_zurich "$HOME/repos/sprintd_zurich" "$HOME/sprintd_zurich"; do
  [[ -z "${KEV_REPO:-}" && -x "$c/.venv-kev/bin/python" ]] && KEV_REPO="$(cd "$c" && pwd)"; done
[[ "${NO_KEV:-0}" == 1 || -n "${KEV_REPO:-}" ]] || { echo "Kev env not found (set KEV_REPO or NO_KEV=1)"; exit 1; }
[[ -f "$Q38_GGUF" ]] || { echo "Qwen3.8 GGUF not found: $Q38_GGUF (GUIDE.md: download unsloth/Qwen3.8-27B-GGUF)"; exit 1; }
[[ -x "$LLAMA_SERVER" ]] || { echo "llama-server not found: $LLAMA_SERVER (GUIDE.md: build llama.cpp with CUDA)"; exit 1; }

shopt -s nullglob
SRC=("$IN"/*.wav "$IN"/*.WAV)
(( ${#SRC[@]} )) || { echo "no .wav files in $IN"; exit 1; }
for f in "${SRC[@]}"; do cp -n "$f" "$OUT/audio/"; done
FILES=("$OUT"/audio/*.wav "$OUT"/audio/*.WAV)
log "${#FILES[@]} calls -> $OUT   (GPU: $(gpu_free))"
S=$(stamp)

# 1) transcripts: one process, Whisper loaded once, no LLM on the GPU
stop_pid runs/logs/llamacpp.pid; stop_pid runs/logs/kev.pid
s=$(stamp)
NODATA="$NODATA" uv run python - "${FILES[@]}" <<'PY'
import os, pathlib, sys
from callguard.config import load_config
from callguard.pipeline import Pipeline
sets = [f"paths.data_dir={os.environ['NODATA']}"]
sets += [f"paths.cache_dir={os.environ['CACHE_DIR']}"] if os.environ.get("CACHE_DIR") else []
p = Pipeline(load_config("sherlock", sets))
for f in sys.argv[1:]:
    p.transcribe(pathlib.Path(f), pathlib.Path(f).stem)
    print("  asr ok", pathlib.Path(f).name, flush=True)
PY
mark 1_transcripts $s

# 2) Qwen3.8-27B 3-bit (llama-server): roles, fact answers, evidence, Qwen-only decision
s=$(stamp)
scripts/remote/serve_llamacpp.sh "$Q38_GGUF" 99 "${Q38_CTX:-24576}" "${Q38_SLOTS:-2}"
mark 2a_qwen38_start $s; log "GPU: $(gpu_free)"
s=$(stamp)
uv run callguard run "${FILES[@]}" -c sherlock-qwen --set "paths.runs_dir=$OUT/qwen" "${CSETS[@]}" > "$OUT/run_qwen.log" 2>&1 \
  || log "WARNING: stage 2 failed for some calls (run_qwen.log); continuing with the others"
mark 2b_qwen38_roles_facts_evidence $s
stop_pid runs/logs/llamacpp.pid

# 3) Kev-4B: every fact a second time (roles + Qwen's answers from the cache), two-reader decision
if [[ "${NO_KEV:-0}" != 1 ]]; then
  s=$(stamp)
  REPO="$PWD"
  ( cd "$KEV_REPO" && KEV_DTYPE=bf16 exec nohup .venv-kev/bin/python "$REPO/scripts/remote/serve_kev.py" --port 8003 \
      > "$REPO/runs/logs/kev.log" 2>&1 ) &
  echo $! > runs/logs/kev.pid   # exec: this pid IS the Kev server
  for _ in $(seq 1 120); do curl -sf localhost:8003/health >/dev/null && break
    kill -0 "$(cat runs/logs/kev.pid)" 2>/dev/null || { echo "Kev DIED"; tail -20 runs/logs/kev.log; exit 1; }; sleep 3; done
  mark 3a_kev_start $s; log "GPU: $(gpu_free)"
  s=$(stamp)
  uv run callguard run "${FILES[@]}" -c sherlock --set "paths.runs_dir=$OUT" "${CSETS[@]}" > "$OUT/run_kev.log" 2>&1 \
    || log "WARNING: stage 3 failed for some calls (run_kev.log); continuing with the others"
  stop_pid runs/logs/kev.pid
  mark 3b_kev_facts $s
  if grep -q "PinnedLLMError" "$OUT/run_kev.log"; then log "WARNING: some Qwen answers were not in the cache (run_kev.log): those calls are marked «Prüfen» (reader missing)"; fi
  for f in "${FILES[@]}"; do c=$(basename "${f%.*}"); [[ -f "$OUT/sherlock/$c/result.json" ]] || log "WARNING: no result for $c"; done
fi

# 4) Swiss German display transcript (dialect speech model on the CPU; stored apart from what the AI reads)
if [[ "${NO_GSW:-0}" != 1 && -f models/asr/wav2vec2-gsw-swissdial-onnx/model.onnx ]]; then
  s=$(stamp)
  for d in "$OUT/sherlock" "$OUT/qwen/sherlock-qwen"; do
    [[ -d "$d" ]] && uv run callguard display-views -c sherlock --runs-dir "$d" "${CSETS[@]}" > "$OUT/gsw_$(basename "$d").log" 2>&1 || true
  done
  mark 4_swiss_german_view $s
fi
mark total $S

PROFILE=sherlock; DIR="$OUT"
[[ "${NO_KEV:-0}" == 1 ]] && { PROFILE=sherlock-qwen; DIR="$OUT/qwen"; }
[[ -n "${OUTCEPT_URL:-}" ]] && uv run callguard triggers -c "$PROFILE" --set "paths.runs_dir=$DIR" "${CSETS[@]}" --url "$OUTCEPT_URL" || true
cat <<MSG

Done: ${#FILES[@]} calls in $(( $(stamp) - S )) s (stage times: $T)
Dashboard with only these calls:
  uv run callguard api -c $PROFILE --set paths.runs_dir=$DIR --set paths.data_dir=$NODATA --port 8600   # then: cd frontends/swiss && npm run dev -- --port 8605
Score against labels (call_id = wav name without .wav, expected = alarm|review|no_alert):
  uv run python scripts/score_results.py $DIR/$PROFILE labels.csv
Qwen-only fallback:  uv run python scripts/score_results.py $OUT/qwen/sherlock-qwen labels.csv
Report to Outcept:  uv run callguard triggers -c $PROFILE --set paths.runs_dir=$DIR --url http://<host>:8080/triggers
MSG
