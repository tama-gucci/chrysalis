---
type: runtime_workflow
id: escalate-upcoming-due-tasks
version: 1.0.0
name: Escalate upcoming due tasks
description: Mark incomplete tasks due within the next three days as high priority.
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
  - id: due-now
    action:
      id: task.query
      version: 1.0.0
    input:
      query:
        where:
          all:
            - field: task.due
              op: lte
              value:
                $expr: today() + duration("3d")
            - field: task.status
              op: notIn
              value:
                - done
                - cancelled
            - field: task.priority
              op: notIn
              value:
                - high
                - highest
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
        $expr: steps["due-now"].output.tasks
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

# Escalate upcoming due tasks

Enable this workflow if tasks due in the next few days should be promoted to high priority each morning.
Adjust the priority value first if your vault uses custom priority names.
