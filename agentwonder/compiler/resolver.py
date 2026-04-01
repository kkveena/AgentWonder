"""Resolver — resolves cross-file references into a single resolved bundle.

After validation, a WorkflowConfig still contains string IDs pointing to tools,
prompts, policies, and a template. The resolver looks up each reference in the
appropriate registry and produces a ``ResolvedWorkflow`` that carries the full
typed objects alongside the workflow config.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from agentwonder.schemas.policy import PolicyConfig
from agentwonder.schemas.prompt import PromptConfig
from agentwonder.schemas.template import TemplateConfig
from agentwonder.schemas.tool import ToolConfig
from agentwonder.schemas.workflow import WorkflowConfig

logger = logging.getLogger(__name__)


class ResolutionError(Exception):
    """Raised when a reference cannot be resolved."""


@dataclass(frozen=True)
class ResolvedWorkflow:
    """A workflow config bundled with all of its resolved dependencies.

    This is the handoff object between the compiler and the builder.
    Everything needed to construct a RuntimePlan is available here
    without further lookups.
    """

    workflow: WorkflowConfig
    template: TemplateConfig
    tools: dict[str, ToolConfig] = field(default_factory=dict)
    prompts: dict[str, PromptConfig] = field(default_factory=dict)
    policies: dict[str, PolicyConfig] = field(default_factory=dict)


def resolve_workflow(
    workflow: WorkflowConfig,
    tools_registry: dict[str, ToolConfig],
    templates_registry: dict[str, TemplateConfig],
    prompts_registry: dict[str, PromptConfig] | None = None,
    policies_registry: dict[str, PolicyConfig] | None = None,
) -> ResolvedWorkflow:
    """Resolve all references in a validated workflow.

    Gathers the concrete config objects for every tool, prompt, policy,
    and the template referenced by the workflow.  If any reference cannot
    be found the function raises ``ResolutionError``.

    Args:
        workflow: A validated WorkflowConfig.
        tools_registry: All registered tools keyed by ID.
        templates_registry: All registered templates keyed by ID.
        prompts_registry: All registered prompts keyed by ID.
        policies_registry: All registered policies keyed by ID.

    Returns:
        A ResolvedWorkflow containing the workflow and all resolved objects.

    Raises:
        ResolutionError: If any referenced ID cannot be found.
    """
    prompts_registry = prompts_registry or {}
    policies_registry = policies_registry or {}
    errors: list[str] = []

    # -- Template -----------------------------------------------------------
    template = templates_registry.get(workflow.template)
    if template is None:
        errors.append(f"Template '{workflow.template}' not found")

    # -- Tools (top-level refs + per-step refs) -----------------------------
    all_tool_ids: set[str] = set(workflow.tool_refs)
    for step in workflow.steps:
        if step.tool:
            all_tool_ids.add(step.tool)
        all_tool_ids.update(step.tools)

    resolved_tools: dict[str, ToolConfig] = {}
    for tool_id in sorted(all_tool_ids):
        tool = tools_registry.get(tool_id)
        if tool is None:
            errors.append(f"Tool '{tool_id}' not found")
        else:
            resolved_tools[tool_id] = tool

    # -- Prompts (per-step refs) --------------------------------------------
    all_prompt_ids: set[str] = set()
    for step in workflow.steps:
        if step.prompt_ref:
            all_prompt_ids.add(step.prompt_ref)

    resolved_prompts: dict[str, PromptConfig] = {}
    for prompt_id in sorted(all_prompt_ids):
        prompt = prompts_registry.get(prompt_id)
        if prompt is None:
            errors.append(f"Prompt '{prompt_id}' not found")
        else:
            resolved_prompts[prompt_id] = prompt

    # -- Policies (per-step approval refs) ----------------------------------
    all_policy_ids: set[str] = set()
    for step in workflow.steps:
        if step.approval_ref:
            all_policy_ids.add(step.approval_ref)

    resolved_policies: dict[str, PolicyConfig] = {}
    for policy_id in sorted(all_policy_ids):
        policy = policies_registry.get(policy_id)
        if policy is None:
            errors.append(f"Policy '{policy_id}' not found")
        else:
            resolved_policies[policy_id] = policy

    # -- Raise if anything is missing ----------------------------------------
    if errors:
        raise ResolutionError(
            f"Failed to resolve workflow '{workflow.id}': " + "; ".join(errors)
        )

    assert template is not None  # guaranteed by error check above

    resolved = ResolvedWorkflow(
        workflow=workflow,
        template=template,
        tools=resolved_tools,
        prompts=resolved_prompts,
        policies=resolved_policies,
    )
    logger.info(
        "Resolved workflow '%s': %d tools, %d prompts, %d policies",
        workflow.id,
        len(resolved_tools),
        len(resolved_prompts),
        len(resolved_policies),
    )
    return resolved
