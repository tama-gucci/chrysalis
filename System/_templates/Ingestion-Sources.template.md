---
type: system_memory_extension
id: ingestion-sources
version: "1.0.0"
ingestion:
  schema_version: "1.0.0"
  preserve_originals_in_place: true
  local_resources_folder_enabled: false
  sources:
    media:
      integration: google-drive
      enabled: false
      access: read-only
      mode: read_only
      item_kinds:
        - file
        - text
      account_scope: "user@example.com"
      collection: "<folder-reference>"
      collection_roots:
        - "Chrysalis-Media-Locker/01-Inbox"
        - "Chrysalis-Media-Locker/02-Projects"
      auto_discover_on_audit: true
      write_back_supported: false
    quick-capture:
      integration: google-tasks
      enabled: false
      access: read-only
      mode: read_only
      item_kinds:
        - structured_task
      account_scope: "user@example.com"
      collection: "<list-reference>"
      collection_roots:
        - "@default"
      auto_discover_on_audit: true
      write_back_supported: false
---

# Private Ingestion Source Bindings (`System/Ingestion-Sources.md`)

Optional standalone configuration file for runtime source aliases (`media`, `quick-capture`, or custom adapters).
When present, `ingestion.sources` in this file merges with or overrides `ingestion.sources` in `System/Memory.md`.
All integrations default to `enabled: false` and `mode: read_only` (`write_back_supported: false`).
