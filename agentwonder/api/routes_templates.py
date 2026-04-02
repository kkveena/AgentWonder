"""Template registry routes — list and retrieve workflow templates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agentwonder.schemas.template import TemplateConfig
from agentwonder.registry.templates import TemplateRegistryError

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateConfig])
async def list_templates(request: Request) -> list[TemplateConfig]:
    """Return all registered workflow templates."""
    registry = request.app.state.template_registry
    return registry.list_all()


@router.get("/{template_id}", response_model=TemplateConfig)
async def get_template(template_id: str, request: Request) -> TemplateConfig:
    """Return a single template by ID."""
    registry = request.app.state.template_registry
    try:
        return registry.get(template_id)
    except TemplateRegistryError:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_id}' not found",
        )
