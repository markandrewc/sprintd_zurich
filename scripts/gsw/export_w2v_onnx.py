"""One-off: export the Swiss German dialect CTC model (scasutt/wav2vec2-large-xlsr-52_Swiss_German, Apache-2.0,
trained on SwissDial dialect transcriptions) to ONNX for the ``ctc_dialect`` translator, so the app env needs only
onnxruntime (already there with faster-whisper), no torch.

Needs torch + transformers (any env, e.g. the vLLM venv on the GPU host):
  python scripts/gsw/export_w2v_onnx.py models/asr/wav2vec2-gsw-swissdial-onnx
Writes model.onnx, vocab.json, meta.json and checks the ONNX logits against torch on random audio.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

NAME = "scasutt/wav2vec2-large-xlsr-52_Swiss_German"


def main(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    proc = Wav2Vec2Processor.from_pretrained(NAME)
    model = Wav2Vec2ForCTC.from_pretrained(NAME).eval()
    x = torch.randn(1, 16000 * 3)
    torch.onnx.export(model, (x,), str(out / "model.onnx"), input_names=["input_values"], output_names=["logits"],
                      dynamic_axes={"input_values": {0: "batch", 1: "samples"}, "logits": {0: "batch", 1: "frames"}},
                      opset_version=17, dynamo=False)
    vocab = proc.tokenizer.get_vocab()
    (out / "vocab.json").write_text(json.dumps(vocab, ensure_ascii=False, indent=1))
    fe = proc.feature_extractor
    (out / "meta.json").write_text(json.dumps({
        "source": NAME, "license": "apache-2.0", "sampling_rate": fe.sampling_rate, "do_normalize": fe.do_normalize,
        "pad_token": proc.tokenizer.pad_token, "word_delimiter_token": proc.tokenizer.word_delimiter_token,
    }, indent=1))
    import onnxruntime as ort
    sess = ort.InferenceSession(str(out / "model.onnx"), providers=["CPUExecutionProvider"])
    y = torch.randn(1, 16000 * 5)
    with torch.no_grad():
        ref = model(y).logits.numpy()
    got = sess.run(None, {"input_values": y.numpy()})[0]
    print("max abs diff", float(np.abs(ref - got).max()), "argmax equal", bool((ref.argmax(-1) == got.argmax(-1)).all()))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
