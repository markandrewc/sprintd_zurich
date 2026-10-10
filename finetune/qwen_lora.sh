#!/usr/bin/env bash
# QLoRA of the facts model (Qwen2.5-7B-Instruct) on officer fact labels. SKELETON: not run for the
# submission (finetune/README.md). GPU host only (12 GB: Unsloth 4-bit; plain HF + FA2 does not fit our
# 3-5k-token prompts, docs/research/finetuning_assessment.md §3).
#
#   finetune/qwen_lora.sh runs/<profile>/learning/export [out_dir]
#
# Trains on qwen_sft.train.jsonl (chat = the facts check's own prompt + the officer's one-word answer).
# Stops before activation: shadow evaluation + four-eyes approval first.
set -euo pipefail

EXPORT="${1:?usage: qwen_lora.sh <export dir> [out dir]}"
OUT="${2:-models/qwen-facts-lora-$(date +%Y%m%d-%H%M)}"
MIN_LABELS="${MIN_LABELS:-1000}"
BASE="${BASE:-unsloth/Qwen2.5-7B-Instruct-bnb-4bit}"

TRAIN="$EXPORT/qwen_sft.train.jsonl"
MANIFEST="$EXPORT/manifest.json"
[[ -f "$TRAIN" && -f "$MANIFEST" ]] || { echo "missing $TRAIN or $MANIFEST: run callguard learn export" >&2; exit 2; }
n=$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["trainable_fact_labels"] if m["store"]=="real" else 0)' "$MANIFEST")
if (( n < MIN_LABELS )); then
  echo "only $n trainable fact labels (need >= $MIN_LABELS, real store): not training." >&2
  exit 3
fi

python3 - "$TRAIN" "$OUT" "$BASE" <<'PY'
import json, sys
train, out, base = sys.argv[1:4]
rows = [json.loads(l) for l in open(train)]
assert all(r["meta"]["use"] == "train" and r["meta"]["source"] != "demo" for r in rows), "non-train record"
from unsloth import FastLanguageModel            # noqa: E402  (GPU host environment)
from trl import SFTConfig, SFTTrainer            # noqa: E402
from datasets import Dataset                     # noqa: E402

model, tok = FastLanguageModel.from_pretrained(base, max_seq_length=8192, load_in_4bit=True)
model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=32, lora_dropout=0.0,
                                         target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
ds = Dataset.from_list([{"messages": r["messages"]} for r in rows])
trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=ds,
                     args=SFTConfig(output_dir=out, num_train_epochs=2, learning_rate=1e-4,
                                    per_device_train_batch_size=1, gradient_accumulation_steps=8,
                                    assistant_only_loss=True, logging_steps=10, save_strategy="epoch"))
trainer.train()
model.save_pretrained(out)
print(f"adapter -> {out}")
PY

cat <<EOF
Adapter written to $OUT. NOT activated.
Shadow evaluation next (README step 4-5): serve the base with --enable-lora, add a profile whose facts
LLM uses the adapter, score qwen_sft.shadow_test.jsonl calls with both, and activate only if the paired
CI excludes 0, false alarms do not rise and a second person approves.
EOF
