---
last_audit: "{{TIMESTAMP}}"
last_planning_cycle: "{{TIMESTAMP}}"
timezone_offset: "{{TIMEZONE_OFFSET}}"
active_timezone: "{{TIMEZONE_OFFSET}}"

pause_state:
  is_paused: false
  mode: "operational"
  reason: "system_initialized"
  paused_at: null
  resume_policy: "auto_at_cycle"
  resume_target: "morning"
  freeze_multiplier_decay: false

diurnal_offsets:
  morning_buffer: "+00:45"
  peak_sprint_1_start: "+01:30"
  peak_sprint_1_end: "+02:45"
  decompression_buffer: "+00:15"
  peak_sprint_2_start: "+03:00"
  peak_sprint_2_end: "+04:30"
  slump_start: "+06:30"
  kinetic_defrost_start: "+07:45"
  slump_end: "+08:15"
  recovery_start: "+08:30"
  recovery_end: "+10:30"

learned_wake_rhythms:
  rolling_avg_wake_weekday: "08:30"
  rolling_avg_wake_weekend: "10:00"
  rolling_avg_energy_weekday: 4.0
  rolling_avg_energy_weekend: 4.0
  wake_learning_rate: 0.15

dynamic_multipliers:
  analytical: 1.00
  kinetic: 1.00
  synthesis: 1.00
  administrative: 1.00

candidate_task_pools:
  quick_wins: []
  deep_work: []

system_state:
  production_runtime:
    orchestrator: "{{production_orchestrator}}" # e.g., google_antigravity
    storage_substrate: "{{storage_provider}}" # e.g., google_drive
    central_host_type: "cloud_synced_substrate"
  development_pipeline:
    agent_ide: "{{dev_agent_ide}}" # e.g., google_antigravity
    dev_workstation: "{{dev_hostname}}" # e.g., station-node
    environment_profile: "System/Environment/Active-Profile.md"
  pause_state:
    is_paused: false
    mode: "operational"
    reason: "system_initialized"
    paused_at: null
    resume_policy: "auto_at_cycle"
    resume_target: "morning"
    freeze_multiplier_decay: false
  active_pillar: "Pillar 1: Core Foundation & Systems Setup"

diurnal_baselines:
  weekday_default_wake: "08:30"
  weekend_default_wake: "10:00"
  relative_offsets:
    morning_buffer: "+00:45"
    peak_sprint_1_start: "+01:30"
    peak_sprint_1_end: "+02:45"
    decompression_buffer: "+00:15"
    peak_sprint_2_start: "+03:00"
    peak_sprint_2_end: "+04:30"
    slump_start: "+06:30"
    kinetic_defrost_start: "+07:45"
    slump_end: "+08:15"
    recovery_start: "+08:30"
    recovery_end: "+10:30"

calendar_sync:
  enabled: true
  provider: "google_calendar"
  last_sync: null
  horizon_start: null
  horizon_end: null
  cached_events: []

chronotype_telemetry:
  hourly_efficiency_history: []
  learned_peak_offset: "+01:30"
  learned_slump_offset: "+06:30"
  offset_learning_rate: 0.10

morning_checkin:
  active_today:
    date: null
    prompt_sent_at: null
    response_received_at: null
    recorded_wake_time: null
    reported_energy_level: null
    applied_energy_mode: "optimal"
  learned_rhythms:
    rolling_avg_wake_weekday: "08:30"
    rolling_avg_wake_weekend: "10:00"
    rolling_avg_energy_weekday: 4.0
    rolling_avg_energy_weekend: 4.0
    wake_learning_rate: 0.15
  checkin_history: []

prototype_schedule:
  staged_user_intent: null
  target_date: null
  feedback_status: "pending"
  staged_anchor_task: null
  staged_support_tasks: []

inferred_task_pool:
  max_pool_size: 6
  learning_weights:
    pillar-1/setup: 1.00
    pillar-1/admin: 1.00
    pillar-1/core: 1.00
    pillar-1/finance: 1.00
  interaction_history: []
  tasks:
    - id: "inf-01"
      title: "Configure Obsidian Daily Dashboard & Views"
      tag: "pillar-1/setup"
      modality: "administrative"
      timeEstimate: 20
      energy: "low"
      friction: "low"
      times_presented: 1
      status: "available"
    - id: "inf-02"
      title: "Audit Weekly Recurring Subscriptions & Accounts"
      tag: "pillar-1/finance"
      modality: "administrative"
      timeEstimate: 25
      energy: "low"
      friction: "medium"
      times_presented: 1
      status: "available"

schedule_refinement_memory:
  max_daily_tasks_weekday: 3
  max_daily_tasks_weekend: 2
  weekend_admin_lockout: true
  preferred_buffer_minutes: 20
  feedback_history: []

tag_multipliers:
  pillar-1/setup: 1.00
  pillar-1/admin: 1.00
  pillar-1/core: 1.00
  pillar-1/finance: 1.00
  pillar-2/execution: 1.00
  pillar-2/deliverables: 1.00
  pillar-2/growth: 1.00
  pillar-3/mastery: 1.00
  pillar-3/expansion: 1.00
---
