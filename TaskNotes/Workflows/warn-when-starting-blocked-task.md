---
type: runtime_workflow
id: warn-when-starting-blocked-task
version: 1.0.0
name: Warn when starting a blocked task
description: Show a notice when a task is moved to active while dependencies are incomplete.
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
  - id: dependencies
    action:
      id: task.dependencies
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
  - id: warn
    action:
      id: notice.show
      version: 1.0.0
    input:
      message: "{{event.after.title}} is still blocked by {{steps.dependencies.output.count}} task(s)."
run:
  concurrency:
    group: workflow
    policy: skip
  limits:
    max_items: 10
  on_error: stop
x-tasknotes:
  format_version: 1
  source: tasknotes-workflows
  conditions:
    - field: event.after.path
      operator: exists
    - field: event.after.isBlocked
      operator: is
      value: true
---

# Warn when starting a blocked task

Enable this workflow if you want an Obsidian notice before working on a task that still has incomplete dependencies.
