---
type: runtime_workflow
id: completed-task-to-canvas
version: 1.0.0
name: Add completed tasks to a canvas
description: Demonstrates portable TaskNotes, Workflows, and Canvas Bases interoperability.
enabled: false
triggers:
  - id: task-completed
    event:
      id: tasknotes.task.completed
      version: ^1.0.0
    x-tasknotes:
      type: contract.event
steps:
  - id: add-card
    action:
      id: canvas.card.create
      version: ^1.0.0
    input:
      canvas_path: chrysalis/Canvases/Completed tasks.canvas
      card:
        kind: file
        file:
          $expr: event.data.task_path
    provider:
      application: canvas-bases
run:
  concurrency:
    group: workflow
    policy: queue
  limits:
    max_items: 1
  on_error: stop
x-tasknotes:
  format_version: 1
  source: tasknotes-workflows
---

# Add completed tasks to a canvas

This disabled example is the smallest end-to-end interoperability flow:
TaskNotes publishes a contract event, this workflow consumes it, and Canvas
Bases provides the selected card-creation action. Enable local application
interoperability in mdbase settings before enabling the workflow.
