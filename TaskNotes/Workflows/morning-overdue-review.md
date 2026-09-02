---
type: runtime_workflow
id: morning-overdue-review
version: 1.0.0
name: Morning overdue review
description: Find overdue open tasks every morning and mark them high priority.
enabled: false
triggers:
  - id: every-morning
    event:
      id: tasknotes-workflows.schedule.cron
      version: 1.0.0
    x-tasknotes:
      type: cron
      schedule: 0 9 * * *
      timezone: local
steps:
  - id: overdue
    action:
      id: task.query
      version: 1.0.0
    input:
      query:
        where:
          all:
            - field: task.due
              op: lt
              value:
                fn: today
            - field: task.status
              op: notIn
              value:
                - done
                - cancelled
        sort:
          - field: task.due
            direction: asc
        limit: 50
        scope:
          includeArchived: false
  - id: mark-high
    action:
      id: task.patch
      version: 1.0.0
    input:
      task:
        $expr: task.path
      patch:
        priority: high
    for_each:
      items:
        $expr: steps.overdue.output.tasks
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

# Morning overdue review

Runs while Obsidian is open. Use dry run first, then enable it when the query matches the right tasks.
