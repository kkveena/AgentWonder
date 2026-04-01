"""ToolConfig schema — validates tool registration YAML."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agentwonder.schemas.common import SideEffectLevel, Environment


class RetryPolicy(BaseModel):
    """Retry configuration for tool invocations."""

    max_retries: int = Field(default=1, ge=0, le=10)
    backoff_seconds: float = Field(default=1.0, ge=0)


class AuthConfig(BaseModel):
    """Authentication configuration for a tool endpoint."""

    type: str = Field(..., description="Auth type, e.g. bearer_env, api_key, oauth2")
    token_env_var: Optional[str] = None
    api_key_env_var: Optional[str] = None


class ToolConfig(BaseModel):
    """Pydantic model for a registered tool definition.

    Maps to YAML files in config/tools/.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    owner_team: str = Field(default="")
    type: str = Field(default="rest", description="Tool type: rest, openapi, function")
    method: str = Field(default="GET")
    endpoint: str = Field(default="")
    auth: Optional[AuthConfig] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    idempotent: bool = False
    approval_required: bool = False
    side_effect_level: SideEffectLevel = SideEffectLevel.READ
    allowed_environments: list[Environment] = Field(
        default_factory=lambda: [Environment.DEV, Environment.TEST]
    )
    request_schema_ref: Optional[str] = None
    response_schema_ref: Optional[str] = None
    description: str = ""
