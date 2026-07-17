"""Tests for provider synchronization service."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def _settings_with_provider() -> SimpleNamespace:
    return SimpleNamespace(
        provider=SimpleNamespace(
            model="openclaw",
            base_url="http://127.0.0.1:1234/v1",
            api_key="new-key",
        )
    )


def test_finish_provider_fallback_success_updates_client_persists_and_masks(tmp_path) -> None:
    settings = _settings_with_provider()
    client = MagicMock()
    writer = MagicMock()
    logger = MagicMock()
    save_path = tmp_path / "settings.json"

    with (
        patch("pa_agent.config.settings.save_settings") as save_settings,
        patch("pa_agent.util.logging.update_api_key") as update_api_key,
    ):
        ok = ProviderSyncService(save_path=save_path).finish_provider_fallback(
            provider_name="QClaw",
            err=None,
            settings=settings,
            client=client,
            pending_writer=writer,
            logger=logger,
        )

    assert ok is True
    client.update_provider.assert_called_once_with(settings.provider)
    save_settings.assert_called_once_with(settings, save_path)
    update_api_key.assert_called_once_with("new-key")
    writer.set_api_key.assert_called_once_with("new-key")
    logger.info.assert_called_once_with(
        "%s auto-fallback: model=%s base_url=%s",
        "QClaw",
        "openclaw",
        "http://127.0.0.1:1234/v1",
    )


def test_finish_provider_fallback_err_returns_false_without_side_effects(tmp_path) -> None:
    settings = _settings_with_provider()
    client = MagicMock()
    writer = MagicMock()
    logger = MagicMock()

    ok = ProviderSyncService(save_path=tmp_path / "settings.json").finish_provider_fallback(
        provider_name="QClaw",
        err="not available",
        settings=settings,
        client=client,
        pending_writer=writer,
        logger=logger,
    )

    assert ok is False
    logger.warning.assert_called_once_with(
        "%s auto-fallback unavailable: %s",
        "QClaw",
        "not available",
    )
    client.update_provider.assert_not_called()
    writer.set_api_key.assert_not_called()
    logger.info.assert_not_called()


def test_finish_provider_fallback_save_failure_still_updates_writer(tmp_path) -> None:
    settings = _settings_with_provider()
    client = MagicMock()
    writer = MagicMock()
    logger = MagicMock()
    save_exc = OSError("disk full")

    with (
        patch("pa_agent.config.settings.save_settings", side_effect=save_exc),
        patch("pa_agent.util.logging.update_api_key") as update_api_key,
    ):
        ok = ProviderSyncService(save_path=tmp_path / "settings.json").finish_provider_fallback(
            provider_name="WorkBuddy",
            err=None,
            settings=settings,
            client=client,
            pending_writer=writer,
            logger=logger,
        )

    assert ok is True
    client.update_provider.assert_called_once_with(settings.provider)
    update_api_key.assert_not_called()
    writer.set_api_key.assert_called_once_with("new-key")
    logger.warning.assert_called_once_with(
        "%s fallback applied but settings save failed: %s",
        "WorkBuddy",
        save_exc,
    )


def test_finish_provider_fallback_writer_without_set_api_key_is_allowed(tmp_path) -> None:
    settings = _settings_with_provider()
    client = MagicMock()
    writer = object()
    logger = MagicMock()

    with (
        patch("pa_agent.config.settings.save_settings"),
        patch("pa_agent.util.logging.update_api_key"),
    ):
        ok = ProviderSyncService(save_path=tmp_path / "settings.json").finish_provider_fallback(
            provider_name="Cursor",
            err=None,
            settings=settings,
            client=client,
            pending_writer=writer,
            logger=logger,
        )

    assert ok is True
    client.update_provider.assert_called_once_with(settings.provider)
