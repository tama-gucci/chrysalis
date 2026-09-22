---
type: runtime_workflow
id: daily-active-task-review
version: 1.0.0
name: Daily active task review
description: Show a daily count of tasks still marked active.
enabled: false
triggers:
  - id: weekday-evening
    event:
      id: tasknotes-workflows.schedule.cron
      version: 1.0.0
    x-tasknotes:
      type: cron
      schedule: 0 17 * * 1-5
      timezone: local
steps:
  - id: active-tasks
    action:
      id: task.query
      version: 1.0.0
    input:
      query:
        where:
          field: task.status
          op: eq
          value: active
        scope:
          includeArchived: false
  - id: show-count
    action:
      id: notice.show
      version: 1.0.0
    input:
      message: You have {{steps.active-tasks.output.count}} active task(s) to review.
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

# Daily active task review

Enable this workflow if you want a weekday reminder to close out tasks still marked active.
