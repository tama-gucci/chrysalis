---
kind: mdbase.contract
contract_type: record
id: project-contract
version: "0.3.0"
x-target-type: project
description: "Authoritative data contract for Chrysalis project roadmaps and master deliverable ledgers"
record_schema:
  dialect: json-schema-2020-12
  value:
    type: object
---

# Project Roadmap Data Contract

## 1. Scope and Identity
This contract governs all project roadmap documents located in `Projects/**/Roadmap.md`.
- **Identity Pattern**: `Projects/{project_id}/Roadmap.md`.
- **Target Type**: `project` conforming to `_types/project.md`.
- **Project ID**: Lowercase kebab-case slug matching `^[a-z0-9-]+$`.
- **Multi-Source Provenance**: Supports primary `source_ref` / `source_checksum` alongside `contributing_sources` (multiple specification, rubric, or deadline sources), `reference_sources` (shared reference books/manuals), and `supporting_assets` (deferred binary assets such as `.dwt` CAD templates).

## 2. Master Deliverable Ledger Architecture
Each project roadmap is the absolute single source of truth for all deliverables across the project's entire lifecycle:
- The `deliverables` list in frontmatter must retain 100% of semester or project milestones.
- Each deliverable entry contains:
  - `id`: Stable deliverable identifier (`^[a-z0-9-]+$`).
  - `title`: Human-readable deliverable name.
  - `due`: ISO date string `YYYY-MM-DD` or `null` if uncertain.
  - `due_time` / `due_timezone` / `due_at`: Observed deadline time and timezone evidence (or `null` when date-only; never fabricated).
  - `date_uncertain`: Boolean indicating whether deadline is TBD.
  - `horizon_bucket`: Planning horizon classification (`overdue`, `imminent`, `uncertain`, `future`, `completed`, `archived`, or `null`).
  - `status`: Lifecycle state (`todo`, `in-progress`, `done`, `archived`).
  - `task_ref`: Wikilink to materialized task note in `TaskNotes/Tasks/`, or `null` if out-of-horizon.
  - `tier`: Urgency tier (1=Low, 2=Normal, 3=High, 4=Imminent/Critical).
  - `source_ref` / `source_scope` / `evidence`: Provenance link, scope key, and page/section/image citation.
  - `conflict_flag` / `conflict_notes`: Flags contradictory or stale deadline evidence across sources or existing task notes for human review.
  - `user_modified` / `googleCalendarEventId`: Preserved user edits and calendar sync identifiers.

## 3. Horizon Partitioning ($H=14$ Days)
- **Active Window**: Eligible deliverables with `due <= today + 14d` (`imminent` / `overdue`) or `date_uncertain: true` materialize as individual tasks in `TaskNotes/Tasks/` (excluding `done` and `archived` items).
- **Inert Window**: Deliverables with `due > today + 14d` (`future`) remain recorded in the roadmap's master ledger with `task_ref: null`. They do not clutter the daily task views.

## 4. Multi-Source & Syllabus Revision Reconciliation
- **Supplementary Ingestion (Default)**: Additive by default; appends or enriches deliverables without archiving items from other source scopes.
- **Authoritative Same-Scope Revision**: When an explicitly identified authoritative replacement for the same `source_scope` is ingested:
  - Matching deliverables are updated in-place while preserving `done`/`archived` status, `user_modified` edits, `task_ref`, and `googleCalendarEventId`.
  - New deliverables are appended to the ledger.
  - Omitted deliverables within that replaced scope are transitioned to `status: archived` (never deleted; empty/failed extraction never implies deletion).
  - `last_updated` is stamped with the current local timestamp, and atomic updates use Compare-And-Swap (CAS) with `if_revision` validation.
