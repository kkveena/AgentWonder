"""Session store — pluggable persistence for per-run session data.

Provides a ``SessionStore`` protocol, an in-memory implementation
(for tests and fast iteration), and a file-backed implementation
(for local development with persistence across restarts).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from agentwonder.logging import get_logger

logger = get_logger(__name__)


class SessionNotFoundError(Exception):
    """Raised when a session lookup fails."""


@runtime_checkable
class SessionStore(Protocol):
    """Protocol for session persistence backends."""

    def create_session(self, run_id: str) -> dict[str, Any]: ...
    def get_session(self, run_id: str) -> dict[str, Any]: ...
    def update_session(self, run_id: str, data: dict[str, Any]) -> None: ...
    def delete_session(self, run_id: str) -> None: ...


class InMemorySessionStore:
    """Dict-backed session store. Fast, no persistence across restarts."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def create_session(self, run_id: str) -> dict[str, Any]:
        if run_id in self._sessions:
            raise ValueError(f"Session already exists for run_id='{run_id}'")
        session: dict[str, Any] = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": {},
        }
        self._sessions[run_id] = session
        logger.debug("session created", run_id=run_id)
        return session

    def get_session(self, run_id: str) -> dict[str, Any]:
        if run_id not in self._sessions:
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        return self._sessions[run_id]

    def update_session(self, run_id: str, data: dict[str, Any]) -> None:
        if run_id not in self._sessions:
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        self._sessions[run_id]["data"].update(data)
        logger.debug("session updated", run_id=run_id)

    def delete_session(self, run_id: str) -> None:
        if run_id not in self._sessions:
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        del self._sessions[run_id]
        logger.debug("session deleted", run_id=run_id)


class FileSessionStore:
    """File-backed session store. Persists sessions as JSON files.

    Each session is stored as ``{data_dir}/sessions/{run_id}.json``.
    Suitable for local development.
    """

    def __init__(self, data_dir: str | Path = "data") -> None:
        self._dir = Path(data_dir) / "sessions"
        self._dir.mkdir(parents=True, exist_ok=True)
        logger.info("file session store initialized", path=str(self._dir))

    def _path(self, run_id: str) -> Path:
        return self._dir / f"{run_id}.json"

    def create_session(self, run_id: str) -> dict[str, Any]:
        p = self._path(run_id)
        if p.exists():
            raise ValueError(f"Session already exists for run_id='{run_id}'")
        session: dict[str, Any] = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "data": {},
        }
        p.write_text(json.dumps(session, default=str), encoding="utf-8")
        logger.debug("session created (file)", run_id=run_id)
        return session

    def get_session(self, run_id: str) -> dict[str, Any]:
        p = self._path(run_id)
        if not p.exists():
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        return json.loads(p.read_text(encoding="utf-8"))

    def update_session(self, run_id: str, data: dict[str, Any]) -> None:
        p = self._path(run_id)
        if not p.exists():
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        session = json.loads(p.read_text(encoding="utf-8"))
        session["data"].update(data)
        p.write_text(json.dumps(session, default=str), encoding="utf-8")
        logger.debug("session updated (file)", run_id=run_id)

    def delete_session(self, run_id: str) -> None:
        p = self._path(run_id)
        if not p.exists():
            raise SessionNotFoundError(f"No session for run_id='{run_id}'")
        p.unlink()
        logger.debug("session deleted (file)", run_id=run_id)
