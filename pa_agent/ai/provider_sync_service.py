"""Provider synchronization service.

Centralizes startup synchronization for provider routes that derive settings
from the host environment (QClaw / WorkBuddy / Cursor).  Individual connector
modules still own route detection, provider mutation, persistence, and logging.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class ProviderSyncService:
    """Synchronize special AI provider routes and fallback side effects."""

    def __init__(self, *, save_path: Path | None = None) -> None:
        self._save_path = save_path

    def sync_on_load(self, settings: Any) -> None:
        """Refresh QClaw / WorkBuddy / Cursor provider settings during bootstrap."""
        from pa_agent.ai.cursor_connector import sync_cursor_provider_on_load
        from pa_agent.ai.qclaw_connector import sync_qclaw_agent_provider_on_load
        from pa_agent.ai.workbuddy_connector import sync_workbuddy_provider_on_load

        sync_qclaw_agent_provider_on_load(settings, save_path=self._save_path)
        sync_workbuddy_provider_on_load(settings, save_path=self._save_path)
        sync_cursor_provider_on_load(settings, save_path=self._save_path)

    def finish_provider_fallback(
        self,
        *,
        provider_name: str,
        err: str | None,
        settings: Any,
        client: Any,
        pending_writer: Any,
        logger: Any,
    ) -> bool:
        """Persist and publish provider changes after an auto-fallback apply step."""
        from pa_agent.config.settings import save_settings
        from pa_agent.util.logging import update_api_key

        if err:
            logger.warning("%s auto-fallback unavailable: %s", provider_name, err)
            return False

        client.update_provider(settings.provider)
        new_key = settings.provider.api_key
        try:
            save_settings(settings, self._save_path)
            update_api_key(new_key)
        except Exception as save_exc:  # noqa: BLE001
            logger.warning(
                "%s fallback applied but settings save failed: %s",
                provider_name,
                save_exc,
            )

        # Keep the record writer's masking key aligned with the rotated provider
        # key so records saved after this auto-fallback mask the new plaintext key.
        if hasattr(pending_writer, "set_api_key"):
            pending_writer.set_api_key(new_key)

        logger.info(
            "%s auto-fallback: model=%s base_url=%s",
            provider_name,
            settings.provider.model,
            settings.provider.base_url,
        )
        return True


def sync_providers_on_load(settings: Any, *, save_path: Path | None = None) -> None:
    """Convenience wrapper used by startup wiring."""
    ProviderSyncService(save_path=save_path).sync_on_load(settings)
