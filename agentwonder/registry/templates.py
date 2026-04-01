"""TemplateRegistry — loads, validates, and stores workflow templates."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from agentwonder.compiler.loader import load_all_yaml
from agentwonder.schemas.template import TemplateConfig

logger = logging.getLogger(__name__)


class TemplateRegistryError(Exception):
    """Raised for template registration or lookup failures."""


class TemplateRegistry:
    """In-memory registry of validated TemplateConfig instances.

    Typical usage::

        registry = TemplateRegistry()
        registry.load_from_directory(Path("config/templates"))
        tpl = registry.get("router_specialists")
    """

    def __init__(self) -> None:
        self._store: dict[str, TemplateConfig] = {}

    # ------------------------------------------------------------------
    # Bulk loading
    # ------------------------------------------------------------------

    def load_from_directory(self, directory: Path) -> None:
        """Load all YAML files from *directory* and register each as a template.

        Files that fail Pydantic validation are logged and skipped.
        Duplicate IDs raise :class:`TemplateRegistryError`.

        Args:
            directory: Path to a directory containing template YAML files.
        """
        raw_dicts = load_all_yaml(Path(directory))
        for raw in raw_dicts:
            try:
                config = TemplateConfig(**raw)
            except ValidationError as exc:
                logger.warning(
                    "Skipping invalid template YAML entry: %s", exc
                )
                continue
            self.register(config)

    # ------------------------------------------------------------------
    # Single-item operations
    # ------------------------------------------------------------------

    def register(self, config: TemplateConfig) -> None:
        """Register a validated template config.

        Args:
            config: A validated :class:`TemplateConfig` instance.

        Raises:
            TemplateRegistryError: If a template with the same ID is
                already registered.
        """
        if config.id in self._store:
            raise TemplateRegistryError(
                f"Duplicate template id: '{config.id}' is already registered"
            )
        self._store[config.id] = config
        logger.info("Registered template '%s' v%s", config.id, config.version)

    def get(self, template_id: str) -> TemplateConfig:
        """Return the template config for *template_id*.

        Raises:
            TemplateRegistryError: If the ID is not found.
        """
        try:
            return self._store[template_id]
        except KeyError:
            raise TemplateRegistryError(
                f"Template not found: '{template_id}'"
            ) from None

    def list_all(self) -> list[TemplateConfig]:
        """Return all registered templates, sorted by ID."""
        return sorted(self._store.values(), key=lambda c: c.id)
