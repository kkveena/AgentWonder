"""TemplateConfig schema — validates workflow template YAML."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agentwonder.schemas.common import StepType


class TransitionRule(BaseModel):
    """Defines allowed transitions between step types in a template."""

    from_type: StepType = Field(..., alias="from")
    to_types: list[StepType] = Field(default_factory=list, alias="to")

    model_config = {"populate_by_name": True}


class TemplateConfig(BaseModel):
    """Pydantic model for an approved workflow template.

    Maps to YAML files in config/templates/.
    Templates define the structural constraints for workflows.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    description: str = ""
    allowed_step_types: list[StepType] = Field(default_factory=list)
    requires_explicit_order: bool = True
    supports_parallel: bool = False
    max_steps: int = Field(default=50, ge=1, le=200)

    # Phase 2 fields
    required_sections: list[str] = Field(
        default_factory=list,
        description="YAML sections that must be present in workflows using this template",
    )
    allowed_transitions: list[TransitionRule] = Field(
        default_factory=list,
        description="Allowed step-type transitions; empty means unrestricted",
    )
    requires_approval: bool = Field(
        default=False,
        description="Whether workflows using this template must include an approval step",
    )
    supported_models: list[str] = Field(
        default_factory=list,
        description="Model names/patterns allowed for this template; empty means any",
    )
    supports_loop: bool = Field(
        default=False,
        description="Whether this template supports evaluator loop (retry) patterns",
    )
    max_parallel_branches: int = Field(
        default=1, ge=1, le=50,
        description="Max concurrent branches for parallel templates",
    )
