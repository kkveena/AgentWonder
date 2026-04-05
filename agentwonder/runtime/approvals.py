"""Approval manager for workflow approval gates.

Manages the lifecycle of approval requests: registration, lookup,
decision submission, and timeout enforcement. In v1 this is backed by
in-memory storage; production would persist to a database and integrate
with external approval systems.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from agentwonder.schemas.common import ApprovalOutcome
from agentwonder.schemas.run import ApprovalRequest

logger = logging.getLogger(__name__)


class ApprovalNotFoundError(Exception):
    """Raised when an approval lookup fails."""


class ApprovalManager:
    """In-memory approval gate manager with timeout support."""

    def __init__(self) -> None:
        self._approvals: dict[str, ApprovalRequest] = {}
        self._by_run: dict[str, list[str]] = {}

    def register_approval(self, request: ApprovalRequest) -> ApprovalRequest:
        """Register a new approval request."""
        self._approvals[request.approval_id] = request
        self._by_run.setdefault(request.run_id, []).append(request.approval_id)
        logger.info(
            "Registered approval '%s' for run='%s', step='%s'",
            request.approval_id, request.run_id, request.step_id,
        )
        return request

    def get_pending(self, run_id: str) -> list[ApprovalRequest]:
        """Get all pending (undecided) approval requests for a run."""
        approval_ids = self._by_run.get(run_id, [])
        return [
            self._approvals[aid]
            for aid in approval_ids
            if self._approvals[aid].outcome is None
        ]

    def get_all_for_run(self, run_id: str) -> list[ApprovalRequest]:
        """Get all approval requests for a run (pending and decided)."""
        approval_ids = self._by_run.get(run_id, [])
        return [self._approvals[aid] for aid in approval_ids]

    def get_approval(self, approval_id: str) -> ApprovalRequest:
        """Get a single approval request by ID."""
        if approval_id not in self._approvals:
            raise ApprovalNotFoundError(f"No approval found with id='{approval_id}'")
        return self._approvals[approval_id]

    def submit_decision(
        self,
        approval_id: str,
        outcome: ApprovalOutcome,
        decided_by: str,
    ) -> ApprovalRequest:
        """Submit a decision for an approval request."""
        if approval_id not in self._approvals:
            raise ApprovalNotFoundError(f"No approval found with id='{approval_id}'")

        approval = self._approvals[approval_id]
        if approval.outcome is not None:
            raise ValueError(
                f"Approval '{approval_id}' already decided: {approval.outcome.value}"
            )

        approval.outcome = outcome
        approval.decided_by = decided_by
        approval.decided_at = datetime.now(timezone.utc)

        logger.info(
            "Approval '%s' decided: %s by %s",
            approval_id, outcome.value, decided_by,
        )
        return approval

    def check_timeouts(self, timeout_minutes: int = 60) -> list[ApprovalRequest]:
        """Check for pending approvals that have exceeded their timeout.

        Automatically transitions timed-out approvals to TIMED_OUT.

        Returns:
            List of approvals that were timed out by this call.
        """
        now = datetime.now(timezone.utc)
        timed_out: list[ApprovalRequest] = []

        for approval in self._approvals.values():
            if approval.outcome is not None:
                continue
            deadline = approval.requested_at + timedelta(minutes=timeout_minutes)
            if now >= deadline:
                approval.outcome = ApprovalOutcome.TIMED_OUT
                approval.decided_by = "system_timeout"
                approval.decided_at = now
                timed_out.append(approval)
                logger.warning(
                    "Approval '%s' timed out after %d minutes",
                    approval.approval_id, timeout_minutes,
                )

        return timed_out
