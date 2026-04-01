"""Tests for the AgentWonder compiler layer (loader, validators, resolver, builder)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentwonder.compiler.loader import load_yaml, load_all_yaml, YAMLLoadError
from agentwonder.compiler.validators import (
    validate_workflow,
    validate_tool,
    validate_template,
    validate_policy,
    validate_prompt,
    cross_validate_workflow,
    ConfigValidationError,
)
from agentwonder.compiler.resolver import resolve_workflow, ResolutionError
from agentwonder.compiler.builder import build_plan, BuildError


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

class TestLoader:
    def test_load_yaml_valid(self, tmp_path):
        f = tmp_path / "test.yaml"
        f.write_text(yaml.dump({"key": "value"}))
        data = load_yaml(f)
        assert data == {"key": "value"}

    def test_load_yaml_not_found(self, tmp_path):
        with pytest.raises(YAMLLoadError, match="not found"):
            load_yaml(tmp_path / "missing.yaml")

    def test_load_yaml_empty(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        with pytest.raises(YAMLLoadError, match="empty"):
            load_yaml(f)

    def test_load_yaml_not_mapping(self, tmp_path):
        f = tmp_path / "list.yaml"
        f.write_text("- item1\n- item2")
        with pytest.raises(YAMLLoadError, match="mapping"):
            load_yaml(f)

    def test_load_all_yaml(self, tmp_path):
        for i in range(3):
            (tmp_path / f"file{i}.yaml").write_text(yaml.dump({"id": f"f{i}"}))
        results = load_all_yaml(tmp_path)
        assert len(results) == 3

    def test_load_all_yaml_missing_dir(self, tmp_path):
        with pytest.raises(YAMLLoadError, match="not found"):
            load_all_yaml(tmp_path / "nope")

    def test_load_all_yaml_skips_invalid(self, tmp_path):
        (tmp_path / "good.yaml").write_text(yaml.dump({"id": "ok"}))
        (tmp_path / "bad.yaml").write_text("- not a mapping")
        results = load_all_yaml(tmp_path)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class TestValidators:
    def test_validate_tool_valid(self, tool_data):
        tool = validate_tool(tool_data)
        assert tool.id == "test_tool"

    def test_validate_tool_invalid(self):
        with pytest.raises(ConfigValidationError):
            validate_tool({"name": "no id or version"})

    def test_validate_template_valid(self, template_data):
        t = validate_template(template_data)
        assert t.id == "test_template"

    def test_validate_policy_valid(self, policy_data):
        p = validate_policy(policy_data)
        assert p.id == "test_policy"

    def test_validate_prompt_valid(self, prompt_data):
        p = validate_prompt(prompt_data)
        assert p.id == "test_prompt"

    def test_validate_workflow_valid(self, workflow_data):
        wf = validate_workflow(workflow_data)
        assert wf.id == "test_workflow"


class TestCrossValidation:
    def _registries(self, tool_data, template_data, policy_data, prompt_data):
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig
        from agentwonder.schemas.policy import PolicyConfig
        from agentwonder.schemas.prompt import PromptConfig

        tools = {tool_data["id"]: ToolConfig.model_validate(tool_data)}
        templates = {template_data["id"]: TemplateConfig.model_validate(template_data)}
        policies = {policy_data["id"]: PolicyConfig.model_validate(policy_data)}
        prompts = {prompt_data["id"]: PromptConfig.model_validate(prompt_data)}
        return tools, templates, policies, prompts

    def test_cross_validate_pass(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        tools, templates, policies, prompts = self._registries(tool_data, template_data, policy_data, prompt_data)
        wf = validate_workflow(workflow_data)
        errors = cross_validate_workflow(wf, tools, templates, policies, prompts)
        assert errors == []

    def test_cross_validate_unknown_template(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        tools, templates, policies, prompts = self._registries(tool_data, template_data, policy_data, prompt_data)
        workflow_data["template"] = "nonexistent"
        wf = validate_workflow(workflow_data)
        errors = cross_validate_workflow(wf, tools, templates, policies, prompts)
        assert any("unknown template" in e for e in errors)

    def test_cross_validate_unknown_tool_ref(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        tools, templates, policies, prompts = self._registries(tool_data, template_data, policy_data, prompt_data)
        workflow_data["tool_refs"].append("ghost_tool")
        wf = validate_workflow(workflow_data)
        errors = cross_validate_workflow(wf, tools, templates, policies, prompts)
        assert any("ghost_tool" in e for e in errors)

    def test_cross_validate_disallowed_step_type(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        template_data["allowed_step_types"] = ["evaluator"]  # tool_call not allowed
        tools, templates, policies, prompts = self._registries(tool_data, template_data, policy_data, prompt_data)
        wf = validate_workflow(workflow_data)
        errors = cross_validate_workflow(wf, tools, templates, policies, prompts)
        assert any("not allowed" in e for e in errors)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------

class TestResolver:
    def _make_registries(self, tool_data, template_data, policy_data, prompt_data):
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig
        from agentwonder.schemas.policy import PolicyConfig
        from agentwonder.schemas.prompt import PromptConfig

        return (
            {tool_data["id"]: ToolConfig.model_validate(tool_data)},
            {template_data["id"]: TemplateConfig.model_validate(template_data)},
            {prompt_data["id"]: PromptConfig.model_validate(prompt_data)},
            {policy_data["id"]: PolicyConfig.model_validate(policy_data)},
        )

    def test_resolve_success(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        tools, templates, prompts, policies = self._make_registries(tool_data, template_data, policy_data, prompt_data)
        wf = validate_workflow(workflow_data)
        resolved = resolve_workflow(wf, tools, templates, prompts, policies)
        assert resolved.workflow.id == "test_workflow"
        assert "test_tool" in resolved.tools

    def test_resolve_missing_template(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        tools, templates, prompts, policies = self._make_registries(tool_data, template_data, policy_data, prompt_data)
        workflow_data["template"] = "missing_template"
        wf = validate_workflow(workflow_data)
        with pytest.raises(ResolutionError, match="not found"):
            resolve_workflow(wf, tools, {}, prompts, policies)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class TestBuilder:
    def test_build_plan(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
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
        plan = build_plan(resolved)

        assert plan.workflow_id == "test_workflow"
        assert len(plan.steps) == 1
        assert plan.execution_order == ["step_one"]

    def test_build_detects_cycle(self, workflow_data, tool_data, template_data, policy_data, prompt_data):
        from agentwonder.schemas.tool import ToolConfig
        from agentwonder.schemas.template import TemplateConfig
        from agentwonder.schemas.prompt import PromptConfig
        from agentwonder.schemas.policy import PolicyConfig

        workflow_data["steps"] = [
            {"id": "a", "type": "tool_call", "tool": "test_tool", "depends_on": ["b"]},
            {"id": "b", "type": "tool_call", "tool": "test_tool", "depends_on": ["a"]},
        ]

        tools = {tool_data["id"]: ToolConfig.model_validate(tool_data)}
        templates = {template_data["id"]: TemplateConfig.model_validate(template_data)}
        prompts = {prompt_data["id"]: PromptConfig.model_validate(prompt_data)}
        policies = {policy_data["id"]: PolicyConfig.model_validate(policy_data)}

        wf = validate_workflow(workflow_data)
        resolved = resolve_workflow(wf, tools, templates, prompts, policies)

        with pytest.raises(BuildError, match="Cycle"):
            build_plan(resolved)
