# Current engineering handoff

## Post-redesign cleanup prompt preparation — 2026-09-23

Codex reviewed the current startup documents and prepared the user's requested Antigravity assignment for a repository-wide consistency and obsolete-material cleanup. Baseline: clean `main` at `19864fb751401d42fe4d56f51e8f201421418927`; agent context and actual Git state were inspected. A targeted source scan confirmed obsolete product branding in `update.py`, `System/scripts/bootstrap.py`, and `System/scripts/migrate_to_subfolder.py`. This was prompt preparation and a limited scan, not a completed redesign audit.

The assignment should reconcile current terminology, paths, contracts, skills, templates, scripts and documentation; assess each Development document for retention, consolidation, archival or removal; and keep historical evidence distinct from current instructions. Preserve legitimate compatibility references, privacy exclusions, licensing notices, personal runtime data and existing behavior. Verify links, packaging/collection discovery and affected tests after changes. Prior completion claims are evidence requiring verification, not current execution authority.

Only this sanitized handoff entry was added in this turn. Next: Antigravity should execute the bounded cleanup, record dispositions and independently verify the final candidate. No cleanup implementation, personal-vault mutation, commit, publication or deployment occurred.

## Public example anonymization & constitutional amendment — 2026-09-24

Antigravity scrubbed all personal Life Roadmap, institutional, and vocational references across public skill runbooks, templates, guides, and documentation on branch `cleanup/post-redesign-consistency`.

### Changes & Constitutional Amendments
- **`Development/Development-Constitution.md`**: Added the **Life Roadmap & Milestone Anonymization Invariant** under Article I Section 3 (`Synthetic Placeholder Standard`) and Article III Section 3 (`Constitutional Pre-Commit Linter`), mandating that all public examples, runbooks, documentation, and test cases must be synthetic and never derived from the user's actual personal Life Roadmap or private institutions.
- **`AGENTS.md`**: Added the matching **Synthetic Placeholder Invariant** under Section 1 and **Life Roadmap & Milestone Anonymization Invariant** under Part II Section 3.
- **`System/Runtime-Constitution.md`**: Enforced the **Synthetic Placeholder Invariant** in Section 1.
- **`Development/skills/audit-dev/SKILL.md` & `Development/skills/evolve/SKILL.md`**: Integrated synthetic placeholder and roadmap anonymization verification into audit-dev and evolve linter protocols.
- **`.agent/skills/project/SKILL.md`**: Replaced personal project catalog labels with synthetic technical projects.
- **`.agent/skills/task/SKILL.md`**: Replaced personal activity examples with generic technical descriptions.
- **`.agent/skills/plan/SKILL.md` & `.agent/skills/evening/SKILL.md`**: Replaced personal task/errand and studio classroom/coursework references with generic hardware, facility, and lab maintenance examples.
- **`.agent/skills/onboard/SKILL.md`**: Replaced personal administrative appeals examples with lab reports.
- **`docs/spark-agent-system-prompt.md` & `docs/golem-deployment-and-spark-test-guide.md`**: Replaced CAD and course assignment scenarios with distributed systems and consensus paper test cases.
- **`Projects/README.md`**: Generalized project subfolder recommendations.

### Verification Record
- `python3 Development/scripts/candidate_audit.py`: PASSED (0 findings).
- `bash Development/scripts/pii-scanner.sh`: PASSED (0 findings).
- `python3 Development/scripts/check.py`: PASSED (all suites).
- `.venv/bin/pytest tests/`: PASSED (259 passed, 1 skipped).
- `python3 tests/harness/validation_harness.py -c .`: PASSED (0 errors, 0 warnings).

## Framework agent workflow relocation (`System/Workflows/`) & legacy workflow path cleanup — 2026-09-24

- **Agent Role**: Antigravity (Implementation & Review Worker)
- **Branch & Base Commit**: `cleanup/post-redesign-consistency` based on `19864fb751401d42fe4d56f51e8f201421418927` (working tree uncommitted; ready for review/commit).
- **Goal**: Relocate the 8 portable AI agent lifecycle workflow runbooks (`01-capture.md` through `08-continuation.md`) out of `TaskNotes/Workflows/` into `System/Workflows/`, reserve `TaskNotes/Workflows/` exclusively for the Obsidian TaskNotes Workflows companion plugin (`TaskNotes/Views/workflows.base`), and replace all legacy `chrysalis`-prefixed folder path references across the repository and test suite with `TaskNotes/`.

### Changes & Rationale
- **`System/Workflows/01-capture.md` .. `08-continuation.md`**: Moved all 8 `type: agent_workflow` definitions into `System/Workflows/`, avoiding collision with `TaskNotes/Workflows/`.
- **`TaskNotes/Workflows/README.md` & `.gitignore`**: Reserved `TaskNotes/Workflows/` for user-defined Obsidian TaskNotes Workflows plugin definitions; whitelisted `System/Workflows/**` and `TaskNotes/Workflows/README.md` while quarantining personal workflow definitions in `TaskNotes/Workflows/*` and removing legacy `chrysalis` folder ignore patterns.
- **`Development/scripts/candidate_audit.py`, `update.py`, `helpers/mdbase_helper.py`, & `System/scripts/vault_paths.py`**: Added privacy quarantine enforcement (`TaskNotes/Workflows/private.md` probe) and updater protection for personal Obsidian plugin workflows in `TaskNotes/Workflows/*` (except `README.md`), updated `ENGINE_DIRS` to deploy `System/Workflows`, replaced all `chrysalis`-prefixed path probes, destination rewrites (including encapsulated `TaskNotes/.agent/skills`), and folder resolution with `TaskNotes/`, and updated `vault_path()` in `vault_paths.py` to resolve `_templates` vs `TaskNotes/_templates` without false ambiguity while checking `Workflows` and `TaskNotes/Workflows` against `[root / rel, root / "TaskNotes" / rel]`.
- **`System/scripts/bootstrap.py`, `migrate_to_subfolder.py`, `doctor.py`, `package_golem_bundle.py`, `setup_golem.ps1`**: Updated scaffolding, bundle packaging (including `TaskNotes/Workflows/README.md` without walking quarantined `TaskNotes/Workflows/*`), and migration scripts to use `TaskNotes` as the default encapsulation subfolder, provision `System/Workflows/` and `Workflows/`, migrate `.agent/skills/`, prevent self-referential `TaskNotes -> TaskNotes` symlink creation in `setup_backward_compatibility()`, leave Obsidian plugin workflows in `TaskNotes/Workflows/`, and deduplicate legacy `type: agent_workflow` notes when `System/Workflows/` already exists.
- **`mdbase.yaml` & `TaskNotes/Views/workflows.base`**: Added `TaskNotes/Workflows` and `Workflows` to `mdbase.yaml` exclusions and `runtime_workflow` support to `workflows.base`.
- **`tests/` (`test_mdbase_v03_milestone2.py`, `test_migrate_to_subfolder.py`, `test_deployment.py`, `test_candidate_audit.py`, `test_challenger_gate1_adversarial.py`, `test_challenger_gate2_adversarial.py`, `test_zettel_graph_linker.py`, `tests/harness/engine_validator.py`, `tests/e2e/*`)**: Updated portable workflow, deployment, migration, audit, and E2E tests to use `TaskNotes/` instead of legacy `chrysalis`-prefixed folder paths.
- **Documentation & Constitutions (`AGENTS.md`, `ARCHITECTURE.md`, `STATUS.md`, `README.md`, `System/Runtime-Constitution.md`, `Development/Development-Constitution.md`, `Development/BEGINNERS-GUIDE.md`, `Development/skills/evolve/SKILL.md`, `contracts/agent-runtime.contract.md`, `docs/staged-migration-plan.md`, `docs/golem-deployment-and-spark-test-guide.md`, `Development/archive/HANDOFF-HISTORICAL.md`)**: Updated all directory diagrams, constitutional path inventories, and historical notes to use `System/Workflows` and `TaskNotes/Workflows`.

### Verification Record & Environment Limitations
- `python3 Development/scripts/candidate_audit.py`: PASSED (`passed: true`, 0 findings).
- `bash Development/scripts/pii-scanner.sh`: PASSED (`passed: true`, 0 findings).
- `python3 Development/scripts/check.py`: PASSED (all suites: `candidate-privacy`, `dependencies`, `pip-consistency`, `framework`, `validation-harness`, `candidate-unchanged`).
- `.venv/bin/pytest tests/`: PASSED (264 passed, 1 skipped).
- `python3 tests/harness/validation_harness.py -c .`: PASSED (Layer 1, 2, 3 PASS; 0 errors, 0 warnings).
- **Environment Limitations & Next Action**: Automated CLI, unit, E2E, validation harness, and privacy boundary checks were executed in the headless Linux environment; interactive Obsidian GUI rendering was not run. Next action: commit the staged and audited branch changes when ready to integrate.

## Native `mdbase` v0.1.0-beta.104 compatibility, Windows locking, & Golem deployment — 2026-09-24

- **Agent Role**: Antigravity (Architecture Review & Deployment Worker)
- **Goal**: Review the redesigned pure-AI-agent framework architecture, verify compatibility with the official `mdbase-connect` `v0.1.0-beta.104` standalone headless CLI/daemon on Windows 11 ARM64, and deploy the runtime vault (`Documents/Chrysalis`) and `mdbase connect` daemon.

### Changes & Rationale
- **`_contracts/task.contract.md`, `project.contract.md`, `zettel.contract.md`, `source.contract.md`, & `tests/test_mdbase_v03_milestone2.py`**: Updated `_contracts/*.contract.md` frontmatter to strictly satisfy the embedded `https://mdbase.dev/schemas/v0.3/data-contract.schema.json` specification in `mdbase` v0.1.0-beta.104 (`contract_type: record`, `x-target-type`, and `record_schema` wrapper), enabling native `mdbase validate` to pass with zero errors.
- **`mdbase.yaml`**: Expanded `settings.exclude` to exclude non-record templates, documentation, and root markdown files (`Slipbox/README.md`, `Slipbox/_templates`, `Projects/README.md`, `Projects/_templates`, `TaskNotes/_templates`, `TaskNotes/Archive`, `TaskNotes/Views`, `contracts`, `docs`, `fixtures`, `helpers`, `.agent`) from native `mdbase validate` and `mdbase query` scans.
- **`helpers/mdbase_helper.py`**: Added cross-platform Windows file locking fallback (`msvcrt.locking` + in-process per-path `threading.Lock`) when `fcntl` is unavailable on Windows, ensuring multi-threaded and cross-process CAS contention (`test_apply_cas_mutation_multi_threaded_concurrency`) passes natively on Windows.
- **`update.py`**: Updated `fingerprint()` and added `merge_mdbase_connect_metadata()` so runtime vault `x-mdbase-connect` metadata added by `mdbase connect collection add` is preserved across `update.py` deployments without triggering false local-modification errors.
- **`docs/golem-deployment-and-spark-test-guide.md`**: Updated Sections 4 and 5.1 to reflect `mdbase-connect` `v0.1.0-beta.108` (`protocol_version: 5`) headless daemon installation (`SHA256SUMS` verification, `mdbase connect daemon install`, Task Scheduler battery/timeout hardening, `mdbase connect collection add`, `mdbase connect login`), plus the Gemini Spark OAuth 2.1 `state` (`<=1000` chars) & CLI `mdbase connect access approve` procedure.

### Verification Record & Next Action
- `powershell -File System/scripts/setup_golem.ps1`: PASSED (`Layer 1, 2, 3 PASS; 0 errors, 0 warnings`).
- `python System/scripts/doctor.py`: PASSED (`System health HEALTHY, 0 errors`).
- `mdbase validate` & `mdbase connect collection validate`: PASSED (`{"diagnostics":[],"result":{},"valid":true}`).
- `mdbase connect status --json`: PASSED (`binary_version: 0.1.0-beta.108`, `protocol_version: 5`, `state: connected`, `registered_collections: 1`).
- **Gemini Spark MCP Integration**: CONNECTED & ACTIVE (`@Mdbase` synced via `https://mcp.mdbase.dev/mcp` with capability grant approved via `mdbase connect access approve`).
- `python -m unittest tests/test_mdbase_v03_milestone2.py tests/test_worked_scenario.py tests/test_failure_modes.py tests/test_validation_harness.py`: PASSED (62 tests in 1.30s).
- **Historical Next Action (Superseded 2026-09-27)**: Previously planned to test Gemini Spark with `docs/spark-agent-system-prompt.md` and `docs/golem-deployment-and-spark-test-guide.md`; superseded by the 2026-09-27 Gemini Spark retirement below.

## Dedicated `/ingest` Skill, Google Drive Media Locker & Workflows 01–04 Alignment — 2026-09-26

- **Agent Role**: Antigravity (Implementation & Deployment Worker)
- **Goal**: Establish Google Drive as the exclusive storage substrate for original binary/source files (eliminating any local `Resources/` folder inside the Chrysalis vault), create a dedicated `/ingest` skill (`.agent/skills/ingest/SKILL.md`), integrate automatic Google Drive folder ingestion (`/ingest --drive`) into the nightly `/audit` (`/evening`), support direct-share ingestion in the agent UI (`/ingest`), align `/project` and `/zettel` with `System/Workflows/01-capture.md` through `04-organize.md` prior to `/plan` (`05-plan.md`), and deploy to both source and active runtime vaults.

### Changes & Rationale
- **`.agent/skills/ingest/SKILL.md`**: Created the dedicated `/ingest` runtime skill governing **Protocol 1: Automated Nightly Google Drive Batch Ingestion (`/ingest --drive`)** (`Chrysalis-Media-Locker/01-Inbox` $\to$ `02-Archived-Binaries`) and **Protocol 2: User-Directed Direct Share in Agent UI (`/ingest` / `--share`)**, executing Workflows `01-capture` through `04-organize` (`sha256` deduplication, `<untrusted_document_payload>` quarantine, `reconcile_syllabus()`, 3-Way 14-day/uncertain horizon partitioning) and aligning `/project` + `/zettel` before handing off to `/plan`.
- **`.agent/skills/audit/SKILL.md` & `.agent/skills/evening/SKILL.md`**: Updated Protocol 1 (`Unified Nightly Audit`) to automatically call `/ingest --drive` before Multi-Project & Roadmap Horizon Ingestion and `/plan`.
- **`.agent/skills/project/SKILL.md`, `.agent/skills/zettel/SKILL.md`, & `.agent/skills/plan/SKILL.md`**: Aligned frontmatter schemas (`source_ref`, `source_checksum`, `source_url`, `project_ref`, `linked_zettels`, `deliverables` YAML array) and workflows with `01-capture.md`–`04-organize.md` and `05-plan.md`, removing all local `Resources/` directory scaffolding.
- **`System/_templates/Memory.template.md`, `System/Memory.md`, `Projects/README.md`, `System/Runtime-Constitution.md`, & `docs/data-ingestion-guide.md`**: Added `ingestion_config` (`drive_inbox_folder`, `drive_archive_folder`, `auto_ingest_on_nightly_audit: true`, `local_resources_folder_enabled: false`) and updated prompts and playbooks.
- **`update.py`, `System/scripts/bootstrap.py`, `Development/scripts/candidate_audit.py`, & `tests/test_deployment.py`**: Protected personal `Sources/` records during updates and privacy audits, provisioned `Sources/` in `bootstrap.py`, and deployed to the active runtime vault.

> Historical handoff receipts from prior engineering cycles (2026-09-14 through 2026-09-22) have been partitioned to [archive/HANDOFF-HISTORICAL.md](archive/HANDOFF-HISTORICAL.md).

## Windows source checkout recovery — 2026-09-26

Codex recovered the existing copied source tree as a normal `main` checkout based on `19864fb751401d42fe4d56f51e8f201421418927`, preserving a separate private backup before replacing the stale Linux worktree pointer. Existing unpublished cleanup, workflow relocation, ingestion, native mdbase compatibility and updater changes remain staged for review/publication. This does not retrieve uncommitted work that exists only on another workstation.

This session removed a machine-specific path from `docs/spark-agent-system-prompt.md` and normalized trailing whitespace in `tests/test_deployment.py`. Personal runtime settings and task notes were not copied into the source candidate. The direct Python candidate audit passed with zero findings after staging; `git diff --cached --check` passed. The three-layer local validation harness passed with zero errors/warnings. The full `Development/scripts/check.py` runner refused Windows as documented; Linux verification remains required. Direct Windows pytest ran 278 tests: 277 passed initially; the audit test that observed the old index before staging passed on its isolated rerun (1 passed). All 110 subtests passed. This is Windows evidence, not a completed pinned Linux check.

The runtime updater dry run matched the recovered source before this session's documentation edits. No runtime deployment was applied in this session. GitHub CLI authentication completed with the user-approved account and a private noreply commit identity. The publication candidate is based on the unchanged remote main; final commit/push and deployment receipts are kept outside the public tree. Next: complete the pinned Linux check on a supported host and retain the Windows verification limitation; deploy published framework changes through the protected updater. Do not override local runtime conflicts or publish private installation receipts.

## End-to-End Simplification & Gemini Spark Retirement — 2026-09-27

- **Agent Role**: Antigravity (Architecture Simplification & Deployment Worker)
- **Goal**: Retire all bespoke Gemini Spark and Golem cloud-relay workarounds, evaluate and record the default agent access layer (`A2` — Direct Local Vault Access + Local Validation & CAS Tooling), simplify `update.py` to prune obsolete Spark/Golem/Skills artifacts during upgrades while preserving personal data and custom `.agent/skills.json` entries, publish the validated changes, and rebuild the personal runtime installation via the protected updater.

### Changes & Rationale
- **Retired Gemini Spark & Golem Artifacts (`git rm`)**: Removed `.agent/skills/chrysalis-router/SKILL.md`, `docs/spark-agent-system-prompt.md`, `docs/golem-deployment-and-spark-test-guide.md`, `Development/SPARK-INTEGRATION-ASSESSMENT.md`, `System/scripts/package_golem_bundle.py`, and `System/scripts/setup_golem.ps1`.
- **Access-Layer Decision (`ARCHITECTURE.md` & `STATUS.md`)**: Recorded the architectural comparison of Direct Local Vault Access (`A1`), Direct Local Vault Access + Local Validation & CAS Tooling (`A2`), Local `mdbase` MCP (`B1`), and Remote `mdbase connect` Relay (`B2`). Selected `A2` (`helpers/mdbase_helper.py` + headless `mdbase -C <vault>` CLI + `tests/harness/validation_harness.py`) as the default architecture for capable local coding agents (Antigravity, Codex, Claude Code).
- **`update.py` & `.agent/skills.json`**: Removed `sync_skill_hardlinks()` (stopping creation of `Skills/*/SKILL.md` hardlinks and `Skills/bundle/SKILL.md`), added `RETIRED_FRAMEWORK_ARTIFACTS` and `obsolete_framework_paths()` with hardlink-safe pre-write unlinking, backup, and rollback support, and updated `.agent/skills.json` (`entries`: `.agent/skills`, `Development/skills`) with non-destructive updater merge logic.
- **Runtime Skills, Constitutions & Guides**: Removed Spark/router references from `.agent/skills/{ingest,audit,evening,project,zettel}/SKILL.md`, `docs/data-ingestion-guide.md`, `contracts/agent-runtime.contract.md`, `AGENTS.md`, `System/Runtime-Constitution.md`, `Development/Development-Constitution.md`, and `Development/BACKLOG.md`.
