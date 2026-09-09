---
type: runtime_workflow
id: blocked-task-review
version: 1.0.0
name: Blocked task review
description: Show a weekday count of incomplete tasks that are currently blocked.
enabled: false
triggers:
  - id: weekday-morning
    event:
      id: tasknotes-workflows.schedule.cron
      version: 1.0.0
    x-tasknotes:
      type: cron
      schedule: 0 9 * * 1-5
      timezone: local
steps:
  - id: blocked-tasks
    action:
      id: task.query
      version: 1.0.0
    input:
      query:
        where:
          all:
            - field: task.isBlocked
              op: isTrue
            - field: task.status
              op: notIn
              value:
                - done
                - cancelled
        sort:
          - field: task.due
            direction: asc
        limit: 25
        scope:
          includeArchived: false
  - id: show-count
    action:
      id: notice.show
      version: 1.0.0
    input:
      message: You have {{steps.blocked-tasks.output.count}} blocked task(s) to review.
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
---

# Blocked task review

Enable this workflow if you want a weekday reminder when incomplete tasks are still blocked by dependencies.
