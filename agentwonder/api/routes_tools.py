"""Tool registry routes — list and retrieve registered tools."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from agentwonder.schemas.tool import ToolConfig
from agentwonder.registry.tools import ToolRegistryError

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolConfig])
async def list_tools(request: Request) -> list[ToolConfig]:
    """Return all registered tools."""
    registry = request.app.state.tool_registry
    return registry.list_all()


@router.get("/{tool_id}", response_model=ToolConfig)
async def get_tool(tool_id: str, request: Request) -> ToolConfig:
    """Return a single tool by ID."""
    registry = request.app.state.tool_registry
    try:
        return registry.get(tool_id)
    except ToolRegistryError:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_id}' not found",
        )
