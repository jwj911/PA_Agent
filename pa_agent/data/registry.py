"""Extensible registry primitives for lazily-created market data sources."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING

from pa_agent.data.base import DataSource

if TYPE_CHECKING:
    from pa_agent.config.settings import Settings

DataSourceBuilder = Callable[["Settings | None"], DataSource]


def _normalize_kind(kind: str | None) -> str:
    """Return the canonical registry key without changing its case."""
    return str(kind or "").strip()


@dataclass(frozen=True)
class DataSourceSpec:
    """Metadata and lazy builder for one data-source kind."""

    kind: str
    label: str
    default_symbol: str
    builder: DataSourceBuilder
    visible: bool = False


class DataSourceRegistry:
    """Mutable registry used to discover and instantiate data sources."""

    def __init__(self) -> None:
        self._specs: dict[str, DataSourceSpec] = {}
        self._lock = RLock()

    def register(self, spec: DataSourceSpec, *, replace: bool = False) -> None:
        """Register *spec*, rejecting accidental kind collisions by default."""
        kind = _normalize_kind(spec.kind)
        if not kind:
            raise ValueError("Data source kind must not be empty")
        if kind != spec.kind:
            spec = DataSourceSpec(
                kind=kind,
                label=spec.label,
                default_symbol=spec.default_symbol,
                builder=spec.builder,
                visible=spec.visible,
            )
        with self._lock:
            if kind in self._specs and not replace:
                raise ValueError(f"Data source kind already registered: {kind}")
            self._specs[kind] = spec

    def unregister(self, kind: str) -> DataSourceSpec | None:
        """Remove and return a registered spec, or ``None`` when absent."""
        with self._lock:
            return self._specs.pop(_normalize_kind(kind), None)

    def get(self, kind: str) -> DataSourceSpec | None:
        """Return a spec by canonical kind."""
        with self._lock:
            return self._specs.get(_normalize_kind(kind))

    def specs(self, *, visible_only: bool = False) -> tuple[DataSourceSpec, ...]:
        """Return registered specs in registration order."""
        with self._lock:
            values = tuple(self._specs.values())
        if visible_only:
            return tuple(spec for spec in values if spec.visible)
        return values

    def choices(self) -> tuple[tuple[str, str], ...]:
        """Return UI choices from currently visible registered sources."""
        return tuple((spec.kind, spec.label) for spec in self.specs(visible_only=True))
