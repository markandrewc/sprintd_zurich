"""Transcript views: several textual renderings of one call (docs/design/v2_plan.md §1).

A view is either an **ASR view** (audio -> text with its own ASR plugin, optionally diarized) or a
**translated view** (another view -> text in ``lang`` via a ``translator`` plugin; segment ids, times,
speakers and roles are copied from the source, so findings on it point at the same audio).

```yaml
views:
  de:         {lang: de}                                   # top-level asr + diarizer
  de_large:   {lang: de, asr: {model: models/asr/..., compute_type: float16}}   # merged onto `asr`
  en_from_de: {lang: en, from: de, translator: {type: llm_translate, llm: default}}
  de_fused:   {lang: de, from: [de, de_large], translator: {type: llm_correct, llm: default}}
primary_view: de
check_view: null
extra_views: []
```

A **multi-source** view (``from: [a, b, c]``) is built from several views by a translator with
``multi_source = True`` (``llm_correct``): the first source is the primary (its segments, times, speakers
and roles are kept), the others are alternatives. A single ``from`` (string or one-element list) is
the plain translated view with the unchanged cache key.

No ``views`` block -> one ASR view ``main`` (top-level ``asr`` + ``diarizer``, ``lang`` unset): v1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable

from callguard.config import _deep_merge

if TYPE_CHECKING:
    from callguard.config import AppConfig

MAIN = "main"
VIEW_KEYS = {"lang", "asr", "diarize", "from", "translator", "description"}


class ViewConfigError(ValueError):
    """A ``views`` block that cannot work (unknown source, cycle, missing translator...)."""


@dataclass(frozen=True)
class ViewSpec:
    name: str
    lang: str | None = None
    asr: dict[str, Any] | None = None  # ASR views: full ASR plugin spec (top-level `asr` merged in)
    diarize: bool = True  # ASR views: run the top-level diarizer on this view
    source: str | None = None  # translated views: the view translated from (YAML `from`; first if a list)
    sources: tuple[str, ...] = ()  # all `from` views, primary first (multi-source: len > 1)
    translator: dict[str, Any] | None = None  # translated views: translator plugin spec
    description: str = ""
    raw: dict[str, Any] = field(default_factory=dict, compare=False)

    @property
    def kind(self) -> str:
        return "translate" if self.source else "asr"

    @property
    def alternatives(self) -> tuple[str, ...]:
        """Multi-source views: the sources after the primary one (empty for plain translated views)."""
        return self.sources[1:]


def _sources(name: str, raw: Any) -> tuple[str, ...]:
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, (list, tuple)) and raw and all(isinstance(x, str) and x for x in raw):
        if len(set(raw)) != len(raw):
            raise ViewConfigError(f"view {name!r}: `from` lists a view twice: {list(raw)}")
        return tuple(raw)
    raise ViewConfigError(f"view {name!r}: `from` must be a view name or a non-empty list of view names, "
                          f"got {raw!r}")


def parse_views(cfg: "AppConfig") -> dict[str, ViewSpec]:
    """``cfg.views`` -> specs (insertion order kept). Validates keys and sources, not the DAG."""
    if not cfg.views:
        return {MAIN: ViewSpec(MAIN, None, asr=dict(cfg.asr), diarize=True)}
    specs: dict[str, ViewSpec] = {}
    for name, raw in cfg.views.items():
        raw = dict(raw or {})
        unknown = set(raw) - VIEW_KEYS
        if unknown:
            raise ViewConfigError(f"view {name!r}: unknown keys {sorted(unknown)} (allowed: {sorted(VIEW_KEYS)})")
        lang = raw.get("lang")
        if "from" in raw:
            if "asr" in raw:
                raise ViewConfigError(f"view {name!r}: a translated view (`from`) cannot have its own `asr`")
            tr = raw.get("translator")
            if not tr:
                raise ViewConfigError(f"view {name!r}: translated view needs `translator: {{type: ...}}`")
            if not lang:
                raise ViewConfigError(f"view {name!r}: translated view needs `lang` (the target language)")
            sources = _sources(name, raw["from"])
            specs[name] = ViewSpec(name, str(lang), source=sources[0], sources=sources,
                                   translator={"type": tr} if isinstance(tr, str) else dict(tr),
                                   description=str(raw.get("description", "")), raw=raw)
        else:
            if "translator" in raw:
                raise ViewConfigError(f"view {name!r}: `translator` needs `from: <source view>`")
            own = raw.get("asr") or {}
            if isinstance(own, str):
                own = {"type": own}
            asr = _deep_merge(dict(cfg.asr), dict(own))  # same rules as `extends`: a new type replaces
            specs[name] = ViewSpec(name, str(lang) if lang else None, asr=asr,
                                   diarize=bool(raw.get("diarize", True)),
                                   description=str(raw.get("description", "")), raw=raw)
    for s in specs.values():
        for src in s.sources:
            if src not in specs:
                raise ViewConfigError(f"view {s.name!r}: source view {src!r} is not defined "
                                      f"(views: {list(specs)})")
    return specs


def primary_of(cfg: "AppConfig", specs: dict[str, ViewSpec]) -> str:
    primary = cfg.primary_view or next(iter(specs))
    if primary not in specs:
        raise ViewConfigError(f"primary_view {primary!r} is not defined (views: {list(specs)})")
    return primary


def build_order(specs: dict[str, ViewSpec], wanted: Iterable[str]) -> list[str]:
    """``wanted`` views plus their sources, sources first (topological order). Raises on unknown
    names and cycles."""
    order: list[str] = []
    state: dict[str, str] = {}  # name -> "visiting" | "done"

    def visit(name: str, path: list[str]) -> None:
        if name not in specs:
            raise ViewConfigError(f"view {name!r} is not defined (views: {list(specs)})")
        st = state.get(name)
        if st == "done":
            return
        if st == "visiting":
            raise ViewConfigError(f"views form a cycle: {' -> '.join([*path, name])}")
        state[name] = "visiting"
        for src in specs[name].sources:
            visit(src, [*path, name])
        state[name] = "done"
        order.append(name)

    for w in wanted:
        visit(w, [])
    return order


def root_of(specs: dict[str, ViewSpec], name: str) -> str:
    """The ASR view a (chain of) translated view(s) starts from (primary sources only)."""
    seen = set()
    while specs[name].source is not None and name not in seen:
        seen.add(name)
        name = specs[name].source  # type: ignore[assignment]
    return name
