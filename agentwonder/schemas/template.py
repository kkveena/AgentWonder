"""TemplateConfig schema — validates workflow template YAML."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agentwonder.schemas.common import StepType


class TemplateConfig(BaseModel):
    """Pydantic model for an approved workflow template.

    Maps to YAML files in config/templates/.
    Templates define the structural constraints for workflows.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    allowed_step_types: list[StepType] = Field(default_factory=list)
    requires_explicit_order: bool = True
    supports_parallel: bool = False
    max_steps: int = Field(default=50, ge=1, le=200)
    description: str = ""
