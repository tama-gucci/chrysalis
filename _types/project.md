---
kind: mdbase.type
name: project
version: 1
description: "Authoritative Chrysalis project roadmap and master deliverable ledger model"
match:
  path_glob: "Projects/**/Roadmap.md"
schema:
  dialect: json-schema-2020-12
  value:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    $id: "https://chrysalis.dev/schemas/types/project.schema.json"
    title: "ChrysalisProjectRoadmap"
    type: object
    additionalProperties: false
    required:
      - project_id
      - title
      - status
      - pillar
      - last_updated
    properties:
      type:
        enum: [project, project_roadmap]
        default: project_roadmap
        description: "Explicit type identifier"
      project_id:
        type: string
        pattern: "^[a-z0-9-]+$"
        description: "Unique slug identifier for the project"
      title:
        type: string
        minLength: 1
        description: "Descriptive project title"
      status:
        type: string
        enum: [active, staged, paused, complete, archived]
        default: active
        description: "Strategic lifecycle state of the project"
      pillar:
        type: string
        description: "Strategic pillar category, e.g. pillar-academics, pillar-career"
      horizon_window:
        type: string
        description: "Project active date range, e.g. '2026-09-01 → 2026-12-15'"
      last_updated:
        type: string
        format: date-time
        description: "Timestamp of last modification with explicit local offset"
      source_ref:
        type: [string, "null"]
        description: "Wikilink to primary originating ingestion source, e.g. [[Sources/<id>]]"
      source_checksum:
        type: [string, "null"]
        pattern: "^[a-f0-9]{64}$"
        description: "SHA-256 digest of primary originating source document"
      contributing_sources:
        type: array
        items:
          type: [string, object]
        default: []
        description: "Multiple ingestion sources contributing requirements, rubrics, or deadlines to this project"
      reference_sources:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to shared reference material (e.g. textbook chapters) supporting this project"
      supporting_assets:
        type: array
        items:
          type: object
        default: []
        description: "Supporting binary assets (e.g. .dwt CAD templates) associated with this project with explicit deferred/unsupported status"
      tags:
        type: array
        items:
          type: string
        default: []
        description: "Taxonomy tags associated with the project"
      linked_zettels:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to background research or domain concepts in Slipbox"
      deliverables:
        type: array
        default: []
        description: "Complete master ledger of project deliverables"
        items:
          type: object
          required:
            - id
            - title
            - status
          additionalProperties: false
          properties:
            id:
              type: string
              pattern: "^[a-z0-9-]+$"
              description: "Unique deliverable identifier within project"
            title:
              type: string
              minLength: 1
              description: "Deliverable title"
            due:
              type: [string, "null"]
              format: date
              description: "Target due date in YYYY-MM-DD format, or null if uncertain"
            due_time:
              type: [string, "null"]
              description: "Observed deadline time from source (e.g. '23:59:00'), or null if date-only"
            due_timezone:
              type: [string, "null"]
              description: "Observed timezone label or offset from source (e.g. 'CDT', '-05:00')"
            due_at:
              type: [string, "null"]
              format: date-time
              description: "Full RFC 3339 deadline timestamp with explicit local offset when a deadline time is observed"
            date_uncertain:
              type: boolean
              default: false
              description: "True if deadline is ambiguous or TBD"
            horizon_bucket:
              type: [string, "null"]
              enum: [overdue, imminent, uncertain, future, completed, archived, null]
              description: "Computed planning horizon classification"
            status:
              type: string
              enum: [todo, in-progress, done, archived]
              default: todo
              description: "Deliverable completion status"
            task_ref:
              type: [string, "null"]
              description: "Wikilink to materialized task in TaskNotes/Tasks/"
            tier:
              type: integer
              minimum: 1
              maximum: 4
              default: 2
              description: "Urgency tier (1=Low, 4=Critical)"
            source_ref:
              type: [string, "null"]
              description: "Wikilink to the specific source defining this deliverable"
            source_scope:
              type: [string, "null"]
              description: "Scope key of originating source for authoritative vs supplementary reconciliation"
            evidence:
              type: [string, "null"]
              description: "Page, section, or visual region citation supporting this deliverable"
            conflict_flag:
              type: boolean
              default: false
              description: "True if contradictory or stale evidence requires human review"
            conflict_notes:
              type: [string, "null"]
              description: "Details of contradictory or stale evidence"
            user_modified:
              type: boolean
              default: false
              description: "True if manually edited by the user; preserved across syllabus reconciliation"
            googleCalendarEventId:
              type: [string, "null"]
              description: "Preserved Google Calendar event identifier when associated with a synced task"
collection:
  display:
    name_field: title
  unique:
    - field: project_id
      scope: collection
  read_defaults:
    status: active
    deliverables: []
    linked_zettels: []
    tags: []
  links:
    source_ref:
      target_type: source
      validate_exists: false
    linked_zettels[]:
      target_type: zettel
      validate_exists: false
lifecycle: {}
---

# Project Roadmap Model

This type defines project roadmaps and master deliverable ledgers.
Each project lives in `Projects/{project_id}/Roadmap.md`.

## Master Ledger Architecture:
1. **Single Source of Truth**: The `deliverables` list retains 100% of semester or project deliverables across the complete timeline.
2. **Horizon Materialization**: Only deliverables within the active 14-day planning horizon materialize as individual execution tasks in `TaskNotes/Tasks/`. Deliverables outside 14 days remain recorded in the roadmap's `deliverables` ledger.
3. **Reconciliation**: When an updated syllabus is ingested, the diffing algorithm modifies existing deliverables in-place and archives removed deliverables (`status: archived`).
