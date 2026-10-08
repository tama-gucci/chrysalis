---
title: chrysalis
type: dashboard
---

# chrysalis

TaskNotes supplies the task, calendar and session UI. Open a supplied view in `TaskNotes/Views`.
The following optional Dataview projection uses the same task notes.

```dataview
TABLE priority, due, scheduled, timeEstimate, modality
FROM "TaskNotes/Tasks"
WHERE status != "done" AND status != "archived" AND file.name != "example-task"
SORT scheduled ASC, due ASC
```

Daily focus is in `Daily`; project ledgers are in `Projects`. Notes and original documents
remain readable when optional projections are unavailable.
