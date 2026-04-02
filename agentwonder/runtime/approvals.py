"""Approval manager for workflow approval gates.

Manages the lifecycle of approval requests: registration, lookup,
and decision submission. In v1 this is backed by in-memory storage;
production would persist to a database and integrate with external
approval systems.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from agentwonder.schemas.common import ApprovalOutcome
from agentwonder.schemas.run import ApprovalRequest

logger = logging.getLogger(__name__)


class ApprovalNotFoundError(Exception):
    """Raised when an approval lookup fails."""


class ApprovalManager:
    """In-memory approval gate manager."""

    def __init__(self) -> None:
        # approval_id -> ApprovalRequest
        self._approvals: dict[str, ApprovalRequest] = {}
        # run_id -> list of approval_ids
        self._by_run: dict[str, list[str]] = {}

    def register_approval(self, request: ApprovalRequest) -> ApprovalRequest:
        """Register a new approval request.

        Args:
            request: The approval request to register.

        Returns:
            The registered ApprovalRequest (with generated ID if needed).
        """
        self._approvals[request.approval_id] = request
        self._by_run.setdefault(request.run_id, []).append(request.approval_id)
        logger.info(
            "Registered approval '%s' for run='%s', step='%s'",
            request.approval_id,
            request.run_id,
            request.step_id,
        )
        return request

    def get_pending(self, run_id: str) -> list[ApprovalRequest]:
        """Get all pending (undecided) approval requests for a run.

        Args:
            run_id: Unique identifier for the run.

        Returns:
            List of ApprovalRequest objects that have no outcome yet.
        """
        approval_ids = self._by_run.get(run_id, [])
        return [
            self._approvals[aid]
            for aid in approval_ids
            if self._approvals[aid].outcome is None
        ]

    def submit_decision(
        self,
        approval_id: str,
        outcome: ApprovalOutcome,
        decided_by: str,
    ) -> ApprovalRequest:
        """Submit a decision for an approval request.

        Args:
            approval_id: The ID of the approval to decide.
            outcome: The decision (approved, rejected, timed_out).
            decided_by: Identifier of the person or system that decided.

        Returns:
            The updated ApprovalRequest.

        Raises:
            ApprovalNotFoundError: If the approval_id is not found.
            ValueError: If the approval has already been decided.
        """
        if approval_id not in self._approvals:
            raise ApprovalNotFoundError(
                f"No approval found with id='{approval_id}'"
            )

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
            approval_id,
            outcome.value,
            decided_by,
        )
        return approval
