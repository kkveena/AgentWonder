"""State store — pluggable persistence for per-run step outputs.

Provides a ``StateStore`` protocol, an in-memory implementation
(for tests), and a file-backed implementation (for local dev).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from agentwonder.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class StateStore(Protocol):
    """Protocol for step-output persistence backends."""

    def set(self, run_id: str, step_id: str, value: Any) -> None: ...
    def get(self, run_id: str, step_id: str) -> Any: ...
    def get_all(self, run_id: str) -> dict[str, Any]: ...


class InMemoryStateStore:
    """Dict-backed store for per-run step outputs."""

    def __init__(self) -> None:
        self._state: dict[str, dict[str, Any]] = {}

    def set(self, run_id: str, step_id: str, value: Any) -> None:
        if run_id not in self._state:
            self._state[run_id] = {}
        self._state[run_id][step_id] = value
        logger.debug("state stored", run_id=run_id, step_id=step_id)

    def get(self, run_id: str, step_id: str) -> Any:
        return self._state.get(run_id, {}).get(step_id)

    def get_all(self, run_id: str) -> dict[str, Any]:
        return dict(self._state.get(run_id, {}))


class FileStateStore:
    """File-backed state store. Persists step outputs as JSON.

    Each run's state is stored as ``{data_dir}/state/{run_id}.json``.
    """

    def __init__(self, data_dir: str | Path = "data") -> None:
        self._dir = Path(data_dir) / "state"
        self._dir.mkdir(parents=True, exist_ok=True)
        logger.info("file state store initialized", path=str(self._dir))

    def _path(self, run_id: str) -> Path:
        return self._dir / f"{run_id}.json"

    def _load(self, run_id: str) -> dict[str, Any]:
        p = self._path(run_id)
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def _save(self, run_id: str, data: dict[str, Any]) -> None:
        p = self._path(run_id)
        p.write_text(json.dumps(data, default=str), encoding="utf-8")

    def set(self, run_id: str, step_id: str, value: Any) -> None:
        state = self._load(run_id)
        state[step_id] = value
        self._save(run_id, state)
        logger.debug("state stored (file)", run_id=run_id, step_id=step_id)

    def get(self, run_id: str, step_id: str) -> Any:
        return self._load(run_id).get(step_id)

    def get_all(self, run_id: str) -> dict[str, Any]:
        return self._load(run_id)
