# yaml_usage.md

# YAML Usage Guide for AgentWonder V1

This document explains how to use YAML files in v1.

V1 does **not** provide a full UI. Workflows, tools, policies, and prompts are defined in `config/` as YAML files. These YAML files are then parsed into **Pydantic v2 models** before compilation and execution.

---

## 1. Core rule

```text
+-------------------+
| Human-authored    |
| YAML in config/   |
+---------+---------+
          |
          v
+-------------------+
| Pydantic parsing  |
| validation        |
+---------+---------+
          |
          v
+-------------------+
| Canonical config  |
+---------+---------+
          |
          v
+-------------------+
| ADK runtime       |
+-------------------+
```

YAML is never executed directly.
It is always:
1. loaded
2. parsed into Pydantic
3. validated
4. normalized
5. compiled
6. executed

---

## 2. File layout

```text
config/
├── templates/   # platform-owned approved templates
├── workflows/   # team-authored workflow definitions
├── tools/       # tool registry entries
├── policies/    # approval and execution policies
└── prompts/     # versioned prompts/instructions
```

### Recommended ownership
- `templates/` -> platform team
- `tools/` -> platform team + service-owning team
- `workflows/` -> application team / PM + dev
- `policies/` -> platform + governance
- `prompts/` -> application team + platform review

---

## 3. How YAML maps to Pydantic

Suggested model mapping:

```text
config/workflows/*.yaml  -> WorkflowConfig
config/tools/*.yaml      -> ToolConfig
config/policies/*.yaml   -> PolicyConfig
config/prompts/*.yaml    -> PromptConfig
config/templates/*.yaml  -> TemplateConfig
```

The compiler should never work on raw dictionaries after this stage.

---

## 4. Workflow YAML

A workflow YAML answers five questions:
1. which template is used?
2. which model(s) are used?
3. which tools are allowed?
4. what are the steps?
5. where are approval/eval hooks?

### Example: `config/workflows/break_resolution_v1.yaml`

```yaml
id: break_resolution_v1
name: Break Resolution Workflow
version: 1.0.0
owner_team: markets_ops_ai

template: sequential_with_approval

description: >
  Resolve an operations break by gathering context,
  proposing action, pausing for checker approval,
  and then posting the final update.

models:
  default: gemini-2.5-flash
  evaluator: gemini-2.5-pro

tool_refs:
  - fetch_break_details
  - fetch_trade_context
  - suggest_resolution
  - post_resolution_update

inputs:
  required:
    - break_id
    - source_system

steps:
  - id: enrich_break
    type: tool_call
    tool: fetch_break_details

  - id: enrich_trade_context
    type: tool_call
    tool: fetch_trade_context
    depends_on:
      - enrich_break

  - id: propose_resolution
    type: llm_agent
    prompt_ref: propose_resolution_prompt
    tools:
      - suggest_resolution
    depends_on:
      - enrich_trade_context

  - id: checker_approval
    type: approval
    approval_ref: checker_signoff
    depends_on:
      - propose_resolution

  - id: update_downstream
    type: tool_call
    tool: post_resolution_update
    depends_on:
      - checker_approval

output:
  format: json
  schema_ref: break_resolution_output

evals:
  suite: break_resolution_smoke
```

### Validation expectations
- `template` must exist in `config/templates/`
- every `tool` reference must exist in `config/tools/`
- every `prompt_ref` must exist in `config/prompts/`
- every `approval_ref` must exist in `config/policies/`
- step types must be allowed by the selected template
- write/delete tools must have approval configured

---

## 5. Tool YAML

Tool YAML registers a tool and its operational metadata.

### Example: `config/tools/fetch_break_details.yaml`

```yaml
id: fetch_break_details
name: Fetch Break Details
version: 1.0.0
owner_team: markets_ops_services

type: rest
method: POST
endpoint: https://internal-api.example.com/breaks/details

auth:
  type: bearer_env
  token_env_var: BREAK_API_TOKEN

timeout_seconds: 15
retry_policy:
  max_retries: 2
  backoff_seconds: 1

idempotent: true
approval_required: false
side_effect_level: read
allowed_environments:
  - dev
  - test
  - prod

request_schema:
  type: object
  properties:
    break_id:
      type: string
    source_system:
      type: string
  required:
    - break_id
    - source_system

response_schema:
  type: object
  properties:
    break_id:
      type: string
    status:
      type: string
    details:
      type: object
```

### Minimum tool fields
```text
id
name
version
owner_team
type
endpoint or openapi source
auth
timeout_seconds
retry_policy
idempotent
side_effect_level
allowed_environments
```

---

## 6. Policy YAML

Policies define approval and governance behavior.

### Example: `config/policies/checker_signoff.yaml`

```yaml
id: checker_signoff
name: Checker Signoff
version: 1.0.0

applies_to:
  - side_effect_level: write

approval:
  required: true
  approver_roles:
    - operations_checker
  timeout_minutes: 30
  on_reject: fail_run
```

### Typical policy checks
- does this step need approval?
- who can approve it?
- what happens on reject?
- what happens on timeout?

---

## 7. Prompt YAML

Prompts should be versioned so runs can be traced back to exact instructions.

### Example: `config/prompts/propose_resolution_prompt.yaml`

```yaml
id: propose_resolution_prompt
version: 1.0.0
purpose: Generate candidate resolution for an operations break
text: |
  You are an operations resolution assistant.
  Use the provided break context and trade context.
  Propose a resolution with rationale, confidence, and risk notes.
```

---

## 8. Template YAML

Templates are platform-owned constraints, not app-specific workflows.

### Example structure

```yaml
id: sequential_with_approval
version: 1.0.0
allowed_step_types:
  - tool_call
  - llm_agent
  - approval
  - evaluator
requires_explicit_order: true
supports_parallel: false
```

Templates should be strict. They define what a workflow is allowed to do.

---

## 9. Authoring checklist

```text
+---------------------------------------------------+
| YAML authoring checklist                          |
+---------------------------------------------------+
| choose an approved template                       |
| register every tool before using it               |
| version prompts and policies                      |
| keep workflow ids unique                          |
| add approval for side-effecting actions           |
| validate before compile                           |
+---------------------------------------------------+
```

---

## 10. Recommended validation pipeline

```text
+----------------+
| Load YAML      |
+-------+--------+
        |
        v
+----------------+
| Pydantic model |
+-------+--------+
        |
        v
+----------------+
| Cross-ref      |
| validation     |
+-------+--------+
        |
        v
+----------------+
| Template rules |
+-------+--------+
        |
        v
+----------------+
| Build runtime  |
| plan           |
+----------------+
```

---

## 11. Common mistakes to avoid

- using raw YAML dicts deep in the runtime
- hardcoding tools in code instead of registry YAML
- letting workflow YAML bypass template validation
- letting write tools run without approval checks
- mixing app-specific logic into template definitions

---

## 12. Summary

In v1, YAML is the external configuration layer and **Pydantic is the typed contract layer**. That is the key difference between a quick prototype and a maintainable platform.
