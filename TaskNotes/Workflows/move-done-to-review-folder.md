---
type: runtime_workflow
id: move-done-to-review-folder
version: 1.0.0
name: Move completed tasks to review
description: Move completed tasks into a review folder for later archiving.
enabled: false
triggers:
  - id: completed
    event:
      id: task.completed
      version: 1.0.0
    x-tasknotes:
      type: tasknotes.event
steps:
  - id: move
    action:
      id: task.move
      version: 1.0.0
    input:
      task:
        $expr: event.after.path
      targetFolder: TaskNotes/Review
run:
  concurrency:
    group: workflow
    policy: skip
  limits:
    max_items: 1
  on_error: stop
x-tasknotes:
  format_version: 1
  source: tasknotes-workflows
  conditions:
    - field: event.after.path
      operator: exists
---

# Move completed tasks to review

This is intentionally disabled by default. Change `targetFolder`, dry-run it, then enable it.
