# CLAUDE.md

## Mission
Phase 1 is complete. AgentWonder already has a YAML-first, Pydantic-based, ADK-oriented platform skeleton with config registries, compiler modules, runtime modules, API routes, tests, and example workflows. The current root `CLAUDE.md` and `README_v1.md` are still written as **Phase 1 / v1 build instructions**.

Your job now is to implement **Phase 2: operational runtime hardening and first pilot-ready deployment**.

AgentWonder remains:
- **YAML-first** for authoring
- **Pydantic-first** for contracts and validation
- **API-first** for execution and operations
- **template-governed** for safety and consistency
- **lightweight UI** only; no full visual builder

Do **not** introduce proprietary names such as `nerds_nlp`, `nerds-nlp`, `EDGE`, or `edge` as complete words or in package names, module names, examples, docs, or comments.

---

## Phase 2 objective
Move AgentWonder from a strong Phase 1 scaffold into a platform that can run **one real governed workflow reliably** for an internal pilot team.

Phase 2 should optimize for:
1. durable execution
2. persisted state and approvals
3. safe real tool execution
4. controlled LLM-backed step execution where needed
5. persisted tracing and evaluation
6. stable operational APIs
7. versioning and release governance

The goal is **depth, not breadth**.
Do not expand into a large UI, all 17 patterns, or generalized autonomous-agent behavior.

---

## Product framing for Phase 2

### What we are building now
A pilot-ready governed runtime that lets teams:
1. register and validate tools, prompts, policies, templates, and workflows
2. submit runs through stable APIs
3. execute deterministic and selected LLM-backed steps
4. pause for approval when a policy requires it
5. resume safely after approval
6. inspect run history, traces, outputs, and failures
7. promote certified workflow versions across environments

### What we are not building in Phase 2
- no drag-and-drop UI
- no broad end-user graph builder
- no all-17-pattern runtime surface
- no marketplace or open plugin ecosystem
- no dual-runtime ADK + LangGraph core
- no autonomous memory-heavy agent framework
- no uncontrolled dynamic tool loading

---

## Current-state assumptions
Assume the repository already contains the Phase 1 baseline:
- top-level `config/`
- `agentwonder/` package
- schemas, compiler, runtime, registry, observability, tools, and API modules
- tests and notebook-based validation
- example workflow(s)

Do not rebuild Phase 1 from scratch.
Extend and harden what exists.

---

## Phase 2 workstreams

### 1) Durable execution and run lifecycle
Implement durable run management so workflows can survive process restarts and operator actions.

Required capabilities:
- persisted run record
- persisted step state
- persisted approval state
- restart-safe execution
- resumable runs
- retryable failed steps where safe
- explicit cancellation support
- terminal and non-terminal run states

Canonical run lifecycle:
```text
created
  -> validated
  -> planned
  -> running
  -> waiting_for_approval
  -> resumed
  -> completed
  -> failed
  -> cancelled
```

Rules:
- every run must have a durable `run_id`
- every step execution must be attributable to a run and step id
- state transitions must be explicit and auditable
- retries must not duplicate unsafe side effects

### 2) Approval persistence and control plane
Phase 1 introduced approval concepts. Phase 2 must make them operational.

Required capabilities:
- create approval requests for gated actions
- persist approval status and approver metadata
- support approve / reject / expire flows
- resume run after approval
- fail or cancel run after rejection or expiry
- capture approval audit trail

Approval records should include:
- approval id
- run id
- workflow id + version
- step id
- reason for approval
- requested action summary
- risk / side-effect classification
- request payload summary
- approver identity
- approval decision
- timestamps

### 3) Real tool execution with enterprise safety
Phase 2 must make REST/OpenAPI-backed tool execution real and safe.

Required capabilities:
- authenticated HTTP execution
- timeouts
- retries with guardrails
- idempotency-aware behavior
- request/response logging with redaction
- error normalization
- environment allowlisting
- side-effect classification
- approval enforcement before side-effecting calls

Every registered tool should support structured metadata such as:
- tool id
- version
- owner
- endpoint or OpenAPI source
- auth type
- timeout
- retry policy
- idempotent true/false
- side-effect level
- environments allowed
- optional request/response schema reference

### 4) LLM-backed step execution where needed
Phase 2 should support selected `llm_agent` or equivalent model-backed steps.

Rules:
- do not force an LLM into every workflow step
- deterministic steps stay deterministic
- only use an LLM where semantic reasoning adds value
- every model-backed step must be explicit in config
- model, prompt, temperature, and output contract must be traceable

Required capabilities:
- model selection by workflow default and step override
- prompt resolution with versioning
- structured output validation where applicable
- graceful error handling and fallback strategy
- capture model metadata in traces

Keep model integration modular so the platform can evolve without rewriting the runtime core.

### 5) Persisted observability and evaluation
Phase 2 must move observability beyond in-memory debugging.

Required capabilities:
- persisted trace events
- run timeline
- step-level status and timings
- tool invocation history
- approval history
- model invocation metadata
- error records
- evaluation result storage

Every run should be inspectable by:
- run id
- workflow id
- status
- time window
- environment

Evaluation should support:
- workflow-level regression tests
- prompt or model comparison hooks
- pass/fail results tied to workflow version
- human-readable summary of failures

### 6) Stable operational APIs
Phase 2 should finish the API surface required for real platform usage.

Minimum API surface:
- `POST /runs`
- `GET /runs/{id}`
- `GET /runs/{id}/trace`
- `POST /runs/{id}/resume`
- `POST /runs/{id}/cancel`
- `GET /approvals/{id}`
- `POST /approvals/{id}/approve`
- `POST /approvals/{id}/reject`
- `GET /templates`
- `GET /tools`
- `GET /health`

Design goals:
- typed request/response models
- consistent error contracts
- predictable status codes
- no hidden side effects in read endpoints

### 7) Versioning and promotion governance
Phase 2 should operationalize release discipline.

Required capabilities:
- versioned workflows, prompts, tools, and policies
- validation before publish
- environment-aware promotion rules
- draft vs published status
- compatibility checks where practical
- rollback to prior known-good versions

Keep this lightweight but real.
No large enterprise control-plane UI is needed yet.

---

## Phase 2 architecture guidance
Keep the same high-level architecture, but harden the execution path.

```text
+-------------------------------------------------------------------+
|                          AGENTWONDER PHASE 2                      |
+-------------------------------------------------------------------+
| YAML config -> Pydantic models -> Resolved config -> Runtime plan |
+-------------------------------------------------------------------+
| Registries | Compiler | Runtime | Approvals | Tools | Tracing     |
+-------------------------------------------------------------------+
| API layer -> Run service -> Executor -> Tool/Model adapters       |
|                         |                                         |
|                         +-> State store                           |
|                         +-> Session store                         |
|                         +-> Approval store                        |
|                         +-> Trace / event store                   |
+-------------------------------------------------------------------+
```

Execution model:
```text
Submit Run
   |
   v
Validate request
   |
   v
Load workflow + referenced config
   |
   v
Cross-validate and resolve
   |
   v
Build runtime plan
   |
   v
Execute step-by-step
   |
   +--> deterministic tool step
   |
   +--> model-backed step
   |
   +--> approval gate
   |
   +--> resume after approval
   |
   v
Persist final run status + trace + outputs
```

Architecture rules:
- registries remain source-of-truth for config definitions
- compiler remains responsible for validation, normalization, and plan building
- runtime remains responsible for execution and state transitions
- API layer should orchestrate services, not implement business logic directly
- stores should be abstracted behind interfaces so persistence can evolve cleanly

---

## Repository guidance for Phase 2
Keep the repository shape simple and close to current structure.
Do not introduce unnecessary framework complexity.

Expected focus areas:
```text
agentwonder/
├── api/
│   ├── routes_runs.py
│   ├── routes_approvals.py        # add or expand
│   ├── routes_templates.py
│   ├── routes_tools.py
│   └── routes_health.py
├── compiler/
│   ├── loader.py
│   ├── resolver.py
│   ├── validators.py
│   └── builder.py
├── runtime/
│   ├── executor.py
│   ├── run_service.py             # add if missing
│   ├── session_store.py
│   ├── state_store.py
│   ├── approvals.py
│   ├── approval_store.py          # add if missing
│   ├── model_router.py
│   └── step_handlers.py           # add if useful
├── observability/
│   ├── tracing.py
│   ├── events.py
│   ├── evals.py
│   └── trace_store.py             # add if missing
├── tools/
│   ├── rest_wrapper.py
│   ├── openapi_wrapper.py
│   ├── auth.py
│   └── execution.py               # add if useful
├── schemas/
│   ├── workflow.py
│   ├── tool.py
│   ├── policy.py
│   ├── prompt.py
│   ├── template.py
│   ├── run.py
│   └── approval.py                # add if missing
└── registry/
```

This is guidance, not a mandate to churn filenames.
Prefer targeted additions over sweeping rewrites.

---

## Data model expectations
All persisted and API-facing contracts must be Pydantic v2 models.

Minimum schema families:
- `RunRequest`
- `RunStatus`
- `RunRecord`
- `StepRecord`
- `ApprovalRequest`
- `ApprovalDecision`
- `ApprovalRecord`
- `TraceEvent`
- `ToolExecutionRecord`
- `EvaluationResult`

Validation rules:
- enforce ids and versions
- use enums for finite states
- normalize defaults centrally
- keep models serializable
- make failure states explicit
- reject write steps without approval policy where required

Never pass loose dicts deep into the runtime if a typed model exists.

---

## Persistence guidance
Phase 2 does not need a heavyweight distributed platform.
It does need persistence abstraction.

Implement stores behind interfaces so the initial backend can be simple.
Examples:
- in-memory for tests
- file-based or SQLite-backed persistence for local/dev
- clean upgrade path to Postgres later

Rules:
- do not hard-code a production-only persistence dependency too early
- do not mix storage concerns into route handlers
- do not let execution correctness depend on process memory alone

---

## LLM integration guidance
LLM support is optional per step, not mandatory for the whole platform.

Implementation principles:
- deterministic orchestration stays outside the model
- model-backed steps should be explicit in workflow config
- prompt versions must be traceable
- output should be structured and validated whenever possible
- handle model failures predictably
- keep model adapter boundaries clean

Do not turn AgentWonder into a chat app.
It is a governed workflow platform.

---

## Tool execution guidance
Tool execution is a key Phase 2 focus.

Execution requirements:
- validate request payloads before execution
- respect environment and auth constraints
- support timeout and retry policies
- redact secrets in traces and logs
- capture normalized result metadata
- classify side effects
- enforce approval before side-effecting operations

Where possible, make tool execution deterministic and testable with mocks.

---

## Testing expectations for Phase 2
Add tests as you build. Do not defer test coverage to the end.

Required test categories:
1. schema validation tests
2. cross-reference and compiler tests
3. run lifecycle tests
4. approval flow tests
5. tool execution tests with mocks
6. trace persistence tests
7. API contract tests
8. failure and retry tests

Also add at least one end-to-end test path for the pilot workflow.

---

## Implementation order for Claude Code
Follow this order unless a small deviation is clearly better.

1. assess the current repo and summarize gaps vs Phase 2 goals
2. update or add Phase 2 schemas
3. implement persistence abstractions and simple store backends
4. implement durable run service and run lifecycle handling
5. implement approval persistence and resume/reject flows
6. harden tool execution layer
7. add model-backed step execution support where missing
8. persist trace/event/eval records
9. complete API routes for runs and approvals
10. add or expand tests
11. update docs only after code paths are real

Before large refactors:
- explain the change briefly
- preserve working Phase 1 behavior where practical
- avoid churn for cosmetic reasons alone

---

## Acceptance criteria for Phase 2
Phase 2 is successful when all of the following are true:

1. a workflow can be submitted through an API
2. the run is persisted with a durable lifecycle state
3. deterministic tool steps execute through real wrappers
4. at least one model-backed step can execute in a controlled way
5. an approval-required step pauses the run and creates an approval record
6. approving or rejecting the request changes the run outcome correctly
7. run traces and key events are persisted and retrievable
8. tests cover core run, approval, and tool paths
9. config remains YAML-first and validated through Pydantic
10. no full UI is introduced

---

## Pilot recommendation
Optimize Phase 2 around one pilot workflow, likely the existing example workflow or a close derivative.

The pilot should prove:
- config load and validation
- runtime planning
- deterministic step execution
- one model-backed step
- one approval gate
- persistence and resumption
- trace inspection

Do not broaden the template surface before this works well.

---

## Non-goals and anti-patterns
Do not:
- rebuild the whole repo from scratch
- introduce a broad visual UI
- add all 17 patterns now
- blur compiler and runtime responsibilities
- allow raw YAML dicts to leak throughout the runtime
- add dynamic plugin magic everywhere
- hide state transitions
- let side-effecting tools bypass approvals
- over-engineer persistence too early

---

## Working style for Claude Code
- prefer small, explicit modules
- prefer typed contracts over dynamic behavior
- prefer composition over inheritance
- preserve readability
- keep docs aligned with real implementation
- favor pragmatic production starter quality over abstract framework design

When in doubt, choose the design that makes a single pilot workflow safer, more observable, and easier to operate.

---

## Output expectation
When implementing Phase 2, make AgentWonder feel like a clean internal governed workflow runtime that is ready for one real pilot deployment.

Focus on:
- reliability
- traceability
- safe side effects
- controlled model usage
- operator clarity

Not on surface-area expansion.
