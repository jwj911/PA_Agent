"""Thread-safe registry primitives for AI client provider routes."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pa_agent.config.settings import AIProviderSettings

AIClientMatcher = Callable[["AIProviderSettings"], bool]
AIClientBuilder = Callable[["AIProviderSettings", logging.Logger], Any]


@dataclass(frozen=True)
class AIClientSpec:
    """One provider route matcher and its lazy client builder."""

    name: str
    matcher: AIClientMatcher
    builder: AIClientBuilder
    priority: int = 0


class AIClientRegistry:
    """Resolve provider routes without importing concrete clients eagerly."""

    def __init__(self) -> None:
        self._specs: dict[str, AIClientSpec] = {}
        self._lock = RLock()

    def register(self, spec: AIClientSpec, *, replace: bool = False) -> None:
        """Register a route, rejecting duplicate names unless replacing."""
        name = str(spec.name or "").strip()
        if not name:
            raise ValueError("AI client provider name must not be empty")
        if name != spec.name:
            spec = AIClientSpec(
                name=name,
                matcher=spec.matcher,
                builder=spec.builder,
                priority=spec.priority,
            )
        with self._lock:
            if name in self._specs and not replace:
                raise ValueError(f"AI client provider already registered: {name}")
            self._specs[name] = spec

    def unregister(self, name: str) -> AIClientSpec | None:
        """Remove and return a route, or ``None`` when absent."""
        with self._lock:
            return self._specs.pop(str(name or "").strip(), None)

    def specs(self) -> tuple[AIClientSpec, ...]:
        """Return routes in descending priority and stable registration order."""
        with self._lock:
            values = tuple(self._specs.values())
        return tuple(sorted(values, key=lambda spec: spec.priority, reverse=True))

    def resolve(self, settings: AIProviderSettings) -> AIClientSpec | None:
        """Return the first matching route; matchers run outside the registry lock."""
        for spec in self.specs():
            if spec.matcher(settings):
                return spec
        return None
