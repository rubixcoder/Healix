# Healix Roadmap

## Overview

This roadmap outlines the implemented work and the remaining development plan for Healix. The roadmap now reflects current progress with completed items marked as done and future work marked as pending.

---

## Phase 1: Feedback Loops & Retry Logic (Foundation) ✅ Done

**Goal**: Enable the agent to recover from failed fixes by iterating on the architect stage.

### 1.1 Implement cyclic graph logic ✅
- **Task**: Modify `agents/graph.py` to add conditional edges
- **Details**:
  - If `executor` returns `is_resolved=False`, route back to `architect`
  - Pass failure feedback (test_results) into the next iteration
  - Increment `retry_count` on each loop
  - Exit after `max_retries` (3) even if unresolved
- **Status**: Done
- **Acceptance Criteria**:
  - Graph can loop back on test failure ✅
  - Agent receives failure context in the next iteration ✅
  - `retry_count` is tracked and enforced ✅
  - Unit tests pass ✅

### 1.2 Enhance architect prompt with failure context ✅
- **Task**: Update `agents/architect.py` prompt template
- **Details**:
  - Include prior failed attempts if `retry_count > 0`
  - Include the test failure output
  - Ask the LLM to explain why the prior fix failed
  - Guide the LLM toward a different approach
- **Status**: Done
- **Acceptance Criteria**:
  - Architect receives failure telemetry ✅
  - Prompts are contextual based on retry count ✅
  - Tests validate prompt formation ✅

---

## Phase 2: Dynamic Observability & Real Input (Observer Enhancement) ✅ Done

**Goal**: Replace hardcoded logs with a real monitoring interface and dynamic code ingestion.

### 2.1 Create an observability input interface ✅
- **Task**: Design `ObserverAgent` or enhance `observer_node`
- **Details**:
  - Accept structured log inputs (JSON format)
  - Parse error type, file path, line number, stacktrace
  - Dynamically read the target file from the filesystem
  - Extract context around the error location
- **Status**: Done
- **Acceptance Criteria**:
  - `/run-pipeline` accepts structured error input ✅
  - Observer dynamically reads the target file ✅
  - Context extraction includes surrounding code lines ✅
  - Backward compatible with existing empty payloads ✅

### 2.2 Extend observer to capture environment metadata ✅
- **Task**: Add environment context to the state
- **Details**:
  - Capture service name / module name
  - Capture Python version and dependencies if relevant
  - Capture recent changes or version info
  - Store metadata in state for future retrieval
- **Status**: Done
- **Acceptance Criteria**:
  - State includes environment metadata fields ✅
  - Tests validate metadata extraction ✅

---

## Phase 3: Structured Patch Generation & Safe Application (Executor Enhancement) ✅ Done

**Goal**: Move beyond direct file replacement to semantic patch generation and validation.

### 3.1 Implement structured diff/patch extraction ✅
- **Task**: Create `PatchExtractor` utility in `agents/executor.py`
- **Details**:
  - Parse LLM output to extract structured changes
  - Identify the changed function/class/section
  - Generate a proper unified diff or patch
  - Validate that only the intended code changed
- **Status**: Done
- **Acceptance Criteria**:
  - Patch extractor identifies changed sections ✅
  - Generated patches are valid and testable ✅
  - Tests validate patch extraction on various LLM outputs ✅

### 3.2 Containerize sandbox execution with Docker ✅
- **Task**: Replace local sandbox copy with ephemeral Docker container
- **Details**:
  - Create a lightweight Docker image with Python + pytest
  - Mount the codebase as a read-only volume
  - Apply the patch inside the container
  - Run tests and collect results
  - Automatically clean up the container
- **Status**: Done
- **Acceptance Criteria**:
  - Tests run inside isolated Docker containers ✅
  - No side effects on the host system ✅
  - Performance is acceptable (< 30s per fix attempt) — pending runtime measurement
  - Tests validate container cleanup ✅

### 3.3 Implement safety checks before applying fixes ✅
- **Task**: Add validation gates in `executor_node`
- **Details**:
  - Verify patch applies cleanly (no conflicts)
  - Check that only intended files are modified
  - Validate syntax before execution
  - Limit patch scope (e.g., max lines changed)
- **Status**: Done
- **Acceptance Criteria**:
  - Malicious or overly broad patches are rejected ✅
  - Safety checks are logged ✅
  - Tests cover edge cases (syntax errors, large patches) ✅

---

## Phase 4: Memory & Knowledge Store (Context Retrieval) ⏳ Pending

**Goal**: Build a semantic memory layer to improve fix proposals based on historical patterns.

### 4.1 Set up PostgreSQL + pgvector database ⏳
- **Status**: Pending

### 4.2 Implement incident embedding & retrieval ⏳
- **Status**: Pending

### 4.3 Implement fix persistence & evaluation ⏳
- **Status**: Pending

---

## Phase 5: Human Approval & Audit Workflow (Governance) ⏳ Pending

**Goal**: Add a human review gate and PR creation for approved fixes.

### 5.1 Create approval request interface ⏳
- **Status**: Pending

### 5.2 Implement Git branch & PR creation ⏳
- **Status**: Pending

### 5.3 Implement audit & compliance logging ⏳
- **Status**: Pending

---

## Phase 6: WebSocket Streaming & Real-Time Progress (UX Enhancement) ⏳ Pending

**Goal**: Provide real-time visibility into agent reasoning and progress.

### 6.1 Add WebSocket support to FastAPI ⏳
- **Status**: Pending

### 6.2 Instrument graph nodes with event emission ⏳
- **Status**: Pending

---

## Phase 7: Cloud CLI Tool Integration (Extensibility) ⏳ Pending

**Goal**: Enable the agent to invoke cloud CLI tools safely.

### 7.1 Design secure tool-calling interface ⏳
- **Status**: Pending

### 7.2 Integrate cloud CLIs into executor ⏳
- **Status**: Pending

### 7.3 Add multi-cloud support ⏳
- **Status**: Pending

---

## Phase 8: Deployment & Observability (Production Readiness) ⏳ Pending

**Goal**: Prepare the system for production deployment.

### 8.1 Add comprehensive logging with LangSmith ⏳
- **Status**: Pending

### 8.2 Create Helm charts for Kubernetes ⏳
- **Status**: Pending

### 8.3 Add metrics & alerting ⏳
- **Status**: Pending

---

## Phase 9: Documentation & Demo (Go-Live) ⏳ Pending

**Goal**: Prepare for public demo and knowledge sharing.

### 9.1 Write comprehensive documentation ⏳
- **Status**: Pending

### 9.2 Build demo scenarios ⏳
- **Status**: Pending

### 9.3 Create interactive playground ⏳
- **Status**: Pending

---

## Current Project Status

- Phase 1: Done ✅
- Phase 2: Done ✅
- Phase 3: Done ✅
- Phase 4+: Pending ⏳

---

## Next Focus

1. Add persistent memory and incident retrieval.
2. Implement human approval and audit flows.
3. Add real-time WebSocket progress streaming.
4. Extend to cloud CLI tooling and production deployment.
