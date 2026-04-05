# CLAUDE.md

## Mission
Phase 2 is complete enough to prove the baseline runtime, but AgentWonder is not yet production-realistic. The repository already has:
- a YAML-first configuration model under `config/`
- a Pydantic-first contract layer
- runtime/compiler/registry/api modules under `agentwonder/`
- tests and notebook-driven validation
- a Phase 2 runtime that still uses **stubbed LLM execution** and **in-memory session/state stores**

Your job now is to implement **Version 2.5: runtime realism, logging, persistence design, real Gemini execution, and meaningful LLM-backed tools**.

AgentWonder remains:
- **YAML-first** for authoring
- **Pydantic-first** for contracts and validation
- **API-first** for execution and operations
- **template-governed** for safety and consistency
- **lightweight UI** only; no full visual builder

Do **not** introduce proprietary names such as `nerds_nlp`, `nerds-nlp`, `EDGE`, or `edge` as complete words or in package names, module names, examples, docs, or comments.

---

## Version 2.5 objective
Move AgentWonder from a Phase 2 pilot runtime into a **developer-realistic and operator-realistic execution platform** with:
1. real logging
2. pluggable run/state persistence
3. real Gemini model execution
4. environment-based secret injection
5. a couple of meaningful LLM-backed tools
6. updated tests, notebook, and docs

The goal is still **depth, not breadth**.

Do **not** expand into a large UI, all 17 patterns, autonomous memory-heavy behavior, or broad MCP-first integration.

---

## Current-state assumptions
Assume the repository already contains:
- top-level `config/`
- `agentwonder/` package
- schemas, compiler, runtime, registry, observability, tools, and API modules
- tests and notebook-based validation
- example workflow(s)
- Phase 2 run lifecycle and approvals concepts

Do not rebuild earlier phases from scratch.
Extend and harden what exists.

Important current-state realities to respect:
- the runtime currently uses **stubbed LLM execution** in `executor.py`
- session/state persistence is currently **in-memory only**
- logging is not yet production-useful

---

## What we are building now
Version 2.5 should deliver a runtime that lets teams:
1. run workflows with durable and inspectable execution records
2. persist run/session/state data through a pluggable persistence layer
3. default to append-only file-based persistence/logging
4. later swap to a database-backed persistence implementation without redesigning the runtime
5. execute selected `llm_agent` steps against real Gemini models
6. inject Gemini credentials from environment variables or an enterprise secret provider abstraction
7. use at least two practical LLM-backed tools in workflows
8. inspect logs, traces, failures, and persisted run history
9. validate the full path through tests and a runnable notebook

---

## What we are not building in Version 2.5
- no drag-and-drop UI
- no broad visual workflow editor
- no all-17-pattern runtime expansion
- no generalized marketplace or plugin ecosystem
- no mandatory MCP registration for all tools
- no hard dependency on external databases for local development
- no secrets committed to the repository
- no fragile notebook-only implementation

---

## Architectural direction for Version 2.5

### 1) Logging must become real and structured
Implement a real logging baseline for runtime, tools, approvals, persistence, and LLM execution.

Requirements:
- use Python logging consistently across runtime paths
- support file logging in local development
- prefer structured logs (JSON lines or consistently structured text)
- include at least: timestamp, level, module, run_id, workflow_id, step_id, event_type, message
- ensure every workflow run can be correlated through logs
- ensure errors include useful diagnostic context without leaking secrets
- expose logging configuration through code/config rather than hardcoding

Design preference:
- create a logging configuration module under `agentwonder/observability/`
- support local file sinks by default
- keep the design compatible with future enterprise log aggregation

### 2) Persistence must be pluggable, with file-backed default behavior
Design the persistence layer so the same runtime code can persist to:
- local append-only files / log files by default
- a database-backed implementation later

Important principle:
- **do not scatter persistence decisions across executor logic**
- define interfaces / protocols / base classes for persistence concerns

Minimum persistence domains:
- run metadata
- run status transitions
- step outputs / state
- approval records
- session/context data
- execution events / audit trail

Recommended architecture:
- `RunStore` interface
- `StateStore` interface
- `SessionStore` interface
- `ApprovalStore` interface
- optional `EventStore` interface

Default implementation:
- file-backed persistence under a configurable runtime data directory
- use append-only event logs where practical
- store records in human-inspectable formats such as JSON / JSONL
- allow deterministic reconstruction of run state from persisted records where possible

Database-ready design:
- define clean repository-style contracts now
- keep database implementation optional in Version 2.5
- it is acceptable to include a placeholder or simple reference backend, but file-backed persistence is the primary deliverable

### 3) Replace stubbed LLM execution with real Gemini support
The current Phase 2 runtime recognizes model names but does not yet call the real Gemini API. Version 2.5 must make selected `llm_agent` execution real.

Requirements:
- implement a real model client abstraction
- support Gemini through the official Google Gen AI SDK or ADK-compatible path
- route configured `llm_agent` steps to the real Gemini client
- preserve deterministic fallback behavior for non-LLM steps
- ensure failures are logged and surfaced clearly
- support timeout/error handling and structured model invocation results

Model design guidance:
- create a provider abstraction rather than hard-coding Gemini into executor logic
- support at least one real provider now: Gemini
- keep the interface extensible for future enterprise model backends

### 4) Support environment-based secret injection
Version 2.5 must support local development with `.env` while remaining enterprise-friendly.

Requirements:
- support loading Gemini credentials from environment variables
- support `.env` for local development only
- do not commit real secrets
- add `.env.example` with placeholder variable names only
- design a small secret/config provider abstraction so enterprise environments can inject credentials without changing business logic

Recommended pattern:
- local development: `.env` or shell environment variables
- runtime code: read credentials through a config/settings layer
- enterprise: replace or extend the config provider without rewriting tool/runtime logic

### 5) Add at least two meaningful LLM-backed tools
Version 2.5 should implement at least two practical tools that call an LLM and do something useful beyond a stub.

These should be implemented as real AgentWonder tools that fit the YAML-first and Pydantic-first model.

Suggested tool options (choose at least two):
- `summarize_context_tool`: summarize a structured or semi-structured payload for operators
- `extract_structured_fields_tool`: extract specific fields from free text into typed JSON
- `risk_signal_tool`: classify severity / urgency / action-needed categories from text
- `resolution_draft_tool`: generate a draft resolution or recommendation from gathered context
- `compare_candidates_tool`: compare alternative actions and return a structured recommendation

Tool requirements:
- clear input schema
- clear output schema
- deterministic response parsing where possible
- structured error handling
- logging and trace emission
- config-driven model selection where appropriate

Prefer tools that are actually useful in the existing break-resolution style workflow.

### 6) Preserve and strengthen YAML/Pydantic/runtime layering
The flow must remain:

```text
YAML -> Pydantic schema -> canonical runtime config -> runtime execution
```

Do not bypass schema validation just because a new feature is added.
Do not hide critical runtime behavior inside notebooks.

### 7) Keep APIs and notebook aligned with runtime reality
Version 2.5 must leave the project in a state where:
- tests pass
- the notebook runs locally
- the notebook demonstrates the real Gemini-backed path when credentials are available
- the notebook degrades gracefully or explains prerequisites when credentials are absent
- docs are updated when interfaces/configs change materially

---

## Version 2.5 workstreams

### Workstream 1: Observability and logging baseline
Implement:
- logging configuration module
- per-run correlation fields
- step-level structured logs
- persistence events in logs
- LLM invocation logs (without secrets)
- error/exception logs with useful context

Acceptance signals:
- local runs write inspectable logs to disk
- logs can be traced by `run_id`
- notebook/demo can point operators to the log output location

### Workstream 2: Persistence architecture and default file backend
Implement:
- store interfaces / abstractions
- default file-backed implementations
- persisted run lifecycle records
- persisted state outputs
- persisted approval records
- persisted session/context records
- runtime loading/reconstruction where appropriate

Acceptance signals:
- a run can be inspected after process completion through persisted artifacts
- state is no longer only in memory
- the design clearly allows later DB substitution

### Workstream 3: Real Gemini integration
Implement:
- Gemini provider client
- settings/config integration for API key loading
- real `llm_agent` execution path
- robust response normalization into AgentWonder runtime outputs
- safe error handling and logging

Acceptance signals:
- a configured workflow can call Gemini successfully when credentials are available
- failures are visible and diagnosable
- model configuration remains YAML/config driven where appropriate

### Workstream 4: LLM-backed tools
Implement at least two tools that use the Gemini integration meaningfully.

Acceptance signals:
- tools are callable from workflows
- tools have schemas, tests, and notebook coverage
- outputs are useful and structured enough for downstream use

### Workstream 5: Documentation, notebook, and tests
Update:
- root `README_v1.md` or evolve documentation as needed
- notebook to demonstrate Version 2.5 path
- tests for logging, persistence, model invocation abstraction, and LLM-backed tools
- `.env.example`

Acceptance signals:
- a developer can clone the repo, configure a local environment, set API credentials, and run the notebook/tests successfully

---

## Implementation guidance

### Preferred implementation order
1. review current code and identify exact extension points
2. introduce/configure structured logging
3. define persistence interfaces and file-backed implementations
4. refactor runtime to depend on interfaces instead of in-memory-only stores
5. add settings/config layer for environment and `.env`
6. implement Gemini provider abstraction and real execution path
7. implement two LLM-backed tools
8. update workflow/config examples if needed
9. update notebook and tests
10. update docs

### Design rules
- keep changes incremental and reviewable
- prefer small focused modules over large rewrites
- do not hardcode secrets, absolute paths, or environment-specific assumptions
- avoid introducing unnecessary frameworks
- keep local development easy
- do not let notebook code become the source of truth
- do not degrade current tests while adding new features

### Persistence design preference
Use **file-backed persistence as the default operational baseline**.
A good design is:
- append event / audit records to JSONL files
- persist run metadata and status snapshots separately where useful
- keep storage layout simple and inspectable
- make the storage root configurable

Example concept:

```text
runtime_data/
  runs/
    <run_id>/
      run.json
      status_history.jsonl
      events.jsonl
      state.json
      session.json
      approvals.json
```

This is only a design direction; adapt it if a cleaner file layout emerges.

### Gemini integration guidance
- centralize model invocation behind a provider interface
- load API keys from environment/settings, not from workflow YAML
- support local `.env` but do not require `.env` in enterprise settings
- prefer typed request/response handling
- log model names, latency, and success/failure, but never log raw secrets

### Tool guidance
Choose tools that demonstrate business value and runtime realism.
At least one tool should return a typed structured object suitable for downstream workflow use.

---

## Validation requirements
Before considering Version 2.5 complete:
- all existing tests must pass
- new tests must cover added functionality
- the notebook must run locally
- local setup with `.env` must be documented
- the runtime must work without `.env` by failing gracefully where Gemini is required
- no real secrets may be committed

---

## Deliverables
Version 2.5 should leave the repository with:
- updated runtime logging
- pluggable persistence abstractions
- default file-backed persistence implementation
- real Gemini execution support
- environment/settings-based secret injection
- at least two meaningful LLM-backed tools
- updated tests
- updated notebook
- updated docs/config examples where needed

---

## Done criteria
Version 2.5 is done when:
1. a workflow run writes useful structured logs to disk
2. run/session/state/approval data are persisted through non-memory-only mechanisms
3. the persistence design can later swap to a DB backend cleanly
4. `llm_agent` execution can call real Gemini with credentials from environment/settings
5. at least two LLM-backed tools work meaningfully and are tested
6. notebook and docs demonstrate the new reality clearly
7. the codebase still feels like AgentWonder: YAML-first, Pydantic-first, governed, and modular
