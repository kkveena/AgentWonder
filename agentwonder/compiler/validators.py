"""Validators — convert raw dicts to Pydantic models and cross-validate references.

Single-model validation catches structural issues (missing fields, bad types).
Cross-validation catches referential integrity issues (tool refs that don't
exist, step types not allowed by the template, write tools without approvals).
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from agentwonder.schemas.common import SideEffectLevel, StepType
from agentwonder.schemas.policy import PolicyConfig
from agentwonder.schemas.prompt import PromptConfig
from agentwonder.schemas.template import TemplateConfig
from agentwonder.schemas.tool import ToolConfig
from agentwonder.schemas.workflow import WorkflowConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class ConfigValidationError(Exception):
    """Raised when config data fails Pydantic or cross-reference validation."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        self.details = details or []
        super().__init__(message)


# ---------------------------------------------------------------------------
# Single-model validators
# ---------------------------------------------------------------------------

def _validate_model(data: dict[str, Any], model_cls: type, label: str):
    """Generic helper: validate a dict against a Pydantic model class."""
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        errors = [f"  - {e['loc']}: {e['msg']}" for e in exc.errors()]
        raise ConfigValidationError(
            f"Validation failed for {label}",
            details=errors,
        ) from exc


def validate_workflow(data: dict[str, Any]) -> WorkflowConfig:
    """Validate a raw dict into a ``WorkflowConfig``."""
    return _validate_model(data, WorkflowConfig, f"workflow '{data.get('id', '?')}'")


def validate_tool(data: dict[str, Any]) -> ToolConfig:
    """Validate a raw dict into a ``ToolConfig``."""
    return _validate_model(data, ToolConfig, f"tool '{data.get('id', '?')}'")


def validate_template(data: dict[str, Any]) -> TemplateConfig:
    """Validate a raw dict into a ``TemplateConfig``."""
    return _validate_model(data, TemplateConfig, f"template '{data.get('id', '?')}'")


def validate_policy(data: dict[str, Any]) -> PolicyConfig:
    """Validate a raw dict into a ``PolicyConfig``."""
    return _validate_model(data, PolicyConfig, f"policy '{data.get('id', '?')}'")


def validate_prompt(data: dict[str, Any]) -> PromptConfig:
    """Validate a raw dict into a ``PromptConfig``."""
    return _validate_model(data, PromptConfig, f"prompt '{data.get('id', '?')}'")


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------

def cross_validate_workflow(
    workflow: WorkflowConfig,
    tools: dict[str, ToolConfig],
    templates: dict[str, TemplateConfig],
    policies: dict[str, PolicyConfig],
    prompts: dict[str, PromptConfig] | None = None,
) -> list[str]:
    """Check referential integrity of a validated workflow.

    Verifies:
    - The referenced template exists.
    - Every tool_ref in the workflow points to a registered tool.
    - Every step's ``tool`` field (if set) points to a registered tool.
    - Every step's ``prompt_ref`` (if set) points to a registered prompt.
    - Every step's ``approval_ref`` (if set) points to a registered policy.
    - Step types are allowed by the template.
    - Write/delete tools have an associated approval configuration.
    - Step dependency references (``depends_on``) point to existing step IDs.
    - The workflow does not exceed the template's ``max_steps`` limit.

    Args:
        workflow: A validated WorkflowConfig.
        tools: Registry of available tools keyed by ID.
        templates: Registry of available templates keyed by ID.
        policies: Registry of available policies keyed by ID.
        prompts: Registry of available prompts keyed by ID (optional).

    Returns:
        A list of error strings. An empty list means the workflow is valid.
    """
    prompts = prompts or {}
    errors: list[str] = []

    # -- Template reference --------------------------------------------------
    template = templates.get(workflow.template)
    if template is None:
        errors.append(
            f"Workflow '{workflow.id}' references unknown template '{workflow.template}'"
        )
    else:
        # Step-type constraints
        if template.allowed_step_types:
            allowed = set(template.allowed_step_types)
            for step in workflow.steps:
                if step.type not in allowed:
                    errors.append(
                        f"Step '{step.id}' uses type '{step.type.value}' which is not "
                        f"allowed by template '{template.id}' "
                        f"(allowed: {[t.value for t in template.allowed_step_types]})"
                    )

        # Max steps
        if len(workflow.steps) > template.max_steps:
            errors.append(
                f"Workflow '{workflow.id}' has {len(workflow.steps)} steps, "
                f"exceeding template '{template.id}' max of {template.max_steps}"
            )

    # -- Top-level tool_refs -------------------------------------------------
    for tool_ref in workflow.tool_refs:
        if tool_ref not in tools:
            errors.append(
                f"Workflow '{workflow.id}' references unknown tool '{tool_ref}'"
            )

    # -- Per-step checks -----------------------------------------------------
    step_ids = {s.id for s in workflow.steps}

    for step in workflow.steps:
        # Tool reference on step
        if step.tool and step.tool not in tools:
            errors.append(
                f"Step '{step.id}' references unknown tool '{step.tool}'"
            )

        # Tools list on step (e.g. for llm_agent steps with multiple tools)
        for t in step.tools:
            if t not in tools:
                errors.append(
                    f"Step '{step.id}' references unknown tool '{t}'"
                )

        # Prompt reference
        if step.prompt_ref and step.prompt_ref not in prompts:
            errors.append(
                f"Step '{step.id}' references unknown prompt '{step.prompt_ref}'"
            )

        # Approval reference
        if step.approval_ref and step.approval_ref not in policies:
            errors.append(
                f"Step '{step.id}' references unknown policy '{step.approval_ref}'"
            )

        # Depends-on references
        for dep in step.depends_on:
            if dep not in step_ids:
                errors.append(
                    f"Step '{step.id}' depends on unknown step '{dep}'"
                )

        # Write/delete tools must have approval configured
        if step.tool and step.tool in tools:
            tool_cfg = tools[step.tool]
            if tool_cfg.side_effect_level in (
                SideEffectLevel.WRITE,
                SideEffectLevel.DELETE,
            ):
                has_approval = (
                    step.approval_ref is not None
                    or tool_cfg.approval_required
                )
                if not has_approval:
                    errors.append(
                        f"Step '{step.id}' uses tool '{step.tool}' with side effect "
                        f"level '{tool_cfg.side_effect_level.value}' but has no "
                        f"approval_ref and tool does not require approval"
                    )

    if errors:
        logger.warning(
            "Cross-validation found %d issue(s) for workflow '%s'",
            len(errors),
            workflow.id,
        )
    else:
        logger.debug("Cross-validation passed for workflow '%s'", workflow.id)

    return errors
