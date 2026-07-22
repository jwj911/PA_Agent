"""Construct the correct AI client through the provider route registry."""

from __future__ import annotations

import logging
from typing import Any

from pa_agent.ai.cursor_connector import is_openclaw_cs_model
from pa_agent.ai.provider_registry import (
    AIClientBuilder,
    AIClientMatcher,
    AIClientRegistry,
    AIClientSpec,
)
from pa_agent.config.settings import AIProviderSettings
from pa_agent.extensions import discover_ai_client_extensions

_REGISTRY = AIClientRegistry()


def _build_cursor_client(settings: AIProviderSettings, log: logging.Logger) -> Any:
    from pa_agent.ai.cursor_sdk_client import CursorSdkClient

    log.info("AI client route: Cursor SDK (model=%s)", settings.model)
    return CursorSdkClient(settings=settings, logger_=log)


def _build_openai_compatible_client(settings: AIProviderSettings, log: logging.Logger) -> Any:
    from pa_agent.ai.deepseek_client import DeepSeekClient

    log.info(
        "AI client route: OpenAI-compatible (model=%s base_url=%s)",
        settings.model,
        settings.base_url or "(empty)",
    )
    return DeepSeekClient(settings=settings, logger_=log)


def _register_builtin_routes() -> None:
    _REGISTRY.register(
        AIClientSpec(
            name="cursor_sdk",
            matcher=lambda settings: is_openclaw_cs_model(settings.model),
            builder=_build_cursor_client,
            priority=100,
        )
    )
    _REGISTRY.register(
        AIClientSpec(
            name="openai_compatible",
            matcher=lambda _settings: True,
            builder=_build_openai_compatible_client,
            priority=-100,
        )
    )


_register_builtin_routes()
discover_ai_client_extensions(_REGISTRY)


def register_ai_client_provider(
    name: str,
    *,
    matcher: AIClientMatcher,
    builder: AIClientBuilder,
    priority: int = 0,
    replace: bool = False,
) -> None:
    """Register a custom AI client route without editing this factory."""
    _REGISTRY.register(
        AIClientSpec(
            name=name,
            matcher=matcher,
            builder=builder,
            priority=priority,
        ),
        replace=replace,
    )


def unregister_ai_client_provider(name: str) -> AIClientSpec | None:
    """Remove a runtime AI client route."""
    return _REGISTRY.unregister(name)


def ai_client_provider_specs() -> tuple[AIClientSpec, ...]:
    """Return registered AI client routes in resolution order."""
    return _REGISTRY.specs()


def create_ai_client(
    settings: AIProviderSettings,
    logger_: logging.Logger | None = None,
) -> Any:
    """Build the first matching AI client route."""
    log = logger_ or logging.getLogger(__name__)
    spec = _REGISTRY.resolve(settings)
    if spec is None:
        raise RuntimeError("No AI client provider route matched settings")
    return spec.builder(settings, log)
