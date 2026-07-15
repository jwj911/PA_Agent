"""Tests for provider synchronization service."""
from __future__ import annotations

from pa_agent.ai.provider_sync_service import ProviderSyncService


def test_provider_sync_service_calls_connectors_in_order(monkeypatch, tmp_path) -> None:
    calls: list[tuple[str, object, object]] = []
    settings = object()
    save_path = tmp_path / "settings.json"

    def record(name: str):
        def _sync(obj: object, *, save_path: object = None) -> None:
            calls.append((name, obj, save_path))

        return _sync

    monkeypatch.setattr(
        "pa_agent.ai.qclaw_connector.sync_qclaw_agent_provider_on_load",
        record("qclaw"),
    )
    monkeypatch.setattr(
        "pa_agent.ai.workbuddy_connector.sync_workbuddy_provider_on_load",
        record("workbuddy"),
    )
    monkeypatch.setattr(
        "pa_agent.ai.cursor_connector.sync_cursor_provider_on_load",
        record("cursor"),
    )

    ProviderSyncService(save_path=save_path).sync_on_load(settings)

    assert calls == [
        ("qclaw", settings, save_path),
        ("workbuddy", settings, save_path),
        ("cursor", settings, save_path),
    ]
