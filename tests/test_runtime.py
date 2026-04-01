"""Tests for the AgentWonder runtime layer."""

from __future__ import annotations

import asyncio

import pytest

from agentwonder.compiler.builder import build_plan
from agentwonder.compiler.validators import validate_workflow
from agentwonder.compiler.resolver import resolve_workflow
from agentwonder.runtime.executor import WorkflowExecutor
from agentwonder.runtime.session_store import InMemorySessionStore
from agentwonder.runtime.state_store import InMemoryStateStore
from agentwonder.runtime.approvals import ApprovalManager
from agentwonder.runtime.model_router import ModelRouter
from agentwonder.schemas.common import RunState, ApprovalOutcome
from agentwonder.schemas.run import RunRequest, ApprovalRequest
from agentwonder.runtime.session_store import SessionNotFoundError
from agentwonder.runtime.model_router import ModelNotFoundError


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------

class TestSessionStore:
    def test_create_and_get(self):
        store = InMemorySessionStore()
        store.create_session("run1")
        session = store.get_session("run1")
        assert session is not None

    def test_update_session(self):
        store = InMemorySessionStore()
        store.create_session("run1")
        store.update_session("run1", {"key": "value"})
        session = store.get_session("run1")
        assert session["data"]["key"] == "value"

    def test_get_missing_session(self):
        store = InMemorySessionStore()
        with pytest.raises(SessionNotFoundError):
            store.get_session("nonexistent")

    def test_delete_session(self):
        store = InMemorySessionStore()
        store.create_session("run1")
        store.delete_session("run1")
        with pytest.raises(SessionNotFoundError):
            store.get_session("run1")


# ---------------------------------------------------------------------------
# State store
# ---------------------------------------------------------------------------

class TestStateStore:
    def test_set_and_get(self):
        store = InMemoryStateStore()
        store.set("run1", "step1", {"result": "ok"})
        assert store.get("run1", "step1") == {"result": "ok"}

    def test_get_missing(self):
        store = InMemoryStateStore()
        assert store.get("run1", "step1") is None

    def test_get_all(self):
        store = InMemoryStateStore()
        store.set("run1", "s1", "a")
        store.set("run1", "s2", "b")
        all_data = store.get_all("run1")
        assert all_data == {"s1": "a", "s2": "b"}


# ---------------------------------------------------------------------------
# Approval manager
# ---------------------------------------------------------------------------

class TestApprovalManager:
    def test_register_and_get_pending(self):
        mgr = ApprovalManager()
        req = ApprovalRequest(run_id="r1", step_id="s1", policy_id="p1")
        mgr.register_approval(req)
        pending = mgr.get_pending("r1")
        assert len(pending) == 1
        assert pending[0].step_id == "s1"

    def test_submit_decision(self):
        mgr = ApprovalManager()
        req = ApprovalRequest(run_id="r1", step_id="s1", policy_id="p1")
        mgr.register_approval(req)
        mgr.submit_decision(req.approval_id, ApprovalOutcome.APPROVED, "tester")
        pending = mgr.get_pending("r1")
        assert len(pending) == 0


# ---------------------------------------------------------------------------
# Model router
# ---------------------------------------------------------------------------

class TestModelRouter:
    def test_resolve_known_model(self):
        router = ModelRouter()
        info = router.resolve("gemini-2.5-flash")
        assert info.model_id == "gemini-2.5-flash"

    def test_resolve_unknown_model_raises(self):
        router = ModelRouter()
        with pytest.raises(ModelNotFoundError):
            router.resolve("custom-model-xyz")


# ---------------------------------------------------------------------------
# Executor (integration)
# ---------------------------------------------------------------------------

class TestExecutor:
    def _build_plan(self, workflow_data, tool_data, template_data, prompt_data, policy_data):
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig
        from agentwonder.schemas.prompt import PromptConfig
        from agentwonder.schemas.policy import PolicyConfig

        tools = {tool_data["id"]: ToolConfig.model_validate(tool_data)}
        templates = {template_data["id"]: TemplateConfig.model_validate(template_data)}
        prompts = {prompt_data["id"]: PromptConfig.model_validate(prompt_data)}
        policies = {policy_data["id"]: PolicyConfig.model_validate(policy_data)}

        wf = validate_workflow(workflow_data)
        resolved = resolve_workflow(wf, tools, templates, prompts, policies)
        return build_plan(resolved)

    @pytest.mark.asyncio
    async def test_execute_simple_workflow(self, workflow_data, tool_data, template_data, prompt_data, policy_data):
        plan = self._build_plan(workflow_data, tool_data, template_data, prompt_data, policy_data)
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="test_workflow", inputs={"key": "val"})
        status = await executor.execute(request, plan)

        assert status.state == RunState.COMPLETED
        assert "step_one" in status.outputs

    @pytest.mark.asyncio
    async def test_execute_with_approval(self, workflow_data, tool_data, template_data, prompt_data, policy_data):
        workflow_data["steps"] = [
            {"id": "do_work", "type": "tool_call", "tool": "test_tool"},
            {"id": "approve", "type": "approval", "approval_ref": "test_policy", "depends_on": ["do_work"]},
        ]
        plan = self._build_plan(workflow_data, tool_data, template_data, prompt_data, policy_data)
        executor = WorkflowExecutor()
        request = RunRequest(workflow_id="test_workflow", inputs={})
        status = await executor.execute(request, plan)

        assert status.state == RunState.COMPLETED
        assert "approve" in status.outputs
        assert status.outputs["approve"]["outcome"] == "approved"
