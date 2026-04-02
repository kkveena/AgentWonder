"""Health-check routes."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return basic health status and API version."""
    return {"status": "ok", "version": "1.0.0"}
