---
name: audit
description: "Runtime Operational Audit: Unified nightly system reconciliation: executes pre-flight integrity pass via /doctor, updates telemetry multiplier learning bounded in [0.20, 2.00], chronotype delta learning, multi-project and roadmap horizon ingestion, starter wedge injection, dynamic task selection, and auto-pause evaluation."
trigger: "/audit"
domain: runtime
reads:
  - "Sources/*.md"
  - "TaskNotes/Tasks/*.md"
  - "TaskNotes/Archive/*.md"
  - "Projects/*/Roadmap.md"
  - "Slipbox/*.md"
  - "System/Memory.md"
  - "System/Life-Roadmap.md"
  - "System/System-Health.md"
  - ".agent/skills/ingest/SKILL.md"
writes:
  - "Sources/*.md"
  - "Projects/*/Roadmap.md"
  - "Slipbox/*.md"
  - "System/Memory.md"
  - "System/Life-Roadmap.md"
  - "TaskNotes/Tasks/*.md"
  - "Dashboard.md"
---

> Paths below are relative to the resolved personal runtime vault (`<vault>`). The default layout keeps `System/`, `Projects/`, `Slipbox/`, and `Sources/` at the root and operational task folders under `TaskNotes/`. See `ARCHITECTURE.md`.


# /audit (Runtime Operational Audit & Nightly Reconciliation Engine)

## A2 Access Layer & Runtime Vault Resolution (Platform-Agnostic)

1. **Resolve `<vault>` (Personal Runtime Vault):**
   * Run `python System/scripts/vault_paths.py --runtime --json` (or use `$CHRYSALIS_VAULT_PATH` / `$CHRYSALIS_VAULT_ROOT`). When invoked from the framework source checkout, this automatically resolves to `~/Documents/Chrysalis` so personal life operations never mutate synthetic source files.
2. **Execute via the A2 Access Layer:**
   * All vault reads, queries, and mutations across Google Antigravity, OpenAI Codex, Claude Code, and local CLI agents operate directly on `<vault>` using standard local file/editor tools paired with `helpers/mdbase_helper.py` (`horizon-tasks`, `validate`, `revision`, `check-duplicate`, `apply_cas_mutation`), headless `mdbase -C "<vault>" query/validate`, and `python System/scripts/doctor.py --vault "<vault>"`.

## Supported Commands & Triggers
* `/audit` (or `/audit --nightly`) — Executes the complete nightly operational reconciliation lifecycle (including automatic Google Drive folder ingestion via `/ingest --drive`).
* `/audit --integrity` (or `/audit --health`) — Executes the 6-point pre-flight integrity suite (delegated directly to [`doctor`](../doctor/SKILL.md)).
* `/audit --mutate` — On-demand approved roadmap milestone updates.

---

## Protocol 0: Full System Integrity & Diagnostic Suite (`/audit --integrity` or `/audit --health`)

> [!NOTE]
> Protocol 0 delegates directly to the canonical diagnostic skill [`doctor`](../doctor/SKILL.md) (`python System/scripts/doctor.py --vault "<vault>"`). Calling `/audit --integrity` or `/audit --health` executes the 6-point integrity suite from `/doctor` without triggering the nightly learning lifecycle.

---

## Protocol 1: Unified Nightly Audit (`/audit` or `/audit --nightly`)

Execute this sequence when explicitly invoked in an interactive session. The `--nightly` spelling is a compatibility alias; it does not schedule a background job. Obtain approval before proposed mutations.

### Step 0: Mandatory Pre-Flight Health Pass (Delegated to `/doctor`)
Execute the full 6-point diagnostic pass defined in [`doctor`](../doctor/SKILL.md) (`python System/scripts/doctor.py --vault "<vault>"`). If critical unrecoverable corruption is found, halt execution and alert user. Otherwise, apply auto-heals and proceed to Step 1.

### Step 1: Task Lifecycle, Multipliers & Chronotype Delta Learning
1. Scan `<vault>/TaskNotes/Tasks/*.md` (with `status: done`) and `<vault>/TaskNotes/Archive/*.md` for tasks completed in the preceding 24 hours.
2. Extract exact session durations: $T_{\text{actual}} = \text{completedAt} - \text{startedAt}$ (in minutes).
3. Read `cognitive_modality_defaults.<modality>.multiplier` in `<vault>/System/Memory.md` and apply the deterministic feedback rule defined in `System/Workflows/07-record-outcomes.md` (`helpers.mdbase_helper.calculate_dynamic_multiplier`), clamped to $[0.20, 2.00]$.
4. Use the outcome ledger to avoid applying the same session feedback twice. Missing or invalid timestamps require review before learning.
5. After approval, persist modality multipliers, session metrics, outcome evidence, and `last_updated` to `<vault>/System/Memory.md` via local file mutation tools / `apply_cas_mutation`. Learning occurs only from completed sessions; do not apply passive decay.

### Step 2: Automated Google Drive Folder Ingestion (Delegated to `/ingest --drive`)
Automatically invoke [`/ingest --drive`](../ingest/SKILL.md) (**Protocol 1: Automated Nightly Google Drive Batch Ingestion**) to ingest unindexed files in the dedicated Google Drive folder (`ingestion_config.drive_inbox_folder` in `<vault>/System/Memory.md`, defaulting to `Chrysalis-Media-Locker/01-Inbox`):
1. **Scan & Deduplicate (`01-capture.md`):**
   * Run `python helpers/mdbase_helper.py --runtime drive-inbox` to inspect `Chrysalis-Media-Locker/01-Inbox` config, already-indexed `<vault>/Sources/*.md` digests, and any local Google Drive mount, and list files in `Chrysalis-Media-Locker/01-Inbox` via the **connected Google Drive MCP server** (in Antigravity, OpenAI Codex, or Claude Code) or **local Google Drive mount**.
   * Compute `sha256` over each file's extracted content and check `<vault>/Sources/*.md` via `python helpers/mdbase_helper.py --runtime check-duplicate --text "<content>" --source-url "<url>"` (or `check-duplicate <file>` / `mdbase -C "<vault>" query --types source`). Skip files already recorded in `<vault>/Sources/*.md`.
   * If the Google Drive MCP server / local Drive mount is not currently connected or `01-Inbox` contains 0 unindexed files, log an informational notice and proceed cleanly to Step 3.
2. **Translate & Align Locally via A2 (`02-extract.md` $\to$ `04-organize.md`):**
   * Translate each new or revised source into formatted Markdown (`<vault>/Sources/{source_id}.md` with `<untrusted_document_payload>` quarantine and `source_url`), align `/project` (`<vault>/Projects/{project_id}/Roadmap.md` with 100% of deliverables and `reconcile_syllabus()`) and `/zettel` (`<vault>/Slipbox/{YYYYMMDDHHmmss}-{slug}.md`), and materialize 14-day/uncertain tasks in `<vault>/TaskNotes/Tasks/` after `APPROVAL_GATE`. All original binary files remain in Google Drive (`Chrysalis-Media-Locker/02-Archived-Binaries`); no local `Resources/` folder is created in `<vault>`.

### Step 3: Multi-Project & Roadmap Horizon Ingestion
1. **Project Roadmap Synchronization:** Crawl `<vault>/Projects/*/Roadmap.md` (including roadmaps newly created or updated in Step 2). Sync completed deliverables and status back into `<vault>/System/Life-Roadmap.md`.
2. **Milestone Progress Reconciliation:** Cross-reference completed tasks in `<vault>/TaskNotes/Archive/` with active milestones. Mark corresponding key results (`- [x]`) as complete.
3. **14-Day Horizon Ingestion:**
   * Run `python helpers/mdbase_helper.py --vault "<vault>" horizon-tasks` (and scan `<vault>/System/Life-Roadmap.md` + `<vault>/Projects/*/Roadmap.md`) for upcoming milestones and deliverables occurring within the next 14 calendar days (plus `date_uncertain: true, due: null` deliverables) lacking active task notes (`task_ref: null`).
   * Calculate each task's `timeEstimate` using the modality multiplier from `<vault>/System/Memory.md` (applying the `1.00` fallback rule if unlisted).
   * Create structured `.md` files in `<vault>/TaskNotes/Tasks/` via the A2 access layer with complete YAML frontmatter (`dateCreated`, `created`, `priority`, `urgency_tier`, `modality`, `status: todo`, `scheduled: null`, `linked_zettels`, `project_ref`, `deliverable_id`, `googleCalendarEventId: null`), and validate each new record with `python helpers/mdbase_helper.py --vault "<vault>" validate <path>`.

### Step 4: Friction Reduction & Starter Wedge Injection
Scan active tasks in `<vault>/TaskNotes/Tasks/` for stalled items ($\ge 48\text{h}$ in `status: todo` with `timeEstimate >= 45m` and `micro_chunked: false`). Inject a 3-step Starter Wedge checklist ($< 15\text{m}$ each) into the note body and set `micro_chunked: true`.

### Step 5: Dynamic Task Selection & Handoff to `/plan`
Query actual task notes and project deliverables within the planning horizon on `<vault>` (via `mdbase -C "<vault>" query` or `python helpers/mdbase_helper.py --vault "<vault>" list --type task`, including newly ingested 14-day tasks from Step 2 and Step 3). Present eligible unscheduled work using user preferences from `<vault>/System/Memory.md` and hand off directly to [`/plan`](../plan/SKILL.md) (`05-plan.md`). Keep proposals in the current planning state until reviewed; do not create a separate inferred task pool.

### Step 6: Auto-Pause Evaluation
If `prototype_schedule.feedback_status == "pending"` from the previous cycle without user response and system is not already under an active manual pause (`system_state.pause_state.is_paused == false`):
* Set `system_state.pause_state.is_paused: true`, `mode: "auto_unresponsive"`, and `reason: "unresponsive_nightly_audit"` in `<vault>/System/Memory.md`.
* Preserve learned multipliers while planning is paused.

---

## Protocol 2: Roadmap Updates (`/audit --mutate`)
Triggered on-demand when `/plan` receives user feedback requiring structural system changes:
1. **Roadmap Mutations:** Append, modify, or re-scope milestones and horizons directly in `<vault>/System/Life-Roadmap.md` and relevant `<vault>/Projects/*/Roadmap.md` via the A2 access layer.
2. **Planning Candidates:** Query current task notes and deliverables on `<vault>` again after approved roadmap changes.
