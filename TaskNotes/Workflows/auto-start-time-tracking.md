---
type: runtime_workflow
id: auto-start-time-tracking
version: 1.0.0
name: Auto-start time tracking
description: Start a timer when a task status changes to active.
enabled: true
triggers:
  - id: status-active
    event:
      id: task.status.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
      to: active
steps:
  - id: start-time
    action:
      id: time.start
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
      options:
        description: Started by {{workflow.name}}
run:
  concurrency:
    group: workflow
    policy: skip
  limits:
    max_items: 1
  on_error: stop
x-tasknotes:
  format_version: 1
  source: tasknotes-workflows
  conditions:
    - field: event.after.path
      operator: exists
---

# Auto-start time tracking

Enable this workflow to start time tracking when a TaskNotes task moves to `active`.
