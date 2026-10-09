import { providerJSON } from "../http.ts";
import { requestBudget } from "../profile.ts";
import { observation } from "../contracts.ts";
import { configuredZone } from "../../core/runtime.ts";
import { nowStamp } from "../../time/timezone.ts";
import { routeFingerprint } from "../../core/location.ts";
import { Temporal } from "@js-temporal/polyfill";
import type { Instance, ProviderPorts } from "../contracts.ts";
import type { RuntimeContext, Metadata } from "../../contracts/types.ts";

export async function mapsEvidence(
  ctx: RuntimeContext,
  instance: Instance,
  ports: ProviderPorts,
  args: Metadata,
  location = false,
) {
  if (instance.provider !== "google-maps") throw Error("provider_mismatch");
  // Validate the entire batch before any billable provider request.
  if (!location)
    for (const pair of args.pairs) {
      if (pair.arrival_by && pair.departure_at)
        throw Error("choose_arrival_or_departure");
      if (pair.arrival_by && pair.travel_mode !== "transit")
        throw Error("arrival_time_requires_transit");
      for (const time of [pair.arrival_by, pair.departure_at].filter(Boolean))
        Temporal.Instant.from(time);
    }
  const key = (await ports.secrets.get(instance.secret_id))?.api_key;
  if (!key) throw Error("provider_reconnect_required");
  const headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": key,
    "X-Goog-FieldMask": location
      ? "places.id,places.displayName,places.formattedAddress"
      : "routes.duration",
  };
  if (location) {
    await requestBudget(ctx, instance);
    const r = await providerJSON(
      ctx,
      ports,
      "https://places.googleapis.com/v1/places:searchText",
      {
        method: "POST",
        headers,
        body: JSON.stringify({
          textQuery: args.query,
          ...(args.region_code ? { regionCode: args.region_code } : {}),
        }),
      },
    );
    if (!Array.isArray(r.places ?? []) || (r.places?.length ?? 0) > 20)
      throw Error("provider_invalid_response");
    const places = (r.places ?? []).map((p) => {
      if (
        typeof p.id !== "string" ||
        !p.id ||
        p.id.length > 500 ||
        [p.displayName?.text, p.formattedAddress].some(
          (v) => v !== undefined && (typeof v !== "string" || v.length > 2000),
        )
      )
        throw Error("provider_invalid_response");
      return {
        place_id: p.id,
        label: p.displayName?.text,
        address: p.formattedAddress,
      };
    });
    return observation(ctx, instance, "location.resolve", {
      status:
        places.length === 1
          ? "resolved"
          : places.length
            ? "ambiguous"
            : "empty",
      candidates: places,
      attribution: "Google Maps",
      usage_policy: {
        audience: "native_operator_only",
        persistence: "memory_only",
        stored_location_fields: "place_id_only",
      },
    });
  }
  const results: Metadata[] = [];
  for (const pair of args.pairs) {
    try {
      await requestBudget(ctx, instance);
      const r = await providerJSON(
        ctx,
        ports,
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        {
          method: "POST",
          headers,
          body: JSON.stringify({
            origin: { placeId: pair.origin.place_id },
            destination: { placeId: pair.destination.place_id },
            travelMode: {
              driving: "DRIVE",
              walking: "WALK",
              bicycling: "BICYCLE",
              transit: "TRANSIT",
            }[pair.travel_mode],
            ...(pair.departure_at ? { departureTime: pair.departure_at } : {}),
            ...(pair.arrival_by ? { arrivalTime: pair.arrival_by } : {}),
            ...(pair.travel_mode === "driving"
              ? { routingPreference: "TRAFFIC_AWARE" }
              : {}),
          }),
        },
      );
      if (!Array.isArray(r.routes ?? []) || (r.routes?.length ?? 0) > 20)
        throw Error("provider_invalid_response");
      if (!r.routes?.length) {
        results.push({ status: "empty" });
        continue;
      }
      if (!/^\d+(?:\.\d+)?s$/.test(r.routes[0].duration))
        throw Error("provider_invalid_response");
      results.push({
        status: "ok",
        duration_minutes: Number(r.routes[0].duration.slice(0, -1)) / 60,
        duration_unit: "minutes",
        context_fingerprint: routeFingerprint(pair),
        observed_at: nowStamp(configuredZone(ctx), ctx.now),
        ttl_seconds: 900,
      });
    } catch (e: any) {
      const code = String(e?.message);
      results.push({
        status: "unavailable",
        reason: /^provider_[a-z_]+$|^provider_http_\d{3}$/.test(code)
          ? code
          : "provider_unavailable",
      });
    }
  }
  return observation(ctx, instance, "routing.estimate", {
    status: results.every((r) => r.status === "ok") ? "ok" : "partial",
    estimates: results,
    attribution: "Google Maps",
    usage_policy: {
      audience: "native_operator_only",
      persistence: "memory_only",
      model_disclosure: false,
    },
  });
}
