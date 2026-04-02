"""Helper factories for common TraceEvent instances.

These functions provide a convenient, consistent API for emitting trace
events without manually constructing :class:`TraceEvent` each time.
"""

from __future__ import annotations

from typing import Any

from agentwonder.schemas.run import TraceEvent


# ------------------------------------------------------------------
# Step-level events
# ------------------------------------------------------------------


def step_started(run_id: str, step_id: str) -> TraceEvent:
    """Create a trace event indicating a workflow step has started."""
    return TraceEvent(
        run_id=run_id,
        step_id=step_id,
        event_type="step_start",
    )


def step_completed(
    run_id: str, step_id: str, result: Any = None
) -> TraceEvent:
    """Create a trace event indicating a workflow step completed successfully."""
    return TraceEvent(
        run_id=run_id,
        step_id=step_id,
        event_type="step_end",
        data={"result": result} if result is not None else {},
    )


def step_failed(run_id: str, step_id: str, error: str) -> TraceEvent:
    """Create a trace event indicating a workflow step failed."""
    return TraceEvent(
        run_id=run_id,
        step_id=step_id,
        event_type="step_error",
        data={"error": error},
    )


# ------------------------------------------------------------------
# Tool-level events
# ------------------------------------------------------------------


def tool_invoked(
    run_id: str,
    step_id: str,
    tool_id: str,
    inputs: dict[str, Any] | None = None,
) -> TraceEvent:
    """Create a trace event recording a tool invocation."""
    return TraceEvent(
        run_id=run_id,
        step_id=step_id,
        event_type="tool_call",
        data={"tool_id": tool_id, "inputs": inputs or {}},
    )


# ------------------------------------------------------------------
# Approval events
# ------------------------------------------------------------------


def approval_requested(
    run_id: str, step_id: str, policy_id: str
) -> TraceEvent:
    """Create a trace event recording an approval gate request."""
    return TraceEvent(
        run_id=run_id,
        step_id=step_id,
        event_type="approval_requested",
        data={"policy_id": policy_id},
    )


# ------------------------------------------------------------------
# Run-level events
# ------------------------------------------------------------------


def run_started(run_id: str) -> TraceEvent:
    """Create a trace event indicating a workflow run has started."""
    return TraceEvent(
        run_id=run_id,
        event_type="run_start",
    )


def run_completed(run_id: str) -> TraceEvent:
    """Create a trace event indicating a workflow run completed successfully."""
    return TraceEvent(
        run_id=run_id,
        event_type="run_end",
    )


def run_failed(run_id: str, error: str) -> TraceEvent:
    """Create a trace event indicating a workflow run failed."""
    return TraceEvent(
        run_id=run_id,
        event_type="run_error",
        data={"error": error},
    )
