"""Shared enums and base types used across AgentWonder schemas."""

from __future__ import annotations

from enum import Enum


class StepType(str, Enum):
    """Allowed step types within a workflow."""

    TOOL_CALL = "tool_call"
    LLM_AGENT = "llm_agent"
    APPROVAL = "approval"
    EVALUATOR = "evaluator"
    ROUTER = "router"
    PARALLEL = "parallel"
    AGGREGATOR = "aggregator"


class SideEffectLevel(str, Enum):
    """Describes the side-effect level of a tool."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"


class Environment(str, Enum):
    """Deployment environments."""

    DEV = "dev"
    TEST = "test"
    STAGING = "staging"
    PROD = "prod"


class RunState(str, Enum):
    """Lifecycle states of a workflow run."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalOutcome(str, Enum):
    """Result of an approval decision."""

    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
