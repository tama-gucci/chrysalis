---
type: runtime_workflow
id: mirror-parent-dependencies-to-subtasks
version: 1.0.0
name: Mirror parent dependencies to subtasks
description: Replace each subtask's dependencies with the parent task's current dependencies.
enabled: false
triggers:
  - id: dependencies-changed
    event:
      id: task.dependencies.changed
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
  - id: mirror-dependencies
    action:
      id: task.patch
      version: 1.0.0
    input:
      task:
        $expr: task.path
      patch:
        blockedBy:
          $expr: event.after.blockedBy
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

# Mirror parent dependencies to subtasks

Enable this workflow if subtasks should always have the same blocking dependencies as their parent task.
