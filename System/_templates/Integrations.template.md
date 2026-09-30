---
type: system_memory_extension
id: integrations-registry
version: "1.0.0"
integrations:
  contract_version: "1.0.0"
  instances:
    media:
      integration: google-drive
      enabled: false
      access: read-only
      config:
        collection: "<folder-reference>"
        collection_roots:
          - "Chrysalis-Media-Locker/01-Inbox"
          - "Chrysalis-Media-Locker/02-Projects"
    quick-capture:
      integration: google-tasks
      enabled: false
      access: read-only
      config:
        collection: "<list-reference>"
    maps:
      integration: google-maps
      enabled: false
      access: read-only
      auth_ref: "env:GOOGLE_MAPS_API_KEY"
      config:
        region_code: "US"
        language_code: "en"
        units: "metric"
        default_travel_mode: "driving"
    vault-maps:
      integration: obsidian-maps
      enabled: false
      access: read-only
      config:
        base_view_path: "TaskNotes/Views/maps-default.base"
        coordinate_property: "coordinates"
        plugin_id: "maps"
  bindings:
    ingestion:
      sources:
        media: "media"
        quick-capture: "quick-capture"
    location:
      resolve: "maps"
    routing:
      estimate: "maps"
    visualization:
      map_projection: "vault-maps"
---

# Private Integration Registry & Capability Bindings (`System/Integrations.md`)

Optional standalone configuration file for runtime integration instances and capability bindings (`integrations.instances`, `integrations.bindings`).
When present, `integrations` in this file merges with or overrides `integrations` in `System/Memory.md` and bridges `ingestion.sources` for backward compatibility.
All integrations default to `enabled: false` and `access: read-only`. Secret references must use `env:<VARIABLE_NAME>` or `file:<untracked-path>` and must never contain inline API keys or tokens.
