"""In-memory state store for step outputs during a run.

Keyed by (run_id, step_id), this store holds the output of each
completed step so downstream steps can reference earlier results.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class InMemoryStateStore:
    """Dict-backed store for per-run step outputs."""

    def __init__(self) -> None:
        # Outer key: run_id, inner key: step_id
        self._state: dict[str, dict[str, Any]] = {}

    def set(self, run_id: str, step_id: str, value: Any) -> None:
        """Store the output of a step.

        Args:
            run_id: Unique identifier for the run.
            step_id: Identifier of the step that produced the output.
            value: The step's output value.
        """
        if run_id not in self._state:
            self._state[run_id] = {}
        self._state[run_id][step_id] = value
        logger.debug("Stored state for run_id='%s', step_id='%s'", run_id, step_id)

    def get(self, run_id: str, step_id: str) -> Any:
        """Retrieve the output of a specific step.

        Args:
            run_id: Unique identifier for the run.
            step_id: Identifier of the step.

        Returns:
            The stored value, or None if not found.
        """
        return self._state.get(run_id, {}).get(step_id)

    def get_all(self, run_id: str) -> dict[str, Any]:
        """Retrieve all step outputs for a run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            Dict mapping step_id to output value. Empty dict if no
            state exists for the run.
        """
        return dict(self._state.get(run_id, {}))
