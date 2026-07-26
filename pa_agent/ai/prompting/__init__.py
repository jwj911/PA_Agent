"""Structured prompt template storage and manifest contracts."""

from pa_agent.ai.prompting import prompt_ids
from pa_agent.ai.prompting.compatibility import (
    load_shared_system_prompt_ids,
    load_shared_system_templates,
    make_stage1_prompt_id_loader,
    make_stage1_template_loader,
    make_stage2_template_loader,
    prepare_template_store,
)
from pa_agent.ai.prompting.prompt_catalog import PromptCatalog, PromptCatalogError
from pa_agent.ai.prompting.prompt_ids import PromptId
from pa_agent.ai.prompting.template_context import TemplateContext
from pa_agent.ai.prompting.template_manifest import (
    MANIFEST_VERSION,
    TEMPLATE_CATALOG,
    TEMPLATE_MANIFEST,
    TemplateSpec,
    template_files_for_stage,
    template_ids_for_stage,
)
from pa_agent.ai.prompting.template_store import (
    TemplateIdSnapshot,
    TemplateSnapshot,
    TemplateStore,
    TemplateStoreError,
)

__all__ = [
    "MANIFEST_VERSION",
    "TEMPLATE_CATALOG",
    "TEMPLATE_MANIFEST",
    "PromptCatalog",
    "PromptCatalogError",
    "PromptId",
    "TemplateContext",
    "TemplateIdSnapshot",
    "TemplateSnapshot",
    "TemplateSpec",
    "TemplateStore",
    "TemplateStoreError",
    "load_shared_system_prompt_ids",
    "load_shared_system_templates",
    "make_stage1_prompt_id_loader",
    "make_stage1_template_loader",
    "make_stage2_template_loader",
    "prepare_template_store",
    "prompt_ids",
    "template_files_for_stage",
    "template_ids_for_stage",
]
