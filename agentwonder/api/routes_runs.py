"""Run management routes — submit, query, and trace workflow runs."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from agentwonder.schemas.run import RunRequest, RunStatus, TraceEvent
from agentwonder.schemas.workflow import WorkflowConfig
from agentwonder.compiler.loader import load_yaml
from agentwonder.compiler.validators import (
    validate_workflow,
    cross_validate_workflow,
    ConfigValidationError,
)
from agentwonder.compiler.resolver import resolve_workflow, ResolutionError
from agentwonder.compiler.builder import build_plan, BuildError
from agentwonder.runtime.executor import WorkflowExecutor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


def _registries(request: Request) -> dict[str, Any]:
    """Extract registries from app state."""
    return {
        "templates": request.app.state.template_registry,
        "tools": request.app.state.tool_registry,
        "prompts": request.app.state.prompt_registry,
        "policies": request.app.state.policy_registry,
    }


@router.post("", response_model=RunStatus)
async def submit_run(run_request: RunRequest, request: Request) -> RunStatus:
    """Submit a new workflow run.

    The full pipeline is:
    1. Look up workflow YAML by id from the in-memory workflow store.
    2. Validate into WorkflowConfig.
    3. Cross-validate references against registries.
    4. Resolve all references.
    5. Build a RuntimePlan.
    6. Execute via WorkflowExecutor.
    7. Store and return RunStatus.
    """
    regs = _registries(request)
    workflow_store: dict[str, dict[str, Any]] = request.app.state.workflow_store
    run_store: dict[str, RunStatus] = request.app.state.run_store
    trace_store: dict[str, list[TraceEvent]] = request.app.state.trace_store
    executor: WorkflowExecutor = request.app.state.executor

    # 1. Look up raw workflow data
    raw = workflow_store.get(run_request.workflow_id)
    if raw is None:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{run_request.workflow_id}' not found",
        )

    # 2. Validate into WorkflowConfig
    try:
        workflow_config = validate_workflow(raw)
    except ConfigValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 3. Cross-validate references
    template_store = {t.id: t for t in regs["templates"].list_all()}
    tool_store = {t.id: t for t in regs["tools"].list_all()}
    policy_store = {p.id: p for p in regs["policies"].list_all()}
    prompt_store = {p.id: p for p in regs["prompts"].list_all()}

    errors = cross_validate_workflow(
        workflow=workflow_config,
        tools=tool_store,
        templates=template_store,
        policies=policy_store,
        prompts=prompt_store,
    )
    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Cross-validation failed", "errors": errors},
        )

    # 4. Resolve references
    try:
        resolved = resolve_workflow(
            workflow=workflow_config,
            tools_registry=tool_store,
            templates_registry=template_store,
            prompts_registry=prompt_store,
            policies_registry=policy_store,
        )
    except ResolutionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 5. Build RuntimePlan
    try:
        plan = build_plan(resolved)
    except BuildError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # 6. Execute
    status = await executor.execute(run_request, plan)

    # 7. Persist results in memory
    run_store[status.run_id] = status

    # Collect trace events from the session store
    session_data = executor.session_store.get_session(status.run_id)
    if session_data and "trace_events" in session_data.get("data", {}):
        trace_events = [
            TraceEvent.model_validate(evt)
            for evt in session_data["data"]["trace_events"]
        ]
        trace_store[status.run_id] = trace_events

    logger.info("Run '%s' completed with state '%s'", status.run_id, status.state.value)
    return status


@router.get("/{run_id}", response_model=RunStatus)
async def get_run(run_id: str, request: Request) -> RunStatus:
    """Retrieve the status of a workflow run by its ID."""
    run_store: dict[str, RunStatus] = request.app.state.run_store
    status = run_store.get(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return status


@router.get("/{run_id}/trace", response_model=list[TraceEvent])
async def get_run_trace(run_id: str, request: Request) -> list[TraceEvent]:
    """Retrieve the trace events for a workflow run."""
    trace_store: dict[str, list[TraceEvent]] = request.app.state.trace_store
    events = trace_store.get(run_id)
    if events is None:
        raise HTTPException(
            status_code=404,
            detail=f"No trace found for run '{run_id}'",
        )
    return events
