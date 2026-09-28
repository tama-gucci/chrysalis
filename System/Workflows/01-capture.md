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
Translate external binary or unstructured source files from the dedicated Google Drive inbox (`Chrysalis-Media-Locker/01-Inbox` via `/ingest --drive` during nightly `/audit`, accessed via a connected Google Drive MCP server or local Google Drive desktop mount) or direct share/attachment in the active local agent session (`/ingest`) into a quarantined Markdown source provenance record (`<vault>/Sources/{source_id}.md`), computing cryptographic provenance and checking for cross-session duplicates via the A2 access layer without storing any local `Resources/` binary files in the vault.

## Protocol Steps
1. **Google Drive Media Locker & Entry Resolution (`/ingest`):**
   - **Protocol 1 (`/ingest --drive`):** Triggered automatically during nightly `/audit` (`/evening`) or on demand to scan `ingestion_config.drive_inbox_folder` (`Chrysalis-Media-Locker/01-Inbox` in `System/Memory.md`) via the connected **Google Drive MCP server** (or local Google Drive mount). Original binary files remain in Google Drive (`Chrysalis-Media-Locker/02-Archived-Binaries`) with their URL captured in `source_url`; a local `Resources/` folder inside the vault is prohibited.
   - **Protocol 2 (`/ingest` / `--share`):** Triggered when the user uploads, attaches, or pastes content directly in the active agent session (Google Antigravity, OpenAI Codex, Claude Code, or local CLI). Extracts text/tables/OCR/transcript in-context and records the Google Drive or web link in `source_url` (or `null` if transient).
2. **Strict `source_type` Enum Mapping (`_types/source.md`):**
   - Map the source into one of the 6 valid enum values: `syllabus`, `transcript`, `pdf`, `web_page`, `audio`, or `lecture_recording`.
3. **SHA-256 Digest Calculation:** Compute `sha256(raw_bytes)` as a 64-character lowercase hexadecimal string.
4. **Semantic Duplicate Check (A2 Access Layer):** Query the local vault collection using `python helpers/mdbase_helper.py --vault "<vault>" check-duplicate <file>` (`helpers.mdbase_helper.check_semantic_duplicate(raw_bytes, collection_dir, source_url=source_url)`) or `mdbase -C "<vault>" query --types source`.
   - If an existing record in `<vault>/Sources/` has matching `sha256`:
     - Set `is_duplicate: true`.
     - Emit informational diagnostic: `duplicate_source_detected`.
     - Skip redundant extraction; transition directly to `08-continuation.md`.
5. **Passive Text Quarantine:**
   - Apply escape sanitization via `helpers.mdbase_helper.sanitize_untrusted_payload()`: replace any occurrence of `</untrusted_document_payload>` with `&lt;/untrusted_document_payload&gt;`.
   - Wrap formatted Markdown translation inside `<untrusted_document_payload source_id="..." sha256="..." mime_type="...">`.
6. **Draft Source Record:** Prepare `<vault>/Sources/{source_id}.md` using `_templates/Source-Template.md` (`type: source`, `source_url`, `captured_date` with explicit local offset `"-05:00"`), and validate via `python helpers/mdbase_helper.py --vault "<vault>" validate "<vault>/Sources/{source_id}.md"`.
7. **State Transition:** Transition to `02-extract.md`.
