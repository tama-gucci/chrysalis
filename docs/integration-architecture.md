# Chrysalis Integration Architecture & Capability Model (`v1.0.0`)

Chrysalis decouples core workflows (`/ingest`, `/task`, `/plan`, `/audit`, `/evening`, `/morning`, `/calibrate`, `/project`, `/zettel`) from optional external providers (`google-drive`, `google-tasks`, `google-maps`, `obsidian-maps`) through **versioned capability contracts** ([`contracts/integration-capabilities.contract.md`](../contracts/integration-capabilities.contract.md) and [`contracts/ingestion-input.contract.md`](../contracts/ingestion-input.contract.md)) and a **static trusted registry** (`helpers/integration_registry.py`).

---

## 1. Architectural Separation: Capabilities vs. Providers

1. **Core Workflows Request Capabilities:**
   Core skills and workflows (`System/Workflows/01-capture.md` through `08-continuation.md`) never name external providers, vendor SDKs, or MCP server names. Instead, they request named capabilities:
   - `ingestion.discover` & `ingestion.read` (for `/ingest`)
   - `location.resolve` (for `/task` and `/plan`)
   - `routing.estimate` (for `/plan` contextual commute calculation)
   - `visualization.map_projection` (for task coordinate map projection)
   - *Reserved future capability families:* `calendar.commitments_read`, `calendar.schedule_projection`, `notification.dispatch`.

2. **Static Trusted Integration Registry (`helpers/integration_registry.py`):**
   Only explicitly registered adapters in `TRUSTED_INTEGRATION_ADAPTERS` (`google-drive`, `google-tasks`, `google-maps`, `obsidian-maps`, `filesystem`) can be instantiated. Unregistered or dynamically injected module paths fail closed with `untrusted_integration_id`.

3. **Private Runtime Configuration (`System/Memory.md` or `System/Integrations.md`):**
   Users bind capability requests to configured instances in private runtime state (`integrations.instances` and `integrations.bindings`). Swapping a provider (for example, rebinding `location.resolve` or `routing.estimate` from `maps` to an alternative adapter) requires changing only the binding in `System/Memory.md` or `System/Integrations.md` — **zero edits to core skills or workflows**.

---

## 2. Five-State Readiness Model

Installing a skill folder under `.agent/skills/<provider>/SKILL.md` does **not** activate that integration. `helpers/integration_registry.py` (`evaluate_instance_readiness()`) evaluates five distinct readiness states:

| State | Meaning |
| :--- | :--- |
| **`installed`** | Adapter module and `.agent/skills/<integration_id>/SKILL.md` exist in the framework. |
| **`configured`** | Instance is declared under `integrations.instances.<id>` (or `ingestion.sources.<alias>`) with `enabled: true`. |
| **`authenticated`** | Secret reference (`auth_ref` / `secret_ref` using `env:` or `file:`) resolves without inline secrets (`inline_secret_forbidden`). |
| **`available`** | Local mount path, Base view (`TaskNotes/Views/maps-default.base`), or read-only transport is reachable. |
| **`verified`** | Live or synthetic capability invocation returned a schema-valid contract envelope. |

Check readiness across all configured instances and bindings with:
```bash
python helpers/mdbase_helper.py --runtime integration-status
```

---

## 3. Effect Classes & Approval Gates

Every capability belongs to one of three effect classes:
1. **`external_query`**: Read-only external queries (`ingestion.discover`, `ingestion.read`, `location.resolve`, `routing.estimate`). Must never mutate external state (`write_back_supported: false`).
2. **`local_projection`**: Read-only projection over local vault records (`visualization.map_projection` over `TaskNotes/Views/maps-default.base`).
3. **`external_mutation`**: Reserved for future external writes; requires explicit human approval (`APPROVAL_GATE`) before execution.

---

## 4. Provider Storage & Cross-Map Display Policies (`google-maps` vs. `obsidian-maps`)

Chrysalis enforces provider data-use terms at the schema, adapter, and validation layers:

1. **Google Maps Platform (`google-maps`):**
   - Separates **Places API (New)** (`resolve_google_maps_location`, `places:searchText`) from **Routes API v2** (`estimate_google_maps_route`, `computeRoutes` with mandatory `X-Goog-FieldMask`).
   - **Outbound Privacy:** Only location query strings, Place IDs, or coordinates, travel mode, departure/arrival timestamps, and locale hints are transmitted. Task titles, notes, tags, project names, and vault file paths are rejected by `sanitize_google_maps_outbound_request()`.
   - **Persistence Policy (`place_id_only` / `ephemeral_only`):** `place_id` may be stored indefinitely in `TaskNotes/Tasks/*.md` (`location.provider_ref.place_id`). Google-derived `lat`/`lng` coordinates (`persistence_policy: "place_id_only"`, `map_display_permitted: false`) and `computeRoutes` durations/polylines (`persistence_policy: "ephemeral_only"`) are stripped from persistent Markdown storage and rejected by `validate_record()` if written to disk.

2. **Official Obsidian Maps (`obsidian-maps`, `obsidianmd/obsidian-maps` for Bases):**
   - Uses `TaskNotes/Views/maps-default.base` (`type: map`) and top-level `coordinates: "lat, lng"` (`provenance: "user_supplied"` or `"compatible_open_source"`, `map_display_permitted: true`).
   - Because `obsidianmd/obsidian-maps` renders on non-Google map tiles (such as OpenFreeMap / MapLibre), `project_tasks_to_obsidian_maps()` and `maps-default.base` (`formula.hasPermittedMapPin`) deterministically block any coordinate record with `provider == "google-maps"` or `map_display_permitted == false` (`google_derived_cross_map_display_forbidden`).

---

## 5. External Dependency & Legacy Script Disposition Inventory (Migrated vs. Bridged vs. Deferred)

To prevent parallel integration frameworks while maintaining full backward compatibility, every external integration touchpoint and legacy script in Chrysalis has an explicit architectural disposition:

| External Dependency / Touchpoint | Capability / Role | Disposition | Implementation & Compatibility Details |
| :--- | :--- | :--- | :--- |
| **`google-drive`** (`helpers/providers/google_drive.py`, `.agent/skills/google-drive/SKILL.md`) | `ingestion.discover`, `ingestion.read` (`external_query`) | **Migrated Now** | Registered in `TRUSTED_INTEGRATION_ADAPTERS` (`helpers/integration_registry.py`) and bound via `integrations.bindings.ingestion.sources.<alias>` (with automatic bidirectional bridge to `ingestion.sources.<alias>`). |
| **`google-tasks`** (`helpers/providers/google_tasks.py`, `.agent/skills/google-tasks/SKILL.md`) | `ingestion.discover`, `ingestion.read` (`external_query`) | **Migrated Now** | Registered in `TRUSTED_INTEGRATION_ADAPTERS` (`write_back_supported: false`); local task enrichments (`location`, `coordinates`, `route_estimate`, `travel_policy`) are preserved across repeat captures. |
| **`filesystem` / `local`** (`helpers/ingestion_contract.py`) | `ingestion.discover`, `ingestion.read` (`external_query`) | **Migrated Now** | Registered in `TRUSTED_INTEGRATION_ADAPTERS` (`filesystem` / `local`) for local staging directories and media mounts. |
| **`google-maps`** (`helpers/providers/google_maps.py`, `.agent/skills/google-maps/SKILL.md`) | `location.resolve`, `routing.estimate` (`external_query`) | **Migrated Now** | Registered in `TRUSTED_INTEGRATION_ADAPTERS`; separates Places API (New) from Routes API v2 (`computeRoutes`) with strict outbound privacy and `place_id_only` / `ephemeral_only` storage enforcement. |
| **`obsidian-maps`** (`helpers/providers/obsidian_maps.py`, `.agent/skills/obsidian-maps/SKILL.md`, `TaskNotes/Views/maps-default.base`) | `visualization.map_projection` (`local_projection`) | **Migrated Now** | Registered in `TRUSTED_INTEGRATION_ADAPTERS`; targets official `obsidianmd/obsidian-maps` Bases (`type: map`) over top-level `coordinates` while blocking Google-derived coordinates. |
| **Legacy `ingestion.sources.<alias>` (`System/Memory.md`, `System/Ingestion-Sources.md`)** | `ingestion.discover`, `ingestion.read` | **Bridged Compatibly** | Automatically bridged into `integrations.instances` and `integrations.bindings` by `resolve_integration_config()` and back into `resolve_ingestion_config()` so existing `/ingest` configs work unchanged. |
| **`System/scripts/fetch_ical.py` (Read-Only iCal Feed Fetcher)** | `calendar.commitments_read` (Legacy Script & Overlap Disposition) | **Bridged Compatibly / Deferred** | Preserved as an optional read-only commitment helper for external iCal feed blocks; reserved under future capability `calendar.commitments_read` without duplicating TaskNotes two-way calendar sync. |
| **Obsidian TaskNotes & Google Calendar Sync (`googleCalendarEventId`, `tn_role`)** | UI & Calendar Event Sync | **Deferred (UI Layer)** | Managed directly by the Obsidian community TaskNotes plugin at the UI/Calendar boundary (`ARCHITECTURE.md` Section 1). Core agent skills read/preserve `googleCalendarEventId` and `scheduled` ISO timestamps without calling Google Calendar APIs directly. |
| **GitHub Upstream Release Sync (`System/scripts/update.py`, `/update`)** | Framework Maintenance | **Deferred (Dev/Ops CLI)** | Framework-level git/release synchronization utility (`tama-gucci/chrysalis`); operates outside runtime life-operations capabilities. |

---

## 6. Adding a New Routing or Visualization Provider Without Editing Core Workflow Skills

Because core workflows (`/task`, `/plan`, `/calibrate`, `/evening`, `/morning`, `/ingest`, `/doctor`) depend **only** on capability names (`location.resolve`, `routing.estimate`, `visualization.map_projection`) and provider-neutral task fields (`location`, `coordinates`, `route_estimate`, `travel_policy`), adding a new provider (for example, `openrouteservice`, `osrm`, `valhalla`, or `apple-maps`) requires **zero modifications** to core workflow runbooks or task schemas:

1. **Author the Provider Helper (`helpers/providers/<provider_id>.py`):**
   - Implement pure handler functions matching the v1.0.0 capability signatures in [`contracts/integration-capabilities.contract.md`](../contracts/integration-capabilities.contract.md) (e.g., `resolve_<provider>_location(request, *, instance_config, transport, resolved_secret)` and/or `estimate_<provider>_route(...)`).
   - Set appropriate `persistence_policy` (`"persistent_permitted"` if open-data licensing permits storing coordinates/estimates in Markdown and displaying them on `obsidianmd/obsidian-maps`, or `"place_id_only"` / `"ephemeral_only"` if restricted) and `map_display_permitted` (`True` or `False`).
2. **Register in the Static Trusted Registry (`helpers/integration_registry.py`):**
   - Add an entry to `TRUSTED_INTEGRATION_ADAPTERS` mapping `<provider_id>` to its supported `capabilities`, `effects`, `skill_path` (`.agent/skills/<provider_id>/SKILL.md`), and `handlers`.
   - Register the optional skill in `.agent/skills.json`.
3. **Bind in Private Runtime Config (`<vault>/System/Integrations.md` or `<vault>/System/Memory.md`):**
   - Define an instance under `integrations.instances.<instance_id>` with `integration: "<provider_id>"`, `enabled: true`, and `auth_ref: "env:<ENV_VAR_NAME>"`.
   - Point `integrations.bindings.task.location_lookup` (`location.resolve`), `plan.route_estimate` (`routing.estimate`), or `views.map_projection` (`visualization.map_projection`) to `<instance_id>`.
   - Core workflows (`python helpers/mdbase_helper.py --runtime location-resolve`, `route-estimate`, `map-project`) immediately route through the new provider instance.
