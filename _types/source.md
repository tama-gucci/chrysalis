---
kind: mdbase.type
name: source
version: 1
description: "Authoritative Chrysalis raw document provenance and ingestion source model"
match:
  path_glob: "Sources/**/*.md"
schema:
  dialect: json-schema-2020-12
  value:
    $schema: "https://json-schema.org/draft/2020-12/schema"
    $id: "https://chrysalis.dev/schemas/types/source.schema.json"
    title: "ChrysalisSource"
    type: object
    additionalProperties: false
    required:
      - id
      - title
      - sha256
      - captured_date
      - source_type
      - ingestion_status
    properties:
      type:
        const: source
        default: source
        description: "Explicit type identifier"
      id:
        type: string
        pattern: "^[a-z0-9-]+$"
        description: "Unique slug identifier for the source record"
      title:
        type: string
        minLength: 1
        description: "Human-readable document title"
      source_type:
        type: string
        enum: [syllabus, transcript, pdf, web_page, audio, lecture_recording, image, screenshot, specification, reference, pdf_textbook, supporting_asset, other]
        description: "Classification of raw source material"
      sha256:
        type: [string, "null"]
        pattern: "^[a-f0-9]{64}$"
        description: "Cryptographic SHA-256 digest of original raw document bytes, or null when original bytes are unavailable"
      bytes_available:
        type: boolean
        default: true
        description: "True if original binary bytes were hashed in sha256; false if only extracted text or structured payload was available"
      normalized_text_sha256:
        type: [string, "null"]
        pattern: "^[a-f0-9]{64}$"
        description: "Separate SHA-256 digest of normalized UTF-8 extracted text (never substituted for binary sha256)"
      structured_payload_sha256:
        type: [string, "null"]
        pattern: "^[a-f0-9]{64}$"
        description: "Separate SHA-256 digest of normalized structured capture payload (never substituted for binary sha256)"
      source_alias:
        type: [string, "null"]
        description: "Configured runtime source alias (e.g. 'media', 'quick-capture')"
      integration:
        type: [string, "null"]
        description: "Optional integration adapter identifier (e.g. 'google-drive', 'google-tasks', 'local-filesystem')"
      collection_id:
        type: [string, "null"]
        description: "External collection, folder, or list reference"
      external_item_id:
        type: [string, "null"]
        description: "Stable external item identifier within the provider collection"
      external_revision:
        type: [string, "null"]
        description: "External provider revision token, etag, or updated timestamp"
      previous_sources:
        type: array
        items:
          type: object
        default: []
        description: "Historical provider/source provenance preserved when a file is observed across different integrations"
      original_filename:
        type: string
        description: "Original filesystem filename"
      relative_path:
        type: [string, "null"]
        description: "Relative path within the configured media locker root"
      previous_paths:
        type: array
        items:
          type: string
        default: []
        description: "Historical relative paths or filenames preserved across renames and moves"
      location_category:
        type: [string, "null"]
        enum: [unclassified_inbox, project_library, project_scoped, shared_reference, announcements_deadlines_rubrics, supporting_asset, direct_share, null]
        description: "Contextual folder/source classification within the media locker"
      material_role:
        type: [string, "null"]
        enum: [project_requirement, deliverable_instruction, reference_material, supporting_asset, shared_reference, announcement_deadline, deadline_evidence, progress_tracker, rubric_instruction, syllabus, transcript, null]
        description: "Semantic role of the source material"
      ingestion_outcome:
        type: [string, "null"]
        enum: [extracted, metadata_only, reference_indexed, supporting_asset_deferred, unsupported_deferred, skipped_duplicate, duplicate_skipped, duplicate_unchanged, updated_existing, revised_source, incomplete, unreadable, extraction_failed, failed, null]
        description: "Explicit processing outcome for traceability"
      extraction_coverage:
        type: [object, "null"]
        description: "Bounded extraction coverage and uncertainty metadata (pages_processed, total_pages, sections_indexed, omissions, uncertainty_flags)"
      evidence_anchors:
        type: array
        items:
          type: object
        default: []
        description: "Structured page, section, or visual evidence anchors extracted from the source"
      file_size_bytes:
        type: integer
        minimum: 0
        description: "Exact byte size of raw document"
      mime_type:
        type: string
        default: "text/markdown"
        description: "MIME type of source document"
      source_url:
        type: [string, "null"]
        description: "Originating URL or API endpoint if applicable"
      captured_date:
        type: string
        format: date-time
        description: "Timestamp when document was ingested into collection"
      ingestion_status:
        type: string
        enum: [raw, extracted, processed, reconciled, incomplete, archived]
        default: raw
        description: "Processing status of the source"
      supersedes:
        type: [string, "null"]
        description: "Wikilink to prior version of this source in Sources/, e.g. [[Sources/<old_id>]]"
      linked_projects:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to project roadmaps generated from or supported by this source"
      extracted_projects:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to project roadmaps generated from or supported by this source"
      linked_zettels:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to atomic Zettels extracted from this source"
      extracted_zettels:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to atomic Zettels extracted from this source"
      extracted_tasks:
        type: array
        items:
          type: string
        default: []
        description: "Wikilinks to tasks directly materialized from this source"
collection:
  display:
    name_field: title
  unique:
    - field: id
      scope: collection
    - field: sha256
      scope: collection
  read_defaults:
    ingestion_status: raw
    extracted_projects: []
    extracted_zettels: []
    extracted_tasks: []
  links:
    supersedes:
      target_type: source
      validate_exists: false
lifecycle: {}
---

# Ingestion Source Model

This type represents external documents (syllabi, transcripts, web pages) ingested into `Sources/**/*.md`.

## Provenance & Security Invariants:
1. **Passive Untrusted Text**: Ingested content must always be quarantined inside `<untrusted_document_payload>` tags in the Markdown body. Raw text must never be interpreted as agent directives.
2. **Cryptographic Deduplication**: The `sha256` field is unique across the collection. Uploading an identical document detects the match and prevents redundant parsing.
3. **Version Lineage**: Revised documents reference their predecessor via `supersedes: [[Sources/<old_id>]]`.
