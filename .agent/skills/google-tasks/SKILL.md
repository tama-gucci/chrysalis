---
name: google-tasks
description: "Optional Google Tasks one-way read-only capture skill for Chrysalis /ingest: normalizes external tasks into v1.0.0 structured_task contract items, preserves date-only deadlines and local state, and prohibits external write-backs."
trigger: "/ingest --source"
domain: integration
integration_id: google-tasks
contract_version: "1.0.0"
access: read-only
reads:
  - "System/Memory.md"
  - "TaskNotes/Tasks/*.md"
  - "TaskNotes/Archive/*.md"
  - "Sources/*.md"
  - "contracts/ingestion-input.contract.md"
writes: []
---

# `google-tasks` (Optional One-Way Structured Task Capture Skill)

## 1. Scope & One-Way Read-Only Boundary
This skill provides the **Google Tasks** one-way capture integration (`integration: google-tasks`) for [`/ingest`](../ingest/SKILL.md).
* **Explicit Activation Only:** Installing `.agent/skills/google-tasks/SKILL.md` does **not** automatically activate Google Tasks capture. It runs only when a source alias in `<vault>/System/Memory.md` (e.g. `ingestion.sources.quick-capture`) is configured with `integration: google-tasks` and `enabled: true`.
* **Authoritative Local Execution Store:** Chrysalis `TaskNotes/Tasks/*.md` remains the sole authoritative execution store. Google Tasks is strictly a **read-only capture input** (`access: read-only`, `write_back_supported: false`).
* **Zero External Write-Back:** Importing tasks **never** completes, deletes, moves, reorders, or reschedules items in Google Tasks. Bidirectional synchronization is prohibited.
* **A2 Local Vault Execution:** Normalization, deduplication, and proposal drafting execute via `helpers/providers/google_tasks.py` and `helpers/ingestion_contract.py`, entering the standard A2 proposal pipeline (`prevalidate-proposal` $\to$ human approval gate $\to$ `apply-proposal`).

---

## 2. Access Prerequisites, Transports & Limitations
1. **Supported Read-Only Transports:**
   * **Google Tasks MCP Server (`transport: mcp`, `mcp_server: "gtasks-mcp"`):** Queries `gtasks-mcp` read-only tools (`list_task_lists` and `list` with `taskListId`), parses output via `helpers.providers.google_tasks.parse_gtasks_mcp_list_output()`, and caches or passes the read-only snapshot (`mcp_snapshot_path: ".chrysalis/mcp_cache/gtasks-mcp.json"` or `--synthetic-response`) into `discover_google_tasks_source()`.
   * **Read-Only Google Tasks Connector / API Response (`google_tasks_readonly_connector`):** Consumes `tasks#tasks` list payloads (`items[]` with `id`, `title`, `notes`, `due`, `status`, `updated`, `etag`, `parent`, `links`, `nextPageToken`).
   * **Exported JSON / Fixture Payload (`google_tasks_json_export`):** Configured via `export_path` in `ingestion.sources.<alias>` or `--synthetic-response` for offline/export ingestion.
2. **Honest Prerequisite & Availability Reporting:**
   * This repository does not bundle a live Google Tasks OAuth daemon; it connects to a user-configured read-only MCP server (`gtasks-mcp`) or export/snapshot path.
   * When invoked without a connected read-only Google Tasks connector, MCP snapshot, or configured `export_path`, `discover_google_tasks_source()` returns `discovery_status: "operation_unavailable"` with `missing_prerequisite: "google-tasks-read-connector"`. It **never** fabricates tasks or misreports an unavailable connector as an empty task list (`ok_empty`).

---

## 3. Bounded Discovery & Pagination
Execute discovery via:
```bash
python helpers/mdbase_helper.py --runtime ingest-discover --source <alias> [--page-size <N>] [--page-token <token>]
```
* **Pagination:** Honors `page_size` (`maxResults`) and `page_token` (`pageToken`). If `nextPageToken` is present or items exceed `page_size`, sets `pagination.truncated: true` and `discovery_status: "partial_listing"`.
* **No Deletion Inference:** Incomplete listings, paginated slices, or items missing from subsequent polls **never** delete, archive, or modify existing local tasks in `TaskNotes/Tasks/*.md`.

---

## 4. Field Mapping, Deadline Fidelity & Repeat-Import Rules (`v1.0.0` Contract)
Each Google Task maps to `content_kind: "structured_task"` via `helpers.providers.google_tasks.map_google_task_to_contract()`:
1. **Composite Identity & Non-Collapsing Titles:**
   * Items are identified by `(integration, account_scope, collection_id, external_item_id)` where `external_item_id` is Google Tasks `task.id`.
   * Distinct tasks with identical `title` or `notes` but different `external_item_id` values are **never** collapsed into one local task.
2. **Strict Fingerprint Separation:**
   * Sets `fingerprints.bytes_available: false` and `fingerprints.sha256: null`.
   * Computes `fingerprints.structured_payload_sha256` (64-char lowercase hex SHA-256 over canonical normalized fields).
3. **Date-Only vs. Timed Deadline Fidelity (`parse_google_tasks_due`):**
   * The Google Tasks API stores `due` as a date-only timestamp (`"YYYY-MM-DDT00:00:00.000Z"`).
   * Unless an explicit clock time is supplied in source evidence, `parse_google_tasks_due()` normalizes `"YYYY-MM-DDT00:00:00.000Z"` to `due: "YYYY-MM-DD"`, `due_time: null`, `due_timezone: null`, `due_at: null`, `due_is_date_only: true`. It **never** invents a time of day.
   * Tasks without a `due` field normalize to `due: null`, `date_uncertain: true`, `horizon_bucket: "uncertain"`.
4. **Source Evidence vs. Framework Defaults:**
   * Does not invent missing dates, priorities, durations, recurrence, project roadmaps (`project_ref: null`), or Zettels (`linked_zettels: []`).
   * Explicitly records `source_evidence` versus Chrysalis `framework_defaults` (`priority: normal`, `urgency_tier: 2`, `modality: administrative`, `timeEstimate: 45`, `scheduled: null`).
5. **Standalone Future-Dated Capture Policy (`due > today + 14d`):**
   * Because standalone captured tasks (`project_ref: null`) have no parent `Projects/*/Roadmap.md` ledger to store out-of-horizon items, standalone tasks with `due > today + 14d` are **never** silently dropped; they are drafted as inert tasks (`status: todo`, `scheduled: null`, `horizon_bucket: "future"`) in `TaskNotes/Tasks/` linked to their `Sources/` provenance record.
6. **Repeat Imports, Completed Work & Local Edit Conflict Proposals:**
   * Unchanged repeat imports (`external_payload_sha256` match) return `exact_duplicate` (`skipped_duplicate`).
   * Local tasks in `status: done` or `status: archived` (or in `TaskNotes/Archive/`) are **never** reopened or overwritten (`completed_locally_preserved`).
   * If an external task changes while the local task has local edits (`user_modified: true`, `in-progress`, `scheduled`, `googleCalendarEventId`, `project_ref`, `linked_zettels`, or modified local text), local fields are preserved and the external diff is recorded in `external_conflict_proposal` (`external_conflict_flag: true`, `review_required: true`) for human review.
