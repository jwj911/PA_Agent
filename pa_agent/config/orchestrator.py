"""Settings for orchestrator rollout controls."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class OrchestratorSettings(BaseModel):
    """Orchestrator rollout switches."""

    model_config = ConfigDict(extra="ignore")

    #: Keep the explicit PipelineBuilder migration opt-in until equivalence is proven.
    pipeline_builder_enabled: bool = False
