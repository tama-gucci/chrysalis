# Chrysalis Capability Status (mdbase v0.3 Agent Framework)

Reviewed against source on 2026-09-27. This document is the authoritative ground-truth implementation reference for the Chrysalis mdbase v0.3 AI Agent Framework.

---

## 1. Framework Core (mdbase v0.3)

| Capability | State | Evidence / Implementation Reference |
| :--- | :--- | :--- |
| **Collection Manifest (`mdbase.yaml`)** | **Implemented** | `mdbase.yaml` specifies `spec_version: "0.3.0"`, Draft 2020-12, types and contracts folders. |
| **Type Schemas (`_types/*.md`)** | **Implemented** | `_types/task.md`, `project.md`, `zettel.md`, `source.md`, `system_state.md` adhering strictly to JSON Schema Draft 2020-12 and `kind: mdbase.type`. |
| **Agent Runtime Contract** | **Implemented** | `contracts/agent-runtime.contract.md` (8-stage lifecycle, 9 discrete actions, approval gate, 22 diagnostic codes). |
| **Ingestion Input Contract (`v1.0.0`)** | **Implemented** | `contracts/ingestion-input.contract.md` & `helpers/ingestion_contract.py` (provider-neutral `file`, `text`, and `structured_task` normalization, separated `sha256` / `normalized_text_sha256` / `structured_payload_sha256` fingerprints, composite external identity, and anti-injection sanitization). |
| **Collection & Path Contract** | **Implemented** | `contracts/mdbase-collection.contract.md` (tripartite model, record identities, wikilinks matrix, 14-day horizon). |
| **Persistent Agent Memory** | **Implemented** | `System/Memory.md` and public templates `System/_templates/Memory.template.md` & `System/_templates/Ingestion-Sources.template.md` (deterministic preferences, modality baselines, bounded multiplier learning, private `ingestion.sources` bindings). |
| **Validation & CAS Helpers** | **Implemented** | `helpers/mdbase_helper.py`, `helpers/ingestion_contract.py`, `helpers/providers/google_drive.py`, `helpers/providers/google_tasks.py` (atomic CAS mutations, `validate_record`, `discover_configured_source`, `evaluate_provider_file_identity`, `evaluate_task_capture_identity`, `draft_structured_task_capture`, `reconcile_syllabus`, `classify_deliverable_horizons`, `prevalidate_ingestion_proposal`, `apply_ingestion_proposal`, `verify_ingestion_batch`). |
| **Operational Workflow Runbooks** | **Implemented** | `System/Workflows/01-capture.md` through `08-continuation.md`. |
| **Provider-Independent Core Ingestion (`/ingest`) & Optional Provider Adapters** | **Implemented** | `.agent/skills/ingest/SKILL.md` (100% provider-neutral 7-stage lifecycle `discover → extract → draft → prevalidate → approve → apply → verify` via `/ingest --source <alias>` and `/ingest --all`), paired with optional read-only integration skills `.agent/skills/google-drive/SKILL.md` (`media`) and `.agent/skills/google-tasks/SKILL.md` (`quick-capture`). |
| **Protected Framework Updater (`update.py`)** | **Implemented** | `update.py` (deploys allowlisted framework files, preserves custom skills, `System/Memory.md`, `System/Ingestion-Sources.md`, and previously deployed `.obsidian/plugins/**`, prunes retired Spark/mirror artifacts with pre-mutation backups, enforces exact-content SHA-256 verification on `_rollback()`, and protects all personal data). |
| **Local Python Test Harness** | **Implemented** | Standalone validation harness in `tests/harness/validation_harness.py`, unit/integration tests in `tests/test_validation_harness.py`. |
| **Synthetic Worked Scenario & Failure Suite** | **Implemented** | Synthetic syllabus v1, v2 revised, transcript, prompt injection (`fixtures/`), end-to-end runner in `tests/test_worked_scenario.py`, 6 negative tests in `tests/test_failure_modes.py`, and provider-neutral ingestion suite in `tests/test_provider_neutral_ingestion.py`. |
| **Staged Vault Migration Plan** | **Implemented** | Non-destructive migration plan in `docs/staged-migration-plan.md`. |

---

## 2. Retained Subsystems & Invariants

| Capability | State | Evidence / Implementation Reference |
| :--- | :--- | :--- |
| **Tripartite Hypergraph Model** | **Implemented** | Sources $\leftrightarrow$ Zettels $\leftrightarrow$ Roadmaps $\leftrightarrow$ Tasks linked via `[[WikiLinks]]`. |
| **Direct Local Agent Access (`A2`)** | **Implemented** | Capable local agents (Antigravity, Codex, Claude Code) operate directly on the local vault paired with `helpers/mdbase_helper.py` and headless `mdbase -C <vault>` CLI. |
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
| **Bespoke Gemini Spark Integration** | `chrysalis-router`, `_types/skill.md`, `Skills/` hardlinks & `Skills/bundle/SKILL.md`, `spark-agent-system-prompt.md`, `golem-deployment-and-spark-test-guide.md`, `mcp.mdbase.dev` relay grants | Retired on 2026-09-27; capable local agents (Antigravity, Codex) read `.agent/skills/` and mutate the local vault directly without cloud MCP workarounds. |
| **Golem Packaging Wrappers** | `System/scripts/package_golem_bundle.py` and `setup_golem.ps1` | Retired on 2026-09-27; redundant with cross-platform `update.py`, `bootstrap.py`, and `export_starter.py`. |
| **`mdbase connect` Background Daemon** | Persistent background relay listener (`mdbase connect` scheduled task) | Retired on 2026-09-27; local filesystem and headless `mdbase -C <vault>` CLI require zero background daemons. |
| **`apps/gateway/`** | FastAPI REST/WebSocket daemon on port 8765 | Archived on `archive/deprecated-apps`; core framework operates directly on local mdbase Markdown files. |
| **`apps/mobile/`** | Custom Flutter cross-platform mobile client | Archived on `archive/deprecated-apps`; mobile access provided by Obsidian Mobile / native recorders. |
| **Vendored Obsidian Plugin Bundle** | 5.8 MB bundle in `.obsidian/plugins/chrysalis-obsidian/` | Removed; community TaskNotes plugin installed directly by users. |
| **Autonomous 3 AM Cron** | Background night-time task mutations | Retired; runtimes execute interactively with human approval. |
| **Static Candidate Task Pools** | `quick_wins` and `deep_work` lists in YAML | Retired; replaced by dynamic mdbase queries. |
| **Continuous Multiplier Decay** | Exponential time-decay loops in background | Retired; replaced by deterministic per-session feedback rule in `System/Memory.md`. |

---

## 4. Deferred Integrations (Clearly Labeled Future Phases)

| Integration | Candidate Architecture | Current Disposition |
| :--- | :--- | :--- |
| **TaskNotes Google Calendar Sync** | Two-way OAuth 2.0 calendar sync via TaskNotes | **DEFERRED** to community plugin runtime; Chrysalis initializes `googleCalendarEventId: null`. |
| **Wear OS Smartwatch Client** | Standalone wearable client | **DEFERRED** / parked in backlog. |

---

## 5. Verification Records

### Provider-Independent Ingestion & One-Way Task Capture Verification (2026-09-29)
- **Provider-Neutral Ingestion Suite**: `python -m unittest tests.test_provider_neutral_ingestion -v` $\to$ **10/10 passed** (core `/ingest` provider neutrality, contract `1.0.0` fingerprint separation, provider relocation guard & `previous_sources`/`previous_paths` preservation, Google Tasks composite identity & date-only preservation, conflict proposal prevalidation/application with local `scheduled`/`project_ref` & repeat-import conflict deduplication, bounded pagination & read-only enforcement, resumable batch ledger, untrusted payload quarantine, legacy migration, and multi-list collision/subtask reconciliation).
- **Core Unittest Suite**: `python -m unittest discover -t . -s tests` $\to$ **301 tests passed, 1 skipped cleanly** (0 failures, 0 errors).
- **Local Validation Harness**: `python tests/harness/validation_harness.py -c .` $\to$ **Exit code 0** (0 errors, 0 warnings).
- **System Integrity Diagnostic (`/doctor`)**: `python System/scripts/doctor.py --vault .` $\to$ **HEALTHY** (0 errors, 17/17 skills strictly verified).
- **Candidate Privacy Audit**: `python Development/scripts/candidate_audit.py` $\to$ **passed: true, 0 findings**.

### Milestone 3 Verification (2026-09-23)
- **Pytest Full Suite**: `.venv/bin/pytest tests/` $\to$ **259 passed, 1 skipped cleanly** (0 failures, 0 errors).
- **Core Unittest Suite**: `.venv/bin/python -m unittest discover -t . -s tests` $\to$ **259 tests passed cleanly**.
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
