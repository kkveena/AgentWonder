"""Policy registry routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agentwonder.schemas.policy import PolicyConfig

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=list[PolicyConfig])
async def list_policies(request: Request) -> list[PolicyConfig]:
    """List all registered policies."""
    return request.app.state.policy_registry.list_all()


@router.get("/{policy_id}", response_model=PolicyConfig)
async def get_policy(policy_id: str, request: Request) -> PolicyConfig:
    """Get a single policy by ID."""
    try:
        return request.app.state.policy_registry.get(policy_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
