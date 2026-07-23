"""Settings for orchestrator rollout controls."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OrchestratorSettings(BaseModel):
    """Orchestrator rollout switches."""

    model_config = ConfigDict(extra="ignore")

    #: New installations use PipelineBuilder after the validated rollout.
    pipeline_builder_enabled: bool = True
