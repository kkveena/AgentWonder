"""AuthProvider — resolves auth configuration to concrete HTTP headers.

For v1 this supports:
- ``bearer_env``: reads a bearer token from an environment variable.
- ``api_key``: reads an API key from an environment variable and sends it
  as an ``X-API-Key`` header.

Other auth types (OAuth2, mTLS, etc.) are left as future extensions.
"""

from __future__ import annotations

import logging
import os

from agentwonder.schemas.tool import AuthConfig

logger = logging.getLogger(__name__)


class AuthProvider:
    """Resolves an :class:`AuthConfig` into a ``dict[str, str]`` of HTTP headers."""

    def resolve(self, auth_config: AuthConfig) -> dict[str, str]:
        """Return authorisation headers for the given config.

        Raises
        ------
        ValueError
            If the auth type is unsupported or a required env var is missing.
        """
        auth_type = auth_config.type.lower().strip()

        if auth_type == "bearer_env":
            return self._resolve_bearer(auth_config)
        if auth_type in ("api_key", "api_key_env"):
            return self._resolve_api_key(auth_config)
        if auth_type == "none":
            return {}

        raise ValueError(f"Unsupported auth type: {auth_config.type!r}")

    # ------------------------------------------------------------------
    # Private resolvers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_bearer(auth_config: AuthConfig) -> dict[str, str]:
        env_var = auth_config.token_env_var
        if not env_var:
            raise ValueError(
                "bearer_env auth requires 'token_env_var' to be set in AuthConfig"
            )

        token = os.environ.get(env_var)
        if not token:
            raise ValueError(
                f"Environment variable '{env_var}' is not set or empty"
            )

        return {"Authorization": f"Bearer {token}"}

    @staticmethod
    def _resolve_api_key(auth_config: AuthConfig) -> dict[str, str]:
        env_var = auth_config.api_key_env_var
        if not env_var:
            raise ValueError(
                "api_key auth requires 'api_key_env_var' to be set in AuthConfig"
            )

        key = os.environ.get(env_var)
        if not key:
            raise ValueError(
                f"Environment variable '{env_var}' is not set or empty"
            )

        return {"X-API-Key": key}
