---
kind: mdbase.contract
contract_type: record
id: task-contract
version: "0.3.0"
x-target-type: task
description: "Authoritative data contract for Chrysalis execution tasks in mdbase v0.3"
record_schema:
  dialect: json-schema-2020-12
  value:
    type: object
---

# Task Data Contract

## 1. Scope and Identity
This contract governs all execution tasks located in `TaskNotes/Tasks/**/*.md`.
- **Identity Pattern**: `TaskNotes/Tasks/{YYYYMMDD}-{slug}.md`.
- **Target Type**: `task` conforming to `_types/task.md`.

## 2. Lifecycle State Transitions
Allowed states: `todo`, `in-progress`, `done`, `archived`.
- `todo` -> `in-progress`: When task execution begins (`startedAt` timestamp serialized).
- `in-progress` -> `done`: When task execution completes (`completedAt` timestamp serialized).
- `todo` / `in-progress` -> `archived`: When task is cancelled or superseded by an updated syllabus.
- Backward transitions are permitted for corrections (e.g. `in-progress` -> `todo`).

## 3. Cognitive Modality Constraints
Tasks must declare one of four bio-cognitive modalities:
- `analytical`: High-cognition problem solving, deep work, coding, formal proofs (aligned with Peak ultradian sprints).
- `kinetic`: Physical, active, or laboratory execution (aligned with Defrost or Slump windows).
- `synthesis`: Reading, summarizing, writing literature reviews, conceptual integration (aligned with Recovery windows).
- `administrative`: Low-cognitive overhead, email, logistics, scheduling verification.

## 4. Calendar, Horizon, and Provenance Metadata
- `googleCalendarEventId`: Populated exclusively by Obsidian TaskNotes sync engine. Chrysalis creates this as `null`.
- `scheduled`: Timestamp with explicit local offset (`YYYY-MM-DDTHH:mm:ss-05:00`) when calibrated to daily focus block, or `null` when staged or inert (ingestion must always leave `scheduled: null`).
- `due`: Target date string in `YYYY-MM-DD` format, or `null` if deadline is ambiguous/uncertain.
- `due_time` / `due_timezone` / `due_at`: Observed deadline time (`HH:mm:ss`), timezone label/offset (e.g., `CDT`, `-05:00`), and full RFC 3339 timestamp with explicit local offset when observed in source material (`null` for date-only deadlines; never fabricated from screenshot filenames).
- `date_uncertain`: Boolean flag (`true` when deadline is TBD, prohibiting automatic calendar hard-locking).
- `horizon_bucket`: Horizon classification (`overdue`, `imminent`, `uncertain`, `future`, or `null`).
- `source_ref` / `evidence_ref`: Wikilink to originating `Sources/<id>.md` record and specific page/section/visual evidence anchor.
- `review_required` / `review_notes`: Flags contradictory, stale, or uncertain deadline/association evidence requiring human review.
- `external_source_alias` / `external_integration` / `external_account_scope` / `external_collection_id` / `external_item_id` / `external_revision` / `external_payload_sha256`: Optional one-way external capture provenance fields identifying imported tasks by `(integration, account_scope, collection_id, external_item_id)` without collapsing distinct items that share a title.
- `external_conflict_flag` / `external_conflict_proposal` / `user_modified`: Preserves local edits and completed/archived status on repeat imports while surfacing conflicting external changes as review proposals.

## 5. Timezone Format Invariant
All timestamps (`dateCreated`, `created`, `dateModified`, `due_at`, `scheduled`, `startedAt`, `completedAt`) must serialize with an explicit local timezone offset (e.g. `-05:00`). Raw UTC `"Z"` strings violate this contract and fail validation.
