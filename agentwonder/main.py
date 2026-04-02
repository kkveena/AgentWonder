"""AgentWonder API — FastAPI application entry point.

Creates the FastAPI app, includes all routers under ``/api/v1``, and
loads registries from the config directory on startup.

Usage::

    # Default (config/ relative to cwd):
    uvicorn agentwonder.main:app --reload

    # Custom config directory:
    import agentwonder.main
    app = agentwonder.main.create_app(config_dir="/path/to/config")
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI

from agentwonder.api.routes_health import router as health_router
from agentwonder.api.routes_runs import router as runs_router
from agentwonder.api.routes_templates import router as templates_router
from agentwonder.api.routes_tools import router as tools_router
from agentwonder.compiler.loader import load_all_yaml
from agentwonder.compiler.validators import validate_workflow, ConfigValidationError
from agentwonder.observability.tracing import TraceCollector
from agentwonder.registry import (
    TemplateRegistry,
    ToolRegistry,
    PromptRegistry,
    PolicyRegistry,
)
from agentwonder.runtime.executor import WorkflowExecutor
from agentwonder.schemas.run import RunStatus, TraceEvent

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"


# ---------------------------------------------------------------------------
# Registry and store initialisation
# ---------------------------------------------------------------------------

def _load_registries(config_dir: Path) -> dict[str, Any]:
    """Load all registries from the config directory.

    Silently skips missing subdirectories so the app can start even with
    an incomplete config tree (useful for development and testing).
    """
    template_registry = TemplateRegistry()
    tool_registry = ToolRegistry()
    prompt_registry = PromptRegistry()
    policy_registry = PolicyRegistry()

    templates_dir = config_dir / "templates"
    tools_dir = config_dir / "tools"
    prompts_dir = config_dir / "prompts"
    policies_dir = config_dir / "policies"

    if templates_dir.is_dir():
        template_registry.load_from_directory(templates_dir)
        logger.info("Loaded templates from %s", templates_dir)
    else:
        logger.warning("Templates directory not found: %s", templates_dir)

    if tools_dir.is_dir():
        tool_registry.load_from_directory(tools_dir)
        logger.info("Loaded tools from %s", tools_dir)
    else:
        logger.warning("Tools directory not found: %s", tools_dir)

    if prompts_dir.is_dir():
        prompt_registry.load_from_directory(prompts_dir)
        logger.info("Loaded prompts from %s", prompts_dir)
    else:
        logger.warning("Prompts directory not found: %s", prompts_dir)

    if policies_dir.is_dir():
        policy_registry.load_from_directory(policies_dir)
        logger.info("Loaded policies from %s", policies_dir)
    else:
        logger.warning("Policies directory not found: %s", policies_dir)

    return {
        "template_registry": template_registry,
        "tool_registry": tool_registry,
        "prompt_registry": prompt_registry,
        "policy_registry": policy_registry,
    }


def _load_workflows(config_dir: Path) -> dict[str, dict[str, Any]]:
    """Load workflow YAML files into an in-memory store keyed by workflow ID.

    Each workflow dict is stored raw (pre-validation) so the run endpoint
    can validate on demand, ensuring the latest validation rules apply.
    """
    workflows_dir = config_dir / "workflows"
    store: dict[str, dict[str, Any]] = {}

    if not workflows_dir.is_dir():
        logger.warning("Workflows directory not found: %s", workflows_dir)
        return store

    raw_dicts = load_all_yaml(workflows_dir)
    for raw in raw_dicts:
        wf_id = raw.get("id")
        if not wf_id:
            logger.warning("Skipping workflow YAML without 'id' field")
            continue
        if wf_id in store:
            logger.warning("Duplicate workflow id '%s'; keeping first", wf_id)
            continue
        store[wf_id] = raw
        logger.info("Loaded workflow '%s' into store", wf_id)

    return store


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app(config_dir: str = "config") -> FastAPI:
    """Create and configure the AgentWonder FastAPI application.

    Args:
        config_dir: Path to the configuration directory containing
            ``templates/``, ``tools/``, ``prompts/``, ``policies/``,
            and ``workflows/`` subdirectories.

    Returns:
        A fully configured FastAPI app instance.
    """
    config_path = Path(config_dir).resolve()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        """Startup: load registries and stores. Shutdown: cleanup."""
        logger.info("Starting AgentWonder API (config_dir=%s)", config_path)

        # Load registries
        registries = _load_registries(config_path)
        application.state.template_registry = registries["template_registry"]
        application.state.tool_registry = registries["tool_registry"]
        application.state.prompt_registry = registries["prompt_registry"]
        application.state.policy_registry = registries["policy_registry"]

        # Load workflows
        application.state.workflow_store = _load_workflows(config_path)

        # In-memory run and trace stores
        application.state.run_store: dict[str, RunStatus] = {}
        application.state.trace_store: dict[str, list[TraceEvent]] = {}

        # Shared executor and trace collector
        application.state.trace_collector = TraceCollector()
        application.state.executor = WorkflowExecutor()

        logger.info("AgentWonder API ready")
        yield
        logger.info("Shutting down AgentWonder API")

    application = FastAPI(
        title="AgentWonder API",
        description="Governed agentic workflow platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Mount routers
    application.include_router(health_router, prefix=API_PREFIX)
    application.include_router(runs_router, prefix=API_PREFIX)
    application.include_router(templates_router, prefix=API_PREFIX)
    application.include_router(tools_router, prefix=API_PREFIX)

    return application


# Default app instance for ``uvicorn agentwonder.main:app``
app = create_app()
