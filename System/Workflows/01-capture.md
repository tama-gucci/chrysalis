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
  - source_url
outputs:
  - source_id
  - sha256_digest
  - source_path
  - is_duplicate
---

# Workflow 01: Capture & Passive Quarantine (`/ingest` Stage 1)

## Objective
Accept external inputs across configured runtime source aliases (`/ingest --source <alias>` or `/ingest --all`, resolved from `ingestion.sources` in `<vault>/System/Memory.md` or `<vault>/System/Ingestion-Sources.md`, plus legacy `--drive` / `Chrysalis-Media-Locker/01-Inbox` compatibility) or direct session inputs (`/ingest`) via the versioned (`1.0.0`) Ingestion Input Contract (`contracts/ingestion-input.contract.md`), computing separated provenance fingerprints (`sha256`, `normalized_text_sha256`, `structured_payload_sha256`), quarantining untrusted payloads, and checking for cross-session duplicates via the **A2 Access Layer** without storing local `Resources/` binary files in the vault.

## Protocol Steps
1. **Configured Source & Entry Resolution (`/ingest`):**
   - **Protocol 1 (`/ingest --source <alias>` / `/ingest --all`):** Triggered automatically during nightly `/audit` (`/evening`) or on demand via `python helpers/mdbase_helper.py --runtime ingest-discover --all` (`discover_all_configured_sources` / `discover_configured_source`). Optional provider integration skills supplying `ingestion.discover` and `ingestion.read` (bound under `integrations.bindings.ingestion.sources.<alias>` or `ingestion.sources.<alias>`) emit normalized `v1.0.0` discovery envelopes (`file`, `text`, or `structured_task`). Legacy `/ingest --drive` (`Chrysalis-Media-Locker/01-Inbox`) translates to `--source media` with a deprecation warning. Original external files remain preserved in place (`preserve_originals_in_place: true`) with `source_url` captured when available; a local `Resources/` folder inside the vault is prohibited. Explicit status codes (`ok`, `empty`, `fully_indexed`, `partial_listing`, `unavailable`, `auth_failure`, `operation_unavailable`, `write_access_forbidden`) prevent reporting access failures as `0 unindexed files`.
   - **Protocol 2 (`/ingest` / `--share`):** Triggered when the user uploads, attaches, or pastes content directly in the active agent session (`source_alias: "direct-session"`, `integration: "direct-session"`).
2. **Strict `source_type` Enum & Contextual Role Mapping (`_types/source.md`):**
   - Map `source_type` into one of the valid `_types/source.md` enum values: `syllabus`, `transcript`, `pdf`, `web_page`, `audio`, or `lecture_recording` (whilst `structured_task` contract items materialize directly into `TaskNotes/Tasks/*.md` under `_types/task.md`).
   - Classify `location_category` (`unclassified_inbox`, `project_library`, `shared_reference`, `supporting_asset`, `announcements_deadlines_rubrics`) and `material_role` (`project_requirement`, `deliverable_instruction`, `shared_reference`, `supporting_asset`, `announcement_deadline`, `syllabus`).
3. **Strict Fingerprint Separation:**
   - `sha256`: Strictly the 64-character lowercase hex SHA-256 of original raw binary file bytes (`bytes_available: true`). Set `sha256: null` and `bytes_available: false` when raw binary bytes are unavailable.
   - `normalized_text_sha256`: 64-character lowercase hex SHA-256 of canonical UTF-8 extracted text for `file` or `text` items.
   - `structured_payload_sha256`: 64-character lowercase hex SHA-256 of canonicalized structured payload for `structured_task` items.
4. **Multi-Level Identity & Deduplication (A2 Access Layer):**
   - **File/Text Items (`evaluate_provider_file_identity` / `evaluate_source_identity`):**
     - `exact_duplicate`: Identical binary `sha256` and complete linked targets at the same provider $\to$ skip redundant extraction (`skipped_duplicate`).
     - `provider_relocated_candidate`: Identical binary `sha256` encountered under a different `integration`/`account_scope` $\to$ require explicit provenance update approval rather than silently rewriting provider provenance.
     - `renamed_or_moved`: Identical binary `sha256` at a new filename/path within the same provider $\to$ update `original_filename`, `relative_path`, and `previous_paths` (`updated_existing`).
     - `changed_version`: Same `source_url` or composite external identity with modified bytes $\to$ ingest as a revision (`supersedes: "[[Sources/<prior_id>]]"`).
   - **Structured Task Items (`evaluate_task_capture_identity`):**
     - Match by composite external identity `(integration, account_scope, collection_id, external_item_id)` — never collapse distinct tasks that share identical titles.
     - Unchanged `structured_payload_sha256` $\to$ `exact_duplicate` (`skipped_duplicate`).
     - Completed (`done`) or `archived` local task $\to$ `completed_locally_preserved` (never reopen).
     - Changed external payload with local edits (`user_modified`, `googleCalendarEventId`, `linked_zettels`, `project_ref`, `scheduled`) $\to$ `conflict_with_local_edits` (preserve local edits, populate `external_conflict_proposal`).
5. **Passive Text Quarantine & Anti-Control Sanitization:**
   - Apply escape sanitization via `helpers.ingestion_contract.sanitize_ingestion_item()` and `helpers.mdbase_helper.sanitize_untrusted_payload()`: neutralize `</untrusted_document_payload>` and escape leading YAML fence lines (`---`).
   - Wrap formatted Markdown translation inside `<untrusted_document_payload source_id="..." sha256="..." mime_type="...">`.
6. **Draft Source & Capture Records:** Prepare `<vault>/Sources/{source_id}.md` using `_templates/Source-Template.md` (and draft candidate task notes for `structured_task` items), and transition to `02-extract.md`.
