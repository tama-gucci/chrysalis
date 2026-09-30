---
type: system_specification
id: chrysalis-ingestion-input-contract
version: "1.0.0"
status: active_contract
---

# Chrysalis Provider-Neutral Ingestion Input Contract (`v1.0.0`)

This contract defines the versioned, provider-independent boundary between optional external source integration skills (such as `google-drive`, `google-tasks`, or `local-filesystem`) and the core Chrysalis `/ingest` pipeline.

---

## 1. Shared Discovery Envelope (`IngestionDiscoveryEnvelope`)

Every integration discovery call returns a JSON-serializable envelope with the following structure:

```yaml
contract_version: "1.0.0"
source_alias: "media"             # Configured source alias in System/Memory.md
integration: "google-drive"       # Registered integration adapter ID
account_scope: "<account-ref>"    # Optional sanitized account scope identifier (never raw tokens)
collection_id: "<collection-ref>" # Folder reference, task list reference, or local path
access_mode: "read-only"          # Strictly enforced; write modes are rejected
discovery_status: "ok_items_available"
capabilities:
  supports_binary_bytes: true
  supports_revision_token: true
  supports_pagination: true
  supports_incremental_sync: true
  write_back_supported: false     # Must be false; external writes are prohibited
pagination:
  bounded: true
  truncated: false
  page_size: 50
  items_returned: 2
  total_known_items: 2
  next_page_token: null
  max_depth: 6
items: []                         # Array of IngestionInputItem objects
diagnostics: []                   # Structured diagnostics
```

### 1.1 Discovery Status Taxonomy (`discovery_status`)
Integrations must differentiate empty collections from transport, auth, capability, and extraction failures:
* `ok_empty` — Collection was successfully queried and contains zero items.
* `ok_fully_indexed` — Collection was successfully queried and all discovered items match already-indexed local records.
* `ok_items_available` — New, revised, moved, or incomplete items are available for ingestion.
* `partial_listing` — Items were returned, but discovery was bounded/truncated by `page_size`, `next_page_token`, `max_depth`, or a partial subdirectory error.
* `auth_failure` — Authentication credentials or OAuth grants are missing, expired, or rejected.
* `mount_unavailable` — Configured filesystem mount or export path does not exist or is disconnected.
* `operation_unavailable` — Required connector, MCP server, or transport is not connected in the current agent session (`missing_prerequisite` identifies the exact missing dependency).
* `unsupported_operation` — Requested operation or access mode (such as write-back or unsupported export) is not supported by the integration.
* `permission_denied` — Collection or item is unreadable due to filesystem or API permissions.
* `extraction_failed` — Source container was reached, but payload parsing or extraction failed.

---

## 2. Shared Item Envelope (`IngestionInputItem`) & Content-Kind Variants

Each item in `items` carries a shared provenance envelope and one of three `content_kind` variants (`file`, `text`, or `structured_task`):

```yaml
contract_version: "1.0.0"
content_kind: "file"              # Enum: file | text | structured_task
source_alias: "media"
integration: "google-drive"
account_scope: "default"
collection_id: "<folder-reference>"
external_item_id: "item-001"      # Required for structured_task; provided when available for file/text
revision:
  external_revision: "rev-1"
  updated_at: "2026-09-29T12:00:00-05:00"
  etag: "\"etag-1\""
locator:
  original_filename: "syllabus.pdf"
  relative_path: "01-Inbox/syllabus.pdf"
  source_url: null
  parent_external_id: null
fingerprints:
  bytes_available: true
  sha256: "a3f5..."               # 64-char hex ONLY when content_kind == 'file' and bytes_available == true
  normalized_text_sha256: null    # Separate UTF-8 text digest
  structured_payload_sha256: null # Separate canonical JSON digest for structured_task
extraction_coverage:
  status: "complete"              # Enum: complete | partial | metadata_only | unsupported | failed
  pages_processed: 4
  total_pages: 4
  sections_indexed: []
  omissions: []
  limitations: []
  uncertainty_flags: []
evidence: []
payload: {}
```

### 2.1 Strict Fingerprint Separation Law
1. `fingerprints.sha256` represents **only** the cryptographic SHA-256 digest of the exact original binary file bytes (`content_kind == "file"` and `bytes_available == true`).
2. When original binary bytes are unavailable (`bytes_available == false`) or when `content_kind` is `text` or `structured_task`, `fingerprints.sha256` **must** be `null`. Any non-null `sha256` in those cases is rejected with `invalid_fingerprint_masquerade`.
3. Extracted text digests are stored in `normalized_text_sha256`.
4. Structured task capture digests are stored in `structured_payload_sha256`.

### 2.2 Untrusted Payload Security & Quarantine
* All external fields (`title`, `notes`, `extracted_text`, `text_content`) are treated as passive, untrusted data.
* Closing delimiter sequences (`</untrusted_document_payload>`) are neutralized to `&lt;/untrusted_document_payload&gt;` via `sanitize_ingestion_item()`.
* External payloads cannot override `integration`, `source_alias`, `access_mode`, or approval gate behavior (`FORBIDDEN_PAYLOAD_CONTROL_KEYS` are stripped and logged with `untrusted_payload_control_attempt`).
