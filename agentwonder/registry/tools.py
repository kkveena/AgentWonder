"""ToolRegistry — loads, validates, and stores tool definitions."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from agentwonder.compiler.loader import load_all_yaml
from agentwonder.schemas.tool import ToolConfig

logger = logging.getLogger(__name__)


class ToolRegistryError(Exception):
    """Raised for tool registration or lookup failures."""


class ToolRegistry:
    """In-memory registry of validated ToolConfig instances.

    Typical usage::

        registry = ToolRegistry()
        registry.load_from_directory(Path("config/tools"))
        tool = registry.get("search_api")
    """

    def __init__(self) -> None:
        self._store: dict[str, ToolConfig] = {}

    # ------------------------------------------------------------------
    # Bulk loading
    # ------------------------------------------------------------------

    def load_from_directory(self, directory: Path) -> None:
        """Load all YAML files from *directory* and register each as a tool.

        Files that fail Pydantic validation are logged and skipped.
        Duplicate IDs raise :class:`ToolRegistryError`.

        Args:
            directory: Path to a directory containing tool YAML files.
        """
        raw_dicts = load_all_yaml(Path(directory))
        for raw in raw_dicts:
            try:
                config = ToolConfig(**raw)
            except ValidationError as exc:
                logger.warning("Skipping invalid tool YAML entry: %s", exc)
                continue
            self.register(config)

    # ------------------------------------------------------------------
    # Single-item operations
    # ------------------------------------------------------------------

    def register(self, config: ToolConfig) -> None:
        """Register a validated tool config.

        Args:
            config: A validated :class:`ToolConfig` instance.

        Raises:
            ToolRegistryError: If a tool with the same ID is already
                registered.
        """
        if config.id in self._store:
            raise ToolRegistryError(
                f"Duplicate tool id: '{config.id}' is already registered"
            )
        self._store[config.id] = config
        logger.info("Registered tool '%s' v%s", config.id, config.version)

    def get(self, tool_id: str) -> ToolConfig:
        """Return the tool config for *tool_id*.

        Raises:
            ToolRegistryError: If the ID is not found.
        """
        try:
            return self._store[tool_id]
        except KeyError:
            raise ToolRegistryError(
                f"Tool not found: '{tool_id}'"
            ) from None

    def list_all(self) -> list[ToolConfig]:
        """Return all registered tools, sorted by ID."""
        return sorted(self._store.values(), key=lambda c: c.id)
