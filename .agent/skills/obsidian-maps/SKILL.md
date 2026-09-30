---
name: obsidian-maps
description: "Optional Obsidian Maps visualization integration skill (visualization.map_projection) targeting the official obsidianmd/obsidian-maps Bases plugin: projects permitted task location coordinates into Base map views without coupling task records or commute estimation to map plugins."
trigger: "/plan --project-map"
domain: integration
integration_id: obsidian-maps
target_plugin: "obsidianmd/obsidian-maps"
plugin_id: "maps"
contract_version: "1.0.0"
capabilities:
  - visualization.map_projection
effects:
  visualization.map_projection: local_projection
access: read-only
reads:
  - "System/Memory.md"
  - "System/Integrations.md"
  - "TaskNotes/Tasks/*.md"
  - "TaskNotes/Views/maps-default.base"
  - "contracts/integration-capabilities.contract.md"
writes: []
---

# `obsidian-maps` (Optional Obsidian Bases Map View Integration Skill)

## 1. Scope, Target Plugin & Independence Boundary
This skill provides the **Obsidian Maps** visualization adapter (`integration: obsidian-maps`) supplying `visualization.map_projection` under [`contracts/integration-capabilities.contract.md`](../../../contracts/integration-capabilities.contract.md) (`v1.0.0`).
* **Official Target Plugin (`obsidianmd/obsidian-maps`):** Targets the official Obsidian **Maps** community plugin (`obsidian://show-plugin?id=maps`, repository `obsidianmd/obsidian-maps`) which adds the `type: map` view layout to **Obsidian Bases** (`.base` files). Do **not** confuse this with the separate third-party `obsidian-map-view` plugin.
* **Read-Only Local Projection (`access: read-only`, `effect: local_projection`):** `TaskNotes/Tasks/*.md` remains the sole authoritative task store on `<vault>` via the A2 Access Layer. Removing or disabling the `maps` plugin in Obsidian does not break task validation, `/plan`, or `/ingest`.
* **Map Markers vs. Commute Estimation:** Map markers represent task locations (pins with cognitive modality icons and priority colors). Commute estimation (`routing.estimate`) is a completely separate capability; `obsidian-maps` does **not** render route polylines, traffic calculations, or automatic itinerary optimization.

---

## 2. Canonical Location Property Ownership & Refresh Rules
To avoid duplicate editable location values in `TaskNotes/Tasks/*.md`:
1. **Authoritative Source (`location`):**
   * Task location metadata resides in `location` (`label`, `address`, `is_virtual`, `coordinates: {latitude, longitude}`, `provenance`, `resolution_status`, `persistence_policy`, `map_display_permitted`).
2. **Synchronized Projection Property (`coordinates`) & Bases Formula (`formula.mapCoordinates`):**
   * When `location.coordinates` is present and `location.map_display_permitted` is `true` (for `provenance` in `user_supplied`, `manual_override`, or `compatible_open_source`), `helpers.providers.obsidian_maps.synchronize_task_map_coordinates()` synchronizes top-level `coordinates: [latitude, longitude]`.
   * In `TaskNotes/Views/maps-default.base`, the Base view defines `formula.mapCoordinates` (`if(location && location.map_display_permitted == false, null, if(coordinates, coordinates, if(location && location.coordinates, [location.coordinates.latitude, location.coordinates.longitude], null)))`), allowing `obsidianmd/obsidian-maps` to display pins directly from `coordinates` or via `formula.mapCoordinates`.
   * If a user edits top-level `coordinates` (`[lat, lng]` or `"lat, lng"`) directly on a task without an existing `location` object, `synchronize_task_map_coordinates()` promotes it into `location` with `provenance: "user_supplied"` and `map_display_permitted: true`.
   * If `location` is cleared, marked `is_virtual: true`, or updated to a provider-derived source where `map_display_permitted: false`, top-level `coordinates` is automatically cleared to `null` so stale pins never persist.

---

## 3. Provider Data Policy Gate (No Google-Derived Coordinates on Non-Google Tiles)
* Because `obsidianmd/obsidian-maps` uses non-Google map tiles by default (such as [OpenFreeMap](https://openfreemap.org/) `https://tiles.openfreemap.org/styles/liberty`), Google Maps Platform Policies prohibit plotting Google-derived coordinates or routes on this view.
* `helpers.providers.obsidian_maps.project_tasks_to_obsidian_maps()` and `TaskNotes/Views/maps-default.base` enforce `map_display_permitted != false` and exclude any record with `provider == "google-maps"` (`reason: "google_derived_cross_map_display_forbidden"`, `status: "policy_filtered"`).
* Task pins render 100% offline with permitted user-supplied coordinates (`provenance: "user_supplied"`) even when no routing provider is configured or available.
