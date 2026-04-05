"""AgentWonder CLI — command-line interface for workflow operations.

Usage::

    python -m agentwonder.cli run break_resolution_v1 --input break_id=BRK-42
    python -m agentwonder.cli validate config/workflows/break_resolution_v1.yaml
    python -m agentwonder.cli list templates
    python -m agentwonder.cli list tools
    python -m agentwonder.cli list workflows
    python -m agentwonder.cli trace <run_id>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from agentwonder.compiler.loader import load_yaml, load_all_yaml
from agentwonder.compiler.validators import (
    validate_workflow,
    cross_validate_workflow,
    ConfigValidationError,
)
from agentwonder.compiler.resolver import resolve_workflow, ResolutionError
from agentwonder.compiler.builder import build_plan, BuildError
from agentwonder.registry import TemplateRegistry, ToolRegistry, PromptRegistry, PolicyRegistry
from agentwonder.runtime.executor import WorkflowExecutor
from agentwonder.schemas.run import RunRequest

logger = logging.getLogger(__name__)


def _load_registries(config_dir: Path) -> dict:
    """Load all registries from config directory."""
    regs = {}
    for name, cls, subdir in [
        ("templates", TemplateRegistry, "templates"),
        ("tools", ToolRegistry, "tools"),
        ("prompts", PromptRegistry, "prompts"),
        ("policies", PolicyRegistry, "policies"),
    ]:
        reg = cls()
        path = config_dir / subdir
        if path.is_dir():
            reg.load_from_directory(path)
        regs[name] = reg
    return regs


def _registry_dicts(regs: dict) -> tuple[dict, dict, dict, dict]:
    """Convert registries to lookup dicts."""
    return (
        {t.id: t for t in regs["tools"].list_all()},
        {t.id: t for t in regs["templates"].list_all()},
        {t.id: t for t in regs["prompts"].list_all()},
        {t.id: t for t in regs["policies"].list_all()},
    )


def cmd_run(args: argparse.Namespace) -> int:
    """Execute a workflow by ID."""
    config_dir = Path(args.config_dir)
    regs = _load_registries(config_dir)
    tools_d, templates_d, prompts_d, policies_d = _registry_dicts(regs)

    # Load workflow
    workflows_dir = config_dir / "workflows"
    raw_workflows = {}
    if workflows_dir.is_dir():
        for raw in load_all_yaml(workflows_dir):
            wf_id = raw.get("id")
            if wf_id:
                raw_workflows[wf_id] = raw

    raw = raw_workflows.get(args.workflow_id)
    if raw is None:
        print(f"Error: workflow '{args.workflow_id}' not found", file=sys.stderr)
        return 1

    try:
        wf = validate_workflow(raw)
        errors = cross_validate_workflow(wf, tools_d, templates_d, policies_d, prompts_d)
        if errors:
            print("Cross-validation errors:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
            return 1

        resolved = resolve_workflow(wf, tools_d, templates_d, prompts_d, policies_d)
        plan = build_plan(resolved)
    except (ConfigValidationError, ResolutionError, BuildError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    # Parse inputs
    inputs = {}
    for item in args.input or []:
        key, _, value = item.partition("=")
        inputs[key] = value

    request = RunRequest(
        workflow_id=args.workflow_id,
        inputs=inputs,
        environment=args.env,
    )

    executor = WorkflowExecutor()
    status = asyncio.run(executor.execute(request, plan))

    print(json.dumps(status.model_dump(mode="json"), indent=2, default=str))
    return 0 if status.state.value == "completed" else 1


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a workflow YAML file."""
    config_dir = Path(args.config_dir)
    regs = _load_registries(config_dir)
    tools_d, templates_d, prompts_d, policies_d = _registry_dicts(regs)

    try:
        raw = load_yaml(Path(args.path))
        wf = validate_workflow(raw)
    except (Exception,) as exc:
        print(f"Schema validation failed: {exc}", file=sys.stderr)
        return 1

    errors = cross_validate_workflow(wf, tools_d, templates_d, policies_d, prompts_d)
    if errors:
        print("Cross-validation errors:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"Valid: {wf.id} v{wf.version} (template={wf.template}, {len(wf.steps)} steps)")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    """List registered resources."""
    config_dir = Path(args.config_dir)
    regs = _load_registries(config_dir)
    resource = args.resource

    if resource == "templates":
        for t in regs["templates"].list_all():
            print(f"  {t.id:40s} v{t.version}")
    elif resource == "tools":
        for t in regs["tools"].list_all():
            print(f"  {t.id:40s} v{t.version}  [{t.side_effect_level.value}]")
    elif resource == "prompts":
        for p in regs["prompts"].list_all():
            print(f"  {p.id:40s} v{p.version}")
    elif resource == "policies":
        for p in regs["policies"].list_all():
            print(f"  {p.id:40s} v{p.version}")
    elif resource == "workflows":
        wf_dir = config_dir / "workflows"
        if wf_dir.is_dir():
            for raw in load_all_yaml(wf_dir):
                wf_id = raw.get("id", "?")
                wf_ver = raw.get("version", "?")
                wf_tmpl = raw.get("template", "?")
                print(f"  {wf_id:40s} v{wf_ver}  template={wf_tmpl}")
    else:
        print(f"Unknown resource: {resource}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="agentwonder",
        description="AgentWonder CLI — workflow operations",
    )
    parser.add_argument(
        "--config-dir", default="config",
        help="Path to config directory (default: config)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging",
    )

    sub = parser.add_subparsers(dest="command")

    # run
    run_p = sub.add_parser("run", help="Execute a workflow")
    run_p.add_argument("workflow_id", help="Workflow ID to execute")
    run_p.add_argument("--input", "-i", action="append", help="Input key=value pairs")
    run_p.add_argument("--env", default="dev", help="Target environment (default: dev)")

    # validate
    val_p = sub.add_parser("validate", help="Validate a workflow YAML file")
    val_p.add_argument("path", help="Path to workflow YAML file")

    # list
    list_p = sub.add_parser("list", help="List registered resources")
    list_p.add_argument(
        "resource",
        choices=["templates", "tools", "prompts", "policies", "workflows"],
        help="Resource type to list",
    )

    args = parser.parse_args(argv)

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    if args.command == "run":
        return cmd_run(args)
    elif args.command == "validate":
        return cmd_validate(args)
    elif args.command == "list":
        return cmd_list(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
