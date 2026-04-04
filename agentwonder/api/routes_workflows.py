"""Workflow retrieval and validation routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agentwonder.compiler.validators import (
    validate_workflow,
    cross_validate_workflow,
    ConfigValidationError,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
async def list_workflows(request: Request) -> list[dict[str, Any]]:
    """List all loaded workflows (id, name, version, template)."""
    store: dict[str, dict[str, Any]] = request.app.state.workflow_store
    return [
        {
            "id": raw.get("id"),
            "name": raw.get("name"),
            "version": raw.get("version"),
            "template": raw.get("template"),
        }
        for raw in store.values()
    ]


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request) -> dict[str, Any]:
    """Get the full raw workflow definition."""
    store: dict[str, dict[str, Any]] = request.app.state.workflow_store
    raw = store.get(workflow_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return raw


@router.post("/validate")
async def validate_workflow_endpoint(
    body: dict[str, Any],
    request: Request,
) -> dict[str, Any]:
    """Pre-validate a workflow definition without executing it.

    Accepts a raw workflow dict, validates its structure and cross-references.
    Returns validation results.
    """
    # Structural validation
    try:
        wf = validate_workflow(body)
    except ConfigValidationError as exc:
        return {
            "valid": False,
            "stage": "schema_validation",
            "errors": exc.details,
        }

    # Cross-reference validation
    template_store = {t.id: t for t in request.app.state.template_registry.list_all()}
    tool_store = {t.id: t for t in request.app.state.tool_registry.list_all()}
    policy_store = {p.id: p for p in request.app.state.policy_registry.list_all()}
    prompt_store = {p.id: p for p in request.app.state.prompt_registry.list_all()}

    errors = cross_validate_workflow(
        workflow=wf,
        tools=tool_store,
        templates=template_store,
        policies=policy_store,
        prompts=prompt_store,
    )

    if errors:
        return {
            "valid": False,
            "stage": "cross_validation",
            "errors": errors,
        }

    return {
        "valid": True,
        "workflow_id": wf.id,
        "workflow_version": wf.version,
        "template": wf.template,
        "step_count": len(wf.steps),
    }
