"""Workflow executor — drives a RuntimePlan through step-by-step execution.

Supports five template patterns:
- sequential (with optional approval gates)
- single agent with tools
- router → specialists → aggregator
- parallel fanout → aggregator
- evaluator loop (generate → evaluate → retry)

For v1 the actual ADK integration is stubbed; each step type returns a
placeholder result dict.  The executor handles sequencing, parallel dispatch,
routing, looping, approval gates, trace event collection, and state management.
"""

from __future__ import annotations

import asyncio
import logging
import time
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

MAX_EVAL_ITERATIONS = 5


class ExecutionError(Exception):
    """Raised when a step execution fails unrecoverably."""


class WorkflowExecutor:
    """Executes a :class:`RuntimePlan` step by step.

    Supports sequential, parallel, router, and evaluator-loop patterns.
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
        """Execute a workflow plan from start to finish."""
        from agentwonder.schemas.run import RunRequest  # noqa: F811

        status = RunStatus(
            workflow_id=plan.workflow_id,
            workflow_version=plan.workflow_version,
            template_id=plan.template_id,
            state=RunState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        run_id = status.run_id
        trace_events: list[TraceEvent] = []

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
            "model_default": plan.models.default,
            "model_evaluator": plan.models.evaluator or "",
        })

        step_map: dict[str, RuntimeStep] = {s.id: s for s in plan.steps}

        try:
            # Execute using parallel groups when available
            for group in plan.parallel_groups:
                if len(group) == 1:
                    # Single step — sequential execution
                    step_id = group[0]
                    step = step_map[step_id]
                    status.current_step = step_id
                    await self._run_step(
                        step, run_id, status, trace_events,
                        run_request.inputs, step_map,
                    )
                else:
                    # Multiple steps in group — parallel execution
                    self._emit(trace_events, run_id, None, "parallel_group_start", {
                        "steps": group,
                    })
                    tasks = []
                    for step_id in group:
                        step = step_map[step_id]
                        tasks.append(
                            self._run_step(
                                step, run_id, status, trace_events,
                                run_request.inputs, step_map,
                            )
                        )
                    await asyncio.gather(*tasks)
                    self._emit(trace_events, run_id, None, "parallel_group_end", {
                        "steps": group,
                    })

            status.state = RunState.COMPLETED
            status.completed_at = datetime.now(timezone.utc)
            status.outputs = self.state_store.get_all(run_id)

            self._emit(trace_events, run_id, None, "run_complete", {
                "total_steps": len(plan.execution_order),
                "duration_ms": _elapsed_ms(status.started_at),
            })

        except Exception as exc:
            status.state = RunState.FAILED
            status.completed_at = datetime.now(timezone.utc)
            status.error = str(exc)
            self._emit(trace_events, run_id, status.current_step, "error", {
                "error": str(exc),
            })
            logger.exception("Run '%s' failed at step '%s'", run_id, status.current_step)

        self.session_store.update_session(run_id, {
            "trace_events": [evt.model_dump(mode="json") for evt in trace_events],
            "final_state": status.state.value,
        })

        return status

    # ------------------------------------------------------------------
    # Step runner with timing
    # ------------------------------------------------------------------

    async def _run_step(
        self,
        step: RuntimeStep,
        run_id: str,
        status: RunStatus,
        trace_events: list[TraceEvent],
        run_inputs: dict[str, Any],
        step_map: dict[str, RuntimeStep],
    ) -> dict[str, Any]:
        """Execute a single step with timing and trace instrumentation."""
        t0 = time.monotonic()
        self._emit(trace_events, run_id, step.id, "step_start", {
            "step_type": step.type.value,
            "model": step.model or "",
            "prompt_version": step.prompt.version if step.prompt else "",
        })

        result = await self._dispatch_step(
            step=step, run_id=run_id, status=status,
            trace_events=trace_events, run_inputs=run_inputs,
            step_map=step_map,
        )

        duration_ms = round((time.monotonic() - t0) * 1000, 2)
        self.state_store.set(run_id, step.id, result)

        self._emit(trace_events, run_id, step.id, "step_end", {
            "step_type": step.type.value,
            "duration_ms": duration_ms,
            "result_keys": list(result.keys()) if isinstance(result, dict) else [],
        })
        return result

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
        step_map: dict[str, RuntimeStep],
    ) -> dict[str, Any]:
        """Route a step to the appropriate handler based on its type."""
        if step.type == StepType.TOOL_CALL:
            return await self._execute_tool_call(step, run_id, trace_events, run_inputs)
        if step.type == StepType.LLM_AGENT:
            return await self._execute_llm_agent(step, run_id, trace_events, run_inputs)
        if step.type == StepType.APPROVAL:
            return await self._execute_approval(step, run_id, status, trace_events)
        if step.type == StepType.EVALUATOR:
            return await self._execute_evaluator(step, run_id, trace_events, run_inputs)
        if step.type == StepType.ROUTER:
            return await self._execute_router(step, run_id, trace_events, run_inputs, step_map)
        if step.type == StepType.PARALLEL:
            return await self._execute_parallel_marker(step, run_id)
        if step.type == StepType.AGGREGATOR:
            return await self._execute_aggregator(step, run_id)
        return {"status": "skipped", "reason": f"Unknown step type: {step.type.value}"}

    async def _execute_tool_call(
        self,
        step: RuntimeStep,
        run_id: str,
        trace_events: list[TraceEvent],
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub: execute a tool call step with trace instrumentation."""
        tool_id = step.tool.id if step.tool else "unknown"
        logger.info("Executing tool_call step '%s' (tool=%s)", step.id, tool_id)

        self._emit(trace_events, run_id, step.id, "tool_invoked", {
            "tool_id": tool_id,
            "tool_version": step.tool.version if step.tool else "",
            "method": step.tool.method if step.tool else "",
            "endpoint": step.tool.endpoint if step.tool else "",
            "inputs": run_inputs,
        })

        await asyncio.sleep(0)
        return {
            "tool_id": tool_id,
            "status": "success",
            "output": f"Stub result from tool '{tool_id}'",
        }

    async def _execute_llm_agent(
        self,
        step: RuntimeStep,
        run_id: str,
        trace_events: list[TraceEvent],
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Stub: execute an LLM agent step."""
        model_name = step.model or "default"
        logger.info("Executing llm_agent step '%s' (model=%s)", step.id, model_name)

        if step.model:
            self.model_router.resolve(step.model)

        prompt_text = step.prompt.text if step.prompt else ""
        tool_ids = [t.id for t in step.tools]

        self._emit(trace_events, run_id, step.id, "llm_invoked", {
            "model": model_name,
            "prompt_id": step.prompt.id if step.prompt else "",
            "prompt_version": step.prompt.version if step.prompt else "",
            "tools_available": tool_ids,
        })

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
        """Handle an approval gate step with timeout and reject support."""
        policy = step.approval_policy
        policy_id = policy.id if policy else "default_policy"
        on_reject = "fail_run"
        timeout_minutes = 60
        approver_roles: list[str] = []

        if policy and policy.approval:
            approver_roles = policy.approval.approver_roles
            on_reject = policy.approval.on_reject
            timeout_minutes = policy.approval.timeout_minutes

        request = ApprovalRequest(
            run_id=run_id,
            step_id=step.id,
            policy_id=policy_id,
            approver_roles=approver_roles,
        )
        self.approval_manager.register_approval(request)

        status.state = RunState.WAITING_APPROVAL
        self._emit(trace_events, run_id, step.id, "approval_requested", {
            "approval_id": request.approval_id,
            "policy_id": policy_id,
            "approver_roles": approver_roles,
            "timeout_minutes": timeout_minutes,
            "on_reject": on_reject,
        })

        logger.info("Approval gate at step '%s': auto-approving for v1", step.id)

        # V1: auto-approve (production would wait for external decision)
        self.approval_manager.submit_decision(
            approval_id=request.approval_id,
            outcome=ApprovalOutcome.APPROVED,
            decided_by="system_auto_approve_v1",
        )

        status.state = RunState.RUNNING
        self._emit(trace_events, run_id, step.id, "approval_decided", {
            "approval_id": request.approval_id,
            "outcome": "approved",
            "decided_by": "system_auto_approve_v1",
            "on_reject": on_reject,
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
        trace_events: list[TraceEvent],
        run_inputs: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute an evaluator step. Returns pass/fail with score."""
        logger.info("Executing evaluator step '%s'", step.id)

        # Gather prior step results for evaluation context
        prior_outputs = self.state_store.get_all(run_id)

        self._emit(trace_events, run_id, step.id, "eval_started", {
            "prior_steps_available": list(prior_outputs.keys()),
        })

        await asyncio.sleep(0)
        result = {
            "status": "success",
            "passed": True,
            "score": 0.95,
            "output": f"Stub evaluation for step '{step.id}': passed",
        }

        self._emit(trace_events, run_id, step.id, "eval_completed", {
            "passed": result["passed"],
            "score": result["score"],
        })

        return result

    # ------------------------------------------------------------------
    # Template-specific patterns
    # ------------------------------------------------------------------

    async def _execute_router(
        self,
        step: RuntimeStep,
        run_id: str,
        trace_events: list[TraceEvent],
        run_inputs: dict[str, Any],
        step_map: dict[str, RuntimeStep],
    ) -> dict[str, Any]:
        """Execute a router step that selects which specialist to invoke.

        The router examines inputs and chooses one or more downstream steps.
        In production, an LLM would make the routing decision.
        For v1, we route to the first dependent step (stub behavior).
        """
        logger.info("Executing router step '%s'", step.id)

        # Find steps that depend on this router
        dependents = [
            s for s in step_map.values()
            if step.id in s.depends_on and s.type != StepType.AGGREGATOR
        ]
        dependent_ids = [d.id for d in dependents]

        # Stub: pick first specialist (production: LLM routing decision)
        selected = dependent_ids[0] if dependent_ids else None

        self._emit(trace_events, run_id, step.id, "router_decision", {
            "available_routes": dependent_ids,
            "selected_route": selected,
        })

        await asyncio.sleep(0)
        return {
            "status": "success",
            "available_routes": dependent_ids,
            "selected_route": selected,
            "output": f"Routed to '{selected}'",
        }

    async def _execute_parallel_marker(
        self,
        step: RuntimeStep,
        run_id: str,
    ) -> dict[str, Any]:
        """Marker for parallel fanout steps.

        Actual parallel execution is handled by the parallel_groups in
        the main execute() loop. This handler is for explicitly typed
        parallel steps in the workflow definition.
        """
        logger.info("Parallel marker step '%s' — branches dispatched by executor", step.id)
        await asyncio.sleep(0)
        return {
            "status": "success",
            "output": f"Parallel fanout marker for step '{step.id}'",
        }

    async def _execute_aggregator(
        self,
        step: RuntimeStep,
        run_id: str,
    ) -> dict[str, Any]:
        """Aggregate results from preceding parallel or routed steps.

        Collects all outputs from steps this aggregator depends on.
        """
        logger.info("Executing aggregator step '%s'", step.id)

        # Gather outputs from dependency steps
        all_outputs = self.state_store.get_all(run_id)
        aggregated = {}
        for dep_id in step.depends_on:
            dep_output = all_outputs.get(dep_id)
            if dep_output is not None:
                aggregated[dep_id] = dep_output

        await asyncio.sleep(0)
        return {
            "status": "success",
            "aggregated_from": list(aggregated.keys()),
            "branch_count": len(aggregated),
            "branches": aggregated,
            "output": f"Aggregated {len(aggregated)} branch results",
        }

    # ------------------------------------------------------------------
    # Evaluator loop support
    # ------------------------------------------------------------------

    async def execute_with_eval_loop(
        self,
        run_request: "RunRequest",
        plan: RuntimePlan,
        generator_step_id: str,
        evaluator_step_id: str,
        max_iterations: int = MAX_EVAL_ITERATIONS,
    ) -> RunStatus:
        """Execute a workflow with evaluator loop retry logic.

        Runs the generator → evaluator cycle up to max_iterations times.
        If the evaluator passes, proceeds. If it fails, re-runs the
        generator with feedback.
        """
        from agentwonder.schemas.run import RunRequest  # noqa: F811

        status = RunStatus(
            workflow_id=plan.workflow_id,
            workflow_version=plan.workflow_version,
            template_id=plan.template_id,
            state=RunState.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        run_id = status.run_id
        trace_events: list[TraceEvent] = []

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
            "eval_loop": True,
            "max_iterations": max_iterations,
        })

        step_map: dict[str, RuntimeStep] = {s.id: s for s in plan.steps}

        try:
            # Execute pre-loop steps (before generator)
            pre_loop_steps = []
            loop_steps = {generator_step_id, evaluator_step_id}
            post_loop_steps = []
            found_loop = False
            past_loop = False

            for step_id in plan.execution_order:
                if step_id in loop_steps:
                    found_loop = True
                elif not found_loop:
                    pre_loop_steps.append(step_id)
                elif found_loop:
                    past_loop = True
                    post_loop_steps.append(step_id)

            # Run pre-loop steps
            for step_id in pre_loop_steps:
                step = step_map[step_id]
                status.current_step = step_id
                await self._run_step(
                    step, run_id, status, trace_events,
                    run_request.inputs, step_map,
                )

            # Evaluator loop
            iteration = 0
            passed = False
            while iteration < max_iterations and not passed:
                iteration += 1
                self._emit(trace_events, run_id, None, "eval_loop_iteration", {
                    "iteration": iteration,
                    "max_iterations": max_iterations,
                })

                # Run generator
                gen_step = step_map[generator_step_id]
                status.current_step = generator_step_id
                gen_result = await self._run_step(
                    gen_step, run_id, status, trace_events,
                    run_request.inputs, step_map,
                )

                # Run evaluator
                eval_step = step_map[evaluator_step_id]
                status.current_step = evaluator_step_id
                eval_result = await self._run_step(
                    eval_step, run_id, status, trace_events,
                    run_request.inputs, step_map,
                )

                passed = eval_result.get("passed", False)
                self._emit(trace_events, run_id, None, "eval_loop_result", {
                    "iteration": iteration,
                    "passed": passed,
                    "score": eval_result.get("score", 0),
                })

                if not passed:
                    logger.info(
                        "Eval loop iteration %d: failed (score=%.2f), retrying",
                        iteration, eval_result.get("score", 0),
                    )

            if not passed:
                raise ExecutionError(
                    f"Evaluator loop did not pass after {max_iterations} iterations"
                )

            # Run post-loop steps
            for step_id in post_loop_steps:
                step = step_map[step_id]
                status.current_step = step_id
                await self._run_step(
                    step, run_id, status, trace_events,
                    run_request.inputs, step_map,
                )

            status.state = RunState.COMPLETED
            status.completed_at = datetime.now(timezone.utc)
            status.outputs = self.state_store.get_all(run_id)
            self._emit(trace_events, run_id, None, "run_complete", {
                "total_steps": len(plan.execution_order),
                "eval_iterations": iteration,
                "duration_ms": _elapsed_ms(status.started_at),
            })

        except Exception as exc:
            status.state = RunState.FAILED
            status.completed_at = datetime.now(timezone.utc)
            status.error = str(exc)
            self._emit(trace_events, run_id, status.current_step, "error", {
                "error": str(exc),
            })
            logger.exception("Run '%s' failed", run_id)

        self.session_store.update_session(run_id, {
            "trace_events": [evt.model_dump(mode="json") for evt in trace_events],
            "final_state": status.state.value,
        })

        return status

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


def _elapsed_ms(start: datetime) -> float:
    """Milliseconds elapsed since start."""
    return round((datetime.now(timezone.utc) - start).total_seconds() * 1000, 2)
