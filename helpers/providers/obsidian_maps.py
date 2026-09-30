"""
Obsidian Maps Optional Visualization Integration Helper (helpers/providers/obsidian_maps.py)

Supplies the `visualization.map_projection` capability targeting the official
`obsidianmd/obsidian-maps` community plugin (`obsidian://show-plugin?id=maps`) for
Obsidian Bases (`type: map`), while keeping the projection contract provider-neutral.

Key Architectural Invariants:
1. Target Plugin Distinction: Targets `obsidianmd/obsidian-maps` (Bases `type: map` layout),
   NOT the separate third-party `obsidian-map-view` plugin.
2. Canonical Ownership & Refresh: `location` in `TaskNotes/Tasks/*.md` is authoritative.
   Top-level `coordinates: [lat, lng]` is a synchronized projection property populated ONLY
   when `location.map_display_permitted is True` (e.g. `user_supplied`, `manual_override`,
   or `compatible_open_source` provenance).
3. Strict Provider Policy Enforcement: Because `obsidianmd/obsidian-maps` renders markers on
   non-Google map tiles (such as OpenFreeMap / MapLibre / OpenStreetMap), any location or
   coordinate with `provider == "google-maps"` (`provenance == "provider_derived"` or
   `map_display_permitted == False`) is strictly blocked from projection (`policy_filtered`).
4. Pin-Only Scope: Map markers represent task locations only. Commute estimation (`routing.estimate`)
   is a separate capability; this module never claims or projects route polylines, traffic overlays,
   or automatic itinerary optimization.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union


OBSIDIAN_MAPS_INTEGRATION_ID = "obsidian-maps"
OBSIDIAN_MAPS_CONTRACT_VERSION = "1.0.0"
OBSIDIAN_MAPS_PLUGIN_ID = "maps"
OBSIDIAN_MAPS_PLUGIN_REPO = "obsidianmd/obsidian-maps"
OBSIDIAN_MAPS_DEFAULT_BASE_VIEW = "TaskNotes/Views/maps-default.base"
DEFAULT_BASE_VIEW_REL_PATH = OBSIDIAN_MAPS_DEFAULT_BASE_VIEW

MODALITY_TO_LUCIDE_ICON: Dict[str, str] = {
    "analytical": "cpu",
    "kinetic": "wrench",
    "synthesis": "book-open",
    "administrative": "clipboard-list",
}

PRIORITY_TO_CSS_COLOR: Dict[str, str] = {
    "urgent": "var(--color-red)",
    "high": "var(--color-orange)",
    "normal": "var(--color-blue)",
    "low": "var(--color-gray)",
    "none": "var(--color-gray)",
}

OBSIDIAN_MAPS_CAPABILITIES: Dict[str, Any] = {
    "integration_id": OBSIDIAN_MAPS_INTEGRATION_ID,
    "contract_version": OBSIDIAN_MAPS_CONTRACT_VERSION,
    "target_plugin": OBSIDIAN_MAPS_PLUGIN_REPO,
    "plugin_id": OBSIDIAN_MAPS_PLUGIN_ID,
    "capabilities": ["visualization.map_projection"],
    "effects": {
        "visualization.map_projection": "local_projection",
    },
    "write_back_supported": False,
    "external_mutation_authorized": False,
    "supported_transports": ["obsidian_bases_map_view"],
    "supports_route_overlays": False,
    "supports_traffic_calculations": False,
    "supports_itinerary_optimization": False,
    "accepts_google_derived_coordinates": False,
    "accepts_user_supplied_coordinates": True,
}


def parse_coordinates_value(raw: Any) -> Tuple[Optional[Tuple[float, float]], Optional[str]]:
    """
    Parses a coordinate value in any format accepted by Chrysalis or `obsidianmd/obsidian-maps`:
    - `{"latitude": 30.2849, "longitude": -97.7341}`
    - `[30.2849, -97.7341]` or `["30.2849", "-97.7341"]`
    - `"30.2849, -97.7341"`
    Returns `((lat, lng), None)` or `(None, error_reason)`.
    """
    if raw is None:
        return None, "missing_coordinates"

    lat_val: Any = None
    lng_val: Any = None

    if isinstance(raw, dict):
        lat_val = raw.get("latitude", raw.get("lat"))
        lng_val = raw.get("longitude", raw.get("lng"))
    elif isinstance(raw, (list, tuple)):
        if len(raw) != 2:
            return None, "invalid_coordinates_length"
        lat_val, lng_val = raw[0], raw[1]
    elif isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) != 2:
            return None, "invalid_coordinates_string"
        lat_val, lng_val = parts[0], parts[1]
    else:
        return None, "invalid_coordinates_type"

    if isinstance(lat_val, bool) or isinstance(lng_val, bool):
        return None, "invalid_coordinates_boolean"

    try:
        lat = float(lat_val)
        lng = float(lng_val)
    except (TypeError, ValueError):
        return None, "invalid_coordinates_numeric"

    if math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
        return None, "invalid_coordinates_nan"

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return None, "coordinates_out_of_bounds"

    return (round(lat, 6), round(lng, 6)), None


def synchronize_task_map_coordinates(task_fm: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enforces single-source ownership between `location` and the top-level `coordinates`
    projection field used by `obsidianmd/obsidian-maps`:
    - If `location` is present:
      * If `location.is_virtual` is True or `location.map_display_permitted` is False or
        `location.provenance == "provider_derived"` with `provider == "google-maps"`,
        clears top-level `coordinates = None` and (if `persistence_policy != "persistent_permitted"`)
        clears `location["coordinates"] = None`.
      * If `location.coordinates` is present and `map_display_permitted` is True, sets
        top-level `coordinates = [lat, lng]`.
    - If `location` is None and top-level `coordinates` is supplied by the user:
      * Initializes `location` with `provenance: "user_supplied"`, `resolution_status: "resolved"`,
        `persistence_policy: "persistent_permitted"`, `map_display_permitted: True`, and normalized
        `location.coordinates`.
    """
    updated = dict(task_fm)
    loc = updated.get("location")
    top_coords = updated.get("coordinates")

    if isinstance(loc, dict):
        loc_copy = dict(loc)
        prov = str(loc_copy.get("provenance") or "user_supplied")
        provider_id = (
            loc_copy.get("provider_ref", {}).get("provider")
            if isinstance(loc_copy.get("provider_ref"), dict)
            else None
        )
        is_user_or_open = prov in {"user_supplied", "manual_override", "compatible_open_source"}
        is_google_derived = (prov == "provider_derived" and provider_id == "google-maps")

        if loc_copy.get("is_virtual") is True:
            loc_copy["coordinates"] = None
            loc_copy["map_display_permitted"] = False
            updated["coordinates"] = None
            updated["location"] = loc_copy
            return updated

        raw_coords = loc_copy.get("coordinates") if loc_copy.get("coordinates") is not None else top_coords
        parsed, err = parse_coordinates_value(raw_coords)

        if is_user_or_open and parsed is not None and err is None:
            lat, lng = parsed
            was_restricted = loc_copy.get("persistence_policy") in {"place_id_only", "ephemeral_only"}
            if was_restricted:
                loc_copy["persistence_policy"] = "persistent_permitted"
                loc_copy["map_display_permitted"] = True
            if provider_id == "google-maps" and prov in {"user_supplied", "manual_override"}:
                loc_copy["provider_ref"] = None
            if loc_copy.get("map_display_permitted") is False and not was_restricted:
                loc_copy["coordinates"] = {"latitude": lat, "longitude": lng}
                updated["coordinates"] = None
                updated["location"] = loc_copy
                return updated
            loc_copy["coordinates"] = {"latitude": lat, "longitude": lng}
            loc_copy["persistence_policy"] = str(loc_copy.get("persistence_policy") or "persistent_permitted")
            loc_copy["map_display_permitted"] = True
            loc_copy["resolution_status"] = "resolved"
            updated["location"] = loc_copy
            updated["coordinates"] = [lat, lng]
            return updated

        if is_google_derived or loc_copy.get("persistence_policy") in {"place_id_only", "ephemeral_only"}:
            loc_copy["map_display_permitted"] = False
            loc_copy["coordinates"] = None
            updated["coordinates"] = None
            updated["location"] = loc_copy
            return updated

        map_permitted = bool(loc_copy.get("map_display_permitted", not is_google_derived))
        if not map_permitted:
            updated["coordinates"] = None
            updated["location"] = loc_copy
            return updated

        if parsed is not None and err is None:
            lat, lng = parsed
            loc_copy["coordinates"] = {"latitude": lat, "longitude": lng}
            loc_copy["map_display_permitted"] = True
            updated["location"] = loc_copy
            updated["coordinates"] = [lat, lng]
        else:
            updated["coordinates"] = None
            updated["location"] = loc_copy
        return updated

    if top_coords is not None:
        parsed, err = parse_coordinates_value(top_coords)
        if parsed is not None and err is None:
            lat, lng = parsed
            updated["coordinates"] = [lat, lng]
            updated["location"] = {
                "label": str(updated.get("title") or "Task Location"),
                "address": None,
                "is_virtual": False,
                "coordinates": {"latitude": lat, "longitude": lng},
                "provider_ref": None,
                "provenance": "user_supplied",
                "resolution_status": "resolved",
                "persistence_policy": "persistent_permitted",
                "map_display_permitted": True,
                "attribution": None,
                "candidates": None,
                "user_modified": True,
            }
    return updated


def project_tasks_to_obsidian_maps(
    request: Dict[str, Any],
    *,
    instance_config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Executes `visualization.map_projection` over canonical Chrysalis task records.
    Emits markers compatible with `obsidianmd/obsidian-maps` while filtering out
    virtual tasks, invalid coordinates, and provider-derived coordinates prohibited
    from non-Google map display.
    """
    records = request.get("records") if isinstance(request, dict) else []
    if not isinstance(records, list):
        records = []

    markers: List[Dict[str, Any]] = []
    filtered_records: List[Dict[str, Any]] = []

    for rec in records:
        if not isinstance(rec, dict):
            continue
        fm = rec.get("frontmatter") if isinstance(rec.get("frontmatter"), dict) else rec
        title = str(fm.get("title") or rec.get("path") or "Untitled Task")
        rec_path = str(rec.get("path") or fm.get("id") or title)

        loc = fm.get("location")
        top_coords = fm.get("coordinates")

        if isinstance(loc, dict):
            if loc.get("is_virtual") is True or loc.get("resolution_status") == "virtual":
                filtered_records.append(
                    {"path": rec_path, "title": title, "reason": "virtual_task"}
                )
                continue

            prov = str(loc.get("provenance") or "")
            provider_id = (
                loc.get("provider_ref", {}).get("provider")
                if isinstance(loc.get("provider_ref"), dict)
                else None
            )
            if (
                prov == "provider_derived"
                and provider_id == "google-maps"
            ) or loc.get("map_display_permitted") is False:
                filtered_records.append(
                    {
                        "path": rec_path,
                        "title": title,
                        "reason": "google_derived_cross_map_display_forbidden",
                        "provider": provider_id or "google-maps",
                    }
                )
                continue

            if loc.get("resolution_status") == "ambiguous":
                filtered_records.append(
                    {"path": rec_path, "title": title, "reason": "ambiguous_location_unresolved"}
                )
                continue

            raw_coord_source = loc.get("coordinates") if loc.get("coordinates") is not None else top_coords
            if raw_coord_source is None:
                filtered_records.append(
                    {"path": rec_path, "title": title, "reason": "missing_coordinates"}
                )
                continue

            parsed, err = parse_coordinates_value(raw_coord_source)
            if parsed is None or err is not None:
                filtered_records.append(
                    {"path": rec_path, "title": title, "reason": err or "invalid_coordinates"}
                )
                continue

            lat, lng = parsed
            modality = str(fm.get("modality") or "analytical")
            priority = str(fm.get("priority") or "normal")
            markers.append(
                {
                    "path": rec_path,
                    "title": title,
                    "label": str(loc.get("label") or title),
                    "address": loc.get("address"),
                    "coordinates": [f"{lat:.6f}", f"{lng:.6f}"],
                    "numeric_coordinates": [lat, lng],
                    "icon": MODALITY_TO_LUCIDE_ICON.get(modality, "map-pin"),
                    "color": PRIORITY_TO_CSS_COLOR.get(priority, "var(--color-blue)"),
                    "provenance": prov or "user_supplied",
                    "status": str(fm.get("status") or "todo"),
                    "modality": modality,
                    "priority": priority,
                }
            )
        elif top_coords is not None:
            parsed, err = parse_coordinates_value(top_coords)
            if parsed is None or err is not None:
                filtered_records.append(
                    {"path": rec_path, "title": title, "reason": err or "invalid_coordinates"}
                )
                continue
            lat, lng = parsed
            modality = str(fm.get("modality") or "analytical")
            priority = str(fm.get("priority") or "normal")
            markers.append(
                {
                    "path": rec_path,
                    "title": title,
                    "label": title,
                    "address": None,
                    "coordinates": [f"{lat:.6f}", f"{lng:.6f}"],
                    "numeric_coordinates": [lat, lng],
                    "icon": MODALITY_TO_LUCIDE_ICON.get(modality, "map-pin"),
                    "color": PRIORITY_TO_CSS_COLOR.get(priority, "var(--color-blue)"),
                    "provenance": "user_supplied",
                    "status": str(fm.get("status") or "todo"),
                    "modality": modality,
                    "priority": priority,
                }
            )
        else:
            filtered_records.append(
                {"path": rec_path, "title": title, "reason": "no_location"}
            )

    policy_filtered_count = sum(
        1 for item in filtered_records if item.get("reason") == "google_derived_cross_map_display_forbidden"
    )
    if markers:
        status = "ok"
    elif policy_filtered_count > 0:
        status = "policy_filtered"
    else:
        status = "empty"

    icfg = instance_config or {}
    nested_icfg = icfg.get("config") if isinstance(icfg.get("config"), dict) else {}
    eff_base_view = (
        request.get("base_view_path")
        or icfg.get("base_view_path")
        or nested_icfg.get("base_view_path")
        or DEFAULT_BASE_VIEW_REL_PATH
    )
    return {
        "contract_version": OBSIDIAN_MAPS_CONTRACT_VERSION,
        "capability": "visualization.map_projection",
        "integration": OBSIDIAN_MAPS_INTEGRATION_ID,
        "target_plugin": OBSIDIAN_MAPS_PLUGIN_REPO,
        "plugin_id": OBSIDIAN_MAPS_PLUGIN_ID,
        "effect": "local_projection",
        "status": status,
        "markers": markers,
        "filtered_records": filtered_records,
        "base_view_path": str(eff_base_view),
        "diagnostics": [],
    }


class _BaseViewValidationResult(tuple):
    """Tuple `(valid_bool, diagnostics_list)` that also supports dict-style `.get('valid')` / `['valid']` access."""

    def __new__(cls, valid: bool, diagnostics: List[Dict[str, Any]]) -> "_BaseViewValidationResult":
        return super().__new__(cls, (valid, diagnostics))

    def _as_dict(self) -> Dict[str, Any]:
        return {
            "valid": bool(self[0]),
            "ok": bool(self[0]),
            "diagnostics": list(self[1]),
        }

    def get(self, key: str, default: Any = None) -> Any:
        return self._as_dict().get(key, default)

    def __getitem__(self, item: Any) -> Any:
        if isinstance(item, (int, slice)):
            return super().__getitem__(item)
        return self._as_dict()[item]

    def __contains__(self, item: Any) -> bool:
        if isinstance(item, str):
            return item in self._as_dict()
        return super().__contains__(item)


def validate_obsidian_maps_base_view(base_view_path_or_text: Any) -> _BaseViewValidationResult:
    """
    Validates an Obsidian Bases map view file (`TaskNotes/Views/maps-default.base`) targeting
    `obsidianmd/obsidian-maps` (`type: map`, `coordinates` binding, and Google cross-map policy filter).
    """
    from pathlib import Path

    diagnostics: List[Dict[str, Any]] = []
    raw_text = ""
    if isinstance(base_view_path_or_text, Path):
        if not base_view_path_or_text.is_file():
            return _BaseViewValidationResult(
                False,
                [{"code": "missing_base_view_file", "message": f"Base view file not found: {base_view_path_or_text}"}],
            )
        raw_text = base_view_path_or_text.read_text(encoding="utf-8")
    elif isinstance(base_view_path_or_text, str):
        p_cand = Path(base_view_path_or_text)
        if "\n" not in base_view_path_or_text and len(base_view_path_or_text) < 260 and p_cand.is_file():
            raw_text = p_cand.read_text(encoding="utf-8")
        else:
            raw_text = base_view_path_or_text
    else:
        return _BaseViewValidationResult(
            False,
            [{"code": "invalid_base_view_input", "message": "Base view input must be a Path or YAML string."}],
        )

    if "type: map" not in raw_text and "type: 'map'" not in raw_text and 'type: "map"' not in raw_text:
        diagnostics.append(
            {
                "code": "missing_map_view_type",
                "message": "Obsidian Maps .base view must declare a view with 'type: map'.",
            }
        )
    if "coordinates:" not in raw_text:
        diagnostics.append(
            {
                "code": "missing_coordinates_property",
                "message": "Obsidian Maps .base view must specify 'coordinates:' binding for map pins.",
            }
        )
    if "map_display_permitted" not in raw_text:
        diagnostics.append(
            {
                "code": "missing_cross_map_policy_guard",
                "message": "Obsidian Maps .base view must filter out records with map_display_permitted == false.",
            }
        )

    return _BaseViewValidationResult(len(diagnostics) == 0, diagnostics)
