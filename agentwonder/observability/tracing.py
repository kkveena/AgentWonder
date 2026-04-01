"""TraceCollector — in-memory storage and retrieval of TraceEvent objects."""

from __future__ import annotations

import logging
import threading
from collections import defaultdict

from agentwonder.schemas.run import TraceEvent

logger = logging.getLogger(__name__)


class TraceCollector:
    """Collects :class:`TraceEvent` instances emitted during workflow runs.

    For v1 all events are stored in-memory, keyed by ``run_id``.  The
    implementation is thread-safe so it can be shared across async tasks
    running on the same event loop.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events_by_run: dict[str, list[TraceEvent]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def emit(self, event: TraceEvent) -> None:
        """Record a trace event.

        Parameters
        ----------
        event:
            A validated :class:`TraceEvent` instance.
        """
        with self._lock:
            self._events_by_run[event.run_id].append(event)

        logger.debug(
            "Trace event [%s] run=%s step=%s",
            event.event_type,
            event.run_id,
            event.step_id,
        )

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_events(self, run_id: str) -> list[TraceEvent]:
        """Return all events for a given *run_id*, ordered by emission time.

        Returns an empty list if no events have been recorded for the run.
        """
        with self._lock:
            return list(self._events_by_run.get(run_id, []))

    def get_all(self) -> list[TraceEvent]:
        """Return every recorded event across all runs, ordered by timestamp."""
        with self._lock:
            all_events = [
                evt
                for events in self._events_by_run.values()
                for evt in events
            ]
        all_events.sort(key=lambda e: e.timestamp)
        return all_events

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def clear(self, run_id: str | None = None) -> None:
        """Remove recorded events.

        Parameters
        ----------
        run_id:
            If provided, only events for that run are cleared.
            If ``None``, **all** events are removed.
        """
        with self._lock:
            if run_id is not None:
                self._events_by_run.pop(run_id, None)
            else:
                self._events_by_run.clear()

    @property
    def run_ids(self) -> list[str]:
        """Return a sorted list of run IDs that have recorded events."""
        with self._lock:
            return sorted(self._events_by_run)
