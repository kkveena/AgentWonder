"""Builder — converts a ResolvedWorkflow into a RuntimePlan.

The RuntimePlan is the bridge between the compiler and the runtime executor.
It contains fully resolved, execution-ready step objects with all references
inlined, dependency order computed, and approval gates identified.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from agentwonder.schemas.common import StepType
from agentwonder.schemas.policy import PolicyConfig
from agentwonder.schemas.prompt import PromptConfig
from agentwonder.schemas.tool import ToolConfig
from agentwonder.schemas.workflow import ModelSettings, WorkflowStep

from agentwonder.compiler.resolver import ResolvedWorkflow

logger = logging.getLogger(__name__)


class BuildError(Exception):
    """Raised when a RuntimePlan cannot be constructed."""


# ---------------------------------------------------------------------------
# Runtime step model
# ---------------------------------------------------------------------------

class RuntimeStep(BaseModel):
    """A single execution-ready step within a RuntimePlan.

    Unlike WorkflowStep (which carries string references), RuntimeStep
    carries the resolved config objects needed for execution.
    """

    id: str
    type: StepType
    description: str = ""

    # Resolved tool config (for tool_call steps)
    tool: Optional[ToolConfig] = None

    # Resolved tool configs (for llm_agent steps with multiple tools)
    tools: list[ToolConfig] = Field(default_factory=list)

    # Resolved prompt text (for steps that reference a prompt)
    prompt: Optional[PromptConfig] = None

    # Resolved approval policy (for approval steps)
    approval_policy: Optional[PolicyConfig] = None

    # Model to use for this step (inherits from workflow default if not set)
    model: Optional[str] = None

    # Step dependencies (IDs of steps that must complete first)
    depends_on: list[str] = Field(default_factory=list)

    # Pass-through inputs from the workflow step definition
    inputs: dict[str, Any] = Field(default_factory=dict)

    # Whether this step requires approval before or after execution
    requires_approval: bool = False

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Runtime plan model
# ---------------------------------------------------------------------------

class RuntimePlan(BaseModel):
    """Fully resolved, execution-ready workflow plan.

    This is the object handed to the runtime executor. It contains
    everything needed to run the workflow without further lookups.
    """

    workflow_id: str
    workflow_version: str
    template_id: str
    template_version: str

    # Model settings for the run
    models: ModelSettings

    # Ordered list of runtime steps
    steps: list[RuntimeStep]

    # Computed execution order (list of step IDs in topological order)
    execution_order: list[str]

    # Steps that can run in parallel (groups of step IDs)
    parallel_groups: list[list[str]] = Field(default_factory=list)

    # Quick lookup: steps that require approval gates
    approval_step_ids: list[str] = Field(default_factory=list)

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def _compute_execution_order(steps: list[WorkflowStep]) -> list[str]:
    """Compute topological execution order based on depends_on relationships.

    Steps without dependencies come first. Steps are otherwise ordered
    by their position in the workflow definition (stable sort).

    Raises:
        BuildError: If a cycle is detected in dependencies.
    """
    step_map = {s.id: s for s in steps}
    visited: set[str] = set()
    in_progress: set[str] = set()
    order: list[str] = []

    def visit(step_id: str) -> None:
        if step_id in visited:
            return
        if step_id in in_progress:
            raise BuildError(f"Cycle detected in step dependencies involving '{step_id}'")
        in_progress.add(step_id)
        step = step_map[step_id]
        for dep in step.depends_on:
            if dep not in step_map:
                raise BuildError(
                    f"Step '{step_id}' depends on unknown step '{dep}'"
                )
            visit(dep)
        in_progress.remove(step_id)
        visited.add(step_id)
        order.append(step_id)

    for step in steps:
        visit(step.id)

    return order


def _compute_parallel_groups(
    steps: list[WorkflowStep],
    execution_order: list[str],
) -> list[list[str]]:
    """Group steps that can execute in parallel.

    Steps sharing the same set of dependencies (or no dependencies)
    and appearing at the same depth level can run concurrently.
    """
    step_map = {s.id: s for s in steps}
    # Compute depth: max dependency depth + 1
    depths: dict[str, int] = {}

    def depth_of(step_id: str) -> int:
        if step_id in depths:
            return depths[step_id]
        step = step_map[step_id]
        if not step.depends_on:
            depths[step_id] = 0
            return 0
        d = max(depth_of(dep) for dep in step.depends_on) + 1
        depths[step_id] = d
        return d

    for sid in execution_order:
        depth_of(sid)

    # Group by depth, preserving execution_order within each group
    max_depth = max(depths.values(), default=-1)
    groups: list[list[str]] = []
    for d in range(max_depth + 1):
        group = [sid for sid in execution_order if depths[sid] == d]
        if group:
            groups.append(group)

    return groups


def _build_runtime_step(
    step: WorkflowStep,
    resolved: ResolvedWorkflow,
    default_model: str,
) -> RuntimeStep:
    """Convert a WorkflowStep + resolved references into a RuntimeStep."""
    # Resolve single tool
    tool = resolved.tools.get(step.tool) if step.tool else None

    # Resolve multiple tools
    tools = [resolved.tools[t] for t in step.tools if t in resolved.tools]

    # Resolve prompt
    prompt = resolved.prompts.get(step.prompt_ref) if step.prompt_ref else None

    # Resolve approval policy
    approval_policy = (
        resolved.policies.get(step.approval_ref) if step.approval_ref else None
    )

    # Determine if approval is required
    requires_approval = (
        step.type == StepType.APPROVAL
        or approval_policy is not None
        or (tool is not None and tool.approval_required)
    )

    # Determine model: step-level override > workflow default
    model = step.model or default_model

    return RuntimeStep(
        id=step.id,
        type=step.type,
        description=step.description,
        tool=tool,
        tools=tools,
        prompt=prompt,
        approval_policy=approval_policy,
        model=model,
        depends_on=step.depends_on,
        inputs=step.inputs,
        requires_approval=requires_approval,
    )


def build_plan(resolved: ResolvedWorkflow) -> RuntimePlan:
    """Build a RuntimePlan from a ResolvedWorkflow.

    This is the main entry point for the builder. It converts all
    workflow steps into RuntimeSteps, computes execution order and
    parallel groups, and packages everything into a RuntimePlan.

    Args:
        resolved: A fully resolved workflow bundle.

    Returns:
        A RuntimePlan ready for execution.

    Raises:
        BuildError: If the plan cannot be constructed (e.g. dependency cycles).
    """
    wf = resolved.workflow
    default_model = wf.models.default

    # Compute execution order
    execution_order = _compute_execution_order(wf.steps)

    # Compute parallel groups
    parallel_groups = _compute_parallel_groups(wf.steps, execution_order)

    # Build runtime steps
    runtime_steps: list[RuntimeStep] = []
    for step in wf.steps:
        runtime_steps.append(
            _build_runtime_step(step, resolved, default_model)
        )

    # Identify approval steps
    approval_step_ids = [s.id for s in runtime_steps if s.requires_approval]

    plan = RuntimePlan(
        workflow_id=wf.id,
        workflow_version=wf.version,
        template_id=resolved.template.id,
        template_version=resolved.template.version,
        models=wf.models,
        steps=runtime_steps,
        execution_order=execution_order,
        parallel_groups=parallel_groups,
        approval_step_ids=approval_step_ids,
    )

    logger.info(
        "Built RuntimePlan for '%s' v%s: %d steps, %d parallel groups, %d approval gates",
        plan.workflow_id,
        plan.workflow_version,
        len(plan.steps),
        len(plan.parallel_groups),
        len(plan.approval_step_ids),
    )
    return plan
