"""Writes ``<runs_dir>/<call_id>/result.json``: the hand-off between the pipeline and the UI."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from callguard.config import ROOT
from callguard.plugins import Sink
from callguard.types import CallResult

if TYPE_CHECKING:
    from callguard.context import Context


class JsonDirSink(Sink):
    def __init__(self, ctx: "Context", *, dir: str | None = None, enabled: bool = True):
        super().__init__(ctx, enabled=enabled, dir=dir)
        self.dir = dir

    @property
    def root(self) -> Path:
        if not self.dir:
            return self.ctx.runs_dir
        p = Path(self.dir)
        return p if p.is_absolute() else ROOT / p

    def path_for(self, call_id: str) -> Path:
        return self.root / call_id / "result.json"

    def emit(self, result: CallResult) -> None:
        out = self.path_for(result.call_id)
        out.parent.mkdir(parents=True, exist_ok=True)
        # write-then-rename: the UI polls this folder and must never read a half-written file
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(result.model_dump_json(indent=1))
        tmp.replace(out)
