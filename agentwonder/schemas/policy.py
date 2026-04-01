"""PolicyConfig schema — validates policy/approval YAML."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ApprovalPolicy(BaseModel):
    """Approval gate configuration within a policy."""

    required: bool = True
    approver_roles: list[str] = Field(default_factory=list)
    timeout_minutes: int = Field(default=60, ge=1)
    on_reject: str = Field(default="fail_run", pattern=r"^(fail_run|skip_step|retry)$")


class PolicyConfig(BaseModel):
    """Pydantic model for a governance policy.

    Maps to YAML files in config/policies/.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    approval: Optional[ApprovalPolicy] = None
    description: str = ""
