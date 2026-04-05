"""LLM-backed tools for AgentWonder.

These tools use the Gemini client to perform text operations.
They are registered via YAML configs with type=llm and invoked
by the executor when a tool_call step references them.
"""

from __future__ import annotations

from typing import Any

from agentwonder.logging import get_logger
from agentwonder.runtime.llm_client import GeminiClient

logger = get_logger(__name__)


class LLMSummarizer:
    """Summarizes input text using Gemini.

    Registered in config/tools/ with type=llm.
    """

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()

    async def call(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Summarize the provided text.

        Args:
            inputs: Must contain a "text" key with the content to summarize.
                Optional "max_length" key (default: "3 sentences").

        Returns:
            Dict with "summary" and metadata.
        """
        text = inputs.get("text", "")
        max_length = inputs.get("max_length", "3 sentences")

        if not text:
            return {"status": "error", "error": "No 'text' provided in inputs"}

        prompt = (
            f"Summarize the following text in {max_length}. "
            "Be concise and capture the key points.\n\n"
            f"Text:\n{text}"
        )

        logger.info("llm_summarizer invoked", text_len=len(text))

        if not self._client.is_configured:
            return {
                "status": "success",
                "summary": f"[Stub summary of {len(text)} chars]",
                "model": "stub",
            }

        summary = await self._client.generate(prompt, temperature=0.3, max_tokens=512)
        return {
            "status": "success",
            "summary": summary,
            "model": self._client._model,
            "input_length": len(text),
        }


class LLMClassifier:
    """Classifies input text into categories using Gemini.

    Registered in config/tools/ with type=llm.
    """

    def __init__(self, client: GeminiClient | None = None) -> None:
        self._client = client or GeminiClient()

    async def call(self, inputs: dict[str, Any]) -> dict[str, Any]:
        """Classify the provided text into one of the given categories.

        Args:
            inputs: Must contain "text" and "categories" (list of strings).
                Optional "context" for additional guidance.

        Returns:
            Dict with "category", "confidence", and "reasoning".
        """
        text = inputs.get("text", "")
        categories = inputs.get("categories", [])

        if not text:
            return {"status": "error", "error": "No 'text' provided in inputs"}
        if not categories:
            return {"status": "error", "error": "No 'categories' provided in inputs"}

        context = inputs.get("context", "")
        categories_str = ", ".join(categories)

        prompt = (
            f"Classify the following text into exactly one of these categories: {categories_str}\n"
        )
        if context:
            prompt += f"\nAdditional context: {context}\n"
        prompt += (
            f"\nText:\n{text}\n\n"
            "Respond with a JSON object containing:\n"
            '- "category": the selected category (must be one of the listed categories)\n'
            '- "confidence": a float between 0.0 and 1.0\n'
            '- "reasoning": a brief explanation of your choice'
        )

        logger.info("llm_classifier invoked", text_len=len(text), num_categories=len(categories))

        if not self._client.is_configured:
            default_cat = categories[0] if categories else "unknown"
            return {
                "status": "success",
                "category": default_cat,
                "confidence": 0.5,
                "reasoning": f"[Stub classification — selected '{default_cat}']",
                "model": "stub",
            }

        import json
        raw = await self._client.generate(prompt, temperature=0.2, max_tokens=256)

        # Parse response
        try:
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(raw[start:end])
                category = parsed.get("category", categories[0])
                confidence = float(parsed.get("confidence", 0.8))
                reasoning = parsed.get("reasoning", "")
            else:
                category = categories[0]
                confidence = 0.7
                reasoning = raw
        except (json.JSONDecodeError, ValueError):
            category = categories[0]
            confidence = 0.7
            reasoning = raw

        # Validate category
        if category not in categories:
            category = categories[0]

        return {
            "status": "success",
            "category": category,
            "confidence": confidence,
            "reasoning": reasoning,
            "model": self._client._model,
        }
