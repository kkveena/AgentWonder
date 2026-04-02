"""Shared fixtures for AgentWonder tests."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml


# ---------------------------------------------------------------------------
# Sample data factories
# ---------------------------------------------------------------------------

def _make_tool_data(**overrides) -> dict:
    base = {
        "id": "test_tool",
        "name": "Test Tool",
        "version": "1.0.0",
        "type": "rest",
        "method": "GET",
        "endpoint": "https://example.com/api/test",
        "timeout_seconds": 10,
        "side_effect_level": "read",
    }
    base.update(overrides)
    return base


def _make_template_data(**overrides) -> dict:
    base = {
        "id": "test_template",
        "version": "1.0.0",
        "allowed_step_types": ["tool_call", "llm_agent", "approval", "evaluator"],
        "requires_explicit_order": True,
        "supports_parallel": False,
    }
    base.update(overrides)
    return base


def _make_policy_data(**overrides) -> dict:
    base = {
        "id": "test_policy",
        "name": "Test Policy",
        "version": "1.0.0",
        "approval": {
            "required": True,
            "approver_roles": ["reviewer"],
            "timeout_minutes": 30,
            "on_reject": "fail_run",
        },
    }
    base.update(overrides)
    return base


def _make_prompt_data(**overrides) -> dict:
    base = {
        "id": "test_prompt",
        "version": "1.0.0",
        "purpose": "Testing",
        "text": "You are a test assistant.",
    }
    base.update(overrides)
    return base


def _make_workflow_data(**overrides) -> dict:
    base = {
        "id": "test_workflow",
        "name": "Test Workflow",
        "version": "1.0.0",
        "template": "test_template",
        "tool_refs": ["test_tool"],
        "steps": [
            {
                "id": "step_one",
                "type": "tool_call",
                "tool": "test_tool",
            },
        ],
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tool_data():
    return _make_tool_data()


@pytest.fixture
def template_data():
    return _make_template_data()


@pytest.fixture
def policy_data():
    return _make_policy_data()


@pytest.fixture
def prompt_data():
    return _make_prompt_data()


@pytest.fixture
def workflow_data():
    return _make_workflow_data()


@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary config directory populated with sample YAML files."""
    for subdir in ("templates", "tools", "prompts", "policies", "workflows"):
        (tmp_path / subdir).mkdir()

    # Template
    _write_yaml(tmp_path / "templates" / "test_template.yaml", _make_template_data())

    # Tool
    _write_yaml(tmp_path / "tools" / "test_tool.yaml", _make_tool_data())

    # Policy
    _write_yaml(tmp_path / "policies" / "test_policy.yaml", _make_policy_data())

    # Prompt
    _write_yaml(tmp_path / "prompts" / "test_prompt.yaml", _make_prompt_data())

    # Workflow
    _write_yaml(tmp_path / "workflows" / "test_workflow.yaml", _make_workflow_data())

    return tmp_path


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
