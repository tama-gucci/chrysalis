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
Establish bidirectional wikilinks across the 4-collection Chrysalis Hypergraph (`Sources` $\leftrightarrow$ `Projects` $\leftrightarrow$ `Slipbox` $\leftrightarrow$ `TaskNotes/Tasks`) by aligning `/project`, `/zettel`, and structured task capture serialization prior to `/plan` (`05-plan.md`).

## Relational Matrix & Serialization Order (Local A2 Writes on `<vault>`):
1. **Resumable Dependency-Ordered Persistence (`apply_ingestion_proposal`):**
   - Execute `python helpers/mdbase_helper.py --vault "<vault>" apply-proposal <proposal.json> --approved` (`apply_ingestion_proposal(vault_root, proposal, approved=True)`).
   - Writes records in dependency order (`Projects` $\to$ `Slipbox` $\to$ `TaskNotes/Tasks` $\to$ `Sources`) while recording per-file completion in `<vault>/.chrysalis/ingestion_batches/<proposal_id>.json` so retries after any mid-batch failure resume cleanly without duplicating outputs.
   - Unapproved proposals (`approved=False`) are strictly rejected and perform zero disk mutations.
   - Ingestion is strictly one-way into `<vault>`: zero write-back, deletion, or completion sync is ever performed against an external source provider (`write_back_supported: false`).
2. **Project Roadmap Synthesis via `/project` (`<vault>/Projects/{project_id}/Roadmap.md`)**:
   - Persist `type: project_roadmap` (or `project`), `source_ref: "[[Sources/<source_id>]]"`, `contributing_sources`, `reference_sources`, `supporting_assets`, `linked_zettels`, and 100% of `deliverables`. Do not create a local `Resources/` subfolder.
   - Synchronize active pillar milestones and tags into `<vault>/System/Life-Roadmap.md` (`tag_registry`) and `<vault>/System/Memory.md` (`active_horizons.active_projects`).
3. **Knowledge Synthesis via `/zettel` (`<vault>/Slipbox/{YYYYMMDDHHmmss}-{slug}.md`)**:
   - Persist `type: zettel`, `source_ref: "[[Sources/<source_id>]]"`, `source_checksum: "<sha256>"`, `source_url`, `project_ref: "[[Projects/<project_id>/Roadmap]]"`, and `integration_status: "integrated"`.
4. **Eligible & Captured Task Materialization (`<vault>/TaskNotes/Tasks/{YYYYMMDD}-{slug}.md`)**:
   - Materialize project tasks for `overdue`, `imminent` (`due <= today + 14d`), and `uncertain` (`date_uncertain: true`) deliverables with `project_ref: "[[Projects/<project_id>/Roadmap]]"`, `source_ref: "[[Sources/<source_id>]]"`, `linked_zettels`, and `scheduled: null`.
   - Materialize standalone captured tasks (`structured_task`) with composite identity fields (`external_source_alias`, `external_integration`, `external_account_scope`, `external_collection_id`, `external_item_id`, `external_payload_sha256`), `scheduled: null`, and `horizon_bucket` (`overdue` | `imminent` | `uncertain` | `future`).
5. **Source Provenance & Verification (`<vault>/Sources/{source_id}.md` & `verify_ingestion_batch`)**:
   - Persist `type: source`, separated provenance fingerprints (`sha256`, `normalized_text_sha256`, `structured_payload_sha256`), `ingestion_status: "extracted"`, `ingestion_outcome` (`extracted` | `metadata_only` | `unsupported_deferred` | `skipped_duplicate` | `updated_existing` | `failed`), and verify bidirectional links via `verify_ingestion_batch()`.
6. **State Transition**: Transition immediately to `05-plan.md` (`/plan`).
