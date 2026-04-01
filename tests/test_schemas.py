"""Tests for AgentWonder Pydantic schema models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentwonder.schemas.common import StepType, SideEffectLevel, Environment, RunState
from agentwonder.schemas.tool import ToolConfig
from agentwonder.schemas.policy import PolicyConfig
from agentwonder.schemas.prompt import PromptConfig
from agentwonder.schemas.template import TemplateConfig
from agentwonder.schemas.workflow import WorkflowConfig, WorkflowStep
from agentwonder.schemas.run import RunRequest, RunStatus, ApprovalRequest, TraceEvent


# ---------------------------------------------------------------------------
# ToolConfig
# ---------------------------------------------------------------------------

class TestToolConfig:
    def test_valid_tool(self, tool_data):
        tool = ToolConfig.model_validate(tool_data)
        assert tool.id == "test_tool"
        assert tool.version == "1.0.0"
        assert tool.side_effect_level == SideEffectLevel.READ

    def test_tool_missing_id(self, tool_data):
        del tool_data["id"]
        with pytest.raises(ValidationError):
            ToolConfig.model_validate(tool_data)

    def test_tool_bad_version_format(self, tool_data):
        tool_data["version"] = "v1"
        with pytest.raises(ValidationError):
            ToolConfig.model_validate(tool_data)

    def test_tool_bad_id_format(self, tool_data):
        tool_data["id"] = "Invalid-ID"
        with pytest.raises(ValidationError):
            ToolConfig.model_validate(tool_data)

    def test_tool_defaults(self):
        tool = ToolConfig(id="minimal_tool", name="Min", version="0.1.0")
        assert tool.timeout_seconds == 30
        assert tool.idempotent is False
        assert tool.side_effect_level == SideEffectLevel.READ
        assert Environment.DEV in tool.allowed_environments


# ---------------------------------------------------------------------------
# PolicyConfig
# ---------------------------------------------------------------------------

class TestPolicyConfig:
    def test_valid_policy(self, policy_data):
        policy = PolicyConfig.model_validate(policy_data)
        assert policy.id == "test_policy"
        assert policy.approval is not None
        assert policy.approval.required is True

    def test_policy_missing_name(self, policy_data):
        del policy_data["name"]
        with pytest.raises(ValidationError):
            PolicyConfig.model_validate(policy_data)

    def test_policy_bad_on_reject(self, policy_data):
        policy_data["approval"]["on_reject"] = "explode"
        with pytest.raises(ValidationError):
            PolicyConfig.model_validate(policy_data)


# ---------------------------------------------------------------------------
# PromptConfig
# ---------------------------------------------------------------------------

class TestPromptConfig:
    def test_valid_prompt(self, prompt_data):
        prompt = PromptConfig.model_validate(prompt_data)
        assert prompt.id == "test_prompt"
        assert "test assistant" in prompt.text

    def test_prompt_empty_text(self, prompt_data):
        prompt_data["text"] = ""
        with pytest.raises(ValidationError):
            PromptConfig.model_validate(prompt_data)


# ---------------------------------------------------------------------------
# TemplateConfig
# ---------------------------------------------------------------------------

class TestTemplateConfig:
    def test_valid_template(self, template_data):
        template = TemplateConfig.model_validate(template_data)
        assert template.id == "test_template"
        assert StepType.TOOL_CALL in template.allowed_step_types

    def test_template_max_steps_boundary(self, template_data):
        template_data["max_steps"] = 0
        with pytest.raises(ValidationError):
            TemplateConfig.model_validate(template_data)


# ---------------------------------------------------------------------------
# WorkflowConfig
# ---------------------------------------------------------------------------

class TestWorkflowConfig:
    def test_valid_workflow(self, workflow_data):
        wf = WorkflowConfig.model_validate(workflow_data)
        assert wf.id == "test_workflow"
        assert len(wf.steps) == 1
        assert wf.steps[0].type == StepType.TOOL_CALL

    def test_workflow_no_steps(self, workflow_data):
        workflow_data["steps"] = []
        with pytest.raises(ValidationError):
            WorkflowConfig.model_validate(workflow_data)

    def test_workflow_duplicate_step_ids(self, workflow_data):
        workflow_data["steps"] = [
            {"id": "dup", "type": "tool_call", "tool": "test_tool"},
            {"id": "dup", "type": "tool_call", "tool": "test_tool"},
        ]
        with pytest.raises(ValidationError, match="unique"):
            WorkflowConfig.model_validate(workflow_data)

    def test_tool_call_step_requires_tool(self, workflow_data):
        workflow_data["steps"] = [
            {"id": "missing_tool", "type": "tool_call"},
        ]
        with pytest.raises(ValidationError, match="tool_call requires"):
            WorkflowConfig.model_validate(workflow_data)

    def test_approval_step_requires_approval_ref(self, workflow_data):
        workflow_data["steps"] = [
            {"id": "missing_approval", "type": "approval"},
        ]
        with pytest.raises(ValidationError, match="approval requires"):
            WorkflowConfig.model_validate(workflow_data)


# ---------------------------------------------------------------------------
# RunRequest / RunStatus
# ---------------------------------------------------------------------------

class TestRunModels:
    def test_run_request(self):
        req = RunRequest(workflow_id="wf1", inputs={"key": "val"})
        assert req.workflow_id == "wf1"

    def test_run_status_defaults(self):
        status = RunStatus(workflow_id="wf1")
        assert status.state == RunState.PENDING
        assert status.run_id  # auto-generated
        assert status.error is None

    def test_trace_event(self):
        evt = TraceEvent(run_id="r1", event_type="step_start")
        assert evt.run_id == "r1"
        assert evt.timestamp is not None

    def test_approval_request(self):
        req = ApprovalRequest(run_id="r1", step_id="s1", policy_id="p1")
        assert req.outcome is None
