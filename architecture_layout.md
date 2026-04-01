# architecture_layout.md

# Architecture Layout for Agentic Workflow Platform V1

This document shows the v1 architecture using simple boxes and lines, aligned to a repository style similar to `matching_engine`, with `config/` as the YAML source and `agentic_platform/` as the main Python package.

---

## 1. Repository layout

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

---

## 2. End-to-end flow

```text
+------------------------+
| config/workflows/*.yaml|
+-----------+------------+
            |
            v
+------------------------+
| agentic_platform       |
| compiler.loader        |
+-----------+------------+
            |
            v
+------------------------+
| Pydantic schemas       |
| workflow/tool/policy   |
+-----------+------------+
            |
            v
+------------------------+
| compiler.resolver      |
| template/tool refs     |
+-----------+------------+
            |
            v
+------------------------+
| compiler.builder       |
| canonical runtime plan |
+-----------+------------+
            |
            v
+------------------------+
| runtime.executor       |
| ADK workflow execution |
+-----+----------+-------+
      |          |
      |          +----------------------+
      v                                 v
+-------------+                +------------------+
| tools layer |                | approvals layer  |
+------+------+                +---------+--------+
       |                                 |
       v                                 v
+--------------+                 +---------------+
| REST/OpenAPI |                 | pause/resume  |
| services     |                 | decision flow |
+------+-------+                 +-------+-------+
       |                                 |
       +---------------+-----------------+
                       |
                       v
              +-------------------+
              | observability      |
              | traces/evals/events|
              +-------------------+
```

---

## 3. Package-level layout

### 3.1 Schemas

```text
+---------------------------------------------------+
| agentic_platform/schemas/                         |
+---------------------------------------------------+
| common.py    -> shared enums/base metadata        |
| workflow.py  -> WorkflowConfig, StepConfig        |
| template.py  -> TemplateConfig                    |
| tool.py      -> ToolConfig                        |
| policy.py    -> PolicyConfig, ApprovalConfig      |
| prompt.py    -> PromptConfig                      |
| run.py       -> RunRequest, RunStatus, TraceEvent |
+---------------------------------------------------+
```

### 3.2 Compiler

```text
+---------------------------------------------------+
| agentic_platform/compiler/                        |
+---------------------------------------------------+
| loader.py      -> load YAML from config/          |
| validators.py  -> schema + cross-ref checks       |
| resolver.py    -> resolve tools/prompts/policies  |
| builder.py     -> build runtime plan for ADK      |
+---------------------------------------------------+
```

### 3.3 Runtime

```text
+---------------------------------------------------+
| agentic_platform/runtime/                         |
+---------------------------------------------------+
| executor.py      -> execute workflow runs         |
| session_store.py -> session persistence           |
| state_store.py   -> workflow state persistence    |
| approvals.py     -> approval pause/resume logic   |
| model_router.py  -> select model by step/template |
+---------------------------------------------------+
```

### 3.4 Registry

```text
+---------------------------------------------------+
| agentic_platform/registry/                        |
+---------------------------------------------------+
| templates.py -> load approved templates           |
| tools.py     -> load tool registry                |
| prompts.py   -> load prompts registry             |
| policies.py  -> load policy registry              |
+---------------------------------------------------+
```

### 3.5 Tool wrappers

```text
+---------------------------------------------------+
| agentic_platform/tools/                           |
+---------------------------------------------------+
| rest_wrapper.py    -> REST-backed tool adapter    |
| openapi_wrapper.py -> OpenAPI-backed tool adapter |
| auth.py            -> auth helpers                |
+---------------------------------------------------+
```

### 3.6 Observability

```text
+---------------------------------------------------+
| agentic_platform/observability/                   |
+---------------------------------------------------+
| tracing.py -> run/step/tool traces                |
| events.py  -> structured event emission           |
| evals.py   -> evaluation hooks/results            |
+---------------------------------------------------+
```

### 3.7 API

```text
+---------------------------------------------------+
| agentic_platform/api/                             |
+---------------------------------------------------+
| routes_runs.py      -> create and inspect runs    |
| routes_templates.py -> list templates             |
| routes_tools.py     -> list tools                 |
| routes_health.py    -> liveness/readiness         |
+---------------------------------------------------+
```

---

## 4. Runtime sequence

```text
+-----------+      +------------+      +-------------+      +-----------+
| Load YAML | ---> | Validate   | ---> | Compile to  | ---> | Execute   |
| from config|     | Pydantic   |      | runtime plan|      | with ADK  |
+-----+-----+      +------+-----+      +------+------+      +-----+-----+
      |                   |                   |                   |
      |                   |                   |                   v
      |                   |                   |          +-----------------+
      |                   |                   |          | Trace each step |
      |                   |                   |          +--------+--------+
      |                   |                   |                   |
      |                   |                   v                   v
      |                   |          +----------------+   +---------------+
      |                   |          | Resolve tool   |   | Approval gate |
      |                   |          | prompt policy  |   | if side effect|
      |                   |          +----------------+   +-------+-------+
      |                   |                                        |
      |                   +----------------------------------------+
      |                                                            |
      +------------------------------------------------------------+
```

---

## 5. Approval path

```text
+-------------------+
| Step wants write  |
+---------+---------+
          |
          v
+-------------------+
| Check policy YAML |
+---------+---------+
          |
          v
+-------------------+
| Create approval   |
| request           |
+---------+---------+
          |
          v
+-------------------+
| Pause run         |
+---------+---------+
          |
          v
+-------------------+
| Approver decision |
+----+---------+----+
     |         |
   yes         no
     |         |
     v         v
+---------+   +-----------+
| Resume  |   | Fail/stop |
+---------+   +-----------+
```

---

## 6. V1 boundaries

```text
+---------------------------------------------------+
| Included in V1                                    |
+---------------------------------------------------+
| YAML-first configuration                          |
| Pydantic contract layer                           |
| ADK runtime compilation                           |
| REST/OpenAPI tool wrappers                        |
| template registry                                 |
| approvals                                         |
| tracing/evals                                     |
+---------------------------------------------------+

+---------------------------------------------------+
| Deferred beyond V1                                |
+---------------------------------------------------+
| full drag-and-drop UI                             |
| all 17 patterns as runtime objects                |
| broad A2A federation                              |
| generalized marketplace                           |
+---------------------------------------------------+
```
