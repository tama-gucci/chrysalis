---
kind: chrysalis.type
name: zettel
version: 1
description: "Authoritative Chrysalis atomic research note and Slipbox knowledge model"
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
      created:
        type: string
        format: date-time
        description: "Optional creation timestamp"
      tags:
        type: array
        minItems: 1
        items:
          type: string
        description: "Concept and domain tags, e.g. concept/algorithms, #chrysalis"
      summary:
        type: string
        maxLength: 500
        description: One sentence locating this atomic claim in the knowledge index
      source_refs:
        type: array
        maxItems: 100
        uniqueItems: true
        items: {type: string}
        description: Exact Sources WikiLinks supporting the note across multiple captures
      provenance_kind:
        enum: [source, personal, inference]
        description: Source-grounded, user-confirmed personal knowledge, or explicitly labeled inference
      knowledge_status:
        enum: [current, disputed, outdated]
        description: Claim status; contested claims also need cited explanations in the body
      content_updated_at:
        type: string
        format: date-time
        description: Local timestamp of the last knowledge-content change, not formatting or access
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
      related_zettels:
        type: array
        items:
          type: string
        default: []
        description: "Optional related knowledge links"
      integration_status:
        type: string
        enum: [unintegrated, staged, integrated]
        default: unintegrated
        description: "Knowledge synthesis and review state"
---

# Knowledge Zettel Model

This type defines atomic Zettelkasten knowledge notes in `Slipbox/*.md`.

## Core Invariants:
1. **Atomic Thesis**: Each note encapsulates exactly one mental model, theoretical concept, or system evolution idea (`#chrysalis`).
2. **Timestamp Identity**: IDs use a 14-digit local timestamp `YYYYMMDDHHmmss` plus a distinct slug; a timestamp alone is not unique.
3. **Cryptographic Grounding**: When extracted from a lecture transcript or paper, notes link back to `source_ref`; include `source_checksum` only when original raw bytes were observed.
   Text-only or conversational evidence does not have a binary checksum.
