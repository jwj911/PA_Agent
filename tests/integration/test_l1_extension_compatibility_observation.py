"""Repeated observation of external-style registry extension compatibility."""

from __future__ import annotations

from dataclasses import dataclass

from pa_agent.ai.provider_registry import AIClientRegistry, AIClientSpec
from pa_agent.config.settings import AIProviderSettings
from pa_agent.data.registry import DataSourceRegistry, DataSourceSpec
from pa_agent.extensions import (
    EXTENSION_CONTRACT_VERSION,
    REGISTRAR_VERSION_ATTRIBUTE,
    discover_ai_client_extensions,
    discover_data_source_extensions,
)

OBSERVATION_ROUNDS = 5
_DATA_SOURCE_MARKER = object()
_AI_CLIENT_MARKER = object()


@dataclass(frozen=True)
class _ExternalEntryPoint:
    name: str
    registrar: object
    value: str

    def load(self) -> object:
        return self.registrar


def test_external_style_registrars_keep_versioned_and_legacy_contracts() -> None:
    observations: list[tuple[object, ...]] = []

    for _round in range(OBSERVATION_ROUNDS):
        data_registry = DataSourceRegistry()
        ai_registry = AIClientRegistry()

        data_results = discover_data_source_extensions(
            data_registry,
            entry_points_fn=lambda **_kwargs: (
                _ExternalEntryPoint(
                    name="sample_data_source",
                    registrar=_versioned_data_source_registrar,
                    value="sample_extension:register_data_source",
                ),
            ),
        )
        ai_results = discover_ai_client_extensions(
            ai_registry,
            entry_points_fn=lambda **_kwargs: (
                _ExternalEntryPoint(
                    name="legacy_ai_client",
                    registrar=_legacy_ai_client_registrar,
                    value="sample_extension:register_ai_client",
                ),
            ),
        )

        data_spec = data_registry.get("external_sample")
        ai_spec = ai_registry.resolve(AIProviderSettings(model="external-sample"))
        assert data_spec is not None
        assert ai_spec is not None

        observations.append(
            (
                data_results[0].loaded,
                data_results[0].contract_version,
                data_spec.label,
                data_spec.default_symbol,
                data_spec.builder(None) is _DATA_SOURCE_MARKER,
                ai_results[0].loaded,
                ai_results[0].contract_version,
                ai_spec.name,
                ai_spec.builder(AIProviderSettings(model="external-sample"), None)
                is _AI_CLIENT_MARKER,
            )
        )

    assert (
        observations
        == [
            (
                True,
                EXTENSION_CONTRACT_VERSION,
                "External Sample",
                "SAMPLE",
                True,
                True,
                None,
                "external_sample",
                True,
            )
        ]
        * OBSERVATION_ROUNDS
    )


def _versioned_data_source_registrar(registry: DataSourceRegistry) -> None:
    registry.register(
        DataSourceSpec(
            kind="external_sample",
            label="External Sample",
            default_symbol="SAMPLE",
            builder=lambda _settings: _DATA_SOURCE_MARKER,
            visible=True,
        )
    )


setattr(
    _versioned_data_source_registrar,
    REGISTRAR_VERSION_ATTRIBUTE,
    EXTENSION_CONTRACT_VERSION,
)


def _legacy_ai_client_registrar(registry: AIClientRegistry) -> None:
    registry.register(
        AIClientSpec(
            name="external_sample",
            matcher=lambda settings: settings.model == "external-sample",
            builder=lambda _settings, _logger: _AI_CLIENT_MARKER,
            priority=10,
        )
    )
