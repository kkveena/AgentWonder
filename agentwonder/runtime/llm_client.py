"""Gemini LLM client for AgentWonder.

Provides a thin wrapper around the Google GenAI SDK for making
LLM calls. Loads the API key from environment variables (supports
.env files via python-dotenv).

Usage::

    from agentwonder.runtime.llm_client import GeminiClient

    client = GeminiClient()
    response = await client.generate("Summarize this text: ...")
"""

from __future__ import annotations

import os
from typing import Any

from agentwonder.logging import get_logger

logger = get_logger(__name__)

# Lazy-loaded to avoid import errors when google-genai is not installed
_genai = None


def _get_genai():
    """Lazy import of google.genai."""
    global _genai
    if _genai is None:
        try:
            from google import genai
            _genai = genai
        except ImportError:
            raise ImportError(
                "google-genai is required for LLM execution. "
                "Install it with: pip install google-genai"
            )
    return _genai


def load_env() -> None:
    """Load environment variables from .env file if present."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # python-dotenv is optional


class GeminiClient:
    """Async-compatible client for Google Gemini API.

    Reads ``GOOGLE_API_KEY`` from environment variables.
    Supports .env files when python-dotenv is installed.
    """

    def __init__(self, model: str = "gemini-2.0-flash") -> None:
        load_env()
        self._api_key = os.environ.get("GOOGLE_API_KEY", "")
        self._model = model
        self._client = None

        if self._api_key:
            genai = _get_genai()
            self._client = genai.Client(api_key=self._api_key)
            logger.info("gemini client initialized", model=model)
        else:
            logger.warning("GOOGLE_API_KEY not set — LLM calls will use stub responses")

    @property
    def is_configured(self) -> bool:
        """True if an API key is set and the client is ready."""
        return self._client is not None

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> str:
        """Generate text using Gemini.

        Falls back to a stub response if no API key is configured.
        """
        target_model = model or self._model

        if not self.is_configured:
            logger.debug("stub llm response", model=target_model)
            return f"[Stub LLM response — set GOOGLE_API_KEY for real output]"

        logger.info("generating llm response", model=target_model, prompt_len=len(prompt))

        try:
            response = self._client.models.generate_content(
                model=target_model,
                contents=prompt,
                config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            text = response.text or ""
            logger.info("llm response received", model=target_model, response_len=len(text))
            return text
        except Exception as exc:
            logger.error("llm call failed", model=target_model, error=str(exc))
            raise
