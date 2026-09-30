---
type: agent_workflow
id: workflow-03-review
version: "1.0.0"
stage: review
lifecycle_state_ref: PLAN_PROPOSAL
requires_approval: false
inputs:
  - candidate_deliverables
  - target_project_id
outputs:
  - syllabus_diff
  - proposal_summary
---

# Workflow 03: Review & Revision Reconciliation (`/ingest` Stage 3 $\leftrightarrow$ `/project`)

## Objective
Arbitrate extracted candidate entities and captured tasks against existing collection state, execute syllabus reconciliation diffing (`reconcile_syllabus`), partition deliverables and standalone task captures across the 14-day planning horizon (`filter_horizon_deliverables`), and prevalidate the `PlanProposal` at `APPROVAL_GATE`.

## Protocol Steps
1. **Locate Existing Roadmap**: Search `<vault>/Projects/{project_id}/Roadmap.md` (`python System/scripts/vault_paths.py --runtime --json`).
2. **Execute Additive Multi-Source Reconciliation (`/project` Alignment via A2)**:
   - Call `python helpers/mdbase_helper.py --vault "<vault>" reconcile-syllabus "<vault>/Projects/{project_id}/Roadmap.md" <deliverables_file>` (`reconcile_project_deliverables` / `reconcile_syllabus`).
   - Supplementary ingestion is additive by default (`mode="supplementary"`). Missing deliverables are marked `dropped` (`status: archived`) ONLY when `authoritative_replacement=True` for the same `source_scope`.
   - Empty, failed, or partial extraction (`extraction_status in {"empty", "failed", "partial"}`) never implies deletion.
   - Completed (`done`), `archived`, and `user_modified` deliverables, as well as existing `task_ref` links, are strictly preserved.
3. **Horizon & Deadline Partition (`python helpers/mdbase_helper.py --vault "<vault>" horizon-tasks` / `classify_deliverable_horizons(horizon_days=14)`)**:
   - **Overdue (`due < today`)**: Stage for task materialization/review with `review_required: true` and `scheduled: null`.
   - **Imminent (`today <= due <= today + 14d`)**: Stage for `<vault>/TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` creation (`scheduled: null`) and `/plan` sprint scheduling.
   - **Uncertain (`due: null, date_uncertain: true`)**: Stage for `<vault>/TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` creation with `scheduled: null` to prompt deadline clarification without auto-scheduling.
   - **Future Project Deliverables (`due > today + 14d`, linked to a `Projects/<project_id>/Roadmap.md`)**: Retain 100% in `<vault>/Projects/{project_id}/Roadmap.md` (`task_ref: null`); do not create daily task notes yet.
   - **Standalone Future Task Captures (`due > today + 14d`, `project_ref: null`, captured via `structured_task`)**: Materialize as an inert task note in `<vault>/TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` with `scheduled: null` and `horizon_bucket: "future"` so captured reminders with no parent project roadmap are never dropped or prematurely time-blocked.
   - **Excluded (`status in {"done", "archived"}`)**: Never reopen or recreate tasks for completed or archived items.
4. **Prevalidate Proposal Before Approval (`APPROVAL_GATE`)**:
   - Run `python helpers/mdbase_helper.py --vault "<vault>" prevalidate-proposal <proposal.json>` (`prevalidate_ingestion_proposal`) to verify schemas, timezones, pillar/task tags, `scheduled: null`, and cross-references before requesting user approval.
5. **State Transition**: Transition to `04-organize.md`.
