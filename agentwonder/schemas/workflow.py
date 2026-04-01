"""WorkflowConfig schema — validates workflow definition YAML."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator

from agentwonder.schemas.common import StepType


class ModelSettings(BaseModel):
    """Model selection for a workflow."""

    default: str = "gemini-2.5-flash"
    evaluator: Optional[str] = None


class InputSpec(BaseModel):
    """Declares required and optional inputs for a workflow."""

    required: list[str] = Field(default_factory=list)
    optional: list[str] = Field(default_factory=list)


class OutputSpec(BaseModel):
    """Declares the output format of a workflow."""

    format: str = "json"
    schema_ref: Optional[str] = None


class EvalSpec(BaseModel):
    """Evaluation suite reference for a workflow."""

    suite: Optional[str] = None


class WorkflowStep(BaseModel):
    """A single step within a workflow definition."""

    id: str = Field(..., min_length=1)
    type: StepType
    tool: Optional[str] = None
    tools: list[str] = Field(default_factory=list)
    prompt_ref: Optional[str] = None
    approval_ref: Optional[str] = None
    model: Optional[str] = None
    depends_on: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)
    description: str = ""

    @model_validator(mode="after")
    def validate_step_requirements(self) -> "WorkflowStep":
        if self.type == StepType.TOOL_CALL and not self.tool:
            raise ValueError(f"Step '{self.id}': tool_call requires 'tool' field")
        if self.type == StepType.APPROVAL and not self.approval_ref:
            raise ValueError(f"Step '{self.id}': approval requires 'approval_ref'")
        return self


class WorkflowConfig(BaseModel):
    """Pydantic model for a complete workflow definition.

    Maps to YAML files in config/workflows/.
    This is the top-level schema that references tools, prompts,
    policies, and templates by ID.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    owner_team: str = Field(default="")
    template: str = Field(..., min_length=1, description="Template ID reference")
    description: str = ""
    models: ModelSettings = Field(default_factory=ModelSettings)
    tool_refs: list[str] = Field(default_factory=list)
    inputs: InputSpec = Field(default_factory=InputSpec)
    steps: list[WorkflowStep] = Field(..., min_length=1)
    output: OutputSpec = Field(default_factory=OutputSpec)
    evals: EvalSpec = Field(default_factory=EvalSpec)

    @model_validator(mode="after")
    def validate_step_ids_unique(self) -> "WorkflowConfig":
        ids = [s.id for s in self.steps]
        if len(ids) != len(set(ids)):
            raise ValueError("Workflow step IDs must be unique")
        return self
