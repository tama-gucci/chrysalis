---
type: runtime_workflow
id: stamp-completed-at
version: 1.0.0
name: Stamp completed timestamp
description: Set a completedAt field when a task status changes to done.
enabled: true
triggers:
  - id: status-done
    event:
      id: task.status.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
      to: done
steps:
  - id: stamp-completed
    action:
      id: task.patch
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
      patch:
        completedAt:
          $expr: now
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
    - field: event.after.completedAt
      operator: missing
---

# Stamp completed timestamp

Sets a custom `completedAt` field when a task is marked `done`.