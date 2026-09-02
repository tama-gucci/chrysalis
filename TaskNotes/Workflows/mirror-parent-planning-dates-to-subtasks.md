---
type: runtime_workflow
id: mirror-parent-planning-dates-to-subtasks
version: 1.0.0
name: Mirror parent planning dates to subtasks
description: Update existing subtasks when a parent task's scheduled or due date changes.
enabled: false
triggers:
  - id: scheduled-changed
    event:
      id: task.scheduled.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
  - id: due-changed
    event:
      id: task.due.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
steps:
  - id: subtasks
    action:
      id: task.subtasks
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
  - id: mirror-dates
    action:
      id: task.patch
      version: 1.0.0
    input:
      task:
        $expr: task.path
      patch:
        scheduled:
          $expr: event.after.scheduled
        due:
          $expr: event.after.due
    for_each:
      items:
        $expr: steps.subtasks.output.tasks
      as: task
run:
  concurrency:
    group: workflow
    policy: skip
  limits:
    max_items: 50
  on_error: continue
x-tasknotes:
  format_version: 1
  source: tasknotes-workflows
  conditions:
    - field: event.after.path
      operator: exists
---

# Mirror parent planning dates to subtasks

Enable this workflow if subtasks should move with their parent task's scheduled and due dates.
