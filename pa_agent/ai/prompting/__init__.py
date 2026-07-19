"""Structured prompt template storage and manifest contracts."""

from pa_agent.ai.prompting.template_manifest import (
    MANIFEST_VERSION,
    TEMPLATE_MANIFEST,
    TemplateSpec,
    template_files_for_stage,
)
from pa_agent.ai.prompting.template_store import (
    TemplateSnapshot,
    TemplateStore,
    TemplateStoreError,
)

__all__ = [
    "MANIFEST_VERSION",
    "TEMPLATE_MANIFEST",
    "TemplateSnapshot",
    "TemplateSpec",
    "TemplateStore",
    "TemplateStoreError",
    "template_files_for_stage",
]
