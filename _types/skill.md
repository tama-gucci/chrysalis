---
name: skill
description: Chrysalis runtime modular skill definition exposed to remote MCP agents.
strict: false
match:
  path_glob: "Skills/**/SKILL.md"
fields:
  name:
    type: string
    required: true
  description:
    type: string
    required: true
  trigger:
    type: string
  domain:
    type: string
  reads:
    type: list
    items:
      type: string
  writes:
    type: list
    items:
      type: string
---

# Chrysalis Runtime Skill Schema
