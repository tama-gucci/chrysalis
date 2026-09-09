---
type: runtime_workflow
id: clear-scheduled-when-started
version: 1.0.0
name: Clear scheduled when started
description: Clear a task's scheduled date when its status changes to active or in-progress.
enabled: false
triggers:
  - id: status-active
    event:
      id: task.status.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
      to: active
  - id: status-in-progress
    event:
      id: task.status.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
      to: in-progress
steps:
  - id: clear-scheduled
    action:
      id: task.clearScheduled
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
    - field: event.after.scheduled
      operator: exists
---

# Clear scheduled when started

Enable this workflow if moving a task into active work means it should no longer appear on its scheduled day.
Adjust the status trigger values to match your TaskNotes status names before enabling it.
