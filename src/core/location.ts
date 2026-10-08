import { digest, canonical } from "../platforms/filesystem.ts";
import { instant, serialize } from "../time/timezone.ts";
import { Temporal } from "@js-temporal/polyfill";
import type { Metadata } from "../contracts/types.ts";

export function locationPolicy(fm: Metadata) {
  const location = fm.location,
    route = fm.route_estimate;
  if (location?.coordinates) {
    const c = location.coordinates;
    if (
      !Number.isFinite(c.latitude) ||
      !Number.isFinite(c.longitude) ||
      Math.abs(c.latitude) > 90 ||
      Math.abs(c.longitude) > 180
    )
      throw new Error("invalid_coordinates");
  }
  const projection = location?.coordinates
    ? [location.coordinates.latitude, location.coordinates.longitude]
    : null;
  if (location && canonical(projection) !== canonical(fm.coordinates ?? null))
    throw new Error("coordinate_projection_mismatch");
  if (
    location?.provider_ref?.provider === "google-maps" &&
    location.provenance === "provider_derived" &&
    (location.coordinates ||
      fm.coordinates ||
      location.persistence_policy !== "place_id_only" ||
      location.map_display_permitted)
  )
    throw new Error("google_derived_coordinates_persistence_forbidden");
  if (
    route?.persistence_policy === "ephemeral_only" ||
    (route?.provider === "google-maps" &&
      route.provenance === "provider_derived")
  )
    throw new Error("google_derived_route_persistence_forbidden");
}
export function routeFingerprint(request: Metadata) {
  return digest(
    Object.fromEntries(
      [
        "origin",
        "destination",
        "travel_mode",
        "arrival_by",
        "departure_at",
        "previous_task_id",
      ].map((k) => [k, request[k] ?? null]),
    ),
  );
}
export function routeFreshness(
  estimate: Metadata,
  request: Metadata,
  now: string,
) {
  try {
    const age =
      (instant(now).epochMilliseconds -
        instant(estimate.observed_at).epochMilliseconds) /
      1000;
    return estimate.status === "ok" &&
      estimate.context_fingerprint === routeFingerprint(request) &&
      age >= 0 &&
      age <= (estimate.ttl_seconds ?? 900)
      ? "fresh"
      : "stale";
  } catch {
    return "stale";
  }
}
export function travelWindow(
  task: Metadata,
  estimate: Metadata,
  arrival: string,
  zone: string,
  buffer = 10,
) {
  if (
    estimate.duration_unit !== "minutes" ||
    !Number.isFinite(estimate.duration_minutes) ||
    estimate.duration_minutes < 0 ||
    !Number.isFinite(buffer) ||
    buffer < 0
  )
    throw new Error("Invalid travel interval");
  const end = instant(arrival),
    departure = end.subtract({
      milliseconds: Math.round((estimate.duration_minutes + buffer) * 60000),
    }),
    after = end.subtract({ milliseconds: Math.round(buffer * 60000) });
  return {
    status: "ok",
    proposed_departure_at: serialize(departure, zone),
    proposed_arrival_after_travel_at: serialize(after, zone),
    proposed_task_scheduled_at: serialize(end, zone),
    task_timeEstimate: task.timeEstimate,
    occupied_travel_interval: {
      start: serialize(departure, zone),
      end: serialize(end, zone),
      total_transit_minutes: estimate.duration_minutes + buffer,
    },
  };
}
export function mapProjection(tasks: Metadata[]) {
  const markers: Metadata[] = [],
    omitted: Metadata[] = [];
  for (const task of tasks) {
    try {
      locationPolicy(task);
    } catch {
      omitted.push({ id: task.id, reason: "invalid_location" });
      continue;
    }
    const l = task.location;
    if (
      !l?.coordinates ||
      !l.map_display_permitted ||
      (l.provider_ref?.provider === "google-maps" &&
        l.provenance === "provider_derived")
    ) {
      omitted.push({ id: task.id, reason: "display_policy" });
      continue;
    }
    markers.push({ id: task.id, coordinates: l.coordinates, label: l.label });
  }
  return { status: "ok", markers, omitted };
}
