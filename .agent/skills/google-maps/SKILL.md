---
name: google-maps
description: "Optional Google Maps integration skill for Chrysalis location lookup (location.resolve) and contextual commute estimation (routing.estimate): normalizes Google Places (New) and Routes API v2 (computeRoutes) responses into v1.0.0 capability envelopes while enforcing outbound privacy and Google Routes storage/display restrictions."
trigger: "/plan --enrich-routes"
domain: integration
integration_id: google-maps
contract_version: "1.0.0"
capabilities:
  - location.resolve
  - routing.estimate
effects:
  location.resolve: external_query
  routing.estimate: external_query
access: read-only
reads:
  - "System/Memory.md"
  - "System/Integrations.md"
  - "TaskNotes/Tasks/*.md"
  - "contracts/integration-capabilities.contract.md"
writes: []
---

# `google-maps` (Optional Location Lookup & Contextual Commute Integration Skill)

## 1. Scope, Separation of Capabilities & Activation Boundary
This skill provides the **Google Maps Platform** integration adapter (`integration: google-maps`) supplying two distinct capabilities governed by [`contracts/integration-capabilities.contract.md`](../../../contracts/integration-capabilities.contract.md) (`v1.0.0`):
1. **`location.resolve`:** Place and address lookup/disambiguation via Google Places API (New) (`https://places.googleapis.com/v1/places:searchText`).
2. **`routing.estimate`:** Contextual travel duration and distance estimation via Google Routes API v2 (`https://routes.googleapis.com/directions/v2:computeRoutes`).

* **Explicit Activation Only:** Installing `.agent/skills/google-maps/SKILL.md` does **not** automatically activate Google Maps calls. An instance must be configured with `integration: google-maps` and `enabled: true` in `<vault>/System/Memory.md` or `<vault>/System/Integrations.md` and bound to `task.location_lookup` (`location.resolve`) and/or `plan.route_estimate` (`routing.estimate`).
* **Read-Only External Access (`access: read-only`, `effect: external_query`):** This adapter only queries location/routing endpoints; it never mutates external records (`write_back_supported: false`).
* **A2 Local Vault Execution:** All capability resolution, policy filtering, and proposed task/schedule updates execute locally via `helpers/providers/google_maps.py`, `helpers/location_routing.py`, and `helpers/mdbase_helper.py` on `<vault>` over the A2 Access Layer, subject to the mandatory human approval gate.

---

## 2. Access Prerequisites, Authentication & Supported Transports
1. **Credential Reference (`secret_ref`):**
   * Configured via `secret_ref: "env:GOOGLE_MAPS_API_KEY"` (or `file:.chrysalis/secrets/google_maps_key.txt`) in the private integration instance (`integrations.instances.<id>`).
   * Plaintext API keys (`AIza...`) are strictly prohibited in `System/Memory.md`, `System/Integrations.md`, or tracked repository files (`inline_secret_forbidden`).
2. **Supported Transports:**
   * **Google Maps REST v2 (`google_maps_rest_v2`):** Direct HTTPS `POST` requests with mandatory `X-Goog-Api-Key` and minimal `X-Goog-FieldMask` headers (`places.id,places.displayName,places.formattedAddress,places.location,places.types` for `location.resolve`; `routes.duration,routes.staticDuration,routes.distanceMeters,routes.routeLabels` for `routing.estimate`).Never scrapes consumer Google Maps web pages.
   * **Deterministic Fixture / Mock Transport (`mock_fixture`):** Used for offline verification and synthetic conformance tests without billing or live credentials.
3. **Honest Availability & Readiness Reporting:**
   * When `secret_ref` is unconfigured or the environment variable is unset while `live_http_enabled: true`, the adapter reports `status: "auth_failure"` (`missing_prerequisite: "google-maps-api-key"`).
   * When live HTTP is not enabled and no fixture transport is supplied, it reports `status: "unavailable"`. It **never** fabricates coordinates or `0`-minute travel durations.
4. **Locale & Travel Mode Defaults (`config`):**
   * Instance configuration supports `region_code: "US"`, `language_code: "en"`, `units: "metric"`, and `default_travel_mode: "driving"` (canonical modes: `driving`, `transit`, `walking`, `bicycling`; shorthand aliases `drive`, `walk`, `bicycle`, `bike` normalize automatically via `normalize_travel_mode()`, while unsupported modes fail closed with `status: "unsupported_mode"`).

---

## 3. Outbound Privacy & Minimal Request Invariant
* `helpers.providers.google_maps.sanitize_google_maps_outbound_request()` enforces that outbound requests transmit **only** minimal location/routing inputs (`query`, `address`, `place_id`, `coordinates`, `origin`, `destination`, `travel_mode`, `departure_at`, `arrival_by`, `region_code`, `language_code`).
* If a caller passes task titles, Markdown bodies, notes, tags, Zettel links, or project references in the outbound request dictionary, the adapter fails closed with `excessive_payload_fields_forbidden`.

---

## 4. Google Maps Platform Storage, Display & Attribution Policy Enforcement
In compliance with official [Google Routes API Policies](https://developers.google.com/maps/documentation/routes/policies):
1. **`place_id` Persistence Permitted (`persistence_policy: "place_id_only"`):**
   * `location.provider_ref.place_id` (e.g., `"ChIJ_synthetic_place_001"`) is exempt from caching restrictions and may be persisted indefinitely in `TaskNotes/Tasks/*.md` alongside user-supplied `label` and `address`.
2. **No Indefinite Markdown Persistence or Non-Google Map Display of Google-Derived Coordinates/Routes:**
   * Google-derived `coordinates` (`latitude`, `longitude`) and `computeRoutes` route estimates (`duration_minutes`, `distance_meters`, polylines) are tagged with:
     * `provenance: "provider_derived"`
     * `persistence_policy: "ephemeral_only"`
     * `map_display_permitted: false`
     * `attribution: "Powered by Google"`
   * When enriching a task note for persistent disk storage (`helpers.location_routing.enrich_task_location()`), Google-derived `coordinates` and `route_estimate` remain ephemeral in the session/planning proposal and are **stripped** before writing persistent YAML frontmatter to `TaskNotes/Tasks/*.md`.
   * Furthermore, the `obsidian-maps` visualization adapter (`helpers/providers/obsidian_maps.py`) deterministically blocks any record with `provider == "google-maps"` or `map_display_permitted == false` (`google_derived_cross_map_display_forbidden`) from rendering on non-Google map tiles (such as OpenFreeMap / MapLibre).
   * To display a task pin on a non-Google map view in Obsidian, supply user-entered or open-data coordinates (`provenance: "user_supplied"` or `"compatible_open_source"`, `map_display_permitted: true`).
