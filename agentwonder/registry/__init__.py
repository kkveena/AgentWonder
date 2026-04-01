"""Registry layer — in-memory registries for templates, tools, prompts, and policies.

Each registry loads YAML from a config directory, validates entries into
Pydantic models, and stores them keyed by ID for fast lookup.
"""

from agentwonder.registry.templates import TemplateRegistry
from agentwonder.registry.tools import ToolRegistry
from agentwonder.registry.prompts import PromptRegistry
from agentwonder.registry.policies import PolicyRegistry

__all__ = [
    "TemplateRegistry",
    "ToolRegistry",
    "PromptRegistry",
    "PolicyRegistry",
]
