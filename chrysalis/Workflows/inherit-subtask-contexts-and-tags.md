---
type: runtime_workflow
id: inherit-subtask-contexts-and-tags
version: 1.0.0
name: Inherit subtask contexts and tags
description: Copy contexts and tags from the first parent task when a task becomes a subtask.
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
  - id: inherit-contexts-tags
    action:
      id: task.patch
      version: 1.0.0
    if:
      $expr: (has(steps.parents.output.tasks[0].path))
    input:
      task:
        $expr: event.after.path
      patch:
        contexts:
          $expr: steps.parents.output.tasks[0].contexts
        tags:
          $expr: steps.parents.output.tasks[0].tags
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

# Inherit subtask contexts and tags

Enable this workflow if new subtasks should start with the same contexts and tags as their first parent task.
