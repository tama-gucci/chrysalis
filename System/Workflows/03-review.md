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
Arbitrate extracted candidate entities against existing collection state, execute syllabus reconciliation diffing (`reconcile_syllabus`), partition deliverables across the 14-day planning horizon (`filter_horizon_deliverables`), and present the `PlanProposal` at `APPROVAL_GATE`.

## Protocol Steps
1. **Locate Existing Roadmap**: Search `<vault>/Projects/{project_id}/Roadmap.md` (`python System/scripts/vault_paths.py --runtime --json`).
2. **Execute Reconciliation Algorithm (`/project` Alignment via A2)**:
   - Call `python helpers/mdbase_helper.py --vault "<vault>" reconcile-syllabus "<vault>/Projects/{project_id}/Roadmap.md" <deliverables_file>` (`helpers.mdbase_helper.reconcile_syllabus(existing_roadmap_path, candidate_deliverables)`).
   - Categorize items into:
     - `modified`: Existing deliverables whose `due` date, `date_uncertain`, or `title` shifted (preserving existing `task_ref`).
     - `added`: New deliverables present in the new source.
     - `dropped`: Existing deliverables missing in the new source $\to$ transition status to `status: archived` (never delete).
3. **3-Way Horizon Partition (`python helpers/mdbase_helper.py --vault "<vault>" horizon-tasks` / `filter_horizon_deliverables(horizon_days=14)`)**:
   - **Imminent (`due <= today + 14d`)**: Stage for `<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md` creation and `/plan` sprint scheduling.
   - **Uncertain (`due: null, date_uncertain: true`)**: Stage for `<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md` creation with `scheduled: null` to prompt deadline clarification without auto-scheduling.
   - **Out-of-Horizon (`due > today + 14d`)**: Retain 100% in `<vault>/Projects/{project_id}/Roadmap.md` (`deliverables` ledger with `task_ref: null`); do not create daily task notes yet.
4. **Formulate Plan Proposal (`APPROVAL_GATE`)**: Assemble structured `PlanProposal` detailing `<vault>/Sources/{source_id}.md`, `<vault>/Projects/{project_id}/Roadmap.md` diffs, `<vault>/Slipbox/` Zettels, and 14-day/uncertain `<vault>/TaskNotes/Tasks/` files for mandatory human confirmation.
5. **State Transition**: Transition to `04-organize.md`.
