"""Run-related schemas — RunRequest, RunStatus, ApprovalRequest, TraceEvent."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from agentwonder.schemas.common import ApprovalOutcome, RunState


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class RunRequest(BaseModel):
    """Incoming request to execute a workflow."""

    workflow_id: str = Field(..., min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    environment: str = "dev"
    requester: str = ""


class RunStatus(BaseModel):
    """Current status of a workflow run."""

    run_id: str = Field(default_factory=_new_id)
    workflow_id: str
    workflow_version: str = ""
    template_id: str = ""
    state: RunState = RunState.PENDING
    current_step: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    outputs: dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class ApprovalRequest(BaseModel):
    """An approval gate waiting for human decision."""

    approval_id: str = Field(default_factory=_new_id)
    run_id: str
    step_id: str
    policy_id: str
    approver_roles: list[str] = Field(default_factory=list)
    requested_at: datetime = Field(default_factory=_utcnow)
    outcome: Optional[ApprovalOutcome] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None


class TraceEvent(BaseModel):
    """A single observability event captured during a run."""

    event_id: str = Field(default_factory=_new_id)
    run_id: str
    step_id: Optional[str] = None
    event_type: str = Field(..., description="e.g. step_start, step_end, tool_call, approval, error")
    timestamp: datetime = Field(default_factory=_utcnow)
    data: dict[str, Any] = Field(default_factory=dict)
