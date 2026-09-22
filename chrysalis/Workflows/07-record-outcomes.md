---
type: agent_workflow
id: workflow-07-record-outcomes
version: "1.0.0"
stage: record_outcomes
lifecycle_state_ref: OUTCOME_RECORDING
requires_approval: false
inputs:
  - session_telemetry
  - completed_tasks
outputs:
  - memory_update_result
  - source_status_update
---

# Workflow 07: Outcome Recording & Adaptive Learning

## Objective
Record focus session outcomes, update dynamic cognitive multipliers bounded in $[0.20, 2.00]$, transition source statuses, and append to the session history ledger.

## Protocol Steps
1. **Calculate Multiplier Adjustment**:
   - For completed task with duration telemetry ($T_{\text{actual}} = \text{completedAt} - \text{startedAt}$):
     $$\text{Multiplier}_{\text{new}} = \text{Multiplier}_{\text{current}} + 0.10 \times \left(\frac{T_{\text{actual}}}{T_{\text{estimated}}} - \text{Multiplier}_{\text{current}}\right)$$
   - Clamp multiplier strictly to $[0.20, 2.00]$.
2. **Update Persistent Memory**:
   - Update `System/Memory.md` modality multipliers and append session outcome entry to ledger.
3. **Update Source Ingestion Status**:
   - Set `Sources/<id>.md` `ingestion_status` from `raw` to `extracted` or `reconciled`.
4. **State Transition**: Transition to `08-continuation.md`.
