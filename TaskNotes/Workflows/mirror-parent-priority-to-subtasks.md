---
type: runtime_workflow
id: mirror-parent-priority-to-subtasks
version: 1.0.0
name: Mirror parent priority to subtasks
description: Update existing subtasks when a parent task's priority changes.
enabled: true
triggers:
  - id: priority-changed
    event:
      id: task.priority.changed
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
  - id: mirror-priority
    action:
      id: task.patch
      version: 1.0.0
    input:
      task:
        $expr: task.path
      patch:
        priority:
          $expr: event.after.priority
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

# Mirror parent priority to subtasks

Enable this workflow if existing subtasks should keep the same priority as their parent task.
