---
kind: mdbase.type
name: system_state
version: 1
description: "Authoritative Chrysalis runtime state and strategic roadmap records in System/"
match:
  path_glob: "System/*.md"
schema:
  dialect: json-schema-2020-12
  value:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    $id: "https://chrysalis.dev/schemas/types/system_state.schema.json"
    title: "ChrysalisSystemState"
    type: object
    additionalProperties: true
    properties:
      type:
        type: string
        enum: [system_state, strategic_roadmap, system_health, system_health_report, system_specification, system_memory_extension]
      id:
        type: string
      version:
        type: string
      schema_version:
        type: string
      last_updated:
        type: string
---

# System State & Strategic Roadmap Type Specification (`_types/system_state.md`)

Validates Chrysalis runtime state records (`System/Life-Roadmap.md`, `System/Memory.md`, and `System/System-Health.md`) as canonical mdbase v0.3 records.
