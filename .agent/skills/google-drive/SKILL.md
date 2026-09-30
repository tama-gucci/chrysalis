---
name: google-drive
description: "Optional Google Drive read-only integration skill for Chrysalis /ingest: resolves local Drive mounts or connected read-only Google Drive MCP transports, performs bounded pagination and file/text retrieval, and maps items into the v1.0.0 Ingestion Input Contract."
trigger: "/ingest --source"
domain: integration
integration_id: google-drive
contract_version: "1.0.0"
access: read-only
reads:
  - "System/Memory.md"
  - "Sources/*.md"
  - "contracts/ingestion-input.contract.md"
writes: []
---

# `google-drive` (Optional Read-Only File & Media Integration Skill)

## 1. Scope & Activation Boundary
This skill provides the **Google Drive** integration adapter (`integration: google-drive`) for [`/ingest`](../ingest/SKILL.md).
* **Explicit Activation Only:** Installing this skill in `.agent/skills/google-drive/SKILL.md` does **not** automatically activate Google Drive ingestion. It runs only when a source alias in `<vault>/System/Memory.md` (`ingestion.sources.<alias>`) is configured with `integration: google-drive` and `enabled: true`.
* **Read-Only Access Invariant (`access: read-only`):** This adapter never creates, modifies, moves, renames, or deletes files in Google Drive. Original binary files remain preserved in place inside the user's external media storage.
* **A2 Local Vault Execution:** This integration skill retrieves external file metadata/content and emits a `v1.0.0` `IngestionDiscoveryEnvelope` (`helpers/providers/google_drive.py`); all Chrysalis interpretation, validation, and local Markdown writes are executed by core `/ingest` on `<vault>` via the A2 Access Layer (`helpers/mdbase_helper.py` and `mdbase -C "<vault>"`).

---

## 2. Access Prerequisites & Supported Transports
1. **Local Google Drive Desktop Mount / Synced Directory (`local_mount`):**
   * Configured via `ingestion.sources.<alias>.local_mount_path` or `collection` in `<vault>/System/Memory.md` (or `$CHRYSALIS_MEDIA_LOCKER_PATH`).
   * Provides direct read-only byte access (`bytes_available: true`), allowing exact binary `sha256` computation (`sha256(raw_file_bytes)`) and bounded PDF stream inspection (`extract_pdf_bounded`).
2. **Connected Google Drive MCP Server (`google_drive_mcp_readonly`):**
   * When a read-only Google Drive MCP server is connected in the active agent session (Google Antigravity, OpenAI Codex, or Claude Code), retrieves file metadata (`id`, `name`, `mimeType`, `md5Checksum`, `headRevisionId`, `modifiedTime`, `webViewLink`) and exported text or binary streams.
   * When only exported text is returned by an MCP tool (`bytes_available: false`), `sha256` **must** be `null` and the text digest is recorded in `normalized_text_sha256`.

---

## 3. Bounded Discovery, Pagination & Explicit Statuses
Execute discovery via:
```bash
python helpers/mdbase_helper.py --runtime ingest-discover --source <alias> [--page-size <N>] [--page-token <token>]
```
* **Bounded Traversal:** Respects `max_discovery_depth` (default `6`), `discovery_roots` (e.g., `["01-Inbox", "02-Projects"]`), and `page_size` / `page_token`.
* **Pagination Reporting:** When more items exist beyond `page_size`, sets `pagination.truncated: true`, `pagination.next_page_token: "<token>"`, and `discovery_status: "partial_listing"`.
* **Explicit Discovery Status Taxonomy:**
  * `ok_empty`: Configured Drive folder exists, is readable, and contains 0 files.
  * `ok_fully_indexed`: All discovered files match complete existing `Sources/*.md` records.
  * `ok_items_available`: New, revised, renamed/moved, or incomplete items are available.
  * `partial_listing`: Results were bounded by `page_size` or `max_depth`.
  * `mount_unavailable`: Configured `local_mount_path` or Drive mount is disconnected or missing. Never reported as `0 unindexed files`.
  * `auth_failure`: MCP connector OAuth token is missing or expired.
  * `permission_denied`: Folder or file permissions prevent read access.
  * `operation_unavailable`: Neither a local mount nor a connected Google Drive MCP transport is available.

---

## 4. Identifier, Revision & Field Mapping (`v1.0.0` Contract)
Each discovered file maps to `content_kind: "file"` (or `"text"` when binary bytes are unavailable) via `helpers.providers.google_drive.map_google_drive_item_to_contract()`:
* `external_item_id`: Drive file ID (`file.id`) or normalized collection-relative path.
* `revision.external_revision`: Drive `headRevisionId` / `md5Checksum` or binary `sha256`.
* `locator`: `{ original_filename, relative_path, source_url, parent_external_id }` (folder container URLs `/drive/folders/...` are never assigned as individual file `source_url`s).
* `fingerprints`:
  * `bytes_available: true` $\to$ `sha256: "<64-hex>"`, `normalized_text_sha256: "<64-hex>|null"`.
  * `bytes_available: false` $\to$ `sha256: null`, `normalized_text_sha256: "<64-hex>"`.
* **Legacy Compatibility Note:** Legacy `/ingest --drive` and `ingestion_config` in `System/Memory.md` are mapped to `--source media` (`integration: google-drive`) by the compatibility translator in `helpers/ingestion_contract.py`.
