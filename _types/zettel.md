---
kind: mdbase.type
name: zettel
version: 1
description: "Authoritative Chrysalis atomic research note and Slipbox knowledge model"
match:
  path_glob: "Slipbox/**/*.md"
schema:
  dialect: json-schema-2020-12
  value:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    $id: "https://chrysalis.dev/schemas/types/zettel.schema.json"
    title: "ChrysalisZettel"
    type: object
    additionalProperties: false
    required:
      - id
      - title
      - dateCreated
      - tags
    properties:
      type:
        const: zettel
        default: zettel
        description: "Explicit type identifier"
      id:
        type: string
        pattern: "^[0-9]{14}(-[a-z0-9-]+)?$"
        description: "14-digit local timestamp ID (YYYYMMDDHHmmss) with optional kebab-case slug"
      title:
        type: string
        minLength: 1
        description: "Atomic claim or concept title"
      dateCreated:
        type: string
        format: date-time
        description: "Creation timestamp with explicit local offset"
      tags:
        type: array
        minItems: 1
        items:
          type: string
        description: "Concept and domain tags, e.g. concept/algorithms, #chrysalis"
      source_ref:
        type: [string, "null"]
        description: "Wikilink to raw ingestion source in Sources/, e.g. [[Sources/<id>]]"
      source_checksum:
        type: [string, "null"]
        pattern: "^[a-f0-9]{64}$"
        description: "Cryptographic SHA-256 digest of originating lecture or document"
      source_url:
        type: [string, "null"]
        description: "External web URL if applicable"
      project_ref:
        type: [string, "null"]
        description: "Wikilink to parent project roadmap"
      linked_zettels:
        type: array
        items:
          type: string
        default: []
        description: "Bidirectional wikilinks to related atomic Zettels"
      integration_status:
        type: string
        enum: [unintegrated, staged, integrated]
        default: unintegrated
        description: "Knowledge synthesis and review state"
collection:
  display:
    name_field: title
  unique:
    - field: id
      scope: collection
  read_defaults:
    integration_status: unintegrated
    linked_zettels: []
    tags: ["zettel"]
  links:
    project_ref:
      target_type: project
      validate_exists: false
    source_ref:
      target_type: source
      validate_exists: false
    linked_zettels[]:
      target_type: zettel
      validate_exists: false
lifecycle:
  on_create:
    set:
      dateCreated: { now: true }
---

# Knowledge Zettel Model

This type defines atomic Zettelkasten knowledge notes in `Slipbox/**/*.md`.

## Core Invariants:
1. **Atomic Thesis**: Each note encapsulates exactly one mental model, theoretical concept, or system evolution idea (`#chrysalis`).
2. **Timestamp Identity**: IDs are prefixed with a 14-digit local timestamp `YYYYMMDDHHmmss` guaranteeing chronological uniqueness.
3. **Cryptographic Grounding**: When extracted from a lecture transcript or paper, notes link back to `source_ref` and embed `source_checksum`.
