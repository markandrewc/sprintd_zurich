"""Shared resources handed to every plugin: config, paths, cache, families, named LLM clients."""

from __future__ import annotations

from functools import cached_property
from pathlib import Path

from callguard import registry
from callguard.cache import Cache
from callguard.config import AppConfig
from callguard.families import load_families
from callguard.plugins import LLM
from callguard.types import Family


class Context:
    def __init__(self, cfg: AppConfig, *, use_cache: bool = True):
        self.cfg = cfg
        self.cache = Cache(cfg.paths.resolve("cache_dir"), enabled=use_cache)
        self._llms: dict[str, LLM] = {}

    def path(self, name: str) -> Path:
        return self.cfg.paths.resolve(name)

    @property
    def runs_dir(self) -> Path:
        return self.path("runs_dir") / self.cfg.name

    def families(self) -> list[Family]:
        """Re-read every time: the officer may have edited keywords/criteria in the UI."""
        fams = load_families(self.path("keywords"), self.path("criteria"), only=self.cfg.families)
        return [f for f in fams if f.enabled]

    def llm(self, name: str = "default") -> LLM:
        if name not in self._llms:
            if name not in self.cfg.llms:
                raise KeyError(f"LLM {name!r} not configured. Configured: {list(self.cfg.llms)}")
            self._llms[name] = registry.create("llm", self.cfg.llms[name], ctx=self)
        return self._llms[name]

    @cached_property
    def data_dir(self) -> Path:
        return self.path("data_dir")
