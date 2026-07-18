"""Tests for AI client factory routing."""

from __future__ import annotations

import pytest

from pa_agent.ai.client_factory import (
    ai_client_provider_specs,
    create_ai_client,
    register_ai_client_provider,
    unregister_ai_client_provider,
)
from pa_agent.ai.cursor_sdk_client import CursorSdkClient
from pa_agent.ai.deepseek_client import DeepSeekClient
from pa_agent.config.settings import AIProviderSettings


def test_create_ai_client_openclaw_cs_uses_cursor_sdk() -> None:
    settings = AIProviderSettings(
        model="openclaw_cs",
        base_url="",
        api_key="crsr_test",
    )
    client = create_ai_client(settings)
    assert isinstance(client, CursorSdkClient)


def test_create_ai_client_openclaw_uses_deepseek_client() -> None:
    settings = AIProviderSettings(
        model="openclaw",
        base_url="http://127.0.0.1:19000/v1",
        api_key="test",
    )
    client = create_ai_client(settings)
    assert isinstance(client, DeepSeekClient)


def test_ai_client_provider_registry_keeps_builtin_priority_order() -> None:
    names = [spec.name for spec in ai_client_provider_specs()]

    assert names[:2] == ["cursor_sdk", "openai_compatible"]


def test_custom_ai_client_provider_precedes_openai_fallback() -> None:
    marker = object()
    register_ai_client_provider(
        "test_provider",
        matcher=lambda settings: settings.model == "test-provider",
        builder=lambda _settings, _logger: marker,
    )
    try:
        settings = AIProviderSettings(model="test-provider")
        assert create_ai_client(settings) is marker
    finally:
        unregister_ai_client_provider("test_provider")


def test_custom_ai_client_provider_rejects_duplicate_name() -> None:
    def builder(_settings, _logger):
        return object()

    register_ai_client_provider("test_provider", matcher=lambda _settings: False, builder=builder)
    try:
        with pytest.raises(ValueError, match="already registered"):
            register_ai_client_provider(
                "test_provider",
                matcher=lambda _settings: True,
                builder=builder,
            )
    finally:
        unregister_ai_client_provider("test_provider")
