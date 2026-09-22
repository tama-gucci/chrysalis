# Chrysalis Capability Status (mdbase v0.3 Agent Framework)

Reviewed against source on 2026-09-22. This document is the authoritative ground-truth implementation reference for the Chrysalis mdbase v0.3 AI Agent Framework.

---

## 1. Framework Core (mdbase v0.3)

| Capability | State | Evidence / Implementation Reference |
| :--- | :--- | :--- |
| **Collection Manifest (`mdbase.yaml`)** | **Implemented** | `mdbase.yaml` specifies `spec_version: "0.3.0"`, Draft 2020-12, types and contracts folders. |
| **Type Schemas (`_types/*.md`)** | **Implemented** | `_types/task.md`, `project.md`, `zettel.md`, `source.md` adhering strictly to JSON Schema Draft 2020-12 and `kind: mdbase.type`. |
| **Agent Runtime Contract** | **Implemented** | `contracts/agent-runtime.contract.md` (8-stage lifecycle, 9 discrete actions, approval gate, 22 diagnostic codes). |
| **Collection & Path Contract** | **Implemented** | `contracts/mdbase-collection.contract.md` (tripartite model, record identities, wikilinks matrix, 14-day horizon). |
| **Persistent Agent Memory** | **Implemented** | `System/Memory.md` and public template `System/_templates/Memory.template.md` (deterministic preferences, modality baselines, bounded multiplier learning). |
| **Validation & CAS Helpers** | **Implemented** | `helpers/mdbase_helper.py` (atomic CAS mutations via `fcntl.flock`, `compute_revision`, `validate_record`, `check_semantic_duplicate`, `reconcile_syllabus`). |
| **Operational Workflow Runbooks** | **Implemented** | `chrysalis/Workflows/01-capture.md` through `08-continuation.md`. |
| **Local Python Test Harness** | **Implemented** | Standalone validation harness in `tests/harness/validation_harness.py`, unit/integration tests in `tests/test_validation_harness.py`. |
| **Synthetic Worked Scenario & Failure Suite** | **Implemented** | Synthetic syllabus v1, v2 revised, transcript, prompt injection (`fixtures/`), end-to-end runner in `tests/test_worked_scenario.py`, 6 negative tests in `tests/test_failure_modes.py`. |
| **Staged Vault Migration Plan** | **Implemented** | Non-destructive migration plan in `docs/staged-migration-plan.md`. |

---

## 2. Retained Subsystems & Invariants

| Capability | State | Evidence / Implementation Reference |
| :--- | :--- | :--- |
| **Tripartite Hypergraph Model** | **Implemented** | Zettels $\leftrightarrow$ Roadmaps $\leftrightarrow$ Tasks linked via `[[WikiLinks]]`. |
| **Zero-Leak PII Privacy Enforcement** | **Implemented** | Default-deny `.gitignore`, verified via `Development/scripts/candidate_audit.py` and `pii-scanner.sh`. |
| **Anti-Simulation Law** | **Implemented** | Mandatory physical disk mutation; verified via automated test suites. |
| **1:1 Public Template Matrix** | **Implemented** | Sanitized templates in `_templates/`, `System/_templates/`, `Projects/_templates/`, `Slipbox/_templates/`. |
| **Explicit Local Timezone Invariant** | **Implemented** | RFC 3339 timestamps strictly require explicit offset (e.g. `"-05:00"`). |
| **Out-of-Horizon Retention** | **Implemented** | Master roadmaps retain 100% of deliverables; tasks $>14$ days remain inert (`scheduled: null`). |
| **Uncertain Date Modeling** | **Implemented** | Modeled cleanly via `date_uncertain: true` and `due: null`. |
| **Passive Untrusted Text Security** | **Implemented** | Quarantined via `<untrusted_document_payload>` tags and delimiter escaping. |

---

## 3. Retired Subsystems (Historical Reference)

| Subsystem | Previous Role | Retirement Rationale |
| :--- | :--- | :--- |
| **`apps/gateway/`** | FastAPI REST/WebSocket daemon on port 8765 | Retired; core framework operates directly on local mdbase Markdown files. |
| **`apps/mobile/`** | Custom Flutter cross-platform mobile client | Retired; mobile access provided by Obsidian Mobile / candidate runtime agents. |
| **Vendored Obsidian Plugin Bundle** | 5.2 MB pre-compiled `main.js` in `.obsidian/` | Retired; community TaskNotes plugin installed directly by users. |
| **Autonomous 3 AM Cron** | Background night-time task mutations | Retired; runtimes execute interactively with human approval. |
| **Static Candidate Task Pools** | `quick_wins` and `deep_work` lists in YAML | Retired; replaced by dynamic mdbase queries. |
| **Continuous Multiplier Decay** | Exponential time-decay loops in background | Retired; replaced by deterministic per-session feedback rule in `System/Memory.md`. |

---

## 4. Deferred Integrations (Clearly Labeled Future Phases)

| Integration | Candidate Architecture | Current Disposition |
| :--- | :--- | :--- |
| **Gemini Spark Cloud MCP** | Hosted MCP adapter at `mcp.mdbase.dev` | **DEFERRED** to candidate runtime integration phase; local disk authority is primary. |
| **TaskNotes Google Calendar Sync** | Two-way OAuth 2.0 calendar sync via TaskNotes | **DEFERRED** to community plugin runtime; Chrysalis initializes `googleCalendarEventId: null`. |
| **`mdbase connect` Daemon & Relay** | Inbound request listener (`crates/connect-cli`) | **DEFERRED**; local filesystem is authoritative for framework execution. |
| **Wear OS Smartwatch Client** | Standalone wearable client | **DEFERRED** / parked in backlog. |

---

## 5. Verification Records

### Milestone 3 Verification (2026-09-22)
- **Pytest Full Suite**: `.venv/bin/pytest tests/` $\to$ **260 tests passed cleanly** (0 failures, 0 errors, 91 subtests passed).
- **Core Unittest Suite**: `.venv/bin/python -m unittest discover -t . -s tests` $\to$ **260 tests passed cleanly**.
- **Local Validation Harness**: `.venv/bin/python tests/harness/validation_harness.py -c .` $\to$ **Exit code 0** (0 errors, 0 warnings).
- **Privacy Scanner**: `bash Development/scripts/pii-scanner.sh` $\to$ **passed: true, 0 findings**.
- **Candidate Privacy Audit**: `python3 Development/scripts/candidate_audit.py` $\to$ **passed: true, 0 findings**.
- **Worked Scenario Suite**: Full 8-stage lifecycle executed in `tests/test_worked_scenario.py` with physical disk verification.
- **Critical Failure Mode Suite**: 6 negative tests executed in `tests/test_failure_modes.py` with unapproved action blocked, schema violation rejection, CAS conflict, injection neutralization, duplicate deduplication, and revised syllabus diffing.

### Milestone 2 Verification (2026-09-22)
- **Pytest Milestone Suite**: 81 tests passed cleanly in 0.36s.
- **Schema Conformance**: Verified `_types/*.md` against JSON Schema Draft 2020-12 using `jsonschema.Draft202012Validator`.
- **CAS Concurrency**: Verified `apply_cas_mutation` atomic writes and stale revision rejection.
- **Provenance & Deduplication**: Verified SHA-256 duplicate detection and syllabus reconciliation diffing.

### Milestone 1 Verification (2026-09-22)
- **Framework Unittests**: 152 tests passed cleanly.
- **Contracts Implemented**: `contracts/agent-runtime.contract.md` and `contracts/mdbase-collection.contract.md`.
- **Persistent Agent Memory**: Implemented `System/Memory.md` and `System/_templates/Memory.template.md`.
