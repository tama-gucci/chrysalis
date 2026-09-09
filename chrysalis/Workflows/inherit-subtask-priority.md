---
type: runtime_workflow
id: inherit-subtask-priority
version: 1.0.0
name: Inherit subtask priority
description: Copy priority from the first parent task when a task becomes a subtask.
enabled: true
triggers:
  - id: projects-changed
    event:
      id: task.projects.changed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
  - id: task-created
    event:
      id: task.created
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
steps:
  - id: parents
    action:
      id: task.parents
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
  - id: inherit-priority
    action:
      id: task.patch
      version: 1.0.0
    if:
      $expr: (has(steps.parents.output.tasks[0].priority))
    input:
      task:
        $expr: event.after.path
      patch:
        priority:
          $expr: steps.parents.output.tasks[0].priority
    x-tasknotes:
      conditions:
        - field: steps.parents.output.tasks[0].priority
          operator: exists
run:
  concurrency:
    group: workflow
    policy: skip
  limits:
    max_items: 5
  on_error: stop
x-tasknotes:
  format_version: 1
  source: tasknotes-workflows
  conditions:
    - field: event.after.path
      operator: exists
    - field: event.after.projects
      operator: exists
---

# Inherit subtask priority

Enable this workflow if subtasks should take their initial priority from their first parent task.
