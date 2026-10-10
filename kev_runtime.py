"""Kev lokal laden und abfragen (geteilt von kev_app.py und kev_pipeline.py).

Lädt jaredpalmer/kev-4b über kev.checkpoint, wie der HF-Space und kev.serve: LoRA in den Qwen3.5-4B-Base gemerged,
Pointer-Head obendrauf. Unterschied zum Space: bf16 statt fp32. In fp32 braucht Kev-4B ~16 GB und passt nicht auf eine
12-GB-Karte (3080 Ti); bf16 braucht ~8 GB, laut kev.checkpoint.LoadOptions gleiche Argmax, Wahrscheinlichkeiten ±0.01.

Umgebungsvariablen:
  KEV_MODEL   Hub-Repo oder lokaler Ordner (Default jaredpalmer/kev-4b; zum Testen jaredpalmer/kev-0.8b)
  KEV_DEVICE  cuda | cpu (Default: cuda, falls vorhanden)
  KEV_DTYPE   bf16 | fp32 (Default bf16)
"""
import os

os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")

import time  # noqa: E402

import torch  # noqa: E402

from kev.api import SystemOneRequest, output_tokens, to_answers, to_record  # noqa: E402
from kev.checkpoint import Checkpoint, LoadOptions  # noqa: E402
from kev.model import admit  # noqa: E402

MODEL_REPO = os.environ.get("KEV_MODEL", "jaredpalmer/kev-4b")
DEVICE = os.environ.get("KEV_DEVICE") or ("cuda" if torch.cuda.is_available() else "cpu")
DTYPE = {"bf16": torch.bfloat16, "fp32": torch.float32}[os.environ.get("KEV_DTYPE", "bf16")]


def _sync(device):
    if str(device).startswith("cuda"): torch.cuda.synchronize()


class Kev:
    def __init__(self, repo=MODEL_REPO, device=DEVICE, dtype=DTYPE):
        t0 = time.perf_counter()
        ck = Checkpoint(repo)
        # temperature=1.0: rohe Logits; calibrated=True in probs() setzt die im Checkpoint gefittete Temperatur
        self.tok, self.model = ck.load(device, LoadOptions(dtype=dtype, attn="sdpa", temperature=1.0))
        self.repo, self.device, self.fitted = repo, device, ck.meta.temperature
        mem = f", {torch.cuda.memory_allocated() / 2**30:.1f} GB VRAM" if str(device).startswith("cuda") else ""
        print(f"[kev] {repo} auf {device} ({str(dtype).removeprefix('torch.')}), base={ck.meta.base}, "
              f"T={self.fitted:.2f}, {time.perf_counter() - t0:.0f}s{mem}", flush=True)

    @torch.inference_mode()
    def probs(self, req: SystemOneRequest, calibrated=False):
        """-> (Wahrscheinlichkeiten pro Frage, Metadaten pro Frage, Tokenzahl, ms)."""
        self.model.head.temperature = self.fitted if calibrated else 1.0   # Argmax bleibt gleich
        rec, meta = to_record(req)
        enc = admit(self.model, self.tok, rec)   # zu langer State wird abgelehnt, nicht gekürzt
        _sync(self.device); t0 = time.perf_counter()
        ps = self.model.probs(enc)
        _sync(self.device); ms = (time.perf_counter() - t0) * 1000
        return [p.tolist() for p in ps], meta, len(enc["ids"]), ms

    def systemone(self, req: SystemOneRequest, calibrated=False):
        """Die /v1/systemone-Antwort, die kev.serve für diese Anfrage liefern würde."""
        ps, meta, n_tokens, ms = self.probs(req, calibrated)
        answers = to_answers(ps, meta)
        return {"model": self.repo, "answers": answers,
                "usage": {"input_tokens": n_tokens, "output_tokens": output_tokens(self.tok, answers)}, "latency_ms": round(ms, 1)}

    def decide(self, state, questions: dict, calibrated=False):
        """Bequem: state (Text oder JSON) + Fragen-Dict -> answers-Dict."""
        return self.systemone(SystemOneRequest(state=state, questions=questions), calibrated)["answers"]
