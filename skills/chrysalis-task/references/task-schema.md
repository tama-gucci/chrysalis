# Task capture and editing
Read the selected vault's normative `_types/task.md` through `schema` with `type:task`;
do not copy it here. Parse shorthand title, tags, priority,
estimate, due date, modality, project and Zettel links. Infer modality from the concrete work;
uncertain project associations need review. Use `task.draft` for structured capture and complete
reviewed `propose` changes for edits. New tasks are todo, scheduled:null, with null Calendar IDs.
Use date-prefixed filenames and registered pillar tags. If a project is selected, inherit its
existing linked_zettels; a standalone task keeps projects:[] and needs no fabricated Zettel.
TaskNotes contexts, projects, dependencies, timeEntries, recurrence, reminders, occurrence fields,
native date-only scheduling and customProperties have explicit schema support. Unknown frontmatter
requires separate reviewed package/schema maintenance outside the life profile. The tool cannot
edit schemas; do not accept or strip unknown fields silently. Preserve all existing
plugin properties and every googleCalendar field. Native timeEntries may contain RFC3339 UTC;
agent-authored scheduling and creation timestamps use the configured local offset.
Use TaskNotes task list, kanban, calendar and timer UI over these files. Onboarding supplies the plugin's task
folder/field mappings from the shared registry; existing settings are not rewritten by code updates. The supplied Bases/Dataview views are optional projections;
session outcomes come from actual plugin timeEntries or explicit startedAt/completedAt values.
TaskNotes alone owns Google Calendar sync; model authentication does not enable provider access.

The prepared Daily plugin template uses Obsidian date placeholders. The package's
System/_templates/Daily-Note.template.md is a separate agent draft with explicit placeholders.
Native Pomodoro history is stored in Daily and shown in the sessions view. Audit learning uses
completed task timeEntries or explicit task startedAt/completedAt; Daily-only Pomodoros do not
independently update task multipliers.
