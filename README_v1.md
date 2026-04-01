# README_v1.md

# Agentic Workflow Platform V1

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

This repository follows a simple layout style similar to the user's `matching_engine` repo:
- `config/` contains YAML
- one clean Python package contains runtime code
- `tests/` holds unit and integration tests
- no proprietary package names

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
|                  AGENTIC WORKFLOW PLATFORM V1                |
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
agentic_platform_v1/
├── config/
│   ├── templates/
│   ├── workflows/
│   ├── tools/
│   ├── policies/
│   └── prompts/
├── agentic_platform/
│   ├── schemas/
│   ├── compiler/
│   ├── runtime/
│   ├── registry/
│   ├── tools/
│   ├── observability/
│   ├── api/
│   └── main.py
├── tests/
├── README_v1.md
├── architecture_layout.md
├── yaml_usage.md
├── pyproject.toml
└── requirements.txt
```

This structure intentionally mirrors the simplicity of `matching_engine`, but avoids names like `nerds_nlp` and `EDGE`.

---

## 5. Core design choices

### ADK as the runtime
Google ADK is the execution runtime for workflow agents, multi-agent composition, tools, sessions, and future interoperability.

### Pydantic as the contract layer
Every YAML file is parsed into a Pydantic model before use.
The runtime should consume typed objects, not loose dictionaries.

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

## 6. High-level architecture

```text
+--------------------+     +----------------------+     +------------------+
| config/workflows   | --> | Pydantic validation  | --> | Template checks  |
+--------------------+     +----------+-----------+     +---------+--------+
                                      |                           |
                                      v                           v
                            +-------------------+       +-------------------+
                            | Canonical config  | ----> | ADK runtime plan  |
                            +---------+---------+       +---------+---------+
                                      |                           |
                                      v                           v
                             +------------------+       +-------------------+
                             | Tool wrappers     |       | Run execution      |
                             | approvals/policy  |       | traces/evals       |
                             +------------------+       +-------------------+
```

---

## 7. Major modules

### `agentic_platform/schemas/`
Pydantic models for all config and runtime contracts.

Suggested files:
- `common.py`
- `workflow.py`
- `template.py`
- `tool.py`
- `policy.py`
- `prompt.py`
- `run.py`

### `agentic_platform/compiler/`
Loads YAML, validates references, resolves registries, and builds the runtime plan.

### `agentic_platform/runtime/`
Executes compiled workflows, manages sessions/state, and handles approvals.

### `agentic_platform/registry/`
Loads template, tool, prompt, and policy definitions from `config/`.

### `agentic_platform/tools/`
Contains reusable wrappers for REST/OpenAPI-backed tools.

### `agentic_platform/observability/`
Captures traces, events, metrics, and evaluation results.

### `agentic_platform/api/`
FastAPI routes for validation, runs, approvals, templates, and tools.

---

## 8. YAML-to-runtime contract

```text
+------------------+
| YAML in config/  |
+--------+---------+
         |
         v
+------------------+
| Pydantic models  |
+--------+---------+
         |
         v
+------------------+
| Canonical config |
+--------+---------+
         |
         v
+------------------+
| ADK objects      |
+--------+---------+
         |
         v
+------------------+
| Runtime execution|
+------------------+
```

Never execute raw YAML directly.

---

## 9. Example usage flow

```text
1. add tool YAML in config/tools/
2. add policy YAML in config/policies/
3. add prompt YAML in config/prompts/
4. add workflow YAML in config/workflows/
5. validate configs
6. compile workflow
7. run workflow
8. inspect traces and approvals
```

---

## 10. Initial template set

### single_agent_with_tools
Best for one agent using approved tools.

### router_specialists
Best for routing work to specialist agents.

### sequential_with_approval
Best for stepwise workflows with human sign-off before side effects.

### parallel_fanout_aggregate
Best for parallel lookups and aggregation.

### evaluator_loop
Best for generation + critique/retry patterns.

---

## 11. Build order

1. implement Pydantic schemas
2. implement YAML loaders and registries
3. implement template validation
4. implement runtime-plan compiler
5. implement ADK executor
6. implement approval handling
7. implement tracing and eval hooks
8. implement API routes
9. add tests

---

## 12. Design rules

- no proprietary names in code or docs
- keep package names clean and generic
- keep the repo simple and readable
- prefer explicit schema validation over dynamic behavior
- keep v1 YAML-first; do not build a large UI yet
