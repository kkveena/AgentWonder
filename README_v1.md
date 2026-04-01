# AgentWonder v1

A YAML-first internal platform for building, validating, and running **governed agentic workflows** using **Google ADK** as the runtime and **Pydantic v2** as the schema contract layer.

---

## 1. Why this exists

Teams want agentic workflows, but v1 must optimize for:
- fast internal development
- predictable governance
- reusable workflow templates
- safe tool invocation
- approvals for side effects
- traceability and evaluation

---

## 2. V1 scope

### Included
- ADK-based runtime service
- YAML-first workflow configuration under `config/`
- Pydantic schema validation for all YAML
- 5 approved workflow templates
- REST/OpenAPI-backed tool wrappers
- approval gates for side-effecting actions
- tracing, run history, and evaluation hooks
- versioned workflows and registries

### Excluded
- full visual builder UI
- arbitrary graph authoring by end users
- all 17 patterns as native runtime objects
- dual-runtime orchestration
- open external plugin marketplace

---

## 3. V1 mental model

```text
+--------------------------------------------------------------+
|                      AGENTWONDER V1                          |
+--------------------------------------------------------------+
| YAML in config/  ->  Pydantic models  ->  ADK runtime plan   |
+--------------------------------------------------------------+
| Templates | Tools | Policies | Prompts | Approvals | Traces  |
+--------------------------------------------------------------+
```

The user experience in v1 is:
1. define YAML in `config/`
2. validate YAML into typed models
3. compile to runtime objects
4. execute workflow
5. inspect traces, outputs, and approvals

---

## 4. Repository layout

```text
AgentWonder/
├── config/
│   ├── templates/
│   ├── workflows/
│   ├── tools/
│   ├── policies/
│   └── prompts/
├── agentwonder/
│   ├── schemas/
│   │   ├── common.py
│   │   ├── workflow.py
│   │   ├── template.py
│   │   ├── tool.py
│   │   ├── policy.py
│   │   ├── prompt.py
│   │   └── run.py
│   ├── compiler/
│   │   ├── loader.py
│   │   ├── validators.py
│   │   ├── resolver.py
│   │   └── builder.py
│   ├── runtime/
│   │   ├── executor.py
│   │   ├── session_store.py
│   │   ├── state_store.py
│   │   ├── approvals.py
│   │   └── model_router.py
│   ├── registry/
│   │   ├── templates.py
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   └── policies.py
│   ├── tools/
│   │   ├── rest_wrapper.py
│   │   ├── openapi_wrapper.py
│   │   └── auth.py
│   ├── observability/
│   │   ├── tracing.py
│   │   ├── events.py
│   │   └── evals.py
│   ├── api/
│   │   ├── routes_runs.py
│   │   ├── routes_templates.py
│   │   ├── routes_tools.py
│   │   └── routes_health.py
│   └── main.py
├── tests/
│   ├── conftest.py
│   ├── test_schemas.py
│   ├── test_compiler.py
│   ├── test_runtime.py
│   └── test_templates.py
├── README_v1.md
├── architecture_layout.md
├── yaml_usage.md
├── pyproject.toml
└── requirements.txt
```

---

## 5. Quick start

```bash
# Install
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start API server
uvicorn agentwonder.main:app --reload

# API endpoints (under /api/v1)
GET  /api/v1/health
GET  /api/v1/templates
GET  /api/v1/templates/{id}
GET  /api/v1/tools
GET  /api/v1/tools/{id}
POST /api/v1/runs
GET  /api/v1/runs/{id}
GET  /api/v1/runs/{id}/trace
```

---

## 6. Core design choices

### ADK as the runtime
Google ADK is the execution runtime for workflow agents, multi-agent composition, tools, sessions, and future interoperability.

### Pydantic as the contract layer
Every YAML file is parsed into a Pydantic model before use.
The runtime consumes typed objects, not loose dictionaries.

### YAML as the authoring layer
V1 does not include a full UI. Instead:
- platform team manages templates
- developers register tools and policies
- PMs and developers define workflows in YAML

### Templates over free-form graphs
Templates keep platform usage safe and understandable.

Initial templates:
- `single_agent_with_tools`
- `router_specialists`
- `sequential_with_approval`
- `parallel_fanout_aggregate`
- `evaluator_loop`

---

## 7. Major modules

### `agentwonder/schemas/`
Pydantic models for all config and runtime contracts:
`common.py`, `workflow.py`, `template.py`, `tool.py`, `policy.py`, `prompt.py`, `run.py`

### `agentwonder/compiler/`
Loads YAML, validates references, resolves registries, and builds the runtime plan.

### `agentwonder/runtime/`
Executes compiled workflows, manages sessions/state, and handles approvals.

### `agentwonder/registry/`
Loads template, tool, prompt, and policy definitions from `config/`.

### `agentwonder/tools/`
Contains reusable wrappers for REST/OpenAPI-backed tools.

### `agentwonder/observability/`
Captures traces, events, metrics, and evaluation results.

### `agentwonder/api/`
FastAPI routes for runs, templates, tools, and health.

---

## 8. YAML-to-runtime flow

```text
YAML in config/  →  Pydantic models  →  Canonical config  →  RuntimePlan  →  Execution
```

Never execute raw YAML directly. Always validate through Pydantic first.

---

## 9. Example: end-to-end workflow execution

```python
from pathlib import Path
from agentwonder.compiler.loader import load_yaml
from agentwonder.compiler.validators import validate_workflow, cross_validate_workflow
from agentwonder.compiler.resolver import resolve_workflow
from agentwonder.compiler.builder import build_plan
from agentwonder.registry import TemplateRegistry, ToolRegistry, PromptRegistry, PolicyRegistry
from agentwonder.runtime.executor import WorkflowExecutor
from agentwonder.schemas.run import RunRequest

# Load registries
templates = TemplateRegistry()
templates.load_from_directory(Path("config/templates"))
tools = ToolRegistry()
tools.load_from_directory(Path("config/tools"))
prompts = PromptRegistry()
prompts.load_from_directory(Path("config/prompts"))
policies = PolicyRegistry()
policies.load_from_directory(Path("config/policies"))

# Build lookup dicts
tools_dict = {t.id: t for t in tools.list_all()}
templates_dict = {t.id: t for t in templates.list_all()}
prompts_dict = {t.id: t for t in prompts.list_all()}
policies_dict = {t.id: t for t in policies.list_all()}

# Load, validate, resolve, build
raw = load_yaml(Path("config/workflows/break_resolution_v1.yaml"))
wf = validate_workflow(raw)
errors = cross_validate_workflow(wf, tools_dict, templates_dict, policies_dict, prompts_dict)
assert not errors

resolved = resolve_workflow(wf, tools_dict, templates_dict, prompts_dict, policies_dict)
plan = build_plan(resolved)

# Execute
import asyncio
executor = WorkflowExecutor()
request = RunRequest(workflow_id="break_resolution_v1", inputs={"break_id": "BRK-001", "source_system": "test"})
status = asyncio.run(executor.execute(request, plan))
print(status.state)  # RunState.COMPLETED
```

---

## 10. Design rules

- no proprietary names in code or docs
- keep package names clean and generic
- prefer explicit schema validation over dynamic behavior
- keep v1 YAML-first; do not build a large UI yet
- every workflow is versioned, every tool is registered, every run is traced
