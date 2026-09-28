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

ingestion_config:
  drive_inbox_folder: "Chrysalis-Media-Locker/01-Inbox"
  drive_archive_folder: "Chrysalis-Media-Locker/02-Archived-Binaries"
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
