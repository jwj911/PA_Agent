"""Unit tests for L1 registry contracts and lifecycle behavior."""

from __future__ import annotations

import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from pa_agent.ai.provider_registry import AIClientRegistry, AIClientSpec
from pa_agent.config.settings import AIProviderSettings
from pa_agent.data.registry import DataSourceRegistry, DataSourceSpec


def _data_spec(kind: str, marker: object, *, visible: bool = False) -> DataSourceSpec:
    return DataSourceSpec(
        kind=kind,
        label=kind,
        default_symbol="TEST",
        builder=lambda _settings: marker,
        visible=visible,
    )


def _client_spec(name: str, priority: int, marker: object) -> AIClientSpec:
    return AIClientSpec(
        name=name,
        matcher=lambda _settings: True,
        builder=lambda _settings, _logger: marker,
        priority=priority,
    )


def test_data_registry_normalizes_duplicate_names_and_replace_lifecycle() -> None:
    registry = DataSourceRegistry()
    first = object()
    replacement = object()

    registry.register(_data_spec("  test_source  ", first))
    stored = registry.get(" test_source ")
    assert stored is not None
    assert stored.kind == "test_source"
    assert stored.builder(None) is first
    with pytest.raises(ValueError, match="already registered"):
        registry.register(_data_spec("test_source", object()))

    registry.register(_data_spec("test_source", replacement, visible=True), replace=True)
    stored = registry.get("test_source")
    assert stored is not None
    assert stored.builder(None) is replacement
    assert stored.visible is True
    assert registry.specs() == (stored,)

    removed = registry.unregister(" test_source ")
    assert removed is stored
    assert registry.get("test_source") is None
    assert registry.unregister("test_source") is None


def test_ai_registry_resolves_by_priority_with_stable_ties() -> None:
    registry = AIClientRegistry()
    low = object()
    first_high = object()
    second_high = object()

    registry.register(_client_spec("low", priority=0, marker=low))
    registry.register(_client_spec("first_high", priority=10, marker=first_high))
    registry.register(_client_spec("second_high", priority=10, marker=second_high))

    assert [spec.name for spec in registry.specs()] == [
        "first_high",
        "second_high",
        "low",
    ]
    resolved = registry.resolve(AIProviderSettings())
    assert resolved is not None
    assert resolved.name == "first_high"

    registry.register(_client_spec("first_high", priority=-10, marker=object()), replace=True)
    assert [spec.name for spec in registry.specs()] == [
        "second_high",
        "low",
        "first_high",
    ]
    resolved = registry.resolve(AIProviderSettings())
    assert resolved is not None
    assert resolved.name == "second_high"


def test_data_registry_register_get_unregister_is_thread_safe() -> None:
    registry = DataSourceRegistry()
    worker_count = 8
    barrier = Barrier(worker_count)

    def worker(index: int) -> DataSourceSpec:
        key = f"source_{index}"
        barrier.wait(timeout=5)
        registry.register(_data_spec(f" {key} ", object()))
        observed = registry.get(f" {key} ")
        assert observed is not None
        removed = registry.unregister(f" {key} ")
        assert removed is observed
        return removed

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        removed_specs = list(executor.map(worker, range(worker_count)))

    assert [spec.kind for spec in removed_specs] == [
        f"source_{index}" for index in range(worker_count)
    ]
    assert registry.specs() == ()


def test_client_factory_import_is_lazy() -> None:
    root = Path(__file__).resolve().parents[2]
    script = """
import sys

import pa_agent.ai.client_factory

assert "pa_agent.ai.cursor_sdk_client" not in sys.modules
assert "pa_agent.ai.deepseek_client" not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
