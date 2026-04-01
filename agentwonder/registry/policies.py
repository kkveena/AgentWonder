"""PolicyRegistry — loads, validates, and stores governance policies."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError

from agentwonder.compiler.loader import load_all_yaml
from agentwonder.schemas.policy import PolicyConfig

logger = logging.getLogger(__name__)


class PolicyRegistryError(Exception):
    """Raised for policy registration or lookup failures."""


class PolicyRegistry:
    """In-memory registry of validated PolicyConfig instances.

    Typical usage::

        registry = PolicyRegistry()
        registry.load_from_directory(Path("config/policies"))
        policy = registry.get("require_approval_for_writes")
    """

    def __init__(self) -> None:
        self._store: dict[str, PolicyConfig] = {}

    # ------------------------------------------------------------------
    # Bulk loading
    # ------------------------------------------------------------------

    def load_from_directory(self, directory: Path) -> None:
        """Load all YAML files from *directory* and register each as a policy.

        Files that fail Pydantic validation are logged and skipped.
        Duplicate IDs raise :class:`PolicyRegistryError`.

        Args:
            directory: Path to a directory containing policy YAML files.
        """
        raw_dicts = load_all_yaml(Path(directory))
        for raw in raw_dicts:
            try:
                config = PolicyConfig(**raw)
            except ValidationError as exc:
                logger.warning("Skipping invalid policy YAML entry: %s", exc)
                continue
            self.register(config)

    # ------------------------------------------------------------------
    # Single-item operations
    # ------------------------------------------------------------------

    def register(self, config: PolicyConfig) -> None:
        """Register a validated policy config.

        Args:
            config: A validated :class:`PolicyConfig` instance.

        Raises:
            PolicyRegistryError: If a policy with the same ID is already
                registered.
        """
        if config.id in self._store:
            raise PolicyRegistryError(
                f"Duplicate policy id: '{config.id}' is already registered"
            )
        self._store[config.id] = config
        logger.info("Registered policy '%s' v%s", config.id, config.version)

    def get(self, policy_id: str) -> PolicyConfig:
        """Return the policy config for *policy_id*.

        Raises:
            PolicyRegistryError: If the ID is not found.
        """
        try:
            return self._store[policy_id]
        except KeyError:
            raise PolicyRegistryError(
                f"Policy not found: '{policy_id}'"
            ) from None

    def list_all(self) -> list[PolicyConfig]:
        """Return all registered policies, sorted by ID."""
        return sorted(self._store.values(), key=lambda c: c.id)
