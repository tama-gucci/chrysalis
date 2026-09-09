---
type: runtime_workflow
id: inherit-subtask-planning-dates
version: 1.0.0
name: Inherit subtask planning dates
description: Copy scheduled and due dates from the first parent task when a task becomes a subtask.
enabled: false
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
  - id: inherit-dates
    action:
      id: task.patch
      version: 1.0.0
    if:
      $expr: (has(steps.parents.output.tasks[0].path))
    input:
      task:
        $expr: event.after.path
      patch:
        scheduled:
          $expr: steps.parents.output.tasks[0].scheduled
        due:
          $expr: steps.parents.output.tasks[0].due
    x-tasknotes:
      conditions:
        - field: steps.parents.output.tasks[0].path
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

# Inherit subtask planning dates

Enable this workflow if subtasks should inherit their first parent task's scheduled and due dates.
