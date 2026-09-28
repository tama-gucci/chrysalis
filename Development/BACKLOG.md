# Chrysalis Framework Backlog (mdbase v0.3 Architecture)

Objective: Maintain an authoritative engineering roadmap for the Chrysalis mdbase v0.3 AI Agent Framework, tracking completed foundational milestones, active validation tasks, and deferred runtime/application integrations.

---

## Roadmap Overview & Milestone Status

```text
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: MDBASE V0.3 FOUNDATION & CORE CONTRACTS                       │
│  [M1] Product Purpose, Architecture & Shared Contracts   ──► [DONE]     │
│  [M2] Database Foundation & Portable Workflows           ──► [DONE]     │
│  [M3] Local Validation Harness, Scenarios & Migration    ──► [DONE]     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: CANDIDATE RUNTIME AGENT INTEGRATIONS                          │
│  [R01] Gemini Spark Cloud MCP Adapter (mcp.mdbase.dev)   ──► [RETIRED]  │
│  [R02] Claude / OpenAI Codex Local Direct Execution      ──► [ACTIVE]   │
│  [R03] Local LLM / Ollama Local Agent Runner             ──► [PROPOSED] │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: APPLICATION & SYNCHRONIZATION BRIDGES                         │
│  [A01] TaskNotes Google Calendar OAuth Sync Harmonization ─► [DEFERRED] │
│  [A02] mdbase connect Daemon & Local Inbound Listener    ──► [RETIRED]  │
│  [A03] Obsidian Dataview & Kanban View Template Suite    ──► [PROPOSED] │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: EXTENDED CAPABILITIES & HARDWARE                              │
│  [E01] Multimodal Audio Ingestion Pipeline (Recorder Export) [PROPOSED] │
│  [E02] Standalone Wear OS Smartwatch Client              ──► [DEFERRED] │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Phase 1: mdbase v0.3 Foundation (Completed)

| ID | Title | Scope & Deliverables | Status | Evidence Reference |
| :--- | :--- | :--- | :--- | :--- |
| **M1** | Purpose, Architecture & Contracts | Shared contracts (`agent-runtime.contract.md`, `mdbase-collection.contract.md`), `System/Memory.md`, 3-layer validation model, component disposition ledger. | **DONE** | Gate 1 Approved; 152 unittests passed; PII scanner clean. |
| **M2** | Database Foundation & Workflows | `mdbase.yaml`, `_types/*.md` (Draft 2020-12), `_contracts/`, `_templates/`, `helpers/mdbase_helper.py`, workflows 01-08. | **DONE** | Gate 2 Approved; 81 pytest tests passed cleanly. |
| **M3-1**| Local Validation Test Harness | Standalone objective Python test harness (`tests/harness/validation_harness.py`) validating collections, types, and link integrity with 0 cloud dependencies. | **DONE** | Harness package implemented in `tests/harness/`, 20 tests in `tests/test_validation_harness.py`. |
| **M3-2**| Worked Scenario & 6 Failure Tests | Synthetic syllabus v1, v2 revised, transcript, prompt injection; end-to-end 8-stage lifecycle; 6 negative failure mode tests. | **DONE** | Complete 8-stage runner `tests/test_worked_scenario.py` and 6 failure tests `tests/test_failure_modes.py`. |
| **M3-3**| Documentation & Migration Plan | Repository documentation overhaul (README, ARCHITECTURE, AGENTS, BACKLOG, STATUS); staged migration plan; `Development/HANDOFF.md` update. | **DONE** | Overhaul complete; 260 tests passed; PII audit passed (0 findings). |

---

## Phase 2: Runtime Agent Integrations

*Prerequisite: Milestone 3 complete and Gate 3 verified.*

### R01: Gemini Spark Cloud MCP Adapter (`mcp.mdbase.dev`)
- **Status**: **RETIRED** (2026-09-27). Bespoke Gemini Spark routing (`chrysalis-router`), `Skills/` hardlink bundles, Golem setup wrappers, and `mcp.mdbase.dev` cloud relay grants were retired in favor of direct local vault execution by capable agents (Antigravity, Codex).

### R02: Direct Local Vault Execution (`helpers/mdbase_helper.py` + `mdbase -C <vault>`)
- **Status**: **ACTIVE**
- **Scope**: Capable local agents (Google Antigravity, OpenAI Codex, Claude Code) operate directly on the local Markdown collection paired with `helpers/mdbase_helper.py` (`validate_record`, `apply_cas_mutation`) and headless `mdbase -C <vault>` CLI without cloud relays or background daemons.
- **Acceptance Criteria**:
  - Zero network transport; purely local stdio JSON-RPC.
  - Native invocation of `helpers/mdbase_helper.py` for schema and CAS verification.

### R03: Local LLM / Ollama Provider Bridge
- **Status**: **PROPOSED**
- **Scope**: Provider bridge enabling local models (Llama 3, Mistral, Qwen) to execute the 8-stage agent lifecycle using local tool-calling interfaces.

---

## Phase 3: Application & Synchronization Bridges (Deferred / Proposed)

### A01: TaskNotes Google Calendar Synchronization
- **Status**: **DEFERRED** to community plugin runtime.
- **Scope**: Document and verify Obsidian TaskNotes plugin as the designated sole writer for Google Calendar synchronization via `googleCalendarEventId`.
- **Acceptance Criteria**:
  - Chrysalis initializes `googleCalendarEventId: null` on task creation.
  - TaskNotes detects new task notes, creates calendar events, and populates `googleCalendarEventId`.
  - External calendar date shifts are pulled into task frontmatter by TaskNotes without breaking mdbase schemas.

### A02: `mdbase connect` Daemon & Relay Integration
- **Status**: **DEFERRED**
- **Scope**: Inbound request listener (`crates/connect-cli`) running on local workstation.
- **Acceptance Criteria**:
  - Local filesystem remains authoritative.
  - Validated under Windows 11 x64 emulation and native Linux environments.

### A03: Obsidian View Template Suite
- **Status**: **PROPOSED**
- **Scope**: Provide public sanitized Dataview and Kanban view templates in `Views/` optimized for the mdbase v0.3 task schema.

---

## Phase 4: Extended Capabilities (Deferred / Proposed)

### E01: Multimodal Audio Ingestion Pipeline
- **Status**: **PROPOSED**
- **Scope**: Document native mobile recorder integration (Google Recorder / Samsung Voice Recorder) exporting transcripts to `Sources/` with SHA-256 digests, feeding the 8-stage lifecycle.

### E02: Standalone Wear OS Smartwatch Client
- **Status**: **DEFERRED** / Parked in backlog.
