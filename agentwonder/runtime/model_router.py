"""Model router — resolves model name strings to provider configuration.

In v1 this is a simple static mapping. Production would read from
a model registry with quota, cost, and capability metadata.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelInfo:
    """Resolved model configuration."""

    provider: str
    model_id: str
    endpoint: str


# Default model catalogue for v1.
_DEFAULT_MODELS: dict[str, ModelInfo] = {
    "gemini-2.5-flash": ModelInfo(
        provider="google",
        model_id="gemini-2.5-flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta",
    ),
    "gemini-2.5-pro": ModelInfo(
        provider="google",
        model_id="gemini-2.5-pro",
        endpoint="https://generativelanguage.googleapis.com/v1beta",
    ),
    "gemini-2.0-flash": ModelInfo(
        provider="google",
        model_id="gemini-2.0-flash",
        endpoint="https://generativelanguage.googleapis.com/v1beta",
    ),
    "claude-sonnet-4-20250514": ModelInfo(
        provider="anthropic",
        model_id="claude-sonnet-4-20250514",
        endpoint="https://api.anthropic.com/v1",
    ),
    "claude-haiku-4-20250414": ModelInfo(
        provider="anthropic",
        model_id="claude-haiku-4-20250414",
        endpoint="https://api.anthropic.com/v1",
    ),
}


class ModelNotFoundError(Exception):
    """Raised when a model name cannot be resolved."""


@dataclass
class ModelRouter:
    """Resolves model name strings to ModelInfo configurations.

    Initialised with a default catalogue that can be extended via
    :meth:`register`.
    """

    _models: dict[str, ModelInfo] = field(default_factory=lambda: dict(_DEFAULT_MODELS))

    def resolve(self, model_name: str) -> ModelInfo:
        """Resolve a model name to its provider configuration.

        Args:
            model_name: Canonical model name (e.g. ``gemini-2.5-flash``).

        Returns:
            A :class:`ModelInfo` with provider, model_id, and endpoint.

        Raises:
            ModelNotFoundError: If the name is not in the catalogue.
        """
        info = self._models.get(model_name)
        if info is None:
            raise ModelNotFoundError(
                f"Unknown model '{model_name}'. "
                f"Available: {sorted(self._models.keys())}"
            )
        logger.debug("Resolved model '%s' -> %s", model_name, info)
        return info

    def register(self, model_name: str, info: ModelInfo) -> None:
        """Add or overwrite a model entry in the catalogue.

        Args:
            model_name: The canonical name to register.
            info: The model configuration.
        """
        self._models[model_name] = info
        logger.info("Registered model '%s'", model_name)

    def list_models(self) -> list[str]:
        """Return sorted list of available model names."""
        return sorted(self._models.keys())
