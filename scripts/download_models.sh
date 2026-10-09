#!/usr/bin/env bash
# Download the model files the profiles expect under models/. Plain curl against huggingface.co
# "resolve" URLs and the k2-fsa GitHub releases: no huggingface-cli needed. Re-running skips files
# that are already complete; interrupted downloads resume.
#
# Usage: scripts/download_models.sh [local|gpu]      (default: local)
#   local  CPU laptop profile (config/local.yaml):
#            ASR   nebi/whisper-large-v3-turbo-swiss-german-ct2-int8 (CTranslate2 int8, 0.8 GB)
#                  + tokenizer.json from Flurin17/whisper-large-v3-turbo-swiss-german (the CT2 export
#                  ships none; faster-whisper would silently fall back to whisper-tiny's tokenizer)
#                  LICENCE: Flurin17's fine-tune is CC-BY-NC-4.0 (non-commercial). For anything beyond
#                  the hackathon use the MIT models below (gcoli/...-mit, trained on SPC only).
#            LLM   Qwen/Qwen2.5-1.5B-Instruct-GGUF q4_k_m (1.1 GB) for scripts/serve_llm_local.sh
#            diar  sherpa-onnx pyannote segmentation 3.0 + WeSpeaker ResNet34 (k2-fsa releases)
#   gpu    event GPU profile (config/gpu.yaml):
#            ASR   gcoli/whisper-large-v3-swiss-german-mit, its ct2/ subfolder (float16, 3.1 GB, MIT,
#                  trained on SPC) -> models/asr/whisper-large-v3-gsw-ct2
#            diar  same as local
#            LLM   nothing here: vLLM pulls the model itself (scripts/serve_vllm.sh)
#          Alternatives (not wired into a profile, untested):
#            gcoli/whisper-large-v3-turbo-swiss-german-mit  ct2/ (1.6 GB, MIT): licence-clean turbo for CPU
#            Flix-AI/flix-swissgerman-full (Apache-2.0, SPC_R; transformers weights only):
#              asr: {type: hf_whisper, model: Flix-AI/flix-swissgerman-full}  (needs: uv pip install
#              transformers torch accelerate), or convert with ct2-transformers-converter for faster_whisper.
#
# Env: HF_TOKEN (optional, sent as bearer token), MODELS_DIR (default: <repo>/models),
#      SKIP_LLM=1 (local: skip the 1.5B GGUF, e.g. on a GPU host that serves its own LLM).
set -euo pipefail
cd "$(dirname "$0")/.."

PROFILE="${1:-local}"
MODELS="${MODELS_DIR:-models}"
HF="https://huggingface.co"
K2="https://github.com/k2-fsa/sherpa-onnx/releases/download"

AUTH=()
[[ -n "${HF_TOKEN:-}" ]] && AUTH=(-H "Authorization: Bearer ${HF_TOKEN}")

# fetch URL DEST: download to DEST.part (resumable), then move into place
fetch() {
  local url="$1" dest="$2"
  if [[ -s "$dest" ]]; then
    echo "  ok    $dest"
    return
  fi
  mkdir -p "$(dirname "$dest")"
  echo "  get   $dest"
  local auth=()
  [[ "$url" == "$HF"/* ]] && auth=("${AUTH[@]}")
  curl -fL --progress-bar --retry 3 --retry-delay 2 -C - "${auth[@]}" -o "$dest.part" "$url"
  mv "$dest.part" "$dest"
}

# hf REPO PATH_IN_REPO DEST
hf() { fetch "$HF/$1/resolve/main/$2" "$3"; }

diarization() {
  echo "diarization (sherpa-onnx)"
  local seg="$MODELS/diar/sherpa-onnx-pyannote-segmentation-3-0"
  if [[ ! -s "$seg/model.onnx" ]]; then
    fetch "$K2/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2" \
      "$MODELS/diar/segmentation.tar.bz2"
    tar -xjf "$MODELS/diar/segmentation.tar.bz2" -C "$MODELS/diar"
    rm -f "$MODELS/diar/segmentation.tar.bz2"
  fi
  echo "  ok    $seg/model.onnx"
  # "recongition" is the actual (misspelled) release tag
  fetch "$K2/speaker-recongition-models/wespeaker_en_voxceleb_resnet34.onnx" \
    "$MODELS/diar/wespeaker_en_voxceleb_resnet34.onnx"
}

local_models() {
  echo "ASR: whisper-large-v3-turbo Swiss German, CTranslate2 int8"
  local dir="$MODELS/asr/whisper-turbo-gsw-ct2-int8" repo="nebi/whisper-large-v3-turbo-swiss-german-ct2-int8"
  for f in config.json model.bin preprocessor_config.json vocabulary.json; do
    hf "$repo" "$f" "$dir/$f"
  done
  hf Flurin17/whisper-large-v3-turbo-swiss-german tokenizer.json "$dir/tokenizer.json"

  if [[ "${SKIP_LLM:-0}" == 1 ]]; then
    echo "LLM: skipped (SKIP_LLM=1)"
  else
    echo "LLM: Qwen2.5-1.5B-Instruct GGUF q4_k_m"
    hf Qwen/Qwen2.5-1.5B-Instruct-GGUF qwen2.5-1.5b-instruct-q4_k_m.gguf \
      "$MODELS/llm/qwen2.5-1.5b-instruct-q4_k_m.gguf"
  fi

  diarization
}

gpu_models() {
  echo "ASR: whisper-large-v3 Swiss German (MIT), CTranslate2 float16"
  local dir="$MODELS/asr/whisper-large-v3-gsw-ct2" repo="gcoli/whisper-large-v3-swiss-german-mit"
  for f in config.json model.bin preprocessor_config.json tokenizer.json vocabulary.json; do
    hf "$repo" "ct2/$f" "$dir/$f"
  done
  diarization
  echo "LLM: served by vLLM, which downloads the model on first start (scripts/serve_vllm.sh)"
}

case "$PROFILE" in
  local) local_models ;;
  gpu) gpu_models ;;
  *) echo "usage: $0 [local|gpu]" >&2; exit 2 ;;
esac
echo "done: $PROFILE models in $MODELS/"
