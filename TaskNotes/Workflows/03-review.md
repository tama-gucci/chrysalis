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

# Workflow 03: Review & Revision Reconciliation

## Objective
Arbitrate extracted candidate entities against existing collection state. If updating an existing course roadmap, execute syllabus reconciliation diffing.

## Protocol Steps
1. **Locate Existing Roadmap**: Search `Projects/{project_id}/Roadmap.md`.
2. **Execute Reconciliation Algorithm**:
   - Call `helpers.mdbase_helper.reconcile_syllabus(existing_roadmap_path, new_syllabus_text)`.
   - Categorize items into:
     - `modified`: Existing deliverables whose date or title shifted.
     - `added`: New deliverables present in the new syllabus.
     - `dropped`: Existing deliverables missing in the new syllabus -> flag for archiving.
3. **Formulate Plan Proposal**: Assemble structured `PlanProposal` detailing affected files and diffs.
4. **State Transition**: Transition to `04-organize.md`.
