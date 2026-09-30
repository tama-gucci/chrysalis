"""
Google Maps Optional Integration Helper (helpers/providers/google_maps.py)

Supplies two separate provider-neutral capabilities:
1. `location.resolve`: Location lookup and disambiguation via Google Places API (New) / Geocoding.
2. `routing.estimate`: Contextual travel time and distance estimation via Google Routes API v2 (`computeRoutes`).

Strictly enforces:
- Minimal outbound request payloads (never transmits full task notes, Markdown bodies, tags, or vault state).
- Google Maps Platform / Routes API Storage & Display Policies:
  * `place_id` may be persisted in Markdown task records (`persistence_policy: "place_id_only"`).
  * Google-derived `coordinates` (`lat`/`lng`), `computeRoutes` durations, and polylines are marked
    `persistence_policy: "ephemeral_only"` and `map_display_permitted: False` so they are never saved
    indefinitely in Markdown or rendered on non-Google map tiles (such as Obsidian Maps / OpenFreeMap).
  * Required attribution (`"Powered by Google"`) is attached to every result.
- Read-only external operation (`external_query`, `write_back_supported: False`).
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import urllib.parse
import urllib.request

from helpers.providers.obsidian_maps import parse_coordinates_value

GOOGLE_MAPS_INTEGRATION_ID = "google-maps"
GOOGLE_MAPS_CONTRACT_VERSION = "1.0.0"

GOOGLE_PLACES_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"
GOOGLE_PLACES_FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.types"

GOOGLE_COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
GOOGLE_COMPUTE_ROUTES_FIELD_MASK = "routes.duration,routes.staticDuration,routes.distanceMeters,routes.routeLabels"

GOOGLE_MAPS_REQUIRED_ATTRIBUTION = "Powered by Google"

TRAVEL_MODE_TO_GOOGLE_ENUM: Dict[str, str] = {
    "driving": "DRIVE",
    "transit": "TRANSIT",
    "walking": "WALK",
    "bicycling": "BICYCLE",
}

TRAVEL_MODE_ALIASES: Dict[str, str] = {
    "driving": "driving",
    "drive": "driving",
    "transit": "transit",
    "walking": "walking",
    "walk": "walking",
    "bicycling": "bicycling",
    "bicycle": "bicycling",
    "bike": "bicycling",
}


def normalize_travel_mode(mode: Optional[str]) -> Optional[str]:
    """Normalizes a travel mode or shorthand alias into canonical vocabulary, or None if unsupported."""
    if mode is None:
        return None
    s = str(mode).strip().lower()
    if not s:
        return None
    return TRAVEL_MODE_ALIASES.get(s)


GOOGLE_MAPS_CAPABILITIES: Dict[str, Any] = {
    "integration_id": GOOGLE_MAPS_INTEGRATION_ID,
    "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
    "capabilities": ["location.resolve", "routing.estimate"],
    "effects": {
        "location.resolve": "external_query",
        "routing.estimate": "external_query",
    },
    "supported_travel_modes": list(TRAVEL_MODE_TO_GOOGLE_ENUM.keys()),
    "supports_departure_time": True,
    "supports_arrival_time": True,
    "write_back_supported": False,
    "external_mutation_authorized": False,
    "supported_transports": ["google_maps_rest_v2", "mock_fixture"],
    "storage_and_display_policy": {
        "place_id_persistence": "indefinite",
        "derived_coordinates_persistence": "ephemeral_only",
        "derived_route_persistence": "ephemeral_only",
        "non_google_map_display_permitted": False,
        "required_attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
    },
}

FORBIDDEN_TASK_VAULT_FIELDS: Set[str] = {
    "title",
    "body",
    "markdown_body",
    "notes",
    "tags",
    "linked_zettels",
    "project_ref",
    "deliverable_id",
    "source_ref",
    "evidence_ref",
    "googleCalendarEventId",
    "user_modified",
    "vault_root",
    "timeEstimate",
    "urgency_tier",
    "modality",
}

DEFAULT_ALLOWED_OUTBOUND_KEYS: Set[str] = {
    "query",
    "address",
    "label",
    "place_id",
    "coordinates",
    "origin",
    "destination",
    "travel_mode",
    "departure_at",
    "arrival_by",
    "observed_at",
    "routing_preference",
    "context_fingerprint",
    "previous_task_id",
    "region_code",
    "language_code",
}

DURATION_SECONDS_RE = re.compile(r"^([0-9]+(?:\.[0-9]+)?)s$")


class _SanitizeResult(tuple):
    """Tuple `(sanitized_or_none, err_or_none)` that also supports dict-style `['ok']` / `['status']` access."""

    def __new__(cls, sanitized: Optional[Dict[str, Any]], err: Optional[Dict[str, Any]]) -> "_SanitizeResult":
        return super().__new__(cls, (sanitized, err))

    def _as_dict(self) -> Dict[str, Any]:
        sanitized, err = self[0], self[1]
        if err is not None:
            d = dict(err)
            d.setdefault("ok", False)
            d.setdefault("status", err.get("status") or "privacy_violation")
            d["sanitized"] = None
            d["error"] = err
            return d
        return {
            "ok": True,
            "status": "ok",
            "sanitized": sanitized,
            "payload": sanitized,
            "error": None,
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


def _inspect_outbound_string_for_privacy(val: Any, field_name: str) -> Optional[Dict[str, Any]]:
    """Checks a string field (`query`, `address`, `label`, `place_id`) for markdown, frontmatter, long text, WikiLinks, vault/machine paths, or tags."""
    if not isinstance(val, str):
        return None
    reason: Optional[str] = None
    if len(val) > 256:
        reason = "exceeds_256_char_limit"
    elif "\n" in val or "\r" in val or "---" in val:
        reason = "multiline_or_frontmatter_block"
    else:
        # Check both raw string and URL-unquoted string
        candidates_to_check = [val]
        try:
            unquoted = urllib.parse.unquote(val)
            if unquoted != val:
                candidates_to_check.append(unquoted)
        except Exception:
            pass

        for c_str in candidates_to_check:
            if "\n" in c_str or "\r" in c_str or "---" in c_str:
                reason = "multiline_or_frontmatter_block"
                break
            if "[[" in c_str or "]]" in c_str:
                reason = "obsidian_wikilink_leak"
                break
            lower_c = c_str.lower()
            if "#pillar-" in lower_c:
                reason = "chrysalis_taxonomy_tag_leak"
                break
            norm_c = lower_c.replace("\\", "/")
            for path_token in ("tasknotes/", "slipbox/", "projects/", "system/"):
                if path_token in norm_c:
                    reason = f"vault_relative_path_leak ({path_token})"
                    break
            if reason is not None:
                break
            for host_token in ("c:/users/", "/home/", "/users/"):
                if host_token in norm_c:
                    reason = f"local_machine_path_leak ({host_token})"
                    break
            if reason is not None:
                break

    if reason is not None:
        return {
            "ok": False,
            "status": "privacy_violation",
            "code": "privacy_violation",
            "field": field_name,
            "reason": reason,
            "message": f"Outbound location/routing string field '{field_name}' rejected due to privacy policy ({reason}).",
        }
    return None


def sanitize_google_maps_outbound_request(
    request: Dict[str, Any],
    *,
    allowed_keys: Optional[Set[str]] = None,
) -> _SanitizeResult:
    """
    Validates that an outbound Google Maps request contains ONLY minimal location/routing
    inputs and zero private task note or vault fields or leaked string values.
    """
    eff_allowed = allowed_keys if allowed_keys is not None else DEFAULT_ALLOWED_OUTBOUND_KEYS
    if not isinstance(request, dict):
        return _SanitizeResult(
            None,
            {
                "ok": False,
                "status": "invalid_input",
                "code": "invalid_input",
                "message": "Request payload must be a dictionary.",
            },
        )

    leaked_fields = sorted(k for k in request.keys() if k in FORBIDDEN_TASK_VAULT_FIELDS)
    if leaked_fields:
        return _SanitizeResult(
            None,
            {
                "ok": False,
                "status": "privacy_violation",
                "code": "excessive_payload_fields_forbidden",
                "message": (
                    f"Outbound location/routing request contained prohibited task/vault fields: "
                    f"{', '.join(leaked_fields)}"
                ),
                "leaked_fields": leaked_fields,
            },
        )

    for str_key in ("query", "address", "label", "place_id"):
        if str_key in request and request[str_key] is not None:
            v_err = _inspect_outbound_string_for_privacy(request[str_key], str_key)
            if v_err is not None:
                return _SanitizeResult(None, v_err)

    sanitized: Dict[str, Any] = {}
    for k, v in request.items():
        if k in eff_allowed and v is not None:
            if isinstance(v, dict):
                sub_leaked = sorted(sk for sk in v.keys() if sk in FORBIDDEN_TASK_VAULT_FIELDS)
                if sub_leaked:
                    return _SanitizeResult(
                        None,
                        {
                            "ok": False,
                            "status": "privacy_violation",
                            "code": "excessive_payload_fields_forbidden",
                            "message": (
                                f"Nested endpoint '{k}' contained prohibited task/vault fields: "
                                f"{', '.join(sub_leaked)}"
                            ),
                            "leaked_fields": sub_leaked,
                        },
                    )
                for sub_str_key in ("query", "address", "label", "place_id"):
                    if sub_str_key in v and v[sub_str_key] is not None:
                        sub_v_err = _inspect_outbound_string_for_privacy(v[sub_str_key], f"{k}.{sub_str_key}")
                        if sub_v_err is not None:
                            return _SanitizeResult(None, sub_v_err)
                pref = v.get("provider_ref")
                if isinstance(pref, dict) and pref.get("place_id") is not None:
                    pref_err = _inspect_outbound_string_for_privacy(pref["place_id"], f"{k}.provider_ref.place_id")
                    if pref_err is not None:
                        return _SanitizeResult(None, pref_err)
            sanitized[k] = v
    return _SanitizeResult(sanitized, None)


def _to_utc_rfc3339(local_iso: Optional[str]) -> Optional[str]:
    """Converts a local RFC 3339 timestamp with explicit offset to UTC 'Z' for Google Routes protobuf JSON."""
    if not local_iso:
        return None
    s = str(local_iso).strip()
    if s.endswith("Z"):
        raise ValueError(f"Timestamp must include an explicit local timezone offset (not 'Z'): {local_iso}")
    if "T" not in s:
        raise ValueError(f"Timestamp must be a full ISO 8601 datetime with explicit offset: {local_iso}")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError(f"Timestamp must include an explicit timezone offset: {local_iso}")
    utc_dt = dt.astimezone(timezone.utc)
    return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_google_waypoint(endpoint: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Formats a provider-neutral endpoint dict into a Google Routes v2 Waypoint object."""
    if not isinstance(endpoint, dict):
        return None, "missing_endpoint"

    if endpoint.get("resolution_status") == "ambiguous" or endpoint.get("ambiguous") is True:
        return None, "ambiguous_endpoint"

    coords = endpoint.get("coordinates")
    prov = str(endpoint.get("provenance") or "")
    has_valid_coords = False
    lat_val: float = 0.0
    lng_val: float = 0.0
    if coords is not None:
        parsed_c, c_err = parse_coordinates_value(coords)
        if c_err is not None:
            return None, "invalid_coordinates"
        if parsed_c is not None:
            lat_val, lng_val = parsed_c
            has_valid_coords = True

    if has_valid_coords and prov in {"user_supplied", "manual_override"}:
        return {"location": {"latLng": {"latitude": lat_val, "longitude": lng_val}}}, None

    place_id = endpoint.get("place_id") or (
        endpoint.get("provider_ref", {}).get("place_id")
        if isinstance(endpoint.get("provider_ref"), dict)
        else None
    )
    if place_id and str(place_id).strip():
        return {"placeId": str(place_id).strip()}, None

    if has_valid_coords:
        return {"location": {"latLng": {"latitude": lat_val, "longitude": lng_val}}}, None

    address = endpoint.get("address") or endpoint.get("label") or endpoint.get("query")
    if address and str(address).strip():
        return {"address": str(address).strip()}, None

    return None, "missing_endpoint"


def _normalize_place_candidate(raw_place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalizes a Google Places API (New) or Geocoding item into a contract candidate."""
    if not isinstance(raw_place, dict):
        return None

    place_id = str(
        raw_place.get("id")
        or raw_place.get("place_id")
        or raw_place.get("placeId")
        or ""
    ).strip()

    display_name_obj = raw_place.get("displayName")
    if isinstance(display_name_obj, dict):
        label = str(display_name_obj.get("text") or "").strip()
    else:
        label = str(raw_place.get("label") or raw_place.get("name") or "").strip()

    formatted_address = str(
        raw_place.get("formattedAddress")
        or raw_place.get("formatted_address")
        or raw_place.get("address")
        or label
    ).strip()

    if not label and formatted_address:
        label = formatted_address.split(",")[0].strip()

    loc_obj = raw_place.get("location")
    if not isinstance(loc_obj, dict) and isinstance(raw_place.get("geometry"), dict):
        loc_obj = raw_place["geometry"].get("location")
    if not isinstance(loc_obj, dict):
        loc_obj = raw_place.get("coordinates")

    coords_out: Optional[Dict[str, float]] = None
    if loc_obj is not None:
        parsed_loc, loc_err = parse_coordinates_value(loc_obj)
        if parsed_loc is not None and loc_err is None:
            coords_out = {"latitude": parsed_loc[0], "longitude": parsed_loc[1]}

    if not place_id and not formatted_address and coords_out is None:
        return None

    return {
        "label": label or formatted_address,
        "formatted_address": formatted_address or label,
        "coordinates": coords_out,
        "provider_ref": {
            "provider": GOOGLE_MAPS_INTEGRATION_ID,
            "place_id": place_id or None,
            "location_id": place_id or None,
        },
        "provenance": "provider_derived",
        "persistence_policy": "place_id_only",
        "map_display_permitted": False,
        "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
    }


def resolve_google_maps_location(
    request: Dict[str, Any],
    *,
    instance_config: Optional[Dict[str, Any]] = None,
    transport: Optional[Union[Callable[[Dict[str, Any]], Dict[str, Any]], Dict[str, Any]]] = None,
    resolved_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes `location.resolve` via Google Places API (New) or a deterministic test transport.
    Separates location lookup from route calculation and enforces Google Maps data retention rules.
    """
    allowed_keys = {
        "query",
        "address",
        "place_id",
        "coordinates",
        "region_code",
        "language_code",
    }
    sanitized, err = sanitize_google_maps_outbound_request(request, allowed_keys=allowed_keys)
    if err is not None:
        err_status = "privacy_violation" if err.get("status") == "privacy_violation" else "invalid_input"
        return {
            "ok": False,
            "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
            "capability": "location.resolve",
            "integration": GOOGLE_MAPS_INTEGRATION_ID,
            "effect": "external_query",
            "status": err_status,
            "candidates": [],
            "diagnostics": [err],
            "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
        }

    query_text = str(
        sanitized.get("query") or sanitized.get("address") or sanitized.get("place_id") or ""
    ).strip()
    if not query_text and not sanitized.get("coordinates"):
        return {
            "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
            "capability": "location.resolve",
            "integration": GOOGLE_MAPS_INTEGRATION_ID,
            "effect": "external_query",
            "status": "invalid_input",
            "candidates": [],
            "diagnostics": [{"code": "empty_location_query", "message": "Location query or address is required."}],
            "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
        }

    cfg = instance_config or {}
    nested_cfg = cfg.get("config") if isinstance(cfg.get("config"), dict) else {}
    eff_region = sanitized.get("region_code") or cfg.get("region_code") or nested_cfg.get("region_code")
    eff_lang = sanitized.get("language_code") or cfg.get("language_code") or nested_cfg.get("language_code")

    outbound_payload: Dict[str, Any] = {"textQuery": query_text}
    if eff_region:
        outbound_payload["regionCode"] = str(eff_region)
    if eff_lang:
        outbound_payload["languageCode"] = str(eff_lang)

    raw_response: Optional[Dict[str, Any]] = None

    fixture_p = cfg.get("fixture_path") or nested_cfg.get("fixture_path")
    live_http = bool(cfg.get("live_http_enabled") is True or nested_cfg.get("live_http_enabled") is True)
    if callable(transport):
        try:
            raw_response = transport(
                {
                    "operation": "location.resolve",
                    "endpoint": GOOGLE_PLACES_SEARCH_TEXT_URL,
                    "headers": {"X-Goog-FieldMask": GOOGLE_PLACES_FIELD_MASK},
                    "body": outbound_payload,
                }
            )
        except TimeoutError as exc:
            return _location_error_envelope("timeout", "timeout", str(exc))
        except Exception as exc:
            return _location_error_envelope("unavailable", "transport_error", str(exc))
    elif isinstance(transport, dict):
        raw_response = transport
    elif fixture_p:
        fp = Path(str(fixture_p))
        if fp.is_file():
            raw_response = json.loads(fp.read_text(encoding="utf-8"))
        else:
            return _location_error_envelope("unavailable", "fixture_missing", f"Fixture not found: {fp}")
    elif live_http:
        if not resolved_secret:
            return _location_error_envelope(
                "auth_failure",
                "missing_api_key",
                "Google Maps API key secret_ref is not configured or failed to resolve.",
            )
        req = urllib.request.Request(
            GOOGLE_PLACES_SEARCH_TEXT_URL,
            data=json.dumps(outbound_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": resolved_secret,
                "X-Goog-FieldMask": GOOGLE_PLACES_FIELD_MASK,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(cfg.get("timeout_seconds", 10.0))) as resp:
                raw_response = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as http_err:
            if http_err.code in (401, 403):
                return _location_error_envelope("auth_failure", "http_auth_error", f"HTTP {http_err.code}")
            if http_err.code == 429:
                return _location_error_envelope("quota_exceeded", "http_quota_exceeded", "HTTP 429")
            return _location_error_envelope("unavailable", "http_error", f"HTTP {http_err.code}")
        except TimeoutError as t_err:
            return _location_error_envelope("timeout", "request_timeout", str(t_err))
        except urllib.error.URLError as u_err:
            return _location_error_envelope("offline", "network_unreachable", str(u_err))
    else:
        missing_prereq = "google-maps-api-key" if not resolved_secret else "google-maps-live-or-mock-transport"
        return {
            "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
            "capability": "location.resolve",
            "integration": GOOGLE_MAPS_INTEGRATION_ID,
            "effect": "external_query",
            "status": "unavailable" if resolved_secret else "auth_failure",
            "missing_prerequisite": missing_prereq,
            "candidates": [],
            "diagnostics": [
                {
                    "code": missing_prereq,
                    "message": f"Google Maps location lookup requires {missing_prereq}.",
                }
            ],
            "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
        }

    if not isinstance(raw_response, dict):
        return _location_error_envelope("unavailable", "malformed_provider_response", "Response must be a dict.")

    explicit_status = raw_response.get("error_status") or raw_response.get("status")
    if explicit_status in {"auth_failure", "quota_exceeded", "timeout", "offline", "unavailable"}:
        return _location_error_envelope(
            str(explicit_status),
            str(raw_response.get("error_code") or explicit_status),
            str(raw_response.get("error_message") or f"Provider returned {explicit_status}"),
        )

    raw_places = raw_response.get("places")
    if raw_places is None:
        raw_places = raw_response.get("results") or raw_response.get("candidates") or []
    if not isinstance(raw_places, list):
        return _location_error_envelope("unavailable", "malformed_places_list", "places field must be a list.")

    candidates: List[Dict[str, Any]] = []
    for item in raw_places:
        cand = _normalize_place_candidate(item)
        if cand is not None:
            candidates.append(cand)

    if not candidates:
        status = "not_found"
    elif len(candidates) == 1:
        status = "resolved"
    else:
        status = "ambiguous"

    return {
        "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
        "capability": "location.resolve",
        "integration": GOOGLE_MAPS_INTEGRATION_ID,
        "effect": "external_query",
        "status": status,
        "review_required": status == "ambiguous",
        "candidates": candidates,
        "diagnostics": [],
        "policy": GOOGLE_MAPS_CAPABILITIES["storage_and_display_policy"],
        "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
    }


def _location_error_envelope(status: str, code: str, message: str) -> Dict[str, Any]:
    return {
        "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
        "capability": "location.resolve",
        "integration": GOOGLE_MAPS_INTEGRATION_ID,
        "effect": "external_query",
        "status": status,
        "candidates": [],
        "diagnostics": [{"code": code, "message": message}],
        "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
    }


def estimate_google_maps_route(
    request: Dict[str, Any],
    *,
    instance_config: Optional[Dict[str, Any]] = None,
    transport: Optional[Union[Callable[[Dict[str, Any]], Dict[str, Any]], Dict[str, Any]]] = None,
    resolved_secret: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes `routing.estimate` via Google Routes API v2 (`computeRoutes`) or a deterministic test transport.
    Never returns 0 minutes for unknown or failed routes; enforces Google Routes storage/display policy.
    """
    allowed_keys = {
        "origin",
        "destination",
        "travel_mode",
        "departure_at",
        "arrival_by",
        "observed_at",
        "routing_preference",
        "context_fingerprint",
        "previous_task_id",
    }
    sanitized, err = sanitize_google_maps_outbound_request(request, allowed_keys=allowed_keys)
    if err is not None:
        err_status = "privacy_violation" if err.get("status") == "privacy_violation" else "unavailable"
        return _route_error_envelope(err_status, err["code"], err["message"], request=request)

    origin_raw = sanitized.get("origin")
    dest_raw = sanitized.get("destination")
    if not origin_raw:
        return _route_error_envelope(
            "missing_origin",
            "missing_origin",
            "Explicit origin or preceding task location is required; never silently assuming home.",
            request=sanitized,
        )
    if not dest_raw:
        return _route_error_envelope(
            "missing_destination",
            "missing_destination",
            "Destination location is required for route estimation.",
            request=sanitized,
        )

    origin_wp, orig_err = _format_google_waypoint(origin_raw)
    if orig_err is not None:
        status_code = "ambiguous_endpoint" if orig_err == "ambiguous_endpoint" else "missing_origin"
        return _route_error_envelope(status_code, orig_err, f"Invalid origin: {orig_err}", request=sanitized)

    dest_wp, dest_err = _format_google_waypoint(dest_raw)
    if dest_err is not None:
        status_code = "ambiguous_endpoint" if dest_err == "ambiguous_endpoint" else "missing_destination"
        return _route_error_envelope(status_code, dest_err, f"Invalid destination: {dest_err}", request=sanitized)

    cfg = instance_config or {}
    nested_cfg = cfg.get("config") if isinstance(cfg.get("config"), dict) else {}
    raw_mode = (
        sanitized.get("travel_mode")
        or cfg.get("default_travel_mode")
        or nested_cfg.get("default_travel_mode")
        or "driving"
    )
    travel_mode = normalize_travel_mode(str(raw_mode))
    if travel_mode is None or travel_mode not in TRAVEL_MODE_TO_GOOGLE_ENUM:
        return _route_error_envelope(
            "unsupported_mode",
            "unsupported_travel_mode",
            f"Unsupported travel mode '{raw_mode}'. Allowed: {sorted(TRAVEL_MODE_TO_GOOGLE_ENUM.keys())}",
            request=sanitized,
        )
    sanitized["travel_mode"] = travel_mode

    departure_at = sanitized.get("departure_at")
    arrival_by = sanitized.get("arrival_by")
    try:
        utc_departure = _to_utc_rfc3339(str(departure_at)) if departure_at else None
        utc_arrival = _to_utc_rfc3339(str(arrival_by)) if arrival_by else None
    except ValueError as exc:
        return _route_error_envelope("invalid_request", "invalid_timestamp_offset", str(exc), request=sanitized)

    google_mode = TRAVEL_MODE_TO_GOOGLE_ENUM[travel_mode]
    compute_body: Dict[str, Any] = {
        "origin": origin_wp,
        "destination": dest_wp,
        "travelMode": google_mode,
    }
    if utc_departure:
        compute_body["departureTime"] = utc_departure
    elif utc_arrival and google_mode == "TRANSIT":
        compute_body["arrivalTime"] = utc_arrival

    cfg = instance_config or {}
    nested_cfg = cfg.get("config") if isinstance(cfg.get("config"), dict) else {}
    route_fixture_p = (
        cfg.get("route_fixture_path")
        or nested_cfg.get("route_fixture_path")
        or cfg.get("fixture_path")
        or nested_cfg.get("fixture_path")
    )
    live_http = bool(cfg.get("live_http_enabled") is True or nested_cfg.get("live_http_enabled") is True)
    raw_response: Optional[Dict[str, Any]] = None

    if callable(transport):
        try:
            raw_response = transport(
                {
                    "operation": "routing.estimate",
                    "endpoint": GOOGLE_COMPUTE_ROUTES_URL,
                    "headers": {"X-Goog-FieldMask": GOOGLE_COMPUTE_ROUTES_FIELD_MASK},
                    "body": compute_body,
                }
            )
        except TimeoutError as exc:
            return _route_error_envelope("timeout", "timeout", str(exc), request=sanitized)
        except Exception as exc:
            return _route_error_envelope("unavailable", "transport_error", str(exc), request=sanitized)
    elif isinstance(transport, dict):
        raw_response = transport
    elif route_fixture_p:
        fp = Path(str(route_fixture_p))
        if fp.is_file():
            raw_response = json.loads(fp.read_text(encoding="utf-8"))
        else:
            return _route_error_envelope("unavailable", "fixture_missing", f"Fixture not found: {fp}", request=sanitized)
    elif live_http:
        if not resolved_secret:
            return _route_error_envelope(
                "auth_failure",
                "missing_api_key",
                "Google Maps API key secret_ref is not configured or failed to resolve.",
                request=sanitized,
            )
        req = urllib.request.Request(
            GOOGLE_COMPUTE_ROUTES_URL,
            data=json.dumps(compute_body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": resolved_secret,
                "X-Goog-FieldMask": GOOGLE_COMPUTE_ROUTES_FIELD_MASK,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=float(cfg.get("timeout_seconds", 10.0))) as resp:
                raw_response = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as http_err:
            if http_err.code in (401, 403):
                return _route_error_envelope("auth_failure", "http_auth_error", f"HTTP {http_err.code}", request=sanitized)
            if http_err.code == 429:
                return _route_error_envelope("quota_exceeded", "http_quota_exceeded", "HTTP 429", request=sanitized)
            return _route_error_envelope("unavailable", "http_error", f"HTTP {http_err.code}", request=sanitized)
        except TimeoutError as t_err:
            return _route_error_envelope("timeout", "request_timeout", str(t_err), request=sanitized)
        except urllib.error.URLError as u_err:
            return _route_error_envelope("offline", "network_unreachable", str(u_err), request=sanitized)
    else:
        missing_prereq = "google-maps-api-key" if not resolved_secret else "google-maps-live-or-mock-transport"
        return _route_error_envelope(
            "unavailable" if resolved_secret else "auth_failure",
            missing_prereq,
            f"Google Routes computeRoutes requires {missing_prereq}.",
            request=sanitized,
            missing_prerequisite=missing_prereq,
        )

    if not isinstance(raw_response, dict):
        return _route_error_envelope("unavailable", "malformed_provider_response", "Response must be a dict.", request=sanitized)

    explicit_status = raw_response.get("error_status") or raw_response.get("status")
    if explicit_status in {"no_route", "auth_failure", "quota_exceeded", "timeout", "offline", "unavailable"}:
        return _route_error_envelope(
            str(explicit_status),
            str(raw_response.get("error_code") or explicit_status),
            str(raw_response.get("error_message") or f"Provider returned {explicit_status}"),
            request=sanitized,
        )

    routes = raw_response.get("routes")
    if not isinstance(routes, list) or len(routes) == 0:
        return _route_error_envelope(
            "no_route",
            "empty_routes",
            "No feasible route returned by Google Routes API.",
            request=sanitized,
        )

    top_route = routes[0]
    if not isinstance(top_route, dict):
        return _route_error_envelope("unavailable", "malformed_route_item", "Route entry must be an object.", request=sanitized)

    dur_raw = str(top_route.get("duration") or top_route.get("staticDuration") or "").strip()
    m_dur = DURATION_SECONDS_RE.match(dur_raw)
    if not m_dur:
        return _route_error_envelope(
            "unavailable",
            "missing_or_invalid_duration",
            f"Route response missing valid duration string (got {dur_raw!r}).",
            request=sanitized,
        )

    duration_seconds = int(round(float(m_dur.group(1))))
    if duration_seconds <= 0:
        return _route_error_envelope(
            "unavailable",
            "zero_or_negative_duration",
            "Route duration must be strictly positive (> 0 seconds).",
            request=sanitized,
        )

    duration_minutes = round(duration_seconds / 60.0, 2)
    distance_meters_raw = top_route.get("distanceMeters")
    distance_meters: Optional[float] = float(distance_meters_raw) if distance_meters_raw is not None else None

    observed_at = str(sanitized.get("observed_at") or "2026-09-30T09:00:00-05:00")
    def _extract_non_google_coords(ep: Dict[str, Any]) -> Optional[Dict[str, float]]:
        if ep.get("provenance") == "provider_derived" or ep.get("persistence_policy") in {"place_id_only", "ephemeral_only"}:
            return None
        c = ep.get("coordinates")
        if isinstance(c, dict) and c.get("latitude") is not None and c.get("longitude") is not None:
            return {"latitude": float(c["latitude"]), "longitude": float(c["longitude"])}
        if isinstance(c, (list, tuple)) and len(c) == 2 and c[0] is not None and c[1] is not None:
            return {"latitude": float(c[0]), "longitude": float(c[1])}
        return None

    estimate_obj: Dict[str, Any] = {
        "origin": {
            "label": origin_raw.get("label"),
            "address": origin_raw.get("address"),
            "place_id": origin_raw.get("place_id")
            or (origin_raw.get("provider_ref", {}).get("place_id") if isinstance(origin_raw.get("provider_ref"), dict) else None),
            "source": origin_raw.get("source") or "explicit_input",
            "coordinates": _extract_non_google_coords(origin_raw),
        },
        "destination": {
            "label": dest_raw.get("label"),
            "address": dest_raw.get("address"),
            "place_id": dest_raw.get("place_id")
            or (dest_raw.get("provider_ref", {}).get("place_id") if isinstance(dest_raw.get("provider_ref"), dict) else None),
            "coordinates": _extract_non_google_coords(dest_raw),
        },
        "travel_mode": travel_mode,
        "departure_at": departure_at,
        "arrival_by": arrival_by,
        "duration_minutes": duration_minutes,
        "duration_seconds": duration_seconds,
        "duration_unit": "minutes",
        "distance_meters": distance_meters,
        "distance_unit": "meters" if distance_meters is not None else None,
        "observed_at": observed_at,
        "provider": GOOGLE_MAPS_INTEGRATION_ID,
        "provenance": "provider_derived",
        "freshness": "fresh",
        "status": "ok",
        "persistence_policy": "ephemeral_only",
        "map_display_permitted": False,
        "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
        "context_fingerprint": sanitized.get("context_fingerprint"),
        "previous_task_id": sanitized.get("previous_task_id"),
    }

    return {
        "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
        "capability": "routing.estimate",
        "integration": GOOGLE_MAPS_INTEGRATION_ID,
        "effect": "external_query",
        "status": "ok",
        "estimate": estimate_obj,
        "diagnostics": [],
        "policy": GOOGLE_MAPS_CAPABILITIES["storage_and_display_policy"],
        "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
    }


def _route_error_envelope(
    status: str,
    code: str,
    message: str,
    *,
    request: Optional[Dict[str, Any]] = None,
    missing_prerequisite: Optional[str] = None,
) -> Dict[str, Any]:
    req = request or {}
    travel_mode = str(req.get("travel_mode") or "driving").lower()
    if travel_mode not in TRAVEL_MODE_TO_GOOGLE_ENUM:
        travel_mode_val: Optional[str] = None
    else:
        travel_mode_val = travel_mode

    env: Dict[str, Any] = {
        "contract_version": GOOGLE_MAPS_CONTRACT_VERSION,
        "capability": "routing.estimate",
        "integration": GOOGLE_MAPS_INTEGRATION_ID,
        "effect": "external_query",
        "status": status,
        "estimate": {
            "origin": req.get("origin") if isinstance(req.get("origin"), dict) else None,
            "destination": req.get("destination") if isinstance(req.get("destination"), dict) else None,
            "travel_mode": travel_mode_val,
            "departure_at": req.get("departure_at"),
            "arrival_by": req.get("arrival_by"),
            "duration_minutes": None,
            "duration_seconds": None,
            "duration_unit": None,
            "distance_meters": None,
            "distance_unit": None,
            "observed_at": req.get("observed_at"),
            "provider": GOOGLE_MAPS_INTEGRATION_ID,
            "provenance": "unavailable",
            "freshness": "unavailable",
            "status": status,
            "persistence_policy": "ephemeral_only",
            "map_display_permitted": False,
            "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
            "context_fingerprint": req.get("context_fingerprint"),
        },
        "diagnostics": [{"code": code, "message": message}],
        "attribution": GOOGLE_MAPS_REQUIRED_ATTRIBUTION,
    }
    if missing_prerequisite:
        env["missing_prerequisite"] = missing_prerequisite
    return env
