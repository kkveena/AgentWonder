"""Workflow executor — drives a RuntimePlan through step-by-step execution.

For v1 the actual ADK integration is stubbed; each step type returns a
placeholder result dict.  The executor handles sequencing, approval
gates, trace event collection, and state management.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from agentwonder.schemas.common import ApprovalOutcome, RunState, StepType
from agentwonder.schemas.run import ApprovalRequest, RunStatus, TraceEvent

from agentwonder.compiler.builder import RuntimePlan, RuntimeStep
from agentwonder.runtime.approvals import ApprovalManager
from agentwonder.runtime.model_router import ModelRouter
from agentwonder.runtime.session_store import InMemorySessionStore
from agentwonder.runtime.state_store import InMemoryStateStore

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Raised when a step execution fails unrecoverably."""


class WorkflowExecutor:
    """Executes a :class:`RuntimePlan` step by step.

    Orchestrates sessions, state, approvals, and trace event collection.
    The actual per-step work (tool calls, LLM inference, evaluation) is
    stubbed for v1 and will be replaced with ADK runtime calls.

    Args:
        session_store: Session storage backend.
        state_store: Step output storage backend.
        approval_manager: Approval gate handler.
        model_router: Model name resolver.
    """

    def __init__(
        self,
        session_store: InMemorySessionStore | None = None,
        state_store: InMemoryStateStore | None = None,
        approval_manager: ApprovalManager | None = None,
        model_router: ModelRouter | None = None,
    ) -> None:
        self.session_store = session_store or InMemorySessionStore()
        self.state_store = state_store or InMemoryStateStore()
        self.approval_manager = approval_manager or ApprovalManager()
        self.model_router = model_router or ModelRouter()

    async def execute(
        self,
        run_request: "RunRequest",
        plan: RuntimePlan,
    ) -> RunStatus:
        """Execute a workflow plan from start to finish.

        Args:
            run_request: The incoming run request with inputs and metadata.
            plan: A fully resolved RuntimePlan from the compiler.

        Returns:
            A RunStatus reflecting the final state of the run.
        """
        # Avoid circular import at module level — only needed for type hint
        from agentwonder.schemas.run import RunRequest  # noqa: F811

        # Initialise run status
        status = RunStatus(
            workflow_id=plan.workflow_id,
            workflow_version=plan.workflow_version,
            template_id=plan.template_id,
            state=RunState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        run_id = status.run_id
        trace_events: list[TraceEvent] = []

        # Create session
        self.session_store.create_session(run_id)
        self.session_store.update_session(run_id, {
            "workflow_id": plan.workflow_id,
            "inputs": run_request.inputs,
            "environment": run_request.environment,
            "requester": run_request.requester,
        })

        self._emit(trace_events, run_id, None, "run_start", {
            "workflow_id": plan.workflow_id,
            "workflow_version": plan.workflow_version,
            "template_id": plan.template_id,
        })

        # Build a step lookup for execution order traversal
        step_map: dict[str, RuntimeStep] = {s.id: s for s in plan.steps}

        try:
            for step_id in plan.execution_order:
                step = step_map[step_id]
                status.current_step = step_id

                self._emit(trace_events, run_id, step_id, "step_start", {
                    "step_type": step.type.value,
                })

                result = await self._dispatch_step(
                    step=step,
                    run_id=run_id,
                    status=status,
                    trace_events=trace_events,
                    run_inputs=run_request.inputs,
                )

                # Store step output
                self.state_store.set(run_id, step_id, result)

                self._emit(trace_events, run_id, step_id, "step_end", {
                    "step_type": step.type.value,
                    "result_keys": list(result.keys()) if isinstance(result, dict) else [],
                })

            # Run completed successfully
            status.state = RunState.COMPLETED
            status.completed_at = datetime.now(timezone.utc)
            status.outputs = self.state_store.get_all(run_id)

            self._emit(trace_events, run_id, None, "run_complete", {
                "total_steps": len(plan.execution_order),
            })

        except Exception as exc:
            status.state = RunState.FAILED
            status.completed_at = datetime.now(timezone.utc)
            status.error = str(exc)

            self._emit(trace_events, run_id, status.current_step, "error", {
                "error": str(exc),
            })
            logger.exception("Run '%s' failed at step '%s'", run_id, status.current_step)

        # Persist trace events on the session for observability
        self.session_store.update_session(run_id, {
            "trace_events": [evt.model_dump(mode="json") for evt in trace_events],
            "final_state": status.state.value,
        })

        return status

    # ------------------------------------------------------------------
    # Step dispatchers
    # ------------------------------------------------------------------

    async def _dispatch_step(
        self,
        step: RuntimeStep,
        run_id: str,
        status: RunStatus,
        trace_events: list[TraceEvent],
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Route a step to the appropriate handler based on its type."""
        if step.type == StepType.TOOL_CALL:
            return await self._execute_tool_call(step, run_id, run_inputs)

        if step.type == StepType.LLM_AGENT:
            return await self._execute_llm_agent(step, run_id, run_inputs)

        if step.type == StepType.APPROVAL:
            return await self._execute_approval(
                step, run_id, status, trace_events,
            )

        if step.type == StepType.EVALUATOR:
            return await self._execute_evaluator(step, run_id, run_inputs)

        if step.type == StepType.ROUTER:
            return await self._execute_stub(step, "router")

        if step.type == StepType.PARALLEL:
            return await self._execute_stub(step, "parallel")

        if step.type == StepType.AGGREGATOR:
            return await self._execute_stub(step, "aggregator")

        return await self._execute_stub(step, step.type.value)

    async def _execute_tool_call(
        self,
        step: RuntimeStep,
        run_id: str,
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub: execute a tool call step.

        In production this would invoke the tool via the REST/OpenAPI
        wrapper with auth, timeout, and retry handling.
        """
        tool_id = step.tool.id if step.tool else "unknown"
        logger.info("Executing tool_call step '%s' (tool=%s)", step.id, tool_id)

        # Stub: simulate a successful tool invocation
        await asyncio.sleep(0)  # yield control
        return {
            "tool_id": tool_id,
            "status": "success",
            "output": f"Stub result from tool '{tool_id}'",
        }

    async def _execute_llm_agent(
        self,
        step: RuntimeStep,
        run_id: str,
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub: execute an LLM agent step.

        In production this would compile the step into an ADK Agent,
        attach tools, set the prompt, and invoke the model.
        """
        model_name = step.model or "default"
        logger.info("Executing llm_agent step '%s' (model=%s)", step.id, model_name)

        # Resolve model to validate it exists
        if step.model:
            self.model_router.resolve(step.model)

        prompt_text = step.prompt.text if step.prompt else ""
        tool_ids = [t.id for t in step.tools]

        await asyncio.sleep(0)
        return {
            "model": model_name,
            "prompt_snippet": prompt_text[:100] if prompt_text else "",
            "tools_available": tool_ids,
            "status": "success",
            "output": f"Stub LLM response for step '{step.id}'",
        }

    async def _execute_approval(
        self,
        step: RuntimeStep,
        run_id: str,
        status: RunStatus,
        trace_events: list[TraceEvent],
    ) -> dict[str, Any]:
        """Handle an approval gate step.

        Registers an ApprovalRequest, transitions the run to
        WAITING_APPROVAL, and for v1 auto-approves immediately.
        """
        policy = step.approval_policy
        policy_id = policy.id if policy else "default_policy"
        approver_roles = (
            policy.approval.approver_roles
            if policy and policy.approval
            else []
        )

        request = ApprovalRequest(
            run_id=run_id,
            step_id=step.id,
            policy_id=policy_id,
            approver_roles=approver_roles,
        )
        self.approval_manager.register_approval(request)

        # Transition to waiting
        status.state = RunState.WAITING_APPROVAL
        self._emit(trace_events, run_id, step.id, "approval_requested", {
            "approval_id": request.approval_id,
            "policy_id": policy_id,
        })

        logger.info(
            "Approval gate at step '%s': auto-approving for v1", step.id,
        )

        # V1: auto-approve
        self.approval_manager.submit_decision(
            approval_id=request.approval_id,
            outcome=ApprovalOutcome.APPROVED,
            decided_by="system_auto_approve_v1",
        )

        # Resume running
        status.state = RunState.RUNNING
        self._emit(trace_events, run_id, step.id, "approval_granted", {
            "approval_id": request.approval_id,
            "decided_by": "system_auto_approve_v1",
        })

        return {
            "approval_id": request.approval_id,
            "outcome": ApprovalOutcome.APPROVED.value,
            "decided_by": "system_auto_approve_v1",
        }

    async def _execute_evaluator(
        self,
        step: RuntimeStep,
        run_id: str,
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub: execute an evaluator step.

        In production this would run evaluation logic (possibly LLM-based)
        and return a pass/fail determination.
        """
        logger.info("Executing evaluator step '%s'", step.id)

        await asyncio.sleep(0)
        return {
            "status": "success",
            "passed": True,
            "score": 1.0,
            "output": f"Stub evaluation for step '{step.id}': passed",
        }

    async def _execute_stub(
        self,
        step: RuntimeStep,
        step_type_label: str,
    ) -> dict[str, Any]:
        """Generic stub for step types not yet implemented."""
        logger.info(
            "Executing %s step '%s' (stub)", step_type_label, step.id,
        )
        await asyncio.sleep(0)
        return {
            "status": "success",
            "output": f"Stub result for {step_type_label} step '{step.id}'",
        }

    # ------------------------------------------------------------------
    # Trace helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _emit(
        collector: list[TraceEvent],
        run_id: str,
        step_id: str | None,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Create a TraceEvent and append it to the collector list."""
        event = TraceEvent(
            run_id=run_id,
            step_id=step_id,
            event_type=event_type,
            data=data,
        )
        collector.append(event)
        logger.debug("Trace event: %s (step=%s)", event_type, step_id)
