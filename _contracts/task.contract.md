---
kind: mdbase.contract
id: task-contract
version: "0.3.0"
target_type: task
description: "Authoritative data contract for Chrysalis execution tasks in mdbase v0.3"
---

# Task Data Contract

## 1. Scope and Identity
This contract governs all execution tasks located in `chrysalis/Tasks/**/*.md`.
- **Identity Pattern**: `chrysalis/Tasks/{YYYYMMDD}-{slug}.md`.
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

## 4. Calendar and Synchronization
- `googleCalendarEventId`: Populated exclusively by Obsidian TaskNotes sync engine. Chrysalis creates this as `null`.
- `scheduled`: Timestamp with explicit local offset (`YYYY-MM-DDTHH:mm:ss-05:00`) when calibrated to daily focus block, or `null` when staged or inert.
- `due`: Target date string in `YYYY-MM-DD` format, or `null` if deadline is ambiguous/uncertain.
- `date_uncertain`: Boolean flag (`true` when deadline is TBD, prohibiting automatic calendar hard-locking).

## 5. Timezone Format Invariant
All timestamps (`dateCreated`, `dateModified`, `scheduled`, `startedAt`, `completedAt`) must serialize with an explicit local timezone offset (e.g. `-05:00`). Raw UTC `"Z"` strings violate this contract and fail validation.
