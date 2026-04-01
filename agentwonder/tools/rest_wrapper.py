"""RESTToolWrapper — turns a ToolConfig into an async HTTP callable."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from agentwonder.schemas.tool import ToolConfig
from agentwonder.tools.auth import AuthProvider

logger = logging.getLogger(__name__)


class RESTToolWrapper:
    """Wraps a :class:`ToolConfig` so it can be invoked as a simple async call.

    The wrapper builds an HTTP request from the tool's declared method,
    endpoint, auth, and timeout settings, then returns a normalised
    response dict.
    """

    def __init__(
        self,
        tool_config: ToolConfig,
        *,
        auth_provider: AuthProvider | None = None,
        base_url_override: str | None = None,
    ) -> None:
        self.config = tool_config
        self._auth_provider = auth_provider or AuthProvider()
        self._base_url_override = base_url_override

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def call(self, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the HTTP request described by the tool config.

        Parameters
        ----------
        inputs:
            Payload to send.  For GET/DELETE requests the dict is sent as
            query parameters; for POST/PUT/PATCH it is sent as JSON body.

        Returns
        -------
        dict with ``status_code``, ``body`` (parsed JSON or raw text),
        and ``headers``.
        """
        inputs = inputs or {}
        url = self._resolve_endpoint()
        method = self.config.method.upper()
        headers = self._resolve_auth_headers()
        timeout = httpx.Timeout(self.config.timeout_seconds)

        attempt = 0
        max_attempts = 1 + self.config.retry_policy.max_retries
        last_exc: Exception | None = None

        while attempt < max_attempts:
            attempt += 1
            try:
                return await self._send(method, url, headers, inputs, timeout)
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                logger.warning(
                    "Tool %s attempt %d/%d failed: %s",
                    self.config.id,
                    attempt,
                    max_attempts,
                    exc,
                )
                if attempt < max_attempts:
                    import asyncio

                    await asyncio.sleep(self.config.retry_policy.backoff_seconds)

        # All retries exhausted — raise the last exception.
        raise RuntimeError(
            f"Tool {self.config.id} failed after {max_attempts} attempt(s)"
        ) from last_exc

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_endpoint(self) -> str:
        if self._base_url_override:
            return f"{self._base_url_override.rstrip('/')}/{self.config.endpoint.lstrip('/')}"
        return self.config.endpoint

    def _resolve_auth_headers(self) -> dict[str, str]:
        if self.config.auth is None:
            return {}
        return self._auth_provider.resolve(self.config.auth)

    @staticmethod
    async def _send(
        method: str,
        url: str,
        headers: dict[str, str],
        inputs: dict[str, Any],
        timeout: httpx.Timeout,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method in ("GET", "DELETE", "HEAD", "OPTIONS"):
                response = await client.request(
                    method, url, headers=headers, params=inputs
                )
            else:
                response = await client.request(
                    method, url, headers=headers, json=inputs
                )

        # Attempt JSON parse; fall back to raw text.
        try:
            body = response.json()
        except Exception:
            body = response.text

        return {
            "status_code": response.status_code,
            "body": body,
            "headers": dict(response.headers),
        }
