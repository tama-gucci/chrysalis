---
title: "Imperative Task Title"
status: todo # Allowed values: todo, in-progress, done, archived
dateCreated: "{{TIMESTAMP}}"
created: "{{TIMESTAMP}}" # Backward-compatible alias
due: "{{DUE_DATE}}"
scheduled: null # Format: "YYYY-MM-DDTHH:mm:ss{{TIMEZONE_OFFSET}}" or null
priority: normal # Allowed values: urgent, high, normal, low
urgency_tier: 2 # Scale: 1 (Lowest) to 4 (Highest)
modality: analytical # Allowed values: analytical, kinetic, synthesis, administrative
timeEstimate: 45 # In minutes (baseline duration * active tag multiplier)
energy: medium # Allowed values: high, medium, low
friction: medium # Allowed values: high, medium, low
micro_chunked: false # Boolean: true if a 3-step Starter Wedge has been injected
tags:
  - task
  - pillar-1/setup # Must reference a tag defined in Life-Roadmap.md
---

# Imperative Task Title

## Context & Objective
Brief 1-2 sentence description of the deliverable and success criteria.

## Execution Checklist
- [ ] Step 1: Open project workspace and verify dependencies
- [ ] Step 2: Execute primary analytical or synthesis work
- [ ] Step 3: Verify and record deliverable output
