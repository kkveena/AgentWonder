"""PromptConfig schema — validates prompt YAML."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """Pydantic model for a versioned prompt definition.

    Maps to YAML files in config/prompts/.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    purpose: str = ""
    text: str = Field(..., min_length=1)
