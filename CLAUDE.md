# CLAUDE.md

## Mission
Build **v1 of an internal Agentic Workflow Platform** using **Google ADK as the primary runtime**. The platform is **YAML-first**, **API-first**, and **template-governed**. It must follow a repository style similar to the user's `matching_engine` repo:
- simple top-level layout
- `config/` for YAML
- one clean Python package directory
- `tests/`
- `pyproject.toml`
- `requirements.txt`
- **Pydantic v2** as the schema contract layer

Do **not** use proprietary names such as `nerds_nlp`, `EDGE`, or similar in folder names, package names, classes, examples, or docs.

---

## Product framing

### What we are building
A governed platform that lets teams:
1. choose an approved workflow template
2. configure it with YAML
3. attach approved tools
4. define prompts, policies, and model settings
5. run through standard APIs/CLI
6. trace, evaluate, approve, and publish versions safely

### What we are not building in v1
- no drag-and-drop UI
- no free-form graph builder for all users
- no all-17-pattern runtime surface
- no dual-runtime ADK + LangGraph orchestration core
- no open plugin marketplace

---

## Platform principles

1. **ADK-first runtime**
   - Use Google ADK as the execution runtime.
   - Prefer deterministic workflow agents for orchestration.
   - Use LLM reasoning only where it adds value.

2. **YAML-first authoring**
   - YAML is the authoring layer for v1.
   - YAML must be validated into Pydantic models before use.
   - Never execute raw YAML directly.

3. **Pydantic as the contract layer**
   - Every config file maps to a Pydantic model.
   - Validation, defaults, normalization, and cross-reference checks live here.
   - Runtime code should consume typed models, not untyped dicts.

4. **Template-driven design**
   - Start with 5 templates:
     - `single_agent_with_tools`
     - `router_specialists`
     - `sequential_with_approval`
     - `parallel_fanout_aggregate`
     - `evaluator_loop`

5. **Native tools first; MCP-compatible by design**
   - Wrap REST/OpenAPI services as platform tools in v1.
   - Keep tool metadata structured so stable tools can later be exposed through MCP.

6. **Governance from day 1**
   - version every workflow
   - register every tool
   - trace every run
   - gate side effects with approvals
   - support promotion across environments

---

## Required v1 deliverables

### 1) Runtime service
A Python service that:
- loads workflow YAML from `config/`
- validates YAML into Pydantic models
- resolves tool/prompt/policy references
- compiles typed configs into ADK runtime objects
- executes runs
- persists run/session/state metadata
- exposes REST APIs and CLI hooks

### 2) Template registry
A local registry of approved workflow templates.
Each template defines:
- required YAML sections
- supported step types
- allowed transitions
- approval expectations
- supported model classes
- validation constraints

### 3) Tool registry
A registry for tool definitions with metadata:
- tool id and version
- owning team
- endpoint or OpenAPI source
- auth type
- timeout and retry policy
- idempotency
- side effect level
- allowed environments
- request/response schema references

### 4) Approval framework
Support explicit approvals for side-effecting actions such as:
- create/update/delete operations
- ticket creation
- downstream system mutations
- release or settlement actions

### 5) Observability and eval layer
Capture:
- run id
- template id + version
- model + prompt version
- tool invocation history
- timings and status
- approval path
- evaluation outcomes

---

## Required repository structure

Use this structure. Keep it close to `matching_engine` simplicity.

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
│   │   ├── common.py
│   │   ├── workflow.py
│   │   ├── template.py
│   │   ├── tool.py
│   │   ├── policy.py
│   │   ├── prompt.py
│   │   └── run.py
│   ├── compiler/
│   │   ├── loader.py
│   │   ├── resolver.py
│   │   ├── validators.py
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

## YAML to runtime flow

```text
+------------------+
| YAML in config/  |
+--------+---------+
         |
         v
+------------------+
| Pydantic models  |
| validate + clean |
+--------+---------+
         |
         v
+------------------+
| Canonical config |
+--------+---------+
         |
         v
+------------------+
| ADK compilation  |
+--------+---------+
         |
         v
+------------------+
| Run execution    |
+------------------+
```

### Rule
Never pass raw YAML dicts deep into the runtime.
Convert YAML to Pydantic models at the boundary.

---

## Pydantic expectations

Use **Pydantic v2**.

### Required schema categories
- `WorkflowConfig`
- `TemplateConfig`
- `ToolConfig`
- `PolicyConfig`
- `PromptConfig`
- `RunRequest`
- `RunStatus`
- `ApprovalRequest`
- `TraceEvent`

### Validation expectations
- enforce ids, versions, and enums
- validate cross-file references
- reject unsupported step types for a template
- reject write tools without approval configuration
- normalize defaults centrally
- keep schemas serializable and testable

---

## Coding instructions for Claude Code

### General
- Use Python 3.11+
- Use Pydantic v2
- Use FastAPI for APIs
- Use pytest for tests
- Keep modules small and explicit
- Prefer composition over inheritance

### Implementation order
1. create schema models
2. create YAML loader and parser
3. create registry loaders for `config/`
4. create template validator
5. create compiler from typed config to runtime plan
6. create ADK runtime executor
7. add approval handling
8. add tracing/eval hooks
9. add API routes
10. add tests

### Non-goals
- do not create a visual builder
- do not introduce proprietary names
- do not build a generalized autonomous agent framework
- do not rely on hidden magic or dynamic imports everywhere

---

## Required templates for v1

### 1. single_agent_with_tools
```text
+---------------------------+
| Agent                     |
| instruction + tools       |
+-------------+-------------+
              |
              v
     +--------+--------+
     | Registered Tools |
     +------------------+
```

### 2. router_specialists
```text
+-------------------+
| Router Agent      |
+----+----+----+----+
     |    |    |
     v    v    v
 +-----+ +-----+ +-----+
 | A   | | B   | | C   |
 +-----+ +-----+ +-----+
```

### 3. sequential_with_approval
```text
+---------+    +---------+    +-----------+    +---------+
| Step 1  | -> | Step 2  | -> | Approval  | -> | Step 3  |
+---------+    +---------+    +-----------+    +---------+
```

### 4. parallel_fanout_aggregate
```text
               +-------------+
               | Start Node  |
               +------+------+ 
                      |
        +-------------+-------------+
        |             |             |
        v             v             v
   +---------+   +---------+   +---------+
   | Branch1 |   | Branch2 |   | Branch3 |
   +----+----+   +----+----+   +----+----+
        \            |             /
         \           |            /
          +----------+-----------+
                     |
                     v
              +-------------+
              | Aggregator   |
              +-------------+
```

### 5. evaluator_loop
```text
+-----------+    +-------------+    +-----------+
| Generator | -> | Evaluator   | -> | Pass?     |
+-----+-----+    +------+------+
      ^                   |
      | no                | yes
      +-------------------+-----> final
```

---

## Output expectation
When you scaffold code, make it feel like a clean internal production starter repo, similar in clarity to `matching_engine`, but for agent workflows.
