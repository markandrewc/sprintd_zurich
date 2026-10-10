#!/usr/bin/env bash
# Kev-4B LoRA on officer fact labels. SKELETON: not run for the submission (finetune/README.md).
# Runs on the GPU host in the Kev environment (github.com/jaredpalmer/kev; Python >= 3.12, torch < 2.9,
# transformers >= 5.17, flash-linear-attention). Never on the laptop.
#
#   finetune/kev_lora.sh runs/<profile>/learning/export [out_dir]
#
# It trains on *.train.jsonl only and stops before activation: the adapter goes live only after the
# shadow evaluation (README "contract") and a four-eyes approval.
set -euo pipefail

EXPORT="${1:?usage: kev_lora.sh <export dir> [out dir]}"
OUT="${2:-models/kev-lora-$(date +%Y%m%d-%H%M)}"
MIN_LABELS="${MIN_LABELS:-1000}"   # Kev upstream: ~1000 records for a measurable +5 points
KIND="${KIND:-noul}"               # noul | choice

TRAIN="$EXPORT/kev_${KIND}.train.jsonl"
SHADOW="$EXPORT/kev_${KIND}.shadow_test.jsonl"
MANIFEST="$EXPORT/manifest.json"
[[ -f "$TRAIN" && -f "$MANIFEST" ]] || { echo "missing $TRAIN or $MANIFEST: run callguard learn export" >&2; exit 2; }

n=$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["trainable_fact_labels"] if m["store"]=="real" else 0)' "$MANIFEST")
if (( n < MIN_LABELS )); then
  echo "only $n trainable fact labels (need >= $MIN_LABELS, real store): not training." >&2
  exit 3
fi
# never train on anything but train-use records (the export already enforces this; check again)
python3 - "$TRAIN" <<'PY'
import json, sys
bad = [r["meta"]["call_id"] for r in map(json.loads, open(sys.argv[1])) if r["meta"]["use"] != "train" or r["meta"]["source"] == "demo"]
if bad:
    sys.exit(f"refusing: non-train records in the training file: {bad[:5]}")
PY

# recommended upstream recipe (README of jaredpalmer/kev): start from the released checkpoint, small LR.
# --init_from / --epochs / --lr / --batch / --accum / --dtype / --checkpointing are from that README; the
# names of the data / output flags are UNVERIFIED (check `python -m kev.train --help` before the first run).
python -m kev.train \
  --init_from jaredpalmer/kev-4b \
  --train "$TRAIN" \
  --epochs 2 --lr 2e-5 --batch 1 --accum 8 --dtype bf16 --checkpointing 1 \
  --out "$OUT"

cat <<EOF
Adapter written to $OUT. NOT activated.
Next (shadow evaluation, README step 4-5): serve it next to the current Kev, then
  callguard experiment <spec with variants current / candidate on the shadow calls of $SHADOW>
and activate only if the paired CI of the F1 difference excludes 0 and false alarms do not rise,
via a four-eyes approved config change.
EOF
