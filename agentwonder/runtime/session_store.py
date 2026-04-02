"""In-memory session store for v1.

Stores per-run session data (metadata, context, intermediate state)
keyed by run_id. Production replacements would back this with Redis
or a database.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class SessionNotFoundError(Exception):
    """Raised when a session lookup fails."""


class InMemorySessionStore:
    """Simple dict-backed session store for workflow runs."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, run_id: str) -> dict[str, Any]:
        """Create a new session for a run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            The newly created session dict.

        Raises:
            ValueError: If a session already exists for this run_id.
        """
        if run_id in self._sessions:
            raise ValueError(f"Session already exists for run_id='{run_id}'")

        session: dict[str, Any] = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": {},
        }
        self._sessions[run_id] = session
        logger.debug("Created session for run_id='%s'", run_id)
        return session

    def get_session(self, run_id: str) -> dict[str, Any]:
        """Retrieve the session for a run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            The session dict.

        Raises:
            SessionNotFoundError: If no session exists for the run_id.
        """
        if run_id not in self._sessions:
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        return self._sessions[run_id]

    def update_session(self, run_id: str, data: dict[str, Any]) -> None:
        """Merge additional data into an existing session.

        Args:
            run_id: Unique identifier for the run.
            data: Key-value pairs to merge into the session's data dict.

        Raises:
            SessionNotFoundError: If no session exists for the run_id.
        """
        if run_id not in self._sessions:
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        self._sessions[run_id]["data"].update(data)
        logger.debug("Updated session for run_id='%s'", run_id)

    def delete_session(self, run_id: str) -> None:
        """Remove a session.

        Args:
            run_id: Unique identifier for the run.

        Raises:
            SessionNotFoundError: If no session exists for the run_id.
        """
        if run_id not in self._sessions:
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        del self._sessions[run_id]
        logger.debug("Deleted session for run_id='%s'", run_id)
