"""Prefetch HF repos into models/asr/<name> (snapshot_download). Usage: fetch_models.py repo=dir [...]"""
import sys
from huggingface_hub import snapshot_download

for arg in sys.argv[1:]:
    repo, _, d = arg.partition("=")
    sub = None
    if ":" in repo:
        repo, sub = repo.split(":", 1)
    p = snapshot_download(repo, local_dir=f"models/asr/{d}", allow_patterns=[f"{sub}/*"] if sub else None)
    print("ok", repo, p, flush=True)
