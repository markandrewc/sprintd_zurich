#!/usr/bin/env bash
# One-off: put the Swiss German dialect CTC model (for the display-only `gsw` view) at
# models/asr/wav2vec2-gsw-swissdial-onnx. Downloads scasutt/wav2vec2-large-xlsr-52_Swiss_German (Apache-2.0, ~1.3 GB)
# and exports it to ONNX in a throw-away venv (CPU torch + transformers), so the app env needs no torch.
# Faster alternative if another host already has it:  scp -r host:~/sprintd/models/asr/wav2vec2-gsw-swissdial-onnx models/asr/
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:-models/asr/wav2vec2-gsw-swissdial-onnx}
if [[ -f "$OUT/model.onnx" ]]; then echo "already there: $OUT"; exit 0; fi
VENV=$(mktemp -d)/venv
uv venv -q -p 3.12 "$VENV"
VIRTUAL_ENV="$VENV" uv pip install -q --index-url https://download.pytorch.org/whl/cpu torch
VIRTUAL_ENV="$VENV" uv pip install -q transformers onnx onnxruntime numpy
CUDA_VISIBLE_DEVICES= "$VENV/bin/python" scripts/gsw/export_w2v_onnx.py "$OUT"
rm -rf "$(dirname "$VENV")"
ls -la "$OUT"
