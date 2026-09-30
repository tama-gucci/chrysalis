"""
Chrysalis Provider-Neutral Location, Route Estimation & Travel Scheduling Helper
(helpers/location_routing.py)

Implements:
1. Schema and policy validation (`validate_task_location_and_travel_fields`) for task
   `location`, `coordinates`, `route_estimate`, and `travel_policy`.
2. Contextual route fingerprinting (`compute_route_context_fingerprint`) and staleness
   invalidation (`evaluate_route_freshness`) when origin, destination, travel mode,
   departure/arrival context, or schedule predecessor order change.
3. Task location enrichment (`enrich_task_location`) preserving manual overrides,
   work `timeEstimate`, date-only deadlines, and Google Maps persistence/display rules.
4. Contextual commute estimation (`estimate_task_commute`) requiring an explicit origin
   or preceding task location (never silently assuming home) and never turning unknown
   or failed estimates into 0 minutes.
5. Travel-aware schedule window arithmetic and collision detection
   (`propose_travel_schedule_window`) keeping `timeEstimate` separate from travel duration,
   handling explicit local timezone offsets and daylight-saving transitions, and requiring
   human approval before mutating `scheduled`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore

from helpers.integration_registry import invoke_capability, resolve_capability_binding
from helpers.providers.google_maps import TRAVEL_MODE_ALIASES, normalize_travel_mode
from helpers.providers.obsidian_maps import (
    parse_coordinates_value,
    synchronize_task_map_coordinates,
)


ALLOWED_TRAVEL_MODES = {"driving", "transit", "walking", "bicycling"}

EXPLICIT_OFFSET_ISO_RE = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?([+\-][0-9]{2}:[0-9]{2})$"
)


def _parse_cli_endpoint(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Parses a CLI endpoint string (`--origin` / `--destination`) into a canonical endpoint dict:
    - `place_id:<id>` or `ChIJ...` -> `{"label": raw, "place_id": place_id, "provider_ref": {"provider": "google-maps", "place_id": place_id}, "resolution_status": "resolved"}`
    - `"lat,lng"` coordinate pair -> `{"label": raw, "coordinates": [lat, lng], "provenance": "user_supplied", "resolution_status": "resolved"}`
    - Plain address string -> `{"label": raw, "address": raw, "resolution_status": "resolved"}`
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s.lower().startswith("place_id:"):
        pid = s.split(":", 1)[1].strip()
        if not pid:
            return None
        return {
            "label": s,
            "place_id": pid,
            "provider_ref": {"provider": "google-maps", "place_id": pid},
            "resolution_status": "resolved",
        }
    if s.startswith("ChIJ") and " " not in s and "," not in s:
        return {
            "label": s,
            "place_id": s,
            "provider_ref": {"provider": "google-maps", "place_id": s},
            "resolution_status": "resolved",
        }
    parsed_coords, coord_err = parse_coordinates_value(s)
    if parsed_coords is not None and coord_err is None:
        return {
            "label": s,
            "coordinates": [parsed_coords[0], parsed_coords[1]],
            "provenance": "user_supplied",
            "resolution_status": "resolved",
        }
    return {
        "label": s,
        "address": s,
        "resolution_status": "resolved",
    }


def _has_explicit_local_offset(ts: Optional[str]) -> bool:
    if not ts or not isinstance(ts, str):
        return False
    s = ts.strip()
    if s.endswith("Z"):
        return False
    return bool(EXPLICIT_OFFSET_ISO_RE.match(s))


def _endpoint_identity_key(endpoint: Optional[Dict[str, Any]]) -> str:
    """Produces a deterministic string identity for an origin or destination endpoint."""
    if not isinstance(endpoint, dict):
        return "none"
    coords = endpoint.get("coordinates")
    prov = str(endpoint.get("provenance") or "")
    parsed, err = parse_coordinates_value(coords)
    if parsed is not None and err is None and prov in {"user_supplied", "manual_override"}:
        return f"coords:{parsed[0]:.6f},{parsed[1]:.6f}"

    place_id = endpoint.get("place_id") or (
        endpoint.get("provider_ref", {}).get("place_id")
        if isinstance(endpoint.get("provider_ref"), dict)
        else None
    )
    if place_id and str(place_id).strip():
        return f"place_id:{str(place_id).strip()}"

    if parsed is not None and err is None:
        return f"coords:{parsed[0]:.6f},{parsed[1]:.6f}"

    addr = str(endpoint.get("address") or endpoint.get("label") or "").strip().lower()
    if addr:
        return f"addr:{addr}"
    return "none"


def compute_route_context_fingerprint(
    *,
    origin: Optional[Dict[str, Any]],
    destination: Optional[Dict[str, Any]],
    travel_mode: Optional[str],
    departure_at: Optional[str] = None,
    arrival_by: Optional[str] = None,
    previous_task_id: Optional[str] = None,
) -> str:
    """
    Computes a canonical 64-char hex SHA-256 over the contextual parameters of a commute estimate.
    Any change to origin, destination, travel mode, departure/arrival context, or schedule predecessor
    produces a different fingerprint and invalidates stale estimates.
    """
    norm_m = normalize_travel_mode(travel_mode) or str(travel_mode or "driving").strip().lower()
    payload = {
        "origin": _endpoint_identity_key(origin),
        "destination": _endpoint_identity_key(destination),
        "travel_mode": norm_m,
        "departure_at": str(departure_at or ""),
        "arrival_by": str(arrival_by or ""),
        "previous_task_id": str(previous_task_id or ""),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().lower()


def evaluate_route_freshness(
    task_fm: Dict[str, Any],
    *,
    origin: Optional[Dict[str, Any]] = None,
    destination: Optional[Dict[str, Any]] = None,
    travel_mode: Optional[str] = None,
    departure_at: Optional[str] = None,
    arrival_by: Optional[str] = None,
    previous_task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates whether a task's route_estimate is fresh or stale given the current schedule context.
    Invalidates the estimate if endpoints, departure/arrival time, mode, or schedule predecessor changed.
    """
    est = task_fm.get("route_estimate")
    if not isinstance(est, dict):
        return {
            "freshness": "unavailable",
            "is_stale": True,
            "reason": "missing_route_estimate",
            "updated_route_estimate": None,
        }

    eff_origin = origin if origin is not None else est.get("origin")
    eff_dest = destination if destination is not None else (task_fm.get("location") or est.get("destination"))
    eff_mode = travel_mode if travel_mode is not None else est.get("travel_mode")
    eff_dep = departure_at if departure_at is not None else est.get("departure_at")
    eff_arr = arrival_by if arrival_by is not None else (
        (task_fm.get("travel_policy") or {}).get("arrival_at")
        if isinstance(task_fm.get("travel_policy"), dict) and est.get("arrival_by") is None
        else est.get("arrival_by")
    )
    eff_prev_task_id = previous_task_id if previous_task_id is not None else est.get("previous_task_id")

    expected_fp = compute_route_context_fingerprint(
        origin=eff_origin,
        destination=eff_dest,
        travel_mode=eff_mode,
        departure_at=eff_dep,
        arrival_by=eff_arr,
        previous_task_id=eff_prev_task_id,
    )
    stored_fp = est.get("context_fingerprint")

    if stored_fp and stored_fp != expected_fp:
        stale_est = dict(est)
        stale_est["freshness"] = "stale"
        stale_est["status"] = "stale"
        return {
            "freshness": "stale",
            "is_stale": True,
            "reason": "context_changed",
            "expected_fingerprint": expected_fp,
            "stored_fingerprint": stored_fp,
            "updated_route_estimate": stale_est,
        }

    # Even if fingerprint wasn't stored, check direct endpoint/mode/schedule-context mismatches
    if (
        _endpoint_identity_key(eff_origin) != _endpoint_identity_key(est.get("origin"))
        or _endpoint_identity_key(eff_dest) != _endpoint_identity_key(est.get("destination"))
        or str(eff_mode or "").lower() != str(est.get("travel_mode") or "").lower()
        or (departure_at is not None and str(departure_at or "") != str(est.get("departure_at") or ""))
        or (arrival_by is not None and str(arrival_by or "") != str(est.get("arrival_by") or ""))
        or (previous_task_id is not None and str(previous_task_id or "") != str(est.get("previous_task_id") or ""))
    ):
        stale_est = dict(est)
        stale_est["freshness"] = "stale"
        stale_est["status"] = "stale"
        return {
            "freshness": "stale",
            "is_stale": True,
            "reason": "endpoint_or_mode_changed",
            "expected_fingerprint": expected_fp,
            "stored_fingerprint": stored_fp,
            "updated_route_estimate": stale_est,
        }

    if est.get("freshness") == "stale" or est.get("status") == "stale":
        return {
            "freshness": "stale",
            "is_stale": True,
            "reason": "explicitly_marked_stale",
            "expected_fingerprint": expected_fp,
            "stored_fingerprint": stored_fp,
            "updated_route_estimate": est,
        }

    if est.get("provenance") == "manual_override":
        return {
            "freshness": "manual",
            "is_stale": False,
            "reason": "manual_override_valid",
            "expected_fingerprint": expected_fp,
            "updated_route_estimate": est,
        }

    return {
        "freshness": str(est.get("freshness") or "fresh"),
        "is_stale": False,
        "reason": "context_matched",
        "expected_fingerprint": expected_fp,
        "updated_route_estimate": est,
    }


def validate_task_location_and_travel_fields(fm: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Validates task `location`, `coordinates`, `route_estimate`, and `travel_policy` fields
    for coordinate bounds, explicit units, non-zero unknown durations, local timezone offsets,
    and Google Maps storage/display policy compliance.
    """
    issues: List[Dict[str, Any]] = []
    if not isinstance(fm, dict):
        return issues

    loc = fm.get("location")
    top_coords = fm.get("coordinates")

    if top_coords is not None:
        _, coord_err = parse_coordinates_value(top_coords)
        if coord_err is not None:
            issues.append(
                {
                    "code": "invalid_top_level_coordinates",
                    "field": "coordinates",
                    "message": f"Invalid top-level coordinates: {coord_err}",
                }
            )

    if isinstance(loc, dict):
        loc_coords = loc.get("coordinates")
        if loc_coords is not None:
            l_parsed, l_err = parse_coordinates_value(loc_coords)
            if l_err is not None:
                issues.append(
                    {
                        "code": "invalid_location_coordinates",
                        "field": "location.coordinates",
                        "message": f"Invalid location.coordinates: {l_err}",
                    }
                )
            elif top_coords is not None:
                t_parsed, t_err = parse_coordinates_value(top_coords)
                if t_parsed is not None and t_err is None and t_parsed != l_parsed:
                    issues.append(
                        {
                            "code": "coordinates_location_mismatch",
                            "field": "coordinates",
                            "message": "Top-level coordinates projection does not match canonical location.coordinates.",
                        }
                    )

        prov = str(loc.get("provenance") or "")
        provider_id = (
            loc.get("provider_ref", {}).get("provider")
            if isinstance(loc.get("provider_ref"), dict)
            else None
        )
        if prov == "provider_derived" and provider_id == "google-maps":
            if loc_coords is not None:
                issues.append(
                    {
                        "code": "google_derived_coordinates_persistence_forbidden",
                        "field": "location.coordinates",
                        "message": (
                            "Google-derived coordinates cannot be persisted indefinitely in Markdown task records; "
                            "persist place_id in location.provider_ref instead."
                        ),
                    }
                )
            if loc.get("map_display_permitted") is True:
                issues.append(
                    {
                        "code": "google_derived_cross_map_display_forbidden",
                        "field": "location.map_display_permitted",
                        "message": "Google-derived location data must have map_display_permitted: false for non-Google maps.",
                    }
                )
            if top_coords is not None:
                issues.append(
                    {
                        "code": "google_derived_top_level_coordinates_forbidden",
                        "field": "coordinates",
                        "message": "Top-level coordinates projection is prohibited for Google-derived locations.",
                    }
                )

        if loc.get("map_display_permitted") is False and top_coords is not None:
            issues.append(
                {
                    "code": "unpermitted_map_coordinates_projection",
                    "field": "coordinates",
                    "message": "Top-level coordinates must be null when location.map_display_permitted is false.",
                }
            )

    route_est = fm.get("route_estimate")
    if isinstance(route_est, dict):
        r_status = str(route_est.get("status") or "")
        r_dur = route_est.get("duration_minutes")
        r_prov = str(route_est.get("provenance") or "")
        r_provider = str(route_est.get("provider") or "")

        if r_provider == "google-maps" and r_prov == "provider_derived":
            if route_est.get("persistence_policy") != "persistent_permitted":
                issues.append(
                    {
                        "code": "google_derived_route_persistence_forbidden",
                        "field": "route_estimate",
                        "message": (
                            "Google Routes API estimates are ephemeral_only and must not be persisted indefinitely "
                            "in Markdown task frontmatter."
                        ),
                    }
                )

        if r_dur is not None:
            if isinstance(r_dur, bool) or float(r_dur) <= 0:
                issues.append(
                    {
                        "code": "zero_or_negative_route_duration_forbidden",
                        "field": "route_estimate.duration_minutes",
                        "message": "Unknown or failed route estimates must be null, never 0 or negative minutes.",
                    }
                )
            if route_est.get("duration_unit") != "minutes":
                issues.append(
                    {
                        "code": "missing_duration_unit",
                        "field": "route_estimate.duration_unit",
                        "message": "route_estimate.duration_unit must be explicitly set to 'minutes'.",
                    }
                )
            if r_status not in {"ok", "manual_override", "stale"}:
                issues.append(
                    {
                        "code": "failed_route_with_duration_forbidden",
                        "field": "route_estimate.duration_minutes",
                        "message": f"Route estimate with status '{r_status}' must have duration_minutes: null.",
                    }
                )
        else:
            if r_status in {"ok", "manual_override"}:
                issues.append(
                    {
                        "code": "missing_duration_on_ok_route",
                        "field": "route_estimate.duration_minutes",
                        "message": f"Route estimate with status '{r_status}' requires positive duration_minutes.",
                    }
                )

        for ts_field in ("departure_at", "arrival_by", "observed_at"):
            val = route_est.get(ts_field)
            if val is not None and not _has_explicit_local_offset(val):
                issues.append(
                    {
                        "code": "invalid_local_timezone_offset",
                        "field": f"route_estimate.{ts_field}",
                        "message": f"route_estimate.{ts_field} must have an explicit local timezone offset (not 'Z').",
                    }
                )

    t_pol = fm.get("travel_policy")
    if isinstance(t_pol, dict):
        arr_at = t_pol.get("arrival_at")
        if arr_at is not None and not _has_explicit_local_offset(arr_at):
            issues.append(
                {
                    "code": "invalid_local_timezone_offset",
                    "field": "travel_policy.arrival_at",
                    "message": "travel_policy.arrival_at must have an explicit local timezone offset (not 'Z').",
                }
            )
        man_dur = t_pol.get("manual_duration_minutes")
        if man_dur is not None and (isinstance(man_dur, bool) or float(man_dur) <= 0):
            issues.append(
                {
                    "code": "invalid_manual_duration",
                    "field": "travel_policy.manual_duration_minutes",
                    "message": "travel_policy.manual_duration_minutes must be > 0 when specified.",
                }
            )

    return issues


def enrich_task_location(
    vault_root: Union[Path, str],
    task_fm: Dict[str, Any],
    *,
    query: Optional[str] = None,
    region_code: Optional[str] = None,
    language_code: Optional[str] = None,
    user_coordinates: Optional[Any] = None,
    is_virtual: bool = False,
    workflow_binding: str = "task.location_lookup",
    instance_id: Optional[str] = None,
    transport: Optional[Any] = None,
    force_override: bool = False,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Enriches a task's `location` and `coordinates` fields through the provider-neutral
    `location.resolve` capability or explicit user-supplied coordinates.
    - Preserves `timeEstimate`, date-only `due`, and manual location overrides.
    - Never silently picks among ambiguous address candidates.
    - Enforces provider storage/display restrictions (for `google-maps`, persists `place_id`
      while stripping Google-derived coordinates from persistent Markdown and map projection).
    """
    proposed_fm = dict(task_fm)
    existing_loc = proposed_fm.get("location") if isinstance(proposed_fm.get("location"), dict) else None

    if not force_override and existing_loc is not None:
        if existing_loc.get("user_modified") is True or existing_loc.get("provenance") == "manual_override":
            return {
                "status": "preserved_manual_override",
                "requires_human_approval": True,
                "proposed_frontmatter": proposed_fm,
                "ephemeral_candidates": [],
                "diagnostics": [],
            }

    if is_virtual or (existing_loc and existing_loc.get("is_virtual") is True and not force_override):
        proposed_fm["location"] = {
            "label": str((existing_loc or {}).get("label") or "Virtual / Remote"),
            "address": None,
            "is_virtual": True,
            "coordinates": None,
            "provider_ref": None,
            "provenance": "user_supplied",
            "resolution_status": "virtual",
            "persistence_policy": "persistent_permitted",
            "map_display_permitted": False,
            "attribution": None,
            "candidates": None,
            "user_modified": False,
        }
        proposed_fm["coordinates"] = None
        return {
            "status": "virtual",
            "requires_human_approval": True,
            "proposed_frontmatter": proposed_fm,
            "ephemeral_candidates": [],
            "diagnostics": [],
        }

    if user_coordinates is not None:
        parsed, err = parse_coordinates_value(user_coordinates)
        if parsed is None or err is not None:
            return {
                "status": "invalid_coordinates",
                "requires_human_approval": True,
                "proposed_frontmatter": proposed_fm,
                "ephemeral_candidates": [],
                "diagnostics": [{"code": err or "invalid_coordinates", "message": f"Invalid coordinates: {err}"}],
            }
        lat, lng = parsed
        label_val = str(query or (existing_loc or {}).get("label") or proposed_fm.get("title") or "Task Location")
        existing_prov = str((existing_loc or {}).get("provenance") or "")
        existing_pref = (existing_loc or {}).get("provider_ref")
        is_existing_google = isinstance(existing_pref, dict) and existing_pref.get("provider") == "google-maps"
        new_prov = "manual_override" if (existing_prov == "provider_derived" or is_existing_google) else "user_supplied"
        proposed_fm["location"] = {
            "label": label_val,
            "address": str((existing_loc or {}).get("address") or query or "") or None,
            "is_virtual": False,
            "coordinates": {"latitude": lat, "longitude": lng},
            "provider_ref": None if (existing_prov == "provider_derived" or is_existing_google) else existing_pref,
            "provenance": new_prov,
            "resolution_status": "resolved",
            "persistence_policy": "persistent_permitted",
            "map_display_permitted": True,
            "attribution": None,
            "candidates": None,
            "user_modified": True,
        }
        proposed_fm = synchronize_task_map_coordinates(proposed_fm)
        if isinstance(proposed_fm.get("route_estimate"), dict):
            fresh_check = evaluate_route_freshness(proposed_fm, destination=proposed_fm["location"])
            if fresh_check.get("is_stale") and isinstance(fresh_check.get("updated_route_estimate"), dict):
                proposed_fm["route_estimate"] = fresh_check["updated_route_estimate"]
        return {
            "status": "resolved_user_supplied",
            "requires_human_approval": True,
            "proposed_frontmatter": proposed_fm,
            "ephemeral_candidates": [],
            "diagnostics": [],
        }

    lookup_query = str(
        query
        or (existing_loc or {}).get("address")
        or (existing_loc or {}).get("label")
        or ""
    ).strip()
    if not lookup_query:
        return {
            "status": "missing_location_query",
            "requires_human_approval": True,
            "proposed_frontmatter": proposed_fm,
            "ephemeral_candidates": [],
            "diagnostics": [{"code": "missing_location_query", "message": "No location query or address supplied."}],
        }

    clean_request: Dict[str, Any] = {"query": lookup_query}
    if region_code is not None and str(region_code).strip():
        clean_request["region_code"] = str(region_code).strip()
    if language_code is not None and str(language_code).strip():
        clean_request["language_code"] = str(language_code).strip()

    cap_result = invoke_capability(
        vault_root,
        "location.resolve",
        clean_request,
        workflow_binding=workflow_binding,
        instance_id=instance_id,
        transport=transport,
        env=env,
    )
    c_status = cap_result.get("status")
    candidates = cap_result.get("candidates") if isinstance(cap_result.get("candidates"), list) else []

    if c_status == "ambiguous":
        # Store only non-coordinate candidate summaries for user disambiguation review
        review_cands = [
            {
                "label": c.get("label"),
                "formatted_address": c.get("formatted_address"),
                "place_id": (c.get("provider_ref") or {}).get("place_id") if isinstance(c.get("provider_ref"), dict) else None,
            }
            for c in candidates
            if isinstance(c, dict)
        ]
        proposed_fm["location"] = {
            "label": lookup_query,
            "address": lookup_query,
            "is_virtual": False,
            "coordinates": None,
            "provider_ref": None,
            "provenance": "unresolved",
            "resolution_status": "ambiguous",
            "persistence_policy": "place_id_only",
            "map_display_permitted": False,
            "attribution": cap_result.get("attribution"),
            "candidates": review_cands,
            "user_modified": False,
        }
        proposed_fm["coordinates"] = None
        proposed_fm["review_required"] = True
        proposed_fm["review_notes"] = (
            f"Ambiguous location query '{lookup_query}' matched {len(review_cands)} candidates; human review required."
        )
        return {
            "status": "ambiguous",
            "requires_human_approval": True,
            "proposed_frontmatter": proposed_fm,
            "ephemeral_candidates": candidates,
            "capability_result": cap_result,
            "diagnostics": cap_result.get("diagnostics", []),
        }

    if c_status == "resolved" and len(candidates) == 1:
        winner = candidates[0]
        persistence_pol = str(winner.get("persistence_policy") or "place_id_only")
        map_permitted = bool(winner.get("map_display_permitted") is True)
        persisted_coords = winner.get("coordinates") if (persistence_pol == "persistent_permitted" and map_permitted) else None

        proposed_fm["location"] = {
            "label": winner.get("label") or lookup_query,
            "address": winner.get("formatted_address") or lookup_query,
            "is_virtual": False,
            "coordinates": persisted_coords,
            "provider_ref": winner.get("provider_ref"),
            "provenance": str(winner.get("provenance") or "provider_derived"),
            "resolution_status": "resolved",
            "persistence_policy": persistence_pol,
            "map_display_permitted": map_permitted,
            "attribution": winner.get("attribution"),
            "candidates": None,
            "user_modified": False,
        }
        proposed_fm = synchronize_task_map_coordinates(proposed_fm)
        if isinstance(proposed_fm.get("route_estimate"), dict):
            fresh_check = evaluate_route_freshness(proposed_fm, destination=proposed_fm["location"])
            if fresh_check.get("is_stale") and isinstance(fresh_check.get("updated_route_estimate"), dict):
                proposed_fm["route_estimate"] = fresh_check["updated_route_estimate"]
        return {
            "status": "resolved",
            "requires_human_approval": True,
            "proposed_frontmatter": proposed_fm,
            "ephemeral_candidates": candidates,
            "capability_result": cap_result,
            "diagnostics": [],
        }

    return {
        "status": str(c_status or "unavailable"),
        "requires_human_approval": True,
        "proposed_frontmatter": proposed_fm,
        "ephemeral_candidates": [],
        "capability_result": cap_result,
        "diagnostics": cap_result.get("diagnostics", []),
    }


def estimate_task_commute(
    vault_root: Union[Path, str],
    task_fm: Dict[str, Any],
    *,
    origin: Optional[Dict[str, Any]] = None,
    previous_task_location: Optional[Dict[str, Any]] = None,
    configured_origin: Optional[Dict[str, Any]] = None,
    travel_mode: Optional[str] = None,
    departure_at: Optional[str] = None,
    arrival_by: Optional[str] = None,
    observed_at: str = "2026-09-30T09:00:00-05:00",
    previous_task_id: Optional[str] = None,
    workflow_binding: str = "plan.route_estimate",
    instance_id: Optional[str] = None,
    transport: Optional[Any] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Computes a contextual travel estimate for `task_fm`:
    - Resolves origin from explicit `origin` -> `travel_policy.explicit_origin` ->
      `previous_task_location` -> explicitly configured `configured_origin`. Never silently assumes home.
    - Validates and normalizes `travel_mode` (`normalize_travel_mode`) BEFORE manual override fallback.
    - Uses `travel_policy.manual_duration_minutes` only when explicitly provided and labels it `manual_override`.
    - Keeps `task_fm['timeEstimate']` untouched.
    - Preserves date-only deadlines (`due` without `due_at` never invents `arrival_by`).
    """
    proposed_fm = dict(task_fm)
    loc = proposed_fm.get("location") if isinstance(proposed_fm.get("location"), dict) else None
    t_policy = proposed_fm.get("travel_policy") if isinstance(proposed_fm.get("travel_policy"), dict) else {}

    if loc and loc.get("is_virtual") is True:
        return {
            "status": "virtual_no_travel",
            "requires_travel": False,
            "requires_human_approval": True,
            "duration_minutes": None,
            "ephemeral_route_estimate": None,
            "proposed_frontmatter": proposed_fm,
            "diagnostics": [],
        }

    if not loc or loc.get("resolution_status") == "unresolved":
        return {
            "status": "missing_destination",
            "requires_travel": False,
            "requires_human_approval": True,
            "duration_minutes": None,
            "ephemeral_route_estimate": None,
            "proposed_frontmatter": proposed_fm,
            "diagnostics": [{"code": "missing_destination", "message": "Task has no resolved destination location."}],
        }

    if loc.get("resolution_status") == "ambiguous":
        return {
            "status": "ambiguous_endpoint",
            "requires_travel": False,
            "requires_human_approval": True,
            "duration_minutes": None,
            "ephemeral_route_estimate": None,
            "proposed_frontmatter": proposed_fm,
            "diagnostics": [{"code": "ambiguous_destination", "message": "Task destination is ambiguous; resolve candidates first."}],
        }

    # Resolve origin without ever silently assuming "home"
    resolved_origin: Optional[Dict[str, Any]] = None
    origin_source = "explicit_input"
    if isinstance(origin, dict) and origin:
        resolved_origin = dict(origin)
        origin_source = str(origin.get("source") or "explicit_input")
    elif isinstance(t_policy.get("explicit_origin"), dict) and t_policy["explicit_origin"]:
        resolved_origin = dict(t_policy["explicit_origin"])
        origin_source = "explicit_input"
    elif isinstance(previous_task_location, dict) and previous_task_location:
        resolved_origin = dict(previous_task_location)
        origin_source = "previous_task_location"
    elif isinstance(configured_origin, dict) and configured_origin:
        resolved_origin = dict(configured_origin)
        origin_source = "configured_origin"

    if resolved_origin is None:
        return {
            "status": "missing_origin",
            "requires_travel": True,
            "requires_human_approval": True,
            "duration_minutes": None,
            "ephemeral_route_estimate": None,
            "proposed_frontmatter": proposed_fm,
            "diagnostics": [
                {
                    "code": "missing_origin",
                    "message": "Origin is missing; provide explicit origin, preceding task location, or configured origin (never assuming home).",
                }
            ],
        }
    resolved_origin["source"] = origin_source

    binding = resolve_capability_binding(
        vault_root,
        "routing.estimate",
        workflow_binding=workflow_binding,
        instance_id=instance_id,
        env=env,
    )
    inst_obj = binding.get("instance") or binding.get("instance_config") or {}
    inst_cfg = inst_obj.get("config") if isinstance(inst_obj.get("config"), dict) else {}
    inst_default_mode = inst_cfg.get("default_travel_mode") or inst_obj.get("default_travel_mode")

    raw_mode = travel_mode if travel_mode is not None else t_policy.get("preferred_mode")
    if raw_mode is None or not str(raw_mode).strip():
        raw_mode = inst_default_mode if (inst_default_mode is not None and str(inst_default_mode).strip()) else "driving"

    eff_mode = normalize_travel_mode(str(raw_mode))
    if eff_mode is None or eff_mode not in ALLOWED_TRAVEL_MODES:
        return {
            "status": "unsupported_mode",
            "requires_travel": True,
            "requires_human_approval": True,
            "duration_minutes": None,
            "ephemeral_route_estimate": None,
            "proposed_frontmatter": proposed_fm,
            "diagnostics": [
                {
                    "code": "unsupported_travel_mode",
                    "message": f"Unsupported travel mode '{raw_mode}'. Allowed: {sorted(ALLOWED_TRAVEL_MODES)}",
                }
            ],
        }

    # Preserve date-only deadlines: ONLY use arrival_by or travel_policy.arrival_at or due_at, NEVER date-only `due`
    eff_arrival = arrival_by or t_policy.get("arrival_at") or proposed_fm.get("due_at")
    eff_departure = departure_at

    ctx_fp = compute_route_context_fingerprint(
        origin=resolved_origin,
        destination=loc,
        travel_mode=eff_mode,
        departure_at=eff_departure,
        arrival_by=eff_arrival,
        previous_task_id=previous_task_id,
    )

    # Check if an explicit manual override duration is supplied
    manual_mins = t_policy.get("manual_duration_minutes")
    if manual_mins is not None:
        if isinstance(manual_mins, bool) or float(manual_mins) <= 0:
            return {
                "status": "invalid_manual_duration",
                "requires_travel": True,
                "requires_human_approval": True,
                "duration_minutes": None,
                "ephemeral_route_estimate": None,
                "proposed_frontmatter": proposed_fm,
                "diagnostics": [{"code": "invalid_manual_duration", "message": "Manual travel duration must be > 0 minutes."}],
            }
        def _extract_safe_coords(ep: Dict[str, Any]) -> Optional[Dict[str, float]]:
            if ep.get("provenance") == "provider_derived" or ep.get("persistence_policy") in {"place_id_only", "ephemeral_only"}:
                return None
            parsed_c, err_c = parse_coordinates_value(ep.get("coordinates"))
            if parsed_c is not None and err_c is None:
                return {"latitude": parsed_c[0], "longitude": parsed_c[1]}
            return None

        manual_est: Dict[str, Any] = {
            "origin": {
                "label": resolved_origin.get("label"),
                "address": resolved_origin.get("address"),
                "place_id": resolved_origin.get("place_id")
                or ((resolved_origin.get("provider_ref") or {}).get("place_id") if isinstance(resolved_origin.get("provider_ref"), dict) else None),
                "source": origin_source,
                "coordinates": _extract_safe_coords(resolved_origin),
            },
            "destination": {
                "label": loc.get("label"),
                "address": loc.get("address"),
                "place_id": loc.get("place_id")
                or ((loc.get("provider_ref") or {}).get("place_id") if isinstance(loc.get("provider_ref"), dict) else None),
                "coordinates": _extract_safe_coords(loc),
            },
            "travel_mode": eff_mode,
            "departure_at": eff_departure,
            "arrival_by": eff_arrival,
            "duration_minutes": round(float(manual_mins), 2),
            "duration_seconds": int(round(float(manual_mins) * 60)),
            "duration_unit": "minutes",
            "distance_meters": None,
            "distance_unit": None,
            "observed_at": observed_at,
            "provider": "manual",
            "provenance": "manual_override",
            "freshness": "manual",
            "status": "manual_override",
            "persistence_policy": "persistent_permitted",
            "map_display_permitted": False,
            "attribution": "User-supplied manual travel estimate",
            "context_fingerprint": ctx_fp,
            "previous_task_id": previous_task_id,
        }
        proposed_fm["route_estimate"] = manual_est
        return {
            "status": "manual_override",
            "requires_travel": True,
            "requires_human_approval": True,
            "duration_minutes": manual_est["duration_minutes"],
            "ephemeral_route_estimate": manual_est,
            "proposed_frontmatter": proposed_fm,
            "diagnostics": [],
        }

    request_payload = {
        "origin": resolved_origin,
        "destination": loc,
        "travel_mode": eff_mode,
        "departure_at": eff_departure,
        "arrival_by": eff_arrival,
        "observed_at": observed_at,
        "context_fingerprint": ctx_fp,
        "previous_task_id": previous_task_id,
    }
    cap_result = invoke_capability(
        vault_root,
        "routing.estimate",
        request_payload,
        workflow_binding=workflow_binding,
        instance_id=instance_id,
        transport=transport,
        env=env,
    )
    r_status = str(cap_result.get("status") or "unavailable")
    est_obj = cap_result.get("estimate") if isinstance(cap_result.get("estimate"), dict) else None

    if r_status == "ok" and est_obj is not None:
        est_obj = dict(est_obj)
        if "previous_task_id" not in est_obj or est_obj.get("previous_task_id") is None:
            est_obj["previous_task_id"] = previous_task_id
        if est_obj.get("persistence_policy") == "persistent_permitted":
            proposed_fm["route_estimate"] = est_obj
        else:
            # Ephemeral-only estimates (such as Google Routes API) are kept out of persistent Markdown frontmatter
            proposed_fm["route_estimate"] = None
        return {
            "status": "ok",
            "requires_travel": True,
            "requires_human_approval": True,
            "duration_minutes": est_obj.get("duration_minutes"),
            "ephemeral_route_estimate": est_obj,
            "proposed_frontmatter": proposed_fm,
            "capability_result": cap_result,
            "diagnostics": [],
        }

    return {
        "status": r_status,
        "requires_travel": True,
        "requires_human_approval": True,
        "duration_minutes": None,
        "ephemeral_route_estimate": est_obj,
        "proposed_frontmatter": proposed_fm,
        "capability_result": cap_result,
        "diagnostics": cap_result.get("diagnostics", []),
    }


from datetime import tzinfo as _tzinfo


class _USZoneFallback(_tzinfo):
    """Fallback tzinfo implementing post-2007 US DST rules when system tzdata is unavailable on Windows."""

    def __init__(self, std_offset_hours: int, name: str) -> None:
        self._std_offset = timedelta(hours=std_offset_hours)
        self._dst_offset = timedelta(hours=std_offset_hours + 1)
        self._name = name

    @staticmethod
    def _nth_sunday(year: int, month: int, n: int) -> datetime:
        first = datetime(year, month, 1)
        days_to_sunday = (6 - first.weekday()) % 7
        day = 1 + days_to_sunday + (n - 1) * 7
        return datetime(year, month, day, 2, 0, 0)

    def _is_dst_utc(self, utc_naive: datetime) -> bool:
        year = utc_naive.year
        # DST starts 2nd Sunday of March at 02:00 standard time -> 02:00 - std_offset in UTC
        start_utc = self._nth_sunday(year, 3, 2) - self._std_offset
        # DST ends 1st Sunday of November at 02:00 daylight time -> 02:00 - dst_offset in UTC
        end_utc = self._nth_sunday(year, 11, 1) - self._dst_offset
        return start_utc <= utc_naive < end_utc

    def fromutc(self, dt: datetime) -> datetime:
        if dt.tzinfo is not self:
            raise ValueError("dt.tzinfo is not self")
        utc_naive = dt.replace(tzinfo=None)
        if self._is_dst_utc(utc_naive):
            return (utc_naive + self._dst_offset).replace(tzinfo=self)
        return (utc_naive + self._std_offset).replace(tzinfo=self)

    def utcoffset(self, dt: Optional[datetime]) -> timedelta:
        if dt is None:
            return self._std_offset
        year = dt.year
        start_local = self._nth_sunday(year, 3, 2)
        end_local = self._nth_sunday(year, 11, 1)
        naive = dt.replace(tzinfo=None)
        if start_local <= naive < end_local:
            if naive >= end_local - timedelta(hours=1) and getattr(dt, "fold", 0) == 1:
                return self._std_offset
            return self._dst_offset
        return self._std_offset

    def dst(self, dt: Optional[datetime]) -> timedelta:
        return self.utcoffset(dt) - self._std_offset

    def tzname(self, dt: Optional[datetime]) -> str:
        return self._name


_FALLBACK_US_ZONES: Dict[str, _USZoneFallback] = {
    "America/New_York": _USZoneFallback(-5, "America/New_York"),
    "America/Chicago": _USZoneFallback(-6, "America/Chicago"),
    "America/Denver": _USZoneFallback(-7, "America/Denver"),
    "America/Los_Angeles": _USZoneFallback(-8, "America/Los_Angeles"),
}


def _resolve_tzinfo(tz_name: Optional[str]) -> Optional[Any]:
    if not tz_name:
        return None
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return _FALLBACK_US_ZONES.get(tz_name)


def _parse_local_iso(ts: str, *, tz_name: Optional[str] = None) -> datetime:
    if not _has_explicit_local_offset(ts):
        raise ValueError(f"Timestamp must include explicit local offset (not 'Z'): {ts!r}")
    dt = datetime.fromisoformat(ts.strip())
    target_tz = _resolve_tzinfo(tz_name)
    if target_tz is not None:
        dt = dt.astimezone(target_tz)
    return dt


def _add_elapsed_minutes(dt: datetime, minutes: float, *, tz_name: Optional[str] = None) -> datetime:
    """Adds physical elapsed minutes in UTC and converts back to target local timezone (exact across DST)."""
    utc_dt = dt.astimezone(timezone.utc) + timedelta(minutes=minutes)
    target_tz = _resolve_tzinfo(tz_name)
    if target_tz is not None:
        return utc_dt.astimezone(target_tz)
    return utc_dt.astimezone(dt.tzinfo)


def _format_local_iso(dt: datetime, *, tz_name: Optional[str] = None) -> str:
    target_tz = _resolve_tzinfo(tz_name)
    if target_tz is not None:
        dt = dt.astimezone(target_tz)
    return dt.isoformat(timespec="seconds")


def propose_travel_schedule_window(
    task_fm: Dict[str, Any],
    *,
    route_estimate: Optional[Dict[str, Any]] = None,
    arrival_at: Optional[str] = None,
    departure_at: Optional[str] = None,
    buffer_minutes: Optional[int] = None,
    existing_blocks: Optional[Sequence[Dict[str, Any]]] = None,
    tz_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Computes a proposed travel + buffer + task execution schedule window:
    - Example: 10:00 arrival requirement, 25-minute trip, and 10-minute arrival buffer
      imply a proposed 09:25 departure (`[09:25, 09:50)` travel, `[09:50, 10:00)` buffer,
      `[10:00, 10:00 + timeEstimate)` work execution).
    - Never changes `task_fm["timeEstimate"]` and never double-counts travel duration.
    - Rejects stale route estimates (`status: "stale_route_estimate"`).
    - Detects conflicts against `existing_blocks` across both the occupied transit interval
      and the task execution interval.
    - Returns a proposal (`requires_human_approval: True`, `approval_status: "pending"`);
      never automatically writes `scheduled` without review.
    """
    eff_est = route_estimate if isinstance(route_estimate, dict) else (
        task_fm.get("route_estimate") if isinstance(task_fm.get("route_estimate"), dict) else {}
    )
    t_policy = task_fm.get("travel_policy") if isinstance(task_fm.get("travel_policy"), dict) else {}

    include_travel = bool(t_policy.get("include_travel_in_schedule", True))
    work_minutes = int(task_fm.get("timeEstimate", 45))
    eff_buffer = int(buffer_minutes if buffer_minutes is not None else t_policy.get("buffer_minutes", 0))

    has_manual_policy_dur = t_policy.get("manual_duration_minutes") is not None
    if include_travel and eff_est and not has_manual_policy_dur:
        is_explicitly_stale = eff_est.get("freshness") == "stale" or eff_est.get("status") == "stale"
        is_context_stale = False
        if not is_explicitly_stale and (eff_est.get("origin") or eff_est.get("destination") or eff_est.get("context_fingerprint")):
            fresh_check = evaluate_route_freshness(
                {
                    "location": task_fm.get("location"),
                    "travel_policy": t_policy,
                    "route_estimate": eff_est,
                }
            )
            is_context_stale = bool(fresh_check.get("is_stale"))
        if is_explicitly_stale or is_context_stale:
            return {
                "status": "stale_route_estimate",
                "requires_human_approval": True,
                "approval_status": "pending",
                "task_timeEstimate": work_minutes,
                "travel_duration_minutes": None,
                "buffer_minutes": eff_buffer,
                "diagnostics": [
                    {
                        "code": "stale_route_estimate",
                        "message": "Route estimate is stale due to changed origin, destination, travel mode, or schedule context; re-estimate commute before scheduling.",
                    }
                ],
            }

    dur_raw = eff_est.get("duration_minutes")
    if dur_raw is None and has_manual_policy_dur:
        dur_raw = t_policy.get("manual_duration_minutes")

    if include_travel:
        if dur_raw is None or isinstance(dur_raw, bool) or float(dur_raw) <= 0:
            return {
                "status": "travel_duration_unavailable",
                "requires_human_approval": True,
                "approval_status": "pending",
                "task_timeEstimate": work_minutes,
                "travel_duration_minutes": None,
                "buffer_minutes": eff_buffer,
                "diagnostics": [
                    {
                        "code": "travel_duration_unavailable",
                        "message": "Cannot compute travel departure window without a valid (>0 min) route estimate.",
                    }
                ],
            }
        travel_minutes = float(dur_raw)
    else:
        travel_minutes = 0.0
        eff_buffer = 0

    eff_arrival_iso = arrival_at or t_policy.get("arrival_at") or eff_est.get("arrival_by")
    eff_departure_iso = departure_at or eff_est.get("departure_at")

    if not eff_arrival_iso and not eff_departure_iso:
        # Note: never invent appointment times from date-only `due`
        return {
            "status": "missing_schedule_anchor_time",
            "requires_human_approval": True,
            "approval_status": "pending",
            "task_timeEstimate": work_minutes,
            "travel_duration_minutes": travel_minutes if include_travel else 0.0,
            "buffer_minutes": eff_buffer,
            "diagnostics": [
                {
                    "code": "missing_schedule_anchor_time",
                    "message": "An explicit arrival_at or departure_at timestamp is required (never fabricated from date-only due).",
                }
            ],
        }

    total_lead_minutes = travel_minutes + eff_buffer

    try:
        if eff_arrival_iso:
            arrival_dt = _parse_local_iso(str(eff_arrival_iso), tz_name=tz_name)
            departure_dt = _add_elapsed_minutes(arrival_dt, -total_lead_minutes, tz_name=tz_name)
            travel_end_dt = _add_elapsed_minutes(departure_dt, travel_minutes, tz_name=tz_name)
            work_start_dt = arrival_dt
        else:
            departure_dt = _parse_local_iso(str(eff_departure_iso), tz_name=tz_name)
            travel_end_dt = _add_elapsed_minutes(departure_dt, travel_minutes, tz_name=tz_name)
            arrival_dt = _add_elapsed_minutes(departure_dt, total_lead_minutes, tz_name=tz_name)
            work_start_dt = arrival_dt

        work_end_dt = _add_elapsed_minutes(work_start_dt, work_minutes, tz_name=tz_name)
    except ValueError as exc:
        return {
            "status": "invalid_schedule_anchor_time",
            "requires_human_approval": True,
            "approval_status": "pending",
            "task_timeEstimate": work_minutes,
            "travel_duration_minutes": travel_minutes if include_travel else 0.0,
            "buffer_minutes": eff_buffer,
            "diagnostics": [{"code": "invalid_schedule_anchor_time", "message": str(exc)}],
        }

    proposed_departure_str = _format_local_iso(departure_dt, tz_name=tz_name)
    travel_end_str = _format_local_iso(travel_end_dt, tz_name=tz_name)
    work_start_str = _format_local_iso(work_start_dt, tz_name=tz_name)
    work_end_str = _format_local_iso(work_end_dt, tz_name=tz_name)

    conflicts: List[Dict[str, Any]] = []
    for blk in existing_blocks or []:
        if not isinstance(blk, dict) or not blk.get("start") or not blk.get("end"):
            continue
        b_start = _parse_local_iso(str(blk["start"]), tz_name=tz_name)
        b_end = _parse_local_iso(str(blk["end"]), tz_name=tz_name)

        # Check overlap with occupied travel+buffer interval [departure_dt, work_start_dt)
        if include_travel and total_lead_minutes > 0:
            if departure_dt < b_end and b_start < work_start_dt:
                conflicts.append(
                    {
                        "conflict_kind": "travel_window_conflict",
                        "block_id": blk.get("id") or blk.get("title"),
                        "block_title": blk.get("title"),
                        "block_start": blk["start"],
                        "block_end": blk["end"],
                        "overlapping_interval": [proposed_departure_str, work_start_str],
                    }
                )

        # Check overlap with work execution interval [work_start_dt, work_end_dt)
        if work_start_dt < b_end and b_start < work_end_dt:
            conflicts.append(
                {
                    "conflict_kind": "work_window_conflict",
                    "block_id": blk.get("id") or blk.get("title"),
                    "block_title": blk.get("title"),
                    "block_start": blk["start"],
                    "block_end": blk["end"],
                    "overlapping_interval": [work_start_str, work_end_str],
                }
            )

    return {
        "status": "conflict_detected" if conflicts else "ok",
        "requires_human_approval": True,
        "approval_status": "pending",
        "proposed_departure_at": proposed_departure_str,
        "proposed_arrival_after_travel_at": travel_end_str,
        "proposed_task_scheduled_at": work_start_str,
        "proposed_task_end_at": work_end_str,
        "occupied_travel_interval": {
            "start": proposed_departure_str,
            "end": work_start_str,
            "travel_minutes": travel_minutes,
            "buffer_minutes": eff_buffer,
            "total_transit_minutes": total_lead_minutes,
        },
        "task_execution_interval": {
            "start": work_start_str,
            "end": work_end_str,
            "timeEstimate": work_minutes,
        },
        "total_occupied_minutes": total_lead_minutes + work_minutes,
        "task_timeEstimate": work_minutes,
        "conflicts": conflicts,
        "diagnostics": [],
    }
