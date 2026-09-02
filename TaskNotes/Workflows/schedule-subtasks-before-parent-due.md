---
type: runtime_workflow
id: schedule-subtasks-before-parent-due
version: 1.0.0
name: Schedule subtasks before parent due date
description: Schedule existing subtasks one week before their parent task is due.
enabled: false
triggers:
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
  - id: schedule-subtasks
    action:
      id: task.setScheduled
      version: 1.0.0
    input:
      task:
        $expr: task.path
      date:
        $expr: date(event.after.due) - duration("1w")
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
    - field: event.after.due
      operator: exists
---

# Schedule subtasks before parent due date

Enable this workflow if subtasks should be scheduled one week before their parent task is due.
Adjust the amount and unit in the relative date expression if your planning cadence is different.
