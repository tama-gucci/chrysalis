# Task capture and editing
Read the selected vault's normative `_types/task.md` through `schema` with `type:task`;
do not copy it here. Parse shorthand title, tags, priority,
estimate, due date, modality, project and Zettel links. Infer modality from the concrete work;
uncertain project associations need review. Use `task.draft` for structured capture and complete
reviewed `propose` changes for edits. New tasks are todo, scheduled:null, with null Calendar IDs.
Use date-prefixed filenames and registered pillar tags. If a project is selected, inherit its
existing linked_zettels; a standalone task keeps project_ref:null and needs no fabricated Zettel.
TaskNotes contexts, projects, dependencies, timeEntries, recurrence, reminders, occurrence fields,
native date-only scheduling and customProperties have explicit schema support. Unknown frontmatter
requires a reviewed schema extension, never blanket acceptance or stripping. Preserve all existing
plugin properties and every googleCalendar field. Native timeEntries may contain RFC3339 UTC;
agent-authored scheduling and creation timestamps use the configured local offset.
Use TaskNotes task list, kanban, calendar and timer UI over these files. Configure the plugin's task
folder/field mappings explicitly. The supplied Bases/Dataview views are optional projections;
session outcomes come from actual plugin timeEntries or explicit startedAt/completedAt values.
TaskNotes alone owns Google Calendar sync; model authentication does not enable provider access.
