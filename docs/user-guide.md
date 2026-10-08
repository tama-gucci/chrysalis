# Daily use

Pi exposes `/skill:chrysalis-<family>`. Every family calls the shared operation tool.

| Family | Use |
|---|---|
| daily | Calibration, staging, audit, pause/resume |
| task | Capture, editing, actual session outcomes |
| knowledge | Ingestion, atomic notes, projects, onboarding |
| diagnostics | Read-only integrity and reviewed repair |
| environment | Explicit device assessment |
| integrations | Bound optional providers |
| maintenance | Package previews, collisions, removal/rollback |

Use `query` for bounded discovery, `read` for a note/revision and `template` for sanitized
structures. `task.draft` creates an unscheduled proposal; edits use complete `propose` records.
Only exact operator approval enables application.

Ingestion follows discovery, extraction, draft, prevalidation, review, approval, apply and
verification. `original.inspect` reads a selected original and extracts bounded text/PDF pages
with coverage. Scanned PDFs/images require external OCR/vision; opaque files remain deferred.
`duplicates` provides raw/normalized matches and lexical evidence for semantic review without
merging records.

Planning needs observed wake/energy and fresh commitments with `observed_at`. An explicit
fresh no-calendar observation is acceptable when no calendar is used. A missing or stale cache
does not establish free time. Review Daily/task/Memory changes together. `stage` proposes a
pending prototype without scheduling tasks or learning forecast telemetry.

Evening audit checks integrity, learns actual completed sessions once, rolls over unsuccessful
focus and drafts Starter Wedges. The procedure also checks enabled ingestion, project horizons
and knowledge links. Maintenance resumes at evening, rest next morning and vacation at its
date; flow/unresponsive pauses need explicit resume. All preserve learned multipliers.

Entry alone does not suppress fallback. Hashed audit/planning results qualify only after their
local date and offset verify. Manual reruns remain available; job registration is separate.

## TaskNotes UI

Supplied views cover task list, kanban, calendar, agenda, mini-calendar, relationships, workflow
discovery, permitted maps and Pomodoro statistics. TaskNotes provides task editing, sessions
and Calendar sync. Optional companion plugins render workflows/maps. `Dashboard.md` uses
Dataview when installed. These are projections of the same notes.
Personal workflow definitions belong in `TaskNotes/Workflows`.

YAML/schema acceptance does not prove physical rendering or authenticated sync. Test those in
an Obsidian installation. Keep Calendar credentials and identifiers under TaskNotes ownership.
