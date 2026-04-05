"""Approval management routes — list pending, submit decisions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from agentwonder.schemas.common import ApprovalOutcome
from agentwonder.schemas.run import ApprovalRequest
from agentwonder.runtime.approvals import ApprovalNotFoundError

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApprovalDecision(BaseModel):
    """Request body for submitting an approval decision."""
    outcome: ApprovalOutcome
    decided_by: str


@router.get("/pending/{run_id}", response_model=list[ApprovalRequest])
async def get_pending_approvals(run_id: str, request: Request) -> list[ApprovalRequest]:
    """Get all pending approvals for a run."""
    mgr = request.app.state.executor.approval_manager
    return mgr.get_pending(run_id)


@router.get("/run/{run_id}", response_model=list[ApprovalRequest])
async def get_all_approvals_for_run(run_id: str, request: Request) -> list[ApprovalRequest]:
    """Get all approvals (pending and decided) for a run."""
    mgr = request.app.state.executor.approval_manager
    return mgr.get_all_for_run(run_id)


@router.get("/{approval_id}", response_model=ApprovalRequest)
async def get_approval(approval_id: str, request: Request) -> ApprovalRequest:
    """Get a single approval by ID."""
    mgr = request.app.state.executor.approval_manager
    try:
        return mgr.get_approval(approval_id)
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/{approval_id}", response_model=ApprovalRequest)
async def submit_approval_decision(
    approval_id: str,
    decision: ApprovalDecision,
    request: Request,
) -> ApprovalRequest:
    """Submit a decision for an approval request."""
    mgr = request.app.state.executor.approval_manager
    try:
        return mgr.submit_decision(
            approval_id=approval_id,
            outcome=decision.outcome,
            decided_by=decision.decided_by,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
