---
type: agent_workflow
id: workflow-05-plan
version: "1.0.0"
stage: plan
lifecycle_state_ref: PLAN_PROPOSAL
requires_approval: false
inputs:
  - roadmap_deliverables
  - memory_horizons
outputs:
  - active_tasks_to_create
  - inert_deliverables
  - staged_sprint_blocks
---

# Workflow 05: Horizon Evaluation & Staging

## Objective
Enforce the cognitive 14-day horizon boundary. Materialize near-term deliverables into actionable task notes while preserving long-term deliverables as inert entries in the roadmap ledger.

## Protocol Steps
1. **Horizon Partitioning**:
   - Call `helpers.mdbase_helper.filter_horizon_deliverables(deliverables, horizon_days=14)`.
   - **Near-term (`due <= today + 14d`)**: Draft task notes in `chrysalis/Tasks/` with `status: todo`, linking back to `project_ref`.
   - **Out-of-horizon (`due > today + 14d`)**: Keep in roadmap ledger; do not generate daily tasks; set `task_ref: null`.
2. **Cognitive Modality Pairing**:
   - Assign modality based on task nature: `analytical` for problem sets, `synthesis` for essays/literature, `kinetic` for laboratory work.
3. **Uncertain Date Enforcement**: If `date_uncertain: true`, ensure `scheduled: null`.
4. **Compile Proposal**: Mint `proposal_id` and transition to `06-act.md` (Approval Gate).
