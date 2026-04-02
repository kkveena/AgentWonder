"""Tests for template-specific validation and the registry layer."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from agentwonder.registry import TemplateRegistry, ToolRegistry, PromptRegistry, PolicyRegistry
from agentwonder.compiler.loader import load_yaml
from agentwonder.compiler.validators import validate_workflow, cross_validate_workflow


# ---------------------------------------------------------------------------
# Registry loading from disk
# ---------------------------------------------------------------------------

class TestRegistryLoading:
    def test_template_registry_from_dir(self, config_dir):
        reg = TemplateRegistry()
        reg.load_from_directory(config_dir / "templates")
        assert len(reg.list_all()) == 1
        assert reg.get("test_template").id == "test_template"

    def test_tool_registry_from_dir(self, config_dir):
        reg = ToolRegistry()
        reg.load_from_directory(config_dir / "tools")
        assert len(reg.list_all()) == 1

    def test_prompt_registry_from_dir(self, config_dir):
        reg = PromptRegistry()
        reg.load_from_directory(config_dir / "prompts")
        assert len(reg.list_all()) == 1

    def test_policy_registry_from_dir(self, config_dir):
        reg = PolicyRegistry()
        reg.load_from_directory(config_dir / "policies")
        assert len(reg.list_all()) == 1

    def test_registry_get_missing(self, config_dir):
        reg = TemplateRegistry()
        reg.load_from_directory(config_dir / "templates")
        with pytest.raises(Exception):
            reg.get("nonexistent")


# ---------------------------------------------------------------------------
# Integration: load from real config/
# ---------------------------------------------------------------------------

class TestRealConfig:
    """Tests against the actual config/ directory in the repo."""

    @pytest.fixture
    def real_config(self):
        p = Path("config")
        if not p.is_dir():
            pytest.skip("config/ directory not present")
        return p

    def test_load_real_templates(self, real_config):
        reg = TemplateRegistry()
        reg.load_from_directory(real_config / "templates")
        templates = reg.list_all()
        assert len(templates) >= 1
        assert any(t.id == "sequential_with_approval" for t in templates)

    def test_load_real_tools(self, real_config):
        reg = ToolRegistry()
        reg.load_from_directory(real_config / "tools")
        tools = reg.list_all()
        assert len(tools) >= 1

    def test_load_and_validate_real_workflow(self, real_config):
        """Full pipeline test: load real config, validate, cross-validate."""
        tr = TemplateRegistry()
        tr.load_from_directory(real_config / "templates")
        tl = ToolRegistry()
        tl.load_from_directory(real_config / "tools")
        pr = PromptRegistry()
        pr.load_from_directory(real_config / "prompts")
        po = PolicyRegistry()
        po.load_from_directory(real_config / "policies")

        tools_dict = {t.id: t for t in tl.list_all()}
        templates_dict = {t.id: t for t in tr.list_all()}
        prompts_dict = {t.id: t for t in pr.list_all()}
        policies_dict = {t.id: t for t in po.list_all()}

        raw = load_yaml(real_config / "workflows" / "break_resolution_v1.yaml")
        wf = validate_workflow(raw)
        errors = cross_validate_workflow(wf, tools_dict, templates_dict, policies_dict, prompts_dict)
        assert errors == [], f"Cross-validation errors: {errors}"
