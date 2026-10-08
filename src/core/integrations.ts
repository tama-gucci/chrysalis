import fs from "node:fs";
import path from "node:path";
import {
  confined,
  exists,
  readJSON,
  rejectRedirects,
  raw,
  inside,
  PACKAGE_ROOT,
} from "../platforms/filesystem.ts";
import { readRecord } from "../storage/records.ts";
import { routeFingerprint, mapProjection } from "./location.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";

export const ADAPTERS: Record<string, string[]> = {
  "local-filesystem": ["ingestion.discover", "ingestion.read"],
  "google-drive": ["ingestion.discover", "ingestion.read"],
  "google-tasks": ["ingestion.discover", "ingestion.read"],
  "google-maps": ["location.resolve", "routing.estimate"],
  "obsidian-maps": ["visualization.map_projection"],
  "tasknotes-calendar": ["calendar.commitments_read"],
};
const secret =
  /^(resolved_secret|credentials?|.*secret|.*password|(?:access_|refresh_|id_|auth_|bearer_)?token|api_?key|authorization)$/i;
export function redact(value: any): any {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object")
    return Object.fromEntries(
      Object.entries(value)
        .filter(([k]) => !secret.test(k))
        .map(([k, v]) => [k, redact(v)]),
    );
  return value;
}
function configSafety(value: any) {
  if (!value || typeof value !== "object") return;
  for (const [key, item] of Object.entries(value)) {
    if (secret.test(key) && item)
      throw new Error("Inline provider secret forbidden; use secret_ref");
    if (
      key === "secret_ref" &&
      item &&
      !/^(env:[A-Z][A-Z0-9_]*|file:.+)$/.test(String(item))
    )
      throw new Error("Invalid secret reference");
    configSafety(item);
  }
}
export function configuration(ctx: RuntimeContext) {
  const memory = readRecord(ctx.vault, "System/Memory.md").frontmatter,
    result = {
      integrations: structuredClone(
        memory.integrations ?? { instances: {}, bindings: {} },
      ),
      ingestion: structuredClone(memory.ingestion ?? { sources: {} }),
    };
  for (const [file, key, section] of [
    ["System/Integrations.md", "integrations", "instances"],
    ["System/Ingestion-Sources.md", "ingestion", "sources"],
  ])
    if (exists(confined(ctx.vault, file))) {
      const extra = readRecord(ctx.vault, file).frontmatter[key] ?? {};
      result[key] = {
        ...result[key],
        ...extra,
        [section]: { ...result[key]?.[section], ...extra[section] },
        ...(key === "integrations"
          ? { bindings: { ...result[key]?.bindings, ...extra.bindings } }
          : {}),
      };
    }
  configSafety(result);
  return result;
}
function privateFile(ctx: RuntimeContext, file: string) {
  const absolute = rejectRedirects(file);
  if (inside(absolute, ctx.vault) || inside(absolute, PACKAGE_ROOT))
    throw new Error("Secret files must remain outside vault/package");
  return absolute;
}
function credential(ctx: RuntimeContext, ref?: string) {
  if (!ref) return undefined;
  if (ref.startsWith("env:")) return process.env[ref.slice(4)];
  if (ref.startsWith("file:"))
    return raw(privateFile(ctx, ref.slice(5)), 4096)
      .toString("utf8")
      .trim();
  throw new Error("Invalid secret reference");
}
export function integrationStatus(ctx: RuntimeContext) {
  const config = configuration(ctx),
    instances: Metadata = {};
  for (const [id, value] of Object.entries(
    config.integrations.instances ?? {},
  ) as Array<[string, Metadata]>) {
    const installed = !!ADAPTERS[value.integration],
      enabled = value.enabled === true,
      configured =
        installed &&
        enabled &&
        ["read-only", "read_only"].includes(value.access ?? "read-only");
    const fixture = value.export_path ?? value.fixture_path,
      fixtureAvailable =
        typeof fixture === "string" && exists(rejectRedirects(fixture)),
      credentialsPresent = !!credential(ctx, value.secret_ref);
    instances[id] = {
      integration: value.integration,
      installed,
      configured,
      credentials_present: credentialsPresent,
      fixture_available: fixtureAvailable,
      authenticated: fixture ? false : null,
      available:
        configured &&
        (fixtureAvailable ||
          value.integration === "obsidian-maps" ||
          (value.integration === "google-maps" && credentialsPresent)),
      verified: false,
      reason: !installed
        ? "unsupported"
        : !enabled
          ? "disabled"
          : fixture && !fixtureAvailable
            ? "fixture_unavailable"
            : "account_workflow_unverified",
    };
  }
  return { status: "ok", integrations: instances };
}
function allowed(request: Metadata, keys: string[]) {
  for (const k of Object.keys(request))
    if (!keys.includes(k))
      throw new Error(
        "Request cannot override trusted configuration or disclose unrelated data: " +
          k,
      );
}
export function sourceConfiguration(ctx: RuntimeContext, alias: string) {
  const c = configuration(ctx),
    source = c.ingestion.sources?.[alias];
  if (!source || source.enabled !== true)
    throw new Error("Source missing or disabled");
  if (
    !["read-only", "read_only"].includes(
      source.mode ?? source.access ?? "read-only",
    )
  )
    throw new Error("Sources must be read-only");
  const instance = source.instance
    ? c.integrations.instances?.[source.instance]
    : undefined;
  if (source.instance && (!instance || instance.enabled !== true))
    throw new Error("Source integration missing or disabled");
  return {
    ...instance,
    ...source,
    integration:
      source.integration ?? instance?.integration ?? "local-filesystem",
  };
}
export async function capability(
  ctx: RuntimeContext,
  name: string,
  request: Metadata = {},
  binding?: string,
) {
  const config = configuration(ctx);
  let selected = binding
    ? config.integrations.bindings?.[binding]
    : config.integrations.bindings?.[name];
  if (typeof selected === "string")
    selected = { instance: selected, capability: name };
  if (!selected || selected.capability !== name)
    return {
      status: "unavailable",
      capability: name,
      reason: "binding_missing",
    };
  const instance = config.integrations.instances?.[selected.instance];
  if (
    !instance ||
    instance.enabled !== true ||
    !ADAPTERS[instance.integration]?.includes(name)
  )
    return {
      status: "unavailable",
      capability: name,
      reason: "integration_disabled_or_unsupported",
    };
  if (!["read-only", "read_only"].includes(instance.access ?? "read-only"))
    throw new Error("Provider is not read-only");
  if (name === "visualization.map_projection") {
    allowed(request, ["tasks"]);
    if (!Array.isArray(request.tasks) || request.tasks.length > 500)
      throw new Error("Bounded tasks required");
    return mapProjection(request.tasks);
  }
  if (name === "calendar.commitments_read") {
    allowed(request, []);
    if (!instance.export_path || !exists(rejectRedirects(instance.export_path)))
      return { status: "unavailable", reason: "observation_missing" };
    const result = readJSON(instance.export_path);
    if (
      !["ok", "empty"].includes(result.status) ||
      !result.observed_at ||
      !Array.isArray(result.events)
    )
      throw new Error("Invalid calendar observation");
    return result;
  }
  if (["ingestion.discover", "ingestion.read"].includes(name)) {
    allowed(request, ["source_alias", "page_size", "page_token"]);
    const { discover } = await import("./ingestion.ts");
    return discover(ctx, request);
  }
  let response: Metadata;
  if (name === "location.resolve")
    allowed(request, ["query", "language_code", "region_code"]);
  else
    allowed(request, [
      "origin",
      "destination",
      "travel_mode",
      "arrival_by",
      "departure_at",
      "previous_task_id",
      "observed_at",
    ]);
  if (instance.export_path) {
    if (!exists(rejectRedirects(instance.export_path)))
      return { status: "unavailable", reason: "fixture_unavailable" };
    response = readJSON(instance.export_path);
  } else {
    const key = credential(ctx, instance.secret_ref);
    if (!key) return { status: "unavailable", reason: "credentials_missing" };
    // Live transport is opt-in in private operator configuration. No request can enable it.
    if (instance.live_read_enabled !== true)
      return { status: "unavailable", reason: "live_transport_not_enabled" };
    const isLocation = name === "location.resolve",
      endpoint = isLocation
        ? "https://places.googleapis.com/v1/places:searchText"
        : "https://routes.googleapis.com/directions/v2:computeRoutes";
    const body = isLocation
      ? {
          textQuery: request.query,
          languageCode: request.language_code,
          regionCode: request.region_code,
        }
      : {
          origin: { placeId: request.origin?.place_id },
          destination: { placeId: request.destination?.place_id },
          travelMode: {
            driving: "DRIVE",
            walking: "WALK",
            bicycling: "BICYCLE",
            transit: "TRANSIT",
          }[request.travel_mode ?? "driving"],
          ...(request.arrival_by ? { arrivalTime: request.arrival_by } : {}),
          ...(request.departure_at
            ? { departureTime: request.departure_at }
            : {}),
        };
    const abort = AbortSignal.any([
      AbortSignal.timeout(10000),
      ...(ctx.signal ? [ctx.signal] : []),
    ]);
    const result = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": key,
        "X-Goog-FieldMask": isLocation
          ? "places.id,places.displayName,places.formattedAddress,places.location"
          : "routes.duration,routes.distanceMeters",
      },
      body: JSON.stringify(body),
      signal: abort,
    });
    if (!result.ok)
      return {
        status: "unavailable",
        reason: "provider_http_" + result.status,
      };
    const chunks: Uint8Array[] = [];
    let size = 0;
    for await (const chunk of result.body! as any) {
      if ((size += chunk.length) > 1024 * 1024)
        throw new Error("Provider response limit exceeded");
      chunks.push(chunk);
    }
    response = JSON.parse(Buffer.concat(chunks).toString("utf8"));
  }
  if (name === "location.resolve") {
    if (!Array.isArray(response.places))
      throw new Error("Malformed location response");
    const places = response.places.slice(0, 20);
    if (!places.length) return { status: "empty", location: null };
    if (places.length > 1)
      return {
        status: "ambiguous",
        ephemeral_candidates: places,
        location: null,
      };
    const p = places[0];
    if (typeof p.id !== "string")
      throw new Error("Location identifier missing");
    return {
      status: "resolved",
      location: {
        label: p.displayName?.text ?? request.query,
        coordinates: null,
        provider_ref: { provider: "google-maps", place_id: p.id },
        provenance: "provider_derived",
        resolution_status: "resolved",
        persistence_policy: "place_id_only",
        map_display_permitted: false,
      },
      ephemeral_candidate: p,
    };
  }
  if (!Array.isArray(response.routes))
    throw new Error("Malformed route response");
  if (!response.routes.length) return { status: "empty" };
  const r = response.routes[0];
  if (!/^\d+(?:\.\d+)?s$/.test(r.duration))
    throw new Error("Invalid route duration");
  return {
    status: "ok",
    estimate: {
      ...request,
      duration_minutes: Number(r.duration.slice(0, -1)) / 60,
      duration_unit: "minutes",
      distance_meters: r.distanceMeters,
      provider: "google-maps",
      provenance: "provider_derived",
      status: "ok",
      persistence_policy: "ephemeral_only",
      map_display_permitted: false,
      context_fingerprint: routeFingerprint(request),
      observed_at: request.observed_at ?? ctx.now ?? new Date().toISOString(),
      ttl_seconds: 900,
    },
  };
}
