#!/usr/bin/env python
"""Kev-4B as a plain systemone service for callguard (``llms.<name>.type: kev``, src/callguard/llm/kev.py).

The teammate's service (sprintd_zurich ``fraud_analysis/api.py``) only offers POST /analyze (their own question
file, decision rule and localisation in one call); callguard needs the raw primitive: arbitrary questions about
an arbitrary state. This script wraps their loader (``fraud_analysis.runtime.Kev``: LoRA merged into the
Qwen3.5-4B base, pointer head, bf16 ~8 GB) without changing their code.

Run it on the GPU host with the TEAMMATE's environment (torch + transformers + peft + fastapi + uvicorn), NOT
callguard's (which has no torch); vLLM must be stopped first (12 GB card), see docs/KEV.md:

    kill $(cat runs/logs/vllm.pid)
    cd ~/repos/sprintd_zurich && .venv-kev/bin/python ~/repos/sprintd/scripts/remote/serve_kev.py --port 8003
    # the teammate checkout is found via --kev-repo, $KEV_REPO or the current directory (in that order)

Endpoints:
    GET  /health         {"status": "ok", "model", "dtype", "device", "revision", "loaded", "requests"}
    POST /v1/systemone   {"state": str | obj, "questions": {qid: {"type": "noul"|"choice"|"score", ...}},
                          "calibrated": false}
                      -> {"model", "answers": {qid: {"type": "noul", "noul": p}, ...}, "usage", "latency_ms"}
                         422: invalid question or state over Kev's context (not truncated)
Env (read by fraud_analysis.runtime): KEV_MODEL (jaredpalmer/kev-4b; repo@sha pins a revision), KEV_DTYPE (bf16),
KEV_DEVICE (cuda). The model loads at start-up, so /health answering means the weights are on the GPU.
Requests run one at a time (one model, one GPU).
"""

import argparse
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any


def _revision(repo: str) -> str | None:
    """The Hub snapshot (commit sha) the weights were loaded from, if any; provenance only."""
    try:
        from fraud_analysis.kev.checkpoint import resolve_run

        path = Path(resolve_run(repo))
        return path.name if path.parent.name == "snapshots" else None
    except Exception:
        return None


def make_app(kev: Any, info: dict[str, Any]) -> Any:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, ValidationError

    from fraud_analysis.kev.api import SystemOneRequest

    app = FastAPI(title="Kev systemone for callguard", version="1.0")
    lock = threading.Lock()
    stats = {"requests": 0, "errors": 0}

    class Request(BaseModel):
        state: Any
        questions: dict[str, Any]
        model: str = "kev-latest"
        calibrated: bool = False

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", **info, "loaded": True, **stats}

    @app.post("/v1/systemone")
    def systemone(req: Request) -> dict[str, Any]:
        try:
            sreq = SystemOneRequest(state=req.state, questions=req.questions)
        except ValidationError as e:
            stats["errors"] += 1
            raise HTTPException(422, str(e)) from None
        with lock:
            try:
                out = kev.systemone(sreq, calibrated=req.calibrated)
            except ValueError as e:  # ContextOverflow and friends: the caller's input, not the server
                stats["errors"] += 1
                raise HTTPException(422, str(e)) from None
            stats["requests"] += 1
        out["model"] = info["model"]
        return out

    return app


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--host", default=os.environ.get("KEV_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.environ.get("KEV_PORT", "8003")))
    ap.add_argument("--kev-repo", default=os.environ.get("KEV_REPO") or os.getcwd(),
                    help="sprintd_zurich checkout holding fraud_analysis/ (default $KEV_REPO, else the cwd)")
    args = ap.parse_args()
    repo = str(Path(args.kev_repo).expanduser().resolve())
    if (Path(repo) / "fraud_analysis").is_dir() and repo not in sys.path:
        sys.path.insert(0, repo)  # `python /abs/serve_kev.py` puts the script's dir on sys.path, not the cwd
    try:
        from fraud_analysis.runtime import DEVICE, MODEL_REPO, Kev
    except ImportError as e:
        sys.exit(f"cannot import fraud_analysis.runtime ({e}): run with the teammate's Python and "
                 f"PYTHONPATH=<sprintd_zurich checkout> (docs/KEV.md)")
    import uvicorn

    t0 = time.time()
    kev = Kev()  # loads now: /health only answers once the weights are on the GPU
    info = {"model": MODEL_REPO, "dtype": os.environ.get("KEV_DTYPE", "bf16"), "device": str(DEVICE),
            "revision": _revision(MODEL_REPO), "load_seconds": round(time.time() - t0, 1)}
    print(f"[serve_kev] {info} on http://{args.host}:{args.port}", flush=True)
    uvicorn.run(make_app(kev, info), host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
