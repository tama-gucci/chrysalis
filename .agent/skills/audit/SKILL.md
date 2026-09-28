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

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under TaskNotes/. See ARCHITECTURE.md.


# /audit (Runtime Operational Audit & Nightly Reconciliation Engine)

## Supported Commands & Triggers
* `/audit` (or `/audit --nightly`) — Executes the complete nightly operational reconciliation lifecycle (including automatic Google Drive folder ingestion via `/ingest --drive`).
* `/audit --integrity` (or `/audit --health`) — Executes the 6-point pre-flight integrity suite (delegated directly to [`doctor`](../doctor/SKILL.md)).
* `/audit --mutate` — On-demand approved roadmap milestone updates.

---

## Protocol 0: Full System Integrity & Diagnostic Suite (`/audit --integrity` or `/audit --health`)

> [!NOTE]
> Protocol 0 delegates directly to the canonical diagnostic skill [`doctor`](../doctor/SKILL.md). Calling `/audit --integrity` or `/audit --health` executes the 6-point integrity suite from `/doctor` without triggering the nightly learning lifecycle.

---

## Protocol 1: Unified Nightly Audit (`/audit` or `/audit --nightly`)

Execute this sequence when explicitly invoked in an interactive session. The `--nightly` spelling is a compatibility alias; it does not schedule a background job. Obtain approval before proposed mutations.

### Step 0: Mandatory Pre-Flight Health Pass (Delegated to `/doctor`)
Execute the full 6-point diagnostic pass defined in [`doctor`](../doctor/SKILL.md). If critical unrecoverable corruption is found, halt execution and alert user. Otherwise, apply auto-heals and proceed to Step 1.

### Step 1: Task Lifecycle, Multipliers & Chronotype Delta Learning
1. Scan `TaskNotes/Tasks/*.md` (with `status: done`) and archive folders for tasks completed in the preceding 24 hours.
2. Extract exact session durations: $T_{\text{actual}} = \text{completedAt} - \text{startedAt}$ (in minutes).
3. Read `cognitive_modality_defaults.<modality>.multiplier` and apply the deterministic feedback rule defined in `System/Workflows/07-record-outcomes.md`, clamped to $[0.20, 2.00]$.
4. Use the outcome ledger to avoid applying the same session feedback twice. Missing or invalid timestamps require review before learning.
5. After approval, persist modality multipliers, session metrics, outcome evidence, and `last_updated` to `System/Memory.md`. Learning occurs only from completed sessions; do not apply passive decay.

### Step 2: Automated Google Drive Folder Ingestion (Delegated to `/ingest --drive`)
Automatically invoke [`/ingest --drive`](../ingest/SKILL.md) (**Protocol 1: Automated Nightly Google Drive Batch Ingestion**) to ingest unindexed files in the dedicated Google Drive folder (`ingestion_config.drive_inbox_folder` in `System/Memory.md`, defaulting to `Chrysalis-Media-Locker/01-Inbox`):
1. **Scan & Deduplicate (`01-capture.md`):** List all files in the dedicated Google Drive inbox folder, compute `sha256` over the extracted content, and skip files already recorded in `Sources/*.md`. All original binary files remain in Google Drive (`Chrysalis-Media-Locker/02-Archived-Binaries`); no local `Resources/` folder is used in the vault.
2. **Translate & Align (`02-extract.md` $\to$ `04-organize.md`):** Translate each new or revised source into formatted Markdown (`Sources/{source_id}.md` with `<untrusted_document_payload>` quarantine and `source_url`), align `/project` (`Projects/{project_id}/Roadmap.md` with 100% of deliverables and `reconcile_syllabus()`) and `/zettel` (`Slipbox/{YYYYMMDDHHmmss}-{slug}.md`), and materialize 14-day/uncertain tasks after `APPROVAL_GATE`.

### Step 3: Multi-Project & Roadmap Horizon Ingestion
1. **Project Roadmap Synchronization:** Crawl `Projects/*/Roadmap.md` (including roadmaps newly created or updated in Step 2). Sync completed deliverables and status back into `System/Life-Roadmap.md`.
2. **Milestone Progress Reconciliation:** Cross-reference completed tasks in `TaskNotes/Archive/` with active milestones. Mark corresponding key results (`- [x]`) as complete.
3. **14-Day Horizon Ingestion:**
   * Scan `Life-Roadmap.md` and active project roadmaps for upcoming milestones and deliverables occurring within the next 14 calendar days (plus `date_uncertain: true, due: null` deliverables) lacking active task notes.
   * Calculate each task's `timeEstimate` using the modality multiplier from `System/Memory.md` (applying the `1.00` fallback rule if unlisted).
   * Create structured `.md` files in `TaskNotes/Tasks/` with complete YAML frontmatter (`dateCreated`, `created`, `priority`, `urgency_tier`, `modality`, `status: todo`, `scheduled: null`, `linked_zettels`, `project_ref`, `deliverable_id`, `googleCalendarEventId: null`).

### Step 4: Friction Reduction & Starter Wedge Injection
Scan active tasks in `TaskNotes/Tasks/` for stalled items ($\ge 48\text{h}$ in `status: todo` with `timeEstimate >= 45m` and `micro_chunked: false`). Inject a 3-step Starter Wedge checklist ($< 15\text{m}$ each) into the note body and set `micro_chunked: true`.

### Step 5: Dynamic Task Selection & Handoff to `/plan`
Query actual task notes and project deliverables within the planning horizon (including newly ingested 14-day tasks from Step 2 and Step 3). Present eligible unscheduled work using user preferences from `System/Memory.md` and hand off directly to [`/plan`](../plan/SKILL.md) (`05-plan.md`). Keep proposals in the current planning state until reviewed; do not create a separate inferred task pool.

### Step 6: Auto-Pause Evaluation
If `prototype_schedule.feedback_status == "pending"` from the previous cycle without user response and system is not already under an active manual pause (`system_state.pause_state.is_paused == false`):
* Set `system_state.pause_state.is_paused: true`, `mode: "auto_unresponsive"`, and `reason: "unresponsive_nightly_audit"`.
* Preserve learned multipliers while planning is paused.

---

## Protocol 2: Roadmap Updates (`/audit --mutate`)
Triggered on-demand when `/plan` receives user feedback requiring structural system changes:
1. **Roadmap Mutations:** Append, modify, or re-scope milestones and horizons directly in `System/Life-Roadmap.md` and relevant `Projects/*/Roadmap.md`.
2. **Planning Candidates:** Query current task notes and deliverables again after approved roadmap changes.
