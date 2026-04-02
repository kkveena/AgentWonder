"""OpenAPIToolWrapper — scaffold for invoking tools defined via OpenAPI specs.

For v1 this is intentionally thin: it resolves an operation from a cached
spec and delegates actual HTTP execution to :class:`RESTToolWrapper`.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agentwonder.schemas.tool import AuthConfig, ToolConfig
from agentwonder.tools.auth import AuthProvider
from agentwonder.tools.rest_wrapper import RESTToolWrapper

logger = logging.getLogger(__name__)


class OpenAPIToolWrapper:
    """Wraps an OpenAPI spec so individual operations can be called by ID.

    Usage::

        wrapper = OpenAPIToolWrapper(
            spec_url="https://api.example.com/openapi.json",
            auth_config=AuthConfig(type="bearer_env", token_env_var="MY_TOKEN"),
        )
        await wrapper.load_spec()
        result = await wrapper.call("listItems", {"limit": 10})
    """

    def __init__(
        self,
        spec_url: str,
        *,
        auth_config: AuthConfig | None = None,
        auth_provider: AuthProvider | None = None,
        default_timeout: int = 30,
    ) -> None:
        self.spec_url = spec_url
        self._auth_config = auth_config
        self._auth_provider = auth_provider or AuthProvider()
        self._default_timeout = default_timeout
        self._spec: dict[str, Any] | None = None
        self._operations: dict[str, _ResolvedOperation] = {}

    # ------------------------------------------------------------------
    # Spec loading
    # ------------------------------------------------------------------

    async def load_spec(self) -> None:
        """Fetch and index the OpenAPI spec from *spec_url*."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(self.spec_url)
            response.raise_for_status()
            self._spec = response.json()

        self._index_operations()
        logger.info(
            "Indexed %d operations from %s", len(self._operations), self.spec_url
        )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def call(
        self, operation_id: str, inputs: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Invoke an operation by its ``operationId``.

        Parameters
        ----------
        operation_id:
            The ``operationId`` declared in the OpenAPI spec.
        inputs:
            Parameters / body to pass through to the REST call.

        Returns
        -------
        Same response dict as :meth:`RESTToolWrapper.call`.
        """
        if not self._operations:
            raise RuntimeError("Spec not loaded — call load_spec() first")

        op = self._operations.get(operation_id)
        if op is None:
            available = ", ".join(sorted(self._operations)) or "(none)"
            raise ValueError(
                f"Unknown operation_id '{operation_id}'. Available: {available}"
            )

        # Build a minimal ToolConfig for the REST wrapper.
        tool_config = ToolConfig(
            id=f"openapi_{operation_id}",
            name=operation_id,
            version="0.0.1",
            type="openapi",
            method=op.method,
            endpoint=op.url,
            auth=self._auth_config,
            timeout_seconds=self._default_timeout,
        )

        wrapper = RESTToolWrapper(
            tool_config, auth_provider=self._auth_provider
        )
        return await wrapper.call(inputs)

    def list_operations(self) -> list[str]:
        """Return sorted list of available operation IDs."""
        return sorted(self._operations)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _index_operations(self) -> None:
        """Walk the spec's paths and extract operations by operationId."""
        if self._spec is None:
            return

        servers = self._spec.get("servers", [])
        base_url = servers[0]["url"].rstrip("/") if servers else ""

        paths: dict[str, Any] = self._spec.get("paths", {})
        for path, path_item in paths.items():
            for method in ("get", "post", "put", "patch", "delete", "head", "options"):
                operation = path_item.get(method)
                if operation is None:
                    continue
                op_id = operation.get("operationId")
                if op_id is None:
                    continue
                self._operations[op_id] = _ResolvedOperation(
                    method=method.upper(),
                    url=f"{base_url}{path}",
                )


class _ResolvedOperation:
    """Lightweight container for a resolved OpenAPI operation."""

    __slots__ = ("method", "url")

    def __init__(self, method: str, url: str) -> None:
        self.method = method
        self.url = url
