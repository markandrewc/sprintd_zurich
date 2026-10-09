"""Content-addressed JSON cache so every stage only reruns when its inputs or params change.

Key = sha256 over (namespace, JSON of the key object). Transcripts are cached per audio-hash + ASR
params, check results per transcript-hash + check params + the family fields the check reads.
Delete ``.cache/`` to start fresh, or one namespace subfolder to rerun only that stage.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, TypeVar

from pydantic import BaseModel

M = TypeVar("M", bound=BaseModel)


def stable_hash(obj: Any) -> str:
    if isinstance(obj, BaseModel):
        obj = obj.model_dump(mode="json")
    data = json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def file_hash(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


class Cache:
    def __init__(self, root: Path, enabled: bool = True):
        self.root = root
        self.enabled = enabled

    def path(self, namespace: str, key: Any) -> Path:
        return self.root / namespace / f"{stable_hash(key)}.json"

    def get(self, namespace: str, key: Any, model: type[M]) -> M | None:
        p = self.path(namespace, key)
        if not (self.enabled and p.exists()):
            return None
        try:
            return model.model_validate_json(p.read_text())
        except Exception:
            return None  # schema changed -> recompute

    def put(self, namespace: str, key: Any, value: BaseModel) -> None:
        if not self.enabled:
            return
        p = self.path(namespace, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(value.model_dump_json(indent=1))
        tmp.replace(p)

    def get_or_compute(self, namespace: str, key: Any, model: type[M], fn: Callable[[], M],
                       store: Callable[[M], bool] | None = None) -> tuple[M, bool]:
        """Returns (value, was_cached). ``store(value) -> False`` keeps a degraded result (server down,
        model missing) out of the cache, so it is recomputed next time instead of served forever."""
        hit = self.get(namespace, key, model)
        if hit is not None:
            return hit, True
        value = fn()
        if store is None or store(value):
            self.put(namespace, key, value)
        return value, False
