"""PromptRegistry — loads, validates, and stores prompt definitions."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from agentwonder.compiler.loader import load_all_yaml
from agentwonder.schemas.prompt import PromptConfig

logger = logging.getLogger(__name__)


class PromptRegistryError(Exception):
    """Raised for prompt registration or lookup failures."""


class PromptRegistry:
    """In-memory registry of validated PromptConfig instances.

    Typical usage::

        registry = PromptRegistry()
        registry.load_from_directory(Path("config/prompts"))
        prompt = registry.get("system_greeting")
    """

    def __init__(self) -> None:
        self._store: dict[str, PromptConfig] = {}

    # ------------------------------------------------------------------
    # Bulk loading
    # ------------------------------------------------------------------

    def load_from_directory(self, directory: Path) -> None:
        """Load all YAML files from *directory* and register each as a prompt.

        Files that fail Pydantic validation are logged and skipped.
        Duplicate IDs raise :class:`PromptRegistryError`.

        Args:
            directory: Path to a directory containing prompt YAML files.
        """
        raw_dicts = load_all_yaml(Path(directory))
        for raw in raw_dicts:
            try:
                config = PromptConfig(**raw)
            except ValidationError as exc:
                logger.warning("Skipping invalid prompt YAML entry: %s", exc)
                continue
            self.register(config)

    # ------------------------------------------------------------------
    # Single-item operations
    # ------------------------------------------------------------------

    def register(self, config: PromptConfig) -> None:
        """Register a validated prompt config.

        Args:
            config: A validated :class:`PromptConfig` instance.

        Raises:
            PromptRegistryError: If a prompt with the same ID is already
                registered.
        """
        if config.id in self._store:
            raise PromptRegistryError(
                f"Duplicate prompt id: '{config.id}' is already registered"
            )
        self._store[config.id] = config
        logger.info("Registered prompt '%s' v%s", config.id, config.version)

    def get(self, prompt_id: str) -> PromptConfig:
        """Return the prompt config for *prompt_id*.

        Raises:
            PromptRegistryError: If the ID is not found.
        """
        try:
            return self._store[prompt_id]
        except KeyError:
            raise PromptRegistryError(
                f"Prompt not found: '{prompt_id}'"
            ) from None

    def list_all(self) -> list[PromptConfig]:
        """Return all registered prompts, sorted by ID."""
        return sorted(self._store.values(), key=lambda c: c.id)
