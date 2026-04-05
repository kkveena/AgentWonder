"""Phase 2 tests — template patterns, enhanced validation, CLI, approvals."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from agentwonder.compiler.builder import build_plan, BuildError
from agentwonder.compiler.loader import load_yaml, load_all_yaml
from agentwonder.compiler.resolver import resolve_workflow
from agentwonder.compiler.validators import (
    validate_workflow,
    cross_validate_workflow,
    ConfigValidationError,
)
from agentwonder.registry import TemplateRegistry, ToolRegistry, PromptRegistry, PolicyRegistry
from agentwonder.runtime.approvals import ApprovalManager, ApprovalNotFoundError
from agentwonder.runtime.executor import WorkflowExecutor
from agentwonder.schemas.common import ApprovalOutcome, RunState, StepType
from agentwonder.schemas.run import ApprovalRequest, RunRequest
from agentwonder.schemas.template import TemplateConfig, TransitionRule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def real_config():
    p = Path("config")
    if not p.is_dir():
        pytest.skip("config/ directory not present")
    return p


@pytest.fixture
def real_registries(real_config):
    """Load all real registries and return lookup dicts."""
    tr = TemplateRegistry(); tr.load_from_directory(real_config / "templates")
    tl = ToolRegistry(); tl.load_from_directory(real_config / "tools")
    pr = PromptRegistry(); pr.load_from_directory(real_config / "prompts")
    po = PolicyRegistry(); po.load_from_directory(real_config / "policies")
    return {
        "tools": {t.id: t for t in tl.list_all()},
        "templates": {t.id: t for t in tr.list_all()},
        "prompts": {t.id: t for t in pr.list_all()},
        "policies": {t.id: t for t in po.list_all()},
    }


def _load_and_build(real_config, real_registries, workflow_file):
    """Full pipeline: load YAML -> validate -> resolve -> build."""
    raw = load_yaml(real_config / "workflows" / workflow_file)
    wf = validate_workflow(raw)
    errors = cross_validate_workflow(
        wf,
        real_registries["tools"],
        real_registries["templates"],
        real_registries["policies"],
        real_registries["prompts"],
    )
    assert errors == [], f"Cross-validation errors: {errors}"
    resolved = resolve_workflow(
        wf,
        real_registries["tools"],
        real_registries["templates"],
        real_registries["prompts"],
        real_registries["policies"],
    )
    return build_plan(resolved)


# ---------------------------------------------------------------------------
# Template schema Phase 2 fields
# ---------------------------------------------------------------------------

class TestTemplatePhase2:
    def test_template_with_transitions(self):
        t = TemplateConfig(
            id="test_tmpl",
            version="1.0.0",
            allowed_step_types=[StepType.TOOL_CALL, StepType.APPROVAL],
            allowed_transitions=[
                TransitionRule(from_type=StepType.TOOL_CALL, to_types=[StepType.APPROVAL]),
            ],
            requires_approval=True,
        )
        assert t.requires_approval is True
        assert len(t.allowed_transitions) == 1
        assert t.allowed_transitions[0].from_type == StepType.TOOL_CALL

    def test_template_supports_loop(self):
        t = TemplateConfig(
            id="loop_tmpl",
            version="1.0.0",
            supports_loop=True,
            max_steps=20,
        )
        assert t.supports_loop is True
        assert t.max_steps == 20

    def test_template_parallel_branches(self):
        t = TemplateConfig(
            id="par_tmpl",
            version="1.0.0",
            supports_parallel=True,
            max_parallel_branches=10,
        )
        assert t.max_parallel_branches == 10

    def test_all_five_templates_load(self, real_config):
        reg = TemplateRegistry()
        reg.load_from_directory(real_config / "templates")
        ids = {t.id for t in reg.list_all()}
        expected = {
            "single_agent_with_tools",
            "router_specialists",
            "sequential_with_approval",
            "parallel_fanout_aggregate",
            "evaluator_loop",
        }
        assert expected.issubset(ids), f"Missing templates: {expected - ids}"


# ---------------------------------------------------------------------------
# Cross-validation enhancements
# ---------------------------------------------------------------------------

class TestCrossValidationPhase2:
    def test_cycle_detection_at_validation(self):
        raw = {
            "id": "cycle_wf",
            "name": "Cycle Test",
            "version": "1.0.0",
            "template": "test_template",
            "steps": [
                {"id": "a", "type": "tool_call", "tool": "test_tool", "depends_on": ["b"]},
                {"id": "b", "type": "tool_call", "tool": "test_tool", "depends_on": ["a"]},
            ],
        }
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig as TC

        wf = validate_workflow(raw)
        tools = {"test_tool": ToolConfig(id="test_tool", name="T", version="1.0.0")}
        templates = {"test_template": TC(
            id="test_template", version="1.0.0",
            allowed_step_types=[StepType.TOOL_CALL],
        )}
        errors = cross_validate_workflow(wf, tools, templates, {})
        assert any("cycle" in e.lower() for e in errors)

    def test_env_compatibility_check(self):
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig as TC
        from agentwonder.schemas.common import Environment

        raw = {
            "id": "env_wf",
            "name": "Env Test",
            "version": "1.0.0",
            "template": "t",
            "tool_refs": ["prod_only_tool"],
            "steps": [{"id": "s1", "type": "tool_call", "tool": "prod_only_tool"}],
        }
        wf = validate_workflow(raw)
        tools = {"prod_only_tool": ToolConfig(
            id="prod_only_tool", name="P", version="1.0.0",
            allowed_environments=[Environment.PROD],
        )}
        templates = {"t": TC(id="t", version="1.0.0", allowed_step_types=[StepType.TOOL_CALL])}
        errors = cross_validate_workflow(wf, tools, templates, {}, target_environment="dev")
        assert any("not allowed in environment" in e for e in errors)

    def test_template_requires_approval_check(self):
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig as TC

        raw = {
            "id": "no_approval_wf",
            "name": "No Approval",
            "version": "1.0.0",
            "template": "strict_tmpl",
            "steps": [{"id": "s1", "type": "tool_call", "tool": "t"}],
        }
        wf = validate_workflow(raw)
        tools = {"t": ToolConfig(id="t", name="T", version="1.0.0")}
        templates = {"strict_tmpl": TC(
            id="strict_tmpl", version="1.0.0",
            allowed_step_types=[StepType.TOOL_CALL, StepType.APPROVAL],
            requires_approval=True,
        )}
        errors = cross_validate_workflow(wf, tools, templates, {})
        assert any("requires an approval step" in e for e in errors)


# ---------------------------------------------------------------------------
# Template-aware execution
# ---------------------------------------------------------------------------

class TestParallelExecution:
    @pytest.mark.asyncio
    async def test_parallel_fanout_workflow(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "market_data_fanout_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="market_data_fanout_v1", inputs={"source": "test"})
        status = await executor.execute(request, plan)

        assert status.state == RunState.COMPLETED
        assert "combine_snapshot" in status.outputs
        agg_output = status.outputs["combine_snapshot"]
        assert agg_output["status"] == "success"


class TestRouterExecution:
    @pytest.mark.asyncio
    async def test_router_workflow(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "ticket_router_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="ticket_router_v1", inputs={"ticket_id": "T-100"})
        status = await executor.execute(request, plan)

        assert status.state == RunState.COMPLETED
        assert "route_ticket" in status.outputs
        assert "aggregate_response" in status.outputs
        assert status.outputs["route_ticket"]["status"] == "success"


class TestSingleAgentExecution:
    @pytest.mark.asyncio
    async def test_single_agent_workflow(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "customer_support_agent_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="customer_support_agent_v1", inputs={"query": "help"})
        status = await executor.execute(request, plan)

        assert status.state == RunState.COMPLETED


class TestEvaluatorLoop:
    @pytest.mark.asyncio
    async def test_evaluator_loop_workflow(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "content_review_loop_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="content_review_loop_v1", inputs={"topic": "test"})

        # Use eval loop execution
        status = await executor.execute_with_eval_loop(
            request, plan,
            generator_step_id="generate_draft",
            evaluator_step_id="evaluate_quality",
            max_iterations=3,
        )

        assert status.state == RunState.COMPLETED


# ---------------------------------------------------------------------------
# Enhanced observability
# ---------------------------------------------------------------------------

class TestEnhancedTracing:
    @pytest.mark.asyncio
    async def test_step_timings_in_trace(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "break_resolution_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="break_resolution_v1", inputs={"break_id": "B1", "source_system": "t"})
        status = await executor.execute(request, plan)

        session = executor.session_store.get_session(status.run_id)
        events = session["data"]["trace_events"]

        # Check step_end events have duration_ms
        step_ends = [e for e in events if e["event_type"] == "step_end"]
        assert len(step_ends) > 0
        for evt in step_ends:
            assert "duration_ms" in evt["data"]

    @pytest.mark.asyncio
    async def test_model_info_in_trace(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "break_resolution_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="break_resolution_v1", inputs={"break_id": "B1", "source_system": "t"})
        status = await executor.execute(request, plan)

        session = executor.session_store.get_session(status.run_id)
        events = session["data"]["trace_events"]

        # run_start should have model info
        run_start = [e for e in events if e["event_type"] == "run_start"][0]
        assert "model_default" in run_start["data"]

    @pytest.mark.asyncio
    async def test_tool_invoked_events(self, real_config, real_registries):
        plan = _load_and_build(real_config, real_registries, "break_resolution_v1.yaml")
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="break_resolution_v1", inputs={"break_id": "B1", "source_system": "t"})
        status = await executor.execute(request, plan)

        session = executor.session_store.get_session(status.run_id)
        events = session["data"]["trace_events"]

        tool_events = [e for e in events if e["event_type"] == "tool_invoked"]
        assert len(tool_events) >= 1
        assert "tool_id" in tool_events[0]["data"]
        assert "tool_version" in tool_events[0]["data"]


# ---------------------------------------------------------------------------
# Approval enhancements
# ---------------------------------------------------------------------------

class TestApprovalPhase2:
    def test_check_timeouts(self):
        from datetime import datetime, timezone, timedelta

        mgr = ApprovalManager()
        req = ApprovalRequest(run_id="r1", step_id="s1", policy_id="p1")
        # Backdate the request
        req.requested_at = datetime.now(timezone.utc) - timedelta(minutes=120)
        mgr.register_approval(req)

        timed_out = mgr.check_timeouts(timeout_minutes=60)
        assert len(timed_out) == 1
        assert timed_out[0].outcome == ApprovalOutcome.TIMED_OUT

    def test_get_all_for_run(self):
        mgr = ApprovalManager()
        req1 = ApprovalRequest(run_id="r1", step_id="s1", policy_id="p1")
        req2 = ApprovalRequest(run_id="r1", step_id="s2", policy_id="p2")
        mgr.register_approval(req1)
        mgr.register_approval(req2)
        mgr.submit_decision(req1.approval_id, ApprovalOutcome.APPROVED, "tester")

        all_approvals = mgr.get_all_for_run("r1")
        assert len(all_approvals) == 2
        pending = mgr.get_pending("r1")
        assert len(pending) == 1

    def test_get_approval_by_id(self):
        mgr = ApprovalManager()
        req = ApprovalRequest(run_id="r1", step_id="s1", policy_id="p1")
        mgr.register_approval(req)
        fetched = mgr.get_approval(req.approval_id)
        assert fetched.step_id == "s1"

    def test_get_approval_not_found(self):
        mgr = ApprovalManager()
        with pytest.raises(ApprovalNotFoundError):
            mgr.get_approval("nonexistent")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

class TestCLI:
    def test_list_templates(self):
        from agentwonder.cli import main
        rc = main(["list", "templates"])
        assert rc == 0

    def test_list_tools(self):
        from agentwonder.cli import main
        rc = main(["list", "tools"])
        assert rc == 0

    def test_list_workflows(self):
        from agentwonder.cli import main
        rc = main(["list", "workflows"])
        assert rc == 0

    def test_validate_valid_workflow(self):
        from agentwonder.cli import main
        rc = main(["validate", "config/workflows/break_resolution_v1.yaml"])
        assert rc == 0

    def test_run_workflow(self):
        from agentwonder.cli import main
        rc = main(["run", "break_resolution_v1", "-i", "break_id=BRK-1", "-i", "source_system=test"])
        assert rc == 0


# ---------------------------------------------------------------------------
# All five workflow templates validate and execute
# ---------------------------------------------------------------------------

class TestAllWorkflowsEndToEnd:
    """Integration test: every workflow in config/ validates and executes."""

    @pytest.mark.asyncio
    async def test_all_workflows_pass(self, real_config, real_registries):
        workflows_dir = real_config / "workflows"
        raw_list = load_all_yaml(workflows_dir)
        assert len(raw_list) >= 5, f"Expected at least 5 workflows, found {len(raw_list)}"

        for raw in raw_list:
            wf = validate_workflow(raw)
            errors = cross_validate_workflow(
                wf,
                real_registries["tools"],
                real_registries["templates"],
                real_registries["policies"],
                real_registries["prompts"],
            )
            assert errors == [], f"Workflow '{wf.id}' errors: {errors}"
