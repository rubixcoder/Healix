# Healix Technical Design Document

## 1. Purpose

This document describes the current implemented architecture of Healix and captures the actual runtime flow, components, state model, and sandbox execution behavior.

---

## 2. High-Level Architecture

### 2.1 Core design

- A minimal autonomous self-healing pipeline built as a LangGraph state machine.
- Uses `FastAPI` as the HTTP entrypoint.
- Uses `LangGraph` to model the workflow as stateful nodes and conditional retry routing.
- Uses OpenAI via `langchain_openai` for the architect stage.
- Uses sandboxed patch application and test execution to validate proposed fixes.

### 2.2 Workflow

The implemented workflow is:
1. `observer` node: ingests structured error input or fallback demo error, extracts context, and initializes state.
2. `architect` node: generates a suggested fix with retry-aware prompts.
3. `executor` node: applies the fix in a sandbox, runs tests, and returns results.
4. `executor` routes back to `architect` if the fix is not resolved and retry budget remains.

---

## 3. Components

### 3.1 `main.py`

- Defines a `FastAPI` application.
- Exposes endpoints:
  - `POST /run-pipeline`
  - `GET /health`
- Accepts `PipelinePayload` containing:
  - structured `ErrorInput`
  - `test_mode`
  - `use_docker`
- Converts the request into initial workflow state and invokes `agents.graph.app`.

### 3.2 `agents/graph.py`

- Defines a `HealixState` typed dictionary containing workflow, error, and environment fields.
- Uses `StateGraph` from `langgraph.graph`.
- Implements three nodes:
  - `observer_node`
  - `architect_node`
  - `executor_node`
- Includes a conditional retry edge from `executor` back to `architect`.
- `should_retry()` routes to `architect` while `retry_count < 3` and `is_resolved` is false.
- Exposes the compiled workflow as `app`.

### 3.3 `agents/observer.py`

- Implements `ObserverAgent` with structured error ingestion.
- Accepts an error payload containing:
  - `error_type`, `message`, `file`, `line`, `stacktrace`, `service_name`, and `timestamp`.
- Extracts:
  - formatted logs
  - surrounding code context
  - full file snapshot
  - environment metadata (`python_version`, `platform`, `working_directory`).
- Provides a fallback demo error path when no structured input is provided.

### 3.4 `agents/architect.py`

- Implements `ArchitectAgent` using `ChatOpenAI`.
- Builds a retry-aware prompt, including prior `test_results` when `retry_count > 0`.
- Returns `suggested_fix` from the LLM response.
- Requires `OPENAI_API_KEY` from the environment if not passed explicitly.

### 3.5 `agents/executor.py`

- Implements sandboxed test execution and patch generation.
- Copies `demo_app/` to `sandbox_run/demo_app` for isolated change testing.
- Applies suggested fixes using:
  - `_sanitize_suggested_fix()`
  - `_extract_top_level_block()`
  - `_apply_suggested_fix_to_file()`
- Generates a unified diff via `_generate_patch()` and validates it via `_validate_patch()`.
- Performs syntax validation on Python files before continuing.
- Supports two sandbox execution modes:
  - local pytest via `_run_pytest()`
  - Docker sandbox via `_run_pytest_docker()` using `Dockerfile.sandbox`
- Cleans up the sandbox directory after execution.

### 3.6 `Dockerfile.sandbox`

- Builds a lightweight Python 3.12 sandbox image.
- Installs dependencies from `requirements.txt`.
- Sets `PYTHONPATH=/workspace` so tests can run from the mounted workspace.

### 3.7 `demo_app/`

- Contains the sample application under test.
- `demo_app/logic.py` is the primary target for suggested fixes.
- The executor runs `pytest demo_app/ -q` against this sandbox copy.

---

## 4. Data Model

### 4.1 `HealixState`

The workflow state includes:
- `logs: str`
- `codebase_snapshot: str`
- `context_code: str`
- `suggested_fix: str`
- `test_results: str`
- `retry_count: int`
- `is_resolved: bool`
- `patch_diff: str`
- `patch_target_file: str`
- `use_docker: bool`
- `error_input: Optional[dict[str, Any]]`
- `error_type: str`
- `error_message: str`
- `error_file: str`
- `error_line: int`
- `stacktrace: str`
- `service_name: str`
- `environment_metadata: dict[str, Any]`

### 4.2 Runtime state transitions

- `observer_node` initializes:
  - structured logs, code snapshot, context, error metadata, retry_count, patch metadata, and Docker flag.
- `architect_node` produces:
  - `suggested_fix`
- `executor_node` produces:
  - `test_results`, `is_resolved`, updated `retry_count`, and patch metadata.

---

## 5. Dependency Stack

### Python libraries
- `fastapi`
- `uvicorn[standard]`
- `langgraph`
- `python-dotenv`
- `langchain-openai`
- `langchain-core`
- `pytest`

---

## 6. Execution Flow

### Request handling

- Client posts structured payload to `/run-pipeline`.
- `main.py` converts the payload into initial state and sets `use_docker`.
- The compiled LangGraph workflow executes the observer, architect, and executor nodes.
- The result is returned as JSON.

### Fix generation

- `ArchitectAgent` builds a prompt from logs, code snapshot, and failure history.
- The LLM response is captured as `suggested_fix`.

### Validation

- `Executor` copies the demo app into `sandbox_run`, applies the suggested fix, validates the patch, and runs tests.
- If `use_docker` is true, tests run inside the Docker sandbox image.
- The executor updates state with pass/fail status and patch diff information.

---

## 7. Implementation Characteristics

### Currently implemented

- Structured error ingestion via `ObserverAgent`.
- Dynamic code context extraction and environment metadata capture.
- Retry-capable LangGraph workflow with conditional routing.
- Retry-aware LLM prompt construction in `ArchitectAgent`.
- Structured patch extraction and validation in `agents/executor.py`.
- Optional Docker sandbox execution via `Dockerfile.sandbox`.
- Local sandbox copy and cleanup after test execution.

### Safety and sandboxing

- Patch validation limits broad or empty diffs.
- Python syntax is verified before accepting a suggested fix.
- Docker sandbox execution is supported with `--rm` cleanup.

---

## 8. Current Limitations

- No approval gate, PR creation, or human review workflow.
- No WebSocket streaming or real-time progress events.
- No persistent incident memory store or vector database.
- No cloud CLI tool integration.
- No Helm/Kubernetes deployment artifacts in the current repository.
- Docker sandbox is available but not yet fully orchestrated in a production deployment flow.

---

## 9. Summary

The current repository implements a prototype autonomous repair pipeline with:
- a `FastAPI` API surface,
- a LangGraph workflow with retry logic,
- structured observability from error payloads,
- LLM-powered fix planning,
- sandboxed patch application and test execution,
- optional Docker sandbox support.

Remaining work is centered on governance, memory, streaming UX, cloud integration, and deployment readiness.
