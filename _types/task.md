---
kind: mdbase.type
name: task
version: 1
description: "Authoritative Chrysalis task model conforming to mdbase v0.3 and TaskNotes interop"
match:
  path_glob: "TaskNotes/Tasks/**/*.md"
schema:
  dialect: json-schema-2020-12
  value:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    $id: "https://chrysalis.dev/schemas/types/task.schema.json"
    title: "ChrysalisTask"
    type: object
    additionalProperties: false
    required:
      - title
      - status
      - dateCreated
    properties:
      type:
        const: task
        description: "Explicit type identifier"
      title:
        type: string
        minLength: 1
        description: "Imperative task title describing actionable work"
      status:
        type: string
        enum: [todo, in-progress, done, archived]
        default: todo
        description: "Lifecycle status of the task"
      dateCreated:
        type: string
        format: date-time
        description: "Creation timestamp with explicit local timezone offset"
      created:
        type: string
        format: date-time
        description: "Backward-compatible alias for dateCreated"
      dateModified:
        type: string
        format: date-time
        description: "Modification timestamp with explicit local timezone offset"
      due:
        type: [string, "null"]
        format: date
        description: "Target completion date in YYYY-MM-DD format, or null if uncertain"
      scheduled:
        type: [string, "null"]
        format: date-time
        description: "Calibrated focus window timestamp, or null if inert/staged"
      priority:
        type: string
        enum: [urgent, high, normal, low, none]
        default: normal
        description: "Priority tier for scheduling arbitration"
      urgency_tier:
        type: integer
        minimum: 1
        maximum: 4
        default: 2
        description: "1 (Low) to 4 (Imminent/Blocking)"
      modality:
        type: string
        enum: [analytical, kinetic, synthesis, administrative]
        default: analytical
        description: "Bio-cognitive work modality"
      timeEstimate:
        type: integer
        minimum: 0
        default: 45
        description: "Estimated duration as a number of minutes"
      energy:
        type: string
        enum: [high, medium, low]
        default: medium
        description: "Subjective energy required"
      friction:
        type: string
        enum: [high, medium, low]
        default: medium
        description: "Anticipated resistance or cognitive startup cost"
      micro_chunked:
        type: boolean
        default: false
        description: "True if 3-step Starter Wedge has been injected into body"
      tags:
        type: array
        items:
          type: string
        default: ["task"]
        description: "Taxonomy tags referencing strategic pillars"
      linked_zettels:
        type: array
        items:
          type: string
        default: []
        description: "Array of wikilinks to relevant Slipbox atomic research notes"
      project_ref:
        type: [string, "null"]
        description: "Wikilink to parent project roadmap, e.g. [[Projects/<id>/Roadmap]]"
      deliverable_id:
        type: [string, "null"]
        description: "Identifier linking task to deliverable entry in parent roadmap"
      googleCalendarEventId:
        type: [string, "null"]
        description: "TaskNotes Google Calendar event ID for external calendar sync"
      date_uncertain:
        type: boolean
        default: false
        description: "True if deliverable has an ambiguous deadline or is TBD"
      startedAt:
        type: [string, "null"]
        format: date-time
        description: "Timestamp when focus session commenced"
      completedAt:
        type: [string, "null"]
        format: date-time
        description: "Timestamp when task was marked done"
collection:
  display:
    name_field: title
  read_defaults:
    status: todo
    priority: normal
    urgency_tier: 2
    modality: analytical
    timeEstimate: 45
    energy: medium
    friction: medium
    micro_chunked: false
    date_uncertain: false
    tags: ["task"]
    linked_zettels: []
  links:
    project_ref:
      target_type: project
      validate_exists: false
    linked_zettels[]:
      target_type: zettel
      validate_exists: false
lifecycle:
  on_create:
    set:
      dateCreated: { now: true }
      dateModified: { now: true }
  on_update:
    set:
      dateModified: { now: true }
---

# Task Model

This type defines execution tasks managed by Chrysalis and compatible with Obsidian TaskNotes.
Tasks reside strictly in `chrysalis/Tasks/**/*.md`.

## Behavioral Rules:
1. **Filename Convention**: `chrysalis/Tasks/{YYYYMMDD}-{slug}.md`. Date prefix uses `due` date if present, or `dateCreated` date if `due` is null.
2. **Cognitive Alignment**: Tasks are categorized by cognitive modality (`analytical`, `kinetic`, `synthesis`, `administrative`) to align with ultradian rhythm windows during staging and calibration.
3. **Inert Scheduling**: When out-of-horizon deliverables are extracted, `scheduled` remains `null`.
4. **Calendar Sync**: External calendar synchronization is owned by TaskNotes via `googleCalendarEventId`. Chrysalis sets this field to `null` on creation.
5. **Time Estimation**: `timeEstimate` specifies estimated execution duration as a number of minutes.
