---
type: runtime_workflow
id: inherit-subtask-dependencies
version: 1.0.0
name: Inherit subtask dependencies
description: Add the first parent task's blocking dependencies to new subtasks.
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
  - id: parent-dependencies
    action:
      id: task.dependencies
      version: 1.0.0
    if:
      $expr: (has(steps.parents.output.tasks[0].path))
    input:
      task:
        $expr: steps.parents.output.tasks[0].path
    x-tasknotes:
      conditions:
        - field: steps.parents.output.tasks[0].path
          operator: exists
  - id: add-dependency
    action:
      id: task.addDependency
      version: 1.0.0
    if:
      $expr: (has(steps.parent-dependencies.output.dependencies))
    input:
      task:
        $expr: event.after.path
      dependency:
        $expr: task.dependency
    for_each:
      items:
        $expr: steps["parent-dependencies"].output.dependencies
      as: task
    x-tasknotes:
      conditions:
        - field: steps.parent-dependencies.output.dependencies
          operator: exists
run:
  concurrency:
    group: workflow
    policy: skip
  limits:
    max_items: 25
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

# Inherit subtask dependencies

Enable this workflow if new subtasks should also be blocked by anything that blocks their first parent task.
