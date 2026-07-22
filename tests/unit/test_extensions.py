"""Tests for installed entry-point extension discovery."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pa_agent.ai.provider_registry import AIClientRegistry, AIClientSpec
from pa_agent.data.registry import DataSourceRegistry, DataSourceSpec
from pa_agent.extensions import (
    DATA_SOURCE_ENTRY_POINT_GROUP,
    EXTENSION_CONTRACT_VERSION,
    REGISTRAR_VERSION_ATTRIBUTE,
    discover_ai_client_extensions,
    discover_data_source_extensions,
)


@dataclass
class _EntryPoint:
    name: str
    registrar: object
    value: str = ""

    def load(self) -> object:
        if isinstance(self.registrar, BaseException):
            raise self.registrar
        return self.registrar


def test_data_source_entry_points_are_sorted_and_registered() -> None:
    registry = DataSourceRegistry()
    requested_groups: list[str] = []

    def entry_points_fn(*, group: str):
        requested_groups.append(group)
        return [
            _EntryPoint("z_source", lambda target: target.register(_source_spec("z"))),
            _EntryPoint("a_source", lambda target: target.register(_source_spec("a"))),
        ]

    results = discover_data_source_extensions(registry, entry_points_fn=entry_points_fn)

    assert requested_groups == [DATA_SOURCE_ENTRY_POINT_GROUP]
    assert [(item.name, item.loaded) for item in results] == [
        ("a_source", True),
        ("z_source", True),
    ]
    assert [spec.kind for spec in registry.specs()] == ["a", "z"]


def test_ai_entry_point_failure_isolated_from_other_extensions(caplog) -> None:
    registry = AIClientRegistry()
    entries = [
        _EntryPoint("broken", RuntimeError("provider-secret-value")),
        _EntryPoint(
            "working",
            lambda target: target.register(
                AIClientSpec(
                    name="working",
                    matcher=lambda _settings: True,
                    builder=lambda _settings, _logger: object(),
                )
            ),
        ),
    ]

    with caplog.at_level(logging.INFO, logger="pa_agent.extensions"):
        results = discover_ai_client_extensions(
            registry,
            entry_points_fn=lambda **_kwargs: entries,
        )

    assert [(item.name, item.loaded, item.error_type) for item in results] == [
        ("broken", False, "RuntimeError"),
        ("working", True, None),
    ]
    assert [spec.name for spec in registry.specs()] == ["working"]
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert "provider-secret-value" not in messages
    assert "RuntimeError" in messages


def test_discovery_handles_entry_point_api_selection() -> None:
    registry = DataSourceRegistry()
    selected: list[str] = []

    class _Selectable:
        def select(self, *, group: str):
            selected.append(group)
            return [
                _EntryPoint("selected", lambda target: target.register(_source_spec("selected")))
            ]

    results = discover_data_source_extensions(
        registry,
        entry_points_fn=lambda **_kwargs: _Selectable(),
    )

    assert selected == [DATA_SOURCE_ENTRY_POINT_GROUP]
    assert results[0].loaded is True
    assert registry.get("selected") is not None


def test_versioned_registrar_reports_contract_and_legacy_callable_stays_compatible() -> None:
    registry = DataSourceRegistry()

    def versioned(target):
        target.register(_source_spec("versioned"))

    setattr(versioned, REGISTRAR_VERSION_ATTRIBUTE, EXTENSION_CONTRACT_VERSION)

    entries = [
        _EntryPoint("legacy", lambda target: target.register(_source_spec("legacy"))),
        _EntryPoint("versioned", versioned),
    ]
    results = discover_data_source_extensions(
        registry,
        entry_points_fn=lambda **_kwargs: entries,
    )

    assert [(item.name, item.loaded, item.contract_version) for item in results] == [
        ("legacy", True, None),
        ("versioned", True, EXTENSION_CONTRACT_VERSION),
    ]
    assert [spec.kind for spec in registry.specs()] == ["legacy", "versioned"]


def test_unsupported_registrar_contract_isolated_from_valid_extension() -> None:
    registry = DataSourceRegistry()

    def unsupported(_target):
        raise AssertionError("unsupported registrar must not execute")

    setattr(unsupported, REGISTRAR_VERSION_ATTRIBUTE, "pa-agent.registry-extension.v0")
    entries = [
        _EntryPoint("unsupported", unsupported),
        _EntryPoint("valid", lambda target: target.register(_source_spec("valid"))),
    ]

    results = discover_data_source_extensions(
        registry,
        entry_points_fn=lambda **_kwargs: entries,
    )

    assert [(item.name, item.loaded, item.error_type) for item in results] == [
        ("unsupported", False, "ExtensionContractError"),
        ("valid", True, None),
    ]
    assert [spec.kind for spec in registry.specs()] == ["valid"]


def _source_spec(kind: str) -> DataSourceSpec:
    return DataSourceSpec(
        kind=kind,
        label=kind,
        default_symbol=kind,
        builder=lambda _settings: object(),
    )
