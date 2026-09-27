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
        enum: [system_state, strategic_roadmap, system_health]
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

Enables MCP agents (`@Mdbase` in Gemini Spark) to read and update `System/Life-Roadmap.md`, `System/Memory.md`, and `System/System-Health.md` directly via canonical mdbase v0.3 operations.
