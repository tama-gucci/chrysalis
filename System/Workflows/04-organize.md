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

# Workflow 04: Hypergraph Linking & Ledger Assembly (`/ingest` Stage 4 $\leftrightarrow$ `/project` & `/zettel` $\to$ `/plan`)

## Objective
Establish bidirectional wikilinks across the 4-collection Chrysalis Hypergraph (`Sources` $\leftrightarrow$ `Projects` $\leftrightarrow$ `Slipbox` $\leftrightarrow$ `TaskNotes/Tasks`) by aligning `/project` and `/zettel` serialization prior to `/plan` (`05-plan.md`).

## Relational Matrix & Serialization Order (Local A2 Writes on `<vault>`):
1. **Source Provenance (`<vault>/Sources/{source_id}.md`)**:
   - Persist `type: source`, `sha256`, `source_url` (Google Drive link), `ingestion_status: "extracted"`, and arrays `extracted_projects`, `extracted_zettels`, and `extracted_tasks`.
2. **Knowledge Synthesis via `/zettel` (`<vault>/Slipbox/{YYYYMMDDHHmmss}-{slug}.md`)**:
   - Persist `type: zettel`, `source_ref: "[[Sources/<source_id>]]"`, `source_checksum: "<sha256>"`, `source_url`, `project_ref: "[[Projects/<project_id>/Roadmap]]"`, and `integration_status: "integrated"`.
3. **Project Roadmap Synthesis via `/project` (`<vault>/Projects/{project_id}/Roadmap.md`)**:
   - Persist `type: project_roadmap` (or `project`), `source_ref: "[[Sources/<source_id>]]"`, `source_checksum: "<sha256>"`, `linked_zettels` containing all extracted Zettels, and 100% of `deliverables` (`^[a-z0-9-]+$`). Do not create a local `Resources/` subfolder.
   - Synchronize active pillar milestones and tags into `<vault>/System/Life-Roadmap.md` (`tag_registry`) and `<vault>/System/Memory.md` (`active_horizons.active_projects`).
4. **14-Day & Uncertain Task Materialization (`<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md`)**:
   - Materialize tasks for `due <= today + 14d` and `date_uncertain: true` deliverables with `project_ref: "[[Projects/<project_id>/Roadmap]]"`, `deliverable_id`, `linked_zettels`, and `scheduled: null`, backfill `task_ref` in `<vault>/Projects/{project_id}/Roadmap.md`, run `python System/scripts/zettel_graph_linker.py --vault "<vault>" --sync`, and validate records via `python helpers/mdbase_helper.py --vault "<vault>" validate <path>`.
5. **State Transition**: Transition immediately to `05-plan.md` (`/plan`).
