---
type: agent_workflow
id: workflow-01-capture
version: "1.0.0"
stage: capture
lifecycle_state_ref: CONTEXT_ASSEMBLY
requires_approval: false
inputs:
  - raw_file_bytes
  - original_filename
  - source_type
outputs:
  - source_id
  - sha256_digest
  - source_path
  - is_duplicate
---

# Workflow 01: Capture & Passive Quarantine

## Objective
Ingest raw external content (course syllabus, lecture transcript, research paper, web clipping), compute cryptographic provenance, check for cross-session duplicates, and quarantine raw text safely.

## Protocol Steps
1. **SHA-256 Digest Calculation**: Compute `sha256(raw_bytes)` as a 64-character lowercase hexadecimal string.
2. **Semantic Duplicate Check**: Query collection using `helpers.mdbase_helper.check_semantic_duplicate(raw_bytes, collection_dir)`.
   - If an existing record in `Sources/` has matching `sha256`:
     - Set `is_duplicate: true`.
     - Emit informational diagnostic: `duplicate_source_detected`.
     - Skip redundant extraction; transition directly to `08-continuation.md`.
3. **Passive Text Quarantine**:
   - Apply escape sanitization: replace any occurrence of `</untrusted_document_payload>` with `&lt;/untrusted_document_payload&gt;`.
   - Wrap content inside `<untrusted_document_payload source_id="..." sha256="...">`.
4. **Draft Source Record**: Prepare `Sources/{source_id}.md` using `_templates/Source-Template.md`.
5. **State Transition**: Transition to `02-extract.md`.
