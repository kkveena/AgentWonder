"""EvalRunner — lightweight evaluation scaffold for v1.

Runs named evaluation suites against the trace events of a completed run
and returns a structured result.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from agentwonder.schemas.run import TraceEvent

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Result model
# ------------------------------------------------------------------


class EvalResult(BaseModel):
    """Outcome of an evaluation suite execution."""

    suite_name: str
    passed: bool
    score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Normalised score where 1.0 is perfect.",
    )
    details: dict[str, Any] = Field(default_factory=dict)


# ------------------------------------------------------------------
# Built-in checks (extensible in future versions)
# ------------------------------------------------------------------


def _check_no_errors(events: list[TraceEvent]) -> tuple[bool, dict[str, Any]]:
    """Return True if no error events exist in the trace."""
    errors = [e for e in events if "error" in e.event_type]
    return len(errors) == 0, {"error_count": len(errors)}


def _check_all_steps_completed(events: list[TraceEvent]) -> tuple[bool, dict[str, Any]]:
    """Return True if every started step has a corresponding end event."""
    started = {e.step_id for e in events if e.event_type == "step_start" and e.step_id}
    ended = {e.step_id for e in events if e.event_type == "step_end" and e.step_id}
    missing = started - ended
    return len(missing) == 0, {"incomplete_steps": sorted(missing)}


_BUILTIN_SUITES: dict[str, list] = {
    "basic_health": [_check_no_errors, _check_all_steps_completed],
}


# ------------------------------------------------------------------
# Runner
# ------------------------------------------------------------------


class EvalRunner:
    """Runs evaluation suites against trace events from a workflow run.

    For v1 only a ``basic_health`` suite is provided.  Teams can register
    additional suites via :meth:`register_suite`.
    """

    def __init__(self) -> None:
        self._suites: dict[str, list] = dict(_BUILTIN_SUITES)

    def register_suite(
        self,
        name: str,
        checks: list,
    ) -> None:
        """Register a custom evaluation suite.

        Parameters
        ----------
        name:
            Unique suite identifier.
        checks:
            List of callables ``(list[TraceEvent]) -> (bool, dict)``.
        """
        self._suites[name] = list(checks)

    def run_eval(
        self,
        run_id: str,
        suite_name: str,
        trace_events: list[TraceEvent],
    ) -> EvalResult:
        """Execute an evaluation suite and return the result.

        Parameters
        ----------
        run_id:
            The run being evaluated (included for logging).
        suite_name:
            Name of a registered suite.
        trace_events:
            Trace events to evaluate.

        Raises
        ------
        ValueError
            If *suite_name* is not registered.
        """
        checks = self._suites.get(suite_name)
        if checks is None:
            available = ", ".join(sorted(self._suites)) or "(none)"
            raise ValueError(
                f"Unknown eval suite '{suite_name}'. Available: {available}"
            )

        details: dict[str, Any] = {}
        all_passed = True
        passed_count = 0

        for check_fn in checks:
            name = check_fn.__name__
            try:
                passed, info = check_fn(trace_events)
            except Exception as exc:
                passed = False
                info = {"exception": str(exc)}

            details[name] = {"passed": passed, **info}
            if passed:
                passed_count += 1
            else:
                all_passed = False

        score = passed_count / len(checks) if checks else 1.0

        logger.info(
            "Eval suite '%s' for run %s: passed=%s score=%.2f",
            suite_name,
            run_id,
            all_passed,
            score,
        )

        return EvalResult(
            suite_name=suite_name,
            passed=all_passed,
            score=score,
            details=details,
        )
