---
type: runtime_workflow
id: stamp-started-at
version: 1.0.0
name: Stamp started timestamp
description: Set a startedAt field the first time a task status changes to active or in-progress.
enabled: true
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
  - id: stamp-started
    action:
      id: task.patch
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
      patch:
        startedAt:
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
    - field: event.after.startedAt
      operator: missing
---

# Stamp started timestamp

Enable this workflow if you want a custom `startedAt` field recorded when work begins.
Rename the field or remove the missing-field condition if your workflow should update the timestamp every time the task restarts.
