"""Provider synchronization service.

Centralizes startup synchronization for provider routes that derive settings
from the host environment (QClaw / WorkBuddy / Cursor).  Individual connector
modules still own route detection, provider mutation, persistence, and logging.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class ProviderSyncService:
    """Synchronize special AI provider routes against the local environment."""

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


def sync_providers_on_load(settings: Any, *, save_path: Path | None = None) -> None:
    """Convenience wrapper used by startup wiring."""
    ProviderSyncService(save_path=save_path).sync_on_load(settings)
