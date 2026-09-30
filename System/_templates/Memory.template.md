---
type: system_state
schema_version: "1.0.0"
last_updated: "{{TIMESTAMP}}"
updated_by: "agent-session-{{SESSION_ID}}"

user_profile:
  timezone_offset: "{{TIMEZONE_OFFSET}}"
  working_hours:
    start: "09:00"
    end: "18:00"
  focus_preferences:
    default_sprint_minutes: 75
    decompression_buffer_minutes: 15
    max_daily_sprints: 4
    weekend_admin_lockout: true

cognitive_modality_defaults:
  analytical:
    baseline_minutes: 90
    energy_level: "high"
    target_window: "peak_sprint_1"
    multiplier: 1.00
  synthesis:
    baseline_minutes: 75
    energy_level: "medium"
    target_window: "recovery"
    multiplier: 1.00
  kinetic:
    baseline_minutes: 45
    energy_level: "medium"
    target_window: "defrost"
    multiplier: 1.00
  administrative:
    baseline_minutes: 30
    energy_level: "low"
    target_window: "slump"
    multiplier: 1.00

active_horizons:
  planning_window_days: 14
  active_projects:
    - "[[Projects/project-alpha/Roadmap]]"
  paused_projects: []

session_metrics:
  total_completed_tasks: 0
  total_focus_hours: 0.0
  consecutive_planned_days: 1

ingestion:
  contract_version: "1.0.0"
  auto_ingest_on_nightly_audit: true
  local_resources_folder_enabled: false
  preserve_originals_in_place: true
  standalone_future_task_policy: "create_inert_task"
  default_sources:
    - "media"
    - "quick-capture"
  sources:
    media:
      integration: google-drive
      enabled: false
      collection: "<folder-reference>"
      access: read-only
    quick-capture:
      integration: google-tasks
      enabled: false
      collection: "<list-reference>"
      access: read-only

integrations:
  contract_version: "1.0.0"
  instances:
    media:
      integration: google-drive
      enabled: false
      access: read-only
      config:
        collection: "<folder-reference>"
    quick-capture:
      integration: google-tasks
      enabled: false
      access: read-only
      config:
        collection: "<list-reference>"
    maps:
      integration: google-maps
      enabled: false
      access: read-only
      auth_ref: "env:GOOGLE_MAPS_API_KEY"
      config:
        region_code: "US"
        language_code: "en"
        units: "metric"
        default_travel_mode: "driving"
    vault-maps:
      integration: obsidian-maps
      enabled: false
      access: read-only
      config:
        base_view_path: "TaskNotes/Views/maps-default.base"
        coordinate_property: "coordinates"
        plugin_id: "maps"
  bindings:
    ingestion:
      sources:
        media: "media"
        quick-capture: "quick-capture"
    location:
      resolve: "maps"
    routing:
      estimate: "maps"
    visualization:
      map_projection: "vault-maps"

# Narrow legacy compatibility block preserved for older scripts and migration checks
ingestion_config:
  locker_root: "Chrysalis-Media-Locker"
  drive_inbox_folder: "Chrysalis-Media-Locker/01-Inbox"
  drive_projects_folder: "Chrysalis-Media-Locker/02-Projects"
  discovery_roots:
    - "01-Inbox"
    - "02-Projects"
  preserve_originals_in_place: true
  max_discovery_depth: 6
  auto_ingest_on_nightly_audit: true
  local_resources_folder_enabled: false
---

# Agent Persistent Memory

## Strategic Directives & User Preferences
- **Primary Goal**: Deliverable-first planning aligned with active course and project roadmaps.
- **Constraints**: Never schedule administrative tasks on weekends. Multi-day institutional submissions require a mandatory 3–5 business day buffer between submission and verification.
- **Working Style**: Stacking analytical sprints during peak energy (+01:30 to +04:30), kinetic during defrost (+07:45), synthesis during recovery (+08:30).

## Active Project Horizons (14-Day Window)
| Project Roadmap | Status | Horizon Deadline | Key Deliverables in Horizon |
| :--- | :--- | :--- | :--- |
| [[Projects/project-alpha/Roadmap]] | Active | {{HORIZON_DATE}} | Deliverable A, Deliverable B |

## Past Session Outcomes Ledger
<!-- Most recent sessions retained for context window optimization -->

## Optional Interactive Planning State
The planning runbooks may initialize `prototype_schedule`, `morning_checkin`, `checkin_history`, and `system_state.pause_state` after approval. These are agent-managed extensions, not background services or schema-enforced automation. An absent plan is unapproved; an absent pause state means no recorded manual pause. Preserve unknown existing fields. Task candidates are queried from task notes and project deliverables, not duplicated in memory.
