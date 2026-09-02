---
type: runtime_workflow
id: rollover-overdue-scheduled-tasks
version: 1.0.0
name: Rollover overdue scheduled tasks
description: Move incomplete tasks with past scheduled dates to today.
enabled: false
triggers:
  - id: every-morning
    event:
      id: tasknotes-workflows.schedule.cron
      version: 1.0.0
    x-tasknotes:
      type: cron
      schedule: 0 8 * * *
      timezone: local
steps:
  - id: overdue-scheduled
    action:
      id: task.query
      version: 1.0.0
    input:
      query:
        where:
          all:
            - field: task.scheduled
              op: lt
              value:
                fn: today
            - field: task.status
              op: notIn
              value:
                - done
                - cancelled
        sort:
          - field: task.scheduled
            direction: asc
        limit: 50
        scope:
          includeArchived: false
  - id: reschedule-to-today
    action:
      id: task.reschedule
      version: 1.0.0
    input:
      task:
        $expr: task.path
      date:
        $expr: today
    for_each:
      items:
        $expr: steps["overdue-scheduled"].output.tasks
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
---

# Rollover overdue scheduled tasks

Runs while Obsidian is open. Use dry run first to confirm the selected tasks before enabling automatic date changes.
