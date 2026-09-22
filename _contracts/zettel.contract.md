---
kind: mdbase.contract
id: zettel-contract
version: "0.3.0"
target_type: zettel
description: "Authoritative data contract for Chrysalis atomic research notes and Slipbox knowledge in mdbase v0.3"
---

# Knowledge Zettel Data Contract

## 1. Scope and Identity
This contract governs all atomic research notes located in `Slipbox/**/*.md`.
- **Identity Pattern**: `Slipbox/{YYYYMMDDHHmmss}-{slug}.md`.
- **Target Type**: `zettel` conforming to `_types/zettel.md`.
- **Identifier Syntax**: 14-digit local timestamp ID with optional kebab slug matching `^[0-9]{14}(-[a-z0-9-]+)?$`.

## 2. Core Principles
- **Atomic Thesis**: Every note must capture exactly one discrete mental model, concept, or system evolution proposal (`#chrysalis`).
- **Bidirectional Hypergraph Grounding**:
  - `project_ref`: Wikilink to parent project roadmap (e.g. `[[Projects/cs410/Roadmap]]`).
  - `source_ref`: Wikilink to originating ingestion source in `Sources/` (e.g. `[[Sources/lecture-01-recording]]`).
  - `source_checksum`: 64-character lowercase hexadecimal SHA-256 digest of original material.
  - `linked_zettels`: Array of wikilinks connecting related concepts.

## 3. Integration Lifecycle
Zettel integration follows a three-stage lifecycle:
- `unintegrated`: Freshly extracted candidate note pending human synthesis.
- `staged`: Reviewed and placed into active project context.
- `integrated`: Fully woven into the Chrysalis Hypergraph with cross-links and empirical operational applications.

## 4. Format Invariant
All timestamps must serialize with explicit local timezone offsets (e.g. `-05:00`). Raw UTC `"Z"` strings violate this contract.
