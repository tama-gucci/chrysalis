---
kind: mdbase.contract
id: project-contract
version: "0.3.0"
target_type: project
description: "Authoritative data contract for Chrysalis project roadmaps and master deliverable ledgers"
---

# Project Roadmap Data Contract

## 1. Scope and Identity
This contract governs all project roadmap documents located in `Projects/**/Roadmap.md`.
- **Identity Pattern**: `Projects/{project_id}/Roadmap.md`.
- **Target Type**: `project` conforming to `_types/project.md`.
- **Project ID**: Lowercase kebab-case slug matching `^[a-z0-9-]+$`.

## 2. Master Deliverable Ledger Architecture
Each project roadmap is the absolute single source of truth for all deliverables across the project's entire lifecycle:
- The `deliverables` list in frontmatter must retain 100% of semester or project milestones.
- Each deliverable entry contains:
  - `id`: Stable deliverable identifier (`^[a-z0-9-]+$`).
  - `title`: Human-readable deliverable name.
  - `due`: ISO date string `YYYY-MM-DD` or `null` if uncertain.
  - `date_uncertain`: Boolean indicating whether deadline is TBD.
  - `status`: Lifecycle state (`todo`, `in-progress`, `done`, `archived`).
  - `task_ref`: Wikilink to materialized task note in `chrysalis/Tasks/`, or `null` if out-of-horizon.
  - `tier`: Urgency tier (1=Low, 2=Normal, 3=High, 4=Imminent/Critical).

## 3. Horizon Partitioning ($H=14$ Days)
- **Active Window**: Deliverables with `due <= today + 14d` (or `date_uncertain: true`) materialize as individual tasks in `chrysalis/Tasks/`.
- **Inert Window**: Deliverables with `due > today + 14d` remain recorded in the roadmap's master ledger with `task_ref: null`. They do not clutter the daily task views.

## 4. Syllabus Revision Reconciliation
When a revised syllabus is ingested:
- Matching deliverables are updated in-place (date, title changes).
- New deliverables are appended to the ledger.
- Omitted deliverables are transitioned to `status: archived` (never deleted).
- `last_updated` is stamped with the current local timestamp.
- Atomic updates must use Compare-And-Swap (CAS) with `if_revision` validation.
