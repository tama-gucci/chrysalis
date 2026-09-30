---
type: system_specification
id: integration-capabilities-contract
version: "1.0.0"
status: active
---

# Chrysalis Shared Integration & Capability Contract (`v1.0.0`)

## 1. Purpose & Architectural Boundaries

Chrysalis separates core cognitive workflows from external applications, transports, and visualization plugins through **versioned capability contracts** and a **static trusted integration registry** (`helpers/integration_registry.py`):

1. **Core Workflow Skills Own Domain Policy (`A2` Authority):**
   * Core skills (`/ingest`, `/task`, `/plan`, `/audit`, `/evening`, `/morning`, `/calibrate`, `/project`, `/zettel`) decide *what* needs doing, request named capabilities (e.g., `ingestion.discover`, `location.resolve`, `routing.estimate`, `visualization.map_projection`), enforce human approval gates, and execute all authoritative Markdown mutations on `<vault>` through the A2 Access Layer (`helpers/mdbase_helper.py`, `mdbase -C "<vault>"`).
   * Core workflow skills **must not** embed provider names, MCP tool identifiers, API endpoints, or provider-specific conditional branches.
2. **Integration Skills Document Provider Setup & Constraints:**
   * Optional integration skills (`.agent/skills/google-drive/SKILL.md`, `.agent/skills/google-tasks/SKILL.md`, `.agent/skills/google-maps/SKILL.md`, `.agent/skills/obsidian-maps/SKILL.md`) document application-specific prerequisites, supported transports, field mappings, and provider data-use policies.
   * Installing an integration skill does **not** activate it; an integration instance must be explicitly configured with `enabled: true` and bound to a workflow capability in private runtime configuration (`<vault>/System/Memory.md`, `<vault>/System/Integrations.md`, or `<vault>/System/Ingestion-Sources.md`).
3. **Deterministic Adapters Normalize Transport Access:**
   * Small Python adapters (`helpers/providers/*.py`) execute bounded transport calls (or consume read-only MCP snapshots, local filesystem mounts, or test fixtures) and normalize responses into versioned capability envelopes.
   * A `SKILL.md` file is documentation, not an active transport connection.
   * Only static, trusted adapters registered in `helpers/integration_registry.py` may be resolved; dynamic code loading or arbitrary module imports from untrusted payloads are strictly forbidden (`arbitrary_adapter_import_forbidden`).
4. **Specialized vs. General Capability Contracts:**
   * [`contracts/ingestion-input.contract.md`](ingestion-input.contract.md) (`v1.0.0`) remains the authoritative specialization for `ingestion.discover` and `ingestion.read` (`file`, `text`, and `structured_task` items producing `Sources/*.md` provenance records).
   * Task location enrichment (`location.resolve`), contextual route estimation (`routing.estimate`), and application projections (`visualization.map_projection`) use `CapabilityRequestEnvelope` and `CapabilityResultEnvelope` (`v1.0.0`). They are **never** forced into ingestion discovery envelopes or `Sources/*.md` records.

---

## 2. Integration Readiness States

Every integration instance and capability binding is evaluated across five distinct readiness states:

| State | Meaning | Verification Criterion |
| :--- | :--- | :--- |
| **`installed`** | Adapter code and `SKILL.md` exist in the framework checkout/vault. | Trusted module entry in `TRUSTED_INTEGRATION_ADAPTERS` and `.agent/skills/<id>/SKILL.md` present. |
| **`configured`** | Private instance configuration exists, `enabled: true`, and bound to a capability. | Resolved in `integrations.instances.<instance_id>` and `integrations.bindings.<binding_key>`. |
| **`authenticated`** | Required secret reference or local path credential resolves without inline secret leakage. | `secret_ref` (`env:<VAR>` or `file:<private_path>`) resolves to a non-empty credential, or local mount/snapshot is configured. |
| **`available`** | Configured transport endpoint, MCP snapshot, or local directory mount is reachable. | Transport probe or fixture/mount check succeeds (`status != "unavailable"`). |
| **`verified`** | Capability execution has completed and passed `v1.0.0` contract schema validation. | `validate_capability_result()` passes with zero schema or policy errors. |

---

## 3. Operation Effect Taxonomy & Authorization Boundary

Each capability operation declares its effect class. A provider's technical ability to mutate external records is strictly separate from Chrysalis authorization to do so:

* **`external_query`**: Read-only request to an external API, MCP server, or mounted filesystem (`ingestion.discover`, `ingestion.read`, `location.resolve`, `routing.estimate`). External state is never mutated (`external_mutation_authorized: false`).
* **`local_projection`**: Deterministic transformation of canonical local Markdown records into an application view format or proposed local enrichment (`visualization.map_projection`). Any proposed mutation to `<vault>/TaskNotes/Tasks/*.md` remains governed by the A2 validation and human approval gate.
* **`external_mutation`**: Write-back or synchronization to an external service. **Prohibited** across all initial capability families (`google-drive`, `google-tasks`, `google-maps`, `obsidian-maps` all enforce `write_back_supported: false` and `external_mutation_authorized: false`). Future write-capable integrations require separate versioned contracts and explicit per-operation human authorization.

---

## 4. Capability Families (`v1.0.0`)

### 4.1 `ingestion.discover` & `ingestion.read`
* **Specialization:** Governed by [`contracts/ingestion-input.contract.md`](ingestion-input.contract.md) (`v1.0.0`).
* **Supplied By:** `google-drive` (`file`, `text`), `google-tasks` (`structured_task`), or mounted filesystem sources.
* **Effect:** `external_query` (`read-only`).

### 4.2 `location.resolve`
Resolves a user-supplied place label, street address, or coordinate query into normalized location candidates.
* **Effect:** `external_query`.
* **Outbound Privacy Rule:** Only minimal location lookup fields (`query`, `address`, `coordinates`, `place_id`, `region_code`, `language_code`) may be transmitted. Full task notes, Markdown bodies, tags, Zettel links, and project references must never be sent (`excessive_payload_fields_forbidden`).
* **Result Statuses:** `resolved` (single unambiguous match), `ambiguous` (multiple plausible candidates requiring human selection), `not_found`, `invalid_input`, `unavailable`, `auth_failure`, `quota_exceeded`, `timeout`, `offline`.
* **Candidate Schema:**
  ```json
  {
    "label": "Engineering Research Building",
    "formatted_address": "100 Campus Dr, Synthetic City, ST 12345",
    "coordinates": {
      "latitude": 30.2849,
      "longitude": -97.7341
    },
    "provider_ref": {
      "provider": "google-maps",
      "place_id": "ChIJ_synthetic_place_001"
    },
    "provenance": "provider_derived",
    "persistence_policy": "place_id_only",
    "map_display_permitted": false,
    "attribution": "Powered by Google"
  }
  ```

### 4.3 `routing.estimate`
Computes a contextual travel duration and distance estimate between an explicit `origin` and `destination` for a specified `travel_mode` (`driving`, `transit`, `walking`, `bicycling`; shorthand aliases `drive`, `walk`, `bicycle`, `bike` normalize to canonical values; instance fallback `default_travel_mode: "driving"`) and `departure_at` or `arrival_by` timestamp (RFC 3339 with explicit local timezone offset).
* **Effect:** `external_query`.
* **Contextual Invariants:**
  * Origin must be an explicitly supplied starting location, task `travel_policy.explicit_origin`, the preceding scheduled task's resolved location, or an explicitly configured starting point in the routing request. The resolver **must never** silently assume `"home"`.
  * Unknown, failed, unsupported, or unroutable estimates **must** set `duration_minutes: null` and an explicit error status (`no_route`, `unsupported_mode`, `missing_origin`, `missing_destination`, `ambiguous_endpoint`, `timeout`, `quota_exceeded`, `auth_failure`, `offline`, `unavailable`, `invalid_request`). Failed estimates **must never** become `0` minutes, and invalid modes are rejected with `status: "unsupported_mode"` even when a manual duration override is present.
  * Task work duration (`timeEstimate`) is strictly separate from `route_estimate.duration_minutes` and `travel_policy.buffer_minutes`.
* **Result Schema:**
  ```json
  {
    "origin": {
      "label": "North Campus Lab",
      "place_id": "ChIJ_synthetic_origin_001",
      "source": "previous_task_location"
    },
    "destination": {
      "label": "Central Library Annex",
      "place_id": "ChIJ_synthetic_dest_002"
    },
    "travel_mode": "driving",
    "departure_at": "2026-10-01T09:25:00-05:00",
    "arrival_by": "2026-10-01T10:00:00-05:00",
    "duration_minutes": 25.0,
    "duration_seconds": 1500,
    "duration_unit": "minutes",
    "distance_meters": 8400,
    "distance_unit": "meters",
    "observed_at": "2026-09-30T21:00:00-05:00",
    "provider": "google-maps",
    "provenance": "provider_derived",
    "freshness": "fresh",
    "status": "ok",
    "persistence_policy": "ephemeral_only",
    "map_display_permitted": false,
    "attribution": "Powered by Google",
    "context_fingerprint": "<64-char-hex-sha256>"
  }
  ```

### 4.4 `visualization.map_projection`
Projects canonical task locations into an external map view format (such as the official `obsidianmd/obsidian-maps` plugin for Obsidian Bases).
* **Effect:** `local_projection` (`read-only`).
* **Policy Enforcement:** Only projects task locations where `map_display_permitted: true` (such as `user_supplied`, `manual_override`, or `compatible_open_source` coordinates). Provider-derived coordinates restricted from third-party tile display (such as `google-maps` coordinates when using OpenFreeMap/MapLibre tiles in Obsidian Maps) are deterministically filtered out (`policy_filtered`).
* **Scope:** Map markers represent task locations only; route polylines, live traffic overlays, and itinerary optimization are not projected unless both the target plugin and provider data terms explicitly permit them.

---

## 5. Future Capability Families (Reserved, Not Implemented)

To ensure future extensibility without redesigning core skills, the registry reserves two additional capability families:
1. **`calendar.commitments_read` / `calendar.events_write`**:
   * Current two-way calendar synchronization for scheduled tasks remains owned exclusively by the Obsidian TaskNotes plugin via `googleCalendarEventId`.
   * Read-only commitment caching (`System/scripts/fetch_ical.py`) bridges compatibly as a local schedule collision input. No duplicate calendar sync engine may be activated alongside TaskNotes.
2. **`notification.dispatch`**:
   * Reserved for future one-way schedule reminders or wearable notifications under an explicit outbound contract.
