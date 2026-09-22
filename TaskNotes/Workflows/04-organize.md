---
type: agent_workflow
id: workflow-04-organize
version: "1.0.0"
stage: organize
lifecycle_state_ref: PLAN_PROPOSAL
requires_approval: false
inputs:
  - syllabus_diff
  - source_id
  - project_id
outputs:
  - roadmap_payload
  - linked_zettel_payloads
---

# Workflow 04: Hypergraph Linking & Ledger Assembly

## Objective
Establish bidirectional wikilinks across the Chrysalis Hypergraph (Source <-> Project <-> Zettels) and compile the complete master deliverable ledger.

## Relational Matrix:
- Set `project.source_ref = "[[Sources/<source_id>]]"`.
- Set `project.source_checksum = "<sha256>"`.
- Link all extracted zettels to `project.linked_zettels`.
- For each deliverable in `project.deliverables`, assign stable ID (`^[a-z0-9-]+$`).
- State Transition: Transition to `05-plan.md`.
