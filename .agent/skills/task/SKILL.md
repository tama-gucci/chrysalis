---
name: task
description: "Parses shorthand task input, extracts project tags and cognitive modalities, applies adaptive multipliers with a 1.00 fallback rule to baseline estimates, and creates TaskNotes markdown files."
trigger: "/task"
domain: runtime
reads:
  - "chrysalis/System/Scheduling-Memory.md"
writes:
  - "chrysalis/TaskNotes/Tasks/*.md"
---

# /task (Shorthand Task Capture Engine)

## Syntax
`/task [title] [tag] [priority] [est:Xm] [due:YYYY-MM-DD] [modality:analytical|kinetic|synthesis|administrative]`

## Processing Pipeline
1. **Title & Tag Extraction:** Parse task description and assign the corresponding `#pillar-X/*` tag from `chrysalis/System/Life-Roadmap.md`.
2. **Cognitive Modality Inference:**
   * If explicit modality is provided (e.g. `modality:kinetic`), assign it directly.
   * If omitted, infer from nature of task:
     - `analytical`: CAD, coding, drafting, writing, appeals, coursework.
     - `kinetic`: repairs, physical builds, hardware, cleaning, fabrication.
     - `synthesis`: Zettelkasten notes, reading, portfolio review.
     - `administrative`: student portals, emails, forms, payments.
3. **Multiplier Resolution & Fallback Rule:**
   * Read `tag_multipliers` from `chrysalis/System/Scheduling-Memory.md`.
   * Look up the active multiplier matching the assigned tag (baseline `1.00` fallback).
   * Compute effective duration:
     $$\text{timeEstimate} = \text{round}(\text{base\_estimate} \times \text{multiplier})$$
4. **File Generation:** Create a new file in `chrysalis/TaskNotes/Tasks/YYYYMMDD-slug.md` with complete YAML frontmatter:

```yaml
---
title: "Task Title"
status: todo
dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
created: "YYYY-MM-DDTHH:mm:ss-05:00"
due: "YYYY-MM-DD"
scheduled: null
priority: normal # urgent, high, normal, low
urgency_tier: 2 # 1-4
modality: analytical # analytical, kinetic, synthesis, administrative
timeEstimate: 45
energy: medium # high, medium, low
friction: medium # high, medium, low
micro_chunked: false
tags:
  - task
  - pillar-1/setup
---
```
