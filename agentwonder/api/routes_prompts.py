"""Prompt registry routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agentwonder.schemas.prompt import PromptConfig

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptConfig])
async def list_prompts(request: Request) -> list[PromptConfig]:
    """List all registered prompts."""
    return request.app.state.prompt_registry.list_all()


@router.get("/{prompt_id}", response_model=PromptConfig)
async def get_prompt(prompt_id: str, request: Request) -> PromptConfig:
    """Get a single prompt by ID."""
    try:
        return request.app.state.prompt_registry.get(prompt_id)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
