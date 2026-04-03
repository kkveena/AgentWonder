# AgentWonder — Phase 1 Confluence Page

## Overview
AgentWonder is a YAML-first internal platform for building, validating, and running governed agentic workflows.

Phase 1 focuses on a practical and controlled foundation:
- configuration-driven workflow authoring
- Pydantic-based schema validation
- Google ADK as the runtime layer
- approved templates instead of free-form graph design
- REST/OpenAPI-backed tool integration
- approval gates for side-effecting actions
- tracing and evaluation hooks from day 1

The goal of Phase 1 is not to build a full no-code studio. The goal is to create a clean platform foundation that developers and product managers can use safely, quickly, and consistently.

---

## Why We Are Building This
Multiple teams want to experiment with agentic workflows, but direct adoption usually creates the same problems:
- inconsistent workflow design
- weak governance around tools and actions
- limited traceability
- poor reusability across teams
- difficulty moving from prototype to production

AgentWonder addresses this by standardizing how workflows are defined, validated, compiled, executed, and observed.

---

## Phase 1 Objectives
### Primary objectives
- provide a standard way to define workflows in YAML
- validate all configuration through typed Pydantic models
- compile approved configurations into executable runtime plans
- execute workflows through a controlled runtime service
- support tool invocation through reusable wrappers
- enforce approval steps for write or side-effecting actions
- capture traces, events, and execution status

### What success looks like
- teams can define workflows without writing custom orchestration logic each time
- platform can reject invalid or unsafe YAML before runtime
- each workflow run is traceable and inspectable
- side effects are controlled through policy and approval
- the codebase is modular enough to support future UI, MCP, and A2A extensions

---

## Scope of Phase 1
### In scope
- YAML-first workflow authoring in `config/`
- Pydantic v2 schema models for all config types
- template registry
- tool registry
- prompt registry
- policy registry
- compiler layer for validation, resolution, and runtime plan construction
- runtime executor
- approval handling
- observability scaffolding
- FastAPI endpoints for health, templates, tools, and runs
- test coverage for schema, compiler, template, and runtime flows

### Out of scope
- drag-and-drop UI
- free-form graph builder for all users
- all 17 conceptual patterns as first-class runtime objects
- dual-runtime orchestration
- external plugin marketplace
- broad A2A federation

---

## Guiding Principles
### 1. YAML-first authoring
Phase 1 uses YAML as the authoring experience so teams can move quickly without waiting for a full UI.

### 2. Pydantic as the contract layer
Every YAML file is parsed into a typed model before it is used. This keeps validation explicit and prevents raw configuration from driving execution directly.

### 3. ADK-first runtime
Google ADK is the runtime layer for workflow execution. Orchestration is deterministic where possible, with optional model-based reasoning where it adds value.

### 4. Template-governed design
Instead of exposing arbitrary graph design, the platform starts with approved templates that are easier to validate, operate, and govern.

### 5. Governance from day 1
Every workflow is versioned, every tool is registered, side effects are gated, and every run is traceable.

---

## Target Users
### Product Managers
- choose an approved workflow template
- configure workflow intent and structure in YAML
- review steps, policies, and expected outputs

### Developers
- implement tool wrappers
- extend schemas and compiler logic
- add runtime handlers and validations
- operate and troubleshoot workflow execution

### Platform Team
- manage templates
- govern shared tools and policies
- maintain runtime, observability, and promotion standards

---

## Phase 1 Architecture Summary
```text
+--------------------------------------------------------------+
|                         AgentWonder                          |
+--------------------------------------------------------------+
| config/ -> YAML authoring                                    |
|   templates / workflows / tools / policies / prompts         |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                    Pydantic Contract Layer                   |
|              typed validation, defaults, normalization       |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                     Compiler and Resolver                    |
|      reference checks, template resolution, runtime plan     |
+-----------------------------+--------------------------------+
                              |
                              v
+--------------------------------------------------------------+
|                        Runtime Executor                      |
|         execution, state, sessions, approvals, outputs       |
+----------------+--------------------------+------------------+
                 |                          |
                 v                          v
        +------------------+       +---------------------+
        | Tool Wrappers    |       | Approval Controls   |
        | REST / OpenAPI   |       | pause / resume      |
        +---------+--------+       +----------+----------+
                  \                         /
                   \                       /
                    v                     v
                 +--------------------------------+
                 | Observability and Eval Hooks   |
                 | traces, events, status, timing |
                 +--------------------------------+
```

---

## Repository Structure
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

This structure keeps the platform simple:
- `config/` is the authoring layer
- `agentwonder/` is the runtime and platform implementation
- `tests/` validates behavior across schemas, compiler, and runtime paths

---

## Configuration Model
Phase 1 separates configuration into clear YAML types.

### Templates
Define approved workflow patterns and structural expectations.

### Workflows
Define actual workflow implementations using approved templates.

### Tools
Define operational metadata for REST/OpenAPI-backed integrations.

### Policies
Define approval and execution controls.

### Prompts
Define reusable prompt or instruction references where applicable.

### Core rule
The execution flow is always:

`YAML -> Pydantic model -> reference resolution -> runtime plan -> execution`

Raw YAML is never executed directly.

---

## Core Platform Components
### 1. Schemas
Pydantic models define the contract for:
- workflows
- templates
- tools
- policies
- prompts
- run requests and run status

### 2. Registries
Registries load and expose approved configuration objects from `config/`.

### 3. Compiler
The compiler is responsible for:
- loading YAML
- validating structure
- validating cross-references
- resolving tools, prompts, templates, and policies
- building a canonical runtime plan

### 4. Runtime Executor
The executor runs the compiled workflow plan and manages:
- step execution
- workflow status
- run state
- approval pauses
- final outputs

### 5. Tool Layer
The tool layer standardizes integration with internal services through:
- REST wrappers
- OpenAPI-backed wrappers
- authentication helpers
- timeout and retry handling

### 6. Approval Layer
The approval layer prevents uncontrolled side effects by:
- checking policy before write actions
- creating approval requests
- pausing execution
- resuming or failing based on decision

### 7. Observability Layer
The observability layer captures:
- workflow events
- step traces
- tool calls
- errors
- timings
- evaluation hooks

---

## Runtime Lifecycle
```text
+-------------+     +-------------+     +-------------+     +-------------+
| Load YAML   | --> | Validate    | --> | Resolve and | --> | Build plan  |
| from config |     | with schema |     | cross-check |     | for runtime |
+------+------+     +------+------+     +------+------+     +------+------+ 
       |                    |                    |                    |
       +--------------------+--------------------+--------------------+
                                                                    |
                                                                    v
                                                           +----------------+
                                                           | Execute run    |
                                                           +--------+-------+
                                                                    |
                                     +------------------------------+-----------------------------+
                                     |                                                            |
                                     v                                                            v
                            +------------------+                                         +------------------+
                            | Tool invocation  |                                         | Approval check   |
                            +--------+---------+                                         +--------+---------+
                                     |                                                            |
                                     v                                                            v
                            +------------------+                                         +------------------+
                            | Tool result      |                                         | Pause / decision |
                            +--------+---------+                                         +--------+---------+
                                     +------------------------------+-----------------------------+
                                                                    |
                                                                    v
                                                           +----------------+
                                                           | Trace + output |
                                                           +----------------+
```

---

## API Surface in Phase 1
The platform already exposes a simple API foundation.

### Health
- `GET /api/v1/health`

### Templates
- `GET /api/v1/templates`
- `GET /api/v1/templates/{id}`

### Tools
- `GET /api/v1/tools`
- `GET /api/v1/tools/{id}`

### Runs
- `POST /api/v1/runs`
- `GET /api/v1/runs/{id}`
- `GET /api/v1/runs/{id}/trace`

This is enough for initial integration, testing, and future UI enablement.

---

## Current Phase 1 Value
Phase 1 gives the team a real platform foundation rather than a slideware concept.

### Immediate value
- standard workflow definition model
- consistent schema validation
- reusable tool registration pattern
- safer execution path for agentic workflows
- support for approvals and traceability
- clear path to grow into UI and interoperability later

### Technical value
- modular Python package structure
- explicit contracts through Pydantic
- API-first runtime service
- clear separation of config, runtime, and governance concerns

---

## Controls and Governance
Phase 1 intentionally introduces governance early.

### Built-in controls
- approved templates only
- registered tools only
- typed config validation
- approval gate for side effects
- explicit runtime plan generation
- traceable run history

### Why this matters
This reduces the risk of uncontrolled automation and gives teams a safer path from development to production.

---

## Testing and Validation
The codebase includes tests across the main platform layers.

### Coverage areas
- schema validation
- compiler behavior
- template checks
- runtime execution path

This is important because the platform must prove that configuration errors are caught early and runtime behavior remains predictable.

---

## Known Phase 1 Limitations
Phase 1 is intentionally narrow.

### Current limitations
- no visual workflow designer
- limited pattern surface compared with long-term target state
- no broad external agent federation
- no generalized marketplace for tools or templates
- minimal end-user experience beyond YAML and APIs

These are acceptable trade-offs for the first implementation because the objective is platform correctness and adoption, not UI breadth.

---

## Recommended Next Steps
### Near-term
- stabilize the current runtime and schema contracts
- expand test coverage and sample workflows
- add stronger evaluation reporting
- improve approval lifecycle handling
- strengthen tool registration and operational metadata

### Phase 1.1 / later
- richer CLI and admin APIs
- limited UI for workflow browsing and validation
- stronger model routing support
- optional MCP alignment for stable tools
- selective A2A integration where there is a real remote-agent boundary

---

## Summary
AgentWonder Phase 1 establishes a governed base for internal agentic workflow development.

It does this by combining:
- YAML-first authoring
- Pydantic-backed contracts
- ADK-based runtime execution
- reusable tool wrappers
- approvals for side effects
- tracing and evaluation hooks

This gives the team a practical foundation to standardize workflow development now, while keeping the architecture flexible for future UI, interoperability, and broader platform capabilities.
