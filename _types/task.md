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
      due_time:
        type: [string, "null"]
        description: "Observed deadline time from source (e.g. '23:59:00'), or null for date-only deadlines"
      due_timezone:
        type: [string, "null"]
        description: "Observed timezone label/offset from source (e.g. 'CDT', '-05:00')"
      due_at:
        type: [string, "null"]
        format: date-time
        description: "Full RFC 3339 deadline timestamp with explicit local offset when time is observed; null for date-only deadlines"
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
      source_ref:
        type: [string, "null"]
        description: "Wikilink to originating source record, e.g. [[Sources/<id>]]"
      evidence_ref:
        type: [string, "null"]
        description: "Page, section, or visual evidence citation supporting this task"
      horizon_bucket:
        type: [string, "null"]
        enum: [overdue, imminent, uncertain, future, null]
        description: "Horizon bucket classification (overdue, imminent, uncertain, future)"
      review_required:
        type: boolean
        default: false
        description: "True if contradictory, stale, or uncertain deadline/association evidence requires user review"
      review_notes:
        type: [string, "null"]
        description: "Explanation of contradictory, stale, or uncertain evidence"
      googleCalendarEventId:
        type: [string, "null"]
        description: "TaskNotes Google Calendar event ID for external calendar sync"
      date_uncertain:
        type: boolean
        default: false
        description: "True if deliverable has an ambiguous deadline or is TBD"
      external_source_alias:
        type: [string, "null"]
        description: "Configured ingestion source alias that captured this task (e.g. 'quick-capture')"
      external_integration:
        type: [string, "null"]
        description: "Integration adapter that captured this task (e.g. 'google-tasks')"
      external_account_scope:
        type: [string, "null"]
        description: "Account scope identifier for external task deduplication"
      external_collection_id:
        type: [string, "null"]
        description: "External task list or collection identifier"
      external_item_id:
        type: [string, "null"]
        description: "Stable external item ID within the provider task list"
      external_revision:
        type: [string, "null"]
        description: "Observed external revision token, etag, or update timestamp"
      external_payload_sha256:
        type: [string, "null"]
        pattern: "^[a-f0-9]{64}$"
        description: "Separate SHA-256 fingerprint of normalized structured task payload"
      external_conflict_flag:
        type: boolean
        default: false
        description: "True when an external task update conflicts with local edits"
      external_conflict_proposal:
        type: [object, "null"]
        description: "Proposed external changes awaiting human review when local edits are preserved"
      user_modified:
        type: boolean
        default: false
        description: "True if task fields or body were manually modified locally"
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
lifecycle: {}
---

# Task Model

This type defines execution tasks managed by Chrysalis and compatible with Obsidian TaskNotes.
Tasks reside strictly in `TaskNotes/Tasks/**/*.md`.

## Behavioral Rules:
1. **Filename Convention**: `TaskNotes/Tasks/{YYYYMMDD}-{slug}.md`. Date prefix uses `due` date if present, or `dateCreated` date if `due` is null.
2. **Cognitive Alignment**: Tasks are categorized by cognitive modality (`analytical`, `kinetic`, `synthesis`, `administrative`) to align with ultradian rhythm windows during staging and calibration.
3. **Inert Scheduling**: When out-of-horizon deliverables are extracted, `scheduled` remains `null`.
4. **Calendar Sync**: External calendar synchronization is owned by TaskNotes via `googleCalendarEventId`. Chrysalis sets this field to `null` on creation.
5. **Time Estimation**: `timeEstimate` specifies estimated execution duration as a number of minutes.
