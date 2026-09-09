---
type: runtime_workflow
id: stop-time-tracking-on-complete
version: 1.0.0
name: Stop time tracking on complete
description: Stop the active timer when a task is completed.
enabled: true
triggers:
  - id: completed
    event:
      id: task.completed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
steps:
  - id: stop-time
    action:
      id: time.stop
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
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

# Stop time tracking on complete

Enable this workflow if completed tasks should automatically stop any active timer.
